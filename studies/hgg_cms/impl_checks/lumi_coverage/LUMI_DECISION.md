# Which integrated luminosity to use for Run2016G+H DoubleEG — decision (implementation task 3, Part A)

This corrects implementation task 2's luminosity-coverage conclusion.
Task 2 estimated the luminosity carried by certified-but-file-missing
lumisections by **assuming luminosity is spread evenly across a run's
lumisections** (no per-section table was used, by design, to stay within
that task's scope). That assumption turns out to be wrong in a specific,
diagnosable way: the missing sections are not a random, luminosity-typical
subset of a run — they are specifically the sections with **essentially
zero real luminosity in them**. Using the actual per-section table removes
the approximation entirely.

## A.1 — The per-lumisection table

**Source**: CERN Open Data record
[1059](https://opendata.cern.ch/record/1059), file
[`pp_2016lumibyls.csv`](https://opendata.cern.ch/record/1059/files/pp_2016lumibyls.csv)
(21,137,550 bytes — matches the portal's own listed size exactly).

**How it says it was produced** — quoted directly from the file's own
header line:

```
#Brilcalc command:  brilcalc lumi -c web --byls -i /mnt/vol/cert.txt -u /fb --normtag /mnt/vol/normtag_PHYSICS.json --output-style csv
#Data tag : 23v1 , Norm tag: None
```

i.e. CMS's official `brilcalc` luminosity tool, run in "by lumisection"
mode (`--byls`), restricted to the certified-run list (`cert.txt` = the
golden JSON, record 14220), using the official 2016 normtag
(`normtag_PHYSICS_pp_2016.json`, also on record 1059). The record's own
abstract states this file is provided "for luminosity calculation, a
detailed list of luminosity by lumi section."

**Columns** (header row): `run:fill, ls, time, beamstatus, E(GeV),
delivered(/fb), recorded(/fb), avgpu, source`.

- **Recorded luminosity column**: `recorded(/fb)`, the 7th column —
  already in inverse femtobarns (no unit conversion needed). This is the
  actual, delivered-and-recorded (not merely delivered) luminosity for
  that one lumisection.
- **Lumisection encoding**: the `run:fill` field's first number is the run
  number; the `ls` field is formatted `cmsls:pixells` (e.g. `1:1`), and in
  every row checked the two numbers agree — the number before the colon is
  the lumisection number, matching the golden JSON's numbering.
- The file's own footer independently confirms it is exhaustive over the
  certified list:
  ```
  #Summary:
  #nfill,nrun,nls,ncms,totdelivered(/fb),totrecorded(/fb)
  #144,393,234231,233406,38.184814444,36.313753344
  #Check JSON:
  #(run,ls) in json but not in results: []
  ```
  `nrun=393`, `nls=234231` match the golden JSON's own totals (all of 2016,
  B–H) exactly, and brilcalc's own self-check lists **zero** certified
  `(run, ls)` pairs missing from its table.

## A.2 — Sanity check: summed recorded luminosity vs. the official per-era totals

Independently (not just trusting brilcalc's own footer): summed the
`recorded(/fb)` column over every certified section within each era's run
range (`studies/hgg_cms/impl_checks/lumi_coverage/sum_by_era.py`, run
locally against the downloaded CSV).

| Era | Certified sections | Summed from `pp_2016lumibyls.csv` (/fb) | Official (`Run2016{G,H}lumi.txt`) (/fb) | Difference |
|---|---|---|---|---|
| Run2016G | 43,014 | 7.653261218 | 7.653261227 | −0.0000001% |
| Run2016H | 47,793 | 8.740119376 | 8.740119304 | +0.0000001% |

Also confirmed directly (not just via the file's own footer): **every**
one of the 234,231 certified `(run, ls)` pairs (all 2016 eras) appears as
exactly one row in `pp_2016lumibyls.csv`, and every row in the file is a
certified pair — a perfect 1:1 correspondence, zero missing either
direction.

**Agreement is far inside 0.5%** (differences are 9th-decimal
floating-point summation noise) — no normtag/unit/run-boundary
investigation was needed. `pp_2016lumibyls.csv` is confirmed as a reliable
per-section ground truth.

## A.3 — Exact luminosity of the 682 sections missing from our files

Recomputed the missing-section set using task 2's exact method (re-read
the `LuminosityBlocks` tree of all 133 DoubleEG files — 47 for Run2016G,
record 30521; 86 for Run2016H, record 30554 — all 133 opened successfully,
0 failures; `recompute_missing_sections.py`): **332 missing in Run2016G,
350 in Run2016H, 682 total** — identical counts to task 2.

This time, instead of the even-spread approximation, each missing
section's **exact** recorded luminosity was looked up directly in
`pp_2016lumibyls.csv` (`characterize_missing_sections.py`):

| Era | Missing sections | Task 2's even-spread **estimate** (/fb) | This task's **exact** sum (/fb) | Ratio (estimate / exact) |
|---|---|---|---|---|
| Run2016G | 332 | 0.0598917 | **0.000452878** | ≈132× too high |
| Run2016H | 350 | 0.0680646 | **0.000235738** | ≈289× too high |
| **Total** | 682 | 0.1279564 | **0.000688616** | ≈186× too high |

Task 2's estimate overstated the missing luminosity by two to three orders
of magnitude, because it assumed each run's luminosity is spread evenly
across its certified sections. It is not: the sections that are actually
missing from our files are specifically the ones that carried almost no
luminosity in the first place (Section A.4).

## A.4 — What the missing sections actually are

Full detail per section (position in run, contiguous-block membership,
luminosity vs. that run's own median section) is in
`lumi_decision_data.json`'s `by_era_detailed`; summary:

- **661 of the 682 missing sections (97%) have EXACTLY 0.0 recorded
  luminosity** in the official per-section table — not "small," genuinely
  zero. The remaining 21 sections are small but nonzero (largest single
  value: 0.000226 fb⁻¹, in one Run2016H section).
- **99.4% (Run2016G) / 99.1% (Run2016H)** of the missing sections have
  recorded luminosity below **1%** of their own run's median certified-section
  luminosity — they are outliers within their run, not typical sections
  that merely happened to have no DoubleEG events.
- **Position**: mostly interior to a run (225/332 in G, 198/350 in H) with
  a substantial share in a run's last 3 certified sections (105/332 G,
  146/350 H) — consistent with end-of-fill ramp-down/declining-luminosity
  periods; very few (2 in G, 6 in H) are in a run's first 3 sections.
- **Contiguity**: missing sections cluster into contiguous runs of
  consecutive lumisection numbers (block lengths from 1 up to 16 seen in
  both eras) — consistent with a single sustained near-zero-luminosity
  interval within a run (e.g. a brief technical stop or declining-beam
  period), not scattered independent single-section glitches.
- **Concentration**: almost all of the (tiny) nonzero missing luminosity
  is in just two runs — 278969 (Run2016G, 0.000452 fb⁻¹) and 283416
  (Run2016H, 0.000232 fb⁻¹) — together 99.3% of the total 0.000689 fb⁻¹
  missing. Every other one of the 103 affected runs contributes a
  nanofb⁻¹-level sliver or exactly zero.

The plot `missing_sections_luminosity_hist.png` shows this directly: 97%
of missing sections fall in the "exactly 0" bracket, while 96% of *all*
certified sections fall in the normal [10⁻⁴, 10⁻³) fb⁻¹ bracket — the
missing sections are a completely different population from a typical
certified section, not a representative sample of them.

**Conclusion on the physical picture**: these are certified-good
lumisections in which the accelerator delivered essentially no luminosity
(technical stops, ramp-down, etc.) — not lumisections with real physics
data that our specific dataset happened to miss. Task 2's characterization
("sparse per-dataset trigger statistics — DoubleEG had bad luck") is
**superseded**: the exact per-section data shows these sections had (near)
zero luminosity for *any* dataset, which is a more complete and better-supported
explanation than task 2's trigger-statistics framing.

## A.5 — Decision (pre-set rule, applied exactly)

- Total exact missing luminosity: **0.000688616 fb⁻¹** (≈0.69 pb⁻¹).
- Total official recorded luminosity (Run2016G+H): **16.393380531 fb⁻¹**.
- Missing fraction: **0.0042%** — **below the pre-set 0.1% threshold.**

**Decision: missing sections have negligible luminosity. USE the official
luminosity.**

| Era | Luminosity to use (/fb) |
|---|---|
| Run2016G | 7.653261227 |
| Run2016H | 8.740119304 |
| **Total** | **16.393380531** |

**CMS's quoted uncertainty on this 2016 luminosity measurement: 1.2%**
(relative), stated on
[record 1059](https://opendata.cern.ch/record/1059)'s abstract, citing
["Precision luminosity measurement in proton-proton collisions at
√s = 13 TeV in 2015 and 2016 at
CMS"](https://cds.cern.ch/record/2759951). The 0.0042% missing-section
correction is roughly 300× smaller than this uncertainty — using the
official value rather than a corrected one changes nothing within the
measurement's own precision.

## Files in this directory (Part A)

- `sum_by_era.py`, `sum_by_era_results.json` — Part A.2's sanity check.
  `pp_2016lumibyls.csv` itself (21 MB) is a large intermediate download,
  not committed to the repo per this task's "no large intermediate files"
  instruction — re-download it from the URL cited in Part A.1 and pass its
  path to `sum_by_era.py` to reproduce.
- `recompute_missing_sections.py`, `missing_sections_exact.json` — Part
  A.3's exact missing-section set (re-derived from the real files, task
  2's method).
- `characterize_missing_sections.py`, `lumi_decision_data.json`,
  `missing_sections_luminosity_hist.png` — Part A.4's characterization and
  A.5's decision computation.
- This file.
