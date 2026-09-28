#!/usr/bin/env python
"""
Quality-gate plots for a dataset-parameterized delivery, in the style of
studies/cms_coverage/deliver/make_check_plots.py (that script is not
edited -- its own plot_one() is imported and reused unmodified here).

Produces:
  plot_1_largest.png, plot_2_median.png, plot_3_near_25bin_boundary.png
    -- same three as make_check_plots.py, from THIS delivery's own
       manifests/ROOT files.
  plot_new_category_{1,2,3}.png -- 3 histograms from BumpNet categories
    that are NEW relative to a prior delivery's manifest (only produced
    when --old-manifest-min26 is given), including at least one
    zero-jet dimuon category when one exists among the new names.
  plot_crop_comparison.png -- one histogram shown uncropped vs. cropped
    (studies/cms_coverage/deliver/make_crop_comparison_plot.py's own
    layout, reproduced here since that script only knows the old
    delivery's fixed filenames).

Usage:
    python make_delivery_check_plots.py \
        --manifest-min31 <manifest_..._min31bins.json> \
        --manifest-min26 <manifest_..._min26bins.json> \
        --root-min31 <..._min31bins.root> --root-min26 <..._min26bins.root> \
        --root-min31-cropped <..._min31bins_cropped.root> \
        --old-manifest-min26 <old delivery's manifest_min26bins.json> \
        --out-dir <plots dir>
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import uproot  # noqa: E402

from studies.cms_coverage.deliver.make_check_plots import plot_one  # noqa: E402

FS_CAT_PATTERN = re.compile(r"(\d+)ex_(\d+)mx_(\d+)jx_(\d+)gx(?:_(\d+)tx)?(?:_(\d+)bx)?")


def parse_fs_category(final_state_category: str):
    """Returns (n_e, n_m, n_j, n_b) or None if the string doesn't match."""
    m = FS_CAT_PATTERN.search(final_state_category or "")
    if not m:
        return None
    n_e, n_m, n_j = int(m.group(1)), int(m.group(2)), int(m.group(3))
    n_b = int(m.group(6)) if m.group(6) else 0
    return n_e, n_m, n_j, n_b


def is_zero_jet_dimuon(final_state_category: str) -> bool:
    c = parse_fs_category(final_state_category)
    if c is None:
        return False
    n_e, n_m, n_j, n_b = c
    return n_m >= 2 and n_j == 0 and n_b == 0


def is_zero_jet_dilepton(final_state_category: str, lepton_letter: str) -> bool:
    """Generalization of is_zero_jet_dimuon: lepton_letter is 'e' or 'm'."""
    c = parse_fs_category(final_state_category)
    if c is None:
        return False
    n_e, n_m, n_j, n_b = c
    n_lepton = n_e if lepton_letter == "e" else n_m
    return n_lepton >= 2 and n_j == 0 and n_b == 0


def is_zero_lepton(final_state_category: str) -> bool:
    c = parse_fs_category(final_state_category)
    if c is None:
        return False
    n_e, n_m, n_j, n_b = c
    return n_e == 0 and n_m == 0


def is_emu_category(final_state_category: str) -> bool:
    """>=1 selected electron AND >=1 selected muon -- the MuonEG task's
    own required category type among the 'new relative to prior
    deliveries' picks."""
    c = parse_fs_category(final_state_category)
    if c is None:
        return False
    n_e, n_m, n_j, n_b = c
    return n_e >= 1 and n_m >= 1


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--manifest-min31", required=True)
    p.add_argument("--manifest-min26", required=True)
    p.add_argument("--root-min31", required=True)
    p.add_argument("--root-min26", required=True)
    p.add_argument("--root-min31-cropped", required=True)
    p.add_argument("--old-manifest-min26", default=None,
                    help="comma-separated list of prior deliveries' manifest_..._min26bins.json -- "
                         "'new' means absent from the UNION of all of them")
    p.add_argument("--prefer-lepton-letter", default="m", choices=["e", "m"],
                    help="which lepton the 'at least one zero-jet dilepton category' pick should prefer (DoubleMuon: m, DoubleEG: e)")
    p.add_argument("--require-emu-category", action="store_true",
                    help="prioritize picking an e+mu category (>=1 electron AND >=1 muon) among the 'new' picks (MuonEG)")
    p.add_argument("--plot-largest-zero-lepton", action="store_true",
                    help="also plot the largest zero-selected-lepton histogram (0 electrons AND 0 muons)")
    p.add_argument("--out-dir", required=True)
    args = p.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    manifest_a = json.loads(Path(args.manifest_min31).read_text())
    manifest_b = json.loads(Path(args.manifest_min26).read_text())
    root_a = Path(args.root_min31)
    root_b = Path(args.root_min26)

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
        print("NOTE: no histograms unique to the >25-bin file; using the >30-bin file's own closest.")

    plot_one(root_a, largest, out_dir / "plot_1_largest.png", f"Largest by event count ({root_a.name})")
    plot_one(root_a, median_entry, out_dir / "plot_2_median.png",
              f"Median by event count, position {median_idx + 1}/{len(by_events_a)} ({root_a.name})")
    plot_one(near_boundary_root, near_boundary, out_dir / "plot_3_near_25bin_boundary.png",
              f"Near the 25-bin boundary ({near_boundary_root.name})")

    new_category_summary = []
    if args.old_manifest_min26:
        old_paths = args.old_manifest_min26.split(",")
        old_names = set()
        for old_path in old_paths:
            old_manifest = json.loads(Path(old_path).read_text())
            old_names |= set(e["name"] for e in old_manifest)
        new_entries = [e for e in manifest_b if e["name"] not in old_names]
        print(f"{len(new_entries)} names in this delivery's >25-bin manifest are NEW relative to the "
              f"union of {len(old_paths)} prior deliveries' manifests")

        chosen = []
        if args.require_emu_category:
            emu_new = [e for e in new_entries if is_emu_category(e.get("final_state_category", ""))]
            if emu_new:
                chosen.append(max(emu_new, key=lambda e: e["n_events"]))
        zero_jet_dilepton_new = [e for e in new_entries
                                  if is_zero_jet_dilepton(e.get("final_state_category", ""), args.prefer_lepton_letter)
                                  and e not in chosen]
        if zero_jet_dilepton_new:
            chosen.append(max(zero_jet_dilepton_new, key=lambda e: e["n_events"]))
        remaining = [e for e in new_entries if e not in chosen]
        remaining_sorted = sorted(remaining, key=lambda e: -e["n_events"])
        for e in remaining_sorted:
            if len(chosen) >= 3:
                break
            chosen.append(e)

        for i, entry in enumerate(chosen[:3], start=1):
            root_file = root_b if entry["name"] not in names_a else root_a
            plot_one(root_file, entry, out_dir / f"plot_new_category_{i}.png",
                      f"NEW vs. prior delivery ({root_file.name})")
            new_category_summary.append({
                "name": entry["name"], "n_events": entry["n_events"],
                "is_zero_jet_dilepton": is_zero_jet_dilepton(entry.get("final_state_category", ""), args.prefer_lepton_letter),
                "is_emu_category": is_emu_category(entry.get("final_state_category", "")),
            })
        print(json.dumps(new_category_summary, indent=2))

    largest_zero_lepton_summary = None
    if args.plot_largest_zero_lepton:
        zero_lepton_entries = [e for e in manifest_b if is_zero_lepton(e.get("final_state_category", ""))]
        if zero_lepton_entries:
            entry = max(zero_lepton_entries, key=lambda e: e["n_events"])
            root_file = root_b if entry["name"] not in names_a else root_a
            plot_one(root_file, entry, out_dir / "plot_largest_zero_lepton.png",
                      f"Largest zero-selected-lepton histogram ({root_file.name})")
            largest_zero_lepton_summary = {"name": entry["name"], "n_events": entry["n_events"]}
            print(json.dumps({"largest_zero_lepton": largest_zero_lepton_summary}, indent=2))
        else:
            print("NOTE: no zero-selected-lepton histograms found in the >25-bin manifest.")

    # Crop comparison: same histogram, uncropped vs cropped.
    key = f"ROI_{largest['name']}_width_10"
    f_un = uproot.open(str(root_a))
    f_cr = uproot.open(str(args.root_min31_cropped))
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
    fig.savefig(out_dir / "plot_crop_comparison.png", dpi=150)
    plt.close(fig)
    print(f"wrote {out_dir / 'plot_crop_comparison.png'}")

    print(json.dumps({
        "largest": {"name": largest["name"], "n_events": largest["n_events"]},
        "median": {"name": median_entry["name"], "n_events": median_entry["n_events"]},
        "near_25bin_boundary": {"name": near_boundary["name"], "n_filled_bins": near_boundary["n_filled_bins"]},
        "new_categories_plotted": new_category_summary,
        "largest_zero_lepton": largest_zero_lepton_summary,
    }, indent=2))


if __name__ == "__main__":
    main()
