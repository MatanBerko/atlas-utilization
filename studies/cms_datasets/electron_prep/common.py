#!/usr/bin/env python
"""
Shared helpers for the electron-dataset PREPARATION study.

PREPARATION ONLY. Nothing in this package is part of the production
pipeline: `studies/cms_datasets/cluster/run_dataset_on_file.py`, the
delivery builders and every delivered file are untouched. These scripts
only READ, and they import the production object-selection functions
unchanged so that electrons, muons and jets mean exactly what
`studies/m0m1j0_cms/RECIPE.md` says they mean.

What is imported unchanged (never redefined here):
  studies.m0m1j0_cms.selection.select_muons / select_electrons /
      select_and_split_jets
  studies.cms_datasets.cluster.run_dataset_on_file.resolve_file_url /
      read_events / _p4_no_mass_needed / MATCH_DR_MAX
  services.parsing.validated_runs.ValidatedRunsFilter /
      apply_validated_runs_filter
  services.parsing.trigger_requirements.apply_trigger_requirement
  studies.cms_datasets.cluster.datasets_records.DATASETS

The ONE thing re-implemented here is `trigobj_best_match_pt`, because the
production version hard-codes `TRIGOBJ_MUON_ID` (13) and this study has to
match ELECTRON trigger objects (id 11) as well. The formula below is the
production one copied verbatim -- same bit test, same `ak.cartesian`
pairing, same `dR < MATCH_DR_MAX`, same "best = highest online pT",
same `-inf` for "no match" -- with the object id as a parameter instead of
a constant. `assert_matcher_agrees_with_production` checks at runtime that
the two give identical answers for id 13, so this copy cannot drift.
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import awkward as ak  # noqa: E402
import numpy as np  # noqa: E402
import uproot  # noqa: E402

from studies.m0m1j0_cms import selection  # noqa: E402
from studies.cms_datasets.cluster import run_dataset_on_file as drv  # noqa: E402
from studies.cms_datasets.cluster.datasets_records import DATASETS  # noqa: E402
from services.parsing.validated_runs import (  # noqa: E402
    ValidatedRunsFilter, apply_validated_runs_filter,
)
from services.parsing.trigger_requirements import apply_trigger_requirement  # noqa: E402

TRIGOBJ_ELECTRON_ID = 11
TRIGOBJ_MUON_ID = 13
MATCH_DR_MAX = drv.MATCH_DR_MAX  # 0.1, the settled muon-side criterion

# Electron filterBits, from the TrigObj_filterBits branch TITLE inside the
# real UL2016 NanoAODv9 files (see read_trigobj_titles.py and
# evidence/trigobj_titles_electron_datasets.json -- NEVER from memory).
BIT_E_CALOIDL_TRACKIDL_ISOVL = 1      # "1 = CaloIdL_TrackIdL_IsoVL"
BIT_E_WPTIGHT = 2                     # "2 = 1e (WPTight)"
BIT_E_2E = 16                         # "16 = 2e"
BIT_E_1E1MU = 32                      # "32 = 1e-1mu"
# Muon filterBits (same source).
BIT_MU_TRKISOVVL = 1                  # "1 = TrkIsoVVL"
BIT_MU_ISO = 2                        # "2 = Iso"

TRIGOBJ_BRANCHES = (
    "nTrigObj", "TrigObj_pt", "TrigObj_eta", "TrigObj_phi",
    "TrigObj_id", "TrigObj_filterBits",
)

DEFAULT_VALIDATED_RUNS_JSON = REPO_ROOT / drv.DEFAULT_VALIDATED_RUNS_JSON


def dataset_by_label(label: str):
    for d in DATASETS:
        if d.label == label:
            return d
    raise KeyError(f"unknown dataset label {label!r}")


def record_for(label: str, era: str) -> int:
    d = dataset_by_label(label)
    return d.record_g if era == "G" else d.record_h


def zip_trigobj(events: ak.Array) -> ak.Array:
    return ak.zip({
        "pt": events.TrigObj_pt, "eta": events.TrigObj_eta,
        "phi": events.TrigObj_phi, "id": events.TrigObj_id,
        "filterBits": events.TrigObj_filterBits,
    })


def trigobj_best_match_pt(objs: ak.Array, trigobj: ak.Array, obj_id: int,
                          required_bit: int, dr_max: float = MATCH_DR_MAX) -> ak.Array:
    """For each selected offline object (per event, jagged), the highest
    online pT among TrigObj entries with `id == obj_id`,
    `filterBits & required_bit != 0`, within dR < dr_max -- or -inf.

    Copied verbatim from run_dataset_on_file.trigobj_best_match_pt with the
    object id turned into a parameter; see this module's docstring.
    """
    trig_mask = (trigobj.id == obj_id) & ((trigobj.filterBits & required_bit) != 0)
    trig_sel = trigobj[trig_mask]
    obj_p4 = drv._p4_no_mass_needed(objs)
    trig_p4 = drv._p4_no_mass_needed(trig_sel)
    pairs_obj, pairs_trig = ak.unzip(ak.cartesian([obj_p4, trig_p4], nested=True))
    dr = pairs_obj.deltaR(pairs_trig)
    within = dr < dr_max
    candidate_pt = ak.where(within, pairs_trig.pt, -np.inf)
    best_pt = ak.max(candidate_pt, axis=-1)
    return ak.fill_none(best_pt, -np.inf)


def assert_matcher_agrees_with_production(muons: ak.Array, trigobj: ak.Array,
                                          required_bit: int = BIT_MU_TRKISOVVL) -> None:
    """Runtime proof that the id-parameterised copy above is the production
    function for the muon case it was copied from."""
    mine = trigobj_best_match_pt(muons, trigobj, TRIGOBJ_MUON_ID, required_bit)
    theirs = drv.trigobj_best_match_pt(muons, trigobj, required_bit)
    a = ak.to_numpy(ak.flatten(mine, axis=None))
    b = ak.to_numpy(ak.flatten(theirs, axis=None))
    assert a.shape == b.shape and np.array_equal(a, b), (
        "the id-parameterised matcher disagrees with "
        "run_dataset_on_file.trigobj_best_match_pt for id==13; it has drifted"
    )


def select_objects(events: ak.Array):
    """The production object selection, imported unchanged."""
    muons = selection.select_muons(events)
    electrons = selection.select_electrons(events)
    jets = selection.select_and_split_jets(events, muons, electrons)
    return muons, electrons, jets


def read_file(record_id: int, file_index: int, branches, apply_golden: bool = True):
    """Resolve, read (chunked, with retry) and golden-JSON-filter one file.

    Uses the production `resolve_file_url` / `read_events` and the
    production golden-JSON filter, so the event population here is the same
    one the data pipeline would see.
    """
    url = drv.resolve_file_url(record_id, file_index)
    events = drv.read_events(url, list(branches))
    n_read = len(events)
    if apply_golden:
        vr = ValidatedRunsFilter(str(DEFAULT_VALIDATED_RUNS_JSON))
        events, stats = apply_validated_runs_filter(events, vr)
        n_golden = stats["n_after"]
    else:
        n_golden = n_read
    return url, events, {"n_read": n_read, "n_after_golden_json": n_golden}


def fire_mask(events: ak.Array, paths) -> np.ndarray:
    """Event-level OR over a set of HLT path branches."""
    m = np.zeros(len(events), dtype=bool)
    for p in paths:
        m |= ak.to_numpy(events[p]).astype(bool)
    return m


def clopper_pearson(k: np.ndarray, n: np.ndarray, cl: float = 0.68):
    """Clopper-Pearson interval at confidence level `cl` (default 68%).

    Exact binomial interval via the Beta quantile relation; k==0 and k==n
    are handled at the boundaries, where one side is exactly 0 or 1.
    """
    from scipy.stats import beta
    k = np.asarray(k, dtype=float)
    n = np.asarray(n, dtype=float)
    alpha = 1.0 - cl
    lo = np.where(k > 0, beta.ppf(alpha / 2, k, np.maximum(n - k + 1, 1e-12)), 0.0)
    hi = np.where(k < n, beta.isf(alpha / 2, k + 1, np.maximum(n - k, 1e-12)), 1.0)
    with np.errstate(invalid="ignore", divide="ignore"):
        p = np.where(n > 0, k / n, np.nan)
    lo = np.where(n > 0, lo, np.nan)
    hi = np.where(n > 0, hi, np.nan)
    return p, lo, hi


# ECAL barrel / endcap, with the documented transition ("gap") region
# between them reported separately and flagged, never silently merged.
BARREL_ETA_MAX = 1.4442
ENDCAP_ETA_MIN = 1.566


def eta_region(abs_eta: np.ndarray) -> np.ndarray:
    """'barrel' | 'gap' | 'endcap' | 'outside' per entry."""
    out = np.full(abs_eta.shape, "outside", dtype=object)
    out[abs_eta < BARREL_ETA_MAX] = "barrel"
    out[(abs_eta >= BARREL_ETA_MAX) & (abs_eta <= ENDCAP_ETA_MIN)] = "gap"
    out[(abs_eta > ENDCAP_ETA_MIN) & (abs_eta < selection.ELECTRON_ETA_MAX)] = "endcap"
    return out


# Efficiency binning: 1 GeV from 25 to 40, then coarser to 200.
TURNON_BIN_EDGES = np.concatenate([
    np.arange(25.0, 40.0 + 1e-9, 1.0),
    np.array([42.0, 45.0, 50.0, 60.0, 80.0, 100.0, 140.0, 200.0]),
])
