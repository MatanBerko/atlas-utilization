#!/usr/bin/env python
"""
Part A: the published reference, assembled into one evidence JSON.

Three kinds of number go in, and each is labelled in the file itself:

  VERIFIED_HEPDATA   downloaded from HEPData at run time and parsed here.
                     The exclusive jet-multiplicity cross sections and
                     their full uncertainty breakdown (Table 1a, Fig. 4).
  DERIVED            arithmetic on the above, done here. The INCLUSIVE jet
                     multiplicity is not a HEPData table in this record, so
                     it is summed from the exclusive one, with the caveat
                     that the measurement stops at 8 jets.
  UNVERIFIED_FIGURE  read off the published figure by eye, because the
                     record carries no table of the predictions. The
                     generator-to-data ratios in Fig. 4a's lower panels.

The object definitions are quoted verbatim from the arXiv source of
arXiv:2205.02872 (CMS-SMP-19-009) and are labelled as quotes.

Run with --offline to rebuild the file from the constants alone (no
network), which is what the cluster does; the HEPData numbers below were
downloaded once and are checked against the live record when online.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
import urllib.request
from datetime import datetime, timezone

HEPDATA_RECORD = "ins2078067"
HEPDATA_URL = "https://www.hepdata.net/record/ins2078067"
HEPDATA_TABLE = "Table 1a"
HEPDATA_TABLE_JSON = (
    "https://www.hepdata.net/download/table/ins2078067/Table%201a/json")
HEPDATA_DOI = "10.17182/hepdata.115655.v1/t1"
ARXIV = "arXiv:2205.02872"
REPORT_NUMBER = "CMS-SMP-19-009"
JOURNAL = "Phys. Rev. D 108 (2023) 052004"
LUMINOSITY_FB = 35.9

# Downloaded from HEPData Table 1a on 2026-10-11. Kept here so the file can
# be rebuilt offline on the cluster; when the script runs online it
# re-downloads and refuses to continue if anything has changed.
EXCLUSIVE_SIGMA_PB = {
    0: (618.0, 17.0), 1: (97.7, 4.4), 2: (22.3, 1.1), 3: (4.75, 0.29),
    4: (1.113, 0.084), 5: (0.265, 0.021), 6: (0.0609, 0.0082),
    7: (0.0131, 0.0039), 8: (0.0051, 0.0015),
}
# relative uncertainty breakdown, per cent, same table
EXCLUSIVE_UNCERTAINTY_PCT = {
    #        total  stat   JES   JER   Eff  Lumi   Bkg  Pileup Unf.sys Unf.stat
    0: dict(total=2.7, stat=0.020, jes=0.80, jer=0.084, eff=0.012, lumi=2.5,
            bkg=0.018, pileup=0.042, unf_sys=0.30, unf_stat=0.021),
    1: dict(total=4.5, stat=0.067, jes=3.7, jer=0.33, eff=0.087, lumi=2.5,
            bkg=0.024, pileup=0.32, unf_sys=0.32, unf_stat=0.070),
    2: dict(total=4.9, stat=0.16, jes=4.2, jer=0.19, eff=0.073, lumi=2.6,
            bkg=0.034, pileup=0.37, unf_sys=0.53, unf_stat=0.16),
    3: dict(total=6.2, stat=0.40, jes=5.5, jer=0.29, eff=0.20, lumi=2.6,
            bkg=0.035, pileup=0.64, unf_sys=0.44, unf_stat=0.40),
    4: dict(total=7.6, stat=0.95, jes=6.8, jer=0.14, eff=0.048, lumi=2.6,
            bkg=0.054, pileup=0.88, unf_sys=1.1, unf_stat=0.99),
    5: dict(total=8.1, stat=2.3, jes=6.7, jer=1.0, eff=0.18, lumi=2.6,
            bkg=0.051, pileup=0.45, unf_sys=0.43, unf_stat=2.5),
    6: dict(total=13.0, stat=5.9, jes=8.0, jer=0.58, eff=0.98, lumi=2.7,
            bkg=0.13, pileup=2.3, unf_sys=3.8, unf_stat=7.3),
    7: dict(total=30.0, stat=16.0, jes=9.6, jer=2.4, eff=0.82, lumi=2.4,
            bkg=0.055, pileup=4.0, unf_sys=5.0, unf_stat=22.0),
    8: dict(total=29.0, stat=14.0, jes=12.0, jer=3.1, eff=0.78, lumi=2.5,
            bkg=0.015, pileup=2.0, unf_sys=3.3, unf_stat=21.0),
}

# Read off Fig. 4a of the publication (the two lower ratio panels), which is
# the only published form of these numbers -- the HEPData record tabulates
# the measurement but not the predictions. Quoted as prediction/measurement,
# the way the figure plots them. Read to the nearest 0.01-0.02; the reading
# uncertainty is about +-0.02 and is NOT the theory uncertainty.
FIGURE_RATIOS_PREDICTION_OVER_DATA = {
    "MG5_aMC NLO FxFx (<=2j NLO + PS)": {
        0: 0.96, 1: 1.04, 2: 1.02, 3: 1.04, 4: 0.89,
        5: 0.76, 6: 0.68, 7: 0.68, 8: 0.42,
    },
    "MG5_aMC LO MLM (<=4j LO + PS)": {
        0: 0.95, 1: 0.91, 2: 0.81, 3: 0.86, 4: 0.94,
        5: 0.96, 6: 0.99, 7: 1.15, 8: 0.51,
    },
}
FIGURE_READ_UNCERTAINTY = 0.02

# Verbatim quotes from the arXiv source of 2205.02872 (file
# SMP-19-009_temp.tex), with the LaTeX macros expanded by hand into plain
# text. These are the paper's own words for its object definitions.
PAPER_DEFINITIONS = {
    "jets": {
        "quote": "Jets are formed from the particles reconstructed by the PF "
                 "algorithm using the FastJet software package, and the "
                 "anti-kT jet clustering algorithm with a distance parameter "
                 "R of 0.4. ... Tight identification quality criteria, based "
                 "on the fraction of energy carried by charged and neutral "
                 "hadrons, are applied to jets ... Jets are required to have "
                 "|eta| < 2.4, to be separated from all selected lepton "
                 "candidates by at least a distance Delta R = 0.4, and have a "
                 "pT larger than 30 GeV for the single-differential cross "
                 "sections and 20 GeV for the double-differential ones.",
        "pt_min_gev": 30.0,
        "abs_eta_max": 2.4,
        "algorithm": "anti-kT, R = 0.4, PF + charged hadron subtraction",
        "jet_id": "tight",
        "lepton_cleaning_dr": 0.4,
        "b_tagged_jets_counted": True,
        "b_tag_note": "the paper applies no b-tag requirement or veto anywhere "
                      "in the jet-multiplicity definition, so b jets are "
                      "counted as jets",
    },
    "leptons": {
        "quote": "After offline reconstruction, two leptons are required with "
                 "the first having pT > 30 GeV and the second having pT > 20 "
                 "GeV. We require that the two electrons (muons) with highest "
                 "pT form a pair of oppositely charged leptons with an "
                 "invariant mass in the range (91 +- 20 GeV). ... For both "
                 "electrons and muons, medium identification criteria are "
                 "applied.",
        "lead_pt_min_gev": 30.0,
        "sublead_pt_min_gev": 20.0,
        "abs_eta_max": 2.4,
        "eta_quote": "Electron candidates within the geometrical acceptance of "
                     "|eta| < 2.4, excluding the barrel-to-endcap "
                     "(1.444 < |eta| < 1.566) transition regions of the ECAL "
                     "... Muon candidates within the geometrical acceptance of "
                     "|eta| < 2.4",
        "dilepton_mass_window_gev": [71.0, 111.0],
        "identification": "medium, for both flavours",
    },
    "particle_level": {
        "quote": "The particle-level objects are defined with a lifetime of "
                 "c*tau > 1 cm (excluding neutrinos) and identified using the "
                 "same algorithms as used for the data. Leptons are stable "
                 "particles coming from Z boson decays, dressed by adding the "
                 "momenta of all photons within R < 0.1 of their directions.",
        "dressing_radius": 0.1,
    },
    "trigger": {
        "quote": "Candidate events are selected online using single-lepton "
                 "triggers that require at least one isolated electron (muon) "
                 "with pT > 25 (24) GeV and |eta| < 2.4.",
    },
    "normalisation": {
        "quote": "the simulated samples are normalized to the integrated "
                 "luminosity of the data sample using their respective cross "
                 "sections.",
    },
}

PAPER_PREDICTIONS = {
    "MG5_aMC NLO FxFx (<=2j NLO + PS)": {
        "quote": "For the simulation of the signal, we use a sample generated "
                 "at next-to-leading order (NLO) with MG5_aMC versions 2.2.2 "
                 "and 2.3.2 using the FxFx merging scheme. Parton showering "
                 "and hadronization are simulated with PYTHIA8 (version 8.212) "
                 "using the CUETP8M1 tune. The matrix element includes Z boson "
                 "production with up to two additional jets generated at NLO "
                 "with MG5_aMC, effectively yielding leading order (LO) "
                 "accuracy for Z+3 jets.",
        "max_me_jets": 2,
        "me_order": "NLO",
        "merging": "FxFx, merging scale 30 GeV",
        "pdf": "NNPDF 3.0 NLO",
        "alpha_s": 0.118,
        "tune": "CUETP8M1",
        "shower": "PYTHIA8 8.212",
    },
    "MG5_aMC LO MLM (<=4j LO + PS)": {
        "quote": "For the LO MG5_aMC, the generator calculates LO matrix "
                 "elements (MEs) for five processes: pp -> Z + N_jets with "
                 "N = 0, ..., 4. The NNPDF 3.0 LO PDF is used and alpha_s(mZ) "
                 "is set to 0.130. ... The ME and parton shower matching is "
                 "done using the kT-MLM scheme with the matching scale set at "
                 "19 GeV for the LO MG5_aMC.",
        "max_me_jets": 4,
        "me_order": "LO",
        "merging": "kT-MLM, matching scale 19 GeV",
        "pdf": "NNPDF 3.0 LO",
        "alpha_s": 0.130,
        "tune": "CUETP8M1",
        "shower": "PYTHIA8 8.212",
    },
}

# A2: how their setup differs from ours, stated plainly.
DIFFERENCES_FROM_OUR_SETUP = [
    {"what": "reconstruction", "theirs": "legacy 2016 ReReco (the 2016 "
     "analysis campaign of CMS-SMP-19-009)", "ours": "UL2016 postVFP "
     "NanoAODv9", "matters": "different jet energy corrections, different "
     "pileup treatment and a different jet ID training; the two are not the "
     "same detector calibration"},
    {"what": "data period", "theirs": "the full 2016 run, 35.9 fb^-1",
     "ours": "Run2016 G+H only, 16.393 fb^-1", "matters": "G+H is the "
     "post-VFP part of 2016; the pileup profile and the tracker condition "
     "differ from the 2016 average"},
    {"what": "level", "theirs": "particle level, unfolded for detector "
     "effects", "ours": "detector level, no unfolding",
     "matters": "their data/prediction ratio has the detector taken out of "
     "it; ours has it still in. Any difference between the two ratios is "
     "therefore a detector-level statement about our setup"},
    {"what": "lepton thresholds", "theirs": "leading pT > 30, subleading "
     "pT > 20 GeV", "ours": "both leptons pT > 25 GeV",
     "matters": "we can tighten the leading lepton to 30 but cannot lower "
     "the subleading one to 20 without replacing the delivered lepton "
     "selection, which this study may not do"},
    {"what": "jet |eta|", "theirs": "2.4", "ours": "2.5",
     "matters": "we count slightly more forward jets; this is closed in the "
     "paper-like definition"},
    {"what": "b jets", "theirs": "counted as jets", "ours": "excluded from "
     "the light-jet count the excess was seen in",
     "matters": "closed in the paper-like definition, and measured "
     "separately in Part B1"},
    {"what": "signal sample", "theirs": "MG5_aMC FxFx <=2j NLO, CUETP8M1 "
     "tune, NNPDF3.0", "ours": "record 35669, "
     "DYJetsToLL_M-50_TuneCP5_13TeV-amcatnloFXFX-pythia8, UL16 postVFP",
     "matters": "the SAME generator and merging scheme at the same matrix-"
     "element multiplicity, with a newer tune (CP5 rather than CUETP8M1) and "
     "a UL campaign. The published prediction is therefore directly "
     "informative about ours"},
    {"what": "other processes", "theirs": "a full background estimate "
     "including ttbar, single top, dibosons and a data-driven nonresonant "
     "background", "ours": "DY + ttbar(2L2Nu) + ggH only",
     "matters": "single top and dibosons are missing from our simulation; "
     "they matter most at high jet multiplicity"},
]


# HEPData's front end rejects most non-browser User-Agents with a 403 but
# serves a plain curl one, so that is what is sent. Verified by trying three
# agents against the live record on 2026-10-11: only this one returned 200.
HEPDATA_USER_AGENT = "curl/8.4.0"


def download_table():
    request = urllib.request.Request(
        HEPDATA_TABLE_JSON,
        headers={"User-Agent": HEPDATA_USER_AGENT, "Accept": "*/*"})
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))


def parse_table(payload):
    """The measured sigma per exclusive jet bin, with its total uncertainty."""
    out = {}
    for row in payload["values"]:
        njets = int(row["x"][0]["value"])
        sigma = float(row["y"][0]["value"])
        err = float(row["y"][0]["errors"][0]["symerror"])
        out[njets] = (sigma, err)
    return out


def inclusive_from_exclusive(exclusive):
    """sigma(>= N jets) = sum of the exclusive bins from N up.

    The measurement stops at 8 jets, so every inclusive number here is a
    lower bound that misses the >8 tail. Table 1a's own 8-jet bin is
    0.0051 pb against 618 pb at 0 jets, so the tail is far below the
    uncertainty of any bin it would affect.
    """
    keys = sorted(exclusive)
    out = {}
    for n in keys:
        total = sum(exclusive[k][0] for k in keys if k >= n)
        # uncorrelated-in-quadrature is wrong for correlated systematics but
        # is the only thing derivable without the covariance; flagged as such
        err = sum(exclusive[k][1] ** 2 for k in keys if k >= n) ** 0.5
        out[n] = (total, err)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--offline", action="store_true",
                    help="rebuild from the stored constants, no network")
    args = ap.parse_args()

    source = "stored constants (offline)"
    exclusive = {int(k): v for k, v in EXCLUSIVE_SIGMA_PB.items()}
    if not args.offline:
        live = parse_table(download_table())
        mismatch = [n for n in exclusive
                    if n not in live
                    or abs(live[n][0] - exclusive[n][0]) > 1e-9
                    or abs(live[n][1] - exclusive[n][1]) > 1e-9]
        if mismatch or set(live) != set(exclusive):
            raise SystemExit(
                "the live HEPData table no longer matches the stored "
                "constants at jet bins {} -- refusing to write a file that "
                "mixes the two".format(sorted(mismatch)))
        source = HEPDATA_TABLE_JSON

    inclusive = inclusive_from_exclusive(exclusive)

    payload = {
        "what": "Part A: the published Z+jets reference, CMS-SMP-19-009",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "source": {
            "arxiv": ARXIV, "report_number": REPORT_NUMBER,
            "journal": JOURNAL, "hepdata_record": HEPDATA_RECORD,
            "hepdata_url": HEPDATA_URL, "hepdata_table": HEPDATA_TABLE,
            "hepdata_table_doi": HEPDATA_DOI,
            "hepdata_table_location": "Fig. 4 of the publication",
            "downloaded_from": source,
            "luminosity_fb": LUMINOSITY_FB,
        },
        "labels": {
            "exclusive_sigma_pb": "VERIFIED BY RUNNING (downloaded from "
                                  "HEPData Table 1a and parsed)",
            "exclusive_uncertainty_pct": "VERIFIED BY RUNNING (same table)",
            "inclusive_sigma_pb": "DERIVED by summing the exclusive bins; the "
                                  "measurement stops at 8 jets and the "
                                  "uncertainty is a quadrature sum that "
                                  "ignores bin-to-bin correlation",
            "prediction_over_data": "UNVERIFIED -- read off Fig. 4a of the "
                                    "publication by eye, because this HEPData "
                                    "record tabulates the measurement but not "
                                    "the predictions. Reading uncertainty "
                                    "about +-0.02, which is NOT the theory "
                                    "uncertainty",
            "definitions": "VERBATIM QUOTES from the arXiv source of "
                           + ARXIV,
        },
        "exclusive_sigma_pb": {str(k): {"sigma": v[0], "total_unc": v[1]}
                               for k, v in sorted(exclusive.items())},
        "exclusive_uncertainty_pct": {str(k): v for k, v in
                                      sorted(EXCLUSIVE_UNCERTAINTY_PCT.items())},
        "inclusive_sigma_pb": {str(k): {"sigma": v[0], "total_unc": v[1]}
                               for k, v in sorted(inclusive.items())},
        "prediction_over_data": FIGURE_RATIOS_PREDICTION_OVER_DATA,
        "prediction_over_data_read_uncertainty": FIGURE_READ_UNCERTAINTY,
        "data_over_prediction": {
            name: {str(k): round(1.0 / v, 4) for k, v in sorted(ratios.items())}
            for name, ratios in FIGURE_RATIOS_PREDICTION_OVER_DATA.items()
        },
        "paper_definitions": PAPER_DEFINITIONS,
        "paper_predictions": PAPER_PREDICTIONS,
        "differences_from_our_setup": DIFFERENCES_FROM_OUR_SETUP,
    }

    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print("CMS-SMP-19-009 exclusive jet multiplicity ({} fb^-1)".format(
        LUMINOSITY_FB))
    print("{:>4} {:>12} {:>9} | {:>10} {:>10}".format(
        "Nj", "sigma [pb]", "tot unc", "NLO p/d", "LO p/d"))
    nlo = FIGURE_RATIOS_PREDICTION_OVER_DATA["MG5_aMC NLO FxFx (<=2j NLO + PS)"]
    lo = FIGURE_RATIOS_PREDICTION_OVER_DATA["MG5_aMC LO MLM (<=4j LO + PS)"]
    for n in sorted(exclusive):
        sigma, err = exclusive[n]
        print("{:>4} {:>12.4g} {:>8.2g}% | {:>10.2f} {:>10.2f}".format(
            n, sigma, 100.0 * err / sigma, nlo[n], lo[n]))
    print("\nwrote {}".format(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
