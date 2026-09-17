"""
Statistical-model task, Part 5.3: unit tests for the unblinding gate
(`studies.hgg_cms.stats.unblind.gate.check_gate`). Uses only synthetic
plan text and injected git state -- never a real repo, never a real
data file.
"""
from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from studies.hgg_cms.stats.unblind.gate import check_gate

GOOD_HASH = "abc1234def5678900000000000000000000abcd"
PLAN_TEMPLATE = "## 5. Frozen inputs\n\n- Git commit hash (this plan, ...): `{hash}`\n"


def write_plan(directory: Path, hash_text: str) -> Path:
    p = directory / "UNBLINDING_PLAN.md"
    p.write_text(PLAN_TEMPLATE.format(hash=hash_text), encoding="utf-8")
    return p


class GateTests(unittest.TestCase):
    def test_missing_flag_refuses(self):
        with TemporaryDirectory() as d:
            plan = write_plan(Path(d), GOOD_HASH)
            r = check_gate(repo_dir=d, flag_present=False, env_value=GOOD_HASH,
                            plan_path=str(plan), git_head=GOOD_HASH, git_dirty=False)
            self.assertFalse(r.ok)
            self.assertIn("flag", r.reason)

    def test_missing_env_var_refuses(self):
        with TemporaryDirectory() as d:
            plan = write_plan(Path(d), GOOD_HASH)
            r = check_gate(repo_dir=d, flag_present=True, env_value="",
                            plan_path=str(plan), git_head=GOOD_HASH, git_dirty=False)
            self.assertFalse(r.ok)
            self.assertIn("HGG_UNBLIND_APPROVED", r.reason)

    def test_malformed_env_var_refuses(self):
        with TemporaryDirectory() as d:
            plan = write_plan(Path(d), GOOD_HASH)
            r = check_gate(repo_dir=d, flag_present=True, env_value="not-a-hash!!",
                            plan_path=str(plan), git_head=GOOD_HASH, git_dirty=False)
            self.assertFalse(r.ok)
            self.assertIn("does not look like a git commit hash", r.reason)

    def test_wrong_hash_refuses(self):
        with TemporaryDirectory() as d:
            plan = write_plan(Path(d), GOOD_HASH)
            wrong_hash = "f" * 40
            r = check_gate(repo_dir=d, flag_present=True, env_value=wrong_hash,
                            plan_path=str(plan), git_head=GOOD_HASH, git_dirty=False)
            self.assertFalse(r.ok)
            self.assertIn("does not match repository HEAD", r.reason)

    def test_dirty_repo_refuses(self):
        with TemporaryDirectory() as d:
            plan = write_plan(Path(d), GOOD_HASH)
            r = check_gate(repo_dir=d, flag_present=True, env_value=GOOD_HASH,
                            plan_path=str(plan), git_head=GOOD_HASH, git_dirty=True)
            self.assertFalse(r.ok)
            self.assertIn("dirty", r.reason)

    def test_missing_plan_file_refuses(self):
        with TemporaryDirectory() as d:
            missing_plan = Path(d) / "does_not_exist.md"
            r = check_gate(repo_dir=d, flag_present=True, env_value=GOOD_HASH,
                            plan_path=str(missing_plan), git_head=GOOD_HASH, git_dirty=False)
            self.assertFalse(r.ok)
            self.assertIn("could not find a frozen commit hash", r.reason)

    def test_unfilled_plan_placeholder_refuses(self):
        with TemporaryDirectory() as d:
            plan = write_plan(Path(d), "<FILLED IN AT FINAL COMMIT -- see STATS_REPORT.md>")
            r = check_gate(repo_dir=d, flag_present=True, env_value=GOOD_HASH,
                            plan_path=str(plan), git_head=GOOD_HASH, git_dirty=False)
            self.assertFalse(r.ok)
            self.assertIn("unfilled", r.reason)

    def test_plan_hash_mismatch_refuses(self):
        with TemporaryDirectory() as d:
            plan = write_plan(Path(d), "0" * 40)
            r = check_gate(repo_dir=d, flag_present=True, env_value=GOOD_HASH,
                            plan_path=str(plan), git_head=GOOD_HASH, git_dirty=False)
            self.assertFalse(r.ok)
            self.assertIn("frozen commit hash", r.reason)

    def test_all_conditions_met_passes(self):
        with TemporaryDirectory() as d:
            plan = write_plan(Path(d), GOOD_HASH)
            r = check_gate(repo_dir=d, flag_present=True, env_value=GOOD_HASH,
                            plan_path=str(plan), git_head=GOOD_HASH, git_dirty=False)
            self.assertTrue(r.ok)

    def test_short_hash_prefix_still_matches(self):
        with TemporaryDirectory() as d:
            plan = write_plan(Path(d), GOOD_HASH)
            short = GOOD_HASH[:10]
            r = check_gate(repo_dir=d, flag_present=True, env_value=short,
                            plan_path=str(plan), git_head=GOOD_HASH, git_dirty=False)
            self.assertTrue(r.ok)


if __name__ == "__main__":
    unittest.main()
