"""
nonjet4 task, Step 5: independent verification of the nonjet4 combined-
delivery ROOT files with BOTH uproot and real PyROOT 6.40.02.

Checks, per file:
  - histogram names unique
  - count equals the manifest's own count
  - every cropped file's every histogram has a non-empty first bin
  - every histogram has > 30 (min31bins files) or > 25 (min26bins files)
    non-empty bins
  - every histogram has >= 100 events
  - cropped values equal the uncropped file's values over the kept range
"""
import json
import sys
import numpy as np
import uproot
import ROOT

BASE = "/storage/agrp/berkom/atlas-utilization/output/cms_datasets/deliver/muon_combined_nonjet4"

FILES = []
for version, prefix in [("nonjet4", "muon_combined_matched_nonjet4")]:
    for threshold, bin_floor, manifest_suffix in [("min31bins", 30, "min31bins"), ("min26bins", 25, "min26bins")]:
        FILES.append({
            "version": version,
            "threshold": threshold,
            "bin_floor": bin_floor,
            "uncropped": f"{BASE}/{prefix}_bumpnet_{threshold}.root",
            "cropped": f"{BASE}/{prefix}_bumpnet_{threshold}_cropped.root",
            "manifest": f"{BASE}/manifest_{prefix}_{manifest_suffix}.json",
        })


def read_all_uproot(path):
    f = uproot.open(path)
    keys = sorted(set(k.split(";")[0] for k in f.keys()))
    out = {}
    for k in keys:
        h = f[k]
        out[k] = (h.values().astype(np.float64), h.axis().edges().astype(np.float64))
    return out


def read_all_root(path):
    f = ROOT.TFile.Open(path)
    keys = sorted(set(k.GetName() for k in f.GetListOfKeys()))
    out = {}
    for k in keys:
        h = f.Get(k)
        nbins = h.GetNbinsX()
        values = np.array([h.GetBinContent(i) for i in range(1, nbins + 1)])
        edges = np.array([h.GetBinLowEdge(i) for i in range(1, nbins + 2)])
        out[k] = (values, edges)
    f.Close()
    return out


all_problems = []
summary = []

for spec in FILES:
    label = f"{spec['version']}/{spec['threshold']}"
    print(f"\n=== {label} ===")
    manifest = json.load(open(spec["manifest"]))
    n_manifest = len(manifest)

    uproot_uncropped = read_all_uproot(spec["uncropped"])
    uproot_cropped = read_all_uproot(spec["cropped"])
    root_uncropped = read_all_root(spec["uncropped"])
    root_cropped = read_all_root(spec["cropped"])

    problems = []

    for reader_name, uncropped, cropped in [("uproot", uproot_uncropped, uproot_cropped),
                                              ("ROOT", root_uncropped, root_cropped)]:
        names_u = list(uncropped.keys())
        if len(names_u) != len(set(names_u)):
            problems.append(f"[{reader_name}] duplicate names in uncropped file")
        if len(uncropped) != n_manifest:
            problems.append(f"[{reader_name}] uncropped count {len(uncropped)} != manifest count {n_manifest}")
        if len(cropped) != n_manifest:
            problems.append(f"[{reader_name}] cropped count {len(cropped)} != manifest count {n_manifest}")
        if set(uncropped.keys()) != set(cropped.keys()):
            problems.append(f"[{reader_name}] uncropped/cropped name sets differ")

        for name, (u_values, u_edges) in uncropped.items():
            n_nonempty = int(np.count_nonzero(u_values))
            n_events = float(u_values.sum())
            if n_nonempty <= spec["bin_floor"]:
                problems.append(f"[{reader_name}] {name}: n_nonempty={n_nonempty} <= floor {spec['bin_floor']}")
            if n_events < 100:
                problems.append(f"[{reader_name}] {name}: n_events={n_events} < 100")

            if name not in cropped:
                continue
            c_values, c_edges = cropped[name]
            if c_values.size == 0 or c_values[0] <= 0:
                problems.append(f"[{reader_name}] {name}: cropped first bin is EMPTY")
            nz = np.nonzero(u_values > 0)[0]
            expected = u_values[nz[0]:nz[-1] + 1]
            if c_values.shape != expected.shape or not np.array_equal(c_values, expected):
                problems.append(f"[{reader_name}] {name}: cropped values != uncropped's nonzero range")
            if not np.isclose(c_values.sum(), u_values.sum()):
                problems.append(f"[{reader_name}] {name}: cropped total {c_values.sum()} != uncropped total {u_values.sum()}")

    if set(uproot_uncropped.keys()) == set(root_uncropped.keys()):
        for name in uproot_uncropped:
            uv, ue = uproot_uncropped[name]
            rv, re = root_uncropped[name]
            if uv.shape != rv.shape or not np.allclose(uv, rv):
                problems.append(f"[cross-check] {name}: uproot and ROOT disagree on uncropped bin contents")
            if ue.shape != re.shape or not np.allclose(ue, re):
                problems.append(f"[cross-check] {name}: uproot and ROOT disagree on bin edges")
    else:
        problems.append("[cross-check] uproot and ROOT see different name sets in the uncropped file")

    print(f"  manifest entries: {n_manifest}")
    print(f"  uproot uncropped/cropped: {len(uproot_uncropped)}/{len(uproot_cropped)}")
    print(f"  ROOT   uncropped/cropped: {len(root_uncropped)}/{len(root_cropped)}")
    print(f"  problems found: {len(problems)}")
    if problems:
        for p in problems[:20]:
            print(f"    - {p}")
    else:
        print(f"  PASS: all checks clean (uproot AND ROOT, both agree, cropping verified, "
              f">{spec['bin_floor']} bins, >=100 events, non-empty first bin -- all {n_manifest} histograms)")

    all_problems.extend([f"{label}: {p}" for p in problems])
    summary.append({
        "version": spec["version"], "threshold": spec["threshold"],
        "n_manifest": n_manifest, "n_problems": len(problems),
        "all_checks_passed": len(problems) == 0,
    })

print(f"\n\nOVERALL: {'ALL PASS' if not all_problems else f'{len(all_problems)} PROBLEMS'}")
with open(f"{BASE}/verification_summary.json", "w") as f:
    json.dump({"summary": summary, "all_problems": all_problems, "overall_pass": not all_problems}, f, indent=2)
print(f"wrote {BASE}/verification_summary.json")
sys.exit(0 if not all_problems else 1)
