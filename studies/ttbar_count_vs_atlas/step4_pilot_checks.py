#!/usr/bin/env python
"""
Step 4 (ttbar_count_vs_atlas): pilot consistency checks on the
--population notrigger output for a small number of TTTo2L2Nu files.

Checks, per file and pooled:

  (a) variant (a) rare4, RESTRICTED to final states with <= 3 light jets,
      equals variant (b) pr31 restricted the same way -- row for row.
      Three light jets or fewer is exactly the region where the two
      variants are supposed to be the same object: at 4 light jets our
      "4j" label already pools 4-or-more while PR #31's means exactly 4,
      so 4j is deliberately excluded from this comparison.

  (b) variant (b) pr31 has no final state with more than 4 of any type.
      Proved from the shard itself, not from the label text (a label is
      display-capped at 4 and so could never show a 5). The writer
      INSERTs one final_state_counts row per RAW final-state group, so
      the number of ROWS carrying a given label is the number of raw
      groups that collapsed onto it: for pr31 that must be exactly one
      for every label in every shard, while rare4 is expected to show
      more than one for labels containing 4j (5j, 6j, ... all collapse
      there). Finding exactly one row per label everywhere IS the
      statement that nothing was capped, i.e. no type exceeded 4.

  (c) the per-variant event counters are reported and their arithmetic
      re-checked externally:
      events read -> passing the >= 2-object gate -> rejected for
      e+mu+b > 4 -> dropped for >= 5 light jets -> into combinations.

Usage:
    python step4_pilot_checks.py --jobs-dir <pilot output base> --out <report.json>
"""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

import numpy as np  # noqa: E402

from services.storage.sqlite_shards import _deserialize_array  # noqa: E402

SIG_FS = re.compile(r"_FS_([0-9a-z_]+)_IM_([0-9a-z]+)$")
FS_TOKEN = re.compile(r"(\d+)([emjgtb])")


def fs_counts(fs_str: str) -> dict:
    return {letter: int(count) for count, letter in FS_TOKEN.findall(fs_str)}


def read_arrays_ordered(path: str) -> dict:
    con = sqlite3.connect(f"file:{path}?mode=ro&immutable=1", uri=True)
    cur = con.cursor()
    cur.execute("SELECT signature, payload FROM array_chunks ORDER BY id")
    out = defaultdict(list)
    for sig, payload in cur.fetchall():
        if sig.startswith("CAPPED::"):
            continue
        out[sig].append(_deserialize_array(payload))
    con.close()
    return {k: np.concatenate(v) for k, v in out.items()}


def read_fs_rows(path: str):
    """Every final_state_counts ROW (not grouped) -- the row multiplicity
    is what check (b) needs."""
    con = sqlite3.connect(f"file:{path}?mode=ro&immutable=1", uri=True)
    rows = con.execute("SELECT final_state, n_events FROM final_state_counts").fetchall()
    con.close()
    return [(str(fs), int(n)) for fs, n in rows]


def check_a(rare4_path: str, pr31_path: str) -> dict:
    a = read_arrays_ordered(rare4_path)
    b = read_arrays_ordered(pr31_path)

    def restrict(d):
        out = {}
        for sig, arr in d.items():
            m = SIG_FS.search(sig)
            if not m:
                continue
            if fs_counts(m.group(1)).get("j", 0) <= 3:
                out[sig] = arr
        return out

    ra, rb = restrict(a), restrict(b)
    only_a = sorted(set(ra) - set(rb))
    only_b = sorted(set(rb) - set(ra))
    mismatched = []
    for sig in sorted(set(ra) & set(rb)):
        if ra[sig].shape != rb[sig].shape or not np.array_equal(ra[sig], rb[sig]):
            mismatched.append({"signature": sig,
                               "n_rare4": int(ra[sig].size), "n_pr31": int(rb[sig].size)})
    return {
        "check": "(a) rare4 == pr31 on final states with <= 3 light jets, row for row",
        "pass": not only_a and not only_b and not mismatched,
        "n_signatures_compared": len(set(ra) & set(rb)),
        "n_signatures_rare4_le3j": len(ra),
        "n_signatures_pr31_le3j": len(rb),
        "n_only_rare4": len(only_a), "n_only_pr31": len(only_b),
        "only_rare4_sample": only_a[:10], "only_pr31_sample": only_b[:10],
        "n_mismatched": len(mismatched), "mismatched_sample": mismatched[:10],
        "n_signatures_rare4_total": len(a), "n_signatures_pr31_total": len(b),
        "pr31_signatures_are_subset_of_rare4": set(b) <= set(a),
    }


def check_b(pr31_path: str, rare4_path: str) -> dict:
    pr31_rows = read_fs_rows(pr31_path)
    rare4_rows = read_fs_rows(rare4_path)

    def rows_per_label(rows):
        d = defaultdict(int)
        for fs, _n in rows:
            d[fs] += 1
        return d

    pr31_mult = rows_per_label(pr31_rows)
    rare4_mult = rows_per_label(rare4_rows)

    pr31_collapsed = {fs: n for fs, n in pr31_mult.items() if n > 1}
    rare4_collapsed = {fs: n for fs, n in rare4_mult.items() if n > 1}
    # Every label digit must also be <= 4 (a weaker, text-level check that
    # would catch a label-building change).
    bad_labels = [fs for fs in pr31_mult
                  if any(v > 4 for v in fs_counts(fs).values())]
    # The labels rare4 DID collapse must all be 4j ones -- that is the
    # expected and only source of collapsing under the rare4 rule.
    rare4_collapsed_not_4j = [fs for fs in rare4_collapsed
                              if fs_counts(fs).get("j", 0) != 4]
    return {
        "check": "(b) pr31 has no final state with > 4 of any type",
        "pass": not pr31_collapsed and not bad_labels and not rare4_collapsed_not_4j,
        "n_distinct_labels_pr31": len(pr31_mult),
        "n_labels_pr31_with_more_than_one_raw_group": len(pr31_collapsed),
        "pr31_collapsed_sample": dict(sorted(pr31_collapsed.items())[:10]),
        "n_labels_with_a_digit_above_4": len(bad_labels),
        "n_distinct_labels_rare4": len(rare4_mult),
        "n_labels_rare4_with_more_than_one_raw_group": len(rare4_collapsed),
        "rare4_collapsed_sample": dict(sorted(rare4_collapsed.items())[:10]),
        "n_rare4_collapsed_labels_that_are_not_4j": len(rare4_collapsed_not_4j),
        "note": "a label carrying more than one final_state_counts row means two or more "
                "RAW final states collapsed onto it, i.e. a per-type count above 4 was "
                "display-capped. pr31 must have none; rare4 is expected to have them, "
                "and only for 4j labels.",
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--jobs-dir", required=True)
    p.add_argument("--out", required=True)
    args = p.parse_args()

    job_dirs = sorted(Path(args.jobs_dir).glob("job_*"),
                      key=lambda d: int(d.name.split("_")[1]))
    if not job_dirs:
        raise SystemExit(f"no job_* directories under {args.jobs_dir}")

    per_file = []
    overall_pass = True
    for d in job_dirs:
        meta = json.loads((d / "job_metadata.json").read_text())
        nt = meta["notrigger_diagnostics"]

        counters = {}
        arithmetic_ok = True
        for name, v in nt["variants"].items():
            expected = (v["n_events_passing_gate"]
                        - v["n_rejected_e_mu_b_gt4"]
                        - v["n_dropped_ge5_light_jets"])
            ok = expected == v["n_events_into_combinations"]
            arithmetic_ok = arithmetic_ok and ok
            counters[name] = {
                "n_events_read": v["n_events_read_this_file"],
                "n_events_passing_gate": v["n_events_passing_gate"],
                "n_rejected_e_mu_b_gt4": v["n_rejected_e_mu_b_gt4"],
                "n_dropped_ge5_light_jets": v["n_dropped_ge5_light_jets"],
                "n_events_into_combinations": v["n_events_into_combinations"],
                "arithmetic_consistent": ok,
                "n_fs_groups": v["n_fs_groups"],
                "n_signature_writes_inclusive": v["n_signature_writes_inclusive"],
            }

        ra = str(d / "dataset_shard_notrigger_rare4_inclusive.sqlite")
        rb = str(d / "dataset_shard_notrigger_pr31_inclusive.sqlite")
        rc = str(d / "dataset_shard_notrigger_pr31_noOR_inclusive.sqlite")
        res_a = check_a(ra, rb)
        res_b = check_b(rb, ra)
        res_c = check_b(rc, ra)
        res_c["check"] = "(b, applied to pr31_noOR too) no final state with > 4 of any type"
        # rare4's own collapsing is irrelevant for the noOR shard; only its
        # own two pr31-side conditions matter here.
        res_c["pass"] = (res_c["n_labels_pr31_with_more_than_one_raw_group"] == 0
                         and res_c["n_labels_with_a_digit_above_4"] == 0)

        this_pass = res_a["pass"] and res_b["pass"] and res_c["pass"] and arithmetic_ok
        overall_pass = overall_pass and this_pass

        print(f"[{d.name}] counters arithmetic: {'PASS' if arithmetic_ok else 'FAIL'}")
        for name, c in counters.items():
            print(f"  {name:10s} read={c['n_events_read']} gate={c['n_events_passing_gate']} "
                  f"rejected_e_mu_b_gt4={c['n_rejected_e_mu_b_gt4']} "
                  f"dropped_ge5j={c['n_dropped_ge5_light_jets']} "
                  f"into_combinations={c['n_events_into_combinations']} "
                  f"signatures={c['n_signature_writes_inclusive']}")
        print(f"[{d.name}] (a) rare4 == pr31 on <=3 light jets: "
              f"{'PASS' if res_a['pass'] else 'FAIL'} "
              f"({res_a['n_signatures_compared']} signatures compared, "
              f"{res_a['n_mismatched']} mismatched, "
              f"{res_a['n_only_rare4']}+{res_a['n_only_pr31']} unmatched)")
        print(f"[{d.name}] (b) pr31 no type > 4: {'PASS' if res_b['pass'] else 'FAIL'} "
              f"({res_b['n_distinct_labels_pr31']} labels, "
              f"{res_b['n_labels_pr31_with_more_than_one_raw_group']} collapsed; "
              f"rare4 collapsed {res_b['n_labels_rare4_with_more_than_one_raw_group']}, "
              f"all 4j: {res_b['n_rare4_collapsed_labels_that_are_not_4j'] == 0})")
        print(f"[{d.name}] (b) pr31_noOR no type > 4: {'PASS' if res_c['pass'] else 'FAIL'}")
        print()

        per_file.append({
            "job": d.name, "file_url": meta["file_url"],
            "counters": counters, "counters_arithmetic_pass": arithmetic_ok,
            "check_a": res_a, "check_b_pr31": res_b, "check_b_pr31_noOR": res_c,
            "all_pass": this_pass,
        })

    pooled = defaultdict(lambda: defaultdict(int))
    for f in per_file:
        for name, c in f["counters"].items():
            for k, v in c.items():
                if isinstance(v, int):
                    pooled[name][k] += v

    report = {
        "jobs_dir": args.jobs_dir,
        "n_files": len(job_dirs),
        "overall_pass": overall_pass,
        "pooled_counters": {k: dict(v) for k, v in pooled.items()},
        "per_file": per_file,
    }
    Path(args.out).write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("POOLED over", len(job_dirs), "file(s):")
    for name, c in pooled.items():
        print(f"  {name:10s} read={c['n_events_read']} gate={c['n_events_passing_gate']} "
              f"rejected_e_mu_b_gt4={c['n_rejected_e_mu_b_gt4']} "
              f"dropped_ge5j={c['n_dropped_ge5_light_jets']} "
              f"into_combinations={c['n_events_into_combinations']}")
    print(f"\nOVERALL: {'PASS' if overall_pass else 'FAIL'}")
    print(f"wrote {args.out}")
    if not overall_pass:
        sys.exit(1)


if __name__ == "__main__":
    main()
