# The histogram name endings now match upstream exactly (`_width_10.0`)

A small, purely cosmetic correction to the muon delivery for BumpNet: the
last part of every histogram name. **No histogram content changed at all** —
same bins, same entries, same everything. Only the names end differently.

Every number below is labelled **VERIFIED BY RUNNING** (produced or checked
in this session, with the method named) or **UNVERIFIED**.

**The file for Maryna:**
`muon_combined_matched_vB_upstreamnames_w10p0_bumpnet_cropped.root` in
`/storage/agrp/berkom/atlas-utilization/output/cms_datasets/deliver/muon_combined_vB_upstreamnames_w10p0_20261006/`.
A `README.txt` beside it says the same; a copy is committed here at
[`evidence/README_w10p0.txt`](evidence/README_w10p0.txt).

---

## 1. What changed, and why

Every histogram name ends with the bin width it was made with. Ours ended
`_width_10`. Upstream's end `_width_10.0`. Matan's decision is that our names
must match upstream exactly, so ours now do.

**Before → after** (nothing else in the name moved):

| | |
|---|---|
| before | `ROI_mass_m0m1_cat_0ex_2mx_5jx_1bx_width_10` |
| after | `ROI_mass_m0m1_cat_0ex_2mx_5jx_1bx_width_10.0` |

### Why upstream writes `10.0` and not `10`

I read upstream's own code at commit `88d7a4b` rather than taking it on
trust, and then ran it. **VERIFIED BY RUNNING** (loading upstream's own
`config.yaml` and evaluating its f-string):

- Upstream builds the whole name in one place,
  `services/pipelines/histograms_pipeline.py`, as
  `f"ROI_{hist_name_base}_width_{bin_width}"` — the identical line appears
  four times (lines 343, 380, 520, 650).
- `bin_width` comes straight from the configuration and is **never
  converted**: `bin_widths_gev = [histograms_config["bin_width_gev"]]`.
- That configuration value is a **decimal number, not a whole number**:
  `config.yaml` line 170 says `bin_width_gev: 10.0`, which loads as a Python
  float (I printed its type to confirm), and `domain/config.py` line 205
  declares it as `bin_width_gev: float = 10.0`.

Python writes a float `10.0` into text as `"10.0"`. So upstream's name ends
`_width_10.0`.

Ours had been built as `f"ROI_{name}_width_{int(BIN_WIDTH_GEV)}"` — that
`int(...)` turned 10.0 into 10, which is the whole difference.

### How it is built now

Not by hard-coding `"10.0"`. The suffix is now *formatted from the configured
bin width*, exactly the way upstream formats it. A different configured width
gives a different suffix automatically — the tests check this with 5.0 and
2.5 as well as 10.0, so it is demonstrably one general rule and not a special
case for 10.

### Old delivery modes are untouched

The new behaviour is behind a switch that is **off by default**. Every
pre-existing way of running the delivery still produces exactly what it
produced before, including the old `_width_10` names. That is not just
asserted — it was proven on a real build (section 2).

---

## 2. Every check, and whether it passed

### Tests committed with the code — **all pass, VERIFIED BY RUNNING**

`studies/cms_datasets/tests/test_width_suffix.py`:

- our suffix builder compared against **upstream's own f-string** for bin
  widths **10.0, 5.0 and 2.5** — all equal;
- the **full name** for several sample signatures equal to the full name
  upstream's rule produces from the same parts, including
  `ROI_mass_m0m1_cat_0ex_2mx_5jx_1bx_width_10.0`;
- the default form is still exactly `_width_10`, and the two forms differ
  only by the trailing `.0`.

The earlier suites still pass unchanged: `test_upstream_names.py`,
`test_exact_jet_labels.py`, and the m0m1j0 study tests.

### Old invocation unchanged — proven on a real build

A pre-existing invocation (no new switches at all) was re-run with the new
code on the pilot shards and compared against the file that same invocation
produced on 5 October. **Identical: 347 histograms, same names, same bin
contents, same bin edges, 984,547 entries on both sides, nothing missing and
nothing extra** (**VERIFIED BY RUNNING**,
[`evidence/compare_D_width_regression.json`](evidence/compare_D_width_regression.json)).

### The rebuilt delivery — all checks pass, on both files

Checked by reading the **real ROOT files** back, not by trusting the builder
(**VERIFIED BY RUNNING**,
[`evidence/width_suffix_checks.json`](evidence/width_suffix_checks.json)):

| check | uncropped | cropped |
|---|---|---|
| exactly **1,496** histograms | PASS | PASS |
| every histogram is a genuine `TH1F` | PASS | PASS |
| every name ends `_width_10.0` | PASS | PASS |
| names are the current delivery's names with only the suffix swapped | PASS | PASS |
| mapping is one-to-one; no duplicates | PASS | PASS |
| **nothing but the suffix differs** in any name | PASS | PASS |
| bin contents identical for all 1,496 | PASS | PASS |
| bin edges identical for all 1,496 | PASS | PASS |
| entries identical for all 1,496 | PASS | PASS |
| total entries across the file | **78,754,866** on both sides | **78,754,866** on both sides |
| every name reproduced by **upstream's own naming rule** from its own parts | PASS | PASS |
| each histogram's **internal ROOT name equals its key name** | PASS — 0 mismatches | PASS — 0 mismatches |

On the last one: ROOT objects carry a name of their own as well as the key
they are stored under, and the two can drift apart. They do not here — every
one of the 1,496 matches in both files, so nothing was reported.

---

## 3. Counts, before and after

Unchanged, as intended (**VERIFIED BY RUNNING**, both build summaries):

| | current `_width_10` delivery | new `_width_10.0` delivery |
|---|---|---|
| histograms | 1,496 | 1,496 |
| distinct final states | 81 | 81 |
| total entries | 78,754,866 | 78,754,866 |
| histograms with >=25 filled bins | 1,258 | 1,258 |
| per-histogram minimum entries | 1 (upstream rule) | 1 (upstream rule) |
| final states passing ">=100 events per final state" | 1,496 | 1,496 |
| name ending | `_width_10` | **`_width_10.0`** |

The delivery was rebuilt from the same 5 October production shards with the
same settings; the shards were opened read-only and the pruning step ran only
on scratch copies. The per-file production jobs were not re-run.

---

## 4. One thing noticed in passing, not changed

`studies/cms_coverage/deliver/make_crop_comparison_plot.py` — a plotting
helper belonging to the **earlier coverage delivery**, not to the muon
delivery — already built its lookup name with the decimal form
(`_width_10.0`), while the delivery it reads was written with `_width_10`. So
that helper cannot currently find its histograms. It is a pre-existing bug in
older tooling, unrelated to this task and outside its scope, so it was left
alone and is recorded here instead.

The equivalent helper on the muon delivery path *was* fixed as part of this
work: it no longer hard-codes either form, and instead takes the name from
the delivery's own manifest or finds whichever form the file actually
contains.

---

## 5. Where everything is

| what | where |
|---|---|
| branch | `feature/upstream-names-no-hist-min` (not merged into master) |
| pinned commit for the rebuild | `4640c47` |
| pinned checkout | `/storage/agrp/berkom/atlas-utilization/checkouts/4640c47/repo` |
| **the delivery** | `.../output/cms_datasets/deliver/muon_combined_vB_upstreamnames_w10p0_20261006/` |
| **the file for BumpNet** | `muon_combined_matched_vB_upstreamnames_w10p0_bumpnet_cropped.root` |
| uncropped companion (cross-checks only) | `muon_combined_matched_vB_upstreamnames_w10p0_bumpnet.root` |

The cropped file is the one BumpNet needs, because it requires a non-empty
first bin. The uncropped file is on the full fixed 0–10000 GeV grid and is
for cross-checking and plotting.

The previous `_width_10` delivery
(`muon_combined_vB_upstreamnames_20261006/`) is left exactly as it was.
