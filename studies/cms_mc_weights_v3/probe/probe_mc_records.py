#!/usr/bin/env python
"""
Read-only probe of CMS MC NanoAOD records for the cms-mc-weights-v3 design
round (Part C).

For each requested CERN Open Data record it opens ONE file (the portal's
own file index 0, resolved through the repo's existing file-list helper --
no hand-typed URLs anywhere) and reports:

  C1  campaign, from the record's own portal metadata `title` (the full DAS
      dataset path). RunIISummer20UL16NanoAODv9 + asymptotic_v17 == postVFP;
      any "APV"/"preVFP" string is flagged as NOT usable with Run2016G+H.
  C2  presence of every branch the four delivered acceptances need, plus
      HLT_Ele27_WPTight_Gsf, the TrigObj block, genWeight, the L1 prefiring
      weights, Pileup_nTrueInt, run, and the Runs tree's genEventSumw /
      genEventCount.
  C3  the TrigObj_filterBits branch TITLE, verbatim plus sha256, so the bit
      meanings can be compared byte-for-byte against the recorded data-file
      title (studies/cms_datasets/electron_prep/evidence/
      trigobj_titles_electron_datasets.json).
  C4  per-path fired fraction over the probed events, and the negative-
      genWeight fraction.
  C5  sum(genWeight) over EVERY event of the file vs that file's own Runs
      genEventSumw. These agree only if the file carries no pre-skim; this
      one check therefore reads the whole genWeight branch (and nothing
      else) rather than the 10k-event probe window.

Writes one JSON and one text summary into --output-dir. Nothing outside
--output-dir is written, nothing is deleted, and no file is opened for
anything but reading. No batch jobs: this is meant to be run interactively
under `nice` on the analysis node.

Usage:
    python studies/cms_mc_weights_v3/probe/probe_mc_records.py \
        --output-dir /storage/.../work/cms_mc_v3_design_<date> \
        [--records 67801,35669,...] [--max-events 10000]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

import numpy as np  # noqa: E402
import requests  # noqa: E402
import uproot  # noqa: E402

from studies.m0m1j0_cms.design_checks.common import (  # noqa: E402
    fetch_file_list,
    fetch_record_number_events,
)

CMS_RECID_API_URL = "https://opendata.cern.ch/api/records/{0}"

# Records to probe. The v2 normalisation registry
# (studies/cms_mc_weights/cms_mc_normalisation.json on
# feature/cms-mc-weights-v2) plus 37728, the ggH->ZZ->4l signal pilot that
# is tabulated but NOT yet in that registry.
V2_REGISTRY_RECORDS = [
    42407, 67801, 35671, 64895, 64839, 72676,
    72752, 75589, 68187, 68073, 67993, 35669,
]
EXTRA_RECORDS = [37728]
DEFAULT_RECORDS = V2_REGISTRY_RECORDS + EXTRA_RECORDS

# The HLT paths of the four delivered data acceptances, copied from
# studies/cms_datasets/cluster/datasets_records.py::DATASETS (not retyped
# from any document), plus the SingleElectron candidate path of design
# item D2 and the SingleMuon track-muon twin.
HLT_PATHS = [
    # DoubleMuon
    "HLT_Mu17_TrkIsoVVL_Mu8_TrkIsoVVL_DZ",
    "HLT_Mu17_TrkIsoVVL_TkMu8_TrkIsoVVL_DZ",
    # SingleMuon
    "HLT_IsoMu24",
    "HLT_IsoTkMu24",
    # DoubleEG
    "HLT_Ele23_Ele12_CaloIdL_TrackIdL_IsoVL_DZ",
    # MuonEG
    "HLT_Mu23_TrkIsoVVL_Ele12_CaloIdL_TrackIdL_IsoVL_DZ",
    "HLT_Mu8_TrkIsoVVL_Ele23_CaloIdL_TrackIdL_IsoVL_DZ",
    # SingleElectron candidate (D2)
    "HLT_Ele27_WPTight_Gsf",
]

TRIGOBJ_BRANCHES = [
    "nTrigObj", "TrigObj_pt", "TrigObj_eta", "TrigObj_phi",
    "TrigObj_id", "TrigObj_filterBits",
]

WEIGHT_BRANCHES = [
    "genWeight",
    "L1PreFiringWeight_Nom", "L1PreFiringWeight_Up", "L1PreFiringWeight_Dn",
    "Pileup_nTrueInt",
    "run", "luminosityBlock", "event",
]

RUNS_BRANCHES = ["genEventSumw", "genEventCount"]

# Recorded data-file TrigObj_filterBits title, for the C3 comparison.
DATA_TITLES_JSON = (
    REPO_ROOT / "studies" / "cms_datasets" / "electron_prep" / "evidence"
    / "trigobj_titles_electron_datasets.json"
)


def git_commit_hash() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=str(REPO_ROOT), text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except Exception as exc:  # noqa: BLE001
        return f"UNKNOWN ({type(exc).__name__}: {exc})"


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def fetch_record_title(record_id: int) -> str:
    r = requests.get(CMS_RECID_API_URL.format(record_id), timeout=60)
    r.raise_for_status()
    return r.json()["metadata"]["title"]


def classify_campaign(title: str) -> dict:
    """Campaign verdict from the record's own DAS dataset path.

    postVFP UL16 NanoAODv9 is 'RunIISummer20UL16NanoAODv9' with the
    '106X_mcRun2_asymptotic_v17' global tag. The pre-VFP (APV) twin is
    'RunIISummer20UL16NanoAODAPVv9' with '..._preVFP_...'. Anything else is
    reported as 'other' rather than guessed at.
    """
    has_apv = "APV" in title
    has_prevfp = "preVFP" in title
    is_ul16_v9 = "RunIISummer20UL16NanoAODv9" in title
    has_v17 = "asymptotic_v17" in title
    if is_ul16_v9 and not has_apv and not has_prevfp:
        verdict = "UL16_postVFP_NanoAODv9"
    elif has_apv or has_prevfp:
        verdict = "UL16_APV_preVFP__MUST_NOT_BE_USED_WITH_G+H"
    else:
        verdict = "other__NOT_UL16_NanoAODv9"
    return {
        "campaign_verdict": verdict,
        "is_postVFP_UL16_NanoAODv9": verdict == "UL16_postVFP_NanoAODv9",
        "title_contains_APV": has_apv,
        "title_contains_preVFP": has_prevfp,
        "title_contains_RunIISummer20UL16NanoAODv9": is_ul16_v9,
        "title_contains_asymptotic_v17": has_v17,
    }


def probe_record(record_id: int, max_events: int, logf) -> dict:
    out: dict = {"record_id": record_id}
    t0 = time.perf_counter()

    def log(msg: str) -> None:
        line = f"[{record_id}] {msg}"
        print(line, flush=True)
        logf.write(line + "\n")
        logf.flush()

    # ---- C1: campaign from the portal record metadata -------------------
    title = fetch_record_title(record_id)
    out["portal_title"] = title
    out["campaign"] = classify_campaign(title)
    log(f"campaign={out['campaign']['campaign_verdict']}")

    portal_counts = fetch_record_number_events(record_id)
    out["portal_number_events"] = portal_counts["number_events"]
    out["portal_number_files"] = portal_counts["number_files"]

    urls = fetch_file_list(record_id)
    out["n_files_in_portal_list"] = len(urls)
    file_url = urls[0]
    out["probed_file_url"] = file_url
    out["probed_file_index"] = 0

    # ---- open the file --------------------------------------------------
    with uproot.open(file_url) as f:
        tree = f["Events"]
        n_total = int(tree.num_entries)
        out["n_events_in_file"] = n_total
        available = set(tree.keys())

        # ---- C2: branch presence ---------------------------------------
        wanted = HLT_PATHS + TRIGOBJ_BRANCHES + WEIGHT_BRANCHES
        out["branches_present"] = {b: (b in available) for b in wanted}
        out["branches_missing"] = sorted(b for b in wanted if b not in available)

        runs_present: dict = {}
        if "Runs" in {k.split(";")[0] for k in f.keys()}:
            runs = f["Runs"]
            runs_keys = set(runs.keys())
            runs_present = {b: (b in runs_keys) for b in RUNS_BRANCHES}
            out["runs_tree_present"] = True
            out["runs_branches_present"] = runs_present
            if runs_present.get("genEventSumw"):
                sumw_per_run = np.asarray(runs["genEventSumw"].array(library="np"), dtype=np.float64)
                out["runs_genEventSumw_entries"] = sumw_per_run.tolist()
                out["runs_genEventSumw_total"] = float(sumw_per_run.sum())
            if runs_present.get("genEventCount"):
                cnt_per_run = np.asarray(runs["genEventCount"].array(library="np"))
                out["runs_genEventCount_entries"] = [int(c) for c in cnt_per_run]
                out["runs_genEventCount_total"] = int(cnt_per_run.sum())
        else:
            out["runs_tree_present"] = False
            out["runs_branches_present"] = {}
        log(f"n_events={n_total:,} missing_branches={out['branches_missing']}")

        # ---- C3: TrigObj_filterBits / TrigObj_id branch TITLES ---------
        titles = {}
        for b in ("TrigObj_filterBits", "TrigObj_id"):
            if b in available:
                titles[b] = " ".join(str(tree[b].title).split())
        out["trigobj_branch_titles"] = titles
        out["trigobj_filterBits_title_sha256"] = (
            sha256(titles["TrigObj_filterBits"]) if "TrigObj_filterBits" in titles else None
        )

        # ---- C4: fired fractions + negative-weight fraction ------------
        n_probe = min(max_events, n_total)
        out["n_events_probed"] = n_probe
        fired = {}
        if n_probe > 0:
            present_paths = [p for p in HLT_PATHS if p in available]
            if present_paths:
                arrs = tree.arrays(
                    present_paths, entry_start=0, entry_stop=n_probe, library="np"
                )
                for p in present_paths:
                    n_fired = int(np.count_nonzero(arrs[p]))
                    fired[p] = {
                        "n_fired": n_fired,
                        "fraction": n_fired / n_probe,
                    }
            for p in HLT_PATHS:
                if p not in available:
                    fired[p] = {"n_fired": None, "fraction": None, "branch_missing": True}
        out["hlt_fired_in_probe_window"] = fired

        if "genWeight" in available and n_probe > 0:
            gw_probe = tree["genWeight"].array(
                entry_start=0, entry_stop=n_probe, library="np"
            )
            gw_probe = np.asarray(gw_probe, dtype=np.float64)
            out["probe_window_genWeight"] = {
                "n": int(gw_probe.size),
                "n_negative": int(np.count_nonzero(gw_probe < 0)),
                "negative_fraction": float(np.count_nonzero(gw_probe < 0) / gw_probe.size),
                "min": float(gw_probe.min()),
                "max": float(gw_probe.max()),
                "mean": float(gw_probe.mean()),
                "n_distinct_abs_values_capped_at_6": int(
                    min(6, np.unique(np.abs(gw_probe)).size)
                ),
            }

        # ---- C5: whole-file sum(genWeight) vs Runs genEventSumw --------
        if "genWeight" in available:
            t_sum = time.perf_counter()
            total = 0.0
            n_seen = 0
            n_neg = 0
            for chunk in tree.iterate(["genWeight"], step_size="50 MB", library="np"):
                arr = np.asarray(chunk["genWeight"], dtype=np.float64)
                total += float(arr.sum())
                n_seen += int(arr.size)
                n_neg += int(np.count_nonzero(arr < 0))
            out["file_genWeight_sum"] = total
            out["file_genWeight_n_events"] = n_seen
            out["file_genWeight_n_negative"] = n_neg
            out["file_negative_genWeight_fraction"] = (n_neg / n_seen) if n_seen else None
            out["file_genWeight_read_seconds"] = time.perf_counter() - t_sum

            sumw = out.get("runs_genEventSumw_total")
            if sumw is not None:
                diff = total - sumw
                rel = abs(diff) / abs(sumw) if sumw else None
                out["C5_sum_genWeight_vs_runs_genEventSumw"] = {
                    "sum_genWeight_all_events": total,
                    "runs_genEventSumw_total": sumw,
                    "absolute_difference": diff,
                    "relative_difference": rel,
                    # 1e-6 relative is far above float64 round-off on a sum of
                    # O(1e6) terms and far below any real pre-skim effect.
                    "agree_within_1e-6_relative": bool(rel is not None and rel < 1e-6),
                }
                out["C5_event_count_vs_runs_genEventCount"] = {
                    "n_events_in_file": n_seen,
                    "runs_genEventCount_total": out.get("runs_genEventCount_total"),
                    "equal": (
                        out.get("runs_genEventCount_total") == n_seen
                        if out.get("runs_genEventCount_total") is not None else None
                    ),
                }
                log(
                    "C5 sum(genWeight)=%.6e vs genEventSumw=%.6e rel=%s"
                    % (total, sumw, "n/a" if rel is None else f"{rel:.3e}")
                )

    out["probe_seconds"] = time.perf_counter() - t0
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output-dir", required=True)
    ap.add_argument("--records", default=None,
                    help="comma-separated record ids; default is the v2 registry + 37728")
    ap.add_argument("--max-events", type=int, default=10000,
                    help="probe-window size for branch/HLT/weight stats (C2-C4)")
    ap.add_argument("--skip-full-sum", action="store_true",
                    help="skip the C5 whole-file genWeight sum (diagnostics only)")
    args = ap.parse_args()

    records = (
        [int(x) for x in args.records.split(",") if x.strip()]
        if args.records else list(DEFAULT_RECORDS)
    )

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    data_ref = json.loads(DATA_TITLES_JSON.read_text(encoding="utf-8"))
    data_title = " ".join(str(data_ref["filterBits_title_full"]).split())
    data_title_sha = sha256(data_title)

    result = {
        "what": (
            "Read-only probe of CMS MC NanoAOD records for the cms-mc-weights-v3 "
            "design round (Part C). One file per record, portal file index 0."
        ),
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "repo_root": str(REPO_ROOT),
        "git_commit": git_commit_hash(),
        "max_events_probe_window": args.max_events,
        "records_requested": records,
        "v2_registry_records": V2_REGISTRY_RECORDS,
        "extra_records": EXTRA_RECORDS,
        "hlt_paths_probed": HLT_PATHS,
        "data_reference_filterBits_title": data_title,
        "data_reference_filterBits_title_sha256": data_title_sha,
        "data_reference_source": str(DATA_TITLES_JSON.relative_to(REPO_ROOT)),
        "records": {},
        "errors": {},
    }

    log_path = out_dir / "probe_mc_records.log"
    with open(log_path, "w", encoding="utf-8") as logf:
        for rid in records:
            try:
                rec = probe_record(rid, args.max_events, logf)
                ft = rec.get("trigobj_filterBits_title_sha256")
                rec["C3_filterBits_title_matches_data"] = (
                    None if ft is None else bool(ft == data_title_sha)
                )
                result["records"][str(rid)] = rec
            except Exception as exc:  # noqa: BLE001
                msg = f"{type(exc).__name__}: {exc}"
                print(f"[{rid}] ERROR {msg}", flush=True)
                logf.write(f"[{rid}] ERROR {msg}\n{traceback.format_exc()}\n")
                logf.flush()
                result["errors"][str(rid)] = msg

    # ---- roll-up ---------------------------------------------------------
    recs = result["records"]
    result["summary"] = {
        "n_records_probed": len(recs),
        "n_records_failed": len(result["errors"]),
        "records_not_postVFP": sorted(
            k for k, v in recs.items()
            if not v.get("campaign", {}).get("is_postVFP_UL16_NanoAODv9")
        ),
        "records_with_missing_branches": {
            k: v["branches_missing"] for k, v in recs.items() if v.get("branches_missing")
        },
        "records_without_runs_genEventSumw": sorted(
            k for k, v in recs.items()
            if not v.get("runs_branches_present", {}).get("genEventSumw")
        ),
        "records_filterBits_title_differs_from_data": sorted(
            k for k, v in recs.items() if v.get("C3_filterBits_title_matches_data") is False
        ),
        "records_C5_disagreeing": sorted(
            k for k, v in recs.items()
            if v.get("C5_sum_genWeight_vs_runs_genEventSumw", {})
                 .get("agree_within_1e-6_relative") is False
        ),
        "negative_genWeight_fraction_whole_file_by_record": {
            k: v.get("file_negative_genWeight_fraction") for k, v in recs.items()
        },
    }

    json_path = out_dir / "probe_mc_records.json"
    json_path.write_text(json.dumps(result, indent=2), encoding="utf-8")

    lines = [
        "CMS MC NanoAOD probe -- cms-mc-weights-v3 design round (Part C)",
        f"commit: {result['git_commit']}",
        f"generated: {result['generated_utc']}",
        f"probe window: {args.max_events} events per file (C5 reads whole files)",
        "",
        f"{'rec':>6} {'postVFP':>8} {'nEvents':>12} {'negW frac':>10} {'C5':>6} {'bits==data':>11}  title",
    ]
    for k in [str(r) for r in records]:
        v = recs.get(k)
        if v is None:
            lines.append(f"{k:>6}   ERROR: {result['errors'].get(k)}")
            continue
        c5 = v.get("C5_sum_genWeight_vs_runs_genEventSumw", {}).get(
            "agree_within_1e-6_relative")
        negf = v.get("file_negative_genWeight_fraction")
        lines.append(
            f"{k:>6} {str(v['campaign']['is_postVFP_UL16_NanoAODv9']):>8} "
            f"{v.get('n_events_in_file', 0):>12,} "
            f"{('n/a' if negf is None else f'{negf:.5f}'):>10} "
            f"{str(c5):>6} {str(v.get('C3_filterBits_title_matches_data')):>11}  "
            f"{v['portal_title']}"
        )
    lines += ["", "summary:", json.dumps(result["summary"], indent=2)]
    (out_dir / "probe_mc_records.txt").write_text("\n".join(lines), encoding="utf-8")

    print("\n".join(lines[5:]), flush=True)
    print(f"\nwrote {json_path}", flush=True)
    return 0 if not result["errors"] else 1


if __name__ == "__main__":
    sys.exit(main())
