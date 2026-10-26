#!/usr/bin/env python
"""Full run 25 Oct 2026, step 3: OLD vs NEW delivery builds (data matched5 and
the MC smoke build) and the per-file driver outputs, for the PRECHECK report.

Reads, under --work:
  runs/<side>/data/<Dataset>/job_0/job_metadata.json      (overlap removal ON)
  runs/<side>/data_noor/<Dataset>/job_0/job_metadata.json (overlap removal OFF)
  runs/<side>/mc/record<R>/job_0/job_metadata.json
  deliver/<side>/data/{build_summary_rare4_four_dataset.json, manifest_precheck.json,
                       precheck_bumpnet.root}
  deliver/<side>/mc/{precheck_build_report.json, precheck_*_mc.root}
and writes one JSON (--out). ROOT reading, so run it inside a PBS job.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import uproot

DATASETS = ("DoubleMuon", "SingleMuon", "DoubleEG", "MuonEG", "SingleElectron")
MC_RECORDS = (67801, 72752)
EXAMPLES = {"ee": "ROI_mass_e0e1_cat_2ex_0mx_0jx_0bx_width_10.0",
            "mumu": "ROI_mass_m0m1_cat_0ex_2mx_0jx_0bx_width_10.0"}
SIDES = ("old", "new")


def _load(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def per_file(work: Path) -> dict:
    out = {}
    jobs = [("data", ds, f"data/{ds}/job_0") for ds in DATASETS]
    jobs += [("mc", f"MC_{r}", f"mc/record{r}/job_0") for r in MC_RECORDS]
    for kind, name, rel in jobs:
        rec = {}
        for side in SIDES:
            m = _load(work / "runs" / side / rel / "job_metadata.json")
            d4 = m.get("matched4_diagnostics") or {}
            r = {
                "n_read": m["n_read"], "n_after_golden_json": m.get("n_after_golden_json"),
                "n_after_trigger": m["n_after_trigger"], "n_accepted": m.get("n_after_gate"),
                "n_exclusive": m.get("n_exclusive"),
                "n_electrons_removed_by_overlap": d4.get("n_electrons_removed_total"),
                "n_events_with_an_electron_removed": d4.get("n_events_with_an_electron_removed"),
                "acceptance_counts": d4.get("acceptance_counts"),
                "final_states_inclusive": m["final_state_label_event_counts_inclusive"],
            }
            if kind == "data":
                m0 = _load(work / "runs" / side / "data_noor" / name / "job_0" / "job_metadata.json")
                r["n_accepted_without_overlap_removal"] = m0["n_after_gate"]
                r["events_lost_to_overlap_removal"] = m0["n_after_gate"] - m["n_after_gate"]
            rec[side] = r
        out[name] = rec
    return out


def top_final_state_changes(per: dict, kind: str, n: int = 10) -> dict:
    tot = {s: {} for s in SIDES}
    for name, rec in per.items():
        if (kind == "data") != (not name.startswith("MC_")):
            continue
        for s in SIDES:
            for lab, c in rec[s]["final_states_inclusive"].items():
                tot[s][lab] = tot[s].get(lab, 0) + c
    labels = set(tot["old"]) | set(tot["new"])
    rows = [{"label": lab, "old": tot["old"].get(lab, 0), "new": tot["new"].get(lab, 0),
             "change": tot["new"].get(lab, 0) - tot["old"].get(lab, 0)} for lab in labels]
    rows.sort(key=lambda r: (-abs(r["change"]), r["label"]))
    return {"n_labels_old": len(tot["old"]), "n_labels_new": len(tot["new"]),
            "n_events_old": sum(tot["old"].values()), "n_events_new": sum(tot["new"].values()),
            "top": rows[:n]}


def _hist_summary(path: Path) -> dict:
    f = uproot.open(path)
    keys = sorted({k.split(";")[0] for k in f.keys()})
    total = 0.0
    for k in keys:
        total += float(np.sum(f[k].values()))
    return {"n_histograms": len(keys), "sum_of_contents": total, "keys": keys}


def builds(work: Path) -> dict:
    res = {"data": {}, "mc": {}}
    hs = {}
    for side in SIDES:
        d = work / "deliver" / side / "data"
        bs = _load(d / "build_summary_rare4_four_dataset.json")
        man = _load(d / "manifest_precheck.json")
        h = _hist_summary(d / "precheck_bumpnet.root")
        hs[side] = {x["root_key"]: x["n_events"] for x in man}
        res["data"][side] = {
            "n_delivered_histograms": bs["n_delivered_histograms"],
            "n_distinct_final_state_categories_delivered": bs["n_distinct_final_state_categories_delivered"],
            "funnel": bs["funnel"],
            "per_dataset_event_counts": {k: {kk: v[kk] for kk in ("n_events_pooled_rare4", "n_own_accepted", "n_own_exclusive") if kk in v}
                                         for k, v in bs["per_dataset_event_counts"].items()},
            "n_histograms_in_root": h["n_histograms"], "sum_of_contents_root": h["sum_of_contents"],
            "categories": sorted({x["final_state_category"] for x in man}),
        }
    o, n = set(hs["old"]), set(hs["new"])
    res["data"]["only_old"] = sorted(o - n)
    res["data"]["only_new"] = sorted(n - o)
    res["data"]["n_common"] = len(o & n)
    res["data"]["categories_only_old"] = sorted(set(res["data"]["old"]["categories"]) - set(res["data"]["new"]["categories"]))
    res["data"]["categories_only_new"] = sorted(set(res["data"]["new"]["categories"]) - set(res["data"]["old"]["categories"]))
    ch = [{"root_key": k, "old": hs["old"].get(k, 0), "new": hs["new"].get(k, 0)} for k in o | n]
    for r in ch:
        r["change"] = r["new"] - r["old"]
    ch.sort(key=lambda r: (-abs(r["change"]), r["root_key"]))
    res["data"]["top_histogram_changes"] = ch[:15]

    ex = {}
    for tag, key in EXAMPLES.items():
        ex[tag] = {"root_key": key}
        for side in SIDES:
            f = uproot.open(work / "deliver" / side / "data" / "precheck_bumpnet.root")
            if key in {k.split(";")[0] for k in f.keys()}:
                h = f[key]
                ex[tag][side] = {"edges": h.axis().edges().tolist(), "values": h.values().tolist()}
            else:
                ex[tag][side] = None
    res["data_examples"] = ex

    for side in SIDES:
        d = work / "deliver" / side / "mc"
        rep = _load(d / "precheck_build_report.json")
        files = {}
        for p in sorted(d.glob("precheck_*_mc.root")):
            s = _hist_summary(p)
            files[p.name] = {"n_histograms": s["n_histograms"], "sum_of_weights": s["sum_of_contents"],
                             "keys": s["keys"]}
        res["mc"][side] = {"files": files,
                           "summed_sm_n_histograms": rep["summed_sm"]["n_histograms"],
                           "prune_n_final_states_removed": rep["prune"]["n_final_states_removed"]}
    for name in res["mc"]["old"]["files"]:
        ko = set(res["mc"]["old"]["files"][name]["keys"])
        kn = set(res["mc"]["new"]["files"].get(name, {}).get("keys", []))
        res["mc"].setdefault("key_diff", {})[name] = {"only_old": len(ko - kn), "only_new": len(kn - ko),
                                                      "common": len(ko & kn)}
    for side in SIDES:
        for v in res["mc"][side]["files"].values():
            v.pop("keys")
    return res


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--work", required=True)
    p.add_argument("--out", required=True)
    a = p.parse_args()
    work = Path(a.work)
    per = per_file(work)
    out = {"per_file": per,
           "final_state_changes_data": top_final_state_changes(per, "data"),
           "final_state_changes_mc": top_final_state_changes(per, "mc"),
           "builds": builds(work)}
    for name in per:
        for side in SIDES:
            per[name][side].pop("final_states_inclusive")
    Path(a.out).write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps(out["final_state_changes_data"], indent=1)[:3000])


if __name__ == "__main__":
    main()
