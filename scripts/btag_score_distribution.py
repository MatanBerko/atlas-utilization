#!/usr/bin/env python3
"""
btag_score_distribution.py - distribution of the RAW per-jet DeepJet
b-tagging discriminant `Jet_btagDeepFlavB`, read straight from the CERN
NanoAOD source files.

The pipeline parser only ever stores the final tagged / untagged split, not the
score itself, so this re-reads the branch from the same small set of files the
existing CMS b-jet test used: records 30529 + 30562 (/SingleElectron/Run2016G,H),
first N files each - N matches config.cms_bjet_test.yaml's max_files_to_process
(2). No tagging cut applied, no expansion of scope.

Needs XRootD -> run under the WSL venv (~/btag_work/venv), not Docker/Windows:

    ~/btag_work/venv/bin/python -u scripts/btag_score_distribution.py \
        --out-dir reports/btag_score_distribution --files-per-record 2

Plain HTTPS with normal certificate verification is used for the file-list
lookup; TLS verification is never disabled anywhere.
"""
from __future__ import annotations

import argparse
import json
import os
import time
import urllib.request
from pathlib import Path

# XRootD read timeouts so a stalled transfer errors out (and is retried) instead
# of hanging forever. Set before uproot / XRootD import.
os.environ.setdefault("XRD_REQUESTTIMEOUT", "180")
os.environ.setdefault("XRD_STREAMTIMEOUT", "120")
os.environ.setdefault("XRD_TIMEOUTRESOLUTION", "5")
os.environ.setdefault("XRD_CONNECTIONWINDOW", "30")

import awkward as ak
import numpy as np
import uproot
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

MEDIUM_WP = 0.2598  # DeepJet Medium WP, UL2016 post-VFP - the b-jet test's cut
RECORDS = {
    30529: "SingleElectron Run2016G",
    30562: "SingleElectron Run2016H",
}
# b-jet test jet kinematic cuts (config.cms_bjet_test.yaml), used only for the
# reconcile-with-7.69% cross-check:
JET_PT_MIN, JET_ABSETA_MAX = 30.0, 4.5

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
    with urllib.request.urlopen(url, timeout=90) as r:   # normal cert verification
        data = json.load(r)
    return [fe["uri"] for idx in data["index_files"]["files"] for fe in idx["files"]]


def read_file(url: str, tries: int = 3):
    """(n_events, score, pt, abseta) flat float64 arrays for every jet, chunked."""
    for k in range(1, tries + 1):
        t0 = time.time()
        try:
            s_parts, pt_parts, eta_parts = [], [], []
            with uproot.open(url, timeout=180) as f:
                tree = f["Events"]
                n_ev = tree.num_entries
                for chunk in tree.iterate(
                    ["Jet_btagDeepFlavB", "Jet_pt", "Jet_eta"],
                    step_size=200_000, library="ak",
                ):
                    s_parts.append(ak.to_numpy(ak.flatten(chunk["Jet_btagDeepFlavB"])))
                    pt_parts.append(ak.to_numpy(ak.flatten(chunk["Jet_pt"])))
                    eta_parts.append(ak.to_numpy(ak.flatten(chunk["Jet_eta"])))
            s = np.concatenate(s_parts).astype(np.float64)
            pt = np.concatenate(pt_parts).astype(np.float64)
            eta = np.abs(np.concatenate(eta_parts).astype(np.float64))
            log(f"   read ok in {time.time()-t0:.0f}s : {n_ev:,} events, {s.size:,} jets")
            return n_ev, s, pt, eta
        except Exception as e:  # noqa: BLE001 - want to retry any transient XRootD error
            log(f"   attempt {k}/{tries} failed after {time.time()-t0:.0f}s: "
                f"{type(e).__name__}: {str(e)[:160]}")
            time.sleep(10)
    raise RuntimeError(f"could not read {url} after {tries} attempts")


def describe(name: str, s: np.ndarray) -> dict:
    n = s.size
    above = int((s > MEDIUM_WP).sum())
    qs = np.percentile(s, [50, 75, 90, 95, 99]) if n else [0] * 5
    edges = np.linspace(0.30, 0.90, 7)  # 0.30,0.40,...,0.90 - tagging-region shape
    hcounts, _ = np.histogram(s, bins=edges)
    return {
        "name": name, "n_jets": n,
        "above_wp": above, "below_wp": n - above,
        "frac_above_wp": above / n if n else 0.0,
        "outside_0_1": int(((s < 0) | (s > 1)).sum()),
        "min": float(s.min()) if n else None, "max": float(s.max()) if n else None,
        "median": float(qs[0]), "p75": float(qs[1]), "p90": float(qs[2]),
        "p95": float(qs[3]), "p99": float(qs[4]),
        "frac_below_0p05": float((s < 0.05).mean()) if n else 0.0,
        "frac_below_0p10": float((s < 0.10).mean()) if n else 0.0,
        "density_bins_0.30_0.90_step0.10": hcounts.tolist(),
    }


def main() -> int:
    global _LOG_PATH
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--files-per-record", type=int, default=2)
    ap.add_argument("--log", default=None, help="also append progress to this file")
    args = ap.parse_args()
    _LOG_PATH = args.log
    if _LOG_PATH:
        Path(_LOG_PATH).write_text("")

    out = Path(args.out_dir)
    (out / "plots").mkdir(parents=True, exist_ok=True)
    log("start")

    per_record, per_record_sel, n_events, file_rows = {}, {}, {}, []
    for rid, desc in RECORDS.items():
        all_urls = files_for_record(rid)
        urls = all_urls[: args.files_per_record]
        log(f"record {rid} ({desc}): using {len(urls)} of {len(all_urls)} files")
        scores, sel_scores, nev = [], [], 0
        for i, u in enumerate(urls, 1):
            log(f"  file {i}/{len(urls)}: {u.split('/')[-1]}")
            ev, s, pt, aeta = read_file(u)
            nev += ev
            scores.append(s)
            keep = (pt > JET_PT_MIN) & (aeta < JET_ABSETA_MAX)
            sel_scores.append(s[keep])
            file_rows.append({"record": rid, "file": u.split("/")[-1], "events": ev,
                              "jets": int(s.size), "jets_pt_eta": int(keep.sum())})
        per_record[rid] = np.concatenate(scores) if scores else np.array([])
        per_record_sel[rid] = np.concatenate(sel_scores) if sel_scores else np.array([])
        n_events[rid] = nev

    all_scores = np.concatenate(list(per_record.values()))
    all_sel = np.concatenate(list(per_record_sel.values()))

    stats = {
        "medium_wp": MEDIUM_WP,
        "files_per_record": args.files_per_record,
        "records": {str(k): v for k, v in RECORDS.items()},
        "n_events_per_record": {str(k): int(v) for k, v in n_events.items()},
        "files": file_rows,
        "all_jets": describe("all jets (no selection)", all_scores),
        "all_jets_pt_eta_cut": describe(
            f"jets with pt>{JET_PT_MIN:.0f} & |eta|<{JET_ABSETA_MAX:.1f}", all_sel),
        "per_record": {str(k): describe(RECORDS[k], v) for k, v in per_record.items()},
    }
    (out / "stats.json").write_text(json.dumps(stats, indent=2))
    log("stats.json written")
    log(json.dumps(stats, indent=2))

    bins = np.linspace(0.0, 1.0, 101)

    # plot 1: combined, full 0-1 range, log y
    fig, ax = plt.subplots(figsize=(9, 5.5))
    ax.hist(np.clip(all_scores, 0, 1), bins=bins, color="#3b7dd8",
            edgecolor="#1f3f6e", lw=0.3)
    ax.axvline(MEDIUM_WP, color="#c0392b", ls="--", lw=1.8,
               label=f"DeepJet Medium WP = {MEDIUM_WP}")
    ax.set_yscale("log")
    ax.set_xlabel("Jet_btagDeepFlavB  (raw DeepJet b-vs-all discriminant)")
    ax.set_ylabel("jets / 0.01  (log scale)")
    ax.set_title(
        f"CMS raw b-tag discriminant - {all_scores.size:,} jets, "
        f"{args.files_per_record} files x 2 SingleElectron records\n"
        f"{stats['all_jets']['frac_above_wp'] * 100:.2f}% of all jets sit above the Medium WP",
        fontsize=10)
    ax.legend()
    ax.set_xlim(0, 1)
    fig.tight_layout()
    fig.savefig(out / "plots" / "btag_score_all.png", dpi=120)
    plt.close(fig)
    log("wrote plots/btag_score_all.png")

    # plot 2: split by record, normalised
    fig, ax = plt.subplots(figsize=(9, 5.5))
    colors = {30529: "#2e7d32", 30562: "#6a1b9a"}
    for rid, s in per_record.items():
        ax.hist(np.clip(s, 0, 1), bins=bins, histtype="step", lw=1.7, density=True,
                color=colors[rid],
                label=f"{rid}  {RECORDS[rid]}  ({s.size:,} jets)")
    ax.axvline(MEDIUM_WP, color="#c0392b", ls="--", lw=1.8,
               label=f"Medium WP = {MEDIUM_WP}")
    ax.set_yscale("log")
    ax.set_xlabel("Jet_btagDeepFlavB  (raw DeepJet b-vs-all discriminant)")
    ax.set_ylabel("normalised density / 0.01  (log scale)")
    ax.set_title("CMS raw b-tag discriminant, split by SingleElectron record "
                 "(Run2016G vs Run2016H)", fontsize=10)
    ax.legend(fontsize=8)
    ax.set_xlim(0, 1)
    fig.tight_layout()
    fig.savefig(out / "plots" / "btag_score_by_record.png", dpi=120)
    plt.close(fig)
    log("wrote plots/btag_score_by_record.png")
    log("DONE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
