#!/usr/bin/env python3
"""
ttbar_btag_event_multiplicity_real_pipeline.py - per-event tagged-jet
multiplicity vs a binomial model, computed from the REAL services/parsing
pipeline output (Jets + BJets, truth carried through via include_truth_flavour)
instead of the earlier standalone script's raw-branch reimplementation.

This redoes scripts/ttbar_btag_event_multiplicity.py's measurement (same
branch) on real, already-parsed pipeline output from
config.cms_ttbar_truth_crosscheck.yaml (eta_max: 2.5, pt_min: 30.0) -- the
same production-matching window used for the per-jet three-way comparison
already on this branch (reports/ttbar_btag_truth_crosscheck/stats_real_pipeline.json).

"Tagged" here is exactly what the real pipeline decided: a jet landed in the
BJets collection. Per the Step 1 finding already documented on this branch,
BJets carries NO kinematic cut from the pipeline itself, so this script
applies the SAME (pT>30, |eta|<2.5) window to both Jets- and BJets-origin jets
at read time, using their own real, carried-through pt/eta fields -- a
reporting-time slice of already-decided fields, not new selection logic.

Needs no XRootD -- reads the already-parsed local ROOT chunks directly:

    python scripts/ttbar_btag_event_multiplicity_real_pipeline.py \
        --run-dir output/cms_ttbar_truth_crosscheck_eta2p5_TIMESTAMP \
        --out-dir reports/ttbar_btag_truth_crosscheck
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

THRESHOLD = 0.25
PT_MIN, ETA_MAX = 30.0, 2.5
N_TRUE_B_QUARKS_PER_EVENT = 2  # semileptonic ttbar: t->Wb, tbar->Wbar bbar


def load_per_event_counts(run_dir: Path):
    """Per event: (n_eligible, n_tagged_eligible, n_true_b_tagged_eligible),
    from the real parsed Jets/BJets collections, window applied to both."""
    import awkward as ak
    import uproot

    parsed = sorted(run_dir.glob("parsed_data/*.root"))
    if not parsed:
        raise FileNotFoundError(f"no parsed .root chunks in {run_dir/'parsed_data'}")

    n_elig_parts, n_tag_parts, n_trueb_parts = [], [], []
    n_events = 0
    file_rows = []
    for chunk in parsed:
        arr = uproot.open(chunk)["events"].arrays(
            ["Jets_pt", "Jets_eta", "BJets_pt", "BJets_eta", "BJets_hadronFlavour"],
            library="ak",
        )
        n_ev = len(arr)
        n_events += n_ev
        file_rows.append({"file": chunk.name, "events": n_ev})

        elig_jets = (arr["Jets_pt"] > PT_MIN) & (abs(arr["Jets_eta"]) < ETA_MAX)
        elig_bjets = (arr["BJets_pt"] > PT_MIN) & (abs(arr["BJets_eta"]) < ETA_MAX)
        true_b = arr["BJets_hadronFlavour"] == 5

        n_elig = ak.sum(elig_jets, axis=1) + ak.sum(elig_bjets, axis=1)
        n_tag = ak.sum(elig_bjets, axis=1)  # every BJets-origin jet IS tagged
        n_trueb = ak.sum(elig_bjets & true_b, axis=1)

        n_elig_parts.append(ak.to_numpy(n_elig).astype(np.int64))
        n_tag_parts.append(ak.to_numpy(n_tag).astype(np.int64))
        n_trueb_parts.append(ak.to_numpy(n_trueb).astype(np.int64))

    return (
        n_events,
        np.concatenate(n_elig_parts),
        np.concatenate(n_tag_parts),
        np.concatenate(n_trueb_parts),
        file_rows,
    )


def multiplicity_dist(counts: np.ndarray, cap: int = 4) -> dict:
    n_events = counts.size
    dist = {}
    for k in range(cap):
        n_k = int((counts == k).sum())
        dist[str(k)] = {"n_events": n_k, "frac": n_k / n_events if n_events else 0.0}
    n_ge = int((counts >= cap).sum())
    dist[f">={cap}"] = {"n_events": n_ge, "frac": n_ge / n_events if n_events else 0.0}
    return dist


def binomial_pmf(n_trials: int, p: float) -> list[float]:
    return [math.comb(n_trials, k) * (p ** k) * ((1 - p) ** (n_trials - k))
            for k in range(n_trials + 1)]


def plot_multiplicity_vs_binomial(dist: dict, binom: list[float], p: float,
                                   n_events: int, out_png: Path) -> None:
    cats = ["0", "1", "2", "3", ">=4"]
    observed_pct = [dist[c]["frac"] * 100 for c in cats]
    binom_pct = [binom[0] * 100, binom[1] * 100, binom[2] * 100, 0.0, 0.0]

    x = np.arange(len(cats))
    w = 0.38
    fig, ax = plt.subplots(figsize=(9, 5.6))
    b1 = ax.bar(x - w / 2, observed_pct, w, color="#3b6ea5",
                label=f"observed, REAL pipeline output  ({n_events:,} events)")
    b2 = ax.bar(x + w / 2, binom_pct, w, color="#c1272d", alpha=0.85,
                label=f"binomial model  (2 trials, p={p:.4f} from this run's own "
                      f"measured b-efficiency)")
    for bars in (b1, b2):
        for rect in bars:
            h = rect.get_height()
            ax.text(rect.get_x() + rect.get_width() / 2, h, f"{h:.1f}%",
                    ha="center", va="bottom", fontsize=8)
    ax.set_xticks(x)
    ax.set_xticklabels([f"{c} tagged" for c in cats])
    ax.set_ylabel("% of events")
    ax.set_title(
        "Tagged-jet multiplicity per event, REAL services/parsing pipeline output\n"
        "(pT>30 GeV, |eta|<2.5 applied to Jets AND BJets at read time) vs a "
        "simple 2-b-quark binomial model",
        fontsize=9.3)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(out_png, dpi=130)
    plt.close(fig)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True, type=Path)
    ap.add_argument("--out-dir", required=True, type=Path)
    args = ap.parse_args()

    out = args.out_dir
    (out / "plots").mkdir(parents=True, exist_ok=True)

    # p (b-efficiency) comes from this branch's own already-computed real-
    # pipeline eta<2.5 result -- not retyped or assumed.
    prior = json.loads((out / "stats_real_pipeline.json").read_text())
    r = prior["real_pipeline_results"]["eta2p5"]
    assert r["eta_max"] == ETA_MAX and r["pt_min"] == PT_MIN, (
        f"stats_real_pipeline.json eta2p5 window ({r['eta_max']}, {r['pt_min']}) "
        f"doesn't match this script's ({ETA_MAX}, {PT_MIN})"
    )
    p_b_eff = r["windowed_pt_gt_30_eta_window_applied_to_both_collections"]["b"]["rate"]
    print(f"p (b-efficiency, real pipeline, eta<2.5) = {p_b_eff:.6f} "
          f"(source: {out/'stats_real_pipeline.json'} -> "
          f"real_pipeline_results.eta2p5..., run_dir={r['run_dir']})")

    run_dir = args.run_dir
    n_events, n_elig, n_tag, n_trueb, file_rows = load_per_event_counts(run_dir)
    print(f"loaded {n_events:,} events from {len(file_rows)} chunk(s) in {run_dir}")

    tag_dist = multiplicity_dist(n_tag, cap=4)
    trueb_dist = multiplicity_dist(n_trueb, cap=3)
    binom = binomial_pmf(N_TRUE_B_QUARKS_PER_EVENT, p_b_eff)

    n_tagged_total = int(n_tag.sum())
    n_eligible_total = int(n_elig.sum())
    mean_tagged = float(n_tag.mean())
    mean_trueb_tagged = float(n_trueb.mean())
    frac_0 = tag_dist["0"]["frac"]
    frac_1 = tag_dist["1"]["frac"]
    frac_ge2 = 1.0 - frac_0 - frac_1

    stats = {
        "source": "real services/parsing pipeline output (Jets + BJets, "
                   "include_truth_flavour), NOT the standalone script",
        "run_dir": str(run_dir),
        "config": "config.cms_ttbar_truth_crosscheck.yaml",
        "threshold": THRESHOLD,
        "window": {"pt_min_gev": PT_MIN, "abseta_max": ETA_MAX,
                   "applied_to": "both Jets- and BJets-origin jets (BJets "
                                  "receives no kinematic cut from the "
                                  "pipeline itself -- see Step 1 finding)"},
        "files": file_rows,
        "n_events": n_events,
        "n_eligible_jets_total": n_eligible_total,
        "n_tagged_jets_total": n_tagged_total,
        "n_untagged_jets_total": n_eligible_total - n_tagged_total,
        "overall_tagged_fraction": (n_tagged_total / n_eligible_total)
        if n_eligible_total else None,
        "mean_tagged_jets_per_event": mean_tagged,
        "pct_events_0_tags": frac_0 * 100,
        "pct_events_1_tag": frac_1 * 100,
        "pct_events_ge2_tags": frac_ge2 * 100,
        "tagged_jet_multiplicity_any_flavour": tag_dist,
        "binomial_model": {
            "n_trials": N_TRUE_B_QUARKS_PER_EVENT,
            "p_used": p_b_eff,
            "p_source": "reports/ttbar_btag_truth_crosscheck/stats_real_pipeline.json "
                        "-> real_pipeline_results.eta2p5."
                        "windowed_pt_gt_30_eta_window_applied_to_both_collections.b.rate",
            "P0": binom[0], "P1": binom[1], "P2": binom[2],
        },
        "true_b_jets_correctly_tagged_per_event": {
            "mean": mean_trueb_tagged,
            "distribution": trueb_dist,
        },
    }
    (out / "event_multiplicity_stats_real_pipeline.json").write_text(
        json.dumps(stats, indent=2)
    )
    print(json.dumps(stats, indent=2))

    plot_multiplicity_vs_binomial(
        tag_dist, binom, p_b_eff, n_events,
        out / "plots" / "btag_event_multiplicity_vs_binomial_real_pipeline.png",
    )
    print("DONE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
