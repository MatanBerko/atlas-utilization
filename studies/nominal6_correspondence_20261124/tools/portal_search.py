#!/usr/bin/env python
"""CERN Open Data portal title searches for the CMS counterparts of the Nominal-6 items (read-only, public API).

For every (item, pattern): https://opendata.cern.ch/api/records/?q=title:*<pattern>* AND RunIISummer20UL16NanoAODv9
&experiment=CMS&type=Dataset&subtype=Simulated&file_type=nanoaodsim (the query form of the 26 Oct plan, PLAN.md:91, plus
the campaign term so the result is restricted to 2016 UL NanoAODv9), up to 20 pages of 100. Each finished pattern is
cached in evidence/portal_search_cache/ so an interrupted run resumes. Every hit is kept
with its title, events and files; "ul16_postvfp" = the title contains RunIISummer20UL16NanoAODv9 (APV = pre-VFP, out).
A pattern with no post-VFP hit is "NOT OBSERVED with this pattern", not "does not exist".

    python portal_search.py > evidence/portal_searches.json
"""
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

CACHE = Path(__file__).resolve().parents[1] / "evidence" / "portal_search_cache"

SEARCH = ("https://opendata.cern.ch/api/records/?q={q}&experiment=CMS&type=Dataset&subtype=Simulated"
          "&file_type=nanoaodsim&size=100&page={page}")

PATTERNS = {
    "N1": ["JJ_EWK", "JJ_QCD", "JJTo", "JJ_INT", "_INT_", "EWK_", "VBS", "WZJJ", "ZZJJ", "WWJJ", "WpWp", "WmWm",
           "WLLJJ", "ZZTo4L_EWK", "ssWW", "SSWW"],
    "N2": ["WpWpJJ_QCD", "WmWmJJ_QCD", "SameSign", "DoubleScattering", "WWTo2L2Nu_DoubleScattering"],
    "N3": ["Dalitz", "HToMuMuG", "HToEEG", "HToLLG", "HToGG_Dalitz"],
    "N4": ["ZH_HToZZ", "HZJ_HToZZ", "ZHToZZ", "ZH_ZToAll_HToZZ"],
    "N5": ["HToZZTo2L2X", "HToZZTo2L2Q", "VBF_HToZZ", "VBFHToZZ"],
    "N6": ["ggZH", "GluGluZH", "GluGluToZH", "ZH_HToTauTau", "ZHToTauTau", "ZH_HToMuMu", "ZHToMuMu"],
    "N7": ["TTT_", "TTTJ", "TTTW", "ttt_", "TTTTo", "ThreeTop", "3top"],
    "N8": ["HToInvisible", "HToInv", "HToZZTo4Nu", "ZH_ZToLL_HToInv", "WH_WToLNu_HToInv"],
    "N9": ["tZq", "TZQ", "ST_tZ", "tZ_", "TZQB"],
    "N10": ["HToAll", "VBFH_M125", "VBFHToInclusive", "_HToAll", "ToNonbb", "VHTo", "HToNonbb", "WplusH_M125", "WminusH_M125",
            "ZH_M125", "HWplusJ_HToAll", "HZJ_HToAll", "VBFHJJ", "VBF_H_"],
    "N11": ["WGToLNuG", "ZGToLLG", "ZGTo2NuG", "ZGTo2LG", "WGJets", "ZGJets", "LNuG_", "WGTo", "ZGTo", "WG_", "ZG_",
            "ZNuNuGJets", "WGamma", "ZGamma", "ZLLGJets", "TauNuG", "TauTauG"],
    "N12": ["WGG", "ZGG", "GGG", "WGJJ", "ZGJJ", "LNuGJJ", "LLGJJ", "TriPhoton", "WGGJets", "ZGGJets"],
    "N13": ["WJetsToQQ", "ZJetsToQQ", "ZJetsToBB", "WGToQQ", "ZGToQQ", "ZGToBB", "WGToJJ", "ZGToJJ", "Zqq", "Wqq"],
    "N14": ["WZTo2Q2Nu", "WZToQQ2Nu", "WZTo2Nu2Q", "ZZTo2Q2Nu", "ZZTo2Nu2Q", "ZZTo4Nu", "ZZTo2B2Nu", "ZZToBB",
            "2Q2Nu", "2Nu2Q", "4Nu"],
    "N15": ["ST_tW", "tW_", "ST_tWch", "ST_tW_top_5f_inclusiveDecays", "ST_tW_antitop_5f_inclusiveDecays"],
    "C1": ["ST_t-channel", "ST_tch", "tchannel"],
    "C2": ["WWW", "WWZ", "WZZ", "ZZZ", "WWWTo", "WWZTo", "WZZTo", "ZZZTo", "VVV"],
}


def fetch(url):
    err = None
    for attempt in range(6):
        try:
            with urllib.request.urlopen(url, timeout=120) as r:
                return json.load(r)
        except Exception as e:  # noqa: BLE001 - retry, then report
            err = e
            time.sleep(4 * (attempt + 1))
    return {"error": repr(err)}


def search(pattern):
    q = urllib.parse.quote(f"title:*{pattern}* AND RunIISummer20UL16NanoAODv9")
    hits, page, total, errors = {}, 1, None, []
    while True:
        d = fetch(SEARCH.format(q=q, page=page))
        if "error" in d:
            errors.append(d["error"])
            break
        total = d["hits"]["total"]
        for h in d["hits"]["hits"]:
            m = h["metadata"]
            dist = m.get("distribution", {})
            t = m.get("title", "")
            hits[str(h["id"])] = {"title": t, "events": dist.get("number_events"), "files": dist.get("number_files"),
                                  "ul16_postvfp": "RunIISummer20UL16NanoAODv9" in t,
                                  "ul16_apv": "RunIISummer20UL16APVNanoAODv9" in t}
        if not d["hits"]["hits"] or len(hits) >= total or page >= 20:
            break
        page += 1
    return {"pattern": pattern, "query": SEARCH.format(q=q, page="N"), "total": total, "errors": errors,
            "n_postvfp": sum(v["ul16_postvfp"] for v in hits.values()), "hits": hits}


def main():
    jobs = [(item, p) for item, ps in PATTERNS.items() for p in ps]
    CACHE.mkdir(parents=True, exist_ok=True)

    def one(ip):
        c = CACHE / (re.sub(r"[^A-Za-z0-9_-]", "_", f"{ip[0]}__{ip[1]}") + ".json")
        if c.exists():
            return ip[0], json.loads(c.read_text())
        r = search(ip[1])
        if not r["errors"]:
            c.write_text(json.dumps(r, sort_keys=True))
        print(ip[0], r["pattern"], r["total"], r["n_postvfp"], r["errors"][:1], file=sys.stderr, flush=True)
        return ip[0], r
    with ThreadPoolExecutor(8) as ex:
        res = list(ex.map(one, jobs))
    out = {"read": time.strftime("%Y-%m-%d %H:%M %Z"), "items": {}}
    for item, r in res:
        out["items"].setdefault(item, []).append(r)
    json.dump(out, sys.stdout, indent=1, sort_keys=True)


if __name__ == "__main__":
    main()
