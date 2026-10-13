"""
Luminosity-coverage check, four datasets: aggregation and decision.

Combines the eight per-record JSONs written by
read_lumisections_for_record.py with

  * the certified-lumisection list  -- the 2016 golden JSON, CERN Open Data
    record 14220, committed at data/cms/validated_runs/, and
  * the per-lumisection recorded luminosity -- pp_2016lumibyls.csv, CERN
    Open Data record 1059, produced by CMS's own brilcalc over the
    certified list with the official 2016 normtag (not committed: a 21 MB
    intermediate, downloaded at run time),

and answers, per dataset: how many certified Run2016G+H lumisections its
files contain, how many are absent, how much recorded luminosity sits in
the absent ones, and what that leaves as the effective luminosity.

Method and both ground truths are those of
studies/hgg_cms/impl_checks/lumi_coverage/ (check_coverage.py,
recompute_missing_sections.py, sum_by_era.py, LUMI_DECISION.md). The CSV
parsing here -- run from field 0 before the colon, lumisection from field 1
before the colon, recorded(/fb) from field 6 -- is sum_by_era.py's, unchanged.

Usage:
    python aggregate_coverage.py --inputs-dir <dir of present_*.json> \
        --lumi-csv <pp_2016lumibyls.csv> --out-json <summary.json>
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
GOLDEN_JSON = REPO_ROOT / "data" / "cms" / "validated_runs" / \
    "Cert_271036-284044_13TeV_Legacy2016_Collisions16_JSON.txt"

# Era run ranges and official per-era recorded luminosity: both exactly as
# in studies/hgg_cms/impl_checks/lumi_coverage/sum_by_era.py.
RUN_RANGES = {"Run2016G": (278820, 280385), "Run2016H": (280919, 284044)}
OFFICIAL_PER_ERA_FB = {"Run2016G": 7.653261227, "Run2016H": 8.740119304}
OFFICIAL_TOTAL_FB = 16.393380531

DATASETS = ["DoubleMuon", "SingleMuon", "DoubleEG", "MuonEG"]

# The pre-set rule Matan approved before the measurement was run.
DECISION_THRESHOLD_PCT = 0.1

# What the earlier DoubleEG-only task found, for the re-derivation check
# (LUMI_DECISION.md A.3/A.5).
DOUBLEEG_EXPECTED = {
    "n_missing_Run2016G": 332,
    "n_missing_Run2016H": 350,
    "n_missing_total": 682,
    "missing_lumi_fb": 0.000688616,
    "missing_pct": 0.0042,
}


def parse_lumi_csv(path: Path) -> dict:
    per_ls = {}
    n_rows = 0
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            if line.startswith("#"):
                continue
            parts = line.strip().split(",")
            if len(parts) < 7:
                continue
            n_rows += 1
            run = int(parts[0].split(":")[0])
            ls = int(parts[1].split(":")[0])
            per_ls[(run, ls)] = float(parts[6])
    return {"per_ls": per_ls, "n_rows": n_rows}


def certified_pairs(golden: dict, lo: int, hi: int) -> set:
    pairs = set()
    for run_str, ranges in golden.items():
        run = int(run_str)
        if lo <= run <= hi:
            for a, b in ranges:
                for ls in range(a, b + 1):
                    pairs.add((run, ls))
    return pairs


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--inputs-dir", required=True)
    ap.add_argument("--lumi-csv", required=True)
    ap.add_argument("--out-json", required=True)
    args = ap.parse_args()

    golden = json.loads(GOLDEN_JSON.read_text(encoding="utf-8"))
    csv = parse_lumi_csv(Path(args.lumi_csv))
    per_ls = csv["per_ls"]
    print(f"pp_2016lumibyls.csv: {csv['n_rows']} data rows, "
          f"{len(per_ls)} distinct (run,ls) keys")

    certified_by_era = {era: certified_pairs(golden, lo, hi)
                        for era, (lo, hi) in RUN_RANGES.items()}
    certified_all = certified_by_era["Run2016G"] | certified_by_era["Run2016H"]

    # Sanity check of the ground truth itself, before using it: does the CSV
    # cover every certified G+H section, and do the per-era sums reproduce the
    # official per-era totals? (sum_by_era.py's check, restricted to G+H.)
    ground_truth = {}
    for era, cert in certified_by_era.items():
        summed = sum(per_ls.get(k, 0.0) for k in cert)
        n_absent = len(cert - set(per_ls))
        official = OFFICIAL_PER_ERA_FB[era]
        ground_truth[era] = {
            "n_certified_sections": len(cert),
            "n_certified_sections_absent_from_csv": n_absent,
            "summed_recorded_lumi_fb": summed,
            "official_recorded_lumi_fb": official,
            "difference_pct": 100.0 * (summed - official) / official,
        }
        print(f"  {era}: {len(cert)} certified sections, summed "
              f"{summed:.9f} /fb vs official {official:.9f} /fb "
              f"({100.0 * (summed - official) / official:+.7f}%), "
              f"{n_absent} absent from the CSV")
    ground_truth["total_certified_sections"] = len(certified_all)
    ground_truth["total_summed_recorded_lumi_fb"] = sum(
        ground_truth[e]["summed_recorded_lumi_fb"] for e in RUN_RANGES)
    ground_truth["official_total_fb"] = OFFICIAL_TOTAL_FB

    # Load the eight per-record results.
    inputs_dir = Path(args.inputs_dir)
    present_by_record = {}
    files_by_dataset = {}
    for ds in DATASETS:
        for era_suffix, era in (("G", "Run2016G"), ("H", "Run2016H")):
            key = f"{ds}_{era_suffix}"
            path = inputs_dir / f"present_{key}.json"
            if not path.exists():
                raise SystemExit(f"missing input: {path}")
            rec = json.loads(path.read_text(encoding="utf-8"))
            if rec["n_files_failed"]:
                raise SystemExit(
                    f"{key} reports {rec['n_files_failed']} failed file(s); "
                    "refusing to aggregate an incomplete read")
            if rec["n_files_ok"] != rec["n_files_expected"]:
                raise SystemExit(
                    f"{key}: read {rec['n_files_ok']} of "
                    f"{rec['n_files_expected']} files")
            present_by_record[key] = {
                "era": era,
                "record_id": rec["record_id"],
                "n_files": rec["n_files_expected"],
                "pairs": {(r, ls) for r, ls in rec["present_pairs"]},
            }
            files_by_dataset.setdefault(ds, 0)
            files_by_dataset[ds] += rec["n_files_expected"]

    per_dataset = {}
    for ds in DATASETS:
        by_era = {}
        present_all = set()
        for era_suffix, era in (("G", "Run2016G"), ("H", "Run2016H")):
            rec = present_by_record[f"{ds}_{era_suffix}"]
            cert = certified_by_era[era]
            # Only sections inside this era's certified range count as
            # "present" for it; a file may legitimately carry a handful of
            # non-certified sections, which the golden JSON excludes anyway.
            present = rec["pairs"] & cert
            missing = cert - present
            missing_lumi = sum(per_ls.get(k, 0.0) for k in missing)
            by_era[era] = {
                "record_id": rec["record_id"],
                "n_files": rec["n_files"],
                "n_certified_sections": len(cert),
                "n_present": len(present),
                "n_missing": len(missing),
                "missing_lumi_fb": missing_lumi,
                "n_present_pairs_outside_certified": len(rec["pairs"] - cert),
            }
            present_all |= present

        missing_all = certified_all - present_all
        missing_lumi = sum(per_ls.get(k, 0.0) for k in missing_all)
        missing_pct = 100.0 * missing_lumi / OFFICIAL_TOTAL_FB
        per_dataset[ds] = {
            "n_files": files_by_dataset[ds],
            "n_certified_sections_gh": len(certified_all),
            "n_present": len(present_all),
            "n_missing": len(missing_all),
            "missing_lumi_fb": missing_lumi,
            "missing_pct_of_official_total": missing_pct,
            "effective_lumi_fb": OFFICIAL_TOTAL_FB - missing_lumi,
            "by_era": by_era,
            "n_missing_sections_with_exactly_zero_lumi": sum(
                1 for k in missing_all if per_ls.get(k, 0.0) == 0.0),
            "largest_single_missing_section_lumi_fb": (
                max((per_ls.get(k, 0.0) for k in missing_all), default=0.0)),
        }
        print(f"{ds}: {files_by_dataset[ds]} files, {len(present_all)} of "
              f"{len(certified_all)} certified G+H sections present, "
              f"{len(missing_all)} missing, {missing_lumi:.9f} /fb "
              f"({missing_pct:.4f}%), effective "
              f"{OFFICIAL_TOTAL_FB - missing_lumi:.9f} /fb")

    # Re-derivation check against the earlier DoubleEG-only result.
    deg = per_dataset["DoubleEG"]
    reproduces = {
        "n_missing_Run2016G": (deg["by_era"]["Run2016G"]["n_missing"],
                               DOUBLEEG_EXPECTED["n_missing_Run2016G"]),
        "n_missing_Run2016H": (deg["by_era"]["Run2016H"]["n_missing"],
                               DOUBLEEG_EXPECTED["n_missing_Run2016H"]),
        "n_missing_total": (deg["n_missing"],
                            DOUBLEEG_EXPECTED["n_missing_total"]),
    }
    counts_match = all(a == b for a, b in reproduces.values())
    lumi_rel_diff = abs(deg["missing_lumi_fb"]
                        - DOUBLEEG_EXPECTED["missing_lumi_fb"]) \
        / DOUBLEEG_EXPECTED["missing_lumi_fb"]
    pct_rounds_to_expected = round(deg["missing_pct_of_official_total"], 4) == \
        DOUBLEEG_EXPECTED["missing_pct"]
    doubleeg_rederivation = {
        "counts": {k: {"recomputed": a, "earlier_task": b}
                   for k, (a, b) in reproduces.items()},
        "counts_match": counts_match,
        "missing_lumi_fb_recomputed": deg["missing_lumi_fb"],
        "missing_lumi_fb_earlier_task": DOUBLEEG_EXPECTED["missing_lumi_fb"],
        "missing_lumi_relative_difference": lumi_rel_diff,
        "missing_pct_recomputed": deg["missing_pct_of_official_total"],
        "missing_pct_earlier_task": DOUBLEEG_EXPECTED["missing_pct"],
        "reproduces_0p0042_pct": pct_rounds_to_expected,
        "verdict": ("REPRODUCED" if (counts_match and pct_rounds_to_expected
                                     and lumi_rel_diff < 0.01)
                    else "DID NOT REPRODUCE"),
    }
    print(f"DoubleEG re-derivation: {doubleeg_rederivation['verdict']} "
          f"(counts_match={counts_match}, "
          f"pct={deg['missing_pct_of_official_total']:.4f}% vs 0.0042%)")

    worst = max(per_dataset, key=lambda d: per_dataset[d]["missing_pct_of_official_total"])
    worst_pct = per_dataset[worst]["missing_pct_of_official_total"]
    all_below = all(v["missing_pct_of_official_total"] < DECISION_THRESHOLD_PCT
                    for v in per_dataset.values())
    decision = {
        "threshold_pct": DECISION_THRESHOLD_PCT,
        "worst_dataset": worst,
        "worst_missing_pct": worst_pct,
        "all_datasets_below_threshold": all_below,
        "doubleeg_reproduced": doubleeg_rederivation["verdict"] == "REPRODUCED",
        "rule": ("keep 16.393380531 fb^-1 (+/- 1.2%) unchanged for both "
                 "delivery files"),
        "passed": bool(all_below
                       and doubleeg_rederivation["verdict"] == "REPRODUCED"),
    }
    print(f"DECISION: worst = {worst} at {worst_pct:.4f}% "
          f"(threshold {DECISION_THRESHOLD_PCT}%), "
          f"passed={decision['passed']}")

    out = {
        "what": ("luminosity coverage of the four delivered CMS Open Data "
                 "datasets over certified Run2016G+H lumisections"),
        "ground_truth": {
            "certified_list": ("2016 golden JSON, CERN Open Data record "
                               "14220, committed at data/cms/validated_runs/"
                               "Cert_271036-284044_13TeV_Legacy2016_"
                               "Collisions16_JSON.txt"),
            "per_lumisection_luminosity": ("pp_2016lumibyls.csv, CERN Open "
                                           "Data record 1059, brilcalc "
                                           "--byls over the certified list "
                                           "with normtag_PHYSICS_pp_2016"),
            "official_total_fb": OFFICIAL_TOTAL_FB,
            "official_per_era_fb": OFFICIAL_PER_ERA_FB,
            "run_ranges": {k: list(v) for k, v in RUN_RANGES.items()},
            "checks": ground_truth,
        },
        "per_dataset": per_dataset,
        "doubleeg_rederivation": doubleeg_rederivation,
        "decision": decision,
    }
    Path(args.out_json).write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"wrote {args.out_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
