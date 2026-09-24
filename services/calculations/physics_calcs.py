"""
Physics calculations for particle event processing.

Provides functions for invariant mass calculations, event filtering
by kinematics and particle counts, final state grouping, and event slicing.
"""
import awkward as ak
import logging
import numpy as np
import vector
import gc
from typing import Dict, Iterator, Tuple, Optional

from services.calculations import consts
from services.calculations.combinatorics import get_count, get_start


def calc_inv_mass(particle_events: ak.Array) -> ak.Array:
    if len(particle_events) == 0:
        return ak.Array([])

    all_vectors = concat_events(particle_events)
    combined_vectors = ak.concatenate(all_vectors, axis=1)
    total_momentum = ak.sum(combined_vectors, axis=1)

    if hasattr(total_momentum, 'tau'):
        return total_momentum.tau
    return total_momentum.mass


def concat_events(particle_events: ak.Array) -> list:
    all_vectors = []
    for particle_type in particle_events.fields:
        particle_array = particle_events[particle_type]
        mass = get_particle_known_mass(particle_type, particle_array)
        momentum_vector = vector.zip({
            "pt": particle_array.pt,
            "phi": particle_array.phi,
            "eta": particle_array.eta,
            "mass": mass
        })
        all_vectors.append(momentum_vector)
    return all_vectors


def get_particle_known_mass(particle_type: str, particle_array: ak.Array) -> ak.Array:
    if 'mass' in particle_array.fields:
        return particle_array['mass']
    return consts.KNOWN_MASSES.get(particle_type, 0.0)


def extract_object_types(fields: list) -> set:
    particle_types = set()
    for field in fields:
        if '_' in field and not field.startswith('n'):
            particle_type = field.split('_')[0]
            particle_types.add(particle_type)
    return particle_types


def group_by_final_state(events: ak.Array) -> Iterator[Tuple[str, ak.Array]]:
    num_events = len(events)
    zero_array = ak.Array([0] * num_events) if num_events > 0 else ak.Array([])
    particle_counts = ak.num(events)

    e = getattr(particle_counts, "Electrons", zero_array)
    m = getattr(particle_counts, "Muons", zero_array)
    j = getattr(particle_counts, "Jets", zero_array)
    g = getattr(particle_counts, "Photons", zero_array)
    t = getattr(particle_counts, "Taus", zero_array)
    b = getattr(particle_counts, "BJets", zero_array)

    all_events_fs = [
        f"{e}e_{m}m_{j}j_{g}g_{t}t_{b}b"
        for e, m, j, g, t, b in zip(e, m, j, g, t, b)
    ]
    unique_fs = set(all_events_fs)

    for fs in unique_fs:
        mask = (ak.Array(all_events_fs) == fs)
        events_matching_fs = events[mask]
        fs = limit_particles_in_fs(fs, 4)
        yield (fs, events_matching_fs)


def limit_particles_in_fs(final_state: str, threshold: int) -> str:
    fs_particles = final_state.split('_')
    for str_amount_particle in fs_particles:
        if len(str_amount_particle) < 2:
            continue
        amount_to_calc = str_amount_particle[0]
        particle_letter = str_amount_particle[1]
        if amount_to_calc.isdigit():
            amount = int(amount_to_calc)
            if amount > threshold:
                final_state = final_state.replace(
                    f"{amount}{particle_letter}", f"{threshold}{particle_letter}")
    return final_state


def is_finalstate_contain_combination(final_state: str, combination: Dict) -> bool:
    """
    Check whether a final state has enough particles to satisfy a combination.
    Works with both plain-int and (count, start_index) combination values.
    """
    fs_particles = final_state.split('_')
    for str_amount_particle in fs_particles:
        if len(str_amount_particle) < 2:
            continue
        amount_to_calc = str_amount_particle[0]
        particle_letter = str_amount_particle[1]
        particle = consts.LETTER_PARTICLE_MAPPING.get(particle_letter)

        if particle is None or particle not in combination:
            continue
        if not amount_to_calc.isdigit():
            continue

        fs_particle_amount = int(amount_to_calc)
        value = combination[particle]
        count = get_count(value)
        start = get_start(value)
        # Need at least start + count particles available
        if fs_particle_amount < start + count:
            return False
    return True


def filter_events_by_particle_counts(
    events: ak.Array,
    particle_counts: Dict,
    is_exact_count: bool = False,
    is_particle_counts_range: bool = False
) -> ak.Array:
    """
    Filter events by particle counts.
    Accepts both plain-int and (count, start_index) combination values.
    For sub-leading combinations, filters to events that have at least
    start + count particles of each required type.
    """
    if len(events) == 0:
        return events

    combined_mask = ak.ones_like(ak.num(events[events.fields[0]]), dtype=bool)

    for obj, value in particle_counts.items():
        if obj not in events.fields:
            required_min = (
                value["min"]
                if is_particle_counts_range
                else get_start(value) + get_count(value)
            )
            if required_min > 0:
                combined_mask = combined_mask & False
            continue

        obj_array = events[obj]
        if ak.all(ak.is_none(obj_array)):
            required_min = (
                value["min"]
                if is_particle_counts_range
                else get_start(value) + get_count(value)
            )
            if required_min > 0:
                combined_mask = combined_mask & False
            continue

        obj_count = ak.num(obj_array)

        if is_particle_counts_range:
            range_dict = value
            particle_mask = (obj_count >= range_dict['min']) & (obj_count <= range_dict['max'])
        else:
            count = get_count(value)
            start = get_start(value)
            particle_mask = (obj_count >= start + count)

        combined_mask = combined_mask & particle_mask

    filtered_events = events[combined_mask]
    del combined_mask
    gc.collect()

    if is_exact_count:
        fields_to_keep = {}
        for particle_type in particle_counts.keys():
            if particle_type in filtered_events.fields:
                fields_to_keep[particle_type] = filtered_events[particle_type]
            else:
                logging.warning(f"Could not find {particle_type} in event data, skipping!")

        if len(fields_to_keep) == 0:
            return ak.Array([])
        filtered_events = ak.zip(fields_to_keep, depth_limit=1)

    return ak.to_packed(filtered_events)


def slice_events_by_field(
    events: ak.Array,
    particle_counts: Dict,
    field_to_slice_by: str
) -> ak.Array:
    """
    Sort each particle type by field_to_slice_by (descending) and slice
    out the requested window [start : start + count].

    Works with both plain-int values (start=0) and (count, start_index) tuples.

    Example:
        particle_counts = {"Electrons": (1, 1), "Jets": (1, 0)}
        → takes e₁ (second-highest pT electron) and j₀ (leading jet)
    """
    for obj, value in particle_counts.items():
        if obj not in events.fields:
            logging.warning(f"Could not find {obj} in event data, skipping!")
            continue

        count = get_count(value)
        start = get_start(value)

        obj_array = events[obj]
        sorted_obj_array = obj_array[ak.argsort(obj_array[field_to_slice_by], ascending=False)]
        # Slice window: [start : start + count]
        sliced_obj_array = sorted_obj_array[:, start : start + count]
        events[obj] = sliced_obj_array

    return events


def _boolean_field_mask(particles: ak.Array, field: str, obj: str, cut_name: str) -> ak.Array:
    """
    Return ``particles[field]`` as a boolean mask, for the generic
    ``bool_require``/``bool_any_of`` object-level cut types (implementation
    task 4).

    Accepts a genuinely boolean field as-is, or an integer field whose only
    values are 0/1 (documented explicitly, e.g. a field read as ``uint8``
    that is semantically boolean). Anything else -- a non-boolean dtype, or
    an integer field with other values (e.g. ``cutBased``'s 0-3 ordinal
    scale) -- is almost certainly a configuration mistake (silently
    truthy-casting a multi-valued field would quietly do the wrong thing),
    so it raises a clear error instead.

    Raises:
        ValueError: ``field`` is not present on ``particles`` (a
            configuration error, not a runtime KeyError deep in parsing --
            same style as the existing pt/eta/phi checks above), or its
            dtype/values aren't boolean or 0/1.
    """
    if not hasattr(particles, field):
        raise ValueError(f"{obj} is missing configured kinematic field '{field}' ({cut_name})")

    vals = getattr(particles, field)
    # ak.to_numpy's dtype reflects the field's own declared type even when
    # this particular batch has zero particles in it after upstream
    # filtering (a properly-typed empty slice keeps its dtype; only a
    # fresh, never-typed empty literal like ak.Array([[], []]) would fall
    # back to float64 -- not the case here, since `vals` always comes from
    # an already-typed parsed field).
    flat = ak.flatten(vals, axis=None)
    np_dtype = ak.to_numpy(flat).dtype

    if np_dtype.kind == "b":
        return ak.values_astype(vals, bool)

    if np_dtype.kind in ("i", "u"):
        uniq = set(np.unique(ak.to_numpy(flat)).tolist())
        if uniq.issubset({0, 1}):
            return ak.values_astype(vals, bool)
        raise ValueError(
            f"{obj}.{field} used in {cut_name} must be boolean or 0/1-valued, "
            f"got values {sorted(uniq)}"
        )

    raise ValueError(
        f"{obj}.{field} used in {cut_name} must be boolean-typed (or integer "
        f"0/1), got dtype {np_dtype}"
    )


def _kinematic_cuts_is_per_object(cuts: Optional[Dict]) -> bool:
    if not cuts:
        return False
    markers = (
        "Electrons", "Muons", "Jets", "BJets", "Photons", "Taus",
        "electrons", "muons", "jets", "bjets", "photons", "taus",
    )
    return any(k in cuts for k in markers)


def filter_events_by_kinematics(
    events: ak.Array,
    kinematic_cuts: Optional[Dict[str, Dict]],
) -> ak.Array:
    """
    Mask particles within each event by kinematics (and optional electron isolation).

    ``kinematic_cuts`` may be either:

    - **Per-object** (recommended): ``{"Electrons": {"pt": {"min": 25.0}, ...}, "Muons": {...}}``
      Keys must match ``events.fields`` (case-sensitive) or YAML-style names
      (``electrons``, …) — use :func:`map_yaml_kinematic_cuts_to_objects` first.

    - **Legacy (same cuts for every collection)**: ``{"pt": {"min": ...}, "eta": {...}}``
      Applied to every particle array that has the corresponding attributes.
    """
    if not kinematic_cuts:
        return events

    if _kinematic_cuts_is_per_object(kinematic_cuts):
        cuts_by_obj = kinematic_cuts
    else:
        cuts_by_obj = {obj: kinematic_cuts for obj in events.fields}

    filtered_events = {}
    for obj in events.fields:
        particles = events[obj]
        cuts = cuts_by_obj.get(obj)
        if cuts is None:
            for alt in (obj.lower(), obj.capitalize()):
                if alt in cuts_by_obj:
                    cuts = cuts_by_obj[alt]
                    break

        if len(particles.fields) == 0:
            filtered_events[obj] = particles
            continue

        mask_by = None
        if hasattr(particles, "pt"):
            mask_by = particles.pt
        elif len(particles) > 0:
            mask_by = ak.ones_like(ak.num(particles), dtype=bool)
        else:
            mask_by = ak.Array([], dtype=bool)
        mask = ak.ones_like(mask_by, dtype=bool)

        if cuts is None:
            filtered_events[obj] = particles
            continue

        if "pt" in cuts and not hasattr(particles, "pt"):
            raise ValueError(f"{obj} is missing configured kinematic field 'pt'")
        if "pt" in cuts:
            pt_vals = ak.values_astype(particles.pt, float)
            mask = mask & (pt_vals >= cuts["pt"]["min"])

        if "eta" in cuts and not hasattr(particles, "eta"):
            raise ValueError(f"{obj} is missing configured kinematic field 'eta'")
        if "eta" in cuts:
            eta_vals = ak.values_astype(particles.eta, float)
            mask = mask & (eta_vals >= cuts["eta"]["min"]) & (eta_vals <= cuts["eta"]["max"])

        if "phi" in cuts and not hasattr(particles, "phi"):
            raise ValueError(f"{obj} is missing configured kinematic field 'phi'")
        if "phi" in cuts:
            phi_vals = ak.values_astype(particles.phi, float)
            mask = mask & (phi_vals >= cuts["phi"]["min"]) & (phi_vals <= cuts["phi"]["max"])

        if obj == "Electrons" and cuts.get("rel_isolation_max") is not None:
            iso_name = consts.ELECTRON_REL_ISOLATION_FIELD
            if hasattr(particles, iso_name):
                iso = getattr(particles, iso_name)
                pt_vals = ak.values_astype(particles.pt, float)
                iso_vals = ak.values_astype(iso, float)
                rel = iso_vals / ak.where(pt_vals > 0, pt_vals, np.inf)
                mask = mask & (rel < float(cuts["rel_isolation_max"]))
            else:
                raise ValueError(
                    f"Electron rel_isolation_max requires missing field {iso_name!r}"
                )

        # "all of these boolean fields must be True" -- e.g. CMS photon ID:
        # {"bool_require": ["electronVeto", "mvaID_WP90"]}. Implementation
        # task 4, generic (not CMS-specific): any collection/field.
        if "bool_require" in cuts:
            for field in cuts["bool_require"]:
                mask = mask & _boolean_field_mask(particles, field, obj, "bool_require")

        # "at least one of these boolean fields must be True" -- e.g. the
        # CMS photon barrel/endcap supercluster-eta acceptance flags:
        # {"bool_any_of": ["isScEtaEB", "isScEtaEE"]}. A photon in the
        # 1.4442-1.566 gap has neither flag set, so this excludes the gap.
        if "bool_any_of" in cuts:
            fields = cuts["bool_any_of"]
            any_mask = None
            for field in fields:
                field_mask = _boolean_field_mask(particles, field, obj, "bool_any_of")
                any_mask = field_mask if any_mask is None else (any_mask | field_mask)
            mask = mask & any_mask

        # Generic momentum-|eta| exclusion window: {"eta_exclude": {"min":
        # ..., "max": ...}}. NOT the CMS supercluster-eta acceptance gap --
        # see docs/CMS_KNOWN_LIMITATIONS.md's explicit warning; use
        # bool_any_of with isScEtaEB/isScEtaEE for that instead.
        if "eta_exclude" in cuts and not hasattr(particles, "eta"):
            raise ValueError(f"{obj} is missing configured kinematic field 'eta' (eta_exclude)")
        if "eta_exclude" in cuts:
            abs_eta = np.abs(ak.values_astype(particles.eta, float))
            excl = cuts["eta_exclude"]
            mask = mask & ~((abs_eta >= excl["min"]) & (abs_eta <= excl["max"]))

        # Boolean mask (not ak.mask) so dropped particles do not appear in lists
        filtered_events[obj] = particles[mask]

    return ak.zip(filtered_events, depth_limit=1)
