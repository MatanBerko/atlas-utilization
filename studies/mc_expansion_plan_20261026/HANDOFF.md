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

## NOT done: step 4, the probe (cluster unreachable)

`ssh wipp-campus` once: "No route to host". `ssh wipp-home`: "Could not resolve hostname
wipp-jump.weizmann.ac.il" on every try during the session (five tries, 26 Oct). As on 21-23 Oct, this
usually means the Mac's VPN has dropped: **Matan, please reconnect the VPN.** Consequences:
- no probe job was submitted (no job IDs);
- the file quota was **not re-measured**; the plan uses 90,665 (end of 26 Oct, measured by the full-run task);
- the genWeight plots do not exist yet; N_eff values are ESTIMATES;
- the presence of `L1PreFiringWeight_Nom`, `Pileup_nTrueInt`, `LHE_HT`, `LHE_Njets` and the trigger branches
  in the new samples is UNVERIFIED (expected for NanoAODv9, not checked).

### How to run it (the probe script is committed and pushed)

Pin: the branch head at the time of running (it contains `probe_sample.py`, `plan_samples.py` and
`cluster/pbs_probe.sh`; first pushed in `7e26f5c`). From the Mac:

```bash
ssh wipp-home 'bash -s' <<'EOF'
set -euo pipefail
B=/storage/agrp/berkom/atlas-utilization
CK=$B/checkouts/mcplan_20261026; W=$B/work/mcplan_20261026
C=<full sha of the pushed branch head>
lfs quota -u berkom /storage | head -5                       # BEFORE (stop if > 125,000)
test ! -e $CK && test ! -e $W                                # new directories only
mkdir -p $CK $W/logs $W/probe
git clone -q --no-checkout https://github.com/MatanBerko/atlas-utilization.git $CK/repo_$C
git -C $CK/repo_$C checkout -q $C && test "$(git -C $CK/repo_$C rev-parse HEAD)" = $C
R=$CK/repo_$C
/opt/pbs/bin/qsub -J 0-29 -N mcplan_probe -l select=1:ncpus=1:mem=4gb,walltime=01:00:00,io=25 \
  -o "$W/logs/p_^array_index^.out" -e "$W/logs/p_^array_index^.err" \
  -v REPO_DIR=$R,WORK_DIR=$W,OUT_DIR=$W/probe $R/studies/mc_expansion_plan_20261026/cluster/pbs_probe.sh \
  | tee $W/probe_jobid.txt
EOF
```

(30 subjobs = `plan_samples.PROBE`: every tier 1-4 sample, the two W+jets alternatives, four Higgs samples.
`#PBS -m n` and queue N are in the script; io=25 because it reads ROOT files.) If still queued after ~1 h,
write the job ID here and continue.

### Collecting it

```bash
scp 'wipp-home:/storage/agrp/berkom/atlas-utilization/work/mcplan_20261026/probe/probe_*.json' \
    studies/mc_expansion_plan_20261026/evidence/probe/
python3 studies/mc_expansion_plan_20261026/stats_cost.py      # uses the probe files automatically
python3 studies/mc_expansion_plan_20261026/make_candidates.py
python3 studies/mc_expansion_plan_20261026/make_plots.py      # writes plots/genweight_<recid>.png
```
Then check: every `branches_missing` is empty (else STOP: the production would fail on that sample);
`runs_vs_events_sumw_rel` ≈ 0 (no pre-skim, like the 25 Oct files); `frac_negative` ≈ the portal value;
for the W+jets pieces, `lhe_njets_counts`. Re-assemble PLAN.md §4 from `evidence/stats_table.md`
and measure the quota again (`lfs quota`, then after).

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
7. File quota: ~+20,600 files for all tiers (ESTIMATE) → ~111,000 of 125,000.

Local repo switched back to `master` at the end. STOPPED.
