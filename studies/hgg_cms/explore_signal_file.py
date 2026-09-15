"""
Part C (read-only inventory, Phase 2.1): remote branch inspection of one
postVFP GluGluHToGG UL16 NanoAODSIM signal file over HTTPS range requests.
No full download.
"""
import uproot
import numpy as np

URL = ("https://opendata.cern.ch/eos/opendata/cms/mc/RunIISummer20UL16NanoAODv9/"
       "GluGluHToGG_M-125_TuneCP5_13TeV-powheg-pythia8/NANOAODSIM/"
       "106X_mcRun2_asymptotic_v17-v1/40000/3231834B-7A6E-4840-8627-C97FDCF67268.root")

OUT = r"C:\Users\matan\hgg-cms-inventory-20260915-1950\signal_file_report.txt"

with open(OUT, "w", encoding="utf-8") as f:
    file = uproot.open(URL)
    f.write(f"File: {URL}\n")
    f.write(f"Top-level keys: {file.keys()}\n\n")
    tree = file["Events"]
    f.write(f"Number of entries in Events tree: {tree.num_entries}\n\n")
    all_branches = tree.keys()
    f.write(f"Total number of branches: {len(all_branches)}\n\n")

    f.write("=== genWeight ===\n")
    if "genWeight" in all_branches:
        b = tree["genWeight"]
        f.write(f"genWeight | typename={b.typename} | title={b.title!r}\n")

    f.write("\n=== Pileup_nTrueInt ===\n")
    if "Pileup_nTrueInt" in all_branches:
        b = tree["Pileup_nTrueInt"]
        f.write(f"Pileup_nTrueInt | typename={b.typename} | title={b.title!r}\n")

    f.write("\n=== LHE/PS weight branches ===\n")
    for name in all_branches:
        if name.startswith("LHEScaleWeight") or name.startswith("LHEPdfWeight") or \
           name.startswith("PSWeight") or name == "nLHEScaleWeight" or name == "nLHEPdfWeight" or \
           name == "nPSWeight" or name.startswith("LHEWeight"):
            b = tree[name]
            f.write(f"{name} | typename={b.typename} | title={b.title!r}\n")

    f.write("\n=== GenPart availability ===\n")
    genpart_branches = [n for n in all_branches if n.startswith("GenPart_") or n == "nGenPart"]
    for name in genpart_branches:
        b = tree[name]
        f.write(f"{name} | typename={b.typename} | title={b.title!r}\n")

    f.write("\n=== Run/luminosityBlock/event branches ===\n")
    for name in ("run", "luminosityBlock", "event"):
        if name in all_branches:
            b = tree[name]
            f.write(f"{name} | typename={b.typename} | title={b.title!r}\n")

    N = 1000
    wanted = ["genWeight", "Pileup_nTrueInt", "run", "luminosityBlock", "event",
              "Photon_pt", "Photon_eta", "Photon_phi", "Photon_mass", "nPhoton"] + genpart_branches
    wanted = [w for w in wanted if w in all_branches]
    arrays = tree.arrays(wanted, entry_stop=N, library="np")

    f.write(f"\n=== Read {N} events. genWeight stats ===\n")
    if "genWeight" in arrays:
        gw = arrays["genWeight"]
        f.write(f"genWeight: min={gw.min()}, max={gw.max()}, mean={gw.mean()}, "
                f"n_negative={(gw < 0).sum()}, n_unique_abs_values(approx)={len(np.unique(np.round(gw,6)))}\n")
        f.write(f"first 10 genWeight values: {gw[:10].tolist()}\n")

    if "Pileup_nTrueInt" in arrays:
        pu = arrays["Pileup_nTrueInt"]
        f.write(f"\nPileup_nTrueInt: min={pu.min()}, max={pu.max()}, mean={pu.mean()}\n")

    # Sanity check: leading two photons, invariant mass, requiring >=2 photons only.
    if "Photon_pt" in arrays:
        pt = arrays["Photon_pt"]; eta = arrays["Photon_eta"]
        phi = arrays["Photon_phi"]; mass = arrays["Photon_mass"]
        masses = []
        for i in range(len(pt)):
            if len(pt[i]) >= 2:
                order = np.argsort(-pt[i])[:2]
                p4s = []
                for j in order:
                    pt_, eta_, phi_, m_ = pt[i][j], eta[i][j], phi[i][j], mass[i][j]
                    px = pt_ * np.cos(phi_); py = pt_ * np.sin(phi_)
                    pz = pt_ * np.sinh(eta_); e = np.sqrt(px**2 + py**2 + pz**2 + m_**2)
                    p4s.append((e, px, py, pz))
                e = p4s[0][0] + p4s[1][0]; px = p4s[0][1] + p4s[1][1]
                py = p4s[0][2] + p4s[1][2]; pz = p4s[0][3] + p4s[1][3]
                m2 = e**2 - px**2 - py**2 - pz**2
                if m2 > 0:
                    masses.append(np.sqrt(m2))
        masses = np.array(masses)
        f.write(f"\n=== Sanity check: diphoton mass, >=2 photons, NO other selection ===\n")
        f.write(f"n_events_with>=2_photons = {len(masses)} / {N}\n")
        f.write(f"mean = {masses.mean():.3f} GeV, RMS = {masses.std():.3f} GeV\n")

print("done, wrote", OUT)
