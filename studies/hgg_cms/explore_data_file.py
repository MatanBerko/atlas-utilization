"""
Part C (read-only inventory, Phase 2.1): remote branch inspection of one
DoubleEG Run2016G NanoAOD data file over HTTPS range requests. No full
download -- uproot streams only the requested branches/events.
"""
import uproot
import numpy as np

URL = ("https://opendata.cern.ch/eos/opendata/cms/Run2016G/DoubleEG/NANOAOD/"
       "UL2016_MiniAODv2_NanoAODv9-v1/100000/11DA657F-5262-BD4A-AD1E-8E53BE62A601.root")

OUT = r"C:\Users\matan\hgg-cms-inventory-20260915-1950\data_file_report.txt"

with open(OUT, "w", encoding="utf-8") as f:
    file = uproot.open(URL)
    f.write(f"File: {URL}\n")
    f.write(f"Top-level keys: {file.keys()}\n\n")
    tree = file["Events"]
    f.write(f"Number of entries in Events tree: {tree.num_entries}\n\n")

    all_branches = tree.keys()
    f.write(f"Total number of branches: {len(all_branches)}\n\n")

    f.write("=== All Photon_* branches with titles ===\n")
    for name in all_branches:
        if name.startswith("Photon_"):
            b = tree[name]
            f.write(f"{name} | typename={b.typename} | title={b.title!r}\n")

    f.write("\n=== All HLT_Diphoton* / HLT_DoublePhoton* branches ===\n")
    for name in all_branches:
        if name.startswith("HLT_Diphoton") or name.startswith("HLT_DoublePhoton"):
            b = tree[name]
            f.write(f"{name} | typename={b.typename} | title={b.title!r}\n")

    f.write("\n=== Run/luminosityBlock/event branches ===\n")
    for name in ("run", "luminosityBlock", "event"):
        if name in all_branches:
            b = tree[name]
            f.write(f"{name} | typename={b.typename} | title={b.title!r}\n")

    # Read at most 1000 events of a handful of branches
    N = 1000
    wanted = [n for n in all_branches if n.startswith("Photon_")] + \
             [n for n in all_branches if n.startswith("HLT_Diphoton") or n.startswith("HLT_DoublePhoton")] + \
             ["run", "luminosityBlock", "event"]
    arrays = tree.arrays(wanted, entry_stop=N, library="np")

    f.write(f"\n=== Read {N} events successfully. Sample values ===\n")
    f.write(f"nPhoton (event 0..4): {arrays['nPhoton'][:5] if 'nPhoton' in arrays else 'N/A'}\n")
    if "Photon_pt" in arrays:
        pts = arrays["Photon_pt"]
        flat = np.concatenate([p for p in pts if len(p) > 0]) if len(pts) else np.array([])
        f.write(f"Photon_pt: n_photons_total={len(flat)}, min={flat.min() if len(flat) else 'NA'}, "
                f"max={flat.max() if len(flat) else 'NA'}, mean={flat.mean() if len(flat) else 'NA'}\n")
    if "Photon_eCorr" in arrays:
        ec = arrays["Photon_eCorr"]
        flat = np.concatenate([p for p in ec if len(p) > 0]) if len(ec) else np.array([])
        f.write(f"Photon_eCorr: n={len(flat)}, min={flat.min() if len(flat) else 'NA'}, "
                f"max={flat.max() if len(flat) else 'NA'}, mean={flat.mean() if len(flat) else 'NA'}\n")

    # trigger pass fraction for the main diphoton path
    for trig_name in ("HLT_Diphoton30_18_R9Id_OR_IsoCaloId_AND_HE_R9Id_Mass90",
                      "HLT_Diphoton30_18_R9Id_OR_IsoCaloId_AND_HE_R9Id"):
        if trig_name in arrays:
            frac = arrays[trig_name].mean()
            f.write(f"\nFraction of {N} events passing {trig_name}: {frac:.4f}\n")

    f.write("\n=== cutBased value counts (first 1000 events, flattened) ===\n")
    if "Photon_cutBased" in arrays:
        cb = arrays["Photon_cutBased"]
        flat = np.concatenate([p for p in cb if len(p) > 0]) if len(cb) else np.array([])
        vals, counts = np.unique(flat, return_counts=True)
        f.write(f"{dict(zip(vals.tolist(), counts.tolist()))}\n")

print("done, wrote", OUT)
