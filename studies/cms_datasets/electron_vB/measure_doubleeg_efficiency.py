#!/usr/bin/env python
"""
Step D: DoubleEG trigger-MATCHING efficiency, per file.

This measurement decides D4's default `doubleeg_threshold_mode`. One array
subjob per DoubleEG file; aggregate_doubleeg_efficiency.py combines the
per-file JSONs, computes Clopper-Pearson intervals, applies the FIXED
decision criterion and makes the plots.

Population (exactly production's own, nothing new):
  * golden-JSON (validated) lumis only;
  * HLT_Ele23_Ele12_CaloIdL_TrackIdL_IsoVL_DZ fired;
  * the production object selection (studies.m0m1j0_cms.selection,
    imported unchanged) PLUS the D3 electron-muon overlap removal
    (run_dataset_on_file.remove_electrons_overlapping_muons, the
    production function itself);
  * >= 2 selected electrons.

Definitions:
  leading / subleading = 1st / 2nd selected electron by OFFLINE pT, after
      overlap removal, with the collection SORTED by pT here. That sort is
      not cosmetic: VERIFIED BY RUNNING on a real UL2016 NanoAODv9 file,
      the Electron collection is not always pT-descending (~1.3% of events
      raw, 0.0006% after our selection), so index 0/1 is not reliably the
      leading/subleading electron. The pre-sort violation count is
      reported per file.
  matched = there exists a TrigObj with id == 11 and filterBits & 16
      ("2e") within dR < 0.1 -- the production matcher
      run_dataset_on_file.trigobj_best_match, not a copy.
  region  = barrel (|eta| < 1.4442), gap (1.4442 <= |eta| <= 1.566) or
      endcap (1.566 < |eta| < 2.5), on Electron_eta -- the SAME variable
      the electron selection cuts on and the SAME boundaries the
      electron_prep measurement used (electron_prep/common.py). Gap
      electrons DO pass the selection (there is no gap veto), so the gap
      is reported as its own third region and never merged.

Four efficiencies, each in the Step D pT bins and in the two summary bins:
  a_leading_tagged     numerator: leading matched;    denominator: subleading matched
  b_subleading_tagged  numerator: subleading matched; denominator: leading matched AND leading pT > 30
  c_leading_untagged   numerator: leading matched;    denominator: all events in the population
  d_subleading_untagged numerator: subleading matched; denominator: leading pT > 30
  d2_subleading_plain  numerator: subleading matched; denominator: all events in the population
(d2 is reported alongside d so the "leading pT > 30" part and the "leading
is matched" part of b's tag can be separated; the task asks for d without
the TAG requirement, which is the matched part.)

Each is split by the region of the PROBED electron.

Usage:
    python measure_doubleeg_efficiency.py --era G --file-index 0 \
        --out /storage/.../doubleeg_eff/job_0.json
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

import awkward as ak  # noqa: E402
import numpy as np  # noqa: E402

from studies.cms_datasets.cluster import run_dataset_on_file as drv  # noqa: E402
from studies.cms_datasets.electron_prep import common as eprep  # noqa: E402
from studies.m0m1j0_cms import selection  # noqa: E402

# Step D's own pT binning, plus the two summary bins.
PT_BIN_EDGES = [25.0, 26.0, 27.0, 28.0, 29.0, 30.0, 35.0, 40.0, 50.0, 100.0]
SUMMARY_BINS = {"25-30": (25.0, 30.0), "gt30": (30.0, np.inf)}
REGIONS = ("barrel", "gap", "endcap")
MEASUREMENTS = ("a_leading_tagged", "b_subleading_tagged", "c_leading_untagged",
                "d_subleading_untagged", "d2_subleading_plain")

BRANCHES = (
    "run", "luminosityBlock", "event",
    "nMuon", "Muon_pt", "Muon_eta", "Muon_phi", "Muon_mass",
    "Muon_mediumId", "Muon_pfRelIso04_all",
    "nElectron", "Electron_pt", "Electron_eta", "Electron_phi", "Electron_mass",
    "Electron_cutBased",
) + eprep.TRIGOBJ_BRANCHES + ("HLT_Ele23_Ele12_CaloIdL_TrackIdL_IsoVL_DZ",)


def _bin_index(pt: np.ndarray) -> np.ndarray:
    """Index into PT_BIN_EDGES[:-1], or -1 if outside the binned range."""
    idx = np.digitize(pt, PT_BIN_EDGES) - 1
    idx[(pt < PT_BIN_EDGES[0]) | (pt >= PT_BIN_EDGES[-1])] = -1
    return idx


def _accumulate(counts: dict, measurement: str, region: np.ndarray, pt: np.ndarray,
                num: np.ndarray, den: np.ndarray):
    """Add (numerator, denominator) counts for one measurement, per region,
    per pT bin and per summary bin."""
    bin_idx = _bin_index(pt)
    block = counts.setdefault(measurement, {})
    for reg in REGIONS:
        in_reg = (region == reg)
        reg_block = block.setdefault(reg, {"bins": {}, "summary": {}, "all_pt": [0, 0]})
        reg_block["all_pt"][0] += int((num & den & in_reg).sum())
        reg_block["all_pt"][1] += int((den & in_reg).sum())
        for b in range(len(PT_BIN_EDGES) - 1):
            key = f"{PT_BIN_EDGES[b]:g}-{PT_BIN_EDGES[b + 1]:g}"
            sel = in_reg & (bin_idx == b)
            cur = reg_block["bins"].setdefault(key, [0, 0])
            cur[0] += int((num & den & sel).sum())
            cur[1] += int((den & sel).sum())
        for key, (lo, hi) in SUMMARY_BINS.items():
            sel = in_reg & (pt > lo) & (pt <= hi) if np.isfinite(hi) else in_reg & (pt > lo)
            cur = reg_block["summary"].setdefault(key, [0, 0])
            cur[0] += int((num & den & sel).sum())
            cur[1] += int((den & sel).sum())


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--era", required=True, choices=["G", "H"])
    p.add_argument("--file-index", type=int, required=True)
    p.add_argument("--out", required=True)
    args = p.parse_args()

    t0 = time.time()
    record_id = eprep.record_for("DoubleEG", args.era)
    url, events, read_stats = eprep.read_file(record_id, args.file_index, BRANCHES)
    print(f"[DoubleEG {args.era} file {args.file_index}] {url}", flush=True)
    print(f"  read {read_stats['n_read']} -> golden {read_stats['n_after_golden_json']}", flush=True)

    # D2/D6 side-check, free here: are all four datasets' HLT branches present?
    import uproot
    available = set(uproot.open(url)["Events"].keys())
    hlt_presence = {path: (path in available)
                    for paths in drv.MATCHED4_TRIGGER_PATHS.values() for path in paths}

    fired = eprep.fire_mask(events, ["HLT_Ele23_Ele12_CaloIdL_TrackIdL_IsoVL_DZ"])
    events = events[fired]
    n_fired = len(events)

    muons = selection.select_muons(events)
    electrons_pre = selection.select_electrons(events)
    electrons, n_removed, _mask = drv.remove_electrons_overlapping_muons(
        electrons_pre, muons, dr_max=drv.EMU_OVERLAP_DR_MAX, enabled=True)

    has_two = ak.to_numpy(ak.num(electrons, axis=1) >= 2)
    electrons = electrons[has_two]
    n_population = len(electrons)
    # VERIFIED BY RUNNING on a real UL2016 NanoAODv9 file: the Electron
    # collection is NOT always pT-descending (about 1.3% of events in the
    # raw collection, 0.0006% after our selection). "Leading / subleading
    # by offline pT" therefore has to be an explicit sort, never index 0/1.
    # The count before sorting is recorded and reported.
    n_not_sorted = 0
    if n_population:
        _nonincr = ak.all(ak.fill_none(
            electrons.pt[:, :-1] >= electrons.pt[:, 1:], True), axis=1)
        n_not_sorted = int(n_population - int(ak.sum(ak.fill_none(_nonincr, True))))
        electrons = electrons[ak.argsort(electrons.pt, axis=1, ascending=False)]
    print(f"  fired {n_fired}, >=2 selected electrons after overlap removal {n_population}",
          flush=True)

    trigobj = eprep.zip_trigobj(events[has_two])
    bk = drv.trigobj_best_match(electrons, trigobj, drv.TRIGOBJ_ELECTRON_ID,
                                drv.TRIGOBJ_BIT_E_2E)
    guard_violations = drv.count_trigger_guard_violations(
        bk, trigobj, drv.TRIGOBJ_ELECTRON_ID)

    counts: dict = {}
    if n_population:
        pt = electrons.pt
        lead_pt = ak.to_numpy(pt[:, 0]).astype(float)
        sub_pt = ak.to_numpy(pt[:, 1]).astype(float)
        lead_eta = np.abs(ak.to_numpy(electrons.eta[:, 0]).astype(float))
        sub_eta = np.abs(ak.to_numpy(electrons.eta[:, 1]).astype(float))
        lead_reg = eprep.eta_region(lead_eta)
        sub_reg = eprep.eta_region(sub_eta)
        lead_matched = ak.to_numpy(bk["is_matched"][:, 0]).astype(bool)
        sub_matched = ak.to_numpy(bk["is_matched"][:, 1]).astype(bool)
        all_true = np.ones(n_population, dtype=bool)
        lead_above30 = lead_pt > drv.DOUBLEEG_OFFLINE_PT_MIN_GEV

        _accumulate(counts, "a_leading_tagged", lead_reg, lead_pt, lead_matched, sub_matched)
        _accumulate(counts, "b_subleading_tagged", sub_reg, sub_pt, sub_matched,
                    lead_matched & lead_above30)
        _accumulate(counts, "c_leading_untagged", lead_reg, lead_pt, lead_matched, all_true)
        _accumulate(counts, "d_subleading_untagged", sub_reg, sub_pt, sub_matched, lead_above30)
        _accumulate(counts, "d2_subleading_plain", sub_reg, sub_pt, sub_matched, all_true)

        region_counts = {
            "leading": {r: int((lead_reg == r).sum()) for r in REGIONS + ("outside",)},
            "subleading": {r: int((sub_reg == r).sum()) for r in REGIONS + ("outside",)},
        }
    else:
        region_counts = {}

    out = {
        "what": "Step D: DoubleEG trigger-matching efficiency, one file",
        "dataset": "DoubleEG", "era": args.era, "record_id": record_id,
        "file_index": args.file_index, "file_url": url,
        "git_commit": drv.git_commit_hash(REPO_ROOT),
        "n_read": read_stats["n_read"],
        "n_after_golden_json": read_stats["n_after_golden_json"],
        "n_after_path_fired": n_fired,
        "n_electrons_removed_by_overlap_removal": int(n_removed.sum()),
        "n_population_ge2_selected_electrons": n_population,
        "n_events_electron_collection_not_pt_descending": n_not_sorted,
        "trigger_guard_violations": int(guard_violations),
        "hlt_branch_presence_all_four_datasets": hlt_presence,
        "pt_bin_edges": PT_BIN_EDGES,
        "summary_bins": {k: [v[0], None if not np.isfinite(v[1]) else v[1]]
                         for k, v in SUMMARY_BINS.items()},
        "regions": list(REGIONS),
        "region_counts": region_counts,
        "counts": counts,
        "elapsed_sec": round(time.time() - t0, 1),
    }
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"  wrote {args.out} ({out['elapsed_sec']}s)", flush=True)


if __name__ == "__main__":
    main()
