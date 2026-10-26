#!/usr/bin/env python
"""
Full run 25 Oct 2026, verification and plots (Prompt B, 26 Oct). READ-ONLY on
every input; writes only into --out-dir. Run as a PBS job (reads ROOT files and
SQLite shards).

Inputs (the outputs of the full run, see HANDOFF.md):
  --data-build   the default (#40) data build:  fullrun_bumpnet.root, manifest_fullrun.json,
                 multiplicity_rule_fullrun.json
  --data-runs    the data per-file outputs (<Dataset>_index.json, <Dataset>/job_<n>/)
  --mc-build     the MC build: fullrun_record<R>_mc.root, fullrun_summedSM_mc.root
  --mc-scratch   the MC build's kept scratch (weighted shards, `_mcw`)

What it does:
  1. histogram checks of every delivered file: count, NaN/inf, negative variances,
     negative bins, first filled bin per name;
  2. data vs MC names: in both, MC-only (by final state), data-only, first-filled-bin
     agreement, MC names whose first filled bin is above 2,000 GeV;
  3. the 500,000-entry cap: capped signatures per data file (job_metadata) ;
  4. the Z-peak data/MC ratios, the method of the 18 Oct peak-fix study
     (studies/cms_mc_weights_v3/peakfix/z_peak_ratio.py on
     feature/cms-mc-multiplicity40-20261023): stored events before any
     post-processing, absolute normalisation. Data: DoubleMuon inclusive + the
     other FOUR datasets exclusive (the delivery's pooling; 18 Oct had four
     datasets); MC: the builder's union of the five delivered acceptances
     (build_mc_delivery.event_union_mask, unchanged);
  5. per-dataset share of every delivered (#40) final state, from job_metadata;
  6. PNGs: data/MC stacks, Z peaks, histograms per final state, examples per dataset.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
import tempfile
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import uproot  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

from studies.cms_datasets.cluster.run_dataset_on_file import (  # noqa: E402
    DELIVERY_VETO_ORDER_5, MC_SIBLING_ACCEPTANCE, MC_WEIGHT_SUFFIX)
from studies.cms_mc_weights_v3.deliver import build_mc_delivery as BMC  # noqa: E402
from studies.cms_mc_weights_v3.fullrun.sanity_and_plots import (  # noqa: E402
    GROUPS, GRID, INK, INK2, SURF, parse, read_all, style)

LUMI = BMC.TARGET_LUMINOSITY_FB
SIG_PATTERN = BMC.SIG_PATTERN
DATA_SHARD_INCL = "dataset_shard_rare4_inclusive.sqlite"
DATA_SHARD_EXCL = "dataset_shard_rare4_exclusive.sqlite"
FS_TOKEN = re.compile(r"(\d+)([emjgtb])")
MISSING_MC = ("Not in the MC: W+jets, QCD multijet, single top t- and s-channel, "
              "fully hadronic tt̄ (and smaller processes)")
DATA_COLOR = INK
REF_18OCT = {"mumu": 1.0340, "ee": 0.9534}


# ---------------------------------------------------------------------------
# shard reading (the 18 Oct method: a private copy of each shard, so the
# read-only inputs are never opened in place)
# ---------------------------------------------------------------------------

def read_copy(shard_path: str) -> dict:
    tmp = Path(tempfile.mkdtemp(dir=os.environ.get("TMPDIR")))
    try:
        dst = tmp / Path(shard_path).name
        for suffix in ("", "-wal", "-shm"):
            src = Path(shard_path + suffix)
            if src.exists():
                shutil.copyfile(src, Path(str(dst) + suffix))
        return BMC.read_shard_arrays(str(dst))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def fs_counts(fs_str: str) -> dict:
    c = {"e": 0, "m": 0, "j": 0, "g": 0, "t": 0, "b": 0}
    for n, t in FS_TOKEN.findall(fs_str):
        c[t] = int(n)
    return c


def zpeak_keep(im, c):
    return (im == "m0m1" and c["e"] == 0 and c["m"] == 2) or (im == "e0e1" and c["e"] == 2 and c["m"] == 0)


def read_data_z(runs_dir: Path) -> dict:
    """compare_data_mc.read_data with the five delivered datasets."""
    out = defaultdict(lambda: ([], []))
    n = 0
    for i, label in enumerate(DELIVERY_VETO_ORDER_5):
        shard_name = DATA_SHARD_INCL if i == 0 else DATA_SHARD_EXCL
        index = json.loads((runs_dir / f"{label}_index.json").read_text())
        for job_key in sorted(index, key=int):
            shard = runs_dir / label / f"job_{job_key}" / shard_name
            if not shard.exists():
                raise SystemExit(f"missing delivered shard: {shard}")
            n += 1
            for sig, chunks in read_copy(str(shard)).items():
                m = SIG_PATTERN.search(sig)
                if not m:
                    continue
                fs_str, im = m.groups()
                c = fs_counts(fs_str)
                if not zpeak_keep(im, c):
                    continue
                for ch in chunks:
                    out[im][0].append(np.asarray(ch, dtype=np.float64))
                    out[im][1].append(np.full(len(ch), c["j"]))
    res = {im: (np.concatenate(a), np.concatenate(b)) for im, (a, b) in out.items() if a}
    return res, n


def read_mc_z(scratch_dir: Path) -> tuple:
    """compare_data_mc.read_mc, unchanged in substance."""
    per = defaultdict(lambda: defaultdict(lambda: ([], [], [])))
    n, dropped = 0, 0
    for shard in sorted(scratch_dir.rglob("*.sqlite")):
        rid = shard.parent.name.replace("record_", "")
        n += 1
        chunks = read_copy(str(shard))
        for sig in sorted(chunks):
            m = SIG_PATTERN.search(sig)
            if not m:
                continue
            fs_str, im = m.groups()
            c = fs_counts(fs_str)
            if not zpeak_keep(im, c):
                continue
            masses = chunks.get(sig, [])
            weights = chunks.get(sig + MC_WEIGHT_SUFFIX, [])
            accs = chunks.get(sig + MC_SIBLING_ACCEPTANCE, [])
            if not masses:
                continue
            if not weights:
                raise SystemExit(f"{shard}: {sig} has masses but no weights")
            mm = np.concatenate([np.asarray(x, dtype=np.float64) for x in masses])
            ww = np.concatenate([np.asarray(x, dtype=np.float64) for x in weights])
            if accs:
                aa = np.concatenate([np.asarray(x) for x in accs])
                keep = BMC.event_union_mask(aa)
                dropped += int((~keep).sum())
                mm, ww = mm[keep], ww[keep]
            if mm.size == 0:
                continue
            per[rid][im][0].append(mm)
            per[rid][im][1].append(ww)
            per[rid][im][2].append(np.full(len(mm), c["j"]))
    out = {rid: {im: tuple(np.concatenate(x) for x in v) for im, v in by.items() if v[0]}
           for rid, by in per.items()}
    return out, n, dropped


def zpeak(data_runs: Path, mc_scratch: Path, out: Path) -> dict:
    data, n_d = read_data_z(data_runs)
    mc, n_m, dropped = read_mc_z(mc_scratch)
    res = {"n_data_shards": n_d, "n_mc_shards": n_m, "n_mc_entries_dropped_by_event_union": dropped,
           "reference_18oct_76_106_0j": REF_18OCT, "ratios": {}, "plots": {}}
    edges = np.arange(60.0, 120.0 + 1e-9, 2.0)
    for flav, im in (("mumu", "m0m1"), ("ee", "e0e1")):
        dm, dj = data[im]
        r = {}
        for tag, lo, hi, zero_j in (("76_106_0j", 76, 106, True), ("60_120_0j", 60, 120, True),
                                    ("60_120_all_jets", 60, 120, False)):
            dsel = (dm >= lo) & (dm <= hi) & ((dj == 0) if zero_j else True)
            d = float(dsel.sum())
            tot, var, by = 0.0, 0.0, {}
            for rid, by_im in mc.items():
                if im not in by_im:
                    continue
                mm, ww, jj = by_im[im]
                s = (mm >= lo) & (mm <= hi) & ((jj == 0) if zero_j else True)
                by[rid] = float(ww[s].sum())
                tot += by[rid]
                var += float((ww[s] ** 2).sum())
            r[tag] = {"data": d, "mc": tot, "mc_stat_error": var ** 0.5,
                      "data_over_mc": d / tot if tot else None,
                      "stat_error": (d ** 0.5 / tot) if tot else None, "mc_by_record": by}
        res["ratios"][flav] = r
        # plot, 0 jets
        dc, _ = np.histogram(dm[dj == 0], bins=edges)
        fig, (ax, axr) = plt.subplots(2, 1, figsize=(7.8, 6.2), sharex=True,
                                      gridspec_kw={"height_ratios": [3, 1], "hspace": 0.05})
        base = np.zeros(len(edges) - 1)
        tot = np.zeros(len(edges) - 1)
        for label, recs, color in GROUPS:
            v = np.zeros(len(edges) - 1)
            for rid in recs:
                by_im = mc.get(str(rid), {})
                if im in by_im:
                    mm, ww, jj = by_im[im]
                    v += np.histogram(mm[jj == 0], bins=edges, weights=ww[jj == 0])[0]
            tot += v
            vp = np.clip(v, 0, None)
            if vp.sum() > 0:
                ax.fill_between(np.repeat(edges, 2)[1:-1], np.repeat(base, 2), np.repeat(base + vp, 2),
                                color=color, lw=0, label=label)
                base += vp
        c = 0.5 * (edges[:-1] + edges[1:])
        ax.errorbar(c, dc, yerr=np.sqrt(dc), fmt="o", ms=3.5, color=DATA_COLOR, label="data")
        ax.set_yscale("log")
        rr = r["76_106_0j"]
        ax.set_title(f"Z peak, {'μμ' if flav == 'mumu' else 'ee'}, 0 jets — before peak removal\n"
                     f"data/MC (76–106 GeV) = {rr['data_over_mc']:.4f} ± {rr['stat_error']:.4f}"
                     f"   (18 Oct, medium IDs: {REF_18OCT[flav]:.4f})", fontsize=9.5, color=INK)
        ax.set_ylabel(f"events / 2 GeV  (L = {LUMI} fb⁻¹)", color=INK)
        ax.text(0.01, 0.02, MISSING_MC, transform=ax.transAxes, fontsize=7, color=INK2)
        h, l = ax.get_legend_handles_labels()
        ax.legend(h[::-1], l[::-1], fontsize=7.5, frameon=False, loc="upper right")
        style(ax)
        ratio = np.divide(dc, tot, out=np.full_like(tot, np.nan), where=tot > 0)
        axr.errorbar(c, ratio, yerr=np.divide(np.sqrt(dc), tot, out=np.zeros_like(tot), where=tot > 0),
                     fmt="o", ms=3, color=DATA_COLOR)
        axr.axhline(1.0, color=INK2, lw=0.8)
        axr.set_ylim(0.6, 1.4)
        axr.set_ylabel("data/MC", color=INK)
        axr.set_xlabel(f"m({'μμ' if flav == 'mumu' else 'ee'}) [GeV]", color=INK)
        style(axr)
        p = out / f"zpeak_{flav}_0j.png"
        fig.savefig(p, dpi=130, bbox_inches="tight", facecolor=SURF)
        plt.close(fig)
        res["plots"][flav] = p.name
    return res


# ---------------------------------------------------------------------------
# histogram files
# ---------------------------------------------------------------------------

def first_filled_low_edge(h: dict):
    v = h["values"][1:-1]
    nz = np.flatnonzero(v != 0)
    return float(h["edges"][nz[0]]) if nz.size else None


def file_checks(path: Path) -> tuple:
    hs = read_all(path)
    n_nonfinite = sum(1 for h in hs.values()
                      if not (np.all(np.isfinite(h["values"])) and np.all(np.isfinite(h["variances"]))))
    n_negvar = sum(1 for h in hs.values() if np.any(h["variances"] < 0))
    n_negbin = sum(1 for h in hs.values() if np.any(h["values"][1:-1] < 0))
    return hs, {"path": str(path), "n_histograms": len(hs), "n_nonfinite": n_nonfinite,
                "n_negative_variance": n_negvar, "n_with_negative_bins": n_negbin,
                "sum_contents": float(sum(h["values"][1:-1].sum() for h in hs.values()))}


def fs_of(name: str) -> str:
    d = parse(name)
    return f"{d['e']}e_{d['m']}m_{d['j']}j_{d['b']}b" if d else "?"


def names_compare(data: dict, mc: dict) -> dict:
    D, M = set(data), set(mc)
    both = sorted(D & M)
    agree, differ = 0, []
    for n in both:
        a, b = first_filled_low_edge(data[n]), first_filled_low_edge(mc[n])
        if a == b:
            agree += 1
        else:
            differ.append({"name": n, "data_first_gev": a, "mc_first_gev": b})
    mc_only_by_fs = defaultdict(list)
    for n in sorted(M - D):
        mc_only_by_fs[fs_of(n)].append(n)
    data_only = sorted(D - M)
    high = [{"name": n, "first_filled_gev": first_filled_low_edge(mc[n]), "entries": mc[n]["entries"]}
            for n in sorted(M) if (first_filled_low_edge(mc[n]) or 0) > 2000.0]
    diffs = [abs(x["data_first_gev"] - x["mc_first_gev"]) for x in differ
             if x["data_first_gev"] is not None and x["mc_first_gev"] is not None]
    return {"n_data": len(D), "n_mc": len(M), "n_both": len(both), "n_mc_only": len(M - D),
            "n_data_only": len(data_only), "data_only": data_only,
            "data_only_by_fs": {fs: sum(1 for n in data_only if fs_of(n) == fs)
                                for fs in sorted({fs_of(n) for n in data_only})},
            "mc_only_by_final_state": {k: len(v) for k, v in sorted(mc_only_by_fs.items())},
            "mc_only_names": {k: v for k, v in sorted(mc_only_by_fs.items())},
            "first_filled_bin_same": agree, "first_filled_bin_different": len(differ),
            "first_filled_bin_abs_diff_gev_histogram": {str(k): int(v) for k, v in zip(
                *np.unique(np.round(diffs, 1), return_counts=True))} if diffs else {},
            "first_filled_bin_differences": differ,
            "mc_first_filled_above_2000_gev": high}


# ---------------------------------------------------------------------------
# per-dataset shares (job_metadata) and the 500,000-entry cap
# ---------------------------------------------------------------------------

def dataset_shares(data_runs: Path, label_map: dict) -> tuple:
    share = defaultdict(lambda: defaultdict(int))   # #40 fs -> dataset -> events
    capped = {}
    for i, label in enumerate(DELIVERY_VETO_ORDER_5):
        key = "final_state_label_event_counts_inclusive" if i == 0 else "final_state_label_event_counts_exclusive"
        index = json.loads((data_runs / f"{label}_index.json").read_text())
        n_cap, n_cap_files = 0, 0
        for job_key in index:
            m = json.loads((data_runs / label / f"job_{job_key}" / "job_metadata.json").read_text())
            for lab, cnt in m[key].items():
                share[label_map.get(lab, lab)][label] += int(cnt)
            c = int(m.get("n_capped_signatures", 0) or 0)
            n_cap += c
            n_cap_files += int(c > 0)
        capped[label] = {"n_capped_signatures": n_cap, "n_files_with_capped": n_cap_files}
    return {k: dict(v) for k, v in share.items()}, capped


# ---------------------------------------------------------------------------
# plots
# ---------------------------------------------------------------------------

def stack_plot(name, title, data, per, summed, out):
    edges = summed[name]["edges"]
    dv = data[name]["values"][1:-1]
    tv = summed[name]["values"][1:-1]
    nz = np.flatnonzero((dv != 0) | (tv != 0))
    lo, hi = nz[0], nz[-1] + 1
    e = edges[lo:hi + 1]
    fig, (ax, axr) = plt.subplots(2, 1, figsize=(8.2, 6.4), sharex=True,
                                  gridspec_kw={"height_ratios": [3, 1], "hspace": 0.05})
    parts = []
    for label, recs, color in GROUPS:
        v = np.zeros(len(edges) - 1)
        for r in recs:
            if name in per.get(r, {}):
                v += per[r][name]["values"][1:-1]
        parts.append((label, color, v))
    base = np.zeros(hi - lo)
    for i in sorted(range(len(parts)), key=lambda i: parts[i][2].sum()):
        label, color, v = parts[i]
        v = np.clip(v[lo:hi], 0, None)
        if v.sum() <= 0:
            continue
        ax.fill_between(np.repeat(e, 2)[1:-1], np.repeat(base, 2), np.repeat(base + v, 2),
                        color=color, lw=0, label=f"{label} ({parts[i][2].sum():,.4g})")
        base = base + v
    c = 0.5 * (e[:-1] + e[1:])
    ax.errorbar(c, dv[lo:hi], yerr=np.sqrt(np.clip(dv[lo:hi], 0, None)), fmt="o", ms=3,
                color=DATA_COLOR, label=f"data ({dv.sum():,.0f})")
    pos = np.concatenate([dv[lo:hi][dv[lo:hi] > 0], base[base > 0]])
    if pos.size and pos.max() / pos.min() > 50:
        ax.set_yscale("log")
    ax.set_ylabel(f"events / 10 GeV  (L = {LUMI} fb⁻¹)", color=INK)
    ax.set_title(f"CMS 2016 G+H, data vs MC — {title}\n{name}  (delivered histograms: Z cut, "
                 f"peak removal applied)", fontsize=8.8, color=INK)
    ax.text(0.01, 0.02, MISSING_MC, transform=ax.transAxes, fontsize=7, color=INK2)
    h, l = ax.get_legend_handles_labels()
    ax.legend(h[::-1], l[::-1], fontsize=7, frameon=False, loc="upper right")
    style(ax)
    ratio = np.divide(dv[lo:hi], tv[lo:hi], out=np.full(hi - lo, np.nan), where=tv[lo:hi] > 0)
    axr.plot(c, ratio, "o", ms=3, color=DATA_COLOR)
    axr.axhline(1.0, color=INK2, lw=0.8)
    axr.set_ylim(0, 2.5)
    axr.set_ylabel("data/MC", color=INK)
    axr.set_xlabel("mass [GeV]", color=INK)
    style(axr)
    fig.savefig(out, dpi=130, bbox_inches="tight", facecolor=SURF)
    plt.close(fig)
    return {"png": out.name, "category": title, "histogram": name, "data_sum": float(dv.sum()),
            "mc_sum": float(tv.sum()), "data_over_mc": float(dv.sum() / tv.sum()) if tv.sum() else None,
            "mc_by_group": {p[0]: float(p[2].sum()) for p in parts}}


STACK_CATEGORIES = [
    ("μμ, 0 jets", lambda d: d["im"] == "m0m1" and (d["e"], d["m"], d["j"], d["b"]) == (0, 2, 0, 0)),
    ("ee, 0 jets", lambda d: d["im"] == "e0e1" and (d["e"], d["m"], d["j"], d["b"]) == (2, 0, 0, 0)),
    ("eμ, 0 jets", lambda d: d["im"] == "e0m0" and (d["e"], d["m"], d["j"], d["b"]) == (1, 1, 0, 0)),
    ("μμ + jets (most populated)", lambda d: d["im"].startswith("m0m1j") and d["m"] == 2 and d["e"] == 0 and d["j"] >= 1),
    ("μ + jet + b (most populated)", lambda d: "j0" in d["im"] and "b0" in d["im"] and d["m"] == 1 and d["e"] == 0
     and d["im"].startswith("m0")),
    ("3–4 leptons (most populated)", lambda d: d["e"] + d["m"] in (3, 4)),
]


def per_fs_plot(data, summed, out):
    cnt_d = defaultdict(int)
    cnt_m = defaultdict(int)
    for n in data:
        cnt_d[fs_of(n)] += 1
    for n in summed:
        cnt_m[fs_of(n)] += 1
    fss = sorted(set(cnt_d) | set(cnt_m), key=lambda f: [int(x) for x in re.findall(r"\d+", f)])
    x = np.arange(len(fss))
    fig, ax = plt.subplots(figsize=(15, 5))
    ax.bar(x - 0.21, [cnt_d[f] for f in fss], 0.4, color="#2a78d6", label=f"data ({len(data)} histograms)")
    ax.bar(x + 0.21, [cnt_m[f] for f in fss], 0.4, color="#eb6834", label=f"MC summed SM ({len(summed)})")
    ax.set_xticks(x, fss, rotation=90, fontsize=7)
    ax.set_ylabel("histograms", color=INK)
    ax.set_title("Delivered histograms per final state (#40 rule), data vs MC", color=INK)
    ax.legend(frameon=False)
    style(ax)
    fig.savefig(out, dpi=130, bbox_inches="tight", facecolor=SURF)
    plt.close(fig)
    return {"png": out.name, "data": dict(cnt_d), "mc": dict(cnt_m)}


def dataset_examples(data, shares, out):
    """Per dataset, the two delivered final states it dominates most (share of
    the pooled events), and that final state's most-populated histogram."""
    rows, picks = [], []
    for ds in DELIVERY_VETO_ORDER_5:
        cand = []
        for fs, by in shares.items():
            tot = sum(by.values())
            names = [n for n in data if fs_of(n) == fs]
            if not names or tot == 0:
                continue
            cand.append((by.get(ds, 0) / tot, by.get(ds, 0), fs, names))
        cand.sort(key=lambda x: (-x[0], -x[1]))
        for share, nds, fs, names in cand[:2]:
            n = max(names, key=lambda k: data[k]["entries"])
            picks.append((ds, share, fs, n))
            rows.append({"dataset": ds, "final_state": fs, "share_of_events": share, "histogram": n,
                         "entries": data[n]["entries"]})
    fig, axes = plt.subplots(5, 2, figsize=(13, 17))
    for ax, (ds, share, fs, n) in zip(axes.flat, picks):
        h = data[n]
        v, e = h["values"][1:-1], h["edges"]
        nz = np.flatnonzero(v)
        lo, hi = nz[0], nz[-1] + 1
        ax.stairs(v[lo:hi], e[lo:hi + 1], color="#2a78d6", lw=1.8)
        ax.errorbar(0.5 * (e[lo:hi] + e[lo + 1:hi + 1]), v[lo:hi], yerr=np.sqrt(v[lo:hi]), fmt="none",
                    ecolor=INK2, lw=0.7)
        if v[lo:hi].max() / max(v[lo:hi][v[lo:hi] > 0].min(), 1) > 50:
            ax.set_yscale("log")
        ax.set_title(f"{ds}: {share:.0%} of the events in {fs}\n{n} ({h['entries']:,.0f} entries)",
                     fontsize=8.5, color=INK)
        ax.set_xlabel("mass [GeV]", fontsize=8, color=INK2)
        style(ax)
    fig.suptitle("Example delivered data histograms, two per dataset (the final states each dataset "
                 "dominates)", color=INK)
    fig.tight_layout()
    fig.savefig(out, dpi=110, bbox_inches="tight", facecolor=SURF)
    plt.close(fig)
    return {"png": out.name, "examples": rows}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-build", required=True)
    ap.add_argument("--data-runs", required=True)
    ap.add_argument("--mc-build", required=True)
    ap.add_argument("--mc-scratch", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--skip-zpeak", action="store_true")
    a = ap.parse_args()
    out = Path(a.out_dir)
    (out / "plots").mkdir(parents=True, exist_ok=True)
    db, mb = Path(a.data_build), Path(a.mc_build)
    res = {"inputs": vars(a)}

    data, res_d = file_checks(db / "fullrun_bumpnet.root")
    _crop, res_dc = file_checks(db / "fullrun_bumpnet_cropped.root")
    summed, res_s = file_checks(mb / "fullrun_summedSM_mc.root")
    per, res_per = {}, {}
    for p in sorted(mb.glob("fullrun_record*_mc.root")):
        rid = int(re.search(r"record(\d+)_", p.name).group(1))
        per[rid], res_per[rid] = file_checks(p)
    res["file_checks"] = {"data_uncropped": res_d, "data_cropped": res_dc, "mc_summedSM": res_s,
                          "mc_per_record": res_per}
    res["final_states"] = {"data": len({fs_of(n) for n in data}), "mc_summedSM": len({fs_of(n) for n in summed})}
    res["names"] = names_compare(data, summed)
    print(json.dumps({k: v for k, v in res["names"].items() if not isinstance(v, (list, dict))}), flush=True)

    label_map = json.loads((db / "multiplicity_rule_fullrun.json").read_text())["label_map"]
    shares, capped = dataset_shares(Path(a.data_runs), label_map)
    res["dataset_shares_by_final_state"] = shares
    res["data_capped_signatures"] = capped

    plots = {}
    parsed = {n: parse(n) for n in data if n in summed}
    stacks = []
    for i, (title, pred) in enumerate(STACK_CATEGORIES, 1):
        cands = [n for n, d in parsed.items() if d and pred(d)]
        if not cands:
            stacks.append({"category": title, "missing": "no histogram in both data and MC"})
            continue
        n = max(cands, key=lambda k: summed[k]["entries"])
        stacks.append(stack_plot(n, title, data, per, summed, out / "plots" / f"stack_{i}.png"))
    plots["stacks"] = stacks
    plots["per_final_state"] = per_fs_plot(data, summed, out / "plots" / "histograms_per_final_state.png")
    plots["dataset_examples"] = dataset_examples(data, shares, out / "plots" / "dataset_examples.png")
    res["plots"] = plots
    (out / "analysis.json").write_text(json.dumps(res, indent=1, default=float))
    print("wrote analysis.json (without the Z peak)", flush=True)

    if not a.skip_zpeak:
        res["zpeak"] = zpeak(Path(a.data_runs), Path(a.mc_scratch), out / "plots")
        (out / "analysis.json").write_text(json.dumps(res, indent=1, default=float))
        print(json.dumps(res["zpeak"]["ratios"], indent=1, default=float)[:3000], flush=True)
    print("done", flush=True)


if __name__ == "__main__":
    main()
