"""
Full local integration test of studies/m0m1j0_cms/cluster/run_m0m1j0_on_mc_file.py's
main(), with uproot.open and fetch_file_list monkeypatched to a synthetic
in-memory ttbar-MC-shaped file (genWeight included, no golden-JSON
concept at all) -- no network, no cluster.

Run directly: python studies/m0m1j0_cms/tests/test_run_on_mc_file_integration.py
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

import studies.m0m1j0_cms.cluster.run_m0m1j0_on_mc_file as driver  # noqa: E402

FAILURES = []


def check(name: str, condition: bool, detail: str = ""):
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {name}" + (f" -- {detail}" if detail and not condition else ""))
    if not condition:
        FAILURES.append(name)


class FakeTree:
    def __init__(self, data: dict):
        self._data = data

    def keys(self):
        return list(self._data.keys())

    def arrays(self, names, library="ak"):
        return ak.Array({n: self._data[n] for n in names})


def make_synthetic_mc_events(n_events: int):
    """Opposite-sign, broad-mass dimuon pairs (no dominant Z peak, unlike
    the data fixture), each event with >=1 b-tagged jet roughly half the
    time (ttbar dilepton should be b-jet-rich), a mix of positive and
    (10%) negative genWeight (powheg-style), and every 4th event failing
    the trigger."""
    data = {
        "run": [1] * n_events, "luminosityBlock": [1] * n_events, "event": list(range(1, n_events + 1)),
        "HLT_Mu17_TrkIsoVVL_Mu8_TrkIsoVVL_DZ": [(i % 4 != 0) for i in range(n_events)],
        "HLT_Mu17_TrkIsoVVL_TkMu8_TrkIsoVVL_DZ": [False] * n_events,
        "genWeight": [(-1.0 if i % 10 == 0 else 1.0) for i in range(n_events)],
    }
    mu_pt, mu_eta, mu_phi, mu_mass, mu_medium, mu_iso, mu_charge = [], [], [], [], [], [], []
    jet_pt, jet_eta, jet_phi, jet_mass, jet_id, jet_btag = [], [], [], [], [], []
    for i in range(n_events):
        # Muon kinematics vary substantially event-to-event (pt AND the
        # opening angle) so the resulting dimuon mass spans a genuinely
        # broad range rather than -- as an earlier, too-static version of
        # this fixture produced by accident -- coincidentally clustering
        # near the Z mass for every event.
        mu_pt.append([60.0 + 3.0 * (i % 40), 35.0 + (i % 15)])
        mu_eta.append([0.2 + 0.05 * (i % 20), -0.4 - 0.03 * (i % 20)])
        mu_phi.append([0.5, 0.5 + 0.3 + 0.15 * (i % 20)])
        mu_mass.append([0.105, 0.105])
        mu_medium.append([True, True])
        mu_iso.append([0.05, 0.05])
        mu_charge.append([1, -1])
        # TWO jets per event: jet[0] is always LIGHT (passes the >=1
        # light-jet selection unconditionally), jet[1] is a SECOND jet
        # that is b-tagged for ~half the events -- giving a realistic
        # n_bjets>=1 fraction on events that still pass selection. A
        # single-jet-per-event version of this fixture (an earlier draft)
        # made half the events fail selection entirely whenever that one
        # jet was b-tagged (no light jet left at all), which is why it
        # measured 0% b-tagged among SURVIVORS -- not a driver bug, a
        # fixture construction mistake.
        jet_pt.append([90.0 + i, 45.0])
        jet_eta.append([0.8, -1.2])
        jet_phi.append([-1.0, 1.8])
        jet_mass.append([12.0, 8.0])
        jet_id.append([6, 6])
        jet_btag.append([0.01, 0.9 if i % 2 == 0 else 0.01])
    data.update({
        "nMuon": [2] * n_events, "Muon_pt": mu_pt, "Muon_eta": mu_eta, "Muon_phi": mu_phi,
        "Muon_mass": mu_mass, "Muon_mediumId": mu_medium, "Muon_pfRelIso04_all": mu_iso, "Muon_charge": mu_charge,
        "nElectron": [0] * n_events, "Electron_pt": [[] for _ in range(n_events)],
        "Electron_eta": [[] for _ in range(n_events)], "Electron_phi": [[] for _ in range(n_events)],
        "Electron_mass": [[] for _ in range(n_events)], "Electron_cutBased": [[] for _ in range(n_events)],
        "nJet": [1] * n_events, "Jet_pt": jet_pt, "Jet_eta": jet_eta, "Jet_phi": jet_phi,
        "Jet_mass": jet_mass, "Jet_jetId": jet_id, "Jet_btagDeepFlavB": jet_btag,
    })
    return data


def main():
    n_events = 400
    synthetic = make_synthetic_mc_events(n_events)
    fake_tree = FakeTree(synthetic)

    class FakeFile:
        def __getitem__(self, key):
            assert key == "Events"
            return fake_tree

    original_open = uproot.open
    original_fetch = driver.fetch_file_list

    def fake_open(url):
        if isinstance(url, str) and url.startswith("root://fake/"):
            return FakeFile()
        return original_open(url)

    def fake_fetch(record_id):
        return [f"root://fake/{record_id}/mc_file0.root"]

    uproot.open = fake_open
    driver.fetch_file_list = fake_fetch

    with tempfile.TemporaryDirectory() as tmp:
        output_dir = Path(tmp) / "mc_job_out"
        sys.argv = [
            "run_m0m1j0_on_mc_file.py",
            "--record-id", "67801",
            "--file-index", "0",
            "--output-dir", str(output_dir),
        ]
        try:
            driver.main()
        finally:
            uproot.open = original_open
            driver.fetch_file_list = original_fetch

        check("job_metadata.json was written", (output_dir / "job_metadata.json").exists())
        check("mass_by_category.npz was written", (output_dir / "mass_by_category.npz").exists())
        check("sanity_arrays.json was written", (output_dir / "sanity_arrays.json").exists())

        meta = json.loads((output_dir / "job_metadata.json").read_text())
        check("cutflow n_read == 400", meta["cutflow"]["n_read"] == 400, f"got {meta['cutflow']}")
        check(
            "trigger cut removed the every-4th-event failures (n_after_trigger==300)",
            meta["cutflow"]["n_after_trigger"] == 300,
            f"got {meta['cutflow']}",
        )
        check("golden_json_applied is False", meta["golden_json_applied"] is False)
        check("is_simulation is True", meta["is_simulation"] is True)
        check(
            "sum_genWeight_all_read_events == 320 (360 pos - 40 neg, since i%10==0 -> 40 of 400 negative)",
            meta["sum_genWeight_all_read_events"] == 320.0,
            f"got {meta['sum_genWeight_all_read_events']}",
        )
        check(
            "negative_weight_fraction_all_read_events == 0.1",
            abs(meta["negative_weight_fraction_all_read_events"] - 0.1) < 1e-9,
            f"got {meta['negative_weight_fraction_all_read_events']}",
        )
        check("known_limitations lists pileup/SF/trigger-eff/luminosity", len(meta["known_limitations"]) == 4, f"got {meta['known_limitations']}")

        with np.load(output_dir / "mass_by_category.npz", allow_pickle=True) as mbc:
            check("mass_by_category.npz has category/m0m1j0_raw_gev/genWeight fields", set(mbc.files) == {"category", "m0m1j0_raw_gev", "genWeight"}, f"got {mbc.files}")
            check(
                "mass_by_category row count matches n_after_ge1jet_after_cleaning",
                len(mbc["m0m1j0_raw_gev"]) == meta["cutflow"]["n_after_ge1jet_after_cleaning"],
                f"got {len(mbc['m0m1j0_raw_gev'])} vs {meta['cutflow']['n_after_ge1jet_after_cleaning']}",
            )
            check(
                "mass_by_category genWeight values are only +1.0 or -1.0 (matches synthetic construction)",
                set(np.unique(mbc["genWeight"]).tolist()).issubset({1.0, -1.0}),
                f"got {np.unique(mbc['genWeight'])}",
            )

        sanity = json.loads((output_dir / "sanity_arrays.json").read_text())
        check("sanity_arrays has dimuon_mass_gev/leading_jet_pt_gev/n_bjets/genWeight", set(sanity.keys()) == {"dimuon_mass_gev", "leading_jet_pt_gev", "n_bjets", "genWeight"}, f"got {list(sanity.keys())}")
        check(
            "sanity_arrays row counts are all equal and match n_after_ge1jet_after_cleaning",
            len({len(v) for v in sanity.values()}) == 1 and len(sanity["n_bjets"]) == meta["cutflow"]["n_after_ge1jet_after_cleaning"],
            f"got lengths {[len(v) for v in sanity.values()]} vs {meta['cutflow']['n_after_ge1jet_after_cleaning']}",
        )
        check(
            "roughly half of selected events have >=1 b-jet (matches synthetic construction: alternating btag)",
            0.3 < np.mean(np.array(sanity["n_bjets"]) >= 1) < 0.7,
            f"got fraction {np.mean(np.array(sanity['n_bjets']) >= 1) if sanity['n_bjets'] else None}",
        )
        check(
            "no dominant Z peak: dimuon masses span a broad range, not clustered near 91 GeV",
            len(sanity["dimuon_mass_gev"]) > 0 and (max(sanity["dimuon_mass_gev"]) - min(sanity["dimuon_mass_gev"])) > 20.0,
            f"got range {(min(sanity['dimuon_mass_gev']), max(sanity['dimuon_mass_gev'])) if sanity['dimuon_mass_gev'] else None}",
        )

    print()
    if FAILURES:
        print(f"{len(FAILURES)} FAILURE(S): {FAILURES}")
        sys.exit(1)
    else:
        print("All run_m0m1j0_on_mc_file.py integration checks passed.")


if __name__ == "__main__":
    main()
