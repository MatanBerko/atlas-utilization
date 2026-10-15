#!/usr/bin/env python
"""
One summary plot for DATA_MC_JET_MULTIPLICITY.md, drawn from the jet-excess
study's evidence JSON ONLY. There are no new data and no new measurement.

  * the data/MC ratio vs jet multiplicity (0 ... >=5), paper-like jets,
    detector level: results.<ch>.paperlike.{ratio,error}
  * on the same axes, the residual after the C5 generator correction:
    results.part_d.<ch>.C5_generator.{residual_ratio,residual_error}

The evidence is read with `git show` from the study branch's head, pinned:
  9927ca6:studies/cms_mc_weights_v3/jets/evidence/jet_excess_results.json

Run:  python studies/cms_mc_weights_v3/docs_plots/make_jet_multiplicity_summary.py
"""
from __future__ import annotations

import json
import pathlib
import subprocess
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = pathlib.Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[2]
STUDY_COMMIT = "9927ca6"
EVIDENCE = "studies/cms_mc_weights_v3/jets/evidence/jet_excess_results.json"
OUT = HERE / "jet_multiplicity_ratio_summary.png"
LABELS = ["0", "1", "2", "3", "4", "≥5"]


def main() -> int:
    raw = subprocess.run(["git", "show", f"{STUDY_COMMIT}:{EVIDENCE}"], cwd=REPO_ROOT,
                         capture_output=True, check=True).stdout
    res = json.loads(raw)["results"]

    fig, ax = plt.subplots(figsize=(7.5, 4.8), dpi=150)
    x = list(range(len(LABELS)))
    styles = {"mumu": ("μμ", "#2b6cb0"), "ee": ("ee", "#c05621")}
    for i, (ch, (name, colour)) in enumerate(styles.items()):
        off = -0.12 if i == 0 else 0.12
        r = res[ch]["paperlike"]
        ax.errorbar([v + off for v in x], r["ratio"], yerr=r["error"], fmt="o",
                    color=colour, ms=6, capsize=3,
                    label=f"{name}: data / MC (detector level, paper-like jets)")
        c5 = res["part_d"][ch]["C5_generator"]
        ax.errorbar([v + off for v in x], c5["residual_ratio"], yerr=c5["residual_error"],
                    fmt="s", mfc="white", color=colour, ms=6, capsize=3,
                    label=f"{name}: residual after the C5 generator correction")
    ax.axhline(1.0, color="0.4", lw=1, ls="--")
    ax.set_xticks(x)
    ax.set_xticklabels(LABELS)
    ax.set_xlabel("number of jets (exclusive; last bin inclusive)")
    ax.set_ylabel("ratio")
    ax.set_ylim(0.6, 2.4)
    ax.set_title("CMS Z+jets, data/MC vs jet multiplicity: before and after the C5 correction",
                 fontsize=10)
    ax.legend(fontsize=7.5, loc="upper left", frameon=False)
    fig.text(0.01, 0.01,
             f"Source: {STUDY_COMMIT}:{EVIDENCE}\n(results.<ch>.paperlike; "
             "results.part_d.<ch>.C5_generator). Shape normalisation: MC rescaled per "
             "channel to the data subset's inclusive Z yield.", fontsize=6, color="0.35")
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    fig.savefig(OUT)
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
