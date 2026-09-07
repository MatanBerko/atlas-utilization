#!/usr/bin/env python3
"""
ttbar_btag_event_multiplicity.py - per-event b-tagged jet multiplicity, a
standard ttbar b-tagging sanity check, complementary to the per-jet
score-by-true-flavour view in ttbar_btag_truth_crosscheck.py (same branch).

That script looks at individual jets; this one looks at how tags cluster
WITHIN events: how many jets per event pass the DeepJet Medium cut, compared
against a simple binomial model built from this branch's OWN measured
b-tagging efficiency (not any external number) - semileptonic ttbar has
exactly 2 true b-quarks per event (t -> Wb, tbar -> Wbar bbar), so a first
sanity model treats each event as 2 independent "trials", each tagged with
probability p = the b-tagging efficiency already measured on this branch.

Re-reads the SAME 3 files (same record 67993, same filenames) used by
ttbar_btag_truth_crosscheck.py - that script never saved local ROOT copies
(it streams via uproot.open(url) straight from XRootD into arrays, keeping
none of the raw files on disk), so there is nothing to reuse locally; this
does a fresh, but identically-scoped, read. File list and the measured
b-efficiency for the binomial model are both read directly out of the
existing reports/ttbar_btag_truth_crosscheck/stats.json - no numbers are
retyped by hand.

Same "eligible region" as the earlier cross-check: jets with pT > 20 GeV and
|eta| < 2.4 (DeepJet's calibrated tracker-acceptance region). ALL numbers in
this script operate on that eligible-jet universe, not the full uncut jet
collection.

Needs XRootD -> run under the WSL venv (~/btag_work/venv):

    ~/btag_work/venv/bin/python -u scripts/ttbar_btag_event_multiplicity.py \
        --out-dir reports/ttbar_btag_truth_crosscheck
"""
from __future__ import annotations

import argparse
import json
import math
import os
import time
from pathlib import Path

os.environ.setdefault("XRD_REQUESTTIMEOUT", "180")
os.environ.setdefault("XRD_STREAMTIMEOUT", "120")
os.environ.setdefault("XRD_TIMEOUTRESOLUTION", "5")
os.environ.setdefault("XRD_CONNECTIONWINDOW", "30")

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

THRESHOLD = 0.25
ELIGIBLE_PT_MIN, ELIGIBLE_ABSETA_MAX = 20.0, 2.4
N_TRUE_B_QUARKS_PER_EVENT = 2  # semileptonic ttbar: t->Wb, tbar->Wbar bbar

_LOG_PATH = None


def log(*a):
    m = " ".join(str(x) for x in a)
    line = f"[{time.strftime('%H:%M:%S')}] {m}"
    print(line, flush=True)
    if _LOG_PATH:
        with open(_LOG_PATH, "a") as fh:
            fh.write(line + "\n")


def read_file_per_event(url: str, tries: int = 3):
    """
    Per event: (n_eligible, n_tagged_eligible, n_true_b_tagged_eligible) - three
    flat int arrays, one row per event. Computed chunk-by-chunk on the jagged
    (per-event) arrays so only small per-event scalars are kept in memory, not
    the full per-jet arrays.
    """
    import awkward as ak
    import uproot
    for k in range(1, tries + 1):
        t0 = time.time()
        try:
            n_elig_parts, n_tag_parts, n_trueb_parts = [], [], []
            with uproot.open(url, timeout=180) as f:
                tree = f["Events"]
                n_ev = tree.num_entries
                for chunk in tree.iterate(
                    ["Jet_btagDeepFlavB", "Jet_hadronFlavour", "Jet_pt", "Jet_eta"],
                    step_size=200_000, library="ak",
                ):
                    score = chunk["Jet_btagDeepFlavB"]
                    flav = chunk["Jet_hadronFlavour"]
                    pt = chunk["Jet_pt"]
                    abseta = abs(chunk["Jet_eta"])

                    eligible = (pt > ELIGIBLE_PT_MIN) & (abseta < ELIGIBLE_ABSETA_MAX)
                    tagged = score > THRESHOLD
                    true_b = flav == 5

                    n_elig_parts.append(ak.to_numpy(ak.sum(eligible, axis=1)))
                    n_tag_parts.append(ak.to_numpy(ak.sum(eligible & tagged, axis=1)))
                    n_trueb_parts.append(
                        ak.to_numpy(ak.sum(eligible & tagged & true_b, axis=1))
                    )
            n_elig = np.concatenate(n_elig_parts).astype(np.int64)
            n_tag = np.concatenate(n_tag_parts).astype(np.int64)
            n_trueb = np.concatenate(n_trueb_parts).astype(np.int64)
            log(f"   read ok in {time.time()-t0:.0f}s : {n_ev:,} events")
            return n_ev, n_elig, n_tag, n_trueb
        except Exception as e:  # noqa: BLE001 - retry any transient XRootD error
            log(f"   attempt {k}/{tries} failed after {time.time()-t0:.0f}s: "
                f"{type(e).__name__}: {str(e)[:160]}")
            time.sleep(10)
    raise RuntimeError(f"could not read {url} after {tries} attempts")


def multiplicity_dist(counts: np.ndarray, cap: int = 4) -> dict:
    """{'0': frac, '1': frac, ..., '>=cap': frac} of events, plus raw n's."""
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
    # binomial(2 trials) only defines P(0),P(1),P(2); 3 and >=4 are exactly 0%
    binom_pct = [binom[0] * 100, binom[1] * 100, binom[2] * 100, 0.0, 0.0]

    x = np.arange(len(cats))
    w = 0.38
    fig, ax = plt.subplots(figsize=(9, 5.6))
    b1 = ax.bar(x - w / 2, observed_pct, w, color="#3b6ea5",
                label=f"observed  ({n_events:,} events)")
    b2 = ax.bar(x + w / 2, binom_pct, w, color="#c1272d", alpha=0.85,
                label=f"binomial model  (2 trials, p={p:.4f} from this branch's "
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
        "Tagged-jet multiplicity per event (eligible jets, pT>20 GeV, |eta|<2.4)\n"
        "observed (any true flavour, as a real analysis would count it) vs a "
        "simple 2-b-quark binomial model",
        fontsize=9.3)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(out_png, dpi=130)
    plt.close(fig)
    log(f"wrote {out_png.name}")


def plot_tagged_vs_untagged(n_tagged_total: int, n_untagged_total: int,
                             out_png: Path) -> None:
    total = n_tagged_total + n_untagged_total
    frac = n_tagged_total / total if total else 0.0
    fig, ax = plt.subplots(figsize=(5.6, 5.6))
    bars = ax.bar(["tagged\n(score > 0.25)", "untagged\n(score <= 0.25)"],
                   [n_tagged_total, n_untagged_total],
                   color=["#c1272d", "#8c8c8c"])
    for rect in bars:
        h = rect.get_height()
        ax.text(rect.get_x() + rect.get_width() / 2, h, f"{h:,}",
                ha="center", va="bottom", fontsize=9)
    ax.set_ylabel("eligible jets (pT>20 GeV, |eta|<2.4)")
    ax.set_title(
        f"Tagged vs untagged eligible jets, all events\n"
        f"overall tagged fraction = {frac*100:.2f}%  ({n_tagged_total:,} / {total:,})",
        fontsize=10)
    fig.tight_layout()
    fig.savefig(out_png, dpi=130)
    plt.close(fig)
    log(f"wrote {out_png.name}")


def main() -> int:
    global _LOG_PATH
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--log", default=None)
    args = ap.parse_args()
    _LOG_PATH = args.log
    if _LOG_PATH:
        Path(_LOG_PATH).write_text("")

    out = Path(args.out_dir)
    (out / "plots").mkdir(parents=True, exist_ok=True)

    prior = json.loads((out / "stats.json").read_text())
    urls = [f["uri"] for f in prior["files"]]
    assert len(urls) == 3, f"expected the 3 files already used on this branch, got {len(urls)}"
    p_b_eff = prior["eligible_pt_gt_20_abseta_lt_2.4"]["b"]["rate"]
    log(f"reusing exact file list + measured b-efficiency from {out/'stats.json'}")
    log(f"p (b-tagging efficiency, eligible region) = {p_b_eff:.6f}")
    for u in urls:
        log(f"  will re-read: {u.split('/')[-1]}")

    n_elig_all, n_tag_all, n_trueb_all, n_events_total, file_rows = [], [], [], 0, []
    for i, u in enumerate(urls, 1):
        log(f"file {i}/{len(urls)}: {u.split('/')[-1]}")
        n_ev, n_elig, n_tag, n_trueb = read_file_per_event(u)
        n_events_total += n_ev
        n_elig_all.append(n_elig)
        n_tag_all.append(n_tag)
        n_trueb_all.append(n_trueb)
        file_rows.append({"file": u.split("/")[-1], "events": n_ev})

    n_elig = np.concatenate(n_elig_all)
    n_tag = np.concatenate(n_tag_all)
    n_trueb = np.concatenate(n_trueb_all)
    n_events = n_tag.size
    assert n_events == n_events_total

    tag_dist = multiplicity_dist(n_tag, cap=4)
    trueb_dist = multiplicity_dist(n_trueb, cap=3)

    binom = binomial_pmf(N_TRUE_B_QUARKS_PER_EVENT, p_b_eff)

    n_tagged_total = int(n_tag.sum())
    n_eligible_total = int(n_elig.sum())
    n_untagged_total = n_eligible_total - n_tagged_total

    mean_tagged = float(n_tag.mean())
    mean_trueb_tagged = float(n_trueb.mean())

    frac_0 = tag_dist["0"]["frac"]
    frac_1 = tag_dist["1"]["frac"]
    frac_ge2 = 1.0 - frac_0 - frac_1

    stats = {
        "record_id": prior["record_id"],
        "dataset": prior["dataset"],
        "threshold": THRESHOLD,
        "eligible_cut": {"pt_min_gev": ELIGIBLE_PT_MIN, "abseta_max": ELIGIBLE_ABSETA_MAX},
        "files": file_rows,
        "n_events": n_events,
        "n_eligible_jets_total": n_eligible_total,
        "n_tagged_jets_total": n_tagged_total,
        "n_untagged_jets_total": n_untagged_total,
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
            "p_source": "reports/ttbar_btag_truth_crosscheck/stats.json "
                        "-> eligible_pt_gt_20_abseta_lt_2.4.b.rate "
                        "(this branch's own measured b-tagging efficiency)",
            "P0": binom[0], "P1": binom[1], "P2": binom[2],
        },
        "true_b_jets_correctly_tagged_per_event": {
            "mean": mean_trueb_tagged,
            "distribution": trueb_dist,
        },
    }
    (out / "event_multiplicity_stats.json").write_text(json.dumps(stats, indent=2))
    log("event_multiplicity_stats.json written")
    log(json.dumps(stats, indent=2))

    plot_multiplicity_vs_binomial(
        tag_dist, binom, p_b_eff, n_events,
        out / "plots" / "btag_event_multiplicity_vs_binomial.png",
    )
    plot_tagged_vs_untagged(
        n_tagged_total, n_untagged_total,
        out / "plots" / "btag_tagged_vs_untagged_jets.png",
    )
    log("DONE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
