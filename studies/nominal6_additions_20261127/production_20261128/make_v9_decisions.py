#!/usr/bin/env python
"""Writes studies/cms_mc_weights_v3/sources/v9_decisions_2026-11-28.json: Matan's decisions of 28 Nov 2026 ("approve
all" of the technical lead's recommendations), recorded VERBATIM, plus the facts this task adds (cleanup measured, the
WZjj outcome from evidence/wzjj/wzjj_outcome.json). DECISION RECORD: the values it names are entered in registry v6
with matan_hand_check = PENDING; nothing here is VERIFIED BY MATAN yet.

    python production_20261128/make_v9_decisions.py
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
OUT = HERE.parents[0] / "cms_mc_weights_v3" / "sources" / "v9_decisions_2026-11-28.json"
WZ = json.loads((HERE / "evidence" / "wzjj" / "wzjj_outcome.json").read_text())

V = {
 "D-clean": "ALREADY DONE (28 Nov, commit 5197b43 on prep/nominal6-additions-20261127): only .../work/mcexp_20261103/nominal6_precheck_20261127/gridpack_cards/ was deleted, 10,710 entries, file count 133,497 → 122,787. Just confirm the folder is gone and record it in the decision file. Nothing else may be deleted.",
 "D-N1": "Electroweak VV+2 jets: normalise with the CMS portal value (MiniAOD metadata.cross_section.total_value, rule R1; the v5 convention for generator samples such as the tribosons and ttW/ttZ): 75561 ZZJJTo4L_EWKnotop (MiniAOD 75560) 0.0009928 pb; 72648 WWJJToLNuLNu_EWK_noTop (72647) 0.09219 pb; 71636 WpWpJJ_EWKnotop (71635, contains W+W+ and W-W-) 0.02694 pb. Document: CMS generator cut m_jj > 100 GeV and on-shell W/Z (ATLAS: no m_jj cut, off-shell incl. low-mass gamma*), hence CMS/ATLAS ≈ 0.07–0.63 per channel; no interference sample; triboson-like region partly overlapping our tribosons (as on the ATLAS side); s-channel H->WW in 1.3 % of 72648 events (tiny overlap with our VBF H->WW) accepted.",
 "D-WZ": "69771 WLLJJ_WToLNu_EWK is NOT used (no top exclusion: a top quark in 62 % of events, double counting our tZq 68325). Instead: check whether a WZ+2 jets EW record WITH top exclusion exists — first 72728 WZJJ_EWK_InclusivePolarization, then any other UL16 NanoAODv9 postVFP WZjj EW record. \"Top excluded\" must be VERIFIED from the gridpack process card ('$ t t~' or equivalent) AND by running: fraction of events with a generator top quark in file 0 (as gen_check did on 27 Nov). If one is found with top excluded and W->lnu, Z->ll (or a superset that you describe exactly), it replaces 69771: add it to production, with its portal value recorded as a PROPOSAL pending Matan's hand check. If none is found, WZjj is dropped and documented (reason: only CMS sample double counts tZq).",
 "D-N2": "71640 WpWpJJ_QCDnotop (MiniAOD 71639): portal value 0.02037 pb. Document: 8 % below ATLAS 700603 (0.02221 pb).",
 "D-N3": "Higgs Dalitz NOT added (documented; moves from \"add\" to \"documented\"). Reason: the CMS Dalitz samples contain the full H->ll gamma decay incl. the Z pole (MadSpin, kHza = 1); about half of the mumu and a third of the ee events overlap our H->Z gamma samples (m_ll > 50 GeV); avoiding it needs a new generator-level m_ll veto in the production code and an ee normalisation that is not published; gain ≈ 100 events before selection over all modes. ATLAS separates by amplitude (Pythia gamma* conversion, no Z interference).",
 "D-N4": "74314 ZH_HToZZ_4LFilter: option C of the 27 Nov report = sigma(qq->ZH, YR4, mH = 125.00) × BR(H->ZZ*, YR4, mH = 125.00) × (2B − B²) × 0.1509, with B = BR(Z->ll), l = e, mu, tau (PDG, the same value v5 uses), 0.1509 = McM filter efficiency = the 4-lepton filter (INTERPRETATION supported by the file-0 decay mix; document it). Use EXACTLY the YR4 and PDG numbers already used in registry v5 (cite the v5 entries you take them from); show the arithmetic. Document: broader than ATLAS 346645 (H->4l only): it also contains Z(->ll) H(->ZZ->ll X); no overlap with our other ZH samples (none has H->ZZ).",
 "D-40062": "Correct the delivered 40062 (gg->ZH, H->ZZ->4l, same JHUGen card ZZ2l2any_withtaus_filter4l) with the same construction as D-N4: sigma(gg->ZH, YR4) × BR(H->ZZ*) × (2B − B²) × the 4-lepton filter efficiency of 40062 (from its McM request; if McM gives none, use the 74314 value 0.1509 and label it ESTIMATE, same card). Show old value (v5) vs new and the ratio (expected ≈ 1.49).",
 "D-ceiling": "Planning ceiling 140,000 cluster files (unchanged from 27 Nov).",
 "HAND_CHECK_RULE": "Matan will hand-check every new value on the portal. Therefore registry v6 is written with each new/changed value carrying \"matan_hand_check\": \"PENDING\" (plus the full source block). Production does not use the registry (the driver reads no registry), so production can start now. The MC build (a later task) may only run after Matan has confirmed the values and the flags have been set to VERIFIED BY MATAN in a separate commit.",
}


def main():
    out = {
        "what": ("DECISION RECORD. Matan's decisions of 28 Nov 2026 (\"approve all\" of the technical lead's recommendations "
                 "on studies/nominal6_additions_20261127/REPORT.md), recorded verbatim in 'decisions_verbatim'. The values "
                 "are entered in cms_mc_normalisation_v6.json with matan_hand_check = PENDING; the MC build may run only "
                 "after Matan's hand check and a separate commit setting them to VERIFIED BY MATAN."),
        "decided": "Matan, 28 Nov 2026",
        "decisions_verbatim": V,
        "facts_recorded_by_this_task": {
            "D-clean": {"folder_absent_28_nov": True, "checked": "ls on wipp-home 28 Nov 2026: 'No such file or directory'",
                        "file_count_lfs_quota_col6": 122787, "nothing_else_deleted": True},
            "D-WZ": WZ,
        },
        "add_to_production": [75561, 72648, 71636, 71640, 74314] + ([WZ["replacement_nano_recid"]] if WZ.get("replacement_nano_recid") else []),
        "documented_not_added_new": {"N3": [37276, 37420, 68459, 68559, 69681, 69699, 74652, 74670],
                                     "69771": "D-WZ: no top exclusion, double counts tZq 68325"},
        "changed_delivered_value": {"40062": "D-40062 (PENDING Matan's hand check)"},
        "ceiling_cluster_files": 140000,
    }
    OUT.write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n")
    print(OUT)


if __name__ == "__main__":
    main()
