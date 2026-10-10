#!/usr/bin/env python
"""
Step 2 of the CMS multi-dataset BumpNet track: generalized per-file driver.

Built directly on studies/cms_coverage/per_dataset/triggered/cluster/
run_per_dataset_on_file.py (same object definitions from studies.m0m1j0_cms.selection,
same 186-combination pattern set, same chunked XRootD reading with retry) --
imported/copied conventions, not reimplemented. The one structural addition
over that script: dataset-vs-dataset de-duplication (inclusive + exclusive
shards) and a choice of population gate.

Order (per this study's own spec): chunked read -> golden JSON -> own
trigger (services.parsing.trigger_requirements.apply_trigger_requirement,
mode "any") -> object selection (studies.m0m1j0_cms.selection, unchanged)
-> population gate -> all 186 combinations (services.calculations.
combinatorics.get_all_combinations; asserted == 186) -> raw float32 masses
into two SqliteArrayShardWriter shards (inclusive, exclusive), same
signature format as run_coverage_on_file.py so the existing merge/
post-processing/delivery code can read them later, unmodified.

--population generic (default): >=2 selected objects of ANY type (same
topology-free gate as run_per_dataset_on_file.py).
--population v0: studies.m0m1j0_cms.selection.select_event_selection_cutflow
exactly as studies/cms_coverage/cluster/run_coverage_on_file.py calls it
(>=2 muons AND >=1 non-b jet). Exists ONLY for the Step 3 regression check
against that script's own DoubleMuon-only output -- select_event_selection_cutflow
re-applies its own hardcoded DoubleMuon 2-DZ-path trigger internally, which
is idempotent here (a no-op re-filter) ONLY when --dataset-label DoubleMuon,
since that is the exact same 2-path set as this driver's own "own trigger"
step for DoubleMuon. This mode is not meaningful for any other dataset and
is not used for one in this study.

--population matched (trigger-matching task, DoubleMuon and SingleMuon
ONLY -- see studies/cms_datasets/matching/TRIGGER_MATCHING_SPEC.md): the
population gate is CMS NanoAOD TrigObj-based trigger-object matching
(offline selected muon(s) matched dR<0.1 to a trigger object carrying the
path's own HLT filter bit, plus an online-pT floor), not just the event-
level trigger bit used by generic/v0 -- see matched_acceptance_mask. In
this mode ONLY, SingleMuon's own trigger set is HLT_IsoMu24 alone (not
IsoTkMu24); its exclusive shard is vetoed ONLY against DoubleMuon's own
ACCEPTANCE (fired AND matched), not against every higher-veto-priority
dataset's trigger bits the way generic/v0 do. generic and v0's own
behaviour (branches read, trigger sets, gate, veto logic) is completely
unaffected by this mode's existence.

Top-4 truncation (top-4 task, --population matched ONLY): in addition to
its normal inclusive/exclusive shards, a matched-mode job also writes
dataset_shard_top4_inclusive.sqlite / dataset_shard_top4_exclusive.sqlite,
built from the SAME accepted events with each event's selected objects
truncated to at most 4 (priority: leptons by pT, then b-jets by pT, then
light jets by pT -- see build_top4_object_record). Truncation happens
strictly AFTER the matched-mode acceptance gate and the DoubleMuon-veto
decision, so it never changes which events are accepted, which dataset an
event belongs to, or n_after_gate/n_exclusive -- only which objects
represent an already-accepted event in the final-state/combination step.
generic and v0 are completely unaffected by this addition.

nonjet4 final-state rule (nonjet4 task, --population matched ONLY; the
group's own definition, attributed to Shikma): a matched-mode job also
writes dataset_shard_nonjet4_inclusive.sqlite / _exclusive.sqlite, built
from the SAME accepted events (trigger matching, DoubleMuon acceptance,
the SingleMuon veto and the >=2-selected-objects gate are all evaluated
exactly as for the normal/top4 versions, BEFORE this rule). Let
N = (selected electrons + selected muons + selected b-jets) for an
accepted event (light jets never enter N). If N > 4, the event is
REJECTED from this version entirely (it contributes no rows to either
nonjet4 shard) -- this is the ONLY difference from top-4. If N <= 4, the
event's kept objects are identical to its top-4-truncated objects: ALL
selected electrons/muons/b-jets, plus selected light jets in decreasing
pT order up to 4 total kept objects (this is not a coincidence -- top-4's
own priority order is leptons, then b-jets, then light jets, so whenever
N<=4 every lepton/b-jet already has priority rank <4 and is kept
unconditionally, and the remaining slots are filled by light-jet pT
exactly as this rule specifies). The implementation therefore reuses
build_top4_object_record's own output rather than re-deriving the
truncation a second time, and then drops the N>4 rows. generic, v0 and
the existing top-4 shards/diagnostics are completely unaffected by this
addition (Hard Rule 5).

rare4 version (rare4 task, --population matched ONLY; the group's other
candidate reading of the same final-state question, pending their
decision between it and nonjet4): a matched-mode job also writes
dataset_shard_rare4_inclusive.sqlite / _exclusive.sqlite, built from the
SAME accepted events and the SAME N > 4 rejection rule as nonjet4 (N =
selected electrons + selected muons + selected b-jets, using the TRUE
per-event counts, never the display-capped label -- so rare4's own
reject mask is identical to nonjet4's, and the task's own cross-check
requires their rejected-event totals to match exactly). The ONLY
difference from nonjet4: for a KEPT (N<=4) event, rare4 keeps EVERY
selected object, including every selected light jet, completely
unpadded/untruncated -- i.e. rare4 is simply the NORMAL version's own
final-state grouping/labelling/combinations restricted to the N<=4 event
rows. The implementation therefore reuses the normal version's own
obj_record (already built above, byte-for-byte unmodified) and nonjet4's
own reject mask, rather than re-deriving either. generic, v0, and the
existing top-4/nonjet4 shards/diagnostics are completely unaffected by
this addition (Hard Rule 5).

Exact final-state labels (exact-jet-labels task, B1; ALL versions): a
final state's label is now the event's EXACT per-type multiplicity. It
used to be capped for display at 4 by
physics_calcs.limit_particles_in_fs, so e.g. an event with 5 light jets
was filed under "..._4j_..." and its masses were MERGED into the 4j
histograms. The group has decided each light-jet multiplicity gets its
own final state, so there are now separate 5j, 6j, 7j, ... (and
two-digit 10j, 11j, ...) final states. Nothing about which events are
accepted, which objects they
keep, the Version B reject rule, the 186 combinations, the binning or
the >=100-events-per-final-state rule changes: this is purely a
relabelling, and the total event count summed over all labels is
identical to the old capped grouping. See
_group_by_final_state_with_mask's own docstring for the full detail and
for the one shared-code parsing limitation this was checked against.

Because the grouping function is shared by all four versions, the
NORMAL version (which keeps every selected object) may now also show
counts above 4 for non-jet types, e.g. a "5m" label. That is accepted:
only rare4 (Version B) is delivered. top4 and nonjet4 keep at most 4
objects per event in total, so no count in those two versions can ever
exceed 4 and their labels are unchanged in practice.

Final-state name format (upstream-names task, (1); ALL versions): a
label now lists ONLY the configured object types, in upstream's own fixed
order e, m, j, g, t, b, skipping any type the object record does not
carry -- e.g. `0e_2m_5j_1b` rather than the previous
`0e_2m_5j_0g_0t_1b`. This is Maryna's decision: final-state and histogram
names must contain only the configured object types, exactly as the main
(upstream) pipeline produces them. The construction here is upstream's
own, copied from services/calculations/im_calculator.py and
services/calculations/physics_calcs.py at upstream commit 88d7a4b (see
FINAL_STATE_OBJECTS above and _group_by_final_state_with_mask below).
Exact light-jet multiplicities (5j, 6j, ...) are KEPT, which is also what
the upstream authors' own pending fix does. Verified before making the
change: none of the 186 combinations uses photons or taus, and the
Version B reject rule is computed from object COUNTS
(ak.num(electrons)+ak.num(muons)+ak.num(bjets) <= 4), never from a label
string -- so dropping the always-zero g/t tokens cannot affect any
selection, mass, or rejection decision.

Inclusive/exclusive de-duplication (task's own veto priority order, highest
first: DoubleMuon > DoubleEG > MuonEG > SingleMuon > SingleElectron > JetHT
> MET, services.datasets_records.VETO_ORDER): an event is "exclusive" to a
dataset if it passes that dataset's own trigger AND fails every
higher-priority dataset's own trigger set. Masses are computed ONCE per
(final state, combination) on the full (inclusive) population; the
exclusive shard's arrays are a SUB-ARRAY of the already-computed inclusive
array, selected via a cheaply-recomputed (count-only, no vector math)
boolean mask -- see _group_by_final_state_with_mask and
_recompute_exact_count_mask below -- never a second pass through
IMCalculator/_calculate_combination_invariant_mass. This is the "compute
once, split by mask" this study's own spec requires.

Usage:
    python run_dataset_on_file.py --dataset-label SingleMuon --record-id 30530 \
        --file-index 0 --output-dir /storage/.../job_SingleMuon_G_0 \
        --population generic
"""
from __future__ import annotations

import argparse
import json
import logging
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

import awkward as ak  # noqa: E402
import numpy as np  # noqa: E402
import uproot  # noqa: E402

from services.calculations import physics_calcs  # noqa: E402
from services.calculations.combinatorics import get_all_combinations, get_count, get_start  # noqa: E402
from services.calculations.im_calculator import IMCalculator  # noqa: E402
from services.parsing.validated_runs import (  # noqa: E402
    ValidatedRunsFilter, apply_validated_runs_filter, is_simulation,
)
from services.parsing.trigger_requirements import apply_trigger_requirement  # noqa: E402
from services.pipelines.im_pipeline import (  # noqa: E402
    _calculate_combination_invariant_mass,
    prepare_im_combination_name,
)
from services.storage.sqlite_shards import SqliteArrayShardWriter  # noqa: E402
from studies.m0m1j0_cms import selection  # noqa: E402
from studies.m0m1j0_cms.design_checks.common import fetch_file_list  # noqa: E402
from studies.cms_datasets.cluster.datasets_records import DATASETS, VETO_ORDER  # noqa: E402

DEFAULT_VALIDATED_RUNS_JSON = (
    "data/cms/validated_runs/Cert_271036-284044_13TeV_Legacy2016_Collisions16_JSON.txt"
)

TRIGGER_PATHS_BY_DATASET = {d.label: d.trigger_paths for d in DATASETS}

BASE_OBJECT_BRANCHES = (
    "run", "luminosityBlock", "event",
    "nMuon", "Muon_pt", "Muon_eta", "Muon_phi", "Muon_mass",
    "Muon_mediumId", "Muon_pfRelIso04_all", "Muon_charge",
    "nElectron", "Electron_pt", "Electron_eta", "Electron_phi", "Electron_mass",
    "Electron_cutBased", "Electron_charge",
    "nJet", "Jet_pt", "Jet_eta", "Jet_phi", "Jet_mass", "Jet_jetId",
    "Jet_btagDeepFlavB",
)

OBJECT_TYPES = ["Electrons", "Muons", "Jets", "BJets"]
# Copied verbatim from upstream services/calculations/im_calculator.py's
# IMCalculator.FINAL_STATE_OBJECTS at commit 88d7a4b (same tuple, same order).
# Only the types actually present in the object record end up in a label, so
# with OBJECT_TYPES as above a label reads e.g. "0e_2m_5j_1b".
FINAL_STATE_OBJECTS = (
    ("Electrons", "e"), ("Muons", "m"), ("Jets", "j"),
    ("Photons", "g"), ("Taus", "t"), ("BJets", "b"),
)
MIN_PARTICLES_IN_COMBINATION = 1
MAX_PARTICLES_IN_COMBINATION = 4
MIN_COUNT_PARTICLE_IN_COMBINATION = 1
MAX_COUNT_PARTICLE_IN_COMBINATION = 4
MAX_TOTAL_PARTICLES_IN_COMBINATION = 4
INCLUDE_SUBLEADING = True
MAX_SUBLEADING_INDEX = 1
FIELD_TO_SLICE_BY = "pt"

MIN_TOTAL_SELECTED_OBJECTS = 2  # generic population gate

# --- --population matched (trigger-matching task, see
# studies/cms_datasets/matching/TRIGGER_MATCHING_SPEC.md for the full
# derivation and cross-check against CMSSW_10_6_26's own
# PhysicsTools/NanoAOD/python/triggerObjects_cff.py). NEW mode only --
# --population generic and --population v0 are byte-for-byte unchanged
# (Hard Rule 5). ---
MATCHED_MODE_EXTRA_BRANCHES = (
    "nTrigObj", "TrigObj_pt", "TrigObj_eta", "TrigObj_phi", "TrigObj_id", "TrigObj_filterBits",
)
# In matched mode ONLY, SingleMuon's own trigger set is HLT_IsoMu24 alone
# (Maryna's explicit instruction) -- generic mode's SingleMuon trigger set
# (both IsoMu24 and IsoTkMu24) is untouched, since datasets_records.py
# itself is not modified.
SINGLEMUON_MATCHED_TRIGGER_PATHS = ("HLT_IsoMu24",)
TRIGOBJ_MUON_ID = 13
TRIGOBJ_BIT_TRKISOVVL = 1     # dimuon TrkIsoVVL leg (both legs, both DZ paths -- cannot distinguish 17 vs 8 GeV, see spec)
TRIGOBJ_BIT_ISO = 2           # Global("cr")-seeded isolated single-muon leg -- IsoMu24
TRIGOBJ_BIT_ISOTKMU = 8       # Track-seeded isolated single-muon leg -- IsoTkMu24 (not used to accept, only documented)
MATCH_DR_MAX = 0.1
DOUBLEMUON_MATCHED_MIN_MUONS = 2
DOUBLEMUON_MATCHED_LEADING_PT_MIN_GEV = 17.0
SINGLEMUON_MATCHED_MIN_MUONS = 1
SINGLEMUON_MATCHED_PT_MIN_GEV = 24.0
# Efficiency-plot binning (Step 3d): 1 GeV bins, 20-200 GeV; 0.1-wide |eta| bins, 0-2.5.
MATCHED_EFF_PT_BIN_EDGES = np.arange(20.0, 200.01, 1.0)
MATCHED_EFF_ETA_BIN_EDGES = np.arange(0.0, 2.501, 0.1)

# --- --population matched4 (electron-datasets task: the FOUR-dataset
# DoubleMuon + SingleMuon + DoubleEG + MuonEG delivery path). NEW mode
# only -- --population generic, v0 and matched are byte-for-byte
# unchanged, so every pre-existing invocation (including the delivered
# muon production) keeps its old behaviour exactly. See
# studies/cms_datasets/electron_prep/ELECTRON_MATCHING_SPEC.md for the
# derivation of every bit/threshold below and
# studies/cms_datasets/electron_vB/REPORT.md for this round's decisions. ---

# D2: the de-duplication priority order for THIS delivery path, highest
# first. It is deliberately NOT datasets_records.VETO_ORDER, which is
# DoubleMuon > DoubleEG > MuonEG > SingleMuon > SingleElectron > JetHT >
# MET: the group's order for this delivery keeps the two muon datasets on
# top so that the already-delivered muon file's attribution does not
# change, and SingleElectron is postponed entirely (no code, no runs).
# VETO_ORDER itself and every older mode that uses it are untouched.
DELIVERY_VETO_ORDER_4 = ["DoubleMuon", "SingleMuon", "DoubleEG", "MuonEG"]

# In matched4, as in matched, SingleMuon's own trigger set is HLT_IsoMu24
# alone (SINGLEMUON_MATCHED_TRIGGER_PATHS above). The other three datasets
# use their own sets from datasets_records.py unchanged.
MATCHED4_TRIGGER_PATHS = {
    "DoubleMuon": tuple(TRIGGER_PATHS_BY_DATASET["DoubleMuon"]),
    "SingleMuon": SINGLEMUON_MATCHED_TRIGGER_PATHS,
    "DoubleEG": tuple(TRIGGER_PATHS_BY_DATASET["DoubleEG"]),
    "MuonEG": tuple(TRIGGER_PATHS_BY_DATASET["MuonEG"]),
}

TRIGOBJ_ELECTRON_ID = 11
# Electron filterBits, read from the TrigObj_filterBits branch TITLE in the
# real UL2016 NanoAODv9 files (never from memory) -- see
# electron_prep/evidence/trigobj_titles_electron_datasets.json. The titles
# are re-read and asserted at runtime by assert_trigobj_bit_meanings (D6).
TRIGOBJ_BIT_E_2E = 16          # "16 = 2e"       -- DoubleEG dielectron filter
TRIGOBJ_BIT_E_1E1MU = 32       # "32 = 1e-1mu"   -- MuonEG electron leg

# D6: the bit meanings this code depends on, as substrings of the branch
# titles. A mismatch means the files are not the ones this acceptance was
# derived from, so the job stops rather than silently matching the wrong
# filter.
EXPECTED_TRIGOBJ_ID_TITLE_SUBSTRINGS = ("11 = Electron", "13 = Muon")
EXPECTED_TRIGOBJ_FILTERBITS_TITLE_SUBSTRINGS = (
    "16 = 2e",          # electron bit 16, required by DoubleEG
    "32 = 1e-1mu",      # electron bit 32, required by MuonEG
    "1 = TrkIsoVVL",    # muon bit 1, already used by matched mode (DoubleMuon)
    "2 = Iso",          # muon bit 2, already used by matched mode (SingleMuon)
)

# ---------------------------------------------------------------------------
# --is-mc mode (cms-mc-weights-v3, DESIGN.md Part D). Everything from here to
# the end of this block is NEW and reached ONLY when --is-mc is passed; the
# data path never evaluates any of it.
#
# Design references are to studies/cms_mc_weights_v3/DESIGN.md.
# ---------------------------------------------------------------------------

# D2: the SingleElectron candidate condition. Stored, never delivered -- its
# offline threshold (27/30/35 GeV) is undecided and out of scope, which is
# exactly why the OFFLINE pT of the matched electron is stored per entry
# instead of a boolean: the threshold becomes a re-read of the shards rather
# than a re-production.
ELE27_PATH = "HLT_Ele27_WPTight_Gsf"
TRIGOBJ_BIT_E_1E_WPTIGHT = 2        # "2 = 1e (WPTight)" -- the Ele27_WPTight_Gsf leg
ELE27_TRIGOBJ_PT_MIN_GEV = 27.0     # online, the 27 GeV leg
ELE27_MIN_MATCHED_ELECTRONS = 1
ELE27_NO_MATCH_SENTINEL = -1.0      # stored offline pT when nothing matched

# The electron bit-2 meaning is asserted at runtime from the file's own branch
# title, exactly as the four data acceptances assert theirs. Kept in a
# SEPARATE tuple from EXPECTED_TRIGOBJ_FILTERBITS_TITLE_SUBSTRINGS so the data
# path's own assertion is byte-for-byte the one it runs today (Hard Rule 8).
EXPECTED_TRIGOBJ_FILTERBITS_TITLE_SUBSTRINGS_MC = (
    "2 = 1e (WPTight)",   # electron bit 2, required by the Ele27 candidate
)

# D3: per-event MC information, mirroring PR #35's field names exactly so a
# later port is mechanical. See DESIGN.md D3 for why _mcChannelNumber carries
# the CERN Open Data RECORD ID (CMS NanoAOD has no per-event dataset
# identifier at all -- verified, 1504 branches scanned) and why _mcRunNumber
# is informationally empty in CMS (run == 1 on every probed record).
MC_EVENT_INFO_FIELD = "_mcEventInfo"
MC_EVENT_WEIGHT_FIELD = "_mcEventWeight"
MC_CHANNEL_NUMBER_FIELD = "_mcChannelNumber"
MC_RUN_NUMBER_FIELD = "_mcRunNumber"

# D3: raw per-entry sibling arrays written next to each mass signature in the
# same flush. "_mcw" is RESERVED for the FINAL normalised weight and is
# produced only by the build-time builder -- the driver never writes it.
MC_WEIGHT_SUFFIX = "_mcw"                    # reserved; not written here
MC_RAW_SIBLING_PREFIX = "_mcraw_"
MC_SIBLING_GENWEIGHT = "_mcraw_genw"         # genWeight                 float64
MC_SIBLING_L1PREFIRE = "_mcraw_l1pf"         # L1PreFiringWeight_Nom     float32
MC_SIBLING_PILEUP = "_mcraw_puntrue"         # Pileup_nTrueInt           float32
MC_SIBLING_ACCEPTANCE = "_mcraw_acc"         # acceptance bitmask        uint8
MC_SIBLING_ELE27_PT = "_mcraw_ele27pt"       # offline pT, -1 if none    float32
MC_SIBLING_SUFFIXES = (
    MC_SIBLING_GENWEIGHT, MC_SIBLING_L1PREFIRE, MC_SIBLING_PILEUP,
    MC_SIBLING_ACCEPTANCE, MC_SIBLING_ELE27_PT,
)

# D3: one bit per stored condition, in DELIVERY_VETO_ORDER_4 order followed by
# the SingleElectron candidate. DESIGN.md left "should the bare Ele27 fire
# decision be separable from the match" as a one-line choice for this round:
# it IS separable, via bit 5, because an un-matched fire is otherwise
# indistinguishable from no fire at all and the Ele27 efficiency cannot be
# measured without it.
MC_ACC_BIT_BY_LABEL = {
    "DoubleMuon": 1 << 0,     # 1
    "SingleMuon": 1 << 1,     # 2
    "DoubleEG":   1 << 2,     # 4
    "MuonEG":     1 << 3,     # 8
}
MC_ACC_BIT_ELE27_CANDIDATE = 1 << 4   # 16 -- fired AND a matched electron >= 27 GeV online
MC_ACC_BIT_ELE27_FIRED = 1 << 5       # 32 -- the path fired, match or not
MC_ACC_BITMASK_DTYPE = np.uint8       # 6 bits used of 8

# D4: the branches --is-mc additionally requires. A missing one is a hard
# error (read_events already raises on any missing required branch) -- never
# defaulted to 1, because a silent w_gen = 1 mis-normalises every sample that
# is not unit-weight.
MC_REQUIRED_BRANCHES = (
    "genWeight",
    "L1PreFiringWeight_Nom",
    "Pileup_nTrueInt",
)

# --dataset-label value that means "this is simulation, there is no data
# stream". Valid only together with --is-mc; it only names the job and the
# signature prefix, and carries no selection meaning whatsoever.
MC_DATASET_LABEL = "MC"

# D4: DoubleEG acceptance.
DOUBLEEG_MATCHED_MIN_ELECTRONS = 2
DOUBLEEG_TRIGOBJ_LEADING_PT_MIN_GEV = 23.0   # online, the 23 GeV leg
DOUBLEEG_OFFLINE_PT_MIN_GEV = 30.0           # the NEW acceptance-level offline cut
DOUBLEEG_THRESHOLD_MODES = ("leading_only", "both")
# APPROVED 7 Oct 2026 (Maryna/Matan), from the Step D measurement -- this
# is final, not provisional. Set by Step D's own fixed decision criterion
# (Delta_region = eff_sub(>30) - eff_sub(25-30) <= 2.0 pp in BOTH barrel
# and endcap => "leading_only", else "both"); see
# studies/cms_datasets/electron_vB/REPORT.md.
#
# MEASURED (VERIFIED BY RUNNING, 133 DoubleEG files, 6,156,955 population
# events, studies/cms_datasets/electron_vB/evidence/stepD_doubleeg_efficiency.json):
#   barrel Delta = 3.40 pp, 68% interval [3.38, 3.42]
#   endcap Delta = 18.11 pp, 68% interval [18.04, 18.19]
# Both are above 2.0 pp and 2.0 pp lies outside both 68% intervals, so the
# criterion selects "both" and the result is NOT borderline.
DOUBLEEG_THRESHOLD_MODE_DEFAULT = "both"

# D5: MuonEG acceptance. The muon leg cannot be trigger-matched in 2016
# NanoAOD (ELECTRON_MATCHING_SPEC.md section 4) -- it is taken from the
# path decision plus >=1 SELECTED offline muon.
MUONEG_PATH_MU23_ELE12 = "HLT_Mu23_TrkIsoVVL_Ele12_CaloIdL_TrackIdL_IsoVL_DZ"
MUONEG_PATH_MU8_ELE23 = "HLT_Mu8_TrkIsoVVL_Ele23_CaloIdL_TrackIdL_IsoVL_DZ"
MUONEG_ELECTRON_LEG_PT_MIN_GEV_BY_PATH = {
    MUONEG_PATH_MU23_ELE12: 12.0,
    MUONEG_PATH_MU8_ELE23: 23.0,
}
MUONEG_MIN_SELECTED_MUONS = 1

# D3: electron-muon overlap removal, applied in ALL FOUR datasets.
#
# RADIUS APPROVED 7 Oct 2026 (Maryna), raised from 0.05 to 0.12. Provenance,
# recorded so the number is never mistaken for an arbitrary choice:
#   * chosen by Maryna from the MuonEG/SingleElectron per-event min-dR(e,mu)
#     distribution, in which the collinear population -- electrons that are
#     really the same object as a nearby muon -- extends to about 0.12;
#   * ATLAS uses dR < 0.1 for this removal in ttbar MC;
#   * the CMS ZZ paper arXiv:2009.01186 uses 0.05, which is what this
#     pipeline used before 7 Oct 2026.
# The comparison "<" is strict, as before. Nothing else about the removal
# changes: same place in the order, all four datasets, muons never removed,
# jet cleaning untouched.
EMU_OVERLAP_DR_MAX = 0.12

# E5 diagnostic: m(e, mu) over every selected electron-muon pair, 0-20 GeV
# in 0.1 GeV bins. Diagnostics only -- the delivery binning (fixed 10 GeV,
# 0-10000 GeV) is untouched.
DIAGNOSTIC_EMU_MASS_FINE_BIN_EDGES = np.arange(0.0, 20.0001, 0.1)
# E5 diagnostic: m(e,e), 60-120 GeV in 0.5 GeV bins, split barrel-barrel
# vs other, using the same eta regions as the Step D measurement.
DIAGNOSTIC_EE_MASS_Z_BIN_EDGES = np.arange(60.0, 120.0001, 0.5)
# ECAL barrel/endcap boundaries -- the SAME values the electron_prep
# measurement uses (studies/cms_datasets/electron_prep/common.py), on the
# SAME eta variable the electron selection cuts on (Electron_eta).
ECAL_BARREL_ABS_ETA_MAX = 1.4442
ECAL_ENDCAP_ABS_ETA_MIN = 1.566

READ_RETRY_ATTEMPTS = 4
READ_RETRY_BACKOFF_SEC = 15
READ_CHUNK_SIZE = 300_000

COVERAGE_CAP_PER_SIGNATURE = 500_000

# Step 2 diagnostics (task spec): 1 GeV bins, 0-200 GeV.
DIAGNOSTIC_PT_BIN_EDGES = np.arange(0.0, 201.0, 1.0)
DIAGNOSTIC_MASS_BIN_EDGES = np.arange(0.0, 201.0, 1.0)
# 20 MeV bins, 0-10 GeV: 1 GeV bins cannot resolve the J/psi (natural width
# ~93 keV, CMS dimuon mass resolution ~O(10-40 MeV) near 3.1 GeV) at all --
# it would be completely washed out into the surrounding continuum. This
# finer histogram exists solely so a genuine J/psi peak is visible in the
# quality-gate report; it does not affect selection, gating, or shards.
DIAGNOSTIC_LOWMASS_FINE_BIN_EDGES = np.arange(0.0, 10.0001, 0.02)
# 0.02-wide eta bins, -2.6 to 2.6: fine enough to resolve the ECAL
# barrel-endcap transition (gap) region, 1.4442 < |eta| < 1.566 (a
# 0.1218-wide window) -- documentation only, does not affect selection
# (electrons in the gap are not vetoed, per this task's own instruction).
DIAGNOSTIC_ETA_BIN_EDGES = np.arange(-2.6, 2.6001, 0.02)
LOW_MASS_DIMUON_CUTOFF_GEV = 5.0
# MuonEG task, Step 1: electron-muon overlap diagnostics. 0.01-wide dR
# bins, 0-1.0 (100 bins) with an explicit overflow count (task spec) --
# dR(e0,mu0) and the per-event minimum dR over every selected
# electron-muon pair, restricted to events with >=1 selected electron AND
# >=1 selected muon. Documentation only: no overlap removal is added
# anywhere (this task's own explicit instruction).
DIAGNOSTIC_DR_EMU_BIN_EDGES = np.arange(0.0, 1.0001, 0.01)
# m(e0,mu0) bins: 0-5 GeV in 0.05 GeV steps (100 bins) -- a genuine
# collimated e-mu pair (one real muon also reconstructed as a nearby
# "electron") would show up as a low-mass excess here, the same idea as
# the existing low-mass dimuon diagnostic.
DIAGNOSTIC_EMU_LOWMASS_BIN_EDGES = np.arange(0.0, 5.0001, 0.05)


def git_commit_hash(repo_root) -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=str(repo_root), text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except Exception as e:  # noqa: BLE001
        return f"UNKNOWN ({type(e).__name__}: {e})"


def resolve_file_url(record_id: int, file_index: int) -> str:
    urls = fetch_file_list(record_id)
    if file_index < 0 or file_index >= len(urls):
        raise ValueError(
            f"record {record_id}'s portal file list currently has {len(urls)} "
            f"file(s); requested file-index {file_index} is out of range."
        )
    return urls[file_index]


def _read_chunk_with_retry(tree, branches, entry_start, entry_stop, file_url):
    last_exc = None
    for attempt in range(1, READ_RETRY_ATTEMPTS + 1):
        try:
            return tree.arrays(branches, entry_start=entry_start, entry_stop=entry_stop, library="ak")
        except Exception as e:  # noqa: BLE001 -- transient XRootD read failure
            last_exc = e
            print(f"read attempt {attempt}/{READ_RETRY_ATTEMPTS} failed for {file_url} "
                  f"[{entry_start}:{entry_stop}]: {type(e).__name__}: {e}", flush=True)
            if attempt < READ_RETRY_ATTEMPTS:
                time.sleep(READ_RETRY_BACKOFF_SEC)
    raise RuntimeError(
        f"{file_url} [{entry_start}:{entry_stop}]: failed to read after {READ_RETRY_ATTEMPTS} attempts"
    ) from last_exc


def read_events(file_url: str, required_branches, return_titles: bool = False):
    """`return_titles` (electron-datasets task, D6) additionally returns a
    {branch: title} dict for the requested branches, so the TrigObj
    filter-bit meanings can be asserted at runtime against the file's own
    branch titles. Default False -- every pre-existing caller is unchanged."""
    tree = uproot.open(file_url)["Events"]
    available = set(tree.keys())
    missing = [b for b in required_branches if b not in available]
    if missing:
        raise ValueError(
            f"{file_url}: missing required branch(es) {missing}. This includes "
            f"this dataset's own trigger paths and/or a higher-veto-priority "
            f"dataset's trigger paths, which this driver refuses to silently "
            f"treat as 'did not fire'."
        )
    branches = list(required_branches)
    n_entries = tree.num_entries
    chunks = []
    for start in range(0, n_entries, READ_CHUNK_SIZE):
        stop = min(start + READ_CHUNK_SIZE, n_entries)
        chunks.append(_read_chunk_with_retry(tree, branches, start, stop, file_url))
    events = ak.concatenate(chunks) if len(chunks) > 1 else chunks[0]
    if not return_titles:
        return events
    titles = {}
    for b in branches:
        try:
            titles[b] = tree[b].title
        except Exception as e:  # noqa: BLE001 -- a missing title must not kill the job
            titles[b] = f"UNAVAILABLE ({type(e).__name__}: {e})"
    return events, titles


def _group_by_final_state_with_mask(obj_record: ak.Array):
    """Group accepted events by their EXACT final state, and yield each
    group's own boolean mask into obj_record alongside it.

    Grouping formula: same deterministic string-building code as
    services.calculations.physics_calcs.group_by_final_state, with TWO
    documented differences:

    1. It also yields each group's boolean mask into obj_record, which the
       shared function computes internally but does not expose. Needed here
       only so the (already-computed) per-combination mass array can later
       be split into inclusive/exclusive sub-arrays by a cheap,
       alignment-preserving boolean mask, without a second combinatorics
       pass.

    2. exact-jet-labels task, B1: the yielded label is the event's EXACT
       per-type multiplicity (`raw_fs`), NOT
       `physics_calcs.limit_particles_in_fs(raw_fs, 4)`. Previously a count
       above 4 was displayed as "4", so an event with 5 light jets was
       filed under "..._4j_..." and its masses were MERGED into the 4j
       histograms. The group has decided each light-jet multiplicity gets
       its own final state, so 5 light jets now produces "5j", 6 produces
       "6j", 11 produces "11j", and so on.

    What this does and does not change:
      - The NAME FORMAT is upstream's (upstream-names task, (1)): one
        `<count><letter>` field per CONFIGURED object type, in upstream's
        fixed order e, m, j, g, t, b, types the object record does not
        carry omitted entirely, joined by "_". With this study's
        OBJECT_TYPES that is four fields, e.g. `0e_2m_5j_1b`. Counts can
        exceed 4 and can be two digits.
      - No event is added, dropped, reordered or altered. This is purely a
        relabelling: the total number of events summed over all labels is
        identical to the old capped grouping on the same input, and every
        event keeps exactly the objects it had. Events that used to share
        one "4j" label are now distributed across 4j/5j/6j/... labels
        according to their true light-jet count. See
        studies/cms_datasets/tests/test_exact_jet_labels.py for both properties.
      - Object definitions, trigger matching, de-duplication, the
        inclusive/exclusive split, the Version B (rare4) reject rule, the
        186-combination set, the binning and the >=100-events-per-final-
        state rule are all untouched.

    Which versions this affects: this function is shared by every version
    the driver writes (normal, top4, nonjet4, rare4), so all four now get
    exact labels. top4 and nonjet4 keep at most 4 objects in total per
    event by construction, so no count in those two can ever exceed 4 and
    their labels are unchanged in practice. The NORMAL version keeps every
    selected object, so its labels may now show counts above 4 for any type
    (e.g. "5m", "7j"); that is accepted -- only rare4 (Version B) is
    delivered. rare4 is where this change is wanted: it keeps ALL selected
    light jets, so it is the version whose 5+-light-jet events were being
    merged into 4j.

    Known shared-code limitation, NOT worked around here (reported, with a
    test, in studies/cms_datasets/tests/test_exact_jet_labels.py): the shared
    physics_calcs.is_finalstate_contain_combination reads only the FIRST
    character of each count field, so for a two-digit count (>=10) it fails
    to map the particle letter and silently SKIPS that type's requirement,
    i.e. treats it as satisfied. Verified by running: the largest
    (start + count) requirement over all 186 combinations is 4, for every
    object type, so a true count of >=10 satisfies every requirement anyway
    -- skipping the check returns the same answer the correct check would.
    No delivered result changes, so no study-local replacement is needed.

    Not related to this change: the shared IMCalculator has a separate
    upstream bug affecting events with 5+ light jets, which the upstream
    authors are fixing themselves. Nothing in this function or anywhere in
    this study works around or copies that fix."""
    # upstream-names task, (1): build the label from the CONFIGURED object
    # types only, in upstream's own fixed order, exactly as upstream's
    # services/calculations/im_calculator.py:_get_all_events_fs and
    # services/calculations/physics_calcs.py:group_by_final_state do at
    # upstream commit 88d7a4b -- same tuple, same order, same "present in
    # events.fields" filter, same "_" separator, same f"{count}{letter}".
    # Our obj_record (studies.m0m1j0_cms.selection.build_object_record)
    # carries exactly Electrons/Muons/Jets/BJets, so this yields e.g.
    # "0e_2m_5j_1b" -- no photon or tau field, hence no "0g"/"0t" token.
    # The construction itself now lives in exact_final_state_labels (same
    # code, moved unchanged) so the matched4 per-event debug dump can use
    # the identical labels without a second spelling of the rule.
    all_events_fs = exact_final_state_labels(obj_record)
    for raw_fs in sorted(set(all_events_fs.tolist())):
        mask = (all_events_fs == raw_fs)
        events_matching_fs = obj_record[mask]
        # exact-jet-labels task, B1: the EXACT multiplicity is the label.
        # Was: physics_calcs.limit_particles_in_fs(raw_fs, 4), which
        # displayed any count above 4 as "4" and so merged e.g. 5-light-jet
        # events into the 4j histograms. See this function's docstring.
        label = raw_fs
        yield label, events_matching_fs, mask


def _recompute_exact_count_row_mask(fs_events: ak.Array, combination: dict) -> np.ndarray:
    """Cheap (count-only, no vector math) recomputation of the boolean
    row-mask that services.calculations.physics_calcs.filter_events_by_particle_counts's
    is_exact_count=True branch applies internally, using the exact same
    'obj_count >= start + count' formula (that branch's row-reduction
    criterion despite its name -- read directly from
    physics_calcs.py:170-178 -- the is_exact_count flag only controls
    whether NON-combination fields are dropped afterwards, not the row
    filter itself). Recomputing this tiny boolean/count-only step a second
    time is NOT the "combinatorics cost" this study's spec says not to
    double -- that refers to the vector-math-heavy
    calculate_invariant_mass/_calculate_combination_invariant_mass call,
    which runs exactly once. This function exists solely to align the
    is_exclusive flag with the row-order _calculate_combination_invariant_mass
    already produced."""
    combined_mask = np.ones(len(fs_events), dtype=bool)
    for obj, value in combination.items():
        if obj not in fs_events.fields:
            if get_start(value) + get_count(value) > 0:
                combined_mask &= False
            continue
        obj_count = ak.to_numpy(ak.num(fs_events[obj]))
        combined_mask &= (obj_count >= get_start(value) + get_count(value))
    return combined_mask


def _histogram_1gev(values: np.ndarray, edges: np.ndarray) -> dict:
    finite = values[~np.isnan(values)]
    counts, _ = np.histogram(finite, bins=edges)
    return {"bin_edges_gev": edges.tolist(), "counts": counts.tolist(),
            "n_entries": int(finite.size), "n_nan_or_missing": int(values.size - finite.size)}


def _histogram_with_overflow(values: np.ndarray, edges: np.ndarray) -> dict:
    """Like _histogram_1gev, but also tracks an explicit overflow count
    (finite values >= edges[-1]) instead of silently excluding them --
    needed for the dR(e,mu) diagnostics (MuonEG task, Step 1 spec: '0 to
    1.0 in 0.01 bins, plus an overflow count')."""
    finite = values[~np.isnan(values)]
    in_range = finite[finite < edges[-1]]
    overflow = finite[finite >= edges[-1]]
    counts, _ = np.histogram(in_range, bins=edges)
    return {"bin_edges_gev": edges.tolist(), "counts": counts.tolist(),
            "n_entries": int(finite.size), "n_nan_or_missing": int(values.size - finite.size),
            "n_overflow": int(overflow.size)}


def _p4_no_mass_needed(obj, mass=None):
    """vector.zip helper for objects that don't carry their own mass field
    (TrigObj has none) -- deltaR/matching only needs pt/eta/phi, so a
    zero mass is used when none is supplied; harmless since mass never
    enters a deltaR calculation."""
    import vector
    vector.register_awkward()
    if mass is None:
        mass = ak.zeros_like(obj.pt)
    return vector.zip({"pt": obj.pt, "eta": obj.eta, "phi": obj.phi, "mass": mass})


def trigobj_best_match_pt(sel_muons: ak.Array, trigobj: ak.Array, required_bit: int,
                            dr_max: float = MATCH_DR_MAX) -> ak.Array:
    """For each selected muon (per event, jagged), the highest online pT
    among TrigObj entries with id==13, `filterBits & required_bit != 0`,
    within dR < dr_max -- or -inf if no such match exists for that muon.
    See TRIGGER_MATCHING_SPEC.md for why this bit + dR + pT combination is
    the matching/acceptance rule for these 2016-era files. Pure read of
    `trigobj`/`sel_muons` -- never writes to or filters either input.

    electron-datasets task: the body now delegates to
    trigobj_best_match(..., TRIGOBJ_MUON_ID, ...), which is the same
    formula with the object id as a parameter, so the muon and electron
    matchers can never drift apart. Behaviour, inputs and output are
    identical to before -- test_electron_datasets.py checks that directly,
    and so does electron_prep/common.assert_matcher_agrees_with_production.
    """
    return trigobj_best_match(sel_muons, trigobj, TRIGOBJ_MUON_ID, required_bit, dr_max)["best_pt"]


def matched_acceptance_mask(sel_muons: ak.Array, trigobj: ak.Array, required_bit: int,
                              min_matched: int, leading_pt_min_gev: float) -> np.ndarray:
    """Per-event boolean: at least `min_matched` distinct selected muons
    each matched (trigobj_best_match_pt) to a bit-`required_bit` TrigObj,
    AND the highest such matched online pT >= leading_pt_min_gev. This is
    the ACCEPTANCE test itself (does not check whether the event's own
    HLT path fired -- callers apply that separately, since within
    `events_triggered` the current dataset's own trigger has already been
    required, but a cross-dataset veto check needs its own explicit
    fired-mask)."""
    best_pts = trigobj_best_match_pt(sel_muons, trigobj, required_bit)
    matched_mask = best_pts > -np.inf
    matched_pts = best_pts[matched_mask]
    n_matched = ak.to_numpy(ak.num(matched_pts, axis=1))
    leading_matched_pt = ak.to_numpy(ak.fill_none(ak.max(matched_pts, axis=1), -np.inf))
    return (n_matched >= min_matched) & (leading_matched_pt >= leading_pt_min_gev)


# ---------------------------------------------------------------------------
# --population matched4 helpers (electron-datasets task, D2-D6). Every
# function below is NEW; nothing above it is modified except
# trigobj_best_match_pt, which now delegates to the id-parameterised
# matcher so the two can never drift apart (its behaviour, inputs and
# outputs are identical -- asserted by
# studies/cms_datasets/tests/test_electron_datasets.py and by
# electron_prep/common.assert_matcher_agrees_with_production).
# ---------------------------------------------------------------------------

def delta_r_wrapped(obj_a: ak.Array, obj_b: ak.Array) -> ak.Array:
    """Pairwise dR between two per-event collections, nested so the result
    is [event][a][b].

    dR = sqrt(dEta^2 + dPhi^2) with dPhi wrapped into [-pi, pi], written
    out explicitly because D3 specifies the overlap-removal metric that
    way. test_electron_datasets.py asserts it agrees with vector's own
    deltaR (which the trigger matching uses), so this is a second
    spelling of the same quantity, not a second definition."""
    a_eta, b_eta = ak.unzip(ak.cartesian([obj_a.eta, obj_b.eta], nested=True))
    a_phi, b_phi = ak.unzip(ak.cartesian([obj_a.phi, obj_b.phi], nested=True))
    d_eta = a_eta - b_eta
    d_phi = (a_phi - b_phi + np.pi) % (2.0 * np.pi) - np.pi
    return np.sqrt(d_eta ** 2 + d_phi ** 2)


def electrons_overlapping_muons_mask(electrons: ak.Array, muons: ak.Array,
                                     dr_max: float = EMU_OVERLAP_DR_MAX) -> ak.Array:
    """Per selected electron: is it within dR < dr_max of ANY selected
    muon? The one place the D3 overlap condition is evaluated."""
    dr = delta_r_wrapped(electrons, muons)                 # [event][ele][mu]
    return ak.fill_none(ak.any(dr < dr_max, axis=-1), False)


def remove_electrons_overlapping_muons(electrons: ak.Array, muons: ak.Array,
                                       dr_max: float = EMU_OVERLAP_DR_MAX,
                                       enabled: bool = True):
    """D3: drop every selected electron within dR < dr_max of ANY selected
    muon. Muons are never removed.

    Returns (electrons_kept, n_removed_per_event, removed_mask). With enabled=False
    nothing is removed and the input array is returned unchanged -- that
    switch exists for validation only (E1(b)); the default is ON.

    WHERE THIS SITS IN THE ORDER. It is applied after object selection
    (muons, electrons AND jets) and before trigger matching, before the
    Version B count and before final-state assignment, exactly as D3
    requires. Jets are therefore still lepton-cleaned against the electron
    list master cleans them against, so the jet collections are
    bit-for-bit what master produces and every difference this option
    makes traces to a removed electron. The alternative (clean jets
    against the post-removal electron list) would additionally change the
    jet collections, which this task's own out-of-scope list forbids
    ("object definitions ... do not change"). How many events the two
    orderings could possibly differ on is counted and reported --
    n_events_jet_cleaning_order_would_matter in the matched4
    diagnostics."""
    n_events = len(electrons)
    if not enabled:
        none_removed = ak.zeros_like(electrons.pt, dtype=bool)
        return electrons, np.zeros(n_events, dtype=np.int64), none_removed
    is_close = electrons_overlapping_muons_mask(electrons, muons, dr_max)
    n_removed = ak.to_numpy(ak.sum(is_close, axis=1)).astype(np.int64)
    return electrons[~is_close], n_removed, is_close


def count_events_where_jet_cleaning_order_would_matter(
        removed_electrons: ak.Array, muons: ak.Array, light_jets: ak.Array,
        bjets: ak.Array) -> int:
    """How many events the documented ordering choice in
    remove_electrons_overlapping_muons could possibly affect: events with a
    REMOVED electron that has a selected jet within the lepton-cleaning
    cone (selection.JET_LEPTON_CLEAN_DR) which is NOT within that cone of
    any selected muon. Only in such an event could cleaning jets against
    the post-removal electron list give a different jet collection.
    Diagnostic only -- changes nothing."""
    if len(removed_electrons) == 0:
        return 0
    jets_all = ak.concatenate([light_jets, bjets], axis=1)
    dr_mj = delta_r_wrapped(muons, jets_all)                    # [ev][mu][jet]
    near_any_mu = ak.fill_none(ak.any(dr_mj < selection.JET_LEPTON_CLEAN_DR, axis=1), False)
    # Drop the jets that are already inside a muon's cleaning cone FIRST, so
    # the remaining question is a plain [ev][rem_e][jet] reduction (awkward
    # cannot broadcast an [ev][jet] mask against an [ev][rem_e][jet] array).
    jets_far_from_muons = jets_all[~near_any_mu]
    dr_ej = delta_r_wrapped(removed_electrons, jets_far_from_muons)
    would_matter = ak.any(ak.any(dr_ej < selection.JET_LEPTON_CLEAN_DR, axis=-1), axis=-1)
    return int(ak.sum(ak.fill_none(would_matter, False)))


def trigobj_best_match(objs: ak.Array, trigobj: ak.Array, obj_id: int, required_bit: int,
                       dr_max: float = MATCH_DR_MAX) -> dict:
    """The id-parameterised trigger matcher, with per-object bookkeeping
    (D6). For each offline object (per event, jagged) it finds the TrigObj
    with the highest online pT among those with `id == obj_id`,
    `filterBits & required_bit != 0` and dR < dr_max.

    THE TRIGGER-OBJECT GUARD IS THIS id FILTER (D6): offline electrons can
    only ever match id==11 objects and offline muons only id==13 ones,
    because objects of any other id are removed before a single dR is
    computed. count_trigger_guard_violations re-checks that independently,
    from the recorded indices.

    Returns a dict of jagged arrays, all aligned to `objs`:
      best_pt           highest matched TrigObj_pt, -inf if unmatched
      best_dr           dR to that object, NaN if unmatched
      best_index        its index in the ORIGINAL TrigObj collection, -1 if unmatched
      best_id           its TrigObj_id, -1 if unmatched
      best_filterBits   its TrigObj_filterBits, 0 if unmatched
      is_matched        boolean
    `best_pt` is computed by exactly the formula trigobj_best_match_pt has
    always used, which is why that function now delegates here."""
    trig_index = ak.local_index(trigobj, axis=1)
    trig_mask = (trigobj.id == obj_id) & ((trigobj.filterBits & required_bit) != 0)
    trig_sel = trigobj[trig_mask]
    sel_index = trig_index[trig_mask]

    obj_p4 = _p4_no_mass_needed(objs)
    trig_p4 = _p4_no_mass_needed(trig_sel)
    pairs_obj, pairs_trig = ak.unzip(ak.cartesian([obj_p4, trig_p4], nested=True))
    dr = pairs_obj.deltaR(pairs_trig)
    within = dr < dr_max
    candidate_pt = ak.where(within, pairs_trig.pt, -np.inf)
    best_pt = ak.fill_none(ak.max(candidate_pt, axis=-1), -np.inf)
    is_matched = best_pt > -np.inf

    # Which pair won, and what it was: index into the ORIGINAL TrigObj list.
    _, pairs_idx = ak.unzip(ak.cartesian([objs.pt, sel_index], nested=True))
    _, pairs_bits = ak.unzip(ak.cartesian([objs.pt, trig_sel.filterBits], nested=True))
    _, pairs_id = ak.unzip(ak.cartesian([objs.pt, trig_sel.id], nested=True))
    best_slot = ak.argmax(candidate_pt, axis=-1, keepdims=True)
    best_index = ak.fill_none(ak.firsts(pairs_idx[best_slot], axis=-1), -1)
    best_bits = ak.fill_none(ak.firsts(pairs_bits[best_slot], axis=-1), 0)
    best_id = ak.fill_none(ak.firsts(pairs_id[best_slot], axis=-1), -1)
    best_dr = ak.fill_none(ak.firsts(dr[best_slot], axis=-1), np.nan)

    return {
        "best_pt": best_pt,
        "best_dr": ak.where(is_matched, best_dr, np.nan),
        "best_index": ak.where(is_matched, best_index, -1),
        "best_id": ak.where(is_matched, best_id, -1),
        "best_filterBits": ak.where(is_matched, best_bits, 0),
        "is_matched": is_matched,
    }


def count_trigger_guard_violations(bookkeeping: dict, trigobj: ak.Array, expected_id: int) -> int:
    """D6: count offline objects RECORDED as matched to a TrigObj whose id
    is not `expected_id`. Independent of trigobj_best_match's own id
    filter: it takes the recorded index, looks the id up again in the
    ORIGINAL TrigObj collection, and compares. Expected 0; a non-zero
    count means the bookkeeping and the matcher disagree."""
    is_matched = bookkeeping["is_matched"]
    idx = bookkeeping["best_index"]
    safe_idx = ak.where(is_matched, idx, 0)
    # pad_none guarantees a non-empty inner list so index 0 is always legal,
    # even in events with no TrigObj at all (where is_matched is all False).
    ids_padded = ak.fill_none(ak.pad_none(trigobj.id, 1, axis=1), -999)
    looked_up = ids_padded[safe_idx]
    violations = is_matched & (looked_up != expected_id)
    return int(ak.sum(violations))


def assert_trigobj_bit_meanings(branch_titles: dict) -> dict:
    """D6: read the TrigObj branch titles at RUNTIME and assert the bit
    meanings this acceptance depends on are the ones documented in
    ELECTRON_MATCHING_SPEC.md. Stops the job with a clear error on any
    mismatch, rather than silently matching the wrong HLT filter."""
    id_title = " ".join(str(branch_titles.get("TrigObj_id", "")).split())
    bits_title = " ".join(str(branch_titles.get("TrigObj_filterBits", "")).split())
    missing = []
    for needle in EXPECTED_TRIGOBJ_ID_TITLE_SUBSTRINGS:
        if needle not in id_title:
            missing.append(("TrigObj_id", needle))
    for needle in EXPECTED_TRIGOBJ_FILTERBITS_TITLE_SUBSTRINGS:
        if needle not in bits_title:
            missing.append(("TrigObj_filterBits", needle))
    if missing:
        raise RuntimeError(
            "STOP: TrigObj branch titles in this file do not carry the bit "
            "meanings this acceptance was derived from. Missing: "
            f"{missing}. TrigObj_id title={id_title!r}; "
            f"TrigObj_filterBits title={bits_title!r}. Refusing to match "
            "against filter bits whose meaning is not confirmed."
        )
    return {"trigobj_id_title": id_title,
            "trigobj_filterbits_title": bits_title,
            "checked_substrings": {
                "TrigObj_id": list(EXPECTED_TRIGOBJ_ID_TITLE_SUBSTRINGS),
                "TrigObj_filterBits": list(EXPECTED_TRIGOBJ_FILTERBITS_TITLE_SUBSTRINGS)},
            "all_present": True}


def fired_mask(events: ak.Array, paths) -> np.ndarray:
    """Event-level OR over a set of HLT path branches."""
    m = np.zeros(len(events), dtype=bool)
    for path in paths:
        m |= ak.to_numpy(events[path]).astype(bool)
    return m


def _max_over_matched(values: ak.Array, is_matched: ak.Array) -> np.ndarray:
    picked = values[is_matched]
    return ak.to_numpy(ak.fill_none(ak.max(picked, axis=1), -np.inf))


def doublemuon_acceptance(events: ak.Array, muons: ak.Array, trigobj: ak.Array) -> dict:
    """DoubleMuon acceptance: own paths fired AND the settled muon-side
    matching rule (matched_acceptance_mask, unchanged)."""
    fired = fired_mask(events, MATCHED4_TRIGGER_PATHS["DoubleMuon"])
    matched = matched_acceptance_mask(
        muons, trigobj, TRIGOBJ_BIT_TRKISOVVL,
        DOUBLEMUON_MATCHED_MIN_MUONS, DOUBLEMUON_MATCHED_LEADING_PT_MIN_GEV)
    return {"fired": fired, "matched": matched, "accepted": fired & matched,
            "cutflow": {"n_events_considered": int(len(fired)),
                        "n_fired": int(fired.sum()),
                        "n_matched": int(matched.sum()),
                        "n_accepted": int((fired & matched).sum())}}


def singlemuon_acceptance(events: ak.Array, muons: ak.Array, trigobj: ak.Array) -> dict:
    """SingleMuon acceptance: HLT_IsoMu24 fired AND the settled muon-side
    matching rule (matched_acceptance_mask, unchanged)."""
    fired = fired_mask(events, MATCHED4_TRIGGER_PATHS["SingleMuon"])
    matched = matched_acceptance_mask(
        muons, trigobj, TRIGOBJ_BIT_ISO,
        SINGLEMUON_MATCHED_MIN_MUONS, SINGLEMUON_MATCHED_PT_MIN_GEV)
    return {"fired": fired, "matched": matched, "accepted": fired & matched,
            "cutflow": {"n_events_considered": int(len(fired)),
                        "n_fired": int(fired.sum()),
                        "n_matched": int(matched.sum()),
                        "n_accepted": int((fired & matched).sum())}}


def doubleeg_acceptance(events: ak.Array, electrons: ak.Array, trigobj: ak.Array,
                        threshold_mode: str) -> dict:
    """D4: DoubleEG acceptance.

    (1) HLT_Ele23_Ele12_CaloIdL_TrackIdL_IsoVL_DZ fired, AND
    (2) >= 2 distinct selected electrons each matched (dR<0.1) to a
        TrigObj with id==11 and bit 16 ("2e") set, AND
    (3) the higher-pT matched trigger object has TrigObj_pt >= 23 GeV, AND
    (4) the NEW offline-pT requirement, per `threshold_mode`:
          "leading_only": the highest-OFFLINE-pT matched electron has
                          pT > 30 GeV (the other matched electron needs
                          only the normal >= 25 GeV object threshold);
          "both":         at least two matched electrons have offline
                          pT > 30 GeV.

    Two offline electrons MAY share one trigger object -- this mirrors the
    DoubleMuon code exactly (matched_acceptance_mask counts matched
    offline objects, never distinct trigger objects); how often that
    actually happens is counted and reported rather than assumed away.
    Unmatched electrons stay in the event with the normal object
    definition; nothing here changes any object definition."""
    if threshold_mode not in DOUBLEEG_THRESHOLD_MODES:
        raise ValueError(f"unknown doubleeg_threshold_mode {threshold_mode!r}; "
                         f"expected one of {DOUBLEEG_THRESHOLD_MODES}")
    fired = fired_mask(events, MATCHED4_TRIGGER_PATHS["DoubleEG"])
    bk = trigobj_best_match(electrons, trigobj, TRIGOBJ_ELECTRON_ID, TRIGOBJ_BIT_E_2E)
    is_matched = bk["is_matched"]
    n_matched = ak.to_numpy(ak.sum(is_matched, axis=1)).astype(np.int64)
    leading_online_pt = _max_over_matched(bk["best_pt"], is_matched)
    offline_pt_matched = electrons.pt[is_matched]
    leading_offline_pt = ak.to_numpy(
        ak.fill_none(ak.max(offline_pt_matched, axis=1), -np.inf))
    n_matched_above_offline_cut = ak.to_numpy(
        ak.sum(offline_pt_matched > DOUBLEEG_OFFLINE_PT_MIN_GEV, axis=1)).astype(np.int64)

    if threshold_mode == "leading_only":
        offline_ok = leading_offline_pt > DOUBLEEG_OFFLINE_PT_MIN_GEV
    else:
        offline_ok = n_matched_above_offline_cut >= DOUBLEEG_MATCHED_MIN_ELECTRONS

    enough_matched = n_matched >= DOUBLEEG_MATCHED_MIN_ELECTRONS
    online_ok = leading_online_pt >= DOUBLEEG_TRIGOBJ_LEADING_PT_MIN_GEV
    accepted = fired & enough_matched & online_ok & offline_ok

    return {
        "fired": fired,
        "matched": enough_matched & online_ok & offline_ok,
        "accepted": accepted,
        "bookkeeping": bk,
        "n_matched": n_matched,
        "leading_online_pt": leading_online_pt,
        "leading_offline_matched_pt": leading_offline_pt,
        "n_matched_above_offline_cut": n_matched_above_offline_cut,
        "pre_offline_cut_mask": fired & enough_matched & online_ok,
        "cutflow": {
            "n_events_considered": int(len(fired)),
            "n_fired": int(fired.sum()),
            "n_fired_and_ge1_matched": int((fired & (n_matched >= 1)).sum()),
            "n_fired_and_ge2_matched": int((fired & enough_matched).sum()),
            "n_fired_ge2_matched_online23": int((fired & enough_matched & online_ok).sum()),
            "n_accepted": int(accepted.sum()),
            "n_lost_to_offline_cut": int(((fired & enough_matched & online_ok) & ~offline_ok).sum()),
            "threshold_mode": threshold_mode,
            "offline_pt_min_gev": DOUBLEEG_OFFLINE_PT_MIN_GEV,
        },
    }


def doubleeg_interpretation_diagnostics(electrons: ak.Array, bk: dict,
                                        base_mask: np.ndarray) -> dict:
    """D4's two required counts, over the events selected by `base_mask`
    (the events that pass everything except the new offline-pT rule, so
    the counts do not depend on which mode is in force):

    (a) the interpretation check -- events where the LEADING MATCHED
        electron is not the LEADING SELECTED electron of the event.
        "Leading" means highest OFFLINE pT, found by an explicit argmax,
        NOT "index 0": VERIFIED BY RUNNING, the NanoAOD Electron
        collection is not always pT-descending (a small fraction of
        events; the count is reported below). The index-0 reading is
        reported alongside as `..._by_index0` so the two can be compared,
        and the number of events where the two readings could differ at
        all is the non-pT-descending count. Nothing in the acceptance
        depends on the collection order -- D4's own offline rule is a max
        / a count over the matched electrons -- and neither does the
        delivery, because the shared slice_events_by_field sorts each
        type by pT descending itself before slicing e0/e1.

    (b) the shared-trigger-object count -- events with >= 2 matched
        electrons whose recorded best TrigObj indices are not all
        distinct, i.e. two offline electrons matched to the SAME trigger
        object."""
    is_matched = bk["is_matched"]
    pt = electrons.pt
    n_matched = ak.to_numpy(ak.sum(is_matched, axis=1))

    # How often is the selected-electron collection not pT-descending?
    non_increasing = ak.all(ak.fill_none(pt[:, :-1] >= pt[:, 1:], True), axis=1)
    n_not_pt_ordered = int(len(pt) - int(ak.sum(ak.fill_none(non_increasing, True))))

    argmax_all = ak.to_numpy(ak.fill_none(ak.argmax(pt, axis=1), -1))
    matched_pt = ak.where(is_matched, pt, -np.inf)
    argmax_matched = ak.to_numpy(ak.fill_none(ak.argmax(matched_pt, axis=1), -1))
    first_is_matched = ak.to_numpy(ak.fill_none(ak.firsts(is_matched), False))

    has_any = n_matched >= 1
    differs = base_mask & has_any & (argmax_matched != argmax_all)
    differs_by_index0 = base_mask & has_any & (~first_is_matched)

    # Shared trigger object: two matched electrons recorded against the
    # same TrigObj index. Found by sorting each event's matched indices
    # and looking for an adjacent duplicate (no per-event Python objects).
    idx_sorted = ak.sort(bk["best_index"][is_matched], axis=1)
    has_duplicate = ak.to_numpy(ak.fill_none(
        ak.any(idx_sorted[:, :-1] == idx_sorted[:, 1:], axis=1), False)).astype(bool)
    shared = base_mask & (n_matched >= 2) & has_duplicate

    return {
        "n_events_in_base": int(base_mask.sum()),
        "n_selected_electron_collections_not_pt_descending": n_not_pt_ordered,
        "n_leading_matched_differs_from_leading_selected": int(differs.sum()),
        "n_leading_matched_differs_from_leading_selected_by_index0": int(
            differs_by_index0.sum()),
        "leading_definition": ("highest offline pT (explicit argmax); the "
                               "_by_index0 variant instead reads 'leading' as "
                               "collection index 0"),
        "n_events_two_electrons_share_one_trigobj": int(shared.sum()),
    }


def muoneg_acceptance(events: ak.Array, muons: ak.Array, electrons: ak.Array,
                      trigobj: ak.Array) -> dict:
    """D5: MuonEG acceptance.

    (1) HLT_Mu23_TrkIsoVVL_Ele12_..._DZ OR HLT_Mu8_TrkIsoVVL_Ele23_..._DZ
        fired, AND
    (2) >= 1 SELECTED offline muon (the muon leg cannot be trigger-matched
        in 2016 NanoAOD -- ELECTRON_MATCHING_SPEC.md section 4), AND
    (3) >= 1 selected electron matched (dR<0.1) to a TrigObj with id==11
        and bit 32 ("1e-1mu") whose matched TrigObj_pt clears the
        electron-leg threshold of a path that ACTUALLY FIRED: >= 12 GeV
        for Mu23_Ele12, >= 23 GeV for Mu8_Ele23. Either fired path's
        condition suffices, so swapped legs are accepted."""
    fired_a = fired_mask(events, [MUONEG_PATH_MU23_ELE12])
    fired_b = fired_mask(events, [MUONEG_PATH_MU8_ELE23])
    fired = fired_a | fired_b
    bk = trigobj_best_match(electrons, trigobj, TRIGOBJ_ELECTRON_ID, TRIGOBJ_BIT_E_1E1MU)
    is_matched = bk["is_matched"]
    n_matched = ak.to_numpy(ak.sum(is_matched, axis=1)).astype(np.int64)
    best_online_pt = _max_over_matched(bk["best_pt"], is_matched)
    has_muon = ak.to_numpy(ak.num(muons, axis=1) >= MUONEG_MIN_SELECTED_MUONS)

    leg_a_ok = fired_a & (best_online_pt
                          >= MUONEG_ELECTRON_LEG_PT_MIN_GEV_BY_PATH[MUONEG_PATH_MU23_ELE12])
    leg_b_ok = fired_b & (best_online_pt
                          >= MUONEG_ELECTRON_LEG_PT_MIN_GEV_BY_PATH[MUONEG_PATH_MU8_ELE23])
    electron_leg_ok = leg_a_ok | leg_b_ok
    accepted = fired & has_muon & electron_leg_ok

    return {
        "fired": fired,
        "matched": has_muon & electron_leg_ok,
        "accepted": accepted,
        "bookkeeping": bk,
        "n_matched": n_matched,
        "best_online_pt": best_online_pt,
        "cutflow": {
            "n_events_considered": int(len(fired)),
            "n_fired": int(fired.sum()),
            "n_fired_mu23_ele12": int(fired_a.sum()),
            "n_fired_mu8_ele23": int(fired_b.sum()),
            "n_fired_both_paths": int((fired_a & fired_b).sum()),
            "n_fired_and_ge1_selected_muon": int((fired & has_muon).sum()),
            "n_fired_muon_and_ge1_matched_electron": int(
                (fired & has_muon & (n_matched >= 1)).sum()),
            "n_accepted": int(accepted.sum()),
            "n_accepted_via_mu23_ele12_leg": int((fired & has_muon & leg_a_ok).sum()),
            "n_accepted_via_mu8_ele23_leg": int((fired & has_muon & leg_b_ok).sum()),
            "n_matched_electron_fails_fired_path_leg_threshold": int(
                (fired & has_muon & (n_matched >= 1) & ~electron_leg_ok).sum()),
        },
    }


def evaluate_four_acceptances(events: ak.Array, muons: ak.Array, electrons: ak.Array,
                              trigobj: ak.Array, doubleeg_threshold_mode: str) -> dict:
    """D2: the acceptance of each of the four datasets, evaluated on the
    SAME events with the SAME functions and the SAME post-overlap-removal
    objects. `electrons` must already have had the D3 overlap removal
    applied (or deliberately not, for validation).

    An event belongs to dataset D's EXCLUSIVE set iff it passes D's
    acceptance and fails the acceptance of every dataset above it in
    DELIVERY_VETO_ORDER_4."""
    out = {
        "DoubleMuon": doublemuon_acceptance(events, muons, trigobj),
        "SingleMuon": singlemuon_acceptance(events, muons, trigobj),
        "DoubleEG": doubleeg_acceptance(events, electrons, trigobj, doubleeg_threshold_mode),
        "MuonEG": muoneg_acceptance(events, muons, electrons, trigobj),
    }
    assert list(out.keys()) == DELIVERY_VETO_ORDER_4, (
        "acceptance dict order must be DELIVERY_VETO_ORDER_4")
    return out


def ele27_candidate_acceptance(events: ak.Array, electrons: ak.Array,
                               trigobj: ak.Array) -> dict:
    """D2: the SingleElectron CANDIDATE condition, for --is-mc only.

    (1) HLT_Ele27_WPTight_Gsf fired, AND
    (2) >= 1 selected electron -- AFTER the dR < 0.12 overlap removal, i.e.
        the same `electrons` the four data acceptances are evaluated on --
        matched (dR < 0.1) to a TrigObj with id == 11 and bit 2
        ("1e (WPTight)") set, AND
    (3) that matched trigger object has TrigObj_pt >= 27 GeV (online).

    NO offline pT requirement is applied: the offline threshold (27/30/35) is
    undecided and explicitly out of scope. Instead the leading matched
    electron's OFFLINE pT is returned per event (-1 when nothing matched), so
    whichever threshold is chosen later is a re-read of the shards rather than
    a new MC production.

    Built with exactly the same matcher (`trigobj_best_match`) and the same id
    guard the four delivered acceptances use, so the candidate can never drift
    from them. Nothing here is used to accept an event for the current
    delivery -- the builder uses the four data flags only."""
    fired = fired_mask(events, (ELE27_PATH,))
    bk = trigobj_best_match(electrons, trigobj, TRIGOBJ_ELECTRON_ID,
                            TRIGOBJ_BIT_E_1E_WPTIGHT)
    is_matched = bk["is_matched"]
    n_matched = ak.to_numpy(ak.sum(is_matched, axis=1)).astype(np.int64)
    leading_online_pt = _max_over_matched(bk["best_pt"], is_matched)

    # Leading OFFLINE pT over the matched electrons; the sentinel keeps the
    # array float and unambiguous (a real electron always has pt > 0).
    offline_pt_matched = electrons.pt[is_matched]
    leading_offline_pt = ak.to_numpy(
        ak.fill_none(ak.max(offline_pt_matched, axis=1), ELE27_NO_MATCH_SENTINEL)
    ).astype(np.float64)
    leading_offline_pt = np.where(
        n_matched > 0, leading_offline_pt, ELE27_NO_MATCH_SENTINEL)

    enough_matched = n_matched >= ELE27_MIN_MATCHED_ELECTRONS
    online_ok = leading_online_pt >= ELE27_TRIGOBJ_PT_MIN_GEV
    accepted = fired & enough_matched & online_ok

    return {
        "fired": fired,
        "matched": enough_matched & online_ok,
        "accepted": accepted,
        "bookkeeping": bk,
        "n_matched": n_matched,
        "leading_online_pt": leading_online_pt,
        "leading_offline_matched_pt": leading_offline_pt,
        "cutflow": {
            "n_events_considered": int(len(fired)),
            "n_fired": int(fired.sum()),
            "n_fired_and_ge1_matched": int((fired & enough_matched).sum()),
            "n_accepted": int(accepted.sum()),
            "trigobj_pt_min_gev": ELE27_TRIGOBJ_PT_MIN_GEV,
            "offline_pt_cut_applied": False,
            "path": ELE27_PATH,
        },
    }


def assert_trigobj_bit_meanings_mc(branch_titles: dict) -> dict:
    """--is-mc only: additionally assert the electron bit-2 meaning the Ele27
    candidate depends on, from the file's own TrigObj_filterBits title.

    Separate from assert_trigobj_bit_meanings so the data path's own
    assertion is untouched. Verified by running (DESIGN.md C3): the
    filterBits title is byte-identical in MC and in all eight data files, so
    this check is expected to pass -- it exists to stop the job if a future
    sample's title differs."""
    bits_title = " ".join(str(branch_titles.get("TrigObj_filterBits", "")).split())
    missing = [n for n in EXPECTED_TRIGOBJ_FILTERBITS_TITLE_SUBSTRINGS_MC
               if n not in bits_title]
    if missing:
        raise RuntimeError(
            "STOP: TrigObj_filterBits title in this MC file does not carry the "
            f"bit meaning(s) the Ele27 candidate needs: {missing}. "
            f"title={bits_title!r}. Refusing to match against a filter bit "
            "whose meaning is not confirmed."
        )
    return {"checked_substrings_mc": list(EXPECTED_TRIGOBJ_FILTERBITS_TITLE_SUBSTRINGS_MC),
            "all_present": True}


def read_runs_tree_totals(file_url: str) -> dict:
    """D4: this file's own Runs-tree totals -- `genEventSumw` (the sum of
    `genWeight` over every generated event of the file) and `genEventCount`.

    The MC normalisation denominator is the sum of genEventSumw over exactly
    the files that processed successfully, so every job records its own
    contribution here rather than leaving the builder to re-open the file.
    Verified by running (DESIGN.md C5): on all 13 probed records the Runs
    total equals sum(genWeight) to <= 4.4e-8 relative, i.e. no pre-skim."""
    with uproot.open(file_url) as f:
        if "Runs" not in {k.split(";")[0] for k in f.keys()}:
            raise RuntimeError(
                f"STOP: {file_url} has no Runs tree, so its sum of generator "
                "weights cannot be established. Refusing to write a shard that "
                "cannot be normalised.")
        runs = f["Runs"]
        keys = set(runs.keys())
        for needed in ("genEventSumw", "genEventCount"):
            if needed not in keys:
                raise RuntimeError(
                    f"STOP: {file_url}'s Runs tree has no {needed!r} branch.")
        sumw = np.asarray(runs["genEventSumw"].array(library="np"), dtype=np.float64)
        count = np.asarray(runs["genEventCount"].array(library="np"))
    return {
        "gen_event_sumw": float(sumw.sum()),
        "gen_event_count": int(count.sum()),
        "n_runs_entries": int(sumw.size),
    }


def mc_sigma_w_self_check(file_sum_genweight: float, runs_gen_event_sumw: float,
                          n_events_read: int, runs_gen_event_count: int,
                          tolerance: float = 1e-6) -> dict:
    """D4: the pre-skim detector, evaluated per file.

    A skimmed file has fewer events than its Runs `genEventCount` and a
    smaller weight sum than its `genEventSumw`, so normalising with that
    `genEventSumw` would inflate the denominator and under-normalise the whole
    sample. Reported here and re-checked by the builder, which EXCLUDES a
    failing file together with its Sigma-w."""
    rel = (abs(file_sum_genweight - runs_gen_event_sumw) / abs(runs_gen_event_sumw)
           if runs_gen_event_sumw else None)
    return {
        "file_sum_genweight": file_sum_genweight,
        "runs_gen_event_sumw": runs_gen_event_sumw,
        "relative_difference": rel,
        "tolerance": tolerance,
        "passes": bool(rel is not None and rel <= tolerance),
        "n_events_read": int(n_events_read),
        "runs_gen_event_count": int(runs_gen_event_count),
        "event_count_matches": bool(int(n_events_read) == int(runs_gen_event_count)),
    }


def build_mc_event_info(events: ak.Array, record_id: int) -> ak.Array:
    """D3: the per-event `_mcEventInfo` record, mirroring PR #35's shape.

    `_mcEventWeight` = genWeight; `_mcChannelNumber` = the CERN Open Data
    RECORD ID handed to this job via --record-id (never parsed from a file
    name -- and CMS NanoAOD carries no per-event dataset identifier at all,
    verified in DESIGN.md D3); `_mcRunNumber` = the file's own `run`, which is
    1 in every CMS MC sample and therefore carries no campaign information.

    This record is the canonical in-memory form and is what a port to PR #35
    would hand to its own weight code. The driver additionally derives the
    aligned flat arrays written as shard siblings (mc_sibling_arrays below)
    from the SAME source branches, so the two can never disagree."""
    n = len(events)
    return ak.zip({
        MC_EVENT_WEIGHT_FIELD: ak.values_astype(events.genWeight, np.float64),
        MC_CHANNEL_NUMBER_FIELD: ak.Array(np.full(n, int(record_id), dtype=np.int64)),
        MC_RUN_NUMBER_FIELD: ak.values_astype(events.run, np.int64),
    })


def mc_acceptance_bitmask(acceptances: dict, ele27: dict) -> np.ndarray:
    """D3: one integer per event, one bit per stored condition.

    Bits 0-3 are the four delivered data acceptances in DELIVERY_VETO_ORDER_4
    order; bit 4 is the SingleElectron candidate (fired AND matched online);
    bit 5 is the bare Ele27 fire decision, so an un-matched fire is
    distinguishable from no fire at all."""
    n = len(ele27["fired"])
    mask = np.zeros(n, dtype=MC_ACC_BITMASK_DTYPE)
    for label in DELIVERY_VETO_ORDER_4:
        mask |= np.where(acceptances[label]["accepted"],
                         MC_ACC_BIT_BY_LABEL[label], 0).astype(MC_ACC_BITMASK_DTYPE)
    mask |= np.where(ele27["accepted"],
                     MC_ACC_BIT_ELE27_CANDIDATE, 0).astype(MC_ACC_BITMASK_DTYPE)
    mask |= np.where(ele27["fired"],
                     MC_ACC_BIT_ELE27_FIRED, 0).astype(MC_ACC_BITMASK_DTYPE)
    return mask


def mc_store_mask(acceptances: dict, ele27: dict) -> np.ndarray:
    """D2: an MC event is STORED if ANY of the four data acceptances passes OR
    the SingleElectron candidate condition does. No de-duplication: a
    simulated event exists once, so there is nothing to de-duplicate, and the
    four-stream veto order has no meaning here."""
    keep = np.zeros(len(ele27["accepted"]), dtype=bool)
    for label in DELIVERY_VETO_ORDER_4:
        keep |= acceptances[label]["accepted"]
    keep |= ele27["accepted"]
    return keep


def mc_sibling_arrays(events: ak.Array, mc_event_info: ak.Array,
                      acceptances: dict, ele27: dict) -> dict:
    """D3: the per-event sibling arrays, as {suffix: numpy array}.

    One entry per event of `events`, in `events`' own row order, so the caller
    can push them through the identical masks the masses go through. Read from
    the file's own branches; `genWeight` comes via `mc_event_info` so the
    shard siblings and the PR #35-shaped record are the same numbers."""
    return {
        MC_SIBLING_GENWEIGHT: np.asarray(
            ak.to_numpy(mc_event_info[MC_EVENT_WEIGHT_FIELD]), dtype=np.float64),
        MC_SIBLING_L1PREFIRE: np.asarray(
            ak.to_numpy(events.L1PreFiringWeight_Nom), dtype=np.float32),
        MC_SIBLING_PILEUP: np.asarray(
            ak.to_numpy(events.Pileup_nTrueInt), dtype=np.float32),
        MC_SIBLING_ACCEPTANCE: mc_acceptance_bitmask(acceptances, ele27),
        MC_SIBLING_ELE27_PT: np.asarray(
            ele27["leading_offline_matched_pt"], dtype=np.float32),
    }


def mask_mc_siblings(siblings: dict, mask) -> dict:
    """Apply one mask (or index array) to every sibling at once, so no caller
    can mask some siblings and forget another."""
    return {suffix: arr[mask] for suffix, arr in siblings.items()}


def exclusive_mask_from_acceptances(acceptances: dict, dataset_label: str):
    """The exclusive mask for `dataset_label`: NOT accepted by any
    higher-priority dataset in DELIVERY_VETO_ORDER_4. Returned aligned to
    the event array the acceptances were computed on, together with the
    per-higher-dataset overlap counts."""
    higher = DELIVERY_VETO_ORDER_4[:DELIVERY_VETO_ORDER_4.index(dataset_label)]
    own = acceptances[dataset_label]["accepted"]
    vetoed_any = np.zeros(own.shape, dtype=bool)
    per_higher = {}
    for h in higher:
        h_acc = acceptances[h]["accepted"]
        per_higher[h] = int((own & h_acc).sum())
        vetoed_any |= h_acc
    return ~vetoed_any, per_higher, higher


def attribute_to_exclusive_dataset(acceptances: dict) -> np.ndarray:
    """For each event, the label of the HIGHEST-priority dataset whose
    acceptance it passes, or "" if none does. The single source of truth
    for the closure test's "exactly one exclusive set" check."""
    n = len(acceptances[DELIVERY_VETO_ORDER_4[0]]["accepted"])
    out = np.full(n, "", dtype=object)
    for label in reversed(DELIVERY_VETO_ORDER_4):
        out = np.where(acceptances[label]["accepted"], label, out)
    return out


def emu_pair_mass_values(electrons: ak.Array, muons: ak.Array) -> np.ndarray:
    """Invariant mass of every selected (electron, muon) pair, flattened.
    Diagnostic only (E5's overlap-removal plot)."""
    if len(electrons) == 0:
        return np.zeros(0, dtype=np.float64)
    import vector
    vector.register_awkward()
    e_p4 = vector.zip({"pt": electrons.pt, "eta": electrons.eta,
                       "phi": electrons.phi, "mass": electrons.mass})
    m_p4 = vector.zip({"pt": muons.pt, "eta": muons.eta,
                       "phi": muons.phi, "mass": muons.mass})
    pe, pm = ak.unzip(ak.cartesian([e_p4, m_p4]))
    flat = ak.flatten((pe + pm).mass, axis=None)
    if len(flat) == 0:
        return np.zeros(0, dtype=np.float64)
    return ak.to_numpy(flat).astype(np.float64)


def ee_pair_mass_by_region(electrons: ak.Array) -> dict:
    """m(e,e) for every selected electron pair, split barrel-barrel vs
    other, using ECAL_BARREL_ABS_ETA_MAX on the SAME eta variable the
    electron selection cuts on. Diagnostic only (E5's Z-peak plot)."""
    empty = {"barrel_barrel": np.zeros(0), "other": np.zeros(0)}
    if len(electrons) == 0:
        return empty
    import vector
    vector.register_awkward()
    p4 = vector.zip({"pt": electrons.pt, "eta": electrons.eta,
                     "phi": electrons.phi, "mass": electrons.mass})
    is_barrel = abs(electrons.eta) < ECAL_BARREL_ABS_ETA_MAX
    a, b = ak.unzip(ak.combinations(p4, 2))
    ba, bb = ak.unzip(ak.combinations(is_barrel, 2))
    flat = ak.flatten((a + b).mass, axis=None)
    if len(flat) == 0:
        return empty
    mass = ak.to_numpy(flat).astype(np.float64)
    both_barrel = ak.to_numpy(ak.flatten(ba & bb, axis=None)).astype(bool)
    return {"barrel_barrel": mass[both_barrel], "other": mass[~both_barrel]}


def _light_jet_multiplicity(light_jets: ak.Array) -> dict:
    """{multiplicity: n_events} for the accepted events (E5 plot input)."""
    from collections import Counter as _C
    counts = ak.to_numpy(ak.num(light_jets, axis=1)).tolist()
    return {str(k): int(v) for k, v in sorted(_C(counts).items())}


def matching_bookkeeping_summary(bk: dict, label: str) -> dict:
    """D6: per-object match bookkeeping, summarised. Keeps the full
    per-object record out of the metadata (it would be enormous) while
    reporting everything the task asks to see: how many offline objects
    were matched, the distribution of matched TrigObj ids and filterBits,
    and the dR distribution of the accepted matches."""
    from collections import Counter as _C
    is_matched = bk["is_matched"]
    n_objs = int(ak.sum(ak.num(is_matched, axis=1)))
    n_matched = int(ak.sum(is_matched))
    if n_matched:
        dr = ak.to_numpy(ak.flatten(bk["best_dr"][is_matched], axis=None)).astype(float)
        ids = ak.to_numpy(ak.flatten(bk["best_id"][is_matched], axis=None))
        bits = ak.to_numpy(ak.flatten(bk["best_filterBits"][is_matched], axis=None))
    else:
        dr = np.zeros(0)
        ids = np.zeros(0, dtype=np.int64)
        bits = np.zeros(0, dtype=np.int64)
    return {
        "which": label,
        "n_offline_objects": n_objs,
        "n_matched": n_matched,
        "matched_trigobj_id_counts": {str(k): int(v) for k, v in sorted(_C(ids.tolist()).items())},
        "matched_trigobj_filterbits_counts": {
            str(k): int(v) for k, v in sorted(_C(bits.tolist()).items())},
        "matched_dr_histogram": (_histogram_with_overflow(dr, DIAGNOSTIC_DR_EMU_BIN_EDGES)
                                 if dr.size else None),
        "matched_dr_max": float(dr.max()) if dr.size else None,
    }


def exact_final_state_labels(obj_record: ak.Array) -> np.ndarray:
    """One EXACT final-state label per event, in upstream's name format.

    Extracted verbatim from _group_by_final_state_with_mask (which now
    calls it) so the per-event label used by the matched4 debug dump can
    never drift from the label the shards are grouped by. See that
    function's docstring for the full rationale; the construction is
    upstream's own, from services/calculations/im_calculator.py and
    services/calculations/physics_calcs.py at upstream commit 88d7a4b."""
    num_events = len(obj_record)
    zero_array = ak.Array([0] * num_events) if num_events > 0 else ak.Array([])
    particle_counts = ak.num(obj_record)
    present_types = [
        (name, letter, ak.to_numpy(getattr(particle_counts, name, zero_array)))
        for name, letter in FINAL_STATE_OBJECTS
        if name in obj_record.fields
    ]
    return np.array([
        "_".join(
            f"{count}{letter}"
            for (_name, letter, _values), count in zip(present_types, counts)
        )
        for counts in zip(*[values for _name, _letter, values in present_types])
    ])


def compute_matching_diagnostics(muons: ak.Array, trigobj: ak.Array, required_bit: int,
                                    min_matched: int, leading_pt_min_gev: float) -> dict:
    """Step 2 diagnostics for --population matched (diagnostics-only --
    does not feed `keep`/gating/shards). `muons`/`trigobj` come from
    events_triggered, i.e. this dataset's own trigger has ALREADY been
    required -- so 'trigger fired' is automatically true throughout this
    population (see TRIGGER_MATCHING_SPEC.md), and the efficiency
    denominator here is simply 'has the offline muons the trigger
    requires' (n_has_required_offline_muons). Numerator is
    matched_acceptance_mask's own accepted-event mask. Both are also
    histogrammed vs. leading/subleading selected-muon pT and |eta| (1 GeV
    / 0.1-wide bins) so a later report can plot numerator/denominator ==
    matching efficiency in each bin (Step 3d)."""
    has_required_muons = ak.to_numpy(ak.num(muons, axis=1) >= min_matched)
    accepted = matched_acceptance_mask(muons, trigobj, required_bit, min_matched, leading_pt_min_gev)

    mu_order = ak.argsort(muons.pt, axis=1, ascending=False)
    sorted_mu = muons[mu_order]
    padded_mu = ak.pad_none(sorted_mu, 2, axis=1, clip=True)
    leading_pt = ak.to_numpy(ak.fill_none(padded_mu[:, 0].pt, np.nan))
    subleading_pt = ak.to_numpy(ak.fill_none(padded_mu[:, 1].pt, np.nan))
    leading_abseta = ak.to_numpy(ak.fill_none(abs(padded_mu[:, 0].eta), np.nan))
    subleading_abseta = ak.to_numpy(ak.fill_none(abs(padded_mu[:, 1].eta), np.nan))

    def _num_and_den(values, edges):
        return {
            "numerator_accepted": _histogram_1gev(values[accepted], edges),
            "denominator_has_required_muons": _histogram_1gev(values[has_required_muons], edges),
        }

    return {
        "n_trigger_fired": int(len(muons)),
        "n_has_required_offline_muons": int(has_required_muons.sum()),
        "n_accepted": int(accepted.sum()),
        "leading_muon_pt": _num_and_den(leading_pt, MATCHED_EFF_PT_BIN_EDGES),
        "subleading_muon_pt": _num_and_den(subleading_pt, MATCHED_EFF_PT_BIN_EDGES),
        "leading_muon_abseta": _num_and_den(leading_abseta, MATCHED_EFF_ETA_BIN_EDGES),
        "subleading_muon_abseta": _num_and_den(subleading_abseta, MATCHED_EFF_ETA_BIN_EDGES),
    }


def compute_diagnostics(muons: ak.Array, electrons: ak.Array, bjets: ak.Array) -> dict:
    """Step 2 diagnostics (task spec), computed over the INCLUSIVE
    population (all events passing this dataset's own trigger + object
    selection, before the population gate -- 'inclusive population' as
    named in the task brief): leading/subleading muon and electron pT
    (1 GeV bins, 0-200 GeV); every selected electron's eta (0.02-wide
    bins, documentation of the ECAL gap region only); opposite-sign
    dimuon mass and dR for pairs with m<5 GeV; raw (pre-post-processing)
    dilepton masses m(mu0,mu1), m(e0,e1), m(e0,mu0) (1 GeV bins,
    0-200 GeV). Diagnostic only -- does not affect selection, gating, or
    the written shards.

    Added subleading_electron_pt and all_selected_electron_eta for the
    DoubleEG delivery's Step 4 report (leading/subleading electron pT
    plot; electron eta / ECAL-gap-fraction plot) -- neither existed when
    DoubleMuon was run. This is a diagnostics-only addition (no selection,
    gating, combination, or shard-writing code touched); every DoubleEG
    job runs this same commit.

    MuonEG task, Step 1 addition (again diagnostics-only -- `bjets` is
    only read via `ak.num`, never used to filter, select, or write
    anything): for events with >=1 selected electron AND >=1 selected
    muon -- dR(e0,mu0) and the per-event minimum dR over every selected
    electron-muon pair (0-1.0, 0.01 bins, explicit overflow count);
    m(e0,mu0) (0-5 GeV, 0.05 GeV bins); the e0*mu0 charge-product sign
    (opposite vs. same); and the number of selected b-jets per event
    (0/1/2/3/>=4). `electrons` may optionally carry a passthrough
    'charge' field (added by the caller via ak.with_field, exactly as
    already done for muons) -- if absent, the charge-product diagnostic
    is skipped rather than guessed. Measures the known
    no-electron-muon-overlap-removal gap; adds no overlap removal
    anywhere."""
    mu_order = ak.argsort(muons.pt, axis=1, ascending=False)
    sorted_mu = muons[mu_order]
    padded_mu = ak.pad_none(sorted_mu, 2, axis=1, clip=True)
    mu0, mu1 = padded_mu[:, 0], padded_mu[:, 1]

    e_order = ak.argsort(electrons.pt, axis=1, ascending=False)
    sorted_e = electrons[e_order]
    padded_e = ak.pad_none(sorted_e, 2, axis=1, clip=True)
    e0, e1 = padded_e[:, 0], padded_e[:, 1]

    leading_mu_pt = ak.to_numpy(ak.fill_none(padded_mu[:, 0].pt, np.nan))
    subleading_mu_pt = ak.to_numpy(ak.fill_none(padded_mu[:, 1].pt, np.nan))
    leading_e_pt = ak.to_numpy(ak.fill_none(padded_e[:, 0].pt, np.nan))
    subleading_e_pt = ak.to_numpy(ak.fill_none(padded_e[:, 1].pt, np.nan))
    # Every selected electron's eta, across the whole inclusive population
    # (not just leading/subleading) -- documentation of where selected
    # electrons actually land relative to the ECAL gap, not a per-event
    # leading/subleading quantity.
    all_selected_electron_eta = ak.to_numpy(ak.flatten(electrons.eta, axis=None))

    def _p4(obj):
        import vector
        vector.register_awkward()
        return vector.zip({"pt": obj.pt, "eta": obj.eta, "phi": obj.phi, "mass": obj.mass})

    m_mumu = ak.to_numpy(ak.fill_none((_p4(mu0) + _p4(mu1)).mass, np.nan))
    m_ee = ak.to_numpy(ak.fill_none((_p4(e0) + _p4(e1)).mass, np.nan))
    m_emu = ak.to_numpy(ak.fill_none((_p4(e0) + _p4(mu0)).mass, np.nan))

    has_2mu = ak.to_numpy(ak.num(muons) >= 2)
    charge0 = ak.to_numpy(ak.fill_none(mu0.charge, 0)) if "charge" in muons.fields else None
    charge1 = ak.to_numpy(ak.fill_none(mu1.charge, 0)) if "charge" in muons.fields else None
    dr_mumu = ak.to_numpy(ak.fill_none(_p4(mu0).deltaR(_p4(mu1)), np.nan))

    low_mass_mask = has_2mu & (m_mumu < LOW_MASS_DIMUON_CUTOFF_GEV) & ~np.isnan(m_mumu)
    if charge0 is not None and charge1 is not None:
        opp_sign_mask = low_mass_mask & ((charge0 * charge1) < 0)
    else:
        opp_sign_mask = np.zeros_like(low_mass_mask)

    # ---- MuonEG task, Step 1: electron-muon overlap diagnostics ----
    has_1e1mu = ak.to_numpy((ak.num(electrons) >= 1) & (ak.num(muons) >= 1))
    # Leading muon/electron pT restricted to events with >=1 of each --
    # added after the MuonEG task's own full run had already started under
    # a pinned commit (Hard Rule 6), so it is NOT present in MuonEG's own
    # diagnostics; included here for the next dataset that needs it.
    leading_mu_pt_emu = np.where(has_1e1mu, leading_mu_pt, np.nan)
    leading_e_pt_emu = np.where(has_1e1mu, leading_e_pt, np.nan)

    dr_e0mu0 = ak.to_numpy(ak.fill_none(_p4(e0).deltaR(_p4(mu0)), np.nan))
    dr_e0mu0_masked = np.where(has_1e1mu, dr_e0mu0, np.nan)

    # Per-event minimum dR over EVERY selected electron-muon pair (not
    # just leading), via a flat (non-nested) per-event cartesian product.
    electrons_p4_all = _p4(electrons)
    muons_p4_all = _p4(muons)
    pairs_e, pairs_mu = ak.unzip(ak.cartesian([electrons_p4_all, muons_p4_all]))
    dr_all_pairs = pairs_e.deltaR(pairs_mu)
    min_dr_emu = ak.to_numpy(ak.fill_none(ak.min(dr_all_pairs, axis=1), np.nan))
    min_dr_emu_masked = np.where(has_1e1mu, min_dr_emu, np.nan)

    m_emu_masked = np.where(has_1e1mu, m_emu, np.nan)

    e_charge0 = ak.to_numpy(ak.fill_none(e0.charge, 0)) if "charge" in electrons.fields else None
    if e_charge0 is not None and charge0 is not None:
        emu_charge_product = np.where(has_1e1mu, e_charge0 * charge0, 0)
        n_opposite_sign_emu = int(((emu_charge_product < 0) & has_1e1mu).sum())
        n_same_sign_emu = int(((emu_charge_product > 0) & has_1e1mu).sum())
    else:
        n_opposite_sign_emu = None
        n_same_sign_emu = None

    n_bjets_per_event = ak.to_numpy(ak.num(bjets))
    n_bjets_emu = n_bjets_per_event[has_1e1mu]
    bjet_multiplicity_emu = {
        "0": int((n_bjets_emu == 0).sum()),
        "1": int((n_bjets_emu == 1).sum()),
        "2": int((n_bjets_emu == 2).sum()),
        "3": int((n_bjets_emu == 3).sum()),
        ">=4": int((n_bjets_emu >= 4).sum()),
    }

    return {
        "leading_muon_pt": _histogram_1gev(leading_mu_pt, DIAGNOSTIC_PT_BIN_EDGES),
        "subleading_muon_pt": _histogram_1gev(subleading_mu_pt, DIAGNOSTIC_PT_BIN_EDGES),
        "leading_electron_pt": _histogram_1gev(leading_e_pt, DIAGNOSTIC_PT_BIN_EDGES),
        "subleading_electron_pt": _histogram_1gev(subleading_e_pt, DIAGNOSTIC_PT_BIN_EDGES),
        "all_selected_electron_eta": _histogram_1gev(all_selected_electron_eta, DIAGNOSTIC_ETA_BIN_EDGES),
        "raw_dimuon_mass_mu0mu1": _histogram_1gev(m_mumu, DIAGNOSTIC_MASS_BIN_EDGES),
        "raw_dimuon_mass_mu0mu1_lowmass_finebins": _histogram_1gev(m_mumu, DIAGNOSTIC_LOWMASS_FINE_BIN_EDGES),
        "raw_dielectron_mass_e0e1": _histogram_1gev(m_ee, DIAGNOSTIC_MASS_BIN_EDGES),
        "raw_emu_mass_e0mu0": _histogram_1gev(m_emu, DIAGNOSTIC_MASS_BIN_EDGES),
        "low_mass_opposite_sign_dimuon": {
            "n_pairs": int(opp_sign_mask.sum()),
            "mass_gev": m_mumu[opp_sign_mask].tolist(),
            "dr": dr_mumu[opp_sign_mask].tolist(),
        },
        "n_events_ge2_selected_muons": int(has_2mu.sum()),
        "muon_charge_field_present": charge0 is not None,
        "electron_charge_field_present": e_charge0 is not None,
        "n_events_ge1e_ge1mu": int(has_1e1mu.sum()),
        "dr_e0_mu0": _histogram_with_overflow(dr_e0mu0_masked, DIAGNOSTIC_DR_EMU_BIN_EDGES),
        "min_dr_any_e_any_mu": _histogram_with_overflow(min_dr_emu_masked, DIAGNOSTIC_DR_EMU_BIN_EDGES),
        "emu_lowmass_m_e0mu0": _histogram_1gev(m_emu_masked, DIAGNOSTIC_EMU_LOWMASS_BIN_EDGES),
        "emu_charge_product": {
            "n_opposite_sign": n_opposite_sign_emu,
            "n_same_sign": n_same_sign_emu,
        },
        "emu_bjet_multiplicity": bjet_multiplicity_emu,
        "leading_muon_pt_emu_events": _histogram_1gev(leading_mu_pt_emu, DIAGNOSTIC_PT_BIN_EDGES),
        "leading_electron_pt_emu_events": _histogram_1gev(leading_e_pt_emu, DIAGNOSTIC_PT_BIN_EDGES),
    }


def run_combination_funnel(obj_record: ak.Array, is_exclusive_selected: np.ndarray, job_tag: str,
                             all_combinations: list, im_config: dict, logger,
                             writer_incl: SqliteArrayShardWriter, writer_excl: SqliteArrayShardWriter,
                             mc_siblings: dict | None = None) -> dict:
    """The exact combination/shard-writing funnel that used to be main()'s
    own inline for-loop, extracted verbatim (top-4 task, Step 1) so it can
    be called a SECOND time on a top-4-truncated obj_record without
    duplicating ~90 lines of code. Called with the UNCHANGED obj_record
    (generic/v0/matched-normal), this produces byte-for-byte the same
    shards and stats as before the refactor (Hard Rule 5) -- nothing about
    the logic below differs from the pre-refactor inline version.

    `mc_siblings` (cms-mc-weights-v3, DESIGN.md D3) is None for every data
    call -- which is every pre-existing caller -- and then every statement
    guarded by it is skipped and the data output is exactly what it was. Under
    --is-mc it is {suffix: per-event numpy array}, aligned to `obj_record`'s
    OWN row order, and each array is pushed through the IDENTICAL masks the
    masses go through, in the same order
    (group_mask -> combo_row_mask -> nan_mask -> coverage-cap pick) and
    written in the same flush.

    This funnel is deliberately SHARED with the data path rather than
    duplicated for MC: DESIGN.md D1 requires MC to use the identical
    selection code path, and a second copy of these ~90 lines could drift
    from the delivered one, which would be a physics bug. The guard is
    therefore `mc_siblings is not None` -- the same condition as `args.is_mc`
    one call-frame up -- and Part B proves the data output is unchanged."""
    calculator = IMCalculator(
        events=obj_record, min_events_per_fs=1,
        min_k=MIN_COUNT_PARTICLE_IN_COMBINATION, max_k=MAX_COUNT_PARTICLE_IN_COMBINATION,
        min_n=MIN_PARTICLES_IN_COMBINATION, max_n=MAX_PARTICLES_IN_COMBINATION,
    )

    n_fs_groups = 0
    n_signature_writes_incl = 0
    n_signature_writes_excl = 0
    n_values_written_incl = 0
    n_values_written_excl = 0
    max_signature_size = 0
    n_capped_signatures = 0
    label_event_counts_incl: dict[str, int] = {}
    label_event_counts_excl: dict[str, int] = {}
    skip_reason_totals: dict[str, int] = {}
    if mc_siblings is not None:
        # D8: the cap's own bookkeeping, per (signature) -- true_size and the
        # weight scale factor the builder must apply before merging files.
        cap_records: dict[str, dict] = {}
        n_sibling_writes = 0
        for suffix, sib in mc_siblings.items():
            if len(sib) != len(obj_record):
                raise RuntimeError(
                    f"MC sibling {suffix!r} has {len(sib)} entries for "
                    f"{len(obj_record)} events -- it must be aligned to "
                    "obj_record's own row order before the funnel is entered."
                )

    for label, fs_events, group_mask in _group_by_final_state_with_mask(obj_record):
        n_fs_groups += 1
        n_this_group = len(fs_events)
        label_event_counts_incl[label] = label_event_counts_incl.get(label, 0) + n_this_group
        writer_incl.record_final_state_count(label, n_this_group)

        fs_is_exclusive = is_exclusive_selected[group_mask]
        n_excl_this_group = int(fs_is_exclusive.sum())
        label_event_counts_excl[label] = label_event_counts_excl.get(label, 0) + n_excl_this_group
        writer_excl.record_final_state_count(label, n_excl_this_group)
        if mc_siblings is not None:
            # Mask 1 of 4: the final-state group mask, the same one applied to
            # obj_record to get fs_events.
            fs_siblings = mask_mc_siblings(mc_siblings, group_mask)

        for combination in all_combinations:
            if not physics_calcs.is_finalstate_contain_combination(label, combination):
                continue

            inv_mass, skip_reason = _calculate_combination_invariant_mass(
                fs_events, combination, im_config, calculator, logger, label,
            )
            if inv_mass is None:
                if skip_reason:
                    skip_reason_totals[skip_reason] = skip_reason_totals.get(skip_reason, 0) + 1
                continue

            combo_row_mask = _recompute_exact_count_row_mask(fs_events, combination)
            combo_is_exclusive = fs_is_exclusive[combo_row_mask]
            assert combo_is_exclusive.size == len(inv_mass), (
                f"alignment check failed for {label}/{combination}: "
                f"{combo_is_exclusive.size} != {len(inv_mass)}"
            )

            arr = ak.to_numpy(inv_mass).astype(np.float32)
            nan_mask = ~np.isnan(arr)
            arr = arr[nan_mask]
            combo_is_exclusive = combo_is_exclusive[nan_mask]
            if arr.size == 0:
                continue
            if mc_siblings is not None:
                # Masks 2 and 3 of 4: the exact-count row mask, then the NaN
                # mask -- applied in the same order, to the same rows.
                combo_siblings = mask_mc_siblings(fs_siblings, combo_row_mask)
                combo_siblings = mask_mc_siblings(combo_siblings, nan_mask)

            signature = prepare_im_combination_name(job_tag, label, combination)
            if arr.size > max_signature_size:
                max_signature_size = int(arr.size)
            if arr.size > COVERAGE_CAP_PER_SIGNATURE:
                true_size = int(arr.size)
                n_capped_signatures += 1
                rng = np.random.default_rng(seed=0)
                pick = rng.choice(arr.size, size=COVERAGE_CAP_PER_SIGNATURE, replace=False)
                arr = arr[pick]
                combo_is_exclusive = combo_is_exclusive[pick]
                writer_incl.set_metadata(f"CAPPED::{signature}", f"true_size={true_size}")
                if mc_siblings is not None:
                    # Mask 4 of 4: the SAME random pick indices, so a kept
                    # mass keeps its own weight and not another entry's.
                    combo_siblings = mask_mc_siblings(combo_siblings, pick)
                    scale = true_size / float(COVERAGE_CAP_PER_SIGNATURE)
                    cap_records[signature] = {
                        "true_size": true_size,
                        "kept": int(COVERAGE_CAP_PER_SIGNATURE),
                        "weight_scale": scale,
                    }
                    # D8: the builder must multiply this signature's weights by
                    # `weight_scale` BEFORE merging files, so the expected yield
                    # survives the subsample. Recorded in the shard metadata,
                    # not applied here (the raw siblings stay raw).
                    writer_incl.set_metadata(
                        f"CAPPED::{signature}",
                        f"true_size={true_size} kept={COVERAGE_CAP_PER_SIGNATURE} "
                        f"weight_scale={scale!r}",
                    )

            writer_incl.append_array(signature, arr)
            n_signature_writes_incl += 1
            n_values_written_incl += int(arr.size)
            if mc_siblings is not None:
                # Same flush as the masses: one transaction, committed by the
                # caller, so a crash can never leave masses without siblings.
                for suffix, sib in combo_siblings.items():
                    if len(sib) != arr.size:
                        raise RuntimeError(
                            f"{signature}: sibling {suffix!r} has {len(sib)} "
                            f"entries for {arr.size} masses -- alignment lost."
                        )
                    writer_incl.append_array(signature + suffix, sib)
                    n_sibling_writes += 1

            excl_arr = arr[combo_is_exclusive]
            if excl_arr.size > 0:
                writer_excl.append_array(signature, excl_arr)
                n_signature_writes_excl += 1
                n_values_written_excl += int(excl_arr.size)

    result = {
        "n_fs_groups": n_fs_groups,
        "n_signature_writes_incl": n_signature_writes_incl,
        "n_signature_writes_excl": n_signature_writes_excl,
        "n_values_written_incl": n_values_written_incl,
        "n_values_written_excl": n_values_written_excl,
        "max_signature_size": max_signature_size,
        "n_capped_signatures": n_capped_signatures,
        "label_event_counts_incl": label_event_counts_incl,
        "label_event_counts_excl": label_event_counts_excl,
        "skip_reason_totals": skip_reason_totals,
    }
    if mc_siblings is not None:
        result["n_mc_sibling_writes"] = n_sibling_writes
        result["mc_sibling_suffixes"] = list(mc_siblings.keys())
        result["capped_signatures"] = cap_records
    return result


def build_top4_object_record(muons: ak.Array, electrons: ak.Array, light_jets: ak.Array, bjets: ak.Array):
    """Top-4 truncation (Shikma/Maryna's request, top-4 task Step 1): keep
    at most 4 selected objects per event, priority (1) leptons --
    electrons and muons together, highest pT first, (2) b-jets by pT,
    (3) light jets by pT. Events with <=4 total objects are unchanged.
    Called AFTER all object selection/cleaning and AFTER the matched-mode
    acceptance gate has already decided which events are kept -- truncation
    never changes which events are accepted or which dataset an event
    belongs to, only which objects represent it afterward. Each type's own
    internal pT order is preserved (NanoAOD collections are already
    pT-descending; boolean-mask slicing preserves that order), matching
    "grouped by type and ordered by pT within each type as usual" once
    build_object_record zips the truncated arrays back together.

    Returns (top4_muons, top4_electrons, top4_light_jets, top4_bjets,
    n_original_objects) -- n_original_objects (a plain numpy int array,
    one entry per input event) is the per-event total selected-object
    count BEFORE truncation, for the required truncation diagnostics."""
    SRC_ELECTRON, SRC_MUON, SRC_BJET, SRC_JET = 0, 1, 2, 3

    def _tag(arr, src):
        return ak.zip({
            "pt": arr.pt,
            "src": ak.zeros_like(arr.pt, dtype=np.int64) + src,
            "idx": ak.local_index(arr, axis=1),
        })

    tagged_e = _tag(electrons, SRC_ELECTRON)
    tagged_m = _tag(muons, SRC_MUON)
    tagged_b = _tag(bjets, SRC_BJET)
    tagged_j = _tag(light_jets, SRC_JET)

    leptons_combined = ak.concatenate([tagged_e, tagged_m], axis=1)
    leptons_sorted = leptons_combined[ak.argsort(leptons_combined.pt, axis=1, ascending=False)]
    bjets_sorted = tagged_b[ak.argsort(tagged_b.pt, axis=1, ascending=False)]
    jets_sorted = tagged_j[ak.argsort(tagged_j.pt, axis=1, ascending=False)]

    # Priority order: leptons (combined), then b-jets, then light jets --
    # concatenation order IS priority order; local_index on the result is
    # the priority rank (0 = highest priority).
    priority_ordered = ak.concatenate([leptons_sorted, bjets_sorted, jets_sorted], axis=1)
    priority_rank = ak.local_index(priority_ordered, axis=1)
    n_original_objects = ak.to_numpy(ak.num(priority_ordered, axis=1))

    kept = priority_ordered[priority_rank < 4]

    def _keep_mask_for(orig_arr, src):
        orig_idx = ak.local_index(orig_arr, axis=1)
        kept_idx_this_src = kept[kept.src == src].idx
        pairs_orig, pairs_kept = ak.unzip(ak.cartesian([orig_idx, kept_idx_this_src], nested=True))
        return ak.fill_none(ak.any(pairs_orig == pairs_kept, axis=-1), False)

    top4_electrons = electrons[_keep_mask_for(electrons, SRC_ELECTRON)]
    top4_muons = muons[_keep_mask_for(muons, SRC_MUON)]
    top4_bjets = bjets[_keep_mask_for(bjets, SRC_BJET)]
    top4_light_jets = light_jets[_keep_mask_for(light_jets, SRC_JET)]

    return top4_muons, top4_electrons, top4_light_jets, top4_bjets, n_original_objects


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--dataset-label", required=True,
                   choices=list(TRIGGER_PATHS_BY_DATASET.keys()) + [MC_DATASET_LABEL],
                   help=f"the data stream this job reads; {MC_DATASET_LABEL!r} is "
                        "valid only together with --is-mc, where there is no "
                        "stream and the label only names the job.")
    p.add_argument("--record-id", type=int, required=True)
    p.add_argument("--file-index", type=int, required=True)
    p.add_argument("--output-dir", required=True)
    p.add_argument("--population", choices=["generic", "v0", "matched", "matched4"],
                   default="generic")
    p.add_argument("--validated-runs-json", default=DEFAULT_VALIDATED_RUNS_JSON)
    # --- electron-datasets task: options for --population matched4 ONLY.
    # They are ignored by generic/v0/matched, so no pre-existing invocation
    # changes behaviour.
    p.add_argument(
        "--no-emu-overlap-removal", action="store_true",
        help="matched4 only: switch OFF the D3 electron-muon overlap removal "
             f"(remove every selected electron within dR<{EMU_OVERLAP_DR_MAX} of a "
             "selected muon). FOR VALIDATION ONLY -- the production default is ON.",
    )
    p.add_argument(
        "--doubleeg-threshold-mode", choices=list(DOUBLEEG_THRESHOLD_MODES),
        default=DOUBLEEG_THRESHOLD_MODE_DEFAULT,
        help="matched4 only: D4's offline-pT rule on the matched DoubleEG "
             "electrons. 'leading_only' = the highest-offline-pT matched electron "
             "above 30 GeV; 'both' = at least two matched electrons above 30 GeV. "
             f"Default {DOUBLEEG_THRESHOLD_MODE_DEFAULT!r} -- approved 7 Oct 2026 "
             "(Maryna/Matan), from the Step D measurement's own fixed criterion.",
    )
    p.add_argument(
        "--debug-event-dump", action="store_true",
        help="matched4 only: also write debug_events.csv with one row per "
             "ACCEPTED event (run, lumi, event, dataset, the four acceptance "
             "flags, exclusive yes/no, final-state label, electrons removed by "
             "overlap removal). OFF by default -- not written in production.",
    )
    p.add_argument(
        "--is-mc", action="store_true",
        help="process a simulated (MC) NanoAOD file instead of real data. "
             "Requires --population matched4 and --dataset-label "
             f"{MC_DATASET_LABEL}. Skips the golden-JSON run filter (asserting "
             "the file IS simulation instead), requires the OR of all four "
             f"datasets' trigger paths plus {ELE27_PATH}, stores an event if "
             "any of the four data acceptances OR the SingleElectron candidate "
             "passes, applies NO de-duplication, and writes the per-entry MC "
             "weight siblings next to every mass signature. See "
             "studies/cms_mc_weights_v3/DESIGN.md Part D. WITHOUT this flag "
             "nothing below changes and the data output is unaffected.",
    )
    args = p.parse_args()

    # --is-mc preconditions, checked before anything is read.
    if args.is_mc:
        if args.population != "matched4":
            raise ValueError(
                "--is-mc is implemented for --population matched4 only (the "
                f"delivered selection) -- got {args.population!r}")
        if args.dataset_label != MC_DATASET_LABEL:
            raise ValueError(
                f"--is-mc requires --dataset-label {MC_DATASET_LABEL} (simulation has "
                f"no data stream) -- got {args.dataset_label!r}")
    elif args.dataset_label == MC_DATASET_LABEL:
        raise ValueError(
            f"--dataset-label {MC_DATASET_LABEL} is only valid together with --is-mc")

    logging.basicConfig(level=logging.WARNING, format="%(asctime)s %(levelname)s %(message)s")
    logger = logging.getLogger("run_dataset_on_file")

    dataset_label = args.dataset_label
    if args.is_mc:
        # D2: no stream, no de-duplication. The trigger gate is the OR over
        # every path any of the five stored conditions can need, so an event
        # that only the SingleElectron candidate would accept still survives
        # to be evaluated.
        own_paths = tuple(sorted(
            {p for paths in MATCHED4_TRIGGER_PATHS.values() for p in paths}
            | {ELE27_PATH}
        ))
        higher_priority = []
        veto_paths_by_label = {}
    elif args.population == "matched4":
        # electron-datasets task, D1/D2: this path's own trigger sets
        # (SingleMuon = HLT_IsoMu24 only, as on master) and its own
        # priority order DELIVERY_VETO_ORDER_4 -- never VETO_ORDER.
        if dataset_label not in DELIVERY_VETO_ORDER_4:
            raise ValueError(
                f"--population matched4 is implemented for {DELIVERY_VETO_ORDER_4} "
                f"only (SingleElectron is postponed) -- got {dataset_label!r}")
        own_paths = MATCHED4_TRIGGER_PATHS[dataset_label]
    elif dataset_label == "SingleMuon" and args.population == "matched":
        # Matched mode's SingleMuon trigger set is HLT_IsoMu24 ONLY (Maryna's
        # explicit instruction, TRIGGER_MATCHING_SPEC.md Section 4) --
        # generic/v0's SingleMuon trigger set (both IsoMu24 and IsoTkMu24,
        # from TRIGGER_PATHS_BY_DATASET) is untouched (Hard Rule 5); this
        # override only ever fires for population=="matched".
        own_paths = SINGLEMUON_MATCHED_TRIGGER_PATHS
    else:
        own_paths = TRIGGER_PATHS_BY_DATASET[dataset_label]
    if args.is_mc:
        pass  # own_paths / higher_priority / veto_paths_by_label set above
    elif args.population == "matched4":
        higher_priority = DELIVERY_VETO_ORDER_4[:DELIVERY_VETO_ORDER_4.index(dataset_label)]
        veto_paths_by_label = {h: list(MATCHED4_TRIGGER_PATHS[h]) for h in higher_priority}
    else:
        higher_priority = VETO_ORDER[:VETO_ORDER.index(dataset_label)]
        veto_paths_by_label = {h: TRIGGER_PATHS_BY_DATASET[h] for h in higher_priority}

    all_trigger_branches = list(own_paths)
    for paths in veto_paths_by_label.values():
        all_trigger_branches.extend(paths)
    if args.population == "matched4":
        # D2: every HLT branch needed to evaluate ALL FOUR acceptances must
        # be present in this file, whichever dataset it comes from. They are
        # listed as REQUIRED branches, so read_events stops the job with a
        # clear error if any one is missing rather than silently treating it
        # as "did not fire".
        for paths in MATCHED4_TRIGGER_PATHS.values():
            all_trigger_branches.extend(paths)
    required_branches = list(BASE_OBJECT_BRANCHES) + sorted(set(all_trigger_branches))
    if args.population in ("matched", "matched4"):
        required_branches = list(required_branches) + list(MATCHED_MODE_EXTRA_BRANCHES)
    if args.is_mc:
        # A missing weight branch is a hard error (read_events raises on any
        # missing required branch). Never defaulted to 1: a silent w_gen = 1
        # mis-normalises every sample that is not unit-weight.
        required_branches = list(required_branches) + list(MC_REQUIRED_BRANCHES)

    t0 = time.time()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    file_url = resolve_file_url(args.record_id, args.file_index)
    print(f"[{dataset_label}] resolved record {args.record_id} file index {args.file_index} -> {file_url}", flush=True)

    branch_titles = {}
    if args.population == "matched4":
        events, branch_titles = read_events(file_url, required_branches, return_titles=True)
    else:
        events = read_events(file_url, required_branches)
    n_read = len(events)
    print(f"[{dataset_label}] read {n_read} events", flush=True)

    if args.is_mc:
        # D2 / data-MC difference 2: simulation has no certified-run concept
        # (run == 1 throughout), so the golden-JSON filter is SKIPPED -- and
        # not silently: the file is asserted to BE simulation first, so a data
        # file handed to --is-mc stops the job instead of quietly losing the
        # run filter.
        if not is_simulation(events):
            raise RuntimeError(
                "STOP: --is-mc was given but this file does not look like "
                "simulation (no genWeight field and run != 1 for every event). "
                "Refusing to skip the golden-JSON run filter on what may be "
                f"real data: {file_url}"
            )
        events_golden = events
        golden_stats = {"n_before": n_read, "n_after": n_read,
                        "skipped_reason": "simulation: no golden JSON applies"}
        n_after_golden_json = n_read
        print(f"[{dataset_label}] simulation confirmed; golden-JSON filter SKIPPED "
              f"({n_read} events kept)", flush=True)
    else:
        validated_runs = ValidatedRunsFilter(args.validated_runs_json)
        events_golden, golden_stats = apply_validated_runs_filter(events, validated_runs)
        n_after_golden_json = golden_stats["n_after"]
        print(f"[{dataset_label}] golden-JSON filter: {golden_stats['n_before']} -> {n_after_golden_json}", flush=True)

    events_triggered, trigger_stats = apply_trigger_requirement(
        events_golden, {"mode": "any", "paths": own_paths}
    )
    n_after_trigger = trigger_stats["n_after"]
    print(f"[{dataset_label}] own-trigger requirement ({own_paths}): "
          f"{trigger_stats['n_before']} -> {n_after_trigger}, per_path={trigger_stats['per_path']}", flush=True)

    # Veto masks (Step 2 de-duplication), computed on events_triggered --
    # i.e. AFTER this dataset's own trigger, matching the task's own
    # "exclusive" definition (passes own trigger AND fails every
    # higher-veto-priority dataset's trigger set).
    n_events_triggered = len(events_triggered)
    veto_masks = {}
    for label, paths in veto_paths_by_label.items():
        m = np.zeros(n_events_triggered, dtype=bool)
        for path in paths:
            m |= ak.to_numpy(events_triggered[path]).astype(bool)
        veto_masks[label] = m
    n_vetoed_by_each_higher_dataset = {label: int(m.sum()) for label, m in veto_masks.items()}

    vetoed_by_any = np.zeros(n_events_triggered, dtype=bool)
    for m in veto_masks.values():
        vetoed_by_any |= m
    is_exclusive_pretrigger = ~vetoed_by_any  # aligned to events_triggered
    # For MC veto_paths_by_label is empty, so the loops above are no-ops and
    # is_exclusive_pretrigger is already all-True -- which is D2's "no
    # de-duplication" expressed through the existing machinery rather than
    # around it. The exclusive shard an MC job writes therefore holds the same
    # masses as the inclusive one (without siblings) and is ignored by the MC
    # builder, which reads the inclusive shards only.

    # Object selection (unchanged, imported). `charge` is passed as a pure
    # passthrough extra field (selection.select_muons's own documented
    # mechanism) -- needed only for the opposite-sign low-mass dimuon
    # diagnostic below; it does not affect the selection mask itself.
    muons = selection.select_muons(events_triggered, extra_fields={"charge": events_triggered.Muon_charge})
    electrons = selection.select_electrons(events_triggered)
    jets = selection.select_and_split_jets(events_triggered, muons, electrons, apply_lepton_cleaning=True)

    # Diagnostics-only: an electron-charge passthrough, mirroring the
    # muon-charge one above. selection.select_electrons itself has no
    # extra_fields parameter (unlike select_muons), so this reproduces its
    # own exact 3-condition mask externally, using ONLY that function's
    # own imported constants (never re-typed), then adds the resulting
    # per-event charge array as a new field via ak.with_field on a
    # SEPARATE variable (electrons_diag) -- the real `electrons` used for
    # gating/combinations/shards below is completely untouched.
    electron_diag_mask = (
        (events_triggered.Electron_pt > selection.ELECTRON_PT_MIN_GEV)
        & (abs(events_triggered.Electron_eta) < selection.ELECTRON_ETA_MAX)
        & (events_triggered.Electron_cutBased >= selection.ELECTRON_CUTBASED_MIN)
    )
    electron_charge_selected = events_triggered.Electron_charge[electron_diag_mask]
    electrons_diag = ak.with_field(electrons, electron_charge_selected, "charge")

    diagnostics = compute_diagnostics(muons, electrons_diag, jets["BJets"])

    v0_result = None
    matching_diagnostics = None
    matched4_diagnostics = None
    mc_diagnostics = None
    if args.population == "generic":
        total_objects = ak.num(muons) + ak.num(electrons) + ak.num(jets["Jets"]) + ak.num(jets["BJets"])
        keep = ak.to_numpy(total_objects >= MIN_TOTAL_SELECTED_OBJECTS)
        obj_record = selection.build_object_record(
            muons[keep], electrons[keep], {"Jets": jets["Jets"][keep], "BJets": jets["BJets"][keep]}
        )
    elif args.population == "matched":
        # Trigger-matching task (TRIGGER_MATCHING_SPEC.md). NEW mode only --
        # does not touch the generic/v0 branches above/below (Hard Rule 5).
        if dataset_label not in ("DoubleMuon", "SingleMuon"):
            raise ValueError(
                f"--population matched is only implemented for DoubleMuon and SingleMuon "
                f"(see TRIGGER_MATCHING_SPEC.md) -- got dataset_label={dataset_label!r}"
            )
        trigobj = ak.zip({
            "pt": events_triggered.TrigObj_pt,
            "eta": events_triggered.TrigObj_eta,
            "phi": events_triggered.TrigObj_phi,
            "id": events_triggered.TrigObj_id,
            "filterBits": events_triggered.TrigObj_filterBits,
        })
        if dataset_label == "DoubleMuon":
            required_bit = TRIGOBJ_BIT_TRKISOVVL
            min_matched = DOUBLEMUON_MATCHED_MIN_MUONS
            leading_pt_min = DOUBLEMUON_MATCHED_LEADING_PT_MIN_GEV
        else:  # SingleMuon
            required_bit = TRIGOBJ_BIT_ISO
            min_matched = SINGLEMUON_MATCHED_MIN_MUONS
            leading_pt_min = SINGLEMUON_MATCHED_PT_MIN_GEV

        keep = matched_acceptance_mask(muons, trigobj, required_bit, min_matched, leading_pt_min)
        matching_diagnostics = compute_matching_diagnostics(muons, trigobj, required_bit, min_matched, leading_pt_min)
        obj_record = selection.build_object_record(
            muons[keep], electrons[keep], {"Jets": jets["Jets"][keep], "BJets": jets["BJets"][keep]}
        )

        if dataset_label == "SingleMuon":
            # Matched mode's own exclusive-shard definition (task spec): veto
            # ONLY against DoubleMuon, using ACCEPTANCE (DoubleMuon's own
            # trigger fired AND DoubleMuon's own matching rule), evaluated on
            # this SAME event -- NOT the generic-mode veto_masks computed
            # above (bits-only, and also vetoes against DoubleEG/MuonEG,
            # which are "not part of this combination" per the task's own
            # scope). This override replaces is_exclusive_pretrigger for
            # THIS branch only. DoubleMuon's own matched-mode run needs no
            # override: higher_priority is already empty for DoubleMuon, so
            # is_exclusive_pretrigger computed above is already all-True
            # ("DoubleMuon identical to inclusive", per spec).
            doublemuon_fired = np.zeros(n_events_triggered, dtype=bool)
            for path in TRIGGER_PATHS_BY_DATASET["DoubleMuon"]:
                doublemuon_fired |= ak.to_numpy(events_triggered[path]).astype(bool)
            doublemuon_accepted = matched_acceptance_mask(
                muons, trigobj, TRIGOBJ_BIT_TRKISOVVL,
                DOUBLEMUON_MATCHED_MIN_MUONS, DOUBLEMUON_MATCHED_LEADING_PT_MIN_GEV,
            )
            is_exclusive_pretrigger = ~(doublemuon_fired & doublemuon_accepted)
    elif args.population == "matched4":
        # Electron-datasets task (D2-D6): the FOUR-dataset delivery path.
        # DoubleMuon + SingleMuon + DoubleEG + MuonEG, acceptance-based
        # de-duplication in DELIVERY_VETO_ORDER_4, electron-muon overlap
        # removal ON by default. --population matched (the delivered muon
        # production) is untouched by everything in this branch.
        if not args.is_mc and dataset_label not in DELIVERY_VETO_ORDER_4:
            raise ValueError(
                f"--population matched4 is implemented for "
                f"{DELIVERY_VETO_ORDER_4} only (SingleElectron is postponed) -- "
                f"got dataset_label={dataset_label!r}"
            )
        trigobj = ak.zip({
            "pt": events_triggered.TrigObj_pt,
            "eta": events_triggered.TrigObj_eta,
            "phi": events_triggered.TrigObj_phi,
            "id": events_triggered.TrigObj_id,
            "filterBits": events_triggered.TrigObj_filterBits,
        })
        # D6: the bit meanings are re-read from the file's own branch titles
        # and asserted BEFORE a single match is computed.
        trigobj_title_check = assert_trigobj_bit_meanings(branch_titles)

        # D3: electron-muon overlap removal, right after object selection.
        overlap_removal_enabled = not args.no_emu_overlap_removal
        electrons_pre_removal = electrons
        electrons, n_electrons_removed, removed_mask = remove_electrons_overlapping_muons(
            electrons_pre_removal, muons, dr_max=EMU_OVERLAP_DR_MAX,
            enabled=overlap_removal_enabled,
        )
        # From here on `electrons` IS the post-removal collection, so every
        # later step -- trigger matching, the Version B count, the
        # final-state labels, top4/nonjet4/rare4 -- uses it automatically.
        n_events_removal_changed = int((n_electrons_removed > 0).sum())
        n_jet_order_would_matter = count_events_where_jet_cleaning_order_would_matter(
            electrons_pre_removal[removed_mask], muons, jets["Jets"], jets["BJets"])

        doubleeg_threshold_mode = args.doubleeg_threshold_mode
        acceptances = evaluate_four_acceptances(
            events_triggered, muons, electrons, trigobj, doubleeg_threshold_mode)
        if args.is_mc:
            # D2: the four acceptances are computed by the IDENTICAL functions
            # on the IDENTICAL post-overlap-removal objects -- the call above is
            # the data path's own. The only MC additions are the fifth
            # (candidate) condition and the store rule.
            mc_title_check = assert_trigobj_bit_meanings_mc(branch_titles)
            ele27 = ele27_candidate_acceptance(events_triggered, electrons, trigobj)
            keep = mc_store_mask(acceptances, ele27)
            # No de-duplication (D2): every stored MC event is "exclusive" in
            # the only sense the shared funnel uses the flag for.
            is_exclusive_pretrigger = np.ones(n_events_triggered, dtype=bool)
            acceptance_overlap_with_higher = {}
            higher4 = []
            mc_event_info = build_mc_event_info(events_triggered, args.record_id)
            # D3: aligned to events_triggered here; masked down to obj_record's
            # rows by `keep` immediately below, then through every later mask.
            mc_siblings_triggered = mc_sibling_arrays(
                events_triggered, mc_event_info, acceptances, ele27)
        else:
            keep = acceptances[dataset_label]["accepted"]
            is_exclusive_pretrigger, acceptance_overlap_with_higher, higher4 = (
                exclusive_mask_from_acceptances(acceptances, dataset_label))
        attributed = attribute_to_exclusive_dataset(acceptances)

        # D6: guard-violation counters, one per matcher actually used. The
        # two muon matchers are the ones matched mode already uses
        # (DoubleMuon's bit 1 and SingleMuon's bit 2); the two electron
        # matchers are DoubleEG's bit 16 and MuonEG's bit 32, whose
        # bookkeeping the acceptance functions already produced.
        muon_bk_bit1 = trigobj_best_match(muons, trigobj, TRIGOBJ_MUON_ID, TRIGOBJ_BIT_TRKISOVVL)
        muon_bk_bit2 = trigobj_best_match(muons, trigobj, TRIGOBJ_MUON_ID, TRIGOBJ_BIT_ISO)
        guard_violations = {
            "muons_vs_id13_bit_trkisovvl": count_trigger_guard_violations(
                muon_bk_bit1, trigobj, TRIGOBJ_MUON_ID),
            "muons_vs_id13_bit_iso": count_trigger_guard_violations(
                muon_bk_bit2, trigobj, TRIGOBJ_MUON_ID),
            "electrons_vs_id11_bit_2e": count_trigger_guard_violations(
                acceptances["DoubleEG"]["bookkeeping"], trigobj, TRIGOBJ_ELECTRON_ID),
            "electrons_vs_id11_bit_1e1mu": count_trigger_guard_violations(
                acceptances["MuonEG"]["bookkeeping"], trigobj, TRIGOBJ_ELECTRON_ID),
        }
        guard_violations["total"] = int(sum(guard_violations.values()))

        obj_record = selection.build_object_record(
            muons[keep], electrons[keep], {"Jets": jets["Jets"][keep], "BJets": jets["BJets"][keep]}
        )
        if args.is_mc:
            # D3: the _mcEventInfo record is carried through the acceptance
            # mask exactly like the object collections above, and the flat
            # siblings with it. Asserted rather than assumed, because every
            # later alignment claim rests on this one.
            mc_event_info_kept = mc_event_info[keep]
            mc_siblings_base = mask_mc_siblings(mc_siblings_triggered, keep)
            assert len(mc_event_info_kept) == len(obj_record), (
                f"_mcEventInfo lost alignment at the acceptance mask: "
                f"{len(mc_event_info_kept)} != {len(obj_record)}")
            for _suffix, _sib in mc_siblings_base.items():
                assert len(_sib) == len(obj_record), (
                    f"MC sibling {_suffix!r} lost alignment at the acceptance "
                    f"mask: {len(_sib)} != {len(obj_record)}")

        n_removed_total = int(n_electrons_removed.sum())
        matched4_diagnostics = {
            "delivery_veto_order": list(DELIVERY_VETO_ORDER_4),
            "own_dataset": dataset_label,
            "higher_priority_datasets_this_path": higher4,
            "doubleeg_threshold_mode": doubleeg_threshold_mode,
            "emu_overlap_removal_enabled": overlap_removal_enabled,
            "emu_overlap_removal_dr_max": EMU_OVERLAP_DR_MAX,
            "n_electrons_removed_total": n_removed_total,
            "n_events_with_an_electron_removed": n_events_removal_changed,
            "n_events_jet_cleaning_order_would_matter": n_jet_order_would_matter,
            "trigobj_title_check": trigobj_title_check,
            "trigger_guard_violations": guard_violations,
            "acceptance_counts": {
                label: int(acceptances[label]["accepted"].sum())
                for label in DELIVERY_VETO_ORDER_4
            },
            "fired_counts": {
                label: int(acceptances[label]["fired"].sum())
                for label in DELIVERY_VETO_ORDER_4
            },
            "cutflow_per_dataset": {
                label: acceptances[label]["cutflow"] for label in DELIVERY_VETO_ORDER_4
            },
            "n_own_accepted": int(keep.sum()),
            "n_own_exclusive": int((keep & is_exclusive_pretrigger).sum()),
            "n_own_accepted_also_accepted_by_higher": acceptance_overlap_with_higher,
            "n_attributed_per_dataset": {
                label: int((attributed == label).sum()) for label in DELIVERY_VETO_ORDER_4
            },
            "n_accepted_by_none": int((attributed == "").sum()),
            "bookkeeping_summary": {
                "doubleeg_electrons_bit16": matching_bookkeeping_summary(
                    acceptances["DoubleEG"]["bookkeeping"], "electrons vs id11 bit16 (2e)"),
                "muoneg_electrons_bit32": matching_bookkeeping_summary(
                    acceptances["MuonEG"]["bookkeeping"], "electrons vs id11 bit32 (1e-1mu)"),
                "doublemuon_muons_bit1": matching_bookkeeping_summary(
                    muon_bk_bit1, "muons vs id13 bit1 (TrkIsoVVL)"),
                "singlemuon_muons_bit2": matching_bookkeeping_summary(
                    muon_bk_bit2, "muons vs id13 bit2 (Iso)"),
            },
            "doubleeg_interpretation_checks": doubleeg_interpretation_diagnostics(
                electrons, acceptances["DoubleEG"]["bookkeeping"],
                acceptances["DoubleEG"]["pre_offline_cut_mask"]),
            "emu_pair_mass_fine_histogram_accepted_events": _histogram_with_overflow(
                emu_pair_mass_values(electrons[keep], muons[keep]),
                DIAGNOSTIC_EMU_MASS_FINE_BIN_EDGES),
            "emu_pair_mass_fine_histogram_accepted_events_pre_removal": _histogram_with_overflow(
                emu_pair_mass_values(electrons_pre_removal[keep], muons[keep]),
                DIAGNOSTIC_EMU_MASS_FINE_BIN_EDGES),
            "ee_pair_mass_z_histograms_accepted_events": {
                region: _histogram_1gev(values, DIAGNOSTIC_EE_MASS_Z_BIN_EDGES)
                for region, values in ee_pair_mass_by_region(electrons[keep]).items()
            },
            "light_jet_multiplicity_accepted_events": _light_jet_multiplicity(
                jets["Jets"][keep]),
        }
        if args.is_mc:
            acc_mask_kept = mc_siblings_base[MC_SIBLING_ACCEPTANCE]
            genw_kept = mc_siblings_base[MC_SIBLING_GENWEIGHT]
            ele27pt_kept = mc_siblings_base[MC_SIBLING_ELE27_PT]
            four_bits = sum(MC_ACC_BIT_BY_LABEL.values())
            only_ele27_mask = (
                ((acc_mask_kept & MC_ACC_BIT_ELE27_CANDIDATE) != 0)
                & ((acc_mask_kept & four_bits) == 0)
            )
            n_only_ele27 = int(only_ele27_mask.sum())
            mc_diagnostics = {
                "record_id": args.record_id,
                "mc_channel_number_source": "--record-id argument (CMS NanoAOD "
                                            "carries no per-event dataset identifier)",
                "trigger_gate_paths": list(own_paths),
                "golden_json_applied": False,
                "deduplication_applied": False,
                "trigobj_title_check_mc": mc_title_check,
                "n_events_triggered": int(n_events_triggered),
                "n_stored": int(len(obj_record)),
                "n_accepted_per_dataset": {
                    label: int(acceptances[label]["accepted"].sum())
                    for label in DELIVERY_VETO_ORDER_4
                },
                "ele27_candidate_cutflow": ele27["cutflow"],
                "n_ele27_candidate_accepted": int(ele27["accepted"].sum()),
                "n_stored_by_acceptance_bit": {
                    label: int(((acc_mask_kept & bit) != 0).sum())
                    for label, bit in MC_ACC_BIT_BY_LABEL.items()
                },
                "n_stored_ele27_candidate": int(
                    ((acc_mask_kept & MC_ACC_BIT_ELE27_CANDIDATE) != 0).sum()),
                "n_stored_ele27_fired": int(
                    ((acc_mask_kept & MC_ACC_BIT_ELE27_FIRED) != 0).sum()),
                "n_stored_only_ele27_candidate": n_only_ele27,
                "n_stored_with_ele27_match": int((ele27pt_kept >= 0).sum()),
                "genweight_stored_events": {
                    "sum": float(genw_kept.sum()),
                    "n_negative": int((genw_kept < 0).sum()),
                    "min": float(genw_kept.min()) if genw_kept.size else None,
                    "max": float(genw_kept.max()) if genw_kept.size else None,
                },
                "mc_run_number_distinct_values": sorted(
                    int(v) for v in np.unique(
                        ak.to_numpy(mc_event_info_kept[MC_RUN_NUMBER_FIELD]))
                ) if len(mc_event_info_kept) else [],
                "sibling_suffixes": list(MC_SIBLING_SUFFIXES),
                "acceptance_bit_map": dict(
                    list(MC_ACC_BIT_BY_LABEL.items())
                    + [("Ele27Candidate", MC_ACC_BIT_ELE27_CANDIDATE),
                       ("Ele27Fired", MC_ACC_BIT_ELE27_FIRED)]),
            }
    else:  # v0 -- regression-check mode only, see module docstring.
        keep = ak.to_numpy((ak.num(muons) >= 2) & (ak.num(jets["Jets"]) >= 1))
        v0_result = selection.select_event_selection_cutflow(events_triggered)
        obj_record = v0_result["obj_record"]
        # This driver's own externally-computed `keep` mask (used below to
        # align is_exclusive_pretrigger with obj_record's row order) must
        # select exactly the same events as select_event_selection_cutflow's
        # own internal final_mask -- true by construction (same muons/jets
        # selection functions, same >=2mu & >=1 light-jet condition), but
        # asserted here rather than only assumed, since obj_record's actual
        # row order/count comes from the internal call, not from `keep`.
        assert len(obj_record) == int(keep.sum()), (
            f"v0 population alignment check failed: len(obj_record)={len(obj_record)} "
            f"!= keep.sum()={int(keep.sum())} -- externally recomputed gate mask does not "
            f"match select_event_selection_cutflow's own internal population"
        )

    n_after_gate = len(obj_record)
    is_exclusive_selected = is_exclusive_pretrigger[keep]
    n_exclusive = int(is_exclusive_selected.sum())
    print(f"[{dataset_label}] population={args.population}: n_after_gate={n_after_gate}, "
          f"n_exclusive={n_exclusive}, n_vetoed_by_each_higher_dataset={n_vetoed_by_each_higher_dataset}",
          flush=True)

    all_combinations = get_all_combinations(
        object_types=OBJECT_TYPES,
        min_particles=MIN_PARTICLES_IN_COMBINATION,
        max_particles=MAX_PARTICLES_IN_COMBINATION,
        min_count=MIN_COUNT_PARTICLE_IN_COMBINATION,
        max_count=MAX_COUNT_PARTICLE_IN_COMBINATION,
        max_total_particles=MAX_TOTAL_PARTICLES_IN_COMBINATION,
        include_subleading=INCLUDE_SUBLEADING,
        max_subleading_index=MAX_SUBLEADING_INDEX,
    )
    assert len(all_combinations) == 186, f"expected 186 combinations, got {len(all_combinations)}"

    im_config = {"field_to_slice_by": FIELD_TO_SLICE_BY}

    job_tag = f"{dataset_label}_record{args.record_id}_file{args.file_index}"
    incl_shard_path = output_dir / "dataset_shard_inclusive.sqlite"
    excl_shard_path = output_dir / "dataset_shard_exclusive.sqlite"
    for path in (incl_shard_path, excl_shard_path):
        if path.exists():
            path.unlink()
    writer_incl = SqliteArrayShardWriter(str(incl_shard_path))
    writer_excl = SqliteArrayShardWriter(str(excl_shard_path))

    funnel_result = run_combination_funnel(
        obj_record, is_exclusive_selected, job_tag, all_combinations, im_config, logger, writer_incl, writer_excl,
        mc_siblings=(mc_siblings_base if args.is_mc else None),
    )
    n_fs_groups = funnel_result["n_fs_groups"]
    n_signature_writes_incl = funnel_result["n_signature_writes_incl"]
    n_signature_writes_excl = funnel_result["n_signature_writes_excl"]
    n_values_written_incl = funnel_result["n_values_written_incl"]
    n_values_written_excl = funnel_result["n_values_written_excl"]
    max_signature_size = funnel_result["max_signature_size"]
    n_capped_signatures = funnel_result["n_capped_signatures"]
    label_event_counts_incl = funnel_result["label_event_counts_incl"]
    label_event_counts_excl = funnel_result["label_event_counts_excl"]
    skip_reason_totals = funnel_result["skip_reason_totals"]

    common_metadata = {
        "n_read": n_read,
        "n_after_golden_json": n_after_golden_json,
        "n_after_trigger": n_after_trigger,
        "n_after_gate": n_after_gate,
        "n_exclusive": n_exclusive,
        "dataset_label": dataset_label,
        "record_id": args.record_id,
        "file_index": args.file_index,
        "file_url": file_url,
        "population": args.population,
        "own_trigger_paths": ",".join(own_paths),
        "higher_priority_datasets": ",".join(higher_priority),
    }
    if args.is_mc:
        # D4: the builder reads these from the shard itself, so a shard always
        # carries the numbers needed to normalise it -- it never has to trust a
        # separate bookkeeping file. runs_gen_event_sumw is this FILE's own
        # Runs-tree total and file_sum_genweight is the sum over every event of
        # the file BEFORE any selection; the builder's per-file Sigma-w check
        # compares exactly these two.
        mc_runs = read_runs_tree_totals(file_url)
        file_sum_genweight = float(np.asarray(
            ak.to_numpy(events.genWeight), dtype=np.float64).sum())
        common_metadata.update({
            "is_mc": 1,
            "mc_record_id": args.record_id,
            "mc_channel_number": args.record_id,
            "mc_sibling_suffixes": ",".join(MC_SIBLING_SUFFIXES),
            "mc_weight_suffix_reserved": MC_WEIGHT_SUFFIX,
            "runs_gen_event_sumw": repr(mc_runs["gen_event_sumw"]),
            "runs_gen_event_count": repr(mc_runs["gen_event_count"]),
            "file_sum_genweight_all_events": repr(file_sum_genweight),
            "file_n_events_all": n_read,
        })
    for writer in (writer_incl, writer_excl):
        for k, v in common_metadata.items():
            writer.set_metadata(k, v)
        writer.commit()
        writer.close()

    # --- Top-4 truncation (Shikma/Maryna's request, top-4 task Step 1) ---
    # --population matched ONLY -- generic/v0 are completely untouched
    # (Hard Rule 5). Computed on the SAME accepted-event objects
    # (muons[keep]/electrons[keep]/jets["Jets"][keep]/jets["BJets"][keep])
    # already used to build the normal obj_record above -- truncation is
    # purely a post-gate relabeling of which objects represent an already-
    # accepted event, so it can never change n_after_gate/n_exclusive.
    top4_diagnostics = None
    nonjet4_diagnostics = None
    rare4_diagnostics = None
    if args.population in ("matched", "matched4"):
        top4_muons, top4_electrons, top4_light_jets, top4_bjets, n_original_objects = build_top4_object_record(
            muons[keep], electrons[keep], jets["Jets"][keep], jets["BJets"][keep]
        )
        obj_record_top4 = selection.build_object_record(
            top4_muons, top4_electrons, {"Jets": top4_light_jets, "BJets": top4_bjets}
        )
        assert len(obj_record_top4) == n_after_gate, (
            f"top-4 truncation must not change the accepted-event count: "
            f"len(obj_record_top4)={len(obj_record_top4)} != n_after_gate={n_after_gate}"
        )

        top4_incl_shard_path = output_dir / "dataset_shard_top4_inclusive.sqlite"
        top4_excl_shard_path = output_dir / "dataset_shard_top4_exclusive.sqlite"
        for path in (top4_incl_shard_path, top4_excl_shard_path):
            if path.exists():
                path.unlink()
        writer_top4_incl = SqliteArrayShardWriter(str(top4_incl_shard_path))
        writer_top4_excl = SqliteArrayShardWriter(str(top4_excl_shard_path))

        top4_funnel_result = run_combination_funnel(
            obj_record_top4, is_exclusive_selected, job_tag, all_combinations, im_config, logger,
            writer_top4_incl, writer_top4_excl,
            # top-4 truncation keeps every accepted event (asserted above), so
            # the siblings are the same rows in the same order.
            mc_siblings=(mc_siblings_base if args.is_mc else None),
        )

        top4_common_metadata = dict(common_metadata)
        top4_common_metadata["object_truncation"] = "top4"
        for writer in (writer_top4_incl, writer_top4_excl):
            for k, v in top4_common_metadata.items():
                writer.set_metadata(k, v)
            writer.commit()
            writer.close()

        n_truncated = int((n_original_objects > 4).sum())
        from collections import Counter
        original_object_count_distribution = {
            str(k): int(v) for k, v in sorted(Counter(n_original_objects.tolist()).items())
        }
        top4_diagnostics = {
            "n_accepted_events": n_after_gate,
            "n_accepted_events_gt4_objects": n_truncated,
            "original_object_count_distribution": original_object_count_distribution,
            "n_fs_groups": top4_funnel_result["n_fs_groups"],
            "n_signature_writes_inclusive": top4_funnel_result["n_signature_writes_incl"],
            "n_signature_writes_exclusive": top4_funnel_result["n_signature_writes_excl"],
            "n_values_written_inclusive": top4_funnel_result["n_values_written_incl"],
            "n_values_written_exclusive": top4_funnel_result["n_values_written_excl"],
            "max_signature_size_this_job": top4_funnel_result["max_signature_size"],
            "n_capped_signatures": top4_funnel_result["n_capped_signatures"],
            "final_state_label_event_counts_inclusive": top4_funnel_result["label_event_counts_incl"],
            "final_state_label_event_counts_exclusive": top4_funnel_result["label_event_counts_excl"],
            "skip_reason_totals": top4_funnel_result["skip_reason_totals"],
        }

        # --- nonjet4 rule (nonjet4 task, Step 1) -- see module docstring.
        # Reuses the top4_* outputs just computed above (aligned to the
        # accepted-event rows, i.e. muons[keep]/electrons[keep]/
        # jets["Jets"][keep]/jets["BJets"][keep]); does not recompute the
        # truncation. Only new work here: the N>4 reject mask and the
        # required rejection diagnostics.
        n_lepton_bjet = ak.to_numpy(
            ak.num(electrons[keep], axis=1) + ak.num(muons[keep], axis=1) + ak.num(jets["BJets"][keep], axis=1)
        )
        nonjet4_keep_mask = n_lepton_bjet <= 4
        n_rejected = int((~nonjet4_keep_mask).sum())

        nonjet4_muons = top4_muons[nonjet4_keep_mask]
        nonjet4_electrons = top4_electrons[nonjet4_keep_mask]
        nonjet4_light_jets = top4_light_jets[nonjet4_keep_mask]
        nonjet4_bjets = top4_bjets[nonjet4_keep_mask]
        obj_record_nonjet4 = selection.build_object_record(
            nonjet4_muons, nonjet4_electrons, {"Jets": nonjet4_light_jets, "BJets": nonjet4_bjets}
        )
        assert len(obj_record_nonjet4) == n_after_gate - n_rejected, (
            f"nonjet4 rejection must remove exactly the N>4 events: "
            f"len(obj_record_nonjet4)={len(obj_record_nonjet4)} != "
            f"n_after_gate-n_rejected={n_after_gate - n_rejected}"
        )

        is_exclusive_selected_nonjet4 = is_exclusive_selected[nonjet4_keep_mask]

        nonjet4_incl_shard_path = output_dir / "dataset_shard_nonjet4_inclusive.sqlite"
        nonjet4_excl_shard_path = output_dir / "dataset_shard_nonjet4_exclusive.sqlite"
        for path in (nonjet4_incl_shard_path, nonjet4_excl_shard_path):
            if path.exists():
                path.unlink()
        writer_nonjet4_incl = SqliteArrayShardWriter(str(nonjet4_incl_shard_path))
        writer_nonjet4_excl = SqliteArrayShardWriter(str(nonjet4_excl_shard_path))

        nonjet4_funnel_result = run_combination_funnel(
            obj_record_nonjet4, is_exclusive_selected_nonjet4, job_tag, all_combinations, im_config, logger,
            writer_nonjet4_incl, writer_nonjet4_excl,
            mc_siblings=(mask_mc_siblings(mc_siblings_base, nonjet4_keep_mask)
                         if args.is_mc else None),
        )

        nonjet4_common_metadata = dict(common_metadata)
        nonjet4_common_metadata["object_truncation"] = "nonjet4"
        for writer in (writer_nonjet4_incl, writer_nonjet4_excl):
            for k, v in nonjet4_common_metadata.items():
                writer.set_metadata(k, v)
            writer.commit()
            writer.close()

        # Required diagnostics (nonjet4 task, Step 1 spec): distribution of
        # N and the electron/muon/b-jet composition of the REJECTED (N>4)
        # events, and how many of the KEPT (N<=4) events had >=1 selected
        # light jet dropped (more selected light jets existed than the
        # remaining slots up to 4 total kept objects).
        from collections import Counter as _Counter
        rej_mask_np = ~nonjet4_keep_mask
        rejected_N_distribution = {
            str(k): int(v) for k, v in sorted(_Counter(n_lepton_bjet[rej_mask_np].tolist()).items())
        }
        n_e_rej = ak.to_numpy(ak.num(electrons[keep], axis=1))[rej_mask_np]
        n_m_rej = ak.to_numpy(ak.num(muons[keep], axis=1))[rej_mask_np]
        n_b_rej = ak.to_numpy(ak.num(jets["BJets"][keep], axis=1))[rej_mask_np]
        rejected_event_composition = {
            "electrons": {str(k): int(v) for k, v in sorted(_Counter(n_e_rej.tolist()).items())},
            "muons": {str(k): int(v) for k, v in sorted(_Counter(n_m_rej.tolist()).items())},
            "bjets": {str(k): int(v) for k, v in sorted(_Counter(n_b_rej.tolist()).items())},
        }

        n_orig_light_jets_kept_events = ak.to_numpy(ak.num(jets["Jets"][keep][nonjet4_keep_mask], axis=1))
        n_kept_light_jets = ak.to_numpy(ak.num(nonjet4_light_jets, axis=1))
        n_kept_events_with_light_jets_dropped = int((n_orig_light_jets_kept_events > n_kept_light_jets).sum())

        nonjet4_diagnostics = {
            "n_accepted_events_before_nonjet4_rule": n_after_gate,
            "n_rejected_gt4_lepton_bjet": n_rejected,
            "n_kept_le4_lepton_bjet": n_after_gate - n_rejected,
            "rejected_N_distribution": rejected_N_distribution,
            "rejected_event_composition": rejected_event_composition,
            "n_kept_events_with_light_jets_dropped": n_kept_events_with_light_jets_dropped,
            "n_fs_groups": nonjet4_funnel_result["n_fs_groups"],
            "n_signature_writes_inclusive": nonjet4_funnel_result["n_signature_writes_incl"],
            "n_signature_writes_exclusive": nonjet4_funnel_result["n_signature_writes_excl"],
            "n_values_written_inclusive": nonjet4_funnel_result["n_values_written_incl"],
            "n_values_written_exclusive": nonjet4_funnel_result["n_values_written_excl"],
            "max_signature_size_this_job": nonjet4_funnel_result["max_signature_size"],
            "n_capped_signatures": nonjet4_funnel_result["n_capped_signatures"],
            "final_state_label_event_counts_inclusive": nonjet4_funnel_result["label_event_counts_incl"],
            "final_state_label_event_counts_exclusive": nonjet4_funnel_result["label_event_counts_excl"],
            "skip_reason_totals": nonjet4_funnel_result["skip_reason_totals"],
        }

        # --- rare4 rule (rare4 task, Step 1) -- see module docstring.
        # Reuses nonjet4's own reject mask (n_lepton_bjet, nonjet4_keep_mask
        # -- identical N>4 rule, same accepted-event rows) and the NORMAL
        # version's own obj_record (built earlier, byte-for-byte
        # unmodified) -- rare4 keeps every object of a kept event, so it
        # is exactly obj_record restricted to the N<=4 rows, no re-
        # derivation of truncation/padding needed at all.
        rare4_keep_mask = nonjet4_keep_mask
        n_rejected_rare4 = n_rejected
        obj_record_rare4 = obj_record[rare4_keep_mask]
        assert len(obj_record_rare4) == n_after_gate - n_rejected_rare4, (
            f"rare4 rejection must remove exactly the N>4 events: "
            f"len(obj_record_rare4)={len(obj_record_rare4)} != "
            f"n_after_gate-n_rejected_rare4={n_after_gate - n_rejected_rare4}"
        )
        is_exclusive_selected_rare4 = is_exclusive_selected[rare4_keep_mask]

        rare4_incl_shard_path = output_dir / "dataset_shard_rare4_inclusive.sqlite"
        rare4_excl_shard_path = output_dir / "dataset_shard_rare4_exclusive.sqlite"
        for path in (rare4_incl_shard_path, rare4_excl_shard_path):
            if path.exists():
                path.unlink()
        writer_rare4_incl = SqliteArrayShardWriter(str(rare4_incl_shard_path))
        writer_rare4_excl = SqliteArrayShardWriter(str(rare4_excl_shard_path))

        rare4_funnel_result = run_combination_funnel(
            obj_record_rare4, is_exclusive_selected_rare4, job_tag, all_combinations, im_config, logger,
            writer_rare4_incl, writer_rare4_excl,
            # rare4 is the DELIVERED version: obj_record restricted to the
            # Version B (e+mu+b <= 4) rows, so the siblings take the same mask.
            mc_siblings=(mask_mc_siblings(mc_siblings_base, rare4_keep_mask)
                         if args.is_mc else None),
        )

        rare4_common_metadata = dict(common_metadata)
        rare4_common_metadata["object_truncation"] = "rare4"
        for writer in (writer_rare4_incl, writer_rare4_excl):
            for k, v in rare4_common_metadata.items():
                writer.set_metadata(k, v)
            writer.commit()
            writer.close()

        # "Hidden" cases (rare4 task, Step 1 spec): rejected (N>4) events
        # whose DISPLAY-CAPPED label (each object type's count capped at
        # 4, physics_calcs.limit_particles_in_fs's own convention -- the
        # SAME one the normal version's own final-state labels already
        # use) would read e+m+b<=4, masking the true N>4 rejection --
        # e.g. 5 muons/0 electrons/0 b-jets displays as "4m..." (capped
        # digit sum 4, not >4). Reuses the rejected-event e/m/b arrays
        # already computed above for nonjet4's own composition diagnostic
        # (same rejected-event set, same counts).
        capped_e_rej = np.minimum(n_e_rej, 4)
        capped_m_rej = np.minimum(n_m_rej, 4)
        capped_b_rej = np.minimum(n_b_rej, 4)
        n_hidden_cases = int(((capped_e_rej + capped_m_rej + capped_b_rej) <= 4).sum())

        if args.population == "matched4" and args.debug_event_dump:
            # B2: one row per ACCEPTED event, so the pilot can be checked at
            # event level. Off by default (not written in production).
            rare4_labels_full = np.full(n_after_gate, "VERSION_B_REJECTED", dtype=object)
            rare4_labels_full[rare4_keep_mask] = exact_final_state_labels(obj_record_rare4)
            dump_path = output_dir / "debug_events.csv"
            with open(dump_path, "w", encoding="utf-8", newline="") as fh:
                fh.write("run,luminosityBlock,event,dataset,"
                         + ",".join(f"acc_{l}" for l in DELIVERY_VETO_ORDER_4)
                         + ",exclusive,final_state,n_electrons_removed\n")
                runs = ak.to_numpy(events_triggered.run[keep]).tolist()
                lumis = ak.to_numpy(events_triggered.luminosityBlock[keep]).tolist()
                evts = ak.to_numpy(events_triggered.event[keep]).tolist()
                accs = [acceptances[l]["accepted"][keep].tolist() for l in DELIVERY_VETO_ORDER_4]
                excl = is_exclusive_selected.tolist()
                nrem = n_electrons_removed[keep].tolist()
                for i in range(n_after_gate):
                    fh.write(f"{runs[i]},{lumis[i]},{evts[i]},{dataset_label},"
                             + ",".join("1" if accs[j][i] else "0"
                                        for j in range(len(DELIVERY_VETO_ORDER_4)))
                             + f",{1 if excl[i] else 0},{rare4_labels_full[i]},{nrem[i]}\n")
            print(f"[{dataset_label}] wrote per-event debug dump: {dump_path} "
                  f"({n_after_gate} rows)", flush=True)

        rare4_diagnostics = {
            "n_accepted_events_before_rare4_rule": n_after_gate,
            "n_rejected_gt4_lepton_bjet": n_rejected_rare4,
            "n_kept_le4_lepton_bjet": n_after_gate - n_rejected_rare4,
            "n_hidden_cases": n_hidden_cases,
            "rejected_N_distribution": rejected_N_distribution,
            "rejected_event_composition": rejected_event_composition,
            "n_fs_groups": rare4_funnel_result["n_fs_groups"],
            "n_signature_writes_inclusive": rare4_funnel_result["n_signature_writes_incl"],
            "n_signature_writes_exclusive": rare4_funnel_result["n_signature_writes_excl"],
            "n_values_written_inclusive": rare4_funnel_result["n_values_written_incl"],
            "n_values_written_exclusive": rare4_funnel_result["n_values_written_excl"],
            "max_signature_size_this_job": rare4_funnel_result["max_signature_size"],
            "n_capped_signatures": rare4_funnel_result["n_capped_signatures"],
            "final_state_label_event_counts_inclusive": rare4_funnel_result["label_event_counts_incl"],
            "final_state_label_event_counts_exclusive": rare4_funnel_result["label_event_counts_excl"],
            "skip_reason_totals": rare4_funnel_result["skip_reason_totals"],
        }

    elapsed = time.time() - t0
    incl_shard_size_mb = incl_shard_path.stat().st_size / (1024 * 1024)
    excl_shard_size_mb = excl_shard_path.stat().st_size / (1024 * 1024)

    metadata = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "git_commit": git_commit_hash(REPO_ROOT),
        "dataset_label": dataset_label,
        "record_id": args.record_id,
        "file_index": args.file_index,
        "file_url": file_url,
        "population": args.population,
        "own_trigger_paths": list(own_paths),
        "higher_priority_datasets": higher_priority,
        "n_read": n_read,
        "n_after_golden_json": n_after_golden_json,
        "n_after_trigger": n_after_trigger,
        "trigger_per_path": trigger_stats["per_path"],
        "n_after_gate": n_after_gate,
        "n_exclusive": n_exclusive,
        "n_vetoed_by_each_higher_dataset": n_vetoed_by_each_higher_dataset,
        "n_final_state_groups": n_fs_groups,
        "final_state_label_event_counts_inclusive": label_event_counts_incl,
        "final_state_label_event_counts_exclusive": label_event_counts_excl,
        "n_combinations_checked_per_group": len(all_combinations),
        "n_signature_writes_inclusive": n_signature_writes_incl,
        "n_signature_writes_exclusive": n_signature_writes_excl,
        "n_values_written_inclusive": n_values_written_incl,
        "n_values_written_exclusive": n_values_written_excl,
        "max_signature_size_this_job": max_signature_size,
        "n_capped_signatures": n_capped_signatures,
        "skip_reason_totals": skip_reason_totals,
        "inclusive_shard_size_mb": round(incl_shard_size_mb, 3),
        "exclusive_shard_size_mb": round(excl_shard_size_mb, 3),
        "elapsed_sec": elapsed,
        "diagnostics": diagnostics,
        "matching_diagnostics": matching_diagnostics,
        "matched4_diagnostics": matched4_diagnostics,
        "top4_diagnostics": top4_diagnostics,
        "nonjet4_diagnostics": nonjet4_diagnostics,
        "rare4_diagnostics": rare4_diagnostics,
    }
    if args.is_mc:
        # Added ONLY under --is-mc, so job_metadata.json on the data path is
        # key-for-key what it was before this round -- which Part B proves.
        metadata["mc_diagnostics"] = mc_diagnostics
        metadata["is_mc"] = True
        metadata["mc_runs_tree"] = mc_runs
        metadata["mc_file_sum_genweight_all_events"] = file_sum_genweight
        metadata["mc_sigma_w_self_check"] = mc_sigma_w_self_check(
            file_sum_genweight, mc_runs["gen_event_sumw"], n_read,
            mc_runs["gen_event_count"])
        metadata["mc_capped_signatures_rare4"] = (
            rare4_funnel_result.get("capped_signatures", {})
            if rare4_diagnostics is not None else {})
        metadata["mc_n_sibling_writes_rare4"] = (
            rare4_funnel_result.get("n_mc_sibling_writes", 0)
            if rare4_diagnostics is not None else 0)
    (output_dir / "job_metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    print(json.dumps({
        "dataset_label": dataset_label, "population": args.population, "n_read": n_read,
        "n_after_gate": n_after_gate, "n_exclusive": n_exclusive,
        "n_signature_writes_inclusive": n_signature_writes_incl,
        "n_signature_writes_exclusive": n_signature_writes_excl,
        "elapsed_sec": round(elapsed, 1),
    }, indent=2))
    print(f"[{dataset_label}] wrote {incl_shard_path}, {excl_shard_path}, and job_metadata.json "
          f"under {output_dir} ({elapsed:.1f}s elapsed)")


if __name__ == "__main__":
    main()
