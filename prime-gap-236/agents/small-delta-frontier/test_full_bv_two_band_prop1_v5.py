#!/usr/bin/env python3
"""Cheap exact branch regressions for the corrected narrow v5 audit."""

from __future__ import annotations

import importlib.util
import sys
import unittest
from fractions import Fraction as Q
from pathlib import Path


PATH = Path(__file__).with_name("verify_full_bv_two_band_prop1_v5.py")
SPEC = importlib.util.spec_from_file_location("narrow_v5_tested", PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load narrow v5 checker")
M = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = M
SPEC.loader.exec_module(M)
M.configure_core()


class NarrowV5Tests(unittest.TestCase):
    def test_identity_and_active_counts(self):
        self.assertEqual(M.core.active(M.INNER), tuple(range(10)))
        self.assertEqual(M.core.active(M.OUTER), tuple(range(6)))
        self.assertEqual((M.CROSS_OMEGA, M.OUTER_OMEGA),
                         (Q(3, 2000), Q(3, 1000)))

    def test_corrected_iib_c3(self):
        for omega in (Q(0), M.CROSS_OMEGA, M.OUTER_OMEGA):
            safe = M.core.fixed_capacities(omega)["IIb"][2]
            self.assertEqual(safe, M.DELTA + 2 * omega)
            self.assertEqual(M.core.iib_c3_actual_infimum(omega) - safe,
                             2 * M.core.H / 7)

    def test_near_square_all_three_band_pairs(self):
        families = ("IIa", "IIb", "III")
        cross = M.core.fixed_interval_family(
            M.INNER, M.OUTER, Q(0), families)
        transpose = M.core.fixed_interval_family(
            M.OUTER, M.INNER, Q(0), families)
        outer = M.core.fixed_interval_family(
            M.OUTER, M.OUTER, Q(0), families)
        self.assertEqual((cross["pairs"], transpose["pairs"], outer["pairs"]),
                         (59, 59, 35))
        self.assertEqual((cross["checks"], transpose["checks"], outer["checks"]),
                         (177, 177, 105))
        self.assertEqual((cross["nodes"], transpose["nodes"], outer["nodes"]),
                         (177, 177, 105))
        self.assertLess(Q(cross["worst_all_first_margin"]), 0)
        self.assertLess(Q(transpose["worst_all_first_margin"]), 0)
        self.assertGreater(Q(outer["worst_all_first_margin"]), 0)

    def test_near_iic_really_empty(self):
        gap = ((Q(2, 5) - M.core.H) -
               (Q(1, 3) + Q(7, 3) * M.DELTA + 3 * M.core.H))
        self.assertEqual(gap, Q(1, 750) - 4 * M.core.H)
        self.assertGreater(gap, 0)


if __name__ == "__main__":
    unittest.main()
