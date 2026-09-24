"""
m0m1j0 design phase, design check 0: portal file inventory for records
30522 (DoubleMuon Run2016G) and 30555 (DoubleMuon Run2016H).

For EVERY file in both records (not just the two used for the other
checks): the exact URI, HTTP Content-Length (bytes), and total event
count (tree.num_entries -- metadata only, no branches read, no data
downloaded beyond the TTree header). This is the source for Section I's
"file counts and event totals from the portal" job-sizing input, and
for choosing (and recording, exactly) which one file per record the
other design checks use.

Read-only: no file is kept locally; only metadata is written out.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import common  # noqa: E402

RECORDS = {30522: "DoubleMuon Run2016G", 30555: "DoubleMuon Run2016H"}


def main():
    out = {}
    for rec_id, label in RECORDS.items():
        print(f"=== record {rec_id} ({label}) ===")
        files = common.fetch_file_list(rec_id)
        print(f"  {len(files)} files in portal file list")
        file_info = []
        total_events = 0
        for i, uri in enumerate(files):
            t0 = time.time()
            try:
                head = common.https_head(uri)
                size_bytes = int(head["headers"].get("Content-Length", -1))
            except Exception as e:
                size_bytes = None
                print(f"  [{i}] HEAD failed: {e}")
            try:
                f = common.open_root_https(uri)
                n_entries = int(f["Events"].num_entries)
                f.close()
            except Exception as e:
                n_entries = None
                print(f"  [{i}] open failed: {e}")
            dt = time.time() - t0
            if n_entries is not None:
                total_events += n_entries
            print(f"  [{i}] {uri.split('/')[-1]}: size={size_bytes} events={n_entries} ({dt:.1f}s)")
            file_info.append({"index": i, "uri": uri, "size_bytes": size_bytes, "n_events": n_entries})
        out[str(rec_id)] = {
            "label": label,
            "n_files": len(files),
            "total_events": total_events,
            "files": file_info,
        }
        print(f"  TOTAL: {len(files)} files, {total_events} events")

    common.write_json(HERE / "00_file_inventory.json", out)


if __name__ == "__main__":
    main()
