"""
Check C: effect of trigger-mimicking (TM) cuts.

Reads: SIGNAL_FILES[0] (ggH, up to 50,000 events) and DATA_FILES
(Run2016G + Run2016H, up to 25,000 events each = 50,000 total).
BLINDING: no data diphoton mass in [115, 135] GeV is ever computed and
kept; only a count of candidates falling there is recorded.
"""
import json
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import uproot

sys.path.insert(0, r"C:\Users\matan\hgg-physchecks-20260915-2052\repo\studies\hgg_cms\physics_checks")
from file_list import SIGNAL_FILES, DATA_FILES
from common import (
    TRIGGER, BLIND_LO, BLIND_HI, diphoton_mass_massless, effective_sigma_68,
    histogram_mode, binomial_err, photon_v1_mask, photon_tm_mask,
    compute_isolation_proxies,
)

OUT_DIR = r"C:\Users\matan\hgg-physchecks-20260915-2052\repo\studies\hgg_cms\physics_checks"

BRANCHES = [
    TRIGGER,
    "Photon_pt", "Photon_eta", "Photon_phi",
    "Photon_r9", "Photon_hoe", "Photon_sieie",
    "Photon_pfRelIso03_all", "Photon_pfRelIso03_chg",
    "Photon_isScEtaEB", "Photon_isScEtaEE",
    "Photon_electronVeto", "Photon_mvaID_WP90",
]

ORTHOGONAL_TRIGGER_CANDIDATES = [
    "HLT_Ele27_WPTight_Gsf",
    "HLT_Ele23_WPLoose_Gsf",
    "HLT_Ele25_eta2p1_WPTight_Gsf",
    "HLT_DoubleEle33_CaloIdL_MW",
    "HLT_DoubleEle33_CaloIdL_GsfTrkIdVL",
]


def masks_for_event(arrays, i, want_tm):
    pt = arrays["Photon_pt"][i]
    eb = arrays["Photon_isScEtaEB"][i]
    ee = arrays["Photon_isScEtaEE"][i]
    evtoveto = arrays["Photon_electronVeto"][i]
    mva90 = arrays["Photon_mvaID_WP90"][i]
    v1 = photon_v1_mask(pt, eb, ee, evtoveto, mva90)
    if not want_tm:
        return v1
    hoe = arrays["Photon_hoe"][i]
    r9 = arrays["Photon_r9"][i]
    sieie = arrays["Photon_sieie"][i]
    iso_all = arrays["Photon_pfRelIso03_all"][i]
    iso_chg = arrays["Photon_pfRelIso03_chg"][i]
    i_ch, i_ph, i_tk = compute_isolation_proxies(pt, iso_all, iso_chg)
    tm = photon_tm_mask(pt, eb, ee, hoe, r9, sieie, i_ch, i_ph, i_tk)
    return v1 & tm


def leading_pair(arrays, i, mask):
    idx = np.nonzero(mask)[0]
    if len(idx) < 2:
        return None
    pt = arrays["Photon_pt"][i]
    order = idx[np.argsort(-pt[idx])]
    return order[0], order[1]


def diphoton_from_pair(arrays, i, j1, j2):
    pt = arrays["Photon_pt"][i]; eta = arrays["Photon_eta"][i]; phi = arrays["Photon_phi"][i]
    return diphoton_mass_massless(pt[j1], eta[j1], phi[j1], pt[j2], eta[j2], phi[j2])


# ---------------------------------------------------------------------
# C1: signal MC efficiency and HLT pass fraction, with/without TM
# ---------------------------------------------------------------------

def check_c1(arrays):
    n_events = len(arrays["Photon_pt"])
    result = {}
    for tm_label, want_tm in (("without_TM", False), ("with_TM", True)):
        n_offline_pass = 0
        n_offline_pass_bb = 0
        n_offline_pass_other = 0
        n_hlt_pass_given_offline = 0
        n_hlt_pass_given_offline_bb = 0
        n_hlt_pass_given_offline_other = 0

        for i in range(n_events):
            mask = masks_for_event(arrays, i, want_tm)
            pair = leading_pair(arrays, i, mask)
            if pair is None:
                continue
            j1, j2 = pair
            mgg = diphoton_from_pair(arrays, i, j1, j2)
            if not (100.0 < mgg < 180.0):
                continue
            pt = arrays["Photon_pt"][i]
            if not (pt[j1] > mgg / 3.0 and pt[j2] > mgg / 4.0):
                continue
            n_offline_pass += 1
            eb = arrays["Photon_isScEtaEB"][i]
            is_bb = bool(eb[j1] and eb[j2])
            if is_bb:
                n_offline_pass_bb += 1
            else:
                n_offline_pass_other += 1
            if arrays[TRIGGER][i]:
                n_hlt_pass_given_offline += 1
                if is_bb:
                    n_hlt_pass_given_offline_bb += 1
                else:
                    n_hlt_pass_given_offline_other += 1

        def frac(k, n):
            return {"k": k, "n": n, "frac": (k / n if n else None), "err": binomial_err(k, n)}

        result[tm_label] = {
            "n_events_read": n_events,
            "n_offline_selected": n_offline_pass,
            "offline_efficiency_rel_all_events": frac(n_offline_pass, n_events),
            "offline_efficiency_barrel_barrel": frac(n_offline_pass_bb, n_events),
            "offline_efficiency_other": frac(n_offline_pass_other, n_events),
            "hlt_pass_given_offline": frac(n_hlt_pass_given_offline, n_offline_pass),
            "hlt_pass_given_offline_barrel_barrel": frac(n_hlt_pass_given_offline_bb, n_offline_pass_bb),
            "hlt_pass_given_offline_other": frac(n_hlt_pass_given_offline_other, n_offline_pass_other),
        }

    fig, ax = plt.subplots(figsize=(6.5, 5))
    labels = ["without TM\n(all)", "with TM\n(all)", "without TM\n(BB)", "with TM\n(BB)",
              "without TM\n(other)", "with TM\n(other)"]
    vals = [
        result["without_TM"]["hlt_pass_given_offline"]["frac"],
        result["with_TM"]["hlt_pass_given_offline"]["frac"],
        result["without_TM"]["hlt_pass_given_offline_barrel_barrel"]["frac"],
        result["with_TM"]["hlt_pass_given_offline_barrel_barrel"]["frac"],
        result["without_TM"]["hlt_pass_given_offline_other"]["frac"],
        result["with_TM"]["hlt_pass_given_offline_other"]["frac"],
    ]
    errs = [
        result["without_TM"]["hlt_pass_given_offline"]["err"],
        result["with_TM"]["hlt_pass_given_offline"]["err"],
        result["without_TM"]["hlt_pass_given_offline_barrel_barrel"]["err"],
        result["with_TM"]["hlt_pass_given_offline_barrel_barrel"]["err"],
        result["without_TM"]["hlt_pass_given_offline_other"]["err"],
        result["with_TM"]["hlt_pass_given_offline_other"]["err"],
    ]
    vals = [v if v is not None else 0 for v in vals]
    errs = [e if e is not None else 0 for e in errs]
    colors = ["tab:orange", "tab:blue"] * 3
    ax.bar(range(6), vals, yerr=errs, color=colors, capsize=4)
    ax.set_xticks(range(6)); ax.set_xticklabels(labels, fontsize=8)
    ax.set_ylabel("fraction of offline-selected MC events passing HLT bit")
    ax.set_ylim(0, 1.05)
    ax.axhline(1.0, color="k", lw=0.8, ls=":")
    ax.set_title("Check C1: HLT pass fraction among offline-selected ggH MC,\nwithout vs with trigger-mimicking cuts")
    fig.tight_layout()
    fig.savefig(f"{OUT_DIR}/plots_C1_hlt_pass_fraction.png", dpi=140)
    plt.close(fig)

    return result


# ---------------------------------------------------------------------
# C2: data sidebands + blinded count, Z region, with/without TM
# ---------------------------------------------------------------------

def check_c2(all_data_arrays):
    result = {}
    zee_masses = {"without_TM": [], "with_TM": []}
    for tm_label, want_tm in (("without_TM", False), ("with_TM", True)):
        n_sideband = 0
        n_blinded = 0
        n_total_candidates = 0
        sideband_masses = []
        for arrays in all_data_arrays:
            n_events = len(arrays["Photon_pt"])
            for i in range(n_events):
                if not arrays[TRIGGER][i]:
                    continue
                mask = masks_for_event(arrays, i, want_tm)
                pair = leading_pair(arrays, i, mask)
                if pair is not None:
                    j1, j2 = pair
                    mgg = diphoton_from_pair(arrays, i, j1, j2)
                    pt = arrays["Photon_pt"][i]
                    if (100.0 < mgg < 180.0) and (pt[j1] > mgg / 3.0) and (pt[j2] > mgg / 4.0):
                        n_total_candidates += 1
                        if BLIND_LO <= mgg <= BLIND_HI:
                            n_blinded += 1
                        else:
                            n_sideband += 1
                            sideband_masses.append(mgg)

                # Z control region: electron veto inverted on BOTH photons
                pt_i = arrays["Photon_pt"][i]
                eb = arrays["Photon_isScEtaEB"][i]
                ee = arrays["Photon_isScEtaEE"][i]
                mva90 = arrays["Photon_mvaID_WP90"][i]
                evtoveto = arrays["Photon_electronVeto"][i]
                base = (pt_i > 20.0) & (eb | ee) & mva90 & (~evtoveto)
                if want_tm:
                    hoe = arrays["Photon_hoe"][i]; r9 = arrays["Photon_r9"][i]
                    sieie = arrays["Photon_sieie"][i]
                    iso_all = arrays["Photon_pfRelIso03_all"][i]; iso_chg = arrays["Photon_pfRelIso03_chg"][i]
                    i_ch, i_ph, i_tk = compute_isolation_proxies(pt_i, iso_all, iso_chg)
                    tm_mask = photon_tm_mask(pt_i, eb, ee, hoe, r9, sieie, i_ch, i_ph, i_tk)
                    base = base & tm_mask
                zpair = leading_pair(arrays, i, base)
                if zpair is not None:
                    j1, j2 = zpair
                    mz = diphoton_from_pair(arrays, i, j1, j2)
                    if 70.0 < mz < 110.0:
                        zee_masses[tm_label].append(mz)

        result[tm_label] = {
            "n_candidates_100_180": n_total_candidates,
            "n_sideband_lt115_or_gt135": n_sideband,
            "n_blinded_115_135_count_only": n_blinded,
            "sideband_min_GeV": float(min(sideband_masses)) if sideband_masses else None,
            "sideband_max_GeV": float(max(sideband_masses)) if sideband_masses else None,
        }

    zee_result = {}
    for tm_label in ("without_TM", "with_TM"):
        vals = np.array(zee_masses[tm_label])
        if len(vals) > 8:
            zee_result[tm_label] = {
                "n": int(len(vals)),
                "mean": float(vals.mean()),
                "median": float(np.median(vals)),
                "peak_mode": histogram_mode(vals, bin_width=1.0, lo=70, hi=110),
                "effective_sigma68": effective_sigma_68(vals),
            }
        else:
            zee_result[tm_label] = {"n": int(len(vals)), "note": "too few events for a peak estimate"}

    fig, ax = plt.subplots(figsize=(7, 5))
    bins = np.linspace(70, 110, 41)
    for tm_label, color in (("without_TM", "tab:orange"), ("with_TM", "tab:blue")):
        vals = zee_masses[tm_label]
        if len(vals) > 3:
            ax.hist(vals, bins=bins, histtype="step", lw=1.8, color=color,
                    label=f"{tm_label.replace('_', ' ')} (n={len(vals)})")
    ax.axvline(91.19, color="k", ls="--", lw=1, label="PDG $m_Z$ = 91.19 GeV")
    ax.set_xlabel(r"$m_{\gamma\gamma}$ (electron-veto-inverted pair) [GeV]")
    ax.set_ylabel("events / bin")
    ax.set_title("Check C2: Z control region, data, without vs. with TM cuts")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(f"{OUT_DIR}/plots_C2_zpeak_with_without_TM.png", dpi=140)
    plt.close(fig)

    return {"sidebands_and_blinded": result, "zee_control_region": zee_result}


# ---------------------------------------------------------------------
# C3: orthogonal trigger cross-check (best-effort)
# ---------------------------------------------------------------------

def check_c3(all_data_arrays, orthogonal_trigger, all_data_full_arrays):
    if orthogonal_trigger is None:
        return {"status": "SKIPPED",
                "reason": "none of the candidate single/double-electron trigger branches "
                          f"({ORTHOGONAL_TRIGGER_CANDIDATES}) were found in the data file(s)"}
    result = {"orthogonal_trigger_used": orthogonal_trigger, "status": "OK"}
    for tm_label, want_tm in (("without_TM", False), ("with_TM", True)):
        n_pass_ortho_and_zee = 0
        n_also_diphoton_hlt = 0
        for arrays in all_data_full_arrays:
            n_events = len(arrays["Photon_pt"])
            for i in range(n_events):
                if not arrays[orthogonal_trigger][i]:
                    continue
                pt_i = arrays["Photon_pt"][i]
                eb = arrays["Photon_isScEtaEB"][i]
                ee = arrays["Photon_isScEtaEE"][i]
                mva90 = arrays["Photon_mvaID_WP90"][i]
                evtoveto = arrays["Photon_electronVeto"][i]
                base = (pt_i > 20.0) & (eb | ee) & mva90 & (~evtoveto)
                if want_tm:
                    hoe = arrays["Photon_hoe"][i]; r9 = arrays["Photon_r9"][i]
                    sieie = arrays["Photon_sieie"][i]
                    iso_all = arrays["Photon_pfRelIso03_all"][i]; iso_chg = arrays["Photon_pfRelIso03_chg"][i]
                    i_ch, i_ph, i_tk = compute_isolation_proxies(pt_i, iso_all, iso_chg)
                    tm_mask = photon_tm_mask(pt_i, eb, ee, hoe, r9, sieie, i_ch, i_ph, i_tk)
                    base = base & tm_mask
                zpair = leading_pair(arrays, i, base)
                if zpair is None:
                    continue
                j1, j2 = zpair
                mz = diphoton_from_pair(arrays, i, j1, j2)
                if not (70.0 < mz < 110.0):
                    continue
                n_pass_ortho_and_zee += 1
                if arrays[TRIGGER][i]:
                    n_also_diphoton_hlt += 1
        result[tm_label] = {
            "n_pass_orthogonal_trigger_and_zee_selection": n_pass_ortho_and_zee,
            "n_also_pass_diphoton_hlt": n_also_diphoton_hlt,
            "fraction": (n_also_diphoton_hlt / n_pass_ortho_and_zee) if n_pass_ortho_and_zee else None,
            "err": binomial_err(n_also_diphoton_hlt, n_pass_ortho_and_zee) if n_pass_ortho_and_zee else None,
        }
    result["caveat"] = ("Rough estimate: small samples, and the orthogonal trigger's own "
                         "kinematic/ID requirements are not identical to the diphoton trigger's, "
                         "so this is a cross-check of plausibility, not a precision measurement.")
    return result


def main():
    fsig = uproot.open(SIGNAL_FILES[0]["url"])
    tsig = fsig["Events"]
    sig_arrays = tsig.arrays(BRANCHES, entry_start=SIGNAL_FILES[0]["entry_start"],
                              entry_stop=SIGNAL_FILES[0]["entry_stop"], library="np")

    # figure out orthogonal trigger availability once
    available_keys = tsig.keys()
    orthogonal_trigger = next((t for t in ORTHOGONAL_TRIGGER_CANDIDATES if t in available_keys), None)

    data_branches = list(BRANCHES)
    if orthogonal_trigger:
        data_branches.append(orthogonal_trigger)

    all_data_arrays = []
    for spec in DATA_FILES:
        f = uproot.open(spec["url"])
        t = f["Events"]
        keys = t.keys()
        use_branches = [b for b in data_branches if b in keys]
        arrays = t.arrays(use_branches, entry_start=spec["entry_start"],
                           entry_stop=spec["entry_stop"], library="np")
        all_data_arrays.append(arrays)
        if orthogonal_trigger and orthogonal_trigger not in keys:
            orthogonal_trigger = None  # must exist in ALL files used

    c1 = check_c1(sig_arrays)
    c2 = check_c2(all_data_arrays)
    c3 = check_c3(all_data_arrays, orthogonal_trigger, all_data_arrays)

    result = {
        "files_read": {"signal": SIGNAL_FILES, "data": DATA_FILES},
        "orthogonal_trigger_considered": ORTHOGONAL_TRIGGER_CANDIDATES,
        "orthogonal_trigger_found": orthogonal_trigger,
        "c1_signal_efficiency_and_hlt_pass": c1,
        "c2_data_sidebands_blinded_and_zee": c2,
        "c3_orthogonal_trigger_crosscheck": c3,
    }
    out_path = f"{OUT_DIR}/check_c_results.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, default=str)
    print(json.dumps(result, indent=2, default=str))
    print("wrote", out_path)


if __name__ == "__main__":
    main()
