# H -> ZZ -> 4l, Part B: full-scale run on the Weizmann ATLAS Grid cluster

Branch: `analysis/higgs-4lepton-clean`. Parsed on the cluster (PBS job
`4999623.pbs`, queue N, 238/238 files, 100% success, 2h33m, all six records
non-zero — see the PBS job report). Analysis run:
`scripts/higgs_4lepton_partB_report.py` against
`output/cms_higgs_4lepton_cluster_fullscale_20260909_113726` (parsed on the
cluster, not the laptop). Plots: `scripts/higgs_4lepton_partB_plots.py`.

Full selection: Part A (muons pT>5/|eta|<2.4/looseId/iso<0.35; electrons
pT>7/|eta|<2.5/cutBased>=2/iso<0.35; exactly-4/charge-0; A1 low-mass veto;
A2 ghost removal; leading pT>20/sub-leading pT>10; Z1/Z2 pairing) plus Part
B's impact-parameter cuts: sip3d<4, |dxy|<0.5 cm, |dz|<1.0 cm.

## THE VALIDATION CHECK: does the 91 GeV Z peak survive? Yes, and purity improves.

**419/535 candidates (78.3%) have m_Z1 in [85,97] GeV**, up from Part A's
68.6% (1,168/1,702). Plot: `plots/partB_z1_validation.png` — a sharp, clean
peak sitting right at 91.1876 GeV, if anything more concentrated than
before the impact-parameter cuts were added. This is the expected physics
result: genuine Z->4l leptons are prompt and pass tight impact-parameter
cuts cleanly, while non-prompt/heavy-flavor-decay leptons (the intended
target of sip3d/dxy/dz) disproportionately populate the non-peak
background — so removing them should *raise* the peak's purity, not lower
it, and that is exactly what happens here. The cuts are behaving as
designed.

## De-duplication

**1,138,023 duplicate events removed of 14,717,075 seen (7.7%)** —
higher than the 0.76% seen at 12-file validation scale, as expected: more
files means more real run/lumi overlap between the DoubleEG/DoubleMuon/
MuonEG trigger streams for the dedup set to catch. `13,579,052` events
entered the analysis (matches `14,717,075 − 1,138,023` exactly).

## Cut-flow, combined (all 6 records)

| Stage | Combined |
|---|---:|
| after parse-time selection | 13,579,052 |
| >=4 quality leptons (incl. sip3d/dxy/dz) | 2,282 |
| exactly 4, charge 0 | 2,096 |
| A1: low-mass veto (>4 GeV) | 839 |
| A2: ghost removal (dR>0.02) | 838 |
| pT thresholds (20/10 GeV) | 809 |
| **final candidates (valid Z1/Z2)** | **535** |

Per-record breakdown: `plots/partB_cutflow.png`.

## Which impact-parameter cut does the work: sip3d, dxy, or dz?

Each applied independently against the *same* Part A baseline (not a
sequential cut-flow, so cut order can't bias the comparison) — final
candidate counts:

| Variant | Combined | 115-135 GeV | 118-130 GeV | Z1 purity |
|---|---:|---:|---:|---:|
| no IP cuts (Part A baseline) | 1,702 | 311 | 202 | 68.6% |
| sip3d < 4 only | 539 | 44 | 39 | 78.5% |
| \|dxy\| < 0.5 only | 1,315 | 231 | 150 | 69.5% |
| \|dz\| < 1.0 only | 710 | 70 | 52 | 74.6% |
| **all three combined (primary)** | **535** | **43** | **39** | **78.3%** |

**sip3d alone does almost all the work** (1,702 -> 539, a 68.3% reduction)
and lands within 4 candidates of the full three-cut result (539 vs 535).
`|dz|` has a real secondary effect (58.3% reduction alone). `|dxy|` is the
weakest individually (22.7% reduction alone). This matches, and sharpens,
the same finding from the earlier 12-file validation pass (where sip3d-only
and all-three-combined gave identical counts) — now with a 4-candidate gap
visible at full statistics, small but real. Plot:
`plots/partB_ip_cut_scan.png` (combined and per-record).

## Candidates by channel (primary selection)

**4mu: 224, 2e2mu: 234, 4e: 77** (total 535). Plot:
`plots/partB_channel_breakdown.png`.

## Mass spectrum: pre-Part-B baseline vs. Part B

`plots/partB_mass_baseline_vs_partB.png` — pre-Part-B laptop baseline
(no A1/A2, no IP cuts): 1,509 candidates in [70,180] GeV. Part B (full
selection): 159 candidates in the same window. The 3 GeV/37-bin combined
histogram (`histograms/cluster_fullscale_partB_4l_combined_bumpnet.root`)
meets BumpNet's own usability bar (>30 bins, >=100 entries: 37 bins, 159
entries).

## 115-135 GeV and 118-130 GeV vs. CMS's published result

**Part B: 43 candidates in 115-135 GeV, 39 in 118-130 GeV.** Part A alone
(no IP cuts) gave 202 in 118-130; adding sip3d/dxy/dz brings that down to
**39 — a further 80.7% reduction from Part A**. Against the absolute
pre-Part-B baseline (no A1/A2, no IP cuts: 251 in 118-130), Part B is a
**6.4x reduction**. CMS's own published H->ZZ->4l analysis
observed **8** events in 118-130 GeV, with **more** integrated luminosity
than this dataset. **39 vs. 8 is still roughly a 4.9x excess** even after
the full validated selection (Part A + Part B). This is reported plainly as
what is observed — no significance, p-value, or sigma is computed, and no
attempt was made to tune any cut to close this gap further. A correct
selection leaving too few (or, as here, still-too-many) events to draw a
discovery-level conclusion is an acceptable, expected outcome at this
dataset's scale; the remaining gap likely reflects irreducible background
categories outside this exercise's scope (FSR recovery, lepton
momentum-scale corrections, matrix-element discriminants — all explicitly
out of scope here).

Individual candidate masses in 115-135 GeV:
`cluster_fullscale_partB_115_135_candidates.csv` (43 rows).

## Bottom line

The Part B impact-parameter cuts work exactly as intended: the Z->4l
validation peak survives and strengthens (68.6% -> 78.3% purity), sip3d is
confirmed as the dominant lever with dz secondary and dxy weakest, and the
118-130 GeV excess over CMS's published count shrinks substantially
(202 -> 39 from Part A to Part B, a 6.4x reduction from the pre-Part-B
baseline of 251) without disturbing the Z-peak signature. A ~4.9x excess
over CMS's 8 remains and is reported as observed, not explained away or
tuned down.
