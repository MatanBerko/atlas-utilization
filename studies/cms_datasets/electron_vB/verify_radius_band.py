#!/usr/bin/env python
"""
Step B, GATE 2 verification against the DATA (not against an argument).

For the events that `check_radius_change.py` could not settle from the
debug dumps alone -- those accepted at dR 0.05 but absent at dR 0.12, so
they have no row in the new dump -- this re-reads the ORIGINAL NanoAOD file
and computes, for every selected electron in the event, the dR to the
nearest selected muon. The event is EXPLAINED if at least one selected
electron falls in the band 0.05 <= dR < 0.12, i.e. the new radius removed
an electron the old radius kept.

Everything is computed with the production functions themselves
(`selection.select_*`, `drv.delta_r_wrapped`), never a copy.

It also optionally dumps, for MuonEG, every surviving selected e-mu pair
with m(e,mu) below a cut after the NEW radius has been applied -- the
detail GATE 1 asks for if it fails: each pair's dR, both pT values and both
object identities.

Usage (one array subjob per dataset+job):
    python verify_radius_band.py --dataset MuonEG --job job_3 \
        --keys-json evidence/B_events_to_verify.json \
        --out /storage/.../bandcheck/MuonEG_job_3.json \
        --pilot-files /storage/.../pilot_files.json [--dump-lowmass-pairs 5.0]
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

from services.parsing.validated_runs import ValidatedRunsFilter, apply_validated_runs_filter  # noqa: E402
from services.parsing.trigger_requirements import apply_trigger_requirement  # noqa: E402
from studies.cms_datasets.cluster import run_dataset_on_file as drv  # noqa: E402
from studies.m0m1j0_cms import selection  # noqa: E402

OLD_RADIUS = 0.05
NEW_RADIUS = 0.12


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--dataset", required=True, choices=drv.DELIVERY_VETO_ORDER_4)
    p.add_argument("--job", required=True, help="e.g. job_3")
    p.add_argument("--keys-json", required=True)
    p.add_argument("--pilot-files", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--dump-lowmass-pairs", type=float, default=None,
                   help="also dump surviving e-mu pairs below this mass (GeV)")
    p.add_argument("--validated-runs-json", default=drv.DEFAULT_VALIDATED_RUNS_JSON)
    args = p.parse_args()

    wanted = json.loads(Path(args.keys_json).read_text(encoding="utf-8"))
    keys = wanted.get("by_dataset_job", {}).get(f"{args.dataset}:{args.job}", [])
    key_set = {tuple(k) for k in keys}

    pilot = json.loads(Path(args.pilot_files).read_text(encoding="utf-8"))
    entry = next(e for e in pilot["files"]
                 if e["dataset"] == args.dataset and f"job_{e['job_index']}" == args.job)
    record_id, file_index = entry["record_id"], entry["file_index"]

    out = {"dataset": args.dataset, "job": args.job, "record_id": record_id,
           "file_index": file_index, "n_keys_requested": len(key_set),
           "old_radius": OLD_RADIUS, "new_radius": NEW_RADIUS,
           "git_commit": drv.git_commit_hash(REPO_ROOT)}

    if not key_set and args.dump_lowmass_pairs is None:
        out["note"] = "nothing to verify for this file"
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(out, indent=2), encoding="utf-8")
        print(f"[{args.dataset} {args.job}] nothing to do")
        return

    own_paths = drv.MATCHED4_TRIGGER_PATHS[args.dataset]
    needed_hlt = sorted({q for paths in drv.MATCHED4_TRIGGER_PATHS.values() for q in paths})
    required = list(drv.BASE_OBJECT_BRANCHES) + needed_hlt + list(drv.MATCHED_MODE_EXTRA_BRANCHES)
    url = drv.resolve_file_url(record_id, file_index)
    out["file_url"] = url
    print(f"[{args.dataset} {args.job}] {url}", flush=True)

    events = drv.read_events(url, required)
    validated = ValidatedRunsFilter(args.validated_runs_json)
    events, _ = apply_validated_runs_filter(events, validated)
    events, _ = apply_trigger_requirement(events, {"mode": "any", "paths": own_paths})

    muons = selection.select_muons(events)
    electrons = selection.select_electrons(events)

    # Per selected electron: dR to the NEAREST selected muon.
    dr = drv.delta_r_wrapped(electrons, muons)            # [event][ele][mu]
    nearest = ak.fill_none(ak.min(dr, axis=-1), np.inf)   # [event][ele]
    in_band = (nearest >= OLD_RADIUS) & (nearest < NEW_RADIUS)
    below_old = nearest < OLD_RADIUS
    n_in_band = ak.to_numpy(ak.sum(in_band, axis=1))
    n_below_old = ak.to_numpy(ak.sum(below_old, axis=1))

    run = ak.to_numpy(events.run)
    lumi = ak.to_numpy(events.luminosityBlock)
    evt = ak.to_numpy(events.event)

    checked = []
    n_explained = 0
    n_unexplained = 0
    if key_set:
        key_arr = np.array(sorted(key_set), dtype=np.int64)
        for i in range(len(run)):
            k = (int(run[i]), int(lumi[i]), int(evt[i]))
            if k not in key_set:
                continue
            explained = bool(n_in_band[i] >= 1)
            n_explained += int(explained)
            n_unexplained += int(not explained)
            checked.append({
                "key": list(k),
                "n_selected_electrons": int(ak.num(electrons, axis=1)[i]),
                "n_selected_muons": int(ak.num(muons, axis=1)[i]),
                "n_electrons_in_band_005_012": int(n_in_band[i]),
                "n_electrons_below_005": int(n_below_old[i]),
                "nearest_dr_per_electron": [round(float(x), 5)
                                            for x in ak.to_list(nearest[i])],
                "explained": explained,
            })
        out["n_keys_found_in_file"] = len(checked)
        out["n_explained"] = n_explained
        out["n_unexplained"] = n_unexplained
        out["checked"] = checked
        print(f"[{args.dataset} {args.job}] verified {len(checked)}/{len(key_set)} keys: "
              f"explained {n_explained}, unexplained {n_unexplained}", flush=True)

    # Optional GATE 1 detail: surviving low-mass e-mu pairs after the NEW radius.
    if args.dump_lowmass_pairs is not None:
        import vector
        vector.register_awkward()
        kept, _n, _m = drv.remove_electrons_overlapping_muons(
            electrons, muons, dr_max=NEW_RADIUS, enabled=True)
        e_p4 = vector.zip({"pt": kept.pt, "eta": kept.eta, "phi": kept.phi,
                           "mass": kept.mass})
        m_p4 = vector.zip({"pt": muons.pt, "eta": muons.eta, "phi": muons.phi,
                           "mass": muons.mass})
        pe, pm = ak.unzip(ak.cartesian([e_p4, m_p4]))
        mass = (pe + pm).mass
        pair_dr = pe.deltaR(pm)
        low = mass < args.dump_lowmass_pairs
        survivors = []
        idx_e, idx_m = ak.unzip(ak.cartesian([ak.local_index(kept, axis=1),
                                              ak.local_index(muons, axis=1)]))
        for i in range(len(run)):
            sel = ak.to_numpy(low[i]) if len(low[i]) else np.zeros(0, dtype=bool)
            if not sel.any():
                continue
            for j in np.flatnonzero(sel):
                survivors.append({
                    "key": [int(run[i]), int(lumi[i]), int(evt[i])],
                    "m_emu_gev": round(float(mass[i][j]), 4),
                    "dr": round(float(pair_dr[i][j]), 5),
                    "electron_pt": round(float(pe[i][j].pt), 3),
                    "electron_eta": round(float(pe[i][j].eta), 4),
                    "muon_pt": round(float(pm[i][j].pt), 3),
                    "muon_eta": round(float(pm[i][j].eta), 4),
                    "electron_index": int(idx_e[i][j]),
                    "muon_index": int(idx_m[i][j]),
                })
        out["lowmass_pair_cut_gev"] = args.dump_lowmass_pairs
        out["n_surviving_lowmass_pairs"] = len(survivors)
        out["surviving_lowmass_pairs"] = survivors[:200]
        print(f"[{args.dataset} {args.job}] surviving pairs below "
              f"{args.dump_lowmass_pairs} GeV at dR {NEW_RADIUS}: {len(survivors)}",
              flush=True)

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
