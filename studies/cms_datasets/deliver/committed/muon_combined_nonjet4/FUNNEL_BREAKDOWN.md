# nonjet4 combined delivery: full funnel breakdown (read-only)

Computed directly from the full-run shards (DoubleMuon nonjet4 inclusive,
57 files + SingleMuon nonjet4 exclusive, 152 files -- pooled per
histogram name exactly as `build_muon_combined_delivery.py --version
nonjet4` itself does). **Read-only**: the per-final-state prune (which
mutates its input files) was run ONLY on throwaway scratch copies in a
temp directory, never on the real shards under `runs_matched_nonjet4/`;
nothing under any existing output directory was modified. Script:
`scripts/funnel_breakdown_readonly.py`; full evidence:
`funnel_breakdown_readonly.json`.

## The funnel

| Stage | Description | Combined (delivered) |
|---|---|---|
| (a) | Distinct histogram names (combination x final-state category) with >=1 pooled raw event, before any cut | **224** |
| (a2) | Of those, names whose OWN pooled raw array has >=100 entries (a per-name threshold) | **187** |
| (b) | After the real >=100-events-per-final-state prune | **187** |
| (c) | After post-processing (Z-peak cut, max-mass cut, rightmost-peak selection, first-empty-bin split), requiring >=100 events in the resulting main range | **180** |
| (d) | Of (c), >25 filled bins on the fixed grid (min26bins) | **159** |
| (d') | Of (c), >30 filled bins on the fixed grid (min31bins) | **148** |

**(b), (c), (d), (d') exactly match `build_summary_nonjet4.json`'s own
recorded numbers (187, 180, 159, 148)** -- confirmed by re-running the
same shared funnel code (`run_funnel_at_threshold`, `make_fixed_grid_histogram`,
the same `BINS_THRESHOLD_A`/`BINS_THRESHOLD_B`/`MIN_BUMPNET_EVENTS`
constants) on the same pooled shards, a reproducibility check rather than
an independent reimplementation.

## (a2) vs (b): same count, and the same SET

(a2)'s per-NAME threshold (187) exactly equals (b)'s per-FINAL-STATE
threshold (187) -- and it's not just a matching count, the two stages
keep the exact same 187 histogram names (verified directly: 0 names in
one but not the other). This isn't a general guarantee of the pruning
logic (a final state can host multiple combinations with different
subleading-object requirements, so a combination's own raw array COULD
in principle be smaller than its final state's own event population) --
it just happens to hold exactly for every one of the 224 stage-(a) names
in this dataset, because within each final-state category every event
has exactly the object counts the category label specifies, so almost
every combination built from those objects is computable for every event
in the category (no partial availability).

Attrition through the rest of the funnel: 224 -> 187 (37 names dropped by
the per-name/per-final-state >=100-raw-event threshold) -> 180 (7 more
dropped by post-processing's own >=100-main-events requirement) -> 159
(21 more fall short of the >25-filled-bin floor) -> 148 (a further 11
fall short of the stricter >30-filled-bin floor; every min31bins name is
also a min26bins name, since 148 < 159 and the >30 condition implies
>25).

## Stage (a), per dataset alone

| Population | Distinct names with >=1 event |
|---|---|
| Combined (DoubleMuon inclusive + SingleMuon exclusive, pooled) | 224 |
| DoubleMuon alone (inclusive, all 57 files) | 102 |
| SingleMuon alone (inclusive, all 152 files) | 224 |

SingleMuon alone already reaches the full 224 -- every histogram name
that ever appears in the combined delivery has at least one raw event
from SingleMuon somewhere in its own (larger, lower-priority) dataset;
DoubleMuon alone only reaches 102, since it has far fewer events overall
(9.4M vs. 163M accepted) and a higher trigger threshold (2 matched
muons), so it never populates some of the rarer/lower-multiplicity
categories at all (rows do not add up -- this is the same non-additivity
already noted in `NONJET4_REPORT.md`'s own count table, one level
earlier in the funnel).
