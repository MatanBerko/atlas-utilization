"""
exact-jet-labels task, Step 5: the five required report plots.

All five are built from REAL delivered output, never from synthetic data:
  - the 1 Oct rare4 delivery ROOT file (read-only), and
  - the new exact-labels delivery ROOT file, and
  - the per-job rare4 label counts in each job's job_metadata.json.

Plots produced:
  1. plot_1_4j_old_vs_new.png        -- one 4j histogram, old vs new overlaid.
  2. plot_2_new_high_jet.png         -- one brand-new 5j (or higher) histogram.
  3. plot_3_zcut_110_vs_115.png      -- a same-flavour dilepton histogram near
                                        the Z cut, old (115) vs new (110).
  4. plot_4_outlier_split_moved.png  -- an example where the outlier split moved.
  5. plot_5_lightjet_multiplicity.png-- light-jet multiplicity of accepted
                                        Version B events.

Plots 3 and 4 deliberately pick a final state with <=3 light jets. Step 3
check (c) proved the raw mass arrays are IDENTICAL there, so any difference
between old and new in those plots is caused purely by the post-processing
change (Z cut, outlier split) and not by the relabelling.

Usage:
    python vB_make_report_plots.py --old-root <1oct min26bins .root> \
        --new-root <new delivery .root> \
        --runs-dir <runs_matched_vB_exactlabels_...> \
        --out-dir <where to write the PNGs>
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import uproot  # noqa: E402

BIN_WIDTH_GEV = 10.0
Z_OLD, Z_NEW = 115.0, 110.0

OLD_C = "#B3573F"   # 1 Oct delivery
NEW_C = "#2F6D8E"   # new delivery


def load_root(path: Path) -> dict:
    """name -> (values, edges) for every ROI_* TH1 in the file."""
    out = {}
    with uproot.open(str(path)) as f:
        for key in f.keys():
            obj = f[key]
            name = key.split(";")[0]
            try:
                values = obj.values()
                edges = obj.axis().edges()
            except Exception:
                continue
            out[name] = (np.asarray(values, dtype=float), np.asarray(edges, dtype=float))
    return out


def cat_of(root_key: str):
    """ROI_mass_<combo>_cat_<fs>_width_10 -> (combo, fs)."""
    body = root_key
    if body.startswith("ROI_"):
        body = body[4:]
    if body.endswith(f"_width_{int(BIN_WIDTH_GEV)}"):
        body = body[: -len(f"_width_{int(BIN_WIDTH_GEV)}")]
    if not body.startswith("mass_") or "_cat_" not in body:
        return None, None
    combo, fs = body[len("mass_"):].split("_cat_", 1)
    return combo, fs


def jets_of(fs: str):
    """fs like 0ex_2mx_5jx_0gx_0tx_1bx -> 5"""
    for tok in fs.split("_"):
        if tok.endswith("jx"):
            try:
                return int(tok[:-2])
            except ValueError:
                return None
    return None


def is_same_flavour_dilepton(combo: str) -> bool:
    letters = [c for c in combo if c in "emjgtb"]
    return letters.count("e") >= 2 or letters.count("m") >= 2


def nonempty_range(values, edges):
    idx = np.nonzero(values > 0)[0]
    if len(idx) == 0:
        return None, None
    return float(edges[idx[0]]), float(edges[idx[-1] + 1])


def step_plot(ax, values, edges, color, label, lw=1.6, ls="-"):
    ax.stairs(values, edges, color=color, label=label, linewidth=lw, linestyle=ls)


def finish(fig, ax, title, out_path, xlabel="invariant mass [GeV]"):
    ax.set_xlabel(xlabel)
    ax.set_ylabel(f"events / {int(BIN_WIDTH_GEV)} GeV")
    ax.set_title(title, fontsize=10)
    ax.legend(fontsize=8)
    ax.grid(alpha=0.25, linewidth=0.5)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    print(f"  wrote {out_path}")


# --------------------------------------------------------------------------

def plot_1(old, new, out_dir):
    """A 4j histogram present in BOTH files. The old one has the 5j..9j
    events merged in; the new one is pure 4j."""
    cands = []
    for name in set(old) & set(new):
        combo, fs = cat_of(name)
        if fs is None or jets_of(fs) != 4:
            continue
        o, n = old[name][0], new[name][0]
        if o.sum() < 500:
            continue
        cands.append((abs(o.sum() - n.sum()), name))
    if not cands:
        print("  plot 1: no shared 4j histogram found -- SKIPPED")
        return None
    # the one where the merged-in high-multiplicity events mattered most
    _diff, name = max(cands)
    ov, oe = old[name]
    nv, ne = new[name]
    combo, fs = cat_of(name)

    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    step_plot(ax, ov, oe, OLD_C, f"1 Oct: 4j label (4 or more light jets merged in)"
                                f"  [{int(ov.sum()):,} events]")
    step_plot(ax, nv, ne, NEW_C, f"new: exactly 4 light jets"
                                f"  [{int(nv.sum()):,} events]")
    lo, hi = nonempty_range(ov, oe)
    lo2, hi2 = nonempty_range(nv, ne)
    ax.set_xlim(min(lo, lo2) - 50, max(hi, hi2) + 50)
    ax.set_yscale("log")
    finish(fig, ax, f"Plot 1 - one 4-light-jet histogram, old vs new\n"
                    f"combination {combo}, final state {fs}",
           out_dir / "plot_1_4j_old_vs_new.png")
    return {"plot": 1, "name": name, "combination": combo, "final_state": fs,
            "old_events": int(ov.sum()), "new_events": int(nv.sum()),
            "events_moved_out_to_higher_jet_labels": int(ov.sum() - nv.sum())}


def plot_2(old, new, out_dir):
    """A histogram that exists ONLY in the new delivery because its final
    state has 5 or more light jets."""
    cands = []
    for name in set(new) - set(old):
        combo, fs = cat_of(name)
        j = jets_of(fs) if fs else None
        if j is None or j < 5:
            continue
        cands.append((new[name][0].sum(), name, j))
    if not cands:
        print("  plot 2: no new >=5j histogram found -- SKIPPED")
        return None
    _s, name, j = max(cands)
    nv, ne = new[name]
    combo, fs = cat_of(name)

    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    step_plot(ax, nv, ne, NEW_C,
              f"new final state: exactly {j} light jets  [{int(nv.sum()):,} events]")
    lo, hi = nonempty_range(nv, ne)
    ax.set_xlim(lo - 50, hi + 50)
    finish(fig, ax, f"Plot 2 - a histogram that did not exist before\n"
                    f"combination {combo}, final state {fs} "
                    f"({j} light jets, previously merged into 4j)",
           out_dir / "plot_2_new_high_jet.png")
    return {"plot": 2, "name": name, "combination": combo, "final_state": fs,
            "light_jets": j, "new_events": int(nv.sum()),
            "n_new_high_jet_histograms": len(cands)}


def plot_3(old, new, out_dir):
    """A same-flavour dilepton channel with <=3 light jets: raw arrays are
    identical there, so the only visible change is the Z cut 115 -> 110."""
    cands = []
    for name in set(old) & set(new):
        combo, fs = cat_of(name)
        if fs is None or (jets_of(fs) or 99) > 3:
            continue
        if not is_same_flavour_dilepton(combo):
            continue
        ov, oe = old[name]
        nv, ne = new[name]
        # events gained in the 110-120 GeV bin region
        gained = nv.sum() - ov.sum()
        if gained <= 0:
            continue
        cands.append((gained, name))
    if not cands:
        print("  plot 3: no dilepton channel gained events at the Z cut -- SKIPPED")
        return None
    gained, name = max(cands)
    ov, oe = old[name]
    nv, ne = new[name]
    combo, fs = cat_of(name)

    fig, (ax, ax2) = plt.subplots(1, 2, figsize=(11.0, 4.2),
                                  gridspec_kw={"width_ratios": [2, 1]})
    step_plot(ax, ov, oe, OLD_C, f"1 Oct: Z cut at 115 GeV  [{int(ov.sum()):,}]")
    step_plot(ax, nv, ne, NEW_C, f"new: Z cut at 110 GeV  [{int(nv.sum()):,}]")
    lo, hi = nonempty_range(nv, ne)
    ax.set_xlim(lo - 20, min(hi + 50, lo + 900))
    ax.set_yscale("log")
    ax.axvline(Z_NEW, color=NEW_C, ls=":", lw=1.2)
    ax.axvline(Z_OLD, color=OLD_C, ls=":", lw=1.2)
    ax.set_xlabel("invariant mass [GeV]")
    ax.set_ylabel(f"events / {int(BIN_WIDTH_GEV)} GeV")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.25, linewidth=0.5)

    # zoom on the cut region
    step_plot(ax2, ov, oe, OLD_C, "115 GeV cut")
    step_plot(ax2, nv, ne, NEW_C, "110 GeV cut")
    ax2.axvline(Z_NEW, color=NEW_C, ls=":", lw=1.2, label="110 (a bin edge)")
    ax2.axvline(Z_OLD, color=OLD_C, ls=":", lw=1.2, label="115 (mid-bin)")
    ax2.set_xlim(90, 190)
    ax2.set_xlabel("invariant mass [GeV]")
    ax2.set_title(f"zoom: {int(gained):,} events recovered", fontsize=9)
    ax2.legend(fontsize=7)
    ax2.grid(alpha=0.25, linewidth=0.5)

    fig.suptitle(f"Plot 3 - same-flavour dilepton near the Z cut, old (115) vs new (110)\n"
                 f"combination {combo}, final state {fs} (<=3 light jets, so the raw "
                 f"data is identical)", fontsize=10)
    fig.tight_layout(rect=(0, 0, 1, 0.90))
    fig.savefig(out_dir / "plot_3_zcut_110_vs_115.png", dpi=150)
    plt.close(fig)
    print(f"  wrote {out_dir / 'plot_3_zcut_110_vs_115.png'}")
    return {"plot": 3, "name": name, "combination": combo, "final_state": fs,
            "old_events": int(ov.sum()), "new_events": int(nv.sum()),
            "events_recovered_in_110_115_window": int(gained)}


def plot_4(old, new, out_dir):
    """A channel with <=3 light jets whose highest filled bin moved -- the
    outlier split now cuts on a 10 GeV grid edge."""
    cands = []
    for name in set(old) & set(new):
        combo, fs = cat_of(name)
        if fs is None or (jets_of(fs) or 99) > 3:
            continue
        ov, oe = old[name]
        nv, ne = new[name]
        o_lo, o_hi = nonempty_range(ov, oe)
        n_lo, n_hi = nonempty_range(nv, ne)
        if o_hi is None or n_hi is None or o_hi == n_hi:
            continue
        cands.append((abs(o_hi - n_hi), name, o_hi, n_hi))
    if not cands:
        print("  plot 4: no <=3-light-jet channel changed its upper boundary -- SKIPPED")
        return None
    _d, name, o_hi, n_hi = max(cands)
    ov, oe = old[name]
    nv, ne = new[name]
    combo, fs = cat_of(name)

    fig, ax = plt.subplots(figsize=(7.6, 4.2))
    step_plot(ax, ov, oe, OLD_C,
              f"1 Oct: outlier split on a min-to-max grid  (last bin ends {o_hi:.1f} GeV)")
    step_plot(ax, nv, ne, NEW_C,
              f"new: split aligned to the 10 GeV grid  (last bin ends {n_hi:.1f} GeV)")
    ax.axvline(o_hi, color=OLD_C, ls=":", lw=1.2)
    ax.axvline(n_hi, color=NEW_C, ls=":", lw=1.2)
    lo = min(nonempty_range(ov, oe)[0], nonempty_range(nv, ne)[0])
    ax.set_xlim(lo - 50, max(o_hi, n_hi) + 150)
    ax.set_yscale("log")
    finish(fig, ax,
           f"Plot 4 - the outlier split moved onto a 10 GeV bin edge\n"
           f"combination {combo}, final state {fs} (<=3 light jets, raw data identical)",
           out_dir / "plot_4_outlier_split_moved.png")
    return {"plot": 4, "name": name, "combination": combo, "final_state": fs,
            "old_last_bin_high_edge_gev": o_hi, "new_last_bin_high_edge_gev": n_hi,
            "old_events": int(ov.sum()), "new_events": int(nv.sum()),
            "n_candidates_found": len(cands)}


def plot_5(runs_dir: Path, out_dir):
    """Light-jet multiplicity of accepted Version B events, pooled exactly the
    way the delivery pools them: DoubleMuon INCLUSIVE + SingleMuon EXCLUSIVE."""
    counts = defaultdict(int)
    n_jobs = 0
    for ds, which in (("DoubleMuon", "inclusive"), ("SingleMuon", "exclusive")):
        index = json.loads((runs_dir / f"{ds}_index.json").read_text())
        for idx in index:
            meta_path = runs_dir / ds / f"job_{idx}" / "job_metadata.json"
            if not meta_path.exists():
                print(f"  plot 5: WARNING missing {meta_path}")
                continue
            md = json.loads(meta_path.read_text())
            labels = md["rare4_diagnostics"][f"final_state_label_event_counts_{which}"]
            for label, cnt in labels.items():
                nj = int(label.split("_")[2][:-1])
                counts[nj] += cnt
            n_jobs += 1

    if not counts:
        print("  plot 5: no label counts found -- SKIPPED")
        return None

    ks = sorted(counts)
    vs = [counts[k] for k in ks]
    total = sum(vs)

    fig, ax = plt.subplots(figsize=(7.6, 4.2))
    bars = ax.bar(ks, vs, color=NEW_C, width=0.8)
    for k, v, b in zip(ks, vs, bars):
        if v > 0:
            ax.text(b.get_x() + b.get_width() / 2, v * 1.15,
                    f"{100.0 * v / total:.2g}%", ha="center", fontsize=7, rotation=0)
    ax.axvline(4.5, color=OLD_C, ls="--", lw=1.3)
    ax.text(4.6, max(vs) * 0.3,
            "the 1 Oct delivery merged\n5-9 light jets into the 4j label",
            color=OLD_C, fontsize=8, va="center")
    ax.set_yscale("log")
    ax.set_xticks(ks)
    ax.set_xlabel("number of selected light jets in the event")
    ax.set_ylabel("accepted Version B events")
    ax.set_title(f"Plot 5 - light-jet multiplicity of accepted Version B events\n"
                 f"{total:,} events over {n_jobs} files "
                 f"(DoubleMuon inclusive + SingleMuon exclusive)", fontsize=10)
    ax.grid(alpha=0.25, linewidth=0.5, axis="y")
    fig.tight_layout()
    fig.savefig(out_dir / "plot_5_lightjet_multiplicity.png", dpi=150)
    plt.close(fig)
    print(f"  wrote {out_dir / 'plot_5_lightjet_multiplicity.png'}")
    return {"plot": 5, "n_jobs": n_jobs, "total_events": total,
            "events_by_light_jet_count": {str(k): counts[k] for k in ks},
            "events_with_ge5_light_jets": sum(v for k, v in counts.items() if k >= 5),
            "events_with_ge10_light_jets": sum(v for k, v in counts.items() if k >= 10)}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--old-root", required=True)
    p.add_argument("--new-root", required=True)
    p.add_argument("--runs-dir", required=True)
    p.add_argument("--out-dir", required=True)
    args = p.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"loading old delivery: {args.old_root}")
    old = load_root(Path(args.old_root))
    print(f"  {len(old)} histograms")
    print(f"loading new delivery: {args.new_root}")
    new = load_root(Path(args.new_root))
    print(f"  {len(new)} histograms")

    info = {
        "old_root": args.old_root, "new_root": args.new_root,
        "n_old_histograms": len(old), "n_new_histograms": len(new),
        "n_shared": len(set(old) & set(new)),
        "n_only_old": len(set(old) - set(new)),
        "n_only_new": len(set(new) - set(old)),
    }
    print(f"shared={info['n_shared']} only_old={info['n_only_old']} "
          f"only_new={info['n_only_new']}")

    print("building plots:")
    for fn, args_ in ((plot_1, (old, new, out_dir)), (plot_2, (old, new, out_dir)),
                      (plot_3, (old, new, out_dir)), (plot_4, (old, new, out_dir)),
                      (plot_5, (Path(args.runs_dir), out_dir))):
        res = fn(*args_)
        if res:
            info[f"plot_{res['plot']}"] = res

    (out_dir / "plot_info.json").write_text(json.dumps(info, indent=2, default=str))
    print(f"\nwrote {out_dir / 'plot_info.json'}")
    print(json.dumps(info, indent=2, default=str))


if __name__ == "__main__":
    main()
