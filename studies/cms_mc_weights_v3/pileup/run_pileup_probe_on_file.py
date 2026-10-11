#!/usr/bin/env python
"""
Part B: the pileup fingerprint probe, one input file per job.

The pilot shards store per-entry pileup (`_mcraw_puntrue`) but not per-event
vertex counts and not individual jet properties, so this re-reads a SUBSET of
files to get `PV_npvsGood`, the jet pT spectrum and `Jet_puId`.

**It reuses the delivered selection unmodified**, by importing from
`studies/cms_datasets/cluster/run_dataset_on_file.py` and
`studies/m0m1j0_cms/selection.py`: the same muon/electron/jet selection, the
same electron-muon overlap removal, the same four acceptances, the same
Version B (rare4) rule and the same exact final-state labels. Nothing in
either module is changed.

Z events are defined exactly as the pilot's P3 did:
  * the `matched4` population of the file's own dataset,
  * Version B (electrons + muons + b-jets <= 4),
  * a final state with exactly 2 same-flavour leptons and 0 of the other
    flavour,
  * dilepton mass in 76-106 GeV.

Data de-duplication: for this diagnostic, mumu events are taken from
DoubleMuon files and ee events from DoubleEG files only. DoubleMuon is the
highest-priority dataset so it contributes its INCLUSIVE acceptance, and
DoubleEG contributes its EXCLUSIVE one -- the same rule the delivery builder
uses. (For a 0-muon ee event the exclusive mask is almost always already
true, since DoubleMuon/SingleMuon acceptance needs trigger-matched muons; it
is applied anyway rather than assumed.)

Jet `puId` is recovered WITHOUT touching the selection: the raw jet record is
built with the extra `puId` field and pushed through the selection's own
`_clean_and_cut_jets`, which only ever applies boolean masks, so extra fields
survive untouched. The result is asserted to have the same per-event light-jet
counts as `select_and_split_jets` itself.

Output: ONE small JSON of pre-binned histograms per input file. No per-event
files are written (the account is near its inode quota).
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
    BTAG_DEEPFLAVB_MEDIUM_WP, _clean_and_cut_jets,
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
from studies.cms_mc_weights_v3.pileup.pu_weights import load as load_pu  # noqa: E402

# ---- binning, fixed here so every job produces addable histograms --------
NPVS_EDGES = np.arange(0.0, 81.0, 1.0)          # PV_npvsGood
NJET_BINS = 6                                   # 0,1,2,3,4,5+
JET_PT_THRESHOLDS = (30.0, 40.0, 50.0)          # 30 is the delivered one
JET3_PT_EDGES = np.arange(30.0, 205.0, 5.0)
JET3_ABSETA_EDGES = np.arange(0.0, 2.6, 0.1)
NTRUEINT_EDGES = np.arange(0.0, 100.0, 1.0)
Z_WINDOW = (76.0, 106.0)

CHANNELS = ("mumu", "ee")


def _njet_bin(n):
    return np.clip(np.asarray(n, dtype=np.int64), 0, NJET_BINS - 1)


def _dilepton_mass(leptons: ak.Array) -> np.ndarray:
    """Invariant mass of the two leading leptons, by pT. Only called on
    events already known to hold exactly two of them."""
    order = ak.argsort(leptons.pt, axis=1, ascending=False)
    lep = leptons[order]
    px = lep.pt * np.cos(lep.phi)
    py = lep.pt * np.sin(lep.phi)
    pz = lep.pt * np.sinh(lep.eta)
    e = np.sqrt(px ** 2 + py ** 2 + pz ** 2 + lep.mass ** 2)
    sx, sy, sz, se = (ak.sum(px, axis=1), ak.sum(py, axis=1),
                      ak.sum(pz, axis=1), ak.sum(e, axis=1))
    m2 = se ** 2 - sx ** 2 - sy ** 2 - sz ** 2
    return np.sqrt(np.maximum(ak.to_numpy(m2), 0.0))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--kind", required=True, choices=("data", "mc"))
    ap.add_argument("--dataset-label", required=True,
                    help="DoubleMuon / DoubleEG for data; MC for simulation")
    ap.add_argument("--record-id", type=int, required=True)
    ap.add_argument("--file-index", type=int, required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--pu-json", default=None,
                    help="the official puWeights.json.gz; when given, MC "
                         "histograms are also filled pileup-weighted")
    ap.add_argument("--validated-runs-json", default=DEFAULT_VALIDATED_RUNS_JSON)
    args = ap.parse_args()

    is_mc = args.kind == "mc"
    t0 = time.perf_counter()

    # ---- branches ------------------------------------------------------
    trigger_branches = sorted({p for paths in MATCHED4_TRIGGER_PATHS.values()
                               for p in paths} | {ELE27_PATH})
    required = (list(BASE_OBJECT_BRANCHES) + trigger_branches
                + list(MATCHED_MODE_EXTRA_BRANCHES) + ["PV_npvsGood"])
    if is_mc:
        required += ["genWeight", "L1PreFiringWeight_Nom", "Pileup_nTrueInt"]

    file_url = resolve_file_url(args.record_id, args.file_index)
    print(f"[{args.dataset_label}] {file_url}", flush=True)

    # Jet_puId is optional: check it exists before requiring it.
    import uproot
    with uproot.open(file_url) as f:
        available = set(f["Events"].keys())
        has_puid = "Jet_puId" in available
        puid_title = (" ".join(str(f["Events"]["Jet_puId"].title).split())
                      if has_puid else None)
    if has_puid:
        required.append("Jet_puId")
    print(f"  Jet_puId present: {has_puid}", flush=True)

    events, branch_titles = read_events(file_url, required, return_titles=True)
    n_read = len(events)

    # ---- golden JSON (data) / simulation assertion (MC) ----------------
    if is_mc:
        if not is_simulation(events):
            raise SystemExit("--kind mc but the file is not simulation")
        events_golden = events
        n_after_golden = n_read
    else:
        vr = ValidatedRunsFilter(args.validated_runs_json)
        events_golden, gstats = apply_validated_runs_filter(events, vr)
        n_after_golden = gstats["n_after"]

    # ---- trigger gate --------------------------------------------------
    if is_mc:
        own_paths = tuple(trigger_branches)
    else:
        own_paths = MATCHED4_TRIGGER_PATHS[args.dataset_label]
    events_trig, tstats = apply_trigger_requirement(
        events_golden, {"mode": "any", "paths": own_paths})
    n_after_trigger = tstats["n_after"]
    if n_after_trigger == 0:
        print("  no events after the trigger gate", flush=True)

    # ---- objects, exactly as delivered ---------------------------------
    muons = selection.select_muons(events_trig)
    electrons_pre = selection.select_electrons(events_trig)
    jets = selection.select_and_split_jets(events_trig, muons, electrons_pre,
                                           apply_lepton_cleaning=True)
    electrons, _n_removed, _mask = remove_electrons_overlapping_muons(
        electrons_pre, muons, dr_max=EMU_OVERLAP_DR_MAX, enabled=True)
    # jets are cleaned against the PRE-removal electrons, exactly as the
    # driver does (it calls select_and_split_jets before the removal).

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
        is_excl = np.ones(len(keep), dtype=bool)
    else:
        keep = acceptances[args.dataset_label]["accepted"]
        is_excl, _ov, _h = exclusive_mask_from_acceptances(
            acceptances, args.dataset_label)
    # The delivery takes DoubleMuon inclusive and every other dataset
    # exclusive. DoubleMuon is index 0 of DELIVERY_VETO_ORDER_4.
    if not is_mc and args.dataset_label != DELIVERY_VETO_ORDER_4[0]:
        keep = keep & is_excl

    # ---- light jets WITH puId, via the selection's own cut function ----
    raw_fields = {
        "pt": events_trig.Jet_pt, "eta": events_trig.Jet_eta,
        "phi": events_trig.Jet_phi, "mass": events_trig.Jet_mass,
        "jetId": events_trig.Jet_jetId,
        "btagDeepFlavB": events_trig.Jet_btagDeepFlavB,
    }
    if has_puid:
        raw_fields["puId"] = events_trig.Jet_puId
    raw_jets = ak.zip(raw_fields)
    raw_light = raw_jets[~(raw_jets.btagDeepFlavB > BTAG_DEEPFLAVB_MEDIUM_WP)]
    light_with_puid = _clean_and_cut_jets(raw_light, muons, electrons_pre,
                                          apply_lepton_cleaning=True)
    same = ak.to_numpy(ak.num(light_with_puid, axis=1)) == ak.to_numpy(
        ak.num(jets["Jets"], axis=1))
    if not bool(np.all(same)):
        raise SystemExit(
            "the puId-carrying light-jet collection does not match the "
            "selection's own light jets event-for-event -- refusing to report")

    # ---- Version B and the final-state label ---------------------------
    n_lep_b = ak.to_numpy(ak.num(electrons[keep], axis=1)
                          + ak.num(muons[keep], axis=1)
                          + ak.num(jets["BJets"][keep], axis=1))
    rare4 = n_lep_b <= 4

    obj_record = selection.build_object_record(
        muons[keep], electrons[keep],
        {"Jets": jets["Jets"][keep], "BJets": jets["BJets"][keep]})
    labels = exact_final_state_labels(obj_record[rare4])

    mu_kept = muons[keep][rare4]
    el_kept = electrons[keep][rare4]
    lj_kept = light_with_puid[keep][rare4]
    bj_kept = jets["BJets"][keep][rare4]
    npvs = ak.to_numpy(events_trig.PV_npvsGood[keep][rare4]).astype(np.float64)

    n_mu = ak.to_numpy(ak.num(mu_kept, axis=1))
    n_el = ak.to_numpy(ak.num(el_kept, axis=1))

    if is_mc:
        genw = ak.to_numpy(events_trig.genWeight[keep][rare4]).astype(np.float64)
        l1pf = ak.to_numpy(
            events_trig.L1PreFiringWeight_Nom[keep][rare4]).astype(np.float64)
        ntrue = ak.to_numpy(
            events_trig.Pileup_nTrueInt[keep][rare4]).astype(np.float64)
        w_base = genw * l1pf
        if args.pu_json:
            pu = load_pu(args.pu_json)
            w_pu = w_base * pu(ntrue, "nominal")
        else:
            w_pu = None
    else:
        w_base = np.ones(len(npvs), dtype=np.float64)
        w_pu = None
        ntrue = None

    # ---- per-channel histograms ----------------------------------------
    out_channels = {}
    for channel in CHANNELS:
        if channel == "mumu":
            sel = (n_mu == 2) & (n_el == 0)
            leptons = mu_kept
        else:
            sel = (n_el == 2) & (n_mu == 0)
            leptons = el_kept
        # for data, only take the channel this dataset is the source of
        if not is_mc:
            want = "mumu" if args.dataset_label == "DoubleMuon" else "ee"
            if channel != want:
                out_channels[channel] = None
                continue
        if not np.any(sel):
            out_channels[channel] = {"n_z_events": 0}
            continue

        mass = _dilepton_mass(leptons[sel])
        inz = (mass >= Z_WINDOW[0]) & (mass <= Z_WINDOW[1])
        idx = np.nonzero(sel)[0][inz]
        if idx.size == 0:
            out_channels[channel] = {"n_z_events": 0}
            continue

        npv_z = npvs[idx]
        w_z = w_base[idx]
        wpu_z = w_pu[idx] if w_pu is not None else None
        jets_z = lj_kept[idx]
        jpt = jets_z.pt

        entry = {"n_z_events": int(idx.size), "sum_w": float(w_z.sum())}

        # njets at each threshold, and npvs x njet (>=30 GeV) for B2
        for thr in JET_PT_THRESHOLDS:
            nj = _njet_bin(ak.to_numpy(ak.sum(jpt > thr, axis=1)))
            key = f"njets{int(thr)}"
            entry[key] = np.bincount(nj, weights=w_z, minlength=NJET_BINS).tolist()
            entry[key + "_sumw2"] = np.bincount(
                nj, weights=w_z ** 2, minlength=NJET_BINS).tolist()
            entry[key + "_raw"] = np.bincount(nj, minlength=NJET_BINS).tolist()
            if wpu_z is not None:
                entry[key + "_pu"] = np.bincount(
                    nj, weights=wpu_z, minlength=NJET_BINS).tolist()
                entry[key + "_pu_sumw2"] = np.bincount(
                    nj, weights=wpu_z ** 2, minlength=NJET_BINS).tolist()

        nj30 = _njet_bin(ak.to_numpy(ak.sum(jpt > 30.0, axis=1)))
        h2, _, _ = np.histogram2d(nj30, npv_z,
                                  bins=[np.arange(NJET_BINS + 1) - 0.5, NPVS_EDGES],
                                  weights=w_z)
        entry["npvs_by_njet30"] = h2.tolist()
        h2r, _, _ = np.histogram2d(nj30, npv_z,
                                   bins=[np.arange(NJET_BINS + 1) - 0.5, NPVS_EDGES])
        entry["npvs_by_njet30_raw"] = h2r.tolist()
        if wpu_z is not None:
            h2p, _, _ = np.histogram2d(
                nj30, npv_z, bins=[np.arange(NJET_BINS + 1) - 0.5, NPVS_EDGES],
                weights=wpu_z)
            entry["npvs_by_njet30_pu"] = h2p.tolist()

        # 3rd-leading jet in >=3-jet events (B4)
        ge3 = nj30 >= 3
        if np.any(ge3):
            j3 = jets_z[ge3]
            order = ak.argsort(j3.pt, axis=1, ascending=False)
            j3s = j3[order]
            third_pt = ak.to_numpy(j3s.pt[:, 2])
            third_eta = np.abs(ak.to_numpy(j3s.eta[:, 2]))
            w3 = w_z[ge3]
            entry["jet3_pt"] = np.histogram(third_pt, bins=JET3_PT_EDGES,
                                            weights=w3)[0].tolist()
            entry["jet3_abseta"] = np.histogram(third_eta, bins=JET3_ABSETA_EDGES,
                                                weights=w3)[0].tolist()
            entry["jet3_pt_raw"] = np.histogram(third_pt, bins=JET3_PT_EDGES)[0].tolist()
            entry["jet3_abseta_raw"] = np.histogram(third_eta,
                                                    bins=JET3_ABSETA_EDGES)[0].tolist()

        # pileup-jet ID failure fraction per njet bin (B5), diagnostic only
        if has_puid:
            fail_n = np.zeros(NJET_BINS)
            tot_n = np.zeros(NJET_BINS)
            fail_lowpt = np.zeros(NJET_BINS)
            tot_lowpt = np.zeros(NJET_BINS)
            passes_loose = (jets_z.puId & 1) != 0
            lowpt = jets_z.pt < 50.0
            n_per_ev = ak.to_numpy(ak.num(jets_z, axis=1))
            n_fail_ev = ak.to_numpy(ak.sum(~passes_loose, axis=1))
            n_fail_low = ak.to_numpy(ak.sum((~passes_loose) & lowpt, axis=1))
            n_low = ak.to_numpy(ak.sum(lowpt, axis=1))
            for b in range(NJET_BINS):
                m = nj30 == b
                if np.any(m):
                    tot_n[b] = float((n_per_ev[m] * w_z[m]).sum())
                    fail_n[b] = float((n_fail_ev[m] * w_z[m]).sum())
                    tot_lowpt[b] = float((n_low[m] * w_z[m]).sum())
                    fail_lowpt[b] = float((n_fail_low[m] * w_z[m]).sum())
            entry["pujet_total_by_njet"] = tot_n.tolist()
            entry["pujet_fail_by_njet"] = fail_n.tolist()
            entry["pujet_total_lowpt_by_njet"] = tot_lowpt.tolist()
            entry["pujet_fail_lowpt_by_njet"] = fail_lowpt.tolist()

        if is_mc:
            entry["ntrueint"] = np.histogram(
                ntrue[idx], bins=NTRUEINT_EDGES, weights=w_z)[0].tolist()
        out_channels[channel] = entry

    payload = {
        "what": "Part B pileup fingerprint probe, one input file",
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
        "jet_puid_present": has_puid,
        "jet_puid_title": puid_title,
        "pu_json": args.pu_json,
        "z_window": list(Z_WINDOW),
        "jet_pt_thresholds": list(JET_PT_THRESHOLDS),
        "npvs_edges": NPVS_EDGES.tolist(),
        "jet3_pt_edges": JET3_PT_EDGES.tolist(),
        "jet3_abseta_edges": JET3_ABSETA_EDGES.tolist(),
        "ntrueint_edges": NTRUEINT_EDGES.tolist(),
        "channels": out_channels,
        "seconds": round(time.perf_counter() - t0, 1),
    }
    path = pathlib.Path(args.out)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")
    for ch, e in out_channels.items():
        if e:
            print(f"  {ch}: {e['n_z_events']:,} Z events", flush=True)
    print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
