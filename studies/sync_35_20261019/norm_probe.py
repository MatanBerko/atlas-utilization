"""#35's compute_normalization vs the CMS builder's normalisation_factor, on the 13 registry records x 1000 random Sigma-w."""
import json, sys
import numpy as np
sys.path.insert(0, sys.argv[1])
from services.calculations.mc_weights import compute_normalization
from domain.metadata import MCDatasetMetadata
reg = json.load(open(sys.argv[1] + "/studies/cms_mc_weights_v3/cms_mc_normalisation_v3.json"))
recs = reg.get("records", reg)
rng = np.random.default_rng(1)
n = same = 0
for rid, r in recs.items():
    if not isinstance(r, dict) or "cross_section_pb" not in r or not r.get("in_full_run"):
        continue
    for sw in rng.uniform(1e3, 1e12, 1000):
        cms = float(r["cross_section_pb"]) * 1000.0 * float(r["k_factor"]) * float(r["gen_filt_eff"]) * 16.393 / float(sw)
        atl = compute_normalization(MCDatasetMetadata(dataset_number=int(rid), cross_section_pb=float(r["cross_section_pb"]), sum_of_weights=float(sw), k_factor=float(r["k_factor"]), gen_filt_eff=float(r["gen_filt_eff"])), 16.393)
        n += 1; same += (cms == atl)
print(f"records in full run: {n // 1000}; comparisons: {n}; bit-identical: {same}")
