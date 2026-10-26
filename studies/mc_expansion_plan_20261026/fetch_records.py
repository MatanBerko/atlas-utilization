"""Fetch the CERN Open Data portal records of the MC expansion candidates (26 Oct 2026).

Research only: reads the public portal API, writes raw copies under evidence/records/
and a flat summary evidence/records_summary.json. Nothing here touches a config or a
registry. Run from the repo root:

    python3 studies/mc_expansion_plan_20261026/fetch_records.py

For every NanoAOD record: the record itself, then its MiniAOD parent (from the
"relations" field), whose metadata.cross_section holds the generator ("portal") value.
"""
from __future__ import annotations

import gzip
import json
import sys
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
REC_DIR = HERE / "evidence" / "records"
API = "https://opendata.cern.ch/api/records/{}"

# group -> list of NanoAOD record IDs found by the 26 Oct portal searches
# (evidence/portal_search_titles.json). "existing" = one of the 13 delivered samples.
CANDIDATES = {
    "existing": [67801, 67993, 35669, 35631, 64895, 64839, 72676, 72752, 75589,
                 68187, 68073, 37728, 68847],
    "a_wjets": [69747, 69745, 69545, 69547, 69549, 69551, 69715, 69717, 69719,
                69733, 69721, 69725, 69729, 69731, 69735, 69723, 69727,
                69737, 69739, 69741, 69743, 69749, 69553, 69555, 69713, 69712,
                35987, 35993],
    "b_singletop": [64759, 64659, 64793, 64693, 64635, 64633, 64881, 64825,
                    64853, 64855, 64711, 64745],
    "c_tthad": [67841, 67731, 67733],
    "d_diboson": [72738, 72740, 72742, 72744, 72746, 72748, 72750, 72754,
                  75567, 75565, 75569, 75571, 75573, 75587, 75577, 75593,
                  72658, 72694, 72696, 72684, 69543, 72678,
                  40044, 40046, 40048, 40050, 40052, 40054, 40056, 40058, 40060,
                  71638, 71642, 72728, 75561, 75563, 69771, 72648],
    "e_triboson": [72702, 72701, 72698, 72712, 72711, 72718, 72762, 72761, 75601, 75600],
    "f_raretop": [68325, 64873, 68087, 68089, 68215, 68045, 68067, 67771, 68069, 68097,
                  65649, 65721, 68197, 68185, 68201, 68200, 68206, 68207, 68083, 68071,
                  67691, 67645, 67639, 67589],
    "g_higgs": [
        # ggF
        37474, 37472, 37616, 37678, 37532, 37446, 37260, 37432, 37604, 37350,
        # VBF
        68603, 68601, 68741, 68833, 68659, 68591, 68445, 68571, 68731, 68499,
        # W+H / W-H
        71227, 70383, 71161, 70317, 71213, 70369, 41877, 41873, 71305, 70461,
        41879, 41875, 71297, 70453, 71003, 70163, 71295, 70451, 71145, 70301, 71013, 70173,
        # qq -> ZH
        74314, 74300, 74384, 74440, 41915, 41914, 41911, 41963, 74684, 74116, 74682,
        74292, 74132,
        # gg -> ZH
        40096, 40095, 40090, 36595, 36611,
        # ttH (other decays), bbH, tH, VH inclusive
        67697, 67689, 67707, 32783, 32785, 32825, 69389,
    ],
    "h_znunu_dy": [74894, 74896, 74898, 74900, 74902, 74904, 74906, 74908, 74910,
                   73746, 73748, 73750, 73752, 73760, 73762, 73764, 73766, 36001,
                   35663, 35651, 35655, 35659, 35661, 35665, 35653, 35657,
                   35647, 35639, 35641, 35643, 35645,
                   35523, 35541, 35547, 35551, 35521, 35539, 35545, 35549,
                   35577, 35595, 35613, 35615, 35623, 35617, 35619, 35621, 35625,
                   35629, 35649, 35627, 35635, 35637, 35673, 35675, 35999, 35677, 35633, 35671],
    "i_photon": [36949, 36943, 36945, 36947, 36951, 36957, 36953, 36955, 36959,
                 34123, 34121, 69575, 69577, 69567, 73904, 73902, 67475, 67439, 67459, 67453],
    "j_qcd": [63164, 63186, 63204, 63222, 63238, 63154, 63174, 63192, 63216, 63228, 63232, 63146,
              63180, 63198,
              63162, 63184, 63202, 63220, 63236, 63152, 63172, 63196,
              63160, 63182, 63208, 63242, 63170, 63190,
              63132, 63087, 63111, 63119, 63127, 63140, 63079, 63095, 63103],
}


def get(recid: int) -> dict:
    err = None
    for attempt in range(5):
        try:
            with urllib.request.urlopen(API.format(recid), timeout=90) as r:
                return json.load(r)
        except Exception as e:  # network hiccup: retry, then fail loudly
            err = e
            time.sleep(3 * (attempt + 1))
    raise RuntimeError(f"record {recid}: {err}")


def save(recid: int, rec: dict) -> None:
    with gzip.open(REC_DIR / f"{recid}.json.gz", "wt") as f:
        json.dump(rec, f, sort_keys=True)


def load_or_get(recid: int) -> dict:
    p = REC_DIR / f"{recid}.json.gz"
    if p.exists():
        with gzip.open(p, "rt") as f:
            return json.load(f)
    rec = get(recid)
    save(recid, rec)
    return rec


def generators(meta: dict) -> list[str]:
    out = []
    for s in (meta.get("methodology") or {}).get("steps", []):
        out += s.get("generators", [])
    return out


def summarise(group: str, recid: int) -> dict:
    nano = load_or_get(recid)
    m = nano["metadata"]
    parents = [r for r in m.get("relations", []) if r.get("type") == "isParentOf"]
    mini_id = int(parents[0]["recid"]) if parents else None
    xs, mini_title, mini_gens = None, None, []
    if mini_id:
        mm = load_or_get(mini_id)["metadata"]
        xs, mini_title, mini_gens = mm.get("cross_section"), mm.get("title"), generators(mm)
    d = m.get("distribution", {})
    return {
        "group": group,
        "nano_recid": recid,
        "mini_recid": mini_id,
        "dataset": m["title"],
        "mini_dataset": mini_title,
        "generators": mini_gens or generators(m),
        "number_events": d.get("number_events"),
        "number_files": d.get("number_files"),
        "size_bytes": d.get("size"),
        "portal_cross_section": xs,
        "link": f"https://opendata.cern.ch/record/{recid}",
        "mini_api": f"https://opendata.cern.ch/api/records/{mini_id}" if mini_id else None,
    }


def main() -> int:
    REC_DIR.mkdir(parents=True, exist_ok=True)
    rows = []
    for group, ids in CANDIDATES.items():
        for rid in ids:
            rows.append(summarise(group, rid))
            print(group, rid, rows[-1]["dataset"].split("/")[1], file=sys.stderr)
    out = {
        "what": "Portal metadata of the MC expansion candidates; raw API copies in evidence/records/",
        "fetched": time.strftime("%Y-%m-%d %H:%M %Z"),
        "api": API,
        "rows": rows,
    }
    (HERE / "evidence" / "records_summary.json").write_text(json.dumps(out, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
