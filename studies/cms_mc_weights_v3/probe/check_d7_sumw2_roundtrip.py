#!/usr/bin/env python
"""
Design item D7: can a weighted TH1 with a genuine Sumw2 array be written
through uproot (the fork's own histogram writer, which does NOT use PyROOT),
and does it read back with bin error == sqrt(sum of w^2)?

The fork writes histograms via
studies/m0m1j0_cms/histograms.py::to_writable_th1f, which calls
uproot.writing.identify.to_TH1x with fSumw2=None (unweighted data, float32
contents => TH1F). This check shows the weighted variant: float64 contents
plus an explicit fSumw2 array of length n_bins + 2 (ROOT's own on-disk
convention, including the underflow and overflow slots), written and then
read back and compared against numpy.

Deliberately includes a NEGATIVE weight, because NLO samples produce them and
a negative weight must lower the bin content while still RAISING its error.

Writes one small .root into a temp directory and nothing else.

Run:  python studies/cms_mc_weights_v3/probe/check_d7_sumw2_roundtrip.py
"""
from __future__ import annotations

import json
import os
import sys
import tempfile

import numpy as np
import uproot
import uproot.writing.identify as uproot_identify

BIN_WIDTH = 10.0
EDGES = np.arange(0.0, 60.0 + 1e-9, BIN_WIDTH)          # 6 bins


def main() -> int:
    masses = np.array([5.0, 5.0, 15.0, 25.0, 25.0, 25.0, 55.0])
    weights = np.array([2.0, -1.0, 3.0, 0.5, 0.5, 0.5, 4.0])

    values, _ = np.histogram(masses, bins=EDGES, weights=weights)
    sumw2, _ = np.histogram(masses, bins=EDGES, weights=weights * weights)
    n_bins = len(values)

    data = np.zeros(n_bins + 2, dtype=np.float64)
    data[1:-1] = values
    sumw2_on_disk = np.zeros(n_bins + 2, dtype=np.float64)
    sumw2_on_disk[1:-1] = sumw2

    xaxis = uproot_identify.to_TAxis(
        "xaxis", "", n_bins, float(EDGES[0]), float(EDGES[-1]),
        fXbins=np.asarray(EDGES, dtype=np.float64),
    )
    hist = uproot_identify.to_TH1x(
        fName=None,
        fTitle="ROI_sumw2_roundtrip_check",
        data=data,
        fEntries=float(len(masses)),
        fTsumw=float(weights.sum()),
        fTsumw2=float((weights * weights).sum()),
        fTsumwx=0.0,
        fTsumwx2=0.0,
        fSumw2=sumw2_on_disk,
        fXaxis=xaxis,
    )

    tmp_dir = tempfile.mkdtemp(prefix="d7_sumw2_check_")
    root_path = os.path.join(tmp_dir, "sumw2_roundtrip.root")
    with uproot.recreate(root_path) as f:
        f["ROI_sumw2_roundtrip_check"] = hist

    with uproot.open(root_path) as f:
        obj = f["ROI_sumw2_roundtrip_check"]
        got_values = obj.values(flow=False)
        got_errors = obj.errors(flow=False)
        got_variances = obj.variances(flow=False)
        result = {
            "root_path": root_path,
            "uproot_version": uproot.__version__,
            "classname_on_disk": obj.classname,
            "classname_is_TH1D": obj.classname == "TH1D",
            "expected_values": values.tolist(),
            "readback_values": got_values.tolist(),
            "values_match": bool(np.allclose(got_values, values)),
            "expected_sum_w2": sumw2.tolist(),
            "readback_variances": got_variances.tolist(),
            "variances_match_sum_w2": bool(np.allclose(got_variances, sumw2)),
            "readback_errors": got_errors.tolist(),
            "expected_sqrt_sum_w2": np.sqrt(sumw2).tolist(),
            "errors_equal_sqrt_sum_w2": bool(
                np.allclose(got_errors, np.sqrt(sumw2))),
            "fSumw2_length_on_disk": len(obj.member("fSumw2")),
            "fSumw2_length_expected_n_bins_plus_2": n_bins + 2,
            "negative_weight_bin_index": 0,
            "negative_weight_bin_content": float(got_values[0]),
            "negative_weight_bin_error": float(got_errors[0]),
        }

    print(json.dumps(result, indent=2))
    return 0 if (result["values_match"] and result["errors_equal_sqrt_sum_w2"]
                 and result["classname_is_TH1D"]) else 1


if __name__ == "__main__":
    sys.exit(main())
