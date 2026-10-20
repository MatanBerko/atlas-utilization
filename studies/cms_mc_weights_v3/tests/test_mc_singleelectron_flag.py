"""
Self-checks for the MC side of Maryna's 20 Oct 2026 decisions:

  F1  the per-file MC driver stores the delivered SingleElectron acceptance
      as acceptance bit 6, computed by the DATA path's own
      singleelectron_acceptance (the T = 32 GeV rule); bits 0-5 keep their
      meaning; the store rule keeps exactly the events the old rule kept
      (bit 6 is a subset of the bit-4 candidate).
  F2  the MC builder's event union is the five delivered flags (bits 0-3
      and 6), and the builder refuses per-file outputs made before bit 6
      existed.

Run directly:
    python studies/cms_mc_weights_v3/tests/test_mc_singleelectron_flag.py
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

import numpy as np  # noqa: E402

from studies.cms_datasets.cluster import run_dataset_on_file as drv  # noqa: E402
from studies.cms_datasets.tests.test_btag_singleelectron import (  # noqa: E402
    ELE27,
    _five_dataset_synthetic,
    make_events5,
)
from studies.cms_datasets.tests.test_electron_datasets import (  # noqa: E402
    make_objects,
    make_trigobj,
)
from studies.cms_mc_weights_v3.deliver import build_mc_delivery as B  # noqa: E402

FAILURES: list[str] = []
N_CHECKS = 0


def check(name: str, condition: bool, detail: str = ""):
    global N_CHECKS
    N_CHECKS += 1
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {name}" + (f" -- {detail}" if detail and not condition else ""))
    if not condition:
        FAILURES.append(name)


def _random_events(n=3000, seed=20261020):
    rng = np.random.default_rng(seed)
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
    return events, make_objects(el_list), make_trigobj(trig_list)


def test_f1_driver_bits():
    print("\n--- F1. MC driver: SingleElectron acceptance bit ---")
    check("bit 6 = 64 is the SingleElectron acceptance; bits 0-5 unchanged",
          drv.MC_ACC_BIT_SINGLEELECTRON == 64
          and drv.MC_ACC_BIT_BY_LABEL == {"DoubleMuon": 1, "SingleMuon": 2,
                                          "DoubleEG": 4, "MuonEG": 8}
          and drv.MC_ACC_BIT_ELE27_CANDIDATE == 16 and drv.MC_ACC_BIT_ELE27_FIRED == 32)
    check("the delivery union is bits 0-3 and 6 (= 79)",
          drv.MC_ACC_BITS_DELIVERY_UNION == 79)

    # Five-dataset synthetic events: bit 6 is set exactly when the data
    # path's SingleElectron acceptance passes.
    events, muons, electrons, trigobj, subsets, _m = _five_dataset_synthetic(n_copies=1)
    acc4 = drv.evaluate_four_acceptances(events, muons, electrons, trigobj, "both")
    ele27 = drv.ele27_candidate_acceptance(events, electrons, trigobj)
    se = drv.singleelectron_acceptance(events, electrons, trigobj)
    mask = drv.mc_acceptance_bitmask(acc4, ele27, se)
    bit6 = (mask & drv.MC_ACC_BIT_SINGLEELECTRON) != 0
    check("bit 6 is set exactly for the events whose recipe includes SingleElectron",
          [bool(x) for x in bit6] == ["SingleElectron" in s for s in subsets])
    for label, bit in drv.MC_ACC_BIT_BY_LABEL.items():
        check(f"bit value {bit} ({label}) unchanged: equals the data acceptance",
              np.array_equal((mask & bit) != 0, acc4[label]["accepted"]))

    # Random events: bit 6 is the data function, bit 4 is a superset, so
    # the store rule keeps exactly what the old rule (four OR bit 4) kept.
    events, electrons, trigobj = _random_events()
    muons = make_objects([[] for _ in range(len(events))])
    acc4 = drv.evaluate_four_acceptances(events, muons, electrons, trigobj, "both")
    ele27 = drv.ele27_candidate_acceptance(events, electrons, trigobj)
    se = drv.singleelectron_acceptance(events, electrons, trigobj)
    mask = drv.mc_acceptance_bitmask(acc4, ele27, se)
    bit6 = (mask & drv.MC_ACC_BIT_SINGLEELECTRON) != 0
    bit4 = (mask & drv.MC_ACC_BIT_ELE27_CANDIDATE) != 0
    check(f"bit 6 equals singleelectron_acceptance on {len(events)} random events "
          f"({int(bit6.sum())} set)", np.array_equal(bit6, se["accepted"]) and bit6.any())
    check("bit 6 implies bit 4 (the T = 32 rule is a subset of the candidate)",
          not np.any(bit6 & ~bit4))
    check("bit 4 has events bit 6 does not (offline pT <= 32, or a different "
          "electron) -- so the two are really different conditions",
          bool(np.any(bit4 & ~bit6)))
    keep_old = ele27["accepted"].copy()
    for label in drv.DELIVERY_VETO_ORDER_4:
        keep_old |= acc4[label]["accepted"]
    check("the store rule keeps exactly the events the old rule kept",
          np.array_equal(drv.mc_store_mask(acc4, ele27, se), keep_old))


def _write_meta(job_dir: Path, bit_map):
    job_dir.mkdir(parents=True)
    (job_dir / B.SHARD_NAME).write_bytes(b"")
    meta = {"is_mc": True, "record_id": 67801, "file_index": 0}
    if bit_map is not None:
        meta["mc_diagnostics"] = {"acceptance_bit_map": bit_map}
    (job_dir / "job_metadata.json").write_text(json.dumps(meta))


def test_f2_builder_union():
    print("\n--- F2. MC builder: five-flag event union ---")
    cases = {
        "DoubleMuon only": (drv.MC_ACC_BIT_BY_LABEL["DoubleMuon"], True),
        "MuonEG only": (drv.MC_ACC_BIT_BY_LABEL["MuonEG"], True),
        "SingleElectron (bit 6, with bits 4 and 5)": (64 | 16 | 32, True),
        "Ele27 candidate only (bit 4, offline <= 32)": (16 | 32, False),
        "Ele27 fired only (bit 5)": (32, False),
        "nothing": (0, False),
    }
    for name, (bits, want) in cases.items():
        got = bool(B.event_union_mask(np.array([bits], dtype=np.uint8))[0])
        check(f"event union: {name} -> {'kept' if want else 'dropped'}", got is want)

    old_map = {"DoubleMuon": 1, "SingleMuon": 2, "DoubleEG": 4, "MuonEG": 8,
               "Ele27Candidate": 16, "Ele27Fired": 32}
    new_map = dict(old_map, SingleElectron=64)
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _write_meta(root / "old" / "record67801" / "job_0", old_map)
        _write_meta(root / "new" / "record67801" / "job_0", new_map)
        _write_meta(root / "fixture" / "record67801" / "job_0", None)
        refused = False
        try:
            B.discover_jobs(root / "old", None, None)
        except SystemExit as exc:
            refused = "SingleElectron" in str(exc)
        check("the builder REFUSES per-file outputs made before bit 6 existed", refused)
        jobs = B.discover_jobs(root / "new", None, None)
        check("the builder accepts per-file outputs that carry bit 6",
              list(jobs) == ["67801"])
        jobs = B.discover_jobs(root / "fixture", None, None)
        check("metadata without mc_diagnostics (test fixtures) is still accepted",
              list(jobs) == ["67801"])


def main():
    print("MC side of the 20 Oct 2026 decisions: SingleElectron flag and five-flag union")
    print("=" * 72)
    test_f1_driver_bits()
    test_f2_builder_union()
    print("=" * 72)
    print(f"{N_CHECKS} checks, {len(FAILURES)} failure(s)")
    for f in FAILURES:
        print(f"  FAILED: {f}")
    sys.exit(1 if FAILURES else 0)


if __name__ == "__main__":
    main()
