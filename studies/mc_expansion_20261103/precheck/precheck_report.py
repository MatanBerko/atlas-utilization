#!/usr/bin/env python
"""Small real-file check report (task A1 step 3). Runs in a PBS job (reads the smoke-build ROOT files).

Inputs: the file-0 production outputs (runs_new: 54 new samples; runs_old13: 13 delivered re-runs),
the registry v4, the smoke-build reports and ROOT files of build A (13 delivered, v3 registry) and
build C (13 + 54, v4 registry), and the portal event counts from the saved records.

Writes <out>/precheck_report.json and PNGs into <out>/plots/:
  stack_<category>.png  -- build C summed by process group (13 delivered as one grey block + 7 new
                           groups), with build A's total (13 delivered only) as a black line;
  weight_scale.png      -- per-sample event weight scale sigma_eff x 16.393 fb^-1 / Sigma-w(sample).
SMOKE TEST: Sigma-w in the builds comes from file 0 only, so yields are not physics.
"""
from __future__ import annotations

import argparse
import gzip
import json
import re
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import uproot  # noqa: E402

REPO = Path(__file__).resolve().parents[3]
REG = json.loads((REPO / "studies/cms_mc_weights_v3/cms_mc_normalisation_v4.json").read_text())["records"]
EV = REPO / "studies/cms_mc_weights_v3/sources/mcexp_20261103/records"
L_PB = 16393.0
DELIVERED = [67801, 67993, 35669, 35631, 64895, 64839, 72676, 72752, 75589, 68187, 68073, 37728, 68847]
GROUPS = [  # fixed order = fixed colour; the 13 delivered are one neutral block
    ("delivered 13", DELIVERED, "#b5b4af"),
    ("W+jets", [69715, 69717, 69719], "#2a78d6"),
    ("single top t/s", [64759, 64659, 64635], "#eb6834"),
    ("tt̄ hadronic", [67841], "#1baf7a"),
    ("dibosons (new)", [72742, 75573, 72738, 72658, 72740, 75567], "#eda100"),
    ("VVV, tt̄X, 4t", [72701, 72711, 72761, 75600, 67645, 67691, 68083, 68045], "#e87ba4"),
    ("Higgs (new)", [37474, 68601, 41877, 41873, 41914, 40095, 37446, 68591, 71297, 70453, 74684, 37616, 68741,
                     71227, 70383, 37432, 68571, 71295, 70451, 74682, 37604, 68731, 71145, 70301, 74292, 40062], "#008300"),
    ("Z → νν", [74894, 74898, 74902, 74904, 74906, 74896, 74900], "#6250d6"),
]
CATS = [("mumu_0j", "μμ, 0 jets", "mass_m0m1_cat_0ex_2mx_0jx_0bx", None),
        ("emu_0j", "eμ, 0 jets", "mass_e0m0_cat_1ex_1mx_0jx_0bx", None),
        ("ee_1j", "ee + 1 jet", "mass_e0e1_cat_2ex_0mx_1jx_0bx", None),
        ("ee_2j", "ee + 2 jets", "mass_e0e1_cat_2ex_0mx_2jx_0bx", None),
        ("3l_eem", "3ℓ (ee + μ, 0 jets), m(ee)", "mass_e0e1_cat_2ex_1mx_0jx_0bx", None),
        ("3l_emm", "3ℓ (e + μμ, 0 jets), m(μμ)", "mass_m0m1_cat_1ex_2mx_0jx_0bx", None),
        ("mumu_0j_125", "μμ, 0 jets, 100-150 GeV", "mass_m0m1_cat_0ex_2mx_0jx_0bx", (100, 150))]
INK, INK2, GRID, SURF = "#0b0b0b", "#52514e", "#e6e6e3", "#fcfcfb"


def read_root(path):
    out = {}
    with uproot.open(path) as f:
        for k in f.keys(cycle=False):
            h = f[k]
            if not hasattr(h, "values"):
                continue
            m = re.search(r"(mass_[a-z0-9]+_cat_\d+ex_\d+mx_\d+jx_\d+bx)", k)
            if m:
                out[m.group(1)] = (np.asarray(h.values(), float), np.asarray(h.variances(), float), np.asarray(h.axis().edges(), float))
    return out


def portal_events(rid):
    with gzip.open(EV / f"{rid}.json.gz", "rt") as f:
        return json.load(f)["metadata"]["distribution"]["number_events"]


def style(ax):
    ax.set_facecolor(SURF)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.tick_params(colors=INK2, labelsize=8)
    ax.grid(axis="y", color=GRID, lw=0.6)
    ax.set_axisbelow(True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", nargs="+", required=True)
    ap.add_argument("--build-a", required=True)
    ap.add_argument("--build-c", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    out = Path(a.out)
    (out / "plots").mkdir(parents=True, exist_ok=True)
    rep_c = json.loads(next(Path(a.build_c).glob("*_build_report.json")).read_text())
    samples = {}
    for runs in a.runs:
        for mp in sorted(Path(runs).rglob("job_metadata.json")):
            m = json.loads(mp.read_text())
            rid = int(m["record_id"])
            mc = m["mc_diagnostics"]
            reg = REG[str(rid)]
            sw_file = m["mc_sigma_w_self_check"]["runs_gen_event_sumw"]
            n_portal = (portal_events(rid) if (EV / f"{rid}.json.gz").exists()
                        else (reg.get("provenance") or {}).get("n_events_record"))   # delivered 13: v3 provenance
            sw_sample = sw_file * n_portal / m["n_read"] if n_portal else None
            fs = m["final_state_label_event_counts_inclusive"]
            top3 = sorted(fs.items(), key=lambda kv: -kv[1])[:3]
            sc = rep_c["samples"].get(str(rid), {})
            samples[rid] = {
                "name": reg["physics_short"], "tier": reg.get("tier", 0), "sigma_eff_pb": reg["cross_section_pb"],
                "events_read": m["n_read"], "events_stored": mc["n_stored"],
                "events_in_delivery_union": mc["n_stored_in_delivery_union"],
                "sigma_w_file0": sw_file, "sigma_w_check_passes": m["mc_sigma_w_self_check"]["passes"],
                "portal_events": n_portal, "sigma_w_sample_estimate": sw_sample,
                "weight_scale_full_sample_estimate": reg["cross_section_pb"] * L_PB / sw_sample if sw_sample else None,
                "typical_event_weight_full_sample": reg["cross_section_pb"] * L_PB / n_portal if n_portal else None,
                "weight_scale_smoke_file0": sc.get("normalisation_factor"),
                "genweight_stored": mc["genweight_stored_events"],
                "top3_final_states_raw": top3, "git_commit": m["git_commit"], "elapsed_sec": m["elapsed_sec"],
            }
    hc, ha = {}, None
    for p in Path(a.build_c).glob("*_record*_mc.root"):
        hc[int(re.search(r"_record(\d+)_mc", p.name).group(1))] = read_root(p)
    sa = next(Path(a.build_a).glob("*_summedSM_mc.root"))
    ha = read_root(sa)
    plotted = {}
    for key, title, name, xr in CATS:
        present = [r for r in hc if name in hc[r]]
        if not present:
            plotted[key] = "absent in build C"
            continue
        edges = hc[present[0]][name][2]
        fig, ax = plt.subplots(figsize=(7.5, 4.4), facecolor=SURF)
        style(ax)
        bottom = np.zeros(len(edges) - 1)
        yields = {}
        for lab, recs, col in GROUPS:
            v = np.zeros(len(edges) - 1)
            for r in recs:
                if r in hc and name in hc[r] and len(hc[r][name][0]) == len(v):
                    v += hc[r][name][0]
            yields[lab] = float(v.sum())
            if v.any():
                ax.bar(edges[:-1], v, width=np.diff(edges), bottom=bottom, align="edge", color=col,
                       edgecolor=SURF, linewidth=0.4, label=f"{lab} ({v.sum():.3g})")
                bottom += v
        if name in ha:
            va, _, ea = ha[name]
            ax.stairs(va, ea, color=INK, lw=1.4, label=f"build A: delivered 13 only, v3 ({va.sum():.3g})")
            yields["build_A_total"] = float(va.sum())
        ax.set_yscale("log")
        ax.set_ylim(bottom=max(1e-3, bottom[bottom > 0].min() * 0.3) if (bottom > 0).any() else 1e-3)
        if xr:
            ax.set_xlim(*xr)
        else:  # crop to the filled range (the histograms are booked far beyond it)
            nz = np.nonzero(bottom)[0]
            if len(nz):
                lo, hi = edges[nz[0]], edges[nz[-1] + 1]
                ax.set_xlim(lo - 0.05 * (hi - lo), hi + 0.05 * (hi - lo))
        ax.set_xlabel(name.replace("mass_", "m(").split("_cat")[0] + ") [GeV]", color=INK, fontsize=9)
        ax.set_ylabel("weighted events / bin (SMOKE: file 0 only)", color=INK, fontsize=8)
        ax.set_title(f"{title} — {name}\nbuild C (13 + 54, registry v4) stacked; line = build A", fontsize=9, color=INK, loc="left")
        ax.legend(fontsize=7, frameon=False, loc="upper right")
        fig.tight_layout()
        fig.savefig(out / "plots" / f"stack_{key}.png", dpi=120, facecolor=SURF)
        plt.close(fig)
        plotted[key] = yields
    rows = sorted((s for s in samples.values() if s["typical_event_weight_full_sample"]), key=lambda s: (s["tier"], s["name"]))
    fig, ax = plt.subplots(figsize=(8, 0.2 * len(rows) + 1.2), facecolor=SURF)
    style(ax)
    ax.grid(axis="x", color=GRID, lw=0.6)
    y = np.arange(len(rows))[::-1]
    ax.barh(y, [s["typical_event_weight_full_sample"] for s in rows], color="#2a78d6", height=0.6)
    ax.axvline(1, color=INK, lw=0.8)
    ax.set_xscale("log")
    ax.set_yticks(y, [f"T{s['tier']} {s['name'][:38]}" for s in rows], fontsize=6.5)
    ax.set_xlabel("typical event weight σ_eff × 16.393 fb⁻¹ / N_events(sample) = data events per MC event (line: 1)", fontsize=8)
    ax.set_title("Per-sample typical event weight, full sample (tier 0 = delivered 13)", fontsize=9, loc="left")
    fig.tight_layout()
    fig.savefig(out / "plots" / "weight_scale.png", dpi=120, facecolor=SURF)
    plt.close(fig)
    res = {"samples": {str(k): v for k, v in sorted(samples.items())}, "plots": plotted,
           "build_c_summary": {"n_samples": len(rep_c["samples"]), "prune": {k: rep_c["prune"][k] for k in ("n_final_states_removed",)},
                               "outputs": rep_c["outputs"]}}
    (out / "precheck_report.json").write_text(json.dumps(res, indent=1, default=str) + "\n")
    print(f"{len(samples)} samples; plots: {list(plotted)}")


if __name__ == "__main__":
    sys.exit(main())
