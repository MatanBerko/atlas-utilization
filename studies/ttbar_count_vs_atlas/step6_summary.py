#!/usr/bin/env python
"""
Step 6 (ttbar_count_vs_atlas), final assembly: one table across the three
variants, the delivered CMS data result and Maryna's ATLAS numbers.

Reads each variant's build_summary_<variant>.json (written by
build_study_histograms.py) plus the delivered CMS data ROOT file, and
writes STEP6_RESULTS.md and evidence/step6_summary.json.

The ATLAS figures are Maryna's, quoted -- they are NOT computed here and
are labelled as reported, not verified.

Usage:
    python step6_summary.py --study-dir <dir> --cms-delivery-root <root> \
        --out-md <md> --out-json <json>
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

import uproot

VARIANTS = ("rare4", "pr31", "pr31_noOR")
VARIANT_DESC = {
    "rare4": "(a) rare4 - our delivered final-state rule (>= 5 light jets kept, labelled 4j)",
    "pr31": "(b) pr31 - as (a) but >= 5 light jets dropped, reproducing PR #31",
    "pr31_noOR": "(c) pr31_noOR - as (b) without our jet-lepton dR < 0.4 overlap removal",
}
LEPTON_ORDER = ["at_least_one_muon", "electrons_but_no_muon", "no_lepton"]
LEPTON_LABEL = {
    "at_least_one_muon": "has >= 1 muon",
    "electrons_but_no_muon": "electrons, no muon",
    "no_lepton": "no lepton",
}

# Reported by Maryna for ATLAS ttbar MC through upstream PR #31.
ATLAS_HISTOGRAMS = 2146
ATLAS_CATEGORIES = 135


def strip_key(k):
    n = k.split(";")[0]
    if n.startswith("ROI_"):
        n = n[len("ROI_"):]
    if "_width_" in n:
        n = n.rsplit("_width_", 1)[0]
    return n


def category_of(name):
    return name.split("_cat_", 1)[1] if "_cat_" in name else "UNKNOWN"


def lepton_content(category):
    counts = {}
    for tok in category.split("_"):
        tok = tok[:-1] if tok.endswith("x") else tok
        if len(tok) >= 2 and tok[:-1].isdigit():
            counts[tok[-1]] = int(tok[:-1])
    if counts.get("m", 0) >= 1:
        return "at_least_one_muon"
    if counts.get("e", 0) >= 1:
        return "electrons_but_no_muon"
    return "no_lepton"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--study-dir", required=True)
    p.add_argument("--cms-delivery-root", required=True)
    p.add_argument("--out-md", required=True)
    p.add_argument("--out-json", required=True)
    args = p.parse_args()

    study = Path(args.study_dir)
    summaries = {v: json.loads((study / v / f"build_summary_{v}.json").read_text())
                 for v in VARIANTS}

    with uproot.open(args.cms_delivery_root) as f:
        cms_names = [strip_key(k) for k in sorted(set(k.split(";")[0] for k in f.keys()))]
    cms_cats = sorted({category_of(n) for n in cms_names})
    cms_cat_lc = Counter(lepton_content(c) for c in cms_cats)
    cms_hist_lc = Counter(lepton_content(category_of(n)) for n in cms_names)

    L = []
    L.append("# Step 6 - CMS ttbar study histograms, three variants")
    L.append("")
    L.append("All numbers below are VERIFIED BY RUNNING unless a row says otherwise.")
    L.append("Histograms are RAW, unweighted counts, built with the SAME post-processing")
    L.append("as our delivery (fixed 10 GeV bins 0-10 TeV, 115 GeV Z-peak cutoff on")
    L.append("same-flavour dilepton channels, 10 TeV max-mass cutoff, peak removal,")
    L.append("first-empty-bin split, >= 100 events per final state and per histogram,")
    L.append("cropping), reusing the delivery builder functions unmodified.")
    L.append("")

    L.append("## Events processed")
    L.append("")
    L.append("| variant | events read | passing >= 2-object gate | rejected e+mu+b > 4 | dropped >= 5 light jets | into combinations |")
    L.append("|---|---:|---:|---:|---:|---:|")
    for v in VARIANTS:
        e = summaries[v]["event_counts"]
        L.append(f"| {v} | {e['n_events_read']:,} | {e['n_events_passing_gate']:,} | "
                 f"{e['n_rejected_e_mu_b_gt4']:,} | {e['n_dropped_ge5_light_jets']:,} | "
                 f"{e['n_events_into_combinations']:,} |")
    L.append("")
    gw = summaries["rare4"]["sum_genweight_all_events"]
    L.append(f"Sum of `genWeight` over every event in the record: **{gw:,.6g}** "
             f"(FOR INFORMATION ONLY - it is never applied; the histograms are raw counts, "
             f"as the ATLAS reference counts are).")
    L.append(f"Input files: {summaries['rare4']['n_input_files']}.")
    L.append("")

    L.append("## The funnel")
    L.append("")
    L.append("| stage | " + " | ".join(VARIANTS) + " |")
    L.append("|---|" + "---:|" * len(VARIANTS))
    stages = [
        ("names with >= 1 event", "a_names_with_at_least_1_event"),
        ("after >= 100 events per FINAL STATE", "b_after_min_events_per_final_state_100"),
        ("after post-processing (>= 100 main events)", "c_after_postprocessing_ge100_main_events"),
        (">= 25 filled bins (ATLAS wording)", "d_ge25_bins"),
        ("> 25 filled bins (min26bins, our delivery)", "d_gt25_bins_min26bins"),
        ("> 30 filled bins (min31bins)", "d_gt30_bins_min31bins"),
    ]
    for label, key in stages:
        L.append(f"| {label} | " + " | ".join(str(summaries[v]["funnel"][key]) for v in VARIANTS) + " |")
    L.append("")

    L.append("## Headline: categories and histograms, against ATLAS and against our CMS data")
    L.append("")
    L.append("| | categories | histograms |")
    L.append("|---|---:|---:|")
    L.append(f"| **ATLAS ttbar through PR #31** (reported by Maryna, >= 25 bins, "
             f">= 100 events) - NOT verified here | {ATLAS_CATEGORIES} | {ATLAS_HISTOGRAMS} |")
    for v in VARIANTS:
        b = summaries[v]["breakdown"]["d_ge25_bins"]
        L.append(f"| CMS ttbar, {v}, >= 25 bins | {b['n_categories']} | {b['n_histograms']} |")
    for v in VARIANTS:
        b = summaries[v]["breakdown"]["d_gt25_bins_min26bins"]
        L.append(f"| CMS ttbar, {v}, > 25 bins | {b['n_categories']} | {b['n_histograms']} |")
    L.append(f"| **our delivered CMS DATA** (rare4, > 25 bins, muon-triggered) | "
             f"{len(cms_cats)} | {len(cms_names)} |")
    L.append("")

    L.append("## Categories by lepton content (>= 25 filled bins)")
    L.append("")
    L.append("| variant | " + " | ".join(LEPTON_LABEL[k] for k in LEPTON_ORDER) + " | total |")
    L.append("|---|" + "---:|" * (len(LEPTON_ORDER) + 1))
    for v in VARIANTS:
        b = summaries[v]["breakdown"]["d_ge25_bins"]["n_categories_by_lepton_content"]
        tot = summaries[v]["breakdown"]["d_ge25_bins"]["n_categories"]
        L.append(f"| {v} | " + " | ".join(str(b.get(k, 0)) for k in LEPTON_ORDER) + f" | {tot} |")
    L.append("| **delivered CMS data (reference)** | "
             + " | ".join(str(cms_cat_lc.get(k, 0)) for k in LEPTON_ORDER)
             + f" | {len(cms_cats)} |")
    L.append("")
    L.append("## Histograms by lepton content (>= 25 filled bins)")
    L.append("")
    L.append("| variant | " + " | ".join(LEPTON_LABEL[k] for k in LEPTON_ORDER) + " | total |")
    L.append("|---|" + "---:|" * (len(LEPTON_ORDER) + 1))
    for v in VARIANTS:
        b = summaries[v]["breakdown"]["d_ge25_bins"]["n_histograms_by_lepton_content"]
        tot = summaries[v]["breakdown"]["d_ge25_bins"]["n_histograms"]
        L.append(f"| {v} | " + " | ".join(str(b.get(k, 0)) for k in LEPTON_ORDER) + f" | {tot} |")
    L.append("| **delivered CMS data (reference)** | "
             + " | ".join(str(cms_hist_lc.get(k, 0)) for k in LEPTON_ORDER)
             + f" | {len(cms_names)} |")
    L.append("")

    # How much of the gap the muon restriction accounts for, per variant.
    L.append("## How much of the category count the muon-trigger restriction removes")
    L.append("")
    L.append("| variant | categories at >= 25 bins | of those, with >= 1 muon | lost to a muon requirement | share lost |")
    L.append("|---|---:|---:|---:|---:|")
    gap_rows = {}
    for v in VARIANTS:
        b = summaries[v]["breakdown"]["d_ge25_bins"]
        tot = b["n_categories"]
        with_mu = b["n_categories_by_lepton_content"].get("at_least_one_muon", 0)
        lost = tot - with_mu
        gap_rows[v] = {"total": tot, "with_muon": with_mu, "lost": lost,
                       "share_lost": (lost / tot if tot else 0.0)}
        L.append(f"| {v} | {tot} | {with_mu} | {lost} | {100 * lost / tot:.0f}% |" if tot
                 else f"| {v} | 0 | 0 | 0 | - |")
    L.append("")
    L.append("Every one of the delivered CMS data categories has at least one muon "
             f"({cms_cat_lc.get('at_least_one_muon', 0)} of {len(cms_cats)}), which is what a "
             "DoubleMuon+SingleMuon trigger-matched selection must give. The rows above are "
             "therefore the part of the category space that our delivered CMS data cannot "
             "reach at all, independently of statistics.")
    L.append("")

    L.append("## Per-variant object content of the surviving histograms (>= 25 bins)")
    L.append("")
    L.append("| variant | b-jet-containing | lepton+jet | lepton-only | jet-only |")
    L.append("|---|---:|---:|---:|---:|")
    for v in VARIANTS:
        o = summaries[v]["object_content_categories_ge25"]
        L.append(f"| {v} | {o.get('b-jet-containing', 0)} | {o.get('lepton+jet', 0)} | "
                 f"{o.get('lepton-only', 0)} | {o.get('jet-only', 0)} |")
    L.append("")

    Path(args.out_md).write_text("\n".join(L) + "\n", encoding="utf-8")

    out = {
        "atlas_reported": {"categories": ATLAS_CATEGORIES, "histograms": ATLAS_HISTOGRAMS,
                           "status": "reported by Maryna, NOT verified here"},
        "cms_data_delivery": {
            "root": args.cms_delivery_root,
            "categories": len(cms_cats), "histograms": len(cms_names),
            "categories_by_lepton_content": dict(cms_cat_lc),
            "histograms_by_lepton_content": dict(cms_hist_lc),
        },
        "variants": {v: {
            "description": VARIANT_DESC[v],
            "n_input_files": summaries[v]["n_input_files"],
            "event_counts": summaries[v]["event_counts"],
            "sum_genweight_all_events": summaries[v]["sum_genweight_all_events"],
            "funnel": summaries[v]["funnel"],
            "ge25": summaries[v]["breakdown"]["d_ge25_bins"]["n_histograms"],
            "ge25_categories": summaries[v]["breakdown"]["d_ge25_bins"]["n_categories"],
            "ge25_categories_by_lepton_content":
                summaries[v]["breakdown"]["d_ge25_bins"]["n_categories_by_lepton_content"],
            "ge25_histograms_by_lepton_content":
                summaries[v]["breakdown"]["d_ge25_bins"]["n_histograms_by_lepton_content"],
            "gt25": summaries[v]["breakdown"]["d_gt25_bins_min26bins"]["n_histograms"],
            "gt25_categories": summaries[v]["breakdown"]["d_gt25_bins_min26bins"]["n_categories"],
            "gt30": summaries[v]["breakdown"]["d_gt30_bins_min31bins"]["n_histograms"],
            "gt30_categories": summaries[v]["breakdown"]["d_gt30_bins_min31bins"]["n_categories"],
            "object_content_ge25": summaries[v]["object_content_categories_ge25"],
        } for v in VARIANTS},
        "muon_restriction_effect_on_categories_ge25": gap_rows,
    }
    Path(args.out_json).write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"wrote {args.out_md} and {args.out_json}")
    for v in VARIANTS:
        d = out["variants"][v]
        print(f"{v:10s} >=25bins: {d['ge25']:5d} histograms in {d['ge25_categories']:3d} categories "
              f"| >25: {d['gt25']:5d}/{d['gt25_categories']:3d} "
              f"| >30: {d['gt30']:5d}/{d['gt30_categories']:3d}")
    print(f"ATLAS reported: {ATLAS_HISTOGRAMS} histograms in {ATLAS_CATEGORIES} categories")
    print(f"CMS data delivery: {len(cms_names)} histograms in {len(cms_cats)} categories")


if __name__ == "__main__":
    main()
