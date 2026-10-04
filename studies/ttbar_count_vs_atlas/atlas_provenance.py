#!/usr/bin/env python
"""
Follow-up Step A (ttbar_count_vs_atlas): provenance of Maryna's ATLAS ttbar
histogram file.

Everything here is derived from files that were COPIED out of Maryna's area
into work/ttbar_count_vs_atlas/atlas_input/ (sha256-verified against the
source) plus read-only `git` queries against her checkout. Nothing in
/storage/agrp/marybo/ is written, and her git repository is queried with
`--no-optional-locks` and a per-command `-c safe.directory=...` override, so
no config file anywhere is modified either.

Writes evidence/atlas_provenance.json and prints a short summary.

Usage:
    python atlas_provenance.py --atlas-input <dir> --checkout <her checkout> \
        --out <json>
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

import yaml

UPSTREAM_MASTER = "8120fb857da9b591f6d4b8914c7904036072c4b3"
PR31_HEAD = "81dd40aa6a0713088e811ae2732558766d854691"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def git(checkout: str, *args) -> str:
    """Read-only git against someone else's checkout."""
    cmd = ["git", "--no-optional-locks", "-c", f"safe.directory={checkout}",
           "-C", checkout, *args]
    r = subprocess.run(cmd, capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else f"<failed: {r.stderr.strip()[:200]}>"


def git_ok(checkout: str, *args) -> bool:
    cmd = ["git", "--no-optional-locks", "-c", f"safe.directory={checkout}",
           "-C", checkout, *args]
    return subprocess.run(cmd, capture_output=True, text=True).returncode == 0


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--atlas-input", required=True)
    p.add_argument("--checkout", required=True)
    p.add_argument("--out", required=True)
    args = p.parse_args()

    A = Path(args.atlas_input)
    C = args.checkout

    cfg = yaml.safe_load((A / "run_logs" / "config.yaml").read_text())
    parsing = cfg["parsing_task_config"]
    mass = cfg["mass_calculation_task_config"]
    post = cfg["post_processing_task_config"]
    hist = cfg["histogram_creation_task_config"]
    submit = (A / "run_logs" / "submit_mc.sh").read_text()
    pipeline_log = (A / "run_logs" / "pipeline.out").read_text()

    code = A / "code"
    pp_src = (code / "services/pipelines/post_processing_pipeline.py").read_text()
    im_src = (code / "services/calculations/im_calculator.py").read_text()
    es_src = (code / "services/parsing/event_selection.py").read_text()
    dc_src = (code / "domain/config.py").read_text()
    ph_src = (code / "orchestration/handlers/parsing_handler.py").read_text()

    head = git(C, "rev-parse", "HEAD")
    enable_or_in_config = "enable_overlap_removal" in parsing
    jets_max = parsing.get("particle_counts", {}).get("jets", {}).get("max")

    out = {
        "what": "provenance of Maryna's ATLAS ttbar BumpNet histogram file",
        "atlas_root_file": (
            "/storage/agrp/marybo/DDP/BumpNet4AtlasOpenData/Test_master_atlas-utilization/"
            "data/atlas_mc_UnlimetedJets_test_ttbar_mc_20261003_210612/histograms/"
            "atlas_opendata_bumpnet.root"),
        "atlas_root_file_readable": False,
        "sample_list_readable": False,
        "copied_inputs_sha256": {
            str(f.relative_to(A)): sha256(f)
            for f in sorted(A.rglob("*")) if f.is_file()
        },

        "checkout": {
            "path": C,
            "head_commit": head,
            "branch": git(C, "rev-parse", "--abbrev-ref", "HEAD"),
            "recent_commits": git(C, "log", "--oneline", "-8").splitlines(),
            "is_upstream_master": head == UPSTREAM_MASTER,
            "is_pr31": head == PR31_HEAD,
            "upstream_master_is_ancestor": git_ok(C, "merge-base", "--is-ancestor",
                                                  UPSTREAM_MASTER, "HEAD"),
            "pr31_is_ancestor": git_ok(C, "merge-base", "--is-ancestor", PR31_HEAD, "HEAD"),
            "merge_base_with_upstream_master": git(C, "merge-base", "HEAD", UPSTREAM_MASTER),
            "commits_on_her_branch_not_in_upstream_master":
                git(C, "log", "--oneline", f"{UPSTREAM_MASTER}..HEAD").splitlines(),
            "commits_in_upstream_master_not_on_her_branch":
                git(C, "log", "--oneline", f"HEAD..{UPSTREAM_MASTER}").splitlines(),
            "uncommitted_tracked_changes":
                [l for l in git(C, "status", "--porcelain").splitlines()
                 if not l.startswith("??")],
            "untracked_files_count":
                len([l for l in git(C, "status", "--porcelain").splitlines()
                     if l.startswith("??")]),
        },

        "config_used_for_this_run": {
            "source": "the run's own logs/config.yaml snapshot (copied, sha256-verified)",
            "which_config_file": "config.yaml, per submit_mc.sh in the same log directory",
            "submit_sets_CONFIG": [l.strip() for l in submit.splitlines()
                                   if l.strip().startswith("CONFIG=")],
            "run_name": cfg["names"]["run_name"],
            "trigger_config": cfg.get("trigger_config"),
            "parse_mc": parsing.get("parse_mc"),
            "max_files_to_process": parsing.get("max_files_to_process"),
            "enable_jet_tagging": parsing.get("enable_jet_tagging"),
            "jet_btagging_thresholds": parsing.get("jet_btagging_thresholds"),
            "particle_counts": parsing.get("particle_counts"),
            "kinematic_cuts": parsing.get("kinematic_cuts"),
            "objects_to_calculate": mass.get("objects_to_calculate"),
            "mass_calculation_task_config": mass,
            "post_processing_task_config": post,
            "histogram_creation_task_config": hist,
            "enable_overlap_removal_present_in_config": enable_or_in_config,
            "enable_overlap_removal_value": parsing.get("enable_overlap_removal"),
        },

        "answers": {
            "1_five_or_more_light_jets": {
                "verdict": "DROPPED - not grouped as 4j, and not kept as their own categories",
                "how": "READ (her own code + the run's own config snapshot)",
                "why": [
                    f"the run config sets particle_counts.jets.max = {jets_max}",
                    "her apply_parsing_event_selection passes particle_counts straight to "
                    "filter_events_by_particle_counts with is_particle_counts_range=True, "
                    "which builds the EVENT-level mask (obj_count >= min) & (obj_count <= max) "
                    "and drops events outside it -- she does NOT have PR #31's override that "
                    "raises the light-jet max to infinity (no LIGHT_JET_FIELD logic in her "
                    "event_selection.py at all)",
                    "and IMCalculator._is_valid_fs, with max_count_particle_in_combination = "
                    f"{mass.get('max_count_particle_in_combination')}, would drop any surviving "
                    "final state with a per-type count above that anyway",
                ],
                "caveat": "the run directory is named 'UnlimetedJets', which suggests the "
                          "opposite intent. The config snapshot stored with the run says "
                          "jets max 4. Worth confirming with Maryna.",
                "has_pr31_light_jet_override": "LIGHT_JET_FIELD" in es_src,
            },
            "2_jet_lepton_overlap_removal": {
                "verdict": "NOT APPLIED in this run, although the code for it is on her branch",
                "how": "READ (her parsing_handler.py, domain/config.py and the run config)",
                "why": [
                    "her branch adds ATLAS-style overlap removal (arXiv:1606.03903 Table 2) in "
                    "services/parsing/event_selection.apply_overlap_removal",
                    "parsing_handler.py calls it only under `if parsing_config.enable_overlap_removal:`",
                    "domain/config.py defines `enable_overlap_removal: bool = False` and reads it "
                    "with parsing_dict.get('enable_overlap_removal', False)",
                    f"the run's own config snapshot has no enable_overlap_removal key "
                    f"(present={enable_or_in_config}), so the default False applied",
                ],
                "apply_overlap_removal_defined": "def apply_overlap_removal" in es_src,
                "gated_on_enable_flag": "enable_overlap_removal" in ph_src,
                "default_is_false": "enable_overlap_removal: bool = False" in dc_src,
            },
            "3_btag_selection": {
                "verdict": "jet tagging ON; ATLAS DL1d discriminant with threshold 2.51",
                "how": "READ (run config snapshot + her file_parser b-tag split)",
                "enable_jet_tagging": parsing.get("enable_jet_tagging"),
                "thresholds": parsing.get("jet_btagging_thresholds"),
                "note": "btagDeepFlavB 0.5 is also listed but is the CMS branch; for ATLAS "
                        "PHYSLITE input the DL1d score (threshold 2.51) is the one in force.",
            },
            "4_upstream_27_present": {
                "verdict": "NO - upstream #27 is absent from her run",
                "how": "READ (git log) and RAN (hasattr probe on the copied module is not "
                       "possible without importing her tree; the textual check is definitive)",
                "evidence": "the ONLY commit upstream master has that her branch does not is "
                            "'Align outlier split to bin edges (#27)'",
                "has_aligned_bin_edges_helper": "_aligned_bin_edges" in pp_src,
            },
            "5_config_actually_used": "see config_used_for_this_run above",
        },

        "differences_from_what_the_original_task_assumed": [
            "Her file was NOT produced by PR #31. Her HEAD is ba57abc on branch "
            "feature/overlap-removal; neither PR #31 (81dd40a) nor upstream master "
            "(8120fb8) is an ancestor of it.",
            "Her branch = upstream master MINUS #27, PLUS 5 overlap-removal commits "
            "(which were not switched on for this run).",
            "min_events_per_fs is 10 in her run, not the 100 our pipeline uses.",
            "z_peak_cutoff is 110 GeV in her run, not the 115 GeV our pipeline uses.",
            "max_files_to_process is 40.",
        ],

        "counts_reported_in_her_pipeline_log": [
            l.strip() for l in pipeline_log.splitlines()
            if "2684" in l or "merged histogram" in l
        ][:6],
    }

    Path(args.out).write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"HEAD={out['checkout']['head_commit']} branch={out['checkout']['branch']}")
    print(f"is PR31: {out['checkout']['is_pr31']}   is upstream master: "
          f"{out['checkout']['is_upstream_master']}")
    print(f"PR31 ancestor: {out['checkout']['pr31_is_ancestor']}   "
          f"master ancestor: {out['checkout']['upstream_master_is_ancestor']}")
    print("in master but not hers:", out["checkout"]["commits_in_upstream_master_not_on_her_branch"])
    print("uncommitted TRACKED changes:", out["checkout"]["uncommitted_tracked_changes"] or "none")
    for k, v in out["answers"].items():
        if isinstance(v, dict):
            print(f"{k}: {v['verdict']}")
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
