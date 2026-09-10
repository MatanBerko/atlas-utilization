# H -> ZZ -> 4l Part B: response to Maryna's review

No new parsing; reused `load_events`/`build_selected_leptons`/
`run_selection` against the same parsed ROOT chunks on Lustre, reproducing
the same 535 primary candidates exactly. Ran interactively on wipp-an1 with
`nice`.

## 1. Legend bug (fixed)

`plot_split()` in `scripts/higgs_4lepton_partB_splits.py` labeled each
histogram bar with the half's **full-mass-range** candidate count (268/267
for parity, 241/294 for era) while the histogram itself only displays
70-180 GeV (actually 78/81 and 79/80 there, summing to 159 either way) —
the legend didn't match what was plotted. Fixed to show the in-window
count (matching the bars) plus the full-range total separately, e.g.
`"2016G (79 in 70-180 GeV, 241 total)"`. Plots regenerated:
`plots/partB_split_era.png`, `plots/partB_split_parity.png`.

**Audited every other plot-generating function** in
`higgs_4lepton_zz_plots.py`, `higgs_4lepton_clean_plots.py`, and
`higgs_4lepton_partB_plots.py` (cutflow, channel-breakdown, baseline-vs-
cleaned, Z1-validation, IP-cut-scan, the fit plot): all already derive
their legend/title numbers directly from the same array being histogrammed
(or, for cutflow/channel plots, have no mass window to mismatch in the
first place). No other instance of this bug found.

## 2. Per-channel split

| Channel | Total | 70-180 GeV | 118-130 | 120.5-123.5 | **123.5-126.5** | 126.5-129.5 | Z1 purity |
|---|---:|---:|---:|---:|---:|---:|---:|
| 4mu | 224 | 84 | 20 | 2 | **14** | 2 | 74.6% |
| 2e2mu | 234 | 52 | 13 | 2 | **7** | 2 | 84.2% |
| 4e | 77 | 23 | 6 | 2 | **2** | 1 | 71.4% |

Plot: `plots/partB_split_channel.png`.

**The 91 GeV Z1 peak is present in all three channels** (71.4-84.2%
purity, consistent with the combined 78.3% — no channel stands out as
anomalous).

**The 123.5-126.5 GeV feature does NOT appear in all three channels
equally, and this is reported plainly rather than explained away:**
4mu shows a clear local bump over its immediate neighbors (2, **14**, 2).
2e2mu shows the same pattern (2, **7**, 2). **4e does not** — its
123.5-126.5 count (2) is essentially flat against its neighbors (2, **2**,
1), no local enhancement visible. It is not confined to a single channel
(it is present in two of three), but it is genuinely absent from the third
(4e) rather than just smaller — visible directly in the third panel of
`partB_split_channel.png`. 4e has the fewest candidates of the three
channels (23 in 70-180 GeV vs. 84 and 52), so this could simply reflect low
statistics rather than a real channel-dependent effect; no attempt is made
here to decide between those two explanations, only to report what is and
isn't there.

## 3. Flat-spectrum investigation

Bin-by-bin contents, 95-180 GeV (3 GeV bins, combined all channels):

```
[ 93.78, 96.76): 2      [126.49,129.46): 5      [153.24,156.22): 1
[ 96.76, 99.73): 1      [129.46,132.43): 3      [156.22,159.19): 2
[ 99.73,102.70): 1      [132.43,135.41): 0      [159.19,162.16): 2
[102.70,105.68): 1      [135.41,138.38): 5      [162.16,165.14): 3
[105.68,108.65): 2      [138.38,141.35): 2      [165.14,168.11): 1
[108.65,111.62): 1      [141.35,144.32): 3      [168.11,171.08): 4
[111.62,114.59): 3      [144.32,147.30): 2      [171.08,174.05): 3
[114.59,117.57): 3      [147.30,150.27): 3      [174.05,177.03): 2
[117.57,120.54): 4      [150.27,153.24): 4      [177.03,180.00): 9
[120.54,123.51): 6
[123.51,126.49): 23
```

Away from the 123.5-126.5 bin, the 95-180 GeV region sits mostly in the
1-4 candidates/bin range with bin-to-bin fluctuation, not a smooth
monotonic fall — e.g. 0 at [132.43,135.41) next to 5 at [135.41,138.38),
or 1 at [165.14,168.11) next to 4 at [168.11,171.08). At only 1-135
candidates total across this whole 85 GeV range, this level of bin-to-bin
scatter is not unexpected. No fit or background model was applied, as
instructed — this is a plain read of the counts.

**Is there a rise in the highest bins approaching 2·m_Z ≈ 182 GeV?
Yes, in the very last bin.** [174.05,177.03) has 2, but [177.03,180.00) —
the last bin before the window closes at 180 — has **9**, clearly above
the neighboring bins on both sides. This is consistent with what would be
physically expected approaching the ZZ threshold (below ~182 GeV one Z
must be off-shell, suppressing the rate; the phase space opens up as both
Z's can go on-shell). It is reported as an observation consistent with
that expectation — no cause is asserted, and this single bin (9 candidates)
is not treated as proof of the threshold effect on its own.

**Off-peak composition** (m4l in [70,180) GeV, excluding [85,97) near the
Z peak and [118,130) near 125 GeV): **70 of 159** candidates in the
70-180 window (44%) fall outside both regions.

| By channel | Count |
|---|---:|
| 4mu | 35 |
| 2e2mu | 25 |
| 4e | 10 |

Roughly proportional to each channel's overall share of the 70-180
window (4mu 84, 2e2mu 52, 4e 23) — no channel is disproportionately
concentrated in the off-peak region.

| By record | Count |
|---|---:|
| DoubleMuon H (30555) | 23 |
| DoubleMuon G (30522) | 19 |
| DoubleEG G (30521) | 15 |
| DoubleEG H (30554) | 12 |
| MuonEG G (30528) | 1 |
| MuonEG H (30561) | 0 |

**This is not evenly spread.** The off-peak/flat component is
concentrated almost entirely in the DoubleMuon and DoubleEG records
(42 and 27 respectively) and is essentially **absent from MuonEG**
(1 + 0 = 1 of 70). This tracks the same pattern seen throughout this
project's MuonEG records having far fewer candidates overall at every
stage (2 final candidates each out of 535, per the earlier IP-cut scan) —
so this is consistent with MuonEG simply contributing very little to the
whole sample, not evidence that the flat component is specifically a
DoubleMuon/DoubleEG artifact. No cause is asserted.

## 4. Units, read from the actual NanoAOD branch titles

Checked live via `uproot` against a real UL2016 NanoAODv9 file (record
30521, same file previously used for the sip3d/dxy/dz check):

| Quantity | Branch title (as stored) | Unit |
|---|---|---|
| `Electron_pt` / `Muon_pt` | `"p_{T}"` / `"pt"` | **GeV** (not stated in the title itself; see note below) |
| `Electron_eta` / `Muon_eta` | `"eta"` | dimensionless (pseudorapidity) |
| `Electron_mass` / `Muon_mass` | `"mass"` | **GeV** (same note) |
| `Electron_pfRelIso03_all` | `"PF relative isolation dR=0.3, total (with rho*EA PU corrections)"` | dimensionless (a *relative*/ratio isolation) |
| `Muon_pfRelIso04_all` | `"PF relative isolation dR=0.4, total (deltaBeta corrections)"` | dimensionless (ratio) |
| `Muon_sip3d` | `"3D impact parameter significance wrt first PV"` | dimensionless (a significance: distance / its own uncertainty) |
| `Electron_sip3d` | `"3D impact parameter significance wrt first PV, in cm"` | dimensionless — **the trailing "in cm" is wrong**, see below |
| `Electron_dxy` / `Muon_dxy` | `"dxy (with sign) wrt first PV, in cm"` | **cm** |
| `Electron_dz` / `Muon_dz` | `"dz (with sign) wrt first PV, in cm"` | **cm** |

**pt/mass unit note:** unlike ATLAS xAOD, where the branch/variable itself
is typically documented in MeV, CMS NanoAOD's `pt`/`mass` branch titles
carry no unit string at all. The GeV convention comes from CMS's public
NanoAOD documentation and is independently confirmed empirically in this
project (`services/parsing/schemas.py`): an e+e- pair's invariant mass
computed directly from the raw branch values peaks at ~91 GeV, not
~91,000, before any unit scaling is applied.

**Flagging explicitly for Maryna, coming from ATLAS: CMS NanoAOD's native
unit is GeV, where ATLAS xAOD's native unit is MeV** — the opposite
convention. This project's schema layer
(`services/parsing/schemas.py::native_pt_unit`) already tracks this
per-release (`"GeV"` for CMS NanoAOD, `"MeV"` for the ATLAS
DAOD/PHYSLITE schemas used elsewhere in this project) specifically to
avoid a 1000x scaling bug when mixing the two — this was in fact a real
bug caught and fixed earlier in this project's history (see the
"CMS invariant-mass 1000x scale bug" work). It is not a live issue for the
current Part B selection, which stays entirely within the CMS/GeV schema,
but is worth stating plainly since it's exactly the kind of mistake an
ATLAS-accustomed reader could otherwise make when reading these numbers.

**Electron_sip3d's "in cm" is confirmed wrong, and is not followed.** A
significance is, by construction, a ratio of a distance to its own
uncertainty (both in the same length unit), and is therefore
dimensionless — this is also what `Muon_sip3d`'s own title correctly
states, with no "in cm" suffix. `Electron_sip3d`'s trailing ", in cm" is
an inconsistent copy-paste from the neighboring `dxy`/`dz` titles in CMS's
own NanoAOD metadata (both of those genuinely are in cm). The selection
used throughout this project (`sip3d < 4`, the standard dimensionless CMS
H->ZZ->4l working point) treats `sip3d` as dimensionless for both flavors,
correctly ignoring the electron title's erroneous unit suffix.
