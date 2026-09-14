#!/usr/bin/env python3
"""
m0m1j0: two leading-pT muons + leading-pT jet invariant mass (CMS Open Data,
DoubleMuon Run2016G/H, records 30522/30555 only).

This is a generic BumpNet search histogram, not a resonance search. The
expected shape is a smoothly falling continuum with no bump: the dimuon
subsystem contains a real Z peak at ~91 GeV, but that peak does NOT transfer
to the three-body mu-mu-jet mass, which sums a Z-consistent dimuon system
with an unrelated jet. Nothing in this script is tuned to produce or remove
any feature; it applies the fixed selection below and reports what comes out.

Reads a completed parse-only run directory (config.cms_m0m1j0_smoketest.yaml
or config.cms_m0m1j0_fullscale.yaml, --tasks parsing) and computes the
invariant mass directly from the parsed Muons/Jets collections -- the
generic mass-calculation stage is NOT used. That stage was already found,
for the diphoton and 4-lepton analyses on this project, to be impractically
slow at full scale (one chunk alone enumerated 1,648 distinct final-state
signatures in ~12 minutes with no sign of finishing) -- the exact same
final-state-proliferation limitation applies here, so this script follows
the same direct-computation approach those two analyses used
(scripts/higgs_diphoton_stage2_report.py, scripts/higgs_4lepton_zz_report.py).

Selection (see docs/M0M1J0_SPEC_INVESTIGATION.md and config.cms_m0m1j0_*.yaml
for the parse-time side of this):

  Parse time (loose, config.cms_m0m1j0_*.yaml -- already applied to the input
  files this script reads):
    - >=2 muons AND >=1 jet (particle_counts, not combined_particle_counts)
    - muons: pT > 5 GeV, |eta| < 2.4
    - jets: no cut
    - no charge / isolation / ID requirement

  Analysis time (tight, applied HERE, in this script):
    - muons: pT > 5 GeV, |eta| < 2.4, looseId == True, pfRelIso04_all < 0.35
      (the working point reused from the H->ZZ->4l analysis on this project)
    - jets: pT > 30 GeV, |eta| < 2.4
    - NO jet quality/ID cut of any kind -- this pipeline has no Jet_jetId or
      Jet_puId field anywhere in its schema (services/parsing/schemas.py).
      This is a known, accepted gap for this deliverable, not an oversight;
      it is restated on every plot and in the stats JSON this script writes.
    - no opposite-sign requirement on the two muons, no b-tag requirement or
      veto on the jet
    - take the 2 highest-pT muons and the 1 highest-pT jet surviving the
      above cuts; drop events with fewer than that
    - invariant mass = |sum of the three four-momenta| (muon/jet masses
      taken from their own parsed Muons_mass/Jets_mass branches, not a
      fixed lookup table)

  NOT implemented, on purpose, out of scope for this deliverable:
    - Z-candidate collapsing (removing leptons that form a Z candidate from
      the lepton list before combinatorics, as the BumpNet paper does). If
      the two leading muons here happen to form a Z candidate, they are
      still used to build m0m1j0 -- the paper's methodology would route
      them elsewhere first. This repository's m0m1j0 is therefore NOT
      directly equivalent to the same-named histogram in the BumpNet paper.

Units: CMS NanoAOD is GeV-native; this repo applies no MeV->GeV scaling to
it (services/parsing/schemas.py: native_pt_unit="GeV" for the cms-nanoaod
schema). As a sanity check against the real factor-of-1000 bug this project
hit before, this script reports the median dimuon (2 leading muons alone,
before adding the jet) mass -- it must cluster near 91 GeV, not 91000.

Framing: this script reports observed counts and shapes only. It computes
no significance, p-value, or sigma, and asserts no cause for any feature in
the distribution -- that is not what a BumpNet input histogram is for.

Usage (on the cluster, inside the pipeline's conda env):
    python scripts/m0m1j0_mumujet_report.py \\
        --run-dir /storage/agrp/berkom/atlas-utilization/output/cms_m0m1j0_smoketest_YYYYMMDD_HHMMSS \\
        --log /path/to/smoketest_run.log \\
        --out-dir reports/m0m1j0_mumujet_smoketest
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import numpy as np

BUMPNET_MIN_BINS = 30
BUMPNET_MIN_ENTRIES = 100
BIN_WIDTH_GEV = 10.0
HIST_MIN_GEV = 0.0
HIST_MAX_GEV = 1000.0
N_BINS = int(round((HIST_MAX_GEV - HIST_MIN_GEV) / BIN_WIDTH_GEV))  # 100

# Hand-written to match this repo's established (if ad hoc) precedent for
# standalone-script histogram names -- see docs/M0M1J0_SPEC_INVESTIGATION.md
# section A.6/B.3. The generic naming function
# (services/pipelines/histograms_pipeline.py::_convert_to_bumpnet_name)
# is NOT imported: its module imports `fcntl`, which does not exist on
# Windows, and neither of the two prior precedent scripts imported it either
# -- both hand-wrote their name the same way this one does.
BUMPNET_NAME = "mass_m0m1j0_cat_0ex_2mx_1jx_0gx_0tx_0bx"

RECORD_LABELS = {"30522": "DoubleMuon Run2016G", "30555": "DoubleMuon Run2016H"}
RECORD_ORDER = ["30522", "30555"]

# Analysis-time cuts (see module docstring). Kept as named constants so the
# plot annotation and the actual filtering logic can never drift apart.
MUON_PT_MIN_GEV = 5.0
MUON_ETA_MAX = 2.4
MUON_ISO_MAX = 0.35
JET_PT_MIN_GEV = 30.0
JET_ETA_MAX = 2.4


def parse_log(log_path: Path) -> dict:
    """
    Scrape per-record retention and file-open stats from a parsing run log.

    Matches the log lines this project's parsing_handler.py actually emits:
      "Retention record_<id>: <kept> / <raw> events kept (<pct>%)"
      "File opens record_<id>: <ok>/<total> succeeded, <fail> failed (<pct>% failure)"
      "Parsing complete: <ok>/<total> files, <events> events, <rate>% success rate"
    """
    text = log_path.read_text(errors="replace")
    records: dict[str, dict] = {}

    for m in re.finditer(
        r"Retention record_(\d+): ([\d,]+) / ([\d,]+) events kept \(([\d.]+)%\)", text
    ):
        rid = m.group(1)
        records.setdefault(rid, {})
        records[rid]["events_final"] = int(m.group(2).replace(",", ""))
        records[rid]["events_raw"] = int(m.group(3).replace(",", ""))
        records[rid]["retention_pct"] = float(m.group(4))

    for m in re.finditer(
        r"File opens record_(\d+): (\d+)/(\d+) succeeded, (\d+) failed \(([\d.]+)% failure\)",
        text,
    ):
        rid = m.group(1)
        records.setdefault(rid, {})
        records[rid]["files_ok"] = int(m.group(2))
        records[rid]["files_attempted"] = int(m.group(3))
        records[rid]["files_failed"] = int(m.group(4))
        records[rid]["file_failure_pct"] = float(m.group(5))

    aborted = None
    m = re.search(
        r"Record (\d+): (\d+)/(\d+) files failed to open \(([\d.]+)% failure rate, "
        r"exceeds the ([\d.]+)% threshold\)",
        text,
    )
    if m:
        aborted = {
            "record": m.group(1),
            "files_failed": int(m.group(2)),
            "files_total": int(m.group(3)),
            "failure_rate_pct": float(m.group(4)),
            "threshold_pct": float(m.group(5)),
        }

    totals = {}
    m = re.search(
        r"Parsing complete: (\d+)/(\d+) files, (\d+) events, ([\d.]+)% success rate", text
    )
    if m:
        totals["files_ok"] = int(m.group(1))
        totals["files_attempted"] = int(m.group(2))
        totals["events_total"] = int(m.group(3))
        totals["file_success_rate_pct"] = float(m.group(4))

    return {"records": records, "totals": totals, "aborted_by_guard": aborted}


def _select_muons(arr):
    """Boolean per-muon mask: pT>5, |eta|<2.4, looseId, pfRelIso04_all<0.35."""
    import awkward as ak

    pt = arr["Muons_pt"]
    eta = arr["Muons_eta"]
    loose = arr["Muons_looseId"]
    iso = arr["Muons_pfRelIso04_all"]
    mask = (
        (pt > MUON_PT_MIN_GEV)
        & (abs(eta) < MUON_ETA_MAX)
        & (ak.values_astype(loose, bool) == True)  # noqa: E712
        & (iso < MUON_ISO_MAX)
    )
    return mask


def _select_jets(arr):
    """Boolean per-jet mask: pT>30, |eta|<2.4. No jet-quality/ID cut (none exists)."""
    pt = arr["Jets_pt"]
    eta = arr["Jets_eta"]
    return (pt > JET_PT_MIN_GEV) & (abs(eta) < JET_ETA_MAX)


def load_masses(run_dir: Path):
    """
    Read every parsed chunk under run_dir/parsed_data, apply the analysis-time
    selection, and return (m0m1j0 masses, dimuon-only masses, per-record
    candidate counts, per-record raw-event counts seen by this script).
    """
    import awkward as ak
    import uproot
    import vector

    vector.register_awkward()

    parsed = sorted((run_dir / "parsed_data").glob("*.root"))
    if not parsed:
        raise FileNotFoundError(f"no parsed .root chunks in {run_dir / 'parsed_data'}")

    branches = [
        "Muons_pt", "Muons_eta", "Muons_phi", "Muons_mass",
        "Muons_looseId", "Muons_pfRelIso04_all",
        "Jets_pt", "Jets_eta", "Jets_phi", "Jets_mass",
        "source_record",
    ]

    mumujet_parts: list[np.ndarray] = []
    dimuon_parts: list[np.ndarray] = []
    per_record_candidates: dict[str, int] = {}
    per_record_events_seen: dict[str, int] = {}

    for chunk in parsed:
        arr = uproot.open(chunk)["events"].arrays(branches, library="ak")

        src_all = np.asarray(arr["source_record"])
        for rid in np.unique(src_all):
            per_record_events_seen[str(int(rid))] = (
                per_record_events_seen.get(str(int(rid)), 0) + int((src_all == rid).sum())
            )

        muon_mask = _select_muons(arr)
        jet_mask = _select_jets(arr)

        mu_pt = arr["Muons_pt"][muon_mask]
        mu_eta = arr["Muons_eta"][muon_mask]
        mu_phi = arr["Muons_phi"][muon_mask]
        mu_mass = arr["Muons_mass"][muon_mask]

        jet_pt = arr["Jets_pt"][jet_mask]
        jet_eta = arr["Jets_eta"][jet_mask]
        jet_phi = arr["Jets_phi"][jet_mask]
        jet_mass = arr["Jets_mass"][jet_mask]

        has_2mu = ak.num(mu_pt, axis=1) >= 2
        has_1jet = ak.num(jet_pt, axis=1) >= 1
        keep = has_2mu & has_1jet

        if not ak.any(keep):
            continue

        mu_pt, mu_eta, mu_phi, mu_mass = (
            mu_pt[keep], mu_eta[keep], mu_phi[keep], mu_mass[keep]
        )
        jet_pt, jet_eta, jet_phi, jet_mass = (
            jet_pt[keep], jet_eta[keep], jet_phi[keep], jet_mass[keep]
        )
        src = src_all[np.asarray(keep)]

        # Rank by pT (descending) and take the 2 leading muons + leading jet.
        mu_order = ak.argsort(mu_pt, axis=1, ascending=False)
        mu_pt, mu_eta, mu_phi, mu_mass = (
            mu_pt[mu_order][:, :2], mu_eta[mu_order][:, :2],
            mu_phi[mu_order][:, :2], mu_mass[mu_order][:, :2],
        )
        jet_order = ak.argsort(jet_pt, axis=1, ascending=False)
        jet_pt, jet_eta, jet_phi, jet_mass = (
            jet_pt[jet_order][:, :1], jet_eta[jet_order][:, :1],
            jet_phi[jet_order][:, :1], jet_mass[jet_order][:, :1],
        )

        mu_vecs = vector.zip({"pt": mu_pt, "eta": mu_eta, "phi": mu_phi, "mass": mu_mass})
        jet_vecs = vector.zip({"pt": jet_pt, "eta": jet_eta, "phi": jet_phi, "mass": jet_mass})

        dimuon = mu_vecs[:, 0] + mu_vecs[:, 1]
        total = dimuon + jet_vecs[:, 0]

        m_mumujet = np.asarray(ak.to_numpy(total.mass), dtype=float)
        m_dimuon = np.asarray(ak.to_numpy(dimuon.mass), dtype=float)

        mumujet_parts.append(m_mumujet)
        dimuon_parts.append(m_dimuon)

        for rid in np.unique(src):
            per_record_candidates[str(int(rid))] = (
                per_record_candidates.get(str(int(rid)), 0) + int((src == rid).sum())
            )

    masses = np.concatenate(mumujet_parts) if mumujet_parts else np.array([], dtype=float)
    dimuon_masses = np.concatenate(dimuon_parts) if dimuon_parts else np.array([], dtype=float)
    return masses, dimuon_masses, per_record_candidates, per_record_events_seen


def build_hist(masses: np.ndarray):
    edges = np.linspace(HIST_MIN_GEV, HIST_MAX_GEV, N_BINS + 1)
    in_range = masses[(masses >= HIST_MIN_GEV) & (masses <= HIST_MAX_GEV)]
    counts, _ = np.histogram(in_range, bins=edges)
    n_below_min = int((masses < HIST_MIN_GEV).sum())
    n_above_max = int((masses > HIST_MAX_GEV).sum())
    return edges, counts, n_below_min, n_above_max


def find_p99_cutoff(masses: np.ndarray) -> float | None:
    """
    Return the smallest round-ish GeV cutoff such that >99% of entries fall
    below it, or None if not applicable (e.g. no entries, or >1% of entries
    already extend past HIST_MAX_GEV so a zoom would hide real content).
    """
    if masses.size == 0:
        return None
    n = masses.size
    p99 = float(np.percentile(masses, 99))
    # Round up to the next 50 GeV for a clean axis, floor at 100 GeV.
    cutoff = max(100.0, 50.0 * np.ceil(p99 / 50.0))
    if cutoff >= HIST_MAX_GEV:
        return None
    frac_below = float((masses < cutoff).sum()) / n
    if frac_below <= 0.99:
        return None
    return cutoff


def write_bumpnet_root(edges, counts, out_root: Path) -> str:
    import uproot

    out_root.parent.mkdir(parents=True, exist_ok=True)
    name = f"{BUMPNET_NAME}_width_{BIN_WIDTH_GEV}"
    with uproot.recreate(str(out_root)) as f:
        f[name] = (counts, edges)
    return name


CAPTION_NOTE = (
    "This is a generic BumpNet search histogram (no resonance expected). The "
    "dimuon subsystem contains a real Z peak near 91 GeV, but the three-body "
    "mu-mu-jet mass is a continuum -- the Z peak does not transfer to it. "
    "No jet quality/ID cut applied (no such field exists in this pipeline). "
    "Z-candidate collapsing (BumpNet paper) is NOT implemented here -- if "
    "the 2 leading muons form a Z candidate they are included anyway; this "
    "is this repository's own m0m1j0, not directly paper-comparable. "
    "Not a significance claim -- visual only."
)


def _annotate(ax, n_in, nbins, dimuon_median):
    bar_bins = "PASS" if nbins > BUMPNET_MIN_BINS else "FAIL"
    bar_ent = "PASS" if n_in >= BUMPNET_MIN_ENTRIES else "FAIL"
    ax.text(
        0.985, 0.97,
        f"entries={n_in:,}  bins={nbins}\n"
        f">{BUMPNET_MIN_BINS} bins: {bar_bins}   >={BUMPNET_MIN_ENTRIES} entries: {bar_ent}\n"
        f"dimuon median = {dimuon_median:.1f} GeV (sanity check, expect ~91)\n"
        f"cuts: mu pT>{MUON_PT_MIN_GEV:.0f}, |eta|<{MUON_ETA_MAX}, looseId, iso<{MUON_ISO_MAX} | "
        f"jet pT>{JET_PT_MIN_GEV:.0f}, |eta|<{JET_ETA_MAX}, NO jet ID cut",
        transform=ax.transAxes, ha="right", va="top", fontsize=6.8,
        bbox=dict(boxstyle="round", fc="white", ec="#999999", alpha=0.9),
    )


def plot_mass(edges, counts, out_png: Path, dimuon_median: float, title_suffix: str = "") -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    centers = 0.5 * (edges[:-1] + edges[1:])
    n_in = int(counts.sum())
    nbins = len(counts)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5.4))

    ax1.bar(centers, counts, width=BIN_WIDTH_GEV * 0.9,
            color="#1b6fa8", edgecolor="#0d3a57", linewidth=0.4)
    ax1.set_xlabel("m(mu0, mu1, jet0)  [GeV]")
    ax1.set_ylabel(f"events / {BIN_WIDTH_GEV:.0f} GeV")
    ax1.set_xlim(edges[0], edges[-1])
    ax1.set_yscale("log")
    ax1.set_title(f"log scale{title_suffix}", fontsize=9)

    ax2.bar(centers, counts, width=BIN_WIDTH_GEV * 0.9,
            color="#1b6fa8", edgecolor="#0d3a57", linewidth=0.4)
    ax2.set_xlabel("m(mu0, mu1, jet0)  [GeV]")
    ax2.set_ylabel(f"events / {BIN_WIDTH_GEV:.0f} GeV")
    ax2.set_xlim(edges[0], edges[-1])
    ax2.set_title(f"linear scale{title_suffix}", fontsize=9)
    _annotate(ax2, n_in, nbins, dimuon_median)

    fig.suptitle(
        f"CMS Open Data DoubleMuon (30522+30555) -- m0m1j0{title_suffix}\n{CAPTION_NOTE}",
        fontsize=7.6, wrap=True,
    )
    fig.tight_layout(rect=(0, 0, 1, 0.90))
    fig.savefig(out_png, dpi=130)
    plt.close(fig)


def plot_funnel(records: dict, out_png: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    labels, raw_v, final_v = [], [], []
    for rid in RECORD_ORDER:
        r = records.get(rid, {})
        labels.append(RECORD_LABELS.get(rid, rid).replace(" Run", "\nRun"))
        raw_v.append(r.get("events_raw", 0))
        final_v.append(r.get("events_final", 0))
    labels.append("COMBINED")
    raw_v.append(sum(raw_v))
    final_v.append(sum(final_v))

    x = np.arange(len(labels))
    fig, ax = plt.subplots(figsize=(7, 5))
    w = 0.35
    ax.bar(x - w / 2, raw_v, w, color="#999999", label="raw events read")
    ax.bar(x + w / 2, final_v, w, color="#1b6fa8",
           label=">=2 muons (pT>5,|eta|<2.4) AND >=1 jet\n(parse-time selection)")
    ax.set_yscale("log")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=8)
    for xi, v in zip(x, raw_v):
        ax.text(xi - w / 2, v, f"{v:,}", ha="center", va="bottom", fontsize=7)
    for xi, v in zip(x, final_v):
        ax.text(xi + w / 2, v, f"{v:,}", ha="center", va="bottom", fontsize=7)
    ax.legend(fontsize=7, loc="upper left")
    ax.set_title("m0m1j0: parse-time event funnel", fontsize=10)
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

    cache = args.run_dir / "m0m1j0_masses.npz"
    if cache.exists():
        z = np.load(cache, allow_pickle=True)
        masses = z["masses"]
        dimuon_masses = z["dimuon_masses"]
        per_record_candidates = {str(k): int(v) for k, v in z["per_record_candidates"].item().items()}
        per_record_events_seen = {str(k): int(v) for k, v in z["per_record_events_seen"].item().items()}
        print(f"loaded {masses.size:,} masses from cache {cache}")
    else:
        masses, dimuon_masses, per_record_candidates, per_record_events_seen = load_masses(args.run_dir)
        np.savez_compressed(
            cache, masses=masses, dimuon_masses=dimuon_masses,
            per_record_candidates=np.array(per_record_candidates, dtype=object),
            per_record_events_seen=np.array(per_record_events_seen, dtype=object),
        )

    dimuon_median = float(np.median(dimuon_masses)) if dimuon_masses.size else float("nan")

    edges, counts, n_below, n_above = build_hist(masses)
    n_in = int(counts.sum())
    nbins = len(counts)

    hist_name = write_bumpnet_root(
        edges, counts, out / "histograms" / f"{BUMPNET_NAME}_width_{BIN_WIDTH_GEV}.root"
    )
    plot_mass(edges, counts, out / "plots" / "m0m1j0_mass.png", dimuon_median)
    plot_funnel(records, out / "plots" / "m0m1j0_funnel.png")

    zoom_png = None
    p99_cutoff = find_p99_cutoff(masses)
    if p99_cutoff is not None:
        zoom_edges = np.linspace(0.0, p99_cutoff, int(round(p99_cutoff / BIN_WIDTH_GEV)) + 1)
        zoom_in_range = masses[(masses >= 0.0) & (masses <= p99_cutoff)]
        zoom_counts, _ = np.histogram(zoom_in_range, bins=zoom_edges)
        zoom_png = out / "plots" / "m0m1j0_mass_zoomed.png"
        plot_mass(zoom_edges, zoom_counts, zoom_png, dimuon_median,
                  title_suffix=f" (zoomed to 0-{p99_cutoff:.0f} GeV, >99% of entries)")

    stats = {
        "run_dir": str(args.run_dir),
        "records_used": RECORD_ORDER,
        "records_excluded": "SingleMuon not used -- see module docstring / task instructions",
        "bumpnet_histogram": {
            "root_file": str(out / "histograms" / f"{BUMPNET_NAME}_width_{BIN_WIDTH_GEV}.root"),
            "hist_name": hist_name,
            "bin_width_gev": BIN_WIDTH_GEV,
            "range_gev": [HIST_MIN_GEV, HIST_MAX_GEV],
            "n_bins": nbins,
            "n_nonempty_bins": int((counts > 0).sum()),
            "entries_in_range": n_in,
            "entries_below_range": n_below,
            "entries_above_range": n_above,
            "entries_total": int(masses.size),
            "meets_bin_bar": nbins > BUMPNET_MIN_BINS,
            "meets_entry_bar": n_in >= BUMPNET_MIN_ENTRIES,
            "min_bins_required": BUMPNET_MIN_BINS,
            "min_entries_required": BUMPNET_MIN_ENTRIES,
        },
        "mass_range_actual": {
            "min_gev": float(masses.min()) if masses.size else None,
            "max_gev": float(masses.max()) if masses.size else None,
            "median_gev": float(np.median(masses)) if masses.size else None,
            "p99_gev": float(np.percentile(masses, 99)) if masses.size else None,
            "zoomed_plot": str(zoom_png) if zoom_png else None,
            "zoomed_cutoff_gev": p99_cutoff,
        },
        "dimuon_sanity_check": {
            "median_gev": dimuon_median,
            "expected_near_gev": 91.0,
            "note": "2 leading muons only, before adding the jet -- confirms GeV "
                    "(not MeV-scale, i.e. not ~91000) units for this CMS NanoAOD data",
        },
        "per_record": {
            rid: {
                "label": RECORD_LABELS.get(rid, rid),
                "files_attempted": records.get(rid, {}).get("files_attempted"),
                "files_ok": records.get(rid, {}).get("files_ok"),
                "files_failed": records.get(rid, {}).get("files_failed"),
                "file_failure_pct": records.get(rid, {}).get("file_failure_pct"),
                "events_raw": records.get(rid, {}).get("events_raw"),
                "events_retained_parse_time": records.get(rid, {}).get("events_final"),
                "retention_pct_parse_time": records.get(rid, {}).get("retention_pct"),
                "events_seen_by_this_script": per_record_events_seen.get(rid),
                "m0m1j0_candidates_analysis_time": per_record_candidates.get(rid),
            }
            for rid in RECORD_ORDER
        },
        "loud_failure_guard": {
            "present": True,
            "threshold_pct": 20.0,
            "aborted_this_run": scraped["aborted_by_guard"] is not None,
            "abort_detail": scraped["aborted_by_guard"],
        },
        "files_ok_total": totals.get("files_ok"),
        "files_attempted_total": totals.get("files_attempted"),
        "selection": {
            "records": RECORD_ORDER,
            "parse_time": {
                "particle_counts": {"muons": {"min": 2}, "jets": {"min": 1}},
                "kinematic_cuts": {"muons": {"pt_min": MUON_PT_MIN_GEV, "eta_max": MUON_ETA_MAX}},
                "jet_cut_at_parse_time": None,
                "mechanism": "particle_counts (per-collection, AND-combined) -- "
                             "NOT combined_particle_counts (that is the >=4-lepton "
                             "OR/sum machinery, wrong tool here)",
            },
            "analysis_time": {
                "muons": {"pt_min": MUON_PT_MIN_GEV, "eta_max": MUON_ETA_MAX,
                          "looseId": True, "pfRelIso04_all_max": MUON_ISO_MAX},
                "jets": {"pt_min": JET_PT_MIN_GEV, "eta_max": JET_ETA_MAX,
                         "jet_id_cut": "NONE -- no Jet_jetId/Jet_puId field exists "
                                       "in this pipeline's schema (known, accepted gap)"},
                "opposite_sign_required": False,
                "btag_requirement_or_veto": False,
                "z_candidate_collapsing": "NOT implemented (out of scope) -- see "
                                           "module docstring",
            },
        },
    }

    (out / "m0m1j0_stats.json").write_text(json.dumps(stats, indent=2))
    print(json.dumps(stats, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
