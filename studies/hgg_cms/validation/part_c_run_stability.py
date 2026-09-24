"""
Implementation task 6, Part 3C: run-by-run stability of the selected
sideband rate.

For every certified run in the Run2016G (278820-280385) + Run2016H
(280919-284044) ranges (same golden JSON already used by the pipeline's
own validated_runs filter -- data/cms/validated_runs/
Cert_271036-284044_13TeV_Legacy2016_Collisions16_JSON.txt), computes:
  N_run   = selected sideband events in data_sidebands.root with that run
  L_run   = that run's CERTIFIED RECORDED luminosity (sum of
            pp_2016lumibyls.csv's per-lumisection "recorded(/fb)" column
            over every lumisection the golden JSON certifies for that
            run -- same method as impl_checks/lumi_coverage/sum_by_era.py,
            applied per-run instead of per-era).
  rate_run = N_run / L_run

Compares each run's rate to the GLOBAL average rate (sum(N)/sum(L)) with
a Poisson significance, flags any run deviating by more than 3 sigma, and
reports the overall chi2/ndf of "rate is constant across runs".

pp_2016lumibyls.csv (21,137,550 bytes, CERN Open Data record 1059) is a
large intermediate download, NOT committed to the repo -- download it
first (same source LUMI_DECISION.md and sum_by_era.py already used):
    curl -o pp_2016lumibyls.csv https://opendata.cern.ch/record/1059/files/pp_2016lumibyls.csv
and pass its path via --lumi-csv or the HGG_LUMI_CSV environment variable.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from studies.hgg_cms.validation import common

OUT_DIR = Path(__file__).resolve().parent / "results"
PLOTS_DIR = OUT_DIR / "plots"
REPO_ROOT = Path(__file__).resolve().parents[3]
GOLDEN_JSON = REPO_ROOT / "data" / "cms" / "validated_runs" / \
    "Cert_271036-284044_13TeV_Legacy2016_Collisions16_JSON.txt"

RUN_RANGES = {"Run2016G": (278820, 280385), "Run2016H": (280919, 284044)}


def load_golden_certified_ls(golden_path: Path) -> dict:
    golden = json.loads(golden_path.read_text(encoding="utf-8"))
    certified = {}
    for run_str, ranges in golden.items():
        run = int(run_str)
        lo_g, hi_g = RUN_RANGES["Run2016G"]
        lo_h, hi_h = RUN_RANGES["Run2016H"]
        if not (lo_g <= run <= hi_g or lo_h <= run <= hi_h):
            continue
        lss = set()
        for a, b in ranges:
            lss.update(range(a, b + 1))
        certified[run] = lss
    return certified


def sum_lumi_per_run(csv_path: Path, certified: dict) -> dict:
    per_ls_recorded = {}
    with open(csv_path, encoding="utf-8") as f:
        for line in f:
            if line.startswith("#"):
                continue
            parts = line.strip().split(",")
            run = int(parts[0].split(":")[0])
            if run not in certified:
                continue
            ls = int(parts[1].split(":")[0])
            per_ls_recorded[(run, ls)] = float(parts[6])

    l_per_run = {}
    for run, lss in certified.items():
        l_per_run[run] = sum(per_ls_recorded.get((run, ls), 0.0) for ls in lss)
    return l_per_run


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--lumi-csv", default=os.environ.get("HGG_LUMI_CSV"))
    args = p.parse_args()
    if not args.lumi_csv:
        raise SystemExit(
            "Pass --lumi-csv <path to pp_2016lumibyls.csv> or set HGG_LUMI_CSV "
            "-- see this script's module docstring for the download command."
        )
    csv_path = Path(args.lumi_csv)

    PLOTS_DIR.mkdir(parents=True, exist_ok=True)
    data = common.load_data_sidebands()
    runs_in_data = np.asarray(data["run"])

    certified = load_golden_certified_ls(GOLDEN_JSON)
    l_per_run = sum_lumi_per_run(csv_path, certified)

    all_runs = sorted(certified.keys())
    n_per_run = {r: int(np.sum(runs_in_data == r)) for r in all_runs}

    # Only runs with nonzero certified luminosity can enter a rate=N/L
    # calculation; a certified run with L_run==0 (possible if, per
    # LUMI_DECISION.md, ALL of that run's certified sections happen to be
    # zero-luminosity technical-stop sections) is reported separately, not
    # divided by zero.
    usable_runs = [r for r in all_runs if l_per_run[r] > 0]
    zero_lumi_runs = [r for r in all_runs if l_per_run[r] == 0]
    runs_with_events_but_zero_lumi = [r for r in zero_lumi_runs if n_per_run[r] > 0]

    N = np.array([n_per_run[r] for r in usable_runs], dtype=float)
    L = np.array([l_per_run[r] for r in usable_runs], dtype=float)
    rate = N / L

    global_rate = N.sum() / L.sum()
    expected = global_rate * L
    # Poisson significance; guard the (should-never-happen, since every
    # usable run has L>0 hence expected>0 unless global_rate==0) zero case.
    sig = np.where(expected > 0, (N - expected) / np.sqrt(np.maximum(expected, 1e-12)), 0.0)

    chi2 = float(np.sum((N - expected) ** 2 / np.maximum(expected, 1e-12)))
    ndf = len(usable_runs) - 1
    chi2_over_ndf = chi2 / ndf if ndf > 0 else None

    flagged_runs = [
        {"run": int(r), "N": int(n), "L_fb": float(l), "rate": float(rr), "significance_sigma": float(s)}
        for r, n, l, rr, s in zip(usable_runs, N, L, rate, sig) if abs(s) > 3.0
    ]

    # ---- Plot ----
    fig, ax = plt.subplots(figsize=(12, 5))
    rate_err = np.sqrt(N) / L
    colors = np.where(np.abs(sig) > 3.0, "#D55E00", "#0072B2")
    ax.errorbar(usable_runs, rate, yerr=rate_err, fmt="o", markersize=3, elinewidth=0.7,
                ecolor="#999999", color="none")
    ax.scatter(usable_runs, rate, c=colors, s=14, zorder=3)
    ax.axhline(global_rate, color="#1a1a1a", linewidth=1.2, linestyle="--",
               label=f"average = {global_rate:.1f} events/fb$^{{-1}}$")
    ax.set_yscale("log")
    ax.set_xlabel("run number")
    ax.set_ylabel("selected sideband events / fb$^{-1}$ (log scale)")
    ax.set_title(f"Run-by-run sideband rate stability ($\\chi^2$/ndf = {chi2_over_ndf:.2f}, "
                 f"{len(flagged_runs)} run(s) flagged >3$\\sigma$)\n"
                 f"note: log y-axis -- a handful of sub-0.01 fb$^{{-1}}$ runs have huge Poisson "
                 f"noise on their rate and dominate a linear axis otherwise")
    ax.legend(loc="upper right", fontsize=8, frameon=False)
    ax.grid(alpha=0.25, linewidth=0.5)
    fig.tight_layout()
    fig.savefig(PLOTS_DIR / "part_c_run_stability.png", dpi=150)
    plt.close(fig)

    result = {
        "n_certified_runs_G_and_H": len(all_runs),
        "n_usable_runs_L_gt_0": len(usable_runs),
        "n_zero_lumi_certified_runs": len(zero_lumi_runs),
        "runs_with_events_but_zero_certified_lumi": runs_with_events_but_zero_lumi,
        "global_rate_events_per_fb": float(global_rate),
        "total_N": int(N.sum()),
        "total_L_fb": float(L.sum()),
        "chi2": chi2, "ndf": ndf, "chi2_over_ndf": chi2_over_ndf,
        "n_runs_flagged_gt_3sigma": len(flagged_runs),
        "n_flagged_runs_with_L_fb_below_0p01": int(sum(1 for f in flagged_runs if f["L_fb"] < 0.01)),
        "flagged_runs": flagged_runs,
    }
    (OUT_DIR / "part_c_results.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    print(f"\nwrote {OUT_DIR / 'part_c_results.json'} and plot to {PLOTS_DIR}")


if __name__ == "__main__":
    main()
