import importlib.util
import awkward as ak
import numpy as np

spec = importlib.util.spec_from_file_location(
    "run_dataset_on_file", "studies/cms_datasets/cluster/run_dataset_on_file.py"
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

# 4 synthetic events for DoubleMuon-style matching (bit=1, min_matched=2, leading_pt_min=17)
muons = ak.Array([
    # event 0: 2 muons, both matchable, leading trig pt 20 -> should be accepted
    [{"pt": 20.0, "eta": 0.1, "phi": 0.1}, {"pt": 10.0, "eta": -0.3, "phi": 1.0}],
    # event 1: 2 muons but only 1 matches (2nd muon far from any trig obj) -> not accepted
    [{"pt": 20.0, "eta": 0.1, "phi": 0.1}, {"pt": 10.0, "eta": 2.0, "phi": -2.0}],
    # event 2: 2 muons matched but leading matched pt only 15 -> below 17 GeV threshold -> not accepted
    [{"pt": 15.0, "eta": 0.1, "phi": 0.1}, {"pt": 9.0, "eta": -0.3, "phi": 1.0}],
    # event 3: only 1 muon -> not accepted (needs 2)
    [{"pt": 20.0, "eta": 0.1, "phi": 0.1}],
])

trigobj = ak.Array([
    [{"pt": 20.5, "eta": 0.11, "phi": 0.11, "id": 13, "filterBits": 1},
     {"pt": 10.5, "eta": -0.29, "phi": 1.01, "id": 13, "filterBits": 1}],
    [{"pt": 20.5, "eta": 0.11, "phi": 0.11, "id": 13, "filterBits": 1}],
    [{"pt": 15.5, "eta": 0.11, "phi": 0.11, "id": 13, "filterBits": 1},
     {"pt": 9.5, "eta": -0.29, "phi": 1.01, "id": 13, "filterBits": 1}],
    [{"pt": 20.5, "eta": 0.11, "phi": 0.11, "id": 13, "filterBits": 1}],
])

accept = mod.matched_acceptance_mask(
    muons, trigobj, mod.TRIGOBJ_BIT_TRKISOVVL,
    mod.DOUBLEMUON_MATCHED_MIN_MUONS, mod.DOUBLEMUON_MATCHED_LEADING_PT_MIN_GEV,
)
print("DoubleMuon-style accept mask:", accept.tolist())
expected = [True, False, False, False]
assert accept.tolist() == expected, f"expected {expected}, got {accept.tolist()}"
print("PASS: matched_acceptance_mask DoubleMuon-style logic correct")

diag = mod.compute_matching_diagnostics(
    muons, trigobj, mod.TRIGOBJ_BIT_TRKISOVVL,
    mod.DOUBLEMUON_MATCHED_MIN_MUONS, mod.DOUBLEMUON_MATCHED_LEADING_PT_MIN_GEV,
)
print("n_trigger_fired:", diag["n_trigger_fired"])
print("n_has_required_offline_muons:", diag["n_has_required_offline_muons"])
print("n_accepted:", diag["n_accepted"])
assert diag["n_trigger_fired"] == 4
assert diag["n_has_required_offline_muons"] == 3  # events 0,1,2 have >=2 muons
assert diag["n_accepted"] == 1
print("PASS: compute_matching_diagnostics counts correct")

# SingleMuon-style: bit=2, min_matched=1, leading_pt_min=24
muons_sm = ak.Array([
    [{"pt": 30.0, "eta": 0.0, "phi": 0.0}],   # matched, pt 30 -> accept
    [{"pt": 20.0, "eta": 0.0, "phi": 0.0}],   # matched but online pt below 24 -> reject
    [{"pt": 30.0, "eta": 0.0, "phi": 0.0}],   # trig has wrong bit (8, IsoTkMu) -> reject
])
trigobj_sm = ak.Array([
    [{"pt": 30.5, "eta": 0.01, "phi": 0.01, "id": 13, "filterBits": 2}],
    [{"pt": 20.5, "eta": 0.01, "phi": 0.01, "id": 13, "filterBits": 2}],
    [{"pt": 30.5, "eta": 0.01, "phi": 0.01, "id": 13, "filterBits": 8}],
])
accept_sm = mod.matched_acceptance_mask(
    muons_sm, trigobj_sm, mod.TRIGOBJ_BIT_ISO,
    mod.SINGLEMUON_MATCHED_MIN_MUONS, mod.SINGLEMUON_MATCHED_PT_MIN_GEV,
)
print("SingleMuon-style accept mask:", accept_sm.tolist())
assert accept_sm.tolist() == [True, False, False]
print("PASS: matched_acceptance_mask SingleMuon-style logic correct (bit discrimination + pT floor)")

print("ALL SMOKE TESTS PASSED")
