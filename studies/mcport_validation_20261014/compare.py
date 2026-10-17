#!/usr/bin/env python
"""
Rebuild validation (14 Oct 2026): old code (ba89791) vs new code
(rebuild/master-2026-10-14) on the same 8 NanoAOD files.

Self-contained on purpose: standard library + numpy (+ uproot for the
delivery comparison), no imports from the repo, so the same script judges
both sides.

Subcommands
-----------
inputs    From the 7 Oct production directory (READ-ONLY), write the 8-file
          PBS mapping and one <Dataset>_index.json per side.
runs      Compare two per-file output trees job by job: every shard database
          (all tables; every stored mass array decoded and compared element
          by element) and job_metadata.json (every key).
delivery  Compare two delivery directories: every histogram in both ROOT
          files (names, edges, bin contents, variances, entries) plus the
          build summary and manifest JSONs.

Shard databases are never opened in place: each one (with any -wal/-shm
side files) is copied to a temporary directory first, so the inputs --
including the read-only 7 Oct outputs -- are never written to.
"""
from __future__ import annotations

import argparse
import io
import json
import shutil
import sqlite3
import tempfile
import zlib
from pathlib import Path

import numpy as np

DATASETS = ("DoubleMuon", "SingleMuon", "DoubleEG", "MuonEG")
N_FILES_PER_DATASET = 2

# job_metadata.json keys that record provenance, not physics: expected to
# differ between two runs of identical code.
PROVENANCE_KEYS = {"created_utc", "git_commit", "elapsed_sec",
                   "inclusive_shard_size_mb", "exclusive_shard_size_mb"}


# ---------------------------------------------------------------- inputs
def cmd_inputs(args):
    full = Path(args.full_runs_dir)
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    rows, files = [], []
    for dataset in DATASETS:
        index = json.loads((full / f"{dataset}_index.json").read_text())
        mapping = {int(l.split()[0]): l.split() for l in
                   (full / f"{dataset}_mapping.txt").read_text().splitlines() if l.strip()}
        small = {}
        for job in range(N_FILES_PER_DATASET):
            ent = index[str(job)]
            m = mapping[job]
            assert m[1] == dataset and int(m[2]) == ent["record_id"] and int(m[3]) == ent["file_index"] \
                and int(m[4]) == job, f"index/mapping disagree for {dataset} job {job}: {m} {ent}"
            small[str(job)] = ent
            rows.append(f"{len(rows)} {dataset} {ent['record_id']} {ent['file_index']} {job}")
            files.append({"dataset": dataset, "job_index": job, **ent})
        for side in args.sides.split(","):
            d = out / side
            d.mkdir(parents=True, exist_ok=True)
            (d / f"{dataset}_index.json").write_text(json.dumps(small, indent=2))
    if (full / "full_files.json").exists():
        urls = {(f["dataset"], f["job_index"]): f["url"]
                for f in json.loads((full / "full_files.json").read_text())["files"]}
        for f in files:
            f["url"] = urls[(f["dataset"], f["job_index"])]
    (out / "mapping.txt").write_text("\n".join(rows) + "\n")
    (out / "files.json").write_text(json.dumps(files, indent=2))
    print("\n".join(rows))


# ------------------------------------------------------------ shard tools
def _deserialize(payload: bytes) -> np.ndarray:
    return np.load(io.BytesIO(zlib.decompress(payload)), allow_pickle=False)


def _read_db(path: Path) -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        copy = Path(tmp) / path.name
        shutil.copy2(path, copy)
        for suffix in ("-wal", "-shm"):
            side = Path(str(path) + suffix)
            if side.exists():
                shutil.copy2(side, Path(str(copy) + suffix))
        con = sqlite3.connect(str(copy))
        tables = [r[0] for r in con.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
        out = {"tables": tables, "chunks": {}, "metadata": {}, "fs_counts": [], "other": {}}
        for t in tables:
            cols = [r[1] for r in con.execute(f"PRAGMA table_info({t})")]
            if {"signature", "n_entries", "payload"} <= set(cols):
                for sig, n, payload in con.execute(
                        f"SELECT signature, n_entries, payload FROM {t} ORDER BY id"):
                    out["chunks"].setdefault((t, sig), []).append((n, _deserialize(payload)))
            elif t == "shard_metadata":
                out["metadata"] = dict(con.execute("SELECT key, value FROM shard_metadata"))
            elif t == "final_state_counts":
                out["fs_counts"] = list(con.execute(
                    "SELECT final_state, n_events FROM final_state_counts ORDER BY rowid"))
            else:
                out["other"][t] = list(con.execute(f"SELECT * FROM {t} ORDER BY rowid"))
        con.close()
    return out


def _compare_arrays(a: np.ndarray, b: np.ndarray) -> dict | None:
    if a.dtype != b.dtype or a.shape != b.shape:
        return {"dtype_a": str(a.dtype), "dtype_b": str(b.dtype),
                "shape_a": list(a.shape), "shape_b": list(b.shape)}
    if a.tobytes() == b.tobytes():
        return None
    neq = ~((a == b) | (np.isnan(a) & np.isnan(b))) if a.dtype.kind == "f" else (a != b)
    idx = np.flatnonzero(neq)
    return {"n_elements_differ": int(idx.size), "first_indices": idx[:10].tolist(),
            "first_a": a.ravel()[idx[:10]].tolist(), "first_b": b.ravel()[idx[:10]].tolist()}


def compare_dbs(pa: Path, pb: Path) -> dict:
    a, b = _read_db(pa), _read_db(pb)
    diffs = []
    if a["tables"] != b["tables"]:
        diffs.append({"what": "tables", "a": a["tables"], "b": b["tables"]})
    keys = sorted(set(a["chunks"]) | set(b["chunks"]))
    n_arrays = n_values = 0
    for k in keys:
        ca, cb = a["chunks"].get(k), b["chunks"].get(k)
        if ca is None or cb is None:
            diffs.append({"what": "signature only on one side", "table": k[0], "signature": k[1],
                          "side": "a" if cb is None else "b"})
            continue
        if len(ca) != len(cb):
            diffs.append({"what": "chunk count", "signature": k[1], "a": len(ca), "b": len(cb)})
            continue
        for i, ((na, xa), (nb, xb)) in enumerate(zip(ca, cb)):
            n_arrays += 1
            n_values += int(xa.size)
            if na != nb:
                diffs.append({"what": "n_entries", "signature": k[1], "chunk": i, "a": na, "b": nb})
            d = _compare_arrays(xa, xb)
            if d:
                diffs.append({"what": "array values", "signature": k[1], "chunk": i, **d})
    if a["fs_counts"] != b["fs_counts"]:
        diffs.append({"what": "final_state_counts", "a_rows": len(a["fs_counts"]),
                      "b_rows": len(b["fs_counts"]),
                      "differing_labels": sorted({r[0] for r in set(a["fs_counts"]) ^ set(b["fs_counts"])})[:50]})
    md_keys = sorted(set(a["metadata"]) | set(b["metadata"]))
    md_diff = [k for k in md_keys if a["metadata"].get(k) != b["metadata"].get(k)]
    if md_diff:
        diffs.append({"what": "shard_metadata", "keys": md_diff,
                      "values": {k: [a["metadata"].get(k), b["metadata"].get(k)] for k in md_diff[:20]}})
    if a["other"] != b["other"]:
        diffs.append({"what": "other tables differ", "tables": sorted(set(a["other"]) | set(b["other"]))})
    return {"identical": not diffs, "n_signatures": len({k[1] for k in keys}),
            "n_arrays_compared": n_arrays, "n_values_compared": n_values,
            "n_final_state_rows": len(a["fs_counts"]), "n_metadata_keys": len(a["metadata"]),
            "differences": diffs}


def json_diff(a, b, path="") -> list:
    if isinstance(a, dict) and isinstance(b, dict):
        out = []
        for k in sorted(set(a) | set(b)):
            p = f"{path}/{k}"
            if k not in a or k not in b:
                out.append({"path": p, "a": a.get(k, "<missing>"), "b": b.get(k, "<missing>")})
            else:
                out += json_diff(a[k], b[k], p)
        return out
    if isinstance(a, list) and isinstance(b, list) and len(a) == len(b):
        out = []
        for i, (x, y) in enumerate(zip(a, b)):
            out += json_diff(x, y, f"{path}[{i}]")
        return out
    return [] if a == b else [{"path": path, "a": a, "b": b}]


CUTFLOW_KEYS = ("n_read", "n_after_golden_json", "n_after_trigger", "n_after_gate", "n_exclusive",
                "n_final_state_groups", "n_signature_writes_inclusive", "n_signature_writes_exclusive",
                "n_values_written_inclusive", "n_values_written_exclusive")


def cmd_runs(args):
    ra, rb = Path(args.a), Path(args.b)
    result = {"a": str(ra), "b": str(rb), "jobs": {}}
    all_identical = True
    for dataset in DATASETS:
        for job in range(N_FILES_PER_DATASET):
            name = f"{dataset}/job_{job}"
            ja, jb = ra / dataset / f"job_{job}", rb / dataset / f"job_{job}"
            ma = json.loads((ja / "job_metadata.json").read_text())
            mb = json.loads((jb / "job_metadata.json").read_text())
            jd = json_diff(ma, mb)
            prov = [d for d in jd if d["path"].lstrip("/") in PROVENANCE_KEYS]
            phys = [d for d in jd if d["path"].lstrip("/") not in PROVENANCE_KEYS]
            shards_a = sorted(p.name for p in ja.glob("*.sqlite"))
            shards_b = sorted(p.name for p in jb.glob("*.sqlite"))
            shards = {}
            for s in sorted(set(shards_a) | set(shards_b)):
                if s not in shards_a or s not in shards_b:
                    shards[s] = {"identical": False, "differences": [{"what": "shard missing on one side"}]}
                else:
                    shards[s] = compare_dbs(ja / s, jb / s)
                print(f"{name:20s} {s:42s} identical={shards[s]['identical']}", flush=True)
            ident = not phys and all(v["identical"] for v in shards.values()) and shards_a == shards_b
            all_identical &= ident
            result["jobs"][name] = {
                "identical": ident,
                "file_url_a": ma.get("file_url"), "file_url_b": mb.get("file_url"),
                "git_commit_a": ma.get("git_commit"), "git_commit_b": mb.get("git_commit"),
                "cutflow_a": {k: ma.get(k) for k in CUTFLOW_KEYS},
                "cutflow_b": {k: mb.get(k) for k in CUTFLOW_KEYS},
                "n_labels_inclusive": len(ma.get("final_state_label_event_counts_inclusive", {})),
                "metadata_physics_differences": phys,
                "metadata_provenance_differences": [d["path"] for d in prov],
                "n_metadata_leaves_compared": _count_leaves(ma),
                "shards": shards,
            }
    result["all_identical"] = all_identical
    Path(args.out).write_text(json.dumps(result, indent=2, default=str))
    print(f"ALL IDENTICAL: {all_identical}  -> {args.out}")


def _count_leaves(x) -> int:
    if isinstance(x, dict):
        return sum(_count_leaves(v) for v in x.values())
    if isinstance(x, list):
        return sum(_count_leaves(v) for v in x) or 1
    return 1


# --------------------------------------------------------------- delivery
def _read_root(path: Path) -> dict:
    import uproot
    out = {}
    with uproot.open(path) as f:
        for key in f.keys(cycle=False):
            h = f[key]
            out[key] = {
                "edges": h.axis().edges(flow=False),
                "values": h.values(flow=True),
                "variances": h.variances(flow=True),
                "entries": float(h.member("fEntries")),
                "title": h.member("fTitle"),
            }
    return out


def cmd_delivery(args):
    da, db = Path(args.a), Path(args.b)
    result = {"a": str(da), "b": str(db), "root_files": {}, "json_files": {}}
    all_identical = True
    for suffix in ("_bumpnet.root", "_bumpnet_cropped.root"):
        pa, pb = da / f"{args.prefix}{suffix}", db / f"{args.prefix}{suffix}"
        ha, hb = _read_root(pa), _read_root(pb)
        diffs = []
        only_a, only_b = sorted(set(ha) - set(hb)), sorted(set(hb) - set(ha))
        if only_a or only_b:
            diffs.append({"what": "names", "only_a": only_a[:50], "only_b": only_b[:50]})
        n_bins = 0
        for name in sorted(set(ha) & set(hb)):
            x, y = ha[name], hb[name]
            n_bins += x["values"].size
            for field in ("edges", "values", "variances"):
                if x[field].shape != y[field].shape or x[field].tobytes() != y[field].tobytes():
                    diffs.append({"what": field, "histogram": name})
            for field in ("entries", "title"):
                if x[field] != y[field]:
                    diffs.append({"what": field, "histogram": name, "a": x[field], "b": y[field]})
        ident = not diffs
        all_identical &= ident
        result["root_files"][suffix] = {
            "identical": ident, "n_histograms_a": len(ha), "n_histograms_b": len(hb),
            "n_bins_compared": n_bins,
            "total_entries_a": sum(h["values"].sum() for h in ha.values()),
            "total_entries_b": sum(h["values"].sum() for h in hb.values()),
            "differences": diffs[:200]}
        print(f"{suffix:24s} histograms {len(ha)} vs {len(hb)}  identical={ident}")
    for name in (f"build_summary_rare4_four_dataset.json", f"manifest_{args.prefix}.json"):
        # Output/run directory paths legitimately differ between the two
        # sides; replace them by placeholders before comparing.
        ta = (da / name).read_text().replace(str(da), "<OUT>").replace(args.a_runs, "<RUNS>")
        tb = (db / name).read_text().replace(str(db), "<OUT>").replace(args.b_runs, "<RUNS>")
        n_path = (da / name).read_text().count(str(da)) + (da / name).read_text().count(args.a_runs)
        other = json_diff(json.loads(ta), json.loads(tb))
        all_identical &= not other
        result["json_files"][name] = {"identical_except_paths": not other,
                                      "n_path_mentions_normalised": n_path, "differences": other[:100]}
        print(f"{name:60s} identical_except_paths={not other}")
    result["all_identical"] = all_identical
    Path(args.out).write_text(json.dumps(result, indent=2, default=float))
    print(f"ALL IDENTICAL: {all_identical}  -> {args.out}")


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("inputs")
    s.add_argument("--full-runs-dir", required=True)
    s.add_argument("--out-dir", required=True)
    s.add_argument("--sides", default="old,new")
    s = sub.add_parser("runs")
    s.add_argument("--a", required=True)
    s.add_argument("--b", required=True)
    s.add_argument("--out", required=True)
    s = sub.add_parser("delivery")
    s.add_argument("--a", required=True)
    s.add_argument("--b", required=True)
    s.add_argument("--a-runs", required=True, help="side A's runs dir (path fields may mention it)")
    s.add_argument("--b-runs", required=True)
    s.add_argument("--prefix", required=True)
    s.add_argument("--out", required=True)
    args = p.parse_args()
    {"inputs": cmd_inputs, "runs": cmd_runs, "delivery": cmd_delivery}[args.cmd](args)


if __name__ == "__main__":
    main()
