#!/usr/bin/env python
"""
b-tag re-check (19 Oct 2026), Part 2 aggregation: DeepJet 0.2598 vs 0.25 on
the every-10th-file sample of the 4 data datasets and the 13 MC records.

Inputs (all small, copied from the cluster): the per-job summary.json +
nb.npz (merge_pair.py), production_totals.json (production_totals.py),
sample_files.json, and the delivered data final-state list.

Populations
  "delivered population": what the delivery is built from -- data: DoubleMuon
  inclusive + the other three exclusive; MC: every accepted event (inclusive).
  "kept": of those, the Version B events (e + mu + b <= 4) -- this changes
  with the threshold, because n_b enters the rule.

Per group (dataset / MC record): fraction of jets b-tagged, n_b distribution,
the n_b migration matrix (0/1/2/3+ and "rejected" = Version B rejected), the
yield per final-state group (0b/1b/2b/3b+), and the final states that gain or
lose most. Data vs MC: the fraction of kept events in 1b and 2b.

PROJECTION (UNVERIFIED -- sample based): each group's sample counts are scaled
to its full statistics by s_g = (production population of all files) /
(production population of the sampled files), summed, and a final state passes
if it reaches >= 100 events (raw, as both builders count it) and has at least
one of the 186 mass combinations (otherwise it yields no histogram). Projected
histograms = for each passing final state, the number of the 186 mass
combinations it satisfies (shared physics_calcs function, as the 7 Oct Step D;
an UPPER BOUND). The exact 0.2598 numbers from the production metadata and the
real deliveries (data 103 FS / 1,975 histograms; MC 205 / 4,977) show how good
the projection is.

Every per-file 0.2598 count is also checked against the production metadata
of the same file (the sample must reproduce production exactly).
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT))

TAGS = ("0p2598", "0p25")
WP = {"0p2598": 0.2598, "0p25": 0.25}
DATASETS = ("DoubleMuon", "SingleMuon", "DoubleEG", "MuonEG")
NB_CATS = ("0b", "1b", "2b", "3b+")
MIN_EVENTS = 100
REAL = {"data": {"fs": 103, "hist": 1975}, "mc": {"fs": 205, "hist": 4977}}
INK, INK2, GRID, SURF = "#0b0b0b", "#52514e", "#e6e6e3", "#fcfcfb"
C_T = {"0p2598": "#2a78d6", "0p25": "#eb6834"}          # categorical slots 1, 2
C_GROUPS = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"]


def nb_cat(nb: np.ndarray) -> np.ndarray:
    return np.minimum(nb, 3)


def labels(n_e, n_m, n_j, n_b) -> np.ndarray:
    """exact_final_state_labels' format, e.g. '0e_2m_5j_1b'."""
    return np.char.add(np.char.add(np.char.add(np.char.add(np.char.add(np.char.add(np.char.add(
        n_e.astype(str), "e_"), n_m.astype(str)), "m_"), n_j.astype(str)), "j_"), n_b.astype(str)), "b")


def load_group(files: list[Path]) -> dict:
    parts = defaultdict(list)
    summaries = []
    for d in files:
        z = np.load(d / "nb.npz")
        for k in z.files:
            parts[k].append(z[k])
        summaries.append(json.loads((d / "summary.json").read_text()))
    return {k: np.concatenate(v) for k, v in parts.items()}, summaries


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample-dir", required=True)
    ap.add_argument("--production-totals", required=True)
    ap.add_argument("--sample-files", required=True)
    ap.add_argument("--delivery-json", required=True)
    ap.add_argument("--out-json", required=True)
    ap.add_argument("--out-plots", required=True)
    args = ap.parse_args()
    prod = json.loads(Path(args.production_totals).read_text())
    sample = json.loads(Path(args.sample_files).read_text())
    delivered_fs = set(json.loads(Path(args.delivery_json).read_text())["per_final_state_entries_new"])
    sd = Path(args.sample_dir)

    groups = [(ds, "data") for ds in DATASETS] + [(rid, "mc") for rid in sorted(prod["mc"])]
    res = {"groups": {}, "validation": {}, "sample": {}}
    proj_counts = {k: {t: Counter() for t in TAGS} for k in ("data", "mc")}
    fs_change = {k: {t: Counter() for t in TAGS} for k in ("data", "mc")}
    dm = {k: {t: {"kept": 0.0, "1b": 0.0, "2b": 0.0, "by_nlep": defaultdict(lambda: [0.0, 0.0, 0.0])}
              for t in TAGS} for k in ("data", "mc")}
    mig_tot = {k: np.zeros((5, 5)) for k in ("data", "mc")}
    validation_fail = []

    for g, kind in groups:
        picked = [f for f in sample["files"] if (f["label"] == g if kind == "data" else str(f["record_id"]) == g)]
        dirs = [sd / (f"{g}_{f['record_id']}" if kind == "data" else f"MC_{g}") / f"f{f['file_index']}"
                for f in picked]
        missing = [str(d) for d in dirs if not (d / "summary.json").exists()]
        if missing:
            res["groups"][g] = {"kind": kind, "missing": missing}
            continue
        arr, summ = load_group(dirs)
        pfiles = prod["data"][g] if kind == "data" else prod["mc"][g]
        excluded = set() if kind == "data" else {str(i) for i in prod["mc_norm"][g]["excluded_files"]}
        key_of = (lambda f: str(f["index"])) if kind == "data" else (lambda f: str(f["file_index"]))
        sampled_keys = {key_of(f) for f in picked}
        pop_field = "n_after_gate" if (kind == "mc" or g == "DoubleMuon") else "n_exclusive"
        tot_pop = sum(v[pop_field] for k, v in pfiles.items() if k not in excluded)
        smp_pop = sum(pfiles[k][pop_field] for k in sampled_keys)
        s_g = tot_pop / smp_pop
        frac_read = sum(pfiles[k]["n_read"] for k in sampled_keys) / sum(
            v["n_read"] for k, v in pfiles.items() if k not in excluded)
        res["sample"][g] = {"kind": kind, "n_files_sampled": len(picked), "n_files_total": len(pfiles) - len(excluded),
                            "fraction_of_events_read": frac_read, "population_field": pop_field,
                            "population_sampled": smp_pop, "population_total": tot_pop, "scale": s_g}

        # validation: capture vs run metadata vs production, per file
        for f, s in zip(picked, summ):
            pk = key_of(f)
            r0 = s["runs"]["0p2598"]
            for k in ("n_read", "n_after_gate", "n_exclusive"):
                if r0.get(k) != pfiles[pk].get(k):
                    validation_fail.append(f"{g}/{pk}: {k} sample {r0.get(k)} != production {pfiles[pk].get(k)}")
            for which in ("incl", "excl"):
                a = r0["rare4"][f"final_state_label_event_counts_{'inclusive' if which == 'incl' else 'exclusive'}"]
                b = pfiles[pk][f"rare4_{which}"]
                if {k: v for k, v in a.items() if v} != {k: v for k, v in (b or {}).items() if v}:
                    validation_fail.append(f"{g}/{pk}: rare4 {which} label counts differ from production")
            if not all(s["alignment_checks"].values()):
                validation_fail.append(f"{g}/{pk}: alignment {s['alignment_checks']}")

        n_e, n_m = arr["n_e"].astype(int), arr["n_m"].astype(int)
        pop = np.ones(len(n_e), bool) if pop_field == "n_after_gate" else arr["is_exclusive"]
        w_mc = (arr["genweight"] * prod["mc_norm"][g]["normalisation_factor"]) if kind == "mc" else None
        gres = {"kind": kind, "n_events_accepted": int(len(n_e)), "n_events_population": int(pop.sum()),
                "per_threshold": {}}
        cat = {}
        keep = {}
        for t in TAGS:
            nj, nb = arr[f"n_j_{t}"].astype(int), arr[f"n_b_{t}"].astype(int)
            kp = pop & (n_e + n_m + nb <= 4)
            keep[t] = kp
            cat[t] = np.where(n_e + n_m + nb <= 4, nb_cat(nb), 4)        # 4 = Version B rejected
            lab = labels(n_e[kp], n_m[kp], nj[kp], nb[kp])
            fs = Counter(lab.tolist())
            for fsl, n in fs.items():
                proj_counts[kind][t][fsl] += s_g * n
                fs_change[kind][t][fsl] += s_g * n
            # check: capture-derived kept labels == the run's own rare4 label counts
            run = summ and [s["runs"][t]["rare4"] for s in summ]
            ref = Counter()
            for r4 in run:
                ref.update(r4["final_state_label_event_counts_inclusive" if pop_field == "n_after_gate"
                              else "final_state_label_event_counts_exclusive"])
            # the driver's exclusive label counts also list labels with 0 events; ignore those
            if {k: v for k, v in ref.items() if v} != {k: v for k, v in fs.items() if v}:
                validation_fail.append(f"{g} {t}: captured kept labels != run metadata rare4 labels")
            jets = int((nj + nb).sum())
            yield_grp = {c: int(((nb_cat(nb) == i) & kp).sum()) for i, c in enumerate(NB_CATS)}
            entry = {"jets_total": jets, "bjets_total": int(nb.sum()),
                     "fraction_jets_btagged": nb.sum() / jets if jets else None,
                     "n_kept": int(kp.sum()), "n_version_b_rejected": int((pop & ~kp).sum()),
                     "nb_distribution_population": {c: int(((nb_cat(nb) == i) & pop).sum())
                                                    for i, c in enumerate(NB_CATS)},
                     "yield_kept_by_group": yield_grp, "n_final_states": len(fs)}
            if w_mc is not None:
                entry["weighted_yield_kept_by_group"] = {c: float(w_mc[(nb_cat(nb) == i) & kp].sum())
                                                         for i, c in enumerate(NB_CATS)}
            gres["per_threshold"][t] = entry
            # data vs MC, full-statistics weights
            ww = (w_mc * s_g) if w_mc is not None else np.full(len(n_e), s_g)
            nlep = np.minimum(n_e + n_m, 3)
            dm[kind][t]["kept"] += ww[kp].sum()
            dm[kind][t]["1b"] += ww[kp & (nb == 1)].sum()
            dm[kind][t]["2b"] += ww[kp & (nb == 2)].sum()
            for L in (1, 2, 3):
                m = kp & (nlep == L)
                acc = dm[kind][t]["by_nlep"][L]
                acc[0] += ww[m].sum(); acc[1] += ww[m & (nb == 1)].sum(); acc[2] += ww[m & (nb == 2)].sum()
        mig = np.zeros((5, 5), dtype=np.int64)
        np.add.at(mig, (cat["0p2598"][pop], cat["0p25"][pop]), 1)
        gres["migration_raw"] = mig.tolist()
        mw = np.zeros((5, 5))
        ww = (w_mc * s_g) if w_mc is not None else np.full(len(n_e), s_g)
        np.add.at(mw, (cat["0p2598"][pop], cat["0p25"][pop]), ww[pop])
        mig_tot[kind] += mw
        a, b = gres["per_threshold"]["0p2598"], gres["per_threshold"]["0p25"]
        gres["relative_change"] = {
            "fraction_jets_btagged": b["fraction_jets_btagged"] / a["fraction_jets_btagged"] - 1,
            "bjets_total": b["bjets_total"] / a["bjets_total"] - 1 if a["bjets_total"] else None,
            "yield_kept_by_group": {c: (b["yield_kept_by_group"][c] / a["yield_kept_by_group"][c] - 1)
                                    if a["yield_kept_by_group"][c] else None for c in NB_CATS},
            "n_kept": b["n_kept"] / a["n_kept"] - 1,
        }
        res["groups"][g] = gres

    # final states that gain / lose most (projected full statistics)
    for kind in ("data", "mc"):
        a, b = fs_change[kind]["0p2598"], fs_change[kind]["0p25"]
        rows = [{"final_state": f, "proj_0p2598": a.get(f, 0.0), "proj_0p25": b.get(f, 0.0),
                 "delta": b.get(f, 0.0) - a.get(f, 0.0)} for f in set(a) | set(b)]
        res[f"{kind}_final_states_gain_most"] = sorted(rows, key=lambda r: -r["delta"])[:10]
        res[f"{kind}_final_states_lose_most"] = sorted(rows, key=lambda r: r["delta"])[:10]

    complete = {k: all("per_threshold" in v for v in res["groups"].values() if v["kind"] == k)
                and any(v["kind"] == k for v in res["groups"].values()) for k in ("data", "mc")}
    res["complete"] = complete
    # data vs MC
    res["data_vs_mc"] = {}
    for t in TAGS:
        row = {}
        for kind in ("data", "mc"):
            d = dm[kind][t]
            if not complete[kind]:
                row[kind] = None
                continue
            row[kind] = {"frac_1b": d["1b"] / d["kept"], "frac_2b": d["2b"] / d["kept"],
                         "by_nlep": {str(L): {"frac_1b": v[1] / v[0], "frac_2b": v[2] / v[0]} if v[0] else None
                                     for L, v in d["by_nlep"].items()}}
        res["data_vs_mc"][t] = row
    res["data_vs_mc"]["relative_change"] = {
        kind: ({c: res["data_vs_mc"]["0p25"][kind][c] / res["data_vs_mc"]["0p2598"][kind][c] - 1
                for c in ("frac_1b", "frac_2b")} if complete[kind] else None) for kind in ("data", "mc")}
    res["migration_full_stat_weighted"] = {k: v.tolist() for k, v in mig_tot.items()}
    res["migration_axes"] = list(NB_CATS) + ["rejected"]

    # projection
    from services.calculations import physics_calcs
    from studies.cms_datasets.singleelectron_prep.aggregate_threshold import all_186_combinations
    combos = all_186_combinations()
    _nc = {}

    def ncomb(fs):
        if fs not in _nc:
            _nc[fs] = sum(1 for c in combos if physics_calcs.is_finalstate_contain_combination(fs, c))
        return _nc[fs]
    exact = {"data": Counter(), "mc": Counter()}
    for ds in DATASETS:
        for v in prod["data"][ds].values():
            exact["data"].update(v["rare4_incl"] if ds == "DoubleMuon" else v["rare4_excl"])
    for rid, files in prod["mc"].items():
        exc = {str(i) for i in prod["mc_norm"][rid]["excluded_files"]}
        for k, v in files.items():
            if k not in exc:
                exact["mc"].update(v["rare4_incl"])
    res["projection"] = {}
    for kind in ("data", "mc"):
        if not complete[kind]:
            res["projection"][kind] = {"incomplete": "not every group of this kind finished"}
            continue
        # a final state is a delivered category only if it has >= 100 events AND at least one
        # mass combination (e.g. 0e_1m_0j_0b has 112.5M data events but no histogram)
        ex = {f for f, n in exact[kind].items() if n >= MIN_EVENTS and ncomb(f) > 0}
        p = {}
        for t in TAGS:
            passing = {f for f, n in proj_counts[kind][t].items() if n >= MIN_EVENTS and ncomb(f) > 0}
            p[t] = {"n_final_states_ge100": len(passing), "projected_histograms_upper_bound":
                    sum(ncomb(f) for f in passing), "final_states": sorted(passing)}
        exact_hist = sum(ncomb(f) for f in ex)
        cal = REAL[kind]["hist"] / exact_hist
        p["exact_0p2598_from_production_metadata"] = {"n_final_states_ge100": len(ex),
                                                      "histograms_upper_bound": exact_hist}
        p["real_delivery"] = REAL[kind]
        p["calibration_real_over_upper_bound"] = cal
        p["projected_histograms_calibrated"] = {t: p[t]["projected_histograms_upper_bound"] * cal for t in TAGS}
        p["fs_projected_0p2598_vs_exact"] = {
            "only_projected": sorted(set(p["0p2598"]["final_states"]) - ex),
            "only_exact": sorted(ex - set(p["0p2598"]["final_states"]))}
        p["fs_0p25_vs_0p2598_projected"] = {
            "gained": sorted(set(p["0p25"]["final_states"]) - set(p["0p2598"]["final_states"])),
            "lost": sorted(set(p["0p2598"]["final_states"]) - set(p["0p25"]["final_states"]))}
        if kind == "data":
            p["data_fs_0p2598_exact_vs_delivered_list"] = {"same": ex == delivered_fs}
        res["projection"][kind] = p
    res["validation"] = {"n_failures": len(validation_fail), "failures": validation_fail[:50]}
    Path(args.out_json).write_text(json.dumps(res, indent=1, default=float))
    plots(res, Path(args.out_plots))
    print_summary(res)
    return 0


def style(ax):
    ax.set_facecolor(SURF)
    ax.grid(axis="y", color=GRID, lw=0.6)
    ax.set_axisbelow(True)
    ax.tick_params(colors=INK2)
    for s in ax.spines.values():
        s.set_color("#c9c8c3")
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)


def plots(res: dict, out: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    out.mkdir(parents=True, exist_ok=True)
    gr = {g: v for g, v in res["groups"].items() if "per_threshold" in v}

    # 1. b-multiplicity, data vs MC, both thresholds (full-statistics weights)
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.6), facecolor=SURF)
    mw = {k: np.array(v) for k, v in res["migration_full_stat_weighted"].items()}
    x = np.arange(5)
    for ax, kind, title in ((axes[0], "data", "Data (4 datasets, delivered population)"),
                            (axes[1], "mc", "MC (13 records, weighted)")):
        if not res["complete"][kind]:
            ax.set_title(f"{title}: not complete", color=INK, fontsize=10)
            continue
        for i, t in enumerate(TAGS):
            v = mw[kind].sum(axis=1) if t == "0p2598" else mw[kind].sum(axis=0)
            ax.bar(x + (i - 0.5) * 0.38, v / v.sum(), 0.36, color=C_T[t], label=f"DeepJet > {WP[t]}",
                   edgecolor=SURF, lw=2)
        ax.set_yscale("log")
        ax.set_xticks(x, ["0 b", "1 b", "2 b", "3+ b", "rejected\n(e+μ+b > 4)"])
        ax.set_ylabel("fraction of events", color=INK)
        ax.set_title(title, color=INK, fontsize=10)
        ax.legend(frameon=False, fontsize=8)
        style(ax)
    fig.suptitle("b-jet multiplicity at DeepJet 0.2598 vs 0.25 (sample, scaled to full statistics)",
                 color=INK, fontsize=11)
    fig.savefig(out / "btag_nb_multiplicity_data_vs_mc.png", dpi=130, bbox_inches="tight", facecolor=SURF)
    plt.close(fig)

    # 2. relative yield change per final-state group, per data dataset and summed MC
    fig, ax = plt.subplots(figsize=(10, 4.6), facecolor=SURF)
    series = [(ds, gr[ds]["relative_change"]["yield_kept_by_group"]) for ds in DATASETS if ds in gr]
    a = {c: sum(v["per_threshold"]["0p2598"]["weighted_yield_kept_by_group"][c] *
                res["sample"][g]["scale"] for g, v in gr.items() if v["kind"] == "mc") for c in NB_CATS}
    b = {c: sum(v["per_threshold"]["0p25"]["weighted_yield_kept_by_group"][c] *
                res["sample"][g]["scale"] for g, v in gr.items() if v["kind"] == "mc") for c in NB_CATS}
    if res["complete"]["mc"]:
        series.append(("MC (weighted)", {c: b[c] / a[c] - 1 if a[c] else None for c in NB_CATS}))
    xs = np.arange(len(NB_CATS))
    wdt = 0.8 / len(series)
    for i, (name, rc) in enumerate(series):
        vals = [100 * (rc[c] or 0) for c in NB_CATS]
        ax.bar(xs + (i - (len(series) - 1) / 2) * wdt, vals, wdt * 0.92, color=C_GROUPS[i], label=name)
    ax.axhline(0, color=INK2, lw=0.8)
    ax.set_xticks(xs, ["0b", "1b", "2b", "3b+"])
    ax.set_ylabel("yield change, 0.25 vs 0.2598 [%]", color=INK)
    ax.set_title("Kept (Version B) events per b-jet group: change when DeepJet 0.2598 → 0.25",
                 color=INK, fontsize=10)
    ax.legend(frameon=False, fontsize=8, ncol=3)
    style(ax)
    fig.savefig(out / "btag_yield_change_by_group.png", dpi=130, bbox_inches="tight", facecolor=SURF)
    plt.close(fig)

    # 3. fraction of jets b-tagged, per group
    names = [g for g in gr]
    lab = [g if gr[g]["kind"] == "data" else f"MC {g}" for g in names]
    fig, ax = plt.subplots(figsize=(9, 0.32 * len(names) + 1.5), facecolor=SURF)
    y = np.arange(len(names))
    for i, t in enumerate(TAGS):
        ax.barh(y + (i - 0.5) * 0.4, [100 * gr[g]["per_threshold"][t]["fraction_jets_btagged"] for g in names],
                0.38, color=C_T[t], label=f"DeepJet > {WP[t]}")
    for yy, g in zip(y, names):
        ax.text(100 * gr[g]["per_threshold"]["0p25"]["fraction_jets_btagged"] + 0.3, yy + 0.2,
                f"+{100 * gr[g]['relative_change']['fraction_jets_btagged']:.1f}%", va="center",
                fontsize=7, color=INK2)
    ax.set_yticks(y, lab, fontsize=8)
    ax.invert_yaxis()
    ax.set_xlabel("selected jets that are b-tagged [%] (raw)", color=INK)
    ax.set_xlim(0, 1.15 * max(100 * gr[g]["per_threshold"]["0p25"]["fraction_jets_btagged"] for g in names))
    ax.legend(frameon=False, fontsize=8, loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=2)
    ax.grid(axis="x", color=GRID, lw=0.6)
    style(ax)
    ax.grid(axis="y", visible=False)
    fig.savefig(out / "btag_fraction_jets_tagged.png", dpi=130, bbox_inches="tight", facecolor=SURF)
    plt.close(fig)

    # 4. migration matrices (row-normalised), data vs MC
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.6), facecolor=SURF)
    for ax, kind, title in ((axes[0], "data", "Data"), (axes[1], "mc", "MC (weighted)")):
        if not res["complete"][kind]:
            ax.set_title(f"{title}: not complete", color=INK, fontsize=10)
            continue
        m = mw[kind]
        rn = m / np.where(m.sum(axis=1, keepdims=True) > 0, m.sum(axis=1, keepdims=True), 1)
        ax.imshow(rn, cmap="Blues", vmin=0, vmax=1)
        for i in range(5):
            for j in range(5):
                if m[i].sum() > 0:
                    ax.text(j, i, f"{100 * rn[i, j]:.2f}%" if rn[i, j] < 0.9995 else "100%", ha="center",
                            va="center", fontsize=7, color="white" if rn[i, j] > 0.6 else INK)
        ticks = ["0b", "1b", "2b", "3b+", "rej."]
        ax.set_xticks(range(5), ticks)
        ax.set_yticks(range(5), ticks)
        ax.set_xlabel("at 0.25", color=INK)
        ax.set_ylabel("at 0.2598", color=INK)
        ax.set_title(f"{title}: where events at 0.2598 go at 0.25 (row %)", color=INK, fontsize=10)
        ax.tick_params(colors=INK2)
    fig.savefig(out / "btag_migration_data_vs_mc.png", dpi=130, bbox_inches="tight", facecolor=SURF)
    plt.close(fig)


def print_summary(res: dict) -> None:
    print("validation failures:", res["validation"]["n_failures"], res["validation"]["failures"][:5])
    for g, s in res["sample"].items():
        print(f"{g:<11} files {s['n_files_sampled']}/{s['n_files_total']}  events read {100 * s['fraction_of_events_read']:.1f}%  scale {s['scale']:.2f}")
    for g, v in res["groups"].items():
        if "relative_change" not in v:
            print(g, "MISSING", v.get("missing", [])[:2])
            continue
        rc = v["relative_change"]
        print(f"{g:<11} b-tag frac {100 * v['per_threshold']['0p2598']['fraction_jets_btagged']:.2f}% -> "
              f"{100 * v['per_threshold']['0p25']['fraction_jets_btagged']:.2f}% ({100 * rc['fraction_jets_btagged']:+.2f}%)  "
              f"kept {100 * rc['n_kept']:+.3f}%  yields " + " ".join(
                  f"{c}:{100 * x:+.2f}%" if x is not None else f"{c}:-" for c, x in rc["yield_kept_by_group"].items()))
    print(json.dumps(res["data_vs_mc"], indent=1, default=float)[:1500])
    for kind in ("data", "mc"):
        p = res["projection"][kind]
        if "incomplete" in p:
            print(kind, "projection: incomplete")
            continue
        print(kind, {t: (p[t]["n_final_states_ge100"], p[t]["projected_histograms_upper_bound"]) for t in TAGS},
              "exact", p["exact_0p2598_from_production_metadata"], "real", p["real_delivery"],
              "calibrated", {t: round(v) for t, v in p["projected_histograms_calibrated"].items()},
              "fs changes", {k: len(v) for k, v in p["fs_0p25_vs_0p2598_projected"].items()},
              "proj vs exact", {k: len(v) for k, v in p["fs_projected_0p2598_vs_exact"].items()})


if __name__ == "__main__":
    raise SystemExit(main())
