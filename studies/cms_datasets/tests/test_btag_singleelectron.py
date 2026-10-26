"""
Self-checks for Maryna's 20 Oct 2026 decisions (CMS only):

  B1  b-tag: DeepJet Jet_btagDeepFlavB > 0.2489 (official CMS medium WP for
      UL2016 postVFP) is the constant, and select_and_split_jets -- the only
      b-tag cut -- uses it, read at call time.
  S1  SingleElectron acceptance (--population matched5) on synthetic
      events: offline pT just below / at / above 32 GeV, online pT at the
      27 GeV edge, unmatched electron, wrong filter bit, id guard, electron
      removed by the e-mu dR < 0.12 overlap removal, trigger not fired, and
      the "same electron" requirement. Also agreement, on random events,
      with the study's own Step D formula (measure_singleelectron.py).
  P1  priority / de-duplication: synthetic events accepted by every subset
      of the five datasets. Per-dataset jobs and pooling are simulated with
      the driver's own functions for two priority orders (SingleElectron
      LAST, the delivery order, and SingleElectron FIRST). The union of
      pooled events and the combined histogram are identical; only the
      per-dataset assignment changes. Each accepted event is pooled once.
  P2  the data builder's priority-order guard.
  M4  --population matched4 is unchanged: still four datasets, and the
      five-dataset evaluation's first four acceptances are matched4's own.

Run directly:
    python studies/cms_datasets/tests/test_btag_singleelectron.py
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

import awkward as ak  # noqa: E402
import numpy as np  # noqa: E402

from studies.cms_datasets.cluster import run_dataset_on_file as drv  # noqa: E402
from studies.cms_datasets.deliver import build_four_dataset_delivery as bld  # noqa: E402
from studies.cms_datasets.tests.test_electron_datasets import (  # noqa: E402
    make_objects,
    make_trigobj,
)
from studies.m0m1j0_cms import selection  # noqa: E402

FAILURES: list[str] = []
N_CHECKS = 0

ELE27 = "HLT_Ele27_WPTight_Gsf"
BIT2 = drv.TRIGOBJ_BIT_E_1E_WPTIGHT_SE


def check(name: str, condition: bool, detail: str = ""):
    global N_CHECKS
    N_CHECKS += 1
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {name}" + (f" -- {detail}" if detail and not condition else ""))
    if not condition:
        FAILURES.append(name)


def make_events5(hlt: dict, n: int) -> ak.Array:
    """Event record carrying every HLT branch the five acceptances read."""
    all_paths = sorted({p for paths in drv.MATCHED5_TRIGGER_PATHS.values() for p in paths})
    return ak.Array({p: np.array(hlt.get(p, [False] * n), dtype=bool) for p in all_paths})


# ---------------------------------------------------------------------------
# B1. b-tag working point
# ---------------------------------------------------------------------------

def _jet_events(scores):
    """One event per score: one jet (pt 60, eta 0, tight id) with that
    DeepJet score, no leptons."""
    n = len(scores)
    def jag(vals, dtype):
        return ak.unflatten(np.array(vals, dtype=dtype), np.ones(n, dtype=np.int64))
    def empty(dtype):
        return ak.unflatten(np.array([], dtype=dtype), np.zeros(n, dtype=np.int64))
    return ak.Array({
        "Jet_pt": jag([60.0] * n, np.float64), "Jet_eta": jag([0.0] * n, np.float64),
        "Jet_phi": jag([0.0] * n, np.float64), "Jet_mass": jag([5.0] * n, np.float64),
        "Jet_jetId": jag([6] * n, np.int32),
        "Jet_btagDeepFlavB": jag(scores, np.float64),
        "Muon_pt": empty(np.float64), "Muon_eta": empty(np.float64),
        "Muon_phi": empty(np.float64), "Muon_mass": empty(np.float64),
        "Muon_looseId": empty(bool), "Muon_pfRelIso04_all": empty(np.float64),
        "Electron_pt": empty(np.float64), "Electron_eta": empty(np.float64),
        "Electron_phi": empty(np.float64), "Electron_mass": empty(np.float64),
        "Electron_cutBased": empty(np.int32),
    })


def _n_b(events):
    muons = selection.select_muons(events)
    electrons = selection.select_electrons(events)
    jets = selection.select_and_split_jets(events, muons, electrons, apply_lepton_cleaning=True)
    return (ak.to_numpy(ak.num(jets["BJets"], axis=1)).tolist(),
            ak.to_numpy(ak.num(jets["Jets"], axis=1)).tolist())


def test_b1_btag():
    print("\n--- B1. b-tag working point ---")
    check("BTAG_DEEPFLAVB_MEDIUM_WP is 0.2489 (official CMS DeepJet medium, UL2016 postVFP)",
          selection.BTAG_DEEPFLAVB_MEDIUM_WP == 0.2489,
          f"got {selection.BTAG_DEEPFLAVB_MEDIUM_WP}")
    scores = [0.2400, 0.2488, 0.2489, 0.2490, 0.2500, 0.2597, 0.2598, 0.2599, 0.9]
    n_b, n_light = _n_b(_jet_events(scores))
    want_b = [1 if s > 0.2489 else 0 for s in scores]
    check("select_and_split_jets tags exactly the jets with score > 0.2489 "
          "(0.2489 itself is light: the cut is strict '>')", n_b == want_b,
          f"got {n_b}, want {want_b}")
    check("every jet is either b or light (none lost)",
          [b + l for b, l in zip(n_b, n_light)] == [1] * len(scores))
    check("jets with 0.2489 < score <= 0.2598 are now b-tagged (they were light at 0.2598)",
          [n for s, n in zip(scores, n_b) if 0.2489 < s <= 0.2598] == [1, 1, 1, 1])
    # The selection reads the module constant at call time.
    saved = selection.BTAG_DEEPFLAVB_MEDIUM_WP
    try:
        selection.BTAG_DEEPFLAVB_MEDIUM_WP = 0.5
        n_b_05, _ = _n_b(_jet_events(scores))
    finally:
        selection.BTAG_DEEPFLAVB_MEDIUM_WP = saved
    check("select_and_split_jets reads the constant (a different value moves the cut)",
          n_b_05 == [1 if s > 0.5 else 0 for s in scores], f"got {n_b_05}")


# ---------------------------------------------------------------------------
# S1. SingleElectron acceptance
# ---------------------------------------------------------------------------

def _se_case(electrons, trigs, fired=True, muons=None):
    """Run the production chain for ONE event: overlap removal, then
    singleelectron_acceptance. Returns (accepted, n_electrons_after_removal)."""
    els = make_objects([electrons])
    mus = make_objects([muons or []])
    els, _n_removed, _mask = drv.remove_electrons_overlapping_muons(
        els, mus, dr_max=drv.EMU_OVERLAP_DR_MAX, enabled=True)
    events = make_events5({ELE27: [fired]}, 1)
    res = drv.singleelectron_acceptance(events, els, make_trigobj([trigs]))
    return bool(res["accepted"][0]), int(ak.num(els, axis=1)[0])


def _e(pt, eta=0.5, phi=1.0):
    return {"pt": pt, "eta": eta, "phi": phi}


def _t(pt, eta=0.5, phi=1.0, bits=BIT2, oid=11):
    return {"pt": pt, "eta": eta, "phi": phi, "id": oid, "filterBits": bits}


def _study_formula(events, electrons, trigobj, T=32.0):
    """measure_singleelectron.py's Step D acceptance, transcribed: Ele27
    fired, then per electron qualifies = matched & best_pt >= 27, then
    max offline pT over qualifying electrons > T."""
    fired = ak.to_numpy(events[ELE27]).astype(bool)
    bk = drv.trigobj_best_match(electrons, trigobj, drv.TRIGOBJ_ELECTRON_ID, 2)
    qualifies = bk["is_matched"] & (bk["best_pt"] >= 27.0)
    qual_pt = ak.where(qualifies, electrons.pt, -np.inf)
    max_qual_pt = ak.to_numpy(ak.fill_none(ak.max(qual_pt, axis=1), -np.inf))
    return fired & (max_qual_pt > T)


def test_s1_singleelectron():
    print("\n--- S1. SingleElectron acceptance (T = 32 GeV) ---")
    check("constants: Ele27 path, bit 2, online >= 27, offline > 32",
          drv.MATCHED5_TRIGGER_PATHS["SingleElectron"] == (ELE27,)
          and BIT2 == 2 and drv.SINGLEELECTRON_TRIGOBJ_PT_MIN_GEV == 27.0
          and drv.SINGLEELECTRON_OFFLINE_PT_MIN_GEV == 32.0)
    check("offline pT 31.9 (just below 32) -> rejected",
          _se_case([_e(31.9)], [_t(30.0)])[0] is False)
    check("offline pT exactly 32.0 -> rejected (the cut is strict '>', as in the study)",
          _se_case([_e(32.0)], [_t(30.0)])[0] is False)
    check("offline pT 32.1 (just above 32) -> accepted",
          _se_case([_e(32.1)], [_t(30.0)])[0] is True)
    check("unmatched electron (no trigger object at all) -> rejected",
          _se_case([_e(50.0)], [])[0] is False)
    check("unmatched electron (bit-2 object at dR ~ 0.5) -> rejected",
          _se_case([_e(50.0)], [_t(50.0, eta=1.0)])[0] is False)
    check("matched online TrigObj_pt 26.9 (< 27) -> rejected",
          _se_case([_e(50.0)], [_t(26.9)])[0] is False)
    check("matched online TrigObj_pt exactly 27.0 -> accepted (>=)",
          _se_case([_e(50.0)], [_t(27.0)])[0] is True)
    check("trigger object with the wrong bit (16 = 2e, not 2) -> rejected",
          _se_case([_e(50.0)], [_t(50.0, bits=drv.TRIGOBJ_BIT_E_2E)])[0] is False)
    check("id guard: an id-13 object with bit 2 on top of the electron -> rejected",
          _se_case([_e(50.0)], [_t(50.0, oid=13)])[0] is False)
    check("trigger not fired -> rejected, even with a perfect match",
          _se_case([_e(50.0)], [_t(50.0)], fired=False)[0] is False)
    acc, n_left = _se_case([_e(50.0, eta=0.5, phi=1.0)], [_t(50.0)],
                           muons=[{"pt": 40.0, "eta": 0.55, "phi": 1.0}])
    check("electron within dR 0.05 < 0.12 of a muon is removed first -> rejected",
          acc is False and n_left == 0, f"accepted={acc}, electrons left={n_left}")
    acc, n_left = _se_case([_e(50.0, eta=0.5, phi=1.0)], [_t(50.0)],
                           muons=[{"pt": 40.0, "eta": 0.70, "phi": 1.0}])
    check("same electron with the muon at dR 0.20 is kept -> accepted",
          acc is True and n_left == 1, f"accepted={acc}, electrons left={n_left}")
    acc, _ = _se_case([_e(40.0, eta=0.5), _e(30.0, eta=-1.5)],
                      [_t(25.0, eta=0.5), _t(30.0, eta=-1.5)])
    check("the SAME electron must pass both: A (offline 40, online 25) + "
          "B (offline 30, online 30) -> rejected", acc is False)
    acc, _ = _se_case([_e(40.0, eta=0.5), _e(30.0, eta=-1.5)],
                      [_t(25.0, eta=0.5), _t(33.0, eta=0.5), _t(30.0, eta=-1.5)])
    check("best match per electron is the highest online pT (25 and 33 near A) -> accepted",
          acc is True)

    # Random events: identical to the study's own Step D formula.
    rng = np.random.default_rng(20261020)
    n = 3000
    el_list, trig_list = [], []
    for _ in range(n):
        els = [{"pt": float(rng.uniform(25, 60)), "eta": float(rng.uniform(-2.4, 2.4)),
                "phi": float(rng.uniform(-3.1, 3.1))} for _ in range(rng.integers(0, 3))]
        trigs = []
        for e in els:
            if rng.random() < 0.7:
                trigs.append({"pt": float(rng.uniform(20, 60)),
                              "eta": e["eta"] + float(rng.normal(0, 0.05)),
                              "phi": e["phi"] + float(rng.normal(0, 0.05)),
                              "id": int(rng.choice([11, 11, 11, 13])),
                              "filterBits": int(rng.choice([2, 2, 16, 18, 32, 34]))})
        el_list.append(els)
        trig_list.append(trigs)
    events = make_events5({ELE27: (rng.random(n) < 0.8).tolist()}, n)
    els, trigobj = make_objects(el_list), make_trigobj(trig_list)
    got = drv.singleelectron_acceptance(events, els, trigobj)["accepted"]
    want = _study_formula(events, els, trigobj)
    check(f"identical to the study's Step D formula on {n} random events "
          f"({int(want.sum())} accepted)", np.array_equal(got, want) and 0 < want.sum() < n)
    guard = drv.count_trigger_guard_violations(
        drv.trigobj_best_match(els, trigobj, drv.TRIGOBJ_ELECTRON_ID, BIT2),
        trigobj, drv.TRIGOBJ_ELECTRON_ID)
    check("trigger-guard violations on the random events: 0", guard == 0, f"got {guard}")

    ok = True
    try:
        drv.assert_trigobj_bit_meanings_se({"TrigObj_filterBits": "1 = CaloIdL_TrackIdL_IsoVL, "
                                                                  "2 = 1e (WPTight), 4 = 1e (WPLoose)"})
    except RuntimeError:
        ok = False
    check("assert_trigobj_bit_meanings_se accepts a title with '2 = 1e (WPTight)'", ok)
    raised = False
    try:
        drv.assert_trigobj_bit_meanings_se({"TrigObj_filterBits": "2 = 1e (WPLoose)"})
    except RuntimeError:
        raised = True
    check("assert_trigobj_bit_meanings_se STOPS when bit 2's meaning differs", raised)


# ---------------------------------------------------------------------------
# P1. priority order / de-duplication with SingleElectron
# ---------------------------------------------------------------------------

def _five_dataset_synthetic(n_copies=3, seed=7):
    """Events accepted by EVERY subset of the five datasets (32 subsets, each
    n_copies times), built from the four-dataset recipes of
    test_electron_datasets._four_dataset_synthetic plus SingleElectron: one
    electron matched to an id-11 bit-2 object, online 40, offline 40, with
    HLT_Ele27_WPTight_Gsf fired. Each event also gets a random mass."""
    labels = drv.DELIVERY_VETO_ORDER_5
    rng = np.random.default_rng(seed)
    subsets = []
    for mask in range(32):
        subsets += [{labels[i] for i in range(5) if mask >> i & 1}] * n_copies
    mu_list, el_list, trig_list = [], [], []
    hlt = {p: [] for paths in drv.MATCHED5_TRIGGER_PATHS.values() for p in paths}
    for want in subsets:
        mus, els, trigs = [], [], []
        need_muons = 2 if "DoubleMuon" in want else (1 if {"SingleMuon", "MuonEG"} & want else 0)
        for i in range(need_muons):
            eta = -2.0 + 0.5 * i
            mus.append({"eta": eta, "phi": -2.0, "pt": 40.0})
            bits = 0
            if "DoubleMuon" in want:
                bits |= drv.TRIGOBJ_BIT_TRKISOVVL
            if "SingleMuon" in want and i == 0:
                bits |= drv.TRIGOBJ_BIT_ISO
            if bits:
                pt = 30.0 if (bits & drv.TRIGOBJ_BIT_ISO) else 20.0
                trigs.append({"eta": eta, "phi": -2.0, "pt": pt, "id": 13, "filterBits": bits})
        n_el = 2 if "DoubleEG" in want else (1 if {"MuonEG", "SingleElectron"} & want else 0)
        for i in range(n_el):
            eta = 1.0 + 0.5 * i
            els.append({"eta": eta, "phi": 2.0, "pt": 40.0})
            bits = 0
            if "DoubleEG" in want:
                bits |= drv.TRIGOBJ_BIT_E_2E
            if "MuonEG" in want and i == 0:
                bits |= drv.TRIGOBJ_BIT_E_1E1MU
            if "SingleElectron" in want and i == 0:
                bits |= BIT2
            if bits:
                trigs.append({"eta": eta, "phi": 2.0, "pt": 40.0, "id": 11, "filterBits": bits})
        mu_list.append(mus)
        el_list.append(els)
        trig_list.append(trigs)
        for label, paths in drv.MATCHED5_TRIGGER_PATHS.items():
            for p in paths:
                hlt[p].append(label in want)
    events = make_events5(hlt, len(subsets))
    masses = rng.uniform(50.0, 500.0, len(subsets))
    return (events, make_objects(mu_list), make_objects(el_list),
            make_trigobj(trig_list), subsets, masses)


def _pool(acc, events, masses, order):
    """Simulate the per-file jobs and the builder for one priority order.

    Per dataset: the job sees only events whose OWN trigger fired (as a
    primary dataset file does), keeps its own accepted events, marks the
    exclusive ones with exclusive_mask_from_acceptances(order), and the
    builder pools the first dataset's inclusive set with every other one's
    exclusive set. Returns ({dataset: event indices}, pooled indices)."""
    by_dataset = {}
    for i, label in enumerate(order):
        own_fired = drv.fired_mask(events, drv.MATCHED5_TRIGGER_PATHS[label])
        excl, _per_higher, _higher = drv.exclusive_mask_from_acceptances(acc, label, order)
        keep = own_fired & acc[label]["accepted"]
        take = keep if i == 0 else (keep & excl)
        by_dataset[label] = np.flatnonzero(take)
    pooled = np.concatenate([by_dataset[label] for label in order])
    return by_dataset, pooled


def test_p1_priority_dedup():
    print("\n--- P1. priority order / de-duplication (five datasets) ---")
    check("the delivery order is DoubleMuon > SingleMuon > DoubleEG > MuonEG > SingleElectron",
          drv.DELIVERY_VETO_ORDER_5 == ["DoubleMuon", "SingleMuon", "DoubleEG", "MuonEG",
                                        "SingleElectron"])
    events, muons, electrons, trigobj, subsets, masses = _five_dataset_synthetic()
    acc = drv.evaluate_five_acceptances(events, muons, electrons, trigobj, "both")
    for label in drv.DELIVERY_VETO_ORDER_5:
        got = [bool(x) for x in acc[label]["accepted"]]
        want = [label in s for s in subsets]
        check(f"{label} acceptance matches the recipe for all {len(subsets)} synthetic events",
              got == want)

    order_last = list(drv.DELIVERY_VETO_ORDER_5)
    order_first = ["SingleElectron"] + list(drv.DELIVERY_VETO_ORDER_4)
    by_last, pooled_last = _pool(acc, events, masses, order_last)
    by_first, pooled_first = _pool(acc, events, masses, order_first)
    accepted_any = np.zeros(len(subsets), dtype=bool)
    for label in order_last:
        accepted_any |= acc[label]["accepted"]

    for name, pooled in (("SingleElectron last", pooled_last), ("SingleElectron first", pooled_first)):
        check(f"{name}: every accepted event is pooled exactly once",
              np.array_equal(np.bincount(pooled, minlength=len(subsets)),
                             accepted_any.astype(int)))
    check("the union of pooled events is identical for the two orders",
          np.array_equal(np.sort(pooled_last), np.sort(pooled_first)))
    edges = np.arange(0.0, 510.0, 10.0)
    h_last, _ = np.histogram(masses[pooled_last], bins=edges)
    h_first, _ = np.histogram(masses[pooled_first], bins=edges)
    check(f"the combined histogram is identical for the two orders "
          f"({int(h_last.sum())} entries)", np.array_equal(h_last, h_first) and h_last.sum() > 0)
    n_se_last = len(by_last["SingleElectron"])
    n_se_first = len(by_first["SingleElectron"])
    only_se = np.flatnonzero(np.array([s == {"SingleElectron"} for s in subsets]))
    check("SingleElectron LAST receives only events no other dataset accepts",
          set(by_last["SingleElectron"].tolist()) == set(only_se.tolist()),
          f"got {n_se_last}, want {len(only_se)}")
    check("SingleElectron FIRST receives every event it accepts (inclusive)",
          n_se_first == int(acc["SingleElectron"]["accepted"].sum()))
    check("the per-dataset assignment DOES change between the orders",
          n_se_first > n_se_last
          and any(len(by_first[l]) < len(by_last[l]) for l in drv.DELIVERY_VETO_ORDER_4))
    attributed = drv.attribute_to_exclusive_dataset(acc, order_last)
    check("attribute_to_exclusive_dataset(order_5) agrees with the SingleElectron-last pooling",
          all(attributed[i] == label for label in order_last for i in by_last[label]))
    for label in drv.DELIVERY_VETO_ORDER_4:
        excl4, _, _ = drv.exclusive_mask_from_acceptances(acc, label)
        excl5, _, _ = drv.exclusive_mask_from_acceptances(acc, label, order_last)
        check(f"{label}'s exclusive set is unchanged by adding SingleElectron last",
              np.array_equal(excl4, excl5))


# ---------------------------------------------------------------------------
# P2. builder priority-order guard
# ---------------------------------------------------------------------------

def test_p2_builder_guard():
    print("\n--- P2. data builder priority-order guard ---")
    def ok(ds):
        try:
            bld.check_priority_order(ds)
            return True
        except SystemExit:
            return False
    check("five datasets in delivery order are accepted", ok(list(drv.DELIVERY_VETO_ORDER_5)))
    check("the four-dataset default is accepted", ok(list(drv.DELIVERY_VETO_ORDER_4)))
    check("a subset in order is accepted (DoubleMuon,DoubleEG,SingleElectron)",
          ok(["DoubleMuon", "DoubleEG", "SingleElectron"]))
    check("SingleElectron first is REFUSED", not ok(["SingleElectron"] + drv.DELIVERY_VETO_ORDER_4))
    check("a swapped pair is REFUSED", not ok(["SingleMuon", "DoubleMuon"]))
    check("an unknown dataset is REFUSED", not ok(["DoubleMuon", "JetHT"]))
    check("a duplicate is REFUSED", not ok(["DoubleMuon", "DoubleMuon"]))


# ---------------------------------------------------------------------------
# M4. matched4 unchanged
# ---------------------------------------------------------------------------

def test_m4_matched4_unchanged():
    print("\n--- M4. --population matched4 unchanged ---")
    check("DELIVERY_VETO_ORDER_4 is still the four datasets",
          drv.DELIVERY_VETO_ORDER_4 == ["DoubleMuon", "SingleMuon", "DoubleEG", "MuonEG"])
    check("matched4 still uses the four-dataset order and trigger sets",
          drv.MATCHED_DELIVERY_ORDER_BY_POPULATION["matched4"] is drv.DELIVERY_VETO_ORDER_4
          and drv.MATCHED_DELIVERY_PATHS_BY_POPULATION["matched4"] is drv.MATCHED4_TRIGGER_PATHS
          and ELE27 not in {p for v in drv.MATCHED4_TRIGGER_PATHS.values() for p in v})
    check("matched5's first four trigger sets are matched4's",
          all(drv.MATCHED5_TRIGGER_PATHS[l] == drv.MATCHED4_TRIGGER_PATHS[l]
              for l in drv.DELIVERY_VETO_ORDER_4))
    check("the matched4 title assertion does not require the SingleElectron bit",
          "2 = 1e (WPTight)" not in drv.EXPECTED_TRIGOBJ_FILTERBITS_TITLE_SUBSTRINGS)
    events, muons, electrons, trigobj, _subsets, _m = _five_dataset_synthetic(n_copies=1)
    a4 = drv.evaluate_four_acceptances(events, muons, electrons, trigobj, "both")
    a5 = drv.evaluate_five_acceptances(events, muons, electrons, trigobj, "both")
    check("evaluate_five_acceptances' first four acceptances equal matched4's",
          all(np.array_equal(a4[l]["accepted"], a5[l]["accepted"]) for l in drv.DELIVERY_VETO_ORDER_4))
    check("attribute_to_exclusive_dataset's default order is still the four datasets",
          np.array_equal(drv.attribute_to_exclusive_dataset(a4),
                         drv.attribute_to_exclusive_dataset(a5, drv.DELIVERY_VETO_ORDER_4)))


def main():
    print("20 Oct 2026 decisions: b-tag 0.2489 + SingleElectron (T = 32 GeV)")
    print("=" * 72)
    test_b1_btag()
    test_s1_singleelectron()
    test_p1_priority_dedup()
    test_p2_builder_guard()
    test_m4_matched4_unchanged()
    print("=" * 72)
    print(f"{N_CHECKS} checks, {len(FAILURES)} failure(s)")
    for f in FAILURES:
        print(f"  FAILED: {f}")
    sys.exit(1 if FAILURES else 0)


if __name__ == "__main__":
    main()
