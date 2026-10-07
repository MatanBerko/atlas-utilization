#!/usr/bin/env python
"""
SingleElectron Step 1, Step B aggregation: combine the per-file Z->ee
tag-and-probe counts, compute Clopper-Pearson 68% intervals, do the
same-sign background subtraction, describe the plateau, compare against the
old orthogonal-tag measurement, and make the plots.

Usage:
    python aggregate_tnp.py --in-dir .../tnp \
        --old-json studies/cms_datasets/electron_prep/evidence/step2_ele27_turnon.json \
        --out-json evidence/stepB_tnp.json --out-plots plots
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

import numpy as np  # noqa: E402

from studies.cms_datasets.electron_prep.common import clopper_pearson  # noqa: E402
from studies.cms_datasets.singleelectron_prep.measure_singleelectron import (  # noqa: E402
    PROBE_PT_EDGES, REGIONS,
)

PLATEAU_LO, PLATEAU_HI = 45.0, 100.0
BACKGROUND_FLAG_PP = 1.0        # flag if raw and subtracted differ by > 1 pp
THRESHOLD_LINES = (27, 30, 32, 35)


def eff_ci(k, n):
    k = np.asarray(k, dtype=float)
    n = np.asarray(n, dtype=float)
    p, lo, hi = clopper_pearson(k, n)
    return p, lo, hi


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in-dir", required=True)
    ap.add_argument("--old-json", required=True)
    ap.add_argument("--out-json", required=True)
    ap.add_argument("--out-plots", required=True)
    args = ap.parse_args()

    files = sorted(Path(args.in_dir).glob("tnp_*.json"))
    if not files:
        raise SystemExit(f"no per-file results under {args.in_dir}")
    nb = len(PROBE_PT_EDGES) - 1

    tot = {s: {r: {k: np.zeros(nb, dtype=np.int64)
                   for k in ("numerator", "denominator",
                             "n_matched_any_electron_trigobj",
                             "n_matched_wptight_any_pt")}
               for r in REGIONS} for s in ("opposite_sign", "same_sign")}
    agg = {"n_read": 0, "n_after_golden_json": 0, "n_after_ele27": 0,
           "n_electrons_removed_by_overlap_removal": 0,
           "trigger_guard_violations": 0,
           "n_pairs_opposite_sign_in_window": 0, "n_pairs_same_sign_in_window": 0,
           "n_pairs_probe_shares_tag_trigobj": 0}
    cone = {"n_qualify_dr01": 0, "n_qualify_dr02": 0, "n_qualify_dr02_not_dr01": 0}
    amb = {"n_golden_events": 0, "n_ele27_fired": 0,
           "n_with_qualifying_bit2_object_pt27": 0,
           "n_qualifying_object_but_ele27_NOT_fired": 0,
           "n_qualifying_and_ele27_not_fired_but_other_wptight_fired": 0,
           "n_ele27_fired_but_no_qualifying_object": 0}
    mass = {"opposite_sign": None, "same_sign": None, "bin_edges_gev": None}
    per_file = []

    for f in files:
        d = json.loads(f.read_text(encoding="utf-8"))
        per_file.append({"era": d["era"], "file_index": d["file_index"],
                         "n_after_ele27": d.get("n_after_ele27"),
                         "elapsed_sec": d.get("elapsed_sec")})
        for k in agg:
            agg[k] += int(d.get(k, 0) if k in d else
                          d.get("tagandprobe", {}).get(k, 0))
        t = d.get("tagandprobe")
        if not t:
            continue
        for k in cone:
            cone[k] += int(t["matching_cone_crosscheck"].get(k, 0))
        for k in amb:
            amb[k] += int(d.get("bit2_ambiguity", {}).get(k, 0))
        for sign in ("opposite_sign", "same_sign"):
            for r in REGIONS:
                blk = t["counts"][sign][r]
                for k in tot[sign][r]:
                    if k in blk:
                        tot[sign][r][k] += np.asarray(blk[k], dtype=np.int64)
        mh = t.get("mass_histograms")
        if mh:
            if mass["bin_edges_gev"] is None:
                mass["bin_edges_gev"] = mh["bin_edges_gev"]
                mass["opposite_sign"] = np.asarray(mh["opposite_sign"], dtype=np.int64)
                mass["same_sign"] = np.asarray(mh["same_sign"], dtype=np.int64)
            else:
                mass["opposite_sign"] += np.asarray(mh["opposite_sign"], dtype=np.int64)
                mass["same_sign"] += np.asarray(mh["same_sign"], dtype=np.int64)

    centres = np.array([(PROBE_PT_EDGES[i] + PROBE_PT_EDGES[i + 1]) / 2 for i in range(nb)])
    results = {}
    flagged_bins = []
    for r in REGIONS:
        os_n = tot["opposite_sign"][r]["numerator"].astype(float)
        os_d = tot["opposite_sign"][r]["denominator"].astype(float)
        ss_n = tot["same_sign"][r]["numerator"].astype(float)
        ss_d = tot["same_sign"][r]["denominator"].astype(float)
        p_raw, lo_raw, hi_raw = eff_ci(os_n, os_d)
        # same-sign background subtraction, bin by bin
        sub_n = np.maximum(os_n - ss_n, 0.0)
        sub_d = np.maximum(os_d - ss_d, 0.0)
        with np.errstate(invalid="ignore", divide="ignore"):
            p_sub = np.where(sub_d > 0, sub_n / sub_d, np.nan)
        diff_pp = (p_sub - p_raw) * 100.0
        for i in range(nb):
            if os_d[i] > 0 and np.isfinite(diff_pp[i]) and abs(diff_pp[i]) > BACKGROUND_FLAG_PP:
                flagged_bins.append({
                    "region": r, "pt_lo": PROBE_PT_EDGES[i], "pt_hi": PROBE_PT_EDGES[i + 1],
                    "eff_raw": float(p_raw[i]), "eff_background_subtracted": float(p_sub[i]),
                    "difference_pp": float(diff_pp[i])})
        anyeg = tot["opposite_sign"][r]["n_matched_any_electron_trigobj"].astype(float)
        wpt = tot["opposite_sign"][r]["n_matched_wptight_any_pt"].astype(float)
        bins = []
        for i in range(nb):
            bins.append({
                "pt_lo": PROBE_PT_EDGES[i], "pt_hi": PROBE_PT_EDGES[i + 1],
                "numerator": int(os_n[i]), "denominator": int(os_d[i]),
                "eff": None if os_d[i] == 0 else float(p_raw[i]),
                "lo68": None if os_d[i] == 0 else float(lo_raw[i]),
                "hi68": None if os_d[i] == 0 else float(hi_raw[i]),
                "eff_background_subtracted": (None if not np.isfinite(p_sub[i])
                                              else float(p_sub[i])),
                "same_sign_numerator": int(ss_n[i]), "same_sign_denominator": int(ss_d[i]),
                "n_matched_any_electron_trigobj": int(anyeg[i]),
                "n_matched_wptight_any_pt": int(wpt[i]),
                "frac_any_electron_trigobj": (None if os_d[i] == 0 else float(anyeg[i] / os_d[i])),
                "frac_wptight_given_any_eg": (None if anyeg[i] == 0 else float(wpt[i] / anyeg[i])),
            })
        # plateau: bins wholly inside [45, 100]
        inside = [i for i in range(nb)
                  if PROBE_PT_EDGES[i] >= PLATEAU_LO and PROBE_PT_EDGES[i + 1] <= PLATEAU_HI]
        pn, pd = os_n[inside].sum(), os_d[inside].sum()
        pp, plo, phi = eff_ci(np.array([pn]), np.array([pd]))
        per_bin_eff = [float(p_raw[i]) for i in inside if os_d[i] > 0]
        results[r] = {
            "bins": bins,
            "plateau": {
                "definition": f"bins wholly inside {PLATEAU_LO}-{PLATEAU_HI} GeV "
                              f"({', '.join(f'{PROBE_PT_EDGES[i]:g}-{PROBE_PT_EDGES[i+1]:g}' for i in inside)})",
                "numerator": int(pn), "denominator": int(pd),
                "eff": None if pd == 0 else float(pp[0]),
                "lo68": None if pd == 0 else float(plo[0]),
                "hi68": None if pd == 0 else float(phi[0]),
                "per_bin_efficiencies": per_bin_eff,
                "spread_pp": (None if len(per_bin_eff) < 2
                              else float((max(per_bin_eff) - min(per_bin_eff)) * 100)),
                "is_flat_within_1pp": (None if len(per_bin_eff) < 2
                                       else bool((max(per_bin_eff) - min(per_bin_eff)) * 100 <= 1.0)),
            },
        }

    old = json.loads(Path(args.old_json).read_text(encoding="utf-8"))
    out = {
        "what": "Step B: Z->ee tag-and-probe efficiency for HLT_Ele27_WPTight_Gsf "
                "on SingleElectron data",
        "n_files": len(files),
        "population_totals": agg,
        "matching_cone_crosscheck": cone,
        "bit2_ambiguity": amb,
        "pt_bin_edges": PROBE_PT_EDGES,
        "plateau_window_gev": [PLATEAU_LO, PLATEAU_HI],
        "background_subtraction": {
            "method": "same-sign tag-probe pairs in the same 81-101 GeV window, "
                      "subtracted bin by bin from the opposite-sign numerator and "
                      "denominator",
            "flag_threshold_pp": BACKGROUND_FLAG_PP,
            "n_bins_differing_by_more_than_1pp": len(flagged_bins),
            "flagged_bins": flagged_bins,
        },
        "results": results,
        "mass_histograms": {
            "bin_edges_gev": mass["bin_edges_gev"],
            "opposite_sign": None if mass["opposite_sign"] is None else mass["opposite_sign"].tolist(),
            "same_sign": None if mass["same_sign"] is None else mass["same_sign"].tolist(),
        },
        "old_measurement_reference": {
            "file": str(args.old_json),
            "what": old.get("what"), "pass": old.get("pass"),
            "n_probes_total": old.get("n_probes_total"),
        },
        "per_file": per_file,
    }
    Path(args.out_json).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out_json).write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"wrote {args.out_json}")

    for r in REGIONS:
        pl = results[r]["plateau"]
        print(f"  {r:7s} plateau {pl['eff']} [{pl['lo68']},{pl['hi68']}] "
              f"n={pl['numerator']}/{pl['denominator']} spread={pl['spread_pp']} pp")
    print(f"  background-subtraction bins differing >1pp: {len(flagged_bins)}")

    make_plots(out, old, Path(args.out_plots))


def make_plots(out, old, out_dir: Path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    out_dir.mkdir(parents=True, exist_ok=True)
    edges = out["pt_bin_edges"]
    centres = [(edges[i] + edges[i + 1]) / 2 for i in range(len(edges) - 1)]
    widths = [(edges[i + 1] - edges[i]) / 2 for i in range(len(edges) - 1)]

    old_edges = old["bin_edges"]
    old_centres = [(old_edges[i] + old_edges[i + 1]) / 2 for i in range(len(old_edges) - 1)]

    fig, axes = plt.subplots(1, 3, figsize=(15.5, 4.8), sharey=True)
    for ax, r in zip(axes, REGIONS):
        bins = out["results"][r]["bins"]
        xs, ys, lo, hi, xe = [], [], [], [], []
        for b, c, w in zip(bins, centres, widths):
            if b["denominator"] == 0:
                continue
            xs.append(c); ys.append(b["eff"])
            lo.append(b["eff"] - b["lo68"]); hi.append(b["hi68"] - b["eff"]); xe.append(w)
        if xs:
            ax.errorbar(xs, ys, yerr=[lo, hi], xerr=xe, fmt="o", ms=3.5, lw=1.1,
                        capsize=0, color="C0",
                        label="new: Z$\\to$ee tag and probe")
        for variant, colour, style in (("all", "darkorange", "--"),
                                       ("prompt_like", "seagreen", ":")):
            blk = old.get("by_variant", {}).get(variant, {}).get(r)
            if not blk:
                continue
            e = blk["efficiency"]
            n = min(len(e), len(old_centres))
            ax.plot(old_centres[:n], e[:n], style, color=colour, lw=1.4,
                    label=f"old (orthogonal muon tag): {variant}")
        for t in THRESHOLD_LINES:
            ax.axvline(t, color="grey", ls="-", lw=0.7, alpha=0.6)
        ax.set_title(r, fontsize=10)
        ax.set_xlabel("probe electron offline $p_T$ [GeV]", fontsize=9)
        ax.set_xscale("log")
        ax.set_xticks([25, 30, 35, 40, 50, 70, 100, 200])
        ax.get_xaxis().set_major_formatter(matplotlib.ticker.ScalarFormatter())
        ax.set_ylim(0, 1.05)
        ax.grid(alpha=0.3)
        ax.tick_params(labelsize=8)
    axes[0].set_ylabel("efficiency", fontsize=9)
    axes[0].legend(fontsize=7.5, loc="lower right")
    fig.suptitle("HLT_Ele27_WPTight_Gsf efficiency for our offline electrons\n"
                 "new Z$\\to$ee tag and probe vs the old orthogonal-muon-tag "
                 "measurement; grey lines at 27, 30, 32, 35 GeV", fontsize=10)
    fig.tight_layout(rect=(0, 0, 1, 0.9))
    fig.savefig(out_dir / "stepB_efficiency_new_vs_old.png", dpi=140)
    plt.close(fig)
    print(f"wrote {out_dir / 'stepB_efficiency_new_vs_old.png'}")

    mh = out["mass_histograms"]
    if mh["bin_edges_gev"]:
        e = np.asarray(mh["bin_edges_gev"], dtype=float)
        c = 0.5 * (e[:-1] + e[1:])
        fig, ax = plt.subplots(figsize=(7.6, 4.4))
        ax.step(c, mh["opposite_sign"], where="mid", lw=1.3, color="C0",
                label=f"opposite sign ({sum(mh['opposite_sign']):,} pairs)")
        ax.step(c, mh["same_sign"], where="mid", lw=1.3, color="crimson",
                label=f"same sign ({sum(mh['same_sign']):,} pairs)")
        ax.axvline(81, color="grey", ls="--", lw=1)
        ax.axvline(101, color="grey", ls="--", lw=1, label="81-101 GeV window")
        ax.set_yscale("log")
        ax.set_xlabel("m(tag, probe) [GeV]")
        ax.set_ylabel("pairs")
        ax.set_title("Tag-probe pair mass: the Z peak, and the same-sign pairs\n"
                     "used to estimate the background under it")
        ax.legend(fontsize=8)
        ax.grid(alpha=0.3)
        fig.tight_layout()
        fig.savefig(out_dir / "stepB_tagprobe_mass.png", dpi=140)
        plt.close(fig)
        print(f"wrote {out_dir / 'stepB_tagprobe_mass.png'}")

    # where the inefficiency comes from
    fig, axes = plt.subplots(1, 3, figsize=(15.5, 4.4), sharey=True)
    for ax, r in zip(axes, REGIONS):
        bins = out["results"][r]["bins"]
        xs = [c for b, c in zip(bins, centres) if b["denominator"] > 0]
        f_any = [b["frac_any_electron_trigobj"] for b in bins if b["denominator"] > 0]
        f_wpt = [b["frac_wptight_given_any_eg"] for b in bins if b["denominator"] > 0]
        f_eff = [b["eff"] for b in bins if b["denominator"] > 0]
        ax.plot(xs, f_any, "o-", ms=3, lw=1.1, color="seagreen",
                label="has any HLT electron object")
        ax.plot(xs, f_wpt, "s-", ms=3, lw=1.1, color="darkorange",
                label="of those, WPTight")
        ax.plot(xs, f_eff, "^-", ms=3, lw=1.1, color="C0",
                label="full pass (WPTight & $p_T\\geq$27)")
        ax.set_xscale("log")
        ax.set_xticks([25, 30, 35, 40, 50, 70, 100, 200])
        ax.get_xaxis().set_major_formatter(matplotlib.ticker.ScalarFormatter())
        ax.set_title(r, fontsize=10)
        ax.set_xlabel("probe electron offline $p_T$ [GeV]", fontsize=9)
        ax.set_ylim(0, 1.05)
        ax.grid(alpha=0.3)
        ax.tick_params(labelsize=8)
    axes[0].set_ylabel("fraction", fontsize=9)
    axes[0].legend(fontsize=7.5, loc="lower right")
    fig.suptitle("Where the inefficiency comes from: the HLT finds an electron "
                 "almost always,\nbut the online WPTight identification is tighter "
                 "than our offline Medium selection", fontsize=10)
    fig.tight_layout(rect=(0, 0, 1, 0.88))
    fig.savefig(out_dir / "stepB_inefficiency_breakdown.png", dpi=140)
    plt.close(fig)
    print(f"wrote {out_dir / 'stepB_inefficiency_breakdown.png'}")


if __name__ == "__main__":
    main()
