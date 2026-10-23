#!/usr/bin/env python
"""
CMS MC full run (17 Oct 2026), step 5b-d: build-report checks, sanity
checks and the PNGs. Runs as a PBS job (it reads every delivered ROOT file).

5b  Build report: 13 records, Sigma-w per record, files included/excluded,
    exactly one exclusion (75589 file 98, Matan's option A).
5c  Every histogram of every per-sample file and of the summed-SM file:
    count, NaN/inf in contents or variances. Per record, a reasonableness
    check of the weighted yield of the STORED events, computed from the
    production metadata (no histogram double counting):
        sigma_eff * 1000 * L * sum(genWeight over stored events) / Sigma-w
    vs sigma_eff * L (= every generated event): the ratio is the weighted
    storage efficiency and must sit near the raw stored fraction (L1
    prefiring, < 3%, is not included here). Negative-weight fractions
    from the production audit.
5d  Stacked summed-SM mass plots for well-populated categories, the 13
    samples grouped into 8 processes (the colour palette carries 8
    distinguishable hues; a 9th generated hue is never used), with the
    summed-SM file drawn on top as a closure check; and one plot per record
    of its most-populated weighted histogram.

Writes sanity_report.json and the PNGs into --out-dir.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import uproot  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))
from studies.cms_mc_weights_v3.deliver import build_mc_delivery as B  # noqa: E402

RECORDS = [67801, 67993, 35669, 35631, 64895, 64839, 72676, 72752, 75589, 68187,
           68073, 37728, 68847]
GROUPS = [  # fixed order = fixed colour (validated default palette, light mode)
    ("tt̄", (67801, 67993), "#2a78d6"),
    ("Drell-Yan", (35669, 35631), "#eb6834"),
    ("single top tW", (64895, 64839), "#1baf7a"),
    ("WW", (72676,), "#eda100"),
    ("WZ", (72752,), "#e87ba4"),
    ("ZZ", (75589,), "#008300"),
    ("tt̄W, tt̄Z", (68187, 68073), "#6250d6"),
    ("Higgs → ZZ → 4ℓ", (37728, 68847), "#e34948"),
]
INK, INK2, GRID, SURF = "#0b0b0b", "#52514e", "#e6e6e3", "#fcfcfb"
NAME_RE = re.compile(r"ROI_mass_(?P<im>[a-z0-9]+)_cat_(?P<e>\d+)ex_(?P<m>\d+)mx_(?P<j>\d+)jx_(?P<b>\d+)bx")
CATEGORIES = [  # (title, predicate on the parsed name)
    ("μμ, 0 jets", lambda d: d["im"] == "m0m1" and (d["e"], d["m"], d["j"], d["b"]) == (0, 2, 0, 0)),
    ("ee, 0 jets", lambda d: d["im"] == "e0e1" and (d["e"], d["m"], d["j"], d["b"]) == (2, 0, 0, 0)),
    ("eμ, 0 jets", lambda d: d["im"] == "e0m0" and (d["e"], d["m"], d["j"], d["b"]) == (1, 1, 0, 0)),
    ("μμ + jets, ≥3 jets (most populated)", lambda d: d["im"].startswith("m0m1j0") and d["m"] == 2 and d["e"] == 0 and d["j"] >= 3),
    ("4 leptons (most populated)", lambda d: len(re.findall(r"[em]\d", d["im"])) == 4 and d["e"] + d["m"] == 4),
    ("μ + jet + b (tt̄-like, most populated)", lambda d: "b0" in d["im"] and d["m"] == 1 and d["e"] == 0),
]


def read_all(path: Path) -> dict:
    out = {}
    with uproot.open(path) as f:
        for k in f.keys(cycle=False):
            h = f[k]
            if not hasattr(h, "values"):
                continue
            out[k] = {"values": np.asarray(h.values(flow=True), float),
                      "variances": np.asarray(h.variances(flow=True), float),
                      "edges": np.asarray(h.axis().edges(), float),
                      "entries": float(h.member("fEntries"))}
    return out


def parse(name: str):
    m = NAME_RE.search(name)
    if not m:
        return None
    d = m.groupdict()
    return {"im": d["im"], "e": int(d["e"]), "m": int(d["m"]), "j": int(d["j"]), "b": int(d["b"])}


def style(ax):
    ax.grid(axis="y", color=GRID, lw=0.6)
    ax.tick_params(colors=INK2)
    for s in ax.spines.values():
        s.set_color("#c9c8c3")


def stacked(name: str, title: str, per: dict, summed: dict, out: Path) -> dict:
    edges = summed[name]["edges"]
    parts = []
    for label, recs, color in GROUPS:
        v = np.zeros(len(edges) - 1)
        for r in recs:
            if name in per.get(r, {}):
                v += per[r][name]["values"][1:-1]
        parts.append((label, color, v))
    total = summed[name]["values"][1:-1]
    err = np.sqrt(summed[name]["variances"][1:-1])
    closure = float(np.max(np.abs(sum(p[2] for p in parts) - total)) /
                    max(float(np.max(np.abs(total))), 1e-300))
    nz = np.flatnonzero(total != 0)
    lo, hi = (nz[0], nz[-1] + 1) if nz.size else (0, len(total))
    e = edges[lo:hi + 1]
    fig, ax = plt.subplots(figsize=(8, 5))
    base = np.zeros(hi - lo)
    order = sorted(range(len(parts)), key=lambda i: parts[i][2].sum())  # small at bottom
    for i in order:
        label, color, v = parts[i]
        v = np.clip(v[lo:hi], 0, None)   # negative group contents are not stackable; shown in the total
        if v.sum() <= 0:
            continue
        ax.fill_between(np.repeat(e, 2)[1:-1], np.repeat(base, 2), np.repeat(base + v, 2),
                        color=color, lw=0, label=f"{label}  ({parts[i][2].sum():,.4g})")
        base = base + v
    ax.stairs(total[lo:hi], e, color=INK, lw=1.2, label=f"summed-SM file ({total.sum():,.4g})")
    c = 0.5 * (e[:-1] + e[1:])
    ax.errorbar(c, total[lo:hi], yerr=err[lo:hi], fmt="none", ecolor=INK2, lw=0.7)
    pos = total[lo:hi][total[lo:hi] > 0]
    if pos.size and pos.max() / pos.min() > 50:
        ax.set_yscale("log")
        ax.set_ylim(bottom=max(pos.min() * 0.3, pos.max() * 1e-6))
    ax.set_xlabel("mass [GeV]", color=INK)
    ax.set_ylabel(f"weighted events / bin  (L = {B.TARGET_LUMINOSITY_FB} fb⁻¹)", color=INK)
    ax.set_title(f"CMS MC full run, summed SM — {title}\n{name}", fontsize=9, color=INK)
    h, l = ax.get_legend_handles_labels()
    ax.legend(h[::-1], l[::-1], fontsize=7.5, frameon=False, loc="upper right")
    style(ax)
    fig.savefig(out, dpi=130, bbox_inches="tight", facecolor=SURF)
    plt.close(fig)
    return {"png": out.name, "category": title, "histogram": name,
            "total_weighted": float(total.sum()), "entries": summed[name]["entries"],
            "by_group": {p[0]: float(p[2].sum()) for p in parts},
            "max_rel_closure_groups_vs_summed_file": closure}


def per_record_plot(rid: int, hists: dict, label: str, out: Path) -> dict:
    k = max(hists, key=lambda x: hists[x]["entries"])
    h = hists[k]
    v, err, e = h["values"][1:-1], np.sqrt(h["variances"][1:-1]), h["edges"]
    nz = np.flatnonzero(v != 0)
    lo, hi = (nz[0], nz[-1] + 1) if nz.size else (0, len(v))
    color = next(c for _l, recs, c in GROUPS if rid in recs)
    fig, ax = plt.subplots(figsize=(7.5, 4.4))
    ax.stairs(v[lo:hi], e[lo:hi + 1], color=color, lw=2)
    c = 0.5 * (e[lo:hi] + e[lo + 1:hi + 1])
    ax.errorbar(c, v[lo:hi], yerr=err[lo:hi], fmt="none", ecolor=INK2, lw=0.8)
    pos = v[lo:hi][v[lo:hi] > 0]
    if pos.size and pos.max() / pos.min() > 50:
        ax.set_yscale("log")
    ax.set_xlabel("mass [GeV]", color=INK)
    ax.set_ylabel(f"weighted events / bin  (L = {B.TARGET_LUMINOSITY_FB} fb⁻¹)", color=INK)
    ax.set_title(f"CMS MC full run — record {rid} {label}\n{k}  ({h['entries']:,.0f} raw entries; "
                 f"sum {v.sum():,.4g})", fontsize=8.5, color=INK)
    style(ax)
    fig.savefig(out, dpi=130, bbox_inches="tight", facecolor=SURF)
    plt.close(fig)
    return {"png": out.name, "histogram": k, "entries": h["entries"], "sum_weighted": float(v.sum())}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--build-dir", required=True)
    ap.add_argument("--prefix", default="fullrun")
    ap.add_argument("--audit", required=True)
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args()
    bd, out = Path(args.build_dir), Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    report = json.loads((bd / f"{args.prefix}_build_report.json").read_text())
    audit = json.loads(Path(args.audit).read_text())["records"]
    registry = B.load_registry()["records"]

    # ---- 5b build report --------------------------------------------------
    samples = report["samples"]
    excluded = [(int(rid), e["file_index"]) for rid, s in samples.items()
                for e in s.get("per_file_sigma_w", []) if "EXCLUDED" in str(e.get("verdict"))]
    b = {"records_in_build": sorted(int(r) for r in samples),
         "all_13_present": sorted(int(r) for r in samples) == sorted(RECORDS),
         "excluded_files": excluded,
         "exactly_one_exclusion_75589_98": excluded == [(75589, 98)],
         "per_record": {rid: {k: s.get(k) for k in ("physics_short", "cross_section_pb_sigma_eff",
                                                      "n_files_included", "n_files_excluded",
                                                      "sigma_w_over_surviving_files",
                                                      "normalisation_factor", "n_capped_signatures_total")}
                        for rid, s in samples.items()},
         "prune": {k: v for k, v in (report.get("prune") or {}).items() if not isinstance(v, (list, dict))},
         "git_commit": report.get("git_commit"), "options": report.get("options")}

    # ---- 5c sanity ----------------------------------------------------------
    per = {}
    files = {}
    for rid in RECORDS:
        p = bd / f"{args.prefix}_record{rid}_mc.root"
        per[rid] = read_all(p)
        files[str(rid)] = per[rid]
    summed = read_all(bd / f"{args.prefix}_summedSM_mc.root")
    files["summedSM"] = summed
    hist_checks = {}
    for k, hs in files.items():
        bad = [n for n, h in hs.items() if not (np.all(np.isfinite(h["values"])) and np.all(np.isfinite(h["variances"])))]
        neg_var = [n for n, h in hs.items() if np.any(h["variances"] < 0)]
        hist_checks[k] = {"n_histograms": len(hs), "n_with_nan_or_inf": len(bad), "examples": bad[:5],
                          "n_with_negative_variance": len(neg_var),
                          "n_with_negative_bins": sum(1 for h in hs.values() if np.any(h["values"][1:-1] < 0))}
    L = B.TARGET_LUMINOSITY_FB
    yields = {}
    for rid in RECORDS:
        a = audit[str(rid)]
        sigma = registry[str(rid)]["cross_section_pb"]
        sw = samples[str(rid)]["sigma_w_over_surviving_files"]
        all_gen = sigma * 1000 * L
        stored_w = all_gen * a["sum_genweight_stored_passing"] / sw
        yields[rid] = {"sigma_eff_pb": sigma, "sigma_x_L_all_generated": all_gen,
                       "weighted_stored_events": stored_w,
                       "weighted_storage_efficiency": stored_w / all_gen,
                       "raw_stored_fraction": a["events_stored"] / a["events_read"],
                       "negative_weight_fraction_stored": a["negative_weight_fraction_stored"],
                       "audit_sigma_w_matches_build": abs(a["sum_runs_gen_event_sumw_passing"] - sw) / sw < 1e-9}

    # ---- 5d PNGs ------------------------------------------------------------
    plots = []
    parsed = {n: parse(n) for n in summed}
    for i, (title, pred) in enumerate(CATEGORIES, 1):
        cands = [n for n, d in parsed.items() if d and pred(d)]
        if not cands:
            plots.append({"category": title, "png": None, "reason": "no such histogram in the summed file"})
            continue
        name = max(cands, key=lambda n: summed[n]["entries"])
        plots.append(stacked(name, title, per, summed, out / f"stack_{i}.png"))
    rec_plots = {rid: per_record_plot(rid, per[rid], registry[str(rid)]["physics_short"], out / f"record_{rid}.png")
                 for rid in RECORDS}

    res = {"build_report": b, "histogram_checks": hist_checks, "yields": yields,
           "stacked_plots": plots, "per_record_plots": rec_plots}
    (out / "sanity_report.json").write_text(json.dumps(res, indent=2, default=str))
    print(json.dumps({"build_report": {k: v for k, v in b.items() if k != "per_record"},
                      "histogram_checks": hist_checks}, indent=1, default=str))
    for rid, y in yields.items():
        print(rid, {k: (round(v, 5) if isinstance(v, float) else v) for k, v in y.items()})
    for p in plots:
        print(p.get("png"), p.get("category"), p.get("histogram"), p.get("total_weighted"),
              p.get("max_rel_closure_groups_vs_summed_file"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
