#!/usr/bin/env python3
"""Exact regressions for per-stratum total-degree-two multipliers."""

import os
import sys
import unittest
from fractions import Fraction as Q

HERE = os.path.dirname(os.path.abspath(__file__))
AGENT = os.path.abspath(os.path.join(HERE, ".."))
sys.path[:0] = [AGENT, os.path.join(AGENT, "src")]

import exact_integrator as ei  # noqa: E402
from stratum_linear import (  # noqa: E402
    StratumLinearEvaluator,
    independent_gram_indices,
    quadratic,
)
from stratum_quadratic import StratumQuadraticEvaluator  # noqa: E402


class StratumQuadraticTests(unittest.TestCase):
    @staticmethod
    def fixture():
        support = ei.OneStratumSupport(
            3, Q(13, 50), Q(1, 20), Q(6, 25),
            Q(3, 20), Q(4, 25), Q(17, 100))
        labels = [(0, ()), (1, ()), (0, (2,)), (0, (3,))]
        coefficients = [Q(2), Q(-3), Q(5), Q(7)]
        return support, labels, coefficients

    def test_degree_one_principal_submatrix_is_bitwise_identical(self):
        support, labels, coefficients = self.fixture()
        linear = StratumLinearEvaluator(
            support, labels, coefficients, Q).evaluate_forms()
        quadratic_forms = StratumQuadraticEvaluator(
            support, labels, coefficients, Q).evaluate_forms()
        qpos = {label: i for i, label in enumerate(quadratic_forms["labels"])}
        for matrix_name in ("a_matrix", "b_matrix"):
            expected = linear[matrix_name]
            observed = quadratic_forms[matrix_name]
            for i, left in enumerate(linear["labels"]):
                for j, right in enumerate(linear["labels"]):
                    self.assertEqual(observed[qpos[left]][qpos[right]],
                                     expected[i][j])
        for key in ("i_faces", "j_branch_domains", "i_orbit_groups",
                    "marginal_components"):
            self.assertEqual(quadratic_forms[key], linear[key])

    def test_signed_block_equals_direct_and_has_exact_sparsity(self):
        support, labels, coefficients = self.fixture()
        evaluator = StratumQuadraticEvaluator(
            support, labels, coefficients, Q)
        forms = evaluator.evaluate_forms()
        vector = [Q((-1) ** i * (i + 2), i + 3)
                  for i in range(len(forms["labels"]))]
        expected = (quadratic(forms["a_matrix"], vector, Q(0)),
                    quadratic(forms["b_matrix"], vector, Q(0)))
        direct = evaluator.evaluate_direct(vector)
        self.assertEqual(direct[:2], expected)
        self.assertEqual(direct[2:],
                         (forms["i_faces"], forms["j_branch_domains"]))
        for matrix in (forms["a_matrix"], forms["b_matrix"]):
            for i, (ri, _) in enumerate(forms["labels"]):
                for j, (rj, _) in enumerate(forms["labels"]):
                    self.assertEqual(matrix[i][j], matrix[j][i])
                    if matrix is forms["a_matrix"] and ri != rj:
                        self.assertEqual(matrix[i][j], 0)
                    if matrix is forms["b_matrix"] and abs(ri - rj) > 1:
                        self.assertEqual(matrix[i][j], 0)

    def test_k1_all_degree_two_entries_match_hand_integrals(self):
        d, bound = Q(1, 10), Q(2, 5)
        support = ei.OneStratumSupport(
            1, Q(1), d, Q(9, 10), bound, bound, bound)
        evaluator = StratumQuadraticEvaluator(
            support, [(0, ())], [Q(1)], Q)
        forms = evaluator.evaluate_forms()
        powers = evaluator.CHANNEL_POWERS

        def integral(lo, hi, exponent):
            return (hi ** (exponent + 1) - lo ** (exponent + 1)) / \
                (exponent + 1)

        def inner(label):
            r, p = label
            a, b = powers[p]
            if r == 0:
                return integral(Q(0), d, b) if a == 0 else Q(0)
            return integral(d, bound, a) if b == 0 else Q(0)

        for i, left in enumerate(forms["labels"]):
            rl, pl = left
            al, bl = powers[pl]
            for j, right in enumerate(forms["labels"]):
                rr, pr = right
                ar, br = powers[pr]
                if rl != rr:
                    expected_i = Q(0)
                elif rl == 0:
                    expected_i = (integral(Q(0), d, bl + br)
                                  if al + ar == 0 else Q(0))
                else:
                    expected_i = (integral(d, bound, al + ar)
                                  if bl + br == 0 else Q(0))
                self.assertEqual(forms["a_matrix"][i][j], expected_i)
                self.assertEqual(forms["b_matrix"][i][j],
                                 inner(left) * inner(right))

        selected, discarded = independent_gram_indices(
            forms["a_matrix"], forms["labels"])
        self.assertTrue(selected)
        self.assertEqual({forms["labels"][i] for i in discarded}, {
            (0, 1), (0, 3), (0, 4),
            (1, 2), (1, 4), (1, 5),
        })


if __name__ == "__main__":
    unittest.main()
