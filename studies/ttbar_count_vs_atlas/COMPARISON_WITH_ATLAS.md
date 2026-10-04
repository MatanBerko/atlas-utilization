# CMS ttbar vs ATLAS ttbar - comparison

**Date: 2026-10-04.**

## Summary in plain language

There are two separate questions here. One is **blocked**, one is **answered**.

**Blocked: how our CMS ttbar histograms compare with Maryna's ATLAS ttbar
histograms, final state by final state.** This needs her ATLAS ROOT file, and
that file still cannot be read. The folder it sits in, `histograms/`, is set to
owner-only. Every folder above it is open; this one is not. Nothing else is
missing: the comparison tool is written, self-tested, and needs only the file.
The precise one-line fix is in section 2 below.

**Answered, without the ROOT file: why Maryna's and Ariel's own ATLAS runs give
different counts.** Her run logs and configuration files *are* readable, and
they settle most of it. In short:

1. **Switching the lepton trigger on is a small effect.** With everything else
   held fixed, turning the trigger on changed her histogram total from 2,684 to
   2,651 - about 1% fewer. A second, independent pair of runs from 21 September
   shows the same small shift (3,495 to 3,371). So the trigger is not where the
   big differences come from.
2. **Switching overlap removal on is a large effect.** With everything else held
   fixed, turning overlap removal on changed the total from 3,371 to 2,867 -
   about 15% fewer. That is roughly twelve times the size of the trigger effect.
   This is the same direction we see in our own CMS data, where removing jets
   that sit close to a selected lepton also lowers the count.
3. **There is a third difference nobody has mentioned, and it matters:
   photons and taus.** The two runs from 3 October do not restrict photons or
   taus at all, while every other run requires exactly zero of each. In her code
   the photon and tau counts are part of the final-state label, so these two
   runs can produce final states that the other runs simply cannot. This means
   the 135-final-state run and the overlap-removal run are **not** a fair
   one-change-at-a-time comparison - they differ in two ways, not one.
4. **One naming caution.** The two 3 October runs are called "UnlimetedJets",
   but their own saved configuration still caps jets at 4, exactly like every
   other run. Within what the saved files show, no run had an unlimited number
   of jets. This is worth checking with Maryna, because the name and the saved
   setting disagree.
5. **The rule PR #31 adds is genuinely absent from her code.** Her code limits
   the number of object *types* to 4 and each type's count to 4, but it has no
   rule on the *sum*. So an event with 4 electrons, 4 muons, 4 jets and 4 b-jets
   (16 objects) is accepted by her code and rejected by PR #31. **How many of her
   final states that rule would remove cannot be measured without the ROOT
   file** - that is the one piece of this request that stays blocked.

One caveat that matters for reading the table below: the final-state counts of
135, 132 and 129 are counted *after* the ">= 25 filled bins and >= 100 entries"
cuts, which are applied inside the ROOT file. The totals I can read from her logs
are from *before* any bin cut. They are different levels and need not move in the
same direction - and in fact they do not: the overlap-removal run has *more*
total histograms than the trigger-on run (2,867 vs 2,651) while reportedly having
*fewer* final states (129 vs 132). Resolving that needs the ROOT files.

## 1. Status of each deliverable

| asked for | status |
|---|---|
| Step 2 - reproduce 2,684 / 2,161 / 2,146 and 135 FS | **BLOCKED** (ROOT file unreadable). 2,684 is corroborated by her log; the rest are inside the file |
| Step 3 - four-level FS and histogram table, her file + our 3 variants | **BLOCKED** for the ATLAS column |
| Step 4 - FS-by-FS comparison | **BLOCKED** |
| Addition item 2 - ATLAS FS that PR #31's `e + mu + b <= 4` rule would reject | **BLOCKED** (needs the FS list from the ROOT file) |
| Step 5 - PNG plots | **BLOCKED** (all four plots need ATLAS contents) |
| Addition item 1 - name the blocking directory and its permissions | **DONE**, section 2 |
| Addition item 3 - survey her other ttbar runs | **DONE**, section 3 |
| Addition item 4 - "Why the ATLAS runs differ" | **DONE**, section 4 |

## 2. What exactly blocks access

Re-checked 2026-10-04 (**RAN**: `stat`, `getfacl`, `find` over ssh as `berkom`,
groups `watlas`).

The blocking item is **one directory**:

```
/storage/agrp/marybo/DDP/BumpNet4AtlasOpenData/Test_master_atlas-utilization/data/atlas_mc_UnlimetedJets_test_ttbar_mc_20261003_210612/histograms
```

| | value |
|---|---|
| permissions | **`drwx------`** (owner-only) |
| owner:group | `marybo:watlas` |
| `getfacl` | `group::---`, `other::---`, no ACL entries - plain mode bits |
| its own mtime | 2026-10-03 21:29 - i.e. **not modified since**, so it was not re-opened |

Every directory above it is `drwxr-xr-x` and fine. Because this one has no `x`
bit for group or other, it cannot be entered, so the files inside cannot be read
or even listed:

* `atlas_opendata_bumpnet.root` - the main file
* `atlas_btag_ttbar_test_bumpnet_nopostproc.root` - the pre-post-processing file

The sample list is blocked separately, at **file** level, in an otherwise open
directory:

```
.../Test_master_atlas-utilization/atlas-utilization/metadata_ttbar_cache.json    -rw-------
```

It is also not in git (**RAN**: `git show HEAD:metadata_ttbar_cache.json` reports
"exists on disk, but not in HEAD" - an untracked runtime cache). So the sample
composition - the DSIDs, their physics names, the number of events processed, and
**whether the ATLAS ttbar sample is dilepton-only or also semileptonic** - is
UNVERIFIED and unavailable.

**This is not specific to one run.** Checked all 49 run directories under her
`data/`: **every single one** has `histograms/` set to `drwx------`, and there is
no readable `atlas_opendata_bumpnet.root` anywhere under `/storage/agrp`
(**RAN**: `find ... -readable`). So no ATLAS histogram file of any run is
currently readable, and no FS or histogram count in this study can be
VERIFIED BY RUNNING.

### The precise fix

`berkom` and `marybo` share the group `watlas`, so group read is the minimal
change. Only Maryna can do this; her area is read-only for us.

```bash
R=/storage/agrp/marybo/DDP/BumpNet4AtlasOpenData/Test_master_atlas-utilization
H=$R/data/atlas_mc_UnlimetedJets_test_ttbar_mc_20261003_210612/histograms
chmod g+rx "$H"
chmod g+r  "$H"/atlas_opendata_bumpnet.root
chmod g+r  "$H"/atlas_btag_ttbar_test_bumpnet_nopostproc.root
chmod g+r  "$R"/atlas-utilization/metadata_ttbar_cache.json
```

The first line is the essential one. To unblock the other runs too, the same
`chmod g+rx` is needed on each run's `histograms/` directory plus `g+r` on the
`.root` files inside.

## 3. Survey of her ttbar runs

**READ, not RAN.** Source: the world-readable `logs/config.yaml`,
`logs/pipeline.out` and `logs/submit_mc.sh` inside each run directory, copied
into `work/ttbar_count_vs_atlas/atlas_input/other_runs/` with sha256 of source
and copy recorded in `other_runs/CHECKSUMS.tsv` (134 files, 49 runs, **0
checksum mismatches**). Extracted by
`atlas_input/atlas_runs_survey.json` via `extract_runs.py`. Nothing in
`/storage/agrp/marybo/` was written; only `data/` was examined.

Only `logs/` is readable in these runs. `aggregated_stats.json`,
`parsing_stats_*.json` and the `batch_*.out` logs are all owner-only, so **the
number of events and the number of input files processed are UNVERIFIED for every
run.** Each run used `NUM_JOBS=3` and merged 3 shards.

The four runs that matter, with the histogram totals **as reported by her own
logs** (UNVERIFIED by us - we could not open the files):

| # | run directory | date | trigger | overlap removal | jets max | photons/taus max | min_events_per_fs | z-cut (GeV) | bin width | total histograms (her log) | code (inferred) |
|---|---|---|---|---|---|---|---|---|---|---:|---|
| A | `atlas_mc_UnlimetedJets_test_ttbar_mc_20261003_210612` | 3 Oct 21:06 | **off** | **off** (key absent, code default `False`) | 4 | **no cap** | 10 | 110 | 10 GeV | **2,684** | `ba57abc` |
| B | `atlas_mc_UnlimetedJets_Leptontrigger_test_ttbar_mc_20261003_224244` | 3 Oct 22:42 | **ON** | off (key absent) | 4 | **no cap** | 10 | 110 | 10 GeV | **2,651** | `ba57abc` |
| C | `atlas_minEvt10_maxTot4_up4j_sublead_btag_ttbar_outliers_Leptontriggers_OverlapRemoval_mc_20261004_115434` | 4 Oct 11:54 | ON | **ON** | 4 | **0 / 0** | 10 | 110 | 10 GeV | **2,867** | `ba57abc` |
| D | `atlas_minEvt10_maxTot4_up4j_sublead_btag_ttbar_outliers_Leptontriggers_NoOverlapRemoval_mc_20261004_185801` | 4 Oct 18:58 | ON | **off** | 4 | **0 / 0** | 10 | 110 | 10 GeV | **3,371** | `747b5d5` |

Run **A** is the one our study has been comparing against: its log total, 2,684,
matches the 2,684 Maryna reported, so A is the 135-final-state run. Mapping
**B to 132** and **C to 129** is **inferred** from the run names, dates and
settings - it is not recorded anywhere, and should be confirmed with Maryna.

Supporting runs, same extraction, used below as cross-checks:

| run | date | trigger | overlap removal | photons/taus max | z-cut | total histograms (her log) |
|---|---|---|---|---|---|---:|
| `..._ttbar_NoLeptontriggers_mc_20260921_223701` | 21 Sep | off | off | 0 / 0 | 110 | 3,495 |
| `..._ttbar_Leptontriggers_mc_20260921_223832` | 21 Sep | ON | off | 0 / 0 | 110 | **3,371** |
| `..._ttbar_outliers_Leptontriggers_mc_20260925_220618` | 25 Sep | ON | off | 0 / 0 | 110 | 3,310 |
| `..._ttbar_outliers_NoLeptontriggers_mc_20260925_220817` | 25 Sep | off | off | 0 / 0 | 110 | 3,675 |
| `atlas_full_fixComb_fixCut_mc_20261001_141954` | 1 Oct | ON | ON | 0 / 0 | 110 | 3,099 (`min_events_per_fs` 100) |

### Which code each run used

**READ.** The submit script runs `main.py` from the shared checkout
`.../Test_master_atlas-utilization/atlas-utilization` and **does not record a
commit**, so the code per run is inferred from commit timestamps. Her checkout is
on branch `feature/overlap-removal`; `HEAD` moved to `747b5d5` ("Remove
NumTrkPt500 from Jets schema - not writable by uproot, mu-jet falls back to
dR-only", 4 Oct 18:25), so runs A, B, C predate it and ran at `ba57abc` (2 Oct
21:41), while run D ran at `747b5d5`.

Two caveats, both **READ**:

* `submit_mc.sh` is **modified but uncommitted** in her checkout, and the run
  configs are untracked, so provenance cannot be pinned exactly.
* The only difference between `ba57abc` and `747b5d5` is **one line in
  `services/parsing/schemas.py`**. The final-state logic
  (`services/calculations/im_calculator.py`, `services/parsing/event_selection.py`)
  is **byte-identical** between them, and `im_calculator.py` has not changed
  since 9 September. So every run from September onward shares the same
  final-state rules.

## 4. Why the ATLAS runs differ

All numbers in this section are **READ** from her logs and **UNVERIFIED** by us.
All statements about code are **READ** from her checkout.

| change made | runs compared | histograms before -> after | effect |
|---|---|---:|---|
| lepton trigger off -> **on** | A -> B (configs identical but for `trigger_config.enabled`) | 2,684 -> 2,651 | **-33 (-1.2%)** |
| lepton trigger off -> **on** | 21 Sep pair (independent confirmation) | 3,495 -> 3,371 | **-124 (-3.5%)** |
| overlap removal off -> **on** | D -> C (configs identical but for `enable_overlap_removal`) | 3,371 -> 2,867 | **-504 (-15.0%)** |
| photons/taus uncapped -> **forced to 0** | A/B vs C/D (confounded, see below) | not isolable | cannot be separated |

### 4.1 The trigger is a small effect

Runs A and B are a clean one-change-at-a-time test: a line-by-line diff of their
two saved configs shows **exactly two differences** - the run name, and
`trigger_config.enabled: false` -> `true` (**RAN**: `diff` on our copies).
Requiring at least one trigger-matched lepton cost 33 histograms out of 2,684.
The 21 September pair, in the other config family, shows the same small
downward shift. **Plain language: turning the trigger on removes a small slice of
events, and only a small number of histograms with them. It cannot explain a
large change in counts.** A drop of 135 to 132 final states is consistent with an
effect of this size.

### 4.2 Overlap removal is the large effect

Runs D and C are also a clean pair: their configs differ in **exactly two
lines** - the run name and `enable_overlap_removal: false` -> `true` (**RAN**:
`diff`). Turning overlap removal on cost 504 histograms out of 3,371, about 15%.

The two runs did use different commits, so this needs one check. The single
differing line removes `NumTrkPt500` from the jet schema, and that field is used
**only** by the muon-jet track condition inside overlap removal - so with overlap
removal switched off it does nothing. Supporting this: run D's total, 3,371,
**exactly reproduces** the 21 September trigger-on, overlap-removal-off total of
3,371. So the 504-histogram drop is attributable to overlap removal, not to the
code change.

**Plain language: overlap removal is where the real difference lies. It throws
away jets that sit too close to a selected lepton, which changes how many
objects the event has, which moves the event into a different final state or
removes it. It is about twelve times as important as the trigger here.**

Her overlap removal is **not** the same as ours (**READ**, her
`event_selection.py`): it is the multi-step ATLAS recipe from arXiv:1606.03903
Table 2, with an electron-jet cone of dR < 0.2, a muon-jet cone of dR < 0.2 with
a track-count-or-pT-ratio condition, then a sliding lepton-jet cone of
`0.4` / `0.04` / `10 GeV`, plus photon and tau steps. Ours is a single
dR < 0.4 removal of jets near selected leptons. **So "overlap removal on" does
not mean the same thing in the two pipelines, and the two should not be expected
to agree even at identical settings.**

Forward-looking note for Ariel and Maryna: at `747b5d5` the `NumTrkPt500` field
is gone from the jet schema, so the muon-jet step now **falls back to dR-only**.
Any *future* overlap-removal-on run will therefore not reproduce run C. Run C is
the last one with the track condition active.

### 4.3 The hidden third difference: photons and taus

This is the finding not in anyone's list so far, and it undermines the natural
reading of the 135 / 132 / 129 sequence.

**READ**, from the saved configs: runs A and B have `particle_counts` entries for
electrons, muons, jets and b-jets **only**. Runs C and D, and every other ttbar
run surveyed, add `photons: {min: 0, max: 0}` and `taus: {min: 0, max: 0}`.

**READ**, from her code: an absent `particle_counts` entry applies no filter
(`services/parsing/event_selection.py` iterates only the keys present), so in A
and B photons and taus are **unrestricted**, whereas C and D **require exactly
zero of each**. And the final state is labelled in
`im_calculator.py` as `f"{e}e_{m}m_{j}j_{g}g_{t}t_{b}b"` - the photon count `g`
and tau count `t` are **part of the final-state identity**, and
`_is_valid_fs` counts them when it limits an event to at most 4 object types.

Consequences, both of them structural:

* A and B can produce final states **containing photons or taus** that C and D
  cannot produce at all.
* A and B can also **lose** events that C and D keep: once photons and taus are
  counted as object types, an event with five types present is rejected by
  `_is_valid_fs`, whereas in C and D that event would have been thrown out
  earlier or had no photon to begin with.

**Plain language: runs A/B and runs C/D are not two settings of the same
analysis. They select different events and they name final states differently.
Comparing 135 against 129 therefore mixes the overlap-removal change together
with the photon/tau change, and the two cannot be separated from the logs
alone.** To get a clean answer, one run should be done changing **only**
`enable_overlap_removal` on top of run B's config.

### 4.4 The "UnlimetedJets" name does not match the saved setting

**READ**: both 3 October configs set `particle_counts.jets: {min: 0, max: 4}` -
the same cap as every other run surveyed. No run among the 49 has a jets cap
other than 4. So, on the evidence of the saved configs, **run A was not an
unlimited-jet run**, despite its name. The name may refer to the uncapped
photons/taus of section 4.3, or be left over from an earlier attempt. Flagging
rather than concluding: worth one question to Maryna, because our whole
comparison treats run A as her reference.

### 4.5 What PR #31's rule would change - and why it cannot be measured yet

**READ**, her `services/calculations/im_calculator.py`:

```python
def _is_valid_fs(self, particle_counts) -> bool:
    total_types = [p for p in particle_counts if p > 0]
    if len(total_types) < self.min_n or len(total_types) > self.max_n:
        return False
    for p in total_types:
        if p < self.min_k or p > self.max_k:
            return False
    return True
```

With her settings (`max_particles_in_combination: 4`,
`max_count_particle_in_combination: 4`) this means: **at most 4 object types
present, and at most 4 of each type.** There is **no constraint on the total**.
So `4e_4m_4j_4b` - sixteen objects - is a valid final state for her code, and is
rejected by PR #31's `electrons + muons + b-jets <= 4` rule. A grep of her whole
checkout for any sum-based rule (`_is_valid_fs`, `max_total_objects`,
`electrons + muons`) finds nothing else. **This confirms, by reading the code,
what `ATLAS_PROVENANCE.md` previously inferred from the config alone.**

Note that `max_total_particles_in_combination: 4` is a different thing: it limits
how many objects go into **one invariant mass**, not how many the **event** may
have.

**Listing every ATLAS final state that this rule would reject, with its histogram
and event counts (addition item 2), requires the list of final states inside the
ROOT file. It is blocked on exactly the permission in section 2, and nothing
else.** The moment the file is readable this is a single run of
`compare_with_atlas.py` plus one grouping step.

## 5. Resuming

When the `chmod` in section 2 is done:

1. Copy the two ROOT files and the JSON into
   `work/ttbar_count_vs_atlas/atlas_input/`, recording sha256 of source and copy.
2. Run Step 2 (reproduce 2,684 / 2,161 / 2,146 / 135 FS), then
   `compare_with_atlas.py` once per variant with `pr31_noOR` as the main
   comparison (see `HANDOFF.md` section 8).
3. Add the `e + mu + b > 4` breakdown (addition item 2) and the four plots.

Nothing else in the study needs re-running.
