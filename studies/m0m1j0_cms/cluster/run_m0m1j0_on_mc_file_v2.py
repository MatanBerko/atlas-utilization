#!/usr/bin/env python
"""
Phase-1 MC weights task -- per-job MC driver (amendment A1, A5).

One job = one CMS NanoAODSIM file (one MC record's file list, by index --
same portal-API resolution as the data driver,
studies.m0m1j0_cms.design_checks.common.fetch_file_list).

A1 -- SAME selection/invariant-mass/final-state-category functions as the
DoubleMuon DATA driver, imported and called, never copied:
  - Event-level selection: studies.m0m1j0_cms.selection
    .select_event_selection_cutflow -- BYTE-IDENTICAL call to
    run_m0m1j0_on_file.py's own (studies/m0m1j0_cms/cluster/
    run_m0m1j0_on_file.py:284), same TRIGGER_BRANCHES default (the
    DoubleMuon data production's own two HLT paths --
    HLT_Mu17_TrkIsoVVL_Mu8_TrkIsoVVL_DZ,
    HLT_Mu17_TrkIsoVVL_TkMu8_TrkIsoVVL_DZ,
    studies/m0m1j0_cms/selection.py:66-69).
  - Multi-combination invariant mass (needed for the phase-1 validation
    histograms, which are NOT all the single "m0m1j0" combination --
    e.g. mass_m0m1b0_cat_..., mass_m0m1_cat_...): the SAME general
    combination machinery the ACTUAL DoubleMuon data driver that produced
    the delivered BumpNet manifest uses -- studies.cms_coverage.cluster
    .run_coverage_on_file (origin/deliver/doublemuon-bumpnet, read via
    `git show`, NOT checked out) imports and calls
    services.calculations.combinatorics.get_all_combinations,
    services.calculations.im_calculator.IMCalculator,
    services.calculations.physics_calcs (group_by_final_state,
    is_finalstate_contain_combination, filter_events_by_particle_counts,
    slice_events_by_field), services.pipelines.im_pipeline
    .prepare_im_combination_name -- ALL of those, unmodified, are used
    here too, with the SAME config constants (OBJECT_TYPES,
    MIN/MAX_PARTICLES_IN_COMBINATION, etc.) copied verbatim from that
    script (cited at each constant below) so the exact same 186
    combinations are generated.

Only differences from the data path (A1 (i)-(iii)):
  (i) NO golden-JSON (validated-runs) filter -- MC has no certified-run
      structure; applying it would remove every event (it checks real
      (run, luminosityBlock) pairs against a JSON of real data-taking
      periods, which no simulated event has). Explicitly NOT called;
      asserted below that the event count entering selection equals the
      raw read count (i.e. nothing was silently filtered by an accidental
      leftover call).
  (ii) genWeight and L1PreFiringWeight_Nom are read (REQUIRED -- fail
      loudly if either is absent, mirroring services/parsing/mc_weights.py's
      own "raise loudly rather than silently mis-detect" philosophy) and
      carried through the SAME event-level boolean-mask operations
      (apply_trigger, the final_mask slice in
      select_event_selection_cutflow) that data's own `sel_events` already
      goes through -- since those are plain `events[mask]` operations on
      the whole record, both branches survive automatically, no shared
      code touched.
  (iii) trigger requirement: SAME as data (selection.TRIGGER_BRANCHES,
      the default) -- confirmed present in Phase-1's 3 sample files by
      this driver's own read_events() (fails loudly, listed in
      job_metadata.json, if absent).

A5 -- per-file Runs-tree genEventSumw/genEventCount/genEventSumw2 read via
services.parsing.mc_weights.read_runs_tree_sums, UNMODIFIED, imported
directly -- never re-derived. Aggregation across all processed files
(aggregate_sumw_for_processed_files, ALSO unmodified) happens at MERGE
time (merge_full_v2_mc.py), not here -- this script's job_metadata.json
records this ONE file's own sums so the merge step can re-read/aggregate
them, and separately records this file's own read success/failure so a
failure is visible, never silently absorbed.

The general multi-combination extraction has ONE necessary deviation from
im_pipeline._calculate_combination_invariant_mass's own convenience
wrapper: that wrapper calls
IMCalculator.filter_by_particle_counts(..., is_exact_count=True), which
(services/calculations/physics_calcs.py:184-194) REBUILDS the record
keeping ONLY the named object-type fields -- silently dropping any extra
field (genWeight, L1PreFiringWeight_Nom) that might have been attached.
Confirmed directly (physics_calcs.py:184-194,
im_calculator.py:157-160,165-171): the underlying boolean MASK
(physics_calcs.py:144-180) is computed IDENTICALLY regardless of
is_exact_count, and the count-based masking + slice_by_field's per-object
pT-rank slicing (physics_calcs.py:214-228, a plain `events[obj] = ...`
per named object key) BOTH already preserve any unrelated field
untouched. So this driver calls the SAME two underlying calculator
methods directly (filter_by_particle_counts with is_exact_count=FALSE,
then slice_by_field) -- same mask, same slicing, genWeight/
L1PreFiringWeight_Nom preserved -- and only strips those two extra fields
itself, immediately before calling calculator.calculate_invariant_mass
(which iterates `.fields` internally and would crash on a non-jagged
extra field, im_calculator.py:42-52) -- mirroring, not reimplementing,
the exact field-selection physics_calcs.py's own is_exact_count=True
branch already does.

Usage:
    python run_m0m1j0_on_mc_file_v2.py \
        --record-id 42407 --file-index 0 \
        --output-dir /storage/agrp/berkom/atlas-utilization/work/cms_mc_phase1/42407/job_0

Writes, under --output-dir:
    mc_combinations.npz  -- one row per (signature, event): raw invariant
                            mass, genWeight, L1PreFiringWeight_Nom, for
                            EVERY non-empty (final_state, combination) this
                            file produced (all 186 combinations attempted,
                            same as the data coverage driver).
    job_metadata.json    -- file URL, n_read, golden-JSON-skip assertion,
                            cutflow, trigger branches confirmed present,
                            Runs-tree genEventSumw/genEventCount/genEventSumw2
                            for this file, sum(genWeight) over selected
                            events (cross-check only), mean
                            L1PreFiringWeight_Nom, per-signature raw event
                            counts, git commit.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

import awkward as ak  # noqa: E402
import numpy as np  # noqa: E402
import uproot  # noqa: E402

from services.calculations import physics_calcs  # noqa: E402
from services.calculations.combinatorics import get_all_combinations  # noqa: E402
from services.calculations.im_calculator import IMCalculator  # noqa: E402
from services.parsing.mc_weights import read_runs_tree_sums  # noqa: E402
from services.pipelines.im_pipeline import prepare_im_combination_name  # noqa: E402
from studies.m0m1j0_cms import selection  # noqa: E402
from studies.m0m1j0_cms.histograms import _convert_to_bumpnet_name  # noqa: E402
from studies.m0m1j0_cms.design_checks.common import fetch_file_list  # noqa: E402

MC_REQUIRED_BRANCHES = ("genWeight", "L1PreFiringWeight_Nom")

# Copied verbatim from studies/cms_coverage/cluster/run_coverage_on_file.py
# (origin/deliver/doublemuon-bumpnet, read via `git show`) -- config.yaml
# :135-144 (mass_calculation_task_config), so the SAME 186 combinations
# are generated as the real DoubleMuon data coverage run.
OBJECT_TYPES = ["Electrons", "Muons", "Jets", "BJets"]
MIN_PARTICLES_IN_COMBINATION = 1
MAX_PARTICLES_IN_COMBINATION = 4
MIN_COUNT_PARTICLE_IN_COMBINATION = 1
MAX_COUNT_PARTICLE_IN_COMBINATION = 4
MAX_TOTAL_PARTICLES_IN_COMBINATION = 4
INCLUDE_SUBLEADING = True
MAX_SUBLEADING_INDEX = 1
FIELD_TO_SLICE_BY = "pt"

READ_CHUNK_SIZE = 300_000  # studies/cms_coverage/cluster/run_coverage_on_file.py's own convention
READ_RETRY_ATTEMPTS = 4
READ_RETRY_BACKOFF_SEC = 15


def git_commit_hash(repo_root) -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=str(repo_root), text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except Exception as e:  # noqa: BLE001
        return f"UNKNOWN ({type(e).__name__}: {e})"


def resolve_file_url(record_id: int, file_index: int) -> str:
    urls = fetch_file_list(record_id)
    if file_index < 0 or file_index >= len(urls):
        raise ValueError(
            f"record {record_id}'s portal file list currently has {len(urls)} "
            f"file(s); requested file-index {file_index} is out of range."
        )
    return urls[file_index]


def _read_chunk_with_retry(tree, branches, entry_start, entry_stop, file_url):
    last_exc = None
    for attempt in range(1, READ_RETRY_ATTEMPTS + 1):
        try:
            return tree.arrays(branches, entry_start=entry_start, entry_stop=entry_stop, library="ak")
        except Exception as e:  # noqa: BLE001
            last_exc = e
            print(f"read attempt {attempt}/{READ_RETRY_ATTEMPTS} failed for {file_url} "
                  f"[{entry_start}:{entry_stop}]: {type(e).__name__}: {e}", flush=True)
            if attempt < READ_RETRY_ATTEMPTS:
                time.sleep(READ_RETRY_BACKOFF_SEC)
    raise RuntimeError(
        f"{file_url} [{entry_start}:{entry_stop}]: failed to read after {READ_RETRY_ATTEMPTS} attempts"
    ) from last_exc


def read_events_mc(file_url: str):
    """Data's own NEEDED_BRANCHES (selection.py) PLUS genWeight and
    L1PreFiringWeight_Nom, REQUIRED (fail loudly if absent -- A1(ii)/(iii),
    services/parsing/mc_weights.py's own philosophy). Trigger branches are
    already inside NEEDED_BRANCHES (selection.TRIGGER_BRANCHES), so their
    presence is checked by the same missing-branch check as everything
    else -- reported explicitly in job_metadata.json regardless."""
    tree = uproot.open(file_url)["Events"]
    available = set(tree.keys())
    required = list(selection.NEEDED_BRANCHES) + list(MC_REQUIRED_BRANCHES)
    missing = [b for b in required if b not in available]
    if missing:
        raise ValueError(
            f"{file_url}: missing required branch(es): {missing}. This MC "
            f"driver requires genWeight and L1PreFiringWeight_Nom in "
            f"addition to every data-side required branch; refusing to "
            f"proceed rather than silently weighting events as 1.0."
        )
    trigger_present = {b: (b in available) for b in selection.TRIGGER_BRANCHES}

    n_entries = tree.num_entries
    chunks = []
    for start in range(0, n_entries, READ_CHUNK_SIZE):
        stop = min(start + READ_CHUNK_SIZE, n_entries)
        chunks.append(_read_chunk_with_retry(tree, required, start, stop, file_url))
    events = ak.concatenate(chunks) if len(chunks) > 1 else chunks[0]
    return events, trigger_present


def compute_all_combination_signatures(obj_record_with_weights: ak.Array, job_tag: str, logger):
    """Mirrors studies.cms_coverage.cluster.run_coverage_on_file's main
    loop (group_by_final_state -> is_finalstate_contain_combination ->
    filter+slice+calculate_invariant_mass) exactly, with genWeight/
    L1PreFiringWeight_Nom preserved through filter+slice (is_exact_count=
    FALSE, see module docstring) and stripped only immediately before
    calculate_invariant_mass. Returns {signature: {"mass": arr,
    "genWeight": arr, "l1_prefiring": arr}} plus {label: n_events} raw
    final-state population counts (for the side report)."""
    all_combinations = get_all_combinations(
        object_types=OBJECT_TYPES,
        min_particles=MIN_PARTICLES_IN_COMBINATION,
        max_particles=MAX_PARTICLES_IN_COMBINATION,
        min_count=MIN_COUNT_PARTICLE_IN_COMBINATION,
        max_count=MAX_COUNT_PARTICLE_IN_COMBINATION,
        max_total_particles=MAX_TOTAL_PARTICLES_IN_COMBINATION,
        include_subleading=INCLUDE_SUBLEADING,
        max_subleading_index=MAX_SUBLEADING_INDEX,
    )
    assert len(all_combinations) == 186, f"expected 186 combinations, got {len(all_combinations)}"

    # Object-only view for the calculator constructor / group_by_final_state
    # (both compute ak.num() per named object type -- an extra scalar field
    # would not break THESE two, since neither iterates .fields the way
    # calculate_invariant_mass does, but we keep the constructor's own
    # input minimal and standard, matching run_coverage_on_file.py exactly).
    object_only = ak.zip(
        {k: obj_record_with_weights[k] for k in ("Electrons", "Muons", "Jets", "BJets")},
        depth_limit=1,
    )
    calculator = IMCalculator(
        events=object_only, min_events_per_fs=1,
        min_k=MIN_COUNT_PARTICLE_IN_COMBINATION, max_k=MAX_COUNT_PARTICLE_IN_COMBINATION,
        min_n=MIN_PARTICLES_IN_COMBINATION, max_n=MAX_PARTICLES_IN_COMBINATION,
    )

    out: dict = {}
    label_event_counts: dict = {}

    for label, fs_events_full in physics_calcs.group_by_final_state(obj_record_with_weights):
        label_event_counts[label] = label_event_counts.get(label, 0) + len(fs_events_full)

        for combination in all_combinations:
            if not physics_calcs.is_finalstate_contain_combination(label, combination):
                continue

            # is_exact_count=False: SAME boolean mask as the real pipeline's
            # is_exact_count=True call (physics_calcs.py:144-180 -- mask
            # computation does not depend on is_exact_count), but WITHOUT
            # the field-stripping rebuild, so genWeight/L1PreFiringWeight_Nom
            # survive (module docstring).
            filtered = calculator.filter_by_particle_counts(
                events=fs_events_full, particle_counts=combination, is_exact_count=False,
            )
            if len(filtered) == 0:
                continue

            sliced = calculator.slice_by_field(
                events=filtered, particle_counts=combination, field_to_slice_by=FIELD_TO_SLICE_BY,
            )
            if len(sliced) == 0:
                continue

            gw = ak.to_numpy(sliced["genWeight"])
            l1 = ak.to_numpy(sliced["L1PreFiringWeight_Nom"])

            # Strip to object-only fields immediately before
            # calculate_invariant_mass (which iterates .fields internally
            # and would crash on genWeight/L1PreFiringWeight_Nom -- module
            # docstring) -- mirrors physics_calcs.py's own is_exact_count=
            # True field selection, not a new algorithm.
            mass_input = ak.zip(
                {k: sliced[k] for k in combination.keys() if k in sliced.fields},
                depth_limit=1,
            )
            if len(mass_input.fields) == 0:
                continue
            inv_mass = calculator.calculate_invariant_mass(mass_input)
            if not ak.any(inv_mass):
                continue

            arr = ak.to_numpy(inv_mass).astype(np.float32)
            not_nan = ~np.isnan(arr)
            arr = arr[not_nan]
            if arr.size == 0:
                continue
            gw_kept = gw[not_nan].astype(np.float64)
            l1_kept = l1[not_nan].astype(np.float64)

            # prepare_im_combination_name's own output is
            # "<job_tag>_FS_<label>_IM_<im_str>" (im_pipeline.py:297-330);
            # extract just the IM_ suffix and feed it, with the RAW label,
            # into histograms._convert_to_bumpnet_name -- the SAME function
            # (unmodified, imported) that produced the real delivered
            # manifest's own display names, so a signature computed here
            # is directly comparable to a manifest entry, not a
            # differently-formatted equivalent.
            raw_name = prepare_im_combination_name(job_tag, label, combination)
            im_str = raw_name.split("_IM_", 1)[1]
            bumpnet_name = _convert_to_bumpnet_name(label, im_str)

            if bumpnet_name in out:
                out[bumpnet_name]["mass"] = np.concatenate([out[bumpnet_name]["mass"], arr])
                out[bumpnet_name]["genWeight"] = np.concatenate([out[bumpnet_name]["genWeight"], gw_kept])
                out[bumpnet_name]["l1_prefiring"] = np.concatenate([out[bumpnet_name]["l1_prefiring"], l1_kept])
            else:
                out[bumpnet_name] = {"mass": arr, "genWeight": gw_kept, "l1_prefiring": l1_kept}

    return out, label_event_counts


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--record-id", type=int, required=True)
    p.add_argument("--file-index", type=int, required=True)
    p.add_argument("--output-dir", required=True)
    args = p.parse_args()

    import logging
    logging.basicConfig(level=logging.WARNING)
    logger = logging.getLogger("mc_job")

    t0 = time.time()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    file_url = resolve_file_url(args.record_id, args.file_index)
    print(f"resolved record {args.record_id} file index {args.file_index} -> {file_url}", flush=True)

    events, trigger_present = read_events_mc(file_url)
    n_read = len(events)
    print(f"read {n_read} events from {file_url}", flush=True)

    # A1(i): NO golden-JSON filter for MC. Explicit assertion, not a silent
    # omission: the population entering selection below is asserted equal
    # to the raw read count.
    n_before_selection = len(events)
    assert n_before_selection == n_read, (
        "internal error: event count changed between read and selection "
        "with no golden-JSON filter applied -- investigate before trusting "
        "this job's output."
    )

    # A5: this file's own Runs-tree sums, read via fork master's existing,
    # unmodified function.
    runs_sums = read_runs_tree_sums(file_url)

    # A1: SAME function, SAME default trigger branches, as the data driver
    # (run_m0m1j0_on_file.py:284). genWeight/L1PreFiringWeight_Nom ride
    # along as ordinary fields of `events` through apply_trigger's and the
    # final_mask's plain boolean-mask operations -- no shared code touched.
    result = selection.select_event_selection_cutflow(events)
    obj_record = result["obj_record"]
    sel_events = result["sel_events"]
    n_selected = len(obj_record)
    print(f"V0-selected events (>=2mu, >=1 light jet): {n_selected}", flush=True)

    gen_weight_sel = ak.to_numpy(sel_events["genWeight"]).astype(np.float64)
    l1_prefiring_sel = ak.to_numpy(sel_events["L1PreFiringWeight_Nom"]).astype(np.float64)
    sum_gen_weight_selected = float(gen_weight_sel.sum())
    mean_l1_prefiring_selected = float(l1_prefiring_sel.mean()) if n_selected > 0 else None

    # Build the object-record-plus-weights record the general combination
    # step needs (Electrons/Muons/Jets/BJets from obj_record, genWeight/
    # L1PreFiringWeight_Nom attached as sibling scalar fields -- safe here
    # because group_by_final_state/filter_by_particle_counts(is_exact_count
    # =False)/slice_by_field never iterate `.fields` the way
    # calculate_invariant_mass does; see module docstring).
    obj_record_with_weights = ak.zip(
        {
            "Electrons": obj_record["Electrons"], "Muons": obj_record["Muons"],
            "Jets": obj_record["Jets"], "BJets": obj_record["BJets"],
            "genWeight": sel_events["genWeight"],
            "L1PreFiringWeight_Nom": sel_events["L1PreFiringWeight_Nom"],
        },
        depth_limit=1,
    )

    job_tag = f"record{args.record_id}_file{args.file_index}"
    signatures, label_event_counts = compute_all_combination_signatures(
        obj_record_with_weights, job_tag, logger,
    )

    npz_path = output_dir / "mc_combinations.npz"
    npz_payload = {}
    for sig, d in signatures.items():
        npz_payload[f"{sig}::mass"] = d["mass"]
        npz_payload[f"{sig}::genWeight"] = d["genWeight"]
        npz_payload[f"{sig}::l1_prefiring"] = d["l1_prefiring"]
    npz_payload["__signatures__"] = np.array(list(signatures.keys()), dtype=object)
    np.savez_compressed(npz_path, **npz_payload)

    elapsed = time.time() - t0

    metadata = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "git_commit": git_commit_hash(REPO_ROOT),
        "record_id": args.record_id,
        "file_index": args.file_index,
        "file_url": file_url,
        "golden_json_filter_applied": False,
        "golden_json_skip_assertion_passed": True,
        "trigger_branches_required": list(selection.TRIGGER_BRANCHES),
        "trigger_branches_present_in_file": trigger_present,
        "n_read": n_read,
        "n_after_v0_selection": n_selected,
        "cutflow": {
            "n_after_trigger": result["n_after_trigger"],
            "n_after_ge2mu": result["n_after_ge2mu"],
            "n_after_ge1jet_after_cleaning": result["n_after_ge1jet_after_cleaning"],
            "n_after_z_peak_and_mass_cutoff_m0m1j0_only": result["n_after_z_peak_and_mass_cutoff"],
        },
        "runs_tree_sums_this_file": runs_sums,
        "sum_genWeight_selected_events_this_file": sum_gen_weight_selected,
        "mean_L1PreFiringWeight_Nom_selected_events_this_file": mean_l1_prefiring_selected,
        "n_signatures_written": len(signatures),
        "signature_names": sorted(signatures.keys()),
        "raw_final_state_label_counts": label_event_counts,
        "elapsed_sec": elapsed,
    }
    (output_dir / "job_metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    print(json.dumps({"n_read": n_read, "n_selected": n_selected, "n_signatures": len(signatures),
                       "elapsed_sec": elapsed}, indent=2))
    print(f"wrote {npz_path}, job_metadata.json under {output_dir} ({elapsed:.1f}s elapsed)")


if __name__ == "__main__":
    main()
