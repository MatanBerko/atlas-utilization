#!/usr/bin/env python
"""
Pilot Part 4: data vs simulation, read from the STORED EVENTS (the shards)
directly -- before the Z cut, peak removal and the outlier split.

Why before post-processing: the 110 GeV Z cut removes the Z peak from every
delivered same-flavour dilepton histogram, so a comparison built on delivered
histograms could not show the Z at all. Both sides are therefore read from
their shards at the same stage, and nothing is rescaled.

  DATA  the delivered four-dataset production, de-duplicated exactly as the
        delivery does it: the highest-priority dataset (DoubleMuon)
        contributes its INCLUSIVE shard and every other its EXCLUSIVE one, so
        each collision is counted once. Version B (`rare4`) shards. Read-only.
  MC    the pilot shards after the builder has written the final `_mcw`
        weights, restricted to the union of the FOUR data acceptance flags --
        Ele27-only events are excluded, to match what the data streams can
        contain. DY + ttbar + ggH stacked. Absolute normalisation, no fitting
        or rescaling of any kind.

Errors: data sqrt(N), MC sqrt(sum w^2).

Plots (PNG, each with a data/MC ratio panel):
  P1  Z peak, mumu   -- m0m1 in final states with exactly 2 muons, 0 electrons
  P2  Z peak, ee     -- e0e1 in final states with exactly 2 electrons, 0 muons
  P3  jet and b-jet multiplicity for Z events (dilepton mass 76-106 GeV)
  P4  e-mu           -- e0m0 in final states with exactly 1 electron, 1 muon
  P5  4-lepton mass  -- 4mu, 4e, 2e2mu

Also fits a Gaussian core to the Z peak in data and in MC and reports both
positions, so a mass-scale or width difference is stated rather than eyeballed.

Writes PNGs and one JSON into --out-dir. Reads everything else read-only.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

from services.storage.sqlite_shards import (  # noqa: E402
    iter_arrays_for_signature, list_signatures,
)
from studies.cms_datasets.cluster.run_dataset_on_file import (  # noqa: E402
    DELIVERY_VETO_ORDER_4, MC_SIBLING_ACCEPTANCE, MC_WEIGHT_SUFFIX,
)
from studies.cms_mc_weights_v3.deliver.build_mc_delivery import (  # noqa: E402
    SIG_PATTERN, event_union_mask,
)

DATA_SHARD_INCL = "dataset_shard_rare4_inclusive.sqlite"
DATA_SHARD_EXCL = "dataset_shard_rare4_exclusive.sqlite"
MC_SHARD = "dataset_shard_rare4_inclusive.sqlite"
LUMI_FB = 16.393

# final-state label -> per-type counts, e.g. "0e_2m_5j_1b"
FS_TOKEN = re.compile(r"(\d+)([emjgtb])")

SAMPLE_STYLE = {
    "35669": ("DY -> ll (NLO)", "#4299e1"),
    "67801": ("t-tbar -> 2l2nu", "#ed8936"),
    "37728": ("ggH -> ZZ -> 4l", "#9f7aea"),
}


def fs_counts(fs_str: str) -> dict:
    out = {"e": 0, "m": 0, "j": 0, "b": 0, "g": 0, "t": 0}
    for n, letter in FS_TOKEN.findall(fs_str):
        out[letter] = int(n)
    return out


# ---------------------------------------------------------------------------
# readers
# ---------------------------------------------------------------------------

def read_data(runs_dir: pathlib.Path, want_im: set, fs_filter) -> dict:
    """{im_str: (masses, fs_counts_per_entry)} over the de-duplicated delivered
    population. `fs_filter(counts) -> bool` selects final states."""
    out = defaultdict(lambda: ([], []))
    n_shards = 0
    for i, label in enumerate(DELIVERY_VETO_ORDER_4):
        shard_name = DATA_SHARD_INCL if i == 0 else DATA_SHARD_EXCL
        index_path = runs_dir / f"{label}_index.json"
        index = json.loads(index_path.read_text(encoding="utf-8"))
        for job_key in sorted(index, key=int):
            shard = runs_dir / label / f"job_{job_key}" / shard_name
            if not shard.exists():
                raise SystemExit(f"missing delivered shard: {shard}")
            n_shards += 1
            for sig in list_signatures(str(shard)):
                m = SIG_PATTERN.search(sig)
                if not m:
                    continue
                fs_str, im_str = m.groups()
                if im_str not in want_im:
                    continue
                counts = fs_counts(fs_str)
                if not fs_filter(im_str, counts):
                    continue
                for chunk in iter_arrays_for_signature(str(shard), sig):
                    if len(chunk):
                        out[im_str][0].append(np.asarray(chunk, dtype=np.float64))
                        out[im_str][1].append(
                            np.repeat(np.array([[counts["j"], counts["b"]]]),
                                      len(chunk), axis=0))
    res = {}
    for im, (ms, cs) in out.items():
        if ms:
            res[im] = (np.concatenate(ms), np.concatenate(cs))
    res["_n_shards"] = n_shards
    return res


def read_mc(scratch_dir: pathlib.Path, want_im: set, fs_filter) -> dict:
    """{record: {im_str: (masses, weights, jb_counts)}} from the builder's
    scratch shards, which carry the final `_mcw` weights.

    Only entries in the union of the FOUR data acceptance flags are kept, so
    the MC population matches what the data streams can contain."""
    per_record = defaultdict(lambda: defaultdict(lambda: ([], [], [])))
    n_shards = 0
    n_dropped_union = 0
    for shard in sorted(scratch_dir.rglob("*.sqlite")):
        rid = shard.parent.name.replace("record_", "")
        n_shards += 1
        sigs = set(list_signatures(str(shard)))
        for sig in sorted(sigs):
            m = SIG_PATTERN.search(sig)
            if not m:
                continue
            fs_str, im_str = m.groups()
            if im_str not in want_im:
                continue
            counts = fs_counts(fs_str)
            if not fs_filter(im_str, counts):
                continue
            masses = list(iter_arrays_for_signature(str(shard), sig))
            weights = list(iter_arrays_for_signature(str(shard), sig + MC_WEIGHT_SUFFIX))
            accs = list(iter_arrays_for_signature(str(shard), sig + MC_SIBLING_ACCEPTANCE))
            if not masses:
                continue
            if not weights:
                raise SystemExit(
                    f"{shard}: {sig} has masses but no {MC_WEIGHT_SUFFIX} -- run "
                    "build_mc_delivery.py with --keep-scratch first.")
            mm = np.concatenate([np.asarray(c, dtype=np.float64) for c in masses])
            ww = np.concatenate([np.asarray(c, dtype=np.float64) for c in weights])
            if len(mm) != len(ww):
                raise SystemExit(f"{shard}: {sig} has {len(mm)} masses, {len(ww)} weights")
            if accs:
                aa = np.concatenate([np.asarray(c) for c in accs])
                if len(aa) != len(mm):
                    raise SystemExit(f"{shard}: {sig} acceptance length mismatch")
                keep = event_union_mask(aa)
                n_dropped_union += int((~keep).sum())
                mm, ww = mm[keep], ww[keep]
            if mm.size == 0:
                continue
            per_record[rid][im_str][0].append(mm)
            per_record[rid][im_str][1].append(ww)
            per_record[rid][im_str][2].append(
                np.repeat(np.array([[counts["j"], counts["b"]]]), len(mm), axis=0))
    out = {}
    for rid, by_im in per_record.items():
        out[rid] = {im: (np.concatenate(a), np.concatenate(b), np.concatenate(c))
                    for im, (a, b, c) in by_im.items() if a}
    out["_n_shards"] = n_shards
    out["_n_entries_dropped_by_event_union"] = n_dropped_union
    return out


# ---------------------------------------------------------------------------
# plotting
# ---------------------------------------------------------------------------

def _stack_and_ratio(ax_main, ax_ratio, edges, data_counts, mc_by_sample,
                     xlabel, title, logy=False):
    """One stacked-MC vs data panel plus its ratio panel. Returns the summary."""
    centres = 0.5 * (edges[:-1] + edges[1:])
    widths = np.diff(edges)

    bottom = np.zeros(len(centres))
    mc_total = np.zeros(len(centres))
    mc_var = np.zeros(len(centres))
    for rid in sorted(mc_by_sample, key=lambda r: -mc_by_sample[r][0].sum()):
        vals, var = mc_by_sample[rid]
        label, colour = SAMPLE_STYLE.get(rid, (rid, "#a0aec0"))
        ax_main.bar(centres, vals, width=widths, bottom=bottom, label=label,
                    color=colour, edgecolor="none", alpha=0.85)
        bottom = bottom + vals
        mc_total = mc_total + vals
        mc_var = mc_var + var

    mc_err = np.sqrt(mc_var)
    ax_main.errorbar(centres, mc_total, yerr=mc_err, fmt="none",
                     ecolor="#2d3748", elinewidth=1, capsize=0, alpha=0.6)
    d_err = np.sqrt(data_counts)
    ax_main.errorbar(centres, data_counts, yerr=d_err, fmt="o", ms=3.2,
                     color="black", lw=1, capsize=1.5, label="data (2016 G+H)")
    ax_main.set_ylabel(f"events / {widths[0]:g}" if np.allclose(widths, widths[0])
                       else "events / bin")
    ax_main.set_title(title, fontsize=9.5)
    ax_main.legend(fontsize=7.5)
    ax_main.grid(alpha=0.2, lw=0.5)
    if logy:
        ax_main.set_yscale("log")

    with np.errstate(divide="ignore", invalid="ignore"):
        ratio = np.where(mc_total > 0, data_counts / mc_total, np.nan)
        rerr = np.where(mc_total > 0,
                        np.sqrt(np.maximum(data_counts, 0)) / mc_total, np.nan)
    ax_ratio.errorbar(centres, ratio, yerr=rerr, fmt="o", ms=3.2, color="black",
                      lw=1, capsize=1.5)
    ax_ratio.axhline(1.0, color="#718096", ls="--", lw=1)
    ax_ratio.set_ylabel("data / MC", fontsize=8)
    ax_ratio.set_xlabel(xlabel)
    ax_ratio.set_ylim(0, 2)
    ax_ratio.grid(alpha=0.2, lw=0.5)

    d_tot, m_tot = float(data_counts.sum()), float(mc_total.sum())
    return {
        "data_integral": d_tot,
        "mc_integral": m_tot,
        "mc_stat_error": float(np.sqrt(mc_var.sum())),
        "ratio": (d_tot / m_tot) if m_tot else None,
        "ratio_stat_error": (np.sqrt(d_tot) / m_tot) if m_tot else None,
        "per_sample_integral": {r: float(v[0].sum()) for r, v in mc_by_sample.items()},
    }


def gaussian_core_fit(centres, values, lo=85.0, hi=97.0):
    """A plain Gaussian least-squares fit to the peak core, stated as such.

    Not a Breit-Wigner convolved with resolution -- just enough to put a number
    on a mass-scale shift. Returns None when the window has too few points."""
    sel = (centres >= lo) & (centres <= hi) & (values > 0)
    if int(sel.sum()) < 4:
        return None
    x, y = centres[sel], values[sel]
    # ln y = ln A - (x - mu)^2 / (2 sigma^2) -> quadratic in x
    try:
        c2, c1, c0 = np.polyfit(x, np.log(y), 2)
    except Exception:  # noqa: BLE001
        return None
    if c2 >= 0:
        return None
    sigma = float(np.sqrt(-1.0 / (2.0 * c2)))
    mu = float(-c1 / (2.0 * c2))
    return {"fit": "Gaussian core, least squares on ln(counts)",
            "window_gev": [lo, hi], "peak_gev": mu, "sigma_gev": sigma,
            "n_points": int(sel.sum())}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-runs-dir", required=True)
    ap.add_argument("--mc-scratch-dir", required=True,
                    help="the builder's --keep-scratch directory, built with "
                         "--min-events-per-fs 1 so nothing is pruned")
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--z-bin-width", type=float, default=2.0)
    args = ap.parse_args()

    out_dir = pathlib.Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    want_im = {"m0m1", "e0e1", "e0m0", "m0m1m2m3", "e0e1e2e3", "e0e1m0m1"}

    def keep(im, c):
        if im == "m0m1":
            return c["e"] == 0 and c["m"] == 2
        if im == "e0e1":
            return c["e"] == 2 and c["m"] == 0
        if im == "e0m0":
            return c["e"] == 1 and c["m"] == 1
        if im == "m0m1m2m3":
            return c["e"] == 0 and c["m"] == 4
        if im == "e0e1e2e3":
            return c["e"] == 4 and c["m"] == 0
        if im == "e0e1m0m1":
            return c["e"] == 2 and c["m"] == 2
        return False

    print("reading DATA shards ...", flush=True)
    data = read_data(pathlib.Path(args.data_runs_dir), want_im, keep)
    print(f"  {data.pop('_n_shards')} data shards", flush=True)
    for im in sorted(data):
        print(f"    {im}: {len(data[im][0]):,} entries", flush=True)

    print("reading MC shards ...", flush=True)
    mc = read_mc(pathlib.Path(args.mc_scratch_dir), want_im, keep)
    n_mc_shards = mc.pop("_n_shards")
    n_union_dropped = mc.pop("_n_entries_dropped_by_event_union")
    print(f"  {n_mc_shards} MC shards; {n_union_dropped:,} entries dropped by "
          f"the four-flag event union", flush=True)
    for rid in sorted(mc):
        for im in sorted(mc[rid]):
            print(f"    {rid} {im}: {len(mc[rid][im][0]):,} entries, "
                  f"sum w = {mc[rid][im][1].sum():,.1f}", flush=True)

    report = {
        "what": "CMS MC pilot: data vs simulation, read from the stored events "
                "before the Z cut / peak removal / outlier split",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "data_runs_dir": str(args.data_runs_dir),
        "mc_scratch_dir": str(args.mc_scratch_dir),
        "luminosity_fb": LUMI_FB,
        "normalisation": "absolute; MC is NOT rescaled to data",
        "data_population": "delivered four-dataset de-duplicated set "
                           "(DoubleMuon inclusive + the other three exclusive), "
                           "Version B rare4 shards",
        "mc_population": "union of the four data acceptance flags; Ele27-only "
                         "events excluded",
        "n_mc_entries_dropped_by_event_union": n_union_dropped,
        "errors": "data sqrt(N), MC sqrt(sum w^2)",
        "plots": {},
    }

    def binned(masses, weights, edges):
        v, _ = np.histogram(masses, bins=edges, weights=weights)
        w2, _ = np.histogram(masses, bins=edges,
                             weights=None if weights is None else weights ** 2)
        return v, w2

    # ---- P1 / P2: the Z peak ------------------------------------------
    z_edges = np.arange(60.0, 120.0 + 1e-9, args.z_bin_width)
    for tag, im, title in (("P1", "m0m1", "Z peak, dimuon (exactly 2 muons, 0 electrons)"),
                           ("P2", "e0e1", "Z peak, dielectron (exactly 2 electrons, 0 muons)")):
        fig, (axm, axr) = plt.subplots(
            2, 1, figsize=(7.0, 5.6), sharex=True,
            gridspec_kw={"height_ratios": [3, 1], "hspace": 0.06})
        d_counts, _ = binned(data[im][0], None, z_edges) if im in data else (
            np.zeros(len(z_edges) - 1), None)
        mc_by = {}
        for rid in sorted(mc):
            if im not in mc[rid]:
                continue
            v, w2 = binned(mc[rid][im][0], mc[rid][im][1], z_edges)
            mc_by[rid] = (v, w2)
        summ = _stack_and_ratio(axm, axr, z_edges, d_counts, mc_by,
                                f"{'dimuon' if im == 'm0m1' else 'dielectron'} "
                                f"invariant mass [GeV]", title)
        centres = 0.5 * (z_edges[:-1] + z_edges[1:])
        mc_tot = sum(v for v, _ in mc_by.values()) if mc_by else np.zeros(len(centres))
        summ["data_gaussian_core_fit"] = gaussian_core_fit(centres, d_counts)
        summ["mc_gaussian_core_fit"] = gaussian_core_fit(centres, mc_tot)
        fig.suptitle("CMS MC pilot -- absolute normalisation, L = 16.393 fb^-1. "
                     "MC = DY + ttbar + ggH only.\nBefore the Z cut: read from "
                     "the stored events, not the delivered histograms.",
                     fontsize=8.5)
        fig.tight_layout(rect=(0, 0, 1, 0.92))
        path = out_dir / f"{tag}_zpeak_{'mumu' if im == 'm0m1' else 'ee'}.png"
        fig.savefig(path, dpi=140)
        plt.close(fig)
        summ["png"] = str(path)
        report["plots"][tag] = summ
        print(f"wrote {path}", flush=True)

    # ---- P3: jet and b-jet multiplicity for Z events --------------------
    fig, axes = plt.subplots(2, 4, figsize=(17.0, 6.4),
                             gridspec_kw={"height_ratios": [3, 1], "hspace": 0.08})
    p3 = {}
    for col, (im, flavour) in enumerate((("m0m1", "mumu"), ("e0e1", "ee"))):
        for kind, maxk, labels in (("j", 5, ["0", "1", "2", "3", "4", "5+"]),
                                   ("b", 2, ["0", "1", "2+"])):
            idx = col * 2 + (0 if kind == "j" else 1)
            axm, axr = axes[0][idx], axes[1][idx]
            edges = np.arange(-0.5, maxk + 1.0, 1.0)
            col_i = 0 if kind == "j" else 1

            if im in data:
                m, jb = data[im]
                sel = (m >= 76.0) & (m <= 106.0)
                k = np.clip(jb[sel][:, col_i], 0, maxk)
                d_counts, _ = np.histogram(k, bins=edges)
            else:
                d_counts = np.zeros(len(edges) - 1)
            mc_by = {}
            for rid in sorted(mc):
                if im not in mc[rid]:
                    continue
                m, w, jb = mc[rid][im]
                sel = (m >= 76.0) & (m <= 106.0)
                k = np.clip(jb[sel][:, col_i], 0, maxk)
                v, _ = np.histogram(k, bins=edges, weights=w[sel])
                w2, _ = np.histogram(k, bins=edges, weights=w[sel] ** 2)
                mc_by[rid] = (v, w2)
            summ = _stack_and_ratio(
                axm, axr, edges, d_counts, mc_by,
                ("light jets" if kind == "j" else "b-jets"),
                f"{flavour}, 76-106 GeV: {'light-jet' if kind == 'j' else 'b-jet'} multiplicity",
                logy=True)
            axr.set_xticks(range(maxk + 1))
            axr.set_xticklabels(labels)
            # per-bin ratios are what the >=3-jet question needs
            mc_tot = sum(v for v, _ in mc_by.values()) if mc_by else np.zeros(len(edges) - 1)
            with np.errstate(divide="ignore", invalid="ignore"):
                per_bin = np.where(mc_tot > 0, d_counts / mc_tot, np.nan)
            summ["per_bin_ratio"] = {labels[i]: (None if np.isnan(per_bin[i])
                                                 else float(per_bin[i]))
                                     for i in range(len(labels))}
            summ["per_bin_data"] = {labels[i]: float(d_counts[i]) for i in range(len(labels))}
            summ["per_bin_mc"] = {labels[i]: float(mc_tot[i]) for i in range(len(labels))}
            p3[f"{flavour}_{kind}"] = summ
    fig.suptitle("CMS MC pilot -- jet and b-jet multiplicity for Z-window events "
                 "(dilepton mass 76-106 GeV). Absolute normalisation.", fontsize=9)
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    path = out_dir / "P3_jet_multiplicity_zwindow.png"
    fig.savefig(path, dpi=140)
    plt.close(fig)
    p3["png"] = str(path)
    report["plots"]["P3"] = p3
    print(f"wrote {path}", flush=True)

    # ---- P4: e-mu -------------------------------------------------------
    emu_edges = np.arange(0.0, 500.0 + 1e-9, 10.0)
    fig, (axm, axr) = plt.subplots(
        2, 1, figsize=(7.0, 5.6), sharex=True,
        gridspec_kw={"height_ratios": [3, 1], "hspace": 0.06})
    d_counts, _ = binned(data["e0m0"][0], None, emu_edges) if "e0m0" in data else (
        np.zeros(len(emu_edges) - 1), None)
    mc_by = {}
    for rid in sorted(mc):
        if "e0m0" not in mc[rid]:
            continue
        v, w2 = binned(mc[rid]["e0m0"][0], mc[rid]["e0m0"][1], emu_edges)
        mc_by[rid] = (v, w2)
    summ = _stack_and_ratio(axm, axr, emu_edges, d_counts, mc_by,
                            "e-mu invariant mass [GeV]",
                            "e-mu (exactly 1 electron, 1 muon)")
    fig.suptitle("CMS MC pilot -- e-mu mass. MC is DY + ttbar + ggH ONLY: single "
                 "top, dibosons, W+jets and fakes\nare not in the pilot, so MC "
                 "below data is expected here.", fontsize=8.5)
    fig.tight_layout(rect=(0, 0, 1, 0.92))
    path = out_dir / "P4_emu_mass.png"
    fig.savefig(path, dpi=140)
    plt.close(fig)
    summ["png"] = str(path)
    report["plots"]["P4"] = summ
    print(f"wrote {path}", flush=True)

    # ---- P5: the 4-lepton mass -----------------------------------------
    four_edges = np.arange(70.0, 200.0 + 1e-9, 5.0)
    fig, axes = plt.subplots(1, 3, figsize=(16.0, 4.6))
    p5 = {}
    for ax, (im, name) in zip(axes, (("m0m1m2m3", "4mu"), ("e0e1e2e3", "4e"),
                                     ("e0e1m0m1", "2e2mu"))):
        centres = 0.5 * (four_edges[:-1] + four_edges[1:])
        d_counts, _ = (binned(data[im][0], None, four_edges) if im in data
                       else (np.zeros(len(centres)), None))
        mc_tot = np.zeros(len(centres))
        mc_var = np.zeros(len(centres))
        for rid in sorted(mc):
            if im not in mc[rid]:
                continue
            v, w2 = binned(mc[rid][im][0], mc[rid][im][1], four_edges)
            mc_tot += v
            mc_var += w2
        ax.bar(centres, mc_tot, width=np.diff(four_edges), color="#9f7aea",
               alpha=0.8, edgecolor="none", label="MC (DY+ttbar+ggH)")
        ax.errorbar(centres, mc_tot, yerr=np.sqrt(mc_var), fmt="none",
                    ecolor="#2d3748", elinewidth=1, alpha=0.6)
        ax.errorbar(centres, d_counts, yerr=np.sqrt(d_counts), fmt="o", ms=3.5,
                    color="black", lw=1, capsize=1.5, label="data")
        ax.axvline(125.0, color="#c05621", ls="--", lw=1, label="m(H) = 125 GeV")
        ax.set_title(f"{name}  ({im})", fontsize=9.5)
        ax.set_xlabel("4-lepton invariant mass [GeV]")
        ax.set_ylabel("events / 5 GeV")
        ax.legend(fontsize=7.5)
        ax.grid(alpha=0.2, lw=0.5)
        p5[name] = {
            "data_entries": float(d_counts.sum()),
            "mc_weighted": float(mc_tot.sum()),
            "mc_stat_error": float(np.sqrt(mc_var.sum())),
            "data_raw_entries_in_shards": (int(len(data[im][0])) if im in data else 0),
        }
    fig.suptitle("CMS MC pilot -- 4-lepton mass, data vs MC. Very few events are "
                 "expected: the lepton pT thresholds are 25 GeV.", fontsize=9)
    fig.tight_layout(rect=(0, 0, 1, 0.91))
    path = out_dir / "P5_fourlepton_mass.png"
    fig.savefig(path, dpi=140)
    plt.close(fig)
    p5["png"] = str(path)
    report["plots"]["P5"] = p5
    print(f"wrote {path}", flush=True)

    out = out_dir / "data_mc_comparison.json"
    out.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    print(f"\nwrote {out}")

    print("\n=== data / MC integral ratios ===")
    for tag in ("P1", "P2", "P4"):
        s = report["plots"][tag]
        if s.get("ratio") is not None:
            print(f"  {tag}: data={s['data_integral']:>12,.0f}  "
                  f"MC={s['mc_integral']:>12,.1f}  "
                  f"ratio={s['ratio']:.4f} +/- {s['ratio_stat_error']:.4f}")
    for key in ("mumu_j", "ee_j"):
        s = report["plots"]["P3"][key]
        print(f"  P3 {key}: ratio={s['ratio']:.4f} +/- {s['ratio_stat_error']:.4f}"
              f"   per-bin: {s['per_bin_ratio']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
