#!/usr/bin/env python3
"""Exact tests for the fixed-vector stratum-amplitude evaluator."""

import os
import sys
import unittest
from fractions import Fraction as Q

HERE = os.path.dirname(os.path.abspath(__file__))
AGENT = os.path.abspath(os.path.join(HERE, ".."))
SRC = os.path.join(AGENT, "src")
sys.path[:0] = [AGENT, SRC]

import exact_integrator as ei  # noqa: E402
from grouped_fixed_vector import GroupedEvaluator  # noqa: E402
from stratum_amplitude import StratumAmplitudeEvaluator  # noqa: E402
from stratum_integrator import StratumSupport  # noqa: E402


class StratumAmplitudeTests(unittest.TestCase):
    def setUp(self):
        params = (3, Q(13, 50), Q(1, 20), Q(6, 25),
                  Q(3, 20), Q(4, 25), Q(17, 100))
        self.support = ei.OneStratumSupport(*params)
        self.tagged = StratumSupport(*params)
        self.labels = [(0, ()), (1, ()), (0, (2,)), (0, (3,))]
        self.coefficients = [Q(2), Q(-3), Q(5), Q(7)]

    def evaluator(self):
        return StratumAmplitudeEvaluator(
            self.support, self.labels, self.coefficients, Q)

    def expected_entry(self, left_r, right_r, j_form=False):
        answer = Q(0)
        for i, left in enumerate(self.labels):
            for j, right in enumerate(self.labels):
                if j_form:
                    moment = self.tagged.basis_j_in_strata(
                        left_r, left, right_r, right)
                    moment *= self.tagged.k
                else:
                    moment = self.tagged.basis_m1_in_strata(
                        left_r, left, right_r, right)
                answer += self.coefficients[i] * self.coefficients[j] * moment
        return answer

    def test_blocks_equal_pairwise_tagged_entries_and_all_ones(self):
        evaluator = self.evaluator()
        result = evaluator.evaluate_all_blocks()
        a = result["a_diagonal"]
        b = result["b_diagonal"]
        c = result["b_superdiagonal"]
        for r in range(len(a)):
            self.assertEqual(a[r], self.expected_entry(r, r, False), ("I", r))
            self.assertEqual(b[r], self.expected_entry(r, r, True), ("J", r, r))
            if r + 1 < len(a):
                self.assertEqual(c[r], self.expected_entry(
                    r, r + 1, True), ("J", r, r + 1))

        scalar = GroupedEvaluator(
            self.support, self.labels, self.coefficients, Q)
        denominator, _, _ = scalar.evaluate_i()
        j_value, _, _ = scalar.evaluate_j()
        self.assertEqual(result["all_ones_denominator"], denominator)
        self.assertEqual(result["all_ones_numerator"], self.support.k * j_value)
        self.assertEqual(sum(result["i_by_r"].values(), Q(0)), denominator)
        self.assertEqual(sum((sum(block, Q(0))
                              for block in result["j_by_common_r"].values()),
                             Q(0)), j_value)

    def test_signed_amplitude_direct_block_and_pairwise_agree(self):
        evaluator = self.evaluator()
        result = evaluator.evaluate_all_blocks()
        amplitudes = [Q(3, 2), Q(-2), Q(5, 3), Q(-7, 4)]
        denominator = evaluator.tridiagonal_quadratic(
            result["a_diagonal"], (), amplitudes, Q(0))
        numerator = evaluator.tridiagonal_quadratic(
            result["b_diagonal"], result["b_superdiagonal"],
            amplitudes, Q(0))
        direct = evaluator.evaluate_amplitudes_direct(
            amplitudes, result["i_by_r"])
        self.assertEqual(direct[0], denominator)
        self.assertEqual(direct[1], numerator)

        expected_denominator = Q(0)
        expected_numerator = Q(0)
        for r, ar in enumerate(amplitudes):
            for s, ass in enumerate(amplitudes):
                expected_denominator += ar * ass * self.expected_entry(
                    r, s, False)
                expected_numerator += ar * ass * self.expected_entry(
                    r, s, True)
                if abs(r - s) > 1:
                    self.assertEqual(self.expected_entry(r, s, True), 0)
        self.assertEqual(denominator, expected_denominator)
        self.assertEqual(numerator, expected_numerator)

    def test_serial_and_fork_blocks_agree_entrywise(self):
        serial = self.evaluator().evaluate_all_blocks(workers=1)
        parallel = self.evaluator().evaluate_all_blocks(workers=2)
        for key in ("i_by_r", "j_by_common_r", "a_diagonal", "b_diagonal",
                    "b_superdiagonal", "all_ones_denominator",
                    "all_ones_numerator", "i_orbit_groups", "i_faces",
                    "marginal_components", "j_branch_integrals"):
            self.assertEqual(parallel[key], serial[key], key)

    def test_k1_boundary_tie_is_assigned_once(self):
        support = ei.OneStratumSupport(
            1, Q(1, 10), Q(1, 10), Q(1, 10),
            Q(3, 20), Q(3, 20), Q(17, 100))
        evaluator = StratumAmplitudeEvaluator(
            support, [(0, ())], [Q(1)], Q)
        result = evaluator.evaluate_all_blocks()
        scalar = GroupedEvaluator(support, [(0, ())], [Q(1)], Q)
        denominator, _, _ = scalar.evaluate_i()
        j_value, _, _ = scalar.evaluate_j()
        self.assertEqual(result["all_ones_denominator"], denominator)
        self.assertEqual(result["all_ones_numerator"], j_value)
        self.assertEqual(denominator, Q(1, 10))
        self.assertEqual(j_value, Q(1, 100))


if __name__ == "__main__":
    unittest.main()
