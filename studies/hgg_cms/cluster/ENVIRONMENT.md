# Python environment: laptop vs. cluster, all H→γγ stages so far

Written 18 Sep 2026, after the bias-study cluster jobs' first real
submission failed instantly with `ModuleNotFoundError: No module named
'iminuit'` — the cluster conda env had never had it installed, because
`iminuit` is not in `docker/requirements.txt` (the file that originally
built that env) at all; it became a dependency only with the
signal-model task, well after that env was last set up. This document
exists so the next new dependency doesn't repeat that failure mode.

## Baseline: `docker/requirements.txt`

This is the file the cluster conda env (`/storage/agrp/berkom/atlas-utilization/envs/atlas-pipeline`)
was originally built from (unpinned except where shown):
```
awkward
atlasopenmagic==1.5.0
cernopendata-client==1.0.0
fsspec_xrootd==0.5.1
matplotlib
numpy
PyYAML
requests
scikit-learn
seaborn
tqdm
uproot==5.6.2
vector==1.6.2
xrootd==5.8.3
```
**`scipy` and `iminuit` are NOT in this file**, even though both are now
required (scipy since the Z→ee validation round's Crystal Ball/Breit-
Wigner fits; iminuit since the signal-model and background-model
tasks). Both had to be added to the cluster env by hand, after the fact,
rather than by updating this manifest and re-provisioning from it. This
is a real gap worth closing (updating `docker/requirements.txt` itself
is left for the group to decide — out of scope for what this note was
asked to do, which is document current state, not change the shared
pipeline's dependency manifest).

## Package versions, by stage

| package | needed since | laptop (this project's sessions, verified via `pip show`, 18 Sep 2026) | cluster (`atlas-pipeline` env) |
|---|---|---|---|
| Python | task 1 | 3.13.1 | UNVERIFIED — not directly checked from this side; the conda env name (`atlas-pipeline`) and its build history are the cluster team's, not queried here |
| numpy | task 1 | 2.2.4 | 2.4.6 (reported by the user after the iminuit install — numpy was NOT touched by that install) |
| uproot | task 1 | 5.6.2 (pinned, matches `docker/requirements.txt`) | UNVERIFIED, expected 5.6.2 per the pin — not directly re-checked this round |
| awkward | task 1 | 2.13.0 | UNVERIFIED — not pinned in `docker/requirements.txt`, not re-checked this round |
| matplotlib | signal-model task (fit-validation plots) | 3.10.1 | 3.11.1 (reported by the user) |
| scipy | Z→ee validation (Crystal Ball / Breit-Wigner fits); signal-model (DCB shape); background-model (families, F-test, toy fits) | 1.15.2 | 1.17.1 (reported by the user) |
| iminuit | signal-model task (weighted ML shape fits) onward; background-model (all background/bias fits) | 2.32.0 | 2.32.0 (installed by the user to match, 18 Sep 2026) |

**Laptop numbers above are freshly re-verified in this session** (`pip
show scipy numpy iminuit matplotlib uproot awkward`, 18 Sep 2026), not
carried over from memory of earlier sessions.

**Discrepancy flagged, not silently resolved**: an earlier message in
this conversation described the laptop/cluster scipy difference as
"1.18.1 vs 1.17.1". This session's own direct check of the laptop
environment used for every H→γγ script so far shows **scipy 1.15.2**,
not 1.18.1. Both numbers are reported here rather than picking one
silently — if the laptop actually has two different Python
environments (e.g. a separate system-wide install vs. the one these
sessions have been using), that is worth clarifying; if 1.18.1 was a
recollection rather than a fresh check, 1.15.2 (this session's direct
`pip show`) is the number to trust for reproducing this project's own
results. Either way, no code in this repo currently depends on a
specific scipy minor version — this is a documentation note, not a
known compatibility problem.

## What actually needs to match between laptop and cluster

Exact version equality is **not** required for any package here — none
of this project's code pins a specific numpy/scipy/matplotlib/iminuit
minor version, and nothing in the analysis (fit results, toy studies)
is expected to be numerically sensitive to, e.g., scipy 1.15 vs. 1.17.
What matters is that **every required module is importABLE at all** in
the env a job actually runs in — which is exactly what failed here
(iminuit missing entirely, not merely a version mismatch) and exactly
what `submit_bias_study.sh`'s new preflight import check now catches
before submission, rather than after 120 subjobs have already failed.

## Verifying the cluster env yourself

```bash
source /usr/wipp/conda/24.5.0/etc/profile.d/conda.sh
conda activate /storage/agrp/berkom/atlas-utilization/envs/atlas-pipeline
python -c "import numpy, scipy, matplotlib, iminuit, uproot, awkward; \
  print('numpy', numpy.__version__); print('scipy', scipy.__version__); \
  print('matplotlib', matplotlib.__version__); print('iminuit', iminuit.__version__); \
  print('uproot', uproot.__version__); print('awkward', awkward.__version__)"
```
(This is exactly what `submit_bias_study.sh`'s preflight now runs
automatically before every submission of the bias-study jobs.)
