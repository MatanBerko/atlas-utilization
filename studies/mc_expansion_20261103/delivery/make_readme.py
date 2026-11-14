#!/usr/bin/env python
"""Write the README of the final MC delivery draft (14 Nov 2026) from the registry v5, the build report and the
checks (evidence/final_build/). Every value's file:line source: MANIFEST.md (code at pin 6de9d3e).

    python studies/mc_expansion_20261103/delivery/make_readme.py
"""
from __future__ import annotations

import json
import textwrap
from pathlib import Path

HERE = Path(__file__).resolve().parent
STUDY = HERE.parent
REPO = STUDY.parents[1]
EV = STUDY / "evidence" / "final_build"
REG = json.loads((REPO / "studies/cms_mc_weights_v3/cms_mc_normalisation_v5.json").read_text())
V7 = json.loads((REPO / "studies/cms_mc_weights_v3/sources/v7_decisions_2026-11-14.json").read_text())
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
            # v7 (14 Nov 2026): the three portal values were checked by Matan on the live portal
            return ("portal value " + V7["wjets_portal_values"]["verification"]
                    + "; 61526.7 VERIFIED BY MATAN (RazorAnalyzer stays SECONDARY)")
        return v.split(" (")[0]
    return "decided by Matan 15 Oct (25 Oct delivery)"


def construction(r):
    d = r.get("decision_2026_11_07") or r.get("decision_2026_11_03") or r.get("decision_2026_10_15") or {}
    if "factors" in d:
        src = "; ".join(f["source"]["citation"] for f in d["factors"] if f.get("source"))
    else:
        src = "; ".join(s.get("citation", "") for s in d.get("sources", []))
    order = d.get("order", "")
    if r.get("physics_short") == V7["68847"]["physics_short"]:
        order = V7["68847"]["order"]   # v7 (14 Nov 2026): order label only, value unchanged
    return d.get("construction", ""), order, src


def main():
    chk = json.loads((EV / "checks_final.json").read_text())
    bsum = json.loads((EV / "build_report_summary.json").read_text())
    sm = json.loads((EV / "start_masses_20261114.json").read_text())
    psum = json.loads((EV / "per_sample_sumcheck_20261114.json").read_text())
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
    n_both = sm["n_both"]
    n_diff = n_both - sm["n_first_filled_same"]
    shifts = sm["shift_mc_minus_data_gev"]
    n_one_bin = shifts.get("10.0", 0) + shifts.get("-10.0", 0)
    n_later = sum(v for k, v in shifts.items() if float(k) > 0)
    shift_txt = ", ".join(f"{float(k):+.0f}: {v}" for k, v in sorted(shifts.items(), key=lambda kv: float(kv[0])))
    mu1j = sm["examples"]["ROI_mass_m0j0_cat_0ex_1mx_1jx_0bx_width_10.0"]
    emu = next(c for c in chk["data_mc_categories"] if c["key"] == "emu_0j")
    sl = [c for c in chk["data_mc_categories"] if c["key"] in ("e_1j", "mu_1j", "e_2j", "mu_2j", "e_3j", "mu_3j")]
    sl_lo = min(min(c["data_over_mc_new"], c["data_over_mc_new_common"]) for c in sl)
    sl_hi = max(max(c["data_over_mc_new"], c["data_over_mc_new_common"]) for c in sl)
    csv_name = f"{FNAME}.start_masses.csv"
    mc_only = textwrap.fill(", ".join(n.replace("ROI_mass_", "mass_").replace("_width_10.0", "") for n in sm["mc_only"]),
                            width=76, initial_indent="    ", subsequent_indent="    ")
    txt = f"""{FNAME}
{'=' * len(FNAME)}

CMS 2016 SIMULATION (MC), summed Standard Model: the sum of the {len(rows)} samples below,
normalised to 16.393 fb^-1 (Run2016G+H), RunIISummer20UL16 NanoAODv9 (postVFP).
Built 14 Nov 2026; README finalised 14 Nov 2026 (to be verified by the
technical lead before hand-over).

CONTENTS
  {n_hist} histograms (TH1D with Sumw2), weighted events, in {n_fs} final states.
  Data: the 25 Oct 2026 data delivery (CMS_Run2016GH_DoubleMuon-SingleMuon-DoubleEG-
  MuonEG-SingleElectron_16p393invfb_prod2026-10-25_data_bumpnet_*.root) is unchanged
  and is the data to compare with. Names in both: {nb['n_both']}; MC-only: {len(nb['mc_only'])};
  data-only: {len(nb['data_only'])}.

COMPARING THESE MC HISTOGRAMS WITH THE CMS DATA HISTOGRAMS (START MASSES)
  Read this before comparing data and MC.
  * What peak removal does: in each histogram the masses below the highest
    10 GeV bin of the spectrum (the rightmost one if several are equally
    high) are removed, so every histogram starts at its peak; the tail is cut
    at the first empty bin above it (the upstream ATLAS post-processing
    functions). This is done SEPARATELY for data and MC: the data are cut at a
    mass found from the data, the MC at a mass found from the sum of all
    {len(rows)} MC samples (weighted). The two cuts can land in different bins.
  * The ATLAS pipeline works the same way: data and MC are separate pipeline
    runs and each finds its own peak, so ATLAS data and MC histograms can also
    start at different masses.
  * This MC file and the UNCROPPED data file use the same axis: 0-10,000 GeV
    in 10 GeV bins (1000 bins), so bin i of the data is bin i of the MC
    (one-to-one). The CROPPED data file (the one for BumpNet) keeps only the
    data's filled range (its axis runs from the data's first to its last
    filled bin, on the same 10 GeV grid), so to use it, match bins by their
    mass edges, not by bin number.
  * In {n_diff} of the {n_both} histograms present in both files the first filled
    bin differs (MC minus data, in GeV: number of histograms):
      {shift_txt}
    {n_one_bin} of the {n_diff} differ by one bin (10 GeV); in {n_later} the MC starts
    later than the data.
  * RULE: before comparing shapes or computing data/MC, crop BOTH histograms
    to the common start = the later of the two first filled bins. The common
    start of every histogram is in the file
      {csv_name}
    (column common_start_gev), with the data and MC integrals from there.
  * Worked example, mu + 1 jet (ROI_mass_m0j0_cat_0ex_1mx_1jx_0bx_width_10.0):
    data start {mu1j['data_first_filled_gev']:.0f} GeV, MC start {mu1j['mc_first_filled_gev']:.0f} GeV. data/MC over each file's own range =
    {mu1j['data_over_mc_own_range']:.2f}; from the common start ({mu1j['common_start_gev']:.0f} GeV) = {mu1j['data_over_mc_from_common_start']:.2f}. The low-mass bins hold
    most of the events, so a one-bin offset changes the ratio a lot.
  * {len(sm['mc_only'])} MC histograms have no data counterpart (four-lepton final states
    not in the data file):
{mc_only}

PER-SAMPLE FILES (folder per_sample/)
  * One file per sample, {psum['n_per_sample_files']} files, named
    CMS_Run2016GH_MC-<dataset short>-rec<record>_16p393invfb_build2026-11-14_mc.root,
    each with a short README (sample, record, dataset, sigma_eff and its
    source and status, Sigma_w, normalisation, files used and published).
    Each holds only the histograms its sample fills ({psum['n_histogram_entries_per_sample_total']:,} histograms in all).
  * They come from the same build as the summed file and add up to it: for
    every one of the {psum['n_histograms_summed']} histograms, the sum of the per-sample histograms
    equals the summed histogram to {psum['largest_relative_difference']['value']:.1e} (relative; floating-point
    rounding), bin errors (Sumw2) to {psum['largest_relative_difference_sumw2']['value']:.1e}.
  * Start masses: every per-sample histogram is cut at the SAME peak-removal
    and split masses as the summed histogram of the same name (found once on
    the weighted sum of all {len(rows)} samples and applied to each sample), so the
    per-sample files are slices of the summed file. A sample can be empty in
    the lowest bins, so its own first filled bin can lie later; compare with
    data only from the common start in the CSV (rule above).

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
  * W+jets (69715, 69717, 69719): the portal generator values (MiniAOD 69714
    5.330e+04 pb, 69716 8.958e+03 pb, 69718 3.330e+03 pb) are VERIFIED BY
    MATAN on the live portal (14 Nov 2026); the NNLO total 61,526.7 pb is
    VERIFIED BY MATAN; its source RazorAnalyzer stays a SECONDARY source.

FILES LISTED BY CERN BUT NOT PUBLISHED (cannot be processed)
  * 69717 W+jets 1 jet: 30 of 117 files published -> this piece's MC
    luminosity is about 0.08 x the data luminosity (ESTIMATE).
  * 72761 WZZ: 6 of 9 files published.
  Normalisation is still correct (Sigma_w over the files used); the effect is
  fewer MC events, i.e. larger single-event weights. 69717 is nevertheless the
  largest single sample in the sum ({100*rows['69717']['share_of_total']:.0f} % of the summed weighted yield,
  from {rows['69717']['n_files_included']} of 117 files), and its few heavy events give isolated spikes,
  e.g. in e-mu 0 jets at high mass (data/MC there {emu['data_over_mc_new']:.2f} overall).

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
  * QCD multijet: NOT included (Matan, 14 Nov 2026: deliver now; the question
    to Maryna is open; it may follow as a separate component). Where it
    matters: the single-lepton + jets final states, where data/MC is still
    {sl_lo:.1f}-{sl_hi:.1f} with this MC (e or mu + 1-3 jets, own or common range). A
    one-file probe (QCD_PROBE.md, ESTIMATE) puts QCD (jets faking a lepton)
    at the scale of that excess, with huge single-event weights; it is
    negligible in two-lepton final states and was not seen in e-mu 0 jets.
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
  * QCD multijet (see MISSING).
  Decided (Matan, 14 Nov 2026): the binning is delivered as is (same axis;
  start masses differ in {n_diff} of {n_both} histograms); compare data and MC
  only from the common start (see "COMPARING ... (START MASSES)" above).

PRODUCTION
  Produced 3-9 Nov 2026 (new samples) and 25-26 Oct 2026 (the 13 delivered
  samples, reused unchanged) on the Weizmann WIPP cluster from the code at
  commit {PIN} (github.com/MatanBerko/atlas-utilization); built 14 Nov 2026
  with registry v5; README finalised 14 Nov 2026 (decisions:
  studies/cms_mc_weights_v3/sources/v7_decisions_2026-11-14.json).
  Files: this README, the ROOT file, {csv_name},
  per_sample/ ({psum['n_per_sample_files']} ROOT files + {psum['n_per_sample_files']} READMEs), MANIFEST.md (sources of every
  value) and SHA256SUMS.txt (checksums of every file in the package).
"""
    out = HERE / f"{FNAME}.README.txt"
    out.write_text(txt)
    print("wrote", out)


if __name__ == "__main__":
    main()
