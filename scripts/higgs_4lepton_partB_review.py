#!/usr/bin/env python3
"""
H -> ZZ -> 4l Part B: follow-up checks from review (Maryna). NO new parsing --
reapplies the identical Part B selection to the same parsed ROOT chunks
already on Lustre, via higgs_4lepton_partB_report.py's load_events/
build_selected_leptons/run_selection (reused, not rewritten).

TASK 2: per-channel (4mu/2e2mu/4e) 70-180 GeV / 3 GeV mass spectra, reporting
per channel: candidates in 70-180, in 118-130, in 123.5-126.5 and its
neighbours, and whether the 91 GeV Z1 peak is present.

TASK 3: descriptive investigation of the "flat" part of the spectrum --
bin-by-bin contents 95-180 GeV, whether the highest bins rise approaching
the 2*m_Z ~ 182 GeV ZZ threshold, and the channel/record composition of the
off-peak (non-Z, non-Higgs-region) candidates. No fit, no background model,
no cause asserted.

NO significance/p-value/sigma computed or implied anywhere. No selection
tuning.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from higgs_4lepton_partB_report import load_events, build_selected_leptons, run_selection  # noqa: E402

BIN_LO, BIN_HI, N_BINS = 70.0, 180.0, 37
NEAR_91 = (85.0, 97.0)
NEAR_125 = (118.0, 130.0)

RECORD_NAMES = {
    30521: "DoubleEG G", 30554: "DoubleEG H", 30522: "DoubleMuon G",
    30555: "DoubleMuon H", 30528: "MuonEG G", 30561: "MuonEG H",
}
CHANNELS = ("4mu", "2e2mu", "4e")


def window_count(masses, lo, hi):
    m = np.asarray(masses)
    return int(((m >= lo) & (m < hi)).sum())


def summarize_channel(name, cands):
    m4l = np.array([c["m4l"] for c in cands]) if cands else np.array([])
    z1 = np.array([c["m_z1"] for c in cands]) if cands else np.array([])
    n_peak = int(((z1 >= 85) & (z1 <= 97)).sum()) if len(z1) else 0
    return {
        "label": name,
        "n_candidates_total": len(cands),
        "n_70_180": window_count(m4l, BIN_LO, BIN_HI),
        "n_118_130": window_count(m4l, 118.0, 130.0),
        "n_120_5_123_5_before": window_count(m4l, 120.5, 123.5),
        "n_123_5_126_5": window_count(m4l, 123.5, 126.5),
        "n_126_5_129_5_after": window_count(m4l, 126.5, 129.5),
        "n_zpeak_85_97": n_peak,
        "n_z1_total": len(z1),
        "zpeak_fraction": (n_peak / len(z1)) if len(z1) else None,
    }


def plot_channel_split(channel_cands, out_png):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    edges = np.linspace(BIN_LO, BIN_HI, N_BINS + 1)
    centers = 0.5 * (edges[:-1] + edges[1:])
    w = edges[1] - edges[0]
    colors = {"4mu": "#4477aa", "2e2mu": "#cc3311", "4e": "#228833"}

    fig, axes = plt.subplots(1, 3, figsize=(17, 5.5), sharey=True)
    for ax, ch in zip(axes, CHANNELS):
        cands = channel_cands[ch]
        m = np.array([c["m4l"] for c in cands]) if cands else np.array([])
        counts, _ = np.histogram(m, bins=edges)
        ax.bar(centers, counts, width=w * 0.92, color=colors[ch])
        ax.axvline(91.1876, color="#888888", ls="--", lw=1)
        ax.axvline(125.0, color="#333333", ls="--", lw=1)
        ax.set_xlabel("4-lepton invariant mass [GeV]")
        ax.set_title(f"{ch}: {int(counts.sum())} in 70-180 GeV, {len(cands)} total")
    axes[0].set_ylabel(f"candidates / {w:.2f} GeV")
    fig.suptitle(
        "H->ZZ->4l Part B mass spectrum by channel\n"
        "Descriptive only -- no significance, p-value, or sigma computed or implied"
    )
    fig.tight_layout()
    fig.savefig(out_png, dpi=130)
    print(f"wrote {out_png}")


def bin_table_95_180(candidates):
    m4l = np.array([c["m4l"] for c in candidates])
    edges = np.linspace(BIN_LO, BIN_HI, N_BINS + 1)
    counts, _ = np.histogram(m4l, bins=edges)
    rows = []
    for i in range(N_BINS):
        lo, hi = edges[i], edges[i + 1]
        if hi <= 95.0:
            continue
        rows.append({"bin_lo_gev": round(float(lo), 2), "bin_hi_gev": round(float(hi), 2),
                     "count": int(counts[i])})
    return rows


def off_peak_composition(candidates):
    off = [c for c in candidates
           if BIN_LO <= c["m4l"] < BIN_HI
           and not (NEAR_91[0] <= c["m4l"] < NEAR_91[1])
           and not (NEAR_125[0] <= c["m4l"] < NEAR_125[1])]
    by_channel = {ch: sum(1 for c in off if c["channel"] == ch) for ch in CHANNELS}
    by_record = {RECORD_NAMES.get(r, str(r)): sum(1 for c in off if c["source_record"] == r)
                 for r in sorted(set(c["source_record"] for c in candidates))}
    return {
        "definition": f"m4l in [{BIN_LO},{BIN_HI}) GeV, excluding [{NEAR_91[0]},{NEAR_91[1]}) "
                       f"(near-91) and [{NEAR_125[0]},{NEAR_125[1]}) (near-125)",
        "n_off_peak": len(off),
        "n_total_70_180": window_count([c["m4l"] for c in candidates], BIN_LO, BIN_HI),
        "by_channel": by_channel,
        "by_record": by_record,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True, type=Path)
    ap.add_argument("--out-dir", required=True, type=Path)
    args = ap.parse_args()

    out = args.out_dir
    (out / "plots").mkdir(parents=True, exist_ok=True)

    events, n_events, file_rows = load_events(args.run_dir)
    print(f"loaded {n_events:,} events from {len(file_rows)} chunk file(s)")

    leptons = build_selected_leptons(events, use_sip3d=True, use_dxy=True, use_dz=True)
    cutflow, candidates = run_selection(events, leptons)
    print(f"primary candidates: {len(candidates)} (cross-check vs. the earlier full-scale run's 535)")

    # ---- TASK 2: per-channel split ----
    channel_cands = {ch: [c for c in candidates if c["channel"] == ch] for ch in CHANNELS}
    channel_summary = {ch: summarize_channel(ch, cands) for ch, cands in channel_cands.items()}
    for ch, s in channel_summary.items():
        print(f"\n=== channel {ch} ===")
        print(json.dumps(s, indent=2))
    plot_channel_split(channel_cands, out / "plots" / "partB_split_channel.png")

    # ---- TASK 3: flat-spectrum investigation ----
    bin_table = bin_table_95_180(candidates)
    print("\n=== bin-by-bin, 95-180 GeV ===")
    for row in bin_table:
        print(f"  [{row['bin_lo_gev']:.2f}, {row['bin_hi_gev']:.2f}): {row['count']}")

    off_peak = off_peak_composition(candidates)
    print("\n=== off-peak (non-91, non-125) composition ===")
    print(json.dumps(off_peak, indent=2))

    stats = {
        "n_primary_candidates": len(candidates),
        "channel_summary": channel_summary,
        "bin_table_95_180": bin_table,
        "off_peak_composition": off_peak,
    }
    (out / "partB_review_stats.json").write_text(json.dumps(stats, indent=2))
    print(f"\nwrote {out / 'partB_review_stats.json'}")


if __name__ == "__main__":
    main()
