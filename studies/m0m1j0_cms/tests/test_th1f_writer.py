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

        histograms.verify_written_th1f(root_path, {"ROI_mass_test_width_10": values})
        check("verify_written_th1f passes on correct data (reached here without raising)", True)

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
