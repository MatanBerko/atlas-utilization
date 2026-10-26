#!/usr/bin/env python
"""
Generate studies/cms_mc_weights_v3/cms_mc_normalisation_v3.json (DESIGN.md A4).

Inputs, all in-tree and read-only (see sources/README.md):
  * sources/v4_decisions_2026-10-15.json   -- Matan's reviewed cross-section
                                              decisions (15 Oct 2026). THIS is
                                              where cross_section_pb, the
                                              record list and in_full_run
                                              come from.
  * sources/v2_cms_mc_normalisation.json   -- the 12 v2 registry records
  * sources/v2_normalisation_table_v2.csv  -- all 25 tabulated samples, with
                                              the sigma_eff column and the
                                              full per-sample provenance
  * evidence/probe_mc_records.json         -- the portal dataset TITLE of each
                                              record, as read from the CERN
                                              Open Data API in the design
                                              round's Part C probe (verified
                                              by running). The title is what
                                              the D5 APV/preVFP guard tests.

Output: every record of the v4 decisions file, keyed by record ID: the 12 v2
records, 37728 (GluGluHToZZTo4L_M125, added in v3 -- DESIGN.md D10), and
35631 / 68847 (added with the v4 decisions). cross_section_pb is taken from
the decisions file; the older v2 table row is kept as `provenance`, marked
superseded, so the history stays readable. Each record carries an
`in_full_run` flag.

The arithmetic rule, stated once here and again in the output file's header:
`cross_section_pb` is sigma_eff -- the theory production cross section at the
chosen order, times the decay branching ratio where the decay is a separate
generator step, times any generator-level selection factor. `k_factor` and
`gen_filt_eff` are therefore PINNED TO 1.0 and must never be set from the
provenance block, or the correction is applied twice.

Deterministic: running it twice produces the same bytes.

Run:  python studies/cms_mc_weights_v3/build_registry.py
      python studies/cms_mc_weights_v3/build_registry.py --check
"""
from __future__ import annotations

import argparse
import csv
import json
import pathlib
import sys

STUDY_DIR = pathlib.Path(__file__).resolve().parent
V2_REGISTRY = STUDY_DIR / "sources" / "v2_cms_mc_normalisation.json"
V2_TABLE = STUDY_DIR / "sources" / "v2_normalisation_table_v2.csv"
PROBE_EVIDENCE = STUDY_DIR / "evidence" / "probe_mc_records.json"
DECISIONS = STUDY_DIR / "sources" / "v4_decisions_2026-10-15.json"
OUTPUT = STUDY_DIR / "cms_mc_normalisation_v3.json"

# DESIGN.md D10: tabulated in v2 but absent from the v2 registry; added in v3.
V3_ADDED_RECORDS = ("37728",)

HEADER_NOTE = (
    "cross_section_pb is sigma_eff: the theory production cross section at the "
    "stated order, TIMES the decay branching ratio where the decay is a "
    "separate generator step, TIMES any generator-level selection factor. "
    "k_factor and gen_filt_eff are PINNED TO 1.0 and must NEVER be set from "
    "the provenance block -- every ingredient is already inside "
    "cross_section_pb, so setting them again applies the correction twice. "
    "This is a deliberate semantic difference from PR #35, where the three "
    "fields are independent ATLAS metadata values. See "
    "studies/cms_mc_weights_v3/DESIGN.md D4."
)

PILEUP_NOTE = (
    "Pileup weights NOT applied (Matan, 15 Oct 2026), to align with ATLAS: "
    "upstream PR #35 (aesenc, head fa63544, unmerged as of 15 Oct) computes "
    "w = genWeight x sigma x 1000 x k x eps x L / Sigma-w with no pileup weight; "
    "upstream master uses RandomRunNumber only for trigger-year assignment. "
    "Pileup_nTrueInt remains stored (_mcraw_puntrue) so this can be revisited "
    "without re-processing; revisit if ATLAS adds pileup weighting. The CMS L1 "
    "prefiring weight stays applied (CMS-specific). See DESIGN.md D11."
)

DECISION_FIELDS = (
    "construction", "inputs", "sources", "order", "previous_cross_section_pb",
    "decision_note", "replaced_citation", "alternative_not_used",
    "arithmetic_note", "not_in_full_run_reason", "note",
)


def _float_or_none(text):
    text = (text or "").strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return text


def load_table_rows() -> dict:
    with open(V2_TABLE, encoding="utf-8-sig", newline="") as fh:
        return {row["recid"].strip(): row for row in csv.DictReader(fh)}


def load_portal_titles() -> dict:
    if not PROBE_EVIDENCE.exists():
        raise SystemExit(
            f"missing {PROBE_EVIDENCE} -- the portal titles come from the design "
            "round's Part C probe evidence; it must be present to build the "
            "registry (the D5 APV guard needs the title).")
    probe = json.loads(PROBE_EVIDENCE.read_text(encoding="utf-8"))
    return {rid: rec["portal_title"] for rid, rec in probe["records"].items()}


def provenance_from_table(row: dict, v2_provenance: dict | None) -> dict:
    """The table row's own fields, kept as-is, plus the v2 registry's
    provenance where it exists (the v2 record carries a `decision` narrative
    the CSV does not always repeat in the same words)."""
    prov = {
        "label": row["label"],
        "portal_total_value_pb": _float_or_none(row["portal_total_value_pb"]),
        "matching_filter_already_included": row["matching_filter_already_included"],
        "br_applied_description": row["br_applied_description"],
        "br_value": _float_or_none(row["br_value"]),
        "generator_level_sigma_pb": _float_or_none(row["generator_level_sigma_pb"]),
        "reference_sigma_pb": _float_or_none(row["reference_sigma_pb"]),
        "reference_order": row["reference_order"],
        "reference_url": row["reference_url"],
        "k_factor_from_table_DO_NOT_APPLY": _float_or_none(row["k_factor"]),
        "sigma_eff_pb_from_table": _float_or_none(row["sigma_eff_pb"]),
        "n_events_record": _float_or_none(row["n_events_record"]),
        "neg_weight_fraction_from_table": _float_or_none(row["neg_weight_fraction"]),
        "mc_equivalent_luminosity_fb": _float_or_none(row["mc_equivalent_luminosity_fb-1"]),
        "mc_equiv_lumi_over_L": _float_or_none(row["mc_equiv_lumi_over_L"]),
        "note": row["note"],
        "decision": row.get("decision", ""),
        "table_row_source": "studies/cms_mc_weights_v3/sources/v2_normalisation_table_v2.csv",
        "values_are": "UNVERIFIED by the v3 round -- carried forward from the "
                      "v2 normalisation research with its provenance, not re-derived",
    }
    if v2_provenance:
        prov["v2_registry_provenance"] = v2_provenance
    return prov


def load_decisions() -> dict:
    payload = json.loads(DECISIONS.read_text(encoding="utf-8"))
    decisions = {}
    for dec in payload["records"]:
        rid = str(dec["nano_recid"])
        if rid in decisions:
            raise SystemExit(f"record {rid} appears twice in {DECISIONS.name}")
        if not isinstance(dec["in_full_run"], bool):
            raise SystemExit(f"record {rid}: in_full_run must be true or false")
        if not dec["in_full_run"] and not dec.get("not_in_full_run_reason"):
            raise SystemExit(f"record {rid}: not in the full run but no reason given")
        decisions[rid] = dec
    excluded = payload["excluded_records"]
    overlap = set(decisions) & set(excluded)
    if overlap:
        raise SystemExit(f"records both decided and excluded: {sorted(overlap)}")
    return {"records": decisions, "excluded": excluded}


def build() -> dict:
    v2 = json.loads(V2_REGISTRY.read_text(encoding="utf-8"))
    table = load_table_rows()
    titles = load_portal_titles()
    decided = load_decisions()
    decisions = decided["records"]

    missing_v2 = (set(v2) | set(V3_ADDED_RECORDS)) - set(decisions)
    if missing_v2:
        raise SystemExit(f"records of the previous registry with no v4 decision: "
                         f"{sorted(missing_v2, key=int)}. Refusing to drop them silently.")

    record_ids = sorted(decisions, key=int)
    records = {}
    for rid in record_ids:
        if rid not in table:
            raise SystemExit(f"record {rid} is not in the v2 table; cannot build it")
        row = table[rid]
        dec = decisions[rid]
        sigma_eff = dec["cross_section_pb"]
        if not isinstance(sigma_eff, (int, float)) or sigma_eff <= 0:
            raise SystemExit(f"record {rid}: decided cross_section_pb is not a positive number ({sigma_eff!r})")
        sigma_eff = float(sigma_eff)

        # Cross-check: the decision's `previous` must be what the previous
        # registry actually held (the v2 table's sigma_eff), for every record
        # that was in it. A mismatch means the decision was made against a
        # different baseline -- a human must look, never this script.
        previous = dec["previous_cross_section_pb"]
        was_in_registry = rid in v2 or rid in V3_ADDED_RECORDS
        table_sigma = _float_or_none(row["sigma_eff_pb"])
        if was_in_registry:
            if previous is None or abs(float(previous) - table_sigma) > 1e-9 * max(1.0, table_sigma):
                raise SystemExit(
                    f"record {rid}: decision says previous={previous!r} but the "
                    f"previous registry held {table_sigma}. Refusing to guess.")
        elif previous is not None:
            raise SystemExit(f"record {rid}: was not in the previous registry, "
                             f"but the decision gives previous={previous!r}")

        v2_rec = v2.get(rid)
        if v2_rec is not None:
            # Cross-check: the v2 registry's own cross_section_pb must already
            # be the table's sigma_eff. If it is not, the two disagree and a
            # human must decide which is right -- never this script.
            v2_xsec = v2_rec.get("cross_section_pb")
            if v2_xsec is not None and abs(float(v2_xsec) - table_sigma) > 1e-9 * max(1.0, table_sigma):
                raise SystemExit(
                    f"record {rid}: v2 registry cross_section_pb={v2_xsec} disagrees "
                    f"with the table's sigma_eff_pb={table_sigma}. Refusing to guess.")
            physics_short = v2_rec.get("physics_short")
            generator = v2_rec.get("generator")
            v2_prov = v2_rec.get("provenance")
        elif rid in V3_ADDED_RECORDS:
            physics_short = row["label"]
            generator = None
            v2_prov = None
        else:
            physics_short = dec["physics_short"]
            generator = dec.get("generator")
            v2_prov = None

        # The portal title: from the design-round probe where it exists, else
        # from the decisions file (read live from the CERN API on 15 Oct 2026,
        # evidence/portal_crosscheck_20261015.json). Both present -> must agree.
        title = titles.get(rid)
        dec_title = dec.get("portal_dataset_title")
        if title and dec_title and title != dec_title:
            raise SystemExit(f"record {rid}: probe title {title!r} != decisions title {dec_title!r}")
        title = title or dec_title

        if v2_rec is not None:
            added_in = "v2"
        elif rid in V3_ADDED_RECORDS:
            added_in = "v3"
        else:
            added_in = "v4"

        provenance = provenance_from_table(row, v2_prov)
        provenance["status"] = (
            "SUPERSEDED for cross_section_pb, citation and order by "
            "`decision_2026_10_15` (sources/v4_decisions_2026-10-15.json). "
            "Kept unchanged as history.")

        decision = {"decided": "Matan, 15 Oct 2026",
                    "source_file": "studies/cms_mc_weights_v3/sources/" + DECISIONS.name}
        for key in DECISION_FIELDS:
            if key in dec:
                decision[key] = dec[key]

        records[rid] = {
            "dataset_number": int(rid),
            "record_id": int(rid),
            "mini_recid": int(dec["mini_recid"]),
            "cross_section_pb": sigma_eff,
            "k_factor": 1.0,
            "gen_filt_eff": 1.0,
            "sum_of_weights": None,
            "physics_short": physics_short,
            "generator": generator,
            "portal_dataset_title": title,
            "in_full_run": dec["in_full_run"],
            "added_in": added_in,
            "decision_2026_10_15": decision,
            "provenance": provenance,
        }

    for rid, rec in records.items():
        if rec["k_factor"] != 1.0 or rec["gen_filt_eff"] != 1.0:
            raise SystemExit(f"record {rid}: k_factor/gen_filt_eff must stay 1.0")
        if rec["sum_of_weights"] is not None:
            raise SystemExit(f"record {rid}: sum_of_weights must be null (measured at build)")
        if not rec["portal_dataset_title"]:
            raise SystemExit(
                f"record {rid}: no portal dataset title -- the D5 APV/preVFP guard "
                "cannot run without it.")

    return {
        "what": "CMS MC normalisation registry, v3. Keyed by CERN Open Data record ID.",
        "generated_by": "studies/cms_mc_weights_v3/build_registry.py",
        "design": "studies/cms_mc_weights_v3/DESIGN.md D4 / A4",
        "decisions": "studies/cms_mc_weights_v3/sources/" + DECISIONS.name +
                     " (Matan, 15 Oct 2026); readable table: "
                     "studies/cms_mc_weights_v3/XSEC_DECISIONS.md",
        "HOW_TO_READ_cross_section_pb": HEADER_NOTE,
        "pileup_weights": PILEUP_NOTE,
        "target_luminosity_fb": 16.393,
        "target_luminosity_note": "Run2016G 7.653 + Run2016H 8.740 fb^-1; the "
                                  "post-golden-JSON data luminosity, so the MC "
                                  "normalisation matches the filtered data.",
        "campaign_required": "RunIISummer20UL16NanoAODv9 postVFP; any APV/preVFP "
                             "record is a hard error (DESIGN.md D5).",
        "sum_of_weights_note": "null for every record by design: it is MEASURED at "
                               "build time as the sum of the Runs-tree genEventSumw "
                               "over exactly the files that processed successfully "
                               "and passed the per-file Sigma-w check (DESIGN.md D4).",
        "unknown_record_policy": "HARD ERROR. A record absent from this registry "
                                 "aborts the build; nothing is ever stored unweighted.",
        "full_run_records": sorted((r for r, v in records.items() if v["in_full_run"]), key=int),
        "not_in_full_run_records": {
            r: v["decision_2026_10_15"]["not_in_full_run_reason"]
            for r, v in sorted(records.items(), key=lambda kv: int(kv[0]))
            if not v["in_full_run"]},
        "deliberately_excluded_records": {
            "records": sorted(decided["excluded"], key=int),
            "why": dict(sorted(decided["excluded"].items(), key=lambda kv: int(kv[0]))),
        },
        "n_records": len(records),
        "records": records,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="verify the committed registry matches what this script "
                         "would generate; do not write anything")
    args = ap.parse_args()

    payload = json.dumps(build(), indent=2, sort_keys=False) + "\n"
    if args.check:
        if not OUTPUT.exists():
            print(f"FAIL: {OUTPUT} does not exist")
            return 1
        current = OUTPUT.read_text(encoding="utf-8")
        if current != payload:
            print(f"FAIL: {OUTPUT} differs from freshly generated content")
            return 1
        print(f"OK: {OUTPUT} matches build_registry.py output "
              f"({json.loads(current)['n_records']} records)")
        return 0

    OUTPUT.write_text(payload, encoding="utf-8")
    built = json.loads(payload)
    print(f"wrote {OUTPUT} -- {built['n_records']} records: "
          f"{', '.join(sorted(built['records'], key=int))}")
    for rid, rec in sorted(built["records"].items(), key=lambda kv: int(kv[0])):
        print(f"  {rid:>6} {rec['physics_short'] or rec['provenance']['label']:<42} "
              f"sigma_eff={rec['cross_section_pb']:<12g} added_in={rec['added_in']} "
              f"in_full_run={rec['in_full_run']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
