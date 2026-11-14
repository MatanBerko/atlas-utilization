#!/usr/bin/env python
"""Write one short README per per-sample MC file of the final delivery (14 Nov 2026), as the 25 Oct delivery had.

Inputs: registry v5 and the v7 decisions (via make_readme.py's helpers), evidence/final_build/checks_final.json
(sigma, Sigma_w, normalisation, files, histograms, yield), build_report_summary.json (process groups),
per_sample_sumcheck_20261114.json (histograms per file) and the portal file counts in mappings/inputs_*.json.
The 13 samples reused from 25 Oct were run on every file of their complete file index (HANDOFF.md:102,311).

    python studies/mc_expansion_20261103/delivery/make_per_sample_readmes.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import make_readme as mr  # noqa: E402

OUT = HERE / "per_sample"
DELIVERED_25OCT = {"35631", "35669", "37728", "64839", "64895", "67801", "67993", "68073", "68187", "68847",
                   "72676", "72752", "75589"}


def portal_files() -> dict:
    out = {}
    for f in ("inputs_20261103.json", "inputs_D15_20261107.json"):
        for rid, r in json.loads((HERE.parent / "mappings" / f).read_text())["records"].items():
            out[rid] = r["portal_number_files"]
    return out


def main():
    chk = json.loads((mr.EV / "checks_final.json").read_text())
    bsum = json.loads((mr.EV / "build_report_summary.json").read_text())
    psum = json.loads((mr.EV / "per_sample_sumcheck_20261114.json").read_text())
    groups = {str(m): g for g, ms in bsum["groups"].items() for m in ms}
    portal = portal_files()
    OUT.mkdir(exist_ok=True)
    written = []
    for s in sorted(chk["samples"], key=lambda s: int(s["record"])):
        rid = s["record"]
        r = mr.REG["records"][rid]
        c, o, src = mr.construction(r)
        fname = f"CMS_Run2016GH_MC-{s['physics_short']}-rec{rid}_16p393invfb_build2026-11-14_mc.root"
        if rid in DELIVERED_25OCT:
            pub = (f"{s['n_files_included'] + s['n_files_excluded']} (every file of the record's complete file index; "
                   "reused unchanged from the 25 Oct production)")
        else:
            pub = str(portal[rid])
            if portal[rid] != s["n_files_included"] + s["n_files_excluded"]:
                pub += (f" listed by the portal, only {s['n_files_included'] + s['n_files_excluded']} published "
                        "(the rest cannot be processed)")
        excl = (f"; {s['n_files_excluded']} excluded by the per-file Sigma_w check" if s["n_files_excluded"] else "")
        txt = f"""{fname}
{'=' * len(fname)}

CMS 2016 SIMULATION (MC), ONE sample: {s['physics_short']} (CMS Open Data record {rid}),
normalised to 16.393 fb^-1 (Run2016G+H), RunIISummer20UL16 NanoAODv9 (postVFP).
Part of the final MC delivery of 14 Nov 2026; the summed file
{mr.FNAME}
is the sum of this file and the other {len(chk['samples']) - 1} per-sample files.

SAMPLE
  Record:          {rid} (NanoAOD; MiniAOD record {r['mini_recid']})
  Dataset:         {r['portal_dataset_title']}
  Process group:   {groups.get(rid, '')}
  sigma_eff:       {r['cross_section_pb']:g} pb (k_factor = gen_filt_eff = 1; all factors inside)
  Order:           {o}
  Construction:    {c}
  Source:          {src}
  Status:          {mr.status(rid, r)}

NORMALISATION
  Sigma_w (sum of genWeight, files used): {s['sigma_w']:.6g}
  Normalisation factor sigma_eff x 1000 x 16.393 / Sigma_w: {s['normalisation_build']:.6g}
  Each event: genWeight x L1PreFiringWeight_Nom x normalisation factor.
  Files used: {s['n_files_included']}{excl}; files in the record: {pub}.
  Fraction of stored events with a negative generator weight: {s['negative_weight_fraction_stored']:.3f}

CONTENTS
  {psum['n_histograms_per_file'][rid]} histograms (TH1D with Sumw2), weighted events; only the histograms
  this sample fills. Share of the summed MC yield: {100 * s['share_of_total']:.3g} %.
  Start masses: each histogram is cut at the SAME peak and split masses as the
  summed file (found once on the sum of all samples), so this file is a slice
  of the summed histogram; its own first filled bin can lie later where this
  sample is empty. Compare with data only from the common start given in
  {mr.FNAME}.start_masses.csv.

SEE THE MAIN README
  {mr.FNAME}.README.txt
  for the object selection, triggers, final states, post-processing, start
  masses (how to compare with data), single-event dominance, and the MISSING
  list (QCD multijet and photon processes are NOT in the MC).
"""
        (OUT / f"{fname}.README.txt").write_text(txt)
        written.append(fname)
    print(f"wrote {len(written)} READMEs into {OUT}")


if __name__ == "__main__":
    main()
