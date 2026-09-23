"""
Full local integration test of
studies/m0m1j0_cms/cluster/run_m0m1j0_variants_on_mc_file.py's main().
Adapted from test_run_variants_on_file_integration.py, minus golden-JSON,
plus genWeight.

Run directly:
    python studies/m0m1j0_cms/tests/test_run_variants_on_mc_file_integration.py
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

import studies.m0m1j0_cms.cluster.run_m0m1j0_variants_on_mc_file as driver  # noqa: E402
from studies.m0m1j0_cms import variants  # noqa: E402

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


def make_synthetic_events(n_events: int):
    rng = np.random.default_rng(1)
    data = {
        "run": [1] * n_events,
        "luminosityBlock": [1] * n_events,
        "event": list(range(1, n_events + 1)),
        "HLT_Mu17_TrkIsoVVL_Mu8_TrkIsoVVL_DZ": [(i % 5 != 0) for i in range(n_events)],
        "HLT_Mu17_TrkIsoVVL_TkMu8_TrkIsoVVL_DZ": [False] * n_events,
        "HLT_IsoMu24": [(i % 5 == 0) for i in range(n_events)],
        "HLT_IsoTkMu24": [False] * n_events,
        "genWeight": (rng.choice([1.0, -1.0], size=n_events, p=[0.9, 0.1])).tolist(),
    }
    mu_pt, mu_eta, mu_phi, mu_mass, mu_medium, mu_iso, mu_charge = [], [], [], [], [], [], []
    for i in range(n_events):
        mu_pt.append([60.0, 30.0 + (i % 20)])
        mu_eta.append([0.1, -0.5])
        mu_phi.append([0.0, 2.0])
        mu_charge.append([1, -1])
        mu_iso.append([0.05, 0.05])
        mu_mass.append([0.105, 0.105])
        mu_medium.append([True, True])
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
    data.update({
        "nJet": [1] * n_events,
        "Jet_pt": [[85.0] for _ in range(n_events)], "Jet_eta": [[1.0] for _ in range(n_events)],
        "Jet_phi": [[-2.0] for _ in range(n_events)], "Jet_mass": [[8.0] for _ in range(n_events)],
        "Jet_jetId": [[6] for _ in range(n_events)], "Jet_btagDeepFlavB": [[0.01] for _ in range(n_events)],
    })
    return data


def main():
    n_events = 300
    synthetic = make_synthetic_events(n_events)
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
        return [f"root://fake/{record_id}/file0.root"]

    uproot.open = fake_open
    driver.fetch_file_list = fake_fetch

    with tempfile.TemporaryDirectory() as tmp:
        output_dir = Path(tmp) / "job_out"
        sys.argv = [
            "run_m0m1j0_variants_on_mc_file.py",
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
        for v in variants.VARIANT_ORDER:
            check(f"mass_by_category_{v}.npz was written", (output_dir / f"mass_by_category_{v}.npz").exists())

        meta = json.loads((output_dir / "job_metadata.json").read_text())
        check("n_read == 300", meta["n_read"] == 300, f"got {meta['n_read']}")
        check("is_simulation is True", meta["is_simulation"] is True)
        check("golden_json_applied is False", meta["golden_json_applied"] is False)
        check(
            "sum_genWeight is roughly (0.9-0.1)*300 = 240 (90% +1, 10% -1)",
            abs(meta["sum_genWeight_all_read_events"] - 240.0) < 40.0,
            f"got {meta['sum_genWeight_all_read_events']}",
        )

        with np.load(output_dir / "mass_by_category_V0_baseline.npz", allow_pickle=True) as mbc:
            check(
                "V0 npz has category/mass/genWeight fields",
                set(["category", "m0m1j0_raw_gev", "genWeight"]) == set(mbc.files), f"got {mbc.files}",
            )
            check(
                "genWeight row count matches mass row count",
                len(mbc["genWeight"]) == len(mbc["m0m1j0_raw_gev"]),
            )

    print()
    if FAILURES:
        print(f"{len(FAILURES)} FAILURE(S): {FAILURES}")
        sys.exit(1)
    else:
        print("All run_m0m1j0_variants_on_mc_file.py integration checks passed.")


if __name__ == "__main__":
    main()
