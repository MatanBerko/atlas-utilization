# Stage 3: resolution-matched binning + analysis-grade photon cuts

Branch: `analysis/higgs-diphoton-stage3-resolution`, branched off
`analysis/higgs-diphoton-stage2-fullscale` (commit `2964037`), not off master.
No Stage 0/1/2 branch or master was modified.

## 1. Data reuse — no re-download, no re-parse

Stage 2's parsed output at
`output/cms_higgs_diphoton_stage2_20260907_201708/parsed_data/` was checked
**before any data access** and found complete:

- `parsed_record_30554_chunk0.root` + `parsed_record_30554_final.root`
  (both filenames say "30554" but contain mixed 30521+30554 data — a known
  pre-existing `EventAccumulator` labeling quirk already documented in
  Stage 2's own report; per-event attribution uses the `source_record`
  field, not the filename).
- Sum of events: **3,831,837**, exactly matching Stage 2's reported final
  diphoton-candidate count for all 133/133 files.
- Confirmed present: `Photons_pt`, `Photons_eta`, `Photons_phi`,
  `Photons_mass`, `Photons_cutBased`, `Photons_electronVeto`,
  `source_record`.

**Result: reused as-is. No re-download of the 160 GB dataset, no re-parse.**
The whole of Stage 3 is a pure post-hoc analysis script
(`scripts/higgs_diphoton_stage3_report.py`) run against this already-parsed
data; it ran to completion in under a minute inside the pipeline Docker
image, as the task predicted.

## 2. ECAL barrel/endcap gap — confirmed boundary

Applied cut: reject photons with `1.4442 < |eta| < 1.566`.

These values were **not assumed** — two independent checks were attempted:

1. **Live NanoAOD cross-check (attempted, blocked):** tried to open a fresh
   UL2016 NanoAODv9 file over XRootD to look for a supercluster-eta flag
   (e.g. `Photon_isScEtaEB`/`isScEtaEE`). Blocked by a genuine network
   outage on this machine — a raw TCP connect to `eospublic.cern.ch:1094`
   timed out (`OSError: Operation expired` / `Socket timeout`), while HTTPS
   to `opendata.cern.ch:443` succeeded. Per the standing rule, no workaround
   (no cert bypass, no DNS override, no protocol switch) was attempted —
   this sub-check was simply dropped in favor of the second method below.
2. **Documentation-based confirmation (succeeded):** the CMS Collaboration's
   own photon-reconstruction performance paper, arXiv:1502.02702 (JINST),
   fetched via its `ar5iv.arxiv.org` HTML mirror, states verbatim:
   > "...excluding the last two crystals at each end of the barrel
   > (|η|<1.4442). The outer circumferences of the endcaps are obscured by
   > services passing between the barrel and the endcaps, and this area is
   > removed from the fiducial region by excluding the first ring of
   > trigger towers of the endcaps (|η|>1.566)."

   This ties the boundary to **fixed ECAL crystal/trigger-tower geometry**,
   not to any per-era calibration — so it applies unchanged to this UL2016
   NanoAODv9 production. Applied directly to `Photon_eta`: unlike
   electrons, photons have no track, so there is no track-vs-supercluster
   eta ambiguity to resolve.

Effect: 3,831,837 → **3,583,609** diphoton events with ≥2 photons surviving
the gap cut (same for all three ID variants, since the gap cut is ID-blind).

## 3. Photon ID variants (loose / medium / tight)

Stage 2's parsed data already only contains `cutBased>=1` (loose) photons,
so loose is exactly what's on disk; medium (`>=2`) and tight (`>=3`) are
strict subsets, computed for free from the same parsed arrays — no
additional data needed for any of the three.

## 4. Asymmetric pT cut — where it's implemented

Per the task's explicit instruction, this is a **pair-level** cut (leading
photon pT > mγγ/3, subleading pT > mγγ/4) that depends on the diphoton mass
itself, so it was **not** forced into `services/calculations/physics_calcs.py`'s
per-object kinematic-cut machinery (which can only express cuts on a single
object's own kinematics, independent of any other object or of a derived
quantity like the pair mass). It is implemented entirely in
`scripts/higgs_diphoton_stage3_report.py::build_cutflow()`, applied strictly
**after** `leading_pair_mass()` computes the diphoton mass from the 2
leading surviving photons at that cut stage — see the `asym_pass` mask
there.

## 5. Full cut-flow (all counts are diphoton-candidate events)

| Stage | loose (≥1) | medium (≥2) | tight (≥3) |
|---|---:|---:|---:|
| Stage 2 candidates | 3,831,837 | 3,831,837 | 3,831,837 |
| after ECAL gap | 3,583,609 | 3,583,609 | 3,583,609 |
| after ID threshold | 3,583,609 | 2,113,527 | 1,522,231 |
| after asymmetric pT | 2,848,402 | 1,725,328 | 1,249,214 |
| **final (100–180 GeV window)** | **420,822** | **254,173** | **185,500** |

The medium variant (cutBased≥2) is the **primary** selection used for the
histograms below.

Plot: `plots/diphoton_stage3_cutflow.png` — log-scale bar chart of the above
table across all three variants.

## 6. Histograms (medium ID, 100–180 GeV window)

| | bins | entries | non-empty bins | meets >30-bin bar | meets ≥100-entry bar |
|---|---:|---:|---:|---|---|
| **Primary (2 GeV)** | 40 | 254,173 | 40 | **PASS** | **PASS** |
| Secondary (1 GeV) | 80 | 254,173 | 80 | **PASS** | **PASS** |

Files (BumpNet naming convention, `uproot.recreate`):
- `histograms/diphoton_stage3_2gev_bumpnet.root` →
  `mass_g0g1_cat_0ex_0mx_0jx_2gx_0tx_0bx_width_2.0`
- `histograms/diphoton_stage3_1gev_bumpnet.root` →
  `mass_g0g1_cat_0ex_0mx_0jx_2gx_0tx_0bx_width_1.0`

The 2 GeV bin width was chosen as primary per the task's instruction to
roughly approximate CMS's diphoton mass resolution near 125 GeV (~1–2 GeV),
and because it clears BumpNet's 30-bin training minimum by a comfortable
margin (40 bins) — the BumpNet paper itself notes degraded performance
close to the 30-bin floor, which is why the ~100–155 GeV / 2 GeV window used
in its own Figure 15 (~28 bins) was deliberately widened here to 100–180 GeV.

## 7. Background fit and the Figure-15-style plot

Plot: `plots/diphoton_stage3_2gev_bumpnet_style.png` — 2 panels:
- **Top:** data points (Poisson error bars) + a **4th-order polynomial**
  background fit (`numpy.polyfit`, weighted by per-bin Poisson `sqrt(N)`),
  fit over the full 100–180 GeV range with no blinding/exclusion window.
  A 4th-order polynomial was chosen because it is the exact convention the
  BumpNet paper's own referenced ATLAS H→γγ figure (Fig. 15) is built on —
  direct precedent for this specific plot, not a general default choice for
  diphoton continua.
- **Middle:** residuals, plotted as raw **(data − fit) counts** — deliberately
  *not* normalized by `sqrt(fit)`, specifically to avoid producing a
  quantity that could be mistaken for a per-bin significance/pull value.
- **No third panel.** Per the task's instruction, no significance curve was
  computed, plotted, or implied anywhere.

**Explicit framing, present on the plot itself (title) and repeated here:**
the background fit and residual panel are **illustrative only**. No
significance, p-value, or sigma value is computed, estimated, quoted, or
implied anywhere in this script or report, and no residual structure is
described as evidence of a signal. Determining significance is BumpNet's
job — not this script's, and not a matter of visual inspection of this
plot.

## 8. BumpNet status

Per the task's instruction, BumpNet was **not** re-checked for on this
machine in this task — it was already confirmed absent during Stage 2 and
that finding was not revisited. The deliverable of Stage 3 is the two
histogram ROOT files above, ready for BumpNet if/when it becomes available.

## 9. Honest next step

The primary (2 GeV, medium-ID) histogram is a clean, monotonically falling
diphoton continuum over 100–180 GeV with 254,173 entries across 40 bins —
comfortably past both of BumpNet's usability thresholds. The residual panel
shows visible structure at the low-mass edge (100–113 GeV) that is most
plausibly a polynomial edge-fit artifact from fitting a steeply falling
curve right at the window boundary, not a physics claim — consistent with
the explicit "illustrative only" framing above. The honest next step is to
actually run this histogram through BumpNet once it's available on some
machine, since that determination was explicitly out of scope for this
script and was not attempted here.
