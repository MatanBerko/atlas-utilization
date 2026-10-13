"""
Luminosity-coverage check, four datasets: ONE PBS array subjob per
(dataset, era) record.

Reads ONLY the small ``LuminosityBlocks`` tree of every file of one CERN
Open Data record, and only its ``run`` and ``luminosityBlock`` branches --
no event content is touched. This is exactly the method of
studies/hgg_cms/impl_checks/lumi_coverage/recompute_missing_sections.py,
which did the same thing for DoubleEG alone; the only changes are that the
file list comes from the repository's own committed list rather than a
live portal fetch, that the files are opened over xrootd (this runs on the
cluster, where xrootd works), and that one record is handled per process
so the work can be an array job.

Writes exactly one JSON per record into --output-dir:
    present_<record_key>.json

Usage:
    python read_lumisections_for_record.py --record-key DoubleMuon_G \
        --output-dir <dir> [--file-lists <record_file_lists.json>]
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
DEFAULT_FILE_LISTS = REPO_ROOT / "studies" / "cms_datasets" / "evidence" / \
    "record_file_lists.json"

# The four delivered datasets only. SingleElectron/JetHT/MET are present in
# the committed file list but are out of scope for this check.
DELIVERY_RECORD_KEYS = [
    "DoubleMuon_G", "DoubleMuon_H",
    "SingleMuon_G", "SingleMuon_H",
    "DoubleEG_G", "DoubleEG_H",
    "MuonEG_G", "MuonEG_H",
]

READ_ATTEMPTS = 6
READ_BACKOFF_SEC = 5.0


def read_lumiblocks_pairs(url: str) -> tuple[set, str | None]:
    """The (run, luminosityBlock) pairs recorded in one file's
    LuminosityBlocks tree. Retries, because a transient xrootd failure must
    not be mistaken for a genuinely absent lumisection -- the whole point of
    the check is which sections are missing, so a read error has to be a
    hard failure, never a silent zero."""
    import uproot

    last_err = None
    for attempt in range(READ_ATTEMPTS):
        try:
            with uproot.open(url) as f:
                tree = f["LuminosityBlocks"]
                arrays = tree.arrays(["run", "luminosityBlock"], library="np")
            return set(zip(arrays["run"].tolist(),
                           arrays["luminosityBlock"].tolist())), None
        except Exception as exc:  # noqa: BLE001 -- recorded, then retried
            last_err = f"{type(exc).__name__}: {exc}"
            if attempt < READ_ATTEMPTS - 1:
                time.sleep(READ_BACKOFF_SEC * (attempt + 1))
    return set(), last_err


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--record-key", required=True, choices=DELIVERY_RECORD_KEYS)
    ap.add_argument("--output-dir", required=True)
    ap.add_argument("--file-lists", default=str(DEFAULT_FILE_LISTS))
    args = ap.parse_args()

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    records = json.loads(Path(args.file_lists).read_text(encoding="utf-8"))["records"]
    rec = records[args.record_key]
    urls = rec["file_urls"]

    print(f"record_key={args.record_key} dataset={rec['dataset_label']} "
          f"era={rec['era']} record_id={rec['record_id']} n_files={len(urls)}",
          flush=True)

    present: set = set()
    per_file = []
    failed = []
    for i, url in enumerate(urls, 1):
        t0 = time.time()
        pairs, err = read_lumiblocks_pairs(url)
        name = url.rsplit("/", 1)[-1]
        if err is not None:
            failed.append({"url": url, "error": err})
            print(f"[{i}/{len(urls)}] FAILED {name}: {err}", flush=True)
        else:
            present |= pairs
            per_file.append({"file": name, "n_lumisections": len(pairs)})
            print(f"[{i}/{len(urls)}] {name}: {len(pairs)} lumisections "
                  f"({time.time() - t0:.1f}s)", flush=True)

    out = {
        "record_key": args.record_key,
        "dataset_label": rec["dataset_label"],
        "era": rec["era"],
        "record_id": rec["record_id"],
        "n_files_expected": len(urls),
        "n_files_ok": len(per_file),
        "n_files_failed": len(failed),
        "failed_files": failed,
        "n_present_pairs": len(present),
        "present_pairs": sorted([int(r), int(ls)] for r, ls in present),
        "per_file": per_file,
        "method": "LuminosityBlocks tree, branches run + luminosityBlock only",
    }
    out_path = out_dir / f"present_{args.record_key}.json"
    out_path.write_text(json.dumps(out), encoding="utf-8")
    print(f"wrote {out_path}: {len(present)} distinct lumisections, "
          f"{len(failed)} failed files", flush=True)

    # A failed file would understate coverage, so fail the subjob loudly
    # rather than let the aggregation average over a hole.
    if failed:
        print(f"ERROR: {len(failed)} file(s) could not be read", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
