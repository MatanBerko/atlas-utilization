#!/usr/bin/env python
"""
Generate studies/cms_mc_weights_v3/cms_mc_normalisation_v4.json (MC expansion, 3 Nov 2026).

An ADDED variant of build_registry.py; build_registry.py and cms_mc_normalisation_v3.json are
not touched and stay the default of the builder.

Inputs (in-tree, read-only):
  * cms_mc_normalisation_v3.json             -- the 15 v3 records, copied UNCHANGED (same
                                                dict, so every value is byte-identical);
  * sources/v5_decisions_2026-11-03.json     -- Matan's final values for the 58 new records
                                                (54 in the full run, 4 ON HOLD).

Every new record carries: NanoAOD + MiniAOD record IDs, sigma_eff (cross_section_pb), the
construction and every factor with its source and verification status, tier, in_full_run,
an `estimate` flag, and the v3 convention k_factor = gen_filt_eff = 1.0 (pinned). The same
arithmetic rule as v3 holds (HEADER_NOTE of build_registry.py).

Deterministic. Run:  python studies/cms_mc_weights_v3/build_registry_v4.py [--check]
"""
from __future__ import annotations

import argparse
import json
import math
import pathlib
import sys

STUDY_DIR = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(STUDY_DIR))
from build_registry import HEADER_NOTE, PILEUP_NOTE  # noqa: E402

V3 = STUDY_DIR / "cms_mc_normalisation_v3.json"
DECISIONS = STUDY_DIR / "sources" / "v5_decisions_2026-11-03.json"
OUTPUT = STUDY_DIR / "cms_mc_normalisation_v4.json"
REL_TOL = 1e-4   # listed value vs product of the factors


def build() -> dict:
    v3 = json.loads(V3.read_text(encoding="utf-8"))
    dec = json.loads(DECISIONS.read_text(encoding="utf-8"))
    records = {rid: rec for rid, rec in v3["records"].items()}   # unchanged

    for d in dec["records"]:
        rid = str(d["nano_recid"])
        if rid in records:
            raise SystemExit(f"record {rid} is already in the v3 registry or appears twice")
        sigma = d["cross_section_pb"]
        if not isinstance(sigma, (int, float)) or sigma <= 0:
            raise SystemExit(f"record {rid}: cross_section_pb not a positive number: {sigma!r}")
        product = math.prod(f["value"] for f in d["factors"])
        if abs(product / sigma - 1) > REL_TOL:
            raise SystemExit(f"record {rid}: listed {sigma} vs product of factors {product} "
                             f"(rel diff {product / sigma - 1:.2e} > {REL_TOL}). Refusing to guess.")
        if not d["in_full_run"] and not d.get("not_in_full_run_reason"):
            raise SystemExit(f"record {rid}: not in the full run but no reason given")
        decision = {"decided": dec["decided"],
                    "source_file": "studies/cms_mc_weights_v3/sources/" + DECISIONS.name}
        for key in ("construction", "factors", "order", "verification", "note", "not_in_full_run_reason"):
            if key in d:
                decision[key] = d[key]
        decision["product_of_factors"] = product
        records[rid] = {
            "dataset_number": int(rid),
            "record_id": int(rid),
            "mini_recid": int(d["mini_recid"]),
            "cross_section_pb": float(sigma),
            "k_factor": 1.0,
            "gen_filt_eff": 1.0,
            "sum_of_weights": None,
            "physics_short": d["physics_short"],
            "generator": d["generator"],
            "portal_dataset_title": d["portal_dataset_title"],
            "in_full_run": d["in_full_run"],
            "added_in": "v4",
            "tier": d["tier"],
            "estimate": d["estimate"],
            "decision_2026_11_03": decision,
        }

    excluded = dict(v3["deliberately_excluded_records"]["why"])
    for rid in dec["removed_from_v3_excluded"]:
        excluded.pop(rid, None)
    for rid, why in dec["excluded_records"].items():
        if rid in records:
            raise SystemExit(f"record {rid} both in the registry and excluded")
        excluded[rid] = why
    for rid, rec in records.items():
        if rec["k_factor"] != 1.0 or rec["gen_filt_eff"] != 1.0 or rec["sum_of_weights"] is not None:
            raise SystemExit(f"record {rid}: k_factor/gen_filt_eff must stay 1.0, sum_of_weights null")
        if "RunIISummer20UL16NanoAODv9" not in (rec["portal_dataset_title"] or ""):
            raise SystemExit(f"record {rid}: title not RunIISummer20UL16NanoAODv9")

    def reason(rec):
        for key in ("decision_2026_11_03", "decision_2026_10_15"):
            if key in rec and rec[key].get("not_in_full_run_reason"):
                return rec[key]["not_in_full_run_reason"]
        return None

    ordered = dict(sorted(records.items(), key=lambda kv: int(kv[0])))
    return {
        "what": "CMS MC normalisation registry, v4 (MC expansion). Keyed by CERN Open Data record ID.",
        "generated_by": "studies/cms_mc_weights_v3/build_registry_v4.py",
        "previous_version": "studies/cms_mc_weights_v3/cms_mc_normalisation_v3.json (its 15 records are carried over unchanged)",
        "decisions": "studies/cms_mc_weights_v3/sources/v5_decisions_2026-11-03.json (Matan, 3 Nov 2026) for the "
                     "added records; studies/cms_mc_weights_v3/sources/v4_decisions_2026-10-15.json for the v3 ones",
        "HOW_TO_READ_cross_section_pb": HEADER_NOTE,
        "pileup_weights": PILEUP_NOTE,
        "target_luminosity_fb": v3["target_luminosity_fb"],
        "target_luminosity_note": v3["target_luminosity_note"],
        "campaign_required": v3["campaign_required"],
        "sum_of_weights_note": v3["sum_of_weights_note"],
        "unknown_record_policy": v3["unknown_record_policy"],
        "estimates": {r: v["decision_2026_11_03"]["verification"] for r, v in ordered.items()
                      if v.get("estimate")},
        "full_run_records": [r for r, v in ordered.items() if v["in_full_run"]],
        "not_in_full_run_records": {r: reason(v) for r, v in ordered.items() if not v["in_full_run"]},
        "deliberately_excluded_records": {
            "records": sorted(excluded, key=int),
            "why": dict(sorted(excluded.items(), key=lambda kv: int(kv[0]))),
        },
        "n_records": len(ordered),
        "records": ordered,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    payload = json.dumps(build(), indent=2, ensure_ascii=False) + "\n"
    if args.check:
        ok = OUTPUT.exists() and OUTPUT.read_text(encoding="utf-8") == payload
        print(("OK: " if ok else "FAIL: ") + f"{OUTPUT.name} {'matches' if ok else 'differs from'} build_registry_v4.py output")
        return 0 if ok else 1
    OUTPUT.write_text(payload, encoding="utf-8")
    b = json.loads(payload)
    print(f"wrote {OUTPUT}: {b['n_records']} records, {len(b['full_run_records'])} in the full run, "
          f"{len(b['not_in_full_run_records'])} not, {len(b['deliberately_excluded_records']['records'])} excluded")
    return 0


if __name__ == "__main__":
    sys.exit(main())
