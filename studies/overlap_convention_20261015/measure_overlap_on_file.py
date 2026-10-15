#!/usr/bin/env python
"""
Jet-lepton overlap conventions, side by side, on ONE CMS data file.
Read-only measurement (15 Oct 2026). Nothing in the production path changes.

Every step is the production's own code, imported, never re-typed:
  * reading, golden JSON, own trigger, trigger-object table and its bit check,
    the e-mu rule and the four-dataset acceptance:
        studies/cms_datasets/cluster/run_dataset_on_file.py (matched4 path)
  * muons, electrons, jets (pt/eta/tight ID, b/light split, the optional
    dR<0.4 cleaning):  studies/m0m1j0_cms/selection.py
  * the ATLAS #32 two-step overlap removal:
        services/parsing/event_selection.py::apply_overlap_removal (upstream)
  * the final-state label: run_dataset_on_file.exact_final_state_labels on
    selection.build_object_record, with the production's N = e+m+b <= 4 rule.

Variants (all on the same events, same objects up to the jet-lepton step):
  V0   no jet-lepton cleaning: select_and_split_jets(..., apply_lepton_cleaning=False)
  V1   current CMS one-step:   select_and_split_jets(..., apply_lepton_cleaning=True)
       -- exactly the production call, i.e. against the electrons BEFORE the
       e-mu rule removes any (that is the production order).
  V2   #32 two-step: apply_overlap_removal(cuts={"e_mu_dr": 0.0}) on
       Electrons (after OUR e-mu rule) / Muons / Jets = V0 light jets.
       e_mu_dr = 0.0 disables upstream's own e-mu step (dR < 0 never holds),
       so the CMS e-mu rule, applied first, is the one in force.
       b-jets: "V2"  keeps the CMS dR<0.4-cleaned b-jets (the V1 b-jets);
               "V2u" leaves b-jets uncleaned (V0 b-jets), as #32 does.
  Order relative to trigger matching:
       "A" (upstream's order: parsing_handler applies trigger selection
           before overlap removal): acceptance evaluated on the leptons
           BEFORE the #32 step, exactly as production; #32 then changes
           only the objects that represent the event.
       "B": acceptance re-evaluated on the leptons AFTER the #32 step.

Writes <out>/overlap_<dataset>_<file_index>.json (counts, histograms, label
tables) and <out>/overlap_<dataset>_<file_index>.npz (per-event leading-jet
dR arrays, for exact medians).

Run:  python studies/overlap_convention_20261015/measure_overlap_on_file.py \
          --dataset-label DoubleMuon --record-id 30522 --file-index 0 --out-dir <dir>
"""
from __future__ import annotations

import argparse
import json
import logging
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

import awkward as ak  # noqa: E402
import numpy as np  # noqa: E402

from services.parsing.event_selection import apply_overlap_removal  # noqa: E402
from services.parsing.trigger_requirements import apply_trigger_requirement  # noqa: E402
from services.parsing.validated_runs import ValidatedRunsFilter, apply_validated_runs_filter  # noqa: E402
from studies.m0m1j0_cms import selection  # noqa: E402
from studies.cms_datasets.cluster import run_dataset_on_file as R  # noqa: E402

V2_CUTS = {"e_mu_dr": 0.0}
DR_EDGES = np.round(np.arange(0.0, 1.0001, 0.02), 10)       # (b): 0-1.0, 0.02 bins
PT_EDGES = np.arange(25.0, 305.0, 5.0)                       # (c): lepton pT, 25-300 GeV
NJ_MAX = 10                                                  # jet multiplicity 0..10, last = >=10
REJECTED = "REJECTED_N>4"


# --------------------------------------------------------------------------
# small helpers (bookkeeping only -- no selection logic lives here)
# --------------------------------------------------------------------------

def n_of(arr) -> np.ndarray:
    return ak.to_numpy(ak.num(arr, axis=1)).astype(np.int64)


def min_dr(a, b) -> ak.Array:
    """Per object of `a`: dR to the nearest object of `b` (None if b empty).
    Uses the production's own dR spelling (run_dataset_on_file.delta_r_wrapped)."""
    return ak.min(R.delta_r_wrapped(a, b), axis=-1)


def leading(arr) -> ak.Array:
    order = ak.argsort(arr.pt, axis=1, ascending=False)
    return ak.pad_none(arr[order], 1, axis=1, clip=True)[:, 0]


def lead_dr_to(jets, objs) -> np.ndarray:
    """dR from each event's leading jet to its nearest object of `objs`;
    NaN if the event has no jet or no such object."""
    lj_list = ak.singletons(leading(jets))               # [ev][0 or 1]
    d = ak.firsts(min_dr(lj_list, objs))
    return ak.to_numpy(ak.fill_none(d, np.nan)).astype(np.float64)


def is_in(before, after) -> ak.Array:
    """Per object of `before`: is it still present in `after` (same event)?
    `after` is always a subset of `before` here, so (pt, eta, phi) identity
    is exact -- the values are the very same floats."""
    a, b = ak.unzip(ak.cartesian([before, after], nested=True))
    same = (a.pt == b.pt) & (a.eta == b.eta) & (a.phi == b.phi)
    return ak.fill_none(ak.any(same, axis=-1), False)


def hist(values, edges) -> dict:
    v = np.asarray(values, dtype=np.float64)
    v = v[np.isfinite(v)]
    counts, _ = np.histogram(v, bins=edges)
    return {"edges": [float(x) for x in edges], "counts": counts.astype(int).tolist(),
            "underflow": int((v < edges[0]).sum()), "overflow": int((v >= edges[-1]).sum()),
            "n": int(v.size)}


def jet_mult(counts: np.ndarray) -> list:
    c = np.minimum(counts, NJ_MAX)
    return np.bincount(c, minlength=NJ_MAX + 1).astype(int).tolist()


def labels_rare4(muons, electrons, light, bjets) -> np.ndarray:
    """The production's delivered label: exact label for N = e+m+b <= 4,
    REJECTED otherwise (run_dataset_on_file's rare4 rule)."""
    rec = selection.build_object_record(muons, electrons, {"Jets": light, "BJets": bjets})
    n = n_of(electrons) + n_of(muons) + n_of(bjets)
    out = np.full(len(rec), REJECTED, dtype=object)
    keep = n <= 4
    if keep.any():
        out[keep] = R.exact_final_state_labels(rec[keep])
    return out


def counter(labels) -> dict:
    return dict(Counter(labels.tolist()))


# --------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset-label", required=True, choices=R.DELIVERY_VETO_ORDER_4)
    ap.add_argument("--record-id", type=int, required=True)
    ap.add_argument("--file-index", type=int, required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--max-events", type=int, default=None, help="testing only")
    args = ap.parse_args()
    logging.basicConfig(level=logging.WARNING)
    t0 = time.time()
    label = args.dataset_label

    # ---- the production's matched4 path, up to the jet-lepton step --------
    own_paths = R.MATCHED4_TRIGGER_PATHS[label]
    trig = []
    for paths in R.MATCHED4_TRIGGER_PATHS.values():
        trig.extend(paths)
    required = (list(R.BASE_OBJECT_BRANCHES) + sorted(set(trig))
                + list(R.MATCHED_MODE_EXTRA_BRANCHES))
    url = R.resolve_file_url(args.record_id, args.file_index)
    if args.max_events:
        # testing only: the first N entries, through the production's own
        # chunk reader (the full run uses R.read_events, as production does)
        import uproot
        tree = uproot.open(url)["Events"]
        events = R._read_chunk_with_retry(tree, required, 0, args.max_events, url)
        titles = {b: tree[b].title for b in required}
    else:
        events, titles = R.read_events(url, required, return_titles=True)
    n_read = len(events)
    golden = ValidatedRunsFilter(str(REPO_ROOT / R.DEFAULT_VALIDATED_RUNS_JSON))
    events_golden, gstats = apply_validated_runs_filter(events, golden)
    et, tstats = apply_trigger_requirement(events_golden, {"mode": "any", "paths": own_paths})

    muons = selection.select_muons(et, extra_fields={"charge": et.Muon_charge})
    electrons_sel = selection.select_electrons(et)
    jets_v1 = selection.select_and_split_jets(et, muons, electrons_sel, apply_lepton_cleaning=True)
    jets_v0 = selection.select_and_split_jets(et, muons, electrons_sel, apply_lepton_cleaning=False)

    trigobj = ak.zip({"pt": et.TrigObj_pt, "eta": et.TrigObj_eta, "phi": et.TrigObj_phi,
                      "id": et.TrigObj_id, "filterBits": et.TrigObj_filterBits})
    R.assert_trigobj_bit_meanings(titles)
    electrons, n_e_removed_emu, _ = R.remove_electrons_overlapping_muons(
        electrons_sel, muons, dr_max=R.EMU_OVERLAP_DR_MAX, enabled=True)

    mode = R.DOUBLEEG_THRESHOLD_MODE_DEFAULT
    acc_a = R.evaluate_four_acceptances(et, muons, electrons, trigobj, mode)
    keep_a = np.asarray(acc_a[label]["accepted"], dtype=bool)
    excl_a = np.asarray(R.exclusive_mask_from_acceptances(acc_a, label)[0], dtype=bool)

    # ---- V2: upstream's #32 function on the CMS objects ---------------------
    v2_in = ak.zip({"Electrons": electrons, "Muons": muons, "Jets": jets_v0["Jets"]}, depth_limit=1)
    v2_out = apply_overlap_removal(v2_in, cuts=V2_CUTS)
    e2, m2, j2 = v2_out["Electrons"], v2_out["Muons"], v2_out["Jets"]
    # the function must not have touched anything it should not have
    assert len(v2_out) == len(et)
    assert bool(ak.all(n_of(e2) <= n_of(electrons))) and bool(ak.all(n_of(m2) <= n_of(muons)))

    acc_b = R.evaluate_four_acceptances(et, m2, e2, trigobj, mode)
    keep_b = np.asarray(acc_b[label]["accepted"], dtype=bool)
    excl_b = np.asarray(R.exclusive_mask_from_acceptances(acc_b, label)[0], dtype=bool)

    b_v1, b_v0 = jets_v1["BJets"], jets_v0["BJets"]
    leptons = ak.concatenate([muons, electrons], axis=1)       # selected, after e-mu
    leptons2 = ak.concatenate([m2, e2], axis=1)                # after #32

    out = {
        "what": "jet-lepton overlap conventions on one file (read-only measurement)",
        "git_commit": subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT,
                                     capture_output=True, text=True).stdout.strip(),
        "dataset": label, "record_id": args.record_id, "file_index": args.file_index,
        "file_url": url, "n_read": n_read, "max_events": args.max_events,
        "n_after_golden_json": int(gstats["n_after"]), "n_after_own_trigger": int(len(et)),
        "n_accepted_orderA": int(keep_a.sum()), "n_accepted_orderB": int(keep_b.sum()),
        "n_accepted_A_not_B": int((keep_a & ~keep_b).sum()),
        "n_accepted_B_not_A": int((keep_b & ~keep_a).sum()),
        "n_exclusive_accepted_orderA": int((keep_a & excl_a).sum()),
        "n_exclusive_accepted_orderB": int((keep_b & excl_b).sum()),
        "n_electrons_removed_by_emu_rule": int(n_e_removed_emu.sum()),
        "v2_cuts_passed_to_apply_overlap_removal": V2_CUTS,
    }

    # ---- (a) the September number, and its electron twin --------------------
    jets_all_v0 = ak.concatenate([jets_v0["Jets"], b_v0], axis=1)
    arrays = {}
    a_res = {}
    for pop_name, ev_mask in (("triggered", np.ones(len(et), dtype=bool)), ("accepted", keep_a)):
        has_jet = n_of(jets_all_v0) >= 1
        pops = {
            "mumu": ev_mask & has_jet & (n_of(muons) >= 2),
            "ee": ev_mask & has_jet & (n_of(electrons) >= 2),
            "ll": ev_mask & has_jet & (n_of(leptons) >= 2),
        }
        d_mu = lead_dr_to(jets_all_v0, muons)
        d_e = lead_dr_to(jets_all_v0, electrons)
        d_l = lead_dr_to(jets_all_v0, leptons)
        d_mu_light = lead_dr_to(jets_v0["Jets"], muons)
        for pn, pm in pops.items():
            key = f"{pop_name}_{pn}"
            a_res[key] = {
                "n_events": int(pm.sum()),
                "n_lead_jet_within_0p4_of_muon": int((d_mu[pm] < 0.4).sum()),
                "n_lead_jet_within_0p4_of_electron": int((d_e[pm] < 0.4).sum()),
                "n_lead_jet_within_0p4_of_any_lepton": int((d_l[pm] < 0.4).sum()),
            }
            arrays[f"a_{key}_dr_mu"] = d_mu[pm]
            arrays[f"a_{key}_dr_e"] = d_e[pm]
            arrays[f"a_{key}_dr_l"] = d_l[pm]
            arrays[f"a_{key}_dr_mu_lightonly"] = d_mu_light[pm & (n_of(jets_v0["Jets"]) >= 1)]
    out["a_leading_jet_overlap_V0"] = a_res
    out["a_note"] = ("leading jet = highest-pT jet of V0 (light + b, pt>30, |eta|<2.5, tight ID, "
                     "no cleaning). 'triggered' = golden JSON + own trigger fired (the September "
                     "population for mumu); 'accepted' = production matched4 acceptance. Electrons "
                     "are after the CMS e-mu rule.")

    # ---- (b) dR(jet, nearest selected lepton), V0 jets, accepted events -----
    b_res = {}
    for jname, jcol in (("all", jets_all_v0), ("light", jets_v0["Jets"]), ("b", b_v0)):
        jk = jcol[keep_a]
        d_any = ak.to_numpy(ak.fill_none(ak.flatten(min_dr(jk, leptons[keep_a]), axis=1), np.nan))
        d_m = ak.to_numpy(ak.fill_none(ak.flatten(min_dr(jk, muons[keep_a]), axis=1), np.nan))
        d_e = ak.to_numpy(ak.fill_none(ak.flatten(min_dr(jk, electrons[keep_a]), axis=1), np.nan))
        nearest_is_mu = np.where(np.isnan(d_e), True, np.where(np.isnan(d_m), False, d_m <= d_e))
        b_res[jname] = {
            "n_jets": int(len(d_any)),
            "n_jets_no_lepton_in_event": int(np.isnan(d_any).sum()),
            "hist_dr_nearest_lepton": hist(d_any, DR_EDGES),
            "hist_dr_nearest_lepton_when_nearest_is_muon": hist(d_any[nearest_is_mu], DR_EDGES),
            "hist_dr_nearest_lepton_when_nearest_is_electron": hist(d_any[~nearest_is_mu], DR_EDGES),
            "n_below_0p2": int((d_any < 0.2).sum()),
            "n_0p2_to_0p4": int(((d_any >= 0.2) & (d_any < 0.4)).sum()),
            "n_below_0p2_nearest_muon": int(((d_any < 0.2) & nearest_is_mu).sum()),
            "n_0p2_to_0p4_nearest_muon": int(((d_any >= 0.2) & (d_any < 0.4) & nearest_is_mu).sum()),
            "n_below_0p2_nearest_electron": int(((d_any < 0.2) & ~nearest_is_mu).sum()),
            "n_0p2_to_0p4_nearest_electron": int(((d_any >= 0.2) & (d_any < 0.4) & ~nearest_is_mu).sum()),
        }
    out["b_dr_jet_nearest_lepton_V0_accepted"] = b_res

    # ---- (c) what V2's steps removed (order A population) -------------------
    ka = keep_a
    jl0, jl2 = jets_v0["Jets"][ka], j2[ka]
    rem_jet_mask = ~is_in(jl0, jl2)        # V0 light jets that are not in V2's output
    rem_jets = jl0[rem_jet_mask]
    d_rem_e = ak.to_numpy(ak.fill_none(ak.flatten(min_dr(rem_jets, electrons[ka]), axis=1), np.nan))
    d_rem_m = ak.to_numpy(ak.fill_none(ak.flatten(min_dr(rem_jets, muons[ka]), axis=1), np.nan))
    n_jets_removed = int((n_of(jl0) - n_of(jl2)).sum())
    assert n_jets_removed == int(ak.sum(rem_jet_mask))

    def removed(before, after):
        return before[~is_in(before, after)], before

    rem_m, all_m = removed(muons[ka], m2[ka])
    rem_e, all_e = removed(electrons[ka], e2[ka])
    assert int(ak.sum(n_of(rem_m))) == int((n_of(muons[ka]) - n_of(m2[ka])).sum())
    assert int(ak.sum(n_of(rem_e))) == int((n_of(electrons[ka]) - n_of(e2[ka])).sum())

    # trigger-object matching of the removed leptons (production matcher)
    def matched_any(objs, obj_id, bits):
        m = None
        for bit in bits:
            bk = R.trigobj_best_match(objs, trigobj[ka], obj_id, bit)
            m = bk["is_matched"] if m is None else (m | bk["is_matched"])
        return m

    mu_match = matched_any(muons[ka], R.TRIGOBJ_MUON_ID, (R.TRIGOBJ_BIT_TRKISOVVL, R.TRIGOBJ_BIT_ISO))
    e_match = matched_any(electrons[ka], R.TRIGOBJ_ELECTRON_ID, (R.TRIGOBJ_BIT_E_2E, R.TRIGOBJ_BIT_E_1E1MU))
    m_is_rem = ~is_in(muons[ka], m2[ka])
    e_is_rem = ~is_in(electrons[ka], e2[ka])
    lost_any = (n_of(m2[ka]) < n_of(muons[ka])) | (n_of(e2[ka]) < n_of(electrons[ka]))
    rem_m_iso = ak.to_numpy(ak.flatten(rem_m.pfRelIso04_all))
    out["c_v2_removals_orderA"] = {
        "n_accepted_events": int(ka.sum()),
        "n_light_jets_V0": int(n_of(jl0).sum()),
        "n_light_jets_removed_by_0p2_steps": n_jets_removed,
        "n_removed_jets_within_0p2_of_an_electron": int((d_rem_e < 0.2).sum()),
        "n_removed_jets_within_0p2_of_a_muon": int((d_rem_m < 0.2).sum()),
        "n_muons_selected": int(n_of(muons[ka]).sum()),
        "n_muons_removed_by_0p4_step": int(n_of(rem_m).sum()),
        "n_electrons_selected": int(n_of(electrons[ka]).sum()),
        "n_electrons_removed_by_0p4_step": int(n_of(rem_e).sum()),
        "n_events_losing_ge1_lepton": int(lost_any.sum()),
        "n_events_losing_ge1_muon": int((n_of(m2[ka]) < n_of(muons[ka])).sum()),
        "n_events_losing_ge1_electron": int((n_of(e2[ka]) < n_of(electrons[ka])).sum()),
        "removed_leptons_pass_production_id_iso": (
            "ALL, by construction: the #32 step only ever removes leptons that already passed the "
            "production selection (muons: pT>25, |eta|<2.4, mediumId, pfRelIso04_all<0.15; "
            "electrons: pT>25, |eta|<2.5, cutBased>=3 medium, which includes isolation)."),
        "n_removed_muons_pfRelIso04_below_0p06": int((rem_m_iso < 0.06).sum()),
        "n_removed_muons_pfRelIso04_0p06_to_0p15": int(((rem_m_iso >= 0.06) & (rem_m_iso < 0.15)).sum()),
        "n_removed_electrons_cutBased_tight4": int(ak.sum(rem_e.cutBased >= 4)),
        "n_removed_electrons_cutBased_medium3": int(ak.sum(rem_e.cutBased == 3)),
        "n_removed_muons_trigger_matched": int(ak.sum(mu_match[m_is_rem])),
        "n_removed_electrons_trigger_matched": int(ak.sum(e_match[e_is_rem])),
        "hist_pt_all_selected_muons": hist(ak.to_numpy(ak.flatten(all_m.pt)), PT_EDGES),
        "hist_pt_removed_muons": hist(ak.to_numpy(ak.flatten(rem_m.pt)), PT_EDGES),
        "hist_pt_all_selected_electrons": hist(ak.to_numpy(ak.flatten(all_e.pt)), PT_EDGES),
        "hist_pt_removed_electrons": hist(ak.to_numpy(ak.flatten(rem_e.pt)), PT_EDGES),
    }

    # ---- (d) residual contamination (order A, accepted events) --------------
    d_res = {}
    variants_jets = {
        "V0": (jets_v0["Jets"], b_v0, muons, electrons),
        "V1": (jets_v1["Jets"], b_v1, muons, electrons),
        "V2": (j2, b_v1, m2, e2),
        "V2u": (j2, b_v0, m2, e2),
    }
    for vn, (lj, bj, mm, ee) in variants_jets.items():
        allj = ak.concatenate([lj, bj], axis=1)[ka]
        surv = ak.concatenate([mm, ee], axis=1)[ka]
        orig = leptons[ka]
        has = n_of(allj) >= 1
        has_l = n_of(lj[ka]) >= 1
        d_s = lead_dr_to(allj, surv)
        d_o = lead_dr_to(allj, orig)
        d_sl = lead_dr_to(lj[ka], surv)
        d_ol = lead_dr_to(lj[ka], orig)
        d_res[vn] = {
            "n_events_with_a_jet": int(has.sum()),
            "n_lead_jet_within_0p4_of_surviving_lepton": int((d_s[has] < 0.4).sum()),
            "n_lead_jet_within_0p4_of_originally_selected_lepton": int((d_o[has] < 0.4).sum()),
            "n_events_with_a_light_jet": int(has_l.sum()),
            "n_lead_light_jet_within_0p4_of_surviving_lepton": int((d_sl[has_l] < 0.4).sum()),
            "n_lead_light_jet_within_0p4_of_originally_selected_lepton": int((d_ol[has_l] < 0.4).sum()),
        }
    out["d_residual_contamination_accepted"] = d_res

    # ---- jet multiplicities (plot 2), accepted events ------------------------
    out["jet_multiplicity_accepted"] = {
        vn: {"light": jet_mult(n_of(lj[ka])), "light_plus_b": jet_mult(n_of(lj[ka]) + n_of(bj[ka]))}
        for vn, (lj, bj, _m, _e) in variants_jets.items()
    }

    # ---- (e) categories ------------------------------------------------------
    lab = {
        "V0": labels_rare4(muons, electrons, jets_v0["Jets"], b_v0),
        "V1": labels_rare4(muons, electrons, jets_v1["Jets"], b_v1),
        "V2": labels_rare4(m2, e2, j2, b_v1),
        "V2u": labels_rare4(m2, e2, j2, b_v0),
    }
    cats = {}
    for pop, (k1, k2) in {
        "inclusive_orderA": (keep_a, keep_a),
        "exclusive_orderA": (keep_a & excl_a, keep_a & excl_a),
        "inclusive_orderB": (keep_a, keep_b),
        "exclusive_orderB": (keep_a & excl_a, keep_b & excl_b),
    }.items():
        entry = {"V1": counter(lab["V1"][k1]), "V0": counter(lab["V0"][k1])}
        for vn in ("V2", "V2u"):
            entry[vn] = counter(lab[vn][k2])
            # event-level transitions V1 -> V2: an event present in only one
            # population is counted as moving to/from "NOT_ACCEPTED"
            union = k1 | k2
            l1 = np.where(k1, lab["V1"], "NOT_ACCEPTED")[union]
            l2 = np.where(k2, lab[vn], "NOT_ACCEPTED")[union]
            moved = l1 != l2
            entry[f"n_events_V1_population"] = int(k1.sum())
            entry[f"n_events_{vn}_population"] = int(k2.sum())
            entry[f"n_events_changing_category_V1_to_{vn}"] = int(moved.sum())
            entry[f"transitions_V1_to_{vn}"] = {f"{a} -> {b}": int(n) for (a, b), n in
                                                Counter(zip(l1[moved].tolist(), l2[moved].tolist())).items()}
        cats[pop] = entry
    out["e_categories"] = cats

    # production cross-check: V1 inclusive labels must equal the production's
    # rare4 inclusive label counts for this file (compared by the merge step)
    out["elapsed_sec"] = round(time.time() - t0, 1)

    od = Path(args.out_dir)
    od.mkdir(parents=True, exist_ok=True)
    stem = od / f"overlap_{label}_{args.file_index}"
    stem.with_suffix(".json").write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")
    np.savez_compressed(stem.with_suffix(".npz"), **arrays)
    print(f"wrote {stem}.json/.npz in {out['elapsed_sec']} s; accepted A={out['n_accepted_orderA']} "
          f"B={out['n_accepted_orderB']}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
