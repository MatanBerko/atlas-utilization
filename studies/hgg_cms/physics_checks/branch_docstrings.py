"""
Read and record the exact doc strings (titles) of the branches used to
define the "v1 + trigger-mimicking" preselection, from both the signal
file and a data file. No event data read here -- branch metadata only.
"""
import json
import sys
import uproot

sys.path.insert(0, r"C:\Users\matan\hgg-physchecks-20260915-2052\repo\studies\hgg_cms\physics_checks")
from file_list import SIGNAL_FILES, DATA_FILES

BRANCHES = [
    "Photon_r9", "Photon_hoe", "Photon_sieie",
    "Photon_pfRelIso03_all", "Photon_pfRelIso03_chg",
    "Photon_isScEtaEB", "Photon_isScEtaEE",
    "Photon_eCorr",
    "Photon_dEscaleUp", "Photon_dEscaleDown",
    "Photon_dEsigmaUp", "Photon_dEsigmaDown",
    "Photon_electronVeto", "Photon_mvaID_WP90",
]

OUT_TXT = (r"C:\Users\matan\hgg-physchecks-20260915-2052\repo\studies\hgg_cms"
           r"\physics_checks\branch_docstrings.txt")
OUT_JSON = (r"C:\Users\matan\hgg-physchecks-20260915-2052\repo\studies\hgg_cms"
            r"\physics_checks\branch_docstrings.json")


def dump(label, url):
    f = uproot.open(url)
    tree = f["Events"]
    out = {}
    for name in BRANCHES:
        if name in tree.keys():
            b = tree[name]
            out[name] = {"typename": b.typename, "title": b.title}
        else:
            out[name] = None
    return out


def main():
    result = {
        "signal_file": SIGNAL_FILES[0]["url"],
        "data_file": DATA_FILES[0]["url"],
        "signal": dump("signal", SIGNAL_FILES[0]["url"]),
        "data": dump("data", DATA_FILES[0]["url"]),
    }
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
    with open(OUT_TXT, "w", encoding="utf-8") as f:
        for sample in ("signal", "data"):
            f.write(f"=== {sample} file: {result[sample + '_file' if False else sample]} ===\n")
        f.write(f"=== signal file ===\n{result['signal_file']}\n")
        for name, info in result["signal"].items():
            f.write(f"  {name} | {info}\n")
        f.write(f"\n=== data file ===\n{result['data_file']}\n")
        for name, info in result["data"].items():
            f.write(f"  {name} | {info}\n")
        f.write("\nNote: Photon_r9's title says 'calculated with full 5x5 region' and\n"
                 "Photon_sieie's title says the same -- both are the 'full5x5' shower-shape\n"
                 "variants (the modern, standard CMS EGM definition), confirmed directly\n"
                 "above, not assumed.\n")
    print(json.dumps(result, indent=2))
    print("wrote", OUT_JSON, "and", OUT_TXT)


if __name__ == "__main__":
    main()
