#!/usr/bin/env python
"""
Diagnosis round -- D1: Z-peak normalisation test.

Builds dimuon-mass ("m0m1" combination) distributions BEFORE any
post-processing (no z-peak cut, no max-mass cut, no peak-removal, no
first-empty-bin split, no cropping -- this is the raw invariant-mass
population straight out of the shared selection+combinatorics code),
for:
  - data: read directly from the coverage_shard.sqlite files already on
    the cluster from the real DoubleMuon delivery production
    (studies/cms_coverage/cluster/run_coverage_on_file.py, records 30522
    [Run2016G] + 30555 [Run2016H], 57/57 files) -- NOT reprocessed here,
    only read;
  - MC (DY madgraphMLM [35671] + TTTo2L2Nu [67801]): read directly from
    the phase-1 mc_combinations.npz per-job files already on the cluster
    (studies/m0m1j0_cms/cluster/run_m0m1j0_on_mc_file_v2.py), weighted by
    genWeight * L1PreFiringWeight_Nom * per_file_normalization_factor
    (the SAME weight formula phase-1 validated, per_file_normalization_factor
    read from each sample's own merge_mc_summary.json -- not recomputed).

Both data and MC "m0m1" signatures come from the exact same shared
selection (>=2 muons, >=1 light jet -- see DIAGNOSIS.md D0) and the exact
same shared combinatorics code (services.calculations.combinatorics /
im_calculator / physics_calcs, services.pipelines.im_pipeline), so the
0-light-jet bin is expected to be structurally EMPTY on both sides (D0's
finding), not a gap in this script.

Final-state label -> jet count / b-jet count is parsed directly from the
signature/bumpnet-name string (both sides use the identical
"..._NjJx_..._NbBx" convention, produced by the same shared code), no
re-derivation of the selection logic itself.

Writes d1_zpeak_result.json and d1_zpeak_inclusive.png under
studies/cms_mc_weights/phase1/diagnosis/.
"""
from __future__ import annotations

import glob
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT))

import numpy as np  # noqa: E402
import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from services.storage.sqlite_shards import list_signatures, iter_arrays_for_signature  # noqa: E402

DATA_SHARD_BASE = "/storage/agrp/berkom/atlas-utilization/output/cms_coverage_full"
MC_WORK_BASE = "/storage/agrp/berkom/atlas-utilization/work/cms_mc_phase1"
MC_SAMPLES = {"35671": ("DYJetsToLL_M-50_madgraphMLM", 61), "67801": ("TTTo2L2Nu", 49)}

Z_LO, Z_HI = 60.0, 120.0
NARROW_LO, NARROW_HI = 76.0, 106.0
BIN_WIDTH = 1.0
N_BINS = int(round((Z_HI - Z_LO) / BIN_WIDTH))
EDGES = np.linspace(Z_LO, Z_HI, N_BINS + 1)

LABEL_RE = re.compile(r"_FS_([0-9a-z_]+)_IM_m0m1$")
# Matches BOTH the raw data shard label convention (e.g. "0e_2m_1j_0g_0t_0b",
# no trailing 'x', jet/b-jet counts NOT capped at 4) and the MC driver's
# bumpnet-name convention (e.g. "..._0ex_2mx_1jx_0gx_0tx_0bx", trailing 'x',
# capped at 4 by limit_particles_in_fs) -- confirmed directly by reading one
# real coverage_shard.sqlite's actual signatures (raw, uncapped format) vs
# one real mc_combinations.npz's actual signature names (bumpnet format).
NJ_RE = re.compile(r"_(\d+)jx?(?:_|$)")
NB_RE = re.compile(r"_(\d+)bx?(?:_|$)")
NM_RE = re.compile(r"_(\d+)mx?(?:_|$)")


def jet_bucket(n: int) -> str:
    return str(n) if n < 3 else ">=3"


def bjet_bucket(n: int) -> str:
    return str(n) if n < 1 else ">=1"


def parse_label(label: str):
    nj = NJ_RE.search(label)
    nb = NB_RE.search(label)
    nm = NM_RE.search(label)
    return (
        int(nj.group(1)) if nj else None,
        int(nb.group(1)) if nb else None,
        int(nm.group(1)) if nm else None,
    )


def load_data():
    """Returns list of (mass_array, label) from every 'IM_m0m1' signature in
    every coverage_shard.sqlite -- raw, pre-postprocessing masses."""
    job_dirs = sorted(glob.glob(f"{DATA_SHARD_BASE}/job_*/"))
    records = []
    n_jobs_read = 0
    n_jobs_missing = 0
    for jd in job_dirs:
        db = Path(jd, "coverage_shard.sqlite")
        if not db.is_file():
            n_jobs_missing += 1
            continue
        n_jobs_read += 1
        sigs = [s for s in list_signatures(str(db)) if s.endswith("_IM_m0m1")]
        for sig in sigs:
            m = LABEL_RE.search(sig)
            label = m.group(1) if m else "UNKNOWN"
            for chunk in iter_arrays_for_signature(str(db), sig):
                records.append((chunk.astype(np.float64), label))
    return records, n_jobs_read, n_jobs_missing


def load_mc():
    """Returns dict record_id -> (list of (mass, genWeight, l1_prefiring,
    label) tuples, per_file_normalization_factor, n_files_expected,
    n_files_found)."""
    out = {}
    for rid, (name, n_expected) in MC_SAMPLES.items():
        summary_path = REPO_ROOT / "studies/cms_mc_weights/phase1" / rid / "merge_mc_summary.json"
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        norm = summary["per_file_normalization_factor"]

        job_dirs = sorted(
            glob.glob(f"{MC_WORK_BASE}/{rid}/job_*/"),
            key=lambda p: int(p.rstrip("/").rsplit("_", 1)[1]),
        )
        recs = []
        n_found = 0
        for jd in job_dirs:
            npz_path = Path(jd, "mc_combinations.npz")
            if not npz_path.is_file():
                continue
            n_found += 1
            npz = np.load(npz_path, allow_pickle=True)
            sig_names = [s for s in npz["__signatures__"] if s.startswith("mass_m0m1_cat_")]
            for sig in sig_names:
                mass = npz[f"{sig}::mass"].astype(np.float64)
                gw = npz[f"{sig}::genWeight"].astype(np.float64)
                l1 = npz[f"{sig}::l1_prefiring"].astype(np.float64)
                recs.append((mass, gw, l1, sig))
        out[rid] = {
            "name": name, "records": recs, "per_file_normalization_factor": norm,
            "n_files_expected": n_expected, "n_files_found": n_found,
        }
    return out


def main():
    out_dir = REPO_ROOT / "studies/cms_mc_weights/phase1/diagnosis"
    out_dir.mkdir(parents=True, exist_ok=True)

    data_records, n_data_jobs_read, n_data_jobs_missing = load_data()
    mc_data = load_mc()

    # --- bucket data by (jet, bjet) ---
    categories = {
        "inclusive": lambda nj, nb: True,
        "jet_0": lambda nj, nb: nj == 0,
        "jet_1": lambda nj, nb: nj == 1,
        "jet_2": lambda nj, nb: nj == 2,
        "jet_ge3": lambda nj, nb: nj is not None and nj >= 3,
        "bjet_0": lambda nj, nb: nb == 0,
        "bjet_ge1": lambda nj, nb: nb is not None and nb >= 1,
    }

    result = {
        "z_window_gev": [Z_LO, Z_HI],
        "narrow_window_gev": [NARROW_LO, NARROW_HI],
        "bin_width_gev": BIN_WIDTH,
        "n_data_jobs_read": n_data_jobs_read,
        "n_data_jobs_missing": n_data_jobs_missing,
        "mc_samples": {
            rid: {
                "name": d["name"],
                "n_files_expected": d["n_files_expected"],
                "n_files_found": d["n_files_found"],
                "per_file_normalization_factor": d["per_file_normalization_factor"],
            }
            for rid, d in mc_data.items()
        },
        "categories": {},
    }

    # Pre-parse all data labels once.
    data_parsed = [(mass, *parse_label(label)) for mass, label in data_records]
    # Pre-parse + pre-weight all MC records once (weight = genWeight * l1 * norm).
    mc_parsed = []
    for rid, d in mc_data.items():
        norm = d["per_file_normalization_factor"]
        for mass, gw, l1, sig in d["records"]:
            nj, nb, nm = parse_label(sig)
            weight = gw * l1 * norm
            mc_parsed.append((mass, weight, nj, nb, nm, rid))

    inclusive_data_hist = None
    inclusive_mc_hist = None
    inclusive_mc_sumw2 = None

    for cat_name, pred in categories.items():
        d_mass = np.concatenate(
            [m for m, nj, nb, nm in data_parsed if pred(nj, nb)]
        ) if any(pred(nj, nb) for _, nj, nb, _ in data_parsed) else np.array([])

        mc_mass_list, mc_w_list = [], []
        for mass, weight, nj, nb, nm, rid in mc_parsed:
            if pred(nj, nb):
                mc_mass_list.append(mass)
                mc_w_list.append(weight)
        mc_mass = np.concatenate(mc_mass_list) if mc_mass_list else np.array([])
        mc_w = np.concatenate(mc_w_list) if mc_w_list else np.array([])

        d_in_window = d_mass[(d_mass >= Z_LO) & (d_mass < Z_HI)]
        mc_in_window_mask = (mc_mass >= Z_LO) & (mc_mass < Z_HI)
        mc_w_in_window = mc_w[mc_in_window_mask]

        d_hist, _ = np.histogram(d_in_window, bins=EDGES)
        mc_hist, _ = np.histogram(mc_mass[mc_in_window_mask], bins=EDGES, weights=mc_w_in_window)
        mc_sumw2, _ = np.histogram(mc_mass[mc_in_window_mask], bins=EDGES, weights=mc_w_in_window ** 2)

        d_narrow = d_mass[(d_mass >= NARROW_LO) & (d_mass < NARROW_HI)]
        mc_narrow_mask = (mc_mass >= NARROW_LO) & (mc_mass < NARROW_HI)
        mc_w_narrow = mc_w[mc_narrow_mask]

        n_data_60_120 = int(d_in_window.size)
        n_mc_60_120 = float(mc_w_in_window.sum())
        n_mc_60_120_stat = float(np.sqrt((mc_w_in_window ** 2).sum()))
        n_data_narrow = int(d_narrow.size)
        n_mc_narrow = float(mc_w_narrow.sum())
        n_mc_narrow_stat = float(np.sqrt((mc_w_narrow ** 2).sum()))

        ratio_60_120 = (n_data_60_120 / n_mc_60_120) if n_mc_60_120 > 0 else None
        if ratio_60_120 is not None and n_data_60_120 > 0:
            rel_stat = (1.0 / np.sqrt(n_data_60_120)) + (n_mc_60_120_stat / n_mc_60_120 if n_mc_60_120 > 0 else 0)
            ratio_60_120_staterr = ratio_60_120 * rel_stat
        else:
            ratio_60_120_staterr = None

        ratio_narrow = (n_data_narrow / n_mc_narrow) if n_mc_narrow > 0 else None
        if ratio_narrow is not None and n_data_narrow > 0:
            rel_stat_n = (1.0 / np.sqrt(n_data_narrow)) + (n_mc_narrow_stat / n_mc_narrow if n_mc_narrow > 0 else 0)
            ratio_narrow_staterr = ratio_narrow * rel_stat_n
        else:
            ratio_narrow_staterr = None

        result["categories"][cat_name] = {
            "n_data_events_60_120": n_data_60_120,
            "n_mc_weighted_60_120": n_mc_60_120,
            "n_mc_weighted_stat_err_60_120": n_mc_60_120_stat,
            "data_over_mc_60_120": ratio_60_120,
            "data_over_mc_60_120_stat_err": ratio_60_120_staterr,
            "n_data_events_76_106": n_data_narrow,
            "n_mc_weighted_76_106": n_mc_narrow,
            "n_mc_weighted_stat_err_76_106": n_mc_narrow_stat,
            "data_over_mc_76_106": ratio_narrow,
            "data_over_mc_76_106_stat_err": ratio_narrow_staterr,
        }

        if cat_name == "inclusive":
            inclusive_data_hist = d_hist
            inclusive_mc_hist = mc_hist
            inclusive_mc_sumw2 = mc_sumw2

    result_path = out_dir / "d1_zpeak_result.json"
    result_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result["categories"], indent=2))
    print(f"wrote {result_path}")

    # --- inclusive plot with ratio panel ---
    centers = 0.5 * (EDGES[:-1] + EDGES[1:])
    mc_err = np.sqrt(inclusive_mc_sumw2)
    data_err = np.sqrt(inclusive_data_hist)

    fig, (ax1, ax2) = plt.subplots(
        2, 1, figsize=(8, 7), sharex=True, gridspec_kw={"height_ratios": [3, 1], "hspace": 0.05},
    )
    ax1.bar(centers, inclusive_mc_hist, width=BIN_WIDTH, color="tab:orange", alpha=0.5,
            label="MC (DY + TTTo2L2Nu, weighted)")
    ax1.fill_between(centers, inclusive_mc_hist - mc_err, inclusive_mc_hist + mc_err,
                      step="mid", color="tab:orange", alpha=0.3, label="MC stat. band")
    ax1.errorbar(centers, inclusive_data_hist, yerr=data_err, fmt="ko", markersize=3, label="Data")
    ax1.set_ylabel(f"Events / {BIN_WIDTH:.0f} GeV")
    ax1.set_title("D1: inclusive dimuon mass, pre-postprocessing (>=1 jet base selection)")
    ax1.legend()

    with np.errstate(divide="ignore", invalid="ignore"):
        ratio = np.where(inclusive_mc_hist > 0, inclusive_data_hist / inclusive_mc_hist, np.nan)
        ratio_err = np.where(
            inclusive_mc_hist > 0,
            ratio * np.sqrt(
                np.where(inclusive_data_hist > 0, 1.0 / inclusive_data_hist, 0.0)
                + (mc_err / inclusive_mc_hist) ** 2
            ),
            np.nan,
        )
    ax2.errorbar(centers, ratio, yerr=ratio_err, fmt="ko", markersize=3)
    ax2.axhline(1.0, color="gray", linestyle="--", linewidth=1)
    ax2.set_xlabel("m(mu0, mu1) [GeV]")
    ax2.set_ylabel("Data / MC")
    ax2.set_ylim(0, 2)

    plot_path = out_dir / "d1_zpeak_inclusive.png"
    fig.savefig(plot_path, dpi=130)
    print(f"wrote {plot_path}")


if __name__ == "__main__":
    main()
