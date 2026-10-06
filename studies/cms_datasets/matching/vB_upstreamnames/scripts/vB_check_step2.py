"""
upstream-names task, Step 2: pilot validation on the 4 pilot files.

Compares the NEW pilot run (pinned commit 06922a9, upstream name format)
against the 5 Oct exact-labels pilot run, which is opened strictly
READ-ONLY (`mode=ro&immutable=1`; nothing under output/ is ever modified).

Checks, all of which must pass before the full delivery is rebuilt:

  (a) Selection and per-file counts unchanged -- every per-stage count and
      every Version B reject diagnostic identical, file by file. Renaming a
      final state must not move a single event.
  (b) Signature correspondence -- every NEW signature corresponds 1:1 to an
      OLD signature through convert_legacy_fs_label, with no new signature
      unmatched, no old signature unmatched, and no two old signatures
      landing on the same new one.
  (c) Mass arrays byte-identical for every corresponding signature pair.
  (d) Per-final-state event counts identical after conversion, for the
      delivered rare4 version and for the normal version.

Run from an ANALYSIS checkout (never the pinned production one):
    python studies/cms_datasets/matching/vB_upstreamnames/scripts/vB_check_step2.py
"""
from __future__ import annotations

import json
import sqlite3
import sys
from collections import Counter, defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(REPO_ROOT))

import numpy as np  # noqa: E402

from services.storage.sqlite_shards import _deserialize_array  # noqa: E402
from studies.cms_coverage.cluster.merge_and_count import SIG_PATTERN  # noqa: E402
from studies.cms_datasets.deliver.build_muon_combined_delivery import (  # noqa: E402
    convert_legacy_fs_label,
)

OUT = Path("/storage/agrp/berkom/atlas-utilization/output/cms_datasets")
OLD_BASE = OUT / "vB_exactlabels_pilot"
NEW_BASE = OUT / "vB_upstreamnames_pilot"
PINNED = "06922a9835f188dffbd3cc770ba80c04f78aee59"

RUNS = [
    "DoubleMuon_30522_0_matched",
    "DoubleMuon_30555_0_matched",
    "SingleMuon_30530_0_matched",
    "SingleMuon_30563_0_matched",
]

SHARDS = ("dataset_shard_rare4_inclusive.sqlite",
          "dataset_shard_rare4_exclusive.sqlite",
          "dataset_shard_inclusive.sqlite",
          "dataset_shard_exclusive.sqlite")

FAILURES = []
RESULTS = {}


def check(name, condition, detail=""):
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {name}" + (f" -- {detail}" if detail and not condition else ""))
    if not condition:
        FAILURES.append(name)
    return bool(condition)


def read_ro(path: Path) -> dict:
    """signature -> concatenated values, strictly read-only."""
    con = sqlite3.connect(f"file:{path}?mode=ro&immutable=1", uri=True)
    try:
        cur = con.cursor()
        cur.execute("SELECT signature, payload FROM array_chunks")
        out = defaultdict(list)
        for signature, payload in cur.fetchall():
            if signature.startswith("CAPPED::"):
                continue
            out[signature].extend(_deserialize_array(payload).tolist())
        return dict(out)
    finally:
        con.close()


def meta(base: Path, run: str) -> dict:
    return json.loads((base / run / "job_metadata.json").read_text())


def convert_signature(sig: str) -> str:
    """Apply the legacy final-state conversion to a whole signature."""
    m = SIG_PATTERN.search(sig)
    if m is None:
        raise ValueError(f"unparsable signature {sig!r}")
    fs, im = m.groups()
    prefix = sig[: m.start()]
    return f"{prefix}_FS_{convert_legacy_fs_label(fs)}_IM_{im}"


# ==========================================================================

def check_a():
    print("\n" + "=" * 74)
    print("(a) Selection and per-file counts unchanged")
    print("=" * 74)
    TOP = ("n_read", "n_after_golden_json", "n_after_trigger", "n_after_gate",
           "n_exclusive")
    DIAG = ("n_accepted_events_before_rare4_rule", "n_rejected_gt4_lepton_bjet",
            "n_kept_le4_lepton_bjet", "n_hidden_cases", "rejected_N_distribution")
    rows = []
    for run in RUNS:
        o, n = meta(OLD_BASE, run), meta(NEW_BASE, run)
        check(f"{run}: produced by the pinned commit 06922a9",
              n["git_commit"] == PINNED, f"got {n['git_commit']}")
        bad = [k for k in TOP if o[k] != n[k]]
        bad += [f"rare4.{k}" for k in DIAG
                if o["rare4_diagnostics"][k] != n["rare4_diagnostics"][k]]
        check(f"{run}: all {len(TOP)} per-stage counts and all {len(DIAG)} Version B "
              f"reject diagnostics identical to 5 Oct", not bad, f"differ: {bad}")
        # number of final-state groups may legitimately stay the same; renaming
        # must not merge or split anything.
        check(f"{run}: number of rare4 final-state groups unchanged "
              f"({n['rare4_diagnostics']['n_fs_groups']})",
              o["rare4_diagnostics"]["n_fs_groups"] == n["rare4_diagnostics"]["n_fs_groups"],
              f"old={o['rare4_diagnostics']['n_fs_groups']} "
              f"new={n['rare4_diagnostics']['n_fs_groups']}")
        rows.append({"run": run, "n_read": n["n_read"],
                     "n_after_gate": n["n_after_gate"],
                     "n_exclusive": n["n_exclusive"],
                     "n_fs_groups_rare4": n["rare4_diagnostics"]["n_fs_groups"]})
    RESULTS["check_a"] = rows


def check_bc():
    print("\n" + "=" * 74)
    print("(b) Signature correspondence 1:1, and (c) mass arrays identical")
    print("=" * 74)
    totals = []
    for run in RUNS:
        for shard in SHARDS:
            old = read_ro(OLD_BASE / run / shard)
            new = read_ro(NEW_BASE / run / shard)

            # Old labels must still be the six-field form, new ones must not be.
            old_has_gt = [s for s in old if "_0g_" in s or "_0t_" in s]
            new_has_gt = [s for s in new if "_0g_" in s or "_0t_" in s]
            check(f"{run}/{shard}: the 5 Oct shard really is in the legacy format",
                  len(old_has_gt) == len(old) and len(old) > 0,
                  f"{len(old_has_gt)} of {len(old)} carry 0g/0t")
            check(f"{run}/{shard}: the NEW shard carries no photon/tau field at all",
                  not new_has_gt, f"{len(new_has_gt)} still carry them")

            converted = {}
            collisions = []
            for sig in old:
                c = convert_signature(sig)
                if c in converted:
                    collisions.append((c, converted[c], sig))
                converted[c] = sig
            check(f"{run}/{shard}: no two old signatures convert onto the same new one",
                  not collisions, f"{len(collisions)} collisions: {collisions[:2]}")

            only_new = sorted(set(new) - set(converted))
            only_old = sorted(set(converted) - set(new))
            check(f"{run}/{shard}: every one of the {len(new)} new signatures "
                  f"corresponds 1:1 to a 5 Oct signature",
                  not only_new and not only_old,
                  f"{len(only_new)} unmatched new, {len(only_old)} unmatched old; "
                  f"examples new={only_new[:2]} old={only_old[:2]}")

            diff = []
            for conv_sig, old_sig in converted.items():
                if conv_sig not in new:
                    continue
                if Counter(np.round(old[old_sig], 6)) != Counter(np.round(new[conv_sig], 6)):
                    diff.append(conv_sig)
            check(f"{run}/{shard}: all {len(converted)} corresponding mass arrays "
                  f"are identical", not diff,
                  f"{len(diff)} differ, first: {diff[:2]}")

            totals.append({"run": run, "shard": shard, "n_signatures": len(new),
                           "n_differing_arrays": len(diff)})
    RESULTS["check_bc"] = totals


def check_d():
    print("\n" + "=" * 74)
    print("(d) Per-final-state event counts identical after conversion")
    print("=" * 74)
    rows = []
    for run in RUNS:
        o, n = meta(OLD_BASE, run), meta(NEW_BASE, run)
        sources = [
            ("rare4", lambda md, w: md["rare4_diagnostics"][
                f"final_state_label_event_counts_{w}"]),
            ("normal", lambda md, w: md[f"final_state_label_event_counts_{w}"]),
        ]
        for version, get in sources:
            for which in ("inclusive", "exclusive"):
                old_counts = get(o, which)
                new_counts = get(n, which)
                converted = {}
                for lb, c in old_counts.items():
                    cl = convert_legacy_fs_label(lb)
                    converted[cl] = converted.get(cl, 0) + c
                check(f"{run} [{version}/{which}]: converted 5 Oct label counts equal "
                      f"the new ones exactly ({len(new_counts)} final states)",
                      converted == new_counts,
                      f"only_old={sorted(set(converted)-set(new_counts))[:3]} "
                      f"only_new={sorted(set(new_counts)-set(converted))[:3]}")
                check(f"{run} [{version}/{which}]: total events unchanged",
                      sum(old_counts.values()) == sum(new_counts.values()),
                      f"old={sum(old_counts.values())} new={sum(new_counts.values())}")
                rows.append({"run": run, "version": version, "which": which,
                             "n_final_states": len(new_counts),
                             "total_events": sum(new_counts.values())})
    RESULTS["check_d"] = rows

    # One worked example for the report.
    n = meta(NEW_BASE, RUNS[0])
    labels = sorted(n["rare4_diagnostics"]["final_state_label_event_counts_inclusive"])
    print(f"\n       example new labels from {RUNS[0]}:")
    for lb in labels[:6]:
        print(f"         {lb}")


def main():
    print("=" * 74)
    print("upstream-names task, Step 2: pilot validation")
    print(f"  NEW: {NEW_BASE}")
    print(f"  5 Oct (read-only): {OLD_BASE}")
    print("=" * 74)
    check_a()
    check_bc()
    check_d()

    out = NEW_BASE / "step2_validation.json"
    out.write_text(json.dumps({"failures": FAILURES, "results": RESULTS},
                              indent=2, default=str))
    print(f"\nwrote {out}")

    print("\n" + "=" * 74)
    if FAILURES:
        print(f"{len(FAILURES)} CHECK(S) FAILED -- DO NOT REBUILD THE DELIVERY:")
        for f in FAILURES:
            print(f"  - {f}")
        sys.exit(1)
    print("ALL STEP 2 CHECKS PASSED")


if __name__ == "__main__":
    main()
