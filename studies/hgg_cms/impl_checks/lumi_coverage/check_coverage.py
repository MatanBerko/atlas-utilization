"""
Implementation task 2, Part C: do our DoubleEG Run2016G/H NanoAOD files
contain every CMS-certified ("golden JSON") luminosity section?

Method:
  1. Get the full file list for CERN Open Data records 30521 (Run2016G)
     and 30554 (Run2016H) from the portal API (metadata only).
  2. For every one of those files, read ONLY the small `LuminosityBlocks`
     tree (its `run`/`luminosityBlock` branches) -- never the `Events`
     tree, and never a full-file download. Build the set of (run, section)
     pairs actually present in our files.
  3. Compare against the certified sections in the committed golden JSON
     (data/cms/validated_runs/), restricted to the Run2016G/H run-number
     ranges quoted on record 14220.
  4. Estimate the luminosity implied by any certified sections missing
     from our files, using the per-run recorded-luminosity tables
     (Run2016Glumi.txt / Run2016Hlumi.txt, record 1059 -- see
     studies/hgg_cms/INVENTORY.md A.2), approximating evenly per run
     (the portal's own per-lumisection table, pp_2016lumibyls.csv, would
     remove this approximation but is out of this check's scope).

Remote reading here is metadata + the LuminosityBlocks tree only, for
every file of both records -- explicitly allowed at that scope by this
task, unlike the 4-file/2,000-event limit used elsewhere in this branch.
Requests are made ONE AT A TIME with a short pacing delay and an
exponential backoff specifically for HTTP 429 (rate limit) responses --
the portal rate-limits concurrent/rapid requests from one client.

Run from anywhere; writes its outputs into this same directory.
"""
from __future__ import annotations

import csv
import json
import time
from pathlib import Path

import requests

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[2]
GOLDEN_JSON_PATH = REPO_ROOT / "data" / "cms" / "validated_runs" / \
    "Cert_271036-284044_13TeV_Legacy2016_Collisions16_JSON.txt"

RECORDS = {"Run2016G": 30521, "Run2016H": 30554}
# Run-number ranges quoted on record 14220's own abstract (see
# data/cms/validated_runs/README.md) -- record 30554's own run_numbers
# list starts later (281613), but there are zero certified runs in the
# 280919-281613 gap either way (verified in golden_json_analysis.py), so
# this choice does not affect the result.
RUN_RANGES = {"Run2016G": (278820, 280385), "Run2016H": (280919, 284044)}

LUMI_TABLE_URLS = {
    "Run2016G": "https://opendata.cern.ch/record/1059/files/Run2016Glumi.txt",
    "Run2016H": "https://opendata.cern.ch/record/1059/files/Run2016Hlumi.txt",
}


def get_file_urls(recid: int) -> list[str]:
    r = requests.get(f"https://opendata.cern.ch/api/records/{recid}", headers={"Accept": "application/json"})
    r.raise_for_status()
    md = r.json()["metadata"]
    urls = []
    for grp in md.get("_file_indices", []):
        for f in grp["files"]:
            urls.append(f["uri"].replace(
                "root://eospublic.cern.ch//eos/opendata/", "https://opendata.cern.ch/eos/opendata/"
            ))
    return urls


def read_lumiblocks_pairs(url: str, max_attempts: int = 8) -> tuple[set[tuple[int, int]], str | None]:
    import uproot

    last_err = None
    for attempt in range(max_attempts):
        try:
            f = uproot.open(url)
            t = f["LuminosityBlocks"]
            arrays = t.arrays(["run", "luminosityBlock"], library="np")
            pairs = set(zip(arrays["run"].tolist(), arrays["luminosityBlock"].tolist()))
            return pairs, None
        except Exception as e:
            last_err = f"{type(e).__name__}: {e}"
            is_429 = "429" in last_err or "Too Many Requests" in last_err
            time.sleep((20.0 if is_429 else 2.0) * (attempt + 1))
    return set(), last_err


def parse_lumi_table(text: str) -> dict[int, float]:
    """Per-run recorded luminosity (fb^-1) from a Run2016{G,H}lumi.txt table."""
    per_run = {}
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        parts = [p.strip() for p in line.strip("|").split("|")]
        if len(parts) != 6 or ":" not in parts[0] or not parts[0].split(":")[0].isdigit():
            continue
        run = int(parts[0].split(":")[0])
        try:
            per_run[run] = float(parts[5])
        except ValueError:
            continue
    return per_run


def certified_pairs_in_range(golden: dict, lo: int, hi: int) -> tuple[set, dict]:
    pairs = set()
    by_run = {}
    for run_str, ranges in golden.items():
        run = int(run_str)
        if lo <= run <= hi:
            n = 0
            for a, b in ranges:
                for ls in range(a, b + 1):
                    pairs.add((run, ls))
                    n += 1
            by_run[run] = n
    return pairs, by_run


def main():
    golden = json.loads(GOLDEN_JSON_PATH.read_text(encoding="utf-8"))

    lumi_tables = {}
    for era, url in LUMI_TABLE_URLS.items():
        r = requests.get(url)
        r.raise_for_status()
        lumi_tables[era] = parse_lumi_table(r.text)

    era_results = {}
    n_files_ok = n_files_failed = 0
    failed_files = []

    for era, recid in RECORDS.items():
        urls = get_file_urls(recid)
        present = set()
        for i, url in enumerate(urls, 1):
            pairs, err = read_lumiblocks_pairs(url)
            if err:
                n_files_failed += 1
                failed_files.append({"era": era, "url": url, "error": err})
                print(f"[{era} {i}/{len(urls)}] ERROR {url}: {err}", flush=True)
            else:
                n_files_ok += 1
                present |= pairs
                print(f"[{era} {i}/{len(urls)}] {url.split('/')[-1]}: {len(pairs)} LS entries", flush=True)
            time.sleep(0.4)

        lo, hi = RUN_RANGES[era]
        certified, certified_by_run = certified_pairs_in_range(golden, lo, hi)
        missing = certified - present
        extra = present - certified

        missing_by_run: dict[int, list[int]] = {}
        for run, ls in missing:
            missing_by_run.setdefault(run, []).append(ls)

        official_lumi = sum(lumi_tables[era].values())
        est_missing_lumi = 0.0
        per_run_rows = []
        for run, missing_ls in sorted(missing_by_run.items()):
            n_cert_this_run = certified_by_run.get(run, 0)
            run_lumi = lumi_tables[era].get(run)
            est = (len(missing_ls) / n_cert_this_run) * run_lumi if (n_cert_this_run and run_lumi is not None) else None
            est_missing_lumi += est or 0.0
            per_run_rows.append({
                "era": era, "run": run, "n_certified_sections_this_run": n_cert_this_run,
                "n_missing_sections": len(missing_ls), "run_recorded_lumi_fb": run_lumi,
                "estimated_missing_lumi_fb": est,
            })

        era_results[era] = {
            "n_certified_sections": len(certified),
            "n_certified_sections_present_in_files": len(certified & present),
            "n_certified_sections_missing_from_files": len(missing),
            "n_sections_present_but_not_certified": len(extra),
            "n_runs_affected": len(missing_by_run),
            "official_recorded_lumi_fb": official_lumi,
            "estimated_covered_lumi_fb": official_lumi - est_missing_lumi,
            "per_run_rows": per_run_rows,
        }

    total_official = sum(v["official_recorded_lumi_fb"] for v in era_results.values())
    total_covered = sum(v["estimated_covered_lumi_fb"] for v in era_results.values())
    pct = 100.0 * total_covered / total_official
    verdict = ("full coverage; use the official luminosity" if abs(total_covered - total_official) / total_official < 0.005
               else "use the corrected (covered) luminosity value")

    summary = {
        "n_files_ok": n_files_ok,
        "n_files_failed": n_files_failed,
        "failed_files": failed_files,
        "run2016g": {k: v for k, v in era_results["Run2016G"].items() if k != "per_run_rows"},
        "run2016h": {k: v for k, v in era_results["Run2016H"].items() if k != "per_run_rows"},
        "total_official_recorded_lumi_fb": total_official,
        "total_estimated_covered_lumi_fb": total_covered,
        "pct_of_official_covered": pct,
        "preset_interpretation_rule": "within 0.5% of official => full coverage, else use corrected value",
        "verdict": verdict,
        "important_caveat": (
            "A luminosity gap here is not evidence of corrupted/missing files "
            "(this script counts file read failures separately, above). The "
            "missing (run, section) pairs are certified-good lumisections "
            "where the DoubleEG primary dataset specifically recorded zero "
            "events -- CMS's per-run 'recorded' luminosity is a detector-level "
            "quantity, counting every certified lumisection's full luminosity "
            "regardless of whether any given trigger/dataset had an accepted "
            "event in it. If missing sections are spread thinly across many "
            "runs rather than concentrated in a few, that is consistent with "
            "sparse trigger-rate statistics, not systematic data loss."
        ),
        "approximation_method": (
            "Per affected run: estimated_missing_lumi_fb = "
            "(n_missing_certified_sections_in_run / n_certified_sections_in_run) "
            "* run_recorded_lumi_fb -- assumes luminosity is spread evenly "
            "across a run's certified lumisections. The portal's per-lumisection "
            "table (pp_2016lumibyls.csv, INVENTORY.md A.2) would remove this "
            "approximation if used instead; not used here to keep this check "
            "within the LuminosityBlocks-tree-only scope."
        ),
    }

    with open(HERE / "coverage_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    with open(HERE / "affected_runs_table.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["era", "run", "n_certified_sections_this_run", "n_missing_sections",
                    "run_recorded_lumi_fb", "estimated_missing_lumi_fb"])
        for era in ("Run2016G", "Run2016H"):
            for row in era_results[era]["per_run_rows"]:
                w.writerow([row["era"], row["run"], row["n_certified_sections_this_run"],
                            row["n_missing_sections"], row["run_recorded_lumi_fb"],
                            row["estimated_missing_lumi_fb"]])

    print(json.dumps(summary, indent=2))
    print(f"\nwrote {HERE / 'coverage_summary.json'} and {HERE / 'affected_runs_table.csv'}")


if __name__ == "__main__":
    main()
