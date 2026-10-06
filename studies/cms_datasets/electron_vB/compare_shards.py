#!/usr/bin/env python
"""
E1(a)/(c): compare the shard CONTENTS of two per-file job directories.

For every version the matched/matched4 driver writes (normal, top4,
nonjet4, rare4) and both the inclusive and exclusive shard, it compares:
  * the set of signatures;
  * for every signature, the concatenated float32 mass array, bit for bit
    (same length, same values, same order);
  * the per-final-state event counts recorded in the shard.

Shards are opened with a STRICT READ-ONLY sqlite connection
(mode=ro&immutable=1) so that comparing against a production directory
cannot create a journal file beside a read-only output.

--legacy-gt-labels-b converts side B's final-state labels from the old
six-field form (0e_2m_5j_0g_0t_1b) to the upstream form as they are read,
using the delivery's own convert_legacy_fs_label -- needed only when side
B was produced before the upstream-names change.

Usage:
    python compare_shards.py --a /path/runA/job_0 --b /path/runB/job_0 \
        --out out.json
    python compare_shards.py --a-root /path/runA --b-root /path/runB \
        --jobs DoubleMuon:0,DoubleMuon:7 --out out.json
"""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

import numpy as np  # noqa: E402

from studies.cms_datasets.deliver.build_muon_combined_delivery import (  # noqa: E402
    convert_legacy_fs_label,
)

VERSIONS = {
    "normal": ("dataset_shard_inclusive.sqlite", "dataset_shard_exclusive.sqlite"),
    "top4": ("dataset_shard_top4_inclusive.sqlite", "dataset_shard_top4_exclusive.sqlite"),
    "nonjet4": ("dataset_shard_nonjet4_inclusive.sqlite", "dataset_shard_nonjet4_exclusive.sqlite"),
    "rare4": ("dataset_shard_rare4_inclusive.sqlite", "dataset_shard_rare4_exclusive.sqlite"),
}
SIG_FS_PATTERN = re.compile(r"_FS_([0-9a-z_]+)_IM_")


def _ro_connect(path: Path) -> sqlite3.Connection:
    return sqlite3.connect(f"file:{path.as_posix()}?mode=ro&immutable=1", uri=True)


def _deserialize(payload: bytes) -> np.ndarray:
    import io
    import zlib
    return np.load(io.BytesIO(zlib.decompress(payload)), allow_pickle=False)


def read_shard(path: Path, convert_legacy: bool = False):
    """{signature: concatenated float32 array}, {final_state: n_events}."""
    conn = _ro_connect(path)
    try:
        arrays = {}
        for sig, payload in conn.execute(
                "SELECT signature, payload FROM array_chunks ORDER BY id"):
            arrays.setdefault(sig, []).append(_deserialize(payload))
        counts = {}
        has_counts = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='final_state_counts'"
        ).fetchone()
        if has_counts:
            for fs, n in conn.execute(
                    "SELECT final_state, COALESCE(SUM(n_events), 0) FROM "
                    "final_state_counts GROUP BY final_state"):
                counts[fs] = int(n)
    finally:
        conn.close()
    out = {sig: np.concatenate(chunks) for sig, chunks in arrays.items()}
    if convert_legacy:
        out = {_convert_sig(sig): arr for sig, arr in out.items()}
        counts = {convert_legacy_fs_label(fs): n for fs, n in counts.items()}
    return out, counts


def _convert_sig(sig: str) -> str:
    m = SIG_FS_PATTERN.search(sig)
    if not m:
        raise ValueError(f"signature {sig!r} does not carry a _FS_<label>_IM_ part")
    return sig[:m.start(1)] + convert_legacy_fs_label(m.group(1)) + sig[m.end(1):]


def compare_one(dir_a: Path, dir_b: Path, convert_legacy_b: bool) -> dict:
    result = {"a": str(dir_a), "b": str(dir_b), "versions": {}, "identical": True}
    for version, (incl, excl) in VERSIONS.items():
        for which, name in (("inclusive", incl), ("exclusive", excl)):
            pa, pb = dir_a / name, dir_b / name
            key = f"{version}_{which}"
            if not pa.exists() and not pb.exists():
                result["versions"][key] = {"status": "absent on both sides"}
                continue
            if not pa.exists() or not pb.exists():
                result["versions"][key] = {
                    "status": "MISSING ON ONE SIDE",
                    "a_exists": pa.exists(), "b_exists": pb.exists()}
                result["identical"] = False
                continue
            arr_a, cnt_a = read_shard(pa)
            arr_b, cnt_b = read_shard(pb, convert_legacy=convert_legacy_b)
            only_a = sorted(set(arr_a) - set(arr_b))
            only_b = sorted(set(arr_b) - set(arr_a))
            differing = []
            for sig in sorted(set(arr_a) & set(arr_b)):
                a, b = arr_a[sig], arr_b[sig]
                if a.shape != b.shape or not np.array_equal(a, b):
                    differing.append({
                        "signature": sig, "n_a": int(a.size), "n_b": int(b.size),
                        "n_value_differences": (None if a.shape != b.shape
                                                else int((a != b).sum()))})
            count_diffs = {fs: [cnt_a.get(fs), cnt_b.get(fs)]
                           for fs in sorted(set(cnt_a) | set(cnt_b))
                           if cnt_a.get(fs) != cnt_b.get(fs)}
            same = not only_a and not only_b and not differing and not count_diffs
            result["versions"][key] = {
                "status": "IDENTICAL" if same else "DIFFERENT",
                "n_signatures_a": len(arr_a), "n_signatures_b": len(arr_b),
                "n_entries_a": int(sum(int(v.size) for v in arr_a.values())),
                "n_entries_b": int(sum(int(v.size) for v in arr_b.values())),
                "n_final_states_a": len(cnt_a), "n_final_states_b": len(cnt_b),
                "n_events_summed_a": int(sum(cnt_a.values())),
                "n_events_summed_b": int(sum(cnt_b.values())),
                "signatures_only_in_a": only_a[:20],
                "n_signatures_only_in_a": len(only_a),
                "signatures_only_in_b": only_b[:20],
                "n_signatures_only_in_b": len(only_b),
                "n_signatures_with_different_arrays": len(differing),
                "differing_examples": differing[:20],
                "final_state_count_differences": dict(list(count_diffs.items())[:20]),
                "n_final_state_count_differences": len(count_diffs),
            }
            if not same:
                result["identical"] = False
    return result


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--a")
    p.add_argument("--b")
    p.add_argument("--a-root")
    p.add_argument("--b-root")
    p.add_argument("--jobs", help="comma-separated Dataset:jobindex pairs")
    p.add_argument("--legacy-gt-labels-b", action="store_true")
    p.add_argument("--out", required=True)
    args = p.parse_args()

    comparisons = []
    if args.a and args.b:
        comparisons.append(("single", Path(args.a), Path(args.b)))
    elif args.a_root and args.b_root and args.jobs:
        for spec in args.jobs.split(","):
            dataset, idx = spec.split(":")
            comparisons.append((spec,
                                Path(args.a_root) / dataset / f"job_{idx}",
                                Path(args.b_root) / dataset / f"job_{idx}"))
    else:
        raise SystemExit("give either --a/--b or --a-root/--b-root/--jobs")

    out = {"what": "shard-content comparison (E1)", "n_comparisons": len(comparisons),
           "legacy_gt_labels_converted_on_b": bool(args.legacy_gt_labels_b),
           "comparisons": {}}
    all_same = True
    for tag, dir_a, dir_b in comparisons:
        res = compare_one(dir_a, dir_b, args.legacy_gt_labels_b)
        out["comparisons"][tag] = res
        all_same = all_same and res["identical"]
        print(f"{tag}: {'IDENTICAL' if res['identical'] else 'DIFFERENT'}")
        for key, v in res["versions"].items():
            if v.get("status") not in ("IDENTICAL", "absent on both sides"):
                print(f"   {key}: {v['status']} "
                      f"(only_a={v.get('n_signatures_only_in_a')}, "
                      f"only_b={v.get('n_signatures_only_in_b')}, "
                      f"arrays={v.get('n_signatures_with_different_arrays')}, "
                      f"fs_counts={v.get('n_final_state_count_differences')})")
    out["all_identical"] = all_same
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"\nall_identical = {all_same}")
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
