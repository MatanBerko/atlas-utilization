"""
Full local integration test of studies/m0m1j0_cms/cluster/run_m0m1j0_on_file.py's
main(), with uproot.open and fetch_file_list monkeypatched to a synthetic
in-memory NanoAOD-shaped file -- no network, no cluster, no golden-JSON
file needed (a temporary one is written).

This exercises the entire per-job pipeline exactly as the cluster will
run it: golden-JSON filter, selection, TH1F writing + verification
(Step 2 requirement A), and the low-mass dimuon diagnostic npz
(Step 2 requirement B) -- checking the actual files written to disk, not
just the in-memory functions individually (those are covered by the
other test_*.py files in this directory).

Run directly: python studies/m0m1j0_cms/tests/test_run_on_file_integration.py
"""
from __future__ import annotations

import json
import sys
import tempfile
import types
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

import awkward as ak  # noqa: E402
import numpy as np  # noqa: E402
import uproot  # noqa: E402

import studies.m0m1j0_cms.cluster.run_m0m1j0_on_file as driver  # noqa: E402
from studies.m0m1j0_cms import selection  # noqa: E402

FAILURES = []


def check(name: str, condition: bool, detail: str = ""):
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {name}" + (f" -- {detail}" if detail and not condition else ""))
    if not condition:
        FAILURES.append(name)


class FakeTree:
    """Minimal stand-in for uproot's TTree interface: .keys() and
    .arrays(names, library='ak')."""
    def __init__(self, data: dict):
        self._data = data

    def keys(self):
        return list(self._data.keys())

    def arrays(self, names, library="ak"):
        return ak.Array({n: self._data[n] for n in names})


def make_synthetic_events(n_events: int, include_optional: bool):
    """n_events events, ~half passing the full selection with a range of
    dimuon masses (including some near-duplicate-like low-mass pairs),
    all in run 111, certified lumis 1-100 (golden JSON below covers this).

    Every 5th event deliberately FAILS both trigger paths -- essential,
    not incidental: an earlier version of this fixture had every event
    pass the trigger, which hid a real bug (muon_extra_fields built from
    events BEFORE the trigger cut, then zipped against muons built from
    events AFTER it -- an ak.zip length mismatch) that only surfaced
    running the real cluster array, where every one of the first 57
    full-run jobs crashed on it, 2026-09-22. See
    selection.select_event_selection_cutflow's own docstring for the
    full story. This fixture must keep exercising that shrinkage."""
    rng = np.random.default_rng(0)
    data = {
        "run": [111] * n_events,
        "luminosityBlock": [((i % 50) + 1) for i in range(n_events)],
        "event": list(range(1, n_events + 1)),
        "HLT_Mu17_TrkIsoVVL_Mu8_TrkIsoVVL_DZ": [(i % 5 != 0) for i in range(n_events)],
        "HLT_Mu17_TrkIsoVVL_TkMu8_TrkIsoVVL_DZ": [False] * n_events,
    }
    mu_pt, mu_eta, mu_phi, mu_mass, mu_medium, mu_iso, mu_charge = [], [], [], [], [], [], []
    for i in range(n_events):
        # offset 3, not 0: i%5==0 events fail the trigger above, so using
        # the SAME multiple-of-5-aligned offset here would make every
        # near-duplicate event also a trigger failure, leaving none of
        # them in the final sample -- confirmed to happen with i%10==0.
        if i % 10 == 3:
            # near-duplicate-like low-mass pair
            mu_pt.append([40.0, 39.5])
            mu_eta.append([0.3, 0.301])
            mu_phi.append([1.2, 1.2001])
            mu_charge.append([1, 1])
        else:
            mu_pt.append([60.0, 30.0 + (i % 20)])
            mu_eta.append([0.1, -0.5])
            mu_phi.append([0.0, 2.0])
            mu_charge.append([1, -1])
        mu_mass.append([0.105, 0.105])
        mu_medium.append([True, True])
        mu_iso.append([0.05, 0.05])
    data.update({
        "nMuon": [2] * n_events,
        "Muon_pt": mu_pt, "Muon_eta": mu_eta, "Muon_phi": mu_phi, "Muon_mass": mu_mass,
        "Muon_mediumId": mu_medium, "Muon_pfRelIso04_all": mu_iso, "Muon_charge": mu_charge,
    })
    data.update({
        "nElectron": [0] * n_events,
        "Electron_pt": [[] for _ in range(n_events)], "Electron_eta": [[] for _ in range(n_events)],
        "Electron_phi": [[] for _ in range(n_events)], "Electron_mass": [[] for _ in range(n_events)],
        "Electron_cutBased": [[] for _ in range(n_events)],
    })
    jet_pt, jet_eta, jet_phi, jet_mass, jet_id, jet_btag = [], [], [], [], [], []
    for i in range(n_events):
        jet_pt.append([80.0 + i])
        jet_eta.append([1.0])
        jet_phi.append([-2.0])
        jet_mass.append([8.0])
        jet_id.append([6])
        jet_btag.append([0.01])
    data.update({
        "nJet": [1] * n_events,
        "Jet_pt": jet_pt, "Jet_eta": jet_eta, "Jet_phi": jet_phi, "Jet_mass": jet_mass,
        "Jet_jetId": jet_id, "Jet_btagDeepFlavB": jet_btag,
    })
    if include_optional:
        data["Muon_isGlobal"] = [[True, False]] * n_events
        data["Muon_isTracker"] = [[True, True]] * n_events
        # deliberately NOT including isPFcand/nStations/nTrackerLayers,
        # to exercise the "some optional branches present, some not" path
    return data


def main():
    n_events = 500
    synthetic = make_synthetic_events(n_events, include_optional=True)
    fake_tree = FakeTree(synthetic)

    class FakeFile:
        def __getitem__(self, key):
            assert key == "Events"
            return fake_tree

    original_open = uproot.open
    original_fetch = driver.fetch_file_list

    def fake_open(url):
        # Only intercept the fake portal URL (the synthetic input file);
        # everything else (e.g. verify_written_th1f re-opening the real,
        # just-written output ROOT file on local disk) goes to the real
        # uproot.open -- patching uproot.open globally means this same
        # function stands in for BOTH call sites, so it must discriminate.
        if isinstance(url, str) and url.startswith("root://fake/"):
            return FakeFile()
        return original_open(url)

    def fake_fetch(record_id):
        return [f"root://fake/{record_id}/file0.root", f"root://fake/{record_id}/file1.root"]

    uproot.open = fake_open
    driver.fetch_file_list = fake_fetch

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        golden_json_path = tmp_path / "golden.json"
        golden_json_path.write_text(json.dumps({"111": [[1, 100]]}), encoding="utf-8")

        output_dir = tmp_path / "job_out"
        sys.argv = [
            "run_m0m1j0_on_file.py",
            "--record-id", "12345",
            "--file-index", "0",
            "--output-dir", str(output_dir),
            "--validated-runs-json", str(golden_json_path),
        ]
        try:
            driver.main()
        finally:
            uproot.open = original_open
            driver.fetch_file_list = original_fetch

        check("job_metadata.json was written", (output_dir / "job_metadata.json").exists())
        check("all_histograms.root was written", (output_dir / "all_histograms.root").exists())
        check("outliers_gt_1tev.json was written", (output_dir / "outliers_gt_1tev.json").exists())
        check("sanity_arrays.json was written", (output_dir / "sanity_arrays.json").exists())
        check("dimuon_diagnostics.npz was written", (output_dir / "dimuon_diagnostics.npz").exists())
        check("mass_by_category.npz was written", (output_dir / "mass_by_category.npz").exists())

        meta = json.loads((output_dir / "job_metadata.json").read_text())
        check("cutflow n_read == 500", meta["cutflow"]["n_read"] == 500, f"got {meta['cutflow']}")
        check(
            "trigger cut actually removed events (n_after_trigger==400, not 500) -- otherwise this test proves nothing about muon_extra_branches correctness",
            meta["cutflow"]["n_after_trigger"] == 400,
            f"got {meta['cutflow']}",
        )
        check("file_url recorded matches the fake portal's file-index-0 URL", meta["file_url"] == "root://fake/12345/file0.root")
        check(
            "optional_muon_diagnostic_branches_present includes isGlobal/isTracker only",
            set(meta["optional_muon_diagnostic_branches_present"]) == {"Muon_isGlobal", "Muon_isTracker"},
            f"got {meta['optional_muon_diagnostic_branches_present']}",
        )
        check("histograms_verified_th1f is True (verify_written_th1f did not raise)", meta["histograms_verified_th1f"] is True)

        # Directly re-verify the written ROOT file ourselves too (belt and
        # braces -- don't just trust the job's own self-report).
        f = uproot.open(str(output_dir / "all_histograms.root"))
        keys = f.keys()
        check("at least the inclusive histogram was written", len(keys) >= 1, f"got {keys}")
        all_th1f = all(f[k].classname == "TH1F" for k in keys)
        check("every written histogram is genuinely TH1F", all_th1f, f"classnames: {[f[k].classname for k in keys]}")

        with np.load(output_dir / "dimuon_diagnostics.npz") as npz:
            check("npz has the expected core fields", set(["run", "luminosityBlock", "event", "m_mumu_gev", "deltaR_mu0_mu1", "charge_product", "pt_ratio_mu1_mu0", "m0m1j0_gev"]).issubset(set(npz.files)), f"got {npz.files}")
            check("npz has isGlobal_mu0/mu1 (present in this synthetic file)", "isGlobal_mu0" in npz.files and "isGlobal_mu1" in npz.files)
            check("npz has isPFcand_mu0 filled with NaN (absent in this synthetic file)", np.all(np.isnan(npz["isPFcand_mu0"])), f"got {npz['isPFcand_mu0'][:5]}")
            check(
                "npz row count matches n_after_z_peak_and_mass_cutoff",
                len(npz["run"]) == meta["cutflow"]["n_after_z_peak_and_mass_cutoff"],
                f"got {len(npz['run'])} vs {meta['cutflow']['n_after_z_peak_and_mass_cutoff']}",
            )
            # near-duplicate-like events (every 10th, i%10==0, low mass ~few
            # GeV) should show up with small deltaR and charge_product == 1
            # somewhere in the diagnostic npz (not asserting exact counts --
            # just that the pattern the synthetic data was built to contain
            # is visible).
            has_small_dr_same_sign = np.any((npz["deltaR_mu0_mu1"] < 0.01) & (npz["charge_product"] == 1))
            check("synthetic near-duplicate pattern is visible in the diagnostic npz", bool(has_small_dr_same_sign))
        npz_size_mb = (output_dir / "dimuon_diagnostics.npz").stat().st_size / (1024 * 1024)
        check("npz stays well under the 20 MB per-job limit", npz_size_mb < 1.0, f"got {npz_size_mb:.3f} MB")

        with np.load(output_dir / "mass_by_category.npz", allow_pickle=True) as mbc:
            check("mass_by_category.npz has category + m0m1j0_raw_gev fields", set(["category", "m0m1j0_raw_gev"]) == set(mbc.files), f"got {mbc.files}")
            check(
                "mass_by_category row count matches n_after_ge1jet_after_cleaning (the pre-z_peak/max_mass population)",
                len(mbc["m0m1j0_raw_gev"]) == meta["cutflow"]["n_after_ge1jet_after_cleaning"],
                f"got {len(mbc['m0m1j0_raw_gev'])} vs {meta['cutflow']['n_after_ge1jet_after_cleaning']}",
            )
            check(
                "mass_by_category row count is >= mass_by_category.npz-informed n_after_z_peak_and_mass_cutoff (raw includes events the z_peak/max_mass cut would later drop)",
                len(mbc["m0m1j0_raw_gev"]) >= meta["cutflow"]["n_after_z_peak_and_mass_cutoff"],
                f"got {len(mbc['m0m1j0_raw_gev'])} vs {meta['cutflow']['n_after_z_peak_and_mass_cutoff']}",
            )
            # (This synthetic fixture's masses never happen to fall below
            # the 115 GeV z_peak_cutoff at all -- n_after_ge1jet_after_
            # cleaning == n_after_z_peak_and_mass_cutoff == 400 here --
            # so row counts alone can't discriminate "raw" from "already
            # cut" in this specific fixture. build_mass_by_category_npz's
            # own source (uses result["raw_mass"], never result["mass"])
            # is the authority for that; not re-asserted here to avoid a
            # second fixture rebuild solely to force a sub-115-GeV event.)

    print()
    if FAILURES:
        print(f"{len(FAILURES)} FAILURE(S): {FAILURES}")
        sys.exit(1)
    else:
        print("All run_m0m1j0_on_file.py integration checks passed.")


if __name__ == "__main__":
    main()
