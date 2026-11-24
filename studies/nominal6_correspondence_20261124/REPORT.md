# Nominal-6 vs our 71 CMS samples: per-item facts (24 Nov 2026)

Research only. Nothing in this folder is adopted, built, or written into any registry. Every number is labelled:
**VERIFIED** (read from a saved public record, or by reading code) or **ESTIMATE**. Every choice is left to Matan.

## 1. Plain summary

1. Maryna's sheet equals the official public ATLAS metadata: 246 DSIDs × 7 fields, 0 differences (VERIFIED); only 64 free-text descriptions differ.
2. So S1–S15 are properties of the official ATLAS metadata, which our ATLAS code uses as published: 13 CONFIRMED (S1–S8, S11–S15; S4 with a caveat), S9 CANNOT TELL, S10 NOT CONFIRMED.
3. CMS has a public counterpart, full or partial, for 12 of 15 N-items (N1–N5, N7, N9, N11–N15).
4. No CMS counterpart: N6 (gg→ZH, H→ττ/μμ) and N8 (H→invisible with leptonic W/Z); N10 has only an overlapping VH→non-bb sample.
5. New: W±H Dalitz samples exist (69681, 69699); the 26 Oct plan had them "not observed".
6. Double-counting risks: N5 (contains two of ours), N10 (all our VH), N15 (contains our tW), N11/N12 (W+jets/DY photons).
7. Our code has no sample-level photon overlap removal on either side (VERIFIED by reading).
8. Largest costs (ESTIMATE, cluster files): N13 ~3,700, N11 ~1,500, N3 ~1,400, N1 ~1,100; the 14 Nov projection left ~3,200 below 125,000.
9. Three CMS portal σ look wrong by orders of magnitude (42145, 69565, 42137); four have no H/V decay BR inside (74314, 74300, 68833, 69389). None is proposed.
10. C1/C2: CMS (ours) inclusive, ATLAS leptonic only; CMS leptonic alternatives exist but are partial (C1) or subsets (C2).
11. Every decision is listed as "Choice" in the table; nothing is adopted.

## 2. One row per item

Column meanings:
- **ATLAS** is the summed σ×k×ε of the Nominal-6 DSIDs (VERIFIED, public metadata).
- **CMS** gives NanoAOD record ids: events / files from the complete file index / portal `total_value` (VERIFIED, `evidence/record_details.json`). Raw records are in `evidence/records/`; MiniAOD ids, generators and every alternative are in `cms_candidates.csv`.
- **Cost** is cluster files = files × (12 + 1,518/497) + 2 per record. This is an **ESTIMATE** using the ratios at `studies/mc_expansion_20261103/HANDOFF.md:142,152,771`.
- **R1** (`studies/cms_mc_weights_v3/DESIGN.md:363-369`, `studies/mc_expansion_20261103/QCD_PROBE.md:229`): the portal `total_value` already contains the matching and filter efficiency, but **not** a decay BR done in a separate Pythia/JHUGen step.

No file was flagged as "listed but not published" for any new candidate. The only flag is our existing 72761 (WZZ, 9 listed / 6 published), which is already known (`HANDOFF.md:95,107`).

| Item | What ATLAS has (σ_eff) | CMS counterpart | Size (events / files) | Cost ESTIMATE (cluster files) | Double counting vs our 71 | Portal σ remarks (B4) / open choice for Matan |
|---|---|---|---|---|---|---|
| **N1** EW VV+2j / VBS | 8 Sherpa 2.2.12 DSIDs, 0.319 pb (4 EW + 4 interference) | **Partial.** 75561 ZZjj→4ℓ EW; 69771 WZjj EW (W→ℓν, Z→ℓℓ); 72648 W±W∓jj EW; 71636 W+W+jj EW. No separate W−W−jj; no interference-only sample (72652 = EW+QCD+interference). 5 more alternatives in the CSV. | 3.65 M / 70 | ~1,060 | Our WZ/ZZ/WW are QCD-produced (different coupling order), so no standard overlap. "noTop" versions avoid overlap with tZq/tt̄. | Portal σ 0.156 pb (4 records) vs ATLAS 0.319 pb; the generator cuts differ (fragments not read). **Choice:** which subset; with or without interference. |
| **N2** QCD same-sign ℓνℓν | 700603, 0.0222 pb | **Yes.** 71640 W+W+jj QCD (no top), 0.0204 pb. Alternative 71642 (with top). 72678 (WW double-parton) is a different process. | 0.46 M / 22 | ~330 | None (our WW 72676 is opposite-sign only). | W−W− not observed separately. **Choice:** 71640 or 71642. |
| **N3** Higgs Dalitz ℓℓγ | 5 DSIDs, 0.0344 pb | **Yes, all 5 modes, separately for ee and μμ:** ggF 37420/37276, VBF 68559/68459, **WH 69699/69681 (new)**, ZH 74670/74652. Also bbH/ttH Dalitz exist (not in ATLAS). | 10.9 M / 91 | ~1,390 | Possible overlap with our H→Zγ samples (37604, 68731, 70301, 71145, 74292) where m_ℓℓ is near m_Z; the m_ℓℓ cut is in the McM fragment (not read). | CMS sum 0.0055 pb vs ATLAS 0.0344 pb (ATLAS ggF uses the S5 filter value). **Choice:** add, and how to treat the m_ℓℓ overlap with H→Zγ. |
| **N4** qq→ZH, H→ZZ→4ℓ | 346645, 2.09e-4 pb (uses the S2 BR) | **Yes.** 74314 ZH_HToZZ_4LFilter. Alternative 74300 (2ℓ filter). | 0.49 M / 4 | ~60 | None (we have ggZH 4ℓ 40062 and W±H 4ℓ, but no qq→ZH 4ℓ). | Portal total_value 0.7935 pb is roughly the ZH production σ: the H→ZZ BR and the 4ℓ filter are not in it (JHUGen decay, R1). The portal also lists "matching 0.2" (validation efficiency 0.151), as noted in D13 (`PLAN.md:485`). **σ missing → a value is needed, not proposed here.** |
| **N5** VBF H→ZZ→ℓℓbb | 450576, 2.02e-3 pb | **Broader.** 68833 VBF_HToZZTo2L2X (2ℓ + anything). | 0.27 M / 1 | ~20 | **Yes:** 2L2X includes our 68741 (VBF ZZ→2ℓ2ν) and 68847 (VBF ZZ→4ℓ). | total_value 3.935 pb ≈ VBF production σ; the BR is missing (JHUGen decay, R1). **Choice:** use 68833 with a veto, or keep ours and leave ℓℓqq out. |
| **N6** gg→ZH, H→ττ / μμ | 600686 + 345098, 7.7e-3 pb | **NOT OBSERVED.** 13 + 6 + 246 hits for ggZH patterns; all are BSM, ZZ→4ℓ (40062, ours) or WW (40095, ours). | – | 0 | – | Our ZHToTauTau 74684 and ZHToMuMu 74682 are qq→ZH (POWHEG HZJ) only. **Choice:** accept the gap. |
| **N7** SM three top | 304014, 1.64e-3 pb | **Yes, in two parts:** 67771 TTTJ + 68067 TTTW. | 0.32 M / 21 | ~320 | None (our TTTT 68045 is four top). | Sum 1.13e-3 pb (LO). **Choice:** add or not (tiny σ). |
| **N8** VH H→inv (leptonic V) + ggZH ZZ→4ν | 4 DSIDs, 2.37e-3 pb | **NOT OBSERVED** for a leptonic V or 4ν. Only hadronic-V records exist (71359, 70515, 74892, 36929), plus ggF/VBF/ttH H→inv. | (hadronic: 2.0 M / 18) | (~280) | – | The hadronic-V samples have no prompt lepton, so they are not equivalent. **Choice:** accept the gap. |
| **N9** tZq | 410560 tZ 4fl noAllHad, 0.240 pb (LO): leptonic top with Z→all, plus hadronic top with Z→ℓℓ (VERIFIED, job options) | **Partial, already ours:** 68325 tZq_ll (Z→ℓℓ only, NLO), 0.0756 pb. No CMS tZq with Z→νν/qq (patterns tZq, TZQ, ST_tZ, tZ_, TZQB; only tune variations 68327–68335). | (in v5) | 0 | – | The difference is scope (Z→νν/qq with leptonic top), not a missing sample. **Choice:** accept. |
| **N10** inclusive Higgs (VBF, W±H, ZH all decays) | 4 DSIDs, 5.92 pb; listed **on top of** the exclusive decays (S12) | **Only a near match:** 69389 VHToNonbb (W±H + ZH, H→not bb). No inclusive VBF H. | 0.33 M / 14 | ~210 | **Yes:** it overlaps every VH sample we have (WH/ZH → ττ, μμ, WW, ZZ, Zγ). | total_value 2.516 pb ≈ VH production σ; BR(non-bb) is not in it (R1; matching 0.4 listed). ATLAS itself double counts here (S12). **Choice:** leave out. |
| **N11** V+γ (ℓℓγ, ννγ, ℓνγ) | 7 Sherpa 2.2.11 DSIDs, 1,461 pb (pT_γ > 7 GeV) | **Yes:** 69575 WGToLNuG_01J, 73904 ZGToLLG_01J, 73900 ZGTo2NuG. Alternatives: photon-pT slices 69569/71/73, the low-m_ℓℓ/low-pT_γ sample 73902, and 73898 (μμγ, 2 < m_ℓℓ < 15). | 88.7 M / 97 | ~1,470 | **Yes:** overlaps our W+jets (69715/17/19) and DY (35631, 35669) through photon radiation. **Our code has no sample-level photon overlap removal** (section 3). CMS analyses use a gen-level photon veto; the only text found is an analysis note (AN-24-159, HTTP 403, **UNVERIFIED**). | CMS 273 pb vs ATLAS 1,461 pb (different photon cuts). **Choice:** add, and whether a gen-photon veto must be written first. |
| **N12** V+γγ, EW ℓνγjj / ℓℓγjj, γγγ | 10 DSIDs, 12.7 pb | **Partial:** 42145 LNuGJJ EW, 42137 LLGJJ EW; alternatives 69565 and 73892. V+γγ and γγγ were **NOT OBSERVED**. | 0.37 M / 5 | ~80 | Overlap with N11 and with our W+jets/DY (as N11). | **Inconsistent portal σ:** 42145 = 66,680 pb and 69565 = 66,570 pb (for EW ℓνγjj; ATLAS 1.78 pb); 42137 = 145 pb (ATLAS ℓℓγjj 0.32 pb); 73892 = 0.115 pb. **A σ is missing/wrong; none is proposed.** |
| **N13** hadronic W/Z at high pT, hadronic V+γ | 6 DSIDs, 211 pb | **Yes:** W→qq HT 200–∞ (69751/53/55/57), Z→qq HT 200–∞ (74912/14/16/18), W(→jj)γ 69559. Z→bb and Z(→qq/bb)γ **NOT OBSERVED**. | 54.3 M / 245 | **~3,710** | None (our V+jets are leptonic or Z→νν). No prompt lepton, so it would contribute only via fake leptons. | The portal lists matching 0.1–0.2 next to total_value; R1 says it is inside, which is the same issue as the QCD probe (`QCD_PROBE.md:205,229`). **Choice:** add (largest cost). |
| **N14** WZ→qqνν, ZZ→qqνν/bbνν, ZZ→4ν | 4 DSIDs, 11.3 pb | **Partial:** 75571 ZZTo2Nu2Q (qq includes bb). WZ→qqνν and ZZ→4ν **NOT OBSERVED**. | 2.47 M / 23 | ~350 | None standard (our ZJetsToNuNu has QCD jets, not Z→qq). | 4.56 pb. **Choice:** add or not. |
| **N15** tW inclusive decays | 601352 + 601355, 72.0 pb | **Yes:** 64881 (top) + 64825 (antitop) inclusiveDecays. | 5.04 M / 47 | ~710 | **Yes, it contains** our 64895/64839 (NoFullyHadronic). Use one set or the other, never both. | Portal total_value is 32.45/32.51 pb for **both** inclusive and NoFullyHadronic. v5 uses 19.56 pb for ours (factor 0.5456, DESIGN.md:367). **Choice:** keep ours or replace with inclusive. |
| **C1** t-channel | ATLAS 410658/410659 leptonic top only, 70.4 pb | **Ours:** 64759/64659 InclusiveDecays (v5 136.02 / 80.95 pb). Leptonic-only CMS: 64711 (t→e) and 64745 (t→τ) CompHEP LO only; no SM t→μ record observed. | (in v5: 93.7 M / 121) | 0 (alternatives ~30) | – | Portal 113.4 / 67.93 pb vs v5 136.02 / 80.95 pb (v5 decision). **Choice:** keep inclusive (CMS has more hadronic-top events than ATLAS), or accept the difference. |
| **C2** tribosons | 12 lepton-filtered Sherpa DSIDs, 0.043 pb | **Ours:** 72701 WWW, 72711 WWZ, 72761 WZZ, 75600 ZZZ (inclusive, 0.458 pb). Lepton-filtered CMS: 72698 WWW DiLeptonFilter (6.87e-3 pb; = 0.2158 × filter 0.0318, R1 holds), 72718 WWZ→4ℓ2ν (2.07e-3 pb). | (in v5: 17.8 M / 57) | 0 (alternatives ~580) | The alternatives are subsets of ours (do not add both). | **Choice:** keep inclusive. |

C3 and C4 were not searched (as instructed). Confirmed in v5: 37616, 68741 (C3) and 41873, 41877, 41914, 40095 (C4) are all in `full_run_records` (VERIFIED, `items.json` check).
## 3. Code facts (VERIFIED BY READING, upstream/master 0f4c614; CMS driver at pin 6de9d3e)

**C1 - is there any overlap removal between samples (e.g. V+γ vs V+jets)?** No.

- The ATLAS pipeline has no sample-level or generator-level overlap removal. A search of all non-`studies/` code for
  truth / `GenPart` / LHE / `isPrompt` / photon-veto logic finds nothing.
- What exists is reconstruction-level ATLAS object overlap removal ("Table 4.1"):
  `services/parsing/event_selection.py:254-313`, defaults from `:151`. The photon steps are `:300-309`
  (photon within ΔR 0.4 of an e/μ is dropped; a jet within ΔR 0.4 of a photon is dropped). It is switched on at
  `config.yaml:98` (`enable_overlap_removal: true`).
- Photons are loaded and used in that step although they are not analysed:
  - `config.yaml:167` `objects_to_calculate: [Electrons, Muons, Jets, BJets] # , Photons, Taus`;
  - the 2024r-pp schema takes `BASE_OBJECTS`, which includes Photons (`services/parsing/schemas.py:30`, `:203-216`);
  - `services/parsing/file_parser.py:269-282` reads every schema object;
  - photon cuts pT > 25 GeV, |η| < 2.37 (`config.yaml:150`);
  - order in `orchestration/handlers/parsing_handler.py`: kinematic cuts `:284`, overlap removal `:306-309`, and only
    then `retain_objects_for_storage` `:326-328` (`event_selection.py:133-148`) drops photons; `objects_to_store`
    = `objects_to_calculate` (`domain/config.py:376-379`, `:410`).
  - Consequence (fact, not a recommendation): on the ATLAS side a reconstructed photon removes a nearby jet
    before the masses are built. The CMS driver does not do this.
- The CMS driver reads no `Photon_` branch (grep empty in `run_dataset_on_file.py` and `selection.py` at 6de9d3e);
  its only overlap removal is e–μ ΔR < 0.12 (`run_dataset_on_file.py:489`, `:833`). It has no sample-level overlap
  removal either.

So if V+γ (N11/N12) were added on either side next to V+jets, nothing in our code would remove the photon-radiation
overlap; that would need a new truth-level veto (an open choice for Matan, section 2, N11).

**C2 - where does the ATLAS side get σ, k-factor, filter efficiency and sumOfWeights?**

- `docker/requirements.txt:2` pins `atlasopenmagic==1.5.0`; `config.yaml:110-111` selects release `2024r-pp`.
- `services/metadata/fetcher.py:377-409` reads `cross_section_pb`, `sumOfWeights`, `kFactor`, `genFiltEff` from
  `atom.get_metadata`, defaulting a missing value to 1.0.
- Weight = σ × k × ε_filter × L / sumOfWeights: `domain/metadata.py:46`, `services/calculations/mc_weights.py:55-61`.
- Therefore every metadata value in section 4 is used by the ATLAS pipeline exactly as published (D1 below shows the
  sheet equals the published metadata), i.e. the S-inconsistencies are in the official ATLAS metadata, not in
  Maryna's copy.

## 4. Maryna's sheet vs the public ATLAS metadata; S1–S15

**D1 result (VERIFIED, `sheet_vs_public_metadata.csv`, 1,722 rows = 246 DSIDs × 7 fields):** all 246 DSIDs exist in
the public 2024r-pp metadata, and Physics Short, Generator, σ, k-factor, filter efficiency, sumOfWeights and the
number of file URLs (total 11,647) agree for **every** DSID (0 differences above 0.1 %). Every S-item below that is
"CONFIRMED" is therefore a property of the **official public ATLAS metadata**, which our ATLAS pipeline reads as-is
(section 3, C2) — not a copying error in the sheet.

The only column that differs is the free-text **Description**: 64 of 246 DSIDs
(`sheet_description_vs_public.csv`). Those differences do not enter any calculation.

All numbers below are VERIFIED from `evidence/atlas_public_metadata_2024r-pp.json` unless marked otherwise.
Reference values (YR4 Higgs σ, BRs) are quoted only to compare; none is proposed.

| S | Claim (short) | Finding | Evidence |
|---|---|---|---|
| S1 | VBF H→ττ filter efficiencies do not fit BR(ττ) | **CONFIRMED.** VBF ττ 346190–346193 have genFiltEff 0.02921 / 0.01106 / 0.01107 / 0.02966; divided by BR(H→ττ) = 0.06272 these are 0.4657 + 0.1764 + 0.1765 + 0.4729 = 1.29 (a set of filters on one decay cannot add to more than 1). The ℓℓ channel (346190) alone is 0.466 although BR(ττ→ℓℓ) ≈ 0.12. The same ratio for the ggF ττ set adds to 0.318. | 346190–346193 |
| S2 | H→μμ filter = H→4ℓ value | **CONFIRMED.** All H→μμ samples (345098 ggZH, 345103 ZH, 345104 W+H, 345105 W−H, 345106 VBF) have genFiltEff 2.745e-4, the same number as the ZZ→4ℓ samples (345066, 346414, 346511, 346645–346647) and as CMS record 37728 uses for 4ℓ; YR4 BR(H→μμ) is 2.18e-4 (reference only). | listed DSIDs |
| S3 | VH samples with BR missing | **CONFIRMED.** genFiltEff = 1 while σ is already the full VH σ: 506098 σ 0.90303 pb (> W+H 0.84), 506099 0.78732 (> ZH 0.7612), 506813 0.54655 (≈ ZH × BR(Z→qq)). The H decay BR is missing (factor ≈ 15.9 for ττ, ≈ 440 for γγ). They duplicate 345212 / 345217 / 345319. | 506098, 506099, 506813 |
| S4 | 346198 filter = BR(H→Zγ) only | **CONFIRMED, with caveat.** f = 0.001533 = BR(H→Zγ). Caveat: sibling semileptonic samples carry an extra ≈ ×0.45 (ZZ4ν semileptonic 4.82e-4 / 1.06e-3 = 0.455; ZZ4ℓ 5.58e-5 / 1.24e-4 = 0.45), so whether 346198 also needs a Z-decay factor is an **open choice for Matan / the technical lead**. | 346198 |
| S5 | ggF Dalitz 345961 filter differs from others | **CONFIRMED.** 4.306e-4 vs 0.00227 for VBF / W±H / ZH Dalitz (345834, 345963–345965). | N3 DSIDs |
| S6 | LFV H→eτ/μτ filters differ | **CONFIRMED.** ggF and W±H/ZH eτ/μτ (345124, 345125, 345213–345216, 345218, 345219) have 6.393e-6 / 6.395e-6; VBF eτ/μτ (346194, 346195) have 6.722e-4 / 6.719e-4 (factor 105). | listed DSIDs |
| S7 | W−H σ in one sample differs | **CONFIRMED.** 346647 (W−H, ZZ→4ℓ) σ 0.54001 pb vs 0.5328 pb in every other W−H sample. | 346647 |
| S8 | tHjb σ too small | **CONFIRMED anomaly.** 346414 (and 346188 γγ) 0.002879 pb vs YR4 tHq 0.0743 pb (factor 25.8). The public job options (`evidence/atlas_joboptions/`: `generate p p > h t1 b1 j $$ w+ w- [QCD]`, top decays all) show **no** generator cut that would explain it. tWH (346486/346511) 0.0152 pb agrees with YR4. | job options |
| S9 | Z→ee/μμ/ττ low-mass σ inconsistent | **PARTLY EXPLAINED → CANNOT TELL.** The ee/μμ job options have a MultiLeptonFilter (2 e/μ, pT > 5 GeV), which explains filter sums of 0.365 / 0.315; ττ has no filter. But the σ bases differ (7,897 pb Sherpa 2.2.11 vs 4,106.6 pb Sherpa 2.2.14) and ee ≠ μμ: effective ee 2,884, μμ 2,487, ττ 4,107 pb. Whether this is right cannot be decided from public information. | job options |
| S10 | sumOfWeights looks like a partial sum | **NOT CONFIRMED.** Test sumW² / (N · sumW2) (= 1 for constant weights, (1−2f)² for negative-weight fraction f): 410560 gives 1.000 (constant weight 4.37e-5 × N 129,200 = sumW); 410408 0.307 (≈ 22 % negative weights, normal for NLO); tribosons 0.85–0.90. Nothing points to a partial sum. | sumOfWeights, sumOfWeightsSquared, nEvents |
| S11 | duplicates in Nominal-6 | **CONFIRMED** – all listed duplicate pairs are present together. | sheet DSIDs |
| S12 | inclusive Higgs + exclusive decays both present | **CONFIRMED.** 346317, 346310–346312 and 346343–346345 are present together with the exclusive-decay samples (15 VBF, 44 qqVH DSIDs). This is N10. | sheet DSIDs |
| S13 | WZ/ZZ slicing incomplete | **CONFIRMED.** 364541 and 364545–364547 present; 364542–364544 absent. | sheet DSIDs |
| S14 | labels | **CONFIRMED** for categories (700358–700364 and 700442 under "Single top"; 700000 under ttW/ttZ; 700488/700491/700492/700507/700843 under W+jets; 700849/700855 under Other) and for the Generator column lacking Pythia8 (410644/410645 "Powheg+EvtGen"; 345961/345963–345965). These Generator strings are the **public** values. The description swaps (410156/410157, 410659, 601355) are **in the sheet only** – the public descriptions are correct. "mumugamma" for 700399/700401 is in the public metadata itself. | both CSVs |
| S15 | changes vs the 31 Oct list | **CONFIRMED** against `atlas_dsid_classification-4.xlsx` (31 Oct, BG Nominal 296 DSIDs; Matan's Downloads, not in the repo): exactly 57 removed (32 overflow + 25 Herwig7/duplicates + 801976/801978) and exactly 7 added (410156, 410157, 410218–410220, 410408, 410560), which on 31 Oct were "BG, Systematic, ME generator (MadGraph), alternative". The repo's only list is the 26 Oct 337-DSID `atlas_bkg_metadata.csv`; Nominal-6 is a subset of it. | xlsx, repo CSV |

**Other differences found:** none in the 7 numeric/text fields. 64 free-text descriptions differ (list in
`sheet_description_vs_public.csv`); the four S14 swaps are among them.

## 5. Method and sources

**Inputs (read only):**
- Maryna's sheet `~/Downloads/atlas_dsid_classification-5(Nominal-6 Samples).csv` (246 DSIDs, read in place, **not committed**).
- The 31 Oct workbook `~/Downloads/atlas_dsid_classification-4.xlsx` (for S15, not committed).
- Registry v5 `studies/cms_mc_weights_v3/cms_mc_normalisation_v5.json` (71 `full_run_records`).
- The technical lead's item list, encoded in `items.json` (N1–N15, C1–C4 and the documented exceptions that were not researched).

**ATLAS side (D1/D2):** `tools/fetch_atlas_public.py` in a temporary venv with `atlasopenmagic==1.5.0` (the version pinned at `docker/requirements.txt:2`), release `2024r-pp`. It reads `get_metadata` and the URL count for all 246 DSIDs and writes `evidence/atlas_public_metadata_2024r-pp.json`.
- `tools/compare_sheet.py` → `sheet_vs_public_metadata.csv` (difference threshold 0.1 %).
- `tools/compare_descriptions.py` → `sheet_description_vs_public.csv`.
- Public ATLAS job options (GitLab `mc15joboptions`, `mcjoboptions`) for 346188 (tHjb γγ; 346414 has the same σ), 410560 (tZ) and the Sherpa low-mass Z→ee and Z→ττ samples are in `evidence/atlas_joboptions/`.

**CMS side (B1/B2):**
- `tools/portal_search.py` → `evidence/portal_searches.json`. It ran 137 title patterns, each `title:*<pattern>* AND RunIISummer20UL16NanoAODv9`, NanoAODSIM, up to 20 pages of 100; results are cached in `evidence/portal_search_cache/`. Only post-VFP titles (`RunIISummer20UL16NanoAODv9`) count; APV is out.
  - The over-broad pattern `HTo2` stalled the first run and was replaced by `ToNonbb`, `VHTo` and `HToNonbb`.
  - "NOT OBSERVED" means no hit with these patterns, not proof that a sample does not exist.
- Tune/width/mass variations, BSM and non-125 GeV Higgs samples were set aside by reading titles.
- `tools/record_details.py` → `evidence/record_details.json` and the raw NanoAOD + MiniAOD records `evidence/records/<recid>.json.gz` (73 NanoAOD records). It records:
  - events;
  - the complete file index (sum of `_file_indices` number_files) and the number of listed entries;
  - generators;
  - the MiniAOD `cross_section` block.
- `tools/gen_prepids.py` → `evidence/gen_prepids.json`: the McM GEN request id and validation efficiency named in each record. The McM generator fragments (which hold the exact phase-space cuts) were **not** read; a fetch attempt was blocked by this session's permission settings. The fragment URLs are listed there. Where a cut is in the dataset title (HT, PtG, MLL, MJJ, filters) it is quoted from the title.
- `tools/build_candidates.py` → `cms_candidates.csv` (67 rows: item, role candidate/alternative/in_v5, NanoAOD/MiniAOD id, dataset, generators, events, files, file flag, portal σ, filter, matching, cost ESTIMATE, note).

**Cost ESTIMATE:** cluster files = files × (12 + 1,518/497) + 2 per record. The sources are:
- 12 per input file + 2 per record: `studies/mc_expansion_20261103/HANDOFF.md:142`;
- build scratch 1,518/497: `HANDOFF.md:152`, `:771`;
- the ~121,800 projection vs 125,000: `HANDOFF.md:771`, `:152`.

No cluster was used.

**Code (C1/C2):** read at upstream/master 0f4c614 and at the CMS driver pin 6de9d3e (file:line in section 3).

**Overlap documentation (B3):** no official CMS public document on V+γ vs V+jets overlap removal was found. The text seen is from an analysis note (AN-24-159, https://www.crc.nd.edu/~abasnet/EFT/Fall2024/photon_studies/AN-24-159/AN-24-159_temp.pdf, HTTP 403; quoted from a search snippet only, **UNVERIFIED**): a Zγ/DY veto at photon pT > 15 GeV, |η| < 2.6, ΔR 0.05, and a tt̄γ/tt̄ veto at pT > 10 GeV. For context only:
- CMS-TOP-23-002, https://cms-results.web.cern.ch/cms-results/public-results/publications/TOP-23-002/index.html;
- the ATLAS method, arXiv:2007.06946.

**Not done (by instruction):** no cross section, k-factor or filter efficiency was chosen; no registry, production code or upstream file was changed; nothing was produced or built; nobody was messaged.
