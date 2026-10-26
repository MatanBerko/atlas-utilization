"""Build candidates.json and the per-group markdown tables of PLAN.md (26 Oct 2026).

Merges evidence/records_summary.json (portal), plan_samples.py (role, tier),
evidence/xsec_proposals.json (PROPOSED sigma_eff) and evidence/stats_cost.json.
Writes candidates.json and evidence/group_tables.md.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from plan_samples import by_recid  # noqa: E402

GROUP_TITLE = {
    "existing": "The 13 delivered samples (campaign check)",
    "a_wjets": "a. W+jets", "b_singletop": "b. Single top t- and s-channel", "c_tthad": "c. tt̄ fully hadronic",
    "d_diboson": "d. Dibosons not yet covered", "e_triboson": "e. Tribosons", "f_raretop": "f. Rare top",
    "g_higgs": "g. Higgs, other production modes and decays", "h_znunu_dy": "h. Z → νν and other Drell-Yan",
    "i_photon": "i. Photon samples (DEFERRED)", "j_qcd": "j. QCD multijet (availability only)",
}

# can the sample put events into the e-mu 0-jet histogram? (statement only, nothing computed)
EMU0J = {
    "a_wjets": "yes: W → ℓν plus a jet or photon faking the second lepton (or a non-prompt lepton)",
    "b_singletop": "t-channel/s-channel: yes, one prompt lepton + a fake; jets usually present",
    "c_tthad": "only with two fake/non-prompt leptons and lost jets; small",
}

# how each group overlaps with what we have (short; the full analysis is in PLAN.md)
ORDER_RX = (("amcatnlo", "NLO"), ("powheg", "NLO"), ("madgraphMLM", "LO"), ("madgraph", "LO"),
            ("sherpa", "NLO (0-2j) / LO"), ("pythia8", "LO"), ("comphep", "LO"), ("mcfm", "LO (loop-induced)"))


def order(name):
    n = name.lower()
    for k, v in ORDER_RX:
        if k.lower() in n:
            return v
    return "?"


def main():
    rows = json.loads((HERE / "evidence" / "records_summary.json").read_text())["rows"]
    props = {p["recid"]: p for p in json.loads((HERE / "evidence" / "xsec_proposals.json").read_text())["proposals"]}
    stats = {s["recid"]: s for s in json.loads((HERE / "evidence" / "stats_cost.json").read_text())["samples"]}
    plan = by_recid()
    out, md = [], []
    groups = {}
    for r in rows:
        groups.setdefault(r["group"], []).append(r)
    for g, rs in groups.items():
        md += [f"### {GROUP_TITLE[g]}", "",
               "| NanoAOD / MiniAOD | dataset (short) | gen. order | events | files | size GB | portal σ [pb] (filter / matching) | role |",
               "|---|---|---|---:|---:|---:|---|---|"]
        for r in rs:
            short = r["dataset"].split("/")[1].replace("_TuneCP5", "").replace("_13TeV", "")
            camp = r["dataset"].split("/")[2]
            ext = "ext1" if "_ext1" in camp else ""
            x = r["portal_cross_section"] or {}
            pl = plan.get(r["nano_recid"])
            role = f"{pl['role']} (tier {pl['tier']})" if pl and pl["role"] != "optional" else (pl["role"] if pl else ("delivered" if g == "existing" else "not proposed"))
            xs = f"{x.get('total_value')} ({x.get('filter_efficiency')} / {x.get('matching_efficiency')})" if x else "none on portal"
            md.append(f"| [{r['nano_recid']}]({r['link']}) / {r['mini_recid']} | {short}{' ' + ext if ext else ''} | {order(short)} | "
                      f"{r['number_events']:,} | {r['number_files']} | {r['size_bytes'] / 1e9:.1f} | {xs} | {role} |")
            rec = dict(r)
            rec.update(dataset_is_postVFP_NanoAODv9=bool(re.search(r"/RunIISummer20UL16NanoAODv9-106X_mcRun2_asymptotic_v17", r["dataset"])),
                       tune_CP5="CP5" in r["dataset"].split("/")[1] or "13TeV-sherpa" in r["dataset"],
                       generator_order_from_name=order(short),
                       role=pl["role"] if pl else ("delivered" if g == "existing" else "not_proposed"),
                       tier=pl["tier"] if pl else None,
                       can_contribute_to_emu_0j=EMU0J.get(g) if pl else None,
                       proposed_sigma_eff_pb=props[r["nano_recid"]]["sigma_eff_pb"] if r["nano_recid"] in props else None,
                       stats=stats.get(r["nano_recid"]))
            if g == "i_photon":
                rec["status"] = "DEFERRED: photons are not in the delivery (Itamar's branch, pending Maryna)"
            if g == "j_qcd":
                rec["status"] = "NOT on the ATLAS list; question pending with Maryna; relevant to the open e-mu 0j data/MC = 2.19 question"
            out.append(rec)
        md.append("")
    (HERE / "candidates.json").write_text(json.dumps(
        {"what": "MC expansion candidates, 2016 UL post-VFP NanoAODv9 (CERN Open Data), 26 Oct 2026. PLANNING ONLY: "
                 "proposed_sigma_eff_pb values are proposals, not decided; nothing here is in any registry.",
         "portal_fetch": "evidence/records_summary.json", "n_records": len(out), "candidates": out},
        indent=1, ensure_ascii=False) + "\n")
    (HERE / "evidence" / "group_tables.md").write_text("\n".join(md) + "\n")
    print(len(out), "records")


if __name__ == "__main__":
    main()
