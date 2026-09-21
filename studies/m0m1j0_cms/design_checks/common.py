"""
m0m1j0 BumpNet design phase -- shared helpers for the small, read-only
design_checks scripts (Phase 0 of the m0m1j0 design task). NOT part of
the shared pipeline: nothing here is imported by services/, domain/, or
any config -- these are standalone scripts under studies/m0m1j0_cms/
only, per this phase's hard scope rule.

Data-access note (documented here since it isn't obvious): the group's
usual access path for CMS Open Data is XRootD (root://eospublic.cern.ch/...),
via the shared pipeline's own metadata fetcher. On this design machine
(Windows, no prebuilt XRootD python bindings, and `pip install xrootd`
fails without a C++ build toolchain / CMake), that path is not available.
Instead, this module reads the SAME EOS-hosted files over HTTPS, using
the EOS/XRootD gateway's own HTTP(S) interface (confirmed live: the
server identifies itself as "XrootD/5.9.5" and serves HTTP GET with
Accept-Ranges: bytes -- i.e. genuine byte-range streaming, not a
one-shot download). The gateway's TLS certificate chain includes a
self-signed certificate in this environment, so certificate verification
is disabled FOR THIS READ-ONLY ACCESS TO PUBLIC, NON-SENSITIVE CMS OPEN
DATA ONLY. This is not used anywhere in the shared pipeline and should
not be copied there without separately deciding whether it's acceptable
for that context.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import aiohttp
import numpy as np
import requests
import uproot

CMS_RECID_FILEPAGE_URL = "https://opendata.cern.ch/record/{0}/filepage/1?group=1"

HERE = Path(__file__).resolve().parent
PLOTS_DIR = HERE / "plots"


async def _get_client_no_ssl_verify(**kwargs):
    """uproot/fsspec `get_client` override: build the aiohttp session's
    TCPConnector with ssl=False INSIDE the running event loop (aiohttp's
    TCPConnector requires a running loop at construction time in this
    aiohttp version, so it cannot be built ahead of time in sync code)."""
    kwargs.pop("connector", None)
    connector = aiohttp.TCPConnector(ssl=False)
    return aiohttp.ClientSession(connector=connector, **kwargs)


def open_root_https(url: str):
    """Open a root://eospublic.cern.ch//... URI's HTTPS-gateway equivalent
    with uproot, TLS verification disabled per this module's docstring.
    Accepts either a root:// URI (rewritten to https://) or an already-
    https:// URL."""
    if url.startswith("root://eospublic.cern.ch/"):
        https_url = "https://eospublic.cern.ch/" + url.split("root://eospublic.cern.ch//", 1)[1]
    elif url.startswith("https://"):
        https_url = url
    else:
        raise ValueError(f"Unrecognized URL scheme for {url!r}")
    return uproot.open(https_url, get_client=_get_client_no_ssl_verify)


def fetch_file_list(record_id: int) -> list[str]:
    """The CERN Open Data portal's own file list for a record, exactly as
    the shared pipeline's services/metadata/fetcher.py::_fetch_files_for_record
    does it (same URL template, same JSON path) -- read-only HTTP GET
    against the public portal API, not the shared pipeline code itself
    (kept standalone per this phase's hard scope rule: no imports from
    services/ into studies/m0m1j0_cms/)."""
    url = CMS_RECID_FILEPAGE_URL.format(record_id)
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    data = json.loads(r.text)
    files = []
    for index_file in data["index_files"]["files"]:
        for file_entry in index_file["files"]:
            files.append(file_entry["uri"])
    return files


def https_head(root_uri: str) -> dict:
    """HEAD request (no body) for a root:// URI's HTTPS-gateway
    equivalent -- gets Content-Length (file size) without downloading."""
    https_url = "https://eospublic.cern.ch/" + root_uri.split("root://eospublic.cern.ch//", 1)[1]
    r = requests.head(https_url, timeout=30, verify=False)
    return {"status": r.status_code, "headers": dict(r.headers)}


def to_native(obj):
    """Recursively convert numpy scalar/array types to plain Python types
    for JSON serialization."""
    if isinstance(obj, dict):
        return {k: to_native(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [to_native(v) for v in obj]
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        return float(obj)
    if isinstance(obj, np.ndarray):
        return to_native(obj.tolist())
    if isinstance(obj, np.bool_):
        return bool(obj)
    return obj


def write_json(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(to_native(data), indent=2), encoding="utf-8")
    print(f"wrote {path}")
