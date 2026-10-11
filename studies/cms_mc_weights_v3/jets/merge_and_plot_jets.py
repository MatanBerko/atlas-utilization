#!/usr/bin/env python
"""
Parts B, C and D: merge the per-file probe JSONs, make the tables and plots,
and score each pre-stated suspect.

Normalisation, stated up front because it matters for reading every plot:

  * Each MC sample's events carry `genWeight x L1PreFiringWeight_Nom` from
    the probe. Here they are multiplied by `sigma_eff[pb] * 1000 * L_fb /
    Sigma-w(subset)`, where Sigma-w(subset) is the Runs-tree `genEventSumw`
    summed over exactly the files in this subset. That is the pilot's own
    rule applied to the subset, so the MC is on an absolute footing.
  * A data file's integrated luminosity is not recoverable from what is
    stored, so the data subset's luminosity is NOT known. **This is
    therefore a SHAPE study**: per channel the MC is rescaled by one single
    number so its inclusive Z-window yield matches the data subset's, and
    that number is reported. Every question asked here -- does the ratio
    rise with jet multiplicity, does a different jet definition change it,
    does JER or JES move it, do the extra jets look different in data -- is
    a statement about shape and is untouched by that one factor.
  * The ABSOLUTE normalisation was already answered by the pilot
    (data/MC = 1.034 mumu, 0.953 ee over the full file set).
  * Part C5 is the one exception: the particle-level cross section is an
    absolute prediction in pb, with no rescaling at all, compared directly
    with the published measurement.
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

from studies.cms_mc_weights_v3.deliver.compare_data_mc import (  # noqa: E402
    LUMI_FB, SAMPLE_STYLE,
)

NJET_LABELS = ["0", "1", "2", "3", "4", "5+"]
PB_TO_FB = 1000.0
CHANNELS = ("mumu", "ee")
CHANNEL_TITLE = {"mumu": r"$\mu\mu$", "ee": "ee"}
# keys whose values are raw counts and must never be scaled by a weight
RAW_SUFFIXES = ("_raw",)


def is_raw(key):
    return any(key.endswith(s) for s in RAW_SUFFIXES)


def accumulate(dst, key, value, scale):
    """Add one probe entry into the running sum, scaling the weighted ones."""
    if isinstance(value, dict):
        sub = dst.setdefault(key, {})
        for name, inner in value.items():
            factor = 1.0 if name == "raw" else (scale ** 2 if name == "w2"
                                                else scale)
            arr = np.asarray(inner, dtype=np.float64) * factor
            sub[name] = arr if name not in sub else sub[name] + arr
        return
    if isinstance(value, list):
        factor = 1.0 if is_raw(key) else scale
        arr = np.asarray(value, dtype=np.float64) * factor
        dst[key] = arr if key not in dst else dst[key] + arr
        return
    if isinstance(value, (int, float)):
        factor = 1.0 if is_raw(key) else scale
        dst[key] = dst.get(key, 0.0) + value * factor


def merge(probe_dir, registry, inputs):
    """Sum the per-file histograms, applying each MC sample's absolute
    normalisation over the Sigma-w of the subset actually read."""
    files = sorted(p for p in probe_dir.glob("*.json")
                   if not p.name.startswith("smoke_"))
    if not files:
        raise SystemExit("no probe JSONs in {}".format(probe_dir))

    meta = {"data_files": 0, "mc_files": defaultdict(int),
            "sigma_w_subset": defaultdict(float),
            "probe_files": len(files), "jet_id_titles": set(),
            "raw_factor_titles": set(), "jet_pt_titles": set(),
            "jer": {}, "n_read": 0}

    # pass 1: Sigma-w of the MC files actually in the subset
    for path in files:
        payload = json.loads(path.read_text(encoding="utf-8"))
        meta["n_read"] += int(payload["n_read"])
        meta["jet_id_titles"].add(payload.get("jet_id_branch_title"))
        meta["raw_factor_titles"].add(payload.get("jet_rawfactor_branch_title"))
        meta["jet_pt_titles"].add(payload.get("jet_pt_branch_title"))
        if payload["kind"] != "mc":
            meta["data_files"] += 1
            continue
        rid = str(payload["record_id"])
        index = payload["file_index"]
        per_file = inputs["records"][rid]["files"][index]
        if per_file["file_index"] != index:
            raise SystemExit(
                "input index mismatch for {} file {}".format(rid, index))
        meta["sigma_w_subset"][rid] += float(per_file["runs_gen_event_sumw"])
        meta["mc_files"][rid] += 1
        if payload.get("jer", {}).get("applied"):
            meta["jer"] = {k: v for k, v in payload["jer"].items()
                           if k in ("source", "resolution", "scale_factor")}

    norm = {}
    for rid, sumw in meta["sigma_w_subset"].items():
        record = registry["records"][rid]
        if record["k_factor"] != 1.0 or record["gen_filt_eff"] != 1.0:
            raise SystemExit("record {}: k/eps must be 1.0".format(rid))
        norm[rid] = float(record["cross_section_pb"]) * PB_TO_FB * LUMI_FB / sumw

    data = {ch: {} for ch in CHANNELS}
    mc = {ch: defaultdict(dict) for ch in CHANNELS}
    gen = defaultdict(dict)
    gen_sumw = defaultdict(float)

    # pass 2: the histograms
    for path in files:
        payload = json.loads(path.read_text(encoding="utf-8"))
        is_mc = payload["kind"] == "mc"
        rid = str(payload["record_id"])
        scale = norm[rid] if is_mc else 1.0

        if is_mc and payload.get("gen_particle_level"):
            block = payload["gen_particle_level"]
            gen_sumw[rid] += float(block["sum_genweight_all_events"])
            for key, value in block.items():
                if isinstance(value, (dict, list)):
                    accumulate(gen[rid], key, value, 1.0)

        for channel, entry in payload["channels"].items():
            if not entry:
                continue
            target = mc[channel][rid] if is_mc else data[channel]
            for key, value in entry.items():
                accumulate(target, key, value, scale)

    mc_sum = {ch: {} for ch in CHANNELS}
    for channel in CHANNELS:
        for rid, block in mc[channel].items():
            for key, value in block.items():
                if isinstance(value, dict):
                    sub = mc_sum[channel].setdefault(key, {})
                    for name, arr in value.items():
                        sub[name] = arr if name not in sub else sub[name] + arr
                elif isinstance(value, np.ndarray):
                    mc_sum[channel][key] = (
                        value if key not in mc_sum[channel]
                        else mc_sum[channel][key] + value)
                else:
                    mc_sum[channel][key] = mc_sum[channel].get(key, 0.0) + value

    meta["norm"] = norm
    meta["jet_id_titles"] = sorted(t for t in meta["jet_id_titles"] if t)
    meta["raw_factor_titles"] = sorted(t for t in meta["raw_factor_titles"] if t)
    meta["jet_pt_titles"] = sorted(t for t in meta["jet_pt_titles"] if t)
    meta["mc_files"] = dict(meta["mc_files"])
    meta["sigma_w_subset"] = dict(meta["sigma_w_subset"])
    return data, mc, mc_sum, dict(gen), dict(gen_sumw), meta


def shape_factor(data, mc_sum, channel, key="delivered_light"):
    """One number per channel: the MC rescale that matches the inclusive
    Z-window yield of this data subset."""
    d = data[channel][key]["w"].sum()
    m = mc_sum[channel][key]["w"].sum()
    return float(d / m) if m else float("nan")


def ratio_with_error(data_block, mc_block, factor):
    """data / (factor x MC) per bin, with the combined statistical error."""
    d = np.asarray(data_block["w"], dtype=np.float64)
    d_raw = np.asarray(data_block["raw"], dtype=np.float64)
    m = np.asarray(mc_block["w"], dtype=np.float64) * factor
    m2 = np.asarray(mc_block["w2"], dtype=np.float64) * factor ** 2
    with np.errstate(divide="ignore", invalid="ignore"):
        ratio = np.where(m > 0, d / m, np.nan)
        rel = np.sqrt(np.where(d_raw > 0, 1.0 / d_raw, 0.0)
                      + np.where(m > 0, m2 / m ** 2, 0.0))
    return ratio, ratio * rel


def explained_fraction(ratio_before, ratio_after, error_before):
    """What share of the excess a correction removes.

    Both ratios share the same data numerator, so the correction factor is
    a pure MC quantity measured on the same events; its own statistical
    error is far smaller than the data's and is not propagated. The quoted
    uncertainty is the one from the measured excess itself.
    """
    excess = ratio_before - 1.0
    with np.errstate(divide="ignore", invalid="ignore"):
        fraction = np.where(np.abs(excess) > 1e-9,
                            (ratio_before - ratio_after) / excess, np.nan)
        # d(fraction)/d(ratio_before) at fixed ratio_after
        slope = np.where(np.abs(excess) > 1e-9,
                         (ratio_after - 1.0) / excess ** 2, np.nan)
    return fraction, np.abs(slope) * error_before


def table(rows, headers):
    widths = [max(len(str(h)), max((len(str(r[i])) for r in rows), default=0))
              for i, h in enumerate(headers)]
    line = "  ".join(str(h).rjust(w) for h, w in zip(headers, widths))
    out = [line, "-" * len(line)]
    for row in rows:
        out.append("  ".join(str(c).rjust(w) for c, w in zip(row, widths)))
    return "\n".join(out)


def fmt(value, digits=3):
    if value is None or (isinstance(value, float) and not np.isfinite(value)):
        return "-"
    return "{:.{}f}".format(value, digits)


# ---------------------------------------------------------------- plots
def plot_b1_b2(data, mc_sum, factors, out_dir, results):
    """B1 and B2: the ratio under each jet definition."""
    keys = [("delivered_light", "delivered light jets (P3)"),
            ("delivered_all", "delivered jets, b counted in"),
            ("paperlike", "paper-like jets, our Z"),
            ("paperlike_paperZ", "paper-like jets, paper Z")]
    fig, axes = plt.subplots(1, 2, figsize=(13, 5), sharey=True)
    x = np.arange(len(NJET_LABELS))
    for ax, channel in zip(axes, CHANNELS):
        for key, label in keys:
            if key not in data[channel] or key not in mc_sum[channel]:
                continue
            ratio, err = ratio_with_error(data[channel][key],
                                          mc_sum[channel][key],
                                          factors[channel])
            ax.errorbar(x, ratio, yerr=err, marker="o", capsize=3, label=label)
            results.setdefault(channel, {})[key] = {
                "ratio": ratio.tolist(), "error": err.tolist(),
                "data_raw": np.asarray(data[channel][key]["raw"]).tolist(),
            }
        ax.axhline(1.0, color="k", lw=1)
        ax.set_xticks(x)
        ax.set_xticklabels(NJET_LABELS)
        ax.set_xlabel("jets")
        ax.set_title("{} Z events, 76-106 GeV".format(CHANNEL_TITLE[channel]))
        ax.grid(alpha=0.3)
    axes[0].set_ylabel("data / simulation (shape normalised)")
    axes[0].legend(fontsize=8)
    fig.suptitle("B1/B2: the excess under four jet definitions")
    fig.tight_layout()
    path = out_dir / "B1_B2_jet_definitions.png"
    fig.savefig(path, dpi=140)
    plt.close(fig)
    return path


def plot_b3(results, reference, out_dir):
    """B3: ours vs the published data/prediction, side by side."""
    published = reference["data_over_prediction"][
        "MG5_aMC NLO FxFx (<=2j NLO + PS)"]
    pub = [published[str(n)] for n in range(6)]
    fig, axes = plt.subplots(1, 2, figsize=(13, 5), sharey=True)
    x = np.arange(len(NJET_LABELS))
    for ax, channel in zip(axes, CHANNELS):
        block = results[channel]
        for key, label, style in (
                ("delivered_light", "ours, delivered light jets", "o-"),
                ("paperlike_paperZ", "ours, paper-like", "s-")):
            if key not in block:
                continue
            ax.errorbar(x, block[key]["ratio"], yerr=block[key]["error"],
                        fmt=style, capsize=3, label=label)
        ax.plot(x, pub, "^--", color="k",
                label="published, data / MG5_aMC NLO\n(particle level, read "
                      "off Fig. 4a)")
        ax.axhline(1.0, color="k", lw=1)
        ax.set_xticks(x)
        ax.set_xticklabels(NJET_LABELS)
        ax.set_xlabel("jets  (ours: 5+ is inclusive; published: =5)")
        ax.set_title(CHANNEL_TITLE[channel])
        ax.grid(alpha=0.3)
    axes[0].set_ylabel("data / prediction")
    axes[0].legend(fontsize=8)
    fig.suptitle("B3: our detector-level ratio against the published "
                 "particle-level one")
    fig.tight_layout()
    path = out_dir / "B3_vs_published.png"
    fig.savefig(path, dpi=140)
    plt.close(fig)
    return path


def plot_c1_c2(data, mc_sum, factors, out_dir, results):
    """C1 the JER effect, C2 the JES scan."""
    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    x = np.arange(len(NJET_LABELS))

    ax = axes[0]
    for channel, colour in zip(CHANNELS, ("tab:blue", "tab:red")):
        for key, suffix, style in (("paperlike", "", "o-"),
                                   ("paperlike_jer", "_jer", "s--")):
            if key not in mc_sum[channel]:
                continue
            ratio, err = ratio_with_error(
                data[channel]["paperlike"], mc_sum[channel][key],
                factors[channel])
            ax.errorbar(x, ratio, yerr=err, fmt=style, color=colour,
                        capsize=3,
                        label="{} {}".format(CHANNEL_TITLE[channel],
                                             "with JER" if suffix else "as is"))
            results.setdefault(channel, {})[key] = {
                "ratio": ratio.tolist(), "error": err.tolist()}
    ax.axhline(1.0, color="k", lw=1)
    ax.set_xticks(x)
    ax.set_xticklabels(NJET_LABELS)
    ax.set_xlabel("jets")
    ax.set_ylabel("data / simulation")
    ax.set_title("C1: official JER smearing applied to simulation")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)

    ax = axes[1]
    shifts, curves = [], {}
    for channel in CHANNELS:
        keys = sorted((k for k in mc_sum[channel] if k.startswith("paperlike_jes_")),
                      key=lambda s: float(s.rsplit("_", 1)[1]))
        shifts = [float(k.rsplit("_", 1)[1]) for k in keys]
        series = {n: [] for n in (2, 3, 4)}
        for key in keys:
            ratio, _ = ratio_with_error(data[channel]["paperlike"],
                                        mc_sum[channel][key], factors[channel])
            for n in series:
                series[n].append(ratio[n])
        base, _ = ratio_with_error(data[channel]["paperlike"],
                                   mc_sum[channel]["paperlike"],
                                   factors[channel])
        for n in series:
            full_x = shifts + [0.0]
            full_y = series[n] + [base[n]]
            order = np.argsort(full_x)
            ax.plot(np.array(full_x)[order] * 100, np.array(full_y)[order],
                    marker="o", ls="-" if channel == "mumu" else "--",
                    label="{} {} jets".format(CHANNEL_TITLE[channel], n))
        curves[channel] = {"shifts": shifts,
                           "ratios": {str(n): series[n] for n in series},
                           "baseline": base.tolist()}
    ax.axhline(1.0, color="k", lw=1)
    ax.axvline(0.0, color="k", lw=0.8, ls=":")
    ax.set_xlabel("jet energy scale shift applied to simulation [%]")
    ax.set_ylabel("data / simulation")
    ax.set_title("C2: how big a scale shift would close the gap")
    ax.legend(fontsize=7, ncol=2)
    ax.grid(alpha=0.3)
    results["jes_scan"] = curves

    fig.tight_layout()
    path = out_dir / "C1_C2_jer_jes.png"
    fig.savefig(path, dpi=140)
    plt.close(fig)
    return path


def normalised(values):
    values = np.asarray(values, dtype=np.float64)
    total = values.sum()
    return values / total if total else values


def plot_c3(data, mc_sum, edges, out_dir, results):
    """C3: do the extra jets in data look like the ones in simulation?"""
    panels = [("xjet_pt", "xjet_pt", r"3rd+ jet $p_T$ [GeV]"),
              ("xjet_eta", "xjet_eta", r"3rd+ jet $\eta$"),
              ("xjet_phi", "xjet_phi", r"3rd+ jet $\phi$"),
              ("xjet_chHEF", "fraction", "charged hadron fraction"),
              ("xjet_neHEF", "fraction", "neutral hadron fraction"),
              ("xjet_emfrac", "fraction", "total EM fraction")]
    fig, axes = plt.subplots(2, 3, figsize=(16, 8))
    stored = {}
    for ax, (key, edge_name, xlabel) in zip(axes.ravel(), panels):
        channel = "mumu"
        if key not in data[channel] or key not in mc_sum[channel]:
            ax.set_visible(False)
            continue
        bins = np.asarray(edges[edge_name], dtype=np.float64)
        centres = 0.5 * (bins[:-1] + bins[1:])
        d = normalised(data[channel][key])
        m = normalised(mc_sum[channel][key])
        ax.step(centres, d, where="mid", label="data")
        ax.step(centres, m, where="mid", label="simulation")
        ax.set_xlabel(xlabel)
        ax.set_ylabel("fraction of jets")
        ax.legend(fontsize=8)
        ax.grid(alpha=0.3)
        stored[key] = {"data": d.tolist(), "mc": m.tolist(),
                       "edges": bins.tolist()}
    fig.suptitle(r"C3: the 3rd-and-later jets in $\mu\mu$ Z events, shape "
                 "normalised")
    fig.tight_layout()
    path = out_dir / "C3_extra_jet_shapes.png"
    fig.savefig(path, dpi=140)
    plt.close(fig)
    results["c3_shapes"] = stored
    return path


def plot_c3_occupancy(data, mc_sum, edges, out_dir, results):
    """C3: the detector map, looking for a hot spot in data."""
    key = "xjet_occupancy_raw"
    if key not in data["mumu"]:
        return None
    eta = np.asarray(edges["xjet_occ_eta"])
    phi = np.asarray(edges["xjet_occ_phi"])
    d = np.asarray(data["mumu"][key], dtype=np.float64)
    m = np.asarray(mc_sum["mumu"][key], dtype=np.float64)
    dn = d / d.sum() if d.sum() else d
    mn = m / m.sum() if m.sum() else m
    with np.errstate(divide="ignore", invalid="ignore"):
        rel = np.where(mn > 0, dn / mn, np.nan)

    fig, axes = plt.subplots(1, 3, figsize=(17, 4.6))
    for ax, grid, title in ((axes[0], dn, "data"), (axes[1], mn, "simulation")):
        im = ax.pcolormesh(eta, phi, grid.T, shading="auto")
        fig.colorbar(im, ax=ax)
        ax.set_title("{} occupancy (fraction per cell)".format(title))
        ax.set_xlabel(r"$\eta$")
        ax.set_ylabel(r"$\phi$")
    im = axes[2].pcolormesh(eta, phi, rel.T, shading="auto", cmap="coolwarm",
                            vmin=0.5, vmax=1.5)
    fig.colorbar(im, ax=axes[2])
    axes[2].set_title("data / simulation")
    axes[2].set_xlabel(r"$\eta$")
    axes[2].set_ylabel(r"$\phi$")
    fig.suptitle(r"C3: where the 3rd-and-later jets sit, $\mu\mu$ Z events")
    fig.tight_layout()
    path = out_dir / "C3_occupancy.png"
    fig.savefig(path, dpi=140)
    plt.close(fig)

    finite = rel[np.isfinite(rel)]
    results["c3_occupancy"] = {
        "n_cells": int(finite.size),
        "max_data_over_mc": float(finite.max()) if finite.size else None,
        "min_data_over_mc": float(finite.min()) if finite.size else None,
        "fraction_of_cells_above_1p5": float((finite > 1.5).mean())
        if finite.size else None,
        "data_jets_raw": float(d.sum()), "mc_jets_raw": float(m.sum()),
    }
    return path


def plot_c4(data, mc_sum, edges, out_dir, results):
    """C4: are the extra jets really leptons or photons?"""
    fig, axes = plt.subplots(1, 3, figsize=(16, 4.6))
    bins = np.asarray(edges["dr"])
    centres = 0.5 * (bins[:-1] + bins[1:])
    for ax, key, title in (
            (axes[0], "xjet_dr_sel_lepton", "to the nearest selected lepton"),
            (axes[1], "xjet_dr_any_lepton", "to ANY lepton, no ID at all"),
            (axes[2], "xjet_dr_photon", "to the nearest photon")):
        channel = "mumu"
        if key not in data[channel] or key not in mc_sum[channel]:
            ax.set_visible(False)
            continue
        d = normalised(data[channel][key])
        m = normalised(mc_sum[channel][key])
        ax.step(centres, d, where="mid", label="data")
        ax.step(centres, m, where="mid", label="simulation")
        ax.set_xlabel(r"$\Delta R$ " + title)
        ax.set_ylabel("fraction of jets")
        ax.set_yscale("log")
        ax.legend(fontsize=8)
        ax.grid(alpha=0.3)
    fig.suptitle(r"C4: how close the 3rd-and-later jets are to leptons and "
                 r"photons, $\mu\mu$ Z events")
    fig.tight_layout()
    path = out_dir / "C4_lepton_photon.png"
    fig.savefig(path, dpi=140)
    plt.close(fig)

    summary = {}
    for channel in CHANNELS:
        if "xjet_n_raw" not in data[channel]:
            continue
        block = {}
        for name in ("xjet_n_fail_tightlepveto", "xjet_n_highEM"):
            for source, store in (("data", data), ("mc", mc_sum)):
                total = store[channel].get("xjet_n", 0.0)
                block["{}_{}".format(name, source)] = (
                    float(store[channel].get(name, 0.0) / total)
                    if total else None)
        for name in ("xjet_nMuons", "xjet_nElectrons"):
            for source, store in (("data", data), ("mc", mc_sum)):
                counts = np.asarray(store[channel].get(name, [0.0]),
                                    dtype=np.float64)
                block["{}_ge1_{}".format(name, source)] = (
                    float(counts[1:].sum() / counts.sum())
                    if counts.sum() else None)
        block["xjet_n_raw_data"] = float(data[channel]["xjet_n_raw"])
        block["xjet_n_raw_mc"] = float(mc_sum[channel]["xjet_n_raw"])
        summary[channel] = block
    results["c4_summary"] = summary
    return path


def plot_c5(gen, gen_sumw, registry, reference, out_dir, results):
    """C5: our own sample's particle-level cross section against the
    published measurement, absolutely, in pb."""
    dy = "35669"
    if dy not in gen:
        return None
    sigma = float(registry["records"][dy]["cross_section_pb"])
    total = gen_sumw[dy]
    measured = [reference["exclusive_sigma_pb"][str(n)]["sigma"]
                for n in range(6)]
    measured_err = [reference["exclusive_sigma_pb"][str(n)]["total_unc"]
                    for n in range(6)]
    # the 5+ bin of ours is inclusive, so compare it with the sum of the
    # published 5..8 bins rather than with the published 5-jet bin alone
    measured[5] = sum(reference["exclusive_sigma_pb"][str(n)]["sigma"]
                      for n in range(5, 9))
    measured_err[5] = sum(
        reference["exclusive_sigma_pb"][str(n)]["total_unc"] ** 2
        for n in range(5, 9)) ** 0.5

    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    stored = {}
    x = np.arange(len(NJET_LABELS))
    for channel, style in (("mumu", "o-"), ("ee", "s--")):
        if channel not in gen[dy]:
            continue
        counts = np.asarray(gen[dy][channel]["w"], dtype=np.float64)
        w2 = np.asarray(gen[dy][channel]["w2"], dtype=np.float64)
        prediction = sigma * counts / total
        error = sigma * np.sqrt(w2) / total
        axes[0].errorbar(x, prediction, yerr=error, fmt=style,
                         label="ours, {} (DY FxFx)".format(CHANNEL_TITLE[channel]))
        with np.errstate(divide="ignore", invalid="ignore"):
            ratio = prediction / np.asarray(measured)
            ratio_err = error / np.asarray(measured)
        axes[1].errorbar(x, ratio, yerr=ratio_err, fmt=style,
                         label="ours / measured, {}".format(CHANNEL_TITLE[channel]))
        stored[channel] = {
            "sigma_pb": prediction.tolist(), "error_pb": error.tolist(),
            "ratio_to_measured": ratio.tolist(),
            "ratio_error": ratio_err.tolist(),
            "n_raw": int(gen[dy].get(channel + "_n_raw", 0)),
        }
    axes[0].errorbar(x, measured, yerr=measured_err, fmt="^k",
                     label="CMS-SMP-19-009 measurement")
    axes[0].set_yscale("log")
    axes[0].set_xticks(x)
    axes[0].set_xticklabels(NJET_LABELS)
    axes[0].set_xlabel("jets at particle level")
    axes[0].set_ylabel(r"$\sigma$ [pb]")
    axes[0].set_title("C5: our sample's particle-level prediction, absolute")
    axes[0].legend(fontsize=8)
    axes[0].grid(alpha=0.3)

    published_ratio = reference["prediction_over_data"][
        "MG5_aMC NLO FxFx (<=2j NLO + PS)"]
    pub = [published_ratio[str(n)] for n in range(5)] + [float("nan")]
    axes[1].plot(x, pub, "^--", color="k",
                 label="published MG5_aMC NLO / measurement\n(read off Fig. 4a)")
    axes[1].axhline(1.0, color="k", lw=1)
    axes[1].set_xticks(x)
    axes[1].set_xticklabels(NJET_LABELS)
    axes[1].set_xlabel("jets at particle level")
    axes[1].set_ylabel("prediction / measurement")
    axes[1].set_title("C5: does our sample behave like the published one?")
    axes[1].legend(fontsize=8)
    axes[1].grid(alpha=0.3)

    fig.tight_layout()
    path = out_dir / "C5_generator_closure.png"
    fig.savefig(path, dpi=140)
    plt.close(fig)

    prefire = {}
    for channel in CHANNELS:
        key = channel + "_prefire"
        if key in gen[dy] and channel in gen[dy]:
            plain = np.asarray(gen[dy][channel]["w"], dtype=np.float64)
            withpf = np.asarray(gen[dy][key]["w"], dtype=np.float64)
            with np.errstate(divide="ignore", invalid="ignore"):
                prefire[channel] = np.where(plain != 0, withpf / plain,
                                            np.nan).tolist()
    results["c5"] = {
        "sample": registry["records"][dy]["physics_short"],
        "cross_section_pb": sigma,
        "sum_genweight_subset": total,
        "measured_pb": measured, "measured_unc_pb": measured_err,
        "note_5plus": "our 5+ bin is inclusive, so it is compared with the "
                      "sum of the published 5, 6, 7 and 8 jet bins",
        "channels": stored,
        "l1prefiring_ratio_per_bin": prefire,
    }
    return path


def plot_c6(mc_sum, out_dir, results):
    """C6: what reconstruction does to the generator's jets."""
    if "reco_vs_gen" not in mc_sum["mumu"]:
        return None
    matrix = np.asarray(mc_sum["mumu"]["reco_vs_gen"], dtype=np.float64)
    with np.errstate(divide="ignore", invalid="ignore"):
        by_gen = np.where(matrix.sum(axis=0) > 0,
                          matrix / matrix.sum(axis=0), np.nan)
    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    im = axes[0].imshow(matrix, origin="lower", aspect="auto",
                        norm=matplotlib.colors.SymLogNorm(linthresh=1e3))
    fig.colorbar(im, ax=axes[0])
    axes[0].set_title("C6: weighted events, reconstruction vs generator")
    im = axes[1].imshow(by_gen, origin="lower", aspect="auto", vmin=0, vmax=1)
    fig.colorbar(im, ax=axes[1])
    axes[1].set_title("column normalised: where a generator jet count lands")
    for ax in axes:
        ax.set_xlabel("generator jets")
        ax.set_ylabel("reconstructed jets")
        ax.set_xticks(range(len(NJET_LABELS)))
        ax.set_xticklabels(NJET_LABELS)
        ax.set_yticks(range(len(NJET_LABELS)))
        ax.set_yticklabels(NJET_LABELS)
    fig.suptitle(r"C6: jet migration in simulation, $\mu\mu$ Z events")
    fig.tight_layout()
    path = out_dir / "C6_migration.png"
    fig.savefig(path, dpi=140)
    plt.close(fig)
    diagonal = np.diag(by_gen)
    results["c6"] = {
        "matrix": matrix.tolist(),
        "column_normalised": np.where(np.isfinite(by_gen), by_gen,
                                      None).tolist(),
        "diagonal_purity": [None if not np.isfinite(v) else float(v)
                            for v in diagonal],
    }
    return path


BINS_OF_INTEREST = (3, 4, 5)
VERDICT_THRESHOLDS = ((0.6, "EXPLAINS"), (0.1, "CONTRIBUTES"),
                      (-1e9, "RULED OUT"))


def verdict_for(fraction, error):
    """The pre-stated wording, from the fraction of the excess removed."""
    if fraction is None or not np.isfinite(fraction):
        return "INCONCLUSIVE"
    if not np.isfinite(error):
        error = 0.0
    # a suspect that could be anything from nothing to everything has not
    # been measured well enough to judge
    if error > 0.5:
        return "INCONCLUSIVE"
    for threshold, word in VERDICT_THRESHOLDS:
        if fraction >= threshold:
            return word
    return "RULED OUT"


def part_d(results, reference, out_dir):
    """Score every suspect on the same footing: what share of the measured
    excess it removes at 3, 4 and 5+ jets.

    The excess is taken from the paper-like definition, which is the one
    closest to the published measurement.
    """
    out = {}
    for channel in CHANNELS:
        observed = np.asarray(results[channel]["paperlike"]["ratio"])
        observed_err = np.asarray(results[channel]["paperlike"]["error"])
        entry = {}

        # C1: official JER smearing
        jer = results[channel].get("paperlike_jer")
        if jer is not None:
            fraction, error = explained_fraction(
                observed, np.asarray(jer["ratio"]), observed_err)
            entry["C1_jer"] = {"fraction": fraction.tolist(),
                               "error": error.tolist()}

        # C2: the jet energy scale, expressed in units of the published
        # 1-sigma JES, so "how big a shift would be needed" becomes "how
        # many standard deviations away that is"
        scan = results["jes_scan"][channel]
        shifts = np.asarray(scan["shifts"] + [0.0], dtype=np.float64)
        order = np.argsort(shifts)
        jes = {}
        for n in BINS_OF_INTEREST:
            values = np.asarray(scan["ratios"][str(n)] + [scan["baseline"][n]],
                                dtype=np.float64)
            sx, sy = shifts[order], values[order]
            baseline = scan["baseline"][n]
            needed = results["jes_shift_needed_to_close"][channel][str(n)]
            # the shift that reproduces the published 1-sigma JES effect on
            # this bin's cross section
            published_pct = reference["exclusive_uncertainty_pct"].get(
                str(min(n, 8)), {}).get("jes")
            one_sigma = float("nan")
            if published_pct:
                target = baseline / (1.0 + published_pct / 100.0)
                if sy.min() <= target <= sy.max():
                    one_sigma = float(np.interp(target, sy[::-1], sx[::-1]))
            # what a +1 sigma JES shift alone would remove
            fraction = float("nan")
            if np.isfinite(one_sigma) and abs(observed[n] - 1.0) > 1e-9:
                moved = float(np.interp(one_sigma, sx, sy))
                fraction = (observed[n] - moved) / (observed[n] - 1.0)
            jes[str(n)] = {
                "shift_needed_to_close": needed,
                "published_one_sigma_jes_pct": published_pct,
                "shift_equivalent_to_one_sigma": one_sigma,
                "needed_in_sigma": (needed / one_sigma
                                    if np.isfinite(one_sigma) and one_sigma
                                    else float("nan")),
                "fraction_explained_by_one_sigma": fraction,
            }
        entry["C2_jes"] = jes

        # C5: our own sample's particle-level deficit against the published
        # measurement. Correcting the simulation to the measured particle-
        # level cross section is the single most direct test there is.
        c5 = results.get("c5", {}).get("channels", {}).get(channel)
        if c5 is not None:
            closure = np.asarray(c5["ratio_to_measured"], dtype=np.float64)
            closure_err = np.asarray(c5["ratio_error"], dtype=np.float64)
            measured_rel = np.asarray(
                results["c5"]["measured_unc_pb"], dtype=np.float64) / np.asarray(
                    results["c5"]["measured_pb"], dtype=np.float64)
            total_rel = np.sqrt((closure_err / closure) ** 2 + measured_rel ** 2)
            residual = observed * closure
            residual_err = residual * np.sqrt(
                (observed_err / observed) ** 2 + total_rel ** 2)
            fraction, error = explained_fraction(observed, residual,
                                                 observed_err)
            # the generator closure carries its own uncertainty into the
            # fraction as well, so add it rather than quoting the data-only
            # piece on its own
            with np.errstate(divide="ignore", invalid="ignore"):
                extra = np.where(np.abs(observed - 1.0) > 1e-9,
                                 observed * total_rel / np.abs(observed - 1.0),
                                 np.nan)
            entry["C5_generator"] = {
                "closure": closure.tolist(),
                "closure_total_rel_error": total_rel.tolist(),
                "residual_ratio": residual.tolist(),
                "residual_error": residual_err.tolist(),
                "fraction": fraction.tolist(),
                "error": np.sqrt(error ** 2 + np.nan_to_num(extra) ** 2).tolist(),
            }
        out[channel] = entry

    # C3 and C4 are rate statements, not corrections: the most they could
    # contribute is the data-minus-simulation difference in the fake-like
    # fraction of the extra jets.
    c4 = results.get("c4_summary", {})
    for channel in CHANNELS:
        if channel not in c4:
            continue
        block = c4[channel]
        ceilings = {}
        for name in ("xjet_n_fail_tightlepveto", "xjet_n_highEM"):
            data_f = block.get(name + "_data")
            mc_f = block.get(name + "_mc")
            if data_f is None or mc_f is None:
                continue
            ceilings[name] = {"data": data_f, "mc": mc_f,
                              "data_minus_mc": data_f - mc_f}
        for name in ("xjet_nMuons", "xjet_nElectrons"):
            data_f = block.get(name + "_ge1_data")
            mc_f = block.get(name + "_ge1_mc")
            if data_f is None or mc_f is None:
                continue
            ceilings[name + "_ge1"] = {"data": data_f, "mc": mc_f,
                                       "data_minus_mc": data_f - mc_f}
        out[channel]["C4_ceiling"] = ceilings
    out["c3_occupancy"] = results.get("c3_occupancy")

    # ---- print it -----------------------------------------------------
    rows = []
    for channel in CHANNELS:
        entry = out[channel]
        for n in BINS_OF_INTEREST:
            label = NJET_LABELS[n]
            observed = results[channel]["paperlike"]["ratio"][n]
            row = [CHANNEL_TITLE[channel], label, fmt(observed)]
            jer = entry.get("C1_jer")
            row.append("{}%".format(fmt(100 * jer["fraction"][n], 1))
                       if jer else "-")
            jes = entry["C2_jes"][str(n)]
            row.append("{} sigma".format(fmt(jes["needed_in_sigma"], 1)))
            gen = entry.get("C5_generator")
            if gen:
                row.append("{} +- {}%".format(fmt(100 * gen["fraction"][n], 0),
                                              fmt(100 * gen["error"][n], 0)))
                row.append(fmt(gen["residual_ratio"][n]))
            else:
                row += ["-", "-"]
            rows.append(row)
    print(table(rows, ["channel", "jets", "data/MC", "C1 JER removes",
                       "C2 JES needed", "C5 generator removes",
                       "residual after C5"]))

    print("\nverdicts")
    vrows = []
    for channel in CHANNELS:
        entry = out[channel]
        for name, key in (("C1 jet energy resolution", "C1_jer"),
                          ("C5 generator modelling", "C5_generator")):
            block = entry.get(key)
            if not block:
                continue
            fractions = [block["fraction"][n] for n in BINS_OF_INTEREST]
            errors = [block["error"][n] for n in BINS_OF_INTEREST]
            mean_fraction = float(np.nanmean(fractions))
            mean_error = float(np.nanmean(errors))
            word = verdict_for(mean_fraction, mean_error)
            entry[key]["verdict"] = word
            entry[key]["mean_fraction_3to5"] = mean_fraction
            vrows.append([CHANNEL_TITLE[channel], name,
                          "{}%".format(fmt(100 * mean_fraction, 0)), word])
        needed = [entry["C2_jes"][str(n)]["needed_in_sigma"]
                  for n in BINS_OF_INTEREST]
        finite = [v for v in needed if np.isfinite(v)]
        word = "RULED OUT" if (finite and min(finite) > 3.0) else "INCONCLUSIVE"
        entry["C2_jes"]["verdict"] = word
        vrows.append([CHANNEL_TITLE[channel], "C2 jet energy scale",
                      "needs {}+ sigma".format(fmt(min(finite), 1))
                      if finite else "cannot reach 1", word])
    print(table(vrows, ["channel", "suspect", "size", "verdict"]))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--probe-dir", required=True)
    ap.add_argument("--registry", required=True)
    ap.add_argument("--pilot-inputs", required=True)
    ap.add_argument("--hepdata", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--evidence", required=True)
    args = ap.parse_args()

    probe_dir = pathlib.Path(args.probe_dir)
    out_dir = pathlib.Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    registry = json.loads(pathlib.Path(args.registry).read_text(encoding="utf-8"))
    inputs = json.loads(pathlib.Path(args.pilot_inputs).read_text(encoding="utf-8"))
    reference = json.loads(pathlib.Path(args.hepdata).read_text(encoding="utf-8"))

    data, mc, mc_sum, gen, gen_sumw, meta = merge(probe_dir, registry, inputs)
    factors = {ch: shape_factor(data, mc_sum, ch) for ch in CHANNELS}

    print("merged {} probe files: {} data, {} MC".format(
        meta["probe_files"], meta["data_files"], sum(meta["mc_files"].values())))
    print("events read: {:,}".format(meta["n_read"]))
    for channel in CHANNELS:
        print("  {}: {:,} data Z events, MC rescale factor {:.4f}".format(
            channel, int(data[channel]["delivered_light"]["raw"].sum()),
            factors[channel]))
    print("Jet_pt branch title     : {}".format(meta["jet_pt_titles"]))
    print("Jet_rawFactor title     : {}".format(meta["raw_factor_titles"]))
    print("Jet_jetId title         : {}".format(meta["jet_id_titles"]))

    results = {ch: {} for ch in CHANNELS}
    plots = {}
    plots["B1_B2"] = str(plot_b1_b2(data, mc_sum, factors, out_dir, results))
    plots["B3"] = str(plot_b3(results, reference, out_dir))
    plots["C1_C2"] = str(plot_c1_c2(data, mc_sum, factors, out_dir, results))

    edges = None
    for path in sorted(probe_dir.glob("*.json")):
        if not path.name.startswith("smoke_"):
            edges = json.loads(path.read_text(encoding="utf-8"))["edges"]
            break
    plots["C3"] = str(plot_c3(data, mc_sum, edges, out_dir, results))
    occupancy = plot_c3_occupancy(data, mc_sum, edges, out_dir, results)
    if occupancy:
        plots["C3_occupancy"] = str(occupancy)
    plots["C4"] = str(plot_c4(data, mc_sum, edges, out_dir, results))
    c5 = plot_c5(gen, gen_sumw, registry, reference, out_dir, results)
    if c5:
        plots["C5"] = str(c5)
    c6 = plot_c6(mc_sum, out_dir, results)
    if c6:
        plots["C6"] = str(c6)

    # ---- the tables ---------------------------------------------------
    print("\n=== B1/B2: data/simulation per jet bin, by definition ===")
    for channel in CHANNELS:
        rows = []
        for key in ("delivered_light", "delivered_all", "paperlike",
                    "paperlike_paperZ"):
            if key not in results[channel]:
                continue
            block = results[channel][key]
            rows.append([key] + ["{} +- {}".format(fmt(r), fmt(e, 3))
                                 for r, e in zip(block["ratio"], block["error"])])
        print("\n{}".format(CHANNEL_TITLE[channel]))
        print(table(rows, ["definition"] + NJET_LABELS))

    print("\n=== B3: ours against the published ratio ===")
    published = reference["data_over_prediction"][
        "MG5_aMC NLO FxFx (<=2j NLO + PS)"]
    rows = []
    for n, label in enumerate(NJET_LABELS):
        row = [label]
        for channel in CHANNELS:
            for key in ("delivered_light", "paperlike_paperZ"):
                block = results[channel].get(key)
                row.append("{} +- {}".format(fmt(block["ratio"][n]),
                                             fmt(block["error"][n]))
                           if block else "-")
        row.append(fmt(published[str(n)]) if str(n) in published else "-")
        rows.append(row)
    print(table(rows, ["jets", "mumu delivered", "mumu paper-like",
                       "ee delivered", "ee paper-like",
                       "published data/NLO"]))
    results["b3_published_data_over_nlo"] = {
        str(n): published[str(n)] for n in range(6) if str(n) in published}

    print("\n=== C1: what official JER smearing removes ===")
    rows = []
    for channel in CHANNELS:
        before = np.asarray(results[channel]["paperlike"]["ratio"])
        err = np.asarray(results[channel]["paperlike"]["error"])
        after_block = results[channel].get("paperlike_jer")
        if after_block is None:
            continue
        after = np.asarray(after_block["ratio"])
        fraction, fraction_err = explained_fraction(before, after, err)
        results[channel]["c1_explained_fraction"] = {
            "fraction": fraction.tolist(), "error": fraction_err.tolist()}
        # "what share of the excess it removes" is meaningless where there
        # is no excess to remove, so the percentage is only printed where
        # the ratio is more than 5% away from one.
        cells = []
        for b, a, f in zip(before, after, fraction):
            share = ("({}%)".format(fmt(100 * f, 1)) if abs(b - 1.0) > 0.05
                     else "(no excess)")
            cells.append("{} -> {}  {}".format(fmt(b), fmt(a), share))
        rows.append([CHANNEL_TITLE[channel]] + cells)
    print(table(rows, ["channel"] + NJET_LABELS))

    print("\n=== C2: the jet energy scale shift that would close the gap ===")
    rows = []
    jes_needed = {}
    for channel in CHANNELS:
        scan = results["jes_scan"][channel]
        shifts = np.asarray(scan["shifts"] + [0.0], dtype=np.float64)
        order = np.argsort(shifts)
        for n in (2, 3, 4):
            values = np.asarray(scan["ratios"][str(n)] + [scan["baseline"][n]],
                                dtype=np.float64)
            sx, sy = shifts[order], values[order]
            # raising the scale moves jets up past the threshold, so the
            # simulation gains events and the ratio falls: sy decreases with
            # sx. np.interp needs an increasing x, hence the reversal.
            needed = (float(np.interp(1.0, sy[::-1], sx[::-1]))
                      if sy.min() <= 1.0 <= sy.max() else float("nan"))
            jes_needed.setdefault(channel, {})[str(n)] = needed
            rows.append([CHANNEL_TITLE[channel], n,
                         fmt(scan["baseline"][n]),
                         "{}%".format(fmt(100 * needed, 1))])
    results["jes_shift_needed_to_close"] = jes_needed
    print(table(rows, ["channel", "jets", "ratio at 0 shift",
                       "shift needed to reach 1"]))

    print("\n=== D: what each suspect explains, at 3, 4 and 5+ jets ===")
    verdicts = part_d(results, reference, out_dir)
    results["part_d"] = verdicts

    print("\n=== what the simulation is made of, per jet bin "
          "(paper-like definition) ===")
    composition = {}
    for channel in CHANNELS:
        total = np.asarray(mc_sum[channel]["paperlike"]["w"], dtype=np.float64)
        rows = []
        for rid, block in sorted(mc[channel].items()):
            if "paperlike" not in block:
                continue
            part = np.asarray(block["paperlike"]["w"], dtype=np.float64)
            with np.errstate(divide="ignore", invalid="ignore"):
                share = np.where(total != 0, part / total, np.nan)
            label = registry["records"][rid]["physics_short"]
            composition.setdefault(channel, {})[rid] = {
                "label": label, "fraction": share.tolist()}
            rows.append([label] + [fmt(100 * s, 1) + "%" for s in share])
        print("\n{}".format(CHANNEL_TITLE[channel]))
        print(table(rows, ["sample"] + NJET_LABELS))
    results["mc_composition_percent"] = composition

    payload = {
        "what": "Parts B, C and D of the jet-excess study",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "normalisation": {
            "mode": "shape study; MC rescaled per channel to the data "
                    "subset's inclusive Z yield",
            "factors": factors,
            "luminosity_fb": LUMI_FB,
            "absolute_exception": "Part C5 is absolute, in pb, with no "
                                  "rescaling",
        },
        "meta": {k: v for k, v in meta.items() if k != "sigma_w_subset"},
        "sigma_w_subset": meta["sigma_w_subset"],
        "reference": reference["source"],
        "results": results,
        "plots": plots,
    }
    evidence = pathlib.Path(args.evidence)
    evidence.parent.mkdir(parents=True, exist_ok=True)
    evidence.write_text(json.dumps(payload, indent=1, default=float),
                        encoding="utf-8")
    print("\nwrote {}".format(evidence))
    for name, path in sorted(plots.items()):
        print("  {:14s} {}".format(name, path))
    return 0


if __name__ == "__main__":
    sys.exit(main())
