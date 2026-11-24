#!/usr/bin/env python
"""Maryna's Nominal-6 sheet (read in place, not committed) vs the public ATLAS metadata (2024r-pp, atlasopenmagic
1.5.0; evidence/atlas_public_metadata_2024r-pp.json). Per DSID and field: sheet value, public value, relative
difference; a field "differs" if the relative difference exceeds 0.1 % (text fields: not equal).

    python compare_sheet.py <sheet.csv> > sheet_vs_public_metadata.csv
"""
import csv
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
FIELDS = [("Physics Short", "physics_short", "text"), ("Generator", "generator", "text"),
          ("xsec [pb]", "cross_section_pb", "num"), ("k-factor", "kFactor", "num"),
          ("filter_eff", "genFiltEff", "num"), ("sumOfWeights", "sumOfWeights", "num"), ("URLs", "n_urls", "num")]


def num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def main():
    pub = json.loads((HERE / "evidence" / "atlas_public_metadata_2024r-pp.json").read_text())["records"]
    rows = [r for r in csv.DictReader(open(sys.argv[1], encoding="utf-8-sig")) if r["DSID"].strip().isdigit()]
    assert len(rows) == 246, len(rows)
    w = csv.writer(sys.stdout)
    w.writerow(["dsid", "category_sheet", "field", "sheet", "public", "rel_diff", "differs_gt_0p1pct"])
    for r in rows:
        d = r["DSID"].strip()
        p = pub.get(d, {})
        m = p.get("metadata") or {}
        for sk, pk, kind in FIELDS:
            sv = r[sk]
            pv = p.get("n_urls") if pk == "n_urls" else m.get(pk)
            if not m:
                w.writerow([d, r["Category"], sk, sv, "MISSING_IN_PUBLIC", "", True])
                continue
            if kind == "text":
                differs = (sv or "").strip() != (str(pv) if pv is not None else "").strip()
                w.writerow([d, r["Category"], sk, sv, pv, "", differs])
            else:
                a, b = num(sv), num(pv)
                if a is None or b is None:
                    w.writerow([d, r["Category"], sk, sv, pv, "", a != b])
                    continue
                rel = abs(a - b) / abs(b) if b else (0.0 if a == 0 else float("inf"))
                w.writerow([d, r["Category"], sk, sv, pv, f"{rel:.3e}", rel > 1e-3])


if __name__ == "__main__":
    main()
