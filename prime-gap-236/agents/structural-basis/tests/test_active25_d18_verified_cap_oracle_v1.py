#!/usr/bin/env python3

from fractions import Fraction as Q
import importlib.util
from pathlib import Path
import sys
import unittest


TARGET = (Path(__file__).parents[1] / "code" /
          "active25_d18_verified_cap_oracle_v1.py")
SPEC = importlib.util.spec_from_file_location(
    "active25_d18_verified_cap_oracle_v1", TARGET)
if SPEC is None or SPEC.loader is None:
    raise ImportError(TARGET)
V = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = V
SPEC.loader.exec_module(V)


class D18VerifiedCapOracleTest(unittest.TestCase):
    def test_all_bindings_match(self):
        self.assertEqual(V.sha256(V.CORE), V.CORE_SHA256)
        self.assertEqual(V.sha256(V.SUPPORT), V.SUPPORT_SHA256)
        self.assertEqual(V.sha256(V.CONTRACTION), V.CONTRACTION_SHA256)

    def test_verified_schedule_is_exact_and_plateaus(self):
        module = V.load_core()
        row = V.verified_geometry(module)
        expected = tuple(Q(value, 1_000_000) for value in (
            138360, 155020, 158662, 171688, 177684, 180588,
            183402, 185486, 187011, 188221, 189137, 189137))
        self.assertEqual(row["schedule"][:12], expected)
        self.assertEqual(row["schedule"][11:], (Q(189137, 1_000_000),) * 15)
        module.GEOMETRIES[V.GEOMETRY] = row
        module.configure_geometry(V.GEOMETRY)
        self.assertEqual(module.MAX_ACTIVE_COUNT, 11)
        self.assertEqual(module.ALPHA2, Q(237991, 900000))
        self.assertEqual(module.ETA2, Q(224491, 900000))

    def test_exact_projection_has_the_required_orientation(self):
        module = V.load_core()
        _data, projection, a11_ratio, b01_ratio = V.exact_contraction(module)
        self.assertAlmostEqual(float(projection),
                               0.0157186769470348646, places=16)
        self.assertAlmostEqual(float(a11_ratio),
                               0.06362361729216537, places=16)
        self.assertAlmostEqual(float(b01_ratio),
                               0.03162402704301475, places=16)
        self.assertEqual(projection, b01_ratio ** 2 / a11_ratio)


if __name__ == "__main__":
    unittest.main()
