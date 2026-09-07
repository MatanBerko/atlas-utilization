#!/usr/bin/env python3
"""
Stage 1 of the H -> gamma gamma rediscovery exercise: photon ID + electron
veto on top of Stage 0's basic pT/eta acceptance cut.

Reads a completed `config.cms_higgs_diphoton_stage1.yaml` run directory and
produces:

  * plots/diphoton_stage1_funnel.png  - 3-stage per-record + combined funnel:
                                        raw events -> >=2 photons passing
                                        kinematic (pT/eta) cuts [Stage 0 number,
                                        quoted as a consistency check] ->
                                        >=2 photons ALSO passing
                                        electronVeto+cutBased [this run]
  * plots/diphoton_stage1_mass.png    - the new diphoton mass histogram,
                                        BumpNet binning (10 GeV), with the
                                        Stage 0 histogram overlaid for a direct
                                        before/after comparison
  * histograms/diphoton_stage1_bumpnet.root - the new histogram, BumpNet name
                                        `mass_g0g1_cat_...`
  * diphoton_stage1_stats.json        - every number, per record and combined,
                                        plus the Stage 0 comparison numbers

Stage 0's numbers (branch analysis/higgs-diphoton-stage0-stats, commit
0d5fc60, reports/higgs_diphoton_stage0/diphoton_stage0_stats.json) are quoted
here as fixed reference constants -- that branch is not touched or read from
disk by this script. The "raw events processed" figures from THIS run are
compared against them live, as the actual consistency check the task asked
for (same records + same 10 files/record => same files read => same raw event
counts), and the match/mismatch is reported plainly rather than assumed.

Usage (inside the pipeline's Docker image):
    python scripts/higgs_diphoton_stage1_report.py \
        --run-dir output/cms_higgs_diphoton_stage1_YYYYMMDD_HHMMSS \
        --log /path/to/diphoton_stage1_run.log \
        --out-dir reports/higgs_diphoton_stage1_idveto
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
HIST_MAX_GEV = 400.0  # same fixed upper edge as Stage 0, for a like-for-like plot

BUMPNET_NAME = "mass_g0g1_cat_0ex_0mx_0jx_2gx_0tx_0bx"

RECORD_LABELS = {
    "30521": "DoubleEG Run2016G",
    "30554": "DoubleEG Run2016H",
}
RECORD_ORDER = ["30521", "30554"]
RECORD_NFILES_TOTAL = {"30521": 47, "30554": 86}
RECORD_NEVENTS_TOTAL = {"30521": 78_797_031, "30554": 85_388_673}

# --- Stage 0 reference numbers (branch analysis/higgs-diphoton-stage0-stats,
# commit 0d5fc60, reports/higgs_diphoton_stage0/diphoton_stage0_stats.json) --
# Quoted, not recomputed; that branch is not touched by this script.
STAGE0 = {
    "raw_events": {"30521": 18_962_247, "30554": 9_998_279, "combined": 28_960_526},
    "ge2photon_kinematic_only": {
        "30521": 12_740_818, "30554": 7_178_538, "combined": 19_919_356,
    },
    "diphoton_mass": {
        "n_pairs_total": 19_919_356,
        "n_pairs_in_hist_range": 19_447_027,
        "n_in_80_100_gev_Zwindow": 4_735_893,
        "n_in_115_135_gev": 1_844_952,
    },
    "bumpnet_histogram": {"n_bins": 40, "entries": 19_447_027},
}


def parse_log(log_path: Path) -> dict:
    import re

    text = log_path.read_text(errors="replace")
    records: dict[str, dict] = {}

    for m in re.finditer(r"Limiting record_(\d+) to (\d+) files \(was (\d+)", text):
        rid = m.group(1)
        records.setdefault(rid, {})
        records[rid]["files_processed"] = int(m.group(2))
        records[rid]["files_total"] = int(m.group(3))

    for m in re.finditer(r"Fetched (\d+) files from record (\d+)", text):
        rid = m.group(2)
        records.setdefault(rid, {}).setdefault("files_total", int(m.group(1)))
        records[rid].setdefault("files_processed", int(m.group(1)))

    # "Retention record_30521: 12345 / 678901 events kept (1.8%)" -- with the
    # Stage 1 config, <kept> is events with >=2 photons passing BOTH the
    # kinematic (pT/eta) cuts AND the new electronVeto+cutBased ID cuts.
    for m in re.finditer(
        r"Retention record_(\d+): ([\d,]+) / ([\d,]+) events kept", text
    ):
        rid = m.group(1)
        records.setdefault(rid, {})
        records[rid]["events_ge2photon_id"] = int(m.group(2).replace(",", ""))
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
    Diphoton invariant mass of the 2 leading (highest-pT) photons in every
    parsed event, read straight from the parsing-stage output -- same approach
    as Stage 0 and for the same reason: the mass-calculation stage's
    final-state label is capped at 4 objects/type
    (`IMCalculator._limit_particles_in_fs`), and with a kinematic cut on
    photons only, real DoubleEG events keep uncut jets/leptons with >4 of some
    type, making that stage's entry count unreliable for a pure statistics
    check. The per-event selection (>=2 photons passing pT/eta + ID + veto)
    was already applied at parse time, so every event in these chunks is a
    Stage 1 diphoton candidate; here we just form the leading-pair mass, once
    per event.
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


def plot_mass_comparison(edges, counts_stage1, stage0_hist_root: Path | None,
                          n_total, n_overflow, out_png: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    centers = 0.5 * (edges[:-1] + edges[1:])
    n_in = int(counts_stage1.sum())
    nbins = len(counts_stage1)
    nonempty = int((counts_stage1 > 0).sum())
    bar_bins = "PASS" if nbins > BUMPNET_MIN_BINS else "FAIL"
    bar_ent = "PASS" if n_in >= BUMPNET_MIN_ENTRIES else "FAIL"

    counts_stage0 = None
    if stage0_hist_root is not None and stage0_hist_root.exists():
        import uproot
        with uproot.open(stage0_hist_root) as f:
            h = f[f.keys()[0]]
            counts_stage0 = h.values()

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5.4))

    # Left: Stage 0 vs Stage 1 overlay, log-y (the two differ by ~30x, a linear
    # scale would make Stage 1 invisible next to Stage 0).
    if counts_stage0 is not None:
        ax1.bar(centers, counts_stage0, width=BIN_WIDTH_GEV * 0.95,
                color="#bbbbbb", edgecolor="#888888", linewidth=0.4,
                label="Stage 0 (no ID, for reference)")
    ax1.bar(centers, counts_stage1, width=BIN_WIDTH_GEV * 0.7,
            color="#c1272d", edgecolor="#6e1414", linewidth=0.4,
            label="Stage 1 (electronVeto + cutBased>=1)")
    ax1.axvline(HIGGS_MASS_GEV, color="#1b3a5c", ls="--", lw=1.2,
                label=f"m = {HIGGS_MASS_GEV:.0f} GeV")
    ax1.axvspan(80, 100, color="#ddaa33", alpha=0.18, label="Z window 80-100")
    ax1.set_xlabel("diphoton invariant mass  [GeV]")
    ax1.set_ylabel(f"pairs / {BIN_WIDTH_GEV:.0f} GeV")
    ax1.set_xlim(0, edges[-1])
    ax1.set_yscale("log")
    ax1.set_title("Stage 0 vs Stage 1 (log scale)", fontsize=9)
    ax1.legend(fontsize=7.5)

    # Right: Stage 1 ALONE, linear scale, so its own shape is visible at its
    # own scale (obscured by Stage 0 in the left panel).
    ax2.bar(centers, counts_stage1, width=BIN_WIDTH_GEV * 0.95,
            color="#c1272d", edgecolor="#6e1414", linewidth=0.4,
            label="Stage 1 (electronVeto + cutBased>=1)")
    ax2.axvline(HIGGS_MASS_GEV, color="#1b3a5c", ls="--", lw=1.2,
                label=f"m = {HIGGS_MASS_GEV:.0f} GeV")
    ax2.axvspan(80, 100, color="#ddaa33", alpha=0.18, label="Z window 80-100")
    ax2.set_xlabel("diphoton invariant mass  [GeV]")
    ax2.set_ylabel(f"pairs / {BIN_WIDTH_GEV:.0f} GeV")
    ax2.set_xlim(0, edges[-1])
    ax2.set_title("Stage 1 alone (linear scale)", fontsize=9)
    ax2.legend(fontsize=7.5)

    fig.suptitle(
        "CMS Open Data DoubleEG  -  diphoton mass, Stage 1 (electronVeto + "
        "cutBased>=1) vs Stage 0 (no ID)\n"
        f"Stage 1: {n_in:,} entries in [0, {edges[-1]:.0f}] GeV over {nbins} "
        f"bins ({nonempty} filled)  |  BumpNet bar: >{BUMPNET_MIN_BINS} bins = "
        f"{bar_bins}, >={BUMPNET_MIN_ENTRIES} entries = {bar_ent}",
        fontsize=8.7,
    )
    fig.tight_layout()
    fig.savefig(out_png, dpi=130)
    plt.close(fig)


def plot_funnel3(records: dict, out_png: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    labels, raw_v, kin_v, id_v = [], [], [], []
    for rid in RECORD_ORDER:
        r = records.get(rid, {})
        labels.append(RECORD_LABELS[rid].replace(" Run", "\nRun"))
        raw_v.append(r.get("events_raw", 0))
        kin_v.append(STAGE0["ge2photon_kinematic_only"][rid])
        id_v.append(r.get("events_ge2photon_id", 0))
    labels.append("COMBINED")
    raw_v.append(sum(raw_v))
    kin_v.append(sum(kin_v))
    id_v.append(sum(id_v))

    x = np.arange(len(labels))
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

    ax1.bar(x, raw_v, color="#999999")
    ax1.set_yscale("log")
    ax1.set_title("Raw events processed (log scale)")
    ax1.set_xticks(x)
    ax1.set_xticklabels(labels, fontsize=8)
    for xi, v in zip(x, raw_v):
        ax1.text(xi, v, f"{v:,}", ha="center", va="bottom", fontsize=7.5)

    w = 0.38
    ax2.bar(x - w / 2, kin_v, w, color="#4477aa",
            label=">=2 photons, pT/eta only (Stage 0 number)")
    ax2.bar(x + w / 2, id_v, w, color="#c1272d",
            label=">=2 photons, + electronVeto + cutBased>=1 (Stage 1)")
    ax2.set_title("Candidate funnel: kinematic-only vs + ID/veto")
    ax2.set_xticks(x)
    ax2.set_xticklabels(labels, fontsize=8)
    for xi, v in zip(x, kin_v):
        ax2.text(xi - w / 2, v, f"{v:,}", ha="center", va="bottom", fontsize=7)
    for xi, v, k in zip(x, id_v, kin_v):
        pct = f"\n({100.0*v/k:.1f}% of kin.)" if k else ""
        ax2.text(xi + w / 2, v, f"{v:,}{pct}", ha="center", va="bottom", fontsize=7)
    ax2.legend(fontsize=7.5)
    ax2.set_ylim(0, max(kin_v) * 1.25)

    fig.suptitle(
        "H -> gamma gamma  Stage 1 event funnel  (DoubleEG, same 10 files/record as Stage 0)",
        fontsize=11)
    fig.tight_layout()
    fig.savefig(out_png, dpi=130)
    plt.close(fig)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True, type=Path)
    ap.add_argument("--log", required=True, type=Path)
    ap.add_argument("--out-dir", required=True, type=Path)
    ap.add_argument("--stage0-hist-root", type=Path, default=None,
                    help="optional: path to Stage 0's diphoton_stage0_bumpnet.root, "
                         "for the overlay comparison plot")
    args = ap.parse_args()

    out = args.out_dir
    (out / "plots").mkdir(parents=True, exist_ok=True)
    (out / "histograms").mkdir(parents=True, exist_ok=True)

    scraped = parse_log(args.log)
    records, totals = scraped["records"], scraped["totals"]

    # consistency check: raw event counts must match Stage 0 exactly (same
    # records, same 10 files/record => same files read)
    raw_match = {}
    for rid in RECORD_ORDER:
        this_raw = records.get(rid, {}).get("events_raw")
        raw_match[rid] = {
            "stage1_raw": this_raw,
            "stage0_raw": STAGE0["raw_events"][rid],
            "matches": this_raw == STAGE0["raw_events"][rid],
        }

    cache = args.run_dir / "diphoton_masses_stage1.npz"
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
        edges, counts, out / "histograms" / "diphoton_stage1_bumpnet.root"
    )
    plot_mass_comparison(edges, counts, args.stage0_hist_root, n_total, n_overflow,
                          out / "plots" / "diphoton_stage1_mass.png")
    plot_funnel3(records, out / "plots" / "diphoton_stage1_funnel.png")

    n_in = int(counts.sum())
    nbins = len(counts)
    n_zwindow = int(((masses >= 80) & (masses <= 100)).sum())
    n_115_135 = int(((masses >= 115) & (masses <= 135)).sum())

    def _frac(a, b):
        return (a / b) if b else None

    stats = {
        "run_dir": str(args.run_dir),
        "config": "config.cms_higgs_diphoton_stage1.yaml",
        "cutbased_threshold_used": 1,
        "cutbased_wp_meaning": (
            "Fall17V2 ordinal ID confirmed from the Photon_cutBased branch's "
            "own ROOT title on real files from both records: "
            "'cut-based ID bitmap, Fall17V2, (0:fail, 1:loose, 2:medium, "
            "3:tight)'. cutBased>=1 = loose."
        ),
        "consistency_check_raw_events_vs_stage0": raw_match,
        "records": {
            rid: {
                "label": RECORD_LABELS[rid],
                "files_total": RECORD_NFILES_TOTAL[rid],
                "files_processed": records.get(rid, {}).get("files_processed"),
                "events_full_dataset": RECORD_NEVENTS_TOTAL[rid],
                "events_raw_processed": records.get(rid, {}).get("events_raw"),
                "events_ge2photon_kinematic_only_stage0": STAGE0["ge2photon_kinematic_only"][rid],
                "events_ge2photon_id_stage1": records.get(rid, {}).get("events_ge2photon_id"),
                "diphoton_pairs_formed_stage1": pairs_per_record.get(rid),
            }
            for rid in RECORD_ORDER
        },
        "combined": {
            "events_raw_processed": sum(
                records.get(r, {}).get("events_raw", 0) for r in RECORD_ORDER
            ),
            "events_ge2photon_kinematic_only_stage0": STAGE0["ge2photon_kinematic_only"]["combined"],
            "events_ge2photon_id_stage1": sum(
                records.get(r, {}).get("events_ge2photon_id", 0) for r in RECORD_ORDER
            ),
            "diphoton_pairs_formed_stage1": int(masses.size),
            "dedup_removed": totals.get("dedup_removed"),
        },
        "diphoton_mass_stage1": {
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
        "before_after_vs_stage0": {
            "n_pairs_total": {"stage0": STAGE0["diphoton_mass"]["n_pairs_total"],
                               "stage1": int(masses.size),
                               "retained_fraction": _frac(masses.size, STAGE0["diphoton_mass"]["n_pairs_total"])},
            "n_in_80_100_gev_Zwindow": {"stage0": STAGE0["diphoton_mass"]["n_in_80_100_gev_Zwindow"],
                                         "stage1": n_zwindow,
                                         "retained_fraction": _frac(n_zwindow, STAGE0["diphoton_mass"]["n_in_80_100_gev_Zwindow"])},
            "n_in_115_135_gev": {"stage0": STAGE0["diphoton_mass"]["n_in_115_135_gev"],
                                  "stage1": n_115_135,
                                  "retained_fraction": _frac(n_115_135, STAGE0["diphoton_mass"]["n_in_115_135_gev"])},
        },
        "bumpnet_histogram": {
            "root_file": str(out / "histograms" / "diphoton_stage1_bumpnet.root"),
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

    (out / "diphoton_stage1_stats.json").write_text(json.dumps(stats, indent=2))
    print(json.dumps(stats, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
