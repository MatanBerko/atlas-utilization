"""
Phase 2.2 design check (Section 3): how often does the default NanoAOD
primary vertex (PV, chosen by highest sum-pT^2, see PV_score's own doc
string) land within 1 cm of the true Higgs-production vertex, and what
does that do to the reconstructed diphoton mass?

Read-only, remote (HTTPS range requests), <=1000 events from ONE postVFP
ggH signal file -- no full download, no data file touched here (signal
only, so no blinding concern).

NanoAOD does not store the photon supercluster (x,y,z) position, only the
already-vertex-pointed eta/phi -- so a literal "recompute the mass under a
different vertex hypothesis" is not possible from these branches alone.
Instead this script uses the natural split that IS possible: NanoAOD's own
Photon_pt/eta/phi already reflect whatever vertex CMS's central
reconstruction picked for this event (the same PV_x/y/z branch), so
comparing the truth-matched diphoton mass for events where that PV happens
to already be close to the true vertex, vs. events where it is not, is a
direct, honest measurement of the real effect -- not a simulation of a
smarter algorithm that could hypothetically be run instead.
"""
import json
import numpy as np
import uproot

URL = ("https://opendata.cern.ch/eos/opendata/cms/mc/RunIISummer20UL16NanoAODv9/"
       "GluGluHToGG_M-125_TuneCP5_13TeV-powheg-pythia8/NANOAODSIM/"
       "106X_mcRun2_asymptotic_v17-v1/40000/3231834B-7A6E-4840-8627-C97FDCF67268.root")
N = 1000
DR_MATCH = 0.1
VTX_MATCH_CM = 1.0  # 1 cm, as specified in the task


def deltaR(eta1, phi1, eta2, phi2):
    dphi = np.abs(phi1 - phi2)
    dphi = np.where(dphi > np.pi, 2 * np.pi - dphi, dphi)
    return np.sqrt((eta1 - eta2) ** 2 + dphi ** 2)


def effective_sigma_68(values):
    """Half-width of the shortest interval containing 68.3% of `values`."""
    values = np.sort(values)
    n = len(values)
    k = int(np.ceil(0.683 * n))
    if k >= n:
        return 0.5 * (values[-1] - values[0])
    widths = values[k:] - values[:n - k]
    i = np.argmin(widths)
    return 0.5 * widths[i]


def main():
    f = uproot.open(URL)
    tree = f["Events"]
    wanted = [
        "GenVtx_x", "GenVtx_y", "GenVtx_z",
        "PV_x", "PV_y", "PV_z", "PV_npvsGood",
        "GenPart_pt", "GenPart_eta", "GenPart_phi", "GenPart_mass",
        "GenPart_pdgId", "GenPart_genPartIdxMother", "GenPart_status",
        "Photon_pt", "Photon_eta", "Photon_phi", "Photon_mass",
    ]
    arrays = tree.arrays(wanted, entry_stop=N, library="np")

    n_events = len(arrays["PV_z"])
    dz = np.abs(arrays["PV_z"] - arrays["GenVtx_z"])
    n_vtx_ok = int(np.sum(dz < VTX_MATCH_CM))
    frac_vtx_ok = n_vtx_ok / n_events
    frac_vtx_ok_err = np.sqrt(frac_vtx_ok * (1 - frac_vtx_ok) / n_events)

    mass_all = {"right": [], "wrong": []}
    n_matched = 0
    n_no_higgs_photons = 0
    n_match_failed = 0

    for i in range(n_events):
        pdg = arrays["GenPart_pdgId"][i]
        mother = arrays["GenPart_genPartIdxMother"][i]
        is_photon = pdg == 22
        # direct daughters of a Higgs (pdgId 25)
        mother_pdg = np.full(len(pdg), 0)
        valid_mother = mother >= 0
        mother_pdg[valid_mother] = pdg[mother[valid_mother]]
        is_h_daughter = is_photon & valid_mother & (mother_pdg == 25)
        idx_h_gammas = np.nonzero(is_h_daughter)[0]
        if len(idx_h_gammas) != 2:
            n_no_higgs_photons += 1
            continue

        g_eta = arrays["GenPart_eta"][i][idx_h_gammas]
        g_phi = arrays["GenPart_phi"][i][idx_h_gammas]

        reco_eta = arrays["Photon_eta"][i]
        reco_phi = arrays["Photon_phi"][i]
        reco_pt = arrays["Photon_pt"][i]
        reco_mass = arrays["Photon_mass"][i]
        if len(reco_eta) < 2:
            n_match_failed += 1
            continue

        matched_idx = []
        used = set()
        ok = True
        for k in range(2):
            drs = deltaR(g_eta[k], g_phi[k], reco_eta, reco_phi)
            order = np.argsort(drs)
            found = None
            for j in order:
                if j not in used and drs[j] < DR_MATCH:
                    found = j
                    break
            if found is None:
                ok = False
                break
            used.add(found)
            matched_idx.append(found)
        if not ok:
            n_match_failed += 1
            continue

        j1, j2 = matched_idx
        pt1, pt2 = reco_pt[j1], reco_pt[j2]
        eta1, eta2 = reco_eta[j1], reco_eta[j2]
        phi1, phi2 = reco_phi[j1], reco_phi[j2]
        m1, m2 = reco_mass[j1], reco_mass[j2]

        def p4(pt, eta, phi, m):
            px = pt * np.cos(phi); py = pt * np.sin(phi); pz = pt * np.sinh(eta)
            e = np.sqrt(px**2 + py**2 + pz**2 + m**2)
            return e, px, py, pz

        e1, px1, py1, pz1 = p4(pt1, eta1, phi1, m1)
        e2, px2, py2, pz2 = p4(pt2, eta2, phi2, m2)
        e, px, py, pz = e1 + e2, px1 + px2, py1 + py2, pz1 + pz2
        m2gg = e**2 - px**2 - py**2 - pz**2
        if m2gg <= 0:
            n_match_failed += 1
            continue
        mgg = float(np.sqrt(m2gg))

        n_matched += 1
        bucket = "right" if dz[i] < VTX_MATCH_CM else "wrong"
        mass_all[bucket].append(mgg)

    results = {
        "n_events_read": n_events,
        "vertex_match_threshold_cm": VTX_MATCH_CM,
        "n_events_pv_within_1cm_of_true_vertex": n_vtx_ok,
        "fraction_pv_within_1cm": frac_vtx_ok,
        "fraction_pv_within_1cm_stat_err": frac_vtx_ok_err,
        "n_events_no_2_higgs_daughter_photons_in_GenPart": n_no_higgs_photons,
        "n_events_truth_match_failed_or_lt2_reco_photons": n_match_failed,
        "n_events_truth_matched_diphoton": n_matched,
    }
    for bucket in ("right", "wrong"):
        m = np.array(mass_all[bucket])
        if len(m) > 2:
            results[f"{bucket}_vertex"] = {
                "n": len(m),
                "mean_mgg_GeV": float(m.mean()),
                "rms_GeV": float(m.std(ddof=1)),
                "rms_stat_err_GeV": float(m.std(ddof=1) / np.sqrt(2 * (len(m) - 1))),
                "effective_sigma68_GeV": float(effective_sigma_68(m - 125.0)),
            }
        else:
            results[f"{bucket}_vertex"] = {"n": len(m), "note": "too few events for a resolution estimate"}

    out_path = r"C:\Users\matan\hgg-design-20260915-2027\repo\studies\hgg_cms\design_checks\vertex_study_results.json"
    with open(out_path, "w", encoding="utf-8") as fjson:
        json.dump(results, fjson, indent=2)
    print(json.dumps(results, indent=2))
    print("wrote", out_path)


if __name__ == "__main__":
    main()
