"""
Phase 2.2 design check (Section 2, step 1): does the diphoton trigger bit
exist in simulation, and what fraction of signal MC events pass it?
Justifies requiring the same trigger cut in MC as in data (Section 2).

Read-only, remote (HTTPS range requests), <=1000 events from the same
postVFP ggH signal file already used by vertex_study.py (same file, so
no additional file counted against the 6-file design-check budget).
"""
import json
import uproot

URL = ("https://opendata.cern.ch/eos/opendata/cms/mc/RunIISummer20UL16NanoAODv9/"
       "GluGluHToGG_M-125_TuneCP5_13TeV-powheg-pythia8/NANOAODSIM/"
       "106X_mcRun2_asymptotic_v17-v1/40000/3231834B-7A6E-4840-8627-C97FDCF67268.root")
N = 1000
TRIGGER = "HLT_Diphoton30_18_R9Id_OR_IsoCaloId_AND_HE_R9Id_Mass90"


def main():
    f = uproot.open(URL)
    tree = f["Events"]
    exists = TRIGGER in tree.keys()
    result = {"trigger": TRIGGER, "exists_in_mc_file": exists}
    if exists:
        arr = tree[TRIGGER].array(entry_stop=N, library="np")
        result["n_events_read"] = len(arr)
        result["n_pass"] = int(arr.sum())
        result["fraction_pass"] = float(arr.mean())

    out_path = (r"C:\Users\matan\hgg-design-20260915-2027\repo\studies\hgg_cms\design_checks"
                r"\mc_trigger_check_results.json")
    with open(out_path, "w", encoding="utf-8") as fjson:
        json.dump(result, fjson, indent=2)
    print(json.dumps(result, indent=2))
    print("wrote", out_path)


if __name__ == "__main__":
    main()
