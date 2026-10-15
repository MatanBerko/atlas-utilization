#!/usr/bin/env python
"""
Which panel of CMS-SMP-19-009 (arXiv:2205.02872) Fig. 4 were the "published
MG5_aMC" prediction/measurement ratios of jets/HANDOFF_JETS.md read from?

Reads the paper's own LaTeX source and figure PDFs (the arXiv e-print,
unpacked beforehand -- this script downloads nothing):

    curl -sSL https://arxiv.org/e-print/2205.02872 -o src.tgz
    mkdir src && tar -xzf src.tgz -C src

and, read-only:
  1. quotes the Fig. 4 caption from the .tex (which panel is inclusive);
  2. reads each panel's x-axis bin labels from the PDF text ("N_jets >= k"
     vs "N_jets = k");
  3. extracts the plotted prediction/measurement ratio of the NLO FxFx and
     LO MLM ratio panels from the vector drawing (centre of each bin's
     uncertainty box, in the axis coordinates set by the 0.5 / 1.0 / 1.5 ticks);
  4. compares both panels with the values read by eye in the jet study
     (9927ca6:studies/cms_mc_weights_v3/jets/evidence/hepdata_smp19009.json,
     key prediction_over_data).

Run:  python studies/cms_mc_weights_v3/probe/check_smp19009_fig4_panels.py <src dir> \
          [--out studies/cms_mc_weights_v3/evidence/smp19009_fig4_panel_check_20261015.json]
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import subprocess
import sys
import zlib

STUDY_DIR = pathlib.Path(__file__).resolve().parents[1]
REPO_ROOT = STUDY_DIR.parents[1]
DEFAULT_OUT = STUDY_DIR / "evidence" / "smp19009_fig4_panel_check_20261015.json"
STUDY_COMMIT = "9927ca6"
HEPDATA_EVIDENCE = "studies/cms_mc_weights_v3/jets/evidence/hepdata_smp19009.json"

# Ratio panels of the figure, top to bottom (clip-box y range in PDF points,
# y of the 1.0 tick, points per unit ratio from the 0.5 -> 1.0 -> 1.5 ticks).
PANELS = {
    "MG5_aMC NLO FxFx (<=2j NLO + PS)": (284.224, 391.675, 337.95),
    "MG5_aMC LO MLM (<=4j LO + PS)": (176.774, 284.224, 230.5),
    "GENEVA": (69.323, 176.774, 123.05),
}
UNIT = 67.158        # points per 1.0 of ratio (304.371 -> 337.95 is 0.5)
X0, BIN_W = 89.0079, 48.1512


def streams(pdf: pathlib.Path):
    raw = pdf.read_bytes()
    for m in re.finditer(rb"stream\r?\n(.*?)\r?\nendstream", raw, re.S):
        try:
            yield zlib.decompress(m.group(1)).decode("latin1")
        except zlib.error:
            continue


def panel_page(pdf: pathlib.Path) -> str:
    for text in streams(pdf):
        if "Measurement" in text:
            return text
    raise SystemExit(f"{pdf}: no page stream with the ratio-axis label found")


def bin_labels(text: str) -> list[str]:
    # the >= glyph is drawn in the Symbol font as byte 0xB3 ('³' in latin1)
    labels = re.findall(r"\((= \d|³| \d)\) Tj", text)
    return labels[:20]


def axis_label_order(text: str) -> dict:
    # the ratio-axis title is rotated (0 1 -1 0 x y cm): the text further left
    # (smaller x) is the one above the fraction bar, i.e. the numerator.
    pos = {}
    for word in ("Measurement", "Prediction"):
        m = re.search(r"0 1 -1 0 ([\d.]+) ([\d.]+) cm BT /F\d+ [\d.]+ Tf \(" + word + r"\) Tj", text)
        pos[word] = float(m.group(1)) if m else None
    num = min(pos, key=lambda k: pos[k]) if all(pos.values()) else None
    den = max(pos, key=lambda k: pos[k]) if all(pos.values()) else None
    return {"x_positions": pos, "numerator": num, "denominator": den}


def ratios(text: str) -> dict:
    rects = [tuple(map(float, r)) for r in re.findall(r"([\d.]+) ([\d.]+) ([\d.]+) ([\d.]+) re b\*", text)]
    out = {}
    for name, (lo, hi, one) in PANELS.items():
        per_bin = {}
        for (x, y, w, h) in rects:
            if abs(w - BIN_W) > 0.01 or not (lo <= y <= hi):
                continue
            b = round((x - X0) / BIN_W)
            per_bin.setdefault(b, set()).add(round(1.0 + ((y + h / 2) - one) / UNIT, 3))
        out[name] = {str(b): sorted(v) for b, v in sorted(per_bin.items())}
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("src", help="unpacked arXiv e-print directory of 2205.02872")
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    args = ap.parse_args()
    src = pathlib.Path(args.src)

    tex = next(src.glob("SMP-19-009*.tex")).read_text(encoding="latin1")
    m = re.search(r"\\includegraphics\[[^]]*\]\{Figure_004-a\.pdf\}.*?\\caption\{(.*?)\\unfcaption\}", tex, re.S)
    caption = m.group(1).strip() if m else None

    study = json.loads(subprocess.run(["git", "show", f"{STUDY_COMMIT}:{HEPDATA_EVIDENCE}"],
                                      cwd=REPO_ROOT, capture_output=True, check=True).stdout)
    read_by_eye = study["prediction_over_data"]

    panels = {}
    for tag in ("a", "b"):
        text = panel_page(src / f"Figure_004-{tag}.pdf")
        extracted = ratios(text)
        cmp = {}
        for name, eye in read_by_eye.items():
            diffs = {}
            for k, v in eye.items():
                vals = extracted.get(name, {}).get(k)
                if vals:
                    diffs[k] = round(v - vals[0], 3)
            cmp[name] = {"diff_read_by_eye_minus_extracted": diffs,
                         "max_abs_diff": max(abs(d) for d in diffs.values()) if diffs else None}
        panels[f"Figure_004-{tag}"] = {
            "x_axis_bin_labels_first": bin_labels(text),
            "ratio_axis": axis_label_order(text),
            "prediction_over_measurement_extracted": extracted,
            "comparison_with_jet_study": cmp,
        }

    best = {name: min(panels, key=lambda p: panels[p]["comparison_with_jet_study"][name]["max_abs_diff"])
            for name in read_by_eye}
    payload = {
        "what": "Which Fig. 4 panel of CMS-SMP-19-009 the jet study's read-off prediction/data "
                "ratios match (read-only check of the paper's own source files)",
        "paper": "arXiv:2205.02872 (CMS-SMP-19-009)",
        "source": "https://arxiv.org/e-print/2205.02872",
        "fig4_caption": caption,
        "study_values_from": f"{STUDY_COMMIT}:{HEPDATA_EVIDENCE} key prediction_over_data",
        "panels": panels,
        "panel_matching_the_study_values": best,
        "method_note": "Ratios are the centres of the drawn uncertainty boxes, converted with the "
                       "0.5/1.0/1.5 tick positions; good to about 0.001 in ratio.",
    }
    pathlib.Path(args.out).write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
                                      encoding="utf-8")
    print(f"wrote {args.out}")
    print("caption:", caption)
    for p, v in panels.items():
        print(p, "labels:", v["x_axis_bin_labels_first"][:6], "ratio axis:",
              v["ratio_axis"]["numerator"], "/", v["ratio_axis"]["denominator"])
        for name, c in v["comparison_with_jet_study"].items():
            print(f"   {name}: max |read-by-eye - extracted| = {c['max_abs_diff']}  {c['diff_read_by_eye_minus_extracted']}")
    print("panel matching the study's values:", best)
    return 0


if __name__ == "__main__":
    sys.exit(main())
