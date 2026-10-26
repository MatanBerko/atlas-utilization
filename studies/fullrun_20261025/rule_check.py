#!/usr/bin/env python
"""
Rule check of an upstream40 build (the #40 max-4-objects rule, the builders'
default since 23 Oct 2026) against the exact build of the same inputs, for
the DATA five-dataset delivery (--kind data) or the MC builder (--kind mc).
Adapted from studies/cms_ttbar_pr40_20261021/rule_check.py (study branch
0f90fe5): the same R1-R7, reading the new report keys, and R2 against
upstream's physics_calcs.limit_particles_in_fs itself.

  R1 every upstream40 final state has e+m+b <= 4 and e+m+j+b <= 4;
  R2 every final state is upstream's limit_particles_in_fs(x, 4) of each
     exact label x merged into it, and the build's label map equals
     upstream's function on every production label;
  R3 no upstream40 histogram uses a rank >= its label's count of that type
     (no dropped jet used);
  R4 every upstream40 final state has >= 100 events after merging, and the
     final states removed are exactly those below 100;
  R5 names follow exactly the exact build's format (ROI_mass_<im>_cat_
     <n>ex_<n>mx_<n>jx_<n>bx_width_10.0), same histogram class, same title
     convention, same binning;
  R6 events conserved before the >=100 rule: total and per final state (the
     sum over the merged exact labels), exact vs upstream40; MC also the
     weighted yield;
  R7 no NaN/inf, no negative variances (both builds).

Also: counts, the merge table, final states unchanged by the rule compared
bit for bit, and the arrays for the plots.

Inputs per kind (all read-only):
  data  <dir>/<prefix>_bumpnet.root (uncropped), build_summary_rare4_four_dataset.json,
        multiplicity_rule_<prefix>.json
  mc    <dir>/<prefix>_record<record>_mc.root, <prefix>_build_report.json
Writes one JSON. Run as a PBS job (cluster/pbs_proof.sh WHAT=check).
"""
from __future__ import annotations

import argparse
import json
import math
import pathlib
import re
import sys
from collections import defaultdict

import numpy as np
import uproot

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from services.calculations import physics_calcs  # noqa: E402

KEY_PATTERN = re.compile(
    r"^ROI_mass_(?P<im>[a-z0-9]+)_cat_(?P<cat>\d+ex_\d+mx_\d+jx_\d+bx)_width_10\.0$")
RANK_PATTERN = re.compile(r"([a-z])(\d+)")
TOKEN_PATTERN = re.compile(r"(\d+)([a-z])")


def label_counts(label: str) -> dict:
    return {letter: int(n) for n, letter in TOKEN_PATTERN.findall(label)}


def upstream_cap(label: str) -> str:
    return physics_calcs.limit_particles_in_fs(label, 4)


def cat_to_label(cat: str) -> str:
    return "_".join(f"{n}{p}" for n, p in re.findall(r"(\d+)([a-z])x", cat))


def strip_fs(fs: str) -> str:
    return fs[len("_FS_"):] if fs.startswith("_FS_") else fs


def read_root(path: pathlib.Path) -> dict:
    f = uproot.open(path)
    hists = {}
    for key in f.keys():
        name = key.split(";")[0]
        h = f[name]
        hists[name] = {
            "classname": h.classname,
            "values": h.values(flow=True),
            "variances": h.variances(flow=True),
            "edges": h.axis().edges(),
            "entries": float(h.member("fEntries")),
            "title": h.member("fTitle"),
        }
    return hists


def load(kind: str, build_dir: pathlib.Path, prefix: str, record: str, min_events: int) -> dict:
    """{rule, hists, mult (upstream40 section or None), pop, pruned, commit}"""
    if kind == "mc":
        rep = json.loads((build_dir / f"{prefix}_build_report.json").read_text())
        hists = read_root(build_dir / f"{prefix}_record{record}_mc.root")
        pop = {strip_fs(k): v for k, v in rep["final_state_population_before_prune"].items()}
        return {"rule": rep["options"]["multiplicity_rule"], "hists": hists,
                "mult": rep.get("multiplicity_rule_upstream40"), "pop": pop,
                "pruned": {strip_fs(fs) for fs in rep["prune"]["final_states_removed"]},
                "pruned_source": "build report prune.final_states_removed",
                "commit": rep.get("git_commit")}
    summary = json.loads((build_dir / "build_summary_rare4_four_dataset.json").read_text())
    mult = json.loads((build_dir / f"multiplicity_rule_{prefix}.json").read_text())
    hists = read_root(build_dir / f"{prefix}_bumpnet.root")
    pop = {strip_fs(k): {"n_events": int(v)}
           for k, v in mult["final_state_events_before_min_events_rule"].items()}
    return {"rule": summary["multiplicity_rule"], "hists": hists,
            "mult": mult if mult["rule"] == "upstream40" else None, "pop": pop,
            "exact_label_events": {strip_fs(k): int(v)
                                   for k, v in mult["final_state_events_exact_labels"].items()},
            "pruned": {fs for fs, v in pop.items() if v["n_events"] < min_events},
            "pruned_source": "derived: final states with < min events (the data builder "
                             "does not list them)",
            "commit": None}


def parse(name: str):
    m = KEY_PATTERN.match(name)
    return (None, None) if not m else (cat_to_label(m.group("cat")), m.group("im"))


def by_label(hists: dict) -> dict:
    out = defaultdict(list)
    for name in hists:
        lab, _im = parse(name)
        out[lab].append(name)
    return dict(out)


def trimmed(h: dict) -> dict:
    v = h["values"][1:-1]
    nz = np.nonzero(v)[0]
    lo, hi = (int(nz[0]), int(nz[-1]) + 1) if nz.size else (0, 0)
    return {"lo_edge": float(h["edges"][lo]), "width": float(h["edges"][1] - h["edges"][0]),
            "values": v[lo:hi].tolist(), "entries": h["entries"]}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--kind", required=True, choices=("data", "mc"))
    ap.add_argument("--exact-dir", required=True, type=pathlib.Path)
    ap.add_argument("--up40-dir", required=True, type=pathlib.Path)
    ap.add_argument("--exact-prefix", required=True)
    ap.add_argument("--up40-prefix", required=True)
    ap.add_argument("--record", default="67801", help="mc only")
    ap.add_argument("--min-events", type=int, default=100)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    E = load(args.kind, args.exact_dir, args.exact_prefix, args.record, args.min_events)
    P = load(args.kind, args.up40_dir, args.up40_prefix, args.record, args.min_events)
    assert E["rule"] == "exact", E["rule"]
    assert P["rule"] == "upstream40", P["rule"]
    h_e, h_p = E["hists"], P["hists"]
    label_map = P["mult"]["label_map"]
    merged_into = P["mult"]["exact_labels_merged_into"]
    pop_e, pop_p = E["pop"], P["pop"]
    pruned_e, pruned_p = E["pruned"], P["pruned"]
    lab_e, lab_p = by_label(h_e), by_label(h_p)
    weighted = args.kind == "mc"
    res = {"kind": args.kind,
           "inputs": {"exact": str(args.exact_dir), "upstream40": str(args.up40_dir),
                      "exact_commit": E["commit"], "upstream40_commit": P["commit"],
                      "pruned_source": P["pruned_source"]}}

    # ---- counts ---------------------------------------------------------
    res["counts"] = {
        "n_histograms_exact": len(h_e), "n_histograms_upstream40": len(h_p),
        "n_final_states_with_histograms_exact": len(lab_e),
        "n_final_states_with_histograms_upstream40": len(lab_p),
        "n_exact_labels_in_input": len(label_map),
        "n_upstream40_labels_before_min_events_rule": len(merged_into),
        "n_final_states_before_min_events_rule_exact": len(pop_e),
        "n_final_states_before_min_events_rule_upstream40": len(pop_p),
        "n_removed_by_min_events_exact": len(pruned_e),
        "n_removed_by_min_events_upstream40": len(pruned_p),
    }

    # ---- R1 -------------------------------------------------------------
    r1_bad = []
    for lab in lab_p:
        c = label_counts(lab)
        nonjet = sum(v for k, v in c.items() if k != "j")
        if nonjet > 4 or nonjet + c.get("j", 0) > 4:
            r1_bad.append(lab)
    res["R1"] = {"pass": not r1_bad, "n_checked": len(lab_p), "violations": r1_bad}

    # ---- R2 -------------------------------------------------------------
    r2_bad = []
    table = []
    for lab in sorted(lab_p):
        members = merged_into.get(lab, [])
        if not members or not all(upstream_cap(x) == lab for x in members):
            r2_bad.append(lab)
        row = {"final_state": lab, "events": pop_p[lab]["n_events"],
               "n_histograms_upstream40": len(lab_p[lab]),
               "merged_exact_labels": [
                   {"label": x, "events": pop_e.get(x, {}).get("n_events", 0),
                    "survives_in_exact_build": x in lab_e,
                    "n_histograms_exact": len(lab_e.get(x, []))} for x in members]}
        if weighted:
            row["weighted_yield"] = pop_p[lab]["weighted_yield"]
        table.append(row)
    map_bad = sorted(x for x, c in label_map.items() if upstream_cap(x) != c)
    res["R2"] = {"pass": not r2_bad and not map_bad, "n_checked": len(lab_p),
                 "violations": r2_bad, "n_production_labels_checked": len(label_map),
                 "label_map_violations": map_bad,
                 "reference": "services.calculations.physics_calcs.limit_particles_in_fs(x, 4)"}
    res["merge_table"] = table

    # ---- R3 -------------------------------------------------------------
    def r3(hists):
        bad = []
        for name in hists:
            lab, im = parse(name)
            c = label_counts(lab)
            if any(int(r) >= c.get(t, 0) for t, r in RANK_PATTERN.findall(im)):
                bad.append(name)
        return bad
    r3_bad = r3(h_p)
    res["R3"] = {"pass": not r3_bad, "n_checked": len(h_p), "violations": r3_bad[:50],
                 "exact_build_for_reference_n_violations": len(r3(h_e))}

    # ---- R4 -------------------------------------------------------------
    r4_bad = [lab for lab in lab_p if pop_p[lab]["n_events"] < args.min_events]
    prune_consistent = pruned_p == {fs for fs, v in pop_p.items() if v["n_events"] < args.min_events}
    res["R4"] = {"pass": not r4_bad and prune_consistent, "n_checked": len(lab_p),
                 "violations": r4_bad, "pruned_set_equals_below_threshold": prune_consistent,
                 "min_events_among_kept": min((pop_p[lab]["n_events"] for lab in lab_p),
                                              default=None)}

    # ---- R5 -------------------------------------------------------------
    edges0 = next(iter(h_e.values()))["edges"]
    classes_e = {h["classname"] for h in h_e.values()}
    title_is_name_e = all(h["title"] == n for n, h in h_e.items())

    def r5(hists):
        bad = []
        for name, h in hists.items():
            if (not KEY_PATTERN.match(name) or h["classname"] not in classes_e
                    or (h["title"] == name) != title_is_name_e
                    or not np.array_equal(h["edges"], edges0)):
                bad.append(name)
        return bad
    r5_bad_p, r5_bad_e = r5(h_p), r5(h_e)
    res["R5"] = {"pass": not r5_bad_p and not r5_bad_e and len(classes_e) == 1,
                 "pattern": KEY_PATTERN.pattern, "n_bins": int(len(edges0) - 1),
                 "histogram_class": sorted(classes_e), "title_equals_name": title_is_name_e,
                 "violations_upstream40": r5_bad_p[:50], "violations_exact": r5_bad_e[:50],
                 "n_names_in_both_builds": len(set(h_e) & set(h_p)),
                 "example_exact": sorted(h_e)[0], "example_upstream40": sorted(h_p)[0]}

    # ---- R6 -------------------------------------------------------------
    def rel(a, b):
        return abs(a - b) / abs(a) if a else (0.0 if b == 0 else math.inf)

    def totals(pop, keep=None):
        sel = {k: v for k, v in pop.items() if keep is None or k in keep}
        out = {"n_final_states": len(sel), "events": int(sum(v["n_events"] for v in sel.values()))}
        if weighted:
            out["weighted_yield"] = float(sum(v["weighted_yield"] for v in sel.values()))
            out["weighted_yield_union"] = float(sum(v["weighted_yield_union"] for v in sel.values()))
            out["n_ref_entries"] = int(sum(v["n_ref_entries"] for v in sel.values()))
        return out
    before_e, before_p = totals(pop_e), totals(pop_p)
    ok = before_e["events"] == before_p["events"]
    if weighted:
        ok &= (before_e["n_ref_entries"] == before_p["n_ref_entries"]
               and rel(before_e["weighted_yield"], before_p["weighted_yield"]) < 1e-12
               and rel(before_e["weighted_yield_union"], before_p["weighted_yield_union"]) < 1e-12)
    per_fs_bad = []
    for lab, members in merged_into.items():
        if sum(pop_e.get(x, {}).get("n_events", 0) for x in members) != pop_p[lab]["n_events"]:
            per_fs_bad.append(lab)
        elif weighted and rel(sum(pop_e[x]["weighted_yield"] for x in members),
                              pop_p[lab]["weighted_yield"]) > 1e-12:
            per_fs_bad.append(lab)
    extra = {}
    if args.kind == "data":
        # both builds read the same shards: the exact labels the upstream40
        # build saw are the exact build's final states, event for event
        same_inputs = P["exact_label_events"] == {k: v["n_events"] for k, v in pop_e.items()}
        ok &= same_inputs
        extra["upstream40_exact_label_events_equal_exact_build"] = same_inputs
    res["R6"] = {
        "pass": bool(ok and not per_fs_bad),
        "before_min_events_rule": {"exact": before_e, "upstream40": before_p},
        "after_min_events_rule": {
            "exact": totals(pop_e, {k for k in pop_e if k not in pruned_e}),
            "upstream40": totals(pop_p, {k for k in pop_p if k not in pruned_p})},
        "per_final_state_sum_violations": per_fs_bad, **extra,
        "definition": "events = the final_state_counts the >=100 rule counts"
                      + ("; weighted yield = sum of _mcw over each label's reference "
                         "combination; 'union' = after the five-flag event union"
                         if weighted else ""),
    }

    # ---- R7 -------------------------------------------------------------
    def r7(hists):
        nonfinite = [n for n, h in hists.items()
                     if not (np.isfinite(h["values"]).all() and np.isfinite(h["variances"]).all())]
        negvar = [n for n, h in hists.items() if (h["variances"] < 0).any()]
        negbins = sum(int((h["values"] < 0).sum()) for h in hists.values())
        return nonfinite, negvar, negbins
    nf_p, nv_p, nb_p = r7(h_p)
    nf_e, nv_e, nb_e = r7(h_e)
    res["R7"] = {"pass": not (nf_p or nv_p or nf_e or nv_e),
                 "upstream40": {"n_nonfinite": len(nf_p), "n_negative_variance": len(nv_p),
                                "n_negative_bins_info": nb_p},
                 "exact": {"n_nonfinite": len(nf_e), "n_negative_variance": len(nv_e),
                           "n_negative_bins_info": nb_e}}

    # ---- the >=100 rule and the regrouping --------------------------------
    gained = [lab for lab in sorted(lab_p) if not any(x in lab_e for x in merged_into[lab])]
    rescued = sorted(x for x, c in label_map.items() if x in pruned_e and c in lab_p)
    res["min_events_rule_and_regrouping"] = {
        "upstream40_final_states_gained": gained,
        "exact_labels_below_100_rescued_by_merging": rescued,
        "n_exact_labels_rescued": len(rescued),
        "rescued_events": int(sum(pop_e[x]["n_events"] for x in rescued if x in pop_e)),
        "exact_labels_surviving_whose_upstream40_final_state_was_removed": sorted(
            x for x, c in label_map.items() if x in lab_e and c not in lab_p),
        "upstream40_final_states_removed": sorted(pruned_p),
    }

    # ---- unchanged final states: bit for bit ------------------------------
    unchanged = [lab for lab, m in merged_into.items() if m == [lab] and lab in lab_p]
    n_same = n_diff = 0
    diff_names = []
    for lab in unchanged:
        for name in lab_p[lab]:
            he, hp = h_e.get(name), h_p[name]
            if (he is not None and he["values"].tobytes() == hp["values"].tobytes()
                    and he["variances"].tobytes() == hp["variances"].tobytes()):
                n_same += 1
            else:
                n_diff += 1
                diff_names.append(name)
    res["unchanged_final_states"] = {
        "n_final_states": len(unchanged), "n_histograms_identical": n_same,
        "n_histograms_different": n_diff, "different": diff_names[:50],
        "names_only_in_exact_for_these": sorted(
            n for lab in unchanged for n in lab_e.get(lab, []) if n not in h_p)[:50]}

    # ---- plot data --------------------------------------------------------
    def exact_name(name, x):
        """The exact build's name of `name`'s combination under exact label x."""
        cat = name.split("_cat_")[1].split("_width")[0]
        return name.replace(f"_cat_{cat}", "_cat_" + "_".join(
            f"{n}{p}x" for n, p in re.findall(r"(\d+)([a-z])", x)))

    cands = []
    for lab in lab_p:
        if len(merged_into[lab]) < 2:
            continue
        for name in lab_p[lab]:
            contrib = [x for x in merged_into[lab] if exact_name(name, x) in h_e]
            if len(contrib) >= 2:
                cands.append((len(contrib), h_p[name]["entries"], name, contrib))
    cands.sort(key=lambda t: (-t[0], -t[1]))
    picks, seen_fs = [], set()
    for _n, _ent, name, contrib in cands:
        lab, _im = parse(name)
        if lab in seen_fs:
            continue
        seen_fs.add(lab)
        picks.append((name, contrib))
        if len(picks) == 4:
            break
    unchanged_pick = max((n for lab in unchanged for n in lab_p[lab] if n in h_e),
                         key=lambda n: h_p[n]["entries"], default=None)
    res["plot_data"] = {
        "per_upstream40_final_state": [
            {"final_state": t["final_state"],
             "n_histograms_upstream40": t["n_histograms_upstream40"],
             "n_histograms_exact_members": sum(m["n_histograms_exact"]
                                               for m in t["merged_exact_labels"]),
             "events_upstream40": t["events"],
             "events_exact_members_surviving": sum(
                 m["events"] for m in t["merged_exact_labels"] if m["survives_in_exact_build"]),
             "events_exact_members_all": sum(m["events"] for m in t["merged_exact_labels"])}
            for t in table],
        "merged_examples": [
            {"upstream40_name": name, "upstream40": trimmed(h_p[name]),
             "contributors": {x: trimmed(h_e[exact_name(name, x)]) for x in contrib},
             "members_not_in_exact_build": [x for x in merged_into[parse(name)[0]]
                                            if exact_name(name, x) not in h_e]}
            for name, contrib in picks],
        "unchanged_example": None if unchanged_pick is None else {
            "name": unchanged_pick, "exact": trimmed(h_e[unchanged_pick]),
            "upstream40": trimmed(h_p[unchanged_pick])},
    }

    res["all_rules_pass"] = all(res[r]["pass"] for r in ("R1", "R2", "R3", "R4", "R5", "R6", "R7"))
    pathlib.Path(args.out).write_text(json.dumps(res, indent=2, default=float))
    print(json.dumps({"counts": res["counts"], "all_rules_pass": res["all_rules_pass"],
                      **{r: res[r]["pass"] for r in ("R1", "R2", "R3", "R4", "R5", "R6", "R7")}},
                     indent=1))
    return 0 if res["all_rules_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
