#!/usr/bin/env python
"""Per-sample summary of the 27 Nov 2026 precheck: file 0 of each of the 14 Nominal-6 additions, run through the pinned
production code (6de9d3e, pbs_mc_pilot.sh unchanged). READ ONLY on every input.

Per record: exit status, wall time and max memory (from the /usr/bin/time block of the job's .err log), the files in
the job directory, events read / stored / in the builder's delivery union, the Sigma-w self-check, the negative
genWeight fraction of the stored events, and the events "entering a histogram" by final state (top 5).

"Enters a histogram" uses the same definition as the 7 Nov QCD probe (qcd_probe/analyze_qcd_probe.py): the event is
stored, is in the builder's union of acceptance bits (DoubleMuon|SingleMuon|DoubleEG|MuonEG|SingleElectron), and its
final state has at least one invariant-mass signature. The builder's later mass-range cuts are NOT applied (upper
bound).

The precheck-only registry (portal total_value, labelled PRECHECK ONLY) is used for ONE illustrative column: the
weighted full-sample events entering a histogram, sigma x 1000 x L x Sum genWeight(entering, file 0) / Sigma_w(file 0).
It is not a cross-section decision.

    python precheck_analysis.py --runs <W>/runs --logs <W>/logs --mapping <map> --registry <precheck registry>
        --inputs inputs_20261127.json --out <W>/evidence
"""
from __future__ import annotations

import argparse
import io
import json
import re
import sqlite3
import zlib
from collections import defaultdict
from pathlib import Path

import numpy as np

UNION_BITS = 1 | 2 | 4 | 8 | 64      # build_mc_delivery.MC_ACC_BITS_DELIVERY_UNION (driver bits), as the QCD probe
SIG_RE = re.compile(r"^MC_record(\d+)_file(\d+)_FS_(\d+)e_(\d+)m_(\d+)j_(\d+)b_IM_([a-z0-9]+)(_mcraw_[a-z0-9]+)?$")


def read_shard(path: Path) -> dict:
    con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    out = defaultdict(list)
    for sig, payload in con.execute("select signature, payload from array_chunks order by id"):
        out[sig].append(np.load(io.BytesIO(zlib.decompress(payload)), allow_pickle=False))
    con.close()
    return {k: np.concatenate(v) for k, v in out.items()}


def time_block(err: Path) -> dict:
    t = err.read_text(errors="replace") if err.exists() else ""
    g = lambda p: (re.search(p, t).group(1) if re.search(p, t) else None)  # noqa: E731
    return {"exit_status": g(r"Exit status: (\d+)"), "wall_clock": g(r"Elapsed \(wall clock\) time \(h:mm:ss or m:ss\): (\S+)"),
            "max_rss_kb": g(r"Maximum resident set size \(kbytes\): (\d+)"),
            "traceback": "Traceback" in t, "err_tail": t.strip().splitlines()[-3:] if t else None}


def main() -> int:
    ap = argparse.ArgumentParser()
    for k in ("--runs", "--logs", "--mapping", "--registry", "--inputs", "--out"):
        ap.add_argument(k, required=True)
    ap.add_argument("--lumi", type=float, default=16.393)
    a = ap.parse_args()
    reg = json.loads(Path(a.registry).read_text())
    assert reg.get("PRECHECK_ONLY") is True, "not the precheck-only registry"
    inputs = json.loads(Path(a.inputs).read_text())["records"]
    res = {"what": "Nominal-6 additions precheck, file 0 per record (VERIFIED BY RUNNING). Weighted column uses the "
                   "PRECHECK ONLY portal values: NOT a cross-section decision.", "records": {}}
    for line in Path(a.mapping).read_text().split("\n"):
        if not line.strip():
            continue
        idx, rid, fi = line.split()
        jd = Path(a.runs) / f"record{rid}" / f"job_{fi}"
        r = {"array_index": int(idx), "file_index": int(fi), "job_dir": str(jd),
             "files_in_job_dir": sorted(p.name for p in jd.iterdir()) if jd.exists() else [],
             "log": time_block(Path(a.logs) / f"f_{idx}.err")}
        mp = jd / "job_metadata.json"
        if not mp.exists():
            r["problem"] = "no job_metadata.json"
            res["records"][rid] = r
            continue
        meta = json.loads(mp.read_text())
        mcd = meta["mc_diagnostics"]
        gws = mcd["genweight_stored_events"]
        r.update({"git_commit": meta["git_commit"], "n_read": meta["n_read"], "n_after_trigger": meta["n_after_trigger"],
                  "n_stored": mcd["n_stored"], "n_stored_in_delivery_union": mcd["n_stored_in_delivery_union"],
                  "n_accepted_per_dataset": mcd["n_accepted_per_dataset"],
                  "fraction_negative_genweight_stored": gws["n_negative"] / mcd["n_stored"] if mcd["n_stored"] else None,
                  "sigma_w_self_check": meta["mc_sigma_w_self_check"], "elapsed_sec_driver": meta["elapsed_sec"],
                  "n_capped_signatures": meta.get("n_capped_signatures"),
                  "skip_reason_totals": meta.get("skip_reason_totals")})
        arrs = read_shard(jd / "dataset_shard_inclusive.sqlite")
        by_fs = defaultdict(dict)
        for sig, arr in arrs.items():
            mt = SIG_RE.match(sig)
            if mt:
                by_fs[tuple(int(x) for x in mt.group(3, 4, 5, 6))].setdefault(mt.group(7), {})[mt.group(8) or "mass"] = arr
        sw_file = meta["mc_file_sum_genweight_all_events"]
        sigma = reg["records"][rid]["cross_section_pb_PRECHECK_ONLY"]
        n_sample = inputs[rid]["portal_number_events"]
        rows = []
        for fs, ims in by_fs.items():
            rep = ims[sorted(ims)[0]]
            union = (rep["_mcraw_acc"].astype(np.int64) & UNION_BITS) != 0
            gw = rep["_mcraw_genw"][union]
            rows.append({"final_state": "{}e_{}m_{}j_{}b".format(*fs), "n_events_file0": int(union.sum()),
                         "weighted_full_sample_PRECHECK_ONLY": float(sigma * 1000 * a.lumi * gw.sum() / sw_file)})
        rows.sort(key=lambda x: -x["n_events_file0"])
        r["n_entering_a_histogram_file0"] = int(sum(x["n_events_file0"] for x in rows))
        r["n_final_states_entered"] = len(rows)
        r["top5_final_states"] = rows[:5]
        r["weighted_full_sample_entering_PRECHECK_ONLY"] = float(sum(x["weighted_full_sample_PRECHECK_ONLY"] for x in rows))
        r["typical_event_weight_PRECHECK_ONLY"] = sigma * 1000 * a.lumi / n_sample
        res["records"][rid] = r
        print(rid, r["log"]["exit_status"], r["n_read"], r["n_stored"], r["n_entering_a_histogram_file0"],
              r["sigma_w_self_check"]["passes"], f"{r['fraction_negative_genweight_stored']:.3f}", r["log"]["wall_clock"],
              r["log"]["max_rss_kb"], len(r["files_in_job_dir"]), [x["final_state"] for x in rows[:5]], flush=True)
    Path(a.out).mkdir(parents=True, exist_ok=True)
    (Path(a.out) / "precheck_analysis.json").write_text(json.dumps(res, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
