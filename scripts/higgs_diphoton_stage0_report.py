#!/usr/bin/env python3
"""
Stage 0 statistics check for H -> gamma gamma (diphoton).

Reads a completed `config.cms_higgs_diphoton_stage0.yaml` run directory and
produces:

  * plots/diphoton_stage0_funnel.png  - per-record + combined event funnel
                                        (raw events -> events with >=2 photons
                                        passing pT>20 GeV, |eta|<2.5)
  * plots/diphoton_stage0_mass.png    - the diphoton invariant-mass histogram,
                                        BumpNet binning (10 GeV), raw candidates
  * histograms/diphoton_stage0_bumpnet.root - the same histogram in a ROOT file,
                                        BumpNet name `mass_g0g1_cat_...`
  * diphoton_stage0_stats.json        - every number, per record and combined

Per-record event counts come from the pipeline log (`Retention record_<id>:
<kept> / <raw> events kept` -- with no de-dup effect here, <kept> is exactly the
count of events with >=2 photons passing the kinematic cuts). The diphoton mass
array is read straight from the mass-calculation SQLite shard.

Usage (inside the pipeline's Docker image):
    python scripts/higgs_diphoton_stage0_report.py \
        --run-dir output/cms_higgs_diphoton_stage0_YYYYMMDD_HHMMSS \
        --log /path/to/diphoton_run.log \
        --out-dir reports/higgs_diphoton_stage0
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

# --- BumpNet usability bar --------------------------------------------------
BUMPNET_MIN_BINS = 30
BUMPNET_MIN_ENTRIES = 100
BIN_WIDTH_GEV = 10.0
HIGGS_MASS_GEV = 125.0
HIST_MAX_GEV = 400.0  # fixed upper edge so the bin grid is stable run-to-run

# BumpNet histogram name for the one channel this run produces:
#   final state 0e_0m_0j_2g_0t_0b  +  IM combo g0g1
BUMPNET_NAME = "mass_g0g1_cat_0ex_0mx_0jx_2gx_0tx_0bx"

RECORD_LABELS = {
    "30521": "DoubleEG Run2016G",
    "30554": "DoubleEG Run2016H",
}
RECORD_ORDER = ["30521", "30554"]
RECORD_NFILES_TOTAL = {"30521": 47, "30554": 86}
RECORD_NEVENTS_TOTAL = {"30521": 78_797_031, "30554": 85_388_673}


def parse_log(log_path: Path) -> dict:
    import re

    text = log_path.read_text(errors="replace")
    records: dict[str, dict] = {}

    # "Limiting record_30521 to 10 files (was 47, max_files_to_process=10)"
    for m in re.finditer(r"Limiting record_(\d+) to (\d+) files \(was (\d+)", text):
        rid = m.group(1)
        records.setdefault(rid, {})
        records[rid]["files_processed"] = int(m.group(2))
        records[rid]["files_total"] = int(m.group(3))

    # "Fetched 47 files from record 30521"
    for m in re.finditer(r"Fetched (\d+) files from record (\d+)", text):
        rid = m.group(2)
        records.setdefault(rid, {}).setdefault("files_total", int(m.group(1)))
        records[rid].setdefault("files_processed", int(m.group(1)))

    # "Retention record_30521: 12345 / 678901 events kept (1.8%)"
    for m in re.finditer(
        r"Retention record_(\d+): ([\d,]+) / ([\d,]+) events kept", text
    ):
        rid = m.group(1)
        records.setdefault(rid, {})
        records[rid]["events_ge2photon"] = int(m.group(2).replace(",", ""))
        records[rid]["events_raw"] = int(m.group(3).replace(",", ""))

    totals = {}
    m = re.search(
        r"de-duplication: ([\d,]+) duplicate event\(s\) removed of ([\d,]+) seen",
        text,
    )
    if m:
        totals["dedup_removed"] = int(m.group(1).replace(",", ""))
        totals["dedup_seen"] = int(m.group(2).replace(",", ""))
    m = re.search(r"Parsing complete: (\d+)/(\d+) files", text)
    if m:
        totals["files_ok"] = int(m.group(1))
        totals["files_attempted"] = int(m.group(2))
    return {"records": records, "totals": totals}


def load_diphoton_masses(run_dir: Path):
    """
    Diphoton invariant mass of the 2 leading (highest-pT) photons in every parsed
    event, read straight from the parsing-stage output.

    We deliberately do NOT use the mass-calculation stage's SQLite output here:
    that stage groups events by exact final state and its final-state label is
    capped at 4 objects/type (`IMCalculator._limit_particles_in_fs`). With a
    kinematic cut on photons only, real DoubleEG events keep uncut jets/leptons
    and many have >4 of some type, so the capping both drops those events and
    re-counts lower-multiplicity ones -- an unreliable entry count for a pure
    statistics check. The per-event selection (>=2 photons, pT>20, |eta|<2.5)
    was already applied at parse time, so every event in these chunks is a
    diphoton candidate; here we just form the leading-pair mass, once per event.
    """
    import awkward as ak
    import vector

    vector.register_awkward()

    parsed = sorted((run_dir / "parsed_data").glob("*.root"))
    if not parsed:
        raise FileNotFoundError(f"no parsed .root chunks in {run_dir/'parsed_data'}")

    import uproot

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

        # keep only events that really have >=2 photons in the collection
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


def plot_mass(edges, counts, n_total, n_overflow, out_png: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    centers = 0.5 * (edges[:-1] + edges[1:])
    n_in = int(counts.sum())
    nbins = len(counts)
    nonempty = int((counts > 0).sum())
    bar_bins = "PASS" if nbins > BUMPNET_MIN_BINS else "FAIL"
    bar_ent = "PASS" if n_in >= BUMPNET_MIN_ENTRIES else "FAIL"

    fig, axes = plt.subplots(1, 2, figsize=(13, 5.2))
    for ax, logy in zip(axes, (False, True)):
        ax.bar(centers, counts, width=BIN_WIDTH_GEV * 0.95, color="#4477aa",
               edgecolor="#22435f", linewidth=0.4)
        ax.axvline(HIGGS_MASS_GEV, color="#cc3311", ls="--", lw=1.2,
                   label=f"m = {HIGGS_MASS_GEV:.0f} GeV")
        ax.axvspan(80, 100, color="#ddaa33", alpha=0.18, label="Z window 80-100")
        ax.set_xlabel("diphoton invariant mass  [GeV]")
        ax.set_ylabel(f"pairs / {BIN_WIDTH_GEV:.0f} GeV")
        ax.set_xlim(0, edges[-1])
        if logy:
            ax.set_yscale("log")
            ax.set_title("log scale", fontsize=9)
        else:
            ax.set_title("linear scale", fontsize=9)
        ax.legend(fontsize=8)

    fig.suptitle(
        "CMS Open Data DoubleEG  -  raw diphoton candidates "
        "(2 leading photons, pT>20 GeV, |eta|<2.5, NO photon ID / isolation / "
        "pixel-seed veto)\n"
        f"{n_in:,} entries in [0, {edges[-1]:.0f}] GeV over {nbins} bins "
        f"({nonempty} filled)  |  BumpNet bar: >{BUMPNET_MIN_BINS} bins = "
        f"{bar_bins}, >={BUMPNET_MIN_ENTRIES} entries = {bar_ent}  |  the "
        f"~90 GeV peak is Z->ee (electrons rebuilt as photons), NOT signal",
        fontsize=8.7,
    )
    fig.tight_layout()
    fig.savefig(out_png, dpi=130)
    plt.close(fig)


def plot_funnel(records: dict, out_png: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    labels, raw_v, ge2_v = [], [], []
    for rid in RECORD_ORDER:
        r = records.get(rid, {})
        labels.append(RECORD_LABELS[rid].replace(" Run", "\nRun"))
        raw_v.append(r.get("events_raw", 0))
        ge2_v.append(r.get("events_ge2photon", 0))
    labels.append("COMBINED")
    raw_v.append(sum(raw_v))
    ge2_v.append(sum(ge2_v))

    x = np.arange(len(labels))
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.8))

    ax1.bar(x, raw_v, color="#999999")
    ax1.set_yscale("log")
    ax1.set_title("Raw events processed (log scale)")
    ax1.set_xticks(x)
    ax1.set_xticklabels(labels, fontsize=8)
    for xi, v in zip(x, raw_v):
        ax1.text(xi, v, f"{v:,}", ha="center", va="bottom", fontsize=7.5)

    ax2.bar(x, ge2_v, color="#4477aa")
    ax2.set_title(">=2 photons, pT>20 GeV, |eta|<2.5  (diphoton candidates)")
    ax2.set_xticks(x)
    ax2.set_xticklabels(labels, fontsize=8)
    for xi, v, r in zip(x, ge2_v, raw_v):
        pct = f"\n({100.0 * v / r:.0f}% of raw)" if r else ""
        ax2.text(xi, v, f"{v:,}{pct}", ha="center", va="bottom", fontsize=7.5)
    ax2.set_ylim(0, max(ge2_v) * 1.18)

    fig.suptitle("H -> gamma gamma  Stage-0 event funnel  (DoubleEG, partial scale)",
                 fontsize=11)
    fig.tight_layout()
    fig.savefig(out_png, dpi=130)
    plt.close(fig)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True, type=Path)
    ap.add_argument("--log", required=True, type=Path)
    ap.add_argument("--out-dir", required=True, type=Path)
    args = ap.parse_args()

    out = args.out_dir
    (out / "plots").mkdir(parents=True, exist_ok=True)
    (out / "histograms").mkdir(parents=True, exist_ok=True)

    scraped = parse_log(args.log)
    records, totals = scraped["records"], scraped["totals"]

    # cache the (large) mass array next to the run output, NOT under reports/
    cache = args.run_dir / "diphoton_masses.npz"
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
        edges, counts, out / "histograms" / "diphoton_stage0_bumpnet.root"
    )
    plot_mass(edges, counts, n_total, n_overflow,
              out / "plots" / "diphoton_stage0_mass.png")
    plot_funnel(records, out / "plots" / "diphoton_stage0_funnel.png")

    n_in = int(counts.sum())
    nbins = len(counts)

    def _frac(a, b):
        return (a / b) if b else None

    stats = {
        "run_dir": str(args.run_dir),
        "config": "config.cms_higgs_diphoton_stage0.yaml",
        "records": {
            rid: {
                "label": RECORD_LABELS[rid],
                "files_total": RECORD_NFILES_TOTAL[rid],
                "files_processed": records.get(rid, {}).get("files_processed"),
                "files_fraction": _frac(
                    records.get(rid, {}).get("files_processed", 0),
                    RECORD_NFILES_TOTAL[rid],
                ),
                "events_full_dataset": RECORD_NEVENTS_TOTAL[rid],
                "events_raw_processed": records.get(rid, {}).get("events_raw"),
                "events_fraction": _frac(
                    records.get(rid, {}).get("events_raw", 0),
                    RECORD_NEVENTS_TOTAL[rid],
                ),
                "events_ge2photon": records.get(rid, {}).get("events_ge2photon"),
                "diphoton_pairs_formed": pairs_per_record.get(rid),
            }
            for rid in RECORD_ORDER
        },
        "combined": {
            "events_raw_processed": sum(
                records.get(r, {}).get("events_raw", 0) for r in RECORD_ORDER
            ),
            "events_ge2photon": sum(
                records.get(r, {}).get("events_ge2photon", 0) for r in RECORD_ORDER
            ),
            "diphoton_pairs_formed": int(masses.size),
            "dedup_removed": totals.get("dedup_removed"),
        },
        "diphoton_mass": {
            "n_pairs_total": int(masses.size),
            "n_pairs_in_hist_range": n_in,
            "n_pairs_above_%.0f_gev" % HIST_MAX_GEV: n_overflow,
            "min_gev": float(masses.min()) if masses.size else None,
            "max_gev": float(masses.max()) if masses.size else None,
            "median_gev": float(np.median(masses)) if masses.size else None,
            "mean_gev": float(np.mean(masses)) if masses.size else None,
            "n_in_80_100_gev_Zwindow": int(((masses >= 80) & (masses <= 100)).sum()),
            "n_in_115_135_gev": int(((masses >= 115) & (masses <= 135)).sum()),
            "pairs_per_record_direct": pairs_per_record,
        },
        "bumpnet_histogram": {
            "root_file": str(out / "histograms" / "diphoton_stage0_bumpnet.root"),
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
        "files_ok": totals.get("files_ok"),
        "files_attempted": totals.get("files_attempted"),
    }

    (out / "diphoton_stage0_stats.json").write_text(json.dumps(stats, indent=2))
    print(json.dumps(stats, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
