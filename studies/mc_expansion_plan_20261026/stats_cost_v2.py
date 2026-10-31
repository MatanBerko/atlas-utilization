"""Statistics and cost of the final sample list (31 Oct 2026, DECISIONS.md). Research only.

Same method as stats_cost.py (26 Oct; kept unchanged), for plan_samples_v2.SAMPLES_V2:
- portal events / files: evidence/records/ (atlas_mapping/cms_records/ for 40062);
- sigma_eff: evidence/xsec_proposals_v2.json (PROPOSED; for DECISION-NEEDED cards the
  placeholder = option (a), the generator value);
- N_eff, sum w: the probe of file 0 scaled to the sample (evidence/probe/ of 26 Oct or
  evidence/probe_v2/ of 31 Oct) -- every planned sample is now probed;
- CPU: events x CPU seconds per event of the most similar delivered sample (25-26 Oct audit);
- cluster files: 6014/497 per input file + 2240/13 per sample (17 Oct measurements);
- the projection starts from the file count measured on 31 Oct after the probe (93,638).

Writes evidence/stats_cost_v2.json and evidence/stats_table_v2.md.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
from plan_samples_v2 import SAMPLES_V2  # noqa: E402
from stats_cost import BUILD_FILES_PER_SAMPLE, CLONE_FILES, FILES_PER_JOB, L_DATA_PB, QUOTA_MAX, WALL_LIMIT_S  # noqa: E402
from xsec_proposals_v2 import load  # noqa: E402

QUOTA_NOW = 93638   # lfs quota -u berkom /storage, 31 Oct 2026 after probe 5420807[] (92,041 before); VERIFIED BY RUNNING
ANALOG = {"a_wjets": "35669", "b_singletop": "64895", "c_tthad": "67993", "d_diboson": "72752",
          "e_triboson": "72752", "g_higgs": "37728", "h_ewk_v2j": "35669", "i_znunu": "35669"}


def analog_for(recid, group):
    if group == "f_raretop":
        return {68325: "64895", 64873: "64895"}.get(recid, "68187")
    return ANALOG[group]


def main():
    cards = {c["recid"]: c for c in json.loads((HERE / "evidence" / "xsec_proposals_v2.json").read_text())["cards"]}
    audit = json.loads((REPO / "studies/fullrun_20261025/evidence/final_mc/production_audit.json").read_text())["records"]
    rate = {k: v["cpu_seconds_driver"] / v["events_read"] for k, v in audit.items()}
    out = []
    for recid, name, group, tier, status, dec in SAMPLES_V2:
        d = load(recid)["distribution"]
        n, nf = d["number_events"], d["number_files"]
        c = cards[recid]
        s = c["options"][0][1] if c["options"] else c["sigma_eff_pb"]
        pr = next(p for p in (HERE / "evidence" / "probe_v2" / f"probe_{recid}.json",
                              HERE / "evidence" / "probe" / f"probe_{recid}.json") if p.exists())
        p = json.loads(pr.read_text())
        scale = n / p["events_in_file"]
        sumw, sumw2 = p["sum_w"] * scale, p["sum_w2"] * scale
        neff = sumw ** 2 / sumw2
        a = analog_for(recid, group)
        cpu_s = n * rate[a]
        out.append(dict(recid=recid, name=name, group=group, tier=tier, status=status, decision=dec,
                        events=n, files=nf, sigma_eff_pb_PROPOSED=s,
                        sigma_is_placeholder=bool(c["options"]),
                        weight_per_event_x_genWeight=s * L_DATA_PB / sumw,
                        n_eff=neff, mc_lumi_fb=neff / s / 1000, mc_lumi_over_data=neff / s / L_DATA_PB,
                        probe=str(pr.relative_to(HERE)), probe_frac_negative=p["frac_negative"],
                        cpu_analog=a, cpu_hours=cpu_s / 3600, cpu_s_per_file=cpu_s / nf,
                        over_walltime=cpu_s / nf > WALL_LIMIT_S, cluster_files=FILES_PER_JOB * nf))
    cum, proj = QUOTA_NOW, []
    for t in sorted({o["tier"] for o in out}):
        sel = [o for o in out if o["tier"] == t and o["status"] == "planned"]
        add = sum(o["cluster_files"] for o in sel) + BUILD_FILES_PER_SAMPLE * len(sel)
        cum += add
        proj.append(dict(tier=t, samples=len(sel), files=sum(o["files"] for o in sel),
                         events=sum(o["events"] for o in sel), cpu_hours=sum(o["cpu_hours"] for o in sel),
                         cluster_files_added=add, cumulative=cum, fits=cum + CLONE_FILES < QUOTA_MAX))
    res = dict(what="Statistics and cost of the final list (31 Oct); sigma_eff PROPOSED, placeholders where a decision is needed",
               quota_now=QUOTA_NOW, quota_max=QUOTA_MAX, files_per_job=FILES_PER_JOB,
               build_files_per_sample=BUILD_FILES_PER_SAMPLE, clone_files=CLONE_FILES,
               cpu_source="studies/fullrun_20261025/evidence/final_mc/production_audit.json (audit job 5341394)",
               samples=out, tiers=proj)
    (HERE / "evidence" / "stats_cost_v2.json").write_text(json.dumps(res, indent=1) + "\n")
    L = ["| tier | record | sample | status | events | files | σ_eff [pb] | N_eff | MC lumi [fb⁻¹] | ÷ data | CPU h | CPU s/file | cluster files |",
         "|---:|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for o in out:
        L.append(f"| {o['tier']} | {o['recid']} | {o['name']} | {o['status']}{' (σ placeholder)' if o['sigma_is_placeholder'] else ''} | "
                 f"{o['events']:,} | {o['files']} | {o['sigma_eff_pb_PROPOSED']:.4g} | {o['n_eff'] / 1e6:.3g} M | {o['mc_lumi_fb']:.3g} | "
                 f"{o['mc_lumi_over_data']:.3g}{' **< data**' if o['mc_lumi_over_data'] < 1 else ''} | {o['cpu_hours']:.1f} | {o['cpu_s_per_file']:.0f}{' **> 2 h**' if o['over_walltime'] else ''} | {o['cluster_files']:.0f} |")
    L += ["", f"| tier | samples | files | events | CPU h | cluster files added | cumulative (from {QUOTA_NOW:,}) | under 125,000? |",
          "|---:|---:|---:|---:|---:|---:|---:|---|"]
    for p in proj:
        L.append(f"| {p['tier']} | {p['samples']} | {p['files']} | {p['events']:,} | {p['cpu_hours']:.0f} | {p['cluster_files_added']:,.0f} | {p['cumulative']:,.0f} | {'yes' if p['fits'] else 'NO'} |")
    tot = dict(samples=sum(p["samples"] for p in proj), files=sum(p["files"] for p in proj), events=sum(p["events"] for p in proj),
               cpu=sum(p["cpu_hours"] for p in proj), add=sum(p["cluster_files_added"] for p in proj))
    L.append(f"| all | {tot['samples']} | {tot['files']} | {tot['events']:,} | {tot['cpu']:.0f} | {tot['add']:,.0f} | {proj[-1]['cumulative']:,.0f} | {'yes' if proj[-1]['fits'] else 'NO'} |")
    (HERE / "evidence" / "stats_table_v2.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
