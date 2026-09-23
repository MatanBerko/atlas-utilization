"""
m0m1j0 CMS histogram -- selection-variants task (supervisor request).

The supervisor asked for three variants of the V0 baseline selection, to
see the effect of individual cuts. This module is the single place that
defines what each variant changes, as a set of keyword arguments to
studies.m0m1j0_cms.selection.select_event_selection_cutflow -- every
variant is READ ONLY through this dict; no variant re-implements any
selection logic of its own. The BASELINE selection (RECIPE.md) is
unchanged: V0's entry below is exactly select_event_selection_cutflow's
own defaults, and every non-V0 variant changes exactly ONE flag relative
to V0, everything else identical -- confirmed by this module's own
self-check test at import time (see _SELF_CHECK below) and by
studies/m0m1j0_cms/tests/test_variants_synthetic.py.

  V0  baseline                    -- RECIPE.md, unchanged.
  V1  no muon isolation           -- apply_muon_iso=False. Drops
                                      Muon_pfRelIso04_all < 0.15; pt/eta/
                                      mediumId unchanged.
  V2  no jet-lepton overlap       -- apply_jet_lepton_cleaning=False. Drops
      removal                        the deltaR>=0.4 jet-lepton cleaning
                                      step entirely; pt/eta/tight-ID/b-tag
                                      split unchanged. The leading light
                                      jet can differ from V0's (a jet V0
                                      would have cleaned away can now be
                                      the leading jet, or even displace a
                                      jet that WAS the leading one), so
                                      m0m1j0 is recomputed from scratch for
                                      every event under this variant, never
                                      reweighted from V0's own histogram.
  V3  single-muon trigger         -- trigger_branches=
                                      selection.SINGLE_MUON_TRIGGER_BRANCHES
                                      (HLT_IsoMu24 OR HLT_IsoTkMu24) instead
                                      of the two double-muon DZ paths.
                                      Object selection unchanged.

IMPORTANT CAVEAT for V3 (state this in every V3 report/plot caption, not
just here): the input files for this task are DoubleMuon PRIMARY DATASET
files. A DoubleMuon file's events were recorded because SOME double-muon
(or, for a subset, also single-muon) trigger fired at data-taking time --
CMS does not re-run every possible trigger offline. So "V3 selects events
with HLT_IsoMu24 or HLT_IsoTkMu24 set in the file" does NOT mean "the
single-muon dataset's own selection" -- every V3-selected event, being
present in this file at all, ALSO fired a double-muon path (that's why it
was written to DoubleMuon in the first place; a single-muon-only trigger
firing on an event otherwise absent from DoubleMuon would simply not be in
these files to select from). V3 is therefore a cross-check on events that
fired BOTH kinds of trigger, not a true single-muon selection -- an actual
single-muon selection would require the SingleMuon primary dataset, which
is explicitly out of scope for this task.
"""
from __future__ import annotations

from typing import Dict

from studies.m0m1j0_cms import selection

VARIANT_SPECS: Dict[str, dict] = {
    "V0_baseline": dict(
        apply_muon_iso=True,
        apply_jet_lepton_cleaning=True,
        trigger_branches=selection.TRIGGER_BRANCHES,
    ),
    "V1_no_muon_iso": dict(
        apply_muon_iso=False,
        apply_jet_lepton_cleaning=True,
        trigger_branches=selection.TRIGGER_BRANCHES,
    ),
    "V2_no_jet_lepton_cleaning": dict(
        apply_muon_iso=True,
        apply_jet_lepton_cleaning=False,
        trigger_branches=selection.TRIGGER_BRANCHES,
    ),
    "V3_single_muon_trigger": dict(
        apply_muon_iso=True,
        apply_jet_lepton_cleaning=True,
        trigger_branches=selection.SINGLE_MUON_TRIGGER_BRANCHES,
    ),
}

# Short human-readable one-liners, reused verbatim in plot captions/reports
# so the wording is defined once, not retyped per script.
VARIANT_DESCRIPTIONS: Dict[str, str] = {
    "V0_baseline": "Baseline selection (RECIPE.md), unchanged.",
    "V1_no_muon_iso": "V0 without the Muon_pfRelIso04_all < 0.15 requirement.",
    "V2_no_jet_lepton_cleaning": "V0 without the deltaR<0.4 jet-lepton cleaning step.",
    "V3_single_muon_trigger": (
        "V0 but requiring HLT_IsoMu24 OR HLT_IsoTkMu24 instead of the double-muon "
        "DZ paths. CAVEAT: these are DoubleMuon primary-dataset files, so this "
        "selects events that fired BOTH a double-muon and a single-muon path -- "
        "a cross-check, not a true single-muon selection (that needs the "
        "SingleMuon primary dataset, out of scope here)."
    ),
}

VARIANT_ORDER = ("V0_baseline", "V1_no_muon_iso", "V2_no_jet_lepton_cleaning", "V3_single_muon_trigger")

# Every trigger branch any variant needs, for the per-file driver's required-
# branch read list -- the union of V0's and V3's, deduplicated, order
# preserved (V0's first, since that's the pre-existing required set).
ALL_TRIGGER_BRANCHES = tuple(
    dict.fromkeys(list(selection.TRIGGER_BRANCHES) + list(selection.SINGLE_MUON_TRIGGER_BRANCHES))
)


def run_variant(variant_key: str, events, muon_extra_branches=None) -> dict:
    """Runs studies.m0m1j0_cms.selection.select_event_selection_cutflow
    for one named variant against ALREADY-READ, already-golden-JSON-
    filtered (data) or already-read (MC) `events` -- the caller reads the
    file and applies the golden-JSON filter ONCE, then calls this once per
    variant on the SAME `events`, so all four variants are computed in one
    pass per file (never four separate file reads)."""
    if variant_key not in VARIANT_SPECS:
        raise ValueError(f"Unknown variant {variant_key!r}; known variants: {list(VARIANT_SPECS)}")
    spec = VARIANT_SPECS[variant_key]
    return selection.select_event_selection_cutflow(
        events, muon_extra_branches=muon_extra_branches, **spec
    )


def _self_check() -> None:
    """V0's spec must be EXACTLY select_event_selection_cutflow's own
    defaults (not just 'behaviourally equivalent') -- checked by introspecting
    the function's real default values via inspect.signature, not by
    hand-copying them a second time into this assertion (which could drift
    independently of the function itself and silently stop checking anything
    real). Every non-V0 variant must change EXACTLY ONE key relative to V0.
    Raises AssertionError at import time if either invariant is violated --
    a loud failure here, not a silent drift, since this module's entire
    purpose is to be the one place the BASELINE-must-not-change guarantee is
    enforced."""
    import inspect

    sig = inspect.signature(selection.select_event_selection_cutflow)
    real_defaults = {
        "apply_muon_iso": sig.parameters["apply_muon_iso"].default,
        "apply_jet_lepton_cleaning": sig.parameters["apply_jet_lepton_cleaning"].default,
        "trigger_branches": sig.parameters["trigger_branches"].default,
    }
    v0 = VARIANT_SPECS["V0_baseline"]
    if v0 != real_defaults:
        raise AssertionError(
            f"V0_baseline spec {v0} does not match select_event_selection_cutflow's "
            f"real defaults {real_defaults} -- the baseline must be defined AS those "
            f"defaults, not merely equal to them by coincidence."
        )
    for key, spec in VARIANT_SPECS.items():
        if key == "V0_baseline":
            continue
        diff_keys = [k for k in spec if spec[k] != v0[k]]
        if len(diff_keys) != 1:
            raise AssertionError(
                f"variant {key!r} differs from V0 in {len(diff_keys)} flag(s) "
                f"({diff_keys}), expected exactly 1"
            )


_self_check()
