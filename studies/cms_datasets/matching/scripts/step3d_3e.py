"""
Step 3d: matching-efficiency PNG plots per dataset (G+H pilot files summed),
vs leading/subleading selected-muon pT and |eta|. Reports the 25-26/26-27/
27-28 GeV bins and the plateau (pt>=40 GeV) efficiency explicitly.

Step 3e: accounting -- generic vs matched event counts at each stage, and
SingleMuon's exclusive fraction under the acceptance-based veto (matched)
vs the bits-based veto (generic).
"""
import json
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

BASE = "/storage/agrp/berkom/atlas-utilization/output/cms_datasets/matching_validation"
OUT_PLOTS = f"{BASE}/plots"
import os
os.makedirs(OUT_PLOTS, exist_ok=True)

DATASETS = {
    "DoubleMuon": ["DoubleMuon_30522_0_matched", "DoubleMuon_30555_0_matched"],
    "SingleMuon": ["SingleMuon_30530_0_matched", "SingleMuon_30563_0_matched"],
}


def sum_hist(entries, key):
    """Sum a list of job_metadata matching_diagnostics[key] num/den histogram
    dicts (same bin_edges_gev across files, since MATCHED_EFF_*_BIN_EDGES is
    a fixed module constant -- asserted, not assumed)."""
    edges = None
    num_total = None
    den_total = None
    for md in entries:
        h = md[key]
        n_edges = np.array(h["numerator_accepted"]["bin_edges_gev"])
        d_edges = np.array(h["denominator_has_required_muons"]["bin_edges_gev"])
        assert np.array_equal(n_edges, d_edges)
        if edges is None:
            edges = n_edges
        else:
            assert np.array_equal(edges, n_edges), "bin edges differ between files"
        n = np.array(h["numerator_accepted"]["counts"])
        d = np.array(h["denominator_has_required_muons"]["counts"])
        num_total = n if num_total is None else num_total + n
        den_total = d if den_total is None else den_total + d
    return edges, num_total, den_total


def eff_report(edges, num, den, label):
    centers = (edges[:-1] + edges[1:]) / 2
    print(f"--- {label} ---")
    for lo, hi in [(25, 26), (26, 27), (27, 28)]:
        m = (centers >= lo) & (centers < hi)
        n_, d_ = num[m].sum(), den[m].sum()
        eff = n_ / d_ if d_ else float("nan")
        print(f"  {lo}-{hi} GeV: num={n_} den={d_} eff={eff:.4f}" if d_ else f"  {lo}-{hi} GeV: EMPTY (no denominator entries)")
    plateau_mask = centers >= 40
    n_p, d_p = num[plateau_mask].sum(), den[plateau_mask].sum()
    print(f"  plateau (>=40 GeV): num={n_p} den={d_p} eff={n_p/d_p:.5f}")
    overall_n, overall_d = num.sum(), den.sum()
    print(f"  overall (all bins): num={overall_n} den={overall_d} eff={overall_n/overall_d:.5f}")
    return {
        "bins_25_26": eff_bin(centers, num, den, 25, 26),
        "bins_26_27": eff_bin(centers, num, den, 26, 27),
        "bins_27_28": eff_bin(centers, num, den, 27, 28),
        "plateau_ge_40": {"num": int(n_p), "den": int(d_p), "eff": float(n_p / d_p) if d_p else None},
        "overall": {"num": int(overall_n), "den": int(overall_d), "eff": float(overall_n / overall_d) if overall_d else None},
    }


def eff_bin(centers, num, den, lo, hi):
    m = (centers >= lo) & (centers < hi)
    n_, d_ = int(num[m].sum()), int(den[m].sum())
    return {"num": n_, "den": d_, "eff": (n_ / d_) if d_ else None}


def make_plot(edges, num, den, title, out_path, xlabel):
    centers = (edges[:-1] + edges[1:]) / 2
    with np.errstate(divide="ignore", invalid="ignore"):
        eff = np.where(den > 0, num / den, np.nan)
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8, 7), sharex=True,
                                     gridspec_kw={"height_ratios": [1, 2]})
    ax1.bar(centers, den, width=(edges[1] - edges[0]) * 0.9, color="lightgray", label="denominator (has required muons)")
    ax1.bar(centers, num, width=(edges[1] - edges[0]) * 0.9, color="steelblue", label="numerator (accepted)")
    ax1.set_yscale("log")
    ax1.set_ylabel("Events")
    ax1.legend(fontsize=8)
    ax2.plot(centers, eff, "o", markersize=3, color="darkorange")
    ax2.axhline(1.0, color="gray", linewidth=0.5, linestyle="--")
    ax2.axhline(0.9, color="red", linewidth=0.5, linestyle=":")
    ax2.set_ylim(0, 1.05)
    ax2.set_xlabel(xlabel)
    ax2.set_ylabel("Matching efficiency")
    fig.suptitle(title, fontsize=10)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    print(f"wrote {out_path}")


summary = {}
for dataset_label, run_dirs in DATASETS.items():
    entries = [json.load(open(f"{BASE}/{rd}/job_metadata.json"))["matching_diagnostics"] for rd in run_dirs]
    summary[dataset_label] = {}
    for key, xlabel, fname_suffix in [
        ("leading_muon_pt", "Leading selected-muon pT [GeV]", "leading_pt"),
        ("subleading_muon_pt", "Subleading selected-muon pT [GeV]", "subleading_pt"),
        ("leading_muon_abseta", "Leading selected-muon |eta|", "leading_abseta"),
        ("subleading_muon_abseta", "Subleading selected-muon |eta|", "subleading_abseta"),
    ]:
        edges, num, den = sum_hist(entries, key)
        report = eff_report(edges, num, den, f"{dataset_label} / {key}")
        summary[dataset_label][key] = report
        make_plot(edges, num, den,
                   f"{dataset_label} matching efficiency vs {xlabel}\n(pilot files G+H summed: {', '.join(run_dirs)})",
                   f"{OUT_PLOTS}/matching_efficiency_{dataset_label}_{fname_suffix}.png",
                   xlabel)

with open(f"{BASE}/step3d_efficiency_summary.json", "w") as f:
    json.dump(summary, f, indent=2)
print("wrote", f"{BASE}/step3d_efficiency_summary.json")

# --- Step 3e: accounting ---
print()
print("=== Step 3e: generic vs matched accounting ===")
acc = {}
for label, files in [("DoubleMuon", ["30522_0", "30555_0"]), ("SingleMuon", ["30530_0", "30563_0"])]:
    for f in files:
        gen = json.load(open(f"{BASE}/{label}_{f}_generic/job_metadata.json"))
        mat = json.load(open(f"{BASE}/{label}_{f}_matched/job_metadata.json"))
        key = f"{label}_{f}"
        acc[key] = {
            "n_read": gen["n_read"],
            "n_after_golden_json": gen["n_after_golden_json"],
            "generic_n_after_trigger": gen["n_after_trigger"],
            "matched_n_after_trigger": mat["n_after_trigger"],
            "generic_n_after_gate": gen["n_after_gate"],
            "matched_n_after_gate": mat["n_after_gate"],
            "generic_n_exclusive": gen["n_exclusive"],
            "matched_n_exclusive": mat["n_exclusive"],
            "generic_exclusive_fraction": gen["n_exclusive"] / gen["n_after_gate"] if gen["n_after_gate"] else None,
            "matched_exclusive_fraction": mat["n_exclusive"] / mat["n_after_gate"] if mat["n_after_gate"] else None,
        }
        print(f"{key}:")
        for k, v in acc[key].items():
            print(f"  {k}: {v}")
with open(f"{BASE}/step3e_accounting.json", "w") as f:
    json.dump(acc, f, indent=2)
print("wrote", f"{BASE}/step3e_accounting.json")
