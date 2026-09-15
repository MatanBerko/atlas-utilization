"""
Extract the UNWEIGHTED diphoton-mass data points from ATLAS Figure 4
(arXiv:1207.7214) by parsing the vector (PostScript) content of the
figure's own EPS source file, shipped in the paper's arXiv e-print
(mggweighted_panel_nonorm.eps, ROOT 5.32/00 output).

Why this file, and why the TOP sub-panel of it:
- The single EPS combines two stacked mini-figures: panel (a), the
  UNWEIGHTED "Events / 2 GeV" distribution with its "Events - Bkg"
  residual underneath, and panel (b), the "weights / 2 GeV" distribution
  (events weighted by ln(1+S/B) per category) below that. This is
  confirmed directly from the EPS's own axis-title text strings
  ("Events / 2 GeV" vs " weights / 2 GeV") and their vertical clip
  regions (see below) -- not assumed from the filename.
- We use ONLY the top sub-panel (the unweighted one). ATLAS's own text
  says the weighted panel exists purely for visualization; its entries
  are not Poisson counts (a weighted sum can't be fed into a Poisson
  likelihood), so PART A of this study must not use it.

How the extraction works (all done by parsing PostScript drawing
commands, not by reading pixels):
- ROOT's EPS output draws N marker points with the idiom
  `x1 y1 x2 y2 ... xN yN N { m20 } R` (`R` = `repeat`; `m20` = filled
  circle). We find this exact idiom (see parse_eps.py, an ad hoc helper
  written for this one file) and recover the (x, y) pairs in PostScript
  points. There are two "m20" (circle-marker) blocks and one "m22"
  (triangle-marker) block, each with 30 points, at three clearly
  separated vertical pixel ranges -- one per sub-panel/residual/weighted
  region. We take the block with the HIGHEST y-range, since that is
  visually and clip-wise the top-most panel (Events / 2 GeV): the panel
  clip region "2077 973 0 1975 C" found in the file sets that panel's
  y-range to [1975, 2948] PostScript units, and the topmost marker block
  (y in [2191, 2814]) falls entirely inside it.
- The x-axis is calibrated from the panel's own MAJOR tick marks: found
  as the seven `<x> 1965 m 10 Y s` lines at x = 332, 606, 879, 1153,
  1426, 1700, 1973 PostScript units, which the panel's frame and
  minor-tick spacing identify as m = 100, 110, ..., 160 GeV (a perfect
  straight line, slope 27.35 PS-units/GeV, checked below).
- The y-axis is calibrated from the six axis number labels "1000",
  "1500", ..., "3500" at y = 2184.89, 2299.88, 2414.88, 2529.87,
  2644.87, 2759.86 (the "500" label's line is dropped from the fit --
  its spacing to "1000" is visibly inconsistent with the other 5 gaps,
  by about 3%, suggesting a text-rendering offset specific to that one
  label -- excluded rather than silently averaged in).

Everything below is printed and written to
results/atlas_hgg_fig4_points.csv so it can be checked independently.
"""
from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

HERE = Path(__file__).parent
RESULTS_DIR = HERE / "results"
RESULTS_DIR.mkdir(exist_ok=True)

# The EPS lives in the paper's arXiv e-print, which is NOT committed to
# this repository (per the task instructions: reference papers go in a
# scratch folder outside the repo, never committed -- and that instruction
# is extended here to this one figure's source file too, since it is also
# paper content, not something authored for this study). To reproduce:
#   curl -L -o atlas_1207.7214_src.tar.gz https://arxiv.org/e-print/1207.7214
#   tar xzf atlas_1207.7214_src.tar.gz mggweighted_panel_nonorm.eps
#   python extract_atlas_fig4.py /path/to/mggweighted_panel_nonorm.eps
# The only committed artifact from this step is the derived
# results/atlas_hgg_fig4_points.csv (the numbers), plus this script.
if len(sys.argv) < 2:
    sys.exit("usage: extract_atlas_fig4.py <path to mggweighted_panel_nonorm.eps>")
EPS_PATH = Path(sys.argv[1])


def parse_marker_blocks(text: str):
    """Find every `<2N numbers> N { mXX } R` idiom; return list of
    (marker_style, n, [(x,y), ...])."""
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


def parse_major_xticks(text: str):
    """The 7 major tick marks on the top panel's x-axis: `<x> 1965 m 10 Y s`."""
    xs = sorted(set(float(m) for m in re.findall(r"([-\d.]+) 1965 m 10 Y s", text)))
    return xs


def parse_yaxis_labels(text: str, y_min: float, y_max: float):
    """Number labels whose y-position falls inside [y_min, y_max] -- i.e.
    physically inside the target panel's own clip region, which is what
    actually distinguishes them from the residual/weighted panels' labels
    (font size alone is reused across panels and is NOT a safe filter --
    caught by an earlier version of this script raising a KeyError, see
    git history / REPORT.md)."""
    pattern = r"([-\d.]+) ([-\d.]+) t 0 r /Helvetica findfont [\d.]+ sf 0 0 m \((\d+)\) show"
    out = []
    for x, y, val in re.findall(pattern, text):
        y = float(y)
        if y_min <= y <= y_max:
            out.append((y, int(val)))
    return sorted(set(out))


def linear_fit(xs, ys):
    """Simple least-squares y = a*x + b; returns (a, b)."""
    n = len(xs)
    mx = sum(xs) / n
    my = sum(ys) / n
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    den = sum((x - mx) ** 2 for x in xs)
    a = num / den
    b = my - a * mx
    return a, b


def main():
    text = EPS_PATH.read_text(errors="replace")

    blocks = parse_marker_blocks(text)
    # Deduplicate identical blocks (ROOT sometimes draws the same marker
    # set twice, once per redraw pass) and keep unique (proc, y-range).
    seen = set()
    unique_blocks = []
    for proc, n, pairs in blocks:
        key = (proc, tuple(pairs))
        if key not in seen:
            seen.add(key)
            unique_blocks.append((proc, n, pairs))

    print(f"Found {len(unique_blocks)} unique marker blocks:")
    for proc, n, pairs in unique_blocks:
        ys = [p[1] for p in pairs]
        print(f"  proc={proc} n={n} y-range=[{min(ys):.1f}, {max(ys):.1f}]")

    # The top (Events / 2 GeV) panel's data is the m20 block with the
    # HIGHEST y-range (panel clip region starts at y=1975; this block's
    # y-values all lie above that).
    m20_blocks = [b for b in unique_blocks if b[0] == "m20"]
    top_block = max(m20_blocks, key=lambda b: min(p[1] for p in b[2]))
    proc, n, data_xy = top_block
    print(f"\nUsing block proc={proc} n={n}, y-range="
          f"[{min(p[1] for p in data_xy):.1f}, {max(p[1] for p in data_xy):.1f}] "
          "as the unweighted top-panel data points.")

    # --- x-axis calibration (mass) ---
    xticks = parse_major_xticks(text)
    print(f"\nMajor x-tick PostScript positions: {xticks}")
    assert len(xticks) == 7, f"expected 7 major x-ticks (100..160 GeV), got {len(xticks)}"
    tick_masses = [100.0, 110.0, 120.0, 130.0, 140.0, 150.0, 160.0]
    a_x, b_x = linear_fit(xticks, tick_masses)
    resid_x = [abs((a_x * x + b_x) - m) for x, m in zip(xticks, tick_masses)]
    print(f"x-calibration: mass = {a_x:.6f} * x_ps + {b_x:.4f}  "
          f"(max residual on the 7 fit points: {max(resid_x):.4f} GeV)")

    # --- y-axis calibration (event count) ---
    # Restrict to labels physically inside the top panel's clip region
    # (y in [1975, 2948]); this is what actually separates them from the
    # residual/weighted panels' own axis labels, not font size.
    ylabels = parse_yaxis_labels(text, 1975.0, 2948.0)
    print(f"\nTop-panel y-axis number labels found (y_ps, value): {ylabels}")
    value_to_y = {v: y for y, v in ylabels}
    # Drop the "500" label: its spacing to "1000" is ~3% off the otherwise
    # perfectly consistent 115.0-unit/500-count spacing among the rest --
    # excluded explicitly, not silently averaged in.
    ylabels_used = [(y, v) for y, v in ylabels if v != 500]
    y_ps = [y for y, v in ylabels_used]
    y_val = [v for y, v in ylabels_used]
    a_y, b_y = linear_fit(y_ps, y_val)
    resid_y = [abs((a_y * y + b_y) - v) for y, v in zip(y_ps, y_val)]
    print(f"y-calibration: count = {a_y:.6f} * y_ps + {b_y:.4f}  "
          f"(max residual on the {len(y_ps)} fit points: {max(resid_y):.4f} events)")
    if 500 in value_to_y:
        y500 = value_to_y[500]
        pred500 = a_y * y500 + b_y
        print(f"('500' label at y={y500} excluded from the fit; its predicted "
              f"value from the fit would be {pred500:.1f}, a "
              f"{abs(pred500-500):.1f}-event discrepancy vs. the other "
              f"{len(y_ps)} labels' internal consistency of <{max(resid_y):.1f} events)")

    # --- apply calibration to the 30 data points ---
    rows = []
    max_int_dev = 0.0
    for x_ps, y_ps_val in sorted(data_xy, key=lambda p: p[0]):
        mass = a_x * x_ps + b_x
        count_raw = a_y * y_ps_val + b_y
        count_round = round(count_raw)
        dev = abs(count_raw - count_round)
        max_int_dev = max(max_int_dev, dev)
        bin_low = round(mass) - 1.0
        bin_high = round(mass) + 1.0
        rows.append((bin_low, bin_high, count_round, count_raw, dev))

    print(f"\n{len(rows)} bins extracted. Largest deviation from an integer "
          f"before rounding: {max_int_dev:.3f} events.")
    total = sum(r[2] for r in rows)
    print(f"Total events in range [{rows[0][0]:.0f}, {rows[-1][1]:.0f}] GeV: {total}")

    with open(RESULTS_DIR / "atlas_hgg_fig4_points.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["bin_low_GeV", "bin_high_GeV", "count", "count_raw_before_rounding",
                    "deviation_from_integer", "source"])
        for bl, bh, c, craw, dev in rows:
            w.writerow([bl, bh, c, f"{craw:.3f}", f"{dev:.3f}",
                        "vector extraction of mggweighted_panel_nonorm.eps "
                        "(ATLAS arXiv:1207.7214 e-print), top (unweighted) panel"])

    print(f"\nWrote {RESULTS_DIR / 'atlas_hgg_fig4_points.csv'}")
    return rows, (a_x, b_x), (a_y, b_y), data_xy


if __name__ == "__main__":
    main()
