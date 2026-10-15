#!/usr/bin/env python
"""
Read-only live cross-check of the v4 cross-section decisions against the CERN
Open Data portal and the RazorAnalyzer table (15 Oct 2026 task, Step 2).

For every record in sources/v4_decisions_2026-10-15.json, plus 35633:
  * fetch https://opendata.cern.ch/api/records/<nano_recid> and confirm its
    `relations` field points at the expected MiniAODSIM record;
  * fetch https://opendata.cern.ch/api/records/<mini_recid> and record
    metadata.cross_section (total_value, total_value_uncertainty,
    filter_efficiency, matching_efficiency);
  * compare total_value with the generator value quoted in the decisions.
Also fetches the RazorAnalyzer xSections.dat and confirms the two DY lines.

Nothing is changed anywhere: a mismatch is RECORDED, never acted on.

Run:  python studies/cms_mc_weights_v3/probe/portal_crosscheck.py \
          [--out studies/cms_mc_weights_v3/evidence/portal_crosscheck_20261015.json]
"""
from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import pathlib
import re
import sys
import urllib.request

STUDY_DIR = pathlib.Path(__file__).resolve().parents[1]
DECISIONS = STUDY_DIR / "sources" / "v4_decisions_2026-10-15.json"
DEFAULT_OUT = STUDY_DIR / "evidence" / "portal_crosscheck_20261015.json"
API = "https://opendata.cern.ch/api/records/{0}"
RAZOR_URL = "https://raw.githubusercontent.com/RazorCMS/RazorAnalyzer/master/data/xSections.dat"

# 35633 is excluded from the registry but cross-checked on request.
EXTRA = [{"nano_recid": 35633, "mini_recid": None,
          "physics_short": "DYJetsToLL_M-10to50_madgraphMLM (excluded)"}]

# The generator (portal) values quoted in the decision list, by MiniAODSIM
# record. These are the numbers the live portal is compared against.
QUOTED_GENERATOR_PB = {
    67800: 687.1, 67992: 687.1, 35668: 6422.0, 35630: 20480.0,
    64894: 32.45, 64838: 32.51, 72675: 11.09, 72751: 5.218,
    75588: 1.325, 68186: 0.2439, 68072: 0.2151, 37727: 28.87, 68846: 3.935,
}

RAZOR_LINES = {
    "35669": ("DYJetsToLL_M-50_TuneCUETP8M1_13TeV-amcatnloFXFX-pythia8", "1921.8*3"),
    "35631": ("DYJetsToLL_M-10to50_TuneCUETP8M1_13TeV-amcatnloFXFX-pythia8", "18610.0"),
}
RAZOR_SECTION = "#13 TeV Spring 15 MC"


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"Accept": "application/json",
                                               "User-Agent": "curl/8"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        return resp.read()


def fetch_record(recid: int) -> dict:
    return json.loads(fetch(API.format(recid)))["metadata"]


def _f(text):
    try:
        return float(text)
    except (TypeError, ValueError):
        return None


def check_razor() -> dict:
    raw = fetch(RAZOR_URL)
    lines = raw.decode("utf-8").splitlines()
    sections = [(i, ln) for i, ln in enumerate(lines, 1) if ln.startswith("#") and not ln.startswith("##")]
    out = {"url": RAZOR_URL, "sha256": hashlib.sha256(raw).hexdigest(),
           "n_lines": len(lines), "lines": {}}
    for rid, (name, value) in RAZOR_LINES.items():
        hits = [(i, ln) for i, ln in enumerate(lines, 1) if ln.split() and ln.split()[0] == name]
        entry = {"expected_tokens": [name, value], "found": []}
        for i, ln in hits:
            section = [s for (j, s) in sections if j < i]
            entry["found"].append({
                "line_number": i,
                "line_verbatim": ln,
                "tokens": ln.split(),
                "tokens_match": ln.split() == [name, value],
                "under_section": section[-1] if section else None,
            })
        entry["verdict"] = ("MATCH" if len(hits) == 1 and entry["found"][0]["tokens_match"]
                            and entry["found"][0]["under_section"] == RAZOR_SECTION
                            else "MISMATCH")
        out["lines"][rid] = entry
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    args = ap.parse_args()

    decisions = json.loads(DECISIONS.read_text(encoding="utf-8"))["records"]
    rows = []
    for dec in decisions + EXTRA:
        nano = int(dec["nano_recid"])
        meta_n = fetch_record(nano)
        rel = [r.get("recid") for r in meta_n.get("relations", [])]
        expected_mini = dec.get("mini_recid")
        mini = int(expected_mini) if expected_mini is not None else (int(rel[0]) if len(rel) == 1 else None)
        row = {
            "nano_recid": nano,
            "physics_short": dec.get("physics_short"),
            "nano_title": meta_n.get("title"),
            "relations": meta_n.get("relations"),
            "expected_mini_recid": expected_mini,
            "relation_points_to_expected_mini": (expected_mini is not None and rel == [str(expected_mini)]),
        }
        if mini is not None:
            meta_m = fetch_record(mini)
            xs = meta_m.get("cross_section")
            row["mini_recid"] = mini
            row["mini_title"] = meta_m.get("title")
            row["cross_section_raw"] = xs
            if xs:
                row["total_value_pb"] = _f(xs.get("total_value"))
                row["total_value_uncertainty_pb"] = _f(xs.get("total_value_uncertainty"))
                row["filter_efficiency"] = _f(xs.get("filter_efficiency"))
                row["matching_efficiency"] = _f(xs.get("matching_efficiency"))
            quoted = QUOTED_GENERATOR_PB.get(mini)
            row["quoted_generator_pb"] = quoted
            if quoted is not None:
                tv = row.get("total_value_pb")
                row["generator_value_matches"] = (tv is not None and abs(tv - quoted) <= 1e-9 * max(1.0, quoted))
        if "cross_section_pb" in dec:
            row["decided_cross_section_pb"] = dec["cross_section_pb"]
            row["in_full_run"] = dec["in_full_run"]
        rows.append(row)

    razor = check_razor()
    mismatches = [r["nano_recid"] for r in rows
                  if (r["expected_mini_recid"] is not None and not r["relation_points_to_expected_mini"])
                  or r.get("generator_value_matches") is False]
    payload = {
        "what": "Live read-only cross-check of the v4 cross-section decisions against "
                "the CERN Open Data portal and the RazorAnalyzer table.",
        "generated_utc": _dt.datetime.now(_dt.timezone.utc).isoformat(),
        "decisions_file": "studies/cms_mc_weights_v3/sources/" + DECISIONS.name,
        "api": API,
        "records": rows,
        "razoranalyzer": razor,
        "summary": {
            "n_records_checked": len(rows),
            "records_with_relation_or_generator_mismatch": mismatches,
            "records_without_portal_cross_section": [r["nano_recid"] for r in rows
                                                     if r.get("mini_recid") and not r.get("cross_section_raw")],
            "razor_lines": {k: v["verdict"] for k, v in razor["lines"].items()},
            "matching_efficiency_by_record": {str(r["nano_recid"]): r.get("matching_efficiency") for r in rows},
            "matching_efficiency_note": "Reported only. Whether the portal total_value already "
                                        "includes the matching efficiency is an OPEN question; "
                                        "nothing was decided or changed here.",
        },
    }
    out = pathlib.Path(args.out)
    out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {out}")
    print(f"{'nano':>6} {'mini':>6} rel  {'portal pb':>10} {'quoted':>8} match  match_eff  physics")
    for r in rows:
        print(f"{r['nano_recid']:>6} {str(r.get('mini_recid')):>6} "
              f"{'ok ' if r['relation_points_to_expected_mini'] else '-- '} "
              f"{str(r.get('total_value_pb')):>10} {str(r.get('quoted_generator_pb')):>8} "
              f"{str(r.get('generator_value_matches')):>5}  {str(r.get('matching_efficiency')):>9}  "
              f"{r['physics_short']}")
    for k, v in razor["lines"].items():
        for f in v["found"]:
            print(f"razor {k}: line {f['line_number']} {f['line_verbatim']!r} "
                  f"section={f['under_section']!r} -> {v['verdict']}")
    print("mismatches:", mismatches or "none")
    return 0


if __name__ == "__main__":
    sys.exit(main())
