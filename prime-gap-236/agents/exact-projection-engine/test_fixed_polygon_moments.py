#!/usr/bin/env python3
"""Exact equality tests for fixed-denominator polygon moments."""

from __future__ import annotations

from fractions import Fraction as Q
import importlib.util
from pathlib import Path
import random
import sys
import unittest


HERE = Path(__file__).resolve().parent
SOURCE = HERE / "fixed_polygon_moments.py"
REFERENCE = HERE.parents[1] / "verify/exact_capped_certificate.py"


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


M = load("fixed_polygon_moments_test", SOURCE)
R = load("fixed_polygon_moments_reference", REFERENCE)


class FixedPolygonMomentsTest(unittest.TestCase):
    def check(self, polygon, powers):
        expected = R._polygon_monomial_batch(polygon, powers)
        observed = M.polygon_monomial_batch_fixed(polygon, powers)
        self.assertEqual(observed, expected)

    def test_hand_triangles_and_clipped_polygons(self):
        powers = {(a, b) for a in range(7) for b in range(7-a)}
        self.check(((Q(0), Q(0)), (Q(2, 3), Q(0)),
                    (Q(0), Q(5, 7))), powers)
        polygon = R._shifted_polygon(
            Q(7, 10), Q(2, 5), Q(1, 9), Q(3, 5), Q(1, 4))
        self.check(polygon, powers)

    def test_seeded_rational_polygons_and_sparse_degrees(self):
        rng = random.Random(23609)
        powers = {(0, 0), (1, 0), (0, 1), (3, 2), (2, 5), (8, 0), (0, 8)}
        for _ in range(12):
            total = Q(rng.randint(4, 12), rng.randint(13, 29))
            x_bound = Q(rng.randint(1, 3), 10)
            y_upper = Q(rng.randint(3, 7), 10)
            polygon = R._shifted_polygon(
                total, x_bound, None, y_upper, None)
            self.check(polygon, powers)

    def test_degenerate_empty_and_invalid_inputs(self):
        powers = {(0, 0), (2, 3)}
        self.check((), powers)
        self.check(((Q(0), Q(0)), (Q(1), Q(0)), (Q(2), Q(0))), powers)
        with self.assertRaises(ValueError):
            M.polygon_monomial_batch_fixed(
                ((Q(0), Q(0)), (Q(1), Q(0)), (Q(0), Q(1))), {(True, 0)})


if __name__ == "__main__":
    unittest.main()
