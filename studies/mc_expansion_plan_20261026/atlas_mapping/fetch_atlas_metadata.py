"""Step 1: public ATLAS Open Data metadata (atlasopenmagic, release 2024r-pp) for Maryna's background DSIDs.

Writes atlas_bkg_metadata.json (raw per-DSID dicts + the call used), atlas_bkg_metadata.csv (flat),
and atlas_release_all_dsids.json (every dataset_number in the release, for the 337-vs-353 question).
No ROOT file is downloaded; get_urls only lists file names.
"""
import csv
import json

import atlasopenmagic as atom

from dsid_list import rows

RELEASE = "2024r-pp"
FIELDS = ["dsid", "record", "maryna_class", "physics_short", "process", "description", "generator", "keywords",
          "cross_section_pb", "kFactor", "genFiltEff", "xsec_k_filt_pb", "nEvents", "sumOfWeights",
          "sumOfWeightsSquared", "n_files", "e_tag", "PDF", "job_path"]

atom.set_release(RELEASE)
allmeta = atom.get_all_metadata()
json.dump({"call": f"atlasopenmagic {atom.__dict__.get('__version__', '1.10.1')} set_release('{RELEASE}'); "
                   "get_all_metadata()",
           "n": len(allmeta),
           "dataset_numbers": sorted(str(v.get("dataset_number", k)) for k, v in allmeta.items())},
          open("atlas_release_all_dsids.json", "w"), indent=1)

raw, flat, missing = {}, [], []
for r in rows():
    d = r["dsid"]
    try:
        m = atom.get_metadata(d)
    except Exception as e:  # noqa: BLE001 - record the failure, do not guess
        m = None
        err = repr(e)
    if not m:
        missing.append({"dsid": d, "error": err if m is None else "empty"})
        flat.append({**r, "physics_short": "UNKNOWN"})
        continue
    try:
        urls = atom.get_urls(d, skim="noskim", protocol="https")
    except Exception as e:  # noqa: BLE001
        urls = None
    m = {k: v for k, v in m.items()}
    m["n_files_get_urls"] = None if urls is None else len(urls)
    raw[d] = {"maryna": r, "metadata": m,
              "call": f"atom.set_release('{RELEASE}'); atom.get_metadata('{d}'); "
                      f"atom.get_urls('{d}', skim='noskim', protocol='https')"}
    row = {**r}
    for f in FIELDS[3:]:
        row[f] = m.get(f)
    row["keywords"] = ";".join(m.get("keywords") or [])
    row["n_files"] = m["n_files_get_urls"]
    try:
        row["xsec_k_filt_pb"] = float(m["cross_section_pb"]) * float(m["kFactor"]) * float(m["genFiltEff"])
    except (TypeError, ValueError, KeyError):
        row["xsec_k_filt_pb"] = None
    flat.append(row)

json.dump({"release": RELEASE, "source": "atlasopenmagic (public ATLAS Open Data metadata)",
           "missing": missing, "datasets": raw}, open("atlas_bkg_metadata.json", "w"), indent=1, default=str)
with open("atlas_bkg_metadata.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=FIELDS)
    w.writeheader()
    for row in flat:
        w.writerow({k: row.get(k) for k in FIELDS})
print("found", len(raw), "missing", len(missing), missing[:5])
