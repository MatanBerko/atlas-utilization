#!/usr/bin/env python
"""
Per-dataset funnel measurement WITH full histogram name lists, for one
dataset's single-file SQLite shard produced by
studies/cms_coverage/per_dataset/triggered/cluster/run_per_dataset_on_file.py.

Builds on studies/cms_coverage/per_dataset/cluster/measure_per_dataset_funnel.py
(same real, unmodified shared post-processing functions, same funnel
stage definitions -- see that module's own docstring for the exact
algorithm). The ONE change: this version writes out the COMPLETE list of
surviving histogram names at stage (b) and stage (d) -- not a top-10 --
each with its (unscaled) event count and, at stage (d), its bin count.
This is what a later, purely-local name-level union/overlap computation
needs; the previous script only kept a top-10, which is why this task
exists.

Name lists are UNSCALED (directly measured on the one file): scaling is
an arithmetic estimate applied to COUNTS (see the non-full-list script's
own docstring for why), not something that can produce a trustworthy
per-name list on its own -- only the unscaled names are real,
measured survivors.

Usage:
    python measure_per_dataset_funnel.py \
        --shard /storage/.../job_SingleMuon/coverage_shard.sqlite \
        --dataset-label SingleMuon --scale-factor 50.9959 \
        --out /storage/.../funnel_SingleMuon.json \
        --names-out /storage/.../names_SingleMuon.json
"""
from __future__ import annotations

import argparse
import json
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
from studies.m0m1j0_cms.histograms import _convert_to_bumpnet_name  # noqa: E402
from studies.cms_coverage.cluster.merge_and_count import (  # noqa: E402
    SIG_PATTERN,
    MIN_BUMPNET_BINS,
    MIN_BUMPNET_EVENTS,
    fixed_grid_histogram,
    object_count,
    object_content_category,
    copy_shards,
    load_chunks_by_signature,
)
from studies.cms_coverage.per_dataset.cluster.measure_per_dataset_funnel import (  # noqa: E402
    read_final_state_populations,
    run_chain,
)

import logging
logging.basicConfig(level=logging.WARNING)
LOGGER = logging.getLogger("per_dataset_funnel_triggered")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--shard", required=True)
    p.add_argument("--dataset-label", required=True)
    p.add_argument("--scale-factor", type=float, required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--names-out", required=True)
    args = p.parse_args()

    shard_path = args.shard
    scale = args.scale_factor

    sig_to_bumpnet = {}
    for sig in list_signatures(shard_path):
        m = SIG_PATTERN.search(sig)
        if not m:
            continue
        fs_str, im_str = m.groups()
        bn = _convert_to_bumpnet_name(fs_str, im_str)
        sig_to_bumpnet[sig] = (bn, fs_str, im_str)

    stage_a_names = set(bn for bn, _fs, _im in sig_to_bumpnet.values())

    fs_population = read_final_state_populations(shard_path)

    # ---- stage (b) unscaled: real prune, on a scratch copy ----
    with tempfile.TemporaryDirectory(prefix=f"pd_funnel_{args.dataset_label}_") as tmp:
        copy = copy_shards([shard_path], Path(tmp))
        prune_final_states_below_min_events(copy, MIN_BUMPNET_EVENTS)
        chunks_unscaled = load_chunks_by_signature(copy)
    stage_b_unscaled_names = set(
        sig_to_bumpnet[sig][0] for sig in chunks_unscaled if sig in sig_to_bumpnet
    )

    # ---- stage (b) scaled: population x scale >= 100, arithmetic only (count only, no name list) ----
    fs_scaled_survives = {fs: (pop * scale >= MIN_BUMPNET_EVENTS) for fs, pop in fs_population.items()}
    stage_b_scaled_names = set()
    for sig, (bn, fs_str, im_str) in sig_to_bumpnet.items():
        if fs_scaled_survives.get(fs_str, False):
            stage_b_scaled_names.add(bn)

    # ---- raw event counts per bumpnet name at stage (b), for the saved name list ----
    b_raw_events_by_name: dict[str, int] = {}
    for sig, chunks in chunks_unscaled.items():
        if sig not in sig_to_bumpnet:
            continue
        bn = sig_to_bumpnet[sig][0]
        n = sum(int(c.size) for c in chunks)
        b_raw_events_by_name[bn] = b_raw_events_by_name.get(bn, 0) + n

    # ---- stage (c) + (d) unscaled: real chain on (b)-unscaled survivors ----
    all_chunks = load_chunks_by_signature([shard_path])
    stage_c_survivors = {}
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

    stage_d_unscaled = {}
    for bn, (main_arr, im_str) in stage_c_survivors.items():
        hist = fixed_grid_histogram(main_arr)
        n_nonempty = int(np.count_nonzero(hist))
        n_events = int(hist.sum())
        if n_nonempty > MIN_BUMPNET_BINS and n_events >= MIN_BUMPNET_EVENTS:
            stage_d_unscaled[bn] = {"n_events": n_events, "n_nonempty_bins": n_nonempty, "im_str": im_str}

    # ---- stage (d) scaled ESTIMATE (count only, as before) ----
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

    # ---- FULL name lists (the point of this script) ----
    names_result = {
        "dataset_label": args.dataset_label,
        "stage_b_unscaled_names": {
            bn: {"n_events": b_raw_events_by_name.get(bn, None)}
            for bn in sorted(stage_b_unscaled_names)
        },
        "stage_d_unscaled_names": {
            bn: {"n_events": info["n_events"], "n_nonempty_bins": info["n_nonempty_bins"]}
            for bn, info in sorted(stage_d_unscaled.items())
        },
    }
    Path(args.names_out).write_text(json.dumps(names_result, indent=2))

    print(json.dumps(result["funnel"], indent=2))
    print(f"wrote {args.out} and {args.names_out} "
          f"(stage_b names: {len(stage_b_unscaled_names)}, stage_d names: {len(stage_d_unscaled)})")


if __name__ == "__main__":
    main()
