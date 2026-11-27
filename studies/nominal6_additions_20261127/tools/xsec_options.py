#!/usr/bin/env python
"""Cross-section OPTIONS for the 14 Nominal-6 additions, side by side (Part B3). NOTHING here is adopted: every row is
an option with its source, for Matan's hand check. Inputs (all saved in this folder):
  evidence/mcm_index.json            portal MiniAOD cross_section block + McM generator_parameters (fetch_mcm.py)
  evidence/theory/*.html, *.txt      YR4 twiki pages (read 27 Nov 2026), CMS-HIG-17-007 and ATLAS arXiv:2103.10322 text
  ../nominal6_correspondence_20261124/evidence/atlas_public_metadata_2024r-pp.json   ATLAS sigma, kFactor, genFiltEff
Writes evidence/xsec_options.json and evidence/xsec_tables.md (markdown tables pasted into REPORT.md).

    python tools/xsec_options.py
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
IDX = json.loads((HERE / "evidence" / "mcm_index.json").read_text())["records"]
ATL = json.loads((HERE.parents[0] / "nominal6_correspondence_20261124" / "evidence" /
                  "atlas_public_metadata_2024r-pp.json").read_text())["records"]

YR4 = "https://twiki.cern.ch/twiki/bin/view/LHCPhysics/CERNYellowReportPageAt13TeV"
YR4BR = "https://twiki.cern.ch/twiki/bin/view/LHCPhysics/CERNYellowReportPageBR"
PDGZ = "https://pdglive.lbl.gov/Particle.action?node=S044"
# VERIFIED: read 27 Nov 2026 from the saved pages evidence/theory/CERNYellowReportPage{At13TeV,BR}.html, rows 125.00
SIG = {"ggF": 48.58, "VBF": 3.782, "W+H": 0.8400, "W-H": 0.5328, "WH": 0.8400 + 0.5328, "qqZH": 0.8839 - 0.1227,
       "ZH_total": 0.8839, "ggZH": 0.1227}
BR = {"ZZ": 0.02619, "Zgam": 1.533e-3, "gamgam": 2.270e-3, "4l_emt": 2.745e-4, "4l_em": 1.240e-4}
# PDG Z (decision D6, re-read 31 Oct 2026; VERIFIED BY MATAN 3 Nov in v5): ee, mumu, tautau
BRZ = {"ee": 0.033632, "mumu": 0.033662, "tautau": 0.033696}
BRZ_ll = sum(BRZ.values())   # 0.10099
DALITZ = {  # published H -> l l gamma branching fractions with an m_ll cut (primary experimental papers)
    "CMS_MCFM_mumu_lt50": (3.83e-5, "CMS-HIG-17-007, arXiv:1806.05996, Eq. (1) and text: B(H->gamma*gamma->mumugamma) = "
                           "3.83e-5 from MCFM 7.0.1; the paper separates H->gamma*gamma from H->Zgamma at m_ll = 50 GeV "
                           "(the cut is stated in the text around Eq. (1), not next to the number: INTERPRETATION)"),
    "ATLAS_Py8_ee_lt30": (7.20e-5, "ATLAS arXiv:2103.10322 Sect. 3: B(H->eegamma) = 7.20e-5 estimated with Pythia 8 for "
                          "m_ll < 30 GeV (an ATLAS MC estimate, not a theory calculation; agrees with Refs. [74,76] "
                          "within 3 % 'when extrapolated to a common phase space')"),
    "ATLAS_Py8_mumu_lt30": (3.42e-5, "ATLAS arXiv:2103.10322 Sect. 3: B(H->mumugamma) = 3.42e-5, Pythia 8, m_ll < 30 GeV"),
}


def portal(r):
    xs = IDX[str(r)]["portal_cross_section"]
    return {k: (float(v) if k != "matching_efficiency" else float(v)) for k, v in xs.items()}


def mcm(r):
    x = IDX[str(r)]
    return {"cross_section_pb": x["mcm_cross_section_pb"], "filter_efficiency": x["mcm_filter_efficiency"],
            "match_efficiency": x["mcm_match_efficiency"], "prepid": x["gen_prepid"], "url": x["request_url"]}


def atlas(dsids):
    out, tot = [], 0.0
    for d in dsids:
        m = ATL[str(d)]["metadata"]
        v = m["cross_section_pb"] * m["kFactor"] * m["genFiltEff"]
        tot += v
        out.append({"dsid": d, "physics_short": m["physics_short"], "sigma_pb": m["cross_section_pb"],
                    "kFactor": m["kFactor"], "genFiltEff": m["genFiltEff"], "sigma_eff_pb": v})
    return out, tot


S = {}
GEN = json.loads((HERE / "evidence" / "precheck" / "gen_check.json").read_text())["records"]


def GEN_FRAC(rid):
    f = GEN[str(rid)]["m_ll_fractions_weighted"]
    fl = next(iter(f))
    return f"{f[fl]['50-130'] + f[fl]['>130']:.3f} ({fl}; 80-100 GeV: {f[fl]['80-100']:.3f})"


def add(rid, item, label, r1, theory, v5_analogue, atlas_dsids, notes):
    p = portal(rid)
    a, at = atlas(atlas_dsids)
    S[str(rid)] = {"item": item, "label": label, "mini_recid": IDX[str(rid)]["mini_recid"],
                   "dataset": IDX[str(rid)]["mcm_dataset_name"], "portal": p,
                   "portal_url": f"https://opendata.cern.ch/record/{IDX[str(rid)]['mini_recid']}",
                   "r1": r1, "mcm": mcm(rid), "theory_options": theory, "v5_analogue": v5_analogue,
                   "atlas": a, "atlas_sigma_eff_pb": at,
                   "cms_portal_over_atlas": p["total_value"] / at if at else None, "notes": notes}


# ---------------- N1 / N2: decays in the MadGraph matrix element (decay chain), so R1 applies fully ----------------
R1_ME = ("Decay inside the MadGraph matrix element (process card decay chain `v > l v`); no separate decay step, no "
         "filter (fragment filterEfficiency 1.0), no matching (ickkw 0): R1 applies, the portal total_value is the "
         "complete generator cross section of the sample.")
V5_VV = ("Dibosons (E1): generator x NNLO/NLO k-factor (WZ, ZZ) or NNLO total x BR (WW); tribosons 72701/72711 and "
         "ttZ/ttW: generator NLO value as is. No EW VV+2j precedent: E2 dropped the EW V+2j samples (35999/35987/35993) "
         "before any value was chosen.")
NO_THEORY_VBS = [{"option": "none found for the generator phase space",
                  "note": "CMS measured EW VBS in fiducial regions with reconstruction-like cuts (e.g. EW ZZjj 0.33 fb, "
                          "SM 0.275 fb, arXiv:2008.07013 abstract; EW W+W-jj 10.2 fb, SM 9.1 fb, arXiv:2205.05711 "
                          "abstract). These are NOT the generator phase space of the samples (m_jj > 100 GeV, "
                          "|eta_l| < 3 at generator level), so they cannot be used directly; no NLO calculation for "
                          "the generator phase space was found."}]
add(75561, "N1", "ZZjj -> 4l EW (no top)", R1_ME, NO_THEORY_VBS, V5_VV, [700587, 700591],
    "CMS card (gridpack): p p > z z j j $ t t~ QED=4 QCD=0, z > l+ l- (l = e mu tau), on-shell Z decay chain (bwcutoff 15); m_jj > 100, "
    "|eta_l| < 3, |eta_j| < 5, pT_j > 10 GeV. ATLAS Sherpa: off-shell 4 charged leptons + 2 jets, m_ll > 0.25/0.46/3.8 GeV "
    "(ee/mumu/tautau), pT_l > 5, 2 jets pT > 15, NO m_jj cut, 0,1j@LO merged; incl. gamma* and triboson-like diagrams. "
    "McM 7.1654e-4 pb differs from the portal 9.928e-4 pb (factor 1.39; unexplained).")
add(69771, "N1", "WZjj EW, W -> l nu, Z -> ll", R1_ME, NO_THEORY_VBS, V5_VV, [700588, 700592],
    "CMS card READ FROM THE GRIDPACK (evidence/gridpack_cards/69771/InputCards): p p > w+- z j j QED=4 QCD=0, z > l+ l-, "
    "w > l v, with NO '$ t t~' top exclusion (the genproductions master card is the _notop variant, NOT the one used); "
    "file 0: a top quark in 2,304 of 3,712 events (62 %), i.e. tZq-like diagrams are inside (overlap with our tZq 68325). "
    "m_jj > 100, |eta_l| < 3, bwcutoff 20. ATLAS lllvjj: off-shell, no m_jj cut, b quarks not in the jet container "
    "(MASSIVE[5]). McM 0.01654 pb is 0.46 x the portal 0.03566 pb (unexplained).")
add(72648, "N1", "W+W-jj EW (no top), both W -> l nu", R1_ME, NO_THEORY_VBS, V5_VV, [700589, 700593],
    "CMS card (gridpack = linked card): p p > w+ w- j j $ t t~ QED=4 QCD=0, w > l v; m_jj > 100, no eta cuts, "
    "dR(jj, ll, jl) > 0.4; file 0: a Higgs boson in 1,252 of 100,000 events (1.3 %, s-channel H->WW inside). ATLAS llvvjj_os: ALL opposite-sign l l nu nu (also ZZ -> ll nunu and non-resonant), no m_jj cut.")
add(71636, "N1", "W+-W+-jj EW (no top), same sign", R1_ME, NO_THEORY_VBS, V5_VV, [700590, 700594],
    "CMS card (gridpack = genproductions card): BOTH w+w+jj AND w-w-jj "
    "(so W-W- is inside, correcting the 24 Nov 'no separate W-W-'), m_jj > 100, |eta_l| < 3. ATLAS llvvjj_ss: off-shell, "
    "pT_l > 5, no m_jj cut.")
add(71640, "N2", "W+-W+-jj QCD (no top), same sign", R1_ME,
    [{"option": "none found for the generator phase space", "note": "no published QCD same-sign WWjj total for these cuts"}],
    V5_VV, [700603],
    "CMS card: p p > w+w+ j j and w-w- j j, QED=2 QCD=99, $ t t~, m_jj > 100, |eta_l| < 3. ATLAS 700603: Sherpa 0,1j@LO "
    "Order(*,4), pT_l > 5, >= 2 jets pT > 15, no m_jj cut. McM 0.02227 pb vs portal 0.02037 pb.")

# ---------------- N3: Dalitz, decay in MadSpin (part of the gridpack LHE step) ----------------
R1_MS = ("Decay H -> l+ l- gamma done by MadSpin inside the gridpack (madspin_card `decay x0 > l+ l- a`, spinmode none). "
         "The decay IS inside the portal value: ee and mumu samples of the same production differ (e.g. ggF 2.816e-3 vs "
         "1.858e-3 pb), which only the decay can cause. Not a separate Pythia/JHUGen step, so R1's 'decay not inside' "
         "does NOT apply. Whether the listed matching efficiency (FxFx) is inside is the general R1 assumption "
         "(UNVERIFIED for these records).")
V5_HIGGS = ("Every Higgs sample in v5 = YR4 production (mH = 125.00) x YR4 BR (x PDG Z BR), e.g. 37604 ggF H->Zgamma "
            "48.58 x 0.001533 x 0.10099; VERIFIED BY MATAN 3 Nov. No YR4 BR exists for H -> l l gamma (Dalitz).")


def dalitz(rid, mode, fl, prod_keys, atlas_dsids, atlas_share):
    sig = sum(SIG[k] for k in prod_keys)
    th = []
    if fl == "mumu":
        th.append({"option": "YR4 sigma x B(CMS MCFM, m_mumu < 50 GeV)", "value_pb": sig * 3.83e-5,
                   "factors": f"{sig:.4g} x 3.83e-5", "source": DALITZ["CMS_MCFM_mumu_lt50"][1]})
        th.append({"option": "YR4 sigma x B(ATLAS Pythia8, m_ll < 30 GeV)", "value_pb": sig * 3.42e-5,
                   "factors": f"{sig:.4g} x 3.42e-5", "source": DALITZ["ATLAS_Py8_mumu_lt30"][1]})
    else:
        th.append({"option": "YR4 sigma x B(ATLAS Pythia8, m_ll < 30 GeV)", "value_pb": sig * 7.20e-5,
                   "factors": f"{sig:.4g} x 7.20e-5", "source": DALITZ["ATLAS_Py8_ee_lt30"][1]})
        th.append({"option": "YR4 sigma x B(CMS MCFM)", "value_pb": None,
                   "note": "CMS-HIG-17-007 gives no ee value (only mumu)"})
    th.append({"option": "Z-pole part, if the sample contains it (see REPORT section 2)",
               "value_pb": sig * BR["Zgam"] * BRZ[fl], "factors": f"{sig:.4g} x 1.533e-3 x {BRZ[fl]}",
               "note": "YR4 BR(H->Zgamma) x PDG BR(Z->ll) per flavour: the H->Zgamma part with m_ll near m_Z"})
    th.append({"option": "no published value for the full m_ll range of the sample (no m_ll cut)", "value_pb": None})
    p = portal(rid)
    th.append({"option": "implied B = portal / YR4 sigma (arithmetic only)", "value": p["total_value"] / sig,
               "note": "the generator's own production sigma is not YR4, so this is not a measured BR"})
    a, at = atlas(atlas_dsids)
    add(rid, "N3", f"{mode} H -> {fl} gamma (Dalitz, no m_ll cut)", R1_MS, th, V5_HIGGS, atlas_dsids,
        "CMS cards (genproductions master, directory 'dalitz_no_mll_cut'): production MG5_aMC NLO "
        + ("HEFT ggH 0,1,2j FxFx (ptj 10, qCut 30)" if mode == "ggF" else "VBF NLO" if mode == "VBF" else f"{mode} 0,1,2j NLO FxFx")
        + "; decay in MadSpin x0 > l+ l- a with model HC_NLO_X0_UFO-lepton_masses_no_lepton_yukawas, MadSpin param card "
          "kHaa = kHza = 1, cosa = 1 (H-gamma-gamma AND H-Z-gamma couplings on: the Z pole is inside); no m_ll or photon "
          "cut in the decay (run_card mll_sf 30 / ptgmin 20 act on production-level particles; there are none). Cards "
          "read from the gridpack (evidence/gridpack_cards/). File 0: m_ll > 50 GeV in "
          + GEN_FRAC(rid) + " of the weighted events. "
        + f"ATLAS: the {atlas_share} of the listed ATLAS DSID(s) is shared by ee and mumu (ATLAS has one sample for both).")


dalitz(37276, "ggF", "ee", ["ggF"], [345961], "full sigma_eff")
dalitz(37420, "ggF", "mumu", ["ggF"], [345961], "full sigma_eff")
dalitz(68459, "VBF", "ee", ["VBF"], [345834], "full sigma_eff")
dalitz(68559, "VBF", "mumu", ["VBF"], [345834], "full sigma_eff")
dalitz(69681, "WH", "ee", ["WH"], [345963, 345964], "full sigma_eff")
dalitz(69699, "WH", "mumu", ["WH"], [345963, 345964], "full sigma_eff")
dalitz(74652, "ZH", "ee", ["qqZH"], [345965], "full sigma_eff")
dalitz(74670, "ZH", "mumu", ["qqZH"], [345965], "full sigma_eff")

# ---------------- N4 ----------------
eps_v5 = 1 - (1 - BRZ_ll) ** 2
add(74314, "N4", "qq -> ZH, H -> ZZ (JHUGen, 4-lepton filter)",
    "Production POWHEG HZJ MiNLO (Z -> all, vdecaymode 10, min_z_mass 10 GeV); H decay in a SEPARATE JHUGen step "
    "(DecayMode1=8 Z->2l incl. tau, DecayMode2=9 Z->anything, FilterNLept=4, WriteFailedEvents=2). R1: the decay BR is "
    "NOT inside the portal value; the portal value 0.7935 pb is close to the ZH production sigma (YR4 qq->ZH 0.7612, "
    "ZH total 0.8839), so the 4-lepton filter efficiency is NOT inside it either (if it were, the production sigma would "
    "be ~4-5 pb). The portal 'matching_efficiency' 0.2 (McM match_efficiency 0.1509, the validation efficiency) is "
    "therefore most likely the JHUGen filter efficiency, not a jet-matching efficiency (INTERPRETATION, open).",
    [{"option": "A: YR4 qq->ZH x BR(H->4l, l=e,mu,tau)", "value_pb": SIG["qqZH"] * BR["4l_emt"],
      "factors": "0.7612 x 2.745e-4", "note": "the convention of v5 71227/70383 (WH H->ZZ->4l) and of ATLAS 346645; counts "
      "only events with 4 leptons from the Higgs, so it misses the filtered events where the 4th/3rd lepton comes from the "
      "associated Z"},
     {"option": "B: v5 40062 convention (estimate)", "value_pb": SIG["qqZH"] * BR["ZZ"] * BRZ_ll * eps_v5,
      "factors": f"0.7612 x 0.02619 x 0.10099 x {eps_v5:.5f}", "note": "eps = 1-(1-BR(Z->ll))^2: P(at least one of the "
      "other H-Z and the associated Z -> ll), as 40062; ESTIMATE. Under the reading of option C this construction "
      "counts the H->Z(ll)Z(ll) events twice too few and differs from C by x0.67"},
     {"option": "C: YR4 qq->ZH x BR(H->ZZ) x [1-(1-BR(Z->ll))^2] x McM filter efficiency 0.1509",
      "value_pb": SIG["qqZH"] * BR["ZZ"] * eps_v5 * 0.150882730885,
      "factors": f"0.7612 x 0.02619 x {eps_v5:.5f} x 0.15088", "note": "reading supported by the file-0 decay content "
      "(REPORT section 3, N4): JHUGen DecayMode 8+9 gives H->ZZ with AT LEAST one Z->ll (e,mu,tau), fraction "
      "1-(1-B)^2 = 2B-B^2; the FilterNLept=4 filter then keeps (B^2 + 2B(1-B) B)/(2B-B^2) = 0.149 of them, matching McM "
      "0.1509; the predicted decay mix after the filter (llll 0.357 / llqq 0.499 / llnunu 0.143) matches file 0 "
      "(0.367 / 0.489 / 0.143). INTERPRETATION, not documented by CMS"},
     {"option": "C': as C with the filter efficiency computed from BRs, 0.1491", "value_pb": SIG["qqZH"] * BR["ZZ"] *
      (BRZ_ll**2 + 2*BRZ_ll*(1-BRZ_ll)*BRZ_ll), "factors": "0.7612 x 0.02619 x [B^2 + 2B(1-B)B], B = 0.10099",
      "note": "same reading; ESTIMATE (ignores tau-decay and lepton-counting details)"},
     {"option": "D: portal 0.7935 x BR(H->ZZ) x [1-(1-B)^2] x 0.1509", "value_pb": 0.7935 * BR["ZZ"] * eps_v5 * 0.150882730885,
      "factors": f"0.7935 x 0.02619 x {eps_v5:.5f} x 0.15088", "note": "generator production sigma instead of YR4"},
     {"option": "E: measure the filter content in file 0 (precheck, generator particles)", "value_pb": None,
      "note": "REPORT section 5: fraction of events by H->ZZ and associated-Z decay"}],
    "40062 ggZH 4l (ESTIMATE, 0.1227 x 0.02619 x 0.10099 x 0.19178); 71227/70383 WH 4l (YR4 x 2.745e-4); 37728/68847 "
    "ggF/VBF 4l (YR4 x 2.745e-4).", [346645],
    "ATLAS 346645 = 0.7612 x 2.745e-4 (S2: the same 2.745e-4 is used as filter for H->mumu samples).")


def fmt(v):
    return "—" if v is None else (f"{v:.4g}" if isinstance(v, float) else str(v))


def tables():
    out = []
    for rid, s in S.items():
        p = s["portal"]
        out.append(f"#### {s['item']} {rid} — {s['dataset']}\n")
        out.append("| option | value [pb] | how | source / status |\n|---|---:|---|---|")
        out.append(f"| (a) portal total_value (MiniAOD [{s['mini_recid']}]({s['portal_url']})) | {fmt(p['total_value'])} | "
                   f"filter {fmt(p['filter_efficiency'])}, matching {fmt(p['matching_efficiency'])}, neg. weights "
                   f"{fmt(p['neg_weight_fraction'])} | VERIFIED (saved record) |")
        m = s["mcm"]
        out.append(f"| (b) McM generator value ([{m['prepid']}]({m['url']})) | {fmt(m['cross_section_pb'])} | filter "
                   f"{fmt(m['filter_efficiency'])}, match {fmt(m['match_efficiency'])} | VERIFIED (saved request JSON); "
                   f"{'1 = placeholder, not a cross section' if m['cross_section_pb'] == 1 else 'user-entered value'} |")
        for t in s["theory_options"]:
            val = t.get("value_pb", t.get("value"))
            out.append(f"| (c) {t['option']} | {fmt(val)} | {t.get('factors', '')} | "
                       f"{(t.get('source') or t.get('note') or '')} |")
        out.append(f"| (e) ATLAS σ×k×ε ({', '.join(str(a['dsid']) for a in s['atlas'])}) | {fmt(s['atlas_sigma_eff_pb'])} | "
                   + "; ".join(f"{a['dsid']}: {a['sigma_pb']:.5g}×{a['kFactor']:.4g}×{a['genFiltEff']:.4g}" for a in s["atlas"])
                   + f" | VERIFIED (public metadata 2024r-pp); CMS portal / ATLAS = {fmt(s['cms_portal_over_atlas'])} |")
        out.append(f"\n- **R1:** {s['r1']}\n- **(d) registry v5 analogue:** {s['v5_analogue']}\n- **Generator settings:** {s['notes']}\n")
    return "\n".join(out)


def main():
    (HERE / "evidence" / "xsec_options.json").write_text(json.dumps(
        {"what": "Cross-section OPTIONS for the 14 Nominal-6 additions. NOTHING ADOPTED; for Matan's hand check.",
         "yr4_production_pb": SIG, "yr4_br": BR, "pdg_z_br": BRZ, "sources": {"YR4": YR4, "YR4BR": YR4BR, "PDG_Z": PDGZ},
         "samples": S}, indent=1, ensure_ascii=False) + "\n")
    (HERE / "evidence" / "xsec_tables.md").write_text(tables() + "\n")
    for rid, s in S.items():
        print(rid, s["item"], f"portal {s['portal']['total_value']:.4g}", f"ATLAS {s['atlas_sigma_eff_pb']:.4g}",
              f"ratio {s['cms_portal_over_atlas']:.3g}")


if __name__ == "__main__":
    main()
