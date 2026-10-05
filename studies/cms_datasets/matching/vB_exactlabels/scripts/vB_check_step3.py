"""
exact-jet-labels task, Step 3: pilot validation on the 4 pilot files.

Compares the NEW pilot run (pinned commit 2666684, exact light-jet labels +
Z 110 + aligned outlier split) against the EXISTING 1 Oct rare4 pilot run
(commit 52bea52), which is opened strictly READ-ONLY
(`mode=ro&immutable=1`, Hard Rule 4 -- nothing under output/ is ever
modified).

Checks, all of which must pass before production is submitted:

  (a) Selection unchanged: n_after_gate, n_exclusive and the rare4
      rejected-event totals are identical, file by file.
  (b) Label redistribution only: each OLD final state's event count equals
      the sum of the NEW final states that the OLD capping rule would have
      folded into it; every final state with <=3 light jets has an
      identical event count.
  (c) For final states with <=3 light jets, the RAW (pre-post-processing)
      mass arrays are identical, signature by signature.
  (d) Post-processing differences appear only where expected -- the
      dilepton Z-cut window 110-115 GeV and the outlier-split boundary --
      with one concrete example of each.

Run from the pinned checkout:
    /storage/agrp/berkom/atlas-utilization/envs/atlas-pipeline/bin/python \
      studies/cms_datasets/matching/vB_exactlabels/scripts/vB_check_step3.py
"""
from __future__ import annotations

import json
import logging
import math
import sqlite3
import sys
from collections import Counter, defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(REPO_ROOT))

import numpy as np  # noqa: E402

from services.calculations import physics_calcs  # noqa: E402
from services.pipelines.post_processing_pipeline import (  # noqa: E402
    _apply_z_peak_cut,
    _dilepton_flavor,
    _find_rightmost_highest_peak,
    _split_by_first_empty_bin,
)
from services.storage.sqlite_shards import _deserialize_array  # noqa: E402
from studies.cms_coverage.cluster.merge_and_count import SIG_PATTERN  # noqa: E402

LOGGER = logging.getLogger("vB_check_step3")
logging.basicConfig(level=logging.WARNING)

OUT = Path("/storage/agrp/berkom/atlas-utilization/output/cms_datasets")
OLD_BASE = OUT / "rare4_pilot"
NEW_BASE = OUT / "vB_exactlabels_pilot"

RUNS = [
    "DoubleMuon_30522_0_matched",
    "DoubleMuon_30555_0_matched",
    "SingleMuon_30530_0_matched",
    "SingleMuon_30563_0_matched",
]

BIN_WIDTH_GEV = 10.0
MAX_MASS_CUTOFF = 10000.0
Z_OLD = 115.0
Z_NEW = 110.0

FAILURES = []
RESULTS = {}


def check(name, condition, detail=""):
    """Prints `detail` only on failure, so a PASS line can never be misread as
    carrying a contradictory explanation."""
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {name}" + (f" -- {detail}" if detail and not condition else ""))
    if not condition:
        FAILURES.append(name)
    return bool(condition)


def read_ro(path: Path):
    """Read every (signature -> concatenated float array) from a shard,
    strictly read-only. Never writes, never creates -wal/-shm files."""
    con = sqlite3.connect(f"file:{path}?mode=ro&immutable=1", uri=True)
    cur = con.cursor()
    cur.execute("SELECT signature, payload FROM array_chunks")
    out = defaultdict(list)
    for signature, payload in cur.fetchall():
        if signature.startswith("CAPPED::"):
            continue
        out[signature].extend(_deserialize_array(payload).tolist())
    con.close()
    return dict(out)


def meta(base: Path, run: str) -> dict:
    return json.loads((base / run / "job_metadata.json").read_text())


def label_of(signature: str):
    m = SIG_PATTERN.search(signature)
    return (m.group(1), m.group(2)) if m else (None, None)


def jet_count(label: str) -> int:
    return int(label.split("_")[2][:-1])


def old_split_by_first_empty_bin(im_array, bin_width):
    """The pre-8120fb8 split, verbatim, as the reference."""
    if len(im_array) == 0:
        return np.array([]), np.array([])
    lo, hi = np.min(im_array), np.max(im_array)
    nbins = math.ceil((hi - lo) / bin_width)
    if nbins == 0:
        return im_array, np.array([])
    edges = np.linspace(lo, hi, nbins + 1)
    counts, _ = np.histogram(im_array, bins=edges)
    first_empty = None
    for i in range(len(counts)):
        if counts[i] == 0:
            first_empty = i
            break
    if first_empty is None or first_empty <= 1:
        return im_array, np.array([])
    split = edges[first_empty]
    return im_array[im_array < split], im_array[im_array >= split]


def chain(raw, im_str, z_cutoff, use_new_split):
    """The real post-processing chain, with the Z cutoff and the split
    implementation selectable so old and new can be compared on identical
    input. Peak detection is byte-identical in both (upstream 8120fb8 only
    factored its already-aligned grid into a helper), so the same real
    function is used for both.

    Returns a dict with the resulting main array AND the three boundaries
    that produced it, so check (d) can verify that the main array is
    nothing more than the raw array cut at those boundaries -- i.e. that
    every old-vs-new difference is a boundary move and nothing else."""
    fake_sig = f"x_FS_x_IM_{im_str}"
    raw = np.asarray(raw, dtype=np.float64)
    dilepton = _dilepton_flavor(fake_sig)
    arr = _apply_z_peak_cut(raw, fake_sig, z_cutoff, LOGGER)
    z_floor = z_cutoff if (dilepton and z_cutoff > 0) else None
    arr = arr[arr <= MAX_MASS_CUTOFF]
    out = {"main": np.array([]), "z_floor": z_floor, "peak": None, "split": None,
           "dilepton": dilepton}
    if arr.size == 0:
        return out
    peak = _find_rightmost_highest_peak(arr, BIN_WIDTH_GEV, LOGGER)
    out["peak"] = None if peak is None else float(peak)
    filtered = arr if peak is None else arr[arr >= peak]
    if filtered.size == 0:
        return out
    if use_new_split:
        main, outliers = _split_by_first_empty_bin(filtered, BIN_WIDTH_GEV, LOGGER)
    else:
        main, outliers = old_split_by_first_empty_bin(filtered, BIN_WIDTH_GEV)
    out["main"] = main
    out["split"] = float(np.min(outliers)) if len(outliers) else None
    return out


def reconstruct_from_boundaries(raw, res):
    """The raw array cut at exactly the boundaries `chain` reported. If this
    reproduces `chain`'s own main array, then the main array is fully
    determined by (Z floor, peak mass, split mass) -- so any old-vs-new
    difference must be a move of one of those three boundaries, and cannot be
    anything else (no altered values, no lost or duplicated events)."""
    raw = np.asarray(raw, dtype=np.float64)
    keep = raw <= MAX_MASS_CUTOFF
    if res["z_floor"] is not None:
        keep &= raw >= res["z_floor"]
    if res["peak"] is not None:
        keep &= raw >= res["peak"]
    if res["split"] is not None:
        keep &= raw < res["split"]
    return raw[keep]


# ==========================================================================
# (a) Selection unchanged
# ==========================================================================

def check_a():
    print("\n" + "=" * 74)
    print("(a) Selection unchanged: n_after_gate, n_exclusive, rare4 rejected")
    print("=" * 74)
    rows = []
    for run in RUNS:
        o, n = meta(OLD_BASE, run), meta(NEW_BASE, run)
        o_rej = o["rare4_diagnostics"]["n_rejected_gt4_lepton_bjet"]
        n_rej = n["rare4_diagnostics"]["n_rejected_gt4_lepton_bjet"]
        ok = (
            o["n_read"] == n["n_read"]
            and o["n_after_golden_json"] == n["n_after_golden_json"]
            and o["n_after_trigger"] == n["n_after_trigger"]
            and o["n_after_gate"] == n["n_after_gate"]
            and o["n_exclusive"] == n["n_exclusive"]
            and o_rej == n_rej
            and o["rare4_diagnostics"]["n_accepted_events_before_rare4_rule"]
                == n["rare4_diagnostics"]["n_accepted_events_before_rare4_rule"]
            and o["rare4_diagnostics"]["n_kept_le4_lepton_bjet"]
                == n["rare4_diagnostics"]["n_kept_le4_lepton_bjet"]
            and o["rare4_diagnostics"]["rejected_N_distribution"]
                == n["rare4_diagnostics"]["rejected_N_distribution"]
            and o["rare4_diagnostics"]["n_hidden_cases"]
                == n["rare4_diagnostics"]["n_hidden_cases"]
        )
        check(f"{run}: n_read / golden / trigger / gate / exclusive / rare4-rejected identical",
              ok,
              f"old=({o['n_read']},{o['n_after_golden_json']},{o['n_after_trigger']},"
              f"{o['n_after_gate']},{o['n_exclusive']},{o_rej}) "
              f"new=({n['n_read']},{n['n_after_golden_json']},{n['n_after_trigger']},"
              f"{n['n_after_gate']},{n['n_exclusive']},{n_rej})")
        rows.append({
            "run": run, "n_read": n["n_read"], "n_after_gate": n["n_after_gate"],
            "n_exclusive": n["n_exclusive"], "rare4_rejected": n_rej,
            "identical_to_1oct": ok,
            "n_hidden_cases": n["rare4_diagnostics"]["n_hidden_cases"],
            "old_n_fs_groups_normal": o["n_final_state_groups"],
            "new_n_fs_groups_normal": n["n_final_state_groups"],
            "old_n_fs_groups_rare4": o["rare4_diagnostics"]["n_fs_groups"],
            "new_n_fs_groups_rare4": n["rare4_diagnostics"]["n_fs_groups"],
        })
        print(f"       final-state groups (normal): old={o['n_final_state_groups']} "
              f"new={n['n_final_state_groups']}")
        print(f"       final-state groups (rare4):  "
              f"old={o['rare4_diagnostics']['n_fs_groups']} "
              f"new={n['rare4_diagnostics']['n_fs_groups']}")
    RESULTS["check_a"] = rows


# ==========================================================================
# (b) Label redistribution only
# ==========================================================================

def check_b():
    print("\n" + "=" * 74)
    print("(b) Label redistribution only")
    print("=" * 74)
    summary = []
    for run in RUNS:
        o, n = meta(OLD_BASE, run), meta(NEW_BASE, run)
        # BOTH the delivered Version B (rare4) label counts AND the normal
        # version's, since _group_by_final_state_with_mask is shared by every
        # version the driver writes. rare4 is the one that gets delivered;
        # normal is checked too so nothing silently changed there either.
        sources = [
            ("rare4", lambda md, w: md["rare4_diagnostics"][
                f"final_state_label_event_counts_{w}"]),
            ("normal", lambda md, w: md[f"final_state_label_event_counts_{w}"]),
        ]
        for version, get in sources:
            for which_raw in ("inclusive", "exclusive"):
              old_counts = get(o, which_raw)
              new_counts = get(n, which_raw)
              which = f"{version}/{which_raw}"

              check(f"{run}/{which}: total events over all labels identical",
                    sum(old_counts.values()) == sum(new_counts.values()),
                    f"old={sum(old_counts.values())} new={sum(new_counts.values())}")

              # Fold each NEW label through the OLD capping rule: that is, by
              # construction, the OLD label it used to be filed under.
              folded = defaultdict(int)
              contributors = defaultdict(list)
              for label, cnt in new_counts.items():
                  old_label = physics_calcs.limit_particles_in_fs(label, 4)
                  folded[old_label] += cnt
                  contributors[old_label].append(label)

              check(f"{run}/{which}: folded NEW labels reproduce the OLD label set exactly",
                    set(folded) == set(old_counts),
                    f"only_folded={sorted(set(folded)-set(old_counts))[:4]} "
                    f"only_old={sorted(set(old_counts)-set(folded))[:4]}")

              mismatches = [(lb, old_counts[lb], folded.get(lb, 0))
                            for lb in old_counts if old_counts[lb] != folded.get(lb, 0)]
              check(f"{run}/{which}: every OLD label's count == sum of the NEW labels "
                    f"folding into it ({len(old_counts)} labels)",
                    not mismatches, f"mismatches: {mismatches[:4]}")

              # Final states with <=3 light jets must be completely untouched --
              # same label, same count. The comparison is restricted to labels
              # the OLD capping rule would have left alone
              # (limit_particles_in_fs(label, 4) == label): a label whose
              # NON-jet counts exceeded 4 had a different name under the old
              # rule, so there is no same-named old entry to compare against.
              # For the DELIVERED rare4 version this excludes nothing at all,
              # because Version B rejects any event with electrons+muons+
              # b-jets > 4, so no non-jet count can exceed 4. It can exclude
              # labels in the NORMAL version, which keeps every object -- those
              # are counted and reported separately just below.
              le3 = [lb for lb in new_counts if jet_count(lb) <= 3]
              le3_same_name = [lb for lb in le3
                               if physics_calcs.limit_particles_in_fs(lb, 4) == lb]
              le3_renamed = [lb for lb in le3 if lb not in set(le3_same_name)]
              le3_bad = [(lb, old_counts.get(lb), new_counts.get(lb))
                         for lb in le3_same_name
                         if old_counts.get(lb) != new_counts.get(lb)]
              check(f"{run}/{which}: all {len(le3_same_name)} final states with <=3 "
                    f"light jets and no non-jet count above 4 have identical "
                    f"event counts",
                    not le3_bad, f"differing: {le3_bad[:4]}")
              if version == "rare4":
                  check(f"{run}/{which}: rare4 has NO <=3-light-jet label with a "
                        f"non-jet count above 4 (guaranteed by the Version B rule)",
                        not le3_renamed, f"found: {sorted(le3_renamed)[:4]}")
              elif le3_renamed:
                  print(f"       note [{version}]: {len(le3_renamed)} <=3-light-jet "
                        f"label(s) have a non-jet count above 4, so they were "
                        f"renamed by the old rule, e.g. "
                        f"{sorted(le3_renamed)[:3]} -- expected for the normal "
                        f"version, which is not delivered")

              split_labels = {ol: sorted(c) for ol, c in contributors.items() if len(c) > 1}
              if which.endswith("/inclusive"):
                  print(f"       {run} [{version}]: {len(old_counts)} old labels -> "
                        f"{len(new_counts)} new labels; "
                        f"{len(split_labels)} old labels split into several")
                  for ol, cs in sorted(split_labels.items())[:3]:
                      print(f"         e.g. {ol} ({old_counts[ol]} events) -> "
                            + ", ".join(f"{c}:{new_counts[c]}" for c in cs))
              summary.append({
                  "run": run, "version": version, "which": which,
                  "n_old_labels": len(old_counts), "n_new_labels": len(new_counts),
                  "n_old_labels_that_split": len(split_labels),
                  "total_events": sum(new_counts.values()),
              })
    RESULTS["check_b"] = summary


# ==========================================================================
# (c) Raw arrays identical for <=3 light jets
# ==========================================================================

def check_c():
    print("\n" + "=" * 74)
    print("(c) RAW mass arrays identical for final states with <=3 light jets")
    print("=" * 74)
    totals = []
    for run in RUNS:
        for shard in ("dataset_shard_rare4_inclusive.sqlite",
                      "dataset_shard_rare4_exclusive.sqlite"):
            old = read_ro(OLD_BASE / run / shard)
            new = read_ro(NEW_BASE / run / shard)

            old_le3 = {s: v for s, v in old.items()
                       if label_of(s)[0] and jet_count(label_of(s)[0]) <= 3}
            new_le3 = {s: v for s, v in new.items()
                       if label_of(s)[0] and jet_count(label_of(s)[0]) <= 3}

            check(f"{run}/{shard.split('_')[-1][:-7]}: same <=3-light-jet signature set "
                  f"({len(old_le3)} signatures)",
                  set(old_le3) == set(new_le3),
                  f"only_old={len(set(old_le3)-set(new_le3))} "
                  f"only_new={len(set(new_le3)-set(old_le3))}")

            bad = []
            for sig in sorted(set(old_le3) & set(new_le3)):
                if Counter(np.round(old_le3[sig], 5)) != Counter(np.round(new_le3[sig], 5)):
                    bad.append(sig)
            check(f"{run}/{shard.split('_')[-1][:-7]}: all "
                  f"{len(set(old_le3) & set(new_le3))} <=3-light-jet raw arrays identical",
                  not bad, f"{len(bad)} differ, first: {bad[:2]}")
            totals.append({"run": run, "shard": shard,
                           "n_le3_signatures": len(old_le3), "n_differing": len(bad)})
    RESULTS["check_c"] = totals


# ==========================================================================
# (d) Post-processing differences only where expected
# ==========================================================================

def check_d():
    print("\n" + "=" * 74)
    print("(d) Post-processing differences only where expected")
    print("=" * 74)
    # Use the <=3-light-jet signatures only: check (c) proved their raw
    # arrays are identical, so every difference seen here is caused purely
    # by the post-processing change, not by relabelling.
    pooled = defaultdict(list)
    im_by_sig = {}
    for run in RUNS:
        new = read_ro(NEW_BASE / run / "dataset_shard_rare4_inclusive.sqlite")
        for sig, vals in new.items():
            fs, im = label_of(sig)
            if fs is None or jet_count(fs) > 3:
                continue
            pooled[(fs, im)].extend(vals)
            im_by_sig[(fs, im)] = im

    n_same = 0
    recon_fail = []
    z_only = []
    peak_moved = []
    split_moved = []
    unexplained = []

    for key, vals in pooled.items():
        fs, im = key
        raw = np.asarray(vals, dtype=np.float64)
        old_res = chain(raw, im, Z_OLD, use_new_split=False)
        new_res = chain(raw, im, Z_NEW, use_new_split=True)
        old_main, new_main = old_res["main"], new_res["main"]

        # First, the strong structural statement: each side's histogram is
        # EXACTLY the raw array cut at its own three boundaries. If this holds
        # for both, then the only possible cause of any difference is a
        # boundary move -- nothing in the data itself changed.
        for tag, res in (("old", old_res), ("new", new_res)):
            got = Counter(np.round(res["main"], 5))
            want = Counter(np.round(reconstruct_from_boundaries(raw, res), 5))
            if got != want:
                recon_fail.append({"final_state": fs, "combination": im, "side": tag,
                                   "n_got": int(res["main"].size),
                                   "n_want": int(len(list(want.elements())))})

        if Counter(np.round(old_main, 5)) == Counter(np.round(new_main, 5)):
            n_same += 1
            continue

        z_changed = old_res["z_floor"] != new_res["z_floor"]
        peak_changed = old_res["peak"] != new_res["peak"]
        split_changed = old_res["split"] != new_res["split"]
        new_split_on_grid = (
            new_res["split"] is None
            or abs(new_res["split"] / BIN_WIDTH_GEV
                   - round(new_res["split"] / BIN_WIDTH_GEV)) < 1e-9
        )

        added = Counter(np.round(new_main, 5)) - Counter(np.round(old_main, 5))
        removed = Counter(np.round(old_main, 5)) - Counter(np.round(new_main, 5))
        added_vals = np.array(list(added.elements())) if added else np.array([])
        removed_vals = np.array(list(removed.elements())) if removed else np.array([])

        rec = {
            "final_state": fs, "combination": im, "n_raw": int(raw.size),
            "dilepton": bool(new_res["dilepton"]),
            "n_old_main": int(old_main.size), "n_new_main": int(new_main.size),
            "n_added": int(len(added_vals)), "n_removed": int(len(removed_vals)),
            "added_min": float(added_vals.min()) if len(added_vals) else None,
            "added_max": float(added_vals.max()) if len(added_vals) else None,
            "removed_min": float(removed_vals.min()) if len(removed_vals) else None,
            "removed_max": float(removed_vals.max()) if len(removed_vals) else None,
            "old_z_floor": old_res["z_floor"], "new_z_floor": new_res["z_floor"],
            "old_peak": old_res["peak"], "new_peak": new_res["peak"],
            "old_split": old_res["split"], "new_split": new_res["split"],
            "new_split_on_10gev_grid": new_split_on_grid,
            "which_boundaries_moved": [
                nm for nm, ch in (("z_cut", z_changed), ("peak", peak_changed),
                                  ("split", split_changed)) if ch],
        }

        if not (z_changed or peak_changed or split_changed):
            # Should be impossible: identical boundaries but different output.
            unexplained.append(rec)
        elif split_changed and not new_split_on_grid:
            unexplained.append(rec)
        elif split_changed:
            split_moved.append(rec)
        elif peak_changed:
            peak_moved.append(rec)
        else:
            z_only.append(rec)

    n_changed = len(z_only) + len(peak_moved) + len(split_moved) + len(unexplained)
    print(f"       {len(pooled)} pooled <=3-light-jet (final state, combination) channels")
    print(f"       unchanged by the post-processing change:       {n_same}")
    print(f"       changed, Z cut boundary only:                  {len(z_only)}")
    print(f"       changed, peak boundary moved (Z cut knock-on): {len(peak_moved)}")
    print(f"       changed, outlier-split boundary moved:         {len(split_moved)}")
    print(f"       changed for an UNEXPLAINED reason:             {len(unexplained)}")

    check("each side's histogram is EXACTLY the raw array cut at its own "
          "(Z floor, peak, split) boundaries, so no difference can come from "
          "anything but a boundary move",
          not recon_fail,
          f"{len(recon_fail)} reconstruction failures, first: {recon_fail[:2]}")
    check("every post-processing difference is a move of the Z cut, the peak "
          "boundary or the outlier split -- nothing else",
          not unexplained,
          f"{len(unexplained)} unexplained, first: {unexplained[:2]}")
    check("every moved outlier-split boundary lands on a 10 GeV grid edge",
          all(r["new_split_on_10gev_grid"] for r in split_moved + peak_moved + z_only))

    # Every channel whose Z floor or peak moved must be a same-flavour
    # dilepton channel: those are the only ones _apply_z_peak_cut touches.
    non_dilepton_z = [r for r in z_only + peak_moved if not r["dilepton"]]
    check("only same-flavour dilepton channels changed via the Z cut or the "
          "peak boundary (non-dilepton channels are untouched by the Z cut)",
          not non_dilepton_z, f"found: {non_dilepton_z[:2]}")

    # Everything newly admitted by a Z-cut or peak move must sit at or above
    # the new Z floor of 110 GeV and below the old boundary it was excluded by.
    bad_added = [r for r in z_only + peak_moved
                 if r["added_min"] is not None and r["added_min"] < Z_NEW]
    check(f"every value newly admitted by the Z cut or peak move sits at or "
          f"above {Z_NEW:.0f} GeV",
          not bad_added, f"found: {bad_added[:2]}")

    check("at least one concrete Z-cut example exists",
          len(z_only) + len(peak_moved) > 0)
    check("at least one concrete moved-split example exists", len(split_moved) > 0)

    z_examples = z_only + peak_moved
    if z_examples:
        ex = max(z_examples, key=lambda r: r["n_added"])
        print("\n       EXAMPLE 1 -- Z cut 115 -> 110 (same-flavour dilepton):")
        print(f"         final state {ex['final_state']}, combination {ex['combination']}")
        print(f"         Z floor {ex['old_z_floor']} -> {ex['new_z_floor']} GeV; "
              f"peak {ex['old_peak']} -> {ex['new_peak']} GeV")
        print(f"         {ex['n_added']} values in "
              f"[{ex['added_min']:.2f}, {ex['added_max']:.2f}] GeV are now KEPT, "
              f"{ex['n_removed']} removed")
        print(f"         histogram entries {ex['n_old_main']:,} -> {ex['n_new_main']:,}")
    if split_moved:
        ex = max(split_moved, key=lambda r: abs(r["n_new_main"] - r["n_old_main"]))
        print("\n       EXAMPLE 2 -- outlier split boundary moved onto a 10 GeV edge:")
        print(f"         final state {ex['final_state']}, combination {ex['combination']}")
        print(f"         split mass {ex['old_split']} -> {ex['new_split']} GeV "
              f"(None = no split, everything kept)")
        print(f"         histogram entries {ex['n_old_main']:,} -> {ex['n_new_main']:,}")

    RESULTS["check_d"] = {
        "n_channels": len(pooled), "n_unchanged": n_same, "n_changed": n_changed,
        "n_z_cut_only": len(z_only), "n_peak_moved": len(peak_moved),
        "n_split_moved": len(split_moved), "n_unexplained": len(unexplained),
        "n_reconstruction_failures": len(recon_fail),
        "example_z_cut": (max(z_only + peak_moved, key=lambda r: r["n_added"])
                          if (z_only + peak_moved) else None),
        "example_split_moved": (max(split_moved,
                                    key=lambda r: abs(r["n_new_main"] - r["n_old_main"]))
                                if split_moved else None),
        "all_z_cut_examples": (z_only + peak_moved)[:80],
        "all_split_moved_examples": split_moved[:80],
        "all_unexplained": unexplained[:80],
    }


def main():
    print("=" * 74)
    print("exact-jet-labels task, Step 3: pilot validation")
    print(f"  NEW: {NEW_BASE}")
    print(f"  OLD (read-only): {OLD_BASE}")
    print("=" * 74)
    for run in RUNS:
        new_commit = meta(NEW_BASE, run)["git_commit"]
        check(f"{run}: new run was produced by the pinned commit 2666684",
              new_commit.startswith("2666684"), f"got {new_commit}")

    check_a()
    check_b()
    check_c()
    check_d()

    out_path = NEW_BASE / "step3_validation.json"
    out_path.write_text(json.dumps(
        {"failures": FAILURES, "results": RESULTS}, indent=2, default=str))
    print(f"\nwrote {out_path}")

    print("\n" + "=" * 74)
    if FAILURES:
        print(f"{len(FAILURES)} CHECK(S) FAILED -- DO NOT SUBMIT PRODUCTION:")
        for f in FAILURES:
            print(f"  - {f}")
        sys.exit(1)
    print("ALL STEP 3 CHECKS PASSED -- production may be submitted")


if __name__ == "__main__":
    main()
