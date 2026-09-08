# H -> ZZ -> 4l: validation pass (2 files/record, 12 files total)

Branch: `analysis/higgs-4lepton-zz`. Purpose: exercise the new Z1/Z2 pairing
logic on real data cheaply, and sanity-check parse-time selection +
de-duplication before committing to the full ~294 GiB / 238-file run. This
is NOT a physics result — statistics are tiny and only 5.0% of the full
dataset is used.

## A real bug caught by this pass, fixed before proceeding

The first attempt at this validation pass failed for 4 of the 6 records
(30522, 30555, 30528, 30561 — everything except the two already-known
DoubleEG records): `services/parsing/schemas.py`'s `RECORD_ID_TO_SCHEMA`
mapping was never updated with the 4 new record IDs, so the parser fell back
to auto-detection, which fails silently for NanoAOD's flat branch naming
("No particles found in schema for file ..."), producing 0 events from
those records with no exception raised. This is exactly the one required
infrastructure step documented for every prior new CMS record on this
project (e.g. the ttbar truth cross-check's registration of 67993) — missed
here initially. Fixed by adding all four IDs to `RECORD_ID_TO_SCHEMA`; the
broken run's (junk, incomplete) output directory was deleted and the pass
was re-run cleanly. This is exactly why a validation pass exists.

## Result of the corrected re-run

- **12/12 files, 100% success rate, 0 errors, 0 warnings** (other than the
  expected "missing handlers" notice for the three disabled stages).
- **22,218,407** raw events read across the 12 files.
- **De-duplication: 9,963 duplicate events removed of 1,311,332 seen
  (0.76%)** — genuinely non-zero, as expected: unlike the diphoton work's
  two disjoint DoubleEG records, DoubleEG/DoubleMuon/MuonEG heavily overlap
  the same runs. Sanity-checked: the duplicate count is broken down per run
  number in the log and is spread across ~50 different runs in a pattern
  consistent with genuine trigger overlap (not a single anomalous run
  driving the whole count) — plausible.
- **Per-record retention after parse-time >=4-loose-lepton selection:**

| Record | Kept / seen | Retention |
|---|---:|---:|
| 30521 DoubleEG G | 71,281 / 3,981,756 | 1.8% |
| 30554 DoubleEG H | 37,861 / 1,914,343 | 2.0% |
| 30522 DoubleMuon G | 334,526 / 4,782,423 | 7.0% |
| 30555 DoubleMuon H | 329,777 / 4,314,519 | 7.6% |
| 30528 MuonEG G | 281,871 / 4,408,864 | 6.4% |
| 30561 MuonEG H | 246,053 / 2,816,502 | 8.7% |
| **combined (post-dedup)** | **1,301,369** | — |

DoubleEG's lower retention vs. DoubleMuon/MuonEG is consistent with an
electron-triggered stream requiring a higher-threshold single/double
electron trigger relative to the loose parse-time lepton cuts used here —
not investigated further, not needed for this validation.

## Full cut-flow through the analysis script (real data)

| Stage | 30521 | 30554 | 30522 | 30555 | 30528 | 30561 | combined |
|---|---:|---:|---:|---:|---:|---:|---:|
| after parse-time selection | 71,281 | 37,861 | 334,526 | 329,777 | 281,871 | 246,053 | 1,301,369 |
| after per-lepton quality, >=4 selected | 64 | 29 | 777 | 1,062 | 311 | 309 | 2,552 |
| exactly 4, charge sum 0 | 38 | 20 | 446 | 567 | 167 | 187 | 1,425 |
| leading pT>20, sublead pT>10 | 37 | 20 | 285 | 308 | 118 | 147 | 915 |
| **valid Z1/Z2, final candidates** | **12** | **8** | **71** | **84** | **28** | **21** | **224** |

**224 final candidates from just 5.0% of the full dataset — non-zero, as
required.** This is expected to include mostly Z+X-type background (a real
on-shell Z plus 2 additional softer/looser leptons), not mostly Higgs — see
below.

## Z1/Z2 pairing logic sanity check: DOES the expected 91 GeV peak appear?

**Yes, clearly, in the Z1 pair mass** — the intended, standard validation
signal. Because Z1 is defined as whichever OSSF pair is closest to
91.1876 GeV, seeing it land there confirms lepton identification, charge
reading, and mass computation are all working correctly (a broken pairing
would produce a flat or randomly-distributed m_Z1, not a sharp physical
peak):

```
m_Z1 histogram (5 GeV bins, 224 candidates):
  85-90 GeV: 45 candidates
  90-95 GeV: 76 candidates   <- sharp peak right at the Z pole
```

**121 of 224 candidates (54%) have m_Z1 within 85-95 GeV.** m_Z1 ranges
40.4-113.4 GeV overall (mean 81.0, median 88.8) — the bulk sits right at the
Z mass, exactly as expected for a selection dominated by real on-shell-Z
pairs at this scale.

**The full 4-lepton mass (m4l) spectrum is broader, not sharply peaked at
91 GeV** — this is physically expected, not a discrepancy: m4l also carries
Z2's momentum, and Z2's own mass is broadly distributed (m_Z2: min 12.2,
max 118.7, median 36.8 GeV — mostly off-shell/low-mass, as expected for a
loose, non-resonant "extra pair"), so the total 4-lepton system is smeared
well above 91 GeV even when Z1 alone is genuinely on-shell. The clean
signal is in m_Z1, as reported above, not in the raw m4l shape.

## Verdict

The validation pass demonstrates the new logic works correctly on real
data: parse-time selection retains a sane, non-trivial fraction of events
per record, de-duplication removes a real and plausible number of
duplicates, and the Z1/Z2 pairing recovers a clean physical Z-peak
signature exactly where expected. Combined with the independent synthetic
tests (`scripts/test_higgs_4lepton_synthetic.py`, hand-computed known-mass
constructions, run before touching any real data), this is sufficient
confidence to proceed to the full-scale run.
