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
     a HARD ERROR, never a fallback to unweighted. With --peak-scope combined
     (the default) the peak-removal and split masses of each histogram name
     are found ONCE on the combined spectrum of all samples and applied to
     every sample, so the summed SM is "sum, then cut" like the data.
  8. Writes TH1D + Sumw2 with names identical to data, asserts them on
     read-back, and reports per-sample Sigma-w, file counts, cap incidence,
     raw and weighted yields per final state, and the negative/empty-bin
     inventory.

Build-time OPTIONS, so an answer from Maryna or Yuval needs no re-run:
  --peak-on {weighted,unweighted}   [weighted]
  --peak-scope {combined,per-sample} [combined]
  --min-events-basis {raw,weighted} [raw]
  --output-mode {per-sample,summed,both} [both]

No negative-bin fix is implemented -- only the inventory is reported. That
choice is Maryna's (DESIGN.md open questions).

The event union for this build is the FIVE delivered acceptance flags
(Maryna, 20 Oct 2026): the four data flags OR the SingleElectron
acceptance (driver bit 6, the T = 32 GeV rule). The bare SingleElectron
candidate (bit 4, no offline cut) and the Ele27 fire bit (bit 5) are stored
by the driver and are NOT part of the union. Shards made before bit 6
existed are refused (discover_jobs).
"""
from __future__ import annotations

import argparse
import json
import logging
import pathlib
import re
import shutil
import sqlite3
import sys
import tempfile
from collections import defaultdict
from datetime import datetime, timezone

import numpy as np

REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

from domain.metadata import MCDatasetMetadata  # noqa: E402
from services.calculations.mc_weights import compute_normalization  # noqa: E402
from services.pipelines.post_processing_pipeline import (  # noqa: E402
    _aligned_bin_edges,
    _dilepton_flavor,
    _find_rightmost_highest_peak,
)
from services.storage.sqlite_shards import (  # noqa: E402
    SqliteArrayShardWriter,
    _deserialize_array,
    iter_arrays_for_signature,
    list_signatures,
)
from studies.cms_mc_weights_v3.deliver.cms_shard_pruning import (  # noqa: E402
    prune_final_states_below_min_events,  # CMS copy with the D3 sibling change
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
    MC_ACC_BIT_SINGLEELECTRON,
    MC_ACC_BITS_DELIVERY_UNION,
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
LOGGER = logging.getLogger("build_mc_delivery")

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


def assert_in_full_run(record_id: str, record: dict) -> None:
    """Matan, 15 Oct 2026: a record whose registry entry has
    in_full_run = false (e.g. 35671, which would double-count Drell-Yan with
    35669) must never be weighted into a delivery. Hard error, naming the
    record and the registry's reason."""
    if record.get("in_full_run") is True:
        return
    reason = ((record.get("decision_2026_10_15") or {})
              .get("not_in_full_run_reason")
              or "no reason recorded in the registry")
    raise SystemExit(
        f"STOP: record {record_id} ({record.get('physics_short', '?')}) has "
        f"in_full_run = {record.get('in_full_run')!r} in {REGISTRY_PATH.name} "
        f"and is refused by the builder. Reason: {reason}")


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
        bit_map = (meta.get("mc_diagnostics") or {}).get("acceptance_bit_map")
        if bit_map is not None and bit_map.get("SingleElectron") != MC_ACC_BIT_SINGLEELECTRON:
            raise SystemExit(
                f"STOP: {meta_path} has no SingleElectron acceptance bit "
                f"({MC_ACC_BIT_SINGLEELECTRON}) in its acceptance_bit_map: it was "
                "made before the five-flag union (20 Oct 2026). Re-produce it "
                "with the current driver.")
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

def read_shard_arrays(shard_path: str) -> dict:
    """{signature: [chunk, ...]} for a whole shard, from ONE sqlite connection.

    The shared `iter_arrays_for_signature` / `list_signatures` open a NEW
    connection per call and close it only when the garbage collector gets
    round to it (`with sqlite3.connect(...)` commits but does not close). At
    pilot scale that is fatal: a ttbar shard holds 28,788 signatures, and
    calling them per signature pushes the process past `ulimit -n` (1024 on
    the analysis node) between collections, which surfaces as
    `sqlite3.OperationalError: unable to open database file`.

    Reading each shard in a single pass through a single read-only connection
    fixes that and is far faster. The shared functions are deliberately NOT
    modified: they are on the delivered data path, and this round may not
    change it.
    """
    conn = sqlite3.connect(
        f"file:{pathlib.Path(shard_path).as_posix()}?mode=ro", uri=True)
    try:
        rows = conn.execute(
            "SELECT signature, payload FROM array_chunks ORDER BY id").fetchall()
    finally:
        conn.close()
    out = defaultdict(list)
    for signature, payload in rows:
        arr = _deserialize_array(payload)
        if len(arr):
            out[signature].append(arr)
    return dict(out)


def normalisation_factor(record: dict, sigma_w: float) -> float:
    """sigma_eff[pb] * 1000 * k * eps * L_fb / Sigma-w, with k = eps = 1.

    The arithmetic is upstream #35's own compute_normalization; the inputs
    stay CMS's: sigma_eff from the registry and Sigma-w measured over the
    surviving files. Bit-identical to the previous inline formula
    (tests/test_upstream35_drift.py pins its output)."""
    k = float(record["k_factor"])
    eps = float(record["gen_filt_eff"])
    if k != 1.0 or eps != 1.0:
        raise SystemExit(
            f"record {record['record_id']}: k_factor={k} gen_filt_eff={eps}. "
            "Both must be exactly 1.0 -- every correction is already inside "
            "cross_section_pb (see the registry header). Refusing to apply a "
            "correction twice.")
    metadata = MCDatasetMetadata(
        dataset_number=int(record["record_id"]),
        cross_section_pb=float(record["cross_section_pb"]),
        sum_of_weights=sigma_w,
        k_factor=k,
        gen_filt_eff=eps,
        physics_short=record.get("physics_short"),
    )
    return compute_normalization(metadata, TARGET_LUMINOSITY_FB)


def write_mcw_siblings(shard_path: str, norm: float, cap_scales: dict) -> dict:
    """D4/D8: compute w_event per entry and write it as the `_mcw` sibling.

    One mass chunk and one sibling chunk per signature per file (the funnel
    writes them together), so the pairing is 1:1. Any length mismatch is a
    HARD ERROR -- there is no unweighted fallback anywhere in this builder.
    """
    chunks = read_shard_arrays(shard_path)
    writer = SqliteArrayShardWriter(shard_path)
    n_written = 0
    n_entries = 0
    n_capped_applied = 0
    try:
        for sig in sorted(chunks):
            if not SIG_PATTERN.search(sig):
                continue  # a sibling, or not a mass signature
            masses = chunks.get(sig, [])
            genw = chunks.get(sig + MC_SIBLING_GENWEIGHT, [])
            l1pf = chunks.get(sig + MC_SIBLING_L1PREFIRE, [])
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
    """The rightmost highest peak on the aligned grid: upstream #35's own
    `_find_rightmost_highest_peak` (with its `weights` argument), returned
    as a plain float as before. tests/test_upstream35_drift.py pins its
    behaviour on fixed inputs."""
    peak = _find_rightmost_highest_peak(masses, BIN_WIDTH_GEV, LOGGER, weights=weights)
    return None if peak is None else float(peak)


def split_mass(masses: np.ndarray) -> float | None:
    """The low edge of the first empty bin (UNWEIGHTED counts, aligned grid),
    i.e. where main_split_mask splits; None means "keep everything"."""
    if len(masses) == 0:
        return None
    edges = _aligned_bin_edges(masses, BIN_WIDTH_GEV)
    counts, _ = np.histogram(masses, bins=edges)
    if len(counts) == 0:
        return None
    first_empty = None
    for i in range(len(counts)):
        if counts[i] == 0:
            first_empty = i
            break
    if first_empty is None or first_empty <= 1:
        return None
    return float(edges[first_empty])


def main_split_mask(masses: np.ndarray) -> np.ndarray:
    """The first-empty-bin split as a MASK, on UNWEIGHTED counts (PR #35's own
    semantics: the split is a statement about where the spectrum runs out of
    entries, not about weight)."""
    if len(masses) == 0:
        return np.zeros(0, dtype=bool)
    split = split_mass(masses)
    if split is None:
        return np.ones(len(masses), dtype=bool)
    return masses < split


def z_and_max_mass_mask(masses: np.ndarray, im_str: str) -> np.ndarray:
    """The Z cut and the max-mass cut together (both independent of the
    sample)."""
    keep = z_peak_keep_mask(masses, f"x_FS_x_IM_{im_str}")
    if MAX_MASS_CUTOFF > 0:
        keep = keep & (masses <= MAX_MASS_CUTOFF)
    return keep


def combined_cuts(per_sample: list, im_str: str, peak_on: str) -> dict:
    """--peak-scope combined: the peak-removal mass and the outlier-split mass
    of ONE histogram name, found ONCE on the combined spectrum.

    `per_sample` is [(masses, weights), ...] in record order. Each sample's
    Z cut and max-mass cut are applied, the survivors are concatenated, and
    the SAME rules as postprocess_in_lockstep are used: the weighted (or
    unweighted, per --peak-on) rightmost-highest peak on the aligned grid,
    then the first-empty-bin split on the unweighted counts above the peak.
    With a single sample this reproduces that sample's own cuts exactly."""
    ms, ws = [], []
    for masses, weights in per_sample:
        keep = z_and_max_mass_mask(masses, im_str)
        ms.append(masses[keep])
        ws.append(weights[keep])
    masses = np.concatenate(ms) if ms else np.zeros(0)
    weights = np.concatenate(ws) if ws else np.zeros(0)
    out = {"n_samples": len(per_sample),
           "n_combined_after_z_and_max_mass": int(len(masses))}
    if len(masses) == 0:
        return {**out, "peak_mass": None, "split_mass": None,
                "combined_main_weight": 0.0}
    peak = find_peak_mass(masses, weights if peak_on == "weighted" else None)
    if peak is not None:
        keep = masses >= peak
        masses, weights = masses[keep], weights[keep]
    split = split_mass(masses)
    main = np.ones(len(masses), dtype=bool) if split is None else masses < split
    return {**out, "peak_mass": peak, "split_mass": split,
            "combined_main_weight": float(weights[main].sum())}


def postprocess_in_lockstep(masses: np.ndarray, weights: np.ndarray,
                            im_str: str, peak_on: str,
                            cuts: dict | None = None) -> dict:
    """Z cut -> max-mass cut -> peak removal -> bin-aligned split, with every
    step a boolean mask applied to BOTH arrays. A length mismatch at any point
    is a hard error.

    cuts=None (--peak-scope per-sample) finds the peak and the split on THIS
    spectrum. cuts=combined_cuts(...) (--peak-scope combined) applies the
    peak mass and split mass found once on the combined spectrum instead."""
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

    if cuts is None:
        peak_weights = weights if peak_on == "weighted" else None
        peak_mass = find_peak_mass(masses, peak_weights)
    else:
        peak_mass = cuts["peak_mass"]
    stages["peak_mass"] = peak_mass
    stages["peak_on"] = peak_on
    stages["peak_scope"] = "per-sample" if cuts is None else "combined"
    if peak_mass is not None:
        keep = masses >= peak_mass
        masses, weights = masses[keep], weights[keep]
    stages["n_after_peak_removal"] = int(len(masses))
    if len(masses) == 0:
        return {**stages, "empty_at": "peak_removal"}

    if cuts is None:
        main_mask = main_split_mask(masses)
    else:
        split = cuts["split_mass"]
        stages["split_mass"] = split
        main_mask = (np.ones(len(masses), dtype=bool) if split is None
                     else masses < split)
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
    """The event union for THIS build: the four data acceptance flags OR the
    SingleElectron acceptance (bit 6, T = 32 GeV) -- the five delivered
    datasets. The SingleElectron candidate (bit 4) and the Ele27 fire bit
    (bit 5) are stored and are not part of the union."""
    return (np.asarray(acceptance_bitmask).astype(np.int64)
            & MC_ACC_BITS_DELIVERY_UNION) != 0


def collect_signature_arrays(shard_paths: list, suffix: str = "") -> dict:
    """{signature: [chunk, ...]} over every shard, for the mass signatures
    (suffix="") or one sibling family."""
    out = defaultdict(list)
    for path in shard_paths:
        for sig, sig_chunks in read_shard_arrays(path).items():
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
            out[key].extend(sig_chunks)
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
            "peak_scope": args.peak_scope,
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
            "event_union": "the five delivered acceptance flags: the four data "
                           "flags OR SingleElectron (bit 6, offline pT > 32 GeV); "
                           "the bare Ele27 candidate (bit 4) is not used",
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

    # ---- refuse records excluded from the full run, before any work ------
    for rid in sorted(jobs_by_record, key=int):
        if rid in registry["records"]:
            assert_in_full_run(rid, registry["records"][rid])

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
            f"{orphans[:10]}. The sibling-aware prune (cms_shard_pruning.py, "
            "DESIGN.md D3) is not in effect.")
    report["prune"]["n_orphan_rows_after_prune"] = 0

    # ---- per-sample histograms ------------------------------------------
    per_sample_hists = {}
    record_order = sorted(shards_by_record, key=int)
    if args.peak_scope == "per-sample":
        # Each sample cut at its own peak/split (the 17-18 Oct full-run
        # build); kept only to reproduce that build.
        for rid in record_order:
            hists, diag = histograms_for_shards(shards_by_record[rid], args)
            per_sample_hists[rid] = hists
            report["samples"][rid]["histograms"] = diag
            print(f"[{rid}] {len(hists)} histogram(s) after post-processing", flush=True)
    else:
        # --peak-scope combined (Matan's decision, 18 Oct 2026, option A): the
        # peak and split of each name are found ONCE on all samples together
        # and the same cut is applied to every sample, so the per-sample
        # files sum exactly to the summed-SM file, cut like the data.
        arrays_by_record, diags = {}, {}
        for rid in record_order:
            arrays_by_record[rid], diags[rid] = name_arrays_for_shards(shards_by_record[rid])
            print(f"[{rid}] {len(arrays_by_record[rid])} name(s) collected", flush=True)
        names = sorted(set().union(*(a.keys() for a in arrays_by_record.values())))
        cuts_by_name = {}
        for name in names:
            present = [arrays_by_record[rid][name] for rid in record_order
                       if name in arrays_by_record[rid]]
            cuts_by_name[name] = combined_cuts(
                [(m, w) for m, w, _im in present], present[0][2], args.peak_on)
        report["combined_cuts"] = cuts_by_name
        for rid in record_order:
            hists = histograms_from_name_arrays(
                arrays_by_record.pop(rid), diags[rid], args, cuts_by_name)
            per_sample_hists[rid] = hists
            report["samples"][rid]["histograms"] = diags[rid]
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
    """{bumpnet_name: (sum_w, sum_w2, edges, n_raw_entries)} plus diagnostics,
    for ONE sample with its own cuts (--peak-scope per-sample)."""
    arrays, diag = name_arrays_for_shards(shard_paths)
    hists = histograms_from_name_arrays(arrays, diag, args, None)
    return hists, diag


def name_arrays_for_shards(shard_paths: list) -> tuple[dict, dict]:
    """{bumpnet_name: (masses, weights, im_str)} for one sample, after the
    event union and BEFORE any post-processing, plus the diagnostics of that
    stage."""
    masses_by_sig = collect_signature_arrays(shard_paths)
    weights_by_sig = collect_signature_arrays(shard_paths, MC_WEIGHT_SUFFIX)
    acc_by_sig = collect_signature_arrays(shard_paths, MC_SIBLING_ACCEPTANCE)

    grouped = defaultdict(list)
    for sig in sorted(masses_by_sig):
        m = SIG_PATTERN.search(sig)
        fs_str, im_str = m.groups()
        grouped[_convert_to_bumpnet_name(fs_str, im_str)].append((sig, im_str))

    arrays = {}
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
        arrays[name] = (masses, weights, im_str)
    diag["raw_yield_by_final_state"] = dict(diag["raw_yield_by_final_state"])
    diag["weighted_yield_by_final_state"] = dict(diag["weighted_yield_by_final_state"])
    return arrays, diag


def histograms_from_name_arrays(arrays: dict, diag: dict, args,
                                cuts_by_name: dict | None) -> dict:
    """Post-process and fill one sample's histograms. cuts_by_name=None: each
    histogram is cut at its own peak/split (per-sample scope); otherwise at
    the combined cuts of its name, and the weighted min-events floor (if
    requested) is judged on the combined spectrum too, so every sample keeps
    or drops a name together."""
    hists = {}
    for name, (masses, weights, im_str) in sorted(arrays.items()):
        cuts = None if cuts_by_name is None else cuts_by_name[name]
        pp = postprocess_in_lockstep(masses, weights, im_str, args.peak_on, cuts)
        if "main_masses" not in pp:
            diag["n_dropped_empty"] += 1
            diag["per_histogram"][name] = {**pp, "kept": False}
            continue
        main_m, main_w = pp["main_masses"], pp["main_weights"]
        if main_m.size == 0:
            diag["n_dropped_empty"] += 1
            diag["per_histogram"][name] = {**_scrub(pp), "kept": False}
            continue
        floor_w = main_w.sum() if cuts is None else cuts["combined_main_weight"]
        if args.min_events_basis == "weighted" and floor_w < args.min_events_per_fs:
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
    diag["n_histograms_kept"] = len(hists)
    return hists


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
    p.add_argument("--peak-scope", choices=("combined", "per-sample"), default="combined",
                   help="where the peak-removal and outlier-split masses are found. "
                        "Default combined: once per histogram name on all samples "
                        "together, then applied to every sample, so the summed SM "
                        "is cut like the data and the per-sample files sum to it "
                        "exactly (Matan, 18 Oct 2026). 'per-sample' cuts each "
                        "sample at its own peak and exists only to reproduce the "
                        "17-18 Oct full-run build.")
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
