#!/usr/bin/env python
"""
Phase-1 MC weights task -- MC merge (amendments A2, A5).

Reads every per-job mc_combinations.npz + job_metadata.json
(run_m0m1j0_on_mc_file_v2.py's output) for one sample, and:

A5: Sigma genWeight = Runs-tree genEventSumw summed over exactly the
files that were processed successfully, via fork master's existing,
UNMODIFIED aggregate_sumw_for_processed_files()
(services/parsing/mc_weights.py:173-226) -- called with an INJECTED
reader (that function's own `reader` parameter, designed for exactly
this) that returns each file's ALREADY-READ Runs-tree sums from its own
job_metadata.json, instead of re-opening the ROOT file a second time
over the network. Any file whose job directory is missing or whose
job_metadata.json cannot be read is a hard failure of the injected
reader for that URL -- aggregate_sumw_for_processed_files' own
try/except-and-collect-failures logic (mc_weights.py:201-218) then
surfaces it in its raised RuntimeError, listing every such failure
together -- never silently absorbed.

A2: MC does NOT run its own z-peak/max-mass/peak-removal/first-empty-bin
post-processing. For every BumpNet histogram name this sample's combined
MC output has ANY entries for, this script looks up that EXACT name in
the delivered DoubleMuon manifest (origin/deliver/doublemuon-bumpnet
:studies/cms_coverage/deliver/committed/manifest_min26bins.json, read via
`git show`, cached locally as evidence/deliver_manifest_min26bins.json.gz)
and recovers data's own post-processing decision as the manifest's own
`first_filled_bin_low_edge_gev`/`last_filled_bin_high_edge_gev` -- i.e.
the exact mass WINDOW data's peak-removal + first-empty-bin split ended
up keeping for that category (this is the data merge's own RECORDED
outcome, not a re-derivation of the peak-finding algorithm). A MC event's
raw mass is kept only if it falls in that exact window -- the same
boundary decision data made, reproduced from the delivered artifact
itself. If a name is NOT in the manifest at all, it is a genuine
MC-only category (listed separately, with its raw count, never written
as a histogram this run).

Per DESIGN.md Sec 2 / this task's own formula:
    weight = genWeight * L1PreFiringWeight_Nom * sigma_eff[pb] * 1000 * L[fb^-1] / Sigma genWeight

Usage:
    python merge_full_v2_mc.py \
        --record-id 67801 --jobs-base /storage/.../work/cms_mc_phase1/67801 \
        --n-files 49 --normalisation studies/cms_mc_weights/cms_mc_normalisation.json \
        --manifest studies/cms_mc_weights/evidence/deliver_manifest_min26bins.json.gz \
        --lumi-fb 16.393 \
        --out-dir studies/cms_mc_weights/phase1/67801
"""
from __future__ import annotations

import argparse
import gzip
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

import numpy as np  # noqa: E402
import uproot  # noqa: E402

from services.parsing.mc_weights import aggregate_sumw_for_processed_files  # noqa: E402
from studies.m0m1j0_cms.histograms import (  # noqa: E402
    make_fixed_grid_histogram, to_writable_th1f, verify_written_th1f,
    FIXED_MASS_MIN_GEV, FIXED_MASS_MAX_GEV, BIN_WIDTH_GEV,
)

sys.path.insert(0, str(REPO_ROOT / "studies" / "cms_mc_weights" / "phase1"))
from build_weights_registry import CMSWeightsRegistry  # noqa: E402


def load_manifest(path: Path) -> dict:
    """{bumpnet_name: entry} from the saved delivered-manifest excerpt."""
    opener = gzip.open if str(path).endswith(".gz") else open
    with opener(path, "rt", encoding="utf-8") as f:
        data = json.load(f)
    entries = data if isinstance(data, list) else data.get("all_m0m1_bjet_entries") or data.get("entries") or data
    if isinstance(entries, dict):
        # already {name: entry}
        return entries
    return {e["name"]: e for e in entries}


def discover_jobs(jobs_base: Path, n_files: int):
    """Returns (present_job_dirs: {file_index: Path}, missing: [file_index])."""
    present = {}
    missing = []
    for i in range(n_files):
        d = jobs_base / f"job_{i}"
        meta = d / "job_metadata.json"
        npz = d / "mc_combinations.npz"
        if meta.exists() and npz.exists():
            present[i] = d
        else:
            missing.append(i)
    return present, missing


def make_runs_sums_reader(job_dirs_by_url: dict):
    """Injected reader for aggregate_sumw_for_processed_files (A5): returns
    the ALREADY-READ Runs-tree sums recorded in each job's own
    job_metadata.json, keyed by file_url -- never re-opens the ROOT file."""
    def reader(file_url: str):
        job_dir = job_dirs_by_url.get(file_url)
        if job_dir is None:
            raise RuntimeError(f"no processed job directory recorded for URL {file_url}")
        meta = json.loads((job_dir / "job_metadata.json").read_text(encoding="utf-8"))
        sums = meta.get("runs_tree_sums_this_file")
        if sums is None:
            raise RuntimeError(f"job_metadata.json for {file_url} has no runs_tree_sums_this_file")
        return sums
    return reader


def load_all_combinations(present_job_dirs: dict) -> dict:
    """{bumpnet_name: {"mass": arr, "genWeight": arr, "l1_prefiring": arr}}
    concatenated across every present job."""
    out: dict = {}
    for file_index, job_dir in present_job_dirs.items():
        with np.load(job_dir / "mc_combinations.npz", allow_pickle=True) as npz:
            sig_names = list(npz["__signatures__"])
            for sig in sig_names:
                mass = npz[f"{sig}::mass"]
                gw = npz[f"{sig}::genWeight"]
                l1 = npz[f"{sig}::l1_prefiring"]
                if sig in out:
                    out[sig]["mass"] = np.concatenate([out[sig]["mass"], mass])
                    out[sig]["genWeight"] = np.concatenate([out[sig]["genWeight"], gw])
                    out[sig]["l1_prefiring"] = np.concatenate([out[sig]["l1_prefiring"], l1])
                else:
                    out[sig] = {"mass": mass, "genWeight": gw, "l1_prefiring": l1}
    return out


def build_full_grid_edges():
    n_bins = round((FIXED_MASS_MAX_GEV - FIXED_MASS_MIN_GEV) / BIN_WIDTH_GEV)
    return np.linspace(FIXED_MASS_MIN_GEV, FIXED_MASS_MAX_GEV, n_bins + 1)


def crop_to_window(full_values, full_edges, full_sumw2, low_edge, high_edge):
    """Crop a full-fixed-grid (values, edges, sumw2) triple down to the
    [low_edge, high_edge) bin window -- same convention as
    crop_bumpnet_root.py's own crop_arrays (bin-index slice, edges kept
    aligned to the original grid)."""
    first_idx = int(round((low_edge - FIXED_MASS_MIN_GEV) / BIN_WIDTH_GEV))
    last_idx_exclusive = int(round((high_edge - FIXED_MASS_MIN_GEV) / BIN_WIDTH_GEV))
    first_idx = max(0, first_idx)
    last_idx_exclusive = min(len(full_values), last_idx_exclusive)
    return (
        full_values[first_idx:last_idx_exclusive],
        full_edges[first_idx:last_idx_exclusive + 1],
        full_sumw2[first_idx:last_idx_exclusive],
    )


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--record-id", required=True)
    p.add_argument("--jobs-base", required=True)
    p.add_argument("--n-files", type=int, required=True)
    p.add_argument("--normalisation", default="studies/cms_mc_weights/cms_mc_normalisation.json")
    p.add_argument("--manifest", default="studies/cms_mc_weights/evidence/deliver_manifest_min26bins.json.gz")
    p.add_argument("--lumi-fb", type=float, default=16.393)
    p.add_argument("--out-dir", required=True)
    args = p.parse_args()

    record_id = str(args.record_id)
    jobs_base = Path(args.jobs_base)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    present, missing = discover_jobs(jobs_base, args.n_files)
    print(f"jobs present: {len(present)}/{args.n_files}; missing: {missing}", flush=True)

    # Recover each present job's own file_url (needed for the injected
    # A5 reader) from its own job_metadata.json.
    job_dirs_by_url = {}
    for i, job_dir in present.items():
        meta = json.loads((job_dir / "job_metadata.json").read_text(encoding="utf-8"))
        job_dirs_by_url[meta["file_url"]] = job_dir
    processed_urls = list(job_dirs_by_url.keys())

    reader = make_runs_sums_reader(job_dirs_by_url)
    try:
        agg = aggregate_sumw_for_processed_files(processed_urls, reader=reader)
    except RuntimeError as e:
        (out_dir / "merge_mc_summary.json").write_text(
            json.dumps({"complete": False, "error": str(e), "n_files_present": len(present),
                        "n_files_missing": len(missing), "missing_file_indices": missing}, indent=2),
            encoding="utf-8",
        )
        print(f"FATAL (A5 consistency rule): {e}", flush=True)
        sys.exit(1)

    sum_gen_weight = agg["genEventSumw"]
    print(f"Sigma genEventSumw over {agg['n_files_processed']} processed file(s): {sum_gen_weight}", flush=True)

    normalisation = json.loads(Path(args.normalisation).read_text(encoding="utf-8"))
    entry = normalisation[record_id]
    registry = CMSWeightsRegistry.build(
        {record_id: entry}, {record_id: sum_gen_weight}, target_luminosity_fb=args.lumi_fb,
    )
    per_file_weight = registry.weight_for(record_id)  # sigma_eff*1000*L / Sigma genWeight
    print(f"per-file normalization factor (excl. genWeight, L1 prefiring): {per_file_weight}", flush=True)

    combos = load_all_combinations(present)
    manifest = load_manifest(Path(args.manifest))

    full_edges = build_full_grid_edges()
    written = {}
    skipped_unreproducible = []
    mc_only_categories = {}
    raw_count_flags = []

    for bumpnet_name, d in combos.items():
        n_raw = len(d["mass"])
        if bumpnet_name not in manifest:
            mc_only_categories[bumpnet_name] = n_raw
            continue

        entry_manifest = manifest[bumpnet_name]
        low = entry_manifest.get("first_filled_bin_low_edge_gev")
        high = entry_manifest.get("last_filled_bin_high_edge_gev")
        if low is None or high is None:
            skipped_unreproducible.append({
                "name": bumpnet_name, "reason": "manifest entry has no recorded bin-edge window",
            })
            continue

        mass = d["mass"].astype(np.float64)
        gw = d["genWeight"]
        l1 = d["l1_prefiring"]

        in_window = (mass >= low) & (mass < high)
        n_raw_in_window = int(in_window.sum())
        if n_raw_in_window < 100:
            raw_count_flags.append({"name": bumpnet_name, "n_raw_in_window": n_raw_in_window})

        weight = gw[in_window] * l1[in_window] * per_file_weight
        full_values, edges_check, full_sumw2 = make_fixed_grid_histogram(mass[in_window], weights=weight)
        assert np.array_equal(edges_check, full_edges)

        cropped_values, cropped_edges, cropped_sumw2 = crop_to_window(full_values, full_edges, full_sumw2, low, high)

        written[bumpnet_name] = {
            "values": cropped_values, "edges": cropped_edges, "sumw2": cropped_sumw2,
            "n_raw_in_window": n_raw_in_window, "n_raw_total_all_categories_this_name": n_raw,
            "data_window_low_gev": low, "data_window_high_gev": high,
            "sum_of_weights_this_histogram": float(cropped_values.sum()),
        }

    root_path = out_dir / f"{record_id}_mc.root"
    verify_expected = {}
    with uproot.recreate(str(root_path)) as f:
        for name, info in written.items():
            key = f"ROI_{name}_width_{int(BIN_WIDTH_GEV)}"
            f[key] = to_writable_th1f(info["values"], info["edges"], key, sumw2=info["sumw2"])
            verify_expected[key] = info["values"]
    verify_written_th1f(str(root_path), verify_expected)
    print(f"wrote {root_path}: {len(written)} histogram(s), verified TH1F", flush=True)

    summary = {
        "complete": True,
        "record_id": record_id,
        "n_files_present": len(present), "n_files_missing": len(missing),
        "missing_file_indices": missing,
        "sum_genEventSumw": sum_gen_weight,
        "n_files_in_sumw_aggregation": agg["n_files_processed"],
        "cross_section_pb": entry["cross_section_pb"],
        "target_luminosity_fb": args.lumi_fb,
        "per_file_normalization_factor": per_file_weight,
        "n_histograms_written": len(written),
        "histograms_written": {
            k: {kk: (vv if not isinstance(vv, np.ndarray) else vv.tolist())
                for kk, vv in v.items() if kk not in ("values", "edges", "sumw2")}
            for k, v in written.items()
        },
        "n_mc_only_categories_not_written": len(mc_only_categories),
        "mc_only_categories": mc_only_categories,
        "n_skipped_unreproducible": len(skipped_unreproducible),
        "skipped_unreproducible": skipped_unreproducible,
        "raw_count_flags_below_100": raw_count_flags,
        "root_path": str(root_path),
    }
    (out_dir / "merge_mc_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"wrote {out_dir / 'merge_mc_summary.json'}", flush=True)


if __name__ == "__main__":
    main()
