#!/usr/bin/env python
"""
SingleElectron Step 1, Step C(2) aggregation: per-run and per-era verdict on
whether HLT_Ele27_WPTight_Gsf was prescaled or disabled in Run2016G+H.

The input is muon-triggered (IsoMu24) SingleMuon data, so the test does not
depend on the electron path. For each run it reports how many events held a
trigger object meeting the Ele27 electron requirements, and of those how
many had the path read 0. An unprescaled, enabled path gives about zero.

Runs are flagged when the not-fired fraction exceeds --flag-fraction AND
there are enough events for that to be meaningful.

Usage:
    python aggregate_prescale.py --in-dir .../prescale \
        --out-json evidence/stepC_prescale.json --out-plots plots
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

import numpy as np  # noqa: E402

FLAG_FRACTION = 0.01     # 1% of qualifying events not firing is "clearly non-zero"
MIN_EVENTS_TO_JUDGE = 100


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in-dir", required=True)
    ap.add_argument("--out-json", required=True)
    ap.add_argument("--out-plots", required=True)
    ap.add_argument("--flag-fraction", type=float, default=FLAG_FRACTION)
    args = ap.parse_args()

    files = sorted(Path(args.in_dir).glob("presc_*.json"))
    if not files:
        raise SystemExit(f"no per-file results under {args.in_dir}")

    per_run_qual = Counter()
    per_run_not = Counter()
    per_era = defaultdict(lambda: {"qualifying": 0, "not_fired": 0,
                                   "n_read": 0, "n_golden": 0, "n_isomu24": 0})
    run_era = {}
    other_when_not_fired = Counter()
    totals = {"n_read": 0, "n_golden": 0, "n_isomu24": 0,
              "qualifying": 0, "not_fired": 0, "not_fired_other_wptight": 0}
    ele27_branch_everywhere = True
    n_files = 0

    for f in files:
        d = json.loads(f.read_text(encoding="utf-8"))
        n_files += 1
        era = d["era"]
        ele27_branch_everywhere &= bool(d.get("ele27_branch_present_in_this_singlemuon_file", False))
        totals["n_read"] += int(d.get("n_read", 0))
        totals["n_golden"] += int(d.get("n_after_golden_json", 0))
        totals["n_isomu24"] += int(d.get("n_after_isomu24", 0))
        totals["qualifying"] += int(d.get("n_events_with_qualifying_object", 0))
        totals["not_fired"] += int(d.get("n_qualifying_but_ele27_not_fired", 0))
        totals["not_fired_other_wptight"] += int(
            d.get("n_qualifying_not_fired_but_other_wptight_fired", 0))
        per_era[era]["n_read"] += int(d.get("n_read", 0))
        per_era[era]["n_golden"] += int(d.get("n_after_golden_json", 0))
        per_era[era]["n_isomu24"] += int(d.get("n_after_isomu24", 0))
        per_era[era]["qualifying"] += int(d.get("n_events_with_qualifying_object", 0))
        per_era[era]["not_fired"] += int(d.get("n_qualifying_but_ele27_not_fired", 0))
        for k, v in (d.get("which_other_wptight_fired_when_ele27_did_not") or {}).items():
            other_when_not_fired[k] += int(v)
        for run, blk in (d.get("per_run") or {}).items():
            per_run_qual[int(run)] += int(blk["n_events_with_qualifying_object"])
            per_run_not[int(run)] += int(blk["n_of_those_with_ele27_not_fired"])
            run_era[int(run)] = era

    runs = sorted(per_run_qual)
    per_run = []
    flagged = []
    for r in runs:
        q, nf = per_run_qual[r], per_run_not[r]
        frac = (nf / q) if q else None
        row = {"run": r, "era": run_era.get(r),
               "n_events_with_qualifying_object": q,
               "n_of_those_with_ele27_not_fired": nf,
               "fraction_not_fired": frac}
        per_run.append(row)
        if q >= MIN_EVENTS_TO_JUDGE and frac is not None and frac > args.flag_fraction:
            flagged.append(row)

    overall = (totals["not_fired"] / totals["qualifying"]) if totals["qualifying"] else None
    verdict = ("no evidence of a prescale or a disabled path: in every run with "
               "enough events, essentially every event that met the Ele27 electron "
               "requirements also has the path fired")
    if flagged:
        verdict = (f"{len(flagged)} run(s) show a not-fired fraction above "
                   f"{args.flag_fraction:.1%}; see flagged_runs")

    out = {
        "what": "Step C(2): empirical prescale / path-enabled test for "
                "HLT_Ele27_WPTight_Gsf, from muon-triggered events",
        "method": "SingleMuon Run2016G+H, golden lumis, HLT_IsoMu24 fired. Count "
                  "events holding a TrigObj with id==11, filterBits & 2 and "
                  "TrigObj_pt >= 27, then the fraction of those with "
                  "HLT_Ele27_WPTight_Gsf == 0, per run and per era.",
        "n_files": n_files,
        "ele27_branch_present_in_every_file_read": ele27_branch_everywhere,
        "totals": totals,
        "overall_fraction_not_fired": overall,
        "per_era": {k: dict(v, fraction_not_fired=(v["not_fired"] / v["qualifying"]
                                                   if v["qualifying"] else None))
                    for k, v in per_era.items()},
        "flag_fraction": args.flag_fraction,
        "min_events_to_judge_a_run": MIN_EVENTS_TO_JUDGE,
        "n_runs": len(runs),
        "n_runs_flagged": len(flagged),
        "flagged_runs": flagged,
        "verdict": verdict,
        "which_other_wptight_fired_when_ele27_did_not": dict(other_when_not_fired),
        "note_on_bit2": "the same numbers bound the bit-2 ambiguity: bit 2 is set by "
                        "any hltEle*WPTight*TrackIsoFilter*, so 'qualifying object but "
                        "Ele27 did not fire' is exactly the rate at which bit 2 plus "
                        "TrigObj_pt >= 27 does NOT mean 'passed Ele27'",
        "per_run": per_run,
    }
    Path(args.out_json).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out_json).write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"runs: {len(runs)}, flagged: {len(flagged)}")
    print(f"overall not-fired fraction: {overall}")
    print(f"per era: { {k: round(v['not_fired']/v['qualifying'],6) if v['qualifying'] else None for k,v in per_era.items()} }")
    print(f"verdict: {verdict}")
    print(f"wrote {args.out_json}")

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    out_dir = Path(args.out_plots)
    out_dir.mkdir(parents=True, exist_ok=True)
    xs = [r["run"] for r in per_run if r["n_events_with_qualifying_object"] >= MIN_EVENTS_TO_JUDGE]
    ys = [r["fraction_not_fired"] for r in per_run
          if r["n_events_with_qualifying_object"] >= MIN_EVENTS_TO_JUDGE]
    cs = ["C0" if run_era.get(x) == "G" else "crimson" for x in xs]
    if xs:
        fig, ax = plt.subplots(figsize=(10.5, 4.2))
        ax.scatter(xs, ys, s=12, c=cs)
        ax.axhline(args.flag_fraction, color="grey", ls="--", lw=1,
                   label=f"flag level {args.flag_fraction:.0%}")
        ax.set_xlabel("run number")
        ax.set_ylabel("fraction with Ele27 not fired")
        ax.set_title("Per run: events whose trigger object met the Ele27 electron\n"
                     "requirements, but where the path did not fire "
                     "(blue = era G, red = era H)")
        ax.set_ylim(bottom=-0.002)
        ax.legend(fontsize=8)
        ax.grid(alpha=0.3)
        fig.tight_layout()
        fig.savefig(out_dir / "stepC_prescale_per_run.png", dpi=140)
        plt.close(fig)
        print(f"wrote {out_dir / 'stepC_prescale_per_run.png'}")


if __name__ == "__main__":
    main()
