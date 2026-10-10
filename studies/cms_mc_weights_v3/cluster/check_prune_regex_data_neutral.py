#!/usr/bin/env python
"""
Part B, second check: the one `services/` change -- the sibling-tolerant prune
regex -- is data-neutral on REAL delivered shards.

Takes a set of delivered per-file shards, makes two independent SCRATCH COPIES
of each, and runs the >= 100-events-per-final-state prune twice:

  * once with the NEW (committed) sibling-tolerant pattern;
  * once with the OLD `$`-anchored pattern, monkeypatched back in for the
    duration of that call only.

Then asserts the two produce the SAME removed final states, the SAME surviving
signature set and the SAME surviving entry counts. Since a data shard contains
no `_mcw` or `_mcraw_*` row, the third regex group is always None and every
decision in the function body is identical -- this check demonstrates that on
real data rather than arguing it.

The delivered shards themselves are only ever READ (copied with shutil.copy2);
the prune runs on the copies, which is what the data builder itself does.

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
import re
import shutil
import sqlite3
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

from services.storage import sqlite_shards  # noqa: E402
from services.storage.sqlite_shards import (  # noqa: E402
    list_signatures,
    prune_final_states_below_min_events,
)
from studies.cms_coverage.cluster.merge_and_count import PRIMARY_MIN_EVENTS_PER_FS  # noqa: E402

# The pattern fork master carried before this round's change.
OLD_PATTERN_SOURCE = r"(_FS_[0-9a-z_]+)_IM_([0-9a-z]+)$"
SHARD_NAME = "dataset_shard_rare4_inclusive.sqlite"


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
    return {
        "signatures": {s: int(n) for s, n in sigs},
        "final_state_counts": {f: int(n) for f, n in fs},
    }


class _OldPattern:
    """Monkeypatch `re.compile` for the duration of one prune call so the
    function compiles the OLD pattern instead of the new one. Scoped and
    reverted; nothing else in the process is affected."""

    def __init__(self):
        self._real = sqlite_shards.re.compile
        self.n_swapped = 0

    def __enter__(self):
        outer = self

        def fake_compile(pattern, *a, **k):
            if "_mcraw_" in pattern:
                outer.n_swapped += 1
                return outer._real(OLD_PATTERN_SOURCE, *a, **k)
            return outer._real(pattern, *a, **k)

        sqlite_shards.re.compile = fake_compile
        return self

    def __exit__(self, *exc):
        sqlite_shards.re.compile = self._real
        return False


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs-dir", required=True)
    ap.add_argument("--mapping", required=True,
                    help="the Part B mapping file: "
                         "'<idx> <dataset> <record> <file_index> <job_dir_index>'")
    ap.add_argument("--scratch", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--min-events", type=int, default=PRIMARY_MIN_EVENTS_PER_FS)
    args = ap.parse_args()

    runs_dir = pathlib.Path(args.runs_dir)
    scratch = pathlib.Path(args.scratch)
    for sub in ("new_regex", "old_regex"):
        (scratch / sub).mkdir(parents=True, exist_ok=True)

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
        for sub, bucket in (("new_regex", new_paths), ("old_regex", old_paths)):
            dest = scratch / sub / f"{tag}_{SHARD_NAME}"
            shutil.copy2(src, dest)
            bucket.append(str(dest))

    before = {p: shard_state(p) for p in new_paths}

    removed_new = prune_final_states_below_min_events(new_paths, args.min_events)
    with _OldPattern() as patch:
        removed_old = prune_final_states_below_min_events(old_paths, args.min_events)
    if patch.n_swapped == 0:
        raise SystemExit(
            "the old-pattern monkeypatch never fired -- the committed prune no "
            "longer compiles a pattern containing '_mcraw_', so this check is "
            "not testing what it claims. Refusing to report a pass.")

    after_new = {pathlib.Path(p).name: shard_state(p) for p in new_paths}
    after_old = {pathlib.Path(p).name: shard_state(p) for p in old_paths}

    diffs = []
    if sorted(removed_new) != sorted(removed_old):
        diffs.append({
            "kind": "removed_final_states",
            "only_new": sorted(set(removed_new) - set(removed_old)),
            "only_old": sorted(set(removed_old) - set(removed_new)),
        })
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

    n_sigs_before = sum(len(v["signatures"]) for v in before.values())
    n_sigs_after = sum(len(v["signatures"]) for v in after_new.values())
    report = {
        "what": "Part B second check: the sibling-tolerant prune regex is "
                "data-neutral on real delivered shards",
        "runs_dir": str(runs_dir),
        "n_shards": len(sources),
        "shards": [tag for tag, _ in sources],
        "min_events_per_fs": args.min_events,
        "old_pattern": OLD_PATTERN_SOURCE,
        "new_pattern": r"(_FS_[0-9a-z_]+)_IM_([0-9a-z]+)(_mcw|_mcraw_[a-z0-9]+)?$",
        "n_times_old_pattern_substituted": patch.n_swapped,
        "n_signatures_before_prune": n_sigs_before,
        "n_signatures_after_prune": n_sigs_after,
        "n_final_states_removed_new_regex": len(removed_new),
        "n_final_states_removed_old_regex": len(removed_old),
        "final_states_removed_new_regex": sorted(removed_new),
        "final_states_removed_old_regex": sorted(removed_old),
        "n_differences": len(diffs),
        "differences": diffs,
        "VERDICT": ("DATA-NEUTRAL -- old and new regex give identical results "
                    "on real delivered shards" if not diffs else
                    f"NOT NEUTRAL -- {len(diffs)} difference(s); STOP"),
    }
    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(f"shards:                    {len(sources)}")
    print(f"signatures before prune:   {n_sigs_before:,}")
    print(f"signatures after prune:    {n_sigs_after:,}")
    print(f"final states removed, new: {len(removed_new)}")
    print(f"final states removed, old: {len(removed_old)}")
    print(f"old-pattern substitutions: {patch.n_swapped}")
    print(f"\nVERDICT: {report['VERDICT']}")
    print(f"wrote {out}")
    return 0 if not diffs else 1


if __name__ == "__main__":
    sys.exit(main())
