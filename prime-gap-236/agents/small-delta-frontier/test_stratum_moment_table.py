#!/usr/bin/env python3
"""Exact low-k tests for the reusable L/Z stratum moment table."""

from __future__ import annotations

import os
import sys
import unittest
from fractions import Fraction as Q
from pathlib import Path


HERE = Path(__file__).resolve().parent
EI = HERE.parent / "exact-integrator"
sys.path[:0] = [str(HERE), str(EI), str(EI / "src")]

import exact_integrator as ei  # noqa: E402
from stratum_moment_table import (  # noqa: E402
    StratumMomentTableEvaluator,
    aggregate_powers,
    channel_powers,
    quadratic,
)
from stratum_quadratic import StratumQuadraticEvaluator  # noqa: E402


class MomentTableTests(unittest.TestCase):
    @staticmethod
    def fixture():
        support = ei.OneStratumSupport(
            3, Q(13, 50), Q(1, 20), Q(6, 25),
            Q(3, 20), Q(4, 25), Q(17, 100))
        labels = [(0, ()), (1, ()), (0, (2,)), (0, (3,))]
        coefficients = [Q(2), Q(-3), Q(5), Q(7)]
        return support, labels, coefficients

    def test_channel_and_table_counts(self):
        self.assertEqual(channel_powers(3), (
            (0, 0), (1, 0), (0, 1), (2, 0), (1, 1), (0, 2),
            (3, 0), (2, 1), (1, 2), (0, 3)))
        self.assertEqual(len(aggregate_powers(6)), 28)
        # A full ordered distinguished-moment family has 180 tagged moments.
        count = sum(len(aggregate_powers(6 - j - k))
                    for j in range(4) for k in range(4))
        self.assertEqual(count, 180)

    def test_degree_two_matrix_matches_independent_channel_evaluator(self):
        support, labels, coefficients = self.fixture()
        table = StratumMomentTableEvaluator(
            support, labels, coefficients, Q, degree=2).evaluate_moment_forms()
        direct = StratumQuadraticEvaluator(
            support, labels, coefficients, Q).evaluate_forms()
        self.assertEqual(table["labels"], direct["labels"])
        self.assertEqual(table["a_matrix"], direct["a_matrix"])
        self.assertEqual(table["b_matrix"], direct["b_matrix"])
        self.assertEqual(table["i_faces"], direct["i_faces"])
        self.assertEqual(table["j_branch_domains"],
                         direct["j_branch_domains"])
        vector = [Q((-1) ** i * (i + 2), i + 3)
                  for i in range(len(table["labels"]))]
        self.assertEqual(
            quadratic(table["a_matrix"], vector),
            quadratic(direct["a_matrix"], vector))
        self.assertEqual(
            quadratic(table["b_matrix"], vector),
            quadratic(direct["b_matrix"], vector))
        self.assertLess(table["j_moment_products"],
                        direct["j_channel_integrals"])

    def test_k1_degree_three_matches_literal_hand_integrals(self):
        delta, cap = Q(1, 10), Q(2, 5)
        support = ei.OneStratumSupport(
            1, Q(1), delta, Q(9, 10), cap, cap, cap)
        evaluator = StratumMomentTableEvaluator(
            support, [(0, ())], [Q(1)], Q, degree=3)
        forms = evaluator.evaluate_moment_forms()
        powers = evaluator.moment_channels

        def integral(lo, hi, exponent):
            return (hi ** (exponent + 1) - lo ** (exponent + 1)) / \
                (exponent + 1)

        def marginal(label):
            r, p = label
            a, b = powers[p]
            if r == 0:
                return integral(Q(0), delta, b) if a == 0 else Q(0)
            return integral(delta, cap, a) if b == 0 else Q(0)

        for i, left in enumerate(forms["labels"]):
            rl, pl = left
            al, bl = powers[pl]
            for j, right in enumerate(forms["labels"]):
                rr, pr = right
                ar, br = powers[pr]
                if rl != rr:
                    expected_i = Q(0)
                elif rl == 0:
                    expected_i = (integral(Q(0), delta, bl + br)
                                  if al + ar == 0 else Q(0))
                else:
                    expected_i = (integral(delta, cap, al + ar)
                                  if bl + br == 0 else Q(0))
                self.assertEqual(forms["a_matrix"][i][j], expected_i)
                self.assertEqual(forms["b_matrix"][i][j],
                                 marginal(left) * marginal(right))


if __name__ == "__main__":
    unittest.main()
