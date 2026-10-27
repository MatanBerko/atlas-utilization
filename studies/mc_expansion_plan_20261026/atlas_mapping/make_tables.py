"""Markdown tables for MAPPING.md from mapping.json / higgs_scope.json / extras_cost.json (27 Oct 2026). Research only.

Writes mapping_tables.md (process table, alternative-generator list, Higgs production x decay table, reverse check)
and reverse_check.json.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PLAN = HERE.parent
sys.path.insert(0, str(PLAN))
from plan_samples import SAMPLES  # noqa: E402

M = json.loads((HERE / "mapping.json").read_text())
HS = json.loads((HERE / "higgs_scope.json").read_text())
META = json.loads((HERE / "atlas_bkg_metadata.json").read_text())["datasets"]
REG = json.loads((PLAN.parents[1] / "studies/cms_mc_weights_v3/cms_mc_normalisation_v3.json").read_text())

STATUS = {"delivered": "in the 25-26 Oct delivery", "proposed": "proposed in the plan",
          "portal": "exists on the CMS portal, not proposed", "none": "no CMS 2016 sample found",
          "out_of_scope": "out of scope"}

# one-line notes for the reverse check (CMS samples with no ATLAS counterpart in Maryna's list)
REVERSE_NOTE = {
    37616: "ggF H → ZZ → 2ℓ2ν: ATLAS list has ggF H → ZZ → 4ν and → 4ℓ but no 2ℓ2ν; a genuine lepton background, cheap (2 files)",
    68741: "VBF H → ZZ → 2ℓ2ν: no ATLAS counterpart (ATLAS has VBF ZZ → 4ℓ and → ℓℓbb only); 21 files",
    68185: "tt̄ + ℓℓ with 1 < m(ℓℓ) < 10 GeV: ATLAS tt̄ee/μμ/ττ state no m(ℓℓ) threshold in the metadata, so whether "
           "they cover it is UNKNOWN",
    69745: "W+jets inclusive NLO: alternative only (D1 decided the jet-binned set)",
    69747: "W+jets inclusive LO: alternative only (D1 decided)",
    64759: "t-channel 4-flavour: alternative for D4; ATLAS uses Powheg t-channel (flavour scheme not stated in the metadata)",
    64659: "t-channel 4-flavour antitop: as 64759",
    64633: "s-channel hadronic (optional): ATLAS has leptonic s-channel only",
    72678: "WW double-parton scattering (optional): no ATLAS counterpart",
    68071: "tt̄W EWK (optional): ATLAS tt̄W (aMC@NLO 410155 / Sherpa 700000) — whether the EW part is inside is UNKNOWN",
    37678: "ggF H → ZZ → 2ℓ2q (optional): no ATLAS counterpart",
    71003: "W+H → bb, W → ℓν (optional): ATLAS has VH → bb only with Z → νν",
    70163: "W−H → bb, W → ℓν (optional): as 71003",
    74116: "ZH → bb, Z → ℓℓ (optional): as 71003",
    36595: "gg → ZH → bb, Z → ℓℓ (optional): as 71003",
    32783: "bb̄H inclusive (optional): no bb̄H in the ATLAS list",
    37532: "ggF H → WW → ℓνqq (optional): ATLAS has H → WW → ℓνqq only in qq̄ → ZH (Z → νν)",
}


def fmt(x):
    if x is None:
        return "—"
    return f"{x:.4g}"


def main():
    L = []
    rows = M["rows"]
    L.append("## A. One row per ATLAS process\n")
    L.append("ATLAS σ = Σ cross_section_pb × kFactor × genFiltEff over the **nominal** DSIDs (atlasopenmagic 2024r-pp), "
             "CROSS-CHECK only. CMS σ_eff: registry v3 for delivered samples, `evidence/xsec_proposals.json` for proposed "
             "ones (PROPOSED, not decided). Ratio = ATLAS / CMS; ⚑ = outside 0.7-1.4. ATLAS files = number of file URLs "
             "(`atom.get_urls(dsid)`), nominal DSIDs only. All values VERIFIED BY RUNNING (`mapping.py`).\n")
    for cat in ["V+jets", "diboson", "triboson", "top", "Higgs", "photon", "QCD", "BSM"]:
        sel = [r for r in rows if r["category"] == cat]
        if not sel:
            continue
        L.append(f"\n### {cat} ({len(sel)} processes)\n")
        L.append("| ATLAS process | ATLAS DSIDs (nominal) | files | ATLAS σ×k×filter [pb] | CMS status | CMS records | CMS σ_eff [pb] | ATLAS/CMS | note |")
        L.append("|---|---|---:|---:|---|---|---:|---:|---|")
        for r in sel:
            recs = ", ".join(f"{c['recid']}" + (f" (T{c['plan_tier']})" if c["plan_tier"] and c["plan_tier"] < 9 else
                                                " (opt.)" if c["plan_role"] == "optional" else "") for c in r["cms_records"]) or "—"
            ds = r["atlas_nominal_dsids"]
            dtxt = ", ".join(ds) if len(ds) <= 4 else f"{ds[0]}–{ds[-1]} ({len(ds)})"
            ratio = r["ratio_atlas_over_cms"]
            rtxt = "—" if ratio is None else (f"**{ratio:.2f}** ⚑" if r["ratio_flag"] else f"{ratio:.2f}")
            note = "; ".join(x for x in [r["ratio_note"], r["note"], r["slicing"]] if x)
            if r["atlas_subset_dsids"]:
                note += f" (+{len(r['atlas_subset_dsids'])} subset DSIDs)"
            L.append(f"| {r['process']} | {dtxt} | {r['atlas_files_nominal']} | {fmt(r['atlas_sigma_nominal_pb_CROSSCHECK'])} | "
                     f"{STATUS[r['cms_status']]} | {recs} | {fmt(r['cms_sigma_eff_pb'])} | {rtxt} | {note} |")
    L.append("\nLike-for-like checks for the flagged single-top ratios (W → ℓν = 0.3272, W → hadrons = 0.6741, settled PDG values):\n")
    for k, v in M["like_for_like_checks"].items():
        L.append(f"- {k}: **{v:.3f}**")

    # alternatives
    L.append("\n## B. ATLAS alternative generators for the same process (ATLAS-side double counting is their business)\n")
    L.append("Listed for Maryna: mixing a nominal and an alternative set would count the process twice on the ATLAS side.\n")
    L.append("| ATLAS process | nominal DSIDs (files) | alternative | DSIDs | files |")
    L.append("|---|---|---|---|---:|")
    nalt = 0
    for r in rows:
        for lab, ds in r["atlas_alternatives"].items():
            nalt += len(ds)
            dtxt = ", ".join(ds) if len(ds) <= 4 else f"{ds[0]}–{ds[-1]} ({len(ds)})"
            L.append(f"| {r['process']} | {', '.join(r['atlas_nominal_dsids'][:4])}{' …' if len(r['atlas_nominal_dsids']) > 4 else ''} "
                     f"({r['atlas_files_nominal']}) | {lab} | {dtxt} | {r['atlas_files_alternatives'][lab]} |")
    nsub = sum(len(r["atlas_subset_dsids"]) for r in rows)
    L.append(f"\n{nalt} DSIDs are alternatives and {nsub} are decay/filter subsets of another listed DSID "
             "(tW dilepton, tt̄H by decay; see notes in table A). Also: the V+jets b/c-filter splits and the pT/mass/JZ "
             "slices are exclusive pieces of one sample and are NOT double counting.\n")

    # Higgs table
    L.append("\n## C. Higgs: ATLAS production × decay vs CMS (input to D13)\n")
    L.append("Cell = ATLAS nominal DSIDs → CMS. ● delivered, ◆ proposed (tier 4/5), ○ on the CMS portal, not proposed, "
             "✗ no CMS 2016 sample found, — not in the ATLAS list, (oos) out of scope.\n")
    prods = ["ggF", "VBF", "W±H", "qq̄ → ZH", "gg → ZH", "tt̄H", "tHq (tHjb)", "tWH"]
    sym = {"delivered": "●", "proposed": "◆", "portal": "○", "none": "✗", "out_of_scope": "(oos)"}
    cells = HS["cells"]
    decs = []
    for c in cells:
        if c["decay"] not in decs:
            decs.append(c["decay"])
    L.append("| decay ↓ / production → | " + " | ".join(prods) + " |")
    L.append("|---|" + "---|" * len(prods))
    for d in decs:
        line = [d]
        for p in prods:
            cs = [c for c in cells if c["production"] == p and c["decay"] == d]
            if not cs:
                line.append("—")
            else:
                c = cs[0]
                recs = ",".join(str(x["recid"]) for x in c["cms_records"])
                line.append(f"{sym[c['cms_status']]} {','.join(c['atlas_dsids'])}" + (f" → {recs}" if recs else ""))
        L.append("| " + " | ".join(line) + " |")
    L.append("")
    L.append("Cost of adding CMS samples for the cells marked ○ (ESTIMATES, PLAN §4 method: files × 6014/497 + 2240/13 per "
             "sample cluster files; CPU at the delivered ggH → 4ℓ rate):\n")
    L.append("| group | cells | samples | portal files | events | cluster files | CPU h |")
    L.append("|---|---|---:|---:|---:|---:|---:|")
    for g, v in HS["cost_by_group"].items():
        L.append(f"| {g} | {', '.join(v['cells'])} | {v['samples']} | {v['files']} | {v['events']/1e6:.1f} M | {v['cluster_files']:,} | {v['cpu_hours']:.1f} |")
    a = HS["cost_all_remaining_cells_with_a_cms_sample"]
    L.append(f"| **all ○ cells** | | {a['samples']} | {a['files']} | {a['events']/1e6:.1f} M | {a['cluster_files']:,} | {a['cpu_hours']:.1f} |")
    t5 = HS["plan_tier5_cost"]
    L.append(f"| (for scale: plan tier 5) | 15 proposed | {t5['samples']} | {t5['files']} | | {t5['cluster_files']:,} | {t5['cpu_hours']:.1f} |")

    # reverse check
    referenced = {c["recid"] for r in rows for c in r["cms_records"]}
    plan = [(r, n, t, role) for r, n, g, t, role in SAMPLES]
    delivered = [int(k) for k in REG["full_run_records"]]
    rev = []
    for r in delivered:
        if r not in referenced:
            rev.append(dict(recid=r, name="delivered", note="UNEXPECTED: delivered sample not mapped"))
    for r, n, t, role in plan:
        if r not in referenced:
            rev.append(dict(recid=r, name=n, tier=t, role=role, note=REVERSE_NOTE.get(r, "UNKNOWN — no note written")))
    (HERE / "reverse_check.json").write_text(json.dumps(rev, indent=1, ensure_ascii=False) + "\n")
    L.append("\n## D. Reverse check: CMS samples (delivered or in the plan) with no ATLAS counterpart in Maryna's list\n")
    L.append("| CMS record | sample | plan tier / role | note |")
    L.append("|---|---|---|---|")
    for x in rev:
        L.append(f"| {x['recid']} | {x['name']} | {x.get('tier', '—') if x.get('tier', 9) < 9 else '—'} / {x.get('role', 'delivered')} | {x['note']} |")
    L.append("\nAll 13 delivered samples have an ATLAS counterpart." if not any(x["name"] == "delivered" for x in rev) else "")
    (HERE / "mapping_tables.md").write_text("\n".join(L) + "\n")
    print(len(L), "lines;", len(rev), "reverse-check rows; alternatives", nalt, "subsets", nsub)
    for x in rev:
        print(x)


if __name__ == "__main__":
    main()
