#!/usr/bin/env python3
"""
H -> ZZ -> 4l, Part B: standard CMS primary-vertex (impact-parameter)
compatibility cuts, added on top of Part A's selection. Extends
scripts/higgs_4lepton_clean_report.py -- reuses its passes_low_mass_veto/
passes_ghost_removal/run_selection/write_bumpnet_root rather than rewriting
them; only build_selected_leptons is extended (new IP mask) and load_events
is extended (three new branches per flavor).

B1/B2: sip3d < 4, |dxy| < 0.5 cm, |dz| < 1.0 cm -- confirmed on a real
UL2016 NanoAODv9 file (record 30521) via the branches' own ROOT titles
before use (see services/parsing/schemas.py's comment for the exact titles
and the sip3d "in cm" title inconsistency noted and resolved there: sip3d
is used as the standard dimensionless significance, per its own
description and universal CMS convention, despite that copy-paste artifact
in Electron_sip3d's title). These are the standard CMS H->ZZ->4l
primary-vertex compatibility cuts, suppressing leptons from b/c-hadron
decays -- the dominant reducible background (Z+jets, ttbar, Zbb).

Per instruction, isolation and electron ID are deliberately NOT tightened
here (kept at Part A's iso<0.35, cutBased>=2) so the impact-parameter
cuts' effect can be attributed cleanly.

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
from higgs_4lepton_zz_report import ELECTRON_MASS, MUON_MASS, BIN_LO, BIN_HI, N_BINS, write_bumpnet_root  # noqa: E402
from higgs_4lepton_clean_report import passes_low_mass_veto, passes_ghost_removal  # noqa: E402
from higgs_4lepton_zz_report import find_z1_z2  # noqa: E402

# Standard CMS H->ZZ->4l primary-vertex compatibility working point.
SIP3D_MAX = 4.0
DXY_MAX_CM = 0.5
DZ_MAX_CM = 1.0

ISO_WP = 0.35          # Part A's working point, unchanged (deliberately not tightened)
ELECTRON_CUTBASED_MIN = 2  # loose, unchanged


def load_events(run_dir: Path):
    """Same chunk-loading pattern as the earlier scripts, extended with the
    three new impact-parameter branches per flavor."""
    import awkward as ak
    import uproot

    parsed = sorted((run_dir / "parsed_data").glob("*.root"))
    if not parsed:
        raise FileNotFoundError(f"no parsed .root chunks in {run_dir/'parsed_data'}")

    branches = [
        "Electrons_pt", "Electrons_eta", "Electrons_phi", "Electrons_mass",
        "Electrons_charge", "Electrons_pfRelIso03_all", "Electrons_cutBased",
        "Electrons_sip3d", "Electrons_dxy", "Electrons_dz",
        "Muons_pt", "Muons_eta", "Muons_phi", "Muons_mass",
        "Muons_charge", "Muons_pfRelIso04_all", "Muons_looseId",
        "Muons_sip3d", "Muons_dxy", "Muons_dz",
        "source_record", "run", "luminosityBlock", "event",
    ]
    parts = []
    n_events = 0
    file_rows = []
    for chunk in parsed:
        tree = uproot.open(chunk)["events"]
        available = [b for b in branches if b in tree.keys()]
        arr = tree.arrays(available, library="ak")
        n_events += len(arr)
        file_rows.append({"file": chunk.name, "events": len(arr)})
        parts.append(arr)
    events = ak.concatenate(parts) if len(parts) > 1 else parts[0]
    return events, n_events, file_rows


def build_selected_leptons(events, use_sip3d=True, use_dxy=True, use_dz=True):
    """Part A's quality selection (iso<0.35, electron cutBased>=2, muon
    looseId) with the Part B impact-parameter cuts ANDed in, each
    independently toggleable so their individual effect can be isolated."""
    import awkward as ak

    e_mask = (events.Electrons_cutBased >= ELECTRON_CUTBASED_MIN) & \
             (events.Electrons_pfRelIso03_all < ISO_WP)
    m_mask = (events.Muons_looseId == True) & (events.Muons_pfRelIso04_all < ISO_WP)  # noqa: E712

    if use_sip3d:
        e_mask = e_mask & (events.Electrons_sip3d < SIP3D_MAX)
        m_mask = m_mask & (events.Muons_sip3d < SIP3D_MAX)
    if use_dxy:
        e_mask = e_mask & (abs(events.Electrons_dxy) < DXY_MAX_CM)
        m_mask = m_mask & (abs(events.Muons_dxy) < DXY_MAX_CM)
    if use_dz:
        e_mask = e_mask & (abs(events.Electrons_dz) < DZ_MAX_CM)
        m_mask = m_mask & (abs(events.Muons_dz) < DZ_MAX_CM)

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


def run_selection(events, leptons):
    """Identical structure/order to higgs_4lepton_clean_report.run_selection
    (exactly4/charge0 -> A1 low-mass veto -> A2 ghost removal -> pT
    thresholds -> Z1/Z2), reproduced here so this script has no import-time
    dependency beyond the two vetting functions themselves."""
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

        if not passes_low_mass_veto(leps):
            continue
        n_after_lowmass[r] += 1
        n_after_lowmass["combined"] += 1

        if not passes_ghost_removal(leps):
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
    z1 = np.array([c["m_z1"] for c in candidates]) if candidates else np.array([])
    n_zpeak = int(((z1 >= 85) & (z1 <= 97)).sum())
    return {
        "label": label,
        "n_final_candidates": cutflow["final_candidates"]["combined"],
        "n_115_135": int(((m4l >= 115) & (m4l <= 135)).sum()),
        "n_118_130": int(((m4l >= 118) & (m4l <= 130)).sum()),
        "n_zpeak_85_97": n_zpeak,
        "zpeak_fraction": (n_zpeak / len(z1)) if len(z1) else None,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True, type=Path)
    ap.add_argument("--out-dir", required=True, type=Path)
    ap.add_argument("--label", default="run")
    args = ap.parse_args()

    out = args.out_dir
    (out / "plots").mkdir(parents=True, exist_ok=True)
    (out / "histograms").mkdir(parents=True, exist_ok=True)

    events, n_events, file_rows = load_events(args.run_dir)
    print(f"[{args.label}] loaded {n_events:,} events (post parse-time selection + dedup) "
          f"from {len(file_rows)} chunk file(s)")

    # ---- IP-cut scan: no-IP baseline (=Part A), sip3d-only, dxy-only,
    # dz-only, all-three-combined -- each independently vs. the SAME Part A
    # baseline selection, so the marginal effect of each is not confounded
    # by cut ORDER (a sequential cut-flow would let whichever cut runs
    # first "use up" correlated rejection power).
    variants = {
        "no_ip_cuts (Part A baseline)": dict(use_sip3d=False, use_dxy=False, use_dz=False),
        "sip3d_only": dict(use_sip3d=True, use_dxy=False, use_dz=False),
        "dxy_only": dict(use_sip3d=False, use_dxy=True, use_dz=False),
        "dz_only": dict(use_sip3d=False, use_dxy=False, use_dz=True),
        "all_three_combined (PRIMARY)": dict(use_sip3d=True, use_dxy=True, use_dz=True),
    }

    scan_results = {}
    primary_cutflow = None
    primary_candidates = None
    for name, kwargs in variants.items():
        leps = build_selected_leptons(events, **kwargs)
        cf, cand = run_selection(events, leps)
        s = summarize(name, cf, cand)
        # Per-record final_candidates too (not just the combined summary), so
        # the sip3d/dxy/dz-only scan can be shown per-record, not just
        # combined -- same reasoning as the primary cut-flow.
        scan_results[name] = {
            "summary": s,
            "final_candidates_per_record": cf["final_candidates"],
            "cutflow": cf,
        }
        print(f"\n=== {name} ===")
        print(json.dumps(s, indent=2))
        if "PRIMARY" in name:
            primary_cutflow, primary_candidates = cf, cand

    channels = {ch: sum(1 for c in primary_candidates if c["channel"] == ch) for ch in ("4mu", "4e", "2e2mu")}
    print("\nPRIMARY candidates by channel:", channels)

    stats = {
        "n_parsed_events": n_events,
        "ip_cut_scan": {
            k: {"summary": v["summary"], "final_candidates_per_record": v["final_candidates_per_record"]}
            for k, v in scan_results.items()
        },
        "primary_cutflow": primary_cutflow,
        "primary_candidates_by_channel": channels,
        "primary_candidates": primary_candidates,
    }
    (out / f"{args.label}_partB_stats.json").write_text(json.dumps(stats, indent=2))

    if primary_candidates:
        masses = np.array([c["m4l"] for c in primary_candidates])
        edges = np.linspace(BIN_LO, BIN_HI, N_BINS + 1)
        counts, _ = np.histogram(masses, bins=edges)
        write_bumpnet_root(edges, counts, "mass_l0l1l2l3_cat_4lx_0jx_0gx_0tx_0bx_width_3.0",
                            out / "histograms" / f"{args.label}_partB_4l_combined_bumpnet.root")
        print(f"\n3 GeV combined histogram (primary, all-3-IP-cuts): {counts.sum()} entries / {len(counts)} bins")

    rows = sorted((c for c in primary_candidates if 115 <= c["m4l"] <= 135), key=lambda c: c["m4l"])
    with open(out / f"{args.label}_partB_115_135_candidates.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["m4l_gev", "channel", "m_z1_gev", "m_z2_gev", "source_record", "run", "luminosityBlock", "event"])
        for c in rows:
            w.writerow([f"{c['m4l']:.3f}", c["channel"], f"{c['m_z1']:.3f}", f"{c['m_z2']:.3f}",
                        c["source_record"], c["run"], c["luminosityBlock"], c["event"]])
    print(f"115-135 GeV: {len(rows)} candidates -> {args.label}_partB_115_135_candidates.csv")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
