#!/usr/bin/env python
"""
b-tag re-check (19 Oct 2026), Part 2, inside each PBS job: merge the two
runs of one file (DeepJet 0.2598 and 0.25) into the two small files that
are kept -- summary.json and nb.npz. Everything else stays in $TMPDIR.

Checks that the two runs saw the SAME accepted events in the SAME order (the
b-tag split cannot change the acceptance: the trigger matching uses no jets,
and every jet is either b or light with the same cuts, so n_j + n_b is
invariant): equal event-ID hashes, equal n_e / n_m / exclusive flags /
genWeight, equal n_j + n_b. Any mismatch is a hard error.

nb.npz: n_e, n_m, is_exclusive, [genweight], n_j_<tag>, n_b_<tag> per event.
summary.json: both runs' job_metadata essentials (counts, rare4 diagnostics
and final-state label counts) and the alignment checks.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

KEEP_META = ("dataset_label", "record_id", "file_index", "file_url", "git_commit", "elapsed_sec",
             "n_read", "n_after_golden_json", "n_after_trigger", "n_after_gate", "n_exclusive",
             "final_state_label_event_counts_inclusive", "final_state_label_event_counts_exclusive",
             "is_mc")
KEEP_RARE4 = ("n_accepted_events_before_rare4_rule", "n_rejected_gt4_lepton_bjet", "n_kept_le4_lepton_bjet",
              "final_state_label_event_counts_inclusive", "final_state_label_event_counts_exclusive")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tags", nargs=2, default=["0p2598", "0p25"])
    ap.add_argument("--work", required=True, help="dir holding cap_<tag>.npz(.json) and meta_<tag>.json")
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--job", required=True, help="mapping line, for the record")
    args = ap.parse_args()
    w = Path(args.work)
    caps = {t: dict(np.load(w / f"cap_{t}.npz")) for t in args.tags}
    capm = {t: json.loads((w / f"cap_{t}.npz.json").read_text()) for t in args.tags}
    meta = {t: json.loads((w / f"meta_{t}.json").read_text()) for t in args.tags}
    a, b = (caps[t] for t in args.tags)

    checks = {
        "event_ids_sha256_equal": capm[args.tags[0]]["event_ids_sha256"] == capm[args.tags[1]]["event_ids_sha256"]
                                  and capm[args.tags[0]]["event_ids_sha256"] is not None,
        "n_events_equal": len(a["n_b"]) == len(b["n_b"]),
    }
    if checks["n_events_equal"]:
        for k in ("n_e", "n_m", "is_exclusive", "genweight"):
            if k in a or k in b:
                checks[f"{k}_equal"] = bool(k in a and k in b and np.array_equal(a[k], b[k]))
        checks["n_j_plus_n_b_equal"] = bool(np.array_equal(a["n_j"].astype(int) + a["n_b"],
                                                           b["n_j"].astype(int) + b["n_b"]))
    bad = [k for k, v in checks.items() if not v]
    if bad:
        raise SystemExit(f"alignment checks failed: {bad}")

    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    arrays = {k: a[k] for k in ("n_e", "n_m", "is_exclusive", "genweight") if k in a}
    for t in args.tags:
        arrays[f"n_j_{t}"] = caps[t]["n_j"]
        arrays[f"n_b_{t}"] = caps[t]["n_b"]
    np.savez_compressed(out / "nb.npz", **arrays)
    summary = {"job": args.job, "tags": args.tags, "alignment_checks": checks,
               "capture": capm, "runs": {}}
    for t in args.tags:
        m = meta[t]
        r = {k: m.get(k) for k in KEEP_META}
        r["rare4"] = {k: (m.get("rare4_diagnostics") or {}).get(k) for k in KEEP_RARE4}
        summary["runs"][t] = r
    (out / "summary.json").write_text(json.dumps(summary, indent=1))
    print(f"merged {args.job}: {len(a['n_b'])} events, checks OK -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
