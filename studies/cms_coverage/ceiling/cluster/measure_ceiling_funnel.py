#!/usr/bin/env python
"""
Ceiling-task funnel measurement WITH full histogram name lists, for one
config x dataset's single-file SQLite shard produced by
studies/cms_coverage/ceiling/cluster/run_ceiling_on_file.py.

Byte-for-byte the same real, unmodified funnel/threshold logic as
studies/cms_coverage/per_dataset/triggered/cluster/measure_per_dataset_funnel.py
(same imports, same stage a/b/c/d definitions, same MIN_BUMPNET_EVENTS/
MIN_BUMPNET_BINS thresholds) -- this file exists only because that script's
own REPO_ROOT depth assumption (parents[5]) doesn't match this new
directory's depth, and because object_count/object_content_category (from
merge_and_count.py) only know about the 4 ATLAS-style letters; both are
handled below without touching either shared/prior function.

Usage:
    python measure_ceiling_funnel.py \
        --shard /storage/.../job_SingleMuon_C1/coverage_shard.sqlite \
        --dataset-label SingleMuon --scale-factor 50.9959 \
        --out /storage/.../funnel_C1_SingleMuon.json \
        --names-out /storage/.../names_C1_SingleMuon.json
"""
from __future__ import annotations

import argparse
import json
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
    copy_shards,
    load_chunks_by_signature,
)
from studies.cms_coverage.per_dataset.cluster.measure_per_dataset_funnel import (  # noqa: E402
    read_final_state_populations,
    run_chain,
)

import logging
import re
logging.basicConfig(level=logging.WARNING)
LOGGER = logging.getLogger("ceiling_funnel")

# Object-count/content-category, extended for Photons/Taus/MET. NOT a call
# to studies.cms_coverage.cluster.merge_and_count's object_count/
# object_content_category with different parameters -- those two take only
# an im_str, with no parameter to widen the letter set their module-level
# IM_PARTICLE_PATTERN = re.compile(r"([emjb])(\d+)") matches, and that
# regex silently returns zero matches (undercounting) for any im_str
# containing a photon ('g') or tau ('t') letter, which every C2+ config
# produces -- so this genuinely cannot be done by "calling the shared
# function with different parameters" and is new code instead, per this
# task's own instruction for that case. Category labels for the original
# 4 types (b-jet-containing/lepton+jet/lepton-only/jet-only/other) are kept
# identical to the shared function's own strings for cross-config
# comparability.
#
# The "met" suffix run_ceiling_on_file.py appends to a +MET variant's
# signature (see that file's own comment) is stripped first: it is 3
# literal letters with no digit, so bare "t" in im_str would otherwise
# false-positive tau-detection on every MET variant via the trailing "t"
# in "met" itself.
IM_PARTICLE_PATTERN_6TYPE = re.compile(r"([emjgtb])(\d+)")


def _strip_met_suffix(im_str: str):
    if im_str.endswith("met"):
        return im_str[:-3], True
    return im_str, False


def object_count(im_str: str) -> int:
    base_im, has_met = _strip_met_suffix(im_str)
    n = len(IM_PARTICLE_PATTERN_6TYPE.findall(base_im))
    return n + (1 if has_met else 0)


def object_content_category(im_str: str) -> str:
    base_im, has_met = _strip_met_suffix(im_str)
    letters = set(letter for letter, _rank in IM_PARTICLE_PATTERN_6TYPE.findall(base_im))
    has_b = "b" in letters
    has_j = "j" in letters
    has_lepton = ("e" in letters) or ("m" in letters)
    has_photon = "g" in letters
    has_tau = "t" in letters
    if has_met:
        return "met_variant"
    if has_photon and has_tau:
        return "photon_and_tau"
    if has_photon:
        return "photon_containing"
    if has_tau:
        return "tau_containing"
    if has_b:
        return "b-jet-containing"
    if has_lepton and has_j:
        return "lepton+jet"
    if has_lepton:
        return "lepton-only"
    if has_j:
        return "jet-only"
    return "other"


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

    with tempfile.TemporaryDirectory(prefix=f"ceiling_funnel_{args.dataset_label}_") as tmp:
        copy = copy_shards([shard_path], Path(tmp))
        prune_final_states_below_min_events(copy, MIN_BUMPNET_EVENTS)
        chunks_unscaled = load_chunks_by_signature(copy)
    stage_b_unscaled_names = set(
        sig_to_bumpnet[sig][0] for sig in chunks_unscaled if sig in sig_to_bumpnet
    )

    fs_scaled_survives = {fs: (pop * scale >= MIN_BUMPNET_EVENTS) for fs, pop in fs_population.items()}
    stage_b_scaled_names = set()
    for sig, (bn, fs_str, im_str) in sig_to_bumpnet.items():
        if fs_scaled_survives.get(fs_str, False):
            stage_b_scaled_names.add(bn)

    b_raw_events_by_name: dict[str, int] = {}
    for sig, chunks in chunks_unscaled.items():
        if sig not in sig_to_bumpnet:
            continue
        bn = sig_to_bumpnet[sig][0]
        n = sum(int(c.size) for c in chunks)
        b_raw_events_by_name[bn] = b_raw_events_by_name.get(bn, 0) + n

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
