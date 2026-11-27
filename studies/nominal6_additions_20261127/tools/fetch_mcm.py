#!/usr/bin/env python
"""Read-only: for each NanoAOD record id, the CERN Open Data NanoAOD + MiniAOD records (saved raw), the GEN request id
(McM prepid) named in the MiniAOD production script, and from the public McM REST API the request JSON and the
generator fragment of that GEN request. Where the fragment names a genproductions card directory ("Link to cards"),
the public cards in it are read from GitHub too.

    python fetch_mcm.py <recid> [<recid> ...] > evidence/mcm_index.json

Saved: evidence/records/<recid>.json.gz, evidence/mcm/<prepid>.request.json, evidence/mcm/<prepid>.fragment.py,
evidence/mcm/cards/<prepid>/<card>. Already-saved files are reused (no re-fetch).
"""
import gzip
import json
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
REC = HERE / "evidence" / "records"
MCM = HERE / "evidence" / "mcm"
OD = "https://opendata.cern.ch/api/records/{}"
MCM_GET = "https://cms-pdmv-prod.web.cern.ch/mcm/public/restapi/requests/get/{}"
MCM_FRAG = "https://cms-pdmv-prod.web.cern.ch/mcm/public/restapi/requests/get_fragment/{}"
GH_API = "https://api.github.com/repos/cms-sw/genproductions/contents/{}?ref={}"
PREP = re.compile(r"get_fragment/([A-Za-z0-9_-]+)")
CARDS = re.compile(r"https://(?:raw\.)?github(?:usercontent)?\.com/cms-sw/genproductions/(?:tree/|blob/)?([^/\s]+)/(\S+)")


def get(url, binary=False):
    err = None
    for attempt in range(5):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "atlas-utilization-research"})
            with urllib.request.urlopen(req, timeout=120) as r:
                b = r.read()
                return b if binary else b.decode()
        except urllib.error.HTTPError as e:
            if e.code in (403, 404):
                raise RuntimeError(f"{url}: HTTP {e.code}")
            err = e
        except Exception as e:  # noqa: BLE001
            err = e
        time.sleep(4 * (attempt + 1))
    raise RuntimeError(f"{url}: {err}")


def cached(path, url):
    if path.exists():
        return path.read_text()
    txt = get(url)
    if path.suffix == ".py" and txt.startswith('"'):
        txt = json.loads(txt)  # McM returns the fragment as a JSON string to non-curl clients
    path.write_text(txt)
    return txt


def record(recid):
    p = REC / f"{recid}.json.gz"
    if p.exists():
        with gzip.open(p, "rt") as f:
            return json.load(f)
    rec = json.loads(get(OD.format(recid)))
    with gzip.open(p, "wt") as f:
        json.dump(rec, f, sort_keys=True)
    return rec


def cards(prepid, frag):
    out = []
    for branch, path in CARDS.findall(frag):
        path = path.rstrip("/").rstrip(".").rstrip("'\",)")
        d = MCM / "cards" / prepid
        d.mkdir(parents=True, exist_ok=True)
        try:
            listing = json.loads(get(GH_API.format(path, branch)))
        except RuntimeError as e:
            out.append({"link": f"{branch}/{path}", "error": str(e)})
            continue
        if isinstance(listing, dict):
            listing = [listing]
        for item in listing:
            if item.get("type") != "file" or not item.get("download_url"):
                continue
            (d / item["name"]).write_text(get(item["download_url"]))
            out.append({"link": f"{branch}/{path}", "file": item["name"], "url": item["download_url"]})
    return out


def one(recid):
    m = record(recid)["metadata"]
    par = [r for r in m.get("relations", []) if r.get("type") == "isParentOf"]
    mini = int(par[0]["recid"]) if par else None
    mm = record(mini)["metadata"] if mini else {}
    p = PREP.findall(json.dumps(mm.get("methodology", {})))
    res = {"nano_recid": int(recid), "mini_recid": mini, "title": m.get("title"), "gen_prepid": p[0] if p else None,
           "portal_cross_section": mm.get("cross_section")}
    if not p:
        return res
    pid = p[0]
    res["request_url"], res["fragment_url"] = MCM_GET.format(pid), MCM_FRAG.format(pid)
    req = json.loads(cached(MCM / f"{pid}.request.json", MCM_GET.format(pid))).get("results", {})
    frag = cached(MCM / f"{pid}.fragment.py", MCM_FRAG.format(pid))
    gp = (req.get("generator_parameters") or [{}])[-1]
    res.update({"mcm_dataset_name": req.get("dataset_name"), "mcm_generators": req.get("generators"),
                "mcm_cross_section_pb": gp.get("cross_section"), "mcm_filter_efficiency": gp.get("filter_efficiency"),
                "mcm_match_efficiency": gp.get("match_efficiency"), "mcm_negative_weights_fraction":
                gp.get("negative_weights_fraction"), "mcm_generator_parameters_all": req.get("generator_parameters"),
                "mcm_notes": req.get("notes"), "mcm_member_of_chain": req.get("member_of_chain")})
    cdir = MCM / "cards" / pid / "_index.json"
    if cdir.exists():
        res["cards"] = json.loads(cdir.read_text())
    else:
        res["cards"] = cards(pid, frag)
        cdir.parent.mkdir(parents=True, exist_ok=True)
        cdir.write_text(json.dumps(res["cards"], indent=1))
    return res


def main():
    REC.mkdir(parents=True, exist_ok=True)
    MCM.mkdir(parents=True, exist_ok=True)
    out = {"read": time.strftime("%Y-%m-%d %H:%M %Z"), "records": {}}
    for r in sys.argv[1:]:
        try:
            out["records"][r] = one(r)
        except RuntimeError as e:
            out["records"][r] = {"nano_recid": int(r), "error": str(e)}
        d = out["records"][r]
        print(r, d.get("gen_prepid"), d.get("mcm_cross_section_pb"), d.get("mcm_filter_efficiency"),
              len(d.get("cards") or []), d.get("error", ""), file=sys.stderr, flush=True)
    json.dump(out, sys.stdout, indent=1, sort_keys=True)


if __name__ == "__main__":
    main()
