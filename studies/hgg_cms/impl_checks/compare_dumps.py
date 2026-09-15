"""
Implementation task 1, Part A4 (regression proof): compare the JSON dumps
produced by dump_parsed_fields.py for the same file parsed by two
different checkouts (e.g. master @ 8cf737e vs. this feature branch).

Usage: python compare_dumps.py <dump_a.json> <dump_b.json>
Exits non-zero and prints every difference found if the two are not
identical; prints "IDENTICAL" and exits 0 otherwise.
"""
import json
import sys


def compare(path_a: str, path_b: str) -> list[str]:
    a = json.load(open(path_a, encoding="utf-8"))
    b = json.load(open(path_b, encoding="utf-8"))
    diffs = []
    if a["n_events"] != b["n_events"]:
        diffs.append(f"n_events differs: a={a['n_events']} b={b['n_events']}")
    if a["fields"] != b["fields"]:
        diffs.append(f"field sets differ: a={a['fields']} b={b['fields']}")
    for f in sorted(set(a.get("fields") or []) & set(b.get("fields") or [])):
        if a["field_dtypes"].get(f) != b["field_dtypes"].get(f):
            diffs.append(
                f"field '{f}' dtype differs: a={a['field_dtypes'].get(f)} "
                f"b={b['field_dtypes'].get(f)}"
            )
        if a["field_values"].get(f) != b["field_values"].get(f):
            diffs.append(f"field '{f}' VALUES differ")
    return diffs


if __name__ == "__main__":
    diffs = compare(sys.argv[1], sys.argv[2])
    if diffs:
        print("DIFFERENT:")
        for d in diffs:
            print(" -", d)
        sys.exit(1)
    print("IDENTICAL")
