# HANDOFF — SingleElectron Step 1 (measurement only)

Measurement only. No production code is changed, no delivery is built, no
production run is made, and the threshold decision is not taken here.

## 1. Code

| what | value |
|---|---|
| branch | `study/singleelectron-ele27-tnp` (fork `github.com/MatanBerko/atlas-utilization`) |
| branched from | `origin/master` = `db1bd32` (verified before branching) |
| **pinned commit every job runs from** | `8670f8f5363344754416152dbdee8c828d091ce1` |
| cluster checkout | `/storage/agrp/berkom/atlas-utilization/checkouts/8670f8f/repo` |

An earlier commit `58f3ca1` has a checkout too; it was superseded by
`8670f8f`, which adds the inefficiency decomposition. Only `8670f8f`
produced reported results.

Everything from production is **imported read-only** — the object
definitions, the dR < 0.12 electron-muon overlap removal, the id-guarded
trigger matcher, the four dataset acceptances, the Version B labelling and
the golden-JSON / HLT filters. Nothing in `services/`,
`run_dataset_on_file.py`, `datasets_records.py` or the delivery builders is
modified.

## 2. Jobs

OpenPBS arrays, queue `N`, `#PBS -m n`, `mem=8gb`, `walltime=02:00:00`,
`io=25`. Logs under
`/storage/agrp/berkom/atlas-utilization/logs/singleelectron_prep/`
(never `$HOME`); temporaries in `$TMPDIR`.

| job ID | array | what | output |
|---|---|---|---|
| `5195985[]` | 0-150 | **Steps B + D**: Z→ee tag-and-probe and the offline-threshold scan, all **151** SingleElectron files | `.../singleelectron_prep_20261007/tnp/` |
| `5195986[]` | 0-151 | **Step C(2)**: prescale / path-enabled test on all **152** SingleMuon files | `.../singleelectron_prep_20261007/prescale/` |

Step C uses the full SingleMuon set rather than the 40-file minimum: a
timing test showed a file costs under a minute here, because only the run,
HLT and TrigObj branches are read.

## 3. Output directories (all NEW, date-suffixed; nothing existing touched)

```
/storage/agrp/berkom/atlas-utilization/output/cms_datasets/
  singleelectron_prep_20261007/
    mappings/      singleelectron.txt (151), singlemuon.txt (152)
    tnp/           per-file Step B + D results, tnp_<era>_<index>.json
    prescale/      per-file Step C results, presc_<era>_<index>.json
```

Scratch, safe to delete:
`/storage/agrp/berkom/atlas-utilization/work/se_smoke_20261007/`.

Everything else under `output/` was opened read-only and is untouched.

## 4. Inputs

SingleElectron Run2016G+H: records **30529** (G, **71** files) and **30562**
(H, **80** files) = **151**, which matches the prep study's count
(VERIFIED BY RUNNING, `fetch_file_list`). SingleMuon: 30530 (G, 70) and
30563 (H, 82) = 152.

## 5. Findings already fixed by the smoke test (see REPORT.md for the full version)

* **Six** `HLT_Ele*WPTight*` paths exist in these files — `Ele25`,
  `Ele25_eta2p1`, `Ele27`, `Ele27_L1JetTauSeeded`, `Ele27_eta2p1`,
  `Ele32_eta2p1` — and bit 2's CMSSW pattern
  `hltEle*WPTight*TrackIsoFilter*` is wildcarded on threshold and eta, so
  all six can set it. Measured on one file: of 1,730,659 events holding a
  bit-2 object with `TrigObj_pt >= 27`, only **140** (0.008%) had
  `HLT_Ele27_WPTight_Gsf` read 0. So the `pT >= 27` requirement is
  sufficient in practice; the residual is quantified rather than assumed.
* The probe never shares the tag's trigger object (**0** cases), and the
  dR < 0.1 vs dR < 0.2 cone makes a difference of **2** probes out of
  55,680 — so neither choice drives the result.

## 6. How to resume

```bash
C=8670f8f5363344754416152dbdee8c828d091ce1
B=/storage/agrp/berkom/atlas-utilization/checkouts
git clone --no-checkout https://github.com/MatanBerko/atlas-utilization.git $B/${C:0:7}/repo
cd $B/${C:0:7}/repo && git fetch origin $C && git checkout --detach $C

R=$B/${C:0:7}/repo
O=/storage/agrp/berkom/atlas-utilization/output/cms_datasets/singleelectron_prep_20261007
L=/storage/agrp/berkom/atlas-utilization/logs/singleelectron_prep
cd $R
# qsub is at /opt/pbs/bin/qsub and is NOT on $PATH
/opt/pbs/bin/qsub -J 0-150 -N se_tnp \
  -o $L/tnp/t_^array_index^.out -e $L/tnp/t_^array_index^.err \
  -v REPO_DIR=$R,MAPPING_FILE=$O/mappings/singleelectron.txt,\
OUT_DIR=$O/tnp,SCRIPT=measure_singleelectron.py,TAG=tnp \
  studies/cms_datasets/singleelectron_prep/cluster/pbs_measure.sh

# aggregation runs on the analysis node with nice (scripts added after the
# arrays were submitted; see the branch for aggregate_*.py)
```

## 7. Rules observed

Pushed only to the fork; upstream fetched read-only and never written to;
no pull request anywhere; nothing merged into master; no existing cluster
output overwritten or deleted; no batch job writes to `$HOME`.
