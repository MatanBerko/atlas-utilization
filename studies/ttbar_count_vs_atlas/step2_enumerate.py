#!/usr/bin/env python
"""
Step 2 (ttbar_count_vs_atlas): enumerate, for every category allowed by the
rule, the invariant-mass combinations the pipeline would produce.

This script is deliberately side-agnostic: it is run TWICE, once inside our
own checkout and once inside a read-only checkout of upstream
refs/pull/31/head, and each run imports `services.calculations.*` from
whichever repo is on PYTHONPATH.  Nothing is imported from the other side,
so the two answers are genuinely produced by the two codebases.

  --side ours   : combinatorics parameters are read from
                  studies.cms_datasets.cluster.run_dataset_on_file's own
                  module-level constants (the values the production driver
                  actually passes to get_all_combinations), and containment
                  is decided by the function the driver actually calls,
                  services.calculations.physics_calcs.is_finalstate_contain_combination.

  --side pr31   : combinatorics parameters are read from PR #31's own
                  config.yaml (mass_calculation_task_config), and containment
                  is decided by the function PR #31's im_pipeline actually
                  calls, IMCalculator.does_final_state_contain_combination.

Category rule (given): e, mu, j, b each 0-4, e + mu + b <= 4, and at least 2
objects in total.  `j` is the LIGHT-jet count; 4 means "4" for PR #31 and
">= 4" for us (our label is capped at 4), which is exactly the asymmetry the
study is about -- it does not change the combination list for the label.

Writes a JSON file: {"side", "n_combinations", "combinations": [...],
"categories": {label: [combo_key, ...]}, "config": {...}}.
"""
import argparse
import json
import os
import sys


def combo_key(combination):
    """Stable, side-independent text key for one combination dict.

    Sorted by particle-type name so dict insertion order can never make two
    identical combinations compare unequal across the two codebases.
    """
    from services.calculations.combinatorics import get_count, get_start
    parts = []
    for ptype in sorted(combination):
        parts.append(f"{ptype}:{get_count(combination[ptype])}@{get_start(combination[ptype])}")
    return "+".join(parts)


def build_categories(max_per_type=4, max_nonlight=4, min_total=2):
    """Every (e, mu, j, b) allowed by the rule, in a deterministic order."""
    cats = []
    for e in range(max_per_type + 1):
        for m in range(max_per_type + 1):
            for b in range(max_per_type + 1):
                if e + m + b > max_nonlight:
                    continue
                for j in range(max_per_type + 1):
                    if e + m + j + b < min_total:
                        continue
                    cats.append((e, m, j, b))
    return cats


def cat_name(e, m, j, b):
    """Short human-readable category name, shared by both sides."""
    return f"{e}e_{m}m_{j}j_{b}b"


def fs_label_ours(e, m, j, b):
    """The final-state string our driver builds (always all six types).

    See studies/cms_datasets/cluster/run_dataset_on_file.py
    _group_by_final_state_with_mask.
    """
    return f"{e}e_{m}m_{j}j_0g_0t_{b}b"


def fs_label_pr31(e, m, j, b):
    """The final-state string PR #31 builds for a record whose fields are
    exactly Electrons/Muons/Jets/BJets (its own objects_to_calculate), i.e.
    only the present types appear.  See its IMCalculator._get_all_events_fs.
    """
    return f"{e}e_{m}m_{j}j_{b}b"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--side", required=True, choices=["ours", "pr31"])
    p.add_argument("--repo", required=True, help="repo root (must also be on PYTHONPATH)")
    p.add_argument("--out", required=True)
    args = p.parse_args()

    # Guard against silently importing the wrong repo's services/ package.
    import services.calculations.combinatorics as _comb
    resolved = os.path.realpath(_comb.__file__)
    expected = os.path.realpath(os.path.join(args.repo, "services", "calculations", "combinatorics.py"))
    if resolved != expected:
        raise SystemExit(
            f"WRONG REPO: imported {resolved}, expected {expected}. "
            f"Set PYTHONPATH to {args.repo} only."
        )

    from services.calculations.combinatorics import get_all_combinations

    if args.side == "ours":
        import studies.cms_datasets.cluster.run_dataset_on_file as drv
        cfg = {
            "object_types": list(drv.OBJECT_TYPES),
            "min_particles": drv.MIN_PARTICLES_IN_COMBINATION,
            "max_particles": drv.MAX_PARTICLES_IN_COMBINATION,
            "min_count": drv.MIN_COUNT_PARTICLE_IN_COMBINATION,
            "max_count": drv.MAX_COUNT_PARTICLE_IN_COMBINATION,
            "max_total_particles": drv.MAX_TOTAL_PARTICLES_IN_COMBINATION,
            "include_subleading": drv.INCLUDE_SUBLEADING,
            "max_subleading_index": drv.MAX_SUBLEADING_INDEX,
        }
        cfg_source = "studies/cms_datasets/cluster/run_dataset_on_file.py module constants"
        from services.calculations.physics_calcs import is_finalstate_contain_combination as contains
        contains_source = "services.calculations.physics_calcs.is_finalstate_contain_combination"
        label_of = fs_label_ours
    else:
        import yaml
        with open(os.path.join(args.repo, "config.yaml")) as fh:
            y = yaml.safe_load(fh)
        mc = y["mass_calculation_task_config"]
        cfg = {
            "object_types": list(mc["objects_to_calculate"]),
            "min_particles": mc["min_particles_in_combination"],
            "max_particles": mc["max_particles_in_combination"],
            "min_count": mc["min_count_particle_in_combination"],
            "max_count": mc["max_count_particle_in_combination"],
            "max_total_particles": mc["max_total_particles_in_combination"],
            "include_subleading": mc["include_subleading"],
            "max_subleading_index": mc["max_subleading_index"],
        }
        cfg_source = "PR #31 config.yaml mass_calculation_task_config"
        from services.calculations.im_calculator import IMCalculator
        contains = IMCalculator.does_final_state_contain_combination
        contains_source = "services.calculations.im_calculator.IMCalculator.does_final_state_contain_combination"
        label_of = fs_label_pr31

    combinations = get_all_combinations(
        object_types=cfg["object_types"],
        min_particles=cfg["min_particles"],
        max_particles=cfg["max_particles"],
        min_count=cfg["min_count"],
        max_count=cfg["max_count"],
        max_total_particles=cfg["max_total_particles"],
        include_subleading=cfg["include_subleading"],
        max_subleading_index=cfg["max_subleading_index"],
    )

    keys = [combo_key(c) for c in combinations]
    if len(set(keys)) != len(keys):
        raise SystemExit("duplicate combination keys -- combo_key is not injective here")

    categories = {}
    for (e, m, j, b) in build_categories():
        label = label_of(e, m, j, b)
        matched = [k for k, c in zip(keys, combinations) if contains(label, c)]
        categories[cat_name(e, m, j, b)] = sorted(matched)

    out = {
        "side": args.side,
        "repo": args.repo,
        "repo_head": os.environ.get("REPO_HEAD", ""),
        "config": cfg,
        "config_source": cfg_source,
        "containment_function": contains_source,
        "fs_label_example": label_of(1, 2, 3, 1),
        "n_combinations": len(combinations),
        "combinations": sorted(keys),
        "n_categories": len(categories),
        "categories": categories,
    }
    with open(args.out, "w") as fh:
        json.dump(out, fh, indent=1, sort_keys=True)
    print(f"[{args.side}] combinations={len(combinations)} categories={len(categories)} -> {args.out}")
    print(f"[{args.side}] imported services from {resolved}")


if __name__ == "__main__":
    sys.exit(main())
