#!/usr/bin/env python
"""
Peak fix step 6, Z-peak data/MC ratios (18-19 Oct 2026). READ-ONLY.

The delivered histograms carry the 110 GeV Z cut, so the Z peak is not in
them; as in the pilot (deliver/compare_data_mc.py, HANDOFF_PILOT.md Part 4),
it is read from the STORED EVENTS of both sides before any post-processing,
with the pilot's own readers:

  DATA  the delivered four-dataset de-duplicated production (DoubleMuon
        inclusive + the other three exclusive), Version B rare4 shards.
  MC    the full run's kept weighted scratch shards (work/fullrun_20261017/
        scratch_default, `_mcw` = final weights), all 13 records, restricted
        to the four data acceptance flags. The peak fix does not touch
        anything below 110 GeV or any weight, so these are the weights of
        the new build too.

Ratios (absolute normalisation, nothing rescaled):
  * 60-120 GeV, all jet multiplicities (the pilot's P1/P2 definition;
    pilot: mumu 1.0337, ee 0.9534 with DY + ttbar + ggH only)
  * 76-106 GeV, 0 light jets (the pilot's 0-jet Z-window bin; pilot:
    mumu 1.035, ee 0.954)
  * 60-120 GeV, 0 light jets
One plot per flavour, 0 jets, with a ratio panel.

Difference to the pilot, stated: the full-run scratch was pruned at >= 100
raw entries per final state (93 sparse final states removed); the pilot's
comparison scratch was not pruned. Final states with 2 leptons and 0 jets
are far above that threshold.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from studies.cms_mc_weights_v3.deliver import compare_data_mc as C  # noqa: E402
from studies.cms_mc_weights_v3.deliver.compare_data_mc import read_data, read_mc  # noqa: E402
from studies.cms_mc_weights_v3.peakfix.common import GROUPS, INK, INK2, LUMI, SURF, style  # noqa: E402

_read_in_place = C.read_shard_arrays


def read_copy(shard_path: str) -> dict:
    """Read a shard from a private copy (the db and its -wal/-shm side files)
    in $TMPDIR, so the read-only inputs are never opened in place -- opening a
    WAL database can write its -shm index even with mode=ro."""
    tmp = Path(tempfile.mkdtemp(dir=os.environ.get("TMPDIR")))
    try:
        dst = tmp / Path(shard_path).name
        for suffix in ("", "-wal", "-shm"):
            src = Path(shard_path + suffix)
            if src.exists():
                shutil.copyfile(src, Path(str(dst) + suffix))
        return _read_in_place(str(dst))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


C.read_shard_arrays = read_copy   # read_data/read_mc look it up in C's namespace

PILOT = {"mumu": {"60_120_all_jets": 1.0337, "76_106_0j": 1.035},
         "ee": {"60_120_all_jets": 0.9534, "76_106_0j": 0.954}}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-runs-dir", required=True)
    ap.add_argument("--mc-scratch-dir", required=True)
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args()
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)

    want = {"m0m1", "e0e1"}

    def keep(im, c):
        return (im == "m0m1" and c["e"] == 0 and c["m"] == 2) or (im == "e0e1" and c["e"] == 2 and c["m"] == 0)

    data = read_data(Path(args.data_runs_dir), want, keep)
    n_data_shards = data.pop("_n_shards")
    mc = read_mc(Path(args.mc_scratch_dir), want, keep)
    n_mc_shards = mc.pop("_n_shards")
    n_union = mc.pop("_n_entries_dropped_by_event_union")
    print(f"{n_data_shards} data shards, {n_mc_shards} MC shards, {n_union:,} MC entries dropped by the union",
          flush=True)

    res = {"data_runs_dir": args.data_runs_dir, "mc_scratch_dir": args.mc_scratch_dir,
           "n_data_shards": n_data_shards, "n_mc_shards": n_mc_shards,
           "n_mc_entries_dropped_by_event_union": n_union, "pilot": PILOT, "ratios": {}, "plots": {}}
    edges = np.arange(60.0, 120.0 + 1e-9, 2.0)
    for flav, im in (("mumu", "m0m1"), ("ee", "e0e1")):
        if im not in data:
            res["ratios"][flav] = {"missing": f"no {im} entries in the data shards"}
            continue
        dm, djb = data[im]
        r = {}
        for tag, lo, hi, zero_j in (("60_120_all_jets", 60, 120, False), ("76_106_0j", 76, 106, True),
                                    ("60_120_0j", 60, 120, True)):
            dsel = (dm >= lo) & (dm <= hi) & ((djb[:, 0] == 0) if zero_j else True)
            d = float(dsel.sum())
            m_tot, m_var, by = 0.0, 0.0, {}
            for rid, by_im in mc.items():
                if im not in by_im:
                    continue
                mm, ww, jb = by_im[im]
                sel = (mm >= lo) & (mm <= hi) & ((jb[:, 0] == 0) if zero_j else True)
                by[rid] = float(ww[sel].sum())
                m_tot += by[rid]
                m_var += float((ww[sel] ** 2).sum())
            r[tag] = {"data": d, "mc": m_tot, "mc_stat_error": m_var ** 0.5,
                      "data_over_mc": d / m_tot if m_tot else None,
                      "stat_error": (d ** 0.5 / m_tot) if m_tot else None,
                      "pilot": PILOT[flav].get(tag), "mc_by_record": by}
        res["ratios"][flav] = r

        # plot, 0 jets
        dsel = djb[:, 0] == 0
        dc, _ = np.histogram(dm[dsel], bins=edges)
        fig, (ax, axr) = plt.subplots(2, 1, figsize=(7.5, 6), sharex=True,
                                      gridspec_kw={"height_ratios": [3, 1], "hspace": 0.05})
        base = np.zeros(len(edges) - 1)
        tot = np.zeros(len(edges) - 1)
        parts = []
        for label, recs, color in GROUPS:
            v = np.zeros(len(edges) - 1)
            for rid in recs:
                by_im = mc.get(str(rid), {})
                if im in by_im:
                    mm, ww, jb = by_im[im]
                    s = jb[:, 0] == 0
                    v += np.histogram(mm[s], bins=edges, weights=ww[s])[0]
            parts.append((label, color, v))
            tot += v
        for label, color, v in sorted(parts, key=lambda p: p[2].sum()):
            vv = np.clip(v, 0, None)
            if vv.sum() <= 0:
                continue
            ax.fill_between(np.repeat(edges, 2)[1:-1], np.repeat(base, 2), np.repeat(base + vv, 2),
                            color=color, lw=0, label=f"{label}  ({v.sum():,.4g})")
            base += vv
        c = 0.5 * (edges[:-1] + edges[1:])
        ax.errorbar(c, dc, yerr=np.sqrt(dc), fmt="o", ms=3, color=INK, lw=0.9, label=f"data  ({dc.sum():,.0f})")
        ax.set_yscale("log")
        ax.set_ylabel("events / 2 GeV", color=INK)
        ax.set_title(f"Z peak, {'μμ' if flav == 'mumu' else 'ee'}, 0 jets — stored events before the Z cut\n"
                     f"absolute normalisation, L = {LUMI} fb⁻¹, all 13 MC records, nothing rescaled",
                     fontsize=9, color=INK)
        hh, ll = ax.get_legend_handles_labels()
        ax.legend(hh[::-1], ll[::-1], fontsize=7, frameon=False, loc="upper left")
        style(ax)
        with np.errstate(divide="ignore", invalid="ignore"):
            axr.errorbar(c, np.where(tot > 0, dc / tot, np.nan), yerr=np.where(tot > 0, np.sqrt(dc) / tot, np.nan),
                         fmt="o", ms=2.6, color=INK, lw=0.8)
        axr.axhline(1.0, color=INK2, ls="--", lw=0.8)
        axr.set_ylim(0.6, 1.4)
        axr.set_ylabel("data / MC", color=INK)
        axr.set_xlabel(f"{'dimuon' if flav == 'mumu' else 'dielectron'} mass [GeV]", color=INK)
        style(axr)
        p = out / f"zpeak_{flav}_0j.png"
        fig.savefig(p, dpi=130, bbox_inches="tight", facecolor=SURF)
        plt.close(fig)
        res["plots"][flav] = p.name

    (out / "z_peak_ratio.json").write_text(json.dumps(res, indent=1, default=str))
    for flav, r in res["ratios"].items():
        for tag, x in r.items():
            if not isinstance(x, dict):
                print(flav, tag, x)
                continue
            print(f"{flav:5} {tag:16} data {x['data']:>12,.0f}  MC {x['mc']:>14,.1f}  "
                  f"data/MC {x['data_over_mc']}  ± {x['stat_error']}  (pilot {x['pilot']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
