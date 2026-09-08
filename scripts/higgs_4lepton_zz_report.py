#!/usr/bin/env python3
"""
H -> ZZ -> 4l rediscovery exercise (analysis/higgs-4lepton-zz).

Reads parsed Electron/Muon collections (already loose-pT/eta-cut and
combined>=4-filtered at PARSE time -- see
config.cms_higgs_4lepton_validation.yaml / config.cms_higgs_4lepton_fullscale.yaml),
applies the tighter per-lepton quality cuts and the Z1/Z2 pairing logic
described below, and produces the cut-flow, channel breakdown, mass
histograms (BumpNet ROOT format), and plots.

Per-lepton "selected" requirements (pT/eta already enforced at parse time;
only ID/isolation applied here):
  - Muons:     looseId == True, pfRelIso04_all < 0.35
  - Electrons: cutBased >= 2  ***NOTE: this is the "loose" tier, NOT 1.***
    Electron_cutBased on this UL2016 NanoAODv9 production is the Fall17V2
    5-tier scheme (0:fail, 1:veto, 2:loose, 3:medium, 4:tight), confirmed by
    reading the branch's own ROOT title on a real file (record 30521) before
    use: "cut-based ID Fall17 V2 (0:fail, 1:veto, 2:loose, 3:medium, 4:tight)".
    This is DIFFERENT from the photon cutBased scheme already used elsewhere
    in this project (Fall17V2, 4-tier, 0:fail/1:loose/2:medium/3:tight, no
    veto tier) -- do not reuse that convention here.

Event requirements: exactly 4 selected leptons (any e/mu mix), total charge
0, leading pT>20 GeV, subleading pT>10 GeV.

Z1/Z2 pairing (standard CMS H->ZZ->4l convention), implemented in
find_z1_z2() below: form every opposite-sign-same-flavor (OSSF) way to split
the 4 leptons into two pairs; among partitions where BOTH pairs are OSSF,
Z1 is whichever pair's mass is closest to 91.1876 GeV (require
40<mZ1<120 GeV), Z2 is the other pair (require 12<mZ2<120 GeV). No valid
OSSF split -> event rejected. This is genuinely a small-N combinatorial
problem (at most 3 partitions x 2 orderings per event) so it is implemented
as a plain per-event Python function for clarity, run only on the
(typically small) set of events that already pass the exactly-4/charge-0/pT
cuts -- not vectorized, deliberately, for readability and easy review.

NO significance/p-value/sigma is computed anywhere in this script. This
script only counts and plots what is observed.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

ELECTRON_MASS = 0.000511
MUON_MASS = 0.105658
Z_MASS = 91.1876

# Real, per-record dataset totals verified individually against
# opendata.cern.ch before use (see reports/higgs_4lepton_zz/summary.md
# Step 1) -- used only to anchor the "raw events" end of the cut-flow funnel;
# not recomputed from parsed output (parsed output already only contains the
# >=4-loose-lepton, post-dedup survivors).
RECORD_INFO = {
    30521: {"name": "DoubleEG Run2016G", "files": 47, "raw_events": 78_797_031},
    30554: {"name": "DoubleEG Run2016H", "files": 86, "raw_events": 85_388_673},
    30522: {"name": "DoubleMuon Run2016G", "files": 29, "raw_events": 45_235_604},
    30555: {"name": "DoubleMuon Run2016H", "files": 28, "raw_events": 48_912_812},
    30528: {"name": "MuonEG Run2016G", "files": 29, "raw_events": 33_854_612},
    30561: {"name": "MuonEG Run2016H", "files": 19, "raw_events": 29_236_516},
}

BIN_LO, BIN_HI = 70.0, 180.0
N_BINS = 37  # (180-70)/37 = 2.973 GeV/bin, "~3 GeV" per the task; exact 70-180 range kept
BUMPNET_MIN_BINS = 30
BUMPNET_MIN_ENTRIES = 100


def load_events(run_dir: Path):
    """Read every parsed chunk in run_dir/parsed_data, return concatenated
    awkward array with Electrons_*/Muons_*/source_record/event-id fields."""
    import awkward as ak
    import uproot

    parsed = sorted((run_dir / "parsed_data").glob("*.root"))
    if not parsed:
        raise FileNotFoundError(f"no parsed .root chunks in {run_dir/'parsed_data'}")

    branches = [
        "Electrons_pt", "Electrons_eta", "Electrons_phi", "Electrons_mass",
        "Electrons_charge", "Electrons_pfRelIso03_all", "Electrons_cutBased",
        "Muons_pt", "Muons_eta", "Muons_phi", "Muons_mass",
        "Muons_charge", "Muons_pfRelIso04_all", "Muons_looseId",
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


def build_selected_leptons(events):
    """Apply per-lepton quality cuts (ID + isolation only -- pT/eta already
    enforced at parse time) and merge Electrons+Muons into one per-event
    jagged 'leptons' collection carrying pt/eta/phi/mass/charge/flavor.
    Returns (leptons, n_events_with_ge4_selected)."""
    import awkward as ak

    e_mask = (events.Electrons_cutBased >= 2) & (events.Electrons_pfRelIso03_all < 0.35)
    m_mask = (events.Muons_looseId == True) & (events.Muons_pfRelIso04_all < 0.35)  # noqa: E712

    e_pt, e_eta, e_phi = events.Electrons_pt[e_mask], events.Electrons_eta[e_mask], events.Electrons_phi[e_mask]
    e_charge = events.Electrons_charge[e_mask]
    e_flavor = ak.zeros_like(e_pt, dtype=np.int32)  # 0 = electron

    m_pt, m_eta, m_phi = events.Muons_pt[m_mask], events.Muons_eta[m_mask], events.Muons_phi[m_mask]
    m_charge = events.Muons_charge[m_mask]
    m_flavor = ak.ones_like(m_pt, dtype=np.int32)  # 1 = muon

    pt = ak.concatenate([e_pt, m_pt], axis=1)
    eta = ak.concatenate([e_eta, m_eta], axis=1)
    phi = ak.concatenate([e_phi, m_phi], axis=1)
    charge = ak.concatenate([e_charge, m_charge], axis=1)
    flavor = ak.concatenate([e_flavor, m_flavor], axis=1)
    mass = ak.where(flavor == 0, ELECTRON_MASS, MUON_MASS)

    leptons = ak.zip(
        {"pt": pt, "eta": eta, "phi": phi, "mass": mass, "charge": charge, "flavor": flavor}
    )
    return leptons


def four_vector_mass(leps):
    """Invariant mass of a small list of lepton dicts (pt/eta/phi/mass)."""
    import vector
    vector.register_awkward()
    vecs = [vector.obj(pt=l["pt"], eta=l["eta"], phi=l["phi"], mass=l["mass"]) for l in leps]
    total = vecs[0]
    for v in vecs[1:]:
        total = total + v
    return float(total.mass)


def find_z1_z2(leps):
    """
    leps: list of exactly 4 lepton dicts (pt, eta, phi, mass, charge, flavor).
    Returns dict with z1/z2 indices+masses+4l mass+channel, or None if no
    valid OSSF split exists, or the mass windows aren't satisfied.
    """
    partitions = [((0, 1), (2, 3)), ((0, 2), (1, 3)), ((0, 3), (1, 2))]

    def is_ossf(i, j):
        return leps[i]["flavor"] == leps[j]["flavor"] and leps[i]["charge"] * leps[j]["charge"] < 0

    candidates = []
    for pair_a, pair_b in partitions:
        for z_pair, other_pair in ((pair_a, pair_b), (pair_b, pair_a)):
            if not (is_ossf(*z_pair) and is_ossf(*other_pair)):
                continue
            m_z = four_vector_mass([leps[z_pair[0]], leps[z_pair[1]]])
            m_other = four_vector_mass([leps[other_pair[0]], leps[other_pair[1]]])
            candidates.append((abs(m_z - Z_MASS), z_pair, other_pair, m_z, m_other))

    if not candidates:
        return None

    candidates.sort(key=lambda c: c[0])
    _, z1_pair, z2_pair, m_z1, m_z2 = candidates[0]

    if not (40.0 < m_z1 < 120.0):
        return None
    if not (12.0 < m_z2 < 120.0):
        return None

    n_e = sum(1 for l in leps if l["flavor"] == 0)
    n_m = 4 - n_e
    channel = {4: "4e", 0: "4mu"}.get(n_e, "2e2mu")

    m4l = four_vector_mass(leps)
    return {
        "m4l": m4l, "m_z1": m_z1, "m_z2": m_z2, "channel": channel,
        "z1_pair": z1_pair, "z2_pair": z2_pair,
    }


def run_selection(events, leptons):
    """Full per-record + combined cut-flow, returns (cutflow dict, candidates list)."""
    import awkward as ak

    src = np.asarray(events.source_record)
    records = sorted(set(int(r) for r in src))

    n_after_parse = {r: int((src == r).sum()) for r in records}
    n_after_parse["combined"] = len(events)

    n_sel = ak.num(leptons)
    ge4_mask = np.asarray(n_sel >= 4)
    n_ge4 = {r: int((ge4_mask & (src == r)).sum()) for r in records}
    n_ge4["combined"] = int(ge4_mask.sum())

    exact4_mask_full = np.asarray(n_sel == 4)
    combined_exact4 = exact4_mask_full & ge4_mask  # ge4_mask implies exact4 subset anyway, kept explicit

    charge_sum = np.asarray(ak.sum(leptons.charge, axis=1))
    charge0_mask = combined_exact4 & (charge_sum == 0)
    n_charge0 = {r: int((charge0_mask & (src == r)).sum()) for r in records}
    n_charge0["combined"] = int(charge0_mask.sum())

    # pT threshold stage + Z1/Z2 stage: only evaluated on the (small)
    # exactly-4/charge-0 survivor set, via a plain per-event Python loop
    # (see find_z1_z2 docstring for why this is deliberately not vectorized).
    survivor_idx = np.nonzero(charge0_mask)[0]
    lep_pt = leptons.pt[charge0_mask]
    lep_eta = leptons.eta[charge0_mask]
    lep_phi = leptons.phi[charge0_mask]
    lep_mass = leptons.mass[charge0_mask]
    lep_charge = leptons.charge[charge0_mask]
    lep_flavor = leptons.flavor[charge0_mask]
    src_surv = src[charge0_mask]
    run_arr = np.asarray(events.run)[charge0_mask] if "run" in events.fields else np.zeros(len(survivor_idx), dtype=np.int64)
    lumi_arr = np.asarray(events.luminosityBlock)[charge0_mask] if "luminosityBlock" in events.fields else np.zeros_like(run_arr)
    evt_arr = np.asarray(events.event)[charge0_mask] if "event" in events.fields else np.zeros_like(run_arr)

    n_pt_pass = {r: 0 for r in records}
    n_pt_pass["combined"] = 0
    n_final = {r: 0 for r in records}
    n_final["combined"] = 0
    candidates = []

    for i in range(len(survivor_idx)):
        pts = np.asarray(lep_pt[i])
        order = np.argsort(-pts)
        leps = [
            {
                "pt": float(lep_pt[i][j]), "eta": float(lep_eta[i][j]),
                "phi": float(lep_phi[i][j]), "mass": float(lep_mass[i][j]),
                "charge": int(lep_charge[i][j]), "flavor": int(lep_flavor[i][j]),
            }
            for j in order
        ]
        r = int(src_surv[i])
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
            "source_record": r,
            "run": int(run_arr[i]), "luminosityBlock": int(lumi_arr[i]), "event": int(evt_arr[i]),
            **result,
        })

    cutflow = {
        "records": records,
        "after_parse_time_selection": n_after_parse,
        "after_ge4_quality_leptons": n_ge4,
        "exactly4_charge0": n_charge0,
        "after_pt_thresholds": n_pt_pass,
        "final_candidates": n_final,
    }
    return cutflow, candidates


def build_hist(masses, lo=BIN_LO, hi=BIN_HI, nbins=N_BINS):
    edges = np.linspace(lo, hi, nbins + 1)
    counts, _ = np.histogram(masses, bins=edges)
    return edges, counts


def write_bumpnet_root(edges, counts, name, out_root: Path):
    import uproot
    out_root.parent.mkdir(parents=True, exist_ok=True)
    with uproot.recreate(str(out_root)) as f:
        f[name] = (counts, edges)
    return name


def main() -> int:
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

    leptons = build_selected_leptons(events)
    cutflow, candidates = run_selection(events, leptons)

    stats = {
        "label": args.label,
        "run_dir": str(args.run_dir),
        "n_parsed_events": n_events,
        "cutflow": cutflow,
        "n_candidates": len(candidates),
        "candidates_by_channel": {
            ch: sum(1 for c in candidates if c["channel"] == ch)
            for ch in ("4mu", "4e", "2e2mu")
        },
        "candidates": candidates,
    }
    (out / f"{args.label}_stats.json").write_text(json.dumps(stats, indent=2))

    print(json.dumps({k: v for k, v in stats.items() if k != "candidates"}, indent=2))

    if candidates:
        masses = np.array([c["m4l"] for c in candidates])
        edges, counts = build_hist(masses)
        name = write_bumpnet_root(
            edges, counts, "mass_l0l1l2l3_cat_4lx_0jx_0gx_0tx_0bx_width_3.0",
            out / "histograms" / f"{args.label}_4l_combined_bumpnet.root",
        )
        print(f"combined histogram: {counts.sum()} entries, {len(counts)} bins -> {name}")

        for ch, comp in (("4mu", "0e4mx"), ("4e", "4e0mx"), ("2e2mu", "2e2mx")):
            ch_masses = np.array([c["m4l"] for c in candidates if c["channel"] == ch])
            if len(ch_masses) == 0:
                continue
            e2, c2 = build_hist(ch_masses)
            nm = write_bumpnet_root(
                e2, c2, f"mass_l0l1l2l3_cat_{comp}_0jx_0gx_0tx_0bx_width_3.0",
                out / "histograms" / f"{args.label}_4l_{ch}_bumpnet.root",
            )
            print(f"{ch} histogram: {c2.sum()} entries, {len(c2)} bins -> {nm}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
