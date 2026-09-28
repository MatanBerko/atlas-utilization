#!/usr/bin/env python
"""
Step 2 of the CMS multi-dataset BumpNet track: generalized per-file driver.

Built directly on studies/cms_coverage/per_dataset/triggered/cluster/
run_per_dataset_on_file.py (same object definitions from studies.m0m1j0_cms.selection,
same 186-combination pattern set, same chunked XRootD reading with retry) --
imported/copied conventions, not reimplemented. The one structural addition
over that script: dataset-vs-dataset de-duplication (inclusive + exclusive
shards) and a choice of population gate.

Order (per this study's own spec): chunked read -> golden JSON -> own
trigger (services.parsing.trigger_requirements.apply_trigger_requirement,
mode "any") -> object selection (studies.m0m1j0_cms.selection, unchanged)
-> population gate -> all 186 combinations (services.calculations.
combinatorics.get_all_combinations; asserted == 186) -> raw float32 masses
into two SqliteArrayShardWriter shards (inclusive, exclusive), same
signature format as run_coverage_on_file.py so the existing merge/
post-processing/delivery code can read them later, unmodified.

--population generic (default): >=2 selected objects of ANY type (same
topology-free gate as run_per_dataset_on_file.py).
--population v0: studies.m0m1j0_cms.selection.select_event_selection_cutflow
exactly as studies/cms_coverage/cluster/run_coverage_on_file.py calls it
(>=2 muons AND >=1 non-b jet). Exists ONLY for the Step 3 regression check
against that script's own DoubleMuon-only output -- select_event_selection_cutflow
re-applies its own hardcoded DoubleMuon 2-DZ-path trigger internally, which
is idempotent here (a no-op re-filter) ONLY when --dataset-label DoubleMuon,
since that is the exact same 2-path set as this driver's own "own trigger"
step for DoubleMuon. This mode is not meaningful for any other dataset and
is not used for one in this study.

Inclusive/exclusive de-duplication (task's own veto priority order, highest
first: DoubleMuon > DoubleEG > MuonEG > SingleMuon > SingleElectron > JetHT
> MET, services.datasets_records.VETO_ORDER): an event is "exclusive" to a
dataset if it passes that dataset's own trigger AND fails every
higher-priority dataset's own trigger set. Masses are computed ONCE per
(final state, combination) on the full (inclusive) population; the
exclusive shard's arrays are a SUB-ARRAY of the already-computed inclusive
array, selected via a cheaply-recomputed (count-only, no vector math)
boolean mask -- see _group_by_final_state_with_mask and
_recompute_exact_count_mask below -- never a second pass through
IMCalculator/_calculate_combination_invariant_mass. This is the "compute
once, split by mask" this study's own spec requires.

Usage:
    python run_dataset_on_file.py --dataset-label SingleMuon --record-id 30530 \
        --file-index 0 --output-dir /storage/.../job_SingleMuon_G_0 \
        --population generic
"""
from __future__ import annotations

import argparse
import json
import logging
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
from services.calculations.combinatorics import get_all_combinations, get_count, get_start  # noqa: E402
from services.calculations.im_calculator import IMCalculator  # noqa: E402
from services.parsing.validated_runs import ValidatedRunsFilter, apply_validated_runs_filter  # noqa: E402
from services.parsing.trigger_requirements import apply_trigger_requirement  # noqa: E402
from services.pipelines.im_pipeline import (  # noqa: E402
    _calculate_combination_invariant_mass,
    prepare_im_combination_name,
)
from services.storage.sqlite_shards import SqliteArrayShardWriter  # noqa: E402
from studies.m0m1j0_cms import selection  # noqa: E402
from studies.m0m1j0_cms.design_checks.common import fetch_file_list  # noqa: E402
from studies.cms_datasets.cluster.datasets_records import DATASETS, VETO_ORDER  # noqa: E402

DEFAULT_VALIDATED_RUNS_JSON = (
    "data/cms/validated_runs/Cert_271036-284044_13TeV_Legacy2016_Collisions16_JSON.txt"
)

TRIGGER_PATHS_BY_DATASET = {d.label: d.trigger_paths for d in DATASETS}

BASE_OBJECT_BRANCHES = (
    "run", "luminosityBlock", "event",
    "nMuon", "Muon_pt", "Muon_eta", "Muon_phi", "Muon_mass",
    "Muon_mediumId", "Muon_pfRelIso04_all", "Muon_charge",
    "nElectron", "Electron_pt", "Electron_eta", "Electron_phi", "Electron_mass",
    "Electron_cutBased",
    "nJet", "Jet_pt", "Jet_eta", "Jet_phi", "Jet_mass", "Jet_jetId",
    "Jet_btagDeepFlavB",
)

OBJECT_TYPES = ["Electrons", "Muons", "Jets", "BJets"]
MIN_PARTICLES_IN_COMBINATION = 1
MAX_PARTICLES_IN_COMBINATION = 4
MIN_COUNT_PARTICLE_IN_COMBINATION = 1
MAX_COUNT_PARTICLE_IN_COMBINATION = 4
MAX_TOTAL_PARTICLES_IN_COMBINATION = 4
INCLUDE_SUBLEADING = True
MAX_SUBLEADING_INDEX = 1
FIELD_TO_SLICE_BY = "pt"

MIN_TOTAL_SELECTED_OBJECTS = 2  # generic population gate

READ_RETRY_ATTEMPTS = 4
READ_RETRY_BACKOFF_SEC = 15
READ_CHUNK_SIZE = 300_000

COVERAGE_CAP_PER_SIGNATURE = 500_000

# Step 2 diagnostics (task spec): 1 GeV bins, 0-200 GeV.
DIAGNOSTIC_PT_BIN_EDGES = np.arange(0.0, 201.0, 1.0)
DIAGNOSTIC_MASS_BIN_EDGES = np.arange(0.0, 201.0, 1.0)
# 20 MeV bins, 0-10 GeV: 1 GeV bins cannot resolve the J/psi (natural width
# ~93 keV, CMS dimuon mass resolution ~O(10-40 MeV) near 3.1 GeV) at all --
# it would be completely washed out into the surrounding continuum. This
# finer histogram exists solely so a genuine J/psi peak is visible in the
# quality-gate report; it does not affect selection, gating, or shards.
DIAGNOSTIC_LOWMASS_FINE_BIN_EDGES = np.arange(0.0, 10.0001, 0.02)
LOW_MASS_DIMUON_CUTOFF_GEV = 5.0


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
        except Exception as e:  # noqa: BLE001 -- transient XRootD read failure
            last_exc = e
            print(f"read attempt {attempt}/{READ_RETRY_ATTEMPTS} failed for {file_url} "
                  f"[{entry_start}:{entry_stop}]: {type(e).__name__}: {e}", flush=True)
            if attempt < READ_RETRY_ATTEMPTS:
                time.sleep(READ_RETRY_BACKOFF_SEC)
    raise RuntimeError(
        f"{file_url} [{entry_start}:{entry_stop}]: failed to read after {READ_RETRY_ATTEMPTS} attempts"
    ) from last_exc


def read_events(file_url: str, required_branches):
    tree = uproot.open(file_url)["Events"]
    available = set(tree.keys())
    missing = [b for b in required_branches if b not in available]
    if missing:
        raise ValueError(
            f"{file_url}: missing required branch(es) {missing}. This includes "
            f"this dataset's own trigger paths and/or a higher-veto-priority "
            f"dataset's trigger paths, which this driver refuses to silently "
            f"treat as 'did not fire'."
        )
    branches = list(required_branches)
    n_entries = tree.num_entries
    chunks = []
    for start in range(0, n_entries, READ_CHUNK_SIZE):
        stop = min(start + READ_CHUNK_SIZE, n_entries)
        chunks.append(_read_chunk_with_retry(tree, branches, start, stop, file_url))
    return ak.concatenate(chunks) if len(chunks) > 1 else chunks[0]


def _group_by_final_state_with_mask(obj_record: ak.Array):
    """Identical grouping/capping formula to
    services.calculations.physics_calcs.group_by_final_state (copied
    verbatim, not reimplemented differently) -- the ONLY difference is that
    this also yields each group's own boolean mask into obj_record, which
    the shared function computes internally but does not expose. Needed
    here only so the (already-computed) per-combination mass array can
    later be split into inclusive/exclusive sub-arrays by a cheap,
    alignment-preserving boolean mask, without a second combinatorics pass.
    Byte-identical (label, fs_events) pairs to the shared function for the
    same input, since it is the same deterministic string-building code
    applied to the same array."""
    num_events = len(obj_record)
    zero_array = ak.Array([0] * num_events) if num_events > 0 else ak.Array([])
    particle_counts = ak.num(obj_record)

    e = getattr(particle_counts, "Electrons", zero_array)
    m = getattr(particle_counts, "Muons", zero_array)
    j = getattr(particle_counts, "Jets", zero_array)
    g = getattr(particle_counts, "Photons", zero_array)
    t = getattr(particle_counts, "Taus", zero_array)
    b = getattr(particle_counts, "BJets", zero_array)

    all_events_fs = np.array([
        f"{ee}e_{mm}m_{jj}j_{gg}g_{tt}t_{bb}b"
        for ee, mm, jj, gg, tt, bb in zip(e, m, j, g, t, b)
    ])
    for raw_fs in sorted(set(all_events_fs.tolist())):
        mask = (all_events_fs == raw_fs)
        events_matching_fs = obj_record[mask]
        label = physics_calcs.limit_particles_in_fs(raw_fs, 4)
        yield label, events_matching_fs, mask


def _recompute_exact_count_row_mask(fs_events: ak.Array, combination: dict) -> np.ndarray:
    """Cheap (count-only, no vector math) recomputation of the boolean
    row-mask that services.calculations.physics_calcs.filter_events_by_particle_counts's
    is_exact_count=True branch applies internally, using the exact same
    'obj_count >= start + count' formula (that branch's row-reduction
    criterion despite its name -- read directly from
    physics_calcs.py:170-178 -- the is_exact_count flag only controls
    whether NON-combination fields are dropped afterwards, not the row
    filter itself). Recomputing this tiny boolean/count-only step a second
    time is NOT the "combinatorics cost" this study's spec says not to
    double -- that refers to the vector-math-heavy
    calculate_invariant_mass/_calculate_combination_invariant_mass call,
    which runs exactly once. This function exists solely to align the
    is_exclusive flag with the row-order _calculate_combination_invariant_mass
    already produced."""
    combined_mask = np.ones(len(fs_events), dtype=bool)
    for obj, value in combination.items():
        if obj not in fs_events.fields:
            if get_start(value) + get_count(value) > 0:
                combined_mask &= False
            continue
        obj_count = ak.to_numpy(ak.num(fs_events[obj]))
        combined_mask &= (obj_count >= get_start(value) + get_count(value))
    return combined_mask


def _histogram_1gev(values: np.ndarray, edges: np.ndarray) -> dict:
    finite = values[~np.isnan(values)]
    counts, _ = np.histogram(finite, bins=edges)
    return {"bin_edges_gev": edges.tolist(), "counts": counts.tolist(),
            "n_entries": int(finite.size), "n_nan_or_missing": int(values.size - finite.size)}


def compute_diagnostics(muons: ak.Array, electrons: ak.Array) -> dict:
    """Step 2 diagnostics (task spec), computed over the INCLUSIVE
    population (all events passing this dataset's own trigger + object
    selection, before the population gate -- 'inclusive population' as
    named in the task brief): leading muon/electron pT (1 GeV bins,
    0-200 GeV); opposite-sign dimuon mass and dR for pairs with m<5 GeV;
    raw (pre-post-processing) dilepton masses m(mu0,mu1), m(e0,e1),
    m(e0,mu0) (1 GeV bins, 0-200 GeV). Diagnostic only -- does not affect
    selection, gating, or the written shards."""
    mu_order = ak.argsort(muons.pt, axis=1, ascending=False)
    sorted_mu = muons[mu_order]
    padded_mu = ak.pad_none(sorted_mu, 2, axis=1, clip=True)
    mu0, mu1 = padded_mu[:, 0], padded_mu[:, 1]

    e_order = ak.argsort(electrons.pt, axis=1, ascending=False)
    sorted_e = electrons[e_order]
    padded_e = ak.pad_none(sorted_e, 2, axis=1, clip=True)
    e0, e1 = padded_e[:, 0], padded_e[:, 1]

    leading_mu_pt = ak.to_numpy(ak.fill_none(padded_mu[:, 0].pt, np.nan))
    subleading_mu_pt = ak.to_numpy(ak.fill_none(padded_mu[:, 1].pt, np.nan))
    leading_e_pt = ak.to_numpy(ak.fill_none(padded_e[:, 0].pt, np.nan))

    def _p4(obj):
        import vector
        vector.register_awkward()
        return vector.zip({"pt": obj.pt, "eta": obj.eta, "phi": obj.phi, "mass": obj.mass})

    m_mumu = ak.to_numpy(ak.fill_none((_p4(mu0) + _p4(mu1)).mass, np.nan))
    m_ee = ak.to_numpy(ak.fill_none((_p4(e0) + _p4(e1)).mass, np.nan))
    m_emu = ak.to_numpy(ak.fill_none((_p4(e0) + _p4(mu0)).mass, np.nan))

    has_2mu = ak.to_numpy(ak.num(muons) >= 2)
    charge0 = ak.to_numpy(ak.fill_none(mu0.charge, 0)) if "charge" in muons.fields else None
    charge1 = ak.to_numpy(ak.fill_none(mu1.charge, 0)) if "charge" in muons.fields else None
    dr_mumu = ak.to_numpy(ak.fill_none(_p4(mu0).deltaR(_p4(mu1)), np.nan))

    low_mass_mask = has_2mu & (m_mumu < LOW_MASS_DIMUON_CUTOFF_GEV) & ~np.isnan(m_mumu)
    if charge0 is not None and charge1 is not None:
        opp_sign_mask = low_mass_mask & ((charge0 * charge1) < 0)
    else:
        opp_sign_mask = np.zeros_like(low_mass_mask)

    return {
        "leading_muon_pt": _histogram_1gev(leading_mu_pt, DIAGNOSTIC_PT_BIN_EDGES),
        "subleading_muon_pt": _histogram_1gev(subleading_mu_pt, DIAGNOSTIC_PT_BIN_EDGES),
        "leading_electron_pt": _histogram_1gev(leading_e_pt, DIAGNOSTIC_PT_BIN_EDGES),
        "raw_dimuon_mass_mu0mu1": _histogram_1gev(m_mumu, DIAGNOSTIC_MASS_BIN_EDGES),
        "raw_dimuon_mass_mu0mu1_lowmass_finebins": _histogram_1gev(m_mumu, DIAGNOSTIC_LOWMASS_FINE_BIN_EDGES),
        "raw_dielectron_mass_e0e1": _histogram_1gev(m_ee, DIAGNOSTIC_MASS_BIN_EDGES),
        "raw_emu_mass_e0mu0": _histogram_1gev(m_emu, DIAGNOSTIC_MASS_BIN_EDGES),
        "low_mass_opposite_sign_dimuon": {
            "n_pairs": int(opp_sign_mask.sum()),
            "mass_gev": m_mumu[opp_sign_mask].tolist(),
            "dr": dr_mumu[opp_sign_mask].tolist(),
        },
        "muon_charge_field_present": charge0 is not None,
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--dataset-label", required=True, choices=list(TRIGGER_PATHS_BY_DATASET.keys()))
    p.add_argument("--record-id", type=int, required=True)
    p.add_argument("--file-index", type=int, required=True)
    p.add_argument("--output-dir", required=True)
    p.add_argument("--population", choices=["generic", "v0"], default="generic")
    p.add_argument("--validated-runs-json", default=DEFAULT_VALIDATED_RUNS_JSON)
    args = p.parse_args()

    logging.basicConfig(level=logging.WARNING, format="%(asctime)s %(levelname)s %(message)s")
    logger = logging.getLogger("run_dataset_on_file")

    dataset_label = args.dataset_label
    own_paths = TRIGGER_PATHS_BY_DATASET[dataset_label]
    higher_priority = VETO_ORDER[:VETO_ORDER.index(dataset_label)]
    veto_paths_by_label = {h: TRIGGER_PATHS_BY_DATASET[h] for h in higher_priority}

    all_trigger_branches = list(own_paths)
    for paths in veto_paths_by_label.values():
        all_trigger_branches.extend(paths)
    required_branches = list(BASE_OBJECT_BRANCHES) + sorted(set(all_trigger_branches))

    t0 = time.time()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    file_url = resolve_file_url(args.record_id, args.file_index)
    print(f"[{dataset_label}] resolved record {args.record_id} file index {args.file_index} -> {file_url}", flush=True)

    events = read_events(file_url, required_branches)
    n_read = len(events)
    print(f"[{dataset_label}] read {n_read} events", flush=True)

    validated_runs = ValidatedRunsFilter(args.validated_runs_json)
    events_golden, golden_stats = apply_validated_runs_filter(events, validated_runs)
    n_after_golden_json = golden_stats["n_after"]
    print(f"[{dataset_label}] golden-JSON filter: {golden_stats['n_before']} -> {n_after_golden_json}", flush=True)

    events_triggered, trigger_stats = apply_trigger_requirement(
        events_golden, {"mode": "any", "paths": own_paths}
    )
    n_after_trigger = trigger_stats["n_after"]
    print(f"[{dataset_label}] own-trigger requirement ({own_paths}): "
          f"{trigger_stats['n_before']} -> {n_after_trigger}, per_path={trigger_stats['per_path']}", flush=True)

    # Veto masks (Step 2 de-duplication), computed on events_triggered --
    # i.e. AFTER this dataset's own trigger, matching the task's own
    # "exclusive" definition (passes own trigger AND fails every
    # higher-veto-priority dataset's trigger set).
    n_events_triggered = len(events_triggered)
    veto_masks = {}
    for label, paths in veto_paths_by_label.items():
        m = np.zeros(n_events_triggered, dtype=bool)
        for path in paths:
            m |= ak.to_numpy(events_triggered[path]).astype(bool)
        veto_masks[label] = m
    n_vetoed_by_each_higher_dataset = {label: int(m.sum()) for label, m in veto_masks.items()}

    vetoed_by_any = np.zeros(n_events_triggered, dtype=bool)
    for m in veto_masks.values():
        vetoed_by_any |= m
    is_exclusive_pretrigger = ~vetoed_by_any  # aligned to events_triggered

    # Object selection (unchanged, imported). `charge` is passed as a pure
    # passthrough extra field (selection.select_muons's own documented
    # mechanism) -- needed only for the opposite-sign low-mass dimuon
    # diagnostic below; it does not affect the selection mask itself.
    muons = selection.select_muons(events_triggered, extra_fields={"charge": events_triggered.Muon_charge})
    electrons = selection.select_electrons(events_triggered)
    jets = selection.select_and_split_jets(events_triggered, muons, electrons, apply_lepton_cleaning=True)

    diagnostics = compute_diagnostics(muons, electrons)

    v0_result = None
    if args.population == "generic":
        total_objects = ak.num(muons) + ak.num(electrons) + ak.num(jets["Jets"]) + ak.num(jets["BJets"])
        keep = ak.to_numpy(total_objects >= MIN_TOTAL_SELECTED_OBJECTS)
        obj_record = selection.build_object_record(
            muons[keep], electrons[keep], {"Jets": jets["Jets"][keep], "BJets": jets["BJets"][keep]}
        )
    else:  # v0 -- regression-check mode only, see module docstring.
        keep = ak.to_numpy((ak.num(muons) >= 2) & (ak.num(jets["Jets"]) >= 1))
        v0_result = selection.select_event_selection_cutflow(events_triggered)
        obj_record = v0_result["obj_record"]
        # This driver's own externally-computed `keep` mask (used below to
        # align is_exclusive_pretrigger with obj_record's row order) must
        # select exactly the same events as select_event_selection_cutflow's
        # own internal final_mask -- true by construction (same muons/jets
        # selection functions, same >=2mu & >=1 light-jet condition), but
        # asserted here rather than only assumed, since obj_record's actual
        # row order/count comes from the internal call, not from `keep`.
        assert len(obj_record) == int(keep.sum()), (
            f"v0 population alignment check failed: len(obj_record)={len(obj_record)} "
            f"!= keep.sum()={int(keep.sum())} -- externally recomputed gate mask does not "
            f"match select_event_selection_cutflow's own internal population"
        )

    n_after_gate = len(obj_record)
    is_exclusive_selected = is_exclusive_pretrigger[keep]
    n_exclusive = int(is_exclusive_selected.sum())
    print(f"[{dataset_label}] population={args.population}: n_after_gate={n_after_gate}, "
          f"n_exclusive={n_exclusive}, n_vetoed_by_each_higher_dataset={n_vetoed_by_each_higher_dataset}",
          flush=True)

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

    calculator = IMCalculator(
        events=obj_record, min_events_per_fs=1,
        min_k=MIN_COUNT_PARTICLE_IN_COMBINATION, max_k=MAX_COUNT_PARTICLE_IN_COMBINATION,
        min_n=MIN_PARTICLES_IN_COMBINATION, max_n=MAX_PARTICLES_IN_COMBINATION,
    )
    im_config = {"field_to_slice_by": FIELD_TO_SLICE_BY}

    job_tag = f"{dataset_label}_record{args.record_id}_file{args.file_index}"
    incl_shard_path = output_dir / "dataset_shard_inclusive.sqlite"
    excl_shard_path = output_dir / "dataset_shard_exclusive.sqlite"
    for path in (incl_shard_path, excl_shard_path):
        if path.exists():
            path.unlink()
    writer_incl = SqliteArrayShardWriter(str(incl_shard_path))
    writer_excl = SqliteArrayShardWriter(str(excl_shard_path))

    n_fs_groups = 0
    n_signature_writes_incl = 0
    n_signature_writes_excl = 0
    n_values_written_incl = 0
    n_values_written_excl = 0
    max_signature_size = 0
    n_capped_signatures = 0
    label_event_counts_incl: dict[str, int] = {}
    label_event_counts_excl: dict[str, int] = {}
    skip_reason_totals: dict[str, int] = {}

    for label, fs_events, group_mask in _group_by_final_state_with_mask(obj_record):
        n_fs_groups += 1
        n_this_group = len(fs_events)
        label_event_counts_incl[label] = label_event_counts_incl.get(label, 0) + n_this_group
        writer_incl.record_final_state_count(label, n_this_group)

        fs_is_exclusive = is_exclusive_selected[group_mask]
        n_excl_this_group = int(fs_is_exclusive.sum())
        label_event_counts_excl[label] = label_event_counts_excl.get(label, 0) + n_excl_this_group
        writer_excl.record_final_state_count(label, n_excl_this_group)

        for combination in all_combinations:
            if not physics_calcs.is_finalstate_contain_combination(label, combination):
                continue

            inv_mass, skip_reason = _calculate_combination_invariant_mass(
                fs_events, combination, im_config, calculator, logger, label,
            )
            if inv_mass is None:
                if skip_reason:
                    skip_reason_totals[skip_reason] = skip_reason_totals.get(skip_reason, 0) + 1
                continue

            combo_row_mask = _recompute_exact_count_row_mask(fs_events, combination)
            combo_is_exclusive = fs_is_exclusive[combo_row_mask]
            assert combo_is_exclusive.size == len(inv_mass), (
                f"alignment check failed for {label}/{combination}: "
                f"{combo_is_exclusive.size} != {len(inv_mass)}"
            )

            arr = ak.to_numpy(inv_mass).astype(np.float32)
            nan_mask = ~np.isnan(arr)
            arr = arr[nan_mask]
            combo_is_exclusive = combo_is_exclusive[nan_mask]
            if arr.size == 0:
                continue

            signature = prepare_im_combination_name(job_tag, label, combination)
            if arr.size > max_signature_size:
                max_signature_size = int(arr.size)
            if arr.size > COVERAGE_CAP_PER_SIGNATURE:
                true_size = int(arr.size)
                n_capped_signatures += 1
                rng = np.random.default_rng(seed=0)
                pick = rng.choice(arr.size, size=COVERAGE_CAP_PER_SIGNATURE, replace=False)
                arr = arr[pick]
                combo_is_exclusive = combo_is_exclusive[pick]
                writer_incl.set_metadata(f"CAPPED::{signature}", f"true_size={true_size}")

            writer_incl.append_array(signature, arr)
            n_signature_writes_incl += 1
            n_values_written_incl += int(arr.size)

            excl_arr = arr[combo_is_exclusive]
            if excl_arr.size > 0:
                writer_excl.append_array(signature, excl_arr)
                n_signature_writes_excl += 1
                n_values_written_excl += int(excl_arr.size)

    common_metadata = {
        "n_read": n_read,
        "n_after_golden_json": n_after_golden_json,
        "n_after_trigger": n_after_trigger,
        "n_after_gate": n_after_gate,
        "n_exclusive": n_exclusive,
        "dataset_label": dataset_label,
        "record_id": args.record_id,
        "file_index": args.file_index,
        "file_url": file_url,
        "population": args.population,
        "own_trigger_paths": ",".join(own_paths),
        "higher_priority_datasets": ",".join(higher_priority),
    }
    for writer in (writer_incl, writer_excl):
        for k, v in common_metadata.items():
            writer.set_metadata(k, v)
        writer.commit()
        writer.close()

    elapsed = time.time() - t0
    incl_shard_size_mb = incl_shard_path.stat().st_size / (1024 * 1024)
    excl_shard_size_mb = excl_shard_path.stat().st_size / (1024 * 1024)

    metadata = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "git_commit": git_commit_hash(REPO_ROOT),
        "dataset_label": dataset_label,
        "record_id": args.record_id,
        "file_index": args.file_index,
        "file_url": file_url,
        "population": args.population,
        "own_trigger_paths": list(own_paths),
        "higher_priority_datasets": higher_priority,
        "n_read": n_read,
        "n_after_golden_json": n_after_golden_json,
        "n_after_trigger": n_after_trigger,
        "trigger_per_path": trigger_stats["per_path"],
        "n_after_gate": n_after_gate,
        "n_exclusive": n_exclusive,
        "n_vetoed_by_each_higher_dataset": n_vetoed_by_each_higher_dataset,
        "n_final_state_groups": n_fs_groups,
        "final_state_label_event_counts_inclusive": label_event_counts_incl,
        "final_state_label_event_counts_exclusive": label_event_counts_excl,
        "n_combinations_checked_per_group": len(all_combinations),
        "n_signature_writes_inclusive": n_signature_writes_incl,
        "n_signature_writes_exclusive": n_signature_writes_excl,
        "n_values_written_inclusive": n_values_written_incl,
        "n_values_written_exclusive": n_values_written_excl,
        "max_signature_size_this_job": max_signature_size,
        "n_capped_signatures": n_capped_signatures,
        "skip_reason_totals": skip_reason_totals,
        "inclusive_shard_size_mb": round(incl_shard_size_mb, 3),
        "exclusive_shard_size_mb": round(excl_shard_size_mb, 3),
        "elapsed_sec": elapsed,
        "diagnostics": diagnostics,
    }
    (output_dir / "job_metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    print(json.dumps({
        "dataset_label": dataset_label, "population": args.population, "n_read": n_read,
        "n_after_gate": n_after_gate, "n_exclusive": n_exclusive,
        "n_signature_writes_inclusive": n_signature_writes_incl,
        "n_signature_writes_exclusive": n_signature_writes_excl,
        "elapsed_sec": round(elapsed, 1),
    }, indent=2))
    print(f"[{dataset_label}] wrote {incl_shard_path}, {excl_shard_path}, and job_metadata.json "
          f"under {output_dir} ({elapsed:.1f}s elapsed)")


if __name__ == "__main__":
    main()
