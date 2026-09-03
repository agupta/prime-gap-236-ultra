#!/usr/bin/env python3

import importlib.util
import itertools
import json
import math
import unittest
from fractions import Fraction
from pathlib import Path


HERE = Path(__file__).resolve()
MODULE_PATH = HERE.parents[1] / "code" / "importance_point_eval.py"
SPEC = importlib.util.spec_from_file_location("importance_point_eval", MODULE_PATH)
MOD = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MOD)


def brute_monomial(point, partition):
    partition = tuple(partition)
    if not partition:
        return Fraction(1)
    total = Fraction(0)
    exponent_orders = set(itertools.permutations(partition))
    for coordinates in itertools.combinations(range(len(point)), len(partition)):
        for exponents in exponent_orders:
            term = Fraction(1)
            for coordinate, exponent in zip(coordinates, exponents):
                term *= point[coordinate] ** exponent
            total += term
    return total


class PointEvaluatorTests(unittest.TestCase):
    def test_orbit_normalization_against_brute_force(self):
        point = [Fraction(1, 11), Fraction(2, 13), Fraction(3, 17),
                 Fraction(5, 19)]
        partitions = [(), (2,), (4,), (2, 2), (4, 2), (2, 2, 2),
                      (6, 2), (4, 4)]
        evaluator = MOD.MonomialSymmetricPointEvaluator(partitions)
        actual = evaluator.evaluate(point)
        for partition in partitions:
            self.assertEqual(actual[tuple(partition)],
                             brute_monomial(point, partition))

    def test_polynomial_and_permutation_invariance(self):
        point = [Fraction(1, 20), Fraction(1, 15), Fraction(1, 12)]
        basis = [[0, []], [2, []], [0, [2]], [1, [4, 2]], [0, [2, 2]]]
        coefficients = [Fraction(7, 3), Fraction(-5, 8), Fraction(11, 9),
                        Fraction(13, 17), Fraction(-19, 23)]
        evaluator = MOD.MonomialSymmetricPointEvaluator(x[1] for x in basis)
        expected = Fraction(0)
        residual = 1 - sum(point)
        for coefficient, (a, partition) in zip(coefficients, basis):
            expected += coefficient * residual ** a * brute_monomial(
                point, partition)
        self.assertEqual(MOD.evaluate_sieve_polynomial(
            point, basis, coefficients, evaluator), expected)
        for permuted in itertools.permutations(point):
            self.assertEqual(MOD.evaluate_sieve_polynomial(
                permuted, basis, coefficients, evaluator), expected)

    def test_complete_d12_input_is_permutation_invariant(self):
        path = HERE.parents[2] / "exact-integrator" / "results" / \
            "hb_c10_fullsimplex_noones_D12_integer_scaled.json"
        raw = json.loads(path.read_text())
        basis = raw["basis"]
        coefficients = [int(x) for x in raw["rational_vector"]]
        evaluator = MOD.MonomialSymmetricPointEvaluator(x[1] for x in basis)
        point = [Fraction(i, 10000) for i in range(1, 49)]
        first = MOD.evaluate_sieve_polynomial(
            point, basis, coefficients, evaluator)
        permutation = point[17:] + point[:17]
        second = MOD.evaluate_sieve_polynomial(
            permutation, basis, coefficients, evaluator)
        self.assertEqual(first, second)
        self.assertNotEqual(first, 0)

    def test_fail_closed_inputs(self):
        with self.assertRaises(ValueError):
            MOD.MonomialSymmetricPointEvaluator([(2, 0)])
        with self.assertRaises(ValueError):
            MOD.evaluate_sieve_polynomial([Fraction(1, 3)], [[0, []]], [])
        with self.assertRaises(ValueError):
            MOD.evaluate_sieve_polynomial(
                [Fraction(1, 3)], [[-1, []]], [Fraction(1)])
        with self.assertRaisesRegex(ValueError, "exact integer"):
            MOD.MonomialSymmetricPointEvaluator([(2.5,)])
        with self.assertRaisesRegex(ValueError, "exact integer"):
            MOD.evaluate_sieve_polynomial(
                [Fraction(1, 3)], [[1.5, []]], [Fraction(1)])
        with self.assertRaisesRegex(ValueError, "nonfinite"):
            MOD.MonomialSymmetricPointEvaluator([(2,)]).evaluate([math.nan])
        with self.assertRaisesRegex(ValueError, "nonfinite"):
            MOD.support_contains([math.nan], 0.4, 0.1, lambda _: 0.2)

    def test_distinguished_polynomial_pointwise(self):
        common = [Fraction(1, 20), Fraction(1, 15), Fraction(1, 12)]
        basis = [[0, []], [2, []], [0, [2]], [1, [4, 2]],
                 [0, [2, 2]], [3, [6, 2, 2]]]
        coefficients = [Fraction(7, 3), Fraction(-5, 8), Fraction(11, 9),
                        Fraction(13, 17), Fraction(-19, 23), Fraction(29, 31)]
        polynomial = MOD.distinguished_polynomial(common, basis, coefficients)
        for t in (Fraction(0), Fraction(1, 100), Fraction(1, 25),
                  Fraction(3, 20)):
            value = sum(c * t ** j for j, c in enumerate(polynomial))
            self.assertEqual(value, MOD.evaluate_sieve_polynomial(
                common + [t], basis, coefficients))

    def test_repeated_part_distinguished_normalization(self):
        # m_(2,2)(u,t)=m_(2,2)(u)+t^2*m_(2)(u), with no repeated-part
        # multiplicity two.  This is the smallest repeated-part marginal.
        common = [Fraction(2, 7), Fraction(3, 11)]
        poly = MOD.distinguished_polynomial(
            common, [[0, [2, 2]]], [Fraction(1)])
        self.assertEqual(poly, [common[0]**2 * common[1]**2,
                                0,
                                common[0]**2 + common[1]**2])

    def test_marginal_intervals_and_channels(self):
        alpha = Fraction(2, 5)
        eta = Fraction(3, 10)
        delta = Fraction(1, 10)

        def beta(r):
            return {1: Fraction(1, 4), 2: Fraction(7, 20),
                    3: Fraction(7, 20)}.get(r, Fraction(7, 20))

        # F=1+2t_1^2+2t_2^2.  One common coordinate is large.
        common = [Fraction(3, 20)]
        basis = [[0, []], [0, [2]]]
        coefficients = [Fraction(1), Fraction(2)]
        small, large = MOD.distinguished_intervals(
            common, alpha, eta, delta, beta)
        self.assertEqual(small, (0, Fraction(1, 10)))
        # The large cap is tighter than the total upper endpoint here:
        # beta(2)-L_c = 7/20-3/20 = 1/5.
        self.assertEqual(large, (Fraction(1, 10), Fraction(1, 5)))
        channels = [(1, 0, 0), (1, 1, 0), (1, 0, 1),
                    (2, 0, 0), (2, 1, 0), (2, 0, 1)]
        actual = MOD.marginal_multiplier_vector(
            common, basis, coefficients, channels,
            alpha, eta, delta, beta)
        c = common[0]
        # Independent literal antiderivatives for the two branches.
        def primitive(x):
            return (1 + 2 * c * c) * x + Fraction(2, 3) * x ** 3
        base_small = primitive(delta) - primitive(0)
        large_upper = Fraction(1, 5)
        base_large = primitive(large_upper) - primitive(delta)
        self.assertEqual(actual[0], base_small)
        self.assertEqual(actual[1], c * base_small)
        self.assertEqual(actual[2],
                         (1 + 2*c*c) * delta**2 / 2 + delta**4 / 2)
        self.assertEqual(actual[3], base_large)
        self.assertEqual(actual[4],
                         c * base_large +
                         (1 + 2*c*c) * (large_upper**2-delta**2)/2 +
                         (large_upper**4-delta**4)/2)
        self.assertEqual(actual[5], c * 0)

    def test_support_strict_threshold_and_cutoff(self):
        delta = Fraction(1, 10)
        alpha = Fraction(2, 5)
        eta = Fraction(3, 10)
        beta = lambda r: Fraction(1, 4)
        self.assertTrue(MOD.support_contains(
            [delta, Fraction(3, 20)], alpha, delta, beta))
        self.assertFalse(MOD.support_contains(
            [Fraction(11, 100), Fraction(3, 20)], alpha, delta, beta))
        self.assertEqual(MOD.distinguished_intervals(
            [Fraction(31, 100)], alpha, eta, delta, beta), (None, None))

    def test_delta_eta_and_cap_total_switch_boundaries(self):
        alpha = Fraction(2, 5)
        eta = Fraction(3, 10)
        delta = Fraction(1, 10)
        common = [Fraction(3, 20)]

        # At equality the cap and total restrictions give the same endpoint.
        beta_equal = lambda r: {1: Fraction(1, 4),
                                2: Fraction(2, 5)}.get(r, Fraction(2, 5))
        self.assertEqual(MOD.distinguished_intervals(
            common, alpha, eta, delta, beta_equal)[1],
            (delta, Fraction(1, 4)))
        beta_cap = lambda r: {1: Fraction(1, 4),
                              2: Fraction(39, 100)}.get(r, Fraction(39, 100))
        beta_total = lambda r: {1: Fraction(1, 4),
                                2: Fraction(41, 100)}.get(r, Fraction(41, 100))
        self.assertEqual(MOD.distinguished_intervals(
            common, alpha, eta, delta, beta_cap)[1],
            (delta, Fraction(6, 25)))
        self.assertEqual(MOD.distinguished_intervals(
            common, alpha, eta, delta, beta_total)[1],
            (delta, Fraction(1, 4)))

        # t=delta remains small; the right-hand point changes the large count.
        beta_threshold = lambda r: Fraction(1, 4)
        self.assertTrue(MOD.support_contains(
            [Fraction(3, 20), delta], alpha, delta, beta_threshold))
        self.assertFalse(MOD.support_contains(
            [Fraction(3, 20), delta + Fraction(1, 10**6)],
            alpha, delta, beta_threshold))

        # The common eta boundary is retained (measure-zero convention); any
        # point immediately above it has no distinguished interval.
        beta_eta = lambda r: Fraction(1, 2)
        self.assertNotEqual(MOD.distinguished_intervals(
            [eta], alpha, eta, delta, beta_eta), (None, None))
        self.assertEqual(MOD.distinguished_intervals(
            [eta + Fraction(1, 10**6)], alpha, eta, delta, beta_eta),
            (None, None))


if __name__ == "__main__":
    unittest.main()
