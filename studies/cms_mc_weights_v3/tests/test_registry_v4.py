"""Checks of the v4 registry (MC expansion, 3 Nov 2026), task A1 step 2 a-d.

Run as a script (the Mac has no pytest):  PYTHONPATH=. python studies/cms_mc_weights_v3/tests/test_registry_v4.py
Offline: uses only in-tree files (the registry, the decisions file, the saved portal records and
generator cards in sources/mcexp_20261103/). The live portal comparison is in
studies/mc_expansion_20261103/registry_v4_report.py.
"""
from __future__ import annotations

import gzip
import json
import math
import pathlib
import re
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parents[3]
STUDY = REPO / "studies" / "cms_mc_weights_v3"
V3 = json.loads((STUDY / "cms_mc_normalisation_v3.json").read_text())
V4 = json.loads((STUDY / "cms_mc_normalisation_v4.json").read_text())
DEC = json.loads((STUDY / "sources" / "v5_decisions_2026-11-03.json").read_text())
EV = STUDY / "sources" / "mcexp_20261103"

# Matan's FINAL list (task A1, 3 Nov 2026), typed independently of the decisions file:
# nano -> (mini or None = "from the record relations", sigma_eff pb, tier)
MATAN_FINAL = {
    69715: (69714, 49999.6, 1), 69717: (69716, 8403.3, 1), 69719: (69718, 3123.8, 1),
    64759: (64758, 136.02, 1), 64659: (64658, 80.95, 1), 64635: (64634, 3.3767, 1), 67841: (67840, 378.93, 1),
    72742: (72741, 7.1326, 2), 75573: (75572, 4.3108, 2), 72738: (72737, 10.161, 2), 72658: (None, 52.362, 2),
    72740: (72739, 3.7888, 2), 75567: (75566, 1.1349, 2),
    72701: (72699, 0.2158, 3), 72711: (72709, 0.1707, 3), 72761: (72759, 0.05709, 3), 75600: (75598, 0.01476, 3),
    67645: (None, 0.29534, 4), 67691: (None, 0.21176, 4), 68083: (68082, 0.4375, 4), 68045: (68044, 0.01197, 4),
    37474: (None, 1.11145, 5), 68601: (None, 0.0865272, 5), 41877: (None, 0.179508, 5), 41873: (None, 0.113859, 5),
    41914: (None, 0.162668, 5), 40095: (None, 0.00264806, 5), 37446: (None, 3.04694, 5), 68591: (None, 0.237207, 5),
    71297: (None, 0.0526848, 5), 70453: (None, 0.0334172, 5), 74684: (None, 0.0477425, 5), 37616: (None, 0.0342475, 5),
    68741: (None, 0.0026662, 5), 71227: (None, 0.00023058, 5), 70383: (None, 0.000146254, 5), 37432: (None, 0.010571, 5),
    68571: (None, 0.000822963, 5), 71295: (None, 0.000182784, 5), 70451: (None, 0.000115937, 5), 74682: (None, 0.000165637, 5),
    37604: (None, 0.00752104, 5), 68731: (None, 0.00058552, 5), 71145: (None, 0.00128772, 5), 70301: (None, 0.000816782, 5),
    74292: (None, 0.00116692, 5), 40062: (40061, 6.22392e-05, 5),
    74894: (74893, 284.53, 6), 74898: (74897, 78.019, 6), 74902: (74901, 10.593, 6), 74904: (74903, 2.5739, 6),
    74906: (74905, 1.1507, 6), 74896: (74895, 0.26658, 6), 74900: (74899, 0.0059985, 6),
}
ON_HOLD = (68325, 64873, 68206, 68185)
DELIVERED = (67801, 67993, 35669, 35631, 64895, 64839, 72676, 72752, 75589, 68187, 68073, 37728, 68847)


def rec(rid):
    with gzip.open(EV / "records" / f"{rid}.json.gz", "rt") as f:
        return json.load(f)["metadata"]


def new_records():
    return {int(r): v for r, v in V4["records"].items() if "decision_2026_11_03" in v}


# ---------------------------------------------------------------- a
def test_a_sigma_matches_matan_and_factors():
    new = new_records()
    assert len(MATAN_FINAL) == 54
    assert set(new) == set(MATAN_FINAL) | set(ON_HOLD), sorted(set(new) ^ (set(MATAN_FINAL) | set(ON_HOLD)))
    for rid, (mini, sigma, tier) in MATAN_FINAL.items():
        r = new[rid]
        assert r["cross_section_pb"] == sigma, (rid, r["cross_section_pb"], sigma)
        prod = math.prod(f["value"] for f in r["decision_2026_11_03"]["factors"])
        assert abs(prod / sigma - 1) < 1e-4, (rid, prod, sigma)
        assert r["tier"] == tier and r["in_full_run"] is True, rid
        if mini is not None:
            assert r["mini_recid"] == mini, (rid, r["mini_recid"], mini)


def test_a_mini_from_relations():
    for rid, r in new_records().items():
        nano = rec(rid)
        mini = [x["recid"] for x in nano["relations"] if x["type"] == "isParentOf"][0]
        assert r["mini_recid"] == int(mini), rid
        assert r["portal_dataset_title"] == nano["title"], rid


# ---------------------------------------------------------------- b
def portal_values():
    """(nano, mini, factor value) for every factor that is a portal generator value, + the 5396."""
    out = []
    for rid, r in new_records().items():
        for f in r["decision_2026_11_03"]["factors"]:
            if f["name"].startswith("generator cross section (portal)"):
                out.append((rid, r["mini_recid"], f["value"]))
    return out


def test_b_portal_values_equal_saved_copies():
    vals = portal_values()
    assert len(vals) == 24, len(vals)   # W 3 + dibosons 5 + tribosons 4 + ttW 1 + on-hold 4 + Z->nunu 7
    for rid, mini, v in vals:
        saved = float(rec(mini)["cross_section"]["total_value"])
        assert saved == v, (rid, mini, saved, v)
    assert float(rec(35670)["cross_section"]["total_value"]) == 5396.0
    # the W k-factor uses the three W portal values
    w = [float(rec(m)["cross_section"]["total_value"]) for m in (69714, 69716, 69718)]
    assert w == [53300.0, 8958.0, 3330.0]


# ---------------------------------------------------------------- c
def card_text(rid):
    d = EV / "cards" / str(rid)
    return "\n".join(p.read_text(errors="replace") for p in sorted(d.iterdir()) if p.is_file())


# sample -> (factor used, evidence regex in the card(s), what the evidence means)
TAU_CHECKS = {
    64635: ("BR(W -> l nu) 0.3272 (e, mu, tau)", r"define ell\+ = e\+ mu\+ ta\+[\s\S]*w\+ > ell\+ vl", "MadSpin W -> ell vl, ell = e mu ta"),
    72658: ("2 BR(W -> l nu) BR(W -> had), l = e, mu, tau", r"define ell\+ = e\+ mu\+ ta\+[\s\S]*generate p p > ell\+ vl w-", "ell = e mu ta in the matrix element"),
    37474: ("BR(W -> l nu)^2 0.10706 (with tau)", r"24:onIfMatch = 11 12[\s\S]*24:onIfMatch = 13 14[\s\S]*24:onIfMatch = 15 16", "Pythia W -> e/mu/tau nu"),
    68601: ("BR(W -> l nu)^2 0.10706 (with tau)", r"DecayMode1=10 DecayMode2=10", "JHUGen 10: W -> l nu (l = e, mu, tau)"),
    40095: ("BR(Z -> ll) 0.10099 (with tau)", r"vdecaymode\s+11\s+! 1: e, 2: mu, 3: tau, .*11: inclusive leptons", "POWHEG vdecaymode 11 = inclusive charged leptons"),
    37616: ("2 BR(Z -> ee+mumu) BR(Z -> nunu) (no tau)", r"DecayMode1=3 DecayMode2=0", "JHUGen 3: Z -> nu nu; 0: Z -> ee, mumu (no tau)"),
    68741: ("2 BR(Z -> ee+mumu) BR(Z -> nunu) (no tau)", r"DecayMode1=3 DecayMode2=0", "JHUGen 3 / 0 (no tau)"),
    71227: ("BR(H -> 4l) 2.745e-4 (with tau)", r"DecayMode1=8 DecayMode2=8", "JHUGen 8: Z -> ll (l = e, mu, tau)"),
    70383: ("BR(H -> 4l) 2.745e-4 (with tau)", r"DecayMode1=8 DecayMode2=8", "JHUGen 8 / 8"),
    37604: ("BR(Z -> ll) 0.10099 (with tau)", r"23:onIfAny = 11 13 15", "Pythia Z -> e/mu/tau"),
    68731: ("BR(Z -> ll) 0.10099 (with tau)", r"23:onIfAny = 11 13 15", "Pythia Z -> e/mu/tau"),
    40062: ("BR(Z -> ll) 0.10099 (with tau)", r"DecayMode1=8 DecayMode2=9", "JHUGen 8: Z -> ll (e, mu, tau); 9: Z -> anything"),
}
# The factor value each check expects in the registry.
TAU_FACTOR = {64635: 0.3272, 72658: 2 * 0.3272 * 0.6741, 37474: 0.3272 ** 2, 68601: 0.3272 ** 2, 40095: 0.10099,
              37616: 2 * 0.067294 * 0.2, 68741: 2 * 0.067294 * 0.2, 71227: 2.745e-4, 70383: 2.745e-4,
              37604: 0.10099, 68731: 0.10099, 40062: 0.10099}


def tau_table():
    rows = []
    new = new_records()
    for rid, (factor, rx, meaning) in TAU_CHECKS.items():
        text = card_text(rid)
        found = re.search(rx, text) is not None
        vals = [f["value"] for f in new[rid]["decision_2026_11_03"]["factors"]]
        has = any(abs(v / TAU_FACTOR[rid] - 1) < 1e-9 for v in vals)
        rows.append({"sample": rid, "card_evidence": meaning, "pattern_found": found,
                     "factor": factor, "factor_in_registry": has, "result": "OK" if found and has else "MISMATCH"})
    return rows


def test_c_tau_inclusion():
    rows = tau_table()
    bad = [r for r in rows if r["result"] != "OK"]
    assert not bad, bad
    # every new sample whose formula contains a W/Z leptonic BR or H->4l is covered
    lep = ("BR(W -> l nu", "BR(Z -> ll", "BR(Z -> ee", "BR(Z -> nunu", "H -> ZZ -> 4l", "2 x BR(W -> l nu")
    users = {rid for rid, r in new_records().items() if r["in_full_run"]
             and any(any(k in f["name"] for k in lep) for f in r["decision_2026_11_03"]["factors"])}
    assert users == set(TAU_CHECKS), sorted(users ^ set(TAU_CHECKS))
    # TTToHadronic: both W hadronic (POWHEG topdecaymode 00022), so BR(W -> had)^2 is right
    assert re.search(r"topdecaymode 00022", card_text(67841))


# ---------------------------------------------------------------- d
def test_d_no_duplicates_and_overlaps():
    ids = [int(r) for r in V4["records"]]
    assert len(ids) == len(set(ids)) == V4["n_records"] == 73
    assert set(V3["records"]) <= set(V4["records"])
    for r, v in V3["records"].items():
        assert V4["records"][r] == v, r                      # v3 entries unchanged
    full = {int(r) for r in V4["full_run_records"]}
    assert full == set(DELIVERED) | set(MATAN_FINAL)
    assert {int(r) for r in V4["not_in_full_run_records"]} == {35671, 42407} | set(ON_HOLD)
    excl = {int(r) for r in V4["deliberately_excluded_records"]["records"]}
    assert not excl & {int(r) for r in V4["records"]}
    # W+jets: pieces only, never the inclusive samples
    assert {69745, 69747} <= excl and not {69745, 69747} & full
    # tribosons: ext1 only (the small records not in the registry)
    assert not {72702, 72712, 72762, 75601} & {int(r) for r in V4["records"]}
    # dropped / deferred
    assert {35999, 35987, 35993, 64793, 64693, 68833, 74314} <= excl
    # ttbar decay split: dilepton + semileptonic (v3) + hadronic (v4) = 1.0026 of 833.9
    tot = sum(V4["records"][str(r)]["cross_section_pb"] for r in (67801, 67993, 67841)) / 833.9
    assert abs(tot - 1.0026) < 2e-4, tot
    # qq -> ZH samples use 'all but gg -> ZH' 0.7612; gg -> ZH samples 0.1227
    new = new_records()
    for rid in (41914, 74684, 74682, 74292):
        assert new[rid]["decision_2026_11_03"]["factors"][0]["value"] == 0.7612, rid
    for rid in (40095, 40062):
        assert new[rid]["decision_2026_11_03"]["factors"][0]["value"] == 0.1227, rid
    # conventions
    for r, v in V4["records"].items():
        assert v["k_factor"] == 1.0 and v["gen_filt_eff"] == 1.0 and v["sum_of_weights"] is None, r
    assert [r for r, v in new.items() if v["estimate"]] == [40062]
    assert set(V4["estimates"]) == {"40062"}


def test_registry_reproducible_and_builder_default():
    out = subprocess.run([sys.executable, str(STUDY / "build_registry_v4.py"), "--check"], capture_output=True, text=True)
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
