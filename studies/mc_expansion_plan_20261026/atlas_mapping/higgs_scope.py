"""Step 5: the ATLAS Higgs DSIDs as a production x decay table, CMS coverage, and the cost of extra CMS Higgs cells.

Cost method = PLAN.md §4 / stats_cost.py: cluster files = (6014/497) x portal files + 2240/13 per sample;
CPU = events x (CPU s / event of the delivered ggH -> ZZ -> 4l, 37728, from the 25-26 Oct production audit).
All costs are ESTIMATES. Reads mapping.json; writes higgs_scope.json. Research only.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PLAN = HERE.parent
REPO = PLAN.parents[1]
sys.path.insert(0, str(PLAN))
import stats_cost as sc  # noqa: E402

M = json.loads((HERE / "mapping.json").read_text())
AUDIT = json.loads((REPO / "studies/fullrun_20261025/evidence/final_mc/production_audit.json").read_text())["records"]
RATE = AUDIT["37728"]["cpu_seconds_driver"] / AUDIT["37728"]["events_read"]
STATS = {s["recid"]: s for s in json.loads((PLAN / "evidence/stats_cost.json").read_text())["samples"]}

# Remaining cells that have a CMS sample, grouped by why they would (not) be worth adding
NO_LEPTON_OR_PHOTON = {"VBF_bb", "qqZH_bb_vv", "qqZH_cc_vv", "ggZH_bb_vv", "ggZH_cc_vv", "WH_inv", "qqZH_inv", "ggZH_inv"}
PHOTON = {"ggF_gamgam", "VBF_gamgam", "WH_gamgam", "qqZH_gamgam", "ggZH_gamgam"}
RECOMMENDED_ADD = {"ggF_mumu", "VBF_mumu", "WH_mumu", "qqZH_mumu", "ggF_Zgam", "VBF_Zgam", "WH_Zgam", "qqZH_Zgam", "ggZH_ZZ4l"}


def cost(recs):
    files = sum(r["files"] for r in recs)
    ev = sum(r["events"] for r in recs)
    return dict(samples=len(recs), files=files, events=ev,
                cluster_files=round(sc.FILES_PER_JOB * files + sc.BUILD_FILES_PER_SAMPLE * len(recs)),
                cpu_hours=ev * RATE / 3600)


def main():
    rows = [r for r in M["rows"] if r["category"] == "Higgs"]
    cells = []
    for r in rows:
        prod, dec = r["higgs_cell"]
        cells.append(dict(key=r["key"], production=prod, decay=dec, atlas_dsids=r["atlas_nominal_dsids"],
                          atlas_alternatives=r["atlas_alternatives"], atlas_sigma_pb_CROSSCHECK=r["atlas_sigma_nominal_pb_CROSSCHECK"],
                          cms_status=r["cms_status"], cms_records=r["cms_records"]))
    remaining = [c for c in cells if c["cms_status"] == "portal"]
    groups = {}
    for c in remaining:
        g = ("recommended to add" if c["key"] in RECOMMENDED_ADD else "no leptons on the CMS side" if c["key"] in NO_LEPTON_OR_PHOTON
             else "photon final state (deferred)" if c["key"] in PHOTON else "other (tiny, overlapping, or needs a decision)")
        groups.setdefault(g, []).append(c)
    allrecs = {r["recid"]: r for c in remaining for r in c["cms_records"]}
    out = dict(
        what="ATLAS Higgs DSIDs vs CMS Higgs samples (27 Oct 2026). Costs are ESTIMATES (PLAN §4 method).",
        cpu_rate_s_per_event=RATE, cpu_rate_source="production_audit.json record 37728",
        n_atlas_higgs_dsids=sum(len(c["atlas_dsids"]) + sum(len(v) for v in c["atlas_alternatives"].values()) for c in cells)
        + sum(len(r["atlas_subset_dsids"]) for r in rows),
        cells=cells,
        cost_all_remaining_cells_with_a_cms_sample=cost(list(allrecs.values())),
        cost_by_group={g: dict(cells=[c["key"] for c in cs], **cost(list({r["recid"]: r for c in cs for r in c["cms_records"]}.values())))
                       for g, cs in groups.items()},
        plan_tier5_cost=dict(samples=sum(1 for s in STATS.values() if s["tier"] == 5),
                             files=sum(s["files"] for s in STATS.values() if s["tier"] == 5),
                             cluster_files=round(sum(s["cluster_files"] for s in STATS.values() if s["tier"] == 5)
                                                 + sc.BUILD_FILES_PER_SAMPLE * sum(1 for s in STATS.values() if s["tier"] == 5)),
                             cpu_hours=sum(s["cpu_hours"] for s in STATS.values() if s["tier"] == 5)),
    )
    (HERE / "higgs_scope.json").write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n")
    print("ATLAS Higgs DSIDs", out["n_atlas_higgs_dsids"], "cells", len(cells))
    from collections import Counter
    print(Counter(c["cms_status"] for c in cells))
    print("all remaining", out["cost_all_remaining_cells_with_a_cms_sample"])
    for g, v in out["cost_by_group"].items():
        print(g, {k: v[k] for k in v if k != "cells"}, v["cells"])
    print("tier5", out["plan_tier5_cost"])


if __name__ == "__main__":
    main()
