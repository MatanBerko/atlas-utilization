# MC expansion plan v2 — summary after Matan's decisions (31 Oct 2026)

Branch `plan/mc-expansion-20261026` (fork only). **Planning only:** no production, no build, nothing in any
registry or config, no cross section applied. Decisions: `DECISIONS.md`. Cross-section cards: `XSEC_PROPOSALS_v2.md`.
`PLAN.md`, `XSEC_PROPOSALS.md` and `atlas_mapping/MAPPING.md` are kept as they were (one pointer line added at the top
of the first two). Every number is VERIFIED BY RUNNING unless marked ESTIMATE, PROPOSED or UNVERIFIED.

## In plain words

**The final list.** 57 new samples in 6 tiers, plus 4 kept ON HOLD:

| tier | what | samples |
|---:|---|---:|
| 1 | W+jets (3 pieces), single top t-channel (4-flavour, top + antitop), s-channel, tt̄ fully hadronic | 7 |
| 2 | dibosons with one boson → quarks (5), and ZZ → ℓℓνν | 6 |
| 3 | tribosons (4), electroweak Z/W + 2 jets (3) | 7 |
| 4 | tt̄H (bb̄ and non-bb̄), tt̄W → qq, four tops (+ tZq, tWℓℓ, tt̄Z → qq, tt̄ + low-mass ℓℓ ON HOLD) | 4 (+4) |
| 5 | Higgs: the 15 planned + H → μμ (5), H → Zγ (5), gg → ZH → ZZ (1) | 26 |
| 6 | Z → νν + jets, 7 HT bins from 100 GeV | 7 |

**What changed compared with PLAN.md (26 Oct).**
- t-channel single top: 4-flavour samples instead of 5-flavour (D4), normalised to the old Top WG NLO values 136.02 / 80.95 pb (D5).
- s-channel: 10.32 pb × 0.3272 = 3.377 pb (D5; was 3.623).
- Four tops: 11.97 fb (D7; was 8.09).
- Added: ZZ → ℓℓνν (D14), electroweak V + 2 jets (D12), Z → νν as tier 6 (D11), and 11 Higgs samples (D13).
- Moved to ON HOLD: tZq, tWℓℓ, tt̄Z → qq, tt̄ + low-mass ℓℓ.

**Probe of the 35 samples never probed before (PBS array 5420807[], 31 Oct).** All 35 jobs finished normally.
- **No sample is missing a branch.** All 42 branches our production reads are in every file, so none of these
  samples would make production fail.
- The weight sums in the files agree with the files' own bookkeeping to better than 5 in 100 million.
- The fraction of negative weights matches the portal everywhere (largest difference 0.003, on files with only a few thousand events).

Nothing surprising in the probe. Two surprises came from the cards instead (below).

**What the cards show.**
1. **ZZ → ℓℓνν (the "42 % question", D14).** Its generator settings are *the same* as for our delivered ZZ → 4ℓ, including
   "minimum lepton-pair mass 4 GeV". The generator also includes virtual photons, so the lepton pair is not
   always a real Z. That supports the explanation that the extra 42 % sits at low pair mass. **It is only qualitative**:
   the card cannot say how big that low-mass part is. Whether that is enough to take 1.135 pb, or to fall back to 0.683 pb,
   is for Matan to decide. A one-job check that would measure it is described in the card.
2. **Electroweak V + 2 jets: CMS is about 2.7 × ATLAS per lepton flavour** (Z: 2.07 vs 0.78 pb; W: 23.7 vs 8.50 pb).
   This is not a contradiction; the two samples are made differently:
   - CMS keeps every purely electroweak diagram, including "two bosons, one of which decays to quarks";
   - ATLAS removes those diagrams (its "Min_N_TChannels" option);
   - CMS also uses very loose cuts (jet pT > 10, m(jj) > 10 GeV).

   **New overlap flag:** that two-boson part of the CMS samples is the same physics as our tier-2 dibosons, so using both
   counts it twice there. Not decided; options are in the cards.
3. **gg → ZH → ZZ (40062) is not a plain "H → 4 leptons" sample.** It keeps events with 4 leptons from either Higgs
   decay or the associated Z. The efficiency of that filter is not published, and the portal record looks odd. Three options
   are listed; the sample is tiny (≲ 4 events before selection), so the choice matters very little.
4. **Z → νν HT bins:** 100–200–400–600–800–1200–2500–∞ GeV, contiguous and exclusive (cards). The probe confirms
   at generator level that each file stays inside its bin.

**Cross-section cards for the review.** 61 cards in `XSEC_PROPOSALS_v2.md` (57 planned + 4 ON HOLD):
- 31 unchanged from 26 Oct;
- 4 changed by a decision: 64759 and 64659 (D4, D5), 64635 (D5), 68045 (D7);
- 11 new with a definite proposal (75567 and 10 Higgs);
- **11 need a decision on the value** (3 EW V + 2 jets, 7 Z → νν, 40062): they list options and do not choose.

The 4 ON HOLD cards are kept but are not for review now.

**Cost.** All six tiers fit under the 125,000-file limit: 1,332 portal files, 786 M events, ~180 CPU hours, ~25,900 new
cluster files, giving ~119,600 files (ESTIMATE, from today's measured 93,638).

## Probe results (step 2; VERIFIED BY RUNNING)

PBS array **5420807[]** (`-J 0-34`, queue N, io=25, mem 4 GB, 1 h), submitted 31 Oct from the pinned checkout
`/storage/agrp/berkom/atlas-utilization/checkouts/mcplan2_20261031/repo_53c6b8ca4122580e434dde03a0d775b008729510`
(HEAD asserted; every log prints `commit=53c6b8c…`), outputs in `work/mcplan2_20261031/{probe,logs}`. 35 / 35 `Exit status: 0`,
wall time ≤ 30 s each. File index 0 of each record, read with uproot by `probe_sample.py --list v2`.
Raw results: `evidence/probe_v2/probe_<recid>.json`, logs `evidence/probe_v2/logs/`, plots `plots/genweight_<recid>.png`.

- `branches_missing`: **empty for all 35** (42 production branches incl. `genWeight`, `L1PreFiringWeight_Nom`,
  `Pileup_nTrueInt`); `LHE_HT` and `LHE_Njets` present in all 35.
- Σ genWeight (file) ÷ Runs `genEventSumw` − 1: |·| ≤ 4.5 × 10⁻⁸ for all 35.
- Negative-weight fraction: matches the portal within 0.003 everywhere (largest: 70383 0.0228 vs 0.0254, 3,072 events; 71227 0.0297 vs 0.0278, 13,797 events).
- The LO MadGraph samples (EW V + 2 jets, Z → νν) and 40095 / 40062 have one weight value only (no negative weights).
- Z → νν, LHE_HT in file 0 (min / median / max, GeV): 74894 100.0 / 129 / 200.0; 74898 200.0 / 250 / 400.0;
  74902 400.0 / 463 / 600.0; 74904 600.0 / 670 / 800.0; 74906 800.0 / 915 / 1199.9; 74896 1200.0 / 1382 / 2480;
  74900 2500.0 / 2780 / 7794.

| record | sample | events in file 0 | branches missing (of 42) | Σw file ÷ Runs Σw − 1 | negative-weight fraction (probe / portal) | N_eff/N (file 0) | plot |
|---|---|---:|---|---:|---|---:|---|
| 64759 | ST_t-channel_top_4f_InclusiveDecays | 861,000 | none | -1.2e-08 | 0.0314 / 0.0316 | 0.878 | `plots/genweight_64759.png` |
| 64659 | ST_t-channel_antitop_4f_InclusiveDecays | 860,000 | none | -4.5e-08 | 0.0295 / 0.0293 | 0.885 | `plots/genweight_64659.png` |
| 75567 | ZZTo2L2Nu | 750,000 | none | 4.8e-09 | 0.0011 / 0.0011 | 0.996 | `plots/genweight_75567.png` |
| 35999 | EWKZ2Jets_ZToLL_M-50 | 4,000 | none | 0.0e+00 | 0.0000 / 0.0000 | 1.000 | `plots/genweight_35999.png` |
| 35987 | EWKWMinus2Jets_WToLNu_M-50 | 161,000 | none | 0.0e+00 | 0.0000 / 0.0000 | 1.000 | `plots/genweight_35987.png` |
| 35993 | EWKWPlus2Jets_WToLNu_M-50 | 13,000 | none | 0.0e+00 | 0.0000 / 0.0000 | 1.000 | `plots/genweight_35993.png` |
| 74894 | ZJetsToNuNu_HT-100To200 | 121,434 | none | 0.0e+00 | 0.0000 / 0.0000 | 1.000 | `plots/genweight_74894.png` |
| 74898 | ZJetsToNuNu_HT-200To400 | 1,157,106 | none | 0.0e+00 | 0.0000 / 0.0000 | 1.000 | `plots/genweight_74898.png` |
| 74902 | ZJetsToNuNu_HT-400To600 | 612,424 | none | 0.0e+00 | 0.0000 / 0.0000 | 1.000 | `plots/genweight_74902.png` |
| 74904 | ZJetsToNuNu_HT-600To800 | 9,272 | none | 0.0e+00 | 0.0000 / 0.0000 | 1.000 | `plots/genweight_74904.png` |
| 74906 | ZJetsToNuNu_HT-800To1200 | 62,724 | none | 0.0e+00 | 0.0000 / 0.0000 | 1.000 | `plots/genweight_74906.png` |
| 74896 | ZJetsToNuNu_HT-1200To2500 | 1,249 | none | 0.0e+00 | 0.0000 / 0.0000 | 1.000 | `plots/genweight_74896.png` |
| 74900 | ZJetsToNuNu_HT-2500ToInf | 96,199 | none | 0.0e+00 | 0.0000 / 0.0000 | 1.000 | `plots/genweight_74900.png` |
| 41873 | HWminusJ_HToWW_M-125 | 22,461 | none | -1.9e-08 | 0.0263 / 0.0262 | 0.898 | `plots/genweight_41873.png` |
| 41914 | HZJ_HToWW_M-125 (ext1) | 918,060 | none | -4.2e-08 | 0.0298 / 0.0296 | 0.884 | `plots/genweight_41914.png` |
| 40095 | GluGluZH_HToWW_ZTo2L_M-125 (ext1) | 936,318 | none | 1.9e-08 | 0.0000 / 0.0000 | 1.000 | `plots/genweight_40095.png` |
| 68591 | VBFHToTauTau_M125 | 2,504 | none | 5.1e-10 | 0.0012 / 0.0006 | 0.995 | `plots/genweight_68591.png` |
| 71297 | WplusHToTauTau_M125 | 72,352 | none | -3.1e-08 | 0.0281 / 0.0279 | 0.891 | `plots/genweight_71297.png` |
| 70453 | WminusHToTauTau_M125 | 599,276 | none | -2.8e-08 | 0.0264 / 0.0265 | 0.897 | `plots/genweight_70453.png` |
| 74684 | ZHToTauTau_M125 | 640,875 | none | 2.4e-08 | 0.0291 / 0.0290 | 0.887 | `plots/genweight_74684.png` |
| 37616 | GluGluHToZZTo2L2Nu_M125 | 252,000 | none | 2.3e-09 | 0.0051 / 0.0049 | 0.980 | `plots/genweight_37616.png` |
| 68741 | VBF_HToZZTo2L2Nu_M125 | 8,000 | none | -1.4e-08 | 0.0005 / 0.0007 | 0.998 | `plots/genweight_68741.png` |
| 71227 | WplusH_HToZZTo4L_M125 | 13,797 | none | -2.0e-08 | 0.0297 / 0.0278 | 0.885 | `plots/genweight_71227.png` |
| 70383 | WminusH_HToZZTo4L_M125 | 3,072 | none | -3.0e-08 | 0.0228 / 0.0254 | 0.911 | `plots/genweight_70383.png` |
| 37432 | GluGluHToMuMu_M125 | 500,000 | none | 2.3e-08 | 0.0052 / 0.0052 | 0.979 | `plots/genweight_37432.png` |
| 68571 | VBFHToMuMu_M125 | 943,000 | none | 5.1e-10 | 0.0007 / 0.0007 | 0.997 | `plots/genweight_68571.png` |
| 71295 | WplusHToMuMu_M125 | 300,000 | none | -3.1e-08 | 0.0275 / 0.0275 | 0.893 | `plots/genweight_71295.png` |
| 70451 | WminusHToMuMu_M125 | 300,000 | none | -2.8e-08 | 0.0262 / 0.0262 | 0.898 | `plots/genweight_70451.png` |
| 74682 | ZHToMuMu_M125 | 496,320 | none | 2.4e-08 | 0.0290 / 0.0290 | 0.887 | `plots/genweight_74682.png` |
| 37604 | GluGluHToZG_ZToLL_M-125 | 1,856 | none | 1.7e-08 | 0.0043 / 0.0052 | 0.983 | `plots/genweight_37604.png` |
| 68731 | VBFHToZG_ZToLL_M-125 | 2,646 | none | 5.1e-10 | 0.0011 / 0.0006 | 0.995 | `plots/genweight_68731.png` |
| 71145 | WplusH_HToZG_WToAll_M-125 | 161,991 | none | 2.4e-08 | 0.0299 / 0.0299 | 0.884 | `plots/genweight_71145.png` |
| 70301 | WminusH_HToZG_WToAll_M-125 | 18,811 | none | 4.4e-08 | 0.0253 / 0.0257 | 0.901 | `plots/genweight_70301.png` |
| 74292 | ZH_HToZG_ZToAll_M-125 | 19,000 | none | -2.8e-08 | 0.0286 / 0.0286 | 0.889 | `plots/genweight_74292.png` |
| 40062 | GluGluToZH_HToZZTo4L_M125 | 985 | none | 0.0e+00 | 0.0000 / 0.0000 | 1.000 | `plots/genweight_40062.png` |

(Same table: `evidence/probe_v2_table.md`.)

## Generator-card findings (step 3)

Cards fetched 31 Oct by `fetch_cards_v2.py` into new directories `evidence/cards/<recid>/` (index `evidence/cards/index_v2.json`).
40062's two portal card links return HTTP 404; its cards were fetched from the CMS genproductions links quoted in its
own record (`evidence/cards/40062/`).

**75567 ZZTo2L2Nu vs 75589 ZZTo4L (D14).**
- 75567 `powheg.input`: line 2 `mllmin 4d0 ! default 0.1 GeV this is minimum invar mass for Z leptons`; line 31 `leptons-nu 1`.
- 75589: the same file except the PDF set (306000 vs 325300) and `leptonic 1`.
- Neither file sets a Z-mass window or a `zerowidth` option.
- The POWHEG-BOX-V2 ZZ code includes all four-lepton diagrams (singly resonant, interference), except W+W−/ZZ
  interference (arXiv:1311.1365 §1).
- Therefore the charged pair is Z/γ* down to 4 GeV, which **supports the low-m(ℓℓ) explanation qualitatively**.
- The size is **not** shown by the card:
  - generator 0.9738 pb vs on-shell NNLO 0.6831 pb (× 1.426);
  - vs on-shell NLO 0.5861 pb (× 1.661).
- For comparison, the same setting makes our ZZTo4L portal value 9.0 × its on-shell NLO expectation (both pairs can be γ*).
- Open (UNVERIFIED): whether `leptons-nu` includes τ and all three ν.

**35999 / 35987 / 35993 EW V + 2 jets vs ATLAS 700358–700364.** CMS proc cards: `p p > l+ l- j j / t t~ h QED=4 QCD=0`,
`p p > l- vl~ j j / t t~ h QCD=0`, `p p > l+ vl j j / t t~ h QCD=0` (ℓ = e, μ, τ). Run cards: m(ℓℓ) > 50 (Z) or m(ℓν) > 50
GeV (W), jet pT > 10 GeV, |η(j)| < 6.5, m(jj) > 10 GeV, no Δη(jj) cut, no lepton pT/η cut. ATLAS: Sherpa 2.2.11 LO
"2,3j", names "Min_N_TChannel"; the metadata gives no generator cuts (UNKNOWN). Sherpa manual §5.6.14: Min_N_TChannels
"limits the minimum number of t-channel propagators" → ATLAS removes the pure s-channel (diboson-like) diagrams that
the CMS `QED=4 QCD=0` samples keep. Per lepton flavour: CMS Z 2.07 pb vs ATLAS 0.779 pb (2.66 ×); CMS W⁺ + W⁻ 23.7 pb vs
ATLAS 8.50 pb (2.79 ×). Explained qualitatively by (1) the s-channel diagrams and (2) the looser CMS cuts; not quantified.
CMS's own measurements (narrower region m(jj) > 120, pT(j) > 25 GeV) agree with the LO prediction: 534 / 543 fb for Z
(SMP-16-018), 6.23 / 6.81 pb for W (SMP-17-011), and both papers state that NLO (VBFNLO) agrees with LO within 2–5 %.

**Z → νν HT bins.** `htjmin / htjmax` = 100/200, 200/400, 400/600, 600/800, 800/1200, 1200/2500, 2500/1d5 GeV (jet HT,
MLM, 0–4 partons, `xqcut 10`): exclusive and contiguous from 100 GeV; nothing below 100 GeV (as D11 says).

**40062 gg → ZH.** `Process=51 VH_PC=gg DecayMode1=9` (associated Z → anything) and decay card `DecayMode1=8 DecayMode2=9
FilterNLept=4 WriteFailedEvents=2` (H → Z(ℓℓ, ℓ = e, μ, τ) Z(anything), 4-lepton filter). Every genWeight is 1.0 in the
probe (no zero-weight failed events kept), so the filter efficiency cannot be measured from the NanoAOD.

## Cost per tier (ESTIMATES; method of PLAN.md §4; `stats_cost_v2.py` → `evidence/stats_cost_v2.json`, `evidence/stats_table_v2.md`)

N_eff and MC luminosity from the probes (every planned sample is now probed); σ_eff = the v2 PROPOSAL, or the
generator value as a placeholder where a decision is needed. CPU = events × CPU s/event of the most similar delivered
sample (25–26 Oct audit); EW V + 2 jets and Z → νν use the DY rate. Cluster files = 12.1 per input file + 172 per sample.
**File count measured 31 Oct: 92,041 before the probe, 93,638 after it** (`lfs quota -u berkom /storage`, VERIFIED BY RUNNING).

| tier | samples | files | events | CPU h | cluster files added | cumulative (from 93,638) | under 125,000? |
|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | 7 | 563 | 619,095,364 | 77 | 8,019 | 101,657 | yes |
| 2 | 6 | 142 | 68,091,910 | 28 | 2,752 | 104,409 | yes |
| 3 | 7 | 96 | 22,530,000 | 8 | 2,368 | 106,777 | yes |
| 4 | 4 | 77 | 12,030,977 | 25 | 1,621 | 108,398 | yes |
| 5 | 26 | 347 | 41,611,581 | 41 | 8,679 | 117,077 | yes |
| 6 | 7 | 107 | 22,752,609 | 2 | 2,501 | 119,578 | yes |
| all | 57 | 1,332 | 786,112,441 | 180 | 25,940 | 119,578 | yes |

Notes:
- Each production also needs a pinned clone (~170 files measured on 17 Oct; this probe's clone + outputs added 1,597).
  Even with one clone per tier, the total stays under 125,000 (~120,600).
- Headroom after all six tiers: ~5,400 files. Dropping tier 6 (D11 allows it) frees ~2,500 files.
- Statistics: W+jets is still the only group below the data luminosity (0.13 / 0.29 / 0.16 ×; D3).
  The lowest of the rest:
  - Z → νν HT 100–200: 1.6 × the data (σ placeholder);
  - EW V + 2 jets: 3.2–4.5 ×;
  - Z → νν HT 200–400: 5.7 ×.
- Queue: ≤ 1,000 queued subjobs per user. Every tier fits in one submission; tier 1 (563 files) is the largest.
  The 3 h wall time is kept for tier 4. No file is estimated above 2 h (largest: gg → ZH → WW 3,328 s; VBF H → μμ 3,312 s, one file).
- Full per-sample table: `evidence/stats_table_v2.md`.

## Open points

**For Maryna (unchanged, not reopened here):**
- **QCD multijet.** Deferred on our side. Her list holds a full Pythia8 dijet set (MAPPING.md).
- **tt̄Z → qq, tZq, tWZ (and tt̄ + low-mass ℓℓ).** ON HOLD until she confirms the ATLAS nominal samples.
- **Pythia + Herwig "double nominal".** Her list carries 86 ATLAS alternative-generator DSIDs, for example Powheg+Herwig7
  next to Powheg+Pythia8 (MAPPING.md table B). If both are summed as nominal on the ATLAS side, those processes are
  counted twice.

**For the cross-section review (Matan, one sample at a time, tier 1 first):**
1. **D14 card check (75567):** decide whether the qualitative card evidence counts as "verified" → 1.135 pb, or take
   the fallback 0.6831 pb. Or ask for the one-job LHE m(ℓℓ) measurement first.
2. **EW V + 2 jets (35999, 35987, 35993):**
   - the value: (a) generator LO, or (b) generator × measured/LO;
   - **the overlap with the tier-2 dibosons**: (i) accept it; (ii) remove the V → qq part with an LHE m(jj) window (new builder code); or (iii) measure its size first.
3. **Z → νν (7 bins):** (a) generator LO; (b) × 1.23 (RazorAnalyzer, SECONDARY); or (c) × 1.0685 (our DY NNLO ÷ LO DY).
4. **40062:** options (a) 2.33e-4, (b) 4.66e-5 and (c) 6.22e-5 pb; all are UNVERIFIED or ESTIMATE.
5. **No other new convention question.** The Higgs, single-top and four-top cards follow D5, D6, D7 and D13 directly.

## Where things are

- `DECISIONS.md`: the decisions, E1, and the final list.
- `XSEC_PROPOSALS_v2.md`: 61 cards (`xsec_proposals_v2.py` → `evidence/xsec_proposals_v2.json`).
- This file.
- Scripts:
  - `plan_samples_v2.py` (final list, `PROBE2`);
  - `fetch_cards_v2.py`;
  - `stats_cost_v2.py`;
  - `probe_sample.py` and `cluster/pbs_probe.sh`: new `--list v2` / `PROBE_LIST=v2` options; the default is unchanged;
  - `make_plots.py`: `genweight_plots` takes a probe directory; the default is unchanged.
- Evidence:
  - `evidence/probe_v2/`, `evidence/probe_v2_table.md`;
  - `evidence/cards/<recid>/` (21 new directories), `evidence/cards/index_v2.json`;
  - `evidence/stats_cost_v2.json`, `evidence/stats_table_v2.md`;
  - `plots/genweight_<recid>.png` (35 new).
