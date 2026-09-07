#!/usr/bin/env python3
"""
Stage 2 of the H -> gamma gamma rediscovery exercise: full-scale (133/133
files) version of Stage 1's validated selection.

Reads a completed config.cms_higgs_diphoton_stage2.yaml PARSING run directory
and produces:

  * plots/diphoton_stage2_funnel.png  - per-record + combined event funnel
  * plots/diphoton_stage2_mass.png    - the full-scale diphoton mass histogram,
                                        BumpNet binning (10 GeV), overlaid on
                                        Stage 1's partial-scale histogram
  * histograms/diphoton_stage2_bumpnet.root - the same histogram, BumpNet name
  * diphoton_stage2_stats.json        - every number, per record and combined

Mass-calculation was attempted for real (config.cms_higgs_diphoton_stage2.yaml,
--tasks parsing,mass_calculating) but interrupted: at full scale the parsed
survivor sample (3,831,837 events, vs Stage 0/1's 683,213) produced far more
distinct raw jet/lepton-multiplicity final-state signatures than Stage 0/1's
partial run, and IMCalculator.group_by_final_state() enumerates every one of
them individually (chunk 0 alone passed 1,648 distinct final states in the
first ~12 minutes at a steady ~1.8/s with no sign of finishing) -- exactly the
final-state-capping/proliferation limitation Stage 0/1 already documented,
now confirmed at full scale to make the mass-calculation stage's own SQLite
output impractically slow to produce and, per that same documented limitation,
not a single trustworthy combined histogram even once produced. So, exactly as
in Stage 0/1, the diphoton mass here is computed directly from the complete,
already-safely-parsed photon collections (2 leading photons per event) --
this reproduces the parse-stage candidate count exactly and needs nothing
from the mass-calculation stage's output.

Usage (inside the pipeline's Docker image):
    python scripts/higgs_diphoton_stage2_report.py \
        --run-dir output/cms_higgs_diphoton_stage2_YYYYMMDD_HHMMSS \
        --log /path/to/diphoton_stage2_run.log \
        --out-dir reports/higgs_diphoton_stage2_fullscale \
        --stage1-hist-root <path to Stage 1's diphoton_stage1_bumpnet.root>
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

BUMPNET_MIN_BINS = 30
BUMPNET_MIN_ENTRIES = 100
BIN_WIDTH_GEV = 10.0
HIGGS_MASS_GEV = 125.0
HIST_MAX_GEV = 400.0

BUMPNET_NAME = "mass_g0g1_cat_0ex_0mx_0jx_2gx_0tx_0bx"

RECORD_LABELS = {"30521": "DoubleEG Run2016G", "30554": "DoubleEG Run2016H"}
RECORD_ORDER = ["30521", "30554"]
RECORD_NFILES_TOTAL = {"30521": 47, "30554": 86}
RECORD_NEVENTS_TOTAL = {"30521": 78_797_031, "30554": 85_388_673}

# Stage 1 (branch analysis/higgs-diphoton-stage1-idveto, commit 961a95c,
# reports/higgs_diphoton_stage1_idveto/diphoton_stage1_stats.json) -- quoted
# for the before/after comparison, not touched or re-derived.
STAGE1 = {
    "raw_events": {"30521": 18_962_247, "30554": 9_998_279, "combined": 28_960_526},
    "final_candidates": {"30521": 428_391, "30554": 254_822, "combined": 683_213},
    "diphoton_mass": {
        "n_pairs_in_hist_range": 680_177,
        "n_in_80_100_gev_Zwindow": 201_385,
        "n_in_115_135_gev": 48_719,
    },
    "bumpnet_histogram": {"n_bins": 40, "entries": 680_177},
}
# Stage 0 (branch analysis/higgs-diphoton-stage0-stats, commit 0d5fc60):
# kinematic-only (pT>20, |eta|<2.5, NO electronVeto/cutBased) retention rate,
# measured at 10 files/record. Stage 0 was never run at full scale, so this
# cannot be quoted as an absolute full-scale number -- only its RATE is
# extrapolated here, clearly labelled as such, for the 3-stage funnel.
STAGE0_KINEMATIC_ONLY_RETENTION_RATE = {
    "30521": 12_740_818 / 18_962_247,
    "30554": 7_178_538 / 9_998_279,
    "combined": 19_919_356 / 28_960_526,
}


def parse_log(log_path: Path) -> dict:
    import re

    text = log_path.read_text(errors="replace")
    records: dict[str, dict] = {}
    for m in re.finditer(
        r"Retention record_(\d+): ([\d,]+) / ([\d,]+) events kept", text
    ):
        rid = m.group(1)
        records.setdefault(rid, {})
        records[rid]["events_final"] = int(m.group(2).replace(",", ""))
        records[rid]["events_raw"] = int(m.group(3).replace(",", ""))
    totals = {}
    m = re.search(
        r"de-duplication: ([\d,]+) duplicate event\(s\) removed of ([\d,]+) seen", text
    )
    if m:
        totals["dedup_removed"] = int(m.group(1).replace(",", ""))
    m = re.search(r"Parsing complete: (\d+)/(\d+) files, (\d+) events", text)
    if m:
        totals["files_ok"] = int(m.group(1))
        totals["files_attempted"] = int(m.group(2))
        totals["events_total"] = int(m.group(3))
    return {"records": records, "totals": totals}


def load_diphoton_masses(run_dir: Path):
    import awkward as ak
    import uproot
    import vector

    vector.register_awkward()

    parsed = sorted((run_dir / "parsed_data").glob("*.root"))
    if not parsed:
        raise FileNotFoundError(f"no parsed .root chunks in {run_dir/'parsed_data'}")

    per_record: dict[str, int] = {}
    mass_parts: list[np.ndarray] = []
    branches = ["Photons_pt", "Photons_eta", "Photons_phi", "Photons_mass",
                "source_record"]

    for chunk in parsed:
        arr = uproot.open(chunk)["events"].arrays(branches, library="ak")
        pt = arr["Photons_pt"]
        order = ak.argsort(pt, axis=1, ascending=False)
        pt = pt[order][:, :2]
        eta = arr["Photons_eta"][order][:, :2]
        phi = arr["Photons_phi"][order][:, :2]
        mass = arr["Photons_mass"][order][:, :2]

        has2 = ak.num(pt, axis=1) == 2
        pt, eta, phi, mass = pt[has2], eta[has2], phi[has2], mass[has2]
        src = np.asarray(arr["source_record"][has2])

        vecs = vector.zip({"pt": pt, "eta": eta, "phi": phi, "mass": mass})
        diphoton = vecs[:, 0] + vecs[:, 1]
        m = np.asarray(ak.to_numpy(diphoton.mass), dtype=float)
        mass_parts.append(m)

        for rid in np.unique(src):
            per_record[str(int(rid))] = per_record.get(str(int(rid)), 0) + int(
                (src == rid).sum()
            )

    masses = np.concatenate(mass_parts) if mass_parts else np.array([], dtype=float)
    return masses, per_record


def build_hist(masses: np.ndarray):
    nbins = int(round(HIST_MAX_GEV / BIN_WIDTH_GEV))
    edges = np.linspace(0.0, HIST_MAX_GEV, nbins + 1)
    in_range = masses[(masses >= 0.0) & (masses <= HIST_MAX_GEV)]
    counts, _ = np.histogram(in_range, bins=edges)
    return edges, counts, int(masses.size), int((masses > HIST_MAX_GEV).sum())


def write_bumpnet_root(edges, counts, out_root: Path) -> str:
    import uproot

    out_root.parent.mkdir(parents=True, exist_ok=True)
    name = f"{BUMPNET_NAME}_width_{BIN_WIDTH_GEV}"
    with uproot.recreate(str(out_root)) as f:
        f[name] = (counts, edges)
    return name


def plot_mass_comparison(edges, counts_stage2, stage1_hist_root: Path | None,
                          out_png: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    centers = 0.5 * (edges[:-1] + edges[1:])
    n_in = int(counts_stage2.sum())
    nbins = len(counts_stage2)
    nonempty = int((counts_stage2 > 0).sum())
    bar_bins = "PASS" if nbins > BUMPNET_MIN_BINS else "FAIL"
    bar_ent = "PASS" if n_in >= BUMPNET_MIN_ENTRIES else "FAIL"

    counts_stage1 = None
    if stage1_hist_root is not None and stage1_hist_root.exists():
        import uproot
        with uproot.open(stage1_hist_root) as f:
            h = f[f.keys()[0]]
            counts_stage1 = h.values()

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5.4))

    # Left: Stage 1 (partial, scaled up to Stage 2's statistics for shape
    # comparison) vs Stage 2 (full scale, real counts), log scale.
    scale = (n_in / counts_stage1.sum()) if counts_stage1 is not None and counts_stage1.sum() else None
    if counts_stage1 is not None:
        ax1.bar(centers, counts_stage1 * scale, width=BIN_WIDTH_GEV * 0.95,
                color="#bbbbbb", edgecolor="#888888", linewidth=0.4,
                label=f"Stage 1 shape, scaled x{scale:.2f} to Stage 2 stats")
    ax1.bar(centers, counts_stage2, width=BIN_WIDTH_GEV * 0.65,
            color="#1b6fa8", edgecolor="#0d3a57", linewidth=0.4,
            label=f"Stage 2, full scale ({n_in:,} entries)")
    ax1.axvline(HIGGS_MASS_GEV, color="#cc3311", ls="--", lw=1.2,
                label=f"m = {HIGGS_MASS_GEV:.0f} GeV")
    ax1.axvspan(80, 100, color="#ddaa33", alpha=0.18, label="Z window 80-100")
    ax1.set_xlabel("diphoton invariant mass  [GeV]")
    ax1.set_ylabel(f"pairs / {BIN_WIDTH_GEV:.0f} GeV")
    ax1.set_xlim(0, edges[-1])
    ax1.set_yscale("log")
    ax1.set_title("Stage 2 vs Stage 1 shape (log scale)", fontsize=9)
    ax1.legend(fontsize=7.5)

    # Right: Stage 2 alone, linear, so its own shape near 125 GeV is visible
    # at its own scale.
    ax2.bar(centers, counts_stage2, width=BIN_WIDTH_GEV * 0.95,
            color="#1b6fa8", edgecolor="#0d3a57", linewidth=0.4)
    ax2.axvline(HIGGS_MASS_GEV, color="#cc3311", ls="--", lw=1.2,
                label=f"m = {HIGGS_MASS_GEV:.0f} GeV")
    ax2.axvspan(80, 100, color="#ddaa33", alpha=0.18, label="Z window 80-100")
    ax2.set_xlabel("diphoton invariant mass  [GeV]")
    ax2.set_ylabel(f"pairs / {BIN_WIDTH_GEV:.0f} GeV")
    ax2.set_xlim(0, edges[-1])
    ax2.set_title("Stage 2 alone (linear scale)", fontsize=9)
    ax2.legend(fontsize=8)

    fig.suptitle(
        "CMS Open Data DoubleEG, FULL SCALE (133/133 files) - diphoton mass, "
        "Stage 2 (electronVeto + cutBased>=1)\n"
        f"{n_in:,} entries in [0, {edges[-1]:.0f}] GeV over {nbins} bins "
        f"({nonempty} filled)  |  BumpNet bar: >{BUMPNET_MIN_BINS} bins = "
        f"{bar_bins}, >={BUMPNET_MIN_ENTRIES} entries = {bar_ent}  |  NOT a "
        "significance claim - visual only",
        fontsize=8.5,
    )
    fig.tight_layout()
    fig.savefig(out_png, dpi=130)
    plt.close(fig)


def plot_funnel(records: dict, out_png: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    labels, raw_v, kin_v, final_v = [], [], [], []
    for rid in RECORD_ORDER:
        r = records.get(rid, {})
        labels.append(RECORD_LABELS[rid].replace(" Run", "\nRun"))
        raw = r.get("events_raw", 0)
        raw_v.append(raw)
        kin_v.append(raw * STAGE0_KINEMATIC_ONLY_RETENTION_RATE[rid])
        final_v.append(r.get("events_final", 0))
    labels.append("COMBINED")
    raw_v.append(sum(raw_v))
    kin_v.append(sum(kin_v))
    final_v.append(sum(final_v))

    x = np.arange(len(labels))
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

    ax1.bar(x, raw_v, color="#999999")
    ax1.set_yscale("log")
    ax1.set_title("Raw events processed, full scale (log scale)")
    ax1.set_xticks(x)
    ax1.set_xticklabels(labels, fontsize=8)
    for xi, v in zip(x, raw_v):
        ax1.text(xi, v, f"{v:,}", ha="center", va="bottom", fontsize=7.5)

    w = 0.35
    ax2.bar(x - w / 2, kin_v, w, color="#4477aa",
            label=">=2 photons, pT/eta only\n(Stage 0 RATE extrapolated, not re-measured)")
    ax2.bar(x + w / 2, final_v, w, color="#c1272d",
            label=">=2 photons + electronVeto + cutBased>=1\n(Stage 2, real full-scale count)")
    ax2.set_yscale("log")
    ax2.set_title("Candidate funnel, full scale (log scale)")
    ax2.set_xticks(x)
    ax2.set_xticklabels(labels, fontsize=8)
    for xi, v in zip(x, kin_v):
        ax2.text(xi - w / 2, v, f"{v:,.0f}", ha="center", va="bottom", fontsize=7)
    for xi, v in zip(x, final_v):
        ax2.text(xi + w / 2, v, f"{v:,}", ha="center", va="bottom", fontsize=7)
    ax2.legend(fontsize=7, loc="upper left")
    ax2.set_ylim(min(final_v) * 0.5, max(kin_v) * 3)

    fig.suptitle(
        "H -> gamma gamma  Stage 2 event funnel  (DoubleEG, FULL SCALE, 133/133 files)",
        fontsize=11)
    fig.tight_layout()
    fig.savefig(out_png, dpi=130)
    plt.close(fig)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True, type=Path)
    ap.add_argument("--log", required=True, type=Path)
    ap.add_argument("--out-dir", required=True, type=Path)
    ap.add_argument("--stage1-hist-root", type=Path, default=None)
    args = ap.parse_args()

    out = args.out_dir
    (out / "plots").mkdir(parents=True, exist_ok=True)
    (out / "histograms").mkdir(parents=True, exist_ok=True)

    scraped = parse_log(args.log)
    records, totals = scraped["records"], scraped["totals"]

    cache = args.run_dir / "diphoton_masses_stage2.npz"
    if cache.exists():
        z = np.load(cache, allow_pickle=True)
        masses = z["masses"]
        pairs_per_record = {str(k): int(v) for k, v in z["pairs_per_record"].item().items()}
        print(f"loaded {masses.size:,} masses from cache {cache}")
    else:
        masses, pairs_per_record = load_diphoton_masses(args.run_dir)
        np.savez_compressed(
            cache, masses=masses,
            pairs_per_record=np.array(pairs_per_record, dtype=object),
        )

    edges, counts, n_total, n_overflow = build_hist(masses)
    hist_name = write_bumpnet_root(
        edges, counts, out / "histograms" / "diphoton_stage2_bumpnet.root"
    )
    plot_mass_comparison(edges, counts, args.stage1_hist_root,
                          out / "plots" / "diphoton_stage2_mass.png")
    plot_funnel(records, out / "plots" / "diphoton_stage2_funnel.png")

    n_in = int(counts.sum())
    nbins = len(counts)
    n_zwindow = int(((masses >= 80) & (masses <= 100)).sum())
    n_115_135 = int(((masses >= 115) & (masses <= 135)).sum())

    def _frac(a, b):
        return (a / b) if b else None

    stats = {
        "run_dir": str(args.run_dir),
        "config": "config.cms_higgs_diphoton_stage2.yaml",
        "scale": "FULL: 133/133 files (47 + 86)",
        "records": {
            rid: {
                "label": RECORD_LABELS[rid],
                "files_total": RECORD_NFILES_TOTAL[rid],
                "files_processed": RECORD_NFILES_TOTAL[rid],
                "events_full_dataset": RECORD_NEVENTS_TOTAL[rid],
                "events_raw_processed": records.get(rid, {}).get("events_raw"),
                "events_final_candidates": records.get(rid, {}).get("events_final"),
                "diphoton_pairs_formed": pairs_per_record.get(rid),
                "retention_pct": _frac(
                    records.get(rid, {}).get("events_final", 0),
                    records.get(rid, {}).get("events_raw", 0),
                ),
            }
            for rid in RECORD_ORDER
        },
        "combined": {
            "events_raw_processed": sum(
                records.get(r, {}).get("events_raw", 0) for r in RECORD_ORDER
            ),
            "events_final_candidates": sum(
                records.get(r, {}).get("events_final", 0) for r in RECORD_ORDER
            ),
            "diphoton_pairs_formed": int(masses.size),
            "dedup_removed": totals.get("dedup_removed"),
        },
        "vs_stage1_partial_scale": {
            "raw_events": {"stage1": STAGE1["raw_events"]["combined"],
                            "stage2": sum(records.get(r, {}).get("events_raw", 0) for r in RECORD_ORDER),
                            "scale_factor": _frac(
                                sum(records.get(r, {}).get("events_raw", 0) for r in RECORD_ORDER),
                                STAGE1["raw_events"]["combined"])},
            "final_candidates": {"stage1": STAGE1["final_candidates"]["combined"],
                                   "stage2": int(masses.size),
                                   "scale_factor": _frac(int(masses.size), STAGE1["final_candidates"]["combined"])},
        },
        "diphoton_mass": {
            "n_pairs_total": int(masses.size),
            "n_pairs_in_hist_range": n_in,
            "n_pairs_above_%.0f_gev" % HIST_MAX_GEV: n_overflow,
            "min_gev": float(masses.min()) if masses.size else None,
            "max_gev": float(masses.max()) if masses.size else None,
            "median_gev": float(np.median(masses)) if masses.size else None,
            "mean_gev": float(np.mean(masses)) if masses.size else None,
            "n_in_80_100_gev_Zwindow": n_zwindow,
            "n_in_115_135_gev": n_115_135,
            "pairs_per_record_direct": pairs_per_record,
        },
        "before_after_vs_stage1": {
            "n_pairs_total": {"stage1": STAGE1["diphoton_mass"]["n_pairs_in_hist_range"],
                               "stage2": n_in,
                               "ratio": _frac(n_in, STAGE1["diphoton_mass"]["n_pairs_in_hist_range"])},
            "n_in_80_100_gev_Zwindow": {"stage1": STAGE1["diphoton_mass"]["n_in_80_100_gev_Zwindow"],
                                          "stage2": n_zwindow,
                                          "ratio": _frac(n_zwindow, STAGE1["diphoton_mass"]["n_in_80_100_gev_Zwindow"])},
            "n_in_115_135_gev": {"stage1": STAGE1["diphoton_mass"]["n_in_115_135_gev"],
                                   "stage2": n_115_135,
                                   "ratio": _frac(n_115_135, STAGE1["diphoton_mass"]["n_in_115_135_gev"])},
        },
        "bumpnet_histogram": {
            "root_file": str(out / "histograms" / "diphoton_stage2_bumpnet.root"),
            "hist_name": hist_name,
            "bin_width_gev": BIN_WIDTH_GEV,
            "range_gev": [0.0, HIST_MAX_GEV],
            "n_bins": nbins,
            "n_nonempty_bins": int((counts > 0).sum()),
            "entries": n_in,
            "meets_bin_bar": nbins > BUMPNET_MIN_BINS,
            "meets_entry_bar": n_in >= BUMPNET_MIN_ENTRIES,
            "min_bins_required": BUMPNET_MIN_BINS,
            "min_entries_required": BUMPNET_MIN_ENTRIES,
        },
        "mass_calculation_stage": {
            "attempted": True,
            "outcome": "interrupted -- impractically slow at full scale, same "
                       "final-state-proliferation limitation Stage 0/1 already "
                       "documented, now confirmed at full scale: chunk 0 alone "
                       "(2,412,355 events) had already enumerated 1,648 distinct "
                       "raw final-state signatures after ~12 minutes at a "
                       "steady ~1.8/s with no sign of finishing",
            "diphoton_mass_source": "computed directly from parsed photon "
                                      "collections instead, same method as "
                                      "Stage 0/1",
        },
        "files_ok": totals.get("files_ok"),
        "files_attempted": totals.get("files_attempted"),
    }

    (out / "diphoton_stage2_stats.json").write_text(json.dumps(stats, indent=2))
    print(json.dumps(stats, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
