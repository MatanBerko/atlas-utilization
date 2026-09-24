"""
Implementation task 1, Part A4 (regression proof): parse one real CMS
NanoAOD file with a given checkout's services.parsing.FileParser and dump
every resulting field to JSON, for byte-for-byte comparison against
another checkout's output on the identical input.

Usage: python dump_parsed_fields.py <repo_root> <record_id> <file_url> <out_json>

Reads at most 2,000 events (via a tree wrapper that caps num_entries),
matching the task's real-file-reading limit. No full-file download --
uproot streams only the requested branches over HTTPS range requests.
"""
import json
import sys

repo_root = sys.argv[1]
record_id = sys.argv[2]
file_url = sys.argv[3]
out_path = sys.argv[4]
MAX_EVENTS = 2000

sys.path.insert(0, repo_root)

import awkward as ak  # noqa: E402
import uproot  # noqa: E402
from services.parsing.file_parser import FileParser  # noqa: E402


class _CappedTree:
    def __init__(self, real_tree, max_entries):
        self._real = real_tree
        self.num_entries = min(real_tree.num_entries, max_entries)

    def keys(self):
        return self._real.keys()

    def arrays(self, branches, entry_start, entry_stop, library):
        capped_stop = min(entry_stop, self.num_entries)
        return self._real.arrays(
            branches, entry_start=entry_start, entry_stop=capped_stop, library=library
        )


class _RootProxy(dict):
    def keys(self):
        return ["Events;1"]


def main():
    tree_names = ["Events", "CollectionTree"]
    real_file = uproot.open(file_url)
    real_keys = [k.split(";")[0] for k in real_file.keys()]
    tree_name = next((t for t in tree_names if t in real_keys), tree_names[0])
    capped = _CappedTree(real_file[tree_name], MAX_EVENTS)

    class _Proxy(dict):
        def keys(self):
            return [f"{tree_name};1"]

    root = _Proxy({tree_name: capped})

    release_year = record_id if not record_id.isdigit() else f"record_{record_id}"
    result = FileParser._parse_opened_file(
        root, tree_names, release_year, MAX_EVENTS, file_url, False, None,
    )

    out = {
        "repo_root": repo_root,
        "record_id": record_id,
        "file_url": file_url,
        "n_events": len(result) if result is not None else None,
        "fields": sorted(result.fields) if result is not None else None,
        "field_dtypes": {},
        "field_values": {},
    }
    if result is not None:
        for f in result.fields:
            col = result[f]
            try:
                out["field_dtypes"][f] = str(ak.to_numpy(ak.flatten(col, axis=None)).dtype)
            except Exception as e:
                out["field_dtypes"][f] = f"ERROR:{e}"
            out["field_values"][f] = ak.to_list(col)

    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(out, fh)
    print(f"wrote {out_path}: n_events={out['n_events']}, fields={out['fields']}")


if __name__ == "__main__":
    main()
