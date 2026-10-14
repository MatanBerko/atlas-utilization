#!/usr/bin/env python
"""
Generate studies/cms_mc_weights_v3/cms_mc_normalisation_v3.json (DESIGN.md A4).

Inputs, all in-tree and read-only (see sources/README.md):
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

Output: the 12 v2 records PLUS record 37728 (GluGluHToZZTo4L_M125, tabulated
but missing from the v2 registry -- DESIGN.md D10), keyed by record ID.

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
OUTPUT = STUDY_DIR / "cms_mc_normalisation_v3.json"

# DESIGN.md D10: tabulated in v2 but absent from the v2 registry; added here.
EXTRA_RECORDS = ("37728",)

# Explicitly NOT added, per this round's out-of-scope list: the gg->ZZ family
# (38428-38442, the ~1000x pb-vs-fb units problem), 75567 ZZTo2L2Nu (the
# unresolved 42% discrepancy), 68847 VBF_HToZZTo4L_M125, and the low-mass DY
# records 35631/35633.
DELIBERATELY_EXCLUDED = {
    "38428", "38430", "38432", "38434", "38436", "38438", "38440", "38442",
    "75567", "68847", "35631", "35633",
}

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


def build() -> dict:
    v2 = json.loads(V2_REGISTRY.read_text(encoding="utf-8"))
    table = load_table_rows()
    titles = load_portal_titles()

    record_ids = sorted(set(v2) | set(EXTRA_RECORDS), key=int)
    records = {}
    for rid in record_ids:
        if rid not in table:
            raise SystemExit(f"record {rid} is not in the v2 table; cannot build it")
        row = table[rid]
        sigma_eff = _float_or_none(row["sigma_eff_pb"])
        if not isinstance(sigma_eff, float) or sigma_eff <= 0:
            raise SystemExit(f"record {rid}: sigma_eff_pb is not a positive number ({sigma_eff!r})")

        v2_rec = v2.get(rid)
        if v2_rec is not None:
            # Cross-check: the v2 registry's own cross_section_pb must already
            # be the table's sigma_eff. If it is not, the two disagree and a
            # human must decide which is right -- never this script.
            v2_xsec = v2_rec.get("cross_section_pb")
            if v2_xsec is not None and abs(float(v2_xsec) - sigma_eff) > 1e-9 * max(1.0, sigma_eff):
                raise SystemExit(
                    f"record {rid}: v2 registry cross_section_pb={v2_xsec} disagrees "
                    f"with the table's sigma_eff_pb={sigma_eff}. Refusing to guess.")
            physics_short = v2_rec.get("physics_short")
            generator = v2_rec.get("generator")
            v2_prov = v2_rec.get("provenance")
        else:
            physics_short = row["label"]
            generator = None
            v2_prov = None

        records[rid] = {
            "dataset_number": int(rid),
            "record_id": int(rid),
            "cross_section_pb": sigma_eff,
            "k_factor": 1.0,
            "gen_filt_eff": 1.0,
            "sum_of_weights": None,
            "physics_short": physics_short,
            "generator": generator,
            "portal_dataset_title": titles.get(rid),
            "added_in": "v3" if v2_rec is None else "v2",
            "provenance": provenance_from_table(row, v2_prov),
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
        "HOW_TO_READ_cross_section_pb": HEADER_NOTE,
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
        "deliberately_excluded_records": {
            "records": sorted(DELIBERATELY_EXCLUDED, key=int),
            "why": "Out of scope for this round: the gg->ZZ family 38428-38442 "
                   "(portal values ~1000x too large, pb-vs-fb), 75567 ZZTo2L2Nu "
                   "(unresolved 42% discrepancy), 68847 VBF_HToZZTo4L_M125, and "
                   "the low-mass DY records 35631/35633.",
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
              f"sigma_eff={rec['cross_section_pb']:<12g} added_in={rec['added_in']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
