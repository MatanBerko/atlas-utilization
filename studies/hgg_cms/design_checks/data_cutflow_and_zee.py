"""
Phase 2.2 design checks (Sections 2 and 5): a numbered cutflow on real
DoubleEG Run2016G data, and a Z->ee-as-diphoton cross-check (electron veto
INVERTED) to look for the 91.19 GeV Z peak using only photon-collection
branches, mirroring the tag-and-probe method CMS's own paper uses (see
DESIGN_SELECTION.md Section 1, Table 2).

BLINDING: this script never computes or reports anything derived from
events whose selected diphoton mass falls in [115, 135] GeV. The blinded
count itself is not even printed -- only "how many candidate events fall
in the two sidebands" and "how many were skipped as blinded" are reported.

Read-only, remote (HTTPS range requests), <=1000 events from ONE
Run2016G data file -- no full download.
"""
import json
import numpy as np
import uproot

URL = ("https://opendata.cern.ch/eos/opendata/cms/Run2016G/DoubleEG/NANOAOD/"
       "UL2016_MiniAODv2_NanoAODv9-v1/100000/11DA657F-5262-BD4A-AD1E-8E53BE62A601.root")
N = 1000
BLIND_LO, BLIND_HI = 115.0, 135.0
TRIGGER = "HLT_Diphoton30_18_R9Id_OR_IsoCaloId_AND_HE_R9Id_Mass90"
EB_EE_GAP = (1.4442, 1.566)


def diphoton_mass(pt1, eta1, phi1, pt2, eta2, phi2):
    def p4(pt, eta, phi):
        px = pt * np.cos(phi); py = pt * np.sin(phi); pz = pt * np.sinh(eta)
        e = np.sqrt(px**2 + py**2 + pz**2)  # massless photon
        return e, px, py, pz
    e1, px1, py1, pz1 = p4(pt1, eta1, phi1)
    e2, px2, py2, pz2 = p4(pt2, eta2, phi2)
    e, px, py, pz = e1 + e2, px1 + px2, py1 + py2, pz1 + pz2
    m2 = e**2 - px**2 - py**2 - pz**2
    return np.sqrt(m2) if m2 > 0 else np.nan


def effective_sigma_68(values):
    values = np.sort(values)
    n = len(values)
    k = int(np.ceil(0.683 * n))
    if k >= n or n < 4:
        return None
    widths = values[k:] - values[:n - k]
    i = np.argmin(widths)
    return 0.5 * float(widths[i])


def main():
    f = uproot.open(URL)
    tree = f["Events"]
    wanted = [
        TRIGGER,
        "Photon_pt", "Photon_eta", "Photon_phi",
        "Photon_isScEtaEB", "Photon_isScEtaEE",
        "Photon_mvaID_WP90", "Photon_electronVeto",
    ]
    arrays = tree.arrays(wanted, entry_stop=N, library="np")
    n_events = len(arrays[TRIGGER])

    cutflow = []
    cutflow.append(("0_all_events_read", n_events))

    trig_mask = arrays[TRIGGER]
    cutflow.append(("1_pass_trigger", int(trig_mask.sum())))

    # --- Real-photon selection cutflow (electron veto = True, standard) ---
    n_after_2photons_loose = 0
    n_after_eta_accept = 0
    n_after_id = 0
    n_after_eveto = 0
    n_candidate_pairs = 0
    sideband_masses = []
    n_blinded_skipped = 0

    # --- Zee-as-diphoton cutflow (electron veto INVERTED) ---
    zee_n_after_2photons_loose = 0
    zee_n_after_eta_accept = 0
    zee_n_after_evetofail = 0
    zee_masses = []

    for i in range(n_events):
        if not trig_mask[i]:
            continue
        pt = arrays["Photon_pt"][i]
        eta = arrays["Photon_eta"][i]
        phi = arrays["Photon_phi"][i]
        eb = arrays["Photon_isScEtaEB"][i]
        ee = arrays["Photon_isScEtaEE"][i]
        mva90 = arrays["Photon_mvaID_WP90"][i]
        evtoveto = arrays["Photon_electronVeto"][i]

        loose = pt > 20.0
        if loose.sum() >= 2:
            n_after_2photons_loose += 1
            zee_n_after_2photons_loose += 1

        accept_eta = (eb | ee) & loose
        if accept_eta.sum() >= 2:
            n_after_eta_accept += 1
            zee_n_after_eta_accept += 1

        # --- real-photon branch ---
        if (mva90 & accept_eta).sum() >= 2:
            n_after_id += 1
        pass_real = accept_eta & mva90 & evtoveto
        if pass_real.sum() >= 2:
            n_after_eveto += 1
            idx = np.nonzero(pass_real)[0]
            order = idx[np.argsort(-pt[idx])]
            j1, j2 = order[0], order[1]
            m = diphoton_mass(pt[j1], eta[j1], phi[j1], pt[j2], eta[j2], phi[j2])
            if not np.isnan(m) and 100.0 < m < 180.0:
                if BLIND_LO <= m <= BLIND_HI:
                    n_blinded_skipped += 1
                    n_candidate_pairs += 1
                    continue  # BLINDED: mass value never recorded
                n_candidate_pairs += 1
                sideband_masses.append(m)

        # --- Zee-as-diphoton branch: electron veto INVERTED (fails veto) ---
        pass_zee = accept_eta & (~evtoveto)
        if pass_zee.sum() >= 2:
            zee_n_after_evetofail += 1
            idx = np.nonzero(pass_zee)[0]
            order = idx[np.argsort(-pt[idx])]
            j1, j2 = order[0], order[1]
            m = diphoton_mass(pt[j1], eta[j1], phi[j1], pt[j2], eta[j2], phi[j2])
            if not np.isnan(m) and 50.0 < m < 130.0:
                zee_masses.append(m)

    cutflow.append(("2_ge2_photons_pt_gt_20", n_after_2photons_loose))
    cutflow.append(("3_ge2_in_eta_acceptance_EBorEE", n_after_eta_accept))
    cutflow.append(("4_ge2_pass_mvaID_WP90_and_eta", int(n_after_id)))
    cutflow.append(("5_ge2_pass_electronVeto_too_leading_pair_formed", n_after_eveto))
    cutflow.append(("6_pair_in_100_180_GeV_window_sideband_plus_blinded", n_candidate_pairs))
    cutflow.append(("6a_of_which_in_sidebands_lt115_or_gt135", len(sideband_masses)))
    cutflow.append(("6b_of_which_BLINDED_115_135_not_examined", n_blinded_skipped))

    zee_result = {
        "n_events_ge2_photons_pt20": zee_n_after_2photons_loose,
        "n_events_ge2_in_eta_acceptance": zee_n_after_eta_accept,
        "n_events_ge2_fail_electron_veto_pair_formed": zee_n_after_evetofail,
        "n_pairs_50_130_GeV": len(zee_masses),
    }
    if len(zee_masses) >= 4:
        zee_masses_arr = np.array(zee_masses)
        zee_result["mean_GeV"] = float(zee_masses_arr.mean())
        zee_result["rms_GeV"] = float(zee_masses_arr.std(ddof=1))
        sig68 = effective_sigma_68(zee_masses_arr)
        zee_result["effective_sigma68_GeV"] = sig68
        zee_result["masses_GeV"] = [round(float(x), 2) for x in zee_masses_arr]
    else:
        zee_result["note"] = "too few pairs in this 1000-event sample for a peak estimate"

    # Sideband summary only (no blinded values anywhere)
    sideband_result = {"n_sideband_pairs": len(sideband_masses)}
    if sideband_masses:
        sb = np.array(sideband_masses)
        sideband_result["min_GeV"] = float(sb.min())
        sideband_result["max_GeV"] = float(sb.max())
        sideband_result["n_below_115"] = int((sb < BLIND_LO).sum())
        sideband_result["n_above_135"] = int((sb > BLIND_HI).sum())

    results = {
        "trigger_used": TRIGGER,
        "n_events_read": n_events,
        "cutflow": cutflow,
        "sideband_check": sideband_result,
        "zee_electron_veto_inverted_check": zee_result,
        "blinding_note": "No mass value in [115, 135] GeV was ever computed-and-kept; "
                          "only a count of how many candidate pairs fell there is reported.",
    }
    out_path = (r"C:\Users\matan\hgg-design-20260915-2027\repo\studies\hgg_cms\design_checks"
                r"\data_cutflow_and_zee_results.json")
    with open(out_path, "w", encoding="utf-8") as fjson:
        json.dump(results, fjson, indent=2)
    print(json.dumps(results, indent=2))
    print("wrote", out_path)


if __name__ == "__main__":
    main()
