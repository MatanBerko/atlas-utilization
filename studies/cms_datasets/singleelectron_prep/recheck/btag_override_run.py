#!/usr/bin/env python
"""
SingleElectron / b-tag re-check (19 Oct 2026), STUDY ONLY: run an EXISTING
per-file script with the DeepJet b-tag threshold overridden inside this
process, without editing any production file.

How the override works
----------------------
The only b-tag cut in the CMS path is

    studies/m0m1j0_cms/selection.py::select_and_split_jets
        is_bjet = raw_jets.btagDeepFlavB > BTAG_DEEPFLAVB_MEDIUM_WP

and BTAG_DEEPFLAVB_MEDIUM_WP is a module-level constant read when the
function RUNS (not bound as a default argument, and copied by no other
module -- `git grep BTAG_DEEPFLAVB_MEDIUM_WP` lists only selection.py). So
this wrapper imports `studies.m0m1j0_cms.selection`, assigns the constant,
and only then imports and runs the target script's main() in the same
process. Every later call sees the new value; selection.py on disk is
unchanged. With --btag-wp omitted nothing is overridden.

Targets
-------
--target driver  : studies/cms_datasets/cluster/run_dataset_on_file.py (data
                   or --is-mc). The wrapper also OBSERVES the driver's first
                   run_combination_funnel call (the "normal" version: every
                   accepted event, before the Version B rule) and, after the
                   driver finishes, writes per-event object counts to
                   --capture-out (.npz). The call is passed through unchanged,
                   with the same arguments, and its return value is returned
                   as is.
--target measure_se : studies/cms_datasets/singleelectron_prep/
                   measure_singleelectron.py (the 7 Oct Step B + D script).

--driver-repo puts another checkout first on sys.path (the MC driver lives
at the full run's pinned commit 294ee59, not on this branch).

Usage:
    python btag_override_run.py --target driver --btag-wp 0.25 \
        --capture-out cap.npz -- --dataset-label DoubleMuon --record-id 30522 ...
"""
from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import sys
from pathlib import Path

import numpy as np

TARGET_MODULES = {
    "driver": "studies.cms_datasets.cluster.run_dataset_on_file",
    "measure_se": "studies.cms_datasets.singleelectron_prep.measure_singleelectron",
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", required=True, choices=list(TARGET_MODULES))
    ap.add_argument("--btag-wp", type=float, default=None,
                    help="DeepJet threshold to set; omitted = no override")
    ap.add_argument("--driver-repo", default=None,
                    help="checkout to import the target and selection from")
    ap.add_argument("--capture-out", default=None,
                    help="driver only: write per-event counts of the normal version here (.npz)")
    ap.add_argument("rest", nargs=argparse.REMAINDER)
    args = ap.parse_args()
    rest = args.rest[1:] if args.rest[:1] == ["--"] else args.rest

    repo = Path(args.driver_repo).resolve() if args.driver_repo else Path(__file__).resolve().parents[4]
    sys.path.insert(0, str(repo))

    from studies.m0m1j0_cms import selection
    original = selection.BTAG_DEEPFLAVB_MEDIUM_WP
    if args.btag_wp is not None:
        selection.BTAG_DEEPFLAVB_MEDIUM_WP = args.btag_wp
    print(f"[btag_override_run] selection from {selection.__file__}; "
          f"BTAG_DEEPFLAVB_MEDIUM_WP {original} -> {selection.BTAG_DEEPFLAVB_MEDIUM_WP}", flush=True)

    mod = importlib.import_module(TARGET_MODULES[args.target])
    captured = {}
    if args.target == "driver" and args.capture_out:
        original_funnel = mod.run_combination_funnel

        def observed_funnel(obj_record, is_exclusive_selected, *a, **kw):
            if "obj_record" not in captured:            # first call = the normal version
                captured["obj_record"] = obj_record
                captured["is_exclusive"] = np.asarray(is_exclusive_selected, dtype=bool)
                sib = kw.get("mc_siblings")
                if sib is not None:
                    captured["genweight"] = np.asarray(sib[mod.MC_SIBLING_GENWEIGHT], dtype=np.float64)
            return original_funnel(obj_record, is_exclusive_selected, *a, **kw)

        mod.run_combination_funnel = observed_funnel

    sys.argv = [mod.__file__] + rest
    mod.main()

    # the threshold must still be the one we set when the target finished
    assert selection.BTAG_DEEPFLAVB_MEDIUM_WP == (args.btag_wp if args.btag_wp is not None else original)

    if args.target == "driver" and args.capture_out:
        import awkward as ak
        if "obj_record" not in captured:
            raise SystemExit("the driver never called run_combination_funnel -- nothing captured")
        rec = captured["obj_record"]
        counts = {k: ak.to_numpy(ak.num(rec[f])).astype(np.uint16)
                  for k, f in (("n_e", "Electrons"), ("n_m", "Muons"), ("n_j", "Jets"), ("n_b", "BJets"))}
        arrays = {**counts, "is_exclusive": captured["is_exclusive"]}
        if "genweight" in captured:
            arrays["genweight"] = captured["genweight"]
        # event identity, in the same row order, from the driver's own debug dump
        outdir = Path(rest[rest.index("--output-dir") + 1])
        dump = outdir / "debug_events.csv"
        ids_sha = None
        if dump.exists():
            rows = np.loadtxt(dump, delimiter=",", skiprows=1, usecols=(0, 1, 2), dtype=np.int64, ndmin=2)
            if len(rows) != len(counts["n_b"]):
                raise SystemExit(f"debug dump has {len(rows)} rows, captured {len(counts['n_b'])}")
            ids_sha = hashlib.sha256(np.ascontiguousarray(rows).tobytes()).hexdigest()
        np.savez_compressed(args.capture_out, **arrays)
        meta = {"btag_wp": float(selection.BTAG_DEEPFLAVB_MEDIUM_WP), "btag_wp_default": float(original),
                "n_events": int(len(counts["n_b"])), "event_ids_sha256": ids_sha,
                "selection_file": selection.__file__}
        Path(str(args.capture_out) + ".json").write_text(json.dumps(meta, indent=1))
        print(f"[btag_override_run] captured {meta['n_events']} events -> {args.capture_out}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
