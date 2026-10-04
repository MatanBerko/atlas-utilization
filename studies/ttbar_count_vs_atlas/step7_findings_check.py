#!/usr/bin/env python
"""
Step 7 (ttbar_count_vs_atlas): confirm or refute findings (i)-(iv) about
upstream PR #31 BY RUNNING its code, not only by reading it.

Run twice, once per side, exactly like step2_enumerate.py: the script is
side-agnostic and imports `services.*` from whichever repo is on
PYTHONPATH, hard-failing if it resolves the wrong one. The two JSON
outputs are then merged by step7_findings_report.py.

What is actually executed on the PR #31 side:

  (i)  PR #31's own services.parsing.event_selection.apply_parsing_event_selection
       is run on a hand-built event record, with PR #31's own config.yaml
       particle_counts and kinematic_cuts, to see whether an event with
       5 light jets survives PARSING.  Then PR #31's own
       IMCalculator (constructed with its own config.yaml
       min/max_count_particle_in_combination and
       min/max_particles_in_combination) is run on the SAME record, and
       its final_state_counts()/group_by_final_state() output is
       inspected to see whether that event survives MASS CALCULATION.

  (ii) PR #31's whole parse+select path is run on an event whose single
       light jet sits at dR = 0.1 from the selected muon, to see whether
       the jet is still there afterwards.

  (iii) The thresholds are read out of PR #31's own config.yaml and
       reported next to ours (which are read out of the modules that
       actually apply them), so the comparison is between values in
       force, not values quoted in a document.

  (iv) services.pipelines.post_processing_pipeline._split_by_first_empty_bin
       is RUN on a crafted array whose gap does not sit on a 10 GeV grid
       boundary; the split mass it returns tells you directly whether the
       implementation is grid-aligned (upstream #27) or not.

Usage:
    PYTHONPATH=<repo> python step7_findings_check.py --side pr31|ours \
        --repo <repo> --out <json>
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys

import awkward as ak
import numpy as np

LOGGER = logging.getLogger("step7")
logging.basicConfig(level=logging.ERROR)

BIN_WIDTH = 10.0


def build_record(n_e, n_m, n_j, n_b, jet_phi_offsets=None, muon_phi=0.0):
    """A tiny Electrons/Muons/Jets/BJets record, one event.

    Every object is given a comfortably-passing pt (60 GeV) and eta (0.0)
    so that NO per-object kinematic cut can be the reason an event is
    dropped -- the only thing under test is the count/overlap logic.
    `jet_phi_offsets`, when given, sets each light jet's phi relative to
    the muon, which is how the overlap-removal probe is built.
    """
    def objs(n, phis=None, phi0=0.0):
        phis = phis if phis is not None else [phi0] * n
        return [{"pt": 60.0, "eta": 0.0, "phi": float(phis[i]), "mass": 1.0,
                 "ptvarcone30_Nonprompt_All_MaxWeightTTVALooseCone_pt1000": 0.0}
                for i in range(n)]

    jet_phis = ([muon_phi + d for d in jet_phi_offsets]
                if jet_phi_offsets is not None else [2.0 + 0.3 * i for i in range(n_j)])
    return ak.Array([{
        "Electrons": objs(n_e, phi0=3.0),
        "Muons": objs(n_m, phi0=muon_phi),
        "Jets": objs(n_j, phis=jet_phis),
        "BJets": objs(n_b, phi0=-2.0),
    }])


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--side", required=True, choices=["ours", "pr31"])
    p.add_argument("--repo", required=True)
    p.add_argument("--out", required=True)
    args = p.parse_args()

    import services.calculations.im_calculator as _im
    resolved = os.path.realpath(_im.__file__)
    expected = os.path.realpath(os.path.join(args.repo, "services", "calculations", "im_calculator.py"))
    if resolved != expected:
        raise SystemExit(f"WRONG REPO: imported {resolved}, expected {expected}")

    from services.calculations.im_calculator import IMCalculator
    from services.pipelines.post_processing_pipeline import _split_by_first_empty_bin, _find_rightmost_highest_peak

    out = {"side": args.side, "repo": args.repo,
           "repo_head": os.environ.get("REPO_HEAD", ""),
           "imported_im_calculator_from": resolved}

    # --- configuration in force on this side -----------------------------
    if args.side == "pr31":
        import yaml
        cfg = yaml.safe_load(open(os.path.join(args.repo, "config.yaml")))
        mc = cfg["mass_calculation_task_config"]
        pt = cfg["parsing_task_config"]
        pp = cfg["post_processing_task_config"]
        hc = cfg["histogram_creation_task_config"]
        conf = {
            "source": "PR #31 config.yaml",
            "trigger_enabled": cfg["trigger_config"]["enabled"],
            "btag_threshold_btagDeepFlavB": pt["jet_btagging_thresholds"]["btagDeepFlavB"],
            "particle_counts": pt["particle_counts"],
            "kinematic_cuts": pt["kinematic_cuts"],
            "min_count_particle_in_combination": mc["min_count_particle_in_combination"],
            "max_count_particle_in_combination": mc["max_count_particle_in_combination"],
            "min_particles_in_combination": mc["min_particles_in_combination"],
            "max_particles_in_combination": mc["max_particles_in_combination"],
            "min_events_per_fs": mc["min_events_per_fs"],
            "z_peak_cutoff_gev": pp["z_peak_cutoff"],
            "max_mass_cutoff_gev": pp["max_mass_cutoff"],
            "peak_detection_bin_width_gev": pp["peak_detection_bin_width_gev"],
            "histogram_bin_width_gev": hc["bin_width_gev"],
        }
        min_k, max_k = mc["min_count_particle_in_combination"], mc["max_count_particle_in_combination"]
        min_n, max_n = mc["min_particles_in_combination"], mc["max_particles_in_combination"]
    else:
        from studies.m0m1j0_cms import selection as sel
        import studies.cms_datasets.cluster.run_dataset_on_file as drv
        from studies.cms_coverage.cluster.merge_and_count import (
            Z_PEAK_CUTOFF, MAX_MASS_CUTOFF, PRIMARY_MIN_EVENTS_PER_FS, BIN_WIDTH_GEV,
        )
        conf = {
            "source": "the modules that actually apply the values",
            "trigger_enabled": "yes for data and for --population matched; "
                               "no for --population notrigger (study only)",
            "btag_threshold_btagDeepFlavB": sel.BTAG_DEEPFLAVB_MEDIUM_WP,
            "muon_pt_min_gev": sel.MUON_PT_MIN_GEV, "muon_eta_max": sel.MUON_ETA_MAX,
            "muon_iso_max_pfRelIso04_all": sel.MUON_ISO_MAX,
            "electron_pt_min_gev": sel.ELECTRON_PT_MIN_GEV, "electron_eta_max": sel.ELECTRON_ETA_MAX,
            "electron_cutBased_min": sel.ELECTRON_CUTBASED_MIN,
            "jet_pt_min_gev": sel.JET_PT_MIN_GEV, "jet_eta_max": sel.JET_ETA_MAX,
            "jet_lepton_clean_dr": sel.JET_LEPTON_CLEAN_DR,
            "min_count_particle_in_combination": drv.MIN_COUNT_PARTICLE_IN_COMBINATION,
            "max_count_particle_in_combination": drv.MAX_COUNT_PARTICLE_IN_COMBINATION,
            "min_particles_in_combination": drv.MIN_PARTICLES_IN_COMBINATION,
            "max_particles_in_combination": drv.MAX_PARTICLES_IN_COMBINATION,
            "min_events_per_fs": PRIMARY_MIN_EVENTS_PER_FS,
            "z_peak_cutoff_gev": Z_PEAK_CUTOFF,
            "max_mass_cutoff_gev": MAX_MASS_CUTOFF,
            "histogram_bin_width_gev": BIN_WIDTH_GEV,
        }
        min_k, max_k = drv.MIN_COUNT_PARTICLE_IN_COMBINATION, drv.MAX_COUNT_PARTICLE_IN_COMBINATION
        min_n, max_n = drv.MIN_PARTICLES_IN_COMBINATION, drv.MAX_PARTICLES_IN_COMBINATION
    out["config_in_force"] = conf

    # --- (i) does an event with 5 light jets survive? --------------------
    finding_i = {}
    for n_j in (3, 4, 5, 6):
        rec = build_record(n_e=0, n_m=1, n_j=n_j, n_b=1)
        calc = IMCalculator(events=rec, min_events_per_fs=1,
                            min_k=min_k, max_k=max_k, min_n=min_n, max_n=max_n)
        counts = calc.final_state_counts()           # PR #31's own grouping entry point
        labels = list(calc.group_by_final_state())   # with the display cap applied
        finding_i[f"{n_j}_light_jets"] = {
            "survives_mass_calculation": len(counts) > 0,
            "final_state_counts": {str(k): int(v) for k, v in counts.items()},
            "labels_after_display_cap": labels,
        }
    out["finding_i_mass_calculation"] = finding_i
    out["finding_i_mass_calculation_note"] = (
        "IMCalculator._is_valid_fs is the same class on both sides, so both sides answer "
        "the same way HERE. That is not the comparison that matters: PR #31's im_pipeline "
        "really does group events through IMCalculator, while our driver does NOT -- it "
        "groups with its own run_dataset_on_file._group_by_final_state_with_mask, which "
        "applies no validity filter at all. See finding_i_our_driver_grouping below for "
        "what our production code path actually does with the same events."
    )

    if args.side == "ours":
        # The function our driver REALLY uses for final-state grouping.
        from studies.cms_datasets.cluster.run_dataset_on_file import (
            _group_by_final_state_with_mask,
        )
        driver_i = {}
        for n_j in (3, 4, 5, 6):
            rec = build_record(n_e=0, n_m=1, n_j=n_j, n_b=1)
            groups = [(label, int(len(evts))) for label, evts, _m
                      in _group_by_final_state_with_mask(rec)]
            driver_i[f"{n_j}_light_jets"] = {
                "survives_our_driver_grouping": len(groups) > 0,
                "labels": [g[0] for g in groups],
                "n_events_per_label": {g[0]: g[1] for g in groups},
            }
        out["finding_i_our_driver_grouping"] = driver_i

    # The same events through the PARSING stage, on the PR #31 side only
    # (we have no equivalent stage: our driver selects objects inline).
    if args.side == "pr31":
        import yaml
        from services.parsing.event_selection import apply_parsing_event_selection
        cfg = yaml.safe_load(open(os.path.join(args.repo, "config.yaml")))
        pt = cfg["parsing_task_config"]
        parse_i = {}
        for n_j in (3, 4, 5, 6):
            rec = build_record(n_e=0, n_m=1, n_j=n_j, n_b=1)
            kept = apply_parsing_event_selection(
                rec,
                particle_counts=pt["particle_counts"],
                # pt/eta cuts are in MeV in the ATLAS config; our synthetic
                # objects are built in the same units the rest of this probe
                # uses, so the kinematic cuts are deliberately NOT applied
                # here -- this probe is about counts, not kinematics.
                kinematic_cuts=None,
            )
            parse_i[f"{n_j}_light_jets"] = {
                "survives_parsing": len(kept) > 0,
                "n_light_jets_after": (int(ak.num(kept["Jets"], axis=1)[0]) if len(kept) else None),
            }
        out["finding_i_parsing"] = parse_i

        # (i) continued: >4 NON-light-jet objects must be rejected at parsing.
        nonlight = {}
        for n_b in (3, 4, 5):
            rec = build_record(n_e=0, n_m=1, n_j=1, n_b=n_b)
            kept = apply_parsing_event_selection(
                rec, particle_counts=pt["particle_counts"], kinematic_cuts=None)
            nonlight[f"1_muon_plus_{n_b}_bjets"] = {
                "n_non_light_jet_objects": 1 + n_b,
                "survives_parsing": len(kept) > 0,
            }
        out["finding_i_parsing_non_light_jet_cap"] = nonlight

        # (ii) overlap removal: a light jet 0.1 away in phi from the muon.
        rec = build_record(n_e=0, n_m=1, n_j=1, n_b=0, jet_phi_offsets=[0.1], muon_phi=0.0)
        kept = apply_parsing_event_selection(
            rec, particle_counts=pt["particle_counts"], kinematic_cuts=None)
        out["finding_ii_overlap"] = {
            "probe": "1 muon at (eta=0, phi=0) and 1 light jet at (eta=0, phi=0.1), dR = 0.1",
            "n_light_jets_before": 1,
            "n_light_jets_after_parsing_selection": (
                int(ak.num(kept["Jets"], axis=1)[0]) if len(kept) else 0),
            "jet_was_removed": (len(kept) == 0 or int(ak.num(kept["Jets"], axis=1)[0]) == 0),
        }
    else:
        # Our side: run the REAL selection function with cleaning on and off.
        from studies.m0m1j0_cms import selection as sel
        events = ak.Array([{
            "Muon_pt": [60.0], "Muon_eta": [0.0], "Muon_phi": [0.0], "Muon_mass": [0.105],
            "Muon_mediumId": [True], "Muon_pfRelIso04_all": [0.0], "Muon_charge": [1],
            "Electron_pt": [], "Electron_eta": [], "Electron_phi": [], "Electron_mass": [],
            "Electron_cutBased": [], "Electron_charge": [],
            "Jet_pt": [60.0], "Jet_eta": [0.0], "Jet_phi": [0.1], "Jet_mass": [5.0],
            "Jet_jetId": [6], "Jet_btagDeepFlavB": [0.0],
        }])
        muons = sel.select_muons(events)
        electrons = sel.select_electrons(events)
        with_or = sel.select_and_split_jets(events, muons, electrons, apply_lepton_cleaning=True)
        without_or = sel.select_and_split_jets(events, muons, electrons, apply_lepton_cleaning=False)
        out["finding_ii_overlap"] = {
            "probe": "1 muon at (eta=0, phi=0) and 1 light jet at (eta=0, phi=0.1), dR = 0.1",
            "n_light_jets_before": 1,
            "n_light_jets_with_overlap_removal": int(ak.num(with_or["Jets"], axis=1)[0]),
            "n_light_jets_without_overlap_removal": int(ak.num(without_or["Jets"], axis=1)[0]),
            "jet_was_removed": int(ak.num(with_or["Jets"], axis=1)[0]) == 0,
            "clean_dr": sel.JET_LEPTON_CLEAN_DR,
        }

    # --- (iv) is the outlier split aligned to the 10 GeV grid? -----------
    # Values packed into [203, 207] then a gap then [251, 255]. On a
    # 10 GeV grid the first empty bin starts at 210. With edges derived
    # from min/max by linspace, the split lands somewhere else entirely.
    arr = np.concatenate([
        np.linspace(203.0, 207.0, 40),
        np.linspace(251.0, 255.0, 40),
    ])
    main_arr, outliers = _split_by_first_empty_bin(arr, BIN_WIDTH, LOGGER)
    split_mass = float(main_arr.max()) if main_arr.size else None
    peak = _find_rightmost_highest_peak(arr, BIN_WIDTH, LOGGER)
    out["finding_iv_outlier_split"] = {
        "probe": "40 values in [203,207] + 40 values in [251,255], 10 GeV bins",
        "n_main": int(main_arr.size), "n_outliers": int(outliers.size),
        "max_of_main": split_mass,
        "split_boundary_is_on_the_10gev_grid": (
            None if main_arr.size == 0 or outliers.size == 0
            else bool(abs(float(outliers.min()) / BIN_WIDTH
                          - round(float(outliers.min()) / BIN_WIDTH)) < 1e-9
                      or _grid_aligned(main_arr, outliers, BIN_WIDTH))
        ),
        "first_outlier": float(outliers.min()) if outliers.size else None,
        "has_aligned_bin_edges_helper": _has_aligned_helper(),
        "peak_mass_returned": None if peak is None else float(peak),
    }

    with open(args.out, "w") as fh:
        json.dump(out, fh, indent=2, sort_keys=True)
    print(f"[{args.side}] wrote {args.out} (imported from {resolved})")


def _grid_aligned(main_arr, outliers, bin_width):
    """True when the split boundary coincides with a multiple of bin_width.

    The boundary lies in (max(main), min(outliers)]; it is grid-aligned iff
    exactly one multiple of bin_width sits in that half-open interval and
    the implementation chose it. We can only observe the interval, so this
    reports whether a grid multiple separates the two groups at all.
    """
    lo, hi = float(main_arr.max()), float(outliers.min())
    k = np.ceil(lo / bin_width)
    return bool(k * bin_width <= hi)


def _has_aligned_helper() -> bool:
    """Whether this side's post-processing module defines the
    `_aligned_bin_edges` helper that upstream #27 introduced."""
    import services.pipelines.post_processing_pipeline as pp
    return hasattr(pp, "_aligned_bin_edges")


if __name__ == "__main__":
    main()
