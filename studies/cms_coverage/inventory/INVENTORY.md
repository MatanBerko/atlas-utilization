# Complete CMS Open Data inventory

**Survey task — no cluster jobs, no data files opened, no histogram
production.** Everything below comes from the CERN Open Data portal's own
record API (`https://opendata.cern.ch/api/records/`), fetched directly
from this machine. Every number traces to a saved API response under
`portal_raw/`, or is explicitly marked **INFERRED**/**UNVERIFIED**.

## 0. Headline: what we can read TODAY, with zero new work

This is the number that matters most to the group right now — everything
else in this document is either already-known territory measured
completely for the first time, or a description of what more work could
unlock.

| | Records | Files | Events | Size |
|---|---:|---:|---:|---:|
| **NanoAOD** (collision data) | 32 | 1,254 | 2,096,825,318 | 1.88 TB |
| **NanoAODSIM** (simulation), fully detailed | 10,679 | 79,483 | 13,182,683,386 | 21.08 TB |
| **NanoAODSIM, Supersymmetry benchmark points** (count only — see §1) | 10,896 | not measured | not measured | not measured |
| **NanoAOD + NanoAODSIM total** | **21,607** | ≥80,737 | ≥15,279,508,704 | ≥22.96 TB |

**Versus the earlier measurement's 16 data + 29 MC = 45 records**: the
portal actually has **32 NanoAOD data records** (not 16 — see §3.1) and
**21,575 NanoAODSIM records** (not 29). Of the physics we'd actually use
(excluding Supersymmetry/Exotica/other BSM benchmark points — see §4), the
comparable pool is **32 data + 2,406 Standard-Model-relevant MC = 2,438
records**, of which the earlier measurement used 45 (**1.8%**). No new
capability is needed to read any of this — same NanoAOD schema, same
tooling, same everything. This is pure "we didn't look everywhere."

**CMSSW requirement for NanoAOD/NanoAODSIM: "Not required"** (the portal's
own `system_details.release` field is absent for every one of the 32+21,575
records checked) — confirmed directly, not assumed, matching what the
2016 NanoAOD release page states.

## 1. Method: how every record below was found, and how completeness is proven

**Endpoint**: `GET https://opendata.cern.ch/api/records/`, query parameter
`q` (a Lucene-style string), plus separate `category`/`subcategory` GET
parameters for facet filtering (these do **not** work inside `q` — e.g.
`q=...AND category:"Standard Model Physics"` returns zero hits; `category=
Standard Model Physics` as its own parameter returns the correct 1,030 —
this is the same "field-qualified queries mostly fail" trap the earlier
survey hit, now isolated to exactly which fields behave which way).
Working filters used throughout: `experiment:CMS`, `type.primary:Dataset`,
`type.secondary:Collision` / `type.secondary:Simulated`,
`distribution.formats:<format>`, `collision_information.type:<PbPb|pPb>`.

**Two real pagination bugs were found and fixed, not assumed away:**

1. **Default sort (`bestmatch`) is unstable across pages.** A first,
   naive 4-page fetch of the 345 CMS collision-dataset records (recorded,
   then discarded) returned 345 hits containing only **245 unique record
   IDs** — 100 duplicates, meaning 100 real records were silently never
   returned. Diagnosed by checking `next` link echoes: an explicit
   `sort=recid` parameter was silently dropped (not a recognized sort key,
   confirmed by inspecting the API's own echoed pagination links) and
   pagination fell back to `bestmatch`, which has no stable tie-break.
   **Fixed** with `sort=title` (confirmed to be honored) — re-fetching the
   same 345-record query then returned exactly 345 unique IDs. **Every
   multi-page fetch in this survey uses `sort=title`, and every one was
   verified for unique-recid-count == reported total before being used.**
2. **A ~10,000-result deep-pagination ceiling** (the classic Elasticsearch
   `max_result_window` default). Paginating the 21,575-record NanoAODSIM
   set at `size=1000` returned real data through page 9 (9,000 hits) and
   **silently empty pages from page 10 onward** — not an error, not a
   truncation notice, just zero hits with `hits.total` still correctly
   reporting 21,575. Same behavior confirmed on the 28,693-record
   MiniAODSIM set. **Fixed** by partitioning each query with the portal's
   own `category` facet (Supersymmetry / Exotica / Higgs Physics /
   Standard Model Physics / Beyond 2 Generations / B physics and
   Quarkonia / Miscellaneous / …) before paginating — every category
   bucket used is individually under 10,000 **except Supersymmetry**
   (10,896 in NanoAODSIM, 11,379 in MiniAODSIM), which has no further
   facet to split by (no subcategory, no keywords, no distinguishing
   collision-energy/run-period values were found). **This is the one
   genuine gap in this inventory**: Supersymmetry's record *count* is
   exact (from the API's own facet aggregation, itself a saved response —
   `portal_raw/facet_aggregations/07_nanoaodsim_susy_total.json` and
   `.../06_miniaodsim_category_breakdown.json`), but its per-record
   title/file/event/size detail was not fetched, and its files/events/TB
   are reported as **NOT MEASURED**, not estimated.

**Completeness proof, applied to every fetch used in this report**: after
each paginated fetch, the number of hits actually returned was compared to
`hits.total`, AND the number of *unique* `recid` values was compared to
the same total. Every figure quoted below passed both checks. The full
per-page results (each already de-duplicated in this way) are saved,
`_file_indices`/`files`/`methodology`/`abstract`/and other large unused
free-text fields stripped (see `process_pages.ps1`/`process_mc_pages.ps1`
for exactly which fields and why — `methodology` alone runs ~50 KB per MC
record and drove one intermediate save to >1 GB before this stripping).

**Cross-check against the previously-known 16 data + 29 MC records
(required by this task)**: all 16 of the earlier survey's data record IDs
(30521–30532, 30554–30565) and all 29 of its MC record IDs appear in this
inventory's master table — **confirmed present, not missing** (checked by
recid lookup against `master_table.csv`). The earlier survey was not
*wrong* about what it found; it simply never looked for the other ~480×
more records that also exist.

## 2. Full picture: every CMS Dataset-type record on the portal

| type.secondary | Records |
|---|---:|
| Collision (real data) | 345 |
| Simulated (MC) | 51,365 |
| Derived (educational/reduced/enhanced) | 253 |
| **Total** | **51,963** |

(`portal_raw/facet_aggregations/01_cms_all_types.json`,
`02_cms_collision_dataset_total.json.gz`,
`03_cms_simulated_dataset_total.json`.)

## 3. Collision data — every year and format

### 3.1 pp collisions (329 records)

| Year | Format | Records | Files | Events | Size | CMSSW release |
|---|---|---:|---:|---:|---:|---|
| 2010 | AOD | 26 | 50,388 | 991,487,088 | 53.93 TB | `CMSSW_4_2_8` |
| 2010 | RAW | 4 | 390 | 9,524,698 | 1.27 TB | `CMSSW_4_2_8` |
| 2010 | RECO | 3 | 5,060 | 195,698,408 | 15.82 TB | `CMSSW_3_9_2_patch5` / `CMSSW_4_2_8_lowpupatch1` |
| 2011 | AOD | 35 | 61,509 | 1,309,223,646 | 195.04 TB | `CMSSW_5_3_32` |
| 2011 | RAW | 6 | 735 | 12,340,393 | 2.16 TB | `CMSSW_5_3_32` |
| 2011 | RECO | 7 | 2,237 | 82,931,979 | 9.69 TB | `CMSSW_4_4_7` |
| 2012 | AOD | 94 | 290,587 | 3,663,681,961 | 954.07 TB | `CMSSW_5_3_32` |
| 2012 | RAW | 6 | 1,154 | 13,378,072 | 3.45 TB | `CMSSW_5_3_32` |
| 2013 | RECO (pp reference, alongside the 2013 pPb run) | 10 | 5,183 | 157,127,096 | 20.27 TB | `CMSSW_5_3_20` |
| 2015 | AOD | 50 | 70,055 | 3,937,452,456 | 150.80 TB | `CMSSW_7_6_7` / `CMSSW_7_5_8_patch3` |
| 2015 | MiniAOD | 17 | 21,046 | 912,087,667 | 13.34 TB | `CMSSW_7_6_7` |
| 2016 | MiniAOD | 34 | 19,724 | 2,164,901,833 | 64.20 TB | `CMSSW_10_6_30` |
| **2016** | **NanoAOD** | **32** | **1,254** | **2,096,825,318** | **1.88 TB** | **"Not required"** |
| 2017/2024 | RAW (technical/monitoring streams — see §3.3) | 3 | 0* | 0* | 0* | none listed |
| unlabeled run_period | AOD | 2 | 2,212 | 60,426,678 | 7.51 TB | `CMSSW_5_3_32` |

\* The 2017 `ZeroBias` and 2024 `EphemeralHLTPhysics0/1` RAW records have
no file/event count populated on the portal at all — consistent with
being live-monitoring technical streams, not curated physics releases.

**Run 1 (2010–2012) total: 155 AOD + 16 RAW + 10 RECO (2010+2011 only) =
181 records, 412,060 files, 6,278,266,245 events, 1,235.43 TB.** RAW and
RECO here are separate processing tiers of the same underlying runs, not
additional independent events — the physically distinct event content is
the AOD tier's own 5,964,392,695 events (1,203.04 TB). This predates
NanoAOD entirely — every one of these needs a full CMSSW AOD analyzer.

**2015: 67 records (50 AOD + 17 MiniAOD), matches the year-facet count
exactly.** MiniAOD-level tooling reaches all 17 of these; the 50 AOD
records would additionally need AOD-level support.

**2016 non-NanoAOD: 66 records (34 MiniAOD, matches the year-facet count
exactly, + 32 counted separately as NanoAOD above).**

### 3.2 Heavy-ion collisions (16 records) — a different physics case, not currently considered

| Collision type | Energy | Format | Records | Files | Events | Size | CMSSW |
|---|---|---|---:|---:|---:|---:|---|
| PbPb | 2.76 TeV | RECO | 6 | 39,983 | 132,435,777 | 185.17 TB | `CMSSW_3_9_2_patch5` (2010) / `CMSSW_4_4_7` (2011) |
| pPb | 5.02 TeV | RECO | 9 | 38,423 | 733,740,167 | 199.49 TB | `CMSSW_5_3_20` (2013) |
| Interfill (`/ForwardTriggers/HIRun2011`) | 0 TeV | RECO | 1 | 361 | 409,335 | 0.04 TB | `CMSSW_4_4_7` |

**Heavy-ion total: 16 records, 78,767 files, 866,585,279 events, 384.70
TB — all in RECO format, never AOD/MiniAOD/NanoAOD.** This is a genuinely
different physics regime (nuclear collisions, not the pp physics this
group's object selection, triggers, and combinatorics were built for) and
is flagged here as complete but **out of scope for anything this group is
currently doing**, per the task's own instruction.

### 3.3 What non-NanoAOD would take (REASONING, not measurement — no conversion attempted)

Every AOD/MiniAOD/RECO/RAW release names a specific CMSSW version and
(confirmed directly on a sample record, `system_details.container_images`)
ships a ready-to-pull Docker/Singularity container for it
(`docker.io/cmsopendata/...` and a CERN GitLab mirror) — except the bare
2017/2024 RAW technical streams, which have no CMSSW release or container
listed at all (consistent with never having been processed beyond raw
detector output).

**The shape of the work, reasoned through, not measured:**
- **MiniAOD → flat ntuples/branches we can read**: one CMSSW job per
  dataset (a PAT-tuple analyzer running inside the named container),
  producing the same kind of flat pt/eta/phi/mass branches our current
  NanoAOD selection reads. This is the same *kind* of task CMS itself runs
  to produce NanoAOD from MiniAOD in the first place — the structure of
  the objects (electrons, muons, jets, MET) is already very close to
  NanoAOD's; the work is schema/branch-name translation more than new
  physics logic. Rough compute shape: 802.57 TB of non-SUSY MiniAODSIM +
  77.55 TB of MiniAOD collision data (§3.1) — at typical CMSSW
  MiniAOD-processing throughput (order 10–50 MB/s per core for this era,
  itself **UNVERIFIED** here, no job was run) this is many thousands of
  CPU-hours, comparable in scale to a real production campaign, not a
  weekend job. What could go wrong: CMSSW/container environment quirks
  specific to each named release, dataset-specific corrupt/missing files
  (already a recurring finding throughout this whole project's real-file
  experience), and the same kind of subtle branch-naming/schema mismatches
  already documented for NanoAOD version differences.
- **AOD → the same**: a materially bigger lift — AOD carries far more raw
  reconstruction detail than MiniAOD (hence needing PAT slimming logic
  MiniAOD/NanoAOD already did once, on the real production side, which
  we'd effectively be redoing ourselves), older CMSSW releases
  (`CMSSW_3_9_2_patch5` through `CMSSW_7_6_7`) with correspondingly older
  documentation and community support, and roughly 2,300 TB combined
  (collision + simulation, §3.1 + §4) to work through — several times the
  volume of MiniAOD.
- **RAW → anything**: would need full event reconstruction from detector
  raw data, the heaviest possible lift, and (per §3.1) the only RAW
  records that aren't already a byproduct of an AOD/RECO release with its
  own CMSSW version are the tiny, uncurated 2017/2024 technical streams,
  which are very unlikely to be worth this effort for physics content.
- **Derived/reduced tiers (§4.4)**: lighter to read (already flat,
  NanoAOD-like) but a **different, undocumented-here branch schema** per
  the classification rule — would need per-format branch-name mapping,
  not a CMSSW job.

## 4. Simulation — every campaign, every process group

### 4.1 By format tier (all CMS, `type.secondary:Simulated`)

| Format | Records | Year(s) | Files | Events | Size |
|---|---:|---|---:|---:|---:|
| NanoAODSIM | 21,575 | 2016 only | ≥79,483 (10,679 measured) | ≥13,182,683,386 (10,679 measured) | ≥21.08 TB (10,679 measured) |
| MiniAODSIM | 28,693 | 2015: 7,109 / 2016: 21,584 | ≥610,845 (17,314 measured) | ≥21,178,801,870 (17,314 measured) | ≥802.57 TB (17,314 measured) |
| AODSIM | 859 | 2010: 100 / 2011: 382 / 2012: 377 | 422,533 | 3,898,045,033 | 940.03 TB |
| GEN-SIM-RECO (mostly heavy-ion MC) | 225 | — | — | — | — |
| RAW, GEN-SIM, GEN-SIM-DIGI-RAW, PREMIX (production-tier intermediates) | 13 | — | — | — | — |
| *(GEN-SIM-RECO + the 4 tiny tiers combined)* | **238** | | **114,038** | **759,405,643** | **351.09 TB** |

**No preVFP/APV 2016 UL NanoAODSIM campaign was found** (re-confirmed:
100% of NanoAODSIM records report `date_created` from the single "2016"
bucket, with zero hits for `NanoAODAPVv9`/`HIPM_UL2016` naming variants
searched directly) — matching the earlier survey's own finding, now on a
complete enumeration rather than a partial one.

**"Over 7,000 simulated datasets" in 2015 — confirmed exactly: 7,109
MiniAODSIM records**, all Run1-style (no NanoAODSIM existed for 2015).

### 4.2 By physics category (NanoAODSIM, 21,575 total)

| Category | Records | Notes |
|---|---:|---|
| Supersymmetry | 10,896 | BSM benchmark-point signal samples. **Files/events/size not measured** — exceeds the 10,000-record pagination ceiling (§1), no further facet split available. |
| Higgs Physics | 4,384 | 3,008 Beyond Standard Model + **1,376 Standard Model** (§4.3) |
| Exotica | 4,348 | BSM benchmark-point signal samples (Dark Matter, Gravitons, Leptoquarks, Heavy Gauge Bosons, Contact Interaction, Excited Fermions, Resonances, …) |
| Standard Model Physics | 1,030 | ElectroWeak 430, Top physics 397, Drell-Yan 109, QCD 92, Forward/small-x QCD 2 — **full list in §4.3** |
| Beyond 2 Generations | 683 | BSM |
| B physics and Quarkonia | 216 | |
| Miscellaneous | 18 | |

(MiniAODSIM's category breakdown is the same shape: Supersymmetry 11,379,
Exotica 8,810, Higgs Physics 5,658, Standard Model Physics 1,584, Beyond 2
Generations 921, B physics 271, Physics Modelling 51, Miscellaneous 18,
Heavy-Ion Physics 1 — `portal_raw/facet_aggregations/06_...json`.)

**"Any signal samples" — a genuinely large, previously-unknown-to-this-
project population**: 10,896 (NanoAODSIM SUSY) + 4,348 (Exotica) + 3,008
(BSM Higgs) + 683 (Beyond 2 Generations) = **18,935 BSM benchmark-point
NanoAODSIM signal samples** exist on the portal — none used or previously
known to this project, none relevant to the SM-background-focused work
this group does today, but real and worth knowing about if the group's
scope ever widens.

### 4.3 Full per-sample list — Standard Model Physics + SM Higgs (2,406 NanoAODSIM records, the group directly relevant to this project's work)

**Drell-Yan (109 records)** — far more than the single inclusive sample
the earlier survey found: the inclusive `DYJetsToLL_M-50` (multiple
generators/tunes: `amcatnloFXFX`, `madgraphMLM`, `herwig7`), **HT-binned**
(`M-50_HT-70to100` through `HT-1200to2500`, plus a parallel `M-4to50_HT-*`
low-mass HT-binned family), **jet-multiplicity-binned** NLO samples
(`0J`/`1J`/`2J`, each further split into fine dilepton-mass windows
`MLL_200_400` through `MLL_6000_Inf`), **Z-pT-filtered**
(`LHEFilterPtZ-0To50` through `650ToInf`), and a broad **mass-range**
family (`M-100to200` through `M-2000to3000`). Full list:
`portal_raw/mc_nanoaodsim_by_category/Standard_Model_Physics_p*.json`
(recids 32xxx-6xxxx range) and `master_table.csv` (filter
`title contains "DYJetsToLL"`).

**W+jets (≈20 records)** — again far more than the single inclusive
sample found before: inclusive `WJetsToLNu` (`amcatnloFXFX` and
`madgraphMLM`), **HT-binned** (`HT-70To100` through `HT-2500ToInf`),
**jet-binned** (`0J`/`1J`/`2J` NLO), **pT-filtered**
(`Pt-100To250` through `600ToInf`), and a Sherpa multi-jet-merged sample.

**QCD multijet (92 records)** — the earlier survey's "11 of ~13-15 pT
bins checked" undercounted badly: the true set is **92 distinct samples**,
made of (a) the plain inclusive `QCD_Pt_XXtoYY` family (underscore
naming, 21 records, pT 5 GeV–3.2 TeV, `TuneCP5_13TeV_pythia8`) — this is
the family the existing `mc_qcd_multijet_170to300` group sample came from
— (b) a **parallel, hyphenated `QCD_Pt-XXtoYY` family with additional
enrichment filters** (`MuEnrichedPt5`, `EMEnriched`, `DoubleEMEnriched`
with explicit diphoton mass windows `MGG-40to80`/`MGG-80toInf`, `bcToE`) —
not previously known to exist at all — and (c) an **HT-binned family**
(`QCD_HT50to100` through `HT2000toInf`, each with `BGenFilter`,
`TuneCH3-herwig7`, and `TuneCP5_PSWeights` generator variants), plus
`QCD_bEnriched` and `QCD_pomflux` (diffractive) samples. Total: 2,551
files, 1,352,831,204 events, 2.01 TB.

**Top physics (397 records)** — ttbar (`TTTo2L2Nu`, `TTToSemiLeptonic`,
`TTToHadronic`, `TTJets`, matching the 3 already used plus more),
single top (`ST_t-channel`, `ST_tW`, `ST_s-channel`, matching the 4
already used), plus a large `ttbar+X` family not previously used at all:
`TTZ*` (to LL/QQ/NuNu), `TTW*`, `TTGamma`, `TTGG`, `TTbb`, `tZq`, and a
BSM-adjacent `TTZprimeToTT` resonance-search sample (40 records, tagged
under "Top physics" rather than Exotica).

**ElectroWeak (430 records)** — diboson (`WW`/`WZ`/`ZZ`, all decay
channels, matching the 3 already used) plus triboson (`WWW`, `WWZ`, `WZZ`,
`ZZZ`), vector-boson-scattering/EWK-VBS samples (`EWK_LLJJ`,
`ZZ2JTo2L2Nu2J_EWK_aQGC`), polarized-diboson samples, and photon+jets
(`GJets`, `G1Jet_LHEGpT-*`) — none of these beyond plain WW/WZ/ZZ were
previously used.

**Standard Model Higgs (1,376 records)** — every major production mode
(ggH, VBF, WH+, WH-, ZH, ttH, bbH, THQ) crossed with **every major decay
channel**: H→ZZ (553 records — by far the largest single channel, not
currently used at all), H→WW (206), H→γγ (135 — the only channel this
project currently uses), H→ττ, H→μμ, H→bb, H→Zγ, plus di-Higgs (HH→bb,
HH→ZZ) samples. **H→γγ is a small fraction (~10%) of what's available.**

Full machine-readable detail for all 2,406 of these records:
`master_table.csv`/`master_table.json.gz`, filterable by title, or the
per-category raw pages under
`portal_raw/mc_nanoaodsim_by_category/{Standard_Model_Physics,Higgs_Physics}_p*.json`.

### 4.4 Derived/educational/reduced datasets (253 records, separate from Simulated/Collision)

Type.secondary = `Derived`, not `Collision` or `Simulated`. Formats:
`nanoaod-pf` (83 — real 2016G data enhanced with Particle Flow
candidates), `nanoaodsim-poet` (56 — reduced MC samples "for education
and outreach", includes HT-binned Drell-Yan samples at reduced/simplified
branch content), `nanoaod-run1`/`nanoaodsim-run1` (31 + 3 — Run 1 data/MC
back-ported into a NanoAOD-like flat format), `nanoaod-reduced`/
`nanoaodsim-reduced` (7 + 11), `nanoaod-poet` (2), plus non-analysis
formats (`ig` event-display files ×83 already counted above under
nanoaod-pf's sibling rows — see raw CSV for the exact per-record format
string; `csv`/`json`/`h5`/`xls`/`gz` tabular/summary exports). Total: 253
records, 24,224 files, 3,099,523,316 events, 13.2 TB.
**USABLE WITH WORK at best** (different, reduced, or enhanced branch sets
— none match the current schema as-is); the pure `ig`/`csv`/`json`/`h5`
event-display and tabular exports (roughly 108 of the 253) are
**NOT USABLE** — no full event content.

## 5. Usability classification, with counts

| Class | Records | Files | Events | Size | Why |
|---|---:|---:|---:|---:|---|
| **DIRECTLY USABLE** | 10,711 (measured) + 10,896 (SUSY, count only) = 21,607 | ≥80,737 | ≥15,279,508,704 | ≥22.96 TB | NanoAOD/NanoAODSIM, our existing schema's branch names, confirmed present on real files earlier in this project |
| **USABLE WITH WORK** | 313 (collision AOD/MiniAOD/RECO/RAW, i.e. the 345 collision records minus the 32 NanoAOD already counted above) + 28,693 (MiniAODSIM, 17,314 measured) + 859 (AODSIM) + 145 (Derived, NanoAOD-like but different branches) ≈ **30,010** | — | — | see §3/§4 | Needs CMSSW (AOD/MiniAOD/RECO/RAW, §3.3) or a branch-name mapping (Derived tier) |
| **NOT USABLE** | 238 (GEN-SIM-RECO/GEN-SIM/RAW/PREMIX production intermediates) + ~108 (Derived event-display/tabular) ≈ **346** | — | — | — | No full event content, or purely intermediate production artifacts never meant for analysis |

Every count above is exact except where explicitly marked "measured"
subsets within a larger exact total (the Supersymmetry gap, §1).
Reconciliation: 21,607 + 30,010 + 346 = 51,963, matching §2's total
exactly.

## 6. "What this changes"

**How much of what CMS has released is reachable by us today, and what
fraction that is**: 21,607 of 51,963 total CMS Dataset-type records
(**~42% by record count** — almost entirely because of the ~19,000 BSM
NanoAODSIM benchmark samples we have no use for) are NanoAOD/NanoAODSIM
and readable with zero new work. By **volume**, though, NanoAOD/NanoAODSIM
is only **~23 TB of the ~4,006 TB this inventory measured in total**
(collision 1,878 TB, heavy-ion already included in that figure, +
simulation detailed 2,115 TB + Derived 13 TB; Supersymmetry's volume is
not measured, §1, so the true total is somewhat larger) — **well under
1%**. Almost everything CMS has released, by data volume, is in a format
we cannot read today.

**Ranked by what would unlock the most** (REASONING — a size/effort
read, not a recommendation to build any of it):

1. **MiniAOD support** — unlocks 2015 (7,109 MC samples, 67 collision
   records) and the rest of 2016 (21,584 MC samples via MiniAODSIM,
   34 collision records) — **~880 TB, ~28,700 MC records + 51 data
   records** for what is architecturally the *smallest* step up from
   NanoAOD (§3.3): MiniAOD's object content is already close to
   NanoAOD's, just not yet flattened into the same branch names. This
   is the unlock the user flagged as the likely biggest lever, and the
   size numbers here support that read.
2. **AOD support** — unlocks all of Run 1 (2010–2012: 181 collision
   records, 859 MC records) plus the AOD half of the 2015 release (50
   collision records) — **~2,300 TB combined**, the single largest pool
   by volume, but requiring the heavier AOD-to-flat-branches lift
   (§3.3).
3. **RECO support** — mostly the heavy-ion program (§3.2, 385 TB, a
   different physics case) plus a modest pp slice (2010/2011, ~25 TB)
   already subsumed by AOD access once that exists.
4. **RAW support** — not worth pursuing: the only RAW records not
   already covered by an AOD/RECO release with real physics content are
   small, uncurated 2017/2024 technical monitoring streams.

**How many MC samples the earlier survey missed, and of what kind**: it
found 29 of 21,575 NanoAODSIM records (0.13%) and entirely missed
MiniAODSIM (28,693), AODSIM (859), and every BSM signal category. Within
the 2,406 Standard-Model-relevant NanoAODSIM records specifically (the
fair comparison — the earlier survey was never trying to find BSM
samples), it found 29 of 2,406 (1.2%): it had the right *processes*
(ttbar, Drell-Yan, W+jets, diboson, single top, QCD, H→γγ) but only ever
found each process's single plainest/inclusive sample, missing every
HT-bin, jet-bin, mass-bin, and enrichment-filter variant, and missing
every other Higgs decay channel entirely (H→ZZ alone, at 553 records, is
larger than the entire previously-known MC table).

**Reasoning on whether the missed samples populate new final states**:
almost certainly yes, for two different reasons that don't require
running anything to see. First, physically: the HT/pT/mass-binned QCD and
Drell-Yan/W+jets samples exist specifically to give usable statistics in
*regions the inclusive sample under-populates* (very high jet HT, very
high dilepton mass, very high vector-boson pT) — by construction, their
whole purpose is to reach event populations the single inclusive sample
this project already uses does not reach at all. Second, structurally:
per this project's own earlier finding (`CEILING_REPORT.md`) that the
distinct-histogram count **saturates with statistics** for a *fixed*
selection and object menu, more inclusive-sample statistics would not
have helped much — but a materially different production-mode/decay-
channel/kinematic-bin sample (e.g. H→ZZ→4ℓ, an entirely different final
state from H→γγ) is not "more of the same sample," and would very likely
add new BumpNet histogram names rather than just refill existing ones
more precisely.

## 7. Standing notes

- **UNVERIFIED, by design of this task's scope**: whether any AOD/MiniAOD/
  RECO record is actually openable/parseable with the tooling this
  project has today — no file was opened, per the task's own out-of-scope
  list.
- **UNVERIFIED**: CMSSW MiniAOD/AOD processing throughput used in §3.3's
  compute-cost reasoning — a plausible order-of-magnitude figure, not
  measured.
- **INFERRED**: which of the Derived tier's `csv`/`json`/`ig`/`h5` records
  genuinely carry zero usable event content versus a reduced-but-real
  subset — based on the format name and portal convention (educational/
  event-display exports), not opened to confirm.
- **Not investigated (explicitly out of scope)**: physical de-duplication
  of events shared between the newly-found primary datasets (e.g.
  DoubleMuonLowMass vs DoubleMuon likely share triggered events the way
  DoubleMuon/MuonEG already do, per the earlier triggered-run report) —
  this inventory counts records and their stated event totals, not
  physical, de-duplicated event content.
- **Surprising, confirmed findings, collected in one place**: (1) 16
  additional 2016 NanoAOD primary datasets nobody had found
  (`DoubleMuonLowMass` among them — directly relevant to this project's
  own previously-flagged unexplained sub-1 GeV dimuon population); (2)
  the portal's default pagination silently drops/duplicates records past
  a few hundred results, and silently returns empty past 10,000 — a
  methodology hazard for any future portal query, not just this one; (3)
  Run 2017 and even Run 2024 (Run 3!) collision data exists on the
  portal, in RAW form only, as small technical streams; (4) ~19,000 BSM
  benchmark-point NanoAODSIM signal samples exist and were completely
  unknown to this project; (5) H→ZZ has more available NanoAODSIM
  samples (553) than this project's entire current H→γγ sample (135).

## Evidence map

- `portal_raw/facet_aggregations/` — the exact API queries and their raw
  aggregation responses backing every top-level count in this report
  (total CMS records, Collision/Simulated/Derived split, format-tier
  breakdowns, category breakdowns, the Supersymmetry gap).
- `portal_raw/data/` — all 345 CMS collision-dataset records, complete
  and de-duplication-verified (gzipped).
- `portal_raw/mc_nanoaodsim_by_category/`,
  `portal_raw/mc_miniaodsim_by_category/`, `portal_raw/mc_aodsim/`,
  `portal_raw/mc_othertiers/` — every Simulated-type record this report
  measured individually (everything except the two Supersymmetry
  buckets), partitioned exactly as fetched.
- `master_table.csv` / `master_table.json.gz` — the single combined
  machine-readable table (29,688 rows: every collision record, every
  individually-fetched Simulated record, every Derived record), each row
  carrying recid, title, type, formats, files, events, size, run_period,
  DOI, and a usability-class note.
- `process_pages.ps1` / `process_mc_pages.ps1` / `build_master_table.ps1`
  — the exact, reproducible processing steps from raw API response to
  the tables above (field-stripping list and why, documented inline).
