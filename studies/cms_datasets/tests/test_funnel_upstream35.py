"""
Self-check for the upstream #35 compatibility of the CMS per-file funnel.

Upstream #35 (7f2da5d) changed
services.pipelines.im_pipeline._calculate_combination_invariant_mass to
return (inv_mass, mc_event_weights, skip_reason) instead of
(inv_mass, skip_reason). run_combination_funnel unpacks the new form and
asserts the middle value is None (CMS never enables #35's weighting).

Covers, with real (not mocked) code:
  1. the funnel runs end to end on a fixed synthetic obj_record (e, mu,
     light jets, b-jets; no photons or taus, like CMS; 200 events) with the
     real 186 combinations;
  2. everything it writes -- every signature, every value, the per-final-
     state counts of both shards, and the returned stats -- hashes to
     EXPECTED_DIGEST. That digest was produced by the PRE-#35 code (fork
     master 45a7e06, 2-value unpacking) running this same script, so a
     match means the adapted funnel's output is byte-identical to before.

Run directly:
    python studies/cms_datasets/tests/test_funnel_upstream35.py
"""
from __future__ import annotations

import hashlib
import json
import logging
import sqlite3
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

import awkward as ak  # noqa: E402
import numpy as np  # noqa: E402

from services.calculations.combinatorics import get_all_combinations  # noqa: E402
from services.storage.sqlite_shards import SqliteArrayShardWriter  # noqa: E402
from studies.cms_datasets.cluster.run_dataset_on_file import (  # noqa: E402
    FIELD_TO_SLICE_BY,
    FINAL_STATE_OBJECTS,
    INCLUDE_SUBLEADING,
    MAX_COUNT_PARTICLE_IN_COMBINATION,
    MAX_PARTICLES_IN_COMBINATION,
    MAX_SUBLEADING_INDEX,
    MAX_TOTAL_PARTICLES_IN_COMBINATION,
    MIN_COUNT_PARTICLE_IN_COMBINATION,
    MIN_PARTICLES_IN_COMBINATION,
    OBJECT_TYPES,
    run_combination_funnel,
)

# Produced by this script on fork master 45a7e06 (pre-#35 upstream code).
EXPECTED_DIGEST = "5c43cbc0fa9bc7109b115af81ac6ef62f04449023976bbebe17a39d272fe4fb0"

FAILURES = []


def check(name: str, condition: bool, detail: str = ""):
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {name}" + (f" -- {detail}" if detail else ""))
    if not condition:
        FAILURES.append(name)


def make_obj_record(n_events: int = 200, seed: int = 20261020) -> ak.Array:
    """Fixed synthetic events, pT-ordered; few objects so the test stays fast."""
    rng = np.random.default_rng(seed)
    max_by_obj = {"Electrons": 2, "Muons": 2, "Jets": 2, "Photons": 0, "Taus": 0, "BJets": 1}
    fields = {}
    for obj, _letter in FINAL_STATE_OBJECTS:
        counts = rng.integers(0, max_by_obj[obj] + 1, n_events)
        total = int(counts.sum())
        pt = np.sort(rng.uniform(20.0, 300.0, total))[::-1].copy()
        rec = ak.zip({
            "pt": pt,
            "eta": rng.uniform(-2.4, 2.4, total),
            "phi": rng.uniform(-np.pi, np.pi, total),
            "mass": np.zeros(total),
        })
        jagged = ak.unflatten(rec, counts)
        fields[obj] = jagged[ak.argsort(jagged.pt, ascending=False)]
    return ak.zip(fields, depth_limit=1)


def dump_shard(path: str) -> list:
    con = sqlite3.connect(path)
    try:
        tables = [r[0] for r in con.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
        out = []
        for t in tables:
            rows = sorted(con.execute(f"SELECT * FROM {t}").fetchall(), key=repr)
            out.append((t, rows))
        return out
    finally:
        con.close()


def run() -> str:
    obj_record = make_obj_record()
    is_exclusive = np.random.default_rng(7).random(len(obj_record)) < 0.5
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
    check("186 combinations", len(all_combinations) == 186, str(len(all_combinations)))
    with tempfile.TemporaryDirectory() as tmp:
        incl, excl = f"{tmp}/incl.sqlite", f"{tmp}/excl.sqlite"
        w_incl, w_excl = SqliteArrayShardWriter(incl), SqliteArrayShardWriter(excl)
        stats = run_combination_funnel(
            obj_record, is_exclusive, "testjob", all_combinations,
            {"field_to_slice_by": FIELD_TO_SLICE_BY}, logging.getLogger("t"), w_incl, w_excl)
        for w in (w_incl, w_excl):
            w.commit()
            w.close()
        content = {"stats": stats, "incl": dump_shard(incl), "excl": dump_shard(excl)}
    check("funnel wrote values", stats.get("n_values_written_incl", 0) > 0,
          f"n_values_written_incl={stats.get('n_values_written_incl')}, n_fs_groups={stats.get('n_fs_groups')}")
    return hashlib.sha256(json.dumps(content, sort_keys=True, default=repr).encode()).hexdigest()


def main() -> int:
    digest = run()
    print(f"digest {digest}")
    check("output identical to the pre-#35 code", digest == EXPECTED_DIGEST,
          f"expected {EXPECTED_DIGEST}")
    print("ALL CHECKS PASSED" if not FAILURES else f"{len(FAILURES)} FAILED: {FAILURES}")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    raise SystemExit(main())
