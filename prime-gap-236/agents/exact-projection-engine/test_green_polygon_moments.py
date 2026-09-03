#!/usr/bin/env python3
"""Exact equality tests for Green-theorem polygon moments."""

from __future__ import annotations

from fractions import Fraction as Q
import importlib.util
from pathlib import Path
import random
import sys
import unittest


HERE = Path(__file__).resolve().parent
SOURCE = HERE / "green_polygon_moments.py"
REFERENCE = HERE.parents[1] / "verify/exact_capped_certificate.py"


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


M = load("green_polygon_moments_test", SOURCE)
R = load("green_polygon_moments_reference", REFERENCE)


class GreenPolygonMomentsTest(unittest.TestCase):
    def check(self, polygon, powers):
        self.assertEqual(
            M.polygon_monomial_batch_green(polygon, powers),
            R._polygon_monomial_batch(polygon, powers))

    def test_simplex_clipped_and_reversed(self):
        powers = {(a, b) for a in range(10) for b in range(10 - a)}
        polygons = [
            ((Q(0), Q(0)), (Q(1), Q(0)), (Q(0), Q(1))),
            R._shifted_polygon(
                Q(7, 10), Q(2, 5), Q(1, 9), Q(3, 5), Q(1, 4)),
            ((Q(-2, 7), Q(-1, 5)), (Q(11, 13), Q(2, 9)),
             (Q(9, 11), Q(17, 19)), (Q(-1, 13), Q(5, 7))),
        ]
        for polygon in polygons:
            self.check(polygon, powers)
            self.check(tuple(reversed(polygon)), powers)

    def test_seeded_target_shaped_polygons_and_high_degrees(self):
        rng = random.Random(236_80)
        powers = {
            (0, 0), (1, 0), (0, 1), (8, 37),
            (80, 0), (0, 80), (79, 1), (1, 79)}
        for _ in range(12):
            total = Q(rng.randint(10, 30), rng.randint(37, 83))
            x_bound = Q(rng.randint(5, 15), rng.randint(41, 97))
            y_lower = Q(rng.randint(0, 6), rng.randint(53, 101))
            y_upper = y_lower + Q(rng.randint(5, 15), rng.randint(47, 89))
            total_lower = Q(rng.randint(0, 9), rng.randint(59, 103))
            polygon = R._shifted_polygon(
                total, x_bound, y_lower, y_upper, total_lower)
            self.check(polygon, powers)

    def test_empty_degenerate_invalid_and_nonconvex(self):
        powers = {(0, 0), (2, 3)}
        for polygon in ((), ((Q(0), Q(0)), (Q(1), Q(0))),
                        ((Q(0), Q(0)), (Q(1), Q(1)), (Q(2), Q(2)))):
            self.assertEqual(
                M.polygon_monomial_batch_green(polygon, powers),
                {power: Q(0) for power in powers})
        with self.assertRaises(ValueError):
            M.polygon_monomial_batch_green(
                ((Q(0), Q(0)), (Q(1), Q(0)), (Q(0), Q(1))),
                {(True, 0)})
        with self.assertRaises(ValueError):
            M.polygon_monomial_batch_green(
                ((Q(0), Q(0)), (Q(2), Q(0)), (Q(1), Q(1)),
                 (Q(2), Q(2)), (Q(0), Q(2))), powers)
        with self.assertRaises(ValueError):
            M.polygon_monomial_batch_green(
                ((Q(0), Q(0)), (Q(1), Q(0)), (Q(0), Q(1)),
                 (Q(0), Q(0)), (Q(1), Q(0)), (Q(0), Q(1))), powers)
        with self.assertRaises(ValueError):
            M.polygon_monomial_batch_green(
                ((Q(5), Q(-2)), (Q(2), Q(1)), (Q(-2), Q(-3)),
                 (Q(0), Q(-4)), (Q(-4), Q(4)), (Q(-5), Q(3))), powers)


if __name__ == "__main__":
    unittest.main()
