#!/usr/bin/env python
"""
SingleElectron Step 1, Step C(2): is HLT_Ele27_WPTight_Gsf prescaled in
Run2016G+H?

The test uses events selected by a MUON trigger, so it is independent of
the electron path being tested. In SingleMuon data, golden lumis, with
HLT_IsoMu24 fired, it finds events that contain a trigger object which met
the Ele27 electron requirements (id == 11, filterBits & 2, TrigObj_pt >= 27)
and then asks, per run, how often HLT_Ele27_WPTight_Gsf nevertheless reads
0. For an unprescaled, enabled path that fraction should be about zero. A
run or block of runs with a clearly non-zero fraction points to a prescale
or to the path being disabled there.

The same numbers answer a second question the brief raises: bit 2's CMSSW
filter pattern `hltEle*WPTight*TrackIsoFilter*` is wildcarded, so several
WPTight paths can set it. If "object qualifies but Ele27 did not fire" is
rare, then "bit 2 and TrigObj_pt >= 27" is in practice equivalent to
"passed Ele27". The other WPTight paths present in the files are read ONLY
to report which of them fired in those events; none is used in any
acceptance.

Usage:
    python prescale_check.py --era G --file-index 0 --out out.json
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

from services.parsing.validated_runs import ValidatedRunsFilter, apply_validated_runs_filter  # noqa: E402
from services.parsing.trigger_requirements import apply_trigger_requirement  # noqa: E402
from studies.cms_datasets.cluster import run_dataset_on_file as drv  # noqa: E402
from studies.cms_datasets.electron_prep.common import record_for  # noqa: E402
from studies.cms_datasets.singleelectron_prep.measure_singleelectron import (  # noqa: E402
    ELE27, ONLINE_PT_MIN, OTHER_WPTIGHT_PATHS, TRIGOBJ_BIT_WPTIGHT,
    assert_bit_meanings,
)

ISOMU24 = "HLT_IsoMu24"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--era", required=True, choices=["G", "H"])
    p.add_argument("--file-index", type=int, required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--validated-runs-json", default=drv.DEFAULT_VALIDATED_RUNS_JSON)
    args = p.parse_args()

    t0 = time.time()
    record_id = record_for("SingleMuon", args.era)
    required = (["run", "luminosityBlock", "event", ISOMU24, ELE27]
                + list(drv.MATCHED_MODE_EXTRA_BRANCHES) + list(OTHER_WPTIGHT_PATHS))
    url = drv.resolve_file_url(record_id, args.file_index)
    print(f"[SingleMuon {args.era} {args.file_index}] {url}", flush=True)

    events, titles = drv.read_events(url, sorted(set(required)), return_titles=True)
    n_read = len(events)
    bit_check = assert_bit_meanings(titles)

    validated = ValidatedRunsFilter(args.validated_runs_json)
    events, _ = apply_validated_runs_filter(events, validated)
    n_golden = len(events)

    events, _ = apply_trigger_requirement(events, {"mode": "any", "paths": [ISOMU24]})
    n_tag = len(events)
    print(f"  golden {n_golden} -> IsoMu24 {n_tag}", flush=True)

    out = {
        "what": "Step C(2): prescale / path-enabled test for HLT_Ele27_WPTight_Gsf, "
                "using muon-triggered events so the test is independent of the "
                "electron path",
        "dataset": "SingleMuon", "era": args.era, "record_id": record_id,
        "file_index": args.file_index, "file_url": url,
        "git_commit": drv.git_commit_hash(REPO_ROOT),
        "n_read": n_read, "n_after_golden_json": n_golden, "n_after_isomu24": n_tag,
        "trigobj_title_check": bit_check,
        "ele27_branch_present_in_this_singlemuon_file": True,
    }

    if n_tag == 0:
        out["note"] = "no events after the IsoMu24 requirement"
        out["per_run"] = {}
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(out, indent=2), encoding="utf-8")
        return

    trigobj = ak.zip({
        "pt": events.TrigObj_pt, "eta": events.TrigObj_eta, "phi": events.TrigObj_phi,
        "id": events.TrigObj_id, "filterBits": events.TrigObj_filterBits})
    qualifying = ((trigobj.id == drv.TRIGOBJ_ELECTRON_ID)
                  & ((trigobj.filterBits & TRIGOBJ_BIT_WPTIGHT) != 0)
                  & (trigobj.pt >= ONLINE_PT_MIN))
    has_qual = ak.to_numpy(ak.any(qualifying, axis=1))
    fired = ak.to_numpy(events[ELE27]).astype(bool)
    runs = ak.to_numpy(events.run).astype(np.int64)

    other = {}
    other_any = np.zeros(n_tag, dtype=bool)
    for path in OTHER_WPTIGHT_PATHS:
        f = ak.to_numpy(events[path]).astype(bool)
        other[path] = int((has_qual & ~fired & f).sum())
        other_any |= f

    per_run = {}
    for r in np.unique(runs[has_qual]) if has_qual.any() else []:
        sel = has_qual & (runs == r)
        n = int(sel.sum())
        n_not = int((sel & ~fired).sum())
        per_run[str(int(r))] = {
            "n_events_with_qualifying_object": n,
            "n_of_those_with_ele27_not_fired": n_not,
            "fraction_not_fired": (n_not / n) if n else None,
        }

    out.update({
        "n_events_with_qualifying_object": int(has_qual.sum()),
        "n_qualifying_but_ele27_not_fired": int((has_qual & ~fired).sum()),
        "fraction_qualifying_but_not_fired": (
            float((has_qual & ~fired).sum() / has_qual.sum()) if has_qual.any() else None),
        "n_qualifying_not_fired_but_other_wptight_fired": int(
            (has_qual & ~fired & other_any).sum()),
        "which_other_wptight_fired_when_ele27_did_not": other,
        "per_run": per_run,
        "elapsed_sec": round(time.time() - t0, 1),
    })
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"  qualifying {out['n_events_with_qualifying_object']}, "
          f"of which Ele27 not fired {out['n_qualifying_but_ele27_not_fired']}", flush=True)
    print(f"  wrote {args.out}", flush=True)


if __name__ == "__main__":
    main()
