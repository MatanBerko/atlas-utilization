CMS_OpenData_Run2016GH_13TeV_Data_DoubleMuon_16p4fb_340hists_cropped_2026-09-27.root
====================================================================================

WHAT THIS FILE IS
-----------------
340 mass histograms (TH1F) from real CMS proton-proton collision data --
not simulation. CMS Open Data, DoubleMuon primary dataset, NanoAODv9
(UL2016 MiniAODv2), 13 TeV, Run2016G + Run2016H, golden-JSON
data-quality filtered.

This is the file prepared for BumpNet: every histogram has been cropped
(see BINNING AND CROPPING below) so that its first bin is never empty.

DATASET AND CERN OPEN DATA RECORDS
----------------------------------
DoubleMuon, Run2016G   -- CERN Open Data record 30522   (29 files)
DoubleMuon, Run2016H   -- CERN Open Data record 30555   (28 files)

All 57 files of both records were read; 94,148,416 events read in total,
which matches the Open Data portal's own published total for these two
records exactly.

LUMINOSITY
----------
16.393380531 fb^-1 (quoted as 16.393 fb^-1), uncertainty +/- 1.2%.

Source: the official CMS per-lumisection luminosity table
pp_2016lumibyls.csv on CERN Open Data record 1059, produced with CMS's
own brilcalc tool over the certified (golden JSON, record 14220) run list
with the official 2016 normtag. Summed over the certified lumisections of
Run2016G (7.653261227 fb^-1) and Run2016H (8.740119304 fb^-1). The 1.2%
uncertainty is CMS's own quoted uncertainty on the 2016 luminosity
measurement, stated on record 1059 and citing "Precision luminosity
measurement in proton-proton collisions at sqrt(s) = 13 TeV in 2015 and
2016 at CMS" (CDS 2759951).

UNVERIFIED -- please read before quoting this luminosity:
16.393 fb^-1 is the recorded luminosity of the certified Run2016G+H
lumisections. In this project it was established, and its lumisection
coverage checked, for the DoubleEG dataset only (0.0042% of the
luminosity sits in lumisections absent from those files, which is why the
official value was adopted unchanged). The equivalent coverage check has
NOT been done for the 57 DoubleMuon files used here, and the
repository's own code comment states in as many words that this value is
"UNVERIFIED for DoubleMuon specifically -- established for DoubleEG".
Treat 16.393 fb^-1 for this file as the Run2016G+H run-range value, not
as a DoubleMuon-specific measured number.

TRIGGER
-------
PLEASE NOTE: no HLT trigger requirement was applied in the measurement
that produced this file. Its delivery record states explicitly: "No HLT
trigger requirement was applied in this measurement (that is a separate,
later survey's own addition, not part of this run)."

For completeness: the two dimuon DZ paths that the DoubleMuon selection
code defines, and that the LATER four-dataset delivery does require
(either one, OR'd together), are
  HLT_Mu17_TrkIsoVVL_Mu8_TrkIsoVVL_DZ
  HLT_Mu17_TrkIsoVVL_TkMu8_TrkIsoVVL_DZ
They were NOT applied to this file. For a trigger-selected DoubleMuon
sample, use the four-dataset delivery instead.

EVENT SELECTION
---------------
An event is used if it has
  >= 2 selected muons       (pT > 25 GeV, |eta| < 2.4, medium ID,
                             relative isolation < 0.15)
  AND
  >= 1 selected light jet   (non-b-tagged; pT > 30 GeV, |eta| < 2.5,
                             tight ID, delta-R >= 0.4 from every selected
                             muon and electron)

Jets are split into b-tagged and light with the DeepJet DeepFlavB
discriminant at the medium working point, 0.2598. Electrons (pT > 25 GeV,
|eta| < 2.5, cutBased medium) are selected and counted in the final-state
label but are not required. Leptons, jets and b-jets only -- no taus, no
photons.

Z-peak cutoff 115 GeV, removed from any object combination whose letters
contain two of the same lepton flavour. Hard mass cap 10,000 GeV. Then
peak removal, then a first-empty-bin outlier split; only the "main"
population of each surviving category is histogrammed.

Thresholds: at least 100 events per final-state category (applied first),
then per histogram the BumpNet acceptance criterion (arXiv:2501.05603
sec. 2.2.2) of more than 25 filled bins AND at least 100 events.

BINNING AND CROPPING
--------------------
Fixed 10 GeV bins on the shared grid 0 - 10,000 GeV. Every histogram here
has then been CROPPED: the all-empty leading region (and trailing region
where present) was removed by slicing to the window from the first to the
last non-zero bin. Bin width stays exactly 10 GeV and every remaining
edge stays aligned to the original grid -- a bin that ran 140-150 GeV
still runs 140-150 GeV, only its index changes. Empty bins in the middle
are kept untouched. Bin 1 is non-empty in all 340 histograms.

CONTENTS
--------
340 histograms over 17 final-state categories. Light-jet multiplicities 1
to 4. Smallest histogram 26 filled bins / 105 events; largest 187 bins /
1,051,110 events.

HISTOGRAM NAMING
----------------
  ROI_mass_<object combination>_cat_<final state>_width_10

example:
  ROI_mass_m0m1j0_cat_0ex_2mx_1jx_0gx_0tx_0bx_width_10

read as: the invariant mass of (muon 0, muon 1, jet 0), in the category
0 electrons, 2 muons, 1 light jet, 0 photons, 0 taus, 0 b-jets. Note the
photon (gx) and tau (tx) slots in the label and the "_width_10" ending --
see OLDER CONVENTIONS below.

PROVENANCE
----------
Built            27 September 2026
Fork commit      30c19a1 (the cropped files; their uncropped parents came
                 from a37d626), in
                 https://github.com/MatanBerko/atlas-utilization
Repository path  studies/cms_coverage/deliver/committed/
                 doublemuon_bumpnet_min26bins_cropped.root
                 (this file is a byte-identical copy, renamed)
Size             327,518 bytes
sha256           4d7880020a6266d1e3fd98c864f83280a4a9b5e2f2ed6b57d3e0dfe62abdc6f6

BumpNet status: this is the file BumpNet was already run on in late
September 2026, with 339 of the 340 histograms smoothed successfully.
UNVERIFIED -- that outcome is not recorded anywhere in the repository; it
comes from project communication only.

*** OLDER CONVENTIONS ***
This file predates trigger matching, the Version B final-state rule and
upstream-exact histogram names; do not mix it with the four-dataset file
without accounting for that. Concretely, in this file:
  - no HLT trigger requirement and no trigger matching at all;
  - final-state labels still carry photon and tau slots (0gx_0tx) and
    names end "_width_10", whereas the four-dataset file's names are
    exactly what the upstream pipeline produces and end "_width_10.0";
  - the Version B rule (reject an event if electrons + muons + b-jets > 4)
    is not applied;
  - the Z-peak cut is 115 GeV here, 110 GeV in the four-dataset file;
  - a per-histogram cut (more than 25 filled bins, at least 100 events) is
    applied here; the four-dataset file has no per-histogram cut.

KNOWN ARTIFACTS (not corrected in this file)
--------------------------------------------
1. Muon-jet overlap. In CMS NanoAOD a selected muon is very often also
   reconstructed inside a nearby jet -- measured on this same data,
   92.66% (Run2016G) / 92.68% (Run2016H) of jets lie within delta-R < 0.4
   of a selected muon. This is why the jet selection includes delta-R
   cleaning against selected muons and electrons.
2. An unexplained low-mass dimuon population. Of the 1,772,095 events in
   the inclusive mass(mu,mu,jet) histogram, 2.18% have m(mu,mu) < 2 GeV
   (3.03% below 4 GeV). Diagnostics point to genuine, independently
   reconstructed low-mass muon pairs for the large majority, but that is
   diagnostic evidence, not proof, and no cut was applied for it.

WHERE THESE FACTS COME FROM
---------------------------
In https://github.com/MatanBerko/atlas-utilization at commit 2734dd3:

  studies/cms_coverage/deliver/committed/README.txt
      dataset, records, 57 files, 94,148,416 events, selection,
      post-processing, thresholds, cropping, the no-trigger statement,
      the two known artifacts
  studies/cms_coverage/deliver/committed/build_summary.json
      340 histograms, event and bin statistics, shard identity check
  studies/cms_coverage/deliver/committed/crop_summary.json
      340 of 340 cropped histograms with a non-empty bin 1
  studies/m0m1j0_cms/selection.py
      object definitions, b-tag working point 0.2598, the two dimuon DZ
      path names, Z-peak cutoff 115 GeV
  studies/hgg_cms/impl_checks/lumi_coverage/LUMI_DECISION.md
      the 16.393380531 fb^-1 value, its brilcalc / record-1059 source,
      and the +/- 1.2% uncertainty
  studies/m0m1j0_cms/cluster/make_variants_plots.py, lines 41-45
      the statement that this luminosity is UNVERIFIED for DoubleMuon
      specifically

CONTACT
-------
Matan Berko
