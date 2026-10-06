"""
Self-checks for the histogram-name width suffix.

Maryna's decision: our histogram names must match what the main (upstream)
pipeline produces, exactly. Upstream builds the whole name as

    hist_name = f"ROI_{hist_name_base}_width_{bin_width}"

(services/pipelines/histograms_pipeline.py at upstream commit 88d7a4b --
the identical f-string at lines 343, 380, 520 and 650), with `bin_width`
taken straight from the configuration and never converted:

    bin_widths_gev = [histograms_config["bin_width_gev"]]

In the configuration that value is a FLOAT: config.yaml carries
`bin_width_gev: 10.0`, which YAML parses as a Python float, and
domain/config.py declares `bin_width_gev: float = 10.0`. So for the default
configuration upstream writes `..._width_10.0`, not `..._width_10`.

Covers:
  1. Our suffix builder vs upstream's own f-string, for several bin widths
     (10.0 as configured, plus 5.0 and 2.5 to show the rule is the same one
     and not a special case for 10).
  2. The full name for a sample signature, built by our code, equal to the
     full name upstream's own rule produces from the same parts.
  3. The default (legacy) suffix is unchanged, so pre-existing invocations
     keep producing exactly what they produced before.
  4. The suffix is derived from the bin width, not hard-coded.

Run directly:
    python studies/cms_datasets/tests/test_width_suffix.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

from studies.cms_datasets.deliver.build_dataset_delivery import (  # noqa: E402
    roi_key,
    width_suffix,
)
from studies.m0m1j0_cms.histograms import BIN_WIDTH_GEV  # noqa: E402

FAILURES = []


def check(name: str, condition: bool, detail: str = ""):
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {name}" + (f" -- {detail}" if detail and not condition else ""))
    if not condition:
        FAILURES.append(name)


# --------------------------------------------------------------------------
# Upstream's own rule, replicated from its source. Test-only.
# --------------------------------------------------------------------------

def upstream_hist_name(hist_name_base: str, bin_width) -> str:
    """Verbatim from upstream services/pipelines/histograms_pipeline.py at
    commit 88d7a4b (lines 343/380/520/650 are all this one f-string)."""
    return f"ROI_{hist_name_base}_width_{bin_width}"


def upstream_convert_to_bumpnet_name(fs_str: str, im_str: str) -> str:
    """Verbatim from upstream services/pipelines/histograms_pipeline.py
    _convert_to_bumpnet_name at commit 88d7a4b."""
    combo = im_str if im_str else "none"
    fs_particles = re.findall(r'(\d+)([emjgtb])', fs_str)
    fs_formatted = "_".join(f"{c}{p}x" for c, p in fs_particles)
    return f"mass_{combo}_cat_{fs_formatted}"


# --------------------------------------------------------------------------

def test_suffix_matches_upstream_for_several_bin_widths():
    print("\n--- 1. Our suffix vs upstream's f-string, for several bin widths ---")
    base = "mass_m0m1_cat_0ex_2mx_5jx_1bx"
    for bw in (10.0, 5.0, 2.5):
        ours = roi_key(base, bin_width=bw, upstream_width_suffix=True)
        theirs = upstream_hist_name(base, bw)
        check(f"bin width {bw!r} -> {ours}", ours == theirs, f"upstream gives {theirs}")

    check("the configured bin width is the float 10.0, as upstream holds it",
          BIN_WIDTH_GEV == 10.0 and isinstance(BIN_WIDTH_GEV, float),
          f"got {BIN_WIDTH_GEV!r} ({type(BIN_WIDTH_GEV).__name__})")
    check("with no bin width given, the configured one is used and gives _width_10.0",
          width_suffix(upstream=True) == "_width_10.0",
          f"got {width_suffix(upstream=True)!r}")

    # The rule is genuinely derived from the value, not a hard-coded string:
    # a different bin width must produce a different suffix, matching upstream.
    check("the suffix is derived from the bin width, not hard-coded",
          width_suffix(2.5, upstream=True) == "_width_2.5"
          and width_suffix(5.0, upstream=True) == "_width_5.0",
          f"got {width_suffix(2.5, upstream=True)!r} and "
          f"{width_suffix(5.0, upstream=True)!r}")

    # Integer-valued widths still carry the float formatting upstream gives
    # them, because the configuration holds them as floats.
    check("an integer-valued width still formats as upstream formats it (20.0)",
          width_suffix(20.0, upstream=True) == upstream_hist_name("x", 20.0)[len("ROI_x"):],
          f"got {width_suffix(20.0, upstream=True)!r}")


def test_full_name_matches_upstream():
    print("\n--- 2. Full name for a sample signature equals upstream's ---")
    samples = [
        ("0e_2m_5j_1b", "m0m1"),
        ("0e_1m_11j_0b", "j0j1j2j3"),
        ("1e_1m_12j_4b", "e0m0b0"),
        ("0e_2m_0j_0b", "m0m1"),
    ]
    for fs, im in samples:
        base = upstream_convert_to_bumpnet_name(fs, im)
        theirs = upstream_hist_name(base, BIN_WIDTH_GEV)
        ours = roi_key(base, upstream_width_suffix=True)
        check(f"{fs} + {im} -> {ours}", ours == theirs, f"upstream gives {theirs}")

    expected = "ROI_mass_m0m1_cat_0ex_2mx_5jx_1bx_width_10.0"
    got = roi_key(upstream_convert_to_bumpnet_name("0e_2m_5j_1b", "m0m1"),
                  upstream_width_suffix=True)
    check(f"the worked example is exactly {expected}", got == expected, f"got {got}")


def test_default_is_unchanged():
    print("\n--- 3. The default (pre-existing) suffix is unchanged ---")
    base = "mass_m0m1_cat_0ex_2mx_5jx_1bx"
    check("default suffix is still _width_10", width_suffix() == "_width_10",
          f"got {width_suffix()!r}")
    check("default full key is still the pre-existing one",
          roi_key(base) == f"ROI_{base}_width_10", f"got {roi_key(base)}")
    check("explicitly asking for the legacy form gives the same",
          roi_key(base, upstream_width_suffix=False) == f"ROI_{base}_width_10")
    check("the two forms differ only by the trailing '.0'",
          roi_key(base, upstream_width_suffix=True)
          == roi_key(base, upstream_width_suffix=False) + ".0",
          f"{roi_key(base, upstream_width_suffix=True)} vs "
          f"{roi_key(base, upstream_width_suffix=False)}")


def main():
    print("=" * 74)
    print("width-suffix task: self-checks")
    print("=" * 74)
    test_suffix_matches_upstream_for_several_bin_widths()
    test_full_name_matches_upstream()
    test_default_is_unchanged()

    print("\n" + "=" * 74)
    if FAILURES:
        print(f"{len(FAILURES)} CHECK(S) FAILED:")
        for name in FAILURES:
            print(f"  - {name}")
        sys.exit(1)
    print("ALL CHECKS PASSED")


if __name__ == "__main__":
    main()
