import json
from pathlib import Path

BASE = Path("/storage/agrp/berkom/atlas-utilization/output/cms_datasets/runs_matched")

for label in ["DoubleMuon", "SingleMuon"]:
    index = json.loads((BASE / f"{label}_index.json").read_text())
    total_read = total_golden = total_trigger = total_gate = total_excl = 0
    for idx in index:
        meta = json.loads((BASE / label / f"job_{idx}" / "job_metadata.json").read_text())
        total_read += meta["n_read"]
        total_golden += meta["n_after_golden_json"]
        total_trigger += meta["n_after_trigger"]
        total_gate += meta["n_after_gate"]
        total_excl += meta["n_exclusive"]
    print(f"{label}: read={total_read} golden={total_golden} trigger={total_trigger} "
          f"matched_gate={total_gate} exclusive={total_excl}")
    print(f"  fractions: golden/read={total_golden/total_read:.4f} trigger/golden={total_trigger/total_golden:.4f} "
          f"gate/trigger={total_gate/total_trigger:.4f} excl/gate={total_excl/total_gate:.4f}")
