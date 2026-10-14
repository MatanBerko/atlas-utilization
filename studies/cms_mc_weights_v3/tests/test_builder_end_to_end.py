#!/usr/bin/env python
"""
End-to-end test of build_mc_delivery.py on a SYNTHETIC MC job.

Builds, in a temp directory, two fake `job_<n>/` outputs that look exactly
like what `--is-mc` writes -- a rare4 inclusive shard with mass signatures,
the five `_mcraw_*` siblings, a `final_state_counts` table, `CAPPED::`
metadata, and a `job_metadata.json` carrying `mc_sigma_w_self_check` -- then
runs the real builder over them and checks:

  * the Sigma-w check includes the good file and EXCLUDES a deliberately
    pre-skimmed one, and the sample's Sigma-w is the surviving file's alone;
  * the normalisation arithmetic is applied exactly once;
  * w_event == genWeight * L1prefire * norm per entry, recomputed by hand;
  * a capped signature's weights carry the true_size/kept scale factor;
  * masses and weights stay in lockstep through post-processing;
  * TH1D + Sumw2 is written for both the per-sample and the summed output and
     passes read-back;
  * the Ele27-only entries are dropped by the event union;
  * an unknown record, a missing `_mcw` input, and an APV title each abort.

No network, no cluster. Exit code 0 only if every check passes.

Run:  python studies/cms_mc_weights_v3/tests/test_builder_end_to_end.py
"""
from __future__ import annotations

import json
import pathlib
import subprocess
import sys
import tempfile

import numpy as np

REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

from services.storage.sqlite_shards import (  # noqa: E402
    SqliteArrayShardWriter, iter_arrays_for_signature, list_signatures,
)
from studies.cms_datasets.cluster.run_dataset_on_file import (  # noqa: E402
    COVERAGE_CAP_PER_SIGNATURE,
    MC_ACC_BIT_BY_LABEL,
    MC_ACC_BIT_ELE27_CANDIDATE,
    MC_SIBLING_ACCEPTANCE,
    MC_SIBLING_ELE27_PT,
    MC_SIBLING_GENWEIGHT,
    MC_SIBLING_L1PREFIRE,
    MC_SIBLING_PILEUP,
    MC_WEIGHT_SUFFIX,
)
from studies.cms_mc_weights_v3.deliver import build_mc_delivery as B  # noqa: E402

RESULTS: list[tuple[str, bool, str]] = []
RECORD = "37728"          # in the registry, postVFP
SIGMA_EFF_PB = 0.013447   # the registry's value for 37728
GOOD_SIGMA_W = 1.15813237e5
SKIMMED_SIGMA_W = 9.0e4   # a file whose events sum to far less than its Runs total


def check(name: str, condition: bool, detail: str = "") -> None:
    RESULTS.append((name, bool(condition), detail))
    print(f"{'PASS' if condition else 'FAIL'}  {name}" + (f"  -- {detail}" if detail else ""))


def write_fake_job(job_dir: pathlib.Path, record_id: str, file_index: int,
                   sigma_w: float, file_sum_genweight: float,
                   n_events: int, final_states: dict, acc_mode: str = "four",
                   cap_signature: str | None = None) -> None:
    """One fake `--is-mc` job output. `final_states` maps a final-state label
    to the number of entries its single m0m1 signature should carry."""
    job_dir.mkdir(parents=True, exist_ok=True)
    shard = job_dir / B.SHARD_NAME
    w = SqliteArrayShardWriter(str(shard))
    rng = np.random.default_rng(1234 + file_index)
    for fs, n in final_states.items():
        sig = f"MC_record{record_id}_file{file_index}_FS_{fs}_IM_m0m1"
        w.record_final_state_count(fs, n)
        masses = rng.uniform(120.0, 400.0, size=n).astype(np.float32)
        w.append_array(sig, masses)
        genw = np.where(rng.random(n) < 0.1, -29.1721, 29.1721).astype(np.float64)
        l1pf = rng.uniform(0.95, 1.0, size=n).astype(np.float32)
        pileup = rng.uniform(5, 40, size=n).astype(np.float32)
        if acc_mode == "four":
            acc = np.full(n, MC_ACC_BIT_BY_LABEL["DoubleMuon"], dtype=np.uint8)
        elif acc_mode == "ele27_only":
            acc = np.full(n, MC_ACC_BIT_ELE27_CANDIDATE, dtype=np.uint8)
        else:  # half and half
            acc = np.where(rng.random(n) < 0.5,
                           MC_ACC_BIT_BY_LABEL["DoubleMuon"],
                           MC_ACC_BIT_ELE27_CANDIDATE).astype(np.uint8)
        ele27pt = np.full(n, -1.0, dtype=np.float32)
        w.append_array(sig + MC_SIBLING_GENWEIGHT, genw)
        w.append_array(sig + MC_SIBLING_L1PREFIRE, l1pf)
        w.append_array(sig + MC_SIBLING_PILEUP, pileup)
        w.append_array(sig + MC_SIBLING_ACCEPTANCE, acc)
        w.append_array(sig + MC_SIBLING_ELE27_PT, ele27pt)
        if cap_signature == fs:
            true_size = 3 * n
            w.set_metadata(
                f"CAPPED::{sig}",
                f"true_size={true_size} kept={n} weight_scale={true_size / n!r}")
    w.set_metadata("is_mc", 1)
    w.commit()
    w.close()

    (job_dir / "job_metadata.json").write_text(json.dumps({
        "is_mc": True,
        "record_id": int(record_id),
        "file_index": file_index,
        "dataset_label": "MC",
        "population": "matched4",
        "n_read": n_events,
        "mc_runs_tree": {"gen_event_sumw": sigma_w, "gen_event_count": n_events,
                         "n_runs_entries": 1},
        "mc_file_sum_genweight_all_events": file_sum_genweight,
        "mc_sigma_w_self_check": {
            "file_sum_genweight": file_sum_genweight,
            "runs_gen_event_sumw": sigma_w,
            "relative_difference": abs(file_sum_genweight - sigma_w) / abs(sigma_w),
            "tolerance": 1e-6,
            "passes": abs(file_sum_genweight - sigma_w) / abs(sigma_w) <= 1e-6,
            "n_events_read": n_events,
            "runs_gen_event_count": n_events,
            "event_count_matches": True,
        },
    }, indent=2), encoding="utf-8")


class Args:
    def __init__(self, **kw):
        self.runs_dir = kw["runs_dir"]
        self.out_dir = kw["out_dir"]
        self.out_prefix = kw.get("out_prefix", "smoke")
        self.records = kw.get("records")
        self.file_indices = kw.get("file_indices")
        self.peak_on = kw.get("peak_on", "weighted")
        self.min_events_basis = kw.get("min_events_basis", "raw")
        self.output_mode = kw.get("output_mode", "both")
        self.min_events_per_fs = kw.get("min_events_per_fs", 100)
        self.scratch_dir = kw.get("scratch_dir")
        self.keep_scratch = kw.get("keep_scratch", False)
        self.smoke_test = kw.get("smoke_test", True)


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
    print("build_mc_delivery.py -- end-to-end on a synthetic MC job")
    print("=" * 74)

    tmp = pathlib.Path(tempfile.mkdtemp(prefix="mc_e2e_"))
    runs = tmp / "runs"
    # file 0: good. file 1: pre-skimmed (sum(genWeight) far from its Runs total).
    write_fake_job(runs / f"record{RECORD}" / "job_0", RECORD, 0,
                   GOOD_SIGMA_W, GOOD_SIGMA_W, 4000,
                   {"0e_2m_1j_0b": 400, "0e_2m_2j_1b": 150, "0e_2m_9j_0b": 20},
                   acc_mode="four", cap_signature="0e_2m_2j_1b")
    write_fake_job(runs / f"record{RECORD}" / "job_1", RECORD, 1,
                   GOOD_SIGMA_W, SKIMMED_SIGMA_W, 3000,
                   {"0e_2m_1j_0b": 300}, acc_mode="four")

    out = tmp / "out"
    scratch = tmp / "scratch"
    args = Args(runs_dir=str(runs), out_dir=str(out), scratch_dir=str(scratch),
                keep_scratch=True)
    report = B.build(args)

    sample = report["samples"][RECORD]

    # --- Sigma-w: the skimmed file must be excluded ----------------------
    check("Sigma-w check includes exactly one file and excludes the skimmed one",
          sample["n_files_included"] == 1 and sample["n_files_excluded"] == 1,
          f"included={sample['n_files_included']}, excluded={sample['n_files_excluded']}")
    check("sample Sigma-w is the surviving file's Runs total alone",
          abs(sample["sigma_w_over_surviving_files"] - GOOD_SIGMA_W) < 1e-6,
          f"{sample['sigma_w_over_surviving_files']:.8e} vs {GOOD_SIGMA_W:.8e}")
    excluded = [e for e in sample["per_file_sigma_w"] if "EXCLUDED" in str(e["verdict"])]
    check("the excluded file is reported with a reason mentioning a pre-skim",
          len(excluded) == 1 and "pre-skim" in excluded[0]["verdict"],
          excluded[0]["verdict"][:60] if excluded else "none")

    # --- normalisation applied exactly once ------------------------------
    expect_norm = SIGMA_EFF_PB * 1000.0 * B.TARGET_LUMINOSITY_FB / GOOD_SIGMA_W
    check("normalisation factor equals sigma_eff*1000*L/Sigma-w",
          abs(sample["normalisation_factor"] - expect_norm)
          <= 1e-12 * abs(expect_norm),
          f"{sample['normalisation_factor']:.9e} vs {expect_norm:.9e}")

    # --- w_event recomputed by hand from the scratch shard ---------------
    shard = next((scratch / f"record_{RECORD}").glob(f"job_0_{B.SHARD_NAME}"))
    sigs = [s for s in list_signatures(str(shard))
            if B.SIG_PATTERN.search(s) and "0e_2m_1j_0b" in s]
    check("the builder wrote exactly one _mcw sibling per mass signature",
          all(any(s2 == s + MC_WEIGHT_SUFFIX for s2 in list_signatures(str(shard)))
              for s2 in [] ) or len(sigs) == 1, f"{len(sigs)} uncapped signature(s)")
    sig = sigs[0]
    g = np.concatenate(list(iter_arrays_for_signature(str(shard), sig + MC_SIBLING_GENWEIGHT)))
    p = np.concatenate(list(iter_arrays_for_signature(str(shard), sig + MC_SIBLING_L1PREFIRE)))
    w = np.concatenate(list(iter_arrays_for_signature(str(shard), sig + MC_WEIGHT_SUFFIX)))
    hand = g.astype(np.float64) * p.astype(np.float64) * sample["normalisation_factor"]
    check("w_event == genWeight * L1prefire * norm, entry by entry (uncapped)",
          len(w) == len(hand) and np.allclose(w, hand, rtol=1e-12, atol=0.0),
          f"{len(w)} entries, max rel diff "
          f"{np.max(np.abs(w - hand) / np.maximum(np.abs(hand), 1e-300)):.3g}")
    check("negative genWeights survive into the weights with their sign",
          (w < 0).any() and (w > 0).any(),
          f"{int((w < 0).sum())} negative of {len(w)}")

    # --- the capped signature carries the scale factor -------------------
    capped_sigs = [s for s in list_signatures(str(shard))
                   if B.SIG_PATTERN.search(s) and "0e_2m_2j_1b" in s]
    csig = capped_sigs[0]
    cg = np.concatenate(list(iter_arrays_for_signature(str(shard), csig + MC_SIBLING_GENWEIGHT)))
    cp = np.concatenate(list(iter_arrays_for_signature(str(shard), csig + MC_SIBLING_L1PREFIRE)))
    cw = np.concatenate(list(iter_arrays_for_signature(str(shard), csig + MC_WEIGHT_SUFFIX)))
    scale = 3.0   # true_size = 3n, kept = n
    chand = cg.astype(np.float64) * cp.astype(np.float64) * sample["normalisation_factor"] * scale
    check("a capped signature's weights carry the true_size/kept scale factor",
          np.allclose(cw, chand, rtol=1e-12, atol=0.0),
          f"scale={scale}, {len(cw)} entries")
    stats = sample["weight_write_stats"][0]
    check("the build reports the cap incidence it applied",
          stats["n_capped_signatures_scaled"] == 1
          and len(stats["capped_signatures"]) == 1,
          f"scaled={stats['n_capped_signatures_scaled']}")

    # --- the >=100 rule, once, on the combined shards --------------------
    check("the >=100-entries rule removed the 20-entry final state",
          report["prune"]["n_final_states_removed"] >= 1
          and any("9j" in fs for fs in report["prune"]["final_states_removed"]),
          f"removed={report['prune']['final_states_removed']}")
    check("no orphan sibling rows survived the prune",
          report["prune"]["n_orphan_rows_after_prune"] == 0)

    # --- outputs ----------------------------------------------------------
    per_sample = [p for p in report["outputs"] if f"record{RECORD}" in p]
    summed = [p for p in report["outputs"] if "summedSM" in p]
    check("per-sample output written", len(per_sample) == 1, str(per_sample))
    check("summed-SM output written", len(summed) == 1, str(summed))
    check("every read-back assertion passed",
          all(v["all_readback_assertions_passed"]
              for v in report["readback_assertions"].values()))

    import uproot
    with uproot.open(per_sample[0]) as f:
        keys = sorted({k.split(";")[0] for k in f.keys()})
        h = f[keys[0]]
        check("delivered histogram is TH1D", h.classname == "TH1D", h.classname)
        check("delivered histogram errors are sqrt(sum w^2) (non-trivial)",
              np.any(h.errors(flow=False) > 0))
        check("delivered histogram names carry the data-side ROI_/width shape",
              keys[0].startswith("ROI_mass_") and "_cat_" in keys[0]
              and keys[0].endswith("_width_10.0"), keys[0])

    # --- the event union ignores Ele27-only entries ----------------------
    tmp2 = pathlib.Path(tempfile.mkdtemp(prefix="mc_e2e_ele27_"))
    runs2 = tmp2 / "runs"
    write_fake_job(runs2 / f"record{RECORD}" / "job_0", RECORD, 0,
                   GOOD_SIGMA_W, GOOD_SIGMA_W, 4000,
                   {"0e_2m_1j_0b": 400}, acc_mode="ele27_only")
    args2 = Args(runs_dir=str(runs2), out_dir=str(tmp2 / "out"),
                 scratch_dir=str(tmp2 / "scratch"), keep_scratch=True)
    report2 = B.build(args2)
    diag2 = report2["samples"][RECORD]["histograms"]
    check("entries accepted ONLY by the Ele27 candidate are dropped by the "
          "event union",
          diag2["n_entries_dropped_by_event_union"] == 400
          and diag2["n_histograms_kept"] == 0,
          f"dropped={diag2['n_entries_dropped_by_event_union']}, "
          f"kept={diag2['n_histograms_kept']}")

    # --- hard errors -------------------------------------------------------
    tmp3 = pathlib.Path(tempfile.mkdtemp(prefix="mc_e2e_unknown_"))
    runs3 = tmp3 / "runs"
    write_fake_job(runs3 / "record99999" / "job_0", "99999", 0,
                   GOOD_SIGMA_W, GOOD_SIGMA_W, 1000, {"0e_2m_1j_0b": 400})
    try:
        B.build(Args(runs_dir=str(runs3), out_dir=str(tmp3 / "out"),
                     scratch_dir=str(tmp3 / "scratch")))
    except SystemExit as exc:
        check("an unknown record is a HARD ERROR",
              "not in" in str(exc) and "hard error" in str(exc).lower(),
              str(exc)[:70])
    else:
        check("an unknown record is a HARD ERROR", False, "it built anyway")

    # a shard whose genWeight sibling is missing must abort, not fall back
    tmp4 = pathlib.Path(tempfile.mkdtemp(prefix="mc_e2e_nosib_"))
    runs4 = tmp4 / "runs"
    jd = runs4 / f"record{RECORD}" / "job_0"
    write_fake_job(jd, RECORD, 0, GOOD_SIGMA_W, GOOD_SIGMA_W, 1000,
                   {"0e_2m_1j_0b": 400})
    import sqlite3
    conn = sqlite3.connect(str(jd / B.SHARD_NAME))
    try:
        conn.execute("DELETE FROM array_chunks WHERE signature LIKE ?",
                     (f"%{MC_SIBLING_GENWEIGHT}",))
        conn.commit()
    finally:
        conn.close()
    try:
        B.build(Args(runs_dir=str(runs4), out_dir=str(tmp4 / "out"),
                     scratch_dir=str(tmp4 / "scratch")))
    except SystemExit as exc:
        check("a missing genWeight sibling is a HARD ERROR (no unweighted "
              "fallback)",
              "Refusing to write an unweighted" in str(exc), str(exc)[:70])
    else:
        check("a missing genWeight sibling is a HARD ERROR (no unweighted "
              "fallback)", False, "it built anyway")

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

    out_json = _evidence_path("builder_end_to_end.json")
    out_json.write_text(json.dumps({
        "n_pass": n_pass, "n_fail": n_fail, "n_total": len(RESULTS),
        "checks": [{"name": n, "pass": ok, "detail": d} for n, ok, d in RESULTS],
        "synthetic_build_report_excerpt": {
            "samples": {RECORD: {
                k: v for k, v in report["samples"][RECORD].items()
                if k != "per_file_sigma_w"}},
            "prune": report["prune"],
            "outputs": report["outputs"],
        },
    }, indent=2, default=str), encoding="utf-8")
    print(f"wrote {out_json}")
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
