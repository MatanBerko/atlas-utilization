"""
Implementation task 3, Part A.2: sanity-check the per-lumisection luminosity
table (pp_2016lumibyls.csv, CERN Open Data record 1059) against the
official per-era recorded-luminosity totals (Run2016Glumi.txt /
Run2016Hlumi.txt, same record).

pp_2016lumibyls.csv itself (21,137,550 bytes) is NOT committed to the repo
(a large intermediate download, per this task's scope) -- download it
first from https://opendata.cern.ch/record/1059/files/pp_2016lumibyls.csv
and pass its local path as this script's one argument.

Usage: python sum_by_era.py <path to pp_2016lumibyls.csv>

Writes sum_by_era_results.json into this directory.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[3]
GOLDEN_JSON = REPO_ROOT / "data" / "cms" / "validated_runs" / \
    "Cert_271036-284044_13TeV_Legacy2016_Collisions16_JSON.txt"

RUN_RANGES = {"Run2016G": (278820, 280385), "Run2016H": (280919, 284044)}
OFFICIAL_PER_ERA_FB = {"Run2016G": 7.653261227, "Run2016H": 8.740119304}


def main():
    csv_path = Path(sys.argv[1])
    golden = json.loads(GOLDEN_JSON.read_text(encoding="utf-8"))

    # per-(run,ls) recorded luminosity, in fb^-1, straight from brilcalc's own table
    per_ls_recorded: dict[tuple[int, int], float] = {}
    n_rows = 0
    with open(csv_path, encoding="utf-8") as f:
        for line in f:
            if line.startswith("#"):
                continue
            n_rows += 1
            parts = line.strip().split(",")
            run = int(parts[0].split(":")[0])
            ls = int(parts[1].split(":")[0])
            recorded = float(parts[6])
            per_ls_recorded[(run, ls)] = recorded

    print(f"parsed {n_rows} data rows, {len(per_ls_recorded)} unique (run,ls) keys")

    # Independent check of brilcalc's own footer self-report ("(run,ls) in
    # json but not in results: []"): does every certified pair (all 2016
    # eras) appear as a row, and is every row a certified pair?
    all_certified = set()
    for run_str, ranges in golden.items():
        run = int(run_str)
        for a, b in ranges:
            for ls in range(a, b + 1):
                all_certified.add((run, ls))

    missing_from_csv = all_certified - set(per_ls_recorded.keys())
    extra_in_csv = set(per_ls_recorded.keys()) - all_certified
    print(f"certified (all eras, from golden JSON): {len(all_certified)}")
    print(f"certified pairs missing from pp_2016lumibyls.csv: {len(missing_from_csv)}")
    print(f"csv rows not in the golden JSON: {len(extra_in_csv)}")

    results = {}
    for era, (lo, hi) in RUN_RANGES.items():
        era_certified = {(r, l) for (r, l) in all_certified if lo <= r <= hi}
        total = sum(per_ls_recorded.get(k, 0.0) for k in era_certified)
        n_missing_from_csv = len(era_certified - set(per_ls_recorded.keys()))
        results[era] = {
            "n_certified_sections": len(era_certified),
            "n_certified_sections_missing_from_csv": n_missing_from_csv,
            "summed_recorded_lumi_fb": total,
        }
        diff_pct = 100.0 * (total - OFFICIAL_PER_ERA_FB[era]) / OFFICIAL_PER_ERA_FB[era]
        print(f"{era}: {len(era_certified)} certified sections, summed recorded = {total:.9f} /fb, "
              f"official={OFFICIAL_PER_ERA_FB[era]:.9f} /fb, diff={diff_pct:+.7f}%, "
              f"missing-from-csv={n_missing_from_csv}")

    with open(HERE / "sum_by_era_results.json", "w", encoding="utf-8") as f:
        json.dump({
            "n_csv_rows": n_rows,
            "n_certified_all_eras": len(all_certified),
            "n_certified_missing_from_csv_all_eras": len(missing_from_csv),
            "n_csv_rows_not_certified": len(extra_in_csv),
            "by_era": results,
            "official_per_era_fb": OFFICIAL_PER_ERA_FB,
        }, f, indent=2)
    print(f"wrote {HERE / 'sum_by_era_results.json'}")


if __name__ == "__main__":
    main()
