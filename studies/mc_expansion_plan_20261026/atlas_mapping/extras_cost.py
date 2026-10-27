"""Cost of the non-Higgs CMS samples the ATLAS mapping suggests considering (27 Oct 2026). ESTIMATES, PLAN §4 method.

Same method as stats_cost.py; CPU analogs: EW V+2 jets like DY (35669), VBS like WZ -> 3lnu (72752),
tt+X like ttZ (68187). Reads candidates.json; writes extras_cost.json. Research only.
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PLAN = HERE.parent
REPO = PLAN.parents[1]
sys.path.insert(0, str(PLAN))
import stats_cost as sc  # noqa: E402

CANDS = {c["nano_recid"]: c for c in json.loads((PLAN / "candidates.json").read_text())["candidates"]}
AUDIT = json.loads((REPO / "studies/fullrun_20261025/evidence/final_mc/production_audit.json").read_text())["records"]
rate = lambda k: AUDIT[k]["cpu_seconds_driver"] / AUDIT[k]["events_read"]  # noqa: E731
HIGGS = json.loads((HERE / "higgs_scope.json").read_text())

GROUPS = {
    "EW V + 2 jets (Z → ℓℓ jj, W± → ℓν jj)": ([35999, 35987, 35993], "35669"),
    "VBS (ZZjj → 4ℓ, WLLJJ, WWjj → 2ℓ2ν, W±W±jj EWK + QCD)": ([75561, 69771, 72648, 71638, 71642], "72752"),
    "tt̄WW and three-top (TTWW, TTTJ, TTTW)": ([68087, 67771, 68067], "68187"),
}


def main():
    out, tot_cf = {}, 0
    for g, (recs, an) in GROUPS.items():
        rows = [dict(recid=r, name=CANDS[r]["dataset"].split("/")[1], events=CANDS[r]["number_events"],
                     files=CANDS[r]["number_files"], portal_total_value=(CANDS[r]["portal_cross_section"] or {}).get("total_value"))
                for r in recs]
        files = sum(x["files"] for x in rows)
        ev = sum(x["events"] for x in rows)
        cf = round(sc.FILES_PER_JOB * files + sc.BUILD_FILES_PER_SAMPLE * len(rows))
        tot_cf += cf
        out[g] = dict(records=rows, files=files, events=ev, cluster_files=cf, cpu_hours=ev * rate(an) / 3600, cpu_analog=an)
    tier5_cum = 112616  # PLAN §4 projection after all five tiers (from 92,041 measured 26 Oct)
    hig = HIGGS["cost_by_group"]["recommended to add"]["cluster_files"]
    res = dict(what="ESTIMATES; portal values are NOT proposals", groups=out,
               quota_projection=dict(after_tier5=tier5_cum, plus_recommended_higgs=tier5_cum + hig,
                                     plus_all_extras_here=tier5_cum + hig + tot_cf, ceiling=sc.QUOTA_MAX,
                                     note="projection from the 26 Oct measurement (92,041); not re-measured (no cluster use in this task)"))
    (HERE / "extras_cost.json").write_text(json.dumps(res, indent=1, ensure_ascii=False) + "\n")
    for g, v in out.items():
        print(g, v["files"], v["events"], v["cluster_files"], round(v["cpu_hours"], 1))
    print(res["quota_projection"])


if __name__ == "__main__":
    main()
