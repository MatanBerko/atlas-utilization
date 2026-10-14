#!/usr/bin/env python
"""
Design item D3: does a CMS MC NanoAOD file carry ANY per-event dataset
identifier, i.e. anything that could play the role ATLAS's
`EventInfoAuxDyn.mcChannelNumber` plays in PR #35?

PR #35 reads the dataset number from the events themselves and refuses to
infer it from file names (mass_calculation_handler.py's own docstring). This
design cannot do that for CMS, because `_mcChannelNumber` is set from the
driver's `--record-id` argument instead. That is a deliberate deviation, so
it needs evidence rather than an assumption.

This probe lists, for one MC file and one DATA file, every Events-tree branch
whose name could plausibly identify the sample or the process, plus the
complete set of event-level (non-collection) scalar branch names, so a
reviewer can see for themselves that no dataset-id branch is being ignored.

Read-only. Writes one JSON into --output-dir and nothing else.

Run:
    python studies/cms_mc_weights_v3/probe/probe_dataset_identity_branches.py \
        --output-dir /storage/.../work/cms_mc_v3_design_<date>/identity_out
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
from datetime import datetime, timezone

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3]))

import uproot  # noqa: E402

from studies.m0m1j0_cms.design_checks.common import fetch_file_list  # noqa: E402

# One MC record (the ggH->ZZ->4l signal pilot) and one DATA record
# (DoubleMuon Run2016G, the highest-priority delivered dataset), both taken
# from the study's own record tables rather than typed as URLs.
MC_RECORD = 37728
DATA_RECORD = 30522

# Names that would identify a sample, a process, a dataset or a channel.
IDENTITY_PATTERNS = [
    "dsid", "channel", "sample", "dataset", "process", "procid", "proc_id",
    "mcid", "mc_id", "xsec", "crossSection", "lheweight", "genId",
]


def scan_file(file_url: str) -> dict:
    with uproot.open(file_url) as f:
        tree = f["Events"]
        keys = sorted(tree.keys())
        # Event-level scalars: branches that are not part of a jagged
        # collection, i.e. whose interpretation has no counter branch.
        scalars = []
        for k in keys:
            try:
                interp = tree[k].interpretation
            except Exception:  # noqa: BLE001
                continue
            if "AsJagged" not in type(interp).__name__ and not k.startswith("n"):
                scalars.append(k)
        hits = sorted({
            k for k in keys
            for pat in IDENTITY_PATTERNS
            if re.search(pat, k, flags=re.IGNORECASE)
        })
        top_level = sorted({k.split(";")[0] for k in f.keys()})
        return {
            "file_url": file_url,
            "n_branches": len(keys),
            "top_level_objects": top_level,
            "identity_pattern_matches": hits,
            "n_event_level_scalars": len(scalars),
            "event_level_scalars": scalars,
            "run_branch_present": "run" in keys,
            "genWeight_branch_present": "genWeight" in keys,
        }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output-dir", required=True)
    args = ap.parse_args()

    out_dir = pathlib.Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    result = {
        "what": (
            "Per-event dataset-identifier search in one CMS MC NanoAOD file and "
            "one CMS DATA NanoAOD file (design item D3)."
        ),
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "identity_patterns_searched": IDENTITY_PATTERNS,
        "mc_record": MC_RECORD,
        "data_record": DATA_RECORD,
    }
    result["mc"] = scan_file(fetch_file_list(MC_RECORD)[0])
    result["data"] = scan_file(fetch_file_list(DATA_RECORD)[0])

    mc_hits = result["mc"]["identity_pattern_matches"]
    result["verdict"] = {
        "mc_has_any_identity_pattern_branch": bool(mc_hits),
        "mc_identity_pattern_branches": mc_hits,
        "branches_only_in_mc": sorted(
            set(result["mc"]["event_level_scalars"])
            - set(result["data"]["event_level_scalars"])
        ),
        "branches_only_in_data": sorted(
            set(result["data"]["event_level_scalars"])
            - set(result["mc"]["event_level_scalars"])
        ),
    }

    path = out_dir / "dataset_identity_branches.json"
    path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result["verdict"], indent=2))
    print(f"\nwrote {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
