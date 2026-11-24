#!/usr/bin/env python
"""Public ATLAS Open Data metadata for the 246 Nominal-6 DSIDs (read-only), as upstream reads it:
atlasopenmagic 1.5.0 (upstream docker/requirements.txt:2), release 2024r-pp (upstream config.yaml:110-111),
get_metadata(dsid) for physics_short, generator, cross_section_pb, kFactor, genFiltEff, sumOfWeights, description,
and len(get_urls(dsid)) for the number of files. Run in a scratch venv with atlasopenmagic==1.5.0:

    python fetch_atlas_public.py <dsid list file> <out.json>
"""
import json
import sys
import time

import atlasopenmagic as atom


def main():
    dsids = [l.strip() for l in open(sys.argv[1]) if l.strip()]
    atom.set_release("2024r-pp")
    out = {"release": atom.get_current_release(), "package": "atlasopenmagic==1.5.0",
           "read": time.strftime("%Y-%m-%d %H:%M %Z"), "records": {}}
    for d in dsids:
        rec = {}
        try:
            rec["metadata"] = atom.get_metadata(d)
        except Exception as e:  # noqa: BLE001 - a DSID missing from the release is a finding
            rec["error_metadata"] = repr(e)
        try:
            rec["n_urls"] = len(atom.get_urls(d))
        except Exception as e:  # noqa: BLE001
            rec["error_urls"] = repr(e)
        out["records"][d] = rec
        print(d, "ok" if "metadata" in rec else rec.get("error_metadata"), rec.get("n_urls"), flush=True)
    json.dump(out, open(sys.argv[2], "w"), indent=1, sort_keys=True, default=str)


if __name__ == "__main__":
    main()
