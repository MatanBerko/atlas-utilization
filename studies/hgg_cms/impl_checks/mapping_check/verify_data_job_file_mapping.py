"""
Full-run prep, Part 1: offline verification of the data array job's
index -> file mapping.

Uses the REAL utils.batching.get_batch_slice_by_year (imported, not
reimplemented) against a LOCALLY CACHED copy of both DoubleEG records'
file lists (cms_hgg_data_file_lists.json, fetched once from the CERN
Open Data record filepage API -- a metadata-only read, no event data).

Prints, for every index 1..133: the record and file URL it would get.
Then proves:
  - every one of the 133 files appears in EXACTLY one index
  - no index is empty
  - no index has more than one file
  - both records are fully covered (47 + 86 = 133)

This does NOT prove the mapping is stable ACROSS independently-fetched
runs (each real array job fetches its own copy of these file lists fresh
from the portal, at a different wall-clock time, with no shared cache --
see this task's own report for why that matters). It only proves that,
GIVEN one fixed, fetched file-list ordering, get_batch_slice_by_year
distributes it deterministically and completely across all 133 batch
indices.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT))

from utils.batching import get_batch_slice_by_year  # noqa: E402

CACHE_PATH = Path(__file__).resolve().parent / "cms_hgg_data_file_lists.json"
TOTAL_BATCHES = 133


def main():
    file_lists = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
    total_files = sum(len(v) for v in file_lists.values())
    print(f"Loaded {len(file_lists)} record(s), {total_files} total files:")
    for key, urls in file_lists.items():
        print(f"  {key}: {len(urls)} files")

    index_to_file = {}
    for i in range(1, TOTAL_BATCHES + 1):
        sliced = get_batch_slice_by_year(file_lists, i, TOTAL_BATCHES)
        n = sum(len(v) for v in sliced.values())
        if n != 1:
            index_to_file[i] = {"ERROR": f"expected exactly 1 file, got {n}", "sliced": sliced}
            continue
        (record_key, urls), = sliced.items()
        index_to_file[i] = {"record": record_key, "url": urls[0]}

    # ---- Print the full mapping ----
    print("\n=== index -> file mapping ===")
    for i in range(1, TOTAL_BATCHES + 1):
        entry = index_to_file[i]
        if "ERROR" in entry:
            print(f"  {i}: ERROR -- {entry['ERROR']}")
        else:
            print(f"  {i}: {entry['record']} -> {entry['url']}")

    # ---- Proofs ----
    errors = [i for i, e in index_to_file.items() if "ERROR" in e]
    all_assigned_urls = [e["url"] for i, e in index_to_file.items() if "ERROR" not in e]
    all_source_urls = [u for urls in file_lists.values() for u in urls]

    url_counts = {}
    for u in all_assigned_urls:
        url_counts[u] = url_counts.get(u, 0) + 1
    duplicated = {u: c for u, c in url_counts.items() if c != 1}
    missing = sorted(set(all_source_urls) - set(all_assigned_urls))
    extra = sorted(set(all_assigned_urls) - set(all_source_urls))

    per_record_assigned = {}
    for i, e in index_to_file.items():
        if "ERROR" in e:
            continue
        per_record_assigned.setdefault(e["record"], []).append(e["url"])

    print("\n=== proofs ===")
    print(f"no-empty / exactly-one-file-per-index errors: {errors if errors else 'NONE'}")
    print(f"every file appears exactly once (no duplicates): {'YES' if not duplicated else 'NO -- ' + str(duplicated)}")
    print(f"no file missing from the mapping: {'YES' if not missing else 'NO -- ' + str(missing)}")
    print(f"no unexpected/extra url in the mapping: {'YES' if not extra else 'NO -- ' + str(extra)}")
    for record_key, urls in file_lists.items():
        assigned = per_record_assigned.get(record_key, [])
        print(f"{record_key}: {len(assigned)} assigned / {len(urls)} in source list -- "
              f"{'FULLY COVERED' if len(assigned) == len(urls) else 'MISMATCH'}")

    ok = (not errors) and (not duplicated) and (not missing) and (not extra) and all(
        len(per_record_assigned.get(k, [])) == len(v) for k, v in file_lists.items()
    )
    print(f"\nOVERALL: {'PASS' if ok else 'FAIL'} -- "
          f"(GIVEN this one fixed fetch of the file lists; see module docstring "
          f"for what this does NOT prove)")

    out = {
        "total_batches": TOTAL_BATCHES,
        "index_to_file": index_to_file,
        "proofs": {
            "errors": errors,
            "duplicated": duplicated,
            "missing": missing,
            "extra": extra,
            "overall_pass": ok,
        },
    }
    out_path = Path(__file__).resolve().parent / "data_job_file_mapping_results.json"
    out_path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"\nwrote {out_path}")


if __name__ == "__main__":
    main()
