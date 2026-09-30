#!/usr/bin/env python
"""
Phase-1 MC weights task, amendment A3: build the CMS normalisation JSON
(DESIGN.md Sec 2 schema) from normalisation_table_v2.csv, for exactly the
3 phase-1 samples. Does NOT import any PR#23 code (A3) -- this is a small,
independent CMS-side script.

`gen_filt_eff` is fixed at 1.0 for every record, always (DESIGN.md Sec 2:
R1 established the portal's cross section already includes matching/
filter efficiency; multiplying by anything else here would double-count).
`k_factor` is fixed at 1.0 too -- it is already folded into
`cross_section_pb` (= sigma_eff from the table), per DESIGN.md's own
"folded into cross_section_pb, not re-applied at weight-computation time"
design choice; the table's own k_factor column is carried into
`provenance` for audit only.

Usage:
    python build_normalisation_json.py \
        --table studies/cms_mc_weights/normalisation_table_v2.csv \
        --out studies/cms_mc_weights/cms_mc_normalisation.json
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

# Phase-1 samples (task's own exact list and order).
PHASE1_RECORD_IDS = ["42407", "67801", "35671"]

PORTAL_RECORD_URLS = {
    # NanoAODSIM record -> MiniAODSIM sibling (portal cross_section source),
    # per INVESTIGATION.md Sec C / evidence/task_c_xsec_table.json.
    "42407": None,  # leptoquark: no portal cross_section block at all (Sec C coverage)
    "67801": "https://opendata.cern.ch/record/67800",
    "35671": "https://opendata.cern.ch/record/35670",
}

GENERATOR_BY_RECORD = {
    "42407": "madgraph (LO, pair production)",
    "67801": "powheg",
    "35671": "madgraphMLM",
}

PHYSICS_SHORT_BY_RECORD = {
    "42407": "LQToBMu_M-400_pair",
    "67801": "TTTo2L2Nu",
    "35671": "DYJetsToLL_M-50_madgraphMLM",
}


def build(table_path: Path) -> dict:
    with open(table_path, newline="", encoding="utf-8") as f:
        rows = {r["recid"]: r for r in csv.DictReader(f) if r.get("recid")}

    out = {}
    for recid in PHASE1_RECORD_IDS:
        if recid not in rows:
            raise KeyError(
                f"record {recid} not found in {table_path} -- refusing to "
                f"build a normalisation entry from missing data."
            )
        row = rows[recid]

        def _num(key):
            v = row.get(key, "")
            return float(v) if v not in ("", None) else None

        sigma_eff = _num("sigma_eff_pb")
        if sigma_eff is None:
            raise ValueError(f"record {recid}: sigma_eff_pb is empty in {table_path} -- cannot build a weight.")

        n_events = row.get("n_events_record", "")
        entry = {
            "dataset_number": int(recid),
            "cross_section_pb": sigma_eff,
            "sum_of_weights": None,  # computed at merge time, per-run (DESIGN.md Sec 2 / A5) -- never a static constant
            "k_factor": 1.0,          # already folded into cross_section_pb -- see module docstring
            "gen_filt_eff": 1.0,      # ALWAYS 1.0 for CMS -- R1, portal sigma already final (DESIGN.md Sec 2)
            "n_events": int(float(n_events)) if n_events not in ("", None) else None,
            "physics_short": PHYSICS_SHORT_BY_RECORD.get(recid),
            "generator": GENERATOR_BY_RECORD.get(recid),
            "provenance": {
                "label": row.get("label"),
                "portal_total_value_pb": _num("portal_total_value_pb"),
                "portal_record_url": PORTAL_RECORD_URLS.get(recid),
                "matching_filter_already_included": row.get("matching_filter_already_included"),
                "br_applied_description": row.get("br_applied_description"),
                "br_value": row.get("br_value") or None,
                "generator_level_sigma_pb": _num("generator_level_sigma_pb"),
                "reference_sigma_pb": row.get("reference_sigma_pb") or None,
                "reference_order": row.get("reference_order"),
                "reference_url": row.get("reference_url"),
                "k_factor_from_table": row.get("k_factor"),
                "decision": row.get("decision"),
                "table_row_source": str(table_path),
            },
        }
        out[recid] = entry
    return out


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--table", default="studies/cms_mc_weights/normalisation_table_v2.csv")
    p.add_argument("--out", default="studies/cms_mc_weights/cms_mc_normalisation.json")
    args = p.parse_args()

    result = build(Path(args.table))
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"wrote {args.out} with {len(result)} record(s): {list(result.keys())}")
    for recid, entry in result.items():
        print(f"  {recid}: cross_section_pb={entry['cross_section_pb']}, "
              f"gen_filt_eff={entry['gen_filt_eff']}, k_factor={entry['k_factor']}")


if __name__ == "__main__":
    main()
