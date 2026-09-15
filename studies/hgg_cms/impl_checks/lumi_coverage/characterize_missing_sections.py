"""
Implementation task 3, Part A.4-A.5: characterize the certified lumisections
that are missing from our DoubleEG NanoAOD files (exact set from
recompute_missing_sections.py's missing_sections_exact.json), using the
per-lumisection recorded-luminosity table (pp_2016lumibyls.csv, record
1059) for exact (not approximated) luminosity values.

For each missing section: its position within its run (first N / last N /
interior, based on the full certified section list for that run), whether
it belongs to a contiguous run of missing sections, and its recorded
luminosity relative to that run's median certified-section luminosity.
Also produces a histogram comparing missing-section luminosity to the
luminosity distribution of all certified sections, and applies this task's
pre-set decision rule.

Run from anywhere; writes lumi_decision_data.json and
missing_sections_luminosity_hist.png into this directory.
"""
from __future__ import annotations

import json
import statistics
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[2]
GOLDEN_JSON_PATH = REPO_ROOT / "data" / "cms" / "validated_runs" / \
    "Cert_271036-284044_13TeV_Legacy2016_Collisions16_JSON.txt"
CSV_PATH = Path(r"C:\Users\matan\hgg-trigger-20260915\lumi_partA\pp_2016lumibyls.csv")
MISSING_SECTIONS_PATH = HERE / "missing_sections_exact.json"

RUN_RANGES = {"Run2016G": (278820, 280385), "Run2016H": (280919, 284044)}
OFFICIAL_PER_ERA_FB = {"Run2016G": 7.653261227, "Run2016H": 8.740119304}
DECISION_THRESHOLD_PCT = 0.1  # pre-set rule: <0.1% of certified lumi -> negligible


def load_per_ls_recorded() -> dict[tuple[int, int], float]:
    per_ls: dict[tuple[int, int], float] = {}
    with open(CSV_PATH, encoding="utf-8") as f:
        for line in f:
            if line.startswith("#"):
                continue
            parts = line.strip().split(",")
            run = int(parts[0].split(":")[0])
            ls = int(parts[1].split(":")[0])
            per_ls[(run, ls)] = float(parts[6])
    return per_ls


def main():
    golden = json.loads(GOLDEN_JSON_PATH.read_text(encoding="utf-8"))
    per_ls_recorded = load_per_ls_recorded()
    missing_data = json.loads(MISSING_SECTIONS_PATH.read_text(encoding="utf-8"))

    result = {"by_era": {}}
    all_certified_lumis = []
    all_missing_lumis = []

    for era, (lo, hi) in RUN_RANGES.items():
        # Full certified section list per run, in order, for position analysis.
        certified_by_run: dict[int, list[int]] = {}
        for run_str, ranges in golden.items():
            run = int(run_str)
            if lo <= run <= hi:
                sections = []
                for a, b in ranges:
                    sections.extend(range(a, b + 1))
                certified_by_run[run] = sorted(sections)

        missing_pairs = [tuple(p) for p in missing_data["missing_sections_by_era"][era]]
        missing_set = set(missing_pairs)

        era_certified_lumis = [
            per_ls_recorded.get((run, ls), 0.0)
            for run, sections in certified_by_run.items()
            for ls in sections
        ]
        all_certified_lumis.extend(era_certified_lumis)

        exact_missing_lumi = sum(per_ls_recorded.get(k, 0.0) for k in missing_pairs)
        n_missing_not_in_csv = sum(1 for k in missing_pairs if k not in per_ls_recorded)

        per_section_details = []
        by_run_missing: dict[int, list[int]] = {}
        for run, ls in missing_pairs:
            by_run_missing.setdefault(run, []).append(ls)

        for run, missing_ls_list in by_run_missing.items():
            full_sections = certified_by_run.get(run, [])
            n_sections = len(full_sections)
            run_lumis = [per_ls_recorded.get((run, s), 0.0) for s in full_sections]
            run_median = statistics.median(run_lumis) if run_lumis else 0.0
            missing_ls_sorted = sorted(missing_ls_list)
            # contiguous-block detection
            blocks = []
            block = [missing_ls_sorted[0]]
            for ls in missing_ls_sorted[1:]:
                if ls == block[-1] + 1:
                    block.append(ls)
                else:
                    blocks.append(block)
                    block = [ls]
            blocks.append(block)

            for ls in missing_ls_sorted:
                lumi = per_ls_recorded.get((run, ls), 0.0)
                all_missing_lumis.append(lumi)
                idx = full_sections.index(ls) if ls in full_sections else -1
                if idx == -1:
                    position = "not_in_certified_list_for_run(!)"
                elif idx < 3:
                    position = "first_3"
                elif idx >= n_sections - 3:
                    position = "last_3"
                else:
                    position = "interior"
                in_block_len = next((len(b) for b in blocks if ls in b), 1)
                per_section_details.append({
                    "run": run, "ls": ls,
                    "recorded_lumi_fb": lumi,
                    "position_in_run": position,
                    "index_in_run": idx,
                    "n_certified_sections_in_run": n_sections,
                    "contiguous_block_length": in_block_len,
                    "lumi_vs_run_median_ratio": (lumi / run_median) if run_median > 0 else None,
                })

        result["by_era"][era] = {
            "n_missing_sections": len(missing_pairs),
            "n_missing_sections_not_in_lumibyls_csv": n_missing_not_in_csv,
            "exact_missing_lumi_fb": exact_missing_lumi,
            "official_recorded_lumi_fb": OFFICIAL_PER_ERA_FB[era],
            "corrected_covered_lumi_fb": OFFICIAL_PER_ERA_FB[era] - exact_missing_lumi,
            "pct_of_official_missing": 100.0 * exact_missing_lumi / OFFICIAL_PER_ERA_FB[era],
            "n_runs_affected": len(by_run_missing),
            "per_section_details": per_section_details,
        }

    total_official = sum(OFFICIAL_PER_ERA_FB.values())
    total_missing_exact = sum(v["exact_missing_lumi_fb"] for v in result["by_era"].values())
    total_corrected = total_official - total_missing_exact
    pct_missing = 100.0 * total_missing_exact / total_official

    decision = (
        "negligible_use_official"
        if pct_missing < DECISION_THRESHOLD_PCT
        else "use_corrected_value"
    )

    # Largest-missing-luminosity runs, across both eras
    all_run_rows = []
    for era, era_data in result["by_era"].items():
        by_run_agg: dict[int, float] = {}
        for d in era_data["per_section_details"]:
            by_run_agg[d["run"]] = by_run_agg.get(d["run"], 0.0) + d["recorded_lumi_fb"]
        for run, lumi in by_run_agg.items():
            all_run_rows.append({"era": era, "run": run, "missing_lumi_fb": lumi})
    all_run_rows.sort(key=lambda r: -r["missing_lumi_fb"])

    summary = {
        "decision_threshold_pct": DECISION_THRESHOLD_PCT,
        "total_official_recorded_lumi_fb": total_official,
        "total_exact_missing_lumi_fb": total_missing_exact,
        "total_corrected_covered_lumi_fb": total_corrected,
        "pct_of_official_missing": pct_missing,
        "decision": decision,
        "cms_2016_luminosity_uncertainty_pct": 1.2,
        "cms_2016_luminosity_uncertainty_source": (
            "https://opendata.cern.ch/record/1059 abstract, citing "
            "https://cds.cern.ch/record/2759951 (\"Precision luminosity "
            "measurement in proton-proton collisions at sqrt(s)=13 TeV in "
            "2015 and 2016 at CMS\")"
        ),
        "top_20_runs_by_missing_lumi": all_run_rows[:20],
        "by_era": {
            era: {k: v for k, v in d.items() if k != "per_section_details"}
            for era, d in result["by_era"].items()
        },
    }

    with open(HERE / "lumi_decision_data.json", "w", encoding="utf-8") as f:
        json.dump({**summary, "by_era_detailed": result["by_era"]}, f, indent=2)

    print(json.dumps(summary, indent=2))

    # Plot: distribution of missing-section luminosity vs all certified sections
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import numpy as np

        fig, ax = plt.subplots(figsize=(8, 5))
        bins = np.logspace(-9, -2, 60)
        ax.hist(np.clip(all_certified_lumis, 1e-9, None), bins=bins, alpha=0.5,
                label=f"all certified sections (n={len(all_certified_lumis)})", density=True)
        ax.hist(np.clip(all_missing_lumis, 1e-9, None), bins=bins, alpha=0.7,
                label=f"missing sections (n={len(all_missing_lumis)})", density=True)
        ax.set_xscale("log")
        ax.set_xlabel("recorded luminosity per lumisection (/fb)")
        ax.set_ylabel("probability density")
        ax.set_title("Missing vs. all certified lumisections: recorded luminosity per section")
        ax.legend()
        fig.tight_layout()
        fig.savefig(HERE / "missing_sections_luminosity_hist.png", dpi=150)
        print(f"wrote {HERE / 'missing_sections_luminosity_hist.png'}")
    except ImportError:
        print("matplotlib not available; skipping plot")


if __name__ == "__main__":
    main()
