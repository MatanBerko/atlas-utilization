#!/usr/bin/env python3
"""
ttbar_btag_truth_crosscheck.py - REAL, truth-based DeepJet b-tagging
efficiency and mistag-rate measurement, using a simulated ttbar sample.

All prior b-tagging work in this project (config.cms_bjet_test.yaml, the raw
score-distribution work) used real CMS collision data, which carries no
generator-level truth: we could see the raw Jet_btagDeepFlavB score's shape and
count how many jets fall above a threshold, but never know what fraction of
*actual* b-jets that threshold correctly tags. Simulated samples carry
Jet_hadronFlavour, the generator-level truth label per jet (5 = true b-jet,
4 = true c-jet, 0 = true light/gluon jet), which real Open Data events do not
have. This script reads both Jet_btagDeepFlavB and Jet_hadronFlavour from a
simulated ttbar sample and computes the real efficiency/mistag numbers.

Dataset: CERN Open Data record 67993
  /TTToSemiLeptonic_TuneCP5_13TeV-powheg-pythia8/
    RunIISummer20UL16NanoAODv9-106X_mcRun2_asymptotic_v17-v1/NANOAODSIM
(simulated - NANOAODSIM, not NANOAOD)

Access pattern confirmed identical to the real-data work: same
opendata.cern.ch filepage JSON endpoint (plain HTTPS, normal certificate
verification), same root://eospublic.cern.ch XRootD host/protocol for the
files themselves. The only differences found: the MC file-index groups files
under 5 "index_files" groups instead of 1 (the fetch already handles multiple
groups generically) and the eos path includes an extra /mc/ segment
(.../eos/opendata/cms/mc/RunIISummer20UL16NanoAODv9/... vs the real-data
.../eos/opendata/cms/Run2016H/...). No workaround, no TLS changes, nothing
else needed.

Needs XRootD -> run under the WSL venv (~/btag_work/venv), not Docker/Windows:

    ~/btag_work/venv/bin/python -u scripts/ttbar_btag_truth_crosscheck.py \
        --out-dir reports/ttbar_btag_truth_crosscheck --files 3
"""
from __future__ import annotations

import argparse
import json
import os
import time
import urllib.request
from pathlib import Path

# XRootD read timeouts so a stalled transfer errors out (and is retried)
# instead of hanging forever. Set before uproot / XRootD import.
os.environ.setdefault("XRD_REQUESTTIMEOUT", "180")
os.environ.setdefault("XRD_STREAMTIMEOUT", "120")
os.environ.setdefault("XRD_TIMEOUTRESOLUTION", "5")
os.environ.setdefault("XRD_CONNECTIONWINDOW", "30")

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

RECORD_ID = 67993
DATASET = (
    "/TTToSemiLeptonic_TuneCP5_13TeV-powheg-pythia8/"
    "RunIISummer20UL16NanoAODv9-106X_mcRun2_asymptotic_v17-v1/NANOAODSIM"
)
# Project-wide standard threshold (config.cms_bjet_test.yaml, standardized
# 2026-09-07) - no discrepancy to flag here, this cross-check uses the same
# value.
THRESHOLD = 0.25

# Standard CMS b-tag POG eligibility region for a fair comparison to the
# officially quoted ~75-80% Medium-WP efficiency / ~1% light-mistag figures:
# DeepJet is only calibrated/recommended within the tracker acceptance and
# above a minimum jet pT. Used only for the cross-check numbers below; the
# headline numbers use every jet, no cut, exactly as asked.
ELIGIBLE_PT_MIN, ELIGIBLE_ABSETA_MAX = 20.0, 2.4

FLAVOUR_NAMES = {5: "b", 4: "c", 0: "light/gluon"}
FLAVOUR_COLORS = {5: "#c1272d", 4: "#2166ac", 0: "#1b7837"}
BINS = np.linspace(0.0, 1.0, 101)  # 100 bins of 0.01

_LOG_PATH = None


def log(*a):
    m = " ".join(str(x) for x in a)
    line = f"[{time.strftime('%H:%M:%S')}] {m}"
    print(line, flush=True)
    if _LOG_PATH:
        with open(_LOG_PATH, "a") as fh:
            fh.write(line + "\n")


def files_for_record(rid: int) -> list[str]:
    url = f"https://opendata.cern.ch/record/{rid}/filepage/1?group=1"
    with urllib.request.urlopen(url, timeout=90) as r:  # normal cert verification
        data = json.load(r)
    return [fe["uri"] for idx in data["index_files"]["files"] for fe in idx["files"]]


def read_file(url: str, tries: int = 3):
    """(n_events, score, hadron_flavour, pt, abseta) flat arrays, one row/jet."""
    import awkward as ak
    import uproot
    for k in range(1, tries + 1):
        t0 = time.time()
        try:
            s_parts, f_parts, pt_parts, eta_parts = [], [], [], []
            with uproot.open(url, timeout=180) as f:
                tree = f["Events"]
                n_ev = tree.num_entries
                for chunk in tree.iterate(
                    ["Jet_btagDeepFlavB", "Jet_hadronFlavour", "Jet_pt", "Jet_eta"],
                    step_size=200_000, library="ak",
                ):
                    s_parts.append(ak.to_numpy(ak.flatten(chunk["Jet_btagDeepFlavB"])))
                    f_parts.append(ak.to_numpy(ak.flatten(chunk["Jet_hadronFlavour"])))
                    pt_parts.append(ak.to_numpy(ak.flatten(chunk["Jet_pt"])))
                    eta_parts.append(ak.to_numpy(ak.flatten(chunk["Jet_eta"])))
            s = np.concatenate(s_parts).astype(np.float64)
            flav = np.concatenate(f_parts).astype(np.int64)
            pt = np.concatenate(pt_parts).astype(np.float64)
            eta = np.abs(np.concatenate(eta_parts).astype(np.float64))
            log(f"   read ok in {time.time()-t0:.0f}s : {n_ev:,} events, {s.size:,} jets")
            return n_ev, s, flav, pt, eta
        except Exception as e:  # noqa: BLE001 - retry any transient XRootD error
            log(f"   attempt {k}/{tries} failed after {time.time()-t0:.0f}s: "
                f"{type(e).__name__}: {str(e)[:160]}")
            time.sleep(10)
    raise RuntimeError(f"could not read {url} after {tries} attempts")


def flavour_stats(score: np.ndarray, flav: np.ndarray, mask: np.ndarray | None = None) -> dict:
    """Per true-flavour jet counts, tagged counts and efficiency/mistag rate."""
    if mask is not None:
        score, flav = score[mask], flav[mask]
    out = {}
    known = np.isin(flav, [0, 4, 5])
    n_unknown = int((~known).sum())
    if n_unknown:
        vals, counts = np.unique(flav[~known], return_counts=True)
        out["_unexpected_hadronFlavour_values"] = {
            int(v): int(c) for v, c in zip(vals, counts)
        }
    for fv, name in FLAVOUR_NAMES.items():
        sel = flav == fv
        n = int(sel.sum())
        tagged = int((score[sel] > THRESHOLD).sum()) if n else 0
        out[name] = {
            "hadronFlavour": fv,
            "n_jets": n,
            "n_tagged": tagged,
            "rate": (tagged / n) if n else None,
        }
    out["n_jets_total"] = int(score.size)
    out["n_unknown_hadronFlavour"] = n_unknown
    return out


def describe_score(score: np.ndarray) -> dict:
    n = score.size
    n_lt0 = int((score < 0).sum())
    n_gt1 = int((score > 1).sum())
    return {
        "n_jets": n, "min": float(score.min()) if n else None,
        "max": float(score.max()) if n else None,
        "n_negative_sentinel": n_lt0, "n_gt_1": n_gt1,
    }


def plot_by_flavour(counts_by_flav: dict, n_by_flav: dict, out_png: Path):
    fig, ax = plt.subplots(figsize=(9.5, 5.6))
    centers = 0.5 * (BINS[:-1] + BINS[1:])
    for fv in (5, 4, 0):  # draw b on top
        counts = counts_by_flav[fv]
        ax.stairs(counts, BINS, lw=1.8, color=FLAVOUR_COLORS[fv],
                  label=f"true {FLAVOUR_NAMES[fv]}-jet  ({n_by_flav[fv]:,} jets)")
    ax.axvline(THRESHOLD, color="#555555", ls="--", lw=1.2,
                label=f"DeepJet Medium WP = {THRESHOLD}")
    ax.set_yscale("log")
    ax.set_xlabel("Jet_btagDeepFlavB  (raw DeepJet b-vs-all discriminant)")
    ax.set_ylabel("jets / 0.01  (log scale)")
    ax.set_title(
        "Simulated ttbar (record 67993) - DeepJet score by TRUE generator-level "
        "flavour (Jet_hadronFlavour)\nno kinematic cuts; real MC truth, not "
        "fabricated",
        fontsize=9.5)
    ax.legend(fontsize=8.5)
    ax.set_xlim(0, 1)
    fig.tight_layout()
    fig.savefig(out_png, dpi=120)
    plt.close(fig)
    log(f"wrote {out_png.name}")


def main() -> int:
    global _LOG_PATH
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--files", type=int, default=3)
    ap.add_argument("--log", default=None)
    args = ap.parse_args()
    _LOG_PATH = args.log
    if _LOG_PATH:
        Path(_LOG_PATH).write_text("")

    out = Path(args.out_dir)
    (out / "plots").mkdir(parents=True, exist_ok=True)

    log("start")
    all_urls = files_for_record(RECORD_ID)
    urls = all_urls[: args.files]
    log(f"record {RECORD_ID} ({DATASET}): using {len(urls)} of {len(all_urls)} files")

    scores, flavs, pts, etas, n_events, file_rows = [], [], [], [], 0, []
    for i, u in enumerate(urls, 1):
        log(f"  file {i}/{len(urls)}: {u.split('/')[-1]}")
        ev, s, flav, pt, aeta = read_file(u)
        n_events += ev
        scores.append(s)
        flavs.append(flav)
        pts.append(pt)
        etas.append(aeta)
        file_rows.append({
            "file": u.split("/")[-1], "uri": u, "events": ev, "jets": int(s.size),
        })

    score = np.concatenate(scores)
    flav = np.concatenate(flavs)
    pt = np.concatenate(pts)
    abseta = np.concatenate(etas)

    score_desc = describe_score(score)
    log(f"score check: {score_desc}")

    all_stats = flavour_stats(score, flav)
    eligible_mask = (pt > ELIGIBLE_PT_MIN) & (abseta < ELIGIBLE_ABSETA_MAX)
    eligible_stats = flavour_stats(score, flav, mask=eligible_mask)

    stats = {
        "record_id": RECORD_ID,
        "dataset": DATASET,
        "threshold": THRESHOLD,
        "files_used": args.files,
        "files_total_in_record": len(all_urls),
        "n_events": n_events,
        "files": file_rows,
        "score_check": score_desc,
        "all_jets_no_cut": all_stats,
        f"eligible_pt_gt_{ELIGIBLE_PT_MIN:.0f}_abseta_lt_{ELIGIBLE_ABSETA_MAX}": eligible_stats,
        "eligible_cut_definition": {
            "pt_min_gev": ELIGIBLE_PT_MIN, "abseta_max": ELIGIBLE_ABSETA_MAX,
            "why": ("DeepJet is only calibrated/recommended inside the tracker "
                    "acceptance and above a minimum jet pT; this is the standard "
                    "region official b-tag POG efficiency numbers quote, used "
                    "here only as a cross-check against the no-cut headline "
                    "numbers above."),
        },
    }
    (out / "stats.json").write_text(json.dumps(stats, indent=2))
    log("stats.json written")
    log(json.dumps(stats, indent=2))

    # histogram cache, split by true flavour, for the plot
    counts_by_flav = {}
    n_by_flav = {}
    for fv in (0, 4, 5):
        sel = flav == fv
        counts_by_flav[fv] = np.histogram(np.clip(score[sel], 0, 1), bins=BINS)[0]
        n_by_flav[fv] = int(sel.sum())
    (out / "hist_cache_by_flavour.json").write_text(json.dumps({
        "bins": BINS.tolist(),
        "counts_by_flavour": {str(k): v.tolist() for k, v in counts_by_flav.items()},
        "n_by_flavour": n_by_flav,
    }, indent=2))
    log("hist_cache_by_flavour.json written")

    plot_by_flavour(counts_by_flav, n_by_flav, out / "plots" / "btag_score_by_true_flavour.png")
    log("DONE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
