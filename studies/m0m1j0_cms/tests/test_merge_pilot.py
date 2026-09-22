"""
Self-checks for studies/m0m1j0_cms/cluster/merge_pilot.py.

Replaces the earlier test_merge_pilot_json_logic.py (removed): after the
2026-09-22 pilot run discovered the cluster's atlas-pipeline conda env has
no PyROOT at all (see studies/m0m1j0_cms/histograms.py's module
docstring), merge_pilot.py was rewritten to use uproot instead of PyROOT
for all histogram I/O -- which means this test no longer needs to stub
ROOT/fcntl at all; it builds REAL small ROOT files via uproot (the same
library the actual cluster jobs use) and exercises merge_pilot.py's
histogram-summing and merge-time min_events_per_fs pruning against them
directly, on top of the JSON-only checks the earlier version had
(cutflow summation, outlier/sanity-array concatenation, portal-identity
comparison, ROI_ name stripping).

Run directly: python studies/m0m1j0_cms/tests/test_merge_pilot.py
"""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

import awkward as ak  # noqa: E402
import numpy as np  # noqa: E402
import uproot  # noqa: E402

import studies.m0m1j0_cms.design_checks.common as common_mod  # noqa: E402
from studies.m0m1j0_cms import histograms  # noqa: E402

FAILURES = []


def check(name: str, condition: bool, detail: str = ""):
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {name}" + (f" -- {detail}" if detail and not condition else ""))
    if not condition:
        FAILURES.append(name)


def write_job(job_dir: Path, record_id: int, file_index: int, recorded_url: str,
              n_muons_per_event: list, n_read: int):
    """Builds a real all_histograms.root + job_metadata.json for one
    synthetic job, using the REAL histograms.build_m0m1j0_histograms and
    a real uproot.recreate write (exactly what run_m0m1j0_on_file.py
    does), so merge_pilot.py's reading code is exercised against genuine
    files, not a mock."""
    job_dir.mkdir(parents=True, exist_ok=True)
    n = len(n_muons_per_event)
    obj_record = ak.Array({
        "Electrons": [[] for _ in range(n)],
        "Muons": [[1] * c for c in n_muons_per_event],
        "Jets": [[1]] * n,
        "BJets": [[] for _ in range(n)],
    })
    mass = ak.Array([200.0 + 10.0 * i for i in range(n)])
    hists, hist_meta = histograms.build_m0m1j0_histograms(obj_record, mass, apply_min_events_prune=False)

    with uproot.recreate(str(job_dir / "all_histograms.root")) as f:
        for name, (values, edges) in hists.items():
            f[f"ROI_{name}_width_10"] = (values, edges)

    (job_dir / "job_metadata.json").write_text(json.dumps({
        "file_url": recorded_url,
        "git_commit": "deadbeef",
        "per_category": hist_meta,
        "cutflow": {
            "n_read": n_read, "n_after_golden_json": n_read, "n_after_trigger": n_read,
            "n_after_ge2mu": n, "n_after_ge1jet_after_cleaning": n,
            "n_after_z_peak_and_mass_cutoff": n, "n_outliers_gt_1tev": 0,
        },
    }), encoding="utf-8")
    (job_dir / "outliers_gt_1tev.json").write_text("[]", encoding="utf-8")
    (job_dir / "sanity_arrays.json").write_text(json.dumps({
        "dimuon_mass_gev": [91.0] * n, "leading_jet_pt_gev": [50.0] * n,
    }), encoding="utf-8")


def main():
    portal_urls = {
        30522: ["root://eospublic.cern.ch//eos/opendata/cms/G_0.root", "root://eospublic.cern.ch//eos/opendata/cms/G_1.root"],
        30555: ["root://eospublic.cern.ch//eos/opendata/cms/H_0.root", "root://eospublic.cern.ch//eos/opendata/cms/H_1.root"],
    }
    common_mod.fetch_file_list = lambda record_id: portal_urls[record_id]

    import studies.m0m1j0_cms.cluster.merge_pilot as merge_pilot
    merge_pilot.fetch_file_list = lambda record_id: portal_urls[record_id]

    with tempfile.TemporaryDirectory() as tmp:
        jobs_base = Path(tmp) / "jobs"

        # 4 events with 2 muons each across jobs 1+2 (2 each) -- combined
        # population of 4, well below MIN_EVENTS_PER_FINAL_STATE (100) so
        # the 2-muon category must be dropped at merge time; jobs 3+4
        # deliberately have 0 events, matching a real "no events in this
        # file" edge case.
        write_job(jobs_base / "job_1", 30522, 0, portal_urls[30522][0], [2, 2], n_read=500)
        write_job(jobs_base / "job_2", 30522, 1, portal_urls[30522][1], [2, 2], n_read=500)
        write_job(jobs_base / "job_3", 30555, 0, "root://eospublic.cern.ch//eos/opendata/cms/STALE.root", [], n_read=300)
        write_job(jobs_base / "job_4", 30555, 1, portal_urls[30555][1], [], n_read=300)

        present_indices = [1, 2, 3, 4]

        identity = merge_pilot.check_portal_identity(jobs_base)
        check("job_1 matches current portal", identity["per_job"][1]["matches_current_portal"] is True)
        check("job_3 (deliberately stale) does NOT match current portal", identity["per_job"][3]["matches_current_portal"] is False)

        merged_hists = merge_pilot.merge_histograms(jobs_base, present_indices)
        inclusive_key = next(k for k in merged_hists if merge_pilot._bumpnet_name_from_root_name(k) == histograms.INCLUSIVE_HIST_NAME)
        inclusive_values, inclusive_edges = merged_hists[inclusive_key]
        check(
            "merged inclusive histogram has 4 total entries (2+2+0+0 across 4 jobs)",
            inclusive_values.sum() == 4.0,
            f"got {inclusive_values.sum()}",
        )
        check("merged histogram edges are the fixed 0-10000 GeV grid", inclusive_edges[0] == 0.0 and inclusive_edges[-1] == 10000.0)

        per_category_counts = merge_pilot.sum_per_category_counts(jobs_base, present_indices)
        expected_2m_name = "mass_m0m1j0_cat_0ex_2mx_1jx_0gx_0tx_0bx"
        check(
            "per-category counts sum the 2-muon category to 4 across jobs 1+2",
            per_category_counts.get(expected_2m_name) == 4,
            f"got {per_category_counts}",
        )

        kept, dropped = merge_pilot.apply_merge_time_min_events_prune(merged_hists, per_category_counts)
        check(
            "2-muon category (4 events total, < 100) is pruned at merge time",
            not any(merge_pilot._bumpnet_name_from_root_name(k) == expected_2m_name for k in kept),
            f"kept keys: {list(kept.keys())}",
        )
        check(
            "dropped-categories list reports the 2-muon category with n_entries=4",
            any(d["name"] == expected_2m_name and d["n_entries"] == 4 for d in dropped),
            f"got {dropped}",
        )
        check(
            "inclusive histogram survives pruning regardless of its own count",
            any(merge_pilot._bumpnet_name_from_root_name(k) == histograms.INCLUSIVE_HIST_NAME for k in kept),
        )

        # Round-trip the merged histograms back through a real uproot.recreate
        # write + read, exactly as main() does, to catch any serialization bug.
        out_root = jobs_base / "merged_test.root"
        with uproot.recreate(str(out_root)) as f:
            for name, (values, edges) in kept.items():
                f[name] = (values, edges)
        f2 = uproot.open(str(out_root))
        check("merged ROOT file round-trips with the expected number of surviving histograms", len(f2.keys()) == len(kept), f"got {len(f2.keys())} vs {len(kept)}")

        cutflow = merge_pilot.sum_cutflow(jobs_base, present_indices)
        check("cutflow n_read sums to 500+500+300+300=1600", cutflow["n_read"] == 1600, f"got {cutflow['n_read']}")

        sanity = merge_pilot.merge_sanity_arrays(jobs_base, present_indices)
        check("dimuon_mass_gev concatenated across all 4 jobs (2+2+0+0)", len(sanity["dimuon_mass_gev"]) == 4, f"got {len(sanity['dimuon_mass_gev'])}")

    print()
    if FAILURES:
        print(f"{len(FAILURES)} FAILURE(S): {FAILURES}")
        sys.exit(1)
    else:
        print("All merge_pilot self-checks passed.")


if __name__ == "__main__":
    main()
