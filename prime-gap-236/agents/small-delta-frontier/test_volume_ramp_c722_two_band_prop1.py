#!/usr/bin/env python3
"""Cheap exact regressions for the independent volume-ramp audit."""

from __future__ import annotations

import importlib.util
import sys
import unittest
from fractions import Fraction as Q
from pathlib import Path


PATH = Path(__file__).with_name("verify_volume_ramp_c722_two_band_prop1.py")
SPEC = importlib.util.spec_from_file_location("volume_ramp_tested", PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load volume-ramp checker")
M = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = M
SPEC.loader.exec_module(M)


class VolumeRampTests(unittest.TestCase):
    def test_schedule_identity(self):
        self.assertEqual(len(M.OUTER), 23)
        self.assertEqual(M.OUTER[0], Q(49, 625))
        self.assertEqual(M.OUTER[-1], Q(1599, 10000))
        self.assertEqual(M.core.active(M.OUTER), tuple(range(23)))

    def test_fixed_prefix_margins(self):
        cross = M.core.fixed_prefix_family(
            M.core.INNER, M.OUTER, M.core.CROSS_OMEGA)
        outer = M.core.fixed_prefix_family(
            M.OUTER, M.OUTER, M.core.OUTER_OMEGA)
        self.assertEqual(cross["pairs"], 827)
        self.assertEqual(Q(cross["worst_margin"]),
                         Q(3049959149, 45000000000000))
        self.assertEqual(outer["pairs"], 528)
        self.assertEqual(Q(outer["worst_margin"]),
                         Q(24199986563, 15000000000000))

    def test_outer_near_square_literal_cover(self):
        near = M.core.fixed_interval_family(
            M.OUTER, M.OUTER, Q(0), ("IIa", "IIb", "III"))
        self.assertEqual((near["pairs"], near["checks"]), (528, 1584))
        self.assertEqual((near["nodes"], near["leaves"]), (1584, 1584))
        self.assertEqual(Q(near["worst_all_first_margin"]),
                         Q(75949999, 2500000000))

    def test_mixed_iic_range_empty(self):
        result = M.core.dynamic_iic_family(
            M.core.INNER, M.OUTER, M.core.CROSS_OMEGA)
        self.assertEqual(result["checks"], 0)
        self.assertEqual(Q(result["empty_gamma_margin"]),
                         Q(71149997, 7500000000))


if __name__ == "__main__":
    unittest.main()
