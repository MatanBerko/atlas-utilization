#!/usr/bin/env python
"""
Read-only count of the MC pilot histograms, by light-jet multiplicity and by
whether a histogram carries a negative bin.

Purpose: size the options for what a delivery would contain if high-jet-
multiplicity final states and/or histograms with negative bins were dropped.
This script COUNTS ONLY. It changes nothing, applies nothing, and expresses
no preference between the options.

Every input ROOT file is opened read-only; the only thing written is one
JSON at --out.

Definitions, stated because the numbers depend on them:

  final state   the `_cat_<...>` part of the histogram name, e.g. the
                `0ex_2mx_5jx_1bx` of
                `ROI_mass_m0m1_cat_0ex_2mx_5jx_1bx_width_10.0`.
  light jets    the `<n>` of the `_<n>jx_` token in that part. The regex
                accepts multi-digit counts, so a `10jx` final state is read
                as 10 and not as 1.
  filled range  first..last bin that actually received an entry. For a
                weighted MC histogram (TH1D with Sumw2) that is `error > 0`,
                which is the honest test: a bin whose positive and negative
                weights cancel exactly has content 0 but WAS filled. For an
                unweighted data histogram (TH1F, no Sumw2) the error is just
                sqrt(content), so `content != 0` is used instead.
  negative bin  a bin with content < 0 lying inside that filled range. Bins
                outside it are structurally empty and are not counted.

Run:
    python studies/cms_mc_weights_v3/counts/count_hist_options.py \
        --files <a.root> <b.root> ... --out <dir>/hist_counts.json
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone

import numpy as np
import uproot

# `ROI_mass_<combo>_cat_<final state>_width_<w>` -> the final-state part.
CAT_PATTERN = re.compile(r"_cat_(.+?)_width_")
# the light-jet token; multi-digit counts are deliberately allowed
JET_PATTERN = re.compile(r"_(\d+)jx(?:_|$)")

JET_GROUPS = ["0", "1", "2", "3", "4", "5+"]


def jet_group(n_jets: int) -> str:
    return str(n_jets) if n_jets < 5 else "5+"


def analyse(path: pathlib.Path) -> dict:
    total = 0
    skipped_no_cat = []
    skipped_no_jets = []
    final_states = set()
    fs_by_group = defaultdict(set)
    by_group = Counter()
    neg_by_group = Counter()
    neg_names = []
    classnames = Counter()
    n_bins_negative_total = 0

    with uproot.open(str(path)) as f:
        for key in sorted({k.split(";")[0] for k in f.keys()}):
            obj = f[key]
            cls = getattr(obj, "classname", "")
            if not cls.startswith("TH1"):
                continue
            total += 1
            classnames[cls] += 1

            m = CAT_PATTERN.search(key)
            if not m:
                skipped_no_cat.append(key)
                continue
            fs = m.group(1)
            final_states.add(fs)

            jm = JET_PATTERN.search(fs)
            if not jm:
                skipped_no_jets.append(key)
                continue
            n_jets = int(jm.group(1))
            grp = jet_group(n_jets)
            by_group[grp] += 1
            fs_by_group[grp].add(fs)

            values = obj.values(flow=False)
            errors = obj.errors(flow=False)
            # TH1D written with Sumw2 -> error > 0 marks a filled bin.
            # TH1F without Sumw2 -> error is sqrt(content), so fall back to
            # content != 0, which for unweighted counts is the same thing.
            if cls == "TH1D":
                filled = np.nonzero(errors > 0)[0]
            else:
                filled = np.nonzero(values != 0)[0]
            if filled.size == 0:
                continue
            lo, hi = int(filled[0]), int(filled[-1])
            window = values[lo:hi + 1]
            n_neg = int(np.count_nonzero(window < 0))
            if n_neg:
                neg_by_group[grp] += 1
                n_bins_negative_total += n_neg
                neg_names.append({"histogram": key, "jet_group": grp,
                                  "n_negative_bins": n_neg,
                                  "most_negative": float(window.min())})

    classified = sum(by_group.values())
    ge3 = sum(by_group[g] for g in ("3", "4", "5+"))
    ge4 = sum(by_group[g] for g in ("4", "5+"))
    neg_total = sum(neg_by_group.values())
    neg_ge3 = sum(neg_by_group[g] for g in ("3", "4", "5+"))
    neg_le2 = sum(neg_by_group[g] for g in ("0", "1", "2"))
    neg_ge4 = sum(neg_by_group[g] for g in ("4", "5+"))

    neg_names.sort(key=lambda r: -r["n_negative_bins"])

    return {
        "file": str(path),
        "n_histograms_total": total,
        "classnames": dict(classnames),
        "n_histograms_classified_by_jets": classified,
        "n_histograms_without_cat_in_name": len(skipped_no_cat),
        "n_histograms_without_jet_token": len(skipped_no_jets),
        "examples_without_jet_token": skipped_no_jets[:5],
        "n_distinct_final_states": len(final_states),
        "by_jet_group": {g: int(by_group[g]) for g in JET_GROUPS},
        "final_states_by_jet_group": {g: len(fs_by_group[g]) for g in JET_GROUPS},
        "n_ge3_light_jets": ge3,
        "n_ge4_light_jets": ge4,
        "n_with_negative_bin": neg_total,
        "n_negative_bins_summed": n_bins_negative_total,
        "negative_by_jet_group": {g: int(neg_by_group[g]) for g in JET_GROUPS},
        "n_with_negative_bin_ge3_jets": neg_ge3,
        "n_with_negative_bin_ge4_jets": neg_ge4,
        "n_with_negative_bin_0to2_jets": neg_le2,
        "worst_ten_negative": neg_names[:10],
        "options": {
            "a_everything": classified,
            "b_drop_ge3_light_jets": classified - ge3,
            "c_drop_ge4_light_jets": classified - ge4,
            "d_drop_any_negative_bin": classified - neg_total,
            # b and d together: a histogram removed by BOTH rules must not be
            # subtracted twice, hence the explicit 0-2-jet negative count.
            "e_drop_ge3_light_jets_and_any_negative_bin":
                classified - ge3 - neg_le2,
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--files", nargs="+", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    report = {
        "what": "read-only count of MC pilot histograms by light-jet "
                "multiplicity and negative-bin status",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "definitions": {
            "final_state": "the _cat_<...>_width_ part of the histogram name",
            "light_jets": "the <n> of the _<n>jx_ token; multi-digit allowed",
            "filled_range": "first..last bin with an entry (error > 0 for "
                            "TH1D with Sumw2; content != 0 for TH1F)",
            "negative_bin": "content < 0 inside the filled range",
            "option_e": "drop >=3-jet final states AND any remaining "
                        "histogram with a negative bin; computed without "
                        "double-subtracting histograms removed by both",
        },
        "files": {},
    }
    for raw in args.files:
        path = pathlib.Path(raw)
        if not path.exists():
            raise SystemExit(f"missing input: {path}")
        res = analyse(path)
        report["files"][path.name] = res
        print(f"\n=== {path.name} ===")
        print(f"  histograms            : {res['n_histograms_total']:,} "
              f"({res['classnames']})")
        print(f"  distinct final states : {res['n_distinct_final_states']}")
        print(f"  by light jets         : " +
              "  ".join(f"{g}={res['by_jet_group'][g]:,}" for g in JET_GROUPS))
        print(f"  >=3 jets {res['n_ge3_light_jets']:,}   "
              f">=4 jets {res['n_ge4_light_jets']:,}")
        print(f"  with a negative bin   : {res['n_with_negative_bin']:,} "
              f"({res['n_negative_bins_summed']:,} bins)")
        print(f"     by light jets      : " +
              "  ".join(f"{g}={res['negative_by_jet_group'][g]:,}" for g in JET_GROUPS))
        o = res["options"]
        print(f"  options: a={o['a_everything']:,}  "
              f"b={o['b_drop_ge3_light_jets']:,}  "
              f"c={o['c_drop_ge4_light_jets']:,}  "
              f"d={o['d_drop_any_negative_bin']:,}  "
              f"e={o['e_drop_ge3_light_jets_and_any_negative_bin']:,}")

    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\nwrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
