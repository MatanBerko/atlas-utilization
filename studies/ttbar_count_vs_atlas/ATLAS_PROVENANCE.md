# Step A - provenance of Maryna's ATLAS ttbar file

**Status: Step A is complete. Steps B-G are BLOCKED by file permissions** — see
the last section.

Everything below comes from files copied out of Maryna's area into
`work/ttbar_count_vs_atlas/atlas_input/` with sha256 verified against the source,
plus read-only `git` queries against her checkout. Nothing in
`/storage/agrp/marybo/` was written: her checkout is not writable by us (checked),
and every git call used `--no-optional-locks` with a per-command
`-c safe.directory=...` override, so no config file anywhere was modified.
Machine-readable version: `evidence/atlas_provenance.json`.

## The headline: her file was NOT produced by PR #31

| | |
|---|---|
| checkout | `/storage/agrp/marybo/.../Test_master_atlas-utilization/atlas-utilization` |
| branch | **`feature/overlap-removal`** |
| HEAD | **`ba57abc20467782d8a98a216e45fed6d7648296f`** |
| is it upstream master (`8120fb8`)? | **no** |
| is it PR #31 (`81dd40a`)? | **no** |
| is PR #31 an ancestor of it? | **no** |
| is upstream master an ancestor of it? | **no** |
| uncommitted changes to **tracked** files | **none** (33 untracked files, all configs/plots/scripts) |

**RAN** (`git --no-optional-locks -c safe.directory=... -C <her checkout> ...`).

Her branch forks from `fe5a560` ("Fix trigger-config wiring (#29)") and adds five
commits:

```
ba57abc Add xrootd timeout + retry with backoff for stuck CERN connections
4b9ef6a Fix overlap removal: drop NumTrkPt500 before save, use ak.with_field to preserve layout
252637f Fix overlap removal: skip steps when particle collection is empty
459a0af Fix overlap removal: use flat numpy dR, bypass awkward layout bugs
8cd9acd Add ATLAS-style overlap removal (arXiv:1606.03903, Table 2)
```

The **only** commit upstream master has that her branch does not is
`8120fb8 Align outlier split to bin edges (#27)`.

So: **her run = upstream master, minus #27, plus unused overlap-removal code.**
This matters, because the original study compared our pipeline against PR #31 on
the assumption that PR #31 produced the 2,146. It did not.

## The five questions

### (1) Are events with >= 5 light jets dropped, grouped as `4j`, or kept?

**DROPPED.** Not grouped into `4j`, and not kept as their own categories. **READ**
(her code plus the run's own config snapshot).

* The run config sets `particle_counts.jets = {min: 0, max: 4}`.
* Her `apply_parsing_event_selection` passes `particle_counts` straight into
  `filter_events_by_particle_counts(..., is_particle_counts_range=True)`, whose
  range branch builds the **event-level** mask
  `(obj_count >= min) & (obj_count <= max)` and drops events outside it.
* She does **not** have PR #31's override that raises the light-jet maximum to
  infinity — there is no `LIGHT_JET_FIELD` logic in her `event_selection.py` at all.
* And `IMCalculator._is_valid_fs`, with `max_count_particle_in_combination = 4`,
  would drop any surviving >4 final state anyway.

> **Flag for Maryna.** The run directory is named
> `atlas_mc_UnlimetedJets_test_ttbar_...`, which suggests the opposite intent, but
> the config snapshot stored *with that run* says `jets: max: 4`. Either the name is
> left over from an earlier attempt, or the intended unlimited-jets setting did not
> make it into this run. This is worth one question before the comparison is read.

### (2) Is there any jet-lepton overlap removal?

**NOT APPLIED in this run** — even though her branch is called
`feature/overlap-removal` and contains a full ATLAS-style implementation. **READ.**

* `services/parsing/event_selection.apply_overlap_removal` implements ATLAS
  Table 2 of arXiv:1606.03903 (e-jet dR 0.2, mu-jet dR 0.2 with a track/pT-ratio
  veto, a pT-dependent sliding lepton-jet cone, photon-jet, photon-electron,
  tau-electron).
* `orchestration/handlers/parsing_handler.py` calls it only inside
  `if parsing_config.enable_overlap_removal:`.
* `domain/config.py` declares `enable_overlap_removal: bool = False` and reads it
  as `parsing_dict.get("enable_overlap_removal", False)`.
* The run's own config snapshot has **no `enable_overlap_removal` key**, so the
  default `False` applied.

She does have a separate config file
(`config_up4j_minEvt10_subleading_btag_ttbar_test_Leptontriggers_OverlapRemoval.yaml`)
that is presumably the one that turns it on — but it is not the config this run used.

**Consequence: for overlap removal, the fair CMS comparison is our variant (c)
`pr31_noOR`, not (a) or (b).** That was not obvious before reading her tree.

### (3) What b-tag selection?

Jet tagging **on**; thresholds `{btagDeepFlavB: 0.5, DL1d: 2.51}`. For ATLAS
PHYSLITE input the **DL1d score at 2.51** is the one in force (`btagDeepFlavB` is
the CMS branch and is not present in ATLAS files). **READ.**

### (4) Is upstream #27 present?

**No.** It is precisely the one commit upstream master has and her branch lacks
(`Align outlier split to bin edges (#27)`), and `_aligned_bin_edges` does not
appear in her `post_processing_pipeline.py`. **READ** (git log + text check).

This matches our side: our branch does not have #27 either, so the outlier split
behaves the same way on both sides and still cannot explain any difference.

### (5) The config actually used

`config.yaml`, confirmed by `CONFIG="config.yaml"` in the run's **own**
`logs/submit_mc.sh` — so my open question from the original task is settled: it is
`config.yaml`, not the `configWmaxTotal_...` file. But the `config.yaml` in **her**
checkout is not the same as PR #31's. The snapshot stored with the run says:

| setting | her run | our pipeline |
|---|---|---|
| `trigger_config.enabled` | `false` | muon HLT + trigger matching (data); off for `--population notrigger` |
| `parse_mc` | `true` | n/a |
| `max_files_to_process` | **40** | all 49 files of record 67801 |
| `objects_to_calculate` | `[Electrons, Muons, Jets, BJets]` | same |
| combinatorics (min/max types, min/max count, max total, subleading) | 1 / 4 / 1 / 4 / 4 / on, index 1 | **identical** |
| **`min_events_per_fs`** | **10** | **100** |
| **`z_peak_cutoff`** | **110 GeV** | **115 GeV** |
| `max_mass_cutoff` | 10000 GeV | same |
| `bin_width_gev` | 10.0 | same |
| `particle_counts` (e / mu / j / b) | all `{min 0, max 4}` | e+mu+b <= 4 combined; light jets uncapped (rare4) |
| electron cuts | pT > 25 GeV, \|eta\| < 2.47, rel iso < 0.06 | pT > 25 GeV, \|eta\| < 2.5, cutBased >= 3 |
| muon cuts | pT > 25 GeV, \|eta\| < 2.5 | pT > 25 GeV, \|eta\| < 2.4, mediumId, iso < 0.15 |
| jet cuts | pT > 30 GeV, \|eta\| < 2.5 | same + tight jetId |
| overlap removal | **off** | on (dR < 0.4) in (a)/(b), off in (c) |

**Two of these are new and material**, and neither was visible from PR #31:
`min_events_per_fs = 10` against our 100, and `z_peak_cutoff = 110` against our 115.
The first is the bigger one — it lets final states through that our pipeline prunes
away an order of magnitude earlier, so some of her 135 categories may be ones we
discard on statistics rather than ones we cannot form.

## Her own pipeline log

From `logs/pipeline.out` (copied, sha256-verified):

```
Merging 1 batch histogram files -> atlas_opendata_bumpnet.root
hadd succeeded: .../histograms/atlas_opendata_bumpnet.root
Applied global tail display ranges to 2684 merged histogram(s)
Grouped 8052 signatures into 2684 unique histogram signatures
Wrote 2684 histograms to shared file .../atlas_btag_ttbar_test_bumpnet_nopostproc.root
```

**2,684** matches the total she reported exactly. Note there is a second file,
`atlas_btag_ttbar_test_bumpnet_nopostproc.root`, holding the same 2,684 histograms
**before** post-processing — that is the right file for a like-for-like comparison
against our pre-bin-cut histograms in Step D, if it can be made readable.

## BLOCKED: what we cannot read

We are `uid=berkom, gid=watlas`. Her files are mode `700`/`600`, so group and other
have no access. **VERIFIED BY RUNNING** (`test -r`, `ls`, `find -readable`):

| path | mode | readable? |
|---|---|---|
| `.../histograms/` (and the ATLAS ROOT file in it) | `drwx------` | **NO** |
| `.../atlas-utilization/metadata_ttbar_cache.json` (the sample list) | `-rw-------` | **NO** |
| `.../im_arrays/`, `im_arrays_processed/`, `parsed_data/`, `plots/` | `drwx------` | **NO** |
| `.../logs/` directory listing | `drwxr-xr-x` | yes |
| `.../logs/config.yaml`, `pipeline.out`, `submit_mc.sh` | `-rw-r--r--` | yes |
| her git checkout and its source files | world-readable | yes |

Only **3** files under the whole run directory are readable by us.

**Steps B, C, D, E, F and G cannot proceed** without read access to:

1. `.../histograms/atlas_opendata_bumpnet.root` — the ATLAS histogram file (Steps C, E, F)
2. `.../atlas-utilization/metadata_ttbar_cache.json` — the sample list (Step B)
3. ideally also `.../histograms/atlas_btag_ttbar_test_bumpnet_nopostproc.root` — the
   pre-post-processing histograms, which make Step D's "count our way, her way"
   comparison exact rather than approximate

The simplest fix, for Maryna to run:

```bash
chmod o+rx /storage/agrp/marybo/DDP/BumpNet4AtlasOpenData/Test_master_atlas-utilization/data/atlas_mc_UnlimetedJets_test_ttbar_mc_20261003_210612/histograms
chmod o+r  /storage/agrp/marybo/DDP/BumpNet4AtlasOpenData/Test_master_atlas-utilization/data/atlas_mc_UnlimetedJets_test_ttbar_mc_20261003_210612/histograms/*.root
chmod o+r  /storage/agrp/marybo/DDP/BumpNet4AtlasOpenData/Test_master_atlas-utilization/atlas-utilization/metadata_ttbar_cache.json
```

(or `g+rx`/`g+r` — we share the `watlas` group). Alternatively she can copy the
three files anywhere world-readable and send the path. Once any of that is done,
Steps B-G run unchanged: everything needed is already written and self-tested.
