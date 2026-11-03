# Small real-file check (task A1 step 3, 3 Nov 2026)

**SMOKE TEST, NOT PHYSICS.** File 0 of every sample, built with the existing MC builder (`--smoke-test`): Σw
comes from file 0 only, so each sample is normalised as if file 0 were the whole sample. Yields are statistically
unbiased but noisy; nothing here is a result. All numbers VERIFIED BY RUNNING (jobs below) unless marked ESTIMATE.

## What ran

- Code: commit `e04121d` on `feature/mc-expansion-20261103`, pinned clone `checkouts/mcexp_20261103/repo_e04121d…`
  (HEAD asserted). Production code = master `3054df3` = the 25 Oct production pin `75b399e` (only
  `studies/fullrun_20261025/` files differ); the production does not read the registry.
- Production, `studies/cms_mc_weights_v3/cluster/pbs_mc_pilot.sh` unchanged (mem 6 GB, 3 h, io=25):
  - **5433276[]**: file 0 of the 54 new samples — **54/54 exit 0**;
  - **5433277[]**: file 0 of the 13 delivered samples again — **13/13 exit 0**;
  - every Σw self-check passes; every job records commit `e04121d`.
- Post jobs (`precheck/pbs_precheck.sh`):
  - `compare` 5433278: the 13 re-runs vs the 25 Oct outputs — **ALL IDENTICAL**: every table of all 8 shards per
    job, and the job metadata apart from time, commit and timing diagnostics;
  - smoke builds A / B / C / D (5433279-82), all exit 0:
    - A = 13 delivered, registry v3;
    - B = the same with registry v4;
    - C = 54 new + 13 re-runs, registry v4, 331 histograms, 39 min, 0.76 GB;
    - D = 54 new + **the 25 Oct outputs read through `--extra-runs-dir`** (read only; the 25 Oct `job_0` files
      have identical name, size and mtime before and after);
  - `compare_builds` (5433397, then 5433883): **A vs B IDENTICAL** (14 ROOT files, every histogram; same σ_eff, Σw,
    normalisation). C vs D: see "Reuse" below;
  - `report` (5433283; plots re-made as `report_v2`, 5433447): the table and the plots below;
  - `checks_test` (5433398): the B-step checks run once on build C (see below).
- Two jobs (5433388, 5433389) stayed held on a dependency that PBS never released. They were resubmitted without
  the dependency and left in place: deleting them needs Matan's OK.

## Per sample (file 0)

Columns:
- Σw: the file's Runs-tree genEventSumw.
- N_eff/N: file 0, from the plan's probes of 26 / 31 Oct (same file).
- Weight scale: σ_eff × 16.393 fb⁻¹ / Σw(sample), with Σw(sample) = Σw(file 0) × events(sample) / events(file 0)
  (ESTIMATE until production); an event's weight = scale × genWeight (× L1 prefiring).
- Typical event weight: σ_eff × L / N_events(sample) = how many data events one MC event stands for.
- Final states: the production's exact labels, raw stored events, before the #40 rule.

| tier | record | sample | events read | stored | in delivery union | Σw (file 0, Runs) | N_eff/N (file 0) | weight scale σ·L/Σw (× genWeight) | typical event weight σ·L/N | 3 largest final states (raw, file 0) |
|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| del. | 35631 | DYJetsToLL_M-10to50_amcatnloFXFX | 2,444,741 | 21,807 | 19,771 | 8.261e+10 | — | 0.000183 | 6.19 | 0e_1m_0j_0b 5,412, 0e_1m_1j_0b 5,244, 1e_0m_1j_0b 3,324 |
| del. | 35669 | DYJetsToLL_M-50_amcatnloFXFX | 1,933,726 | 709,645 | 682,098 | 3.289e+10 | — | 7.74e-05 | 1.32 | 0e_2m_0j_0b 143,503, 2e_0m_0j_0b 112,685, 0e_1m_0j_0b 98,880 |
| del. | 37728 | GluGluHToZZTo4L_M125 | 4,000 | 2,115 | 2,037 | 1.158e+05 | — | 7.55e-06 | 0.000219 | 0e_2m_0j_0b 338, 2e_0m_0j_0b 293, 0e_1m_0j_0b 233 |
| del. | 64839 | ST_tW_antitop_5f_NoFullyHadronicDe | 45,342 | 19,237 | 18,785 | 1.474e+06 | — | 0.0027 | 0.0877 | 0e_1m_1j_1b 1,902, 0e_1m_2j_1b 1,688, 1e_0m_1j_1b 1,414 |
| del. | 64895 | ST_tW_top_5f_NoFullyHadronicDecays | 651,757 | 277,374 | 270,554 | 2.115e+07 | — | 0.00293 | 0.0952 | 0e_1m_1j_1b 27,177, 0e_1m_2j_1b 24,174, 1e_0m_1j_1b 21,051 |
| del. | 67801 | TTTo2L2Nu | 136,000 | 80,028 | 78,241 | 9.808e+06 | — | 0.000466 | 0.0336 | 0e_1m_1j_1b 5,403, 1e_0m_1j_1b 4,142, 0e_1m_0j_2b 3,864 |
| del. | 67993 | TTToSemiLeptonic | 1,233,000 | 431,885 | 419,238 | 3.711e+08 | — | 0.000138 | 0.0417 | 0e_1m_2j_1b 38,966, 1e_0m_2j_1b 30,045, 0e_1m_2j_2b 28,641 |
| del. | 68073 | TTWJetsToLNu | 9,451 | 4,520 | 4,435 | 3280 | — | 0.00306 | 0.00106 | 0e_1m_3j_1b 225, 0e_1m_3j_2b 188, 1e_0m_3j_1b 172 |
| del. | 68187 | TTZToLLNuNu_M-10 | 25,000 | 9,614 | 9,459 | 6254 | — | 0.00266 | 0.000664 | 0e_1m_3j_1b 353, 0e_1m_2j_1b 338, 1e_0m_3j_1b 315 |
| del. | 68847 | VBF_HToZZTo4L_M125 | 4,000 | 2,470 | 2,415 | 1.572e+04 | — | 8.69e-06 | 3.42e-05 | 0e_2m_1j_0b 217, 0e_1m_1j_0b 181, 2e_0m_1j_0b 160 |
| del. | 72676 | WWTo2L2Nu | 15,000 | 7,530 | 7,269 | 1.663e+05 | — | 0.00648 | 0.0718 | 0e_1m_0j_0b 1,668, 1e_0m_0j_0b 1,152, 0e_1m_1j_0b 937 |
| del. | 72752 | WZTo3LNu_amcatnloFXFX | 457,263 | 165,814 | 160,284 | 3.876e+06 | — | 0.00107 | 0.00909 | 0e_1m_0j_0b 25,599, 0e_1m_1j_0b 17,852, 1e_0m_0j_0b 16,069 |
| del. | 75589 | ZZTo4L | 168,000 | 48,759 | 46,594 | 2.225e+05 | — | 0.000367 | 0.000486 | 0e_1m_0j_0b 7,872, 0e_2m_0j_0b 6,443, 2e_0m_0j_0b 4,860 |
| 1 | 64635 | ST_s-channel_4f_leptonDecays-amcat | 1,000 | 271 | 256 | 3796 | 0.484 | 0.00267 | 0.0101 | 0e_1m_0j_1b 41, 0e_1m_1j_1b 33, 1e_0m_1j_1b 26 |
| 1 | 64659 | ST_t-channel_antitop_4f_InclusiveD | 860,000 | 97,897 | 94,233 | 5.497e+07 | 0.885 | 0.000678 | 0.0434 | 0e_1m_0j_1b 14,762, 0e_1m_1j_1b 12,799, 0e_1m_1j_0b 8,999 |
| 1 | 64759 | ST_t-channel_top_4f_InclusiveDecay | 861,000 | 92,244 | 88,847 | 9.153e+07 | 0.878 | 0.000333 | 0.0354 | 0e_1m_0j_1b 15,070, 0e_1m_1j_1b 11,255, 1e_0m_0j_1b 8,733 |
| 1 | 67841 | TTToHadronic-powheg-pythia8 | 1,344,000 | 1,078 | 1,020 | 4.218e+08 | 0.984 | 0.000185 | 0.058 | 0e_1m_3j_1b 108, 0e_1m_2j_1b 79, 1e_0m_3j_1b 70 |
| 1 | 69715 | WJetsToLNu_0J-amcatnloFXFX-pythia8 | 639,021 | 123,621 | 114,301 | 3.809e+10 | 0.643 | 8.61e-05 | 5.13 | 0e_1m_0j_0b 73,145, 1e_0m_0j_0b 45,016, 0e_1m_1j_0b 2,414 |
| 1 | 69717 | WJetsToLNu_1J-amcatnloFXFX-pythia8 | 2,083,059 | 527,560 | 503,994 | 9.512e+10 | 0.237 | 1.8e-05 | 0.823 | 0e_1m_1j_0b 190,621, 1e_0m_1j_0b 136,553, 0e_1m_0j_0b 99,780 |
| 1 | 69719 | WJetsToLNu_2J-amcatnloFXFX-pythia8 | 1,756,098 | 449,937 | 432,397 | 4.281e+10 | 0.097 | 2.45e-05 | 0.597 | 0e_1m_2j_0b 101,668, 0e_1m_1j_0b 93,833, 1e_0m_2j_0b 75,503 |
| 2 | 72658 | WWTo1L1Nu2Q_4f-amcatnloFXFX-pythia | 259,170 | 77,340 | 74,549 | 2.189e+07 | 0.364 | 0.000509 | 0.043 | 0e_1m_1j_0b 14,641, 0e_1m_2j_0b 12,937, 1e_0m_1j_0b 10,876 |
| 2 | 72738 | WZTo1L1Nu2Q_4f-amcatnloFXFX-pythia | 17,425 | 5,154 | 4,979 | 2.662e+05 | 0.340 | 0.00295 | 0.0451 | 0e_1m_2j_0b 875, 0e_1m_1j_0b 798, 1e_0m_2j_0b 635 |
| 2 | 72740 | WZTo1L3Nu_4f-amcatnloFXFX-pythia8 | 156,213 | 48,030 | 46,311 | 8.772e+05 | 0.328 | 0.00899 | 0.0505 | 0e_1m_0j_0b 13,399, 0e_1m_1j_0b 9,856, 1e_0m_0j_0b 9,491 |
| 2 | 72742 | WZTo2Q2L_mllmin4p0-amcatnloFXFX-py | 593,737 | 186,711 | 182,631 | 5.695e+06 | 0.389 | 0.000901 | 0.00864 | 0e_1m_2j_0b 16,442, 0e_1m_1j_0b 14,707, 1e_0m_2j_0b 13,595 |
| 2 | 75567 | ZZTo2L2Nu_powheg_pythia8 | 750,000 | 250,262 | 244,604 | 7.303e+05 | 0.996 | 0.0012 | 0.00117 | 0e_2m_0j_0b 45,656, 0e_1m_0j_0b 41,147, 2e_0m_0j_0b 36,085 |
| 2 | 75573 | ZZTo2Q2L_mllmin4p0-amcatnloFXFX-py | 883,793 | 306,269 | 299,977 | 4.871e+06 | 0.419 | 0.000933 | 0.00514 | 0e_1m_2j_0b 24,006, 0e_1m_1j_0b 22,491, 1e_0m_2j_0b 20,369 |
| 3 | 72701 | WWW_4F-amcatnlo-pythia8 | 79,000 | 23,367 | 22,821 | 1.707e+04 | 0.823 | 0.00394 | 0.000851 | 0e_1m_2j_0b 2,573, 0e_1m_3j_0b 2,288, 1e_0m_2j_0b 2,031 |
| 3 | 72711 | WWZ_4F-amcatnlo-pythia8 | 201,000 | 53,900 | 52,886 | 3.434e+04 | 0.823 | 0.00356 | 0.000609 | 0e_1m_2j_0b 4,836, 0e_1m_3j_0b 4,423, 1e_0m_2j_0b 3,882 |
| 3 | 72761 | WZZ-amcatnlo-pythia8 | 348,000 | 73,388 | 71,974 | 1.986e+04 | 0.822 | 0.0036 | 0.000206 | 0e_1m_2j_0b 5,059, 0e_1m_3j_0b 4,545, 1e_0m_2j_0b 4,238 |
| 3 | 75600 | ZZZ-amcatnlo-pythia8 | 212,000 | 33,609 | 33,142 | 3125 | 0.791 | 0.00362 | 5.34e-05 | 0e_2m_2j_0b 1,723, 0e_1m_2j_0b 1,703, 1e_0m_2j_0b 1,480 |
| 4 | 67645 | ttHTobb_M125-powheg-pythia8 | 9,000 | 1,997 | 1,968 | 4501 | 0.956 | 0.00196 | 0.000981 | 0e_1m_2j_2b 112, 0e_1m_2j_3b 103, 1e_0m_2j_3b 84 |
| 4 | 67691 | ttHToNonbb_M125-powheg-pythia8 | 83,999 | 23,915 | 23,328 | 4.215e+04 | 0.962 | 0.00309 | 0.00155 | 0e_1m_3j_2b 1,124, 0e_1m_3j_1b 1,107, 0e_1m_4j_1b 1,065 |
| 4 | 68045 | TTTT-amcatnlo-pythia8 | 9,000 | 3,283 | 3,235 | 69.63 | 0.174 | 0.00558 | 4.32e-05 | 0e_1m_5j_3b 98, 0e_1m_4j_3b 94, 1e_0m_5j_3b 89 |
| 4 | 68083 | TTWJetsToQQ-amcatnloFXFX-madspin-p | 1,023 | 231 | 224 | 682 | 0.290 | 0.0348 | 0.0232 | 0e_1m_3j_1b 18, 0e_1m_4j_1b 18, 0e_1m_3j_2b 14 |
| 5 | 37432 | GluGluHToMuMu_M125-powheg-pythia8 | 500,000 | 428,164 | 428,162 | 1.073e+07 | 0.979 | 1.61e-05 | 0.000347 | 0e_2m_0j_0b 201,243, 0e_1m_0j_0b 65,944, 0e_2m_1j_0b 65,309 |
| 5 | 37446 | GluGluHToTauTau_M125-powheg-pythia | 1,000 | 124 | 116 | 2.157e+04 | 0.988 | 0.00036 | 0.00776 | 0e_1m_1j_0b 30, 1e_0m_1j_0b 26, 0e_1m_0j_0b 19 |
| 5 | 37474 | GluGluHToWWTo2L2Nu_M-125-powheg-py | 12,000 | 4,196 | 3,942 | 2.577e+05 | 1.000 | 0.000299 | 0.00642 | 0e_1m_0j_0b 1,400, 1e_0m_0j_0b 858, 0e_1m_1j_0b 575 |
| 5 | 37604 | GluGluHToZG_ZToLL_M-125-powheg-pyt | 1,856 | 968 | 942 | 5.406e+04 | 0.983 | 1.96e-05 | 0.000571 | 0e_2m_0j_0b 143, 0e_2m_1j_0b 110, 2e_0m_0j_0b 110 |
| 5 | 37616 | GluGluHToZZTo2L2Nu_M125_powheg2_JH | 252,000 | 108,117 | 103,698 | 7.277e+06 | 0.980 | 3.92e-05 | 0.00113 | 0e_2m_0j_0b 19,476, 0e_1m_0j_0b 15,581, 2e_0m_0j_0b 15,270 |
| 5 | 40062 | GluGluToZH_HToZZTo4L_M125-jhugenv7 | 985 | 741 | 727 | 985 | 1.000 | 1.02e-06 | 1.02e-06 | 0e_2m_1j_0b 39, 2e_0m_1j_0b 36, 2e_0m_2j_0b 36 |
| 5 | 40095 | GluGluZH_HToWW_ZTo2L_M-125-powheg- | 936,318 | 663,979 | 658,469 | 5791 | 1.000 | 0.00148 | 9.16e-06 | 0e_2m_2j_0b 47,999, 2e_0m_2j_0b 42,034, 0e_2m_3j_0b 36,296 |
| 5 | 41873 | HWminusJ_HToWW_M-125-powheg-jhugen | 22,461 | 4,782 | 4,608 | 1.223e+04 | 0.898 | 0.00117 | 0.000637 | 0e_1m_1j_0b 672, 0e_1m_2j_0b 630, 1e_0m_2j_0b 529 |
| 5 | 41877 | HWplusJ_HToWW_M-125-powheg-jhugen7 | 5,603 | 1,217 | 1,188 | 4888 | 0.892 | 0.00118 | 0.00103 | 0e_1m_2j_0b 179, 0e_1m_1j_0b 164, 1e_0m_1j_0b 131 |
| 5 | 41914 | HZJ_HToWW_M-125-powheg-jhugen727-p | 918,060 | 151,742 | 146,164 | 8.739e+05 | 0.884 | 0.000627 | 0.000597 | 0e_1m_1j_0b 16,375, 0e_1m_2j_0b 15,310, 1e_0m_1j_0b 11,834 |
| 5 | 68571 | VBFHToMuMu_M125_withDipoleRecoil-p | 943,000 | 841,966 | 841,959 | 3.64e+06 | 0.997 | 3.71e-06 | 1.43e-05 | 0e_2m_1j_0b 262,757, 0e_2m_0j_0b 179,431, 0e_1m_1j_0b 124,143 |
| 5 | 68591 | VBFHToTauTau_M125-powheg-pythia8 | 2,504 | 396 | 378 | 9655 | 0.995 | 0.000672 | 0.00259 | 1e_0m_1j_0b 68, 0e_1m_1j_0b 67, 0e_1m_2j_0b 57 |
| 5 | 68601 | VBFHToWWTo2L2Nu_M125_powheg2_JHUGe | 366,700 | 148,484 | 142,500 | 1.427e+06 | 0.997 | 0.000101 | 0.000394 | 0e_1m_1j_0b 29,727, 1e_0m_1j_0b 21,167, 0e_1m_0j_0b 18,848 |
| 5 | 68731 | VBFHToZG_ZToLL_M-125-powheg-pythia | 2,646 | 1,496 | 1,465 | 1.02e+04 | 0.995 | 2.3e-05 | 8.89e-05 | 0e_2m_1j_0b 172, 2e_0m_1j_0b 129, 0e_1m_1j_0b 127 |
| 5 | 68741 | VBF_HToZZTo2L2Nu_M125_powheg2_JHUG | 8,000 | 4,215 | 4,087 | 3.149e+04 | 0.998 | 2.22e-05 | 8.74e-05 | 0e_1m_1j_0b 586, 1e_0m_1j_0b 490, 0e_2m_1j_0b 473 |
| 5 | 70301 | WminusH_HToZG_WToAll_M-125-powheg- | 18,811 | 2,924 | 2,842 | 1.021e+04 | 0.901 | 0.000152 | 8.27e-05 | 0e_1m_2j_0b 342, 0e_1m_1j_0b 328, 1e_0m_2j_0b 267 |
| 5 | 70383 | WminusH_HToZZTo4L_M125_powheg2-min | 3,072 | 1,856 | 1,814 | 1676 | 0.911 | 2.28e-05 | 1.24e-05 | 0e_2m_1j_0b 127, 0e_1m_1j_0b 124, 0e_1m_2j_0b 108 |
| 5 | 70451 | WminusHToMuMu_M125-powheg-pythia8 | 300,000 | 260,131 | 260,073 | 1.625e+05 | 0.898 | 1.17e-05 | 6.34e-06 | 0e_2m_1j_0b 48,149, 0e_2m_2j_0b 37,113, 0e_2m_0j_0b 28,088 |
| 5 | 70453 | WminusHToTauTau_M125-powheg-pythia | 599,276 | 141,858 | 136,554 | 3.245e+05 | 0.897 | 0.000507 | 0.000275 | 0e_1m_1j_0b 21,035, 0e_1m_2j_0b 18,569, 1e_0m_1j_0b 15,699 |
| 5 | 71145 | WplusH_HToZG_WToAll_M-125-powheg-p | 161,991 | 26,327 | 25,628 | 1.399e+05 | 0.884 | 0.000151 | 0.00013 | 0e_1m_1j_0b 3,169, 0e_1m_2j_0b 2,779, 1e_0m_1j_0b 2,586 |
| 5 | 71227 | WplusH_HToZZTo4L_M125_powheg2-minl | 13,797 | 8,109 | 7,918 | 1.192e+04 | 0.885 | 1.48e-05 | 1.28e-05 | 0e_1m_1j_0b 548, 0e_1m_2j_0b 492, 0e_2m_1j_0b 446 |
| 5 | 71295 | WplusHToMuMu_M125-powheg-pythia8 | 300,000 | 249,390 | 249,244 | 2.604e+05 | 0.893 | 1.15e-05 | 9.99e-06 | 0e_2m_1j_0b 43,041, 0e_2m_2j_0b 33,777, 0e_1m_1j_0b 27,841 |
| 5 | 71297 | WplusHToTauTau_M125-powheg-pythia8 | 72,352 | 17,094 | 16,440 | 6.273e+04 | 0.891 | 0.000498 | 0.000432 | 0e_1m_1j_0b 2,501, 0e_1m_2j_0b 2,192, 1e_0m_1j_0b 1,988 |
| 5 | 74292 | ZH_HToZG_ZToAll_M-125-powheg-pythi | 19,000 | 2,104 | 2,048 | 1.502e+04 | 0.889 | 0.000149 | 0.000118 | 1e_0m_2j_0b 138, 0e_1m_1j_0b 131, 0e_1m_2j_0b 131 |
| 5 | 74682 | ZHToMuMu_M125_CP5-powheg-pythia8 | 496,320 | 420,080 | 420,013 | 3.92e+05 | 0.887 | 6.93e-06 | 5.47e-06 | 0e_2m_1j_0b 63,570, 0e_2m_0j_0b 55,791, 0e_2m_2j_0b 53,655 |
| 5 | 74684 | ZHToTauTau_M125_CP5-powheg-pythia8 | 640,875 | 121,167 | 116,383 | 5.061e+05 | 0.887 | 0.00041 | 0.000323 | 0e_1m_1j_0b 13,511, 0e_1m_2j_0b 12,734, 1e_0m_1j_0b 9,902 |
| 6 | 74894 | ZJetsToNuNu_HT-100To200-madgraphML | 121,434 | 11 | 11 | 1.214e+05 | 1.000 | 0.659 | 0.659 | 1e_0m_1j_0b 5, 1e_0m_0j_0b 3, 0e_1m_2j_0b 1 |
| 6 | 74896 | ZJetsToNuNu_HT-1200To2500-madgraph | 1,249 | 1 | 1 | 1249 | 1.000 | 0.0378 | 0.0378 | 0e_1m_6j_0b 1 |
| 6 | 74898 | ZJetsToNuNu_HT-200To400-madgraphML | 1,157,106 | 235 | 224 | 1.157e+06 | 1.000 | 0.188 | 0.188 | 1e_0m_1j_0b 51, 1e_0m_2j_0b 43, 1e_0m_3j_0b 26 |
| 6 | 74900 | ZJetsToNuNu_HT-2500ToInf-madgraphM | 96,199 | 70 | 69 | 9.62e+04 | 1.000 | 0.00089 | 0.00089 | 1e_0m_3j_0b 11, 1e_0m_4j_0b 11, 1e_0m_2j_0b 9 |
| 6 | 74902 | ZJetsToNuNu_HT-400To600-madgraphML | 612,424 | 192 | 187 | 6.124e+05 | 1.000 | 0.0284 | 0.0284 | 1e_0m_2j_0b 52, 1e_0m_1j_0b 38, 1e_0m_3j_0b 23 |
| 6 | 74904 | ZJetsToNuNu_HT-600To800-madgraphML | 9,272 | 5 | 5 | 9272 | 1.000 | 0.0224 | 0.0224 | 0e_1m_5j_0b 1, 1e_0m_1j_0b 1, 1e_0m_1j_1b 1 |
| 6 | 74906 | ZJetsToNuNu_HT-800To1200-madgraphM | 62,724 | 32 | 32 | 6.272e+04 | 1.000 | 0.0298 | 0.0298 | 1e_0m_2j_0b 7, 1e_0m_4j_0b 7, 1e_0m_3j_0b 5 |

Things to note:
- **Zero / almost no selected events:**
  - Z → νν has 1-235 stored events per file 0 (of 1k-1.2M read). This is **expected**: no prompt charged lepton,
    so only fake or non-prompt leptons pass.
  - tt̄ hadronic stores 1,078 of 1,344,000 (0.08 %, also expected).
  - No sample has zero.
- **Largest typical event weights** among the new samples:
  - W+jets 0J: 5.1 data events per MC event (with negative weights; D3);
  - Z → νν HT 100-200: 0.66;
  - W+jets 1J: 0.82 if all 117 files existed, but only 30 are published (see HANDOFF), so effectively ≈ 3.0;
  - W+jets 2J: 0.60.

  For comparison, the delivered DY 10-50 is 6.2.
- **H → μμ samples**: 37432, 68571, 71295, 70451, 74682 (and 71145) are single-file samples, so the smoke and
  full-sample weights coincide.

## Stacks: 13 delivered (build A, line) vs 13 + 54 (build C, stacked)

`precheck_plots/stack_<category>.png`. Smoke-normalised weighted yields:

| category | build A: 13 delivered | build C: 13 delivered | C: W+jets | C: dibosons new | C: Higgs new | C: VVV, tt̄X, 4t | C: single top t/s |
|---|---:|---:|---:|---:|---:|---:|---:|
| μμ, 0 jets | 176,975 | 177,262 | 9,011 | 119 | 78 | 5.1 | 7.5 |
| eμ, 0 jets | 34,566 | 18,442 | **19,168** | 40 | 32 | 13.6 | 85.7 |
| ee + 1 jet | 37,593 | 37,619 | 1,290 | 163 | 5.8 | 10.7 | 20.6 |
| ee + 2 jets | 13,334 | 13,393 | 783 | 235 | 4.7 | 20.1 | 10.3 |
| 3ℓ (ee + μ, 0j), m(ee) | 79.0 | 93.5 | 0 | 0.02 | 0.88 | 1.09 | 0 |
| 3ℓ (e + μμ, 0j), m(μμ) | 192.6 | 206.8 | 0 | 0.17 | 0.52 | 0.94 | 0 |

Plots are from the report re-run 5433447 (`report_v2`: stacks cropped to the filled range; typical-weight plot).
In `stack_emu_0j.png` the W+jets contribution shows isolated single-event spikes up to ~570 GeV. In the smoke build a
W+jets event weighs ~(number of files) × its full-run weight, so the spikes are exaggerated, but this is exactly what
the D3 check counts in the full build.

Two findings for the technical lead:
1. **W+jets roughly doubles the eμ 0-jet MC** (smoke; it is the open data/MC = 2.19 question in that final state).
2. **The 13 delivered samples' histograms change in the new build even though their inputs and weights are
   identical.** This is the builder's existing combined peak/split rule (`--peak-scope combined`, Matan 18 Oct): the
   peak and split masses are found on all samples together, so adding samples moves them. Examples:
   - eμ 0j: lower edge 60 → 80 GeV, split 560 → 640 GeV (this is why "13 delivered" drops from 34,566 to 18,442);
   - μμ 0j: split 620 → 780 GeV;
   - 3ℓ: split 250 → 420 and 200 → 350 GeV.

   The B step must compare the MC and data ranges per histogram (the data delivery keeps its own cuts).

μμ near 125 GeV (`stack_mumu_0j_125.png`): the μμ 0j histograms start at 110 GeV (Z cut); the H → μμ samples add
78 weighted events in the whole μμ 0j histogram, invisible on top of 1.8 × 10⁵.

Per-sample typical event weight: `precheck_plots/weight_scale.png`.

## B-step checks, test run on smoke build C (`evidence/precheck/checks_v4_on_C/`)

- NaN / inf / negative variances: **none** in 331 summed + all per-record histograms.
- Names: MC names have the data format (`ROI_mass_<pair>_cat_..._width_10.0`). Every data name exists in MC; 18 MC-only
  names are rare 4-lepton categories absent from the data delivery (fewer than 100 events in data).
- D3: the script runs. Its count (144 histograms) is meaningless on a smoke build, where a W+jets event's weight is
  ≈ (number of files) × its full-run weight.
- The two `zpeak_*.png` files in that folder are NOT Z peaks: they are the delivered ee/μμ 0j histograms, which start
  at 110 GeV (the builder's Z cut). That is why
- the Z-peak part was changed after this test to use the 25 Oct analysis function on the build's kept scratch (the
  delivered histograms have the Z region cut away). **That part has not been exercised yet**; A2/B must check it.
