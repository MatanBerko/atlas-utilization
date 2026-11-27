# Nominal-6 additions: generator settings, cross-section options, one-file precheck (27 Nov 2026)

Preparation only, for Matan's hand check of the cross sections of the 14 samples added by his decision of 27 Nov
2026 ("Option A", `studies/cms_mc_weights_v3/sources/v8_decisions_2026-11-27.json`). **No cross section,
k-factor, filter efficiency or branching ratio is adopted here, no registry is changed, nothing is produced or
built.** Every number is labelled VERIFIED (read from a saved primary source / VERIFIED BY RUNNING) or
ESTIMATE / INTERPRETATION / UNVERIFIED. Every choice is listed for Matan.

## 1. Summary for Matan

1. Your decision is recorded word for word (`v8_decisions_2026-11-27.json`); the README text is `DOCUMENTED_EXCEPTIONS.md`.
2. **N3 overlaps our H→Zγ:** half of the CMS Dalitz μμ events (a third of ee) are H→Zγ with the Z on its peak,
   which our H→Zγ samples already contain. N3 cannot be added as is (section 2).
3. All 14 samples ran through our production code: 14/14 OK (section 5).
4. Cross-section options with sources for every sample (section 3):
   - N1: no matching theory value; CMS 0.156 pb vs ATLAS 0.319 pb (CMS requires m(jj) > 100 GeV, on-shell).
     69771 contains top diagrams (62 % of events), which overlap our tZq.
   - N2: CMS within 8 % of ATLAS.
   - N3: no published value for the samples' full mass range.
   - N4: the portal 0.79 pb is bare ZH production. McM's 0.151 is the 4-lepton filter efficiency; that option is
     ~2.8 × ATLAS. The same reading makes our delivered 40062 ~1.5 × too low (not changed; for you).
5. Cost (ESTIMATE): ~2,300 cluster files for the 14 and ~6,200 for a full rebuild. Count now 133,497, of which
   ~10,700 are my mistake (a card extraction made thousands of folders; removing them needs your OK). That gives
   ~142,000 as is and ~131,300 without them: above 125,000 either way, below 140,000 only without them.
6. Next: the technical lead checks on GitHub; you decide the N3 overlap and hand-check each cross section.

## 2. The N3 overlap answer (B2, blocking for N3)

**In plain words: the CMS Dalitz samples are not "Dalitz only". They contain the complete H → ℓℓγ decay, including
H → Zγ → ℓℓγ with the Z on its peak. Our five H→Zγ samples contain only the Z-peak region (m_ℓℓ > 50 GeV). So the two
overlap for m_ℓℓ above ~50 GeV, mostly at 80–100 GeV, in the ee and μμ channels. They do not overlap in Z → ττ
(Dalitz has no ττ) nor below 50 GeV (H→Zγ has nothing there).**

Evidence (all VERIFIED: read from the gridpack cards on /cvmfs, `evidence/gridpack_cards/`, and BY RUNNING on file 0,
`evidence/precheck/gen_check.json`):

| | CMS Dalitz (37276, 37420, 68459, 68559, 69681, 69699, 74652, 74670) | CMS H→Zγ in v5 (37604, 68731, 70301, 71145, 74292) |
|---|---|---|
| how the decay is made | MadSpin `decay x0 > l+ l- a` (full 3-body matrix element), HC_NLO_X0 model; MadSpin param card kHaa = 1, **kHza = 1**, cosa = 1, so the γ* and the **Z** amplitudes and their interference are inside | Pythia 8: `25:onIfMatch = 23 22` (H → Z γ, Breit–Wigner Z); ggF/VBF `23:mMin = 50`, Z → e/μ/τ; W±H/ZH Z → all (no mMin set) |
| m_ℓℓ cut | **none** (the run-card `mll_sf 30`, `ptgmin 20` act on the production step, which has no leptons/photons) | ggF/VBF: m_ℓℓ > 50 GeV; W±H/ZH: Pythia default |
| file 0, weighted fraction with m_ℓℓ < 30 / < 50 / > 50 GeV (80–100 GeV) | ee: 0.64 / 0.67 / **0.33** (0.30); μμ: 0.46 / 0.49 / **0.51** (0.46), the same in all four production modes | ≥ 0.997 above 50 GeV in all five, 0.93–0.96 in 80–100 GeV |
| lepton flavours | ee or μμ (one sample each) | ee, μμ, ττ |

The parent recorded for the leptons in the Dalitz files is a Z in 30–49 % of the events and the Higgs directly in
the rest (`lepton_pair_parent`).

**How ATLAS separates them (VERIFIED, public job options in `evidence/atlas_joboptions/`):**
- Dalitz 345961, 345834, 345963–345965: Pythia 8 H → γγ with one photon converted internally
  (`TimeShower:mMaxGamma 90`, `nGammaToLepton = 2` = e, μ only, `HllgamRepeatTimeShower`). The job options say
  "no interference between γ* and Z". So γ* only, m_ℓℓ up to 90 GeV, no Z amplitude.
- H→Zγ 345316 and 345833: Pythia 8 H → Zγ with `23:mMin = 2.0`, Z → ee/μμ/ττ. 345320–345322: Z → e/μ/τ, no mMin set.
- So ATLAS splits by **amplitude** (γ* in one sample, Z in the other, no interference) and not by m_ℓℓ. Both cover
  overlapping m_ℓℓ ranges, but they are different terms of the decay. CMS has the full amplitude in the Dalitz samples,
  so adding them to the CMS H→Zγ samples counts the Z part twice.

**Size (arithmetic, ESTIMATE).** Take the μμ ggF channel with YR4 values:
- H→Zγ→μμγ is 48.58 × 1.533e-3 × 0.03366 = 2.5 fb;
- CMS-HIG-17-007 gives H→γ*γ→μμγ ≈ 48.58 × 3.83e-5 = 1.9 fb, with m_μμ < 50 GeV as their dividing line.

The two parts are comparable, so the overlap is not small.

**Options (no choice made):**
1. **Cut the Dalitz samples at m_ℓℓ < 50 GeV on generator leptons.** This is CMS-HIG-17-007's dividing line. Keep
   our H→Zγ samples unchanged. It requires:
   - a generator-level m_ℓℓ veto, which does not exist in our code. Either the CMS production driver needs a new
     selection (a production-code change and a new pin), or the builder needs one (it has no generator information
     today);
   - a cross section for the Dalitz part that matches the cut. CMS-HIG-17-007 gives μμ 3.83e-5 × σ(H). No published
     ee value exists for m < 50 GeV (ATLAS gives ee and μμ only for m < 30 GeV).
2. **Cut at m_ℓℓ < 30 GeV.** The ATLAS measurement region (arXiv:2103.10322). Same requirements as 1. ATLAS's
   Pythia 8 values exist for both flavours (ee 7.20e-5, μμ 3.42e-5). This leaves 30–50 GeV uncovered: 2–4 % of the
   Dalitz sample, and none of H→Zγ.
3. **Use the Dalitz samples for the full range and drop the ee/μμ part of our H→Zγ.** It requires:
   - a full-range normalisation, which is not published;
   - splitting our H→Zγ by Z flavour at generator level, because those samples also hold Z → ττ (and Z → all for
     W±H/ZH), which Dalitz lacks;
   - a change to five delivered values.
4. **Do not add N3** (document it, as for N5–N15).

A note for any option: ATLAS's own Dalitz normalisations disagree with its own paper. The 2024r-pp filter for
VBF/W±H/ZH is 0.00227 = BR(H→γγ) (the conversion probability is missing), and for ggF it is 4.306e-4 (S5, 24 Nov).
CMS / ATLAS is 0.02–0.22 per sample, from that and from the m_ℓℓ coverage.

## 3. Cross sections per item

### 3.1 Generator settings (B1)

All fragments and request JSONs are in `evidence/mcm/` (public McM REST API, read 27 Nov 2026). The cards actually
used are in `evidence/gridpack_cards/`, extracted from the gridpacks named in the fragments on /cvmfs. Generator-level
facts are from file 0 (`evidence/precheck/gen_check.json`; GenPart part: up to 100,000 events).

**N1 – electroweak VV+2 jets (MadGraph5 2.6.5 LO, model `sm-ckm_no_b_mass`, 5 flavours, no merging; decays in the
matrix element as a decay chain, on-shell W/Z within bwcutoff 15–20 Γ; Pythia 8 with dipole recoil).**

| record | process (gridpack card) | generator cuts | file 0 |
|---|---|---|---|
| 75561 ZZJJTo4L_EWKnotop | `p p > z z j j $ t t~ QED=4 QCD=0, z > l+ l-, z > l+ l-` (ℓ = e μ τ) | m_jj > 100, pT_j > 10, \|η_j\| < 5, \|η_ℓ\| < 3, ΔR > 0.01 | no Higgs, no top seen |
| 69771 WLLJJ_WToLNu_EWK | `p p > w± z j j QED=4 QCD=0, z > l+ l-, w > l v` (**no top exclusion**) | as 75561, bwcutoff 20 | **a top quark in 62 % of the events** (tZq-like diagrams) |
| 72648 WWJJToLNuLNu_EWK_noTop | `p p > w+ w- j j $ t t~ QED=4 QCD=0, w+ > l+ vl, w- > l- vl~` | m_jj > 100, pT_j > 10, no η cuts, ΔR(jj, ℓℓ, jℓ) > 0.4 | a Higgs in 1.3 % (s-channel H→WW) |
| 71636 WpWpJJ_EWKnotop | `w+ w+ j j` **and** `w- w- j j`, `$ t t~`, QED=4 QCD=0 | as 75561 | W⁻W⁻ is inside (corrects 24 Nov) |

**Corrections to 24 Nov.**
- 71636 contains W⁻W⁻ as well.
- The genproductions master card for WZ is the `_notop` variant, but the gridpack actually used (`WZ3lnujj_ewk`)
  has no top exclusion.

**N2 – 71640 WpWpJJ_QCDnotop.** Same generator, `w± w± j j $ t t~ QED=2 QCD=99`, same cuts as 75561.

**N3 – Higgs Dalitz.**
- Production with MG5_aMC 2.6.5 at NLO:
  - ggF: HEFT `p p > x0 / t [QCD]` + 1j + 2j, FxFx (qCut 30, ptj 10);
  - VBF: NLO;
  - W±H and ZH: `p p > V h [QCD]` + 1j + 2j, FxFx.
- Decay in MadSpin as in section 2.
- The gridpack run cards equal the genproductions master cards (checked for 37420 and 69699).

**N4 – 74314 ZH_HToZZ_4LFilter.**
- Production: POWHEG HZJ MiNLO, `vdecaymode 10` (Z → all), `min_z_mass 10`.
- H decay: a separate JHUGen 7.0.11 step, `DecayMode1=8` (Z → 2ℓ, ℓ = e μ τ), `DecayMode2=9` (Z → anything),
  `FilterNLept=4` (≥ 4 leptons in the event, the associated Z included), `WriteFailedEvents=2`.
- Pythia 8 with the POWHEG emission veto.
- File 0 (6,988 events, all with ≥ 4 prompt charged leptons):
  - H → ZZ → ℓℓqq 48.9 %, ℓℓℓℓ 36.7 %, ℓℓνν 14.3 %;
  - the associated Z → ℓℓ in 66.8 %.
- **Reading of McM's 0.1509 (INTERPRETATION, supported by these numbers).**
  - JHUGen 8+9 gives H → ZZ with at least one Z → ℓℓ, a fraction 1 − (1 − B)² = 0.19178 of H → ZZ, with
    B = BR(Z→ℓℓ) = 0.10099.
  - The filter then keeps B² + 2B(1 − B)·B over 2B − B², which is 0.149. McM lists 0.1509.
  - The predicted decay mix after the filter, ℓℓℓℓ 0.357 / ℓℓqq 0.499 / ℓℓνν 0.143, matches file 0
    (0.367 / 0.489 / 0.143).


### 3.2 Rule R1 for these samples

R1 (`studies/cms_mc_weights_v3/DESIGN.md:363-369`): the portal `total_value` includes matching and filter
efficiencies, but not a decay done in a separate generator step.
- **N1, N2:** the decay is in the MadGraph matrix element, with no filter and no matching. The portal value is the
  sample's complete generator cross section.
- **N3:** the decay is done by MadSpin inside the gridpack, so it is **inside** the portal value. The ee and μμ
  samples of the same production differ by ×1.5, which only the decay can cause. The FxFx matching efficiency that
  the portal lists (0.3) is assumed inside, as everywhere (UNVERIFIED for these records).
- **N4:** the decay is a separate JHUGen step, so it is **not** inside. The 4-lepton filter is not inside either:
  0.7935 pb is the bare ZH production (YR4 qq→ZH 0.7612 pb; ZH total 0.8839 pb). The portal's "matching 0.2"
  (McM 0.1509) is the filter efficiency (section 3.1), not a jet-matching efficiency.

### 3.3 Item summaries

**N1 – EW VV+2 jets.** CMS sums to 0.1558 pb against ATLAS's 0.3187 pb (EW 0.2989 + interference 0.0197), a ratio
of 0.49. Per sample, CMS / ATLAS (EW + interference) is:
- ZZjj 0.072;
- WZjj 0.63;
- W⁺W⁻jj 0.46;
- W±W±jj 0.55.

Reasons (cards read on both sides):
1. CMS requires m_jj > 100 GeV at generator level; ATLAS has no m_jj cut (2 jets, pT > 15 GeV). This removes the
   V→jj triboson-like region and low-m_jj VBS.
2. CMS has on-shell W/Z (decay chains, |η_ℓ| < 3); ATLAS is off-shell 2→6, including γ* → ℓℓ down to m_ℓℓ > 0.25 GeV
   with pT_ℓ > 5 GeV. This is why ZZjj (four charged leptons) differs most: ATLAS lllljj is dominated by low-mass
   γ* pairs (INTERPRETATION, not measured).
3. ATLAS llvvjj_os (700589) holds every opposite-sign ℓℓνν final state, so it also includes ZZ → ℓℓνν. CMS 72648
   is W⁺W⁻ only.
4. τ: both sides include τ (CMS ℓ = e μ τ; ATLAS lepton container 90 includes τ).
5. Top removal: CMS 75561, 72648 and 71636 have `$ t t~`. 69771 does not (62 % of its events contain a top quark).
   ATLAS keeps b quarks out of the jet container (`MASSIVE[5]=1`, jets = 93).
6. ATLAS merges 0,1 jets at LO; CMS is fixed-order LO.

No published calculation or measurement covers the generator phase space (CMS measurements exist only in tighter
fiducial regions: arXiv:2008.07013, arXiv:2205.05711). The McM values differ from the portal for 75561 (×0.72) and
69771 (×0.46). This is unexplained, and McM's value is a user-entered field.

**N2 – QCD W±W±jj.** CMS portal 0.02037 pb against ATLAS 700603 0.02221 pb (Sherpa, no m_jj cut, pT_ℓ > 5 GeV), a
ratio of 0.92. McM lists 0.02227 pb. No theory value for this phase space was found.

**N3 – Dalitz.** Per mode, CMS (ee + μμ, portal) against ATLAS (σ×k×ε, one sample per mode for both flavours):

| mode | CMS ee | CMS μμ | CMS sum | ATLAS | CMS / ATLAS |
|---|---:|---:|---:|---:|---:|
| ggF | 2.816e-3 | 1.858e-3 | 4.674e-3 | 2.092e-2 (345961: 28.3 × 1.717 × 4.306e-4) | 0.22 |
| VBF | 3.150e-4 | 2.080e-4 | 5.230e-4 | 8.585e-3 (345834: 3.782 × 0.00227) | 0.061 |
| W±H | 1.238e-4 | 8.169e-5 | 2.055e-4 | 3.116e-3 (345963 + 345964) | 0.066 |
| ZH | 6.762e-5 | 4.459e-5 | 1.122e-4 | 1.728e-3 (345965: 0.7612 × 0.00227) | 0.065 |

The differences above 20 % come from the ATLAS filter values (S5): 0.00227 is BR(H → γγ), with no internal
conversion probability applied, and the ggF value differs again. The m_ℓℓ coverage also differs (section 2).

Theory values are published only with an m_ℓℓ cut:
- CMS-HIG-17-007: μμ 3.83e-5 (MCFM), with the 50 GeV dividing line;
- ATLAS arXiv:2103.10322: ee 7.20e-5 and μμ 3.42e-5 for m_ℓℓ < 30 GeV (a Pythia 8 estimate).

None matches the samples' full m_ℓℓ range. An observation (arithmetic only): 37420's portal value 1.858e-3 pb equals
YR4 ggF 48.58 pb × 3.83e-5 = 1.861e-3 pb to 0.2 %. Yet the sample has 51 % of its events above 50 GeV. So the portal
value looks like the m < 50 GeV rate applied to a full-range sample. The other Dalitz records do not show this
(implied B 5.5–6.0 × 10⁻⁵ for μμ).

**N4 – ZH, H→ZZ, 4-lepton filter.** The options are:
- A: YR4 × BR(H→4ℓ) = 2.089e-4 pb (ATLAS convention);
- B: the 40062 convention = 3.861e-4;
- C: YR4 × BR(ZZ) × 0.19178 × 0.1509 = 5.769e-4;
- C′: the filter from BRs = 5.689e-4;
- D: as C, with the portal production σ = 6.014e-4.

Under the reading in 3.1, A leaves out the events where the third and fourth leptons come from the associated Z
(63 % of the sample). B counts H → Z(ℓℓ)Z(X) once instead of twice, giving ×0.67 of C. **The same JHUGen decay card
(`ZZ2l2any_withtaus_filter4l.input`) is used by our delivered 40062 (gg→ZH)**, normalised with construction B
(v5, ESTIMATE). If the reading holds, 40062 is low by ×1.49. This is outside this task: nothing was changed, and it is
listed for Matan. 71227 and 70383 (W±H 4ℓ) use JHUGen `8 8` with no filter, so they are not affected.

### 3.4 Per-sample tables (B3; generated by `tools/xsec_options.py` → `evidence/xsec_options.json`)

Columns:
- (a) portal;
- (b) McM;
- (c) theory options;
- (d) registry v5 analogue;
- (e) ATLAS σ×k×ε and the CMS/ATLAS ratio.

#### N1 75561 — ZZJJTo4L_EWKnotop_TuneCP5_13TeV-madgraph-pythia8

| option | value [pb] | how | source / status |
|---|---:|---|---|
| (a) portal total_value (MiniAOD [75560](https://opendata.cern.ch/record/75560)) | 0.0009928 | filter 1, matching 1, neg. weights 0 | VERIFIED (saved record) |
| (b) McM generator value ([SUS-RunIISummer20UL16wmLHEGEN-00134](https://cms-pdmv-prod.web.cern.ch/mcm/public/restapi/requests/get/SUS-RunIISummer20UL16wmLHEGEN-00134)) | 0.0007165 | filter 1, match 1 | VERIFIED (saved request JSON); user-entered value |
| (c) none found for the generator phase space | — |  | CMS measured EW VBS in fiducial regions with reconstruction-like cuts (e.g. EW ZZjj 0.33 fb, SM 0.275 fb, arXiv:2008.07013 abstract; EW W+W-jj 10.2 fb, SM 9.1 fb, arXiv:2205.05711 abstract). These are NOT the generator phase space of the samples (m_jj > 100 GeV, |eta_l| < 3 at generator level), so they cannot be used directly; no NLO calculation for the generator phase space was found. |
| (e) ATLAS σ×k×ε (700587, 700591) | 0.01382 | 700587: 0.01151×1×1; 700591: 0.0023142×1×1 | VERIFIED (public metadata 2024r-pp); CMS portal / ATLAS = 0.07182 |

- **R1:** Decay inside the MadGraph matrix element (process card decay chain `v > l v`); no separate decay step, no filter (fragment filterEfficiency 1.0), no matching (ickkw 0): R1 applies, the portal total_value is the complete generator cross section of the sample.
- **(d) registry v5 analogue:** Dibosons (E1): generator x NNLO/NLO k-factor (WZ, ZZ) or NNLO total x BR (WW); tribosons 72701/72711 and ttZ/ttW: generator NLO value as is. No EW VV+2j precedent: E2 dropped the EW V+2j samples (35999/35987/35993) before any value was chosen.
- **Generator settings:** CMS card (gridpack): p p > z z j j $ t t~ QED=4 QCD=0, z > l+ l- (l = e mu tau), on-shell Z decay chain (bwcutoff 15); m_jj > 100, |eta_l| < 3, |eta_j| < 5, pT_j > 10 GeV. ATLAS Sherpa: off-shell 4 charged leptons + 2 jets, m_ll > 0.25/0.46/3.8 GeV (ee/mumu/tautau), pT_l > 5, 2 jets pT > 15, NO m_jj cut, 0,1j@LO merged; incl. gamma* and triboson-like diagrams. McM 7.1654e-4 pb differs from the portal 9.928e-4 pb (factor 1.39; unexplained).

#### N1 69771 — WLLJJ_WToLNu_EWK_TuneCP5_13TeV_madgraph-madspin-pythia8

| option | value [pb] | how | source / status |
|---|---:|---|---|
| (a) portal total_value (MiniAOD [69770](https://opendata.cern.ch/record/69770)) | 0.03566 | filter 1, matching 1, neg. weights 0 | VERIFIED (saved record) |
| (b) McM generator value ([SMP-RunIISummer20UL16wmLHEGEN-00539](https://cms-pdmv-prod.web.cern.ch/mcm/public/restapi/requests/get/SMP-RunIISummer20UL16wmLHEGEN-00539)) | 0.01654 | filter 1, match 1 | VERIFIED (saved request JSON); user-entered value |
| (c) none found for the generator phase space | — |  | CMS measured EW VBS in fiducial regions with reconstruction-like cuts (e.g. EW ZZjj 0.33 fb, SM 0.275 fb, arXiv:2008.07013 abstract; EW W+W-jj 10.2 fb, SM 9.1 fb, arXiv:2205.05711 abstract). These are NOT the generator phase space of the samples (m_jj > 100 GeV, |eta_l| < 3 at generator level), so they cannot be used directly; no NLO calculation for the generator phase space was found. |
| (e) ATLAS σ×k×ε (700588, 700592) | 0.0562 | 700588: 0.048453×1×1; 700592: 0.0077437×1×1 | VERIFIED (public metadata 2024r-pp); CMS portal / ATLAS = 0.6346 |

- **R1:** Decay inside the MadGraph matrix element (process card decay chain `v > l v`); no separate decay step, no filter (fragment filterEfficiency 1.0), no matching (ickkw 0): R1 applies, the portal total_value is the complete generator cross section of the sample.
- **(d) registry v5 analogue:** Dibosons (E1): generator x NNLO/NLO k-factor (WZ, ZZ) or NNLO total x BR (WW); tribosons 72701/72711 and ttZ/ttW: generator NLO value as is. No EW VV+2j precedent: E2 dropped the EW V+2j samples (35999/35987/35993) before any value was chosen.
- **Generator settings:** CMS card READ FROM THE GRIDPACK (evidence/gridpack_cards/69771/InputCards): p p > w+- z j j QED=4 QCD=0, z > l+ l-, w > l v, with NO '$ t t~' top exclusion (the genproductions master card is the _notop variant, NOT the one used); file 0: a top quark in 2,304 of 3,712 events (62 %), i.e. tZq-like diagrams are inside (overlap with our tZq 68325). m_jj > 100, |eta_l| < 3, bwcutoff 20. ATLAS lllvjj: off-shell, no m_jj cut, b quarks not in the jet container (MASSIVE[5]). McM 0.01654 pb is 0.46 x the portal 0.03566 pb (unexplained).

#### N1 72648 — WWJJToLNuLNu_EWK_noTop_TuneCP5_13TeV-madgraph-pythia8

| option | value [pb] | how | source / status |
|---|---:|---|---|
| (a) portal total_value (MiniAOD [72647](https://opendata.cern.ch/record/72647)) | 0.09219 | filter 1, matching 1, neg. weights 0 | VERIFIED (saved record) |
| (b) McM generator value ([HIG-RunIISummer20UL16wmLHEGEN-03478](https://cms-pdmv-prod.web.cern.ch/mcm/public/restapi/requests/get/HIG-RunIISummer20UL16wmLHEGEN-03478)) | 0.09283 | filter 1, match 1 | VERIFIED (saved request JSON); user-entered value |
| (c) none found for the generator phase space | — |  | CMS measured EW VBS in fiducial regions with reconstruction-like cuts (e.g. EW ZZjj 0.33 fb, SM 0.275 fb, arXiv:2008.07013 abstract; EW W+W-jj 10.2 fb, SM 9.1 fb, arXiv:2205.05711 abstract). These are NOT the generator phase space of the samples (m_jj > 100 GeV, |eta_l| < 3 at generator level), so they cannot be used directly; no NLO calculation for the generator phase space was found. |
| (e) ATLAS σ×k×ε (700589, 700593) | 0.1997 | 700589: 0.19336×1×1; 700593: 0.0063366×1×1 | VERIFIED (public metadata 2024r-pp); CMS portal / ATLAS = 0.4617 |

- **R1:** Decay inside the MadGraph matrix element (process card decay chain `v > l v`); no separate decay step, no filter (fragment filterEfficiency 1.0), no matching (ickkw 0): R1 applies, the portal total_value is the complete generator cross section of the sample.
- **(d) registry v5 analogue:** Dibosons (E1): generator x NNLO/NLO k-factor (WZ, ZZ) or NNLO total x BR (WW); tribosons 72701/72711 and ttZ/ttW: generator NLO value as is. No EW VV+2j precedent: E2 dropped the EW V+2j samples (35999/35987/35993) before any value was chosen.
- **Generator settings:** CMS card (gridpack = linked card): p p > w+ w- j j $ t t~ QED=4 QCD=0, w > l v; m_jj > 100, no eta cuts, dR(jj, ll, jl) > 0.4; file 0: a Higgs boson in 1,252 of 100,000 events (1.3 %, s-channel H->WW inside). ATLAS llvvjj_os: ALL opposite-sign l l nu nu (also ZZ -> ll nunu and non-resonant), no m_jj cut.

#### N1 71636 — WpWpJJ_EWKnotop_TuneCP5_13TeV-madgraph-pythia8

| option | value [pb] | how | source / status |
|---|---:|---|---|
| (a) portal total_value (MiniAOD [71635](https://opendata.cern.ch/record/71635)) | 0.02694 | filter 1, matching 1, neg. weights 0 | VERIFIED (saved record) |
| (b) McM generator value ([SUS-RunIISummer20UL16wmLHEGEN-00122](https://cms-pdmv-prod.web.cern.ch/mcm/public/restapi/requests/get/SUS-RunIISummer20UL16wmLHEGEN-00122)) | 0.0287 | filter 1, match 1 | VERIFIED (saved request JSON); user-entered value |
| (c) none found for the generator phase space | — |  | CMS measured EW VBS in fiducial regions with reconstruction-like cuts (e.g. EW ZZjj 0.33 fb, SM 0.275 fb, arXiv:2008.07013 abstract; EW W+W-jj 10.2 fb, SM 9.1 fb, arXiv:2205.05711 abstract). These are NOT the generator phase space of the samples (m_jj > 100 GeV, |eta_l| < 3 at generator level), so they cannot be used directly; no NLO calculation for the generator phase space was found. |
| (e) ATLAS σ×k×ε (700590, 700594) | 0.04894 | 700590: 0.045598×1×1; 700594: 0.0033375×1×1 | VERIFIED (public metadata 2024r-pp); CMS portal / ATLAS = 0.5505 |

- **R1:** Decay inside the MadGraph matrix element (process card decay chain `v > l v`); no separate decay step, no filter (fragment filterEfficiency 1.0), no matching (ickkw 0): R1 applies, the portal total_value is the complete generator cross section of the sample.
- **(d) registry v5 analogue:** Dibosons (E1): generator x NNLO/NLO k-factor (WZ, ZZ) or NNLO total x BR (WW); tribosons 72701/72711 and ttZ/ttW: generator NLO value as is. No EW VV+2j precedent: E2 dropped the EW V+2j samples (35999/35987/35993) before any value was chosen.
- **Generator settings:** CMS card (gridpack = genproductions card): BOTH w+w+jj AND w-w-jj (so W-W- is inside, correcting the 24 Nov 'no separate W-W-'), m_jj > 100, |eta_l| < 3. ATLAS llvvjj_ss: off-shell, pT_l > 5, no m_jj cut.

#### N2 71640 — WpWpJJ_QCDnotop_TuneCP5_13TeV-madgraph-pythia8

| option | value [pb] | how | source / status |
|---|---:|---|---|
| (a) portal total_value (MiniAOD [71639](https://opendata.cern.ch/record/71639)) | 0.02037 | filter 1, matching 1, neg. weights 0 | VERIFIED (saved record) |
| (b) McM generator value ([SUS-RunIISummer20UL16wmLHEGEN-00123](https://cms-pdmv-prod.web.cern.ch/mcm/public/restapi/requests/get/SUS-RunIISummer20UL16wmLHEGEN-00123)) | 0.02227 | filter 1, match 1 | VERIFIED (saved request JSON); user-entered value |
| (c) none found for the generator phase space | — |  | no published QCD same-sign WWjj total for these cuts |
| (e) ATLAS σ×k×ε (700603) | 0.02221 | 700603: 0.022206×1×1 | VERIFIED (public metadata 2024r-pp); CMS portal / ATLAS = 0.9173 |

- **R1:** Decay inside the MadGraph matrix element (process card decay chain `v > l v`); no separate decay step, no filter (fragment filterEfficiency 1.0), no matching (ickkw 0): R1 applies, the portal total_value is the complete generator cross section of the sample.
- **(d) registry v5 analogue:** Dibosons (E1): generator x NNLO/NLO k-factor (WZ, ZZ) or NNLO total x BR (WW); tribosons 72701/72711 and ttZ/ttW: generator NLO value as is. No EW VV+2j precedent: E2 dropped the EW V+2j samples (35999/35987/35993) before any value was chosen.
- **Generator settings:** CMS card: p p > w+w+ j j and w-w- j j, QED=2 QCD=99, $ t t~, m_jj > 100, |eta_l| < 3. ATLAS 700603: Sherpa 0,1j@LO Order(*,4), pT_l > 5, >= 2 jets pT > 15, no m_jj cut. McM 0.02227 pb vs portal 0.02037 pb.

#### N3 37276 — GluGluHToEEG_M125_Dalitz_012j_TuneCP5_13TeV_amcatnlo_pythia8

| option | value [pb] | how | source / status |
|---|---:|---|---|
| (a) portal total_value (MiniAOD [37275](https://opendata.cern.ch/record/37275)) | 0.002816 | filter 1, matching 0.3, neg. weights 0.2151 | VERIFIED (saved record) |
| (b) McM generator value ([HIG-RunIISummer20UL16wmLHEGEN-04069](https://cms-pdmv-prod.web.cern.ch/mcm/public/restapi/requests/get/HIG-RunIISummer20UL16wmLHEGEN-04069)) | 0.0008082 | filter 1, match 0.308 | VERIFIED (saved request JSON); user-entered value |
| (c) YR4 sigma x B(ATLAS Pythia8, m_ll < 30 GeV) | 0.003498 | 48.58 x 7.20e-5 | ATLAS arXiv:2103.10322 Sect. 3: B(H->eegamma) = 7.20e-5 estimated with Pythia 8 for m_ll < 30 GeV (an ATLAS MC estimate, not a theory calculation; agrees with Refs. [74,76] within 3 % 'when extrapolated to a common phase space') |
| (c) YR4 sigma x B(CMS MCFM) | — |  | CMS-HIG-17-007 gives no ee value (only mumu) |
| (c) Z-pole part, if the sample contains it (see REPORT section 2) | 0.002505 | 48.58 x 1.533e-3 x 0.033632 | YR4 BR(H->Zgamma) x PDG BR(Z->ll) per flavour: the H->Zgamma part with m_ll near m_Z |
| (c) no published value for the full m_ll range of the sample (no m_ll cut) | — |  |  |
| (c) implied B = portal / YR4 sigma (arithmetic only) | 5.797e-05 |  | the generator's own production sigma is not YR4, so this is not a measured BR |
| (e) ATLAS σ×k×ε (345961) | 0.02092 | 345961: 28.3×1.717×0.0004306 | VERIFIED (public metadata 2024r-pp); CMS portal / ATLAS = 0.1346 |

- **R1:** Decay H -> l+ l- gamma done by MadSpin inside the gridpack (madspin_card `decay x0 > l+ l- a`, spinmode none). The decay IS inside the portal value: ee and mumu samples of the same production differ (e.g. ggF 2.816e-3 vs 1.858e-3 pb), which only the decay can cause. Not a separate Pythia/JHUGen step, so R1's 'decay not inside' does NOT apply. Whether the listed matching efficiency (FxFx) is inside is the general R1 assumption (UNVERIFIED for these records).
- **(d) registry v5 analogue:** Every Higgs sample in v5 = YR4 production (mH = 125.00) x YR4 BR (x PDG Z BR), e.g. 37604 ggF H->Zgamma 48.58 x 0.001533 x 0.10099; VERIFIED BY MATAN 3 Nov. No YR4 BR exists for H -> l l gamma (Dalitz).
- **Generator settings:** CMS cards (genproductions master, directory 'dalitz_no_mll_cut'): production MG5_aMC NLO HEFT ggH 0,1,2j FxFx (ptj 10, qCut 30); decay in MadSpin x0 > l+ l- a with model HC_NLO_X0_UFO-lepton_masses_no_lepton_yukawas, MadSpin param card kHaa = kHza = 1, cosa = 1 (H-gamma-gamma AND H-Z-gamma couplings on: the Z pole is inside); no m_ll or photon cut in the decay (run_card mll_sf 30 / ptgmin 20 act on production-level particles; there are none). Cards read from the gridpack (evidence/gridpack_cards/). File 0: m_ll > 50 GeV in 0.334 (ee; 80-100 GeV: 0.308) of the weighted events. ATLAS: the full sigma_eff of the listed ATLAS DSID(s) is shared by ee and mumu (ATLAS has one sample for both).

#### N3 37420 — GluGluHToMuMuG_M125_Dalitz_012j_TuneCP5_13TeV_amcatnlo_pythia8

| option | value [pb] | how | source / status |
|---|---:|---|---|
| (a) portal total_value (MiniAOD [37419](https://opendata.cern.ch/record/37419)) | 0.001858 | filter 1, matching 0.3, neg. weights 0.2151 | VERIFIED (saved record) |
| (b) McM generator value ([HIG-RunIISummer20UL16wmLHEGEN-04063](https://cms-pdmv-prod.web.cern.ch/mcm/public/restapi/requests/get/HIG-RunIISummer20UL16wmLHEGEN-04063)) | 0.0008082 | filter 1, match 0.308 | VERIFIED (saved request JSON); user-entered value |
| (c) YR4 sigma x B(CMS MCFM, m_mumu < 50 GeV) | 0.001861 | 48.58 x 3.83e-5 | CMS-HIG-17-007, arXiv:1806.05996, Eq. (1) and text: B(H->gamma*gamma->mumugamma) = 3.83e-5 from MCFM 7.0.1; the paper separates H->gamma*gamma from H->Zgamma at m_ll = 50 GeV (the cut is stated in the text around Eq. (1), not next to the number: INTERPRETATION) |
| (c) YR4 sigma x B(ATLAS Pythia8, m_ll < 30 GeV) | 0.001661 | 48.58 x 3.42e-5 | ATLAS arXiv:2103.10322 Sect. 3: B(H->mumugamma) = 3.42e-5, Pythia 8, m_ll < 30 GeV |
| (c) Z-pole part, if the sample contains it (see REPORT section 2) | 0.002507 | 48.58 x 1.533e-3 x 0.033662 | YR4 BR(H->Zgamma) x PDG BR(Z->ll) per flavour: the H->Zgamma part with m_ll near m_Z |
| (c) no published value for the full m_ll range of the sample (no m_ll cut) | — |  |  |
| (c) implied B = portal / YR4 sigma (arithmetic only) | 3.825e-05 |  | the generator's own production sigma is not YR4, so this is not a measured BR |
| (e) ATLAS σ×k×ε (345961) | 0.02092 | 345961: 28.3×1.717×0.0004306 | VERIFIED (public metadata 2024r-pp); CMS portal / ATLAS = 0.0888 |

- **R1:** Decay H -> l+ l- gamma done by MadSpin inside the gridpack (madspin_card `decay x0 > l+ l- a`, spinmode none). The decay IS inside the portal value: ee and mumu samples of the same production differ (e.g. ggF 2.816e-3 vs 1.858e-3 pb), which only the decay can cause. Not a separate Pythia/JHUGen step, so R1's 'decay not inside' does NOT apply. Whether the listed matching efficiency (FxFx) is inside is the general R1 assumption (UNVERIFIED for these records).
- **(d) registry v5 analogue:** Every Higgs sample in v5 = YR4 production (mH = 125.00) x YR4 BR (x PDG Z BR), e.g. 37604 ggF H->Zgamma 48.58 x 0.001533 x 0.10099; VERIFIED BY MATAN 3 Nov. No YR4 BR exists for H -> l l gamma (Dalitz).
- **Generator settings:** CMS cards (genproductions master, directory 'dalitz_no_mll_cut'): production MG5_aMC NLO HEFT ggH 0,1,2j FxFx (ptj 10, qCut 30); decay in MadSpin x0 > l+ l- a with model HC_NLO_X0_UFO-lepton_masses_no_lepton_yukawas, MadSpin param card kHaa = kHza = 1, cosa = 1 (H-gamma-gamma AND H-Z-gamma couplings on: the Z pole is inside); no m_ll or photon cut in the decay (run_card mll_sf 30 / ptgmin 20 act on production-level particles; there are none). Cards read from the gridpack (evidence/gridpack_cards/). File 0: m_ll > 50 GeV in 0.507 (mumu; 80-100 GeV: 0.468) of the weighted events. ATLAS: the full sigma_eff of the listed ATLAS DSID(s) is shared by ee and mumu (ATLAS has one sample for both).

#### N3 68459 — VBFHToEEG_M125_Dalitz_TuneCP5_13TeV-amcatnlo-pythia8

| option | value [pb] | how | source / status |
|---|---:|---|---|
| (a) portal total_value (MiniAOD [68458](https://opendata.cern.ch/record/68458)) | 0.000315 | filter 1, matching 1, neg. weights 0.3429 | VERIFIED (saved record) |
| (b) McM generator value ([HIG-RunIISummer20UL16wmLHEGEN-04047](https://cms-pdmv-prod.web.cern.ch/mcm/public/restapi/requests/get/HIG-RunIISummer20UL16wmLHEGEN-04047)) | 1 | filter 1, match 1 | VERIFIED (saved request JSON); 1 = placeholder, not a cross section |
| (c) YR4 sigma x B(ATLAS Pythia8, m_ll < 30 GeV) | 0.0002723 | 3.782 x 7.20e-5 | ATLAS arXiv:2103.10322 Sect. 3: B(H->eegamma) = 7.20e-5 estimated with Pythia 8 for m_ll < 30 GeV (an ATLAS MC estimate, not a theory calculation; agrees with Refs. [74,76] within 3 % 'when extrapolated to a common phase space') |
| (c) YR4 sigma x B(CMS MCFM) | — |  | CMS-HIG-17-007 gives no ee value (only mumu) |
| (c) Z-pole part, if the sample contains it (see REPORT section 2) | 0.000195 | 3.782 x 1.533e-3 x 0.033632 | YR4 BR(H->Zgamma) x PDG BR(Z->ll) per flavour: the H->Zgamma part with m_ll near m_Z |
| (c) no published value for the full m_ll range of the sample (no m_ll cut) | — |  |  |
| (c) implied B = portal / YR4 sigma (arithmetic only) | 8.329e-05 |  | the generator's own production sigma is not YR4, so this is not a measured BR |
| (e) ATLAS σ×k×ε (345834) | 0.008585 | 345834: 3.782×1×0.00227 | VERIFIED (public metadata 2024r-pp); CMS portal / ATLAS = 0.03669 |

- **R1:** Decay H -> l+ l- gamma done by MadSpin inside the gridpack (madspin_card `decay x0 > l+ l- a`, spinmode none). The decay IS inside the portal value: ee and mumu samples of the same production differ (e.g. ggF 2.816e-3 vs 1.858e-3 pb), which only the decay can cause. Not a separate Pythia/JHUGen step, so R1's 'decay not inside' does NOT apply. Whether the listed matching efficiency (FxFx) is inside is the general R1 assumption (UNVERIFIED for these records).
- **(d) registry v5 analogue:** Every Higgs sample in v5 = YR4 production (mH = 125.00) x YR4 BR (x PDG Z BR), e.g. 37604 ggF H->Zgamma 48.58 x 0.001533 x 0.10099; VERIFIED BY MATAN 3 Nov. No YR4 BR exists for H -> l l gamma (Dalitz).
- **Generator settings:** CMS cards (genproductions master, directory 'dalitz_no_mll_cut'): production MG5_aMC NLO VBF NLO; decay in MadSpin x0 > l+ l- a with model HC_NLO_X0_UFO-lepton_masses_no_lepton_yukawas, MadSpin param card kHaa = kHza = 1, cosa = 1 (H-gamma-gamma AND H-Z-gamma couplings on: the Z pole is inside); no m_ll or photon cut in the decay (run_card mll_sf 30 / ptgmin 20 act on production-level particles; there are none). Cards read from the gridpack (evidence/gridpack_cards/). File 0: m_ll > 50 GeV in 0.325 (ee; 80-100 GeV: 0.296) of the weighted events. ATLAS: the full sigma_eff of the listed ATLAS DSID(s) is shared by ee and mumu (ATLAS has one sample for both).

#### N3 68559 — VBFHToMuMuG_M125_Dalitz_TuneCP5_13TeV-amcatnlo-pythia8

| option | value [pb] | how | source / status |
|---|---:|---|---|
| (a) portal total_value (MiniAOD [68558](https://opendata.cern.ch/record/68558)) | 0.000208 | filter 1, matching 1, neg. weights 0.3435 | VERIFIED (saved record) |
| (b) McM generator value ([HIG-RunIISummer20UL16wmLHEGEN-04044](https://cms-pdmv-prod.web.cern.ch/mcm/public/restapi/requests/get/HIG-RunIISummer20UL16wmLHEGEN-04044)) | 1 | filter 1, match 1 | VERIFIED (saved request JSON); 1 = placeholder, not a cross section |
| (c) YR4 sigma x B(CMS MCFM, m_mumu < 50 GeV) | 0.0001449 | 3.782 x 3.83e-5 | CMS-HIG-17-007, arXiv:1806.05996, Eq. (1) and text: B(H->gamma*gamma->mumugamma) = 3.83e-5 from MCFM 7.0.1; the paper separates H->gamma*gamma from H->Zgamma at m_ll = 50 GeV (the cut is stated in the text around Eq. (1), not next to the number: INTERPRETATION) |
| (c) YR4 sigma x B(ATLAS Pythia8, m_ll < 30 GeV) | 0.0001293 | 3.782 x 3.42e-5 | ATLAS arXiv:2103.10322 Sect. 3: B(H->mumugamma) = 3.42e-5, Pythia 8, m_ll < 30 GeV |
| (c) Z-pole part, if the sample contains it (see REPORT section 2) | 0.0001952 | 3.782 x 1.533e-3 x 0.033662 | YR4 BR(H->Zgamma) x PDG BR(Z->ll) per flavour: the H->Zgamma part with m_ll near m_Z |
| (c) no published value for the full m_ll range of the sample (no m_ll cut) | — |  |  |
| (c) implied B = portal / YR4 sigma (arithmetic only) | 5.5e-05 |  | the generator's own production sigma is not YR4, so this is not a measured BR |
| (e) ATLAS σ×k×ε (345834) | 0.008585 | 345834: 3.782×1×0.00227 | VERIFIED (public metadata 2024r-pp); CMS portal / ATLAS = 0.02423 |

- **R1:** Decay H -> l+ l- gamma done by MadSpin inside the gridpack (madspin_card `decay x0 > l+ l- a`, spinmode none). The decay IS inside the portal value: ee and mumu samples of the same production differ (e.g. ggF 2.816e-3 vs 1.858e-3 pb), which only the decay can cause. Not a separate Pythia/JHUGen step, so R1's 'decay not inside' does NOT apply. Whether the listed matching efficiency (FxFx) is inside is the general R1 assumption (UNVERIFIED for these records).
- **(d) registry v5 analogue:** Every Higgs sample in v5 = YR4 production (mH = 125.00) x YR4 BR (x PDG Z BR), e.g. 37604 ggF H->Zgamma 48.58 x 0.001533 x 0.10099; VERIFIED BY MATAN 3 Nov. No YR4 BR exists for H -> l l gamma (Dalitz).
- **Generator settings:** CMS cards (genproductions master, directory 'dalitz_no_mll_cut'): production MG5_aMC NLO VBF NLO; decay in MadSpin x0 > l+ l- a with model HC_NLO_X0_UFO-lepton_masses_no_lepton_yukawas, MadSpin param card kHaa = kHza = 1, cosa = 1 (H-gamma-gamma AND H-Z-gamma couplings on: the Z pole is inside); no m_ll or photon cut in the decay (run_card mll_sf 30 / ptgmin 20 act on production-level particles; there are none). Cards read from the gridpack (evidence/gridpack_cards/). File 0: m_ll > 50 GeV in 0.503 (mumu; 80-100 GeV: 0.462) of the weighted events. ATLAS: the full sigma_eff of the listed ATLAS DSID(s) is shared by ee and mumu (ATLAS has one sample for both).

#### N3 69681 — WHToEEG_M125_Dalitz_012j_TuneCP5_13TeV_amcatnloFXFX_pythia8

| option | value [pb] | how | source / status |
|---|---:|---|---|
| (a) portal total_value (MiniAOD [69680](https://opendata.cern.ch/record/69680)) | 0.0001238 | filter 1, matching 0.3, neg. weights 0.1937 | VERIFIED (saved record) |
| (b) McM generator value ([HIG-RunIISummer20UL16wmLHEGEN-03857](https://cms-pdmv-prod.web.cern.ch/mcm/public/restapi/requests/get/HIG-RunIISummer20UL16wmLHEGEN-03857)) | 1 | filter 1, match 0.318 | VERIFIED (saved request JSON); 1 = placeholder, not a cross section |
| (c) YR4 sigma x B(ATLAS Pythia8, m_ll < 30 GeV) | 9.884e-05 | 1.373 x 7.20e-5 | ATLAS arXiv:2103.10322 Sect. 3: B(H->eegamma) = 7.20e-5 estimated with Pythia 8 for m_ll < 30 GeV (an ATLAS MC estimate, not a theory calculation; agrees with Refs. [74,76] within 3 % 'when extrapolated to a common phase space') |
| (c) YR4 sigma x B(CMS MCFM) | — |  | CMS-HIG-17-007 gives no ee value (only mumu) |
| (c) Z-pole part, if the sample contains it (see REPORT section 2) | 7.078e-05 | 1.373 x 1.533e-3 x 0.033632 | YR4 BR(H->Zgamma) x PDG BR(Z->ll) per flavour: the H->Zgamma part with m_ll near m_Z |
| (c) no published value for the full m_ll range of the sample (no m_ll cut) | — |  |  |
| (c) implied B = portal / YR4 sigma (arithmetic only) | 9.018e-05 |  | the generator's own production sigma is not YR4, so this is not a measured BR |
| (e) ATLAS σ×k×ε (345963, 345964) | 0.003116 | 345963: 0.5328×1×0.00227; 345964: 0.84×1×0.00227 | VERIFIED (public metadata 2024r-pp); CMS portal / ATLAS = 0.03973 |

- **R1:** Decay H -> l+ l- gamma done by MadSpin inside the gridpack (madspin_card `decay x0 > l+ l- a`, spinmode none). The decay IS inside the portal value: ee and mumu samples of the same production differ (e.g. ggF 2.816e-3 vs 1.858e-3 pb), which only the decay can cause. Not a separate Pythia/JHUGen step, so R1's 'decay not inside' does NOT apply. Whether the listed matching efficiency (FxFx) is inside is the general R1 assumption (UNVERIFIED for these records).
- **(d) registry v5 analogue:** Every Higgs sample in v5 = YR4 production (mH = 125.00) x YR4 BR (x PDG Z BR), e.g. 37604 ggF H->Zgamma 48.58 x 0.001533 x 0.10099; VERIFIED BY MATAN 3 Nov. No YR4 BR exists for H -> l l gamma (Dalitz).
- **Generator settings:** CMS cards (genproductions master, directory 'dalitz_no_mll_cut'): production MG5_aMC NLO WH 0,1,2j NLO FxFx; decay in MadSpin x0 > l+ l- a with model HC_NLO_X0_UFO-lepton_masses_no_lepton_yukawas, MadSpin param card kHaa = kHza = 1, cosa = 1 (H-gamma-gamma AND H-Z-gamma couplings on: the Z pole is inside); no m_ll or photon cut in the decay (run_card mll_sf 30 / ptgmin 20 act on production-level particles; there are none). Cards read from the gridpack (evidence/gridpack_cards/). File 0: m_ll > 50 GeV in 0.338 (ee; 80-100 GeV: 0.309) of the weighted events. ATLAS: the full sigma_eff of the listed ATLAS DSID(s) is shared by ee and mumu (ATLAS has one sample for both).

#### N3 69699 — WHToMuMuG_M125_Dalitz_012j_TuneCP5_13TeV_amcatnloFXFX_pythia8

| option | value [pb] | how | source / status |
|---|---:|---|---|
| (a) portal total_value (MiniAOD [69698](https://opendata.cern.ch/record/69698)) | 8.169e-05 | filter 1, matching 0.3, neg. weights 0.1933 | VERIFIED (saved record) |
| (b) McM generator value ([HIG-RunIISummer20UL16wmLHEGEN-03848](https://cms-pdmv-prod.web.cern.ch/mcm/public/restapi/requests/get/HIG-RunIISummer20UL16wmLHEGEN-03848)) | 1 | filter 1, match 0.318 | VERIFIED (saved request JSON); 1 = placeholder, not a cross section |
| (c) YR4 sigma x B(CMS MCFM, m_mumu < 50 GeV) | 5.258e-05 | 1.373 x 3.83e-5 | CMS-HIG-17-007, arXiv:1806.05996, Eq. (1) and text: B(H->gamma*gamma->mumugamma) = 3.83e-5 from MCFM 7.0.1; the paper separates H->gamma*gamma from H->Zgamma at m_ll = 50 GeV (the cut is stated in the text around Eq. (1), not next to the number: INTERPRETATION) |
| (c) YR4 sigma x B(ATLAS Pythia8, m_ll < 30 GeV) | 4.695e-05 | 1.373 x 3.42e-5 | ATLAS arXiv:2103.10322 Sect. 3: B(H->mumugamma) = 3.42e-5, Pythia 8, m_ll < 30 GeV |
| (c) Z-pole part, if the sample contains it (see REPORT section 2) | 7.084e-05 | 1.373 x 1.533e-3 x 0.033662 | YR4 BR(H->Zgamma) x PDG BR(Z->ll) per flavour: the H->Zgamma part with m_ll near m_Z |
| (c) no published value for the full m_ll range of the sample (no m_ll cut) | — |  |  |
| (c) implied B = portal / YR4 sigma (arithmetic only) | 5.951e-05 |  | the generator's own production sigma is not YR4, so this is not a measured BR |
| (e) ATLAS σ×k×ε (345963, 345964) | 0.003116 | 345963: 0.5328×1×0.00227; 345964: 0.84×1×0.00227 | VERIFIED (public metadata 2024r-pp); CMS portal / ATLAS = 0.02621 |

- **R1:** Decay H -> l+ l- gamma done by MadSpin inside the gridpack (madspin_card `decay x0 > l+ l- a`, spinmode none). The decay IS inside the portal value: ee and mumu samples of the same production differ (e.g. ggF 2.816e-3 vs 1.858e-3 pb), which only the decay can cause. Not a separate Pythia/JHUGen step, so R1's 'decay not inside' does NOT apply. Whether the listed matching efficiency (FxFx) is inside is the general R1 assumption (UNVERIFIED for these records).
- **(d) registry v5 analogue:** Every Higgs sample in v5 = YR4 production (mH = 125.00) x YR4 BR (x PDG Z BR), e.g. 37604 ggF H->Zgamma 48.58 x 0.001533 x 0.10099; VERIFIED BY MATAN 3 Nov. No YR4 BR exists for H -> l l gamma (Dalitz).
- **Generator settings:** CMS cards (genproductions master, directory 'dalitz_no_mll_cut'): production MG5_aMC NLO WH 0,1,2j NLO FxFx; decay in MadSpin x0 > l+ l- a with model HC_NLO_X0_UFO-lepton_masses_no_lepton_yukawas, MadSpin param card kHaa = kHza = 1, cosa = 1 (H-gamma-gamma AND H-Z-gamma couplings on: the Z pole is inside); no m_ll or photon cut in the decay (run_card mll_sf 30 / ptgmin 20 act on production-level particles; there are none). Cards read from the gridpack (evidence/gridpack_cards/). File 0: m_ll > 50 GeV in 0.504 (mumu; 80-100 GeV: 0.463) of the weighted events. ATLAS: the full sigma_eff of the listed ATLAS DSID(s) is shared by ee and mumu (ATLAS has one sample for both).

#### N3 74652 — ZHToEEG_M125_Dalitz_012j_TuneCP5_13TeV_amcatnloFXFX_pythia8

| option | value [pb] | how | source / status |
|---|---:|---|---|
| (a) portal total_value (MiniAOD [74651](https://opendata.cern.ch/record/74651)) | 6.762e-05 | filter 1, matching 0.3, neg. weights 0.1988 | VERIFIED (saved record) |
| (b) McM generator value ([HIG-RunIISummer20UL16wmLHEGEN-03856](https://cms-pdmv-prod.web.cern.ch/mcm/public/restapi/requests/get/HIG-RunIISummer20UL16wmLHEGEN-03856)) | 1 | filter 1, match 0.4 | VERIFIED (saved request JSON); 1 = placeholder, not a cross section |
| (c) YR4 sigma x B(ATLAS Pythia8, m_ll < 30 GeV) | 5.481e-05 | 0.7612 x 7.20e-5 | ATLAS arXiv:2103.10322 Sect. 3: B(H->eegamma) = 7.20e-5 estimated with Pythia 8 for m_ll < 30 GeV (an ATLAS MC estimate, not a theory calculation; agrees with Refs. [74,76] within 3 % 'when extrapolated to a common phase space') |
| (c) YR4 sigma x B(CMS MCFM) | — |  | CMS-HIG-17-007 gives no ee value (only mumu) |
| (c) Z-pole part, if the sample contains it (see REPORT section 2) | 3.925e-05 | 0.7612 x 1.533e-3 x 0.033632 | YR4 BR(H->Zgamma) x PDG BR(Z->ll) per flavour: the H->Zgamma part with m_ll near m_Z |
| (c) no published value for the full m_ll range of the sample (no m_ll cut) | — |  |  |
| (c) implied B = portal / YR4 sigma (arithmetic only) | 8.883e-05 |  | the generator's own production sigma is not YR4, so this is not a measured BR |
| (e) ATLAS σ×k×ε (345965) | 0.001728 | 345965: 0.7612×1×0.00227 | VERIFIED (public metadata 2024r-pp); CMS portal / ATLAS = 0.03913 |

- **R1:** Decay H -> l+ l- gamma done by MadSpin inside the gridpack (madspin_card `decay x0 > l+ l- a`, spinmode none). The decay IS inside the portal value: ee and mumu samples of the same production differ (e.g. ggF 2.816e-3 vs 1.858e-3 pb), which only the decay can cause. Not a separate Pythia/JHUGen step, so R1's 'decay not inside' does NOT apply. Whether the listed matching efficiency (FxFx) is inside is the general R1 assumption (UNVERIFIED for these records).
- **(d) registry v5 analogue:** Every Higgs sample in v5 = YR4 production (mH = 125.00) x YR4 BR (x PDG Z BR), e.g. 37604 ggF H->Zgamma 48.58 x 0.001533 x 0.10099; VERIFIED BY MATAN 3 Nov. No YR4 BR exists for H -> l l gamma (Dalitz).
- **Generator settings:** CMS cards (genproductions master, directory 'dalitz_no_mll_cut'): production MG5_aMC NLO ZH 0,1,2j NLO FxFx; decay in MadSpin x0 > l+ l- a with model HC_NLO_X0_UFO-lepton_masses_no_lepton_yukawas, MadSpin param card kHaa = kHza = 1, cosa = 1 (H-gamma-gamma AND H-Z-gamma couplings on: the Z pole is inside); no m_ll or photon cut in the decay (run_card mll_sf 30 / ptgmin 20 act on production-level particles; there are none). Cards read from the gridpack (evidence/gridpack_cards/). File 0: m_ll > 50 GeV in 0.332 (ee; 80-100 GeV: 0.305) of the weighted events. ATLAS: the full sigma_eff of the listed ATLAS DSID(s) is shared by ee and mumu (ATLAS has one sample for both).

#### N3 74670 — ZHToMuMuG_M125_Dalitz_012j_TuneCP5_13TeV_amcatnloFXFX_pythia8

| option | value [pb] | how | source / status |
|---|---:|---|---|
| (a) portal total_value (MiniAOD [74669](https://opendata.cern.ch/record/74669)) | 4.459e-05 | filter 1, matching 0.3, neg. weights 0.1992 | VERIFIED (saved record) |
| (b) McM generator value ([HIG-RunIISummer20UL16wmLHEGEN-03850](https://cms-pdmv-prod.web.cern.ch/mcm/public/restapi/requests/get/HIG-RunIISummer20UL16wmLHEGEN-03850)) | 1 | filter 1, match 0.4 | VERIFIED (saved request JSON); 1 = placeholder, not a cross section |
| (c) YR4 sigma x B(CMS MCFM, m_mumu < 50 GeV) | 2.915e-05 | 0.7612 x 3.83e-5 | CMS-HIG-17-007, arXiv:1806.05996, Eq. (1) and text: B(H->gamma*gamma->mumugamma) = 3.83e-5 from MCFM 7.0.1; the paper separates H->gamma*gamma from H->Zgamma at m_ll = 50 GeV (the cut is stated in the text around Eq. (1), not next to the number: INTERPRETATION) |
| (c) YR4 sigma x B(ATLAS Pythia8, m_ll < 30 GeV) | 2.603e-05 | 0.7612 x 3.42e-5 | ATLAS arXiv:2103.10322 Sect. 3: B(H->mumugamma) = 3.42e-5, Pythia 8, m_ll < 30 GeV |
| (c) Z-pole part, if the sample contains it (see REPORT section 2) | 3.928e-05 | 0.7612 x 1.533e-3 x 0.033662 | YR4 BR(H->Zgamma) x PDG BR(Z->ll) per flavour: the H->Zgamma part with m_ll near m_Z |
| (c) no published value for the full m_ll range of the sample (no m_ll cut) | — |  |  |
| (c) implied B = portal / YR4 sigma (arithmetic only) | 5.858e-05 |  | the generator's own production sigma is not YR4, so this is not a measured BR |
| (e) ATLAS σ×k×ε (345965) | 0.001728 | 345965: 0.7612×1×0.00227 | VERIFIED (public metadata 2024r-pp); CMS portal / ATLAS = 0.02581 |

- **R1:** Decay H -> l+ l- gamma done by MadSpin inside the gridpack (madspin_card `decay x0 > l+ l- a`, spinmode none). The decay IS inside the portal value: ee and mumu samples of the same production differ (e.g. ggF 2.816e-3 vs 1.858e-3 pb), which only the decay can cause. Not a separate Pythia/JHUGen step, so R1's 'decay not inside' does NOT apply. Whether the listed matching efficiency (FxFx) is inside is the general R1 assumption (UNVERIFIED for these records).
- **(d) registry v5 analogue:** Every Higgs sample in v5 = YR4 production (mH = 125.00) x YR4 BR (x PDG Z BR), e.g. 37604 ggF H->Zgamma 48.58 x 0.001533 x 0.10099; VERIFIED BY MATAN 3 Nov. No YR4 BR exists for H -> l l gamma (Dalitz).
- **Generator settings:** CMS cards (genproductions master, directory 'dalitz_no_mll_cut'): production MG5_aMC NLO ZH 0,1,2j NLO FxFx; decay in MadSpin x0 > l+ l- a with model HC_NLO_X0_UFO-lepton_masses_no_lepton_yukawas, MadSpin param card kHaa = kHza = 1, cosa = 1 (H-gamma-gamma AND H-Z-gamma couplings on: the Z pole is inside); no m_ll or photon cut in the decay (run_card mll_sf 30 / ptgmin 20 act on production-level particles; there are none). Cards read from the gridpack (evidence/gridpack_cards/). File 0: m_ll > 50 GeV in 0.508 (mumu; 80-100 GeV: 0.467) of the weighted events. ATLAS: the full sigma_eff of the listed ATLAS DSID(s) is shared by ee and mumu (ATLAS has one sample for both).

#### N4 74314 — ZH_HToZZ_4LFilter_M125_TuneCP5_13TeV_powheg2-minlo-HZJ_JHUGenV7011_pythia8

| option | value [pb] | how | source / status |
|---|---:|---|---|
| (a) portal total_value (MiniAOD [74313](https://opendata.cern.ch/record/74313)) | 0.7935 | filter 1, matching 0.2, neg. weights 0.02914 | VERIFIED (saved record) |
| (b) McM generator value ([HIG-RunIISummer20UL16wmLHEGEN-00239](https://cms-pdmv-prod.web.cern.ch/mcm/public/restapi/requests/get/HIG-RunIISummer20UL16wmLHEGEN-00239)) | 1 | filter 1, match 0.1509 | VERIFIED (saved request JSON); 1 = placeholder, not a cross section |
| (c) A: YR4 qq->ZH x BR(H->4l, l=e,mu,tau) | 0.0002089 | 0.7612 x 2.745e-4 | the convention of v5 71227/70383 (WH H->ZZ->4l) and of ATLAS 346645; counts only events with 4 leptons from the Higgs, so it misses the filtered events where the 4th/3rd lepton comes from the associated Z |
| (c) B: v5 40062 convention (estimate) | 0.0003861 | 0.7612 x 0.02619 x 0.10099 x 0.19178 | eps = 1-(1-BR(Z->ll))^2: P(at least one of the other H-Z and the associated Z -> ll), as 40062; ESTIMATE. Under the reading of option C this construction counts the H->Z(ll)Z(ll) events twice too few and differs from C by x0.67 |
| (c) C: YR4 qq->ZH x BR(H->ZZ) x [1-(1-BR(Z->ll))^2] x McM filter efficiency 0.1509 | 0.0005769 | 0.7612 x 0.02619 x 0.19178 x 0.15088 | reading supported by the file-0 decay content (REPORT section 3, N4): JHUGen DecayMode 8+9 gives H->ZZ with AT LEAST one Z->ll (e,mu,tau), fraction 1-(1-B)^2 = 2B-B^2; the FilterNLept=4 filter then keeps (B^2 + 2B(1-B) B)/(2B-B^2) = 0.149 of them, matching McM 0.1509; the predicted decay mix after the filter (llll 0.357 / llqq 0.499 / llnunu 0.143) matches file 0 (0.367 / 0.489 / 0.143). INTERPRETATION, not documented by CMS |
| (c) C': as C with the filter efficiency computed from BRs, 0.1491 | 0.0005689 | 0.7612 x 0.02619 x [B^2 + 2B(1-B)B], B = 0.10099 | same reading; ESTIMATE (ignores tau-decay and lepton-counting details) |
| (c) D: portal 0.7935 x BR(H->ZZ) x [1-(1-B)^2] x 0.1509 | 0.0006014 | 0.7935 x 0.02619 x 0.19178 x 0.15088 | generator production sigma instead of YR4 |
| (c) E: measure the filter content in file 0 (precheck, generator particles) | — |  | REPORT section 5: fraction of events by H->ZZ and associated-Z decay |
| (e) ATLAS σ×k×ε (346645) | 0.0002089 | 346645: 0.7612×1×0.0002745 | VERIFIED (public metadata 2024r-pp); CMS portal / ATLAS = 3798 |

- **R1:** Production POWHEG HZJ MiNLO (Z -> all, vdecaymode 10, min_z_mass 10 GeV); H decay in a SEPARATE JHUGen step (DecayMode1=8 Z->2l incl. tau, DecayMode2=9 Z->anything, FilterNLept=4, WriteFailedEvents=2). R1: the decay BR is NOT inside the portal value; the portal value 0.7935 pb is close to the ZH production sigma (YR4 qq->ZH 0.7612, ZH total 0.8839), so the 4-lepton filter efficiency is NOT inside it either (if it were, the production sigma would be ~4-5 pb). The portal 'matching_efficiency' 0.2 (McM match_efficiency 0.1509, the validation efficiency) is therefore most likely the JHUGen filter efficiency, not a jet-matching efficiency (INTERPRETATION, open).
- **(d) registry v5 analogue:** 40062 ggZH 4l (ESTIMATE, 0.1227 x 0.02619 x 0.10099 x 0.19178); 71227/70383 WH 4l (YR4 x 2.745e-4); 37728/68847 ggF/VBF 4l (YR4 x 2.745e-4).
- **Generator settings:** ATLAS 346645 = 0.7612 x 2.745e-4 (S2: the same 2.745e-4 is used as filter for H->mumu samples).


### 3.5 Decisions Matan must make (options only, no recommendation)

1. **N1, all four records.**
   - (i) Portal value as is (the precedent is the tribosons and tt̄W/tt̄Z in v5). Trade-off: LO; it differs from
     ATLAS by ×0.07–0.63 because the phase space differs, not because the normalisation is wrong.
   - (ii) McM value. Trade-off: it differs from the portal for 75561/69771, with no source given.
   - No theory option exists.
2. **N1, 69771 (WZjj).** It contains top diagrams (62 % of events), which overlap our tZq 68325.
   - (i) Accept and document.
   - (ii) Use an alternative record without top. On 24 Nov the CSV listed alternatives; whether a `_notop` WZ
     NanoAOD exists was not checked today.
   - (iii) Drop 69771.
3. **N1, s-channel Higgs inside 72648 (1.3 % of events) and the triboson-like part.** Accept and document (as your
   decision already says for tribosons), or not.
4. **N2, 71640.** Portal (0.02037) or McM (0.02227).
5. **N3, first the overlap** (section 2, options 1–4). Then the normalisation per sample:
   - (i) portal;
   - (ii) YR4 × a published B with the matching m_ℓℓ cut (needs option 1 or 2);
   - (iii) portal × the m_ℓℓ fraction measured in the sample (would need a convention for the denominator).

   Each depends on the overlap choice.
6. **N4, 74314.** One of options A, B, C/C′, D (3.3). Options C/C′/D rest on an INTERPRETATION of McM's 0.1509
   that the file-0 decay mix supports but no CMS document states.
7. **Outside scope, for later:** 40062's delivered estimate under the same reading (×1.49).

## 4. Files and cost (B4)

The file lists come from `tools/make_mappings.py`, which uses `fetch_file_list_complete` from pin 6de9d3e.
- The complete list equals page 1 for all 14 records, and every file the portal lists is published (no unpublished
  files).
- The mappings are in `precheck/mappings/`; URLs and counts are in `evidence/inputs_20261127.json`.

| item | records | files | events | production cluster files (12/file + 2/record, `HANDOFF.md:142`) |
|---|---|---:|---:|---:|
| N1 | 75561 (9), 69771 (34), 72648 (5), 71636 (22) | 70 | 3,647,203 | 848 |
| N2 | 71640 | 22 | 463,652 | 266 |
| N3 | 37276 (16), 37420 (4), 68459 (29), 68559 (4), 69681 (5), 69699 (25), 74652 (5), 74670 (3) | 91 | 10,897,859 | 1,108 |
| N4 | 74314 | 4 | 486,281 | 50 |
| **total** | 14 | **187** | **15,494,995** | **2,272** (ESTIMATE) |

**File count (`lfs quota -u berkom /storage`, column 6; VERIFIED BY RUNNING):**
- **122,540** before this task;
- **133,497** after the precheck.
- Of the +10,957:
  - about 10,710 are `nominal6_precheck_20261127/gridpack_cards/` (my card extraction matched card files in every
    MadGraph sub-process folder and created thousands of folders; the 143 card files that matter are copied to
    `evidence/gridpack_cards/`);
  - 183 are the precheck runs;
  - the rest are logs and scripts.
- Removing `gridpack_cards/` on the cluster needs Matan's OK; nothing was deleted.

**Projection (ESTIMATE):**
- production of the 14: +2,272;
- a full rebuild + checks into a new directory: +6,226 = (1,786 + 187) input files × 1,518/497 + ~200. This uses the
  rule of `studies/mc_expansion_20261103/HANDOFF.md:771`; the 14 Nov build measured +5,613 for 1,786 files
  (`HANDOFF.md`, "Final MC build").

| state | count | vs 125,000 | vs 140,000 |
|---|---:|---|---|
| now | 133,497 | above | below |
| + production + rebuild, as is | ~141,995 | above | **above** (by ~2,000) |
| the same, if `gridpack_cards/` (~10,710) is removed first | ~131,285 | above | below (~8,700 left) |
| the same, if the 14 Nov build scratch is also archived (Matan's call, not measured here) | lower | | |

## 5. Precheck results (C3; VERIFIED BY RUNNING)

How it ran:
- Code: pinned checkout 6de9d3e (HEAD and a clean status asserted); `studies/cms_mc_weights_v3/cluster/pbs_mc_pilot.sh`
  unchanged, mem 6 GB, 3 h, io=25.
- Jobs:
  - array **5662736[]** (14 subjobs, file 0 of each record);
  - generator check **5662743** (a retry of 5662737, which failed in 9 s because the job environment cannot open
    HTTPS files; the retry opens the `root://` URL as the driver does; the first attempt's logs are kept);
  - gridpack cards **5662738**;
  - analysis **5662739**.
- Output in the **new** directory `/storage/agrp/berkom/atlas-utilization/work/mcexp_20261103/nominal6_precheck_20261127/`;
  the production runs tree was not touched.
- The production driver does not read any registry. The precheck-only registry
  (`precheck/precheck_registry_PRECHECK_ONLY.json`, portal values, labelled "PRECHECK ONLY — NOT A CROSS SECTION
  DECISION") was passed explicitly to the analysis step only, for one illustrative column. The builder was not run.

Columns:
- "stored" = passed trigger + selection;
- "hist" = stored, in the delivery union, and with at least one mass signature, before the builder's mass-range cuts
  (as the QCD probe);
- negative weights are among the stored events (all-event fractions from `gen_check.json` agree);
- every job wrote the standard 9 files (8 shards + `job_metadata.json`), exited 0, had no traceback and no capped
  signatures, and recorded commit 6de9d3e.

| record | read | stored | hist | Σw check (rel. diff.) | neg. w | wall | max mem | top final states (events, file 0) |
|---|---:|---:|---:|---|---:|---:|---:|---|
| 75561 ZZjj EW | 106,134 | 91,533 | 90,813 | pass (0) | 0.000 | 12:36 | 0.55 GB | 0e2m2j 3,970; 2e0m2j 3,555; 0e2m3j 3,453; 2e0m3j 3,068; 0e1m3j 2,446 |
| 69771 WZjj EW | 3,712 | 2,856 | 2,769 | pass (0) | 0.000 | 4:27 | 0.10 GB | 0e1m2j 106; 0e2m2j 91; 0e2m1j 86; 0e1m1j1b 82; 2e0m1j 82 |
| 72648 WWjj EW | 124,000 | 79,269 | 69,900 | pass (0) | 0.000 | 3:59 | 0.39 GB | 0e1m1j 9,500; 1e0m1j 7,353; 0e1m2j 7,162; 1e0m2j 5,439; 1e1m1j 4,589 |
| 71636 W±W±jj EW | 22,392 | 14,437 | 13,401 | pass (0) | 0.000 | 2:31 | 0.15 GB | 0e1m2j 1,721; 0e1m1j 1,553; 1e0m2j 1,208; 1e0m1j 1,072; 1e1m1j 1,020 |
| 71640 W±W±jj QCD | 3,728 | 2,072 | 1,997 | pass (0) | 0.000 | 2:43 | 0.10 GB | 0e1m2j 242; 0e1m3j 203; 1e0m2j 168; 1e0m3j 154; 0e1m4j 122 |
| 37276 ggF Dalitz ee | 81,870 | 36,069 | 26,670 | pass (2.9e-9) | 0.214 | 2:14 | 0.23 GB | 1e0m1j 8,749; 2e0m0j 4,376; 1e0m2j 4,325; 2e0m1j 3,830; 2e0m2j 1,517 |
| 37420 ggF Dalitz μμ | 50,466 | 33,075 | 26,075 | pass (4.8e-10) | 0.211 | 2:23 | 0.21 GB | 0e1m1j 7,029; 0e2m0j 5,112; 0e2m1j 4,626; 0e1m2j 3,323; 0e2m2j 1,934 |
| 68459 VBF Dalitz ee | 35,378 | 16,982 | 14,328 | pass (3.4e-9) | 0.348 | 1:51 | 0.17 GB | 1e0m1j 4,850; 1e0m2j 2,816; 2e0m1j 2,052; 2e0m0j 1,083; 2e0m2j 1,028 |
| 68559 VBF Dalitz μμ | 50,000 | 34,056 | 30,145 | pass (8.2e-9) | 0.345 | 2:18 | 0.21 GB | 0e1m1j 7,914; 0e2m1j 5,819; 0e1m2j 4,765; 0e2m2j 3,065; 0e2m0j 2,922 |
| 69681 WH Dalitz ee | 759,742 | 377,403 | 342,197 | pass (1.5e-9) | 0.196 | 7:04 | 1.65 GB | 1e0m2j 59,227; 1e0m1j 54,095; 1e0m3j 36,411; 2e0m1j 29,349; 2e0m2j 26,321 |
| 69699 WH Dalitz μμ | 27,239 | 18,037 | 16,902 | pass (2.4e-9) | 0.191 | 3:17 | 0.17 GB | 0e1m2j 2,541; 0e1m1j 2,408; 0e2m1j 1,810; 0e2m2j 1,741; 0e1m3j 1,573 |
| 74652 ZH Dalitz ee | 26,042 | 12,437 | 11,179 | pass (7.6e-9) | 0.198 | 3:52 | 0.16 GB | 1e0m1j 1,808; 1e0m2j 1,808; 1e0m3j 1,156; 2e0m1j 823; 2e0m2j 732 |
| 74670 ZH Dalitz μμ | 61,990 | 40,068 | 37,308 | pass (3.0e-9) | 0.199 | 5:28 | 0.25 GB | 0e1m2j 5,159; 0e1m1j 5,005; 0e2m1j 3,474; 0e2m2j 3,449; 0e1m3j 3,234 |
| 74314 ZH H→ZZ 4ℓ filt. | 6,988 | 4,324 | 3,965 | pass (1.0e-8) | 0.029 | 4:52 | 0.11 GB | 0e1m1j 238; 0e2m1j 211; 2e0m1j 205; 0e1m2j 198; 0e2m2j 178 |

Final states are written `<e>e<m>m<j>j` with 0 b-jets unless shown.

**Unexpected, for the technical lead:**
1. The Dalitz ee samples land mostly in "1 electron" final states. The two electrons from a low-mass γ* are often
   too close to be resolved as two selected electrons. This is physics, not a crash.
2. The 69771 and 75561 file-0 sizes differ a lot (3,712 vs 106,134 events), as in the portal index.
3. No missing branches, zero-event files or crashes.

Other observations:
- The largest wall time was 12.6 min (75561 file 0, 106k events), so production walltimes of 2–3 h are ample
  (ESTIMATE).
- The illustrative weighted column (PRECHECK ONLY portal σ) is in `evidence/precheck/precheck_analysis.json`. For
  74314 it gives ~7,500 weighted events, a size that shows why the portal value (no BR, no filter) cannot be used as
  is.

## 6. Method and sources

**CMS (read-only, public):**
- CERN Open Data record API: `https://opendata.cern.ch/api/records/<id>`. The NanoAOD and MiniAOD records are saved
  in `evidence/records/`, the cross_section block is MiniAOD `metadata.cross_section`, and file lists come from
  `fetch_file_list_complete`.
- McM: request JSON `https://cms-pdmv-prod.web.cern.ch/mcm/public/restapi/requests/get/<prepid>` and fragment
  `https://cms-pdmv-prod.web.cern.ch/mcm/public/restapi/requests/get_fragment/<prepid>`. They are saved in
  `evidence/mcm/` (`tools/fetch_mcm.py`; the GEN prepids come from the MiniAOD production scripts). For the 19 records
  (14 additions + 5 H→Zγ), see `evidence/mcm_index.json`.
- Cards:
  - cms-sw/genproductions, linked in the fragments or found by name, in `evidence/mcm/cards/`;
  - **the cards inside the gridpacks** used on /cvmfs (`/cvmfs/cms.cern.ch/phys_generator/gridpacks/...`, list in
    `precheck/gridpacks.txt`, sha256 of every gridpack in `evidence/gridpack_cards/<rec>/gridpack.sha256`), in
    `evidence/gridpack_cards/`. Where the two disagree (69771), the gridpack is authoritative.

**ATLAS:**
- Public metadata, 2024r-pp, atlasopenmagic 1.5.0 (24 Nov, `../nominal6_correspondence_20261124/evidence/`).
- Public job options from `gitlab.cern.ch/atlas-physics/pmg/infrastructure/mc15joboptions` and
  `gitlab.cern.ch/atlas-physics/pmg/mcjoboptions` (the `job_path` of each DSID), in `evidence/atlas_joboptions/`:
  345961, 345834, 345963–345965, 345316, 345833, 345320–345322, 346645, 700587–700594, 700603.

**Theory and experiment:**
- LHC Higgs WG YR4 pages, read 27 Nov 2026, saved in `evidence/theory/`:
  - <https://twiki.cern.ch/twiki/bin/view/LHCPhysics/CERNYellowReportPageAt13TeV>, rows 125.00:
    ggF 48.58, VBF 3.782, W⁺H 0.8400, W⁻H 0.5328, ZH 0.8839 (gg→ZH 0.1227), so qq→ZH 0.7612 pb;
  - <https://twiki.cern.ch/twiki/bin/view/LHCPhysics/CERNYellowReportPageBR>, row 125.00: ZZ 2.619e-2, Zγ 1.533e-3,
    γγ 2.270e-3, H→4ℓ (ℓ = e μ τ) 2.745e-4, (ℓ = e μ) 1.240e-4.
  - The YR4 report itself is CERN-2017-002, arXiv:1610.07922.
- PDG Z branching ratios (decision D6, re-read 31 Oct 2026): ee 3.3632 %, μμ 3.3662 %, ττ 3.3696 %.
- CMS-HIG-17-007, JHEP 11 (2018) 152, arXiv:1806.05996, Eq. (1) and text: B(H→γ*γ→μμγ) = 3.83e-5 (MCFM 7.0.1),
  with an m_ℓℓ = 50 GeV dividing line. Text extract in `evidence/theory/`.
- ATLAS, arXiv:2103.10322, Sect. 3: B(H→eeγ) = 7.20e-5 and B(H→μμγ) = 3.42e-5 for m_ℓℓ < 30 GeV (Pythia 8). Text
  extract in `evidence/theory/`.
- Measurements in other phase spaces (abstracts only): CMS arXiv:2008.07013 (EW ZZjj) and arXiv:2205.05711
  (EW W⁺W⁻jj).

**Tools (this folder):**
- `tools/fetch_mcm.py`, `tools/make_mappings.py`, `tools/make_v8_decisions.py`, `tools/xsec_options.py`;
- `precheck/gen_check.py`, `precheck/precheck_analysis.py`, `precheck/pbs_*.sh`, `precheck/submit_20261127.sh`.
- Cluster copies are listed with their sha256 in `evidence/precheck/scripts*.sha256`.

**Not done (by instruction):**
- no cross section chosen;
- no registry v6;
- no production of the 14, no rebuild, no delivery;
- no upstream change, no message to anyone;
- nothing deleted or moved on the cluster.
