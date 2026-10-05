"""
exact-jet-labels task, Step 4: full-scale completeness and identity checks.

Run after all 209 production jobs have finished. Checks, in order:

  1. Completeness: every array index present exactly once (57 DoubleMuon,
     152 SingleMuon), every job produced by the ONE pinned commit, no Python
     traceback in any stderr log.
  2. Totals: each dataset's summed n_read equals the CMS portal total the
     1 Oct production also matched (DoubleMuon 94,148,416; SingleMuon
     323,952,013).
  3. No capping: zero CAPPED:: entries in any rare4 shard.
  4. Step 3 check (a) at full scale: selection counts and every rare4 reject
     diagnostic identical to the 1 Oct rare4 production, job by job.
  5. Step 3 check (b) at full scale: label redistribution only -- each OLD
     label's event count equals the sum of the NEW labels that the OLD
     capping rule folds into it, and every <=3-light-jet rare4 final state
     is untouched.
  6. Reporting: how many 5j/6j/... final states were created, how many
     survive the >=100-events-per-final-state rule, the light-jet
     multiplicity distribution, and how many events ended up in a final
     state with 10 or more light jets (where the OLD capping was itself
     inconsistent -- see REPORT.md).

The 1 Oct production is opened strictly READ-ONLY throughout
(`mode=ro&immutable=1`); nothing under output/ is ever modified.

Usage (from the ANALYSIS checkout, never the pinned production one):
    python studies/cms_datasets/matching/vB_exactlabels/scripts/vB_check_step4.py
"""
from __future__ import annotations

import json
import re
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(REPO_ROOT))

from services.calculations import physics_calcs  # noqa: E402

OUT = Path("/storage/agrp/berkom/atlas-utilization/output/cms_datasets")
OLD_BASE = OUT / "runs_matched_rare4"
NEW_BASE = OUT / "runs_matched_vB_exactlabels_20261005"

PINNED_COMMIT = "26666844debb374bf3872831320a79a6c8d7ea22"
EXPECTED_N_JOBS = {"DoubleMuon": 57, "SingleMuon": 152}
EXPECTED_N_READ = {"DoubleMuon": 94_148_416, "SingleMuon": 323_952_013}
# How the delivery pools the two datasets, so the per-label numbers reported
# here describe exactly the delivered population.
DELIVERY_SIDE = {"DoubleMuon": "inclusive", "SingleMuon": "exclusive"}

RARE4_SHARDS = ("dataset_shard_rare4_inclusive.sqlite",
                "dataset_shard_rare4_exclusive.sqlite")

FAILURES = []
RESULTS = {}


def check(name, condition, detail=""):
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {name}" + (f" -- {detail}" if detail and not condition else ""))
    if not condition:
        FAILURES.append(name)
    return bool(condition)


def jet_count(label: str) -> int:
    return int(label.split("_")[2][:-1])


def count_capped(path: Path) -> int:
    con = sqlite3.connect(f"file:{path}?mode=ro&immutable=1", uri=True)
    try:
        cur = con.cursor()
        n = 0
        for (table, col) in (("array_chunks", "signature"), ("metadata", "key")):
            try:
                cur.execute(
                    f"SELECT COUNT(*) FROM {table} WHERE {col} LIKE 'CAPPED::%'")
                n += int(cur.fetchone()[0])
            except sqlite3.OperationalError:
                pass
        return n
    finally:
        con.close()


def load_metas(base: Path, dataset: str):
    index = json.loads((base / f"{dataset}_index.json").read_text())
    metas = {}
    missing = []
    for idx in index:
        p = base / dataset / f"job_{idx}" / "job_metadata.json"
        if not p.exists():
            missing.append(idx)
            continue
        metas[idx] = json.loads(p.read_text())
    return metas, missing, index


# ==========================================================================

def main():
    print("=" * 74)
    print("exact-jet-labels task, Step 4: full-scale checks")
    print(f"  NEW: {NEW_BASE}")
    print(f"  OLD (read-only): {OLD_BASE}")
    print("=" * 74)

    all_new, all_old = {}, {}

    # ---------------- 1 + 2: completeness and totals ----------------
    print("\n--- 1. Completeness, pinned commit, logs ---")
    for dataset, n_expected in EXPECTED_N_JOBS.items():
        metas, missing, index = load_metas(NEW_BASE, dataset)
        all_new[dataset] = metas
        check(f"{dataset}: all {n_expected} jobs present",
              len(metas) == n_expected and not missing,
              f"have {len(metas)}, missing indices {missing[:10]}")
        check(f"{dataset}: index map has {n_expected} entries",
              len(index) == n_expected, f"got {len(index)}")

        commits = {m["git_commit"] for m in metas.values()}
        check(f"{dataset}: every job produced by the ONE pinned commit 2666684",
              commits == {PINNED_COMMIT}, f"found {sorted(commits)}")

        # One file each, no duplicates.
        urls = [m["file_url"] for m in metas.values()]
        check(f"{dataset}: every input file read exactly once ({len(set(urls))} distinct)",
              len(urls) == len(set(urls)),
              f"{len(urls) - len(set(urls))} duplicate file_url(s)")

        bad_logs = []
        log_dir = NEW_BASE / "logs" / dataset
        for idx in index:
            err = log_dir / f"err.{idx}.log"
            if not err.exists():
                bad_logs.append((idx, "missing err log"))
                continue
            text = err.read_text(errors="replace")
            if "Traceback (most recent call last)" in text:
                bad_logs.append((idx, "traceback"))
        check(f"{dataset}: no Python traceback in any of the {len(index)} stderr logs",
              not bad_logs, f"{bad_logs[:5]}")

        total_read = sum(m["n_read"] for m in metas.values())
        check(f"{dataset}: summed n_read == {EXPECTED_N_READ[dataset]:,} "
              f"(the CMS portal total the 1 Oct run also matched)",
              total_read == EXPECTED_N_READ[dataset], f"got {total_read:,}")
        print(f"       {dataset}: n_read total = {total_read:,}")

    # ---------------- 3: no capping ----------------
    print("\n--- 2. No capped signatures in any rare4 shard ---")
    for dataset in EXPECTED_N_JOBS:
        total_capped = 0
        for idx in all_new[dataset]:
            for shard in RARE4_SHARDS:
                total_capped += count_capped(NEW_BASE / dataset / f"job_{idx}" / shard)
        check(f"{dataset}: zero CAPPED:: entries across all rare4 shards",
              total_capped == 0, f"found {total_capped}")

    # ---------------- 4: check (a) at full scale ----------------
    print("\n--- 3. Check (a) at full scale: selection identical to 1 Oct ---")
    DIAG_KEYS = ("n_accepted_events_before_rare4_rule", "n_rejected_gt4_lepton_bjet",
                 "n_kept_le4_lepton_bjet", "n_hidden_cases", "rejected_N_distribution")
    TOP_KEYS = ("n_read", "n_after_golden_json", "n_after_trigger",
                "n_after_gate", "n_exclusive")
    totals = {"rare4_rejected": 0, "hidden_cases": 0}
    for dataset in EXPECTED_N_JOBS:
        old_metas, old_missing, _ = load_metas(OLD_BASE, dataset)
        all_old[dataset] = old_metas
        check(f"{dataset}: the 1 Oct run has all {EXPECTED_N_JOBS[dataset]} jobs to "
              f"compare against", not old_missing, f"missing {old_missing[:5]}")
        bad = []
        for idx, nm in all_new[dataset].items():
            om = old_metas.get(idx)
            if om is None:
                bad.append((idx, "no 1 Oct counterpart"))
                continue
            for k in TOP_KEYS:
                if om[k] != nm[k]:
                    bad.append((idx, k, om[k], nm[k]))
            for k in DIAG_KEYS:
                if om["rare4_diagnostics"][k] != nm["rare4_diagnostics"][k]:
                    bad.append((idx, f"rare4.{k}",
                                om["rare4_diagnostics"][k], nm["rare4_diagnostics"][k]))
            totals["rare4_rejected"] += nm["rare4_diagnostics"]["n_rejected_gt4_lepton_bjet"]
            totals["hidden_cases"] += nm["rare4_diagnostics"]["n_hidden_cases"]
        check(f"{dataset}: all {len(TOP_KEYS)} selection counts AND all "
              f"{len(DIAG_KEYS)} rare4 reject diagnostics identical to 1 Oct, "
              f"job by job ({len(all_new[dataset])} jobs)",
              not bad, f"{len(bad)} differences, first: {bad[:3]}")

    print(f"       total rare4 rejected events over all 209 jobs: "
          f"{totals['rare4_rejected']:,}")
    print(f"       total rare4 'hidden' cases over all 209 jobs:  "
          f"{totals['hidden_cases']:,}")
    check("total rare4 rejected events == 5,738 (the 1 Oct production's own total)",
          totals["rare4_rejected"] == 5738, f"got {totals['rare4_rejected']}")
    RESULTS["rare4_rejected_total"] = totals["rare4_rejected"]
    RESULTS["hidden_cases_total"] = totals["hidden_cases"]

    # ---------------- 5: check (b) at full scale ----------------
    print("\n--- 4. Check (b) at full scale: label redistribution only ---")
    pooled_new = defaultdict(int)
    pooled_old = defaultdict(int)
    for dataset in EXPECTED_N_JOBS:
        side = DELIVERY_SIDE[dataset]
        key = f"final_state_label_event_counts_{side}"
        per_job_bad = []
        for idx, nm in all_new[dataset].items():
            om = all_old[dataset][idx]
            new_counts = nm["rare4_diagnostics"][key]
            old_counts = om["rare4_diagnostics"][key]

            if sum(new_counts.values()) != sum(old_counts.values()):
                per_job_bad.append((idx, "total events differ"))

            folded = defaultdict(int)
            contributors = defaultdict(list)
            for lb, c in new_counts.items():
                ol = physics_calcs.limit_particles_in_fs(lb, 4)
                folded[ol] += c
                contributors[ol].append(lb)
            if set(folded) != set(old_counts):
                per_job_bad.append((idx, "folded label set differs"))
            for ol, c in old_counts.items():
                if folded.get(ol, 0) != c:
                    per_job_bad.append((idx, f"{ol}: {c} vs {folded.get(ol, 0)}"))

            # <=3 light jets untouched (rare4: e+m+b<=4, so no non-jet merging)
            for lb, c in new_counts.items():
                if jet_count(lb) <= 3 and old_counts.get(lb) != c:
                    per_job_bad.append((idx, f"<=3j label {lb} changed"))

            for lb, c in new_counts.items():
                pooled_new[lb] += c
            for lb, c in old_counts.items():
                pooled_old[lb] += c

        check(f"{dataset} ({side}): label redistribution only, job by job "
              f"({len(all_new[dataset])} jobs)",
              not per_job_bad, f"{len(per_job_bad)} problems, first: {per_job_bad[:3]}")

    # Pooled (delivery-population) statement.
    folded = defaultdict(int)
    contributors = defaultdict(list)
    for lb, c in pooled_new.items():
        ol = physics_calcs.limit_particles_in_fs(lb, 4)
        folded[ol] += c
        contributors[ol].append(lb)
    check("POOLED delivery population: total events identical to 1 Oct",
          sum(pooled_new.values()) == sum(pooled_old.values()),
          f"new={sum(pooled_new.values()):,} old={sum(pooled_old.values()):,}")
    mism = [(ol, c, folded.get(ol, 0)) for ol, c in pooled_old.items()
            if folded.get(ol, 0) != c]
    check(f"POOLED: every one of the {len(pooled_old)} OLD final states equals the "
          f"sum of the NEW final states folding into it",
          not mism, f"{len(mism)} mismatches, first: {mism[:3]}")
    le3_bad = [lb for lb in pooled_new
               if jet_count(lb) <= 3 and pooled_old.get(lb) != pooled_new[lb]]
    check(f"POOLED: every <=3-light-jet final state has an identical event count",
          not le3_bad, f"{len(le3_bad)} differ, first: {le3_bad[:3]}")

    # ---------------- 6: reporting numbers ----------------
    print("\n--- 5. Reporting numbers (delivered population) ---")
    by_jets = defaultdict(int)
    for lb, c in pooled_new.items():
        by_jets[jet_count(lb)] += c
    total_events = sum(pooled_new.values())

    new_fs = set(pooled_new)
    old_fs = set(pooled_old)
    created = sorted(new_fs - old_fs)
    ge5 = [lb for lb in new_fs if jet_count(lb) >= 5]
    ge5_over_100 = [lb for lb in ge5 if pooled_new[lb] >= 100]
    ge10 = [lb for lb in new_fs if jet_count(lb) >= 10]

    print(f"       final states, 1 Oct: {len(old_fs)}   new: {len(new_fs)}")
    print(f"       brand-new final states (not present on 1 Oct): {len(created)}")
    print(f"       final states with >=5 light jets: {len(ge5)}, of which "
          f"{len(ge5_over_100)} have >=100 events (so survive the per-final-state rule)")
    print(f"       final states with >=10 light jets: {len(ge10)} "
          f"(the range where the OLD capping was itself inconsistent)")
    print(f"       total delivered-population events: {total_events:,}")
    print("       light-jet multiplicity distribution:")
    for k in sorted(by_jets):
        print(f"         {k:>3}j : {by_jets[k]:>12,}  ({100.0*by_jets[k]/total_events:6.3f}%)")

    RESULTS.update({
        "n_final_states_1oct": len(old_fs),
        "n_final_states_new": len(new_fs),
        "n_final_states_created": len(created),
        "n_final_states_ge5_lightjets": len(ge5),
        "n_final_states_ge5_lightjets_with_ge100_events": len(ge5_over_100),
        "n_final_states_ge5_lightjets_dropped_by_100_event_rule":
            len(ge5) - len(ge5_over_100),
        "n_final_states_ge10_lightjets": len(ge10),
        "final_states_ge10_lightjets": sorted(ge10),
        "total_delivered_population_events": total_events,
        "events_by_light_jet_count": {str(k): by_jets[k] for k in sorted(by_jets)},
        "events_with_ge5_lightjets": sum(c for k, c in by_jets.items() if k >= 5),
        "events_with_ge10_lightjets": sum(c for k, c in by_jets.items() if k >= 10),
        "pooled_new_final_state_event_counts": dict(sorted(pooled_new.items())),
        "pooled_1oct_final_state_event_counts": dict(sorted(pooled_old.items())),
    })

    out_path = NEW_BASE / "step4_checks.json"
    out_path.write_text(json.dumps({"failures": FAILURES, "results": RESULTS},
                                   indent=2, default=str))
    print(f"\nwrote {out_path}")

    print("\n" + "=" * 74)
    if FAILURES:
        print(f"{len(FAILURES)} CHECK(S) FAILED -- DO NOT BUILD THE DELIVERY:")
        for f in FAILURES:
            print(f"  - {f}")
        sys.exit(1)
    print("ALL STEP 4 CHECKS PASSED -- the delivery may be built")


if __name__ == "__main__":
    main()
