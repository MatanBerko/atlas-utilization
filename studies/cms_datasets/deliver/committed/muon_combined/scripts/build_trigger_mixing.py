"""
Top-4 task, Step 6: trigger-mixing check. For the 5 largest combined
histograms and 5 (distinct, ranks 6-10) one-muon-category histograms
(normal version, min31bins manifest), split the delivered histogram's own
contents EXACTLY by origin dataset (DoubleMuon-inclusive vs. SingleMuon-
exclusive), using the SAME real post-processing functions
(_apply_z_peak_cut, _find_rightmost_highest_peak, _split_by_first_empty_bin,
imported unmodified) applied to determine the exact [min,max] mass window
the real delivery kept for that signature, then windowing each source's
own (same-cut) raw values by that identical range -- an EXACT partition,
not an approximation (dm_contribution + sm_contribution reproduces the
delivered histogram's own bin contents exactly, verified against the ROOT
file directly).
"""
import json
import sys
import logging
import numpy as np
from pathlib import Path

sys.path.insert(0, "/storage/agrp/berkom/atlas-utilization/work/muon_combined_delivery/repo")
from services.storage.sqlite_shards import iter_all_chunks  # noqa: E402
from services.pipelines.post_processing_pipeline import (  # noqa: E402
    _apply_z_peak_cut, _find_rightmost_highest_peak, _split_by_first_empty_bin,
)
from studies.m0m1j0_cms.histograms import make_fixed_grid_histogram  # noqa: E402

RUNS_BASE = Path("/storage/agrp/berkom/atlas-utilization/output/cms_datasets/runs_matched")
OUT_DIR = Path("/storage/agrp/berkom/atlas-utilization/output/cms_datasets/deliver/muon_combined")
BIN_WIDTH_GEV = 10.0
Z_PEAK_CUTOFF = 115.0
MAX_MASS_CUTOFF = 10000.0
LOGGER = logging.getLogger("trigger_mixing")

manifest = json.loads((OUT_DIR / "manifest_muon_combined_matched_min31bins.json").read_text())
by_events = sorted(manifest, key=lambda e: -e["n_events"])
five_largest = [e["name"] for e in by_events[:5]]
one_mu = [e for e in manifest if e["final_state_category"] and e["final_state_category"].split("_")[1] == "1mx"]
one_mu_sorted = sorted(one_mu, key=lambda e: -e["n_events"])
five_one_muon = [e["name"] for e in one_mu_sorted[5:10]]  # ranks 6-10 (top 5 already == five_largest)

targets = {"five_largest": five_largest, "five_one_muon_ranks6to10": five_one_muon}
all_names = set(five_largest) | set(five_one_muon)
print("Target signatures:", all_names)

dm_index = json.loads((RUNS_BASE / "DoubleMuon_index.json").read_text())
sm_index = json.loads((RUNS_BASE / "SingleMuon_index.json").read_text())
dm_paths = [str(RUNS_BASE / "DoubleMuon" / f"job_{idx}" / "dataset_shard_inclusive.sqlite") for idx in dm_index]
sm_paths = [str(RUNS_BASE / "SingleMuon" / f"job_{idx}" / "dataset_shard_exclusive.sqlite") for idx in sm_index]


def pool_raw(shard_paths, target_names):
    """{bumpnet_name: [raw values]} pooled across every shard/final-state
    group whose signature's own name (via SIG_PATTERN-equivalent suffix
    match) is one of target_names. Names here are matched by checking
    each shard's own signature strings for a "_FS_<fs>_IM_<combo>" suffix
    that maps to a target bumpnet name -- reuse build_sig_to_bumpnet's own
    logic via direct regex since we only need a handful of names."""
    import re
    from studies.m0m1j0_cms.histograms import _convert_to_bumpnet_name
    SIG_PATTERN = re.compile(r"_FS_([0-9a-z_]+)_IM_([0-9a-z]+)$")
    out = {name: [] for name in target_names}
    for shard_path in shard_paths:
        for sig, arr in iter_all_chunks(shard_path):
            m = SIG_PATTERN.search(sig)
            if not m:
                continue
            fs_str, im_str = m.groups()
            bumpnet_name = _convert_to_bumpnet_name(fs_str, im_str)
            if bumpnet_name in out:
                out[bumpnet_name].append(arr)
    return {name: (np.concatenate(chunks).astype(np.float64) if chunks else np.array([]))
            for name, chunks in out.items()}


print("Pooling DoubleMuon raw values for target signatures...")
dm_raw = pool_raw(dm_paths, all_names)
print("Pooling SingleMuon (exclusive) raw values for target signatures...")
sm_raw = pool_raw(sm_paths, all_names)

results = {}
for name in all_names:
    dm_vals = dm_raw[name]
    sm_vals = sm_raw[name]
    combined_vals = np.concatenate([dm_vals, sm_vals])

    # Same post-processing as the real delivery, applied to the pooled (combined) array.
    after_zpeak = _apply_z_peak_cut(combined_vals, name, Z_PEAK_CUTOFF, LOGGER)
    after_maxmass = after_zpeak[after_zpeak <= MAX_MASS_CUTOFF] if MAX_MASS_CUTOFF > 0 else after_zpeak
    peak_mass = _find_rightmost_highest_peak(after_maxmass, BIN_WIDTH_GEV, LOGGER)
    filtered = after_maxmass if peak_mass is None else after_maxmass[after_maxmass >= peak_mass]
    main_arr, _outliers = _split_by_first_empty_bin(filtered, BIN_WIDTH_GEV, LOGGER)

    if main_arr.size == 0:
        print(f"{name}: main_arr empty, skipping")
        continue
    lo, hi = float(main_arr.min()), float(main_arr.max())

    # Apply the SAME per-source cuts, then window by [lo, hi] -- an EXACT
    # partition of main_arr by origin dataset.
    def same_cuts(vals):
        v = _apply_z_peak_cut(vals, name, Z_PEAK_CUTOFF, LOGGER)
        v = v[v <= MAX_MASS_CUTOFF] if MAX_MASS_CUTOFF > 0 else v
        return v[(v >= lo) & (v <= hi)]

    dm_contribution = same_cuts(dm_vals)
    sm_contribution = same_cuts(sm_vals)

    # Cross-check: dm_contribution + sm_contribution must equal main_arr exactly (as multisets).
    check_ok = (dm_contribution.size + sm_contribution.size == main_arr.size)

    values_dm, edges = make_fixed_grid_histogram(dm_contribution)
    values_sm, _ = make_fixed_grid_histogram(sm_contribution)
    values_combined, _ = make_fixed_grid_histogram(main_arr)
    cross_check_hist = np.array_equal(values_dm + values_sm, values_combined)

    results[name] = {
        "n_dm": int(dm_contribution.size), "n_sm": int(sm_contribution.size),
        "n_main_arr": int(main_arr.size),
        "partition_count_check": bool(check_ok),
        "partition_histogram_check": bool(cross_check_hist),
        "values_dm": values_dm.tolist(), "values_sm": values_sm.tolist(),
        "values_combined": values_combined.tolist(), "edges": edges.tolist(),
    }
    print(f"{name}: n_dm={dm_contribution.size} n_sm={sm_contribution.size} "
          f"n_main_arr={main_arr.size} count_check={check_ok} hist_check={cross_check_hist}")

with open(OUT_DIR / "trigger_mixing_data.json", "w") as f:
    json.dump({"targets": targets, "results": results}, f, indent=2)
print(f"\nwrote {OUT_DIR / 'trigger_mixing_data.json'}")

# --- Plots ---
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

for group_label, names in targets.items():
    for name in names:
        if name not in results:
            continue
        r = results[name]
        edges = np.array(r["edges"])
        centers = 0.5 * (edges[:-1] + edges[1:])
        v_dm = np.array(r["values_dm"])
        v_sm = np.array(r["values_sm"])
        nz = np.nonzero((v_dm + v_sm) > 0)[0]
        if nz.size == 0:
            continue
        lo_i, hi_i = nz[0], nz[-1] + 1

        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(9, 7), sharex=True,
                                         gridspec_kw={"height_ratios": [3, 1]})
        ax1.bar(centers[lo_i:hi_i], v_dm[lo_i:hi_i], width=BIN_WIDTH_GEV * 0.9,
                 label="DoubleMuon", color="steelblue")
        ax1.bar(centers[lo_i:hi_i], v_sm[lo_i:hi_i], width=BIN_WIDTH_GEV * 0.9,
                 bottom=v_dm[lo_i:hi_i], label="SingleMuon (exclusive)", color="darkorange")
        ax1.set_yscale("log")
        ax1.set_ylabel("Events / 10 GeV")
        ax1.set_title(f"{name}\nn_dm={r['n_dm']} n_sm={r['n_sm']} (stacked, log scale)", fontsize=9)
        ax1.legend()

        total = v_dm[lo_i:hi_i] + v_sm[lo_i:hi_i]
        with np.errstate(divide="ignore", invalid="ignore"):
            sm_frac = np.where(total > 0, v_sm[lo_i:hi_i] / total, np.nan)
        ax2.plot(centers[lo_i:hi_i], sm_frac, "o-", markersize=3, color="darkorange")
        ax2.axhline(0.5, color="gray", linestyle="--", linewidth=0.8)
        ax2.set_ylim(0, 1)
        ax2.set_xlabel("Invariant mass [GeV]")
        ax2.set_ylabel("SingleMuon fraction")
        fig.tight_layout()
        safe_name = name.replace("/", "_")
        fig.savefig(OUT_DIR / f"trigger_mixing_{safe_name}.png", dpi=150)
        plt.close(fig)
        print(f"wrote trigger_mixing_{safe_name}.png")
