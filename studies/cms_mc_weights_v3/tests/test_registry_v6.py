"""Checks of the v6 registry (Nominal-6 additions, 28 Nov 2026; sources/v9_decisions_2026-11-28.json).

Run as a script (the Mac has no pytest):  PYTHONPATH=. python studies/cms_mc_weights_v3/tests/test_registry_v6.py
Offline except test_b_live (the CERN Open Data API; it FAILS if the portal is unreachable).
v6 must be v5 plus exactly: 6 new records, the 40062 value change, the new exclusions; every new/changed value PENDING.
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
V5 = json.loads((STUDY / "cms_mc_normalisation_v5.json").read_text())
V6 = json.loads((STUDY / "cms_mc_normalisation_v6.json").read_text())
N6 = REPO / "studies" / "nominal6_additions_20261127" / "evidence"

# Matan's 28 Nov list, typed independently of the decisions file: nano -> (mini, sigma pb)
PORTAL = {75561: (75560, 0.0009928), 72648: (72647, 0.09219), 71636: (71635, 0.02694), 71640: (71639, 0.02037),
          72720: (72719, 0.01370)}
B = 0.033632 + 0.033662 + 0.033696          # PDG Z -> ee, mumu, tautau (D6)
N74314 = 0.7612 * 0.02619 * (2 * B - B * B) * 0.1509
N40062 = 0.1227 * 0.02619 * (2 * B - B * B) * 0.1505
DALITZ = {37276, 37420, 68459, 68559, 69681, 69699, 74652, 74670}
NEW = set(PORTAL) | {74314}


def saved(rid):
    with gzip.open(N6 / "records" / f"{rid}.json.gz", "rt") as f:
        return json.load(f)["metadata"]


def test_a_values_and_factors():
    for rid, (mini, sigma) in PORTAL.items():
        r = V6["records"][str(rid)]
        assert r["mini_recid"] == mini and r["in_full_run"] is True, rid
        assert abs(r["cross_section_pb"] / sigma - 1) <= 1e-4, rid
        assert r["matan_hand_check"] == "PENDING" == r["decision_2026_11_28"]["matan_hand_check"], rid
        assert len(r["decision_2026_11_28"]["factors"]) == 1, rid     # no BR applied by hand (decay in the ME)
    for rid, val in ((74314, N74314), (40062, N40062)):
        r = V6["records"][str(rid)]
        d = r["decision_2026_11_28"]
        assert abs(r["cross_section_pb"] / val - 1) <= 1e-9, (rid, r["cross_section_pb"], val)
        assert abs(math.prod(f["value"] for f in d["factors"]) / r["cross_section_pb"] - 1) <= 1e-12, rid
        assert r["matan_hand_check"] == "PENDING", rid
    for r in V6["records"].values():
        for key in ("decision_2026_11_28",):
            if key in r:
                assert abs(math.prod(f["value"] for f in r[key]["factors"]) / r["cross_section_pb"] - 1) <= 1e-4


def test_a2_factors_are_the_v5_numbers():
    d = V6["records"]["74314"]["decision_2026_11_28"]["factors"]
    v5_40062 = {f["name"]: f["value"] for f in V5["records"]["40062"]["decision_2026_11_03"]["factors"]}
    v5_74292 = {f["name"]: f["value"] for f in V5["records"]["74292"]["decision_2026_11_03"]["factors"]}
    assert d[0]["value"] == v5_74292["sigma(ZH, all but gg->ZH)"] == 0.7612
    assert d[1]["value"] == v5_40062["BR(H -> ZZ)"] == 0.02619
    assert abs(v5_40062["BR(Z -> ll), l = e, mu, tau"] - B) < 1e-12
    r = V6["records"]["40062"]["decision_2026_11_28"]
    assert r["factors"][0]["value"] == v5_40062["sigma(gg->ZH)"] == 0.1227
    # the v5 value is stored rounded to 6 digits (6.22392e-05), hence 1e-5
    assert abs(r["new_over_old"] / (0.1505 / 0.10099) - 1) < 1e-5 and 1.48 < r["new_over_old"] < 1.50


def test_b_saved_portal_values():
    for rid, (mini, sigma) in PORTAL.items():
        nano = saved(rid)
        assert [x["recid"] for x in nano["relations"] if x["type"] == "isParentOf"][0] in (mini, str(mini)), rid
        xs = saved(mini)["cross_section"]
        assert abs(float(xs["total_value"]) / sigma - 1) <= 1e-4, (rid, xs)
        assert float(xs["filter_efficiency"]) == 1.0 and float(xs["matching_efficiency"]) == 1.0, (rid, xs)


def test_b_live_portal_values():
    for rid, (mini, sigma) in PORTAL.items():
        with urllib.request.urlopen(f"https://opendata.cern.ch/api/records/{mini}", timeout=60) as r:
            xs = json.load(r)["metadata"]["cross_section"]
        assert abs(float(xs["total_value"]) / sigma - 1) <= 1e-4, (rid, xs)


def test_c_tau_inclusion_and_cards():
    cards = {75561: "gridpack_cards/75561/InputCards", 72648: "gridpack_cards/72648/InputCards",
             71636: "gridpack_cards/71636/InputCards", 71640: "gridpack_cards/71640/InputCards"}
    for rid, d in cards.items():
        t = "\n".join(p.read_text() for p in sorted((N6 / d).glob("*proc_card*")))
        assert re.search(r"define l\+ = e\+ mu\+ ta\+", t) and "$ t t~" in t, rid
    t = (N6 / "wzjj" / "cards" / "72720__InputCards__WZ3lnujj_ewk_notop_proc_card.dat").read_text()
    assert re.search(r"define l\+ = e\+ mu\+ ta\+", t) and t.count("$ t t~") == 2
    assert "DecayMode1=8 DecayMode2=9 FilterNLept=4" in (N6 / "gridpack_cards" / "74314" / "JHUGen.input").read_text()
    g = json.loads((N6 / "wzjj" / "gen_check_wzjj.json").read_text())["records"]["72720"]
    assert g["n_events_with_top_in_genpart"] == 0 and g["n_events_genpart"] > 5000


def test_d_only_the_decided_changes():
    assert set(V6["records"]) == set(V5["records"]) | {str(r) for r in NEW}
    for rid, r5 in V5["records"].items():
        r6 = V6["records"][rid]
        changed = {k for k in set(r5) | set(r6) if r5.get(k) != r6.get(k)}
        if rid == "40062":
            assert changed == {"cross_section_pb", "estimate", "matan_hand_check", "decision_2026_11_28"}, changed
            assert r6["decision_2026_11_03"] == r5["decision_2026_11_03"]
        else:
            assert not changed, (rid, changed)
    assert set(V6["matan_hand_check_pending"]) == {str(r) for r in NEW} | {"40062"}
    exc = set(V6["deliberately_excluded_records"]["records"])
    assert exc == (set(V5["deliberately_excluded_records"]["records"]) - {"74314"}) | {str(r) for r in DALITZ} | {"69771"}
    assert not exc & set(V6["records"])
    full_titles = [V6["records"][r]["portal_dataset_title"].split("/")[1] for r in V6["full_run_records"]]
    assert len(full_titles) == len(set(full_titles)) and len(V6["full_run_records"]) == 77
    assert "WLLJJ_WToLNu_EWK" not in " ".join(full_titles)


def test_registry_reproducible_and_builder_default():
    for script in ("build_registry_v6.py", "build_registry_v5.py", "build_registry_v4.py"):
        out = subprocess.run([sys.executable, str(STUDY / script), "--check"], capture_output=True, text=True)
        assert out.returncode == 0, out.stdout + out.stderr
    sys.path.insert(0, str(REPO))
    from studies.cms_mc_weights_v3.deliver import build_mc_delivery as Bm
    assert Bm.REGISTRY_PATH.name == "cms_mc_normalisation_v3.json"   # v3 stays the default


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
