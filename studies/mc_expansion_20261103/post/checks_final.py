#!/usr/bin/env python
"""Final MC build checks that checks_v4.py does not cover (MC expansion, 14 Nov 2026). REPORT ONLY.

Reads (never writes) the new MC build, the 25 Oct MC build, the 25 Oct DELIVERED data histograms, the registry,
the production audits and the job metadata; writes checks_final.json + PNGs into --out. Runs in a PBS job (ROOT).

  c. per sample: sigma_eff (registry vs build report), Sigma-w, normalisation = sigma*1000*L/Sigma-w recomputed,
     total weighted yield (per final state, the largest histogram integral of that final state, summed), share;
     the registry's in_full_run set vs the samples built; negative-weight fraction (audits); capped signatures;
  d. names and binning vs the delivered data (uncropped and cropped): names in both / MC-only / data-only; axis
     edges; first/last filled bin per name (new MC, 25 Oct MC, data); mismatches by final state;
  f. data/MC per final state (integral ratio over the bins where BOTH data and MC are filled, and over each one's
     own range), 25 Oct MC vs this build, MC by group, the share of the data-MC(25 Oct) gap closed;
  g. D3 single-event dominance over ALL histograms of the summed file and ALL samples. The single-event weight is
     not stored per bin, so an UPPER BOUND is used (as checks_v4.py): w1_s(bin) = min( sqrt(sum w^2 of sample s
     in the bin), normalisation_s x max|genWeight|_s x max cap scale_s ). A bin is flagged when
     max_s w1_s(bin) / (summed MC content of the bin) > 0.5 (bins with summed MC <= 0 are counted apart);
  plots: data/MC stacks (MC by group, 25 Oct MC as a line, ratio panel, the missing-processes note) and 5 D3
     examples.

    python checks_final.py --build-dir B --prefix fullrun --old-build-dir B25 --data-root D.root
        --data-cropped Dc.root --registry v5.json --audit A.json --old-audit A25.json --runs R --old-runs R25
        --out OUT
"""
from __future__ import annotations

import argparse
import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import uproot  # noqa: E402

NAME = re.compile(r"(mass_([a-z0-9]+)_cat_(\d+)ex_(\d+)mx_(\d+)jx_(\d+)bx)")
DELIVERED = [35631, 35669, 37728, 64839, 64895, 67801, 67993, 68073, 68187, 68847, 72676, 72752, 75589]
GROUPS = [  # fixed order = fixed colour (the A1 precheck palette); D15 rare top joins the tt̄X group
    ("delivered 13 (25 Oct)", DELIVERED, "#b5b4af"),
    ("W+jets", [69715, 69717, 69719], "#2a78d6"),
    ("single top t/s", [64759, 64659, 64635], "#eb6834"),
    ("tt̄ hadronic", [67841], "#1baf7a"),
    ("dibosons (new)", [72742, 75573, 72738, 72658, 72740, 75567], "#eda100"),
    ("VVV, tt̄X, 4t, rare top", [72701, 72711, 72761, 75600, 67645, 67691, 68083, 68045,
                                 68325, 64873, 68206, 68185], "#e87ba4"),
    ("Higgs (new)", [37474, 68601, 41877, 41873, 41914, 40095, 37446, 68591, 71297, 70453, 74684, 37616, 68741,
                     71227, 70383, 37432, 68571, 71295, 70451, 74682, 37604, 68731, 71145, 70301, 74292, 40062],
     "#008300"),
    ("Z → νν", [74894, 74898, 74902, 74904, 74906, 74896, 74900], "#6250d6"),
]
INK, INK2, GRID, SURF = "#0b0b0b", "#52514e", "#e6e6e3", "#fcfcfb"
MISSING = "MC missing: QCD multijet, photon processes (γ+jets, Vγ, ttγ)"
# (key, label, histogram, final state) -- the categories of the task; the histogram is the 25 Oct REPORT's choice
# where it had one, else the leading-objects mass of that final state
CATS = [
    ("mumu_0j", "μμ, 0 jets", "mass_m0m1_cat_0ex_2mx_0jx_0bx"),
    ("ee_0j", "ee, 0 jets", "mass_e0e1_cat_2ex_0mx_0jx_0bx"),
    ("emu_0j", "eμ, 0 jets", "mass_e0m0_cat_1ex_1mx_0jx_0bx"),
    ("mumu_1j", "μμ + 1 jet", "mass_m0m1j0_cat_0ex_2mx_1jx_0bx"),
    ("ee_1j", "ee + 1 jet", "mass_e0e1j0_cat_2ex_0mx_1jx_0bx"),
    ("emu_1j", "eμ + 1 jet", "mass_e0m0j0_cat_1ex_1mx_1jx_0bx"),
    ("e_1j", "e + 1 jet", "mass_e0j0_cat_1ex_0mx_1jx_0bx"),
    ("mu_1j", "μ + 1 jet", "mass_m0j0_cat_0ex_1mx_1jx_0bx"),
    ("e_2j", "e + 2 jets", "mass_e0j0j1_cat_1ex_0mx_2jx_0bx"),
    ("mu_2j", "μ + 2 jets", "mass_m0j0j1_cat_0ex_1mx_2jx_0bx"),
    ("e_3j", "e + 3 jets", "mass_e0j0j1j2_cat_1ex_0mx_3jx_0bx"),
    ("mu_3j", "μ + 3 jets", "mass_m0j0j1j2_cat_0ex_1mx_3jx_0bx"),
    ("e_1j1b", "e + jet + b", "mass_e0j0b0_cat_1ex_0mx_1jx_1bx"),
    ("mu_1j1b", "μ + jet + b", "mass_m0j0b0_cat_0ex_1mx_1jx_1bx"),
    ("mu_2j1b", "μ + 2 jets + b", "mass_m0j0j1b0_cat_0ex_1mx_2jx_1bx"),
    ("e_2j1b", "e + 2 jets + b", "mass_e0j0j1b0_cat_1ex_0mx_2jx_1bx"),
    ("3l_emm_1j", "3ℓ (e + μμ + 1 jet)", "mass_e0m0j0_cat_1ex_2mx_1jx_0bx"),
    ("3l_eem", "3ℓ (ee + μ)", "mass_e0e1_cat_2ex_1mx_0jx_0bx"),
    ("3l_emm", "3ℓ (e + μμ)", "mass_m0m1_cat_1ex_2mx_0jx_0bx"),
    ("3l_mmm", "3ℓ (μμμ)", "mass_m0m1_cat_0ex_3mx_0jx_0bx"),
    ("3l_eee", "3ℓ (eee)", "mass_e0e1_cat_3ex_0mx_0jx_0bx"),
    ("4l_eemm", "4ℓ (ee + μμ)", "mass_e0e1m0m1_cat_2ex_2mx_0jx_0bx"),
    ("4l_mmmm", "4ℓ (μμμμ)", "mass_m0m1m2m3_cat_0ex_4mx_0jx_0bx"),
]
STACKS = ["mumu_0j", "ee_0j", "emu_0j", "mumu_1j", "e_1j", "mu_2j", "mu_1j1b", "3l_emm_1j"]


def fs_of(m):
    return f"{m.group(3)}e_{m.group(4)}m_{m.group(5)}j_{m.group(6)}b"


def read(path):
    out = {}
    with uproot.open(path) as f:
        for k in f.keys(cycle=False):
            h = f[k]
            if not hasattr(h, "values"):
                continue
            m = NAME.search(k)
            if m:
                out[m.group(1)] = {"v": np.asarray(h.values(), float), "s2": np.asarray(h.variances(), float),
                                   "e": np.asarray(h.axis().edges(), float), "fs": fs_of(m)}
    return out


def filled(v):
    nz = np.nonzero(v != 0)[0]
    return (int(nz[0]), int(nz[-1])) if nz.size else (None, None)


def style(ax):
    ax.set_facecolor(SURF)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.tick_params(colors=INK2, labelsize=8)
    ax.grid(axis="y", color=GRID, lw=0.6)


def main() -> int:
    ap = argparse.ArgumentParser()
    for a in ("--build-dir", "--old-build-dir", "--data-root", "--data-cropped", "--registry", "--audit",
              "--old-audit", "--runs", "--old-runs", "--out"):
        ap.add_argument(a, required=True)
    ap.add_argument("--prefix", default="fullrun")
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=False)
    bd, ob = Path(a.build_dir), Path(a.old_build_dir)
    rep = json.loads((bd / f"{a.prefix}_build_report.json").read_text())
    reg = json.loads(Path(a.registry).read_text())
    L = reg["target_luminosity_fb"]
    res = {"what": "final MC build checks (report only)", "inputs": vars(a), "build_git_commit": rep.get("git_commit"),
           "build_registry": rep.get("registry"), "build_extra_runs_dirs": rep.get("extra_runs_dirs"),
           "build_options": rep.get("options")}

    # ---------------------------------------------------------------- c. samples
    built = sorted(rep["samples"], key=int)
    full = sorted(reg["full_run_records"], key=int)
    res["samples_built_vs_registry"] = {"n_built": len(built), "n_in_full_run": len(full),
                                        "missing": sorted(set(full) - set(built), key=int),
                                        "extra": sorted(set(built) - set(full), key=int)}
    aud = {**json.loads(Path(a.old_audit).read_text())["records"], **json.loads(Path(a.audit).read_text())["records"]}
    summed = read(bd / f"{a.prefix}_summedSM_mc.root")
    per = {rid: read(bd / f"{a.prefix}_record{rid}_mc.root") for rid in built}
    # max |genWeight| of the stored events per sample (job metadata; for the D3 bound)
    gmax = {}
    for rid in built:
        base = Path(a.runs) / f"record{rid}"
        if not base.exists():
            base = Path(a.old_runs) / f"record{rid}"
        g = 0.0
        for mp in base.glob("job_*/job_metadata.json"):
            st = (json.loads(mp.read_text()).get("mc_diagnostics") or {}).get("genweight_stored_events") or {}
            g = max(g, abs(st.get("max") or 0.0), abs(st.get("min") or 0.0))
        gmax[rid] = g

    def total_yield(hs):
        best = {}
        for n, h in hs.items():
            best[h["fs"]] = max(best.get(h["fs"], 0.0), float(h["v"].sum()))
        return sum(best.values())

    rows, tot_all = [], total_yield(summed)
    for rid in built:
        s = rep["samples"][rid]
        r = reg["records"][rid]
        sw = s["sigma_w_over_surviving_files"]
        norm_re = r["cross_section_pb"] * 1000.0 * L / sw
        y = total_yield(per[rid])
        caps = [w.get("capped_signatures") or {} for w in s.get("weight_write_stats", [])]
        cap_scale = max([1.0] + [float(v) for c in caps for v in (c.values() if isinstance(c, dict) else [])])
        ad = aud.get(rid, {})
        rows.append({"record": rid, "physics_short": s["physics_short"], "sigma_eff_pb_registry": r["cross_section_pb"],
                     "sigma_eff_pb_build": s["cross_section_pb_sigma_eff"],
                     "sigma_equal": r["cross_section_pb"] == s["cross_section_pb_sigma_eff"],
                     "k_factor": s["k_factor"], "gen_filt_eff": s["gen_filt_eff"], "sigma_w": sw,
                     "n_files_included": s["n_files_included"], "n_files_excluded": s["n_files_excluded"],
                     "normalisation_build": s["normalisation_factor"], "normalisation_recomputed": norm_re,
                     "normalisation_rel_diff": s["normalisation_factor"] / norm_re - 1,
                     "n_capped_signatures": s.get("n_capped_signatures_total"), "max_cap_scale": cap_scale,
                     "max_abs_genweight_stored": gmax[rid],
                     "negative_weight_fraction_stored": ad.get("negative_weight_fraction_stored"),
                     "n_histograms": len(per[rid]), "total_weighted_yield": y, "share_of_total": y / tot_all,
                     "estimate": bool(r.get("estimate")), "added_in": r.get("added_in")})
    res["samples"] = rows
    res["total_weighted_yield_summed"] = tot_all

    # ---------------------------------------------------------------- b. NaN / negative variance (summed + per sample)
    bad = []
    for label, hs in [("summed", summed)] + [(rid, per[rid]) for rid in built]:
        for n, h in hs.items():
            if not (np.isfinite(h["v"]).all() and np.isfinite(h["s2"]).all()) or (h["s2"] < 0).any():
                bad.append([label, n])
    res["nan_inf_negvar"] = {"n_bad": len(bad), "bad": bad[:50], "n_histograms_summed": len(summed)}

    # ---------------------------------------------------------------- d. names and binning vs the delivered data
    data = read(a.data_root)
    datac = read(a.data_cropped)
    old = read(ob / f"{a.prefix}_summedSM_mc.root")
    both = sorted(set(data) & set(summed))
    names = {"n_mc": len(summed), "n_data": len(data), "n_data_cropped": len(datac), "n_both": len(both),
             "mc_only": sorted(set(summed) - set(data)), "data_only": sorted(set(data) - set(summed)),
             "n_old_mc": len(old), "new_vs_old_mc_added": sorted(set(summed) - set(old)),
             "new_vs_old_mc_removed": sorted(set(old) - set(summed))}
    edges = []
    for n in both:
        d, m = data[n], summed[n]
        dfi, dla = filled(d["v"])
        mfi, mla = filled(m["v"])
        ofi, ola = filled(old[n]["v"]) if n in old else (None, None)
        c = datac.get(n)
        edges.append({"name": n, "fs": m["fs"], "axis_equal": bool(np.array_equal(d["e"], m["e"])),
                      "data_first_gev": None if dfi is None else d["e"][dfi], "data_last_gev": None if dla is None else d["e"][dla + 1],
                      "mc_first_gev": None if mfi is None else m["e"][mfi], "mc_last_gev": None if mla is None else m["e"][mla + 1],
                      "old_mc_first_gev": None if ofi is None else old[n]["e"][ofi],
                      "cropped_data_lo_gev": None if c is None else float(c["e"][0]),
                      "cropped_data_hi_gev": None if c is None else float(c["e"][-1])})
    for e in edges:
        e["first_bin_shift_gev_mc_minus_data"] = (None if e["mc_first_gev"] is None or e["data_first_gev"] is None
                                                  else e["mc_first_gev"] - e["data_first_gev"])
        e["first_bin_shift_gev_new_minus_old_mc"] = (None if e["mc_first_gev"] is None or e["old_mc_first_gev"] is None
                                                     else e["mc_first_gev"] - e["old_mc_first_gev"])
        e["mc_starts_inside_cropped_data"] = (None if e["cropped_data_lo_gev"] is None or e["mc_first_gev"] is None
                                              else e["cropped_data_lo_gev"] <= e["mc_first_gev"] <= e["cropped_data_hi_gev"])
    sh = Counter(e["first_bin_shift_gev_mc_minus_data"] for e in edges)
    sh_old = Counter(e["first_bin_shift_gev_new_minus_old_mc"] for e in edges)
    by_fs = defaultdict(lambda: [0, 0])
    for e in edges:
        by_fs[e["fs"]][0] += 1
        by_fs[e["fs"]][1] += e["first_bin_shift_gev_mc_minus_data"] not in (0, 0.0)
    old_vs_data = Counter((old[n]["e"][filled(old[n]["v"])[0]] - data[n]["e"][filled(data[n]["v"])[0]])
                          for n in both if n in old and filled(old[n]["v"])[0] is not None and filled(data[n]["v"])[0] is not None)
    names["edges"] = {"n_axis_equal": sum(e["axis_equal"] for e in edges),
                      "first_filled_same_as_data": sh.get(0.0, 0),
                      "first_filled_shift_mc_minus_data_gev": {str(k): v for k, v in sorted(sh.items(), key=lambda kv: (kv[0] is None, kv[0]))},
                      "old_mc_first_filled_shift_vs_data_gev": {str(k): v for k, v in sorted(old_vs_data.items())},
                      "first_filled_shift_new_minus_old_mc_gev": {str(k): v for k, v in sorted(sh_old.items(), key=lambda kv: (kv[0] is None, kv[0]))},
                      "by_final_state_n_hist_n_mismatch": {k: v for k, v in sorted(by_fs.items())},
                      "per_histogram": edges}
    res["names_binning"] = names

    # ---------------------------------------------------------------- f. data / MC per final state
    def grp_values(n):
        g = []
        for gname, recs, col in GROUPS:
            v = sum((per[str(r)][n]["v"] for r in recs if str(r) in per and n in per[str(r)]), np.zeros(1000))
            g.append((gname, v, col))
        return g

    def ratios(n):
        d, m = data[n]["v"], summed[n]["v"]
        o = old[n]["v"] if n in old else None
        common = (d != 0) & (m != 0)
        r = {"name": n, "data": float(d.sum()), "mc_new": float(m.sum()),
             "mc_old": None if o is None else float(o.sum()),
             "data_over_mc_new": float(d.sum() / m.sum()) if m.sum() else None,
             "data_over_mc_old": None if o is None or not o.sum() else float(d.sum() / o.sum()),
             "data_common_new": float(d[common].sum()), "mc_new_common": float(m[common].sum()),
             "data_over_mc_new_common": float(d[common].sum() / m[common].sum()) if m[common].sum() else None}
        if o is not None:
            co = (d != 0) & (o != 0)
            r["data_over_mc_old_common"] = float(d[co].sum() / o[co].sum()) if o[co].sum() else None
            gap = d.sum() - o.sum()
            r["gap_closed_fraction"] = float((m.sum() - o.sum()) / gap) if gap else None
        r["mc_new_by_group"] = {g: float(v.sum()) for g, v, _ in grp_values(n)}
        return r

    cats = []
    for key, label, n in CATS:
        if n not in data or n not in summed:
            fs_want = NAME.search(n)
            alt = [x for x in sorted(set(data) & set(summed), key=lambda x: -data[x]["v"].sum())
                   if fs_want and summed[x]["fs"] == fs_of(fs_want)]
            if not alt:
                cats.append({"key": key, "label": label, "name": n, "missing": True})
                continue
            n = alt[0]
        cats.append({"key": key, "label": label, **ratios(n)})
    res["data_mc_categories"] = cats
    res["data_mc_all"] = [ratios(n) for n in both]

    # ---------------------------------------------------------------- g. D3 over all histograms and samples
    normf = {r["record"]: r["normalisation_build"] for r in rows}
    capf = {r["record"]: r["max_cap_scale"] for r in rows}
    flagged, n_neg_or_zero = [], 0
    hist_flag = Counter()
    for n, h in summed.items():
        tot = h["v"]
        w1 = np.zeros_like(tot)
        who = np.full(tot.shape, -1)
        for rid in built:
            p = per[rid].get(n)
            if p is None:
                continue
            bound = np.minimum(np.sqrt(np.clip(p["s2"], 0, None)), normf[rid] * gmax[rid] * capf[rid])
            better = bound > w1
            w1[better] = bound[better]
            who[better] = int(rid)
        has = w1 > 0
        n_neg_or_zero += int((has & (tot <= 0)).sum())
        sel = has & (tot > 0) & (w1 / np.where(tot > 0, tot, 1) > 0.5)
        for b in np.nonzero(sel)[0]:
            flagged.append({"histogram": n, "fs": h["fs"], "bin_lo_gev": float(h["e"][b]), "sample": str(who[b]),
                            "single_event_weight_bound": float(w1[b]), "bin_content": float(tot[b]),
                            "share_bound": float(min(w1[b] / tot[b], 1.0))})
        if sel.any():
            hist_flag[n] += 1
    by_sample = Counter(f["sample"] for f in flagged)
    by_fs_d3 = Counter(f["fs"] for f in flagged)
    worst = sorted(flagged, key=lambda f: -f["single_event_weight_bound"])[:20]
    hist_by_sample = Counter()
    for n in hist_flag:
        hist_by_sample.update({f["sample"] for f in flagged if f["histogram"] == n})
    res["d3"] = {"method": "upper bound, see docstring", "n_bins_flagged": len(flagged),
                 "n_histograms_with_flagged_bin": len(hist_flag), "n_histograms": len(summed),
                 "n_bins_with_mc_le_zero_and_some_weight": n_neg_or_zero,
                 "bins_by_sample": dict(by_sample.most_common()), "histograms_by_sample": dict(hist_by_sample.most_common()),
                 "bins_by_final_state": dict(by_fs_d3.most_common()),
                 "worst20_by_single_event_weight": worst,
                 "wjets_1j_69717": {"bins": by_sample.get("69717", 0), "histograms": hist_by_sample.get("69717", 0)},
                 "wzz_72761": {"bins": by_sample.get("72761", 0), "histograms": hist_by_sample.get("72761", 0)}}

    # ---------------------------------------------------------------- plots
    pdir = out / "plots"
    pdir.mkdir()
    lab = {r["record"]: r["physics_short"] for r in rows}
    for key in STACKS:
        c = next(x for x in cats if x["key"] == key)
        if c.get("missing"):
            continue
        n = c["name"]
        d = data[n]["v"]
        e = data[n]["e"]
        lo, hi = filled(d)
        ml, mh = filled(summed[n]["v"])
        lo = min(x for x in (lo, ml) if x is not None)
        hi = max(x for x in (hi, mh) if x is not None)
        sl = slice(max(lo - 1, 0), min(hi + 2, len(d)))
        x = e[:-1][sl]
        fig, (ax, rx) = plt.subplots(2, 1, figsize=(7.2, 5.6), sharex=True, gridspec_kw={"height_ratios": [3, 1]},
                                     facecolor=SURF)
        bottom = np.zeros(len(x))
        for gname, v, col in grp_values(n):
            vv = v[sl]
            if np.abs(vv).sum() == 0:
                continue
            ax.bar(x, vv, width=10.0, bottom=bottom, align="edge", color=col, edgecolor=SURF, lw=0.3, label=gname)
            bottom += vv
        if n in old:
            ax.step(x, old[n]["v"][sl], where="post", color=INK2, lw=1.0, ls="--", label="MC 25 Oct (13 samples)")
        cen = x + 5
        ax.errorbar(cen, d[sl], yerr=np.sqrt(np.clip(d[sl], 0, None)), fmt="o", ms=2.5, color=INK, lw=0.8, label="data")
        ax.set_yscale("log")
        ax.set_ylabel("events / 10 GeV", color=INK2, fontsize=9)
        ax.set_title(f"{c['label']}  ({n})", color=INK, fontsize=10, loc="left")
        ax.text(0.99, 0.97, f"data/MC = {c['data_over_mc_new']:.3f} (25 Oct MC: "
                f"{c['data_over_mc_old'] if c['data_over_mc_old'] is None else round(c['data_over_mc_old'], 3)})\n{MISSING}",
                transform=ax.transAxes, ha="right", va="top", fontsize=7.5, color=INK2)
        ax.legend(fontsize=7, frameon=False, loc="lower left", ncol=2)
        rat = np.divide(d[sl], bottom, out=np.full(len(x), np.nan), where=bottom > 0)
        rx.plot(cen, rat, "o", ms=2.5, color=INK)
        rx.axhline(1.0, color=INK2, lw=0.8)
        rx.set_ylim(0, 3)
        rx.set_ylabel("data / MC", color=INK2, fontsize=9)
        rx.set_xlabel("mass [GeV]", color=INK2, fontsize=9)
        for axx in (ax, rx):
            style(axx)
        fig.tight_layout()
        fig.savefig(pdir / f"stack_{key}.png", dpi=130)
        plt.close(fig)
    for i, f in enumerate(worst[:5], 1):
        n = f["histogram"]
        h = summed[n]
        b = int(np.searchsorted(h["e"], f["bin_lo_gev"]))
        sl = slice(max(b - 30, 0), min(b + 31, len(h["v"])))
        x = h["e"][:-1][sl]
        fig, ax = plt.subplots(figsize=(7.2, 3.8), facecolor=SURF)
        ax.step(x, h["v"][sl], where="post", color=INK2, lw=1.0, label="summed MC")
        p = per[f["sample"]][n]["v"][sl]
        ax.bar(x, p, width=10.0, align="edge", color="#2a78d6", alpha=0.8, label=f"{f['sample']} {lab[f['sample']]}")
        if n in data:
            ax.plot(x + 5, data[n]["v"][sl], "o", ms=2.5, color=INK, label="data")
        ax.axvspan(f["bin_lo_gev"], f["bin_lo_gev"] + 10, color="#eb6834", alpha=0.25)
        ax.set_yscale("symlog", linthresh=1.0)
        ax.set_title(f"D3 example {i}: {n}, bin {f['bin_lo_gev']:.0f} GeV: one event ≤ {f['single_event_weight_bound']:.3g} "
                     f"of {f['bin_content']:.3g}", color=INK, fontsize=9, loc="left")
        ax.legend(fontsize=7, frameon=False)
        ax.set_xlabel("mass [GeV]", color=INK2, fontsize=9)
        style(ax)
        fig.tight_layout()
        fig.savefig(pdir / f"d3_example_{i}.png", dpi=130)
        plt.close(fig)

    (out / "checks_final.json").write_text(json.dumps(res, indent=1, default=float) + "\n")
    s = res["samples_built_vs_registry"]
    print("samples built", s, "| NaN/negvar", res["nan_inf_negvar"]["n_bad"], "| names both", names["n_both"],
          "mc-only", len(names["mc_only"]), "data-only", len(names["data_only"]),
          "| first filled same", names["edges"]["first_filled_same_as_data"],
          "| D3 bins", res["d3"]["n_bins_flagged"], "hists", res["d3"]["n_histograms_with_flagged_bin"], flush=True)
    for c in cats:
        if not c.get("missing"):
            print(f"{c['key']:10s} {c['name']:40s} data {c['data']:.4g} new {c['mc_new']:.4g} old {c['mc_old']} "
                  f"d/new {c['data_over_mc_new']} d/old {c['data_over_mc_old']} gap_closed {c.get('gap_closed_fraction')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
