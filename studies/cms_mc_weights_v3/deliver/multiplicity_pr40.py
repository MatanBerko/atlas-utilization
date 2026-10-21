"""
Optional PR #40 multiplicity rule for the CMS MC builder (TEST ONLY).

Source of the rule
    upstream repo  Zhavi221/atlas-utilization
    pull request   #40 "Fix event multiplicity" (branch feature/multiplicity-fix)
    commit         c2488b77e497813bba2da4a46d411d1f834e69f9 (20 Oct 2026, 22:47)
    function       services/calculations/physics_calcs.py::limit_particles_in_fs
    status         NOT merged. The CMS production code is unchanged; this
                   module is used only by build_mc_delivery.py with
                   --multiplicity-rule pr40 (default: exact).

The rule (Maryna, 20 Oct 2026):
  - at most 4 objects per final-state category, priority mu > e > b-jet >
    light jet;
  - events with leptons + b-jets > 4 are rejected (the CMS rare4 shards
    already do this, so e + m + b <= 4 for every label read here);
  - light jets fill the free slots: label jet count =
    min(raw light jets, 4 - (e + m + b)); extra jets are ignored and the
    event is KEPT;
  - invariant masses use only the kept (leading-pT) jets.
  Examples: 1mu + 5j -> 0e_1m_3j_0b; 2e + 1b + 5j -> 2e_0m_1j_1b.

Why it can be applied at BUILD time (study step 1, checked by reading the
driver and on real 67801 shards): the per-file driver labels every event
with its EXACT multiplicity (each event in exactly one label) and stores,
for each label, every one of the 186 combinations the label contains
(physics_calcs.is_finalstate_contain_combination), each holding one entry
per event of the label. A combination's mass uses the event's leading-pT
objects, which does not depend on the label. So the entries #40 would store
under a capped label + combination are exactly the union of the entries
stored under every exact label that caps to it, for every combination the
capped label still contains. Only the ORDER of the entries inside a merged
array differs (here: exact labels in ascending multiplicity, then file
order; #40: file order), which can move a weighted bin sum by float64
round-off.
"""
from __future__ import annotations

import re
import sqlite3
from collections import defaultdict

import numpy as np

from services.storage.sqlite_shards import _deserialize_array

PR40_COMMIT = "c2488b77e497813bba2da4a46d411d1f834e69f9"
THRESHOLD = 4
JET_LETTER = "j"

# <prefix>_FS_<label>_IM_<combination>[<sibling suffix>]; a combination has no
# "_", so the optional suffix (_mcw or _mcraw_<field>) is unambiguous.
ROW_PATTERN = re.compile(
    r"^(?P<prefix>.*?)_FS_(?P<fs>[0-9a-z_]+?)_IM_(?P<im>[0-9a-z]+?)"
    r"(?P<suffix>_mcw|_mcraw_[a-z0-9]+)?$")
TOKEN_PATTERN = re.compile(r"(\d+)([a-z])")
RANK_PATTERN = re.compile(r"([a-z])(\d+)")


def cap_label(label: str) -> str:
    """#40's limit_particles_in_fs(label, 4) at c2488b7, logic copied
    unchanged: non-jet counts are summed, the jet count becomes
    min(jets, max(4 - non_jet_total, 0)), any other count above 4 becomes 4.
    Every non-jet letter (e, m, b, and g/t if present) counts as non-jet."""
    fs_particles = label.split("_")

    non_jet_total = 0
    for token in fs_particles:
        if len(token) < 2:
            continue
        amount_str = token[:-1]
        letter = token[-1]
        if amount_str.isdigit() and letter != JET_LETTER:
            non_jet_total += int(amount_str)

    jet_slots = max(THRESHOLD - non_jet_total, 0)

    parts = []
    for token in fs_particles:
        if len(token) < 2:
            parts.append(token)
            continue
        amount_str = token[:-1]
        letter = token[-1]
        if not amount_str.isdigit():
            parts.append(token)
            continue
        amount = int(amount_str)
        if letter == JET_LETTER:
            parts.append(f"{min(amount, jet_slots)}{letter}")
        elif amount > THRESHOLD:
            parts.append(f"{THRESHOLD}{letter}")
        else:
            parts.append(token)
    return "_".join(parts)


def label_counts(label: str) -> dict:
    """{letter: count} of a label, e.g. '0e_1m_5j_0b' -> {e:0, m:1, j:5, b:0}."""
    return {letter: int(n) for n, letter in TOKEN_PATTERN.findall(label)}


def combination_allowed(capped_label: str, im: str) -> bool:
    """Whether combination `im` (e.g. 'm0j0j1j2', ranks 0 = leading) exists
    under the capped label: every rank of every type is below that type's
    count in the capped label. Only the jet count is ever reduced by
    cap_label, so in practice this is 'highest jet rank < capped jet count'."""
    counts = label_counts(capped_label)
    for letter, rank in RANK_PATTERN.findall(im):
        if int(rank) >= counts.get(letter, 0):
            return False
    return True


def _multiplicity_key(label: str) -> tuple:
    return tuple(label_counts(label).values())


def apply_pr40_to_shard(shard_path: str) -> dict:
    """Regroup ONE scratch shard (after the _mcw siblings exist, before the
    >=100 rule) under the PR #40 labels, in place.

      - every row (mass, _mcw, _mcraw_*) is renamed to cap_label(label);
      - a combination the capped label does not contain is deleted, with
        its siblings;
      - rows of different exact labels that land on the same signature are
        merged by keeping all of them, ordered by exact label (ascending
        multiplicity), then original row order -- the SAME order for the
        masses and every sibling family, so entries stay aligned;
      - final_state_counts is summed per capped label.

    Payload bytes are not touched. A CAPPED:: (coverage-cap) signature that
    would be merged is refused: its subsample could not equal #40's."""
    conn = sqlite3.connect(shard_path)
    try:
        rows = conn.execute(
            "SELECT id, signature, n_entries, payload FROM array_chunks ORDER BY id"
        ).fetchall()
        capped_meta = [k for (k,) in conn.execute(
            "SELECT key FROM shard_metadata WHERE key LIKE 'CAPPED::%'")]
        fs_counts = conn.execute(
            "SELECT final_state, n_events FROM final_state_counts").fetchall()

        for key in capped_meta:
            m = ROW_PATTERN.match(key[len("CAPPED::"):])
            if m and cap_label(m.group("fs")) != m.group("fs"):
                raise SystemExit(
                    f"STOP: {shard_path}: {key} is coverage-capped and would be "
                    "merged under PR #40; the merged subsample cannot equal "
                    "what #40 would store. Refusing to build.")

        by_target = defaultdict(list)   # new signature -> [(order key, row)]
        n_rows_dropped = 0
        entries_dropped = 0
        label_map = {}
        for row_id, sig, n_entries, payload in rows:
            m = ROW_PATTERN.match(sig)
            if not m:
                raise SystemExit(
                    f"{shard_path}: row signature {sig!r} is not "
                    "<prefix>_FS_<label>_IM_<combination>[sibling]. Refusing "
                    "to regroup an unknown row.")
            exact = m.group("fs")
            capped = cap_label(exact)
            label_map[exact] = capped
            if not combination_allowed(capped, m.group("im")):
                n_rows_dropped += 1
                if m.group("suffix") is None:
                    entries_dropped += int(n_entries)
                continue
            new_sig = (f"{m.group('prefix')}_FS_{capped}_IM_{m.group('im')}"
                       f"{m.group('suffix') or ''}")
            by_target[new_sig].append(
                ((_multiplicity_key(exact), exact, row_id), (n_entries, payload)))

        # Lockstep proof: per merged signature, the per-exact-label entry
        # counts of the masses equal those of every sibling family.
        layout = {}
        for new_sig, items in by_target.items():
            items.sort(key=lambda it: it[0])
            per_label = defaultdict(int)
            for (_k, exact, _id), (n_entries, _p) in items:
                per_label[exact] += int(n_entries)
            layout[new_sig] = dict(per_label)
        for new_sig, per_label in layout.items():
            base = ROW_PATTERN.match(new_sig)
            if base.group("suffix") is None:
                continue
            mass_sig = new_sig[: -len(base.group("suffix"))]
            if layout.get(mass_sig) != per_label:
                raise SystemExit(
                    f"{shard_path}: sibling {new_sig} is not aligned with "
                    f"{mass_sig} after the PR #40 regrouping. HARD ERROR.")

        merged_counts = defaultdict(int)
        for fs, n in fs_counts:
            merged_counts[cap_label(fs)] += int(n)
        for fs, _n in fs_counts:   # labels without a stored combination too
            label_map.setdefault(fs, cap_label(fs))

        conn.execute("DELETE FROM array_chunks")
        conn.executemany(
            "INSERT INTO array_chunks(signature, n_entries, payload) VALUES (?, ?, ?)",
            [(new_sig, n_entries, payload)
             for new_sig in sorted(by_target)
             for _key, (n_entries, payload) in by_target[new_sig]])
        conn.execute("DELETE FROM final_state_counts")
        conn.executemany(
            "INSERT INTO final_state_counts(final_state, n_events) VALUES (?, ?)",
            sorted(merged_counts.items()))
        conn.commit()
    finally:
        conn.close()
    return {
        "n_rows_in": len(rows),
        "n_rows_out": sum(len(v) for v in by_target.values()),
        "n_rows_dropped_combination_not_in_capped_label": n_rows_dropped,
        "n_mass_entries_dropped": entries_dropped,
        "label_map": dict(sorted(label_map.items())),
    }


def final_state_population(shard_paths: list, weight_suffix: str,
                           acceptance_suffix: str, union_fn) -> dict:
    """Read-only, for the build report (both rules): per final state, over
    all shards, BEFORE the >=100 rule --
      n_events             sum of final_state_counts (what the rule counts);
      n_ref_entries        entries of the label's reference combination;
      weighted_yield       sum of _mcw over that combination;
      weighted_yield_union the same after the five-flag event union.
    Every stored combination of a label holds one entry per event of the
    label (study step 1), so the reference combination -- the first mass
    signature in sorted order -- carries each event's weight exactly once.
    A label with a single object has no combination and no weight entry."""
    out = defaultdict(lambda: {"n_events": 0, "n_ref_entries": 0,
                               "weighted_yield": 0.0, "weighted_yield_union": 0.0})
    for path in shard_paths:
        conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        try:
            for fs, n in conn.execute(
                    "SELECT final_state, SUM(n_events) FROM final_state_counts "
                    "GROUP BY final_state"):
                out[fs]["n_events"] += int(n)
            ref = {}
            for (sig,) in conn.execute(
                    "SELECT DISTINCT signature FROM array_chunks ORDER BY signature"):
                m = ROW_PATTERN.match(sig)
                if m and m.group("suffix") is None:
                    ref.setdefault(m.group("fs"), sig)
            for fs, sig in ref.items():
                def chunks(name):
                    return [_deserialize_array(p) for (p,) in conn.execute(
                        "SELECT payload FROM array_chunks WHERE signature = ? "
                        "ORDER BY id", (name,))]
                w = np.concatenate([np.asarray(c, dtype=np.float64)
                                    for c in chunks(sig + weight_suffix)])
                acc_chunks = chunks(sig + acceptance_suffix)
                union = (union_fn(np.concatenate([np.asarray(c) for c in acc_chunks]))
                         if acc_chunks else np.ones(w.size, dtype=bool))
                out[fs]["n_ref_entries"] += int(w.size)
                out[fs]["weighted_yield"] += float(w.sum())
                out[fs]["weighted_yield_union"] += float(w[union].sum())
        finally:
            conn.close()
    return {fs: dict(v) for fs, v in sorted(out.items())}
