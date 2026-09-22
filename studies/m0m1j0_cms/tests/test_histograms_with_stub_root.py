"""
Exercises studies/m0m1j0_cms/histograms.py (and, through it, the REAL
services/pipelines/histograms_pipeline.py functions it imports --
FIXED_MASS_MIN_GEV/MAX_GEV, _fill_mass, trim_empty_tail,
_convert_to_bumpnet_name) against a minimal in-memory TH1F/TFile stub, on
this Windows dev machine where PyROOT and `fcntl` are not installed.

This is NOT a substitute for running on the real cluster (the stub does
not reproduce ROOT's exact floating-point binning internals) -- it exists
only to catch integration bugs between studies/m0m1j0_cms/histograms.py
and the real, unmodified shared module before ever touching the cluster.
Both stubbed modules are inserted into sys.modules BEFORE importing
anything that needs them, and this script does not modify
services/pipelines/histograms_pipeline.py in any way -- it is imported
completely unchanged; only its own `import ROOT` / `import fcntl` lines
resolve to these stand-ins.

Run directly: python studies/m0m1j0_cms/tests/test_histograms_with_stub_root.py
"""
from __future__ import annotations

import sys
import types
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))


# --- Minimal ROOT stub: enough of TH1F's interface for _fill_mass and
# trim_empty_tail (services/pipelines/histograms_pipeline.py:26-41, 67-72)
# to run unmodified against it. -----------------------------------------
class _FakeAxis:
    def __init__(self, xmin, xmax):
        self._xmin = xmin
        self._xmax = xmax
        self._range = (xmin, xmax)

    def SetRangeUser(self, lo, hi):
        self._range = (lo, hi)

    def GetXmin(self):
        return self._xmin

    def GetXmax(self):
        return self._xmax


class FakeTH1F:
    def __init__(self, name, title, nbins, xmin, xmax):
        self.name = name
        self.title = title
        self.nbins = nbins
        self.xmin = xmin
        self.xmax = xmax
        self.bin_width = (xmax - xmin) / nbins
        self.contents = [0.0] * (nbins + 2)  # ROOT convention: 0=underflow, nbins+1=overflow
        self._axis = _FakeAxis(xmin, xmax)

    def Sumw2(self):
        pass

    def Fill(self, value):
        if value < self.xmin:
            self.contents[0] += 1.0
            return
        if value >= self.xmax:
            self.contents[self.nbins + 1] += 1.0
            return
        b = int((value - self.xmin) / self.bin_width) + 1
        self.contents[b] += 1.0

    def GetNbinsX(self):
        return self.nbins

    def GetBinContent(self, b):
        return self.contents[b]

    def GetBinLowEdge(self, b):
        return self.xmin + (b - 1) * self.bin_width

    def GetXaxis(self):
        return self._axis

    def InheritsFrom(self, _cls):
        return True

    def Write(self, *_a, **_kw):
        pass


fake_root = types.ModuleType("ROOT")
fake_root.TH1F = FakeTH1F
fake_root.TObject = types.SimpleNamespace(kOverwrite=1)
fake_root.TFile = object  # not exercised by this test
sys.modules["ROOT"] = fake_root
sys.modules["fcntl"] = types.ModuleType("fcntl")  # unused attributes are fine; not called here

import awkward as ak  # noqa: E402
import numpy as np  # noqa: E402

from studies.m0m1j0_cms import histograms  # noqa: E402

FAILURES = []


def check(name: str, condition: bool, detail: str = ""):
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {name}" + (f" -- {detail}" if detail and not condition else ""))
    if not condition:
        FAILURES.append(name)


def main():
    check(
        "FIXED_MASS grid is 0-10000 GeV imported from the real shared module",
        histograms.FIXED_MASS_MIN_GEV == 0.0 and histograms.FIXED_MASS_MAX_GEV == 10000.0,
    )
    check("bin width is 10 GeV -> 1000 bins", histograms._n_bins() == 1000)

    # 12 events: 10 with final state "0e_2m_1j_0g_0t_0b" (>= MIN_EVENTS
    # would need 100 normally -- lower the threshold here to make a small
    # synthetic set exercise both the "kept" and "dropped" branches).
    histograms.MIN_EVENTS_PER_FINAL_STATE = 5

    obj_record = ak.Array({
        "Electrons": [[] for _ in range(12)],
        "Muons": [[1, 2]] * 10 + [[1, 2, 3]] * 2,  # 10 events with 2 muons, 2 with 3 muons
        "Jets": [[1]] * 12,
        "BJets": [[] for _ in range(12)],
    })
    mass = ak.Array([200.0 + 10.0 * i for i in range(10)] + [300.0, 400.0])

    hists, meta = histograms.build_m0m1j0_histograms(obj_record, mass)

    check("inclusive histogram present", histograms.INCLUSIVE_HIST_NAME in hists)
    check(
        "inclusive histogram contains all 12 events",
        meta[histograms.INCLUSIVE_HIST_NAME]["n_events_in_histogram"] == 12,
        f"got {meta[histograms.INCLUSIVE_HIST_NAME]}",
    )

    expected_2m_name = "mass_m0m1j0_cat_0ex_2mx_1jx_0gx_0tx_0bx"
    expected_3m_name = "mass_m0m1j0_cat_0ex_3mx_1jx_0gx_0tx_0bx"
    check(
        "2-muon category (10 events, >= threshold of 5) has its own histogram",
        expected_2m_name in hists,
        f"hists keys: {list(hists.keys())}",
    )
    check(
        "3-muon category (2 events, < threshold of 5) is dropped, not silently omitted",
        expected_3m_name not in hists and expected_3m_name in meta.get("_dropped_categories_below_min_events_per_fs", []),
        f"dropped list: {meta.get('_dropped_categories_below_min_events_per_fs')}",
    )
    if expected_2m_name in hists:
        h = hists[expected_2m_name]
        check(
            "2-muon category ROOT-internal name carries ROI_ prefix and _width_10 suffix",
            h.name == f"ROI_{expected_2m_name}_width_10",
            f"got {h.name}",
        )
        total_filled = sum(h.contents)
        check("2-muon category histogram has 10 entries filled", total_filled == 10, f"got {total_filled}")

    # trim_empty_tail sanity: values go up to 290 GeV -> last filled bin
    # should set the display range well below 10000, never touching bin
    # content (stub tracks contents/range separately, matching the real
    # function's own SetRangeUser-only contract, histograms_pipeline.py:26-41).
    if expected_2m_name in hists:
        h = hists[expected_2m_name]
        lo, hi = h._axis._range
        check(
            "trim_empty_tail narrowed the display range (not the stored bin content)",
            hi < 1000.0 and sum(h.contents) == 10,
            f"range={h._axis._range}, total_contents={sum(h.contents)}",
        )

    # apply_min_events_prune=False (the per-job driver's own mode): the
    # 3-muon category (2 events, below the threshold of 5) must still get
    # its own histogram written, not dropped -- pruning is a merge-time-
    # only operation (RECIPE.md section 5/6.5).
    hists_nopune, meta_noprune = histograms.build_m0m1j0_histograms(
        obj_record, mass, apply_min_events_prune=False
    )
    check(
        "apply_min_events_prune=False: 3-muon category IS written despite being below threshold",
        expected_3m_name in hists_nopune,
        f"hists keys: {list(hists_nopune.keys())}",
    )
    check(
        "apply_min_events_prune=False: no categories reported as dropped",
        meta_noprune.get("_dropped_categories_below_min_events_per_fs") == [],
        f"got {meta_noprune.get('_dropped_categories_below_min_events_per_fs')}",
    )

    # z_peak/max_mass cutoff propagation: an all-NaN mass array must yield
    # zero entries, not crash.
    empty_obj = ak.Array({"Electrons": [[]], "Muons": [[1, 2]], "Jets": [[1]], "BJets": [[]]})
    empty_mass = ak.Array([np.nan])
    hists2, meta2 = histograms.build_m0m1j0_histograms(empty_obj, empty_mass)
    check(
        "all-NaN mass array yields 0 inclusive entries without crashing",
        meta2[histograms.INCLUSIVE_HIST_NAME]["n_events_in_histogram"] == 0,
        f"got {meta2}",
    )

    print()
    if FAILURES:
        print(f"{len(FAILURES)} FAILURE(S): {FAILURES}")
        sys.exit(1)
    else:
        print("All histogram-stub self-checks passed.")


if __name__ == "__main__":
    main()
