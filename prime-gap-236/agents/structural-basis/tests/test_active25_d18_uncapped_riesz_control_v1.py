#!/usr/bin/env python3

from fractions import Fraction as Q
import importlib.util
import math
from pathlib import Path
import sys
import unittest

import numpy as np


TARGET = (Path(__file__).parents[1] / "code" /
          "active25_d18_uncapped_riesz_control_v1.py")
SPEC = importlib.util.spec_from_file_location(
    "active25_d18_uncapped_riesz_control_v1", TARGET)
if SPEC is None or SPEC.loader is None:
    raise ImportError(TARGET)
C = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = C
SPEC.loader.exec_module(C)
M = C.load_oracle_module()


class D18UncappedRieszControlTest(unittest.TestCase):
    def tearDown(self):
        M.configure_geometry("audited")

    def test_pinned_capped_oracle(self):
        self.assertEqual(C.sha256(C.ORACLE), C.ORACLE_SHA256)
        self.assertEqual(C.sha256(C.VERIFIED_WRAPPER),
                         C.VERIFIED_WRAPPER_SHA256)

    def test_exact_anchor_is_geometry_bound(self):
        cert, uncapped, *_ = M.load_inputs()
        M.configure_geometry("d1over60")
        row = C.natural_projection_anchor(M, "d1over60", cert, uncapped)
        self.assertEqual(C.sha256(C.D1_EXACT), C.D1_EXACT_SHA256)
        self.assertAlmostEqual(float(row["value"]),
                               0.0157186769470348646, places=16)
        M.configure_geometry("d014")
        self.assertIsNone(C.natural_projection_anchor(
            M, "d014", cert, uncapped))
        C.install_verified_geometry(M)
        M.configure_geometry(C.VERIFIED_GEOMETRY)
        verified = C.natural_projection_anchor(
            M, C.VERIFIED_GEOMETRY, cert, uncapped)
        self.assertEqual(verified["value"], row["value"])
        self.assertEqual(M.SCHEDULE[11:], (Q(189137, 1000000),) * 15)

    def test_full_simplex_constant_weight_and_shell(self):
        M.configure_geometry("d014")
        points, measure, shell = C.full_simplex_shell_sample(
            M, np.random.default_rng(236), 256)
        total = np.sum(points, axis=1, dtype=np.longdouble)
        self.assertTrue(np.all(total <= M.ld(M.ALPHA2) +
                               np.longdouble("1e-18")))
        self.assertTrue(np.array_equal(
            shell, (total > M.ld(M.ALPHA1)) &
            (total < M.ld(M.ALPHA2) + np.longdouble("1e-18"))))
        self.assertEqual(
            measure, M.ld(M.ALPHA2) ** M.K / math.factorial(M.K))

    def test_exact_full_shell_volume_literal_k2_analogue(self):
        # Area between the 1/2 and 3/4 two-simplexes.
        observed = (Q(3, 4) ** 2 - Q(1, 2) ** 2) / math.factorial(2)
        self.assertEqual(observed, Q(5, 32))
        M.configure_geometry("audited")
        self.assertEqual(
            C.exact_full_shell_volume(M),
            (M.ALPHA2 ** M.K - M.ALPHA1 ** M.K) /
            math.factorial(M.K))

    def test_weighted_quantiles_literal(self):
        observed = C.weighted_quantiles(
            np.array([3, 1, 2], dtype=np.longdouble),
            np.array([1, 2, 1], dtype=np.longdouble),
            (0.25, 0.5, 0.75, 1.0))
        self.assertEqual(observed, [1.0, 1.0, 2.0, 3.0])

    def test_cap_membership_matches_schedule_literal(self):
        M.configure_geometry("d014")
        counts = np.array([0, 1, 1, 13, 14])
        b1 = M.ld(M.SCHEDULE[0])
        b13 = M.ld(M.SCHEDULE[12])
        large_sums = np.array(
            [0, b1, b1 + np.longdouble("1e-6"), b13, 0],
            dtype=np.longdouble)
        self.assertEqual(
            C.cap_membership(M, counts, large_sums).tolist(),
            [True, True, False, True, False])


if __name__ == "__main__":
    unittest.main()
