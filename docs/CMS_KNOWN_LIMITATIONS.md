# CMS pipeline — known limitations and future requirements

## Current scope: SingleElectron-only CMS data

The CMS configuration (`config.cms_records_master.yaml`) is **currently and
intentionally scoped to SingleElectron data only** — CERN Open Data records
**30529** (`/SingleElectron/Run2016G-UL2016_MiniAODv2_NanoAODv9-v1/NANOAOD`)
and **30562** (`/SingleElectron/Run2016H-...`).

This is a **temporary decision for the current phase**, not a permanent one.

### Why the SingleMuon records are excluded

The other two records originally listed —
**30530** (`/SingleMuon/Run2016G-...`) and
**30563** (`/SingleMuon/Run2016H-...`) — are **SingleMuon** primary datasets:
events were recorded because a muon fired the trigger, with no electron
requirement.

The pipeline's event selection applies a hard "at least one electron"
requirement (`parsing_task_config.particle_counts.electrons.min = 1`, with
pt > 25 GeV, |eta| < 2.47) **identically to every record**, with no awareness
of which trigger stream an event came from. Measured on real data, that cut:

- keeps ~85–89% of the SingleElectron records, but
- **discards ~97% of the SingleMuon records**, and the ~3% that survive are a
  biased electron+muon subsample rather than representative muon-triggered
  events.

Including the SingleMuon records under the current selection therefore throws
away almost all of that data and biases what remains. They are left out until
the pipeline can select them correctly.

## Required before final delivery

Per supervisor **Maryna**, the **final delivery must use all available CMS
data**, not SingleElectron only. This is a **confirmed project requirement**,
not an optional improvement.

Bringing the SingleMuon records back in requires, at minimum:

1. **Per-trigger-stream event selection** — apply an electron requirement to
   the SingleElectron records and a muon requirement to the SingleMuon
   records, instead of one blanket electron requirement for all four. The
   selection stage currently takes a single `particle_counts` block and
   applies it to every record with no branch on record / trigger-stream
   origin; that origin (which the parser does encode in the output filenames)
   would need to be threaded into the selection.

2. **De-duplication of events that fired both triggers** — the SingleElectron
   and SingleMuon datasets of the same run era share identical run-number
   ranges, so an event that fired both an electron and a muon trigger appears
   in *both* datasets. Without run/event-number-based de-duplication, combining
   all four records double-counts those events (~2% of events).

3. Then re-add records 30530 and 30563 to
   `config.cms_records_master.yaml`.

## Related, separately tracked

- **Histogram bin width** is fixed at 10 GeV rather than resolution-based, so
  some narrow-mass channels can never reach BumpNet's ">30 bins" requirement.
  Deliberately parked for a later task.
- **Object overlap** — in CMS NanoAOD an electron is normally also
  reconstructed as a photon and often as a jet (same calorimeter cluster).
  With no overlap removal (delta-R cleaning between the electron, photon and
  jet collections), 2-body combinations such as electron+photon or
  electron+jet are dominated by ~0 GeV "self-pairs", producing spike-shaped
  histograms. This is an upstream reconstruction/selection gap, not a
  post-processing bug. Noted for a future decision on adding overlap removal.
