"""
Toy Monte Carlo study validating the profiled likelihood-ratio (LR)
procedure for bump searches, on synthetic histograms only (no real data).

Runs tests T1-T6 described in studies/lr_toys/REPORT.md, writes every
number to studies/lr_toys/results/toy_study_results.json, and writes PNG
plots to the same directory. T0 (the closed-form cross-check) lives in
test_lr_core.py, not here.

Usage: python run_toy_study.py
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy import stats
from scipy.optimize import brentq

import lr_core as lc

HERE = Path(__file__).parent
RESULTS_DIR = HERE / "results"
RESULTS_DIR.mkdir(exist_ok=True)

# ----------------------------------------------------------------------------
# Fixed, pre-registered seeds (recorded here AND in the output JSON, so the
# whole study is exactly reproducible).
# ----------------------------------------------------------------------------
SEEDS = {
    "T1_bkg_only": 10_001,
    "T2_sig_bkg": {"z1": 20_001, "z2": 20_002, "z3": 20_003, "z5": 20_005},
    "T4_lee": 40_001,
    "T5_spurious": 50_001,
    "T6_floating_width": 60_001,
}

# ----------------------------------------------------------------------------
# Pre-set toy counts and pass criteria (fixed BEFORE looking at any result;
# see REPORT.md "Limitations and assumptions" for the T4 reduction).
# ----------------------------------------------------------------------------
N_T1 = 20_000
N_T2 = 2_000
N_T4 = 1_500  # reduced from the requested >=5,000: timed at ~340 ms/toy for the
# full 81-point scan (measured on this machine before committing to this
# number), so 5,000 toys would take ~28 minutes on its own. 1,500 toys keeps
# the full T1-T6 run comfortably inside the ~45-minute target and increases
# T4's binomial uncertainty by a factor sqrt(5000/1500) = 1.8; see REPORT.md.
N_T5 = 2_000
N_T6 = 2_000
T4_MASS_POINTS = np.linspace(110.0, 150.0, 81)  # 0.5 GeV steps, as specified

EDGES = lc.bin_edges()
CENTERS = lc.bin_centers(EDGES)
NODES, WEIGHTS = lc.gl_bin_nodes(EDGES)
SIDEBAND_MASK = (CENTERS < 115.0) | (CENTERS > 135.0)
SIDEBAND_NODES = NODES[SIDEBAND_MASK]
SIDEBAND_WEIGHTS = WEIGHTS[SIDEBAND_MASK]

TRUE_COEFFS = [lc.P1_TRUE, lc.P2_TRUE]
TRUE_B = lc.background_bin_expectation(NODES, WEIGHTS, lc.N_BKG_TRUE, TRUE_COEFFS)


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def binomial_3sigma(k: int, n: int, p0: float):
    """(observed fraction, expected p0, 3-sigma band half-width, pass bool)."""
    phat = k / n
    se = np.sqrt(p0 * (1 - p0) / n)
    return phat, p0, 3 * se, abs(phat - p0) <= 3 * se


# ----------------------------------------------------------------------------
# T1: background-only toys -> q0 distribution
# ----------------------------------------------------------------------------

def run_t1():
    log(f"T1: generating and fitting {N_T1} background-only toys...")
    rng = np.random.default_rng(SEEDS["T1_bkg_only"])
    q0s = np.empty(N_T1)
    mu_hats = np.empty(N_T1)
    n_failed = 0
    toys = np.empty((N_T1, lc.N_BINS), dtype=np.int32)
    t0 = time.time()
    for i in range(N_T1):
        toy = lc.generate_toy(rng, TRUE_B)
        toys[i] = toy
        null = lc.fit_bkg_only(toy, NODES, WEIGHTS)
        alt = lc.fit_full(toy, EDGES, NODES, WEIGHTS, s_ref=1.0, mh=lc.MH_NOMINAL,
                           sigma=lc.SIGMA_NOMINAL)
        if not (null["valid"] and alt["valid"]):
            n_failed += 1
            q0s[i] = np.nan
            mu_hats[i] = np.nan
            continue
        mu_hats[i] = alt["mu_hat"]
        q0s[i] = lc.q0_from_nll(null["nll"], alt["nll"], alt["mu_hat"])
    dt = time.time() - t0
    log(f"T1: done in {dt:.1f}s ({dt/N_T1*1000:.2f} ms/toy), {n_failed} failed fits")

    valid = ~np.isnan(q0s)
    n_valid = int(valid.sum())
    q0v = q0s[valid]
    muv = mu_hats[valid]
    zs = np.sqrt(q0v)

    frac_mu_leq0, p0, band, ok_mu = binomial_3sigma(int(np.sum(muv <= 0)), n_valid, 0.5)

    tail_results = {}
    for z_thresh in (1, 2, 3):
        k = int(np.sum(zs >= z_thresh))
        phat, p0t, band_t, ok = binomial_3sigma(k, n_valid, 1 - stats.norm.cdf(z_thresh))
        tail_results[str(z_thresh)] = {
            "toy_fraction": phat, "asymptotic": p0t, "band_3sigma": band_t, "pass": bool(ok),
        }

    # Plot: q0 distribution (log y) vs half-delta(0) + half-chi2_1
    fig, ax = plt.subplots(figsize=(6.5, 5))
    bins = np.linspace(0, 25, 101)
    ax.hist(q0v, bins=bins, density=True, histtype="stepfilled", alpha=0.5,
            color="tab:blue", label=f"T1 toys (N={n_valid})")
    xx = np.linspace(0.05, 25, 400)
    ax.plot(xx, 0.5 * stats.chi2(df=1).pdf(xx), "r-", lw=1.8,
            label=r"asymptotic: $\frac{1}{2}\delta(0)+\frac{1}{2}\chi^2_1$")
    ax.axvline(0, color="r", ls="--", lw=1)
    ax.set_yscale("log")
    ax.set_xlim(0, 25)
    ax.set_ylim(1e-5, 5)
    ax.set_xlabel(r"$q_0$")
    ax.set_ylabel("probability density")
    ax.set_title("T1: background-only $q_0$ distribution vs. asymptotic prediction")
    ax.legend(loc="upper right", fontsize=9)
    fig.tight_layout()
    fig.savefig(RESULTS_DIR / "T1_q0_distribution.png", dpi=140)
    plt.close(fig)

    return {
        "n_toys": N_T1, "n_valid": n_valid, "n_failed": n_failed,
        "seed": SEEDS["T1_bkg_only"],
        "frac_mu_hat_leq_0": {"toy": frac_mu_leq0, "expected": p0, "band_3sigma": band,
                               "pass": bool(ok_mu)},
        "tail_fractions": tail_results,
        "runtime_s": dt,
    }, toys, q0v, muv


# ----------------------------------------------------------------------------
# Find s_ref for a target Asimov Z (used by T2 and reused by T3)
# ----------------------------------------------------------------------------

def asimov_z_full_model(s_ref: float) -> float:
    nu = lc.asimov_expectation(1.0, s_ref, lc.MH_NOMINAL, lc.SIGMA_NOMINAL,
                                lc.N_BKG_TRUE, TRUE_COEFFS, EDGES, NODES, WEIGHTS)
    null = lc.fit_bkg_only(nu, NODES, WEIGHTS)
    alt = lc.fit_full(nu, EDGES, NODES, WEIGHTS, s_ref=s_ref, mh=lc.MH_NOMINAL,
                       sigma=lc.SIGMA_NOMINAL, mu_start=1.0)
    q0 = lc.q0_from_nll(null["nll"], alt["nll"], alt["mu_hat"])
    return lc.z_from_q0(q0)


def find_s_ref_for_z(target_z: float, bracket=(1.0, 30000.0)) -> float:
    f = lambda s: asimov_z_full_model(s) - target_z
    return float(brentq(f, bracket[0], bracket[1], xtol=1e-2, rtol=1e-6))


# ----------------------------------------------------------------------------
# T2: signal+background toys at 4 strengths
# ----------------------------------------------------------------------------

def signal_window_S_over_sqrtB(s_ref: float) -> dict:
    lo, hi = lc.MH_NOMINAL - 2 * lc.SIGMA_NOMINAL, lc.MH_NOMINAL + 2 * lc.SIGMA_NOMINAL
    in_win = (CENTERS >= lo) & (CENTERS <= hi)
    S = float(lc.signal_bin_expectation(EDGES, 1.0, s_ref, lc.MH_NOMINAL, lc.SIGMA_NOMINAL)[in_win].sum())
    B = float(TRUE_B[in_win].sum())
    return {"window_GeV": [lo, hi], "S": S, "B": B, "S_over_sqrtB": S / np.sqrt(B)}


def run_t2():
    targets = {"z1": 1.0, "z2": 2.0, "z3": 3.0, "z5": 5.0}
    log("T2: solving for s_ref at each target Asimov Z...")
    s_refs = {}
    for key, z in targets.items():
        s_refs[key] = find_s_ref_for_z(z)
        achieved = asimov_z_full_model(s_refs[key])
        log(f"T2: target Z={z} -> s_ref={s_refs[key]:.2f} (Asimov Z check: {achieved:.4f})")

    out = {}
    toy_cache = {}
    for key, z_target in targets.items():
        s_ref = s_refs[key]
        seed = SEEDS["T2_sig_bkg"][key]
        rng = np.random.default_rng(seed)
        true_nu = lc.asimov_expectation(1.0, s_ref, lc.MH_NOMINAL, lc.SIGMA_NOMINAL,
                                         lc.N_BKG_TRUE, TRUE_COEFFS, EDGES, NODES, WEIGHTS)
        mu_hats = np.empty(N_T2)
        mu_errs = np.empty(N_T2)
        q0s = np.empty(N_T2)
        n_failed = 0
        toys = np.empty((N_T2, lc.N_BINS), dtype=np.int32)
        t0 = time.time()
        for i in range(N_T2):
            toy = lc.generate_toy(rng, true_nu)
            toys[i] = toy
            null = lc.fit_bkg_only(toy, NODES, WEIGHTS)
            alt = lc.fit_full(toy, EDGES, NODES, WEIGHTS, s_ref=s_ref, mh=lc.MH_NOMINAL,
                               sigma=lc.SIGMA_NOMINAL, mu_start=1.0, hesse=True)
            if not (null["valid"] and alt["valid"]) or not np.isfinite(alt["mu_err"]) or alt["mu_err"] <= 0:
                n_failed += 1
                mu_hats[i] = np.nan
                mu_errs[i] = np.nan
                q0s[i] = np.nan
                continue
            mu_hats[i] = alt["mu_hat"]
            mu_errs[i] = alt["mu_err"]
            q0s[i] = lc.q0_from_nll(null["nll"], alt["nll"], alt["mu_hat"])
        dt = time.time() - t0
        log(f"T2[{key}]: done in {dt:.1f}s, {n_failed} failed fits")

        valid = ~np.isnan(mu_hats)
        n_valid = int(valid.sum())
        muv, errv, q0v = mu_hats[valid], mu_errs[valid], q0s[valid]
        pulls = (muv - 1.0) / errv
        zs = np.sqrt(q0v)
        median_z = float(np.median(zs))

        win = signal_window_S_over_sqrtB(s_ref)

        out[key] = {
            "target_asimov_z": z_target,
            "s_ref": s_ref,
            "n_toys": N_T2, "n_valid": n_valid, "n_failed": n_failed, "seed": seed,
            "mu_hat_mean": float(np.mean(muv)), "mu_hat_std": float(np.std(muv)),
            "pull_mean": float(np.mean(pulls)), "pull_std": float(np.std(pulls)),
            "pull_pass": bool(abs(np.mean(pulls)) <= 0.05 and abs(np.std(pulls) - 1.0) <= 0.05),
            "median_observed_z": median_z,
            "asimov_z": z_target,
            "median_minus_asimov": median_z - z_target,
            "median_criterion_pass": (abs(median_z - z_target) <= 0.15) if z_target >= 2 else None,
            "p_z_geq_3": float(np.mean(zs >= 3)),
            "p_z_geq_5": float(np.mean(zs >= 5)),
            "signal_window": win,
            "runtime_s": dt,
        }
        toy_cache[key] = (toys, mu_hats, mu_errs, q0s)

        # per-strength plots (pull + Z)
        fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
        axes[0].hist(muv, bins=40, color="tab:blue", alpha=0.7)
        axes[0].axvline(1.0, color="k", ls="--", lw=1, label=r"$\mu_{true}=1$")
        axes[0].set_xlabel(r"$\hat\mu$")
        axes[0].set_ylabel("toys")
        axes[0].set_title(f"T2 [{key}]: fitted signal strength")
        axes[0].legend(fontsize=8)

        axes[1].hist(pulls, bins=40, color="tab:orange", alpha=0.7, density=True)
        xx = np.linspace(-4, 4, 200)
        axes[1].plot(xx, stats.norm.pdf(xx), "k-", lw=1.5, label="N(0,1)")
        axes[1].set_xlabel(r"pull $(\hat\mu-\mu_{true})/\sigma(\hat\mu)$")
        axes[1].set_title(f"mean={np.mean(pulls):.3f}, width={np.std(pulls):.3f}")
        axes[1].legend(fontsize=8)
        fig.suptitle(f"T2 [{key}]: asimov Z={z_target}, s_ref={s_ref:.1f}")
        fig.tight_layout()
        fig.savefig(RESULTS_DIR / f"T2_{key}_pull.png", dpi=140)
        plt.close(fig)

    # combined Z plot across strengths
    fig, ax = plt.subplots(figsize=(7, 5))
    colors = {"z1": "tab:gray", "z2": "tab:blue", "z3": "tab:green", "z5": "tab:red"}
    for key in targets:
        toys, mu_hats, mu_errs, q0s = toy_cache[key]
        valid = ~np.isnan(q0s)
        zs = np.sqrt(q0s[valid])
        ax.hist(zs, bins=40, histtype="step", lw=1.6, color=colors[key],
                density=True, label=f"{key}: Asimov Z={targets[key]}, median={np.median(zs):.2f}")
        ax.axvline(targets[key], color=colors[key], ls=":", lw=1)
    ax.set_xlabel(r"observed $Z=\sqrt{q_0}$")
    ax.set_ylabel("probability density")
    ax.set_title("T2: observed-Z distributions vs. Asimov expectation (dotted)")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(RESULTS_DIR / "T2_Z_distributions.png", dpi=140)
    plt.close(fig)

    return out, s_refs, toy_cache


def make_example_plot(data, null_fit_b, alt_fit_coeffs, alt_fit_nbkg,
                       alt_mu, s_ref, mh, sigma, title, filename):
    """One example toy: data + background-only fit + S+B fit + residual panel."""
    b_null = lc.background_bin_expectation(NODES, WEIGHTS, null_fit_b["n_bkg"], null_fit_b["coeffs"])
    b_alt = lc.background_bin_expectation(NODES, WEIGHTS, alt_fit_nbkg, alt_fit_coeffs)
    s_alt = lc.signal_bin_expectation(EDGES, alt_mu, s_ref, mh, sigma)
    total_alt = b_alt + s_alt

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(7.5, 6.5), sharex=True,
                                    gridspec_kw={"height_ratios": [3, 1]})
    ax1.errorbar(CENTERS, data, yerr=np.sqrt(np.clip(data, 1, None)), fmt="k.",
                 ms=4, elinewidth=0.8, label="toy data")
    ax1.plot(CENTERS, b_null, "b--", lw=1.4, label="background-only fit")
    ax1.plot(CENTERS, total_alt, "r-", lw=1.4, label="S+B fit")
    ax1.set_ylabel("events / GeV")
    ax1.set_title(title)
    ax1.legend(fontsize=8)

    resid = (data - b_null) / np.sqrt(np.clip(b_null, 1, None))
    ax2.bar(CENTERS, resid, width=lc.BIN_WIDTH * 0.9, color="tab:gray")
    ax2.axhline(0, color="k", lw=0.8)
    ax2.set_xlabel("m (GeV)")
    ax2.set_ylabel(r"(data-bkg)/$\sqrt{bkg}$")
    fig.tight_layout()
    fig.savefig(RESULTS_DIR / filename, dpi=140)
    plt.close(fig)


# ----------------------------------------------------------------------------
# T3: why profiling matters
# ----------------------------------------------------------------------------

def sideband_bkg_predict(data):
    sb_data = data[SIDEBAND_MASK]
    fit = lc.fit_bkg_only(sb_data, SIDEBAND_NODES, SIDEBAND_WEIGHTS, n_coeffs=2,
                           norm_nodes=NODES, norm_weights=WEIGHTS)
    b_full = lc.background_bin_expectation(NODES, WEIGHTS, fit["n_bkg"], fit["coeffs"],
                                            norm_nodes=NODES, norm_weights=WEIGHTS)
    return b_full, fit["valid"]


def method_bc_q0(data, bkg_fixed, s_ref):
    nll_null = lc.poisson_nll(data, bkg_fixed)
    fit = lc.fit_mu_only(data, bkg_fixed, EDGES, s_ref, lc.MH_NOMINAL, lc.SIGMA_NOMINAL)
    q0 = lc.q0_from_nll(nll_null, fit["nll"], fit["mu_hat"])
    return q0, fit["valid"]


def run_t3(bkg_toys, bkg_q0_a, sig_toys, sig_q0_a, s_ref_sig):
    log("T3: recomputing sideband-fixed and true-shape-fixed significance...")
    out = {}
    plot_data = {}
    for label, toys, q0_a, s_ref_use in [
        ("bkg_only", bkg_toys, bkg_q0_a, 1.0),
        ("sig_z2", sig_toys, sig_q0_a, s_ref_sig),
    ]:
        n = len(toys)
        q0_b = np.full(n, np.nan)
        q0_c = np.full(n, np.nan)
        n_failed_b = 0
        n_failed_c = 0
        t0 = time.time()
        for i in range(n):
            data = toys[i]
            b_side, ok_side = sideband_bkg_predict(data)
            if ok_side:
                q0b, ok_mu = method_bc_q0(data, b_side, s_ref_use)
                if ok_mu:
                    q0_b[i] = q0b
                else:
                    n_failed_b += 1
            else:
                n_failed_b += 1
            q0c, ok_muc = method_bc_q0(data, TRUE_B, s_ref_use)
            if ok_muc:
                q0_c[i] = q0c
            else:
                n_failed_c += 1
        dt = time.time() - t0
        log(f"T3[{label}]: done in {dt:.1f}s, failed b={n_failed_b}, c={n_failed_c}")

        valid_a = ~np.isnan(q0_a)
        valid_b = ~np.isnan(q0_b)
        valid_c = ~np.isnan(q0_c)
        za, zb, zc = np.sqrt(q0_a[valid_a]), np.sqrt(q0_b[valid_b]), np.sqrt(q0_c[valid_c])
        entry = {
            "n_toys": n,
            "n_failed_b": n_failed_b, "n_failed_c": n_failed_c,
            "p_z_geq_3": {
                "profiled_a": float(np.mean(za >= 3)),
                "sideband_fixed_b": float(np.mean(zb >= 3)),
                "true_shape_fixed_c": float(np.mean(zc >= 3)),
            },
            "median_z": {
                "profiled_a": float(np.median(za)),
                "sideband_fixed_b": float(np.median(zb)),
                "true_shape_fixed_c": float(np.median(zc)),
            },
            "runtime_s": dt,
        }
        out[label] = entry
        plot_data[label] = (za, zb, zc)

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    for ax, label in zip(axes, ["bkg_only", "sig_z2"]):
        za, zb, zc = plot_data[label]
        bins = np.linspace(0, 8, 60)
        ax.hist(za, bins=bins, histtype="step", density=True, lw=1.6, color="tab:blue",
                label="(a) profiled")
        ax.hist(zb, bins=bins, histtype="step", density=True, lw=1.6, color="tab:orange",
                label="(b) sideband-fixed bkg")
        ax.hist(zc, bins=bins, histtype="step", density=True, lw=1.6, color="tab:green",
                label="(c) true-shape bkg (ideal)")
        ax.set_yscale("log")
        ax.set_xlabel("Z")
        ax.set_title("background-only toys" if label == "bkg_only" else "signal toys (Asimov Z=2)")
        ax.legend(fontsize=8)
    fig.suptitle("T3: effect of how the background is treated on significance")
    fig.tight_layout()
    fig.savefig(RESULTS_DIR / "T3_method_comparison.png", dpi=140)
    plt.close(fig)

    return out


# ----------------------------------------------------------------------------
# T4: look-elsewhere effect
# ----------------------------------------------------------------------------

def run_t4():
    log(f"T4: {N_T4} background-only toys, scanning {len(T4_MASS_POINTS)} mass points each...")
    rng = np.random.default_rng(SEEDS["T4_lee"])
    s_ref = 100.0
    u0 = 1.0  # Gross-Vitells low reference level (Z0 = 1)
    max_local_z = np.full(N_T4, np.nan)
    upcross_u0 = np.full(N_T4, np.nan)
    n_failed = 0
    t0 = time.time()
    for i in range(N_T4):
        toy = lc.generate_toy(rng, TRUE_B)
        null = lc.fit_bkg_only(toy, NODES, WEIGHTS)
        if not null["valid"]:
            n_failed += 1
            continue
        local_q0 = np.full(len(T4_MASS_POINTS), np.nan)
        bkg_start = [null["n_bkg"]] + list(null["coeffs"])
        mu_start = 0.0
        ok_all = True
        for j, mh in enumerate(T4_MASS_POINTS):
            alt = lc.fit_full(toy, EDGES, NODES, WEIGHTS, s_ref=s_ref, mh=mh,
                               sigma=lc.SIGMA_NOMINAL, mu_start=max(mu_start, 0.0),
                               bkg_start=bkg_start)
            if not alt["valid"]:
                ok_all = False
                break
            local_q0[j] = lc.q0_from_nll(null["nll"], alt["nll"], alt["mu_hat"])
            bkg_start = [alt["n_bkg"]] + list(alt["coeffs"])
            mu_start = alt["mu_hat"]
        if not ok_all or np.any(np.isnan(local_q0)):
            n_failed += 1
            continue
        max_local_z[i] = np.sqrt(local_q0.max())
        above = local_q0 >= u0
        upcross_u0[i] = np.sum((~above[:-1]) & above[1:])
        if (i + 1) % 1000 == 0:
            log(f"T4: {i + 1}/{N_T4} toys done ({time.time() - t0:.0f}s elapsed)")
    dt = time.time() - t0
    log(f"T4: done in {dt:.1f}s ({dt/N_T4*1000:.2f} ms/toy), {n_failed} failed")

    valid = ~np.isnan(max_local_z)
    n_valid = int(valid.sum())
    mlz = max_local_z[valid]
    n_up_mean = float(np.mean(upcross_u0[valid]))

    global_p = {}
    for z in (2.0, 3.0, 4.0):
        p_toy = float(np.mean(mlz >= z))
        p_local = float(1 - stats.norm.cdf(z))
        u = z * z
        p_gv = float((1 - stats.norm.cdf(z)) + n_up_mean * np.exp(-(u - u0) / 2.0)) if u >= u0 else None
        trials_factor = (p_toy / p_local) if p_toy > 0 else None
        global_p[str(z)] = {
            "toy_global_p": p_toy,
            "local_p": p_local,
            "implied_trials_factor": trials_factor,
            "gross_vitells_global_p": p_gv,
        }

    # Plot: survival function of max local Z (toy-based) vs GV formula vs naive local
    fig, ax = plt.subplots(figsize=(6.5, 5))
    zz = np.sort(mlz)
    surv = 1.0 - np.arange(1, len(zz) + 1) / len(zz)
    ax.step(zz, np.clip(surv, 1.0 / len(zz) / 2, None), where="post", color="tab:blue",
            label=f"toy-based P(max local Z > z), N={n_valid}")
    zgrid = np.linspace(0.5, 5, 200)
    p_local_grid = 1 - stats.norm.cdf(zgrid)
    p_gv_grid = np.where(zgrid ** 2 >= u0,
                         p_local_grid + n_up_mean * np.exp(-(zgrid ** 2 - u0) / 2.0),
                         np.nan)
    ax.plot(zgrid, p_gv_grid, "r-", lw=1.6, label=f"Gross-Vitells estimate (<N(u0={u0})>={n_up_mean:.3f})")
    ax.plot(zgrid, p_local_grid, "k--", lw=1.2, label="naive local p-value (no LEE correction)")
    ax.set_yscale("log")
    ax.set_xlabel("Z")
    ax.set_ylabel("global p-value / survival probability")
    ax.set_title("T4: look-elsewhere effect, mass scan 110-150 GeV")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(RESULTS_DIR / "T4_max_local_Z.png", dpi=140)
    plt.close(fig)

    return {
        "n_toys": N_T4, "n_valid": n_valid, "n_failed": n_failed,
        "seed": SEEDS["T4_lee"], "mass_scan_points": len(T4_MASS_POINTS),
        "mass_scan_range_GeV": [float(T4_MASS_POINTS[0]), float(T4_MASS_POINTS[-1])],
        "gv_reference_level_u0": u0, "gv_mean_upcrossings_at_u0": n_up_mean,
        "global_p_values": global_p, "runtime_s": dt,
    }


# ----------------------------------------------------------------------------
# T5: spurious signal from a wrong background function
# ----------------------------------------------------------------------------

def run_t5():
    log(f"T5: {N_T5} true-shape toys, fit with 3 background models...")
    rng = np.random.default_rng(SEEDS["T5_spurious"])
    s_ref = 500.0
    toys = np.array([lc.generate_toy(rng, TRUE_B) for _ in range(N_T5)], dtype=np.int32)

    models = {"correct_quadratic": 2, "too_simple_exp": 1, "flexible_cubic": 3}
    out = {}
    example_fits = {}
    t0_all = time.time()
    for name, n_coeffs in models.items():
        mu_hats = np.full(N_T5, np.nan)
        mu_errs = np.full(N_T5, np.nan)
        zs = np.full(N_T5, np.nan)
        n_failed = 0
        t0 = time.time()
        for i in range(N_T5):
            toy = toys[i]
            null = lc.fit_bkg_only(toy, NODES, WEIGHTS, n_coeffs=n_coeffs)
            alt = lc.fit_full(toy, EDGES, NODES, WEIGHTS, s_ref=s_ref, mh=lc.MH_NOMINAL,
                               sigma=lc.SIGMA_NOMINAL, n_coeffs=n_coeffs, hesse=True)
            if not (null["valid"] and alt["valid"]) or not np.isfinite(alt["mu_err"]) or alt["mu_err"] <= 0:
                n_failed += 1
                continue
            mu_hats[i] = alt["mu_hat"]
            mu_errs[i] = alt["mu_err"]
            q0 = lc.q0_from_nll(null["nll"], alt["nll"], alt["mu_hat"])
            zs[i] = np.sqrt(q0)
            if i == 0:
                example_fits[name] = dict(alt)
        dt = time.time() - t0
        log(f"T5[{name}]: done in {dt:.1f}s, {n_failed} failed")

        valid = ~np.isnan(mu_hats)
        n_valid = int(valid.sum())
        mean_yield = float(s_ref * np.mean(mu_hats[valid]))
        mean_unc = float(s_ref * np.mean(mu_errs[valid]))
        frac_of_unc = mean_yield / mean_unc if mean_unc > 0 else None
        zv = zs[valid]
        out[name] = {
            "n_coeffs": n_coeffs, "n_toys": N_T5, "n_valid": n_valid, "n_failed": n_failed,
            "mean_spurious_signal_events": mean_yield,
            "mean_statistical_uncertainty_events": mean_unc,
            "spurious_over_uncertainty": frac_of_unc,
            "atlas_style_20pct_criterion_pass": (abs(frac_of_unc) < 0.20) if frac_of_unc is not None else None,
            "p_z_geq_2": float(np.mean(zv >= 2)),
            "p_z_geq_3": float(np.mean(zv >= 3)),
            "runtime_s": dt,
        }
    log(f"T5: total {time.time() - t0_all:.1f}s")

    # Example toy plot: data + all three fits
    fig, ax = plt.subplots(figsize=(7.5, 5))
    data0 = toys[0]
    ax.errorbar(CENTERS, data0, yerr=np.sqrt(np.clip(data0, 1, None)), fmt="k.", ms=4,
                elinewidth=0.8, label="toy data")
    colors = {"correct_quadratic": "tab:green", "too_simple_exp": "tab:red",
              "flexible_cubic": "tab:purple"}
    for name, n_coeffs in models.items():
        fit = example_fits[name]
        b = lc.background_bin_expectation(NODES, WEIGHTS, fit["n_bkg"], fit["coeffs"])
        s = lc.signal_bin_expectation(EDGES, fit["mu_hat"], s_ref, lc.MH_NOMINAL, lc.SIGMA_NOMINAL)
        ax.plot(CENTERS, b + s, "-", lw=1.5, color=colors[name],
                label=f"{name} (fitted signal={fit['mu_hat']*s_ref:.0f} evt)")
    ax.set_xlabel("m (GeV)")
    ax.set_ylabel("events / GeV")
    ax.set_title("T5: same background-only toy, three different fitted shapes")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(RESULTS_DIR / "T5_example_toy_three_fits.png", dpi=140)
    plt.close(fig)

    # Summary bar plot
    fig, ax = plt.subplots(figsize=(6.5, 5))
    names = list(models.keys())
    ratios = [out[n]["spurious_over_uncertainty"] for n in names]
    ax.bar(names, ratios, color=["tab:green", "tab:red", "tab:purple"])
    ax.axhline(0.20, color="k", ls="--", lw=1, label="example ATLAS-style bound (0.20)")
    ax.axhline(-0.20, color="k", ls="--", lw=1)
    ax.axhline(0, color="k", lw=0.8)
    ax.set_ylabel("spurious signal / statistical uncertainty")
    ax.set_title("T5: spurious signal by background model")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(RESULTS_DIR / "T5_summary.png", dpi=140)
    plt.close(fig)

    return out


# ----------------------------------------------------------------------------
# T6: the floating-width trap
# ----------------------------------------------------------------------------

def run_t6():
    log(f"T6: {N_T6} true-shape toys, too-simple background, fixed vs floating width...")
    rng = np.random.default_rng(SEEDS["T6_floating_width"])
    s_ref = 500.0
    toys = np.array([lc.generate_toy(rng, TRUE_B) for _ in range(N_T6)], dtype=np.int32)

    z_fixed = np.full(N_T6, np.nan)
    z_floating = np.full(N_T6, np.nan)
    sigma_hat = np.full(N_T6, np.nan)
    n_failed_fixed = 0
    n_failed_floating = 0
    t0 = time.time()
    for i in range(N_T6):
        toy = toys[i]
        null = lc.fit_bkg_only(toy, NODES, WEIGHTS, n_coeffs=1)
        if not null["valid"]:
            n_failed_fixed += 1
            n_failed_floating += 1
            continue
        alt_fixed = lc.fit_full(toy, EDGES, NODES, WEIGHTS, s_ref=s_ref, mh=lc.MH_NOMINAL,
                                 sigma=lc.SIGMA_NOMINAL, n_coeffs=1)
        if alt_fixed["valid"]:
            q0f = lc.q0_from_nll(null["nll"], alt_fixed["nll"], alt_fixed["mu_hat"])
            z_fixed[i] = np.sqrt(q0f)
        else:
            n_failed_fixed += 1

        alt_float = lc.fit_full_floating_width(toy, EDGES, NODES, WEIGHTS, s_ref=s_ref,
                                                mh=lc.MH_NOMINAL, n_coeffs=1)
        if alt_float["valid"]:
            q0v = lc.q0_from_nll(null["nll"], alt_float["nll"], alt_float["mu_hat"])
            z_floating[i] = np.sqrt(q0v)
            sigma_hat[i] = alt_float["sigma_hat"]
        else:
            n_failed_floating += 1
    dt = time.time() - t0
    log(f"T6: done in {dt:.1f}s, failed fixed={n_failed_fixed}, floating={n_failed_floating}")

    zf_valid = z_fixed[~np.isnan(z_fixed)]
    zv_valid = z_floating[~np.isnan(z_floating)]
    sig_valid = sigma_hat[~np.isnan(sigma_hat)]

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    bins = np.linspace(0, 8, 50)
    axes[0].hist(zf_valid, bins=bins, histtype="step", density=True, lw=1.6, color="tab:blue",
                 label="width fixed at 2.0 GeV")
    axes[0].hist(zv_valid, bins=bins, histtype="step", density=True, lw=1.6, color="tab:red",
                 label="width floating (0.5-15 GeV)")
    axes[0].set_yscale("log")
    axes[0].set_xlabel("Z")
    axes[0].set_title("T6: significance, fixed vs. floating width")
    axes[0].legend(fontsize=8)

    axes[1].hist(sig_valid, bins=40, color="tab:red", alpha=0.7)
    axes[1].axvline(lc.SIGMA_NOMINAL, color="k", ls="--", lw=1, label="true width (2.0 GeV)")
    axes[1].set_xlabel(r"fitted width $\hat\sigma$ (GeV)")
    axes[1].set_title("Fitted width when left floating")
    axes[1].legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(RESULTS_DIR / "T6_floating_width.png", dpi=140)
    plt.close(fig)

    return {
        "n_toys": N_T6, "seed": SEEDS["T6_floating_width"],
        "n_failed_fixed": n_failed_fixed, "n_failed_floating": n_failed_floating,
        "fixed_width": {"p_z_geq_3": float(np.mean(zf_valid >= 3)), "n_valid": int(len(zf_valid))},
        "floating_width": {"p_z_geq_3": float(np.mean(zv_valid >= 3)), "n_valid": int(len(zv_valid)),
                            "sigma_hat_mean": float(np.mean(sig_valid)),
                            "sigma_hat_median": float(np.median(sig_valid))},
        "runtime_s": dt,
    }


# ----------------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------------

def to_jsonable(obj):
    if isinstance(obj, dict):
        return {k: to_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [to_jsonable(v) for v in obj]
    if isinstance(obj, (np.floating, np.integer)):
        return obj.item()
    if isinstance(obj, np.bool_):
        return bool(obj)
    return obj


if __name__ == "__main__":
    t_start = time.time()
    results = {"seeds": SEEDS, "model": {
        "mass_range_GeV": [lc.MASS_MIN, lc.MASS_MAX], "n_bins": lc.N_BINS,
        "p1_true": lc.P1_TRUE, "p2_true": lc.P2_TRUE, "n_bkg_true": lc.N_BKG_TRUE,
        "mh_nominal": lc.MH_NOMINAL, "sigma_nominal": lc.SIGMA_NOMINAL,
        "background_drop_factor_100_to_180": float(TRUE_B[0] / TRUE_B[-1]),
    }}

    log("=== T1 ===")
    t1_summary, t1_toys, t1_q0, t1_mu = run_t1()
    results["T1"] = t1_summary

    log("=== T2 ===")
    t2_summary, s_refs, t2_cache = run_t2()
    results["T2"] = t2_summary

    log("=== example plots ===")
    ex_bkg_idx = 0
    null_ex = lc.fit_bkg_only(t1_toys[ex_bkg_idx], NODES, WEIGHTS)
    alt_ex = lc.fit_full(t1_toys[ex_bkg_idx], EDGES, NODES, WEIGHTS, s_ref=1.0,
                          mh=lc.MH_NOMINAL, sigma=lc.SIGMA_NOMINAL)
    make_example_plot(t1_toys[ex_bkg_idx], null_ex, alt_ex["coeffs"], alt_ex["n_bkg"],
                       alt_ex["mu_hat"], 1.0, lc.MH_NOMINAL, lc.SIGMA_NOMINAL,
                       "Example background-only toy", "example_bkg_only_toy.png")

    z3_toys, z3_mu, z3_err, z3_q0 = t2_cache["z3"]
    ex_sig_idx = 0
    s_ref_z3 = s_refs["z3"]
    null_ex2 = lc.fit_bkg_only(z3_toys[ex_sig_idx], NODES, WEIGHTS)
    alt_ex2 = lc.fit_full(z3_toys[ex_sig_idx], EDGES, NODES, WEIGHTS, s_ref=s_ref_z3,
                           mh=lc.MH_NOMINAL, sigma=lc.SIGMA_NOMINAL, mu_start=1.0)
    make_example_plot(z3_toys[ex_sig_idx], null_ex2, alt_ex2["coeffs"], alt_ex2["n_bkg"],
                       alt_ex2["mu_hat"], s_ref_z3, lc.MH_NOMINAL, lc.SIGMA_NOMINAL,
                       f"Example toy, Asimov Z=3 (mu_hat={alt_ex2['mu_hat']:.2f})",
                       "example_Z3_toy.png")

    log("=== T3 ===")
    z2_toys, z2_mu, z2_err, z2_q0 = t2_cache["z2"]
    t3_summary = run_t3(t1_toys, t1_q0, z2_toys, z2_q0, s_refs["z2"])
    results["T3"] = t3_summary

    log("=== T4 ===")
    t4_summary = run_t4()
    results["T4"] = t4_summary

    log("=== T5 ===")
    t5_summary = run_t5()
    results["T5"] = t5_summary

    log("=== T6 ===")
    t6_summary = run_t6()
    results["T6"] = t6_summary

    results["total_runtime_s"] = time.time() - t_start
    with open(RESULTS_DIR / "toy_study_results.json", "w") as f:
        json.dump(to_jsonable(results), f, indent=2)
    log(f"ALL DONE in {results['total_runtime_s']:.1f}s "
        f"({results['total_runtime_s']/60:.1f} min). "
        f"Wrote {RESULTS_DIR / 'toy_study_results.json'}")
