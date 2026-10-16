#!/usr/bin/env python
"""
SingleElectron Step 1, Step D aggregation: the cost/benefit table for
offline thresholds 27, 30, 32 and 35 GeV.

For each threshold T it reports
  (a) events accepted by the candidate rule, and the % lost relative to T=27;
  (b) of those, the events accepted by NONE of the four existing datasets --
      the gain if SingleElectron is placed LAST in the priority order;
  (c) the Version B final-state breakdown of the (b) events: how many final
      states have >= 100 events, how many of those are categories the
      current delivery does not have, and a PROJECTION of the histograms
      they would bring;
  (d) the Step B efficiency just above T (first 1 GeV, and averaged over
      T..T+5), barrel and endcap;
  (e) the trigger-guard violation count.

The histogram projection counts, for each new final state, how many of the
186 mass combinations it satisfies, using the SAME shared function the
production uses (physics_calcs.is_finalstate_contain_combination). It is an
upper bound: the real delivery then applies the Z cut, the max-mass cut,
peak removal and the outlier split, which can only remove histograms.

Usage:
    python aggregate_threshold.py --in-dir .../tnp \
        --stepb-json evidence/stepB_tnp.json \
        --delivery-json studies/cms_datasets/electron_vB/evidence/D2_D3_delivery_checks.json \
        --out-json evidence/stepD_thresholds.json
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

import numpy as np  # noqa: E402

from services.calculations import physics_calcs  # noqa: E402
from services.calculations.combinatorics import get_all_combinations  # noqa: E402
from studies.cms_datasets.cluster import run_dataset_on_file as drv  # noqa: E402

MIN_EVENTS_PER_FINAL_STATE = 100


def all_186_combinations():
    combos = get_all_combinations(
        object_types=drv.OBJECT_TYPES,
        min_particles=drv.MIN_PARTICLES_IN_COMBINATION,
        max_particles=drv.MAX_PARTICLES_IN_COMBINATION,
        min_count=drv.MIN_COUNT_PARTICLE_IN_COMBINATION,
        max_count=drv.MAX_COUNT_PARTICLE_IN_COMBINATION,
        max_total_particles=drv.MAX_TOTAL_PARTICLES_IN_COMBINATION,
        include_subleading=drv.INCLUDE_SUBLEADING,
        max_subleading_index=drv.MAX_SUBLEADING_INDEX,
    )
    assert len(combos) == 186, f"expected 186 combinations, got {len(combos)}"
    return combos


def eff_window(stepb: dict, region: str, lo: float, hi: float):
    """Pooled efficiency over probe-pT bins overlapping [lo, hi)."""
    num = den = 0
    for b in stepb["results"][region]["bins"]:
        if b["pt_hi"] <= lo or b["pt_lo"] >= hi:
            continue
        num += b["numerator"]
        den += b["denominator"]
    return (num, den, (num / den) if den else None)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in-dir", required=True)
    ap.add_argument("--stepb-json", required=True)
    ap.add_argument("--delivery-json", required=True)
    ap.add_argument("--out-json", required=True)
    args = ap.parse_args()

    files = sorted(Path(args.in_dir).glob("tnp_*.json"))
    if not files:
        raise SystemExit(f"no per-file results under {args.in_dir}")

    thresholds = None
    acc = Counter()
    gain = Counter()
    vb_kept = Counter()
    vb_rej = Counter()
    fs_counts = {}
    guard = 0
    n_files = 0
    existing_acc = Counter()
    n_any_existing = 0
    n_ele27 = 0

    for f in files:
        d = json.loads(f.read_text(encoding="utf-8"))
        n_files += 1
        guard += int(d.get("trigger_guard_violations", 0))
        n_ele27 += int(d.get("n_after_ele27", 0))
        n_any_existing += int(d.get("n_accepted_by_any_existing_dataset", 0))
        for k, v in (d.get("four_dataset_acceptance_counts_on_this_population") or {}).items():
            existing_acc[k] += int(v)
        scan = d.get("threshold_scan")
        if not scan:
            continue
        thresholds = scan["thresholds"]
        for T, blk in scan["results"].items():
            acc[T] += blk["n_accepted"]
            gain[T] += blk["n_gain_not_accepted_by_existing"]
            vb_kept[T] += blk.get("n_gain_version_b_kept", 0)
            vb_rej[T] += blk.get("n_gain_version_b_rejected", 0)
            tgt = fs_counts.setdefault(T, Counter())
            for fs, n in blk["final_state_counts"].items():
                tgt[fs] += n

    stepb = json.loads(Path(args.stepb_json).read_text(encoding="utf-8"))
    delivered = set(json.loads(Path(args.delivery_json).read_text(
        encoding="utf-8"))["per_final_state_entries_new"])
    combos = all_186_combinations()

    base = str(min(float(t) for t in acc)) if acc else None
    base_key = sorted(acc, key=lambda t: float(t))[0]
    base_acc = acc[base_key]
    base_gain = gain[base_key]

    rows = []
    for T in sorted(acc, key=lambda t: float(t)):
        Tf = float(T)
        counts = fs_counts.get(T, Counter())
        big = {fs: n for fs, n in counts.items() if n >= MIN_EVENTS_PER_FINAL_STATE}
        new_fs = {fs: n for fs, n in big.items() if fs not in delivered}
        projected = 0
        per_new = []
        for fs, n in sorted(new_fs.items(), key=lambda kv: -kv[1]):
            k = sum(1 for c in combos
                    if physics_calcs.is_finalstate_contain_combination(fs, c))
            projected += k
            per_new.append({"final_state": fs, "events": n, "combinations_satisfied": k})
        row = {
            "threshold_gev": Tf,
            "a_events_accepted": acc[T],
            "a_percent_lost_vs_27": (None if not base_acc else
                                     round(100.0 * (base_acc - acc[T]) / base_acc, 3)),
            "b_gain_not_accepted_by_existing": gain[T],
            "b_gain_percent_of_T27_gain": (None if not base_gain else
                                           round(100.0 * gain[T] / base_gain, 3)),
            "b_gain_percent_of_own_accepted": (None if not acc[T] else
                                               round(100.0 * gain[T] / acc[T], 3)),
            "c_gain_version_b_kept": vb_kept[T],
            "c_gain_version_b_rejected": vb_rej[T],
            "c_n_final_states_total": len(counts),
            "c_n_final_states_ge100": len(big),
            "c_n_final_states_ge100_not_in_current_delivery": len(new_fs),
            "c_projected_new_histograms": projected,
            "c_new_final_states_top10": per_new[:10],
        }
        for region in ("barrel", "endcap"):
            n1, d1, e1 = eff_window(stepb, region, Tf, Tf + 1.0)
            n5, d5, e5 = eff_window(stepb, region, Tf, Tf + 5.0)
            row[f"d_eff_{region}_first_1gev"] = (None if e1 is None else round(e1, 4))
            row[f"d_eff_{region}_first_1gev_counts"] = [n1, d1]
            row[f"d_eff_{region}_T_to_T5"] = (None if e5 is None else round(e5, 4))
            row[f"d_eff_{region}_T_to_T5_counts"] = [n5, d5]
            pl = stepb["results"][region]["plateau"]["eff"]
            row[f"d_eff_{region}_plateau"] = (None if pl is None else round(pl, 4))
            row[f"d_eff_over_plateau_{region}_T_to_T5"] = (
                None if (e5 is None or not pl) else round(e5 / pl, 4))
        rows.append(row)

    out = {
        "what": "Step D: cost/benefit of the offline threshold on the matched "
                "SingleElectron electron",
        "candidate_rule": "HLT_Ele27_WPTight_Gsf fired AND >=1 selected electron "
                          "(after the dR<0.12 overlap removal) matched dR<0.1 to an "
                          "id-11 bit-2 TrigObj with TrigObj_pt >= 27 AND that "
                          "electron's offline pT > T",
        "measurement_only": "this rule is evaluated here for measurement; it is NOT "
                            "implemented in production and no threshold is chosen",
        "n_files": n_files,
        "n_events_ele27_fired": n_ele27,
        "n_accepted_by_any_existing_dataset": n_any_existing,
        "four_dataset_acceptance_counts_on_the_ele27_population": dict(existing_acc),
        "existing_delivery_final_states": len(delivered),
        "min_events_per_final_state": MIN_EVENTS_PER_FINAL_STATE,
        "histogram_projection_method": "number of the 186 mass combinations each new "
                                       "final state satisfies, via the shared "
                                       "physics_calcs.is_finalstate_contain_combination; "
                                       "an UPPER BOUND -- the real delivery's "
                                       "post-processing can only remove histograms",
        "e_trigger_guard_violations": guard,
        "table": rows,
    }
    Path(args.out_json).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out_json).write_text(json.dumps(out, indent=2), encoding="utf-8")

    print(f"{'T':>4} {'accepted':>12} {'%lost':>7} {'gain':>12} {'%ofT27':>8} "
          f"{'FS>=100':>8} {'new FS':>7} {'proj.hist':>10} {'eff_b T..T+5':>13} "
          f"{'eff_e T..T+5':>13}")
    for r in rows:
        print(f"{r['threshold_gev']:>4.0f} {r['a_events_accepted']:>12,} "
              f"{r['a_percent_lost_vs_27']:>7} {r['b_gain_not_accepted_by_existing']:>12,} "
              f"{r['b_gain_percent_of_T27_gain']:>8} {r['c_n_final_states_ge100']:>8} "
              f"{r['c_n_final_states_ge100_not_in_current_delivery']:>7} "
              f"{r['c_projected_new_histograms']:>10} "
              f"{r['d_eff_barrel_T_to_T5']:>13} {r['d_eff_endcap_T_to_T5']:>13}")
    print(f"\nguard violations: {guard}")
    print(f"wrote {args.out_json}")


if __name__ == "__main__":
    main()
