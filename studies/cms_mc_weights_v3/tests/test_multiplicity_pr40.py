#!/usr/bin/env python
"""
Tests of the optional PR #40 multiplicity rule (deliver/multiplicity_pr40.py).

  1. Maryna's examples (20 Oct 2026): 1mu + 5j -> 0e_1m_3j_0b,
     1mu + 100j -> 0e_1m_3j_0b, 2e + 1b + 5j -> 2e_0m_1j_1b.
  2. combination_allowed: highest jet rank < capped jet count.
  3. apply_pr40_to_shard on a SYNTHETIC shard: exact labels 3j/4j/5j (one
     muon) merge into 0e_1m_3j_0b; a combination using jet rank 3 is dropped
     with its siblings; masses and every sibling are concatenated in the
     same order (3j, 4j, 5j); final_state_counts are summed; payloads are
     unchanged; a coverage-capped signature that would merge is refused.
  4. Optional, with --real-shard <rare4_inclusive.sqlite>: on a COPY of a
     real per-file shard, every merged mass signature holds exactly the
     merged label's event count, every sibling family is aligned, and the
     entries kept equal the entries of the allowed combinations before.

No network, no cluster. Exit code 0 only if every check passes.

Run:  python studies/cms_mc_weights_v3/tests/test_multiplicity_pr40.py [--real-shard PATH]
"""
from __future__ import annotations

import argparse
import pathlib
import re
import shutil
import sqlite3
import sys
import tempfile
from collections import defaultdict

import numpy as np

REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

from services.storage.sqlite_shards import SqliteArrayShardWriter, iter_arrays_for_signature  # noqa: E402
from studies.cms_mc_weights_v3.deliver.multiplicity_pr40 import (  # noqa: E402
    ROW_PATTERN, apply_pr40_to_shard, cap_label, combination_allowed,
)

RESULTS: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    RESULTS.append((name, bool(ok), detail))
    print(f"[{'PASS' if ok else 'FAIL'}] {name} {detail}")


def test_examples() -> None:
    check("1mu+5j", cap_label("0e_1m_5j_0b") == "0e_1m_3j_0b", cap_label("0e_1m_5j_0b"))
    check("1mu+100j", cap_label("0e_1m_100j_0b") == "0e_1m_3j_0b", cap_label("0e_1m_100j_0b"))
    check("2e+1b+5j", cap_label("2e_0m_5j_1b") == "2e_0m_1j_1b", cap_label("2e_0m_5j_1b"))
    check("no jet slot", cap_label("2e_0m_3j_2b") == "2e_0m_0j_2b", cap_label("2e_0m_3j_2b"))
    check("unchanged", cap_label("1e_1m_2j_0b") == "1e_1m_2j_0b")


def test_combination_allowed() -> None:
    check("m0j0j1j2 in 1m3j", combination_allowed("0e_1m_3j_0b", "m0j0j1j2"))
    check("j1j2j3 not in 1m3j", not combination_allowed("0e_1m_3j_0b", "j1j2j3"))
    check("e1b0 in 2e1j1b", combination_allowed("2e_0m_1j_1b", "e1b0"))
    check("e0j1 not in 2e1j1b", not combination_allowed("2e_0m_1j_1b", "e0j1"))


def _write(writer, sig, masses, w):
    writer.append_array(sig, np.asarray(masses, dtype=np.float32))
    writer.append_array(sig + "_mcw", np.asarray(w, dtype=np.float64))
    writer.append_array(sig + "_mcraw_acc", np.ones(len(masses), dtype=np.uint8))


def test_synthetic_shard(tmp: pathlib.Path) -> None:
    path = tmp / "shard.sqlite"
    w = SqliteArrayShardWriter(str(path))
    pre = "MC_record67801_file0"
    data = {"0e_1m_3j_0b": 2, "0e_1m_4j_0b": 3, "0e_1m_5j_0b": 4}
    for i, (lab, n) in enumerate(sorted(data.items(), reverse=True)):  # written 5j first
        w.record_final_state_count(lab, n)
        _write(w, f"{pre}_FS_{lab}_IM_m0j0", [100 * (i + 1) + k for k in range(n)],
               [float(i + 1)] * n)
        if lab != "0e_1m_3j_0b":
            _write(w, f"{pre}_FS_{lab}_IM_j1j2j3", [5.0] * n, [1.0] * n)
    w.close()
    stats = apply_pr40_to_shard(str(path))
    target = f"{pre}_FS_0e_1m_3j_0b_IM_m0j0"
    m = np.concatenate(list(iter_arrays_for_signature(str(path), target)))
    ww = np.concatenate(list(iter_arrays_for_signature(str(path), target + "_mcw")))
    check("merged masses, 3j then 4j then 5j",
          m.tolist() == [300, 301, 200, 201, 202, 100, 101, 102, 103], str(m.tolist()))
    check("weights in the same order", ww.tolist() == [3, 3, 2, 2, 2, 1, 1, 1, 1], str(ww.tolist()))
    conn = sqlite3.connect(path)
    sigs = {s for (s,) in conn.execute("SELECT DISTINCT signature FROM array_chunks")}
    counts = dict(conn.execute("SELECT final_state, n_events FROM final_state_counts"))
    conn.close()
    check("rank-3 combination dropped with siblings", not any("j1j2j3" in s for s in sigs), str(sorted(sigs)))
    check("counts summed", counts == {"0e_1m_3j_0b": 9}, str(counts))
    check("dropped rows", stats["n_rows_dropped_combination_not_in_capped_label"] == 6
          and stats["n_mass_entries_dropped"] == 7, str(stats))

    path2 = tmp / "capped.sqlite"
    w = SqliteArrayShardWriter(str(path2))
    w.record_final_state_count("0e_1m_5j_0b", 1)
    _write(w, f"{pre}_FS_0e_1m_5j_0b_IM_m0j0", [1.0], [1.0])
    w.set_metadata(f"CAPPED::{pre}_FS_0e_1m_5j_0b_IM_m0j0", "true_size=2 kept=1 weight_scale=2.0")
    w.close()
    try:
        apply_pr40_to_shard(str(path2))
        check("capped merge refused", False)
    except SystemExit as e:
        check("capped merge refused", "STOP" in str(e))


def test_real_shard(shard: pathlib.Path, tmp: pathlib.Path) -> None:
    copy = tmp / "real.sqlite"
    shutil.copy2(shard, copy)
    conn = sqlite3.connect(copy)
    before = defaultdict(int)
    for sig, n in conn.execute("SELECT signature, SUM(n_entries) FROM array_chunks GROUP BY signature"):
        m = ROW_PATTERN.match(sig)
        if m.group("suffix") is None and combination_allowed(cap_label(m.group("fs")), m.group("im")):
            before[(cap_label(m.group("fs")), m.group("im"))] += int(n)
    n_events_before = sum(n for (n,) in conn.execute("SELECT n_events FROM final_state_counts"))
    conn.close()
    stats = apply_pr40_to_shard(str(copy))
    conn = sqlite3.connect(copy)
    counts = dict(conn.execute("SELECT final_state, n_events FROM final_state_counts"))
    after = defaultdict(dict)
    for sig, n in conn.execute("SELECT signature, SUM(n_entries) FROM array_chunks GROUP BY signature"):
        m = ROW_PATTERN.match(sig)
        after[(m.group("fs"), m.group("im"))][m.group("suffix")] = int(n)
    conn.close()
    bad_count = [k for k, v in after.items() if v[None] != counts[k[0]]]
    bad_sib = [k for k, v in after.items() if len(set(v.values())) != 1]
    check("real: events conserved", sum(counts.values()) == n_events_before,
          f"{n_events_before} -> {sum(counts.values())}")
    check("real: every merged combination holds every merged event", not bad_count,
          f"{len(after)} signatures, {len(bad_count)} bad")
    check("real: siblings aligned", not bad_sib)
    check("real: kept entries == allowed entries before",
          {k: v[None] for k, v in after.items()} == dict(before),
          f"{len(counts)} final states from {len(stats['label_map'])} exact labels, "
          f"{stats['n_rows_dropped_combination_not_in_capped_label']} rows dropped")


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--real-shard", type=pathlib.Path)
    args = p.parse_args()
    test_examples()
    test_combination_allowed()
    with tempfile.TemporaryDirectory() as d:
        test_synthetic_shard(pathlib.Path(d))
        if args.real_shard:
            test_real_shard(args.real_shard, pathlib.Path(d))
    n_fail = sum(not ok for _n, ok, _d in RESULTS)
    print(f"\n{len(RESULTS) - n_fail}/{len(RESULTS)} checks passed")
    return 1 if n_fail else 0


if __name__ == "__main__":
    sys.exit(main())
