"""
Per-event output writer for the H->gamma-gamma analysis, with blinding
built in (implementation task 6, Part C).

Format: ROOT, via uproot (``uproot.recreate``/``uproot.open``) -- not
Parquet. Justification: docker/requirements.txt (this repo's own
dependency list, used to build the cluster conda environment at
/storage/agrp/berkom/atlas-utilization/envs/atlas-pipeline) lists
``awkward`` and ``uproot`` explicitly; it does NOT list ``pyarrow`` (the
library Parquet-via-awkward would need). ROOT/uproot is also what every
earlier stage of this shared pipeline already reads and writes
(orchestration/handlers/parsing_handler.py's own
``_save_chunk_to_root``), so this output uses a format and library
already proven to work in this exact environment, adding zero new
dependencies.

One output file per input (parsed-chunk) file; merged later (see
studies/hgg_cms/cluster/merge_outputs.py) -- never write into the same
output file from two different jobs.

BLINDING BY CONSTRUCTION: for data, any selected event with
115 <= m_gg <= 135 GeV is written ONLY to a separate file whose name
contains "BLINDED_SIGNAL_REGION" -- never mixed into the normal output.
``read_output`` (the one reader this task provides) refuses to open a
BLINDED_SIGNAL_REGION file without ``unblind=True``, and additionally
asserts that no data event with 115 <= m_gg <= 135 is ever present in a
FILE OPENED WITHOUT unblind=True (whether or not its name happens to
contain the marker) -- a second, independent check, not just a filename
convention. Simulation is never blinded (it carries no real information
about the observed data).
"""
from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

import awkward as ak
import numpy as np
import uproot

BLIND_LO, BLIND_HI = 115.0, 135.0
BLINDED_MARKER = "BLINDED_SIGNAL_REGION"

PHOTON_OUTPUT_FIELDS = [
    "pt", "eta", "phi", "r9", "hoe", "sieie",
    "pfRelIso03_all", "pfRelIso03_chg", "mvaID", "isScEtaEB", "isScEtaEE",
]


def git_commit_hash(repo_root) -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=str(repo_root), text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except Exception as e:
        return f"UNKNOWN ({type(e).__name__}: {e})"


def config_sha256(config_path) -> str:
    return hashlib.sha256(Path(config_path).read_bytes()).hexdigest()


def build_output_table(events: ak.Array, selection_result: Dict, is_data: bool, record_id: int) -> ak.Array:
    """One flat (non-jagged) record per SELECTED event -- see
    studies.hgg_cms.selection.select_diphoton_events for
    ``selection_result``'s shape. Never touches Photon_eCorr (not read
    into ``events`` at all by this task's configs, so there is nothing to
    accidentally apply)."""
    sel = selection_result["selected"]
    ev = events[sel]
    lead = selection_result["lead"][sel]
    sublead = selection_result["sublead"][sel]
    mgg = selection_result["mgg"][sel]
    cat = selection_result["category"][sel]

    n = len(ev)
    table = {
        "record_id": ak.Array(np.full(n, record_id, dtype=np.int64)),
        "is_data": ak.Array(np.full(n, is_data, dtype=bool)),
        "run": ev["run"],
        "luminosityBlock": ev["luminosityBlock"],
        "event": ev["event"],
        "m_gg": mgg,
        "category": cat,
        "PV_npvsGood": ev["PV_npvsGood"],
    }
    for label, ph in (("lead", lead), ("sublead", sublead)):
        for field in PHOTON_OUTPUT_FIELDS:
            table[f"{label}_{field}"] = ph[field]

    if not is_data:
        # Per-event normalization weight is NOT stored -- computed later
        # from sigma * BR * L / genEventSumw (task 5/6), which is a
        # per-SAMPLE constant, not a per-event quantity worth duplicating
        # in every row.
        table["genWeight"] = ev["genWeight"]
        table["Pileup_nTrueInt"] = ev["Pileup_nTrueInt"]

    return ak.zip(table, depth_limit=1)


def _write_root_table(table: ak.Array, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    # ak.packed() rebuilds each field as a plain, contiguous layout --
    # needed because a boolean-masked string field (e.g. "category" after
    # slicing by the blinding-window mask) can come out as an IndexedArray,
    # which uproot's own string-branch writer does not support directly
    # (confirmed: raises AttributeError 'IndexedArray' object has no
    # attribute 'offsets'). Packing is a pure layout normalization, values
    # are unchanged.
    packed = ak.to_packed(table)
    with uproot.recreate(str(path)) as f:
        f["events"] = {field: packed[field] for field in packed.fields}


def write_event_output(
    table: ak.Array,
    output_path: Path,
    is_data: bool,
) -> Dict[str, int]:
    """Writes ``table`` to ``output_path``. For data, events with
    115 <= m_gg <= 135 are instead written to a sibling file whose name
    has "_BLINDED_SIGNAL_REGION" inserted before the extension -- never
    into ``output_path`` itself. For simulation, everything goes to
    ``output_path`` unchanged (no blinding).

    Returns {"n_written_normal": int, "n_written_blinded": int}.
    """
    if not is_data:
        _write_root_table(table, output_path)
        return {"n_written_normal": len(table), "n_written_blinded": 0}

    mgg = ak.to_numpy(table["m_gg"])
    in_window = (mgg >= BLIND_LO) & (mgg <= BLIND_HI)

    normal_table = table[~in_window]
    blinded_table = table[in_window]

    _write_root_table(normal_table, output_path)

    blinded_path = output_path.with_name(f"{output_path.stem}_{BLINDED_MARKER}{output_path.suffix}")
    if len(blinded_table) > 0:
        _write_root_table(blinded_table, blinded_path)

    return {"n_written_normal": len(normal_table), "n_written_blinded": len(blinded_table)}


def write_metadata(
    metadata_path: Path,
    *,
    repo_root,
    config_path,
    processed_files: List[str],
    failed_files: List[Dict],
    cutflow: Dict,
    genEventSumw: Optional[Dict] = None,
    luminosity_fb: Optional[float] = None,
    luminosity_uncertainty_pct: Optional[float] = None,
) -> None:
    metadata = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "git_commit": git_commit_hash(repo_root),
        "config_path": str(config_path),
        "config_sha256": config_sha256(config_path),
        "input_files_processed": processed_files,
        "input_files_failed": failed_files,
        "cutflow": cutflow,
    }
    if genEventSumw is not None:
        metadata["genEventSumw_over_processed_files"] = genEventSumw
    if luminosity_fb is not None:
        metadata["luminosity_fb_used"] = luminosity_fb
        metadata["luminosity_uncertainty_pct"] = luminosity_uncertainty_pct

    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, default=str)


def read_output(path, unblind: bool = False) -> ak.Array:
    """The one reader this task provides. Refuses to open a
    BLINDED_SIGNAL_REGION file without ``unblind=True``, and -- regardless
    of filename -- asserts that no data event with 115 <= m_gg <= 135 is
    present when ``unblind`` is False (catches a blinded event that ended
    up in a normally-named file some other way, not just a naming
    mistake)."""
    path = Path(path)
    if BLINDED_MARKER in path.name and not unblind:
        raise PermissionError(
            f"{path} is a blinded signal-region file (its name contains "
            f"'{BLINDED_MARKER}'); pass unblind=True to open it."
        )

    arr = uproot.open(str(path))["events"].arrays(library="ak")

    if not unblind and "is_data" in arr.fields and "m_gg" in arr.fields and len(arr) > 0:
        is_data = ak.to_numpy(arr["is_data"])
        if is_data.any():
            mgg_data = ak.to_numpy(arr["m_gg"])[is_data]
            in_window = (mgg_data >= BLIND_LO) & (mgg_data <= BLIND_HI)
            if in_window.any():
                raise AssertionError(
                    f"BLINDING VIOLATION: {path} contains {int(in_window.sum())} "
                    f"data event(s) with {BLIND_LO} <= m_gg <= {BLIND_HI} GeV in "
                    f"a file opened without unblind=True."
                )
    return arr


def safe_output_filename(input_url_or_path: str, suffix: str = ".root") -> str:
    """Derives an output filename with no spaces, '+', or '=' -- from an
    input file's own basename (already a NanoAOD-style hex ID, safe as-is)
    or URL."""
    base = Path(input_url_or_path).stem
    base = base.replace(" ", "_").replace("+", "plus").replace("=", "_")
    return f"{base}{suffix}"
