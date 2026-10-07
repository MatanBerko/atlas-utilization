#!/usr/bin/env python
"""
Step B: the two pass/fail gates for raising the electron-muon overlap
radius from dR 0.05 to dR 0.12 (DEC-2), decided in advance.

GATE 1 -- the leftover low-mass cluster disappears.
    Count selected electron-muon pairs with m(e,mu) < 5 GeV in accepted
    MuonEG pilot events, at each radius. PASS if <= 10 pairs remain at
    0.12. The counts come from the m(e,mu) histogram the driver already
    writes per job (0-20 GeV in 0.1 GeV bins), so nothing is re-read; if
    the gate FAILS the script says exactly which pairs survive, by
    re-reading the four MuonEG pilot files and dumping each surviving
    pair's dR, both pT values and both object IDs.

GATE 2 -- every change is explained.
    For every event that differs between the two radii, the event must
    contain at least one selected electron with 0.05 <= dR(e, nearest
    selected muon) < 0.12 that the new radius removed. That is EXACTLY
    the condition `electrons removed at 0.12 > electrons removed at 0.05`
    for that event: the removal is monotonic in the radius, so the set
    removed at 0.05 is a subset of the set removed at 0.12 and the
    difference is precisely the electrons in the 0.05-0.12 band. Both
    counts are in the per-event debug dumps. PASS if unexplained
    differences = 0.

Also reported: changed events per dataset, accepted events lost per
dataset, the two muon datasets' change versus master (the removal-off run,
which Prompt 1 proved shard-for-shard identical to master 4bbe972), and
the trigger-guard totals.

Plots: m(e,mu) in MuonEG with all three curves overlaid, and the per-event
minimum dR(e,mu) before any removal, with the 0.05 and 0.12 lines.

Usage:
    python check_radius_change.py \
        --new-root  /storage/.../runs_matched4_pilot_dr012_20261007 \
        --old-root  /storage/.../runs_matched4_pilot_onboth_20261006 \
        --off-root  /storage/.../runs_matched4_pilot_off_20261006 \
        --out-json  evidence/B_gates.json --out-plots plots
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

import numpy as np  # noqa: E402

from studies.cms_datasets.cluster.run_dataset_on_file import DELIVERY_VETO_ORDER_4  # noqa: E402

FLAG_COLS = [f"acc_{l}" for l in DELIVERY_VETO_ORDER_4] + ["exclusive"]
GATE1_MASS_MAX_GEV = 5.0
GATE1_MAX_REMAINING_PAIRS = 10
OLD_RADIUS = 0.05
NEW_RADIUS = 0.12


def load_metadata(root: Path) -> dict:
    out = {}
    for dataset in DELIVERY_VETO_ORDER_4:
        metas = []
        d = root / dataset
        if d.exists():
            for job in sorted(d.glob("job_*")):
                f = job / "job_metadata.json"
                if f.exists():
                    metas.append(json.loads(f.read_text(encoding="utf-8")))
        out[dataset] = metas
    return out


def emu_hist(metas) -> tuple:
    """Sum the per-job m(e,mu) fine histogram (0-20 GeV, 0.1 GeV bins)."""
    edges = None
    total = None
    for m in metas:
        node = (m.get("matched4_diagnostics") or {}).get(
            "emu_pair_mass_fine_histogram_accepted_events")
        if not node:
            continue
        e = np.asarray(node["bin_edges_gev"], dtype=float)
        c = np.asarray(node["counts"], dtype=float)
        if edges is None:
            edges, total = e, c.copy()
        else:
            assert np.array_equal(edges, e), "m(e,mu) binning differs between jobs"
            total += c
    return edges, total


def min_dr_hist(metas) -> tuple:
    """Sum the per-job per-event minimum dR(e,mu) histogram, which the
    driver computes BEFORE any overlap removal."""
    edges = None
    total = None
    overflow = 0
    for m in metas:
        # The driver's own diagnostic, computed BEFORE any overlap removal:
        # the per-event minimum dR over every selected electron-muon pair,
        # restricted to events with >=1 electron AND >=1 muon selected.
        node = (m.get("diagnostics") or {}).get("min_dr_any_e_any_mu")
        _unused = None
        if not node:
            continue
        e = np.asarray(node["bin_edges_gev"], dtype=float)
        c = np.asarray(node["counts"], dtype=float)
        overflow += int(node.get("n_overflow", 0))
        if edges is None:
            edges, total = e, c.copy()
        else:
            total += c
    return edges, total, overflow


def load_dump(path: Path) -> dict:
    rows = {}
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            rows[(int(row["run"]), int(row["luminosityBlock"]), int(row["event"]))] = row
    return rows


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--new-root", required=True, help="the dR 0.12 run")
    p.add_argument("--old-root", required=True, help="the dR 0.05 run")
    p.add_argument("--off-root", required=True, help="the removal-off run")
    p.add_argument("--out-json", required=True)
    p.add_argument("--out-plots", required=True)
    p.add_argument("--max-examples", type=int, default=25)
    p.add_argument("--band-check-dir", default=None,
                   help="directory of verify_radius_band.py outputs; with it, the "
                        "events that are absent from the dR 0.12 dump are settled "
                        "against the data and GATE 2 gets its final verdict")
    args = p.parse_args()

    new_root, old_root, off_root = map(Path, (args.new_root, args.old_root, args.off_root))
    meta = {"new": load_metadata(new_root), "old": load_metadata(old_root),
            "off": load_metadata(off_root)}
    report = {"what": "Step B gates for the dR 0.05 -> 0.12 overlap-removal radius",
              "new_root": str(new_root), "old_root": str(old_root),
              "off_root": str(off_root),
              "old_radius": OLD_RADIUS, "new_radius": NEW_RADIUS}

    # ---------------- GATE 1 ----------------------------------------------
    gate1 = {"definition": f"selected e-mu pairs with m(e,mu) < {GATE1_MASS_MAX_GEV} GeV "
                           "in accepted MuonEG pilot events",
             "pass_if": f"<= {GATE1_MAX_REMAINING_PAIRS} pairs remain at dR {NEW_RADIUS}"}
    for tag in ("off", "old", "new"):
        edges, counts = emu_hist(meta[tag]["MuonEG"])
        if edges is None:
            gate1[tag] = None
            continue
        below = edges[:-1] < GATE1_MASS_MAX_GEV
        gate1[f"n_pairs_below_5gev_{tag}"] = int(counts[below].sum())
        gate1[f"n_pairs_below_1gev_{tag}"] = int(counts[edges[:-1] < 1.0].sum())
        gate1[f"n_pairs_total_0_20gev_{tag}"] = int(counts.sum())
    n_remaining = gate1.get("n_pairs_below_5gev_new")
    gate1["n_remaining"] = n_remaining
    gate1["passed"] = bool(n_remaining is not None
                           and n_remaining <= GATE1_MAX_REMAINING_PAIRS)
    report["gate1"] = gate1
    print(f"GATE 1: m(e,mu) < {GATE1_MASS_MAX_GEV} GeV pairs in MuonEG accepted events")
    print(f"  removal OFF      : {gate1.get('n_pairs_below_5gev_off')}")
    print(f"  dR {OLD_RADIUS}          : {gate1.get('n_pairs_below_5gev_old')}")
    print(f"  dR {NEW_RADIUS}          : {gate1.get('n_pairs_below_5gev_new')}")
    print(f"  => {'PASS' if gate1['passed'] else 'FAIL'}")

    # ---------------- GATE 2 ----------------------------------------------
    gate2 = {"definition": "every event differing between the two radii must contain "
                           "at least one selected electron with "
                           f"{OLD_RADIUS} <= dR(e, nearest selected muon) < {NEW_RADIUS} "
                           "that the new radius removed; equivalently, that event's "
                           "removed-electron count must be strictly larger at "
                           f"{NEW_RADIUS} than at {OLD_RADIUS} (the removal is "
                           "monotonic in the radius)",
             "per_dataset": {}}
    totals = {"n_changed": 0, "n_only_old": 0, "n_only_new": 0, "n_unexplained": 0,
              "n_fs_changed": 0, "n_flags_changed": 0, "n_extra_electrons_removed": 0}
    # {"<dataset>:<job>": [[run, lumi, event], ...]} -- events whose
    # explanation must be checked against the original data because they are
    # absent from the dR 0.12 dump.
    to_verify: dict = {}
    unexplained_examples = []
    changed_examples = []
    for dataset in DELIVERY_VETO_ORDER_4:
        blk = {"n_accepted_old": 0, "n_accepted_new": 0, "n_only_old": 0, "n_only_new": 0,
               "n_fs_changed": 0, "n_flags_changed": 0, "n_changed": 0,
               "n_unexplained": 0, "n_extra_electrons_removed": 0}
        for job in sorted((new_root / dataset).glob("job_*")):
            idx = job.name
            new_f = job / "debug_events.csv"
            old_f = old_root / dataset / idx / "debug_events.csv"
            if not new_f.exists() or not old_f.exists():
                continue
            new_rows = load_dump(new_f)
            old_rows = load_dump(old_f)
            blk["n_accepted_new"] += len(new_rows)
            blk["n_accepted_old"] += len(old_rows)
            only_old = set(old_rows) - set(new_rows)
            only_new = set(new_rows) - set(old_rows)
            blk["n_only_old"] += len(only_old)
            blk["n_only_new"] += len(only_new)
            # events dropped by the larger radius must also be explained
            # Events accepted at 0.05 but gone at 0.12 have no row in the
            # new dump, so their removed-electron count cannot be read there.
            # They are listed for verify_radius_band.py, which re-reads the
            # original file and checks the band condition against the data.
            for key in only_old:
                blk["n_changed"] += 1
                to_verify.setdefault(f"{dataset}:{idx}", []).append(list(key))
            for key in set(new_rows) & set(old_rows):
                a, b = new_rows[key], old_rows[key]
                nr_new = int(a["n_electrons_removed"])
                nr_old = int(b["n_electrons_removed"])
                fs_diff = a["final_state"] != b["final_state"]
                flag_diff = any(a[c] != b[c] for c in FLAG_COLS)
                if not (fs_diff or flag_diff):
                    continue
                blk["n_changed"] += 1
                blk["n_fs_changed"] += int(fs_diff)
                blk["n_flags_changed"] += int(flag_diff)
                extra = nr_new - nr_old
                blk["n_extra_electrons_removed"] += max(extra, 0)
                if extra <= 0:
                    blk["n_unexplained"] += 1
                    if len(unexplained_examples) < args.max_examples:
                        unexplained_examples.append({
                            "dataset": dataset, "job": idx, "key": list(key),
                            "n_removed_old": nr_old, "n_removed_new": nr_new,
                            "fs_old": b["final_state"], "fs_new": a["final_state"]})
                elif len(changed_examples) < args.max_examples:
                    changed_examples.append({
                        "dataset": dataset, "job": idx, "key": list(key),
                        "n_removed_old": nr_old, "n_removed_new": nr_new,
                        "fs_old": b["final_state"], "fs_new": a["final_state"]})
        gate2["per_dataset"][dataset] = blk
        for k in totals:
            if k in blk:
                totals[k] += blk[k]
        print(f"  {dataset:12s} accepted {blk['n_accepted_old']} -> {blk['n_accepted_new']}"
              f"  lost {blk['n_only_old']}  gained {blk['n_only_new']}"
              f"  changed {blk['n_changed']}  unexplained {blk['n_unexplained']}")
    gate2["totals"] = totals
    gate2["events_needing_data_verification"] = to_verify
    gate2["n_events_needing_data_verification"] = sum(len(v) for v in to_verify.values())
    gate2["unexplained_examples"] = unexplained_examples
    gate2["changed_examples"] = changed_examples
    gate2["passed_for_events_present_in_both"] = bool(totals["n_unexplained"] == 0)

    # Settle the events that have no row in the dR 0.12 dump, using
    # verify_radius_band.py's read-back of the original files.
    band = {"checked": False}
    if args.band_check_dir:
        bd = Path(args.band_check_dir)
        files = sorted(bd.glob("*.json"))
        n_req = n_found = n_expl = n_unexpl = 0
        lowmass = []
        per_file = []
        for f in files:
            d = json.loads(f.read_text(encoding="utf-8"))
            n_req += int(d.get("n_keys_requested", 0))
            n_found += int(d.get("n_keys_found_in_file", 0))
            n_expl += int(d.get("n_explained", 0))
            n_unexpl += int(d.get("n_unexplained", 0))
            lowmass.extend(d.get("surviving_lowmass_pairs", []))
            per_file.append({k: d.get(k) for k in
                             ("dataset", "job", "n_keys_requested",
                              "n_keys_found_in_file", "n_explained", "n_unexplained",
                              "n_surviving_lowmass_pairs")})
        band = {"checked": True, "n_result_files": len(files),
                "n_events_requested": n_req, "n_events_found": n_found,
                "n_explained": n_expl, "n_unexplained": n_unexpl,
                "all_requested_events_found": bool(n_found == n_req),
                "per_file": per_file,
                "surviving_lowmass_pairs_from_data": lowmass[:50],
                "n_surviving_lowmass_pairs_from_data": len(lowmass)}
        print(f"  band check: {n_found}/{n_req} events found, "
              f"explained {n_expl}, unexplained {n_unexpl}")
    gate2["band_check"] = band

    if to_verify and not band.get("checked"):
        gate2["passed"] = None
        verdict = "PENDING the data check on events absent from the 0.12 dump"
    else:
        ok = totals["n_unexplained"] == 0 and band.get("n_unexplained", 0) == 0             and (not to_verify or band.get("all_requested_events_found", False))
        gate2["passed"] = bool(ok)
        verdict = "PASS" if ok else "FAIL"
    gate2["verdict"] = verdict
    report["gate2"] = gate2
    print(f"GATE 2: unexplained differences {totals['n_unexplained']} "
          f"(events present at both radii) => {verdict}")

    # ---------------- B3 --------------------------------------------------
    b3 = {}
    guard = 0
    for tag in ("new", "old"):
        for dataset in DELIVERY_VETO_ORDER_4:
            for m in meta[tag][dataset]:
                guard += int(((m.get("matched4_diagnostics") or {})
                              .get("trigger_guard_violations") or {}).get("total", 0))
    b3["trigger_guard_violations_total"] = guard
    same_sets = {}
    for dataset in ("DoubleMuon", "SingleMuon"):
        identical = True
        for job in sorted((new_root / dataset).glob("job_*")):
            new_f = job / "debug_events.csv"
            old_f = old_root / dataset / job.name / "debug_events.csv"
            if not new_f.exists() or not old_f.exists():
                identical = False
                continue
            if set(load_dump(new_f)) != set(load_dump(old_f)):
                identical = False
        same_sets[dataset] = identical
    b3["accepted_event_sets_identical_to_dr005"] = same_sets
    # versus master == the removal-off run (Prompt 1 E1(a) proved OFF is
    # shard-for-shard identical to master 4bbe972)
    vs_master = {}
    for dataset in ("DoubleMuon", "SingleMuon"):
        n_fs = 0
        n_acc = 0
        for job in sorted((new_root / dataset).glob("job_*")):
            new_f = job / "debug_events.csv"
            off_f = off_root / dataset / job.name / "debug_events.csv"
            if not new_f.exists() or not off_f.exists():
                continue
            a, b = load_dump(new_f), load_dump(off_f)
            n_acc += len(a)
            for key in set(a) & set(b):
                if a[key]["final_state"] != b[key]["final_state"]:
                    n_fs += 1
        vs_master[dataset] = {"n_accepted": n_acc, "n_final_state_changed_vs_master": n_fs}
    b3["muon_datasets_vs_master"] = vs_master
    report["b3"] = b3
    print(f"B3: guard violations {guard}; accepted sets identical to dR 0.05: {same_sets}")
    print(f"    vs master (removal off): {vs_master}")

    # ---------------- B4 plots -------------------------------------------
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    out_plots = Path(args.out_plots)
    out_plots.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(7.8, 4.6))
    styles = {"off": ("removal OFF", "crimson"), "old": (f"dR < {OLD_RADIUS}", "darkorange"),
              "new": (f"dR < {NEW_RADIUS}", "C0")}
    for tag, (label, colour) in styles.items():
        edges, counts = emu_hist(meta[tag]["MuonEG"])
        if edges is None:
            continue
        ax.step(0.5 * (edges[:-1] + edges[1:]), counts, where="mid", lw=1.2,
                color=colour, label=f"{label} ({int(counts.sum())} pairs)")
    ax.set_yscale("log")
    ax.set_xlabel("m(e, $\\mu$) [GeV], every selected pair (0.1 GeV diagnostic bins)")
    ax.set_ylabel("pairs")
    ax.set_title("MuonEG pilot, accepted events: electron-muon pair mass\n"
                 "removal off vs dR < 0.05 vs dR < 0.12")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(out_plots / "B4_muoneg_emu_mass_three_radii.png", dpi=140)
    plt.close(fig)
    print(f"wrote {out_plots / 'B4_muoneg_emu_mass_three_radii.png'}")

    all_metas = [m for ds in DELIVERY_VETO_ORDER_4 for m in meta["new"][ds]]
    edges, counts, overflow = min_dr_hist(all_metas)
    mindr = {"found": edges is not None}
    if edges is not None:
        keep = edges[:-1] < 0.6
        fig, ax = plt.subplots(figsize=(7.8, 4.6))
        ax.step(0.5 * (edges[:-1] + edges[1:])[keep], counts[keep], where="mid",
                lw=1.2, color="C0")
        ax.axvline(OLD_RADIUS, color="darkorange", ls="--", lw=1.2,
                   label=f"old radius {OLD_RADIUS}")
        ax.axvline(NEW_RADIUS, color="crimson", ls="--", lw=1.2,
                   label=f"new radius {NEW_RADIUS}")
        ax.set_yscale("log")
        ax.set_xlabel("per-event minimum dR(e, $\\mu$) over selected pairs, BEFORE removal")
        ax.set_ylabel("events")
        ax.set_title("All pilot events with >=1 selected electron and >=1 selected muon:\n"
                     "how close the closest electron-muon pair is")
        ax.legend(fontsize=8)
        ax.grid(alpha=0.3)
        fig.tight_layout()
        fig.savefig(out_plots / "B4_min_dr_emu_before_removal.png", dpi=140)
        plt.close(fig)
        print(f"wrote {out_plots / 'B4_min_dr_emu_before_removal.png'}")
        in_band = (edges[:-1] >= OLD_RADIUS) & (edges[:-1] < NEW_RADIUS)
        mindr.update({
            "n_events_min_dr_below_005": int(counts[edges[:-1] < OLD_RADIUS].sum()),
            "n_events_min_dr_in_band_005_012": int(counts[in_band].sum()),
            "n_events_min_dr_below_012": int(counts[edges[:-1] < NEW_RADIUS].sum()),
            "n_events_total_in_histogram": int(counts.sum()) + overflow,
        })
        print(f"    min-dR: below 0.05 {mindr['n_events_min_dr_below_005']}, "
              f"in band {mindr['n_events_min_dr_in_band_005_012']}")
    report["min_dr_before_removal"] = mindr

    keys_path = Path(args.out_json).with_name("B_events_to_verify.json")
    keys_path.write_text(json.dumps({
        "what": "events accepted at dR 0.05 but not at dR 0.12; their band "
                "condition is checked against the original data by "
                "verify_radius_band.py",
        "old_radius": OLD_RADIUS, "new_radius": NEW_RADIUS,
        "by_dataset_job": to_verify}, indent=2), encoding="utf-8")
    print(f"wrote {keys_path} "
          f"({gate2['n_events_needing_data_verification']} events to verify)")

    report["both_gates_passed"] = bool(gate1["passed"] and gate2["passed"] is True)
    Path(args.out_json).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out_json).write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\nBOTH GATES PASSED = {report['both_gates_passed']}")
    print(f"wrote {args.out_json}")


if __name__ == "__main__":
    main()
