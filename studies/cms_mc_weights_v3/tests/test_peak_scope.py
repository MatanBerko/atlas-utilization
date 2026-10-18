#!/usr/bin/env python
"""
Tests for build_mc_delivery.py --peak-scope (Matan's decision, 18 Oct 2026,
option A): the peak-removal and outlier-split masses of each histogram name
are found ONCE on the combined spectrum of all samples and applied to every
sample.

  1. CLOSURE -- with several samples and --peak-scope combined, the sum of
     the per-sample histograms equals the summed-SM histogram bin by bin
     (contents and sum-of-w^2), to <= 1e-12 relative, read back from ROOT.
  2. ONE LOWER CUT -- every per-sample histogram of a name carries the same
     peak and split masses as the combined cut of that name, has no content
     below that peak, and the summed SM starts exactly at it. The combined
     peak is the rightmost-highest weighted bin of the CONCATENATED spectrum.
     (Control: the same inputs built --peak-scope per-sample DO cut the
     samples at different masses, so the test exercises the difference.)
  3. ONE SAMPLE -- with a single sample, combined == per-sample bit for bit
     (ROOT contents and variances, peak masses), on a full build and on
     random spectra through postprocess_in_lockstep directly; so the change
     only matters when several samples are combined.

No network, no cluster. Exit code 0 only if every check passes.

Run:  python studies/cms_mc_weights_v3/tests/test_peak_scope.py
"""
from __future__ import annotations

import json
import pathlib
import sys
import tempfile

import numpy as np
import uproot

REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

from studies.cms_mc_weights_v3.deliver import build_mc_delivery as B  # noqa: E402
from studies.cms_mc_weights_v3.tests.test_builder_end_to_end import (  # noqa: E402
    Args, write_fake_job,
)

RESULTS: list[tuple[str, bool, str]] = []
FS = "0e_2m_0j_0b"
SIGMA_W = 1.15813237e5
# three in_full_run records of the registry with comparable weights
# (sigma_eff 19.56, 19.56 and 5.789 pb), each with its own spectrum: a broad
# one peaking low, a narrow one peaking higher, and a flat one
SPECTRA = {
    "64839": ("normal", 150.0, 60.0, 3000),
    "64895": ("normal", 260.0, 10.0, 6000),
    "72752": ("uniform", 115.0, 900.0, 2000),
}


def check(name: str, condition: bool, detail: str = "") -> None:
    RESULTS.append((name, bool(condition), detail))
    print(f"{'PASS' if condition else 'FAIL'}  {name}" + (f"  -- {detail}" if detail else ""))


def masses_for(rid: str, seed: int) -> np.ndarray:
    kind, a, b, n = SPECTRA[rid]
    rng = np.random.default_rng(seed)
    m = rng.normal(a, b, n) if kind == "normal" else rng.uniform(a, b, n)
    m = np.clip(m, 111.0, None)
    m[:3] = [1500.0, 1520.0, 1980.0]   # isolated high-mass entries -> outlier split
    return m


def make_runs(root: pathlib.Path, rids: list) -> pathlib.Path:
    runs = root / "runs"
    for i, rid in enumerate(rids):
        n = SPECTRA[rid][3]
        write_fake_job(runs / f"record{rid}" / f"job_{i}", rid, i, SIGMA_W, SIGMA_W, 4 * n,
                       {FS: n}, masses_by_fs={FS: masses_for(rid, 100 + i)})
    return runs


def build(runs: pathlib.Path, root: pathlib.Path, scope: str) -> tuple[dict, pathlib.Path]:
    out = root / f"out_{scope}"
    report = B.build(Args(runs_dir=str(runs), out_dir=str(out), out_prefix="t",
                          scratch_dir=str(root / f"scratch_{scope}"),
                          keep_scratch=True, peak_scope=scope))
    return report, out


def read_root(path: pathlib.Path) -> dict:
    with uproot.open(path) as f:
        return {k: (np.asarray(f[k].values(flow=True), float),
                    np.asarray(f[k].variances(flow=True), float),
                    np.asarray(f[k].axis().edges(), float))
                for k in f.keys(cycle=False)}


def first_filled_low_edge(values_flow: np.ndarray, edges: np.ndarray):
    nz = np.nonzero(values_flow[1:-1])[0]
    return None if nz.size == 0 else float(edges[nz[0]])


def test_closure_and_one_cut(tmp: pathlib.Path) -> dict:
    rids = sorted(SPECTRA, key=int)
    runs = make_runs(tmp, rids)
    rep_c, out_c = build(runs, tmp, "combined")
    rep_p, out_p = build(runs, tmp, "per-sample")

    summed = read_root(out_c / "t_summedSM_mc.root")
    per = {rid: read_root(out_c / f"t_record{rid}_mc.root") for rid in rids
           if (out_c / f"t_record{rid}_mc.root").exists()}
    check("combined build: every sample has the histogram", len(per) == len(rids),
          f"{sorted(per)}")

    # 1. closure
    worst = 0.0
    for key, (v, var, _e) in summed.items():
        sv = sum(p[key][0] for p in per.values() if key in p)
        svar = sum(p[key][1] for p in per.values() if key in p)
        for a, b in ((sv, v), (svar, var)):
            scale = np.maximum(np.abs(b), 1e-300)
            worst = max(worst, float(np.max(np.abs(a - b) / scale)))
    check("CLOSURE: sum of per-sample == summed SM bin by bin (contents and sumw2)",
          worst <= 1e-12, f"max relative difference {worst:.3e}")

    # 2. one lower cut per name
    name = B._convert_to_bumpnet_name(FS, "m0m1")
    key = next(iter(summed))
    cut = rep_c["combined_cuts"][name]
    peaks = {rid: rep_c["samples"][rid]["histograms"]["per_histogram"][name]["peak_mass"]
             for rid in rids}
    splits = {rid: rep_c["samples"][rid]["histograms"]["per_histogram"][name].get("split_mass")
              for rid in rids}
    check("ONE CUT: every sample's peak mass == the combined peak mass",
          set(peaks.values()) == {cut["peak_mass"]}, f"{peaks} vs {cut['peak_mass']}")
    check("ONE CUT: every sample's split mass == the combined split mass",
          set(splits.values()) == {cut["split_mass"]}, f"{splits} vs {cut['split_mass']}")
    firsts = {rid: first_filled_low_edge(p[key][0], p[key][2]) for rid, p in per.items()}
    s_first = first_filled_low_edge(summed[key][0], summed[key][2])
    check("ONE CUT: no sample has content below the combined peak",
          all(f >= cut["peak_mass"] for f in firsts.values()), f"{firsts}")
    check("ONE CUT: the summed SM starts exactly at the combined peak",
          s_first == cut["peak_mass"], f"{s_first} vs {cut['peak_mass']}")
    lasts_ok = all(np.all(p[key][0][1:-1][p[key][2][:-1] >= cut["split_mass"]] == 0)
                   for p in per.values()) if cut["split_mass"] is not None else True
    check("ONE CUT: no sample has content at or above the combined split",
          cut["split_mass"] is not None and lasts_ok, f"split {cut['split_mass']}")

    # the combined peak is the concatenated spectrum's rightmost-highest weighted bin
    ms, ws = [], []
    for rid in rids:
        shard = tmp / "scratch_combined" / f"record_{rid}"
        path = next(shard.glob("*.sqlite"), None) if shard.exists() else None
        if path is None:
            break
        arr = B.read_shard_arrays(str(path))
        sig = next(s for s in arr if s.endswith("_IM_m0m1"))
        m = np.concatenate([np.asarray(c, float) for c in arr[sig]])
        w = np.concatenate([np.asarray(c, float) for c in arr[sig + B.MC_WEIGHT_SUFFIX]])
        keep = B.z_and_max_mass_mask(m, "m0m1")
        ms.append(m[keep]); ws.append(w[keep])
    if len(ms) == len(rids):
        expect = B.find_peak_mass(np.concatenate(ms), np.concatenate(ws))
        check("the combined peak is the rightmost-highest weighted bin of the "
              "concatenated spectrum", expect == cut["peak_mass"], f"{expect} vs {cut['peak_mass']}")
    else:
        check("the combined peak is the rightmost-highest weighted bin of the "
              "concatenated spectrum", False, "scratch shards not found (scratch not kept?)")

    # control: per-sample scope cuts the samples at different masses
    peaks_p = {rid: rep_p["samples"][rid]["histograms"]["per_histogram"][name]["peak_mass"]
               for rid in rids}
    check("CONTROL: --peak-scope per-sample cuts the samples at different peaks",
          len(set(peaks_p.values())) > 1, f"{peaks_p}")
    return {"closure_max_rel": worst, "combined_cut": cut, "per_sample_peaks_old": peaks_p,
            "first_filled_combined": firsts, "summed_first_combined": s_first}


def test_one_sample(tmp: pathlib.Path) -> None:
    runs = make_runs(tmp, ["64839"])
    rep_c, out_c = build(runs, tmp, "combined")
    rep_p, out_p = build(runs, tmp, "per-sample")
    same = True
    for fname in ("t_record64839_mc.root", "t_summedSM_mc.root"):
        a, b = read_root(out_c / fname), read_root(out_p / fname)
        same &= a.keys() == b.keys() and all(
            np.array_equal(a[k][0], b[k][0]) and np.array_equal(a[k][1], b[k][1]) for k in a)
    check("ONE SAMPLE: combined == per-sample, ROOT contents and variances bit-identical", same)
    pa = rep_c["samples"]["64839"]["histograms"]["per_histogram"]
    pb = rep_p["samples"]["64839"]["histograms"]["per_histogram"]
    check("ONE SAMPLE: identical peak masses and entry counts in the report",
          all(pa[n]["peak_mass"] == pb[n]["peak_mass"] and pa[n]["n_main"] == pb[n]["n_main"]
              and pa[n]["n_outliers"] == pb[n]["n_outliers"] for n in pa) and pa.keys() == pb.keys())


def test_one_sample_property(n_trials: int = 300, seed: int = 20261018) -> None:
    rng = np.random.default_rng(seed)
    bad = 0
    for t in range(n_trials):
        n = int(rng.integers(1, 400))
        m = np.concatenate([rng.normal(rng.uniform(60, 600), rng.uniform(1, 80), n),
                            rng.uniform(1000, 3000, int(rng.integers(0, 4)))])
        w = rng.normal(1.0, 0.7, len(m))
        im = "m0m1" if t % 2 else "j0j1"
        for peak_on in ("weighted", "unweighted"):
            a = B.postprocess_in_lockstep(m, w, im, peak_on)
            cuts = B.combined_cuts([(m, w)], im, peak_on)
            b = B.postprocess_in_lockstep(m, w, im, peak_on, cuts)
            if a.get("peak_mass") != b.get("peak_mass") or ("main_masses" in a) != ("main_masses" in b):
                bad += 1
                continue
            if "main_masses" in a and not all(
                    np.array_equal(a[k], b[k]) for k in
                    ("main_masses", "main_weights", "outlier_masses", "outlier_weights")):
                bad += 1
    check("ONE SAMPLE (property): postprocess with the combined cuts of a single "
          f"sample == per-sample, {2 * n_trials} random spectra", bad == 0, f"{bad} mismatches")


def main() -> int:
    print("=" * 74)
    print("build_mc_delivery.py --peak-scope")
    print("=" * 74)
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="mc_peakscope_"))
    detail = test_closure_and_one_cut(tmp / "multi")
    test_one_sample(tmp / "one")
    test_one_sample_property()
    n_fail = sum(1 for _, ok, _ in RESULTS if not ok)
    print("=" * 74)
    print(f"{len(RESULTS) - n_fail} pass, {n_fail} fail, {len(RESULTS)} checks total")
    out = REPO_ROOT / "studies" / "cms_mc_weights_v3" / "peakfix" / "evidence" / "peak_scope_tests.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"checks": [{"name": n, "pass": ok, "detail": d} for n, ok, d in RESULTS],
                               "multi_sample_detail": detail}, indent=2, default=str))
    print(f"wrote {out}")
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
