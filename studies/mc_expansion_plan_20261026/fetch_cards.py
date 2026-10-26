"""Download the generator input cards of the planned samples, as evidence (26 Oct 2026).

For each sample in plan_samples.SAMPLES, every "/eos/opendata/cms/lhe_generators/..." card
linked from its MiniAOD record (proc/run/madspin cards, POWHEG inputs, JHUGen decay cards)
is fetched over HTTPS from opendata.cern.ch into evidence/cards/<nano recid>/, plus the
Pythia8 decay settings found in the record's own configuration text
(evidence/cards/<nano recid>/pythia_decay_settings.txt). Gridpack tarballs and shell
scripts are skipped. Run from the repo root after fetch_records.py.
"""
from __future__ import annotations

import gzip
import json
import re
import sys
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from plan_samples import SAMPLES  # noqa: E402

REC = HERE / "evidence" / "records"
OUT = HERE / "evidence" / "cards"
SKIP = (".tar.xz", ".tgz", ".tar.gz", ".sh")
DECAY_RX = re.compile(r"'((?:\d+):(?:onMode|onIfAny|onIfMatch|oneChannel|addChannel|mMin|mMax)[^']*)'")


def load(recid):
    with gzip.open(REC / f"{recid}.json.gz", "rt") as f:
        return json.load(f)["metadata"]


def fetch(url, dest):
    for attempt in range(4):
        try:
            with urllib.request.urlopen(url, timeout=90) as r:
                dest.write_bytes(r.read())
            return True
        except Exception as e:
            err = e
            time.sleep(2 * (attempt + 1))
    print("FAILED", url, err, file=sys.stderr)
    return False


def main():
    index = {}
    for recid, name, *_ in SAMPLES:
        nano = load(recid)
        mini_id = [r["recid"] for r in nano["relations"] if r["type"] == "isParentOf"][0]
        mini = load(mini_id)
        text = json.dumps(mini)
        d = OUT / str(recid)
        d.mkdir(parents=True, exist_ok=True)
        got = []
        for u in sorted(set(re.findall(r'"url": "(/eos/opendata/cms/lhe_generators/[^"]+)"', text))):
            if u.endswith(SKIP):
                continue
            dest = d / u.rsplit("/", 1)[1]
            if dest.exists() or fetch("https://opendata.cern.ch" + u, dest):
                got.append(dest.name)
        decays = sorted(set(DECAY_RX.findall(json.loads(json.dumps(text)).replace("\\'", "'"))))
        (d / "pythia_decay_settings.txt").write_text("\n".join(decays) + "\n")
        index[recid] = {"name": name, "mini_recid": int(mini_id), "cards": got, "pythia_decay_settings": decays}
        print(recid, name, len(got), decays[:4], file=sys.stderr)
    (OUT / "index.json").write_text(json.dumps(index, indent=1) + "\n")


if __name__ == "__main__":
    main()
