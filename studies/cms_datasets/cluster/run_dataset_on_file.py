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
from services.parsing.validated_runs import ValidatedRunsFilter, apply_validated_runs_filter  # noqa: E402
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


def read_events(file_url: str, required_branches):
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
    return ak.concatenate(chunks) if len(chunks) > 1 else chunks[0]


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
    num_events = len(obj_record)
    zero_array = ak.Array([0] * num_events) if num_events > 0 else ak.Array([])
    particle_counts = ak.num(obj_record)

    # upstream-names task, (1): build the label from the CONFIGURED object
    # types only, in upstream's own fixed order, exactly as upstream's
    # services/calculations/im_calculator.py:_get_all_events_fs and
    # services/calculations/physics_calcs.py:group_by_final_state do at
    # upstream commit 88d7a4b -- same tuple, same order, same "present in
    # events.fields" filter, same "_" separator, same f"{count}{letter}".
    # Our obj_record (studies.m0m1j0_cms.selection.build_object_record)
    # carries exactly Electrons/Muons/Jets/BJets, so this yields e.g.
    # "0e_2m_5j_1b" -- no photon or tau field, hence no "0g"/"0t" token.
    present_types = [
        (name, letter, ak.to_numpy(getattr(particle_counts, name, zero_array)))
        for name, letter in FINAL_STATE_OBJECTS
        if name in obj_record.fields
    ]

    all_events_fs = np.array([
        "_".join(
            f"{count}{letter}"
            for (_name, letter, _values), count in zip(present_types, counts)
        )
        for counts in zip(*[values for _name, _letter, values in present_types])
    ])
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
    `trigobj`/`sel_muons` -- never writes to or filters either input."""
    trig_muon_mask = (trigobj.id == TRIGOBJ_MUON_ID) & ((trigobj.filterBits & required_bit) != 0)
    trig_muons = trigobj[trig_muon_mask]
    mu_p4 = _p4_no_mass_needed(sel_muons)
    trig_p4 = _p4_no_mass_needed(trig_muons)
    pairs_mu, pairs_trig = ak.unzip(ak.cartesian([mu_p4, trig_p4], nested=True))
    dr = pairs_mu.deltaR(pairs_trig)
    within = dr < dr_max
    candidate_pt = ak.where(within, pairs_trig.pt, -np.inf)
    best_pt = ak.max(candidate_pt, axis=-1)
    return ak.fill_none(best_pt, -np.inf)


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
                             writer_incl: SqliteArrayShardWriter, writer_excl: SqliteArrayShardWriter) -> dict:
    """The exact combination/shard-writing funnel that used to be main()'s
    own inline for-loop, extracted verbatim (top-4 task, Step 1) so it can
    be called a SECOND time on a top-4-truncated obj_record without
    duplicating ~90 lines of code. Called with the UNCHANGED obj_record
    (generic/v0/matched-normal), this produces byte-for-byte the same
    shards and stats as before the refactor (Hard Rule 5) -- nothing about
    the logic below differs from the pre-refactor inline version."""
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

    for label, fs_events, group_mask in _group_by_final_state_with_mask(obj_record):
        n_fs_groups += 1
        n_this_group = len(fs_events)
        label_event_counts_incl[label] = label_event_counts_incl.get(label, 0) + n_this_group
        writer_incl.record_final_state_count(label, n_this_group)

        fs_is_exclusive = is_exclusive_selected[group_mask]
        n_excl_this_group = int(fs_is_exclusive.sum())
        label_event_counts_excl[label] = label_event_counts_excl.get(label, 0) + n_excl_this_group
        writer_excl.record_final_state_count(label, n_excl_this_group)

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

            writer_incl.append_array(signature, arr)
            n_signature_writes_incl += 1
            n_values_written_incl += int(arr.size)

            excl_arr = arr[combo_is_exclusive]
            if excl_arr.size > 0:
                writer_excl.append_array(signature, excl_arr)
                n_signature_writes_excl += 1
                n_values_written_excl += int(excl_arr.size)

    return {
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
    p.add_argument("--dataset-label", required=True, choices=list(TRIGGER_PATHS_BY_DATASET.keys()))
    p.add_argument("--record-id", type=int, required=True)
    p.add_argument("--file-index", type=int, required=True)
    p.add_argument("--output-dir", required=True)
    p.add_argument("--population", choices=["generic", "v0", "matched"], default="generic")
    p.add_argument("--validated-runs-json", default=DEFAULT_VALIDATED_RUNS_JSON)
    args = p.parse_args()

    logging.basicConfig(level=logging.WARNING, format="%(asctime)s %(levelname)s %(message)s")
    logger = logging.getLogger("run_dataset_on_file")

    dataset_label = args.dataset_label
    if dataset_label == "SingleMuon" and args.population == "matched":
        # Matched mode's SingleMuon trigger set is HLT_IsoMu24 ONLY (Maryna's
        # explicit instruction, TRIGGER_MATCHING_SPEC.md Section 4) --
        # generic/v0's SingleMuon trigger set (both IsoMu24 and IsoTkMu24,
        # from TRIGGER_PATHS_BY_DATASET) is untouched (Hard Rule 5); this
        # override only ever fires for population=="matched".
        own_paths = SINGLEMUON_MATCHED_TRIGGER_PATHS
    else:
        own_paths = TRIGGER_PATHS_BY_DATASET[dataset_label]
    higher_priority = VETO_ORDER[:VETO_ORDER.index(dataset_label)]
    veto_paths_by_label = {h: TRIGGER_PATHS_BY_DATASET[h] for h in higher_priority}

    all_trigger_branches = list(own_paths)
    for paths in veto_paths_by_label.values():
        all_trigger_branches.extend(paths)
    required_branches = list(BASE_OBJECT_BRANCHES) + sorted(set(all_trigger_branches))
    if args.population == "matched":
        required_branches = list(required_branches) + list(MATCHED_MODE_EXTRA_BRANCHES)

    t0 = time.time()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    file_url = resolve_file_url(args.record_id, args.file_index)
    print(f"[{dataset_label}] resolved record {args.record_id} file index {args.file_index} -> {file_url}", flush=True)

    events = read_events(file_url, required_branches)
    n_read = len(events)
    print(f"[{dataset_label}] read {n_read} events", flush=True)

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
    if args.population == "matched":
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
        "top4_diagnostics": top4_diagnostics,
        "nonjet4_diagnostics": nonjet4_diagnostics,
        "rare4_diagnostics": rare4_diagnostics,
    }
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
