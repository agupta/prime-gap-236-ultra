#!/usr/bin/env python3
"""Exact small regression for direct D2 multiplier transfer semantics."""

import os
import sys
import copy
import hashlib
import tempfile
import unittest
from fractions import Fraction as Q

HERE = os.path.dirname(os.path.abspath(__file__))
AGENT = os.path.abspath(os.path.join(HERE, ".."))
sys.path[:0] = [AGENT, os.path.join(AGENT, "src")]

import exact_integrator as ei  # noqa: E402
from stratum_quadratic import StratumQuadraticEvaluator  # noqa: E402
from stratum_quadratic_transfer_decimal import (  # noqa: E402
    DirectQuadraticTransfer,
    PINNED,
    read_pinned_bytes,
    require_pinned_dependencies,
)


class QuadraticTransferTests(unittest.TestCase):
    def test_input_and_multiplier_snapshots_reject_mutation(self):
        with tempfile.NamedTemporaryFile() as handle:
            handle.write(b"pinned-input\n")
            handle.flush()
            expected = hashlib.sha256(b"pinned-input\n").hexdigest()
            raw, actual = read_pinned_bytes(handle.name, expected, "test input")
            self.assertEqual((raw, actual), (b"pinned-input\n", expected))
            handle.seek(0)
            handle.write(b"mutated-data\n")
            handle.truncate()
            handle.flush()
            with self.assertRaises(SystemExit):
                read_pinned_bytes(handle.name, expected, "test input")

    def test_full_dependency_closure_rejects_transitive_mutation(self):
        require_pinned_dependencies(dict(PINNED))
        for key in ("stratum_amplitude", "grouped", "integrator",
                    "scheduled_basis", "scheduled_verifier"):
            changed = copy.deepcopy(PINNED)
            changed[key] = "0" * 64
            with self.assertRaises(SystemExit):
                require_pinned_dependencies(changed)

    def test_per_r_direct_equals_independent_monolithic_direct(self):
        support = ei.OneStratumSupport(
            3, Q(13, 50), Q(1, 20), Q(6, 25),
            Q(3, 20), Q(4, 25), Q(17, 100))
        labels = [(0, ()), (1, ()), (0, (2,)), (0, (3,))]
        base = [Q(2), Q(-3), Q(5), Q(7)]
        max_r = 3
        vector = [Q((-1) ** i * (i + 2), i + 3)
                  for i in range(6 * (max_r + 1))]
        reference = StratumQuadraticEvaluator(
            support, labels, base, Q).evaluate_direct(vector)

        evaluator = DirectQuadraticTransfer(support, labels, base, Q)
        amplitudes = {r: tuple(vector[6 * r:6 * r + 6])
                      for r in range(max_r + 1)}
        grouped = evaluator.square_residual_terms()
        i_pieces, i_faces = [], 0
        for r in evaluator._r_values_i():
            value, count = evaluator.evaluate_i_r_transfer(
                grouped, amplitudes, r)
            i_pieces.append(value)
            i_faces += count
        _, lrs, by_lr = evaluator._j_component_data()
        j_pieces, domains = [], 0
        for r in evaluator._r_values_j():
            value, count = evaluator.evaluate_j_r_transfer(
                lrs, by_lr, amplitudes, r)
            j_pieces.append(value)
            domains += count
        self.assertEqual(sum(i_pieces, Q(0)), reference[0])
        self.assertEqual(support.k * sum(j_pieces, Q(0)), reference[1])
        self.assertEqual((i_faces, domains), reference[2:])


if __name__ == "__main__":
    unittest.main()
