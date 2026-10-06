#!/usr/bin/env python
"""
Step D aggregation: combine the per-file DoubleEG matching-efficiency
JSONs, compute Clopper-Pearson 68% intervals, apply the FIXED decision
criterion and write the evidence JSON plus the two four-panel plots.

The decision criterion is fixed in advance and is NOT changed here:
  Delta_region = eff_sub(>30) - eff_sub(25-30), from measurement (b),
  in barrel and in endcap.
    * Delta <= 2.0 percentage points in BOTH regions -> "leading_only"
    * otherwise                                      -> "both"
  BORDERLINE (not settled) if, in either region, 2.0 pp lies within the
  68% uncertainty of Delta. The uncertainty on Delta is built from the two
  Clopper-Pearson 68% intervals by combining the relevant one-sided errors
  in quadrature, treating the two pT ranges as independent samples (they
  are disjoint event sets).

Usage:
    python aggregate_doubleeg_efficiency.py \
        --in-dir  /storage/.../doubleeg_eff \
        --out-json studies/cms_datasets/electron_vB/evidence/stepD_doubleeg_efficiency.json \
        --out-plots studies/cms_datasets/electron_vB/plots
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

import numpy as np  # noqa: E402

from studies.cms_datasets.electron_prep.common import clopper_pearson  # noqa: E402
from studies.cms_datasets.electron_vB.measure_doubleeg_efficiency import (  # noqa: E402
    MEASUREMENTS, PT_BIN_EDGES, REGIONS, SUMMARY_BINS,
)

CRITERION_DELTA_PP = 2.0
DECISION_REGIONS = ("barrel", "endcap")   # the criterion's own two regions
MEASUREMENT_TITLES = {
    "a_leading_tagged": "(a) leading, subleading matched",
    "b_subleading_tagged": "(b) subleading, leading matched & >30",
    "c_leading_untagged": "(c) leading, untagged",
    "d_subleading_untagged": "(d) subleading, leading >30 only",
    "d2_subleading_plain": "(d2) subleading, no requirement",
}


def eff_with_interval(k: int, n: int) -> dict:
    p, lo, hi = clopper_pearson(np.array([k]), np.array([n]))
    return {"num": int(k), "den": int(n),
            "eff": None if n == 0 else float(p[0]),
            "lo68": None if n == 0 else float(lo[0]),
            "hi68": None if n == 0 else float(hi[0])}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--in-dir", required=True)
    p.add_argument("--out-json", required=True)
    p.add_argument("--out-plots", required=True)
    args = p.parse_args()

    files = sorted(Path(args.in_dir).glob("*.json"))
    if not files:
        raise SystemExit(f"no per-file JSONs under {args.in_dir}")
    per_file = [json.loads(f.read_text(encoding="utf-8")) for f in files]
    print(f"combining {len(per_file)} per-file measurements")

    totals = {m: {r: {"bins": {}, "summary": {}, "all_pt": [0, 0]} for r in REGIONS}
              for m in MEASUREMENTS}
    agg = {"n_read": 0, "n_after_golden_json": 0, "n_after_path_fired": 0,
           "n_population_ge2_selected_electrons": 0,
           "n_electrons_removed_by_overlap_removal": 0,
           "trigger_guard_violations": 0,
           "n_events_electron_collection_not_pt_descending": 0}
    hlt_missing = {}
    files_used = []
    for d in per_file:
        for k in agg:
            agg[k] += int(d.get(k, 0))
        files_used.append({"era": d["era"], "file_index": d["file_index"],
                           "n_population": d["n_population_ge2_selected_electrons"],
                           "elapsed_sec": d.get("elapsed_sec")})
        for path, present in d.get("hlt_branch_presence_all_four_datasets", {}).items():
            if not present:
                hlt_missing.setdefault(path, []).append(
                    f"{d['dataset']}-{d['era']}-file{d['file_index']}")
        for m, by_region in d.get("counts", {}).items():
            for r, block in by_region.items():
                tgt = totals[m][r]
                tgt["all_pt"][0] += block["all_pt"][0]
                tgt["all_pt"][1] += block["all_pt"][1]
                for key, (num, den) in block["bins"].items():
                    cur = tgt["bins"].setdefault(key, [0, 0])
                    cur[0] += num
                    cur[1] += den
                for key, (num, den) in block["summary"].items():
                    cur = tgt["summary"].setdefault(key, [0, 0])
                    cur[0] += num
                    cur[1] += den

    results = {}
    for m in MEASUREMENTS:
        results[m] = {}
        for r in REGIONS:
            results[m][r] = {
                "bins": {k: eff_with_interval(*v) for k, v in sorted(
                    totals[m][r]["bins"].items(),
                    key=lambda kv: float(kv[0].split("-")[0]))},
                "summary": {k: eff_with_interval(*totals[m][r]["summary"][k])
                            for k in SUMMARY_BINS if k in totals[m][r]["summary"]},
                "all_pt": eff_with_interval(*totals[m][r]["all_pt"]),
            }

    # ---- the fixed criterion -------------------------------------------
    criterion = {"rule": ("Delta_region = eff_sub(>30) - eff_sub(25-30) from "
                          "measurement (b); <= 2.0 pp in BOTH barrel and endcap "
                          "-> leading_only, else both"),
                 "threshold_pp": CRITERION_DELTA_PP, "per_region": {}}
    deltas_ok = []
    borderline = False
    for r in DECISION_REGIONS:
        lo_bin = results["b_subleading_tagged"][r]["summary"].get("25-30")
        hi_bin = results["b_subleading_tagged"][r]["summary"].get("gt30")
        entry = {"eff_25_30": lo_bin, "eff_gt30": hi_bin}
        if not lo_bin or not hi_bin or lo_bin["eff"] is None or hi_bin["eff"] is None:
            entry["delta_pp"] = None
            entry["verdict"] = "NO DATA"
            deltas_ok.append(False)
            borderline = True
        else:
            delta = (hi_bin["eff"] - lo_bin["eff"]) * 100.0
            # One-sided errors on Delta, combined in quadrature.
            err_lo = float(np.hypot(hi_bin["eff"] - hi_bin["lo68"],
                                    lo_bin["hi68"] - lo_bin["eff"]) * 100.0)
            err_hi = float(np.hypot(hi_bin["hi68"] - hi_bin["eff"],
                                    lo_bin["eff"] - lo_bin["lo68"]) * 100.0)
            entry["delta_pp"] = float(delta)
            entry["delta_err_lo_pp"] = err_lo
            entry["delta_err_hi_pp"] = err_hi
            entry["delta_68_interval_pp"] = [float(delta - err_lo), float(delta + err_hi)]
            within = (delta - err_lo) <= CRITERION_DELTA_PP <= (delta + err_hi)
            entry["threshold_inside_68_interval"] = bool(within)
            entry["verdict"] = ("<= 2.0 pp" if delta <= CRITERION_DELTA_PP else "> 2.0 pp")
            deltas_ok.append(delta <= CRITERION_DELTA_PP)
            borderline = borderline or within
        criterion["per_region"][r] = entry
    criterion["outcome"] = "leading_only" if all(deltas_ok) else "both"
    criterion["borderline"] = bool(borderline)
    criterion["outcome_status"] = "PROVISIONAL -- Matan has the final say"

    # Does the LEADING leg show a 25-30 GeV inefficiency? Same shape of test,
    # from measurement (a).
    leading_note = {}
    any_leading_ineff = False
    for r in DECISION_REGIONS:
        lo_bin = results["a_leading_tagged"][r]["summary"].get("25-30")
        hi_bin = results["a_leading_tagged"][r]["summary"].get("gt30")
        if lo_bin and hi_bin and lo_bin["eff"] is not None and hi_bin["eff"] is not None:
            delta = (hi_bin["eff"] - lo_bin["eff"]) * 100.0
            leading_note[r] = {"eff_25_30": lo_bin, "eff_gt30": hi_bin,
                               "delta_pp": float(delta),
                               "shows_25_30_inefficiency": bool(delta > CRITERION_DELTA_PP)}
            any_leading_ineff = any_leading_ineff or delta > CRITERION_DELTA_PP
        else:
            leading_note[r] = {"delta_pp": None, "shows_25_30_inefficiency": None}
    leading_note["leading_leg_shows_inefficiency_in_either_region"] = bool(any_leading_ineff)
    subleading_ineff = not all(deltas_ok)
    leading_note["FLAG_neither_leg_shows_inefficiency"] = bool(
        not any_leading_ineff and not subleading_ineff)

    out = {
        "what": "Step D: DoubleEG trigger-matching efficiency, all files combined",
        "n_files": len(per_file),
        "files": files_used,
        "population_totals": agg,
        "hlt_branches_missing_anywhere": hlt_missing,
        "pt_bin_edges": PT_BIN_EDGES,
        "regions": list(REGIONS),
        "regions_note": ("barrel |eta|<1.4442, gap 1.4442<=|eta|<=1.566, endcap "
                         "1.566<|eta|<2.5, on Electron_eta -- the variable the "
                         "electron selection itself cuts on. Gap electrons DO pass "
                         "the selection (no gap veto), so the gap is a separate "
                         "third region and is never merged into either."),
        "measurement_definitions": {
            "a_leading_tagged": "num leading matched / den subleading matched",
            "b_subleading_tagged": "num subleading matched / den (leading matched AND leading pT>30)",
            "c_leading_untagged": "num leading matched / den all population events",
            "d_subleading_untagged": "num subleading matched / den (leading pT>30)",
            "d2_subleading_plain": "num subleading matched / den all population events",
        },
        "results": results,
        "criterion": criterion,
        "leading_leg_check": leading_note,
    }
    Path(args.out_json).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out_json).write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"wrote {args.out_json}")

    make_plots(results, criterion, Path(args.out_plots))

    print("\n=== Step D criterion ===")
    for r in DECISION_REGIONS:
        e = criterion["per_region"][r]
        print(f"  {r:7s} Delta = {e.get('delta_pp')} pp  "
              f"68% [{e.get('delta_68_interval_pp')}]  {e.get('verdict')}")
    print(f"  OUTCOME: {criterion['outcome']}  (borderline={criterion['borderline']})")
    print(f"  leading leg shows 25-30 inefficiency: "
          f"{leading_note['leading_leg_shows_inefficiency_in_either_region']}")
    print(f"  FLAG neither leg shows inefficiency: "
          f"{leading_note['FLAG_neither_leg_shows_inefficiency']}")


def make_plots(results, criterion, out_dir: Path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    out_dir.mkdir(parents=True, exist_ok=True)
    centres = [(PT_BIN_EDGES[i] + PT_BIN_EDGES[i + 1]) / 2 for i in range(len(PT_BIN_EDGES) - 1)]
    widths = [(PT_BIN_EDGES[i + 1] - PT_BIN_EDGES[i]) / 2 for i in range(len(PT_BIN_EDGES) - 1)]
    keys = [f"{PT_BIN_EDGES[i]:g}-{PT_BIN_EDGES[i + 1]:g}" for i in range(len(PT_BIN_EDGES) - 1)]

    def panel(ax, measurement, region, title):
        ys, los, his, xs, xerr = [], [], [], [], []
        block = results[measurement][region]["bins"]
        for k, c, w in zip(keys, centres, widths):
            e = block.get(k)
            if not e or e["den"] == 0:
                continue
            ys.append(e["eff"])
            los.append(e["eff"] - e["lo68"])
            his.append(e["hi68"] - e["eff"])
            xs.append(c)
            xerr.append(w)
        if ys:
            ax.errorbar(xs, ys, yerr=[los, his], xerr=xerr, fmt="o", ms=3, lw=1,
                        capsize=0, color="C0")
        ax.axvline(30.0, color="crimson", ls="--", lw=1, label="30 GeV")
        ax.set_title(title, fontsize=9)
        ax.set_xlabel("probed electron offline $p_T$ [GeV]", fontsize=8)
        ax.set_ylabel("matching efficiency", fontsize=8)
        ax.set_ylim(0.0, 1.05)
        ax.grid(alpha=0.3)
        ax.tick_params(labelsize=7)
        ax.legend(fontsize=7, loc="lower right")

    for fname, (m_lead, m_sub), supt in (
        ("stepD_efficiency_tagged.png", ("a_leading_tagged", "b_subleading_tagged"),
         "DoubleEG matching efficiency, TAGGED (the other electron matched)"),
        ("stepD_efficiency_untagged.png", ("c_leading_untagged", "d_subleading_untagged"),
         "DoubleEG matching efficiency, UNTAGGED (no requirement on the other electron)"),
    ):
        fig, axes = plt.subplots(2, 2, figsize=(9.5, 7.0))
        for col, region in enumerate(DECISION_REGIONS):
            panel(axes[0][col], m_lead, region,
                  f"{MEASUREMENT_TITLES[m_lead]} -- {region}")
            panel(axes[1][col], m_sub, region,
                  f"{MEASUREMENT_TITLES[m_sub]} -- {region}")
        fig.suptitle(f"{supt}\ncriterion outcome: {criterion['outcome']} "
                     f"(PROVISIONAL{', BORDERLINE' if criterion['borderline'] else ''})",
                     fontsize=10)
        fig.tight_layout(rect=(0, 0, 1, 0.94))
        fig.savefig(out_dir / fname, dpi=140)
        plt.close(fig)
        print(f"wrote {out_dir / fname}")

    # The gap region, reported separately so it is never silently merged.
    fig, axes = plt.subplots(1, 2, figsize=(9.5, 3.8))
    panel(axes[0], "a_leading_tagged", "gap", "(a) leading -- GAP (1.4442-1.566)")
    panel(axes[1], "b_subleading_tagged", "gap", "(b) subleading -- GAP (1.4442-1.566)")
    fig.suptitle("DoubleEG matching efficiency in the barrel-endcap GAP region "
                 "(these electrons DO pass the selection)", fontsize=10)
    fig.tight_layout(rect=(0, 0, 1, 0.9))
    fig.savefig(out_dir / "stepD_efficiency_gap.png", dpi=140)
    plt.close(fig)
    print(f"wrote {out_dir / 'stepD_efficiency_gap.png'}")


if __name__ == "__main__":
    main()
