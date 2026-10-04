#!/usr/bin/env python
"""
Step 1 evidence, part 2: cross-check the filterBits meanings read from the
real files against the CMSSW release that actually produced them
(CMSSW_10_6_26, the NANO-step release recorded on the Open Data portal for
these records), exactly as TRIGGER_MATCHING_SPEC.md did for the muons.

The point of this script is one structural fact that cannot be read off
the branch title alone: the 2016 HLT-menu override block in
`PhysicsTools/NanoAOD/python/triggerObjects_cff.py` replaces the
qualityBits formula for `sel.name=='Muon'` and `sel.name=='Tau'` ONLY.
The Electron selection is NOT overridden, so the Electron bits in these
2016 files are the DEFAULT (Run-2-latest) Electron formula, and each bit
can be traced to the HLT filter-name pattern that sets it.

Usage:
    python read_cmssw_bit_definitions.py --out evidence/cmssw_bit_definitions.json
"""
from __future__ import annotations

import argparse
import json
import re
import urllib.request
from pathlib import Path

URL = ("https://raw.githubusercontent.com/cms-sw/cmssw/CMSSW_10_6_26/"
       "PhysicsTools/NanoAOD/python/triggerObjects_cff.py")

# The electron bits this study uses, with the filter-name pattern that sets
# each one, so the claim "bit 16 is the DoubleEG dielectron filter" is
# traceable to a string in the config rather than to memory.
ELECTRON_BITS_OF_INTEREST = {
    1: "filter('*CaloIdLTrackIdLIsoVL*TrackIso*Filter')",
    2: "filter('hltEle*WPTight*TrackIsoFilter*')",
    16: "filter('hltEle*Ele*CaloIdLTrackIdLIsoVL*Filter')",
    32: "filter('hltMu*TrkIsoVVL*Ele*CaloIdLTrackIdLIsoVL*Filter*')",
}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--out", required=True)
    args = p.parse_args()

    src = urllib.request.urlopen(URL, timeout=60).read().decode()

    # The 2016 override loop: which selections does it actually touch?
    override_block = src.split("selections2016 = copy.deepcopy")[1].split(
        "run2_HLTconditions_2016.toModify")[0]
    overridden = re.findall(r"sel\.name=='(\w+)'", override_block)

    # Default Electron block (the one in force for 2016, since Electron is
    # not in `overridden`).
    ele_block = src.split("name = cms.string(\"Electron\")")[1].split("cms.PSet(")[0] \
        if 'name = cms.string("Electron")' in src else ""
    if not ele_block:
        # fall back: grab the region around the electron qualityBitsDoc
        i = src.find("1 = CaloIdL_TrackIdL_IsoVL")
        ele_block = src[max(0, i - 2000):i + 400]

    ele_doc_m = re.search(r'qualityBitsDoc = cms\.string\("(1 = CaloIdL_TrackIdL_IsoVL[^"]*)"\)', src)
    mu_default_doc_m = re.search(r'qualityBitsDoc = cms\.string\("(1 = TrkIsoVVL, 2 = Iso, 4 = OverlapFilter PFTau, 8 = 1mu[^"]*)"\)', src)
    mu_2016_doc_m = re.search(r'qualityBitsDoc = cms\.string\("(1 = TrkIsoVVL, 2 = Iso, 4 = OverlapFilter PFTau, 8 = IsoTkMu[^"]*)"\)', src)
    mu_2016_bits_m = re.search(r"sel\.qualityBits = cms\.string\(\"(filter\('\*RelTrkIso\*Filtered0p4'\)[^\"]*)\"\)", src)

    out = {
        "source_url": URL,
        "cmssw_release": "CMSSW_10_6_26",
        "why_this_release": "the NANO-step release recorded on the CERN Open Data "
                            "portal for these records (same cross-check "
                            "TRIGGER_MATCHING_SPEC.md Section 0 did for the muons)",
        "selections_replaced_by_the_2016_override": overridden,
        "electron_is_overridden_for_2016": "Electron" in overridden,
        "consequence": (
            "The 2016 override replaces the qualityBits formula for Muon and Tau "
            "ONLY. The Electron selection keeps the DEFAULT (Run-2-latest) formula, "
            "which is why the real 2016 files' Electron portion of the "
            "TrigObj_filterBits title carries all 14 bits while the Muon portion "
            "carries only the 5 override bits."
        ),
        "electron_qualityBitsDoc_default": ele_doc_m.group(1) if ele_doc_m else None,
        "muon_qualityBitsDoc_default_NOT_used_for_2016": mu_default_doc_m.group(1) if mu_default_doc_m else None,
        "muon_qualityBitsDoc_2016_override_IN_FORCE": mu_2016_doc_m.group(1) if mu_2016_doc_m else None,
        "muon_qualityBits_2016_override_formula": mu_2016_bits_m.group(1) if mu_2016_bits_m else None,
        "electron_bits_used_by_this_study": {
            str(bit): {
                "filter_pattern": pat,
                "present_in_source": pat.replace("filter('", "").replace("')", "") in src,
            } for bit, pat in ELECTRON_BITS_OF_INTEREST.items()
        },
        "key_finding_muon_side": (
            "The DEFAULT muon formula contains a cross-trigger bit "
            "32*filter('hltMu*TrkIsoVVL*Ele*CaloIdLTrackIdLIsoVL*Filter*') = '1mu-1e'. "
            "The 2016 override REPLACES the whole formula and does NOT include it. "
            "So for these files there is NO muon bit that identifies the MuonEG "
            "muon leg specifically: the only usable muon bit is bit 1 (TrkIsoVVL), "
            "whose 2016 pattern '*RelTrkIso*Filtered0p4' is wildcarded and is shared "
            "with the DoubleMuon dimuon legs."
        ),
        "key_finding_electron_side": (
            "The electron side DOES have per-path bits, because it kept the default "
            "formula: bit 16 ('2e', hltEle*Ele*CaloIdLTrackIdLIsoVL*Filter) is the "
            "DIELECTRON filter (DoubleEG), bit 32 ('1e-1mu', "
            "hltMu*TrkIsoVVL*Ele*CaloIdLTrackIdLIsoVL*Filter*) is the MUON-ELECTRON "
            "cross filter (MuonEG electron leg), and bit 2 ('1e (WPTight)', "
            "hltEle*WPTight*TrackIsoFilter*) is the single-electron WPTight filter "
            "(SingleElectron). This is a genuine bit-level separation, better than "
            "what the 2016 muon bits allow."
        ),
    }

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(out, indent=2), encoding="utf-8")
    print("selections replaced by the 2016 override:", overridden)
    print("Electron overridden for 2016:", out["electron_is_overridden_for_2016"])
    for bit, d in out["electron_bits_used_by_this_study"].items():
        print(f"  electron bit {bit}: pattern present in source = {d['present_in_source']}")
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
