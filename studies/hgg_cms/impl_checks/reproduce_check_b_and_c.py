"""
Implementation task 6, Part D1-D2: exact reproduction of the earlier
physics checks (check_c_trigger_mimicking.py / check_b_vertex.py), using
the REAL production code (FileParser + physics_calcs.filter_events_by_kinematics
for the pipeline's v1 preselection, studies.hgg_cms.selection for
everything after), on the EXACT SAME files and event ranges those checks
used (see check_c_results.json's own "files_read").

check_c1 (signal) computed "n_offline_selected" WITHOUT requiring the
trigger at all, then separately measured "hlt_pass_given_offline" as a
CONDITIONAL count on top of that. This script's production chain applies
the trigger as a hard pre-cut (as config.cms_hgg_signal.yaml actually
does) -- mathematically the AND of two independent masks does not depend
on the order they're applied in, so:
  - this script's "n_offline_selected" (computed with NO trigger filter,
    matching check_c1 exactly) must equal check_c1's with_TM n_offline_selected.
  - this script's "n_after_trigger" (offline-selected AND hlt-passing)
    must equal check_c1's with_TM hlt_pass_given_offline's k.
check_c2 (data) already required the trigger before counting candidates,
so no such distinction is needed there.

BLINDING: data diphoton masses are only ever aggregated into sideband/
blinded COUNTS here, never printed/plotted individually.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import awkward as ak
import numpy as np
import uproot

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

from services.parsing.file_parser import FileParser  # noqa: E402
from services.calculations.physics_calcs import filter_events_by_kinematics  # noqa: E402
from studies.hgg_cms import selection  # noqa: E402

TRIGGER = "HLT_Diphoton30_18_R9Id_OR_IsoCaloId_AND_HE_R9Id_Mass90"
BLIND_LO, BLIND_HI = 115.0, 135.0

V1_KINEMATIC_CUTS = {
    "Photons": {
        "pt": {"min": 20.0},
        "bool_require": ["electronVeto", "mvaID_WP90"],
        "bool_any_of": ["isScEtaEB", "isScEtaEE"],
    }
}
EXTRA_OBJECT_FIELDS = {
    "Photons": [
        "electronVeto", "mvaID_WP90", "isScEtaEB", "isScEtaEE", "r9", "hoe",
        "sieie", "pfRelIso03_all", "pfRelIso03_chg", "mvaID", "cutBased", "pixelSeed",
    ]
}

# XRootD (root://eospublic.cern.ch//eos/opendata/...) is used here in
# preference to the HTTPS mirror. Two independent reasons:
#  1. It is what CERN Open Data's own record filepage API returns for CMS
#     records by default (confirmed by querying
#     https://opendata.cern.ch/record/<id>/filepage/1?group=1 directly --
#     every "uri" field for a CMS record's files is already a root://
#     URL, not https://) -- so this matches what the production pipeline
#     itself reads when it fetches files via specific_record_ids
#     (services/metadata/fetcher.py's MetadataFetcher._fetch_files_for_record
#     just returns file_entry["uri"] verbatim).
#  2. The persistent "TypeError: 'ClientResponseError' object is not
#     subscriptable" failures hit repeatedly here (across many retries and
#     two different internet connections, always over HTTPS) look like an
#     HTTP-transport-specific bug/instability in this uproot version's
#     HTTP source handling, not a problem with the files or the query
#     itself -- switching transport is a reasonable thing to try. THIS IS
#     UNVERIFIED: the local development machine used to write and test
#     this script does not have the `xrootd`/`fsspec_xrootd` Python
#     packages installed (confirmed: `import XRootD` /
#     `import fsspec_xrootd` both fail here with ModuleNotFoundError), so
#     the XRootD code path in this script could not actually be exercised
#     locally. It has only been confirmed that uproot.open() on the SAME
#     three pinned files' root:// URIs is possible in principle (the URIs
#     themselves were obtained from CERN Open Data's own filepage API, see
#     point 1) -- not that the read succeeds or avoids the bug above. This
#     must be confirmed on the cluster's own run (its conda env, per
#     docker/requirements.txt, does list xrootd==5.8.3 and
#     fsspec_xrootd==0.5.1) before trusting this script's cluster results
#     any more than its earlier HTTPS-based runs.
SIGNAL_URL = (
    "root://eospublic.cern.ch//eos/opendata/cms/mc/RunIISummer20UL16NanoAODv9/"
    "GluGluHToGG_M-125_TuneCP5_13TeV-powheg-pythia8/NANOAODSIM/"
    "106X_mcRun2_asymptotic_v17-v1/40000/3231834B-7A6E-4840-8627-C97FDCF67268.root"
)
SIGNAL_ENTRY_STOP = 50000

DATA_FILES = [
    ("Run2016G", "root://eospublic.cern.ch//eos/opendata/cms/Run2016G/DoubleEG/NANOAOD/"
                 "UL2016_MiniAODv2_NanoAODv9-v1/100000/11DA657F-5262-BD4A-AD1E-8E53BE62A601.root", 25000),
    ("Run2016H", "root://eospublic.cern.ch//eos/opendata/cms/Run2016H/DoubleEG/NANOAOD/"
                 "UL2016_MiniAODv2_NanoAODv9-v1/100000/2AD46B56-E1CA-CD44-B30D-C57FE1C35D15.root", 25000),
]


class _CappedTree:
    def __init__(self, real_tree, max_entries):
        self._real = real_tree
        self.num_entries = min(real_tree.num_entries, max_entries)

    def keys(self):
        return self._real.keys()

    def arrays(self, branches, entry_start, entry_stop, library):
        capped_stop = min(entry_stop, self.num_entries)
        return self._real.arrays(branches, entry_start=entry_start, entry_stop=capped_stop, library=library)


class _FakeRoot(dict):
    def keys(self):
        return ["Events;1"]


def parse_capped(url, entry_stop, extra_scalar_branches=None, batch_size=5_000, max_attempts=10):
    """batch_size is deliberately much smaller than entry_stop -- a single
    all-in-one-request read of tens of thousands of events is far more
    prone to a transient remote-read failure (confirmed: repeatedly hit
    this in practice) than several smaller batched requests, and a
    PartialFileReadError here would silently give a smaller-than-expected
    sample for this exact-reproduction check, so the whole read is
    retried a few times on any failure instead."""
    if url.startswith("root://"):
        try:
            import XRootD  # noqa: F401
        except ModuleNotFoundError:
            raise RuntimeError(
                f"cannot open {url}: the XRootD client Python packages "
                "(xrootd, fsspec_xrootd) are not installed in this "
                "environment -- this is an environment/setup problem, not "
                "a transient read failure, so it is not retried. Install "
                "them (see docker/requirements.txt) or run this on the "
                "cluster conda env, which already has them."
            ) from None

    last_err = None
    for attempt in range(max_attempts):
        try:
            real_file = uproot.open(url)
            capped = _CappedTree(real_file["Events"], entry_stop)
            root = _FakeRoot(Events=capped)
            events = FileParser._parse_opened_file(
                root, ["Events"], "cms-nanoaod", batch_size, url, False, None,
                extra_scalar_branches=extra_scalar_branches,
                extra_object_fields=EXTRA_OBJECT_FIELDS,
            )
            if len(events) != entry_stop:
                raise RuntimeError(
                    f"expected exactly {entry_stop} events, got {len(events)} "
                    f"(a partial read likely occurred)"
                )
            return events
        except Exception as e:
            last_err = e
            print(f"  parse_capped attempt {attempt+1}/{max_attempts} failed: "
                  f"{type(e).__name__}: {e}", flush=True)
            import time
            time.sleep(30.0 * (attempt + 1))
    raise RuntimeError(f"parse_capped failed after {max_attempts} attempts: {last_err}") from last_err


def apply_v1(events):
    return filter_events_by_kinematics(events, V1_KINEMATIC_CUTS)


def signal_check():
    events = parse_capped(SIGNAL_URL, SIGNAL_ENTRY_STOP, extra_scalar_branches={"Trigger": [TRIGGER]})
    n_read = len(events)
    v1_events = apply_v1(events)
    result = selection.select_diphoton_events(v1_events)

    selected = result["selected"]
    n_offline_selected = int(ak.sum(selected))

    trig = ak.to_numpy(v1_events[TRIGGER]).astype(bool)
    selected_np = ak.to_numpy(selected)
    n_hlt_given_offline = int(np.sum(selected_np & trig))

    # per-category breakdown among offline-selected (trigger-agnostic)
    cat = ak.to_list(result["category"])
    cat_np = np.array(cat)
    is_bb = (cat_np == "EBEB") & selected_np
    is_other = (cat_np == "notEBEB") & selected_np
    n_bb = int(np.sum(is_bb))
    n_other = int(np.sum(is_other))
    n_hlt_bb = int(np.sum(is_bb & trig))
    n_hlt_other = int(np.sum(is_other & trig))

    # signal-shape numbers over the "offline-selected AND hlt-passing" set
    # (matches check_b's "plain_leading_pair_no_truthmatch_stored_only",
    # n=19792, which includes the trigger requirement -- see this script's
    # module docstring).
    final_mask = selected_np & trig
    mgg_final = ak.to_numpy(result["mgg"])[final_mask]

    from studies.hgg_cms.physics_checks.common import effective_sigma_68, histogram_mode

    shape = {
        "n": int(final_mask.sum()),
        "mean": float(np.mean(mgg_final)) if len(mgg_final) else None,
        "rms": float(np.sqrt(np.mean((mgg_final - np.mean(mgg_final)) ** 2))) if len(mgg_final) else None,
        "median": float(np.median(mgg_final)) if len(mgg_final) else None,
        "peak_mode": histogram_mode(mgg_final, bin_width=0.5, lo=100, hi=180) if len(mgg_final) else None,
        "effective_sigma68": effective_sigma_68(mgg_final) if len(mgg_final) else None,
    }

    return {
        "n_events_read": n_read,
        "n_offline_selected": n_offline_selected,
        "n_offline_selected_barrel_barrel": n_bb,
        "n_offline_selected_other": n_other,
        "n_hlt_pass_given_offline": n_hlt_given_offline,
        "n_hlt_pass_given_offline_barrel_barrel": n_hlt_bb,
        "n_hlt_pass_given_offline_other": n_hlt_other,
        "signal_shape_over_offline_and_hlt_pass": shape,
    }


def data_check():
    n_candidates = 0
    n_sideband = 0
    n_blinded = 0
    per_file = {}
    for era, url, entry_stop in DATA_FILES:
        events = parse_capped(url, entry_stop, extra_scalar_branches={"Trigger": [TRIGGER]})
        n_read = len(events)
        trig = ak.to_numpy(events[TRIGGER]).astype(bool)
        events_trig = events[trig]

        v1_events = apply_v1(events_trig)
        result = selection.select_diphoton_events(v1_events)
        selected_np = ak.to_numpy(result["selected"])
        mgg = ak.to_numpy(result["mgg"])[selected_np]

        n_cand_file = len(mgg)
        n_blind_file = int(((mgg >= BLIND_LO) & (mgg <= BLIND_HI)).sum())
        n_side_file = n_cand_file - n_blind_file

        n_candidates += n_cand_file
        n_sideband += n_side_file
        n_blinded += n_blind_file
        per_file[era] = {
            "n_events_read": n_read,
            "n_after_trigger": int(trig.sum()),
            "n_candidates_100_180": n_cand_file,
            "n_sideband": n_side_file,
            "n_blinded_count_only": n_blind_file,
        }

    return {
        "per_file": per_file,
        "n_candidates_100_180_total": n_candidates,
        "n_sideband_lt115_or_gt135_total": n_sideband,
        "n_blinded_115_135_count_only_total": n_blinded,
    }


def main():
    print("=== Signal (ggH) reproduction of check_c1 (with_TM) ===")
    sig = signal_check()
    print(json.dumps(sig, indent=2))

    print("\n=== Data reproduction of check_c2 (with_TM) ===")
    dat = data_check()
    print(json.dumps(dat, indent=2))

    reference = {
        "check_c1_with_TM": {
            "n_offline_selected": 19986,
            "hlt_pass_given_offline_k": 19792,
            "hlt_pass_given_offline_n": 19986,
        },
        "check_c2_with_TM": {
            "n_candidates_100_180": 92,
            "n_sideband_lt115_or_gt135": 70,
            "n_blinded_115_135_count_only": 22,
        },
        "check_b_plain_leading_pair_no_truthmatch_stored_only": {
            "n": 19792, "mean": 124.36102585747179, "rms": 2.799447767254517,
            "effective_sigma68": 2.049364741663119, "peak_mode": 124.75,
            "median": 124.68260312391092,
        },
    }

    comparison = {
        "signal_n_offline_selected_match": sig["n_offline_selected"] == reference["check_c1_with_TM"]["n_offline_selected"],
        "signal_hlt_given_offline_match": sig["n_hlt_pass_given_offline"] == reference["check_c1_with_TM"]["hlt_pass_given_offline_k"],
        "data_n_candidates_match": dat["n_candidates_100_180_total"] == reference["check_c2_with_TM"]["n_candidates_100_180"],
        "data_n_sideband_match": dat["n_sideband_lt115_or_gt135_total"] == reference["check_c2_with_TM"]["n_sideband_lt115_or_gt135"],
        "data_n_blinded_match": dat["n_blinded_115_135_count_only_total"] == reference["check_c2_with_TM"]["n_blinded_115_135_count_only"],
        "signal_shape_n_match": sig["signal_shape_over_offline_and_hlt_pass"]["n"] == reference["check_b_plain_leading_pair_no_truthmatch_stored_only"]["n"],
    }
    print("\n=== Comparison against pre-recorded reference results ===")
    print(json.dumps(comparison, indent=2))

    out = {
        "signal": sig, "data": dat, "reference": reference, "comparison": comparison,
    }
    out_path = Path(__file__).resolve().parent / "reproduce_check_b_and_c_results.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print(f"\nwrote {out_path}")


if __name__ == "__main__":
    main()
