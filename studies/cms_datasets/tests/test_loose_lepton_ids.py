"""
Self-checks for Maryna's 24 Oct 2026 decision (CMS only): LOOSE lepton IDs.

  L1  muons: the ID branch is Muon_looseId (not Muon_mediumId), read by
      select_muons, NEEDED_BRANCHES and the per-file driver's branch list;
      the isolation pfRelIso04_all < 0.15 is kept (strict '<').
  L2  electrons: ELECTRON_CUTBASED_MIN is 2 (Loose); select_electrons keeps
      cutBased 2, 3, 4 and drops 0, 1.
  L3  the driver's diagnostics-only electron mask (run_dataset_on_file.py)
      uses the same constants, so it selects the same electrons as
      select_electrons.
  L4  jets are unchanged: tight jet ID (Jet_jetId bit 2) and the 0.2489 b-tag.

Run directly:
    python studies/cms_datasets/tests/test_loose_lepton_ids.py
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

import awkward as ak  # noqa: E402
import numpy as np  # noqa: E402

from studies.cms_datasets.cluster import run_dataset_on_file as drv  # noqa: E402
from studies.m0m1j0_cms import selection  # noqa: E402

FAILURES: list[str] = []
N_CHECKS = 0


def check(name: str, condition: bool, detail: str = ""):
    global N_CHECKS
    N_CHECKS += 1
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {name}" + (f" -- {detail}" if detail and not condition else ""))
    if not condition:
        FAILURES.append(name)


def _one_per_event(vals, dtype):
    n = len(vals)
    return ak.unflatten(np.array(vals, dtype=dtype), np.ones(n, dtype=np.int64))


def _empty(n, dtype):
    return ak.unflatten(np.array([], dtype=dtype), np.zeros(n, dtype=np.int64))


def _muon_events(loose, medium, iso):
    """One event per entry: one muon (pt 40, eta 0) with the given IDs/iso.
    Muon_mediumId is present too, so a selection that still read it would
    give a different answer."""
    n = len(loose)
    return ak.Array({
        "Muon_pt": _one_per_event([40.0] * n, np.float64),
        "Muon_eta": _one_per_event([0.0] * n, np.float64),
        "Muon_phi": _one_per_event([0.0] * n, np.float64),
        "Muon_mass": _one_per_event([0.105] * n, np.float64),
        "Muon_looseId": _one_per_event(loose, bool),
        "Muon_mediumId": _one_per_event(medium, bool),
        "Muon_pfRelIso04_all": _one_per_event(iso, np.float64),
    })


def _electron_events(cut_based):
    n = len(cut_based)
    return ak.Array({
        "Electron_pt": _one_per_event([40.0] * n, np.float64),
        "Electron_eta": _one_per_event([0.0] * n, np.float64),
        "Electron_phi": _one_per_event([0.0] * n, np.float64),
        "Electron_mass": _one_per_event([0.0005] * n, np.float64),
        "Electron_cutBased": _one_per_event(cut_based, np.int32),
    })


def test_l1_muons():
    print("\n--- L1. muons: Loose ID, isolation < 0.15 kept ---")
    check("MUON_ID_BRANCH is Muon_looseId", selection.MUON_ID_BRANCH == "Muon_looseId",
          f"got {selection.MUON_ID_BRANCH!r}")
    check("MUON_ISO_MAX is still 0.15", selection.MUON_ISO_MAX == 0.15,
          f"got {selection.MUON_ISO_MAX}")
    check("NEEDED_BRANCHES reads Muon_looseId and not Muon_mediumId",
          "Muon_looseId" in selection.NEEDED_BRANCHES
          and "Muon_mediumId" not in selection.NEEDED_BRANCHES)
    check("the driver's BASE_OBJECT_BRANCHES reads Muon_looseId and not Muon_mediumId",
          "Muon_looseId" in drv.BASE_OBJECT_BRANCHES
          and "Muon_mediumId" not in drv.BASE_OBJECT_BRANCHES)
    #           loose  medium  iso    -> selected?
    cases = [(True,  True,  0.05, True),    # medium is a subset of loose
             (True,  False, 0.05, True),    # loose only: now selected
             (False, True,  0.05, False),   # (unphysical) medium without loose: not selected
             (False, False, 0.05, False),
             (True,  False, 0.1499, True),
             (True,  False, 0.15, False),   # isolation cut is strict '<'
             (True,  True,  0.20, False)]
    events = _muon_events([c[0] for c in cases], [c[1] for c in cases], [c[2] for c in cases])
    got = (ak.to_numpy(ak.num(selection.select_muons(events), axis=1)) == 1).tolist()
    want = [c[3] for c in cases]
    check("select_muons selects on looseId and pfRelIso04_all < 0.15", got == want,
          f"got {got}, want {want}")
    no_iso = (ak.to_numpy(ak.num(selection.select_muons(events, apply_iso=False), axis=1)) == 1).tolist()
    check("apply_iso=False drops only the isolation cut",
          no_iso == [c[0] for c in cases], f"got {no_iso}")
    check("select_muons carries a looseId field, not mediumId",
          "looseId" in selection.select_muons(events).fields
          and "mediumId" not in selection.select_muons(events).fields)
    no_medium = ak.Array({k: events[k] for k in events.fields if k != "Muon_mediumId"})
    check("select_muons works on events without Muon_mediumId",
          (ak.to_numpy(ak.num(selection.select_muons(no_medium), axis=1)) == 1).tolist() == want)


def test_l2_electrons():
    print("\n--- L2. electrons: cutBased >= 2 (Loose) ---")
    check("ELECTRON_CUTBASED_MIN is 2 (Loose)", selection.ELECTRON_CUTBASED_MIN == 2,
          f"got {selection.ELECTRON_CUTBASED_MIN}")
    cut_based = [0, 1, 2, 3, 4]
    got = ak.to_numpy(ak.num(selection.select_electrons(_electron_events(cut_based)), axis=1)).tolist()
    check("select_electrons keeps cutBased 2, 3, 4 and drops 0 (fail) and 1 (veto)",
          got == [0, 0, 1, 1, 1], f"got {got}")
    check("Electron_cutBased is still read", "Electron_cutBased" in selection.NEEDED_BRANCHES
          and "Electron_cutBased" in drv.BASE_OBJECT_BRANCHES)


def test_l3_driver_diag_mask():
    print("\n--- L3. driver diagnostics mask uses the same constants ---")
    rng = np.random.default_rng(24)
    n_per = rng.integers(0, 4, size=500)
    tot = int(n_per.sum())
    ev = ak.Array({
        "Electron_pt": ak.unflatten(rng.uniform(10, 60, tot), n_per),
        "Electron_eta": ak.unflatten(rng.uniform(-3, 3, tot), n_per),
        "Electron_phi": ak.unflatten(rng.uniform(-3, 3, tot), n_per),
        "Electron_mass": ak.unflatten(np.zeros(tot), n_per),
        "Electron_cutBased": ak.unflatten(rng.integers(0, 5, tot).astype(np.int32), n_per),
    })
    # The expression at run_dataset_on_file.py (electron_diag_mask), verbatim.
    electron_diag_mask = (
        (ev.Electron_pt > selection.ELECTRON_PT_MIN_GEV)
        & (abs(ev.Electron_eta) < selection.ELECTRON_ETA_MAX)
        & (ev.Electron_cutBased >= selection.ELECTRON_CUTBASED_MIN)
    )
    src = (REPO_ROOT / "studies/cms_datasets/cluster/run_dataset_on_file.py").read_text()
    check("the driver's diagnostics mask reads selection.ELECTRON_CUTBASED_MIN",
          "(events_triggered.Electron_cutBased >= selection.ELECTRON_CUTBASED_MIN)" in src)
    code = "\n".join(line.split("#", 1)[0] for line in src.splitlines())
    check("no Muon_mediumId left in the driver's code (comments aside)",
          "Muon_mediumId" not in code and "mediumId" not in code)
    a = ak.to_list(ak.num(selection.select_electrons(ev), axis=1))
    b = ak.to_list(ak.sum(electron_diag_mask, axis=1))
    check("diagnostics mask selects the same number of electrons per event", a == b)


def test_l4_jets_unchanged():
    print("\n--- L4. jets unchanged ---")
    check("BTAG_DEEPFLAVB_MEDIUM_WP is still 0.2489", selection.BTAG_DEEPFLAVB_MEDIUM_WP == 0.2489)
    check("JET_PT_MIN_GEV 30 and JET_ETA_MAX 2.5 unchanged",
          selection.JET_PT_MIN_GEV == 30.0 and selection.JET_ETA_MAX == 2.5)
    n = 4
    ev = ak.Array({
        "Jet_pt": _one_per_event([60.0] * n, np.float64), "Jet_eta": _one_per_event([0.0] * n, np.float64),
        "Jet_phi": _one_per_event([0.0] * n, np.float64), "Jet_mass": _one_per_event([5.0] * n, np.float64),
        "Jet_jetId": _one_per_event([0, 1, 2, 6], np.int32),
        "Jet_btagDeepFlavB": _one_per_event([0.0] * n, np.float64),
        "Muon_pt": _empty(n, np.float64), "Muon_eta": _empty(n, np.float64),
        "Muon_phi": _empty(n, np.float64), "Muon_mass": _empty(n, np.float64),
        "Muon_looseId": _empty(n, bool), "Muon_pfRelIso04_all": _empty(n, np.float64),
        "Electron_pt": _empty(n, np.float64), "Electron_eta": _empty(n, np.float64),
        "Electron_phi": _empty(n, np.float64), "Electron_mass": _empty(n, np.float64),
        "Electron_cutBased": _empty(n, np.int32),
    })
    mu = selection.select_muons(ev)
    el = selection.select_electrons(ev)
    jets = selection.select_and_split_jets(ev, mu, el, apply_lepton_cleaning=True)
    got = ak.to_numpy(ak.num(jets["Jets"], axis=1)).tolist()
    check("tight jet ID (bit 2) still required: jetId 0,1 dropped; 2,6 kept",
          got == [0, 0, 1, 1], f"got {got}")


def main():
    test_l1_muons()
    test_l2_electrons()
    test_l3_driver_diag_mask()
    test_l4_jets_unchanged()
    print(f"\n{N_CHECKS - len(FAILURES)}/{N_CHECKS} checks passed")
    if FAILURES:
        print("FAILED:", *FAILURES, sep="\n  ")
        sys.exit(1)


if __name__ == "__main__":
    main()
