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
from services.parsing.schemas import normalize_release_year
from services.parsing.validated_runs import ValidatedRunsFilter, apply_validated_runs_filter
from services.parsing.trigger_requirements import (
    apply_trigger_requirement,
    trigger_group_branches,
    validate_trigger_requirements,
)
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


def select_metadata_for_parsing(
    metadata: dict[str, list[str]],
    release_years,
    parse_mc: bool,
) -> dict[str, list[str]]:
    """Select exactly the requested ATLAS dataset mode from cached metadata.

    ATLAS metadata is stored under paired keys such as ``2024r-pp`` for data
    and ``2024r-pp_mc`` for Monte Carlo. ``parse_mc`` selects one member of
    each pair; it does not mean that data and MC should be parsed together.
    """
    requested_releases = list(release_years or [])
    if requested_releases:
        selected_keys = set()
        for release in requested_releases:
            if release.startswith("record_"):
                selected_keys.add(release)
                continue
            base_release = release[:-3] if release.endswith("_mc") else release
            selected_keys.add(f"{base_release}_mc" if parse_mc else base_release)

        missing_keys = sorted(
            key for key in selected_keys if not metadata.get(key)
        )
        if missing_keys:
            mode = "MC" if parse_mc else "data"
            raise RuntimeError(
                f"No {mode} metadata found for requested release key(s): "
                f"{missing_keys}. Available keys: {sorted(metadata)}"
            )
        return {
            key: urls for key, urls in metadata.items() if key in selected_keys
        }

    # Explicit record IDs are not paired ATLAS release keys, so parse_mc does
    # not alter their selection. For ATLAS releases, retain exactly one mode.
    return {
        key: urls
        for key, urls in metadata.items()
        if key.startswith("record_") or key.endswith("_mc") == parse_mc
    }


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

        # ---- Validated-runs ("golden JSON") filter: loaded once per run ----
        # Absent (the default, and every current config) -> validated_runs is
        # None and the filter below is a complete no-op. See
        # services/parsing/validated_runs.py and
        # data/cms/validated_runs/README.md.
        validated_runs = None
        if parsing_config.validated_runs_json:
            validated_runs = ValidatedRunsFilter(parsing_config.validated_runs_json)
            self.logger.info(
                f"Validated-runs filter enabled: {validated_runs.source_path} "
                f"(sha256={validated_runs.sha256}, {validated_runs.n_runs} runs, "
                f"{validated_runs.n_certified_lumisections} certified lumisections)"
            )
        # release_year -> {run: {"before": n, "after": n}}, accumulated across
        # every file/batch of that release, for the per-run retention report.
        validated_runs_report: dict[str, dict[int, dict[str, int]]] = {}

        # release_year -> {"n_before": n, "n_after": n, "per_path": {path: n_passed}},
        # accumulated across every batch, for the HLT trigger requirement report.
        # Populated only for release years where trigger_requirements (global
        # or per-record) is actually configured.
        trigger_report: dict[str, dict] = {}

        # ---- Apply batch splitting if configured ----
        metadata = dict(context.metadata)  # mutable copy
        metadata = select_metadata_for_parsing(
            metadata,
            parsing_config.release_years,
            parsing_config.parse_mc,
        )
        self.logger.info(
            "Selected %s metadata for release_years=%s: %s",
            "MC" if parsing_config.parse_mc else "data",
            parsing_config.release_years,
            list(metadata.keys()),
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
        # release_year -> [files_opened_ok, files_failed_to_open]
        file_counts: dict[str, list[int]] = {}
        # Above this fraction of a record's files failing to open, treat it as a
        # real failure rather than silently continuing with whatever (possibly
        # zero) events the surviving files produced -- see MAX_FILE_FAILURE_RATE.
        MAX_FILE_FAILURE_RATE = 0.20

        # Parse each release year
        for release_year, file_urls in ordered_metadata:
            # MC-vs-data selection already happened above (metadata = selected);
            # no per-record "skip MC keys" check needed here any more.
            record_key = _record_key_from_release_year(release_year)
            record_profile = sel_by_record.get(record_key)
            record_particle_counts = (
                (record_profile or {}).get("particle_counts")
                or parsing_config.particle_counts
            )
            # Per-record HLT trigger requirement override, same shape as the
            # global parsing_task_config.trigger_requirements key, mirroring
            # the particle_counts override pattern just above. Unlike the
            # global key (validated in ParsingConfig.__post_init__),
            # selection_by_record profiles are freeform dicts not covered by
            # that validation, so a per-record override is validated here.
            record_trigger_requirements = (
                (record_profile or {}).get("trigger_requirements")
                or parsing_config.trigger_requirements
            )
            if record_trigger_requirements:
                validate_trigger_requirements(record_trigger_requirements)

            # The "Trigger" scalar branch group is only added when a trigger
            # requirement is actually configured (global or per-record) --
            # extra_scalar_branches stays byte-identical to
            # parsing_config.extra_scalar_branches (including being the same
            # None when both are unset) for every existing configuration.
            effective_extra_scalar_branches = parsing_config.extra_scalar_branches
            if record_trigger_requirements:
                merged = dict(effective_extra_scalar_branches or {})
                trigger_paths = trigger_group_branches(record_trigger_requirements)
                merged["Trigger"] = list(dict.fromkeys(
                    list(merged.get("Trigger", [])) + trigger_paths
                ))
                effective_extra_scalar_branches = merged

            retention.setdefault(release_year, [0, 0])
            file_counts.setdefault(release_year, [0, 0])
            if record_profile is not None:
                self.logger.info(
                    f"Record {record_key}: per-stream selection "
                    f"(particle_counts={record_particle_counts})"
                )
            if record_trigger_requirements:
                self.logger.info(
                    f"Record {record_key}: HLT trigger requirement enabled "
                    f"(mode={record_trigger_requirements.get('mode', 'any')}, "
                    f"paths={trigger_group_branches(record_trigger_requirements)})"
                )

            self.logger.info(
                f"Parsing {len(file_urls)} files for release year: {release_year}"
            )

            # Define callbacks
            def on_success(file_url: str, event_count: int, time_sec: float):
                stats_collector.record_success(file_url, event_count, 0, time_sec)
                file_counts[release_year][0] += 1

            def on_error(file_url: str, error: Exception):
                stats_collector.record_failure(file_url, error)
                file_counts[release_year][1] += 1

            # Process files
            for batch in self.processor.process_files(
                file_urls=file_urls,
                tree_names=list(parsing_config.possible_data_tree_names),
                release_year=release_year,
                batch_size=40_000,
                enable_jet_tagging=parsing_config.enable_jet_tagging,
                jet_btagging_thresholds=parsing_config.jet_btagging_thresholds,
                extra_scalar_branches=effective_extra_scalar_branches,
                extra_object_fields=parsing_config.extra_object_fields,
                on_success=on_success,
                on_error=on_error
            ):
                retention[release_year][0] += len(batch.events)

                working_events = batch.events

                # Validated-runs filter runs BEFORE any kinematic/particle-
                # count selection and BEFORE de-duplication, so an event
                # rejected here is never counted as "selected" by either of
                # those later stages, and dedup's (run, luminosityBlock,
                # event) keys are only ever built from certified events.
                if validated_runs is not None:
                    working_events, vr_stats = apply_validated_runs_filter(working_events, validated_runs)
                    per_run = validated_runs_report.setdefault(release_year, {})
                    for run, counts in vr_stats["per_run"].items():
                        entry = per_run.setdefault(run, {"before": 0, "after": 0})
                        entry["before"] += counts["before"]
                        entry["after"] += counts["after"]
                    if vr_stats["n_before"] != vr_stats["n_after"]:
                        self.logger.info(
                            f"  {release_year}: validated-runs filter kept "
                            f"{vr_stats['n_after']:,}/{vr_stats['n_before']:,} events in this batch"
                        )

                # HLT trigger requirement runs AFTER the validated-runs
                # filter and BEFORE particle/kinematic selection and
                # de-duplication -- same reasoning as the validated-runs
                # filter above (dedup's (run, luminosityBlock, event) keys
                # must only ever be built from events that also pass the
                # trigger requirement). Applies to data AND simulation
                # (no simulation guard, unlike validated-runs).
                if record_trigger_requirements:
                    working_events, tr_stats = apply_trigger_requirement(
                        working_events, record_trigger_requirements
                    )
                    tr_report = trigger_report.setdefault(
                        release_year, {"n_before": 0, "n_after": 0, "per_path": {}}
                    )
                    tr_report["n_before"] += tr_stats["n_before"]
                    tr_report["n_after"] += tr_stats["n_after"]
                    for path, n_passed in tr_stats["per_path"].items():
                        tr_report["per_path"][path] = tr_report["per_path"].get(path, 0) + n_passed
                    if tr_stats["n_before"] != tr_stats["n_after"]:
                        self.logger.info(
                            f"  {release_year}: trigger requirement kept "
                            f"{tr_stats['n_after']:,}/{tr_stats['n_before']:,} events in this batch"
                        )

                if parsing_config.kinematic_cuts or record_particle_counts:
                    working_events = apply_parsing_event_selection(
                        working_events,
                        particle_counts=record_particle_counts,
                        kinematic_cuts=parsing_config.kinematic_cuts,
                    )

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

            # ---- Fail loudly instead of silently continuing with zero events ----
            # A record whose files mostly fail to open (network blip, bad
            # redirector, exhausted connection pool, ...) used to finish this
            # loop with near-zero retained events and no error -- indistinguishable
            # from a record that genuinely has low yield. Abort instead.
            ok_count, fail_count = file_counts[release_year]
            total_count = ok_count + fail_count
            if total_count > 0:
                failure_rate = fail_count / total_count
                if failure_rate > MAX_FILE_FAILURE_RATE:
                    raise RuntimeError(
                        f"Record {record_key}: {fail_count}/{total_count} files failed to "
                        f"open ({failure_rate:.0%} failure rate, exceeds the "
                        f"{MAX_FILE_FAILURE_RATE:.0%} threshold). Aborting this run rather "
                        f"than silently continuing with zero or near-zero events for this "
                        f"record."
                    )

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

        # ---- Per-record file open success/failure report ----
        for ry, (ok_count, fail_count) in file_counts.items():
            total_count = ok_count + fail_count
            if total_count == 0:
                continue
            fail_pct = 100.0 * fail_count / total_count
            self.logger.info(
                f"File opens {ry}: {ok_count}/{total_count} succeeded, "
                f"{fail_count} failed ({fail_pct:.1f}% failure)"
            )

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

        # ---- Per-run validated-runs filter report ----
        if validated_runs is not None:
            for ry, per_run in validated_runs_report.items():
                total_before = sum(c["before"] for c in per_run.values())
                total_after = sum(c["after"] for c in per_run.values())
                pct = 100.0 * total_after / total_before if total_before else 0.0
                self.logger.info(
                    f"Validated-runs filter {ry}: {total_after:,} / {total_before:,} "
                    f"events kept ({pct:.1f}%) across {len(per_run)} run(s)"
                )
                for run in sorted(per_run):
                    counts = per_run[run]
                    if counts["before"] != counts["after"]:
                        self.logger.info(
                            f"  run {run}: {counts['after']:,} / {counts['before']:,} events kept"
                        )

        # ---- HLT trigger requirement report ----
        for ry, tr in trigger_report.items():
            pct = 100.0 * tr["n_after"] / tr["n_before"] if tr["n_before"] else 0.0
            self.logger.info(
                f"Trigger requirement {ry}: {tr['n_after']:,} / {tr['n_before']:,} "
                f"events kept ({pct:.1f}%)"
            )
            for path, n_passed in sorted(tr["per_path"].items()):
                self.logger.info(f"  {path}: {n_passed:,} / {tr['n_before']:,} events passed")

        # Create parsing statistics
        end_time = datetime.now()
        stats_summary = stats_collector.get_summary()

        # ---- Skipped-file failure-reason breakdown (implementation task 3,
        # Part B3 -- "count ALL skipped files and their failure reasons").
        # Purely additive: a new log line only, using a new
        # ParsingStatisticsCollector.get_summary() key computed from data
        # (file_url, exception) that was already being collected for every
        # existing configuration; does not touch parsed_files, parsing_stats,
        # or any other value written to an output file. ----
        if stats_summary["failure_reason_counts"]:
            self.logger.info(
                f"Skipped-file failure reasons: {stats_summary['failure_reason_counts']}"
            )

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
