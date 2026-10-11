#!/usr/bin/env python
"""
The official CMS pileup weights for 2016 postVFP UL, evaluated without
correctionlib.

Source (Part A1), downloaded on the cluster and never hand-edited:

    https://opendata.cern.ch/eos/opendata/cms/corrections/jsonpog-integration-2016post.tar
      -> POG/LUM/2016postVFP_UL/puWeights.json.gz
         correction "Collisions16_UltraLegacy_goldenJSON", version 0
         input  NumTrueInteractions, real, [0, 99), flow = clamp
         input  weights, string, one of {nominal, up, down}
         output weight, real

`correctionlib` is not installed in the shared conda environment, and this
study is not allowed to modify that environment, so the file is read
directly. The only node types involved are a `category` on the variation
string and a `binning` with uniform unit-width edges and `flow: "clamp"`,
which is exactly what `np.searchsorted` plus a clip reproduces. The test in
`tests/test_pu_weights.py` checks that reproduction against values read
straight out of the JSON.

Nothing here is invented, hand-typed or taken from a forum: every number
comes out of the official file at run time.
"""
from __future__ import annotations

import gzip
import json
import pathlib

import numpy as np

CORRECTION_NAME = "Collisions16_UltraLegacy_goldenJSON"
SOURCE_URL = ("https://opendata.cern.ch/eos/opendata/cms/corrections/"
              "jsonpog-integration-2016post.tar")
SOURCE_MEMBER = "POG/LUM/2016postVFP_UL/puWeights.json.gz"
# The era the official file covers. Our data is Run2016 G+H, which is a
# SUBSET of postVFP, so using this profile is an approximation -- see
# `provenance()`.
ERA = "2016postVFP_UL"


class PileupWeights:
    """Official pileup weight as a function of Pileup_nTrueInt."""

    def __init__(self, path: str | pathlib.Path):
        self.path = pathlib.Path(path)
        with gzip.open(self.path, "rt") as fh:
            payload = json.load(fh)
        corrections = {c["name"]: c for c in payload["corrections"]}
        if CORRECTION_NAME not in corrections:
            raise SystemExit(
                f"{self.path}: no correction named {CORRECTION_NAME!r}; "
                f"found {sorted(corrections)}")
        correction = corrections[CORRECTION_NAME]
        self.version = correction.get("version")
        node = correction["data"]
        if node["nodetype"] != "category" or node["input"] != "weights":
            raise SystemExit(
                f"{self.path}: unexpected top node {node['nodetype']!r} on "
                f"{node.get('input')!r}; this reader only handles the official "
                "category-on-variation layout.")
        self._edges: dict[str, np.ndarray] = {}
        self._content: dict[str, np.ndarray] = {}
        for item in node["content"]:
            binning = item["value"]
            if binning["nodetype"] != "binning":
                raise SystemExit(
                    f"{self.path}: variation {item['key']!r} is a "
                    f"{binning['nodetype']!r} node, not a binning.")
            if binning["input"] != "NumTrueInteractions":
                raise SystemExit(
                    f"{self.path}: variation {item['key']!r} bins on "
                    f"{binning['input']!r}, not NumTrueInteractions.")
            if binning.get("flow") != "clamp":
                raise SystemExit(
                    f"{self.path}: variation {item['key']!r} has flow="
                    f"{binning.get('flow')!r}; this reader implements 'clamp' only.")
            self._edges[item["key"]] = np.asarray(binning["edges"], dtype=np.float64)
            self._content[item["key"]] = np.asarray(binning["content"], dtype=np.float64)
        for needed in ("nominal", "up", "down"):
            if needed not in self._content:
                raise SystemExit(f"{self.path}: missing variation {needed!r}")

    @property
    def variations(self) -> list[str]:
        return sorted(self._content)

    def edges(self, variation: str = "nominal") -> np.ndarray:
        return self._edges[variation]

    def content(self, variation: str = "nominal") -> np.ndarray:
        return self._content[variation]

    def __call__(self, n_true_int, variation: str = "nominal") -> np.ndarray:
        """Weight per event. `flow: clamp` means values below the first edge
        take the first bin and values at or above the last edge take the last
        bin, which is what the clip below does."""
        if variation not in self._content:
            raise SystemExit(
                f"unknown variation {variation!r}; have {self.variations}")
        edges = self._edges[variation]
        content = self._content[variation]
        x = np.asarray(n_true_int, dtype=np.float64)
        idx = np.searchsorted(edges, x, side="right") - 1
        idx = np.clip(idx, 0, len(content) - 1)
        return content[idx]

    def provenance(self) -> dict:
        nominal = self._content["nominal"]
        return {
            "correction": CORRECTION_NAME,
            "version": self.version,
            "era_of_the_official_file": ERA,
            "source_url": SOURCE_URL,
            "source_member": SOURCE_MEMBER,
            "local_path": str(self.path),
            "input": "Pileup_nTrueInt (NumTrueInteractions)",
            "n_bins": int(len(nominal)),
            "range": [float(self._edges["nominal"][0]),
                      float(self._edges["nominal"][-1])],
            "flow": "clamp",
            "variations": self.variations,
            "weight_min": float(nominal.min()),
            "weight_max": float(nominal.max()),
            "APPROXIMATION": (
                "The official file covers the whole 2016 postVFP period. Our "
                "data is Run2016 G+H, a subset of postVFP (16.393 fb^-1 of the "
                "postVFP total). Using it is therefore an approximation of the "
                "G+H pileup profile, not an exact match. It is the finest "
                "granularity published."),
            "derivation": (
                "Official CMS LUM POG weights, derived from the golden JSON "
                "with the standard minimum-bias cross section and the UL16 MC "
                "pileup profile as denominator. Taken as published; nothing "
                "here recomputes or edits it."),
        }


def load(path: str | pathlib.Path) -> PileupWeights:
    return PileupWeights(path)
