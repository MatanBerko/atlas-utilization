#!/usr/bin/env python
"""
Dataset-parameterized BumpNet ROOT delivery builder, built directly on
studies/cms_coverage/deliver/build_bumpnet_root.py's own pattern (that
script itself is NOT edited -- it stays hardcoded to the old 57-job,
316/340-name DoubleMuon coverage run; this script imports the same shared
functions it does and serves any dataset run under
studies/cms_datasets/cluster/run_dataset_on_file.py's own output layout,
--dataset-label chosen at the command line).

Reuses, unmodified:
  - services.storage.sqlite_shards: list_signatures, iter_all_chunks
    (via merge_and_count's own load_chunks_by_signature),
    prune_final_states_below_min_events (via merge_and_count's own
    run_funnel_at_threshold).
  - studies.cms_coverage.cluster.merge_and_count: SIG_PATTERN,
    PRIMARY_MIN_EVENTS_PER_FS, MIN_BUMPNET_BINS, MIN_BUMPNET_EVENTS,
    copy_shards, run_funnel_at_threshold, object_content_category,
    object_count -- the exact same post-processing chain (z-peak cut,
    max-mass cut, peak removal, first-empty-bin split), same >=100 events,
    same >30/>25 non-empty-bin thresholds.
  - studies.m0m1j0_cms.histograms: _convert_to_bumpnet_name,
    make_fixed_grid_histogram, to_writable_th1f, verify_written_th1f --
    same fixed 10 GeV / 0-10,000 GeV grid, same TH1F writing.
  - studies.cms_coverage.deliver.crop_bumpnet_root: crop_arrays -- the
    exact same crop-to-first/last-filled-bin logic (imported directly,
    not reimplemented, so the two deliveries can never silently diverge
    in how cropping works).

Mandatory checks, each a hard STOP (non-zero exit, no partial write) on
failure:
  (a) Completeness/identity: every job index 1..N_FILES present exactly
      once, covering every (record_id, file_index) the dataset's file
      lists say should exist, with no duplicates and no gaps; sum of
      n_read across all jobs equals the dataset's real total event count
      (computed from Step 1's own per-file pre-flight scan, not assumed);
      every job ran the SAME git commit; and (Step 1's cap policy) ZERO
      CAPPED:: shard-metadata entries anywhere -- a hard stop, not a
      silent subsample, per this task's own instruction.
  (b) Funnel: stages (a)-(d), via merge_and_count's own
      run_funnel_at_threshold, unmodified.
  (c) Continuity check (only run when --old-delivery-min31/--old-delivery-min26
      are given -- meaningful only for a dataset that has a prior
      delivery to check against, e.g. DoubleMuon): every histogram in the
      given prior delivery file(s) must appear in this run's own
      stage-(c) survivors with IDENTICAL bin contents and edges. Any
      difference is reported exactly, never adjusted to force agreement.

Usage:
    python build_dataset_delivery.py --dataset-label DoubleMuon \
        --runs-dir /storage/.../output/cms_datasets/runs/DoubleMuon \
        --preflight-dir /storage/.../output/cms_datasets/preflight \
        --file-lists studies/cms_datasets/evidence/record_file_lists.json \
        --population generic --inclusive-only \
        --old-delivery-min31 /storage/.../deliver_doublemuon_bumpnet/doublemuon_bumpnet_min31bins.root \
        --old-delivery-min26 /storage/.../deliver_doublemuon_bumpnet/doublemuon_bumpnet_min26bins.root \
        --out-dir /storage/.../output/cms_datasets/deliver/DoubleMuon \
        --out-prefix doublemuon_generic
"""
from __future__ import annotations

import argparse
import glob
import json
import logging
import re
import sys
import tempfile
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

import numpy as np  # noqa: E402
import uproot  # noqa: E402

from services.storage.sqlite_shards import list_signatures  # noqa: E402
from studies.cms_coverage.cluster.merge_and_count import (  # noqa: E402
    SIG_PATTERN,
    PRIMARY_MIN_EVENTS_PER_FS,
    MIN_BUMPNET_BINS,
    MIN_BUMPNET_EVENTS,
    copy_shards,
    run_funnel_at_threshold,
    object_content_category,
    object_count,
)
from studies.cms_coverage.deliver.crop_bumpnet_root import crop_arrays  # noqa: E402
from studies.m0m1j0_cms.histograms import (  # noqa: E402
    _convert_to_bumpnet_name,
    make_fixed_grid_histogram,
    to_writable_th1f,
    verify_written_th1f,
    BIN_WIDTH_GEV,
    FIXED_MASS_MIN_GEV,
    FIXED_MASS_MAX_GEV,
)

logging.basicConfig(level=logging.WARNING, format="%(asctime)s %(levelname)s %(message)s")
LOGGER = logging.getLogger("build_dataset_delivery")

BINS_THRESHOLD_A = 30  # >30, i.e. >=31
BINS_THRESHOLD_B = 25  # >25, i.e. >=26


def real_total_events_from_preflight(preflight_dir: Path, dataset_label: str) -> int:
    """Sums n_read across every file of `dataset_label` (both eras) from
    Step 1's own pre-flight scan -- ground truth, not the portal's
    aggregate metadata, not assumed from the task brief."""
    total = 0
    n_files = 0
    for f in preflight_dir.glob("job_*/preflight_result.json"):
        d = json.loads(f.read_text())
        if d["dataset_label"] != dataset_label:
            continue
        for pf in d["per_file"]:
            total += pf["n_read"]
            n_files += 1
    return total, n_files


def expected_record_file_pairs(file_lists: dict, dataset_label: str) -> set:
    g = file_lists["records"][f"{dataset_label}_G"]
    h = file_lists["records"][f"{dataset_label}_H"]
    pairs = {(g["record_id"], i) for i in range(g["n_files_from_filepage_api"])}
    pairs |= {(h["record_id"], i) for i in range(h["n_files_from_filepage_api"])}
    return pairs


def load_run_jobs(runs_dir: Path, population: str, inclusive_only: bool):
    """Reads every job_<i>/job_metadata.json + shard(s) under runs_dir.
    Returns (shard_paths, per_job_metadata keyed by array index,
    n_capped_total, capped_details)."""
    job_dirs = sorted(runs_dir.glob("job_*"), key=lambda p: int(p.name.split("_")[1]))
    if not job_dirs:
        raise RuntimeError(f"no job_* directories found under {runs_dir}")

    shard_paths = []
    per_job_metadata = {}
    capped_details = []
    for job_dir in job_dirs:
        idx = int(job_dir.name.split("_")[1])
        meta_path = job_dir / "job_metadata.json"
        if not meta_path.exists():
            raise RuntimeError(f"{job_dir}: missing job_metadata.json")
        meta = json.loads(meta_path.read_text())
        if meta.get("population") != population:
            raise RuntimeError(f"{job_dir}: population={meta.get('population')!r}, expected {population!r}")
        per_job_metadata[idx] = meta

        shard_names = ["dataset_shard_inclusive.sqlite"] if inclusive_only else [
            "dataset_shard_inclusive.sqlite", "dataset_shard_exclusive.sqlite"
        ]
        for shard_name in shard_names:
            shard_path = job_dir / shard_name
            if not shard_path.exists():
                raise RuntimeError(f"{job_dir}: missing {shard_name}")
            shard_paths.append(str(shard_path))
            if shard_name == "dataset_shard_inclusive.sqlite" or not inclusive_only:
                n_capped, capped_here = _check_capped_metadata(str(shard_path))
                if n_capped:
                    capped_details.append({"job": job_dir.name, "shard": shard_name, "entries": capped_here})

    return shard_paths, per_job_metadata, capped_details


def _check_capped_metadata(shard_path: str) -> tuple:
    """Scans a shard's shard_metadata table for any CAPPED:: key (Step 1's
    cap policy: a hard stop, never a silent subsample). Reads directly via
    sqlite3 (not through SqliteArrayShardWriter, a writer class) since
    this is a pure read of metadata we wrote ourselves."""
    import sqlite3
    with sqlite3.connect(shard_path) as conn:
        rows = conn.execute(
            "SELECT key, value FROM shard_metadata WHERE key LIKE 'CAPPED::%'"
        ).fetchall()
    return len(rows), [{"key": k, "value": v} for k, v in rows]


def build_sig_to_bumpnet(shard_paths, fs_converter=None):
    """Map each raw shard signature to (bumpnet_name, fs_str, im_str).

    `fs_converter` (upstream-names task, (1)) is an OPTIONAL callable applied
    to the final-state string before the BumpNet name is built. It exists so
    shards written BEFORE the name-format change -- whose labels still carry
    the always-zero `_0g`/`_0t` tokens -- can be read into the new upstream
    name format without re-running the per-file jobs. Passing nothing (every
    pre-existing caller) leaves behaviour bit-for-bit unchanged."""
    sig_to_bumpnet = {}
    for shard_path in shard_paths:
        for sig in list_signatures(shard_path):
            m = SIG_PATTERN.search(sig)
            if not m:
                continue
            fs_str, im_str = m.groups()
            if fs_converter is not None:
                fs_str = fs_converter(fs_str)
            bumpnet_name = _convert_to_bumpnet_name(fs_str, im_str)
            sig_to_bumpnet[sig] = (bumpnet_name, fs_str, im_str)
    return sig_to_bumpnet


def width_suffix(bin_width: float = BIN_WIDTH_GEV, upstream: bool = False) -> str:
    """The `_width_<...>` part of a histogram name.

    `upstream=True` reproduces upstream's own rule EXACTLY. Upstream builds
    the whole name as

        hist_name = f"ROI_{hist_name_base}_width_{bin_width}"

    (services/pipelines/histograms_pipeline.py at upstream commit 88d7a4b,
    lines 343/380/520/650 -- the same f-string in all four places), where
    `bin_width` comes straight from the configuration and is NOT converted:
    `bin_widths_gev = [histograms_config["bin_width_gev"]]`. In the
    configuration that value is a FLOAT -- config.yaml has
    `bin_width_gev: 10.0`, which YAML parses as a Python float, and
    domain/config.py declares `bin_width_gev: float = 10.0` with the same
    float default. So upstream's suffix for the default configuration is
    `_width_10.0`, and this function formats the configured bin width the
    same way rather than hard-coding any string.

    `upstream=False` (the default) keeps the suffix this study wrote before
    the width-suffix task -- `f"_width_{int(bin_width)}"`, i.e. `_width_10` --
    so every pre-existing invocation keeps producing byte-for-byte what it
    produced before. Only the delivery built with the upstream rule switched
    on uses the upstream form."""
    return f"_width_{bin_width}" if upstream else f"_width_{int(bin_width)}"


def roi_key(name: str, bin_width: float = BIN_WIDTH_GEV,
            upstream_width_suffix: bool = False) -> str:
    """The full ROOT key: upstream's `ROI_` prefix, the BumpNet name, and the
    width suffix. Built from the configured bin width, never hard-coded."""
    return f"ROI_{name}" + width_suffix(bin_width, upstream_width_suffix)


def write_root_file(path: Path, histograms: dict, upstream_width_suffix: bool = False):
    written = {}
    with uproot.recreate(str(path)) as fout:
        for name, (values, edges) in sorted(histograms.items()):
            key = roi_key(name, upstream_width_suffix=upstream_width_suffix)
            fout[key] = to_writable_th1f(values, edges, key)
            written[key] = values
    verify_written_th1f(str(path), written)
    return written


def write_cropped_root_file(path: Path, histograms: dict,
                            upstream_width_suffix: bool = False):
    """Crops every histogram to its first..last filled bin (crop_arrays,
    imported from crop_bumpnet_root.py unmodified) before writing --
    exactly the same operation the earlier delivery's own
    crop_bumpnet_root.py performs, just applied here at build time on
    freshly-computed histograms instead of as a separate pass over
    already-written files (this dataset's histograms are not written
    uncropped to disk first at all -- no functional difference, since
    crop_arrays' input here is the identical (values, edges) pair either
    script would start from)."""
    written = {}
    with uproot.recreate(str(path)) as fout:
        for name, (values, edges) in sorted(histograms.items()):
            cropped_values, cropped_edges, _first, _last = crop_arrays(values, edges)
            widths = np.diff(cropped_edges)
            if not np.allclose(widths, BIN_WIDTH_GEV, atol=1e-9):
                raise AssertionError(f"{name}: cropped bin widths are not exactly {BIN_WIDTH_GEV} GeV")
            key = roi_key(name, upstream_width_suffix=upstream_width_suffix)
            fout[key] = to_writable_th1f(cropped_values, cropped_edges, key)
            written[key] = cropped_values
    verify_written_th1f(str(path), written)
    return written


def manifest_entry(name, im_str, values, edges, upstream_width_suffix: bool = False):
    nonzero_idx = np.nonzero(values > 0)[0]
    n_bins = int(len(nonzero_idx))
    n_events = int(values.sum())
    first_edge = float(edges[nonzero_idx[0]]) if n_bins > 0 else None
    last_edge = float(edges[nonzero_idx[-1] + 1]) if n_bins > 0 else None
    return {
        "name": name,
        "root_key": roi_key(name, upstream_width_suffix=upstream_width_suffix),
        "combination": im_str,
        "final_state_category": name.split("_cat_", 1)[1] if "_cat_" in name else None,
        "object_count": object_count(im_str),
        "object_content_category": object_content_category(im_str),
        "n_events": n_events,
        "n_filled_bins": n_bins,
        "first_filled_bin_low_edge_gev": first_edge,
        "last_filled_bin_high_edge_gev": last_edge,
    }


def load_old_delivery_histograms(root_path: Path) -> dict:
    f = uproot.open(str(root_path))
    out = {}
    for key in sorted(set(k.split(";")[0] for k in f.keys())):
        h = f[key]
        out[key] = (h.values().astype(np.float64), h.axis().edges().astype(np.float64))
    return out


def continuity_check(old_hists: dict, new_hists_by_name: dict, old_file_label: str) -> dict:
    """old_hists: {ROI_key: (values, edges)}. new_hists_by_name: {name: (values, edges)}
    (from THIS run's own stage-c survivors, i.e. the fully post-processed
    but not-yet-bin-count-thresholded histograms -- the natural
    "corresponding new histogram" for any old name, since bin-count
    classification happens after this point in both scripts)."""
    problems = []
    n_checked = 0
    n_identical = 0
    for old_key, (old_values, old_edges) in old_hists.items():
        name = old_key[len("ROI_"):].rsplit("_width_", 1)[0] if old_key.startswith("ROI_") else old_key
        n_checked += 1
        if name not in new_hists_by_name:
            problems.append({"name": name, "issue": "missing_from_new_stage_c_survivors"})
            continue
        new_values, new_edges = new_hists_by_name[name]
        if new_values.shape != old_values.shape or not np.array_equal(new_values, old_values):
            problems.append({
                "name": name, "issue": "bin_contents_differ",
                "old_n_events": float(old_values.sum()), "new_n_events": float(new_values.sum()),
                "old_n_bins": int(old_values.size), "new_n_bins": int(new_values.size),
            })
            continue
        if new_edges.shape != old_edges.shape or not np.array_equal(new_edges, old_edges):
            problems.append({"name": name, "issue": "edges_differ"})
            continue
        n_identical += 1
    return {
        "old_file": old_file_label,
        "n_old_histograms": len(old_hists),
        "n_checked": n_checked,
        "n_identical": n_identical,
        "n_problems": len(problems),
        "problems": problems,
        "all_identical": len(problems) == 0,
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--dataset-label", required=True)
    p.add_argument("--runs-dir", required=True, help="e.g. .../output/cms_datasets/runs/DoubleMuon")
    p.add_argument("--preflight-dir", required=True)
    p.add_argument("--file-lists", required=True)
    p.add_argument("--population", default="generic")
    p.add_argument("--inclusive-only", action="store_true",
                    help="dataset is top veto priority: inclusive==exclusive, deliver inclusive only")
    p.add_argument("--old-delivery-min31", default=None,
                    help="prior delivery's >30-bin ROOT file, for the continuity check (optional)")
    p.add_argument("--old-delivery-min26", default=None,
                    help="prior delivery's >25-bin ROOT file, for the continuity check (optional)")
    p.add_argument("--out-dir", required=True)
    p.add_argument("--out-prefix", required=True, help="e.g. doublemuon_generic")
    args = p.parse_args()

    runs_dir = Path(args.runs_dir)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    file_lists = json.loads(Path(args.file_lists).read_text())

    assert BIN_WIDTH_GEV == 10.0 and FIXED_MASS_MIN_GEV == 0.0 and FIXED_MASS_MAX_GEV == 10000.0, (
        "fixed-grid constants have drifted from the expected 0-10000 GeV / 10 GeV grid"
    )

    print("=== Step (a): completeness/identity check ===")
    expected_pairs = expected_record_file_pairs(file_lists, args.dataset_label)
    expected_real_total, expected_n_files_preflight = real_total_events_from_preflight(
        Path(args.preflight_dir), args.dataset_label
    )
    print(f"expected {len(expected_pairs)} (record,file) pairs; "
          f"expected total real events (from Step 1 scan) = {expected_real_total:,}")
    if expected_n_files_preflight != len(expected_pairs):
        print(f"STOP: Step 1's own pre-flight scan covered {expected_n_files_preflight} files for "
              f"{args.dataset_label}, but the portal file list says {len(expected_pairs)} -- these must "
              f"agree before any completeness check against Step 1's event totals can be trusted.",
              file=sys.stderr)
        sys.exit(1)

    shard_paths, per_job_metadata, capped_details = load_run_jobs(
        runs_dir, args.population, args.inclusive_only
    )

    n_jobs = len(per_job_metadata)
    pairs_list = [(m["record_id"], m["file_index"]) for m in per_job_metadata.values()]
    seen_pairs = set(pairs_list)
    duplicate_pairs = sorted({p for p in pairs_list if pairs_list.count(p) > 1})
    missing_pairs = sorted(expected_pairs - seen_pairs)
    extra_pairs = sorted(seen_pairs - expected_pairs)
    total_n_read = sum(m["n_read"] for m in per_job_metadata.values())
    commits = sorted(set(m["git_commit"] for m in per_job_metadata.values()))

    identity = {
        "n_jobs_present": n_jobs,
        "n_expected_files": len(expected_pairs),
        "missing_pairs": missing_pairs,
        "extra_pairs": extra_pairs,
        "duplicate_pairs": duplicate_pairs,
        "each_file_index_exactly_once": (len(seen_pairs) == n_jobs and not duplicate_pairs),
        "total_n_read": total_n_read,
        "expected_total_events": expected_real_total,
        "n_read_matches": total_n_read == expected_real_total,
        "distinct_git_commits_used": commits,
        "single_commit_used": len(commits) == 1,
        "n_capped_entries_found": sum(len(c["entries"]) for c in capped_details),
        "capped_details": capped_details,
        "cap_policy_clean": len(capped_details) == 0,
    }
    print(json.dumps(identity, indent=2)[:2000])

    hard_stop = (
        n_jobs != len(expected_pairs)
        or missing_pairs or extra_pairs
        or not identity["each_file_index_exactly_once"]
        or not identity["n_read_matches"]
        or not identity["single_commit_used"]
        or not identity["cap_policy_clean"]
    )
    if hard_stop:
        print("STOP: completeness/identity/cap-policy check failed -- refusing to build a delivery.",
              file=sys.stderr)
        (out_dir / "identity_check_FAILED.json").write_text(json.dumps(identity, indent=2))
        sys.exit(1)
    print(f"PASS: {n_jobs}/{len(expected_pairs)} files present exactly once, "
          f"total_n_read={total_n_read:,} matches expected exactly, single git commit "
          f"({commits[0]}), zero CAPPED:: entries.")

    print("\n=== Step (b): funnel (real, shared post-processing chain) ===")
    sig_to_bumpnet = build_sig_to_bumpnet(shard_paths)
    with tempfile.TemporaryDirectory(prefix=f"deliver_{args.dataset_label}_funnel_") as tmp:
        scratch_shards = copy_shards(shard_paths, Path(tmp))
        stage_b_names, stage_c_survivors, stage_d_survivors, im_str_by_name = run_funnel_at_threshold(
            scratch_shards, PRIMARY_MIN_EVENTS_PER_FS, sig_to_bumpnet
        )
    print(f"stage_b(>=100 events per final state)={len(stage_b_names)} "
          f"stage_c(post-processed, >=100 main events)={len(stage_c_survivors)} "
          f"stage_d(>{MIN_BUMPNET_BINS} bins, merge_and_count's own threshold)={len(stage_d_survivors)}")

    print("\n=== Classify every stage-c survivor against both bin thresholds ===")
    all_hists = {}
    n_nonempty_by_name = {}
    n_events_by_name = {}
    for name, main_arr in stage_c_survivors.items():
        values, edges = make_fixed_grid_histogram(main_arr)
        all_hists[name] = (values, edges)
        n_nonempty_by_name[name] = int(np.count_nonzero(values))
        n_events_by_name[name] = int(values.sum())

    set_a = {n for n in stage_c_survivors
             if n_nonempty_by_name[n] > BINS_THRESHOLD_A and n_events_by_name[n] >= MIN_BUMPNET_EVENTS}
    set_b = {n for n in stage_c_survivors
             if n_nonempty_by_name[n] > BINS_THRESHOLD_B and n_events_by_name[n] >= MIN_BUMPNET_EVENTS}
    print(f"set_a (>{BINS_THRESHOLD_A} bins): {len(set_a)} names")
    print(f"set_b (>{BINS_THRESHOLD_B} bins): {len(set_b)} names")
    if not set_a.issubset(set_b):
        print("STOP: >25-bin set is not a superset of the >30-bin set (should be impossible).",
              file=sys.stderr)
        sys.exit(1)

    continuity_results = {}
    if args.old_delivery_min31:
        print("\n=== Step (c): CONTINUITY CHECK vs prior delivery (min31bins) ===")
        old_hists_31 = load_old_delivery_histograms(Path(args.old_delivery_min31))
        continuity_results["min31bins"] = continuity_check(old_hists_31, all_hists, args.old_delivery_min31)
        r = continuity_results["min31bins"]
        print(f"{r['n_identical']}/{r['n_old_histograms']} identical, {r['n_problems']} problem(s)")
        if not r["all_identical"]:
            print(f"CONTINUITY CHECK FAILED for min31bins -- {r['n_problems']} histogram(s) differ. "
                  f"Reporting, not adjusting.", file=sys.stderr)
            for prob in r["problems"][:20]:
                print(f"  - {prob}", file=sys.stderr)
    if args.old_delivery_min26:
        print("\n=== Step (c): CONTINUITY CHECK vs prior delivery (min26bins) ===")
        old_hists_26 = load_old_delivery_histograms(Path(args.old_delivery_min26))
        continuity_results["min26bins"] = continuity_check(old_hists_26, all_hists, args.old_delivery_min26)
        r = continuity_results["min26bins"]
        print(f"{r['n_identical']}/{r['n_old_histograms']} identical, {r['n_problems']} problem(s)")
        if not r["all_identical"]:
            print(f"CONTINUITY CHECK FAILED for min26bins -- {r['n_problems']} histogram(s) differ. "
                  f"Reporting, not adjusting.", file=sys.stderr)
            for prob in r["problems"][:20]:
                print(f"  - {prob}", file=sys.stderr)

    print("\n=== Writing ROOT files ===")
    hists_a = {name: all_hists[name] for name in set_a}
    hists_b = {name: all_hists[name] for name in set_b}
    path_a = out_dir / f"{args.out_prefix}_bumpnet_min31bins.root"
    path_b = out_dir / f"{args.out_prefix}_bumpnet_min26bins.root"
    path_a_cropped = out_dir / f"{args.out_prefix}_bumpnet_min31bins_cropped.root"
    path_b_cropped = out_dir / f"{args.out_prefix}_bumpnet_min26bins_cropped.root"

    write_root_file(path_a, hists_a)
    write_root_file(path_b, hists_b)
    write_cropped_root_file(path_a_cropped, hists_a)
    write_cropped_root_file(path_b_cropped, hists_b)
    print(f"wrote {path_a} ({len(hists_a)} histograms)")
    print(f"wrote {path_b} ({len(hists_b)} histograms)")
    print(f"wrote {path_a_cropped} ({len(hists_a)} histograms, cropped)")
    print(f"wrote {path_b_cropped} ({len(hists_b)} histograms, cropped)")

    print("\n=== Writing manifests ===")
    manifest_a = [manifest_entry(n, im_str_by_name[n], *all_hists[n]) for n in sorted(set_a)]
    manifest_b = [manifest_entry(n, im_str_by_name[n], *all_hists[n]) for n in sorted(set_b)]
    (out_dir / f"manifest_{args.out_prefix}_min31bins.json").write_text(json.dumps(manifest_a, indent=2))
    (out_dir / f"manifest_{args.out_prefix}_min26bins.json").write_text(json.dumps(manifest_b, indent=2))

    extra_names = sorted(set_b - set_a)
    extra_stats = {
        "n_extra": len(extra_names),
        "extra_names": extra_names,
        "event_count_stats": {
            "min": min((n_events_by_name[n] for n in extra_names), default=None),
            "median": float(np.median([n_events_by_name[n] for n in extra_names])) if extra_names else None,
            "max": max((n_events_by_name[n] for n in extra_names), default=None),
        },
    }

    summary = {
        "dataset_label": args.dataset_label,
        "population": args.population,
        "inclusive_only": args.inclusive_only,
        "identity_check": identity,
        "funnel": {
            "b_after_min_events_per_fs_100": len(stage_b_names),
            "c_after_postprocessing_ge100_main": len(stage_c_survivors),
            "d_bumpnet_usable_gt30bins_ge100events": len(stage_d_survivors),
        },
        "n_histograms_min31bins": len(set_a),
        "n_histograms_min26bins": len(set_b),
        "extra_histograms_min26_vs_min31": extra_stats,
        "continuity_check": {k: {kk: vv for kk, vv in v.items() if kk != "problems"} for k, v in continuity_results.items()},
        "output_files": {
            path_a.name: str(path_a), path_b.name: str(path_b),
            path_a_cropped.name: str(path_a_cropped), path_b_cropped.name: str(path_b_cropped),
        },
    }
    (out_dir / "build_summary.json").write_text(json.dumps(summary, indent=2))
    if continuity_results:
        (out_dir / "continuity_check.json").write_text(json.dumps(continuity_results, indent=2))
    print(json.dumps(summary, indent=2)[:3000])

    continuity_all_pass = all(v["all_identical"] for v in continuity_results.values()) if continuity_results else None
    if continuity_all_pass is False:
        print("\nSTOP: continuity check FAILED -- see continuity_check.json. Not treating this as a "
              "silent success; delivery files were still written for inspection, but should not be "
              "treated as verified until this is resolved.", file=sys.stderr)
        sys.exit(2)

    print("\nAll mandatory checks PASSED.")


if __name__ == "__main__":
    main()
