#!/usr/bin/env python
"""Write studies/cms_mc_weights_v3/sources/v5_decisions_2026-11-03.json (task A1, 3 Nov 2026).

The decisions file records Matan's FINAL cross sections of 3 Nov 2026 (his by-hand review of
studies/mc_expansion_plan_20261026/XSEC_PROPOSALS_v2.md, plan branch commit 25d6423, plus his
later decisions: EW V+2 jets dropped (E2), Z->nunu method (c), 40062 estimate). Every
`cross_section_pb` below is the value Matan listed, typed in as given; the factors are recorded
so tests/test_registry_v4.py can recompute each value. Dataset titles and MiniAOD record IDs are
read from the saved portal copies in sources/mcexp_20261103/records/ (copied from the plan
branch, commit 25d6423). Deterministic; run once:

    python studies/mc_expansion_20261103/make_v5_decisions.py
"""
from __future__ import annotations

import gzip
import json
import pathlib

REPO = pathlib.Path(__file__).resolve().parents[2]
SRC = REPO / "studies" / "cms_mc_weights_v3" / "sources"
REC = SRC / "mcexp_20261103" / "records"
OUT = SRC / "v5_decisions_2026-11-03.json"
PLAN_COMMIT = "25d64230c9375c5403b88c1c8afa15e991e87a97"

VM = "VERIFIED BY MATAN (review completed 3 Nov 2026)"
TL = "technical-lead saved copy, live check pending"
EST = "ESTIMATE"

S = {  # source key -> (citation, location, url)
    "PORTAL": ("CERN Open Data MiniAOD record (generator cross section)", "metadata.cross_section.total_value", None),
    "RAZOR_W": ("RazorAnalyzer data/xSections.dat (SECONDARY source)", "line 64: WJetsToLNu_TuneCUETP8M1_13TeV-amcatnloFXFX-pythia8 61526.7",
                "https://raw.githubusercontent.com/RazorCMS/RazorAnalyzer/master/data/xSections.dat"),
    "RAZOR_DY": ("RazorAnalyzer data/xSections.dat (SECONDARY source; the value our delivered DY M-50 uses)", "line 90: DYJetsToLL_M-50 ... 1921.8*3",
                 "https://raw.githubusercontent.com/RazorCMS/RazorAnalyzer/master/data/xSections.dat"),
    "ST_T": ("LHC Top WG SingleTopRefXsec (Hathor NLO)", "section 'Single-top t channel cross sections (superseded)', 13 TeV, rows top 136.02 / anti-top 80.95",
             "https://twiki.cern.ch/twiki/bin/view/LHCPhysics/SingleTopRefXsec"),
    "ST_S": ("LHC Top WG SingleTopRefXsec (Hathor NLO)", "section 'Single-top s channel cross sections', 13 TeV, row top + anti-top 10.32",
             "https://twiki.cern.ch/twiki/bin/view/LHCPhysics/SingleTopRefXsec"),
    "PDG_W": ("PDG live, W boson", "W DECAY MODES: e nu 10.71 %, mu nu 10.63 %, tau nu 11.38 %, hadrons 67.41 %",
              "https://pdglive.lbl.gov/Particle.action?node=S043"),
    "PDG_Z": ("PDG live, Z boson", "Z DECAY MODES: ee 3.3632 %, mumu 3.3662 %, tautau 3.3696 %, invisible 20.000 %",
              "https://pdglive.lbl.gov/Particle.action?node=S044"),
    "TTBAR": ("LHC Top WG TtbarNNLO", "table 'Updated reference cross sections' (July 2022), 13 TeV, central value 833.9",
              "https://twiki.cern.ch/twiki/bin/view/LHCPhysics/TtbarNNLO"),
    "WZ": ("arXiv:1604.08576", "Table 1, 13 TeV: sigma_NLO 46.068, sigma_NNLO 51.11 pb", "https://arxiv.org/abs/1604.08576"),
    "ZZ": ("arXiv:1405.2219", "Table 1, 13 TeV: sigma_NLO 14.51, sigma_NNLO 16.91 pb", "https://arxiv.org/abs/1405.2219"),
    "WW": ("arXiv:1408.5243", "Table I, 13 TeV: sigma_NNLO 118.7 pb", "https://arxiv.org/abs/1408.5243"),
    "TTTT": ("arXiv:1711.02116", "Table 5, mu = HT/4, column 'LO + NLO': 11.97 fb", "https://arxiv.org/abs/1711.02116"),
    "YR4_XS": ("LHC Higgs WG YR4, 13 TeV", "mH = 125.00: ggF 48.58, VBF 3.782, W+H 0.8400, W-H 0.5328, ZH 'all but gg->ZH' 0.7612, gg->ZH 0.1227 pb",
               "https://twiki.cern.ch/twiki/bin/view/LHCPhysics/CERNYellowReportPageAt13TeV"),
    "YR4_BR": ("LHC Higgs WG YR4 branching ratios", "MH = 125.00: bb 0.5824, tautau 0.06272, mumu 2.176e-4, WW 0.2137, ZZ 0.02619, Zgamma 1.533e-3, H->4l (l=e,mu,tau) 2.745e-4",
               "https://twiki.cern.ch/twiki/bin/view/LHCPhysics/CERNYellowReportPageBR"),
    "EPS40062": ("plan XSEC_PROPOSALS_v2.md card 54, option (c) (ESTIMATE)", f"plan branch commit {PLAN_COMMIT}: eps = 1 - (1 - 0.10099)^2, P(at least one of the two other Zs -> ll); filter efficiency not published",
                 "studies/mc_expansion_plan_20261026/XSEC_PROPOSALS_v2.md"),
}

K_W = 61526.7 / (53300 + 8958 + 3330)
K_WZ = 51.11 / 46.068
K_ZZ = 16.91 / 14.51
K_ZNN = 5765.4 / 5396
W_L, W_H = 0.1071 + 0.1063 + 0.1138, 0.6741
Z_LL, Z_LL_EM, Z_NN = 0.10099, 0.067294, 0.2000
EPS = 1 - (1 - 0.10099) ** 2


def F(name, value, src, status=VM, record=None):
    cit, loc, url = S[src]
    if src == "PORTAL":
        url = f"https://opendata.cern.ch/record/{record}"
        cit = f"CERN Open Data MiniAOD record {record} (generator cross section)"
    return {"name": name, "value": value, "source": {"citation": cit, "location": loc, "url": url}, "verification": status}


def gen(mini, v, status=VM):
    return F("generator cross section (portal)", v, "PORTAL", status, mini)


# (nano, tier, value as listed by Matan, construction, factor builder(mini) -> [factors], order, extra)
def entries():
    E = []

    def add(nano, tier, value, construction, factors, order, **extra):
        E.append(dict(nano=nano, tier=tier, value=value, construction=construction, factors=factors, order=order, extra=extra))

    # ---- tier 1
    for nano, v, g in ((69715, 49999.6, 53300.0), (69717, 8403.3, 8958.0), (69719, 3123.8, 3330.0)):
        add(nano, 1, v, f"{g:g} x 61526.7 / (53300 + 8958 + 3330)",
            lambda m, g=g: [gen(m, g, TL), F("k = 61526.7 / (53300 + 8958 + 3330) (W NNLO inclusive / sum of the three NLO pieces)", K_W, "RAZOR_W")],
            "NLO generator x NNLO/NLO k-factor",
            verification=TL + " for the three portal values (5.330e+04 / 8.958e+03 / 3.330e+03); 61526.7 " + VM,
            note="Each jet piece used alone, no stitching (D1). k uses all three portal values, so all three carry the live-check-pending note.")
    add(64759, 1, 136.02, "136.02 (Hathor NLO, t-channel top)", lambda m: [F("sigma(t-channel top)", 136.02, "ST_T")], "NLO (Hathor)")
    add(64659, 1, 80.95, "80.95 (Hathor NLO, t-channel antitop)", lambda m: [F("sigma(t-channel antitop)", 80.95, "ST_T")], "NLO (Hathor)")
    add(64635, 1, 3.3767, "10.32 x 0.3272", lambda m: [F("sigma(s-channel, top + antitop)", 10.32, "ST_S"), F("BR(W -> l nu), l = e, mu, tau", W_L, "PDG_W")], "NLO (Hathor) x BR")
    add(67841, 1, 378.93, "833.9 x 0.6741^2", lambda m: [F("sigma(ttbar) NNLO+NNLL", 833.9, "TTBAR"), F("BR(W -> hadrons)^2", W_H ** 2, "PDG_W")], "NNLO+NNLL x BR")
    # ---- tier 2
    for nano, v, g in ((72742, 7.1326, 6.429), (72738, 10.161, 9.159), (72740, 3.7888, 3.415)):
        add(nano, 2, v, f"{g:g} x (51.11 / 46.068)", lambda m, g=g: [gen(m, g), F("k = 51.11 / 46.068 (WZ NNLO/NLO)", K_WZ, "WZ")], "NLO generator x NNLO/NLO k-factor",
            note="E1: ATLAS uses Sherpa generator values with kFactor 1 (no gg -> VV samples).")
    add(75573, 2, 4.3108, "3.699 x (16.91 / 14.51)", lambda m: [gen(m, 3.699), F("k = 16.91 / 14.51 (ZZ NNLO/NLO, includes gg -> ZZ)", K_ZZ, "ZZ")], "NLO generator x NNLO/NLO k-factor",
        note="E1.")
    add(72658, 2, 52.362, "118.7 x 2 x 0.3272 x 0.6741", lambda m: [F("sigma(WW) NNLO", 118.7, "WW"), F("2 x BR(W -> l nu) x BR(W -> hadrons)", 2 * W_L * W_H, "PDG_W")], "NNLO x BR",
        note="E1.")
    add(75567, 2, 1.1349, "0.9738 x (16.91 / 14.51)", lambda m: [gen(m, 0.9738), F("k = 16.91 / 14.51 (ZZ NNLO/NLO)", K_ZZ, "ZZ")], "NLO generator x NNLO/NLO k-factor",
        note=f"D14, confirmed by the 3 Nov LHE check (R2 = 0.967; studies/mc_expansion_plan_20261026/zz2l2nu_check/RESULT.md, plan commit {PLAN_COMMIT}). Was in v3's deliberately_excluded_records (15 Oct); moved into the registry by D14. E1.")
    # ---- tier 3
    for nano, v in ((72701, 0.2158), (72711, 0.1707), (72761, 0.05709), (75600, 0.01476)):
        add(nano, 3, v, f"{v:g} (generator NLO)", lambda m, v=v: [gen(m, v)], "NLO (generator)", note="D10: ext1 record only.")
    # ---- tier 4
    add(67645, 4, 0.29534, "0.5071 x 0.5824", lambda m: [F("sigma(ttH)", 0.5071, "YR4_XS"), F("BR(H -> bb)", 0.5824, "YR4_BR")], "NLO QCD + NLO EW (YR4) x BR")
    add(67691, 4, 0.21176, "0.5071 x (1 - 0.5824)", lambda m: [F("sigma(ttH)", 0.5071, "YR4_XS"), F("1 - BR(H -> bb)", 1 - 0.5824, "YR4_BR")], "NLO QCD + NLO EW (YR4) x BR")
    add(68083, 4, 0.4375, "0.4375 (generator NLO)", lambda m: [gen(m, 0.4375)], "NLO (generator)", note="Portal matching efficiency 0.6 shown, not applied.")
    add(68045, 4, 0.01197, "11.97 fb (complete NLO QCD+EW)", lambda m: [F("sigma(tttt) [11.97 fb]", 0.01197, "TTTT")], "complete NLO QCD+EW", note="D7; ATLAS 412043 = 12.03 fb.")
    for nano, v in ((68325, 0.07561), (64873, 0.01105), (68206, 0.5113), (68185, 0.0537)):
        add(nano, 4, v, f"{v:g} (generator, as proposed 26 Oct; NOT reviewed for use)", lambda m, v=v: [gen(m, v, "ON HOLD: not reviewed for use")], "generator",
            on_hold=True, verification="ON HOLD (no ATLAS nominal counterpart; waiting for Maryna) -- value not for use",
            not_in_full_run_reason="ON HOLD (Matan, 31 Oct 2026): no ATLAS nominal counterpart; waiting for Maryna.")
    # ---- tier 5
    G, VBF, WP, WM, QZ, GZ = 48.58, 3.782, 0.8400, 0.5328, 0.7612, 0.1227
    BWW, BTT, BZZ, B4L, BMM, BZG = 0.2137, 0.06272, 0.02619, 2.745e-4, 2.176e-4, 1.533e-3
    P = lambda name, v: F(name, v, "YR4_XS")
    B = lambda name, v: F(name, v, "YR4_BR")
    WLL2 = F("BR(W -> l nu)^2, l = e, mu, tau", W_L ** 2, "PDG_W")
    higgs = [
        (37474, 1.11145, [P("sigma(ggF)", G), B("BR(H -> WW)", BWW), WLL2]),
        (68601, 0.0865272, [P("sigma(VBF)", VBF), B("BR(H -> WW)", BWW), WLL2]),
        (41877, 0.179508, [P("sigma(W+H)", WP), B("BR(H -> WW)", BWW)]),
        (41873, 0.113859, [P("sigma(W-H)", WM), B("BR(H -> WW)", BWW)]),
        (41914, 0.162668, [P("sigma(ZH, all but gg->ZH)", QZ), B("BR(H -> WW)", BWW)]),
        (40095, 0.00264806, [P("sigma(gg->ZH)", GZ), B("BR(H -> WW)", BWW), F("BR(Z -> ll), l = e, mu, tau", Z_LL, "PDG_Z")]),
        (37446, 3.04694, [P("sigma(ggF)", G), B("BR(H -> tautau)", BTT)]),
        (68591, 0.237207, [P("sigma(VBF)", VBF), B("BR(H -> tautau)", BTT)]),
        (71297, 0.0526848, [P("sigma(W+H)", WP), B("BR(H -> tautau)", BTT)]),
        (70453, 0.0334172, [P("sigma(W-H)", WM), B("BR(H -> tautau)", BTT)]),
        (74684, 0.0477425, [P("sigma(ZH, all but gg->ZH)", QZ), B("BR(H -> tautau)", BTT)]),
        (37616, 0.0342475, [P("sigma(ggF)", G), B("BR(H -> ZZ)", BZZ), F("2 x BR(Z -> ee + mumu) x BR(Z -> nunu)", 2 * Z_LL_EM * Z_NN, "PDG_Z")]),
        (68741, 0.0026662, [P("sigma(VBF)", VBF), B("BR(H -> ZZ)", BZZ), F("2 x BR(Z -> ee + mumu) x BR(Z -> nunu)", 2 * Z_LL_EM * Z_NN, "PDG_Z")]),
        (71227, 0.00023058, [P("sigma(W+H)", WP), B("BR(H -> ZZ -> 4l), l = e, mu, tau", B4L)]),
        (70383, 0.000146254, [P("sigma(W-H)", WM), B("BR(H -> ZZ -> 4l), l = e, mu, tau", B4L)]),
        (37432, 0.010571, [P("sigma(ggF)", G), B("BR(H -> mumu)", BMM)]),
        (68571, 0.000822963, [P("sigma(VBF)", VBF), B("BR(H -> mumu)", BMM)]),
        (71295, 0.000182784, [P("sigma(W+H)", WP), B("BR(H -> mumu)", BMM)]),
        (70451, 0.000115937, [P("sigma(W-H)", WM), B("BR(H -> mumu)", BMM)]),
        (74682, 0.000165637, [P("sigma(ZH, all but gg->ZH)", QZ), B("BR(H -> mumu)", BMM)]),
        (37604, 0.00752104, [P("sigma(ggF)", G), B("BR(H -> Zgamma)", BZG), F("BR(Z -> ll), l = e, mu, tau", Z_LL, "PDG_Z")]),
        (68731, 0.00058552, [P("sigma(VBF)", VBF), B("BR(H -> Zgamma)", BZG), F("BR(Z -> ll), l = e, mu, tau", Z_LL, "PDG_Z")]),
        (71145, 0.00128772, [P("sigma(W+H)", WP), B("BR(H -> Zgamma)", BZG)]),
        (70301, 0.000816782, [P("sigma(W-H)", WM), B("BR(H -> Zgamma)", BZG)]),
        (74292, 0.00116692, [P("sigma(ZH, all but gg->ZH)", QZ), B("BR(H -> Zgamma)", BZG)]),
    ]
    for nano, v, fac in higgs:
        add(nano, 5, v, " x ".join(f"{f['value']:.6g}" for f in fac), lambda m, fac=fac: fac, "YR4 production x YR4 BR (x PDG W/Z BR)")
    add(40062, 5, 6.22392e-05, "0.1227 x 0.02619 x 0.10099 x eps, eps = 1 - (1 - 0.10099)^2 = 0.19178",
        lambda m: [P("sigma(gg->ZH)", GZ), B("BR(H -> ZZ)", BZZ), F("BR(Z -> ll), l = e, mu, tau", Z_LL, "PDG_Z"),
                   F("eps(4-lepton filter), ESTIMATED", EPS, "EPS40062", EST)],
        "LO (JHUGen gg->ZH) normalised to YR4 x BR x estimated filter efficiency",
        estimate=True, verification=EST + " (filter efficiency not published; the portal value 2.330e-4 pb of MiniAOD 40061 is NOT used)",
        note="4-lepton-filtered sample (JHUGen FilterNLept=4). The delivery README must state this ESTIMATE.")
    # ---- tier 6
    for nano, v, g in ((74894, 284.53, 266.3), (74898, 78.019, 73.02), (74902, 10.593, 9.914), (74904, 2.5739, 2.409),
                       (74906, 1.1507, 1.077), (74896, 0.26658, 0.2495), (74900, 0.0059985, 0.005614)):
        add(nano, 6, v, f"{g:g} x 5765.4 / 5396", lambda m, g=g: [
            gen(m, g), F("k = 5765.4 / 5396 (our DY NNLO normalisation, 3 x 1921.8, / LO DY M-50 madgraphMLM portal value, MiniAOD 35670)", K_ZNN, "RAZOR_DY")],
            "LO generator x NNLO/LO k-factor (from DY)", note="Z -> nunu option (c) (Matan). The 5396 is the portal value of MiniAOD 35670 (saved copy in sources/mcexp_20261103/records/35670.json.gz).")
    return E


def load(rid):
    with gzip.open(REC / f"{rid}.json.gz", "rt") as f:
        return json.load(f)["metadata"]


def generator_of(title):
    name = title.split("/")[1]
    for g in ("amcatnloFXFX", "amcatnlo", "madgraphMLM", "madgraph", "powheg2", "powheg", "jhugen", "JHUGen"):
        if g.lower() in name.lower():
            return g
    return None


def main():
    recs = []
    for e in entries():
        nano = load(e["nano"])
        mini = int([r["recid"] for r in nano["relations"] if r["type"] == "isParentOf"][0])
        title = nano["title"]
        rec = {
            "nano_recid": e["nano"], "mini_recid": mini,
            "physics_short": title.split("/")[1].replace("_TuneCP5", "").replace("_13TeV", ""),
            "generator": generator_of(title), "portal_dataset_title": title,
            "tier": e["tier"], "in_full_run": not e["extra"].get("on_hold", False),
            "cross_section_pb": e["value"], "construction": e["construction"],
            "factors": e["factors"](mini), "order": e["order"],
            "verification": e["extra"].get("verification", VM),
            "estimate": bool(e["extra"].get("estimate", False)),
            "previous_cross_section_pb": None,
        }
        for k in ("note", "not_in_full_run_reason"):
            if k in e["extra"]:
                rec[k] = e["extra"][k]
        recs.append(rec)
    out = {
        "what": "Matan's FINAL cross-section decisions for the MC expansion (3 Nov 2026). Input of build_registry_v4.py.",
        "decided": "Matan, review completed 3 Nov 2026 (XSEC_PROPOSALS_v2.md card by card + later decisions E2, Z->nunu (c), 40062 estimate)",
        "plan": f"branch plan/mc-expansion-20261026 @ {PLAN_COMMIT}: DECISIONS.md, XSEC_PROPOSALS_v2.md, PLAN_v2_summary.md, zz2l2nu_check/RESULT.md",
        "evidence_copied": "sources/mcexp_20261103/records/ (NanoAOD + MiniAOD portal records) and sources/mcexp_20261103/cards/ (generator cards), copied byte for byte from the plan branch commit above",
        "convention": "cross_section_pb = sigma_eff (all factors inside); k_factor = gen_filt_eff = 1.0 as in v3. The 15 v3 records are carried into v4 unchanged.",
        "records": recs,
        "excluded_records": {
            "35999": "E2 (Matan, 3 Nov 2026): EW Z+2 jets dropped -- double counting with the tier-2 dibosons",
            "35987": "E2: EW W-+2 jets dropped -- double counting with the tier-2 dibosons",
            "35993": "E2: EW W++2 jets dropped -- double counting with the tier-2 dibosons",
            "64793": "D4: 5-flavour t-channel top not used (4-flavour 64759 instead)",
            "64693": "D4: 5-flavour t-channel antitop not used (4-flavour 64659 instead)",
            "69745": "D1: inclusive NLO W+jets not used (would double count the 0J/1J/2J pieces)",
            "69747": "D1: inclusive LO W+jets not used (would double count the 0J/1J/2J pieces)",
            "68833": "D13: deferred Higgs extra (VBF H -> ZZ -> 2l2X)",
            "74314": "D13: deferred Higgs extra (ZH -> ZZ 4l-filtered)",
            "37420": "D13: deferred Higgs Dalitz sample", "37276": "D13: deferred Higgs Dalitz sample",
            "68559": "D13: deferred Higgs Dalitz sample", "68459": "D13: deferred Higgs Dalitz sample",
            "74670": "D13: deferred Higgs Dalitz sample", "74652": "D13: deferred Higgs Dalitz sample",
        },
        "removed_from_v3_excluded": {"75567": "D14 (31 Oct) + LHE check (3 Nov): ZZTo2L2Nu now in the registry"},
    }
    OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {OUT}: {len(recs)} records ({sum(r['in_full_run'] for r in recs)} in the full run)")


if __name__ == "__main__":
    main()
