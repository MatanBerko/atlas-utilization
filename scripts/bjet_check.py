#!/usr/bin/env python3
"""
bjet_check.py - first-look sanity check for the CMS b-jet tagging path.

CMS b-tagging (config.cms_bjet_test.yaml: enable_jet_tagging + a
Jet_btagDeepFlavB threshold) had never been run before. This diagnostic reads
the output of a parsing + mass-calculation run and answers three questions:

  1. Are *some* jets tagged as b-jets - not zero, not all?
     -> counts Jets vs BJets in parsed_data/*.root
  2. Do b-jet final-state combinations actually get produced?
     -> scans im_arrays/*.sqlite for FS signatures with a non-zero b count
        (the 6th slot in _FS_<e>_<m>_<j>_<g>_<t>_<b>_) or a 'b' in the IM part
  3. Are the b-jet invariant masses physically sane (not a 0 GeV spike, not
     absurd), e.g. the pure b0b1 di-b-jet spectrum.

Usage:
    python scripts/bjet_check.py --run-dir output/<run>
    python scripts/bjet_check.py           # newest run under ./output
"""
from __future__ import annotations

import argparse
import io
import re
import sqlite3
import sys
import zlib
from collections import defaultdict
from pathlib import Path

import numpy as np


def find_latest_run_dir(base: str = "./output") -> Path | None:
    base_p = Path(base)
    if not base_p.is_dir():
        return None
    cands = [d for d in base_p.iterdir() if d.is_dir() and (d / "im_arrays").is_dir()]
    if not cands:
        cands = [d for d in base_p.iterdir() if d.is_dir()]
    if not cands:
        return None
    cands.sort(key=lambda d: d.stat().st_mtime, reverse=True)
    return cands[0]


# --------------------------------------------------------------------------- #
# 1. parse-level: Jets vs BJets
# --------------------------------------------------------------------------- #
def check_parse_level(parsed_dir: Path) -> None:
    print("=" * 74)
    print("1. PARSE LEVEL  -  are some jets tagged as b-jets?")
    print("=" * 74)
    roots = sorted(parsed_dir.glob("*.root"))
    if not roots:
        print(f"  no *.root under {parsed_dir}")
        return
    try:
        import uproot
        import awkward as ak
    except ImportError:
        print("  (uproot/awkward unavailable - skipping parse-level check)")
        return

    tot_jets = tot_bjets = tot_events = 0
    for rf in roots:
        f = uproot.open(rf)
        tname = "events" if "events" in f else f.keys()[0].split(";")[0]
        t = f[tname]
        keys = [k.split(";")[0] for k in t.keys()]
        # collection fields written as "<Coll>_<field>" or nested records
        def count_coll(coll: str) -> int:
            cand = [k for k in keys if k == coll or k.startswith(coll + "_") or k == "n" + coll]
            if not cand:
                return -1
            # prefer an explicit counter branch
            if "n" + coll in keys:
                return int(ak.sum(t["n" + coll].array()))
            # else take the first per-object field and count entries
            field = sorted(cand)[0]
            arr = t[field].array()
            try:
                return int(ak.count(arr))
            except Exception:
                return int(ak.sum(ak.num(arr)))

        nj = count_coll("Jets")
        nb = count_coll("BJets")
        ne = t.num_entries
        tot_events += ne
        if nj >= 0:
            tot_jets += nj
        if nb >= 0:
            tot_bjets += nb
        print(f"  {rf.name}: events={ne}  Jets={nj}  BJets={nb}")

    print("-" * 74)
    if tot_jets <= 0 and tot_bjets <= 0:
        print("  could not read Jets/BJets collections by name - check branch layout above")
        return
    light = tot_jets
    total_jets_before_split = light + tot_bjets
    frac = tot_bjets / total_jets_before_split if total_jets_before_split else 0.0
    print(f"  TOTAL over {tot_events} events:")
    print(f"    non-b jets (Jets)     : {light}")
    print(f"    b-tagged jets (BJets) : {tot_bjets}")
    print(f"    b-tag fraction        : {frac*100:.2f}%  of all reconstructed jets")
    if tot_bjets == 0:
        print("    VERDICT: no jets tagged -> threshold too high, or field not read. SUSPECT.")
    elif frac > 0.6:
        print("    VERDICT: >60% of jets tagged -> threshold too low / wrong field. SUSPECT.")
    elif 0.005 <= frac <= 0.35:
        print("    VERDICT: plausible. A SingleElectron sample is mostly light/gluon jets "
              "with a minority of real b-jets (ttbar, single-top, b-quark QCD).")
    else:
        print("    VERDICT: outside the rough expected 0.5-35% band - worth a closer look.")


# --------------------------------------------------------------------------- #
# 2 + 3. IM level: b-jet final states and their masses
# --------------------------------------------------------------------------- #
FS_IM_RE = re.compile(r"_FS_(\d+)e_(\d+)m_(\d+)j_(\d+)g_(\d+)t_(\d+)b_IM_([0-9a-z]+)(?:_(main|outliers))?$")


def _des(payload: bytes) -> np.ndarray:
    return np.load(io.BytesIO(zlib.decompress(payload)), allow_pickle=False)


def check_im_level(im_dir: Path) -> None:
    print()
    print("=" * 74)
    print("2/3. MASS-CALC LEVEL  -  b-jet combinations and their invariant masses")
    print("=" * 74)
    shards = sorted(im_dir.glob("*.sqlite"))
    if not shards:
        print(f"  no *.sqlite under {im_dir}")
        return

    bjet_sigs = 0
    bjet_entries = 0
    by_impart: dict[str, list] = defaultdict(list)
    all_bjet_vals: list = []
    pure_bb: list = []
    example_rows = []

    for shard in shards:
        conn = sqlite3.connect(str(shard))
        try:
            rows = conn.execute("SELECT signature, payload FROM array_chunks ORDER BY id").fetchall()
        finally:
            conn.close()
        for sig, payload in rows:
            m = FS_IM_RE.search(sig)
            if not m:
                continue
            ne, nm, nj, ng, nt, nb, impart, tag = m.groups()
            nb = int(nb)
            if nb == 0 and "b" not in impart:
                continue
            arr = np.asarray(_des(payload), dtype="float64").ravel()
            arr = arr[np.isfinite(arr)]
            bjet_sigs += 1
            bjet_entries += arr.size
            by_impart[impart].append(arr)
            all_bjet_vals.append(arr)
            if impart == "b0b1" and (ne, nm, nj, ng, nt) == ("0", "0", "0", "0", "0"):
                pure_bb.append(arr)
            if len(example_rows) < 12 and arr.size:
                example_rows.append((sig, arr.size, float(np.median(arr)), float(arr.min()), float(arr.max())))

    print(f"  b-jet-involving FS_IM signatures : {bjet_sigs}")
    print(f"  total entries in them            : {bjet_entries}")
    if bjet_sigs == 0:
        print("  VERDICT: no b-jet combinations produced despite BJets in objects_to_calculate.")
        return

    print()
    print("  sample of b-jet channels (signature : n, median, min, max) [GeV]:")
    for sig, n, med, lo, hi in example_rows:
        short = sig.split("_IM_")
        print(f"    ...{short[0][-34:]}_IM_{short[1]:<16}  n={n:<6} med={med:8.1f}  [{lo:7.1f}, {hi:8.1f}]")

    print()
    print("  by IM-combination type (the b-jet ones):")
    for impart in sorted(by_impart):
        if "b" not in impart:
            continue
        v = np.concatenate(by_impart[impart])
        if v.size == 0:
            continue
        neg = int((v < 0).sum())
        near0 = int((v < 5).sum())
        print(f"    {impart:<10} n={v.size:<7} median={np.median(v):8.1f}  "
              f"p05={np.percentile(v,5):7.1f}  p95={np.percentile(v,95):8.1f}  "
              f"<5GeV={near0}  <0={neg}")

    # di-b-jet spectrum sanity
    print()
    print("  DI-B-JET (b0b1) sanity:")
    src = pure_bb if pure_bb else by_impart.get("b0b1", [])
    if not src or (isinstance(src, list) and sum(a.size for a in src) == 0):
        print("    no b0b1 pairs at all in this small run (rare final state; not alarming).")
    else:
        v = np.concatenate(src) if isinstance(src, list) else src
        near0 = int((v < 10).sum())
        print(f"    n={v.size}  min={v.min():.2f}  median={np.median(v):.1f}  max={v.max():.1f}")
        print(f"    fraction below 10 GeV: {near0}/{v.size} = {100*near0/v.size:.1f}%")
        edges = np.arange(0, 505, 25)
        counts, _ = np.histogram(v[(v >= 0) & (v <= 500)], bins=edges)
        mx = counts.max() if counts.any() else 1
        bars = "".join("#" if c == mx else ("+" if c > mx*0.25 else ".") for c in counts)
        print(f"    0|{bars}|500 GeV  (25 GeV bins)")
        if near0 / v.size > 0.5:
            print("    VERDICT: dominated by ~0 GeV self-pairs -> object-overlap artifact, "
                  "same as e+j / e+g. Not physical di-b-jet mass.")
        elif np.median(v) < 15:
            print("    VERDICT: median very low - suspicious, look closer.")
        else:
            print("    VERDICT: broad continuum well away from 0 GeV - looks like a real "
                  "di-jet mass spectrum.")

    print()
    print("  OVERALL b-jet mass range:")
    v = np.concatenate(all_bjet_vals)
    print(f"    n={v.size}  min={v.min():.2f}  p01={np.percentile(v,1):.1f}  "
          f"median={np.median(v):.1f}  p99={np.percentile(v,99):.1f}  max={v.max():.1f}")
    if v.min() < -1:
        print(f"    NOTE: {int((v<-1).sum())} entries below -1 GeV (numerical / bad kinematics).")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", default=None)
    ap.add_argument("--base-output", default="./output")
    args = ap.parse_args()
    run_dir = Path(args.run_dir) if args.run_dir else find_latest_run_dir(args.base_output)
    if run_dir is None or not run_dir.is_dir():
        sys.exit(f"[bjet_check] no run dir under {args.base_output!r}")
    print(f"run dir: {run_dir}\n")
    check_parse_level(run_dir / "parsed_data")
    check_im_level(run_dir / "im_arrays")
    print()
    print("=" * 74)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
