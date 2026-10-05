"""
Self-checks for the exact-jet-labels task (B1-B4) on the Version B (rare4)
CMS delivery path.

Covers, with real (not mocked) code:
  1. B1  -- exact light-jet labels: 3/4/5/6/11 light jets give 3j/4j/5j/6j/11j.
  2. B1  -- event conservation: the total number of events summed over all
            labels is identical to the OLD capped grouping on the same input,
            and every event keeps exactly the objects it had.
  3. B1  -- multi-digit label parsing on this delivery path: whether the
            shared single-digit parser in
            physics_calcs.is_finalstate_contain_combination can ever give a
            WRONG answer for a label this delivery can actually produce.
  4. B2  -- Z cut 115 -> 110: dilepton values in [110, 115) are now kept
            where 115 removed them; non-dilepton signatures behave exactly
            as before.
  5. B3  -- aligned outlier split: a concrete array where the old and new
            split differ, with the new cut landing on a 10 GeV bin edge.

Run directly:
    python studies/cms_datasets/tests/test_exact_jet_labels.py
"""
from __future__ import annotations

import logging
import math
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

import awkward as ak  # noqa: E402
import numpy as np  # noqa: E402

from services.calculations import physics_calcs  # noqa: E402
from services.calculations.combinatorics import (  # noqa: E402
    get_all_combinations,
    get_count,
    get_start,
)
from services.pipelines.post_processing_pipeline import (  # noqa: E402
    _apply_z_peak_cut,
    _split_by_first_empty_bin,
)
from studies.cms_coverage.cluster.merge_and_count import Z_PEAK_CUTOFF  # noqa: E402
from studies.cms_datasets.cluster.run_dataset_on_file import (  # noqa: E402
    _group_by_final_state_with_mask,
    MAX_COUNT_PARTICLE_IN_COMBINATION,
    MAX_PARTICLES_IN_COMBINATION,
    MAX_SUBLEADING_INDEX,
    MAX_TOTAL_PARTICLES_IN_COMBINATION,
    MIN_COUNT_PARTICLE_IN_COMBINATION,
    MIN_PARTICLES_IN_COMBINATION,
    INCLUDE_SUBLEADING,
    OBJECT_TYPES,
)

LOGGER = logging.getLogger("test_exact_jet_labels")
BIN_WIDTH_GEV = 10.0

FAILURES = []


def check(name: str, condition: bool, detail: str = ""):
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {name}" + (f" -- {detail}" if detail else ""))
    if not condition:
        FAILURES.append(name)


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------

def make_obj_record(events):
    """Build a synthetic obj_record in exactly the layout
    studies.m0m1j0_cms.selection.build_object_record produces: an ak.zip of
    the four fields Electrons/Muons/Jets/BJets, depth_limit=1, each a
    per-event list of objects carrying a `pt`. Photons/Taus are genuinely
    absent, as they are in the real driver -- which is why
    _group_by_final_state_with_mask falls back to a zero array for them.

    `events` is a list of dicts like {"Muons": 2, "Jets": 5, "BJets": 1},
    giving the object COUNT per type for each event. pt values are made
    distinct and pT-descending within a type so the record is realistic.
    """
    fields = {}
    for field in ("Electrons", "Muons", "Jets", "BJets"):
        per_event = []
        for i, ev in enumerate(events):
            n = int(ev.get(field, 0))
            # descending pt, distinct across events and types
            per_event.append([100.0 + 10.0 * (n - k) + 0.25 * i for k in range(n)])
        fields[field] = ak.zip({"pt": ak.Array(per_event)})
    return ak.zip(fields, depth_limit=1)


def old_capped_grouping(obj_record):
    """The grouping this task replaced, reproduced here verbatim as the
    reference: label = physics_calcs.limit_particles_in_fs(raw_fs, 4).
    Yields (label, n_events_in_group)."""
    num_events = len(obj_record)
    zero_array = ak.Array([0] * num_events) if num_events > 0 else ak.Array([])
    particle_counts = ak.num(obj_record)
    e = getattr(particle_counts, "Electrons", zero_array)
    m = getattr(particle_counts, "Muons", zero_array)
    j = getattr(particle_counts, "Jets", zero_array)
    g = getattr(particle_counts, "Photons", zero_array)
    t = getattr(particle_counts, "Taus", zero_array)
    b = getattr(particle_counts, "BJets", zero_array)
    all_events_fs = np.array([
        f"{ee}e_{mm}m_{jj}j_{gg}g_{tt}t_{bb}b"
        for ee, mm, jj, gg, tt, bb in zip(e, m, j, g, t, b)
    ])
    out = {}
    for raw_fs in sorted(set(all_events_fs.tolist())):
        mask = (all_events_fs == raw_fs)
        label = physics_calcs.limit_particles_in_fs(raw_fs, 4)
        out[label] = out.get(label, 0) + int(mask.sum())
    return out


def old_split_by_first_empty_bin(im_array, bin_width, logger):
    """The pre-upstream-8120fb8 outlier split, copied verbatim from
    services/pipelines/post_processing_pipeline.py at commit f3d1d9b (this
    branch's own parent), as the reference the new aligned version is
    compared against. Not used anywhere in production -- test-only."""
    if len(im_array) == 0:
        return np.array([]), np.array([])
    min_mass = np.min(im_array)
    max_mass = np.max(im_array)
    nbins = math.ceil((max_mass - min_mass) / bin_width)
    if nbins == 0:
        return im_array, np.array([])
    bin_edges = np.linspace(min_mass, max_mass, nbins + 1)
    counts, _ = np.histogram(im_array, bins=bin_edges)
    first_empty_bin_idx = None
    for i in range(len(counts)):
        if counts[i] == 0:
            first_empty_bin_idx = i
            break
    if first_empty_bin_idx is None or first_empty_bin_idx <= 1:
        return im_array, np.array([])
    split_mass = bin_edges[first_empty_bin_idx]
    return im_array[im_array < split_mass], im_array[im_array >= split_mass]


def correct_parse_contains_combination(final_state: str, combination: dict) -> bool:
    """A deliberately CORRECT multi-digit reference implementation of
    physics_calcs.is_finalstate_contain_combination, used only to find out
    whether the shared single-digit version can ever disagree with it for a
    label this delivery path can produce. Not production code."""
    letter_to_particle = {"e": "Electrons", "m": "Muons", "j": "Jets",
                          "g": "Photons", "t": "Taus", "b": "BJets"}
    for token in final_state.split("_"):
        if len(token) < 2:
            continue
        digits, letter = token[:-1], token[-1]
        if not digits.isdigit():
            continue
        particle = letter_to_particle.get(letter)
        if particle is None or particle not in combination:
            continue
        value = combination[particle]
        if int(digits) < get_start(value) + get_count(value):
            return False
    return True


# --------------------------------------------------------------------------
# 1. B1 -- exact light-jet labels
# --------------------------------------------------------------------------

def test_exact_light_jet_labels():
    print("\n--- 1. B1: exact light-jet labels ---")
    jet_counts = [3, 4, 5, 6, 11]
    events = [{"Muons": 2, "Jets": n, "BJets": 1} for n in jet_counts]
    obj_record = make_obj_record(events)

    labels = [label for label, _ev, _mask in _group_by_final_state_with_mask(obj_record)]
    for n in jet_counts:
        expected = f"0e_2m_{n}j_0g_0t_1b"
        check(f"{n} light jets -> label {expected}", expected in labels,
              f"got labels {sorted(labels)}")

    check("exactly 5 distinct labels (one per multiplicity, none merged)",
          len(labels) == 5, f"got {len(labels)}: {sorted(labels)}")

    # What the OLD grouping did with the same input. NOTE: it merged 5 and 6
    # light jets into "4j", but it did NOT merge 11 -- see
    # test_old_capping_was_inconsistent below for why, and for the wider
    # consequence. So the old grouping gives 3 labels here, not 2.
    old = old_capped_grouping(obj_record)
    check("old grouping merged 5j and 6j into 4j (3 events under one 4j label)",
          old.get("0e_2m_4j_0g_0t_1b") == 3, f"old grouping = {old}")
    check("old grouping left 11j as its own label (the two-digit quirk)",
          old.get("0e_2m_11j_0g_0t_1b") == 1, f"old grouping = {old}")
    check("old grouping produced 3 labels where the new one produces 5",
          len(old) == 3, f"old labels = {sorted(old)}")

    # Name format: still exactly six <count><letter> fields, order e m j g t b.
    for label in labels:
        tokens = label.split("_")
        ok_format = (
            len(tokens) == 6
            and [tk[-1] for tk in tokens] == ["e", "m", "j", "g", "t", "b"]
            and all(tk[:-1].isdigit() for tk in tokens)
        )
        check(f"name format unchanged (six <count><letter> fields, e m j g t b): {label}",
              ok_format)

    check("two-digit counts render as two digits (11j, not 1j or 4j)",
          "0e_2m_11j_0g_0t_1b" in labels, f"got {sorted(labels)}")


# --------------------------------------------------------------------------
# 2. B1 -- event conservation
# --------------------------------------------------------------------------

def test_event_conservation():
    print("\n--- 2. B1: event conservation vs the old capped grouping ---")
    # A deliberately awkward mix: counts above and below the old cap of 4,
    # several events sharing a final state, several types above 4 at once,
    # two-digit jet counts, and an all-zero-but-one event.
    events = (
        [{"Muons": 2, "Jets": 0, "BJets": 0}] * 7
        + [{"Muons": 2, "Jets": 3, "BJets": 1}] * 5
        + [{"Muons": 2, "Jets": 4, "BJets": 1}] * 4
        + [{"Muons": 2, "Jets": 5, "BJets": 1}] * 3
        + [{"Muons": 2, "Jets": 6, "BJets": 1}] * 2
        + [{"Muons": 2, "Jets": 11, "BJets": 1}] * 1
        + [{"Muons": 5, "Jets": 7, "BJets": 2}] * 2
        + [{"Electrons": 1, "Muons": 1, "Jets": 12, "BJets": 6}] * 3
        + [{"Muons": 1}] * 1
    )
    obj_record = make_obj_record(events)
    n_input = len(events)

    new_groups = list(_group_by_final_state_with_mask(obj_record))
    new_total = sum(len(fs_events) for _label, fs_events, _mask in new_groups)
    old = old_capped_grouping(obj_record)
    old_total = sum(old.values())

    check(f"new grouping total events == input events ({n_input})",
          new_total == n_input, f"got {new_total}")
    check(f"old grouping total events == input events ({n_input})",
          old_total == n_input, f"got {old_total}")
    check("EVENT CONSERVATION: new total == old total",
          new_total == old_total, f"new={new_total} old={old_total}")

    # Masks must partition the input exactly once each: no event lost, none
    # counted twice.
    stacked = np.zeros(n_input, dtype=int)
    for _label, _fs_events, mask in new_groups:
        stacked += np.asarray(mask, dtype=int)
    check("every input event belongs to exactly one new label (masks partition)",
          bool(np.all(stacked == 1)), f"counts per event = {stacked.tolist()}")

    # Redistribution check (Step 3 check (b) in miniature): each OLD label's
    # event count must equal the sum of the NEW labels that the old capping
    # rule would have folded into it. Rather than guess which new labels
    # those are, each new label is run through the OLD capping function
    # itself -- that is exactly, by construction, the old label it used to
    # be filed under. This is correct for every case, including the
    # two-digit quirk documented below.
    def jet_count(label):
        return int(label.split("_")[2][:-1])

    new_counts = {}
    for label, fs_events, _mask in new_groups:
        new_counts[label] = new_counts.get(label, 0) + len(fs_events)

    folded = {}
    for label, n in new_counts.items():
        old_label = physics_calcs.limit_particles_in_fs(label, 4)
        folded.setdefault(old_label, []).append(label)

    check("every old label is reproduced by folding the new labels",
          set(folded) == set(old),
          f"folded={sorted(folded)} old={sorted(old)}")

    for old_label, old_n in sorted(old.items()):
        contributors = folded.get(old_label, [])
        matched = sum(new_counts[lb] for lb in contributors)
        check(f"old {old_label} ({old_n} events) == sum of new labels "
              f"{sorted(contributors)}",
              matched == old_n, f"got {matched}")

    # <=3 light jets must be completely untouched, label and count.
    for label, n in sorted(new_counts.items()):
        if jet_count(label) <= 3:
            check(f"final state with <=3 light jets unchanged: {label} ({n} events)",
                  old.get(label) == n, f"old had {old.get(label)}")


# --------------------------------------------------------------------------
# 2b. B1 -- what the OLD capping actually did (an unexpected finding)
# --------------------------------------------------------------------------

def test_old_capping_was_inconsistent():
    """Documents, by running it, an inconsistency in the grouping this task
    replaced -- found while writing these tests, not previously recorded.

    services.calculations.physics_calcs.limit_particles_in_fs reads only the
    FIRST character of each count field. For a two-digit count that first
    character is not the real count, so:

      - counts 5..9      WERE capped to 4  (merged into the 4j histograms)
      - counts 10..14,
        20..24, 30..34,
        40..44           were NOT capped at all (own separate final state!)
      - counts 50..99    were MANGLED: e.g. "99j" became "49j", "50j" -> "40j"

    So the old 1 Oct delivery did not consistently group high-multiplicity
    final states under 4j the way its own documentation described. The new
    exact-label grouping does not call limit_particles_in_fs at all, so none
    of this can affect the new delivery. Recorded here so the comparison
    against the 1 Oct numbers is interpreted correctly."""
    print("\n--- 2b. B1: the OLD capping was inconsistent (finding) ---")
    cap = physics_calcs.limit_particles_in_fs

    for n in (5, 6, 7, 8, 9):
        check(f"OLD: {n} light jets WAS capped to 4j",
              cap(f"0e_2m_{n}j_0g_0t_1b", 4) == "0e_2m_4j_0g_0t_1b")
    for n in (10, 11, 12, 13, 14, 20, 24, 40, 44):
        label = f"0e_2m_{n}j_0g_0t_1b"
        check(f"OLD: {n} light jets was NOT capped (kept its own label)",
              cap(label, 4) == label, f"got {cap(label, 4)}")
    check("OLD: 99 light jets was MANGLED to 49j",
          cap("0e_2m_99j_0g_0t_1b", 4) == "0e_2m_49j_0g_0t_1b",
          f"got {cap('0e_2m_99j_0g_0t_1b', 4)}")
    check("OLD: 50 light jets was MANGLED to 40j",
          cap("0e_2m_50j_0g_0t_1b", 4) == "0e_2m_40j_0g_0t_1b",
          f"got {cap('0e_2m_50j_0g_0t_1b', 4)}")

    # The new grouping has none of these problems: the label IS the count.
    jet_counts = [5, 9, 10, 14, 20, 50, 99]
    events = [{"Muons": 2, "Jets": n, "BJets": 1} for n in jet_counts]
    labels = [lb for lb, _e, _m in
              _group_by_final_state_with_mask(make_obj_record(events))]
    for n in jet_counts:
        check(f"NEW: {n} light jets -> exact label {n}j, no capping, no mangling",
              f"0e_2m_{n}j_0g_0t_1b" in labels, f"got {sorted(labels)}")


# --------------------------------------------------------------------------
# 3. B1 -- multi-digit label parsing on the delivery path
# --------------------------------------------------------------------------

def test_multidigit_label_parsing():
    print("\n--- 3. B1: multi-digit parsing of final-state labels ---")
    combos = get_all_combinations(
        object_types=OBJECT_TYPES,
        min_particles=MIN_PARTICLES_IN_COMBINATION,
        max_particles=MAX_PARTICLES_IN_COMBINATION,
        min_count=MIN_COUNT_PARTICLE_IN_COMBINATION,
        max_count=MAX_COUNT_PARTICLE_IN_COMBINATION,
        max_total_particles=MAX_TOTAL_PARTICLES_IN_COMBINATION,
        include_subleading=INCLUDE_SUBLEADING,
        max_subleading_index=MAX_SUBLEADING_INDEX,
    )
    check("the delivery path uses exactly 186 combinations", len(combos) == 186,
          f"got {len(combos)}")

    max_required = max(
        get_start(v) + get_count(v) for c in combos for v in c.values()
    )
    check("largest (start+count) requirement over all 186 combinations is 4",
          max_required == 4, f"got {max_required}")

    # Confirm the shared parser really is single-digit: for a two-digit
    # count it fails to map the letter and skips that type's requirement.
    # This is the documented shared-code limitation, demonstrated, not fixed.
    single_digit_blind = physics_calcs.is_finalstate_contain_combination(
        "0e_0m_11j_0g_0t_0b", {"Jets": (4, 0)}
    )
    check("shared parser returns True for 11 jets vs a 4-jet requirement "
          "(correct answer, reached by skipping the check)",
          single_digit_blind is True)

    # The real question: over every label this delivery can produce and all
    # 186 combinations, does the shared single-digit parser EVER disagree
    # with a correct multi-digit parse?
    disagreements = []
    labels_tested = 0
    for e in range(0, 5):
        for m in range(0, 6):
            for j in list(range(0, 13)) + [20, 99]:
                for b in range(0, 5):
                    label = f"{e}e_{m}m_{j}j_0g_0t_{b}b"
                    labels_tested += 1
                    for combo in combos:
                        got = physics_calcs.is_finalstate_contain_combination(label, combo)
                        want = correct_parse_contains_combination(label, combo)
                        if got != want:
                            disagreements.append((label, combo, got, want))
    check(f"shared single-digit parser agrees with a correct multi-digit parse "
          f"for all {labels_tested} labels x 186 combinations",
          not disagreements,
          f"{len(disagreements)} disagreements, first: {disagreements[:1]}")

    # And show WHY it is safe, so the result is not a coincidence nobody
    # understands: any count >= 10 exceeds every requirement anyway.
    check("any two-digit count (>=10) exceeds the largest requirement (4), "
          "so skipping the check and doing it correctly both give True",
          10 > max_required)

    # Guard for the future: if anyone ever raises the combination limits so
    # a requirement could exceed 9, this test must start failing loudly.
    check("GUARD: max requirement <= 9, so single-digit parsing stays safe; "
          "if this ever fails, the shared parser must be replaced study-locally",
          max_required <= 9, f"max requirement is {max_required}")


# --------------------------------------------------------------------------
# 4. B2 -- Z cut 115 -> 110
# --------------------------------------------------------------------------

def test_z_cut_110():
    print("\n--- 4. B2: Z-peak cut 115 -> 110 GeV ---")
    check("study constant Z_PEAK_CUTOFF is now 110.0", Z_PEAK_CUTOFF == 110.0,
          f"got {Z_PEAK_CUTOFF}")
    check("110 lands exactly on a 10 GeV bin edge",
          abs(110.0 / BIN_WIDTH_GEV - round(110.0 / BIN_WIDTH_GEV)) < 1e-12)
    check("115 did NOT land on a 10 GeV bin edge (the reason for the change)",
          abs(115.0 / BIN_WIDTH_GEV - round(115.0 / BIN_WIDTH_GEV)) > 1e-12)

    # A same-flavour dimuon signature: the IM part has two 'm' entries.
    dimuon_sig = "job_FS_0e_2m_1j_0g_0t_0b_IM_m0m1"
    values = np.array([80.0, 105.0, 109.999, 110.0, 112.5, 114.999, 115.0, 200.0])

    kept_110 = _apply_z_peak_cut(values, dimuon_sig, 110.0, LOGGER)
    kept_115 = _apply_z_peak_cut(values, dimuon_sig, 115.0, LOGGER)

    newly_kept = sorted(set(kept_110.tolist()) - set(kept_115.tolist()))
    check("dilepton: values in [110, 115) are now KEPT where 115 removed them",
          newly_kept == [110.0, 112.5, 114.999], f"got {newly_kept}")
    check("dilepton: nothing below 110 is kept",
          float(kept_110.min()) >= 110.0, f"min kept = {kept_110.min()}")
    check("dilepton: the 110 cut keeps a strict superset of what 115 kept",
          set(kept_115.tolist()).issubset(set(kept_110.tolist())))
    check("dilepton: 115 kept 2 values, 110 keeps 5",
          (len(kept_115), len(kept_110)) == (2, 5),
          f"got {(len(kept_115), len(kept_110))}")

    # Non-dilepton signatures must be untouched -- exactly as before.
    for sig, why in [
        ("job_FS_0e_1m_1j_0g_0t_0b_IM_m0j0", "one muon + one jet (no same-flavour pair)"),
        ("job_FS_1e_1m_0j_0g_0t_0b_IM_e0m0", "one electron + one muon (different flavours)"),
        ("job_FS_0e_0m_2j_0g_0t_0b_IM_j0j1", "two light jets (no leptons at all)"),
        ("job_FS_0e_0m_0j_0g_0t_2b_IM_b0b1", "two b-jets"),
    ]:
        out110 = _apply_z_peak_cut(values, sig, 110.0, LOGGER)
        out115 = _apply_z_peak_cut(values, sig, 115.0, LOGGER)
        check(f"non-dilepton untouched by either cutoff: {why}",
              np.array_equal(out110, values) and np.array_equal(out115, values),
              f"110 -> {out110.tolist()}, 115 -> {out115.tolist()}")

    # Same-flavour dielectron must behave like dimuon.
    ee_sig = "job_FS_2e_0m_1j_0g_0t_0b_IM_e0e1"
    ee110 = _apply_z_peak_cut(values, ee_sig, 110.0, LOGGER)
    check("same-flavour dielectron is cut too, at 110",
          float(ee110.min()) >= 110.0 and len(ee110) == 5,
          f"got {ee110.tolist()}")

    # Multi-digit FS part must not confuse the dilepton test (it reads the
    # IM part only) -- relevant now that labels can carry 11j.
    big_j_sig = "job_FS_0e_2m_11j_0g_0t_1b_IM_m0m1"
    big = _apply_z_peak_cut(values, big_j_sig, 110.0, LOGGER)
    check("dilepton detection still works with a two-digit jet count in the label",
          np.array_equal(big, _apply_z_peak_cut(values, dimuon_sig, 110.0, LOGGER)))


# --------------------------------------------------------------------------
# 5. B3 -- aligned outlier split
# --------------------------------------------------------------------------

def test_aligned_outlier_split():
    print("\n--- 5. B3: outlier split aligned to the fixed 10 GeV grid ---")
    # An array where the OLD and NEW splits genuinely DISAGREE.
    #   - a dense main block, 103..138 GeV in 1 GeV steps (36 values)
    #   - a real empty gap over 139..149
    #   - a small secondary cluster, 150..154 (5 values)
    #   - one far outlier at 512 GeV
    # The data minimum (103) is deliberately NOT on a 10 GeV edge, which is
    # exactly the situation where the old min-to-max grid drifts away from
    # the histogram grid.
    main_block = np.arange(103.0, 139.0, 1.0)      # 103 .. 138, 36 values
    secondary = np.arange(150.0, 155.0, 1.0)       # 150 .. 154, 5 values
    outlier = np.array([512.0])
    arr = np.concatenate([main_block, secondary, outlier])
    check("test array is as described (42 values)", len(arr) == 42, f"got {len(arr)}")

    new_main, new_out = _split_by_first_empty_bin(arr, BIN_WIDTH_GEV, LOGGER)
    old_main, old_out = old_split_by_first_empty_bin(arr, BIN_WIDTH_GEV, LOGGER)

    # --- the headline: they differ ---
    check("OLD and NEW outlier split give DIFFERENT results on this array",
          len(new_main) != len(old_main),
          f"old main={len(old_main)} new main={len(new_main)}")
    print(f"       OLD: n_main={len(old_main)} n_outliers={len(old_out)} "
          f"last kept={float(old_main.max()) if len(old_main) else None}")
    print(f"       NEW: n_main={len(new_main)} n_outliers={len(new_out)} "
          f"last kept={float(new_main.max()) if len(new_main) else None}")

    # --- where each one cut ---
    # NEW: aligned grid is multiples of 10 from 0, so bins are
    # [100,110) [110,120) [120,130) [130,140) [140,150) ...
    # [140,150) is the first empty bin -> split at 140.0, a grid edge.
    aligned_edges = np.arange(
        math.floor(float(arr.min()) / BIN_WIDTH_GEV) * BIN_WIDTH_GEV,
        math.ceil(float(arr.max()) / BIN_WIDTH_GEV) * BIN_WIDTH_GEV + BIN_WIDTH_GEV,
        BIN_WIDTH_GEV,
    )
    counts, _ = np.histogram(arr, bins=aligned_edges)
    first_empty = next(i for i, c in enumerate(counts) if c == 0)
    new_split_mass = float(aligned_edges[first_empty])

    check("NEW grid starts at 100.0 (a multiple of 10), not at the data "
          "minimum 103.0",
          float(aligned_edges[0]) == 100.0, f"first edge = {aligned_edges[0]}")
    check("NEW grid bins are exactly 10 GeV wide",
          bool(np.allclose(np.diff(aligned_edges), BIN_WIDTH_GEV)))
    check("NEW split mass is 140.0 GeV", new_split_mass == 140.0,
          f"got {new_split_mass}")
    check("NEW split mass lands EXACTLY on a 10 GeV bin edge",
          abs(new_split_mass / BIN_WIDTH_GEV
              - round(new_split_mass / BIN_WIDTH_GEV)) < 1e-12,
          f"got {new_split_mass}")
    check("NEW keeps the 36 main-block values and calls the rest outliers "
          "(5 secondary + 1 far) = 6",
          len(new_main) == 36 and len(new_out) == 6,
          f"got main={len(new_main)} out={len(new_out)}")

    # OLD: min-to-max linspace -> 41 bins of 9.9756 GeV, offset from the grid.
    old_min, old_max = float(arr.min()), float(arr.max())
    old_nbins = math.ceil((old_max - old_min) / BIN_WIDTH_GEV)
    old_edges = np.linspace(old_min, old_max, old_nbins + 1)
    old_counts, _ = np.histogram(arr, bins=old_edges)
    old_first_empty = next(i for i, c in enumerate(old_counts) if c == 0)
    old_split_mass = float(old_edges[old_first_empty])

    check("OLD grid bins were NOT 10 GeV wide",
          abs(float(old_edges[1] - old_edges[0]) - BIN_WIDTH_GEV) > 1e-9,
          f"old width = {float(old_edges[1] - old_edges[0]):.4f} GeV")
    check("OLD split mass was NOT on a 10 GeV bin edge",
          abs(old_split_mass / BIN_WIDTH_GEV
              - round(old_split_mass / BIN_WIDTH_GEV)) > 1e-9,
          f"got {old_split_mass:.4f}")
    check("OLD missed the 139-149 GeV gap entirely and kept the secondary "
          "cluster in the main array (41 values, 1 outlier)",
          len(old_main) == 41 and len(old_out) == 1,
          f"got main={len(old_main)} out={len(old_out)}")
    print(f"       OLD split mass = {old_split_mass:.4f} GeV (off-grid), "
          f"old bin width = {float(old_edges[1] - old_edges[0]):.4f} GeV")
    print(f"       NEW split mass = {new_split_mass:.1f} GeV (on-grid), "
          f"new bin width = {BIN_WIDTH_GEV:.1f} GeV")

    # --- degenerate inputs must not crash ---
    empty_main, empty_out = _split_by_first_empty_bin(
        np.array([]), BIN_WIDTH_GEV, LOGGER)
    check("empty array returns two empty arrays without crashing",
          len(empty_main) == 0 and len(empty_out) == 0)
    single_main, single_out = _split_by_first_empty_bin(
        np.array([123.0]), BIN_WIDTH_GEV, LOGGER)
    check("single-value array keeps its one value, no outliers",
          len(single_main) == 1 and len(single_out) == 0,
          f"got main={single_main.tolist()} out={single_out.tolist()}")
    flat_main, flat_out = _split_by_first_empty_bin(
        np.full(50, 200.0), BIN_WIDTH_GEV, LOGGER)
    check("50 identical values keep all 50, no outliers, no crash",
          len(flat_main) == 50 and len(flat_out) == 0,
          f"got main={len(flat_main)} out={len(flat_out)}")


def main():
    print("=" * 74)
    print("exact-jet-labels task (B1-B4): self-checks")
    print("=" * 74)
    test_exact_light_jet_labels()
    test_event_conservation()
    test_old_capping_was_inconsistent()
    test_multidigit_label_parsing()
    test_z_cut_110()
    test_aligned_outlier_split()

    print("\n" + "=" * 74)
    if FAILURES:
        print(f"{len(FAILURES)} CHECK(S) FAILED:")
        for name in FAILURES:
            print(f"  - {name}")
        sys.exit(1)
    print("ALL CHECKS PASSED")


if __name__ == "__main__":
    main()
