"""
Implementation task 2, Part A: analyze the committed golden JSON
(data/cms/validated_runs/Cert_271036-284044_13TeV_Legacy2016_Collisions16_JSON.txt),
computing its checksum and certified run/lumisection counts, and the
subset falling within the Run2016G/H run-number ranges quoted on portal
records 30521, 30554 and 14220. See data/cms/validated_runs/README.md.
"""
import hashlib
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
path = REPO_ROOT / "data" / "cms" / "validated_runs" / "Cert_271036-284044_13TeV_Legacy2016_Collisions16_JSON.txt"
data = json.load(open(path, encoding="utf-8"))
raw = open(path, "rb").read()
sha256 = hashlib.sha256(raw).hexdigest()

n_runs = len(data)
n_ranges = sum(len(v) for v in data.values())
n_sections = sum(hi - lo + 1 for v in data.values() for lo, hi in v)

runs_int = sorted(int(k) for k in data.keys())
print("sha256:", sha256)
print("size_bytes:", len(raw))
print("n_runs:", n_runs)
print("n_ranges:", n_ranges)
print("n_certified_lumisections:", n_sections)
print("min_run:", runs_int[0], "max_run:", runs_int[-1])

# Run2016G per record 30521's own run_numbers list
G_LO, G_HI = 278820, 280385
# Run2016H: two candidate boundaries
H_LO_ABSTRACT, H_HI = 280919, 284044   # record 14220 abstract's stated era boundary
H_LO_RECORD, _ = 281613, 284044         # record 30554's own run_numbers list minimum

def runs_in_range(lo, hi):
    return [r for r in runs_int if lo <= r <= hi]

g_runs = runs_in_range(G_LO, G_HI)
h_runs_abstract = runs_in_range(H_LO_ABSTRACT, H_HI)
h_runs_record = runs_in_range(H_LO_RECORD, H_HI)

def sections_for_runs(runs):
    return sum(hi - lo + 1 for r in runs for lo, hi in data[str(r)])

print()
print(f"Run2016G range [{G_LO},{G_HI}]: {len(g_runs)} certified runs, "
      f"{sections_for_runs(g_runs)} certified lumisections")
print(f"Run2016H range per record-14220-abstract [{H_LO_ABSTRACT},{H_HI}]: "
      f"{len(h_runs_abstract)} certified runs, {sections_for_runs(h_runs_abstract)} certified lumisections")
print(f"Run2016H range per record-30554-own-list [{H_LO_RECORD},{H_HI}]: "
      f"{len(h_runs_record)} certified runs, {sections_for_runs(h_runs_record)} certified lumisections")

out = {
    "sha256": sha256,
    "size_bytes": len(raw),
    "n_runs_total_in_json": n_runs,
    "n_ranges_total_in_json": n_ranges,
    "n_certified_lumisections_total_in_json": n_sections,
    "min_run_in_json": runs_int[0],
    "max_run_in_json": runs_int[-1],
    "run2016g_range_used": [G_LO, G_HI],
    "run2016g_certified_runs": g_runs,
    "run2016g_certified_lumisections": sections_for_runs(g_runs),
    "run2016h_range_abstract": [H_LO_ABSTRACT, H_HI],
    "run2016h_certified_runs_abstract_range": h_runs_abstract,
    "run2016h_certified_lumisections_abstract_range": sections_for_runs(h_runs_abstract),
    "run2016h_range_record30554": [H_LO_RECORD, H_HI],
    "run2016h_certified_runs_record30554_range": h_runs_record,
    "run2016h_certified_lumisections_record30554_range": sections_for_runs(h_runs_record),
}
out_path = Path(__file__).resolve().parent / "golden_json_analysis_results.json"
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(out, f, indent=2)
print(f"\nwrote {out_path}")
