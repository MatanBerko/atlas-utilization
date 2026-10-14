"""
Shared record table for this study: the 7 primary CMS 2016 datasets, both
run eras (G, H), Tau excluded per this task's own out-of-scope list.

Record IDs and expected (G+H) file counts are copied verbatim from this
task's own brief -- not derived -- and are independently checked against
the CERN Open Data portal's own file-list/metadata API by
fetch_record_file_lists.py, which is the actual source of truth used
everywhere else in this study.

Trigger sets and veto (de-duplication) priority order are likewise copied
verbatim from the task brief. Priority order highest-first: DoubleMuon >
DoubleEG > MuonEG > SingleMuon > SingleElectron > JetHT > MET.
"""
from __future__ import annotations

from typing import Dict, List, NamedTuple


class DatasetRecords(NamedTuple):
    label: str
    record_g: int
    record_h: int
    expected_files_g_plus_h: int
    trigger_paths: List[str]


# Order = veto priority, highest first.
DATASETS: List[DatasetRecords] = [
    DatasetRecords("DoubleMuon", 30522, 30555, 57,
                    ["HLT_Mu17_TrkIsoVVL_Mu8_TrkIsoVVL_DZ", "HLT_Mu17_TrkIsoVVL_TkMu8_TrkIsoVVL_DZ"]),
    DatasetRecords("DoubleEG", 30521, 30554, 133,
                    ["HLT_Ele23_Ele12_CaloIdL_TrackIdL_IsoVL_DZ"]),
    DatasetRecords("MuonEG", 30528, 30561, 48,
                    ["HLT_Mu23_TrkIsoVVL_Ele12_CaloIdL_TrackIdL_IsoVL_DZ",
                     "HLT_Mu8_TrkIsoVVL_Ele23_CaloIdL_TrackIdL_IsoVL_DZ"]),
    DatasetRecords("SingleMuon", 30530, 30563, 152,
                    ["HLT_IsoMu24", "HLT_IsoTkMu24"]),
    DatasetRecords("SingleElectron", 30529, 30562, 151,
                    ["HLT_Ele27_WPTight_Gsf"]),
    DatasetRecords("JetHT", 30525, 30558, 142,
                    ["HLT_PFHT900", "HLT_PFJet450"]),
    DatasetRecords("MET", 30526, 30559, 49,
                    ["HLT_PFMET170_HBHECleaned", "HLT_PFMET170_NotCleaned"]),
]

VETO_ORDER = [d.label for d in DATASETS]  # already highest-priority first

# MuonEG non-DZ paths, read ONLY for the Step 1(b)/(c) menu-gap and
# prescale-nesting checks -- never used as the actual MuonEG trigger
# requirement in Step 2+ (task brief: "Read those non-DZ paths too for
# this purpose").
MUONEG_NONDZ_PATHS = [
    "HLT_Mu23_TrkIsoVVL_Ele12_CaloIdL_TrackIdL_IsoVL",
    "HLT_Mu8_TrkIsoVVL_Ele23_CaloIdL_TrackIdL_IsoVL",
]

# Nested-reference pairs for the prescale test (task brief Step 1(c)):
# (looser_path, stricter_path) -- stricter firing should imply looser's
# condition is met, so per-run N(looser AND stricter)/N(stricter) tests
# whether the LOOSER path is prescaled.
NESTED_REFERENCE_PAIRS = [
    ("HLT_PFJet450", "HLT_PFJet500"),
    ("HLT_IsoMu24", "HLT_IsoMu27"),
    ("HLT_IsoTkMu24", "HLT_IsoTkMu27"),
    ("HLT_Ele27_WPTight_Gsf", "HLT_Ele32_eta2p1_WPTight_Gsf"),
    # MuonEG: the DZ path requires everything the non-DZ path requires PLUS
    # an extra dz-vertex-matching cut, so DZ firing implies the non-DZ
    # path's own condition is met -- non-DZ is the "looser" reference here.
    ("HLT_Mu23_TrkIsoVVL_Ele12_CaloIdL_TrackIdL_IsoVL",
     "HLT_Mu23_TrkIsoVVL_Ele12_CaloIdL_TrackIdL_IsoVL_DZ"),
    ("HLT_Mu8_TrkIsoVVL_Ele23_CaloIdL_TrackIdL_IsoVL",
     "HLT_Mu8_TrkIsoVVL_Ele23_CaloIdL_TrackIdL_IsoVL_DZ"),
    # MET: HLT_PFMET300 is a pure higher-MET-threshold version of the
    # PFMET170 paths (same underlying quantity, higher cut), so it is a
    # valid nested reference. HLT_PFMET110_PFMHT110_IDTight additionally
    # requires MHT>110, which is NOT strictly implied by PFMET170 alone --
    # it is read (MET_HIGHER_THRESHOLD_CANDIDATES) and its own marginal
    # fire count is reported, but it is deliberately NOT used as a nested
    # pair here (not a valid "stricter implies looser" test).
    ("HLT_PFMET170_HBHECleaned", "HLT_PFMET300"),
    ("HLT_PFMET170_NotCleaned", "HLT_PFMET300"),
]
# MET: any higher-threshold PFMET path present is checked as a nested
# reference against BOTH PFMET170 paths -- read as a list since which one
# exists (e.g. HLT_PFMET300) is itself an empirical question (Step 1a).
MET_HIGHER_THRESHOLD_CANDIDATES = ["HLT_PFMET300", "HLT_PFMET110_PFMHT110_IDTight"]

# All HLT branch names Step 1 needs to read, across every dataset's own
# trigger set plus every reference/non-DZ path above. A single flat list
# (order-independent; de-duplicated) so one per-file read covers everything.
def all_step1_hlt_branches() -> List[str]:
    branches: List[str] = []
    for d in DATASETS:
        branches.extend(d.trigger_paths)
    branches.extend(MUONEG_NONDZ_PATHS)
    for looser, stricter in NESTED_REFERENCE_PAIRS:
        branches.append(looser)
        branches.append(stricter)
    branches.extend(MET_HIGHER_THRESHOLD_CANDIDATES)
    return sorted(set(branches))


def records_for_era(era: str) -> Dict[str, int]:
    """era: 'G' or 'H'."""
    if era == "G":
        return {d.label: d.record_g for d in DATASETS}
    if era == "H":
        return {d.label: d.record_h for d in DATASETS}
    raise ValueError(f"unknown era {era!r}, expected 'G' or 'H'")


def all_records() -> List[tuple]:
    """[(label, era, record_id), ...] for all 14 dataset x era combinations."""
    out = []
    for d in DATASETS:
        out.append((d.label, "G", d.record_g))
        out.append((d.label, "H", d.record_h))
    return out
