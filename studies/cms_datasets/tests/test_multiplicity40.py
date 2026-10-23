#!/usr/bin/env python
"""
Tests of the build-time max-4-objects multiplicity rule
(studies/cms_datasets/common/multiplicity.py; upstream #40, 5fbf1ef).

  1. Label grid: every label with e, m, b in 0..4, e + m + b <= 4 and
     j in 0..12 (455 labels). cap_label equals upstream's
     limit_particles_in_fs(label, 4), and both equal the rule as written:
     jets -> min(j, 4 - (e + m + b)), e/m/b unchanged, at most 4 objects.
     Plus Maryna's examples.
  2. Combination filtering: the 186 driver combinations are all named; on
     every grid label, combination_allowed(capped, im) equals upstream's
     is_finalstate_contain_combination AND "every rank in the name is below
     that type's count in the capped label"; an unknown name is an error.
  3. regroup_shard on SYNTHETIC shards, data-style (masses only) and
     MC-style (masses + _mcw + _mcraw_acc): exact labels 3j/4j/5j (one muon)
     merge into 0e_1m_3j_0b; a combination using jet rank 3 is dropped with
     its siblings; masses and siblings are concatenated in the same order
     (3j, 4j, 5j); final_state_counts are summed (events conserved);
     payloads are unchanged; a coverage-capped signature that would merge
     is refused, one that keeps its label is accepted.
  4. Optional, with --real-shard <shard.sqlite> (repeatable): on a COPY of a
     real per-file shard, events are conserved, every merged combination
     holds the merged label's event count (inclusive shards), siblings stay
     aligned, and the entries kept equal the entries of the allowed
     combinations before.

No network, no cluster. Exit code 0 only if every check passes.

Run:  PYTHONPATH=. python studies/cms_datasets/tests/test_multiplicity40.py [--real-shard PATH ...]
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

from services.calculations import physics_calcs  # noqa: E402
from services.storage.sqlite_shards import SqliteArrayShardWriter, iter_arrays_for_signature  # noqa: E402
from studies.cms_datasets.common.multiplicity import (  # noqa: E402
    COMBINATION_BY_IM, ROW_PATTERN, cap_label, combination_allowed, label_counts,
    regroup_shard,
)

RESULTS: list[tuple[str, bool, str]] = []
RANK_PATTERN = re.compile(r"([a-z])(\d+)")


def check(name: str, ok: bool, detail: str = "") -> None:
    RESULTS.append((name, bool(ok), detail))
    print(f"[{'PASS' if ok else 'FAIL'}] {name} {detail}")


def grid_labels() -> list:
    return [f"{e}e_{m}m_{j}j_{b}b"
            for e in range(5) for m in range(5) for b in range(5) if e + m + b <= 4
            for j in range(13)]


def test_label_grid() -> None:
    labels = grid_labels()
    bad_upstream, bad_rule = [], []
    for lab in labels:
        got = cap_label(lab)
        if got != physics_calcs.limit_particles_in_fs(lab, 4):
            bad_upstream.append(lab)
        c = label_counts(lab)
        nonjet = c["e"] + c["m"] + c["b"]
        want = f"{c['e']}e_{c['m']}m_{min(c['j'], 4 - nonjet)}j_{c['b']}b"
        if got != want or sum(label_counts(got).values()) > 4:
            bad_rule.append((lab, got, want))
    check("grid: 455 labels", len(labels) == 455, str(len(labels)))
    check("grid: cap_label == upstream limit_particles_in_fs(label, 4)", not bad_upstream,
          str(bad_upstream[:5]))
    check("grid: == the rule as written, <= 4 objects", not bad_rule, str(bad_rule[:5]))
    for lab, want in [("0e_1m_5j_0b", "0e_1m_3j_0b"), ("0e_1m_100j_0b", "0e_1m_3j_0b"),
                      ("2e_0m_5j_1b", "2e_0m_1j_1b"), ("2e_0m_3j_2b", "2e_0m_0j_2b"),
                      ("1e_1m_2j_0b", "1e_1m_2j_0b"), ("0e_0m_7j_0b", "0e_0m_4j_0b")]:
        check(f"example {lab}", cap_label(lab) == want, cap_label(lab))


def test_combinations() -> None:
    check("186 driver combinations named", len(COMBINATION_BY_IM) == 186,
          str(len(COMBINATION_BY_IM)))
    check("names are letter+rank", all(re.fullmatch(r"([embj]\d)+", im) for im in COMBINATION_BY_IM))
    n_pairs, bad_up, bad_rank, n_allowed = 0, [], [], 0
    for lab in grid_labels():
        capped = cap_label(lab)
        counts = label_counts(capped)
        for im, combo in COMBINATION_BY_IM.items():
            n_pairs += 1
            got = combination_allowed(capped, im)
            n_allowed += got
            if got != physics_calcs.is_finalstate_contain_combination(capped, combo):
                bad_up.append((capped, im))
            by_rank = all(int(r) < counts.get(letter, 0) for letter, r in RANK_PATTERN.findall(im))
            if got != by_rank:
                bad_rank.append((capped, im))
    check("pairs == upstream is_finalstate_contain_combination", not bad_up,
          f"{n_pairs} pairs, {n_allowed} allowed; {bad_up[:5]}")
    check("pairs == every rank below the capped count", not bad_rank, str(bad_rank[:5]))
    check("m0j0j1j2 in 0e_1m_3j_0b", combination_allowed("0e_1m_3j_0b", "m0j0j1j2"))
    check("j0j1j2j3 not in 0e_1m_3j_0b", not combination_allowed("0e_1m_3j_0b", "j0j1j2j3"))
    check("e1b0 in 2e_0m_1j_1b", combination_allowed("2e_0m_1j_1b", "e1b0"))
    check("e0j1 not in 2e_0m_1j_1b", not combination_allowed("2e_0m_1j_1b", "e0j1"))
    try:
        combination_allowed("0e_1m_3j_0b", "m0m1m2m3m4")
        check("unknown combination is an error", False)
    except KeyError:
        check("unknown combination is an error", True)


def _write(writer, sig, masses, w, mc):
    writer.append_array(sig, np.asarray(masses, dtype=np.float32))
    if mc:
        writer.append_array(sig + "_mcw", np.asarray(w, dtype=np.float64))
        writer.append_array(sig + "_mcraw_acc", np.ones(len(masses), dtype=np.uint8))


def test_synthetic_shard(tmp: pathlib.Path, mc: bool) -> None:
    kind = "mc" if mc else "data"
    path = tmp / f"shard_{kind}.sqlite"
    w = SqliteArrayShardWriter(str(path))
    pre = "MC_record67801_file0" if mc else "DoubleMuon_record30522_file0"
    data = {"0e_1m_3j_0b": 2, "0e_1m_4j_0b": 3, "0e_1m_5j_0b": 4, "0e_2m_0j_0b": 5}
    for i, (lab, n) in enumerate(sorted(data.items(), reverse=True)):  # written 5j first
        w.record_final_state_count(lab, n)
        if lab == "0e_2m_0j_0b":
            _write(w, f"{pre}_FS_{lab}_IM_m0m1", [91.0] * n, [0.5] * n, mc)
            continue
        _write(w, f"{pre}_FS_{lab}_IM_m0j0", [100 * i + k for k in range(n)],
               [float(i)] * n, mc)
        if lab != "0e_1m_3j_0b":
            _write(w, f"{pre}_FS_{lab}_IM_j0j1j2j3", [5.0] * n, [1.0] * n, mc)
    w.close()
    conn = sqlite3.connect(path)
    payloads_before = sorted(p for (p,) in conn.execute("SELECT payload FROM array_chunks"))
    conn.close()
    stats = regroup_shard(str(path))
    target = f"{pre}_FS_0e_1m_3j_0b_IM_m0j0"
    m = np.concatenate(list(iter_arrays_for_signature(str(path), target)))
    check(f"{kind}: merged masses, 3j then 4j then 5j",
          m.tolist() == [300, 301, 200, 201, 202, 100, 101, 102, 103], str(m.tolist()))
    if mc:
        ww = np.concatenate(list(iter_arrays_for_signature(str(path), target + "_mcw")))
        check(f"{kind}: weights in the same order", ww.tolist() == [3, 3, 2, 2, 2, 1, 1, 1, 1],
              str(ww.tolist()))
    conn = sqlite3.connect(path)
    sigs = {s for (s,) in conn.execute("SELECT DISTINCT signature FROM array_chunks")}
    counts = dict(conn.execute("SELECT final_state, n_events FROM final_state_counts"))
    payloads_after = [p for (p,) in conn.execute("SELECT payload FROM array_chunks")]
    conn.close()
    check(f"{kind}: rank-3 combination dropped with siblings",
          not any("j0j1j2j3" in s for s in sigs), str(sorted(sigs)))
    check(f"{kind}: counts summed, events conserved",
          counts == {"0e_1m_3j_0b": 9, "0e_2m_0j_0b": 5}
          and sum(counts.values()) == sum(data.values()), str(counts))
    check(f"{kind}: unchanged label untouched",
          f"{pre}_FS_0e_2m_0j_0b_IM_m0m1" in sigs)
    n_fam = 3 if mc else 1
    check(f"{kind}: dropped rows", stats["n_rows_dropped_combination_not_in_capped_label"]
          == 2 * n_fam and stats["n_mass_entries_dropped"] == 7, str(stats))
    dropped = 2 * n_fam
    check(f"{kind}: payload bytes unchanged",
          len(payloads_after) == len(payloads_before) - dropped
          and all(p in payloads_before for p in payloads_after))

    path2 = tmp / f"capped_{kind}.sqlite"
    w = SqliteArrayShardWriter(str(path2))
    w.record_final_state_count("0e_1m_5j_0b", 1)
    _write(w, f"{pre}_FS_0e_1m_5j_0b_IM_m0j0", [1.0], [1.0], mc)
    w.set_metadata(f"CAPPED::{pre}_FS_0e_1m_5j_0b_IM_m0j0", "true_size=2")
    w.close()
    try:
        regroup_shard(str(path2))
        check(f"{kind}: capped merge refused", False)
    except SystemExit as e:
        check(f"{kind}: capped merge refused", "STOP" in str(e))
    path3 = tmp / f"capped_ok_{kind}.sqlite"
    w = SqliteArrayShardWriter(str(path3))
    w.record_final_state_count("0e_2m_0j_0b", 1)
    _write(w, f"{pre}_FS_0e_2m_0j_0b_IM_m0m1", [1.0], [1.0], mc)
    w.set_metadata(f"CAPPED::{pre}_FS_0e_2m_0j_0b_IM_m0m1", "true_size=2")
    w.close()
    regroup_shard(str(path3))
    check(f"{kind}: capped signature that keeps its label accepted", True)


def test_real_shard(shard: pathlib.Path, tmp: pathlib.Path, i: int) -> None:
    copy = tmp / f"real_{i}.sqlite"
    shutil.copy2(shard, copy)
    inclusive = "inclusive" in shard.name
    conn = sqlite3.connect(copy)
    before = defaultdict(int)
    for sig, n in conn.execute("SELECT signature, SUM(n_entries) FROM array_chunks GROUP BY signature"):
        m = ROW_PATTERN.match(sig)
        if m.group("suffix") is None and combination_allowed(cap_label(m.group("fs")), m.group("im")):
            before[(cap_label(m.group("fs")), m.group("im"))] += int(n)
    n_events_before = sum(n for (n,) in conn.execute("SELECT n_events FROM final_state_counts"))
    conn.close()
    stats = regroup_shard(str(copy))
    conn = sqlite3.connect(copy)
    counts = dict(conn.execute("SELECT final_state, n_events FROM final_state_counts"))
    after = defaultdict(dict)
    for sig, n in conn.execute("SELECT signature, SUM(n_entries) FROM array_chunks GROUP BY signature"):
        m = ROW_PATTERN.match(sig)
        after[(m.group("fs"), m.group("im"))][m.group("suffix")] = int(n)
    conn.close()
    tag = f"real {shard.parent.name}/{shard.name}"
    check(f"{tag}: events conserved", sum(counts.values()) == n_events_before,
          f"{n_events_before} -> {sum(counts.values())}")
    if inclusive:
        bad_count = [k for k, v in after.items() if v[None] != counts[k[0]]]
        check(f"{tag}: every merged combination holds every merged event", not bad_count,
              f"{len(after)} signatures, {len(bad_count)} bad")
    check(f"{tag}: siblings aligned", all(len(set(v.values())) == 1 for v in after.values()))
    check(f"{tag}: kept entries == allowed entries before",
          {k: v[None] for k, v in after.items()} == dict(before),
          f"{len(counts)} final states from {len(stats['label_map'])} exact labels, "
          f"{stats['n_rows_dropped_combination_not_in_capped_label']} rows dropped")


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--real-shard", type=pathlib.Path, action="append", default=[])
    args = p.parse_args()
    test_label_grid()
    test_combinations()
    with tempfile.TemporaryDirectory() as d:
        test_synthetic_shard(pathlib.Path(d), mc=False)
        test_synthetic_shard(pathlib.Path(d), mc=True)
        for i, shard in enumerate(args.real_shard):
            test_real_shard(shard, pathlib.Path(d), i)
    n_fail = sum(not ok for _n, ok, _d in RESULTS)
    print(f"\n{len(RESULTS) - n_fail}/{len(RESULTS)} checks passed")
    return 1 if n_fail else 0


if __name__ == "__main__":
    sys.exit(main())
