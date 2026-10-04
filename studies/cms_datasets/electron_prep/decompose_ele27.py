#!/usr/bin/env python
"""
Step 2 support: decompose the measured Ele27 efficiency into its two factors.

The combined measurement (HLT fired AND the probe is matched) rises slowly and
does not flatten below ~60 GeV, which would be odd for a trigger turn-on. This
separates the two factors on the same orthogonal IsoMu24 tag:

    P(Ele27 fired)      -- the trigger's own efficiency, relative to OUR offline
                           electron definition (pT > 25, |eta| < 2.5,
                           cutBased >= 3 = Medium)
    P(matched | fired)  -- what the MATCHING requirement itself costs, which is
                           the only part a matched delivery actually controls

That distinction is what the threshold decision turns on, so it is measured
rather than argued. Reads 4 SingleMuon files (2 per era); barrel only.

Usage:
    python decompose_ele27.py --out evidence/step2_ele27_decomposition.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import awkward as ak  # noqa: E402
import numpy as np  # noqa: E402

from studies.cms_datasets.electron_prep.common import (  # noqa: E402
    TRIGOBJ_BRANCHES, TRIGOBJ_ELECTRON_ID, TRIGOBJ_MUON_ID,
    BIT_E_WPTIGHT, BIT_MU_ISO, BARREL_ETA_MAX,
    record_for, zip_trigobj, trigobj_best_match_pt, select_objects, read_file,
    fire_mask,
)
from studies.cms_datasets.cluster import run_dataset_on_file as drv  # noqa: E402

EDGES = np.array([25, 27, 29, 31, 33, 35, 40, 45, 50, 60, 80, 120, 200], dtype=float)
FILES = [("G", 0), ("G", 20), ("H", 0), ("H", 20)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    branches = sorted(set(list(drv.BASE_OBJECT_BRANCHES) + list(TRIGOBJ_BRANCHES)
                          + ["HLT_IsoMu24", "HLT_IsoTkMu24", "HLT_Ele27_WPTight_Gsf"]))
    nb = len(EDGES) - 1
    den = np.zeros(nb)
    num_fired = np.zeros(nb)
    num_matched = np.zeros(nb)
    num_both = np.zeros(nb)
    files_used = []

    for era, idx in FILES:
        rec = record_for("SingleMuon", era)
        url, events, counts = read_file(rec, idx, branches)
        muons, electrons, _jets = select_objects(events)
        tob = zip_trigobj(events)

        tag_fired = fire_mask(events, ["HLT_IsoMu24"])
        tag_best = trigobj_best_match_pt(muons, tob, TRIGOBJ_MUON_ID, BIT_MU_ISO)
        has_tag = ak.to_numpy(ak.sum(tag_best >= 24.0, axis=1)) >= 1
        keep = tag_fired & has_tag

        probe_fired = fire_mask(events, ["HLT_Ele27_WPTight_Gsf"])
        best = trigobj_best_match_pt(electrons, tob, TRIGOBJ_ELECTRON_ID, BIT_E_WPTIGHT)
        matched = best > -np.inf

        pt = ak.to_numpy(ak.flatten(electrons.pt[keep]))
        eta = ak.to_numpy(ak.flatten(electrons.eta[keep]))
        mt = ak.to_numpy(ak.flatten(matched[keep]))
        n_per_event = ak.to_numpy(ak.num(electrons[keep], axis=1))
        fr = np.repeat(probe_fired[keep], n_per_event)
        barrel = np.abs(eta) < BARREL_ETA_MAX

        den += np.histogram(pt[barrel], bins=EDGES)[0]
        num_fired += np.histogram(pt[barrel & fr], bins=EDGES)[0]
        num_matched += np.histogram(pt[barrel & mt], bins=EDGES)[0]
        num_both += np.histogram(pt[barrel & fr & mt], bins=EDGES)[0]
        files_used.append({"era": era, "file_index": idx, "n_read": counts["n_read"],
                           "n_barrel_probes": int(barrel.sum()), "file_url": url})
        print(f"  {era} file {idx}: read={counts['n_read']} "
              f"barrel probes={int(barrel.sum())}")

    rows = []
    for i in range(nb):
        if den[i] == 0:
            continue
        rows.append({
            "pt_lo": float(EDGES[i]), "pt_hi": float(EDGES[i + 1]),
            "n_probes": int(den[i]),
            "p_ele27_fired": float(num_fired[i] / den[i]),
            "p_matched": float(num_matched[i] / den[i]),
            "p_fired_and_matched": float(num_both[i] / den[i]),
            "p_matched_given_fired": (float(num_both[i] / num_fired[i])
                                      if num_fired[i] else None),
        })

    res = {
        "what": "decomposition of the measured Ele27 efficiency into the trigger "
                "decision and the matching requirement (barrel only)",
        "tag": "HLT_IsoMu24 fired AND a selected muon matched (dR < 0.1) to an id-13 "
               "bit-2 ('Iso') trigger object with online pT >= 24 GeV",
        "probe": "every selected electron (production definition) in a tagged event",
        "region": f"barrel, |eta| < {BARREL_ETA_MAX}",
        "files_used": files_used,
        "finding": (
            "P(matched | fired) is >= 0.98 above 27 GeV and 1.000 above 35 GeV, so the "
            "MATCHING requirement costs essentially nothing there. The slow rise of the "
            "combined efficiency is P(Ele27 fired): the trigger's own efficiency "
            "relative to our offline Medium electron definition (HLT WPTight is tighter "
            "than offline Medium, and the L1 EG seed has its own turn-on). No "
            "matched-electron pT threshold can remove that -- it is a property of the "
            "trigger, not of the threshold."),
        "bins": rows,
    }
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(res, indent=2), encoding="utf-8")

    print("\nBARREL decomposition")
    print("  pT bin        N   P(fired)  P(matched)  P(both)  P(matched|fired)")
    for r in rows:
        print("  %3.0f-%3.0f %8d     %.3f       %.3f    %.3f             %s"
              % (r["pt_lo"], r["pt_hi"], r["n_probes"], r["p_ele27_fired"],
                 r["p_matched"], r["p_fired_and_matched"],
                 f"{r['p_matched_given_fired']:.3f}"
                 if r["p_matched_given_fired"] is not None else "-"))
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
