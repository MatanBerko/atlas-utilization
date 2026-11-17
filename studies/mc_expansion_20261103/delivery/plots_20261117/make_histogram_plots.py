#!/usr/bin/env python
"""One picture per MC histogram of the final delivery (17 Nov 2026). Report only: reads the delivered files, writes a
NEW folder (refuses to write into an existing one).

Per histogram name of the summed MC file (331):
  * top: MC stacked by process group (built from the 71 per-sample files), MC statistical uncertainty (sqrt of the
    summed Sumw2) as a hatched band, data (25 Oct, uncropped) as black points with Poisson (Garwood 68 %) errors;
    log y, "Events / 10 GeV";
  * x range: from common_start_gev of the start-mass CSV (MC-only names: the MC's first filled bin) to the last bin
    filled in data or MC;
  * bottom (names with data only): data/MC with the data errors, the MC uncertainty band around 1, range 0-2.5;
  * text: the name, the final state in words, the dataset label, the missing MC, the data and MC integrals from the
    common start and their ratio.
One PDF with contents pages, then the 331 plots ordered by number of leptons, final state, mass combination.

    python make_histogram_plots.py --data <data uncropped.root> --mc-dir <deliver_20261109> --out <new folder>
        --evidence-dir <dir for the check JSON and the page list>
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
import re
from pathlib import Path

import numpy as np

MC_SUMMED = "CMS_Run2016GH_MC-summedSM-71samples_16p393invfb_build2026-11-14_mc.root"
PDF_NAME = "CMS_Run2016GH_MC-summedSM-71samples_vs_data_16p393invfb_plots_2026-11-17.pdf"
NAME = re.compile(r"^ROI_mass_([a-z0-9]+)_cat_(\d+)ex_(\d+)mx_(\d+)jx_(\d+)bx_width_10\.0$")
REC = re.compile(r"-rec(\d+)_")

# Process groups (records as in the MC README sample table). Fixed order = fixed colour = stacking order (bottom
# first). Colours: the dataviz reference categorical palette, 8 slots in its validated order (light mode, adjacent
# pairs: CVD dE >= 9.1, normal-vision dE >= 19.6); every colour is named in the legend.
GROUPS = [
    ("Drell-Yan", "#2a78d6", [35631, 35669]),
    ("W+jets", "#eb6834", [69715, 69717, 69719]),
    (r"$t\bar{t}$", "#1baf7a", [67801, 67993, 67841]),
    ("single top", "#eda100", [64635, 64659, 64759, 64839, 64895]),
    ("dibosons", "#e87ba4", [72658, 72676, 72738, 72740, 72742, 72752, 75567, 75573, 75589]),
    (r"tribosons, $t\bar{t}$X, $t\bar{t}t\bar{t}$, rare top", "#008300",
     [72701, 72711, 72761, 75600, 67645, 67691, 68045, 68073, 68083, 68185, 68187, 68206, 68325, 64873]),
    (r"Z$\to\nu\nu$", "#6250d6", [74894, 74896, 74898, 74900, 74902, 74904, 74906]),
    ("Higgs", "#e34948", [37432, 37446, 37474, 37604, 37616, 37728, 40062, 40095, 41873, 41877, 41914, 68571, 68591,
                          68601, 68731, 68741, 68847, 70301, 70383, 70451, 70453, 71145, 71227, 71295, 71297, 74292,
                          74682, 74684]),
]
GROUP_PLAIN = ["Drell-Yan", "W+jets", "ttbar", "single top", "dibosons",
               "tribosons, ttbar+X (ttW, ttZ, ttH), four top, rare top (tZq, tWll)", "Z->nunu", "Higgs"]
INK, INK2, GRID, SURF = "#0b0b0b", "#52514e", "#e6e6e3", "#fcfcfb"
LABEL = "CMS Open Data 2016 (Run G+H), 16.4 fb$^{-1}$, $\\sqrt{s}$ = 13 TeV"
MISSING = "MC missing: QCD multijet, photon processes"
OBJ = {"e": "electron", "m": "muon", "j": "jet", "b": "b-jet"}


def read(path):
    import uproot
    out = {}
    with uproot.open(path) as f:
        for k in f.keys(cycle=False):
            if NAME.match(k):
                h = f[k]
                out[k] = (np.asarray(h.values(), float), np.asarray(h.variances(), float),
                          np.asarray(h.axis().edges(), float))
    return out


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def plural(n, word):
    return f"{n} {word}{'' if n == 1 else 's'}"


def final_state_words(e, m, j, b):
    parts = [plural(n, OBJ[k]) for k, n in (("e", e), ("m", m), ("j", j), ("b", b)) if n]
    if not j and not b:
        parts.append("no jets")
    return " + ".join(parts)


def combination_words(combo):
    objs = re.findall(r"([emjb])(\d+)", combo)
    return "mass of " + " + ".join(f"{OBJ[k]} {int(i) + 1}" for k, i in objs)


def sort_key(name):
    m = NAME.match(name)
    e, mu, j, b = (int(x) for x in m.group(2, 3, 4, 5))
    return (e + mu, e, mu, j, b, len(m.group(1)), m.group(1))


def garwood(n):
    from scipy.stats import chi2
    n = np.asarray(n, float)
    lo = np.where(n > 0, n - chi2.ppf(0.15865, 2 * n) / 2, 0.0)
    hi = chi2.ppf(0.84135, 2 * (n + 1)) / 2 - n
    return lo, hi


def first_last(v):
    nz = np.nonzero(v != 0)[0]
    return (int(nz[0]), int(nz[-1])) if nz.size else (None, None)


def main() -> int:
    ap = argparse.ArgumentParser()
    for a in ("--data", "--mc-dir", "--out", "--evidence-dir"):
        ap.add_argument(a, required=True)
    a = ap.parse_args()
    out, ev = Path(a.out), Path(a.evidence_dir)
    out.mkdir(parents=False, exist_ok=False)
    (out / "pngs").mkdir()
    for p in (ev / "plots_check_20261117.json", ev / "plots_index_20261117.csv"):
        if p.exists():
            raise SystemExit(f"refusing to overwrite {p}")

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_pdf import PdfPages
    from matplotlib.patches import Patch

    mcdir = Path(a.mc_dir)
    summed = read(mcdir / MC_SUMMED)
    data = read(a.data)
    csv_path = mcdir / f"{MC_SUMMED}.start_masses.csv"
    sm = {r["histogram"]: r for r in csv.DictReader(open(csv_path))}
    rec_group = {str(r): gi for gi, (_, _, recs) in enumerate(GROUPS) for r in recs}
    per_files = sorted((mcdir / "per_sample").glob("*_mc.root"))
    assert len(per_files) == 71 and len(rec_group) == 71, (len(per_files), len(rec_group))
    groups = {}          # name -> (8, nbins) group contents
    for p in per_files:
        gi = rec_group[REC.search(p.name).group(1)]
        for k, (v, _, _) in read(p).items():
            groups.setdefault(k, np.zeros((len(GROUPS), len(v))))[gi] += v

    names = sorted(summed, key=sort_key)
    assert len(names) == 331, len(names)
    n_contents = int(np.ceil(len(names) / 48))
    page = {n: n_contents + i + 1 for i, n in enumerate(names)}
    check = {"n_names": len(names), "stack_vs_summed_max_rel_diff": 0.0, "stack_vs_summed_worst": None,
             "integrals": {}}

    plt.rcParams.update({"font.family": "DejaVu Sans", "axes.edgecolor": INK2, "axes.labelcolor": INK,
                         "xtick.color": INK2, "ytick.color": INK2, "axes.linewidth": 0.8})
    pdf = PdfPages(out / PDF_NAME, metadata={"Title": "CMS Open Data 2016 G+H: MC (71 samples) vs data, all histograms",
                                              "Subject": "CMS-side BumpNet delivery, 17 Nov 2026"})
    # ---------------------------------------------------------------- contents pages
    for c in range(n_contents):
        fig = plt.figure(figsize=(32 / 3, 8), dpi=150, facecolor=SURF)
        fig.text(0.06, 0.95, "Contents" + (f" ({c + 1}/{n_contents})" if n_contents > 1 else ""),
                 fontsize=16, color=INK, weight="bold")
        if c == 0:
            fig.text(0.06, 0.915, "One page per histogram of the MC delivery (331), ordered by number of leptons, "
                     "final state, mass combination. " + MISSING + ".", fontsize=8, color=INK2)
        chunk = names[c * 48:(c + 1) * 48]
        for i, n in enumerate(chunk):
            m = NAME.match(n)
            fs = final_state_words(*(int(x) for x in m.group(2, 3, 4, 5)))
            y = 0.87 - i * 0.0172
            fig.text(0.06, y, n.replace("ROI_", "").replace("_width_10.0", ""), fontsize=7.5, color=INK,
                     family="DejaVu Sans Mono")
            fig.text(0.50, y, fs + ("   [MC only]" if n not in data else ""), fontsize=7.5, color=INK2)
            fig.text(0.94, y, str(page[n]), fontsize=7.5, color=INK, ha="right")
        pdf.savefig(fig, facecolor=SURF)
        plt.close(fig)

    # ---------------------------------------------------------------- one plot per histogram
    rng = random.Random(20261117)
    sample10 = set(rng.sample([n for n in names if n in data], 9) + rng.sample([n for n in names if n not in data], 1))
    for n in names:
        m = NAME.match(n)
        e_, m_, j_, b_ = (int(x) for x in m.group(2, 3, 4, 5))
        sv, ss2, edges = summed[n]
        g = groups[n]
        diff = np.abs(g.sum(axis=0) - sv)
        rel = float(diff.max() / np.abs(sv).max()) if np.abs(sv).max() else float(diff.max())
        if rel > check["stack_vs_summed_max_rel_diff"]:
            check["stack_vs_summed_max_rel_diff"], check["stack_vs_summed_worst"] = rel, n
        has_data = n in data
        mf, ml = first_last(sv)
        if has_data:
            dv = data[n][0]
            assert np.array_equal(data[n][2], edges)
            df, dl = first_last(dv)
            start = int(round(float(sm[n]["common_start_gev"]) / 10.0))
            assert edges[start] == float(sm[n]["common_start_gev"])
            last = max(dl, ml)
        else:
            dv, start, last = None, mf, ml
        sl = slice(start, last + 1)
        x_lo, x_hi = edges[start], edges[last + 1]
        mc_int = float(sv[start:].sum())
        d_int = float(dv[start:].sum()) if has_data else None
        if n in sample10:
            r = sm[n]
            check["integrals"][n] = {
                "plot_data": d_int, "csv_data": float(r["data_from_common_start"]) if has_data else None,
                "plot_mc": mc_int, "csv_mc": float(r["mc_from_common_start"]) if has_data else None,
                "mc_first_filled_gev_csv": float(r["mc_first_filled_gev"]), "plot_x_start_gev": float(x_lo)}

        fig = plt.figure(figsize=(32 / 3, 8), dpi=150, facecolor=SURF)
        if has_data:
            gs = fig.add_gridspec(2, 1, height_ratios=[3, 1], hspace=0.05, left=0.09, right=0.97, top=0.80, bottom=0.08)
            ax, rx = fig.add_subplot(gs[0]), fig.add_subplot(gs[1])
        else:
            gs = fig.add_gridspec(1, 1, left=0.09, right=0.97, top=0.80, bottom=0.08)
            ax, rx = fig.add_subplot(gs[0]), None
        for axx in (ax, rx):
            if axx is not None:
                axx.set_facecolor(SURF)
                axx.grid(axis="y", color=GRID, lw=0.6)
                axx.set_axisbelow(True)
                for s in ("top", "right"):
                    axx.spines[s].set_visible(False)
        x = edges[sl.start:sl.stop + 1]
        bottom = np.zeros(last + 1 - start)
        for gi, (lab, col, _) in enumerate(GROUPS):
            h = np.clip(g[gi, sl], 0, None)      # a group with net negative weight in a bin is drawn as 0
            if not h.any():
                continue
            ax.fill_between(x, np.append(bottom, bottom[-1]), np.append(bottom + h, (bottom + h)[-1]), step="post",
                            color=col, lw=0.4, edgecolor=SURF)
            bottom = bottom + h
        tot, err = sv[sl], np.sqrt(np.clip(ss2[sl], 0, None))
        ax.stairs(tot, x, color=INK, lw=0.9)
        ax.fill_between(x, np.append(tot - err, (tot - err)[-1]), np.append(tot + err, (tot + err)[-1]), step="post",
                        facecolor="none", edgecolor=INK2, hatch="////", lw=0)
        centers = 0.5 * (x[:-1] + x[1:])
        if has_data:
            d = dv[sl]
            lo, hi = garwood(d)
            k = d > 0
            ax.errorbar(centers[k], d[k], yerr=[lo[k], hi[k]], fmt="o", ms=3.2, color=INK, lw=0.8, capsize=0)
        pos = np.concatenate([tot[tot > 0], d[d > 0] if has_data else np.array([])])
        ymax = pos.max() if pos.size else 1.0
        # data are whole events: start at 0.1 so tiny MC tails do not squash the data; MC-only: at most 5 decades
        ymin = 0.1 if has_data else (max(pos.min() * 0.3, ymax * 1e-5) if pos.size else 0.1)
        ymax = max(ymax, ymin * 10)
        ax.set_yscale("log")
        ax.set_ylim(ymin, ymax * 10 ** (0.32 * np.log10(ymax / ymin) + 0.2))   # headroom for the legend
        ax.set_xlim(x_lo, x_hi)
        ax.set_ylabel("Events / 10 GeV", fontsize=11)
        handles = []
        if has_data:
            handles.append(ax.errorbar([], [], yerr=[], fmt="o", ms=3.2, color=INK, label="Data (25 Oct 2026)"))
        handles.append(Patch(facecolor="none", edgecolor=INK2, hatch="////", label="MC stat. uncertainty"))
        handles += [Patch(facecolor=col, edgecolor=SURF, label=lab) for lab, col, _ in reversed(GROUPS)]
        ax.legend(handles=handles, loc="upper right", fontsize=8.5, ncol=2, frameon=False, labelcolor=INK)
        # header (above the axes): name, words, label, integrals, missing
        fig.text(0.09, 0.955, n, fontsize=12.5, color=INK, weight="bold", family="DejaVu Sans Mono")
        fig.text(0.09, 0.925, f"{final_state_words(e_, m_, j_, b_)};  {combination_words(m.group(1))}"
                 + ("   [MC only: no data histogram]" if not has_data else ""), fontsize=10.5, color=INK)
        fig.text(0.09, 0.895, LABEL, fontsize=10, color=INK2)
        if has_data:
            ratio = d_int / mc_int if mc_int else float("nan")
            integ = (f"From the common start {x_lo:.0f} GeV:  data {d_int:,.0f}   MC {mc_int:,.1f}   "
                     f"data/MC {ratio:.3f}")
        else:
            integ = f"From the MC start {x_lo:.0f} GeV:  MC {mc_int:,.2f}"
        fig.text(0.09, 0.865, integ, fontsize=10, color=INK)
        fig.text(0.09, 0.835, MISSING + ".  MC: 71 samples, built 14 Nov 2026.", fontsize=9.5, color="#b3261e")
        fig.text(0.97, 0.955, f"page {page[n]}", fontsize=9, color=INK2, ha="right")
        if rx is not None:
            ok = tot > 0
            rv = np.full_like(tot, np.nan)
            rv[ok] = d[ok] / tot[ok]
            rlo = np.where(ok, lo / np.where(ok, tot, 1), np.nan)
            rhi = np.where(ok, hi / np.where(ok, tot, 1), np.nan)
            band = np.where(ok, err / np.where(ok, tot, 1), 0)
            rx.fill_between(x, np.append(1 - band, 1 - band[-1]), np.append(1 + band, 1 + band[-1]), step="post",
                            facecolor="none", edgecolor=INK2, hatch="////", lw=0)
            rx.axhline(1, color=INK, lw=0.8)
            show = ok & (d > 0) & (rv <= 2.5)
            rx.errorbar(centers[show], rv[show], yerr=[rlo[show], rhi[show]], fmt="o", ms=3, color=INK, lw=0.8)
            over = ok & (rv > 2.5)
            rx.plot(centers[over], np.full(over.sum(), 2.38), marker="^", ls="none", ms=4, color=INK2)
            rx.set_ylim(0, 2.5)
            rx.set_xlim(x_lo, x_hi)
            rx.set_ylabel("Data / MC", fontsize=10)
            rx.set_xlabel("Invariant mass [GeV]", fontsize=11)
            ax.tick_params(labelbottom=False)
        else:
            ax.set_xlabel("Invariant mass [GeV]", fontsize=11)
        fig.savefig(out / "pngs" / f"{n}.png", dpi=150, facecolor=SURF)
        pdf.savefig(fig, facecolor=SURF)
        plt.close(fig)
    n_pages = pdf.get_pagecount()
    pdf.close()

    # ---------------------------------------------------------------- checks, index, README, checksums
    pngs = sorted((out / "pngs").glob("*.png"))
    raw = (out / PDF_NAME).read_bytes()
    check.update({"n_png": len(pngs), "pdf_pages_total": n_pages, "pdf_contents_pages": n_contents,
                  "pdf_plot_pages": n_pages - n_contents,
                  "pdf_type_page_objects": len(re.findall(rb"/Type\s*/Page[^s]", raw))})
    for v in check["integrals"].values():
        v["data_rel_diff"] = (abs(v["plot_data"] - v["csv_data"]) / abs(v["csv_data"])
                              if v["csv_data"] else None)
        v["mc_rel_diff"] = abs(v["plot_mc"] - v["csv_mc"]) / abs(v["csv_mc"]) if v["csv_mc"] else None
    with open(ev / "plots_index_20261117.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["histogram", "final_state", "has_data", "pdf_page"])
        for n in names:
            m = NAME.match(n)
            w.writerow([n, final_state_words(*(int(x) for x in m.group(2, 3, 4, 5))), n in data, page[n]])
    srcs = {"data (25 Oct, uncropped)": Path(a.data), "MC summed (14 Nov)": mcdir / MC_SUMMED,
            "start-mass CSV": csv_path}
    src_lines = "\n".join(f"  {k}:\n    {p.name}\n    sha256 {sha256(p)}" for k, p in srcs.items())
    legend = "\n".join(f"  {col}  {plain}  (records {', '.join(map(str, recs))})"
                       for (lab, col, recs), plain in zip(GROUPS, GROUP_PLAIN))
    (out / "README_plots.txt").write_text(f"""README_plots.txt  --  pictures of every histogram of the CMS MC delivery (17 Nov 2026)
=====================================================================================

WHAT IS HERE
  pngs/<histogram name>.png   one picture per histogram of the summed MC file, {len(names)} in all
                              (1600 x 1200 pixels, 150 dpi); {sum(n in data for n in names)} with data,
                              {sum(n not in data for n in names)} MC-only (four-lepton final states not in the data file)
  {PDF_NAME}
                              the same {len(names)} pictures, one per page, after {n_contents} contents pages
                              (each picture's page number is in the contents and on the picture)
  SHA256SUMS.txt              checksums of every file in this folder

WHAT ONE PICTURE SHOWS
  Top: the simulation (MC), 71 samples stacked by process group (colours below), with its statistical
  uncertainty as a hatched band around the MC total (black line); the CMS data as black points with
  Poisson (68 %) error bars. Logarithmic vertical axis, events per 10 GeV bin.
  Bottom (only when there is data): data divided by MC per bin, with the data errors, the MC
  uncertainty band around 1 and a line at 1; range 0-2.5 (points above 2.5 are shown as triangles at
  the top edge).
  Text: the histogram name, the final state in words, "CMS Open Data 2016 (Run G+H), 16.4 fb-1,
  sqrt(s) = 13 TeV", the integrals of data and MC from the common start and their ratio, and
  "MC missing: QCD multijet, photon processes".
  These are not official CMS results; no CMS label is used.

IMPORTANT: QCD multijet and photon processes are NOT in the MC. Where they matter (single lepton +
  jets above all) the data lie above the MC.

COLOURS (fixed for all pictures; stacking order bottom to top as listed)
{legend}
  A group whose net weight in a bin is negative (negative generator weights) is drawn as zero in that
  bin; the black MC total line, the band and all numbers use the true total.

CROPPING RULE (horizontal range)
  From the common start = the later of the data's and the MC's first filled bin (column
  common_start_gev of the start-mass CSV; the rule of the MC README) to the last bin filled in data
  or MC. MC-only histograms start at the MC's first filled bin.

INTEGRALS ON THE PICTURE
  data = sum of the data bins from the common start to 10,000 GeV; MC = the same for the summed MC
  file; data/MC = their ratio. These equal the columns data_from_common_start and
  mc_from_common_start of the CSV. MC-only: the MC sum from its first filled bin.

SOURCE FILES (read only)
{src_lines}
  plus the 71 per-sample MC files (per_sample/ of the MC delivery) for the stacking; the stacked total
  equals the summed file in every histogram (largest relative difference
  {check['stack_vs_summed_max_rel_diff']:.1e}).

MADE BY
  studies/mc_expansion_20261103/delivery/plots_20261117/make_histogram_plots.py
  (github.com/MatanBerko/atlas-utilization, branch feature/mc-expansion-20261103), 17 Nov 2026.
""")
    files = sorted(p for p in out.rglob("*") if p.is_file() and p.name != "SHA256SUMS.txt")
    (out / "SHA256SUMS.txt").write_text("".join(f"{sha256(p)}  {p.relative_to(out)}\n" for p in files))
    (ev / "plots_check_20261117.json").write_text(json.dumps(check, indent=1) + "\n")
    print(json.dumps({k: v for k, v in check.items() if k != "integrals"}, indent=1))
    for k, v in check["integrals"].items():
        print(k, v)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
