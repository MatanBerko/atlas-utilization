"""CMS records needed by the ATLAS mapping that the 26 Oct plan did not fetch (27 Oct 2026). Research only.

For each dataset short name: the public CERN Open Data search
  https://opendata.cern.ch/api/records/?q=title:*<name>*&experiment=CMS&type=Dataset&subtype=Simulated&file_type=nanoaodsim
keeping only titles '/<name>_TuneCP5_13TeV...' (or '/<name>_13TeV...', '/<name>-...') of RunIISummer20UL16NanoAODv9
(post-VFP, no APV). Then the NanoAOD record and its MiniAOD parent (portal cross section).
Raw copies go to cms_records/<recid>.json.gz; the summary to cms_extra_records.json.
A name with no matching title is recorded as NOT OBSERVED (not "does not exist").
"""
import gzip
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "cms_records"
SEARCH = ("https://opendata.cern.ch/api/records/?q={q}&experiment=CMS&type=Dataset&subtype=Simulated"
          "&file_type=nanoaodsim&size=100")
API = "https://opendata.cern.ch/api/records/{}"

# (short name, ATLAS process key it is looked up for)
NAMES = [
    # V -> qq at high pT, VV -> qq nu nu
    ("WJetsToQQ_HT-200to400", "W->qq' (pT>200)"), ("WJetsToQQ_HT-400to600", "W->qq' (pT>200)"),
    ("WJetsToQQ_HT-600to800", "W->qq' (pT>200)"), ("WJetsToQQ_HT-800toInf", "W->qq' (pT>200)"),
    ("ZJetsToQQ_HT-200to400", "Z->qq (pT>200)"), ("ZJetsToQQ_HT-400to600", "Z->qq (pT>200)"),
    ("ZJetsToQQ_HT-600to800", "Z->qq (pT>200)"), ("ZJetsToQQ_HT-800toInf", "Z->qq (pT>200)"),
    ("ZJetsToBB", "Z->bb (pT>200)"), ("WZTo2Q2Nu", "WZ->qq nu nu"), ("WZToQQ2Nu", "WZ->qq nu nu"),
    ("ZZTo4Nu", "ZZ->4nu"),
    # Higgs cells the plan did not fetch
    ("ZH_HToBB_ZToNuNu_M-125", "qqZH H->bb Z->nunu"), ("ggZH_HToBB_ZToNuNu_M-125", "ggZH H->bb Z->nunu"),
    ("ZH_HToCC_ZToNuNu_M-125", "qqZH H->cc Z->nunu"), ("ggZH_HToCC_ZToNuNu_M-125", "ggZH H->cc Z->nunu"),
    ("VHToEE_M125", "VH H->ee"),
    ("GluGluHToMuMuG_M125_Dalitz_012j", "ggF H->gamma* gamma"), ("GluGluHToEEG_M125_Dalitz_012j", "ggF H->gamma* gamma"),
    ("VBFHToMuMuG_M125_Dalitz", "VBF H->gamma* gamma"), ("VBFHToEEG_M125_Dalitz", "VBF H->gamma* gamma"),
    ("ZHToMuMuG_M125_Dalitz_012j", "ZH H->gamma* gamma"), ("ZHToEEG_M125_Dalitz_012j", "ZH H->gamma* gamma"),
    ("WplusHToMuMuG_M125_Dalitz", "WH H->gamma* gamma"), ("WminusHToMuMuG_M125_Dalitz", "WH H->gamma* gamma"),
    ("GluGluHToZZTo4Nu", "ggF H->ZZ->4nu"),
    ("WplusH_WToQQ_HToInvisible_M125", "WH H->inv"), ("WminusH_WToQQ_HToInvisible_M125", "WH H->inv"),
    ("ZH_ZToQQ_HToInvisible_M125", "qqZH H->inv"), ("ggZH_ZToQQ_HToInvisible_M125", "ggZH H->inv"),
    ("ttH_HToInvisible_M125", "ttH H->inv"),
    ("ttHToGG_M125", "ttH H->gamma gamma"), ("THQ_ctcvcp_HToGG", "tHq H->gamma gamma"),
    ("ggZH_HToGG_ZToNuNu_M125", "ggZH H->gamma gamma"), ("ggZH_HToGG_ZToQQ_M125", "ggZH H->gamma gamma"),
    ("ZH_HToBB_ZToQQ_M-125", "qqZH H->bb"),
    ("GluGluZH_HToZZ", "ggZH H->ZZ->4l"), ("ggZH_HToZZ", "ggZH H->ZZ->4l"),
    ("ggZH_HToTauTau", "ggZH H->tautau"), ("GluGluZH_HToTauTau", "ggZH H->tautau"),
    ("ggZH_HToMuMu", "ggZH H->mumu"), ("GluGluZH_HToMuMu", "ggZH H->mumu"),
    ("GluGluZH_HToWW_M-125", "ggZH H->WW (Z incl)"),
    # found afterwards in the plan's saved search titles (evidence/portal_search_titles.json)
    ("GluGluToZH_HToZZTo4L_M125", "ggZH H->ZZ->4l"), ("ttHJetToGG_M125", "ttH H->gamma gamma"),
    ("THQ_ctcvcp_HToGG_M125", "tHq H->gamma gamma"), ("THW_ctcvcp_HToGG_M125", "tWH H->gamma gamma"),
]


def fetch(url):
    err = None
    for attempt in range(5):
        try:
            with urllib.request.urlopen(url, timeout=90) as r:
                return json.load(r)
        except Exception as e:  # noqa: BLE001 - retry, then fail loudly
            err = e
            time.sleep(3 * (attempt + 1))
    raise RuntimeError(f"{url}: {err}")


def record(recid):
    p = OUT / f"{recid}.json.gz"
    if p.exists():
        with gzip.open(p, "rt") as f:
            return json.load(f)
    rec = fetch(API.format(recid))
    with gzip.open(p, "wt") as f:
        json.dump(rec, f, sort_keys=True)
    return rec


def main():
    OUT.mkdir(exist_ok=True)
    rows = []
    for name, atlas_proc in NAMES:
        q = urllib.parse.quote(f"title:*{name}*")
        url = SEARCH.format(q=q)
        hits = fetch(url)["hits"]["hits"]
        rx = re.compile(r"^/" + re.escape(name) + r"(_TuneCP5|_CP5|_13TeV|-)[^/]*/RunIISummer20UL16NanoAODv9-106X_mcRun2_asymptotic_v17")
        keep = [h for h in hits if rx.match(h["metadata"]["title"]) and "TuneCP5Up" not in h["metadata"]["title"]
                and "TuneCP5Down" not in h["metadata"]["title"]]
        if not keep:
            rows.append(dict(name=name, atlas_process=atlas_proc, search=url, status="NOT OBSERVED"))
            continue
        for h in keep:
            rid = int(h["id"])
            m = record(rid)["metadata"]
            par = [r for r in m.get("relations", []) if r.get("type") == "isParentOf"]
            mini = int(par[0]["recid"]) if par else None
            xs = record(mini)["metadata"].get("cross_section") if mini else None
            d = m.get("distribution", {})
            rows.append(dict(name=name, atlas_process=atlas_proc, search=url, status="found", nano_recid=rid,
                             mini_recid=mini, dataset=m["title"], number_events=d.get("number_events"),
                             number_files=d.get("number_files"), size_bytes=d.get("size"),
                             portal_cross_section=xs, link=f"https://opendata.cern.ch/record/{rid}"))
        print(name, len(keep), file=sys.stderr)
    (HERE / "cms_extra_records.json").write_text(json.dumps(
        {"what": "CMS 2016 post-VFP NanoAODv9 records looked up for the ATLAS mapping (27 Oct 2026); VERIFIED BY RUNNING "
                 "(public CERN Open Data API, URL per row)", "rows": rows}, indent=1) + "\n")
    for r in rows:
        print(r["status"], r["name"], r.get("nano_recid"), r.get("dataset", "")[:90], r.get("number_events"),
              r.get("number_files"), (r.get("portal_cross_section") or {}).get("total_value"))


if __name__ == "__main__":
    main()
