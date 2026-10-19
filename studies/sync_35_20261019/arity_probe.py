"""Run the CMS driver's exact call (run_dataset_on_file.py:1451) on a tiny event, with the given repo on sys.path."""
import logging, sys
sys.path.insert(0, sys.argv[1])
import awkward as ak
from services.calculations.im_calculator import IMCalculator
from services.pipelines.im_pipeline import _calculate_combination_invariant_mass
import inspect
src = open(sys.argv[1] + "/studies/cms_datasets/cluster/run_dataset_on_file.py").read().split("\n")
print("CMS call site line 1451:", src[1450].strip())
mu = ak.Array([[{"pt": 40000.0, "eta": 0.1, "phi": 0.2, "mass": 105.7}, {"pt": 30000.0, "eta": -0.3, "phi": 2.9, "mass": 105.7}]])
events = ak.zip({"Muons": mu}, depth_limit=1)
calc = IMCalculator(events=events, min_events_per_fs=1, min_k=1, max_k=4, min_n=2, max_n=4)
im_config = {"field_to_slice_by": "pt"}
res = _calculate_combination_invariant_mass(events, {"Muons": 2}, im_config, calc, logging.getLogger("x"), "0e_2m_0j_0b")
print("returns", len(res), "values:", [type(x).__name__ for x in res], "mass", res[0])
try:
    inv_mass, skip_reason = res
    print("CMS unpacking: OK")
except ValueError as e:
    print("CMS unpacking: ValueError:", e)
