"""
Render panel (a) of ATLAS Figure 4 straight from the paper's own PDF
(arXiv:1207.7214), and overlay the extracted marker points, so the
extraction can be checked by eye.

Calibration approach (revised after an earlier version showed a growing
rightward/upward drift -- traced to font-metric imprecision in using text
label BOUNDING-BOX CENTERS for calibration, not the underlying data):
map the EPS source's own panel FRAME edges (found from its vector draw
commands: left/right vertical frame lines at EPS x=332/1973, spanning
EPS y=[1975,2899]) directly onto this PDF page's panel (a) frame
rectangle (found from its vector drawings: PDF x=[348.79,514.63],
y=[111.41,204.79]). Both are the SAME ROOT-drawn frame, just re-embedded
at a different absolute scale, so a single 2-point affine fit per axis
turns EPS marker coordinates directly into PDF points -- with no
dependence on axis-label text metrics at all.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pymupdf
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).parent
RESULTS_DIR = HERE / "results"

PDF_PATH = Path(sys.argv[1])
EPS_PATH = Path(sys.argv[2])
PAGE_INDEX = int(sys.argv[3]) if len(sys.argv) > 3 else 10

# EPS-space frame (from mggweighted_panel_nonorm.eps, panel (a)):
EPS_X0, EPS_X1 = 332.0, 1973.0
EPS_Y0, EPS_Y1 = 1975.0, 2899.0  # bottom, top (PostScript: y increases upward)

# PDF-space frame for this page's panel (a), from get_drawings():
PDF_X0, PDF_X1 = 348.7919921875, 514.6310424804688
PDF_Y_TOP, PDF_Y_BOTTOM = 111.40771484375, 204.7869873046875  # PDF: y increases downward


def parse_marker_blocks(text: str):
    tokens = re.findall(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?|\{[^{}]*\}|\S+", text)
    blocks = []
    for i, t in enumerate(tokens):
        if t.startswith("{") and i + 1 < len(tokens) and tokens[i + 1] == "R":
            try:
                n = int(tokens[i - 1])
            except (ValueError, IndexError):
                continue
            proc = t.strip("{} ")
            need = 2 * n
            coords = tokens[i - 1 - need:i - 1]
            if len(coords) == need and all(re.match(r"^[-+]?\d*\.?\d+$", c) for c in coords):
                pairs = [(float(coords[j]), float(coords[j + 1])) for j in range(0, len(coords), 2)]
                blocks.append((proc, n, pairs))
    return blocks


def eps_to_pdf(x_eps, y_eps):
    x_pdf = PDF_X0 + (x_eps - EPS_X0) * (PDF_X1 - PDF_X0) / (EPS_X1 - EPS_X0)
    # EPS y increases upward, PDF y increases downward: y_eps=EPS_Y1 (top) -> PDF_Y_TOP;
    # y_eps=EPS_Y0 (bottom) -> PDF_Y_BOTTOM.
    y_pdf = PDF_Y_TOP + (EPS_Y1 - y_eps) * (PDF_Y_BOTTOM - PDF_Y_TOP) / (EPS_Y1 - EPS_Y0)
    return x_pdf, y_pdf


def main():
    eps_text = EPS_PATH.read_text(errors="replace")
    blocks = parse_marker_blocks(eps_text)
    seen = set()
    unique = []
    for proc, n, pairs in blocks:
        key = (proc, tuple(pairs))
        if key not in seen:
            seen.add(key)
            unique.append((proc, n, pairs))
    m20_blocks = [b for b in unique if b[0] == "m20"]
    _, _, data_xy_eps = max(m20_blocks, key=lambda b: min(p[1] for p in b[2]))

    pdf_points = [eps_to_pdf(x, y) for x, y in data_xy_eps]

    doc = pymupdf.open(str(PDF_PATH))
    page = doc[PAGE_INDEX]
    dpi = 300
    crop = pymupdf.Rect(330, 105, 528, 210)
    pix = page.get_pixmap(dpi=dpi, clip=crop)
    img_path = RESULTS_DIR / "_fig4_panel_a_crop.png"
    pix.save(str(img_path))

    fig, ax = plt.subplots(figsize=(9, 5))
    img = plt.imread(str(img_path))
    ax.imshow(img, extent=[crop.x0, crop.x1, crop.y1, crop.y0])
    xs = [p[0] for p in pdf_points]
    ys = [p[1] for p in pdf_points]
    ax.plot(xs, ys, marker="x", color="red", ms=7, mew=1.8, ls="none",
             label="extracted points (frame-to-frame mapped)")
    ax.set_xlim(crop.x0, crop.x1)
    ax.set_ylim(crop.y1, crop.y0)
    ax.axis("off")
    ax.legend(loc="lower left", fontsize=9)
    ax.set_title("Extracted points (red x) overlaid on ATLAS Fig. 4(a), arXiv:1207.7214\n"
                 "(EPS marker coords mapped via frame-to-frame affine transform)")
    fig.tight_layout()
    fig.savefig(RESULTS_DIR / "atlas_hgg_fig4_extraction_overlay.png", dpi=200)
    print(f"Wrote {RESULTS_DIR / 'atlas_hgg_fig4_extraction_overlay.png'}")
    (RESULTS_DIR / "_fig4_panel_a_crop.png").unlink(missing_ok=True)


if __name__ == "__main__":
    main()
