"""
Added 18 Sep 2026, after a real cluster submission of
`pbs_hgg_bias_array.sh` was rejected outright ("Job violates queue
and/or server resource limits") because it had no `-l io=...` resource
request -- see `studies/hgg_cms/cluster/FULL_RUN_README.md`'s "Every PBS
job must request -l io=<value>" section for the full story. This
scheduler rejects ANY job missing that request, regardless of its other
resource requests, so every PBS script this project writes must have
one. This test enforces that going forward, over every PBS script under
`studies/hgg_cms/` (present or future), not just the one that actually
failed.
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
STUDIES_HGG_CMS = REPO_ROOT / "studies" / "hgg_cms"

# A PBS script in this repo is any file matching pbs_*.sh under
# studies/hgg_cms/ -- the naming convention every existing one already
# follows (pbs_hgg_d3_data.sh, pbs_hgg_zee_array.sh, pbs_hgg_bias_array.sh, ...).
PBS_IO_LINE_RE = re.compile(r"^\s*#PBS\s+-l\s+io\s*=\s*\S+", re.MULTILINE)


def discover_pbs_scripts() -> list:
    return sorted(STUDIES_HGG_CMS.glob("**/pbs_*.sh"))


class PbsIoResourceRequestTests(unittest.TestCase):
    def test_at_least_one_pbs_script_is_discovered(self):
        # A guard against this test silently passing if the glob pattern
        # or directory ever stops matching anything real.
        scripts = discover_pbs_scripts()
        self.assertGreater(len(scripts), 0, "no pbs_*.sh files found under studies/hgg_cms/ -- "
                                             "check PBS_IO_LINE_RE / discover_pbs_scripts' glob")

    def test_every_pbs_script_requests_io(self):
        scripts = discover_pbs_scripts()
        missing = []
        for script in scripts:
            text = script.read_text(encoding="utf-8")
            if not PBS_IO_LINE_RE.search(text):
                missing.append(str(script.relative_to(REPO_ROOT)))
        self.assertEqual(
            missing, [],
            "these PBS scripts have no '#PBS -l io=<value>' line -- this cluster's scheduler "
            "rejects any job missing one at submission time, regardless of its other resource "
            "requests (see studies/hgg_cms/cluster/FULL_RUN_README.md): " + ", ".join(missing)
        )


if __name__ == "__main__":
    unittest.main()
