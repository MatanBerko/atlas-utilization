#!/usr/bin/env python3
"""
Read-only diagnostic for the union-vs-intersection EventChunk bug
(upstream d488f21, domain/events.py).

Background: the OLD EventChunk.from_batches() called
``ak.concatenate([batch.events for batch in batches])`` directly on the
per-batch event records. If the batches being merged into one chunk had
different top-level fields (particle collections -- Electrons, Muons,
Jets, Photons, Taus, BJets), ak.concatenate on record arrays with
mismatched fields silently keeps only the fields common to *every* batch,
dropping the rest from the whole merged chunk. No error, no warning.

This script does NOT need to reconstruct which specific input files or
batches went into a chunk -- it checks the parsed OUTPUT chunk files
directly, which is the only place the bug's effect could actually show
up. For a real CMS NanoAOD H->ZZ->4l parse, every chunk is expected to
carry all of the base object collections the schema requests
(Electrons, Muons, Jets, Photons, Taus) as top-level branches -- even
for events with zero particles of a given type, the branch itself
(e.g. "Photons_pt") is still present, just with an empty per-event list.
A collection being COMPLETELY ABSENT as a branch from an otherwise
normal parsed chunk is the direct, unambiguous signature this bug would
leave behind.

For each parsed_data/*.root file under --run-dir (or each file listed
via --files), this script:
  1. Opens it read-only with uproot (no writes, no moves, no deletes).
  2. Lists which of the expected base collections have at least one
     branch present, and which are completely absent.
  3. Groups files by CMS record ID (parsed from the filename) and flags
     any record whose chunks disagree with each other on which
     collections are present -- that inconsistency is the bug's
     signature within a single record's own set of chunks.

Exit summary states plainly whether the drop condition was observed at
all in the data checked, and lists exactly which files/collections.

Usage:
    python scripts/check_collection_drop.py --run-dir /path/to/run_dir
    python scripts/check_collection_drop.py --files a.root b.root ...
"""
from __future__ import annotations

import argparse
import re
from collections import defaultdict
from pathlib import Path

# Base collections this pipeline's cms-nanoaod schema always requests
# (services/parsing/schemas.py RELEASE_SCHEMAS["cms-nanoaod"]["objects"]).
EXPECTED_COLLECTIONS = ["Electrons", "Muons", "Jets", "Photons", "Taus"]

_RECORD_RE = re.compile(r"parsed_record_(\d+)_")


def record_id_from_filename(name: str) -> str:
    m = _RECORD_RE.search(name)
    return m.group(1) if m else "unknown"


def collections_in_file(path: Path) -> dict:
    """Return {"present": [...], "absent": [...]} of EXPECTED_COLLECTIONS."""
    import uproot

    with uproot.open(str(path)) as f:
        tree_key = "events" if "events" in f else ("CollectionTree" if "CollectionTree" in f else None)
        if tree_key is None:
            return {"present": [], "absent": list(EXPECTED_COLLECTIONS), "error": f"no recognised tree in {path.name}"}
        branches = set(f[tree_key].keys())

    present, absent = [], []
    for coll in EXPECTED_COLLECTIONS:
        # A collection is "present" if any of its own branches (e.g. Electrons_pt)
        # exist. It is "absent" only if NONE of its branches exist at all.
        has_any = any(b.startswith(f"{coll}_") or b == f"n{coll}" for b in branches)
        (present if has_any else absent).append(coll)
    return {"present": present, "absent": absent}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run-dir", type=Path, default=None,
                     help="A run directory containing parsed_data/*.root (or pointing directly at a parsed_data dir)")
    ap.add_argument("--files", nargs="*", type=Path, default=None,
                     help="Explicit list of parsed .root files to check instead of --run-dir")
    args = ap.parse_args()

    if args.files:
        files = sorted(args.files)
    elif args.run_dir:
        candidate = args.run_dir / "parsed_data"
        search_dir = candidate if candidate.is_dir() else args.run_dir
        files = sorted(search_dir.glob("*.root"))
    else:
        ap.error("Provide --run-dir or --files")
        return 2

    if not files:
        print(f"No .root files found to check.")
        return 1

    print(f"Checking {len(files)} parsed chunk file(s), read-only, no writes:")
    for f in files:
        print(f"  {f}")
    print()

    per_file = {}
    for f in files:
        result = collections_in_file(f)
        per_file[f.name] = result
        tag = "OK (all present)" if not result["absent"] else f"MISSING: {result['absent']}"
        err = f"  [{result['error']}]" if "error" in result else ""
        print(f"{f.name}: present={result['present']} absent={result['absent']}  -> {tag}{err}")

    print()
    print("=" * 70)
    print("Per-record consistency check (same record, different chunks):")
    by_record = defaultdict(list)
    for fname, result in per_file.items():
        by_record[record_id_from_filename(fname)].append((fname, tuple(sorted(result["present"]))))

    any_drop_observed = False
    any_inconsistency = False
    for record_id, entries in sorted(by_record.items()):
        signatures = {sig for _, sig in entries}
        if len(signatures) > 1:
            any_inconsistency = True
            print(f"  Record {record_id}: INCONSISTENT collection sets across its own chunks!")
            for fname, sig in entries:
                print(f"    {fname}: present={list(sig)}")
        else:
            (sig,) = signatures
            missing = set(EXPECTED_COLLECTIONS) - set(sig)
            note = f" (missing {sorted(missing)} in every chunk of this record -- consistent, not the bug's signature)" if missing else ""
            print(f"  Record {record_id}: consistent across {len(entries)} chunk(s): {list(sig)}{note}")

    for fname, result in per_file.items():
        if result["absent"]:
            any_drop_observed = True

    print()
    print("=" * 70)
    print("VERDICT")
    print("=" * 70)
    if any_inconsistency:
        print("YES -- at least one record's chunks disagree on which collections")
        print("are present. This is the direct signature of the union-vs-")
        print("intersection concat bug: some chunk of this record silently")
        print("dropped a collection that other chunks of the SAME record kept.")
    elif any_drop_observed:
        print("A collection is missing from at least one chunk, but it is")
        print("missing CONSISTENTLY across every chunk of that record -- this")
        print("looks like the record genuinely never had that collection")
        print("(or it was never accessible), not evidence of this specific bug.")
    else:
        print("NO -- every chunk file checked carries all expected collections.")
        print("No evidence of the union-vs-intersection drop in the data checked.")
    print()
    print(f"(Coverage note: {len(files)} chunk file(s) were checked. If this is")
    print("fewer than the full run's original chunk count, this verdict only")
    print("covers what still exists on disk -- say so explicitly in any report.)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
