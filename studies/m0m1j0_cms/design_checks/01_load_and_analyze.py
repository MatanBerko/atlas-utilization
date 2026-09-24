"""
m0m1j0 design phase, design checks 1-6 (branch inventory, Jet_rawFactor
summary, cutflow, m(mumuj)/m(mumu) plots incl. the 125-145 GeV feature
test, muon-jet overlap + outlier table, binning comparison).

Reads AT MOST the first 500,000 events from exactly one file per record
(30522 = DoubleMuon Run2016G, 30555 = DoubleMuon Run2016H), chosen as
file index 0 of each record's portal file list (see
00_file_inventory.json for the full list) -- read-only, over HTTPS
(see common.py's docstring for why, and the caveat about disabled TLS
verification for this read-only public-data access only).

This script does NOT modify any shared pipeline file. It imports
`services.parsing.validated_runs` READ-ONLY (no edits) to apply the
golden-JSON filter using the exact same, already-tested logic the
shared pipeline itself uses, rather than reimplementing it.

No significance/p-value/sigma calculation anywhere in this script, per
this phase's hard scope rule -- shapes and counts only.
"""
from __future__ import annotations

import re
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")

import awkward as ak
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import common  # noqa: E402

REPO_ROOT = HERE.parents[2]
sys.path.insert(0, str(REPO_ROOT))
from services.parsing.validated_runs import (  # noqa: E402
    ValidatedRunsFilter,
    apply_validated_runs_filter,
)

MAX_EVENTS = 500_000
GOLDEN_JSON = REPO_ROOT / "data" / "cms" / "validated_runs" / "Cert_271036-284044_13TeV_Legacy2016_Collisions16_JSON.txt"

FILES = {
    "30522": {
        "label": "DoubleMuon Run2016G",
        "uri": "root://eospublic.cern.ch//eos/opendata/cms/Run2016G/DoubleMuon/NANOAOD/UL2016_MiniAODv2_NanoAODv9-v2/2430000/05DD095C-F6C3-9A4F-9FB3-348A5A6403D5.root",
        "file_index": 0,
    },
    "30555": {
        "label": "DoubleMuon Run2016H",
        "uri": "root://eospublic.cern.ch//eos/opendata/cms/Run2016H/DoubleMuon/NANOAOD/UL2016_MiniAODv2_NanoAODv9-v1/2510000/127C2975-1B1C-A046-AABF-62B77E757A86.root",
        "file_index": 0,
    },
}

CHECK_MUON_FIELDS = ["pt", "eta", "phi", "mass", "charge", "looseId", "mediumId",
                     "tightId", "pfRelIso04_all", "dxy", "dz"]
CHECK_JET_FIELDS = ["pt", "eta", "phi", "mass", "jetId", "puId", "rawFactor",
                    "muonIdx1", "muonIdx2"]

READ_MUON_FIELDS = ["pt", "eta", "phi", "mass", "charge", "mediumId", "pfRelIso04_all"]
READ_JET_FIELDS = ["pt", "eta", "phi", "mass", "jetId", "puId", "rawFactor",
                   "muonIdx1", "muonIdx2"]
DZ_PATHS = ["HLT_Mu17_TrkIsoVVL_Mu8_TrkIsoVVL_DZ", "HLT_Mu17_TrkIsoVVL_TkMu8_TrkIsoVVL_DZ"]

MUON_MASS = 0.1057  # GeV, consts.KNOWN_MASSES value used by the shared pipeline (services/calculations/consts.py)


# ---------------------------------------------------------------------------
# 4-vector helpers (standalone -- no import from services/, mass-aware,
# needed since muons/jets here are NOT massless like the hgg photons were)
# ---------------------------------------------------------------------------

def to_p4(pt, eta, phi, mass):
    px = pt * np.cos(phi)
    py = pt * np.sin(phi)
    pz = pt * np.sinh(eta)
    e = np.sqrt(np.maximum(px**2 + py**2 + pz**2 + mass**2, 0.0))
    return np.stack([e, px, py, pz], axis=-1)


def p4_mass(p4):
    e, px, py, pz = p4[..., 0], p4[..., 1], p4[..., 2], p4[..., 3]
    m2 = e**2 - px**2 - py**2 - pz**2
    return np.sqrt(np.maximum(m2, 0.0))


def delta_r(eta1, phi1, eta2, phi2):
    dphi = np.abs(phi1 - phi2)
    dphi = np.where(dphi > np.pi, 2 * np.pi - dphi, dphi)
    deta = eta1 - eta2
    return np.sqrt(deta**2 + dphi**2)


# ---------------------------------------------------------------------------
# 1. Branch inventory
# ---------------------------------------------------------------------------

def branch_inventory():
    out = {}
    for rec_id, info in FILES.items():
        print(f"=== branch inventory: record {rec_id} ({info['label']}) ===")
        f = common.open_root_https(info["uri"])
        tree = f["Events"]
        all_keys = set(tree.keys())

        muon_report = {}
        for field in CHECK_MUON_FIELDS:
            b = f"Muon_{field}"
            present = b in all_keys
            muon_report[field] = {
                "branch": b, "present": present,
                "title": tree[b].title if present else None,
            }
        jet_report = {}
        for field in CHECK_JET_FIELDS:
            b = f"Jet_{field}"
            present = b in all_keys
            jet_report[field] = {
                "branch": b, "present": present,
                "title": tree[b].title if present else None,
            }
        event_report = {}
        for b in ["run", "luminosityBlock"]:
            present = b in all_keys
            event_report[b] = {
                "present": present, "title": tree[b].title if present else None,
            }

        hlt_pattern = re.compile(r".*Mu17.*(Mu8|TkMu8).*")
        hlt_matches = sorted(k for k in all_keys if k.startswith("HLT_") and hlt_pattern.match(k))
        hlt_report = {}
        if hlt_matches:
            hlt_arr = tree.arrays(hlt_matches, entry_stop=MAX_EVENTS, library="np")
            n = len(hlt_arr[hlt_matches[0]])
            for path in hlt_matches:
                n_fired = int(np.sum(hlt_arr[path]))
                hlt_report[path] = {"n_events_checked": n, "n_fired": n_fired,
                                     "fraction_fired": n_fired / n if n else None}
        print(f"  {len(muon_report)} Muon fields, {len(jet_report)} Jet fields checked; "
              f"{len(hlt_matches)} HLT paths matching *Mu17*(Mu8|TkMu8)*")
        f.close()
        out[rec_id] = {
            "label": info["label"], "uri": info["uri"],
            "muon_fields": muon_report, "jet_fields": jet_report,
            "event_fields": event_report, "hlt_paths": hlt_report,
        }
    common.write_json(HERE / "01_branch_inventory.json", out)
    return out


# ---------------------------------------------------------------------------
# 2. Jet_rawFactor summary
# ---------------------------------------------------------------------------

def rawfactor_summary(loaded):
    out = {}
    for rec_id, ev in loaded.items():
        raw = ak.to_numpy(ak.flatten(ev["Jet_rawFactor"]))
        n_total = len(raw)
        n_exact_zero = int(np.sum(raw == 0.0))
        out[rec_id] = {
            "n_jets_total": int(n_total),
            "n_exact_zero": n_exact_zero,
            "fraction_exact_zero": n_exact_zero / n_total if n_total else None,
            "median": float(np.median(raw)) if n_total else None,
            "p5": float(np.percentile(raw, 5)) if n_total else None,
            "p95": float(np.percentile(raw, 95)) if n_total else None,
        }
        print(f"[{rec_id}] Jet_rawFactor: n={n_total} exact_zero_frac={out[rec_id]['fraction_exact_zero']:.4f} "
              f"median={out[rec_id]['median']:.4f} p5={out[rec_id]['p5']:.4f} p95={out[rec_id]['p95']:.4f}")
    common.write_json(HERE / "02_rawfactor_summary.json", out)
    return out


# ---------------------------------------------------------------------------
# Selection building blocks, shared by cutflow (3) and the mass plots (4)
# ---------------------------------------------------------------------------

def select_muon_pairs(ev, mu_pt_min=15.0, mu_eta_max=2.4, use_id_iso=True,
                       iso_max=0.15, lead_pt_min=20.0):
    """Per-event leading 2 muons passing the proposed quality selection.
    Returns arrays (n_events,) of: has_pair(bool), lead 4-vector fields,
    sub 4-vector fields, m(mumu), charge product, plus the muon-level mask
    used (for jet-overlap cleaning downstream)."""
    pt, eta, phi, mass = ev["Muon_pt"], ev["Muon_eta"], ev["Muon_phi"], ev["Muon_mass"]
    charge = ev["Muon_charge"]
    mask = (pt > mu_pt_min) & (np.abs(eta) < mu_eta_max)
    if use_id_iso:
        mask = mask & (ev["Muon_mediumId"] == True) & (ev["Muon_pfRelIso04_all"] < iso_max)  # noqa: E712

    n_pass = ak.sum(mask, axis=1)
    has_ge2 = ak.to_numpy(n_pass >= 2)

    order = ak.argsort(pt, axis=1, ascending=False)
    pt_s, eta_s, phi_s, mass_s, charge_s, mask_s = (
        pt[order], eta[order], phi[order], mass[order], charge[order], mask[order]
    )
    # keep only muons passing mask, then take leading 2 of the SURVIVORS
    pt_sel = pt_s[mask_s]
    eta_sel = eta_s[mask_s]
    phi_sel = phi_s[mask_s]
    mass_sel = mass_s[mask_s]
    charge_sel = charge_s[mask_s]

    padded_pt = ak.fill_none(ak.pad_none(pt_sel, 2, axis=1, clip=True), np.nan)
    padded_eta = ak.fill_none(ak.pad_none(eta_sel, 2, axis=1, clip=True), np.nan)
    padded_phi = ak.fill_none(ak.pad_none(phi_sel, 2, axis=1, clip=True), np.nan)
    padded_mass = ak.fill_none(ak.pad_none(mass_sel, 2, axis=1, clip=True), np.nan)
    padded_charge = ak.fill_none(ak.pad_none(charge_sel, 2, axis=1, clip=True), 0)

    lead_pt = ak.to_numpy(padded_pt[:, 0])
    lead_eta = ak.to_numpy(padded_eta[:, 0])
    lead_phi = ak.to_numpy(padded_phi[:, 0])
    lead_mass = ak.to_numpy(padded_mass[:, 0])
    sub_pt = ak.to_numpy(padded_pt[:, 1])
    sub_eta = ak.to_numpy(padded_eta[:, 1])
    sub_phi = ak.to_numpy(padded_phi[:, 1])
    sub_mass = ak.to_numpy(padded_mass[:, 1])
    q1 = ak.to_numpy(padded_charge[:, 0])
    q2 = ak.to_numpy(padded_charge[:, 1])

    has_pair = has_ge2 & (lead_pt > lead_pt_min) & ~np.isnan(lead_pt) & ~np.isnan(sub_pt)

    p4_lead = to_p4(lead_pt, lead_eta, lead_phi, lead_mass)
    p4_sub = to_p4(sub_pt, sub_eta, sub_phi, sub_mass)
    p4_mumu = p4_lead + p4_sub
    m_mumu = p4_mass(p4_mumu)

    return {
        "has_pair": has_pair, "p4_lead": p4_lead, "p4_sub": p4_sub, "p4_mumu": p4_mumu,
        "m_mumu": m_mumu, "lead_eta": lead_eta, "lead_phi": lead_phi,
        "sub_eta": sub_eta, "sub_phi": sub_phi, "charge_product": q1 * q2,
        "muon_mask": mask,
    }


def select_leading_clean_jet(ev, muon_result, jet_pt_min=30.0, jet_eta_max=2.8,
                              require_tight_id=True, clean_overlap=True, dr_clean=0.4):
    """Per-event leading jet passing pT/eta/(tight jetId)/(muon-overlap
    cleaning against the 2 selected muons). Returns has_jet(bool), the
    jet 4-vector, and (for the overlap-statistics check) the dR of the
    ORIGINAL leading jet (pT/eta/ID only, no cleaning) to each selected
    muon."""
    pt, eta, phi, mass = ev["Jet_pt"], ev["Jet_eta"], ev["Jet_phi"], ev["Jet_mass"]
    jet_id = ev["Jet_jetId"]

    base_mask = (pt > jet_pt_min) & (np.abs(eta) < jet_eta_max)
    if require_tight_id:
        base_mask = base_mask & ((jet_id & 2) != 0)

    order = ak.argsort(pt, axis=1, ascending=False)
    pt_o, eta_o, phi_o, mass_o, mask_o = pt[order], eta[order], phi[order], mass[order], base_mask[order]

    # dR of the ORIGINAL (pT/eta/ID-only, uncleaned) leading jet to each muon,
    # for the overlap-statistics check (D3) -- computed BEFORE any cleaning.
    lead_pt_raw = ak.fill_none(ak.pad_none(pt_o[mask_o], 1, axis=1, clip=True), np.nan)[:, 0]
    lead_eta_raw = ak.fill_none(ak.pad_none(eta_o[mask_o], 1, axis=1, clip=True), np.nan)[:, 0]
    lead_phi_raw = ak.fill_none(ak.pad_none(phi_o[mask_o], 1, axis=1, clip=True), np.nan)[:, 0]
    lead_pt_raw = ak.to_numpy(lead_pt_raw)
    lead_eta_raw = ak.to_numpy(lead_eta_raw)
    lead_phi_raw = ak.to_numpy(lead_phi_raw)
    dr_to_lead_mu = delta_r(lead_eta_raw, lead_phi_raw, muon_result["lead_eta"], muon_result["lead_phi"])
    dr_to_sub_mu = delta_r(lead_eta_raw, lead_phi_raw, muon_result["sub_eta"], muon_result["sub_phi"])
    dr_min = np.fmin(dr_to_lead_mu, dr_to_sub_mu)

    if clean_overlap:
        dr_lead = delta_r(eta_o, phi_o, ak.Array(muon_result["lead_eta"]), ak.Array(muon_result["lead_phi"]))
        dr_sub = delta_r(eta_o, phi_o, ak.Array(muon_result["sub_eta"]), ak.Array(muon_result["sub_phi"]))
        overlap = (dr_lead < dr_clean) | (dr_sub < dr_clean)
        mask_o = mask_o & ~overlap

    pt_sel, eta_sel, phi_sel, mass_sel = pt_o[mask_o], eta_o[mask_o], phi_o[mask_o], mass_o[mask_o]
    padded_pt = ak.fill_none(ak.pad_none(pt_sel, 1, axis=1, clip=True), np.nan)
    padded_eta = ak.fill_none(ak.pad_none(eta_sel, 1, axis=1, clip=True), np.nan)
    padded_phi = ak.fill_none(ak.pad_none(phi_sel, 1, axis=1, clip=True), np.nan)
    padded_mass = ak.fill_none(ak.pad_none(mass_sel, 1, axis=1, clip=True), np.nan)

    lead_pt = ak.to_numpy(padded_pt[:, 0])
    lead_eta = ak.to_numpy(padded_eta[:, 0])
    lead_phi = ak.to_numpy(padded_phi[:, 0])
    lead_mass = ak.to_numpy(padded_mass[:, 0])
    has_jet = ~np.isnan(lead_pt)

    p4_jet = to_p4(lead_pt, lead_eta, lead_phi, lead_mass)
    return {"has_jet": has_jet, "p4_jet": p4_jet, "dr_min_uncleaned_lead_jet_to_muon": dr_min,
            "lead_pt_raw_uncleaned": lead_pt_raw}


def combine_mumuj(muon_result, jet_result):
    ok = muon_result["has_pair"] & jet_result["has_jet"]
    p4_tot = np.where(ok[:, None], muon_result["p4_mumu"] + jet_result["p4_jet"], np.nan)
    m = p4_mass(p4_tot)
    return ok, m


# ---------------------------------------------------------------------------
# 3. Cutflow
# ---------------------------------------------------------------------------

def run_cutflow(loaded, golden):
    out = {}
    for rec_id, ev in loaded.items():
        steps = []
        n0 = len(ev)
        steps.append(("n_input_events_read", n0))

        # Golden JSON
        ev_g, gstats = apply_validated_runs_filter(ev, golden)
        steps.append(("after_golden_json", gstats["n_after"]))

        # Trigger (any of the two DZ paths)
        trig = np.zeros(len(ev_g), dtype=bool)
        for p in DZ_PATHS:
            trig = trig | ak.to_numpy(ev_g[p])
        ev_t = ev_g[trig]
        steps.append(("after_trigger_any_DZ_path", int(len(ev_t))))

        # Muon selection (>=2 quality muons, leading pt>20/eta<2.4/mediumId/iso<0.15)
        mu = select_muon_pairs(ev_t, use_id_iso=True)
        ev_m = ev_t[mu["has_pair"]]
        mu_pass = {k: (v[mu["has_pair"]] if hasattr(v, "__len__") and len(v) == len(mu["has_pair"]) else v)
                   for k, v in mu.items() if k != "muon_mask"}
        n_after_muon = int(np.sum(mu["has_pair"]))
        steps.append(("after_muon_selection_ge2_quality_leading20_sub15", n_after_muon))

        mu2 = select_muon_pairs(ev_m, use_id_iso=True)  # recompute on the reduced sample for jet step
        jet_noclean = select_leading_clean_jet(ev_m, mu2, jet_pt_min=30.0, require_tight_id=True, clean_overlap=False)
        n_after_jet_id_pt = int(np.sum(jet_noclean["has_jet"]))
        steps.append(("after_jet_tightID_pt30_eta2p8_no_overlap_clean", n_after_jet_id_pt))

        jet_clean = select_leading_clean_jet(ev_m, mu2, jet_pt_min=30.0, require_tight_id=True, clean_overlap=True)
        n_after_jet_clean = int(np.sum(jet_clean["has_jet"]))
        steps.append(("after_muon_jet_overlap_cleaning_dR0p4", n_after_jet_clean))

        out[rec_id] = {"steps": [{"step": s, "n_events": int(n)} for s, n in steps]}
        print(f"[{rec_id}] cutflow: " + " -> ".join(f"{s}={n}" for s, n in steps))
    common.write_json(HERE / "03_cutflow.json", out)
    return out


# ---------------------------------------------------------------------------
# 4. Mass plots (m(mumu), m(mumuj), the 125-145 GeV feature test)
# ---------------------------------------------------------------------------

def z_window_scale(pt_min):
    """UNVERIFIED-as-a-hard-edge, per this task's own hypothesis: for a Z
    at rest recoiling against a jet of pT=pt_min, m(mumuj) >= sqrt(mZ^2 +
    2*mZ*pt_min) (see DESIGN.md Section G for the derivation and caveats).
    mZ = 91.1876 GeV (PDG)."""
    mZ = 91.1876
    return float(np.sqrt(mZ**2 + 2 * mZ * pt_min))


def mass_plots(loaded, golden):
    all_results = {}
    for rec_id, ev in loaded.items():
        print(f"=== mass plots: {rec_id} ===")
        ev_g, _ = apply_validated_runs_filter(ev, golden)
        trig = np.zeros(len(ev_g), dtype=bool)
        for p in DZ_PATHS:
            trig = trig | ak.to_numpy(ev_g[p])
        ev_t = ev_g[trig]

        mu = select_muon_pairs(ev_t, use_id_iso=True)
        m_mumu = mu["m_mumu"]
        in_z = mu["has_pair"] & (m_mumu > 76.18) & (m_mumu < 106.18)
        out_z = mu["has_pair"] & ~in_z

        results_by_ptmin = {}
        for pt_min in (20.0, 30.0, 50.0):
            jet = select_leading_clean_jet(ev_t, mu, jet_pt_min=pt_min, require_tight_id=True, clean_overlap=True)
            ok, m_mumuj = combine_mumuj(mu, jet)
            results_by_ptmin[pt_min] = {"ok": ok, "m_mumuj": m_mumuj}

        # loose legacy-like: muon pt>5 only, no ID/iso, no jet cleaning, jet any pt/eta/ID
        mu_loose = select_muon_pairs(ev_t, mu_pt_min=5.0, mu_eta_max=2.4, use_id_iso=False, lead_pt_min=0.0)
        jet_loose = select_leading_clean_jet(ev_t, mu_loose, jet_pt_min=0.0, jet_eta_max=999.0,
                                              require_tight_id=False, clean_overlap=False)
        ok_loose, m_mumuj_loose = combine_mumuj(mu_loose, jet_loose)

        all_results[rec_id] = {
            "m_mumu": m_mumu, "has_pair": mu["has_pair"], "in_z": in_z, "out_z": out_z,
            "charge_product": mu["charge_product"], "by_ptmin": results_by_ptmin,
            "loose": {"ok": ok_loose, "m_mumuj": m_mumuj_loose},
        }

    # --- combine both records for the plots (documented as "both files combined") ---
    def cat(key, sub=None, field=None):
        arrs = []
        for rec_id in all_results:
            r = all_results[rec_id]
            v = r[key] if sub is None else r[key][sub]
            if field is not None:
                v = v[field]
            arrs.append(v)
        return np.concatenate(arrs)

    m_mumu_all = cat("m_mumu")
    has_pair_all = cat("has_pair")
    in_z_all = cat("in_z")
    out_z_all = cat("out_z")
    charge_prod_all = cat("charge_product")

    # sanity check plot: m(mumu)
    fig, ax = plt.subplots(figsize=(7, 5))
    vals = m_mumu_all[has_pair_all & (m_mumu_all > 0) & (m_mumu_all < 200)]
    ax.hist(vals, bins=100, range=(0, 200), histtype="step", color="k", label=f"m($\\mu\\mu$), N={len(vals)}")
    ax.axvline(91.19, color="r", ls="--", lw=1, label="$m_Z$=91.19 GeV (PDG)")
    ax.set_xlabel(r"$m(\mu\mu)$ [GeV]")
    ax.set_ylabel("Events / 2 GeV")
    ax.set_yscale("log")
    ax.legend()
    fig.tight_layout()
    fig.savefig(common.PLOTS_DIR / "dimuon_mass_sanity.png", dpi=150)
    plt.close(fig)
    print("wrote dimuon_mass_sanity.png")

    summary = {"n_events_with_muon_pair_both_files": int(np.sum(has_pair_all)),
               "median_m_mumu": float(np.median(vals)) if len(vals) else None}

    # --- G: turn-on feature plots, per jet pT threshold ---
    turnon_summary = {}
    for pt_min in (20.0, 30.0, 50.0):
        m_all = cat("by_ptmin", pt_min, "m_mumuj")
        ok_all = cat("by_ptmin", pt_min, "ok")

        fig, ax = plt.subplots(figsize=(8, 5.5))
        bins = np.linspace(0, 300, 76)
        for label, sel, color in [
            ("all events", ok_all, "k"),
            ("m($\\mu\\mu$) in Z window [76.18,106.18]", ok_all & in_z_all, "#c1272d"),
            ("m($\\mu\\mu$) outside Z window", ok_all & out_z_all, "#1f5fa8"),
        ]:
            vals = m_all[sel & ~np.isnan(m_all)]
            ax.hist(vals, bins=bins, histtype="step", label=f"{label} (N={len(vals)})", color=color, lw=1.5)
        scale = z_window_scale(pt_min)
        ax.axvline(scale, color="green", ls=":", lw=1.5,
                   label=f"computed turn-on scale, pT>{pt_min:.0f}: {scale:.1f} GeV")
        ax.set_xlabel(r"$m(\mu\mu j)$ [GeV]")
        ax.set_ylabel(f"Events / {bins[1]-bins[0]:.1f} GeV")
        ax.set_yscale("log")
        ax.set_title(f"Leading jet pT > {pt_min:.0f} GeV")
        ax.legend(fontsize=8.5)
        fig.tight_layout()
        fname = f"mumuj_turnon_ptmin{int(pt_min)}.png"
        fig.savefig(common.PLOTS_DIR / fname, dpi=150)
        plt.close(fig)
        print(f"wrote {fname}")

        # OS/SS split at this pT threshold
        fig, ax = plt.subplots(figsize=(8, 5.5))
        for label, sel, color in [
            ("OS (opposite sign)", ok_all & (charge_prod_all < 0), "#c1272d"),
            ("SS (same sign)", ok_all & (charge_prod_all > 0), "#1f5fa8"),
        ]:
            vals = m_all[sel & ~np.isnan(m_all)]
            ax.hist(vals, bins=bins, histtype="step", label=f"{label} (N={len(vals)})", color=color, lw=1.5)
        ax.axvline(scale, color="green", ls=":", lw=1.5, label=f"turn-on scale: {scale:.1f} GeV")
        ax.set_xlabel(r"$m(\mu\mu j)$ [GeV]")
        ax.set_ylabel(f"Events / {bins[1]-bins[0]:.1f} GeV")
        ax.set_yscale("log")
        ax.set_title(f"OS/SS split, leading jet pT > {pt_min:.0f} GeV")
        ax.legend(fontsize=9)
        fig.tight_layout()
        fname = f"mumuj_osss_ptmin{int(pt_min)}.png"
        fig.savefig(common.PLOTS_DIR / fname, dpi=150)
        plt.close(fig)
        print(f"wrote {fname}")

        vals_120_150 = m_all[ok_all & ~np.isnan(m_all) & (m_all > 120) & (m_all < 150)]
        vals_all_valid = m_all[ok_all & ~np.isnan(m_all)]
        turnon_summary[pt_min] = {
            "computed_turnon_scale_gev": scale,
            "n_total": int(len(vals_all_valid)),
            "n_in_120_150_window": int(len(vals_120_150)),
            "fraction_in_120_150_window": float(len(vals_120_150) / len(vals_all_valid)) if len(vals_all_valid) else None,
        }

    # --- loose legacy-like comparison ---
    m_loose_all = cat("loose", field="m_mumuj")
    ok_loose_all = cat("loose", field="ok")
    fig, ax = plt.subplots(figsize=(8, 5.5))
    bins_wide = np.linspace(0, 500, 126)
    vals = m_loose_all[ok_loose_all & ~np.isnan(m_loose_all)]
    ax.hist(vals, bins=bins_wide, histtype="step", color="k", lw=1.2, label=f"loose legacy-like selection, N={len(vals)}")
    ax.set_xlabel(r"$m(\mu\mu j)$ [GeV]")
    ax.set_ylabel("Events / 4 GeV")
    ax.set_yscale("log")
    ax.legend()
    fig.tight_layout()
    fig.savefig(common.PLOTS_DIR / "mumuj_loose_legacy_like.png", dpi=150)
    plt.close(fig)
    print("wrote mumuj_loose_legacy_like.png")

    common.write_json(HERE / "04_mass_plots_summary.json", {
        "dimuon_sanity": summary, "turnon_by_ptmin": turnon_summary,
        "loose_legacy_like": {"n_total": int(len(vals)), "max_gev": float(np.nanmax(m_loose_all)) if len(m_loose_all) else None},
    })
    return all_results


# ---------------------------------------------------------------------------
# 5. Overlap statistics + outlier table
# ---------------------------------------------------------------------------

def overlap_and_outliers(loaded, golden):
    out = {}
    outlier_rows = []
    for rec_id, ev in loaded.items():
        ev_g, _ = apply_validated_runs_filter(ev, golden)
        trig = np.zeros(len(ev_g), dtype=bool)
        for p in DZ_PATHS:
            trig = trig | ak.to_numpy(ev_g[p])
        ev_t = ev_g[trig]

        mu = select_muon_pairs(ev_t, use_id_iso=True)
        jet_unclean_stats = select_leading_clean_jet(ev_t, mu, jet_pt_min=30.0, require_tight_id=True, clean_overlap=False)
        dr_min = jet_unclean_stats["dr_min_uncleaned_lead_jet_to_muon"]
        has_both = mu["has_pair"] & jet_unclean_stats["has_jet"]
        dr_valid = dr_min[has_both]
        n_overlap_04 = int(np.sum(dr_valid < 0.4))

        # Corroborate via NanoAOD's own Jet_muonIdx1/Jet_muonIdx2 (native
        # jet-muon matching, independent of the geometric dR check above):
        # does the leading (pt-sorted, tight-ID, pT>30) jet's own muonIdx
        # point at the ORIGINAL (pre-sort, pre-mask) collection index of
        # either selected muon? (D3's explicit request.)
        pt_m = ev_t["Muon_pt"]
        order_mu = ak.argsort(pt_m, axis=1, ascending=False)
        mu_mask = mu["muon_mask"]
        orig_idx = ak.local_index(pt_m, axis=1)
        idx_sel = orig_idx[order_mu][mu_mask[order_mu]]
        idx_pad = ak.to_numpy(ak.fill_none(ak.pad_none(idx_sel, 2, axis=1, clip=True), -999))
        lead_mu_idx, sub_mu_idx = idx_pad[:, 0], idx_pad[:, 1]

        pt_j = ev_t["Jet_pt"]
        base_jet_mask = (pt_j > 30.0) & ((ev_t["Jet_jetId"] & 2) != 0)
        order_j = ak.argsort(pt_j, axis=1, ascending=False)
        m1_sel = ev_t["Jet_muonIdx1"][order_j][base_jet_mask[order_j]]
        m2_sel = ev_t["Jet_muonIdx2"][order_j][base_jet_mask[order_j]]
        m1 = ak.to_numpy(ak.fill_none(ak.pad_none(m1_sel, 1, axis=1, clip=True), -999))[:, 0]
        m2 = ak.to_numpy(ak.fill_none(ak.pad_none(m2_sel, 1, axis=1, clip=True), -999))[:, 0]
        muonidx_match = has_both & ((m1 == lead_mu_idx) | (m1 == sub_mu_idx)
                                     | (m2 == lead_mu_idx) | (m2 == sub_mu_idx))
        n_muonidx_match = int(np.sum(muonidx_match))

        out[rec_id] = {
            "n_events_with_muon_pair_and_leading_jet": int(np.sum(has_both)),
            "n_leading_jet_within_dR_0p4_of_selected_muon": n_overlap_04,
            "fraction": n_overlap_04 / len(dr_valid) if len(dr_valid) else None,
            "median_dR": float(np.median(dr_valid)) if len(dr_valid) else None,
            "n_leading_jet_muonIdx_points_at_selected_muon": n_muonidx_match,
            "fraction_muonIdx_corroboration": n_muonidx_match / len(dr_valid) if len(dr_valid) else None,
        }
        print(f"[{rec_id}] overlap: {out[rec_id]}")

        # outlier table: highest m(mumuj) with jet pt>20 (paper threshold, most permissive)
        jet20 = select_leading_clean_jet(ev_t, mu, jet_pt_min=20.0, require_tight_id=False, clean_overlap=False)
        ok, m = combine_mumuj(mu, jet20)
        m_valid = np.where(ok, m, -1.0)
        top_idx = np.argsort(m_valid)[::-1][:10]
        jet_pt = ak.to_numpy(ak.fill_none(ak.pad_none(ev_t["Jet_pt"][ak.argsort(ev_t["Jet_pt"], axis=1, ascending=False)], 1, axis=1, clip=True), np.nan))[:, 0]
        jet_eta = ak.to_numpy(ak.fill_none(ak.pad_none(ev_t["Jet_eta"][ak.argsort(ev_t["Jet_pt"], axis=1, ascending=False)], 1, axis=1, clip=True), np.nan))[:, 0]
        jet_id_arr = ak.to_numpy(ak.fill_none(ak.pad_none(ev_t["Jet_jetId"][ak.argsort(ev_t["Jet_pt"], axis=1, ascending=False)], 1, axis=1, clip=True), -1))[:, 0]
        jet_pu_arr = ak.to_numpy(ak.fill_none(ak.pad_none(ev_t["Jet_puId"][ak.argsort(ev_t["Jet_pt"], axis=1, ascending=False)], 1, axis=1, clip=True), -1))[:, 0]
        for i in top_idx:
            if m_valid[i] <= 0:
                continue
            passes_tight_id = bool((int(jet_id_arr[i]) & 2) != 0)
            passes_pt30 = bool(jet_pt[i] > 30.0)
            removed_by_pt30_or_id = not (passes_pt30 and passes_tight_id)
            outlier_rows.append({
                "record": rec_id, "m_mumuj_gev": float(m_valid[i]),
                "leading_jet_pt": float(jet_pt[i]), "leading_jet_eta": float(jet_eta[i]),
                "leading_jet_jetId": int(jet_id_arr[i]), "leading_jet_puId": int(jet_pu_arr[i]),
                "removed_by_proposed_pt30_tightID_cut": removed_by_pt30_or_id,
            })
    outlier_rows.sort(key=lambda r: -r["m_mumuj_gev"])
    common.write_json(HERE / "05_overlap_and_outliers.json",
                       {"overlap_stats": out, "top_mass_outliers_paper_style_selection_jetpt20": outlier_rows[:20]})
    return out, outlier_rows


# ---------------------------------------------------------------------------
# 6. Binning comparison
# ---------------------------------------------------------------------------

def binning_comparison(mass_results):
    m_all = np.concatenate([mass_results[r]["by_ptmin"][30.0]["m_mumuj"] for r in mass_results])
    ok_all = np.concatenate([mass_results[r]["by_ptmin"][30.0]["ok"] for r in mass_results])
    vals = m_all[ok_all & ~np.isnan(m_all)]
    vals = vals[vals > 0]

    # The REAL shared convention: FIXED_MASS_MIN_GEV=0, FIXED_MASS_MAX_GEV=10000,
    # 10 GeV width (services/pipelines/histograms_pipeline.py:22-23) -> 1000 bins
    # total, computed here in full (not truncated) so the reported bin counts are
    # correct; only the PLOT below truncates the x-axis for readability.
    fixed_edges_full = np.arange(0.0, 10000.0 + 10.0, 10.0)
    fixed_edges_plot = fixed_edges_full[fixed_edges_full <= 2000.0]

    # Paper-style variable bins: bin width = 0.5*sqrt(sum sigma_i^2(pT=m/2)).
    # sigma(m) for mu, mu, jet NOT independently measured here (would need
    # CMS muon-performance / JER papers with figures actually read -- not
    # available in this environment; see DESIGN.md Section F). Marked
    # UNVERIFIED: formula only, using a placeholder constant relative
    # resolution per object (10% for the jet, 2% for each muon) SOLELY to
    # illustrate the shape of variable binning on this sample -- not a
    # physics resolution measurement.
    PLACEHOLDER_MUON_REL_RES = 0.02
    PLACEHOLDER_JET_REL_RES = 0.10

    edges = [0.0]
    m_current = 0.0
    max_m = float(np.max(vals)) if len(vals) else 500.0
    while m_current < max_m:
        sigma = 0.5 * np.sqrt(2 * (PLACEHOLDER_MUON_REL_RES * m_current / 2) ** 2
                               + (PLACEHOLDER_JET_REL_RES * m_current / 2) ** 2)
        width = max(sigma, 1.0)
        m_current += width
        edges.append(m_current)
    variable_edges = np.array(edges)

    fig, axes = plt.subplots(2, 1, figsize=(8, 8), sharex=True)
    axes[0].hist(vals[vals < 2000], bins=fixed_edges_plot, histtype="step", color="k")
    axes[0].set_title(f"Fixed 10 GeV bins, 0-10 TeV shared convention "
                       f"({len(fixed_edges_full)-1} bins total 0-10 TeV; x-axis truncated at 2 TeV for display)")
    axes[0].set_ylabel("Events / 10 GeV")
    axes[0].set_yscale("log")
    axes[1].hist(vals, bins=variable_edges, histtype="step", color="#c1272d")
    axes[1].set_title(f"Paper-style variable bins (UNVERIFIED placeholder resolutions), {len(variable_edges)-1} bins to sample max")
    axes[1].set_ylabel("Events / bin")
    axes[1].set_xlabel(r"$m(\mu\mu j)$ [GeV]")
    axes[1].set_yscale("log")
    axes[1].set_xlim(0, min(max_m * 1.05, 600))
    fig.tight_layout()
    fig.savefig(common.PLOTS_DIR / "binning_comparison.png", dpi=150)
    plt.close(fig)
    print("wrote binning_comparison.png")

    n_bins_fixed_after_max = int(np.sum(fixed_edges_full[:-1] >= vals.max())) if len(vals) else None
    common.write_json(HERE / "06_binning_comparison.json", {
        "n_events_used": int(len(vals)),
        "fixed_10gev": {"n_bins_total_0_to_10tev": len(fixed_edges_full) - 1,
                        "n_bins_after_sample_max": n_bins_fixed_after_max,
                        "sample_max_gev": float(vals.max()) if len(vals) else None},
        "paper_style_variable": {
            "note": "UNVERIFIED placeholder relative resolutions (2% per muon, 10% for jet) "
                    "-- NOT independently measured CMS resolutions; formula only, per DESIGN.md Section F.",
            "n_bins_to_sample_max": len(variable_edges) - 1,
            "first_10_edges_gev": variable_edges[:10].tolist(),
        },
    })


def main():
    common.PLOTS_DIR.mkdir(parents=True, exist_ok=True)

    branch_inventory()

    golden = ValidatedRunsFilter(str(GOLDEN_JSON))
    print(f"Golden JSON loaded: {golden.n_runs} runs, {golden.n_certified_lumisections} certified lumisections, "
          f"sha256={golden.sha256}")

    loaded = {}
    for rec_id, info in FILES.items():
        print(f"=== loading {rec_id} ({info['label']}) ===")
        f = common.open_root_https(info["uri"])
        tree = f["Events"]
        branches = ([f"Muon_{x}" for x in READ_MUON_FIELDS]
                    + [f"Jet_{x}" for x in READ_JET_FIELDS]
                    + ["run", "luminosityBlock"] + DZ_PATHS)
        arr = tree.arrays(branches, entry_stop=MAX_EVENTS, library="ak")
        obj = ak.zip({
            "Muon_pt": arr["Muon_pt"], "Muon_eta": arr["Muon_eta"], "Muon_phi": arr["Muon_phi"],
            "Muon_mass": arr["Muon_mass"], "Muon_charge": arr["Muon_charge"],
            "Muon_mediumId": arr["Muon_mediumId"], "Muon_pfRelIso04_all": arr["Muon_pfRelIso04_all"],
            "Jet_pt": arr["Jet_pt"], "Jet_eta": arr["Jet_eta"], "Jet_phi": arr["Jet_phi"],
            "Jet_mass": arr["Jet_mass"], "Jet_jetId": arr["Jet_jetId"], "Jet_puId": arr["Jet_puId"],
            "Jet_rawFactor": arr["Jet_rawFactor"], "Jet_muonIdx1": arr["Jet_muonIdx1"], "Jet_muonIdx2": arr["Jet_muonIdx2"],
            "run": arr["run"], "luminosityBlock": arr["luminosityBlock"],
        } | {p: arr[p] for p in DZ_PATHS}, depth_limit=1)
        loaded[rec_id] = obj
        f.close()
        print(f"  loaded {len(obj)} events")

    rawfactor_summary(loaded)
    run_cutflow(loaded, golden)
    mass_results = mass_plots(loaded, golden)
    overlap_and_outliers(loaded, golden)
    binning_comparison(mass_results)

    print("\nALL DESIGN CHECKS COMPLETE")


if __name__ == "__main__":
    main()
