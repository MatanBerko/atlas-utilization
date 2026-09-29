"""
Top-4 task, Step 6: Z and J/psi resonance check on the COMBINED raw
m(mu0,mu1) -- i.e. the actually-delivered population (DoubleMuon
inclusive + SingleMuon exclusive, normal version), read directly from the
RAW per-event masses in the shards (BEFORE the z-peak cut / max-mass cut
/ peak-removal post-processing, which would otherwise remove the Z peak
at 91 GeV -- well below the 115 GeV z_peak_cutoff -- and the J/psi at
3.1 GeV entirely). Pools every "_IM_m0m1" signature (the leading+
subleading-muon combination) across every final-state category and every
shard, for both DoubleMuon-inclusive and SingleMuon-exclusive.
"""
import json
import sys
import numpy as np
from pathlib import Path

sys.path.insert(0, "/storage/agrp/berkom/atlas-utilization/work/muon_combined_delivery/repo")
from services.storage.sqlite_shards import iter_all_chunks  # noqa: E402

RUNS_BASE = Path("/storage/agrp/berkom/atlas-utilization/output/cms_datasets/runs_matched")
OUT_DIR = Path("/storage/agrp/berkom/atlas-utilization/output/cms_datasets/deliver/muon_combined")

dm_index = json.loads((RUNS_BASE / "DoubleMuon_index.json").read_text())
sm_index = json.loads((RUNS_BASE / "SingleMuon_index.json").read_text())

dm_paths = [str(RUNS_BASE / "DoubleMuon" / f"job_{idx}" / "dataset_shard_inclusive.sqlite") for idx in dm_index]
sm_paths = [str(RUNS_BASE / "SingleMuon" / f"job_{idx}" / "dataset_shard_exclusive.sqlite") for idx in sm_index]

m0m1_values_dm = []
m0m1_values_sm = []
for paths, bucket, label in [(dm_paths, m0m1_values_dm, "DoubleMuon"), (sm_paths, m0m1_values_sm, "SingleMuon")]:
    n_shards_done = 0
    for shard_path in paths:
        for sig, arr in iter_all_chunks(shard_path):
            if sig.endswith("_IM_m0m1"):
                bucket.append(arr)
        n_shards_done += 1
        if n_shards_done % 20 == 0:
            print(f"  {label}: {n_shards_done}/{len(paths)} shards scanned")
    print(f"{label}: {n_shards_done} shards scanned, {sum(a.size for a in bucket)} raw m0m1 values pooled")

m0m1_dm = np.concatenate(m0m1_values_dm).astype(np.float64) if m0m1_values_dm else np.array([])
m0m1_sm = np.concatenate(m0m1_values_sm).astype(np.float64) if m0m1_values_sm else np.array([])
m0m1_combined = np.concatenate([m0m1_dm, m0m1_sm])
m0m1_combined = m0m1_combined[~np.isnan(m0m1_combined)]

print(f"\nTotal combined raw m(mu0,mu1) entries: {m0m1_combined.size}")
print(f"  DoubleMuon contributes: {m0m1_dm.size}")
print(f"  SingleMuon contributes: {m0m1_sm.size}")

np.save(OUT_DIR / "raw_m0m1_combined.npy", m0m1_combined.astype(np.float32))
np.save(OUT_DIR / "raw_m0m1_doublemuon.npy", m0m1_dm.astype(np.float32))
np.save(OUT_DIR / "raw_m0m1_singlemuon_exclusive.npy", m0m1_sm.astype(np.float32))

# --- Z peak region: coarse histogram, simple Gaussian fit near 91 GeV ---
z_mask = (m0m1_combined > 70) & (m0m1_combined < 110)
z_vals = m0m1_combined[z_mask]
print(f"\nZ-window (70-110 GeV) entries: {z_vals.size}")

from scipy.optimize import curve_fit

def gauss(x, A, mu, sigma, bkg):
    return A * np.exp(-0.5 * ((x - mu) / sigma) ** 2) + bkg

counts, edges = np.histogram(z_vals, bins=80, range=(70, 110))
centers = 0.5 * (edges[:-1] + edges[1:])
p0 = [counts.max(), 91.0, 3.0, np.median(counts[:5])]
try:
    popt, pcov = curve_fit(gauss, centers, counts, p0=p0, maxfev=10000)
    perr = np.sqrt(np.diag(pcov))
    z_fit = {
        "amplitude": float(popt[0]), "mean_gev": float(popt[1]), "sigma_gev": float(popt[2]),
        "background": float(popt[3]),
        "mean_err_gev": float(perr[1]), "sigma_err_gev": float(perr[2]),
        "n_entries_in_window": int(z_vals.size),
    }
    print(f"Z fit: mean={popt[1]:.3f}+-{perr[1]:.3f} GeV, sigma={popt[2]:.3f}+-{perr[2]:.3f} GeV")
except Exception as e:
    z_fit = {"error": str(e), "n_entries_in_window": int(z_vals.size)}
    print(f"Z fit FAILED: {e}")

# --- J/psi region: fine-binned, look for an excess near 3.0-3.2 GeV ---
jpsi_mask = (m0m1_combined > 2.5) & (m0m1_combined < 3.7)
jpsi_vals = m0m1_combined[jpsi_mask]
print(f"\nJ/psi-window (2.5-3.7 GeV) entries: {jpsi_vals.size}")
counts_j, edges_j = np.histogram(jpsi_vals, bins=120, range=(2.5, 3.7))  # 10 MeV bins
centers_j = 0.5 * (edges_j[:-1] + edges_j[1:])
peak_bin = np.argmax(counts_j)
jpsi_summary = {
    "n_entries_in_window": int(jpsi_vals.size),
    "peak_bin_center_gev": float(centers_j[peak_bin]),
    "peak_bin_count": int(counts_j[peak_bin]),
    "median_count_away_from_peak": float(np.median(np.delete(counts_j, peak_bin))),
}
print(f"J/psi window peak bin: {centers_j[peak_bin]:.3f} GeV, count={counts_j[peak_bin]}, "
      f"median elsewhere={jpsi_summary['median_count_away_from_peak']:.1f}")

result = {
    "n_combined": int(m0m1_combined.size),
    "n_doublemuon": int(m0m1_dm.size),
    "n_singlemuon_exclusive": int(m0m1_sm.size),
    "z_fit": z_fit,
    "jpsi_window": jpsi_summary,
}
with open(OUT_DIR / "resonance_check.json", "w") as f:
    json.dump(result, f, indent=2)
print("\nwrote resonance_check.json")

# --- Plots ---
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

fig, ax = plt.subplots(figsize=(7, 5))
ax.bar(centers, counts, width=(edges[1] - edges[0]), color="steelblue", alpha=0.7, label="data")
if "error" not in z_fit:
    xs = np.linspace(70, 110, 400)
    ax.plot(xs, gauss(xs, *popt), "r-", linewidth=2,
             label=f"Gaussian fit: mean={popt[1]:.2f}$\\pm${perr[1]:.2f} GeV\nsigma={popt[2]:.2f}$\\pm${perr[2]:.2f} GeV")
ax.set_xlabel("m(mu0, mu1) [GeV]")
ax.set_ylabel("Events / 0.5 GeV")
ax.set_title("Combined raw dimuon mass -- Z peak region")
ax.legend()
fig.tight_layout()
fig.savefig(OUT_DIR / "plots_z_peak.png", dpi=150)
plt.close(fig)

fig, ax = plt.subplots(figsize=(7, 5))
ax.bar(centers_j, counts_j, width=(edges_j[1] - edges_j[0]), color="darkorange", alpha=0.8)
ax.set_xlabel("m(mu0, mu1) [GeV]")
ax.set_ylabel("Events / 10 MeV")
ax.set_title("Combined raw dimuon mass -- J/psi window (2.5-3.7 GeV)")
fig.tight_layout()
fig.savefig(OUT_DIR / "plots_jpsi_window.png", dpi=150)
plt.close(fig)
print("wrote plots_z_peak.png, plots_jpsi_window.png")
