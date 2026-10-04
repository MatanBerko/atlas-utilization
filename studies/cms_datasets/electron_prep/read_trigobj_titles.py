#!/usr/bin/env python
"""
Step 1 evidence: read the TrigObj branch TITLES out of the real NanoAOD
files of the three electron datasets (and SingleMuon, for the tag side of
Step 2), plus check which HLT path branches actually exist in each.

Hard rule: every trigger-object bit meaning used anywhere in this study is
taken from the `TrigObj_filterBits` branch title inside the actual files,
quoted verbatim -- never from memory. This script is what produces that
quote. It also records whether the title is byte-identical across datasets
and eras, which is the thing that would otherwise be assumed.

Reads only file headers / branch metadata (no event payload), so it is
cheap enough to run on the login node.

Usage:
    python read_trigobj_titles.py --out evidence/trigobj_titles_electron_datasets.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import uproot  # noqa: E402

from studies.cms_datasets.electron_prep.common import (  # noqa: E402
    TRIGOBJ_BRANCHES, dataset_by_label, record_for,
)
from studies.cms_datasets.cluster import run_dataset_on_file as drv  # noqa: E402

# Datasets whose own files must be quoted, with the era of the file read.
TARGETS = [
    ("DoubleEG", "G"), ("DoubleEG", "H"),
    ("MuonEG", "G"), ("MuonEG", "H"),
    ("SingleElectron", "G"), ("SingleElectron", "H"),
    ("SingleMuon", "G"), ("SingleMuon", "H"),
]

# Every HLT path this study needs to exist, per dataset.
PATHS_NEEDED = {
    "DoubleEG": ["HLT_Ele23_Ele12_CaloIdL_TrackIdL_IsoVL_DZ"],
    "MuonEG": ["HLT_Mu23_TrkIsoVVL_Ele12_CaloIdL_TrackIdL_IsoVL_DZ",
               "HLT_Mu8_TrkIsoVVL_Ele23_CaloIdL_TrackIdL_IsoVL_DZ",
               "HLT_Mu23_TrkIsoVVL_Ele12_CaloIdL_TrackIdL_IsoVL",
               "HLT_Mu8_TrkIsoVVL_Ele23_CaloIdL_TrackIdL_IsoVL"],
    "SingleElectron": ["HLT_Ele27_WPTight_Gsf", "HLT_Ele32_eta2p1_WPTight_Gsf"],
    "SingleMuon": ["HLT_IsoMu24", "HLT_IsoTkMu24"],
}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--out", required=True)
    p.add_argument("--file-index", type=int, default=0)
    args = p.parse_args()

    out = {"what": "TrigObj branch titles and HLT branch presence, read from the "
                   "real UL2016 NanoAODv9 files of each dataset",
           "match_dr_max_used_everywhere": drv.MATCH_DR_MAX,
           "datasets": {}}

    for label, era in TARGETS:
        rec = record_for(label, era)
        url = drv.resolve_file_url(rec, args.file_index)
        tree = uproot.open(url)["Events"]
        keys = set(tree.keys())
        titles = {}
        for b in TRIGOBJ_BRANCHES:
            titles[b] = tree[b].title if b in keys else None
        paths = {pth: (pth in keys) for pth in PATHS_NEEDED[label]}
        key = f"{label}_{era}"
        out["datasets"][key] = {
            "label": label, "era": era, "record_id": rec,
            "file_index": args.file_index, "file_url": url,
            "n_entries": int(tree.num_entries),
            "trigobj_branch_titles": titles,
            "hlt_paths_present": paths,
            "filterBits_title_sha256": hashlib.sha256(
                (titles.get("TrigObj_filterBits") or "").encode()).hexdigest(),
        }
        print(f"[{key}] record {rec}: {tree.num_entries} entries; "
              f"HLT present: {paths}")

    # Is the filterBits title the same string everywhere? (Would otherwise
    # be assumed. If it is not, every per-dataset bit meaning must be taken
    # from that dataset's own title.)
    hashes = {k: v["filterBits_title_sha256"] for k, v in out["datasets"].items()}
    unique = sorted(set(hashes.values()))
    out["filterBits_title_identical_across_all_datasets_and_eras"] = len(unique) == 1
    out["filterBits_title_sha256_by_dataset"] = hashes
    out["n_distinct_filterBits_titles"] = len(unique)

    # Pull out just the Electron and Muon portions of the one title, for quoting.
    any_title = next(v["trigobj_branch_titles"]["TrigObj_filterBits"]
                     for v in out["datasets"].values())
    out["filterBits_title_full"] = any_title
    ele_part = any_title.split("for Electron")[0] if "for Electron" in any_title else None
    mu_part = None
    if "for Electron (PixelMatched e/gamma);" in any_title:
        mu_part = any_title.split("for Electron (PixelMatched e/gamma);")[1].split("for Muon")[0]
    out["filterBits_title_electron_portion"] = (ele_part or "").strip()
    out["filterBits_title_muon_portion"] = (mu_part or "").strip()
    out["trigobj_id_title"] = next(v["trigobj_branch_titles"]["TrigObj_id"]
                                   for v in out["datasets"].values())

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"\nfilterBits title identical across all 8 (dataset, era) files: "
          f"{out['filterBits_title_identical_across_all_datasets_and_eras']} "
          f"({out['n_distinct_filterBits_titles']} distinct title(s))")
    print("\nELECTRON portion of the filterBits title:")
    print(" ", out["filterBits_title_electron_portion"])
    print("\nMUON portion of the filterBits title:")
    print(" ", out["filterBits_title_muon_portion"])
    print(f"\nwrote {args.out}")


if __name__ == "__main__":
    main()
