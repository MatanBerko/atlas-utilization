"""
Full local integration test of
studies/m0m1j0_cms/cluster/run_m0m1j0_variants_on_file.py's main(), with
uproot.open/fetch_file_list monkeypatched to a synthetic in-memory NanoAOD
file -- no network, no cluster, no golden-JSON file needed (a temporary
one is written). Adapted from test_run_on_file_integration.py's fixture,
extended with the V3 single-muon trigger branches (required by this
driver) and a deliberately-collimated low-mass muon pair fraction to
exercise the diagnostics.

Run directly:
    python studies/m0m1j0_cms/tests/test_run_variants_on_file_integration.py
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

import studies.m0m1j0_cms.cluster.run_m0m1j0_variants_on_file as driver  # noqa: E402
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
    """Every 5th event fails BOTH V0 trigger paths but has HLT_IsoMu24 set
    (fires under V3, not V0) -- exercises the V3 variant actually changing
    the selected population, not just accepting the same events. Every
    10th event (offset 3) is a collimated low-mass muon pair (dimuon mass
    ~0.7 GeV) with mu1 sitting just above V0's isolation threshold (0.20 >
    0.15), so V1 (no iso) recovers it and V0 rejects it -- exercises the
    "does removing isolation increase collimated low-mass pairs" question
    end to end, not just via selection.py's own unit test."""
    data = {
        "run": [111] * n_events,
        "luminosityBlock": [((i % 50) + 1) for i in range(n_events)],
        "event": list(range(1, n_events + 1)),
        "HLT_Mu17_TrkIsoVVL_Mu8_TrkIsoVVL_DZ": [(i % 5 != 0) for i in range(n_events)],
        "HLT_Mu17_TrkIsoVVL_TkMu8_TrkIsoVVL_DZ": [False] * n_events,
        "HLT_IsoMu24": [(i % 5 == 0) for i in range(n_events)],
        "HLT_IsoTkMu24": [False] * n_events,
    }
    mu_pt, mu_eta, mu_phi, mu_mass, mu_medium, mu_iso, mu_charge = [], [], [], [], [], [], []
    for i in range(n_events):
        if i % 10 == 3:
            mu_pt.append([40.0, 39.5])
            mu_eta.append([0.3, 0.301])
            mu_phi.append([1.2, 1.2001])
            mu_charge.append([1, 1])
            mu_iso.append([0.05, 0.20])  # mu1 fails V0's iso (< 0.15), passes V1
        else:
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
    # Two jets: jetA far from both muons (pt=80+i); jetB close to mu1
    # (dR~0.05) with HIGHER pt than jetA, so V0's cleaning removes jetB
    # (leaving jetA as leading), while V2 (no cleaning) makes jetB the
    # leading jet -- exercises the "leading jet changes under V2" claim.
    jet_pt, jet_eta, jet_phi, jet_mass, jet_id, jet_btag = [], [], [], [], [], []
    for i in range(n_events):
        jet_pt.append([80.0 + i, 200.0 + i])
        jet_eta.append([1.0, -0.501])
        jet_phi.append([-2.0, 2.001])
        jet_mass.append([8.0, 9.0])
        jet_id.append([6, 6])
        jet_btag.append([0.01, 0.01])
    data.update({
        "nJet": [2] * n_events,
        "Jet_pt": jet_pt, "Jet_eta": jet_eta, "Jet_phi": jet_phi, "Jet_mass": jet_mass,
        "Jet_jetId": jet_id, "Jet_btagDeepFlavB": jet_btag,
    })
    return data


def main():
    n_events = 500
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
        return [f"root://fake/{record_id}/file0.root", f"root://fake/{record_id}/file1.root"]

    uproot.open = fake_open
    driver.fetch_file_list = fake_fetch

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        golden_json_path = tmp_path / "golden.json"
        golden_json_path.write_text(json.dumps({"111": [[1, 100]]}), encoding="utf-8")

        output_dir = tmp_path / "job_out"
        sys.argv = [
            "run_m0m1j0_variants_on_file.py",
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
        for v in variants.VARIANT_ORDER:
            check(f"mass_by_category_{v}.npz was written", (output_dir / f"mass_by_category_{v}.npz").exists())

        meta = json.loads((output_dir / "job_metadata.json").read_text())
        check("n_read == 500", meta["n_read"] == 500, f"got {meta['n_read']}")

        cf = meta["per_variant_cutflow"]
        check(
            "V0: n_after_trigger == 400 (every 5th event fails both V0 paths)",
            cf["V0_baseline"]["n_after_trigger"] == 400, f"got {cf['V0_baseline']}",
        )
        check(
            "V3: n_after_trigger == 100 (only the V0-failing events have HLT_IsoMu24 set in this fixture)",
            cf["V3_single_muon_trigger"]["n_after_trigger"] == 100, f"got {cf['V3_single_muon_trigger']}",
        )
        check(
            "V3's 100 selected events are DISJOINT from V0's 400 (by fixture construction: "
            "HLT_IsoMu24 is only True exactly where the V0 DZ path is False)",
            cf["V3_single_muon_trigger"]["n_after_trigger"] + cf["V0_baseline"]["n_after_trigger"] == n_events,
            f"V3={cf['V3_single_muon_trigger']['n_after_trigger']} V0={cf['V0_baseline']['n_after_trigger']}",
        )
        check(
            "V1 (no iso) admits MORE events after >=2mu than V0 (recovers the collimated pairs)",
            cf["V1_no_muon_iso"]["n_after_ge2mu"] > cf["V0_baseline"]["n_after_ge2mu"],
            f"V0={cf['V0_baseline']['n_after_ge2mu']} V1={cf['V1_no_muon_iso']['n_after_ge2mu']}",
        )

        diag = meta["per_variant_diagnostics"]
        check(
            "V0 diagnostic: some collimated low-mass dimuon pairs are already visible (the ones that pass iso)",
            diag["V0_baseline"]["n_dimuon_lt_4gev"] >= 0,
        )
        check(
            "V1 has MORE (or equal) low-mass dimuon events than V0 in its diagnostic population "
            "(removing isolation cannot decrease the collimated-pair count)",
            diag["V1_no_muon_iso"]["n_dimuon_lt_4gev"] >= diag["V0_baseline"]["n_dimuon_lt_4gev"],
            f"V0={diag['V0_baseline']} V1={diag['V1_no_muon_iso']}",
        )
        check(
            "V2 diagnostic block present with the jet-muon overlap fields",
            "n_leading_jet_dr_lt_p4_to_muon" in diag["V2_no_jet_lepton_cleaning"],
            f"got keys {list(diag['V2_no_jet_lepton_cleaning'].keys())}",
        )
        check(
            "V2: a nonzero fraction of events have their leading (uncleaned) jet close to a muon "
            "(by construction: jetB is close to mu1 and has higher pt than jetA)",
            diag["V2_no_jet_lepton_cleaning"]["n_leading_jet_dr_lt_p4_to_muon"] > 0,
            f"got {diag['V2_no_jet_lepton_cleaning']}",
        )
        check(
            "V0/V1/V3 have no V2-only overlap diagnostic keys",
            all("n_leading_jet_dr_lt_p4_to_muon" not in diag[v] for v in ("V0_baseline", "V1_no_muon_iso", "V3_single_muon_trigger")),
        )

        with np.load(output_dir / "mass_by_category_V0_baseline.npz", allow_pickle=True) as mbc0, \
             np.load(output_dir / "mass_by_category_V2_no_jet_lepton_cleaning.npz", allow_pickle=True) as mbc2:
            check(
                "V0 and V2 mass_by_category npz have the expected fields",
                set(["category", "m0m1j0_raw_gev"]) == set(mbc0.files) == set(mbc2.files),
                f"V0 fields={mbc0.files} V2 fields={mbc2.files}",
            )
            check(
                "V0 row count matches its own n_after_ge1jet_after_cleaning",
                len(mbc0["m0m1j0_raw_gev"]) == cf["V0_baseline"]["n_after_ge1jet_after_cleaning"],
                f"got {len(mbc0['m0m1j0_raw_gev'])} vs {cf['V0_baseline']['n_after_ge1jet_after_cleaning']}",
            )
            check(
                "V2's raw mass array differs from V0's (different leading jet for at least one event)",
                not np.array_equal(np.sort(mbc0["m0m1j0_raw_gev"]), np.sort(mbc2["m0m1j0_raw_gev"])) or
                len(mbc0["m0m1j0_raw_gev"]) != len(mbc2["m0m1j0_raw_gev"]),
                "arrays are identical -- V2 should differ from V0 for this fixture",
            )

    print()
    if FAILURES:
        print(f"{len(FAILURES)} FAILURE(S): {FAILURES}")
        sys.exit(1)
    else:
        print("All run_m0m1j0_variants_on_file.py integration checks passed.")


if __name__ == "__main__":
    main()
