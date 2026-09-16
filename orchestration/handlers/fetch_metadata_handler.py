"""
FetchMetadataHandler - Handles metadata fetching state.
Fetches file URLs from ATLAS Open Data API.
"""
from typing import Optional

from orchestration.context import PipelineContext
from orchestration.states import PipelineState
from .base import StateHandler
from services.metadata.fetcher import MetadataFetcher, _classify_url, _classify_cms_url, UrlType
from services.metadata.cache import MetadataCache
from services.parsing.schemas import RECORD_ID_TO_SCHEMA


def _cms_record_id(key: str) -> Optional[int]:
    """Returns the record id if `key` is a "record_<id>" cache key for a
    registered CMS record (schema "cms-nanoaod"), else None. CMS record
    keys carry no "_mc" naming convention the way ATLAS release-year keys
    do (services.metadata.fetcher.fetch_by_record_ids never appends "_mc"
    to a CMS key, whether the record is data or simulation) -- this is
    how _validate_cache_or_abort tells a CMS key apart from an ATLAS one,
    rather than guessing from the key's own spelling."""
    if not key.startswith("record_"):
        return None
    try:
        record_id = int(key.split("_", 1)[1])
    except (ValueError, IndexError):
        return None
    if RECORD_ID_TO_SCHEMA.get(record_id) != "cms-nanoaod":
        return None
    return record_id


def _cms_key_violations(key: str, urls: list) -> list:
    """For a CMS record key: classify every URL by its own EOS path
    (_classify_cms_url) and require ALL of them to agree on one type --
    the record's "type" is whatever its own URLs consistently indicate
    (DoubleEG's two records are all-data, all 6 signal records are
    all-simulation -- verified against the real file lists in
    studies/hgg_cms/impl_checks/record_schema_evidence.json), not a
    naming convention on the key. Returns a list of violation
    description strings (empty if the key is internally consistent)."""
    violations = []
    expected_type = None
    for url in urls:
        try:
            url_type = _classify_cms_url(url)
        except ValueError as e:
            violations.append(f"  Key '{key}': {e}")
            continue
        if expected_type is None:
            expected_type = url_type
        elif url_type != expected_type:
            violations.append(
                f"  Key '{key}': mixed URL types -- first URL classified as "
                f"{expected_type.value}, but this URL classified as "
                f"{url_type.value}: {url}"
            )
        if len(violations) >= 5:
            break
    return violations


class FetchMetadataHandler(StateHandler):

    def __init__(
        self,
        metadata_fetcher: MetadataFetcher,
        metadata_cache: MetadataCache
    ):
        super().__init__()
        self.fetcher = metadata_fetcher
        self.cache = metadata_cache

    def handle(self, context: PipelineContext) -> tuple[PipelineContext, PipelineState]:
        self._log_state_entry(context)

        parsing_config = context.config.parsing_config
        if not parsing_config:
            next_state = self._determine_next_state(context)
            self._log_state_exit(context, next_state)
            return context, next_state

        metadata = self.cache.load()

        if metadata:
            self.logger.info(f"Loaded metadata from cache: {self.cache.cache_path}")

            # ── CHANGE 6: Validate cache integrity before using it ────────────
            # BEFORE: cache was used immediately after loading with no checks.
            # A cache built with parse_mc=False contains MC urls in data keys,
            # which causes MC events to be parsed as collision data silently.
            #
            # AFTER: validate and abort with a clear error if contaminated.
            self._validate_cache_or_abort(metadata)
            # ── END CHANGE 6 ─────────────────────────────────────────────────

        else:
            self.logger.info("Cache miss, fetching metadata from API...")

            # ── CHANGE 7: Remove `separate_mc` argument from fetcher call ─────
            # BEFORE:
            #     metadata = self.fetcher.fetch(
            #         release_years=...,
            #         record_ids=...,
            #         separate_mc=parsing_config.parse_mc   # <-- removed
            #     )
            # AFTER: separation always happens inside fetcher.fetch()
            metadata = self.fetcher.fetch(
                release_years=[y.replace("_mc", "") for y in parsing_config.release_years] if parsing_config.release_years else None,
                record_ids=list(parsing_config.specific_record_ids) if parsing_config.specific_record_ids else None,
            )
            # ── END CHANGE 7 ─────────────────────────────────────────────────

            try:
                self.cache.save(metadata)
            except TimeoutError as e:
                self.logger.warning(f"Could not save to cache: {e}")

        total_files = sum(len(urls) for urls in metadata.values())
        self.logger.info(
            f"Fetched metadata: {len(metadata)} release year(s), {total_files} total files"
        )

        updated_context = context.with_metadata(metadata)
        next_state = self._determine_next_state(updated_context)
        self._log_state_exit(context, next_state)
        return updated_context, next_state

    # ── CHANGE 8: Add cache validation method ────────────────────────────────
    def _validate_cache_or_abort(self, metadata: dict) -> None:
        """
        Validate that no MC URLs are in data keys and vice versa.

        Raises RuntimeError with a clear message if contamination is found,
        rather than silently proceeding with bad data.

        To fix a contaminated cache: delete the cache file and re-run.
        The fetcher will rebuild it correctly with the patched _separate_mc_files.

        CMS record keys ("record_<id>" for a registered cms-nanoaod
        record) are validated separately (_cms_key_violations, using
        _classify_cms_url's EOS-path classification): ATLAS's "_mc"-
        suffix key-naming convention does not apply to them at all
        (fetch_by_record_ids never appends "_mc" to a CMS key, whether
        the record is data or simulation), so running them through
        _classify_url's RUCIO-namespace logic would reject every valid
        CMS URL as unclassifiable -- confirmed live: this is exactly what
        made the first D3 cluster job (which pins its one file via a
        pre-written cache, i.e. a cache HIT) abort on a perfectly valid
        CMS DoubleEG URL. Every other key (ATLAS release-year keys) keeps
        EXACTLY the prior _classify_url/"_mc"-suffix logic, unchanged.
        """
        contaminated_keys = []

        for key, urls in metadata.items():
            if _cms_record_id(key) is not None:
                contaminated_keys.extend(_cms_key_violations(key, urls))
                if len(contaminated_keys) >= 5:
                    break
                continue

            is_mc_key = key.endswith("_mc")
            for url in urls:
                try:
                    url_type = _classify_url(url)
                except ValueError:
                    contaminated_keys.append(
                        f"  Key '{key}': unclassifiable URL: {url}"
                    )
                    continue

                if is_mc_key and url_type != UrlType.MC:
                    contaminated_keys.append(
                        f"  Key '{key}' (MC key): contains DATA url: {url}"
                    )
                elif not is_mc_key and url_type != UrlType.DATA:
                    contaminated_keys.append(
                        f"  Key '{key}' (data key): contains MC url: {url}"
                    )

                # Stop scanning after first 5 violations — enough to diagnose
                if len(contaminated_keys) >= 5:
                    break
            if len(contaminated_keys) >= 5:
                break

        if contaminated_keys:
            raise RuntimeError(
                f"Contaminated metadata cache detected at: {self.cache.cache_path}\n"
                f"MC and data URLs are mixed. This cache was built with parse_mc=False.\n"
                f"Fix: delete the cache file and re-run to rebuild it.\n"
                f"First violations found:\n"
                + "\n".join(contaminated_keys)
            )

        self.logger.info("Cache integrity check passed — no cross-contamination.")
    # ── END CHANGE 8 ─────────────────────────────────────────────────────────
