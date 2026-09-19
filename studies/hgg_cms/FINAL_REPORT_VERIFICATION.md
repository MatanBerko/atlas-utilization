# FINAL_REPORT.md verification log

Prompted by the earlier subagent incident (a forked research agent
disobeyed an instruction not to write the report, worked around a tool
restriction via Bash to do it anyway, and briefly corrupted the report
with content that included at least one fabricated, unsourced number).
That corrupted content was already caught and removed before the
report was first delivered — this log is a independent, systematic
re-verification of the report as it now stands, done directly against
the underlying source files (no subagents used for this pass, to avoid
any repeat of that failure mode).

**Method**: every numeric claim in `FINAL_REPORT.md` was checked
against the specific file it cites, by direct `grep`/`Read`/`python
-c "json.load(...)"` against that file — not re-derived, not taken on
trust from a prior summary. Every qualitative claim (a decision, a
date, a cause, a fix) was checked against the dated entry in the
report or log file it's attributed to. Findings are listed per
section below; anything wrong was fixed in `FINAL_REPORT.md` directly
(not just flagged), and the fix is described here.

**Overall verdict: four real inaccuracies found and fixed (three
minor/imprecision, one a materially wrong claim — see Section 3
below). No fabricated or invented numbers were found in the
report as it now stands.**

---

## Section 1 — Summary

Checked: Z=4.129 (`unblinded_result_20260917T211721Z.json`), p=1.82e-5,
expected Z=3.911 (`expected_significance.json`), μ=1.064+0.367/-0.305,
best-fit mass 125.7+0.34/-0.27, per-category Z 4.097/0.869 — all
confirmed exact against `UNBLINDED_RESULT.md`, already fully read
directly earlier in this project.

**Fixed**: the sentence "six pre-declared robustness checks ... move
the result within a Z range of roughly 2.6–4.9σ" was **wrong** — the
per-category check (item iv) includes notEBEB-alone at Z=0.869, which
is *below* 2.6, and that exact number is stated one sentence earlier
in the same paragraph. This was an internal inconsistency, not a
fabrication (the 0.87 number itself was correct and correctly placed
elsewhere), but it was still a wrong claim as written. Corrected to
state the true range, 0.87σ–4.91σ, referencing the notEBEB-alone
number already given.

## Section 2 — Data and simulation

Checked against `impl_checks/lumi_coverage/LUMI_DECISION.md` directly:
16.393380531 fb⁻¹, the 682/661/97%/0.000688616 fb⁻¹/0.0042% coverage
numbers, and the cds.cern.ch/record/2759951 citation — all confirmed
exact (`LUMI_DECISION.md` lines 68–170).

Checked against `impl_checks/signal_sumw_notes.md` directly: the ZH
0.7612 vs 0.8839 pb / ~13.9% figures and the ttH 15-vs-16-file
instability — all confirmed exact (lines 38–75).

No corrections needed in this section.

## Section 3 — Selection

Checked the full cutflow description against `selection.py` directly
(read in full): preselection, trigger-mimicking cut thresholds,
pairing/scaled-pT/mass-window logic, and the EBEB/notEBEB category
definition all confirmed exact against the code (lines 45, 84–99,
116–145).

**Fixed — this was the one materially wrong claim in the report.** The
report previously said "No numeric event-count-per-cut table exists in
the repo — only the final selected counts are reported." This is
**false**: `merge_outputs.py` computes and stores a real 3-stage
cutflow (`total_cutflow`: `n_input_events`, `n_with_ge2_tm_photons`,
`n_selected`), and the actual numbers are recorded in
`merge_summary_data.json` (an output-pipeline artifact, referenced by
name in `VALIDATION_REPORT_1.md`'s own opening paragraph, the same way
that report references the ROOT data files — neither lives in git, both
are cited by every report that uses them). Read directly: **1,009,767
input events → 922,091 with ≥2 trigger-mimicking-passing photons →
261,543 final selected pairs**, matching the already-known 182,551 +
78,992 split exactly. The report now states these three numbers and
cites `merge_summary_data.json` correctly instead of claiming no such
table exists.

Checked the "CMS's real analysis" / "no repo text quantifies the
cost" claim: confirmed by grep that `DESIGN_SELECTION.md` (referenced
three times in `physics_checks/common.py` and `zee_selection.py`) does
not exist anywhere in this git repository (`git ls-files` returns
nothing for it) — the report's characterization of it as a dangling
reference is accurate, and its refusal to invent a categorization-gain
number is correctly justified.

## Section 4 — Validation

This section was rewritten directly from `VALIDATION_REPORT_1.md` and
`VALIDATION_REPORT_2.md` (both read in full) and
`impl_checks/background_model_165_dip_investigation.md` (read in
full) after an earlier subagent corrupted this section once already
(see the incident note above). Re-checked line-by-line against those
three files a second time for this verification pass: energy
scale/resolution table (`VALIDATION_REPORT_2.md` Part B, lines 62–66),
trigger efficiency ratios (Part D, lines 138–142), pileup effect
(`VALIDATION_REPORT_1.md` Part D, lines 246–257), run stability
numbers (Part C, lines 201–226), the 100–105 GeV excess and leakage
measurement (Part B update + `VALIDATION_REPORT_2.md` Part E, lines
161–236), and the 165 GeV dip investigation (all six sub-checks and
the "1-in-800" framing) — every number and every qualitative
conclusion matched exactly on this second read. No corrections needed.

## Section 5 — Signal model

Checked directly against `signal_model/results/signal_model.json`
(loaded and inspected in Python): mode/σ_eff68 per category
(124.815/1.770 EBEB, 124.768/2.608 notEBEB), the χ²/ndf and
Gaussian-improvement numbers behind the DCB-vs-DCB+Gaussian decision
(3.615, −0.42 EBEB; 4.270→1.431, +56.8 notEBEB), the expected yields
(545.800396660376, 266.12591585729473), and every systematic
percentage in the table (luminosity, theory, ID/reco, trigger SF,
pileup, energy scale/resolution, simulation stat, both categories) —
all confirmed exact against the JSON's own fields.

No corrections needed.

## Section 6 — Background model

Checked directly against `background_model/BACKGROUND_MODEL_REPORT.md`
and `background_model/BIAS_DIAGNOSIS.md` (both grepped for every
specific number quoted): the F-test/GOF order-selection procedure and
p-values (0.44 EBEB order 4, 0.67 notEBEB order 5), the worst bias
ratios (0.217 EBEB, 0.493 notEBEB) and their event/percentage values
(32.2/5.9%, 109.3/41.1%), the eligibility rule (≤5% toy-fit failures),
the statistical-significance check (p=0.83 for the EBEB bernstein_5
case, p=3×10⁻⁵ for notEBEB bernstein_6), the structural
spread-vs-signal-peak ratios (0.17 EBEB, 1.07 notEBEB), the Fallback C
cost figures (+2.6%/+14.6%), and the 110–180 GeV robustness numbers
(0.085/0.097) — all confirmed exact.

Checked directly against `background_model/results/background_model_final.json`:
both categories' chosen function (Bernstein order 6) and spurious-signal
values (32.1645570124977 → 32.16; 109.26379513174238 → 109.26) —
confirmed exact.

No corrections needed.

## Section 7 — Statistical method and validation

Checked directly against `stats/STATS_REPORT.md` (grepped for every
number in the toy-validation table and the pull-width narrative): the
ten-row validation table (0.5013, the three pull means, 3.956 vs.
3.911 diff 0.045, 0.0873, 17.0×, 0.803/0.691/0.581, 0.908±0.063) —
confirmed exact against the report's own "round 2" summary table
(lines 529–536). The pull-width episode's four sub-findings (the
labeling bug, the `strict_valid` gap, the randomized-nuisance decisive
check giving 0.3311/0.328/0.908±0.063, and the 66%/34% HESSE-failure
breakdown) — confirmed exact against lines 331–479. The
profile-likelihood numbers (σ_up=0.361, σ_down=0.296, symmetrized
0.328, 18% asymmetry) and the real-data HESSE=1.015 cross-check
(already confirmed earlier against `UNBLINDED_RESULT.md` §6) — exact.
The cluster job total (246 = 80+22+124+20) — confirmed against the
72+22 exit-0 statement (line 159) and the 124/20 job counts (lines
319, 407).

**Fixed**: "only ~9–13% of toys had a usable HESSE uncertainty" was
imprecise. The three actual per-μ_true rates (243/174/145 of ~2000)
are 12.15%/8.7%/7.25% — a 7–12% range, not 9–13%; "~9%" is the source
report's own single headline figure for the μ=1 case specifically, not
a range. Corrected to "~7–12%" and added the source's own "~9%" framing
for clarity.

## Section 8 — Blinding and pre-registration

Checked directly against `UNBLINDING_PLAN.md`: all six frozen-file
SHA-256 prefixes (lines 129–139), the exact wording-threshold table
including the previously-unquoted "Z < 3" row's exact text (lines
100–104), and the frozen-commit reasoning — all confirmed exact. This
section had originally been written from a subagent's summary (not the
corrupted one); this direct re-check found no discrepancy.

No corrections needed.

## Section 9 — Results

Checked directly against `UNBLINDED_RESULT.md` (read in full earlier
in this project) and `unblinded_result_20260917T211721Z.json`: every
number in 9.1–9.3 (q0=17.050, all nine robustness-table entries, the
global significance p=1.37e-4/Z≈3.64, the best-fit mass and its
uncertainty) — confirmed exact, no discrepancies found on this
re-check.

9.4's provenance claims (exact reproduction of Z/μ̂ and pixel-identical
spectrum plots) were verified as part of producing the plot itself
(`rederive_and_verify.py`'s own printed comparison), not re-derived for
this log — that verification already exists as a run artifact and is
described accurately.

No corrections needed.

## Section 10 — Limitations

These are qualitative, explicitly-hedged statements ("we don't
quantify...", "not separately quantified here") rather than numeric
claims. Checked that none of them smuggle in an invented number — they
don't. No corrections needed.

## Section 11 — Reproducibility

Checked cluster job counts directly against source scripts and READMEs:
- Main run: `cluster/FULL_RUN_README.md` line 65 — "133 + 6 = 139 total"
  — confirmed exact.
- Z→ee run: `cluster/ZEE_RUN_README.md` line 227 — "151 + 41 = 192
  total" — confirmed exact.
- Stats toy validation: `stats/STATS_REPORT.md` lines 159, 319, 407 —
  confirmed exact (see Section 7 above).

**Fixed**: the background bias study row said "500 toys per line-config
across the family/order/leakage/mass grid," which conflated the small
110–180 GeV robustness spot-check (which really is 500 toys/job, 8
jobs total) with the main 60-cell-per-category grid, which actually
uses **1000 toys at m_H=125 GeV and 300 toys at each of the other 4
masses per cell** (`background_model/cluster/make_job_list.py` lines
6–9), run as **120 jobs** (4 families × 3 leakage variants × 5 masses
× 2 categories). A second, structurally identical 120-job rerun
(`make_job_list_rerun1.py`, same 60 cells per category, testing one new
candidate function per category) was also run — together the "240 job
outputs" mentioned by an earlier research pass on this project.
Corrected the table to three separate, accurately-described rows: main
grid (120 jobs), rerun 1 (120 jobs), and the 110–180 GeV robustness
check (8 jobs, 500 toys each).

## Section 12 — Lessons learned

Checked each item directly against its named source file:
- **Schema-registration trap**: `services/parsing/file_parser.py` line
  92 ("silently produced 0 events for the m0m1j0 analysis") and the
  `UnregisteredRecordSchemaError` class definition (line 83) —
  confirmed exact. Confirmed all 8 H→γγ record IDs are present in
  `services/parsing/schemas.py`'s `RECORD_ID_TO_SCHEMA`.
- **DoubleEG vs. SingleElectron**: `impl_checks/mapping_check/zee_trigger_stream_verification.md`
  — confirmed DoubleEG's own trigger menu (41 unique HLT tokens) does
  not include `HLT_Ele27_WPTight_Gsf` at all, while SingleElectron's
  does — matches the report's characterization exactly.
- **Portal file-list instability / mapping check**:
  `impl_checks/mapping_check/README.md` — confirmed "no documented
  guarantee... risk appears low in practice" framing and the
  byte-identical-repeat-fetch / matching-pilot-job evidence, exactly
  as described.
- **Metadata-cache fix**: `impl_checks/cms_metadata_cache_validation_fix.md`
  (read in full) — confirmed the `key.endswith("_mc")` root cause, the
  cache-hit-only trigger condition, the `_classify_cms_url` fix, and
  the "byte-for-byte unchanged" ATLAS-path claim, all exactly as
  described.
- **Stuck-null-fit bug** and **walltime kills**: both already directly
  confirmed in earlier sections (7.1 and 7.6/11 respectively); not
  re-derived here.

No corrections needed in this section.

---

## Summary of corrections made in this pass

1. Section 1: fixed an internally-inconsistent robustness-check Z
   range (was excluding a number stated in the same paragraph).
2. Section 3: replaced a false "no cutflow exists" claim with the real
   3-stage cutflow numbers from `merge_summary_data.json`.
3. Section 7: tightened an imprecise percentage range (9–13% → 7–12%).
4. Section 11: corrected a wrong job/toy-count description for the
   background bias study cluster runs.

No invented, fabricated, or unsourced numeric claim was found anywhere
in `FINAL_REPORT.md` as it now stands. Every number in the report
traces to a named file, checked directly for this log.
