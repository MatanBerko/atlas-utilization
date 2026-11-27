#!/usr/bin/env python
"""Writes studies/cms_mc_weights_v3/sources/v8_decisions_2026-11-27.json: Matan's decision of 27 Nov 2026 ("Option A")
on the Nominal-6 comparison, recorded VERBATIM. DECISION RECORD ONLY: no cross section, k-factor, filter efficiency or
branching ratio is adopted here; no registry (v3-v5) changes. Record titles and MiniAOD ids are copied from the saved
portal records (evidence/mcm_index.json).

    python tools/make_v8_decisions.py
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
OUT = HERE.parents[0] / "cms_mc_weights_v3" / "sources" / "v8_decisions_2026-11-27.json"
IDX = json.loads((HERE / "evidence" / "mcm_index.json").read_text())["records"]

VERBATIM = """"Option A": ADD four items from the Nominal-6 comparison; DOCUMENT the rest; KEEP the CMS-only samples.
- ADD (14 samples), subject to Matan's hand check of every cross section (NOT in this task):
  N1 electroweak VV+2 jets: 75561 ZZJJTo4L_EWKnotop, 69771 WLLJJ_WToLNu_EWK, 72648 WWJJToLNuLNu_EWK_noTop, 71636 WpWpJJ_EWKnotop. No interference sample (CMS has none separately; ATLAS 700591–700594 ≈ 6 % of its EW VV+2j total) — documented. The partial overlap with our tribosons (triboson-like diagrams) is the same as on the ATLAS side — documented.
  N2 QCD same-sign WW: 71640 WpWpJJ_QCDnotop.
  N3 Higgs Dalitz H->gamma* gamma->ll gamma, ee and mumu: ggF 37276/37420, VBF 68459/68559, WH 69681/69699, ZH 74652/74670 — on condition that the overlap with our H->Z gamma samples is settled first (Part B2).
  N4 qq->ZH, H->ZZ->4l: 74314 ZH_HToZZ_4LFilter.
- DOCUMENTED, not added (reason in brackets): N5 VBF H->ZZ->llbb [the only CMS sample 68833 contains our 68741 and 68847]; N6 gg->ZH H->tautau/mumu [no CMS sample]; N7 three-top [~18 events before selection for ~320 cluster files; negligible]; N8 VH H->invisible with leptonic V [no CMS sample]; N9 tZq Z->nunu/qq part [no CMS sample; our 68325 covers Z->ll]; N10 inclusive VBF/VH Higgs [would double count every VH sample we have; ATLAS double counts here itself — question to Maryna]; N11 V+gamma [overlaps our W+jets and Drell–Yan photon radiation; no sample-level photon overlap removal exists in either pipeline; ATLAS double counts]; N12 V+2 photons / EW V gamma jj / 3 photons [partly no CMS sample; CMS portal cross sections wrong by orders of magnitude; same overlap as N11]; N13 hadronic W/Z at high pT and hadronic V+gamma [no prompt lepton: enters lepton-triggered data only via fake leptons, dominated by the QCD multijet absent on both sides; ~3,710 cluster files]; N14 WZ/ZZ -> quarks + neutrinos, ZZ->4nu [no prompt lepton; partly no CMS sample]; N15 tW fully hadronic part [our tW is NoFullyHadronic; difference has no prompt lepton].
- KEPT, CMS-only, documented: C1 hadronic t-channel (ours inclusive, ATLAS leptonic top only); C2 hadronic triboson decays (ours inclusive, ATLAS lepton-filtered); C3 ggF/VBF H->ZZ->2l2nu (37616, 68741; no ATLAS exclusive sample); C4 VH H->WW with all decays (41873, 41877, 41914, 40095).
- Cluster file ceiling: Matan accepts raising the planning ceiling from 125,000 to 140,000 for this addition (it is his planning figure, not a hard quota; still measure and report)."""

ADD = {"N1": [75561, 69771, 72648, 71636], "N2": [71640],
       "N3": [37276, 37420, 68459, 68559, 69681, 69699, 74652, 74670], "N4": [74314]}
ATLAS = {"N1": [700587, 700588, 700589, 700590, 700591, 700592, 700593, 700594], "N2": [700603],
         "N3": [345961, 345834, 345963, 345964, 345965], "N4": [346645]}
DOCUMENTED = [
    ("N5", "VBF H->ZZ->llbb", [450576], [68833], "the only CMS sample 68833 contains our 68741 and 68847"),
    ("N6", "gg->ZH H->tautau/mumu", [600686, 345098], [], "no CMS sample"),
    ("N7", "three-top", [304014], [67771, 68067], "~18 events before selection for ~320 cluster files; negligible"),
    ("N8", "VH H->invisible with leptonic V", [], [], "no CMS sample"),
    ("N9", "tZq Z->nunu/qq part", [410560], [68325], "no CMS sample; our 68325 covers Z->ll"),
    ("N10", "inclusive VBF/VH Higgs", [346317, 346310, 346311, 346312], [69389],
     "would double count every VH sample we have; ATLAS double counts here itself — question to Maryna"),
    ("N11", "V+gamma", [], [69575, 73904, 73900],
     "overlaps our W+jets and Drell–Yan photon radiation; no sample-level photon overlap removal exists in either pipeline; ATLAS double counts"),
    ("N12", "V+2 photons / EW V gamma jj / 3 photons", [], [42145, 42137],
     "partly no CMS sample; CMS portal cross sections wrong by orders of magnitude; same overlap as N11"),
    ("N13", "hadronic W/Z at high pT and hadronic V+gamma", [], [69751, 69753, 69755, 69757, 74912, 74914, 74916, 74918, 69559],
     "no prompt lepton: enters lepton-triggered data only via fake leptons, dominated by the QCD multijet absent on both sides; ~3,710 cluster files"),
    ("N14", "WZ/ZZ -> quarks + neutrinos, ZZ->4nu", [], [75571], "no prompt lepton; partly no CMS sample"),
    ("N15", "tW fully hadronic part", [601352, 601355], [64881, 64825],
     "our tW is NoFullyHadronic; difference has no prompt lepton"),
]
KEPT = [
    ("C1", "hadronic t-channel", [64759, 64659], "ours inclusive, ATLAS leptonic top only"),
    ("C2", "hadronic triboson decays", [72701, 72711, 72761, 75600], "ours inclusive, ATLAS lepton-filtered"),
    ("C3", "ggF/VBF H->ZZ->2l2nu", [37616, 68741], "no ATLAS exclusive sample"),
    ("C4", "VH H->WW with all decays", [41873, 41877, 41914, 40095], ""),
]


def main():
    nom = json.loads((HERE.parents[0] / "nominal6_correspondence_20261124" / "items.json").read_text())["items"]
    nom = {x["id"]: x for x in nom}
    out = {
        "what": ("DECISION RECORD ONLY, no values adopted. Matan's decision of 27 Nov 2026 on the Nominal-6 comparison "
                 "(studies/nominal6_correspondence_20261124/REPORT.md, commit 14cd426), recorded verbatim. No cross "
                 "section, k-factor, filter efficiency or branching ratio is adopted, and no registry (v3-v5) is changed. "
                 "The 14 records to add need Matan's hand check of every cross section first (options: "
                 "studies/nominal6_additions_20261127/REPORT.md); only after that can a registry v6 be written."),
        "decided": "Matan, 27 Nov 2026",
        "name": "Option A",
        "text_verbatim": VERBATIM,
        "add": {}, "documented_not_added": [], "kept_cms_only": [],
        "interference_note": ("N1: no CMS EW-QCD interference sample exists separately; ATLAS 700591-700594 are about 6 % "
                              "of the ATLAS EW VV+2j total (documented, not added)."),
        "triboson_overlap_note": ("N1: the partial overlap of EW VV+2j with our tribosons (triboson-like diagrams) is the same "
                                  "as on the ATLAS side (documented)."),
        "n3_condition": "N3 is added only once the overlap with our H->Z gamma samples (37604, 68731, 70301, 71145, 74292) is settled (REPORT.md section 2).",
        "cross_section_status": "NOT DECIDED: Matan hand-checks every cross section of the 14 records (separate step).",
        "cluster_file_ceiling": {"text": "Matan accepts raising the planning ceiling from 125,000 to 140,000 for this addition (it is his planning figure, not a hard quota; still measure and report).",
                                 "old": 125000, "new": 140000, "hard_quota": False},
    }
    for item, rids in ADD.items():
        out["add"][item] = {"description": nom[item]["description"], "atlas_dsids": ATLAS[item], "records": [
            {"nano_recid": r, "mini_recid": IDX[str(r)]["mini_recid"], "dataset": IDX[str(r)]["mcm_dataset_name"],
             "gen_prepid": IDX[str(r)]["gen_prepid"], "cross_section_pb": None,
             "cross_section_status": "NOT DECIDED (Matan's hand check pending)"} for r in rids]}
    for item, what, dsids, cms, why in DOCUMENTED:
        out["documented_not_added"].append({"item": item, "what": what, "reason": why, "atlas_dsids": nom[item]["atlas_dsids"],
                                            "cms_records_considered": cms})
    for item, what, recs, why in KEPT:
        out["kept_cms_only"].append({"item": item, "what": what, "cms_records_in_v5": recs, "atlas_dsids": nom[item]["atlas_dsids"], "reason": why})
    n = sum(len(v["records"]) for v in out["add"].values())
    assert n == 14, n
    OUT.write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n")
    print(OUT, n)


if __name__ == "__main__":
    main()
