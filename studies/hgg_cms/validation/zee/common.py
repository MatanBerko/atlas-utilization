"""
Implementation task 6, Part 4 (REVISED 16 Sep 2026): shared helpers for
the Z->e+e- offline analysis (studies/hgg_cms/validation/zee/). These
scripts CANNOT be run yet -- no Z->ee cluster run has happened (this task
prepares, does not submit). Written and unit-tested against synthetic
fixtures now so they are ready to run the moment
studies/hgg_cms/cluster/merge_zee_outputs.py produces real merged output.

NO BLINDING LOGIC in any loader here. As established in
studies/hgg_cms/zee_selection.py's own module docstring: this sample's
leading pair is built from electronVeto==False photons, structurally
disjoint from the H->gamma-gamma main analysis's own electronVeto==True
candidate -- even though the stored window (60-180 GeV) numerically
overlaps the H->gamma-gamma blind window (115-135 GeV), this is not
H->gamma-gamma signal-region data. The output field is "m_ee" (never
"m_gg") specifically so it can never be conflated with it.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import awkward as ak
import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT))

from studies.hgg_cms.validation.common import (  # noqa: E402
    LUMI_FB, weighted_mode_and_sigma68,
)

DEFAULT_MERGED_ZEE_DIR = os.environ.get(
    "HGG_ZEE_MERGED_DIR", r"C:\Users\matan\hgg_zee_merged"
)

CATEGORIES = ["EBEB", "notEBEB"]

# ---- Trigger bit field names in the merged output (see
# run_zee_selection_on_chunks.py's TRIGGER_BIT_OUTPUT_FIELDS) ----
ELE27_FIELD = "passes_ele27_hlt"
DIPHOTON_FIELD = "passes_diphoton_hlt"

# ---- Offline sub-window cuts (see studies.hgg_cms.zee_selection's own
# ENERGY_SCALE_MASS_LO/HI, TRIGGER_EFF_MASS_LO -- duplicated here as
# plain floats so this package has no import-time dependency on the
# cluster driver module). ----
ENERGY_SCALE_MASS_LO, ENERGY_SCALE_MASS_HI = 70.0, 110.0
TRIGGER_EFF_MASS_LO = 95.0

# ---- Part 4, item 2(a): PRE-SET agreement criteria, stated here AND in
# ZEE_RUN_README.md BEFORE any results exist (no pilot has run). Do not
# change these after seeing results. ----
PEAK_POSITION_AGREEMENT_REL_TOL = 0.005   # 0.5% relative
SIGMA_EFF_AGREEMENT_REL_TOL = 0.10        # 10% relative

# ---- Part 4, item 3: DY cross section, cited (not independently
# re-derived from an NNLO calculation -- same citation convention as
# signal_sumw_notes.md's ZH entry). 6077.22 pb is the standard NNLO cross
# section widely used across public CMS Run 2 Ultra Legacy analysis
# frameworks for EXACTLY this dataset name,
# DYJetsToLL_M-50_TuneCP5_13TeV-amcatnloFXFX-pythia8 (record 35669) --
# confirmed via the PocketCoffea analysis framework's own dataset
# cross-section tables (https://pocketcoffea.readthedocs.io/en/stable/
# datasets.html) referencing this exact sample name at 6077.22 pb;
# cross-checked for consistency (same process, same order of magnitude,
# different tune/era so not identical) against the RazorAnalyzer public
# xSections.dat table's TuneCUETP8M1-era value (1921.8*3 = 5765.4 pb --
# tune does not change the hard-process cross section). The CERN Open
# Data portal's own record 35669 metadata does NOT itself state a cross
# section (checked directly, 16 Sep 2026) -- this value is therefore
# UNVERIFIED beyond the citation above, not independently re-derived from
# a first-principles NNLO/FEWZ calculation in this task.
DY_CROSS_SECTION_PB = 6077.22


def merged_zee_dir() -> Path:
    d = Path(DEFAULT_MERGED_ZEE_DIR)
    if not d.exists():
        raise FileNotFoundError(
            f"merged Z->ee output directory not found: {d} -- set "
            f"HGG_ZEE_MERGED_DIR to the folder you copied hgg_zee/merged/"
            f"*.root into (see ZEE_RUN_README.md)."
        )
    return d


def load_zee_data() -> ak.Array:
    import uproot
    return uproot.open(str(merged_zee_dir() / "zee_data.root"))["events"].arrays(library="ak")


def load_zee_dy() -> ak.Array:
    import uproot
    return uproot.open(str(merged_zee_dir() / "zee_dy.root"))["events"].arrays(library="ak")


def category_mask(cat: np.ndarray, which: str) -> np.ndarray:
    cat = np.asarray(cat)
    if which == "EBEB":
        return cat == "EBEB"
    if which == "notEBEB":
        return cat != "EBEB"
    raise ValueError(which)


def energy_scale_selection_mask(arr: ak.Array) -> np.ndarray:
    """2(a): Ele27-fired events, 70-110 GeV. Clean of the Mass90-
    sculpting bug by construction -- Ele27 firing has nothing to do with
    the diphoton trigger's own online mass cut, regardless of whether the
    diphoton bit ALSO happened to fire for the same event."""
    ele27 = ak.to_numpy(arr[ELE27_FIELD]).astype(bool)
    mee = ak.to_numpy(arr["m_ee"])
    return ele27 & (mee > ENERGY_SCALE_MASS_LO) & (mee < ENERGY_SCALE_MASS_HI)


def trigger_eff_probe_mask(arr: ak.Array) -> np.ndarray:
    """2(b): Ele27-fired events with offline mass > 95 GeV (comfortably
    above the diphoton trigger's own online Mass90 threshold's turn-on
    region, so this probe sample's SIZE isn't itself biased by that
    trigger)."""
    ele27 = ak.to_numpy(arr[ELE27_FIELD]).astype(bool)
    mee = ak.to_numpy(arr["m_ee"])
    return ele27 & (mee > TRIGGER_EFF_MASS_LO)


def diphoton_only_mask(arr: ak.Array) -> np.ndarray:
    """2(c): the Mass90-sculpting DEMONSTRATION sample -- events where the
    diphoton trigger fired but Ele27 did NOT (so this is exactly the
    population that would have been silently biased by the earlier,
    buggy diphoton-trigger-only design), 70-110 GeV."""
    diphoton = ak.to_numpy(arr[DIPHOTON_FIELD]).astype(bool)
    ele27 = ak.to_numpy(arr[ELE27_FIELD]).astype(bool)
    mee = ak.to_numpy(arr["m_ee"])
    return diphoton & (~ele27) & (mee > ENERGY_SCALE_MASS_LO) & (mee < ENERGY_SCALE_MASS_HI)


def peak_and_width(mee: np.ndarray, weights: np.ndarray = None) -> tuple:
    """Peak (mode) and sigma_eff68 over a 60-180-scale window, reusing
    the same weighted, binned method as the main analysis's validation
    package (see studies.hgg_cms.validation.common.weighted_mode_and_sigma68's
    own docstring for why binned-and-weighted, not a naive weighted
    quantile, is used -- genWeight can be negative for the amc@NLO DY
    sample)."""
    mee = np.asarray(mee)
    if weights is None:
        weights = np.ones_like(mee)
    return weighted_mode_and_sigma68(mee, weights, bin_width=0.5, lo=60.0, hi=120.0)


def relative_difference(a: float, b: float) -> float:
    """(a-b)/b -- used for the 0.5%/10% pre-set agreement checks."""
    if b == 0:
        return float("nan")
    return (a - b) / b
