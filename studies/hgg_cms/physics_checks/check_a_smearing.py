"""
Check A: is simulated (MC) photon energy already smeared to match data
resolution, or not?

Reads: SIGNAL_FILES[0] (ggH, up to 50,000 events) and DATA_FILES (Run2016G
+ Run2016H, up to 25,000 events each = 50,000 total) -- see file_list.py
for exact URLs/ranges. Photon_eCorr and Photon_pt for pT>20 GeV photons;
GenPart_* for the truth-matched response check (signal only).
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
from common import deltaR, effective_sigma_68

OUT_DIR = r"C:\Users\matan\hgg-physchecks-20260915-2052\repo\studies\hgg_cms\physics_checks"


def read_photon_pt20(url, entry_start, entry_stop):
    f = uproot.open(url)
    t = f["Events"]
    arrays = t.arrays(
        ["Photon_pt", "Photon_eta", "Photon_eCorr",
         "Photon_isScEtaEB", "Photon_isScEtaEE"],
        entry_start=entry_start, entry_stop=entry_stop, library="np",
    )
    pt = np.concatenate(arrays["Photon_pt"])
    ecorr = np.concatenate(arrays["Photon_eCorr"])
    eb = np.concatenate(arrays["Photon_isScEtaEB"])
    ee = np.concatenate(arrays["Photon_isScEtaEE"])
    sel = pt > 20.0
    return ecorr[sel], eb[sel], ee[sel]


def summarize_ecorr(ecorr, eb, ee, label):
    out = {"label": label, "n": int(len(ecorr))}
    if len(ecorr) == 0:
        return out
    out["n_exactly_1p0"] = int(np.sum(ecorr == 1.0))
    out["frac_exactly_1p0"] = float(np.mean(ecorr == 1.0))
    out["mean"] = float(np.mean(ecorr))
    out["rms"] = float(np.std(ecorr, ddof=1))
    out["p1"] = float(np.percentile(ecorr, 1))
    out["p99"] = float(np.percentile(ecorr, 99))
    for region_name, mask in (("barrel", eb), ("endcap", ee)):
        sub = ecorr[mask]
        if len(sub) > 1:
            out[region_name] = {
                "n": int(len(sub)),
                "mean": float(np.mean(sub)),
                "rms": float(np.std(sub, ddof=1)),
                "frac_exactly_1p0": float(np.mean(sub == 1.0)),
            }
    return out


def step2_ecorr_distribution():
    mc_ecorr, mc_eb, mc_ee = read_photon_pt20(
        SIGNAL_FILES[0]["url"], SIGNAL_FILES[0]["entry_start"], SIGNAL_FILES[0]["entry_stop"]
    )
    data_ecorr_list, data_eb_list, data_ee_list = [], [], []
    for spec in DATA_FILES:
        e, eb, ee = read_photon_pt20(spec["url"], spec["entry_start"], spec["entry_stop"])
        data_ecorr_list.append(e); data_eb_list.append(eb); data_ee_list.append(ee)
    data_ecorr = np.concatenate(data_ecorr_list)
    data_eb = np.concatenate(data_eb_list)
    data_ee = np.concatenate(data_ee_list)

    mc_summary = summarize_ecorr(mc_ecorr, mc_eb, mc_ee, "MC (ggH)")
    data_summary = summarize_ecorr(data_ecorr, data_eb, data_ee, "data (Run2016G+H)")

    fig, ax = plt.subplots(figsize=(7, 5))
    bins = np.linspace(0.90, 1.10, 101)
    ax.hist(mc_ecorr, bins=bins, histtype="step", density=True, lw=1.8,
            color="tab:red", label=f"MC ggH signal (n={len(mc_ecorr)})")
    ax.hist(data_ecorr, bins=bins, histtype="step", density=True, lw=1.8,
            color="k", label=f"data Run2016G+H (n={len(data_ecorr)})")
    ax.set_xlabel("Photon_eCorr (ratio of calibrated / miniAOD energy)")
    ax.set_ylabel("events / bin (normalized)")
    ax.set_title("Check A2: Photon_eCorr, MC vs. data ($p_T$ > 20 GeV)")
    ax.legend(fontsize=9)
    fig.tight_layout()
    fig.savefig(f"{OUT_DIR}/plots_A2_eCorr_mc_vs_data.png", dpi=140)
    plt.close(fig)

    return {"mc": mc_summary, "data": data_summary}


def step3_response_check():
    f = uproot.open(SIGNAL_FILES[0]["url"])
    t = f["Events"]
    wanted = [
        "Photon_pt", "Photon_eta", "Photon_phi", "Photon_eCorr",
        "Photon_r9", "Photon_isScEtaEB", "Photon_isScEtaEE",
        "GenPart_pt", "GenPart_eta", "GenPart_phi",
        "GenPart_pdgId", "GenPart_genPartIdxMother",
    ]
    arrays = t.arrays(wanted, entry_start=SIGNAL_FILES[0]["entry_start"],
                       entry_stop=SIGNAL_FILES[0]["entry_stop"], library="np")
    n_events = len(arrays["Photon_pt"])

    categories = {"barrel_highR9": [], "barrel_other": [], "endcap": []}
    categories_precorr = {"barrel_highR9": [], "barrel_other": [], "endcap": []}

    for i in range(n_events):
        pdg = arrays["GenPart_pdgId"][i]
        mother = arrays["GenPart_genPartIdxMother"][i]
        is_photon = pdg == 22
        mother_pdg = np.zeros(len(pdg), dtype=int)
        valid = mother >= 0
        mother_pdg[valid] = pdg[mother[valid]]
        is_h_daughter = is_photon & valid & (mother_pdg == 25)
        idx_gamma = np.nonzero(is_h_daughter)[0]
        if len(idx_gamma) != 2:
            continue

        reco_pt = arrays["Photon_pt"][i]
        reco_eta = arrays["Photon_eta"][i]
        reco_phi = arrays["Photon_phi"][i]
        reco_ecorr = arrays["Photon_eCorr"][i]
        reco_r9 = arrays["Photon_r9"][i]
        reco_eb = arrays["Photon_isScEtaEB"][i]
        reco_ee = arrays["Photon_isScEtaEE"][i]
        if len(reco_pt) < 1:
            continue

        used = set()
        for k in idx_gamma:
            g_pt = arrays["GenPart_pt"][i][k]
            g_eta = arrays["GenPart_eta"][i][k]
            g_phi = arrays["GenPart_phi"][i][k]
            drs = deltaR(g_eta, g_phi, reco_eta, reco_phi)
            order = np.argsort(drs)
            match = None
            for j in order:
                if j not in used and drs[j] < 0.1:
                    match = j
                    break
            if match is None:
                continue
            used.add(match)

            response = reco_pt[match] / g_pt
            response_precorr = (reco_pt[match] / reco_ecorr[match]) / g_pt

            if reco_eb[match] and reco_r9[match] > 0.94:
                cat = "barrel_highR9"
            elif reco_eb[match]:
                cat = "barrel_other"
            elif reco_ee[match]:
                cat = "endcap"
            else:
                continue
            categories[cat].append(response)
            categories_precorr[cat].append(response_precorr)

    result = {}
    for cat in categories:
        vals = np.array(categories[cat])
        vals_pre = np.array(categories_precorr[cat])
        entry = {"n": int(len(vals))}
        if len(vals) > 3:
            entry["mean"] = float(vals.mean())
            entry["rms"] = float(vals.std(ddof=1))
            entry["effective_sigma68"] = effective_sigma_68(vals)
            entry["precorrection_mean"] = float(vals_pre.mean())
            entry["precorrection_rms"] = float(vals_pre.std(ddof=1))
            entry["precorrection_effective_sigma68"] = effective_sigma_68(vals_pre)
        result[cat] = entry

    fig, axes = plt.subplots(1, 3, figsize=(15, 4.5), sharey=True)
    for ax, cat in zip(axes, ("barrel_highR9", "barrel_other", "endcap")):
        vals = np.array(categories[cat])
        vals_pre = np.array(categories_precorr[cat])
        bins = np.linspace(0.85, 1.15, 61)
        if len(vals):
            ax.hist(vals, bins=bins, histtype="step", lw=1.8, color="tab:blue",
                     label=f"corrected pt (n={len(vals)})")
            ax.hist(vals_pre, bins=bins, histtype="step", lw=1.8, color="tab:orange",
                     label="pre-correction (pt/eCorr)")
        ax.set_xlabel("Photon_pt / GenPart_pt")
        ax.set_title(cat)
        ax.legend(fontsize=8)
    axes[0].set_ylabel("photons / bin")
    fig.suptitle("Check A3: MC photon energy response, truth-matched Higgs-daughter photons")
    fig.tight_layout()
    fig.savefig(f"{OUT_DIR}/plots_A3_response_mc.png", dpi=140)
    plt.close(fig)

    return result


def step4_interpretation(mc_summary):
    ecorr_is_identity = mc_summary["frac_exactly_1p0"] > 0.99
    rms = mc_summary["rms"]
    mean_offset = abs(mc_summary["mean"] - 1.0)
    if ecorr_is_identity:
        verdict = "not applied (Photon_eCorr is identically 1 in MC)"
    elif rms >= 0.003 and mean_offset <= 0.003:
        verdict = "MC smearing appears applied"
    else:
        verdict = "unclear"
    return {
        "ecorr_frac_exactly_1": mc_summary["frac_exactly_1p0"],
        "ecorr_rms": rms,
        "ecorr_mean_offset_from_1": mean_offset,
        "preset_rule": "RMS>=0.003 and |mean-1|<=0.003 => smearing applied; "
                        "eCorr==1 always => not applied; otherwise unclear",
        "verdict": verdict,
    }


def main():
    step2 = step2_ecorr_distribution()
    step3 = step3_response_check()
    step4 = step4_interpretation(step2["mc"])

    result = {
        "files_read": {
            "signal": SIGNAL_FILES,
            "data": DATA_FILES,
        },
        "step2_ecorr_distribution": step2,
        "step3_response_check_truth_matched_mc": step3,
        "step4_preset_interpretation": step4,
    }
    out_path = f"{OUT_DIR}/check_a_results.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
    print(json.dumps(result, indent=2))
    print("wrote", out_path)


if __name__ == "__main__":
    main()
