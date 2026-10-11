#!/usr/bin/env python
"""
Parts A3 and A4: the pileup weight, and the pilot plots with and without it.

A3 -- build w_PU(nTrueInt) from the official file, report its mean over ALL
      generated events of each sample (which must come out near 1 if the
      sample really follows the standard UL16 MC pileup profile the official
      weights assume) and its range. Bins where the MC profile is empty but
      the weight is non-trivial are reported rather than silently capped.

A4 -- redraw the pilot's P1 (Z peak mumu), P2 (Z peak ee) and P3 (light-jet
      and b-jet multiplicity, both channels) WITH and WITHOUT w_PU, side by
      side, using the stored `_mcraw_puntrue` sibling in the pilot shards.
      The pilot shards are read ONLY; nothing is written back to them.

Everything about the data side, the event union, the Z definition and the
binning is taken from `compare_data_mc.py` unchanged, so the "without"
column reproduces the pilot numbers exactly.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
from collections import defaultdict
from datetime import datetime, timezone

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

from studies.cms_datasets.cluster.run_dataset_on_file import (  # noqa: E402
    MC_SIBLING_ACCEPTANCE, MC_SIBLING_PILEUP, MC_WEIGHT_SUFFIX,
)
from studies.cms_mc_weights_v3.deliver.build_mc_delivery import (  # noqa: E402
    SIG_PATTERN, event_union_mask, read_shard_arrays,
)
from studies.cms_mc_weights_v3.deliver.compare_data_mc import (  # noqa: E402
    LUMI_FB, SAMPLE_STYLE, fs_counts, gaussian_core_fit, read_data,
)
from studies.cms_mc_weights_v3.pileup.pu_weights import load as load_pu  # noqa: E402

Z_EDGES = np.arange(60.0, 120.0 + 1e-9, 2.0)
Z_WINDOW = (76.0, 106.0)
NJET_BINS = 6
NBJET_BINS = 3
WANT_IM = {"m0m1", "e0e1"}


def keep_fs(im, c):
    if im == "m0m1":
        return c["e"] == 0 and c["m"] == 2
    if im == "e0e1":
        return c["e"] == 2 and c["m"] == 0
    return False


def read_mc_with_pileup(scratch_dir: pathlib.Path, pu) -> dict:
    """{record: {im: (masses, w_nominal, w_pileup, jb_counts)}} from the
    pilot's `_mcw` weights and its stored `_mcraw_puntrue` sibling."""
    per = defaultdict(lambda: defaultdict(lambda: ([], [], [], [])))
    n_dropped = 0
    for shard in sorted(scratch_dir.rglob("*.sqlite")):
        rid = shard.parent.name.replace("record_", "")
        chunks = read_shard_arrays(str(shard))
        for sig in sorted(chunks):
            m = SIG_PATTERN.search(sig)
            if not m:
                continue
            fs_str, im_str = m.groups()
            if im_str not in WANT_IM:
                continue
            counts = fs_counts(fs_str)
            if not keep_fs(im_str, counts):
                continue
            masses = chunks.get(sig, [])
            weights = chunks.get(sig + MC_WEIGHT_SUFFIX, [])
            accs = chunks.get(sig + MC_SIBLING_ACCEPTANCE, [])
            pus = chunks.get(sig + MC_SIBLING_PILEUP, [])
            if not masses:
                continue
            if not weights or not pus:
                raise SystemExit(
                    f"{shard}: {sig} lacks {MC_WEIGHT_SUFFIX} or "
                    f"{MC_SIBLING_PILEUP}; this needs the pilot's --keep-scratch build")
            mm = np.concatenate([np.asarray(c, dtype=np.float64) for c in masses])
            ww = np.concatenate([np.asarray(c, dtype=np.float64) for c in weights])
            nt = np.concatenate([np.asarray(c, dtype=np.float64) for c in pus])
            if not (len(mm) == len(ww) == len(nt)):
                raise SystemExit(
                    f"{shard}: {sig} alignment lost ({len(mm)}/{len(ww)}/{len(nt)})")
            if accs:
                aa = np.concatenate([np.asarray(c) for c in accs])
                union = event_union_mask(aa)
                n_dropped += int((~union).sum())
                mm, ww, nt = mm[union], ww[union], nt[union]
            if mm.size == 0:
                continue
            wpu = ww * pu(nt, "nominal")
            per[rid][im_str][0].append(mm)
            per[rid][im_str][1].append(ww)
            per[rid][im_str][2].append(wpu)
            per[rid][im_str][3].append(
                np.repeat(np.array([[counts["j"], counts["b"]]]), len(mm), axis=0))
    out = {rid: {im: tuple(np.concatenate(x) for x in cols)
                 for im, cols in by_im.items() if cols[0]}
           for rid, by_im in per.items()}
    out["_dropped_by_union"] = n_dropped
    return out


def _panel(ax_main, ax_ratio, edges, data_counts, mc_by, xlabel, title,
           logy=False, xticklabels=None):
    centres = 0.5 * (edges[:-1] + edges[1:])
    widths = np.diff(edges)
    bottom = np.zeros(len(centres))
    tot = np.zeros(len(centres))
    var = np.zeros(len(centres))
    for rid in sorted(mc_by, key=lambda r: -mc_by[r][0].sum()):
        v, w2 = mc_by[rid]
        label, colour = SAMPLE_STYLE.get(rid, (rid, "#a0aec0"))
        ax_main.bar(centres, v, width=widths, bottom=bottom, label=label,
                    color=colour, edgecolor="none", alpha=0.85)
        bottom = bottom + v
        tot = tot + v
        var = var + w2
    ax_main.errorbar(centres, tot, yerr=np.sqrt(var), fmt="none",
                     ecolor="#2d3748", elinewidth=1, alpha=0.6)
    ax_main.errorbar(centres, data_counts, yerr=np.sqrt(data_counts), fmt="o",
                     ms=3.2, color="black", lw=1, capsize=1.5, label="data")
    ax_main.set_title(title, fontsize=9)
    ax_main.legend(fontsize=7)
    ax_main.grid(alpha=0.2, lw=0.5)
    if logy:
        ax_main.set_yscale("log")
    with np.errstate(divide="ignore", invalid="ignore"):
        ratio = np.where(tot > 0, data_counts / tot, np.nan)
        rerr = np.where(tot > 0, np.sqrt(np.maximum(data_counts, 0)) / tot, np.nan)
    ax_ratio.errorbar(centres, ratio, yerr=rerr, fmt="o", ms=3.2, color="black",
                      lw=1, capsize=1.5)
    ax_ratio.axhline(1.0, color="#718096", ls="--", lw=1)
    ax_ratio.set_ylabel("data / MC", fontsize=8)
    ax_ratio.set_xlabel(xlabel)
    ax_ratio.set_ylim(0, 2.4)
    ax_ratio.grid(alpha=0.2, lw=0.5)
    if xticklabels is not None:
        ax_ratio.set_xticks(range(len(xticklabels)))
        ax_ratio.set_xticklabels(xticklabels)
    d, m = float(data_counts.sum()), float(tot.sum())
    return {"data": d, "mc": m, "ratio": (d / m) if m else None,
            "ratio_err": (np.sqrt(d) / m) if m else None,
            "per_bin_ratio": [None if not np.isfinite(r) else float(r) for r in ratio],
            "per_bin_ratio_err": [None if not np.isfinite(e) else float(e) for e in rerr],
            "per_bin_data": data_counts.tolist(), "per_bin_mc": tot.tolist()}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-runs-dir", required=True)
    ap.add_argument("--mc-scratch-dir", required=True)
    ap.add_argument("--pu-json", required=True)
    ap.add_argument("--mc-profiles", required=True,
                    help="directory holding mc_pu_profile_<record>.json")
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args()

    out_dir = pathlib.Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    pu = load_pu(args.pu_json)

    # ---- A3: the weight, checked against the measured MC profile -------
    a3 = {"provenance": pu.provenance(), "per_sample": {}}
    edges = pu.edges("nominal")
    centres = 0.5 * (edges[:-1] + edges[1:])
    w_nom = pu.content("nominal")
    for prof_path in sorted(pathlib.Path(args.mc_profiles).glob("mc_pu_profile_*.json")):
        prof = json.loads(prof_path.read_text(encoding="utf-8"))
        rid = prof["record_id"]
        sumw = np.asarray(prof["sumw_genweight"], dtype=np.float64)
        cnt = np.asarray(prof["counts_unweighted"], dtype=np.float64)
        p_mc = sumw / sumw.sum() if sumw.sum() else sumw
        # mean of w_PU over ALL generated events, genWeight-weighted
        mean_w = float((p_mc * w_nom).sum())
        implied_data = p_mc * w_nom
        empty_mc_but_weighted = [
            {"bin": int(i), "nTrueInt": float(centres[i]), "weight": float(w_nom[i])}
            for i in range(len(w_nom))
            if cnt[i] == 0 and w_nom[i] > 0.01
        ]
        a3["per_sample"][rid] = {
            "physics_short": prof["physics_short"],
            "n_files": prof["n_files"],
            "n_events_total": prof["n_events_total"],
            "mean_nTrueInt_genweighted": prof["mean_nTrueInt_genweighted"],
            "mean_w_PU_over_all_generated_events": mean_w,
            "w_PU_min": float(w_nom.min()), "w_PU_max": float(w_nom.max()),
            "mean_nTrueInt_after_weighting": float(
                (implied_data * centres).sum() / implied_data.sum()),
            "n_events_at_or_above_nTrueInt_99": prof[
                "n_events_with_nTrueInt_at_or_above_99"],
            "bins_with_empty_MC_but_nonzero_weight": empty_mc_but_weighted,
            "n_such_bins": len(empty_mc_but_weighted),
        }
        print(f"[{rid}] {prof['physics_short']}: mean w_PU over all generated "
              f"events = {mean_w:.4f}; mean nTrueInt {prof['mean_nTrueInt_genweighted']:.2f} "
              f"-> {a3['per_sample'][rid]['mean_nTrueInt_after_weighting']:.2f}",
              flush=True)

    # the MC profile vs the implied data profile, one plot
    fig, ax = plt.subplots(1, 2, figsize=(12.5, 4.4))
    for prof_path in sorted(pathlib.Path(args.mc_profiles).glob("mc_pu_profile_*.json")):
        prof = json.loads(prof_path.read_text(encoding="utf-8"))
        sumw = np.asarray(prof["sumw_genweight"], dtype=np.float64)
        p_mc = sumw / sumw.sum()
        label, colour = SAMPLE_STYLE.get(prof["record_id"],
                                         (prof["record_id"], "#a0aec0"))
        ax[0].step(centres, p_mc, where="mid", color=colour, lw=1.3, label=label)
        ax[0].step(centres, p_mc * w_nom, where="mid", color=colour, lw=1.3,
                   ls="--", alpha=0.8)
    ax[0].set_xlabel("Pileup_nTrueInt")
    ax[0].set_ylabel("normalised fraction of generated events")
    ax[0].set_title("MC pileup profile (solid) and after the official weight "
                    "(dashed)\n= the implied data profile", fontsize=9)
    ax[0].set_xlim(0, 70)
    ax[0].legend(fontsize=7.5)
    ax[0].grid(alpha=0.2, lw=0.5)
    ax[1].step(centres, w_nom, where="mid", color="#c05621", lw=1.4)
    ax[1].axhline(1.0, color="#718096", ls="--", lw=1)
    ax[1].set_xlabel("Pileup_nTrueInt")
    ax[1].set_ylabel("official pileup weight")
    ax[1].set_title("Collisions16_UltraLegacy_goldenJSON (2016postVFP UL)\n"
                    "weights > 1 near 30-55: MC has too few high-pileup events",
                    fontsize=9)
    ax[1].set_xlim(0, 70)
    ax[1].grid(alpha=0.2, lw=0.5)
    fig.suptitle("Part A3 — the official pileup weight and the measured MC profile",
                 fontsize=10)
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    p = out_dir / "A3_pu_weight_and_profile.png"
    fig.savefig(p, dpi=140)
    plt.close(fig)
    print(f"wrote {p}", flush=True)

    # ---- A4: redraw P1/P2/P3 with and without the weight ---------------
    data = read_data(pathlib.Path(args.data_runs_dir), WANT_IM, keep_fs)
    data.pop("_n_shards", None)
    mc = read_mc_with_pileup(pathlib.Path(args.mc_scratch_dir), pu)
    n_dropped = mc.pop("_dropped_by_union")
    print(f"MC entries dropped by the four-flag union: {n_dropped:,}", flush=True)

    results = {"A3": a3, "A4": {}}

    # P1 / P2
    for tag, im, name in (("P1", "m0m1", "Z peak, dimuon"),
                          ("P2", "e0e1", "Z peak, dielectron")):
        fig, axes = plt.subplots(2, 2, figsize=(13.0, 6.0), sharex="col",
                                 gridspec_kw={"height_ratios": [3, 1], "hspace": 0.06})
        d_counts, _ = np.histogram(data[im][0], bins=Z_EDGES)
        summ = {}
        for col, (which, wname) in enumerate(((1, "without w_PU"), (2, "with w_PU"))):
            mc_by = {}
            for rid in sorted(mc):
                if im not in mc[rid]:
                    continue
                mm, ww, wpu, _jb = mc[rid][im]
                w = ww if which == 1 else wpu
                v, _ = np.histogram(mm, bins=Z_EDGES, weights=w)
                w2, _ = np.histogram(mm, bins=Z_EDGES, weights=w ** 2)
                mc_by[rid] = (v, w2)
            s = _panel(axes[0][col], axes[1][col], Z_EDGES, d_counts, mc_by,
                       f"{'dimuon' if im == 'm0m1' else 'dielectron'} mass [GeV]",
                       f"{name} — {wname}")
            tot = sum(v for v, _ in mc_by.values())
            s["mc_gaussian_core_fit"] = gaussian_core_fit(
                0.5 * (Z_EDGES[:-1] + Z_EDGES[1:]), tot)
            summ[wname] = s
        summ["data_gaussian_core_fit"] = gaussian_core_fit(
            0.5 * (Z_EDGES[:-1] + Z_EDGES[1:]), d_counts)
        fig.suptitle(f"Part A4 — {name}, pilot plot redrawn with and without the "
                     "official pileup weight. Absolute normalisation.", fontsize=10)
        fig.tight_layout(rect=(0, 0, 1, 0.93))
        p = out_dir / f"A4_{tag}_zpeak_{'mumu' if im == 'm0m1' else 'ee'}.png"
        fig.savefig(p, dpi=140)
        plt.close(fig)
        summ["png"] = str(p)
        results["A4"][tag] = summ
        print(f"wrote {p}", flush=True)

    # P3: jet and b-jet multiplicity in the Z window
    fig, axes = plt.subplots(2, 4, figsize=(18.0, 6.4),
                             gridspec_kw={"height_ratios": [3, 1], "hspace": 0.08})
    p3 = {}
    panel = 0
    for im, flavour in (("m0m1", "mumu"), ("e0e1", "ee")):
        for which, wname in ((1, "without w_PU"), (2, "with w_PU")):
            axm, axr = axes[0][panel], axes[1][panel]
            edges = np.arange(-0.5, NJET_BINS, 1.0)
            m, jb = data[im]
            sel = (m >= Z_WINDOW[0]) & (m <= Z_WINDOW[1])
            k = np.clip(jb[sel][:, 0], 0, NJET_BINS - 1)
            d_counts, _ = np.histogram(k, bins=edges)
            mc_by = {}
            for rid in sorted(mc):
                if im not in mc[rid]:
                    continue
                mm, ww, wpu, jbm = mc[rid][im]
                w = ww if which == 1 else wpu
                s2 = (mm >= Z_WINDOW[0]) & (mm <= Z_WINDOW[1])
                kk = np.clip(jbm[s2][:, 0], 0, NJET_BINS - 1)
                v, _ = np.histogram(kk, bins=edges, weights=w[s2])
                w2, _ = np.histogram(kk, bins=edges, weights=w[s2] ** 2)
                mc_by[rid] = (v, w2)
            s = _panel(axm, axr, edges, d_counts, mc_by, "light jets",
                       f"{flavour}, 76-106 GeV — {wname}", logy=True,
                       xticklabels=["0", "1", "2", "3", "4", "5+"])
            p3[f"{flavour}_jets_{wname.replace(' ', '_')}"] = s
            panel += 1
    fig.suptitle("Part A4 — light-jet multiplicity for Z-window events, with and "
                 "without the official pileup weight. Absolute normalisation.",
                 fontsize=10)
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    p = out_dir / "A4_P3_jet_multiplicity.png"
    fig.savefig(p, dpi=140)
    plt.close(fig)
    p3["png"] = str(p)

    # b-jets, same layout
    fig, axes = plt.subplots(2, 4, figsize=(18.0, 6.4),
                             gridspec_kw={"height_ratios": [3, 1], "hspace": 0.08})
    panel = 0
    for im, flavour in (("m0m1", "mumu"), ("e0e1", "ee")):
        for which, wname in ((1, "without w_PU"), (2, "with w_PU")):
            axm, axr = axes[0][panel], axes[1][panel]
            edges = np.arange(-0.5, NBJET_BINS, 1.0)
            m, jb = data[im]
            sel = (m >= Z_WINDOW[0]) & (m <= Z_WINDOW[1])
            k = np.clip(jb[sel][:, 1], 0, NBJET_BINS - 1)
            d_counts, _ = np.histogram(k, bins=edges)
            mc_by = {}
            for rid in sorted(mc):
                if im not in mc[rid]:
                    continue
                mm, ww, wpu, jbm = mc[rid][im]
                w = ww if which == 1 else wpu
                s2 = (mm >= Z_WINDOW[0]) & (mm <= Z_WINDOW[1])
                kk = np.clip(jbm[s2][:, 1], 0, NBJET_BINS - 1)
                v, _ = np.histogram(kk, bins=edges, weights=w[s2])
                w2, _ = np.histogram(kk, bins=edges, weights=w[s2] ** 2)
                mc_by[rid] = (v, w2)
            s = _panel(axm, axr, edges, d_counts, mc_by, "b-jets",
                       f"{flavour}, 76-106 GeV — {wname}", logy=True,
                       xticklabels=["0", "1", "2+"])
            p3[f"{flavour}_bjets_{wname.replace(' ', '_')}"] = s
            panel += 1
    fig.suptitle("Part A4 — b-jet multiplicity for Z-window events, with and "
                 "without the official pileup weight.", fontsize=10)
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    p2p = out_dir / "A4_P3_bjet_multiplicity.png"
    fig.savefig(p2p, dpi=140)
    plt.close(fig)
    p3["png_bjets"] = str(p2p)
    results["A4"]["P3"] = p3
    print(f"wrote {p}\nwrote {p2p}", flush=True)

    results["generated_utc"] = datetime.now(timezone.utc).isoformat()
    results["n_mc_entries_dropped_by_event_union"] = n_dropped
    results["luminosity_fb"] = LUMI_FB
    out = out_dir / "partA_pileup_results.json"
    out.write_text(json.dumps(results, indent=2, default=str), encoding="utf-8")
    print(f"\nwrote {out}")

    print("\n=== A4: light-jet data/MC per bin, before -> after w_PU ===")
    for flavour in ("mumu", "ee"):
        b = p3[f"{flavour}_jets_without_w_PU"]["per_bin_ratio"]
        a = p3[f"{flavour}_jets_with_w_PU"]["per_bin_ratio"]
        print(f"  {flavour}:")
        for i, name in enumerate(["0", "1", "2", "3", "4", "5+"]):
            if b[i] is not None and a[i] is not None:
                print(f"    {name:>2} jets : {b[i]:.3f} -> {a[i]:.3f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
