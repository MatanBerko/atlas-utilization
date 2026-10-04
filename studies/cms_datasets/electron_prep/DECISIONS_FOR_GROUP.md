# Electron datasets: four decisions for the group

For Shikma and Maryna. Everything below is **measured**, not assumed; the file
or plot behind each number is named. Nothing has been implemented and no
delivered file has changed — this is preparation only.

Short version: **DoubleEG and MuonEG are ready and cheap. SingleElectron works
too, but its trigger is much less efficient for our offline electron definition
than we might have assumed, and no pT threshold fixes that.**

---

## (a) SingleElectron: what pT should we require of the matched electron?

**Plot:** `plots/step2_ele27_turnon.png`, `plots/step2_threshold_choice.png`
**Evidence:** `evidence/step2_ele27_turnon.json`, `evidence/step2_ele27_decomposition.json`

Measured on 62,968 probe electrons in SingleMuon data, using a muon trigger as
the tag so the measurement is independent of the electron trigger.

The result is not what the brief anticipated, so please read this one carefully.

**The matching requirement itself is nearly free.** Once `HLT_Ele27_WPTight_Gsf`
has fired, the probability that our offline electron is matched to its trigger
object is **0.977 at 27-29 GeV, 0.987 at 29-31, and 1.000 above 35 GeV**. That
is the only part a "matched" delivery actually controls, and it is excellent.

**The trigger's own efficiency is the slow part.** The probability that
Ele27 fires at all, for an electron passing our offline definition, is 0.286 at
27-29 GeV, 0.568 at 29-31, 0.723 at 33-35, and still only 0.932 at 120-200 GeV.
It reaches its 50-200 GeV plateau (0.863 barrel, 0.688 endcap) only around
**60 GeV**. The reason is that the HLT "WPTight" identification is tighter than
the offline "Medium" identification we select on, plus the Level-1 seed has its
own turn-on. **No choice of pT threshold removes this** — it is a property of
the trigger relative to our object definition.

So the brief's rule ("lowest threshold where efficiency is >= 95% of plateau in
both barrel and endcap") **selects no candidate in the 25-35 GeV range**; it
would select roughly 60 GeV, which is not a sensible place to be.

| threshold | efficiency / plateau, barrel | efficiency / plateau, endcap | SingleElectron events lost |
|---:|---:|---:|---:|
| 25 GeV | 0.025 | 0.012 | 0.00% |
| **27 GeV** | **0.334** | **0.140** | **1.07%** |
| 28 GeV | 0.501 | 0.274 | 3.15% |
| 30 GeV | 0.669 | 0.326 | 9.81% |
| 32 GeV | 0.743 | 0.540 | 17.97% |
| 35 GeV | 0.805 | 0.634 | 31.64% |

**Proposed default: 27 GeV** — but this is the group's call, and the reasoning
matters more than the number:

* it is the trigger's own nominal threshold, so it is the minimal
  self-consistent requirement;
* it costs only **1.07%** of the events this dataset would accept;
* above it the *matching* adds essentially no further inefficiency (>= 0.977);
* raising it buys efficiency that is **not flat anyway** — 35 GeV still sits at
  0.805 / 0.634 of plateau — while discarding a third of the sample.

The counter-argument, if anyone wants to make it: BumpNet looks for *localised*
bumps in mass spectra, and a smoothly varying efficiency is much less dangerous
than a sharp one. The steepest part of the curve is 25-31 GeV. If the group
wants to be clear of it, **30 GeV** (loses 9.8%) is the defensible alternative.

**What we cannot do:** recover the plateau. That would need a looser offline
electron definition or a different trigger, both out of scope here.

## (b) Which of the three datasets should we include?

**Plot:** `plots/step3_leg_matching.png` **Evidence:** `evidence/step3_leg_matching.json`,
`evidence/step5_yield.json`

| dataset | files | matching quality | verdict |
|---|---:|---|---|
| **DoubleEG** | 133 | electrons match the dielectron bit at **98.5%** overall, **>= 99.6%** (barrel) above 30 GeV | **include** |
| **MuonEG** | 48 | electrons match the cross-trigger bit at **99.6%**, flat from 25 GeV | **include** |
| **SingleElectron** | 151 | electrons match the WPTight bit at **97.4%**; the trigger efficiency issue in (a) applies | **include, with (a) decided** |

**One caveat on DoubleEG**, which is a genuine finding: its matching is *not*
flat at the bottom of our pT range. In the first bin (25-26 GeV) only **80.4%**
of barrel and **57.5%** of endcap electrons match, rising to >= 99.6% / 96.4%
above 30 GeV. This is the residual turn-on of the 23 GeV leg. If the group
wants DoubleEG to be as clean as the muon datasets, the natural option is an
extra requirement that the matched electrons be above ~30 GeV — at the cost of
the 25-30 GeV electrons. MuonEG shows **no** such turn-on (99.8% / 99.3% in the
very first bin), so this is a DoubleEG-specific question.

**Expected gain.** Pooling the existing *generic* DoubleEG + MuonEG outputs
through the delivery's own post-processing (`evidence/step5_yield.json`):

| | categories | histograms |
|---|---:|---:|
| electron datasets (DoubleEG + MuonEG, generic) at > 25 bins | 112 | 1,435 |
| our delivered rare4 muon file | 55 | 960 |
| **categories the electron datasets reach that the muon file does not** | **64** | **789 histograms live in them** |

So the electron datasets roughly **double the number of final-state categories**
— which is the point of adding them, since a muon-triggered delivery cannot
reach any category without a muon.

**This is an UNMATCHED APPROXIMATE PROJECTION, not a result.** It uses the older
*generic* (unmatched) outputs; SingleElectron is not in it at all (no generic
SingleElectron production exists to read); and a real matched production accepts
**fewer** events, because trigger matching only ever removes events. Treat 64 /
789 as an **upper bound** on the category reach and only a rough indication of
the histogram count.

## (c) Electron-muon overlap: do we remove close electrons?

**Plot:** `plots/step4_emu_overlap.png` **Evidence:** `evidence/step4_emu_overlap.json`

Measured, counting only — **nothing was removed anywhere**.

| | MuonEG | SingleElectron |
|---|---:|---:|
| events with >= 1 electron and >= 1 muon | 55,305 | 13,432 |
| dR(e, mu) < 0.02 | 0.264% of those | 0.238% |
| dR(e, mu) < 0.05 | **0.561%** | 0.529% |
| dR(e, mu) < 0.1 | 0.790% | 0.864% |

The earlier MuonEG diagnostic reported **0.54%** below dR < 0.05; this
independent measurement gives **0.561%**, so that number is **re-verified**.

**Impact if we did remove them** (this is the number that matters):

| cut | MuonEG events changing final-state category | as a fraction of all triggered MuonEG events |
|---|---:|---:|
| remove e within dR < 0.02 of a muon | 146 | **0.0041%** |
| remove e within dR < 0.05 | 310 | **0.0087%** |
| remove e within dR < 0.1 | 437 | **0.0123%** |

For SingleElectron the effect is smaller still (116 events, 0.0006%, at dR < 0.1).

**Options, with consequences — no recommendation, because this is a physics
convention question, not a measurement question:**

1. **Keep as is.** Consistent with every delivered muon file, which applies no
   electron-muon overlap removal. Costs nothing. A handful of events have an
   electron that is probably a mis-reconstruction of a muon.
2. **Remove electrons within dR < 0.05 of a selected muon.** Affects **0.0087%**
   of triggered MuonEG events. Physically cleaner, but it is a change to the
   object definition and would, for consistency, have to be applied to the
   already-delivered muon datasets too — which means rebuilding them.

The measured impact is small enough that option 1 costs almost nothing in
physics terms and option 2 costs a re-delivery. That asymmetry is the decision.

## (d) Dataset priority order

**Proposed default:** `DoubleMuon > SingleMuon > DoubleEG > MuonEG > SingleElectron`

The three electron datasets sit **below** SingleMuon, so **no delivered muon
file changes**. The existing generic `VETO_ORDER` in the code is different
(DoubleMuon > DoubleEG > MuonEG > SingleMuon > SingleElectron); that difference
is deliberate and documented.

The point to be comfortable with: **the set of collisions kept does not depend
on the order at all.** Only the label saying which dataset an event is counted
under changes. The one exception is the known ~4-per-million difference between
independently produced copies of the same collision. The closure test designed
in the specification checks exactly this, by re-running the attribution under
both orders and requiring the total to be identical.

---

## What to decide

1. **SingleElectron matched-electron pT**: 27 GeV (proposed), or 30 GeV if you
   want to be clear of the steep region. Anything higher costs a lot for
   efficiency that is still not flat.
2. **DoubleEG below 30 GeV**: accept the 80%/58% matching in the first bin, or
   add a ~30 GeV requirement on the matched electrons.
3. **Electron-muon overlap**: keep as is (consistent with the muon delivery), or
   remove and accept re-delivering the muon datasets.
4. **Priority order**: confirm the default above.

Once these are settled the production is roughly **9 to 27 core-hours** over
**332 files** (`evidence/step5_cost.json`) — about an hour of wall-clock on the
cluster.
