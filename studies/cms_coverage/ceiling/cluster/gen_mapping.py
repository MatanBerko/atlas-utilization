#!/usr/bin/env python
"""
Generate a pbs_ceiling.sh MAPPING_FILE from datasets.tsv for one
configuration. Pure text generation, no shared-code imports needed.

Usage:
    python gen_mapping.py --config-label C1 --object-set 4type \
        --max-total-objects 4 --datasets-tsv datasets.tsv \
        --exclude Tau,MET --out mapping_C1.txt
    python gen_mapping.py --config-label C2 --object-set 6type \
        --max-total-objects 4 --datasets-tsv datasets.tsv --out mapping_C2.txt
    python gen_mapping.py --config-label C5 --object-set 6type \
        --max-total-objects 4 --with-met --datasets-tsv datasets.tsv --out mapping_C5.txt
"""
from __future__ import annotations

import argparse
from pathlib import Path


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--config-label", required=True)
    p.add_argument("--object-set", required=True, choices=["4type", "6type"])
    p.add_argument("--max-total-objects", type=int, required=True)
    p.add_argument("--with-met", action="store_true")
    p.add_argument("--datasets-tsv", required=True)
    p.add_argument("--exclude", default="", help="Comma-separated dataset labels to omit.")
    p.add_argument("--out", required=True)
    args = p.parse_args()

    exclude = set(s for s in args.exclude.split(",") if s)
    rows = []
    for line in Path(args.datasets_tsv).read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        label, record_id, is_mc, trigger_paths = line.split("\t")
        if label in exclude:
            continue
        rows.append((label, record_id, is_mc, trigger_paths))

    lines = []
    for idx, (label, record_id, is_mc, trigger_paths) in enumerate(rows, start=1):
        lines.append(
            f"{idx} {record_id} {is_mc} {label} {trigger_paths} "
            f"{args.object_set} {args.max_total_objects} {1 if args.with_met else 0}"
        )
    Path(args.out).write_text("\n".join(lines) + "\n")
    print(f"[{args.config_label}] wrote {len(lines)} rows to {args.out}")


if __name__ == "__main__":
    main()
