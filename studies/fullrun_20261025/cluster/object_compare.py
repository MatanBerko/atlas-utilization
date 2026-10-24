#!/usr/bin/env python
"""Full run 25 Oct 2026, step 3: OLD vs NEW lepton selection on one real file.

OLD = studies/m0m1j0_cms/selection.py of the lean branch (Muon_mediumId,
Electron cutBased >= 3); NEW = this checkout's (Muon_looseId, cutBased >= 2).
Both are the real select_muons / select_electrons functions; the OLD module is
loaded from --old-selection (a copy of the OLD file).

Per file, two populations: "certified" (data: golden JSON; MC: every event)
and "triggered" (data: the dataset's own trigger paths, as the driver does;
MC: any trigger path of the five delivered datasets). For each:
  - selected muons / electrons, OLD and NEW (totals; per-event multiplicity);
  - containment: every OLD-selected object must also be NEW-selected (the
    object identity is its index in the file's own collection); exceptions
    are counted and the first ones listed;
  - what the extra NEW objects are (loose-not-medium muons; cutBased == 2);
  - the driver's e-mu overlap removal (dR < 0.12) applied to OLD and NEW
    objects: electrons removed and events with an electron removed;
  - electron pT and |eta| histograms of the selected electrons, OLD and NEW.

Reads the file in chunks; ROOT reading, so run it inside a PBS job.

    python object_compare.py --label DoubleEG --record 30521 --file-index 0 \
        --old-selection /path/old_selection.py --out objects.json [--is-mc]
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

import awkward as ak  # noqa: E402
import numpy as np  # noqa: E402
import uproot  # noqa: E402

from services.parsing.validated_runs import (  # noqa: E402
    ValidatedRunsFilter, apply_validated_runs_filter)
from studies.cms_datasets.cluster import run_dataset_on_file as drv  # noqa: E402
from studies.m0m1j0_cms import selection as new_sel  # noqa: E402

MULT_MAX = 6  # per-event multiplicity histogram: 0..5 and ">= 6"
PT_EDGES = np.concatenate([np.arange(25.0, 200.0 + 1e-9, 5.0), [np.inf]])
ABSETA_EDGES = np.round(np.arange(0.0, 2.5 + 1e-9, 0.05), 2)
N_EXAMPLES = 20


def load_old_selection(path: str):
    spec = importlib.util.spec_from_file_location("old_selection", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _new_counter():
    return {
        "n_events": 0,
        "muons": {"old": 0, "new": 0, "old_not_new": 0, "new_not_old": 0,
                  "new_not_old_loose_not_medium": 0,
                  "mult_old": [0] * (MULT_MAX + 1), "mult_new": [0] * (MULT_MAX + 1)},
        "electrons": {"old": 0, "new": 0, "old_not_new": 0, "new_not_old": 0,
                      "new_not_old_by_cutbased": {str(c): 0 for c in range(5)},
                      "mult_old": [0] * (MULT_MAX + 1), "mult_new": [0] * (MULT_MAX + 1),
                      "pt_old": [0] * (len(PT_EDGES) - 1), "pt_new": [0] * (len(PT_EDGES) - 1),
                      "abseta_old": [0] * (len(ABSETA_EDGES) - 1),
                      "abseta_new": [0] * (len(ABSETA_EDGES) - 1)},
        "overlap_removal": {"old": {"electrons_removed": 0, "events_with_removal": 0},
                            "new": {"electrons_removed": 0, "events_with_removal": 0}},
        "events_with_any_change": {"muon_multiplicity": 0, "electron_multiplicity": 0},
        "old_not_new_examples": [],
    }


def _add(lst, values):
    for i, v in enumerate(values):
        lst[i] += int(v)


def _global_ids(sel_idx, n_raw):
    """Per-object index -> a file-chunk-wide id (event offset + local index)."""
    starts = np.concatenate([[0], np.cumsum(ak.to_numpy(n_raw))[:-1]])
    counts = ak.to_numpy(ak.num(sel_idx, axis=1))
    return ak.to_numpy(ak.flatten(sel_idx)).astype(np.int64) + np.repeat(starts, counts)


def accumulate(c, ev, old_sel):
    n = len(ev)
    c["n_events"] += n
    if n == 0:
        return
    n_mu_raw = ak.num(ev.Muon_pt, axis=1)
    n_el_raw = ak.num(ev.Electron_pt, axis=1)
    mu_idx = ak.local_index(ev.Muon_pt)
    # select_electrons has no extra_fields: carry the electron's index through
    # the (uncut) mass field of a copy, so both REAL functions are used as-is.
    ev_e = ak.with_field(ev, ak.values_astype(ak.local_index(ev.Electron_pt), np.float64),
                         "Electron_mass")

    mu_old = old_sel.select_muons(ev, extra_fields={"idx": mu_idx})
    mu_new = new_sel.select_muons(ev, extra_fields={"idx": mu_idx})
    el_old_i = old_sel.select_electrons(ev_e)
    el_new_i = new_sel.select_electrons(ev_e)

    for kind, o, nw, nraw in (("muons", mu_old.idx, mu_new.idx, n_mu_raw),
                              ("electrons", ak.values_astype(el_old_i.mass, np.int64),
                               ak.values_astype(el_new_i.mass, np.int64), n_el_raw)):
        g_old, g_new = _global_ids(o, nraw), _global_ids(nw, nraw)
        old_in_new = np.isin(g_old, g_new)
        new_in_old = np.isin(g_new, g_old)
        k = c[kind]
        k["old"] += len(g_old)
        k["new"] += len(g_new)
        k["old_not_new"] += int((~old_in_new).sum())
        k["new_not_old"] += int((~new_in_old).sum())
        m_old = np.minimum(ak.to_numpy(ak.num(o, axis=1)), MULT_MAX)
        m_new = np.minimum(ak.to_numpy(ak.num(nw, axis=1)), MULT_MAX)
        _add(k["mult_old"], np.bincount(m_old, minlength=MULT_MAX + 1))
        _add(k["mult_new"], np.bincount(m_new, minlength=MULT_MAX + 1))
        c["events_with_any_change"][kind[:-1] + "_multiplicity"] += int((m_old != m_new).sum())
        if (~old_in_new).any() and len(c["old_not_new_examples"]) < N_EXAMPLES:
            ev_of = np.repeat(np.arange(n), ak.to_numpy(ak.num(o, axis=1)))
            for j in np.nonzero(~old_in_new)[0][:N_EXAMPLES]:
                e = int(ev_of[j])
                c["old_not_new_examples"].append({
                    "kind": kind, "run": int(ev.run[e]), "luminosityBlock": int(ev.luminosityBlock[e]),
                    "event": int(ev.event[e])})
        if kind == "muons":
            extra = ~new_in_old
            med_flat = ak.to_numpy(ak.flatten(ev.Muon_mediumId[nw]))
            k["new_not_old_loose_not_medium"] += int((extra & ~med_flat).sum())
        else:
            cb_new = ak.to_numpy(ak.flatten(ev.Electron_cutBased[nw]))
            for cbv in range(5):
                k["new_not_old_by_cutbased"][str(cbv)] += int(((~new_in_old) & (cb_new == cbv)).sum())

    # The real electron collections (true masses) for pT / |eta| and overlap removal.
    el_old = old_sel.select_electrons(ev)
    el_new = new_sel.select_electrons(ev)
    k = c["electrons"]
    for side, el in (("old", el_old), ("new", el_new)):
        pt = ak.to_numpy(ak.flatten(el.pt))
        ae = np.abs(ak.to_numpy(ak.flatten(el.eta)))
        _add(k["pt_" + side], np.histogram(pt, PT_EDGES)[0])
        _add(k["abseta_" + side], np.histogram(ae, ABSETA_EDGES)[0])
    for side, el, mu in (("old", el_old, mu_old), ("new", el_new, mu_new)):
        _kept, n_removed, _mask = drv.remove_electrons_overlapping_muons(
            el, mu, dr_max=drv.EMU_OVERLAP_DR_MAX, enabled=True)
        nr = ak.to_numpy(n_removed)
        c["overlap_removal"][side]["electrons_removed"] += int(nr.sum())
        c["overlap_removal"][side]["events_with_removal"] += int((nr > 0).sum())


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--label", required=True)
    p.add_argument("--record", type=int, required=True)
    p.add_argument("--file-index", type=int, required=True)
    p.add_argument("--old-selection", required=True)
    p.add_argument("--is-mc", action="store_true")
    p.add_argument("--out", required=True)
    args = p.parse_args()

    old_sel = load_old_selection(args.old_selection)
    consts = {side: {"muon_id": getattr(m, "MUON_ID_BRANCH", "Muon_mediumId"),
                     "muon_iso_max": m.MUON_ISO_MAX,
                     "electron_cutbased_min": m.ELECTRON_CUTBASED_MIN}
              for side, m in (("old", old_sel), ("new", new_sel))}
    print(json.dumps(consts), flush=True)
    assert consts["old"] == {"muon_id": "Muon_mediumId", "muon_iso_max": 0.15,
                             "electron_cutbased_min": 3}, consts
    assert consts["new"] == {"muon_id": "Muon_looseId", "muon_iso_max": 0.15,
                             "electron_cutbased_min": 2}, consts

    if args.is_mc:
        trig = sorted({t for paths in drv.MATCHED5_TRIGGER_PATHS.values() for t in paths})
    else:
        trig = list(drv.TRIGGER_PATHS_BY_DATASET[args.label])
    branches = ["run", "luminosityBlock", "event",
                "Muon_pt", "Muon_eta", "Muon_phi", "Muon_mass",
                "Muon_looseId", "Muon_mediumId", "Muon_pfRelIso04_all",
                "Electron_pt", "Electron_eta", "Electron_phi", "Electron_mass",
                "Electron_cutBased", *trig]
    url = drv.resolve_file_url(args.record, args.file_index)
    tree = uproot.open(url)["Events"]
    validated = None if args.is_mc else ValidatedRunsFilter(
        str(REPO_ROOT / drv.DEFAULT_VALIDATED_RUNS_JSON))
    pops = {"certified": _new_counter(), "triggered": _new_counter()}
    n_read = 0
    for start in range(0, tree.num_entries, drv.READ_CHUNK_SIZE):
        stop = min(start + drv.READ_CHUNK_SIZE, tree.num_entries)
        ev = drv._read_chunk_with_retry(tree, branches, start, stop, url)
        n_read += len(ev)
        if validated is not None:
            ev, _stats = apply_validated_runs_filter(ev, validated)
        accumulate(pops["certified"], ev, old_sel)
        fired = np.zeros(len(ev), dtype=bool)
        for t in trig:
            fired |= ak.to_numpy(ev[t]).astype(bool)
        accumulate(pops["triggered"], ev[fired], old_sel)
        print(f"chunk {start}-{stop}: {len(ev)} certified, {int(fired.sum())} triggered", flush=True)

    out = {"label": args.label, "record_id": args.record, "file_index": args.file_index,
           "is_mc": args.is_mc, "url": url, "n_read": n_read, "trigger_paths": trig,
           "selection_constants": consts,
           "pt_edges_gev": [float(x) for x in PT_EDGES[:-1]] + ["inf"],
           "abseta_edges": ABSETA_EDGES.tolist(), "mult_max_bin_is_ge": MULT_MAX,
           "populations": pops}
    Path(args.out).write_text(json.dumps(out, indent=1), encoding="utf-8")
    for name, c in pops.items():
        print(name, c["n_events"], "muons", c["muons"]["old"], "->", c["muons"]["new"],
              "electrons", c["electrons"]["old"], "->", c["electrons"]["new"],
              "old_not_new", c["muons"]["old_not_new"], c["electrons"]["old_not_new"], flush=True)


if __name__ == "__main__":
    main()
