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

FROZEN_HASH = "abc1234def5678900000000000000000000abcd"
LATER_HASH = "1111111111111111111111111111111111ffff"
UNRELATED_HASH = "f" * 40
PLAN_TEMPLATE = "## 5. Frozen inputs\n\n- Git commit hash (this plan, ...): `{hash}`\n"


def write_plan(directory: Path, hash_text: str) -> Path:
    p = directory / "UNBLINDING_PLAN.md"
    p.write_text(PLAN_TEMPLATE.format(hash=hash_text), encoding="utf-8")
    return p


class GateTests(unittest.TestCase):
    def test_missing_flag_refuses(self):
        with TemporaryDirectory() as d:
            plan = write_plan(Path(d), FROZEN_HASH)
            r = check_gate(repo_dir=d, flag_present=False, env_value=FROZEN_HASH,
                            plan_path=str(plan), git_head=FROZEN_HASH, git_dirty=False,
                            frozen_is_ancestor_of_head=True)
            self.assertFalse(r.ok)
            self.assertIn("flag", r.reason)

    def test_missing_env_var_refuses(self):
        with TemporaryDirectory() as d:
            plan = write_plan(Path(d), FROZEN_HASH)
            r = check_gate(repo_dir=d, flag_present=True, env_value="",
                            plan_path=str(plan), git_head=FROZEN_HASH, git_dirty=False,
                            frozen_is_ancestor_of_head=True)
            self.assertFalse(r.ok)
            self.assertIn("HGG_UNBLIND_APPROVED", r.reason)

    def test_malformed_env_var_refuses(self):
        with TemporaryDirectory() as d:
            plan = write_plan(Path(d), FROZEN_HASH)
            r = check_gate(repo_dir=d, flag_present=True, env_value="not-a-hash!!",
                            plan_path=str(plan), git_head=FROZEN_HASH, git_dirty=False,
                            frozen_is_ancestor_of_head=True)
            self.assertFalse(r.ok)
            self.assertIn("does not look like a git commit hash", r.reason)

    def test_env_var_not_matching_plan_hash_refuses(self):
        with TemporaryDirectory() as d:
            plan = write_plan(Path(d), FROZEN_HASH)
            r = check_gate(repo_dir=d, flag_present=True, env_value=UNRELATED_HASH,
                            plan_path=str(plan), git_head=UNRELATED_HASH, git_dirty=False,
                            frozen_is_ancestor_of_head=True)
            self.assertFalse(r.ok)
            self.assertIn("does not match UNBLINDING_PLAN.md's frozen commit hash", r.reason)

    def test_frozen_commit_not_ancestor_of_head_refuses(self):
        with TemporaryDirectory() as d:
            plan = write_plan(Path(d), FROZEN_HASH)
            r = check_gate(repo_dir=d, flag_present=True, env_value=FROZEN_HASH,
                            plan_path=str(plan), git_head=UNRELATED_HASH, git_dirty=False,
                            frozen_is_ancestor_of_head=False)
            self.assertFalse(r.ok)
            self.assertIn("not an", r.reason)

    def test_dirty_repo_refuses(self):
        with TemporaryDirectory() as d:
            plan = write_plan(Path(d), FROZEN_HASH)
            r = check_gate(repo_dir=d, flag_present=True, env_value=FROZEN_HASH,
                            plan_path=str(plan), git_head=FROZEN_HASH, git_dirty=True,
                            frozen_is_ancestor_of_head=True)
            self.assertFalse(r.ok)
            self.assertIn("dirty", r.reason)

    def test_missing_plan_file_refuses(self):
        with TemporaryDirectory() as d:
            missing_plan = Path(d) / "does_not_exist.md"
            r = check_gate(repo_dir=d, flag_present=True, env_value=FROZEN_HASH,
                            plan_path=str(missing_plan), git_head=FROZEN_HASH, git_dirty=False,
                            frozen_is_ancestor_of_head=True)
            self.assertFalse(r.ok)
            self.assertIn("could not find a frozen commit hash", r.reason)

    def test_unfilled_plan_placeholder_refuses(self):
        with TemporaryDirectory() as d:
            plan = write_plan(Path(d), "<FILLED IN AT FINAL COMMIT -- see STATS_REPORT.md>")
            r = check_gate(repo_dir=d, flag_present=True, env_value=FROZEN_HASH,
                            plan_path=str(plan), git_head=FROZEN_HASH, git_dirty=False,
                            frozen_is_ancestor_of_head=True)
            self.assertFalse(r.ok)
            self.assertIn("unfilled", r.reason)

    def test_exact_match_at_frozen_commit_passes(self):
        """The simple, common case: HEAD IS the frozen commit."""
        with TemporaryDirectory() as d:
            plan = write_plan(Path(d), FROZEN_HASH)
            r = check_gate(repo_dir=d, flag_present=True, env_value=FROZEN_HASH,
                            plan_path=str(plan), git_head=FROZEN_HASH, git_dirty=False,
                            frozen_is_ancestor_of_head=True)
            self.assertTrue(r.ok)

    def test_trailing_docs_only_commit_after_frozen_commit_passes(self):
        """The real scenario this task hit: the commit that FILLS IN the
        frozen hash is necessarily one commit AFTER the commit it names
        (a commit cannot contain its own resulting hash), so HEAD !=
        the frozen hash even though the frozen hash is exactly correct
        and reviewed. This must still pass -- `frozen_is_ancestor_of_head`
        models "HEAD is a descendant of the frozen commit"."""
        with TemporaryDirectory() as d:
            plan = write_plan(Path(d), FROZEN_HASH)
            r = check_gate(repo_dir=d, flag_present=True, env_value=FROZEN_HASH,
                            plan_path=str(plan), git_head=LATER_HASH, git_dirty=False,
                            frozen_is_ancestor_of_head=True)
            self.assertTrue(r.ok)

    def test_short_hash_prefix_still_matches(self):
        with TemporaryDirectory() as d:
            plan = write_plan(Path(d), FROZEN_HASH)
            short = FROZEN_HASH[:10]
            r = check_gate(repo_dir=d, flag_present=True, env_value=short,
                            plan_path=str(plan), git_head=FROZEN_HASH, git_dirty=False,
                            frozen_is_ancestor_of_head=True)
            self.assertTrue(r.ok)


if __name__ == "__main__":
    unittest.main()
