#!/usr/bin/env python
"""Generator-level facts from file 0 of each record (NanoAOD GenPart / genWeight), READ ONLY. Runs in a PBS job with
the pinned repo on sys.path (for the file list and the HTTPS opener the production driver uses).

Per record:
  * genWeight over ALL events of file 0: number, fraction negative, sum;
  * for the first --max-events events (GenPart, Python loop):
      - leptons (e, mu, tau; first copy) whose ancestry reaches the Higgs, directly (H -> l l gamma, MadSpin) or through
        a Z from the Higgs; m_ll of the opposite-sign same-flavour pair from the Higgs (first copies, before FSR);
      - Higgs -> Z decays and the associated (non-Higgs) Z/W decays, classified as ll / nunu / qq (N4);
      - number of prompt charged leptons (e, mu, tau first copies from a W/Z/H/tau ancestry) per event (N4 filter);
      - events with a Higgs (pdgId 25) or a top quark (|pdgId| 6) anywhere in GenPart (N1/N2);
  * a weighted (genWeight) m_ll histogram 0-130 GeV in 1 GeV bins and fractions in m_ll ranges.

    python gen_check.py --repo <pinned repo> --records 37420 37276 ... --max-events 100000 --out <dir>
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

BRANCHES = ["genWeight", "GenPart_pdgId", "GenPart_genPartIdxMother", "GenPart_pt", "GenPart_eta", "GenPart_phi",
            "GenPart_mass", "GenPart_statusFlags"]
FIRST_COPY = 1 << 12
LEPT = (11, 13, 15)
NU = (12, 14, 16)
EDGES = np.arange(0.0, 131.0, 1.0)
RANGES = [(0, 30), (30, 50), (0, 50), (50, 80), (80, 100), (100, 130), (50, 130)]


def p4(pt, eta, phi, m):
    px, py, pz = pt * np.cos(phi), pt * np.sin(phi), pt * np.sinh(eta)
    e = np.sqrt(px * px + py * py + pz * pz + m * m)
    return np.array([e, px, py, pz])


def minv(a, b):
    s = a + b
    return float(np.sqrt(max(s[0] ** 2 - s[1] ** 2 - s[2] ** 2 - s[3] ** 2, 0.0)))


def classify_v(i, pdg, kids):
    """ll / nunu / qq / other for the LAST copy of a W/Z at index i (children of the last copy)."""
    d = [abs(pdg[k]) for k in kids.get(i, [])]
    if any(x in LEPT for x in d):
        return "ll" if abs(pdg[i]) == 23 else "lnu"
    if any(x in NU for x in d):
        return "nunu"
    if any(1 <= x <= 5 for x in d):
        return "qq"
    return "other"


def last_copy(i, pdg, kids):
    while True:
        same = [k for k in kids.get(i, []) if pdg[k] == pdg[i]]
        if not same:
            return i
        i = same[0]


def one_event(pdg, mom, pt, eta, phi, mass, flags):
    n = len(pdg)
    kids = {}
    for k in range(n):
        if mom[k] >= 0:
            kids.setdefault(int(mom[k]), []).append(k)

    def anc(i):  # first ancestor with a different pdgId
        j = int(mom[i])
        while j >= 0 and pdg[j] == pdg[i]:
            j = int(mom[j])
        return j

    def reaches(i, target):
        j = i
        while j >= 0:
            if abs(pdg[j]) == target:
                return True
            j = int(mom[j])
        return False

    h_leps, prompt = [], 0
    for k in range(n):
        a = abs(pdg[k])
        if a not in LEPT or not (flags[k] & FIRST_COPY):
            continue
        j = anc(k)
        if j < 0:
            continue
        aj = abs(pdg[j])
        if aj in (23, 24, 25) or (aj == 15 and a in (11, 13)):
            if aj != 15:
                prompt += 1
        if aj == 25 or (aj == 23 and reaches(j, 25)):
            h_leps.append((k, "H" if aj == 25 else "Z"))
    pair = None
    for x in range(len(h_leps)):
        for y in range(x + 1, len(h_leps)):
            i, j = h_leps[x][0], h_leps[y][0]
            if pdg[i] == -pdg[j]:
                pair = (i, j, h_leps[x][1])
                break
        if pair:
            break
    mll = flav = via = None
    if pair:
        i, j, via = pair
        mll = minv(p4(pt[i], eta[i], phi[i], mass[i]), p4(pt[j], eta[j], phi[j], mass[j]))
        flav = {11: "ee", 13: "mumu", 15: "tautau"}[abs(int(pdg[i]))]
    hz, vz = [], []
    seen = set()
    for k in range(n):
        if abs(pdg[k]) not in (23, 24) or not (flags[k] & FIRST_COPY):
            continue
        lc = last_copy(k, pdg, kids)
        if lc in seen:
            continue
        seen.add(lc)
        c = classify_v(lc, pdg, kids)
        (hz if anc(k) >= 0 and abs(pdg[anc(k)]) == 25 else vz).append(f"{'Z' if abs(pdg[k]) == 23 else 'W'}:{c}")
    return {"mll": mll, "flav": flav, "via": via, "hz": sorted(hz), "vz": sorted(vz), "prompt": prompt,
            "has_h": bool(np.any(pdg == 25)), "has_t": bool(np.any(np.abs(pdg) == 6))}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--records", nargs="+", type=int, required=True)
    ap.add_argument("--max-events", type=int, default=100000)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    sys.path.insert(0, a.repo)
    from studies.m0m1j0_cms.design_checks.common import fetch_file_list_complete, open_root_https  # noqa: E402
    out = {"what": "generator-level facts, file 0 per record (READ ONLY)", "max_events_genpart": a.max_events,
           "m_ll_edges_gev": EDGES.tolist(), "records": {}}
    Path(a.out).mkdir(parents=True, exist_ok=True)
    for rid in a.records:
        t0 = time.time()
        url = fetch_file_list_complete(rid)[0]
        with open_root_https(url) as f:
            t = f["Events"]
            gw_all = t["genWeight"].array(library="np")
            arr = t.arrays(BRANCHES, entry_stop=a.max_events, library="np")
        res = {"file_url": url, "n_events_file": int(len(gw_all)), "n_negative_genweight": int((gw_all < 0).sum()),
               "fraction_negative_genweight": float((gw_all < 0).mean()), "sum_genweight": float(gw_all.sum()),
               "n_events_genpart": int(len(arr["genWeight"]))}
        hist = {f: np.zeros(len(EDGES) - 1) for f in ("ee", "mumu", "tautau")}
        nhist = {f: np.zeros(len(EDGES) - 1, dtype=int) for f in ("ee", "mumu", "tautau")}
        over = {f: 0.0 for f in hist}
        via = {}
        hz, vz, prompt = {}, {}, {}
        n_pair = n_h = n_t = 0
        wsum = 0.0
        for e in range(len(arr["genWeight"])):
            w = float(arr["genWeight"][e])
            wsum += w
            r = one_event(arr["GenPart_pdgId"][e], arr["GenPart_genPartIdxMother"][e], arr["GenPart_pt"][e],
                          arr["GenPart_eta"][e], arr["GenPart_phi"][e], arr["GenPart_mass"][e],
                          arr["GenPart_statusFlags"][e])
            n_h += r["has_h"]
            n_t += r["has_t"]
            k = "+".join(r["hz"]) or "none"
            hz[k] = hz.get(k, 0) + 1
            k = "+".join(r["vz"]) or "none"
            vz[k] = vz.get(k, 0) + 1
            prompt[r["prompt"]] = prompt.get(r["prompt"], 0) + 1
            if r["mll"] is not None:
                n_pair += 1
                via[r["via"]] = via.get(r["via"], 0) + 1
                b = int(r["mll"])
                if b < len(EDGES) - 1:
                    hist[r["flav"]][b] += w
                    nhist[r["flav"]][b] += 1
                else:
                    over[r["flav"]] += w
        tot = {f: float(hist[f].sum() + over[f]) for f in hist}
        frac = {}
        for f in hist:
            if tot[f] == 0:
                continue
            frac[f] = {f"{lo}-{hi}": float(hist[f][lo:hi].sum() / tot[f]) for lo, hi in RANGES}
            frac[f][">130"] = float(over[f] / tot[f])
        res.update({"n_events_with_higgs_lepton_pair": n_pair, "lepton_pair_parent": via,
                    "m_ll_weighted_hist": {f: hist[f].tolist() for f in hist if tot[f]},
                    "m_ll_counts_hist": {f: nhist[f].tolist() for f in hist if tot[f]},
                    "m_ll_fractions_weighted": frac, "sum_genweight_genpart_events": wsum,
                    "higgs_vdecays": dict(sorted(hz.items(), key=lambda x: -x[1])),
                    "associated_vdecays": dict(sorted(vz.items(), key=lambda x: -x[1])),
                    "n_prompt_charged_leptons": {str(k): v for k, v in sorted(prompt.items())},
                    "n_events_with_higgs_in_genpart": n_h, "n_events_with_top_in_genpart": n_t,
                    "elapsed_sec": time.time() - t0})
        # genWeight magnitudes (information)
        absw = np.abs(gw_all)
        res["abs_genweight_min_max"] = [float(absw.min()), float(absw.max())]
        out["records"][str(rid)] = res
        print(rid, res["n_events_file"], f"neg {res['fraction_negative_genweight']:.4f}", "pairs", n_pair, via,
              {f: {k: round(v, 4) for k, v in frac[f].items()} for f in frac}, f"{res['elapsed_sec']:.0f}s", flush=True)
        (Path(a.out) / "gen_check.json").write_text(json.dumps(out, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
