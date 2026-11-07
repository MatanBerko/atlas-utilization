#!/usr/bin/env python
"""QCD multijet probe analysis (Part B4, 7 Nov 2026). READ ONLY on every input.

Inputs:
  * the probe outputs: file 0 of 10 QCD records run through the pinned production code (6de9d3e) into
    work/mcexp_20261103/qcd_probe_20261107/runs (job_metadata.json + the inclusive SQLite shards);
  * qcd_portal_20261107.json: per record the portal generator cross section (MiniAOD
    metadata.cross_section.total_value), events and files of the whole sample (read live 7 Nov);
  * the 25 Oct delivered MC (summedSM, 13 samples) and the data counts per final state.

Every yield here is an UNREVIEWED ESTIMATE, for the decision only. No number enters any registry.

Definitions (the same conventions as the MC builder; DESIGN.md D4, R1):
  * an event "enters a histogram" if it is stored, it is in the builder's event union (acceptance bits
    DoubleMuon|SingleMuon|DoubleEG|MuonEG|SingleElectron, build_mc_delivery.event_union_mask), and its final
    state has at least one invariant-mass signature (>= 2 objects). The builder's later mass-range cuts
    (Z cut, peak/split) are NOT applied, so this is an upper bound per final state;
  * full-run weight of an event: w = sigma_pb * 1000 * L * genWeight / Sigma_w(sample), with
    Sigma_w(sample) ~= Sigma_w(file 0) * N_events(sample) / N_events(file 0) (ESTIMATE: file 0 only);
  * full-sample weighted yield = sigma * 1000 * L * Sigma_genWeight(union, file 0) / Sigma_w(file 0);
  * R1: the portal total_value is used as is (matching efficiency NOT applied again).

    python analyze_qcd_probe.py --probe <dir> --portal qcd_portal_20261107.json --mc-root <summedSM.root>
        --data-counts analysis.json --lumi 16.393 --out <dir>
"""
from __future__ import annotations

import argparse
import io
import json
import re
import sqlite3
import zlib
from collections import defaultdict
from pathlib import Path

import numpy as np

UNION_BITS = 1 | 2 | 4 | 8 | 64      # build_mc_delivery.MC_ACC_BITS_DELIVERY_UNION (driver bits)
SIG_RE = re.compile(r"^MC_record(\d+)_file(\d+)_FS_(\d+)e_(\d+)m_(\d+)j_(\d+)b_IM_([a-z0-9]+)(_mcraw_[a-z0-9]+)?$")


def read_shard(path: Path) -> dict:
    """{signature: concatenated numpy array} of one SQLite shard, opened read-only."""
    con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    out = defaultdict(list)
    for sig, payload in con.execute("select signature, payload from array_chunks order by id"):
        out[sig].append(np.load(io.BytesIO(zlib.decompress(payload)), allow_pickle=False))
    con.close()
    return {k: np.concatenate(v) for k, v in out.items()}


def hist_name(fs: tuple, im: str) -> str:
    e, m, j, b = fs
    return f"ROI_mass_{im}_cat_{e}ex_{m}mx_{j}jx_{b}bx_width_10.0"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--probe", required=True)
    ap.add_argument("--portal", required=True)
    ap.add_argument("--mc-root", required=True)
    ap.add_argument("--data-counts", required=True)
    ap.add_argument("--lumi", type=float, required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    import uproot

    portal = json.loads(Path(a.portal).read_text())["records"]
    data_counts = {k: sum(v.values()) for k, v in
                   json.loads(Path(a.data_counts).read_text())["dataset_shares_by_final_state"].items()}
    mc = uproot.open(a.mc_root)
    mc_names = {k.split(";")[0] for k in mc.keys()}
    mc_cache = {}

    def mc_hist(name):
        if name not in mc_cache:
            mc_cache[name] = mc[name].to_numpy() if name in mc_names else None
        return mc_cache[name]

    def mc_fs_yield(fs):
        # weighted MC events of a final state = the integral of one of its histograms (each event once)
        best = None
        for n in mc_names:
            if n.endswith(f"_cat_{fs[0]}ex_{fs[1]}mx_{fs[2]}jx_{fs[3]}bx_width_10.0"):
                v, _ = mc_hist(n)
                s = float(v.sum())
                best = s if best is None else max(best, s)
        return best

    result = {"what": "QCD probe, file 0 per record. UNREVIEWED ESTIMATE, for the decision only.",
              "lumi_fb": a.lumi, "records": {}}
    mc_fs_cache = {}
    for rid, p in portal.items():
        jd = Path(a.probe) / f"record{rid}" / "job_0"
        meta = json.loads((jd / "job_metadata.json").read_text())
        mcd = meta["mc_diagnostics"]
        sigma_pb = float(p["xs"]["total_value"])
        n_file, n_sample = meta["n_read"], p["events"]
        sw_file = meta["mc_file_sum_genweight_all_events"]
        sw_sample = sw_file * n_sample / n_file
        scale = sigma_pb * 1000.0 * a.lumi / sw_sample          # full-run weight per unit genWeight
        arrs = read_shard(jd / "dataset_shard_inclusive.sqlite")
        # group signatures by final state; one representative mass signature per final state
        by_fs = defaultdict(dict)
        for sig, arr in arrs.items():
            mt = SIG_RE.match(sig)
            if not mt:
                continue
            fs = tuple(int(x) for x in mt.group(3, 4, 5, 6))
            by_fs[fs].setdefault(mt.group(7), {})[mt.group(8) or "mass"] = arr
        fs_rows, events = [], []
        for fs, ims in sorted(by_fs.items()):
            im0 = sorted(ims)[0]
            rep = ims[im0]
            union = (rep["_mcraw_acc"].astype(np.int64) & UNION_BITS) != 0
            gw = rep["_mcraw_genw"][union]
            w = gw * scale
            label = f"{fs[0]}e_{fs[1]}m_{fs[2]}j_{fs[3]}b"
            if label not in mc_fs_cache:
                mc_fs_cache[label] = mc_fs_yield(fs)
            fs_rows.append({"final_state": label, "n_events_file0": int(union.sum()),
                            "expected_events_full_sample": float(union.sum() * n_sample / n_file),
                            # w is the full-run weight; file 0 holds n_file of the n_sample events
                            "weighted_yield_full_sample": float(w.sum() * n_sample / n_file),
                            "max_event_weight": float(w.max()) if w.size else 0.0,
                            "data_events_25oct": data_counts.get(label),
                            "mc_summedSM_25oct_weighted": mc_fs_cache[label]})
            # per event: every mass of that event in this final state, for the bin-dominance check
            idx = np.nonzero(union)[0]
            for k in idx:
                events.append({"final_state": fs, "w": float(rep["_mcraw_genw"][k] * scale),
                               "masses": {im: float(v["mass"][k]) for im, v in ims.items() if "mass" in v}})
        # bin dominance (as the D3 check): for the 20 heaviest events, in every histogram they enter,
        # their weight vs the 25 Oct MC content of that 10 GeV bin
        dom = []
        for ev in sorted(events, key=lambda e: -e["w"])[:20]:
            worst = None
            n_h = n_dom = n_h_ne = n_dom_ne = 0
            worst_ne = None
            for im, mass in ev["masses"].items():
                h = mc_hist(hist_name(ev["final_state"], im))
                if h is None:
                    continue
                vals, edges = h
                b = np.searchsorted(edges, mass, side="right") - 1
                if b < 0 or b >= len(vals):
                    continue
                n_h += 1
                frac = ev["w"] / (ev["w"] + max(float(vals[b]), 0.0))
                n_dom += frac > 0.5
                if vals[b] > 0:      # bins with 25 Oct MC content: inside the delivered mass range
                    n_h_ne += 1
                    n_dom_ne += frac > 0.5
                    if worst_ne is None or frac > worst_ne["fraction_of_bin"]:
                        worst_ne = {"histogram": hist_name(ev["final_state"], im), "mass_gev": mass,
                                    "mc_bin_content_25oct": float(vals[b]), "fraction_of_bin": frac}
                if worst is None or frac > worst["fraction_of_bin"]:
                    worst = {"histogram": hist_name(ev["final_state"], im), "mass_gev": mass,
                             "mc_bin_content_25oct": float(vals[b]), "fraction_of_bin": frac}
            dom.append({"final_state": "{}e_{}m_{}j_{}b".format(*ev["final_state"]), "event_weight": ev["w"],
                        "n_delivered_histograms_hit": n_h, "n_bins_where_event_gt_50pct": int(n_dom),
                        "worst_bin": worst, "n_hit_bins_with_mc_content": n_h_ne,
                        "n_bins_with_mc_content_where_event_gt_50pct": int(n_dom_ne),
                        "worst_bin_with_mc_content": worst_ne})
        gws = np.concatenate([v for s, v in arrs.items() if s.endswith("_mcraw_genw")] or [np.array([])])
        n_union_any = int(mcd["n_stored_in_delivery_union"])
        result["records"][rid] = {
            "title": p["title"], "sigma_pb_portal_total_value": sigma_pb, "portal_xs_block": p["xs"],
            "events_sample": n_sample, "files_sample": p["n_files"], "events_file0": n_file,
            "n_after_trigger": meta["n_after_trigger"], "n_stored": mcd["n_stored"],
            "n_stored_in_delivery_union": n_union_any,
            "n_accepted_per_dataset": mcd["n_accepted_per_dataset"],
            "n_singleelectron_accepted": mcd["n_singleelectron_accepted"],
            "n_entering_a_histogram_file0": int(sum(r["n_events_file0"] for r in fs_rows)),
            "upper_limit_95_fraction_if_zero": (3.0 / n_file) if n_union_any == 0 else None,
            "sigma_w_file0": sw_file, "sigma_w_self_check_passes": meta["mc_sigma_w_self_check"]["passes"],
            "genweight_stored": mcd["genweight_stored_events"],
            "typical_weight_per_mc_event": sigma_pb * 1000.0 * a.lumi / n_sample,
            "scale_per_unit_genweight": scale,
            "expected_events_full_sample": float(sum(r["expected_events_full_sample"] for r in fs_rows)),
            "weighted_yield_full_sample": float(sum(r["weighted_yield_full_sample"] for r in fs_rows)),
            "max_event_weight": max((r["max_event_weight"] for r in fs_rows), default=0.0),
            "emu_0j_events_file0": next((r["n_events_file0"] for r in fs_rows if r["final_state"] == "1e_1m_0j_0b"), 0),
            "final_states": fs_rows, "heaviest_events_bin_dominance": dom,
            "genweight_stored_signature_entries_min_max": [float(gws.min()), float(gws.max())] if gws.size else None,
        }
        print(rid, "union", n_union_any, "hist", result["records"][rid]["n_entering_a_histogram_file0"],
              "yield", f"{result['records'][rid]['weighted_yield_full_sample']:.3g}",
              "wmax", f"{result['records'][rid]['max_event_weight']:.3g}", flush=True)
    Path(a.out).mkdir(parents=True, exist_ok=True)
    (Path(a.out) / "qcd_probe_analysis.json").write_text(json.dumps(result, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
