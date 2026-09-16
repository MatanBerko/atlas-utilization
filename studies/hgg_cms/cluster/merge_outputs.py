#!/usr/bin/env python
"""
Implementation task 6, Part E (full-run version): merge per-job H->gamma-
gamma outputs, WITH file-identity checks.

Two modes, matching the two PBS job layouts:

  --mode data   : one job PER INPUT FILE (pbs_hgg_data_array.sh), array
                  indices 1..N under --jobs-base (job_<i>/). For each
                  present job, this reconstructs EXACTLY WHICH CERN file
                  that job processed by loading THAT JOB'S OWN
                  <job_dir>/metadata_cache.json (the file-list snapshot it
                  actually fetched and cached -- see
                  utils/paths.py:update_config_paths_with_run_dir) and
                  slicing it with the real, imported
                  utils.batching.get_batch_slice_by_year at its own array
                  index, against --total-batches (the FIXED total the real
                  PBS array job always uses -- TOTAL_FILES=133 in
                  pbs_hgg_data_array.sh -- independent of how many of those
                  133 indices actually have a job directory to merge; see
                  --total-batches's own help).

                  job_metadata.json's own "input_files_processed" is NEVER
                  used for this -- it lists the pipeline's intermediate
                  PARSED chunk file (e.g. parsed_record_67611_final.root),
                  not the original CERN URL (verified on the cluster; see
                  this task's own notes). Likewise parsing statistics
                  JSONs and job logs do not record input file names for
                  data (read_event_weights=False for every H->gamma-gamma
                  data config, so the pipeline's own sumw_by_record/
                  processed_files bookkeeping -- which DOES carry real
                  URLs -- is only ever populated for simulation).

  --mode signal : one job PER RECORD (pbs_hgg_signal.sh), each with its
                  own run directory (no batching -- one job processes
                  every file of its record). Unlike data, a signal job's
                  own <run-dir>/logs/parsing_stats.json's
                  "sumw_by_record"."record_<id>"."processed_files" DOES
                  carry the real CERN URLs of every file that ACTUALLY
                  succeeded at Events-tree parsing (populated by
                  services/parsing/mc_weights.py's
                  aggregate_sumw_for_processed_files, called only because
                  read_event_weights=True for every H->gamma-gamma signal
                  config) -- so the signal identity check compares that
                  real URL list directly against the frozen expected list
                  in studies/hgg_cms/impl_checks/mapping_check/
                  cms_hgg_signal_file_lists.json, not just a count.

Both modes normalize every URL (root:// vs https://, different
redirector hostnames) down to its "/eos/opendata/..." path before
comparing, so scheme/host differences never register as a mismatch.

Either mode REFUSES to mark the merge "COMPLETE" if:
  - any expected file was processed more than once (lists exactly which
    job(s)/index(es) each duplicate came from),
  - any expected file from the frozen list never appears,
  - any unexpected (not-in-the-frozen-list) file appears,
  - a per-record summed event/file count does not match the independently
    -sourced expectation (data: portal-published raw event totals in
    mapping_check/records.json; signal: the frozen file count / the
    pipeline's own reported n_files_failed),
UNLESS --force is passed -- in which case the summary is written but
explicitly stamped "COMPLETE_FORCED_WITH_MISSING" (never silently
"COMPLETE"). Exit code is 1 whenever the merge is not COMPLETE and not
forced, so a calling script can detect this without parsing JSON.

Every category above (duplicates, missing, unexpected, mismatches) is
ALWAYS reported explicitly in the summary JSON, even when empty -- never
omitted just because there was nothing to report.

Merged ROOT output (unless --no-merge-root): reads every job's own
"normal" (never the BLINDED_SIGNAL_REGION-named) selected-event ROOT
file(s) through studies.hgg_cms.output.read_output(unblind=False) --
which independently RE-ASSERTS, on every file, that no data event with
115 <= m_gg <= 135 GeV is present (this task's blinding invariant, not
just trusted from the filename) -- concatenates them with
awkward.concatenate, and writes ONE merged file per mode/record. No
merged file containing individual blinded events is ever produced by this
script; only the blinded COUNT is reported (in the summary and, for data,
in the merged metadata JSON) -- see --mode data's "n_written_blinded"
totals.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

from utils.batching import get_batch_slice_by_year  # noqa: E402

MAPPING_CHECK_DIR = REPO_ROOT / "studies" / "hgg_cms" / "impl_checks" / "mapping_check"
DATA_EXPECTED_JSON = MAPPING_CHECK_DIR / "cms_hgg_data_file_lists.json"
SIGNAL_EXPECTED_JSON = MAPPING_CHECK_DIR / "cms_hgg_signal_file_lists.json"
RECORDS_JSON = MAPPING_CHECK_DIR / "records.json"
SIGNAL_SUMW_JSON = REPO_ROOT / "studies" / "hgg_cms" / "impl_checks" / "signal_sumw.json"

# label -> CMS Open Data record id, for the 6 H->gamma-gamma signal
# production modes (studies/hgg_cms/cluster/submit_full.sh's own
# SIGNAL_CONFIGS / signal_sumw.json's "records" keys).
SIGNAL_LABEL_TO_RECORD = {
    "ggh": "37350",
    "vbf": "68497",
    "wplush": "71013",
    "wminush": "70173",
    "zh": "74132",
    "tth": "67611",
}

DATA_TOTAL_BATCHES_DEFAULT = 133

DATA_CUTFLOW_KEYS = [
    "n_input_events", "n_with_ge2_tm_photons", "n_selected",
    "n_written_normal", "n_written_blinded_signal_region",
]
SIGNAL_CUTFLOW_KEYS = DATA_CUTFLOW_KEYS + [
    "sum_genWeight_input", "sum_genWeight_selected",
]

_EOS_PATH_RE = re.compile(r"(/eos/opendata/.*)$")


def normalize_url(url: str) -> str:
    """Collapses root://<host>/<path> and https://<host>/<path> (any
    redirector/hostname) down to just the '/eos/opendata/...' path, so
    the two schemes/hosts a real job and this frozen list might use never
    register as a mismatch just because of that difference."""
    m = _EOS_PATH_RE.search(url)
    return m.group(1) if m else url


def _load_json(path: Path):
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


# ---------------------------------------------------------------------------
# DATA
# ---------------------------------------------------------------------------

def discover_job_indices(jobs_base: Path) -> list:
    indices = []
    if not jobs_base.exists():
        return indices
    for d in jobs_base.iterdir():
        m = re.fullmatch(r"job_(\d+)", d.name)
        if d.is_dir() and m:
            indices.append(int(m.group(1)))
    return sorted(indices)


def reconstruct_data_job_file(job_dir: Path, index: int, total_batches: int):
    """Returns (record_key, url, error). Uses THIS job's own
    metadata_cache.json (see module docstring) -- never job_metadata.json's
    input_files_processed."""
    cache = _load_json(job_dir / "metadata_cache.json")
    if cache is None:
        return None, None, "missing or unreadable metadata_cache.json"
    try:
        sliced = get_batch_slice_by_year(cache, index, total_batches)
    except Exception as e:  # noqa: BLE001 -- report, don't crash the merge
        return None, None, f"get_batch_slice_by_year raised {type(e).__name__}: {e}"
    n = sum(len(v) for v in sliced.values())
    if n != 1:
        return None, None, f"batching gave {n} file(s) for this index, expected exactly 1"
    (record_key, urls), = sliced.items()
    return record_key, urls[0], None


def _expected_data_urls():
    raw = _load_json(DATA_EXPECTED_JSON)
    if raw is None:
        raise FileNotFoundError(f"expected data file list not found: {DATA_EXPECTED_JSON}")
    return {k: [normalize_url(u) for u in v] for k, v in raw.items()}


def _portal_event_counts():
    raw = _load_json(RECORDS_JSON)
    if raw is None:
        raise FileNotFoundError(f"portal record event counts not found: {RECORDS_JSON}")
    return raw["records"]


def merge_data(jobs_base: Path, total_batches: int, out_path: Path, force: bool,
                merged_dir: Path | None) -> int:
    expected = _expected_data_urls()  # {"record_30521": [urls], "record_30554": [urls]}
    portal_counts = _portal_event_counts()  # {"30521": {"number_events": ...}, ...}

    present_indices = discover_job_indices(jobs_base)
    expected_total_files = sum(len(v) for v in expected.values())

    missing_jobs = []  # index -> no job_dir / no metadata_cache / no job_metadata
    identity_errors = []  # index -> couldn't reconstruct exactly one file
    assigned_by_url = {}  # normalized url -> [job indices that claim it]
    per_record_assigned = {k: [] for k in expected}
    per_record_event_totals = {k: 0 for k in expected}
    missing_parsing_stats = []

    total_cutflow = {k: 0 for k in DATA_CUTFLOW_KEYS}
    commit_hashes, config_hashes = set(), set()
    normal_root_files = []  # for the merged ROOT output

    for i in present_indices:
        job_dir = jobs_base / f"job_{i}"
        job_meta = _load_json(job_dir / "selected" / "job_metadata.json")
        if job_meta is None:
            missing_jobs.append(i)
            continue

        record_key, url, err = reconstruct_data_job_file(job_dir, i, total_batches)
        if err is not None:
            identity_errors.append({"index": i, "error": err})
        else:
            norm = normalize_url(url)
            assigned_by_url.setdefault(norm, []).append(i)
            per_record_assigned.setdefault(record_key, []).append(norm)

            stats_path = job_dir / "logs" / f"parsing_stats_batch_{i}.json"
            stats = _load_json(stats_path)
            if stats is None:
                missing_parsing_stats.append(i)
            else:
                per_record_event_totals[record_key] = per_record_event_totals.get(
                    record_key, 0
                ) + stats.get("total_events", 0)

        cf = job_meta.get("cutflow", {})
        for k in DATA_CUTFLOW_KEYS:
            total_cutflow[k] += cf.get(k, 0)
        if job_meta.get("git_commit"):
            commit_hashes.add(job_meta["git_commit"])
        if job_meta.get("config_sha256"):
            config_hashes.add(job_meta["config_sha256"])

        sel_dir = job_dir / "selected"
        if sel_dir.exists():
            for root_file in sorted(sel_dir.glob("*.root")):
                if "BLINDED_SIGNAL_REGION" not in root_file.name:
                    normal_root_files.append(root_file)

    # ---- Identity-check categories (ALWAYS reported, even if empty) ----
    duplicated = {u: idxs for u, idxs in assigned_by_url.items() if len(idxs) > 1}
    all_assigned_urls = set(assigned_by_url.keys())
    all_expected_urls = set(u for urls in expected.values() for u in urls)
    missing_files = sorted(all_expected_urls - all_assigned_urls)
    unexpected_files = sorted(all_assigned_urls - all_expected_urls)

    per_record_coverage = {}
    for record_key, exp_urls in expected.items():
        assigned = per_record_assigned.get(record_key, [])
        per_record_coverage[record_key] = {
            "n_expected": len(exp_urls),
            "n_assigned": len(assigned),
            "fully_covered": sorted(assigned) == sorted(exp_urls),
        }

    event_total_mismatches = {}
    for record_key in expected:
        record_id = record_key.replace("record_", "")
        expected_events = portal_counts.get(record_id, {}).get("number_events")
        got_events = per_record_event_totals.get(record_key, 0)
        match = (expected_events is not None) and (got_events == expected_events)
        event_total_mismatches[record_key] = {
            "expected_from_portal": expected_events,
            "summed_from_parsing_stats": got_events,
            "match": match,
        }
    total_events_match = all(v["match"] for v in event_total_mismatches.values())

    n_missing_indices = sorted(
        set(range(1, expected_total_files + 1)) - set(present_indices)
    )

    problems = (
        bool(missing_jobs) or bool(identity_errors) or bool(duplicated)
        or bool(missing_files) or bool(unexpected_files)
        or not all(v["fully_covered"] for v in per_record_coverage.values())
        or not total_events_match
        or bool(n_missing_indices)
    )
    complete = not problems
    status = "COMPLETE" if complete else ("COMPLETE_FORCED_WITH_MISSING" if force else "INCOMPLETE")

    summary = {
        "mode": "data",
        "status": status,
        "jobs_base": str(jobs_base),
        "total_batches_used_for_reconstruction": total_batches,
        "expected_total_files": expected_total_files,
        "n_job_dirs_present": len(present_indices),
        "n_array_indices_with_no_job_dir": len(n_missing_indices),
        "array_indices_with_no_job_dir": n_missing_indices,
        "missing_jobs_no_metadata": missing_jobs,
        "identity_reconstruction_errors": identity_errors,
        "duplicated_files": duplicated,
        "missing_files": missing_files,
        "unexpected_files": unexpected_files,
        "per_record_coverage": per_record_coverage,
        "per_record_event_totals_vs_portal": event_total_mismatches,
        "missing_parsing_stats_for_indices": missing_parsing_stats,
        "git_commits_seen": sorted(commit_hashes),
        "config_sha256_seen": sorted(config_hashes),
        "total_cutflow": total_cutflow,
    }
    if len(commit_hashes) > 1:
        summary["WARNING_multiple_git_commits"] = (
            "Jobs ran against different git commits -- results may not be "
            "directly comparable/mergeable."
        )
    if len(config_hashes) > 1:
        summary["WARNING_multiple_configs"] = (
            "Jobs ran with different config file contents (sha256 differs) "
            "-- results may not be directly comparable/mergeable."
        )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    _print_summary(summary)

    if merged_dir is not None and (complete or force):
        merged_dir.mkdir(parents=True, exist_ok=True)
        n_merged = _write_merged_data_root(normal_root_files, merged_dir / "data_sidebands.root")
        merged_meta = {
            "status": status,
            "n_input_root_files_merged": len(normal_root_files),
            "n_events_in_merged_file": n_merged,
            "total_cutflow": total_cutflow,
            "n_written_normal_total": total_cutflow["n_written_normal"],
            "n_written_blinded_signal_region_total": total_cutflow["n_written_blinded_signal_region"],
            "note": (
                "BLINDED events are counted here (n_written_blinded_signal_region_total) "
                "and NEVER merged into data_sidebands.root or any other file this "
                "script writes -- only the sideband/normal events are merged."
            ),
        }
        (merged_dir / "data_merge_metadata.json").write_text(
            json.dumps(merged_meta, indent=2), encoding="utf-8"
        )
        print(f"\nwrote {merged_dir / 'data_sidebands.root'} ({n_merged} events) "
              f"and {merged_dir / 'data_merge_metadata.json'}")

    return 0 if status != "INCOMPLETE" else 1


# ---------------------------------------------------------------------------
# SIGNAL
# ---------------------------------------------------------------------------

def _expected_signal_urls():
    raw = _load_json(SIGNAL_EXPECTED_JSON)
    if raw is None:
        raise FileNotFoundError(f"expected signal file list not found: {SIGNAL_EXPECTED_JSON}")
    return {k: [normalize_url(u) for u in v] for k, v in raw.items()}


def merge_signal(records: dict, out_path: Path, force: bool, merged_dir: Path | None) -> int:
    """`records`: {label: run_dir_str}, e.g. {"ggh": ".../signal/ggh", ...}."""
    expected = _expected_signal_urls()  # {"record_37350": [urls], ...}
    sumw_table = json.loads(SIGNAL_SUMW_JSON.read_text(encoding="utf-8"))["records"]

    missing_records = []
    per_record = {}
    any_problem = False

    for label, job_dir_str in records.items():
        job_dir = Path(job_dir_str)
        record_id = SIGNAL_LABEL_TO_RECORD.get(label)
        record_key = f"record_{record_id}" if record_id else None

        parsing_stats = _load_json(job_dir / "logs" / "parsing_stats.json")
        sel_meta = _load_json(job_dir / "selected" / "job_metadata.json")

        if parsing_stats is None or sel_meta is None or record_key is None:
            missing_records.append(label)
            any_problem = True
            continue

        sw = (parsing_stats.get("sumw_by_record") or {}).get(record_key)
        exp_urls = expected.get(record_key, [])
        expected_n_files = len(exp_urls)

        if sw is None:
            per_record[label] = {
                "record": record_id,
                "PROBLEM": "no sumw_by_record entry for this record in parsing_stats.json "
                           "(read_event_weights must be true for every H->gamma-gamma "
                           "signal config -- check the config actually used)",
            }
            any_problem = True
            continue

        processed_urls = [normalize_url(u) for u in sw.get("processed_files", [])]
        n_processed = sw.get("n_files_processed", len(processed_urls))
        n_failed = sw.get("n_files_failed", 0)
        genEventSumw = sw.get("genEventSumw")
        genEventCount = sw.get("genEventCount")

        got_set = set(processed_urls)
        exp_set = set(exp_urls)
        dup_check = {}
        for u in processed_urls:
            dup_check[u] = dup_check.get(u, 0) + 1
        duplicated = {u: c for u, c in dup_check.items() if c > 1}
        missing_files = sorted(exp_set - got_set)
        unexpected_files = sorted(got_set - exp_set)

        record_ok = (
            n_failed == 0
            and n_processed == expected_n_files
            and not duplicated
            and not missing_files
            and not unexpected_files
        )
        if not record_ok:
            any_problem = True

        sel_cutflow = sel_meta.get("cutflow", {})
        cross_section_pb = sumw_table.get(record_id, {}).get("cross_section_pb")
        br = sumw_table.get(record_id, {}).get("branching_ratio_Hgammagamma")
        sum_gw_sel = sel_cutflow.get("sum_genWeight_selected")

        expected_yield_note = None
        if genEventSumw and sum_gw_sel is not None:
            expected_yield_note = (
                "Combine as: cross_section_pb * 1000 (pb->fb) * "
                "branching_ratio_Hgammagamma * L_fb * "
                "(selection_cutflow.sum_genWeight_selected / genEventSumw_over_processed_files) "
                "-- L_fb (16.393380531 for the Run2016 legacy dataset) is not hardcoded here. "
                "For ttH (record 67611) use ONLY this run's own genEventSumw_over_processed_files "
                "(over the current 15-file portal list) -- NEVER signal_sumw.json's stale "
                "16-file total; for ZH (record 74132) use cross_section_pb=0.7612 "
                "(qq/qg->ZH only -- see signal_sumw_notes.md), not signal_sumw.json's "
                "recorded 0.8839 pb (qq+gg total)."
            )

        per_record[label] = {
            "record": record_id,
            "record_ok": record_ok,
            "expected_n_files": expected_n_files,
            "n_files_processed": n_processed,
            "n_files_failed": n_failed,
            "duplicated_files": duplicated,
            "missing_files": missing_files,
            "unexpected_files": unexpected_files,
            "genEventSumw_over_processed_files": genEventSumw,
            "genEventCount_over_processed_files": genEventCount,
            "genEventSumw2_over_processed_files": sw.get("genEventSumw2"),
            "cross_section_pb": cross_section_pb,
            "branching_ratio_Hgammagamma": br,
            "selection_cutflow": sel_cutflow,
            "dedup_removed_simulation_events": sel_cutflow.get("dedup_removed_simulation_events"),
            "how_to_combine_into_expected_yield": expected_yield_note,
        }

        if merged_dir is not None:
            sel_dir = job_dir / "selected"
            root_files = sorted(sel_dir.glob("*.root")) if sel_dir.exists() else []
            merged_dir.mkdir(parents=True, exist_ok=True)
            n_merged = _write_merged_data_root(root_files, merged_dir / f"signal_{label}.root")
            per_record[label]["n_events_in_merged_file"] = n_merged
            per_record[label]["n_input_root_files_merged"] = len(root_files)

    complete = (not missing_records) and (not any_problem)
    status = "COMPLETE" if complete else ("COMPLETE_FORCED_WITH_MISSING" if force else "INCOMPLETE")

    summary = {
        "mode": "signal",
        "status": status,
        "records_expected": sorted(records.keys()),
        "missing_records": missing_records,
        "per_record": per_record,
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    _print_summary(summary)
    return 0 if status != "INCOMPLETE" else 1


# ---------------------------------------------------------------------------
# Merged-ROOT helper (shared by data + signal)
# ---------------------------------------------------------------------------

def _write_merged_data_root(root_files: list, out_path: Path) -> int:
    """Reads every file in `root_files` through
    studies.hgg_cms.output.read_output(unblind=False) (which asserts, on
    EVERY file, that no data event with 115<=m_gg<=135 is present --
    regardless of filename), concatenates, and writes one merged ROOT
    file. Returns the number of events written. Writes nothing (returns 0)
    if `root_files` is empty."""
    if not root_files:
        return 0
    import awkward as ak
    import uproot
    from studies.hgg_cms.output import read_output

    arrays = [read_output(p, unblind=False) for p in root_files]
    merged = ak.concatenate(arrays) if len(arrays) > 1 else arrays[0]
    packed = ak.to_packed(merged)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with uproot.recreate(str(out_path)) as f:
        f["events"] = {field: packed[field] for field in packed.fields}
    return len(packed)


def _print_summary(summary: dict) -> None:
    print(json.dumps(summary, indent=2))
    if summary["status"] == "COMPLETE":
        print(f"\nAll expected outputs present and verified. status = COMPLETE")
    else:
        print(f"\n{'!' * 70}\nMERGE NOT CLEAN: status = {summary['status']}\n{'!' * 70}")


# ---------------------------------------------------------------------------
# Fast helper mode for status_full.sh: print every data job's reconstructed
# input file in one process (avoids 133 separate python startups).
# ---------------------------------------------------------------------------

def print_data_job_files(jobs_base: Path, total_batches: int) -> None:
    for i in discover_job_indices(jobs_base):
        job_dir = jobs_base / f"job_{i}"
        record_key, url, err = reconstruct_data_job_file(job_dir, i, total_batches)
        if err is not None:
            print(f"{i}\tERROR\t{err}")
        else:
            print(f"{i}\t{record_key}\t{normalize_url(url)}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--mode", choices=["data", "signal"])
    p.add_argument("--out", default=None)
    p.add_argument("--force", action="store_true",
                    help="Write status=COMPLETE_FORCED_WITH_MISSING instead of "
                         "refusing COMPLETE when something is missing.")
    p.add_argument("--merged-dir", default=None,
                    help="If given, also write merged ROOT output(s) + merged "
                         "metadata here. Only written when the merge is "
                         "COMPLETE (or --force).")
    p.add_argument("--no-merge-root", action="store_true",
                    help="Skip writing merged ROOT output even if --merged-dir "
                         "is given (identity checks + summary JSON only).")
    # data mode
    p.add_argument("--jobs-base", default=None)
    p.add_argument("--total-batches", type=int, default=DATA_TOTAL_BATCHES_DEFAULT,
                    help="The FIXED total batch count the real PBS array job "
                         "used (TOTAL_FILES in pbs_hgg_data_array.sh, 133 for "
                         "every H->gamma-gamma data submission so far -- pilot "
                         "included, since the pilot only submits array indices "
                         "1-2 of that SAME 133-way split, not a separate "
                         "2-way one). Only override this if a future run "
                         "genuinely changes TOTAL_FILES.")
    # signal mode
    p.add_argument("--record", action="append", default=[],
                    metavar="LABEL=RUN_DIR",
                    help="Repeatable. e.g. --record ggh=/storage/.../signal/ggh "
                         "(LABEL must be one of: "
                         + ", ".join(SIGNAL_LABEL_TO_RECORD) + ")")
    # helper mode
    p.add_argument("--print-data-job-files", action="store_true",
                    help="Print '<index>\\t<record_key>\\t<url>' (or "
                         "'<index>\\tERROR\\t<message>') for every job_<i> "
                         "directory under --jobs-base, then exit. For "
                         "status_full.sh's use -- no --mode/--out needed.")
    args = p.parse_args()

    if args.print_data_job_files:
        if not args.jobs_base:
            p.error("--print-data-job-files requires --jobs-base")
        print_data_job_files(Path(args.jobs_base), args.total_batches)
        sys.exit(0)

    if not args.mode or not args.out:
        p.error("--mode and --out are required (unless --print-data-job-files)")

    out_path = Path(args.out)
    merged_dir = None
    if args.merged_dir and not args.no_merge_root:
        merged_dir = Path(args.merged_dir)

    if args.mode == "data":
        if not args.jobs_base:
            p.error("--mode data requires --jobs-base")
        rc = merge_data(Path(args.jobs_base), args.total_batches, out_path, args.force, merged_dir)
    else:
        if not args.record:
            p.error("--mode signal requires at least one --record LABEL=RUN_DIR")
        records = {}
        for entry in args.record:
            label, _, job_dir = entry.partition("=")
            if not label or not job_dir:
                p.error(f"bad --record value: {entry!r} (expected LABEL=RUN_DIR)")
            if label not in SIGNAL_LABEL_TO_RECORD:
                p.error(f"unknown signal label {label!r}, expected one of "
                         + ", ".join(SIGNAL_LABEL_TO_RECORD))
            records[label] = job_dir
        rc = merge_signal(records, out_path, args.force, merged_dir)

    sys.exit(rc)


if __name__ == "__main__":
    main()
