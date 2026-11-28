#!/usr/bin/env python
"""
Generate studies/cms_mc_weights_v3/cms_mc_normalisation_v6.json (Nominal-6 additions, 28 Nov 2026).

An ADDED variant; build_registry*.py v3-v5 and cms_mc_normalisation_v3/v4/v5.json are not touched, and the builder's
default registry is unchanged.

v6 = v5 + exactly the changes of sources/v9_decisions_2026-11-28.json:
  * NEW records (in_full_run = true): 75561, 72648, 71636 (D-N1), 71640 (D-N2) = portal total_value (R1); 74314 (D-N4)
    = sigma(qq->ZH) x BR(H->ZZ) x (2B - B^2) x 0.1509; plus the WZjj replacement if the D-WZ check found one
    (studies/nominal6_additions_20261127/evidence/wzjj/wzjj_outcome.json), portal total_value as a PROPOSAL;
  * CHANGED value: 40062 (D-40062) = sigma(gg->ZH) x BR(H->ZZ) x (2B - B^2) x McM filter efficiency 0.1505; its
    decision_2026_11_03 history is kept;
  * every new/changed value carries matan_hand_check = "PENDING" (the MC build must not run until a separate commit
    sets VERIFIED BY MATAN);
  * deliberately excluded: 69771 (D-WZ) and the 8 Dalitz records (D-N3); 74314 leaves the excluded list;
  * the YR4 / PDG factors are copied from the v5 entries named in each factor's "taken_from_v5" (exact v5 numbers).
Every other record is the v5 dict, unchanged (so its values are byte-identical).

Deterministic. Run:  python studies/cms_mc_weights_v3/build_registry_v6.py [--check]
"""
from __future__ import annotations

import argparse
import copy
import gzip
import json
import math
import pathlib
import sys

STUDY_DIR = pathlib.Path(__file__).resolve().parent
REPO = STUDY_DIR.parents[1]
V5 = STUDY_DIR / "cms_mc_normalisation_v5.json"
DECISIONS = STUDY_DIR / "sources" / "v9_decisions_2026-11-28.json"
OUTPUT = STUDY_DIR / "cms_mc_normalisation_v6.json"
N6 = REPO / "studies" / "nominal6_additions_20261127"
WZ_OUTCOME = N6 / "evidence" / "wzjj" / "wzjj_outcome.json"
RECORDS = N6 / "evidence" / "records"
REL_TOL = 1e-4
PENDING = "PENDING"
DECIDED = "Matan, 28 Nov 2026 (v9_decisions_2026-11-28.json)"
DALITZ = ["37276", "37420", "68459", "68559", "69681", "69699", "74652", "74670"]


def portal(mini: int) -> dict:
    with gzip.open(RECORDS / f"{mini}.json.gz", "rt") as f:
        return json.load(f)["metadata"]


def v5_factor(v5recs: dict, rid: str, name: str) -> dict:
    """A factor copied from a v5 entry: exact value and source, with where it was taken from."""
    for f in v5recs[rid]["decision_2026_11_03"]["factors"]:
        if f["name"] == name:
            g = copy.deepcopy(f)
            g["taken_from_v5"] = f"cms_mc_normalisation_v5.json records['{rid}'].decision_2026_11_03.factors['{name}']"
            g["verification_in_v5"] = g.pop("verification")
            return g
    raise SystemExit(f"STOP: factor {name!r} not found in v5 record {rid}")


def portal_record(rid: int, mini: int, decision_key: str, note: str, proposal: bool = False) -> tuple[float, dict]:
    nano, mm = portal(rid), portal(mini)
    xs = float(mm["cross_section"]["total_value"])
    f = {"name": "generator cross section (portal)", "value": xs,
         "source": {"citation": f"CERN Open Data MiniAOD record {mini} (generator cross section)",
                    "location": "metadata.cross_section.total_value",
                    "url": f"https://opendata.cern.ch/record/{mini}",
                    "portal_block_as_read": mm["cross_section"]},
         "verification": "VERIFIED (saved record, read 27-28 Nov 2026); Matan's hand check PENDING"}
    block = {"decided": DECIDED + f" ({decision_key})", "source_file": "studies/cms_mc_weights_v3/sources/" + DECISIONS.name,
             "construction": f"{xs} (generator LO, portal total_value, rule R1; k_factor = gen_filt_eff = 1.0)",
             "factors": [f], "order": "LO (generator, MadGraph5_aMC@NLO 2.6.5 LO)", "note": note,
             "matan_hand_check": PENDING, "product_of_factors": xs}
    if proposal:
        block["status"] = "PROPOSAL pending Matan's hand check (D-WZ)"
    return xs, {"title": nano["title"]}, block


def new_entry(rid: int, mini: int, xs: float, title: str, generator: str, block: dict, estimate=False) -> dict:
    ds = title.split("/")[1]
    return {"dataset_number": rid, "record_id": rid, "mini_recid": mini, "cross_section_pb": xs, "k_factor": 1.0,
            "gen_filt_eff": 1.0, "sum_of_weights": None, "physics_short": ds.replace("_TuneCP5_13TeV", ""),
            "generator": generator, "portal_dataset_title": title, "in_full_run": True, "added_in": "v6", "tier": 7,
            "estimate": estimate, "matan_hand_check": PENDING, "decision_2026_11_28": block}


def build() -> dict:
    v5 = json.loads(V5.read_text(encoding="utf-8"))
    dec = json.loads(DECISIONS.read_text(encoding="utf-8"))
    wz = json.loads(WZ_OUTCOME.read_text(encoding="utf-8"))
    out = copy.deepcopy(v5)
    recs = out["records"]
    for rid in ("75561", "72648", "71636", "71640", "74314", "69771"):
        if rid in recs:
            raise SystemExit(f"STOP: record {rid} is already in v5")

    # ---- D-N1 / D-N2: portal values; the decision quotes them, they must match the saved records ----
    quoted = {75561: (75560, 0.0009928, "D-N1"), 72648: (72647, 0.09219, "D-N1"), 71636: (71635, 0.02694, "D-N1"),
              71640: (71639, 0.02037, "D-N2")}
    notes = {
        75561: ("EW ZZjj -> 4l (l = e, mu, tau), no top (`$ t t~`). Generator cuts m_jj > 100 GeV, on-shell Z decay chains, "
                "|eta_l| < 3 (ATLAS 700587: no m_jj cut, off-shell incl. low-mass gamma*): CMS/ATLAS = 0.072. No "
                "interference sample. Triboson-like region partly overlapping our tribosons (as on the ATLAS side)."),
        72648: ("EW W+W-jj -> l nu l nu, no top. m_jj > 100 GeV, on-shell W (ATLAS 700589: all OS llnunu, no m_jj cut): "
                "CMS/ATLAS = 0.46. s-channel H->WW in 1.3 % of the events (overlap with our VBF H->WW) accepted (D-N1)."),
        71636: ("EW W+-W+-jj (contains W+W+ AND W-W-), no top. m_jj > 100 GeV, on-shell W (ATLAS 700590: no m_jj cut): "
                "CMS/ATLAS = 0.55. No interference sample."),
        71640: "QCD W+-W+-jj, no top. 8 % below ATLAS 700603 (0.02221 pb) (D-N2).",
    }
    new = {}
    for rid, (mini, q, key) in quoted.items():
        xs, info, block = portal_record(rid, mini, key, notes[rid])
        if abs(xs / q - 1) > REL_TOL:
            raise SystemExit(f"STOP: record {rid}: saved portal value {xs} != decision {q}")
        new[str(rid)] = new_entry(rid, mini, xs, info["title"], "madgraph", block)

    # ---- D-WZ replacement (only if found) ----
    if wz.get("replacement_nano_recid"):
        rid, mini = int(wz["replacement_nano_recid"]), int(wz["replacement_mini_recid"])
        xs, info, block = portal_record(rid, mini, "D-WZ", wz["replacement_note"], proposal=True)
        new[str(rid)] = new_entry(rid, mini, xs, info["title"], "madgraph", block)

    # ---- D-N4 74314 and D-40062: sigma x BR(H->ZZ) x (2B - B^2) x eps_filter ----
    B = v5_factor(v5["records"], "40062", "BR(Z -> ll), l = e, mu, tau")
    BRZZ = v5_factor(v5["records"], "40062", "BR(H -> ZZ)")
    SQQ = v5_factor(v5["records"], "74292", "sigma(ZH, all but gg->ZH)")
    SGG = v5_factor(v5["records"], "40062", "sigma(gg->ZH)")
    b = B["value"]
    atl = {"name": "2B - B^2 = P(at least one of the two H->Z bosons -> ll), B = BR(Z -> ll)", "value": 2 * b - b * b,
           "source": {"citation": "arithmetic on the v5 factor BR(Z -> ll), l = e, mu, tau",
                      "location": f"2 x {b} - {b}^2", "url": None},
           "verification": "arithmetic (VERIFIED BY RUNNING)",
           "interpretation": ("JHUGen DecayMode1=8 (Z -> 2l incl. tau), DecayMode2=9 (Z -> anything) generates H -> ZZ with "
                              "at least one Z -> ll; INTERPRETATION supported by the file-0 decay mix "
                              "(studies/nominal6_additions_20261127/REPORT.md section 3.1, 27 Nov 2026)")}

    def filt(value, rid_mcm, prepid, field, exact):
        return {"name": "eps(4-lepton filter, JHUGen FilterNLept=4)", "value": value,
                "source": {"citation": f"McM request {prepid}", "location": f"generator_parameters[-1].{field} = {exact}",
                           "url": f"https://cms-pdmv-prod.web.cern.ch/mcm/public/restapi/requests/get/{prepid}"},
                "verification": "VERIFIED (saved McM request JSON); Matan's hand check PENDING",
                "interpretation": ("the McM efficiency is the 4-lepton filter efficiency relative to H -> ZZ with >= 1 "
                                   "Z -> ll (INTERPRETATION supported by the file-0 decay mix of 74314, 27 Nov 2026)")}

    f74 = [SQQ, BRZZ, atl, filt(0.1509, "74314", "HIG-RunIISummer20UL16wmLHEGEN-00239", "match_efficiency",
                                "0.150882730885 (the decision uses 0.1509)")]
    x74 = math.prod(f["value"] for f in f74)
    b74 = {"decided": DECIDED + " (D-N4, option C of the 27 Nov report)",
           "source_file": "studies/cms_mc_weights_v3/sources/" + DECISIONS.name,
           "construction": f"{SQQ['value']} x {BRZZ['value']} x (2 x {b} - {b}^2) x 0.1509",
           "factors": f74, "order": "YR4 production (NNLO QCD + NLO EW) x YR4 BR x generator filter efficiency",
           "note": ("Broader than ATLAS 346645 (H->4l only, 0.7612 x 2.745e-4 = 2.089e-4 pb): also Z(->ll) H(->ZZ->ll X), "
                    "63 % of the file-0 events. No overlap with our other ZH samples (none has H->ZZ). The portal value "
                    "0.7935 pb (MiniAOD 74313) is production only and is NOT used."),
           "matan_hand_check": PENDING, "product_of_factors": x74}
    m74 = portal(74313)
    new["74314"] = new_entry(74314, 74313, x74, portal(74314)["title"], "powheg+jhugen", b74)
    if abs(float(m74["cross_section"]["total_value"]) - 0.7935) > 1e-9:
        raise SystemExit("STOP: 74313 portal value changed")

    old40062 = recs["40062"]["cross_section_pb"]
    f40 = [SGG, BRZZ, atl, filt(0.1505, "40062", "HIG-RunIISummer20UL16wmLHEGEN-00294", "filter_efficiency", "0.1505")]
    x40 = math.prod(f["value"] for f in f40)
    recs["40062"]["cross_section_pb"] = x40
    recs["40062"]["estimate"] = False
    recs["40062"]["matan_hand_check"] = PENDING
    recs["40062"]["decision_2026_11_28"] = {
        "decided": DECIDED + " (D-40062)", "source_file": "studies/cms_mc_weights_v3/sources/" + DECISIONS.name,
        "construction": f"{SGG['value']} x {BRZZ['value']} x (2 x {b} - {b}^2) x 0.1505",
        "factors": f40, "order": "LO (JHUGen gg->ZH) normalised to YR4 x BR x McM filter efficiency",
        "supersedes": f"decision_2026_11_03 (v5 value {old40062} pb, ESTIMATE eps = 0.19178 in place of BR(Z->ll) x filter)",
        "old_value_v5_pb": old40062, "new_over_old": x40 / old40062,
        "note": "Same JHUGen decay card as 74314 (ZZ2l2any_withtaus_filter4l.input). The filter efficiency now comes from McM.",
        "matan_hand_check": PENDING, "product_of_factors": x40}

    for rid, e in new.items():
        recs[rid] = e
    # ---- exclusions ----
    exc = out["deliberately_excluded_records"]
    exc["records"] = sorted(set(exc["records"]) - {"74314"} | set(DALITZ) | {"69771"})
    exc["why"].pop("74314", None)
    for r in DALITZ:
        exc["why"][r] = ("D-N3 (Matan, 28 Nov 2026): Higgs Dalitz NOT added -- the sample contains the full H->ll gamma "
                         "decay incl. the Z pole (MadSpin, kHza = 1) and overlaps our H->Z gamma samples (m_ll > 50 GeV)")
    exc["why"]["69771"] = ("D-WZ (Matan, 28 Nov 2026): no top exclusion (a top quark in 62 % of file-0 events), double "
                           "counting our tZq 68325")
    for rid, rec in recs.items():
        if rec["k_factor"] != 1.0 or rec["gen_filt_eff"] != 1.0 or rec["sum_of_weights"] is not None:
            raise SystemExit(f"record {rid}: k_factor/gen_filt_eff must stay 1.0, sum_of_weights null")
        if rid in exc["records"]:
            raise SystemExit(f"record {rid} is both in the registry and excluded")
    out["what"] = ("CMS MC normalisation registry, v6 (Nominal-6 additions, 28 Nov 2026). Keyed by CERN Open Data record ID. "
                   "Every value with matan_hand_check = PENDING awaits Matan's hand check: do NOT build with v6 before a "
                   "separate commit sets them to VERIFIED BY MATAN.")
    out["generated_by"] = "studies/cms_mc_weights_v3/build_registry_v6.py"
    out["previous_version"] = ("studies/cms_mc_weights_v3/cms_mc_normalisation_v5.json (all records carried over; only the "
                               "new Nominal-6 records are added and 40062 changes value)")
    out["decisions"] = v5["decisions"] + f"; studies/cms_mc_weights_v3/sources/{DECISIONS.name} (Matan, 28 Nov 2026)"
    out["estimates"] = {k: v for k, v in v5["estimates"].items() if k != "40062"}
    out["matan_hand_check_pending"] = sorted([r for r, v in recs.items() if v.get("matan_hand_check") == PENDING], key=int)
    out["full_run_records"] = [r for r, v in recs.items() if v["in_full_run"]]
    out["not_in_full_run_records"] = {r: v5["not_in_full_run_records"][r] for r, v in recs.items() if not v["in_full_run"]}
    out["n_records"] = len(recs)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    payload = json.dumps(build(), indent=2, ensure_ascii=False) + "\n"
    if args.check:
        ok = OUTPUT.exists() and OUTPUT.read_text(encoding="utf-8") == payload
        print(("OK: " if ok else "FAIL: ") + f"{OUTPUT.name} {'matches' if ok else 'differs from'} build_registry_v6.py output")
        return 0 if ok else 1
    OUTPUT.write_text(payload, encoding="utf-8")
    b = json.loads(payload)
    print(f"wrote {OUTPUT}: {b['n_records']} records, {len(b['full_run_records'])} in the full run, "
          f"{len(b['not_in_full_run_records'])} not, {len(b['deliberately_excluded_records']['records'])} excluded, "
          f"{len(b['matan_hand_check_pending'])} PENDING: {b['matan_hand_check_pending']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
