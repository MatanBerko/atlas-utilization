"""
ParsingHandler - Handles parsing state.

Orchestrates file parsing using services.
Supports batch job splitting via batch_job_index / total_batch_jobs.
"""

import os
from datetime import datetime
from pathlib import Path
import uproot
import awkward as ak

import gc

from orchestration.context import PipelineContext
from orchestration.states import PipelineState
from .base import StateHandler
from services.parsing.file_parser import FileParser
from services.parsing.event_accumulator import EventAccumulator
from services.parsing.threaded_processor import ThreadedFileProcessor, ParsingStatisticsCollector
from domain.statistics import ParsingStatistics
from domain.events import EventBatch
from services.parsing.event_selection import apply_parsing_event_selection
from services.parsing.event_deduplication import EventDeduplicator
from utils.batching import get_batch_slice_by_year


def _record_key_from_release_year(release_year: str) -> str:
    """'record_30530' -> '30530'; anything else returned unchanged."""
    if release_year.startswith("record_"):
        return release_year.split("_", 1)[1]
    return release_year


def _profile_requires_muon(profile: dict) -> bool:
    """True when a selection_by_record profile requires >=1 muon."""
    pc = (profile or {}).get("particle_counts", {}) or {}
    muons = pc.get("muons", {}) or {}
    return int(muons.get("min", 0)) >= 1


class ParsingHandler(StateHandler):
    """
    Handler for PARSING state.
    
    Uses FileParser and ThreadedFileProcessor to parse files,
    EventAccumulator to create chunks, and saves results.
    """
    
    def __init__(
        self,
        file_parser: FileParser,
        threaded_processor: ThreadedFileProcessor,
        event_accumulator: EventAccumulator
    ):
        """
        Initialize handler.
        
        Args:
            file_parser: File parser service
            threaded_processor: Threaded processor service
            event_accumulator: Event accumulator service
        """
        super().__init__()
        self.file_parser = file_parser
        self.processor = threaded_processor
        self.accumulator = event_accumulator
    
    def _save_chunk_to_root(self, chunk, file_path: str):
        """
        Save an EventChunk to a ROOT file.
        
        Args:
            chunk: EventChunk with awkward array data
            file_path: Path where to save the ROOT file
        """
        try:
            # Get the awkward array from the chunk
            if hasattr(chunk, 'events'):
                events_data = chunk.events
            elif hasattr(chunk, 'data'):
                events_data = chunk.data
            else:
                self.logger.warning(f"Chunk has no data to save: {chunk}")
                return
            
            # Flatten the nested structure for ROOT compatibility
            # Each particle type becomes separate branches
            flattened = {}
            for field in events_data.fields:
                particle_data = events_data[field]
                # Store as jagged array - ROOT can handle var * type at top level
                flattened[field] = particle_data
            
            # Save to ROOT file using uproot
            with uproot.recreate(file_path) as root_file:
                root_file["events"] = flattened
            
            self.logger.debug(f"Successfully wrote {len(events_data)} events to {file_path}")
            
        except Exception as e:
            self.logger.error(f"Failed to save chunk to {file_path}: {e}")
            raise
    
    def handle(self, context: PipelineContext) -> tuple[PipelineContext, PipelineState]:
        """
        Parse files and determine next state.
        
        Args:
            context: Current pipeline context
            
        Returns:
            Tuple of (updated_context, next_state)
        """
        self._log_state_entry(context)
        
        parsing_config = context.config.parsing_config
        if not parsing_config or not context.metadata:
            self.logger.warning("No parsing config or metadata, skipping parsing")
            next_state = self._determine_next_state(context)
            return context, next_state
        
        start_time = datetime.now()
        stats_collector = ParsingStatisticsCollector()
        parsed_files = []
        
        # ---- Apply batch splitting if configured ----
        metadata = dict(context.metadata)  # mutable copy
        # Filter to only requested release years (supports _mc suffix convention)
        if parsing_config.release_years:
            metadata = {k: v for k, v in metadata.items()
                        if k in parsing_config.release_years}
            self.logger.info(
                f"Filtered metadata to release_years={parsing_config.release_years}: "
                f"{list(metadata.keys())}"
            )
        batch_idx = context.config.batch_job_index
        total_batches = context.config.total_batch_jobs
        
        if batch_idx is not None and total_batches is not None:
            self.logger.info(
                f"Batch mode: job {batch_idx}/{total_batches}"
            )
            metadata = get_batch_slice_by_year(metadata, batch_idx, total_batches)
        
        # ---- Apply max_files_to_process limit (per year) ----
        max_files = getattr(parsing_config, 'max_files_to_process', None)
        if max_files and max_files > 0:
            for year in metadata:
                original = len(metadata[year])
                metadata[year] = metadata[year][:max_files]
                if original > max_files:
                    self.logger.info(
                        f"Limiting {year} to {max_files} files "
                        f"(was {original}, max_files_to_process={max_files})"
                    )
        
        # ---- Per-trigger-stream selection + cross-record de-duplication setup ----
        # selection_by_record maps a record id (str) to a profile with its own
        # particle_counts. Records not listed use the global particle_counts.
        sel_by_record = {
            str(k): v for k, v in (parsing_config.selection_by_record or {}).items()
        }
        # De-duplication is only meaningful (and only switched on) when multiple
        # trigger streams are combined, i.e. when selection_by_record is present.
        deduplicator = EventDeduplicator() if sel_by_record else None
        # Process the muon-requirement records first so that, for an event that
        # fired both triggers, the SingleMuon copy is the one kept and the
        # SingleElectron copy is dropped.
        ordered_metadata = sorted(
            metadata.items(),
            key=lambda kv: 0 if _profile_requires_muon(
                sel_by_record.get(_record_key_from_release_year(kv[0]), {})
            ) else 1,
        )
        # release_year -> [events_in, events_kept] for a per-record retention report
        retention: dict[str, list[int]] = {}

        # Parse each release year
        for release_year, file_urls in ordered_metadata:
            # ── Skip MC keys when parse_mc=False ─────────────────────────────────────
            # The fetcher always separates data and MC into separate keys (e.g.
            # '2024r-pp' and '2024r-pp_mc'). parse_mc controls whether MC is
            # included in the parsing run, not whether it is separated.
            if release_year.endswith("_mc") and not parsing_config.parse_mc:
                self.logger.info(f"Skipping MC key '{release_year}' (parse_mc=False)")
                continue

            record_key = _record_key_from_release_year(release_year)
            record_profile = sel_by_record.get(record_key)
            record_particle_counts = (
                (record_profile or {}).get("particle_counts")
                or parsing_config.particle_counts
            )
            retention.setdefault(release_year, [0, 0])
            if record_profile is not None:
                self.logger.info(
                    f"Record {record_key}: per-stream selection "
                    f"(particle_counts={record_particle_counts})"
                )

            self.logger.info(
                f"Parsing {len(file_urls)} files for release year: {release_year}"
            )
            
            # Define callbacks
            def on_success(file_url: str, event_count: int, time_sec: float):
                stats_collector.record_success(file_url, event_count, 0, time_sec)
            
            def on_error(file_url: str, error: Exception):
                stats_collector.record_failure(file_url, error)
            
            # Process files
            for batch in self.processor.process_files(
                file_urls=file_urls,
                tree_names=list(parsing_config.possible_data_tree_names),
                release_year=release_year,
                batch_size=40_000,
                enable_jet_tagging=parsing_config.enable_jet_tagging,
                jet_btagging_thresholds=parsing_config.jet_btagging_thresholds,
                on_success=on_success,
                on_error=on_error
            ):
                retention[release_year][0] += len(batch.events)

                if parsing_config.kinematic_cuts or record_particle_counts:
                    working_events = apply_parsing_event_selection(
                        batch.events,
                        particle_counts=record_particle_counts,
                        kinematic_cuts=parsing_config.kinematic_cuts,
                    )
                else:
                    working_events = batch.events

                if deduplicator is not None:
                    working_events, n_dropped = deduplicator.filter_new(working_events)
                    if n_dropped:
                        self.logger.info(
                            f"  {release_year}: dropped {n_dropped} duplicate event(s) "
                            f"already seen in a higher-priority trigger stream"
                        )

                retention[release_year][1] += len(working_events)

                if working_events is not batch.events:
                    batch = EventBatch(
                        events=working_events,
                        file_id=batch.file_id,
                        release_year=batch.release_year,
                        size_bytes=(
                            working_events.layout.nbytes
                            if hasattr(working_events, "layout")
                            else batch.size_bytes
                        ),
                        event_count=len(working_events),
                        processing_time_sec=batch.processing_time_sec,
                    )

                # Accumulate batch into chunks
                chunk = self.accumulator.add_batch(batch)
                
                if chunk:
                    # Save chunk to disk as ROOT file
                    output_dir = Path(parsing_config.output_path)
                    output_dir.mkdir(parents=True, exist_ok=True)
                    
                    batch_suffix = f"_batch{batch_idx}" if batch_idx is not None else ""
                    file_name = f"parsed_{release_year}{batch_suffix}_chunk{chunk.chunk_index}.root"
                    file_path = output_dir / file_name
                    
                    # Save the awkward array to ROOT file
                    self._save_chunk_to_root(chunk, str(file_path))
                    parsed_files.append(str(file_path))
                    
                    self.logger.info(
                        f"Saved chunk {chunk.chunk_index}: "
                        f"{chunk.event_count} events, {chunk.size_mb:.1f} MB → {file_path}"
                    )
                    del chunk
                    gc.collect()
        
        # Flush remaining events
        final_chunk = self.accumulator.flush()
        if final_chunk:
            # Save final chunk to disk
            output_dir = Path(parsing_config.output_path)
            output_dir.mkdir(parents=True, exist_ok=True)
            
            batch_suffix = f"_batch{batch_idx}" if batch_idx is not None else ""
            file_name = f"parsed_{final_chunk.release_year}{batch_suffix}_final.root"
            file_path = output_dir / file_name
            
            # Save the awkward array to ROOT file
            self._save_chunk_to_root(final_chunk, str(file_path))
            parsed_files.append(str(file_path))
            
            self.logger.info(
                f"Saved final chunk: {final_chunk.event_count} events, {final_chunk.size_mb:.1f} MB → {file_path}"
            )
            del final_chunk;
            gc.collect()

        # ---- Per-record retention report (events surviving selection + dedup) ----
        for ry, (n_in, n_kept) in retention.items():
            if n_in == 0:
                continue
            pct = 100.0 * n_kept / n_in
            self.logger.info(
                f"Retention {ry}: {n_kept:,} / {n_in:,} events kept ({pct:.1f}%)"
            )
        if deduplicator is not None:
            self.logger.info(deduplicator.summary())

        # Create parsing statistics
        end_time = datetime.now()
        stats_summary = stats_collector.get_summary()
        
        parsing_stats = ParsingStatistics(
            total_files=stats_summary["total_files"],
            successful_files=stats_summary["successful_files"],
            failed_files=stats_summary["failed_files"],
            total_events=stats_summary["total_events"],
            total_chunks=len(parsed_files),
            total_size_bytes=int(stats_summary["total_size_mb"] * 1024 * 1024),
            max_chunk_size_bytes=parsing_config.chunk_yield_threshold_bytes,
            min_chunk_size_bytes=0,  # TODO: track min chunk size
            max_memory_mb=0.0,  # TODO: track memory
            total_time_sec=(end_time - start_time).total_seconds(),
            start_time=start_time,
            end_time=end_time
        )
        
        self.logger.info(
            f"Parsing complete: {parsing_stats.successful_files}/{parsing_stats.total_files} files, "
            f"{parsing_stats.total_events} events, {parsing_stats.success_rate:.1f}% success rate"
        )
        
        # Update context
        updated_context = context.with_parsed_files(parsed_files).with_parsing_stats(parsing_stats)
        
        # Determine next state
        next_state = self._determine_next_state(updated_context)
        
        self._log_state_exit(context, next_state)
        return updated_context, next_state
