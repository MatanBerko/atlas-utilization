"""
Phase 2.2 design check (Sections 3 and 4): list every vertex- and
pileup-related branch and its doc string, from the same postVFP ggH
signal file already used by vertex_study.py and mc_trigger_check.py (no
additional file against the 6-file design-check budget). Branch names
and titles only -- no event data read.
"""
import uproot

URL = ("https://opendata.cern.ch/eos/opendata/cms/mc/RunIISummer20UL16NanoAODv9/"
       "GluGluHToGG_M-125_TuneCP5_13TeV-powheg-pythia8/NANOAODSIM/"
       "106X_mcRun2_asymptotic_v17-v1/40000/3231834B-7A6E-4840-8627-C97FDCF67268.root")

OUT = (r"C:\Users\matan\hgg-design-20260915-2027\repo\studies\hgg_cms\design_checks"
       r"\vertex_and_pileup_branches.txt")


def main():
    f = uproot.open(URL)
    events = f["Events"]
    runs = f["Runs"]
    with open(OUT, "w", encoding="utf-8") as out:
        out.write("=== Events tree: vertex/pileup-related branches ===\n")
        for k in events.keys():
            if ("Vtx" in k or k.startswith("PV") or k.startswith("Pileup")
                    or "vertex" in k.lower()):
                b = events[k]
                out.write(f"{k} | {b.typename} | {b.title!r}\n")
        out.write("\n=== Runs tree: all branches (gen-weight-sum bookkeeping) ===\n")
        for k in runs.keys():
            b = runs[k]
            out.write(f"{k} | {b.typename} | {b.title!r}\n")
    print("wrote", OUT)


if __name__ == "__main__":
    main()
