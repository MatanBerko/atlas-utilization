#!/usr/bin/env python3
"""
H -> ZZ -> 4l, Part A: cheap background-rejection cuts on EXISTING parsed
data (no re-parse). Extends scripts/higgs_4lepton_zz_report.py -- reuses its
load_events/find_z1_z2/four_vector_mass rather than rewriting them.

Diagnosis: 392 candidates in 115-135 GeV vs. CMS's published 8 in 118-130
GeV at 13 TeV, with less luminosity -- a background-rejection problem.
Part A applies the cuts possible with data already on disk:

  A1. Low-mass resonance veto: EVERY opposite-sign pair among the 4 selected
      leptons (any flavor combination, not just the two Z candidates) must
      have mass > 4 GeV -- removes J/psi, Upsilon, and other low-mass
      resonances that can fake a Z candidate pair.
  A2. Ghost/duplicate removal: deltaR > 0.02 between every pair of the 4
      selected leptons -- removes split-track/duplicate-reconstruction
      "ghost" leptons.
  A3. Isolation working-point scan: pfRelIso < 0.35 (current) / 0.20 / 0.15,
      applied to both flavors' own isolation branch.
  A4. Electron ID scan: cutBased >= 2 (loose, current) vs >= 3 (medium) --
      Fall17V2 5-tier scheme (0:fail,1:veto,2:loose,3:medium,4:tight).

NO significance/p-value/sigma computed anywhere. Purely descriptive counts.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from higgs_4lepton_zz_report import (  # noqa: E402
    ELECTRON_MASS, MUON_MASS, Z_MASS, BIN_LO, BIN_HI, N_BINS,
    BUMPNET_MIN_BINS, BUMPNET_MIN_ENTRIES,
    load_events, find_z1_z2, four_vector_mass, write_bumpnet_root,
)

LOW_MASS_VETO_GEV = 4.0
GHOST_DR_MIN = 0.02


def build_selected_leptons(events, muon_iso_max: float, electron_iso_max: float,
                            electron_cutbased_min: int):
    """Same construction as the original script, but with configurable
    isolation thresholds (both flavors) and electron cutBased minimum."""
    import awkward as ak

    e_mask = (events.Electrons_cutBased >= electron_cutbased_min) & \
             (events.Electrons_pfRelIso03_all < electron_iso_max)
    m_mask = (events.Muons_looseId == True) & (events.Muons_pfRelIso04_all < muon_iso_max)  # noqa: E712

    e_pt, e_eta, e_phi = events.Electrons_pt[e_mask], events.Electrons_eta[e_mask], events.Electrons_phi[e_mask]
    e_charge = events.Electrons_charge[e_mask]
    e_flavor = ak.zeros_like(e_pt, dtype=np.int32)

    m_pt, m_eta, m_phi = events.Muons_pt[m_mask], events.Muons_eta[m_mask], events.Muons_phi[m_mask]
    m_charge = events.Muons_charge[m_mask]
    m_flavor = ak.ones_like(m_pt, dtype=np.int32)

    pt = ak.concatenate([e_pt, m_pt], axis=1)
    eta = ak.concatenate([e_eta, m_eta], axis=1)
    phi = ak.concatenate([e_phi, m_phi], axis=1)
    charge = ak.concatenate([e_charge, m_charge], axis=1)
    flavor = ak.concatenate([e_flavor, m_flavor], axis=1)
    mass = ak.where(flavor == 0, ELECTRON_MASS, MUON_MASS)

    return ak.zip({"pt": pt, "eta": eta, "phi": phi, "mass": mass, "charge": charge, "flavor": flavor})


def delta_r(l1, l2) -> float:
    deta = l1["eta"] - l2["eta"]
    dphi = (l1["phi"] - l2["phi"] + np.pi) % (2 * np.pi) - np.pi
    return float(np.hypot(deta, dphi))


def passes_low_mass_veto(leps, min_mass=LOW_MASS_VETO_GEV) -> bool:
    """Every opposite-sign pair (any flavor combo) among the 4 leptons must
    have mass > min_mass. Checks all 6 pairs, not just OSSF/Z candidates."""
    for i in range(4):
        for j in range(i + 1, 4):
            if leps[i]["charge"] * leps[j]["charge"] < 0:
                if four_vector_mass([leps[i], leps[j]]) <= min_mass:
                    return False
    return True


def passes_ghost_removal(leps, min_dr=GHOST_DR_MIN) -> bool:
    for i in range(4):
        for j in range(i + 1, 4):
            if delta_r(leps[i], leps[j]) <= min_dr:
                return False
    return True


def run_selection(events, leptons, apply_low_mass_veto=True, apply_ghost_removal=True):
    """Cut-flow: parse-time selection (input) -> >=4 quality leptons ->
    exactly4/charge0 -> [A1 low-mass veto] -> [A2 ghost removal] ->
    pT thresholds -> valid Z1/Z2 final candidates. Each new stage is kept
    separate so its individual marginal effect is visible."""
    import awkward as ak

    src = np.asarray(events.source_record)
    records = sorted(set(int(r) for r in src))

    def per_record(mask):
        d = {r: int((mask & (src == r)).sum()) for r in records}
        d["combined"] = int(mask.sum())
        return d

    n_sel = ak.num(leptons)
    ge4_mask = np.asarray(n_sel >= 4)
    exact4_mask = np.asarray(n_sel == 4) & ge4_mask
    charge_sum = np.asarray(ak.sum(leptons.charge, axis=1))
    charge0_mask = exact4_mask & (charge_sum == 0)

    cutflow = {
        "records": records,
        "after_parse_time_selection": per_record(np.ones(len(events), dtype=bool)),
        "after_ge4_quality_leptons": per_record(ge4_mask),
        "exactly4_charge0": per_record(charge0_mask),
    }

    survivor_idx = np.nonzero(charge0_mask)[0]
    lep_pt = leptons.pt[charge0_mask]
    lep_eta = leptons.eta[charge0_mask]
    lep_phi = leptons.phi[charge0_mask]
    lep_mass = leptons.mass[charge0_mask]
    lep_charge = leptons.charge[charge0_mask]
    lep_flavor = leptons.flavor[charge0_mask]
    src_surv = src[charge0_mask]
    run_arr = np.asarray(events.run)[charge0_mask]
    lumi_arr = np.asarray(events.luminosityBlock)[charge0_mask]
    evt_arr = np.asarray(events.event)[charge0_mask]

    n_after_lowmass = {r: 0 for r in records}; n_after_lowmass["combined"] = 0
    n_after_ghost = {r: 0 for r in records}; n_after_ghost["combined"] = 0
    n_pt_pass = {r: 0 for r in records}; n_pt_pass["combined"] = 0
    n_final = {r: 0 for r in records}; n_final["combined"] = 0
    candidates = []

    for i in range(len(survivor_idx)):
        leps = [
            {"pt": float(lep_pt[i][j]), "eta": float(lep_eta[i][j]), "phi": float(lep_phi[i][j]),
             "mass": float(lep_mass[i][j]), "charge": int(lep_charge[i][j]), "flavor": int(lep_flavor[i][j])}
            for j in range(4)
        ]
        r = int(src_surv[i])

        if apply_low_mass_veto and not passes_low_mass_veto(leps):
            continue
        n_after_lowmass[r] += 1
        n_after_lowmass["combined"] += 1

        if apply_ghost_removal and not passes_ghost_removal(leps):
            continue
        n_after_ghost[r] += 1
        n_after_ghost["combined"] += 1

        leps.sort(key=lambda l: -l["pt"])
        if not (leps[0]["pt"] > 20.0 and leps[1]["pt"] > 10.0):
            continue
        n_pt_pass[r] += 1
        n_pt_pass["combined"] += 1

        result = find_z1_z2(leps)
        if result is None:
            continue
        n_final[r] += 1
        n_final["combined"] += 1
        candidates.append({
            "source_record": r, "run": int(run_arr[i]), "luminosityBlock": int(lumi_arr[i]),
            "event": int(evt_arr[i]), **result,
        })

    cutflow["after_low_mass_veto"] = n_after_lowmass
    cutflow["after_ghost_removal"] = n_after_ghost
    cutflow["after_pt_thresholds"] = n_pt_pass
    cutflow["final_candidates"] = n_final
    return cutflow, candidates


def summarize(label, cutflow, candidates):
    m4l = np.array([c["m4l"] for c in candidates]) if candidates else np.array([])
    n_115_135 = int(((m4l >= 115) & (m4l <= 135)).sum())
    n_118_130 = int(((m4l >= 118) & (m4l <= 130)).sum())
    z1 = np.array([c["m_z1"] for c in candidates]) if candidates else np.array([])
    n_zpeak = int(((z1 >= 85) & (z1 <= 97)).sum())
    return {
        "label": label,
        "n_final_candidates": cutflow["final_candidates"]["combined"],
        "n_115_135": n_115_135,
        "n_118_130": n_118_130,
        "n_zpeak_85_97": n_zpeak,
        "zpeak_fraction": (n_zpeak / len(z1)) if len(z1) else None,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True, type=Path)
    ap.add_argument("--out-dir", required=True, type=Path)
    args = ap.parse_args()

    out = args.out_dir
    (out / "plots").mkdir(parents=True, exist_ok=True)
    (out / "histograms").mkdir(parents=True, exist_ok=True)

    events, n_events, file_rows = load_events(args.run_dir)
    print(f"loaded {n_events:,} events (post parse-time selection + dedup) from {len(file_rows)} chunk file(s)")

    # ---- Primary Part A result: current WP (iso<0.35, electron cutBased>=2) + A1 + A2 ----
    leptons_current = build_selected_leptons(events, muon_iso_max=0.35, electron_iso_max=0.35, electron_cutbased_min=2)

    print("\n=== BASELINE (no A1/A2, current WP -- reproduces the 2,216-candidate result) ===")
    cf_baseline, cand_baseline = run_selection(events, leptons_current, apply_low_mass_veto=False, apply_ghost_removal=False)
    s_baseline = summarize("baseline (current WP, no A1/A2)", cf_baseline, cand_baseline)
    print(json.dumps(s_baseline, indent=2))

    print("\n=== CLEANED (current WP + A1 low-mass veto + A2 ghost removal) ===")
    cf_cleaned, cand_cleaned = run_selection(events, leptons_current, apply_low_mass_veto=True, apply_ghost_removal=True)
    s_cleaned = summarize("cleaned (current WP + A1 + A2)", cf_cleaned, cand_cleaned)
    print(json.dumps(s_cleaned, indent=2))
    print(json.dumps(cf_cleaned, indent=2))

    # ---- A3: isolation WP scan (electron cutBased fixed at current, >=2) ----
    print("\n=== A3: isolation working-point scan (electron cutBased>=2 fixed, A1+A2 applied) ===")
    iso_scan = []
    for iso_wp in (0.35, 0.20, 0.15):
        leps = build_selected_leptons(events, muon_iso_max=iso_wp, electron_iso_max=iso_wp, electron_cutbased_min=2)
        cf, cand = run_selection(events, leps, apply_low_mass_veto=True, apply_ghost_removal=True)
        s = summarize(f"iso<{iso_wp}", cf, cand)
        iso_scan.append(s)
        print(json.dumps(s, indent=2))

    # ---- A4: electron ID scan (isolation fixed at current, 0.35) ----
    print("\n=== A4: electron cutBased scan (iso<0.35 fixed, A1+A2 applied) ===")
    eid_scan = []
    for eid_wp, name in ((2, "loose"), (3, "medium")):
        leps = build_selected_leptons(events, muon_iso_max=0.35, electron_iso_max=0.35, electron_cutbased_min=eid_wp)
        cf, cand = run_selection(events, leps, apply_low_mass_veto=True, apply_ghost_removal=True)
        s = summarize(f"electron cutBased>={eid_wp} ({name})", cf, cand)
        eid_scan.append(s)
        print(json.dumps(s, indent=2))

    # ---- Save everything ----
    channels_cleaned = {ch: sum(1 for c in cand_cleaned if c["channel"] == ch) for ch in ("4mu", "4e", "2e2mu")}
    stats = {
        "n_parsed_events": n_events,
        "baseline_summary": s_baseline,
        "baseline_cutflow": cf_baseline,
        "cleaned_summary": s_cleaned,
        "cleaned_cutflow": cf_cleaned,
        "cleaned_candidates_by_channel": channels_cleaned,
        "iso_scan": iso_scan,
        "electron_id_scan": eid_scan,
        "cleaned_candidates": cand_cleaned,
    }
    (out / "partA_stats.json").write_text(json.dumps(stats, indent=2))

    if cand_cleaned:
        masses = np.array([c["m4l"] for c in cand_cleaned])
        edges3 = np.linspace(BIN_LO, BIN_HI, N_BINS + 1)
        counts3, _ = np.histogram(masses, bins=edges3)
        write_bumpnet_root(edges3, counts3, "mass_l0l1l2l3_cat_4lx_0jx_0gx_0tx_0bx_width_3.0",
                            out / "histograms" / "partA_cleaned_4l_combined_3gev_bumpnet.root")
        n4 = int(round((BIN_HI - BIN_LO) / 4.0))
        edges4 = np.linspace(BIN_LO, BIN_HI, n4 + 1)
        counts4, _ = np.histogram(masses, bins=edges4)
        write_bumpnet_root(edges4, counts4, "mass_l0l1l2l3_cat_4lx_0jx_0gx_0tx_0bx_width_4.0",
                            out / "histograms" / "partA_cleaned_4l_combined_4gev_bumpnet.root")
        print(f"\n3 GeV hist: {counts3.sum()} entries / {len(counts3)} bins "
              f"(bar: bins>{BUMPNET_MIN_BINS}={len(counts3)>BUMPNET_MIN_BINS}, "
              f"entries>={BUMPNET_MIN_ENTRIES}={counts3.sum()>=BUMPNET_MIN_ENTRIES})")
        print(f"4 GeV hist: {counts4.sum()} entries / {len(counts4)} bins "
              f"(bar: bins>{BUMPNET_MIN_BINS}={len(counts4)>BUMPNET_MIN_BINS}, "
              f"entries>={BUMPNET_MIN_ENTRIES}={counts4.sum()>=BUMPNET_MIN_ENTRIES})")

    # 115-135 GeV candidate table
    rows = sorted((c for c in cand_cleaned if 115 <= c["m4l"] <= 135), key=lambda c: c["m4l"])
    with open(out / "partA_115_135_candidates.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["m4l_gev", "channel", "m_z1_gev", "m_z2_gev", "source_record", "run", "luminosityBlock", "event"])
        for c in rows:
            w.writerow([f"{c['m4l']:.3f}", c["channel"], f"{c['m_z1']:.3f}", f"{c['m_z2']:.3f}",
                        c["source_record"], c["run"], c["luminosityBlock"], c["event"]])
    print(f"\n115-135 GeV: {len(rows)} candidates -> partA_115_135_candidates.csv")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
