"""
Implementation task 6, Part B3: prove studies/hgg_cms/selection.py's
awkward-vectorized functions produce EXACTLY the same per-event/per-photon
results as physics_checks/common.py's flat, per-event reference functions
(a verbatim copy of the design branch's own reference implementation).

This is required because one common.py idiom
(``np.divide(..., out=..., where=...)``) does not work on awkward arrays
at all (confirmed: raises TypeError -- see selection.py's docstring), so
selection.py rewrites that one line as ``ak.where(...)`` and everything
else in a jagged, event-vectorized form; this test is the proof the
rewrite changed nothing.

Uses random synthetic photons (many events, few photons each) so the
comparison exercises every branch of the trigger-mimicking cuts (barrel
tight/loose, endcap tight/loose, the charged-isolation OR, pt<=0 edge
case), not just a handful of hand-picked values.
"""
from __future__ import annotations

import unittest

import awkward as ak
import numpy as np

from studies.hgg_cms.physics_checks import common
from studies.hgg_cms import selection


def _random_photon_batch(rng, n_events=500, max_photons=4):
    """Build a jagged awkward Photons array AND the equivalent list of
    flat per-event numpy dicts (for feeding to common.py one event at a
    time), from the identical random values."""
    per_event_flat = []
    jagged = {k: [] for k in [
        "pt", "eta", "phi", "hoe", "r9", "sieie",
        "pfRelIso03_all", "pfRelIso03_chg", "isScEtaEB", "isScEtaEE",
    ]}

    for _ in range(n_events):
        n = rng.integers(0, max_photons + 1)
        pt = rng.uniform(0.0, 60.0, n)  # includes pt==0 edge case sometimes
        eta = rng.uniform(-2.5, 2.5, n)
        phi = rng.uniform(-np.pi, np.pi, n)
        hoe = rng.uniform(0.0, 0.2, n)
        r9 = rng.uniform(0.3, 1.0, n)
        sieie = rng.uniform(0.0, 0.05, n)
        iso_all = rng.uniform(0.0, 1.0, n)
        iso_chg = rng.uniform(0.0, iso_all, n) if n else np.array([])
        is_eb = rng.uniform(0, 1, n) < 0.6
        is_ee = ~is_eb
        # occasionally force pt to exactly 0 to hit the i_ch/pt edge case
        if n and rng.uniform() < 0.05:
            pt[0] = 0.0

        for k, v in [("pt", pt), ("eta", eta), ("phi", phi), ("hoe", hoe),
                     ("r9", r9), ("sieie", sieie), ("pfRelIso03_all", iso_all),
                     ("pfRelIso03_chg", iso_chg), ("isScEtaEB", is_eb), ("isScEtaEE", is_ee)]:
            jagged[k].append(list(v))

        per_event_flat.append({
            "pt": pt, "eta": eta, "phi": phi, "hoe": hoe, "r9": r9, "sieie": sieie,
            "pfRelIso03_all": iso_all, "pfRelIso03_chg": iso_chg,
            "isScEtaEB": is_eb, "isScEtaEE": is_ee,
        })

    photons = ak.zip({k: ak.Array(v) for k, v in jagged.items()})
    return photons, per_event_flat


class TmMaskEquivalenceTests(unittest.TestCase):
    def test_photon_tm_mask_matches_common_py_event_by_event(self):
        rng = np.random.default_rng(12345)
        photons, per_event_flat = _random_photon_batch(rng, n_events=800)

        i_ch, i_ph, i_tk = selection.compute_isolation_proxies(
            photons.pt, photons.pfRelIso03_all, photons.pfRelIso03_chg
        )
        vectorized_mask = selection.photon_tm_mask(
            photons.pt, photons.isScEtaEB, photons.isScEtaEE,
            photons.hoe, photons.r9, photons.sieie, i_ch, i_ph, i_tk,
        )
        vectorized_flat = ak.flatten(vectorized_mask).to_list()

        reference_flat = []
        for ev in per_event_flat:
            if len(ev["pt"]) == 0:
                continue
            ref_i_ch, ref_i_ph, ref_i_tk = common.compute_isolation_proxies(
                ev["pt"], ev["pfRelIso03_all"], ev["pfRelIso03_chg"]
            )
            ref_mask = common.photon_tm_mask(
                ev["pt"], ev["isScEtaEB"], ev["isScEtaEE"],
                ev["hoe"], ev["r9"], ev["sieie"], ref_i_ch, ref_i_ph, ref_i_tk,
            )
            reference_flat.extend(ref_mask.tolist())

        self.assertEqual(len(vectorized_flat), len(reference_flat))
        self.assertEqual(vectorized_flat, reference_flat)

    def test_isolation_proxies_match_exactly(self):
        rng = np.random.default_rng(999)
        photons, per_event_flat = _random_photon_batch(rng, n_events=200)
        i_ch, i_ph, i_tk = selection.compute_isolation_proxies(
            photons.pt, photons.pfRelIso03_all, photons.pfRelIso03_chg
        )
        for name, vectorized in [("i_ch", i_ch), ("i_ph", i_ph), ("i_tk", i_tk)]:
            flat_v = ak.flatten(vectorized).to_list()
            flat_ref = []
            for ev in per_event_flat:
                if len(ev["pt"]) == 0:
                    continue
                ref = common.compute_isolation_proxies(ev["pt"], ev["pfRelIso03_all"], ev["pfRelIso03_chg"])
                idx = {"i_ch": 0, "i_ph": 1, "i_tk": 2}[name]
                flat_ref.extend(ref[idx].tolist())
            np.testing.assert_allclose(flat_v, flat_ref, rtol=1e-12)


class MassAndPairEquivalenceTests(unittest.TestCase):
    def test_diphoton_mass_massless_matches_common_py(self):
        rng = np.random.default_rng(42)
        n = 500
        pt1 = rng.uniform(20.0, 100.0, n)
        eta1 = rng.uniform(-2.5, 2.5, n)
        phi1 = rng.uniform(-np.pi, np.pi, n)
        pt2 = rng.uniform(20.0, 100.0, n)
        eta2 = rng.uniform(-2.5, 2.5, n)
        phi2 = rng.uniform(-np.pi, np.pi, n)

        vectorized = selection.diphoton_mass_massless(
            ak.Array(pt1), ak.Array(eta1), ak.Array(phi1),
            ak.Array(pt2), ak.Array(eta2), ak.Array(phi2),
        )
        reference = common.diphoton_mass_massless(pt1, eta1, phi1, pt2, eta2, phi2)
        np.testing.assert_allclose(ak.to_numpy(vectorized), reference, rtol=1e-10)

    def test_leading_pair_matches_common_py_pairing_and_scaled_cuts(self):
        """Build events with exactly 2-4 already-v1-selected photons, run
        selection.leading_pair_mass, and independently reproduce
        check_c_trigger_mimicking.py's own leading_pair + scaled-cut logic
        (which itself calls common.py's diphoton_mass_massless) event by
        event."""
        rng = np.random.default_rng(7)
        photons, per_event_flat = _random_photon_batch(rng, n_events=300, max_photons=4)
        # Require >=2 photons per event for a meaningful pairing comparison.
        has_two = ak.num(photons) >= 2
        photons2 = photons[has_two]
        flat2 = [ev for ev, keep in zip(per_event_flat, ak.to_list(has_two)) if keep]

        pair = selection.leading_pair_mass(photons2)
        vec_mgg = ak.to_list(pair["mgg"])
        vec_scaled_ok = ak.to_list(pair["scaled_and_window_ok"])
        vec_cat = ak.to_list(pair["category"])

        for i, ev in enumerate(flat2):
            order = np.argsort(-ev["pt"])
            j1, j2 = order[0], order[1]
            ref_mgg = common.diphoton_mass_massless(
                ev["pt"][j1], ev["eta"][j1], ev["phi"][j1],
                ev["pt"][j2], ev["eta"][j2], ev["phi"][j2],
            )
            self.assertAlmostEqual(vec_mgg[i], float(ref_mgg), places=8)
            ref_scaled_ok = (ev["pt"][j1] > ref_mgg / 3.0) and (ev["pt"][j2] > ref_mgg / 4.0)
            ref_window_ok = 100.0 < ref_mgg < 180.0
            self.assertEqual(vec_scaled_ok[i], bool(ref_scaled_ok and ref_window_ok))
            ref_cat = "EBEB" if (ev["isScEtaEB"][j1] and ev["isScEtaEB"][j2]) else "notEBEB"
            self.assertEqual(vec_cat[i], ref_cat)


if __name__ == "__main__":
    unittest.main()
