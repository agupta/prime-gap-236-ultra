#!/usr/bin/env python3

from fractions import Fraction as Q
import importlib.util
from itertools import permutations
from pathlib import Path
import sys
import unittest

import numpy as np


TARGET = Path(__file__).with_name("heuristic_active25_d18_target_mcmc.py")
SPEC = importlib.util.spec_from_file_location("target_d18_mcmc", TARGET)
if SPEC is None or SPEC.loader is None:
    raise ImportError(TARGET)
M = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = M
SPEC.loader.exec_module(M)


def literal_orbit(point, partition):
    padded = tuple(partition) + (0,) * (len(point) - len(partition))
    return sum(np.prod([point[i] ** exponent
                        for i, exponent in enumerate(choice)])
               for choice in set(permutations(padded)))


class TargetMCMCTest(unittest.TestCase):
    def test_power_sum_recurrence_literal(self):
        partitions = [(), (2,), (3,), (2, 2), (4, 2), (3, 3, 2)]
        evaluator = M.PowerSumOrbitEvaluator(partitions)
        points = np.array([[Q(1, 7), Q(2, 7), Q(1, 5)],
                           [Q(1, 11), Q(3, 11), Q(2, 9)]], dtype=object)
        # The production evaluator is longdouble; the identity is checked
        # against a literal orbit enumeration at well-separated values.
        observed = evaluator.evaluate(np.asarray(points, dtype=np.longdouble))
        for row, point in enumerate(points):
            for partition in partitions:
                expected = float(literal_orbit(point, partition))
                actual = float(observed[evaluator.index[partition], row])
                self.assertAlmostEqual(actual, expected, places=15)

    def test_batch_polynomial_matches_literal(self):
        basis = ((0, ()), (1, (2,)), (0, (3, 2)))
        coefficients = (Q(2), Q(-3, 5), Q(7, 11))
        polynomial = M.SievePolynomialBatch(basis, coefficients)
        points = np.array([[.03, .07, .02], [.11, .01, .04]],
                          dtype=np.longdouble)
        observed = polynomial.evaluate(points) * polynomial.scale
        for index, point in enumerate(points):
            expected = sum(
                float(c) * (1 - float(sum(point))) ** a *
                float(literal_orbit(point, lam))
                for c, (a, lam) in zip(coefficients, basis))
            self.assertAlmostEqual(float(observed[index]), expected, places=15)

    def test_cap_indicator(self):
        points = np.array([[.01, .02, .03], [.08, .09, .01],
                           [.08, .08, .08]], dtype=np.longdouble)
        cap, counts, ratios = M.cap_indicator(
            points, np.longdouble(.05),
            np.array([.10, .18, .20], dtype=np.longdouble))
        self.assertEqual(counts.tolist(), [0, 2, 3])
        self.assertEqual(cap.tolist(), [True, True, False])
        self.assertEqual(float(ratios[0]), 0)
        self.assertAlmostEqual(float(ratios[1]), 17 / 18)
        self.assertAlmostEqual(float(ratios[2]), 1.2)

    def test_logistic_round_trip_geometry(self):
        z = np.array([[0., 0.], [1., -1.]], dtype=np.longdouble)
        points, y, slack = M.logistic_points(z, np.longdouble(.4))
        self.assertTrue((points > 0).all())
        self.assertTrue(np.allclose(np.sum(y, axis=1) + slack, 1))
        self.assertTrue((np.sum(points, axis=1) < .4).all())

    def test_binary_diagnostics(self):
        chains = np.tile(np.array([0, 1] * 100, dtype=np.int8), (4, 1))
        summary = M.summarize_binary(chains)
        self.assertEqual(summary["mean"], .5)
        self.assertLessEqual(summary["rhat"], 1.01)
        self.assertGreater(summary["ess"], 100)


if __name__ == "__main__":
    unittest.main()
