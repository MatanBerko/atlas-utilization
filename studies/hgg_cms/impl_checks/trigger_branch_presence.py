"""
Implementation task 3, Part B5: confirm the HLT trigger branch exists in
every file we plan to use, before any cluster run.

Method: for every file of the DoubleEG records (30521, 30554) and the
postVFP signal records listed in studies/hgg_cms/records.json (ggH, VBF,
W+H, W-H, ZH, ttH), open the file and check the "Events" tree's branch
LIST ONLY (uproot's tree.keys(), no event data ever read) for
HLT_Diphoton30_18_R9Id_OR_IsoCaloId_AND_HE_R9Id_Mass90.

Requests are made ONE AT A TIME with a pacing delay and an exponential
backoff specifically for HTTP 429 (rate limit) responses, following the
same pattern proven in implementation task 2's
studies/hgg_cms/impl_checks/lumi_coverage/check_coverage.py (needed
because the portal rate-limits concurrent/rapid requests from one client).

Run from anywhere; writes trigger_branch_presence.json into this directory.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import requests

HERE = Path(__file__).resolve().parent
TRIGGER = "HLT_Diphoton30_18_R9Id_OR_IsoCaloId_AND_HE_R9Id_Mass90"

DATA_RECORDS = {"30521": "Run2016G DoubleEG", "30554": "Run2016H DoubleEG"}
SIGNAL_RECORDS = {
    "37350": "ggH",
    "68497": "VBF",
    "71013": "WplusH",
    "70173": "WminusH",
    "74132": "ZH",
    "67611": "ttH",
}


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
    return urls


def check_branch(url: str, max_attempts: int = 8) -> tuple[bool | None, str | None]:
    """Returns (has_branch, error). has_branch is None if the file could
    not be opened at all."""
    import uproot

    last_err = None
    for attempt in range(max_attempts):
        try:
            f = uproot.open(url)
            t = f["Events"]
            return (TRIGGER in set(t.keys()), None)
        except Exception as e:
            last_err = f"{type(e).__name__}: {e}"
            is_429 = "429" in last_err or "Too Many Requests" in last_err
            time.sleep((20.0 if is_429 else 2.0) * (attempt + 1))
    return (None, last_err)


def check_record(recid: str, label: str, urls: list[str]) -> dict:
    n_ok = n_missing = n_unreadable = 0
    missing_urls = []
    unreadable = []
    for i, url in enumerate(urls, 1):
        has_branch, err = check_branch(url)
        if err is not None:
            n_unreadable += 1
            unreadable.append({"url": url, "error": err})
            print(f"[{label} {recid} {i}/{len(urls)}] ERROR {url}: {err}", flush=True)
        elif has_branch:
            n_ok += 1
            print(f"[{label} {recid} {i}/{len(urls)}] OK (has branch): {url.split('/')[-1]}", flush=True)
        else:
            n_missing += 1
            missing_urls.append(url)
            print(f"[{label} {recid} {i}/{len(urls)}] MISSING branch: {url}", flush=True)
        time.sleep(0.4)
    return {
        "label": label,
        "n_files": len(urls),
        "n_files_with_branch": n_ok,
        "n_files_missing_branch": n_missing,
        "n_files_unreadable": n_unreadable,
        "missing_branch_urls": missing_urls,
        "unreadable": unreadable,
    }


def main():
    results = {"trigger": TRIGGER, "data_records": {}, "signal_records": {}}

    for recid, label in DATA_RECORDS.items():
        urls = get_file_urls(recid)
        results["data_records"][recid] = check_record(recid, label, urls)

    for recid, label in SIGNAL_RECORDS.items():
        urls = get_file_urls(recid)
        results["signal_records"][recid] = check_record(recid, label, urls)

    with open(HERE / "trigger_branch_presence.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print(json.dumps({k: v for k, v in results.items() if k != "trigger"}, indent=2)[:2000])
    print(f"\nwrote {HERE / 'trigger_branch_presence.json'}")


if __name__ == "__main__":
    main()
