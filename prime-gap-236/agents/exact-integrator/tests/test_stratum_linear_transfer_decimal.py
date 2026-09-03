#!/usr/bin/env python3
"""Exact small regressions for the transferred-affine direct J path."""

import os
import sys
import hashlib
import copy
import tempfile
import unittest
from fractions import Fraction as Q

HERE = os.path.dirname(os.path.abspath(__file__))
AGENT = os.path.abspath(os.path.join(HERE, ".."))
sys.path[:0] = [AGENT, os.path.join(AGENT, "src")]

import exact_integrator as ei  # noqa: E402
from stratum_linear import StratumLinearEvaluator, quadratic  # noqa: E402
from stratum_linear_transfer_decimal import (  # noqa: E402
    TransferEvaluator,
    contract,
    read_pinned_bytes,
    require_exact_stage_dependencies,
    EXPECTED_STAGE_DEPENDENCIES,
)


class TransferDirectTests(unittest.TestCase):
    def test_pinned_stage_bytes_reject_hash_and_post_read_mutation(self):
        with tempfile.NamedTemporaryFile() as handle:
            handle.write(b"complete-stage\n")
            handle.flush()
            expected = hashlib.sha256(b"complete-stage\n").hexdigest()
            raw, actual = read_pinned_bytes(handle.name, expected, "test stage")
            self.assertEqual(raw, b"complete-stage\n")
            self.assertEqual(actual, expected)
            with self.assertRaises(SystemExit):
                read_pinned_bytes(handle.name, "0" * 64, "test stage")
            handle.seek(0)
            handle.write(b"mutated-stage!\n")
            handle.truncate()
            handle.flush()
            with self.assertRaises(SystemExit):
                read_pinned_bytes(handle.name, expected, "test stage")

    def test_stage_dependency_dictionary_is_exact_not_subset(self):
        require_exact_stage_dependencies(dict(EXPECTED_STAGE_DEPENDENCIES))
        for mutation in ("missing", "extra", "changed"):
            candidate = copy.deepcopy(EXPECTED_STAGE_DEPENDENCIES)
            if mutation == "missing":
                candidate.pop("robust_solver")
            elif mutation == "extra":
                candidate["untracked"] = "0" * 64
            else:
                candidate["grouped"] = "0" * 64
            with self.assertRaises(SystemExit):
                require_exact_stage_dependencies(candidate)

    def test_transfer_j_equals_independent_full_direct_exactly(self):
        support = ei.OneStratumSupport(
            3, Q(13, 50), Q(1, 20), Q(6, 25),
            Q(3, 20), Q(4, 25), Q(17, 100))
        labels = [(0, ()), (1, ()), (0, (2,)), (0, (3,))]
        base = [Q(2), Q(-3), Q(5), Q(7)]
        reference = StratumLinearEvaluator(support, labels, base, Q)
        forms = reference.evaluate_forms()
        vector = [Q((-1) ** i * (i + 2), i + 3)
                  for i in range(len(forms["labels"]))]
        direct = reference.evaluate_direct(vector)

        evaluator = TransferEvaluator(support, labels, base, Q)
        amplitudes = {r: tuple(vector[3 * r:3 * r + 3])
                      for r in range(len(vector) // 3)}
        _, lrs, by_lr = evaluator._j_component_data()
        pieces, domains = [], 0
        for r in evaluator._r_values_j():
            value, count = evaluator.evaluate_j_r_transfer(
                lrs, by_lr, amplitudes, r)
            pieces.append(value)
            domains += count
        self.assertEqual(support.k * sum(pieces, Q(0)), direct[1])
        self.assertEqual(domains, direct[3])

    def test_triangular_entry_contraction_matches_dense_quadratic(self):
        entries = {
            ((0, 0), (0, 0)): Q(2),
            ((0, 1), (0, 0)): Q(-3),
            ((0, 1), (0, 1)): Q(5),
            ((1, 0), (1, 0)): Q(7),
        }
        coefficients = {(0, 0): Q(11), (0, 1): Q(-13), (1, 0): Q(17)}
        labels = list(coefficients)
        dense = [[Q(0) for _ in labels] for _ in labels]
        positions = {label: i for i, label in enumerate(labels)}
        for (left, right), value in entries.items():
            i, j = positions[left], positions[right]
            dense[i][j] += value
            if i != j:
                dense[j][i] += value
        vector = [coefficients[label] for label in labels]
        self.assertEqual(contract(entries, coefficients),
                         quadratic(dense, vector, Q(0)))


if __name__ == "__main__":
    unittest.main()
