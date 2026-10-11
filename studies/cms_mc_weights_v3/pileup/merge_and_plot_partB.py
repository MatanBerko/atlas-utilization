#!/usr/bin/env python
"""
Part B: merge the per-file probe JSONs and make B1-B5, then score the
pre-stated interpretation criteria (ii)-(v).

Normalisation, stated up front because it matters for reading the plots:

  * Each MC sample's events carry `genWeight x L1PreFiringWeight_Nom` from
    the probe. Here they are multiplied by `sigma_eff[pb] * 1000 * L_fb /
    Sigma-w(subset)`, where Sigma-w(subset) is the Runs-tree `genEventSumw`
    summed over exactly the files in this subset. That is the pilot's own
    rule applied to the subset, so the MC is on an absolute footing.
  * The DATA subset is 20 of 57 DoubleMuon and 20 of 133 DoubleEG files, and
    a file's integrated luminosity is not recoverable from what is stored,
    so the data subset's luminosity is NOT known. **Part B is therefore a
    SHAPE study**: per channel, the MC is rescaled by one single number so
    its inclusive Z-window yield matches the data subset's, and that number
    is reported. Every criterion Part B tests -- does the ratio rise with
    pileup, does the excess shrink at a higher jet threshold, are the extra
    jets soft or forward, does data fail the pileup-jet ID more often -- is
    a statement about shape and is untouched by that single factor.
  * The ABSOLUTE normalisation question was already answered by the pilot
    (data/MC = 1.034 mumu, 0.953 ee over the full file set) and is re-tested
    absolutely in Part A4, not here.
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


def _acc(dst, src, key):
    a = np.asarray(src[key], dtype=np.float64)
    if key not in dst:
        dst[key] = a.copy()
    else:
        dst[key] = dst[key] + a


def merge(probe_dir: pathlib.Path, registry: dict, inputs: dict) -> dict:
    """Sum the per-file histograms, applying each MC sample's absolute
    normalisation over the Sigma-w of the subset actually read."""
    data = {ch: {} for ch in ("mumu", "ee")}
    mc = {ch: defaultdict(dict) for ch in ("mumu", "ee")}
    meta = {"data_files": 0, "mc_files": defaultdict(int),
            "sigma_w_subset": defaultdict(float),
            "puid_titles": {}, "puid_present": {}}

    files = sorted(probe_dir.glob("*.json"))
    if not files:
        raise SystemExit(f"no probe JSONs in {probe_dir}")

    # pass 1: Sigma-w of the MC files actually in the subset
    for path in files:
        p = json.loads(path.read_text(encoding="utf-8"))
        if p["kind"] != "mc":
            continue
        rid = str(p["record_id"])
        fi = p["file_index"]
        per_file = inputs["records"][rid]["files"][fi]
        if per_file["file_index"] != fi:
            raise SystemExit(f"input index mismatch for {rid} file {fi}")
        meta["sigma_w_subset"][rid] += float(per_file["runs_gen_event_sumw"])
        meta["mc_files"][rid] += 1

    norm = {}
    for rid, sw in meta["sigma_w_subset"].items():
        rec = registry["records"][rid]
        if rec["k_factor"] != 1.0 or rec["gen_filt_eff"] != 1.0:
            raise SystemExit(f"record {rid}: k/eps must be 1.0")
        norm[rid] = float(rec["cross_section_pb"]) * PB_TO_FB * LUMI_FB / sw

    # pass 2: accumulate
    for path in files:
        p = json.loads(path.read_text(encoding="utf-8"))
        kind = p["kind"]
        meta["puid_present"][f"{kind}:{p['dataset_label']}"] = p["jet_puid_present"]
        if p.get("jet_puid_title"):
            meta["puid_titles"][f"{kind}:{p['dataset_label']}"] = p["jet_puid_title"]
        if kind == "data":
            meta["data_files"] += 1
        scale = norm[str(p["record_id"])] if kind == "mc" else 1.0
        rid = str(p["record_id"]) if kind == "mc" else "data"
        for ch, entry in p["channels"].items():
            if not entry or entry.get("n_z_events", 0) == 0:
                continue
            dst = data[ch] if kind == "data" else mc[ch].setdefault(rid, {})
            for key, val in entry.items():
                if key in ("n_z_events", "sum_w"):
                    dst[key] = dst.get(key, 0) + val
                    continue
                if not isinstance(val, list):
                    continue
                a = np.asarray(val, dtype=np.float64)
                if kind == "mc" and not key.endswith("_raw"):
                    a = a * (scale ** 2 if key.endswith("sumw2") else scale)
                dst[key] = dst.get(key, 0.0) + a
    meta["normalisation_factor"] = norm
    meta["mc_files"] = dict(meta["mc_files"])
    meta["sigma_w_subset"] = dict(meta["sigma_w_subset"])
    return {"data": data, "mc": {ch: dict(v) for ch, v in mc.items()}, "meta": meta}


def mc_sum(mc_ch: dict, key: str) -> np.ndarray:
    tot = None
    for rid, d in mc_ch.items():
        if key not in d:
            continue
        tot = d[key].copy() if tot is None else tot + d[key]
    return tot


def ratio_with_err(d, m, m_err2=None):
    d = np.asarray(d, dtype=np.float64)
    m = np.asarray(m, dtype=np.float64)
    with np.errstate(divide="ignore", invalid="ignore"):
        r = np.where(m > 0, d / m, np.nan)
        e = np.where(m > 0, np.sqrt(np.maximum(d, 0)) / m, np.nan)
    return r, e


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--probe-dir", required=True)
    ap.add_argument("--registry", required=True)
    ap.add_argument("--pilot-inputs", required=True,
                    help="measure_pilot_inputs.py output, for per-file Sigma-w")
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args()

    out_dir = pathlib.Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    registry = json.loads(pathlib.Path(args.registry).read_text(encoding="utf-8"))
    inputs = json.loads(pathlib.Path(args.pilot_inputs).read_text(encoding="utf-8"))

    merged = merge(pathlib.Path(args.probe_dir), registry, inputs)
    data, mc, meta = merged["data"], merged["mc"], merged["meta"]
    npvs_edges = np.arange(0.0, 81.0, 1.0)
    npvs_c = 0.5 * (npvs_edges[:-1] + npvs_edges[1:])

    report = {
        "what": "Part B: pileup fingerprint checks",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "normalisation": (
            "MC absolute via sigma_eff*1000*L/Sigma-w(subset); then ONE factor "
            "per channel so the inclusive Z-window yield matches the data "
            "subset, because the data subset's luminosity is not recoverable. "
            "Part B is a SHAPE study; the absolute test is Part A4."),
        "meta": meta, "results": {},
    }

    # one shape factor per channel, from the 30 GeV jet multiplicity
    shape_factor = {}
    for ch in ("mumu", "ee"):
        if not data[ch] or not mc[ch]:
            continue
        d_tot = float(np.asarray(data[ch]["njets30"]).sum())
        m_tot = float(mc_sum(mc[ch], "njets30").sum())
        shape_factor[ch] = d_tot / m_tot if m_tot else 1.0
    report["shape_factor_per_channel"] = shape_factor
    report["shape_factor_meaning"] = (
        "data_subset_Z_yield / MC_absolute_Z_yield. It absorbs the unknown "
        "luminosity of the data file subset. A value far from the ratio of "
        "file counts would be a red flag; it is reported, not hidden.")

    # ---- B1: PV_npvsGood ------------------------------------------------
    fig, axes = plt.subplots(2, 2, figsize=(13.0, 6.0), sharex=True,
                             gridspec_kw={"height_ratios": [3, 1], "hspace": 0.07})
    b1 = {}
    for col, ch in enumerate(("mumu", "ee")):
        axm, axr = axes[0][col], axes[1][col]
        d = np.asarray(data[ch]["npvs_by_njet30"]).sum(axis=0)
        m = mc_sum(mc[ch], "npvs_by_njet30").sum(axis=0) * shape_factor[ch]
        mpu_raw = mc_sum(mc[ch], "npvs_by_njet30_pu")
        mpu = (mpu_raw.sum(axis=0) * shape_factor[ch]) if mpu_raw is not None else None
        if mpu is not None and mpu.sum() > 0:
            mpu = mpu * (m.sum() / mpu.sum())   # compare SHAPES at equal area
        axm.step(npvs_c, m, where="mid", color="#4299e1", lw=1.4, label="MC, no w_PU")
        if mpu is not None:
            axm.step(npvs_c, mpu, where="mid", color="#ed8936", lw=1.4,
                     label="MC, with w_PU")
        axm.errorbar(npvs_c, d, yerr=np.sqrt(d), fmt="o", ms=2.8, color="black",
                     lw=0.9, capsize=1.2, label="data")
        axm.set_ylabel("Z events / unit")
        axm.set_title(f"{ch}: good primary vertices in Z events", fontsize=9.5)
        axm.set_xlim(0, 60)
        axm.legend(fontsize=7.5)
        axm.grid(alpha=0.2, lw=0.5)
        r, e = ratio_with_err(d, m)
        axr.errorbar(npvs_c, r, yerr=e, fmt="o", ms=2.8, color="#4299e1", lw=0.9)
        if mpu is not None:
            rp, ep = ratio_with_err(d, mpu)
            axr.errorbar(npvs_c, rp, yerr=ep, fmt="s", ms=2.8, color="#ed8936", lw=0.9)
        axr.axhline(1.0, color="#718096", ls="--", lw=1)
        axr.set_ylim(0, 2.4)
        axr.set_xlabel("PV_npvsGood")
        axr.set_ylabel("data / MC", fontsize=8)
        axr.grid(alpha=0.2, lw=0.5)
        mean_d = float((d * npvs_c).sum() / d.sum()) if d.sum() else None
        mean_m = float((m * npvs_c).sum() / m.sum()) if m.sum() else None
        mean_p = (float((mpu * npvs_c).sum() / mpu.sum())
                  if mpu is not None and mpu.sum() else None)
        b1[ch] = {"mean_npvs_data": mean_d, "mean_npvs_mc": mean_m,
                  "mean_npvs_mc_pu": mean_p,
                  "n_z_events_data": data[ch]["n_z_events"]}
    fig.suptitle("B1 — primary-vertex multiplicity in Z events (shapes at equal "
                 "area). If MC under-models pileup, the blue curve sits left of "
                 "the data.", fontsize=9.5)
    fig.tight_layout(rect=(0, 0, 1, 0.92))
    p = out_dir / "B1_npvs.png"
    fig.savefig(p, dpi=140); plt.close(fig)
    b1["png"] = str(p); report["results"]["B1"] = b1
    print(f"wrote {p}", flush=True)

    # ---- B2: data/MC at >=3 jets vs PV_npvsGood -------------------------
    fig, axes = plt.subplots(1, 2, figsize=(12.5, 4.6))
    b2 = {}
    for col, ch in enumerate(("mumu", "ee")):
        ax = axes[col]
        d2 = np.asarray(data[ch]["npvs_by_njet30"])
        m2 = mc_sum(mc[ch], "npvs_by_njet30") * shape_factor[ch]
        d_ge3 = d2[3:, :].sum(axis=0)
        m_ge3 = m2[3:, :].sum(axis=0)
        # ~5 bins of roughly equal DATA statistics in the >=3-jet sample
        cum = np.cumsum(d_ge3)
        if cum[-1] <= 0:
            continue
        targets = np.linspace(0, cum[-1], 6)[1:-1]
        cuts = [0] + [int(np.searchsorted(cum, t)) + 1 for t in targets] + [len(d_ge3)]
        cuts = sorted(set(cuts))
        xs, rs, es, lo, hi = [], [], [], [], []
        for a, b in zip(cuts[:-1], cuts[1:]):
            dd, mm = d_ge3[a:b].sum(), m_ge3[a:b].sum()
            if mm <= 0 or dd <= 0:
                continue
            xs.append(float((npvs_c[a:b] * d_ge3[a:b]).sum() / dd))
            rs.append(float(dd / mm))
            es.append(float(np.sqrt(dd) / mm))
            lo.append(float(npvs_edges[a])); hi.append(float(npvs_edges[b]))
        ax.errorbar(xs, rs, yerr=es, fmt="o", ms=5, color="#c05621", lw=1.2,
                    capsize=2.5)
        ax.axhline(1.0, color="#718096", ls="--", lw=1)
        if len(xs) >= 2:
            slope, intercept = np.polyfit(xs, rs, 1)
            xx = np.linspace(min(xs), max(xs), 10)
            ax.plot(xx, slope * xx + intercept, color="#718096", ls=":", lw=1.2,
                    label=f"slope {slope:+.4f} / vertex")
            ax.legend(fontsize=8)
        else:
            slope = None
        ax.set_xlabel("PV_npvsGood (mean of the bin)")
        ax.set_ylabel("data / MC at >=3 light jets")
        ax.set_title(f"{ch}", fontsize=10)
        ax.grid(alpha=0.2, lw=0.5)
        b2[ch] = {"bin_edges": list(zip(lo, hi)), "x": xs, "ratio": rs,
                  "ratio_err": es,
                  "slope_per_vertex": (None if slope is None else float(slope)),
                  "first_to_last": (None if len(rs) < 2 else float(rs[-1] - rs[0])),
                  "first_to_last_sigma": (
                      None if len(rs) < 2 else
                      float((rs[-1] - rs[0]) / np.hypot(es[0], es[-1])))}
    fig.suptitle("B2 — does the >=3-jet excess grow with pileup? A clear rise "
                 "would support the pileup explanation.", fontsize=9.5)
    fig.tight_layout(rect=(0, 0, 1, 0.90))
    p = out_dir / "B2_ratio_vs_npvs.png"
    fig.savefig(p, dpi=140); plt.close(fig)
    b2["png"] = str(p); report["results"]["B2"] = b2
    print(f"wrote {p}", flush=True)

    # ---- B3: data/MC per jet multiplicity at 30 / 40 / 50 GeV -----------
    fig, axes = plt.subplots(1, 2, figsize=(13.0, 4.8))
    b3 = {}
    x = np.arange(len(NJET_LABELS))
    for col, ch in enumerate(("mumu", "ee")):
        ax = axes[col]
        per_thr = {}
        for thr, colour in ((30, "#c05621"), (40, "#4299e1"), (50, "#2f855a")):
            key = f"njets{thr}"
            d = np.asarray(data[ch][key])
            m = mc_sum(mc[ch], key) * shape_factor[ch]
            # each threshold renormalised to its own inclusive yield, so the
            # comparison is of SHAPE across multiplicity, not of the (unknown)
            # data luminosity
            m = m * (d.sum() / m.sum()) if m.sum() else m
            r, e = ratio_with_err(d, m)
            ax.errorbar(x + (thr - 40) * 0.012, r, yerr=e, fmt="o-", ms=4.5,
                        lw=1.1, capsize=2, color=colour,
                        label=f"jet pT > {thr} GeV")
            per_thr[str(thr)] = {
                "ratio": [None if not np.isfinite(v) else float(v) for v in r],
                "ratio_err": [None if not np.isfinite(v) else float(v) for v in e],
                "data": d.tolist(), "mc": m.tolist()}
        ax.axhline(1.0, color="#718096", ls="--", lw=1)
        ax.set_xticks(x); ax.set_xticklabels(NJET_LABELS)
        ax.set_xlabel("light jets above the threshold")
        ax.set_ylabel("data / MC (shape, each threshold self-normalised)")
        ax.set_title(ch, fontsize=10)
        ax.legend(fontsize=8)
        ax.grid(alpha=0.2, lw=0.5)
        b3[ch] = per_thr
    fig.suptitle("B3 — does the excess shrink when only harder jets are counted? "
                 "Pileup jets are soft, so a strong shrink would support pileup.",
                 fontsize=9.5)
    fig.tight_layout(rect=(0, 0, 1, 0.90))
    p = out_dir / "B3_ratio_vs_threshold.png"
    fig.savefig(p, dpi=140); plt.close(fig)
    b3["png"] = str(p); report["results"]["B3"] = b3
    print(f"wrote {p}", flush=True)

    # ---- B4: the 3rd-leading jet ----------------------------------------
    pt_edges = np.arange(30.0, 205.0, 5.0)
    eta_edges = np.arange(0.0, 2.6, 0.1)
    fig, axes = plt.subplots(2, 2, figsize=(13.0, 7.4))
    b4 = {}
    for row, (key, edges, xlabel) in enumerate(
            (("jet3_pt", pt_edges, "3rd-leading jet pT [GeV]"),
             ("jet3_abseta", eta_edges, "3rd-leading jet |eta|"))):
        c = 0.5 * (edges[:-1] + edges[1:])
        for col, ch in enumerate(("mumu", "ee")):
            ax = axes[row][col]
            if key not in data[ch]:
                continue
            d = np.asarray(data[ch][key])
            m = mc_sum(mc[ch], key)
            if m is None:
                continue
            m = m * (d.sum() / m.sum()) if m.sum() else m
            ax.step(c, m, where="mid", color="#4299e1", lw=1.4, label="MC (area-matched)")
            ax.errorbar(c, d, yerr=np.sqrt(d), fmt="o", ms=2.8, color="black",
                        lw=0.9, capsize=1.2, label="data")
            ax.set_xlabel(xlabel); ax.set_ylabel("events")
            ax.set_title(f"{ch}, >=3 jets", fontsize=9.5)
            ax.legend(fontsize=7.5); ax.grid(alpha=0.2, lw=0.5)
            if key == "jet3_pt":
                ax.set_yscale("log")
            md = float((d * c).sum() / d.sum()) if d.sum() else None
            mm = float((m * c).sum() / m.sum()) if m.sum() else None
            b4.setdefault(ch, {})[key] = {"mean_data": md, "mean_mc": mm,
                                          "n_data": float(d.sum())}
    fig.suptitle("B4 — are the extra jets soft and/or forward? Data softer or more "
                 "forward than MC would support pileup.", fontsize=9.5)
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    p = out_dir / "B4_third_jet.png"
    fig.savefig(p, dpi=140); plt.close(fig)
    b4["png"] = str(p); report["results"]["B4"] = b4
    print(f"wrote {p}", flush=True)

    # ---- B5: pileup-jet-ID failure fraction -----------------------------
    fig, axes = plt.subplots(1, 2, figsize=(13.0, 4.8))
    b5 = {"puid_titles": meta["puid_titles"], "puid_present": meta["puid_present"],
          "note": "DIAGNOSTIC ONLY -- the pileup-jet ID is not applied to "
                  "anything. 'loose' is taken as bit 0 of Jet_puId; the branch "
                  "title is recorded so the convention is auditable. The ID is "
                  "only meaningful below ~50 GeV, so the low-pT subset is given "
                  "too."}
    for col, ch in enumerate(("mumu", "ee")):
        ax = axes[col]
        got = False
        for tag, (num, den, colour, style) in {
            "all jets": ("pujet_fail_by_njet", "pujet_total_by_njet", "#c05621", "o-"),
            "jets pT<50": ("pujet_fail_lowpt_by_njet", "pujet_total_lowpt_by_njet",
                           "#2f855a", "s--"),
        }.items():
            if num not in data[ch]:
                continue
            got = True
            dn, dd = np.asarray(data[ch][num]), np.asarray(data[ch][den])
            mn, md = mc_sum(mc[ch], num), mc_sum(mc[ch], den)
            with np.errstate(divide="ignore", invalid="ignore"):
                fd = np.where(dd > 0, dn / dd, np.nan)
                fm = np.where((md is not None) & (md > 0), mn / md, np.nan)
                ed = np.where(dd > 0, np.sqrt(np.maximum(dn, 0)) / dd, np.nan)
            ax.errorbar(np.arange(len(fd)), fd, yerr=ed, fmt=style, ms=4.5, lw=1.1,
                        color=colour, capsize=2, label=f"data, {tag}")
            ax.plot(np.arange(len(fm)), fm, style, ms=4.5, lw=1.1, mfc="none",
                    color=colour, alpha=0.7, label=f"MC, {tag}")
            b5.setdefault(ch, {})[tag] = {
                "data_fail_fraction": [None if not np.isfinite(v) else float(v) for v in fd],
                "mc_fail_fraction": [None if not np.isfinite(v) else float(v) for v in fm],
                "data_fail_fraction_err": [None if not np.isfinite(v) else float(v) for v in ed],
            }
        if got:
            ax.set_xticks(range(len(NJET_LABELS)))
            ax.set_xticklabels(NJET_LABELS)
            ax.set_xlabel("light-jet multiplicity")
            ax.set_ylabel("fraction FAILING loose pileup-jet ID")
            ax.set_title(ch, fontsize=10)
            ax.legend(fontsize=7)
            ax.grid(alpha=0.2, lw=0.5)
        else:
            ax.text(0.5, 0.5, "Jet_puId not available", ha="center", va="center",
                    transform=ax.transAxes)
            ax.set_axis_off()
    fig.suptitle("B5 — do data jets fail the pileup-jet ID more often than MC? "
                 "DIAGNOSTIC ONLY, nothing is applied.", fontsize=9.5)
    fig.tight_layout(rect=(0, 0, 1, 0.90))
    p = out_dir / "B5_pujet_id.png"
    fig.savefig(p, dpi=140); plt.close(fig)
    b5["png"] = str(p); report["results"]["B5"] = b5
    print(f"wrote {p}", flush=True)

    out = out_dir / "partB_pileup_results.json"
    out.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    print(f"\nwrote {out}")

    print("\n=== B2: data/MC at >=3 jets vs PV_npvsGood ===")
    for ch in ("mumu", "ee"):
        if ch in b2 and isinstance(b2[ch], dict):
            print(f"  {ch}: ratios {[round(v,3) for v in b2[ch]['ratio']]}  "
                  f"slope {b2[ch]['slope_per_vertex']}  "
                  f"first->last {b2[ch]['first_to_last']} "
                  f"({b2[ch]['first_to_last_sigma']} sigma)")
    print("\n=== B3: data/MC by threshold (3,4,5+ jet bins) ===")
    for ch in ("mumu", "ee"):
        for thr in ("30", "40", "50"):
            r = b3[ch][thr]["ratio"]
            print(f"  {ch} pT>{thr}: " +
                  "  ".join(f"{NJET_LABELS[i]}={r[i]:.3f}" if r[i] else f"{NJET_LABELS[i]}=-"
                            for i in (3, 4, 5)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
