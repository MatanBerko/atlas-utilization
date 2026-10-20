#!/usr/bin/env python
"""
b-tag 0.2489 + SingleElectron (20 Oct 2026): turn the real-file outputs of
pbs_checks.sh into evidence JSONs (checks A-E of the task). Reads only.

  A  data, 4 datasets, OLD (matched4, 0.2598) vs NEW (matched5, 0.2489):
     acceptance/cutflow counts, b-tagged jet fraction, n_b distribution,
     per-event label migration (debug dumps joined on run/lumi/event);
     plus NEW-with-0.2598 (ovr) vs OLD: every shard compared value by value.
  B  SingleElectron, NEW, 30529/0 and 30562/0: accepted / exclusive counts
     against the singleelectron_prep study's own per-file outputs (read-only).
  C  de-duplication across the sampled files (shared run/lumi/event).
  D  MC 67801/0, 75589/0: b-tag migration, SingleElectron flag pass fraction,
     ovr vs OLD, and the three MC smoke builds.
  E  the data delivery builds (NEW 5 datasets, OLD 4).

Usage:
    python analyse.py --repo <unpacked NEW data code> --work <work dir> --out <evidence dir>
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

DATA4 = ("DoubleMuon", "SingleMuon", "DoubleEG", "MuonEG")
ORDER5 = DATA4 + ("SingleElectron",)
SE_JOBS = {"0": (30529, 0, "G"), "1": (30562, 0, "H")}
MC_RECORDS = (67801, 75589)
STUDY_PER_FILE = {   # the singleelectron_prep per-file outputs (19 Oct re-run = 7 Oct)
    "0": "/storage/agrp/berkom/atlas-utilization/work/serecheck_20261019/se/a_0p2598/tnp_G_0.json",
    "1": "/storage/agrp/berkom/atlas-utilization/work/serecheck_20261019/se/a_0p2598/tnp_H_0.json",
}
PROVENANCE = {"created_utc", "elapsed_sec", "git_commit", "inclusive_shard_size_mb",
              "exclusive_shard_size_mb"}
LABEL_RE = re.compile(r"^(\d+)e_(\d+)m_(\d+)j_(\d+)b$")
SE_BIT = 64


def meta(d: Path) -> dict:
    return json.loads((d / "job_metadata.json").read_text())


def parse(label: str):
    m = LABEL_RE.match(label)
    return tuple(int(x) for x in m.groups()) if m else None


def jet_summary(label_counts: dict) -> dict:
    """b-tag summary over all accepted events, from the exact final-state
    labels (normal version, all accepted events)."""
    n_ev = n_j = n_b = 0
    nb_dist = Counter()
    for label, n in label_counts.items():
        e, m, j, b = parse(label)
        n_ev += n
        n_j += j * n
        n_b += b * n
        nb_dist[min(b, 3)] += n
    return {"n_events": n_ev, "n_light_jets": n_j, "n_b_jets": n_b,
            "b_tagged_jet_fraction": (n_b / (n_j + n_b)) if (n_j + n_b) else None,
            "n_b_distribution": {("3+" if k == 3 else str(k)): nb_dist[k] for k in range(4)}}


def read_dump(path: Path) -> dict:
    with open(path, newline="") as fh:
        r = csv.DictReader(fh)
        return {(row["run"], row["luminosityBlock"], row["event"]): row for row in r}


def migration(old_rows: dict, new_rows: dict) -> dict:
    """Per-event label change, OLD vs NEW, for the same accepted events."""
    same_keys = set(old_rows) == set(new_rows)
    cls = Counter()
    nb_matrix = Counter()
    other_examples = []
    for k in old_rows.keys() & new_rows.keys():
        lo, ln = old_rows[k]["final_state"], new_rows[k]["final_state"]
        po, pn = parse(lo), parse(ln)
        if lo == ln:
            cls["unchanged"] += 1
            if po:
                nb_matrix[(po[3], po[3])] += 1
        elif po and pn:
            if po[0] == pn[0] and po[1] == pn[1] and po[2] + po[3] == pn[2] + pn[3] and pn[3] > po[3]:
                cls["b_migration_light_to_b"] += 1
                nb_matrix[(po[3], pn[3])] += 1
            else:
                cls["OTHER"] += 1
                other_examples.append([list(k), lo, ln])
        elif po and ln == "VERSION_B_REJECTED":
            cls["kept_to_version_b_rejected"] += 1
        elif lo == "VERSION_B_REJECTED" and pn:
            cls["version_b_rejected_to_kept"] += 1
            other_examples.append([list(k), lo, ln])
        else:
            cls["OTHER"] += 1
            other_examples.append([list(k), lo, ln])
    # acceptance / exclusive flags must not change
    flag_changes = 0
    for k in old_rows.keys() & new_rows.keys():
        for c in [c for c in old_rows[k] if c.startswith("acc_") or c == "exclusive"]:
            if old_rows[k][c] != new_rows[k].get(c):
                flag_changes += 1
    return {"same_accepted_events": same_keys, "n_events_old": len(old_rows),
            "n_events_new": len(new_rows), "classes": dict(cls),
            "n_b_old_to_new_for_kept_events": {f"{a}->{b}": n for (a, b), n in sorted(nb_matrix.items())},
            "n_acceptance_or_exclusive_flag_changes": flag_changes,
            "other_examples": other_examples[:20]}


def metadata_diff(C, ma: dict, mb: dict) -> dict:
    d = C.json_diff(ma, mb)
    phys = [x for x in d if x["path"].lstrip("/").split("/")[0] not in PROVENANCE]
    return {"n_differences": len(phys), "paths": [x["path"] for x in phys][:200],
            "differences": phys[:60]}


def compare_dirs(C, da: Path, db: Path, mc: bool) -> dict:
    """Every shard of two job dirs, value by value (mcport compare.py,
    unchanged). For MC, an acceptance-bitmask sibling difference is allowed
    ONLY if clearing the new SingleElectron bit 6 makes it identical."""
    out = {}
    for s in sorted(p.name for p in da.glob("*.sqlite")):
        r = C.compare_dbs(da / s, db / s)
        if mc and not r["identical"]:
            ra, rb = C._read_db(da / s), C._read_db(db / s)
            rest = []
            n_ok = 0
            for diff in r["differences"]:
                sig = diff.get("signature", "")
                if diff["what"] == "array values" and sig.endswith("_mcraw_acc"):
                    key = next(k for k in ra["chunks"] if k[1] == sig)
                    xa = ra["chunks"][key][diff["chunk"]][1]
                    xb = rb["chunks"][key][diff["chunk"]][1]
                    if np.array_equal(xa, xb & np.uint8(0xFF ^ SE_BIT)):
                        n_ok += 1
                        continue
                rest.append(diff)
            r = dict(r, identical_after_clearing_bit6=not rest,
                     n_acc_sibling_arrays_differing_only_by_bit6=n_ok,
                     differences=rest[:20])
        else:
            r = dict(r, differences=r["differences"][:20])
        out[s] = r
    missing = sorted({p.name for p in db.glob("*.sqlite")} ^ set(out))
    return {"shards": out, "shards_only_on_one_side": missing,
            "all_shards_identical": all(v["identical"] or v.get("identical_after_clearing_bit6")
                                        for v in out.values()) and not missing}


def root_totals(path: Path) -> dict:
    import uproot
    n_h = 0
    entries = 0.0
    sumw = 0.0
    with uproot.open(path) as f:
        for key, cls in f.classnames().items():
            if not cls.startswith("TH1"):
                continue
            h = f[key]
            n_h += 1
            entries += float(h.member("fEntries"))
            sumw += float(h.values(flow=True).sum())
    return {"n_histograms": n_h, "sum_entries": entries, "sum_contents": sumw}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--work", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    sys.path.insert(0, args.repo)
    sys.path.insert(0, str(Path(args.repo) / "studies/mcport_validation_20261014"))
    import compare as C  # noqa: E402  (unchanged mcport compare.py)

    W = Path(args.work)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    R = W / "runs"

    # ---------------- A: data, OLD vs NEW, and ovr vs OLD ----------------
    A = {}
    dumps_new = {}
    for ds in DATA4:
        do, dn, dv = (R / s / "data" / ds / "job_0" for s in ("old", "new", "ovr"))
        mo, mn = meta(do), meta(dn)
        d4o, d4n = mo["matched4_diagnostics"], mn["matched4_diagnostics"]
        rows_old = read_dump(do / "debug_events.csv")
        rows_new = read_dump(dn / "debug_events.csv")
        dumps_new[ds] = rows_new
        A[ds] = {
            "file_url": mn["file_url"],
            "counts_old": {k: mo[k] for k in ("n_read", "n_after_golden_json", "n_after_trigger",
                                               "n_after_gate", "n_exclusive")},
            "counts_new": {k: mn[k] for k in ("n_read", "n_after_golden_json", "n_after_trigger",
                                               "n_after_gate", "n_exclusive")},
            "acceptance_counts_old": d4o["acceptance_counts"],
            "acceptance_counts_new": d4n["acceptance_counts"],
            "four_acceptance_counts_identical": all(
                d4o["acceptance_counts"][k] == d4n["acceptance_counts"][k] for k in DATA4),
            "n_attributed_old": d4o["n_attributed_per_dataset"],
            "n_attributed_new": d4n["n_attributed_per_dataset"],
            "guard_violations_new": d4n["trigger_guard_violations"],
            "jets_old": jet_summary(mo["final_state_label_event_counts_inclusive"]),
            "jets_new": jet_summary(mn["final_state_label_event_counts_inclusive"]),
            "version_b_old": {k: mo["rare4_diagnostics"][k] for k in
                              ("n_rejected_gt4_lepton_bjet", "n_kept_le4_lepton_bjet")},
            "version_b_new": {k: mn["rare4_diagnostics"][k] for k in
                              ("n_rejected_gt4_lepton_bjet", "n_kept_le4_lepton_bjet")},
            "per_event_migration": migration(rows_old, rows_new),
            "override_0p2598_vs_old": {
                "shards": compare_dirs(C, do, dv, mc=False),
                "metadata": metadata_diff(C, mo, meta(dv)),
            },
        }
        jo, jn = A[ds]["jets_old"], A[ds]["jets_new"]
        A[ds]["b_tagged_jet_fraction_relative_change"] = (
            jn["b_tagged_jet_fraction"] / jo["b_tagged_jet_fraction"] - 1
            if jo["b_tagged_jet_fraction"] else None)
        print(f"A {ds}: acc identical {A[ds]['four_acceptance_counts_identical']}, "
              f"bfrac {jo['b_tagged_jet_fraction']:.5f} -> {jn['b_tagged_jet_fraction']:.5f}, "
              f"migration {A[ds]['per_event_migration']['classes']}, "
              f"ovr shards identical {A[ds]['override_0p2598_vs_old']['shards']['all_shards_identical']}",
              flush=True)
    (out / "A_data_old_vs_new.json").write_text(json.dumps(A, indent=2, default=str))

    # ---------------- B: SingleElectron vs the study ----------------
    B = {}
    se_hist = {}
    for job, (rid, fi, era) in SE_JOBS.items():
        d = R / "new" / "data" / "SingleElectron" / f"job_{job}"
        m = meta(d)
        d5 = m["matched4_diagnostics"]
        study = json.loads(Path(STUDY_PER_FILE[job]).read_text())
        s32 = study["threshold_scan"]["results"]["32.0"]
        B[f"{rid}/{fi}"] = {
            "file_url_new": m["file_url"], "file_url_study": study.get("file_url"),
            "same_file": m["file_url"] == study.get("file_url"),
            "n_after_trigger_new": m["n_after_trigger"], "n_after_ele27_study": study["n_after_ele27"],
            "n_accepted_new": d5["n_own_accepted"], "n_accepted_study_T32": s32["n_accepted"],
            "n_exclusive_new": d5["n_own_exclusive"],
            "n_not_accepted_by_existing_study_T32": s32["n_gain_not_accepted_by_existing"],
            "accepted_equal": d5["n_own_accepted"] == s32["n_accepted"],
            "exclusive_equal": d5["n_own_exclusive"] == s32["n_gain_not_accepted_by_existing"],
            "accepted_also_by_higher": d5["n_own_accepted_also_accepted_by_higher"],
            "trigger_guard_violations_new": d5["trigger_guard_violations"],
            "trigger_guard_violations_study": study["trigger_guard_violations"],
            "singleelectron_cutflow": d5["cutflow_per_dataset"]["SingleElectron"],
            "jets_new": jet_summary(m["final_state_label_event_counts_inclusive"]),
            "version_b_new": {k: m["rare4_diagnostics"][k] for k in
                              ("n_rejected_gt4_lepton_bjet", "n_kept_le4_lepton_bjet")},
            "study_source": STUDY_PER_FILE[job],
        }
        se_hist[f"{rid}/{fi}"] = d5["singleelectron"]["leading_qualifying_offline_pt_histogram_fired"]
        dumps_new[f"SingleElectron/{job}"] = read_dump(d / "debug_events.csv")
        print(f"B {rid}/{fi}: accepted {d5['n_own_accepted']} vs study {s32['n_accepted']}, "
              f"exclusive {d5['n_own_exclusive']} vs {s32['n_gain_not_accepted_by_existing']}", flush=True)
    (out / "B_singleelectron_vs_study.json").write_text(json.dumps(B, indent=2, default=str))
    (out / "B_singleelectron_pt_histograms.json").write_text(json.dumps(se_hist))

    # ---------------- C: de-duplication across files ----------------
    where = defaultdict(list)
    for name, rows in dumps_new.items():
        for k in rows:
            where[k].append(name)
    shared = {k: v for k, v in where.items() if len(v) > 1}
    lumis = {name: {(k[0], k[1]) for k in rows} for name, rows in dumps_new.items()}
    runs = {name: {k[0] for k in rows} for name, rows in dumps_new.items()}
    names = sorted(dumps_new)
    pooled_count = Counter()
    for name, rows in dumps_new.items():
        ds = name.split("/")[0]
        first = ds == ORDER5[0]
        for k, row in rows.items():
            if first or row["exclusive"] == "1":
                pooled_count[k] += 1
    flags_consistent = all(
        len({tuple(dumps_new[n][k][f"acc_{d}"] for d in ORDER5) for n in v}) == 1
        for k, v in shared.items())
    C_ = {
        "files": names,
        "n_accepted_events_per_file": {n: len(dumps_new[n]) for n in names},
        "shared_runs": {f"{a} & {b}": len(runs[a] & runs[b]) for i, a in enumerate(names)
                        for b in names[i + 1:]},
        "shared_lumisections": {f"{a} & {b}": len(lumis[a] & lumis[b]) for i, a in enumerate(names)
                                for b in names[i + 1:]},
        "n_events_accepted_in_more_than_one_file": len(shared),
        "shared_events_by_files": dict(Counter(" & ".join(sorted(v)) for v in shared.values())),
        "acceptance_flags_identical_in_every_file_holding_the_event": flags_consistent,
        "n_events_pooled_more_than_once": sum(1 for n in pooled_count.values() if n > 1),
        "n_events_pooled_exactly_once": sum(1 for n in pooled_count.values() if n == 1),
        "n_accepted_events_not_pooled": sum(1 for k in where if pooled_count[k] == 0),
        "shared_event_examples": [[list(k), v] for k, v in list(shared.items())[:10]],
    }
    print(f"C: {len(shared)} shared events, pooled >1: {C_['n_events_pooled_more_than_once']}", flush=True)
    (out / "C_dedup_real_files.json").write_text(json.dumps(C_, indent=2, default=str))

    # ---------------- D: MC ----------------
    D = {"per_file": {}, "builds": {}}
    for rid in MC_RECORDS:
        do, dn, dv = (R / s / "mc" / f"record{rid}" / "job_0" for s in ("old", "new", "ovr"))
        mo, mn = meta(do), meta(dn)
        mdn, mdo = mn["mc_diagnostics"], mo["mc_diagnostics"]
        D["per_file"][str(rid)] = {
            "file_url": mn["file_url"],
            "n_stored_old": mdo["n_stored"], "n_stored_new": mdn["n_stored"],
            "n_accepted_per_dataset_old": mdo["n_accepted_per_dataset"],
            "n_accepted_per_dataset_new": mdn["n_accepted_per_dataset"],
            "n_ele27_candidate_old": mdo["n_ele27_candidate_accepted"],
            "n_ele27_candidate_new": mdn["n_ele27_candidate_accepted"],
            "n_singleelectron_accepted_new": mdn["n_singleelectron_accepted"],
            "n_stored_singleelectron_new": mdn["n_stored_singleelectron"],
            "n_stored_only_singleelectron_new": mdn["n_stored_only_singleelectron"],
            "n_stored_in_delivery_union_new": mdn["n_stored_in_delivery_union"],
            "singleelectron_pass_fraction_of_stored": mdn["n_stored_singleelectron"] / mdn["n_stored"],
            "singleelectron_pass_fraction_of_triggered": mdn["n_singleelectron_accepted"] / mdn["n_events_triggered"],
            "singleelectron_cutflow": mdn["singleelectron_cutflow"],
            "singleelectron_guard_violations": mdn["singleelectron_guard_violations"],
            "jets_old": jet_summary(mo["final_state_label_event_counts_inclusive"]),
            "jets_new": jet_summary(mn["final_state_label_event_counts_inclusive"]),
            "per_event_migration": migration(read_dump(do / "debug_events.csv"),
                                             read_dump(dn / "debug_events.csv")),
            "override_0p2598_vs_old": {
                "shards": compare_dirs(C, do, dv, mc=True),
                "metadata": metadata_diff(C, mo, meta(dv)),
            },
        }
        print(f"D {rid}: stored {mdo['n_stored']} -> {mdn['n_stored']}, SE {mdn['n_stored_singleelectron']} "
              f"(only SE {mdn['n_stored_only_singleelectron']})", flush=True)
    for name in ("old", "oldbuilder_newruns", "new"):
        bd = W / "deliver" / name / "mc"
        rep = json.loads((bd / "smoke_build_report.json").read_text()) \
            if (bd / "smoke_build_report.json").exists() else None
        if rep is None:
            cand = sorted(bd.glob("*report*.json"))
            rep = json.loads(cand[0].read_text()) if cand else {}
        samples = {}
        for rid, s in (rep.get("samples") or {}).items():
            h = s.get("histograms") or {}
            samples[rid] = {
                "normalisation_factor": s.get("normalisation_factor"),
                "sigma_w_over_surviving_files": s.get("sigma_w_over_surviving_files"),
                "n_entries_dropped_by_event_union": h.get("n_entries_dropped_by_event_union"),
                "raw_entries_after_union": sum((h.get("raw_yield_by_final_state") or {}).values()),
                "weighted_yield_after_union": sum((h.get("weighted_yield_by_final_state") or {}).values()),
            }
        D["builds"][name] = {
            "event_union": (rep.get("constants") or {}).get("event_union"),
            "samples": samples,
            "root": {p.name: root_totals(p) for p in sorted(bd.glob("*.root"))},
        }
    (out / "D_mc.json").write_text(json.dumps(D, indent=2, default=str))

    # ---------------- E: data delivery builds ----------------
    E = {}
    for name in ("new", "old"):
        bd = W / "deliver" / name / "data"
        summ = sorted(bd.glob("build_summary_*.json"))
        s = json.loads(summ[0].read_text()) if summ else {}
        E[name] = {k: s.get(k) for k in ("priority_order_highest_first", "pooling",
                                          "per_dataset_event_counts", "n_shards_total",
                                          "n_delivered_histograms",
                                          "n_distinct_final_state_categories_delivered", "funnel")}
        E[name]["root"] = {p.name: root_totals(p) for p in sorted(bd.glob("*.root"))}
    (out / "E_data_builds.json").write_text(json.dumps(E, indent=2, default=str))
    print("analyse done", flush=True)


if __name__ == "__main__":
    main()
