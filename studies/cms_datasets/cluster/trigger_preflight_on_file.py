#!/usr/bin/env python
"""
Step 1 of the CMS multi-dataset BumpNet track: trigger-only pre-flight
scan. One job processes a contiguous range of files belonging to ONE
dataset+era record.

Reads ONLY run, luminosityBlock, and every HLT branch Step 1 needs (every
one of the 7 datasets' own trigger paths, the MuonEG non-DZ reference
paths, the nested-reference pairs, and the MET higher-threshold
candidates -- see datasets_records.all_step1_hlt_branches()), chunked
(300,000 events, matching studies/cms_coverage/cluster/run_coverage_on_file.py's
own convention, retried on the same transient XRootD "Operation expired"
failure that script's docstring documents) -- never a whole-file read.

Applies the golden JSON (services.parsing.validated_runs, imported
unmodified -- same as every other driver in this repo) and reports
before/after counts. Missing HLT branches are recorded explicitly per
file, never silently treated as "did not fire" -- this is a diagnostic
scan, so a missing branch is skipped from that file's per-path counts
(there is nothing to sum) but flagged prominently in the output rather
than causing a crash, which would prevent the pre-flight report itself
from being produced.

For every run present among golden-JSON-passing events, records:
  - n_golden events in that run
  - per-HLT-path fire count in that run, for every path present in this
    file
  - per-nested-reference-pair joint counts (N(looser AND stricter),
    N(stricter alone)), for pairs where BOTH paths are present
  - for the file's OWN dataset (from --dataset-label): the own-trigger
    fire count, the joint count against every OTHER dataset's own
    trigger set (for the overlap matrix), and the exclusive count
    (passes own trigger, fails every higher-veto-priority dataset's
    trigger) -- each only computed when every path involved is present
    in this file

Usage:
    python trigger_preflight_on_file.py --record-id 30522 \
        --file-index-start 0 --file-index-end 8 \
        --dataset-label DoubleMuon --era G \
        --output-dir /storage/.../job_DoubleMuon_G_0
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

import numpy as np  # noqa: E402
import uproot  # noqa: E402

from services.parsing.validated_runs import ValidatedRunsFilter, apply_validated_runs_filter  # noqa: E402
from studies.m0m1j0_cms.design_checks.common import fetch_file_list  # noqa: E402
from studies.cms_datasets.cluster.datasets_records import (  # noqa: E402
    DATASETS,
    VETO_ORDER,
    NESTED_REFERENCE_PAIRS,
    all_step1_hlt_branches,
)

DEFAULT_VALIDATED_RUNS_JSON = (
    "data/cms/validated_runs/Cert_271036-284044_13TeV_Legacy2016_Collisions16_JSON.txt"
)

READ_RETRY_ATTEMPTS = 4
READ_RETRY_BACKOFF_SEC = 15
READ_CHUNK_SIZE = 300_000

TRIGGER_PATHS_BY_DATASET = {d.label: d.trigger_paths for d in DATASETS}


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
            return tree.arrays(branches, entry_start=entry_start, entry_stop=entry_stop, library="np")
        except Exception as e:  # noqa: BLE001 -- transient XRootD read failure
            last_exc = e
            print(f"read attempt {attempt}/{READ_RETRY_ATTEMPTS} failed for {file_url} "
                  f"[{entry_start}:{entry_stop}]: {type(e).__name__}: {e}", flush=True)
            if attempt < READ_RETRY_ATTEMPTS:
                time.sleep(READ_RETRY_BACKOFF_SEC)
    raise RuntimeError(
        f"{file_url} [{entry_start}:{entry_stop}]: failed to read after {READ_RETRY_ATTEMPTS} attempts"
    ) from last_exc


def read_branches_chunked(file_url: str, branches: list) -> dict:
    tree = uproot.open(file_url)["Events"]
    n_entries = tree.num_entries
    chunk_arrays = {b: [] for b in branches}
    for start in range(0, n_entries, READ_CHUNK_SIZE):
        stop = min(start + READ_CHUNK_SIZE, n_entries)
        chunk = _read_chunk_with_retry(tree, branches, start, stop, file_url)
        for b in branches:
            chunk_arrays[b].append(np.asarray(chunk[b]))
    return {b: (np.concatenate(v) if len(v) > 1 else v[0]) for b, v in chunk_arrays.items()}


def process_one_file(record_id: int, file_index: int, dataset_label: str, validated_runs) -> dict:
    file_url = resolve_file_url(record_id, file_index)
    tree = uproot.open(file_url)["Events"]
    available = set(tree.keys())

    wanted_hlt = all_step1_hlt_branches()
    present_hlt = [b for b in wanted_hlt if b in available]
    missing_hlt = [b for b in wanted_hlt if b not in available]

    required_always = ["run", "luminosityBlock"]
    missing_required = [b for b in required_always if b not in available]
    if missing_required:
        raise ValueError(f"{file_url}: missing required branch(es) {missing_required} -- cannot proceed")

    branches = required_always + present_hlt
    data = read_branches_chunked(file_url, branches)
    n_read = len(data["run"])

    # Reuse services.parsing.validated_runs directly: it operates on an
    # awkward-Array-like object exposing .fields and __getitem__; a plain
    # dict of numpy arrays wrapped this way satisfies apply_validated_runs_filter's
    # needs (it only ever accesses events["run"], events["luminosityBlock"],
    # events.fields, and boolean-masks via events[mask]) -- built via
    # awkward.zip so booleans/mask-slicing behave exactly like every other
    # driver's own real awkward-Array usage, not reimplemented here.
    import awkward as ak
    events = ak.Array({b: data[b] for b in branches})
    events_golden, golden_stats = apply_validated_runs_filter(events, validated_runs)
    n_after_golden = golden_stats["n_after"]

    golden_run = np.asarray(events_golden["run"])
    golden_masks = {b: np.asarray(events_golden[b]).astype(bool) for b in present_hlt}

    own_paths = TRIGGER_PATHS_BY_DATASET[dataset_label]
    own_paths_present = [p for p in own_paths if p in golden_masks]
    own_mask = None
    if len(own_paths_present) == len(own_paths) and own_paths:
        own_mask = np.zeros(len(golden_run), dtype=bool)
        for p in own_paths_present:
            own_mask |= golden_masks[p]

    other_masks_by_dataset = {}
    for d in DATASETS:
        if d.label == dataset_label:
            continue
        paths_present = [p for p in d.trigger_paths if p in golden_masks]
        if len(paths_present) == len(d.trigger_paths) and d.trigger_paths:
            m = np.zeros(len(golden_run), dtype=bool)
            for p in paths_present:
                m |= golden_masks[p]
            other_masks_by_dataset[d.label] = m

    higher_priority = VETO_ORDER[:VETO_ORDER.index(dataset_label)]
    exclusive_mask = None
    if own_mask is not None and all(h in other_masks_by_dataset for h in higher_priority):
        vetoed = np.zeros(len(golden_run), dtype=bool)
        for h in higher_priority:
            vetoed |= other_masks_by_dataset[h]
        exclusive_mask = own_mask & ~vetoed
    elif own_mask is not None and not higher_priority:
        exclusive_mask = own_mask.copy()

    runs_present = np.unique(golden_run)
    per_run = {}
    for run in runs_present.tolist():
        run_mask = golden_run == run
        n_golden = int(run_mask.sum())
        per_path_fires = {p: int((golden_masks[p] & run_mask).sum()) for p in present_hlt}

        nested = {}
        for looser, stricter in NESTED_REFERENCE_PAIRS:
            if looser in golden_masks and stricter in golden_masks:
                n_stricter = int((golden_masks[stricter] & run_mask).sum())
                n_both = int((golden_masks[looser] & golden_masks[stricter] & run_mask).sum())
                nested[f"{looser}__vs__{stricter}"] = {"n_stricter": n_stricter, "n_looser_and_stricter": n_both}

        own = None
        if own_mask is not None:
            own_this_run = own_mask & run_mask
            n_own = int(own_this_run.sum())
            overlap = {}
            for other_label, m in other_masks_by_dataset.items():
                overlap[other_label] = int((own_this_run & m).sum())
            n_exclusive = int((exclusive_mask & run_mask).sum()) if exclusive_mask is not None else None
            own = {"n_own_trigger": n_own, "n_also_passing": overlap, "n_exclusive": n_exclusive}

        per_run[str(run)] = {
            "n_golden": n_golden,
            "per_path_fires": per_path_fires,
            "nested_reference_pairs": nested,
            "own_dataset": own,
        }

    return {
        "file_index": file_index,
        "file_url": file_url,
        "missing_hlt_branches": missing_hlt,
        "n_read": n_read,
        "n_after_golden_json": n_after_golden,
        "runs": per_run,
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--record-id", type=int, required=True)
    p.add_argument("--file-index-start", type=int, required=True)
    p.add_argument("--file-index-end", type=int, required=True, help="exclusive")
    p.add_argument("--dataset-label", required=True)
    p.add_argument("--era", required=True, choices=["G", "H"])
    p.add_argument("--output-dir", required=True)
    p.add_argument("--validated-runs-json", default=DEFAULT_VALIDATED_RUNS_JSON)
    args = p.parse_args()

    t0 = time.time()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    validated_runs = ValidatedRunsFilter(args.validated_runs_json)

    per_file_results = []
    for file_index in range(args.file_index_start, args.file_index_end):
        print(f"[{args.dataset_label} {args.era}] processing record {args.record_id} file {file_index}...", flush=True)
        result = process_one_file(args.record_id, file_index, args.dataset_label, validated_runs)
        per_file_results.append(result)
        print(f"[{args.dataset_label} {args.era}] file {file_index}: n_read={result['n_read']} "
              f"n_after_golden_json={result['n_after_golden_json']} "
              f"missing_hlt_branches={result['missing_hlt_branches']}", flush=True)

    elapsed = time.time() - t0
    out = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "git_commit": git_commit_hash(REPO_ROOT),
        "dataset_label": args.dataset_label,
        "era": args.era,
        "record_id": args.record_id,
        "file_index_start": args.file_index_start,
        "file_index_end": args.file_index_end,
        "validated_runs_sha256": validated_runs.sha256,
        "elapsed_sec": elapsed,
        "per_file": per_file_results,
    }
    out_path = output_dir / "preflight_result.json"
    out_path.write_text(json.dumps(out), encoding="utf-8")
    print(f"wrote {out_path} ({elapsed:.1f}s elapsed)")


if __name__ == "__main__":
    main()
