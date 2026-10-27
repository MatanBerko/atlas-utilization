# HANDOFF — MC expansion plan (26 Oct 2026)

Branch `plan/mc-expansion-20261026` (origin = MatanBerko fork only), made from `origin/master` = `3054df3`.
Research and planning only: no production, no build, no config/mapping/registry change, no existing file
edited (the upstream gate printed nothing before each push). No Pull Request; nothing sent to anyone.

## Done

- **Preflight** (VERIFIED BY RUNNING, `git fetch` + `git rev-parse`): `origin/master` = `3054df3`,
  `upstream/master` = `29291ae` (both unchanged).
- **Step 1, campaign check:** all 13 delivered samples are RunIISummer20UL16NanoAODv9 post-VFP, tune CP5;
  no problem (PLAN.md §1).
- **Step 2, candidates:** portal searches per group, 311 NanoAOD records + MiniAOD parents saved
  (`evidence/records/`), generator cards of the 58 planned/alternative/optional samples (`evidence/cards/`).
- **Step 3, double counting:** PLAN.md §3.
- **Step 5, statistics and cost:** `stats_cost.py` → `evidence/stats_cost.json`, PLAN.md §4 — with ESTIMATED
  N_eff (portal negative-weight fraction) because the probe could not run.
- **Step 6, cross-section proposals:** `XSEC_PROPOSALS.md` — 39 recommended + 4 alternative samples, every
  source page/paper opened on 26 Oct (VERIFIED BY RUNNING), nothing applied.
- **Step 7, plan:** `PLAN.md`, `candidates.json`, `plots/mc_lumi_vs_data.png`.

## Step 4, the probe — DONE (26 Oct 2026, second session)

Everything below VERIFIED BY RUNNING.
- Preflight: branch head `868352a` (unchanged), `upstream/master` `29291ae`. `ssh wipp-campus`: "No route to
  host" (one try); `wipp-home` worked.
- File quota (`lfs quota -u berkom /storage`): **90,665 before**, **92,041 after** (+1,376: the pinned clone and
  the probe outputs/logs). Under 125,000.
- New directories (did not exist before): `checkouts/mcplan_20261026/repo_868352ab100da6e45a22682d2d0a324eecf7ed52`
  (HEAD asserted = that sha) and `work/mcplan_20261026/{logs,probe}`.
- Submitted exactly the command of the first HANDOFF with C = `868352ab100da6e45a22682d2d0a324eecf7ed52`:
  **PBS array `5365612[]`**, `-J 0-29`, mem 4gb, walltime 1 h, io=25, queue N, `-m n`. All 30 subjobs
  `Exit status: 0`, wall ≤ 12.6 s; every log prints `commit=868352a…`.
- Collected: `evidence/probe/probe_<recid>.json` (30) and `evidence/probe/logs/p_*.{out,err}`; re-ran
  `stats_cost.py`, `make_candidates.py`, `make_plots.py` (30 `plots/genweight_<recid>.png`).

Results (PLAN.md §4a):
- `branches_missing` is **empty for all 30** (42 production branches incl. `L1PreFiringWeight_Nom`,
  `Pileup_nTrueInt`); `LHE_HT`, `LHE_Njets` present in all.
- `runs_vs_events_sumw_rel` |·| ≤ 5e-8 in all 30.
- `frac_negative` matches the portal within 0.011, except s-channel 0.152 vs 0.174 and ggH → ττ 0.003 vs
  0.005 (both have only 1,000 events in file 0).
- N_eff / MC luminosity within ~3 % of the estimates except s-channel (+14 %) and tt̄tt̄ (−9 %); W+jets still
  0.125 / 0.288 / 0.162 × the data luminosity. No conclusion of the plan changed.
- LHE_Njets in the W+jets NLO pieces: 0J {0: 539,283, 1: 99,738}, 1J {1: 1,472,816, 2: 610,243},
  2J {2: 1,126,525, 3: 629,573} — each piece also contains real-emission events with one more LHE parton,
  so the pieces cannot be cut against each other by LHE_Njets (not needed for option A). For the technical lead.
- Not probed (keep ESTIMATES): 11 of the 15 recommended Higgs samples and the two 4-flavour t-channel
  alternatives (the ≤ 30 limit).

Changed files: `stats_cost.py` (quota baseline 92,041; keeps the portal estimate next to the probe value),
`PLAN.md` (summary, §3 note, §4 table with old-estimate column, new §4a with the plots, §8), this file, the
regenerated `candidates.json`, `evidence/stats_cost.json`, `evidence/stats_table.md`, `evidence/stats_cost_table.txt`,
new `evidence/probe/`, `evidence/probe_section.md`, `plots/genweight_*.png`. Nothing outside this folder;
no registry or config touched; cluster outputs left in place.

## ATLAS DSID mapping — DONE (27 Oct 2026, third session)

Everything below VERIFIED BY RUNNING unless marked ESTIMATE / UNKNOWN. No cluster use; no ROOT file
downloaded; no access to anyone's storage; no registry/config change; no cross section changed.
- Preflight: branch head `21e5fa7` (unchanged), `upstream/master` `29291ae`. atlasopenmagic 1.10.1 in env
  `hep`; release `2024r-pp` available (626 dataset entries).
- Step 1: metadata for all **337** DSIDs (none missing): `atlas_mapping/atlas_bkg_metadata.{json,csv}`.
- Step 2-3: 337 DSIDs → **108 processes** (53 non-Higgs, 55 Higgs cells) → CMS status, σ, ratio
  (`mapping.py` → `mapping.json`, `mapping_tables.md`). 86 DSIDs are ATLAS alternative generators and 21 are
  decay subsets (listed for Maryna).
- Step 4: reverse check, 17 rows (`reverse_check.json`). Only ggF/VBF H → ZZ → 2ℓ2ν clearly lack an ATLAS
  counterpart; for tt̄ + ℓℓ (1-10 GeV) it is UNKNOWN.
- Step 5: Higgs production × decay table and costs (`higgs_scope.py` → `higgs_scope.json`). The recommendation
  is option (a) + 11 samples (H → μμ ×5, H → Zγ ×5, gg → ZH → 4ℓ).
- Extra CMS portal lookups: 31 records + 16 NOT OBSERVED (`fetch_cms_extra.py`, `cms_extra_records.json`,
  `cms_records/`).
- Findings for Matan/Maryna:
  - Maryna's "EW boson" class contains the Pythia8 QCD dijet set 364700-364712.
  - Her "QCD jets" 700442 is EW γ + 2 jets.
  - The 16 DSIDs between 353 and 337 are UNKNOWN from the metadata.
- Written: `atlas_mapping/` (all new files) and the new PLAN.md section "7. ATLAS DSID mapping (27 Oct)" (no
  existing section rewritten), plus this section.

## What the implementation step would need (after the technical lead and Matan)

1. Matan's decisions D1-D15 (PLAN.md §6) and his sample-by-sample check of `XSEC_PROPOSALS.md`.
2. A **new** registry version built from a new decisions file (never an edit of
   `cms_mc_normalisation_v3.json` in place), with `in_full_run` for the chosen records; the builder refuses
   unknown records, so this comes first.
3. The input-file sweep (`cms_mc_weights_v3/fullrun_prep/check_input_files.py`) and mappings
   (`make_fullrun_mappings.py` reads a sweep JSON) for the new records.
4. Production with the unchanged MC launcher (`pbs_mc_pilot.sh`), tier by tier: per-user limit 1,000
   queued subjobs (tier 1 = 518 files fits alone; all tiers = 1,145 do not); io=25; 2 h wall time, 3 h for
   tier 4 (tt+X ran up to 2,668 s per file on 25 Oct); new dated directories.
5. If W+jets option D (LO + binned) were chosen: new LHE-level stitching code in the builder (not needed for
   the recommended option A).
6. One MC build with the old 13 + new samples, then the usual audit, rule check, sanity plots; check the
   W+jets histograms for single-event spikes (MC luminosity 0.13-0.29 × data).
7. File quota: ~+20,600 files for all tiers (ESTIMATE) → ~112,600 of 125,000 (from 92,041 measured 26 Oct).

Local repo switched back to `master` at the end. STOPPED.
