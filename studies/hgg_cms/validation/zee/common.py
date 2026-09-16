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


# ===========================================================================
# Implementation task 6, follow-up (17 Sep 2026): energy-scale/resolution
# machinery -- unbinned weighted median/effective-sigma68 (correct for
# signed weights), and a Breit-Wigner (x) Crystal-Ball fit.
# ===========================================================================

PDG_MZ = 91.1876    # GeV, PDG world-average Z pole mass
PDG_GAMMA_Z = 2.4952  # GeV, PDG world-average Z width


def weighted_mode(values: np.ndarray, weights: np.ndarray, bin_width: float = 0.25,
                   lo: float = None, hi: float = None) -> float:
    """Mode = center of the tallest bin of a fine (0.25 GeV by default)
    weighted histogram -- a mode has no meaningful "unbinned" definition
    (a true empirical mode of continuous data is defined only via some
    smoothing/binning choice), so this is reported as a descriptive
    statistic alongside the fit peak and the (genuinely unbinned)
    sigma_eff68, not used for the pre-set PASS/FAIL criterion itself."""
    values = np.asarray(values)
    weights = np.asarray(weights)
    if lo is None:
        lo = float(values.min())
    if hi is None:
        hi = float(values.max())
    nbins = max(1, int(round((hi - lo) / bin_width)))
    counts, edges = np.histogram(values, bins=nbins, range=(lo, hi), weights=weights)
    i = np.argmax(counts)
    return float(0.5 * (edges[i] + edges[i + 1]))


def weighted_median(values: np.ndarray, weights: np.ndarray) -> float:
    """Exact weighted median: sort by value, find the value where the
    cumulative weight first reaches half the total signed sum. Well-
    defined for signed weights as long as the cumulative sum is
    reasonably monotonic in the bulk (true here -- only ~16% of DY events
    are negative-weight, all of constant magnitude, see
    energy_scale.py's own data check)."""
    values = np.asarray(values)
    weights = np.asarray(weights)
    order = np.argsort(values)
    v, w = values[order], weights[order]
    cw = np.cumsum(w)
    target = 0.5 * cw[-1]
    idx = np.searchsorted(cw, target)
    idx = min(idx, len(v) - 1)
    return float(v[idx])


def unbinned_effective_sigma68(values: np.ndarray, weights: np.ndarray = None) -> dict:
    """UNBINNED shortest-interval effective sigma68: the narrowest PHYSICAL
    mass window [lo, hi] (evaluated per event, not per histogram bin) whose
    events' summed weight reaches 68.3% of the total signed sum.
    sigma_eff68 = (hi - lo) / 2.

    Algorithm: binary search on the window WIDTH W. For a fixed W, "does
    some width-<=W window reach the target sum" is checked in O(n) with a
    two-pointer/searchsorted scan that only relies on `values` being
    sorted (always true) -- NOT on the weights being non-negative. This
    is deliberate: DY's amc@NLO genWeight is signed (~15.85% negative,
    see pileup.py/normalization_check.py docstrings), so any algorithm
    that assumes a monotonic cumulative sum (e.g. a plain two-pointer
    directly over the weight prefix, or minimizing event COUNT instead of
    mass WIDTH) is wrong in general and was found to silently return the
    wrong window on real (dense, non-uniform) data -- see the git history
    for this function: an earlier "shortest subarray with sum >= target"
    deque formulation minimized event count, not mass width, and those
    two are NOT the same thing for a non-uniform density (verified to
    overshoot true sigma by >2x on a large unweighted Gaussian, where the
    correct answer is unambiguous: the count- and width-minimizing
    windows coincide only by coincidence, not by construction).
    "Does W work" is itself monotonic in W (a window achieving the target
    at width W0 still qualifies at any width >= W0), which is what makes
    the binary search valid.

    Returns {"sigma_eff68", "window_lo", "window_hi", "window_n_events"}.
    """
    values = np.asarray(values, dtype=float)
    if weights is None:
        weights = np.ones_like(values)
    weights = np.asarray(weights, dtype=float)

    order = np.argsort(values)
    v = values[order]
    w = weights[order]
    n = len(v)
    total = w.sum()
    if total <= 0 or n < 4:
        return {"sigma_eff68": None, "window_lo": None, "window_hi": None, "window_n_events": None}
    target = 0.683 * total

    prefix = np.concatenate([[0.0], np.cumsum(w)])  # prefix[k] = sum of first k weights
    idx = np.arange(n)

    def best_window_for_width(width):
        # j_end[lo] = number of elements with value <= v[lo] + width
        # (side='right': all elements <= v[lo]+width sort before it).
        j_end = np.searchsorted(v, v + width, side="right")
        sums = prefix[j_end] - prefix[idx]
        best_lo = int(np.argmax(sums))
        return sums[best_lo], best_lo, int(j_end[best_lo])

    lo_w, hi_w = 0.0, float(v[-1] - v[0])
    best = None  # (lo_idx, j_idx) of the narrowest width verified to reach target
    best_sum, best_lo_idx, best_j_idx = best_window_for_width(hi_w)
    if best_sum < target:
        # Even the full range doesn't reach 68.3% (can happen with net-
        # negative weight regions) -- fall back to the full range.
        best = (0, n)
    else:
        best = (best_lo_idx, best_j_idx)
        for _ in range(60):
            mid = 0.5 * (lo_w + hi_w)
            s, lo_idx, j_idx = best_window_for_width(mid)
            if s >= target:
                hi_w = mid
                best = (lo_idx, j_idx)
            else:
                lo_w = mid

    best_i, best_j = best
    if best_j <= best_i:
        return {"sigma_eff68": None, "window_lo": None, "window_hi": None, "window_n_events": None}

    lo = v[best_i]
    hi = v[best_j - 1]
    width = hi - lo
    return {
        "sigma_eff68": float(width / 2.0),
        "window_lo": float(lo), "window_hi": float(hi),
        "window_n_events": int(best_j - best_i),
    }


def crystal_ball_pdf(x: np.ndarray, mu: float, sigma: float, alpha: float, n: float) -> np.ndarray:
    """Standard normalized (single-sided) Crystal Ball PDF: Gaussian core
    for (x-mu)/sigma > -|alpha|, power-law tail below (the conventional
    "low-mass radiative tail" orientation). alpha>0, n>1 required for a
    normalizable tail."""
    from scipy.special import erf
    x = np.asarray(x, dtype=float)
    t = (x - mu) / sigma
    a = abs(alpha)
    A = (n / a) ** n * np.exp(-a ** 2 / 2.0)
    B = n / a - a
    C = (n / a) / (n - 1.0) * np.exp(-a ** 2 / 2.0)
    D = np.sqrt(np.pi / 2.0) * (1.0 + erf(a / np.sqrt(2.0)))
    norm = 1.0 / (sigma * (C + D))
    core = t > -a
    out = np.empty_like(t)
    out[core] = norm * np.exp(-0.5 * t[core] ** 2)
    tail_base = np.maximum(B - t[~core], 1e-6)  # guard against a non-physical excursion during fitting
    out[~core] = norm * A * tail_base ** (-n)
    return out


def breit_wigner_pdf(x: np.ndarray, M: float, Gamma: float, xlo: float, xhi: float, n_grid: int = 4000) -> np.ndarray:
    """Relativistic Breit-Wigner mass lineshape, 1/((x^2-M^2)^2+M^2*Gamma^2),
    normalized by numerical integration over [xlo, xhi] (truncated -- the
    BW's own tails are broad, but this fit only ever needs it inside a
    bounded convolution-integration range, never analytically to +-inf)."""
    x = np.asarray(x, dtype=float)
    grid = np.linspace(xlo, xhi, n_grid)
    bw_grid = 1.0 / ((grid ** 2 - M ** 2) ** 2 + (M * Gamma) ** 2)
    norm = np.trapz(bw_grid, grid)
    return (1.0 / ((x ** 2 - M ** 2) ** 2 + (M * Gamma) ** 2)) / norm


def bw_conv_cb_template(x_eval: np.ndarray, mu: float, sigma: float, alpha: float, n: float,
                         M_Z: float = PDG_MZ, Gamma_Z: float = PDG_GAMMA_Z,
                         xprime_lo: float = 40.0, xprime_hi: float = 160.0,
                         n_xprime: int = 500) -> np.ndarray:
    """(BW convolved with CB)(x_eval) = integral of BW(x') * CB(x_eval-x')
    dx' over x' in [xprime_lo, xprime_hi], computed by direct numerical
    (trapezoidal) integration on a fine grid -- NOT FFT-based, deliberately:
    FFT convolution needs careful index/offset bookkeeping to correctly
    align the physical x-axis, which is easy to get subtly wrong; this
    direct double-sum (vectorized via broadcasting: an len(x_eval) x
    n_xprime matrix) is slower but unambiguous and easy to verify, and
    still fast enough here (a few thousand points, called repeatedly by
    curve_fit -- each call is a few ms)."""
    x_eval = np.asarray(x_eval, dtype=float)
    xprime = np.linspace(xprime_lo, xprime_hi, n_xprime)
    bw = breit_wigner_pdf(xprime, M_Z, Gamma_Z, xprime_lo, xprime_hi, n_grid=n_xprime)
    diff = x_eval[:, None] - xprime[None, :]
    cb = crystal_ball_pdf(diff.ravel(), mu, sigma, alpha, n).reshape(diff.shape)
    return np.trapz(cb * bw[None, :], xprime, axis=1)


def fit_bw_conv_cb(mee: np.ndarray, weights: np.ndarray, lo: float, hi: float,
                    bin_width: float = 0.5, mc_samples: int = 150, seed: int = 20260917) -> dict:
    """Binned chi-square fit of A * (BW(x; PDG_MZ, PDG_GAMMA_Z) (x) CB(x; mu,
    sigma, alpha, n)) to the (weighted) mee histogram over [lo, hi]. M_Z
    and Gamma_Z are FIXED to their PDG values (per this task's own
    instruction) -- only the CB's mu (extra offset on top of M_Z),
    sigma (detector-resolution width), alpha, n, and an overall
    normalization A are free.

    Returns fitted params + covariance, the FITTED PEAK (found by scanning
    the fitted template's own maximum -- not assumed equal to M_Z+mu,
    since the BW(x)CB convolution is not symmetric), its Monte-Carlo
    parameter-covariance uncertainty, sigma (=CB's own sigma) +
    uncertainty, and the fit's own chi2/ndf.
    """
    from scipy.optimize import curve_fit

    mee = np.asarray(mee, dtype=float)
    weights = np.asarray(weights, dtype=float)
    bins = np.arange(lo, hi + bin_width, bin_width)
    centers = 0.5 * (bins[:-1] + bins[1:])
    counts, _ = np.histogram(mee, bins=bins, weights=weights)
    counts_w2, _ = np.histogram(mee, bins=bins, weights=weights ** 2)
    errs = np.sqrt(np.maximum(counts_w2, np.finfo(float).tiny))

    total_w = weights.sum()

    def model(x, A, mu, sigma, alpha, n):
        return A * bw_conv_cb_template(x, mu, sigma, alpha, n)

    p0 = [total_w * bin_width, 0.0, 2.0, 1.5, 4.0]
    bounds = (
        [0.0, -10.0, 0.3, 0.3, 1.05],
        [np.inf, 10.0, 12.0, 10.0, 80.0],
    )
    popt, pcov = curve_fit(
        model, centers, counts, p0=p0, sigma=errs, absolute_sigma=True,
        bounds=bounds, maxfev=30000,
    )

    fine_x = np.linspace(lo, hi, 1201)
    fine_y = model(fine_x, *popt)
    peak = float(fine_x[np.argmax(fine_y)])

    rng = np.random.default_rng(seed)
    try:
        samples = rng.multivariate_normal(popt, pcov, size=mc_samples)
    except np.linalg.LinAlgError:
        samples = np.tile(popt, (mc_samples, 1))
    peaks = []
    for s in samples:
        y = model(fine_x, *s)
        peaks.append(fine_x[np.argmax(y)])
    peak_unc = float(np.std(peaks))

    resid = (counts - model(centers, *popt)) / errs
    chi2 = float(np.sum(resid ** 2))
    ndf = len(centers) - len(popt)

    return {
        "params": {"A": float(popt[0]), "mu": float(popt[1]), "sigma": float(popt[2]),
                   "alpha": float(popt[3]), "n": float(popt[4])},
        "param_errs": {k: float(np.sqrt(pcov[i, i])) for i, k in enumerate(["A", "mu", "sigma", "alpha", "n"])},
        "peak_GeV": peak, "peak_uncertainty_GeV": peak_unc,
        "sigma_GeV": float(popt[2]), "sigma_uncertainty_GeV": float(np.sqrt(pcov[2, 2])),
        "chi2": chi2, "ndf": ndf, "chi2_over_ndf": chi2 / ndf if ndf > 0 else None,
        "fit_window": [lo, hi], "bin_width": bin_width,
        "M_Z_fixed": PDG_MZ, "Gamma_Z_fixed": PDG_GAMMA_Z,
    }
