"""
Check B: which point are NanoAOD photon directions measured from (B1),
and what is the real diphoton mass resolution after the full selection,
with truth-matched photons (B2)?

Reads: SIGNAL_FILES[0] only (ggH, up to 50,000 events) -- signal MC only,
no blinding concern. Branches: Photon_*, GenPart_*, GenVtx_x/y/z, PV_x/y/z,
PV_npvsGood, HLT trigger bit.
"""
import json
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import uproot

sys.path.insert(0, r"C:\Users\matan\hgg-physchecks-20260915-2052\repo\studies\hgg_cms\physics_checks")
from file_list import SIGNAL_FILES
from common import (
    TRIGGER, deltaR, diphoton_mass_massless, effective_sigma_68,
    histogram_mode, bootstrap_stat, photon_v1_mask, photon_tm_mask,
    compute_isolation_proxies,
)

OUT_DIR = r"C:\Users\matan\hgg-physchecks-20260915-2052\repo\studies\hgg_cms\physics_checks"
R_EFF_DEFAULT = 129.0   # cm, barrel ECAL radius
Z_EFF_DEFAULT = 314.0   # cm, endcap ECAL z


def load_all():
    f = uproot.open(SIGNAL_FILES[0]["url"])
    t = f["Events"]
    wanted = [
        TRIGGER,
        "Photon_pt", "Photon_eta", "Photon_phi",
        "Photon_r9", "Photon_hoe", "Photon_sieie",
        "Photon_pfRelIso03_all", "Photon_pfRelIso03_chg",
        "Photon_isScEtaEB", "Photon_isScEtaEE",
        "Photon_electronVeto", "Photon_mvaID_WP90",
        "GenPart_pt", "GenPart_eta", "GenPart_phi",
        "GenPart_pdgId", "GenPart_genPartIdxMother",
        "GenVtx_x", "GenVtx_y", "GenVtx_z",
        "PV_x", "PV_y", "PV_z", "PV_npvsGood",
    ]
    return t.arrays(wanted, entry_start=SIGNAL_FILES[0]["entry_start"],
                     entry_stop=SIGNAL_FILES[0]["entry_stop"], library="np")


def find_higgs_daughter_photons(arrays, i):
    pdg = arrays["GenPart_pdgId"][i]
    mother = arrays["GenPart_genPartIdxMother"][i]
    is_photon = pdg == 22
    mother_pdg = np.zeros(len(pdg), dtype=int)
    valid = mother >= 0
    mother_pdg[valid] = pdg[mother[valid]]
    is_h_daughter = is_photon & valid & (mother_pdg == 25)
    return np.nonzero(is_h_daughter)[0]


def truth_match_photons(arrays, i, cand_idx):
    """Match up to 2 Higgs-daughter gen photons to reco photons in `cand_idx`
    (indices into the event's Photon_* arrays already passing some cut)."""
    idx_gamma = find_higgs_daughter_photons(arrays, i)
    if len(idx_gamma) != 2 or len(cand_idx) < 1:
        return None
    reco_eta = arrays["Photon_eta"][i]
    reco_phi = arrays["Photon_phi"][i]
    used = set()
    matches = {}
    for k in idx_gamma:
        g_eta = arrays["GenPart_eta"][i][k]
        g_phi = arrays["GenPart_phi"][i][k]
        drs = deltaR(g_eta, g_phi, reco_eta[cand_idx], reco_phi[cand_idx])
        order = np.argsort(drs)
        for jj in order:
            j = cand_idx[jj]
            if j not in used and drs[jj] < 0.1:
                used.add(j)
                matches[k] = j
                break
    if len(matches) != 2:
        return None
    return matches  # {gen_idx: reco_idx}


def photon_pass_v1_tm(arrays, i):
    pt = arrays["Photon_pt"][i]
    eb = arrays["Photon_isScEtaEB"][i]
    ee = arrays["Photon_isScEtaEE"][i]
    evtoveto = arrays["Photon_electronVeto"][i]
    mva90 = arrays["Photon_mvaID_WP90"][i]
    v1 = photon_v1_mask(pt, eb, ee, evtoveto, mva90)
    hoe = arrays["Photon_hoe"][i]
    r9 = arrays["Photon_r9"][i]
    sieie = arrays["Photon_sieie"][i]
    iso_all = arrays["Photon_pfRelIso03_all"][i]
    iso_chg = arrays["Photon_pfRelIso03_chg"][i]
    i_ch, i_ph, i_tk = compute_isolation_proxies(pt, iso_all, iso_chg)
    tm = photon_tm_mask(pt, eb, ee, hoe, r9, sieie, i_ch, i_ph, i_tk)
    return v1 & tm


# ---------------------------------------------------------------------
# B1: which vertex are stored photon directions referenced to?
# ---------------------------------------------------------------------

def run_b1(arrays):
    n_events = len(arrays["Photon_pt"])
    rows_barrel = []  # (deltacot_x_RSC, genvtx_z, pv_z)
    rows_endcap = []  # (deltacot_x_Rhit, genvtx_z, pv_z, r_hit)

    for i in range(n_events):
        pass_v1tm = photon_pass_v1_tm(arrays, i)
        cand_idx = np.nonzero(pass_v1tm)[0]
        if len(cand_idx) < 1:
            continue
        matches = truth_match_photons(arrays, i, cand_idx)
        if matches is None:
            continue

        gvz = arrays["GenVtx_z"][i]
        pvz = arrays["PV_z"][i]
        for gen_idx, reco_idx in matches.items():
            eta_reco = arrays["Photon_eta"][i][reco_idx]
            eta_gen = arrays["GenPart_eta"][i][gen_idx]
            cot_reco = np.sinh(eta_reco)
            cot_gen = np.sinh(eta_gen)
            dcot = cot_reco - cot_gen
            is_eb = arrays["Photon_isScEtaEB"][i][reco_idx]
            is_ee = arrays["Photon_isScEtaEE"][i][reco_idx]
            if is_eb:
                y = dcot * R_EFF_DEFAULT
                rows_barrel.append((y, gvz, pvz))
            elif is_ee:
                r_hit = Z_EFF_DEFAULT / abs(cot_reco) if cot_reco != 0 else np.nan
                y = dcot * r_hit
                rows_endcap.append((y, gvz, pvz, r_hit))

    def regress(y, x):
        y = np.asarray(y); x = np.asarray(x)
        n = len(y)
        if n < 5:
            return None
        xm, ym = x.mean(), y.mean()
        sxx = np.sum((x - xm) ** 2)
        sxy = np.sum((x - xm) * (y - ym))
        slope = sxy / sxx
        intercept = ym - slope * xm
        resid = y - (slope * x + intercept)
        dof = n - 2
        s2 = np.sum(resid ** 2) / dof if dof > 0 else np.nan
        slope_err = np.sqrt(s2 / sxx) if sxx > 0 else np.nan
        intercept_err = np.sqrt(s2 * (1.0 / n + xm ** 2 / sxx))
        ss_tot = np.sum((y - ym) ** 2)
        r2 = 1 - np.sum(resid ** 2) / ss_tot if ss_tot > 0 else np.nan
        corr = np.corrcoef(x, y)[0, 1]
        return {
            "n": int(n), "slope": float(slope), "slope_err": float(slope_err),
            "intercept": float(intercept), "intercept_err": float(intercept_err),
            "r2": float(r2), "pearson_r": float(corr), "residuals": resid,
        }

    result = {"n_barrel": len(rows_barrel), "n_endcap": len(rows_endcap)}

    if len(rows_barrel) >= 5:
        y_b = [r[0] for r in rows_barrel]
        gvz_b = [r[1] for r in rows_barrel]
        pvz_b = [r[2] for r in rows_barrel]
        x_i = np.array(gvz_b)  # hyp i: ref = 0
        x_ii = np.array(gvz_b) - np.array(pvz_b)  # hyp ii: ref = PV_z

        fit_i = regress(y_b, x_i)
        fit_ii = regress(y_b, x_ii)

        # residual cross-correlation check: does fit_ii's residual still
        # correlate with PV_z itself (a sign hyp i would fit better)?
        resid_ii_vs_pvz = float(np.corrcoef(fit_ii["residuals"], pvz_b)[0, 1]) if fit_ii else None
        resid_i_vs_pvz = float(np.corrcoef(fit_i["residuals"], pvz_b)[0, 1]) if fit_i else None

        result["barrel"] = {
            "hypothesis_i_ref_origin": {k: v for k, v in fit_i.items() if k != "residuals"},
            "hypothesis_ii_ref_PV": {k: v for k, v in fit_ii.items() if k != "residuals"},
            "hypothesis_i_residual_corr_with_PVz": resid_i_vs_pvz,
            "hypothesis_ii_residual_corr_with_PVz": resid_ii_vs_pvz,
            "hypothesis_iii_beamspot": "SKIPPED: no beamspot position branch found in NanoAODv9 Events tree",
        }

        fig, axes = plt.subplots(1, 2, figsize=(11, 5))
        axes[0].scatter(x_i, y_b, s=4, alpha=0.4, color="tab:blue")
        lims = [min(x_i.min(), y_b[0]), max(x_i.max(), max(y_b))]
        xs = np.linspace(x_i.min(), x_i.max(), 10)
        axes[0].plot(xs, fit_i["slope"] * xs + fit_i["intercept"], color="red",
                     label=f"fit: slope={fit_i['slope']:.2f}±{fit_i['slope_err']:.2f}")
        axes[0].plot(xs, xs, "k--", lw=1, label="slope=1 (expected if correct)")
        axes[0].set_xlabel("GenVtx_z - 0  [cm]")
        axes[0].set_ylabel(r"$\Delta\cot\theta \times R_{SC}$  [cm]")
        axes[0].set_title("Hypothesis (i): reference = detector origin")
        axes[0].legend(fontsize=8)

        axes[1].scatter(x_ii, y_b, s=4, alpha=0.4, color="tab:green")
        xs2 = np.linspace(x_ii.min(), x_ii.max(), 10)
        axes[1].plot(xs2, fit_ii["slope"] * xs2 + fit_ii["intercept"], color="red",
                     label=f"fit: slope={fit_ii['slope']:.2f}±{fit_ii['slope_err']:.2f}")
        axes[1].plot(xs2, xs2, "k--", lw=1, label="slope=1 (expected if correct)")
        axes[1].set_xlabel("GenVtx_z - PV_z  [cm]")
        axes[1].set_ylabel(r"$\Delta\cot\theta \times R_{SC}$  [cm]")
        axes[1].set_title("Hypothesis (ii): reference = default PV")
        axes[1].legend(fontsize=8)
        fig.suptitle("Check B1: which vertex are stored barrel photon directions referenced to?")
        fig.tight_layout()
        fig.savefig(f"{OUT_DIR}/plots_B1_regression_barrel.png", dpi=140)
        plt.close(fig)

    if len(rows_endcap) >= 5:
        y_e = [r[0] for r in rows_endcap]
        gvz_e = [r[1] for r in rows_endcap]
        pvz_e = [r[2] for r in rows_endcap]
        x_i = np.array(gvz_e)
        x_ii = np.array(gvz_e) - np.array(pvz_e)
        fit_i = regress(y_e, x_i)
        fit_ii = regress(y_e, x_ii)
        result["endcap"] = {
            "hypothesis_i_ref_origin": {k: v for k, v in fit_i.items() if k != "residuals"} if fit_i else None,
            "hypothesis_ii_ref_PV": {k: v for k, v in fit_ii.items() if k != "residuals"} if fit_ii else None,
            "note": "R_SC here is the photon's own approximate ECAL-hit radius, "
                    "r_hit = Z_EFF / |sinh(eta_reco)|, Z_EFF=314cm -- an approximation, "
                    "not an exact geometric radius.",
        }
        fig, ax = plt.subplots(figsize=(6, 5))
        ax.scatter(x_ii, y_e, s=4, alpha=0.4, color="tab:purple")
        xs = np.linspace(x_ii.min(), x_ii.max(), 10)
        if fit_ii:
            ax.plot(xs, fit_ii["slope"] * xs + fit_ii["intercept"], color="red",
                    label=f"fit: slope={fit_ii['slope']:.2f}±{fit_ii['slope_err']:.2f}")
        ax.plot(xs, xs, "k--", lw=1, label="slope=1")
        ax.set_xlabel("GenVtx_z - PV_z [cm]")
        ax.set_ylabel(r"$\Delta\cot\theta \times r_{hit}$ [cm]")
        ax.set_title("Check B1 (endcap): hypothesis (ii)")
        ax.legend(fontsize=8)
        fig.tight_layout()
        fig.savefig(f"{OUT_DIR}/plots_B1_regression_endcap.png", dpi=140)
        plt.close(fig)

    return result


# ---------------------------------------------------------------------
# B2: re-aiming test
# ---------------------------------------------------------------------

def eta_from_vertex(eta_stored, is_eb, z_ref_old, z_ref_new, R_EFF, Z_EFF):
    cot_old = np.sinh(eta_stored)
    if is_eb:
        r_hit = R_EFF
        z_hit = z_ref_old + r_hit * cot_old
    else:
        z_hit = np.sign(eta_stored) * Z_EFF
        with np.errstate(divide="ignore", invalid="ignore"):
            r_hit = np.where(cot_old != 0, (z_hit - z_ref_old) / cot_old, np.nan)
    with np.errstate(divide="ignore", invalid="ignore"):
        cot_new = np.where(r_hit != 0, (z_hit - z_ref_new) / r_hit, np.nan)
    return np.arcsinh(cot_new)


def event_passes_full_selection(arrays, i, pass_mask):
    """Leading two photons passing pass_mask; scaled-pT + mass-window cuts."""
    if not arrays[TRIGGER][i]:
        return None
    idx = np.nonzero(pass_mask)[0]
    if len(idx) < 2:
        return None
    pt = arrays["Photon_pt"][i]
    order = idx[np.argsort(-pt[idx])]
    j1, j2 = order[0], order[1]
    eta = arrays["Photon_eta"][i]
    phi = arrays["Photon_phi"][i]
    mgg = diphoton_mass_massless(pt[j1], eta[j1], phi[j1], pt[j2], eta[j2], phi[j2])
    if not (100.0 < mgg < 180.0):
        return None
    if not (pt[j1] > mgg / 3.0 and pt[j2] > mgg / 4.0):
        return None
    return j1, j2, mgg


def recompute_mass_option(arrays, i, j1, j2, z_ref_old_arr, z_ref_new, R_EFF, Z_EFF):
    pt = arrays["Photon_pt"][i]
    eta = arrays["Photon_eta"][i]
    phi = arrays["Photon_phi"][i]
    eb = arrays["Photon_isScEtaEB"][i]
    new_etas = {}
    for j in (j1, j2):
        z_old = z_ref_old_arr[i] if np.isscalar(z_ref_old_arr[i]) else z_ref_old_arr
        new_etas[j] = eta_from_vertex(eta[j], eb[j], z_ref_old_arr, z_ref_new, R_EFF, Z_EFF)
    return diphoton_mass_massless(pt[j1], new_etas[j1], phi[j1], pt[j2], new_etas[j2], phi[j2])


def run_b2(arrays, b1_winner_is_pv, R_EFF=R_EFF_DEFAULT, Z_EFF=Z_EFF_DEFAULT, tag=""):
    n_events = len(arrays["Photon_pt"])
    masses = {"a_stored": [], "b_reaim_PV": [], "c_reaim_GenVtx": []}
    masses_by_cat = {
        "both_barrel": {"a_stored": [], "b_reaim_PV": [], "c_reaim_GenVtx": []},
        "at_least_one_endcap": {"a_stored": [], "b_reaim_PV": [], "c_reaim_GenVtx": []},
    }
    masses_by_vtx = {
        "close_lt1cm": {"a_stored": []},
        "far_ge1cm": {"a_stored": []},
    }
    n_pv_close = 0
    n_full_sel_truth_matched = 0

    # plain leading-pair (no truth-match requirement) stored-value masses
    plain_masses = []

    for i in range(n_events):
        pass_v1tm = photon_pass_v1_tm(arrays, i)
        sel = event_passes_full_selection(arrays, i, pass_v1tm)
        if sel is None:
            continue
        j1, j2, mgg_stored = sel
        plain_masses.append(mgg_stored)

        matches = truth_match_photons(arrays, i, np.array([j1, j2]))
        if matches is None:
            continue
        # require the matched reco indices are exactly {j1, j2}
        if set(matches.values()) != {j1, j2}:
            continue
        n_full_sel_truth_matched += 1

        gvz = arrays["GenVtx_z"][i]
        pvz = arrays["PV_z"][i]
        z_ref_old = pvz if b1_winner_is_pv else 0.0

        eta = arrays["Photon_eta"][i]
        phi = arrays["Photon_phi"][i]
        pt = arrays["Photon_pt"][i]
        eb = arrays["Photon_isScEtaEB"][i]

        eta_b = {j: eta_from_vertex(eta[j], eb[j], z_ref_old, pvz, R_EFF, Z_EFF) for j in (j1, j2)}
        eta_c = {j: eta_from_vertex(eta[j], eb[j], z_ref_old, gvz, R_EFF, Z_EFF) for j in (j1, j2)}

        m_a = mgg_stored
        m_b = diphoton_mass_massless(pt[j1], eta_b[j1], phi[j1], pt[j2], eta_b[j2], phi[j2])
        m_c = diphoton_mass_massless(pt[j1], eta_c[j1], phi[j1], pt[j2], eta_c[j2], phi[j2])

        masses["a_stored"].append(m_a)
        masses["b_reaim_PV"].append(m_b)
        masses["c_reaim_GenVtx"].append(m_c)

        cat = "both_barrel" if (eb[j1] and eb[j2]) else "at_least_one_endcap"
        masses_by_cat[cat]["a_stored"].append(m_a)
        masses_by_cat[cat]["b_reaim_PV"].append(m_b)
        masses_by_cat[cat]["c_reaim_GenVtx"].append(m_c)

        close = abs(pvz - gvz) < 1.0
        if close:
            n_pv_close += 1
            masses_by_vtx["close_lt1cm"]["a_stored"].append(m_a)
        else:
            masses_by_vtx["far_ge1cm"]["a_stored"].append(m_a)

    def stats(vals):
        vals = np.array(vals)
        if len(vals) < 4:
            return {"n": int(len(vals)), "note": "too few events"}
        sig = effective_sigma_68(vals)
        peak = histogram_mode(vals, bin_width=0.5, lo=100, hi=180)
        median = float(np.median(vals))
        frac_2sig = float(np.mean(np.abs(vals - peak) < 2 * sig)) if sig else None
        sig_err = bootstrap_stat(vals, effective_sigma_68, n_boot=200)
        return {
            "n": int(len(vals)), "mean": float(vals.mean()), "rms": float(vals.std(ddof=1)),
            "effective_sigma68": sig, "effective_sigma68_bootstrap_err": sig_err,
            "peak_mode": peak, "median": median, "frac_within_2sigma_of_peak": frac_2sig,
        }

    result = {
        "tag": tag, "R_EFF": R_EFF, "Z_EFF": Z_EFF,
        "b1_winner_used_as_z_ref_old": "PV_z" if b1_winner_is_pv else "origin(0)",
        "n_events_full_selection": len(plain_masses),
        "n_events_full_selection_truth_matched_both": n_full_sel_truth_matched,
        "fraction_pv_within_1cm_of_genvtx": (
            n_pv_close / n_full_sel_truth_matched if n_full_sel_truth_matched else None
        ),
        "n_pv_within_1cm": n_pv_close,
        "options_inclusive": {k: stats(v) for k, v in masses.items()},
        "by_category": {cat: {k: stats(v) for k, v in d.items()} for cat, d in masses_by_cat.items()},
        "by_vertex_distance_stored_only": {k: stats(v["a_stored"]) for k, v in masses_by_vtx.items()},
        "plain_leading_pair_no_truthmatch_stored_only": stats(plain_masses),
    }
    raw = {"inclusive": masses, "by_category": masses_by_cat}
    return result, raw


def main():
    arrays = load_all()
    b1 = run_b1(arrays)

    barrel_ii = b1.get("barrel", {}).get("hypothesis_ii_ref_PV")
    barrel_i = b1.get("barrel", {}).get("hypothesis_i_ref_origin")
    b1_winner_is_pv = None
    if barrel_ii and barrel_i:
        slope_ii_ok = abs(barrel_ii["slope"] - 1.0) < 3 * barrel_ii["slope_err"]
        slope_i_ok = abs(barrel_i["slope"] - 1.0) < 3 * barrel_i["slope_err"]
        if slope_ii_ok and not slope_i_ok:
            b1_winner_is_pv = True
        elif slope_i_ok and not slope_ii_ok:
            b1_winner_is_pv = False
        else:
            b1_winner_is_pv = None  # ambiguous, decided in the writeup

    b2_default, raw_default = run_b2(
        arrays, b1_winner_is_pv if b1_winner_is_pv is not None else True,
        R_EFF=129.0, Z_EFF=314.0, tag="default_REFF129_ZEFF314")
    b2_syst, _raw_syst = run_b2(
        arrays, b1_winner_is_pv if b1_winner_is_pv is not None else True,
        R_EFF=135.0, Z_EFF=320.0, tag="systematic_REFF135_ZEFF320")

    # Plot mass distributions a/b/c overlaid: inclusive, then per category
    bins = np.linspace(100, 180, 81)
    style = (
        ("a_stored", "k", "(a) stored"),
        ("b_reaim_PV", "tab:blue", "(b) re-aimed to PV_z"),
        ("c_reaim_GenVtx", "tab:red", "(c) re-aimed to GenVtx_z (ideal)"),
    )

    fig, ax = plt.subplots(figsize=(7.5, 5))
    for key, color, label in style:
        vals = raw_default["inclusive"][key]
        if len(vals) > 3:
            ax.hist(vals, bins=bins, histtype="step", lw=1.8, color=color,
                    label=f"{label} (n={len(vals)})")
    ax.set_xlabel(r"$m_{\gamma\gamma}$ [GeV]")
    ax.set_ylabel("events / bin")
    ax.set_title("Check B2: diphoton mass, truth-matched, full selection (inclusive)")
    ax.legend(fontsize=9)
    fig.tight_layout()
    fig.savefig(f"{OUT_DIR}/plots_B2_mass_abc_inclusive.png", dpi=140)
    plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(13, 5), sharey=True)
    for ax, cat in zip(axes, ("both_barrel", "at_least_one_endcap")):
        for key, color, label in style:
            vals = raw_default["by_category"][cat][key]
            if len(vals) > 3:
                ax.hist(vals, bins=bins, histtype="step", lw=1.8, color=color,
                        label=f"{label} (n={len(vals)})")
        ax.set_xlabel(r"$m_{\gamma\gamma}$ [GeV]")
        ax.set_title(cat)
        ax.legend(fontsize=8)
    axes[0].set_ylabel("events / bin")
    fig.suptitle("Check B2: diphoton mass by category")
    fig.tight_layout()
    fig.savefig(f"{OUT_DIR}/plots_B2_mass_abc_by_category.png", dpi=140)
    plt.close(fig)

    result = {
        "files_read": SIGNAL_FILES,
        "b1_vertex_reference": b1,
        "b1_verdict_used_for_b2": ("PV_z" if b1_winner_is_pv else
                                    ("origin(0)" if b1_winner_is_pv is False else "ambiguous, defaulted to PV_z")),
        "b2_default_geometry": b2_default,
        "b2_systematic_geometry": b2_syst,
    }
    out_path = f"{OUT_DIR}/check_b_results.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, default=str)
    print(json.dumps({k: v for k, v in result.items() if k != "files_read"}, indent=2, default=str)[:6000])
    print("wrote", out_path)


if __name__ == "__main__":
    main()
