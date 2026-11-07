"""Checks of the v5 registry (D15 rare-top release + E3, 7 Nov 2026).

Run as a script (the Mac has no pytest):  PYTHONPATH=. python studies/cms_mc_weights_v3/tests/test_registry_v5.py
Offline except test_b_live (the CERN Open Data API; it FAILS if the portal is unreachable).
v5 must be v4 plus exactly the D15 changes; the v4 checks (test_registry_v4.py) still cover the rest.
"""
from __future__ import annotations

import gzip
import json
import math
import pathlib
import re
import subprocess
import sys
import urllib.request

REPO = pathlib.Path(__file__).resolve().parents[3]
STUDY = REPO / "studies" / "cms_mc_weights_v3"
V4 = json.loads((STUDY / "cms_mc_normalisation_v4.json").read_text())
V5 = json.loads((STUDY / "cms_mc_normalisation_v5.json").read_text())
EV = STUDY / "sources" / "mcexp_20261103"

# Matan's D15 list (7 Nov 2026), typed independently of the decisions file: nano -> (mini, sigma_eff pb, order)
D15 = {68325: (68324, 0.07561, "generator NLO"), 64873: (64872, 0.01105, "generator LO"),
       68206: (68204, 0.5113, "generator NLO"), 68185: (68184, 0.0537, "generator NLO")}
TTZ = {68185, 68187, 68206}


def saved(rid):
    with gzip.open(EV / "records" / f"{rid}.json.gz", "rt") as f:
        return json.load(f)["metadata"]


def card_text(rid):
    d = EV / "cards" / str(rid)
    return "\n".join(p.read_text(errors="replace") for p in sorted(d.iterdir()) if p.is_file())


# ---------------------------------------------------------------- a: sigma_eff = Matan's value = product of factors
def test_a_sigma_matches_d15_and_factors():
    for rid, (mini, sigma, order) in D15.items():
        r = V5["records"][str(rid)]
        assert r["in_full_run"] is True, rid
        assert r["mini_recid"] == mini, rid
        assert r["cross_section_pb"] == sigma, rid
        assert r["k_factor"] == 1.0 and r["gen_filt_eff"] == 1.0 and r["sum_of_weights"] is None, rid
        d = r["decision_2026_11_07"]
        assert d["order"] == order, rid
        assert abs(math.prod(f["value"] for f in d["factors"]) / sigma - 1) <= 1e-4, rid
    assert "no NLO sample or published total" in V5["records"]["64873"]["decision_2026_11_07"]["note"]


# ---------------------------------------------------------------- b: portal value (saved copy, and live)
def test_b_saved_portal_values():
    for rid, (mini, sigma, _) in D15.items():
        nano = saved(rid)
        assert [x["recid"] for x in nano["relations"] if x["type"] == "isParentOf"][0] in (mini, str(mini)), rid
        xs = saved(mini)["cross_section"]
        assert float(xs["total_value"]) == sigma, (rid, xs)
        assert float(xs["filter_efficiency"]) == 1.0 and float(xs["matching_efficiency"]) == 1.0, (rid, xs)


def test_b_live_portal_values():
    for rid, (mini, sigma, _) in D15.items():
        with urllib.request.urlopen(f"https://opendata.cern.ch/api/records/{mini}", timeout=60) as r:
            xs = json.load(r)["metadata"]["cross_section"]
        assert float(xs["total_value"]) == sigma, (rid, xs)


# ---------------------------------------------------------------- c: tau inclusion (no BR applied by hand)
def test_c_tau_inclusion():
    # Each sigma is the generator total of the generated process; no BR is applied by hand, so the tau
    # question is only "does the generated process match the sample name". l = e mu ta where leptons appear.
    for rid in (68325, 64873, 68185):
        assert re.search(r"define l\+ = e\+ mu\+ ta\+", card_text(rid)), rid
    assert re.search(r"generate p p > t b~ j l\+ l- \$\$ w\+ w- \[QCD\]", card_text(68325))
    assert re.search(r"generate p p > t w- l\+ l- /h @0", card_text(64873))
    assert re.search(r"generate p p > t t~ l\+ l- / h \[QCD\]", card_text(68185))
    assert re.search(r"generate p p > t t~ z / h \[QCD\]", card_text(68206))
    assert re.search(r"decay z > q q~", card_text(68206))      # Z -> qq by MadSpin, inside the portal value
    for rid in D15:
        assert len(V5["records"][str(rid)]["decision_2026_11_07"]["factors"]) == 1, rid   # no hand-applied BR


# ---------------------------------------------------------------- d: v5 = v4 + D15 only, no double counting
def test_d_only_d15_changes():
    assert set(V5["records"]) == set(V4["records"]) and V5["n_records"] == 73
    for rid, r4 in V4["records"].items():
        r5 = V5["records"][rid]
        changed = {k for k in set(r4) | set(r5) if r4.get(k) != r5.get(k)}
        if int(rid) in D15:
            assert changed == {"in_full_run", "decision_2026_11_07"} | ({"exception_E3_2026_11_07"} if int(rid) in TTZ else set()), (rid, changed)
            assert r5["decision_2026_11_03"] == r4["decision_2026_11_03"], rid          # history kept
        elif int(rid) in TTZ:
            assert changed == {"exception_E3_2026_11_07"}, (rid, changed)
        else:
            assert not changed, (rid, changed)
    assert {int(r) for r in V5["full_run_records"]} == {int(r) for r in V4["full_run_records"]} | set(D15)
    assert len(V5["full_run_records"]) == 71
    assert {int(r) for r in V5["not_in_full_run_records"]} == {35671, 42407}
    assert V5["deliberately_excluded_records"] == V4["deliberately_excluded_records"]
    assert V5["estimates"] == V4["estimates"] == {"40062": V4["estimates"]["40062"]}
    # double counting: the ttZ pieces split by Z decay / m(ll) and never repeat a record
    titles = {rid: V5["records"][str(rid)]["portal_dataset_title"] for rid in TTZ}
    assert "TTZToLL_M-1to10" in titles[68185] and "TTZToLLNuNu_M-10" in titles[68187] and "TTZToQQ" in titles[68206]
    full_titles = [V5["records"][r]["portal_dataset_title"].split("/")[1] for r in V5["full_run_records"]]
    assert len(full_titles) == len(set(full_titles))


def test_e3_note_on_all_ttz():
    for rid in TTZ:
        note = V5["records"][str(rid)]["exception_E3_2026_11_07"]
        assert "kFactor 1.11" in note and "k = 1" in note, rid
    assert V5["records"]["68187"]["cross_section_pb"] == 0.2439           # delivered value unchanged


def test_registry_reproducible_and_builder_default():
    for script in ("build_registry_v5.py", "build_registry_v4.py"):
        out = subprocess.run([sys.executable, str(STUDY / script), "--check"], capture_output=True, text=True)
        assert out.returncode == 0, out.stdout + out.stderr
    sys.path.insert(0, str(REPO))
    from studies.cms_mc_weights_v3.deliver import build_mc_delivery as B
    assert B.REGISTRY_PATH.name == "cms_mc_normalisation_v3.json"   # v3 stays the default


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
    print(f"{len(tests) - failed}/{len(tests)} passed")
    sys.exit(1 if failed else 0)
