#!/usr/bin/env python3
"""Desired regressions for frozen v6.5's nonfinite-square gap.

These tests intentionally FAIL on v6.5.  A successor must reject a finite
weighted m0 whose square overflows before forming a comparison tolerance.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace


HERE = Path(__file__).resolve()
REPO = HERE.parents[2]
CODE = REPO / "agents/structural-basis/code"
sys.path.insert(0, str(CODE))

import importance_d4_calibration_v65 as V65  # noqa: E402
from importance_whitening_v6 import WhitenedC10ImportanceDensity  # noqa: E402


def adapter_and_overflow_point():
    oracle = REPO / V65.v64.v63.v62.v61.v6.REQUIRED_DATA_PATHS[0]
    vector = REPO / V65.v64.v63.v62.v61.v6.REQUIRED_DATA_PATHS[1]
    adapter = WhitenedC10ImportanceDensity(vector, oracle)
    unit = [0.0] * adapter.dimension
    unit[0] = sys.float_info.max
    point = SimpleNamespace(
        unit_marginals=tuple(unit), z=0.125, log_g=0.0)
    return adapter, point


class V65SquareOverflowRegression(unittest.TestCase):
    def test_weighted_square_overflow_rejects(self):
        adapter, point = adapter_and_overflow_point()
        with self.assertRaises(ArithmeticError):
            V65._weighted_m0_and_square(adapter, point)

    def test_public_wrapper_cannot_hide_infinite_difference(self):
        adapter, point = adapter_and_overflow_point()
        original = V65.FROZEN_V64_J_ENVELOPE_POINT
        V65.FROZEN_V64_J_ENVELOPE_POINT = lambda _adapter, _common: point
        try:
            with self.assertRaises(ArithmeticError):
                V65.j_envelope_point(adapter, ())
        finally:
            V65.FROZEN_V64_J_ENVELOPE_POINT = original


if __name__ == "__main__":
    unittest.main()
