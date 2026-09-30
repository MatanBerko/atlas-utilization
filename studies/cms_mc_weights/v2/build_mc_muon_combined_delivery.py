#!/usr/bin/env python
"""
CMS MC weights task v2 -- MC delivery builder.

Mirrors studies/cms_datasets/deliver/build_muon_combined_delivery.py's own
pooling rule exactly (Matan's decision, unchanged): per signature, pool
DoubleMuon's INCLUSIVE population with SingleMuon's EXCLUSIVE population.
Applied here to the NEW --is-mc-only shards
(dataset_shard_nonjet4_{inclusive,exclusive}.sqlite +
dataset_shard_nonjet4_weights_{inclusive,exclusive}.sqlite) that
run_dataset_on_file.py --is-mc writes -- never the data shards, never
mixed with them.

MC does NOT run its own peak-finding/splitting/cropping (v2 task's own
explicit instruction): for every one of the 159 nonjet4 min26bins
delivered histogram names, this script fills MC with EXACTLY that
histogram's own recorded bin-edge window
(first_filled_bin_low_edge_gev/last_filled_bin_high_edge_gev, read from
the already-delivered, read-only manifest) -- the data merge's own
recorded post-processing decision, reproduced from the delivered
artifact itself, exactly as phase-1's merge_full_v2_mc.py already
established for the phase-1 delivery. A bumpnet name with no manifest
entry is a genuine MC-only category (listed separately, raw count only,
never written as a histogram).

Per-event weight: genWeight * L1PreFiringWeight_Nom * sigma_eff[pb] *
1000 * 16.393 / Sigma_genWeight, sigma_eff from cms_mc_normalisation.json
(an unknown record id is a hard error), Sigma_genWeight aggregated over
the Runs trees of exactly the files that pass this script's own bad-file
policy (see below) -- both DoubleMuon-run and SingleMuon-run job_metadata
for the SAME physical file carry IDENTICAL mc_runs_tree_sums_this_file /
mc_sum_genweight_all_events_this_file (both computed from the full,
pre-any-cut Events tree of that one file, independent of --dataset-label)
-- asserted equal here as a cheap consistency check, then either one used.

Bad-file policy (v2 task's own spec): any file whose full-Events
Sigma genWeight disagrees with its own Runs genEventSumw by more than
1e-6 relative is EXCLUDED from both the numerator (its mass/weight rows
are dropped entirely, from both DoubleMuon and SingleMuon) and the
denominator (Sigma_genWeight) -- listed explicitly in the summary, never
silently absorbed.

Usage:
    python build_mc_muon_combined_delivery.py \
        --record-id 35669 --n-files 41 \
        --jobs-base /storage/.../work/cms_mc_v2/35669 \
        --manifest studies/cms_datasets/deliver/committed/muon_combined_nonjet4/manifest_muon_combined_matched_nonjet4_min26bins.json \
        --normalisation studies/cms_mc_weights/cms_mc_normalisation.json \
        --lumi-fb 16.393 \
        --out-dir studies/cms_mc_weights/v2/35669
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

import numpy as np  # noqa: E402
import uproot  # noqa: E402

from services.storage.sqlite_shards import list_signatures, iter_arrays_for_signature  # noqa: E402
from studies.cms_coverage.cluster.merge_and_count import SIG_PATTERN  # noqa: E402
from studies.m0m1j0_cms.histograms import (  # noqa: E402
    _convert_to_bumpnet_name,
    make_fixed_grid_histogram,
    to_writable_th1f,
    verify_written_th1f,
    BIN_WIDTH_GEV,
    FIXED_MASS_MIN_GEV,
    FIXED_MASS_MAX_GEV,
)

BAD_FILE_REL_TOL = 1e-6


def load_manifest(path: Path) -> dict:
    entries = json.loads(path.read_text(encoding="utf-8"))
    return {e["name"]: e for e in entries}


def load_job(jobs_base: Path, label: str, file_index: int):
    d = jobs_base / label / f"job_{file_index}"
    meta_path = d / "job_metadata.json"
    if not meta_path.exists():
        return None
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    return {"dir": d, "meta": meta}


def build_full_grid_edges():
    n_bins = round((FIXED_MASS_MAX_GEV - FIXED_MASS_MIN_GEV) / BIN_WIDTH_GEV)
    return np.linspace(FIXED_MASS_MIN_GEV, FIXED_MASS_MAX_GEV, n_bins + 1)


def crop_to_window(full_values, full_edges, full_sumw2, low_edge, high_edge):
    first_idx = int(round((low_edge - FIXED_MASS_MIN_GEV) / BIN_WIDTH_GEV))
    last_idx_exclusive = int(round((high_edge - FIXED_MASS_MIN_GEV) / BIN_WIDTH_GEV))
    first_idx = max(0, first_idx)
    last_idx_exclusive = min(len(full_values), last_idx_exclusive)
    return (
        full_values[first_idx:last_idx_exclusive],
        full_edges[first_idx:last_idx_exclusive + 1],
        full_sumw2[first_idx:last_idx_exclusive],
    )


def load_shard_pooled(mass_shard_path: Path, weights_shard_path: Path):
    """Returns {bumpnet_name: {"mass": arr, "weight_raw": (N,2) arr}} for
    one shard pair (mass + its aligned MC weights shard)."""
    out = {}
    if not mass_shard_path.exists():
        return out
    for sig in list_signatures(str(mass_shard_path)):
        m = SIG_PATTERN.search(sig)
        if not m:
            continue
        fs_str, im_str = m.groups()
        bumpnet_name = _convert_to_bumpnet_name(fs_str, im_str)
        mass_chunks = list(iter_arrays_for_signature(str(mass_shard_path), sig))
        weight_chunks = list(iter_arrays_for_signature(str(weights_shard_path), sig))
        if not mass_chunks:
            continue
        mass = np.concatenate(mass_chunks).astype(np.float64)
        weight_raw = np.concatenate(weight_chunks, axis=0) if weight_chunks else np.zeros((0, 2))
        assert weight_raw.shape[0] == mass.shape[0], (
            f"{sig}: mass/weight row count mismatch ({mass.shape[0]} vs {weight_raw.shape[0]})"
        )
        if bumpnet_name in out:
            out[bumpnet_name]["mass"] = np.concatenate([out[bumpnet_name]["mass"], mass])
            out[bumpnet_name]["weight_raw"] = np.concatenate([out[bumpnet_name]["weight_raw"], weight_raw], axis=0)
        else:
            out[bumpnet_name] = {"mass": mass, "weight_raw": weight_raw}
    return out


def merge_pooled(a: dict, b: dict) -> dict:
    out = dict(a)
    for name, d in b.items():
        if name in out:
            out[name] = {
                "mass": np.concatenate([out[name]["mass"], d["mass"]]),
                "weight_raw": np.concatenate([out[name]["weight_raw"], d["weight_raw"]], axis=0),
            }
        else:
            out[name] = d
    return out


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--record-id", required=True)
    p.add_argument("--n-files", type=int, required=True)
    p.add_argument("--jobs-base", required=True)
    p.add_argument("--manifest", default="studies/cms_datasets/deliver/committed/muon_combined_nonjet4/manifest_muon_combined_matched_nonjet4_min26bins.json")
    p.add_argument("--normalisation", default="studies/cms_mc_weights/cms_mc_normalisation.json")
    p.add_argument("--lumi-fb", type=float, default=16.393)
    p.add_argument("--out-dir", required=True)
    args = p.parse_args()

    record_id = str(args.record_id)
    jobs_base = Path(args.jobs_base)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    normalisation = json.loads(Path(args.normalisation).read_text(encoding="utf-8"))
    if record_id not in normalisation:
        raise KeyError(f"record {record_id} not found in {args.normalisation} -- unknown MC sample, refusing to guess a weight.")
    entry = normalisation[record_id]
    sigma_eff_pb = entry["cross_section_pb"]

    manifest = load_manifest(Path(args.manifest))

    # --- discover files, per-file bookkeeping, bad-file policy ---
    n_files_present = 0
    n_files_missing = []
    bad_files = []
    good_files = []  # list of (file_index, genEventSumw_this_file)
    total_genEventSumw = 0.0

    for i in range(args.n_files):
        dm = load_job(jobs_base, "DoubleMuon", i)
        sm = load_job(jobs_base, "SingleMuon", i)
        if dm is None or sm is None:
            n_files_missing.append(i)
            continue
        n_files_present += 1

        dm_sums = dm["meta"]["mc_runs_tree_sums_this_file"]
        sm_sums = sm["meta"]["mc_runs_tree_sums_this_file"]
        dm_full_gw = dm["meta"]["mc_sum_genweight_all_events_this_file"]
        sm_full_gw = sm["meta"]["mc_sum_genweight_all_events_this_file"]
        assert dm_sums["genEventSumw"] == sm_sums["genEventSumw"] and dm_full_gw == sm_full_gw, (
            f"file {i}: DoubleMuon-run and SingleMuon-run per-file MC bookkeeping disagree for the "
            f"SAME physical file (should be identical, both computed pre-any-cut) -- "
            f"dm={dm_sums['genEventSumw']!r}/{dm_full_gw!r} sm={sm_sums['genEventSumw']!r}/{sm_full_gw!r}"
        )
        genEventSumw_this_file = dm_sums["genEventSumw"]
        rel_diff = abs(dm_full_gw - genEventSumw_this_file) / abs(genEventSumw_this_file) if genEventSumw_this_file != 0 else float("nan")

        if rel_diff > BAD_FILE_REL_TOL:
            bad_files.append({
                "file_index": i, "file_url": dm["meta"]["file_url"],
                "sum_genweight_all_events": dm_full_gw,
                "genEventSumw_runs_tree": genEventSumw_this_file,
                "relative_difference": rel_diff,
            })
            continue

        good_files.append(i)
        total_genEventSumw += genEventSumw_this_file

    per_file_norm = sigma_eff_pb * 1000.0 * args.lumi_fb / total_genEventSumw
    print(f"files present={n_files_present}/{args.n_files}, missing={n_files_missing}, "
          f"bad(excluded)={[b['file_index'] for b in bad_files]}, "
          f"good(used)={len(good_files)}, Sigma_genEventSumw(used)={total_genEventSumw}, "
          f"per_file_norm(excl genWeight*L1)={per_file_norm}", flush=True)

    # --- pool mass+weight per bumpnet name, DoubleMuon-inclusive + SingleMuon-exclusive, GOOD files only ---
    pooled: dict = {}
    for i in good_files:
        dm_dir = jobs_base / "DoubleMuon" / f"job_{i}"
        sm_dir = jobs_base / "SingleMuon" / f"job_{i}"
        dm_pooled = load_shard_pooled(
            dm_dir / "dataset_shard_nonjet4_inclusive.sqlite",
            dm_dir / "dataset_shard_nonjet4_weights_inclusive.sqlite",
        )
        sm_pooled = load_shard_pooled(
            sm_dir / "dataset_shard_nonjet4_exclusive.sqlite",
            sm_dir / "dataset_shard_nonjet4_weights_exclusive.sqlite",
        )
        pooled = merge_pooled(pooled, dm_pooled)
        pooled = merge_pooled(pooled, sm_pooled)

    # --- fill each manifest histogram with MC's own weighted content, data's own window ---
    full_edges = build_full_grid_edges()
    written = {}
    mc_only_categories = {}
    raw_count_flags_below_100 = []

    for bumpnet_name, d in pooled.items():
        mass = d["mass"]
        weight_raw = d["weight_raw"]  # (N,2): genWeight, L1PreFiringWeight_Nom
        n_raw_total = int(mass.size)

        if bumpnet_name not in manifest:
            mc_only_categories[bumpnet_name] = n_raw_total
            continue

        entry_m = manifest[bumpnet_name]
        low = entry_m["first_filled_bin_low_edge_gev"]
        high = entry_m["last_filled_bin_high_edge_gev"]

        in_window = (mass >= low) & (mass < high)
        n_raw_in_window = int(in_window.sum())
        if n_raw_in_window < 100:
            raw_count_flags_below_100.append({"name": bumpnet_name, "n_raw_in_window": n_raw_in_window})

        weight = weight_raw[in_window, 0] * weight_raw[in_window, 1] * per_file_norm
        full_values, edges_check, full_sumw2 = make_fixed_grid_histogram(mass[in_window], weights=weight)
        assert np.array_equal(edges_check, full_edges)

        cropped_values, cropped_edges, cropped_sumw2 = crop_to_window(full_values, full_edges, full_sumw2, low, high)
        written[bumpnet_name] = {
            "values": cropped_values, "edges": cropped_edges, "sumw2": cropped_sumw2,
            "n_raw_in_window": n_raw_in_window, "n_raw_total": n_raw_total,
            "data_window_low_gev": low, "data_window_high_gev": high,
            "sum_of_weights_this_histogram": float(cropped_values.sum()),
        }

    root_path = out_dir / f"{record_id}_mc_nonjet4.root"
    verify_expected = {}
    with uproot.recreate(str(root_path)) as f:
        for name, info in written.items():
            key = f"ROI_{name}_width_{int(BIN_WIDTH_GEV)}"
            f[key] = to_writable_th1f(info["values"], info["edges"], key, sumw2=info["sumw2"])
            verify_expected[key] = info["values"]
    verify_written_th1f(str(root_path), verify_expected)
    print(f"wrote {root_path}: {len(written)} histogram(s), verified TH1F", flush=True)

    summary = {
        "record_id": record_id,
        "sigma_eff_pb": sigma_eff_pb,
        "target_luminosity_fb": args.lumi_fb,
        "n_files_expected": args.n_files,
        "n_files_present": n_files_present,
        "n_files_missing": n_files_missing,
        "n_files_bad_excluded": len(bad_files),
        "bad_files": bad_files,
        "n_files_used_in_denominator": len(good_files),
        "sum_genEventSumw_used": total_genEventSumw,
        "per_file_normalization_factor": per_file_norm,
        "n_histograms_written": len(written),
        "histograms_written": {
            k: {kk: vv for kk, vv in v.items() if kk not in ("values", "edges", "sumw2")}
            for k, v in written.items()
        },
        "n_mc_only_categories_not_written": len(mc_only_categories),
        "mc_only_categories": mc_only_categories,
        "raw_count_flags_below_100": raw_count_flags_below_100,
        "root_path": str(root_path),
    }
    (out_dir / "mc_delivery_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"wrote {out_dir / 'mc_delivery_summary.json'}", flush=True)


if __name__ == "__main__":
    main()
