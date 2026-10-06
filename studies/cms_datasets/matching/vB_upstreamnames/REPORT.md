# Version B re-delivered with upstream histogram names and no per-histogram minimum

Two changes Maryna decided, applied to the muon delivery for BumpNet.
Written for a reader who does not read code.

Nothing about the physics changed. No event was re-selected, no mass was
recomputed, and the 209 per-file jobs were **not** re-run. What changed is
what the histograms are **called**, and **how few entries** a histogram may
have and still be delivered.

Every number below is labelled **VERIFIED BY RUNNING** (produced or checked
in this session, with the method named) or **UNVERIFIED**.

**The file for Maryna:**
`muon_combined_matched_vB_upstreamnames_bumpnet_cropped.root` in
`/storage/agrp/berkom/atlas-utilization/output/cms_datasets/deliver/muon_combined_vB_upstreamnames_20261006/`.
A `README.txt` sits beside it saying the same; a copy is committed here at
[`evidence/README.txt`](evidence/README.txt).

---

## 1. What changed, and why

### (1) Names now contain only the object types we actually configure

**Before.** Every name carried six fields — electrons, muons, light jets,
**photons, taus**, b-jets — even though this analysis selects no photons and
no taus, so those two were *always zero*.

**Now.** A name lists only the configured types, in the upstream pipeline's
own order. Two always-zero fields disappear.

| | 5 Oct | now |
|---|---|---|
| final state | `0e_2m_5j_0g_0t_1b` | `0e_2m_5j_1b` |
| histogram name | `mass_m0m1_cat_0ex_2mx_5jx_0gx_0tx_1bx` | `mass_m0m1_cat_0ex_2mx_5jx_1bx` |
| in the ROOT file | `ROI_mass_m0m1_cat_0ex_2mx_5jx_0gx_0tx_1bx_width_10` | `ROI_mass_m0m1_cat_0ex_2mx_5jx_1bx_width_10` |

**Why it matters.** This is exactly what the main upstream pipeline produces
for this configuration, so BumpNet sees one naming convention rather than
two. The rule is not "drop g and t" — it is "list the configured types" —
so a future analysis that *does* select photons would get its photon field
automatically.

**How it was matched.** The label-building code was taken from upstream
itself at commit `88d7a4b` — the same `FINAL_STATE_OBJECTS` tuple and order
(e, m, j, g, t, b), the same "only types present in the record" filter, the
same `_` separator and `<count><letter>` form. The histogram-name builder
needed no change at all: ours was already identical in behaviour to
upstream's `_convert_to_bumpnet_name`, so the new names follow automatically.
A test compares the two implementations directly on the same inputs rather
than assuming it (**VERIFIED BY RUNNING**).

**Exact light-jet multiplicities are kept** — 5j, 6j, 11j still each have
their own final state. That is also what the upstream authors' own pending
fix does.

**Checked before touching anything**, because dropping fields would be
dangerous if anything downstream read them (**VERIFIED BY RUNNING**):

- **None of the 186 mass combinations uses photons or taus.** The object
  types they reference are exactly BJets, Electrons, Jets, Muons.
- **The Version B reject rule uses object counts, not names.** It is
  `electrons + muons + b-jets <= 4` computed from the actual object arrays,
  never from a label string.

So removing two always-zero fields cannot change any selection, any mass, or
any rejection decision — and the pilot confirmed that it did not.

### (2) No per-histogram minimum entry count

**Before.** On top of everything else, this delivery required each
individual histogram to have at least 100 entries.

**Now.** That requirement is gone; BumpNet re-checks it during smoothing.

**What replaced it, and how it was matched to upstream.** Upstream's own
histogram stage was read (`services/pipelines/histograms_pipeline.py` at
`88d7a4b`). It applies **no minimum entry count whatsoever**. The only thing
it skips is a signature with *no data at all*: `_iter_signature_chunks`
yields only chunks with `len(arr) > 0`, and both
`_create_histograms_for_signature` and
`_create_merged_histograms_from_sqlite_signatures` end with
`if not has_data: return []`. So upstream writes a histogram whenever at
least one value exists and writes nothing when none does. **That is exactly
what this delivery now does: the floor is one entry.**

In practice nothing was dropped by that floor — every histogram that reached
this stage had at least one entry, and **no delivered histogram is empty**
(**VERIFIED BY RUNNING**).

### (3) Confirmed unchanged: the ">=100 events per final state" rule

This is the rule that matters most, and it is **unchanged at 100 and still
applied exactly once, on the combined shards of all 209 files**. Confirmed
in the code and now documented at the place where it happens:

- the **per-file** jobs run with `min_events_per_fs=1`
  (`run_dataset_on_file.py`), so no final state is ever pruned per file;
- the **delivery** calls `prune_final_states_below_min_events` once, with
  all 209 shard paths together. That function sums each final state's
  population across **every** shard before deciding what to delete.

This matters: a per-file or per-batch threshold would wrongly delete final
states that are only large enough once all the files are pooled.

Independent evidence that it behaved identically: the 5 Oct build and this
one both end that stage with **1,496** final-state/combination names
(**VERIFIED BY RUNNING** — both build summaries).

The pruning step deletes rows in place, so it is run only on scratch
**copies** of the shards; the originals are never modified.

### What is deliberately unchanged

The >=100-events-per-final-state value, the Z cut (110 GeV), the outlier
split, the binning, object definitions, the b-tag working point, trigger
matching, de-duplication, the Version B rule, and the 186 combinations.

---

## 2. Counts: 5 Oct delivery vs this one

All **VERIFIED BY RUNNING** — the "now" column from the build I ran this
session ([`evidence/build_summary_rare4_nobincut.json`](evidence/build_summary_rare4_nobincut.json)),
the "5 Oct" column from that delivery's own committed summary and from
re-reading its ROOT file ([`evidence/step3_checks.json`](evidence/step3_checks.json)).

| | 5 Oct | now |
|---|---|---|
| delivered histograms | 1,329 | **1,496** |
| additional histograms | — | **+167** |
| histograms lost | — | **0** |
| distinct final states with a delivered histogram | 78 | **81** |
| histograms with **>=25 filled bins** (information only) | 1,243 | **1,258** |
| … with >25 filled bins (old "min26bins" rule) | 1,233 | 1,247 |
| … with >30 filled bins (old "min31bins" rule) | 1,177 | 1,188 |
| per-histogram minimum entries | 100 | **1** (upstream behaviour) |
| histograms excluded by that minimum | 167 | **0** |
| final states passing ">=100 events per final state" | 1,496 | 1,496 (unchanged) |
| distinct raw signatures before any cut | 247,833 | 247,833 (unchanged) |
| name format | six fields incl. `0g`, `0t` | upstream: configured types only |

**The +167 are precisely the histograms the old per-histogram rule had been
throwing away** — not a new population. They were identified by name from the
5 Oct build's own exclusion list, and every single one is accounted for
(**VERIFIED BY RUNNING**): 167 expected, 167 found, 0 unexplained, 0 missing.

---

## 3. Every check, and whether it passed

### Tests committed with the code — all pass, **VERIFIED BY RUNNING**

`studies/cms_datasets/tests/test_upstream_names.py` (new): label format for
events with 0, 5 and 11 light jets; our labels compared **event by event
against upstream's own label code** replicated from its source (34 synthetic
events, all agree); the legacy conversion including two-digit counts, the
**abort on a non-zero photon or tau count**, rejection of unparsable input,
and the **no-duplicates** check (both that it passes when it should and that
it fails loudly when two names would collapse); histogram names compared
against **upstream's own `_convert_to_bumpnet_name`**; and the new
minimum-entries behaviour including that the default is still 100.

`studies/cms_datasets/tests/test_exact_jet_labels.py` updated to the new
format — **85 checks, all pass**. The m0m1j0 study tests are unaffected and
still pass.

### Step 2 — pilot validation on the 4 pilot files

**124 checks, 0 failures. VERIFIED BY RUNNING** — full output at
[`evidence/step2_pilot_validation_output.txt`](evidence/step2_pilot_validation_output.txt).

- **Selection untouched** — every per-stage count and every Version B reject
  diagnostic identical to 5 Oct, file by file. Renaming moved no events.
- **Signatures correspond 1:1** — every new signature matches a 5 Oct
  signature through the conversion; none unmatched either way; no two old
  signatures land on the same new one.
- **Mass arrays byte-identical** for every corresponding pair, across the
  Version B and normal shards, inclusive and exclusive.
- **Per-final-state event counts identical** after conversion, for both the
  delivered Version B version and the normal one.

### Step 2 — the three pilot delivery builds

**All identical as required. VERIFIED BY RUNNING**
([`evidence/compare_A_vs_B.json`](evidence/compare_A_vs_B.json),
[`evidence/compare_C_vs_5oct.json`](evidence/compare_C_vs_5oct.json)):

| comparison | result |
|---|---|
| **A** built from the NEW shards vs **B** built from the 5 Oct shards through the conversion | **identical** — 476 histograms, same names, same bin contents and edges, 992,123 entries each; the cropped files too |
| **C** = a pre-existing invocation re-run with the new code vs the file it produced on 5 Oct | **identical** — 347 histograms, 984,547 entries |

A vs B is the important one: it proves the conversion applied to the old
shards gives *exactly* what re-running the driver would have given. That is
why the 209 jobs did not need re-running.

C vs 5 Oct proves old invocations still produce exactly what they produced
before, as required.

### Step 3 — the full rebuilt delivery

**All checks pass. VERIFIED BY RUNNING** ([`evidence/step3_checks.json`](evidence/step3_checks.json)):

- All **1,329** histograms of the 5 Oct delivery reappear under their
  converted names, with **identical bin contents and identical bin edges**.
  Converting the 5 Oct names produced no duplicates and preserved the count.
- The new file has **exactly 167** additional histograms; every one is a
  histogram the old >=100-entries rule had excluded; none is unexplained;
  none of the previously-excluded ones is still missing.
- **No delivered histogram is empty.**
- **Every name matches the upstream format**: the `ROI_mass_<combo>_cat_…`
  shape, every category field `<count><letter>x`, and **no photon or tau
  field anywhere**. As an independent check, each name was rebuilt from its
  own parts using upstream's own name builder and came back unchanged.
- **No duplicate names.**
- Both files verified as genuine `TH1F`, 1,496 histograms in each.

---

## 4. One thing that differs from what the task expected

The task anticipated the **final-state count would be unchanged**. It is
**78 → 81** (**VERIFIED BY RUNNING**). This is not a problem, and it is a
direct consequence of change (2) rather than of the renaming.

Three final states had *every* one of their histograms excluded by the old
>=100-entries rule, so they did not appear in the 5 Oct file at all. Now that
the rule is gone, their histograms are delivered and the final states appear:

- `0e_1m_9j_1b`
- `0e_2m_6j_1b`
- `1e_2m_0j_1b`

No final state was lost, and the new delivery contains every 5 Oct final
state (checked explicitly). The renaming itself merged nothing: the
conversion is one-to-one, proven by the no-duplicate checks at both the
signature and the histogram level.

---

## 5. Where everything is

| what | where |
|---|---|
| branch | `feature/upstream-names-no-hist-min` (not merged into master) |
| pinned commit for the pilot run | `06922a9` |
| pinned checkout | `/storage/agrp/berkom/atlas-utilization/checkouts/06922a9/repo` |
| analysis checkout | `/storage/agrp/berkom/atlas-utilization/checkouts/analysis_upnames/repo` |
| pilot run + its validation | `.../output/cms_datasets/vB_upstreamnames_pilot/` |
| **the delivery** | `.../output/cms_datasets/deliver/muon_combined_vB_upstreamnames_20261006/` |
| **the file for BumpNet** | `muon_combined_matched_vB_upstreamnames_bumpnet_cropped.root` |
| uncropped companion (cross-checks only) | `muon_combined_matched_vB_upstreamnames_bumpnet.root` |

The uncropped file is on the full fixed 0–10000 GeV grid and is for
cross-checking and plotting. BumpNet needs the **cropped** one, because it
requires a non-empty first bin.

The 5 Oct delivery and all the 5 Oct production shards were opened
**read-only** throughout and are untouched; the pruning step ran only on
scratch copies. The 209 per-file production jobs were not re-run.

---

## 6. One thing I checked carefully, because it looked wrong at first

A final audit showed that the 209 job **directories** under the 5 Oct
production, and the 4 pilot run directories, had a modification timestamp
from today. Since those outputs are supposed to be strictly read-only, I
chased it down rather than assume it was harmless.

**No data was changed.** What happened: reading a SQLite shard through the
shared helper opens it in read-write mode, and SQLite then creates two small
temporary journal files next to it and deletes them again when it closes.
Creating and deleting a file inside a directory updates that *directory's*
timestamp, but touches nothing inside the shard. Evidence, all **VERIFIED BY
RUNNING**:

- **Not one `.sqlite` file was written today.** The newest shard timestamp
  anywhere in either tree is 5 Oct 22:10.
- **No leftover journal files** remain (zero `-wal`/`-shm` files).
- **The contents are provably identical**: this delivery re-read those exact
  shards and reproduced all 1,329 of the 5 Oct histograms with byte-identical
  bin contents. That could not happen if the data had been altered.

Two things worth the group's attention, neither changed here:

- The helper that lists a shard's contents opens the file read-write even
  though it only reads. That is shared code, which this task may not modify,
  so it is reported rather than fixed. It is a latent risk: a crash at the
  wrong moment could in principle leave a stray journal file beside a
  supposedly read-only shard. Everything this task did for actual data
  reading used a strict read-only connection (`mode=ro&immutable=1`).
- Separately, each job's recorded `*_shard_size_mb` is about 5% smaller than
  the file on disk, consistently and for every shard — including ones nothing
  has opened since 5 Oct. That is a 5 Oct bookkeeping artefact (the size was
  recorded before the database was finally flushed), not a sign of any later
  change. Worth knowing so nobody mistakes it for one, as I briefly did.

## 7. Noted in passing, not changed

- The validation scripts from the 5 Oct task
  (`studies/cms_datasets/matching/vB_exactlabels/scripts/`) still expect the
  old six-field labels. They are the committed record of that task's
  validation and are not re-run, so they were deliberately left alone. The
  same applies to that task's committed evidence files, which quote old-style
  names.
- The b-tag working point question from the 5 Oct report is still open
  (we use DeepJet 0.2598, the 2016 pre-VFP value, on post-VFP data whose
  value would be 0.2489). Unchanged here.
