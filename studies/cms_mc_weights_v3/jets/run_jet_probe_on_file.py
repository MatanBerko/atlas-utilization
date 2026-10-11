#!/usr/bin/env python
"""
Parts B and C: the jet-excess probe, one input file per job.

This re-reads the SAME file subset the pileup study used (study/cms-mc-pileup
Part B) and asks a different question of it: where does the >=3-light-jet
data excess come from?

**It reuses the delivered selection unmodified**, importing from
`studies/cms_datasets/cluster/run_dataset_on_file.py` and
`studies/m0m1j0_cms/selection.py`. Nothing in either module is changed, and
no selection, object definition, threshold or delivered output is altered by
anything here. Every alternative jet definition below is built ALONGSIDE the
delivered one, inside this diagnostic, and is reported separately.

Z events are defined exactly as the pilot's P3 did: the `matched4` population
of the file's own dataset, Version B (electrons + muons + b-jets <= 4), a
final state with exactly 2 same-flavour leptons and 0 of the other flavour,
and a dilepton mass in the window.

Jet multiplicity is counted under four definitions, per Z event:

  delivered_light   the delivered light-jet count: pT > 30, |eta| < 2.5,
                    tight jet ID, dR > 0.4 from every selected lepton,
                    b-tagged jets EXCLUDED. This is the P3 definition and
                    the one the excess was seen in.
  delivered_all     the same jets with the b-tagged ones counted back in.
                    (Part B1: does excluding b jets create the excess?)
  paperlike         CMS-SMP-19-009's jet definition: pT > 30, |eta| < 2.4,
                    tight jet ID, dR > 0.4 from every selected lepton, ALL
                    jets regardless of b tag. Our Z window.
  paperlike_paperZ  the same jets with the paper's Z selection too: leading
                    lepton pT > 30, both leptons |eta| < 2.4, dilepton mass
                    71-111 GeV. (Part B2.)

One difference from the paper is deliberately NOT closed: the paper's
subleading lepton threshold is 20 GeV and ours is 25, because the delivered
lepton selection cuts at 25 and this study may not replace it. The effect is
common to data and MC and is reported as a residual difference, not hidden.

In MC the same counts are repeated with official JER smearing applied (Part
C1) and the paper-like count is repeated over a grid of jet energy scale
shifts (Part C2). Generator jets are counted with the paper's particle-level
definition over ALL generated events in the file (Part C5, an absolute
prediction), and the reco-vs-gen migration matrix is filled (Part C6).

Jet-level diagnostics for the 3rd-and-later jets -- eta, phi, an (eta, phi)
occupancy map, the PF energy fractions, the tight-lepton-veto ID bit, and
the distance to the nearest selected lepton, ANY lepton and any photon --
answer Parts C3 and C4.

Output: ONE small JSON of pre-binned histograms per input file. No
per-event files are written (the account is near its inode quota).
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
import time
from datetime import datetime, timezone

import awkward as ak
import numpy as np

REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

from services.parsing.trigger_requirements import apply_trigger_requirement  # noqa: E402
from services.parsing.validated_runs import (  # noqa: E402
    ValidatedRunsFilter, apply_validated_runs_filter, is_simulation,
)
from studies.m0m1j0_cms import selection  # noqa: E402
from studies.m0m1j0_cms.selection import (  # noqa: E402
    BTAG_DEEPFLAVB_MEDIUM_WP, JET_LEPTON_CLEAN_DR, JET_PT_MIN_GEV,
)
from studies.cms_datasets.cluster.run_dataset_on_file import (  # noqa: E402
    BASE_OBJECT_BRANCHES,
    DEFAULT_VALIDATED_RUNS_JSON,
    DELIVERY_VETO_ORDER_4,
    ELE27_PATH,
    EMU_OVERLAP_DR_MAX,
    MATCHED4_TRIGGER_PATHS,
    MATCHED_MODE_EXTRA_BRANCHES,
    assert_trigobj_bit_meanings,
    evaluate_four_acceptances,
    exact_final_state_labels,
    exclusive_mask_from_acceptances,
    mc_store_mask,
    ele27_candidate_acceptance,
    read_events,
    remove_electrons_overlapping_muons,
    resolve_file_url,
)
from studies.cms_mc_weights_v3.jets.jer import GEN_MATCH_DR_MAX, JerSmearer  # noqa: E402
from studies.cms_mc_weights_v3.pileup.pu_weights import load as load_pu  # noqa: E402

# ---- binning, fixed here so every job produces addable histograms --------
NJET_BINS = 6                               # 0, 1, 2, 3, 4, 5+
Z_WINDOW = (76.0, 106.0)                    # ours, the pilot's P3 window
PAPER_Z_WINDOW = (71.0, 111.0)              # 91 +/- 20, CMS-SMP-19-009
PAPER_LEAD_LEPTON_PT = 30.0
PAPER_SUBLEAD_LEPTON_PT = 20.0              # generator level only, see C5
PAPER_LEPTON_ETA_MAX = 2.4
PAPER_JET_ETA_MAX = 2.4
PAPER_JET_PT_MIN = 30.0

# C2: the jet energy scale shifts to scan, as a fraction
JES_SHIFTS = (-0.10, -0.06, -0.04, -0.02, 0.02, 0.04, 0.06, 0.10)

XJET_PT_EDGES = np.arange(30.0, 205.0, 5.0)
XJET_ETA_EDGES = np.linspace(-2.5, 2.5, 51)
XJET_PHI_EDGES = np.linspace(-np.pi, np.pi, 37)
XJET_OCC_ETA_EDGES = np.linspace(-2.5, 2.5, 26)
XJET_OCC_PHI_EDGES = np.linspace(-np.pi, np.pi, 19)
FRACTION_EDGES = np.linspace(0.0, 1.0, 21)
DR_EDGES = np.linspace(0.0, 4.0, 41)

CHANNELS = ("mumu", "ee")

# NanoAOD Jet_jetId bit meanings. The delivered selection uses `& 2`
# (tight). `& 4` is tightLepVeto, which the delivery does NOT require --
# Part C4 measures how often the extra jets fail it.
JETID_TIGHT_BIT = 2
JETID_TIGHTLEPVETO_BIT = 4

OPTIONAL_JET_BRANCHES = (
    "Jet_chEmEF", "Jet_neEmEF", "Jet_chHEF", "Jet_neHEF",
    "Jet_nElectrons", "Jet_nMuons", "Jet_rawFactor",
)
OPTIONAL_EVENT_BRANCHES = ("fixedGridRhoFastjetAll",)
OPTIONAL_PHOTON_BRANCHES = ("nPhoton", "Photon_pt", "Photon_eta", "Photon_phi")
OPTIONAL_MC_BRANCHES = (
    "Jet_genJetIdx", "nGenJet", "GenJet_pt", "GenJet_eta", "GenJet_phi",
    "nGenDressedLepton", "GenDressedLepton_pt", "GenDressedLepton_eta",
    "GenDressedLepton_phi", "GenDressedLepton_mass", "GenDressedLepton_pdgId",
)


def njet_bin(values):
    return np.clip(np.asarray(values, dtype=np.int64), 0, NJET_BINS - 1)


def delta_r(eta1, phi1, eta2, phi2):
    dphi = (phi1 - phi2 + np.pi) % (2.0 * np.pi) - np.pi
    return np.sqrt((eta1 - eta2) ** 2 + dphi ** 2)


def min_dr_to(jets, others, missing=99.0):
    """Nearest dR from each jet to any member of `others`, per event.

    `others` may be empty in an event; those jets get `missing`, i.e. "far
    from anything", which is what every caller here wants.
    """
    pairs_jet, pairs_other = ak.unzip(ak.cartesian([jets, others], nested=True))
    dr = delta_r(pairs_jet.eta, pairs_jet.phi, pairs_other.eta, pairs_other.phi)
    return ak.fill_none(ak.min(dr, axis=-1), missing)


def dilepton_mass_arrays(pt1, eta1, phi1, m1, pt2, eta2, phi2, m2):
    """Invariant mass of two objects, from flat numpy arrays."""
    def components(pt, eta, phi, mass):
        px = pt * np.cos(phi)
        py = pt * np.sin(phi)
        pz = pt * np.sinh(eta)
        return px, py, pz, np.sqrt(px ** 2 + py ** 2 + pz ** 2 + mass ** 2)

    ax, ay, az, ae = components(pt1, eta1, phi1, m1)
    bx, by, bz, be = components(pt2, eta2, phi2, m2)
    m2sq = (ae + be) ** 2 - (ax + bx) ** 2 - (ay + by) ** 2 - (az + bz) ** 2
    return np.sqrt(np.maximum(m2sq, 0.0))


def two_leading(collection, fields):
    """The two leading members by pT as flat numpy arrays, zero-filled where
    an event has fewer than two. Callers must mask those events themselves."""
    order = ak.argsort(collection.pt, axis=1, ascending=False)
    ordered = collection[order]
    padded = ak.pad_none(ordered, 2, axis=1)
    out = {}
    for name in fields:
        out[name] = (
            ak.to_numpy(ak.fill_none(padded[name][:, 0], 0.0)),
            ak.to_numpy(ak.fill_none(padded[name][:, 1], 0.0)),
        )
    return out


def counts_entry(counts, weights):
    """Weighted + squared + raw multiplicity counts, as plain lists."""
    binned = njet_bin(counts)
    return {
        "w": np.bincount(binned, weights=weights, minlength=NJET_BINS).tolist(),
        "w2": np.bincount(binned, weights=weights ** 2,
                          minlength=NJET_BINS).tolist(),
        "raw": np.bincount(binned, minlength=NJET_BINS).tolist(),
    }


def hist1d(values, edges, weights):
    flat = (ak.to_numpy(ak.flatten(values)) if isinstance(values, ak.Array)
            else np.asarray(values))
    return np.histogram(flat, bins=edges, weights=weights)[0].tolist()


def build_raw_jets(events, extra_present):
    """Every jet in the file, with whatever optional fields are available."""
    fields = {
        "pt": events.Jet_pt, "eta": events.Jet_eta, "phi": events.Jet_phi,
        "mass": events.Jet_mass, "jetId": events.Jet_jetId,
        "btagDeepFlavB": events.Jet_btagDeepFlavB,
    }
    for name in OPTIONAL_JET_BRANCHES:
        if name in extra_present:
            fields[name.replace("Jet_", "")] = events[name]
    if "Jet_genJetIdx" in extra_present:
        fields["genJetIdx"] = events.Jet_genJetIdx
    return ak.zip(fields)


def apply_jet_cuts(jets, leptons, pt_min, eta_max, pt_override=None):
    """The delivered cut shape -- pT, |eta|, tight ID, dR from leptons --
    with the thresholds the caller asks for.

    `pt_override` lets a diagnostic (JER smearing, a JES shift) cut on a
    modified pT while every other field stays as read. The cut SHAPE is
    never changed: this is the delivered recipe with different numbers in
    it, so that a difference in the result can only come from the numbers.
    """
    pt = jets.pt if pt_override is None else pt_override
    keep = ((pt > pt_min)
            & (abs(jets.eta) < eta_max)
            & ((jets.jetId & JETID_TIGHT_BIT) != 0))
    cut = jets[keep]
    return cut[min_dr_to(cut, leptons) >= JET_LEPTON_CLEAN_DR]


def gen_particle_level(events, extra_present):
    """The paper's particle-level Z + jets selection, on generator objects.

    Leptons are the NanoAOD dressed leptons -- photons within R < 0.1 are
    already added, which is exactly the paper's dressing prescription. This
    runs over EVERY generated event in the file, with no trigger, no
    acceptance and no Version B gate, because a particle-level cross section
    is defined without them.

    Returns (jet count, event mask, lepton flavour as 11 or 13).
    """
    if ("GenDressedLepton_pt" not in extra_present
            or "GenJet_pt" not in extra_present):
        return None, None, None

    dressed = ak.zip({
        "pt": events.GenDressedLepton_pt, "eta": events.GenDressedLepton_eta,
        "phi": events.GenDressedLepton_phi, "mass": events.GenDressedLepton_mass,
        "pdgId": events.GenDressedLepton_pdgId,
    })
    is_lepton = (abs(dressed.pdgId) == 11) | (abs(dressed.pdgId) == 13)
    lep = dressed[is_lepton & (abs(dressed.eta) < PAPER_LEPTON_ETA_MAX)]
    order = ak.argsort(lep.pt, axis=1, ascending=False)
    lep = lep[order]
    pair = lep[ak.local_index(lep, axis=1) < 2]

    two = two_leading(lep, ("pt", "eta", "phi", "mass", "pdgId"))
    enough = ak.to_numpy(ak.num(lep, axis=1)) >= 2
    mass = dilepton_mass_arrays(
        two["pt"][0], two["eta"][0], two["phi"][0], two["mass"][0],
        two["pt"][1], two["eta"][1], two["phi"][1], two["mass"][1])

    ok = (enough
          & (two["pt"][0] > PAPER_LEAD_LEPTON_PT)
          & (two["pt"][1] > PAPER_SUBLEAD_LEPTON_PT)
          & (two["pdgId"][0] == -two["pdgId"][1])      # same flavour, opposite sign
          & (mass >= PAPER_Z_WINDOW[0]) & (mass <= PAPER_Z_WINDOW[1]))

    genjets = ak.zip({"pt": events.GenJet_pt, "eta": events.GenJet_eta,
                      "phi": events.GenJet_phi})
    clean = genjets[(genjets.pt > PAPER_JET_PT_MIN)
                    & (abs(genjets.eta) < PAPER_JET_ETA_MAX)]
    clean = clean[min_dr_to(clean, pair) >= JET_LEPTON_CLEAN_DR]
    njet = ak.to_numpy(ak.num(clean, axis=1))
    flavour = np.abs(two["pdgId"][0]).astype(np.int64)
    return njet, ok, flavour


def smeared_jet_pt(events, jets, smearer, rng, extra_present):
    """Official JER smearing, hybrid method. Returns the smeared pT and a
    small report of what the correction actually did."""
    rho = ak.broadcast_arrays(events.fixedGridRhoFastjetAll, jets.pt)[0]

    counts = ak.num(jets.pt, axis=1)
    n_flat = int(ak.sum(counts))
    has_gen = np.zeros(n_flat, dtype=bool)
    gen_pt_flat = np.zeros(n_flat, dtype=np.float64)

    if "Jet_genJetIdx" in extra_present and "GenJet_pt" in extra_present:
        # pad the generator jets with one dummy entry so an event with no
        # generator jets can still be indexed; `valid` keeps it harmless
        def padded(branch):
            return ak.fill_none(ak.pad_none(branch, 1, axis=1), 0.0)

        idx = jets.genJetIdx
        n_gen = ak.num(events.GenJet_pt, axis=1)
        valid = (idx >= 0) & (idx < n_gen)
        safe = ak.where(valid, idx, 0)
        gen_pt = padded(events.GenJet_pt)[safe]
        gen_eta = padded(events.GenJet_eta)[safe]
        gen_phi = padded(events.GenJet_phi)[safe]
        matched = valid & (delta_r(jets.eta, jets.phi, gen_eta, gen_phi)
                           < GEN_MATCH_DR_MAX)
        has_gen = ak.to_numpy(ak.flatten(matched))
        gen_pt_flat = ak.to_numpy(ak.flatten(ak.where(matched, gen_pt, 0.0)))

    pt_flat = ak.to_numpy(ak.flatten(jets.pt))
    factors = smearer.factors(pt_flat, ak.to_numpy(ak.flatten(jets.eta)),
                              ak.to_numpy(ak.flatten(rho)),
                              gen_pt_flat, has_gen, rng)
    report = {
        "applied": True,
        "source": smearer.source,
        "resolution": smearer.resolution_name,
        "scale_factor": smearer.scale_factor_name,
        "gen_matched_fraction": smearer.last_matched_fraction,
        "mean_factor": float(factors.mean()) if factors.size else None,
        "std_factor": float(factors.std()) if factors.size else None,
        "resolution_flow_hits": int(smearer.resolution.last_flow_count),
        "n_jets_smeared": n_flat,
    }
    return ak.unflatten(pt_flat * factors, counts), report


def extra_jet_block(jets, sel_leptons, any_leptons, photons, weights,
                    extra_present):
    """Parts C3 and C4: everything about the 3rd-and-later jets.

    Those are the jets that only exist in the events the excess lives in, so
    they are where a noise jet, a pileup jet or a misreconstructed lepton
    would show up if one were responsible.
    """
    order = ak.argsort(jets.pt, axis=1, ascending=False)
    ordered = jets[order]
    extra = ordered[ak.local_index(ordered, axis=1) >= 2]

    n_per_event = ak.to_numpy(ak.num(extra, axis=1))
    if n_per_event.sum() == 0:
        return {"xjet_n": 0.0, "xjet_n_raw": 0}
    per_jet_w = np.repeat(weights, n_per_event)

    block = {
        "xjet_n": float(per_jet_w.sum()),
        "xjet_n_raw": int(n_per_event.sum()),
        "xjet_pt": hist1d(extra.pt, XJET_PT_EDGES, per_jet_w),
        "xjet_eta": hist1d(extra.eta, XJET_ETA_EDGES, per_jet_w),
        "xjet_phi": hist1d(extra.phi, XJET_PHI_EDGES, per_jet_w),
    }
    eta_flat = ak.to_numpy(ak.flatten(extra.eta))
    phi_flat = ak.to_numpy(ak.flatten(extra.phi))
    occupancy, _, _ = np.histogram2d(
        eta_flat, phi_flat, bins=[XJET_OCC_ETA_EDGES, XJET_OCC_PHI_EDGES])
    block["xjet_occupancy_raw"] = occupancy.tolist()

    fails_lepveto = ak.to_numpy(ak.flatten(
        (extra.jetId & JETID_TIGHTLEPVETO_BIT) == 0))
    block["xjet_n_fail_tightlepveto"] = float(per_jet_w[fails_lepveto].sum())
    block["xjet_n_fail_tightlepveto_raw"] = int(fails_lepveto.sum())

    for name in ("chEmEF", "neEmEF", "chHEF", "neHEF"):
        if "Jet_" + name in extra_present:
            block["xjet_" + name] = hist1d(extra[name], FRACTION_EDGES, per_jet_w)
    if "Jet_chEmEF" in extra_present and "Jet_neEmEF" in extra_present:
        em = ak.to_numpy(ak.flatten(extra.chEmEF + extra.neEmEF))
        block["xjet_emfrac"] = np.histogram(
            em, bins=FRACTION_EDGES, weights=per_jet_w)[0].tolist()
        block["xjet_n_highEM"] = float(per_jet_w[em > 0.9].sum())
        block["xjet_n_highEM_raw"] = int((em > 0.9).sum())
    for name in ("nElectrons", "nMuons"):
        if "Jet_" + name in extra_present:
            counts = ak.to_numpy(ak.flatten(extra[name]))
            block["xjet_" + name] = np.bincount(
                np.clip(counts, 0, 3), weights=per_jet_w, minlength=4).tolist()

    block["xjet_dr_sel_lepton"] = hist1d(
        min_dr_to(extra, sel_leptons), DR_EDGES, per_jet_w)
    block["xjet_dr_any_lepton"] = hist1d(
        min_dr_to(extra, any_leptons), DR_EDGES, per_jet_w)
    if photons is not None:
        block["xjet_dr_photon"] = hist1d(
            min_dr_to(extra, photons), DR_EDGES, per_jet_w)
    return block


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--kind", required=True, choices=("data", "mc"))
    ap.add_argument("--dataset-label", required=True,
                    help="DoubleMuon / DoubleEG for data; MC for simulation")
    ap.add_argument("--record-id", type=int, required=True)
    ap.add_argument("--file-index", type=int, required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--jer-json", default=None,
                    help="the official jet_jerc.json.gz; MC only. Without it "
                         "Part C1 is skipped for this file.")
    ap.add_argument("--pu-json", default=None,
                    help="the official puWeights.json.gz; when given, MC "
                         "histograms are also filled pileup-weighted")
    ap.add_argument("--jer-seed", type=int, default=20261011,
                    help="stochastic-smearing seed; mixed with the record and "
                         "file index so two files never draw the same numbers")
    ap.add_argument("--validated-runs-json", default=DEFAULT_VALIDATED_RUNS_JSON)
    args = ap.parse_args()

    is_mc = args.kind == "mc"
    t0 = time.perf_counter()

    trigger_branches = sorted({p for paths in MATCHED4_TRIGGER_PATHS.values()
                               for p in paths} | {ELE27_PATH})
    required = (list(BASE_OBJECT_BRANCHES) + trigger_branches
                + list(MATCHED_MODE_EXTRA_BRANCHES) + ["PV_npvsGood"])
    if is_mc:
        required += ["genWeight", "L1PreFiringWeight_Nom", "Pileup_nTrueInt"]

    file_url = resolve_file_url(args.record_id, args.file_index)
    print("[{}] {}".format(args.dataset_label, file_url), flush=True)

    # Optional branches are read only if the file actually has them, so a
    # missing one degrades that one diagnostic instead of failing the job.
    import uproot
    optional = (list(OPTIONAL_JET_BRANCHES) + list(OPTIONAL_EVENT_BRANCHES)
                + list(OPTIONAL_PHOTON_BRANCHES))
    if is_mc:
        optional += list(OPTIONAL_MC_BRANCHES)
    with uproot.open(file_url) as handle:
        available = set(handle["Events"].keys())
        raw_factor_title = (
            " ".join(str(handle["Events"]["Jet_rawFactor"].title).split())
            if "Jet_rawFactor" in available else None)
        jet_pt_title = " ".join(str(handle["Events"]["Jet_pt"].title).split())
        jet_id_title = " ".join(str(handle["Events"]["Jet_jetId"].title).split())
    extra_present = sorted(set(optional) & available)
    missing = sorted(set(optional) - available)
    required += extra_present
    print("  optional branches present: {}".format(len(extra_present)), flush=True)
    if missing:
        print("  optional branches MISSING: {}".format(missing), flush=True)

    events, branch_titles = read_events(file_url, required, return_titles=True)
    n_read = len(events)

    # ---- C5 first: it is defined over every generated event ------------
    gen_block = None
    if is_mc:
        gen_njet_all, gen_ok_all, gen_flavour_all = gen_particle_level(
            events, extra_present)
        if gen_njet_all is not None:
            gen_weight = ak.to_numpy(events.genWeight).astype(np.float64)
            prefire = ak.to_numpy(
                events.L1PreFiringWeight_Nom).astype(np.float64)
            # A particle-level cross section is a statement about the
            # generator, so the headline numbers carry genWeight ALONE. The
            # L1 prefiring weight is a detector effect, and it is jet
            # dependent, so including it would quietly suppress exactly the
            # high-multiplicity bins this part is about. It is kept as a
            # second set of counts so the size of that effect is visible
            # rather than assumed.
            gen_block = {
                "weight_note": "the headline counts use genWeight only; the "
                               "'_prefire' counts add L1PreFiringWeight_Nom "
                               "so the size of that detector effect can be "
                               "read off",
                "sum_genweight_all_events": float(gen_weight.sum()),
                "sum_w_prefire_all_events": float((gen_weight * prefire).sum()),
                "n_all_events": int(n_read),
            }
            for channel, pdg in (("mumu", 13), ("ee", 11)):
                sel = gen_ok_all & (gen_flavour_all == pdg)
                gen_block[channel] = counts_entry(gen_njet_all[sel],
                                                  gen_weight[sel])
                gen_block[channel + "_prefire"] = counts_entry(
                    gen_njet_all[sel], (gen_weight * prefire)[sel])
                gen_block[channel + "_n_raw"] = int(sel.sum())

    if is_mc:
        if not is_simulation(events):
            raise SystemExit("--kind mc but the file is not simulation")
        events_golden = events
        n_after_golden = n_read
    else:
        validated = ValidatedRunsFilter(args.validated_runs_json)
        events_golden, gstats = apply_validated_runs_filter(events, validated)
        n_after_golden = gstats["n_after"]

    own_paths = (tuple(trigger_branches) if is_mc
                 else MATCHED4_TRIGGER_PATHS[args.dataset_label])
    events_trig, tstats = apply_trigger_requirement(
        events_golden, {"mode": "any", "paths": own_paths})
    n_after_trigger = tstats["n_after"]
    if n_after_trigger == 0:
        print("  no events after the trigger gate", flush=True)

    # ---- objects, exactly as delivered ---------------------------------
    muons = selection.select_muons(events_trig)
    electrons_pre = selection.select_electrons(events_trig)
    jets_split = selection.select_and_split_jets(
        events_trig, muons, electrons_pre, apply_lepton_cleaning=True)
    electrons, _n_removed, _mask = remove_electrons_overlapping_muons(
        electrons_pre, muons, dr_max=EMU_OVERLAP_DR_MAX, enabled=True)

    trigobj = ak.zip({
        "pt": events_trig.TrigObj_pt, "eta": events_trig.TrigObj_eta,
        "phi": events_trig.TrigObj_phi, "id": events_trig.TrigObj_id,
        "filterBits": events_trig.TrigObj_filterBits,
    })
    assert_trigobj_bit_meanings(branch_titles)
    acceptances = evaluate_four_acceptances(
        events_trig, muons, electrons, trigobj, "both")

    if is_mc:
        ele27 = ele27_candidate_acceptance(events_trig, electrons, trigobj)
        keep = mc_store_mask(acceptances, ele27)
    else:
        keep = acceptances[args.dataset_label]["accepted"]
        is_excl, _ov, _h = exclusive_mask_from_acceptances(
            acceptances, args.dataset_label)
        if args.dataset_label != DELIVERY_VETO_ORDER_4[0]:
            keep = keep & is_excl

    # ---- the alternative jet collections, built alongside --------------
    raw_jets = build_raw_jets(events_trig, extra_present)
    leptons_for_cleaning = ak.concatenate([muons, electrons_pre], axis=1)

    delivered_all = apply_jet_cuts(raw_jets, leptons_for_cleaning,
                                   JET_PT_MIN_GEV, selection.JET_ETA_MAX)
    paper_jets = apply_jet_cuts(raw_jets, leptons_for_cleaning,
                                PAPER_JET_PT_MIN, PAPER_JET_ETA_MAX)

    # cross-check: our rebuilt "all" collection minus b tags must reproduce
    # the delivery's own light jets event for event, or the rebuild is wrong
    rebuilt_light = delivered_all[
        ~(delivered_all.btagDeepFlavB > BTAG_DEEPFLAVB_MEDIUM_WP)]
    same = (ak.to_numpy(ak.num(rebuilt_light, axis=1))
            == ak.to_numpy(ak.num(jets_split["Jets"], axis=1)))
    if not bool(np.all(same)):
        raise SystemExit(
            "the rebuilt jet collection does not reproduce the delivered "
            "light jets event-for-event -- refusing to report")

    # ---- Version B and the final-state label ---------------------------
    n_lep_b = ak.to_numpy(ak.num(electrons[keep], axis=1)
                          + ak.num(muons[keep], axis=1)
                          + ak.num(jets_split["BJets"][keep], axis=1))
    rare4 = n_lep_b <= 4

    obj_record = selection.build_object_record(
        muons[keep], electrons[keep],
        {"Jets": jets_split["Jets"][keep], "BJets": jets_split["BJets"][keep]})
    exact_final_state_labels(obj_record[rare4])   # the same gate the pilot ran

    def kept(array):
        return array[keep][rare4]

    mu_kept = kept(muons)
    el_kept = kept(electrons)
    light_kept = kept(jets_split["Jets"])
    bjet_kept = kept(jets_split["BJets"])
    all_kept = kept(delivered_all)
    paper_kept = kept(paper_jets)
    n_mu = ak.to_numpy(ak.num(mu_kept, axis=1))
    n_el = ak.to_numpy(ak.num(el_kept, axis=1))

    photons_kept = None
    if "Photon_pt" in extra_present:
        photons_kept = kept(ak.zip({"pt": events_trig.Photon_pt,
                                    "eta": events_trig.Photon_eta,
                                    "phi": events_trig.Photon_phi}))
    # every lepton in the file, with no ID, isolation or pT requirement at
    # all -- Part C4's "is the extra jet really an unselected lepton?"
    any_leptons_kept = kept(ak.concatenate([
        ak.zip({"pt": events_trig.Muon_pt, "eta": events_trig.Muon_eta,
                "phi": events_trig.Muon_phi}),
        ak.zip({"pt": events_trig.Electron_pt, "eta": events_trig.Electron_eta,
                "phi": events_trig.Electron_phi}),
    ], axis=1))
    sel_leptons_kept = kept(leptons_for_cleaning)

    if is_mc:
        genw = ak.to_numpy(kept(events_trig.genWeight)).astype(np.float64)
        l1pf = ak.to_numpy(
            kept(events_trig.L1PreFiringWeight_Nom)).astype(np.float64)
        w_base = genw * l1pf
        w_pu = None
        if args.pu_json:
            ntrue = ak.to_numpy(kept(events_trig.Pileup_nTrueInt)).astype(np.float64)
            w_pu = w_base * load_pu(args.pu_json)(ntrue, "nominal")
    else:
        w_base = np.ones(len(n_mu), dtype=np.float64)
        w_pu = None

    # ---- C1: official JER smearing, MC only ----------------------------
    jer_info = {"applied": False}
    paper_jer = light_jer = all_jer = None
    if is_mc and args.jer_json:
        if "fixedGridRhoFastjetAll" not in extra_present:
            raise SystemExit("JER smearing needs fixedGridRhoFastjetAll")
        smearer = JerSmearer(args.jer_json)
        rng = np.random.default_rng(
            args.jer_seed + 1000 * args.record_id + args.file_index)
        smeared_pt, jer_info = smeared_jet_pt(
            events_trig, raw_jets, smearer, rng, extra_present)
        smeared_all = apply_jet_cuts(raw_jets, leptons_for_cleaning,
                                     JET_PT_MIN_GEV, selection.JET_ETA_MAX,
                                     pt_override=smeared_pt)
        smeared_paper = apply_jet_cuts(raw_jets, leptons_for_cleaning,
                                       PAPER_JET_PT_MIN, PAPER_JET_ETA_MAX,
                                       pt_override=smeared_pt)
        all_jer = kept(smeared_all)
        light_jer = kept(smeared_all[
            ~(smeared_all.btagDeepFlavB > BTAG_DEEPFLAVB_MEDIUM_WP)])
        paper_jer = kept(smeared_paper)

    # ---- C2: the jet energy scale scan, MC only ------------------------
    paper_jes = {}
    if is_mc:
        for shift in JES_SHIFTS:
            paper_jes[str(shift)] = kept(apply_jet_cuts(
                raw_jets, leptons_for_cleaning, PAPER_JET_PT_MIN,
                PAPER_JET_ETA_MAX, pt_override=raw_jets.pt * (1.0 + shift)))

    # ---- C6: the same gen jets, on the reco-selected events ------------
    # The gen jet count here is NOT gated on the particle-level Z selection:
    # the question C6 asks is what the generator put in the event that the
    # reconstruction then kept or lost, which is a statement about the jets
    # alone.
    gen_njet_trig = None
    if is_mc:
        gen_njet_trig, _gen_ok_trig, _gen_flavour_trig = gen_particle_level(
            events_trig, extra_present)
        if gen_njet_trig is not None:
            gen_njet_trig = njet_bin(
                gen_njet_trig[ak.to_numpy(keep)][rare4])

    # ---- per-channel histograms ----------------------------------------
    out_channels = {}
    for channel in CHANNELS:
        if channel == "mumu":
            sel = (n_mu == 2) & (n_el == 0)
            leptons = mu_kept
        else:
            sel = (n_el == 2) & (n_mu == 0)
            leptons = el_kept
        if not is_mc:
            want = "mumu" if args.dataset_label == "DoubleMuon" else "ee"
            if channel != want:
                out_channels[channel] = None
                continue
        if not np.any(sel):
            out_channels[channel] = {"n_z_events": 0}
            continue

        two = two_leading(leptons[sel], ("pt", "eta", "phi", "mass"))
        mass = dilepton_mass_arrays(
            two["pt"][0], two["eta"][0], two["phi"][0], two["mass"][0],
            two["pt"][1], two["eta"][1], two["phi"][1], two["mass"][1])
        position = np.nonzero(sel)[0]
        in_our_z = (mass >= Z_WINDOW[0]) & (mass <= Z_WINDOW[1])
        in_paper_z = ((mass >= PAPER_Z_WINDOW[0]) & (mass <= PAPER_Z_WINDOW[1])
                      & (two["pt"][0] > PAPER_LEAD_LEPTON_PT)
                      & (np.abs(two["eta"][0]) < PAPER_LEPTON_ETA_MAX)
                      & (np.abs(two["eta"][1]) < PAPER_LEPTON_ETA_MAX))

        idx = position[in_our_z]
        idx_paper = position[in_paper_z]
        if idx.size == 0:
            out_channels[channel] = {"n_z_events": 0}
            continue

        entry = {"n_z_events": int(idx.size),
                 "n_z_events_paper_window": int(idx_paper.size),
                 "sum_w": float(w_base[idx].sum())}

        def njets_of(collection, where):
            return ak.to_numpy(ak.num(collection[where], axis=1))

        series = [("delivered_light", light_kept, idx),
                  ("delivered_all", all_kept, idx),
                  ("delivered_bjets", bjet_kept, idx),
                  ("paperlike", paper_kept, idx),
                  ("paperlike_paperZ", paper_kept, idx_paper)]
        if paper_jer is not None:
            series += [("delivered_light_jer", light_jer, idx),
                       ("delivered_all_jer", all_jer, idx),
                       ("paperlike_jer", paper_jer, idx),
                       ("paperlike_paperZ_jer", paper_jer, idx_paper)]
        for name, collection, where in series:
            if where.size == 0:
                continue
            entry[name] = counts_entry(njets_of(collection, where), w_base[where])
            if w_pu is not None and not name.endswith("_jer"):
                entry[name + "_pu"] = counts_entry(
                    njets_of(collection, where), w_pu[where])

        for shift, collection in paper_jes.items():
            entry["paperlike_jes_" + shift] = counts_entry(
                njets_of(collection, idx), w_base[idx])

        if gen_njet_trig is not None:
            reco_n = njet_bin(njets_of(paper_kept, idx))
            matrix, _, _ = np.histogram2d(
                reco_n, gen_njet_trig[idx],
                bins=[np.arange(NJET_BINS + 1) - 0.5,
                      np.arange(NJET_BINS + 1) - 0.5],
                weights=w_base[idx])
            entry["reco_vs_gen"] = matrix.tolist()

        entry.update(extra_jet_block(
            paper_kept[idx], sel_leptons_kept[idx], any_leptons_kept[idx],
            photons_kept[idx] if photons_kept is not None else None,
            w_base[idx], extra_present))
        out_channels[channel] = entry

    payload = {
        "what": "Parts B and C jet-excess probe, one input file",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "kind": args.kind,
        "dataset_label": args.dataset_label,
        "record_id": args.record_id,
        "file_index": args.file_index,
        "file_url": file_url,
        "n_read": n_read,
        "n_after_golden_json": n_after_golden,
        "n_after_trigger": n_after_trigger,
        "n_stored_after_versionB": int(rare4.sum()),
        "optional_branches_present": extra_present,
        "optional_branches_missing": missing,
        "jet_pt_branch_title": jet_pt_title,
        "jet_id_branch_title": jet_id_title,
        "jet_rawfactor_branch_title": raw_factor_title,
        "jer": jer_info,
        "pu_json": args.pu_json,
        "jes_shifts": list(JES_SHIFTS),
        "z_window": list(Z_WINDOW),
        "paper_z_window": list(PAPER_Z_WINDOW),
        "gen_particle_level": gen_block,
        "definitions": {
            "delivered_light": "pT>30, |eta|<2.5, tight ID, dR>0.4, b excluded",
            "delivered_all": "the same, b-tagged jets counted back in",
            "paperlike": "pT>30, |eta|<2.4, tight ID, dR>0.4, all jets",
            "paperlike_paperZ": "paperlike jets + lead lepton pT>30, both "
                                "|eta|<2.4, mass 71-111",
            "residual_difference_from_paper": "the paper's subleading lepton "
                                              "threshold is 20 GeV; at reco "
                                              "level ours stays at the "
                                              "delivered 25 GeV",
        },
        "edges": {
            "xjet_pt": XJET_PT_EDGES.tolist(),
            "xjet_eta": XJET_ETA_EDGES.tolist(),
            "xjet_phi": XJET_PHI_EDGES.tolist(),
            "xjet_occ_eta": XJET_OCC_ETA_EDGES.tolist(),
            "xjet_occ_phi": XJET_OCC_PHI_EDGES.tolist(),
            "fraction": FRACTION_EDGES.tolist(),
            "dr": DR_EDGES.tolist(),
        },
        "channels": out_channels,
        "seconds": round(time.perf_counter() - t0, 1),
    }
    path = pathlib.Path(args.out)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")
    for channel, block in out_channels.items():
        if block:
            print("  {}: {:,} Z events".format(channel, block["n_z_events"]),
                  flush=True)
    print("wrote {}".format(path))
    return 0


if __name__ == "__main__":
    sys.exit(main())
