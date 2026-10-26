"""Statistics and cost of the planned samples (26 Oct 2026). Research only.

Inputs (all in git):
- evidence/records_summary.json      portal events, files, size, negative-weight fraction
- evidence/xsec_proposals.json       PROPOSED sigma_eff (PROVISIONAL, not decided)
- studies/fullrun_20261025/evidence/final_mc/production_audit.json
                                     the 25-26 Oct MC production audit (PBS job 5341394):
                                     CPU seconds and events per record, output files per job
- evidence/probe/probe_<recid>.json  probe results, when they exist (else the portal estimate)

Writes evidence/stats_cost.json and prints a table.

Estimates used when no probe result exists (labelled ESTIMATE):
- sum_w / N = 1 - 2 f and N_eff = N (1 - 2 f)^2, f = portal negative-weight fraction:
  exact only if |genWeight| is the same for every event (true for the MG5 LO/NLO samples,
  only approximate for POWHEG);
- CPU = events x (CPU seconds / event of the most similar delivered sample).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
from plan_samples import SAMPLES  # noqa: E402

L_DATA_PB = 16393.0          # 16.393 fb^-1
QUOTA_NOW = 90665            # lfs quota at the end of 26 Oct (fullrun_20261025/HANDOFF.md); not re-measured here
QUOTA_MAX = 125000
FILES_PER_JOB = 6014 / 497   # 17 Oct MC production, measured (fullrun_20261025/HANDOFF.md projection table)
BUILD_FILES_PER_SAMPLE = 2240 / 13  # 17 Oct MC build + post incl. kept scratch, for 13 samples
CLONE_FILES = 170            # one pinned clone (measured ~170, same table)
WALL_LIMIT_S = 7200          # the 2 h walltime used for most MC arrays on 25 Oct

# most similar delivered sample, for CPU seconds per event
ANALOG = {"a_wjets": "35669", "b_singletop": "64895", "c_tthad": "67993", "d_diboson": "72752",
          "e_triboson": "72752", "g_higgs": "37728"}
ANALOG_RARE = {68325: "64895", 64873: "64895"}   # tZq, tWll like single top; the tt+X ones like ttZ


def analog_for(recid, group):
    if group == "f_raretop":
        return ANALOG_RARE.get(recid, "68187")
    return ANALOG[group]


def main():
    rows = {r["nano_recid"]: r for r in json.loads((HERE / "evidence" / "records_summary.json").read_text())["rows"]}
    xs = {p["recid"]: p["sigma_eff_pb"] for p in json.loads((HERE / "evidence" / "xsec_proposals.json").read_text())["proposals"]}
    audit = json.loads((REPO / "studies/fullrun_20261025/evidence/final_mc/production_audit.json").read_text())["records"]
    rate = {k: v["cpu_seconds_driver"] / v["events_read"] for k, v in audit.items()}
    probe_dir = HERE / "evidence" / "probe"
    out = []
    for recid, name, group, tier, role in SAMPLES:
        if role == "optional":
            continue
        r = rows[recid]
        n, nf = r["number_events"], r["number_files"]
        f = float((r["portal_cross_section"] or {}).get("neg_weight_fraction") or 0.0)
        s = xs.get(recid)
        pr = probe_dir / f"probe_{recid}.json"
        if pr.exists():
            p = json.loads(pr.read_text())
            scale = n / p["events_in_file"]
            sumw, sumw2 = p["sum_w"] * scale, p["sum_w2"] * scale
            neff = sumw ** 2 / sumw2
            mean_w = p["sum_w"] / p["events_in_file"]
            how = "PROBE (file 0 scaled to the sample)"
        else:
            mean_w = 1.0 - 2.0 * f   # in units of |w|
            sumw = n * mean_w
            neff = n * mean_w ** 2
            how = "ESTIMATE from the portal negative-weight fraction"
        lumi_mc_pb = neff / s if s else None
        a = analog_for(recid, group)
        cpu_s = n * rate[a]
        out.append(dict(
            recid=recid, name=name, group=group, tier=tier, role=role,
            events=n, files=nf, size_gb=r["size_bytes"] / 1e9, neg_frac_portal=f,
            sigma_eff_pb_PROVISIONAL=s,
            weight_per_event_PROVISIONAL=(s * L_DATA_PB / sumw) if s else None,
            weight_note="in units of the sample's mean |genWeight|" if not pr.exists() else "x genWeight",
            n_eff=neff, mc_lumi_fb=lumi_mc_pb / 1000 if lumi_mc_pb else None,
            mc_lumi_over_data=lumi_mc_pb / L_DATA_PB if lumi_mc_pb else None,
            stats_source=how,
            cpu_analog=a, cpu_s_per_event_analog=rate[a], cpu_hours=cpu_s / 3600,
            cpu_s_per_file=cpu_s / nf, over_walltime=cpu_s / nf > WALL_LIMIT_S,
            cluster_files=FILES_PER_JOB * nf,
        ))
    tiers = sorted({o["tier"] for o in out})
    cum, proj = QUOTA_NOW, []
    for t in tiers:
        sel = [o for o in out if o["tier"] == t and o["role"] == "recommended"]
        add = sum(o["cluster_files"] for o in sel) + BUILD_FILES_PER_SAMPLE * len(sel)
        cum += add
        proj.append(dict(tier=t, samples=len(sel), files=sum(o["files"] for o in sel),
                         events=sum(o["events"] for o in sel), cpu_hours=sum(o["cpu_hours"] for o in sel),
                         cluster_files_added=add, cumulative_quota=cum, fits=cum + CLONE_FILES < QUOTA_MAX))
    res = dict(
        what="Statistics and cost of the planned samples; sigma_eff values are PROPOSALS (PROVISIONAL)",
        data_luminosity_fb=L_DATA_PB / 1000, quota_now=QUOTA_NOW,
        quota_now_source="lfs quota 26 Oct 2026 end of the full run (studies/fullrun_20261025/HANDOFF.md); NOT re-measured in this task (cluster unreachable)",
        quota_max=QUOTA_MAX, files_per_job=FILES_PER_JOB, build_files_per_sample=BUILD_FILES_PER_SAMPLE,
        cpu_rates_s_per_event={k: rate[k] for k in sorted(set(ANALOG.values()) | set(ANALOG_RARE.values()) | {"68187"})},
        cpu_source="studies/fullrun_20261025/evidence/final_mc/production_audit.json (audit job 5341394 of the 25-26 Oct production arrays 5340549[]-5340560[], 5341381[]): cpu_seconds_driver / events_read",
        samples=out, tiers=proj)
    (HERE / "evidence" / "stats_cost.json").write_text(json.dumps(res, indent=1) + "\n")
    for o in out:
        print(f"{o['tier']} {o['role'][:3]} {o['recid']} {o['name'][:38]:38s} N={o['events']/1e6:7.2f}M files={o['files']:4d} "
              f"sig={o['sigma_eff_pb_PROVISIONAL']:.4g} Neff={o['n_eff']/1e6:7.2f}M Lmc={o['mc_lumi_fb']:9.3g}fb "
              f"x{o['mc_lumi_over_data']:8.3g} cpu={o['cpu_hours']:6.1f}h s/file={o['cpu_s_per_file']:6.0f}{' OVER' if o['over_walltime'] else ''}")
    for p in proj:
        print(p)


if __name__ == "__main__":
    main()
