#!/usr/bin/env python
"""
Official CMS UL2016 postVFP jet energy resolution, read straight from the
JME POG's published correction file. Nothing here is hand-typed.

Source (the same tarball the pileup study used, same sha256):
  https://opendata.cern.ch/eos/opendata/cms/corrections/jsonpog-integration-2016post.tar
  sha256 113730e8bd3e72ecb9548cb158c8990579022432d202416317828f4bce3eb28a
  member POG/JME/2016postVFP_UL/jet_jerc.json.gz
  corrections  Summer20UL16_JRV3_MC_PtResolution_AK4PFchs
               Summer20UL16_JRV3_MC_ScaleFactor_AK4PFchs

`correctionlib` is not in the shared conda environment and this study is not
allowed to modify that environment, so the JSON is read directly -- the same
approach, and the same defensive stance, as the pileup study's `pu_weights`:
the loader REFUSES to run if the file's node layout or formula is anything
other than the one implemented here. A silently wrong correction is worse
than no correction.

Resolution node layout, asserted at load time:
    binning(JetEta) -> binning(Rho) -> formula(TFormula, x = JetPt)
with the single expression
    sqrt([2]*abs([2])/(pc*pc) + [3]*[3]*pow(pc,[5]) + [4]*[4])
    where pc = max(min(x,[1]),[0])
Scale-factor node layout:
    binning(JetEta) -> category(systematic) -> float

Smearing follows the JME hybrid recipe: the scaling method when the jet has
a matched generator jet, the stochastic method otherwise.
"""
from __future__ import annotations

import gzip
import json
import pathlib

import numpy as np

RESOLUTION_NAME = "Summer20UL16_JRV3_MC_PtResolution_AK4PFchs"
SCALE_FACTOR_NAME = "Summer20UL16_JRV3_MC_ScaleFactor_AK4PFchs"

# the one expression this module knows how to evaluate, whitespace stripped
EXPECTED_RESOLUTION_EXPRESSION = (
    "sqrt([2]*abs([2])/(max(min(x,[1]),[0])*max(min(x,[1]),[0]))"
    "+[3]*[3]*pow(max(min(x,[1]),[0]),[5])+[4]*[4])"
)

# JME hybrid-method matching window: dR < R/2 for AK4, and the reco-gen
# difference within 3 sigma of the resolution.
GEN_MATCH_DR_MAX = 0.2
GEN_MATCH_NSIGMA = 3.0


class _Binning:
    """One `binning` node: edges plus whatever sits under each bin."""

    def __init__(self, node, expect_input):
        if node.get("nodetype") != "binning":
            raise ValueError(
                "expected a binning node, got {!r}".format(node.get("nodetype")))
        if node.get("input") != expect_input:
            raise ValueError("binning on {!r}, expected {!r}".format(
                node.get("input"), expect_input))
        self.edges = np.asarray(node["edges"], dtype=np.float64)
        self.content = node["content"]
        self.flow = node.get("flow")
        if not isinstance(self.flow, (int, float)):
            raise ValueError(
                "unsupported flow {!r} on the {} binning; this reader only "
                "implements a numeric flow value".format(self.flow, expect_input))

    def index(self, values):
        """Bin index per value; -1 marks out of range (the flow case)."""
        idx = np.searchsorted(self.edges, values, side="right") - 1
        out = (values < self.edges[0]) | (values >= self.edges[-1])
        idx = np.clip(idx, 0, len(self.edges) - 2)
        return np.where(out, -1, idx)


class JetResolution:
    """sigma(pT)/pT for AK4PFchs MC jets."""

    def __init__(self, node):
        self.eta = _Binning(node, "JetEta")
        self.rho = [_Binning(sub, "Rho") for sub in self.eta.content]
        self.params = []
        for rho_bin in self.rho:
            row = []
            for leaf in rho_bin.content:
                if leaf.get("nodetype") != "formula":
                    raise ValueError("resolution leaf is {!r}, not a formula"
                                     .format(leaf.get("nodetype")))
                expr = "".join(str(leaf["expression"]).split())
                if expr != EXPECTED_RESOLUTION_EXPRESSION:
                    raise ValueError(
                        "resolution formula is not the one this reader "
                        "implements:\n  file : {}\n  known: {}".format(
                            expr, EXPECTED_RESOLUTION_EXPRESSION))
                if leaf.get("variables") != ["JetPt"]:
                    raise ValueError("unexpected formula variables {!r}"
                                     .format(leaf.get("variables")))
                params = leaf["parameters"]
                if params is None or len(params) != 6:
                    raise ValueError("expected 6 formula parameters")
                row.append([float(v) for v in params])
            self.params.append(np.asarray(row, dtype=np.float64))
        self.last_flow_count = 0

    def __call__(self, eta, pt, rho):
        eta = np.asarray(eta, dtype=np.float64)
        pt = np.asarray(pt, dtype=np.float64)
        rho = np.asarray(rho, dtype=np.float64)
        out = np.full(eta.shape, np.nan, dtype=np.float64)
        n_flow = 0

        ieta = self.eta.index(eta)
        for ie in np.unique(ieta):
            sel = ieta == ie
            if ie < 0:
                out[sel] = float(self.eta.flow)
                n_flow += int(sel.sum())
                continue
            irho = self.rho[ie].index(rho[sel])
            sub = np.full(int(sel.sum()), np.nan)
            for ir in np.unique(irho):
                mask = irho == ir
                if ir < 0:
                    sub[mask] = float(self.rho[ie].flow)
                    n_flow += int(mask.sum())
                    continue
                p0, p1, p2, p3, p4, p5 = self.params[ie][ir]
                x = pt[sel][mask]
                pc = np.maximum(np.minimum(x, p1), p0)
                sub[mask] = np.sqrt(p2 * abs(p2) / (pc * pc)
                                    + p3 * p3 * np.power(pc, p5)
                                    + p4 * p4)
            out[sel] = sub
        self.last_flow_count = n_flow
        return out


class JetResolutionScaleFactor:
    """The data/MC resolution scale factor, per eta, per systematic."""

    def __init__(self, node):
        self.eta = _Binning(node, "JetEta")
        self.values = {}
        for key in ("nom", "up", "down"):
            row = []
            for leaf in self.eta.content:
                if (leaf.get("nodetype") != "category"
                        or leaf.get("input") != "systematic"):
                    raise ValueError(
                        "scale-factor leaf is not a category on 'systematic'")
                found = [c["value"] for c in leaf["content"] if c["key"] == key]
                if len(found) != 1:
                    raise ValueError(
                        "scale factor has no unique {!r} entry".format(key))
                row.append(float(found[0]))
            self.values[key] = np.asarray(row, dtype=np.float64)

    def __call__(self, eta, systematic="nom"):
        eta = np.asarray(eta, dtype=np.float64)
        idx = self.eta.index(eta)
        vals = self.values[systematic]
        out = np.where(idx < 0, float(self.eta.flow), vals[np.clip(idx, 0, None)])
        return out.astype(np.float64)


class JerSmearer:
    """The JME hybrid smearing, applied to MC jets only."""

    def __init__(self, json_gz_path):
        path = pathlib.Path(json_gz_path)
        with gzip.open(path, "rt", encoding="utf-8") as handle:
            payload = json.load(handle)
        by_name = {c["name"]: c for c in payload["corrections"]}
        for name in (RESOLUTION_NAME, SCALE_FACTOR_NAME):
            if name not in by_name:
                raise ValueError(
                    "{} has no correction named {!r}".format(path, name))
        self.source = str(path)
        self.resolution_name = RESOLUTION_NAME
        self.scale_factor_name = SCALE_FACTOR_NAME
        self.resolution = JetResolution(by_name[RESOLUTION_NAME]["data"])
        self.scale_factor = JetResolutionScaleFactor(
            by_name[SCALE_FACTOR_NAME]["data"])
        self.last_matched_fraction = float("nan")

    def factors(self, pt, eta, rho, gen_pt, has_gen, rng, systematic="nom"):
        """Per-jet multiplicative pT factor. Flat arrays in, flat array out.

        Scaling method where a generator jet is matched (the caller supplies
        `has_gen`, which must already carry the dR < 0.2 half of the match)
        and the reco-gen difference is within 3 sigma; stochastic elsewhere.
        Never negative.
        """
        pt = np.asarray(pt, dtype=np.float64)
        eta = np.asarray(eta, dtype=np.float64)
        rho = np.asarray(rho, dtype=np.float64)
        gen_pt = np.asarray(gen_pt, dtype=np.float64)
        has_gen = np.asarray(has_gen, dtype=bool)

        sigma = self.resolution(eta, pt, rho)
        sf = self.scale_factor(eta, systematic)

        matched = has_gen & (np.abs(pt - gen_pt) < GEN_MATCH_NSIGMA * sigma * pt)

        scaling = 1.0 + (sf - 1.0) * np.divide(
            pt - gen_pt, pt, out=np.zeros_like(pt), where=pt > 0)
        stochastic = 1.0 + rng.normal(0.0, sigma) * np.sqrt(
            np.maximum(sf * sf - 1.0, 0.0))

        factor = np.where(matched, scaling, stochastic)
        self.last_matched_fraction = (float(matched.mean())
                                      if matched.size else float("nan"))
        return np.maximum(factor, 0.0)
