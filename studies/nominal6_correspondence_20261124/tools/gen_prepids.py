#!/usr/bin/env python
"""From the saved MiniAOD records (evidence/records/), the GEN request id (McM prepid) named in the production script
and the "efficiency" line of its validation block. The generator fragment itself (where the phase-space cuts are) is
on McM and was NOT read; its public URL is listed so the technical lead can open it.

    python gen_prepids.py > evidence/gen_prepids.json
"""
import gzip
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
PREP = re.compile(r"get_fragment/([A-Za-z0-9_-]+)")
EFF = re.compile(r"According to ([0-9.]+) efficiency")


def main():
    det = json.loads((HERE / "evidence" / "record_details.json").read_text())["records"]
    out = {}
    for rid, d in sorted(det.items(), key=lambda x: int(x[0])):
        m = json.load(gzip.open(HERE / "evidence" / "records" / f"{d['mini_recid']}.json.gz", "rt"))["metadata"]
        s = json.dumps(m.get("methodology", {}))
        p, e = PREP.findall(s), EFF.findall(s)
        out[rid] = {"mini_recid": d["mini_recid"], "gen_prepid": p[0] if p else None,
                    "validation_efficiency": float(e[0]) if e else None,
                    "fragment_url": f"https://cms-pdmv-prod.web.cern.ch/mcm/public/restapi/requests/get_fragment/{p[0]}"
                    if p else None}
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
