#!/usr/bin/env python
"""
Per-dataset funnel measurement (scaled and unscaled), for one dataset's
single-file SQLite shard produced by run_per_dataset_on_file.py.

Reuses the real, already-committed helpers from
studies/cms_coverage/cluster/merge_and_count.py (itself calling the real,
unmodified shared functions: prune_final_states_below_min_events,
_apply_z_peak_cut, _find_rightmost_highest_peak, _split_by_first_empty_bin)
-- nothing here reimplements that physics.

Produces, per dataset:
  (a) unscaled: distinct (pattern x category) pairs with >=1 raw event.
  (b) unscaled: real prune_final_states_below_min_events at 100, on this
      one file's own raw per-final-state population.
  (b) scaled: same population, multiplied by
      (dataset_total_events / file_n_read), compared to 100 -- an
      arithmetic scaling of an already-measured population, not a
      reimplementation of the prune decision itself.
  (c): the real z-peak/max-mass/peak-removal/first-empty-bin chain,
      applied to (b)-unscaled's survivors, counted if the UNSCALED main
      array still has >=100 events (matches how the committed 316
      DoubleMuon number was computed).
  (d) unscaled: >30 non-empty bins (fixed 10 GeV grid) AND >=100 events,
      on (c)'s survivors -- the direct, measured headline per dataset.
  (d) scaled (ESTIMATE): candidates are (b)-scaled's survivors (a
      superset of (b)-unscaled, since scaling only ever helps), each run
      through the SAME real z-peak/peak-removal/split chain; a candidate
      counts if (unscaled main-array size x scale factor) >= 100 AND the
      FILE-LEVEL (unscaled) bin count is already >30. The bin count
      cannot be scaled -- more real events would very plausibly populate
      MORE bins than the one file already shows, not fewer, so using the
      file-level bin count as a stand-in is flagged explicitly as a
      likely UNDER-estimate of the true scaled (d), not an over-estimate.

Usage:
    python measure_per_dataset_funnel.py \
        --shard /storage/.../job_JetHT/coverage_shard.sqlite \
        --dataset-label JetHT --scale-factor 1123.4 \
        --out /storage/.../funnel_JetHT.json
"""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT))

import numpy as np  # noqa: E402

from services.storage.sqlite_shards import (  # noqa: E402
    list_signatures,
    prune_final_states_below_min_events,
)
from services.pipelines.post_processing_pipeline import (  # noqa: E402
    _apply_z_peak_cut,
    _find_rightmost_highest_peak,
    _split_by_first_empty_bin,
)
from studies.m0m1j0_cms.histograms import _convert_to_bumpnet_name  # noqa: E402
from studies.cms_coverage.cluster.merge_and_count import (  # noqa: E402
    SIG_PATTERN,
    BIN_WIDTH_GEV,
    Z_PEAK_CUTOFF,
    MAX_MASS_CUTOFF,
    MIN_BUMPNET_BINS,
    MIN_BUMPNET_EVENTS,
    fixed_grid_histogram,
    object_count,
    object_content_category,
    copy_shards,
    load_chunks_by_signature,
)

import logging
logging.basicConfig(level=logging.WARNING)
LOGGER = logging.getLogger("per_dataset_funnel")


def read_final_state_populations(shard_path: str) -> dict:
    with sqlite3.connect(shard_path) as conn:
        rows = conn.execute(
            "SELECT final_state, SUM(n_events) FROM final_state_counts GROUP BY final_state"
        ).fetchall()
    return {fs: int(n) for fs, n in rows}


def run_chain(raw_arr: np.ndarray, im_str: str):
    """Real z-peak/max-mass/peak-removal/first-empty-bin chain on one
    signature's raw masses. Returns (main_arr or None)."""
    fake_sig = f"x_FS_x_IM_{im_str}"
    arr = _apply_z_peak_cut(raw_arr, fake_sig, Z_PEAK_CUTOFF, LOGGER)
    arr = arr[arr <= MAX_MASS_CUTOFF] if MAX_MASS_CUTOFF > 0 else arr
    if arr.size == 0:
        return None
    peak_mass = _find_rightmost_highest_peak(arr, BIN_WIDTH_GEV, LOGGER)
    filtered = arr if peak_mass is None else arr[arr >= peak_mass]
    if filtered.size == 0:
        return None
    main_arr, _outliers = _split_by_first_empty_bin(filtered, BIN_WIDTH_GEV, LOGGER)
    return main_arr if main_arr.size > 0 else None


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--shard", required=True)
    p.add_argument("--dataset-label", required=True)
    p.add_argument("--scale-factor", type=float, required=True)
    p.add_argument("--out", required=True)
    args = p.parse_args()

    shard_path = args.shard
    scale = args.scale_factor

    # ---- sig -> (bumpnet_name, fs_str, im_str), from the raw shard ----
    sig_to_bumpnet = {}
    for sig in list_signatures(shard_path):
        m = SIG_PATTERN.search(sig)
        if not m:
            continue
        fs_str, im_str = m.groups()
        bn = _convert_to_bumpnet_name(fs_str, im_str)
        sig_to_bumpnet[sig] = (bn, fs_str, im_str)

    stage_a_names = set(bn for bn, _fs, _im in sig_to_bumpnet.values())

    # ---- final-state populations (unscaled, from the shard's own recorded counts) ----
    fs_population = read_final_state_populations(shard_path)

    # ---- stage (b) unscaled: real prune, on a scratch copy ----
    with tempfile.TemporaryDirectory(prefix=f"pd_funnel_{args.dataset_label}_") as tmp:
        copy = copy_shards([shard_path], Path(tmp))
        prune_final_states_below_min_events(copy, MIN_BUMPNET_EVENTS)
        chunks_unscaled = load_chunks_by_signature(copy)
    stage_b_unscaled_names = set(
        sig_to_bumpnet[sig][0] for sig in chunks_unscaled if sig in sig_to_bumpnet
    )

    # ---- stage (b) scaled: population x scale >= 100, arithmetic only ----
    # fs_population's keys are the bare final-state label (e.g.
    # "2e_0m_3j_0g_0t_1b"), exactly as record_final_state_count stored
    # them (no "_FS_" prefix) -- fs_str from SIG_PATTERN is the same bare
    # string (the regex captures what follows "_FS_"), so no prefix is
    # added here either.
    fs_scaled_survives = {fs: (pop * scale >= MIN_BUMPNET_EVENTS) for fs, pop in fs_population.items()}
    stage_b_scaled_names = set()
    for sig, (bn, fs_str, im_str) in sig_to_bumpnet.items():
        if fs_scaled_survives.get(fs_str, False):
            stage_b_scaled_names.add(bn)

    # ---- stage (c): real chain on (b)-unscaled survivors, raw arrays from the UNPRUNED shard ----
    all_chunks = load_chunks_by_signature([shard_path])
    stage_c_survivors = {}  # bumpnet_name -> (main_arr, im_str)
    for sig, chunks in all_chunks.items():
        if sig not in sig_to_bumpnet:
            continue
        bn, fs_str, im_str = sig_to_bumpnet[sig]
        if bn not in stage_b_unscaled_names:
            continue
        raw_arr = np.concatenate(chunks).astype(np.float64)
        main_arr = run_chain(raw_arr, im_str)
        if main_arr is not None and main_arr.size >= MIN_BUMPNET_EVENTS:
            stage_c_survivors[bn] = (main_arr, im_str)

    # ---- stage (d) unscaled: >30 bins AND >=100 events, on (c) survivors ----
    stage_d_unscaled = {}
    for bn, (main_arr, im_str) in stage_c_survivors.items():
        hist = fixed_grid_histogram(main_arr)
        n_nonempty = int(np.count_nonzero(hist))
        n_events = int(hist.sum())
        if n_nonempty > MIN_BUMPNET_BINS and n_events >= MIN_BUMPNET_EVENTS:
            stage_d_unscaled[bn] = {"n_events": n_events, "n_nonempty_bins": n_nonempty, "im_str": im_str}

    # ---- stage (d) scaled ESTIMATE: (b)-scaled survivors run through the real chain,
    # scaled-events>=100 AND file-level bins>30 (flagged as a likely under-estimate) ----
    stage_d_scaled_candidates = {}
    for sig, chunks in all_chunks.items():
        if sig not in sig_to_bumpnet:
            continue
        bn, fs_str, im_str = sig_to_bumpnet[sig]
        if bn not in stage_b_scaled_names:
            continue
        raw_arr = np.concatenate(chunks).astype(np.float64)
        main_arr = run_chain(raw_arr, im_str)
        if main_arr is None:
            continue
        scaled_events = main_arr.size * scale
        hist = fixed_grid_histogram(main_arr)
        n_nonempty = int(np.count_nonzero(hist))
        if scaled_events >= MIN_BUMPNET_EVENTS and n_nonempty > MIN_BUMPNET_BINS:
            stage_d_scaled_candidates[bn] = {
                "unscaled_main_events": int(main_arr.size),
                "scaled_main_events_estimate": scaled_events,
                "n_nonempty_bins_file_level": n_nonempty,
                "im_str": im_str,
            }

    def breakdown(entries_dict):
        by_count, by_content = {}, {}
        for bn, info in entries_dict.items():
            im_str = info["im_str"]
            c = object_count(im_str)
            k = object_content_category(im_str)
            by_count[c] = by_count.get(c, 0) + 1
            by_content[k] = by_content.get(k, 0) + 1
        return by_count, by_content

    d_unscaled_by_count, d_unscaled_by_content = breakdown(stage_d_unscaled)
    d_scaled_by_count, d_scaled_by_content = breakdown(stage_d_scaled_candidates)

    result = {
        "dataset_label": args.dataset_label,
        "scale_factor": scale,
        "funnel": {
            "a_unscaled": len(stage_a_names),
            "b_unscaled": len(stage_b_unscaled_names),
            "b_scaled": len(stage_b_scaled_names),
            "c_unscaled": len(stage_c_survivors),
            "d_unscaled": len(stage_d_unscaled),
            "d_scaled_estimate": len(stage_d_scaled_candidates),
        },
        "d_unscaled_breakdown_by_object_count": d_unscaled_by_count,
        "d_unscaled_breakdown_by_object_content": d_unscaled_by_content,
        "d_scaled_breakdown_by_object_count": d_scaled_by_count,
        "d_scaled_breakdown_by_object_content": d_scaled_by_content,
        "top10_d_unscaled_by_events": sorted(
            ((bn, info["n_events"], info["n_nonempty_bins"]) for bn, info in stage_d_unscaled.items()),
            key=lambda kv: -kv[1],
        )[:10],
    }
    Path(args.out).write_text(json.dumps(result, indent=2))
    print(json.dumps(result["funnel"], indent=2))
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
