"""
Self-checks for studies/m0m1j0_cms/histograms.py's to_writable_th1f /
verify_written_th1f (Step 2 requirement A: write TH1F, not TH1D, matching
the shared pipeline's own histogram class).

uproot's plain `file[key] = (values, edges)` shortcut always writes a
TH1D regardless of dtype (confirmed directly, see histograms.py's module
docstring) -- to_writable_th1f uses uproot.writing.identify.to_TH1x
instead, which DOES key its output class off the data array's dtype.
This test writes a real ROOT file, reads it back, and checks both the
class and the bin contents -- and separately checks that
verify_written_th1f actually raises on a genuine mismatch (not just that
it passes on correct data).

Run directly: python studies/m0m1j0_cms/tests/test_th1f_writer.py
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

import numpy as np  # noqa: E402
import uproot  # noqa: E402

from studies.m0m1j0_cms import histograms  # noqa: E402

FAILURES = []


def check(name: str, condition: bool, detail: str = ""):
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {name}" + (f" -- {detail}" if detail and not condition else ""))
    if not condition:
        FAILURES.append(name)


def main():
    values, edges = histograms.make_fixed_grid_histogram(np.array([5.0, 15.0, 15.0, 25.0]))

    with tempfile.TemporaryDirectory() as tmp:
        root_path = str(Path(tmp) / "test.root")
        th1f = histograms.to_writable_th1f(values, edges, "ROI_mass_test_width_10")
        with uproot.recreate(root_path) as f:
            f["ROI_mass_test_width_10"] = th1f

        f2 = uproot.open(root_path)
        h = f2["ROI_mass_test_width_10"]
        check("written histogram class is TH1F, not TH1D", h.classname == "TH1F", f"got {h.classname}")
        check("bin contents dtype is float32", h.values().dtype == np.float32, f"got {h.values().dtype}")
        check("bin contents match the float64 input values", np.allclose(h.values(), values), f"got {h.values()}")
        check("read-back name matches the assignment key", h.name == "ROI_mass_test_width_10", f"got {h.name}")
        check("edges match the input fixed grid", np.array_equal(h.axis().edges(), edges))

        # Display-range parity with the shared pipeline's trim_empty_tail
        # (services/pipelines/histograms_pipeline.py:26-41) -- see
        # histograms.py's own module-level derivation. Values [5,15,15,25]
        # bin into make_fixed_grid_histogram's 10-GeV grid as: bin1 (0-10)
        # gets the 5.0 -> 1 entry, bin2 (10-20) gets both 15.0s -> 2
        # entries, bin3 (20-30) gets the 25.0 -> 1 entry, nothing after --
        # so the last bin with content > 0 is ROOT bin 3 (1-based).
        expected_last_bin = 3
        xaxis = h.member("fXaxis")
        check("fFirst is 1 (matches trim_empty_tail's own SetRangeUser(Xmin, ...) call)",
              xaxis.member("fFirst") == 1, f"got {xaxis.member('fFirst')}")
        check(f"fLast is {expected_last_bin} (the last bin with content > 0)",
              xaxis.member("fLast") == expected_last_bin, f"got {xaxis.member('fLast')}")
        check("kAxisRange (bit 11) is set on the axis's TObject fBits",
              bool(xaxis.member("@fBits") & (1 << 11)), f"got fBits={xaxis.member('@fBits'):#x}")

        histograms.verify_written_th1f(root_path, {"ROI_mass_test_width_10": values})
        check("verify_written_th1f passes on correct data (reached here without raising)", True)

        # All-empty histogram: trim_empty_tail is a no-op (its own
        # `if last_filled > 0:` guard never fires), so the axis must be
        # left in the untouched-TAxis default: fFirst=0, fLast=0,
        # kAxisRange NOT set -- not "cropped to nothing".
        empty_values, empty_edges = histograms.make_fixed_grid_histogram(np.array([]))
        empty_path = str(Path(tmp) / "test_empty.root")
        empty_th1f = histograms.to_writable_th1f(empty_values, empty_edges, "ROI_mass_empty_width_10")
        with uproot.recreate(empty_path) as f:
            f["ROI_mass_empty_width_10"] = empty_th1f
        h_empty = uproot.open(empty_path)["ROI_mass_empty_width_10"]
        xaxis_empty = h_empty.member("fXaxis")
        check("all-empty histogram: fFirst is 0 (untouched default, not cropped)",
              xaxis_empty.member("fFirst") == 0, f"got {xaxis_empty.member('fFirst')}")
        check("all-empty histogram: fLast is 0 (untouched default)",
              xaxis_empty.member("fLast") == 0, f"got {xaxis_empty.member('fLast')}")
        check("all-empty histogram: kAxisRange is NOT set",
              not bool(xaxis_empty.member("@fBits") & (1 << 11)), f"got fBits={xaxis_empty.member('@fBits'):#x}")
        histograms.verify_written_th1f(empty_path, {"ROI_mass_empty_width_10": empty_values})
        check("verify_written_th1f passes on the all-empty histogram too", True)

        try:
            histograms.verify_written_th1f(root_path, {"ROI_mass_test_width_10": values + 1000.0})
            check("verify_written_th1f raises on a genuine mismatch", False, "did not raise")
        except AssertionError:
            check("verify_written_th1f raises on a genuine mismatch", True)

        try:
            histograms.verify_written_th1f(root_path, {"does_not_exist": values})
            check("verify_written_th1f raises on a missing histogram", False, "did not raise")
        except AssertionError:
            check("verify_written_th1f raises on a missing histogram", True)

    print()
    if FAILURES:
        print(f"{len(FAILURES)} FAILURE(S): {FAILURES}")
        sys.exit(1)
    else:
        print("All TH1F-writer self-checks passed.")


if __name__ == "__main__":
    main()
