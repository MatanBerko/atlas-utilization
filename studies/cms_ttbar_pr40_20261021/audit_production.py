#!/usr/bin/env python
"""
Production audit for the ttbar PR #40 test (record 67801, 49 files).

For every line of the mapping: runs/record<rid>/job_<fi>/ holds
job_metadata.json (written by the driver as its LAST step) and the rare4
inclusive shard; the PBS log logs/f_<array index>.err carries
/usr/bin/time's "Exit status: 0"; the metadata has the SingleElectron
acceptance bit (6, the five-flag union of 20 Oct) and passes the per-file
Sigma-w self-check; no rare4 signature was coverage-capped and no
combination was skipped (both are what make the build-time PR #40
regrouping equal to #40's own labelling, study step 1).

Read-only. Writes one JSON. Run as a PBS job (cluster/pbs_post.sh WHAT=audit).
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

SIGMA_W_TOLERANCE = 1e-6


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", required=True)
    ap.add_argument("--mapping", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    w = Path(args.work)
    rows, problems = [], []
    for line in Path(args.mapping).read_text().splitlines():
        idx, rid, fi = line.split()
        job = w / "runs" / f"record{rid}" / f"job_{fi}"
        meta_p = job / "job_metadata.json"
        err_p = w / "logs" / f"f_{idx}.err"
        row = {"array_index": int(idx), "record_id": int(rid), "file_index": int(fi),
               "metadata": meta_p.exists(),
               "rare4_shard": (job / "dataset_shard_rare4_inclusive.sqlite").exists()}
        err = err_p.read_text(errors="replace") if err_p.exists() else ""
        m = re.findall(r"Exit status: (\d+)", err)
        row["exit_status"] = int(m[-1]) if m else None
        mx = re.findall(r"Maximum resident set size \(kbytes\): (\d+)", err)
        row["max_rss_gb"] = int(mx[-1]) / 1024 ** 2 if mx else None
        if row["metadata"]:
            meta = json.loads(meta_p.read_text())
            chk = meta["mc_sigma_w_self_check"]
            r4 = meta["rare4_diagnostics"]
            row.update({
                "sigma_w_rel_diff": chk["relative_difference"],
                "sigma_w_ok": chk["relative_difference"] <= SIGMA_W_TOLERANCE,
                "singleelectron_bit": (meta.get("mc_diagnostics") or {})
                .get("acceptance_bit_map", {}).get("SingleElectron"),
                "rare4_n_capped": r4["n_capped_signatures"],
                "rare4_max_signature_size": r4["max_signature_size_this_job"],
                "rare4_skip_reasons": r4["skip_reason_totals"],
                "rare4_n_kept_events": r4["n_kept_le4_lepton_bjet"],
                "n_read": meta["n_read"],
                "git_commit": meta["git_commit"],
            })
        bad = []
        if not (row["metadata"] and row["rare4_shard"]):
            bad.append("missing output")
        if row["exit_status"] != 0:
            bad.append(f"exit status {row['exit_status']}")
        if row["metadata"]:
            if not row["sigma_w_ok"]:
                bad.append("sigma-w check")
            if row["singleelectron_bit"] != 64:
                bad.append("no SingleElectron bit")
            if row["rare4_n_capped"] or row["rare4_skip_reasons"]:
                bad.append("capped or skipped combinations")
        row["problems"] = bad
        if bad:
            problems.append(row)
        rows.append(row)
    commits = sorted({r.get("git_commit") for r in rows if r.get("git_commit")})
    out = {
        "n_files": len(rows),
        "n_ok": len(rows) - len(problems),
        "verdict": "OK" if not problems else "PROBLEMS",
        "problems": problems,
        "git_commits": commits,
        "n_events_read": sum(r.get("n_read", 0) for r in rows),
        "n_rare4_kept_events": sum(r.get("rare4_n_kept_events", 0) for r in rows),
        "max_rare4_signature_size": max((r.get("rare4_max_signature_size") or 0) for r in rows),
        "max_rss_gb": max((r["max_rss_gb"] or 0) for r in rows),
        "files": rows,
    }
    Path(args.out).write_text(json.dumps(out, indent=2))
    print(json.dumps({k: v for k, v in out.items() if k != "files"}, indent=1))
    return 0 if not problems else 1


if __name__ == "__main__":
    raise SystemExit(main())
