"""
Part B: redo the earlier toy study's floating-width trap (T6), this time
with a background mismatch chosen (BEFORE generating any toys) to produce
a fake EXCESS rather than the fake deficit found before.

Calibration on the noiseless Asimov dataset (done first, recorded here,
never adjusted after looking at toys):
Same framework as studies/lr_toys: exp(p1.x + p2.x^2) background,
x=(m-100)/80, mass 100-180 GeV, 1 GeV bins, 250,000 events. The ORIGINAL
toy study used p1=-4.0, p2=+0.8. Flipping p2's sign (keeping p1+p2 = -3.2,
the same target as before, so the 100-to-180-GeV drop factor stays ~20-30x)
and re-solving p1 for each candidate:

  p1=-2.40, p2=-0.80  drop=23.57x  Asimov mu_hat (too-simple exp fit) = +1543.8
  p1=-2.20, p2=-1.00  drop=23.57x  mu_hat = +1936.1
  p1=-2.00, p2=-1.20  drop=23.57x  mu_hat = +2332.1
  p1=-1.70, p2=-1.50  drop=23.57x  mu_hat = +2929.9
  p1=-1.20, p2=-2.00  drop=23.57x  mu_hat = +3934.4
  p1=-0.70, p2=-2.50  drop=23.57x  mu_hat = +4944.5
  p1=-0.20, p2=-3.00  drop=23.56x  mu_hat = +5958.5

The FIRST candidate tried (p1=-2.40, p2=-0.80 -- the direct sign-flip of
the original |p2|=0.8, keeping the comparison to the earlier study as
parallel as possible) already gives a clearly POSITIVE fitted signal on
the noiseless Asimov dataset, both fits valid. No further adjustment was
needed. FINAL CHOICE: p1=-2.40, p2=-0.80.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy import stats

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "lr_toys"))
import lr_core as lc

HERE = Path(__file__).parent
RESULTS_DIR = HERE / "results"
RESULTS_DIR.mkdir(exist_ok=True)

P1_TRUE_B, P2_TRUE_B = -2.40, -0.80
N_TOYS = 2000
SEED = 80_001
S_REF = 500.0
SIGMA_TRUE = 2.0
MH_TRUE = 125.0

EDGES = lc.bin_edges()
NODES, WEIGHTS = lc.gl_bin_nodes(EDGES)
TRUE_B = lc.background_bin_expectation(NODES, WEIGHTS, lc.N_BKG_TRUE, [P1_TRUE_B, P2_TRUE_B])


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def main():
    log(f"Confirmed background: drop factor = {TRUE_B[0]/TRUE_B[-1]:.2f}x, "
        f"monotonic falling = {bool(np.all(np.diff(TRUE_B) < 0))}")

    rng = np.random.default_rng(SEED)
    toys = np.array([lc.generate_toy(rng, TRUE_B) for _ in range(N_TOYS)], dtype=np.int32)

    # (a) width fixed, too-simple (1-coeff) background
    # (b) width floating, too-simple background
    # (c) correct (2-coeff) background, width floating (control)
    results = {}
    example_fits = {}
    z_arrays = {}
    sigma_arrays = {}
    valid_masks = {}
    for label, n_coeffs, float_width in [("a_fixed_width_wrong_bkg", 1, False),
                                          ("b_floating_width_wrong_bkg", 1, True),
                                          ("c_floating_width_correct_bkg", 2, True)]:
        mu_hats = np.full(N_TOYS, np.nan)
        mu_errs = np.full(N_TOYS, np.nan)
        zs = np.full(N_TOYS, np.nan)
        sigma_hats = np.full(N_TOYS, np.nan)
        n_failed = 0
        t0 = time.time()
        for i in range(N_TOYS):
            toy = toys[i]
            null = lc.fit_bkg_only(toy, NODES, WEIGHTS, n_coeffs=n_coeffs)
            if not null["valid"]:
                n_failed += 1
                continue
            if float_width:
                alt = lc.fit_full_floating_width(toy, EDGES, NODES, WEIGHTS, s_ref=S_REF,
                                                  mh=MH_TRUE, n_coeffs=n_coeffs)
                mu_err = float("nan")
            else:
                alt = lc.fit_full(toy, EDGES, NODES, WEIGHTS, s_ref=S_REF, mh=MH_TRUE,
                                   sigma=SIGMA_TRUE, n_coeffs=n_coeffs, hesse=True)
                mu_err = alt["mu_err"]
            if not alt["valid"]:
                n_failed += 1
                continue
            mu_hats[i] = alt["mu_hat"]
            if not float_width and np.isfinite(mu_err) and mu_err > 0:
                mu_errs[i] = mu_err
            q0 = lc.q0_from_nll(null["nll"], alt["nll"], alt["mu_hat"])
            zs[i] = np.sqrt(q0)
            if float_width:
                sigma_hats[i] = alt["sigma_hat"]
        dt = time.time() - t0
        log(f"{label}: done in {dt:.1f}s, {n_failed} failed")

        valid = ~np.isnan(mu_hats)
        n_valid = int(valid.sum())
        # mu is a dimensionless multiplier of S_REF; multiply by S_REF to
        # report actual event counts (mu_hat alone was a bug caught by
        # comparing against the Asimov calibration's expected ~1500-event
        # scale and finding this branch's numbers ~500x too small).
        mean_yield = float(S_REF * np.mean(mu_hats[valid]))
        valid_err = ~np.isnan(mu_errs)
        mean_unc = float(S_REF * np.mean(mu_errs[valid_err])) if valid_err.sum() > 0 else None
        ratio = mean_yield / mean_unc if mean_unc else None
        zv = zs[valid]
        entry = {
            "n_coeffs": n_coeffs, "float_width": float_width, "n_toys": N_TOYS,
            "n_valid": n_valid, "n_failed": n_failed,
            "mean_spurious_signal_events": mean_yield,
            "mean_statistical_uncertainty_events": mean_unc,
            "spurious_over_uncertainty": ratio,
            "p_z_geq_2": float(np.mean(zv >= 2)),
            "p_z_geq_3": float(np.mean(zv >= 3)),
            "runtime_s": dt,
        }
        if float_width:
            sv = sigma_hats[valid]
            entry["sigma_hat_mean"] = float(np.mean(sv))
            entry["sigma_hat_median"] = float(np.median(sv))
        results[label] = entry
        z_arrays[label] = zv
        if float_width:
            sigma_arrays[label] = sigma_hats[valid]
        valid_masks[label] = valid
        log(f"  -> {entry}")

    # Pick one toy index valid under all three fits (for a fair "same toy,
    # three fits" picture), then refit it fresh for the plot -- cheap.
    common_valid = valid_masks["a_fixed_width_wrong_bkg"] & valid_masks["b_floating_width_wrong_bkg"] \
        & valid_masks["c_floating_width_correct_bkg"]
    example_idx = int(np.argmax(common_valid)) if common_valid.any() else 0
    log(f"Example toy for plot: index {example_idx} (valid under all 3 fits: {bool(common_valid.any())})")
    example_toy = toys[example_idx]
    example_fits["a_fixed_width_wrong_bkg"] = lc.fit_full(
        example_toy, EDGES, NODES, WEIGHTS, s_ref=S_REF, mh=MH_TRUE, sigma=SIGMA_TRUE, n_coeffs=1)
    example_fits["b_floating_width_wrong_bkg"] = lc.fit_full_floating_width(
        example_toy, EDGES, NODES, WEIGHTS, s_ref=S_REF, mh=MH_TRUE, n_coeffs=1)
    example_fits["c_floating_width_correct_bkg"] = lc.fit_full_floating_width(
        example_toy, EDGES, NODES, WEIGHTS, s_ref=S_REF, mh=MH_TRUE, n_coeffs=2)

    with open(RESULTS_DIR / "part_b_results.json", "w") as f:
        json.dump({
            "p1_true": P1_TRUE_B, "p2_true": P2_TRUE_B, "seed": SEED, "n_toys": N_TOYS,
            "asimov_calibration_attempts": [
                (-2.40, -0.80, 1543.8), (-2.20, -1.00, 1936.1), (-2.00, -1.20, 2332.1),
                (-1.70, -1.50, 2929.9), (-1.20, -2.00, 3934.4), (-0.70, -2.50, 4944.5),
                (-0.20, -3.00, 5958.5),
            ],
            "results": results,
        }, f, indent=2, default=float)
    log(f"Wrote {RESULTS_DIR / 'part_b_results.json'}")

    # --- Plots ---
    colors = {"a_fixed_width_wrong_bkg": "tab:blue", "b_floating_width_wrong_bkg": "tab:red",
              "c_floating_width_correct_bkg": "tab:green"}
    labels_short = {"a_fixed_width_wrong_bkg": "(a) width fixed, wrong bkg",
                    "b_floating_width_wrong_bkg": "(b) width floating, wrong bkg",
                    "c_floating_width_correct_bkg": "(c) width floating, correct bkg (control)"}

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    bins = np.linspace(0, max(30, float(np.nanmax(z_arrays["b_floating_width_wrong_bkg"])) + 2), 60)
    for label, z in z_arrays.items():
        axes[0].hist(z, bins=bins, histtype="step", density=True, lw=1.6,
                      color=colors[label], label=labels_short[label])
    axes[0].set_yscale("log")
    axes[0].set_xlabel("Z")
    axes[0].set_title("Part B: significance, fixed vs. floating width\n(background mismatch tuned for a fake EXCESS)")
    axes[0].legend(fontsize=7.5)

    for label, sv in sigma_arrays.items():
        axes[1].hist(sv, bins=40, histtype="step", lw=1.6, color=colors[label], label=labels_short[label])
    axes[1].axvline(SIGMA_TRUE, color="k", ls="--", lw=1, label=f"true width ({SIGMA_TRUE} GeV)")
    axes[1].set_xlabel(r"fitted width $\hat\sigma$ (GeV)")
    axes[1].set_title("Fitted width when left floating")
    axes[1].legend(fontsize=7.5)
    fig.tight_layout()
    fig.savefig(RESULTS_DIR / "partB_floating_width_excess.png", dpi=140)
    plt.close(fig)
    log(f"Wrote {RESULTS_DIR / 'partB_floating_width_excess.png'}")

    # --- Example toy plot: data + all three fits ---
    centers = lc.bin_centers(EDGES)
    fig, ax = plt.subplots(figsize=(7.5, 5))
    data0 = example_toy
    ax.errorbar(centers, data0, yerr=np.sqrt(np.clip(data0, 1, None)), fmt="k.", ms=4,
                elinewidth=0.8, label="toy data")
    for label, n_coeffs, float_width in [("a_fixed_width_wrong_bkg", 1, False),
                                          ("b_floating_width_wrong_bkg", 1, True),
                                          ("c_floating_width_correct_bkg", 2, True)]:
        fit = example_fits[label]
        b = lc.background_bin_expectation(NODES, WEIGHTS, fit["n_bkg"], fit["coeffs"])
        sigma_used = fit["sigma_hat"] if float_width else SIGMA_TRUE
        s = lc.signal_bin_expectation(EDGES, fit["mu_hat"], S_REF, MH_TRUE, sigma_used)
        ax.plot(centers, b + s, "-", lw=1.5, color=colors[label],
                label=f"{labels_short[label]} (signal={fit['mu_hat']*S_REF:.0f} evt)")
    ax.set_xlabel("m (GeV)")
    ax.set_ylabel("events / GeV")
    ax.set_title("Part B: same background-only toy, three fits (excess-tuned mismatch)")
    ax.legend(fontsize=7.5)
    fig.tight_layout()
    fig.savefig(RESULTS_DIR / "partB_example_toy.png", dpi=140)
    plt.close(fig)
    log(f"Wrote {RESULTS_DIR / 'partB_example_toy.png'}")

    return results, toys, example_fits


if __name__ == "__main__":
    main()
