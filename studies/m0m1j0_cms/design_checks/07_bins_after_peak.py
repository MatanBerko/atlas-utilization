"""
m0m1j0 design phase, follow-up correction: "bins after the peak", using
the FIXED shared convention (0-10,000 GeV, 10 GeV width -> 1000 bins,
`services/pipelines/histograms_pipeline.py:22-23`) and the SAME "peak"
definition the shared pipeline itself uses for its own peak-removal
step -- `_apply_peak_removal_to_histogram`
(`services/pipelines/histograms_pipeline.py:625-645`): the peak is the
RIGHTMOST bin holding the histogram's maximum bin content (its own
loop runs `for bin_idx in range(nbins, 0, -1)` and takes the first
match), not the sample's highest individual event value. This corrects
an error in DESIGN.md's first pass, which conflated "bins after the
sample's highest event" with "bins after the histogram's peak bin" --
the paper's own rule (arXiv:2501.05603v1 Section 2.2.2, "Histogram
production": "only bins after the histogram maximum are kept").

Reuses the exact same data-loading and object-selection code as
`01_load_and_analyze.py` (imported by file path below, not duplicated)
-- same two files, same first 500,000 events each, same HTTPS read
path, same golden-JSON/trigger/muon/jet selection. No new data read
beyond what that script already reads.

Four variants of the proposed selection's own final m(mumuj) sample:
  (i)   all events passing the full proposed selection
  (ii)  (i) restricted to m(mumu) OUTSIDE [76.18, 106.18] GeV -- a
        PROXY for the paper-style Z-collapsed histogram, since real
        Z-candidate collapsing (removing the matched leptons and
        considering the REST of the event) is not implemented anywhere
        in this repo (DESIGN.md Section B) -- this only removes events
        whose LEADING pair sits in the Z window, it does not look for
        a Z candidate elsewhere in the event or rebuild the leading
        pair from remaining muons.
  (iii) (ii) restricted to opposite-sign muon pairs
  (iv)  (ii) restricted to same-sign muon pairs

No significance/p-value/sigma computed here.
"""
from __future__ import annotations

import importlib.util
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")

import awkward as ak
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import common  # noqa: E402

REPO_ROOT = HERE.parents[2]
sys.path.insert(0, str(REPO_ROOT))
from services.parsing.validated_runs import (  # noqa: E402
    ValidatedRunsFilter,
    apply_validated_runs_filter,
)

# Import 01_load_and_analyze.py by file path (its module name starts with a
# digit, so a plain `import` statement cannot name it) -- reuses that
# script's own selection functions verbatim, no duplicated/divergent logic.
_spec = importlib.util.spec_from_file_location(
    "load_and_analyze", HERE / "01_load_and_analyze.py")
lna = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(lna)

FIXED_MASS_MIN_GEV = 0.0
FIXED_MASS_MAX_GEV = 10000.0
FIXED_BIN_WIDTH_GEV = 10.0
FIXED_EDGES = np.arange(FIXED_MASS_MIN_GEV, FIXED_MASS_MAX_GEV + FIXED_BIN_WIDTH_GEV, FIXED_BIN_WIDTH_GEV)
assert len(FIXED_EDGES) - 1 == 1000

Z_LO, Z_HI = 76.18, 106.18

# Extrapolation factors already used in DESIGN.md Section E (event counts
# only -- the number of non-empty bins is NOT extrapolated, since it
# depends on the actual high-mass tail populating at full statistics,
# not a linear scaling of a 500,000-event subsample).
EXTRAP_FACTOR = {"30522": 2_315_223 / 500_000, "30555": 2_147_195 / 500_000}


def rightmost_peak_bin(counts: np.ndarray) -> int | None:
    """Same convention as `_apply_peak_removal_to_histogram`
    (histograms_pipeline.py:625-645): the peak is the RIGHTMOST bin
    holding the maximum bin content. Returns a 0-indexed bin index, or
    None if every bin is empty."""
    max_count = counts.max() if len(counts) else 0
    if max_count <= 0:
        return None
    nonzero_max_idx = np.where(counts == max_count)[0]
    return int(nonzero_max_idx[-1])  # rightmost = last index in ascending array


def analyze_variant(name: str, m_values: np.ndarray, extrap_events_scaled: float) -> dict:
    counts, _ = np.histogram(m_values, bins=FIXED_EDGES)
    n_total_events = int(counts.sum())

    peak_idx = rightmost_peak_bin(counts)
    nonempty_idx = np.where(counts > 0)[0]
    last_nonempty_idx = int(nonempty_idx[-1]) if len(nonempty_idx) else None

    result = {
        "n_events": n_total_events,
        "n_events_extrapolated_both_full_files": float(extrap_events_scaled),
    }

    if peak_idx is None or last_nonempty_idx is None:
        result.update({
            "peak_bin_lower_edge_gev": None, "n_bins_peak_to_last_nonempty": 0,
            "n_nonempty_bins_in_range": 0, "n_bins_with_fewer_than_10_events": 0,
            "n_events_at_or_after_peak": 0, "last_nonempty_bin_upper_edge_gev": None,
        })
        return result, counts, peak_idx, last_nonempty_idx

    n_bins_range = last_nonempty_idx - peak_idx + 1
    range_counts = counts[peak_idx:last_nonempty_idx + 1]
    n_nonempty_in_range = int(np.sum(range_counts > 0))
    n_sparse_in_range = int(np.sum((range_counts > 0) & (range_counts < 10)) + np.sum(range_counts == 0))
    # "fewer than 10 events" includes empty bins (0 < 10) as the task's own
    # plain-English framing ("nearly empty") implies -- reported separately
    # below too so empty vs. sparse-but-nonzero can be told apart.
    n_empty_in_range = int(np.sum(range_counts == 0))
    n_sparse_nonzero_in_range = int(np.sum((range_counts > 0) & (range_counts < 10)))
    n_events_at_or_after_peak = int(counts[peak_idx:].sum())

    result.update({
        "peak_bin_lower_edge_gev": float(FIXED_EDGES[peak_idx]),
        "n_bins_peak_to_last_nonempty": int(n_bins_range),
        "n_nonempty_bins_in_range": n_nonempty_in_range,
        "n_bins_with_fewer_than_10_events": n_sparse_in_range,
        "n_empty_bins_in_range": n_empty_in_range,
        "n_bins_with_1_to_9_events_in_range": n_sparse_nonzero_in_range,
        "n_events_at_or_after_peak": n_events_at_or_after_peak,
        "last_nonempty_bin_upper_edge_gev": float(FIXED_EDGES[last_nonempty_idx + 1]),
    })
    return result, counts, peak_idx, last_nonempty_idx


def plot_variant(name: str, counts: np.ndarray, peak_idx, last_nonempty_idx, n_events: int, fname: str):
    fig, ax = plt.subplots(figsize=(8, 5.5))
    centers = 0.5 * (FIXED_EDGES[:-1] + FIXED_EDGES[1:])
    x_max = FIXED_EDGES[last_nonempty_idx + 1] if last_nonempty_idx is not None else 500.0
    mask = FIXED_EDGES[:-1] < x_max
    ax.bar(centers[mask], counts[mask], width=FIXED_BIN_WIDTH_GEV, color="#3f7fa8",
           align="center", label=f"{name} (N={n_events})")
    ax.set_yscale("log")
    ax.set_ylim(bottom=0.5)
    if peak_idx is not None:
        ax.axvline(FIXED_EDGES[peak_idx], color="#c1272d", ls="--", lw=1.5,
                   label=f"peak bin lower edge: {FIXED_EDGES[peak_idx]:.0f} GeV")
    if last_nonempty_idx is not None:
        ax.axvline(FIXED_EDGES[last_nonempty_idx + 1], color="green", ls=":", lw=1.5,
                   label=f"last non-empty bin upper edge: {FIXED_EDGES[last_nonempty_idx + 1]:.0f} GeV")
    ax.set_xlabel(r"$m(\mu\mu j)$ [GeV] (fixed 10 GeV bins, 0-10 TeV shared convention)")
    ax.set_ylabel("Events / 10 GeV")
    ax.set_xlim(0, x_max)
    ax.set_title(name)
    ax.legend(fontsize=9)
    fig.tight_layout()
    fig.savefig(common.PLOTS_DIR / fname, dpi=150)
    plt.close(fig)
    print(f"wrote {fname}")


def main():
    golden = ValidatedRunsFilter(str(lna.GOLDEN_JSON))
    print(f"Golden JSON loaded: {golden.n_runs} runs, {golden.n_certified_lumisections} certified lumisections")

    per_record = {}
    for rec_id, info in lna.FILES.items():
        print(f"=== loading {rec_id} ({info['label']}) ===")
        f = common.open_root_https(info["uri"])
        tree = f["Events"]
        branches = ([f"Muon_{x}" for x in lna.READ_MUON_FIELDS]
                    + [f"Jet_{x}" for x in lna.READ_JET_FIELDS]
                    + ["run", "luminosityBlock"] + lna.DZ_PATHS)
        arr = tree.arrays(branches, entry_stop=lna.MAX_EVENTS, library="ak")
        obj = ak.zip({
            "Muon_pt": arr["Muon_pt"], "Muon_eta": arr["Muon_eta"], "Muon_phi": arr["Muon_phi"],
            "Muon_mass": arr["Muon_mass"], "Muon_charge": arr["Muon_charge"],
            "Muon_mediumId": arr["Muon_mediumId"], "Muon_pfRelIso04_all": arr["Muon_pfRelIso04_all"],
            "Jet_pt": arr["Jet_pt"], "Jet_eta": arr["Jet_eta"], "Jet_phi": arr["Jet_phi"],
            "Jet_mass": arr["Jet_mass"], "Jet_jetId": arr["Jet_jetId"], "Jet_puId": arr["Jet_puId"],
            "Jet_rawFactor": arr["Jet_rawFactor"], "Jet_muonIdx1": arr["Jet_muonIdx1"], "Jet_muonIdx2": arr["Jet_muonIdx2"],
            "run": arr["run"], "luminosityBlock": arr["luminosityBlock"],
        } | {p: arr[p] for p in lna.DZ_PATHS}, depth_limit=1)
        f.close()
        print(f"  loaded {len(obj)} events")

        ev_g, _ = apply_validated_runs_filter(obj, golden)
        trig = np.zeros(len(ev_g), dtype=bool)
        for p in lna.DZ_PATHS:
            trig = trig | ak.to_numpy(ev_g[p])
        ev_t = ev_g[trig]

        mu = lna.select_muon_pairs(ev_t, use_id_iso=True)
        jet = lna.select_leading_clean_jet(ev_t, mu, jet_pt_min=30.0, require_tight_id=True, clean_overlap=True)
        ok, m_mumuj = lna.combine_mumuj(mu, jet)

        per_record[rec_id] = {
            "ok": ok, "m_mumuj": m_mumuj, "m_mumu": mu["m_mumu"],
            "charge_product": mu["charge_product"],
        }

    def cat(field):
        return np.concatenate([per_record[r][field] for r in per_record])

    ok_all = cat("ok")
    m_mumuj_all = cat("m_mumuj")
    m_mumu_all = cat("m_mumu")
    charge_prod_all = cat("charge_product")
    valid = ok_all & ~np.isnan(m_mumuj_all)

    # per-record extrapolation of the FINAL selected-event fraction, applied
    # separately per record's own file (matching Section E's own factors),
    # then summed -- event-count extrapolation only, per this task's note.
    def extrap_events(mask_all):
        total = 0.0
        offset = 0
        for rec_id in per_record:
            n = len(per_record[rec_id]["ok"])
            sel = mask_all[offset:offset + n]
            total += float(np.sum(sel)) * EXTRAP_FACTOR[rec_id]
            offset += n
        return total

    variants = {
        "i_all_events": valid,
        "ii_outside_z_window_proxy_for_Z_collapsed": valid & ((m_mumu_all < Z_LO) | (m_mumu_all > Z_HI)),
    }
    variants["iii_outside_z_window_OS"] = variants["ii_outside_z_window_proxy_for_Z_collapsed"] & (charge_prod_all < 0)
    variants["iv_outside_z_window_SS"] = variants["ii_outside_z_window_proxy_for_Z_collapsed"] & (charge_prod_all > 0)

    labels = {
        "i_all_events": "(i) All events, full proposed selection",
        "ii_outside_z_window_proxy_for_Z_collapsed": "(ii) m(mumu) outside Z window -- proxy for Z-collapsed histogram",
        "iii_outside_z_window_OS": "(iii) (ii) restricted to opposite-sign pairs",
        "iv_outside_z_window_SS": "(iv) (ii) restricted to same-sign pairs",
    }

    out = {}
    for key, mask in variants.items():
        m_sel = m_mumuj_all[mask]
        extrap = extrap_events(mask)
        result, counts, peak_idx, last_idx = analyze_variant(labels[key], m_sel, extrap)
        out[key] = result
        plot_variant(labels[key], counts, peak_idx, last_idx, result["n_events"], f"bins_after_peak_{key}.png")
        print(f"[{key}] {result}")

    common.write_json(HERE / "07_bins_after_peak.json", out)
    print("\nDONE")


if __name__ == "__main__":
    main()
