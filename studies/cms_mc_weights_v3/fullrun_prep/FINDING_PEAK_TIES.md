# Part B finding (17 Oct 2026): 4 sparse ggH histograms change beyond ×0.99167

**DECISION (Matan, 17 Oct 2026): ACCEPT AND DOCUMENT as a known effect. No
code change; the peak-finding convention stays exactly as it is.** Recorded
in `XSEC_DECISIONS.md`, section "Known effects". (The task had stopped here on
17 Oct, as instructed, until this decision.) All numbers VERIFIED BY
RUNNING unless marked otherwise.

## What was compared

The 10 Oct pilot build 3a (`work/cms_mc_v3_pilot_20261011/build_default/`,
read-only) against the same build re-run on 17 Oct with the reviewed registry
(job `5234302`, checkout `61c307c`, same 98 per-file outputs, same options,
`work/mcprep_20261017/build_default/`). Tool: `compare_rebuild.py`; raw
result `plots/fullrun_prep/pilot_rebuild_comparison.json`.

Production does not read cross sections (checked in the code:
`run_dataset_on_file.py` has no reference to cross sections or the registry;
only the builder and two probes read it), so only the builder's normalisation
could change.

## Result

| file | histograms | expectation | result |
|---|---:|---|---|
| 67801 ttbar | 3,283 | identical | **bit-for-bit identical** (3,289,566 bins incl. flow) |
| 35669 DY | 2,498 | identical | **bit-for-bit identical** (2,502,996 bins) |
| 37728 ggH | 2,459 | every bin ×0.9916710047, every variance ×r² | **2,455 histograms as expected** (max deviation 2.9e-14 values, 2.3e-14 variances); **4 histograms differ** |
| summed SM | 3,289 | changes only by the ggH change | **as expected except the same 4 histograms** (elsewhere max deviation 7.0e-15 of the bin) |

Names, bin edges and titles are identical everywhere. Total ggH yield ratio
new/old = 0.99167180 (the 4 histograms move it off 0.99167100 in the 7th digit).

## The 4 histograms

| histogram | ggH entries old → new | ggH peak old → new [GeV] | ggH yield old → new | change as fraction of the summed-SM histogram |
|---|---|---|---|---:|
| `ROI_mass_e0j0j1_cat_2ex_0mx_6jx_0bx` | 7 → 3 | 370 → 610 | 0.00154 → 0.00066 | −1.9e-5 |
| `ROI_mass_e1j0j1j2_cat_2ex_0mx_6jx_0bx` | 2 → 4 | 380 → 660 | 0.00044 → 0.00082 | +3.8e-5 |
| `ROI_mass_e1j1b0_cat_2ex_0mx_2jx_2bx` | 4 → 5 | 240 → 270 | 0.00089 → 0.00106 | +1.2e-7 |
| `ROI_mass_j0j1j2j3_cat_2ex_0mx_6jx_0bx` | 4 → 6 | 520 → 410 | 0.00082 → 0.00125 | +1.2e-5 |

The summed-SM entry counts move by the same amounts (448→444, 114→116,
36,325→36,326, 306→308).

## Why (diagnosed by running, `diagnose_peak_flips.py`, `evidence/peak_flips_20261017.json`)

* Masses are identical old vs new, and every per-entry weight equals old × r
  to 2.2e-16. The inputs to post-processing are exactly what they should be.
* In each of the 4 histograms (12–13 ggH entries) **every bin near the top
  holds a single event, and those events all carry essentially the same
  weight** (≈2.2e-4). Their weighted bin contents differ only by **1–8 units
  of float64 round-off** (≈1e-15 relative).
* The peak finder takes "the rightmost bin whose weighted content equals the
  maximum" — an exact-equality test. Which single-event bin "wins" is
  therefore decided by round-off, and multiplying every weight by r rounds
  differently. Example (`j0j1j2j3`): old, the bins at 410 and 520 GeV tie
  exactly, so the rightmost (520) wins; new, 520 is 8 round-off units lower,
  so 410 wins and 2 more entries survive "keep masses ≥ peak".
* This is the same sparse-spectrum tie problem the pilot's Part 3b documented
  for the unweighted rule, now appearing among near-equal weights. With the
  unweighted rule these 4 peaks would sit at 570–1,020 GeV
  (`peak_unweighted` in the evidence).

## Why it matters (and how much)

* Physically negligible here: at most 4×10⁻⁵ of any summed-SM histogram, in
  4 of 3,289.
* But it means **the delivered histograms are not a smooth function of the
  cross sections**: any normalisation change (a registry value, Σw from a
  different file set, e.g. reused vs re-run pilot files) can move the peak in
  sparse histograms by hundreds of GeV and change which entries are kept.
  It will also happen in the full run between any two builds whose weights
  differ in the last digit.

## Options for Matan (nothing was changed)

1. **Accept as is.** Document it as a known property of weighted peak finding
   on sparse spectra (round-off decides ties). No code change; the full run
   proceeds. Simplest; the effect is tiny where statistics exist.
2. **Make the tie test tolerant** (e.g. treat bins within a relative 1e-9 of
   the maximum as tied, then take the rightmost). Stable under any
   normalisation change; a change to the peak-finding convention, so it
   needs your and Yuval's OK, and the same rule would have to be considered
   for the data side for consistency.
3. **Find the peak on raw counts for sparse histograms only** (below some
   entry count). Also a convention change; mixes two rules.
4. **Ask Yuval** which behaviour PR #35 intends for ties before choosing.

Recommendation: 1 for the full run now, with 2/4 raised with Yuval as a
follow-up — the effect is ≤4×10⁻⁵ of the summed histograms and confined to
categories with a handful of MC events, which carry no statistical weight.
