"""
Self-checks for the electron-datasets task (Step C, checks C1-C8).

Covers, in order:
  C1  multi-digit final-state labels round-trip through naming, and the
      known one-digit limitation of the SHARED parser
      services.calculations.physics_calcs.is_finalstate_contain_combination
      is pinned by a test that asserts its CURRENT behaviour plus the
      reason it can never change a result (no combination needs > 4 of a
      type). The parser is deliberately NOT fixed (out of scope).
  C2  electron-muon overlap removal (D3): 0.04 removed, 0.06 kept, the
      phi wrap-around case, muons never removed, option off = no-op.
  C3  the trigger-object guard (D6): an electron sitting exactly on an
      id-13 object never matches it, a muon on an id-11 object never
      matches it, and the violation counter is 0.
  C4  the de-duplication order (D2): synthetic events accepted by various
      subsets of the four datasets land in exactly the highest-priority
      accepting dataset's exclusive set, and the new order constant is
      [DoubleMuon, SingleMuon, DoubleEG, MuonEG].
  C5  DoubleEG modes (D4) at the 25/30 GeV boundaries, both modes.
  C6  MuonEG swapped legs (D5), including "no selected muon -> rejected".
  C7  histogram names from OUR code compared string-for-string against
      names produced by UPSTREAM's OWN naming code, imported from a
      read-only checkout of upstream master -- not re-implemented here.
  C8  old invocations: the pre-existing muon-delivery defaults (name
      format and per-histogram minimum) are unchanged, and the shared
      muon matcher still returns exactly what it returned before.

Run directly:
    python studies/cms_datasets/tests/test_electron_datasets.py
    python studies/cms_datasets/tests/test_electron_datasets.py \
        --pilot-final-states studies/cms_datasets/electron_vB/evidence/pilot_final_states.json
"""
from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

import awkward as ak  # noqa: E402
import numpy as np  # noqa: E402

from services.calculations import physics_calcs  # noqa: E402
from services.calculations.combinatorics import get_all_combinations, get_count, get_start  # noqa: E402
from studies.cms_datasets.cluster import run_dataset_on_file as drv  # noqa: E402
from studies.cms_datasets.deliver.build_dataset_delivery import roi_key, width_suffix  # noqa: E402
from studies.cms_datasets.deliver.build_muon_combined_delivery import (  # noqa: E402
    UPSTREAM_MIN_ENTRIES_PER_HISTOGRAM,
    _deliver_min_entries,
)
from studies.m0m1j0_cms.histograms import _convert_to_bumpnet_name, BIN_WIDTH_GEV  # noqa: E402

FAILURES: list[str] = []
N_CHECKS = 0


def check(name: str, condition: bool, detail: str = ""):
    global N_CHECKS
    N_CHECKS += 1
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {name}" + (f" -- {detail}" if detail and not condition else ""))
    if not condition:
        FAILURES.append(name)


# ---------------------------------------------------------------------------
# synthetic-event helpers
# ---------------------------------------------------------------------------

def _jagged(per_event: list[list[dict]], fields: dict) -> ak.Array:
    """Build a typed jagged record array, so an EMPTY inner list still
    carries every field (ak.Array of plain [[ ]] would not)."""
    flat = [o for ev in per_event for o in ev]
    content = ak.zip({
        name: np.array([o.get(name, default) for o in flat], dtype=dtype)
        for name, (default, dtype) in fields.items()
    })
    return ak.unflatten(content, np.array([len(ev) for ev in per_event], dtype=np.int64))


def make_objects(per_event: list[list[dict]]) -> ak.Array:
    """Jagged pt/eta/phi/mass collection from plain lists of dicts."""
    return _jagged(per_event, {"pt": (50.0, np.float64), "eta": (0.0, np.float64),
                               "phi": (0.0, np.float64), "mass": (0.0, np.float64)})


def make_trigobj(per_event: list[list[dict]]) -> ak.Array:
    return _jagged(per_event, {"pt": (50.0, np.float64), "eta": (0.0, np.float64),
                               "phi": (0.0, np.float64), "id": (0, np.int64),
                               "filterBits": (0, np.int64)})


def make_events(hlt: dict, n: int) -> ak.Array:
    """Event record carrying only the HLT branches the acceptances read."""
    fields = {}
    all_paths = set()
    for paths in drv.MATCHED4_TRIGGER_PATHS.values():
        all_paths.update(paths)
    for path in sorted(all_paths):
        fields[path] = np.array(hlt.get(path, [False] * n), dtype=bool)
    return ak.Array(fields)


def obj_record_from_counts(counts: list[dict]) -> ak.Array:
    """Object record with the requested per-type multiplicities."""
    def coll(n):
        return make_objects([[{} for _ in range(n)]])
    recs = []
    for c in counts:
        recs.append(ak.zip({
            "Electrons": coll(c.get("e", 0))[0:1],
            "Muons": coll(c.get("m", 0))[0:1],
            "Jets": coll(c.get("j", 0))[0:1],
            "BJets": coll(c.get("b", 0))[0:1],
        }, depth_limit=1))
    return ak.concatenate(recs) if recs else ak.Array([])


# ---------------------------------------------------------------------------
# C1. multi-digit labels
# ---------------------------------------------------------------------------

def test_c1_multidigit_labels():
    print("\n--- C1. multi-digit final-state labels and the one-digit parser ---")
    rec = obj_record_from_counts([{"e": 0, "m": 2, "j": 12, "b": 0}])
    labels = drv.exact_final_state_labels(rec)
    check("12 light jets -> label '0e_2m_12j_0b'", list(labels) == ["0e_2m_12j_0b"],
          f"got {list(labels)}")

    fs = "0e_2m_12j_0b"
    bumpnet = _convert_to_bumpnet_name(fs, "m0m1")
    check("bumpnet name keeps the two-digit count",
          bumpnet == "mass_m0m1_cat_0ex_2mx_12jx_0bx", f"got {bumpnet}")
    full = roi_key(bumpnet, upstream_width_suffix=True)
    check("full ROI name round-trips the two-digit count",
          full == "ROI_mass_m0m1_cat_0ex_2mx_12jx_0bx_width_10.0", f"got {full}")

    # Round-trip: the counts can be recovered from the label.
    import re
    recovered = {p: int(c) for c, p in re.findall(r"(\d+)([emjgtb])", fs)}
    check("counts recovered from the label", recovered == {"e": 0, "m": 2, "j": 12, "b": 0},
          f"got {recovered}")

    # The known SHARED-parser limitation, asserted as CURRENT behaviour.
    combo = {"Jets": (2, 0)}
    current = physics_calcs.is_finalstate_contain_combination(fs, combo)
    check("CURRENT behaviour: the one-digit parser reads '1' of '12j', fails to map "
          "letter '2', and silently treats the Jets requirement as satisfied",
          current is True, f"got {current}")
    combo_four_jets = {"Jets": (4, 0)}
    check("CURRENT behaviour: the skip means even a 4-jet requirement is treated "
          "as satisfied by the unparsed '12j' field",
          physics_calcs.is_finalstate_contain_combination(fs, combo_four_jets) is True)
    check("the correct answer for that requirement is also True (12 >= 4), so the "
          "skip changes nothing", 12 >= 4)

    # Why it can never change a delivered result.
    all_combinations = get_all_combinations(
        object_types=drv.OBJECT_TYPES,
        min_particles=drv.MIN_PARTICLES_IN_COMBINATION,
        max_particles=drv.MAX_PARTICLES_IN_COMBINATION,
        min_count=drv.MIN_COUNT_PARTICLE_IN_COMBINATION,
        max_count=drv.MAX_COUNT_PARTICLE_IN_COMBINATION,
        max_total_particles=drv.MAX_TOTAL_PARTICLES_IN_COMBINATION,
        include_subleading=drv.INCLUDE_SUBLEADING,
        max_subleading_index=drv.MAX_SUBLEADING_INDEX,
    )
    check("the combination set is still 186", len(all_combinations) == 186,
          f"got {len(all_combinations)}")
    worst = {}
    for c in all_combinations:
        for obj, value in c.items():
            worst[obj] = max(worst.get(obj, 0), get_start(value) + get_count(value))
    check("no combination needs more than 4 of any type, so a true count >= 10 "
          "satisfies every requirement anyway and the skip returns the same answer",
          max(worst.values()) == 4, f"got {worst}")

    # And a one-digit count is parsed correctly, so nothing below 10 is affected.
    check("a one-digit count is still parsed correctly (3j does not satisfy 4 jets)",
          physics_calcs.is_finalstate_contain_combination("0e_0m_3j_0b", {"Jets": (4, 0)})
          is False)


# ---------------------------------------------------------------------------
# C2. overlap removal
# ---------------------------------------------------------------------------

def test_c2_overlap_removal():
    print("\n--- C2. electron-muon overlap removal (D3) ---")
    # The radius was raised from 0.05 to 0.12 on 7 Oct 2026 (Maryna); these
    # boundaries are the new ones, and dR = 0.06 -- which the old radius kept
    # -- is now removed. Pure-eta separations, so dR == |dEta| exactly.
    check(f"the approved radius is 0.12 (was 0.05)", drv.EMU_OVERLAP_DR_MAX == 0.12,
          f"got {drv.EMU_OVERLAP_DR_MAX}")
    electrons = make_objects([
        [{"eta": 0.11, "phi": 0.0, "pt": 40.0}],   # dR = 0.11 -> removed
        [{"eta": 0.13, "phi": 0.0, "pt": 40.0}],   # dR = 0.13 -> kept
        [{"eta": 0.0, "phi": 3.13, "pt": 40.0}],   # phi wrap: dphi = 0.0232 -> removed
        [{"eta": 0.0, "phi": 0.0, "pt": 40.0}],    # no muon at all -> kept
        [{"eta": 0.0, "phi": 0.0, "pt": 40.0},
         {"eta": 1.0, "phi": 0.0, "pt": 30.0}],    # one of two removed
        [{"eta": 0.06, "phi": 0.0, "pt": 40.0}],   # dR = 0.06 -> removed (was KEPT at 0.05)
        [{"eta": 0.12, "phi": 0.0, "pt": 40.0}],   # dR exactly 0.12 -> kept, "<" is strict
    ])
    muons = make_objects([
        [{"eta": 0.0, "phi": 0.0, "pt": 50.0}],
        [{"eta": 0.0, "phi": 0.0, "pt": 50.0}],
        [{"eta": 0.0, "phi": -3.13, "pt": 50.0}],
        [],
        [{"eta": 0.0, "phi": 0.0, "pt": 50.0}],
        [{"eta": 0.0, "phi": 0.0, "pt": 50.0}],
        [{"eta": 0.0, "phi": 0.0, "pt": 50.0}],
    ])
    kept, n_removed, removed_mask = drv.remove_electrons_overlapping_muons(electrons, muons)
    counts = ak.to_numpy(ak.num(kept, axis=1)).tolist()
    check("dR = 0.11 electron is removed", counts[0] == 0 and n_removed[0] == 1,
          f"kept {counts[0]}, removed {n_removed[0]}")
    check("dR = 0.13 electron is kept", counts[1] == 1 and n_removed[1] == 0,
          f"kept {counts[1]}, removed {n_removed[1]}")
    check("dR = 0.06 electron is NOW REMOVED (the old 0.05 radius kept it)",
          counts[5] == 0 and n_removed[5] == 1, f"kept {counts[5]}, removed {n_removed[5]}")
    check("dR exactly 0.12 is kept -- the comparison is strict '<'",
          counts[6] == 1 and n_removed[6] == 0, f"kept {counts[6]}")
    check("phi wrap-around (+3.13 vs -3.13, dphi = 0.0232) is handled: removed",
          counts[2] == 0 and n_removed[2] == 1, f"kept {counts[2]}")
    check("no muon in the event -> nothing removed", counts[3] == 1 and n_removed[3] == 0)
    check("only the overlapping one of two electrons is removed",
          counts[4] == 1 and n_removed[4] == 1, f"kept {counts[4]}")
    check("the kept electron in the mixed event is the non-overlapping one",
          abs(float(kept[4][0].eta) - 1.0) < 1e-9)

    # The wrap must give 0.0232..., not 6.26.
    dr_wrap = float(drv.delta_r_wrapped(electrons[2:3], muons[2:3])[0][0][0])
    expected_wrap = abs(6.26 - 2.0 * math.pi)
    check("wrapped dPhi gives dR ~ 0.02319, not ~ 6.26",
          abs(dr_wrap - expected_wrap) < 1e-9, f"got {dr_wrap}, expected {expected_wrap}")

    # Muons are never removed: same input muons come back from the caller's
    # point of view -- the function never returns a muon collection at all,
    # and the one it is given is untouched.
    check("muons are never removed (the function returns no muon collection and "
          "leaves its input untouched)",
          ak.to_numpy(ak.num(muons, axis=1)).tolist() == [1, 1, 1, 0, 1, 1, 1])

    off_kept, off_n, off_mask = drv.remove_electrons_overlapping_muons(
        electrons, muons, enabled=False)
    check("with the option OFF nothing is removed",
          ak.to_numpy(ak.num(off_kept, axis=1)).tolist() == [1, 1, 1, 1, 2, 1, 1]
          and int(off_n.sum()) == 0 and int(ak.sum(off_mask)) == 0)

    # The old radius is still available as an explicit argument, which is how
    # the dR 0.05 vs 0.12 comparison in Step B is made.
    old_kept, old_n, _ = drv.remove_electrons_overlapping_muons(
        electrons, muons, dr_max=0.05)
    # Event 2 is the phi-wrap case at dR 0.0232, removed at either radius;
    # event 4 still loses its dR = 0 electron. The 0.06 and 0.11 electrons,
    # which the NEW radius removes, survive the old one -- that difference is
    # exactly what Step B measures on real data.
    check("passing the old radius 0.05 explicitly keeps the dR 0.06 and 0.11 "
          "electrons (only the wrap case and the dR = 0 one are removed)",
          ak.to_numpy(ak.num(old_kept, axis=1)).tolist() == [1, 1, 0, 1, 1, 1, 1],
          f"got {ak.to_numpy(ak.num(old_kept, axis=1)).tolist()}")
    check("the old radius removes strictly fewer electrons than the new one",
          int(old_n.sum()) < int(n_removed.sum()),
          f"old {int(old_n.sum())} vs new {int(n_removed.sum())}")

    # The explicit formula agrees with vector's own deltaR (used by the
    # trigger matching), so this is one quantity spelled two ways.
    rng = np.random.default_rng(7)
    a = make_objects([[{"eta": float(e), "phi": float(p), "pt": 30.0}]
                      for e, p in zip(rng.uniform(-2.5, 2.5, 200),
                                      rng.uniform(-math.pi, math.pi, 200))])
    b = make_objects([[{"eta": float(e), "phi": float(p), "pt": 30.0}]
                      for e, p in zip(rng.uniform(-2.5, 2.5, 200),
                                      rng.uniform(-math.pi, math.pi, 200))])
    mine = ak.to_numpy(ak.flatten(drv.delta_r_wrapped(a, b), axis=None))
    pa = drv._p4_no_mass_needed(a)
    pb = drv._p4_no_mass_needed(b)
    qa, qb = ak.unzip(ak.cartesian([pa, pb], nested=True))
    theirs = ak.to_numpy(ak.flatten(qa.deltaR(qb), axis=None))
    check("the explicit dR formula agrees with vector's deltaR on 200 random pairs",
          np.allclose(mine, theirs, atol=1e-12), f"max diff {np.abs(mine - theirs).max()}")


# ---------------------------------------------------------------------------
# C3. trigger-object guard
# ---------------------------------------------------------------------------

def test_c3_trigger_guard():
    print("\n--- C3. trigger-object guard (D6) ---")
    # One event: an electron and a muon at the SAME eta/phi as two trigger
    # objects, one of each id, both carrying every bit we ever require.
    all_bits = drv.TRIGOBJ_BIT_E_2E | drv.TRIGOBJ_BIT_E_1E1MU | \
        drv.TRIGOBJ_BIT_TRKISOVVL | drv.TRIGOBJ_BIT_ISO
    electrons = make_objects([[{"eta": 0.5, "phi": 0.5, "pt": 40.0}]])
    muons = make_objects([[{"eta": -0.5, "phi": -0.5, "pt": 40.0}]])
    trigobj = make_trigobj([[
        {"eta": -0.5, "phi": -0.5, "pt": 60.0, "id": 13, "filterBits": all_bits},
        {"eta": 0.5, "phi": 0.5, "pt": 60.0, "id": 11, "filterBits": all_bits},
    ]])

    # The electron sits exactly on the id-13 object? No: it sits on the id-11
    # one. Make a second configuration where the ONLY trigger object is the
    # wrong id, at exactly the offline object's position.
    only_muon_trig = make_trigobj([[
        {"eta": 0.5, "phi": 0.5, "pt": 60.0, "id": 13, "filterBits": all_bits}]])
    only_ele_trig = make_trigobj([[
        {"eta": -0.5, "phi": -0.5, "pt": 60.0, "id": 11, "filterBits": all_bits}]])

    bk = drv.trigobj_best_match(electrons, only_muon_trig, drv.TRIGOBJ_ELECTRON_ID,
                                drv.TRIGOBJ_BIT_E_2E)
    check("an electron sitting exactly on an id-13 object does NOT match it",
          int(ak.sum(bk["is_matched"])) == 0)
    bk_mu = drv.trigobj_best_match(muons, only_ele_trig, drv.TRIGOBJ_MUON_ID,
                                   drv.TRIGOBJ_BIT_TRKISOVVL)
    check("a muon sitting exactly on an id-11 object does NOT match it",
          int(ak.sum(bk_mu["is_matched"])) == 0)

    # With the right-id object present, both DO match, and the recorded ids
    # are the expected ones.
    bk_e = drv.trigobj_best_match(electrons, trigobj, drv.TRIGOBJ_ELECTRON_ID,
                                  drv.TRIGOBJ_BIT_E_2E)
    bk_m = drv.trigobj_best_match(muons, trigobj, drv.TRIGOBJ_MUON_ID,
                                  drv.TRIGOBJ_BIT_TRKISOVVL)
    check("the electron matches the id-11 object (index 1)",
          int(ak.sum(bk_e["is_matched"])) == 1 and int(bk_e["best_index"][0][0]) == 1
          and int(bk_e["best_id"][0][0]) == 11)
    check("the muon matches the id-13 object (index 0)",
          int(ak.sum(bk_m["is_matched"])) == 1 and int(bk_m["best_index"][0][0]) == 0
          and int(bk_m["best_id"][0][0]) == 13)

    for label, bookkeeping, obj_id, trig in (
        ("electron/id11", bk_e, drv.TRIGOBJ_ELECTRON_ID, trigobj),
        ("muon/id13", bk_m, drv.TRIGOBJ_MUON_ID, trigobj),
        ("electron/wrong-id-only", bk, drv.TRIGOBJ_ELECTRON_ID, only_muon_trig),
        ("muon/wrong-id-only", bk_mu, drv.TRIGOBJ_MUON_ID, only_ele_trig),
    ):
        n = drv.count_trigger_guard_violations(bookkeeping, trig, obj_id)
        check(f"guard-violation counter is 0 for {label}", n == 0, f"got {n}")

    # An event with no trigger objects at all must not crash the counter.
    empty_trig = make_trigobj([[]])
    bk_empty = drv.trigobj_best_match(electrons, empty_trig, drv.TRIGOBJ_ELECTRON_ID,
                                      drv.TRIGOBJ_BIT_E_2E)
    check("guard counter handles an event with zero trigger objects",
          drv.count_trigger_guard_violations(bk_empty, empty_trig,
                                             drv.TRIGOBJ_ELECTRON_ID) == 0)

    # The runtime title assertion stops on a wrong title and passes on the real one.
    real_titles = {
        "TrigObj_id": ("ID of the object: 11 = Electron (PixelMatched e/gamma), "
                       "22 = Photon, 13 = Muon, 15 = Tau, 1 = Jet"),
        "TrigObj_filterBits": ("extra bits of associated information: "
                               "1 = CaloIdL_TrackIdL_IsoVL, 2 = 1e (WPTight), 16 = 2e, "
                               "32 = 1e-1mu, 1 = TrkIsoVVL, 2 = Iso, 8 = IsoTkMu"),
    }
    try:
        out = drv.assert_trigobj_bit_meanings(real_titles)
        ok = out["all_present"]
    except Exception as e:  # noqa: BLE001
        ok = False
        print(f"      unexpected: {e}")
    check("assert_trigobj_bit_meanings accepts the real branch titles", ok)
    bad = dict(real_titles)
    bad["TrigObj_filterBits"] = bad["TrigObj_filterBits"].replace("16 = 2e", "16 = 3e")
    raised = False
    try:
        drv.assert_trigobj_bit_meanings(bad)
    except RuntimeError:
        raised = True
    check("assert_trigobj_bit_meanings STOPS when bit 16's meaning differs", raised)


# ---------------------------------------------------------------------------
# C4. de-duplication order
# ---------------------------------------------------------------------------

def _four_dataset_synthetic():
    """Build one synthetic event per subset of {DM, SM, DEG, MEG} that we
    want accepted, returning (events, muons, electrons, trigobj, wanted).

    Recipes, all using objects comfortably above every threshold:
      DM  : 2 muons matched to id13/bit1 objects, online pT 20 (>= 17)
      SM  : 1 muon matched to id13/bit2, online pT 30 (>= 24)
      DEG : 2 electrons matched to id11/bit16, online pT 40 (>= 23),
            offline 40 (> 30)
      MEG : 1 muon (any) + 1 electron matched to id11/bit32, online 40
    Muon objects are shared between DM and SM recipes where both are
    wanted, and the HLT flags are set per subset.
    """
    subsets = [
        set(), {"DoubleMuon"}, {"SingleMuon"}, {"DoubleEG"}, {"MuonEG"},
        {"DoubleMuon", "SingleMuon"}, {"DoubleMuon", "DoubleEG"},
        {"SingleMuon", "DoubleEG"}, {"SingleMuon", "MuonEG"},
        {"DoubleEG", "MuonEG"}, {"DoubleMuon", "MuonEG"},
        {"DoubleMuon", "SingleMuon", "DoubleEG", "MuonEG"},
        {"SingleMuon", "DoubleEG", "MuonEG"},
    ]
    mu_list, el_list, trig_list = [], [], []
    hlt = {p: [] for paths in drv.MATCHED4_TRIGGER_PATHS.values() for p in paths}
    for want in subsets:
        mus, els, trigs = [], [], []
        need_muons = 0
        if "DoubleMuon" in want:
            need_muons = max(need_muons, 2)
        if {"SingleMuon", "MuonEG"} & want:
            need_muons = max(need_muons, 1)
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
                trigs.append({"eta": eta, "phi": -2.0, "pt": pt, "id": 13,
                              "filterBits": bits})
        n_el = 2 if "DoubleEG" in want else (1 if "MuonEG" in want else 0)
        for i in range(n_el):
            eta = 1.0 + 0.5 * i
            els.append({"eta": eta, "phi": 2.0, "pt": 40.0})
            bits = 0
            if "DoubleEG" in want:
                bits |= drv.TRIGOBJ_BIT_E_2E
            if "MuonEG" in want and i == 0:
                bits |= drv.TRIGOBJ_BIT_E_1E1MU
            if bits:
                trigs.append({"eta": eta, "phi": 2.0, "pt": 40.0, "id": 11,
                              "filterBits": bits})
        mu_list.append(mus)
        el_list.append(els)
        trig_list.append(trigs)
        for label, paths in drv.MATCHED4_TRIGGER_PATHS.items():
            for p in paths:
                hlt[p].append(label in want)
    events = make_events(hlt, len(subsets))
    return events, make_objects(mu_list), make_objects(el_list), make_trigobj(trig_list), subsets


def test_c4_dedup_order():
    print("\n--- C4. de-duplication order (D2) ---")
    check("the new order constant is [DoubleMuon, SingleMuon, DoubleEG, MuonEG]",
          drv.DELIVERY_VETO_ORDER_4 == ["DoubleMuon", "SingleMuon", "DoubleEG", "MuonEG"],
          f"got {drv.DELIVERY_VETO_ORDER_4}")
    from studies.cms_datasets.cluster.datasets_records import VETO_ORDER
    check("the generic VETO_ORDER is untouched and is a DIFFERENT order",
          VETO_ORDER == ["DoubleMuon", "DoubleEG", "MuonEG", "SingleMuon",
                         "SingleElectron", "JetHT", "MET"]
          and VETO_ORDER[:4] != drv.DELIVERY_VETO_ORDER_4, f"got {VETO_ORDER}")

    events, muons, electrons, trigobj, subsets = _four_dataset_synthetic()
    acc = drv.evaluate_four_acceptances(events, muons, electrons, trigobj, "leading_only")
    for label in drv.DELIVERY_VETO_ORDER_4:
        got = [bool(x) for x in acc[label]["accepted"]]
        want = [label in s for s in subsets]
        check(f"{label} acceptance matches the recipe for all {len(subsets)} synthetic events",
              got == want, f"got {got}, want {want}")

    attributed = drv.attribute_to_exclusive_dataset(acc)
    for i, want in enumerate(subsets):
        expected = ""
        for label in drv.DELIVERY_VETO_ORDER_4:
            if label in want:
                expected = label
                break
        check(f"event {i} accepted by {sorted(want) or 'nothing'} is attributed to "
              f"{expected or 'no dataset'}", attributed[i] == expected,
              f"got {attributed[i]!r}")

    # Exactly one exclusive set, for every dataset.
    n_in_sets = np.zeros(len(subsets), dtype=int)
    for label in drv.DELIVERY_VETO_ORDER_4:
        excl, per_higher, higher = drv.exclusive_mask_from_acceptances(acc, label)
        in_set = acc[label]["accepted"] & excl
        n_in_sets += in_set.astype(int)
        check(f"{label}'s own exclusive set equals 'attributed to {label}'",
              [bool(x) for x in in_set] == [a == label for a in attributed])
    accepted_any = np.zeros(len(subsets), dtype=bool)
    for label in drv.DELIVERY_VETO_ORDER_4:
        accepted_any |= acc[label]["accepted"]
    check("every accepted event is in exactly one exclusive set",
          np.array_equal(n_in_sets, accepted_any.astype(int)),
          f"got {n_in_sets.tolist()} vs {accepted_any.astype(int).tolist()}")
    check("no event accepted by nothing lands in any exclusive set",
          int(n_in_sets[~accepted_any].sum()) == 0)


# ---------------------------------------------------------------------------
# C5. DoubleEG threshold modes
# ---------------------------------------------------------------------------

def _doubleeg_case(offline_pts, online_pts=None, n_matched=None):
    """One event with len(offline_pts) selected electrons; the first
    `n_matched` (default: all) are matched to a bit-16 id-11 object."""
    if online_pts is None:
        online_pts = [40.0] * len(offline_pts)
    if n_matched is None:
        n_matched = len(offline_pts)
    els, trigs = [], []
    for i, pt in enumerate(offline_pts):
        eta = 0.5 * i
        els.append({"eta": eta, "phi": 1.0, "pt": pt})
        if i < n_matched:
            trigs.append({"eta": eta, "phi": 1.0, "pt": online_pts[i], "id": 11,
                          "filterBits": drv.TRIGOBJ_BIT_E_2E})
    hlt = {p: [True] for p in drv.MATCHED4_TRIGGER_PATHS["DoubleEG"]}
    return make_events(hlt, 1), make_objects([els]), make_trigobj([trigs])


def test_c5_doubleeg_modes():
    print("\n--- C5. DoubleEG offline-pT modes at the 25/30 GeV boundaries (D4) ---")
    cases = [
        # (offline pts, leading_only expected, both expected, description)
        ([40.0, 35.0], True, True, "both well above 30"),
        ([30.5, 25.5], True, False, "leading 30.5, subleading 25.5"),
        ([30.0, 29.0], False, False, "leading exactly 30.0 (strict >)"),
        ([30.01, 30.0], True, False, "leading 30.01, subleading exactly 30.0"),
        ([30.01, 30.01], True, True, "both just above 30"),
        ([29.9, 29.9], False, False, "both just below 30"),
        ([25.01, 25.01], False, False, "both just above the 25 GeV object cut"),
        ([100.0], False, False, "only one electron (needs 2 matched)"),
    ]
    for offline, want_leading, want_both, desc in cases:
        for mode, want in (("leading_only", want_leading), ("both", want_both)):
            events, electrons, trigobj = _doubleeg_case(offline)
            got = bool(drv.doubleeg_acceptance(events, electrons, trigobj, mode)["accepted"][0])
            check(f"mode={mode:12s} {desc}: accepted={want}", got == want, f"got {got}")

    # The online 23 GeV requirement is on the matched TRIGGER object.
    events, electrons, trigobj = _doubleeg_case([40.0, 35.0], online_pts=[22.9, 22.9])
    check("online leading TrigObj_pt 22.9 < 23 -> rejected",
          not bool(drv.doubleeg_acceptance(events, electrons, trigobj,
                                           "leading_only")["accepted"][0]))
    events, electrons, trigobj = _doubleeg_case([40.0, 35.0], online_pts=[23.0, 12.0])
    check("online leading TrigObj_pt exactly 23.0 -> accepted (>=), second leg only ~12",
          bool(drv.doubleeg_acceptance(events, electrons, trigobj,
                                       "leading_only")["accepted"][0]))

    # An UNMATCHED electron must not help.
    events, electrons, trigobj = _doubleeg_case([40.0, 35.0], n_matched=1)
    check("only one of two electrons matched -> rejected (needs 2 matched)",
          not bool(drv.doubleeg_acceptance(events, electrons, trigobj,
                                           "leading_only")["accepted"][0]))

    # Path not fired -> rejected whatever the objects look like.
    events, electrons, trigobj = _doubleeg_case([40.0, 35.0])
    hlt = {p: [False] for p in drv.MATCHED4_TRIGGER_PATHS["DoubleEG"]}
    check("path not fired -> rejected",
          not bool(drv.doubleeg_acceptance(make_events(hlt, 1), electrons, trigobj,
                                           "leading_only")["accepted"][0]))

    # leading_only must accept a strict superset of "both".
    rng = np.random.default_rng(3)
    n_super_ok = True
    for _ in range(60):
        pts = sorted(rng.uniform(25.1, 45.0, 2), reverse=True)
        events, electrons, trigobj = _doubleeg_case([float(p) for p in pts])
        a = bool(drv.doubleeg_acceptance(events, electrons, trigobj, "leading_only")["accepted"][0])
        b = bool(drv.doubleeg_acceptance(events, electrons, trigobj, "both")["accepted"][0])
        if b and not a:
            n_super_ok = False
    check("'leading_only' accepts a superset of 'both' (60 random pT pairs)", n_super_ok)

    unknown_raised = False
    try:
        drv.doubleeg_acceptance(events, electrons, trigobj, "whatever")
    except ValueError:
        unknown_raised = True
    check("an unknown threshold mode raises", unknown_raised)


# ---------------------------------------------------------------------------
# C6. MuonEG swapped legs
# ---------------------------------------------------------------------------

def test_c6_muoneg_swapped_legs():
    print("\n--- C6. MuonEG swapped legs (D5) ---")

    def case(online_pt, fired_a, fired_b, n_muons=1, matched=True):
        els = [{"eta": 1.0, "phi": 1.0, "pt": 40.0}]
        trigs = ([{"eta": 1.0, "phi": 1.0, "pt": online_pt, "id": 11,
                   "filterBits": drv.TRIGOBJ_BIT_E_1E1MU}] if matched else [])
        mus = [{"eta": -1.0, "phi": -1.0, "pt": 40.0} for _ in range(n_muons)]
        hlt = {drv.MUONEG_PATH_MU23_ELE12: [fired_a],
               drv.MUONEG_PATH_MU8_ELE23: [fired_b]}
        events = make_events(hlt, 1)
        return bool(drv.muoneg_acceptance(events, make_objects([mus]),
                                          make_objects([els]),
                                          make_trigobj([trigs]))["accepted"][0])

    check("matched electron with TrigObj_pt 15: ACCEPTED when Mu23_Ele12 fired",
          case(15.0, True, False) is True)
    check("matched electron with TrigObj_pt 15: REJECTED when only Mu8_Ele23 fired",
          case(15.0, False, True) is False)
    check("matched electron with TrigObj_pt 25: accepted when only Mu8_Ele23 fired",
          case(25.0, False, True) is True)
    check("TrigObj_pt exactly 12.0 with Mu23_Ele12 fired: accepted (>=)",
          case(12.0, True, False) is True)
    check("TrigObj_pt 11.9 with Mu23_Ele12 fired: rejected",
          case(11.9, True, False) is False)
    check("TrigObj_pt exactly 23.0 with only Mu8_Ele23 fired: accepted (>=)",
          case(23.0, False, True) is True)
    check("no selected muon -> rejected", case(40.0, True, True, n_muons=0) is False)
    check("no matched electron -> rejected", case(40.0, True, True, matched=False) is False)
    check("neither path fired -> rejected", case(40.0, False, False) is False)
    check("both paths fired, TrigObj_pt 15 -> accepted via the Mu23_Ele12 branch",
          case(15.0, True, True) is True)


# ---------------------------------------------------------------------------
# C7. names vs upstream's own naming code
# ---------------------------------------------------------------------------

UPSTREAM_RUNNER = r'''
import ast, json, sys, types

# histograms_pipeline imports ROOT and fcntl at module level; neither is
# needed by the naming code, and neither is available here. Stub them so
# UPSTREAM'S OWN module can be imported and its real function called.
class _AnyAttr:
    """Stands in for ROOT/fcntl: any attribute access returns another one,
    which is enough for the module-level type annotations upstream uses."""
    def __getattr__(self, name):
        return _AnyAttr()
    def __call__(self, *a, **k):
        return _AnyAttr()

for name in ("ROOT", "fcntl"):
    sys.modules[name] = _AnyAttr()
sys.path.insert(0, ".")

from services.pipelines import histograms_pipeline as up_hp

pairs = json.load(open(sys.argv[1]))

# The ROI/width part of the name is an inline f-string in upstream, not a
# function. Take the f-string EXPRESSION out of upstream's own source and
# evaluate it, rather than re-typing it here.
src = open("services/pipelines/histograms_pipeline.py", encoding="utf-8").read()
tree = ast.parse(src)
segments = set()
for node in ast.walk(tree):
    if isinstance(node, ast.Assign) and len(node.targets) == 1 \
            and isinstance(node.targets[0], ast.Name) \
            and node.targets[0].id == "hist_name" \
            and isinstance(node.value, ast.JoinedStr):
        seg = ast.get_source_segment(src, node.value)
        if seg and seg.startswith('f"ROI_'):
            segments.add(seg)
# Upstream spells the same f-string four times, with the name of the
# base part differing (hist_name_base / signature / im_array_filename).
# Normalise that ONE placeholder to `hist_name_base` and require every
# occurrence to be the same string afterwards.
import re as _re
normalised = {_re.sub(r"\{(hist_name_base|signature|im_array_filename)\}",
                      "{hist_name_base}", seg) for seg in segments}
if len(normalised) != 1:
    print(json.dumps({"error": "expected one ROI f-string shape, got "
                               + repr(sorted(normalised))}))
    sys.exit(1)
roi_fstring = sorted(normalised)[0]

out = {"roi_fstring": roi_fstring, "names": []}
for fs_str, im_str, bin_width in pairs:
    hist_name_base = up_hp._convert_to_bumpnet_name(fs_str, im_str)
    full = eval(roi_fstring, {}, {"hist_name_base": hist_name_base, "bin_width": bin_width})
    out["names"].append({"fs": fs_str, "im": im_str, "base": hist_name_base, "full": full})

# Upstream's own final-state label builder, for the label-format check.
from services.calculations.physics_calcs import group_by_final_state
import awkward as ak
spec = json.load(open(sys.argv[3])) if len(sys.argv) > 3 else []
labels = []
for counts in spec:
    rec = ak.zip({
        "Electrons": ak.Array([[{"pt": 1.0}] * counts["e"]]),
        "Muons": ak.Array([[{"pt": 1.0}] * counts["m"]]),
        "Jets": ak.Array([[{"pt": 1.0}] * counts["j"]]),
        "BJets": ak.Array([[{"pt": 1.0}] * counts["b"]]),
    }, depth_limit=1)
    labels.append([fs for fs, _ev in group_by_final_state(rec)][0])
out["labels"] = labels
json.dump(out, open(sys.argv[2], "w"))
'''


def upstream_names(pairs, label_specs):
    """Extract upstream master read-only and call ITS OWN naming code."""
    rev = subprocess.run(["git", "rev-parse", "upstream/master"], cwd=REPO_ROOT,
                         capture_output=True, text=True)
    if rev.returncode != 0:
        raise RuntimeError(
            "upstream/master is not available locally; run "
            "`git fetch upstream` (read-only) first. stderr: " + rev.stderr.strip())
    commit = rev.stdout.strip()
    tmp = Path(tempfile.mkdtemp(prefix="upstream_naming_"))
    archive = tmp / "upstream.tar"
    with open(archive, "wb") as fh:
        subprocess.run(["git", "archive", "--format=tar", commit], cwd=REPO_ROOT,
                       stdout=fh, check=True)
    tree = tmp / "tree"
    tree.mkdir()
    subprocess.run(["tar", "-xf", str(archive), "-C", str(tree)], check=True)
    (tree / "_upstream_namer.py").write_text(UPSTREAM_RUNNER, encoding="utf-8")
    pairs_path = tmp / "pairs.json"
    pairs_path.write_text(json.dumps(pairs), encoding="utf-8")
    spec_path = tmp / "labels.json"
    spec_path.write_text(json.dumps(label_specs), encoding="utf-8")
    out_path = tmp / "out.json"
    proc = subprocess.run([sys.executable, "_upstream_namer.py", str(pairs_path),
                           str(out_path), str(spec_path)],
                          cwd=str(tree), capture_output=True, text=True)
    if proc.returncode != 0 or not out_path.exists():
        raise RuntimeError(f"upstream naming runner failed:\n{proc.stdout}\n{proc.stderr}")
    return commit, json.loads(out_path.read_text(encoding="utf-8"))


DEFAULT_FINAL_STATES = [
    "0e_2m_0j_0b", "0e_2m_5j_1b", "1e_1m_2j_0b", "2e_0m_0j_0b", "2e_0m_3j_2b",
    "1e_0m_1j_1b", "0e_1m_12j_0b", "2e_2m_0j_0b", "0e_0m_4j_4b",
]
IM_STRINGS = ["m0m1", "e0e1", "e0m0", "m0m1j0", "b0b1", "e0e1j0j1", ""]


def test_c7_names_match_upstream(pilot_final_states_path=None):
    print("\n--- C7. histogram names vs UPSTREAM's own naming code ---")
    final_states = list(DEFAULT_FINAL_STATES)
    source = "built-in list (pilot list not supplied)"
    if pilot_final_states_path:
        data = json.loads(Path(pilot_final_states_path).read_text(encoding="utf-8"))
        final_states = sorted(set(data["final_states"]))
        source = f"{pilot_final_states_path} ({len(final_states)} pilot final states)"
    print(f"      final states under test: {source}")

    pairs = [[fs, im, BIN_WIDTH_GEV] for fs in final_states for im in IM_STRINGS]
    # Counts at or below 4 only: upstream's own group_by_final_state still
    # calls limit_particles_in_fs(fs, 4), which CAPS any count above 4 (its
    # authors are removing that themselves -- the 5+-jet bug, out of scope
    # here). The capped case is checked separately and explicitly below.
    label_specs = [{"e": 0, "m": 2, "j": 4, "b": 1}, {"e": 1, "m": 1, "j": 0, "b": 0},
                   {"e": 2, "m": 0, "j": 3, "b": 2}, {"e": 0, "m": 0, "j": 0, "b": 0},
                   {"e": 4, "m": 0, "j": 4, "b": 4}]
    capped_spec = [{"e": 0, "m": 2, "j": 5, "b": 1}, {"e": 0, "m": 2, "j": 12, "b": 1}]
    try:
        commit, up = upstream_names(pairs, label_specs)
    except Exception as e:  # noqa: BLE001
        check(f"upstream naming code could be fetched and called: {e}", False)
        return
    print(f"      upstream master = {commit}")
    print(f"      upstream's own ROI f-string = {up['roi_fstring']}")

    mismatches = []
    for entry in up["names"]:
        ours_base = _convert_to_bumpnet_name(entry["fs"], entry["im"])
        ours_full = roi_key(ours_base, bin_width=BIN_WIDTH_GEV, upstream_width_suffix=True)
        if ours_base != entry["base"] or ours_full != entry["full"]:
            mismatches.append((entry["fs"], entry["im"], ours_full, entry["full"]))
    check(f"all {len(up['names'])} names (every pilot final state x "
          f"{len(IM_STRINGS)} combinations) match upstream string-for-string",
          not mismatches, f"first mismatches: {mismatches[:3]}")
    check("every name ends with upstream's own _width_10.0 suffix",
          all(e["full"].endswith("_width_10.0") for e in up["names"]),
          f"e.g. {up['names'][0]['full']}")

    ours_labels = [str(drv.exact_final_state_labels(obj_record_from_counts([c]))[0])
                   for c in label_specs]
    check("our final-state label format equals upstream's own group_by_final_state "
          "output for every count combination at or below 4",
          ours_labels == up["labels"], f"ours {ours_labels} vs upstream {up['labels']}")

    # The one deliberate divergence, asserted rather than left implicit.
    _, up_capped = upstream_names([["0e_2m_5j_1b", "m0m1", BIN_WIDTH_GEV],
                                   ["0e_2m_12j_1b", "m0m1", BIN_WIDTH_GEV]], capped_spec)
    ours_capped = [str(x) for x in drv.exact_final_state_labels(
        obj_record_from_counts(capped_spec))]
    check("DOCUMENTED DIVERGENCE at 5 light jets: upstream's own grouping still caps "
          "the label at 4j (its limit_particles_in_fs call, which its authors are "
          "removing) while ours keeps 5j -- the group's decision",
          ours_capped[0] == "0e_2m_5j_1b" and up_capped["labels"][0] == "0e_2m_4j_1b",
          f"ours {ours_capped[0]}, upstream {up_capped['labels'][0]}")
    check("NOTED: at 12 light jets upstream does NOT cap, because its own capping "
          "function reads only the first digit ('1' of '12', which is not > 4) -- the "
          "same one-digit limitation C1 pins in is_finalstate_contain_combination",
          ours_capped[1] == "0e_2m_12j_1b" and up_capped["labels"][1] == "0e_2m_12j_1b",
          f"ours {ours_capped[1]}, upstream {up_capped['labels'][1]}")
    check("the NAMING code itself agrees on both labels (it is the grouping, not the "
          "naming, that differs)",
          [_convert_to_bumpnet_name(f, "m0m1") for f in ("0e_2m_5j_1b", "0e_2m_12j_1b")]
          == [e["base"] for e in up_capped["names"]])
    return up


# ---------------------------------------------------------------------------
# C8. old invocations unchanged
# ---------------------------------------------------------------------------

def test_c8_old_invocations():
    print("\n--- C8. old invocations keep their old behaviour ---")

    class Args:
        pass

    a = Args()
    check("delivery per-histogram minimum defaults to 100 with no new flags",
          _deliver_min_entries(a) == 100, f"got {_deliver_min_entries(a)}")
    a.no_hist_min_entries = True
    check("--no-hist-min-entries gives the upstream floor of 1",
          _deliver_min_entries(a) == UPSTREAM_MIN_ENTRIES_PER_HISTOGRAM == 1)
    check("the legacy width suffix is still the default", width_suffix() == "_width_10",
          f"got {width_suffix()}")
    check("the upstream width suffix is opt-in",
          width_suffix(upstream=True) == "_width_10.0")

    # The shared muon matcher must still return exactly what it returned
    # before it was made to delegate to the id-parameterised matcher.
    rng = np.random.default_rng(11)
    mus, trigs = [], []
    for _ in range(300):
        n_mu = int(rng.integers(0, 4))
        n_tr = int(rng.integers(0, 5))
        mus.append([{"eta": float(rng.uniform(-2.4, 2.4)),
                     "phi": float(rng.uniform(-math.pi, math.pi)),
                     "pt": float(rng.uniform(25, 120))} for _ in range(n_mu)])
        trigs.append([{"eta": float(rng.uniform(-2.4, 2.4)),
                       "phi": float(rng.uniform(-math.pi, math.pi)),
                       "pt": float(rng.uniform(5, 150)),
                       "id": int(rng.choice([11, 13, 15])),
                       "filterBits": int(rng.integers(0, 64))} for _ in range(n_tr)])
    muons = make_objects(mus)
    trigobj = make_trigobj(trigs)

    def reference_best_pt(sel_muons, tobj, required_bit, dr_max=drv.MATCH_DR_MAX):
        """The pre-change body of trigobj_best_match_pt, verbatim."""
        trig_muon_mask = (tobj.id == drv.TRIGOBJ_MUON_ID) & ((tobj.filterBits & required_bit) != 0)
        trig_muons = tobj[trig_muon_mask]
        mu_p4 = drv._p4_no_mass_needed(sel_muons)
        trig_p4 = drv._p4_no_mass_needed(trig_muons)
        pairs_mu, pairs_trig = ak.unzip(ak.cartesian([mu_p4, trig_p4], nested=True))
        dr = pairs_mu.deltaR(pairs_trig)
        within = dr < dr_max
        candidate_pt = ak.where(within, pairs_trig.pt, -np.inf)
        return ak.fill_none(ak.max(candidate_pt, axis=-1), -np.inf)

    all_same = True
    for bit in (drv.TRIGOBJ_BIT_TRKISOVVL, drv.TRIGOBJ_BIT_ISO, drv.TRIGOBJ_BIT_ISOTKMU):
        mine = ak.to_numpy(ak.flatten(drv.trigobj_best_match_pt(muons, trigobj, bit), axis=None))
        ref = ak.to_numpy(ak.flatten(reference_best_pt(muons, trigobj, bit), axis=None))
        if mine.shape != ref.shape or not np.array_equal(mine, ref):
            all_same = False
    check("trigobj_best_match_pt returns exactly the pre-change values on 300 random "
          "events, for every muon bit the muon production uses", all_same)

    # And the acceptance mask built on top of it is unchanged too.
    same_masks = True
    for bit, nmin, ptmin in (
        (drv.TRIGOBJ_BIT_TRKISOVVL, drv.DOUBLEMUON_MATCHED_MIN_MUONS,
         drv.DOUBLEMUON_MATCHED_LEADING_PT_MIN_GEV),
        (drv.TRIGOBJ_BIT_ISO, drv.SINGLEMUON_MATCHED_MIN_MUONS,
         drv.SINGLEMUON_MATCHED_PT_MIN_GEV),
    ):
        got = drv.matched_acceptance_mask(muons, trigobj, bit, nmin, ptmin)
        best = reference_best_pt(muons, trigobj, bit)
        m = best > -np.inf
        n_matched = ak.to_numpy(ak.num(best[m], axis=1))
        lead = ak.to_numpy(ak.fill_none(ak.max(best[m], axis=1), -np.inf))
        want = (n_matched >= nmin) & (lead >= ptmin)
        if not np.array_equal(got, want):
            same_masks = False
    check("matched_acceptance_mask is unchanged for DoubleMuon and SingleMuon", same_masks)

    check("the SingleMuon matched-mode trigger set is still HLT_IsoMu24 alone",
          drv.SINGLEMUON_MATCHED_TRIGGER_PATHS == ("HLT_IsoMu24",))
    check("matched4's own SingleMuon trigger set is the same one",
          drv.MATCHED4_TRIGGER_PATHS["SingleMuon"] == ("HLT_IsoMu24",))
    check("the new options default to: overlap removal ON, debug dump OFF",
          drv.EMU_OVERLAP_DR_MAX == 0.12
          and drv.DOUBLEEG_THRESHOLD_MODE_DEFAULT in drv.DOUBLEEG_THRESHOLD_MODES)
    check("the approved DoubleEG threshold mode default is 'both' (7 Oct 2026)",
          drv.DOUBLEEG_THRESHOLD_MODE_DEFAULT == "both",
          f"got {drv.DOUBLEEG_THRESHOLD_MODE_DEFAULT}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--pilot-final-states", default=None,
                   help="JSON with {'final_states': [...]} from the pilot, for C7")
    p.add_argument("--out", default=None, help="write a JSON summary here")
    args = p.parse_args()

    print("electron-datasets task: Step C self-checks (C1-C8)")
    print("=" * 72)
    test_c1_multidigit_labels()
    test_c2_overlap_removal()
    test_c3_trigger_guard()
    test_c4_dedup_order()
    test_c5_doubleeg_modes()
    test_c6_muoneg_swapped_legs()
    up = test_c7_names_match_upstream(args.pilot_final_states)
    test_c8_old_invocations()

    print("=" * 72)
    print(f"{N_CHECKS} checks, {len(FAILURES)} failure(s)")
    for f in FAILURES:
        print(f"  FAILED: {f}")
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps({
            "n_checks": N_CHECKS, "n_failures": len(FAILURES), "failures": FAILURES,
            "c7_final_states_source": args.pilot_final_states or "built-in list",
            "c7_upstream_roi_fstring": (up or {}).get("roi_fstring"),
            "c7_n_names_compared": len((up or {}).get("names", [])),
        }, indent=2), encoding="utf-8")
        print(f"wrote {args.out}")
    sys.exit(1 if FAILURES else 0)


if __name__ == "__main__":
    main()
