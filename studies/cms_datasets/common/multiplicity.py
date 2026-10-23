"""
The max-4-objects multiplicity rule (upstream PR #40, 5fbf1ef) for the CMS
builders, applied at BUILD time. Shared by the data five-dataset matched5
delivery (studies/cms_datasets/deliver/build_four_dataset_delivery.py) and
the MC builder (studies/cms_mc_weights_v3/deliver/build_mc_delivery.py).

The rule (Maryna, upstream #40):
  - at most 4 objects per final state, priority mu > e > b-jet > light jet;
  - leptons + b-jets > 4: event rejected (the CMS per-file rare4 shards
    already do this, so e + m + b <= 4 for every label read here);
  - light jets fill the free slots: label jet count =
    min(raw light jets, 4 - (e + m + b)); extra jets are ignored and the
    event is KEPT;
  - masses use only the kept (leading-pT) jets.
  Examples: 1mu + 5j -> 0e_1m_3j_0b; 2e + 1b + 5j -> 2e_0m_1j_1b.

The rule itself is NOT copied here. cap_label calls upstream's
services.calculations.physics_calcs.limit_particles_in_fs with upstream's
own threshold 4 (physics_calcs.group_by_final_state and
IMCalculator._limit_particles_in_fs use 4), and combination_allowed calls
upstream's physics_calcs.is_finalstate_contain_combination on the
combination dict the per-file driver itself used for that mass.

Why it can be applied at build time (proven on CMS ttbar 67801, 21 Oct 2026,
studies/cms_ttbar_pr40_20261021/REPORT.md on study/cms-ttbar-pr40-20261021):
the per-file driver labels every event with its EXACT multiplicity (each
event in exactly one label) and stores, for each label, every one of the 186
combinations the label contains, each holding one entry per event of the
label. A combination's mass uses the event's leading-pT objects, which does
not depend on the label. So the entries #40 would store under a capped label
+ combination are exactly the union of the entries stored under every exact
label that caps to it, for every combination the capped label still
contains. Only the ORDER of the entries inside a merged array differs (here:
exact labels in ascending multiplicity, then row order), which can move a
weighted bin sum by float64 round-off; an unweighted (data) histogram does
not depend on the order.

regroup_shard is the ttbar study's apply_pr40_to_shard, ported unchanged
except that it uses the two upstream functions above.
"""
from __future__ import annotations

import re
import sqlite3
from collections import defaultdict

import numpy as np

from services.calculations import physics_calcs
from services.calculations.combinatorics import get_all_combinations
from services.pipelines.im_pipeline import prepare_im_combination_name
from services.storage.sqlite_shards import _deserialize_array
from studies.cms_datasets.cluster import run_dataset_on_file as driver

UPSTREAM40_COMMIT = "5fbf1ef"
THRESHOLD = 4
RULES = ("upstream40", "exact")
DEFAULT_RULE = "upstream40"

# <prefix>_FS_<label>_IM_<combination>[<sibling suffix>]; a combination has no
# "_", so the optional MC suffix (_mcw or _mcraw_<field>) is unambiguous. Data
# rows have no suffix.
ROW_PATTERN = re.compile(
    r"^(?P<prefix>.*?)_FS_(?P<fs>[0-9a-z_]+?)_IM_(?P<im>[0-9a-z]+?)"
    r"(?P<suffix>_mcw|_mcraw_[a-z0-9]+)?$")
TOKEN_PATTERN = re.compile(r"(\d+)([a-z])")


def _combinations_by_im() -> dict:
    """{IM string: combination dict} for the driver's own 186 combinations,
    named with the same upstream function the driver names its rows with."""
    combos = get_all_combinations(
        object_types=driver.OBJECT_TYPES,
        min_particles=driver.MIN_PARTICLES_IN_COMBINATION,
        max_particles=driver.MAX_PARTICLES_IN_COMBINATION,
        min_count=driver.MIN_COUNT_PARTICLE_IN_COMBINATION,
        max_count=driver.MAX_COUNT_PARTICLE_IN_COMBINATION,
        max_total_particles=driver.MAX_TOTAL_PARTICLES_IN_COMBINATION,
        include_subleading=driver.INCLUDE_SUBLEADING,
        max_subleading_index=driver.MAX_SUBLEADING_INDEX,
    )
    out = {}
    for combination in combos:
        im = prepare_im_combination_name("x", "x", combination).split("_IM_", 1)[1]
        assert im not in out, f"two combinations share the name {im}"
        out[im] = combination
    assert len(out) == 186, f"expected 186 combinations, got {len(out)}"
    return out


COMBINATION_BY_IM = _combinations_by_im()


def cap_label(label: str) -> str:
    """Upstream #40: physics_calcs.limit_particles_in_fs(label, 4)."""
    return physics_calcs.limit_particles_in_fs(label, THRESHOLD)


def combination_allowed(capped_label: str, im: str) -> bool:
    """Whether combination `im` (e.g. 'm0j0j1j2') exists under the capped
    label: upstream's physics_calcs.is_finalstate_contain_combination on the
    driver's combination dict for that name. An unknown name is an error."""
    if im not in COMBINATION_BY_IM:
        raise KeyError(f"combination {im!r} is not one of the driver's 186")
    return physics_calcs.is_finalstate_contain_combination(capped_label, COMBINATION_BY_IM[im])


def label_counts(label: str) -> dict:
    """{letter: count} of a label, e.g. '0e_1m_5j_0b' -> {e:0, m:1, j:5, b:0}."""
    return {letter: int(n) for n, letter in TOKEN_PATTERN.findall(label)}


def _multiplicity_key(label: str) -> tuple:
    return tuple(label_counts(label).values())


def capped_signatures(shard_path: str) -> list:
    """The CAPPED::<signature> (coverage-cap) metadata keys of a shard,
    read-only. The driver records them in the INCLUSIVE shard only."""
    conn = sqlite3.connect(f"file:{shard_path}?mode=ro", uri=True)
    try:
        return [k[len("CAPPED::"):] for (k,) in conn.execute(
            "SELECT key FROM shard_metadata WHERE key LIKE 'CAPPED::%'")]
    finally:
        conn.close()


def refuse_merged_capped(signatures, where: str) -> None:
    """Stop if a coverage-capped signature would be relabelled: its random
    subsample could not equal what #40 would store."""
    for sig in signatures:
        m = ROW_PATTERN.match(sig)
        if m and cap_label(m.group("fs")) != m.group("fs"):
            raise SystemExit(
                f"STOP: {where}: CAPPED::{sig} is coverage-capped and would be "
                "merged under the #40 rule; the merged subsample cannot equal "
                "what #40 would store. Refusing to build.")


def regroup_shard(shard_path: str) -> dict:
    """Regroup ONE scratch shard under the #40 labels, in place (MC: after
    the _mcw siblings exist; both: before the >=100 rule).

      - every row (mass, and for MC _mcw, _mcraw_*) is renamed to
        cap_label(label);
      - a combination the capped label does not contain is deleted, with
        its siblings;
      - rows of different exact labels that land on the same signature are
        merged by keeping all of them, ordered by exact label (ascending
        multiplicity), then original row order -- the SAME order for the
        masses and every sibling family, so entries stay aligned;
      - final_state_counts is summed per capped label.

    Payload bytes are not touched. A CAPPED:: signature of this shard that
    would be merged is refused (refuse_merged_capped)."""
    conn = sqlite3.connect(shard_path)
    try:
        rows = conn.execute(
            "SELECT id, signature, n_entries, payload FROM array_chunks ORDER BY id"
        ).fetchall()
        capped_meta = [k[len("CAPPED::"):] for (k,) in conn.execute(
            "SELECT key FROM shard_metadata WHERE key LIKE 'CAPPED::%'")]
        fs_counts = conn.execute(
            "SELECT final_state, n_events FROM final_state_counts").fetchall()

        refuse_merged_capped(capped_meta, shard_path)

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
                    f"{mass_sig} after the #40 regrouping. HARD ERROR.")

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


def regroup_report(results: list) -> dict:
    """The build-report section for a list of regroup_shard results."""
    label_map = {}
    for r in results:
        label_map.update(r["label_map"])
    merged_into = defaultdict(list)
    for exact, capped in sorted(label_map.items()):
        merged_into[capped].append(exact)
    return {
        "rule": "upstream40",
        "source": (f"upstream #40 ({UPSTREAM40_COMMIT}): "
                   "services.calculations.physics_calcs.limit_particles_in_fs(label, 4) "
                   "and is_finalstate_contain_combination, called directly"),
        "n_shards": len(results),
        "n_rows_dropped_combination_not_in_capped_label": sum(
            r["n_rows_dropped_combination_not_in_capped_label"] for r in results),
        "n_mass_entries_dropped": sum(r["n_mass_entries_dropped"] for r in results),
        "label_map": dict(sorted(label_map.items())),
        "exact_labels_merged_into": dict(sorted(merged_into.items())),
    }


def final_state_event_counts(shard_paths: list) -> dict:
    """Read-only: per final state, the sum of final_state_counts over all
    shards -- the number the >=100 rule counts."""
    out = defaultdict(int)
    for path in shard_paths:
        conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        try:
            for fs, n in conn.execute(
                    "SELECT final_state, SUM(n_events) FROM final_state_counts "
                    "GROUP BY final_state"):
                out[fs] += int(n)
        finally:
            conn.close()
    return dict(sorted(out.items()))


def final_state_population(shard_paths: list, weight_suffix: str,
                           acceptance_suffix: str, union_fn) -> dict:
    """MC, read-only, for the build report (both rules): per final state, over
    all shards, BEFORE the >=100 rule --
      n_events             sum of final_state_counts (what the rule counts);
      n_ref_entries        entries of the label's reference combination;
      weighted_yield       sum of _mcw over that combination;
      weighted_yield_union the same after the five-flag event union.
    Every stored combination of a label holds one entry per event of the
    label, so the reference combination -- the first mass signature in
    sorted order -- carries each event's weight exactly once. A label with a
    single object has no combination and no weight entry."""
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
