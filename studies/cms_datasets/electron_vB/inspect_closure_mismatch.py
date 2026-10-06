#!/usr/bin/env python
"""
Why do a handful of events in the closure test get different acceptance
flags depending on which dataset's file they were read from?

For each given (run, lumi, event) key this finds every closure part that
holds it, then goes back to the ORIGINAL NanoAOD files and prints, side by
side, what each dataset's own copy of that collision actually contains:
the four datasets' HLT decisions, the raw and selected object
multiplicities, the selected objects' kinematics, and the four acceptance
flags recomputed on the spot.

If the two copies disagree on the HLT bits or on the reconstructed objects,
the difference is in the DATA (two independently produced copies of the
same collision), not in this code. That is the question this script
answers; it asserts nothing.

Usage:
    python inspect_closure_mismatch.py --parts-dir /storage/.../closure/parts \
        --keys 281707:478:663374369,281707:104:29222538 \
        --out evidence/E3_mismatch_inspection.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

import awkward as ak  # noqa: E402
import numpy as np  # noqa: E402

from studies.cms_datasets.cluster import run_dataset_on_file as drv  # noqa: E402
from studies.cms_datasets.electron_prep.common import record_for  # noqa: E402
from studies.m0m1j0_cms import selection  # noqa: E402

KEY_DTYPE = np.dtype([("run", "u4"), ("lumi", "u4"), ("event", "u8")])


def locate(parts: Path, keys: np.ndarray) -> dict:
    """{key tuple: [(dataset, era, file_index), ...]}"""
    found = {tuple(int(x) for x in k): [] for k in keys}
    for f in sorted(parts.glob("keys_*.npz")):
        stem = f.stem[len("keys_"):]
        dataset, era, idx = stem.rsplit("_", 2)
        with np.load(f) as z:
            arr = z["keys"]
        if arr.size == 0:
            continue
        order = np.argsort(arr)
        srt = arr[order]
        pos = np.clip(np.searchsorted(srt, keys), 0, srt.size - 1)
        hit = srt[pos] == keys
        for k in keys[hit]:
            found[tuple(int(x) for x in k)].append((dataset, era, int(idx)))
    return found


def describe(dataset: str, era: str, file_index: int, key: tuple) -> dict:
    record_id = record_for(dataset, era)
    needed_hlt = sorted({p for paths in drv.MATCHED4_TRIGGER_PATHS.values() for p in paths})
    required = list(drv.BASE_OBJECT_BRANCHES) + needed_hlt + list(drv.MATCHED_MODE_EXTRA_BRANCHES)
    url = drv.resolve_file_url(record_id, file_index)
    events = drv.read_events(url, required)
    sel = ak.to_numpy((events.run == key[0]) & (events.luminosityBlock == key[1])
                      & (events.event == key[2]))
    n_copies = int(sel.sum())
    if n_copies == 0:
        return {"dataset": dataset, "era": era, "file_index": file_index,
                "file_url": url, "n_copies_in_file": 0}
    ev = events[sel]
    muons = selection.select_muons(ev)
    electrons_pre = selection.select_electrons(ev)
    electrons, n_removed, _m = drv.remove_electrons_overlapping_muons(
        electrons_pre, muons, dr_max=drv.EMU_OVERLAP_DR_MAX, enabled=True)
    trigobj = ak.zip({"pt": ev.TrigObj_pt, "eta": ev.TrigObj_eta, "phi": ev.TrigObj_phi,
                      "id": ev.TrigObj_id, "filterBits": ev.TrigObj_filterBits})
    out = {
        "dataset": dataset, "era": era, "file_index": file_index, "file_url": url,
        "n_copies_in_file": n_copies,
        "hlt": {p: bool(ak.to_numpy(ev[p])[0]) for p in needed_hlt},
        "n_raw": {"Muon": int(ak.to_numpy(ev.nMuon)[0]),
                  "Electron": int(ak.to_numpy(ev.nElectron)[0]),
                  "Jet": int(ak.to_numpy(ev.nJet)[0]),
                  "TrigObj": int(ak.to_numpy(ev.nTrigObj)[0])},
        "n_selected": {"muons": int(ak.num(muons, axis=1)[0]),
                       "electrons_pre_removal": int(ak.num(electrons_pre, axis=1)[0]),
                       "electrons": int(ak.num(electrons, axis=1)[0])},
        "n_electrons_removed": int(n_removed[0]),
        "selected_muon_pt": [round(float(x), 4) for x in ak.to_list(muons.pt[0])],
        "selected_electron_pt": [round(float(x), 4) for x in ak.to_list(electrons.pt[0])],
        "raw_muon_pt": [round(float(x), 4) for x in ak.to_list(ev.Muon_pt[0])],
        "raw_electron_pt": [round(float(x), 4) for x in ak.to_list(ev.Electron_pt[0])],
    }
    for mode in ("leading_only", "both"):
        acc = drv.evaluate_four_acceptances(ev, muons, electrons, trigobj, mode)
        out[f"acceptance_{mode}"] = {l: bool(acc[l]["accepted"][0])
                                     for l in drv.DELIVERY_VETO_ORDER_4}
    return out


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--parts-dir", required=True)
    p.add_argument("--keys", required=True, help="comma-separated run:lumi:event")
    p.add_argument("--out", required=True)
    args = p.parse_args()

    key_list = []
    for spec in args.keys.split(","):
        r, l, e = spec.split(":")
        key_list.append((int(r), int(l), int(e)))
    keys = np.array(key_list, dtype=KEY_DTYPE)

    where = locate(Path(args.parts_dir), keys)
    print("located:")
    for k, v in where.items():
        print(f"  {k}: {v}")

    report = []
    for k, places in where.items():
        entry = {"key": list(k), "held_by": [list(x) for x in places], "copies": []}
        for dataset, era, idx in places:
            entry["copies"].append(describe(dataset, era, idx, k))
        # Where do the copies disagree?
        hlts = [c.get("hlt") for c in entry["copies"] if c.get("hlt")]
        objs = [c.get("n_selected") for c in entry["copies"] if c.get("n_selected")]
        accs = [c.get("acceptance_leading_only") for c in entry["copies"]
                if c.get("acceptance_leading_only")]
        entry["hlt_identical_across_copies"] = bool(len(hlts) > 1 and all(h == hlts[0] for h in hlts))
        entry["selected_objects_identical_across_copies"] = bool(
            len(objs) > 1 and all(o == objs[0] for o in objs))
        entry["acceptance_identical_across_copies"] = bool(
            len(accs) > 1 and all(a == accs[0] for a in accs))
        entry["differing_hlt_paths"] = sorted(
            p for p in (hlts[0] if hlts else {})
            if len({h[p] for h in hlts}) > 1) if len(hlts) > 1 else []
        report.append(entry)
        print(f"\nkey {k}: hlt_same={entry['hlt_identical_across_copies']} "
              f"objects_same={entry['selected_objects_identical_across_copies']} "
              f"acceptance_same={entry['acceptance_identical_across_copies']}")
        if entry["differing_hlt_paths"]:
            print(f"  HLT paths that differ between copies: {entry['differing_hlt_paths']}")
        for c in entry["copies"]:
            print(f"  {c['dataset']:11s} copies_in_file={c['n_copies_in_file']} "
                  f"n_selected={c.get('n_selected')} "
                  f"acc={c.get('acceptance_leading_only')}")

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps({
        "what": "why a handful of closure events get different flags in different "
                "datasets' copies of the same collision",
        "n_keys_inspected": len(report), "keys": report}, indent=2), encoding="utf-8")
    print(f"\nwrote {args.out}")


if __name__ == "__main__":
    main()
