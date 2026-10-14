#!/usr/bin/env python
"""
Part B, second check: the one `services/` change -- the sibling-tolerant prune
regex -- is data-neutral on REAL delivered shards.

Takes a set of delivered per-file shards, makes two independent SCRATCH COPIES
of each, and runs the >= 100-events-per-final-state prune twice:

  * once with the CURRENT (committed) `services/storage/sqlite_shards.py`;
  * once with the PRE-CHANGE version of that module, loaded straight out of
    git history at `--old-commit` (default: fork master `db1bd32`) and
    executed. It is the real old code, not a transcription of it, so the
    comparison cannot be wrong about what the old behaviour was.

Then asserts the two produce the SAME removed final states, the SAME surviving
signature set and the SAME surviving entry counts. A data shard contains no
`_mcw` or `_mcraw_*` row, so the new pattern's third group is always None and
every decision in the body is the one the old code made -- this check
demonstrates that on real data rather than arguing it.

The delivered shards themselves are only ever READ (copied with shutil.copy2);
both prunes run on the copies, which is what the data builder itself does.

Run:
    python studies/cms_mc_weights_v3/cluster/check_prune_regex_data_neutral.py \
        --runs-dir /storage/.../output/cms_datasets/runs_matched4_full_20261007 \
        --mapping  /storage/.../work/cms_mc_v3_impl_<date>/data_files.txt \
        --scratch  /storage/.../work/cms_mc_v3_impl_<date>/prune_scratch \
        --out      /storage/.../work/cms_mc_v3_impl_<date>/evidence/prune_regex.json
"""
from __future__ import annotations

import argparse
import json
import pathlib
import shutil
import sqlite3
import subprocess
import sys
import types

REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

from services.storage.sqlite_shards import (  # noqa: E402
    prune_final_states_below_min_events as prune_new,
)
from studies.cms_coverage.cluster.merge_and_count import PRIMARY_MIN_EVENTS_PER_FS  # noqa: E402

MODULE_PATH = "services/storage/sqlite_shards.py"
DEFAULT_OLD_COMMIT = "db1bd32"   # fork master, before this round's change
SHARD_NAME = "dataset_shard_rare4_inclusive.sqlite"


def load_old_module(commit: str) -> tuple[types.ModuleType, str]:
    """Import `services/storage/sqlite_shards.py` AS IT WAS at `commit`.

    Returns the module and its source, so the report can record exactly which
    bytes were executed as "the old behaviour"."""
    source = subprocess.check_output(
        ["git", "show", f"{commit}:{MODULE_PATH}"], cwd=str(REPO_ROOT), text=True)
    module = types.ModuleType(f"sqlite_shards_at_{commit}")
    module.__file__ = f"<{commit}:{MODULE_PATH}>"
    exec(compile(source, module.__file__, "exec"), module.__dict__)
    if not hasattr(module, "prune_final_states_below_min_events"):
        raise SystemExit(
            f"{commit}:{MODULE_PATH} has no prune_final_states_below_min_events")
    return module, source


def shard_state(path: str) -> dict:
    conn = sqlite3.connect(f"file:{pathlib.Path(path).as_posix()}?mode=ro", uri=True)
    try:
        sigs = conn.execute(
            "SELECT signature, COALESCE(SUM(n_entries), 0) FROM array_chunks "
            "GROUP BY signature ORDER BY signature").fetchall()
        fs = conn.execute(
            "SELECT final_state, COALESCE(SUM(n_events), 0) FROM final_state_counts "
            "GROUP BY final_state ORDER BY final_state").fetchall()
    finally:
        conn.close()
    return {"signatures": {s: int(n) for s, n in sigs},
            "final_state_counts": {f: int(n) for f, n in fs}}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs-dir", required=True)
    ap.add_argument("--mapping", required=True,
                    help="the Part B mapping file: "
                         "'<idx> <dataset> <record> <file_index> <job_dir_index>'")
    ap.add_argument("--scratch", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--min-events", type=int, default=PRIMARY_MIN_EVENTS_PER_FS)
    ap.add_argument("--old-commit", default=DEFAULT_OLD_COMMIT)
    args = ap.parse_args()

    runs_dir = pathlib.Path(args.runs_dir)
    scratch = pathlib.Path(args.scratch)
    for sub in ("new_code", "old_code"):
        (scratch / sub).mkdir(parents=True, exist_ok=True)

    old_module, old_source = load_old_module(args.old_commit)
    prune_old = old_module.prune_final_states_below_min_events
    old_pattern = None
    for line in old_source.splitlines():
        if "pattern = re.compile" in line:
            old_pattern = line.strip()
            break
    if old_pattern is None or "_mcraw_" in old_pattern:
        raise SystemExit(
            f"the module at {args.old_commit} does not carry the PRE-change "
            f"pattern (found {old_pattern!r}). Refusing to report a pass.")

    sources = []
    for line in pathlib.Path(args.mapping).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        _idx, dataset, _record, _file_index, job_dir_index = line.split()
        src = runs_dir / dataset / f"job_{job_dir_index}" / SHARD_NAME
        if not src.exists():
            raise SystemExit(f"missing delivered shard: {src}")
        sources.append((f"{dataset}_job{job_dir_index}", src))

    new_paths, old_paths = [], []
    for tag, src in sources:
        for sub, bucket in (("new_code", new_paths), ("old_code", old_paths)):
            dest = scratch / sub / f"{tag}_{SHARD_NAME}"
            shutil.copy2(src, dest)
            bucket.append(str(dest))

    before = {pathlib.Path(p).name: shard_state(p) for p in new_paths}
    before_old = {pathlib.Path(p).name: shard_state(p) for p in old_paths}
    if before != before_old:
        raise SystemExit("the two scratch copies differ before pruning")

    removed_new = prune_new(new_paths, args.min_events)
    removed_old = prune_old(old_paths, args.min_events)

    after_new = {pathlib.Path(p).name: shard_state(p) for p in new_paths}
    after_old = {pathlib.Path(p).name: shard_state(p) for p in old_paths}

    diffs = []
    if sorted(removed_new) != sorted(removed_old):
        diffs.append({"kind": "removed_final_states",
                      "only_new": sorted(set(removed_new) - set(removed_old)),
                      "only_old": sorted(set(removed_old) - set(removed_new))})
    for name in sorted(set(after_new) | set(after_old)):
        a = after_new.get(name, {}).get("signatures", {})
        b = after_old.get(name, {}).get("signatures", {})
        if a != b:
            only_a = sorted(set(a) - set(b))
            only_b = sorted(set(b) - set(a))
            changed = sorted(s for s in set(a) & set(b) if a[s] != b[s])
            diffs.append({"kind": "surviving_signatures", "shard": name,
                          "n_only_new": len(only_a), "n_only_old": len(only_b),
                          "n_entry_count_changed": len(changed),
                          "only_new_sample": only_a[:10],
                          "only_old_sample": only_b[:10],
                          "changed_sample": changed[:10]})
        fa = after_new.get(name, {}).get("final_state_counts", {})
        fb = after_old.get(name, {}).get("final_state_counts", {})
        if fa != fb:
            diffs.append({"kind": "final_state_counts", "shard": name})

    n_before = sum(len(v["signatures"]) for v in before.values())
    n_after = sum(len(v["signatures"]) for v in after_new.values())
    entries_before = sum(sum(v["signatures"].values()) for v in before.values())
    entries_after = sum(sum(v["signatures"].values()) for v in after_new.values())

    report = {
        "what": "Part B second check: the sibling-tolerant prune regex is "
                "data-neutral on real delivered shards",
        "runs_dir": str(runs_dir),
        "n_shards": len(sources),
        "shards": [tag for tag, _ in sources],
        "min_events_per_fs": args.min_events,
        "old_code_from_commit": args.old_commit,
        "old_code_module": f"{args.old_commit}:{MODULE_PATH}",
        "old_pattern_line": old_pattern,
        "new_pattern_line": "pattern = re.compile(r\"(_FS_[0-9a-z_]+)_IM_"
                            "([0-9a-z]+)(_mcw|_mcraw_[a-z0-9]+)?$\")",
        "how": "both prunes ran on independent scratch copies of the same "
               "delivered shards; the old code was exec'd straight out of git "
               "history, not transcribed",
        "n_signatures_before_prune": n_before,
        "n_signatures_after_prune": n_after,
        "n_entries_before_prune": entries_before,
        "n_entries_after_prune": entries_after,
        "n_final_states_removed_new_code": len(removed_new),
        "n_final_states_removed_old_code": len(removed_old),
        "final_states_removed_new_code": sorted(removed_new),
        "final_states_removed_old_code": sorted(removed_old),
        "n_differences": len(diffs),
        "differences": diffs,
        "VERDICT": ("DATA-NEUTRAL -- the old and the new code give identical "
                    "results on real delivered shards" if not diffs else
                    f"NOT NEUTRAL -- {len(diffs)} difference(s); STOP"),
    }
    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(f"shards:                     {len(sources)}")
    print(f"old code from:              {args.old_commit}:{MODULE_PATH}")
    print(f"old pattern:                {old_pattern}")
    print(f"signatures before prune:    {n_before:,}")
    print(f"signatures after prune:     {n_after:,}")
    print(f"entries before / after:     {entries_before:,} / {entries_after:,}")
    print(f"final states removed, new:  {len(removed_new)}")
    print(f"final states removed, old:  {len(removed_old)}")
    print(f"\nVERDICT: {report['VERDICT']}")
    print(f"wrote {out}")
    return 0 if not diffs else 1


if __name__ == "__main__":
    sys.exit(main())
