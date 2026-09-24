"""
Full local integration test of studies/m0m1j0_cms/cluster/merge_full_v2.py:
builds synthetic job_1/job_2 outputs (real mass_by_category.npz files) and
a synthetic "v1 merged ROOT" file, mocks the portal calls used by the
reused identity-check functions, and runs merge_full_v2.main() end to
end -- twice: once where the A4 cross-check should PASS (v1's totals
genuinely match), and once where it's deliberately wrong, confirming the
script actually refuses to proceed rather than silently producing output
built on a mismatched premise.

Run directly: python studies/m0m1j0_cms/tests/test_merge_full_v2.py
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

import numpy as np  # noqa: E402
import uproot  # noqa: E402

import studies.m0m1j0_cms.design_checks.common as common_mod  # noqa: E402
from studies.m0m1j0_cms import histograms  # noqa: E402
from studies.m0m1j0_cms.postprocessing import apply_full_postprocessing  # noqa: E402

FAILURES = []


def check(name: str, condition: bool, detail: str = ""):
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {name}" + (f" -- {detail}" if detail and not condition else ""))
    if not condition:
        FAILURES.append(name)


CATEGORY = "mass_m0m1j0_cat_0ex_2mx_1jx_0gx_0tx_0bx"

# job_1: 178 raw events -- well above MIN_EVENTS_PER_FINAL_STATE (100),
# so this category actually survives the prune and its real
# post-processing chain (peak removal + outlier split) gets exercised,
# not just the "dropped, never post-processed" path. 5 below
# z_peak_cutoff (115 GeV, must be dropped), a dominant peak cluster at
# 200-205 GeV (150 events), 20 more spread 210-230 (so the local
# post-peak-removal bins 0/1 are both populated -- avoids the "skip
# splitting" edge case discovered in test_postprocessing.py), then an
# isolated tail at 900-905 GeV (3 events) that should end up in
# "_outliers", excluded from the histogram.
JOB1_RAW = np.concatenate([
    np.array([50.0, 60.0, 70.0, 90.0, 100.0]),      # below z_peak_cutoff
    np.linspace(200.0, 204.5, 150),                   # dominant peak cluster
    np.linspace(212.0, 229.0, 20),                    # populates local bin 1
    np.array([900.0, 902.0, 903.98]),                 # isolated tail -> outliers
])
JOB2_RAW = np.array([80.0, 95.0])  # both below z_peak_cutoff -- contributes 0 to n_after_z_peak


def build_synthetic_job(job_dir: Path, record_id: int, file_index: int, file_url: str, raw_mass: np.ndarray, n_read: int):
    job_dir.mkdir(parents=True, exist_ok=True)
    categories = np.array([CATEGORY] * len(raw_mass), dtype=object)
    np.savez_compressed(job_dir / "mass_by_category.npz", category=categories, m0m1j0_raw_gev=raw_mass)
    (job_dir / "job_metadata.json").write_text(json.dumps({
        "file_url": file_url,
        "cutflow": {"n_read": n_read},
    }), encoding="utf-8")


def build_v1_merged_root(path: Path, category_total: int, inclusive_total: int):
    """A synthetic v1 merged ROOT file whose per-category bin-content sum
    is EXACTLY what a real v1 run would have recorded for the SAME raw
    population, restricted to z_peak_cutoff+max_mass_cutoff only (no
    peak-removal/outlier-split -- that's what v1 never applied)."""
    values_cat = np.zeros(1000)
    values_cat[0] = category_total  # exact total, bin placement doesn't matter for the sum-based cross-check
    edges = np.linspace(0.0, 10000.0, 1001)
    values_inc = np.zeros(1000)
    values_inc[0] = inclusive_total

    with uproot.recreate(str(path)) as f:
        f[f"ROI_{CATEGORY}_width_10"] = histograms.to_writable_th1f(values_cat, edges, CATEGORY)
        f[f"ROI_mass_m0m1j0_inclusive_ge2m_ge1j_width_10"] = histograms.to_writable_th1f(
            values_inc, edges, "mass_m0m1j0_inclusive_ge2m_ge1j"
        )


def run_scenario(v1_category_total_override=None):
    """Returns (exit_code, summary_dict_or_None, root_path_str_or_None,
    real_after_cutoff, tmp_dir_to_clean_up). Reads everything needed out
    of the temp directory HERE, before it goes out of scope, rather than
    returning a Path into it -- tempfile.TemporaryDirectory() deletes its
    tree the moment its `with` block exits, including on an early
    `return` from inside it (discovered via this very test's first run:
    the caller's later `Path.read_text()` failed with FileNotFoundError
    even though the script itself had printed a successful write)."""
    portal_urls = {30522: ["root://fake/G_0.root", "root://fake/G_1.root"]}
    portal_counts = {30522: {"number_events": 180, "number_files": 2}}
    common_mod.fetch_file_list = lambda record_id: portal_urls[record_id]
    common_mod.fetch_record_number_events = lambda record_id: portal_counts[record_id]

    import studies.m0m1j0_cms.cluster.merge_full as merge_full
    merge_full.fetch_file_list = lambda record_id: portal_urls[record_id]
    merge_full.fetch_record_number_events = lambda record_id: portal_counts[record_id]
    merge_full.RECORDS = (30522,)

    original_uproot_open = uproot.open

    def fake_uproot_open(url):
        if isinstance(url, str) and url.startswith("root://fake/"):
            class _FakeEventsTree:
                num_entries = 178 if "G_0" in url else 2
            class _FakeFile:
                def __getitem__(self, key):
                    return _FakeEventsTree()
            return _FakeFile()
        return original_uproot_open(url)

    uproot.open = fake_uproot_open

    import studies.m0m1j0_cms.cluster.merge_full_v2 as merge_full_v2
    merge_full_v2.load_job_index_map = merge_full.load_job_index_map
    merge_full_v2.check_identity_and_counts = merge_full.check_identity_and_counts

    tmp = tempfile.mkdtemp()
    try:
        tmp_path = Path(tmp)
        jobs_base = tmp_path / "jobs"
        build_synthetic_job(jobs_base / "job_1", 30522, 0, portal_urls[30522][0], JOB1_RAW, n_read=178)
        build_synthetic_job(jobs_base / "job_2", 30522, 1, portal_urls[30522][1], JOB2_RAW, n_read=2)

        mapping_file = tmp_path / "job_index_map.txt"
        mapping_file.write_text("1 30522 0\n2 30522 1\n", encoding="utf-8")

        # Real expected count after z_peak_cutoff+max_mass_cutoff for the
        # combined raw population (JOB1_RAW + JOB2_RAW), computed via the
        # SAME real function this script itself uses, as ground truth for
        # what a genuinely-correct v1 total should be.
        combined_raw = np.concatenate([JOB1_RAW, JOB2_RAW])
        real_after_cutoff = apply_full_postprocessing(combined_raw, CATEGORY)["n_after_max_mass"]

        v1_root_path = tmp_path / "v1_merged.root"
        v1_total = v1_category_total_override if v1_category_total_override is not None else real_after_cutoff
        build_v1_merged_root(v1_root_path, v1_total, real_after_cutoff)

        out_dir = tmp_path / "v2_out"
        sys.argv = [
            "merge_full_v2.py",
            "--jobs-base", str(jobs_base),
            "--mapping-file", str(mapping_file),
            "--v1-merged-root", str(v1_root_path),
            "--out-dir", str(out_dir),
        ]
        exit_code = 0
        try:
            merge_full_v2.main()
        except SystemExit as e:
            exit_code = e.code
        finally:
            uproot.open = original_uproot_open

        summary_path = out_dir / "merge_v2_summary.json"
        summary = json.loads(summary_path.read_text()) if summary_path.exists() else None
        root_path = out_dir / "m0m1j0_data_postprocessed.root"
        root_classnames = None
        if root_path.exists():
            rf = uproot.open(str(root_path))
            root_classnames = [rf[k].classname for k in rf.keys()]

        return exit_code, summary, root_classnames, real_after_cutoff
    finally:
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    # --- Scenario 1: A4 cross-check should PASS ---
    exit_code, summary, root_classnames, real_after_cutoff = run_scenario(v1_category_total_override=None)
    check("scenario 1 (matching v1 totals): exits 0", exit_code == 0, f"got {exit_code}")
    check("scenario 1: complete is True", summary is not None and summary.get("complete") is True, f"got {summary}")
    check("scenario 1: a4_cross_check_passed is True", summary.get("a4_cross_check_passed") is True)

    cat_report = summary["per_category"][CATEGORY]
    check("category n_raw == 180 (178 from job1 + 2 from job2)", cat_report["n_raw"] == 180, f"got {cat_report}")
    check("category n_after_z_peak == 173 (5+2=7 of 180 below 115 GeV dropped)", cat_report["n_after_z_peak"] == 173, f"got {cat_report['n_after_z_peak']}")
    check("category is not pruned (180 raw >= MIN_EVENTS_PER_FINAL_STATE=100)", cat_report.get("pruned_by_min_events_per_fs") is False, f"got {cat_report}")
    check("category has 3 outliers (the isolated 900-905 GeV tail)", cat_report.get("n_outliers") == 3, f"got {cat_report}")
    check("category peak_mass lands near 200 GeV", cat_report.get("peak_mass_gev") is not None and 195.0 <= cat_report["peak_mass_gev"] <= 205.0, f"got {cat_report.get('peak_mass_gev')}")
    check("output histograms are genuinely TH1F", root_classnames is not None and all(c == "TH1F" for c in root_classnames), f"got {root_classnames}")

    # --- Scenario 2: A4 cross-check should FAIL (deliberately wrong v1 total) ---
    exit_code2, summary2, root_classnames2, _ = run_scenario(v1_category_total_override=real_after_cutoff + 100)
    check("scenario 2 (deliberately mismatched v1 total): exits non-zero", exit_code2 != 0, f"got {exit_code2}")
    check("scenario 2: complete is False", summary2 is not None and summary2.get("complete") is False, f"got {summary2}")
    check("scenario 2: a4_cross_check_passed is False", summary2.get("a4_cross_check_passed") is False)
    check(
        "scenario 2: the mismatch is reported by category name",
        any(CATEGORY in p for p in summary2.get("a4_cross_check_problems", [])),
        f"got {summary2.get('a4_cross_check_problems')}",
    )
    check("scenario 2: no output ROOT file was written (refused before producing results)", root_classnames2 is None, f"got {root_classnames2}")

    print()
    if FAILURES:
        print(f"{len(FAILURES)} FAILURE(S): {FAILURES}")
        sys.exit(1)
    else:
        print("All merge_full_v2.py integration checks passed.")


if __name__ == "__main__":
    main()
