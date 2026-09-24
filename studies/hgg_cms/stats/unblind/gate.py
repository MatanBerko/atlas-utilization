"""
Statistical-model task, Part 5: the shared unblinding gate. Both
`merge_full_range.py` and `run_unblinded_analysis.py` import
`check_gate` and refuse to do anything else until it returns
`ok=True`. This module has NO import-time side effects and never opens
a data file itself -- it only checks flags, an environment variable, a
git commit hash, and the frozen-hash line already written into
`UNBLINDING_PLAN.md`.

The gate requires ALL of the following simultaneously:
  1. `--i-have-explicit-approval-to-unblind` was passed (checked by the
     caller, passed in here as `flag_present`).
  2. The environment variable `HGG_UNBLIND_APPROVED` is set, and its
     value looks like a git commit hash.
  3. That value equals the git commit hash frozen in
     `UNBLINDING_PLAN.md`'s "Frozen inputs" section -- the approver and
     the document must be naming the SAME reviewed commit.
  4. That frozen commit is HEAD itself, or an ANCESTOR of HEAD (i.e. the
     reviewed commit has already happened; only commits after it, if
     any, are allowed). This is deliberately NOT "must equal HEAD
     exactly": a commit can never contain its own resulting hash, so
     the commit that fills in this very hash is necessarily one commit
     AFTER the commit it names -- an exact-equality check would make
     the gate permanently unpassable the moment anyone records the
     hash, which is the whole point of writing it down. Anything
     committed strictly BEFORE the frozen commit, or on an unrelated
     branch, correctly still fails this check.
  5. The repository working tree is clean (no uncommitted changes that
     could silently alter what actually runs).

Any single failure refuses, with a specific, human-readable reason (the
caller is expected to print `reason` and exit non-zero) -- this is
deliberately NOT a single boolean "did all checks pass" with no detail,
since a wrong-for-the-wrong-reason refusal is much harder to debug when
it happens for real.
"""
from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

APPROVAL_ENV_VAR = "HGG_UNBLIND_APPROVED"
APPROVAL_FLAG = "--i-have-explicit-approval-to-unblind"

_FROZEN_HASH_RE = re.compile(
    r"Git commit hash.*?:\s*`([0-9a-f]{7,40}|<FILLED IN AT FINAL COMMIT[^`]*>)`",
    re.IGNORECASE | re.DOTALL)


@dataclass
class GateResult:
    ok: bool
    reason: str


def _git_head(repo_dir: Path) -> str:
    return subprocess.run(["git", "-C", str(repo_dir), "rev-parse", "HEAD"],
                           capture_output=True, text=True, check=True).stdout.strip()


def _git_dirty(repo_dir: Path) -> bool:
    out = subprocess.run(["git", "-C", str(repo_dir), "status", "--porcelain"],
                          capture_output=True, text=True, check=True).stdout
    return len(out.strip()) > 0


def _git_is_ancestor(repo_dir: Path, ancestor: str, descendant: str) -> bool:
    """True if `ancestor` is `descendant` itself, or a real ancestor of
    it in the commit graph."""
    if descendant.startswith(ancestor) or ancestor.startswith(descendant):
        return True
    result = subprocess.run(["git", "-C", str(repo_dir), "merge-base", "--is-ancestor", ancestor, descendant])
    return result.returncode == 0


def _plan_frozen_hash(plan_path: Path) -> str:
    if not plan_path.exists():
        return ""
    text = plan_path.read_text(encoding="utf-8")
    m = _FROZEN_HASH_RE.search(text)
    return m.group(1) if m else ""


def check_gate(repo_dir: str, flag_present: bool, env_value: str,
               plan_path: str = None, git_head: str = None, git_dirty: bool = None,
               frozen_is_ancestor_of_head: bool = None) -> GateResult:
    """Pure-ish gate check. `git_head`/`git_dirty`/`plan_path`/
    `frozen_is_ancestor_of_head` are injectable so tests can exercise
    every branch with synthetic values, never a real repo or real data
    file."""
    repo = Path(repo_dir)
    plan = Path(plan_path) if plan_path is not None else repo / "studies" / "hgg_cms" / "UNBLINDING_PLAN.md"

    if not flag_present:
        return GateResult(False, f"missing required flag {APPROVAL_FLAG}")

    if not env_value:
        return GateResult(False, f"environment variable {APPROVAL_ENV_VAR} is not set (or empty)")

    env_value = env_value.strip()
    if not re.fullmatch(r"[0-9a-f]{7,40}", env_value, re.IGNORECASE):
        return GateResult(False, f"{APPROVAL_ENV_VAR} does not look like a git commit hash: {env_value!r}")

    plan_hash = _plan_frozen_hash(plan)
    if not plan_hash:
        return GateResult(False, f"could not find a frozen commit hash line in {plan}")
    if plan_hash.startswith("<FILLED IN"):
        return GateResult(False, f"{plan} still has an unfilled '<FILLED IN AT FINAL COMMIT>' placeholder "
                                  f"for its frozen commit hash -- the plan was never finalized")

    if not env_value.startswith(plan_hash) and not plan_hash.startswith(env_value):
        return GateResult(False, f"{APPROVAL_ENV_VAR}={env_value!r} does not match UNBLINDING_PLAN.md's "
                                  f"frozen commit hash ({plan_hash!r}) -- the approver and the plan must "
                                  f"name the same reviewed commit")

    head = git_head if git_head is not None else _git_head(repo)
    is_ancestor = (frozen_is_ancestor_of_head if frozen_is_ancestor_of_head is not None
                   else _git_is_ancestor(repo, plan_hash, head))
    if not is_ancestor:
        return GateResult(False, f"the frozen commit ({plan_hash!r}) is not HEAD ({head!r}) and not an "
                                  f"ancestor of it -- refusing to run against an unreviewed or unrelated state")

    dirty = git_dirty if git_dirty is not None else _git_dirty(repo)
    if dirty:
        return GateResult(False, "repository working tree is dirty -- refusing to run against uncommitted changes")

    return GateResult(True, "all checks passed")
