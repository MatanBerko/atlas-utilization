#!/usr/bin/env python
"""Write the README of the final MC delivery draft (14 Nov 2026) from the registry v5, the build report and the
checks (evidence/final_build/). Every value's file:line source: MANIFEST.md (code at pin 6de9d3e).

    python studies/mc_expansion_20261103/delivery/make_readme.py
"""
from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
STUDY = HERE.parent
REPO = STUDY.parents[1]
EV = STUDY / "evidence" / "final_build"
REG = json.loads((REPO / "studies/cms_mc_weights_v3/cms_mc_normalisation_v5.json").read_text())
PIN = "6de9d3e605900a628bae372bdba4ea3308e9750f"
FNAME = "CMS_Run2016GH_MC-summedSM-71samples_16p393invfb_build2026-11-14_mc.root"

SELECTION = """OBJECT SELECTION (identical for data and MC; unchanged since the 25 Oct delivery)
  Muons:     pT > 25 GeV, |eta| < 2.4, CMS Loose ID (Muon_looseId),
             isolation pfRelIso04_all < 0.15
  Electrons: pT > 25 GeV, |eta| < 2.5, cut-based ID >= 2 (Loose or tighter,
             Fall17 V2: 0 fail, 1 veto, 2 loose, 3 medium, 4 tight)
  Jets:      pT > 30 GeV, |eta| < 2.5, tight jet ID, removed within dR < 0.4
             of a selected lepton
  b-jets:    DeepJet Jet_btagDeepFlavB > 0.2489 (UL2016 postVFP medium WP)
  e-mu overlap removal: every selected electron within dR < 0.12 of a
             selected muon is removed, before trigger matching and before the
             final state is decided."""

TRIGGERS = """TRIGGERS AND OFFLINE THRESHOLDS (trigger-object match dR < 0.1)
  DoubleMuon     HLT_Mu17_TrkIsoVVL_Mu8_TrkIsoVVL_DZ OR ..._TkMu8_..._DZ;
                 >= 2 matched muons, leading > 17 GeV
  SingleMuon     HLT_IsoMu24 (matching); >= 1 matched muon > 24 GeV
  DoubleEG       HLT_Ele23_Ele12_CaloIdL_TrackIdL_IsoVL_DZ; 2 matched
                 electrons, BOTH offline > 30 GeV
  MuonEG         HLT_Mu23_TrkIsoVVL_Ele12_..._DZ OR HLT_Mu8_TrkIsoVVL_Ele23_..._DZ;
                 >= 1 selected muon, electron leg 12 / 23 GeV by path
  SingleElectron HLT_Ele27_WPTight_Gsf; matched electron, online >= 27,
                 offline > 32 GeV
  MC: no de-duplication; an MC event is kept if ANY of the five dataset
  acceptances above holds (the same functions as the data; the data use the
  priority DoubleMuon > SingleMuon > DoubleEG > MuonEG > SingleElectron)."""

BUILD = """FINAL STATES AND POST-PROCESSING (as the 25 Oct delivery)
  * Multiplicity rule of upstream #40 (5fbf1ef): at most 4 objects per final
    state; light jets fill the free slots; masses use the kept leading jets.
  * >= 100 raw MC events per final state, applied once over all samples.
  * Same-flavour dilepton masses below 110 GeV are removed (Z-peak cut);
    masses above 10,000 GeV are removed.
  * Peak removal: entries below the rightmost highest peak are removed and the
    outlier tail is split off at the first empty bin (upstream
    post-processing). MC: on the WEIGHTED distribution of ALL samples combined
    (--peak-on weighted --peak-scope combined), so the cut masses depend on the
    set of samples (see OPEN ITEMS: binning vs data).
  * Fixed binning: 0-10,000 GeV in 10 GeV bins (1000 bins), uncropped.
  Names: ROI_mass_<combination>_cat_<n>ex_<n>mx_<n>jx_<n>bx_width_10.0"""

WEIGHTS = """MC WEIGHTS
  Each event: genWeight x L1PreFiringWeight_Nom x sigma_eff[pb] x 1000 x
  16.393 / Sigma_w. sigma_eff already contains every factor (k_factor =
  gen_filt_eff = 1.0 in the registry). Sigma_w = sum of genWeight over all
  files of the sample that pass the per-file check |sum genWeight -
  Runs.genEventSumw| / genEventSumw <= 1e-6 (a failing file is excluded).
  {excl}
  L = 16.393 fb^-1 (Run2016G 7.653 + Run2016H 8.740, golden JSON).
  No pileup reweighting (as ATLAS; Pileup_nTrueInt is stored).
  Histograms are TH1D with Sumw2 (bin errors = sqrt(sum w^2)). Negative bin
  contents can occur (negative generator weights of the NLO samples)."""


def status(rid, r):
    if r.get("estimate"):
        return "ESTIMATE"
    d = r.get("decision_2026_11_07") or r.get("decision_2026_11_03")
    if d:
        v = d.get("verification", "")
        if rid == "64873":
            return "VERIFIED BY MATAN; generator LO only"
        if v.startswith("VERIFIED BY MATAN"):
            return "VERIFIED BY MATAN"
        if v.startswith("technical-lead saved copy"):
            return "portal values: technical-lead saved copy, Matan's live check pending; 61526.7 VERIFIED BY MATAN"
        return v.split(" (")[0]
    return "decided by Matan 15 Oct (25 Oct delivery)"


def construction(r):
    d = r.get("decision_2026_11_07") or r.get("decision_2026_11_03") or r.get("decision_2026_10_15") or {}
    if "factors" in d:
        src = "; ".join(f["source"]["citation"] for f in d["factors"] if f.get("source"))
    else:
        src = "; ".join(s.get("citation", "") for s in d.get("sources", []))
    return d.get("construction", ""), d.get("order", ""), src


def main():
    chk = json.loads((EV / "checks_final.json").read_text())
    bsum = json.loads((EV / "build_report_summary.json").read_text())
    rows = {s["record"]: s for s in chk["samples"]}
    recs = REG["records"]
    n_hist = bsum["summed_sm"]["n_histograms"]
    n_fs = len({h.split("_cat_")[1] for h in bsum["summed_sm"]["histogram_names"]})
    excluded = [f"{rid} ({rows[rid]['physics_short']}): {rows[rid]['n_files_excluded']} file(s)"
                for rid in rows if rows[rid]["n_files_excluded"]]
    excl = ("Excluded by that check: " + "; ".join(excluded) + ".") if excluded else "No file failed that check."
    table = ["  record  dataset (short)                                   process group             "
             "sigma_eff [pb]  order / construction / source  |  status"]
    groups = {}
    for gname, members in bsum["groups"].items():
        for m in members:
            groups[str(m)] = gname
    for rid in sorted(rows, key=int):
        r = recs[rid]
        c, o, src = construction(r)
        table.append(f"  {rid}   {r['physics_short'][:48]:<48s}  {groups.get(rid, '')[:24]:<24s}  "
                     f"{r['cross_section_pb']:>12.6g}  {o}: {c}  [{src}]  |  {status(rid, r)}")
    d3 = chk["d3"]
    nb = chk["names_binning"]
    ed = nb["edges"]
    same = ed["first_filled_same_as_data"]
    txt = f"""{FNAME}
{'=' * len(FNAME)}

CMS 2016 SIMULATION (MC), summed Standard Model: the sum of the {len(rows)} samples below,
normalised to 16.393 fb^-1 (Run2016G+H), RunIISummer20UL16 NanoAODv9 (postVFP).
DRAFT, built 14 Nov 2026; not yet reviewed for release.

CONTENTS
  {n_hist} histograms (TH1D with Sumw2), weighted events, in {n_fs} final states.
  Data: the 25 Oct 2026 data delivery (CMS_Run2016GH_DoubleMuon-SingleMuon-DoubleEG-
  MuonEG-SingleElectron_16p393invfb_prod2026-10-25_data_bumpnet_*.root) is unchanged
  and is the data to compare with. Names in both: {nb['n_both']}; MC-only: {len(nb['mc_only'])};
  data-only: {len(nb['data_only'])}.

SAMPLES ({len(rows)}; registry studies/cms_mc_weights_v3/cms_mc_normalisation_v5.json)
{chr(10).join(table)}

EXCEPTIONS TO "MATCH ATLAS" (decided by Matan)
  E1  Dibosons: CMS uses NNLO k-factors (incl. gg -> VV) on the generator
      values; ATLAS uses its Sherpa samples with kFactor 1. CMS / ATLAS
      normalisation 0.92-1.24 by process.
  E2  Electroweak V + 2 jets samples are NOT included: they would double count
      with the diboson samples.
  E3  ttZ: ATLAS applies kFactor 1.11 (ttZ -> nunu/qq) and 1.12 (tt + ll); CMS
      keeps the generator NLO values (k = 1) for all ttZ samples (68185, 68187,
      68206): about 11 % on a background below 0.1 % of the total, smooth shape,
      and no change to a delivered value.

ESTIMATES, LO-ONLY AND SECONDARY SOURCES
  * 40062 (gg -> ZH, H -> ZZ -> 4l): sigma_eff = {recs['40062']['cross_section_pb']:g} pb is an ESTIMATE:
    the generator filter efficiency is not published; estimated as
    1 - (1 - BR(Z -> ll))^2 = 0.19178.
  * 64873 (ST_tWll): generator LO value {recs['64873']['cross_section_pb']:g} pb, the only value
    available (no NLO sample or published total for this phase space).
  * Secondary source RazorAnalyzer data/xSections.dat (a CMS analysis group's
    public table, not a primary theory source): DY M-10to50 18,610 pb and
    M-50 3 x 1921.8 pb; the W+jets NNLO total 61,526.7 pb used for the W+jets
    k-factor; the Z -> nunu NNLO/LO k-factor 5765.4 / 5396 (from DY).
  * W+jets (69715, 69717, 69719): the registry records the portal values as
    the technical lead's saved copy with Matan's own live check pending.

FILES LISTED BY CERN BUT NOT PUBLISHED (cannot be processed)
  * 69717 W+jets 1 jet: 30 of 117 files published -> this piece's MC
    luminosity is about 0.08 x the data luminosity (ESTIMATE).
  * 72761 WZZ: 6 of 9 files published.
  Normalisation is still correct (Sigma_w over the files used); the effect is
  fewer MC events, i.e. larger single-event weights. 69717 is nevertheless the
  largest single sample in the sum ({100*rows['69717']['share_of_total']:.0f} % of the summed weighted yield).

SINGLE-EVENT DOMINANCE (decision D3)
  Bins where ONE MC event can carry more than 50 % of the bin's MC content
  (upper bound on the single-event weight, per sample and bin):
  {d3['n_bins_flagged']:,} bins in {d3['n_histograms_with_flagged_bin']} of {d3['n_histograms']} histograms.
  Samples causing most of them: {', '.join(f"{k} ({v:,})" for k, v in list(d3['bins_by_sample'].items())[:6])}.
  W+jets 1 jet (69717): {d3['wjets_1j_69717']['bins']:,} bins in {d3['wjets_1j_69717']['histograms']} histograms;
  WZZ (72761): {d3['wzz_72761']['bins']:,} bins in {d3['wzz_72761']['histograms']} histograms.
  The bound is an upper bound (it uses the sample's largest |genWeight|), so
  the true count is lower. Most flagged bins are in the far tails, where the
  MC content is small; {d3['n_bins_with_mc_le_zero_and_some_weight']:,} of them have a summed MC content <= 0
  (negative generator weights). The samples flagged most are the high-cross-
  section NLO samples (Drell-Yan, W+jets, ttbar, WZ), including samples
  already in the 25 Oct delivery. Such bins can show isolated spikes; treat
  them with care. Details: REPORT.md (D3) and checks_final.json.

MISSING FROM THE MC (important when comparing data with MC)
  * QCD multijet: NOT included (Matan, 14 Nov 2026; the question to Maryna is
    open; it may follow as a separate component). A one-file probe
    (QCD_PROBE.md) shows it matters in the single-lepton + jets final states
    (fake or non-prompt leptons; estimated at the scale of the data excess
    there, with huge single-event weights), is negligible in two-lepton final
    states and was not seen in e-mu 0 jets.
  * Photon processes (gamma + jets, V gamma, tt gamma).
  * BSM signals (none is part of the SM background).
  * Electroweak V + 2 jets (E2).
  * Deferred Higgs extras (further production modes / decays not in the list).
  * 5-flavour t-channel single top: the 4-flavour samples are used (D4, as ATLAS).

{WEIGHTS.format(excl=excl)}

{SELECTION}

{TRIGGERS}

{BUILD}

OPEN ITEMS (for the analysis team)
  * Binning vs the delivered data: the first filled bin of {len(ed['per_histogram']) - same} of
    {len(ed['per_histogram'])} histograms present in both files differs from the data delivery (the
    MC peak removal runs on all {len(rows)} samples combined, so its cut masses moved
    when samples were added). Both use the same 0-10,000 GeV, 10 GeV axis; the
    data were not rebuilt. Options are listed in REPORT.md (decision open).
  * QCD multijet (see MISSING).

PRODUCTION
  Produced 3-9 Nov 2026 (new samples) and 25-26 Oct 2026 (the 13 delivered
  samples, reused unchanged) on the Weizmann WIPP cluster from the code at
  commit {PIN} (github.com/MatanBerko/atlas-utilization); built 14 Nov 2026
  with registry v5. Checksums: SHA256SUMS.txt. Sources of every value:
  MANIFEST.md.
"""
    out = HERE / f"{FNAME}.README.txt"
    out.write_text(txt)
    print("wrote", out)


if __name__ == "__main__":
    main()
