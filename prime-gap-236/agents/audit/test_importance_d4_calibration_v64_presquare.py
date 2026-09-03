#!/usr/bin/env python3
"""Desired regression for frozen v6.4's pre-square underflow gap.

This test intentionally FAILS on v6.4.  A corrected successor must recover
the weighted m0 from the returned unit marginals before trusting point.z.
"""

from __future__ import annotations

import math
import sys
import unittest
from pathlib import Path


HERE = Path(__file__).resolve()
REPO = HERE.parents[2]
CODE = REPO / "agents/structural-basis/code"
sys.path.insert(0, str(CODE))

import importance_d4_calibration_v64 as V64  # noqa: E402
from importance_whitening_v6 import WhitenedC10ImportanceDensity  # noqa: E402


def presquare_fixture():
    oracle = REPO / V64.v63.v62.v61.v6.REQUIRED_DATA_PATHS[0]
    vector = REPO / V64.v63.v62.v61.v6.REQUIRED_DATA_PATHS[1]
    adapter = WhitenedC10ImportanceDensity(vector, oracle)
    marginals = [0.0] * adapter.dimension
    marginals[0] = float.fromhex("0x1p-600")
    marginals[1] = 1.0
    adapter.j_support = lambda _common: True
    adapter.j_marginals = lambda _common: tuple(marginals)

    def j_m0(_common, transformed=None):
        values = marginals if transformed is None else transformed
        return math.fsum(
            adapter.base_constant_weights[6 * r] * values[6 * r]
            for r in adapter.strata)

    adapter.j_m0 = j_m0
    return adapter, (0.0,) * 47


class V64PresquareRegression(unittest.TestCase):
    def test_nonzero_weighted_m0_cannot_become_zero_z(self):
        adapter, common = presquare_fixture()
        point = V64.FROZEN_V63_J_ENVELOPE_POINT(adapter, common)
        weighted_m0 = math.fsum(
            adapter.base_constant_weights[6 * r] *
            point.unit_marginals[6 * r]
            for r in adapter.strata)
        self.assertEqual(weighted_m0.hex(), "0x1.0000000000000p-607")
        self.assertEqual(weighted_m0 * weighted_m0, 0.0)
        self.assertEqual(point.z, 0.0)
        with self.assertRaises(ArithmeticError):
            V64.j_envelope_point(adapter, common)


if __name__ == "__main__":
    unittest.main()
