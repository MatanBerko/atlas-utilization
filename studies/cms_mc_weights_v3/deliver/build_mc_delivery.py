#!/usr/bin/env python
"""
Build the CMS MC delivery from --is-mc per-file shards (DESIGN.md A5 / D4-D8).

What it does, in order:

  1. Discovers the per-file job directories under --runs-dir (each one a
     `job_<n>/` holding `dataset_shard_rare4_inclusive.sqlite` and
     `job_metadata.json`) and groups them by CERN Open Data record ID.
  2. D5 campaign guard: every record's portal dataset title must contain
     `RunIISummer20UL16NanoAODv9` and must NOT contain `APV` or `preVFP`.
     An APV/preVFP record is a hard error -- it cannot be normalised to the
     Run2016G+H luminosity.
  3. D4 per-file Sigma-w check:
         |sum(genWeight) - Runs.genEventSumw| / Runs.genEventSumw <= 1e-6
     A failing file is EXCLUDED and its Sigma-w with it, so a pre-skimmed file
     can never inflate the denominator. A sample's Sigma-w is the sum over
     surviving files only.
  4. Copies the surviving shards to scratch (prune mutates its inputs) and
     computes, per entry,
         w_event = genWeight * L1PreFiringWeight_Nom
                   * sigma_eff[pb] * 1000 * L_fb / Sigma-w
     with k_factor = gen_filt_eff = 1 (both already inside sigma_eff; see the
     registry header), writing it as the reserved `_mcw` sibling -- PR #35's
     convention -- next to each mass signature.
  5. D8 coverage cap: a signature capped in a file has its weights scaled by
     `true_size / kept` for that file BEFORE the files are merged.
  6. Applies the >= 100-entries-per-final-state rule ONCE, on the combined
     shards of every surviving file of every sample at once, so all samples
     share one surviving final-state set and the per-sample files and the
     summed file agree.
  7. Post-processes masses and weights IN LOCKSTEP -- Z cut 110 GeV, max-mass
     cut, peak removal, bin-aligned outlier split -- with any length mismatch
     a HARD ERROR, never a fallback to unweighted.
  8. Writes TH1D + Sumw2 with names identical to data, asserts them on
     read-back, and reports per-sample Sigma-w, file counts, cap incidence,
     raw and weighted yields per final state, and the negative/empty-bin
     inventory.

Build-time OPTIONS, so an answer from Maryna or Yuval needs no re-run:
  --peak-on {weighted,unweighted}   [weighted]
  --min-events-basis {raw,weighted} [raw]
  --output-mode {per-sample,summed,both} [both]

No negative-bin fix is implemented -- only the inventory is reported. That
choice is Maryna's (DESIGN.md open questions).

The event union for this build is the FOUR data acceptance flags only. The
SingleElectron candidate is stored by the driver and deliberately ignored
here (its offline threshold is undecided and out of scope).
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import shutil
import sys
import tempfile
from collections import defaultdict
from datetime import datetime, timezone

import numpy as np

REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

from services.pipelines.post_processing_pipeline import (  # noqa: E402
    _aligned_bin_edges,
    _dilepton_flavor,
)
from services.storage.sqlite_shards import (  # noqa: E402
    SqliteArrayShardWriter,
    iter_arrays_for_signature,
    list_signatures,
    prune_final_states_below_min_events,
)
from studies.cms_coverage.cluster.merge_and_count import (  # noqa: E402
    MAX_MASS_CUTOFF,
    PRIMARY_MIN_EVENTS_PER_FS,
    Z_PEAK_CUTOFF,
)
from studies.cms_datasets.cluster.run_dataset_on_file import (  # noqa: E402
    DELIVERY_VETO_ORDER_4,
    MC_ACC_BIT_BY_LABEL,
    MC_ACC_BIT_ELE27_CANDIDATE,
    MC_SIBLING_ACCEPTANCE,
    MC_SIBLING_GENWEIGHT,
    MC_SIBLING_L1PREFIRE,
    MC_WEIGHT_SUFFIX,
    git_commit_hash,
)
from studies.cms_datasets.deliver.build_dataset_delivery import roi_key  # noqa: E402
from studies.m0m1j0_cms.histograms import (  # noqa: E402
    BIN_WIDTH_GEV,
    _convert_to_bumpnet_name,
    _n_bins,
)
from studies.cms_mc_weights_v3.deliver.weighted_histograms import (  # noqa: E402
    fill_weighted_fixed_grid,
    negative_or_empty_bin_inventory,
    to_writable_th1d,
    verify_written_th1d,
)

import uproot  # noqa: E402

# D4. Run2016G 7.653 + Run2016H 8.740 fb^-1 -- the post-golden-JSON data
# luminosity, so the MC normalisation matches the data it is compared to.
TARGET_LUMINOSITY_FB = 16.393
PB_TO_FB = 1000.0
SIGMA_W_TOLERANCE = 1e-6

REGISTRY_PATH = REPO_ROOT / "studies" / "cms_mc_weights_v3" / "cms_mc_normalisation_v3.json"
SHARD_NAME = "dataset_shard_rare4_inclusive.sqlite"   # rare4 == the delivered Version B

# Same `$`-anchored shape the data builder uses, so a sibling signature can
# never be mistaken for a mass signature.
SIG_PATTERN = re.compile(r"_FS_([0-9a-z_]+)_IM_([0-9a-z]+)$")
CAPPED_METADATA_PATTERN = re.compile(
    r"^true_size=(\d+)\s+kept=(\d+)\s+weight_scale=(.+)$")

# D5.
CAMPAIGN_REQUIRED_SUBSTRING = "RunIISummer20UL16NanoAODv9"
CAMPAIGN_FORBIDDEN_SUBSTRINGS = ("APV", "preVFP")


# --------------------------------------------------------------------------
# discovery and guards
# --------------------------------------------------------------------------

def load_registry() -> dict:
    if not REGISTRY_PATH.exists():
        raise SystemExit(f"missing registry {REGISTRY_PATH}")
    return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))


def assert_campaign_ok(record_id: str, record: dict) -> dict:
    """D5: UL16 postVFP only. An APV/preVFP record is a hard error."""
    title = record.get("portal_dataset_title") or ""
    forbidden = [s for s in CAMPAIGN_FORBIDDEN_SUBSTRINGS if s in title]
    if forbidden:
        raise SystemExit(
            f"STOP: record {record_id} is an APV/preVFP sample "
            f"({forbidden} in its portal title) and cannot be normalised to "
            f"Run2016G+H. title={title!r}")
    if CAMPAIGN_REQUIRED_SUBSTRING not in title:
        raise SystemExit(
            f"STOP: record {record_id}'s portal title does not identify it as "
            f"{CAMPAIGN_REQUIRED_SUBSTRING}. title={title!r}")
    return {"portal_dataset_title": title, "campaign_ok": True}


def discover_jobs(runs_dir: pathlib.Path, only_records: set[int] | None,
                  only_file_indices: set[int] | None) -> dict:
    """{record_id (str): [job metadata dict, ...]}, from every job_*/ under
    runs_dir that has both a shard and a job_metadata.json."""
    jobs = defaultdict(list)
    n_seen = 0
    for meta_path in sorted(runs_dir.rglob("job_metadata.json")):
        shard = meta_path.parent / SHARD_NAME
        if not shard.exists():
            continue
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        if not meta.get("is_mc"):
            continue
        n_seen += 1
        rid = int(meta["record_id"])
        if only_records is not None and rid not in only_records:
            continue
        if only_file_indices is not None and int(meta["file_index"]) not in only_file_indices:
            continue
        jobs[str(rid)].append({
            "job_dir": str(meta_path.parent),
            "shard": str(shard),
            "metadata_path": str(meta_path),
            "metadata": meta,
            "file_index": int(meta["file_index"]),
        })
    if not jobs:
        raise SystemExit(
            f"no --is-mc job directories found under {runs_dir} "
            f"(saw {n_seen} MC job_metadata.json before filtering)")
    for rid in jobs:
        jobs[rid].sort(key=lambda j: j["file_index"])
    return dict(jobs)


def sigma_w_for_sample(record_id: str, job_list: list) -> dict:
    """D4: the per-file Sigma-w check, and the sample's Sigma-w over the
    SURVIVING files only."""
    surviving, excluded = [], []
    sigma_w = 0.0
    for job in job_list:
        meta = job["metadata"]
        check = meta.get("mc_sigma_w_self_check")
        if check is None:
            raise SystemExit(
                f"record {record_id} file {job['file_index']}: job_metadata.json has "
                "no mc_sigma_w_self_check -- it was not produced by the --is-mc "
                "driver this builder expects.")
        runs_sumw = float(check["runs_gen_event_sumw"])
        file_sumw = float(check["file_sum_genweight"])
        rel = abs(file_sumw - runs_sumw) / abs(runs_sumw) if runs_sumw else None
        entry = {
            "file_index": job["file_index"],
            "shard": job["shard"],
            "runs_gen_event_sumw": runs_sumw,
            "file_sum_genweight": file_sumw,
            "relative_difference": rel,
            "tolerance": SIGMA_W_TOLERANCE,
            "n_events_read": check.get("n_events_read"),
            "runs_gen_event_count": check.get("runs_gen_event_count"),
            "event_count_matches": check.get("event_count_matches"),
        }
        if rel is not None and rel <= SIGMA_W_TOLERANCE:
            entry["verdict"] = "included"
            surviving.append({**job, "sigma_w_entry": entry})
            sigma_w += runs_sumw
        else:
            entry["verdict"] = "EXCLUDED: sum(genWeight) disagrees with " \
                               "Runs.genEventSumw (possible pre-skim)"
            excluded.append(entry)
    if not surviving:
        raise SystemExit(
            f"record {record_id}: every file failed the Sigma-w check; nothing to "
            "normalise. Refusing to build.")
    if sigma_w == 0.0:
        raise SystemExit(f"record {record_id}: Sigma-w is zero over surviving files")
    return {
        "sigma_w": sigma_w,
        "n_files_included": len(surviving),
        "n_files_excluded": len(excluded),
        "surviving": surviving,
        "per_file": [j["sigma_w_entry"] for j in surviving] + excluded,
    }


def read_cap_scales(shard_path: str) -> dict:
    """{signature: weight_scale} from a shard's CAPPED:: metadata (D8)."""
    import sqlite3
    scales = {}
    # Closed explicitly: sqlite3's context manager commits but does NOT close,
    # which leaves the file locked on Windows and keeps scratch dirs around.
    conn = sqlite3.connect(shard_path)
    try:
        rows = conn.execute(
            "SELECT key, value FROM shard_metadata WHERE key LIKE 'CAPPED::%'"
        ).fetchall()
    finally:
        conn.close()
    for key, value in rows:
        signature = key[len("CAPPED::"):]
        m = CAPPED_METADATA_PATTERN.match(value.strip())
        if not m:
            raise SystemExit(
                f"{shard_path}: CAPPED metadata for {signature!r} is not in the "
                f"expected form (got {value!r}). Refusing to guess a scale factor.")
        scales[signature] = {
            "true_size": int(m.group(1)),
            "kept": int(m.group(2)),
            "weight_scale": float(m.group(3)),
        }
    return scales


# --------------------------------------------------------------------------
# weights
# --------------------------------------------------------------------------

def normalisation_factor(record: dict, sigma_w: float) -> float:
    """sigma_eff[pb] * 1000 * k * eps * L_fb / Sigma-w, with k = eps = 1."""
    k = float(record["k_factor"])
    eps = float(record["gen_filt_eff"])
    if k != 1.0 or eps != 1.0:
        raise SystemExit(
            f"record {record['record_id']}: k_factor={k} gen_filt_eff={eps}. "
            "Both must be exactly 1.0 -- every correction is already inside "
            "cross_section_pb (see the registry header). Refusing to apply a "
            "correction twice.")
    sigma_pb = float(record["cross_section_pb"])
    return sigma_pb * PB_TO_FB * k * eps * TARGET_LUMINOSITY_FB / sigma_w


def write_mcw_siblings(shard_path: str, norm: float, cap_scales: dict) -> dict:
    """D4/D8: compute w_event per entry and write it as the `_mcw` sibling.

    One mass chunk and one sibling chunk per signature per file (the funnel
    writes them together), so the pairing is 1:1. Any length mismatch is a
    HARD ERROR -- there is no unweighted fallback anywhere in this builder.
    """
    writer = SqliteArrayShardWriter(shard_path)
    n_written = 0
    n_entries = 0
    n_capped_applied = 0
    try:
        for sig in list_signatures(shard_path):
            if not SIG_PATTERN.search(sig):
                continue  # a sibling, or not a mass signature
            masses = list(iter_arrays_for_signature(shard_path, sig))
            genw = list(iter_arrays_for_signature(shard_path, sig + MC_SIBLING_GENWEIGHT))
            l1pf = list(iter_arrays_for_signature(shard_path, sig + MC_SIBLING_L1PREFIRE))
            n_mass = sum(len(a) for a in masses)
            if n_mass == 0:
                continue
            if not genw or not l1pf:
                raise SystemExit(
                    f"{shard_path}: signature {sig} has {n_mass} masses but no "
                    f"{MC_SIBLING_GENWEIGHT}/{MC_SIBLING_L1PREFIRE} siblings. "
                    "Refusing to write an unweighted MC histogram.")
            g = np.concatenate([np.asarray(a, dtype=np.float64) for a in genw])
            p = np.concatenate([np.asarray(a, dtype=np.float64) for a in l1pf])
            if len(g) != n_mass or len(p) != n_mass:
                raise SystemExit(
                    f"{shard_path}: signature {sig} alignment lost -- {n_mass} "
                    f"masses, {len(g)} genWeight, {len(p)} L1 prefiring entries.")
            w = g * p * norm
            cap = cap_scales.get(sig)
            if cap is not None:
                # D8: scale BEFORE the files are merged, so the subsampled
                # signature still carries the full sample's expected yield.
                w = w * cap["weight_scale"]
                n_capped_applied += 1
            writer.append_array(sig + MC_WEIGHT_SUFFIX, w)
            n_written += 1
            n_entries += n_mass
        writer.commit()
    finally:
        writer.close()
    return {"n_mcw_signatures_written": n_written,
            "n_entries_weighted": n_entries,
            "n_capped_signatures_scaled": n_capped_applied}


# --------------------------------------------------------------------------
# post-processing, masses and weights in lockstep
# --------------------------------------------------------------------------

def z_peak_keep_mask(masses: np.ndarray, signature: str) -> np.ndarray:
    """The Z-cut as a MASK, so the same mask can be applied to the weights.

    Uses the shared `_dilepton_flavor` and the shared Z_PEAK_CUTOFF, so which
    channels are cut and at what mass are the data path's own decisions."""
    if Z_PEAK_CUTOFF <= 0 or not _dilepton_flavor(signature):
        return np.ones(len(masses), dtype=bool)
    return masses >= Z_PEAK_CUTOFF


def find_peak_mass(masses: np.ndarray, weights: np.ndarray | None) -> float | None:
    """The rightmost highest peak on the aligned grid.

    Reimplements the shared `_find_rightmost_highest_peak` with an optional
    `weights` argument -- PR #35's own change, which is not merged here. With
    weights=None the arithmetic is identical to the shared function's, which
    the test suite asserts directly."""
    if len(masses) == 0:
        return None
    edges = _aligned_bin_edges(masses, BIN_WIDTH_GEV)
    counts, _ = np.histogram(masses, bins=edges, weights=weights)
    if len(counts) == 0:
        return None
    max_count = np.max(counts)
    peak_idx = None
    for i in range(len(counts) - 1, -1, -1):
        if counts[i] == max_count:
            peak_idx = i
            break
    if peak_idx is None:
        return None
    return float(edges[peak_idx])


def main_split_mask(masses: np.ndarray) -> np.ndarray:
    """The first-empty-bin split as a MASK, on UNWEIGHTED counts (PR #35's own
    semantics: the split is a statement about where the spectrum runs out of
    entries, not about weight)."""
    if len(masses) == 0:
        return np.zeros(0, dtype=bool)
    edges = _aligned_bin_edges(masses, BIN_WIDTH_GEV)
    counts, _ = np.histogram(masses, bins=edges)
    if len(counts) == 0:
        return np.ones(len(masses), dtype=bool)
    first_empty = None
    for i in range(len(counts)):
        if counts[i] == 0:
            first_empty = i
            break
    if first_empty is None or first_empty <= 1:
        return np.ones(len(masses), dtype=bool)
    return masses < float(edges[first_empty])


def postprocess_in_lockstep(masses: np.ndarray, weights: np.ndarray,
                            im_str: str, peak_on: str) -> dict:
    """Z cut -> max-mass cut -> peak removal -> bin-aligned split, with every
    step a boolean mask applied to BOTH arrays. A length mismatch at any point
    is a hard error."""
    if len(masses) != len(weights):
        raise SystemExit(
            f"IM {im_str}: {len(masses)} masses but {len(weights)} weights -- "
            "alignment lost. This builder never falls back to unweighted.")
    fake_sig = f"x_FS_x_IM_{im_str}"   # the shape _dilepton_flavor parses
    stages = {"n_input": int(len(masses))}

    keep = z_peak_keep_mask(masses, fake_sig)
    if MAX_MASS_CUTOFF > 0:
        keep = keep & (masses <= MAX_MASS_CUTOFF)
    masses, weights = masses[keep], weights[keep]
    stages["n_after_z_and_max_mass"] = int(len(masses))
    if len(masses) == 0:
        return {**stages, "empty_at": "z_and_max_mass"}

    peak_weights = weights if peak_on == "weighted" else None
    peak_mass = find_peak_mass(masses, peak_weights)
    stages["peak_mass"] = peak_mass
    stages["peak_on"] = peak_on
    if peak_mass is not None:
        keep = masses >= peak_mass
        masses, weights = masses[keep], weights[keep]
    stages["n_after_peak_removal"] = int(len(masses))
    if len(masses) == 0:
        return {**stages, "empty_at": "peak_removal"}

    main_mask = main_split_mask(masses)
    stages["n_main"] = int(np.count_nonzero(main_mask))
    stages["n_outliers"] = int(np.count_nonzero(~main_mask))
    if len(masses) != len(weights):
        raise SystemExit(f"IM {im_str}: lockstep broken before the split")
    return {
        **stages,
        "main_masses": masses[main_mask],
        "main_weights": weights[main_mask],
        "outlier_masses": masses[~main_mask],
        "outlier_weights": weights[~main_mask],
    }


# --------------------------------------------------------------------------
# build
# --------------------------------------------------------------------------

def event_union_mask(acceptance_bitmask: np.ndarray) -> np.ndarray:
    """The event union for THIS build: the four data acceptance flags only.
    The SingleElectron candidate (bit 4) is stored and deliberately ignored."""
    four_bits = sum(MC_ACC_BIT_BY_LABEL.values())
    return (np.asarray(acceptance_bitmask).astype(np.int64) & four_bits) != 0


def collect_signature_arrays(shard_paths: list, suffix: str = "") -> dict:
    """{signature: [chunk, ...]} over every shard, for the mass signatures
    (suffix="") or one sibling family."""
    out = defaultdict(list)
    for path in shard_paths:
        for sig in list_signatures(path):
            if suffix:
                if not sig.endswith(suffix):
                    continue
                base = sig[: -len(suffix)]
                if not SIG_PATTERN.search(base):
                    continue
                key = base
            else:
                if not SIG_PATTERN.search(sig):
                    continue
                key = sig
            for chunk in iter_arrays_for_signature(path, sig):
                if len(chunk):
                    out[key].append(chunk)
    return dict(out)


def build(args) -> dict:
    runs_dir = pathlib.Path(args.runs_dir)
    out_dir = pathlib.Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    registry = load_registry()
    only_records = ({int(r) for r in args.records.split(",") if r.strip()}
                    if args.records else None)
    only_files = ({int(r) for r in args.file_indices.split(",") if r.strip()}
                  if args.file_indices else None)
    jobs_by_record = discover_jobs(runs_dir, only_records, only_files)

    report = {
        "what": "CMS MC delivery build (studies/cms_mc_weights_v3)",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "git_commit": git_commit_hash(REPO_ROOT),
        "runs_dir": str(runs_dir),
        "out_dir": str(out_dir),
        "is_smoke_test": bool(args.smoke_test),
        "options": {
            "peak_on": args.peak_on,
            "min_events_basis": args.min_events_basis,
            "output_mode": args.output_mode,
            "min_events_per_fs": args.min_events_per_fs,
        },
        "constants": {
            "target_luminosity_fb": TARGET_LUMINOSITY_FB,
            "z_peak_cutoff_gev": Z_PEAK_CUTOFF,
            "max_mass_cutoff_gev": MAX_MASS_CUTOFF,
            "bin_width_gev": BIN_WIDTH_GEV,
            "n_bins": _n_bins(),
            "sigma_w_tolerance": SIGMA_W_TOLERANCE,
            "shard_read": SHARD_NAME,
            "event_union": "the four data acceptance flags only; the "
                           "SingleElectron candidate is stored and ignored",
        },
        "samples": {},
    }
    if args.smoke_test:
        report["SMOKE_TEST_WARNING"] = (
            "THIS IS A SMOKE TEST, NOT A PHYSICS RESULT. Sigma-w comes from the "
            "probed file(s) only, so every weight is normalised as if that file "
            "were the whole sample. Yields are meaningless as physics; the point "
            "is that the chain runs end to end and the arithmetic closes.")

    scratch_root = pathlib.Path(
        args.scratch_dir or tempfile.mkdtemp(prefix="mc_delivery_"))
    scratch_root.mkdir(parents=True, exist_ok=True)

    # ---- per sample: guards, Sigma-w, scratch copies, _mcw --------------
    all_scratch_shards = []
    shards_by_record = {}
    for rid, job_list in sorted(jobs_by_record.items(), key=lambda kv: int(kv[0])):
        if rid not in registry["records"]:
            raise SystemExit(
                f"STOP: record {rid} is not in {REGISTRY_PATH.name}. An unknown "
                "record is a hard error (DESIGN.md D4) -- nothing is ever stored "
                "unweighted.")
        record = registry["records"][rid]
        campaign = assert_campaign_ok(rid, record)
        sw = sigma_w_for_sample(rid, job_list)
        norm = normalisation_factor(record, sw["sigma_w"])

        sample_scratch = scratch_root / f"record_{rid}"
        sample_scratch.mkdir(parents=True, exist_ok=True)
        scratch_shards = []
        weight_stats = []
        for job in sw["surviving"]:
            dest = sample_scratch / f"job_{job['file_index']}_{SHARD_NAME}"
            shutil.copy2(job["shard"], dest)
            cap_scales = read_cap_scales(str(dest))
            weight_stats.append({
                "file_index": job["file_index"],
                "capped_signatures": cap_scales,
                **write_mcw_siblings(str(dest), norm, cap_scales),
            })
            scratch_shards.append(str(dest))
        shards_by_record[rid] = scratch_shards
        all_scratch_shards.extend(scratch_shards)

        report["samples"][rid] = {
            "physics_short": record["physics_short"],
            "cross_section_pb_sigma_eff": record["cross_section_pb"],
            "k_factor": record["k_factor"],
            "gen_filt_eff": record["gen_filt_eff"],
            "campaign_guard": campaign,
            "sigma_w_over_surviving_files": sw["sigma_w"],
            "n_files_included": sw["n_files_included"],
            "n_files_excluded": sw["n_files_excluded"],
            "per_file_sigma_w": sw["per_file"],
            "normalisation_factor": norm,
            "normalisation_formula": "sigma_eff[pb] * 1000 * k * eps * L_fb / Sigma-w",
            "weight_write_stats": weight_stats,
            "n_capped_signatures_total": sum(
                len(ws["capped_signatures"]) for ws in weight_stats),
        }
        print(f"[{rid}] {record['physics_short']}: sigma_eff="
              f"{record['cross_section_pb']:g} pb, Sigma-w={sw['sigma_w']:.6e} over "
              f"{sw['n_files_included']} file(s) ({sw['n_files_excluded']} excluded), "
              f"norm={norm:.6e}", flush=True)

    # ---- the >=100 rule, ONCE, on the combined shards -------------------
    # Applied over every surviving file of every sample at once, so all samples
    # share one surviving final-state set and the per-sample and summed files
    # agree on which categories exist.
    pruned = prune_final_states_below_min_events(
        all_scratch_shards, args.min_events_per_fs)
    report["prune"] = {
        "basis": args.min_events_basis,
        "min_events_per_fs": args.min_events_per_fs,
        "applied_to_n_shards": len(all_scratch_shards),
        "applied": "once, on the combined shards of every surviving file of "
                   "every sample",
        "n_final_states_removed": len(pruned),
        "final_states_removed": pruned,
    }
    if args.min_events_basis == "weighted":
        report["prune"]["note"] = (
            "--min-events-basis weighted was requested, but the shared "
            "prune_final_states_below_min_events counts RAW entries; the "
            "weighted basis is applied as an ADDITIONAL per-histogram cut "
            "below, leaving the shared data-side rule untouched.")
    # No orphan siblings may remain for a pruned final state (D3).
    orphans = []
    for path in all_scratch_shards:
        for sig in list_signatures(path):
            for fs in pruned:
                if fs in sig:
                    orphans.append(f"{pathlib.Path(path).name}:{sig}")
    if orphans:
        raise SystemExit(
            f"STOP: {len(orphans)} orphan row(s) survived the prune: "
            f"{orphans[:10]}. The sqlite_shards sibling regex fix is not in "
            "effect.")
    report["prune"]["n_orphan_rows_after_prune"] = 0

    # ---- per-sample histograms ------------------------------------------
    per_sample_hists = {}
    for rid, shard_paths in sorted(shards_by_record.items(), key=lambda kv: int(kv[0])):
        hists, diag = histograms_for_shards(shard_paths, args)
        per_sample_hists[rid] = hists
        report["samples"][rid]["histograms"] = diag
        print(f"[{rid}] {len(hists)} histogram(s) after post-processing", flush=True)

    # ---- outputs ---------------------------------------------------------
    written = {}
    if args.output_mode in ("per-sample", "both"):
        for rid, hists in per_sample_hists.items():
            if not hists:
                continue
            path = out_dir / f"{args.out_prefix}_record{rid}_mc.root"
            written[str(path)] = write_weighted_root(path, hists)
    if args.output_mode in ("summed", "both"):
        summed = sum_histograms(per_sample_hists)
        if summed:
            path = out_dir / f"{args.out_prefix}_summedSM_mc.root"
            written[str(path)] = write_weighted_root(path, summed)
            report["summed_sm"] = {
                "n_histograms": len(summed),
                "n_samples_summed": len(per_sample_hists),
                "negative_bin_inventory": {
                    name: negative_or_empty_bin_inventory(v, s)
                    for name, (v, s, _e, _n) in summed.items()
                },
            }
    report["outputs"] = {p: {"n_histograms": len(v)} for p, v in written.items()}
    report["readback_assertions"] = {p: v for p, v in written.items()}

    if not args.keep_scratch:
        shutil.rmtree(scratch_root, ignore_errors=True)
        report["scratch_removed"] = str(scratch_root)
    else:
        report["scratch_kept"] = str(scratch_root)

    report_path = out_dir / f"{args.out_prefix}_build_report.json"
    report_path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    print(f"\nwrote {report_path}")
    return report


def histograms_for_shards(shard_paths: list, args) -> tuple[dict, dict]:
    """{bumpnet_name: (sum_w, sum_w2, edges, n_raw_entries)} plus diagnostics."""
    masses_by_sig = collect_signature_arrays(shard_paths)
    weights_by_sig = collect_signature_arrays(shard_paths, MC_WEIGHT_SUFFIX)
    acc_by_sig = collect_signature_arrays(shard_paths, MC_SIBLING_ACCEPTANCE)

    grouped = defaultdict(list)
    for sig in sorted(masses_by_sig):
        m = SIG_PATTERN.search(sig)
        fs_str, im_str = m.groups()
        grouped[_convert_to_bumpnet_name(fs_str, im_str)].append((sig, im_str))

    hists = {}
    diag = {
        "n_mass_signatures": len(masses_by_sig),
        "n_bumpnet_names_before_postprocessing": len(grouped),
        "per_histogram": {},
        "raw_yield_by_final_state": defaultdict(int),
        "weighted_yield_by_final_state": defaultdict(float),
        "n_dropped_empty": 0,
        "n_dropped_min_events_weighted": 0,
        "n_entries_dropped_by_event_union": 0,
    }
    for name, entries in sorted(grouped.items()):
        mass_chunks, weight_chunks, im_str = [], [], None
        for sig, im in sorted(entries):
            im_str = im
            m_parts = masses_by_sig[sig]
            w_parts = weights_by_sig.get(sig)
            a_parts = acc_by_sig.get(sig)
            if not w_parts:
                raise SystemExit(
                    f"{name}: signature {sig} has masses but no "
                    f"{MC_WEIGHT_SUFFIX} sibling. HARD ERROR -- no unweighted "
                    "fallback exists in this builder.")
            mm = np.concatenate([np.asarray(c, dtype=np.float64) for c in m_parts])
            ww = np.concatenate([np.asarray(c, dtype=np.float64) for c in w_parts])
            if len(mm) != len(ww):
                raise SystemExit(
                    f"{name}: signature {sig} has {len(mm)} masses and {len(ww)} "
                    "weights. HARD ERROR.")
            if a_parts:
                aa = np.concatenate([np.asarray(c) for c in a_parts])
                if len(aa) != len(mm):
                    raise SystemExit(
                        f"{name}: signature {sig} acceptance bitmask length "
                        f"{len(aa)} != {len(mm)} masses. HARD ERROR.")
                union = event_union_mask(aa)
                diag["n_entries_dropped_by_event_union"] += int((~union).sum())
                mm, ww = mm[union], ww[union]
            mass_chunks.append(mm)
            weight_chunks.append(ww)
        if not mass_chunks:
            continue
        masses = np.concatenate(mass_chunks)
        weights = np.concatenate(weight_chunks)
        if masses.size == 0:
            diag["n_dropped_empty"] += 1
            continue

        fs_str = SIG_PATTERN.search(sorted(entries)[0][0]).group(1)
        diag["raw_yield_by_final_state"][fs_str] += int(masses.size)
        diag["weighted_yield_by_final_state"][fs_str] += float(weights.sum())

        pp = postprocess_in_lockstep(masses, weights, im_str, args.peak_on)
        if "main_masses" not in pp:
            diag["n_dropped_empty"] += 1
            diag["per_histogram"][name] = {**pp, "kept": False}
            continue
        main_m, main_w = pp["main_masses"], pp["main_weights"]
        if main_m.size == 0:
            diag["n_dropped_empty"] += 1
            diag["per_histogram"][name] = {**_scrub(pp), "kept": False}
            continue
        if args.min_events_basis == "weighted" and main_w.sum() < args.min_events_per_fs:
            diag["n_dropped_min_events_weighted"] += 1
            diag["per_histogram"][name] = {
                **_scrub(pp), "kept": False,
                "dropped_by": "min-events-basis weighted"}
            continue

        sum_w, sum_w2, edges = fill_weighted_fixed_grid(main_m, main_w)
        hists[name] = (sum_w, sum_w2, edges, int(main_m.size))
        diag["per_histogram"][name] = {
            **_scrub(pp),
            "kept": True,
            "n_raw_entries": int(main_m.size),
            "weighted_yield": float(main_w.sum()),
            "sum_w_in_hist": float(sum_w.sum()),
            "sum_w2_in_hist": float(sum_w2.sum()),
            "negative_bin_inventory": negative_or_empty_bin_inventory(sum_w, sum_w2),
        }
    diag["raw_yield_by_final_state"] = dict(diag["raw_yield_by_final_state"])
    diag["weighted_yield_by_final_state"] = dict(diag["weighted_yield_by_final_state"])
    diag["n_histograms_kept"] = len(hists)
    return hists, diag


def _scrub(pp: dict) -> dict:
    """Drop the arrays from a post-processing record so it is JSON-sized."""
    return {k: v for k, v in pp.items() if not isinstance(v, np.ndarray)}


def sum_histograms(per_sample: dict) -> dict:
    """Sum the per-sample histograms bin by bin: contents add, and so do the
    sum-of-w^2 (variances are additive for independent samples)."""
    summed = {}
    for hists in per_sample.values():
        for name, (sum_w, sum_w2, edges, n_raw) in hists.items():
            if name not in summed:
                summed[name] = [sum_w.copy(), sum_w2.copy(), edges, n_raw]
            else:
                summed[name][0] += sum_w
                summed[name][1] += sum_w2
                summed[name][3] += n_raw
    return {k: tuple(v) for k, v in summed.items()}


def write_weighted_root(path: pathlib.Path, hists: dict) -> dict:
    """TH1D + Sumw2, names identical to data, asserted on read-back."""
    expected = {}
    with uproot.recreate(str(path)) as fout:
        for name, (sum_w, sum_w2, edges, n_raw) in sorted(hists.items()):
            key = roi_key(name, upstream_width_suffix=True)
            fout[key] = to_writable_th1d(sum_w, sum_w2, edges, key, n_raw)
            expected[key] = (sum_w, sum_w2)
    checked = verify_written_th1d(str(path), expected)
    print(f"wrote {path} -- {len(expected)} TH1D histogram(s), all read-back "
          f"assertions passed", flush=True)
    return {"path": str(path), "n_histograms": len(expected),
            "all_readback_assertions_passed": True,
            "checked_sample": dict(list(checked.items())[:3])}


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--runs-dir", required=True,
                   help="directory holding the --is-mc per-file job_*/ outputs")
    p.add_argument("--out-dir", required=True)
    p.add_argument("--out-prefix", required=True)
    p.add_argument("--records", default=None,
                   help="comma-separated record IDs to build (default: all found)")
    p.add_argument("--file-indices", default=None,
                   help="comma-separated file indices to build (default: all found)")
    p.add_argument("--peak-on", choices=("weighted", "unweighted"), default="weighted",
                   help="locate the removed peak on the weighted or the unweighted "
                        "spectrum. Default weighted (PR #35's semantics, DESIGN.md "
                        "D6); 'unweighted' answers the open question for Yuval "
                        "without a re-run.")
    p.add_argument("--min-events-basis", choices=("raw", "weighted"), default="raw",
                   help="basis for the >=100-per-final-state rule. Default raw, so "
                        "the rule means the same thing in MC as in data; 'weighted' "
                        "adds a weighted-yield floor on top, leaving the shared "
                        "data-side prune untouched.")
    p.add_argument("--output-mode", choices=("per-sample", "summed", "both"),
                   default="both",
                   help="per-sample ROOT files, one summed-SM file, or both. "
                        "Default both -- the open question for Maryna.")
    p.add_argument("--min-events-per-fs", type=int, default=PRIMARY_MIN_EVENTS_PER_FS)
    p.add_argument("--scratch-dir", default=None,
                   help="where to copy the shards for mutation (default: a temp dir)")
    p.add_argument("--keep-scratch", action="store_true")
    p.add_argument("--smoke-test", action="store_true",
                   help="label the report as a SMOKE TEST, not a physics result "
                        "(use whenever Sigma-w comes from fewer files than the "
                        "sample has)")
    args = p.parse_args()
    build(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
