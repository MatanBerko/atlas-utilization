#!/usr/bin/env python
"""
Full-run preparation (17 Oct 2026), Part C: one-file smoke test of every
never-run full-run record -- the per-record table and one sanity PNG each.

Reads LOCAL COPIES of, for each record:
  runs/record<ID>/job_0/job_metadata.json   (+ a file listing with sizes)
  logs/f_<i>.out / f_<i>.err                 (/usr/bin/time -v output)
  builds/record<ID>/smoke_build_report.json + smoke_record<ID>_mc.root

and writes smoke_test_report.json and C_<ID>.png into --out-dir. The PNG is
the build's most-populated histogram (largest raw entry count), weighted.
It is a sanity look only: Sigma-w is one file's, so the vertical scale is
not physics.

Run:
    python studies/cms_mc_weights_v3/fullrun_prep/smoke_report.py \
        --local <dir holding runs/, logs/, builds/, listing.txt, mapping.txt> \
        --out-dir <dir>
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import uproot  # noqa: E402

COLOR, INK, INK2 = "#2a78d6", "#0b0b0b", "#52514e"


def parse_time_v(text: str) -> dict:
    out = {}
    m = re.search(r"Maximum resident set size \(kbytes\): (\d+)", text)
    if m:
        out["peak_rss_gb"] = int(m.group(1)) / 1024 / 1024
    m = re.search(r"Elapsed \(wall clock\) time \(h:mm:ss or m:ss\): ([\d:.]+)", text)
    if m:
        parts = [float(x) for x in m.group(1).split(":")]
        sec = 0.0
        for p in parts:
            sec = sec * 60 + p
        out["wall_seconds_time_v"] = sec
    m = re.search(r"Exit status: (\d+)", text)
    if m:
        out["exit_status"] = int(m.group(1))
    return out


def warnings_in(text: str) -> list:
    keep = []
    for line in text.splitlines():
        if re.search(r"warn|error|traceback|exception", line, re.I) and \
                "Exit status" not in line:
            keep.append(line.strip()[:240])
    # collapse repeats, keep order
    seen, uniq = set(), []
    for line in keep:
        if line not in seen:
            seen.add(line)
            uniq.append(line)
    return uniq


def most_populated_png(root_path: Path, rid: str, title_extra: str, out: Path) -> dict:
    with uproot.open(root_path) as f:
        hs = {k: f[k] for k in f.keys(cycle=False) if hasattr(f[k], "values")}
        if not hs:
            return {"png": None, "reason": "no histogram in the build output"}
        k = max(hs, key=lambda x: float(hs[x].member("fEntries")))
        h = hs[k]
        v = np.asarray(h.values(), dtype=float)
        err = np.sqrt(np.asarray(h.variances(), dtype=float))
        e = np.asarray(h.axis().edges(), dtype=float)
        entries = float(h.member("fEntries"))
    nz = np.flatnonzero(v != 0)
    lo, hi = (nz[0], nz[-1] + 1) if nz.size else (0, len(v))
    fig, ax = plt.subplots(figsize=(7.5, 4.4))
    ax.stairs(v[lo:hi], e[lo:hi + 1], color=COLOR, lw=2)
    c = 0.5 * (e[lo:hi] + e[lo + 1:hi + 1])
    ax.errorbar(c, v[lo:hi], yerr=err[lo:hi], fmt="none", ecolor=INK2, lw=0.8)
    ax.set_xlabel("mass [GeV]", color=INK)
    ax.set_ylabel("weighted events / bin (1-file normalisation)", color=INK)
    ax.set_title(f"SMOKE TEST record {rid} {title_extra}, file 0 only\n{k}  "
                 f"({entries:,.0f} raw entries; sum {v.sum():,.4g})", fontsize=8.5, color=INK)
    ax.grid(axis="y", color="#e6e6e3", lw=0.6)
    ax.tick_params(colors=INK2)
    path = out / f"C_{rid}.png"
    fig.savefig(path, dpi=130, bbox_inches="tight", facecolor="#fcfcfb")
    plt.close(fig)
    return {"png": path.name, "histogram": k, "raw_entries": entries,
            "sum_of_weights": float(v.sum()), "n_nonzero_bins": int(nz.size)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--local", required=True)
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args()
    base, out = Path(args.local), Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    registry = json.loads((Path(__file__).resolve().parents[1] /
                           "cms_mc_normalisation_v3.json").read_text())["records"]

    # listing.txt: "<size_bytes> <path relative to runs_smoke>" per file
    sizes: dict[str, list] = {}
    for line in (base / "listing.txt").read_text().splitlines():
        size, rel = line.split(maxsplit=1)
        rid = rel.split("/")[0].replace("record", "")
        sizes.setdefault(rid, []).append((rel, int(size)))

    rows = []
    for line in (base / "mapping.txt").read_text().splitlines():
        idx, rid, fidx = line.split()
        row = {"array_index": int(idx), "record": int(rid), "file_index": int(fidx),
               "physics_short": registry[rid]["physics_short"]}
        log_out = base / "logs" / f"f_{idx}.out"
        log_err = base / "logs" / f"f_{idx}.err"
        text = (log_out.read_text(errors="replace") if log_out.exists() else "") + "\n" + \
               (log_err.read_text(errors="replace") if log_err.exists() else "")
        row.update(parse_time_v(text))
        row["log_warnings_or_errors"] = warnings_in(text)
        meta_path = base / "runs" / f"record{rid}" / f"job_{fidx}" / "job_metadata.json"
        if not meta_path.exists():
            row["production_success"] = False
            row["failure"] = "no job_metadata.json (the driver writes it as its last step)"
            rows.append(row)
            continue
        meta = json.loads(meta_path.read_text())
        mc = meta.get("mc_diagnostics") or {}
        sw = meta.get("mc_sigma_w_self_check") or {}
        gw = mc.get("genweight_stored_events") or {}
        n_stored = mc.get("n_stored", meta.get("n_after_gate"))
        files = sizes.get(rid, [])
        row.update({
            "production_success": row.get("exit_status", 0) == 0,
            "git_commit": meta.get("git_commit"),
            "file_url": meta.get("file_url"),
            "events_read": meta.get("n_read"),
            "events_stored": n_stored,
            "stored_fraction": (n_stored / meta["n_read"]) if meta.get("n_read") else None,
            "stored_only_via_ele27": mc.get("n_stored_only_ele27_candidate"),
            "wall_seconds_driver": meta.get("elapsed_sec"),
            "events_per_second": (meta["n_read"] / meta["elapsed_sec"])
            if meta.get("elapsed_sec") else None,
            "n_output_files": len(files),
            "output_bytes": sum(s for _r, s in files),
            "n_final_states": meta.get("n_final_state_groups"),
            "n_capped_signatures": meta.get("n_capped_signatures"),
            "sigma_w_self_check": sw,
            "sigma_w_relative_difference": (abs(sw["file_sum_genweight"] - sw["runs_gen_event_sumw"])
                                            / abs(sw["runs_gen_event_sumw"]))
            if sw.get("runs_gen_event_sumw") else None,
            "negative_weight_fraction_stored": (gw["n_negative"] / n_stored)
            if gw.get("n_negative") is not None and n_stored else None,
            "n_negative_weight_stored": gw.get("n_negative"),
            "genweight_min_max": [gw.get("min"), gw.get("max")],
        })
        brep = base / "builds" / f"record{rid}" / "smoke_build_report.json"
        broot = base / "builds" / f"record{rid}" / f"smoke_record{rid}_mc.root"
        if brep.exists():
            b = json.loads(brep.read_text())
            s = (b.get("samples") or {}).get(rid, {})
            row["build"] = {
                "success": broot.exists(),
                "sigma_w_files_included": s.get("n_files_included"),
                "sigma_w_files_excluded": s.get("n_files_excluded"),
                "sigma_w_verdicts": [e.get("verdict") for e in s.get("per_file_sigma_w", [])],
                "normalisation_factor": s.get("normalisation_factor"),
                "n_histograms": (b.get("outputs") or {}).get("per_sample", [{}])[0].get("n_histograms")
                if isinstance((b.get("outputs") or {}).get("per_sample"), list) else None,
                "prune": {k: v for k, v in (b.get("prune") or {}).items()
                          if not isinstance(v, (list, dict))},
            }
        else:
            row["build"] = {"success": False, "reason": "no smoke_build_report.json"}
        if broot.exists():
            row["png"] = most_populated_png(broot, rid, registry[rid]["physics_short"], out)
        rows.append(row)
        print(f"{rid:>6} ok={row['production_success']} read={row['events_read']} "
              f"stored={row['events_stored']} t={row['wall_seconds_driver']:.0f}s "
              f"rss={row.get('peak_rss_gb', float('nan')):.2f}GB "
              f"files={row['n_output_files']} size={row['output_bytes']/1e6:.1f}MB "
              f"fs={row['n_final_states']} negfrac={row['negative_weight_fraction_stored']} "
              f"swrel={row['sigma_w_relative_difference']} build={row['build'].get('success')}")
    (out / "smoke_test_report.json").write_text(json.dumps({"records": rows}, indent=2, default=str))
    print(f"wrote {out / 'smoke_test_report.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
