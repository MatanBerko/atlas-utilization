"""
FileParser service - Single responsibility: Parse ROOT files.

Extracts events from ATLAS ROOT files using uproot.
No orchestration logic, no state management.
"""

import logging
import time
import awkward as ak
import numpy as np
import itertools
from typing import Callable, Optional

from services.parsing import schemas
from services.parsing.root_io import open_root_file
from services import consts


class PartialFileReadError(RuntimeError):
    """A ROOT file failed after a usable prefix of its events was parsed."""

    def __init__(self, file_path: str, events: ak.Array, read_error: Exception):
        self.file_path = file_path
        self.events = events
        self.read_error = read_error
        super().__init__(
            f"ROOT read failed for {file_path}: {read_error}; "
            f"retaining {len(events)} events parsed before the failure"
        )


class RequiredScalarBranchMissingError(ValueError):
    """A declared scalar branch group (e.g. "Trigger", "EventIds", or any
    ``extra_scalar_branches`` group) is missing one or more of its declared
    branches in one or more input files.

    Subclasses ``ValueError`` (the type this replaces at the raise site
    below) so any existing code or test that catches/asserts ``ValueError``
    is unaffected; the distinct subclass lets ``FileParser.parse_file`` and
    ``ThreadedFileProcessor.process_files`` deliberately NOT swallow this
    one as an ordinary per-file parse failure (implementation task 3, Part
    B3 -- "loud failure for missing required branches", as opposed to e.g. a
    network error, which keeps today's silent-skip-and-log behaviour
    exactly).

    ``failures`` is a list of ``(file_path, group_name, missing_branches)``
    tuples -- usually one entry (raised at a single file), but
    ``ThreadedFileProcessor.process_files`` aggregates every such error seen
    while parsing one record into a single instance with multiple entries,
    so one clear error lists every affected file, not just the first.
    """

    def __init__(self, failures: list[tuple[str, str, list[str]]]):
        self.failures = list(failures)
        lines = [
            f"  {file_path}: scalar branch group '{group_name}' is missing "
            f"required branch(es) {sorted(missing)}"
            for file_path, group_name, missing in self.failures
        ]
        super().__init__(
            f"Required scalar branch(es) missing from {len(self.failures)} "
            f"file(s); refusing to continue silently with those file(s) "
            f"skipped:\n" + "\n".join(lines)
        )


class RequiredObjectFieldMissingError(RequiredScalarBranchMissingError):
    """A per-object (jagged, one-value-per-particle) field requested via
    ``extra_object_fields`` (implementation task 4) is missing from one or
    more files' declared object collection -- e.g. ``Photon_electronVeto``
    requested but not readable in this particular file.

    Subclasses ``RequiredScalarBranchMissingError`` on purpose: it is caught
    by exactly the same "do not swallow, abort the run" handling already in
    ``FileParser.parse_file`` and ``ThreadedFileProcessor.process_files``
    (implementation task 3), with no changes needed to either. ``failures``
    entries use the collection name (e.g. ``"Photons"``) as the "group
    name", for a message consistent in shape with the scalar-group case.
    """


class FileParser:
    """
    Service for parsing individual ROOT files.
    
    Pure function-like service with no state. All methods are static.
    """
    
    @staticmethod
    def parse_file(
        file_path: str,
        tree_names: list[str],
        release_year: str,
        batch_size: int = 40_000,
        enable_jet_tagging: bool = False,
        jet_btagging_thresholds: Optional[dict[str, float]] = None,
        extra_scalar_branches: Optional[dict[str, list[str]]] = None,
        extra_object_fields: Optional[dict[str, list[str]]] = None,
        read_event_weights: bool = False,
        read_pileup_info: bool = False,
        on_probe_retry: Optional[Callable[[], None]] = None,
        on_probe_final_failure: Optional[Callable[[str], None]] = None,
    ) -> Optional[ak.Array]:
        """
        Parse a single ROOT file and return events.

        Args:
            file_path: Path or URI to ROOT file
            tree_names: List of possible tree names to search for
            release_year: Release year identifier (e.g., "2024r-pp")
            batch_size: Number of entries to process per batch
            extra_scalar_branches: Optional extra scalar (per-event, not
                per-particle) branch groups to read on top of whatever the
                schema already declares, e.g.
                ``{"Trigger": ["HLT_SomeBit"]}``. Merged with the schema's
                own groups (see ``schemas.get_scalar_branch_groups``);
                absent/``None`` reproduces today's behaviour exactly.
            extra_object_fields: Optional extra per-object (jagged,
                one-value-per-particle) fields to read on top of whatever
                the schema's default field list for that collection
                already declares, e.g. ``{"Photons": ["electronVeto",
                "mvaID_WP90"]}``. Merged with the schema's own default list
                (see ``_resolve_object_fields``); absent/``None`` reproduces
                today's behaviour exactly (implementation task 4).
            read_event_weights: Optional (default False). Adds the
                per-event ``genWeight`` scalar field -- simulation only;
                raises if this file looks like real data (implementation
                task 5, see ``services.parsing.mc_weights``).
            read_pileup_info: Optional (default False). Adds ``PV_npvsGood``
                (data and simulation) and, for simulation files only,
                ``Pileup_nTrueInt`` (implementation task 5).
            on_probe_retry: Optional callback(), invoked once per branch-
                accessibility-probe retry (implementation task 5, Part B);
                purely additive statistics, no effect on parsing.
            on_probe_final_failure: Optional callback(branch_name), invoked
                once per branch whose probe still fails after every retry.

        Returns:
            Awkward array of events with particle objects, or None if parsing failed
        """
        try:
            with open_root_file(file_path) as root_file:
                return FileParser._parse_opened_file(
                    root_file,
                    tree_names,
                    release_year,
                    batch_size,
                    file_path,
                    enable_jet_tagging,
                    jet_btagging_thresholds,
                    extra_scalar_branches=extra_scalar_branches,
                    extra_object_fields=extra_object_fields,
                    read_event_weights=read_event_weights,
                    read_pileup_info=read_pileup_info,
                    on_probe_retry=on_probe_retry,
                    on_probe_final_failure=on_probe_final_failure,
                )
        except PartialFileReadError:
            raise
        except RequiredScalarBranchMissingError:
            raise
        except Exception as e:
            logging.warning(f"Failed to parse file {file_path}: {e}")
            return None

    @staticmethod
    def _parse_opened_file(
        root_file,
        tree_names: list[str],
        release_year: str,
        batch_size: int,
        file_path: str,
        enable_jet_tagging: bool,
        jet_btagging_thresholds: Optional[dict[str, float]],
        extra_scalar_branches: Optional[dict[str, list[str]]] = None,
        extra_object_fields: Optional[dict[str, list[str]]] = None,
        read_event_weights: bool = False,
        read_pileup_info: bool = False,
        on_probe_retry: Optional[Callable[[], None]] = None,
        on_probe_final_failure: Optional[Callable[[str], None]] = None,
    ) -> Optional[ak.Array]:
        """Parse an already-opened ROOT file."""
        tree_name = FileParser._get_data_tree_name(root_file.keys(), tree_names)
        tree = root_file[tree_name]
        all_tree_branches = set(tree.keys())
        n_entries = tree.num_entries

        # Simulation weights / pileup info (implementation task 5): the
        # required field list depends on whether THIS file is data or
        # simulation (see services.parsing.mc_weights.file_is_simulation),
        # so it's resolved per file, then merged into whatever
        # extra_scalar_branches the caller already passed, and handled by
        # the exact same scalar-branch-group machinery as any other group
        # (accessibility gate, hard-fail-if-any-declared-branch-missing).
        if read_event_weights or read_pileup_info:
            from services.parsing.mc_weights import resolve_weight_and_pileup_groups

            mc_groups = resolve_weight_and_pileup_groups(
                all_tree_branches, file_path, read_event_weights, read_pileup_info
            )
            if mc_groups:
                merged_extra_scalar = dict(extra_scalar_branches or {})
                for group_name, branches in mc_groups.items():
                    merged_extra_scalar[group_name] = list(dict.fromkeys(
                        list(merged_extra_scalar.get(group_name, [])) + branches
                    ))
                extra_scalar_branches = merged_extra_scalar

        obj_branches = FileParser._extract_branches_by_schema(
            all_tree_branches,
            release_year,
            extra_scalar_branches=extra_scalar_branches,
            extra_object_fields=extra_object_fields,
        )

        if not obj_branches:
            logging.warning(f"No particles found in schema for file {file_path}")
            return None

        # Resolved independently of _extract_branches_by_schema's return value
        # (rather than having that method also return the group-name set) so
        # its signature/return type stays exactly what existing tests mock.
        scalar_groups = FileParser._resolve_scalar_groups(release_year, extra_scalar_branches)
        declared_group_names = frozenset(name for name, branches in scalar_groups.items() if branches)

        obj_branches = FileParser._filter_accessible_branches(
            tree, obj_branches, scalar_group_names=declared_group_names,
            file_path=file_path,
            on_probe_retry=on_probe_retry,
            on_probe_final_failure=on_probe_final_failure,
        )

        if not obj_branches:
            logging.warning(f"No accessible particles found in file {file_path}")
            return None

        # A field requested via extra_object_fields that turns out to be
        # inaccessible in THIS file is a hard error, not a silent drop --
        # matching task 3's scalar-group precedent (the object still passes
        # the pt/eta/phi accessibility gate above on its default fields
        # alone, so without this check a missing extra field would silently
        # vanish here with no error at all). Only the extra fields are
        # required in full; the schema's own default fields keep their
        # existing (gate-based, not all-or-nothing) accessibility handling.
        if extra_object_fields:
            obj_field_failures: list[tuple[str, str, list[str]]] = []
            for obj_name, declared_extra in extra_object_fields.items():
                actual_quantities = set(obj_branches.get(obj_name, {}).values())
                missing = sorted(set(declared_extra) - actual_quantities)
                if missing:
                    obj_field_failures.append((file_path, obj_name, missing))
            if obj_field_failures:
                raise RequiredObjectFieldMissingError(obj_field_failures)

        all_branches = set(itertools.chain.from_iterable(obj_branches.values()))
        obj_events, read_error = FileParser._read_file_in_batches(
            tree,
            all_branches,
            obj_branches,
            n_entries,
            batch_size
        )
        obj_events = FileParser._split_combined_leptons(obj_events, release_year)
        if enable_jet_tagging:
            obj_events = FileParser._calculate_btagging_and_split(obj_events, jet_btagging_thresholds)
        # Strip out DirectObjects -- they are not physics objects!
        if "DirectObjects" in obj_events.keys():
            obj_events.pop("DirectObjects")

        # Pull every declared scalar group's fields out before zipping the
        # object collections, then re-attach them as top-level scalar
        # columns. Kept after the physics objects so events.fields[0] is
        # still a particle collection (downstream selection code relies on
        # that). Generalizes the original EventIds-only logic to any number
        # of named scalar groups (see schemas.get_scalar_branch_groups).
        #
        # A group that was declared but ends up with any branch missing or
        # unreadable is a hard error, not a silent skip -- matching the
        # original EventIds behaviour (declared-but-unreadable de-dup keys
        # used to raise) and extending it to require the FULL declared set,
        # not just a non-empty subset, per-group.
        scalar_field_groups: dict[str, ak.Array] = {}
        for group_name in declared_group_names:
            group_fields = obj_events.pop(group_name, None)
            declared_branches = set(scalar_groups[group_name])
            actual_branches = set(group_fields.fields) if group_fields is not None else set()
            if actual_branches != declared_branches:
                missing = sorted(declared_branches - actual_branches)
                raise RequiredScalarBranchMissingError([(file_path, group_name, missing)])
            scalar_field_groups[group_name] = group_fields

        zipped = ak.zip(obj_events, depth_limit=1)

        for group_fields in scalar_field_groups.values():
            for field_name in group_fields.fields:
                zipped = ak.with_field(
                    zipped, group_fields[field_name], where=field_name
                )

        record_id = None
        if release_year.startswith("record_"):
            try:
                record_id = int(release_year.split("_")[1])
            except (ValueError, IndexError):
                record_id = None
        if record_id is not None:
            zipped = ak.with_field(
                zipped,
                np.full(len(zipped), record_id, dtype=np.int64),
                where="source_record",
            )

        if read_error is not None:
            raise PartialFileReadError(file_path, zipped, read_error) from read_error

        return zipped

    @staticmethod
    def _split_combined_leptons(
        obj_events: dict[str, ak.Array], release_year: str
    ) -> dict[str, ak.Array]:
        """Split legacy ``lep_*`` branches using their absolute PDG identifier."""
        normalized_release = schemas.normalize_release_year(release_year)
        if normalized_release not in {"2016e-8tev", "2025e-13tev-beta"}:
            return obj_events

        source = obj_events.get("Electrons")
        if source is None:
            source = obj_events.get("Muons")
        if source is None or "type" not in source.fields:
            raise ValueError(
                f"{normalized_release} combined lepton branches require lep_type"
            )

        abs_type = abs(source["type"])
        obj_events["Electrons"] = source[abs_type == 11]
        obj_events["Muons"] = source[abs_type == 13]
        return obj_events

    @staticmethod
    def _calculate_btagging_and_split(
        obj_events: dict[str, ak.Array],
        jet_btagging_thresholds: Optional[dict[str, float]]
    ) -> dict[str, ak.Array]:
        """
        For each Jet objects in each event, calculates the b-tagging discriminant.
        Then, decides if each jet is a bjet or not, using the per-algorithm threshold in `jet_btagging_thresholds`.
        If bjet, stores in obj_events["BJet"] and removes from obj_events["Jets"]. Otherwise, leaves the Jet be.
        """
        # TODO Find a cleaner way to determine if dealing with nanoAOD, PHYSLITE, etc.
        # TODO Maybe add an explicit check if the algorithm-specific threshold exists in the configuration dict before
        # accessing it. However, I'd rather fail parsing then give false physics data.
        if "Jets" not in obj_events or "DirectObjects" not in obj_events:
            # No jets to tag. Move on.
            return obj_events

        if "Jet_btagDeepFlavB" in obj_events["DirectObjects"].fields:
            # CMS: Discriminant is pre-calculated as the Jet_btagDeepFlavB field. Can change to a different algorithm if needed.
            # See https://cms-opendata-workshop.github.io/workshop2024-lesson-physics-objects/instructor/05-btagging.html
            is_bjet = obj_events["DirectObjects"]["Jet_btagDeepFlavB"] > jet_btagging_thresholds["Jet_btagDeepFlavB"]
        elif "BTagging_AntiKt4EMPFlowAuxDyn.DL1dv01_pb" in obj_events["DirectObjects"].fields:
            # ATLAS
            indices = obj_events["DirectObjects"]["AnalysisJetsAuxDyn.btaggingLink/AnalysisJetsAuxDyn.btaggingLink.m_persIndex"]
            pb = obj_events["DirectObjects"]["BTagging_AntiKt4EMPFlowAuxDyn.DL1dv01_pb"][indices]
            pc = obj_events["DirectObjects"]["BTagging_AntiKt4EMPFlowAuxDyn.DL1dv01_pc"][indices]
            pu = obj_events["DirectObjects"]["BTagging_AntiKt4EMPFlowAuxDyn.DL1dv01_pu"][indices]
            # DL1d score: log(pb / (fc*pc + (1-fc)*pu)), fc=0.018 is standard ATLAS.
            fc = 0.018

            # Handle edge cases where pb=0, or pc=pu=0.
            denominator = fc * pc + (1 - fc) * pu
            is_scoreable = (pb > 0) & (denominator > 0)
            dl1d = np.log(
                ak.where(is_scoreable, pb, 1.0) / ak.where(is_scoreable, denominator, 1.0)
            )
            # For now, if not scoreable -- assume jet.
            is_bjet = ak.where(
                is_scoreable,
                dl1d > jet_btagging_thresholds["DL1d"],
                False,
            )
        else:
            return obj_events
        obj_events["BJets"] = obj_events["Jets"][is_bjet]
        obj_events["Jets"] = obj_events["Jets"][~is_bjet]
        return obj_events
    
    @staticmethod
    def _get_data_tree_name(
        root_file_keys: list[str],
        possible_tree_names: list[str]
    ) -> str:
        if not possible_tree_names:
            return "CollectionTree"
        
        available_trees = [key[:-2] if key.endswith(';1') else key for key in root_file_keys]
        
        for tree_name in possible_tree_names:
            if tree_name in available_trees:
                return tree_name
        
        return "CollectionTree"
    
    @staticmethod
    def _resolve_scalar_groups(
        release_year: str,
        extra_scalar_branches: Optional[dict[str, list[str]]],
        record_id: Optional[int] = None,
    ) -> dict[str, list[str]]:
        """
        Combine the schema's own scalar branch groups (see
        ``schemas.get_scalar_branch_groups``) with caller-requested extra
        ones, validating that no group name or branch name collides with a
        physics-object collection name or another reserved top-level field.

        Called independently by both ``_extract_branches_by_schema`` (to
        know what to read) and ``_parse_opened_file`` (to know which
        ``obj_branches`` entries are scalar groups, for the accessibility-
        gate exemption and the missing-branch check) -- kept as its own
        pure, side-effect-free function rather than folded into either, so
        neither one's signature/return type has to change shape for
        existing callers (including a test that mocks
        ``_extract_branches_by_schema`` with a plain dict return value).

        Raises:
            ValueError: a requested group name or branch name collides with
                an existing physics-object collection name, "DirectObjects",
                or "source_record"; or the same branch name is requested by
                two different groups.
        """
        if release_year.startswith("record_") and record_id is None:
            try:
                record_id = int(release_year.split("_")[1])
            except (ValueError, IndexError):
                pass

        groups = schemas.get_scalar_branch_groups(release_year, record_id=record_id)

        try:
            schema_config = schemas.get_schema_for_release(release_year, record_id=record_id)
            object_names = set(schema_config.get("objects", {}).keys())
        except KeyError:
            object_names = set()

        if extra_scalar_branches:
            reserved_group_names = object_names | {"DirectObjects"}
            for group_name, branches in extra_scalar_branches.items():
                if group_name in reserved_group_names:
                    raise ValueError(
                        f"extra_scalar_branches group name '{group_name}' collides "
                        f"with an existing object collection or reserved name"
                    )
                merged = groups.get(group_name, [])
                groups[group_name] = list(dict.fromkeys(merged + list(branches)))

        reserved_field_names = object_names | {"DirectObjects", "source_record"}
        seen_branch_to_group: dict[str, str] = {}
        for group_name, branches in groups.items():
            for branch in branches:
                if branch in reserved_field_names:
                    raise ValueError(
                        f"scalar branch '{branch}' in group '{group_name}' collides "
                        f"with an existing object collection or reserved field name"
                    )
                existing_group = seen_branch_to_group.get(branch)
                if existing_group is not None and existing_group != group_name:
                    raise ValueError(
                        f"scalar branch '{branch}' is requested by both group "
                        f"'{existing_group}' and group '{group_name}' -- ambiguous "
                        f"top-level field name"
                    )
                seen_branch_to_group[branch] = group_name

        return groups

    @staticmethod
    def _resolve_object_fields(
        objects: dict[str, list[str]],
        extra_object_fields: Optional[dict[str, list[str]]],
    ) -> dict[str, list[str]]:
        """
        Merge caller-requested extra per-object (jagged, one-value-per-
        particle) fields into the schema's own default field list per
        collection, e.g. adding ``"electronVeto"`` to the default
        ``["pt", "eta", "phi", "mass"]`` for ``"Photons"``
        (implementation task 4).

        A field already in the default list is harmlessly de-duplicated,
        not an error. ``extra_object_fields`` naming a collection the
        schema doesn't declare at all (typo, or a collection this release
        genuinely doesn't have) is a hard configuration error.

        Returns a new dict (the schema's own ``objects`` dict is never
        mutated); absent/``None`` ``extra_object_fields`` returns the
        default list unchanged for every collection, reproducing today's
        behaviour exactly.

        Raises:
            ValueError: ``extra_object_fields`` references a collection
                name not present in ``objects``.
        """
        merged = {name: list(fields) for name, fields in objects.items()}
        if extra_object_fields:
            for obj_name, fields in extra_object_fields.items():
                if obj_name not in merged:
                    raise ValueError(
                        f"extra_object_fields references unknown collection "
                        f"'{obj_name}'; this schema declares: {sorted(merged)}"
                    )
                merged[obj_name] = list(dict.fromkeys(merged[obj_name] + list(fields)))
        return merged

    @staticmethod
    def _extract_branches_by_schema(
        tree_branches: set[str],
        release_year: str,
        extra_scalar_branches: Optional[dict[str, list[str]]] = None,
        extra_object_fields: Optional[dict[str, list[str]]] = None,
    ) -> dict[str, dict[str, str]]:
        """
        Extract branches by object based on release-specific schema.

        Returns:
            Dict mapping object names to their branch mappings
            Format: {obj_name: {full_branch: quantity, ...}}
        """
        try:
            record_id = None
            if release_year.startswith("record_"):
                try:
                    record_id = int(release_year.split("_")[1])
                except (ValueError, IndexError):
                    pass

            schema_config = schemas.get_schema_for_release(release_year, record_id=record_id)
        except KeyError:
            logging.warning(
                f"Release year '{release_year}' not found in schemas. "
                "Attempting auto-detection."
            )
            return FileParser._auto_detect_branches(tree_branches)

        obj_branches = {}
        objects = FileParser._resolve_object_fields(schema_config["objects"], extra_object_fields)
        direct_objects = schema_config.get("direct_objects", [])
        naming_pattern = schema_config.get("naming_pattern", "dotted")

        for obj_name, fields in objects.items():
            if naming_pattern == "flat":
                obj_branches_for_obj = FileParser._extract_flat_branches(
                    obj_name, fields, tree_branches, release_year
                )
            else:
                obj_branches_for_obj = FileParser._extract_dotted_branches(
                    obj_name, fields, tree_branches, release_year, schema_config
                )

            if obj_branches_for_obj:
                obj_branches[obj_name] = obj_branches_for_obj
        # Keep direct object names as-is, but store them under the "DirectObjects" key.
        obj_branches.update({"DirectObjects": {k: k for k in direct_objects}})
        # Scalar per-event branch groups (e.g. "EventIds": run/luminosityBlock/
        # event), read verbatim, one dict entry per group. Only added when the
        # schema (or the caller, via extra_scalar_branches) declares a
        # non-empty group, so releases/calls that declare none are unaffected.
        scalar_groups = FileParser._resolve_scalar_groups(release_year, extra_scalar_branches, record_id=record_id)
        for group_name, branches in scalar_groups.items():
            if branches:
                obj_branches[group_name] = {b: b for b in branches}
        return obj_branches
    
    @staticmethod
    def _prepare_obj_branch_name(
        obj_name: str,
        release_year: str = "2024r-pp",
        field: str = None,
        record_id: int = None
    ) -> str:
        """
        Prepare object branch name using release-specific template.

        For flat naming with a field, returns "ObjectName_field".
        For flat naming without a field, returns just the mapped object name.
        For dotted naming, returns "PrefixObjectSuffix".
        Falls back to ATLAS default naming on unknown releases.
        """
        try:
            if release_year.startswith("record_") and record_id is None:
                try:
                    record_id = int(release_year.split("_")[1])
                except (ValueError, IndexError):
                    pass

            schema = schemas.get_schema_for_release(release_year, record_id=record_id)
            naming_pattern = schema.get("naming_pattern", "dotted")
            object_mappings = schema.get("object_mappings", {})
            branch_obj_name = object_mappings.get(obj_name, obj_name)

            if naming_pattern == "flat":
                if field:
                    return f"{branch_obj_name}_{field}"
                return branch_obj_name
            else:
                prefix = schema["branch_prefix"]
                suffix = schema["branch_suffix"]
                return f"{prefix}{branch_obj_name}{suffix}"
        except KeyError:
            logging.warning(f"Release year '{release_year}' not found. Using default branch naming.")
            return "Analysis" + obj_name + "AuxDyn"

    @staticmethod
    def _find_cms_branches(
        base_branch_name: str,
        fields: list[str],
        obj_field_paths: dict,
        tree_branches: set[str]
    ) -> dict[str, str]:
        """
        Find CMS-style nested branches for a given object.

        CMS branch structure: {base}/{base}obj/{base}obj.{field_path}
        """
        branch_mappings = {}
        available_fields = []

        base_obj = f"{base_branch_name}obj"
        obj_container_patterns = [
            base_obj,
            f"{base_branch_name}/{base_obj}",
        ]
        has_obj_container = any(
            pattern in branch
            for branch in tree_branches
            for pattern in obj_container_patterns
        )
        if not has_obj_container:
            return {}

        for field in fields:
            if field not in obj_field_paths:
                continue

            field_path = obj_field_paths[field]
            field_indicator = consts.CMS_FIELD_INDICATORS.get(field)
            if not field_indicator:
                continue

            field_path_suffix = field_path[4:] if field_path.startswith("obj.") else field_path
            expected_path = f"{base_branch_name}/{base_obj}/{base_obj}.{field_path_suffix}"

            if expected_path in tree_branches:
                branch_mappings[expected_path] = field
                available_fields.append(field)
                continue

            matching = [
                branch for branch in tree_branches
                if branch.startswith(base_branch_name)
                and f"{base_obj}/" in branch
                and field_indicator in branch
            ]
            if matching:
                full_path = max(matching, key=len)
                branch_mappings[full_path] = field
                available_fields.append(field)
                continue

            field_selection_path = f"{base_obj}.{field_path_suffix}"
            branch_mappings[field_selection_path] = field
            available_fields.append(field)

        if FileParser._can_calculate_inv_mass(available_fields):
            return branch_mappings
        return {}

    @staticmethod
    def _extract_flat_branches(
        obj_name: str,
        fields: list[str],
        tree_branches: set[str],
        release_year: str
    ) -> dict[str, str]:
        """Extract branches using flat naming pattern (object_field)."""
        branch_base = FileParser._prepare_obj_branch_name(obj_name, release_year=release_year)
        available_fields = [
            f for f in fields if f"{branch_base}_{f}" in tree_branches
        ]
        
        if FileParser._can_calculate_inv_mass(available_fields):
            return {
                f"{branch_base}_{field}": field
                for field in available_fields
            }
        
        return {}
    
    @staticmethod
    def _extract_dotted_branches(
        obj_name: str,
        fields: list[str],
        tree_branches: set[str],
        release_year: str,
        schema_config: dict
    ) -> dict[str, str]:
        """Extract branches using dotted naming pattern (object.field)."""
        branch_name = FileParser._prepare_obj_branch_name(obj_name, release_year=release_year)
        logging.debug(f"ATLAS-style naming for {obj_name}, branch base: {branch_name}")
        
        field_paths = schema_config.get("field_paths", {})
        obj_field_paths = field_paths.get(obj_name, {})
        
        if obj_field_paths:
            return FileParser._find_cms_branches(
                branch_name, fields, obj_field_paths, tree_branches
            )
        
        branch_to_quantity = {}
        available_fields = []
        
        for field in fields:
            branch_full = f"{branch_name}.{field}"
            if branch_full in tree_branches:
                available_fields.append(field)
                branch_to_quantity[branch_full] = field
            elif field == "mass":
                mass_branch = f"{branch_name}.m"
                if mass_branch in tree_branches:
                    available_fields.append(field)
                    branch_to_quantity[mass_branch] = field
        
        if FileParser._can_calculate_inv_mass(available_fields):
            return branch_to_quantity
        
        return {}
    
    @staticmethod
    def _can_calculate_inv_mass(
        available_fields: list[str],
        ref_system: set[str] = {'phi', 'eta', 'pt'}
    ) -> bool:
        return ref_system.issubset(set(available_fields))
    
    # Backoff schedule for a per-branch accessibility probe retry
    # (implementation task 5, Part B). A constant, not a config key --
    # overridable only by tests, via _filter_accessible_branches's
    # retry_delays_sec parameter.
    _PROBE_RETRY_DELAYS_SEC: list[float] = [2.0, 5.0, 10.0]

    @staticmethod
    def _filter_accessible_branches(
        tree,
        obj_branches: dict[str, dict[str, str]],
        scalar_group_names: frozenset = frozenset(),
        file_path: str = "<unknown file>",
        retry_delays_sec: Optional[list[float]] = None,
        on_probe_retry: Optional[Callable[[], None]] = None,
        on_probe_final_failure: Optional[Callable[[str], None]] = None,
    ) -> dict[str, dict[str, str]]:
        """
        Test branch accessibility and filter out inaccessible ones.

        Reads ONE entry with ALL candidate branches at once to minimize
        HTTP round-trips for remote ROOT files.

        ``scalar_group_names`` (like ``"DirectObjects"``) are exempt from
        the physics-object pt/eta/phi accessibility requirement below --
        they're one-value-per-event branches, not particle collections, so
        that requirement doesn't apply to them. A scalar group that turns
        out to have zero accessible branches still passes through here
        (empty dict, same as today's "EventIds"); ``_parse_opened_file``
        is what turns that into a hard error, not this function.

        Implementation task 5, Part B: if the combined probe above fails
        and a branch is tested individually, two cases are now
        distinguished, instead of treating every read exception the same:

        1. The branch name simply isn't in the tree's own branch list
           (``tree.keys()``) -- genuinely absent. No retry (there is
           nothing to retry); unchanged from before.
        2. The branch name IS in the tree's branch list, but reading it
           raised anyway -- treated as a possibly-transient failure (this
           project's remote reads have shown exactly this kind of
           intermittent flakiness repeatedly). Retried with backoff
           (``retry_delays_sec``, default ``_PROBE_RETRY_DELAYS_SEC``) before
           finally giving up and logging a WARNING naming the file, branch,
           and final exception -- at which point the branch is treated as
           inaccessible, exactly as before this fix (this function's return
           value/behaviour for an ultimately-unreadable branch is
           unchanged; only a branch that *recovers* on retry now survives
           instead of being dropped after a single attempt).

        The successful path (the combined probe succeeding) is entirely
        unchanged: no retry logic is even reached, no extra reads happen.

        ``on_probe_retry``/``on_probe_final_failure`` are optional
        callbacks for purely additive statistics (implementation task 5,
        Part B: "count probe retries and final probe failures per file");
        absent (the default) does not change any branch-accessibility
        decision.
        """
        delays = retry_delays_sec if retry_delays_sec is not None else FileParser._PROBE_RETRY_DELAYS_SEC

        all_candidate_branches = []
        for branch_mapping in obj_branches.values():
            all_candidate_branches.extend(branch_mapping.keys())

        tree_branch_names = set(tree.keys())

        accessible_set = set()
        try:
            test_arr = tree.arrays(
                all_candidate_branches,
                entry_start=0, entry_stop=1,
                library="ak"
            )
            accessible_set = set(test_arr.fields)
        except Exception:
            for branch_path in all_candidate_branches:
                if branch_path not in tree_branch_names:
                    # Genuinely absent from this file's tree -- no retry,
                    # exactly today's behaviour.
                    continue

                last_exc: Optional[Exception] = None
                succeeded = False
                for attempt in range(len(delays) + 1):
                    try:
                        test_arr = tree.arrays(
                            branch_path,
                            entry_start=0, entry_stop=1,
                            library="ak"
                        )
                        if branch_path in test_arr.fields:
                            accessible_set.add(branch_path)
                        succeeded = True
                        break
                    except Exception as e:
                        last_exc = e
                        if attempt < len(delays):
                            if on_probe_retry is not None:
                                on_probe_retry()
                            time.sleep(delays[attempt])

                if not succeeded:
                    if on_probe_final_failure is not None:
                        on_probe_final_failure(branch_path)
                    logging.warning(
                        f"Branch accessibility probe failed for '{branch_path}' "
                        f"in {file_path} after {len(delays)} retr"
                        f"{'y' if len(delays) == 1 else 'ies'}: "
                        f"{type(last_exc).__name__}: {last_exc}. "
                        f"Treating this branch as inaccessible for this file."
                    )

        accessible_obj_branches = {}
        for obj_name, branch_mapping in obj_branches.items():
            accessible_branches = {
                bp: qty for bp, qty in branch_mapping.items()
                if bp in accessible_set
            }
            if accessible_branches and FileParser._can_calculate_inv_mass(
                list(accessible_branches.values())
            ) or obj_name == "DirectObjects" or obj_name in scalar_group_names:
                accessible_obj_branches[obj_name] = accessible_branches

        return accessible_obj_branches
    
    @staticmethod
    def _read_file_in_batches(
        tree,
        all_branches: set[str],
        obj_branches: dict[str, dict[str, str]],
        n_entries: int,
        batch_size: int
    ) -> tuple[dict[str, ak.Array], Optional[Exception]]:
        obj_events_by_quantities = {
            obj_name: [] for obj_name in obj_branches.keys()
        }
        read_error = None
        
        is_file_big = n_entries > batch_size
        if is_file_big:
            entry_ranges = [
                (start, min(start + batch_size, n_entries))
                for start in range(0, n_entries, batch_size)
            ]
        else:
            entry_ranges = [(0, n_entries)]
        
        for entry_start, entry_stop in entry_ranges:
            try:
                batch_data = tree.arrays(
                    all_branches,
                    entry_start=entry_start,
                    entry_stop=entry_stop,
                    library="ak"
                )
            except Exception as e:
                read_error = RuntimeError(
                    f"batch {entry_start}-{entry_stop} failed with "
                    f"{type(e).__name__}: {e}"
                )
                logging.warning("Stopping partial ROOT read: %s", read_error)
                break
            
            for obj_name, branch_mapping in obj_branches.items():
                available_branches = [
                    b for b in branch_mapping.keys() if b in batch_data.fields
                ]
                if available_branches:
                    subset = batch_data[available_branches]
                    if len(subset) > 0:
                        obj_events_by_quantities[obj_name].append(subset)
        
        result = {}
        for obj_name, chunks in obj_events_by_quantities.items():
            if chunks:
                concatenated = ak.concatenate(chunks)
                result[obj_name] = ak.zip({
                    quantity: concatenated[full_branch]
                    for full_branch, quantity in obj_branches[obj_name].items()
                })
        
        return result, read_error
    
    @staticmethod
    def _auto_detect_branches(tree_branches: set[str]) -> dict[str, dict[str, str]]:
        """
        Auto-detect branch structure when schema is not available.
        Attempts to find branches matching common patterns.
        """
        obj_branches = {}

        object_patterns = {
            "Electrons": ["Electron", "electron", "el"],
            "Muons": ["Muon", "muon", "mu"],
            "Jets": ["Jet", "jet"],
            "Photons": ["Photon", "photon", "gamma"],
            "Taus": ["Tau", "tau", "TauJet", "taujet"]
        }

        required_fields = ["pt", "eta", "phi"]

        for obj_name, patterns in object_patterns.items():
            for pattern in patterns:
                matching_branches = [b for b in tree_branches if pattern.lower() in b.lower()]

                if matching_branches:
                    base_branch = None
                    for branch in matching_branches:
                        parts = branch.split(".")
                        if len(parts) == 2:
                            potential_base = parts[0]
                            has_required = all(
                                f"{potential_base}.{field}" in tree_branches
                                for field in required_fields
                            )
                            if has_required:
                                base_branch = potential_base
                                break

                    if base_branch:
                        available_fields = []
                        for field in required_fields + ["mass"]:
                            if f"{base_branch}.{field}" in tree_branches:
                                available_fields.append(field)

                        if FileParser._can_calculate_inv_mass(available_fields):
                            obj_branches[obj_name] = {
                                f"{base_branch}.{field}": field
                                for field in available_fields
                            }
                        break

        return obj_branches
