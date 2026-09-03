#!/usr/bin/env python3
"""Small exact regressions for the batched Decimal D1 traversal."""

import os
import sys
import unittest
from fractions import Fraction as Q

HERE = os.path.dirname(os.path.abspath(__file__))
AGENT = os.path.abspath(os.path.join(HERE, ".."))
sys.path[:0] = [AGENT, os.path.join(AGENT, "src")]

import exact_integrator as ei  # noqa: E402
from stratum_linear import StratumLinearEvaluator  # noqa: E402
from stratum_linear_decimal import (  # noqa: E402
    BatchedStratumLinearEvaluator,
    assemble,
)


class BatchedStratumLinearTests(unittest.TestCase):
    def setUp(self):
        self.support = ei.OneStratumSupport(
            3, Q(13, 50), Q(1, 20), Q(6, 25),
            Q(3, 20), Q(4, 25), Q(17, 100))
        self.labels = [(0, ()), (1, ()), (0, (2,)), (0, (3,))]
        self.coefficients = [Q(2), Q(-3), Q(5), Q(7)]

    def test_batched_forms_equal_independent_channel_traversal_exactly(self):
        reference = StratumLinearEvaluator(
            self.support, self.labels, self.coefficients, Q).evaluate_forms()
        evaluator = BatchedStratumLinearEvaluator(
            self.support, self.labels, self.coefficients, Q, 15)
        i_entries, _, groups, faces = evaluator.evaluate_i_batched(workers=1)
        j_entries, _, components, domains, channels = \
            evaluator.evaluate_j_batched(workers=1)
        labels, a_matrix, b_matrix = assemble(evaluator, i_entries, j_entries)
        self.assertEqual(labels, reference["labels"])
        self.assertEqual(a_matrix, reference["a_matrix"])
        self.assertEqual(b_matrix, reference["b_matrix"])
        self.assertEqual((groups, faces, components, domains),
                         (reference["i_orbit_groups"], reference["i_faces"],
                          reference["marginal_components"],
                          reference["j_branch_domains"]))
        self.assertGreater(channels, 0)

    def test_exact_serial_equals_fork_two(self):
        serial = BatchedStratumLinearEvaluator(
            self.support, self.labels, self.coefficients, Q, 1)
        parallel = BatchedStratumLinearEvaluator(
            self.support, self.labels, self.coefficients, Q, 1)
        self.assertEqual(serial.evaluate_i_batched(workers=1),
                         parallel.evaluate_i_batched(workers=2))
        self.assertEqual(serial.evaluate_j_batched(workers=1),
                         parallel.evaluate_j_batched(workers=2))


if __name__ == "__main__":
    unittest.main()
