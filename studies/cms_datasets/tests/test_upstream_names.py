"""
Self-checks for the upstream-names task on the Version B (rare4) CMS
delivery path.

Covers, with real (not mocked) code:
  1. Label format -- the driver's own grouping produces labels containing
     ONLY the configured object types, in upstream's fixed order, for
     events with 0, 5 and 11 light jets (and a few others).
  2. Label format matches UPSTREAM exactly -- upstream's own label-building
     code (services/calculations/physics_calcs.py:group_by_final_state at
     commit 88d7a4b) is replicated here from its source and compared
     against ours on the same synthetic events.
  3. Legacy conversion -- old six-field labels convert to the new form,
     two-digit counts survive, a NON-ZERO photon or tau count ABORTS, and
     no two distinct names collapse onto one.
  4. Histogram-name format -- compared against upstream's own
     _convert_to_bumpnet_name (services/pipelines/histograms_pipeline.py at
     88d7a4b), replicated here from its source, on the same inputs.
  5. The new per-histogram minimum-entries behaviour, and that the default
     is unchanged.

Run directly:
    python studies/cms_datasets/tests/test_upstream_names.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

import awkward as ak  # noqa: E402
import numpy as np  # noqa: E402

from studies.cms_datasets.cluster.run_dataset_on_file import (  # noqa: E402
    FINAL_STATE_OBJECTS,
    OBJECT_TYPES,
    _group_by_final_state_with_mask,
)
from studies.cms_datasets.deliver.build_muon_combined_delivery import (  # noqa: E402
    UPSTREAM_MIN_ENTRIES_PER_HISTOGRAM,
    assert_no_name_collisions,
    convert_legacy_fs_label,
    _deliver_min_entries,
)
from studies.cms_coverage.cluster.merge_and_count import MIN_BUMPNET_EVENTS  # noqa: E402
from studies.m0m1j0_cms.histograms import _convert_to_bumpnet_name  # noqa: E402

FAILURES = []


def check(name: str, condition: bool, detail: str = ""):
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {name}" + (f" -- {detail}" if detail and not condition else ""))
    if not condition:
        FAILURES.append(name)


# --------------------------------------------------------------------------
# Reference implementations, replicated from UPSTREAM source at 88d7a4b.
# These are the thing we must match; they are test-only and never imported
# by production code.
# --------------------------------------------------------------------------

def upstream_group_by_final_state_labels(events: ak.Array):
    """Replicated from upstream services/calculations/physics_calcs.py
    group_by_final_state at commit 88d7a4b, minus its final
    limit_particles_in_fs(fs, 4) capping call -- the upstream authors' own
    pending fix removes that capping, and Maryna's decision is to keep our
    exact light-jet multiplicities. Everything about the NAME (which types
    appear, their order, the separator, the f"{count}{letter}" form) is
    upstream's, unchanged."""
    num_events = len(events)
    zero_array = ak.Array([0] * num_events) if num_events > 0 else ak.Array([])
    particle_counts = ak.num(events)

    object_types = (
        ("Electrons", "e"), ("Muons", "m"), ("Jets", "j"),
        ("Photons", "g"), ("Taus", "t"), ("BJets", "b"),
    )
    present_types = [
        (name, letter, getattr(particle_counts, name, zero_array))
        for name, letter in object_types
        if name in events.fields
    ]
    return [
        "_".join(
            f"{count}{letter}"
            for (_name, letter, _values), count in zip(present_types, counts)
        )
        for counts in zip(*[values for _name, _letter, values in present_types])
    ]


def upstream_convert_to_bumpnet_name(fs_str: str, im_str: str) -> str:
    """Replicated verbatim from upstream
    services/pipelines/histograms_pipeline.py _convert_to_bumpnet_name at
    commit 88d7a4b."""
    combo = im_str if im_str else "none"
    fs_particles = re.findall(r'(\d+)([emjgtb])', fs_str)
    fs_formatted = "_".join(f"{c}{p}x" for c, p in fs_particles)
    result = f"mass_{combo}_cat_{fs_formatted}"
    if 'cat' not in result and 'hCat' not in result:
        raise ValueError(
            f"Generated histogram name '{result}' doesn't contain 'cat' - "
            "BumpNet incompatible"
        )
    return result


def make_obj_record(events):
    """Synthetic obj_record in exactly the layout
    studies.m0m1j0_cms.selection.build_object_record produces: an ak.zip of
    Electrons/Muons/Jets/BJets, depth_limit=1. Photons and Taus are genuinely
    absent, as in the real driver."""
    fields = {}
    for field in ("Electrons", "Muons", "Jets", "BJets"):
        per_event = []
        for i, ev in enumerate(events):
            n = int(ev.get(field, 0))
            per_event.append([100.0 + 10.0 * (n - k) + 0.25 * i for k in range(n)])
        fields[field] = ak.zip({"pt": ak.Array(per_event)})
    return ak.zip(fields, depth_limit=1)


# --------------------------------------------------------------------------
# 1 + 2. Label format, and agreement with upstream
# --------------------------------------------------------------------------

def test_label_format():
    print("\n--- 1. Label format: configured object types only ---")
    check("this study configures exactly Electrons, Muons, Jets, BJets",
          OBJECT_TYPES == ["Electrons", "Muons", "Jets", "BJets"],
          f"got {OBJECT_TYPES}")
    check("FINAL_STATE_OBJECTS is upstream's tuple, in upstream's order",
          FINAL_STATE_OBJECTS == (("Electrons", "e"), ("Muons", "m"), ("Jets", "j"),
                                  ("Photons", "g"), ("Taus", "t"), ("BJets", "b")),
          f"got {FINAL_STATE_OBJECTS}")

    jet_counts = [0, 1, 3, 4, 5, 6, 11]
    events = [{"Muons": 2, "Jets": n, "BJets": 1} for n in jet_counts]
    obj_record = make_obj_record(events)
    labels = [lb for lb, _ev, _m in _group_by_final_state_with_mask(obj_record)]

    for n in jet_counts:
        expected = f"0e_2m_{n}j_1b"
        check(f"{n} light jets -> {expected}", expected in labels,
              f"got {sorted(labels)}")

    check("no label contains a photon field", not any("g" in lb for lb in labels),
          f"got {sorted(labels)}")
    check("no label contains a tau field", not any("t" in lb for lb in labels),
          f"got {sorted(labels)}")
    for lb in labels:
        toks = lb.split("_")
        check(f"exactly four <count><letter> fields in order e, m, j, b: {lb}",
              len(toks) == 4 and [t[-1] for t in toks] == ["e", "m", "j", "b"]
              and all(t[:-1].isdigit() for t in toks))

    # Zero light jets and zero b-jets must still appear as explicit 0 fields.
    zero_rec = make_obj_record([{"Muons": 2}])
    zero_labels = [lb for lb, _e, _m in _group_by_final_state_with_mask(zero_rec)]
    check("zero counts are kept as explicit 0 fields: 0e_2m_0j_0b",
          zero_labels == ["0e_2m_0j_0b"], f"got {zero_labels}")


def test_matches_upstream_labels():
    print("\n--- 2. Labels agree with upstream's own code, event by event ---")
    events = (
        [{"Muons": 2, "Jets": n, "BJets": 1} for n in (0, 1, 2, 3, 4, 5, 6, 9, 11, 13)]
        + [{"Electrons": e, "Muons": m, "Jets": j, "BJets": b}
           for e in (0, 1, 2) for m in (0, 2) for j in (0, 5) for b in (0, 3)]
    )
    obj_record = make_obj_record(events)

    upstream_labels = upstream_group_by_final_state_labels(obj_record)
    ours_by_event = [None] * len(events)
    for label, _ev, mask in _group_by_final_state_with_mask(obj_record):
        for i, hit in enumerate(np.asarray(mask)):
            if hit:
                ours_by_event[i] = label

    mismatches = [(i, upstream_labels[i], ours_by_event[i])
                  for i in range(len(events)) if upstream_labels[i] != ours_by_event[i]]
    check(f"our label == upstream's label for all {len(events)} synthetic events",
          not mismatches, f"{len(mismatches)} mismatches, first: {mismatches[:3]}")
    print(f"       e.g. event 0 -> {ours_by_event[0]!r}, "
          f"event 5 -> {ours_by_event[5]!r}, event 8 -> {ours_by_event[8]!r}")


# --------------------------------------------------------------------------
# 3. Legacy conversion
# --------------------------------------------------------------------------

def test_legacy_conversion():
    print("\n--- 3. Legacy six-field -> upstream conversion ---")
    cases = [
        ("0e_2m_5j_0g_0t_1b", "0e_2m_5j_1b"),
        ("0e_2m_0j_0g_0t_0b", "0e_2m_0j_0b"),
        ("0e_2m_11j_0g_0t_1b", "0e_2m_11j_1b"),
        ("1e_1m_12j_0g_0t_4b", "1e_1m_12j_4b"),
        ("2e_2m_0j_0g_0t_4b", "2e_2m_0j_4b"),
        ("0e_1m_99j_0g_0t_0b", "0e_1m_99j_0b"),
    ]
    for legacy, expected in cases:
        got = convert_legacy_fs_label(legacy)
        check(f"{legacy} -> {expected}", got == expected, f"got {got}")

    check("a label already in the new format is left unchanged",
          convert_legacy_fs_label("0e_2m_5j_1b") == "0e_2m_5j_1b")

    # ABORT on a non-zero photon or tau count.
    for bad in ("0e_2m_5j_1g_0t_1b", "0e_2m_5j_0g_2t_1b", "0e_2m_5j_3g_4t_1b"):
        try:
            convert_legacy_fs_label(bad)
            check(f"ABORTS on a non-zero g/t count: {bad}", False, "no exception raised")
        except ValueError as exc:
            check(f"ABORTS on a non-zero g/t count: {bad}",
                  "NON-ZERO" in str(exc), f"wrong message: {exc}")

    # Unparsable input must raise rather than guess.
    for bad in ("0e_2m_xj_0g_0t_1b", "0e_2m__0g_0t_1b", "nonsense"):
        try:
            convert_legacy_fs_label(bad)
            check(f"rejects an unparsable label: {bad!r}", False, "no exception raised")
        except ValueError:
            check(f"rejects an unparsable label: {bad!r}", True)

    # No two distinct names may collapse onto one.
    legacy_map = {
        "j_FS_0e_2m_5j_0g_0t_1b_IM_m0m1": ("mass_m0m1_cat_0ex_2mx_5jx_0gx_0tx_1bx",
                                           "0e_2m_5j_0g_0t_1b", "m0m1"),
        "j_FS_0e_2m_4j_0g_0t_1b_IM_m0m1": ("mass_m0m1_cat_0ex_2mx_4jx_0gx_0tx_1bx",
                                           "0e_2m_4j_0g_0t_1b", "m0m1"),
    }
    new_map = {
        sig: (_convert_to_bumpnet_name(convert_legacy_fs_label(fs), im),
              convert_legacy_fs_label(fs), im)
        for sig, (_old, fs, im) in legacy_map.items()
    }
    n = assert_no_name_collisions(legacy_map, new_map)
    check("no-collision check passes for distinct labels (2 names in, 2 out)", n == 2,
          f"got {n}")

    # And it must FAIL loudly if two names really did collapse.
    colliding_new = {sig: ("mass_m0m1_cat_0ex_2mx_4jx_1bx", "0e_2m_4j_1b", "m0m1")
                     for sig in legacy_map}
    try:
        assert_no_name_collisions(legacy_map, colliding_new)
        check("no-collision check FAILS when two names collapse onto one", False,
              "no AssertionError raised")
    except AssertionError as exc:
        check("no-collision check FAILS when two names collapse onto one",
              "collapsed" in str(exc), f"wrong message: {exc}")


# --------------------------------------------------------------------------
# 4. Histogram names match upstream
# --------------------------------------------------------------------------

def test_histogram_names_match_upstream():
    print("\n--- 4. Histogram names match upstream's _convert_to_bumpnet_name ---")
    pairs = [
        ("0e_2m_5j_1b", "m0m1"),
        ("0e_2m_0j_0b", "m0m1"),
        ("0e_1m_11j_0b", "j0j1j2j3"),
        ("1e_1m_12j_4b", "e0m0b0"),
        ("0e_2m_4j_2b", "m0m1j0b1"),
        ("2e_0m_1j_0b", "e0e1"),
    ]
    for fs, im in pairs:
        ours = _convert_to_bumpnet_name(fs, im)
        theirs = upstream_convert_to_bumpnet_name(fs, im)
        check(f"{fs} + {im} -> {ours}", ours == theirs, f"upstream gives {theirs}")

    check("example from the task: 0e_2m_5j_1b + m0m1 -> mass_m0m1_cat_0ex_2mx_5jx_1bx",
          _convert_to_bumpnet_name("0e_2m_5j_1b", "m0m1")
          == "mass_m0m1_cat_0ex_2mx_5jx_1bx",
          f"got {_convert_to_bumpnet_name('0e_2m_5j_1b', 'm0m1')}")

    # The legacy name and the converted name differ exactly by the g/t fields.
    legacy_name = _convert_to_bumpnet_name("0e_2m_5j_0g_0t_1b", "m0m1")
    new_name = _convert_to_bumpnet_name(convert_legacy_fs_label("0e_2m_5j_0g_0t_1b"),
                                        "m0m1")
    check("legacy name was mass_m0m1_cat_0ex_2mx_5jx_0gx_0tx_1bx",
          legacy_name == "mass_m0m1_cat_0ex_2mx_5jx_0gx_0tx_1bx", f"got {legacy_name}")
    check("converted name drops exactly the 0gx and 0tx fields",
          new_name == legacy_name.replace("_0gx", "").replace("_0tx", ""),
          f"got {new_name}")

    # The prefix/suffix conventions themselves.
    check("name starts with mass_ and carries the _cat_ separator",
          new_name.startswith("mass_") and "_cat_" in new_name)
    cat = new_name.split("_cat_", 1)[1]
    check("every field in the cat part ends with the x suffix",
          all(tok.endswith("x") for tok in cat.split("_")), f"got {cat}")


# --------------------------------------------------------------------------
# 5. Per-histogram minimum entries
# --------------------------------------------------------------------------

class _Args:
    def __init__(self, no_hist_min_entries):
        self.no_hist_min_entries = no_hist_min_entries


def test_min_entries():
    print("\n--- 5. Per-histogram minimum entries ---")
    check("upstream floor is 1 entry (upstream applies no minimum and only "
          "skips a signature with no data at all)",
          UPSTREAM_MIN_ENTRIES_PER_HISTOGRAM == 1,
          f"got {UPSTREAM_MIN_ENTRIES_PER_HISTOGRAM}")
    check("default (flag off) is unchanged at 100",
          _deliver_min_entries(_Args(False)) == MIN_BUMPNET_EVENTS == 100,
          f"got {_deliver_min_entries(_Args(False))}")
    check("with --no-hist-min-entries the floor becomes 1",
          _deliver_min_entries(_Args(True)) == 1,
          f"got {_deliver_min_entries(_Args(True))}")

    # The practical consequence, stated as a check so it cannot drift.
    counts = {"a": 0, "b": 1, "c": 99, "d": 100, "e": 5000}
    kept_default = sorted(k for k, v in counts.items()
                          if v >= _deliver_min_entries(_Args(False)))
    kept_upstream = sorted(k for k, v in counts.items()
                           if v >= _deliver_min_entries(_Args(True)))
    check("default keeps only >=100-entry histograms", kept_default == ["d", "e"],
          f"got {kept_default}")
    check("upstream mode keeps every histogram with at least one entry, and "
          "drops only the empty one",
          kept_upstream == ["b", "c", "d", "e"], f"got {kept_upstream}")


def main():
    print("=" * 74)
    print("upstream-names task: self-checks")
    print("=" * 74)
    test_label_format()
    test_matches_upstream_labels()
    test_legacy_conversion()
    test_histogram_names_match_upstream()
    test_min_entries()

    print("\n" + "=" * 74)
    if FAILURES:
        print(f"{len(FAILURES)} CHECK(S) FAILED:")
        for name in FAILURES:
            print(f"  - {name}")
        sys.exit(1)
    print("ALL CHECKS PASSED")


if __name__ == "__main__":
    main()
