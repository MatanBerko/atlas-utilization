import importlib.util
import awkward as ak
import numpy as np

spec = importlib.util.spec_from_file_location(
    "run_dataset_on_file", "studies/cms_datasets/cluster/run_dataset_on_file.py"
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

# Event 0: 2 electrons, 2 muons, 1 bjet, 2 jets = 7 objects -> truncate to 4.
#   leptons combined by pT: e(50), m(40), e(30), m(20) -> top-4 lepton priority
#   picks e(50), m(40), e(30), m(20) as the 4 highest-pT leptons... wait we
#   only keep 4 TOTAL across all types, and leptons come first in priority,
#   so if there are >=4 leptons, jets/bjets are dropped entirely for that
#   event. Here 4 leptons exist (2e+2m) so all 4 kept objects are leptons:
#   e0(50), m0(40), e1(30), m1(20); bjet and jets dropped.
electrons = ak.Array([[{"pt": 50.0}, {"pt": 30.0}], [{"pt": 25.0}]])
muons = ak.Array([[{"pt": 40.0}, {"pt": 20.0}], [{"pt": 60.0}]])
bjets = ak.Array([[{"pt": 35.0}], []])
jets = ak.Array([[{"pt": 15.0}, {"pt": 5.0}], [{"pt": 45.0}]])

top4_m, top4_e, top4_j, top4_b, n_orig = mod.build_top4_object_record(muons, electrons, jets, bjets)

print("Event 0 (7 objects -> truncate):")
print("  top4 electrons pt:", ak.to_list(top4_e.pt[0]))
print("  top4 muons pt:", ak.to_list(top4_m.pt[0]))
print("  top4 bjets pt:", ak.to_list(top4_b.pt[0]))
print("  top4 jets pt:", ak.to_list(top4_j.pt[0]))
print("  n_original_objects:", n_orig[0])
assert n_orig[0] == 7
assert ak.to_list(top4_e.pt[0]) == [50.0, 30.0]
assert ak.to_list(top4_m.pt[0]) == [40.0, 20.0]
assert ak.to_list(top4_b.pt[0]) == []
assert ak.to_list(top4_j.pt[0]) == []
print("PASS: event 0 (4 leptons dominate, jets/bjets fully dropped)")

print("\nEvent 1 (1e+1m+0b+1j = 3 objects, <=4 -> unchanged):")
print("  top4 electrons pt:", ak.to_list(top4_e.pt[1]))
print("  top4 muons pt:", ak.to_list(top4_m.pt[1]))
print("  top4 bjets pt:", ak.to_list(top4_b.pt[1]))
print("  top4 jets pt:", ak.to_list(top4_j.pt[1]))
print("  n_original_objects:", n_orig[1])
assert n_orig[1] == 3
assert ak.to_list(top4_e.pt[1]) == [25.0]
assert ak.to_list(top4_m.pt[1]) == [60.0]
assert ak.to_list(top4_b.pt[1]) == []
assert ak.to_list(top4_j.pt[1]) == [45.0]
print("PASS: event 1 (<=4 objects, unchanged)")

# Event with fewer leptons than 4: 1 electron + 0 muons + 2 bjets + 2 jets = 5 objects
electrons2 = ak.Array([[{"pt": 50.0}]])
muons2 = ak.Array([[{"pt": 999.0}]])[ak.Array([[False]])]  # typed-empty muon list
bjets2 = ak.Array([[{"pt": 40.0}, {"pt": 10.0}]])
jets2 = ak.Array([[{"pt": 30.0}, {"pt": 20.0}]])
t4m, t4e, t4j, t4b, norig = mod.build_top4_object_record(muons2, electrons2, jets2, bjets2)
print("\nEvent 2 (1e+0m+2b+2j=5 objects -> truncate, priority lepton>bjet>jet):")
print("  top4 electrons pt:", ak.to_list(t4e.pt[0]))
print("  top4 muons pt:", ak.to_list(t4m.pt[0]))
print("  top4 bjets pt:", ak.to_list(t4b.pt[0]))
print("  top4 jets pt:", ak.to_list(t4j.pt[0]))
# priority: 1 electron (kept, rank0), then both bjets (rank1,2), then leading jet pt=30 (rank3), pt=20 jet dropped (rank4, exceeds top-4)
assert ak.to_list(t4e.pt[0]) == [50.0]
assert ak.to_list(t4m.pt[0]) == []
assert ak.to_list(t4b.pt[0]) == [40.0, 10.0]
assert ak.to_list(t4j.pt[0]) == [30.0]
print("PASS: event 2 (lepton, then both bjets, then only the leading jet -- lowest-pt jet dropped)")

print("\nALL TOP-4 SMOKE TESTS PASSED")
