#!/usr/bin/env python
"""
Sync with upstream #39 #40 #42 (23 Oct 2026), step 2: static check.

Reuses the method of studies/sync_35_20261019/static_check.py, updated:

  - BEFORE = 7f2da5d (the upstream commit the fork is built on), AFTER =
    29291ae (upstream master with #39, #40, #42);
  - every CMS Python file (every file under studies/, tests included, plus
    every other .py file that does not exist upstream) on each of the three
    NEW sync branches;
  - definitions are compared per top-level function/class/assignment AND per
    class method ("IMCalculator._get_all_events_fs"), since #40 changed a
    method inside an unchanged class name;
  - for `from x import module` / `import x.module`, the attributes the CMS
    file reads from that module (`physics_calcs.is_finalstate_contain_...`)
    are listed, so a changed definition the CMS file never touches is not
    mistaken for a used one;
  - "reached_from_cms": a name-based call graph over the upstream code at
    AFTER -- which changed definitions can be reached from the symbols CMS
    uses. Name-based, so it over-approximates (a shared method name counts
    as a call); every hit is then checked by reading (PROOF.md / the JSON's
    "verdict" entries, written by hand).

Read-only: uses `git show`. Usage: python static_check.py --out static_check.json
"""
from __future__ import annotations

import argparse
import ast
import json
import subprocess
from collections import defaultdict

BEFORE, AFTER = "7f2da5d", "29291ae"
CMS_REFS = {"master": "sync/master-upstream-42-20261023",
            "data": "sync/data-upstream-42-20261023",
            "mc": "sync/mc-upstream-42-20261023"}


# Written by hand after reading the code (23 Oct 2026); line numbers are on
# the three sync branches (master / data / mc).
VERDICTS = {
    "services.calculations.im_calculator.IMCalculator._get_all_events_fs": (
        "NOT executed by CMS production. The only CMS construction is "
        "run_dataset_on_file.py:1419 / 1541 / 1882 (master/data/mc), "
        "IMCalculator(events=..., min_events_per_fs=1, ...); __init__ is unchanged "
        "and does not call it. The calculator is used only through "
        "_calculate_combination_invariant_mass (run_dataset_on_file.py:1454 / 1576 / "
        "1933), which calls calculator.filter_by_particle_counts, slice_by_field and "
        "calculate_invariant_mass (services/pipelines/im_pipeline.py:171, 178, 185), "
        "none of them changed. group_by_final_state / final_state_counts / "
        "get_events_for_final_state (the only callers of _get_all_events_fs) are "
        "never called by any CMS file (git grep: comments only)."),
    "services.calculations.im_calculator.IMCalculator._limit_particles_in_fs": (
        "NOT executed by CMS production: only called from _get_all_events_fs (above)."),
    "services.calculations.im_calculator.IMCalculator": (
        "Class source changed only through the two methods above; the methods "
        "CMS executes are unchanged."),
    "services.calculations.physics_calcs.limit_particles_in_fs": (
        "NOT executed by CMS production. CMS labels events itself with the EXACT "
        "multiplicity (run_dataset_on_file.py _group_by_final_state_with_mask / "
        "exact_final_state_labels: `label = raw_fs`; the old capping call survives "
        "only in comments, e.g. :549 / :592 / :693). Live callers: the finished "
        "m0m1j0 study (studies/m0m1j0_cms/histograms.py:455 inside "
        "per_event_raw_and_capped_final_state, called only at :510 in that study; "
        "the delivery builders import only naming/binning helpers from that module), "
        "and CMS TESTS: studies/cms_datasets/tests/test_exact_jet_labels.py:125, "
        ":285, :326 (step 3)."),
    "services.calculations.physics_calcs.filter_events_by_kinematics": (
        "NOT executed by CMS: reached only by name through "
        "IMCalculator.filter_by_kinematics, which no CMS file calls (git grep: no "
        "hit). CMS object selection is its own (studies/m0m1j0_cms/selection.py), "
        "so #39's muon isolation does not reach CMS."),
    "services.calculations.consts.MUON_REL_ISOLATION_FIELD": (
        "Used only by filter_events_by_kinematics (above): not executed by CMS."),
    "parsing / trigger (#42: event_selection, file_parser, schemas, "
    "parsing_handler; config.yaml)": (
        "No CMS file imports services.parsing.event_selection, file_parser, "
        "schemas or orchestration.handlers.parsing_handler (static check: no "
        "symbol rows), and no CMS production file reads config.yaml (git grep: "
        "a comment only). CMS reads NanoAOD with its own reader and does its own "
        "trigger matching (TRIGGER_42_CHECK.md)."),
}


def git(*a) -> str:
    return subprocess.run(["git", *a], check=True, capture_output=True, text=True).stdout


def show(ref, path):
    try:
        return git("show", f"{ref}:{path}")
    except subprocess.CalledProcessError:
        return None


def defs(src: str) -> dict:
    """{name: source} for top-level defs/classes/assignments, every
    'Class.method', and '<module level>' (code outside definitions)."""
    tree = ast.parse(src)
    out, rest = {}, []
    for node in tree.body:
        seg = ast.get_source_segment(src, node)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            out[node.name] = seg
        elif isinstance(node, ast.ClassDef):
            out[node.name] = seg
            for sub in node.body:
                if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    out[f"{node.name}.{sub.name}"] = ast.get_source_segment(src, sub)
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for t in targets:
                for n in ast.walk(t):
                    if isinstance(n, ast.Name):
                        out[n.id] = seg
            rest.append(seg)
        else:
            rest.append(seg)
    out["<module level>"] = "\n".join(s for s in rest if s)
    return out


def called_names(src: str) -> set:
    """Every bare name and attribute name used in a piece of code."""
    names = set()
    for n in ast.walk(ast.parse(src)):
        if isinstance(n, ast.Name):
            names.add(n.id)
        elif isinstance(n, ast.Attribute):
            names.add(n.attr)
    return names


def module_of(path: str) -> str:
    return path[:-3].replace("/", ".")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    upstream_files = set(git("ls-tree", "-r", "--name-only", AFTER).split())
    upstream_py = [p for p in upstream_files if p.endswith(".py")]
    changed = [p for p in git("diff", "--name-only", BEFORE, AFTER).split() if p.endswith(".py")]
    changed_mods = {module_of(p): p for p in changed}
    up_mods = {module_of(p): p for p in upstream_py}

    # changed definitions, per changed module
    changed_defs = {}
    for mod, p in changed_mods.items():
        b, a = defs(show(BEFORE, p) or ""), defs(show(AFTER, p) or "")
        changed_defs[mod] = sorted(n for n in set(b) | set(a) if b.get(n) != a.get(n))

    # name-based call graph over upstream code at AFTER: def -> names it uses
    graph = {}
    for mod, p in up_mods.items():
        for name, seg in defs(show(AFTER, p) or "").items():
            if name != "<module level>" and seg:
                graph[(mod, name)] = called_names(seg)
    by_short = defaultdict(list)   # short name -> [(mod, full name)]
    for mod, name in graph:
        by_short[name.split(".")[-1]].append((mod, name))

    def reach(start: set) -> set:
        """Upstream defs reachable from a set of (mod, name) roots."""
        seen, todo = set(), list(start)
        while todo:
            node = todo.pop()
            if node in seen or node not in graph:
                continue
            seen.add(node)
            for used in graph[node]:
                todo.extend(by_short.get(used, []))
            # a class reaches its own methods
            todo.extend(k for k in graph if k[0] == node[0] and k[1].startswith(node[1] + "."))
        return seen

    rows = {}
    roots_by_ref = defaultdict(set)
    for refname, ref in CMS_REFS.items():
        for path in git("ls-tree", "-r", "--name-only", ref).split():
            if not path.endswith(".py"):
                continue
            if not (path.startswith("studies/") or path not in upstream_files):
                continue
            src = show(ref, path)
            tree = ast.parse(src)
            aliases = {}   # local alias -> upstream module
            for node in ast.walk(tree):
                hits = []
                if isinstance(node, ast.ImportFrom) and node.module:
                    if node.module in up_mods:
                        hits = [(node.module, a.name) for a in node.names]
                    else:  # from services.calculations import physics_calcs
                        for a in node.names:
                            full = f"{node.module}.{a.name}"
                            if full in up_mods:
                                hits.append((full, "<whole module>"))
                                aliases[a.asname or a.name] = full
                elif isinstance(node, ast.Import):
                    for a in node.names:
                        if a.name in up_mods:
                            hits.append((a.name, "<whole module>"))
                            aliases[a.asname or a.name] = a.name
                for mod, name in hits:
                    rows.setdefault((mod, name), {"used_by": set(), "attrs": set()})
                    rows[(mod, name)]["used_by"].add(f"{refname}:{path}:{node.lineno}")
                    if name != "<whole module>":
                        roots_by_ref[refname].add((mod, name))
            for node in ast.walk(tree):
                if (isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name)
                        and node.value.id in aliases):
                    mod = aliases[node.value.id]
                    rows[(mod, "<whole module>")]["attrs"].add(node.attr)
                    roots_by_ref[refname].add((mod, node.attr))

    reached = {ref: reach(roots) for ref, roots in roots_by_ref.items()}
    result = {"before": BEFORE, "after": AFTER, "cms_refs": CMS_REFS,
              "changed_modules": changed_defs, "symbols": [], "reached_changed_defs": {},
              "verdicts_by_reading": VERDICTS}
    for (mod, name), r in sorted(rows.items()):
        entry = {"module": mod, "symbol": name, "used_by": sorted(r["used_by"])}
        if mod in changed_mods:
            if name == "<whole module>":
                entry["attributes_used"] = sorted(r["attrs"])
                entry["changed_definitions_in_module"] = changed_defs[mod]
                entry["changed_and_used"] = sorted(set(r["attrs"]) & set(changed_defs[mod]))
            else:
                entry["changed"] = name in changed_defs[mod]
        else:
            entry["module_changed"] = False
        result["symbols"].append(entry)
    for ref, nodes in reached.items():
        result["reached_changed_defs"][ref] = sorted(
            f"{mod}.{name}" for mod, name in nodes
            if mod in changed_defs and name in changed_defs[mod])
    json.dump(result, open(args.out, "w"), indent=1)
    for e in result["symbols"]:
        if e["module"] in changed_mods:
            print(e["module"], e["symbol"], e.get("changed", e.get("changed_and_used")),
                  "| used by", len(e["used_by"]))
    print("\nchanged definitions reachable (name-based) from CMS-used symbols:")
    for ref, lst in result["reached_changed_defs"].items():
        print(f"  {ref}: {lst}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
