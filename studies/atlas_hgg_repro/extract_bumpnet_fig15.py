"""
Extract BumpNet's own Z_LR (bin-by-bin likelihood-ratio significance,
signed) curve from Figure 15 of arXiv:2501.05603, by parsing the PDF's
vector drawing commands directly (matplotlib output; unlike the ATLAS
figure this is a native PDF, not an EPS needing separate extraction) --
not by reading pixels.

Also re-extracts the top-panel data markers as an independent cross-check
against extract_atlas_fig4.py's ATLAS-source extraction (they should agree
closely, since BumpNet's own Fig. 15 caption says its points are "extracted
from Figure 4" of the same ATLAS paper).

Key finding, confirmed by the vector data itself (not assumed): the Z_LR
curve's underlying vertices span 30 points on the SAME x-grid as our own
30-bin, 100-160 GeV ATLAS extraction (mass = 101, 103, ..., 159 GeV) -- the
LAST TWO points (at 157 and 159 GeV) lie just past the panel's drawn frame
edge (~156 GeV) and are invisible in the rendered figure, but are present
in the underlying vector path. So BumpNet's own calculation was NOT
restricted to 100-156 GeV; only the PLOT's visible window was cropped
there. See REPORT.md for how this resolves the range question.
"""
from __future__ import annotations

import csv
from pathlib import Path

import pymupdf

HERE = Path(__file__).parent
RESULTS_DIR = HERE / "results"
RESULTS_DIR.mkdir(exist_ok=True)

# x-axis calibration (shared by all 3 stacked panels): major tick at
# mass=100 GeV sits at the frame's own left edge (confirmed: the "100"
# text label's center, 197.13, coincides exactly with the top/middle/
# bottom panel frame rectangles' left edge found via get_drawings()).
X0_PDF, MASS_AT_X0 = 197.130859375, 100.0
X_SLOPE_PDF_PER_GEV = None  # computed below from tick spacing


def mass_from_x(x_pdf: float, slope: float) -> float:
    return MASS_AT_X0 + (x_pdf - X0_PDF) / slope


def main(pdf_path: str, page_index: int = 21):
    doc = pymupdf.open(pdf_path)
    page = doc[page_index]
    words = page.get_text("words")
    drawings = page.get_drawings()

    # --- x-axis calibration from the shared bottom-axis tick labels ---
    x_ticks = {}
    for x0, y0, x1, y1, text, *_ in words:
        if 185 <= x0 <= 410 and 400 <= y0 <= 403 and text.isdigit():
            x_ticks[int(text)] = (x0 + x1) / 2
    xs = sorted(x_ticks)
    diffs = [(x_ticks[xs[i + 1]] - x_ticks[xs[i]]) / (xs[i + 1] - xs[i]) for i in range(len(xs) - 1)]
    x_slope = sum(diffs) / len(diffs)
    print(f"x-axis ticks found: {x_ticks}")
    print(f"x-calibration: {x_slope:.5f} PDF-pt/GeV (mass=100 at x={X0_PDF})")

    # --- y-axis calibration for the BOTTOM (significance) panel, from its
    # own major tick marks (length ~5pt, vs ~2.5pt minor ticks) and the
    # y=0 reference dashed line found directly in the drawings. ---
    major_yticks = sorted({round(p0.y, 3) for d in drawings for it in d["items"]
                            if it[0] == "l" and abs(it[1].y - it[2].y) < 0.05
                            and 195 <= it[1].x <= 198 and abs(it[2].x - it[1].x) > 4.5
                            and 333 <= it[1].y <= 405
                            for p0 in [it[1]]})
    print(f"Bottom-panel major y-ticks (PDF pt): {major_yticks}")
    tick_gaps = [major_yticks[i + 1] - major_yticks[i] for i in range(len(major_yticks) - 1)]
    y_gap = sum(tick_gaps) / len(tick_gaps)
    # The y=0 reference line (dashed black horizontal line spanning the
    # full panel width) pins the zero point exactly.
    y_zero = None
    for d in drawings:
        dashes = d.get("dashes")
        # `dashes` is a STRING of the form "[<pattern>] <phase>", e.g.
        # "[] 0" for a solid line or "[2.77 1.20] 0" for an actually
        # dashed one -- not a list/array, and NOT empty even for a solid
        # line ("[] 0" has length 4). A naive `dashes not in (None, [])`
        # or `len(dashes) > 0` both silently pick the wrong (solid) line;
        # found by manually re-deriving the expected +4.2 peak and noticing
        # every extracted value came out negative, then inspecting
        # `repr(d.get("dashes"))` directly to see its real type/format.
        has_dashes = dashes is not None and not dashes.startswith("[] ")
        for it in d["items"]:
            if it[0] == "l" and abs(it[1].y - it[2].y) < 0.01 and it[1].x < 198 and it[2].x > 410:
                if d.get("color") == (0.0, 0.0, 0.0) and has_dashes:
                    y_zero = it[1].y
    print(f"y=0 reference line at y_pdf={y_zero}, tick spacing={y_gap:.4f} pt per 2 sig. units")
    sig_per_pt = 2.0 / y_gap

    def sig_from_y(y_pdf: float) -> float:
        return (y_zero - y_pdf) * sig_per_pt

    # --- Find the Z_LR (blue, dashed) curve: the long multi-segment path ---
    x0f, y0f, x1f, y1f = 195.0, 333.0, 414.0, 405.0
    blue_paths = [d for d in drawings if d.get("color") == (0.0, 0.0, 1.0)
                  and x0f <= d["rect"].x0 <= x1f and y0f <= d["rect"].y0 <= y1f
                  and len(d["items"]) > 5]
    if len(blue_paths) != 1:
        raise RuntimeError(f"expected exactly 1 long blue path, found {len(blue_paths)}")
    zlr_path = blue_paths[0]
    pts_pdf = [zlr_path["items"][0][1]] + [it[2] for it in zlr_path["items"]]
    print(f"Z_LR curve: {len(pts_pdf)} vertices")

    rows = []
    for p in pts_pdf:
        mass = mass_from_x(p.x, x_slope)
        sig = sig_from_y(p.y)
        rows.append((mass, sig, p.x, p.y))
    for mass, sig, x, y in rows:
        in_frame = "yes" if x <= 412.5 + 0.5 else "no (beyond visible frame)"
        print(f"  mass={mass:6.2f} GeV  Z_LR={sig:6.3f}   (visible in figure: {in_frame})")

    with open(RESULTS_DIR / "bumpnet_fig15_zlr_curve.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["mass_GeV", "z_lr", "visible_in_rendered_figure"])
        for mass, sig, x, y in rows:
            w.writerow([f"{mass:.3f}", f"{sig:.4f}", "yes" if x <= 412.5 + 0.5 else "no"])
    print(f"\nWrote {RESULTS_DIR / 'bumpnet_fig15_zlr_curve.csv'}")

    # --- Cross-check: top-panel data markers vs our own ATLAS extraction ---
    top_markers = []
    for d in drawings:
        r = d["rect"]
        if 197 <= r.x0 <= 413 and 127 <= r.y0 <= 266 and r.width < 4 and 2.5 < r.width:
            top_markers.append(((r.x0 + r.x1) / 2, (r.y0 + r.y1) / 2))
    top_markers.sort()
    # Drop the legend-marker outlier (the one whose y is far from the smooth
    # monotonic trend of its neighbours), matching what was found by eye
    # during development -- kept as an explicit, documented filter, not
    # silently dropped.
    cleaned = []
    for i, (x, y) in enumerate(top_markers):
        neighbours_y = [top_markers[j][1] for j in (i - 1, i + 1) if 0 <= j < len(top_markers)]
        if neighbours_y and min(abs(y - ny) for ny in neighbours_y) > 15:
            print(f"  dropping legend-marker outlier at x={x:.2f}, y={y:.2f}")
            continue
        cleaned.append((x, y))
    print(f"\nTop-panel data markers found: {len(top_markers)} raw, {len(cleaned)} after dropping outliers")

    with open(RESULTS_DIR / "bumpnet_fig15_data_points_xcheck.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["mass_GeV_bin_center", "x_pdf", "y_pdf"])
        for x, y in cleaned:
            w.writerow([f"{mass_from_x(x, x_slope):.3f}", f"{x:.3f}", f"{y:.3f}"])
    print(f"Wrote {RESULTS_DIR / 'bumpnet_fig15_data_points_xcheck.csv'} "
          "(x-check only; y not calibrated to events -- see REPORT.md)")


if __name__ == "__main__":
    import sys
    main(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 21)
