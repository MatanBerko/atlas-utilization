"""
Full local integration test of studies/m0m1j0_cms/cluster/merge_full.py:
builds synthetic job_1..job_5 output directories (real ROOT files via
histograms.build_m0m1j0_histograms + to_writable_th1f + uproot, real
job_metadata.json/outliers/sanity_arrays/dimuon_diagnostics.npz shaped
exactly as run_m0m1j0_on_file.py writes them), mocks fetch_file_list /
fetch_record_number_events / the XRootD re-open used for the per-file
count check, and runs merge_full.main() end to end -- checking the real
files it writes (merge_summary.json, the merged TH1F ROOT file, the
diagnostic-variants ROOT file, and all PNGs), not just the individual
helper functions (those are covered elsewhere).

Includes one deliberately-broken job (a re-open "entry count mismatch")
and one deliberately-missing job, to confirm the completeness check
correctly refuses "complete" and reports specific, actionable problems --
not just that it accepts a clean run.

Run directly: python studies/m0m1j0_cms/tests/test_merge_full.py
"""
from __future__ import annotations

import json
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


def write_job(job_dir: Path, record_id: int, file_index: int, file_url: str,
              n_muons_per_event: list, n_read: int, extra_dupe_events: int = 0):
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
            key = f"ROI_{name}_width_10"
            f[key] = histograms.to_writable_th1f(values, edges, key)

    (job_dir / "job_metadata.json").write_text(json.dumps({
        "file_url": file_url,
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

    # dimuon_diagnostics.npz: mostly normal pairs, a few near-duplicate-like
    # low-mass pairs (small deltaR, pt ratio ~1, same charge) mixed in.
    m_mumu = np.full(n, 91.0, dtype=np.float32)
    dr = np.full(n, 2.5, dtype=np.float32)
    charge_product = np.full(n, -1, dtype=np.int8)
    pt_ratio = np.full(n, 0.7, dtype=np.float32)
    if extra_dupe_events:
        m_mumu[:extra_dupe_events] = 1.0
        dr[:extra_dupe_events] = 0.005
        charge_product[:extra_dupe_events] = 1
        pt_ratio[:extra_dupe_events] = 0.99
    fields = {
        "run": np.full(n, 111, dtype=np.int32),
        "luminosityBlock": np.arange(1, n + 1, dtype=np.int32),
        "event": np.arange(1, n + 1, dtype=np.int64),
        "m_mumu_gev": m_mumu,
        "deltaR_mu0_mu1": dr,
        "charge_product": charge_product,
        "pt_ratio_mu1_mu0": pt_ratio,
        "m0m1j0_gev": ak.to_numpy(mass).astype(np.float32),
    }
    for branch_field in ("isGlobal", "isTracker", "isPFcand", "nStations", "nTrackerLayers"):
        fields[f"{branch_field}_mu0"] = np.full(n, 1.0, dtype=np.float32)
        fields[f"{branch_field}_mu1"] = np.full(n, 0.0, dtype=np.float32)
    np.savez_compressed(job_dir / "dimuon_diagnostics.npz", **fields)


def main():
    portal_urls = {
        30522: [f"root://eospublic.cern.ch//eos/opendata/cms/fake/G_{i}.root" for i in range(3)],
        30555: [f"root://eospublic.cern.ch//eos/opendata/cms/fake/H_{i}.root" for i in range(2)],
    }
    portal_counts = {30522: {"number_events": 3000, "number_files": 3}, 30555: {"number_events": 2000, "number_files": 2}}

    common_mod.fetch_file_list = lambda record_id: portal_urls[record_id]
    common_mod.fetch_record_number_events = lambda record_id: portal_counts[record_id]

    import studies.m0m1j0_cms.cluster.merge_full as merge_full
    merge_full.fetch_file_list = lambda record_id: portal_urls[record_id]
    merge_full.fetch_record_number_events = lambda record_id: portal_counts[record_id]

    original_uproot_open = uproot.open

    # job index -> (record, file_index, n_read, url). job_index_map.txt
    # will declare 5 expected jobs (3 for 30522, 2 for 30555); job_4 is
    # deliberately left un-written (missing), and job_2's re-open will be
    # mocked to report a DIFFERENT entry count than it recorded (a
    # deliberate mismatch).
    job_specs = {
        1: (30522, 0, 1000, portal_urls[30522][0]),
        2: (30522, 1, 1000, portal_urls[30522][1]),
        3: (30522, 2, 1000, portal_urls[30522][2]),
        # 4 (30555, 0, ...) deliberately missing
        5: (30555, 1, 1000, portal_urls[30555][1]),
    }

    def fake_uproot_open(url):
        if isinstance(url, str) and url.startswith("root://eospublic.cern.ch//eos/opendata/cms/fake/"):
            class _FakeEventsTree:
                def __init__(self, n):
                    self.num_entries = n
            class _FakeFile:
                def __init__(self, n):
                    self._n = n
                def __getitem__(self, key):
                    assert key == "Events"
                    return _FakeEventsTree(self._n)
            # job_2's file: report a MISMATCHED count on purpose.
            if url == portal_urls[30522][1]:
                return _FakeFile(999)  # recorded was 1000
            return _FakeFile(1000)
        return original_uproot_open(url)

    uproot.open = fake_uproot_open

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        jobs_base = tmp_path / "jobs"
        for idx, (record_id, file_index, n_read, url) in job_specs.items():
            dupe = 50 if idx == 1 else 0  # only job_1 gets the synthetic near-duplicate pattern
            write_job(jobs_base / f"job_{idx}", record_id, file_index, url,
                      [2] * n_read, n_read=n_read, extra_dupe_events=dupe)

        mapping_lines = []
        idx = 1
        for record_id in (30522, 30555):
            for file_index in range(len(portal_urls[record_id])):
                mapping_lines.append(f"{idx} {record_id} {file_index}")
                idx += 1
        mapping_file = tmp_path / "job_index_map.txt"
        mapping_file.write_text("\n".join(mapping_lines) + "\n", encoding="utf-8")

        out_dir = tmp_path / "full_out"
        sys.argv = [
            "merge_full.py",
            "--jobs-base", str(jobs_base),
            "--mapping-file", str(mapping_file),
            "--out-dir", str(out_dir),
        ]
        try:
            merge_full.main()
        except SystemExit as e:
            check("merge_full.main() exits non-zero (INCOMPLETE, as expected)", e.code != 0, f"got exit code {e.code}")
        finally:
            uproot.open = original_uproot_open

        summary = json.loads((out_dir / "merge_summary.json").read_text())
        check("merge correctly reports INCOMPLETE (job_4 missing + job_2 count mismatch)", summary["complete"] is False)
        check("job_4 is in missing_indices", 4 in summary["missing_indices"], f"got {summary['missing_indices']}")
        problems = summary["identity_and_counts"]["problems"]
        check(
            "problems mentions job_4 missing metadata",
            any("job_4" in p and "missing" in p for p in problems),
            f"got {problems}",
        )
        check(
            "problems mentions job_2's entry-count mismatch",
            any("job_2" in p and "999" in p for p in problems),
            f"got {problems}",
        )
        check(
            "job_2 recorded as OK status but count_matches_live_reopen=False",
            summary["identity_and_counts"]["per_job"]["2"]["count_matches_live_reopen"] is False,
            f"got {summary['identity_and_counts']['per_job'].get('2')}",
        )
        check(
            "sum-of-n_read mismatch reported (present jobs sum 4000, portal total 5000)",
            any("sum of n_read" in p for p in problems),
            f"got {problems}",
        )

        check("m0m1j0_full_merged.root was written", (out_dir / "m0m1j0_full_merged.root").exists())
        check("m0m1j0_diagnostic_variants.root was written", (out_dir / "m0m1j0_diagnostic_variants.root").exists())

        f = uproot.open(str(out_dir / "m0m1j0_full_merged.root"))
        all_th1f = all(f[k].classname == "TH1F" for k in f.keys())
        check("every histogram in the merged output is genuinely TH1F", all_th1f, f"classnames: {[f[k].classname for k in f.keys()]}")

        fdiag = uproot.open(str(out_dir / "m0m1j0_diagnostic_variants.root"))
        check("diagnostic variants file has exactly one histogram", len(fdiag.keys()) == 1, f"got {fdiag.keys()}")
        diag_key = fdiag.keys()[0]
        check("diagnostic variant histogram is TH1F", fdiag[diag_key].classname == "TH1F")

        diag_report = summary["low_mass_dimuon_diagnostic"]
        check(
            "diagnostic report found the synthetic <2GeV low-mass population (50 events from job_1)",
            diag_report["n_events_m_mumu_lt_2gev"] == 50,
            f"got {diag_report.get('n_events_m_mumu_lt_2gev')}",
        )
        check(
            "diagnostic report: those events are ~100% same-sign (matches synthetic construction)",
            diag_report["m_mumu_lt_2gev_same_sign_fraction"] == 1.0,
            f"got {diag_report.get('m_mumu_lt_2gev_same_sign_fraction')}",
        )
        check(
            "diagnostic report: those events have tiny median deltaR (matches synthetic construction)",
            diag_report["m_mumu_lt_2gev_deltaR_median"] < 0.01,
            f"got {diag_report.get('m_mumu_lt_2gev_deltaR_median')}",
        )
        check(
            "diagnostic report: global/tracker split fraction is 100% (mu0 global-only, mu1 tracker-only in synthetic data)",
            diag_report.get("m_mumu_lt_2gev_global_tracker_split_fraction") == 1.0,
            f"got {diag_report.get('m_mumu_lt_2gev_global_tracker_split_fraction')}",
        )

        for png in ("dimuon_mass.png", "dimuon_mass_zoom_0_10.png", "leading_jet_pt.png",
                    "inclusive_m0m1j0_logy.png", "inclusive_m0m1j0_linear_100_1000.png", "top5_categories.png",
                    "diagnostic_charge_product.png", "diagnostic_deltaR.png", "diagnostic_pt_ratio.png",
                    "diagnostic_m0m1j0_overlay.png"):
            check(f"plot {png} was written", (out_dir / "plots" / png).exists())

    print()
    if FAILURES:
        print(f"{len(FAILURES)} FAILURE(S): {FAILURES}")
        sys.exit(1)
    else:
        print("All merge_full.py integration checks passed.")


if __name__ == "__main__":
    main()
