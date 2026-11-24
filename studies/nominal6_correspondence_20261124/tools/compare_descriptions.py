#!/usr/bin/env python
"""Description column of Maryna's Nominal-6 sheet (read in place, not committed) vs the public ATLAS metadata
"description" (2024r-pp). Only the DSIDs where the two texts differ (after trimming whitespace) are written.

    python compare_descriptions.py <sheet.csv> > sheet_description_vs_public.csv
"""
import csv
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]


def main():
    pub = json.loads((HERE / "evidence" / "atlas_public_metadata_2024r-pp.json").read_text())["records"]
    rows = [r for r in csv.DictReader(open(sys.argv[1], encoding="utf-8-sig")) if r["DSID"].strip().isdigit()]
    w = csv.writer(sys.stdout)
    w.writerow(["dsid", "category_sheet", "physics_short_public", "description_sheet", "description_public"])
    n = 0
    for r in rows:
        m = pub[r["DSID"].strip()]["metadata"]
        s, p = " ".join((r["Description"] or "").split()), " ".join((m.get("description") or "").split())
        if s != p:
            w.writerow([r["DSID"].strip(), r["Category"], m.get("physics_short"), s, p])
            n += 1
    print(f"{n} of {len(rows)} descriptions differ", file=sys.stderr)


if __name__ == "__main__":
    main()
