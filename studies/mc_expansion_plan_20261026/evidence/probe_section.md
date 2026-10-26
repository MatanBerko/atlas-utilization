### 4a. Probe results (step 4, PBS array 5365612[], 26 Oct 2026; VERIFIED BY RUNNING)

File index 0 of each of the 30 samples in `plan_samples.PROBE`, read with uproot in a PBS job (io=25) from the
checkout pinned to `868352ab100da6e45a22682d2d0a324eecf7ed52`; all 30 subjobs exit status 0, ≤ 13 s each.
Raw results `evidence/probe/probe_<recid>.json`, logs `evidence/probe/logs/`.

- **Branches:** all 42 branches the production reads (object, trigger, trigger-object and MC branches,
  including `genWeight`, `L1PreFiringWeight_Nom`, `Pileup_nTrueInt`) are present in **every** probed file;
  `LHE_HT` and `LHE_Njets` too. `branches_missing` is empty for all 30.
- **Runs tree vs events:** Σ genWeight over the file equals the Runs-tree `genEventSumw` to ≤ 5 × 10⁻⁸ in
  all 30 files (no pre-skim, as for the 25 Oct samples).
- **Negative-weight fraction:** matches the portal value within 0.01 everywhere except s-channel (0.152 vs
  0.174; its file 0 has only 1,000 events) and ggH → ττ (0.003 vs 0.005; 1,000 events).
- **N_eff and MC luminosity:** within ~2 % of the portal estimates for every sample except s-channel
  (+14 %, small file 0) and tt̄tt̄ (−9 %). The table above shows both. 13 recommended Higgs samples and the
  two 4-flavour alternatives were not probed (the ≤ 30 limit) and keep the ESTIMATE.
- **LHE_Njets in the three W+jets pieces** (file 0):

| piece | LHE_Njets counts | 
|---|---|
| 69715 0J | 0: 539,283, 1: 99,738 |
| 69717 1J | 1: 1,472,816, 2: 610,243 |
| 69719 2J | 2: 1,126,525, 3: 629,573 |
| 69745 inclusive NLO (alt.) | 0: 263,893, 1: 110,790, 2: 58,433, 3: 18,540 |
| 69747 inclusive LO (alt.) | 0: 101,865, 1: 22,104, 2: 6,785, 3: 2,025, 4: 913 |

  Not exactly 0 / 1 / 2: each NLO piece also has events with one parton *more* (0J: 16 % with 1, 1J: 29 %
  with 2, 2J: 36 % with 3). That is what an NLO sample looks like (the real-emission parton is written to
  the LHE record); the pieces are still separate by their Born-level parton count, which is how they were
  generated. **It means LHE_Njets cannot be used to cut the pieces against each other or against an
  inclusive sample** — irrelevant for the recommended option A (each piece normalised on its own, no
  stitching), but it rules out naive LHE_Njets stitching of the NLO set. For the technical lead to confirm.
- **genWeight distributions** (sign and log10 |w|, file 0): `plots/genweight_<recid>.png`, below. The MG5
  samples have a single |w| value (constant weights ±); POWHEG samples have a spread.

![genWeight 37446](plots/genweight_37446.png)
![genWeight 37474](plots/genweight_37474.png)
![genWeight 41877](plots/genweight_41877.png)
![genWeight 64635](plots/genweight_64635.png)
![genWeight 64693](plots/genweight_64693.png)
![genWeight 64793](plots/genweight_64793.png)
![genWeight 64873](plots/genweight_64873.png)
![genWeight 67645](plots/genweight_67645.png)
![genWeight 67691](plots/genweight_67691.png)
![genWeight 67841](plots/genweight_67841.png)
![genWeight 68045](plots/genweight_68045.png)
![genWeight 68083](plots/genweight_68083.png)
![genWeight 68185](plots/genweight_68185.png)
![genWeight 68206](plots/genweight_68206.png)
![genWeight 68325](plots/genweight_68325.png)
![genWeight 68601](plots/genweight_68601.png)
![genWeight 69715](plots/genweight_69715.png)
![genWeight 69717](plots/genweight_69717.png)
![genWeight 69719](plots/genweight_69719.png)
![genWeight 69745](plots/genweight_69745.png)
![genWeight 69747](plots/genweight_69747.png)
![genWeight 72658](plots/genweight_72658.png)
![genWeight 72701](plots/genweight_72701.png)
![genWeight 72711](plots/genweight_72711.png)
![genWeight 72738](plots/genweight_72738.png)
![genWeight 72740](plots/genweight_72740.png)
![genWeight 72742](plots/genweight_72742.png)
![genWeight 72761](plots/genweight_72761.png)
![genWeight 75573](plots/genweight_75573.png)
![genWeight 75600](plots/genweight_75600.png)

