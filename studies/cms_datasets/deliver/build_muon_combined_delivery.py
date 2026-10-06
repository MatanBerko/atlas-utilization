#!/usr/bin/env python
"""
Build the combined DoubleMuon+SingleMuon matched-trigger BumpNet delivery
(top-4 task, Step 5; extended by the nonjet4 task, Step 5, for
--version nonjet4; extended again by the rare4 task, Step 5, for
--version rare4). ONE version at a time
(--version normal|top4|nonjet4|rare4).

Combination rule (Matan's decision, unchanged from the design task): per
signature, pool DoubleMuon's INCLUSIVE raw masses with SingleMuon's
EXCLUSIVE raw masses (DoubleMuon is veto priority 1 -- inclusive==
exclusive for it; SingleMuon is priority 2, so its own EXCLUSIVE shard is
already "not already covered by DoubleMuon's acceptance"), then run the
SAME unchanged post-processing chain as every earlier per-dataset
delivery in this study.

Reuses, unmodified (same imports as
studies/cms_datasets/deliver/build_dataset_delivery.py):
  - services.storage.sqlite_shards: list_signatures
  - studies.cms_coverage.cluster.merge_and_count: PRIMARY_MIN_EVENTS_PER_FS,
    MIN_BUMPNET_BINS, MIN_BUMPNET_EVENTS, copy_shards, run_funnel_at_threshold,
    object_content_category, object_count, SIG_PATTERN
  - studies.cms_coverage.deliver.crop_bumpnet_root: crop_arrays
  - studies.m0m1j0_cms.histograms: _convert_to_bumpnet_name,
    make_fixed_grid_histogram, to_writable_th1f, verify_written_th1f,
    BIN_WIDTH_GEV, FIXED_MASS_MIN_GEV, FIXED_MASS_MAX_GEV
  - build_dataset_delivery's own build_sig_to_bumpnet/write_root_file/
    write_cropped_root_file/manifest_entry (imported directly, not
    reimplemented, so this can never silently diverge from how the
    per-dataset deliveries build the same things).

The only genuinely new logic here is WHICH shard files get pooled
together (DoubleMuon inclusive across all 57 files + SingleMuon exclusive
across all 152 files, for one --version at a time) -- everything after
that point is the existing, shared funnel.

Usage:
    python build_muon_combined_delivery.py --version normal \
        --runs-matched-dir /storage/.../output/cms_datasets/runs_matched \
        --out-dir /storage/.../output/cms_datasets/deliver/muon_combined \
        --out-prefix muon_combined_matched
    python build_muon_combined_delivery.py --version top4 \
        --runs-matched-dir /storage/.../output/cms_datasets/runs_matched \
        --out-dir /storage/.../output/cms_datasets/deliver/muon_combined \
        --out-prefix muon_combined_matched_top4
    python build_muon_combined_delivery.py --version nonjet4 \
        --runs-matched-dir /storage/.../output/cms_datasets/runs_matched_nonjet4 \
        --out-dir /storage/.../output/cms_datasets/deliver/muon_combined_nonjet4 \
        --out-prefix muon_combined_matched_nonjet4
    python build_muon_combined_delivery.py --version rare4 \
        --runs-matched-dir /storage/.../output/cms_datasets/runs_matched_rare4 \
        --out-dir /storage/.../output/cms_datasets/deliver/muon_combined_rare4 \
        --out-prefix muon_combined_matched_rare4

nonjet4 task, Step 5 addition: a third `--version nonjet4` choice, reading
`dataset_shard_nonjet4_inclusive/exclusive.sqlite` instead of the normal/
top-4 shard names -- everything else (the funnel, thresholds, cropping,
manifest/summary format) is the exact same shared code path, untouched.
`--runs-matched-dir` for this version points at the nonjet4 production
output directory (`runs_matched_nonjet4/`), which carries its own copies
of `DoubleMuon_index.json`/`SingleMuon_index.json` (identical content to
`runs_matched/`'s, since the file lists never changed).

rare4 task, Step 5 addition: a fourth `--version rare4` choice, reading
`dataset_shard_rare4_inclusive/exclusive.sqlite`. Same shared funnel/
thresholds/cropping/manifest code, untouched; `--runs-matched-dir` points
at `runs_matched_rare4/`, which likewise carries its own copies of the
two index JSON files.

exact-jet-labels task, B4 addition: an OPTIONAL `--no-filled-bin-cut`
flag. The group has decided that the ">=25 filled bins" requirement is
applied by Maryna on the BumpNet side during smoothing, NOT in this
pipeline, so a delivery built with this flag applies NO filled-bin
threshold at all and writes ONE histogram set instead of the previous two
(no more separate ">25"/">30" files):

    python build_muon_combined_delivery.py --version rare4         --no-filled-bin-cut         --runs-matched-dir /storage/.../output/cms_datasets/runs_matched_vB_exactlabels_20261005         --out-dir /storage/.../output/cms_datasets/deliver/muon_combined_vB_exactlabels_20261005         --out-prefix muon_combined_matched_vB_exactlabels

Everything that survives the existing chain is delivered: the
>=100-events-per-final-state prune, the Z cut, the max-mass cut, peak
removal, the outlier split, and the existing per-histogram
>=100-main-entries requirement -- ALL unchanged. Only the bin-count
classification step is skipped. Output is the same two forms as every
earlier delivery, `<prefix>_bumpnet.root` (uncropped) and
`<prefix>_bumpnet_cropped.root`; BumpNet needs the CROPPED one, because
it requires a non-empty first bin. A README.txt saying exactly that is
written next to them.

The flag is OFF by default, so every pre-existing invocation -- including
`--version normal`, `top4` and `nonjet4` -- produces byte-for-byte what it
produced before: the same two min31bins/min26bins files, the same
manifests, the same build-summary key names. The flag only ADDS a code
path; it changes nothing on the old one.

upstream-names task additions -- two further OPTIONAL flags, both OFF by
default, so every pre-existing invocation is again unaffected:

  --legacy-gt-labels   The shards written before the name-format change
      carry labels in the old six-field form `0e_2m_5j_0g_0t_1b`. With this
      flag their final-state strings are converted to the upstream form
      `0e_2m_5j_1b` as they are read, so the full muon delivery can be
      rebuilt in the new naming WITHOUT re-running the 209 per-file jobs.
      The conversion is strict: it drops `0g`/`0t` tokens only, ABORTS if
      any label carries a non-zero photon or tau count (which cannot
      happen -- no selected photons or taus exist in this study and none of
      the 186 combinations uses them), and afterwards asserts that no two
      distinct names collapsed onto one. See convert_legacy_fs_label.

  --no-hist-min-entries   Drops this delivery's extra requirement of >=100
      main entries per individual histogram (Maryna's decision (2):
      BumpNet re-checks it during smoothing). What replaces it is exactly
      what upstream's own histogram stage does -- NO minimum at all, with a
      signature skipped only when it has no data whatsoever. See
      run_funnel_at_threshold's `min_main_entries` and _deliver_min_entries.
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

import numpy as np  # noqa: E402

from services.storage.sqlite_shards import list_signatures  # noqa: E402
from studies.cms_coverage.cluster.merge_and_count import (  # noqa: E402
    PRIMARY_MIN_EVENTS_PER_FS,
    MIN_BUMPNET_BINS,
    MIN_BUMPNET_EVENTS,
    copy_shards,
    run_funnel_at_threshold,
)
from studies.m0m1j0_cms.histograms import (  # noqa: E402
    make_fixed_grid_histogram,
    BIN_WIDTH_GEV,
    FIXED_MASS_MIN_GEV,
    FIXED_MASS_MAX_GEV,
)
from studies.cms_datasets.deliver.build_dataset_delivery import (  # noqa: E402
    build_sig_to_bumpnet,
    write_root_file,
    write_cropped_root_file,
    manifest_entry,
    BINS_THRESHOLD_A,
    BINS_THRESHOLD_B,
)

# upstream-names task, (2): what upstream's histogram stage does for
# histograms with very few or zero entries. Read from upstream
# services/pipelines/histograms_pipeline.py at commit 88d7a4b:
# `_iter_signature_chunks` yields only chunks with `len(arr) > 0`, and both
# `_create_histograms_for_signature` and
# `_create_merged_histograms_from_sqlite_signatures` end with
# `if not has_data: return []`. So upstream applies NO minimum entry count
# whatsoever -- it writes a histogram whenever at least one value exists and
# writes nothing when none does. One entry is therefore the matching floor.
UPSTREAM_MIN_ENTRIES_PER_HISTOGRAM = 1

LEGACY_DROPPED_LETTERS = ("g", "t")


def convert_legacy_fs_label(fs_str: str) -> str:
    """Convert a pre-change six-field final-state label to the upstream form.

    `0e_2m_5j_0g_0t_1b` -> `0e_2m_5j_1b`: the photon and tau fields are
    dropped, every other field is left exactly as it is (including two-digit
    counts such as `11j`). Field order is preserved, so the result is
    identical to what the driver now writes natively.

    STRICT by design. It raises rather than guess if a label is not of the
    expected shape, and in particular it ABORTS on a non-zero photon or tau
    count. That must never happen: this study selects no photons and no
    taus, so those counts are structurally always zero -- but silently
    dropping a non-zero count would merge genuinely different final states,
    so it is made loud instead of silent."""
    tokens = fs_str.split("_")
    kept = []
    for token in tokens:
        if len(token) < 2 or not token[:-1].isdigit():
            raise ValueError(
                f"legacy final-state label {fs_str!r} has an unparsable field "
                f"{token!r}; expected <count><letter> fields joined by '_'"
            )
        count, letter = int(token[:-1]), token[-1]
        if letter in LEGACY_DROPPED_LETTERS:
            if count != 0:
                raise ValueError(
                    f"REFUSING to convert legacy final-state label {fs_str!r}: it "
                    f"carries a NON-ZERO '{letter}' count ({count}). This study "
                    f"selects no photons and no taus, so this must never happen. "
                    f"Dropping the field would merge distinct final states."
                )
            continue
        kept.append(token)
    if not kept:
        raise ValueError(f"legacy final-state label {fs_str!r} converted to nothing")
    return "_".join(kept)


def assert_no_name_collisions(sig_to_bumpnet_legacy: dict, sig_to_bumpnet_new: dict):
    """After legacy conversion, two distinct old histogram names must never
    have collapsed onto one new name."""
    old_names = {v[0] for v in sig_to_bumpnet_legacy.values()}
    new_names = {v[0] for v in sig_to_bumpnet_new.values()}
    if len(new_names) != len(old_names):
        pairs = {}
        for sig, (new_name, _fs, _im) in sig_to_bumpnet_new.items():
            pairs.setdefault(new_name, set()).add(sig_to_bumpnet_legacy[sig][0])
        clashes = {n: sorted(o) for n, o in pairs.items() if len(o) > 1}
        raise AssertionError(
            f"legacy name conversion collapsed {len(old_names)} distinct names onto "
            f"{len(new_names)}; colliding examples: {list(clashes.items())[:3]}"
        )
    return len(new_names)


SHARD_NAMES_BY_VERSION = {
    "normal": {
        "doublemuon": "dataset_shard_inclusive.sqlite",
        "singlemuon": "dataset_shard_exclusive.sqlite",
    },
    "top4": {
        "doublemuon": "dataset_shard_top4_inclusive.sqlite",
        "singlemuon": "dataset_shard_top4_exclusive.sqlite",
    },
    "nonjet4": {
        "doublemuon": "dataset_shard_nonjet4_inclusive.sqlite",
        "singlemuon": "dataset_shard_nonjet4_exclusive.sqlite",
    },
    "rare4": {
        "doublemuon": "dataset_shard_rare4_inclusive.sqlite",
        "singlemuon": "dataset_shard_rare4_exclusive.sqlite",
    },
}


def gather_shard_paths(runs_matched_dir: Path, version: str):
    dm_index = json.loads((runs_matched_dir / "DoubleMuon_index.json").read_text())
    sm_index = json.loads((runs_matched_dir / "SingleMuon_index.json").read_text())
    shard_names = SHARD_NAMES_BY_VERSION[version]

    dm_paths = []
    for idx in dm_index:
        p = runs_matched_dir / "DoubleMuon" / f"job_{idx}" / shard_names["doublemuon"]
        if not p.exists():
            raise RuntimeError(f"missing DoubleMuon shard: {p}")
        dm_paths.append(str(p))

    sm_paths = []
    for idx in sm_index:
        p = runs_matched_dir / "SingleMuon" / f"job_{idx}" / shard_names["singlemuon"]
        if not p.exists():
            raise RuntimeError(f"missing SingleMuon shard: {p}")
        sm_paths.append(str(p))

    return dm_paths, sm_paths


README_TEMPLATE = """BumpNet delivery -- Version B (rare4), EXACT light-jet final states
===================================================================

WHICH FILE TO USE
-----------------
    {cropped}

That is the file for BumpNet. It is the CROPPED one: every histogram has
been trimmed to its first..last filled bin, so the first bin is never
empty, which is what BumpNet requires.

    {uncropped}

is the same {n_delivered} histograms UNCROPPED, on the full fixed
0-10000 GeV grid. It is for cross-checking and plotting only; do not feed
it to BumpNet.

WHAT IS IN IT
-------------
{n_delivered} histograms over {n_final_states} distinct final-state
categories, on the unchanged fixed grid: 0-10000 GeV in 10 GeV bins.

THREE THINGS ARE DIFFERENT FROM THE 1 OCT DELIVERY
--------------------------------------------------
1. EXACT LIGHT-JET FINAL STATES. Each light-jet multiplicity has its own
   final state. Before 5 Oct any count above 4 was written as "4", so
   events with 5, 6, 7 ... light jets were all filed under "4j" and their
   masses were merged into the 4j histograms. There are now separate 5j,
   6j, 7j ... final states.

1b. NAME FORMAT: names now contain ONLY the configured object types --
   electrons, muons, light jets and b-jets -- in the upstream pipeline's
   own order, e.g. 0ex_2mx_5jx_1bx. The always-zero photon and tau fields
   (0gx, 0tx) are gone. This matches exactly what the main upstream
   pipeline produces for this configuration. Old name -> new name:
   mass_m0m1_cat_0ex_2mx_5jx_0gx_0tx_1bx -> mass_m0m1_cat_0ex_2mx_5jx_1bx.

2. Z-PEAK CUT 115 -> 110 GeV, so the cut lands on a 10 GeV bin edge
   instead of in the middle of a bin. Follows upstream commit 8120fb8
   (PR #27). It affects same-flavour dilepton channels only. The outlier
   split (the cut at the first empty bin in the high-mass tail) is
   likewise now aligned to the same fixed 10 GeV grid starting at 0.

3. NO FILLED-BIN CUT. Earlier deliveries shipped two files, one requiring
   more than 30 filled bins and one more than 25. This delivery applies NO
   filled-bin requirement at all, because that cut is applied on the
   BumpNet side during smoothing. There is therefore ONE histogram set,
   not two.

   For information only, of the {n_delivered} delivered histograms:
     - {n_ge25} have 25 or more filled bins (what BumpNet's own cut keeps)
     - {n_gt25} have more than 25 filled bins (the old min26bins rule)
     - {n_gt30} have more than 30 filled bins (the old min31bins rule)

WHAT IS UNCHANGED
-----------------
Object definitions, trigger matching, de-duplication, the golden-JSON run
filter, the Version B reject rule (reject an event if electrons + muons +
b-jets > 4, otherwise keep ALL selected light jets), the 186 combinations,
the fixed 10 GeV binning, the >=100-events-per-final-state rule, the
max-mass cut, and peak removal.

PER-HISTOGRAM MINIMUM
---------------------
{min_entries_note}

Combination rule (unchanged): per signature, DoubleMuon INCLUSIVE raw
masses pooled with SingleMuon EXCLUSIVE raw masses.

Built from {n_dm} DoubleMuon and {n_sm} SingleMuon per-file shards.
"""


def _deliver_min_entries(args) -> int:
    """How many entries a histogram needs to be delivered.

    Default (unchanged): MIN_BUMPNET_EVENTS, i.e. 100. With
    --no-hist-min-entries: UPSTREAM_MIN_ENTRIES_PER_HISTOGRAM, i.e. 1 --
    matching upstream, which applies no minimum and only skips a signature
    that has no data at all."""
    return (UPSTREAM_MIN_ENTRIES_PER_HISTOGRAM
            if getattr(args, "no_hist_min_entries", False) else MIN_BUMPNET_EVENTS)


def _build_no_bin_cut_delivery(args, out_dir: Path, dm_paths, sm_paths, sig_to_bumpnet,
                               stage_b_names, stage_c_survivors, stage_d_survivors,
                               im_str_by_name, all_hists, n_nonempty_by_name,
                               n_events_by_name, funnel_diagnostics: dict) -> None:
    """exact-jet-labels task, B4: write ONE histogram set with NO filled-bin
    threshold, in the same two forms as every earlier delivery (uncropped +
    cropped).

    What is delivered: every stage-c survivor -- i.e. everything that got
    through the >=100-events-per-final-state prune, the Z cut, the max-mass
    cut, peak removal, the outlier split AND the existing per-histogram
    >=100-main-entries requirement. That last rule is deliberately left
    EXACTLY as it was (it is an open question for Maryna); this function only
    COUNTS what it excludes, and reports it.

    The ">=25 filled bins" figure is reported for information only, because
    that is the cut BumpNet applies on its own side during smoothing. It does
    NOT filter anything written here.

    Reuses write_root_file / write_cropped_root_file / manifest_entry from
    build_dataset_delivery unmodified, so these files are built by exactly the
    same code as every earlier delivery."""
    min_entries = _deliver_min_entries(args)
    delivered = sorted(
        n for n in stage_c_survivors if n_events_by_name[n] >= min_entries
    )
    excluded_by_hist_min_events = sorted(
        (n, n_events_by_name[n]) for n in stage_c_survivors
        if n_events_by_name[n] < min_entries
    )

    # Informational only -- BumpNet applies its own cut; nothing is filtered here.
    n_ge25_filled = sum(1 for n in delivered if n_nonempty_by_name[n] >= 25)
    n_gt25_filled = sum(1 for n in delivered if n_nonempty_by_name[n] > BINS_THRESHOLD_B)
    n_gt30_filled = sum(1 for n in delivered if n_nonempty_by_name[n] > BINS_THRESHOLD_A)
    n_excl_post = funnel_diagnostics.get("n_excluded_by_min_main_entries")

    print("\n=== B4: no filled-bin cut -- ONE histogram set ===")
    print(f"delivered histograms (stage-c survivors, no bin cut): {len(delivered)}")
    print(f"  of which >=25 filled bins (BumpNet own cut, informational): {n_ge25_filled}")
    print(f"  of which >25  filled bins (old min26bins rule):             {n_gt25_filled}")
    print(f"  of which >30  filled bins (old min31bins rule):             {n_gt30_filled}")
    print(f"per-histogram minimum entries applied: {min_entries}")
    print(f"  excluded at the post-processing step: {n_excl_post}")
    print(f"  excluded at the histogram step:       "
          f"{len(excluded_by_hist_min_events)}")

    hists = {name: all_hists[name] for name in delivered}
    path_main = out_dir / f"{args.out_prefix}_bumpnet.root"
    path_cropped = out_dir / f"{args.out_prefix}_bumpnet_cropped.root"
    for path in (path_main, path_cropped):
        if path.exists():
            print(f"STOP: refusing to overwrite an existing file: {path}", file=sys.stderr)
            sys.exit(1)

    print("\n=== Writing ROOT files ===")
    write_root_file(path_main, hists)
    write_cropped_root_file(path_cropped, hists)
    print(f"wrote {path_main} ({len(hists)} histograms, uncropped)")
    print(f"wrote {path_cropped} ({len(hists)} histograms, cropped <- BumpNet uses this one)")

    print("\n=== Writing manifest ===")
    manifest = [manifest_entry(n, im_str_by_name[n], *all_hists[n]) for n in delivered]
    (out_dir / f"manifest_{args.out_prefix}.json").write_text(json.dumps(manifest, indent=2))

    n_final_states = len({
        n.split("_cat_", 1)[1] for n in delivered if "_cat_" in n
    })
    summary = {
        "version": args.version,
        "filled_bin_cut": "NONE (B4: applied by Maryna on the BumpNet side during smoothing)",
        "n_doublemuon_shards": len(dm_paths),
        "n_singlemuon_shards": len(sm_paths),
        "n_distinct_raw_signatures": len(sig_to_bumpnet),
        "funnel": {
            "b_after_min_events_per_fs_100": len(stage_b_names),
            "c_after_postprocessing_ge100_main": len(stage_c_survivors),
            "d_bumpnet_usable_gt30bins_ge100events": len(stage_d_survivors),
        },
        "n_delivered_histograms": len(delivered),
        "n_distinct_final_state_categories_delivered": n_final_states,
        "informational_bin_counts": {
            "n_with_ge_25_filled_bins": n_ge25_filled,
            "n_with_gt_25_filled_bins_old_min26bins_rule": n_gt25_filled,
            "n_with_gt_30_filled_bins_old_min31bins_rule": n_gt30_filled,
        },
        "name_format": ("upstream (configured object types only, e.g. "
                        "0ex_2mx_5jx_1bx)" if args.legacy_gt_labels
                        else "as written in the shards"),
        "legacy_gt_label_conversion_applied": bool(args.legacy_gt_labels),
        "per_histogram_min_entries": min_entries,
        "per_histogram_min_entries_source": (
            "upstream: no minimum, a histogram is written whenever it has >=1 entry"
            if min_entries <= UPSTREAM_MIN_ENTRIES_PER_HISTOGRAM
            else "this delivery's own >=100-entries rule"),
        "per_histogram_min_entries_detail": {
            "n_excluded_at_postprocessing": n_excl_post,
            "n_excluded_at_histogram_step": len(excluded_by_hist_min_events),
            "names_excluded_at_histogram_step": excluded_by_hist_min_events,
            "names_excluded_at_postprocessing_step":
                funnel_diagnostics.get("names_excluded_by_min_main_entries"),
        },
        "funnel_diagnostics": {
            k: v for k, v in funnel_diagnostics.items() if not k.startswith("names_")
        },
        "output_files": {
            path_main.name: str(path_main),
            path_cropped.name: str(path_cropped),
        },
        "file_for_bumpnet": path_cropped.name,
    }
    (out_dir / f"build_summary_{args.version}_nobincut.json").write_text(
        json.dumps(summary, indent=2)
    )

    if min_entries <= UPSTREAM_MIN_ENTRIES_PER_HISTOGRAM:
        min_entries_note = (
            "This delivery applies NO per-histogram minimum entry count. That\n"
            "matches what the main upstream pipeline's own histogram stage does:\n"
            "it writes a histogram whenever at least one value exists and writes\n"
            "nothing when none does. BumpNet re-checks this during smoothing.\n"
            "{} histogram(s) had no entries left after the processing chain and\n"
            "so were not written, exactly as upstream would also not write them."
        ).format(n_excl_post)
    else:
        min_entries_note = (
            "A histogram is only delivered if it has at least {} entries. That\n"
            "excluded {} histogram(s) at the post-processing step and {} at the\n"
            "histogram-filling step."
        ).format(min_entries, n_excl_post, len(excluded_by_hist_min_events))

    readme = README_TEMPLATE.format(
        min_entries_note=min_entries_note,
        cropped=path_cropped.name,
        uncropped=path_main.name,
        n_delivered=len(delivered),
        n_final_states=n_final_states,
        n_ge25=n_ge25_filled,
        n_gt25=n_gt25_filled,
        n_gt30=n_gt30_filled,
        n_dm=len(dm_paths),
        n_sm=len(sm_paths),
    )
    (out_dir / "README.txt").write_text(readme)
    print(f"\nwrote {out_dir / 'README.txt'}")
    print(json.dumps(
        {k: v for k, v in summary.items() if k != "per_histogram_min_entries_detail"},
        indent=2,
    ))
    print("\nAll mandatory build-time checks PASSED (per-histogram TH1F verification "
          "already run inside write_root_file/write_cropped_root_file via "
          "verify_written_th1f).")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--version", required=True, choices=["normal", "top4", "nonjet4", "rare4"])
    p.add_argument("--runs-matched-dir", required=True)
    p.add_argument("--out-dir", required=True)
    p.add_argument("--out-prefix", required=True)
    p.add_argument(
        "--no-filled-bin-cut", action="store_true",
        help="exact-jet-labels task B4: apply NO filled-bin threshold and write ONE "
             "histogram set (uncropped + cropped) instead of the min31bins/min26bins "
             "pair. Everything else -- the >=100-events-per-final-state prune, Z cut, "
             "max-mass cut, peak removal, outlier split and the per-histogram "
             ">=100-main-entries requirement -- is unchanged. Off by default: without "
             "this flag the build is exactly what it always was.",
    )
    p.add_argument(
        "--legacy-gt-labels", action="store_true",
        help="upstream-names task: the shards being read were written BEFORE the "
             "name-format change and carry the old six-field labels "
             "(0e_2m_5j_0g_0t_1b). Convert them to the upstream form "
             "(0e_2m_5j_1b) as they are read. Aborts on any non-zero photon or "
             "tau count and checks no two names collapse onto one. Off by default.",
    )
    p.add_argument(
        "--no-hist-min-entries", action="store_true",
        help="upstream-names task (2): drop this delivery's extra >=100-main-"
             "entries-per-histogram requirement and instead do what upstream's "
             "histogram stage does -- no minimum at all, skipping a signature only "
             "when it has no data. Off by default.",
    )
    args = p.parse_args()

    runs_matched_dir = Path(args.runs_matched_dir)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    assert BIN_WIDTH_GEV == 10.0 and FIXED_MASS_MIN_GEV == 0.0 and FIXED_MASS_MAX_GEV == 10000.0, (
        "fixed-grid constants have drifted from the expected 0-10000 GeV / 10 GeV grid"
    )

    print(f"=== Combined muon delivery, version={args.version} ===")
    dm_paths, sm_paths = gather_shard_paths(runs_matched_dir, args.version)
    print(f"DoubleMuon shards (inclusive): {len(dm_paths)}")
    print(f"SingleMuon shards (exclusive): {len(sm_paths)}")
    shard_paths = dm_paths + sm_paths

    print("\n=== Funnel (real, shared post-processing chain) ===")
    if args.legacy_gt_labels:
        print("legacy label conversion ON: dropping always-zero 0g/0t fields "
              "from pre-change shard labels")
        sig_to_bumpnet_legacy = build_sig_to_bumpnet(shard_paths)
        sig_to_bumpnet = build_sig_to_bumpnet(
            shard_paths, fs_converter=convert_legacy_fs_label)
        n_names = assert_no_name_collisions(sig_to_bumpnet_legacy, sig_to_bumpnet)
        print(f"  converted {len(sig_to_bumpnet)} signatures onto {n_names} distinct "
              f"names; no collisions")
    else:
        sig_to_bumpnet = build_sig_to_bumpnet(shard_paths)
    print(f"total distinct raw signatures across all {len(shard_paths)} shards: {len(sig_to_bumpnet)}")

    min_main_entries = (UPSTREAM_MIN_ENTRIES_PER_HISTOGRAM
                        if args.no_hist_min_entries else None)
    if args.no_hist_min_entries:
        print(f"per-histogram minimum: UPSTREAM behaviour -- no minimum, a histogram "
              f"is written whenever it has at least "
              f"{UPSTREAM_MIN_ENTRIES_PER_HISTOGRAM} entry")
    funnel_diagnostics: dict = {}
    # copy_shards makes scratch COPIES: prune_final_states_below_min_events
    # deletes rows in place, so it must never touch the originals.
    with tempfile.TemporaryDirectory(prefix=f"muon_combined_{args.version}_funnel_") as tmp:
        scratch_shards = copy_shards(shard_paths, Path(tmp))
        stage_b_names, stage_c_survivors, stage_d_survivors, im_str_by_name = run_funnel_at_threshold(
            scratch_shards, PRIMARY_MIN_EVENTS_PER_FS, sig_to_bumpnet,
            diagnostics=funnel_diagnostics, min_main_entries=min_main_entries,
        )
    print(f"stage_b(>=100 events per final state)={len(stage_b_names)} "
          f"stage_c(post-processed, >=100 main events)={len(stage_c_survivors)} "
          f"stage_d(>{MIN_BUMPNET_BINS} bins, merge_and_count's own threshold)={len(stage_d_survivors)}")

    print("\n=== Classify every stage-c survivor against both bin thresholds ===")
    all_hists = {}
    n_nonempty_by_name = {}
    n_events_by_name = {}
    for name, main_arr in stage_c_survivors.items():
        values, edges = make_fixed_grid_histogram(main_arr)
        all_hists[name] = (values, edges)
        n_nonempty_by_name[name] = int(np.count_nonzero(values))
        n_events_by_name[name] = int(values.sum())

    if args.no_filled_bin_cut:
        _build_no_bin_cut_delivery(
            args, out_dir, dm_paths, sm_paths, sig_to_bumpnet, stage_b_names,
            stage_c_survivors, stage_d_survivors, im_str_by_name, all_hists,
            n_nonempty_by_name, n_events_by_name, funnel_diagnostics,
        )
        return

    set_a = {n for n in stage_c_survivors
             if n_nonempty_by_name[n] > BINS_THRESHOLD_A and n_events_by_name[n] >= MIN_BUMPNET_EVENTS}
    set_b = {n for n in stage_c_survivors
             if n_nonempty_by_name[n] > BINS_THRESHOLD_B and n_events_by_name[n] >= MIN_BUMPNET_EVENTS}
    print(f"set_a (>{BINS_THRESHOLD_A} bins, min31bins): {len(set_a)} names")
    print(f"set_b (>{BINS_THRESHOLD_B} bins, min26bins): {len(set_b)} names")
    if not set_a.issubset(set_b):
        print("STOP: >25-bin set is not a superset of the >30-bin set (should be impossible).",
              file=sys.stderr)
        sys.exit(1)

    print("\n=== Writing ROOT files ===")
    hists_a = {name: all_hists[name] for name in set_a}
    hists_b = {name: all_hists[name] for name in set_b}
    path_a = out_dir / f"{args.out_prefix}_bumpnet_min31bins.root"
    path_b = out_dir / f"{args.out_prefix}_bumpnet_min26bins.root"
    path_a_cropped = out_dir / f"{args.out_prefix}_bumpnet_min31bins_cropped.root"
    path_b_cropped = out_dir / f"{args.out_prefix}_bumpnet_min26bins_cropped.root"

    write_root_file(path_a, hists_a)
    write_root_file(path_b, hists_b)
    write_cropped_root_file(path_a_cropped, hists_a)
    write_cropped_root_file(path_b_cropped, hists_b)
    print(f"wrote {path_a} ({len(hists_a)} histograms)")
    print(f"wrote {path_b} ({len(hists_b)} histograms)")
    print(f"wrote {path_a_cropped} ({len(hists_a)} histograms, cropped)")
    print(f"wrote {path_b_cropped} ({len(hists_b)} histograms, cropped)")

    print("\n=== Writing manifests ===")
    manifest_a = [manifest_entry(n, im_str_by_name[n], *all_hists[n]) for n in sorted(set_a)]
    manifest_b = [manifest_entry(n, im_str_by_name[n], *all_hists[n]) for n in sorted(set_b)]
    (out_dir / f"manifest_{args.out_prefix}_min31bins.json").write_text(json.dumps(manifest_a, indent=2))
    (out_dir / f"manifest_{args.out_prefix}_min26bins.json").write_text(json.dumps(manifest_b, indent=2))

    summary = {
        "version": args.version,
        "n_doublemuon_shards": len(dm_paths),
        "n_singlemuon_shards": len(sm_paths),
        "n_distinct_raw_signatures": len(sig_to_bumpnet),
        "funnel": {
            "b_after_min_events_per_fs_100": len(stage_b_names),
            "c_after_postprocessing_ge100_main": len(stage_c_survivors),
            "d_bumpnet_usable_gt30bins_ge100events": len(stage_d_survivors),
        },
        "n_histograms_min31bins": len(set_a),
        "n_histograms_min26bins": len(set_b),
        "output_files": {
            path_a.name: str(path_a), path_b.name: str(path_b),
            path_a_cropped.name: str(path_a_cropped), path_b_cropped.name: str(path_b_cropped),
        },
    }
    (out_dir / f"build_summary_{args.version}.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))
    print("\nAll mandatory build-time checks PASSED (per-histogram TH1F verification already run "
          "inside write_root_file/write_cropped_root_file via verify_written_th1f).")


if __name__ == "__main__":
    main()
