#!/usr/bin/env python
"""
Old vs new sigma_eff for every record of the v4 decisions (arithmetic only,
no cluster re-run). "Old" is the registry as committed on
feature/cms-mc-on-master-20261014 (5906dcf), read with `git show`; "new" is
the registry in the working tree.

Run:  python studies/cms_mc_weights_v3/probe/xsec_old_vs_new.py \
          [--old-commit 5906dcf] \
          [--out studies/cms_mc_weights_v3/evidence/xsec_old_vs_new_20261015.json]
"""
from __future__ import annotations

import argparse
import json
import pathlib
import subprocess
import sys

STUDY_DIR = pathlib.Path(__file__).resolve().parents[1]
REPO_ROOT = STUDY_DIR.parents[1]
REGISTRY_REL = "studies/cms_mc_weights_v3/cms_mc_normalisation_v3.json"
DEFAULT_OUT = STUDY_DIR / "evidence" / "xsec_old_vs_new_20261015.json"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--old-commit", default="5906dcf")
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    args = ap.parse_args()

    old_commit = subprocess.run(["git", "rev-parse", args.old_commit], cwd=REPO_ROOT,
                                capture_output=True, text=True, check=True).stdout.strip()
    old = json.loads(subprocess.run(["git", "show", f"{old_commit}:{REGISTRY_REL}"], cwd=REPO_ROOT,
                                    capture_output=True, text=True, check=True).stdout)["records"]
    new = json.loads((REPO_ROOT / REGISTRY_REL).read_text(encoding="utf-8"))["records"]

    rows = []
    for rid in sorted(new, key=int):
        n = new[rid]
        o = old.get(rid)
        old_x = o["cross_section_pb"] if o else None
        new_x = n["cross_section_pb"]
        rows.append({
            "record": int(rid),
            "physics_short": n["physics_short"],
            "in_full_run": n["in_full_run"],
            "old_sigma_eff_pb": old_x,
            "new_sigma_eff_pb": new_x,
            "ratio_new_over_old": (new_x / old_x) if old_x else None,
            "note": None if o else "not in the old registry (was excluded)",
        })
    payload = {
        "what": "sigma_eff old vs new, per record. Arithmetic only; no cluster re-run.",
        "old": f"{REGISTRY_REL} at {old_commit}",
        "new": f"{REGISTRY_REL} (v4 decisions, 15 Oct 2026)",
        "records": rows,
    }
    pathlib.Path(args.out).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {args.out}")
    print(f"{'record':>6}  {'physics':<40} {'full run':<8} {'old pb':>10} {'new pb':>10} {'new/old':>8}")
    for r in rows:
        ratio = f"{r['ratio_new_over_old']:.4f}" if r["ratio_new_over_old"] else "new"
        print(f"{r['record']:>6}  {r['physics_short']:<40} {str(r['in_full_run']):<8} "
              f"{str(r['old_sigma_eff_pb']):>10} {r['new_sigma_eff_pb']:>10} {ratio:>8}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
