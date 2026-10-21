#!/usr/bin/env python
"""
Rule check of the PR #40 ttbar build against the exact build (study step 6).

Reads the two per-sample ROOT files with uproot and the two build reports
(the pr40 report carries the exact -> capped label map and, for both
rules, every final state's population BEFORE the >=100 rule):

  R1 every pr40 final state has e+m+b <= 4 and e+m+j+b <= 4;
  R2 every pr40 final state is cap_label of each exact label merged into it
     (the oracle comparison of cap_label with c2488b7's own
     limit_particles_in_fs on every production label is check_oracle.py,
     run in the same job);
  R3 no pr40 histogram uses a rank >= its label's count of that type;
  R4 every pr40 final state has >= 100 raw MC events after merging;
  R5 names follow exactly the exact build's format (ROI_mass_<im>_cat_
     <n>ex_<n>mx_<n>jx_<n>bx_width_10.0), TH1D, same binning;
  R6 events conserved: total raw events and total weighted yield over final
     states, exact vs pr40, before and after the >=100 rule;
  R7 no NaN/inf, no negative variances (both builds).

Also: histogram counts, the merge table, final states gained / exact labels
rescued by the >=100 rule because of the regrouping, unchanged final states
compared bit for bit, and the arrays for the study plots.

Read-only. Writes one JSON. Run as a PBS job (cluster/pbs_post.sh WHAT=rulecheck).
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

from studies.cms_mc_weights_v3.deliver.multiplicity_pr40 import cap_label, label_counts  # noqa: E402

KEY_PATTERN = re.compile(
    r"^ROI_mass_(?P<im>[a-z0-9]+)_cat_(?P<cat>\d+ex_\d+mx_\d+jx_\d+bx)_width_10\.0$")
RANK_PATTERN = re.compile(r"([a-z])(\d+)")
RECORD = "67801"


def cat_to_label(cat: str) -> str:
    return "_".join(f"{n}{p}" for n, p in re.findall(r"(\d+)([a-z])x", cat))


def load(build_dir: pathlib.Path, prefix: str):
    report = json.loads((build_dir / f"{prefix}_build_report.json").read_text())
    f = uproot.open(build_dir / f"{prefix}_record{RECORD}_mc.root")
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
    return report, hists


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
    ap.add_argument("--exact-dir", required=True, type=pathlib.Path)
    ap.add_argument("--pr40-dir", required=True, type=pathlib.Path)
    ap.add_argument("--exact-prefix", default="exact")
    ap.add_argument("--pr40-prefix", default="pr40")
    ap.add_argument("--min-events", type=int, default=100)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    rep_e, h_e = load(args.exact_dir, args.exact_prefix)
    rep_p, h_p = load(args.pr40_dir, args.pr40_prefix)
    assert rep_e["options"].get("multiplicity_rule") == "exact"
    assert rep_p["options"].get("multiplicity_rule") == "pr40"
    label_map = rep_p["multiplicity_rule_pr40"]["label_map"]
    merged_into = rep_p["multiplicity_rule_pr40"]["exact_labels_merged_into"]
    pop_e = rep_e["final_state_population_before_prune"]
    pop_p = rep_p["final_state_population_before_prune"]
    pruned_e = {fs[len("_FS_"):] for fs in rep_e["prune"]["final_states_removed"]}
    pruned_p = {fs[len("_FS_"):] for fs in rep_p["prune"]["final_states_removed"]}
    lab_e, lab_p = by_label(h_e), by_label(h_p)
    res = {"inputs": {"exact": str(args.exact_dir), "pr40": str(args.pr40_dir),
                      "exact_commit": rep_e["git_commit"], "pr40_commit": rep_p["git_commit"]}}

    # ---- counts ---------------------------------------------------------
    res["counts"] = {
        "n_histograms_exact": len(h_e), "n_histograms_pr40": len(h_p),
        "n_final_states_with_histograms_exact": len(lab_e),
        "n_final_states_with_histograms_pr40": len(lab_p),
        "n_exact_labels_in_production": len(label_map),
        "n_pr40_labels_before_prune": len(merged_into),
        "n_final_states_before_prune_exact": len(pop_e),
        "n_final_states_before_prune_pr40": len(pop_p),
        "n_removed_by_min_events_exact": len(pruned_e),
        "n_removed_by_min_events_pr40": len(pruned_p),
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
        ok = bool(members) and all(label_map[x] == lab and cap_label(x) == lab for x in members)
        if not ok:
            r2_bad.append(lab)
        table.append({
            "final_state": lab,
            "raw_events": pop_p[lab]["n_events"],
            "weighted_yield": pop_p[lab]["weighted_yield"],
            "n_histograms_pr40": len(lab_p[lab]),
            "merged_exact_labels": [
                {"label": x, "raw_events": pop_e.get(x, {}).get("n_events", 0),
                 "survives_in_exact_build": x in lab_e,
                 "n_histograms_exact": len(lab_e.get(x, []))} for x in members],
        })
    res["R2"] = {"pass": not r2_bad, "n_checked": len(lab_p), "violations": r2_bad,
                 "note": "cap_label == c2488b7 limit_particles_in_fs(label, 4) on every "
                         "production label is checked by check_oracle.py (oracle_*.json)"}
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
                 "min_raw_events_among_kept": min(pop_p[lab]["n_events"] for lab in lab_p)}

    # ---- R5 -------------------------------------------------------------
    edges0 = next(iter(h_e.values()))["edges"]
    def r5(hists):
        bad = []
        for name, h in hists.items():
            if (not KEY_PATTERN.match(name) or h["classname"] != "TH1D"
                    or h["title"] != name or not np.array_equal(h["edges"], edges0)):
                bad.append(name)
        return bad
    r5_bad_p, r5_bad_e = r5(h_p), r5(h_e)
    common = sorted(set(h_e) & set(h_p))
    res["R5"] = {"pass": not r5_bad_p and not r5_bad_e,
                 "pattern": KEY_PATTERN.pattern, "n_bins": int(len(edges0) - 1),
                 "violations_pr40": r5_bad_p[:50], "violations_exact": r5_bad_e[:50],
                 "n_names_in_both_builds": len(common),
                 "example_exact": sorted(h_e)[0], "example_pr40": sorted(h_p)[0]}

    # ---- R6 -------------------------------------------------------------
    def totals(pop, keep=None):
        sel = {k: v for k, v in pop.items() if keep is None or k in keep}
        return {"n_final_states": len(sel),
                "raw_events": int(sum(v["n_events"] for v in sel.values())),
                "weighted_yield": float(sum(v["weighted_yield"] for v in sel.values())),
                "weighted_yield_union": float(sum(v["weighted_yield_union"] for v in sel.values())),
                "raw_events_in_labels_with_combinations": int(sum(
                    v["n_events"] for v in sel.values() if v["n_ref_entries"])),
                "n_ref_entries": int(sum(v["n_ref_entries"] for v in sel.values()))}
    before_e, before_p = totals(pop_e), totals(pop_p)
    after_e = totals(pop_e, {k for k in pop_e if k not in pruned_e})
    after_p = totals(pop_p, {k for k in pop_p if k not in pruned_p})
    def rel(a, b):
        return abs(a - b) / abs(a) if a else (0.0 if b == 0 else math.inf)
    # exact labels grouped by their capped label: the merged population must
    # equal the sum of its members, label by label
    per_fs_bad = []
    for lab, members in merged_into.items():
        s = sum(pop_e[x]["n_events"] for x in members)
        sw = sum(pop_e[x]["weighted_yield"] for x in members)
        if s != pop_p[lab]["n_events"] or rel(sw, pop_p[lab]["weighted_yield"]) > 1e-12:
            per_fs_bad.append(lab)
    res["R6"] = {
        "pass": (before_e["raw_events"] == before_p["raw_events"]
                 and before_e["n_ref_entries"] == before_p["n_ref_entries"]
                 and rel(before_e["weighted_yield"], before_p["weighted_yield"]) < 1e-12
                 and rel(before_e["weighted_yield_union"], before_p["weighted_yield_union"]) < 1e-12
                 and not per_fs_bad),
        "before_min_events_rule": {"exact": before_e, "pr40": before_p,
                                   "weighted_rel_diff": rel(before_e["weighted_yield"],
                                                            before_p["weighted_yield"]),
                                   "weighted_union_rel_diff": rel(before_e["weighted_yield_union"],
                                                                  before_p["weighted_yield_union"])},
        "after_min_events_rule": {"exact": after_e, "pr40": after_p},
        "per_final_state_sum_violations": per_fs_bad,
        "definition": "raw events = the final_state_counts the >=100 rule counts; weighted "
                      "yield = sum of _mcw over each label's reference combination (every "
                      "combination holds each event once); 'union' = after the five-flag "
                      "event union; single-object labels have no combination and no weight",
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
                 "pr40": {"n_nonfinite": len(nf_p), "n_negative_variance": len(nv_p),
                          "n_negative_bins_info": nb_p},
                 "exact": {"n_nonfinite": len(nf_e), "n_negative_variance": len(nv_e),
                           "n_negative_bins_info": nb_e}}

    # ---- the >=100 rule and the regrouping --------------------------------
    gained = [lab for lab in sorted(lab_p) if not any(x in lab_e for x in merged_into[lab])]
    rescued = sorted(x for x, c in label_map.items() if x in pruned_e and c in lab_p)
    lost = sorted(x for x, c in label_map.items() if x in lab_e and c not in lab_p)
    still_removed = sorted(c for c in pruned_p)
    res["min_events_rule_and_regrouping"] = {
        "pr40_final_states_gained": gained,
        "exact_labels_below_100_rescued_by_merging": rescued,
        "n_exact_labels_rescued": len(rescued),
        "rescued_raw_events": int(sum(pop_e[x]["n_events"] for x in rescued)),
        "exact_labels_surviving_whose_pr40_final_state_was_removed": lost,
        "pr40_final_states_removed": still_removed,
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

    merged_cands = []
    for lab in lab_p:
        if len(merged_into[lab]) < 2:
            continue
        for name in lab_p[lab]:
            contrib = [x for x in merged_into[lab] if exact_name(name, x) in h_e]
            if len(contrib) >= 3:
                merged_cands.append((len(contrib), h_p[name]["entries"], name, contrib))
    merged_cands.sort(key=lambda t: (-t[0], -t[1]))
    picks, seen_fs = [], set()
    for _n, _ent, name, contrib in merged_cands:
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
        "per_pr40_final_state": [
            {"final_state": t["final_state"], "n_histograms_pr40": t["n_histograms_pr40"],
             "n_histograms_exact_members": sum(m["n_histograms_exact"] for m in t["merged_exact_labels"]),
             "raw_events_pr40": t["raw_events"],
             "raw_events_exact_members_surviving": sum(
                 m["raw_events"] for m in t["merged_exact_labels"] if m["survives_in_exact_build"]),
             "raw_events_exact_members_all": sum(m["raw_events"] for m in t["merged_exact_labels"])}
            for t in table],
        "merged_examples": [
            {"pr40_name": name, "pr40": trimmed(h_p[name]),
             "contributors": {x: trimmed(h_e[exact_name(name, x)]) for x in contrib},
             "members_not_in_exact_build": [x for x in merged_into[parse(name)[0]]
                                            if exact_name(name, x) not in h_e]}
            for name, contrib in picks],
        "unchanged_example": None if unchanged_pick is None else {
            "name": unchanged_pick, "exact": trimmed(h_e[unchanged_pick]),
            "pr40": trimmed(h_p[unchanged_pick])},
    }

    res["all_rules_pass"] = all(res[r]["pass"] for r in ("R1", "R2", "R3", "R4", "R5", "R6", "R7"))
    pathlib.Path(args.out).write_text(json.dumps(res, indent=2, default=float))
    print(json.dumps({k: (v if k in ("counts", "all_rules_pass") else
                          {kk: vv for kk, vv in v.items() if kk in ("pass", "n_checked")})
                      for k, v in res.items() if k in ("counts", "all_rules_pass")
                      or k.startswith("R")}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
