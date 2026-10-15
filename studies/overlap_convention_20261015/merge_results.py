#!/usr/bin/env python
"""
Merge the per-file outputs of measure_overlap_on_file.py into one results
JSON (per dataset and combined), and check that V1 reproduces the production.

Production check: for every file, V1's per-label event counts (accepted
events, N = e+m+b <= 4, inclusive and exclusive) must equal the production's
own rare4 label counts in that file's job_metadata.json
(rare4_diagnostics.final_state_label_event_counts_{inclusive,exclusive}).

Run:  python studies/overlap_convention_20261015/merge_results.py \
          --in-dir <per-file dir> --reference-runs <production runs dir> \
          --out studies/overlap_convention_20261015/results/overlap_results.json
"""
from __future__ import annotations

import argparse
import glob
import json
import pathlib
import sys
from collections import Counter

import numpy as np

DATASETS = ["DoubleMuon", "SingleMuon", "DoubleEG", "MuonEG"]
REJECTED = "REJECTED_N>4"
TOP_N = 20


def frac(n, d):
    return (n / d) if d else None


def add_hist(acc, h):
    if acc is None:
        return {k: (list(v) if isinstance(v, list) else v) for k, v in h.items()}
    assert acc["edges"] == h["edges"]
    acc["counts"] = [a + b for a, b in zip(acc["counts"], h["counts"])]
    for k in ("underflow", "overflow", "n"):
        acc[k] += h[k]
    return acc


def sum_dicts(dicts):
    """Sum nested dicts of ints / histograms / lists of ints."""
    out = {}
    for d in dicts:
        for k, v in d.items():
            if isinstance(v, dict) and "edges" in v:
                out[k] = add_hist(out.get(k), v)
            elif isinstance(v, dict):
                out.setdefault(k, [])
                out[k].append(v)
            elif isinstance(v, list):
                out[k] = [a + b for a, b in zip(out[k], v)] if k in out else list(v)
            elif isinstance(v, (int, float)) and not isinstance(v, bool):
                out[k] = out.get(k, 0) + v
            else:
                out[k] = v
    for k, v in list(out.items()):
        if isinstance(v, list) and v and isinstance(v[0], dict):
            out[k] = sum_dicts(v)
    return out


def median(x):
    x = np.asarray(x, dtype=float)
    x = x[np.isfinite(x)]
    return float(np.median(x)) if x.size else None


def summarise_a(per_file_json, per_file_npz):
    out = {}
    keys = per_file_json[0]["a_leading_jet_overlap_V0"].keys()
    for key in keys:
        n = sum(j["a_leading_jet_overlap_V0"][key]["n_events"] for j in per_file_json)
        nm = sum(j["a_leading_jet_overlap_V0"][key]["n_lead_jet_within_0p4_of_muon"] for j in per_file_json)
        ne = sum(j["a_leading_jet_overlap_V0"][key]["n_lead_jet_within_0p4_of_electron"] for j in per_file_json)
        nl = sum(j["a_leading_jet_overlap_V0"][key]["n_lead_jet_within_0p4_of_any_lepton"] for j in per_file_json)
        cat = lambda s: np.concatenate([z[f"a_{key}_{s}"] for z in per_file_npz]) if per_file_npz else np.array([])
        out[key] = {
            "n_events": n,
            "n_lead_jet_within_0p4_of_muon": nm, "frac_lead_jet_within_0p4_of_muon": frac(nm, n),
            "n_lead_jet_within_0p4_of_electron": ne, "frac_lead_jet_within_0p4_of_electron": frac(ne, n),
            "n_lead_jet_within_0p4_of_any_lepton": nl, "frac_lead_jet_within_0p4_of_any_lepton": frac(nl, n),
            "median_dr_lead_jet_to_nearest_muon": median(cat("dr_mu")),
            "median_dr_lead_jet_to_nearest_electron": median(cat("dr_e")),
            "median_dr_lead_jet_to_nearest_lepton": median(cat("dr_l")),
            "light_jets_only_frac_lead_jet_within_0p4_of_muon": (
                float(np.mean(cat("dr_mu_lightonly")[np.isfinite(cat("dr_mu_lightonly"))] < 0.4))
                if per_file_npz and np.isfinite(cat("dr_mu_lightonly")).any() else None),
            "light_jets_only_median_dr_to_nearest_muon": median(cat("dr_mu_lightonly")),
        }
    return out


def summarise_c(c):
    c = dict(c)
    c["frac_muons_removed"] = frac(c["n_muons_removed_by_0p4_step"], c["n_muons_selected"])
    c["frac_electrons_removed"] = frac(c["n_electrons_removed_by_0p4_step"], c["n_electrons_selected"])
    c["frac_events_losing_ge1_lepton"] = frac(c["n_events_losing_ge1_lepton"], c["n_accepted_events"])
    c["frac_light_jets_removed"] = frac(c["n_light_jets_removed_by_0p2_steps"], c["n_light_jets_V0"])
    return c


def summarise_d(d):
    out = {}
    for v, x in d.items():
        out[v] = dict(x)
        out[v]["frac_lead_jet_within_0p4_of_surviving_lepton"] = frac(
            x["n_lead_jet_within_0p4_of_surviving_lepton"], x["n_events_with_a_jet"])
        out[v]["frac_lead_jet_within_0p4_of_originally_selected_lepton"] = frac(
            x["n_lead_jet_within_0p4_of_originally_selected_lepton"], x["n_events_with_a_jet"])
        out[v]["frac_lead_light_jet_within_0p4_of_surviving_lepton"] = frac(
            x["n_lead_light_jet_within_0p4_of_surviving_lepton"], x["n_events_with_a_light_jet"])
    return out


def merge_categories(entries):
    """entries: list of per-file category dicts for ONE population."""
    out = {}
    for vn in ("V0", "V1", "V2", "V2u"):
        c = Counter()
        for e in entries:
            c.update(e[vn])
        out[vn] = dict(c)
    for vn in ("V2", "V2u"):
        t = Counter()
        for e in entries:
            t.update(e[f"transitions_V1_to_{vn}"])
        out[f"transitions_V1_to_{vn}"] = dict(t.most_common())
        out[f"n_events_changing_category_V1_to_{vn}"] = sum(e[f"n_events_changing_category_V1_to_{vn}"] for e in entries)
        out[f"n_events_{vn}_population"] = sum(e[f"n_events_{vn}_population"] for e in entries)
    out["n_events_V1_population"] = sum(e["n_events_V1_population"] for e in entries)
    top = sorted(((k, v) for k, v in out["V1"].items()), key=lambda kv: -kv[1])[:TOP_N]
    out["top20_by_V1"] = [
        {"category": k, "V1": v, "V2": out["V2"].get(k, 0), "V2u": out["V2u"].get(k, 0),
         "V0": out["V0"].get(k, 0),
         "ratio_V2_over_V1": frac(out["V2"].get(k, 0), v), "ratio_V2u_over_V1": frac(out["V2u"].get(k, 0), v)}
        for k, v in top]
    return out


def production_check(per_file_json, ref_dir):
    rows = []
    for j in per_file_json:
        cands = glob.glob(str(pathlib.Path(ref_dir) / j["dataset"] / "job_*" / "job_metadata.json"))
        ref = None
        for c in cands:
            m = json.loads(pathlib.Path(c).read_text())
            if m.get("record_id") == j["record_id"] and m.get("file_index") == j["file_index"]:
                ref = (c, m)
        row = {"dataset": j["dataset"], "record_id": j["record_id"], "file_index": j["file_index"]}
        if ref is None:
            row["verdict"] = "NO REFERENCE FOUND"
            rows.append(row)
            continue
        path, m = ref
        r4 = m["rare4_diagnostics"]
        row["reference"] = path
        row["reference_git_commit"] = m.get("git_commit")
        for pop, key in (("inclusive", "inclusive_orderA"), ("exclusive", "exclusive_orderA")):
            # zero-count labels are dropped on both sides: the production's
            # exclusive table also lists labels that have no exclusive events
            mine = {k: v for k, v in j["e_categories"][key]["V1"].items() if k != REJECTED and v}
            theirs = {k: v for k, v in r4[f"final_state_label_event_counts_{pop}"].items() if v}
            row[f"{pop}_identical"] = (mine == theirs)
            row[f"{pop}_n_events_mine"] = sum(mine.values())
            row[f"{pop}_n_events_production"] = sum(theirs.values())
            if mine != theirs:
                diff = {k: (mine.get(k, 0), theirs.get(k, 0)) for k in set(mine) | set(theirs)
                        if mine.get(k, 0) != theirs.get(k, 0)}
                row[f"{pop}_differences_mine_vs_production"] = dict(list(diff.items())[:30])
        row["n_accepted_mine"] = j["n_accepted_orderA"]
        row["n_after_gate_production"] = m.get("n_after_gate")
        row["verdict"] = ("IDENTICAL" if row["inclusive_identical"] and row["exclusive_identical"]
                          and row["n_accepted_mine"] == row["n_after_gate_production"] else "DIFFERENT")
        rows.append(row)
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--in-dir", required=True)
    ap.add_argument("--reference-runs", default=None)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    files = sorted(glob.glob(str(pathlib.Path(args.in_dir) / "overlap_*.json")))
    per = [json.loads(pathlib.Path(f).read_text()) for f in files]
    npz = {f: dict(np.load(f[:-5] + ".npz")) for f in files}
    if len(per) != 8:
        print(f"WARNING: {len(per)} per-file outputs, expected 8", flush=True)

    groups = {d: [i for i, j in enumerate(per) if j["dataset"] == d] for d in DATASETS}
    groups["combined"] = list(range(len(per)))
    results = {"what": "Jet-lepton overlap conventions V0/V1/V2 on the 8 rebuild-validation files",
               "n_files": len(per),
               "files": [{k: j[k] for k in ("dataset", "record_id", "file_index", "file_url", "git_commit",
                                            "n_read", "n_after_golden_json", "n_after_own_trigger",
                                            "n_accepted_orderA", "n_accepted_orderB", "elapsed_sec")}
                         for j in per],
               "per_group": {}}
    for g, idx in groups.items():
        js = [per[i] for i in idx]
        zs = [npz[files[i]] for i in idx]
        if not js:
            continue
        counts = sum_dicts([{k: j[k] for k in ("n_read", "n_after_golden_json", "n_after_own_trigger",
                                               "n_accepted_orderA", "n_accepted_orderB",
                                               "n_accepted_A_not_B", "n_accepted_B_not_A",
                                               "n_exclusive_accepted_orderA", "n_exclusive_accepted_orderB",
                                               "n_electrons_removed_by_emu_rule")} for j in js])
        res = {"counts": counts,
               "a": summarise_a(js, zs),
               "b": sum_dicts([j["b_dr_jet_nearest_lepton_V0_accepted"] for j in js]),
               "c": summarise_c(sum_dicts([{k: v for k, v in j["c_v2_removals_orderA"].items()
                                            if k != "removed_leptons_pass_production_id_iso"} for j in js])),
               "d": summarise_d(sum_dicts([j["d_residual_contamination_accepted"] for j in js])),
               "jet_multiplicity": sum_dicts([j["jet_multiplicity_accepted"] for j in js]),
               "e": {pop: merge_categories([j["e_categories"][pop] for j in js])
                     for pop in per[0]["e_categories"]}}
        results["per_group"][g] = res
    results["c_note"] = per[0]["c_v2_removals_orderA"]["removed_leptons_pass_production_id_iso"]
    results["a_note"] = per[0]["a_note"]

    # the delivered four-dataset set: DoubleMuon inclusive + the other three exclusive
    delivered = {}
    for order in ("orderA", "orderB"):
        entries = []
        for j in per:
            pop = f"inclusive_{order}" if j["dataset"] == "DoubleMuon" else f"exclusive_{order}"
            entries.append(j["e_categories"][pop])
        delivered[order] = merge_categories(entries)
    results["delivered_four_dataset_categories"] = delivered

    if args.reference_runs:
        results["production_check_V1"] = production_check(per, args.reference_runs)
    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(results, indent=1) + "\n", encoding="utf-8")
    print(f"wrote {out}")
    for row in results.get("production_check_V1", []):
        print(f"  production check {row['dataset']} {row['record_id']}/{row['file_index']}: {row['verdict']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
