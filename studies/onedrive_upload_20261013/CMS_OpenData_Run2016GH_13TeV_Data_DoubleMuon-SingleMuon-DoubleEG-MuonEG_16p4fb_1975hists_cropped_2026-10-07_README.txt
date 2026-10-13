CMS_OpenData_Run2016GH_13TeV_Data_DoubleMuon-SingleMuon-DoubleEG-MuonEG_16p4fb_1975hists_cropped_2026-10-07.root
================================================================================================================

WHAT THIS FILE IS
-----------------
1,975 mass histograms (TH1F) from real CMS proton-proton collision data --
not simulation. CMS Open Data, NanoAODv9 (UL2016 MiniAODv2), 13 TeV,
Run2016G + Run2016H, golden-JSON data-quality filtered, pooled over four
primary datasets and de-duplicated so that every accepted collision is
counted exactly once.

This is the file prepared for BumpNet: every histogram has been cropped
(see BINNING AND CROPPING below) so that its first bin is never empty.

THE FOUR DATASETS, THEIR CERN OPEN DATA RECORDS AND TRIGGERS
------------------------------------------------------------
                 record G   record H   files   trigger requirement
DoubleMuon         30522      30555       57    either dimuon DZ path,
                                               HLT_Mu17_TrkIsoVVL_Mu8_TrkIsoVVL_DZ
                                               or HLT_Mu17_TrkIsoVVL_TkMu8_TrkIsoVVL_DZ,
                                               plus two trigger-matched
                                               muons (leading pT > 17 GeV)
SingleMuon         30530      30563      152    HLT_IsoMu24, plus one
                                               trigger-matched muon above
                                               24 GeV
DoubleEG           30521      30554      133    HLT_Ele23_Ele12_CaloIdL_TrackIdL_IsoVL_DZ,
                                               plus TWO trigger-matched
                                               electrons above 30 GeV
MuonEG             30528      30561       48    either e-mu DZ path,
                                               HLT_Mu23_TrkIsoVVL_Ele12_CaloIdL_TrackIdL_IsoVL_DZ
                                               or HLT_Mu8_TrkIsoVVL_Ele23_CaloIdL_TrackIdL_IsoVL_DZ,
                                               plus one selected muon and
                                               one trigger-matched electron
                                              total 390 files, all processed

PRIORITY ORDER AND DE-DUPLICATION
---------------------------------
Every collision is counted once. Priority, highest first:
  DoubleMuon > SingleMuon > DoubleEG > MuonEG
A collision belongs to a dataset only if that dataset accepts it and no
higher-priority dataset does -- judged on the dataset's FULL acceptance
(its trigger path fired AND its own trigger-matching / threshold rule
passes), not on the trigger bit alone.

ELECTRON-MUON OVERLAP REMOVAL
-----------------------------
Every selected electron within delta-R < 0.12 of a selected muon is
removed, in all four datasets, before trigger matching and before the
final state is decided. Muons are never removed. The comparison is
strict. Jet cleaning is untouched.

The 0.12 radius was approved on 7 October 2026, raised from the 0.05 this
pipeline used before: it was chosen from the MuonEG / SingleElectron
per-event min-delta-R(e,mu) distribution, in which the collinear
population -- electrons that are really the same object as a nearby muon
-- extends to about 0.12. (For reference, ATLAS uses 0.1 for this removal
in ttbar MC and the CMS ZZ paper arXiv:2009.01186 uses 0.05.)

NOTE: the auto-generated README.txt sitting next to this file on the
production cluster says "dR < 0.05". That text is stale -- it is a
hard-coded string in the delivery script that was not updated when the
radius changed. The radius actually used in this production is 0.12: it
is the production code constant, it is recorded in every one of the 390
per-job metadata records, and it is in this file's own directory name
(..._dr012_...).

FINAL-STATE RULE (VERSION B)
----------------------------
Reject an event if electrons + muons + b-jets > 4; otherwise keep ALL of
its selected light jets. Final states are exact in the light-jet count.

EVENT SELECTION AND POST-PROCESSING
-----------------------------------
Object definitions, the b-tag working point, the golden-JSON run filter,
the 186 object-mass combinations, the fixed 10 GeV binning, the
bin-aligned outlier split, the max-mass cut and peak removal are all
unchanged from the earlier muon-only delivery. The Z-peak cut is 110 GeV.

Thresholds: at least 100 events per final state, applied once over the
combined output of all 390 per-file jobs. No per-histogram minimum-entries
cut and no filled-bin cut (BumpNet applies its own during smoothing). For
information, of the 1,975 histograms delivered, 1,601 have 25 or more
filled bins, 1,586 more than 25, and 1,502 more than 30.

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

File coverage was checked for all four datasets on 13 October 2026. Of
the 90,807 certified Run2016G+H lumisections, each dataset's files
contain 90,125; the 682 absent from each carry this much luminosity:

  dataset      files   missing lumisections   missing lumi   % of total
  DoubleMuon      57            682       0.000688522 fb^-1    0.0042%
  SingleMuon     152            682       0.000688522 fb^-1    0.0042%
  DoubleEG       133            682       0.000688616 fb^-1    0.0042%
  MuonEG          48            682       0.000688522 fb^-1    0.0042%

Every dataset is far below the 0.1% threshold agreed for changing the
quoted value, so 16.393380531 fb^-1 stands. 662 of the 682 missing
lumisections carry exactly zero recorded luminosity. Since all four
datasets cover the same run range to within 0.0042%, that figure applies
to the de-duplicated union delivered here.
See studies/lumi_coverage_four_datasets/LUMI_COVERAGE_REPORT.md.

BINNING AND CROPPING
--------------------
Fixed 10 GeV bins on the fixed grid 0 - 10,000 GeV. Every histogram here
has then been CROPPED to the window from its first to its last filled
bin, so the first bin is never empty; the 10 GeV pitch and the original
grid alignment are preserved. A companion uncropped file holds the same
1,975 histograms on the full 0 - 10,000 GeV grid, for cross-checking and
plotting only.

CONTENTS
--------
1,975 histograms over 103 final-state categories, 82,956,880 entries
summed over all histograms. Light-jet multiplicities 0 to 9. Split by
electron content: 45 categories / 931 histograms / 5,418,308 entries have
at least one electron; 58 categories / 1,044 histograms / 77,538,572
entries have none.

HISTOGRAM NAMING
----------------
Names are exactly what the upstream pipeline's own naming code produces,
including the "_width_10.0" ending:

  ROI_mass_<object combination>_cat_<final state>_width_10.0

example:
  ROI_mass_m0m1_cat_0ex_2mx_5jx_1bx_width_10.0

read as: the invariant mass of (muon 0, muon 1), in the category
0 electrons, 2 muons, 5 light jets, 1 b-jet.

PROVENANCE
----------
Built           7 October 2026
Fork commit     db1bd32, in
                https://github.com/MatanBerko/atlas-utilization
Source path     /storage/agrp/berkom/atlas-utilization/output/cms_datasets/
                deliver/four_dataset_vB_upstreamnames_w10p0_dr012_20261007/
                four_dataset_matched_vB_upstreamnames_w10p0_dr012_bumpnet_cropped.root
                (this file is a byte-identical copy, renamed)
Size            1,668,048 bytes
sha256          deca5da347fedfa6026b29c9bb298d3afce9d3a851e2310fc9601ee81f39c11a

Production: all 390 files processed, every one with exactly one complete
output, no failed subjob, zero trigger-object mismatches. 645,377,261
events read, 633,187,431 after the golden JSON, 168,418,730 delivered
after de-duplication.

KNOWN LIMITATIONS
-----------------
1. About 9 collisions per million are lost and 4 per million counted
   twice, because muon isolation differs slightly between two datasets'
   own copies of the same collision and straddles our cut. Measured on
   run 281707 only; UNVERIFIED for other runs. No priority order removes
   it.
2. The MuonEG muon leg cannot be trigger-matched in 2016 NanoAOD, so it
   is taken from the trigger decision plus one selected offline muon.
   MuonEG-exclusive events are a tiny share of the delivery: 13,443
   collisions, 0.008% of the 168.4 million delivered.
3. Electrons in the barrel-endcap gap (|eta| 1.4442 - 1.566) are kept, as
   in all earlier deliveries.
4. The b-tag working point is unchanged -- DeepJet 0.2598, the 2016
   preVFP medium value, while Run2016G+H are postVFP (0.2489). Pending a
   group decision.
5. SingleElectron is not included.

WHERE THESE FACTS COME FROM
---------------------------
In https://github.com/MatanBerko/atlas-utilization at commit 2734dd3:

  studies/cms_datasets/electron_vB/DELIVERY_NOTES.md
      the file, its contents, the four datasets with file counts and
      trigger requirements, de-duplication, the 0.12 overlap radius,
      Version B, the Z-peak cut, the counts, the five known limitations
  studies/cms_datasets/electron_vB/evidence/D2_D3_delivery_checks.json
      the read-back checks: 1,975 histograms, 103 final states, no
      duplicate names, no empty histogram, 10 GeV edges over 0-10000 GeV,
      every final state above 100 entries, every name equal to what
      upstream's own naming code produces (upstream master 88d7a4b), and
      the per-final-state entry counts
  studies/cms_datasets/electron_vB/REPORT_production.md
      the 390-file production table: events read, after golden JSON,
      after trigger, accepted, exclusive, and the per-job confirmation of
      dR 0.12 with removal on
  studies/cms_datasets/cluster/datasets_records.py
      the CERN Open Data record numbers, file counts and trigger paths
  studies/cms_datasets/cluster/run_dataset_on_file.py
      the acceptance rules per dataset, the DoubleEG 30 GeV offline cut,
      and EMU_OVERLAP_DR_MAX = 0.12 with its provenance
  studies/cms_datasets/electron_vB/evidence/delivery_README.txt
      the thresholds and filled-bin counts (this is the auto-generated
      text whose dR figure is stale -- see the note above)
  studies/hgg_cms/impl_checks/lumi_coverage/LUMI_DECISION.md
      the 16.393380531 fb^-1 value, its brilcalc / record-1059 source,
      and the +/- 1.2% uncertainty
  studies/lumi_coverage_four_datasets/LUMI_COVERAGE_REPORT.md
      the file-coverage check of 13 October 2026: all four datasets,
      390 files, the per-dataset missing-lumisection table above

CONTACT
-------
Matan Berko
