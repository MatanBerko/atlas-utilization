#!/usr/bin/env python
"""
Aggregate the per-file measurement JSONs into Steps 2, 3 and 4 results,
and write the PNG plots.

Reads only the per-file JSONs written by measure_per_file.py. Produces:
  evidence/step2_ele27_turnon.json      plots/step2_ele27_turnon.png
                                        plots/step2_threshold_choice.png
  evidence/step3_leg_matching.json      plots/step3_leg_matching.png
  evidence/step4_emu_overlap.json       plots/step4_emu_overlap.png

Colour: categorical slots 1-3 (blue / orange / aqua), the documented subset
that passes the all-pairs colour-vision checks; no hue is cycled, no dual
axis, a legend whenever more than one series is drawn, recessive grid.

Usage:
    python aggregate_and_plot.py --measurements <dir> --evidence <dir> --plots <dir>
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from studies.cms_datasets.electron_prep.common import clopper_pearson  # noqa: E402

C_BLUE, C_ORANGE, C_AQUA = "#2a78d6", "#eb6834", "#1baf7a"
INK, INK_2, GRID, SURFACE = "#0b0b0b", "#52514e", "#e3e2de", "#fcfcfb"
REF_GREY = "#b4b3ad"

PLATEAU_MIN_GEV = 50.0
PLATEAU_MAX_GEV = 200.0
CANDIDATE_THRESHOLDS = [25.0, 27.0, 28.0, 30.0, 32.0, 35.0]
MIN_PROBES_PER_BIN_BELOW = 500
MIN_PROBES_PT_CEILING = 60.0


def style(ax, title=None, xlabel=None, ylabel=None):
    ax.set_facecolor(SURFACE)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(GRID)
    ax.tick_params(colors=INK_2, labelsize=9, length=3, color=GRID)
    ax.grid(color=GRID, linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)
    if title:
        ax.set_title(title, color=INK, fontsize=12, loc="left", pad=10)
    if xlabel:
        ax.set_xlabel(xlabel, color=INK_2, fontsize=10)
    if ylabel:
        ax.set_ylabel(ylabel, color=INK_2, fontsize=10)


def load(meas_dir: Path):
    out = defaultdict(list)
    for f in sorted(meas_dir.glob("*.json")):
        d = json.loads(f.read_text())
        out[d["dataset"]].append(d)
    return out


def bin_centers(edges):
    e = np.asarray(edges, dtype=float)
    return 0.5 * (e[:-1] + e[1:]), e


# ---------------------------------------------------------------- Step 2
def step2(files, evidence_dir, plots_dir):
    sm = files.get("SingleMuon", [])
    se = files.get("SingleElectron", [])
    if not sm:
        print("step2: no SingleMuon files, skipping")
        return None

    edges = np.asarray(sm[0]["step2_ele27_turnon"]["bin_edges"], dtype=float)
    nb = len(edges) - 1
    regions = ("barrel", "gap", "endcap")
    variants = list(sm[0]["step2_ele27_turnon"]["variants"].keys())
    aggv = {v: {era: {r: {"num": np.zeros(nb), "den": np.zeros(nb)} for r in regions}
                for era in ("G", "H")} for v in variants}
    n_tag_events = 0
    n_probes = 0
    for d in sm:
        t = d["step2_ele27_turnon"]
        era = d["era"]
        n_tag_events += t["n_tag_events"]
        n_probes += t["n_probes"]
        for v in variants:
            for r in regions:
                br = t["variants"][v]["by_region"][r]
                aggv[v][era][r]["num"] += np.asarray(br["numerator"], dtype=float)
                aggv[v][era][r]["den"] += np.asarray(br["denominator"], dtype=float)

    # The recommendation is driven by the prompt-enriched probe, because the
    # as-specified probe convolves the trigger turn-on with the probe sample
    # rising prompt purity. Both variants are reported in full.
    MAIN = "prompt_like" if "prompt_like" in variants else variants[0]
    agg = aggv[MAIN]
    both = {r: {k: agg["G"][r][k] + agg["H"][r][k] for k in ("num", "den")} for r in regions}

    def eff(d):
        p, lo, hi = clopper_pearson(d["num"], d["den"])
        return p, lo, hi

    centers, _ = bin_centers(edges)
    plateau_mask = (centers >= PLATEAU_MIN_GEV) & (centers <= PLATEAU_MAX_GEV)

    res = {
        "what": "HLT_Ele27_WPTight_Gsf turn-on, measured on an orthogonal "
                "HLT_IsoMu24 tag in SingleMuon data",
        "tag": "event fired HLT_IsoMu24 AND has a selected muon matched (dR < 0.1) "
               "to a TrigObj id 13 with bit 2 ('Iso') and online pT >= 24 GeV",
        "probe": "every selected electron (production definition, pT > 25 GeV)",
        "pass": "HLT_Ele27_WPTight_Gsf fired AND the probe is matched (dR < 0.1) to a "
                "TrigObj id 11 with bit 2 ('1e (WPTight)')",
        "n_singlemuon_files": len(sm),
        "n_tag_events": int(n_tag_events),
        "n_probes_total": int(n_probes),
        "bin_edges": [float(x) for x in edges],
        "plateau_definition": f"mean efficiency over {PLATEAU_MIN_GEV:.0f}-{PLATEAU_MAX_GEV:.0f} GeV",
        "probe_variants_available": variants,
        "variant_used_for_recommendation": MAIN,
        "why_two_variants": (
            "The as-specified probe (every selected electron) convolves the Ele27 "
            "trigger efficiency with the prompt purity of the probe sample: in an "
            "IsoMu24-triggered sample most electrons passing the production "
            "definition are non-prompt and can never fire a WPTight single-electron "
            "trigger. The prompt_like variant adds ONLY an isolation requirement on "
            "the probe (Electron_pfRelIso03_all < 0.10); the delivered electron "
            "definition is not changed anywhere."),
        "by_region": {}, "by_era": {}, "by_variant": {}, "statistics_check": {},
    }
    _c = 0.5 * (edges[:-1] + edges[1:])
    _pl = (_c >= PLATEAU_MIN_GEV) & (_c <= PLATEAU_MAX_GEV)
    for v in variants:
        bv = {r: {k: aggv[v]["G"][r][k] + aggv[v]["H"][r][k] for k in ("num", "den")}
              for r in regions}
        res["by_variant"][v] = {}
        for r in regions:
            pv, lov, hiv = clopper_pearson(bv[r]["num"], bv[r]["den"])
            npl = bv[r]["num"][_pl].sum()
            dpl = bv[r]["den"][_pl].sum()
            res["by_variant"][v][r] = {
                "numerator": [int(x) for x in bv[r]["num"]],
                "denominator": [int(x) for x in bv[r]["den"]],
                "efficiency": [None if np.isnan(x) else float(x) for x in pv],
                "cp68_lo": [None if np.isnan(x) else float(x) for x in lov],
                "cp68_hi": [None if np.isnan(x) else float(x) for x in hiv],
                "plateau_efficiency": float(npl / dpl) if dpl > 0 else None,
                "n_probes": int(bv[r]["den"].sum()),
            }

    plateau = {}
    for r in regions:
        p, lo, hi = eff(both[r])
        num_p = both[r]["num"][plateau_mask].sum()
        den_p = both[r]["den"][plateau_mask].sum()
        pl = float(num_p / den_p) if den_p > 0 else float("nan")
        plateau[r] = pl
        res["by_region"][r] = {
            "numerator": [int(x) for x in both[r]["num"]],
            "denominator": [int(x) for x in both[r]["den"]],
            "efficiency": [None if np.isnan(x) else float(x) for x in p],
            "cp68_lo": [None if np.isnan(x) else float(x) for x in lo],
            "cp68_hi": [None if np.isnan(x) else float(x) for x in hi],
            "plateau_efficiency": pl,
            "plateau_numerator": int(num_p), "plateau_denominator": int(den_p),
        }
    for era in ("G", "H"):
        res["by_era"][era] = {}
        for r in regions:
            p, lo, hi = eff(agg[era][r])
            num_p = agg[era][r]["num"][plateau_mask].sum()
            den_p = agg[era][r]["den"][plateau_mask].sum()
            res["by_era"][era][r] = {
                "efficiency": [None if np.isnan(x) else float(x) for x in p],
                "denominator": [int(x) for x in agg[era][r]["den"]],
                "plateau_efficiency": float(num_p / den_p) if den_p > 0 else None,
            }

    # Does every bin below 60 GeV have the required number of probes?
    short = {}
    for r in ("barrel", "endcap"):
        bad = [(float(edges[i]), float(edges[i + 1]), int(both[r]["den"][i]))
               for i in range(nb)
               if centers[i] < MIN_PROBES_PT_CEILING and both[r]["den"][i] < MIN_PROBES_PER_BIN_BELOW]
        short[r] = bad
    res["statistics_check"] = {
        "requirement": f">= {MIN_PROBES_PER_BIN_BELOW} probes per bin below "
                       f"{MIN_PROBES_PT_CEILING:.0f} GeV",
        "bins_below_requirement": short,
        "met_in_barrel": len(short["barrel"]) == 0,
        "met_in_endcap": len(short["endcap"]) == 0,
    }

    # Candidate thresholds: efficiency at that pT relative to plateau.
    thr = {}
    for t in CANDIDATE_THRESHOLDS:
        i = int(np.clip(np.searchsorted(edges, t, side="right") - 1, 0, nb - 1))
        entry = {"bin_low_edge": float(edges[i]), "bin_high_edge": float(edges[i + 1])}
        for r in ("barrel", "endcap"):
            e_i = (both[r]["num"][i] / both[r]["den"][i]) if both[r]["den"][i] > 0 else float("nan")
            entry[r] = {
                "efficiency": None if np.isnan(e_i) else float(e_i),
                "relative_to_plateau": None if (np.isnan(e_i) or not plateau[r]) else float(e_i / plateau[r]),
                "n_probes_in_bin": int(both[r]["den"][i]),
            }
        thr[str(t)] = entry
    res["candidate_thresholds"] = thr

    # SingleElectron loss side.
    if se:
        n_acc = sum(d["step2_se_threshold_loss"]["n_accepted_fired_and_matched"] for d in se)
        n_fin = sum(d["step2_se_threshold_loss"]["n_accepted_with_finite_lead_pt"] for d in se)
        lost = {str(t): sum(d["step2_se_threshold_loss"]["n_accepted_lost_by_threshold"][str(t)]
                            for d in se) for t in CANDIDATE_THRESHOLDS}
        res["singleelectron_loss"] = {
            "n_singleelectron_files": len(se),
            "n_accepted_events": int(n_acc),
            "n_accepted_with_finite_leading_matched_pt": int(n_fin),
            "n_lost_by_threshold": {k: int(v) for k, v in lost.items()},
            "fraction_lost_by_threshold": {
                k: (float(v) / n_fin if n_fin else None) for k, v in lost.items()},
        }
        for t in CANDIDATE_THRESHOLDS:
            res["candidate_thresholds"][str(t)]["fraction_of_singleelectron_accepted_lost"] = (
                res["singleelectron_loss"]["fraction_lost_by_threshold"][str(t)])

    # Recommendation: lowest threshold with >= 95% of plateau in BOTH regions.
    rec = None
    for t in CANDIDATE_THRESHOLDS:
        e = res["candidate_thresholds"][str(t)]
        rb = e["barrel"]["relative_to_plateau"]
        re_ = e["endcap"]["relative_to_plateau"]
        if rb is not None and re_ is not None and rb >= 0.95 and re_ >= 0.95:
            rec = t
            break
    res["recommended_threshold_gev"] = rec
    res["recommendation_rule"] = ("lowest candidate threshold whose efficiency is >= 95% of "
                                  "the plateau in BOTH barrel and endcap")
    res["recommendation_is_the_groups_decision"] = True

    (evidence_dir / "step2_ele27_turnon.json").write_text(json.dumps(res, indent=2), encoding="utf-8")

    # --- plot: turn-on curves ---
    fig, axes = plt.subplots(1, 2, figsize=(13.5, 5.2), dpi=200)
    fig.patch.set_facecolor(SURFACE)
    for ax, (r, col) in zip(axes, (("barrel", C_BLUE), ("endcap", C_ORANGE))):
        if "all" in variants:
            ba = {k: aggv["all"]["G"][r][k] + aggv["all"]["H"][r][k] for k in ("num", "den")}
            pa, _la, _ha = eff(ba)
            ma = ba["den"] > 0
            ax.plot(centers[ma], pa[ma], "s--", ms=3.5, lw=1.1, color=REF_GREY, zorder=3,
                    label="probe = every selected electron (as specified)")
        p, lo, hi = eff(both[r])
        m = both[r]["den"] > 0
        ax.errorbar(centers[m], p[m], yerr=[p[m] - lo[m], hi[m] - p[m]],
                    fmt="o", ms=4, lw=1.4, color=col, zorder=4,
                    label=f"{r}, prompt-like probe (CP 68%)")
        ax.axhline(plateau[r], color=REF_GREY, lw=1.4, ls="--", zorder=3,
                   label=f"plateau {plateau[r]:.3f} (50-200 GeV)")
        ax.axhline(0.95 * plateau[r], color=REF_GREY, lw=1.0, ls=":", zorder=3,
                   label="95% of plateau")
        if rec:
            ax.axvline(rec, color=C_AQUA, lw=1.6, zorder=3,
                       label=f"recommended {rec:.0f} GeV")
        style(ax, title=f"Ele27_WPTight_Gsf turn-on - {r}",
              xlabel="offline electron pT [GeV]", ylabel="efficiency")
        ax.set_xlim(24, 120)
        ax.set_ylim(0, 1.05)
        ax.legend(frameon=False, fontsize=8.5, loc="lower right", labelcolor=INK_2)
    fig.suptitle("Measured on an orthogonal HLT_IsoMu24 tag in SingleMuon data "
                 f"({res['n_probes_total']} probes)", color=INK, fontsize=11, x=0.01, ha="left")
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(plots_dir / "step2_ele27_turnon.png", facecolor=SURFACE, bbox_inches="tight")
    plt.close(fig)

    # --- plot: threshold choice ---
    fig, ax = plt.subplots(figsize=(10, 5.2), dpi=200)
    fig.patch.set_facecolor(SURFACE)
    xs = np.arange(len(CANDIDATE_THRESHOLDS))
    rb = [res["candidate_thresholds"][str(t)]["barrel"]["relative_to_plateau"] or 0
          for t in CANDIDATE_THRESHOLDS]
    re_ = [res["candidate_thresholds"][str(t)]["endcap"]["relative_to_plateau"] or 0
           for t in CANDIDATE_THRESHOLDS]
    ax.bar(xs - 0.2, rb, width=0.36, color=C_BLUE, edgecolor=SURFACE, linewidth=2,
           zorder=3, label="barrel, efficiency / plateau")
    ax.bar(xs + 0.2, re_, width=0.36, color=C_ORANGE, edgecolor=SURFACE, linewidth=2,
           zorder=3, label="endcap, efficiency / plateau")
    for x, v in zip(xs - 0.2, rb):
        ax.text(x, v + 0.012, f"{v:.3f}", ha="center", fontsize=8, color=INK_2)
    for x, v in zip(xs + 0.2, re_):
        ax.text(x, v + 0.012, f"{v:.3f}", ha="center", fontsize=8, color=INK_2)
    ax.axhline(0.95, color=REF_GREY, ls="--", lw=1.4, zorder=4, label="95% of plateau")
    ax.set_xticks(xs)
    if "singleelectron_loss" in res:
        labs = [f"{t:.0f} GeV\nlose {100 * (res['singleelectron_loss']['fraction_lost_by_threshold'][str(t)] or 0):.1f}%"
                for t in CANDIDATE_THRESHOLDS]
    else:
        labs = [f"{t:.0f} GeV" for t in CANDIDATE_THRESHOLDS]
    ax.set_xticklabels(labs, fontsize=9, color=INK_2)
    style(ax, title="Candidate matched-electron pT thresholds for SingleElectron",
          ylabel="efficiency relative to plateau")
    ax.set_ylim(0, 1.12)
    ax.legend(frameon=False, fontsize=9, loc="lower right", labelcolor=INK_2)
    fig.tight_layout()
    fig.savefig(plots_dir / "step2_threshold_choice.png", facecolor=SURFACE, bbox_inches="tight")
    plt.close(fig)
    print(f"step2: {res['n_probes_total']} probes, plateau barrel="
          f"{plateau['barrel']:.4f} endcap={plateau['endcap']:.4f}, recommended={rec}")
    return res


# ---------------------------------------------------------------- Step 3
def step3(files, evidence_dir, plots_dir):
    out = {"what": "per-leg trigger-object matching efficiency for DoubleEG and "
                   "MuonEG, inside each dataset's own triggered events",
           "datasets": {}}
    series = []
    for label in ("DoubleEG", "MuonEG"):
        ds = files.get(label, [])
        if not ds:
            continue
        edges = np.asarray(ds[0]["step3_leg_matching"]["bin_edges"], dtype=float)
        nb = len(edges) - 1
        legs = defaultdict(lambda: defaultdict(lambda: {"num": np.zeros(nb), "den": np.zeros(nb)}))
        totals = defaultdict(lambda: {"n": 0, "m": 0})
        online = defaultdict(lambda: None)
        n_fired = 0
        for d in ds:
            s = d["step3_leg_matching"]
            n_fired += s["n_fired"]
            for leg, e in s["legs"].items():
                totals[leg]["n"] += e["n_objects"]
                totals[leg]["m"] += e["n_matched"]
                for r, v in e["by_region"].items():
                    legs[leg][r]["num"] += np.asarray(v["numerator"], dtype=float)
                    legs[leg][r]["den"] += np.asarray(v["denominator"], dtype=float)
                oc = np.asarray(e["matched_online_pt_hist"]["counts"], dtype=float)
                online[leg] = oc if online[leg] is None else online[leg] + oc
        census = {}
        for d in ds:
            c = d.get("bit_census")
            if not c:
                continue
            for oname, oe in c["objects"].items():
                tgt = census.setdefault(oname, {"n_objects": 0, "n_no_match": 0, "bits": {}})
                tgt["n_objects"] += oe["n_objects"]
                tgt["n_no_match"] += oe["n_with_no_matched_trigger_object"]
                for bit, be in oe["fraction_with_bit"].items():
                    b = tgt["bits"].setdefault(bit, {"meaning": be["meaning_from_branch_title"], "n": 0})
                    b["n"] += be["n"]
        for oname, tgt in census.items():
            n = tgt["n_objects"]
            tgt["fraction_with_no_matched_trigger_object"] = (tgt["n_no_match"] / n) if n else None
            for bit, b in tgt["bits"].items():
                b["fraction"] = (b["n"] / n) if n else None
        entry = {"n_files": len(ds), "n_fired_events": int(n_fired),
                 "bit_census": census,
                 "trigger_paths": ds[0]["step3_leg_matching"]["trigger_paths"],
                 "bin_edges": [float(x) for x in edges], "legs": {}}
        for leg in legs:
            le = {"n_objects": totals[leg]["n"], "n_matched": totals[leg]["m"],
                  "overall_efficiency": (totals[leg]["m"] / totals[leg]["n"]
                                         if totals[leg]["n"] else None),
                  "by_region": {},
                  "matched_online_pt_hist": {
                      "edges": ds[0]["step3_leg_matching"]["legs"][leg]["matched_online_pt_hist"]["edges"],
                      "counts": [int(x) for x in online[leg]]}}
            for r in ("barrel", "endcap", "gap"):
                if r not in legs[leg]:
                    continue
                num, den = legs[leg][r]["num"], legs[leg][r]["den"]
                p, lo, hi = clopper_pearson(num, den)
                m = den > 0
                flat_mask = m & (0.5 * (edges[:-1] + edges[1:]) >= 30)
                le["by_region"][r] = {
                    "numerator": [int(x) for x in num], "denominator": [int(x) for x in den],
                    "efficiency": [None if np.isnan(x) else float(x) for x in p],
                    "cp68_lo": [None if np.isnan(x) else float(x) for x in lo],
                    "cp68_hi": [None if np.isnan(x) else float(x) for x in hi],
                    "min_efficiency_above_30gev": (float(np.nanmin(p[flat_mask]))
                                                   if flat_mask.any() else None),
                    "efficiency_in_first_bin_25_26": (float(p[0]) if m[0] else None),
                }
                if r in ("barrel", "endcap"):
                    series.append((f"{label}: {leg} ({r})", edges, num, den))
            entry["legs"][leg] = le
        out["datasets"][label] = entry

    se = files.get("SingleElectron", [])
    if se:
        ds = se
        census = {}
        for d in ds:
            c = d.get("bit_census")
            if not c:
                continue
            for oname, oe in c["objects"].items():
                tgt = census.setdefault(oname, {"n_objects": 0, "n_no_match": 0, "bits": {}})
                tgt["n_objects"] += oe["n_objects"]
                tgt["n_no_match"] += oe["n_with_no_matched_trigger_object"]
                for bit, be in oe["fraction_with_bit"].items():
                    b = tgt["bits"].setdefault(bit, {"meaning": be["meaning_from_branch_title"], "n": 0})
                    b["n"] += be["n"]
        for oname, tgt in census.items():
            n = tgt["n_objects"]
            tgt["fraction_with_no_matched_trigger_object"] = (tgt["n_no_match"] / n) if n else None
            for bit, b in tgt["bits"].items():
                b["fraction"] = (b["n"] / n) if n else None
        out["datasets"]["SingleElectron"] = {"n_files": len(se), "bit_census": census,
                                             "legs": {}}
    (evidence_dir / "step3_leg_matching.json").write_text(json.dumps(out, indent=2), encoding="utf-8")

    if series:
        n = len(series)
        ncol = 2
        nrow = int(np.ceil(n / ncol))
        fig, axes = plt.subplots(nrow, ncol, figsize=(13.5, 3.6 * nrow), dpi=200, squeeze=False)
        fig.patch.set_facecolor(SURFACE)
        for ax, (name, edges, num, den) in zip(axes.ravel(), series):
            c, _ = bin_centers(edges)
            p, lo, hi = clopper_pearson(num, den)
            m = den > 0
            col = C_BLUE if "barrel" in name else C_ORANGE
            ax.errorbar(c[m], p[m], yerr=[p[m] - lo[m], hi[m] - p[m]], fmt="o", ms=4,
                        lw=1.3, color=col, zorder=4)
            ax.axhline(0.997, color=REF_GREY, ls="--", lw=1.2, zorder=3,
                       label="0.997 (the muon-side benchmark)")
            style(ax, title=name, xlabel="offline pT [GeV]", ylabel="matched fraction")
            ax.set_xlim(24, 120)
            ax.set_ylim(0.0, 1.05)
            ax.legend(frameon=False, fontsize=8, loc="lower right", labelcolor=INK_2)
        for ax in axes.ravel()[n:]:
            ax.axis("off")
        fig.suptitle("Step 3 - leg matching efficiency vs offline pT",
                     color=INK, fontsize=12, x=0.01, ha="left")
        fig.tight_layout(rect=(0, 0, 1, 0.97))
        fig.savefig(plots_dir / "step3_leg_matching.png", facecolor=SURFACE, bbox_inches="tight")
        plt.close(fig)
    for label, e in out["datasets"].items():
        for oname, c in e.get("bit_census", {}).items():
            top = sorted(c["bits"].items(), key=lambda kv: -kv[1]["fraction"])[:3]
            print(f"step3 {label}/{oname}: {c['n_objects']} objects, "
                  f"{100 * c['fraction_with_no_matched_trigger_object']:.1f}% unmatched; "
                  + ", ".join(f"bit {k} ({v['meaning']}) {100 * v['fraction']:.1f}%"
                              for k, v in top))
        for leg, le in e["legs"].items():
            print(f"step3 {label}/{leg}: overall matched fraction "
                  f"{le['overall_efficiency']:.5f} over {le['n_objects']} objects")
    return out


# ---------------------------------------------------------------- Step 4
def step4(files, evidence_dir, plots_dir):
    out = {"what": "electron-muon angular overlap, dR(e, mu). COUNTING ONLY - "
                   "no electron is removed anywhere.",
           "datasets": {}}
    curves = []
    for label in ("MuonEG", "SingleElectron"):
        ds = [d for d in files.get(label, []) if "step4_emu_overlap" in d]
        if not ds:
            continue
        edges = np.asarray(ds[0]["step4_emu_overlap"]["per_event_min_dr"]["edges"], dtype=float)
        nb = len(edges) - 1
        per_ev = np.zeros(nb)
        pairs = np.zeros(nb)
        n_fired = n_both = 0
        below = defaultdict(int)
        changed = defaultdict(int)
        removed = defaultdict(int)
        n_elec = 0
        for d in ds:
            s = d["step4_emu_overlap"]
            n_fired += s["n_fired"]
            n_both += s["n_events_with_e_and_mu"]
            per_ev += np.asarray(s["per_event_min_dr"]["counts"], dtype=float)
            pairs += np.asarray(s["all_pairs"]["counts"], dtype=float)
            for k, v in s["fraction_of_e_mu_events_below"].items():
                below[k] += v["n_events"]
            for k, v in s["category_change_if_removed"].items():
                changed[k] += v["n_events_changed"]
                removed[k] += v["n_electrons_removed"]
            n_elec += list(s["category_change_if_removed"].values())[0]["n_electrons_total"]
        entry = {
            "n_files": len(ds), "n_fired_events": int(n_fired),
            "n_events_with_at_least_one_e_and_one_mu": int(n_both),
            "n_selected_electrons_in_fired_events": int(n_elec),
            "per_event_min_dr": {"edges": [float(x) for x in edges],
                                 "counts": [int(x) for x in per_ev]},
            "all_pairs_dr": {"edges": [float(x) for x in edges],
                             "counts": [int(x) for x in pairs]},
            "events_below_threshold": {},
        }
        for k in sorted(below, key=float):
            entry["events_below_threshold"][k] = {
                "n_events": int(below[k]),
                "fraction_of_e_mu_events": (below[k] / n_both) if n_both else None,
                "fraction_of_fired_events": (below[k] / n_fired) if n_fired else None,
                "n_events_changing_final_state_category_if_removed": int(changed[k]),
                "fraction_of_fired_events_changing_category": (changed[k] / n_fired) if n_fired else None,
                "n_electrons_removed": int(removed[k]),
                "fraction_of_electrons_removed": (removed[k] / n_elec) if n_elec else None,
            }
        out["datasets"][label] = entry
        curves.append((label, edges, per_ev, n_both))

    (evidence_dir / "step4_emu_overlap.json").write_text(json.dumps(out, indent=2), encoding="utf-8")

    if curves:
        fig, axes = plt.subplots(1, len(curves), figsize=(6.8 * len(curves), 5.0),
                                 dpi=200, squeeze=False)
        fig.patch.set_facecolor(SURFACE)
        for ax, (label, edges, counts, n_both) in zip(axes.ravel(), curves):
            c, _ = bin_centers(edges)
            w = np.diff(edges)
            ax.bar(c, counts, width=w * 0.92, color=C_BLUE, edgecolor=SURFACE,
                   linewidth=0.6, zorder=3)
            for thr, col in ((0.02, C_ORANGE), (0.05, C_AQUA), (0.1, REF_GREY)):
                ax.axvline(thr, color=col, lw=1.6, ls="--", zorder=4, label=f"dR = {thr}")
            style(ax, title=f"{label}: smallest dR(e, mu) per event",
                  xlabel="dR(electron, muon)", ylabel="events (log scale)")
            ax.set_yscale("log")
            ax.set_xlim(0, 0.6)
            ax.legend(frameon=False, fontsize=9, labelcolor=INK_2)
            e = out["datasets"][label]["events_below_threshold"]
            txt = "\n".join(
                f"dR < {k}: {e[k]['n_events']} events "
                f"({100 * (e[k]['fraction_of_e_mu_events'] or 0):.2f}% of e+mu events)"
                for k in sorted(e, key=float))
            ax.text(0.98, 0.70, txt, transform=ax.transAxes, ha="right", va="top",
                    fontsize=8.5, color=INK_2)
        fig.suptitle("Step 4 - electron-muon overlap (counting only; nothing removed)",
                     color=INK, fontsize=12, x=0.01, ha="left")
        fig.tight_layout(rect=(0, 0, 1, 0.95))
        fig.savefig(plots_dir / "step4_emu_overlap.png", facecolor=SURFACE, bbox_inches="tight")
        plt.close(fig)
    for label, e in out["datasets"].items():
        b = e["events_below_threshold"]
        print(f"step4 {label}: {e['n_events_with_at_least_one_e_and_one_mu']} e+mu events; "
              + ", ".join(f"dR<{k}: {100 * (b[k]['fraction_of_e_mu_events'] or 0):.3f}%"
                          for k in sorted(b, key=float)))
    return out


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--measurements", required=True)
    p.add_argument("--evidence", required=True)
    p.add_argument("--plots", required=True)
    args = p.parse_args()

    meas = Path(args.measurements)
    ev = Path(args.evidence); ev.mkdir(parents=True, exist_ok=True)
    pl = Path(args.plots); pl.mkdir(parents=True, exist_ok=True)

    files = load(meas)
    print({k: len(v) for k, v in files.items()})
    step2(files, ev, pl)
    step3(files, ev, pl)
    step4(files, ev, pl)
    print("done")


if __name__ == "__main__":
    main()
