#!/usr/bin/env python
"""
Oracle check of multiplicity_pr40.py against Maryna's own PR #40 code
(upstream commit c2488b7, NOT merged), study steps 3(i)/(ii) and R2.

Two processes, so the two code trees never share an import:
  --side cms     (this repo) writes cap_label / combination_allowed answers;
  --side oracle  (run with --oracle-tree = a `git archive c2488b7` extract
                 OUTSIDE the repo) recomputes them with c2488b7's
                 physics_calcs.limit_particles_in_fs(label, 4) and
                 is_finalstate_contain_combination(capped, combination) and
                 compares.

Inputs: the grid (e, m, b in 0..4, e+m+b <= 4, j in 0..12) x the 186
combinations; with --report, every exact label of a pr40 build report
(its label_map, i.e. every label in the production); with --runs-dir,
every (exact label, combination) pair stored in the production's rare4
shards (read-only); with --exact-report, every pair named by the exact
build's histograms.

Usage (see HANDOFF.md):
  python check_oracle.py --side cms --out answers.json [--report pr40_build_report.json]
      [--exact-report exact_build_report.json] [--runs-dir <work>/runs]
  python -I check_oracle.py --side oracle --oracle-tree <extract> --answers answers.json --out result.json
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
NAME_PATTERN = re.compile(r"^mass_([0-9a-z]+)_cat_((?:\d+[a-z]x_?)+)$")


def grid_labels() -> list:
    return [f"{e}e_{m}m_{j}j_{b}b"
            for e in range(5) for m in range(5) for b in range(5) if e + m + b <= 4
            for j in range(13)]


def name_to_label(cat: str) -> str:
    return "_".join(f"{n}{p}" for n, p in re.findall(r"(\d+)([a-z])x", cat))


def side_cms(args) -> None:
    sys.path.insert(0, str(REPO_ROOT))
    from services.calculations.combinatorics import get_all_combinations
    from services.pipelines.im_pipeline import prepare_im_combination_name
    from studies.cms_mc_weights_v3.deliver.multiplicity_pr40 import (
        cap_label, combination_allowed)

    combos = get_all_combinations(["Electrons", "Muons", "Jets", "BJets"], 1, 4, 1, 4,
                                  max_total_particles=4, include_subleading=True,
                                  max_subleading_index=1)
    assert len(combos) == 186
    combo_by_name = {prepare_im_combination_name("x", "f", c).split("_IM_")[1]:
                     {k: list(v) for k, v in c.items()} for c in combos}

    sets = {"grid": grid_labels()}
    pairs = {"grid_x_186": [(lab, im) for lab in sets["grid"] for im in combo_by_name]}
    if args.report:
        rep = json.loads(pathlib.Path(args.report).read_text())
        sets["production"] = sorted(rep["multiplicity_rule_pr40"]["label_map"])
    if args.exact_report:
        rep = json.loads(pathlib.Path(args.exact_report).read_text())
        names = set()
        for s in rep["samples"].values():
            names |= set(s["histograms"]["per_histogram"])
        prod_pairs = set()
        for n in names:
            m = NAME_PATTERN.match(n)
            prod_pairs.add((name_to_label(m.group(2)), m.group(1)))
        pairs["production_exact_histograms"] = sorted(prod_pairs)
    if args.runs_dir:
        import sqlite3
        from studies.cms_mc_weights_v3.deliver.multiplicity_pr40 import ROW_PATTERN
        stored = set()
        shards = sorted(pathlib.Path(args.runs_dir).rglob("dataset_shard_rare4_inclusive.sqlite"))
        for shard in shards:
            conn = sqlite3.connect(f"file:{shard}?mode=ro", uri=True)
            try:
                for (sig,) in conn.execute("SELECT DISTINCT signature FROM array_chunks"):
                    m = ROW_PATTERN.match(sig)
                    if m and m.group("suffix") is None:
                        stored.add((m.group("fs"), m.group("im")))
            finally:
                conn.close()
        pairs["production_stored_pairs"] = sorted(stored)
        sets["production_stored_labels"] = sorted({lab for lab, _im in stored})
        print(f"read {len(shards)} shard(s): {len(stored)} stored (label, combination) pairs")
    out = {
        "combo_by_name": combo_by_name,
        "labels": {k: {lab: cap_label(lab) for lab in v} for k, v in sets.items()},
        "pairs": {k: [[lab, im, cap_label(lab), combination_allowed(cap_label(lab), im)]
                      for lab, im in v] for k, v in pairs.items()},
    }
    pathlib.Path(args.out).write_text(json.dumps(out))
    print(f"wrote {args.out}: " + ", ".join(
        f"{k}={len(v)} labels" for k, v in out["labels"].items()) + ", " + ", ".join(
        f"{k}={len(v)} pairs" for k, v in out["pairs"].items()))


def side_oracle(args) -> None:
    tree = pathlib.Path(args.oracle_tree).resolve()
    sys.path.insert(0, str(tree))
    from services.calculations import physics_calcs as pc  # c2488b7's own
    assert pathlib.Path(pc.__file__).resolve().is_relative_to(tree), pc.__file__
    ans = json.loads(pathlib.Path(args.answers).read_text())
    result = {"oracle_tree": str(tree),
              "oracle_module": str(pathlib.Path(pc.__file__).resolve()),
              "labels": {}, "pairs": {}}
    for k, mapping in ans["labels"].items():
        bad = [(lab, ours, pc.limit_particles_in_fs(lab, 4)) for lab, ours in mapping.items()
               if pc.limit_particles_in_fs(lab, 4) != ours]
        result["labels"][k] = {"n_checked": len(mapping), "n_agree": len(mapping) - len(bad),
                               "disagreements": bad[:50]}
    for k, rows in ans["pairs"].items():
        bad = []
        n_allowed = 0
        for lab, im, capped, ours in rows:
            if capped != pc.limit_particles_in_fs(lab, 4):
                bad.append([lab, im, "capped label differs"])
                continue
            combo = {t: tuple(v) for t, v in ans["combo_by_name"][im].items()}
            theirs = pc.is_finalstate_contain_combination(capped, combo)
            n_allowed += bool(theirs)
            if theirs != ours:
                bad.append([lab, im, capped, ours, theirs])
        result["pairs"][k] = {"n_checked": len(rows), "n_agree": len(rows) - len(bad),
                              "n_allowed_by_oracle": n_allowed, "disagreements": bad[:50]}
    pathlib.Path(args.out).write_text(json.dumps(result, indent=2))
    print(json.dumps({k: {kk: {x: y for x, y in vv.items() if x != "disagreements"}
                          for kk, vv in v.items()} for k, v in result.items()
                      if k in ("labels", "pairs")}, indent=1))
    if any(v["n_agree"] != v["n_checked"] for d in (result["labels"], result["pairs"])
           for v in d.values()):
        raise SystemExit("DISAGREEMENT with c2488b7 -- see " + args.out)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--side", choices=("cms", "oracle"), required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--report")
    p.add_argument("--exact-report")
    p.add_argument("--runs-dir")
    p.add_argument("--oracle-tree")
    p.add_argument("--answers")
    args = p.parse_args()
    (side_cms if args.side == "cms" else side_oracle)(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
