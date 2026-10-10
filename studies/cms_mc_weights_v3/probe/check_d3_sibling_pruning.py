#!/usr/bin/env python
"""
Design item D3: does fork master's prune_final_states_below_min_events leave
orphan sibling arrays behind?

Builds a throwaway SQLite shard in a temp directory with two final states --
one below the >=100-event threshold, one above -- each carrying its physics
invariant-mass signature plus the sibling arrays the v3 design wants to store
next to it. Then calls the REAL
services/storage/sqlite_shards.py::prune_final_states_below_min_events and
reports exactly which rows survive.

Also prints, for each candidate sibling suffix, whether it is matched by:
  * fork master's prune regex          (db1bd32, pre-#35)
  * PR #35's prune regex               (fa63544, adds an optional _mcw)
  * the fix this design proposes       (an optional _mcw OR _mcraw_<field>)
  * the histogram-grouping regex        (which must NEVER match a sibling,
    or the sibling would be histogrammed as if it were a mass spectrum)

Writes nothing outside the system temp directory; touches no cluster output.

Run:  python studies/cms_mc_weights_v3/probe/check_d3_sibling_pruning.py
"""
from __future__ import annotations

import json
import os
import pathlib
import re
import sys
import tempfile

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3]))

from services.storage.sqlite_shards import (  # noqa: E402
    SqliteArrayShardWriter, list_signatures, prune_final_states_below_min_events,
)

JOB_TAG = "job_tag"
SMALL_FS, SMALL_N = "0e_2m_5j_1b", 10     # below the >=100 threshold: pruned
BIG_FS, BIG_N = "0e_2m_1j_0b", 500        # above it: survives
MIN_EVENTS = 100

# _mcw is reserved for the FINAL normalised weight (PR #35's convention, and
# this design keeps it). The raw per-event siblings use the _mcraw_<field>
# family so one regex alternative covers all of them.
SIBLING_SUFFIXES = ("_mcw", "_mcraw_genw", "_mcraw_l1pf", "_mcraw_acc")
ALL_CANDIDATE_SUFFIXES = (
    "", "_mcw", "_mcraw_genw", "_mcraw_l1pf",
    "_mcraw_puntrue", "_mcraw_acc", "_mcraw_ele27pt",
)

FORK_PRUNE_RE = re.compile(r"(_FS_[0-9a-z_]+)_IM_([0-9a-z]+)$")
PR35_PRUNE_RE = re.compile(r"(_FS_[0-9a-z_]+)_IM_([0-9a-z]+)(_mcw)?$")
PROPOSED_PRUNE_RE = re.compile(
    r"(_FS_[0-9a-z_]+)_IM_([0-9a-z]+)(_mcw|_mcraw_[a-z0-9]+)?$")
HIST_GROUPING_RE = re.compile(r"_FS_([0-9emjgtb_]+)_IM_([emjgtb\d]+)$")


def main() -> int:
    tmp_dir = tempfile.mkdtemp(prefix="d3_prune_check_")
    db_path = os.path.join(tmp_dir, "shard.sqlite")

    writer = SqliteArrayShardWriter(db_path)
    for final_state, n in ((SMALL_FS, SMALL_N), (BIG_FS, BIG_N)):
        base = f"{JOB_TAG}_FS_{final_state}_IM_m0m1"
        writer.record_final_state_count(final_state, n)
        writer.append_array(base, np.arange(n, dtype=np.float32))
        for suffix in SIBLING_SUFFIXES:
            writer.append_array(base + suffix, np.ones(n, dtype=np.float32))
    writer.commit()
    writer.close()

    before = sorted(list_signatures(db_path))
    removed = prune_final_states_below_min_events(db_path, min_events=MIN_EVENTS)
    after = sorted(list_signatures(db_path))
    orphans = [s for s in after if SMALL_FS in s]

    regex_table = []
    for suffix in ALL_CANDIDATE_SUFFIXES:
        name = f"{JOB_TAG}_FS_{SMALL_FS}_IM_m0m1{suffix}"
        regex_table.append({
            "suffix": suffix or "(none: the physics signature itself)",
            "fork_master_prune_regex_matches": bool(FORK_PRUNE_RE.search(name)),
            "pr35_prune_regex_matches": bool(PR35_PRUNE_RE.search(name)),
            "proposed_prune_regex_matches": bool(PROPOSED_PRUNE_RE.search(name)),
            "histogram_grouping_regex_matches": bool(HIST_GROUPING_RE.search(name)),
        })

    print(json.dumps({
        "temp_db": db_path,
        "min_events": MIN_EVENTS,
        "signatures_before_prune": before,
        "final_states_removed": removed,
        "signatures_after_prune": after,
        "orphaned_siblings_of_the_pruned_final_state": orphans,
        "n_orphans": len(orphans),
        "regex_behaviour_by_suffix": regex_table,
    }, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
