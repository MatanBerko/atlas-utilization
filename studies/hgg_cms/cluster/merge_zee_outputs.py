#!/usr/bin/env python
"""
Implementation task 6, Part 4: merge for the Z->e+e- control-region run.

Simpler than merge_outputs.py: every Z->ee job (data or DY, main or
trigger-eff sample) uses the SAME one-file-per-job array-job layout
(pbs_hgg_zee_array.sh), so there is only one mode here, not a data/signal
split. Same verified identity-check method as merge_outputs.py's data
mode: each job's own metadata_cache.json + its array index, sliced with
the real utils.batching.get_batch_slice_by_year, checked against a frozen
expected file list -- cms_hgg_data_file_lists.json (133 DoubleEG files,
shared with the main run) for data variants, cms_zee_dy_file_list.json
(41 DY files) for DY variants. No blinding logic anywhere in this script
-- the Z->ee output has no blinded window (studies/hgg_cms/zee_output.py).

Usage:
    python merge_zee_outputs.py --variant data_full --total-batches 133 \
        --jobs-base /storage/.../hgg_zee/data_full \
        --expected-json studies/hgg_cms/impl_checks/mapping_check/cms_hgg_data_file_lists.json \
        --merged-out /storage/.../hgg_zee/merged/zee_data.root \
        --out /storage/.../hgg_zee/merged/merge_summary_zee_data.json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

from utils.batching import get_batch_slice_by_year  # noqa: E402
from studies.hgg_cms.cluster.merge_outputs import normalize_url  # noqa: E402


def _load_json(path: Path):
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def discover_job_indices(jobs_base: Path) -> list:
    indices = []
    if not jobs_base.exists():
        return indices
    for d in jobs_base.iterdir():
        m = re.fullmatch(r"job_(\d+)", d.name)
        if d.is_dir() and m:
            indices.append(int(m.group(1)))
    return sorted(indices)


def merge(jobs_base: Path, total_batches: int, expected_json: Path, out_path: Path,
          force: bool, merged_out: Path = None) -> int:
    expected_raw = _load_json(expected_json)
    if expected_raw is None:
        raise FileNotFoundError(f"expected file list not found: {expected_json}")
    expected = {k: [normalize_url(u) for u in v] for k, v in expected_raw.items()}
    expected_total = sum(len(v) for v in expected.values())

    present = discover_job_indices(jobs_base)
    missing_jobs, identity_errors = [], []
    assigned_by_url = {}
    per_record_assigned = {k: [] for k in expected}
    total_cutflow = {}
    root_files = []

    for i in present:
        job_dir = jobs_base / f"job_{i}"
        job_meta = _load_json(job_dir / "selected" / "job_metadata.json")
        if job_meta is None:
            missing_jobs.append(i)
            continue
        cache = _load_json(job_dir / "metadata_cache.json")
        if cache is None:
            identity_errors.append({"index": i, "error": "missing metadata_cache.json"})
        else:
            try:
                sliced = get_batch_slice_by_year(cache, i, total_batches)
            except Exception as e:  # noqa: BLE001
                identity_errors.append({"index": i, "error": f"{type(e).__name__}: {e}"})
                sliced = None
            if sliced is not None:
                n = sum(len(v) for v in sliced.values())
                if n != 1:
                    identity_errors.append({"index": i, "error": f"batching gave {n} files, expected 1"})
                else:
                    (record_key, urls), = sliced.items()
                    norm = normalize_url(urls[0])
                    assigned_by_url.setdefault(norm, []).append(i)
                    per_record_assigned.setdefault(record_key, []).append(norm)

        for k, v in job_meta.get("cutflow", {}).items():
            if isinstance(v, (int, float)):
                total_cutflow[k] = total_cutflow.get(k, 0) + v

        sel_dir = job_dir / "selected"
        if sel_dir.exists():
            root_files.extend(sorted(sel_dir.glob("*.root")))

    duplicated = {u: idxs for u, idxs in assigned_by_url.items() if len(idxs) > 1}
    all_assigned = set(assigned_by_url.keys())
    all_expected = set(u for urls in expected.values() for u in urls)
    missing_files = sorted(all_expected - all_assigned)
    unexpected_files = sorted(all_assigned - all_expected)
    per_record_coverage = {
        k: {"n_expected": len(v), "n_assigned": len(per_record_assigned.get(k, [])),
            "fully_covered": sorted(per_record_assigned.get(k, [])) == sorted(v)}
        for k, v in expected.items()
    }

    problems = (
        bool(missing_jobs) or bool(identity_errors) or bool(duplicated)
        or bool(missing_files) or bool(unexpected_files)
        or not all(v["fully_covered"] for v in per_record_coverage.values())
        or len(present) != expected_total
    )
    status = "COMPLETE" if not problems else ("COMPLETE_FORCED_WITH_MISSING" if force else "INCOMPLETE")

    summary = {
        "jobs_base": str(jobs_base), "status": status,
        "expected_total_files": expected_total, "n_job_dirs_present": len(present),
        "missing_jobs_no_metadata": missing_jobs,
        "identity_reconstruction_errors": identity_errors,
        "duplicated_files": duplicated, "missing_files": missing_files,
        "unexpected_files": unexpected_files, "per_record_coverage": per_record_coverage,
        "total_cutflow": total_cutflow,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))

    if merged_out is not None and (status != "INCOMPLETE"):
        import awkward as ak
        import uproot
        from studies.hgg_cms.zee_output import read_zee_output
        if root_files:
            arrays = [read_zee_output(p) for p in root_files]
            merged = ak.concatenate(arrays) if len(arrays) > 1 else arrays[0]
            packed = ak.to_packed(merged)
            merged_out.parent.mkdir(parents=True, exist_ok=True)
            with uproot.recreate(str(merged_out)) as f:
                f["events"] = {field: packed[field] for field in packed.fields}
            print(f"\nwrote {merged_out} ({len(packed)} events, from {len(root_files)} input files)")
        else:
            print("\nno .root files found to merge")

    return 0 if status != "INCOMPLETE" else 1


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--jobs-base", required=True)
    p.add_argument("--total-batches", type=int, required=True)
    p.add_argument("--expected-json", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--merged-out", default=None)
    p.add_argument("--force", action="store_true")
    args = p.parse_args()
    merged_out = Path(args.merged_out) if args.merged_out else None
    rc = merge(Path(args.jobs_base), args.total_batches, Path(args.expected_json),
               Path(args.out), args.force, merged_out)
    sys.exit(rc)


if __name__ == "__main__":
    main()
