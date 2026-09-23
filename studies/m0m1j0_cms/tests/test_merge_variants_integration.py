"""
Integration test for studies/m0m1j0_cms/cluster/merge_variants.py: builds a
small synthetic set of 2 "jobs" (each with job_metadata.json +
mass_by_category_<variant>.npz for all 4 variants), monkeypatches
fetch_file_list/fetch_record_number_events/uproot.open (no network), and
checks:
  1. Identity/completeness check passes with a matching mapping file.
  2. V0 cross-check PASSES when the reference JSON matches this run's own
     V0_baseline post-processing result exactly (built via the SAME
     apply_full_postprocessing function, not hand-computed, so this
     specifically tests the plumbing/field-matching, not the postprocessing
     math itself -- that's covered by test_postprocessing.py).
  3. V0 cross-check FAILS (exits non-zero, writes no ROOT files) when the
     reference JSON is deliberately wrong for one category.
  4. Per-variant ROOT files are written and readable, with the expected
     categories.
  5. ratio_to_v0 is 1.0 for V0's own inclusive entry compared to itself,
     and a sensible non-1.0 ratio for a variant with a different count.
  6. Diagnostics are correctly summed across the 2 synthetic jobs.

Run directly: python studies/m0m1j0_cms/tests/test_merge_variants_integration.py
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

import numpy as np  # noqa: E402
import uproot  # noqa: E402

import studies.m0m1j0_cms.cluster.merge_variants as merge  # noqa: E402
from studies.m0m1j0_cms.postprocessing import apply_full_postprocessing, raw_count_passes_min_events_prune  # noqa: E402
from studies.m0m1j0_cms import variants  # noqa: E402

FAILURES = []


def check(name: str, condition: bool, detail: str = ""):
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {name}" + (f" -- {detail}" if detail and not condition else ""))
    if not condition:
        FAILURES.append(name)


FAKE_URL_TEMPLATE = "root://fake/{record}/file{idx}.root"


def build_synthetic_jobs(jobs_base: Path, n_jobs: int, record_id: int, n_events_per_job: int):
    """2 categories: 'cat_A' (100+ events, survives min_events_per_fs) and
    'cat_small' (a handful, gets pruned). V1 has strictly MORE events in
    cat_A than V0 (simulating "removing a cut admits more events"); V2 has
    a completely different mass distribution for cat_A (simulating "leading
    jet changed, mass recomputed")."""
    rng = np.random.default_rng(42)
    per_job_mass = {}
    for job_i in range(1, n_jobs + 1):
        job_dir = jobs_base / f"job_{job_i}"
        job_dir.mkdir(parents=True, exist_ok=True)

        variant_masses = {}
        variant_masses["V0_baseline"] = {
            "cat_A": rng.uniform(120, 500, size=200).astype(np.float64),
            "cat_small": rng.uniform(120, 200, size=3).astype(np.float64),
        }
        variant_masses["V1_no_muon_iso"] = {
            "cat_A": np.concatenate([variant_masses["V0_baseline"]["cat_A"], rng.uniform(120, 500, size=50)]),
            "cat_small": variant_masses["V0_baseline"]["cat_small"],
        }
        variant_masses["V2_no_jet_lepton_cleaning"] = {
            "cat_A": rng.uniform(120, 900, size=200).astype(np.float64),  # different distribution
            "cat_small": variant_masses["V0_baseline"]["cat_small"],
        }
        variant_masses["V3_single_muon_trigger"] = {
            "cat_A": rng.uniform(120, 500, size=80).astype(np.float64),
            "cat_small": variant_masses["V0_baseline"]["cat_small"][:1],
        }

        per_variant_cutflow = {}
        per_variant_diagnostics = {}
        for v, cats in variant_masses.items():
            categories = np.concatenate([np.full(len(arr), cat) for cat, arr in cats.items()])
            masses = np.concatenate(list(cats.values()))
            np.savez_compressed(job_dir / f"mass_by_category_{v}.npz", category=categories, m0m1j0_raw_gev=masses)
            per_variant_cutflow[v] = {
                "n_read": n_events_per_job, "n_after_golden_json": n_events_per_job,
                "n_after_trigger": n_events_per_job, "n_after_ge2mu": len(masses),
                "n_after_ge1jet_after_cleaning": len(masses), "n_after_z_peak_and_mass_cutoff": len(masses),
            }
            per_variant_diagnostics[v] = {
                "n_diagnostic_population": len(masses), "n_dimuon_lt_2gev": 1, "n_dimuon_lt_4gev": 2,
                "frac_dimuon_lt_2gev": 1 / len(masses), "frac_dimuon_lt_4gev": 2 / len(masses),
            }
        per_variant_diagnostics["V2_no_jet_lepton_cleaning"].update({
            "n_diagnostic_population_v2": 200, "n_leading_jet_dr_lt_p4_to_muon": 40,
            "n_leading_jet_pt_within_10pct_of_muon": 20,
            "frac_leading_jet_dr_lt_p4_to_muon": 0.2, "frac_leading_jet_pt_within_10pct_of_muon": 0.1,
        })

        meta = {
            "record_id": record_id, "file_index": job_i - 1,
            "file_url": FAKE_URL_TEMPLATE.format(record=record_id, idx=job_i - 1),
            "n_read": n_events_per_job,
            "per_variant_cutflow": per_variant_cutflow,
            "per_variant_diagnostics": per_variant_diagnostics,
        }
        (job_dir / "job_metadata.json").write_text(json.dumps(meta), encoding="utf-8")
        per_job_mass[job_i] = variant_masses

    return per_job_mass


def build_v0_reference(all_per_job_mass: dict) -> dict:
    """Builds the 'existing v2 summary' reference by concatenating all
    jobs' V0_baseline raw masses per category and running the REAL
    apply_full_postprocessing on them -- i.e. what a correct merge run
    SHOULD produce, computed independently of merge_variants.py's own
    call to the same function (this test still catches plumbing/field-
    name bugs in merge_variants.py, since it does its own independent
    concatenation and dict-shape here)."""
    combined = {}
    for job_masses in all_per_job_mass.values():
        for cat, arr in job_masses["V0_baseline"].items():
            combined.setdefault(cat, []).append(arr)
    combined = {cat: np.concatenate(arrs) for cat, arrs in combined.items()}

    per_category = {}
    for cat, raw in combined.items():
        if not raw_count_passes_min_events_prune(len(raw)):
            per_category[cat] = {"n_raw": len(raw), "pruned_by_min_events_per_fs": True}
            continue
        r = apply_full_postprocessing(raw, cat)
        per_category[cat] = {
            "n_raw": r["n_raw"], "n_after_z_peak": r["n_after_z_peak"], "n_after_max_mass": r["n_after_max_mass"],
            "peak_mass_gev": r["peak_mass"], "n_main": r["n_main"], "n_outliers": r["n_outliers"],
            "split_mass_gev": r["split_mass"], "pruned_by_min_events_per_fs": False,
        }
    all_raw = np.concatenate(list(combined.values()))
    r = apply_full_postprocessing(all_raw, "inclusive")
    # matches merge_variants.V0_REFERENCE_INCLUSIVE_LABEL["ttbar"] -- this
    # test uses the ttbar (single-record) sample; see build_synthetic_jobs.
    per_category["mass_m0m1j0_inclusive_ge2m_ge1j_ttbar_postprocessed"] = {
        "n_raw": r["n_raw"], "n_after_z_peak": r["n_after_z_peak"], "n_after_max_mass": r["n_after_max_mass"],
        "peak_mass_gev": r["peak_mass"], "n_main": r["n_main"], "n_outliers": r["n_outliers"],
        "split_mass_gev": r["split_mass"], "pruned_by_min_events_per_fs": False,
    }
    return {"per_category": per_category}


def main():
    n_jobs = 2
    n_events_per_job = 5000
    record_id = 67801  # single-record sample (ttbar) -- matches SAMPLE_RECORDS["ttbar"]

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        jobs_base = tmp_path / "jobs"
        out_dir = tmp_path / "out"

        all_per_job_mass = build_synthetic_jobs(jobs_base, n_jobs, record_id, n_events_per_job)

        mapping_file = tmp_path / "job_index_map.txt"
        mapping_file.write_text("\n".join(f"{i} {record_id} {i - 1}" for i in range(1, n_jobs + 1)) + "\n")

        v0_ref = build_v0_reference(all_per_job_mass)
        v0_ref_path = tmp_path / "v0_reference.json"
        v0_ref_path.write_text(json.dumps(v0_ref), encoding="utf-8")

        # --- Monkeypatch network-touching functions ---
        original_fetch_list = merge.fetch_file_list
        original_fetch_num = merge.fetch_record_number_events
        original_uproot_open = uproot.open

        def fake_fetch_list(rid):
            return [FAKE_URL_TEMPLATE.format(record=rid, idx=i) for i in range(n_jobs)]

        def fake_fetch_num(rid):
            return {"number_events": n_events_per_job * n_jobs, "number_files": n_jobs}

        class FakeEventsTree:
            num_entries = n_events_per_job

        class FakeFile:
            def __getitem__(self, key):
                assert key == "Events"
                return FakeEventsTree()

        def fake_uproot_open(url):
            if isinstance(url, str) and url.startswith("root://fake/"):
                return FakeFile()
            return original_uproot_open(url)

        merge.fetch_file_list = fake_fetch_list
        merge.fetch_record_number_events = fake_fetch_num
        uproot.open = fake_uproot_open

        try:
            # --- 1+2: normal run, V0 cross-check should PASS ---
            sys.argv = [
                "merge_variants.py", "--sample", "ttbar",
                "--jobs-base", str(jobs_base), "--mapping-file", str(mapping_file),
                "--v0-cross-check-json", str(v0_ref_path), "--out-dir", str(out_dir),
            ]
            per_variant_histograms, result_summary = merge.main()

            check("identity check passed (no problems)", len(result_summary["identity_and_counts"]["problems"]) == 0)
            check("V0 cross-check passed", result_summary.get("v0_cross_check_passed") is True)
            check("merge marked complete", result_summary.get("complete") is True)

            for v in variants.VARIANT_ORDER:
                root_path = out_dir / f"ttbar_{v}.root"
                check(f"{v}: ROOT file written", root_path.exists())
                f = uproot.open(str(root_path))
                keys = set(k.split(";")[0] for k in f.keys())
                check(f"{v}: cat_A histogram present", any("cat_A" in k for k in keys), f"got {keys}")
                check(f"{v}: cat_small (below min_events_per_fs) NOT present", not any("cat_small" in k for k in keys), f"got {keys}")

            report = result_summary["per_variant"]
            v0_incl = report["V0_baseline"]["n_events_in_inclusive_histogram"]
            v1_incl = report["V1_no_muon_iso"]["n_events_in_inclusive_histogram"]
            check("V0 has fewer inclusive events than V1 (V1 admits more, by construction)", v0_incl < v1_incl, f"V0={v0_incl} V1={v1_incl}")
            check(
                "ratio_to_v0.inclusive for V0 itself is exactly 1.0",
                report["V0_baseline"]["ratio_to_v0"]["inclusive"] == 1.0,
                f"got {report['V0_baseline']['ratio_to_v0']['inclusive']}",
            )
            check(
                "ratio_to_v0.inclusive for V1 is > 1.0 (more events than V0)",
                report["V1_no_muon_iso"]["ratio_to_v0"]["inclusive"] > 1.0,
                f"got {report['V1_no_muon_iso']['ratio_to_v0']['inclusive']}",
            )

            check(
                "ttbar report has NO 'diagnostics' key (task's own diagnostics requirement is data-only)",
                "diagnostics" not in report["V0_baseline"],
            )

            # --- diagnostics-aggregation math, tested directly (data-only
            # feature; not exercised via the full main() run above, which
            # used the single-record ttbar sample) ---
            diag_totals = merge.load_per_variant_diagnostics(jobs_base, [1, 2])
            diag_v0 = diag_totals["V0_baseline"]
            check(
                "load_per_variant_diagnostics sums n_diagnostic_population across both jobs (2x203)",
                diag_v0["n_diagnostic_population"] == 2 * 203,
                f"got {diag_v0}",
            )
            diag_v2 = diag_totals["V2_no_jet_lepton_cleaning"]
            check(
                "load_per_variant_diagnostics sums V2 overlap diagnostics across both jobs (2x40)",
                diag_v2["n_leading_jet_dr_lt_p4_to_muon"] == 2 * 40,
                f"got {diag_v2}",
            )
            check(
                "load_per_variant_diagnostics computes fractions correctly",
                abs(diag_v0["frac_dimuon_lt_4gev"] - (2 * 2) / (2 * 203)) < 1e-9,
                f"got {diag_v0['frac_dimuon_lt_4gev']}",
            )

            # --- 3: deliberately wrong reference -> must FAIL loudly, no ROOT written ---
            bad_ref = json.loads(v0_ref_path.read_text())
            bad_ref["per_category"]["cat_A"]["n_main"] += 12345
            bad_ref_path = tmp_path / "bad_v0_reference.json"
            bad_ref_path.write_text(json.dumps(bad_ref), encoding="utf-8")

            out_dir_fail = tmp_path / "out_fail"
            sys.argv = [
                "merge_variants.py", "--sample", "ttbar",
                "--jobs-base", str(jobs_base), "--mapping-file", str(mapping_file),
                "--v0-cross-check-json", str(bad_ref_path), "--out-dir", str(out_dir_fail),
            ]
            try:
                merge.main()
                check("cross-check with a deliberately-wrong reference exits non-zero", False, "main() returned normally instead of exiting")
            except SystemExit as e:
                check("cross-check with a deliberately-wrong reference exits non-zero", e.code != 0, f"exit code {e.code}")
            check(
                "no ROOT file written when the cross-check fails",
                not any((out_dir_fail).glob("*.root")),
            )

        finally:
            merge.fetch_file_list = original_fetch_list
            merge.fetch_record_number_events = original_fetch_num
            uproot.open = original_uproot_open

    print()
    if FAILURES:
        print(f"{len(FAILURES)} FAILURE(S): {FAILURES}")
        sys.exit(1)
    else:
        print("All merge_variants.py integration checks passed.")


if __name__ == "__main__":
    main()
