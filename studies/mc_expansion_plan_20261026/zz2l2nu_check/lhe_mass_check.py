"""Quick check (3 Nov 2026): is the ZZTo2L2Nu portal cross section high because of low-mass Z/γ* → ℓℓ?

Read-only. Two modes:

  run  (cluster, inside one PBS job; repo root on PYTHONPATH):
       python studies/mc_expansion_plan_20261026/zz2l2nu_check/lhe_mass_check.py run --out <dir>/lhe_mass_check.json
  plot (locally, from the JSON the job wrote):
       python studies/mc_expansion_plan_20261026/zz2l2nu_check/lhe_mass_check.py plot --json <json> --plots <dir>

Inputs: ZZTo2L2Nu NanoAOD record 75567, file indices 0, 1, 2; ZZTo4L 75589 (delivered, calibration), indices
0, 1. File URLs come from the CERN Open Data portal file index (fetch_file_list, the same call the production
input sweep and the 26/31 Oct probes use). Branches read: LHEPart_{pt,eta,phi,mass,pdgId,status}, genWeight.

Per event, outgoing LHE particles (status +1): charged leptons |pdgId| 11, 13, 15 and neutrinos 12, 14, 16.
- ZZTo2L2Nu: events with exactly 2 charged leptons + 2 neutrinos are used; m(ll) = mass of the charged pair,
  m(vv) = mass of the neutrino pair.
- ZZTo4L: events with exactly 4 charged leptons are used. Pairing rule: among all same-flavour opposite-sign
  (SFOS) pairs, Z1 = the pair with mass closest to mZ = 91.1876 GeV; Z2 = the other two leptons (the event is
  counted as "Z2 not SFOS" if they are not SFOS; does not happen when the four leptons come as two SFOS pairs).
- f_on = genWeight-weighted fraction of the used events with BOTH pairs in 60 < m < 120 GeV. Also: fraction with
  m(ll) < 60 and > 120 (2l2nu) / Z1, Z2 below/above (4l); fraction of m(vv) outside 60-120; and, for information
  only, f_on for two other windows (66-116, 81-101 GeV). Fractions are sum(w | condition) / sum(w | used).
Nothing is written except the --out JSON (run) or the PNGs (plot). HOME is not used.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

MZ = 91.1876
INPUTS = [("ZZTo2L2Nu", 75567, 0), ("ZZTo2L2Nu", 75567, 1), ("ZZTo2L2Nu", 75567, 2),
          ("ZZTo4L", 75589, 0), ("ZZTo4L", 75589, 1)]
WINDOWS = {"60_120": (60.0, 120.0), "66_116": (66.0, 116.0), "81_101": (81.0, 101.0)}
EDGES = np.linspace(0.0, 200.0, 101)          # 2 GeV bins, 0-200 GeV; overflow kept separately
BRANCHES = ["LHEPart_pt", "LHEPart_eta", "LHEPart_phi", "LHEPart_mass", "LHEPart_pdgId", "LHEPart_status", "genWeight"]


def p4(pt, eta, phi, m):
    px, py, pz = pt * np.cos(phi), pt * np.sin(phi), pt * np.sinh(eta)
    return np.sqrt(px ** 2 + py ** 2 + pz ** 2 + m ** 2), px, py, pz


def pair_mass(a, b):
    e, px, py, pz = (a[i] + b[i] for i in range(4))
    return np.sqrt(np.maximum(e ** 2 - px ** 2 - py ** 2 - pz ** 2, 0.0))


def hist(x, w):
    h = np.histogram(x, bins=EDGES, weights=w)[0]
    n = np.histogram(x, bins=EDGES)[0]
    return h, n, float(w[x >= EDGES[-1]].sum()), int((x >= EDGES[-1]).sum())


class Acc:
    """Accumulates weighted sums and histograms for one sample."""

    def __init__(self, names):
        self.n = {"events": 0, "used": 0, "not_used": 0, "z2_not_sfos": 0}
        self.sw = {"all": 0.0, "used": 0.0}
        self.cond = {}
        self.h = {k: [np.zeros(100), np.zeros(100, dtype=np.int64), 0.0, 0] for k in names}
        self.not_used_patterns = {}

    def add_cond(self, key, w):
        self.cond[key] = self.cond.get(key, 0.0) + float(w.sum())

    def add_hist(self, key, x, w):
        h, n, ow, on = hist(x, w)
        acc = self.h[key]
        acc[0] += h
        acc[1] += n
        acc[2] += ow
        acc[3] += on

    def result(self):
        used = self.sw["used"]
        return dict(counts=self.n, sum_w=self.sw,
                    fractions={k: v / used for k, v in self.cond.items()},
                    weighted_sums=self.cond,
                    not_used_patterns={str(k): v for k, v in sorted(self.not_used_patterns.items(), key=lambda kv: -kv[1])[:10]},
                    hists={k: dict(edges=EDGES.tolist(), sum_w=v[0].tolist(), counts=v[1].tolist(),
                                   overflow_sum_w=v[2], overflow_counts=v[3]) for k, v in self.h.items()})


def process(sample, arrays, acc):
    import awkward as ak
    st, pid = arrays["LHEPart_status"], arrays["LHEPart_pdgId"]
    out = st == 1
    apid = abs(pid)
    is_l = out & ((apid == 11) | (apid == 13) | (apid == 15))
    is_v = out & ((apid == 12) | (apid == 14) | (apid == 16))
    nl, nv = ak.sum(is_l, axis=1), ak.sum(is_v, axis=1)
    w = ak.to_numpy(arrays["genWeight"]).astype(np.float64)
    acc.n["events"] += len(w)
    acc.sw["all"] += float(w.sum())
    good = ((nl == 2) & (nv == 2)) if sample == "ZZTo2L2Nu" else ((nl == 4) & (nv == 0))
    good = ak.to_numpy(good)
    for a, b in zip(ak.to_numpy(nl)[~good], ak.to_numpy(nv)[~good]):
        acc.not_used_patterns[(int(a), int(b))] = acc.not_used_patterns.get((int(a), int(b)), 0) + 1
    acc.n["used"] += int(good.sum())
    acc.n["not_used"] += int((~good).sum())
    wg = w[good]
    acc.sw["used"] += float(wg.sum())

    def pick(mask, k):
        mk = mask[good]
        return [ak.to_numpy(ak.fill_none(ak.pad_none(arrays[f"LHEPart_{v}"][good][mk], k), 0.0)).astype(np.float64)
                for v in ("pt", "eta", "phi", "mass", "pdgId")]

    if sample == "ZZTo2L2Nu":
        pt, eta, phi, m, _ = pick(is_l, 2)
        l1, l2 = p4(pt[:, 0], eta[:, 0], phi[:, 0], m[:, 0]), p4(pt[:, 1], eta[:, 1], phi[:, 1], m[:, 1])
        mll = pair_mass(l1, l2)
        pt, eta, phi, m, _ = pick(is_v, 2)
        v1, v2 = p4(pt[:, 0], eta[:, 0], phi[:, 0], m[:, 0]), p4(pt[:, 1], eta[:, 1], phi[:, 1], m[:, 1])
        mvv = pair_mass(v1, v2)
        acc.add_hist("m_ll", mll, wg)
        acc.add_hist("m_vv", mvv, wg)
        for key, (lo, hi) in WINDOWS.items():
            acc.add_cond(f"f_on_{key}", wg[(mll > lo) & (mll < hi) & (mvv > lo) & (mvv < hi)])
        acc.add_cond("f_mll_below_60", wg[mll < 60])
        acc.add_cond("f_mll_above_120", wg[mll > 120])
        acc.add_cond("f_mll_60_120", wg[(mll > 60) & (mll < 120)])
        acc.add_cond("f_mvv_outside_60_120", wg[(mvv <= 60) | (mvv >= 120)])
        acc.add_cond("f_mll_below_12", wg[mll < 12])
    else:
        pt, eta, phi, m, pdg = pick(is_l, 4)
        L = [p4(pt[:, i], eta[:, i], phi[:, i], m[:, i]) for i in range(4)]
        pairs = [(0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3)]
        n = len(wg)
        best = np.full(n, np.inf)
        z1 = np.zeros(n)
        z2 = np.zeros(n)
        z2ok = np.zeros(n, dtype=bool)
        for i, j in pairs:
            k, l = [x for x in range(4) if x not in (i, j)]
            sfos = pdg[:, i] == -pdg[:, j]
            mij = pair_mass(L[i], L[j])
            better = sfos & (np.abs(mij - MZ) < best)
            best = np.where(better, np.abs(mij - MZ), best)
            z1 = np.where(better, mij, z1)
            z2 = np.where(better, pair_mass(L[k], L[l]), z2)
            z2ok = np.where(better, pdg[:, k] == -pdg[:, l], z2ok)
        acc.n["z2_not_sfos"] += int((~z2ok).sum())
        acc.n["no_sfos_pair"] = acc.n.get("no_sfos_pair", 0) + int(np.isinf(best).sum())
        acc.add_hist("m_Z1", z1, wg)
        acc.add_hist("m_Z2", z2, wg)
        for key, (lo, hi) in WINDOWS.items():
            acc.add_cond(f"f_on_{key}", wg[(z1 > lo) & (z1 < hi) & (z2 > lo) & (z2 < hi)])
        acc.add_cond("f_Z1_below_60", wg[z1 < 60])
        acc.add_cond("f_Z1_above_120", wg[z1 > 120])
        acc.add_cond("f_Z2_below_60", wg[z2 < 60])
        acc.add_cond("f_Z2_above_120", wg[z2 > 120])


def run(out):
    import uproot
    repo = Path(__file__).resolve().parents[3]
    sys.path.insert(0, str(repo))
    from studies.m0m1j0_cms.design_checks.common import fetch_file_list
    accs = {"ZZTo2L2Nu": Acc(["m_ll", "m_vv"]), "ZZTo4L": Acc(["m_Z1", "m_Z2"])}
    files = []
    lists = {}
    for sample, recid, idx in INPUTS:
        if recid not in lists:
            lists[recid] = fetch_file_list(recid)
        url = lists[recid][idx]
        t0 = time.time()
        n0 = accs[sample].n["events"]
        with uproot.open(url) as f:
            for arrays in f["Events"].iterate(BRANCHES, step_size="200 MB"):
                process(sample, arrays, accs[sample])
        files.append(dict(sample=sample, recid=recid, file_index=idx, url=url,
                          events=accs[sample].n["events"] - n0, seconds=round(time.time() - t0, 1)))
        print(json.dumps(files[-1]), flush=True)
    res = dict(what="LHE-level pair masses of ZZTo2L2Nu (75567) and ZZTo4L (75589)", mZ=MZ, windows=WINDOWS,
               files=files, samples={k: v.result() for k, v in accs.items()})
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_text(json.dumps(res, indent=1) + "\n")
    for k, v in res["samples"].items():
        print(k, json.dumps(v["counts"]), json.dumps(v["fractions"]))


def plot(js, outdir):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    d = json.loads(Path(js).read_text())
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    spec = {"ZZTo2L2Nu": [("m_ll", "m(ℓℓ), charged-lepton pair", "#2a78d6"), ("m_vv", "m(νν), neutrino pair", "#eb6834")],
            "ZZTo4L": [("m_Z1", "Z1 (SFOS pair closest to mZ)", "#2a78d6"), ("m_Z2", "Z2 (the other pair)", "#eb6834")]}
    for sample, items in spec.items():
        s = d["samples"][sample]
        fig, axes = plt.subplots(1, 2, figsize=(11, 4), facecolor="#fcfcfb")
        for ax, (key, label, col) in zip(axes, items):
            h = s["hists"][key]
            e = np.array(h["edges"])
            vals = np.array(h["sum_w"]) / s["sum_w"]["used"]
            ax.stairs(np.clip(vals, 1e-9, None), e, color=col, linewidth=1.4)
            for x in (60, 120):
                ax.axvline(x, color="#52514e", linestyle="--", linewidth=0.8)
            ax.set_yscale("log")
            ax.set_xlim(0, 200)
            ax.set_xlabel(f"{label} [GeV] (LHE level)", fontsize=9)
            ax.set_ylabel("fraction of Σ genWeight per 2 GeV", fontsize=9)
            ax.set_title(f"{sample}: {label}\noverflow > 200 GeV: {h['overflow_sum_w'] / s['sum_w']['used']:.4f}", fontsize=9, loc="left")
        fig.suptitle(f"{sample}, {s['counts']['used']:,} events used; dashed: 60 and 120 GeV; f_on(60-120) = {s['fractions']['f_on_60_120']:.4f}", fontsize=10)
        fig.tight_layout()
        fig.savefig(outdir / f"lhe_masses_{sample}.png", dpi=120, facecolor="#fcfcfb")
        plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="mode", required=True)
    r = sub.add_parser("run")
    r.add_argument("--out", required=True)
    p = sub.add_parser("plot")
    p.add_argument("--json", required=True)
    p.add_argument("--plots", required=True)
    a = ap.parse_args()
    run(a.out) if a.mode == "run" else plot(a.json, a.plots)


if __name__ == "__main__":
    main()
