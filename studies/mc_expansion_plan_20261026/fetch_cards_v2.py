"""Fetch the generator cards of the 31 Oct samples that have none yet (DECISIONS.md).

Same method as fetch_cards.py (every "/eos/opendata/cms/lhe_generators/..." card linked from the
MiniAOD record, plus the Pythia8 decay settings of its configuration text), for the planned
samples of plan_samples_v2 without an evidence/cards/<recid>/ directory, plus the delivered
ZZTo4L 75589 (comparison for the D14 check). Only NEW directories are written; existing card
directories are left untouched. Records come from evidence/records/ or atlas_mapping/cms_records/.
Writes evidence/cards/index_v2.json. Run from anywhere: python3 fetch_cards_v2.py
"""
from __future__ import annotations

import gzip
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from fetch_cards import DECAY_RX, SKIP, fetch  # noqa: E402
from plan_samples_v2 import SAMPLES_V2  # noqa: E402

OUT = HERE / "evidence" / "cards"
REC_DIRS = (HERE / "evidence" / "records", HERE / "atlas_mapping" / "cms_records")
EXTRA = {75589: "ZZTo4L (delivered; comparison for D14)"}


def load(recid):
    for d in REC_DIRS:
        p = d / f"{recid}.json.gz"
        if p.exists():
            with gzip.open(p, "rt") as f:
                return json.load(f)["metadata"]
    raise FileNotFoundError(recid)


def main():
    todo = {r: n for r, n, *_ in SAMPLES_V2 if not (OUT / str(r)).exists()}
    todo.update({r: n for r, n in EXTRA.items() if not (OUT / str(r)).exists()})
    index = {}
    for recid, name in todo.items():
        nano = load(recid)
        mini_id = [r["recid"] for r in nano["relations"] if r["type"] == "isParentOf"][0]
        text = json.dumps(load(mini_id))
        d = OUT / str(recid)
        d.mkdir(parents=True)
        got = []
        for u in sorted(set(re.findall(r'"url": "(/eos/opendata/cms/lhe_generators/[^"]+)"', text))):
            if u.endswith(SKIP):
                continue
            dest = d / u.rsplit("/", 1)[1]
            if fetch("https://opendata.cern.ch" + u, dest):
                got.append(dest.name)
        decays = sorted(set(DECAY_RX.findall(text.replace("\\'", "'"))))
        (d / "pythia_decay_settings.txt").write_text("\n".join(decays) + "\n")
        index[recid] = {"name": name, "mini_recid": int(mini_id), "cards": got,
                        "pythia_decay_settings": decays,
                        "card_urls": ["https://opendata.cern.ch" + u for u in sorted(set(
                            re.findall(r'"url": "(/eos/opendata/cms/lhe_generators/[^"]+)"', text)))]}
        print(recid, name, len(got), decays[:4], file=sys.stderr)
    (OUT / "index_v2.json").write_text(json.dumps(index, indent=1) + "\n")


if __name__ == "__main__":
    main()
