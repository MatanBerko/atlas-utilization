"""
Per-event output writer for the Z->e+e- control-region run (implementation
task 6, Part 4). Mirrors studies.hgg_cms.output's structure (same ROOT-
via-uproot format, same reasoning for it), but:
  - the mass field is named "m_ee" (not "m_gg") -- these are electron
    pairs reconstructed as photon objects, not diphoton candidates, and
    using a visibly different field name avoids any chance of this
    output ever being mistaken for (or accidentally read by tooling
    expecting) an H->gamma-gamma output.
  - NO blinding split. A Z peak at ~91 GeV is not a blinded quantity for
    this analysis; ``write_zee_event_output`` writes every selected event
    to one file, always.
  - metadata is written via studies.hgg_cms.output.write_metadata
    directly (reused, not duplicated) -- including this task's Part 1
    fact-5 improvement, ``cern_input_files``, logged by every Z->ee job
    (unlike the already-completed full H->gamma-gamma run, which predates
    that parameter existing).
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional

import awkward as ak
import numpy as np

from studies.hgg_cms.output import PHOTON_OUTPUT_FIELDS, write_metadata  # noqa: F401  (re-exported for callers)

__all__ = ["build_zee_output_table", "write_zee_event_output", "write_metadata"]


def build_zee_output_table(events: ak.Array, selection_result: Dict, is_data: bool,
                            record_id: Optional[int] = None,
                            extra_scalar_fields: Optional[Dict[str, ak.Array]] = None) -> ak.Array:
    """One flat record per SELECTED event. ``extra_scalar_fields`` (e.g.
    {"passes_diphoton_hlt": <bool array>} for the trigger-efficiency
    sample) are per-EVENT-selected arrays already sliced to the same
    `selected` mask as everything else here -- callers slice their own
    extra branch by ``selection_result["selected"]`` before passing it
    in."""
    sel = selection_result["selected"]
    ev = events[sel]
    lead = ak.drop_none(selection_result["lead"][sel])
    sublead = ak.drop_none(selection_result["sublead"][sel])
    m_ee = selection_result["mgg"][sel]
    cat = selection_result["category"][sel]

    n = len(ev)
    if "source_record" in ev.fields:
        record_id_col = ev["source_record"]
    else:
        if record_id is None:
            raise ValueError("record_id must be given when events have no 'source_record' field")
        record_id_col = ak.Array(np.full(n, record_id, dtype=np.int64))

    table = {
        "record_id": record_id_col,
        "is_data": ak.Array(np.full(n, is_data, dtype=bool)),
        "run": ev["run"],
        "luminosityBlock": ev["luminosityBlock"],
        "event": ev["event"],
        "m_ee": m_ee,
        "category": cat,
        "PV_npvsGood": ev["PV_npvsGood"],
    }
    for label, ph in (("lead", lead), ("sublead", sublead)):
        for field in PHOTON_OUTPUT_FIELDS:
            table[f"{label}_{field}"] = ph[field]

    if not is_data:
        table["genWeight"] = ev["genWeight"]
        table["Pileup_nTrueInt"] = ev["Pileup_nTrueInt"]

    if extra_scalar_fields:
        for name, arr in extra_scalar_fields.items():
            table[name] = arr

    return ak.zip(table, depth_limit=1)


def write_zee_event_output(table: ak.Array, output_path: Path) -> int:
    """Writes ``table`` to ``output_path``, no blinding split. Returns the
    number of events written."""
    import uproot
    output_path.parent.mkdir(parents=True, exist_ok=True)
    packed = ak.to_packed(table)
    with uproot.recreate(str(output_path)) as f:
        f["events"] = {field: packed[field] for field in packed.fields}
    return len(packed)


def read_zee_output(path) -> ak.Array:
    """Plain read -- no blinding logic applies to this control sample."""
    import uproot
    return uproot.open(str(path))["events"].arrays(library="ak")
