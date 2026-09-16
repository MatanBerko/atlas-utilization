"""
Implementation task 5, Part A3 test 5a: for up to 3 postVFP signal files,
read the FULL genWeight branch (single-branch read, allowed explicitly by
this task's remote-reading limits) and compare its sum against that same
file's genEventSumw from the Runs tree. Also reports each file's
negative-weight fraction (derivable only from the full per-event branch,
not from the Runs tree's single summed number).

Run from anywhere; writes genweight_vs_sumw_crosscheck.json into this
directory.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import uproot

HERE = Path(__file__).resolve().parent

# One file each from three different production modes (ggH, VBF, ttH),
# spanning two different generators (POWHEG for ggH, aMC@NLO for VBF/ttH)
# and resolved dynamically via the portal's own file list (rather than a
# hardcoded URL) for robustness.
RECORD_IDS = {
    "ggH (37350)": "37350",
    "VBF (68497)": "68497",
    "ttH (67611)": "67611",
}


def resolve_first_file(recid: str) -> str:
    import requests

    r = requests.get(f"https://opendata.cern.ch/api/records/{recid}", headers={"Accept": "application/json"})
    r.raise_for_status()
    md = r.json()["metadata"]
    for grp in md.get("_file_indices", []):
        for f in grp["files"]:
            return f["uri"].replace(
                "root://eospublic.cern.ch//eos/opendata/", "https://opendata.cern.ch/eos/opendata/"
            )
    raise RuntimeError(f"no file found for record {recid}")


def check_one(label, url):
    f = uproot.open(url)
    events = f["Events"]
    n_entries = events.num_entries
    w = events["genWeight"].array(library="np")
    dtype = str(w.dtype)

    sum_genweight_float64 = float(w.astype(np.float64).sum())
    n_negative = int((w < 0).sum())
    frac_negative = n_negative / len(w) if len(w) else None

    runs = f["Runs"]
    runs_sumw = runs["genEventSumw"].array(library="np")
    runs_count = runs["genEventCount"].array(library="np")
    n_runs_entries = runs.num_entries
    genEventSumw = float(runs_sumw.sum())
    genEventCount = int(runs_count.sum())

    rel_diff = abs(sum_genweight_float64 - genEventSumw) / abs(genEventSumw) if genEventSumw else None

    result = {
        "url": url,
        "n_events_in_file": n_entries,
        "genWeight_dtype": dtype,
        "sum_genWeight_full_branch": sum_genweight_float64,
        "n_runs_tree_entries": n_runs_entries,
        "genEventSumw_from_Runs_tree": genEventSumw,
        "genEventCount_from_Runs_tree": genEventCount,
        "n_events_matches_genEventCount": n_entries == genEventCount,
        "relative_difference": rel_diff,
        "agrees_to_floating_point_precision": (rel_diff is not None and rel_diff < 1e-5),
        "n_negative_weight_events": n_negative,
        "fraction_negative_weight_events": frac_negative,
    }
    print(f"\n[{label}] {json.dumps(result, indent=2)}")
    return result


def main():
    results = {}
    for label, recid in RECORD_IDS.items():
        url = resolve_first_file(recid)
        results[label] = check_one(label, url)

    with open(HERE / "genweight_vs_sumw_crosscheck.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"\nwrote {HERE / 'genweight_vs_sumw_crosscheck.json'}")


if __name__ == "__main__":
    main()
