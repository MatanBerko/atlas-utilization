#!/usr/bin/env python
"""
DoubleMuon BumpNet ROOT delivery.

Writes the coverage run's BumpNet-ready histograms as real TH1F ROOT
files, straight from the EXISTING coverage-run SQLite shards
(/storage/.../output/cms_coverage_full/job_*/coverage_shard.sqlite) --
no data file is re-read, no new selection or combination is run. Two
output files, differing ONLY in the minimum-filled-bins threshold applied
to the SAME already-post-processed histograms:

  doublemuon_bumpnet_min31bins.root  -- bins_filled >  30  (i.e. >=31)
  doublemuon_bumpnet_min26bins.root  -- bins_filled >  25  (i.e. >=26)

both also requiring >=100 events, unchanged from the coverage run's own
BumpNet criterion (arXiv:2501.05603 Sec 2.2.2).

Reuses, unmodified, the exact same functions and thresholds that produced
the committed 316 count (studies/cms_coverage/assets/funnel_result.json):
  - studies.cms_coverage.cluster.merge_and_count: copy_shards,
    load_chunks_by_signature, run_funnel_at_threshold, SIG_PATTERN,
    PRIMARY_MIN_EVENTS_PER_FS, MIN_BUMPNET_BINS, MIN_BUMPNET_EVENTS.
    run_funnel_at_threshold itself runs the real, shared
    prune_final_states_below_min_events / _apply_z_peak_cut /
    _find_rightmost_highest_peak / _split_by_first_empty_bin chain --
    the exact same call sequence, on the exact same shards, at the exact
    same thresholds, as the run that produced 316.
  - studies.m0m1j0_cms.histograms: make_fixed_grid_histogram (same
    0-10000 GeV / 10 GeV fixed grid), to_writable_th1f (genuine TH1F,
    trim_empty_tail-equivalent display range), verify_written_th1f.

The ONLY new logic: run_funnel_at_threshold's own stage_c_survivors (every
name that passed post-processing with >=100 main events, REGARDLESS of
bin count) is classified against TWO bin thresholds instead of
merge_and_count's own hardcoded one -- both classifications applied to
the SAME already-computed histogram, so a name common to both output
files is, by construction, backed by the identical (values, edges) object
in both -- never recomputed a second time.

Mandatory checks performed here (all STOP the script, non-zero exit, on
failure -- never a silent partial write):
  1. Shard identity/completeness (57 jobs, total_n_read==94,148,416) --
     same check as merge_and_count.py's own.
  2. The >30-bin set has exactly 316 names, AND is IDENTICAL (as a set)
     to merge_and_count's own run_funnel_at_threshold stage_d_survivors
     for this same run -- two independently-arrived-at 316-name sets from
     the same shards must agree exactly.
  3. Every m0m1j0-combination histogram in the >30-bin file matches the
     committed studies/m0m1j0_cms/v2/data/m0m1j0_data_postprocessed.root
     bin-for-bin.
  4. The >25-bin file is a strict superset of the >30-bin file, with
     identical bin contents for every shared name (re-verified by
     reading BOTH written ROOT files back from disk, not just checked
     in-memory before writing).

Usage:
    python build_bumpnet_root.py \
        --jobs-dir /storage/agrp/berkom/atlas-utilization/output/cms_coverage_full \
        --n-jobs 57 \
        --v2-root studies/m0m1j0_cms/v2/data/m0m1j0_data_postprocessed.root \
        --out-dir /storage/agrp/berkom/atlas-utilization/output/deliver_doublemuon_bumpnet
"""
from __future__ import annotations

import argparse
import json
import logging
import re
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

import numpy as np  # noqa: E402
import uproot  # noqa: E402

from services.storage.sqlite_shards import list_signatures  # noqa: E402
from studies.cms_coverage.cluster.merge_and_count import (  # noqa: E402
    SIG_PATTERN,
    PRIMARY_MIN_EVENTS_PER_FS,
    MIN_BUMPNET_BINS,
    MIN_BUMPNET_EVENTS,
    copy_shards,
    run_funnel_at_threshold,
    object_content_category,
    object_count,
)
from studies.m0m1j0_cms.histograms import (  # noqa: E402
    _convert_to_bumpnet_name,
    make_fixed_grid_histogram,
    to_writable_th1f,
    verify_written_th1f,
    BIN_WIDTH_GEV,
    FIXED_MASS_MIN_GEV,
    FIXED_MASS_MAX_GEV,
)

logging.basicConfig(level=logging.WARNING, format="%(asctime)s %(levelname)s %(message)s")
LOGGER = logging.getLogger("build_bumpnet_root")

EXPECTED_TOTAL_EVENTS = 94_148_416
BINS_THRESHOLD_A = 30  # >30, i.e. >=31 -- the coverage run's own primary criterion
BINS_THRESHOLD_B = 25  # >25, i.e. >=26 -- the supervisor's requested looser cut
OUT_FILE_A = "doublemuon_bumpnet_min31bins.root"
OUT_FILE_B = "doublemuon_bumpnet_min26bins.root"


def load_shards_and_metadata(jobs_dir: Path, n_jobs: int):
    shard_paths, per_job_metadata = [], {}
    for i in range(1, n_jobs + 1):
        job_dir = jobs_dir / f"job_{i}"
        shard = job_dir / "coverage_shard.sqlite"
        meta_path = job_dir / "job_metadata.json"
        if not shard.exists() or not meta_path.exists():
            raise RuntimeError(f"job_{i}: missing shard or metadata under {job_dir}")
        shard_paths.append(str(shard))
        per_job_metadata[i] = json.loads(meta_path.read_text())
    return shard_paths, per_job_metadata


def build_sig_to_bumpnet(shard_paths):
    """Identical to merge_and_count.main()'s own stage-(a) loop (that
    orchestration is inline in main(), not exposed as an importable
    function, so it is replicated here verbatim rather than copy-edited
    -- same SIG_PATTERN, same _convert_to_bumpnet_name call)."""
    sig_to_bumpnet = {}
    for shard_path in shard_paths:
        for sig in list_signatures(shard_path):
            m = SIG_PATTERN.search(sig)
            if not m:
                continue
            fs_str, im_str = m.groups()
            bumpnet_name = _convert_to_bumpnet_name(fs_str, im_str)
            sig_to_bumpnet[sig] = (bumpnet_name, fs_str, im_str)
    return sig_to_bumpnet


def load_v2_m0m1j0_histograms(v2_root_path: Path):
    """{bumpnet_name: values (float64, no under/overflow)} for every
    real (non-inclusive) m0m1j0 category in the committed v2 ROOT file."""
    f = uproot.open(str(v2_root_path))
    out = {}
    for key in f.keys(cycle=False):
        base = key.split(";")[0]
        stripped = base[len("ROI_"):] if base.startswith("ROI_") else base
        stripped = re.sub(r"_width_\d+$", "", stripped)
        if not stripped.startswith("mass_m0m1j0_cat_"):
            continue  # skip the inclusive label, not a real BumpNet category
        out[stripped] = f[base].values()
    return out


def write_root_file(path: Path, histograms: dict):
    """histograms: {bumpnet_name: (values, edges)}. Returns {ROI-key: values} for verification."""
    written = {}
    with uproot.recreate(str(path)) as fout:
        for name, (values, edges) in sorted(histograms.items()):
            key = f"ROI_{name}_width_{int(BIN_WIDTH_GEV)}"
            fout[key] = to_writable_th1f(values, edges, key)
            written[key] = values
    verify_written_th1f(str(path), written)
    return written


def manifest_entry(name, im_str, values, edges):
    nonzero_idx = np.nonzero(values > 0)[0]
    n_bins = int(len(nonzero_idx))
    n_events = int(values.sum())
    first_edge = float(edges[nonzero_idx[0]]) if n_bins > 0 else None
    last_edge = float(edges[nonzero_idx[-1] + 1]) if n_bins > 0 else None
    return {
        "name": name,
        "root_key": f"ROI_{name}_width_{int(BIN_WIDTH_GEV)}",
        "combination": im_str,
        "final_state_category": name.split("_cat_", 1)[1] if "_cat_" in name else None,
        "object_count": object_count(im_str),
        "object_content_category": object_content_category(im_str),
        "n_events": n_events,
        "n_filled_bins": n_bins,
        "first_filled_bin_low_edge_gev": first_edge,
        "last_filled_bin_high_edge_gev": last_edge,
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--jobs-dir", required=True)
    p.add_argument("--n-jobs", type=int, default=57)
    p.add_argument("--v2-root", required=True)
    p.add_argument("--out-dir", required=True)
    args = p.parse_args()

    jobs_dir = Path(args.jobs_dir)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    assert BIN_WIDTH_GEV == 10.0 and FIXED_MASS_MIN_GEV == 0.0 and FIXED_MASS_MAX_GEV == 10000.0, (
        "fixed-grid constants in studies.m0m1j0_cms.histograms have drifted from the "
        "expected 0-10000 GeV / 10 GeV grid -- stopping rather than writing histograms "
        "on an unexpected grid"
    )

    print("=== Step 1: shard identity/completeness check ===")
    shard_paths, per_job_metadata = load_shards_and_metadata(jobs_dir, args.n_jobs)
    total_n_read = sum(m["n_read"] for m in per_job_metadata.values())
    print(f"n_jobs_present={len(per_job_metadata)} total_n_read={total_n_read:,} "
          f"expected={EXPECTED_TOTAL_EVENTS:,}")
    if len(per_job_metadata) != args.n_jobs or total_n_read != EXPECTED_TOTAL_EVENTS:
        print("STOP: shard set is missing or incomplete -- refusing to proceed.", file=sys.stderr)
        sys.exit(1)
    print("PASS: all 57 shards present, total events read matches the portal total exactly.")

    print("\n=== Step 2: build signature->BumpNet-name map, run the real funnel at threshold=100 ===")
    sig_to_bumpnet = build_sig_to_bumpnet(shard_paths)
    with tempfile.TemporaryDirectory(prefix="deliver_bumpnet_funnel_") as tmp:
        scratch_shards = copy_shards(shard_paths, Path(tmp))
        stage_b_names, stage_c_survivors, stage_d_survivors, im_str_by_name = run_funnel_at_threshold(
            scratch_shards, PRIMARY_MIN_EVENTS_PER_FS, sig_to_bumpnet
        )
    print(f"stage_b={len(stage_b_names)} stage_c={len(stage_c_survivors)} "
          f"stage_d(>{MIN_BUMPNET_BINS} bins, using merge_and_count's own unmodified threshold)="
          f"{len(stage_d_survivors)}")

    print("\n=== Step 3: classify every stage-c survivor against BOTH bin thresholds ===")
    all_hists = {}   # name -> (values, edges)
    n_nonempty_by_name = {}
    n_events_by_name = {}
    for name, main_arr in stage_c_survivors.items():
        values, edges = make_fixed_grid_histogram(main_arr)
        all_hists[name] = (values, edges)
        n_nonempty_by_name[name] = int(np.count_nonzero(values))
        n_events_by_name[name] = int(values.sum())

    set_a = {
        name for name in stage_c_survivors
        if n_nonempty_by_name[name] > BINS_THRESHOLD_A and n_events_by_name[name] >= MIN_BUMPNET_EVENTS
    }
    set_b = {
        name for name in stage_c_survivors
        if n_nonempty_by_name[name] > BINS_THRESHOLD_B and n_events_by_name[name] >= MIN_BUMPNET_EVENTS
    }
    print(f"set_a (>{BINS_THRESHOLD_A} bins): {len(set_a)} names")
    print(f"set_b (>{BINS_THRESHOLD_B} bins): {len(set_b)} names")

    print("\n=== MANDATORY CHECK 1: set_a has exactly 316 names, identical to merge_and_count's own stage_d ===")
    if len(set_a) != 316:
        print(f"STOP: expected exactly 316 histograms at >{BINS_THRESHOLD_A} bins, got {len(set_a)}.",
              file=sys.stderr)
        sys.exit(1)
    if set_a != set(stage_d_survivors.keys()):
        only_ours = sorted(set_a - set(stage_d_survivors))
        only_theirs = sorted(set(stage_d_survivors) - set_a)
        print("STOP: set_a does not exactly match merge_and_count's own stage_d_survivors.", file=sys.stderr)
        print(f"  only in ours: {only_ours}", file=sys.stderr)
        print(f"  only in merge_and_count's: {only_theirs}", file=sys.stderr)
        sys.exit(1)
    print("PASS: exactly 316 names, and identical to merge_and_count's own independent stage_d computation.")

    print(f"\n=== MANDATORY CHECK 2: set_b (>{BINS_THRESHOLD_B} bins) is a strict superset of set_a ===")
    if not set_a.issubset(set_b):
        print("STOP: the >25-bin set is NOT a superset of the >30-bin set (should be impossible "
              "by construction -- investigate before proceeding).", file=sys.stderr)
        sys.exit(1)
    n_extra = len(set_b) - len(set_a)
    print(f"PASS: set_b ({len(set_b)}) is a superset of set_a ({len(set_a)}); {n_extra} extra histograms.")

    print("\n=== Writing ROOT files ===")
    hists_a = {name: all_hists[name] for name in set_a}
    hists_b = {name: all_hists[name] for name in set_b}
    path_a = out_dir / OUT_FILE_A
    path_b = out_dir / OUT_FILE_B
    written_a = write_root_file(path_a, hists_a)
    written_b = write_root_file(path_b, hists_b)
    print(f"wrote {path_a} ({len(hists_a)} histograms, verified TH1F)")
    print(f"wrote {path_b} ({len(hists_b)} histograms, verified TH1F)")

    print("\n=== MANDATORY CHECK 3: shared histograms identical bin-for-bin, read back from BOTH files on disk ===")
    fa = uproot.open(str(path_a))
    fb = uproot.open(str(path_b))
    keys_a = set(k.split(";")[0] for k in fa.keys())
    mismatches = []
    for name in sorted(set_a):
        key = f"ROI_{name}_width_{int(BIN_WIDTH_GEV)}"
        va = fa[key].values()
        vb = fb[key].values()
        if not np.array_equal(va, vb):
            mismatches.append(key)
    if mismatches:
        print(f"STOP: {len(mismatches)} shared histogram(s) differ between the two written files: "
              f"{mismatches[:10]}", file=sys.stderr)
        sys.exit(1)
    print(f"PASS: all {len(set_a)} shared histograms are bin-for-bin identical between the two files, "
          f"re-read from disk.")

    print("\n=== MANDATORY CHECK 4: m0m1j0 histograms match studies/m0m1j0_cms/v2 bin-for-bin ===")
    v2_hists = load_v2_m0m1j0_histograms(Path(args.v2_root))
    m0m1j0_in_a = sorted(n for n in set_a if n.startswith("mass_m0m1j0_cat_"))
    print(f"{len(m0m1j0_in_a)} m0m1j0-combination histograms in the >30-bin file; "
          f"{len(v2_hists)} m0m1j0 categories in the committed v2 file.")
    m0m1j0_mismatches = []
    m0m1j0_missing_from_v2 = []
    for name in m0m1j0_in_a:
        if name not in v2_hists:
            m0m1j0_missing_from_v2.append(name)
            continue
        ours = all_hists[name][0].astype(np.float64)
        theirs = v2_hists[name].astype(np.float64)
        if not np.array_equal(ours, theirs):
            m0m1j0_mismatches.append(name)
    if m0m1j0_missing_from_v2:
        print(f"STOP: {len(m0m1j0_missing_from_v2)} m0m1j0 histogram(s) in our >30-bin file have no "
              f"counterpart in the committed v2 file: {m0m1j0_missing_from_v2}", file=sys.stderr)
        sys.exit(1)
    if m0m1j0_mismatches:
        print(f"STOP: {len(m0m1j0_mismatches)} m0m1j0 histogram(s) do not match v2 bin-for-bin: "
              f"{m0m1j0_mismatches}", file=sys.stderr)
        sys.exit(1)
    print(f"PASS: all {len(m0m1j0_in_a)} m0m1j0 histograms in the >30-bin file match the committed "
          f"v2 ROOT file bin-for-bin, exactly.")

    print("\n=== Writing manifests ===")
    manifest_a = [manifest_entry(n, im_str_by_name[n], *all_hists[n]) for n in sorted(set_a)]
    manifest_b = [manifest_entry(n, im_str_by_name[n], *all_hists[n]) for n in sorted(set_b)]
    (out_dir / "manifest_min31bins.json").write_text(json.dumps(manifest_a, indent=2))
    (out_dir / "manifest_min26bins.json").write_text(json.dumps(manifest_b, indent=2))
    print(f"wrote manifest_min31bins.json ({len(manifest_a)} entries)")
    print(f"wrote manifest_min26bins.json ({len(manifest_b)} entries)")

    extra_names = sorted(set_b - set_a)
    extra_stats = {
        "n_extra": len(extra_names),
        "extra_names": extra_names,
        "event_count_stats": {
            "min": min((n_events_by_name[n] for n in extra_names), default=None),
            "median": float(np.median([n_events_by_name[n] for n in extra_names])) if extra_names else None,
            "max": max((n_events_by_name[n] for n in extra_names), default=None),
        },
        "bin_count_stats": {
            "min": min((n_nonempty_by_name[n] for n in extra_names), default=None),
            "median": float(np.median([n_nonempty_by_name[n] for n in extra_names])) if extra_names else None,
            "max": max((n_nonempty_by_name[n] for n in extra_names), default=None),
        },
    }

    summary = {
        "shard_identity_check": {"n_jobs_present": len(per_job_metadata), "total_n_read": total_n_read,
                                  "expected_total_events": EXPECTED_TOTAL_EVENTS, "matches": True},
        "stage_b": len(stage_b_names),
        "stage_c": len(stage_c_survivors),
        "n_histograms_min31bins": len(set_a),
        "n_histograms_min26bins": len(set_b),
        "matches_committed_316": len(set_a) == 316,
        "identical_to_merge_and_count_stage_d": set_a == set(stage_d_survivors.keys()),
        "shared_histograms_bin_identical_on_disk": True,
        "n_m0m1j0_checked_vs_v2": len(m0m1j0_in_a),
        "m0m1j0_matches_v2_bin_for_bin": True,
        "extra_histograms_min26_vs_min31": extra_stats,
        "output_files": {
            OUT_FILE_A: str(path_a),
            OUT_FILE_B: str(path_b),
        },
    }
    (out_dir / "build_summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))
    print("\nAll mandatory checks PASSED.")


if __name__ == "__main__":
    main()
