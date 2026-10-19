#!/usr/bin/env python
"""
Sync with upstream #35 (19 Oct 2026), Part 1c: static check.

For every CMS module (on fork master and on the MC peak-fix branch), list the
symbols it imports from a module that #35 changed, and say whether #35
changed that symbol's source (AST segment of its definition, before = b9f6ea3,
after = 7f2da5d). Module-level code outside definitions is compared too
("<module level>"), since it runs on import. Read-only: uses `git show`.

Usage: python static_check.py --out static_check.json
"""
from __future__ import annotations

import argparse
import ast
import json
import subprocess

BEFORE, AFTER = "b9f6ea3", "7f2da5d"
CMS_REFS = {"master": "45a7e06", "mc_peakfix": "24ecb7c"}
CMS_PREFIXES = ("studies/cms_datasets/", "studies/m0m1j0_cms/", "studies/cms_mc_weights_v3/",
                "studies/cms_coverage/", "studies/mcport_validation_20261014/",
                "services/parsing/validated_runs.py", "services/parsing/trigger_requirements.py")


def git(*a) -> str:
    return subprocess.run(["git", *a], check=True, capture_output=True, text=True).stdout


def show(ref, path):
    try:
        return git("show", f"{ref}:{path}")
    except subprocess.CalledProcessError:
        return None


def defs(src: str) -> dict:
    """{name: source segment} for top-level defs/classes/assignments, plus '<module level>'."""
    tree = ast.parse(src)
    out, rest = {}, []
    for node in tree.body:
        seg = ast.get_source_segment(src, node)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            out[node.name] = seg
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


def module_of(path: str) -> str:
    return path[:-3].replace("/", ".")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    changed = [p for p in git("diff", "--name-only", BEFORE, AFTER).split() if p.endswith(".py")]
    changed_mods = {module_of(p): p for p in changed}
    rows = {}
    for refname, ref in CMS_REFS.items():
        for path in git("ls-tree", "-r", "--name-only", ref).split():
            if not path.endswith(".py") or not path.startswith(CMS_PREFIXES) or "/tests/" in path:
                continue
            src = show(ref, path)
            for node in ast.walk(ast.parse(src)):
                hits = []
                if isinstance(node, ast.ImportFrom) and node.module:
                    if node.module in changed_mods:
                        hits = [(node.module, a.name) for a in node.names]
                    else:  # from services.calculations import physics_calcs
                        for a in node.names:
                            full = f"{node.module}.{a.name}"
                            if full in changed_mods:
                                hits.append((full, "<whole module>"))
                elif isinstance(node, ast.Import):
                    hits = [(a.name, "<whole module>") for a in node.names if a.name in changed_mods]
                for mod, name in hits:
                    rows.setdefault((mod, name), set()).add(f"{refname}:{path}:{node.lineno}")
    result = []
    for (mod, name), users in sorted(rows.items()):
        p = changed_mods[mod]
        b, a = defs(show(BEFORE, p) or ""), defs(show(AFTER, p) or "")
        if name == "<whole module>":
            # which attributes of the module are used? report every changed definition
            changed_names = sorted(n for n in set(b) | set(a) if b.get(n) != a.get(n))
            result.append({"module": mod, "symbol": name, "used_by": sorted(users),
                           "changed_definitions_in_module": changed_names})
        else:
            result.append({"module": mod, "symbol": name, "used_by": sorted(users),
                           "changed_by_35": b.get(name) != a.get(name),
                           "exists_before": name in b, "exists_after": name in a})
    json.dump(result, open(args.out, "w"), indent=1)
    for r in result:
        print(r["module"], r["symbol"], r.get("changed_by_35", r.get("changed_definitions_in_module")),
              "| used by", len(r["used_by"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
