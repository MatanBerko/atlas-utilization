"""
nonjet4 task, Step 6: required plots -- largest, median, near-the-25-bin-
boundary, 3 one-muon categories, crop comparison. Adapted from the top-4
task's own build_required_plots.py (same logic, nonjet4 version only).
"""
import sys
import json
from pathlib import Path

sys.path.insert(0, "/storage/agrp/berkom/atlas-utilization/work/nonjet4_delivery/repo")

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import uproot

from studies.cms_coverage.deliver.make_check_plots import plot_one  # noqa: E402

OUT_DIR = Path("/storage/agrp/berkom/atlas-utilization/output/cms_datasets/deliver/muon_combined_nonjet4")
prefix = "muon_combined_matched_nonjet4"


def is_one_muon(entry):
    cat = entry.get("final_state_category") or ""
    parts = cat.split("_")
    return len(parts) > 1 and parts[1] == "1mx"


manifest_a = json.loads((OUT_DIR / f"manifest_{prefix}_min31bins.json").read_text())  # >30 bins
manifest_b = json.loads((OUT_DIR / f"manifest_{prefix}_min26bins.json").read_text())  # >25 bins
root_a = OUT_DIR / f"{prefix}_bumpnet_min31bins.root"
root_b = OUT_DIR / f"{prefix}_bumpnet_min26bins.root"
root_a_cropped = OUT_DIR / f"{prefix}_bumpnet_min31bins_cropped.root"

by_events_a = sorted(manifest_a, key=lambda e: e["n_events"])
largest = by_events_a[-1]
median_idx = len(by_events_a) // 2
median_entry = by_events_a[median_idx]

names_a = set(e["name"] for e in manifest_a)
extra_b = [e for e in manifest_b if e["name"] not in names_a]
if extra_b:
    near_boundary = min(extra_b, key=lambda e: abs(e["n_filled_bins"] - 26))
    near_boundary_root = root_b
else:
    near_boundary = min(manifest_a, key=lambda e: abs(e["n_filled_bins"] - 31))
    near_boundary_root = root_a

plot_one(root_a, largest, OUT_DIR / "plot_nonjet4_1_largest.png",
          f"Largest by event count ({root_a.name})")
plot_one(root_a, median_entry, OUT_DIR / "plot_nonjet4_2_median.png",
          f"Median by event count, position {median_idx + 1}/{len(by_events_a)} ({root_a.name})")
plot_one(near_boundary_root, near_boundary, OUT_DIR / "plot_nonjet4_3_near_25bin_boundary.png",
          f"Near the 25-bin boundary ({near_boundary_root.name})")

one_muon_entries = sorted([e for e in manifest_a if is_one_muon(e)], key=lambda e: -e["n_events"])
for i, entry in enumerate(one_muon_entries[:3], start=1):
    plot_one(root_a, entry, OUT_DIR / f"plot_nonjet4_one_muon_{i}.png",
              f"One-muon category #{i} ({root_a.name})")

key = f"ROI_{largest['name']}_width_10"
f_un = uproot.open(str(root_a))
f_cr = uproot.open(str(root_a_cropped))
h_un, h_cr = f_un[key], f_cr[key]
v_un, e_un = h_un.values(), h_un.axis().edges()
v_cr, e_cr = h_cr.values(), h_cr.axis().edges()

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))
ax1.stairs(v_un, e_un, fill=False, linewidth=1.0)
ax1.set_yscale("log")
ax1.set_xlabel("Invariant mass [GeV]")
ax1.set_ylabel("Events / 10 GeV")
ax1.set_title(f"UNCROPPED ({root_a.name})\n{v_un.size} bins, bin 1 = {v_un[0]:.0f}", fontsize=9)
ax1.set_xlim(0, e_un[-1])
ax2.stairs(v_cr, e_cr, fill=False, linewidth=1.2, color="darkorange")
ax2.set_yscale("log")
ax2.set_xlabel("Invariant mass [GeV]")
ax2.set_ylabel("Events / 10 GeV")
ax2.set_title(f"CROPPED\n{e_cr[0]:.0f}-{e_cr[-1]:.0f} GeV, {v_cr.size} bins, bin 1 = {v_cr[0]:.0f}", fontsize=9)
ax2.set_xlim(e_cr[0], e_cr[-1])
fig.suptitle(largest["name"], fontsize=10)
fig.tight_layout()
fig.savefig(OUT_DIR / "plot_nonjet4_crop_comparison.png", dpi=150)
plt.close(fig)
print("wrote plot_nonjet4_crop_comparison.png")

print("\nDONE all required plots for nonjet4.")
