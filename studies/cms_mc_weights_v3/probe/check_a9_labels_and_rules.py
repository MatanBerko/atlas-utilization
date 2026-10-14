#!/usr/bin/env python
"""
Part A9: fork master's exact-label implementation vs upstream PR #34
(upstream master f16768e).

Pure-python, no files read, no network. Checks four things and prints one
JSON blob:

  1. The combination set is the delivered 186, and the largest
     (start + count) requirement over it, per object type. This is what
     decides whether the fork's single-character count parse in the shared
     services/calculations/physics_calcs.py::is_finalstate_contain_combination
     can change any delivered answer for a two-digit count such as "10j".
  2. The BumpNet histogram name a two-digit jet count produces, under the
     name-building rule that fork master and f16768e share verbatim.
  3. The signature-grouping regex's behaviour on a two-digit count.
  4. The event-acceptance divergence between upstream #34's per-type rule
     (reject a non-Jets type whose count exceeds max_k, plus the
     distinct-type-count window min_n..max_n) and the fork's delivered
     Version B rule (reject if electrons + muons + b-jets > 4).

Run:  python studies/cms_mc_weights_v3/probe/check_a9_labels_and_rules.py
"""
from __future__ import annotations

import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3]))

from services.calculations.combinatorics import (  # noqa: E402
    get_all_combinations, get_count, get_start,
)

# Copied from studies/cms_datasets/cluster/run_dataset_on_file.py (the
# delivered production driver), not retyped from any document.
OBJECT_TYPES = ["Electrons", "Muons", "Jets", "BJets"]
MIN_PARTICLES, MAX_PARTICLES = 1, 4
MIN_COUNT, MAX_COUNT = 1, 4
MAX_TOTAL_PARTICLES = 4
INCLUDE_SUBLEADING, MAX_SUBLEADING_INDEX = True, 1

# Upstream's IMCalculator is constructed with these in
# orchestration/handlers/mass_calculation_handler.py at f16768e, from
# config.yaml's mass_calculation_config.
UPSTREAM_MIN_K, UPSTREAM_MAX_K = 1, 4
UPSTREAM_MIN_N, UPSTREAM_MAX_N = 1, 4


def bumpnet_name(fs_str: str, im_str: str) -> str:
    """The name rule shared verbatim by studies/m0m1j0_cms/histograms.py
    (fork master) and services/pipelines/histograms_pipeline.py (f16768e)."""
    combo = im_str if im_str else "none"
    fs_particles = re.findall(r"(\d+)([emjgtb])", fs_str)
    return f"mass_{combo}_cat_" + "_".join(f"{c}{p}x" for c, p in fs_particles)


def fork_parse(fs: str) -> list[tuple[str, str]]:
    """The fork's shared physics_calcs count parse at db1bd32: first char is
    the count, second char is the particle letter."""
    return [(tok[0], tok[1]) for tok in fs.split("_") if len(tok) >= 2]


def upstream_parse(fs: str) -> list[tuple[str, str]]:
    """The same parse after PR #34: all but the last char is the count."""
    return [(tok[:-1], tok[-1]) for tok in fs.split("_") if len(tok) >= 2]


def upstream34_keeps(counts, names) -> bool:
    """upstream f16768e services/calculations/im_calculator.py::_is_valid_fs."""
    present = [(n, c) for n, c in zip(names, counts) if c > 0]
    if len(present) < UPSTREAM_MIN_N or len(present) > UPSTREAM_MAX_N:
        return False
    for name, count in present:
        if count < UPSTREAM_MIN_K:
            return False
        if name != "Jets" and count > UPSTREAM_MAX_K:
            return False
    return True


def fork_version_b_keeps(counts, names) -> bool:
    """The delivered Version B (rare4) rule: reject if e + mu + b > 4."""
    d = dict(zip(names, counts))
    return d["Electrons"] + d["Muons"] + d["BJets"] <= 4


def main() -> int:
    combos = get_all_combinations(
        object_types=OBJECT_TYPES,
        min_particles=MIN_PARTICLES, max_particles=MAX_PARTICLES,
        min_count=MIN_COUNT, max_count=MAX_COUNT,
        max_total_particles=MAX_TOTAL_PARTICLES,
        include_subleading=INCLUDE_SUBLEADING,
        max_subleading_index=MAX_SUBLEADING_INDEX,
    )
    out: dict = {"n_combinations": len(combos)}

    max_req: dict[str, int] = {}
    for combo in combos:
        for particle, value in combo.items():
            max_req[particle] = max(
                max_req.get(particle, 0), get_start(value) + get_count(value)
            )
    out["max_start_plus_count_per_type"] = max_req
    out["max_start_plus_count_overall"] = max(max_req.values())

    out["name_for_5j"] = bumpnet_name("0e_2m_5j_1b", "m0m1")
    out["name_for_10j"] = bumpnet_name("0e_2m_10j_1b", "m0m1")

    signature = "job_FS_0e_2m_10j_1b_IM_m0m1_main"
    cleaned = signature[: -len("_main")]
    match = re.search(r"_FS_([0-9emjgtb_]+)_IM_([emjgtb\d]+)$", cleaned)
    out["grouping_regex_matches_two_digit_count"] = bool(match)
    out["grouping_regex_groups"] = list(match.groups()) if match else None

    out["fork_parse_of_10j_label"] = fork_parse("0e_2m_10j_1b")
    out["upstream_parse_of_10j_label"] = upstream_parse("0e_2m_10j_1b")

    names = OBJECT_TYPES
    divergences = []
    for e in range(7):
        for mu in range(7):
            for j in range(3):
                for b in range(7):
                    counts = (e, mu, j, b)
                    up = upstream34_keeps(counts, names)
                    fk = fork_version_b_keeps(counts, names)
                    if up != fk:
                        divergences.append({
                            "label": f"{e}e_{mu}m_{j}j_{b}b",
                            "upstream34_keeps": up,
                            "fork_version_b_keeps": fk,
                        })
    out["divergence_scan_range"] = "e,m,b in 0..6 and j in 0..2"
    out["n_divergent_count_patterns"] = len(divergences)
    out["n_upstream_keeps_fork_rejects"] = sum(
        1 for d in divergences if d["upstream34_keeps"])
    out["n_fork_keeps_upstream_rejects"] = sum(
        1 for d in divergences if d["fork_version_b_keeps"])
    out["divergence_examples"] = divergences[:12]
    out["fork_keeps_upstream_rejects_cases"] = [
        d["label"] for d in divergences if d["fork_version_b_keeps"]]

    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
