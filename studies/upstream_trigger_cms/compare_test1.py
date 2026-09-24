"""
Test 1 comparison: cms/pipeline-baseline (run a) vs test/upstream-trigger-cms
with trigger_config absent (run b). Reads the NORMAL (non-blinded) output only.
Binning: 100-180 GeV, 0.5 GeV width -- same convention already used for display
histograms in studies/hgg_cms/cluster/d3_analysis.py (np.arange(100.0, 180.5, 0.5)).
Not a new/invented binning choice.
"""
import json
import sys
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, "/storage/agrp/berkom/atlas-utilization/work/upstream_trigger_cms/repo")
import studies.hgg_cms.output as out

PATH_A = Path("/storage/agrp/berkom/atlas-utilization/work/upstream_trigger_cms/repo/test_output/run_a/selected/parsed_record_30521_batch1_final.root")
PATH_B = Path("/storage/agrp/berkom/atlas-utilization/work/upstream_trigger_cms/repo_test_branch/test_output/run_b/selected/parsed_record_30521_batch1_final.root")
OUT_DIR = Path("/storage/agrp/berkom/atlas-utilization/work/upstream_trigger_cms/report_assets")
OUT_DIR.mkdir(parents=True, exist_ok=True)

arr_a = out.read_output(PATH_A)
arr_b = out.read_output(PATH_B)

print("n_events a:", len(arr_a))
print("n_events b:", len(arr_b))

mgg_a = arr_a["m_gg"].to_numpy()
mgg_b = arr_b["m_gg"].to_numpy()

edges = np.arange(100.0, 180.5, 0.5)  # existing d3_analysis.py convention
hist_a, _ = np.histogram(mgg_a, bins=edges)
hist_b, _ = np.histogram(mgg_b, bins=edges)

identical = np.array_equal(hist_a, hist_b)
diff_bins = np.where(hist_a != hist_b)[0]

result = {
    "n_events_a": int(len(arr_a)),
    "n_events_b": int(len(arr_b)),
    "n_events_identical": bool(len(arr_a) == len(arr_b)),
    "mgg_sum_a": float(np.sum(mgg_a)),
    "mgg_sum_b": float(np.sum(mgg_b)),
    "mgg_values_identical": bool(np.array_equal(np.sort(mgg_a), np.sort(mgg_b))),
    "n_bins": len(edges) - 1,
    "bin_edges_lo": 100.0,
    "bin_edges_hi": 180.0,
    "bin_width": 0.5,
    "histograms_identical": bool(identical),
    "n_differing_bins": int(len(diff_bins)),
    "differing_bins": [
        {"bin_index": int(i), "edge_lo": float(edges[i]), "edge_hi": float(edges[i+1]),
         "count_a": int(hist_a[i]), "count_b": int(hist_b[i])}
        for i in diff_bins
    ],
}
print(json.dumps(result, indent=2))

with open(OUT_DIR / "test1_comparison_result.json", "w") as f:
    json.dump(result, f, indent=2)

# per-category counts too (categorical breakdown, extra cross-check)
cat_a = arr_a["category"].to_list()
cat_b = arr_b["category"].to_list()
from collections import Counter
ca = dict(Counter(cat_a))
cb = dict(Counter(cat_b))
print("category counts a:", ca)
print("category counts b:", cb)
print("category counts identical:", ca == cb)

with open(OUT_DIR / "test1_category_counts.json", "w") as f:
    json.dump({"a": ca, "b": cb, "identical": ca == cb}, f, indent=2)

# --- PNGs ---
fig, ax = plt.subplots(figsize=(8, 5))
ax.hist(mgg_a, bins=edges, histtype="step", color="C0", linewidth=1.5)
ax.set_xlabel("m_gg [GeV]")
ax.set_ylabel("Events / 0.5 GeV")
ax.set_title("cms/pipeline-baseline (run a) -- H→γγ data, record 30521, batch 1")
fig.tight_layout()
fig.savefig(OUT_DIR / "test1_hist_run_a.png", dpi=150)
plt.close(fig)

fig, ax = plt.subplots(figsize=(8, 5))
ax.hist(mgg_b, bins=edges, histtype="step", color="C1", linewidth=1.5)
ax.set_xlabel("m_gg [GeV]")
ax.set_ylabel("Events / 0.5 GeV")
ax.set_title("test/upstream-trigger-cms, trigger_config absent (run b) -- same file")
fig.tight_layout()
fig.savefig(OUT_DIR / "test1_hist_run_b.png", dpi=150)
plt.close(fig)

fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8, 7), sharex=True,
                                gridspec_kw={"height_ratios": [3, 1]})
centers = 0.5 * (edges[:-1] + edges[1:])
ax1.step(centers, hist_a, where="mid", color="C0", label="run a: cms/pipeline-baseline", linewidth=1.5)
ax1.step(centers, hist_b, where="mid", color="C1", label="run b: test/upstream-trigger-cms", linewidth=1.0, linestyle="--")
ax1.set_ylabel("Events / 0.5 GeV")
ax1.legend()
ax1.set_title("Test 1 overlay: m_gg, non-blinded output, record 30521 batch 1")

with np.errstate(divide="ignore", invalid="ignore"):
    ratio = np.where(hist_a > 0, hist_b / hist_a, np.nan)
ax2.axhline(1.0, color="k", linewidth=0.8)
ax2.step(centers, ratio, where="mid", color="C2")
ax2.set_ylabel("b / a")
ax2.set_xlabel("m_gg [GeV]")
ax2.set_ylim(0.9, 1.1)
fig.tight_layout()
fig.savefig(OUT_DIR / "test1_overlay_ratio.png", dpi=150)
plt.close(fig)

print("Wrote PNGs and JSON to", OUT_DIR)
