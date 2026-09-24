"""
Deliverable 2: inspect real CMS NanoAOD files for TrigObj_* / HLT_* branches.
Reading only -- no implementation. Uses XRootD access to CMS Open Data EOS.
"""
import json
import numpy as np
import uproot

FILES = {
    "hgg_data_30521_file0": "root://eospublic.cern.ch//eos/opendata/cms/Run2016G/DoubleEG/NANOAOD/UL2016_MiniAODv2_NanoAODv9-v1/100000/11DA657F-5262-BD4A-AD1E-8E53BE62A601.root",
    "m0m1j0_30522_file0": "root://eospublic.cern.ch//eos/opendata/cms/Run2016G/DoubleMuon/NANOAOD/UL2016_MiniAODv2_NanoAODv9-v2/2430000/05DD095C-F6C3-9A4F-9FB3-348A5A6403D5.root",
}

HLT_KEYWORDS = {
    "hgg_data_30521_file0": ["Diphoton", "Photon"],
    "m0m1j0_30522_file0": ["DoubleMu", "Mu", "IsoMu", "Mu17", "Mu8"],
}

results = {}
N_EVENTS_SAMPLE = 20000

for label, url in FILES.items():
    print(f"=== {label} ===")
    f = uproot.open(url)
    tree = f["Events"]
    all_branches = tree.keys()
    trigobj_branches = sorted([b for b in all_branches if b.startswith("TrigObj_")])
    hlt_branches = sorted([b for b in all_branches if b.startswith("HLT_")])
    relevant_hlt = sorted([b for b in hlt_branches if any(k.lower() in b.lower() for k in HLT_KEYWORDS[label])])

    print(f"n_events_total: {tree.num_entries}")
    print(f"TrigObj_* branches ({len(trigobj_branches)}):", trigobj_branches)
    print(f"n HLT_* branches total: {len(hlt_branches)}")
    print(f"relevant HLT_* branches ({len(relevant_hlt)}):", relevant_hlt[:20])

    types = {b: str(tree[b].typename) for b in trigobj_branches}

    arrs = tree.arrays(trigobj_branches, entry_stop=N_EVENTS_SAMPLE)
    n_trigobj = arrs["TrigObj_id"] if "TrigObj_id" in arrs.fields else None
    n_per_event = None
    id_vals = None
    id_counts = None
    filterbits_vals = None
    filterbits_counts = None
    if n_trigobj is not None:
        import awkward as ak
        counts = ak.num(n_trigobj, axis=1)
        n_per_event = {
            "mean": float(ak.mean(counts)),
            "min": int(ak.min(counts)),
            "max": int(ak.max(counts)),
        }
        flat_id = ak.flatten(n_trigobj).to_numpy()
        uniq, cnts = np.unique(flat_id, return_counts=True)
        id_counts = {int(u): int(c) for u, c in zip(uniq, cnts)}
        id_vals = {"min": int(flat_id.min()), "max": int(flat_id.max())}

    if "TrigObj_filterBits" in arrs.fields:
        flat_fb = ak.flatten(arrs["TrigObj_filterBits"]).to_numpy()
        filterbits_vals = {"min": int(flat_fb.min()), "max": int(flat_fb.max())}
        uniq_fb, cnt_fb = np.unique(flat_fb, return_counts=True)
        # top 15 most common bit values
        order = np.argsort(-cnt_fb)[:15]
        filterbits_counts = {int(uniq_fb[i]): int(cnt_fb[i]) for i in order}

    # a couple HLT path pass-rates for context (sampled)
    hlt_sample_rates = {}
    for hb in relevant_hlt[:10]:
        try:
            vals = tree[hb].array(entry_stop=N_EVENTS_SAMPLE)
            hlt_sample_rates[hb] = float(np.mean(vals))
        except Exception as e:
            hlt_sample_rates[hb] = f"ERROR: {e}"

    results[label] = {
        "file_url": url,
        "n_events_total_in_file": tree.num_entries,
        "n_events_sampled_for_stats": min(N_EVENTS_SAMPLE, tree.num_entries),
        "trigobj_branches": types,
        "n_hlt_branches_total": len(hlt_branches),
        "relevant_hlt_branches_sample": relevant_hlt[:20],
        "trigobj_id_range": id_vals,
        "trigobj_id_value_counts_sampled": id_counts,
        "trigobj_filterbits_range": filterbits_vals,
        "trigobj_filterbits_top_values_sampled": filterbits_counts,
        "trigobjs_per_event_sampled": n_per_event,
        "relevant_hlt_pass_rate_sampled": hlt_sample_rates,
    }
    print(json.dumps(results[label], indent=2, default=str)[:2000])
    print()

with open("/storage/agrp/berkom/atlas-utilization/work/upstream_trigger_cms/report_assets/deliverable2_trigobj_inventory.json", "w") as fp:
    json.dump(results, fp, indent=2, default=str)

print("DONE")
