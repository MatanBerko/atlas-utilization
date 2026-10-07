# Four-dataset BumpNet delivery — notes

Prepared 7 October 2026. Written to be forwarded as-is.

## The file

```
/storage/agrp/berkom/atlas-utilization/output/cms_datasets/deliver/
  four_dataset_vB_upstreamnames_w10p0_dr012_20261007/
    four_dataset_matched_vB_upstreamnames_w10p0_dr012_bumpnet_cropped.root   <-- use this one
```

The **cropped** file is the one for BumpNet: every histogram is trimmed to
its first..last filled bin, so the first bin is never empty. A companion
`..._bumpnet.root` holds the same 1,975 histograms on the full fixed
0–10000 GeV grid, for cross-checking and plotting only. A `README.txt` and
a manifest sit beside them.

## What is in it

**1,975 histograms** over **103 final-state categories**, **82,956,880
entries**. Fixed 10 GeV bins, 0–10000 GeV. Names are exactly what the main
pipeline produces, e.g.
`ROI_mass_m0m1_cat_0ex_2mx_5jx_1bx_width_10.0`.

**Four datasets, Run2016G+H, 390 files, all processed:**

| dataset | files | trigger requirement |
|---|---:|---|
| DoubleMuon | 57 | either dimuon DZ path, plus two trigger-matched muons |
| SingleMuon | 152 | `HLT_IsoMu24`, plus one trigger-matched muon above 24 GeV |
| DoubleEG | 133 | the dielectron DZ path, plus **two** trigger-matched electrons above 30 GeV |
| MuonEG | 48 | either e-µ DZ path, one selected muon, one trigger-matched electron |

**De-duplication.** Every collision is counted once. Priority, highest
first: **DoubleMuon > SingleMuon > DoubleEG > MuonEG**. A collision belongs
to a dataset only if that dataset accepts it and no higher-priority dataset
does — judged on the dataset's full acceptance (trigger fired *and* its own
matching rule), not just the trigger bit.

**Electron–muon overlap removal.** Every selected electron within
**dR < 0.12** of a selected muon is removed, in all four datasets, before
trigger matching and before the final state is decided. Muons are never
removed. This is the radius you chose on 7 Oct; it clears the collinear
population of electrons that are really the same object as a nearby muon.

**Unchanged from the muon-only delivery:** object definitions, the Version B
rule (reject an event if electrons + muons + b-jets > 4, otherwise keep all
light jets), exact light-jet final states, the 186 mass combinations, the
Z-peak cut at 110 GeV, the bin-aligned outlier split, the ≥100-events-per-
final-state rule (applied once over all 390 files), and no per-histogram
minimum or filled-bin cut.

## The counts, against the muon-only delivery

| | this delivery | muon-only (6 Oct) |
|---|---:|---:|
| histograms | **1,975** | 1,496 |
| final-state categories | **103** | 81 |
| entries | **82,956,880** | 78,754,866 |

Split by electron content:

| | categories | histograms | entries |
|---|---:|---:|---:|
| with ≥ 1 electron | 45 | 931 | 5,418,308 |
| with no electrons | 58 | 1,044 | 77,538,572 |

**22 final-state categories are new** and **none was lost** — every category
in the muon-only delivery is still here. The no-electron categories barely
move (largest change 0.47%, nearly all under 0.1%), which is the expected
behaviour: the electron datasets add events where electrons are, and the
overlap removal only shifts a handful of events between categories.

## Known limitations

1. **About 9 collisions per million are lost and 4 per million counted
   twice**, because muon isolation differs slightly between two datasets'
   own copies of the same collision and straddles our cut. Measured on run
   281707 only; UNVERIFIED for other runs. No priority order removes it.
2. **The MuonEG muon leg cannot be trigger-matched in 2016 NanoAOD**, so it
   is taken from the trigger decision plus one selected offline muon.
   MuonEG-exclusive events are a tiny share of the delivery: **13,443
   collisions, 0.008%** of the 168.4 million delivered.
3. **Electrons in the barrel–endcap gap (|eta| 1.4442–1.566) are kept**, as
   in all earlier deliveries.
4. **The b-tag working point is unchanged** — DeepJet 0.2598, the 2016
   preVFP medium value, while Run2016G+H are postVFP (0.2489). Pending a
   group decision.
5. **SingleElectron is not included.**

## How it was checked

Read back from the real ROOT files: every one of the 1,975 names matches
what the upstream pipeline's own naming code produces (including the
`_width_10.0` ending), no duplicate names, no empty histogram, every final
state above 100 events, and bin edges exactly 10 GeV over 0–10000 GeV.
Across the whole 390-file production there were **zero trigger-object
mismatches** and **zero failed jobs**.
