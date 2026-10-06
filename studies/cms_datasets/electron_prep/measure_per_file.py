#!/usr/bin/env python
"""
PREPARATION measurements, one input file per job. READ-ONLY: this script
never writes outside its own --output-dir, never touches the production
pipeline, and imports the production object selection unchanged.

What it measures depends on the dataset, so that each file is read once:

  SingleMuon      -> Step 2: the HLT_Ele27_WPTight_Gsf turn-on, measured
                     with an ORTHOGONAL tag: the event fired HLT_IsoMu24
                     and has a selected muon matched (dR < 0.1) to an
                     IsoMu24-style trigger object (id 13, bit 2 "Iso",
                     online pT >= 24). Every selected electron in such an
                     event is a probe. A probe PASSES if
                     HLT_Ele27_WPTight_Gsf fired AND the probe is matched
                     (dR < 0.1) to an electron trigger object (id 11) with
                     bit 2 = "1e (WPTight)".

  DoubleEG        -> Step 3: fraction of selected electrons matched to the
                     dielectron leg object (id 11, bit 16 = "2e"), vs
                     offline pT and eta region, in the dataset's own
                     triggered events.

  MuonEG          -> Step 3: fraction of selected electrons matched to the
                     muon-electron cross leg (id 11, bit 32 = "1e-1mu")
                     and of selected muons matched to the TrkIsoVVL leg
                     (id 13, bit 1). Step 4: the dR(e, mu) distribution.

  SingleElectron  -> Step 2 (loss side): among events this dataset would
                     accept, the matched leading electron's offline pT, so
                     the fraction lost by each candidate threshold can be
                     computed. Step 4: the dR(e, mu) distribution.

Every bit value used here comes from the TrigObj_filterBits branch TITLE
inside the real files -- see evidence/trigobj_titles_electron_datasets.json
and evidence/cmssw_bit_definitions.json.

Usage:
    python measure_per_file.py --dataset DoubleEG --era G --file-index 0 \
        --output-dir <dir>
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import awkward as ak  # noqa: E402
import numpy as np  # noqa: E402

from studies.cms_datasets.electron_prep.common import (  # noqa: E402
    TRIGOBJ_BRANCHES, TRIGOBJ_ELECTRON_ID, TRIGOBJ_MUON_ID, MATCH_DR_MAX,
    BIT_E_WPTIGHT, BIT_E_2E, BIT_E_1E1MU, BIT_MU_TRKISOVVL, BIT_MU_ISO,
    TURNON_BIN_EDGES, dataset_by_label, record_for, zip_trigobj,
    trigobj_best_match_pt, assert_matcher_agrees_with_production,
    select_objects, read_file, fire_mask, eta_region,
)
from studies.cms_datasets.cluster import run_dataset_on_file as drv  # noqa: E402

TAG_PATH = "HLT_IsoMu24"
PROBE_PATH = "HLT_Ele27_WPTight_Gsf"
TAG_ONLINE_PT_MIN = 24.0

# dR(e, mu) binning: 0.01-wide near 0 (the region the earlier MuonEG
# diagnostic flagged), then coarser out to 1.0, with an overflow count.
DR_EMU_FINE_EDGES = np.concatenate([
    np.arange(0.0, 0.20 + 1e-9, 0.01),
    np.array([0.25, 0.3, 0.4, 0.5, 0.7, 1.0]),
])
DR_EMU_THRESHOLDS = [0.02, 0.05, 0.1]

# Candidate matched-electron pT thresholds for SingleElectron (Step 2).
SE_CANDIDATE_THRESHOLDS = [25.0, 27.0, 28.0, 30.0, 32.0, 35.0]

# Probe-purity diagnostic. The production electron definition
# (selection.select_electrons: pT > 25, |eta| < 2.5, cutBased >= 3) is NOT
# changed anywhere -- it is imported and used exactly as delivered. But in a
# muon-triggered sample most electrons passing it are non-prompt (from
# jets), and those can never fire a WPTight single-electron trigger, so the
# as-specified probe measures trigger efficiency TIMES prompt purity. A
# second, prompt-enriched probe variant is therefore reported alongside,
# defined only by an extra isolation requirement on the PROBE -- a
# diagnostic selection, never a change to the delivered object definition.
PROBE_ISO_BRANCH = "Electron_pfRelIso03_all"
PROBE_PROMPT_ISO_MAX = 0.10

# Bits to census, so that every claim about which bit tags which leg rests on
# a committed measurement rather than on reading filter-name patterns.
ELECTRON_BITS_TO_CENSUS = [(1, "CaloIdL_TrackIdL_IsoVL"), (2, "1e (WPTight)"),
                           (16, "2e"), (32, "1e-1mu"), (2048, "1e (CaloIdVT_GsfTrkIdT)")]
MUON_BITS_TO_CENSUS = [(1, "TrkIsoVVL"), (2, "Iso"), (4, "OverlapFilter PFTau"),
                       (8, "IsoTkMu"), (1024, "1mu (Mu50)")]


def hist_counts(values: np.ndarray, edges: np.ndarray) -> list:
    h, _ = np.histogram(values, bins=edges)
    return [int(x) for x in h]


def selected_electron_iso(events: ak.Array) -> ak.Array:
    """pfRelIso03_all for the SELECTED electrons, in the same per-event order
    selection.select_electrons returns them.

    Reproduces that function's own 3-condition mask externally, using ONLY
    its own imported constants (never re-typed) -- exactly the pattern
    run_dataset_on_file already uses for its electron-charge diagnostic. The
    production function, and the electrons used for physics, are untouched.
    """
    from studies.m0m1j0_cms import selection as sel
    mask = (
        (events.Electron_pt > sel.ELECTRON_PT_MIN_GEV)
        & (abs(events.Electron_eta) < sel.ELECTRON_ETA_MAX)
        & (events.Electron_cutBased >= sel.ELECTRON_CUTBASED_MIN)
    )
    return events[PROBE_ISO_BRANCH][mask]


def best_matched_bits(objs: ak.Array, trigobj: ak.Array, obj_id: int,
                      dr_max: float = MATCH_DR_MAX) -> ak.Array:
    """filterBits of the best (largest-bits) trigger object of type `obj_id`
    within dR < dr_max of each offline object, or 0 if there is none.

    Diagnostic only. This is what turns "which bit actually tags this leg"
    from an inference about filter-name wildcards into a measurement.
    """
    tsel = trigobj[trigobj.id == obj_id]
    po, pt_ = ak.unzip(ak.cartesian([objs, tsel], nested=True))
    deta = po.eta - pt_.eta
    dphi = (po.phi - pt_.phi + np.pi) % (2 * np.pi) - np.pi
    dr = np.sqrt(deta ** 2 + dphi ** 2)
    b = ak.where(dr < dr_max, pt_.filterBits, 0)
    return ak.fill_none(ak.max(b, axis=-1), 0)


def measure_bit_census(label, events, muons, electrons, trigobj, out):
    """Which trigger-object bits do the offline objects in this dataset's own
    triggered events actually carry? Pure measurement, no selection."""
    d = dataset_by_label(label)
    fired = fire_mask(events, d.trigger_paths)
    res = {"n_fired": int(fired.sum()), "objects": {}}
    for name, objs, oid, bits in (
        ("electrons", electrons[fired], TRIGOBJ_ELECTRON_ID, ELECTRON_BITS_TO_CENSUS),
        ("muons", muons[fired], TRIGOBJ_MUON_ID, MUON_BITS_TO_CENSUS),
    ):
        bb = ak.to_numpy(ak.flatten(best_matched_bits(objs, trigobj[fired], oid)))
        n = int(bb.size)
        entry = {
            "n_objects": n,
            "n_with_no_matched_trigger_object": int((bb == 0).sum()),
            "fraction_with_no_matched_trigger_object": (float((bb == 0).mean()) if n else None),
            "fraction_with_bit": {},
        }
        for bit, meaning in bits:
            entry["fraction_with_bit"][str(bit)] = {
                "meaning_from_branch_title": meaning,
                "fraction": float(((bb & bit) != 0).mean()) if n else None,
                "n": int(((bb & bit) != 0).sum()),
            }
        res["objects"][name] = entry
    out["bit_census"] = res


def _fs_label(n_e, n_m, n_j, n_b) -> np.ndarray:
    """The production final-state label, display-capped at 4 per type --
    same formula as run_dataset_on_file._group_by_final_state_with_mask."""
    from services.calculations import physics_calcs
    return np.array([
        physics_calcs.limit_particles_in_fs(f"{e}e_{m}m_{j}j_0g_0t_{b}b", 4)
        for e, m, j, b in zip(n_e, n_m, n_j, n_b)
    ])


def measure_turnon(events, muons, electrons, trigobj, out):
    """Step 2: Ele27 turn-on on an orthogonal (IsoMu24) tag."""
    tag_fired = fire_mask(events, [TAG_PATH])
    tag_best = trigobj_best_match_pt(muons, trigobj, TRIGOBJ_MUON_ID, BIT_MU_ISO)
    tag_ok_mu = tag_best >= TAG_ONLINE_PT_MIN
    has_tag_muon = ak.to_numpy(ak.sum(tag_ok_mu, axis=1)) >= 1
    is_tag_event = tag_fired & has_tag_muon

    probe_fired = fire_mask(events, [PROBE_PATH])
    probe_best = trigobj_best_match_pt(electrons, trigobj, TRIGOBJ_ELECTRON_ID, BIT_E_WPTIGHT)
    probe_matched = probe_best > -np.inf

    # Flatten probes, keeping only probes in tag events.
    keep = is_tag_event
    e_pt = ak.to_numpy(ak.flatten(electrons.pt[keep]))
    e_eta = ak.to_numpy(ak.flatten(electrons.eta[keep]))
    e_matched = ak.to_numpy(ak.flatten(probe_matched[keep]))
    n_probe_per_event = ak.to_numpy(ak.num(electrons[keep], axis=1))
    e_fired = np.repeat(probe_fired[keep], n_probe_per_event)
    e_pass = e_matched & e_fired

    e_iso = ak.to_numpy(ak.flatten(selected_electron_iso(events)[keep]))
    regions = eta_region(np.abs(e_eta))
    res = {"n_tag_events": int(is_tag_event.sum()),
           "n_tag_fired": int(tag_fired.sum()),
           "n_probes": int(e_pt.size),
           "probe_iso_branch": PROBE_ISO_BRANCH,
           "probe_prompt_iso_max": PROBE_PROMPT_ISO_MAX,
           "bin_edges": [float(x) for x in TURNON_BIN_EDGES],
           "variants": {}}
    for vname, vmask in (("all", np.ones(e_pt.shape, dtype=bool)),
                         ("prompt_like", e_iso < PROBE_PROMPT_ISO_MAX)):
        v = {"n_probes": int(vmask.sum()), "by_region": {}}
        for reg in ("barrel", "gap", "endcap"):
            m = (regions == reg) & vmask
            v["by_region"][reg] = {
                "denominator": hist_counts(e_pt[m], TURNON_BIN_EDGES),
                "numerator": hist_counts(e_pt[m & e_pass], TURNON_BIN_EDGES),
                "n_probes": int(m.sum()),
                "n_pass": int((m & e_pass).sum()),
            }
        res["variants"][vname] = v
    # Alias so the as-specified variant also sits at the original key.
    res["by_region"] = res["variants"]["all"]["by_region"]
    out["step2_ele27_turnon"] = res


def measure_leg_matching(label, events, muons, electrons, trigobj, out):
    """Step 3: per-leg matching efficiency inside the dataset's own
    triggered events."""
    d = dataset_by_label(label)
    fired = fire_mask(events, d.trigger_paths)
    res = {"n_fired": int(fired.sum()), "trigger_paths": list(d.trigger_paths),
           "bin_edges": [float(x) for x in TURNON_BIN_EDGES], "legs": {}}

    if label == "DoubleEG":
        legs = [("electrons_bit16_2e", electrons, TRIGOBJ_ELECTRON_ID, BIT_E_2E)]
    else:  # MuonEG
        legs = [("electrons_bit32_1e1mu", electrons, TRIGOBJ_ELECTRON_ID, BIT_E_1E1MU),
                ("muons_bit1_trkisovvl", muons, TRIGOBJ_MUON_ID, BIT_MU_TRKISOVVL)]

    for name, objs, obj_id, bit in legs:
        best = trigobj_best_match_pt(objs, trigobj, obj_id, bit)
        matched = best > -np.inf
        pt = ak.to_numpy(ak.flatten(objs.pt[fired]))
        eta = ak.to_numpy(ak.flatten(objs.eta[fired]))
        mt = ak.to_numpy(ak.flatten(matched[fired]))
        on_pt = ak.to_numpy(ak.flatten(best[fired]))
        regions = eta_region(np.abs(eta))
        entry = {"n_objects": int(pt.size), "n_matched": int(mt.sum()), "by_region": {}}
        for reg in ("barrel", "gap", "endcap", "outside"):
            m = regions == reg
            if not m.any():
                continue
            entry["by_region"][reg] = {
                "denominator": hist_counts(pt[m], TURNON_BIN_EDGES),
                "numerator": hist_counts(pt[m & mt], TURNON_BIN_EDGES),
                "n_objects": int(m.sum()), "n_matched": int((m & mt).sum()),
            }
        # Online pT of matched objects: needed to see whether a 23 GeV leg
        # shows a turn-on above the 25 GeV offline cut.
        good = mt & np.isfinite(on_pt)
        entry["matched_online_pt_hist"] = {
            "edges": [float(x) for x in np.arange(0.0, 60.0 + 1e-9, 1.0)],
            "counts": hist_counts(on_pt[good], np.arange(0.0, 60.0 + 1e-9, 1.0)),
        }
        res["legs"][name] = entry
    out["step3_leg_matching"] = res


def measure_emu_overlap(label, events, muons, electrons, jets, trigobj, out):
    """Step 4: dR(e, mu) distribution and the category-change impact of a
    hypothetical removal. NOTHING is removed -- this only counts."""
    d = dataset_by_label(label)
    fired = fire_mask(events, d.trigger_paths)
    e = electrons[fired]
    m = muons[fired]
    j_light = jets["Jets"][fired]
    j_b = jets["BJets"][fired]

    has_both = (ak.to_numpy(ak.num(e, axis=1)) >= 1) & (ak.to_numpy(ak.num(m, axis=1)) >= 1)
    e_p4 = drv._p4_no_mass_needed(e)
    m_p4 = drv._p4_no_mass_needed(m)
    pe, pm = ak.unzip(ak.cartesian([e_p4, m_p4], nested=True))
    dr = pe.deltaR(pm)                       # [event][electron][muon]
    min_dr_per_e = ak.fill_none(ak.min(dr, axis=-1), np.inf)   # [event][electron]
    min_dr_per_event = ak.fill_none(ak.min(min_dr_per_e, axis=-1), np.inf)

    all_dr = ak.to_numpy(ak.flatten(dr, axis=None))
    all_dr = all_dr[np.isfinite(all_dr)]
    ev_min = ak.to_numpy(min_dr_per_event)
    ev_min_finite = ev_min[np.isfinite(ev_min)]

    res = {
        "n_fired": int(fired.sum()),
        "n_events_with_e_and_mu": int(has_both.sum()),
        "all_pairs": {
            "edges": [float(x) for x in DR_EMU_FINE_EDGES],
            "counts": hist_counts(all_dr, DR_EMU_FINE_EDGES),
            "n_pairs": int(all_dr.size),
            "n_overflow_above_1": int((all_dr >= DR_EMU_FINE_EDGES[-1]).sum()),
        },
        "per_event_min_dr": {
            "edges": [float(x) for x in DR_EMU_FINE_EDGES],
            "counts": hist_counts(ev_min_finite, DR_EMU_FINE_EDGES),
            "n_events": int(ev_min_finite.size),
        },
        "fraction_of_e_mu_events_below": {},
        "category_change_if_removed": {},
    }
    denom = int(has_both.sum())
    for thr in DR_EMU_THRESHOLDS:
        n_below = int((ev_min_finite < thr).sum())
        res["fraction_of_e_mu_events_below"][str(thr)] = {
            "n_events": n_below,
            "fraction_of_e_mu_events": (n_below / denom) if denom else None,
            "fraction_of_fired_events": (n_below / int(fired.sum())) if int(fired.sum()) else None,
        }

    # How many events would change final-state category if electrons within
    # dR < thr of a selected muon were dropped. Counting only.
    n_e0 = ak.to_numpy(ak.num(e, axis=1))
    n_m0 = ak.to_numpy(ak.num(m, axis=1))
    n_j0 = ak.to_numpy(ak.num(j_light, axis=1))
    n_b0 = ak.to_numpy(ak.num(j_b, axis=1))
    base = _fs_label(n_e0, n_m0, n_j0, n_b0)
    for thr in DR_EMU_THRESHOLDS:
        keep_e = min_dr_per_e >= thr
        n_e1 = ak.to_numpy(ak.sum(keep_e, axis=1))
        alt = _fs_label(n_e1, n_m0, n_j0, n_b0)
        changed = base != alt
        res["category_change_if_removed"][str(thr)] = {
            "n_events_changed": int(changed.sum()),
            "n_events_total_fired": int(fired.sum()),
            "fraction_of_fired_events": (int(changed.sum()) / int(fired.sum()))
                                        if int(fired.sum()) else None,
            "n_electrons_removed": int(n_e0.sum() - n_e1.sum()),
            "n_electrons_total": int(n_e0.sum()),
        }
    out["step4_emu_overlap"] = res


def measure_se_threshold_loss(events, electrons, trigobj, out):
    """Step 2 (loss side): among SingleElectron-accepted events, the
    offline pT of the matched leading electron."""
    fired = fire_mask(events, ["HLT_Ele27_WPTight_Gsf"])
    best = trigobj_best_match_pt(electrons, trigobj, TRIGOBJ_ELECTRON_ID, BIT_E_WPTIGHT)
    matched = best > -np.inf
    n_matched = ak.to_numpy(ak.sum(matched, axis=1))
    accepted = fired & (n_matched >= 1)

    # Offline pT of the highest-pT MATCHED electron (the object a threshold
    # would be applied to).
    pt_matched = ak.where(matched, electrons.pt, -np.inf)
    lead_matched_pt = ak.to_numpy(ak.fill_none(ak.max(pt_matched, axis=1), -np.inf))
    vals = lead_matched_pt[accepted]
    vals = vals[np.isfinite(vals)]

    edges = np.arange(25.0, 200.0 + 1e-9, 1.0)
    res = {
        "n_fired": int(fired.sum()),
        "n_accepted_fired_and_matched": int(accepted.sum()),
        "leading_matched_electron_pt_hist": {
            "edges": [float(x) for x in edges], "counts": hist_counts(vals, edges),
            "n_above_200": int((vals >= 200.0).sum()),
        },
        "n_accepted_lost_by_threshold": {
            str(t): int((vals < t).sum()) for t in SE_CANDIDATE_THRESHOLDS
        },
        "n_accepted_with_finite_lead_pt": int(vals.size),
    }
    out["step2_se_threshold_loss"] = res


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--dataset", required=True,
                   choices=["SingleMuon", "DoubleEG", "MuonEG", "SingleElectron"])
    p.add_argument("--era", required=True, choices=["G", "H"])
    p.add_argument("--file-index", type=int, required=True)
    p.add_argument("--output-dir", required=True)
    args = p.parse_args()

    t0 = time.time()
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    label, era = args.dataset, args.era
    rec = record_for(label, era)
    d = dataset_by_label(label)

    branches = (list(drv.BASE_OBJECT_BRANCHES) + list(TRIGOBJ_BRANCHES)
                + list(d.trigger_paths) + [PROBE_ISO_BRANCH])
    if label == "SingleMuon":
        branches += [TAG_PATH, PROBE_PATH]
    branches = sorted(set(branches))

    url, events, counts = read_file(rec, args.file_index, branches)
    muons, electrons, jets = select_objects(events)
    trigobj = zip_trigobj(events)
    # Prove the id-parameterised matcher is still the production one.
    assert_matcher_agrees_with_production(muons, trigobj)

    out = {
        "dataset": label, "era": era, "record_id": rec,
        "file_index": args.file_index, "file_url": url,
        "git_commit": drv.git_commit_hash(drv.REPO_ROOT),
        "match_dr_max": MATCH_DR_MAX,
        "trigger_paths": list(d.trigger_paths),
        **counts,
        "n_selected_electrons": int(ak.sum(ak.num(electrons, axis=1))),
        "n_selected_muons": int(ak.sum(ak.num(muons, axis=1))),
    }

    if label == "SingleMuon":
        measure_turnon(events, muons, electrons, trigobj, out)
    elif label in ("DoubleEG", "MuonEG"):
        measure_leg_matching(label, events, muons, electrons, trigobj, out)
        measure_bit_census(label, events, muons, electrons, trigobj, out)
        if label == "MuonEG":
            measure_emu_overlap(label, events, muons, electrons, jets, trigobj, out)
    elif label == "SingleElectron":
        measure_bit_census(label, events, muons, electrons, trigobj, out)
        measure_se_threshold_loss(events, electrons, trigobj, out)
        measure_emu_overlap(label, events, muons, electrons, jets, trigobj, out)

    out["elapsed_sec"] = round(time.time() - t0, 1)
    name = f"{label}_{era}_file{args.file_index}.json"
    (out_dir / name).write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"[{label} {era} file {args.file_index}] read={counts['n_read']} "
          f"golden={counts['n_after_golden_json']} -> {out_dir / name} "
          f"({out['elapsed_sec']}s)")


if __name__ == "__main__":
    main()
