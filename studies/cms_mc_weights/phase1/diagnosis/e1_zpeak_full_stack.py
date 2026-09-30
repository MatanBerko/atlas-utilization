#!/usr/bin/env python
"""
Diagnosis round 2 -- E1: redo D1's Z-peak table with the FULL 9-sample
background stack (D4's measured backgrounds), for both DY generators.
FROM EXISTING OUTPUTS ONLY -- no new cluster jobs, no data reprocessing.

Data side: identical to D1 (raw, pre-postprocessing "m0m1" signatures
from the existing coverage_shard.sqlite files).

MC side: every sample's own existing mc_combinations.npz (phase-1's 3
samples + D4's 8 samples), weighted by
    genWeight * L1PreFiringWeight_Nom * per_file_normalization_factor
(per_file_normalization_factor read from each sample's own
merge_mc_summary.json, never recomputed), summed across all 9 samples in
a stack.

Stack (a): DY madgraphMLM (35671) + TTTo2L2Nu (67801) + ST_tW_top (64895)
  + ST_tW_antitop (64839) + WW (72676) + WZ (72752, k=1 flagged)
  + ZZ4L (75589) + TTZ (68187) + TTW (68073).
Stack (b): identical, DY amcatnloFXFX (35669) replacing madgraphMLM.

Writes e1_zpeak_full_stack_result.json under
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

from services.storage.sqlite_shards import list_signatures, iter_arrays_for_signature  # noqa: E402

DATA_SHARD_BASE = "/storage/agrp/berkom/atlas-utilization/output/cms_coverage_full"
MC_WORK_BASE = "/storage/agrp/berkom/atlas-utilization/work/cms_mc_phase1"
PHASE1_DIR = REPO_ROOT / "studies/cms_mc_weights/phase1"

COMMON_SAMPLES = {
    "67801": ("TTTo2L2Nu", 49),
    "64895": ("ST_tW_top", 11),
    "64839": ("ST_tW_antitop", 10),
    "72676": ("WWTo2L2Nu", 7),
    "72752": ("WZTo3LNu_amcatnloFXFX (k=1 flagged)", 31),
    "75589": ("ZZTo4L", 99),
    "68187": ("TTZToLLNuNu_M-10", 42),
    "68073": ("TTWJetsToLNu", 12),
}
STACK_A = {"35671": ("DYJetsToLL_M-50_madgraphMLM", 61), **COMMON_SAMPLES}
STACK_B = {"35669": ("DYJetsToLL_M-50_amcatnloFXFX", 41), **COMMON_SAMPLES}

Z_LO, Z_HI = 60.0, 120.0
NARROW_LO, NARROW_HI = 76.0, 106.0
BIN_WIDTH = 1.0
N_BINS = int(round((Z_HI - Z_LO) / BIN_WIDTH))
EDGES = np.linspace(Z_LO, Z_HI, N_BINS + 1)

LABEL_RE = re.compile(r"_FS_([0-9a-z_]+)_IM_m0m1$")
NJ_RE = re.compile(r"_(\d+)jx?(?:_|$)")
NB_RE = re.compile(r"_(\d+)bx?(?:_|$)")
NM_RE = re.compile(r"_(\d+)mx?(?:_|$)")


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


def load_mc_stack(stack: dict):
    """Returns list of (mass, weight, nj, nb, nm, recid) across every
    sample in `stack`, weight = genWeight*L1*per_file_normalization_factor
    (that sample's own, from its own merge_mc_summary.json)."""
    out = []
    per_sample_info = {}
    for rid, (name, n_expected) in stack.items():
        summary_path = PHASE1_DIR / rid / "merge_mc_summary.json"
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        norm = summary["per_file_normalization_factor"]

        job_dirs = sorted(
            glob.glob(f"{MC_WORK_BASE}/{rid}/job_*/"),
            key=lambda p: int(p.rstrip("/").rsplit("_", 1)[1]),
        )
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
                weight = gw * l1 * norm
                nj, nb, nm = parse_label(sig)
                out.append((mass, weight, nj, nb, nm, rid))
        per_sample_info[rid] = {"name": name, "n_files_expected": n_expected, "n_files_found": n_found,
                                 "per_file_normalization_factor": norm}
    return out, per_sample_info


def build_categories(data_parsed, mc_parsed):
    categories = {
        "inclusive": lambda nj, nb: True,
        "jet_1": lambda nj, nb: nj == 1,
        "jet_2": lambda nj, nb: nj == 2,
        "jet_ge3": lambda nj, nb: nj is not None and nj >= 3,
        "bjet_0": lambda nj, nb: nb == 0,
        "bjet_ge1": lambda nj, nb: nb is not None and nb >= 1,
    }
    result = {}
    for cat_name, pred in categories.items():
        d_mass_list = [m for m, nj, nb, nm in data_parsed if pred(nj, nb)]
        d_mass = np.concatenate(d_mass_list) if d_mass_list else np.array([])

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

        result[cat_name] = {
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
    return result


def main():
    out_dir = REPO_ROOT / "studies/cms_mc_weights/phase1/diagnosis"
    out_dir.mkdir(parents=True, exist_ok=True)

    data_records, n_data_jobs_read, n_data_jobs_missing = load_data()
    data_parsed = [(mass, *parse_label(label)) for mass, label in data_records]

    result = {
        "z_window_gev": [Z_LO, Z_HI],
        "narrow_window_gev": [NARROW_LO, NARROW_HI],
        "n_data_jobs_read": n_data_jobs_read,
        "n_data_jobs_missing": n_data_jobs_missing,
        "stacks": {},
    }

    for stack_name, stack in [("stack_a_madgraphMLM_DY", STACK_A), ("stack_b_amcatnloFXFX_DY", STACK_B)]:
        mc_parsed, per_sample_info = load_mc_stack(stack)
        categories = build_categories(data_parsed, mc_parsed)
        result["stacks"][stack_name] = {"samples": per_sample_info, "categories": categories}
        print(f"=== {stack_name} ===")
        print(json.dumps(categories, indent=2))

    out_path = out_dir / "e1_zpeak_full_stack_result.json"
    out_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"wrote {out_path}")


if __name__ == "__main__":
    main()
