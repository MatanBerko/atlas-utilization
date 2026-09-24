"""
Implementation task 6, Z->ee validation follow-up (17 Sep 2026), item 2:
energy scale and resolution, Ele27-fired, per category and inclusive.

FIT/SIGMA_EFF WINDOW: 80-100 GeV (stated explicitly, chosen -- before
running the data-vs-DY comparison itself -- from the raw m_ee shape in
the full 70-110 GeV energy-scale sub-sample: that wider window has
substantial non-Gaussian shoulders on both sides of the peak -- a rising
tail below ~85 GeV and a long falling tail above ~95 GeV -- that would
make BOTH a naive BW(x)CB fit and an unbinned "shortest interval
containing 68.3%" calculation describe the SURROUNDING CONTINUUM rather
than the Z resonance's own core shape if run over the full 70-110 range.
80-100 GeV (+-10 GeV around M_Z) keeps the vast majority of the genuine
resonance while still leaving real tails on both sides for the Crystal
Ball's own tail parameters to be constrained by.

PRE-SET PASS/FAIL criteria (unchanged from the original Z->ee task, see
studies/hgg_cms/validation/zee/common.py's own
PEAK_POSITION_AGREEMENT_REL_TOL / SIGMA_EFF_AGREEMENT_REL_TOL):
  |Δpeak|/peak < 0.5%, |Δsigma_eff|/sigma_eff < 10%, data vs PU-reweighted
  DY. The fit's OWN peak (BW(x)CB template maximum) is what the PASS/FAIL
  criterion is evaluated on; mode and median are reported alongside as
  descriptive cross-checks, not used for PASS/FAIL. sigma_eff68 is the
  UNBINNED shortest-interval statistic (studies.hgg_cms.validation.zee.
  common.unbinned_effective_sigma68), computed WITHIN the same 80-100 GeV
  window -- a different, model-independent quantity from the fit's own
  CB sigma parameter (which is reported too, for reference, but is not
  itself the PASS/FAIL width metric).

Bootstrap (8 replicas, full-statistics resampling) provides the
sigma_eff68 uncertainty needed for the PASS/FAIL check and the width
-correction derivation.

Runs data vs DY BOTH without and with the pileup weights from pileup.py
(item 1's "report key results both with and without") -- the WITH-PU
comparison is what the PASS/FAIL table uses (this task's own instruction
to "apply them to DY in everything below").
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from studies.hgg_cms.validation import common as main_common
from studies.hgg_cms.validation.zee import common as zc

OUT_DIR = Path(__file__).resolve().parent / "results"
PLOTS_DIR = OUT_DIR / "plots"

FIT_LO, FIT_HI = 80.0, 100.0
BIN_WIDTH = 0.5
N_BOOTSTRAP = 8
BOOTSTRAP_SEED = 20260917


def bootstrap_sigma_eff_uncertainty(mee, weights, n_boot=N_BOOTSTRAP, seed=BOOTSTRAP_SEED):
    rng = np.random.default_rng(seed)
    n = len(mee)
    vals = []
    for _ in range(n_boot):
        idx = rng.integers(0, n, size=n)
        res = zc.unbinned_effective_sigma68(mee[idx], weights[idx])
        if res["sigma_eff68"] is not None:
            vals.append(res["sigma_eff68"])
    return float(np.std(vals)) if len(vals) >= 3 else None


def analyze_one(mee, weights, label):
    t0 = time.time()
    fit = zc.fit_bw_conv_cb(mee, weights, lo=FIT_LO, hi=FIT_HI, bin_width=BIN_WIDTH)
    mode = zc.weighted_mode(mee, weights, bin_width=0.25, lo=FIT_LO, hi=FIT_HI)
    median = zc.weighted_median(mee, weights)
    sigma_eff = zc.unbinned_effective_sigma68(mee, weights)
    sigma_eff_unc = bootstrap_sigma_eff_uncertainty(mee, weights)
    elapsed = time.time() - t0
    print(f"  [{label}] n={len(mee)} fit_peak={fit['peak_GeV']:.4f} "
          f"sigma_eff={sigma_eff['sigma_eff68']:.4f}+-{sigma_eff_unc:.4f} "
          f"({elapsed:.1f}s)", flush=True)
    return {
        "n_events": int(len(mee)),
        "fit": fit,
        "mode_GeV": mode,
        "median_GeV": median,
        "sigma_eff68_GeV": sigma_eff["sigma_eff68"],
        "sigma_eff68_uncertainty_GeV": sigma_eff_unc,
        "sigma_eff68_window": [sigma_eff["window_lo"], sigma_eff["window_hi"]],
    }


def main():
    PLOTS_DIR.mkdir(parents=True, exist_ok=True)
    data_arr = zc.load_zee_data()
    dy_arr = zc.load_zee_dy()

    pu = json.loads((OUT_DIR / "pileup_weights.json").read_text(encoding="utf-8"))
    pu_edges = np.array(pu["bin_edges"])
    pu_weights = np.array(pu["weights"])

    data_mask_full = zc.energy_scale_selection_mask(data_arr)
    dy_mask_full = zc.energy_scale_selection_mask(dy_arr)

    data_mee_all = np.asarray(data_arr["m_ee"])[data_mask_full]
    data_cat_all = np.asarray(data_arr["category"])[data_mask_full]

    dy_mee_all = np.asarray(dy_arr["m_ee"])[dy_mask_full]
    dy_cat_all = np.asarray(dy_arr["category"])[dy_mask_full]
    dy_gw_all = np.asarray(dy_arr["genWeight"])[dy_mask_full]
    dy_pv_all = np.asarray(dy_arr["PV_npvsGood"])[dy_mask_full]
    dy_puw_all = main_common.apply_pileup_weight(dy_pv_all, pu_edges, pu_weights)

    results = {"fit_window": [FIT_LO, FIT_HI], "bin_width": BIN_WIDTH,
               "n_bootstrap": N_BOOTSTRAP, "per_category": {}}

    fig, axes = plt.subplots(1, 3, figsize=(18, 5))
    cats = ["inclusive"] + zc.CATEGORIES

    for ax, cat in zip(axes, cats):
        print(f"=== {cat} ===", flush=True)
        if cat == "inclusive":
            d_sel = np.ones(len(data_mee_all), dtype=bool)
            s_sel = np.ones(len(dy_mee_all), dtype=bool)
        else:
            d_sel = zc.category_mask(data_cat_all, cat)
            s_sel = zc.category_mask(dy_cat_all, cat)

        d_mee = data_mee_all[d_sel]
        d_w = np.ones(len(d_mee))
        s_mee = dy_mee_all[s_sel]
        s_gw = dy_gw_all[s_sel]
        s_puw = dy_puw_all[s_sel]

        # restrict to the fit/sigma_eff window
        d_win = (d_mee > FIT_LO) & (d_mee < FIT_HI)
        s_win = (s_mee > FIT_LO) & (s_mee < FIT_HI)

        data_res = analyze_one(d_mee[d_win], d_w[d_win], f"{cat}/data")
        dy_nopu_res = analyze_one(s_mee[s_win], s_gw[s_win], f"{cat}/DY-noPU")
        dy_pu_res = analyze_one(s_mee[s_win], (s_gw * s_puw)[s_win], f"{cat}/DY-PU")

        def compare(data_r, dy_r):
            peak_reldiff = zc.relative_difference(data_r["fit"]["peak_GeV"], dy_r["fit"]["peak_GeV"])
            sigma_reldiff = zc.relative_difference(data_r["sigma_eff68_GeV"], dy_r["sigma_eff68_GeV"])
            peak_pass = abs(peak_reldiff) < zc.PEAK_POSITION_AGREEMENT_REL_TOL
            sigma_pass = abs(sigma_reldiff) < zc.SIGMA_EFF_AGREEMENT_REL_TOL
            return {
                "peak_relative_difference": peak_reldiff,
                "sigma_eff68_relative_difference": sigma_reldiff,
                "peak_pass": bool(peak_pass), "sigma_eff_pass": bool(sigma_pass),
                "overall_pass": bool(peak_pass and sigma_pass),
            }

        comparison_pu = compare(data_res, dy_pu_res)
        comparison_nopu = compare(data_res, dy_nopu_res)

        correction = None
        if not comparison_pu["overall_pass"]:
            peak_data, peak_dy = data_res["fit"]["peak_GeV"], dy_pu_res["fit"]["peak_GeV"]
            peak_data_unc, peak_dy_unc = data_res["fit"]["peak_uncertainty_GeV"], dy_pu_res["fit"]["peak_uncertainty_GeV"]
            scale_factor = peak_data / peak_dy
            scale_factor_unc = scale_factor * np.sqrt((peak_data_unc / peak_data) ** 2 + (peak_dy_unc / peak_dy) ** 2)

            sig_data, sig_dy = data_res["sigma_eff68_GeV"], dy_pu_res["sigma_eff68_GeV"]
            sig_data_unc, sig_dy_unc = data_res["sigma_eff68_uncertainty_GeV"], dy_pu_res["sigma_eff68_uncertainty_GeV"]
            extra_smear_sq = sig_data ** 2 - sig_dy ** 2
            if extra_smear_sq > 0:
                extra_smear = float(np.sqrt(extra_smear_sq))
                extra_smear_unc = float(np.sqrt((sig_data * sig_data_unc) ** 2 + (sig_dy * sig_dy_unc) ** 2) / extra_smear)
            else:
                extra_smear = 0.0
                extra_smear_unc = None
            correction = {
                "energy_scale_factor_data_over_dy": float(scale_factor),
                "energy_scale_factor_uncertainty": float(scale_factor_unc),
                "extra_gaussian_smearing_GeV": extra_smear,
                "extra_gaussian_smearing_uncertainty_GeV": extra_smear_unc,
                "note": (
                    "NOT applied to the H->gamma-gamma signal model in this "
                    "task -- reported for the signal-model task to apply."
                ),
            }

        results["per_category"][cat] = {
            "data": data_res, "dy_no_pu": dy_nopu_res, "dy_with_pu": dy_pu_res,
            "comparison_with_pu": comparison_pu,
            "comparison_without_pu": comparison_nopu,
            "correction_if_fail": correction,
        }

        # ---- plot ----
        bins = np.arange(FIT_LO, FIT_HI + BIN_WIDTH, BIN_WIDTH)
        ax.hist(d_mee[d_win], bins=bins, density=True, histtype="step", color="#1a1a1a",
                linewidth=1.3, label="data")
        ax.hist(s_mee[s_win], bins=bins, density=True, histtype="step", color="#0072B2",
                linewidth=1.3, weights=(s_gw * s_puw)[s_win], label="DY (PU-wtd)")
        ax.axvline(data_res["fit"]["peak_GeV"], color="#1a1a1a", linestyle=":", linewidth=1.0)
        ax.axvline(dy_pu_res["fit"]["peak_GeV"], color="#0072B2", linestyle=":", linewidth=1.0)
        ax.set_title(f"{cat}: peak {data_res['fit']['peak_GeV']:.2f}/{dy_pu_res['fit']['peak_GeV']:.2f} GeV\n"
                     f"$\\sigma_{{eff}}$ {data_res['sigma_eff68_GeV']:.2f}/{dy_pu_res['sigma_eff68_GeV']:.2f} GeV "
                     f"[{'PASS' if comparison_pu['overall_pass'] else 'FAIL'}]", fontsize=9)
        ax.set_xlabel("$m_{ee}$ [GeV]")
        ax.set_ylabel("normalized")
        ax.grid(alpha=0.25, linewidth=0.5)

    axes[0].legend(fontsize=8, frameon=False)
    fig.suptitle(f"Energy scale/resolution: data vs DY, Ele27-fired, {FIT_LO:.0f}-{FIT_HI:.0f} GeV fit window")
    fig.tight_layout()
    fig.savefig(PLOTS_DIR / "energy_scale.png", dpi=150)
    plt.close(fig)

    (OUT_DIR / "energy_scale_results.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"\nwrote {OUT_DIR / 'energy_scale_results.json'} and plot to {PLOTS_DIR}")


if __name__ == "__main__":
    main()
