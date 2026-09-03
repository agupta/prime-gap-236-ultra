#!/usr/bin/env python3

"""Independent exact cross-checks for importance-discovery point algebra."""

import importlib
import itertools
import random
import sys
import unittest
from fractions import Fraction
from math import comb
from pathlib import Path


HERE = Path(__file__).resolve()
CODE = HERE.parents[1] / "code"
sys.path.insert(0, str(CODE))
MOD = importlib.import_module("importance_point_eval")


def brute_monomial(point, partition):
    if not partition:
        return Fraction(1)
    answer = Fraction(0)
    for coordinates in itertools.combinations(range(len(point)), len(partition)):
        for exponents in set(itertools.permutations(partition)):
            term = Fraction(1)
            for coordinate, exponent in zip(coordinates, exponents):
                term *= point[coordinate] ** exponent
            answer += term
    return answer


def interpolate(nodes, values):
    """Independent Fraction Vandermonde solve; ascending coefficients."""
    n = len(nodes)
    rows = [[x ** power for power in range(n)] + [value]
            for x, value in zip(nodes, values)]
    for column in range(n):
        pivot = next(row for row in range(column, n)
                     if rows[row][column] != 0)
        rows[column], rows[pivot] = rows[pivot], rows[column]
        scale = rows[column][column]
        rows[column] = [x / scale for x in rows[column]]
        for row in range(n):
            if row == column:
                continue
            scale = rows[row][column]
            rows[row] = [x - scale * y
                         for x, y in zip(rows[row], rows[column])]
    return [rows[row][-1] for row in range(n)]


def poly_mul(left, right):
    answer = [Fraction(0)] * (len(left) + len(right) - 1)
    for i, x in enumerate(left):
        for j, y in enumerate(right):
            answer[i + j] += x * y
    return answer


def affine_power(constant, exponent):
    return [comb(exponent, degree) * constant ** (exponent - degree)
            for degree in range(exponent + 1)]


def integrate(poly, lower, upper):
    return sum(coefficient * (upper ** (degree + 1) -
                              lower ** (degree + 1)) / (degree + 1)
               for degree, coefficient in enumerate(poly))


class ImportanceHostileCrosscheck(unittest.TestCase):
    def test_all_small_repeated_part_orbits(self):
        point = (Fraction(-2, 7), Fraction(3, 11),
                 Fraction(5, 13), Fraction(-7, 17))
        partitions = [()]
        for length in range(1, 5):
            partitions.extend(tuple(sorted(parts, reverse=True))
                              for parts in itertools.combinations_with_replacement(
                                  range(1, 5), length))
        evaluator = MOD.MonomialSymmetricPointEvaluator(partitions)
        actual = evaluator.evaluate(point)
        for partition in partitions:
            self.assertEqual(actual[partition],
                             brute_monomial(point, partition))

    def test_random_exact_marginals_by_independent_interpolation(self):
        alpha = Fraction(2, 5)
        eta = Fraction(3, 10)
        delta = Fraction(1, 10)

        def beta(r):
            return {1: Fraction(1, 4), 2: Fraction(7, 20)}.get(
                r, Fraction(7, 20))

        basis = [[0, []], [2, []], [0, [1]], [1, [2, 1]],
                 [0, [2, 2]]]
        coefficients = [Fraction(7, 3), Fraction(-5, 8), Fraction(11, 9),
                        Fraction(13, 17), Fraction(-19, 23)]
        channels = [(r, a, b) for r in range(4)
                    for a, b in ((0, 0), (1, 0), (0, 1),
                                 (2, 0), (1, 1), (0, 2))]
        rng = random.Random(2364801)
        choices = (Fraction(0), Fraction(1, 20), delta,
                   delta + Fraction(1, 1000), Fraction(3, 20),
                   Fraction(11, 50))
        checked = 0
        for _ in range(200):
            common = [rng.choice(choices), rng.choice(choices)]
            if sum(common) > eta:
                continue
            actual = MOD.marginal_multiplier_vector(
                common, basis, coefficients, channels,
                alpha, eta, delta, beta)

            # Degree at most four.  Recover t -> F(common,t) without using
            # distinguished_polynomial or its orbit-splitting recurrence.
            nodes = [Fraction(i, 37) for i in range(5)]
            values = [MOD.evaluate_sieve_polynomial(
                common + [t], basis, coefficients) for t in nodes]
            polynomial = interpolate(nodes, values)
            common_sum = sum(common)
            large = [x for x in common if x > delta]
            small = [x for x in common if x <= delta]
            r, large_sum, small_sum = len(large), sum(large), sum(small)
            total_upper = alpha - common_sum
            small_interval = None
            if (r == 0 or large_sum <= beta(r)) and min(
                    delta, total_upper) > 0:
                small_interval = (Fraction(0), min(delta, total_upper))
            large_upper = min(total_upper, beta(r + 1) - large_sum)
            large_interval = ((delta, large_upper)
                              if large_upper > delta else None)

            expected = []
            for target_r, a, b in channels:
                value = Fraction(0)
                if target_r == r and small_interval is not None:
                    multiplier = [large_sum ** a * x
                                  for x in affine_power(small_sum, b)]
                    value += integrate(poly_mul(polynomial, multiplier),
                                       *small_interval)
                if target_r == r + 1 and large_interval is not None:
                    multiplier = [small_sum ** b * x
                                  for x in affine_power(large_sum, a)]
                    value += integrate(poly_mul(polynomial, multiplier),
                                       *large_interval)
                expected.append(value)
            self.assertEqual(actual, expected)
            checked += 1
        self.assertGreaterEqual(checked, 100)


if __name__ == "__main__":
    unittest.main()
