"""P1 option B (3 Nov 2026): the complete MC file list. NETWORK test (reads the CERN Open Data portal).

Run as a script:  PYTHONPATH=. python studies/cms_mc_weights_v3/tests/test_file_list_complete.py

1. For the 13 delivered MC records, fetch_file_list_complete is IDENTICAL (same files, same order) to
   the list the 25 Oct production used: the 17 Oct input sweep (evidence/fullrun_inputs_20261017.json),
   which make_fullrun_mappings.py checked file by file when it wrote the 25 Oct mappings.
2. For the 8 page-limited records, the page-1 list (fetch_file_list) is a prefix of the complete list,
   which only appends; counts reported. For all 54 new records: prefix, and the total.
3. The driver uses the complete list only with --is-mc; the data path keeps fetch_file_list.
"""
from __future__ import annotations

import inspect
import json
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
from studies.m0m1j0_cms.design_checks.common import fetch_file_list, fetch_file_list_complete  # noqa: E402

SWEEP = REPO / "studies/cms_mc_weights_v3/evidence/fullrun_inputs_20261017.json"
REG = REPO / "studies/cms_mc_weights_v3/cms_mc_normalisation_v4.json"
PAGE_LIMITED = (64659, 69717, 72761, 37446, 68591, 68601, 71297, 74906)
EXPECTED = {64659: 35, 69717: 30, 72761: 6, 37446: 40, 68591: 7, 68601: 30, 71297: 7, 74906: 22}
RESULTS = {}


def test_delivered_identical():
    sweep = json.loads(SWEEP.read_text())["records"]
    assert len(sweep) == 13
    out = {}
    for rid, v in sweep.items():
        old = [f["url"] for f in v["files"]]
        new = fetch_file_list_complete(int(rid))
        assert new == old, (rid, len(old), len(new))
        out[rid] = len(new)
    RESULTS["delivered_identical"] = out


def test_new_prefix_and_counts():
    reg = json.loads(REG.read_text())["records"]
    new_ids = sorted(int(r) for r, v in reg.items() if "decision_2026_11_03" in v and v["in_full_run"])
    assert len(new_ids) == 54
    rows, total = {}, 0
    for rid in new_ids:
        page1 = fetch_file_list(rid)
        full = fetch_file_list_complete(rid)
        assert full[:len(page1)] == page1, rid           # only appends
        rows[rid] = (len(page1), len(full))
        total += len(full)
    for rid, n in EXPECTED.items():
        assert rows[rid][1] == n, (rid, rows[rid], n)
    changed = {r: v for r, v in rows.items() if v[0] != v[1]}
    assert set(changed) == {64659, 37446, 68591, 68601, 71297, 74906}, changed   # 69717, 72761 unchanged
    assert total == 1206, total
    RESULTS["new_page1_vs_complete"] = {str(k): v for k, v in rows.items()}
    RESULTS["new_total_files"] = total


def test_data_path_unchanged():
    from studies.cms_datasets.cluster import run_dataset_on_file as drv
    sig = inspect.signature(drv.resolve_file_url)
    assert sig.parameters["complete"].default is False
    src = inspect.getsource(drv.main)
    assert "resolve_file_url(args.record_id, args.file_index, complete=bool(args.is_mc))" in src


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"PASS {t.__name__}")
        except Exception as e:  # noqa: BLE001
            failed += 1
            print(f"FAIL {t.__name__}: {e!r}")
    print(json.dumps(RESULTS, default=list))
    print(f"{len(tests) - failed}/{len(tests)} passed")
    sys.exit(1 if failed else 0)
