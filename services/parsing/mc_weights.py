"""
Simulation event weights and pileup information.

Implementation task 5 (studies/hgg_cms/DESIGN_SELECTION.md, Section 6.4 /
Section 8 task 5). Config keys ``parsing_task_config.read_event_weights``
and ``read_pileup_info``, absent/False (the default, and every current
config) is a complete no-op.

Both are read via task 1's general scalar-branch-group mechanism (groups
``"Weights"`` and ``"Pileup"``, see ``services.parsing.file_parser.
FileParser._resolve_scalar_groups``) -- resolved freshly for every file,
because a group's REQUIRED field list depends on whether that specific
file is data or simulation (see ``file_is_simulation`` below), which is
determined by inspecting the file's own ``Events`` tree branch list, not
by any global "parse_mc" flag: a single pipeline run can process a mix of
data and simulation CMS records in the same invocation (specific record
IDs are not split into a data/MC pair the way ATLAS release years are --
see ``orchestration.handlers.parsing_handler.select_metadata_for_parsing``'s
own docstring), so a run-wide assumption would be wrong.
"""
from __future__ import annotations

from typing import Callable, Dict, List, Optional

from services.parsing.file_parser import RequiredScalarBranchMissingError

WEIGHT_BRANCH = "genWeight"
PILEUP_DATA_MC_BRANCH = "PV_npvsGood"
PILEUP_MC_ONLY_BRANCH = "Pileup_nTrueInt"

WEIGHTS_GROUP = "Weights"
PILEUP_GROUP = "Pileup"


class SimulationFieldRequestedOnDataError(RequiredScalarBranchMissingError):
    """``read_event_weights`` (or another simulation-only field) was
    requested, but this file looks like real collision data -- no
    ``genWeight`` branch in its ``Events`` tree. A configuration error
    (the wrong record/config combination), not a per-file data-quality
    issue, so it subclasses ``RequiredScalarBranchMissingError`` to
    propagate through the exact same non-swallowed, run-aborting handling
    already in ``FileParser.parse_file`` and ``ThreadedFileProcessor.
    process_files`` (implementation task 3) with no changes needed there.
    """


def file_is_simulation(tree_branches: set) -> bool:
    """
    True if a file's ``Events`` tree looks like simulation, False if it
    looks like real collision data.

    Robust, file-level detection: checks the tree's own branch NAME list
    (``tree.keys()``, already computed once per file before any value is
    ever read) for the presence of ``genWeight`` -- a branch that exists
    in every CMS NanoAOD simulation sample and in no real collision data
    file (confirmed directly: absent on a real DoubleEG file, present on
    a real GluGluHToGG signal file). This is metadata, not a value read,
    so it isn't subject to the same transient-read-failure hazard as
    ``FileParser._filter_accessible_branches``'s probe (see Part B of this
    task) -- a branch either is or isn't in the tree's structure.

    Note: the pipeline has no existing per-record "declared type" (data
    vs. simulation) concept to cross-check this against (schemas.py's
    ``RECORD_ID_TO_SCHEMA`` only maps a record to a branch-naming schema,
    not a data/MC type) -- this file-level check is the only detection
    mechanism, not a secondary consistency check against something else.
    """
    return WEIGHT_BRANCH in tree_branches


def resolve_weight_and_pileup_groups(
    tree_branches: set,
    file_path: str,
    read_event_weights: bool,
    read_pileup_info: bool,
) -> Dict[str, List[str]]:
    """
    Build the scalar-branch-group dict (see ``FileParser._resolve_scalar_
    groups``) for whichever of ``read_event_weights``/``read_pileup_info``
    are enabled, for THIS specific file.

    Returns ``{}`` when both are False (identical to before this feature
    existed). The caller merges the result into whatever
    ``extra_scalar_branches`` it already has for this file.

    Raises:
        SimulationFieldRequestedOnDataError: ``read_event_weights`` is set
            but this file has no ``genWeight`` branch (looks like real
            data).
    """
    groups: Dict[str, List[str]] = {}
    is_sim = file_is_simulation(tree_branches)

    if read_event_weights:
        if not is_sim:
            raise SimulationFieldRequestedOnDataError([(
                file_path,
                WEIGHTS_GROUP,
                [
                    f"{WEIGHT_BRANCH} (read_event_weights is set, but this "
                    f"file has no {WEIGHT_BRANCH} branch -- it looks like "
                    f"real collision data, not simulation; genWeight only "
                    f"exists in simulation)"
                ],
            )])
        groups[WEIGHTS_GROUP] = [WEIGHT_BRANCH]

    if read_pileup_info:
        # PV_npvsGood exists in both data and simulation; Pileup_nTrueInt
        # (a generator-truth quantity) exists only in simulation and is
        # simply not requested at all for a data file -- not an error, and
        # not silently dropped either, since it was never asked for.
        if is_sim:
            groups[PILEUP_GROUP] = [PILEUP_DATA_MC_BRANCH, PILEUP_MC_ONLY_BRANCH]
        else:
            groups[PILEUP_GROUP] = [PILEUP_DATA_MC_BRANCH]

    return groups


def read_runs_tree_sums(
    file_path: str,
    max_attempts: int = 4,
    retry_delays_sec: Optional[List[float]] = None,
) -> Dict[str, float]:
    """
    Sum ``genEventSumw``, ``genEventCount``, and ``genEventSumw2`` over
    every entry of a file's ``Runs`` tree (verified on real signal files:
    exactly one entry per file in every case checked, but every entry is
    summed generically rather than assuming that).

    A small retry (same spirit as Part B's probe retry, for the same
    transient-network-flakiness reason -- this project's remote reads
    have shown this repeatedly -- though this reads full branch VALUES,
    not a branch-accessibility probe, so it is a separate, simpler retry
    rather than a reuse of ``_filter_accessible_branches``'s retry path).

    Raises the last exception if every attempt fails -- callers (see
    ``orchestration.handlers.parsing_handler``) treat that as a loud,
    record-aborting failure, since a missing Runs-tree sum for a file
    whose Events were already successfully processed would make the
    genWeight numerator and genEventSumw denominator cover different file
    sets (implementation task 5's explicit consistency rule).
    """
    from services.parsing.root_io import open_root_file

    delays = retry_delays_sec if retry_delays_sec is not None else [2.0, 5.0, 10.0]
    last_error: Optional[Exception] = None
    for attempt in range(max_attempts):
        try:
            with open_root_file(file_path) as root_file:
                runs_tree = root_file["Runs"]
                arrays = runs_tree.arrays(
                    ["genEventSumw", "genEventCount", "genEventSumw2"], library="np"
                )
                return {
                    "genEventSumw": float(arrays["genEventSumw"].sum()),
                    "genEventCount": int(arrays["genEventCount"].sum()),
                    "genEventSumw2": float(arrays["genEventSumw2"].sum()),
                    "n_runs_entries": int(runs_tree.num_entries),
                }
        except Exception as e:
            last_error = e
            if attempt < len(delays):
                import time
                time.sleep(delays[attempt])
    raise RuntimeError(
        f"Failed to read Runs tree sums for {file_path} after "
        f"{max_attempts} attempt(s): {type(last_error).__name__}: {last_error}"
    ) from last_error


def aggregate_sumw_for_processed_files(
    processed_urls: List[str],
    reader: Callable[[str], Dict[str, float]] = read_runs_tree_sums,
) -> Dict:
    """
    Sum genEventSumw/genEventCount/genEventSumw2 over the Runs tree of
    every URL in ``processed_urls`` -- the files whose Events tree already
    parsed successfully in this run (implementation task 5, Part A).

    ``reader`` is injectable for testing; defaults to
    ``read_runs_tree_sums`` (a real remote/local file read).

    Raises:
        RuntimeError: the Runs tree of ANY of these files could not be
            read (even after ``reader``'s own retries). This is the
            consistency rule: the genWeight numerator (computed
            downstream) and this genEventSumw denominator must come from
            the identical file set -- a file whose Events parsed but whose
            Runs tree failed cannot be silently excluded from the sum,
            since that would leave the denominator covering fewer files
            than the numerator, silently biasing normalization. Every
            such failure is reported together, not just the first.
    """
    total_sumw = 0.0
    total_count = 0
    total_sumw2 = 0.0
    failures: List[tuple] = []

    for url in processed_urls:
        try:
            sums = reader(url)
            total_sumw += sums["genEventSumw"]
            total_count += sums["genEventCount"]
            total_sumw2 += sums["genEventSumw2"]
        except Exception as e:
            failures.append((url, str(e)))

    if failures:
        raise RuntimeError(
            f"Runs-tree genEventSumw read failed for {len(failures)}/"
            f"{len(processed_urls)} files whose Events tree WAS "
            f"successfully parsed. The genEventSumw sum would not cover "
            f"the same file set as the processed events, which would "
            f"silently bias normalization. Failing loudly instead. "
            f"Failures: {failures}"
        )

    return {
        "n_files_processed": len(processed_urls),
        "processed_files": list(processed_urls),
        "genEventSumw": total_sumw,
        "genEventCount": total_count,
        "genEventSumw2": total_sumw2,
    }
