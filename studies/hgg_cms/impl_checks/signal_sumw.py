"""
Implementation task 5, Part A4: sum-of-weights table for all six postVFP
H->gamma-gamma signal production modes.

Reads ONLY the "Runs" tree of every file in each record (one entry per
file in every case checked here; summed generically regardless) --
genEventSumw, genEventCount, genEventSumw2 -- never the (much larger)
"Events" tree, for every file. This is the exception explicitly allowed by
this task's remote-reading limits.

Requests are made ONE AT A TIME with a pacing delay and an exponential
backoff specifically for HTTP 429 (rate limit) responses, following the
same pattern used in every earlier task's real-file checks in this
directory (the portal rate-limits concurrent/rapid requests from one
client).

Run from anywhere; writes signal_sumw.json into this directory.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import requests

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[2]

SIGNAL_RECORDS = {
    "37350": "ggH",
    "68497": "VBF",
    "71013": "WplusH",
    "70173": "WminusH",
    "74132": "ZH",
    "67611": "ttH",
}

# Cross sections (pb) and branching ratio, from studies/hgg_cms/records.json
# (study/hgg-cms-inventory branch), themselves sourced from the LHCHWG
# Yellow Report 4 tables -- see that file's own "source" field.
CROSS_SECTIONS_PB = {
    "ggH": 48.58,
    "VBF": 3.782,
    "WplusH": 0.84,
    "WminusH": 0.5328,
    "ZH": 0.8839,
    "ttH": 0.5071,
}
BR_HGG = 0.00227


def get_file_urls(recid: str) -> list[str]:
    r = requests.get(
        f"https://opendata.cern.ch/api/records/{recid}", headers={"Accept": "application/json"}
    )
    r.raise_for_status()
    md = r.json()["metadata"]
    urls = []
    for grp in md.get("_file_indices", []):
        for f in grp["files"]:
            urls.append(
                f["uri"].replace(
                    "root://eospublic.cern.ch//eos/opendata/",
                    "https://opendata.cern.ch/eos/opendata/",
                )
            )
    dataset_title = md.get("title")
    return urls, dataset_title


def read_runs_tree(url: str, max_attempts: int = 8):
    import uproot

    last_err = None
    for attempt in range(max_attempts):
        try:
            f = uproot.open(url)
            t = f["Runs"]
            arrays = t.arrays(
                ["genEventSumw", "genEventCount", "genEventSumw2"], library="np"
            )
            return {
                "n_entries": t.num_entries,
                "genEventSumw": float(arrays["genEventSumw"].sum()),
                "genEventCount": int(arrays["genEventCount"].sum()),
                "genEventSumw2": float(arrays["genEventSumw2"].sum()),
            }, None
        except Exception as e:
            last_err = f"{type(e).__name__}: {e}"
            is_429 = "429" in last_err or "Too Many Requests" in last_err
            time.sleep((20.0 if is_429 else 2.0) * (attempt + 1))
    return None, last_err


def main():
    results = {}
    for recid, label in SIGNAL_RECORDS.items():
        urls, dataset_title = get_file_urls(recid)
        n_files = len(urls)
        total_sumw = 0.0
        total_count = 0
        total_sumw2 = 0.0
        max_entries_per_file = 0
        unreadable = []
        n_ok = 0

        for i, url in enumerate(urls, 1):
            res, err = read_runs_tree(url)
            if err:
                unreadable.append({"url": url, "error": err})
                print(f"[{label} {recid} {i}/{n_files}] ERROR {url}: {err}", flush=True)
            else:
                n_ok += 1
                total_sumw += res["genEventSumw"]
                total_count += res["genEventCount"]
                total_sumw2 += res["genEventSumw2"]
                max_entries_per_file = max(max_entries_per_file, res["n_entries"])
                print(
                    f"[{label} {recid} {i}/{n_files}] {url.split('/')[-1]}: "
                    f"{res['n_entries']} Runs entries, genEventSumw={res['genEventSumw']:.4f}, "
                    f"genEventCount={res['genEventCount']}",
                    flush=True,
                )
            time.sleep(0.4)

        results[recid] = {
            "label": label,
            "dataset": dataset_title,
            "n_files": n_files,
            "n_files_ok": n_ok,
            "n_files_unreadable": len(unreadable),
            "unreadable_files": unreadable,
            "max_runs_tree_entries_seen_in_one_file": max_entries_per_file,
            "sum_genEventSumw_all_files": total_sumw,
            "sum_genEventCount_all_files": total_count,
            "sum_genEventSumw2_all_files": total_sumw2,
            "cross_section_pb": CROSS_SECTIONS_PB.get(label),
            "branching_ratio_Hgammagamma": BR_HGG,
            "coverage_label": "all files in record (this table), NOT necessarily the files a given pipeline run actually processed",
        }
        print(f"{label} ({recid}): {n_ok}/{n_files} files OK, "
              f"sum genEventSumw={total_sumw:.4f}, sum genEventCount={total_count}")

    summary = {
        "method": (
            "For every file of each of the 6 postVFP H->gamma-gamma signal "
            "records, only the small 'Runs' tree was read (genEventSumw, "
            "genEventCount, genEventSumw2) -- never the much larger 'Events' "
            "tree. Sums are over ALL files in the record as currently listed "
            "on the portal, not necessarily the files a specific pipeline "
            "run processed."
        ),
        "important_note": (
            "task 6's normalization (N_expected = sigma * BR * L * "
            "(sum selected genWeight) / (sum genEventSumw)) MUST use the "
            "sum of genEventSumw over exactly the files that pipeline run "
            "actually processed successfully -- which equals this table's "
            "'all files in record' sum ONLY if every file in the record was "
            "processed without failure. If any file failed to open/parse, "
            "the correct denominator is smaller than this table's number, "
            "and using this table directly would silently bias the result."
        ),
        "negative_weight_fraction_note": (
            "The fraction of negative-weight events cannot be derived from "
            "the Runs tree alone (genEventSumw is a single summed number, "
            "not a per-event breakdown); it requires reading the full "
            "per-event genWeight branch, which this task explicitly limits "
            "to at most 3 files (see the separate genweight_vs_sumw_crosscheck.json "
            "produced by object_field_survival-style scripts for this task -- "
            "not computed here for every file/record)."
        ),
        "records": results,
    }

    with open(HERE / "signal_sumw.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    print(f"\nwrote {HERE / 'signal_sumw.json'}")


if __name__ == "__main__":
    main()
