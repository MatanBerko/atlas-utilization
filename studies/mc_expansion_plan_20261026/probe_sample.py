"""Probe ONE NanoAOD file (index 0) of a planned MC sample (26 Oct 2026). Read-only.

Run on the cluster inside a PBS job (ROOT reading only in PBS), from a checkout pinned to a
pushed commit, with the repo root on PYTHONPATH:

    python studies/mc_expansion_plan_20261026/probe_sample.py --index $PBS_ARRAY_INDEX --out-dir <dir>

`--index` selects plan_samples.PROBE[index] (or, with `--list v2`, plan_samples_v2.PROBE2[index],
the 31 Oct probe of the never-probed samples). It writes <out-dir>/probe_<recid>.json with:
- presence of every branch the CMS production reads (taken from the production driver
  studies/cms_datasets/cluster/run_dataset_on_file.py and studies/m0m1j0_cms/selection.py
  at this commit, so the list cannot drift), plus LHE_HT and LHE_Njets;
- the Runs tree sums of genEventSumw, genEventSumw2 and genEventCount;
- events in the file, sum w, sum w^2, the negative-genWeight fraction, N_eff of the file;
- a histogram of genWeight (sign and log10 magnitude) for the plots;
- LHE_Njets counts and LHE_HT quantiles when present (W+jets stitching question);
- the read time.
Nothing is written anywhere else; HOME is not used.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import awkward as ak
import numpy as np
import uproot

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from plan_samples import PROBE, by_recid  # noqa: E402
from plan_samples_v2 import PROBE2, by_recid_v2  # noqa: E402
from studies.cms_datasets.cluster import run_dataset_on_file as drv  # noqa: E402
from studies.m0m1j0_cms import selection  # noqa: E402
from studies.m0m1j0_cms.design_checks.common import fetch_file_list  # noqa: E402

EXTRA = ("LHE_HT", "LHE_Njets")
# The five delivered datasets (the driver also knows JetHT and MET, which are not delivered).
DELIVERED = ("DoubleMuon", "SingleMuon", "DoubleEG", "MuonEG", "SingleElectron")


def production_branches() -> list[str]:
    names = set(drv.BASE_OBJECT_BRANCHES) | set(drv.MATCHED_MODE_EXTRA_BRANCHES)
    names |= set(drv.MC_REQUIRED_BRANCHES) | set(selection.NEEDED_BRANCHES)
    for label in DELIVERED:
        names |= set(drv.TRIGGER_PATHS_BY_DATASET[label])
    names |= {drv.ELE27_PATH, drv.MUONEG_PATH_MU23_ELE12, drv.MUONEG_PATH_MU8_ELE23}
    names |= set(drv.SINGLEMUON_MATCHED_TRIGGER_PATHS)
    return sorted(names)


def weight_histogram(w: np.ndarray) -> dict:
    out = {"n_unique": int(np.unique(w).size)}
    a = np.abs(w[w != 0])
    lo, hi = (float(np.log10(a.min())), float(np.log10(a.max()))) if a.size else (0.0, 0.0)
    if hi - lo < 1e-9:
        lo, hi = lo - 0.5, hi + 0.5
    edges = np.linspace(lo, hi, 81)
    out["log10_abs_edges"] = edges.tolist()
    out["pos_counts"] = np.histogram(np.log10(w[w > 0]), bins=edges)[0].tolist() if (w > 0).any() else [0] * 80
    out["neg_counts"] = np.histogram(np.log10(-w[w < 0]), bins=edges)[0].tolist() if (w < 0).any() else [0] * 80
    out["n_zero"] = int((w == 0).sum())
    vals, cnt = np.unique(w, return_counts=True)
    top = np.argsort(cnt)[::-1][:10]
    out["most_common_values"] = [[float(vals[i]), int(cnt[i])] for i in top]
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--index", type=int, required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--list", choices=("v1", "v2"), default="v1")
    a = ap.parse_args()
    recid = (PROBE2 if a.list == "v2" else PROBE)[a.index]
    meta = (by_recid_v2() if a.list == "v2" else by_recid())[recid]
    out_dir = Path(a.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    t0 = time.time()
    url = fetch_file_list(recid)[0]
    t_list = time.time() - t0
    res = {"recid": recid, "name": meta["name"], "tier": meta["tier"], "file_index": 0, "file_url": url,
           "probe_commit_note": "see the PBS log for git rev-parse HEAD"}
    with uproot.open(url) as f:
        ev = f["Events"]
        have = set(ev.keys())
        wanted = production_branches()
        res["branches_checked"] = len(wanted)
        res["branches_missing"] = [b for b in wanted if b not in have]
        res["extra_present"] = {b: b in have for b in EXTRA}
        res["has_L1PreFiringWeight_Nom"] = "L1PreFiringWeight_Nom" in have
        res["has_Pileup_nTrueInt"] = "Pileup_nTrueInt" in have
        res["has_genWeight"] = "genWeight" in have
        res["events_in_file"] = int(ev.num_entries)
        w = ev["genWeight"].array(library="np").astype(np.float64)
        res["sum_w"] = float(w.sum())
        res["sum_w2"] = float((w * w).sum())
        res["n_negative"] = int((w < 0).sum())
        res["frac_negative"] = float((w < 0).mean())
        res["n_eff_file"] = res["sum_w"] ** 2 / res["sum_w2"] if res["sum_w2"] > 0 else None
        res["genweight_hist"] = weight_histogram(w)
        if "LHE_Njets" in have:
            nj = ev["LHE_Njets"].array(library="np")
            v, c = np.unique(nj, return_counts=True)
            res["lhe_njets_counts"] = {int(k): int(n) for k, n in zip(v, c)}
            res["lhe_njets_sumw"] = {int(k): float(w[nj == k].sum()) for k in v}
        if "LHE_HT" in have:
            ht = ev["LHE_HT"].array(library="np")
            res["lhe_ht_quantiles"] = {str(q): float(np.quantile(ht, q)) for q in (0, .1, .5, .9, .99, 1)}
            res["lhe_ht_frac_below_70"] = float((ht < 70).mean())
        runs = f["Runs"]
        rk = set(runs.keys())
        res["runs_fields"] = sorted(rk)
        for k in ("genEventSumw", "genEventSumw2", "genEventCount"):
            res[f"runs_{k}"] = float(ak.sum(runs[k].array())) if k in rk else None
        if res.get("runs_genEventSumw"):
            res["runs_vs_events_sumw_rel"] = res["sum_w"] / res["runs_genEventSumw"] - 1.0
    res["file_list_s"] = round(t_list, 2)
    res["read_time_s"] = round(time.time() - t0 - t_list, 2)
    (out_dir / f"probe_{recid}.json").write_text(json.dumps(res, indent=1) + "\n")
    print(json.dumps({k: res[k] for k in ("recid", "name", "events_in_file", "frac_negative",
                                          "branches_missing", "read_time_s")}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
