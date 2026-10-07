#!/usr/bin/env python
"""
SingleElectron Step 1, per-file measurement: Z->ee tag-and-probe for
HLT_Ele27_WPTight_Gsf (Step B) AND the offline-threshold cost/benefit scan
(Step D), in ONE pass over each file.

MEASUREMENT ONLY. Every production function is IMPORTED read-only and
never modified or re-implemented:
    studies.m0m1j0_cms.selection          object definitions
    run_dataset_on_file.remove_electrons_overlapping_muons   (dR < 0.12)
    run_dataset_on_file.trigobj_best_match                   (id-guarded matcher)
    run_dataset_on_file.evaluate_four_acceptances            (the four datasets)
    run_dataset_on_file.exact_final_state_labels             (Version B labels)
    services.parsing.validated_runs / trigger_requirements   (golden JSON, HLT)

STEP B -- Z->ee tag and probe, on SingleElectron data, golden lumis, with
HLT_Ele27_WPTight_Gsf fired:
  tag   : selected electron, offline pT > 30, NOT in the barrel-endcap gap,
          matched dR<0.1 to a TrigObj with id==11, bit 2, TrigObj_pt >= 27
  probe : any OTHER selected electron, opposite charge to the tag,
          81 < m(tag,probe) < 101 GeV
  pass  : probe matched dR<0.1 to a DIFFERENT TrigObj than the tag's, with
          id==11, bit 2 and TrigObj_pt >= 27
Both tag-probe orderings are used when both electrons qualify as tags.
Same-sign pairs are collected in the same window for background subtraction.

STEP D -- for each offline threshold T in 27/30/32/35, the candidate
acceptance (for measurement, NOT production):
  HLT_Ele27_WPTight_Gsf fired, AND >= 1 selected electron matched to a
  bit-2 id-11 TrigObj with TrigObj_pt >= 27, AND that electron's offline
  pT > T.
For the accepted events it also records which are accepted by NONE of the
four existing datasets (the gain if SingleElectron goes last), and their
Version B final-state labels.

Usage:
    python measure_singleelectron.py --era G --file-index 0 --out out.json
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

import awkward as ak  # noqa: E402
import numpy as np  # noqa: E402

from services.parsing.validated_runs import ValidatedRunsFilter, apply_validated_runs_filter  # noqa: E402
from services.parsing.trigger_requirements import apply_trigger_requirement  # noqa: E402
from studies.cms_datasets.cluster import run_dataset_on_file as drv  # noqa: E402
from studies.cms_datasets.electron_prep.common import eta_region, record_for  # noqa: E402
from studies.m0m1j0_cms import selection  # noqa: E402

ELE27 = "HLT_Ele27_WPTight_Gsf"
TRIGOBJ_BIT_WPTIGHT = 2          # "2 = 1e (WPTight)", read from the branch title at run time
ONLINE_PT_MIN = 27.0
TAG_OFFLINE_PT_MIN = 30.0
Z_WINDOW = (81.0, 101.0)
THRESHOLDS = (27.0, 30.0, 32.0, 35.0)

PROBE_PT_EDGES = [25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35,
                  37.5, 40, 45, 50, 60, 80, 120, 200]
MASS_EDGES = np.arange(60.0, 120.0001, 1.0)
REGIONS = ("barrel", "gap", "endcap")

# Other WPTight single-electron paths that exist in these files. They are
# NOT used in any acceptance here -- they are read only to quantify how
# ambiguous trigger-object bit 2 is, because bit 2's CMSSW filter pattern
# 'hltEle*WPTight*TrackIsoFilter*' is wildcarded on the threshold and on
# eta, so every one of these paths can set it.
OTHER_WPTIGHT_PATHS = (
    "HLT_Ele25_WPTight_Gsf",
    "HLT_Ele25_eta2p1_WPTight_Gsf",
    "HLT_Ele27_WPTight_Gsf_L1JetTauSeeded",
    "HLT_Ele27_eta2p1_WPTight_Gsf",
    "HLT_Ele32_eta2p1_WPTight_Gsf",
)

EXPECTED_BIT2_TITLE = "2 = 1e (WPTight)"
EXPECTED_ID11_TITLE = "11 = Electron"


def assert_bit_meanings(titles: dict) -> dict:
    """Stop unless the file's own branch titles still say bit 2 is the
    WPTight single-electron bit and id 11 is the electron."""
    bits = " ".join(str(titles.get("TrigObj_filterBits", "")).split())
    ids = " ".join(str(titles.get("TrigObj_id", "")).split())
    missing = []
    if EXPECTED_BIT2_TITLE not in bits:
        missing.append(("TrigObj_filterBits", EXPECTED_BIT2_TITLE))
    if EXPECTED_ID11_TITLE not in ids:
        missing.append(("TrigObj_id", EXPECTED_ID11_TITLE))
    if missing:
        raise RuntimeError(
            f"STOP: TrigObj branch titles do not carry the expected meanings: "
            f"{missing}. filterBits title={bits!r}; id title={ids!r}")
    return {"trigobj_filterbits_title": bits, "trigobj_id_title": ids,
            "bit2_meaning_confirmed": True}


def electrons_with_charge(events: ak.Array) -> ak.Array:
    """The production electron collection plus a `charge` passthrough.

    Charge is needed for the opposite-sign requirement but
    selection.select_electrons has no extra_fields parameter. This
    reproduces the production driver's OWN documented mechanism for the
    same problem (run_dataset_on_file.main's `electrons_diag`): rebuild the
    identical 3-condition mask from selection's own constants, slice the
    charge with it, and attach it with ak.with_field. The selection itself
    is still selection.select_electrons -- nothing is re-implemented."""
    electrons = selection.select_electrons(events)
    mask = (
        (events.Electron_pt > selection.ELECTRON_PT_MIN_GEV)
        & (abs(events.Electron_eta) < selection.ELECTRON_ETA_MAX)
        & (events.Electron_cutBased >= selection.ELECTRON_CUTBASED_MIN)
    )
    charge = events.Electron_charge[mask]
    assert ak.all(ak.num(charge, axis=1) == ak.num(electrons, axis=1)), (
        "the rebuilt electron mask does not select the same objects as "
        "selection.select_electrons -- refusing to attach a misaligned charge")
    return ak.with_field(electrons, charge, "charge")


def _bin_index(pt: np.ndarray) -> np.ndarray:
    idx = np.digitize(pt, PROBE_PT_EDGES) - 1
    idx[(pt < PROBE_PT_EDGES[0]) | (pt >= PROBE_PT_EDGES[-1])] = -1
    return idx


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--era", required=True, choices=["G", "H"])
    p.add_argument("--file-index", type=int, required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--validated-runs-json", default=drv.DEFAULT_VALIDATED_RUNS_JSON)
    args = p.parse_args()

    t0 = time.time()
    record_id = record_for("SingleElectron", args.era)
    needed_hlt = sorted({q for paths in drv.MATCHED4_TRIGGER_PATHS.values() for q in paths})
    required = (list(drv.BASE_OBJECT_BRANCHES) + needed_hlt
                + list(drv.MATCHED_MODE_EXTRA_BRANCHES) + [ELE27]
                + list(OTHER_WPTIGHT_PATHS))
    url = drv.resolve_file_url(record_id, args.file_index)
    print(f"[SingleElectron {args.era} {args.file_index}] {url}", flush=True)

    events, titles = drv.read_events(url, sorted(set(required)), return_titles=True)
    n_read = len(events)
    bit_check = assert_bit_meanings(titles)

    validated = ValidatedRunsFilter(args.validated_runs_json)
    events, _ = apply_validated_runs_filter(events, validated)
    n_golden = len(events)

    out = {
        "what": "SingleElectron Step 1: Z->ee tag-and-probe for Ele27 and the "
                "offline-threshold scan",
        "dataset": "SingleElectron", "era": args.era, "record_id": record_id,
        "file_index": args.file_index, "file_url": url,
        "git_commit": drv.git_commit_hash(REPO_ROOT),
        "n_read": n_read, "n_after_golden_json": n_golden,
        "trigobj_title_check": bit_check,
        "ele27_branch_present": True,
        "emu_overlap_dr_max_used": drv.EMU_OVERLAP_DR_MAX,
        "doubleeg_threshold_mode_used": drv.DOUBLEEG_THRESHOLD_MODE_DEFAULT,
    }

    # ---- bit-2 ambiguity diagnostic, BEFORE the Ele27 requirement -------
    # How often does a bit-2 trigger object with pT >= 27 exist in an event
    # where Ele27 did NOT fire? If that is ~0, then "bit 2 and pT >= 27" is
    # in practice equivalent to "passed Ele27", despite the shared pattern.
    trigobj_all = ak.zip({
        "pt": events.TrigObj_pt, "eta": events.TrigObj_eta, "phi": events.TrigObj_phi,
        "id": events.TrigObj_id, "filterBits": events.TrigObj_filterBits})
    qualifying = ((trigobj_all.id == drv.TRIGOBJ_ELECTRON_ID)
                  & ((trigobj_all.filterBits & TRIGOBJ_BIT_WPTIGHT) != 0)
                  & (trigobj_all.pt >= ONLINE_PT_MIN))
    has_qual = ak.to_numpy(ak.any(qualifying, axis=1))
    ele27_fired = ak.to_numpy(events[ELE27]).astype(bool)
    other_fired = np.zeros(len(events), dtype=bool)
    per_other = {}
    for path in OTHER_WPTIGHT_PATHS:
        f = ak.to_numpy(events[path]).astype(bool)
        per_other[path] = int(f.sum())
        other_fired |= f
    out["bit2_ambiguity"] = {
        "note": "bit 2's CMSSW filter pattern hltEle*WPTight*TrackIsoFilter* is "
                "wildcarded on threshold and eta, so these other WPTight paths "
                "present in the files can set it too. They are NOT used in any "
                "acceptance here.",
        "other_wptight_paths_fire_counts": per_other,
        "n_golden_events": int(n_golden),
        "n_ele27_fired": int(ele27_fired.sum()),
        "n_with_qualifying_bit2_object_pt27": int(has_qual.sum()),
        "n_qualifying_object_but_ele27_NOT_fired": int((has_qual & ~ele27_fired).sum()),
        "n_qualifying_and_ele27_not_fired_but_other_wptight_fired":
            int((has_qual & ~ele27_fired & other_fired).sum()),
        "n_ele27_fired_but_no_qualifying_object": int((ele27_fired & ~has_qual).sum()),
    }

    # ---- the Step B / Step D population --------------------------------
    events, _trig_stats = apply_trigger_requirement(
        events, {"mode": "any", "paths": [ELE27]})
    n_fired = len(events)
    out["n_after_ele27"] = n_fired
    print(f"  golden {n_golden} -> Ele27 fired {n_fired}", flush=True)

    if n_fired == 0:
        out["note"] = "no events after the Ele27 requirement"
        out["elapsed_sec"] = round(time.time() - t0, 1)
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(out, indent=2), encoding="utf-8")
        return

    muons = selection.select_muons(events)
    electrons_pre = electrons_with_charge(events)
    electrons, n_removed, _mask = drv.remove_electrons_overlapping_muons(
        electrons_pre, muons, dr_max=drv.EMU_OVERLAP_DR_MAX, enabled=True)
    out["n_electrons_removed_by_overlap_removal"] = int(n_removed.sum())

    trigobj = ak.zip({
        "pt": events.TrigObj_pt, "eta": events.TrigObj_eta, "phi": events.TrigObj_phi,
        "id": events.TrigObj_id, "filterBits": events.TrigObj_filterBits})

    # The production matcher, with the id guard. One call gives, per
    # electron, its best bit-2 match: online pT, dR and the TrigObj index.
    bk = drv.trigobj_best_match(electrons, trigobj, drv.TRIGOBJ_ELECTRON_ID,
                                TRIGOBJ_BIT_WPTIGHT)
    out["trigger_guard_violations"] = int(drv.count_trigger_guard_violations(
        bk, trigobj, drv.TRIGOBJ_ELECTRON_ID))

    is_matched = bk["is_matched"]
    best_pt = bk["best_pt"]
    best_idx = bk["best_index"]
    best_dr = bk["best_dr"]
    qualifies = is_matched & (best_pt >= ONLINE_PT_MIN)

    # A second matcher call with a LOOSER cone, for the dR<0.1 vs dR<0.2
    # cross-check the brief asks for.
    bk_loose = drv.trigobj_best_match(electrons, trigobj, drv.TRIGOBJ_ELECTRON_ID,
                                      TRIGOBJ_BIT_WPTIGHT, dr_max=0.2)
    qualifies_loose = bk_loose["is_matched"] & (bk_loose["best_pt"] >= ONLINE_PT_MIN)

    # ---- STEP B: build tag-probe pairs ---------------------------------
    import vector
    vector.register_awkward()
    p4 = vector.zip({"pt": electrons.pt, "eta": electrons.eta,
                     "phi": electrons.phi, "mass": electrons.mass})
    abs_eta = abs(electrons.eta)
    region_ok_tag = (abs_eta < 1.4442) | (abs_eta > 1.566)      # not in the gap
    is_tag = qualifies & (electrons.pt > TAG_OFFLINE_PT_MIN) & region_ok_tag

    # all ordered pairs (i != j) within an event
    idx = ak.local_index(electrons, axis=1)
    ti, pi = ak.unzip(ak.argcartesian([electrons, electrons]))
    keep_pair = ti != pi
    ti, pi = ti[keep_pair], pi[keep_pair]

    def take(arr, which):
        return arr[which]

    tag_is = take(is_tag, ti)
    pair_ok = tag_is
    t_p4 = take(p4, ti)
    p_p4 = take(p4, pi)
    mass = (t_p4 + p_p4).mass
    t_q = take(electrons.charge, ti)
    p_q = take(electrons.charge, pi)
    opposite = (t_q * p_q) < 0
    same = (t_q * p_q) > 0
    in_window = (mass > Z_WINDOW[0]) & (mass < Z_WINDOW[1])

    p_pt = take(electrons.pt, pi)
    p_abseta = take(abs_eta, pi)
    p_qual = take(qualifies, pi)
    p_qual_loose = take(qualifies_loose, pi)
    p_idx = take(best_idx, pi)
    t_idx = take(best_idx, ti)
    p_dr = take(best_dr, pi)
    different_object = p_idx != t_idx
    p_pass = p_qual & different_object

    def flat(x):
        return ak.to_numpy(ak.flatten(x, axis=None))

    sel_os = flat(pair_ok & opposite & in_window)
    sel_ss = flat(pair_ok & same & in_window)
    f_pt = flat(p_pt)
    f_abseta = flat(p_abseta)
    f_pass = flat(p_pass)
    f_qual = flat(p_qual)
    f_qual_loose = flat(p_qual_loose)
    f_sameobj = flat(pair_ok & opposite & in_window & p_qual & ~different_object)
    f_mass = flat(mass)
    f_os_all = flat(pair_ok & opposite)
    f_ss_all = flat(pair_ok & same)
    f_region = eta_region(f_abseta)

    bins = _bin_index(f_pt)
    tnp = {}
    for sign, sel in (("opposite_sign", sel_os), ("same_sign", sel_ss)):
        block = {}
        for reg in REGIONS:
            in_reg = sel & (f_region == reg)
            num = np.zeros(len(PROBE_PT_EDGES) - 1, dtype=np.int64)
            den = np.zeros(len(PROBE_PT_EDGES) - 1, dtype=np.int64)
            for b in range(len(PROBE_PT_EDGES) - 1):
                m = in_reg & (bins == b)
                den[b] = int(m.sum())
                num[b] = int((m & f_pass).sum())
            block[reg] = {"numerator": num.tolist(), "denominator": den.tolist()}
        tnp[sign] = block
    out["tagandprobe"] = {
        "pt_bin_edges": PROBE_PT_EDGES,
        "regions": list(REGIONS),
        "z_window_gev": list(Z_WINDOW),
        "tag_definition": "selected electron, offline pT > 30, not in the "
                          "barrel-endcap gap, matched dR<0.1 to id-11 bit-2 "
                          "TrigObj with TrigObj_pt >= 27",
        "pass_definition": "probe matched dR<0.1 to a DIFFERENT id-11 bit-2 "
                           "TrigObj with TrigObj_pt >= 27",
        "counts": tnp,
        "n_pairs_opposite_sign_in_window": int(sel_os.sum()),
        "n_pairs_same_sign_in_window": int(sel_ss.sum()),
        "n_pairs_probe_shares_tag_trigobj": int(f_sameobj.sum()),
        "matching_cone_crosscheck": {
            "note": "of probes in the Z window that qualify at dR<0.1, how many "
                    "also qualify at the looser dR<0.2 -- and vice versa",
            "n_qualify_dr01": int((sel_os & f_qual).sum()),
            "n_qualify_dr02": int((sel_os & f_qual_loose).sum()),
            "n_qualify_dr02_not_dr01": int((sel_os & f_qual_loose & ~f_qual).sum()),
        },
    }
    mh_os, _ = np.histogram(f_mass[f_os_all], bins=MASS_EDGES)
    mh_ss, _ = np.histogram(f_mass[f_ss_all], bins=MASS_EDGES)
    out["tagandprobe"]["mass_histograms"] = {
        "bin_edges_gev": MASS_EDGES.tolist(),
        "opposite_sign": mh_os.tolist(), "same_sign": mh_ss.tolist()}

    # ---- STEP D: the threshold scan ------------------------------------
    acceptances = drv.evaluate_four_acceptances(
        events, muons, electrons, trigobj, drv.DOUBLEEG_THRESHOLD_MODE_DEFAULT)
    accepted_by_any_existing = np.zeros(n_fired, dtype=bool)
    per_existing = {}
    for label in drv.DELIVERY_VETO_ORDER_4:
        a = acceptances[label]["accepted"]
        per_existing[label] = int(a.sum())
        accepted_by_any_existing |= a
    out["four_dataset_acceptance_counts_on_this_population"] = per_existing
    out["n_accepted_by_any_existing_dataset"] = int(accepted_by_any_existing.sum())

    jets = selection.select_and_split_jets(events, muons, electrons_pre,
                                           apply_lepton_cleaning=True)
    n_e = ak.to_numpy(ak.num(electrons, axis=1))
    n_m = ak.to_numpy(ak.num(muons, axis=1))
    n_b = ak.to_numpy(ak.num(jets["BJets"], axis=1))
    version_b_keep = (n_e + n_m + n_b) <= 4

    # offline pT of the matched (qualifying) electrons, per event
    qual_pt = ak.where(qualifies, electrons.pt, -np.inf)
    max_qual_pt = ak.to_numpy(ak.fill_none(ak.max(qual_pt, axis=1), -np.inf))

    scan = {}
    for T in THRESHOLDS:
        acc = max_qual_pt > T                      # Ele27 already required above
        gain = acc & ~accepted_by_any_existing
        obj_record = selection.build_object_record(
            muons[gain], electrons[gain],
            {"Jets": jets["Jets"][gain], "BJets": jets["BJets"][gain]})
        labels = drv.exact_final_state_labels(obj_record) if int(gain.sum()) else np.array([])
        vb = version_b_keep[gain]
        kept_labels = labels[vb] if labels.size else labels
        scan[str(T)] = {
            "n_accepted": int(acc.sum()),
            "n_gain_not_accepted_by_existing": int(gain.sum()),
            "n_gain_version_b_kept": int(vb.sum()) if labels.size else 0,
            "n_gain_version_b_rejected": int((~vb).sum()) if labels.size else 0,
            "final_state_counts": {k: int(v) for k, v in
                                   sorted(Counter(kept_labels.tolist()).items())},
        }
        print(f"  T={T}: accepted {int(acc.sum())}, gain {int(gain.sum())}", flush=True)
    out["threshold_scan"] = {
        "thresholds": list(THRESHOLDS),
        "rule": "Ele27 fired AND >=1 selected electron matched to an id-11 bit-2 "
                "TrigObj with TrigObj_pt >= 27 AND that electron's offline pT > T",
        "results": scan,
    }

    out["elapsed_sec"] = round(time.time() - t0, 1)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"  wrote {args.out} ({out['elapsed_sec']}s)", flush=True)


if __name__ == "__main__":
    main()
