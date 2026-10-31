# Matan's decisions on the MC expansion plan (taken 26–31 Oct 2026, recorded 31 Oct 2026)

Recorded on branch `plan/mc-expansion-20261026` (fork only). These are **Matan's decisions** on the questions
of `PLAN.md` §6 (D1–D15) and `atlas_mapping/MAPPING.md`. They are recorded here, not reopened. They decide
*which samples* are planned and *which convention* each cross-section proposal follows; the cross-section
**values** in `XSEC_PROPOSALS_v2.md` stay PROPOSED until Matan confirms them sample by sample. Nothing enters
any registry or config; no cross section is applied anywhere.

The individual decisions were taken between 26 and 31 Oct 2026; the per-decision day was not given to me, so
it is not recorded (not guessed).

**Guiding principle:** where the choice is free, **match what ATLAS does**. The documented exceptions are listed
(E1 below, and the cases where ATLAS has no nominal sample: ON HOLD).

How the ATLAS numbers below were checked: `atlas_mapping/atlas_bkg_metadata.json` (public metadata,
atlasopenmagic release 2024r-pp, saved 27 Oct), σ × kFactor × genFiltEff; VERIFIED BY RUNNING on 31 Oct
(`python3` over that file). ATLAS numbers are cross-checks only, never a CMS source.

## The decisions

**D1 — W+jets set.** NLO FxFx jet-binned 0J / 1J / 2J (69715 / 69717 / 69719), **each used alone, no
stitching** (never together with the inclusive NLO 69745 or any LO W sample).

**D2 — W+jets normalisation.** RazorAnalyzer 61,526.7 pb (SECONDARY source, the same table as our DY), split
over the three pieces by their generator (portal) values: k = 61,526.7 / (53,300 + 8,958 + 3,330) = 0.938079.
ATLAS arXiv:1603.09222 Table 3 (3 × 20.08 nb = 60,240 pb) is recorded as the **primary cross-check** (−2.1 %).

**D3 — W+jets despite its low MC luminosity.** W+jets is added although its MC luminosity is only
0.13–0.29 × the data (2.05 / 4.72 / 2.66 fb⁻¹ vs 16.39 fb⁻¹; probe of 26 Oct). Consequences:
- the delivery README must state it;
- the **first build** must count the histograms where **one W+jets event makes up > 50 % of a bin's MC
  content**, and show real PNGs of the worst cases.

**D4 — single-top t-channel: 4-flavour.** POWHEG+MadSpin, inclusive decays: top **64759**, antitop **64659**
(NOT the 5-flavour 64793 / 64693), to match ATLAS 410658 / 410659. The public metadata describes both ATLAS
samples as four-flavour ("ME NNPDF3.04f NLO" for 410658; "ME NNPDF3.0 four-flavour NLO" for 410659; VERIFIED BY
RUNNING, metadata `description` field).

**D5 — single-top normalisation: match ATLAS = the OLD LHC Top WG page `SingleTopRefXsec` throughout.**
- t-channel **136.02 pb (top) / 80.95 pb (antitop)** (Hathor NLO);
- s-channel **10.32 pb** (top + antitop, NLO);
- tW **71.7 pb** (the delivered tW stays unchanged).

The newer `SingleTopNNLORef` values (t-channel 134.2 / 80.0, s-channel 11.073, tW 79.3 pb) are recorded as
**alternatives only**.

ATLAS check (VERIFIED BY RUNNING): ATLAS's t- and s-channel samples hold the leptonic top decay only, and
σ × k ÷ 136.02 / 80.95 / 10.32 gives the same implied branching ratio, 0.3246, for all three:
- 410658: 36.996 × 1.1935 = 44.155 pb; 44.155 / 136.02 = 0.32462;
- 410659: 22.173 × 1.1849 = 26.273 pb; 26.273 / 80.95 = 0.32455;
- 410644 + 410645: 2.027 × 1.017 + 1.2674 × 1.0167 = 3.3500 pb; 3.3500 / 10.32 = 0.32462;
- tW: 601352 + 601355 = 35.972 + 36.003 = **71.975 pb** (kFactor 1).

**D6 — Z branching ratios: PDG individually measured values** (pdglive S044): ee 3.3632 %, μμ 3.3662 %,
ττ 3.3696 %, invisible 20.000 %, hadrons 69.911 %. **Re-checked on pdglive on 31 Oct 2026, unchanged**
(VERIFIED BY RUNNING: `curl https://pdglive.lbl.gov/Particle.action?node=S044`, DECAY MODES Γ1, Γ2, Γ3, Γ7, Γ8 =
(3.3632 ± 0.0042) %, (3.3662 ± 0.0066) %, (3.3696 ± 0.0083) %, (20.000 ± 0.055) %, (69.911 ± 0.056) %).
ATLAS uses BR(Z → νν) = 0.2000 (Matan's statement; consistent with the ZZ → 2ℓ2ν arithmetic of D14).
The W values (pdglive S043) were re-checked the same day, also unchanged: eν 10.71 %, μν 10.63 %, τν 11.38 %,
hadrons 67.41 %.

**D7 — tt̄tt̄ (68045) = 11.97 fb** (complete NLO QCD+EW, arXiv:1711.02116 Table 5), matching ATLAS 412043:
10.673 fb × k 1.1267 = **12.025 fb** (VERIFIED BY RUNNING; ratio ATLAS / CMS = 1.005).

**D8 — tWℓℓ: ON HOLD.** ATLAS has no nominal tWZ counterpart that Matan accepts; waiting for Maryna.

**D9 — dibosons: keep the 14 Oct NNLO convention for ALL dibosons, new and delivered.**
- WZ and ZZ: generator value × NNLO/NLO k-factor:
  - WZ k = 51.11 / 46.068 = 1.10945 (arXiv:1604.08576 Table 1);
  - ZZ k = 16.91 / 14.51 = 1.16540 (arXiv:1405.2219 Table 1).
- WW: 118.7 pb × BR (arXiv:1408.5243 Table 1).

**Documented exception E1 (to the "match ATLAS" principle).** ATLAS normalises its dibosons to the **Sherpa
generator values with kFactor = 1** and has **no gg → ZZ / gg → WW samples**. The CMS NNLO totals used here
*include* those loop-induced gluon-gluon processes, so matching ATLAS would remove real physics. We therefore
keep the NNLO convention. Measured size of the difference, CMS ÷ ATLAS for the same process (Matan's numbers,
from MAPPING.md table A as ATLAS/CMS inverted):

| process | CMS ÷ ATLAS |
|---|---:|
| WZ → ℓνqq | 0.92 |
| WZ → ℓννν | 1.22 |
| WW → ℓνqq | 1.09 |
| WZ → 3ℓν | 1.24 |
| ZZ → 4ℓ | 1.19 |
| WW → 2ℓ2ν | 1.05 |

(Check against MAPPING.md table A, ATLAS/CMS: WZ → ℓνqq 1.08, VV → ℓννν 0.82, WW → ℓνqq 0.92, VV → ℓℓℓν 0.81,
VV → ℓℓℓℓ 0.84, VV → ℓℓνν 0.95; the inverses are 0.93, 1.22, 1.09, 1.24, 1.19, 1.05. The first differs from
0.92 only by rounding of the printed 1.08: 10.16 / 10.99 = 0.925.)

**D10 — tribosons: only the large ext1 record per process:** 72701 (WWW), 72711 (WWZ), 72761 (WZZ), 75600 (ZZZ).

**D11 — Z → νν + jets ADDED as a last tier 6.** HT-binned LO ZJetsToNuNu with HT > 100 GeV: records 74894
(100–200), 74898 (200–400), 74902 (400–600), 74904 (600–800), 74906 (800–1200), 74896 (1200–2500), 74900
(2500–Inf). No stitching needed (exclusive HT bins); HT < 100 GeV is not covered. **Droppable later** if QCD
needs the file headroom.

**D12 — Drell–Yan extras.** No extra QCD Drell–Yan (no 4–10 GeV sample; ATLAS also stops at 10 GeV).
**ADD electroweak V + 2 jets in tier 3:** EWKZ2Jets_ZToLL_M-50 **35999**, EWKWMinus2Jets_WToLNu_M-50 **35987**,
EWKWPlus2Jets_WToLNu_M-50 **35993**. ATLAS counterparts (VERIFIED BY RUNNING): 700358–700360 Z → ee / μμ / ττ
+ 2 jets, 0.77937 / 0.77941 / 0.77911 pb (≈ 0.779 pb per lepton flavour); 700362–700364 W → eν / μν / τν + 2 jets,
8.5022 / 8.5027 / 8.5013 pb (≈ 8.50 pb per flavour).

**D13 — Higgs scope.** The 15 planned tier-5 samples (37474, 68601, 41877, 41873, 41914, 40095, 37446, 68591,
71297, 70453, 74684, 37616, 68741, 71227, 70383) **plus 11 new**:
- H → μμ: 37432, 68571, 71295, 70451, 74682;
- H → Zγ (Z → ℓℓ): 37604, 68731, 71145, 70301, 74292;
- gg → ZH, H → ZZ → 4ℓ: 40062.

Deferred (not in this task): the Dalitz H → γ*γ samples, 68833, 74314.

**D14 — ZZTo2L2Nu 75567 ADDED in tier 2.** Proposed normalisation per D9 = portal 0.9738 pb (MiniAOD 75566) ×
1.1654 = 1.135 pb, **CONDITIONAL** on verifying that the 15 Oct "42 % mismatch" (0.9738 ÷ [on-shell 16.91 × 2 ×
0.10099 × 0.2000 = 0.6831] = 1.426) comes from γ* → ℓℓ / low-m(ℓℓ) phase space. Otherwise the fallback is
**0.6831 pb**. (The generator-card check is in `XSEC_PROPOSALS_v2.md`, card of 75567, and `PLAN_v2_summary.md`.)

**ON HOLD (no ATLAS nominal counterpart; waiting for Maryna).** tZq_ll 68325, ST_tWll 64873, TTZToQQ 68206,
TTZToLL_M-1to10 68185. Their existing cards are kept, marked ON HOLD; nothing is deleted.

**Deferred (unchanged):** QCD multijet and photons.

**D15 (information only, no decision asked):** the matching-efficiency open point stays as in PLAN.md §6;
the portal matching efficiency is never multiplied in.

## Final new-sample list by tier

| tier | samples | records |
|---|---:|---|
| 1 | 7 | 69715, 69717, 69719 (W+jets 0J/1J/2J), 64759, 64659 (t-channel 4f top/antitop), 64635 (s-channel leptonic), 67841 (tt̄ hadronic) |
| 2 | 6 | 72742 (WZ → 2Q2L), 75573 (ZZ → 2Q2L), 72738 (WZ → ℓνqq), 72658 (WW → ℓνqq), 72740 (WZ → ℓννν), 75567 (ZZ → 2ℓ2ν) |
| 3 | 7 | 72701, 72711, 72761, 75600 (WWW, WWZ, WZZ, ZZZ ext1), 35999, 35987, 35993 (EW Z/W⁻/W⁺ + 2 jets) |
| 4 | 4 (+ 4 on hold) | 67645 (tt̄H → bb̄), 67691 (tt̄H → non-bb̄), 68083 (tt̄W → qq), 68045 (tt̄tt̄); ON HOLD: 68325, 64873, 68206, 68185 |
| 5 | 26 | 37474, 68601, 41877, 41873, 41914, 40095, 37446, 68591, 71297, 70453, 74684, 37616, 68741, 71227, 70383, 37432, 68571, 71295, 70451, 74682, 37604, 68731, 71145, 70301, 74292, 40062 |
| 6 | 7 | 74894, 74898, 74902, 74904, 74906, 74896, 74900 (Z → νν + jets, HT-binned) |
| **total** | **57 planned + 4 on hold** | machine-readable: `plan_samples_v2.py` |

What changed against `PLAN.md` (26 Oct): t-channel 5f → 4f (D4); single-top values NNLO → old NLO page (D5);
tt̄tt̄ 8.09 → 11.97 fb (D7); ZZ → 2ℓ2ν added (D14); EW V + 2 jets added (D12); Z → νν added as tier 6 (D11);
11 Higgs added (D13); tZq, tWℓℓ, tt̄Z → qq, tt̄ + low-mass ℓℓ moved to ON HOLD.
