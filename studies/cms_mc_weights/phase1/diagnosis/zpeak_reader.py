#!/usr/bin/env python
"""
Diagnosis round 2 -- E2: a diagnostic-only Z-peak reader that does NOT
impose the shared analysis's own >=1-light-jet requirement (unlike
select_event_selection_cutflow, which enforces it as part of the base
population -- see DIAGNOSIS.md D0). Produces no BumpNet histograms; never
part of any delivery.

Reuses the shared object definitions by IMPORTING the lower-level
functions the data driver's own select_event_selection_cutflow calls
internally (studies/m0m1j0_cms/selection.py) -- never copied:
  - selection.apply_trigger              (same HLT paths as data)
  - selection.select_muons                (pt/eta/mediumId/iso, same cuts)
  - selection.select_electrons            (used only for jet cleaning)
  - selection.select_and_split_jets       (pt>30/eta/tightID/DeltaR-clean,
                                            b-tag split at the same
                                            DeepJet Medium WP)
  - selection.compute_dimuon_mass         (leading+subleading muon mass --
                                            NO opposite-sign requirement;
                                            confirmed by reading the
                                            function: it pads/sorts by pT
                                            only, never touches charge)
  - selection.compute_dimuon_diagnostics  (gives charge_product, from
                                            which opposite-sign is derived
                                            here -- diagnostic only in the
                                            shared code too, never a cut)
  - selection.leading_jet_pt

The only genuinely new logic here is: (i) NOT requiring >=1 jet before
computing these (select_event_selection_cutflow's own has_ge1jet mask is
never applied), (ii) a >=50 GeV jet count computed by filtering the
ALREADY pt>30/eta/ID/cleaned `Jets` collection down further by pt>50 --
same object definition, stricter pt threshold on its own output, not a
re-derivation of the kinematic/ID/cleaning cuts themselves, and (iii)
reading PV_npvsGood (both) and genWeight/L1PreFiringWeight_Nom/
Pileup_nTrueInt (MC only), none of which selection.py reads by default.

Usage:
    python zpeak_reader.py --record-id 30522 --file-index 0 \
        --output-dir .../diagnosis_zpeak/30522/job_0
    python zpeak_reader.py --record-id 35671 --file-index 0 --is-mc \
        --output-dir .../diagnosis_zpeak/35671/job_0

Writes, under --output-dir:
    zpeak_data.npz     -- per-event arrays, mass window [50,150] GeV only:
                          mass, is_os, n_jets_pt30, n_jets_pt50, n_bjets,
                          leading_jet_pt, pv_npvsgood, and for MC also
                          gen_weight, l1_prefiring, pileup_ntrueint.
    job_metadata.json  -- file_url, is_mc, cutflow counts, golden-JSON
                          stats (data only), Runs-tree sums (MC only),
                          elapsed_sec.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT))

import awkward as ak  # noqa: E402
import numpy as np  # noqa: E402
import uproot  # noqa: E402

from services.parsing.validated_runs import ValidatedRunsFilter, apply_validated_runs_filter  # noqa: E402
from services.parsing.mc_weights import read_runs_tree_sums  # noqa: E402
from studies.m0m1j0_cms import selection  # noqa: E402
from studies.m0m1j0_cms.design_checks.common import fetch_file_list  # noqa: E402

DEFAULT_VALIDATED_RUNS_JSON = (
    "data/cms/validated_runs/Cert_271036-284044_13TeV_Legacy2016_Collisions16_JSON.txt"
)

EXTRA_BRANCHES_ALWAYS = ("PV_npvsGood",)
EXTRA_BRANCHES_MC = ("genWeight", "L1PreFiringWeight_Nom", "Pileup_nTrueInt")

READ_CHUNK_SIZE = 300_000
READ_RETRY_ATTEMPTS = 4
READ_RETRY_BACKOFF_SEC = 15

MASS_WINDOW_LOW = 50.0
MASS_WINDOW_HIGH = 150.0
JET_PT_HIGH_THRESHOLD_GEV = 50.0


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


def read_events(file_url: str, is_mc: bool):
    tree = uproot.open(file_url)["Events"]
    available = set(tree.keys())
    required = list(selection.NEEDED_BRANCHES) + list(EXTRA_BRANCHES_ALWAYS)
    if is_mc:
        required += list(EXTRA_BRANCHES_MC)
    missing = [b for b in required if b not in available]
    if missing:
        raise ValueError(
            f"{file_url}: missing required branch(es): {missing}. Refusing "
            f"to proceed rather than silently treating a missing branch as "
            f"absent/zero."
        )
    n_entries = tree.num_entries
    chunks = []
    for start in range(0, n_entries, READ_CHUNK_SIZE):
        stop = min(start + READ_CHUNK_SIZE, n_entries)
        chunks.append(_read_chunk_with_retry(tree, required, start, stop, file_url))
    events = ak.concatenate(chunks) if len(chunks) > 1 else chunks[0]
    return events, n_entries


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--record-id", type=int, required=True)
    p.add_argument("--file-index", type=int, required=True)
    p.add_argument("--output-dir", required=True)
    p.add_argument("--is-mc", action="store_true")
    p.add_argument("--validated-runs-json", default=DEFAULT_VALIDATED_RUNS_JSON)
    args = p.parse_args()

    t0 = time.time()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    file_url = resolve_file_url(args.record_id, args.file_index)
    print(f"resolved record {args.record_id} file index {args.file_index} -> {file_url}", flush=True)

    events, n_read = read_events(file_url, args.is_mc)
    print(f"read {n_read} events from {file_url}", flush=True)

    golden_stats = None
    if args.is_mc:
        events_after_golden = events
    else:
        validated_runs = ValidatedRunsFilter(args.validated_runs_json)
        events_after_golden, golden_stats = apply_validated_runs_filter(events, validated_runs)
        print(f"golden-JSON filter: {golden_stats['n_before']} -> {golden_stats['n_after']}", flush=True)

    triggered = selection.apply_trigger(events_after_golden, trigger_branches=selection.TRIGGER_BRANCHES)
    n_after_trigger = len(triggered)
    print(f"after trigger: {n_after_trigger}", flush=True)

    muons = selection.select_muons(triggered, extra_fields={"charge": triggered["Muon_charge"]})
    electrons = selection.select_electrons(triggered)
    jets = selection.select_and_split_jets(triggered, muons, electrons, apply_lepton_cleaning=True)

    has_ge2mu = ak.num(muons) >= 2
    n_after_ge2mu = int(ak.sum(has_ge2mu))
    print(f"after >=2 selected muons: {n_after_ge2mu}", flush=True)

    sel_muons = muons[has_ge2mu]
    sel_light_jets = jets["Jets"][has_ge2mu]
    sel_bjets = jets["BJets"][has_ge2mu]
    sel_events = triggered[has_ge2mu]

    dimuon_mass = selection.compute_dimuon_mass(sel_muons)
    diag = selection.compute_dimuon_diagnostics(sel_muons)
    charge_product = diag["charge_product"]  # +1 same-sign, -1 opposite-sign (diagnostic only in shared code)

    n_jets_pt30 = ak.num(sel_light_jets)
    n_jets_pt50 = ak.num(sel_light_jets[sel_light_jets.pt > JET_PT_HIGH_THRESHOLD_GEV])
    n_bjets = ak.num(sel_bjets)
    leading_jet_pt = selection.leading_jet_pt(sel_light_jets)

    pv_npvsgood = ak.to_numpy(sel_events["PV_npvsGood"])
    mass_np = ak.to_numpy(dimuon_mass)
    charge_product_np = ak.to_numpy(charge_product)
    n_jets_pt30_np = ak.to_numpy(n_jets_pt30)
    n_jets_pt50_np = ak.to_numpy(n_jets_pt50)
    n_bjets_np = ak.to_numpy(n_bjets)
    leading_jet_pt_np = ak.to_numpy(leading_jet_pt)

    in_window = ~np.isnan(mass_np) & (mass_np >= MASS_WINDOW_LOW) & (mass_np <= MASS_WINDOW_HIGH)
    n_in_window = int(in_window.sum())
    print(f"in [{MASS_WINDOW_LOW},{MASS_WINDOW_HIGH}] GeV mass window: {n_in_window}", flush=True)

    npz_payload = {
        "mass": mass_np[in_window].astype(np.float32),
        "is_os": (charge_product_np[in_window] < 0).astype(np.int8),
        "n_jets_pt30": n_jets_pt30_np[in_window].astype(np.int16),
        "n_jets_pt50": n_jets_pt50_np[in_window].astype(np.int16),
        "n_bjets": n_bjets_np[in_window].astype(np.int16),
        "leading_jet_pt": leading_jet_pt_np[in_window].astype(np.float32),
        "pv_npvsgood": pv_npvsgood[in_window].astype(np.int16),
    }

    runs_sums = None
    if args.is_mc:
        gen_weight = ak.to_numpy(sel_events["genWeight"])
        l1_prefiring = ak.to_numpy(sel_events["L1PreFiringWeight_Nom"])
        pileup_ntrueint = ak.to_numpy(sel_events["Pileup_nTrueInt"])
        npz_payload["gen_weight"] = gen_weight[in_window].astype(np.float64)
        npz_payload["l1_prefiring"] = l1_prefiring[in_window].astype(np.float64)
        npz_payload["pileup_ntrueint"] = pileup_ntrueint[in_window].astype(np.float32)
        runs_sums = read_runs_tree_sums(file_url)

    npz_path = output_dir / "zpeak_data.npz"
    np.savez_compressed(npz_path, **npz_payload)

    elapsed = time.time() - t0
    metadata = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "git_commit": git_commit_hash(REPO_ROOT),
        "record_id": args.record_id,
        "file_index": args.file_index,
        "file_url": file_url,
        "is_mc": args.is_mc,
        "n_read": n_read,
        "golden_json_stats": golden_stats,
        "n_after_trigger": n_after_trigger,
        "n_after_ge2mu": n_after_ge2mu,
        "n_in_mass_window_50_150": n_in_window,
        "runs_tree_sums_this_file": runs_sums,
        "mass_window_gev": [MASS_WINDOW_LOW, MASS_WINDOW_HIGH],
        "jet_pt_high_threshold_gev": JET_PT_HIGH_THRESHOLD_GEV,
        "opposite_sign_requirement_in_shared_selection": (
            "NONE -- selection.compute_dimuon_mass/compute_m0m1j0 pad/sort "
            "the two selected muons by pT only and never inspect charge; "
            "compute_dimuon_diagnostics's charge_product is diagnostic-only "
            "in the shared code too, never used as a cut anywhere in "
            "select_event_selection_cutflow."
        ),
        "elapsed_sec": elapsed,
    }
    (output_dir / "job_metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    print(json.dumps({
        "n_read": n_read, "n_after_trigger": n_after_trigger,
        "n_after_ge2mu": n_after_ge2mu, "n_in_window": n_in_window,
        "elapsed_sec": round(elapsed, 1),
    }, indent=2))
    print(f"wrote {npz_path} and job_metadata.json under {output_dir} ({elapsed:.1f}s elapsed)")


if __name__ == "__main__":
    main()
