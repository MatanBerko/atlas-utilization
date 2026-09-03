# CMS medium-scale four-record test

**Date:** 2026-09-03
**Branch:** `test/cms-mediumscale-fourrecord`
**Configs:** `config.cms_mediumscale_test.yaml` (15 files/record, as briefed) and
`config.cms_mediumscale_complete.yaml` (3 files/record, reduced run that
completes end to end)
**Raw outputs in this folder:**
`dup_rate_probe_output.txt`, `file_run_ranges.txt`,
`oom_run_memory_samples.csv`, `oom_run_parsing_log.txt`,
`completing_run_*.txt`, `plots/*.png`

---

## TL;DR

| Question | Answer |
|---|---|
| Files available / used per record | 30529: 15/71 · 30562: 15/80 · 30530: 15/70 · 30563: 15/82 (probe). Full pipeline could only reach 3/record before OOM (see below). |
| True SingleElectron/SingleMuon duplicate rate | **~0.2%** (Run2016G 0.23%, Run2016H 0.20%), coverage-corrected. The raw number the probe sees is ~0.04%; the docs' "~2%" is **~10x too high**. |
| Does the in-memory de-dup scale? | **No.** The 15-files/record full run was OOM-killed during parsing of the *first* record. De-dup set costs ~87 bytes/kept-event; at full scale that is **35-45 GB**. |
| Should the de-dup scaling fix happen before full scale? | **Yes - it is a hard blocker.** Full scale cannot run without it, on this VM or a large one. |
| Dimuon Z-peak at this scale | _(from the 3-file completing run - filled in below)_ |

---

## 1. Files available vs used, and raw event counts

Checked live via `services/metadata/fetcher.py` / `CMS_RECID_FILEPAGE_URL`.

| Record | Dataset | Files available | Total size | Files used (probe) | Raw events (that sample) |
|---|---|---:|---:|---:|---:|
| 30529 | /SingleElectron/Run2016G | 71 | ~138 GB | 15 | 29,711,216 |
| 30562 | /SingleElectron/Run2016H | 80 | ~119 GB | 15 (11 opened, 4 transient server errors) | 23,929,578 |
| 30530 | /SingleMuon/Run2016G | 70 | ~120 GB | 15 (14 opened, 1 error) | 32,691,355 |
| 30563 | /SingleMuon/Run2016H | 82 | ~140 GB | 15 | 32,230,863 |

All four records have **far more than 15 files** - 30563's tiny event count in the
earlier 2-file smoke test was just because its first two files happen to be
small (14k and 56k events); its other files are ~2-3M events each like the rest.

**Per-file event counts are high and variable:** ~2.0M (30529), ~2.2M (30562),
~2.3M (30530), ~2.1M (30563) raw events per file on average, individual files
ranging ~0.9M-3.3M. Extrapolated full-record raw totals: 30529 ~141M, 30562
~174M, 30530 ~164M, 30563 ~176M -> **~655M raw events across all four records**
(~490M after per-stream selection at the measured ~75%/85% retention). That is
roughly 2-3x the "~2e8" figure in the brief (which was the SingleElectron-only
estimate; the two SingleMuon records roughly double it).

The full pipeline run (`config.cms_mediumscale_test.yaml`, 15 files/record) did
**not** get through even one record - see section 3 - so the "X of Y files used"
for the completed run is **3 of {71,80,70,82}** via
`config.cms_mediumscale_complete.yaml`. The 15-files/record file counts above
come from the lightweight `dup_rate_probe.py`.

---

## 2. Real duplicate rate: **~0.2%**, not ~2%

### Method

The pipeline de-duplicates on `(run, luminosityBlock, event)`. Measuring the true
overlap by a full parse is infeasible at the needed file count (section 3), so
`scripts/dup_rate_probe.py` reads **only** those three branches (plus the
`nMuon`/`nElectron` counters) from 15 files per record - cheap enough to cover
the needed breadth. For each era it builds the SingleMuon key set, then streams
the SingleElectron files counting how many land in it.

**Crucial fact about the file layout** (`file_run_ranges.txt`): CMS NanoAOD files
are **not** sequential in run number. Every file spans essentially the whole run
range of its era (e.g. 30529 files all span runs ~278820-280385). Each file is a
scattered ~1/N sample of all lumisections, not a contiguous slice.

### Raw probe result (what the 15-file sample directly sees)

| Era | SingleElectron events | Raw overlap hits | Raw overlap |
|---|---:|---:|---:|
| Run2016G (30529 vs 30530) | 29,711,216 | 13,612 | **0.046 %** |
| Run2016H (30562 vs 30563) | 23,929,578 | 8,877 | **0.037 %** |

The count-only proxy (SE events with >=1 electron vs SM events with >=1 muon, no
pt/eta cuts) is essentially identical: 0.045 % / 0.037 %.

### Coverage correction -> true rate

Because files are random lumisection samples, a both-triggered SingleElectron
event in the sample is only *detected* if its SingleMuon twin's file was also
sampled - probability = (SM files used) / (SM files total).

| Era | detection prob | corrected dup count in SE sample | **corrected rate** |
|---|---:|---:|---:|
| Run2016G | 14/70 = 0.20 | 13,612 / 0.20 = 68,060 | **0.229 %** |
| Run2016H | 15/82 = 0.183 | 8,877 / 0.183 = 48,500 | **0.203 %** |

**Best estimate of the true SingleElectron/SingleMuon duplicate rate: ~0.2 %**
(consistent across both eras). Hit counts grew linearly with every added file on
both sides, which is what you expect for uniform lumisection sampling and gives
confidence in the correction.

**vs the ~2 % expectation in `docs/CMS_KNOWN_LIMITATIONS.md`: about 10x lower.**
It is still a real, non-trivial overlap - ~0.2 % of ~490M selected events is
**~1 million duplicate events** at full scale that de-dup must catch - just an
order of magnitude smaller than assumed. The pipeline's actual post-kinematic-cut
de-dup removals would be slightly below 0.2 % (the cuts drop ~15-25 % on each
side).

The earlier 2-file smoke test's ~0.003 % was a severe undercount purely from
tiny file coverage (detection prob there ~ (2/70) x (2/71) ~ 0.0008).

---

## 3. De-dup memory behaviour as volume grows

### Direct per-key cost

Measured empirically (build a set of N synthetic `run<<96 | lumi<<64 | event`
keys, read peak RSS): **~87 bytes per key** all-in (Python `set` table + the
>64-bit `int` objects), ~65 bytes/key incremental.

### 2-file run (baseline, completed fine)

`config.cms_fourrecord_test.yaml`: 8,665,374 events into the de-dup set ->
**~0.6-0.75 GB**. The run peaked well inside the 7 GB container.

### 15-file run: OOM-killed during parsing of record 1

`config.cms_mediumscale_test.yaml`, parse knobs deliberately turned *down*
(2 threads, 256 MB chunk flush) to give the set maximum room:

| elapsed | container RSS | where |
|---|---:|---|
| 0 min | 0.6 GiB | start |
| 4 min | 1.9 GiB | record 30530, ~2 files |
| 8 min | 5.2 GiB | ~4 files |
| 11 min | 5.8 GiB | ~6 files |
| ~13 min | **6.6 GiB peak** | ~8-9 files |
| ~15.5 min | pinned ~6.2 GiB, then **OOM-killed** | record 30530 file ~10 of 15 |

At the kill: **16,386,051** muon-selected events had been written (9 chunks on
disk). The de-dup set held ~16.4M keys ~= **1.4 GB**. The other ~4.8 GiB was the
parsing working set (uproot + awkward buffers, even at 2 threads). No
traceback - a clean kernel OOM kill.

### Reading of the scaling

- The de-dup set is a **real and growing** contributor, but at this VM size the
  **parsing working set (~5 GiB) is the bigger half**, leaving only ~1.5-2 GiB
  of headroom. That caps a single container at **~20-25M kept events** regardless
  of the de-dup implementation.
- Within that ceiling the de-dup set scales exactly linearly (~87 B/key) with no
  cliff - it is not pathological, just unbounded.
- **The current implementation cannot process even one full record (15 files) in
  the 7.4 GB Docker VM.**

---

## 4. Full-scale extrapolation (~490M selected events, all four records)

### Memory

| Component | At full scale | Fits 7.4 GB VM? | Fits a 128-256 GB machine? |
|---|---:|---|---|
| De-dup set (current: Python set, ~87 B/key) | **~35-45 GB** | No | Marginal, and grows through the whole run |
| De-dup set (packed uint64 key + sorted `np.unique`/`np.isin`) | ~3-4 GB (or ~1.5-2 GB per era) | No | **Yes, comfortably** |
| Parsing working set | ~5 GiB (unchanged) | Marginal | Yes |

The packed-key/`np.unique` approach (the deferred fix) turns a 35-45 GB
open-ended structure into a ~3-4 GB bounded one, or ~1.5-2 GB if de-dup is done
per run-era. That is the difference between "impossible" and "routine".

### Runtime (rough, single container)

From the 15-file run: ~1.5 min/file parsing at 2 throttled threads
(1-8 files clean, before swap). 303 files -> **~7-8 h parsing** throttled, or
~3-4 h with more threads on a non-memory-bound machine. Mass-calc with 4 object
types (Electrons/Muons/Jets/Photons, `min_particles>=2`) dominates end-to-end
and from earlier SingleElectron runs scales to **~15-25 h single-container** for
all four records. **Use the multi-job `submit.sh` cluster path**, or a large
machine, for the real thing.

---

## 5. Dimuon Z-peak sanity check (3-file completing run)

_(filled in from `config.cms_mediumscale_complete.yaml` results)_

- Retention per record: _TBD_
- De-dup removed at this scale: _TBD_
- Raw `m0m1` Z-peak: _TBD_
- `m0m1_main` after post-processing: _TBD_
- Anything qualitatively different from the 2-file run: _TBD_

Example histograms (actual output from this run): see `plots/`.

---

## 6. Recommendation

**The de-dup scaling fix must land before the full-scale run.** It is not a
"nice to have" - the current Python-set de-dup would need 35-45 GB and grows
without bound as the run proceeds, so the full-scale run simply cannot complete
with it in place, on any machine size that is realistic here.

The fix is small and well understood: pack `(run, luminosityBlock, event)` into
one `uint64` (fits: ~19-bit run + ~12-bit lumi + ~32-bit event) and de-duplicate
with a sorted array + `np.unique`/`np.isin`, ideally per run-era so the working
set stays ~1.5-2 GB. This is separate work, still out of scope for this task.

Two secondary points:
- The measured duplicate rate (~0.2 %) is ~10x below the documented ~2 %.
  `docs/CMS_KNOWN_LIMITATIONS.md` should be updated once this is confirmed on a
  fuller run - it changes "de-dup removes a lot" to "de-dup removes ~1M events",
  still worth doing but a smaller correction than assumed.
- `dup_rate_probe.py` is a cheap way to confirm the rate at any file count
  without a full parse - worth keeping.
