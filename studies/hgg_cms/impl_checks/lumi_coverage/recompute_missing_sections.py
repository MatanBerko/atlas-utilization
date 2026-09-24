"""
Implementation task 3, Part A: re-derive the exact set of certified (run,
luminosityBlock) pairs missing from our DoubleEG Run2016G/H NanoAOD files,
using the same method as implementation task 2's check_coverage.py (which
this script is otherwise identical to, up to the point of saving *exact*
missing-section pairs rather than only aggregated per-run counts).

Re-reads ONLY the small LuminosityBlocks tree of every file of records
30521 (Run2016G) and 30554 (Run2016H) -- allowed at this scope per this
task's remote-reading limits ("the LuminosityBlocks trees already covered
in task 2 may be re-read if needed").

Run from anywhere; writes missing_sections_exact.json into this directory.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import requests

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[3]
GOLDEN_JSON_PATH = REPO_ROOT / "data" / "cms" / "validated_runs" / \
    "Cert_271036-284044_13TeV_Legacy2016_Collisions16_JSON.txt"

RECORDS = {"Run2016G": 30521, "Run2016H": 30554}
RUN_RANGES = {"Run2016G": (278820, 280385), "Run2016H": (280919, 284044)}


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


def certified_pairs_in_range(golden: dict, lo: int, hi: int) -> set:
    pairs = set()
    for run_str, ranges in golden.items():
        run = int(run_str)
        if lo <= run <= hi:
            for a, b in ranges:
                for ls in range(a, b + 1):
                    pairs.add((run, ls))
    return pairs


def main():
    golden = json.loads(GOLDEN_JSON_PATH.read_text(encoding="utf-8"))

    n_files_ok = n_files_failed = 0
    failed_files = []
    missing_by_era: dict[str, list[list[int]]] = {}

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
        certified = certified_pairs_in_range(golden, lo, hi)
        missing = certified - present
        missing_by_era[era] = sorted(list(pair) for pair in missing)
        print(f"{era}: {len(certified)} certified, {len(present)} present, {len(missing)} missing")

    out = {
        "n_files_ok": n_files_ok,
        "n_files_failed": n_files_failed,
        "failed_files": failed_files,
        "missing_sections_by_era": missing_by_era,
        "n_missing_run2016g": len(missing_by_era["Run2016G"]),
        "n_missing_run2016h": len(missing_by_era["Run2016H"]),
    }
    with open(HERE / "missing_sections_exact.json", "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print(f"wrote {HERE / 'missing_sections_exact.json'}")


if __name__ == "__main__":
    main()
