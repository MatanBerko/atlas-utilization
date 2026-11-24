#!/usr/bin/env python
"""Candidate table: one row per (item, CMS NanoAOD record) from evidence/record_details.json.

Every portal number (events, files, cross section) is VERIFIED from the saved raw record (evidence/records/).
"est_cluster_files" is an ESTIMATE with the ratios of studies/mc_expansion_20261103/HANDOFF.md: 12 per input file
+ 2 per record (:142) plus build scratch 1,518 / 497 per input file (:152, :771). Roles:
  "candidate"   - the closest SM, nominal-tune, M125 record found for the item;
  "alternative" - another record that covers (part of) the same process; an open choice for Matan;
  "in_v5"       - already one of the 71 samples (for the comparison only).
Nothing here is adopted.

    python build_candidates.py > cms_candidates.csv
"""
import csv
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
PER_FILE = 12 + 1518 / 497
PER_RECORD = 2

CANDIDATES = {
    "N1": [(75561, "candidate", "ZZjj->4l EW (no top); vs ATLAS lllljj"),
           (69771, "candidate", "WZjj EW, W->lnu Z->ll; vs ATLAS lllvjj"),
           (72648, "candidate", "WWjj EW (no top) opposite-sign l nu l nu; vs ATLAS llvvjj os"),
           (71636, "candidate", "W+W+jj EW (no top); vs ATLAS llvvjj ss (W-W- not observed as a separate record)"),
           (72652, "alternative", "WWjj OS EW+QCD incl. interference (no top); vs ATLAS llvvjj_os_Int"),
           (75563, "alternative", "ZZjj->4l, title without EWK/QCD tag; content to be read in the record"),
           (71638, "alternative", "W+W+jj EW with top diagrams"),
           (64365, "alternative", "SSWW madgraph (inclusive same-sign WW jj)"),
           (72728, "alternative", "WZjj EW, inclusive polarisation (polarisation study sample)")],
    "N2": [(71640, "candidate", "W+W+jj QCD (no top); vs ATLAS llvv_ss QCD"),
           (71642, "alternative", "W+W+jj QCD with top diagrams"),
           (72678, "alternative", "WW->2l2nu double parton scattering (different process, listed for completeness)")],
    "N3": [(37420, "candidate", "ggH Dalitz mumu gamma"), (37276, "candidate", "ggH Dalitz ee gamma"),
           (68559, "candidate", "VBF Dalitz mumu gamma"), (68459, "candidate", "VBF Dalitz ee gamma"),
           (69699, "candidate", "WH Dalitz mumu gamma (W+ and W- together)"),
           (69681, "candidate", "WH Dalitz ee gamma (W+ and W- together)"),
           (74670, "candidate", "ZH Dalitz mumu gamma"), (74652, "candidate", "ZH Dalitz ee gamma")],
    "N4": [(74314, "candidate", "ZH, H->ZZ->4l filter (POWHEG MiNLO HZJ + JHUGen)"),
           (74300, "alternative", "ZH, H->ZZ, 2-lepton filter (contains most of the 4l events too)")],
    "N5": [(68833, "candidate", "VBF H->ZZ->2l2X (X = anything); broader than ATLAS llbb")],
    "N7": [(67771, "candidate", "ttt + jet (SM three-top, part 1)"), (68067, "candidate", "ttt + W (SM three-top, part 2)")],
    "N8": [(71359, "alternative", "W+H, W->qq, H->inv (hadronic W; ATLAS has W inclusive + MET>75)"),
           (70515, "alternative", "W-H, W->qq, H->inv"), (74892, "alternative", "ZH, Z->qq, H->inv"),
           (36929, "alternative", "ggZH, Z->qq, H->inv")],
    "N9": [(68325, "in_v5", "tZq, Z->ll only, NLO 4f (already in the 71)")],
    "N10": [(69389, "alternative", "VH (W+H, W-H, ZH) H->non-bb inclusive, aMC@NLO FxFx; overlaps every exclusive VH sample")],
    "N11": [(69575, "candidate", "W(lnu) gamma 0,1j NLO, inclusive photon pT"),
            (69569, "alternative", "W gamma, photon pT>130 slice"), (69571, "alternative", "W gamma, photon pT>300 slice"),
            (69573, "alternative", "W gamma, photon pT>500 slice"),
            (73904, "candidate", "Z(ll) gamma 0,1j NLO"), (73902, "alternative", "Z(ll) gamma, low m_ll / low photon pT"),
            (73900, "candidate", "Z(nunu) gamma NLO"), (73898, "alternative", "Z(mumu) gamma, 2<m_ll<15 GeV, LO")],
    "N12": [(42145, "candidate", "EW l nu gamma jj (no top); vs ATLAS lvgammajj"),
            (42137, "candidate", "EW ll gamma jj (no top); vs ATLAS llgammajj"),
            (69565, "alternative", "W gamma jj EW+QCD (no top)"),
            (73892, "alternative", "EW Z gamma jj, Z->ll, mll>50, mjj>120")],
    "N13": [(69751, "candidate", "W->qq HT 200-400"), (69753, "candidate", "W->qq HT 400-600"),
            (69755, "candidate", "W->qq HT 600-800"), (69757, "candidate", "W->qq HT>800"),
            (74912, "candidate", "Z->qq HT 200-400"), (74914, "candidate", "Z->qq HT 400-600"),
            (74916, "candidate", "Z->qq HT 600-800"), (74918, "candidate", "Z->qq HT>800"),
            (69559, "candidate", "W(->jj) gamma NLO")],
    "N14": [(75571, "candidate", "ZZ->2nu2q NLO (covers ATLAS ZqqZvv and ZbbZvv)")],
    "N15": [(64881, "candidate", "tW top, inclusive decays"), (64825, "candidate", "tW antitop, inclusive decays"),
            (64895, "in_v5", "tW top, no fully hadronic decays"), (64839, "in_v5", "tW antitop, no fully hadronic decays")],
    "C1": [(64759, "in_v5", "t-channel top, inclusive decays"), (64659, "in_v5", "t-channel antitop, inclusive decays"),
           (64711, "alternative", "t-channel, top -> e decays only, CompHEP LO (top+antitop)"),
           (64745, "alternative", "t-channel, top -> tau decays only, CompHEP LO; a mu-decay SM record was not observed")],
    "C2": [(72701, "in_v5", "WWW inclusive"), (72711, "in_v5", "WWZ inclusive"), (72761, "in_v5", "WZZ inclusive"),
           (75600, "in_v5", "ZZZ inclusive"),
           (72698, "alternative", "WWW with a dilepton filter"), (72718, "alternative", "WWZ -> 4l 2nu")],
}


def main():
    det = json.loads((HERE / "evidence" / "record_details.json").read_text())["records"]
    w = csv.writer(sys.stdout)
    w.writerow(["item", "role", "nano_recid", "mini_recid", "dataset", "generators", "events", "files_complete_index",
                "files_flag", "portal_xs_total_value_pb", "portal_xs_filter_eff", "portal_xs_matching_eff",
                "est_cluster_files", "note", "labels"])
    for item, rows in CANDIDATES.items():
        for rid, role, note in rows:
            d = det[str(rid)]
            xs = d["portal_cross_section"] or {}
            n = d["files_complete_index"]
            w.writerow([item, role, rid, d["mini_recid"], d["title"].split("/")[1], " ".join(d["generators"]), d["events"],
                        n, d["files_flag"] or "", xs.get("total_value"), xs.get("filter_efficiency"),
                        xs.get("matching_efficiency"), round(n * PER_FILE + PER_RECORD), note,
                        "portal values VERIFIED; est_cluster_files ESTIMATE"])


if __name__ == "__main__":
    main()
