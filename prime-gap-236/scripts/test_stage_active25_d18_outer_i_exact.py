#!/usr/bin/env python3
"""Low-dimensional exact tests for the D18 outer-I stratum contraction."""

from __future__ import annotations

from fractions import Fraction as Q
import importlib.util
from pathlib import Path
import sys
import unittest


HERE = Path(__file__).resolve().parent
TARGET = HERE / "stage_active25_d18_outer_i_exact.py"
SPEC = importlib.util.spec_from_file_location("stage_d18_outer_i", TARGET)
if SPEC is None or SPEC.loader is None:
    raise ImportError(TARGET)
M = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = M
SPEC.loader.exec_module(M)


class StageOuterITest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        scalar = M.load_module("stage_d18_outer_i_test_scalar", M.SCALAR)
        core = scalar.load_module(
            "stage_d18_outer_i_test_core", scalar.CORE_PATH)
        cls.support_class = type(core.make_supports()["H"])

    def supports(self):
        support = self.support_class
        high = support.make(3, Q(2, 5), Q(3, 10), Q(1, 10),
                            (Q(3, 20), Q(1, 5), Q(1, 4)))
        low = support.make(3, Q(7, 20), Q(3, 10), Q(1, 10),
                           (Q(3, 20), Q(1, 5), Q(1, 4)))
        return high, low

    def test_strata_sum_to_direct_support_moment(self):
        high, low = self.supports()
        square = {(0, ()): Q(3), (1, (2,)): Q(-2),
                  (2, (3, 2)): Q(5, 7)}
        rows = [M.shell_stratum_contraction(
            square, high, low, r, progress_every=0) for r in range(4)]
        expected_high = sum(
            coefficient * high.orbit_support_moment(orbit, power)
            for (power, orbit), coefficient in square.items())
        expected_low = sum(
            coefficient * low.orbit_support_moment(orbit, power)
            for (power, orbit), coefficient in square.items())
        self.assertEqual(sum(row[0] for row in rows), expected_high)
        self.assertEqual(sum(row[1] for row in rows), expected_low)
        self.assertEqual(sum(row[2] for row in rows),
                         expected_high - expected_low)

    def test_group_slices_add_to_full_contraction(self):
        high, low = self.supports()
        square = {(0, ()): Q(3), (1, (2,)): Q(-2),
                  (2, (3, 2)): Q(5, 7)}
        whole = M.shell_stratum_contraction(
            square, high, low, 1, progress_every=0)
        left = M.shell_stratum_contraction(
            square, high, low, 1, group_start=0, group_stop=1,
            progress_every=0)
        right = M.shell_stratum_contraction(
            square, high, low, 1, group_start=1, group_stop=3,
            progress_every=0)
        self.assertEqual(tuple(left[i] + right[i] for i in range(3)), whole)

    def test_zero_square(self):
        high, low = self.supports()
        self.assertEqual(M.shell_stratum_contraction(
            {}, high, low, 2, progress_every=0), (Q(0), Q(0), Q(0)))

    def test_rejects_bad_count_and_geometry(self):
        high, low = self.supports()
        with self.assertRaises(ValueError):
            M.shell_stratum_contraction({}, high, low, -1,
                                        progress_every=0)
        alien = self.support_class.make(
            3, Q(7, 20), Q(3, 10), Q(1, 10),
            (Q(3, 20), Q(9, 50), Q(1, 4)))
        with self.assertRaises(ValueError):
            M.shell_stratum_contraction({}, high, alien, 0,
                                        progress_every=0)
        with self.assertRaises(ValueError):
            M.shell_stratum_contraction(
                {(0, ()): Q(1)}, high, low, 0,
                group_start=1, group_stop=1, progress_every=0)


if __name__ == "__main__":
    unittest.main()
