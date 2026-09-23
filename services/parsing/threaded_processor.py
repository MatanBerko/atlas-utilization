"""
ThreadedFileProcessor - Orchestrates concurrent file parsing.

Single responsibility: Manage thread pool for parsing multiple files concurrently.
"""

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Iterator, Optional, Callable
from tqdm import tqdm

from domain.events import EventBatch
from .file_parser import FileParser, PartialFileReadError, RequiredScalarBranchMissingError


class ThreadedFileProcessor:
    """
    Service for processing multiple files concurrently using thread pool.
    
    Coordinates FileParser instances across threads and yields results
    as they complete.
    """
    
    def __init__(
        self,
        file_parser: FileParser,
        max_threads: int,
        show_progress: bool = True
    ):
        """
        Initialize threaded processor.
        
        Args:
            file_parser: FileParser instance to use
            max_threads: Maximum number of concurrent threads
            show_progress: Whether to show progress bar
        """
        if max_threads <= 0:
            raise ValueError(f"max_threads must be positive, got {max_threads}")
        
        self.file_parser = file_parser
        self.max_threads = max_threads
        self.show_progress = show_progress
    
    def process_files(
        self,
        file_urls: list[str],
        tree_names: list[str],
        release_year: str,
        batch_size: int = 40_000,
        enable_jet_tagging: bool = False,
        jet_btagging_thresholds: Optional[dict[str, float]] = None,
        extra_scalar_branches: Optional[dict[str, list[str]]] = None,
        extra_object_fields: Optional[dict[str, list[str]]] = None,
        read_event_weights: bool = False,
        read_pileup_info: bool = False,
        on_success: Optional[Callable[[str, int, float], None]] = None,
        on_error: Optional[Callable[[str, Exception], None]] = None,
        on_probe_stats: Optional[Callable[[str, dict], None]] = None,
    ) -> Iterator[EventBatch]:
        """
        Process multiple files concurrently and yield EventBatch objects.

        Args:
            file_urls: List of file URLs to process
            tree_names: List of possible tree names
            release_year: Release year for schema lookup
            batch_size: Batch size for reading large files
            extra_scalar_branches: Optional extra scalar branch groups to
                read on every file (see FileParser.parse_file); absent/None
                reproduces existing behaviour exactly.
            extra_object_fields: Optional extra per-object fields to read on
                every file (see FileParser.parse_file); absent/None
                reproduces existing behaviour exactly.
            read_event_weights: Optional (default False, see
                FileParser.parse_file). Simulation-only.
            read_pileup_info: Optional (default False, see
                FileParser.parse_file).
            on_success: Optional callback(file_url, event_count, time_sec) on success
            on_error: Optional callback(file_url, exception) on error
            on_probe_stats: Optional callback(file_url, probe_stats), called
                once per successfully-parsed file with that file's
                branch-accessibility-probe retry/final-failure counts
                (implementation task 5, Part B); purely additive
                statistics, never called with nonzero counts for any file
                whose probes all succeeded on the first attempt.

        Yields:
            EventBatch objects as files are successfully parsed
        """
        total_files = len(file_urls)

        with ThreadPoolExecutor(max_workers=self.max_threads) as executor:
            # Submit all parse jobs
            futures = {
                executor.submit(
                    self._parse_single_file,
                    file_url,
                    tree_names,
                    release_year,
                    batch_size,
                    enable_jet_tagging,
                    jet_btagging_thresholds,
                    extra_scalar_branches,
                    extra_object_fields,
                    read_event_weights,
                    read_pileup_info,
                ): file_url
                for file_url in file_urls
            }
            
            # Process results as they complete
            progress_bar = self._create_progress_bar(total_files)

            # Missing-required-branch failures (implementation task 3, Part
            # B3) are collected here instead of being swallowed as ordinary
            # per-file failures below -- every other exception type (network
            # errors, corrupt files, ...) keeps today's exact behaviour:
            # logged, reported via on_error, file skipped, run continues.
            missing_branch_failures: list[tuple[str, str, list[str]]] = []

            # Partial reads with weights enabled (implementation task 6,
            # Part A): a PartialFileReadError used to still be yielded as a
            # partial batch (its events, including genWeight, get used
            # downstream) while the file itself was reported only via
            # on_error, never on_success -- so it never lands in a
            # "processed_urls" list built from on_success alone, and its
            # genEventSumw is excluded from the aggregation in
            # orchestration/handlers/parsing_handler.py, silently biasing
            # the numerator (genWeight used) vs. denominator (genEventSumw
            # summed) upward. When read_event_weights is set, a partial
            # read is a loud, record-aborting failure instead -- reported
            # the same way as a RequiredScalarBranchMissingError. Any file
            # that reaches this point as data (not simulation) while
            # read_event_weights is set would already have raised
            # SimulationFieldRequestedOnDataError earlier in parsing
            # (before any batch is ever read), so a PartialFileReadError
            # seen here with read_event_weights enabled is always for a
            # simulation file -- data files, and any run with
            # read_event_weights off, keep today's exact behaviour.
            partial_read_with_weights_failures: list[tuple[str, str, list[str]]] = []

            with progress_bar as pbar:
                for future in as_completed(futures):
                    file_url = futures[future]

                    try:
                        result = future.result(timeout=300)  # 5 minute timeout per file

                        if result is not None:
                            events, processing_time, partial_error, probe_stats = result

                            if partial_error is not None and read_event_weights:
                                logging.warning(
                                    "Partial read of a simulation file with "
                                    "read_event_weights enabled -- treating as a "
                                    "loud failure instead of a partial batch: %s",
                                    partial_error,
                                )
                                partial_read_with_weights_failures.append((
                                    file_url, "PartialFileRead", [str(partial_error)]
                                ))
                                if on_error:
                                    on_error(file_url, partial_error)
                                continue

                            # Create EventBatch
                            batch = self._create_event_batch(
                                events=events,
                                file_url=file_url,
                                release_year=release_year,
                                processing_time=processing_time
                            )

                            if partial_error is not None:
                                logging.warning("Partial parse retained: %s", partial_error)
                                if on_error:
                                    on_error(file_url, partial_error)
                            elif on_success:
                                on_success(file_url, batch.event_count, processing_time)

                            if on_probe_stats and (probe_stats["n_retries"] or probe_stats["n_final_failures"]):
                                on_probe_stats(file_url, probe_stats)

                            if batch.event_count > 0:
                                yield batch

                    except RequiredScalarBranchMissingError as e:
                        logging.warning(f"Required scalar branch missing in {file_url}: {e}")
                        missing_branch_failures.extend(e.failures)
                        if on_error:
                            on_error(file_url, e)

                    except Exception as e:
                        logging.warning(f"Error processing file {file_url}: {e}")
                        if on_error:
                            on_error(file_url, e)

                    finally:
                        if self.show_progress:
                            pbar.update(1)

            if missing_branch_failures:
                raise RequiredScalarBranchMissingError(missing_branch_failures)
            if partial_read_with_weights_failures:
                raise RequiredScalarBranchMissingError(partial_read_with_weights_failures)

    def _parse_single_file(
        self,
        file_url: str,
        tree_names: list[str],
        release_year: str,
        batch_size: int,
        enable_jet_tagging: bool,
        jet_btagging_thresholds: Optional[dict[str, float]],
        extra_scalar_branches: Optional[dict[str, list[str]]] = None,
        extra_object_fields: Optional[dict[str, list[str]]] = None,
        read_event_weights: bool = False,
        read_pileup_info: bool = False,
    ) -> tuple:
        """
        Parse a single file (runs in thread).

        Args:
            file_url: File URL to parse
            tree_names: List of possible tree names
            release_year: Release year
            batch_size: Batch size for reading

        Returns:
            Tuple of (events, processing_time, partial_error, probe_stats).
            probe_stats (implementation task 5, Part B) is
            {"n_retries": int, "n_final_failures": int} for THIS file's
            branch-accessibility probes -- purely additive bookkeeping.
        """
        import time
        start_time = time.time()

        probe_stats = {"n_retries": 0, "n_final_failures": 0}

        def _on_probe_retry():
            probe_stats["n_retries"] += 1

        def _on_probe_final_failure(branch_name: str):
            probe_stats["n_final_failures"] += 1

        partial_error = None
        try:
            events = self.file_parser.parse_file(
                file_path=file_url,
                tree_names=tree_names,
                release_year=release_year,
                batch_size=batch_size,
                enable_jet_tagging=enable_jet_tagging,
                jet_btagging_thresholds=jet_btagging_thresholds,
                extra_scalar_branches=extra_scalar_branches,
                extra_object_fields=extra_object_fields,
                read_event_weights=read_event_weights,
                read_pileup_info=read_pileup_info,
                on_probe_retry=_on_probe_retry,
                on_probe_final_failure=_on_probe_final_failure,
            )
        except PartialFileReadError as error:
            events = error.events
            partial_error = error

        processing_time = time.time() - start_time

        if events is None:
            raise RuntimeError("Parser returned no event data")

        return (events, processing_time, partial_error, probe_stats)
    
    def _create_event_batch(
        self,
        events,
        file_url: str,
        release_year: str,
        processing_time: float
    ) -> EventBatch:
        """
        Create EventBatch from parsed events.
        
        Args:
            events: Awkward array of events
            file_url: Source file URL
            release_year: Release year
            processing_time: Time taken to parse
            
        Returns:
            EventBatch object
        """
        # Extract file ID from URL (use hash for now)
        file_id = hash(file_url)
        
        # Calculate size
        size_bytes = events.layout.nbytes if hasattr(events, 'layout') else 0
        event_count = len(events) if hasattr(events, '__len__') else 0
        
        return EventBatch(
            events=events,
            file_id=file_id,
            file_url=file_url,
            release_year=release_year,
            size_bytes=size_bytes,
            event_count=event_count,
            processing_time_sec=processing_time
        )
    
    def _create_progress_bar(self, total: int):
        """
        Create progress bar or no-op context manager.
        
        Args:
            total: Total number of items
            
        Returns:
            Progress bar context manager or no-op
        """
        if self.show_progress:
            return tqdm(
                total=total,
                desc="Processing files",
                unit="file",
                dynamic_ncols=True,
                mininterval=1
            )
        else:
            # No-op context manager
            from contextlib import nullcontext
            return nullcontext()


class ParsingStatisticsCollector:
    """
    Helper class to collect statistics during parsing.
    
    Thread-safe collector that aggregates parsing statistics.
    """
    
    def __init__(self):
        """Initialize statistics collector."""
        import threading
        self.lock = threading.Lock()
        self.successful_count = 0
        self.failed_count = 0
        self.total_events = 0
        self.total_size_bytes = 0
        self.failed_files = []
        self.processing_times = []
        self._failure_reason_counts: dict[str, int] = {}
        # implementation task 5, Part B: branch-accessibility-probe retry
        # bookkeeping, additive only -- never affects which branches end up
        # accessible.
        self._n_probe_retries = 0
        self._n_probe_final_failures = 0
        self._files_with_probe_retries: list[tuple[str, dict]] = []

    def record_success(self, file_url: str, event_count: int, size_bytes: int, time_sec: float):
        """Record a successful parse."""
        with self.lock:
            self.successful_count += 1
            self.total_events += event_count
            self.total_size_bytes += size_bytes
            self.processing_times.append(time_sec)

    def record_probe_stats(self, file_url: str, probe_stats: dict):
        """Record a file's branch-accessibility-probe retry/final-failure
        counts (implementation task 5, Part B)."""
        with self.lock:
            self._n_probe_retries += probe_stats.get("n_retries", 0)
            self._n_probe_final_failures += probe_stats.get("n_final_failures", 0)
            self._files_with_probe_retries.append((file_url, dict(probe_stats)))
    
    def record_failure(self, file_url: str, error: Exception):
        """Record a failed parse."""
        with self.lock:
            self.failed_count += 1
            # Reason (exception type name) is tracked alongside the message,
            # purely additively, so the final parsing summary/log can report
            # a breakdown of why files were skipped (implementation task 3,
            # Part B3) without changing failed_files' existing use as a
            # (file_url, str(error)) list anywhere it's already consumed --
            # see get_summary()'s "failure_reason_counts".
            self.failed_files.append((file_url, str(error)))
            self._failure_reason_counts[type(error).__name__] = (
                self._failure_reason_counts.get(type(error).__name__, 0) + 1
            )
            partial_events = getattr(error, "events", None)
            if partial_events is not None:
                self.total_events += len(partial_events)
                if hasattr(partial_events, "layout"):
                    self.total_size_bytes += partial_events.layout.nbytes
    
    def get_summary(self) -> dict:
        """Get statistics summary."""
        with self.lock:
            total = self.successful_count + self.failed_count
            avg_time = (
                sum(self.processing_times) / len(self.processing_times)
                if self.processing_times else 0
            )
            
            return {
                "total_files": total,
                "successful_files": self.successful_count,
                "failed_files": self.failed_count,
                "success_rate": (
                    (self.successful_count / total * 100) if total > 0 else 0
                ),
                "total_events": self.total_events,
                "total_size_mb": self.total_size_bytes / (1024 * 1024),
                "average_processing_time_sec": avg_time,
                "failed_file_list": self.failed_files,
                "failure_reason_counts": dict(self._failure_reason_counts),
                "n_probe_retries": self._n_probe_retries,
                "n_probe_final_failures": self._n_probe_final_failures,
                "files_with_probe_retries": list(self._files_with_probe_retries),
            }
