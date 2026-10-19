#!/usr/bin/env python
"""
Drift check for the CMS-owned copy of upstream's pruning function
(studies/cms_mc_weights_v3/deliver/cms_shard_pruning.py).

  1. upstream's services/storage/sqlite_shards.py::prune_final_states_below_min_events
     must still be exactly the 7f2da5d (#35) source recorded below. If this fails,
     upstream changed the function: re-compare the CMS copy with it, port
     the change (keeping only the D3 lines different), and update the
     recorded hash.
  2. the CMS copy must differ from upstream ONLY in the D3 lines (the
     three-group pattern, the three-way unpack, the `not is_sibling` guard,
     and comment lines).
  3. behaviour: on a data-only shard the two functions remove the same final
     states and leave the same rows; on a shard with MC siblings the CMS copy
     leaves no orphan sibling rows (upstream's leaves some, which is why the
     copy exists).

Runs under pytest, or directly:
    python studies/cms_mc_weights_v3/tests/test_cms_shard_pruning_drift.py
"""
from __future__ import annotations

import ast
import difflib
import hashlib
import os
import pathlib
import shutil
import sys
import tempfile

import numpy as np

REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

from services.storage import sqlite_shards as upstream  # noqa: E402
from services.storage.sqlite_shards import SqliteArrayShardWriter, list_signatures  # noqa: E402
from studies.cms_datasets.cluster.run_dataset_on_file import (  # noqa: E402
    MC_SIBLING_SUFFIXES,
    MC_WEIGHT_SUFFIX,
)
from studies.cms_mc_weights_v3.deliver import cms_shard_pruning as cms  # noqa: E402

# The real sibling suffixes the MC driver writes, plus the reserved "_mcw".
SIBLINGS = tuple(MC_SIBLING_SUFFIXES) + (MC_WEIGHT_SUFFIX,)

FUNCTION = "prune_final_states_below_min_events"
UPSTREAM_FILE = REPO_ROOT / "services" / "storage" / "sqlite_shards.py"
CMS_FILE = REPO_ROOT / "studies" / "cms_mc_weights_v3" / "deliver" / "cms_shard_pruning.py"

# sha256 of the function's source text (def line to last line, "\n"-joined,
# trailing newline) in upstream commit 7f2da5d97e539b758bc6c861eca5f794e3431add
# (#35, which taught upstream's pattern the "_mcw" sibling but not the CMS
# "_mcraw_<field>" family). Previously recorded: e1ce8bb, sha256 a32c9434...
RECORDED_UPSTREAM_COMMIT = "7f2da5d97e539b758bc6c861eca5f794e3431add"
RECORDED_UPSTREAM_SHA256 = "3a0add92e5d71581c25afb72ced0b5226abccf29fd9ad3dadac3e10fcfa510ac"

D3_REMOVED = [
    "    # ``_mcw`` rows are the per-event MC weights of a combination; they are",
    "    # removed with their final state but never counted as events.",
    '    pattern = re.compile(r"(_FS_[0-9a-z_]+)_IM_([0-9a-z]+)(_mcw)?$")',
    "            final_state, combination, is_weight = match.groups()",
    "            if final_state not in counted_final_states and not is_weight:",
]
D3_ADDED_CODE = [
    '    pattern = re.compile(r"(_FS_[0-9a-z_]+)_IM_([0-9a-z]+)(_mcw|_mcraw_[a-z0-9]+)?$")',
    "            final_state, combination, is_sibling = match.groups()",
    "            if final_state not in counted_final_states and not is_sibling:",
]


def _function_source(path: pathlib.Path) -> str:
    text = path.read_text(encoding="utf-8")
    node = [n for n in ast.parse(text).body if getattr(n, "name", "") == FUNCTION][0]
    return "\n".join(text.split("\n")[node.lineno - 1:node.end_lineno]) + "\n"


def test_upstream_function_unchanged() -> None:
    digest = hashlib.sha256(_function_source(UPSTREAM_FILE).encode("utf-8")).hexdigest()
    assert digest == RECORDED_UPSTREAM_SHA256, (
        f"upstream {FUNCTION} changed since {RECORDED_UPSTREAM_COMMIT[:7]} "
        f"(sha256 {digest}); re-compare {CMS_FILE.name} with it before using the MC builder")


def test_copy_differs_only_in_d3_lines() -> None:
    up = _function_source(UPSTREAM_FILE).splitlines()
    cp = _function_source(CMS_FILE).splitlines()
    removed, added = [], []
    for line in difflib.ndiff(up, cp):
        if line.startswith("- "):
            removed.append(line[2:])
        elif line.startswith("+ "):
            added.append(line[2:])
    added_code = [l for l in added if l.strip() and not l.strip().startswith("#")]
    assert removed == D3_REMOVED, f"unexpected lines removed from upstream: {removed}"
    assert added_code == D3_ADDED_CODE, f"unexpected code added to upstream: {added_code}"


def _write_shard(path: str, with_siblings: bool) -> None:
    w = SqliteArrayShardWriter(path)
    for fs, n in (("0e_2m_5j_1b", 10), ("0e_2m_1j_0b", 500)):
        w.record_final_state_count(fs, n)
        base = f"job_FS_{fs}_IM_m0m1"
        w.append_array(base, np.arange(n, dtype=np.float32))
        if with_siblings:
            for suffix in SIBLINGS:
                w.append_array(base + suffix, np.ones(n, dtype=np.float32))
    w.commit()
    w.close()


def _prune_both(with_siblings: bool):
    tmp = tempfile.mkdtemp()
    try:
        a, b = os.path.join(tmp, "a.sqlite"), os.path.join(tmp, "b.sqlite")
        _write_shard(a, with_siblings)
        shutil.copy2(a, b)
        ra = upstream.prune_final_states_below_min_events(a, 100)
        rb = cms.prune_final_states_below_min_events(b, 100)
        return ra, sorted(list_signatures(a)), rb, sorted(list_signatures(b))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_data_shard_behaviour_identical() -> None:
    ra, sa, rb, sb = _prune_both(with_siblings=False)
    assert ra == rb == ["_FS_0e_2m_5j_1b"], (ra, rb)
    assert sa == sb == ["job_FS_0e_2m_1j_0b_IM_m0m1"], (sa, sb)


def test_mc_shard_no_orphans_with_cms_copy() -> None:
    ra, sa, rb, sb = _prune_both(with_siblings=True)
    assert rb == ["_FS_0e_2m_5j_1b"], rb
    assert not [s for s in sb if "0e_2m_5j_1b" in s], f"CMS copy left orphans: {sb}"
    assert len(sb) == 1 + len(SIBLINGS), sb  # surviving mass array + its siblings
    # Upstream's version leaves the pruned final state's siblings behind --
    # the reason this copy exists. If this ever stops being true, upstream
    # has adopted an equivalent fix and the copy may no longer be needed.
    assert [s for s in sa if "0e_2m_5j_1b" in s], "upstream no longer leaves orphans"


if __name__ == "__main__":
    failures = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"[PASS] {name}")
            except AssertionError as exc:
                failures += 1
                print(f"[FAIL] {name}: {exc}")
    print(f"{'ALL PASSED' if not failures else f'{failures} FAILED'}")
    sys.exit(1 if failures else 0)
