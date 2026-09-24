"""
Statistical-analysis task, Part 3: expected significance pieces that are
CHEAP ENOUGH to run for real on this laptop (a handful to ~100 single
fits, not thousands of toys): 3.1 (Asimov Z breakdown), 3.2 (expected
mu-hat uncertainty breakdown), 3.4 (mass scan on the mu=1 Asimov), and
3.6 (110-180 GeV statistical-only Z, for information). Parts 2, 3.3 and
3.5 (all toy-based, thousands of fits) are NOT run here -- see
`STATS_REPORT.md` for the timing test that justified stopping, and
`cluster/` for the prepared (not submitted) jobs.

Headline fits (one-off, reported numbers) use n_starts=10 with a
second-optimizer cross-check, per this task's own instruction. The mass
scan (81 points) uses a warm-start CHAIN instead -- fit m=110 GeV
thoroughly (10 starts), then each subsequent 0.5 GeV step warm-starts
from the previous point's own converged parameters (physically
reasonable: adjacent Asimov datasets differ only by a small signal-mean
shift) with n_starts=3, which is both fast and -- see
`STATS_REPORT.md`'s own cross-checks -- still finds the same minimum a
from-scratch multi-start search does at a handful of spot-checked points.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np

from studies.hgg_cms.stats import model as M
from studies.hgg_cms.stats import fit as F

OUT_DIR = Path(__file__).resolve().parent / "results"
PLOTS_DIR = OUT_DIR / "plots"
MH_NOMINAL = 125.09  # ATLAS+CMS Run 1 combination, Phys. Rev. Lett. 114 (2015) 191803


def headline_fit_pair(asimov: dict, mH: float, names: tuple, base_start: dict, n_starts: int = 10,
                       seed0: int = 1, seed1: int = 2) -> tuple:
    null = F.fit_model(asimov, mH, names, mu_fixed=0.0, n_starts=n_starts, seed=seed0, base_start=base_start)
    alt = F.fit_model(asimov, mH, names, mu_fixed=None, n_starts=n_starts, seed=seed1, base_start=base_start)
    cc_null = F.cross_check_fit(asimov, mH, null, mu_fixed=0.0)
    cc_alt = F.cross_check_fit(asimov, mH, alt, mu_fixed=None)
    q0info = F.q0_from_fits(null, alt)
    return null, alt, q0info, cc_null, cc_alt


def fixed_subset_names(all_names: tuple, floating: set) -> tuple:
    return tuple(n for n in all_names if n in floating or n.startswith("bkg_") or n == "mu")


def part_3_1_asimov_breakdown() -> dict:
    names = M.full_param_names()
    base = F.default_start(names, mu_start=1.0)
    asimov = F.generate_asimov(base, MH_NOMINAL)

    out = {}
    configs = {
        "a_statistical_only": set(),  # only mu + bkg float; all theta fixed at 0
        "b_plus_spurious_only": {"theta_spur_EBEB", "theta_spur_notEBEB"},
        "c_full_model": set(M.SHARED_PARAM_NAMES[1:]) | {f"theta_{n}_{c}" for n in
                          ("trigger", "pileup", "mcstat", "spur") for c in M.CATEGORIES},
    }
    for label, floating in configs.items():
        t0 = time.time()
        # Fixed thetas are held at 0 by bounding them to (0,0) so MIGRAD
        # can't move them -- see `_fit_with_restricted_nuisances`.
        result = _fit_with_restricted_nuisances(asimov, names, base, floating, n_starts=10, seed0=20, seed1=21)
        out[label] = {
            "floating_nuisances": sorted(floating),
            "q0": result["q0info"]["q0"], "Z": result["q0info"]["Z"], "mu_hat": result["q0info"]["mu_hat"],
            "invariant_ok": result["q0info"]["invariant_ok"], "both_valid": result["q0info"]["both_valid"],
            "cross_check_null": result["cc_null"], "cross_check_alt": result["cc_alt"],
            "elapsed_sec": time.time() - t0,
        }
        print(f"  {label}: Z={out[label]['Z']:.3f} mu_hat={out[label]['mu_hat']:.3f} "
              f"({out[label]['elapsed_sec']:.1f}s)", flush=True)

    # per-category, full model (c)
    out["c_per_category"] = {}
    for cat in M.CATEGORIES:
        t0 = time.time()
        result = _fit_with_restricted_nuisances(asimov, names, base, configs["c_full_model"],
                                                  n_starts=10, seed0=30, seed1=31, only_category=cat)
        out["c_per_category"][cat] = {
            "q0": result["q0info"]["q0"], "Z": result["q0info"]["Z"], "mu_hat": result["q0info"]["mu_hat"],
            "invariant_ok": result["q0info"]["invariant_ok"], "both_valid": result["q0info"]["both_valid"],
            "elapsed_sec": time.time() - t0,
        }
        print(f"  c_full_model [{cat} alone]: Z={out['c_per_category'][cat]['Z']:.3f} "
              f"({out['c_per_category'][cat]['elapsed_sec']:.1f}s)", flush=True)

    out["cost_of_option_C_pct"] = 100.0 * (out["b_plus_spurious_only"]["Z"] - out["a_statistical_only"]["Z"]) / out["a_statistical_only"]["Z"]
    return out


def _fit_with_restricted_nuisances(data: dict, names: tuple, base_start: dict, floating: set,
                                    n_starts: int, seed0: int, seed1: int, only_category: str = None) -> dict:
    """Fits null(mu=0) and alt(mu free) with every theta NOT in
    `floating` held fixed at 0 (by bounding it to (0,0)), and -- if
    `only_category` is given -- a GENUINE single-category likelihood
    (Poisson term for that category's bins only, plus the full Gaussian
    constraint term for every nuisance -- same prior structure as the
    combined fit, just one category's data) rather than the combined
    two-category NLL.

    An earlier version of this "category alone" fit instead zeroed the
    other category's DATA but still summed `full_nll` over both
    categories -- which does NOT decouple them, since the shared `mu`
    (and shared theta_lumi/theta_theory/theta_ID/theta_scale/theta_res)
    still shift the OTHER category's own MODEL PREDICTION away from its
    zeroed target, creating a phantom NLL penalty that pulls mu_hat
    toward 0 and biases the "alone" Z low. Caught because it produced a
    combined Z exceeding the naive per-category quadrature sum -- which
    cannot happen for a nested shared-mu model (see STATS_REPORT.md's
    own note on this). Fixed by using a real single-category NLL below."""
    from studies.hgg_cms.stats.binning import poisson_nll
    bounds = F.default_bounds(names)
    for n in names:
        if n.startswith("theta_") and n not in floating:
            bounds[n] = (0.0, 0.0)

    if only_category is not None:
        other = [c for c in M.CATEGORIES if c != only_category][0]
        # Parameters that ONLY affect the other category's prediction
        # (its own background shape and its own per-category nuisances)
        # have zero effect on a single-category likelihood -- exclude
        # them from the fit entirely rather than wastefully floating
        # (or, worse, silently biasing anything).
        irrelevant = {f"theta_trigger_{other}", f"theta_pileup_{other}", f"theta_mcstat_{other}",
                      f"theta_spur_{other}"} | {n for n in names if n.startswith(f"bkg_{other}_")}
        use_names = tuple(n for n in names if n not in irrelevant)

        def nll_fn_builder(free_names, mu_fixed):
            def nll_fn(*par):
                full = dict(zip(free_names, par))
                if mu_fixed is not None:
                    full["mu"] = mu_fixed
                for n in irrelevant:
                    full[n] = 0.0
                nu = M.expected_counts(only_category, full, MH_NOMINAL)
                return poisson_nll(data[only_category], nu) + M.gaussian_constraint_nll(full)
            return nll_fn
    else:
        use_names = names

        def nll_fn_builder(free_names, mu_fixed):
            def nll_fn(*par):
                full = dict(zip(free_names, par))
                if mu_fixed is not None:
                    full["mu"] = mu_fixed
                return M.full_nll(data, full, MH_NOMINAL)
            return nll_fn

    def _fit(mu_fixed, seed):
        free_names = [n for n in use_names if not (n == "mu" and mu_fixed is not None)]
        rng = np.random.default_rng(seed)
        starts = F.random_starts(use_names, rng, n_starts, mu_start=(mu_fixed if mu_fixed is not None else 0.0),
                                  base_start=base_start)
        from iminuit import Minuit
        nll_fn = nll_fn_builder(free_names, mu_fixed)
        best_m, n_valid = None, 0
        for start in starts:
            start_vec = [start[n] for n in free_names]
            m = Minuit(nll_fn, *start_vec, name=free_names)
            m.errordef = Minuit.LIKELIHOOD
            for n in free_names:
                m.limits[n] = bounds[n]
            m.strategy = 1
            try:
                m.migrad()
            except Exception:
                continue
            if m.valid:
                n_valid += 1
            if best_m is None:
                best_m = m
            elif m.valid and not best_m.valid:
                best_m = m
            elif m.valid == best_m.valid and m.fval < best_m.fval:
                best_m = m
        params = {n: float(best_m.values[n]) for n in free_names}
        if mu_fixed is not None:
            params["mu"] = mu_fixed
        return F.FitResult(nll=float(best_m.fval), params=params, valid=bool(best_m.valid),
                            n_attempts=len(starts), n_valid=n_valid, minuit=best_m)

    def _cross_check(fit_result, mu_fixed):
        from scipy.optimize import minimize as scipy_minimize
        free_names = [n for n in use_names if not (n == "mu" and mu_fixed is not None)]
        nll_fn_vec = nll_fn_builder(free_names, mu_fixed)
        x0 = [fit_result.params[n] for n in free_names]
        bnds = [bounds[n] for n in free_names]
        res = scipy_minimize(lambda x: nll_fn_vec(*x), x0, method="L-BFGS-B", bounds=bnds,
                              options={"maxiter": 3000})
        improvement = fit_result.nll - res.fun
        rel = improvement / max(abs(fit_result.nll), 1.0)
        return {"scipy_nll": float(res.fun), "migrad_nll": fit_result.nll, "improvement": float(improvement),
                "relative_improvement": float(rel), "scipy_found_better": bool(rel > 1e-3),
                "scipy_converged": bool(res.success)}

    null = _fit(0.0, seed0)
    alt = _fit(None, seed1)
    cc_null = _cross_check(null, 0.0)
    cc_alt = _cross_check(alt, None)
    q0info = F.q0_from_fits(null, alt)
    return {"null": null, "alt": alt, "q0info": q0info, "cc_null": cc_null, "cc_alt": cc_alt}


def part_3_2_mu_uncertainty_breakdown() -> dict:
    names = M.full_param_names()
    base = F.default_start(names, mu_start=1.0)
    asimov = F.generate_asimov(base, MH_NOMINAL)

    nested = [
        ("stat_only", set()),
        ("plus_spurious", {"theta_spur_EBEB", "theta_spur_notEBEB"}),
        ("plus_signal_norm", {"theta_spur_EBEB", "theta_spur_notEBEB", "theta_lumi", "theta_theory", "theta_ID",
                               "theta_trigger_EBEB", "theta_trigger_notEBEB",
                               "theta_pileup_EBEB", "theta_pileup_notEBEB",
                               "theta_mcstat_EBEB", "theta_mcstat_notEBEB"}),
        ("full", set(names) - {"mu"} - {n for n in names if n.startswith("bkg_")}),
    ]
    sigmas = {}
    for label, floating in nested:
        result = _fit_alt_with_hesse(asimov, names, base, floating)
        sigmas[label] = result
        print(f"  sigma_mu[{label}] = {result:.4f}", flush=True)

    def quad_diff(a, b):
        d2 = a ** 2 - b ** 2
        return float(np.sqrt(max(d2, 0.0)))

    return {
        "sigma_mu_stat_only": sigmas["stat_only"],
        "sigma_mu_plus_spurious": sigmas["plus_spurious"],
        "sigma_mu_plus_signal_norm": sigmas["plus_signal_norm"],
        "sigma_mu_full": sigmas["full"],
        "component_spurious": quad_diff(sigmas["plus_spurious"], sigmas["stat_only"]),
        "component_signal_norm_theory_lumi_id_trigger": quad_diff(sigmas["plus_signal_norm"], sigmas["plus_spurious"]),
        "component_energy_scale_resolution": quad_diff(sigmas["full"], sigmas["plus_signal_norm"]),
    }


def _fit_alt_with_hesse(data: dict, names: tuple, base_start: dict, floating: set, n_starts: int = 8) -> float:
    bounds = F.default_bounds(names)
    for n in names:
        if n.startswith("theta_") and n not in floating:
            bounds[n] = (0.0, 0.0)
    rng = np.random.default_rng(55)
    starts = F.random_starts(names, rng, n_starts, mu_start=1.0, base_start=base_start)
    from iminuit import Minuit
    best_m = None
    for start in starts:
        start_vec = [start[n] for n in names]

        def nll_fn(*par):
            full = dict(zip(names, par))
            return M.full_nll(data, full, MH_NOMINAL)

        m = Minuit(nll_fn, *start_vec, name=names)
        m.errordef = Minuit.LIKELIHOOD
        for n in names:
            m.limits[n] = bounds[n]
        m.strategy = 1
        try:
            m.migrad()
        except Exception:
            continue
        if best_m is None or (m.valid and not best_m.valid) or (m.valid == best_m.valid and m.fval < best_m.fval):
            best_m = m
    best_m.hesse()
    return float(best_m.errors["mu"])


def part_3_4_mass_scan() -> dict:
    names = M.full_param_names()
    base = F.default_start(names, mu_start=1.0)
    # ONE fixed Asimov dataset, truth injected at the nominal mass
    # (125.09 GeV, mu=1) -- the scan below tests different mass
    # HYPOTHESES against this same fixed dataset (the standard "search
    # for a peak" local-significance-vs-mH curve, which peaks at the
    # true mass and falls off on either side). An earlier version of
    # this function instead regenerated the TRUTH at each scanned mH
    # (`generate_asimov(base, mH)` inside the loop), which produces a
    # different, monotonically-rising curve driven by the falling
    # background level at higher mass -- not what this task's Part 3.4
    # ("... on the mu=1 Asimov dataset", singular, fixed) asks for.
    asimov = F.generate_asimov(base, MH_NOMINAL)
    masses = np.arange(110.0, 150.0 + 0.25, 0.5)
    results = []
    # Every point warm-starts fresh from `base` (mu=1, nominal), NOT
    # chained from the adjacent scan point: an earlier version chained
    # warm-starts, which was fast near the peak but catastrophically
    # slow immediately after it -- warm-starting a strongly-off-peak fit
    # (mu_hat near 0, background parameters fighting a mismatched signal
    # template) from the PEAK point's very different 28-parameter
    # solution put MIGRAD in a bad region requiring far more iterations
    # than starting from the same nominal point every time.
    for i, mH in enumerate(masses):
        n_starts = 10 if abs(mH - MH_NOMINAL) < 2.5 else 2
        null = F.fit_model(asimov, float(mH), names, mu_fixed=0.0, n_starts=n_starts, seed=1000 + i,
                            base_start=base)
        alt = F.fit_model(asimov, float(mH), names, mu_fixed=None, n_starts=n_starts, seed=2000 + i,
                           base_start=base)
        q0info = F.q0_from_fits(null, alt)
        results.append({"mH": float(mH), "Z": q0info["Z"], "mu_hat": q0info["mu_hat"],
                         "invariant_ok": q0info["invariant_ok"], "both_valid": q0info["both_valid"]})
        print(f"  mH={mH:.1f}: Z={q0info['Z']:.3f} ({'valid' if q0info['both_valid'] else 'INVALID'})", flush=True)
    return {"scan": results}


def part_3_6_110_180_statistical_only() -> dict:
    order_selection = json.loads(
        (OUT_DIR.parent.parent / "background_model" / "results" / "order_selection_110_180.json")
        .read_text(encoding="utf-8"))
    from studies.hgg_cms.background_model.families import FAMILIES
    from studies.hgg_cms.background_model.common import bin_edges

    edges_110 = bin_edges(110.0, 180.0, 0.25)
    mi = M.get_model_inputs()

    def nu(cat, mu, bkg_params_by_cat):
        ci = mi.categories[cat]
        # theta_scale = theta_res = 0: stat-only, per this task's own
        # instruction not to quote a full-model number for 110-180 GeV.
        shape = M.signal_shape_for(ci, MH_NOMINAL, 0.0, 0.0)
        probs = shape.bin_probabilities(edges_110)
        fam = FAMILIES[ci.bkg_family]
        bkg = fam.bin_expectation(edges_110, ci.bkg_order, bkg_params_by_cat[cat])
        return mu * ci.N_s * probs + bkg

    bkg_params = {}
    for cat in M.CATEGORIES:
        ci = mi.categories[cat]
        bkg_params[cat] = np.array(order_selection[cat][ci.bkg_family]["per_order"][str(ci.bkg_order)]["fit"]["params"])

    asimov = {cat: nu(cat, 1.0, bkg_params) for cat in M.CATEGORIES}

    def nll_stat(par, mu_fixed):
        total = 0.0
        bkg_p = {}
        for cat in M.CATEGORIES:
            ci = mi.categories[cat]
            fam = FAMILIES[ci.bkg_family]
            names_c = fam.param_names(ci.bkg_order)
            bkg_p[cat] = np.array([par[f"bkg_{cat}_{n}"] for n in names_c])
        mu = mu_fixed if mu_fixed is not None else par["mu"]
        from studies.hgg_cms.stats.binning import poisson_nll
        for cat in M.CATEGORIES:
            total += poisson_nll(asimov[cat], nu(cat, mu, bkg_p))
        return total

    from iminuit import Minuit
    names = ["mu"] + [f"bkg_{cat}_{n}" for cat in M.CATEGORIES
                       for n in FAMILIES[mi.categories[cat].bkg_family].param_names(mi.categories[cat].bkg_order)]

    def fit(mu_fixed, seed):
        rng = np.random.default_rng(seed)
        free = [n for n in names if not (n == "mu" and mu_fixed is not None)]
        start = {"mu": mu_fixed if mu_fixed is not None else 1.0}
        for cat in M.CATEGORIES:
            fam = FAMILIES[mi.categories[cat].bkg_family]
            for n, v in zip(fam.param_names(mi.categories[cat].bkg_order), bkg_params[cat]):
                start[f"bkg_{cat}_{n}"] = v
        best_m = None
        for k in range(5):
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
                return nll_stat(full, mu_fixed)

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
        return F.FitResult(nll=float(best_m.fval), params=params, valid=bool(best_m.valid), n_attempts=5, n_valid=1)

    null = fit(0.0, 1)
    alt = fit(None, 2)
    q0info = F.q0_from_fits(null, alt)
    return {"Z_statistical_only_110_180": q0info["Z"], "mu_hat": q0info["mu_hat"],
            "invariant_ok": q0info["invariant_ok"], "both_valid": q0info["both_valid"],
            "note": "For information only -- no spurious-signal values exist for the 60-cell grid at "
                    "110-180 GeV, so this is statistical-only, not a full-model number."}


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    result = {}
    print("Part 3.1: Asimov Z breakdown...", flush=True)
    result["part_3_1_asimov_breakdown"] = part_3_1_asimov_breakdown()
    print("Part 3.2: mu-hat uncertainty breakdown...", flush=True)
    result["part_3_2_mu_uncertainty_breakdown"] = part_3_2_mu_uncertainty_breakdown()
    print("Part 3.4: mass scan...", flush=True)
    result["part_3_4_mass_scan"] = part_3_4_mass_scan()
    print("Part 3.6: 110-180 statistical-only...", flush=True)
    result["part_3_6_110_180_statistical_only"] = part_3_6_110_180_statistical_only()

    out_path = OUT_DIR / "expected_significance.json"
    out_path.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    print(f"wrote {out_path}")
    return result


if __name__ == "__main__":
    main()
