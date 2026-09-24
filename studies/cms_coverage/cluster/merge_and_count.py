#!/usr/bin/env python
"""
CMS coverage survey -- merge + funnel counting (Part 1.4/1.5, Part 2).

Merges all per-job SQLite shards (services.storage.sqlite_shards), applies
the REAL shared post-processing chain unmodified
(services.storage.sqlite_shards.prune_final_states_below_min_events,
services.pipelines.post_processing_pipeline._apply_z_peak_cut /
_find_rightmost_highest_peak / _split_by_first_empty_bin), reproduces the
m0m1j0 self-check against studies/m0m1j0_cms/v2's committed numbers, and
counts BumpNet-usable histograms at every funnel stage (a)-(e).

Never mutates the original per-job shards under --jobs-dir: every call to
the (destructive, in-place-DELETE) prune_final_states_below_min_events
runs on a fresh scratch copy, made once per threshold tested -- this is
what lets stage (b)/(d) be recomputed at several min_events thresholds
(50/100/200/1000) using the SAME real, unmodified function each time,
without one threshold's pruning destroying the data another needs.

Usage:
    python merge_and_count.py --jobs-dir /storage/.../cms_coverage_full \
        --n-jobs 57 --out-dir /storage/.../cms_coverage_merge
"""
from __future__ import annotations

import argparse
import json
import logging
import re
import shutil
import sqlite3
import sys
import tempfile
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

import numpy as np  # noqa: E402

from services.storage.sqlite_shards import (  # noqa: E402
    iter_arrays_for_signature,
    list_signatures,
    prune_final_states_below_min_events,
)
from services.pipelines.post_processing_pipeline import (  # noqa: E402
    _apply_z_peak_cut,
    _find_rightmost_highest_peak,
    _split_by_first_empty_bin,
)
from studies.m0m1j0_cms.histograms import _convert_to_bumpnet_name  # noqa: E402

logging.basicConfig(level=logging.WARNING)
LOGGER = logging.getLogger("merge_and_count")

SIG_PATTERN = re.compile(r"_FS_([0-9a-z_]+)_IM_([0-9a-z]+)$")
IM_PARTICLE_PATTERN = re.compile(r"([emjb])(\d+)")

BIN_WIDTH_GEV = 10.0
FIXED_MASS_MIN_GEV = 0.0
FIXED_MASS_MAX_GEV = 10000.0
N_FIXED_BINS = int(round((FIXED_MASS_MAX_GEV - FIXED_MASS_MIN_GEV) / BIN_WIDTH_GEV))
Z_PEAK_CUTOFF = 115.0  # config.yaml:155
MAX_MASS_CUTOFF = 10000.0  # config.yaml:156
PRIMARY_MIN_EVENTS_PER_FS = 100  # config.yaml:142
SENSITIVITY_THRESHOLDS = (50, 200, 1000)
MIN_BUMPNET_BINS = 30  # arXiv:2501.05603 Section 2.2.2
MIN_BUMPNET_EVENTS = 100  # arXiv:2501.05603 Section 2.2.2
MIN_EVENTS_PER_RETAINED_BIN = 10  # arXiv:2501.05603 Section 3.2.4


def object_content_category(im_str: str) -> str:
    letters = set(letter for letter, _rank in IM_PARTICLE_PATTERN.findall(im_str))
    has_b = "b" in letters
    has_j = "j" in letters
    has_lepton = ("e" in letters) or ("m" in letters)
    if has_b:
        return "b-jet-containing"
    if has_lepton and has_j:
        return "lepton+jet"
    if has_lepton:
        return "lepton-only"
    if has_j:
        return "jet-only"
    return "other"


def object_count(im_str: str) -> int:
    return len(IM_PARTICLE_PATTERN.findall(im_str))


def fixed_grid_histogram(values: np.ndarray) -> np.ndarray:
    counts = np.zeros(N_FIXED_BINS, dtype=np.int64)
    finite = values[np.isfinite(values)]
    nudged = np.where(
        finite == FIXED_MASS_MAX_GEV,
        np.nextafter(FIXED_MASS_MAX_GEV, FIXED_MASS_MIN_GEV),
        finite,
    )
    in_range = (nudged >= FIXED_MASS_MIN_GEV) & (nudged < FIXED_MASS_MAX_GEV)
    bin_idx = np.floor((nudged[in_range] - FIXED_MASS_MIN_GEV) / BIN_WIDTH_GEV).astype(np.int64)
    bin_idx = np.clip(bin_idx, 0, N_FIXED_BINS - 1)
    np.add.at(counts, bin_idx, 1)
    return counts


def copy_shards(source_paths, scratch_dir: Path):
    scratch_dir.mkdir(parents=True, exist_ok=True)
    copies = []
    for i, src in enumerate(source_paths):
        dst = scratch_dir / f"shard_{i}.sqlite"
        shutil.copyfile(src, dst)
        copies.append(str(dst))
    return copies


def run_funnel_at_threshold(shard_paths, threshold: int, sig_to_bumpnet: dict):
    """Run the REAL prune_final_states_below_min_events at `threshold` on
    `shard_paths` (expected to be scratch copies -- this mutates them),
    then the REAL z-peak/max-mass/peak-removal/first-empty-bin-split chain
    on every surviving signature's concatenated raw masses. Returns
    (stage_b_names, stage_c_survivors[name -> main_array],
    stage_d_survivors[name -> (main_array, hist_counts, n_nonempty_bins)]).
    """
    prune_final_states_below_min_events(shard_paths, threshold)

    surviving_bumpnet_to_sigs = defaultdict(list)
    for shard_path in shard_paths:
        for sig in list_signatures(shard_path):
            if sig not in sig_to_bumpnet:
                continue
            bumpnet_name, fs_str, im_str = sig_to_bumpnet[sig]
            surviving_bumpnet_to_sigs[bumpnet_name].append((shard_path, sig, im_str))
    stage_b_names = list(surviving_bumpnet_to_sigs.keys())

    stage_c_survivors = {}
    im_str_by_name = {}
    for bumpnet_name, entries in surviving_bumpnet_to_sigs.items():
        chunks = []
        for shard_path, sig, im_str in entries:
            chunks.extend(iter_arrays_for_signature(shard_path, sig))
            im_str_by_name[bumpnet_name] = im_str
        raw_arr = np.concatenate(chunks).astype(np.float64) if chunks else np.array([], dtype=np.float64)

        im_str = im_str_by_name[bumpnet_name]
        fake_sig = f"x_FS_x_IM_{im_str}"
        arr = _apply_z_peak_cut(raw_arr, fake_sig, Z_PEAK_CUTOFF, LOGGER)
        arr = arr[arr <= MAX_MASS_CUTOFF] if MAX_MASS_CUTOFF > 0 else arr
        if arr.size == 0:
            continue
        peak_mass = _find_rightmost_highest_peak(arr, BIN_WIDTH_GEV, LOGGER)
        filtered = arr if peak_mass is None else arr[arr >= peak_mass]
        if filtered.size == 0:
            continue
        main_arr, _outliers = _split_by_first_empty_bin(filtered, BIN_WIDTH_GEV, LOGGER)
        if main_arr.size >= threshold:
            stage_c_survivors[bumpnet_name] = main_arr

    stage_d_survivors = {}
    for bumpnet_name, main_arr in stage_c_survivors.items():
        hist_counts = fixed_grid_histogram(main_arr)
        n_nonempty_bins = int(np.count_nonzero(hist_counts))
        n_events_in_hist = int(hist_counts.sum())
        if n_nonempty_bins > MIN_BUMPNET_BINS and n_events_in_hist >= threshold:
            stage_d_survivors[bumpnet_name] = (main_arr, hist_counts, n_nonempty_bins)

    return stage_b_names, stage_c_survivors, stage_d_survivors, im_str_by_name


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--jobs-dir", required=True)
    p.add_argument("--n-jobs", type=int, required=True)
    p.add_argument("--out-dir", required=True)
    args = p.parse_args()

    jobs_dir = Path(args.jobs_dir)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    shard_paths = []
    per_job_metadata = {}
    for i in range(1, args.n_jobs + 1):
        job_dir = jobs_dir / f"job_{i}"
        shard = job_dir / "coverage_shard.sqlite"
        meta_path = job_dir / "job_metadata.json"
        if not shard.exists() or not meta_path.exists():
            raise RuntimeError(f"job_{i}: missing shard or metadata under {job_dir}")
        shard_paths.append(str(shard))
        per_job_metadata[i] = json.loads(meta_path.read_text())

    # ---- Identity check: every job exactly once, total events read ----
    total_n_read = sum(m["n_read"] for m in per_job_metadata.values())
    identity = {
        "n_jobs_present": len(per_job_metadata),
        "total_n_read": total_n_read,
        "expected_total_events": 94_148_416,
        "matches_expected": total_n_read == 94_148_416,
    }
    print(f"Identity check: {len(per_job_metadata)} jobs, total_n_read={total_n_read:,}, "
          f"expected=94,148,416, match={identity['matches_expected']}")
    if not identity["matches_expected"]:
        print("REFUSING to proceed: total events read does not match the portal total.", file=sys.stderr)
        (out_dir / "identity_check.json").write_text(json.dumps(identity, indent=2))
        sys.exit(1)

    # ---- Stage (a): all (pattern x category) signatures with >=1 event, PRE-prune ----
    sig_to_bumpnet = {}
    all_bumpnet_names_stage_a = set()
    for shard_path in shard_paths:
        for sig in list_signatures(shard_path):
            m = SIG_PATTERN.search(sig)
            if not m:
                continue
            fs_str, im_str = m.groups()
            bumpnet_name = _convert_to_bumpnet_name(fs_str, im_str)
            sig_to_bumpnet[sig] = (bumpnet_name, fs_str, im_str)
            all_bumpnet_names_stage_a.add(bumpnet_name)
    stage_a_count = len(all_bumpnet_names_stage_a)
    print(f"Stage (a): {stage_a_count} distinct (pattern x category) histograms with >=1 event")

    m0m1j0_present = any(bn.startswith("mass_m0m1j0_cat_") for bn in all_bumpnet_names_stage_a)
    print(f"m0m1j0 present among stage-(a) histograms: {m0m1j0_present}")

    # ---- Run the real funnel at the PRIMARY threshold (100), on a scratch copy ----
    with tempfile.TemporaryDirectory(prefix="coverage_merge_primary_") as tmp:
        primary_shards = copy_shards(shard_paths, Path(tmp))
        stage_b_names, stage_c_survivors, stage_d_survivors, im_str_by_name = run_funnel_at_threshold(
            primary_shards, PRIMARY_MIN_EVENTS_PER_FS, sig_to_bumpnet
        )

    # ---- MANDATORY self-check vs v2's committed m0m1j0 numbers ----
    # Reconstruct raw (pre-z-peak) per-signature totals from a SEPARATE
    # fresh copy pruned at 100, before any z-peak cut, for direct
    # comparison against v2_summary's own "n_raw" (pre-z-peak) field.
    with tempfile.TemporaryDirectory(prefix="coverage_merge_selfcheck_") as tmp2:
        selfcheck_shards = copy_shards(shard_paths, Path(tmp2))
        prune_final_states_below_min_events(selfcheck_shards, PRIMARY_MIN_EVENTS_PER_FS)
        raw_after_prune = defaultdict(list)
        for shard_path in selfcheck_shards:
            for sig in list_signatures(shard_path):
                if sig not in sig_to_bumpnet:
                    continue
                bumpnet_name, _fs, _im = sig_to_bumpnet[sig]
                raw_after_prune[bumpnet_name].extend(iter_arrays_for_signature(shard_path, sig))
        combined_raw_after_prune = {
            name: (np.concatenate(chunks) if chunks else np.array([]))
            for name, chunks in raw_after_prune.items()
        }

    v2_summary = json.loads(
        (REPO_ROOT / "studies/m0m1j0_cms/v2/data/merge_v2_summary.json").read_text()
    )
    v2_per_category = v2_summary["per_category"]
    self_check_rows = []
    self_check_all_pass = True
    for bumpnet_name, v2_entry in v2_per_category.items():
        if not bumpnet_name.startswith("mass_m0m1j0_cat_"):
            continue
        v2_pruned = v2_entry.get("pruned_by_min_events_per_fs", False)
        v2_n_raw = v2_entry.get("n_raw")
        our_arr = combined_raw_after_prune.get(bumpnet_name)
        our_present = our_arr is not None and our_arr.size > 0
        our_n_raw = int(our_arr.size) if our_present else 0
        ok = (not our_present) if v2_pruned else (our_present and our_n_raw == v2_n_raw)
        self_check_rows.append({
            "bumpnet_name": bumpnet_name, "v2_n_raw": v2_n_raw, "v2_pruned": v2_pruned,
            "our_n_raw": our_n_raw, "our_present": our_present, "match": ok,
        })
        self_check_all_pass = self_check_all_pass and ok
    n_match = sum(r["match"] for r in self_check_rows)
    print(f"Self-check vs v2 committed numbers: {n_match}/{len(self_check_rows)} categories match, "
          f"ALL PASS = {self_check_all_pass}")
    (out_dir / "self_check_vs_v2.json").write_text(json.dumps(self_check_rows, indent=2))
    if not self_check_all_pass:
        print("SELF-CHECK FAILED -- stopping before Part 2 counting, per task instruction.", file=sys.stderr)
        sys.exit(1)

    print(f"Stage (b): {len(stage_b_names)} histograms survive min_events_per_fs=100")
    print(f"Stage (c): {len(stage_c_survivors)} histograms survive post-processing (>=100 main events)")
    print(f"Stage (d): {len(stage_d_survivors)} BumpNet-usable (>{MIN_BUMPNET_BINS} bins, "
          f">={MIN_BUMPNET_EVENTS} events)")

    # ---- Stage (e): every retained (non-empty) bin has >=10 events ----
    stage_e_names = []
    for bumpnet_name, (main_arr, hist_counts, n_nonempty_bins) in stage_d_survivors.items():
        nonzero_counts = hist_counts[hist_counts > 0]
        if nonzero_counts.size > 0 and np.min(nonzero_counts) >= MIN_EVENTS_PER_RETAINED_BIN:
            stage_e_names.append(bumpnet_name)
    print(f"Stage (e): {len(stage_e_names)} of stage-(d) histograms have >=10 events in EVERY retained bin")

    # ---- Breakdown by object count and content (stages b, c, d) ----
    def breakdown(names, im_lookup):
        by_count, by_content = defaultdict(int), defaultdict(int)
        for bn in names:
            im_str = im_lookup.get(bn, "")
            by_count[object_count(im_str)] += 1
            by_content[object_content_category(im_str)] += 1
        return dict(by_count), dict(by_content)

    b_by_count, b_by_content = breakdown(stage_b_names, im_str_by_name)
    c_by_count, c_by_content = breakdown(list(stage_c_survivors.keys()), im_str_by_name)
    d_by_count, d_by_content = breakdown(list(stage_d_survivors.keys()), im_str_by_name)

    # ---- Top 20 by event count, median bins ----
    top20 = sorted(
        ((bn, int(hist.sum()), n_bins) for bn, (_, hist, n_bins) in stage_d_survivors.items()),
        key=lambda kv: -kv[1],
    )[:20]
    median_bins = float(np.median([n for _, _, n in stage_d_survivors.values()])) if stage_d_survivors else None

    # ---- Sensitivity: (b) and (d) at alternate thresholds ----
    sensitivity = {}
    for threshold in SENSITIVITY_THRESHOLDS:
        with tempfile.TemporaryDirectory(prefix=f"coverage_merge_sens{threshold}_") as tmp:
            sens_shards = copy_shards(shard_paths, Path(tmp))
            b_names, _c, d_survivors, _im = run_funnel_at_threshold(sens_shards, threshold, sig_to_bumpnet)
            sensitivity[str(threshold)] = {"stage_b": len(b_names), "stage_d": len(d_survivors)}
            print(f"Sensitivity threshold={threshold}: stage_b={len(b_names)}, stage_d={len(d_survivors)}")

    result = {
        "identity_check": identity,
        "m0m1j0_present_stage_a": m0m1j0_present,
        "self_check_vs_v2_all_pass": self_check_all_pass,
        "funnel": {
            "a_all_pairs_ge1_event": stage_a_count,
            "b_after_min_events_per_fs_100": len(stage_b_names),
            "c_after_postprocessing_ge100_main": len(stage_c_survivors),
            "d_bumpnet_usable_gt30bins_ge100events": len(stage_d_survivors),
            "e_bumpnet_usable_and_ge10_per_retained_bin": len(stage_e_names),
        },
        "breakdown_by_object_count": {"b": b_by_count, "c": c_by_count, "d": d_by_count},
        "breakdown_by_object_content": {"b": b_by_content, "c": c_by_content, "d": d_by_content},
        "top20_by_event_count_and_bins": top20,
        "median_bins_stage_d": median_bins,
        "stage_e_names": stage_e_names,
        "sensitivity_at_alternate_thresholds": sensitivity,
    }
    (out_dir / "funnel_result.json").write_text(json.dumps(result, indent=2, default=str))
    print(json.dumps(result["funnel"], indent=2))
    print(f"wrote results under {out_dir}")


if __name__ == "__main__":
    main()
