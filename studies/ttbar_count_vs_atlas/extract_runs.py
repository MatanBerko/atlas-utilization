#!/usr/bin/env python
"""Extract settings + log-reported histogram counts from the copied ATLAS run logs.

Reads ONLY our own copies under atlas_input/other_runs/. Nothing in
/storage/agrp/marybo/ is touched.
"""
import json
import os
import re
import sys

import yaml

BASE = "/storage/agrp/berkom/atlas-utilization/work/ttbar_count_vs_atlas/atlas_input/other_runs"
OUT_JSON = "/storage/agrp/berkom/atlas-utilization/work/ttbar_count_vs_atlas/atlas_input/atlas_runs_survey.json"


def g(d, *path, default=None):
    cur = d
    for k in path:
        if not isinstance(cur, dict) or k not in cur:
            return default
        cur = cur[k]
    return cur


def pcount(cfg, obj):
    v = g(cfg, "parsing_task_config", "particle_counts", obj)
    if v is None:
        return None
    return v.get("max")


rows = []
for run in sorted(os.listdir(BASE)):
    rd = os.path.join(BASE, run)
    if not os.path.isdir(rd):
        continue
    files = os.listdir(rd)

    # --- config ---
    cfgf = [f for f in files if f.endswith(".yaml")]
    cfg = {}
    cfg_name = None
    if cfgf:
        cfg_name = sorted(cfgf)[0]
        try:
            with open(os.path.join(rd, cfg_name)) as fh:
                cfg = yaml.safe_load(fh) or {}
        except Exception as exc:          # malformed yaml: record and move on
            cfg = {}
            cfg_name = "%s (UNPARSEABLE: %s)" % (cfg_name, exc)

    # --- pipeline.out: total histograms, as REPORTED BY HER LOG ---
    hist_merged = hist_written = sigs = None
    pof = os.path.join(rd, "logs_pipeline.out")
    if os.path.exists(pof):
        txt = open(pof, errors="replace").read()
        m = re.search(r"tail display ranges to (\d+) merged histogram", txt)
        if m:
            hist_merged = int(m.group(1))
        m = re.search(r"Grouped (\d+) signatures into (\d+) unique histogram", txt)
        if m:
            sigs, hist_written = int(m.group(1)), int(m.group(2))

    # --- submit script: NUM_JOBS ---
    njobs = None
    for f in files:
        if f.startswith("logs_submit"):
            t = open(os.path.join(rd, f), errors="replace").read()
            m = re.search(r"^NUM_JOBS=(\d+)", t, re.M)
            if m:
                njobs = int(m.group(1))

    m = re.search(r"(\d{8})_(\d{6})$", run)
    date = "%s-%s-%s %s:%s" % (m.group(1)[:4], m.group(1)[4:6], m.group(1)[6:],
                               m.group(2)[:2], m.group(2)[2:4]) if m else ""

    rows.append(dict(
        run=run,
        date=date,
        config_file=cfg_name,
        trigger=g(cfg, "trigger_config", "enabled"),
        # her code default is False when the key is absent (domain/config.py:316)
        overlap_removal=g(cfg, "parsing_task_config", "enable_overlap_removal", default=False)
        if cfg else None,
        overlap_key_present=("enable_overlap_removal" in (cfg.get("parsing_task_config") or {}))
        if cfg else None,
        max_e=pcount(cfg, "electrons"), max_m=pcount(cfg, "muons"),
        max_j=pcount(cfg, "jets"), max_b=pcount(cfg, "bjets"),
        max_g=pcount(cfg, "photons"), max_t=pcount(cfg, "taus"),
        max_types=g(cfg, "mass_calculation_task_config", "max_particles_in_combination"),
        max_per_type=g(cfg, "mass_calculation_task_config", "max_count_particle_in_combination"),
        max_total_in_comb=g(cfg, "mass_calculation_task_config", "max_total_particles_in_combination"),
        min_events_per_fs=g(cfg, "mass_calculation_task_config", "min_events_per_fs"),
        z_peak_cutoff=g(cfg, "post_processing_task_config", "z_peak_cutoff"),
        bin_width_gev=g(cfg, "histogram_creation_task_config", "bin_width_gev"),
        max_files=g(cfg, "parsing_task_config", "max_files_to_process"),
        parse_mc=g(cfg, "parsing_task_config", "parse_mc"),
        num_jobs=njobs,
        hist_total_merged=hist_merged,
        hist_total_nopostproc=hist_written,
        signatures=sigs,
    ))

json.dump(rows, open(OUT_JSON, "w"), indent=2)

ttbar = [r for r in rows if "ttbar" in r["run"].lower()]
print("runs surveyed: %d (ttbar in name: %d)" % (len(rows), len(ttbar)))
print("runs with a log-reported histogram total: %d"
      % len([r for r in rows if r["hist_total_merged"] is not None]))
print("written: %s" % OUT_JSON)
print()
hdr = ["date", "trigger", "OR", "maxj", "maxg", "maxt", "minFS", "zcut", "njob", "hist", "run"]
print(" | ".join(hdr))
for r in sorted(rows, key=lambda x: x["date"]):
    if r["hist_total_merged"] is None and r["trigger"] is None:
        continue
    print(" | ".join(str(x) for x in [
        r["date"], r["trigger"], r["overlap_removal"], r["max_j"], r["max_g"], r["max_t"],
        r["min_events_per_fs"], r["z_peak_cutoff"], r["num_jobs"],
        r["hist_total_merged"], r["run"][:58]]))
