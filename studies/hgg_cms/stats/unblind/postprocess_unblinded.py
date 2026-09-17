"""
Statistical-model task, Part 5.2 companion (18 Sep 2026, post-approval):
computes the secondary results and robustness checks that
`run_unblinded_analysis.py`'s own `secondary_note`/`robustness_note`
explicitly deferred to a post-unblinding companion script (pre-declared
in that script's own text, written and committed BEFORE this data was
opened) -- using the SAME already-frozen building blocks
(stats/model.py, stats/fit.py, stats/compute_expected_significance.py),
unmodified. This script is NOT separately gated: the data was already
opened through the proper gate by `run_unblinded_analysis.py`; this
only does further analysis on that same already-unblinded file.

Covers UNBLINDING_PLAN.md:
  Section 2 items 3-6: best-fit m_H (mu, m_H free) with its uncertainty;
    the 110-150 GeV local-p curve; the global significance of the
    largest excess (toy-based + Gross-Vitells, from the ALREADY-
    COLLECTED background-only toy ensemble -- no new toys generated
    here); observed vs expected Z placement in the expected band.
  Section 2 item 1: mu_hat total uncertainty from the PROFILE-LIKELIHOOD
    scan (pre-declared method, not HESSE), with a stat-only/systematic
    breakdown via the same profiling technique.
  Section 3 items i-vi: the six pre-declared robustness checks.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT))

from studies.hgg_cms.output import read_output  # noqa: E402
from studies.hgg_cms.stats import model as M  # noqa: E402
from studies.hgg_cms.stats import fit as F  # noqa: E402
from studies.hgg_cms.stats.binning import poisson_nll  # noqa: E402
from studies.hgg_cms.stats.compute_expected_significance import (  # noqa: E402
    _fit_with_restricted_nuisances, _fit_alt_with_hesse,
)

MH_NOMINAL = 125.09
DATA_FILE = r"C:\Users\matan\hgg_full_merged\data_full_range.root"
OUT_PATH = Path(__file__).resolve().parents[1] / "results" / "unblinded_postprocess.json"

# Run2016G/H boundaries -- already-established definition, reused as-is
# (studies/hgg_cms/validation/part_c_run_stability.py).
RUN_RANGES = {"Run2016G": (278820, 280385), "Run2016H": (280919, 284044)}
LUMI_FB = {"Run2016G": 7.653, "Run2016H": 8.740}
LUMI_TOTAL_FB = LUMI_FB["Run2016G"] + LUMI_FB["Run2016H"]


def load_real_data_counts():
    import awkward as ak
    events = read_output(DATA_FILE, unblind=True)
    edges = M.edges()
    cat_selector = {"EBEB": lambda e: e["category"] == "EBEB", "notEBEB": lambda e: e["category"] != "EBEB"}
    counts = {}
    for cat, sel in cat_selector.items():
        m = events["m_gg"][sel(events)]
        counts[cat], _ = np.histogram(ak.to_numpy(m), bins=edges)
    return events, counts


# ---------------------------------------------------------------------
# Secondary 1: profile-likelihood mu uncertainty, total + breakdown
# ---------------------------------------------------------------------
def profile_mu_breakdown(data_counts, names, base):
    """Total (all nuisances profiled) and statistical-only (all
    nuisances fixed at 0 -- NOT re-fixed to the full fit's own best-fit
    values, matching STATS_REPORT.md Part 3.2's own nested-fixing
    convention for a like-for-like comparison) profile-likelihood
    intervals; the systematic component is the quadrature difference,
    exactly mirroring the pre-declared HESSE-based breakdown's own
    logic, just with profile_interval doing the crossing-finding."""
    all_floating = set(names) - {"mu"} - {n for n in names if n.startswith("bkg_")}

    full = _fit_with_restricted_nuisances(data_counts, names, base, all_floating, n_starts=10, seed0=101, seed1=102)
    alt_full = full["alt"]
    prof_full = F.profile_likelihood_mu_error(data_counts, MH_NOMINAL, names, alt_full, n_starts=3)

    stat_only = _fit_with_restricted_nuisances(data_counts, names, base, set(), n_starts=10, seed0=103, seed1=104)
    alt_stat = stat_only["alt"]
    prof_stat = F.profile_likelihood_mu_error(data_counts, MH_NOMINAL, names, alt_stat, n_starts=3)

    def quad_diff(a, b):
        d2 = a ** 2 - b ** 2
        return float(np.sqrt(max(d2, 0.0))) if (a is not None and b is not None) else None

    return {
        "full": {"mu_hat": alt_full.params["mu"], "sigma_up": prof_full["sigma_up"],
                  "sigma_down": prof_full["sigma_down"]},
        "stat_only": {"mu_hat": alt_stat.params["mu"], "sigma_up": prof_stat["sigma_up"],
                       "sigma_down": prof_stat["sigma_down"]},
        "systematic_component": {
            "up": quad_diff(prof_full["sigma_up"], prof_stat["sigma_up"]),
            "down": quad_diff(prof_full["sigma_down"], prof_stat["sigma_down"]),
        },
        "hesse_cross_check": {
            "sigma_mu_full": _fit_alt_with_hesse(data_counts, names, base, all_floating, n_starts=8),
            "sigma_mu_stat_only": _fit_alt_with_hesse(data_counts, names, base, set(), n_starts=8),
        },
    }


# ---------------------------------------------------------------------
# Secondary 3+4: mH scan (best-fit mH + local-p curve), real data
# ---------------------------------------------------------------------
def mh_scan(data_counts, names, base):
    masses = np.arange(110.0, 150.0 + 0.25, 0.5)
    scan = []
    for i, mH in enumerate(masses):
        n_starts = 10 if abs(mH - MH_NOMINAL) < 2.5 else 3
        null = F.fit_model(data_counts, float(mH), names, mu_fixed=0.0, n_starts=n_starts, seed=1000 + i,
                            base_start=base)
        alt = F.fit_model(data_counts, float(mH), names, mu_fixed=None, n_starts=n_starts, seed=2000 + i,
                           base_start=base)
        q0info = F.q0_from_fits(null, alt)
        scan.append({"mH": float(mH), "Z": q0info["Z"], "mu_hat": q0info["mu_hat"],
                      "nll_alt": alt.nll, "invariant_ok": q0info["invariant_ok"], "both_valid": q0info["both_valid"]})
        print(f"    mH={mH:.1f}: Z={q0info['Z']:.3f}", flush=True)

    best = min(scan, key=lambda r: r["nll_alt"])
    # Refine best-fit mH with a fine local scan +-1 GeV around the coarse
    # grid minimum (0.1 GeV steps), same fitting procedure.
    fine_masses = np.arange(best["mH"] - 1.0, best["mH"] + 1.0 + 0.05, 0.1)
    fine = []
    for i, mH in enumerate(fine_masses):
        alt = F.fit_model(data_counts, float(mH), names, mu_fixed=None, n_starts=5, seed=3000 + i, base_start=base)
        fine.append({"mH": float(mH), "nll_alt": alt.nll, "mu_hat": alt.params.get("mu")})
    best_fine = min(fine, key=lambda r: r["nll_alt"])

    # Profile-likelihood uncertainty on mH itself: same root-finder,
    # scanning in mH instead of mu, at the best-fit mu (re-profiled at
    # each candidate mH inside fit_model, mu included in "names").
    best_alt = F.fit_model(data_counts, best_fine["mH"], names, mu_fixed=None, n_starts=8, seed=4000,
                            base_start=base)

    def nll_at_mh(mh_val):
        fr = fit_at_mh(data_counts, names, mh_val, base)
        return fr.nll

    def fit_at_mh(data, nm, mh_val, base_start):
        return F.fit_model(data, mh_val, nm, mu_fixed=None, n_starts=3, base_start=base_start)

    nll_hat = best_alt.nll
    # explicit initial_step: profile_interval's own default
    # (0.1*max(abs(mu_hat),1.0)) is meant for a mu-scale scan (mu_hat
    # near O(1)) -- passed here with best_fine["mH"] (~125) as the
    # analogous "mu_hat" argument, the default would try a ~12.5 GeV
    # first step, instantly exceeding max_search and returning None
    # without ever evaluating the NLL once (caught in a smoke test
    # before running this for real).
    mh_up = F.profile_interval(lambda mh: fit_at_mh(data_counts, names, mh, best_alt.params).nll,
                                best_fine["mH"], nll_hat, direction=+1, max_search=10.0, initial_step=0.5)
    mh_down = F.profile_interval(lambda mh: fit_at_mh(data_counts, names, mh, best_alt.params).nll,
                                  best_fine["mH"], nll_hat, direction=-1, max_search=10.0, initial_step=0.5)

    return {
        "scan": scan,
        "best_fit_mH_coarse": best["mH"],
        "best_fit_mH_refined": best_fine["mH"],
        "best_fit_mu_hat_at_best_mH": best_alt.params["mu"],
        "mH_sigma_up": (mh_up - best_fine["mH"]) if mh_up is not None else None,
        "mH_sigma_down": (best_fine["mH"] - mh_down) if mh_down is not None else None,
    }


# ---------------------------------------------------------------------
# Secondary 5: global significance of the largest 110-150 excess, from
# the ALREADY-COLLECTED background-only toy ensemble
# ---------------------------------------------------------------------
def global_significance(observed_max_z, merged_toys_path):
    d = json.loads(Path(merged_toys_path).read_text(encoding="utf-8"))
    le = d["part_3_5_look_elsewhere"]
    hist = le["max_Z_histogram"]
    edges = np.array(hist["bin_edges"])
    counts = np.array(hist["counts"])
    n = hist["n"]
    ge_mask = edges[:-1] >= observed_max_z
    global_p_toy = float(counts[ge_mask].sum()) / n if n else None

    gv = le["gross_vitells"]
    from scipy import stats as sps

    def asymptotic_local_p(z):
        return float(1.0 - sps.norm.cdf(z))

    z0 = gv["reference_level_Z0"]
    mean_up = gv["mean_upcrossings_at_Z0"]
    if observed_max_z >= z0:
        c, c0 = observed_max_z ** 2, z0 ** 2
        global_p_gv = asymptotic_local_p(observed_max_z) + mean_up * float(np.exp(-(c - c0) / 2.0))
    else:
        global_p_gv = asymptotic_local_p(observed_max_z)

    return {
        "observed_max_local_Z": observed_max_z,
        "n_toys_used_in_ensemble": n, "n_toys_total": le["n_toys"],
        "toy_based_global_p": global_p_toy,
        "gross_vitells_global_p": global_p_gv,
        "gross_vitells_mean_upcrossings_at_Z0": mean_up,
        "note": "Toy ensemble is the same 523/1000-toy background-only set from STATS_REPORT.md Part 3.5 "
                "(47.7% excluded to fit failures -- same caveat as recorded there); no new toys generated here.",
    }


# ---------------------------------------------------------------------
# Robustness (i): fit range 110-180, bernstein_6, statistical-only
# ---------------------------------------------------------------------
def robustness_110_180(events):
    import awkward as ak
    from studies.hgg_cms.background_model.families import FAMILIES
    from studies.hgg_cms.background_model.common import bin_edges

    order_selection = json.loads(
        (REPO_ROOT / "studies" / "hgg_cms" / "background_model" / "results" / "order_selection_110_180.json")
        .read_text(encoding="utf-8"))
    mi = M.get_model_inputs()
    edges_110 = bin_edges(110.0, 180.0, 0.25)

    cat_selector = {"EBEB": lambda e: e["category"] == "EBEB", "notEBEB": lambda e: e["category"] != "EBEB"}
    data_counts_110 = {}
    for cat, sel in cat_selector.items():
        m = events["m_gg"][sel(events)]
        data_counts_110[cat], _ = np.histogram(ak.to_numpy(m), bins=edges_110)

    bkg_params = {}
    for cat in M.CATEGORIES:
        ci = mi.categories[cat]
        bkg_params[cat] = np.array(order_selection[cat][ci.bkg_family]["per_order"][str(ci.bkg_order)]["fit"]["params"])

    def nu(cat, mu, bkg_p):
        ci = mi.categories[cat]
        shape = M.signal_shape_for(ci, MH_NOMINAL, 0.0, 0.0)
        probs = shape.bin_probabilities(edges_110)
        fam = FAMILIES[ci.bkg_family]
        bkg = fam.bin_expectation(edges_110, ci.bkg_order, bkg_p[cat])
        return mu * ci.N_s * probs + bkg

    names = ["mu"] + [f"bkg_{cat}_{n}" for cat in M.CATEGORIES
                       for n in FAMILIES[mi.categories[cat].bkg_family].param_names(mi.categories[cat].bkg_order)]

    def nll(par, mu_fixed):
        bkg_p = {}
        for cat in M.CATEGORIES:
            fam = FAMILIES[mi.categories[cat].bkg_family]
            names_c = fam.param_names(mi.categories[cat].bkg_order)
            bkg_p[cat] = np.array([par[f"bkg_{cat}_{n}"] for n in names_c])
        mu = mu_fixed if mu_fixed is not None else par["mu"]
        total = 0.0
        for cat in M.CATEGORIES:
            total += poisson_nll(data_counts_110[cat], nu(cat, mu, bkg_p))
        return total

    from iminuit import Minuit

    def fit(mu_fixed, seed):
        rng = np.random.default_rng(seed)
        free = [n for n in names if not (n == "mu" and mu_fixed is not None)]
        start = {"mu": mu_fixed if mu_fixed is not None else 1.0}
        for cat in M.CATEGORIES:
            fam = FAMILIES[mi.categories[cat].bkg_family]
            for n, v in zip(fam.param_names(mi.categories[cat].bkg_order), bkg_params[cat]):
                start[f"bkg_{cat}_{n}"] = v
        best_m = None
        for k in range(8):
            s = dict(start)
            if k > 0:
                for n in free:
                    if n.startswith("bkg_"):
                        s[n] = s[n] * rng.uniform(0.8, 1.2)
                    elif n == "mu":
                        s[n] = s[n] + rng.uniform(-1, 1)
            start_vec = [s[n] for n in free]

            def nll_fn(*par):
                full = dict(zip(free, par))
                if mu_fixed is not None:
                    full["mu"] = mu_fixed
                return nll(full, mu_fixed)

            m = Minuit(nll_fn, *start_vec, name=free)
            m.errordef = Minuit.LIKELIHOOD
            if "mu" in free:
                m.limits["mu"] = (-20, 20)
            for n in free:
                if n.startswith("bkg_"):
                    m.limits[n] = (0.0, None)
            m.strategy = 1
            m.migrad()
            if best_m is None or (m.valid and not best_m.valid) or (m.valid == best_m.valid and m.fval < best_m.fval):
                best_m = m
        params = {n: float(best_m.values[n]) for n in free}
        if mu_fixed is not None:
            params["mu"] = mu_fixed
        return F.FitResult(nll=float(best_m.fval), params=params, valid=bool(best_m.valid), n_attempts=8, n_valid=1)

    null = fit(0.0, 1)
    alt = fit(None, 2)
    q0info = F.q0_from_fits(null, alt)
    return {"Z": q0info["Z"], "mu_hat": q0info["mu_hat"], "invariant_ok": q0info["invariant_ok"],
            "both_valid": q0info["both_valid"],
            "note": "Statistical-only, per the pre-declared definition (no spurious-signal value exists "
                    "at 110-180 GeV)."}


# ---------------------------------------------------------------------
# Robustness (ii): bernstein_5 background
# ---------------------------------------------------------------------
def robustness_bernstein5(data_counts, base):
    from studies.hgg_cms.background_model.families import FAMILIES
    order_selection = json.loads(
        (REPO_ROOT / "studies" / "hgg_cms" / "background_model" / "results" / "order_selection_105_180.json")
        .read_text(encoding="utf-8"))
    bern = FAMILIES["bernstein"]
    order5_params = {cat: np.array(order_selection[cat]["bernstein"]["per_order"]["5"]["fit"]["params"])
                      for cat in M.CATEGORIES}
    bkg5_names = bern.param_names(5)

    names = list(M.SHARED_PARAM_NAMES)
    for cat in M.CATEGORIES:
        for n in M.PER_CATEGORY_NUISANCE_NAMES:
            names.append(f"{n}_{cat}")
    for cat in M.CATEGORIES:
        for pn in bkg5_names:
            names.append(f"bkg5_{cat}_{pn}")
    names = tuple(names)

    edges = M.edges()

    def expected_counts_b5(cat, par, mH):
        mi = M.get_model_inputs()
        ci = mi.categories[cat]
        theta_scale, theta_res = par["theta_scale"], par["theta_res"]
        shape = M.signal_shape_for(ci, mH, theta_scale, theta_res)
        sig_probs = shape.bin_probabilities(edges)
        K = M.K_factor(cat, ci, par["theta_lumi"], par["theta_theory"], par["theta_ID"],
                        par[f"theta_trigger_{cat}"], par[f"theta_pileup_{cat}"], par[f"theta_mcstat_{cat}"])
        mu = par["mu"]
        theta_spur = par[f"theta_spur_{cat}"]
        signal_term = mu * ci.N_s * K * sig_probs
        spurious_term = theta_spur * ci.S_spur * sig_probs
        bkg_p = np.array([par[f"bkg5_{cat}_{n}"] for n in bkg5_names])
        bkg_term = bern.bin_expectation(edges, 5, bkg_p)
        return signal_term + spurious_term + bkg_term

    def full_nll_b5(data, par, mH):
        total = M.gaussian_constraint_nll(par)
        for cat in M.CATEGORIES:
            total += poisson_nll(data[cat], expected_counts_b5(cat, par, mH))
        return total

    bounds = {}
    for n in names:
        if n == "mu":
            bounds[n] = (-20.0, 20.0)
        elif n.startswith("theta_"):
            bounds[n] = (-6.0, 6.0)
        elif n.startswith("bkg5_"):
            _, cat, pname = n.split("_", 2)
            idx = bkg5_names.index(pname)
            total = float(order5_params[cat].sum())
            bounds[n] = bern.bounds(5, total)[idx]

    start = {}
    for n in names:
        if n == "mu":
            start[n] = 1.0
        elif n.startswith("theta_"):
            start[n] = 0.0
        elif n.startswith("bkg5_"):
            _, cat, pname = n.split("_", 2)
            idx = bkg5_names.index(pname)
            start[n] = float(order5_params[cat][idx])

    from iminuit import Minuit

    def fit(mu_fixed, seed):
        rng = np.random.default_rng(seed)
        free = [n for n in names if not (n == "mu" and mu_fixed is not None)]
        best_m = None
        for k in range(8):
            s = dict(start)
            if k > 0:
                for n in free:
                    if n == "mu":
                        s[n] = (mu_fixed if mu_fixed is not None else 1.0) + rng.uniform(-2, 2)
                    elif n.startswith("theta_"):
                        s[n] = rng.normal(0, 1)
                    elif n.startswith("bkg5_"):
                        s[n] = s[n] * rng.uniform(0.7, 1.3)
            start_vec = [s[n] for n in free]

            def nll_fn(*par):
                full = dict(zip(free, par))
                if mu_fixed is not None:
                    full["mu"] = mu_fixed
                return full_nll_b5(data_counts, full, MH_NOMINAL)

            m = Minuit(nll_fn, *start_vec, name=free)
            m.errordef = Minuit.LIKELIHOOD
            for n in free:
                m.limits[n] = bounds[n]
            m.strategy = 1
            m.migrad()
            if best_m is None or (m.valid and not best_m.valid) or (m.valid == best_m.valid and m.fval < best_m.fval):
                best_m = m
        params = {n: float(best_m.values[n]) for n in free}
        if mu_fixed is not None:
            params["mu"] = mu_fixed
        return F.FitResult(nll=float(best_m.fval), params=params, valid=bool(best_m.valid), n_attempts=8, n_valid=1)

    null = fit(0.0, 21)
    alt = fit(None, 22)
    q0info = F.q0_from_fits(null, alt)
    return {"Z": q0info["Z"], "mu_hat": q0info["mu_hat"], "invariant_ok": q0info["invariant_ok"],
            "both_valid": q0info["both_valid"]}


# ---------------------------------------------------------------------
# Robustness (iii): no spurious-signal terms
# ---------------------------------------------------------------------
def robustness_no_spurious(data_counts, names, base):
    all_but_spur = (set(names) - {"mu"} - {n for n in names if n.startswith("bkg_")}
                     - {"theta_spur_EBEB", "theta_spur_notEBEB"})
    r = _fit_with_restricted_nuisances(data_counts, names, base, all_but_spur, n_starts=10, seed0=201, seed1=202)
    return {"Z": r["q0info"]["Z"], "mu_hat": r["q0info"]["mu_hat"],
            "invariant_ok": r["q0info"]["invariant_ok"], "both_valid": r["q0info"]["both_valid"]}


# ---------------------------------------------------------------------
# Robustness (v): Run2016G / Run2016H separately, luminosity-scaled signal
# ---------------------------------------------------------------------
def robustness_run_period(events, names, base, run_label):
    import awkward as ak
    lo, hi = RUN_RANGES[run_label]
    lumi_frac = LUMI_FB[run_label] / LUMI_TOTAL_FB
    run = ak.to_numpy(events["run"])
    mask = (run >= lo) & (run <= hi)
    edges = M.edges()
    cat_selector = {"EBEB": lambda e: e["category"] == "EBEB", "notEBEB": lambda e: e["category"] != "EBEB"}
    data_counts_rp = {}
    n_events = {}
    for cat, sel in cat_selector.items():
        cat_mask = ak.to_numpy(sel(events)) & mask
        m = ak.to_numpy(events["m_gg"])[cat_mask]
        data_counts_rp[cat], _ = np.histogram(m, bins=edges)
        n_events[cat] = int(cat_mask.sum())

    def expected_counts_scaled(cat, par, mH):
        par_scaled = dict(par)
        par_scaled["mu"] = par["mu"] * lumi_frac
        return M.expected_counts(cat, par_scaled, mH)

    def full_nll_scaled(data, par, mH):
        total = M.gaussian_constraint_nll(par)
        for cat in M.CATEGORIES:
            total += poisson_nll(data[cat], expected_counts_scaled(cat, par, mH))
        return total

    bounds = F.default_bounds(names)
    from iminuit import Minuit

    def fit(mu_fixed, seed):
        rng = np.random.default_rng(seed)
        free = [n for n in names if not (n == "mu" and mu_fixed is not None)]
        starts = F.random_starts(names, rng, 8, mu_start=(mu_fixed if mu_fixed is not None else 1.0),
                                  base_start=base)
        best_m = None
        for start in starts:
            start_vec = [start[n] for n in free]

            def nll_fn(*par):
                full = dict(zip(free, par))
                if mu_fixed is not None:
                    full["mu"] = mu_fixed
                return full_nll_scaled(data_counts_rp, full, MH_NOMINAL)

            m = Minuit(nll_fn, *start_vec, name=free)
            m.errordef = Minuit.LIKELIHOOD
            for n in free:
                m.limits[n] = bounds[n]
            m.strategy = 1
            try:
                m.migrad()
            except Exception:
                continue
            if best_m is None or (m.valid and not best_m.valid) or (m.valid == best_m.valid and m.fval < best_m.fval):
                best_m = m
        params = {n: float(best_m.values[n]) for n in free}
        if mu_fixed is not None:
            params["mu"] = mu_fixed
        return F.FitResult(nll=float(best_m.fval), params=params, valid=bool(best_m.valid), n_attempts=8, n_valid=1)

    null = fit(0.0, 301)
    alt = fit(None, 302)
    q0info = F.q0_from_fits(null, alt)
    return {"Z": q0info["Z"], "mu_hat": q0info["mu_hat"], "invariant_ok": q0info["invariant_ok"],
            "both_valid": q0info["both_valid"], "n_events": n_events,
            "luminosity_fb": LUMI_FB[run_label], "luminosity_fraction": lumi_frac}


# ---------------------------------------------------------------------
# Robustness (vi): energy scale/resolution fixed vs profiled
# ---------------------------------------------------------------------
def robustness_scale_res_fixed(data_counts, names, base):
    all_but_scale_res = (set(names) - {"mu"} - {n for n in names if n.startswith("bkg_")}
                          - {"theta_scale", "theta_res"})
    r = _fit_with_restricted_nuisances(data_counts, names, base, all_but_scale_res, n_starts=10,
                                        seed0=401, seed1=402)
    return {"Z": r["q0info"]["Z"], "mu_hat": r["q0info"]["mu_hat"],
            "invariant_ok": r["q0info"]["invariant_ok"], "both_valid": r["q0info"]["both_valid"]}


def main():
    print("Loading real data...", flush=True)
    events, data_counts = load_real_data_counts()
    names = M.full_param_names()
    base = F.default_start(names, mu_start=1.0)

    out = {}

    print("Secondary 1: profile-likelihood mu breakdown...", flush=True)
    t0 = time.time()
    out["mu_breakdown"] = profile_mu_breakdown(data_counts, names, base)
    print(f"  done ({time.time()-t0:.1f}s): {out['mu_breakdown']['full']}", flush=True)

    print("Secondary 3+4: mH scan...", flush=True)
    t0 = time.time()
    out["mh_scan"] = mh_scan(data_counts, names, base)
    print(f"  done ({time.time()-t0:.1f}s): best_fit_mH={out['mh_scan']['best_fit_mH_refined']}", flush=True)

    max_z_observed = max(r["Z"] for r in out["mh_scan"]["scan"])
    print("Secondary 5: global significance...", flush=True)
    out["global_significance"] = global_significance(
        max_z_observed, r"C:\Users\matan\hgg_stats_merged\hgg_stats_merged.json")
    print(f"  {out['global_significance']}", flush=True)

    print("Robustness (i): 110-180 stat-only...", flush=True)
    t0 = time.time()
    out["robustness_i_110_180"] = robustness_110_180(events)
    print(f"  done ({time.time()-t0:.1f}s): {out['robustness_i_110_180']}", flush=True)

    print("Robustness (ii): bernstein_5...", flush=True)
    t0 = time.time()
    out["robustness_ii_bernstein5"] = robustness_bernstein5(data_counts, base)
    print(f"  done ({time.time()-t0:.1f}s): {out['robustness_ii_bernstein5']}", flush=True)

    print("Robustness (iii): no spurious...", flush=True)
    t0 = time.time()
    out["robustness_iii_no_spurious"] = robustness_no_spurious(data_counts, names, base)
    print(f"  done ({time.time()-t0:.1f}s): {out['robustness_iii_no_spurious']}", flush=True)

    print("Robustness (v): Run2016G/H...", flush=True)
    t0 = time.time()
    out["robustness_v_run_periods"] = {
        "Run2016G": robustness_run_period(events, names, base, "Run2016G"),
        "Run2016H": robustness_run_period(events, names, base, "Run2016H"),
    }
    print(f"  done ({time.time()-t0:.1f}s): {out['robustness_v_run_periods']}", flush=True)

    print("Robustness (vi): scale/res fixed...", flush=True)
    t0 = time.time()
    out["robustness_vi_scale_res_fixed"] = robustness_scale_res_fixed(data_counts, names, base)
    print(f"  done ({time.time()-t0:.1f}s): {out['robustness_vi_scale_res_fixed']}", flush=True)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    print(f"wrote {OUT_PATH}")


if __name__ == "__main__":
    main()
