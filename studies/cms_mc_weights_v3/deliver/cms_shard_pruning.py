"""
CMS-owned copy of upstream's prune_final_states_below_min_events, with the
MC sibling-array change (DESIGN.md D3) applied. Used ONLY by the MC code in
studies/cms_mc_weights_v3/; the data delivery keeps calling upstream's own
function in services/storage/sqlite_shards.py, which is not modified.

Copied from
    upstream repo  Zhavi221/atlas-utilization
    file           services/storage/sqlite_shards.py
    function       prune_final_states_below_min_events
    commit         e1ce8bb2bd648a7c35d80b4efe490a20025892b9
                   (the function is byte-identical at fork commit db1bd32,
                   where the MC branch made the same change in place)

The ONLY lines that differ from upstream (everything else is verbatim):

  1. the signature pattern gains an optional third group
       upstream: pattern = re.compile(r"(_FS_[0-9a-z_]+)_IM_([0-9a-z]+)$")
       here:     pattern = re.compile(r"(_FS_[0-9a-z_]+)_IM_([0-9a-z]+)(_mcw|_mcraw_[a-z0-9]+)?$")
     (preceded by a 14-line comment explaining it);
  2. the match unpacks three groups
       upstream: final_state, combination = match.groups()
       here:     final_state, combination, is_sibling = match.groups()
  3. siblings never count as events
       upstream: if final_state not in counted_final_states:
       here:     if final_state not in counted_final_states and not is_sibling:

Why (DESIGN.md D3): an MC mass signature carries sibling arrays ("_mcw",
"_mcraw_<field>") that are weights, not events. Upstream's pattern does not
match them, so a pruned final state would leave its siblings behind as
orphan rows. With the change, siblings are deleted together with their final
state and are never counted towards its population. For a data shard there
is no sibling, the third group is always None, and every decision is the one
upstream's code makes.

MUST be re-compared whenever upstream changes
services/storage/sqlite_shards.py::prune_final_states_below_min_events.
studies/cms_mc_weights_v3/tests/test_cms_shard_pruning_drift.py fails as soon
as upstream's function source differs from the e1ce8bb version recorded
there, and checks that this copy differs from upstream only in the lines
above.
"""
from __future__ import annotations

import os
import re
import sqlite3


def prune_final_states_below_min_events(
    db_path: str | list[str],
    min_events: int,
    table_name: str = "array_chunks",
) -> list[str]:
    """Remove final states whose global event population is below a threshold.

    Chunk/file prefixes are ignored. New shards provide pre-combination-cut event
    counts directly. For legacy shards, the largest global entry count among a
    final state's invariant-mass combinations is used as its contribution. This
    uses the uncompressed SQLite metadata and does not reread ROOT payloads.
    """
    db_paths = [db_path] if isinstance(db_path, str) else list(db_path)
    db_paths = [path for path in db_paths if os.path.exists(path)]
    if min_events <= 1 or not db_paths:
        return []

    # cms-mc-weights-v3, DESIGN.md D3: a mass signature can carry MC sibling
    # arrays -- "_mcw" (the final normalised weight, PR #35's reserved
    # convention) and the raw "_mcraw_<field>" family. They are NOT events:
    # they must never contribute to a final state's population, but they MUST
    # be deleted along with their final state, or a pruned final state leaves
    # orphan rows behind (verified by running, before this change:
    # studies/cms_mc_weights_v3/probe/check_d3_sibling_pruning.py left four
    # orphans). The optional third group makes the pattern match a sibling so
    # it reaches signatures_by_db_and_fs below; `is_sibling` then keeps it out
    # of the event count.
    #
    # Data-neutral: no data signature can end in "_mcw" or "_mcraw_<field>",
    # so for a data shard the third group is always None and every decision
    # below is the one the pre-change code made. Proved on real delivered
    # shards by the Part B regression.
    pattern = re.compile(r"(_FS_[0-9a-z_]+)_IM_([0-9a-z]+)(_mcw|_mcraw_[a-z0-9]+)?$")
    legacy_totals_by_channel: dict[tuple[str, str], int] = {}
    explicit_populations: dict[str, int] = {}
    signatures_by_db_and_fs: dict[tuple[str, str], list[str]] = {}
    for path in db_paths:
        counted_final_states: set[str] = set()
        with sqlite3.connect(path) as conn:
            rows = conn.execute(
                f"""
                SELECT signature, COALESCE(SUM(n_entries), 0)
                FROM {table_name}
                GROUP BY signature
                """
            ).fetchall()
            has_count_table = conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='final_state_counts'"
            ).fetchone()
            if has_count_table:
                count_rows = conn.execute(
                    """
                    SELECT final_state, COALESCE(SUM(n_events), 0)
                    FROM final_state_counts
                    GROUP BY final_state
                    """
                ).fetchall()
                for final_state, count in count_rows:
                    normalized = (
                        final_state if final_state.startswith("_FS_")
                        else f"_FS_{final_state}"
                    )
                    counted_final_states.add(normalized)
                    explicit_populations[normalized] = (
                        explicit_populations.get(normalized, 0) + int(count)
                    )
        for signature, entries in rows:
            match = pattern.search(signature)
            if not match:
                continue
            final_state, combination, is_sibling = match.groups()
            if final_state not in counted_final_states and not is_sibling:
                key = (final_state, combination)
                legacy_totals_by_channel[key] = (
                    legacy_totals_by_channel.get(key, 0) + int(entries)
                )
            signatures_by_db_and_fs.setdefault((path, final_state), []).append(signature)

    legacy_populations: dict[str, int] = {}
    for (final_state, _combination), entries in legacy_totals_by_channel.items():
        legacy_populations[final_state] = max(
            legacy_populations.get(final_state, 0), entries
        )
    populations = dict(explicit_populations)
    for final_state, count in legacy_populations.items():
        populations[final_state] = populations.get(final_state, 0) + count

    removed = [fs for fs, count in populations.items() if count < min_events]
    for path in db_paths:
        with sqlite3.connect(path) as conn:
            signatures = []
            for final_state in removed:
                signatures.extend(signatures_by_db_and_fs.get((path, final_state), []))
            conn.executemany(
                f"DELETE FROM {table_name} WHERE signature = ?",
                [(signature,) for signature in signatures],
            )
            conn.commit()
    return sorted(removed)
