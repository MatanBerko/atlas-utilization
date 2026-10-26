#!/usr/bin/env python
"""Write one README per delivered file (full run 25 Oct 2026) from the build
summaries in ../evidence/. Values and their file:line sources: MANIFEST.md.

    python studies/fullrun_20261025/delivery/make_readmes.py
"""
from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
EV = HERE.parent / "evidence"
OUT = HERE / "readmes"
PIN = "75b399e2dfdacc50affd4e2c78bc865b12f000cc"
PREFIX = "CMS_Run2016GH"
L = "16p393invfb"
T = "prod2026-10-25"
DS = "DoubleMuon-SingleMuon-DoubleEG-MuonEG-SingleElectron"

SELECTION = """OBJECT SELECTION (identical for data and MC)
  Muons:     pT > 25 GeV, |eta| < 2.4, CMS Loose ID (Muon_looseId),
             isolation pfRelIso04_all < 0.15
  Electrons: pT > 25 GeV, |eta| < 2.5, cut-based ID >= 2 (Loose or tighter,
             Fall17 V2: 0 fail, 1 veto, 2 loose, 3 medium, 4 tight)
  Jets:      pT > 30 GeV, |eta| < 2.5, tight jet ID, removed within dR < 0.4
             of a selected lepton
  b-jets:    DeepJet Jet_btagDeepFlavB > 0.2489 (UL2016 postVFP medium WP)
  e-mu overlap removal: every selected electron within dR < 0.12 of a
             selected muon is removed, before trigger matching and before the
             final state is decided.
  (Loose muon and electron IDs since 24 Oct 2026, Maryna; before that the
   deliveries used medium IDs.)"""

TRIGGERS = """TRIGGERS AND OFFLINE THRESHOLDS (trigger-object match dR < 0.1)
  DoubleMuon     HLT_Mu17_TrkIsoVVL_Mu8_TrkIsoVVL_DZ OR ..._TkMu8_..._DZ;
                 >= 2 matched muons, leading > 17 GeV
  SingleMuon     HLT_IsoMu24 OR HLT_IsoTkMu24; >= 1 matched muon > 24 GeV
  DoubleEG       HLT_Ele23_Ele12_CaloIdL_TrackIdL_IsoVL_DZ; 2 matched
                 electrons, BOTH offline > 30 GeV
  MuonEG         HLT_Mu23_TrkIsoVVL_Ele12_..._DZ OR HLT_Mu8_TrkIsoVVL_Ele23_..._DZ;
                 >= 1 selected muon, electron leg 12 / 23 GeV by path
  SingleElectron HLT_Ele27_WPTight_Gsf; matched electron, offline > 32 GeV
  De-duplication (each collision counted once), highest priority first:
    DoubleMuon > SingleMuon > DoubleEG > MuonEG > SingleElectron
  (DoubleMuon contributes all its accepted events, every other dataset only
   the events no higher-priority dataset accepted.)
  MC: no de-duplication; an MC event is kept if ANY of the five dataset
  acceptances above holds (the same functions as data)."""

BUILD = """FINAL STATES AND POST-PROCESSING
  * Multiplicity rule of upstream #40 (5fbf1ef): at most 4 objects per final
    state. Events with electrons + muons + b-jets > 4 are rejected; light
    jets fill the free slots (light jets in the name = min(jets,
    4 - (e + m + b))); the masses use the kept leading-pT jets.
  * >= 100 events per final state, applied once over all files combined.
  * Same-flavour dilepton masses below 110 GeV are removed (Z-peak cut);
    masses above 10,000 GeV are removed.
  * Peak removal: entries below the rightmost highest peak are removed, and
    the outlier tail is split off at the first empty bin (upstream
    post-processing).
  * Fixed binning: 0-10,000 GeV in 10 GeV bins (1000 bins).
  Names: ROI_mass_<combination>_cat_<n>ex_<n>mx_<n>jx_<n>bx_width_10.0"""

DATA_LUMI = """DATA AND LUMINOSITY
  CMS Open Data, Run2016G + Run2016H, UL2016 MiniAODv2 NanoAODv9, five primary
  datasets (541 files: DoubleMuon 57, SingleMuon 152, DoubleEG 133,
  MuonEG 48, SingleElectron 151). Only certified luminosity sections are used
  (golden JSON Cert_271036-284044_13TeV_Legacy2016_Collisions16_JSON).
  Integrated luminosity 16.393 fb^-1 (G 7.653 + H 8.740; the documented value
  used for the MC normalisation)."""

MISSING = """MISSING FROM THE MC (important when comparing data with MC)
  The MC contains only the 13 samples listed. NOT included:
    - W+jets
    - QCD multijet
    - single top t-channel and s-channel (only tW is included)
    - fully hadronic tt-bar (only dileptonic and semileptonic)
    - smaller processes (e.g. tribosons and other rare processes)
  So data can exceed MC wherever these contribute (single-lepton + jets
  final states in particular)."""

MC_WEIGHTS = """MC WEIGHTS
  Each event: genWeight x L1PreFiringWeight_Nom x sigma_eff[pb] x 1000 x
  16.393 / Sigma_w, where Sigma_w is the sum of genWeight over all files of
  the sample that pass the per-file check |sum genWeight - genEventSumw| /
  genEventSumw <= 1e-6 (a failing file is excluded with its Sigma_w).
  One file excluded: ZZTo4L (75589) file 98 (3.7 % of its events missing).
  Histograms are TH1D with Sumw2 (bin errors = sqrt(sum w^2)). Negative bin
  contents can occur (negative generator weights in the NLO samples)."""


def table_samples(samples):
    rows = ["  record  sample                                     sigma_eff [pb]  files  histograms"]
    for rid, s in sorted(samples.items()):
        rows.append(f"  {rid}   {s['physics_short']:<42s} {s['cross_section_pb_sigma_eff']:>12g}  "
                    f"{s['n_files_included']:>5d}  {s['histograms_n']:>5d}")
    return "\n".join(rows)


def common_tail():
    return (f"\nPRODUCTION\n  Produced 25-26 Oct 2026 on the Weizmann WIPP cluster from the code at commit\n"
            f"  {PIN} (github.com/MatanBerko/atlas-utilization, branch\n"
            f"  run/cms-fullrun-20261025). Checksums: SHA256SUMS.txt. Sources of every\n"
            f"  value: MANIFEST.md.\n")


def main():
    OUT.mkdir(exist_ok=True)
    bs = json.loads((EV / "final_data" / "build_summary_rare4_four_dataset.json").read_text())
    mc = json.loads((EV / "final_mc" / "build_report_summary.json").read_text())
    n_d = bs["n_delivered_histograms"]
    n_fs = bs["n_distinct_final_state_categories_delivered"]
    pooled = "\n".join(f"    {k:<15s} {v['n_events_pooled_rare4']:>12,} events ({v['contribution']})"
                       for k, v in bs["per_dataset_event_counts"].items())
    written = []
    for kind, fname, what in (
            ("cropped", f"{PREFIX}_{DS}_{L}_{T}_data_bumpnet_cropped.root",
             "THE FILE FOR BUMPNET. Every histogram is cropped to its first..last filled bin\n"
             "  (the first bin is never empty, as BumpNet requires)."),
            ("uncropped", f"{PREFIX}_{DS}_{L}_{T}_data_bumpnet_uncropped.root",
             "The same histograms UNCROPPED, on the full 0-10,000 GeV grid. For checks and\n"
             "  plots only; BumpNet uses the cropped file.")):
        txt = (f"{fname}\n{'=' * len(fname)}\n\nCMS 2016 collision DATA, Run G+H, 16.393 fb^-1, five datasets.\n"
               f"  {what}\n\nCONTENTS\n  {n_d} histograms (TH1F, event counts) in {n_fs} final states.\n"
               f"  Events pooled per dataset after de-duplication:\n{pooled}\n\n"
               f"{DATA_LUMI}\n\n{SELECTION}\n\n{TRIGGERS}\n\n{BUILD}\n{common_tail()}")
        (OUT / f"{fname}.README.txt").write_text(txt)
        written.append(fname)
    samples = mc["samples"]
    n_sum = mc["summed_sm"]["n_histograms"]
    fname = f"{PREFIX}_MC-summedSM-13samples_{L}_{T}_mc.root"
    txt = (f"{fname}\n{'=' * len(fname)}\n\nCMS 2016 SIMULATION (MC), summed Standard Model: the sum of the 13 samples\n"
           f"below, normalised to 16.393 fb^-1 (Run2016G+H), RunIISummer20UL16 NanoAODv9.\n\n"
           f"CONTENTS\n  {n_sum} histograms (TH1D with Sumw2), weighted events.\n\n{table_samples(samples)}\n\n"
           f"{MISSING}\n\n{MC_WEIGHTS}\n\n{SELECTION}\n\n{TRIGGERS}\n\n{BUILD}\n"
           f"  MC peak removal uses the weighted, combined (all samples) distribution;\n"
           f"  the >= 100 rule counts raw MC events.\n{common_tail()}")
    (OUT / f"{fname}.README.txt").write_text(txt)
    written.append(fname)
    for rid, s in sorted(samples.items()):
        fname = f"{PREFIX}_MC-{s['physics_short']}-rec{rid}_{L}_{T}_mc.root"
        excl = (f"  Files used {s['n_files_included']}, excluded {s['n_files_excluded']}"
                + (" (file 98: Sigma_w check failed)." if s["n_files_excluded"] else "."))
        txt = (f"{fname}\n{'=' * len(fname)}\n\nCMS 2016 SIMULATION (MC), ONE sample: {s['physics_short']} "
               f"(CMS Open Data record {rid}),\nnormalised to 16.393 fb^-1 (Run2016G+H), RunIISummer20UL16 NanoAODv9.\n\n"
               f"CONTENTS\n  {s['histograms_n']} histograms (TH1D with Sumw2), weighted events.\n"
               f"  sigma_eff = {s['cross_section_pb_sigma_eff']:g} pb; normalisation factor "
               f"{s['normalisation_factor']:.6g}.\n{excl}\n"
               f"  The summed-SM file is the sum of this and the other 12 samples.\n\n"
               f"{MISSING}\n\n{MC_WEIGHTS}\n\n{SELECTION}\n\n{TRIGGERS}\n\n{BUILD}\n{common_tail()}")
        (OUT / f"{fname}.README.txt").write_text(txt)
        written.append(fname)
    print(f"wrote {len(written)} READMEs into {OUT}")


if __name__ == "__main__":
    main()
