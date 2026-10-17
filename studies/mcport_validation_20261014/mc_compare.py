#!/usr/bin/env python
"""
MC-port validation (14 Oct 2026): MC per-file outputs and MC builds, old vs
new. Reuses compare.py (copied unchanged from validate/rebuild-2026-10-14)
for the shard, JSON and ROOT comparisons; only the MC directory layout
(record<ID>/job_<file_index>) and the sibling-array bookkeeping are new here.

Subcommands
-----------
runs    Compare two MC per-file trees: every shard database (all tables,
        every mass array AND every MC sibling array _mcw / _mcraw_* decoded
        and compared element by element) and job_metadata.json (every key;
        only created_utc, elapsed_sec, git_commit may differ).
builds  Compare two MC build directories: every histogram in every ROOT file
        (names, edges, bin contents, variances = sumw2, entries, title) and
        the build report JSON (with the two sides' directories replaced by
        placeholders).

Shard databases are copied to a temporary directory before being opened
(compare._read_db), so the inputs are never written to.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from compare import PROVENANCE_KEYS, _read_db, _read_root, compare_dbs, json_diff

SIBLING_RE = re.compile(r"_IM_[0-9a-z]+(_mcw|_mcraw_[a-z0-9]+)$")


def _sibling_counts(db: Path) -> dict:
    chunks = _read_db(db)["chunks"]
    n_sib = n_sib_values = n_mass = 0
    by_suffix: dict[str, int] = {}
    for (_table, sig), lst in chunks.items():
        m = SIBLING_RE.search(sig)
        if m:
            n_sib += len(lst)
            n_sib_values += sum(int(x.size) for _, x in lst)
            by_suffix[m.group(1)] = by_suffix.get(m.group(1), 0) + len(lst)
        else:
            n_mass += len(lst)
    return {"n_mass_arrays": n_mass, "n_sibling_arrays": n_sib,
            "n_sibling_values": n_sib_values, "sibling_arrays_by_suffix": by_suffix}


def cmd_runs(args):
    ra, rb = Path(args.a), Path(args.b)
    jobs = [(int(r), int(f)) for r, f in (x.split(":") for x in args.jobs.split(","))]
    result = {"a": str(ra), "b": str(rb), "jobs": {}}
    all_identical = True
    for rid, fi in jobs:
        name = f"record{rid}/job_{fi}"
        ja, jb = ra / f"record{rid}" / f"job_{fi}", rb / f"record{rid}" / f"job_{fi}"
        ma = json.loads((ja / "job_metadata.json").read_text())
        mb = json.loads((jb / "job_metadata.json").read_text())
        jd = json_diff(ma, mb)
        prov = [d["path"] for d in jd if d["path"].lstrip("/") in PROVENANCE_KEYS]
        phys = [d for d in jd if d["path"].lstrip("/") not in PROVENANCE_KEYS]
        sa = sorted(p.name for p in ja.glob("*.sqlite"))
        sb = sorted(p.name for p in jb.glob("*.sqlite"))
        shards = {}
        for s in sorted(set(sa) | set(sb)):
            if s not in sa or s not in sb:
                shards[s] = {"identical": False, "differences": [{"what": "missing on one side"}]}
                continue
            shards[s] = compare_dbs(ja / s, jb / s)
            shards[s]["siblings_side_a"] = _sibling_counts(ja / s)
            print(f"{name:20s} {s:42s} identical={shards[s]['identical']} "
                  f"siblings={shards[s]['siblings_side_a']['n_sibling_arrays']}", flush=True)
        ident = not phys and sa == sb and all(v["identical"] for v in shards.values())
        all_identical &= ident
        result["jobs"][name] = {
            "identical": ident,
            "file_url_a": ma.get("file_url"), "file_url_b": mb.get("file_url"),
            "git_commit_a": ma.get("git_commit"), "git_commit_b": mb.get("git_commit"),
            "is_mc": [ma.get("is_mc"), mb.get("is_mc")],
            "n_read": ma.get("n_read"), "n_after_gate": ma.get("n_after_gate"),
            "n_labels_inclusive": len(ma.get("final_state_label_event_counts_inclusive", {})),
            "metadata_physics_differences": phys,
            "metadata_provenance_differences": prov,
            "shards": shards,
        }
    result["all_identical"] = all_identical
    Path(args.out).write_text(json.dumps(result, indent=2, default=str))
    print(f"ALL IDENTICAL: {all_identical}  -> {args.out}")


def cmd_builds(args):
    da, db = Path(args.a), Path(args.b)
    result = {"a": str(da), "b": str(db), "root_files": {}, "json_files": {}}
    all_identical = True
    ra = sorted(p.name for p in da.glob("*.root"))
    rb = sorted(p.name for p in db.glob("*.root"))
    if ra != rb:
        all_identical = False
        result["root_file_names_differ"] = {"a": ra, "b": rb}
    for name in sorted(set(ra) & set(rb)):
        ha, hb = _read_root(da / name), _read_root(db / name)
        diffs = []
        if set(ha) != set(hb):
            diffs.append({"what": "names", "only_a": sorted(set(ha) - set(hb))[:50],
                          "only_b": sorted(set(hb) - set(ha))[:50]})
        n_bins = 0
        for h in sorted(set(ha) & set(hb)):
            x, y = ha[h], hb[h]
            n_bins += x["values"].size
            for field in ("edges", "values", "variances"):
                xa, ya = x[field], y[field]
                if (xa is None) != (ya is None) or (xa is not None and (
                        xa.shape != ya.shape or xa.tobytes() != ya.tobytes())):
                    diffs.append({"what": field, "histogram": h})
            for field in ("entries", "title"):
                if x[field] != y[field]:
                    diffs.append({"what": field, "histogram": h, "a": x[field], "b": y[field]})
        ident = not diffs
        all_identical &= ident
        result["root_files"][name] = {
            "identical": ident, "n_histograms_a": len(ha), "n_histograms_b": len(hb),
            "n_bins_compared": n_bins,
            "sum_of_weights_a": float(sum(h["values"].sum() for h in ha.values())),
            "sum_of_weights_b": float(sum(h["values"].sum() for h in hb.values())),
            "variances_present": all(h["variances"] is not None for h in ha.values()),
            "differences": diffs[:200]}
        print(f"{name:40s} hists {len(ha)} vs {len(hb)} identical={ident}")
    for name in sorted(p.name for p in da.glob("*.json")):
        ta = (da / name).read_text()
        tb = (db / name).read_text()
        ta = ta.replace(str(da), "<OUT>").replace(args.a_runs, "<RUNS>").replace(args.a_scratch, "<SCRATCH>")
        tb = tb.replace(str(db), "<OUT>").replace(args.b_runs, "<RUNS>").replace(args.b_scratch, "<SCRATCH>")
        diffs = json_diff(json.loads(ta), json.loads(tb))
        prov = [d for d in diffs if re.search(r"utc|time|commit|elapsed|date", d["path"], re.I)]
        other = [d for d in diffs if d not in prov]
        all_identical &= not other
        result["json_files"][name] = {"identical_except_paths_and_provenance": not other,
                                      "provenance_differences": [d["path"] for d in prov],
                                      "differences": other[:100]}
        print(f"{name:40s} identical_except_paths_and_provenance={not other} "
              f"(provenance fields differing: {len(prov)})")
    result["all_identical"] = all_identical
    Path(args.out).write_text(json.dumps(result, indent=2, default=float))
    print(f"ALL IDENTICAL: {all_identical}  -> {args.out}")


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("runs")
    s.add_argument("--a", required=True)
    s.add_argument("--b", required=True)
    s.add_argument("--jobs", required=True, help="comma list of record:file_index")
    s.add_argument("--out", required=True)
    s = sub.add_parser("builds")
    for a in ("--a", "--b", "--a-runs", "--b-runs", "--a-scratch", "--b-scratch", "--out"):
        s.add_argument(a, required=True)
    args = p.parse_args()
    {"runs": cmd_runs, "builds": cmd_builds}[args.cmd](args)


if __name__ == "__main__":
    main()
