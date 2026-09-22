"""
Smoke-tests the pure-JSON parts of studies/m0m1j0_cms/cluster/merge_pilot.py
(cutflow summation, outlier/sanity-array concatenation, portal-identity
comparison, ROI_ name stripping) against synthetic job_N directories on
disk -- no ROOT, no network (fetch_file_list is monkeypatched).

Does NOT exercise merge_histograms/apply_merge_time_min_events_prune/the
plotting functions (those need real or stubbed ROOT TFile/TH1F::Clone/Add,
a larger stub than is worth building twice -- see
test_histograms_with_stub_root.py for the TH1F-level stub already used
elsewhere). Those remain UNVERIFIED until run on the real cluster, same as
the rest of this task's cluster-dependent code -- this test exists only to
catch bugs in the parts that CAN be checked without the cluster.

Run directly: python studies/m0m1j0_cms/tests/test_merge_pilot_json_logic.py
"""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
import types
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

# merge_pilot.py (like histograms.py) does `import ROOT`, and pulls in
# services/pipelines/histograms_pipeline.py which does `import fcntl` --
# neither is available on this Windows dev machine. Stub both so the
# module can be imported here to exercise its PURE-JSON functions;
# nothing in this test calls into ROOT.TFile/TH1F at all.
_fake_root = types.ModuleType("ROOT")
_fake_root.TH1F = type("TH1F", (), {})  # only needed as a type-annotation target
_fake_root.TFile = type("TFile", (), {})
sys.modules.setdefault("ROOT", _fake_root)
sys.modules.setdefault("fcntl", types.ModuleType("fcntl"))

import studies.m0m1j0_cms.design_checks.common as common_mod  # noqa: E402

FAILURES = []


def check(name: str, condition: bool, detail: str = ""):
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {name}" + (f" -- {detail}" if detail and not condition else ""))
    if not condition:
        FAILURES.append(name)


def make_fake_jobs(jobs_base: Path, portal_urls: dict):
    """portal_urls: {record_id: [url0, url1]} -- what fetch_file_list will
    "currently" return; job 3 will be made to recall a DIFFERENT url than
    what's "currently" on the portal, to exercise the mismatch-detection path."""
    mapping = {1: (30522, 0), 2: (30522, 1), 3: (30555, 0), 4: (30555, 1)}
    for idx, (record_id, file_index) in mapping.items():
        job_dir = jobs_base / f"job_{idx}"
        job_dir.mkdir(parents=True, exist_ok=True)
        recorded_url = portal_urls[record_id][file_index]
        if idx == 3:
            recorded_url = "root://eospublic.cern.ch//eos/opendata/cms/STALE_FILE.root"
        (job_dir / "job_metadata.json").write_text(json.dumps({
            "file_url": recorded_url,
            "git_commit": "deadbeef",
            "cutflow": {
                "n_read": 1000 + idx, "n_after_golden_json": 900 + idx,
                "n_after_trigger": 800 + idx, "n_after_ge2mu": 50 + idx,
                "n_after_ge1jet_after_cleaning": 20 + idx,
                "n_after_z_peak_and_mass_cutoff": 10 + idx, "n_outliers_gt_1tev": 1,
            },
        }), encoding="utf-8")
        (job_dir / "outliers_gt_1tev.json").write_text(json.dumps([
            {"run": 1, "luminosityBlock": 1, "event": idx, "m0m1j0_gev": 1234.5, "category": "mass_m0m1j0_cat_0ex_2mx_1jx_0gx_0tx_0bx"}
        ]), encoding="utf-8")
        (job_dir / "sanity_arrays.json").write_text(json.dumps({
            "dimuon_mass_gev": [90.0 + idx, 91.0 + idx],
            "leading_jet_pt_gev": [50.0 + idx],
        }), encoding="utf-8")
    # job_4 deliberately left WITHOUT a job_metadata.json to exercise the
    # "missing job" path -- overwrite what the loop above wrote.
    shutil.rmtree(jobs_base / "job_4")


def main():
    portal_urls = {
        30522: ["root://eospublic.cern.ch//eos/opendata/cms/G_0.root", "root://eospublic.cern.ch//eos/opendata/cms/G_1.root"],
        30555: ["root://eospublic.cern.ch//eos/opendata/cms/H_0.root", "root://eospublic.cern.ch//eos/opendata/cms/H_1.root"],
    }
    common_mod.fetch_file_list = lambda record_id: portal_urls[record_id]

    # merge_pilot imports fetch_file_list at module level via
    # "from studies.m0m1j0_cms.design_checks.common import fetch_file_list"
    # -- patch it there too (import happens after common_mod is patched
    # above only if we import merge_pilot AFTER this point).
    import studies.m0m1j0_cms.cluster.merge_pilot as merge_pilot
    merge_pilot.fetch_file_list = lambda record_id: portal_urls[record_id]

    with tempfile.TemporaryDirectory() as tmp:
        jobs_base = Path(tmp) / "jobs"
        make_fake_jobs(jobs_base, portal_urls)

        identity = merge_pilot.check_portal_identity(jobs_base)
        check("job_1 (record 30522, file 0) matches current portal", identity["per_job"][1]["matches_current_portal"] is True)
        check("job_3 (deliberately stale) does NOT match current portal", identity["per_job"][3]["matches_current_portal"] is False)
        check("job_4 missing metadata is reported as such", identity["per_job"][4]["status"] == "MISSING_METADATA")
        check("problems list is non-empty (job_3 mismatch + job_4 missing)", len(identity["problems"]) >= 1, f"got {identity['problems']}")

        present_indices = [1, 2, 3]  # job_4 has no metadata
        cutflow = merge_pilot.sum_cutflow(jobs_base, present_indices)
        check(
            "cutflow sums n_read across present jobs (1001+1002+1003)",
            cutflow["n_read"] == 1001 + 1002 + 1003,
            f"got {cutflow['n_read']}",
        )

        outliers = merge_pilot.merge_outliers(jobs_base, present_indices)
        check("outliers merged from 3 present jobs (1 each)", len(outliers) == 3, f"got {len(outliers)}")

        sanity = merge_pilot.merge_sanity_arrays(jobs_base, present_indices)
        check("dimuon_mass_gev concatenated (2 per job x 3 jobs)", len(sanity["dimuon_mass_gev"]) == 6, f"got {sanity}")

        check(
            "ROI_ name stripping recovers the grouping name",
            merge_pilot._bumpnet_name_from_root_name("ROI_mass_m0m1j0_cat_0ex_2mx_1jx_0gx_width_10")
            == "mass_m0m1j0_cat_0ex_2mx_1jx_0gx",
        )

    print()
    if FAILURES:
        print(f"{len(FAILURES)} FAILURE(S): {FAILURES}")
        sys.exit(1)
    else:
        print("All merge_pilot JSON-logic self-checks passed.")


if __name__ == "__main__":
    main()
