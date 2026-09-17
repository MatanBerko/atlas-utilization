# Investigation: low bin near 165.25–165.75 GeV in both categories' sideband pulls

**Question** (raised against `background_model/results/plots/*_105_180_sideband_fits.png`'s
pull panels): in EBEB the 0.25 GeV bin `[165.25, 165.50)` pulls ≈ −4.5σ
against the lowest-NLL fitted background (expsum, order 2); in notEBEB
the pull ≈ −3σ was reported in the nearby region. Two independent
categories both showing a deficit near the same mass is, on its face,
unlikely by chance — is this a bug (binning artifact, run-specific data
issue, event misassignment) or a statistical fluctuation?

**Scope note**: this uses `data_sidebands.root` restricted to
160–170 GeV, deep inside the unblinded sideband (135–180 GeV) — no
blinding concern. Read-only investigation; **no code or result file was
changed as a result of this check** (no bug was found — see Finding
below).

## Method and findings

**1. Exact pull values, recomputed directly from the real fit** (not
re-quoting the earlier approximate description): EBEB's most extreme
bin is `[165.25, 165.50)`, obs=88, pred=130.6, **pull = −4.54**. This is
the single most extreme bin in EBEB's entire 220-bin sideband (next
most extreme bins are all above −2.6). notEBEB's most extreme bin near
there is the **adjacent, not the same**, bin: `[165.50, 165.75)`,
obs=97, pred=125.8, **pull = −2.93** — unremarkable on its own (1 bin
below −2.5 is well within the ~0.4 bins expected by chance across 220
bins). **The two categories' dips are in neighbouring 0.25 GeV bins,
not the same bin** — a first correction to the framing that raised this
check.

**2. Fine (0.05 GeV) binning, 164.5–167.0 GeV**: no sharp spike, cliff,
or single anomalous fine bin at any bin boundary — the deficit in EBEB
is a smooth, several-fine-bin-wide dip (fine bins in
165.25–165.50 read 15, 21, 22, 18, 13 against a local average of
~25–27), consistent with an ordinary downward fluctuation spread across
~0.25 GeV, not a discrete counting/binning bug.

**3. Bin-edge floating-point check**: events within 1×10⁻⁴ GeV of any
0.25-GeV-multiple bin edge in 160–170 GeV: 9/5362 (EBEB), 9/5139
(notEBEB) — close to the ~4–5 events expected by chance for a uniform
distribution at that edge tolerance (2×10⁻⁴/0.25 ≈ 0.08% of events), not
a large excess. No evidence of quantized/clustered mass values.

**4. Shifted grid (edges offset by +0.125 GeV)**: re-binning 160–170 GeV
on a grid offset by half a bin width, the deficit persists in EBEB (the
bin covering 165.375–165.625, closely straddling the original dip,
reads 95 against neighbours of ~130–150) — **the EBEB dip is not an
artifact of the specific 105.00-anchored bin grid**. notEBEB's dip is
comparatively binning-sensitive: on the shifted grid its lowest nearby
bin (165.625–165.875, n=106) is only mildly low against neighbours of
~110–150, less pronounced than the original −2.93 framing suggested.

**5. Neighbouring-bin excess check (event misassignment)**: EBEB's bin
immediately before the dip (`[165.00,165.25)`) reads pull=+1.35
(obs−pred=+16.5 events) — a real but much SMALLER excess than the
dip's deficit (obs−pred=−42.6 events). The magnitudes don't match, so
this is **not consistent with a simple one-bin migration** (events
shifted from the dip bin into a neighbour would need a matching-size
excess next door; there isn't one).

**6. Run-by-run check**: the EBEB dip bin's 88 events are drawn from
**56 different runs** (out of ~156 certified runs total), no single run
contributing more than 4 events (4.5% of the bin); each of the top
contributing runs' share of the dip bin is consistent with that run's
normal share of the surrounding 160–170 GeV window (e.g. run 279931:
4/88=4.5% of the dip vs. 3.11% of the broader window — a ~1.3-event
difference, well within Poisson noise). notEBEB's dip bin similarly
draws from 47 different runs with no outlier. **No evidence this
traces to specific runs or a run-conditions problem.**

**7. Look-elsewhere context**: across BOTH categories' full sidebands
(440 bins total), the number of bins expected at pull < −4.54 by pure
chance is 4.4×10⁻³ (EBEB's dip, taken alone within its own 220-bin
sideband, is the single most extreme bin there — genuinely a locally
rare fluctuation, roughly a 1-in-800 occurrence for the *most extreme
bin* in a 220-bin scan). The number expected at pull < −2.93 is 0.75
(notEBEB's dip is unremarkable). A naive Stouffer combination of the
two ORIGINAL pull values (4.54, 2.93 — despite being adjacent, not
identical, bins) gives Z≈5.28 (two-sided p≈1.3×10⁻⁷), but this
combination is not really meaningful here precisely because they are
different bins in different mass sub-windows with no shared cause
identified — this number is reported for completeness, not endorsed
as "the" significance of a single coincident feature.

## Conclusion

**No bug found.** The binning, floating-point, event-misassignment, and
run-by-run checks all came back clean. **EBEB's `[165.25,165.50)` bin
is a genuine, locally rare (~4.5σ, the most extreme of 220 sideband
bins in that category) downward statistical fluctuation — consistent
with a statistical fluctuation**, not a data-quality problem, once
look-elsewhere within its own sideband is accounted for (a bin this
extreme has roughly a 1-in-800 chance of being the single worst bin in
a 220-bin scan, which is unusual but not implausible, especially given
how many bins and checks this project has looked at in total across
three reports). **notEBEB's nearby dip is unremarkable on its own** and
sits in an adjacent, not identical, bin — the original "coincident
deficit in both categories" framing is weaker than it first appeared;
this is better described as one genuinely unusual EBEB bin plus one
ordinary notEBEB fluctuation nearby, not one shared feature.

**No action taken** — per this check's own instruction, nothing is
changed without a confirmed bug, and none was found. This is recorded
here for the record; the background-model results, fits, and reports
are unchanged by this investigation.
