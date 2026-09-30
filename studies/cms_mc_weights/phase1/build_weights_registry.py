#!/usr/bin/env python
"""
Phase-1 MC weights task, amendment A3: build a weights-registry JSON in
PR#23's exact `{"default_weight", "weights"}` format
(services/calculations/weights_registry.py:113-118, PR#23, read read-only
via `git fetch .../pull/23/head` -- confirmed unchanged this session,
head 9be20a9), WITHOUT importing any PR#23 code -- this module
independently reimplements only the tiny, already-quoted formula
(`compute_normalization` = sigma * k * eps_filter * L / sumOfWeights,
services/calculations/mc_weights.py in PR#23) and the registry's on-disk
shape, both plain enough not to need the actual PR#23 module.

Deliberate difference from PR#23 (DESIGN.md Sec 2, restated here since
this is the module that enforces it): `weight_for()` raises a hard error
for an unrecognized source/record ID -- it does NOT fall back to
`default_weight` silently the way PR#23's own `WeightsRegistry.weight_for`
does.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Optional

PB_TO_FB = 1000.0  # 1 pb = 1000 fb -- same constant PR#23's mc_weights.py uses


def compute_normalization(cross_section_pb: float, k_factor: float, gen_filt_eff: float,
                           target_luminosity_fb: float, sum_of_weights: float) -> float:
    """w = (sigma[pb] * PB_TO_FB * k * eps_filter * L[fb^-1]) / sum_of_weights
    -- the per-event-weight-of-1 normalization factor; multiply by the
    actual per-event genWeight (and, for this phase-1 task, by
    L1PreFiringWeight_Nom) afterward. Identical formula to PR#23's
    compute_normalization(), independently written here (A3: do not
    import PR#23 code)."""
    if sum_of_weights == 0:
        raise ValueError("sum_of_weights is zero -- cannot normalize a sample with zero effective size.")
    expected_yield = cross_section_pb * PB_TO_FB * k_factor * gen_filt_eff * target_luminosity_fb
    return expected_yield / sum_of_weights


class CMSWeightsRegistry:
    """CMS-side equivalent of PR#23's WeightsRegistry, same on-disk format,
    ONE deliberate behavioral difference: unknown source/record IDs raise,
    never silently fall back to default_weight (DESIGN.md Sec 2)."""

    def __init__(self, weights_by_record_id: Dict[str, float], default_weight: float = 1.0):
        self._weights = {str(k): float(v) for k, v in weights_by_record_id.items()}
        self.default_weight = float(default_weight)

    def __len__(self) -> int:
        return len(self._weights)

    def weight_for(self, record_id) -> float:
        key = str(record_id)
        if key not in self._weights:
            raise KeyError(
                f"No normalization weight for CMS record ID '{key}' -- refusing "
                f"to silently fall back to default_weight={self.default_weight} "
                f"(deliberate difference from PR#23's WeightsRegistry, "
                f"DESIGN.md Sec 2: an unknown record almost always means the "
                f"normalisation file is missing an entry for a real sample, "
                f"not that it should be treated as unweighted)."
            )
        return self._weights[key]

    def save(self, path) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"default_weight": self.default_weight, "weights": self._weights}, f, indent=2)

    @classmethod
    def load(cls, path) -> Optional["CMSWeightsRegistry"]:
        p = Path(path)
        if not p.exists():
            return None
        data = json.loads(p.read_text(encoding="utf-8"))
        return cls(data.get("weights", {}), data.get("default_weight", 1.0))

    @classmethod
    def build(cls, normalisation: dict, sum_of_weights_by_record: Dict[str, float],
              target_luminosity_fb: float, default_weight: float = 1.0) -> "CMSWeightsRegistry":
        """`normalisation`: {record_id: entry} as built by
        build_normalisation_json.py. `sum_of_weights_by_record`: {record_id:
        Sigma genWeight}, computed PER RUN (A5) -- never read from a static
        file."""
        weights = {}
        for record_id, entry in normalisation.items():
            if record_id not in sum_of_weights_by_record:
                raise KeyError(
                    f"record {record_id} is in the normalisation file but has "
                    f"no computed sum_of_weights this run -- refusing to build "
                    f"a registry entry from a missing denominator."
                )
            weights[record_id] = compute_normalization(
                cross_section_pb=entry["cross_section_pb"],
                k_factor=entry["k_factor"],
                gen_filt_eff=entry["gen_filt_eff"],
                target_luminosity_fb=target_luminosity_fb,
                sum_of_weights=sum_of_weights_by_record[record_id],
            )
        return cls(weights, default_weight=default_weight)
