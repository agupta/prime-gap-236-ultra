#!/usr/bin/env python3

from fractions import Fraction as Q
import importlib.util
from pathlib import Path
import sys
import unittest

import numpy as np


TARGET = (Path(__file__).parents[1] / "code" /
          "active25_d18_h2_bridge_v1.py")
SPEC = importlib.util.spec_from_file_location("active25_d18_h2_bridge_v1",
                                              TARGET)
if SPEC is None or SPEC.loader is None:
    raise ImportError(TARGET)
B = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = B
SPEC.loader.exec_module(B)


class D18H2BridgeTest(unittest.TestCase):
    def test_pins(self):
        self.assertEqual(B.sha256(B.CORE), B.CORE_SHA256)
        self.assertEqual(B.sha256(B.SUPPORT), B.SUPPORT_SHA256)
        self.assertEqual(B.sha256(B.CONTRACTION), B.CONTRACTION_SHA256)
        self.assertEqual(B.sha256(B.VERIFIED_WRAPPER),
                         B.VERIFIED_WRAPPER_SHA256)

    def test_logistic_simplex_map(self):
        z = np.array([[0, 0], [2, -1]], dtype=np.longdouble)
        points, y, slack = B.logistic_points(z, np.longdouble("0.7"))
        self.assertTrue(np.all(y > 0))
        self.assertTrue(np.all(slack > 0))
        self.assertTrue(np.allclose(
            np.sum(y, axis=1) + slack, 1, rtol=1e-17, atol=1e-17))
        self.assertTrue(np.allclose(points, np.longdouble("0.7") * y))

    def test_exact_d1_bridge_orientation(self):
        module = B.load("h2_bridge_test_core", B.CORE, B.CORE_SHA256)
        B.configure(module, "d1over60_verified")
        cert, uncapped, *_ = module.load_inputs()
        row = B.exact_forms(module, "d1over60_verified", cert, uncapped)
        self.assertAlmostEqual(float(row["A11_over_A00"]),
                               0.06362361729216537, places=16)
        self.assertAlmostEqual(float(row["B01_over_A00"]),
                               0.03162402704301475, places=16)
        self.assertAlmostEqual(float(row["projection_over_A00"]),
                               0.0157186769470348646, places=16)
        self.assertEqual(row["projection_over_A00"],
                         row["B01_over_A00"] ** 2 /
                         row["A11_over_A00"])

    def test_weighted_quantiles(self):
        self.assertEqual(B.weighted_quantiles(
            np.array([3, 1, 2], dtype=np.longdouble),
            np.array([1, 2, 1], dtype=np.longdouble),
            (0.25, 0.5, 0.75, 1.0)), [1.0, 1.0, 2.0, 3.0])

    def test_radial_volume_draw(self):
        rng = np.random.default_rng(236)
        values = B.radial_volume_draw(
            rng, 100000, 3, np.longdouble("0.2"),
            np.longdouble("0.3"))
        self.assertTrue(np.all(values >= np.longdouble("0.2")))
        self.assertTrue(np.all(values <= np.longdouble("0.3")))
        exact_mean_cube = (
            np.longdouble("0.2") ** 3 +
            np.longdouble("0.3") ** 3) / 2
        self.assertAlmostEqual(
            float(np.mean(values ** 3, dtype=np.longdouble)),
            float(exact_mean_cube), places=4)

    def test_verified_cap_membership(self):
        module = B.load("h2_bridge_test_cap_core", B.CORE, B.CORE_SHA256)
        B.configure(module, "d1over60_verified")
        b5 = module.ld(module.SCHEDULE[4])
        counts = np.array([0, 5, 5, 12])
        sums = np.array([0, b5, b5 + 1e-6, 0], dtype=np.longdouble)
        self.assertEqual(B.cap_membership(
            module, counts, sums, geometry="d1over60_verified").tolist(),
                         [True, True, False, False])

    def test_two_band_geometry_is_exactly_bound(self):
        module = B.load("h2_bridge_test_two_band_core", B.CORE,
                        B.CORE_SHA256)
        B.configure(module, B.TWO_BAND_GEOMETRY)
        row = B.two_band_geometry(module)
        self.assertEqual(B.sha256(B.TWO_BAND_CHECKER),
                         B.TWO_BAND_CHECKER_SHA256)
        self.assertEqual(B.sha256(B.TWO_BAND_RESULT),
                         B.TWO_BAND_RESULT_SHA256)
        self.assertEqual(row["boundary"], Q(263741, 1000000))
        self.assertEqual(row["lower_eta_sensitivity"],
                         Q(248741, 1000000))
        self.assertEqual(row["lower_schedule"][:4], tuple(
            Q(x, 1000000) for x in (139683, 156347, 157797, 173014)))
        counts = np.array([4, 4])
        sums = np.array([0.172, 0.172], dtype=np.longdouble)
        totals = np.array([0.263, 0.264], dtype=np.longdouble)
        self.assertEqual(B.cap_membership(
            module, counts, sums, geometry=B.TWO_BAND_GEOMETRY,
            totals=totals, band_geometry=row).tolist(), [True, False])


if __name__ == "__main__":
    unittest.main()
