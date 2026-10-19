#!/usr/bin/env python
"""
SingleElectron re-check (19 Oct 2026), Part 1B: the b-jet-dependent Step D
columns at DeepJet 0.2598 vs 0.25.

Both inputs are made by the UNCHANGED 7 Oct aggregate_threshold.py, on the
1A re-run (0.2598) and on the 1B run (0.25, same script via the override).
Columns (a), (b) and the efficiencies (d) cannot depend on b-tag (the
acceptance uses only electrons and trigger objects); this script asserts
they are identical and reports what does change: Version B kept/rejected,
final states >= 100, new categories, projected histograms, and which final
states enter or leave the >= 100 list. The per-file final-state counts are
read again here to list those final states.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

B_INDEPENDENT = ("a_events_accepted", "b_gain_not_accepted_by_existing", "d_eff_barrel_T_to_T5",
                 "d_eff_endcap_T_to_T5", "d_eff_barrel_first_1gev", "d_eff_endcap_first_1gev")
B_DEPENDENT = ("c_gain_version_b_kept", "c_gain_version_b_rejected", "c_n_final_states_total",
               "c_n_final_states_ge100", "c_n_final_states_ge100_not_in_current_delivery",
               "c_projected_new_histograms")


def fs_counts(d: Path) -> dict:
    out = {}
    for f in sorted(d.glob("tnp_*.json")):
        res = (json.loads(f.read_text()).get("threshold_scan") or {}).get("results", {})
        for T, blk in res.items():
            out.setdefault(T, Counter()).update(blk["final_state_counts"])
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--a-json", required=True, help="stepD_thresholds.json at 0.2598")
    ap.add_argument("--b-json", required=True, help="stepD_thresholds.json at 0.25")
    ap.add_argument("--a-dir", required=True)
    ap.add_argument("--b-dir", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    a = {r["threshold_gev"]: r for r in json.loads(Path(args.a_json).read_text())["table"]}
    b = {r["threshold_gev"]: r for r in json.loads(Path(args.b_json).read_text())["table"]}
    fa, fb = fs_counts(Path(args.a_dir)), fs_counts(Path(args.b_dir))
    rows, problems = [], []
    for T in sorted(a):
        for k in B_INDEPENDENT:
            if a[T][k] != b[T][k]:
                problems.append(f"T={T}: {k} differs ({a[T][k]} vs {b[T][k]}) although it cannot depend on b-tag")
        key = str(T)
        ca, cb = fa.get(key, Counter()), fb.get(key, Counter())
        big_a = {f for f, n in ca.items() if n >= 100}
        big_b = {f for f, n in cb.items() if n >= 100}
        row = {"threshold_gev": T, **{f"{k}_0p2598": a[T][k] for k in B_DEPENDENT},
               **{f"{k}_0p25": b[T][k] for k in B_DEPENDENT},
               "fs_ge100_entering": sorted(big_b - big_a), "fs_ge100_leaving": sorted(big_a - big_b),
               "n_by_nb_0p2598": {}, "n_by_nb_0p25": {}}
        for tag, c in (("0p2598", ca), ("0p25", cb)):
            nb = Counter()
            for f, n in c.items():
                nb[min(int(f.split("_")[-1].rstrip("b")), 3)] += n
            row[f"n_by_nb_{tag}"] = {f"{k}b" if k < 3 else "3b+": nb[k] for k in range(4)}
        rows.append(row)
    out = {"what": "Step D b-dependent columns, DeepJet 0.2598 vs 0.25", "b_independent_checks_failed": problems,
           "table": rows}
    Path(args.out).write_text(json.dumps(out, indent=1))
    for r in rows:
        print(f"T={r['threshold_gev']:.0f}: FS>=100 {r['c_n_final_states_ge100_0p2598']} -> {r['c_n_final_states_ge100_0p25']}, "
              f"new {r['c_n_final_states_ge100_not_in_current_delivery_0p2598']} -> {r['c_n_final_states_ge100_not_in_current_delivery_0p25']}, "
              f"proj.hist {r['c_projected_new_histograms_0p2598']} -> {r['c_projected_new_histograms_0p25']}, "
              f"VB kept {r['c_gain_version_b_kept_0p2598']:,} -> {r['c_gain_version_b_kept_0p25']:,}; "
              f"enter {r['fs_ge100_entering']} leave {r['fs_ge100_leaving']}")
    print("b-independent check problems:", problems or "none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
