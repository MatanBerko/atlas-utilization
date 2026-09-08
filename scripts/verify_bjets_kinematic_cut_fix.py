#!/usr/bin/env python3
"""
Read-only verification for fix/cms-bjets-kinematic-cuts.

Loads REAL, already-parsed BJets_pt/BJets_eta from an on-disk parsed output
(produced BEFORE this fix, by config.cms_bjet_test.yaml's old kinematic_cuts
block, which had no `bjets:` entry) and runs the REAL production function,
services/parsing/event_selection.py::apply_parsing_event_selection, against
it -- once with the OLD kinematic_cuts (jets only) and once with the NEW
kinematic_cuts (jets + bjets, this fix's change) -- to prove concretely, on
real data through real code, that the fix changes BJets' behaviour exactly
as expected. No live XRootD access is used or needed.

Usage (inside the pipeline Docker image):
    python scripts/verify_bjets_kinematic_cut_fix.py \
        --parsed-root output/cms_bjet_test_20260903_124711/parsed_data/parsed_record_30562_final.root
"""
import argparse

import awkward as ak
import numpy as np
import uproot

from services.parsing.event_selection import apply_parsing_event_selection

OLD_KINEMATIC_CUTS = {
    # config.cms_bjet_test.yaml BEFORE this fix -- no "bjets" key at all.
    "electrons": {"pt_min": 25.0, "eta_max": 2.47},
    "muons": {"pt_min": 25.0, "eta_max": 2.5},
    "jets": {"pt_min": 30.0, "eta_max": 4.5},
    "photons": {"pt_min": 25.0, "eta_max": 2.37},
}

NEW_KINEMATIC_CUTS = {
    # config.cms_bjet_test.yaml AFTER this fix -- "bjets" added, same values as "jets".
    **OLD_KINEMATIC_CUTS,
    "bjets": {"pt_min": 30.0, "eta_max": 4.5},
}


def summarize(label: str, pt: ak.Array, eta: ak.Array) -> None:
    pt_flat = np.asarray(ak.flatten(pt, axis=None))
    eta_flat = np.asarray(ak.flatten(eta, axis=None))
    n = len(pt_flat)
    if n == 0:
        print(f"{label}: 0 BJets entries remain")
        return
    n_below_pt = int((pt_flat < 30.0).sum())
    n_above_eta = int((np.abs(eta_flat) > 4.5).sum())
    print(
        f"{label}: n={n:,}  min(pt)={pt_flat.min():.3f} GeV  "
        f"max(|eta|)={np.abs(eta_flat).max():.3f}  "
        f"violating pt_min=30: {n_below_pt:,}  violating eta_max=4.5: {n_above_eta:,}"
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--parsed-root", required=True)
    args = ap.parse_args()

    tree = uproot.open(args.parsed_root)["events"]
    bjets_pt = tree["BJets_pt"].array(library="ak")
    bjets_eta = tree["BJets_eta"].array(library="ak")

    print(f"Loaded {len(bjets_pt):,} events from {args.parsed_root}")
    print()
    print("=== RAW (as currently on disk, parsed by the pre-fix pipeline) ===")
    summarize("raw BJets on disk", bjets_pt, bjets_eta)
    print()

    # Build a real events-shaped awkward array with only a "BJets" field, in
    # exactly the record-array shape apply_parsing_event_selection expects
    # (events.fields -> per-collection record arrays with .pt/.eta).
    events = ak.zip({"BJets": ak.zip({"pt": bjets_pt, "eta": bjets_eta})}, depth_limit=1)

    print("=== BEFORE fix: apply_parsing_event_selection with OLD kinematic_cuts (no bjets key) ===")
    before = apply_parsing_event_selection(events, particle_counts=None, kinematic_cuts=OLD_KINEMATIC_CUTS)
    summarize("after OLD cuts", before.BJets.pt, before.BJets.eta)
    print()

    print("=== AFTER fix: apply_parsing_event_selection with NEW kinematic_cuts (bjets key added) ===")
    after = apply_parsing_event_selection(events, particle_counts=None, kinematic_cuts=NEW_KINEMATIC_CUTS)
    summarize("after NEW cuts", after.BJets.pt, after.BJets.eta)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
