#!/usr/bin/env python
"""
Self-checks for the CMS MC weighting implementation (DESIGN.md "Tests").

Five groups, matching the design's own test table:

  1. ALIGNMENT PROPERTY TESTS -- random masks pushed through the whole chain
     (final-state group -> combo_row_mask -> nan_mask -> coverage-cap pick ->
     Z cut -> peak removal -> outlier split) must leave element i of every
     sibling still describing element i of the masses. Property-based over
     random masks, not fixed examples, because the entire design rests on
     this one invariant.
  2. ORPHAN-SIBLING REGRESSION -- after the real
     prune_final_states_below_min_events, zero rows survive for a removed
     final state; and the fix is data-neutral (a data-only shard prunes to
     exactly what it did before).
  3. SUMW2 READ-BACK -- TH1D, len(fSumw2) == nbins + 2, errors == sqrt(sum
     w^2), negative weights included; and an absent Sumw2 fails.
  4. REGISTRY CLOSURE -- the normalisation arithmetic closes, k and eps are
     pinned to 1.0, every record has a portal title, 37728 is present with the
     BR applied, and the committed JSON matches its generator.
  5. CAMPAIGN GUARD -- an APV/preVFP portal title is rejected; a postVFP one
     is accepted.

Plus a weighted/unweighted parity group proving the v3 histogram and
post-processing mirrors agree with the shared data-side functions whenever the
weights are all 1, i.e. that nothing about the data semantics was reinvented.

No network, no cluster, no ROOT. Prints PASS/FAIL per check and a count.

Run:  python studies/cms_mc_weights_v3/tests/test_mc_weights_v3.py
"""
from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys
import tempfile

import numpy as np

REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

from services.pipelines.post_processing_pipeline import (  # noqa: E402
    _apply_z_peak_cut,
    _find_rightmost_highest_peak,
    _split_by_first_empty_bin,
)
from services.storage.sqlite_shards import (  # noqa: E402
    SqliteArrayShardWriter,
    list_signatures,
    prune_final_states_below_min_events,
)
from studies.cms_coverage.cluster.merge_and_count import Z_PEAK_CUTOFF  # noqa: E402
from studies.cms_datasets.cluster.run_dataset_on_file import (  # noqa: E402
    MC_ACC_BIT_BY_LABEL,
    MC_ACC_BIT_ELE27_CANDIDATE,
    MC_ACC_BIT_ELE27_FIRED,
    MC_SIBLING_SUFFIXES,
    MC_WEIGHT_SUFFIX,
    mask_mc_siblings,
)
from studies.m0m1j0_cms.histograms import BIN_WIDTH_GEV, make_fixed_grid_histogram  # noqa: E402
from studies.cms_mc_weights_v3.deliver import build_mc_delivery as B  # noqa: E402
from studies.cms_mc_weights_v3.deliver.weighted_histograms import (  # noqa: E402
    fill_weighted_fixed_grid,
    negative_or_empty_bin_inventory,
    to_writable_th1d,
    verify_written_th1d,
)

import logging  # noqa: E402
LOGGER = logging.getLogger("test_mc_weights_v3")

RESULTS: list[tuple[str, bool, str]] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    RESULTS.append((name, bool(condition), detail))
    print(f"{'PASS' if condition else 'FAIL'}  {name}" + (f"  -- {detail}" if detail else ""))


# ---------------------------------------------------------------------------
# 1. alignment property tests
# ---------------------------------------------------------------------------

def test_alignment_property(n_trials: int = 200, seed: int = 20261011) -> None:
    """Every mask in the chain applied to masses and siblings together must
    preserve the pairing. The siblings here are deliberately chosen so the
    pairing is CHECKABLE: sibling value == the mass's own original index."""
    rng = np.random.default_rng(seed)
    broken = 0
    stages_exercised = {"group": 0, "combo": 0, "nan": 0, "cap": 0,
                        "z": 0, "peak": 0, "split": 0}

    for _ in range(n_trials):
        n = int(rng.integers(5, 400))
        # masses spread so the Z cut, the peak and an empty bin can all bite
        masses = rng.uniform(50.0, 900.0, size=n)
        # inject NaNs, which the funnel drops
        nan_idx = rng.choice(n, size=int(rng.integers(0, max(1, n // 10))), replace=False)
        masses[nan_idx] = np.nan
        ids = np.arange(n, dtype=np.float64)        # the identity sibling
        siblings = {
            suffix: ids.copy() if i == 0 else (ids * (i + 1))
            for i, suffix in enumerate(MC_SIBLING_SUFFIXES)
        }

        # --- stage 1: final-state group mask
        group_mask = rng.random(n) < 0.8
        masses_g = masses[group_mask]
        sib_g = mask_mc_siblings(siblings, group_mask)
        stages_exercised["group"] += 1
        if any(len(v) != len(masses_g) for v in sib_g.values()):
            broken += 1
            continue

        # --- stage 2: combo_row_mask
        combo_mask = rng.random(len(masses_g)) < 0.9
        masses_c = masses_g[combo_mask]
        sib_c = mask_mc_siblings(sib_g, combo_mask)
        stages_exercised["combo"] += 1

        # --- stage 3: nan_mask (exactly what the funnel does)
        nan_mask = ~np.isnan(masses_c)
        masses_n = masses_c[nan_mask]
        sib_n = mask_mc_siblings(sib_c, nan_mask)
        stages_exercised["nan"] += 1
        if masses_n.size == 0:
            continue
        if np.isnan(masses_n).any():
            broken += 1
            continue

        # --- stage 4: coverage-cap pick (a random index array, not a mask)
        if masses_n.size > 4:
            keep_k = int(rng.integers(1, masses_n.size))
            pick = rng.choice(masses_n.size, size=keep_k, replace=False)
            masses_p = masses_n[pick]
            sib_p = mask_mc_siblings(sib_n, pick)
            stages_exercised["cap"] += 1
        else:
            masses_p, sib_p = masses_n, sib_n

        # the pairing must still hold: sibling_0 is the original index, and
        # sibling_i == sibling_0 * (i + 1) by construction
        base = sib_p[MC_SIBLING_SUFFIXES[0]]
        for i, suffix in enumerate(MC_SIBLING_SUFFIXES):
            if not np.allclose(sib_p[suffix], base * (i + 1)):
                broken += 1
                break
        else:
            # --- stages 5-7: the builder's own lockstep post-processing
            weights = base.copy()      # weight == original index, so pairing is visible
            pp = B.postprocess_in_lockstep(masses_p, weights, "m0m1", "weighted")
            stages_exercised["z"] += 1
            if "main_masses" in pp:
                stages_exercised["peak"] += 1
                stages_exercised["split"] += 1
                mm, mw = pp["main_masses"], pp["main_weights"]
                om, ow = pp["outlier_masses"], pp["outlier_weights"]
                if len(mm) != len(mw) or len(om) != len(ow):
                    broken += 1
                    continue
                # every surviving (mass, weight) pair must be one of the input
                # pairs -- i.e. no mass acquired another entry's weight
                pairs_in = set(zip(masses_p.tolist(), weights.tolist()))
                pairs_out = set(zip(mm.tolist(), mw.tolist())) | set(
                    zip(om.tolist(), ow.tolist()))
                if not pairs_out <= pairs_in:
                    broken += 1
                    continue
                # and nothing may be lost or duplicated
                if len(mm) + len(om) > len(masses_p):
                    broken += 1
                    continue

    check(f"alignment property: {n_trials} random mask chains preserve pairing",
          broken == 0, f"{broken} broken; stages exercised={stages_exercised}")


def test_alignment_rejects_mismatch() -> None:
    """A length mismatch must be a HARD ERROR, never an unweighted fallback."""
    try:
        B.postprocess_in_lockstep(np.array([200.0, 300.0]), np.array([1.0]),
                                  "m0m1", "weighted")
    except SystemExit as exc:
        check("length mismatch is a hard error (no unweighted fallback)",
              "alignment lost" in str(exc), str(exc)[:70])
    else:
        check("length mismatch is a hard error (no unweighted fallback)", False,
              "no exception raised")


def test_event_union_ignores_ele27() -> None:
    """The build's event union is the four data flags only; the Ele27
    candidate is stored and ignored."""
    four = sum(MC_ACC_BIT_BY_LABEL.values())
    only_ele27 = np.array([MC_ACC_BIT_ELE27_CANDIDATE | MC_ACC_BIT_ELE27_FIRED])
    dm_only = np.array([MC_ACC_BIT_BY_LABEL["DoubleMuon"]])
    both = np.array([MC_ACC_BIT_BY_LABEL["MuonEG"] | MC_ACC_BIT_ELE27_CANDIDATE])
    check("event union excludes an Ele27-only event",
          B.event_union_mask(only_ele27)[0] == False,  # noqa: E712
          f"bitmask={int(only_ele27[0])}, four-bit mask={four}")
    check("event union includes a DoubleMuon event",
          B.event_union_mask(dm_only)[0] == True)  # noqa: E712
    check("event union includes an event accepted by both",
          B.event_union_mask(both)[0] == True)  # noqa: E712


# ---------------------------------------------------------------------------
# 2. orphan-sibling regression
# ---------------------------------------------------------------------------

def _build_shard(path: str, final_states: dict, with_siblings: bool) -> None:
    w = SqliteArrayShardWriter(path)
    for fs, n in final_states.items():
        base = f"job_FS_{fs}_IM_m0m1"
        w.record_final_state_count(fs, n)
        w.append_array(base, np.arange(n, dtype=np.float32))
        if with_siblings:
            for suffix in list(MC_SIBLING_SUFFIXES) + [MC_WEIGHT_SUFFIX]:
                w.append_array(base + suffix, np.ones(n, dtype=np.float32))
    w.commit()
    w.close()


def test_orphan_sibling_regression() -> None:
    small, big = "0e_2m_5j_1b", "0e_2m_1j_0b"
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        db = os.path.join(tmp, "mc.sqlite")
        _build_shard(db, {small: 10, big: 500}, with_siblings=True)
        before = set(list_signatures(db))
        removed = prune_final_states_below_min_events(db, 100)
        after = set(list_signatures(db))
        orphans = sorted(s for s in after if small in s)
        check("prune removes the below-threshold final state",
              removed == [f"_FS_{small}"], f"removed={removed}")
        check("prune leaves ZERO orphan sibling rows",
              orphans == [], f"orphans={orphans}")
        check("prune keeps every row of the surviving final state",
              len([s for s in after if big in s]) == len([s for s in before if big in s]),
              f"{len(after)} of {len(before)} signatures kept")


def test_prune_fix_is_data_neutral() -> None:
    """A data-only shard (no siblings anywhere) must prune to exactly what the
    pre-change regex produced. Checked by driving the OLD regex's own logic
    over the same inputs and comparing the surviving signature sets."""
    import re
    old_pattern = re.compile(r"(_FS_[0-9a-z_]+)_IM_([0-9a-z]+)$")
    new_pattern = B.SIG_PATTERN  # same shape; used here only as a sanity anchor
    small, big = "0e_2m_5j_1b", "0e_2m_1j_0b"
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        db = os.path.join(tmp, "data.sqlite")
        _build_shard(db, {small: 10, big: 500}, with_siblings=False)
        before = sorted(list_signatures(db))
        # what the OLD regex would have classified
        old_matched = [s for s in before if old_pattern.search(s)]
        removed = prune_final_states_below_min_events(db, 100)
        after = sorted(list_signatures(db))
        check("prune fix is data-neutral: same final state removed",
              removed == [f"_FS_{small}"], f"removed={removed}")
        check("prune fix is data-neutral: every data signature was classified "
              "by the old regex too",
              len(old_matched) == len(before),
              f"{len(old_matched)} of {len(before)}")
        check("prune fix is data-neutral: survivors are exactly the big "
              "final state's signatures",
              after == [s for s in before if big in s],
              f"after={after}")
        check("v3 builder's mass-signature regex matches a plain data signature",
              bool(new_pattern.search(f"job_FS_{big}_IM_m0m1")))
        check("v3 builder's mass-signature regex REJECTS every sibling",
              not any(new_pattern.search(f"job_FS_{big}_IM_m0m1{s}")
                      for s in list(MC_SIBLING_SUFFIXES) + [MC_WEIGHT_SUFFIX]))


# ---------------------------------------------------------------------------
# 3. Sumw2 read-back
# ---------------------------------------------------------------------------

def test_sumw2_readback() -> None:
    masses = np.array([105.0, 115.0, 125.0, 125.0, 135.0, 205.0])
    weights = np.array([2.0, -1.0, 3.0, 0.5, 0.5, 4.0])
    sum_w, sum_w2, edges = fill_weighted_fixed_grid(masses, weights)
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        path = os.path.join(tmp, "mc.root")
        import uproot
        key = "ROI_mass_m0m1_cat_0ex_2mx_1jx_0bx_width_10.0"
        with uproot.recreate(path) as f:
            f[key] = to_writable_th1d(sum_w, sum_w2, edges, key, len(masses))
        checked = verify_written_th1d(path, {key: (sum_w, sum_w2)})
        info = checked[key]
        check("Sumw2 read-back: classname is TH1D", info["classname"] == "TH1D")
        check("Sumw2 read-back: len(fSumw2) == n_bins + 2",
              info["len_fSumw2"] == info["n_bins"] + 2,
              f"{info['len_fSumw2']} vs {info['n_bins'] + 2}")
        check("Sumw2 read-back: sum of contents equals sum of weights",
              abs(info["sum_w"] - weights.sum()) < 1e-12,
              f"{info['sum_w']} vs {weights.sum()}")
        check("Sumw2 read-back: sum of w^2 matches",
              abs(info["sum_w2"] - (weights ** 2).sum()) < 1e-12)
        # the negative weight must lower the content and raise the error
        with uproot.open(path) as f:
            h = f[key]
            b = int(np.floor(115.0 / BIN_WIDTH_GEV))
            check("a negative weight lowers its bin's content",
                  abs(h.values(flow=False)[b] - (-1.0)) < 1e-12,
                  f"bin {b} content={h.values(flow=False)[b]}")
            check("a negative weight still RAISES its bin's error",
                  abs(h.errors(flow=False)[b] - 1.0) < 1e-12,
                  f"bin {b} error={h.errors(flow=False)[b]}")


def test_absent_sumw2_fails_the_build() -> None:
    """A TH1D written WITHOUT Sumw2 must fail the read-back assertion -- an
    absent Sumw2 means sqrt(content) errors, which is wrong for weighted
    contents and undefined for a negative bin."""
    import uproot
    import uproot.writing.identify as ui
    masses = np.array([125.0, 135.0])
    weights = np.array([2.0, 3.0])
    sum_w, sum_w2, edges = fill_weighted_fixed_grid(masses, weights)
    n = len(sum_w)
    data = np.zeros(n + 2, dtype=np.float64)
    data[1:-1] = sum_w
    xaxis = ui.to_TAxis("xaxis", "", n, float(edges[0]), float(edges[-1]),
                        fXbins=np.asarray(edges, dtype=np.float64))
    bad = ui.to_TH1x(fName=None, fTitle="ROI_bad", data=data, fEntries=2.0,
                     fTsumw=float(sum_w.sum()), fTsumw2=float(sum_w2.sum()),
                     fTsumwx=0.0, fTsumwx2=0.0, fSumw2=None, fXaxis=xaxis)
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        path = os.path.join(tmp, "bad.root")
        with uproot.recreate(path) as f:
            f["ROI_bad"] = bad
        try:
            verify_written_th1d(path, {"ROI_bad": (sum_w, sum_w2)})
        except AssertionError as exc:
            check("a TH1D without Sumw2 FAILS the read-back assertion", True,
                  str(exc)[:70])
        else:
            check("a TH1D without Sumw2 FAILS the read-back assertion", False,
                  "it was accepted")


def test_negative_bin_inventory() -> None:
    # bin 12 (120-130) gets +2 and -2 => content 0 but FILLED
    masses = np.array([125.0, 125.0, 205.0, 305.0])
    weights = np.array([2.0, -2.0, 1.0, 1.0])
    sum_w, sum_w2, _ = fill_weighted_fixed_grid(masses, weights)
    inv = negative_or_empty_bin_inventory(sum_w, sum_w2)
    # Bin 12 = [120,130) received +2 and -2: content 0, sum w^2 = 8, so it WAS
    # filled and still came out non-positive -- the negative-weight
    # cancellation. Bins 20 and 30 hold the two unit-weight entries. The 16
    # bins between them were never filled at all.
    check("negative-bin inventory separates a FILLED cancelling bin from the "
          "never-filled gap",
          inv["n_filled_bins_eq_zero"] == 1 and inv["n_filled_bins_le_zero"] == 1,
          f"n_filled_bins_eq_zero={inv['n_filled_bins_eq_zero']}, "
          f"n_filled_bins_le_zero={inv['n_filled_bins_le_zero']}")
    check("negative-bin inventory spans first..last FILLED bin",
          inv["first_filled_bin"] == 12 and inv["last_filled_bin"] == 30,
          f"{inv['first_filled_bin']}..{inv['last_filled_bin']}")
    check("negative-bin inventory counts every bin <= 0 in the filled range",
          inv["n_bins_le_zero_in_filled_range"] == 17
          and inv["n_bins_in_filled_range"] == 19,
          f"{inv['n_bins_le_zero_in_filled_range']} of "
          f"{inv['n_bins_in_filled_range']} bins (2 populated)")
    check("negative-bin inventory counts the never-filled gap bins",
          inv["n_bins_never_filled_in_range"] == 16,
          f"got {inv['n_bins_never_filled_in_range']}")
    check("negative-bin inventory: no bin is strictly negative here",
          inv["n_bins_lt_zero_in_filled_range"] == 0)


# ---------------------------------------------------------------------------
# 4. registry closure
# ---------------------------------------------------------------------------

def test_registry_closure() -> None:
    reg = json.loads(B.REGISTRY_PATH.read_text(encoding="utf-8"))
    records = reg["records"]
    check("registry has the 12 v2 records plus 37728",
          len(records) == 13 and "37728" in records, f"{len(records)} records")
    bad_k = [r for r, v in records.items()
             if v["k_factor"] != 1.0 or v["gen_filt_eff"] != 1.0]
    check("registry pins k_factor and gen_filt_eff to 1.0 everywhere",
          not bad_k, f"offenders={bad_k}")
    check("registry leaves sum_of_weights null everywhere (measured at build)",
          all(v["sum_of_weights"] is None for v in records.values()))
    check("registry carries a portal dataset title for every record",
          all(v.get("portal_dataset_title") for v in records.values()))
    check("registry header forbids setting k from provenance",
          "never be set from" in reg["HOW_TO_READ_cross_section_pb"].lower()
          or "NEVER be set from" in reg["HOW_TO_READ_cross_section_pb"])
    check("registry target luminosity is 16.393 fb^-1",
          reg["target_luminosity_fb"] == 16.393)

    # 37728: sigma_eff must be the reference sigma TIMES the H->4l BR
    r = records["37728"]
    prov = r["provenance"]
    expect = prov["reference_sigma_pb"] * prov["br_value"]
    check("37728 sigma_eff == reference sigma x BR(H->4l incl. tau)",
          abs(r["cross_section_pb"] - expect) < 5e-7 * max(1.0, expect),
          f"{r['cross_section_pb']} vs {prov['reference_sigma_pb']} x "
          f"{prov['br_value']} = {expect}")
    check("37728 carries its k-factor in provenance only, marked DO NOT APPLY",
          "k_factor_from_table_DO_NOT_APPLY" in prov
          and prov["k_factor_from_table_DO_NOT_APPLY"] == 1.683)

    # the normalisation arithmetic closes against a hand-computed value
    sigma_w = 1.15813237e5          # 37728 file 0, verified by the design probe
    norm = B.normalisation_factor(r, sigma_w)
    expect_norm = (r["cross_section_pb"] * 1000.0 * 1.0 * 1.0
                   * B.TARGET_LUMINOSITY_FB / sigma_w)
    check("normalisation_factor closes: sigma_eff*1000*k*eps*L/Sigma-w",
          abs(norm - expect_norm) < 1e-18 + 1e-12 * abs(expect_norm),
          f"{norm:.9e} vs {expect_norm:.9e}")

    # k != 1 must be refused outright
    tampered = dict(r)
    tampered["k_factor"] = 1.683
    try:
        B.normalisation_factor(tampered, sigma_w)
    except SystemExit as exc:
        check("a registry record with k_factor != 1.0 is refused",
              "already inside cross_section_pb" in str(exc), str(exc)[:60])
    else:
        check("a registry record with k_factor != 1.0 is refused", False,
              "it was accepted")

    # the committed JSON must match its generator
    rc = subprocess.run(
        [sys.executable, str(REPO_ROOT / "studies" / "cms_mc_weights_v3" / "build_registry.py"),
         "--check"], capture_output=True, text=True)
    check("committed registry matches build_registry.py output",
          rc.returncode == 0, (rc.stdout + rc.stderr).strip()[:90])


# ---------------------------------------------------------------------------
# 5. campaign guard
# ---------------------------------------------------------------------------

def test_campaign_guard() -> None:
    post = {"portal_dataset_title":
            "/TTTo2L2Nu_TuneCP5_13TeV-powheg-pythia8/"
            "RunIISummer20UL16NanoAODv9-106X_mcRun2_asymptotic_v17-v1/NANOAODSIM"}
    apv = {"portal_dataset_title":
           "/TTTo2L2Nu_TuneCP5_13TeV-powheg-pythia8/"
           "RunIISummer20UL16NanoAODAPVv9-106X_mcRun2_asymptotic_preVFP_v11-v1/NANOAODSIM"}
    other = {"portal_dataset_title":
             "/X/RunIISummer20UL17NanoAODv9-106X_mc2017_realistic_v9-v1/NANOAODSIM"}
    try:
        B.assert_campaign_ok("67801", post)
        ok_post = True
    except SystemExit:
        ok_post = False
    check("campaign guard ACCEPTS a UL16 postVFP title", ok_post)

    try:
        B.assert_campaign_ok("67801", apv)
    except SystemExit as exc:
        check("campaign guard REJECTS an APV/preVFP title", True, str(exc)[:70])
    else:
        check("campaign guard REJECTS an APV/preVFP title", False, "accepted")

    try:
        B.assert_campaign_ok("99999", other)
    except SystemExit as exc:
        check("campaign guard REJECTS a non-UL16-NanoAODv9 title", True, str(exc)[:60])
    else:
        check("campaign guard REJECTS a non-UL16-NanoAODv9 title", False, "accepted")

    # every committed record must pass
    reg = json.loads(B.REGISTRY_PATH.read_text(encoding="utf-8"))
    failures = []
    for rid, rec in reg["records"].items():
        try:
            B.assert_campaign_ok(rid, rec)
        except SystemExit as exc:
            failures.append((rid, str(exc)[:50]))
    check("every committed registry record passes the campaign guard",
          not failures, f"failures={failures}")


# ---------------------------------------------------------------------------
# 6. the v3 mirrors agree with the shared data-side functions
# ---------------------------------------------------------------------------

def test_mirrors_agree_with_data_side() -> None:
    rng = np.random.default_rng(7)
    masses = rng.uniform(0.0, 9999.0, size=5000)
    masses = np.concatenate([masses, np.array([10000.0, 0.0])])
    ones = np.ones_like(masses)

    data_counts, data_edges = make_fixed_grid_histogram(masses)
    sum_w, sum_w2, edges = fill_weighted_fixed_grid(masses, ones)
    check("weighted fill with unit weights == the data-side fixed-grid fill",
          np.array_equal(data_counts, sum_w) and np.array_equal(data_edges, edges),
          f"max diff {np.max(np.abs(data_counts - sum_w)):.3g}")
    check("with unit weights, sum w^2 == the counts",
          np.array_equal(sum_w2, data_counts))

    # peak finder: unweighted must reproduce the shared function exactly
    sub = masses[:400]
    check("find_peak_mass(weights=None) == the shared _find_rightmost_highest_peak",
          B.find_peak_mass(sub, None)
          == _find_rightmost_highest_peak(sub, BIN_WIDTH_GEV, LOGGER))

    # the split mask must reproduce the shared split
    main_shared, out_shared = _split_by_first_empty_bin(sub, BIN_WIDTH_GEV, LOGGER)
    m = B.main_split_mask(sub)
    check("main_split_mask reproduces the shared _split_by_first_empty_bin",
          np.array_equal(np.sort(sub[m]), np.sort(main_shared))
          and np.array_equal(np.sort(sub[~m]), np.sort(out_shared)),
          f"{m.sum()} main / {(~m).sum()} outliers vs "
          f"{len(main_shared)} / {len(out_shared)}")

    # the Z cut mask must reproduce the shared cut, for a dilepton channel
    dilep_sig = "x_FS_x_IM_m0m1"
    kept_shared = _apply_z_peak_cut(sub, dilep_sig, Z_PEAK_CUTOFF, LOGGER)
    keep = B.z_peak_keep_mask(sub, dilep_sig)
    check("z_peak_keep_mask reproduces the shared _apply_z_peak_cut (dilepton)",
          np.array_equal(np.sort(sub[keep]), np.sort(kept_shared)),
          f"{keep.sum()} kept vs {len(kept_shared)}")
    nondilep_sig = "x_FS_x_IM_m0j0"
    keep_nd = B.z_peak_keep_mask(sub, nondilep_sig)
    check("z_peak_keep_mask keeps everything for a non-dilepton channel",
          bool(keep_nd.all()), f"{keep_nd.sum()} of {len(sub)}")


def _evidence_path(filename: str) -> pathlib.Path:
    """Where to write this run's evidence JSON.

    Defaults to the study's own evidence/ directory. Set
    MCV3_EVIDENCE_DIR to send it elsewhere -- which is what a run on a
    pinned cluster checkout should do, so the checkout stays clean and
    the next `git checkout <commit>` cannot be blocked by test output."""
    import os
    base = os.environ.get("MCV3_EVIDENCE_DIR")
    out = (pathlib.Path(base) if base
           else pathlib.Path(__file__).resolve().parents[1] / "evidence")
    out.mkdir(parents=True, exist_ok=True)
    return out / filename


def main() -> int:
    print("=" * 74)
    print("CMS MC weighting v3 -- self-checks (DESIGN.md Tests)")
    print("=" * 74)
    print("\n-- 1. alignment property tests --")
    test_alignment_property()
    test_alignment_rejects_mismatch()
    test_event_union_ignores_ele27()
    print("\n-- 2. orphan-sibling regression --")
    test_orphan_sibling_regression()
    test_prune_fix_is_data_neutral()
    print("\n-- 3. Sumw2 read-back --")
    test_sumw2_readback()
    test_absent_sumw2_fails_the_build()
    test_negative_bin_inventory()
    print("\n-- 4. registry closure --")
    test_registry_closure()
    print("\n-- 5. campaign guard --")
    test_campaign_guard()
    print("\n-- 6. v3 mirrors vs the shared data-side functions --")
    test_mirrors_agree_with_data_side()

    n_pass = sum(1 for _n, ok, _d in RESULTS if ok)
    n_fail = len(RESULTS) - n_pass
    print("\n" + "=" * 74)
    print(f"{n_pass} pass, {n_fail} fail, {len(RESULTS)} checks total")
    if n_fail:
        print("\nFAILURES:")
        for name, ok, detail in RESULTS:
            if not ok:
                print(f"  - {name}: {detail}")
    print("=" * 74)

    out = _evidence_path("selfchecks_v3.json")
    out.write_text(json.dumps({
        "n_pass": n_pass, "n_fail": n_fail, "n_total": len(RESULTS),
        "checks": [{"name": n, "pass": ok, "detail": d} for n, ok, d in RESULTS],
    }, indent=2), encoding="utf-8")
    print(f"wrote {out}")
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
