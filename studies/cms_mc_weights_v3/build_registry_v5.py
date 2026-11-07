#!/usr/bin/env python
"""
Generate studies/cms_mc_weights_v3/cms_mc_normalisation_v5.json (D15 + E3, 7 Nov 2026).

An ADDED variant; build_registry.py, build_registry_v4.py, cms_mc_normalisation_v3.json and
cms_mc_normalisation_v4.json are not touched, and the builder's default registry is unchanged.

v5 = v4 + exactly the D15 changes (sources/v6_decisions_2026-11-07.json):
  * the 4 ON-HOLD tier-4 records 68325, 64873, 68206, 68185 get in_full_run = true and a
    decision_2026_11_07 block (Matan's hand-verified portal value, order, source). Their
    cross_section_pb must EQUAL the v4 value (Matan verified the same numbers) -- otherwise STOP;
  * the E3 note on every ttZ record (68185, 68187, 68206);
  * the header lists (full_run_records, not_in_full_run_records), what/generated_by/
    previous_version/decisions.
Every other record is the v4 dict, unchanged (so its values are byte-identical).

Deterministic. Run:  python studies/cms_mc_weights_v3/build_registry_v5.py [--check]
"""
from __future__ import annotations

import argparse
import copy
import json
import math
import pathlib
import sys

STUDY_DIR = pathlib.Path(__file__).resolve().parent
V4 = STUDY_DIR / "cms_mc_normalisation_v4.json"
DECISIONS = STUDY_DIR / "sources" / "v6_decisions_2026-11-07.json"
OUTPUT = STUDY_DIR / "cms_mc_normalisation_v5.json"
REL_TOL = 1e-4


def build() -> dict:
    v4 = json.loads(V4.read_text(encoding="utf-8"))
    dec = json.loads(DECISIONS.read_text(encoding="utf-8"))
    out = copy.deepcopy(v4)
    recs = out["records"]
    src = "studies/cms_mc_weights_v3/sources/" + DECISIONS.name

    for d in dec["D15"]["records"]:
        rid = str(d["nano_recid"])
        rec = recs.get(rid)
        if rec is None or rec["in_full_run"] is not False:
            raise SystemExit(f"STOP: record {rid} is not an ON-HOLD v4 record")
        if rec["mini_recid"] != d["mini_recid"]:
            raise SystemExit(f"STOP: record {rid}: MiniAOD {rec['mini_recid']} != decision {d['mini_recid']}")
        if rec["cross_section_pb"] != d["cross_section_pb"]:
            raise SystemExit(f"STOP: record {rid}: v4 value {rec['cross_section_pb']} != D15 {d['cross_section_pb']}")
        factors = [{"name": "generator cross section (portal)", "value": d["cross_section_pb"],
                    "source": {"citation": f"CERN Open Data MiniAOD record {d['mini_recid']} (generator cross section)",
                               "location": "metadata.cross_section.total_value",
                               "url": f"https://opendata.cern.ch/record/{d['mini_recid']}"},
                    "verification": dec["D15"]["verification"]}]
        product = math.prod(f["value"] for f in factors)
        if abs(product / d["cross_section_pb"] - 1) > REL_TOL:
            raise SystemExit(f"STOP: record {rid}: product of factors {product} != {d['cross_section_pb']}")
        block = {"decided": dec["decided"] + " (D15)", "source_file": src,
                 "construction": f"{d['cross_section_pb']} ({d['order']}, portal total_value; k_factor = gen_filt_eff = 1.0)",
                 "factors": factors, "order": d["order"], "verification": dec["D15"]["verification"],
                 "supersedes": "the ON HOLD status of decision_2026_11_03 (released by D15)",
                 "product_of_factors": product}
        if d["note"]:
            block["note"] = d["note"]
        rec["in_full_run"] = True
        rec["decision_2026_11_07"] = block

    for rid in dec["E3"]["applies_to_cms_records"]:
        recs[rid]["exception_E3_2026_11_07"] = dec["E3"]["text"]

    for rid, rec in recs.items():
        if rec["k_factor"] != 1.0 or rec["gen_filt_eff"] != 1.0 or rec["sum_of_weights"] is not None:
            raise SystemExit(f"record {rid}: k_factor/gen_filt_eff must stay 1.0, sum_of_weights null")

    out["what"] = "CMS MC normalisation registry, v5 (MC expansion + D15 rare-top release). Keyed by CERN Open Data record ID."
    out["generated_by"] = "studies/cms_mc_weights_v3/build_registry_v5.py"
    out["previous_version"] = ("studies/cms_mc_weights_v3/cms_mc_normalisation_v4.json (all records carried over; "
                               "only the 4 D15 records change status, plus the E3 note on the ttZ records)")
    out["decisions"] = v4["decisions"] + f"; {src} (Matan, 7 Nov 2026: D15, E3)"
    out["full_run_records"] = [r for r, v in recs.items() if v["in_full_run"]]
    out["not_in_full_run_records"] = {r: v4["not_in_full_run_records"][r] for r, v in recs.items() if not v["in_full_run"]}
    out["n_records"] = len(recs)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    payload = json.dumps(build(), indent=2, ensure_ascii=False) + "\n"
    if args.check:
        ok = OUTPUT.exists() and OUTPUT.read_text(encoding="utf-8") == payload
        print(("OK: " if ok else "FAIL: ") + f"{OUTPUT.name} {'matches' if ok else 'differs from'} build_registry_v5.py output")
        return 0 if ok else 1
    OUTPUT.write_text(payload, encoding="utf-8")
    b = json.loads(payload)
    print(f"wrote {OUTPUT}: {b['n_records']} records, {len(b['full_run_records'])} in the full run, "
          f"{len(b['not_in_full_run_records'])} not, {len(b['deliberately_excluded_records']['records'])} excluded")
    return 0


if __name__ == "__main__":
    sys.exit(main())
