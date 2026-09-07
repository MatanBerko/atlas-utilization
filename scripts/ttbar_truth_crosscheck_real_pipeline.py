#!/usr/bin/env python3
"""
Step 4/5 analysis for the real-pipeline ttbar b-tag truth cross-check.

Reads the ACTUAL parsed output of config.cms_ttbar_truth_crosscheck.yaml
(eta_max 2.5) and config.cms_ttbar_truth_crosscheck_eta4p5.yaml (eta_max 4.5)
-- i.e. the real Jets/BJets split produced by
services/parsing/file_parser.py's FileParser._calculate_btagging_and_split,
with Jet_hadronFlavour and the raw score carried through via the additive
include_truth_flavour flag. No selection/tagging logic is re-derived here:
"tagged" == "landed in the BJets collection", exactly as the real pipeline
decided it.

Per Step 1's finding (see the config file headers and the report): the
pipeline's kinematic cut (pT>30, |eta|<eta_max) is only ever matched against
the "Jets" (untagged) collection, never "BJets" -- BJets carries NO kinematic
cut regardless of config. To report a fair, single (pT, eta) window efficiency
from the real output, this script re-applies the SAME window to both
collections' own real pt/eta fields when aggregating. This is a reporting-time
slice of already-decided real per-jet fields, not a new selection rule fed
back into the parsing code.

Usage:
    python scripts/ttbar_truth_crosscheck_real_pipeline.py \
        --run-eta2p5 output/cms_ttbar_truth_crosscheck_eta2p5_TIMESTAMP \
        --run-eta4p5 output/cms_ttbar_truth_crosscheck_eta4p5_TIMESTAMP \
        --out-dir reports/ttbar_btag_truth_crosscheck
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

THRESHOLD = 0.25
PT_MIN = 30.0
FLAVOUR_NAMES = {5: "b", 4: "c", 0: "light/gluon"}
FLAVOUR_COLORS = {5: "#c1272d", 4: "#2166ac", 0: "#1b7837"}
BINS = np.linspace(0.0, 1.0, 101)

# Step 4 comparison baseline: the earlier, non-production-matching standalone
# script (scripts/ttbar_btag_truth_crosscheck.py, same branch, same 3 files,
# same threshold 0.25) -- ad hoc pT>20 GeV, |eta|<2.4 cut applied directly to
# raw branches, NOT services/parsing. Quoted from
# reports/ttbar_btag_truth_crosscheck/stats.json (eligible_pt_gt_20_abseta_lt_2.4),
# not recomputed here.
STANDALONE_SCRIPT_RESULT = {
    "label": "Earlier standalone script (pT>20, |eta|<2.4; NOT services/parsing)",
    "b": {"n_jets": 6_526_050, "n_tagged": 5_017_244, "rate": 0.7688025681691069},
    "c": {"n_jets": 1_908_811, "n_tagged": 307_287, "rate": 0.16098346038450115},
    "light/gluon": {"n_jets": 11_714_711, "n_tagged": 304_470, "rate": 0.025990397885188973},
}


def load_jets(run_dir: Path):
    """Read every parsed chunk's Jets_* and BJets_* branches, return a dict of
    flat per-jet numpy arrays with an added is_tagged column (True for
    BJets-origin -- the real pipeline's own tag decision, not re-derived)."""
    import awkward as ak
    import uproot

    parsed = sorted(run_dir.glob("parsed_data/*.root"))
    if not parsed:
        raise FileNotFoundError(f"no parsed .root chunks in {run_dir/'parsed_data'}")

    pt_parts, eta_parts, flav_parts, score_parts, tagged_parts = [], [], [], [], []
    n_events = 0
    for chunk in parsed:
        arr = uproot.open(chunk)["events"].arrays(
            ["Jets_pt", "Jets_eta", "Jets_hadronFlavour", "Jets_btagScore",
             "BJets_pt", "BJets_eta", "BJets_hadronFlavour", "BJets_btagScore"],
            library="ak",
        )
        n_events += len(arr)
        for coll, is_tagged in (("Jets", False), ("BJets", True)):
            pt = ak.to_numpy(ak.flatten(arr[f"{coll}_pt"]))
            eta = ak.to_numpy(ak.flatten(arr[f"{coll}_eta"]))
            flav = ak.to_numpy(ak.flatten(arr[f"{coll}_hadronFlavour"]))
            score = ak.to_numpy(ak.flatten(arr[f"{coll}_btagScore"]))
            pt_parts.append(pt.astype(np.float64))
            eta_parts.append(eta.astype(np.float64))
            flav_parts.append(flav.astype(np.int64))
            score_parts.append(score.astype(np.float64))
            tagged_parts.append(np.full(pt.size, is_tagged, dtype=bool))

    return {
        "n_events": n_events,
        "pt": np.concatenate(pt_parts),
        "eta": np.concatenate(eta_parts),
        "flavour": np.concatenate(flav_parts),
        "score": np.concatenate(score_parts),
        "is_tagged": np.concatenate(tagged_parts),
    }


def flavour_stats(pt, eta, flavour, is_tagged, score, eta_max, pt_min=PT_MIN,
                   window=True):
    """Per true-flavour jet counts, tagged counts, rate. If window, restricts
    to pt>pt_min & |eta|<eta_max applied to BOTH Jets- and BJets-origin jets
    (see module docstring); if not window, uses every jet exactly as the
    pipeline delivered it (Jets already pT/eta-cut, BJets not at all)."""
    if window:
        mask = (pt > pt_min) & (np.abs(eta) < eta_max)
    else:
        mask = np.ones(pt.size, dtype=bool)

    out = {}
    counts_by_flav = {}
    for fv, name in FLAVOUR_NAMES.items():
        sel = mask & (flavour == fv)
        n = int(sel.sum())
        tagged = int((is_tagged[sel]).sum())
        out[name] = {"hadronFlavour": fv, "n_jets": n, "n_tagged": tagged,
                      "rate": (tagged / n) if n else None}
        counts_by_flav[fv] = np.histogram(np.clip(score[sel], 0, 1), bins=BINS)[0]
    out["n_jets_total"] = int(mask.sum())
    return out, counts_by_flav


def plot_by_flavour(counts_by_flav, n_by_flav, eta_max, out_png: Path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(9.5, 5.6))
    for fv in (5, 4, 0):
        ax.stairs(counts_by_flav[fv], BINS, lw=1.8, color=FLAVOUR_COLORS[fv],
                   label=f"true {FLAVOUR_NAMES[fv]}-jet  ({n_by_flav[fv]:,} jets)")
    ax.axvline(THRESHOLD, color="#555555", ls="--", lw=1.2,
               label=f"DeepJet Medium WP = {THRESHOLD}")
    ax.set_yscale("log")
    ax.set_xlabel("Jets_btagScore / BJets_btagScore  (real pipeline output)")
    ax.set_ylabel("jets / 0.01  (log scale)")
    ax.set_title(
        f"Simulated ttbar (record 67993), REAL services/parsing pipeline output\n"
        f"pT>{PT_MIN:.0f} GeV, |eta|<{eta_max} applied to Jets AND BJets at "
        f"read time (BJets carries no kinematic cut in the pipeline itself)",
        fontsize=9)
    ax.legend(fontsize=8.5)
    ax.set_xlim(0, 1)
    fig.tight_layout()
    fig.savefig(out_png, dpi=120)
    plt.close(fig)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-eta2p5", required=True, type=Path)
    ap.add_argument("--run-eta4p5", required=True, type=Path)
    ap.add_argument("--out-dir", required=True, type=Path)
    args = ap.parse_args()

    out = args.out_dir
    (out / "plots").mkdir(parents=True, exist_ok=True)

    results = {}
    for label, run_dir, eta_max in (
        ("eta2p5", args.run_eta2p5, 2.5),
        ("eta4p5", args.run_eta4p5, 4.5),
    ):
        data = load_jets(run_dir)
        windowed, counts = flavour_stats(
            data["pt"], data["eta"], data["flavour"], data["is_tagged"],
            data["score"], eta_max=eta_max, window=True,
        )
        as_delivered, _ = flavour_stats(
            data["pt"], data["eta"], data["flavour"], data["is_tagged"],
            data["score"], eta_max=eta_max, window=False,
        )
        n_by_flav = {fv: windowed[name]["n_jets"]
                     for fv, name in FLAVOUR_NAMES.items()}
        plot_name = ("btag_score_by_true_flavour.png" if label == "eta2p5"
                     else "btag_score_by_true_flavour_eta4p5.png")
        plot_by_flavour(counts, n_by_flav, eta_max, out / "plots" / plot_name)

        results[label] = {
            "run_dir": str(run_dir),
            "eta_max": eta_max,
            "pt_min": PT_MIN,
            "n_events": data["n_events"],
            "n_jets_raw_pipeline_output": int(data["pt"].size),
            "windowed_pt_gt_30_eta_window_applied_to_both_collections": windowed,
            "as_delivered_by_pipeline_no_extra_window": as_delivered,
        }
        print(f"{label}: windowed = {json.dumps(windowed, indent=2)}")

    stats = {
        "config_files": [
            "config.cms_ttbar_truth_crosscheck.yaml",
            "config.cms_ttbar_truth_crosscheck_eta4p5.yaml",
        ],
        "threshold": THRESHOLD,
        "real_pipeline_results": results,
        "standalone_script_result_for_comparison": STANDALONE_SCRIPT_RESULT,
        "three_way_comparison": {
            "b_efficiency": {
                "standalone_script_pt20_eta2p4": STANDALONE_SCRIPT_RESULT["b"]["rate"],
                "real_pipeline_eta2p5": results["eta2p5"]["windowed_pt_gt_30_eta_window_applied_to_both_collections"]["b"]["rate"],
                "real_pipeline_eta4p5": results["eta4p5"]["windowed_pt_gt_30_eta_window_applied_to_both_collections"]["b"]["rate"],
            },
            "c_mistag": {
                "standalone_script_pt20_eta2p4": STANDALONE_SCRIPT_RESULT["c"]["rate"],
                "real_pipeline_eta2p5": results["eta2p5"]["windowed_pt_gt_30_eta_window_applied_to_both_collections"]["c"]["rate"],
                "real_pipeline_eta4p5": results["eta4p5"]["windowed_pt_gt_30_eta_window_applied_to_both_collections"]["c"]["rate"],
            },
            "light_mistag": {
                "standalone_script_pt20_eta2p4": STANDALONE_SCRIPT_RESULT["light/gluon"]["rate"],
                "real_pipeline_eta2p5": results["eta2p5"]["windowed_pt_gt_30_eta_window_applied_to_both_collections"]["light/gluon"]["rate"],
                "real_pipeline_eta4p5": results["eta4p5"]["windowed_pt_gt_30_eta_window_applied_to_both_collections"]["light/gluon"]["rate"],
            },
        },
    }
    (out / "stats_real_pipeline.json").write_text(json.dumps(stats, indent=2))
    print(json.dumps(stats["three_way_comparison"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
