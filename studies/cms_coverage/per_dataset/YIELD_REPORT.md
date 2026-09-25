# Per-dataset BumpNet-yield measurement (topology-free, trigger-free)

Branch `survey/per-dataset-yield`, off `survey/cms-coverage` at
`e6f6367b798bd0bb27e0466794b0b7bb1bdca591`. Every number below is labeled
**VERIFIED BY RUNNING**, **FROM COMMITTED DATA**, or **UNVERIFIED /
ESTIMATED**, exactly as in the prior report.

**This measurement is deliberately different from the committed 316
DoubleMuon result** (`studies/cms_coverage/COVERAGE_REPORT.md`), in two
ways, applied to every dataset including DoubleMuon itself here:

1. **No trigger requirement**, anywhere. The committed 316 required
   `HLT_Mu17_TrkIsoVVL_Mu8_TrkIsoVVL_DZ`/`HLT_Mu17_TrkIsoVVL_TkMu8_TrkIsoVVL_DZ`
   to have fired; here, no HLT branch is read or checked at all, on any
   dataset.
2. **No topology requirement.** The committed 316 required exactly
   ">=2 muons AND >=1 light jet" per event. Here, an event is kept if it
   has **>=2 selected objects of ANY type** (muon, electron, jet, or
   b-jet, summed) — object *definitions* themselves (pT/η/ID/isolation
   thresholds, jet-lepton cleaning) are unchanged from
   `studies/m0m1j0_cms/RECIPE.md`, called via the same, unmodified,
   imported `selection.select_muons`/`select_electrons`/
   `select_and_split_jets`.

**Every number in this report is therefore an upper bound relative to
what a properly triggered, physics-motivated selection would yield** —
stated on every table below, not just here.

Golden-JSON (validated-runs) filtering is applied to data only, never to
MC, per task instruction.

## Records used (all re-verified live against the portal API just now)

| Dataset | Record ID | Portal-published events | Portal-published files |
|---|---|---|---|
| DoubleMuon | 30522 | 45,235,604 | 29 |
| SingleMuon | 30530 | 149,916,849 | 70 |
| DoubleEG | 30521 | 78,797,031 | 47 |
| SingleElectron | 30529 | 153,363,109 | 71 |
| MuonEG | 30528 | 33,854,612 | 29 |
| JetHT | 30525 | 120,688,407 | 70 |
| MET | 30526 | 26,974,131 | 17 |
| Tau | 30532 | 79,578,661 | 45 |
| MC ttbar (TTTo2L2Nu) | 67801 | 43,546,000 | 49 |
| MC Drell-Yan (DYJetsToLL_M-50) | 35671 | 82,448,537 | 61 |
| MC W+jets (WJetsToLNu) | 69747 | 80,958,227 | 68 |
| MC diboson (WW) | 72696 | 15,821,000 | 41 |
| MC single top (ST_t-channel_top) | 64759 | 63,073,000 | 86 |
| MC QCD multijet (Pt 170-300, mid-range of 11 bins) | 63176 | 29,758,000 | 38 |
| MC signal (GluGluHToGG) | 37350 | 540,000 | 3 |

Only **era Run2016G** is used for every data primary dataset here (file
index 0 of that record), for consistency with the pilot; QCD is
represented by its **170-300 GeV pT bin**, the 6th of 11 available bins
— a genuinely mid-range choice, not the lowest or highest.

## Pilot — VERIFIED BY RUNNING

Per the task's own instruction, the two most different datasets were run
first: JetHT (jet-rich, no lepton requirement) and SingleMuon (lepton-
gated, structurally closest to DoubleMuon).

| | JetHT | SingleMuon |
|---|---|---|
| file events (`n_read`) | 107,505 | 2,939,781 |
| wall time | 116.6 s | 1,048.9 s (17.5 min) |
| peak memory | 245 MB | 2.46 GB |
| output shard size | 1.66 MB | 11.0 MB |
| events after golden-JSON | 107,505 (no runs excluded) | 2,931,332 |
| events after >=2-object gate | 94,828 (88%) | 1,201,534 (41%) |
| (pattern×category) signatures written | 1,730 | 3,517 |
| largest single signature | 17,171 | 277,527 |

**Both comfortably inside the 60-minute/12 GB stop condition** — the
slower of the two (SingleMuon) used under 30% of the time budget and
about 20% of the memory budget. Proceeded directly to the remaining 13
datasets with no change to the approach.

Note the very different scale of "how much passes the >=2-object gate":
88% for JetHT (a jet-rich dataset easily clears a 2-object bar with no
lepton requirement at all) vs 41% for SingleMuon (already lepton-
selected, but many events still don't reach a second additional selected
object). This foreshadows why a topology-free, trigger-free measurement
is not simply "DoubleMuon's number, scaled" for every dataset.

