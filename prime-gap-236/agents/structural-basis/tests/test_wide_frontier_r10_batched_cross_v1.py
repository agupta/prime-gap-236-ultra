#!/usr/bin/env python3

from __future__ import annotations

from fractions import Fraction as Q
import importlib.util
from pathlib import Path
import sys
import unittest


SOURCE = (Path(__file__).resolve().parents[1] /
          "code/wide_frontier_r10_batched_cross_v1.py")
SPEC = importlib.util.spec_from_file_location("frontier_batch_tested", SOURCE)
M = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = M
SPEC.loader.exec_module(M)
B, P = M.B, M.P


class BatchedCrossTests(unittest.TestCase):
    def setUp(self):
        self.k = 3
        delta, eta = Q(1, 20), Q(1, 5)
        left_schedule = (Q(9, 50), Q(1, 5), Q(11, 50))
        right_schedule = (Q(4, 25), Q(19, 100), Q(21, 100))
        self.left = P.ScheduledSupport.make(
            self.k, Q(13, 50), delta, eta, left_schedule)
        self.right = P.ScheduledSupport.make(
            self.k, Q(6, 25), delta, eta, right_schedule)
        labels = tuple(P.ei.even_basis(2))
        self.left_coordinates = tuple(
            P.components((label,), (Q(1),), self.k) for label in labels)
        # Include one signed coordinate to exercise coefficient aggregation.
        self.right_coordinates = tuple(
            P.components((label,), (Q(-1 if index == 1 else 1),), self.k)
            for index, label in enumerate(labels))
        self.eta = eta

    def test_full_matrix_equals_scalar_literal(self):
        got, counters = M.cross_matrix(
            self.left, self.left_coordinates,
            self.right, self.right_coordinates, self.eta)
        expected = M.scalar_replay(
            self.left, self.left_coordinates,
            self.right, self.right_coordinates, self.eta)
        self.assertEqual(got, expected)
        self.assertGreater(counters["branch_domains"], 0)
        self.assertGreater(counters["scalar_integrals"], 0)
        self.assertLess(counters["density_cache_misses"],
                        counters["scalar_integrals"])

    def test_transpose_symmetry(self):
        forward, _ = M.cross_matrix(
            self.left, self.left_coordinates,
            self.right, self.right_coordinates, self.eta)
        reverse, _ = M.cross_matrix(
            self.right, self.right_coordinates,
            self.left, self.left_coordinates, self.eta)
        self.assertEqual(forward, [list(row) for row in zip(*reverse)])

    def test_selected_rows_sum_to_full(self):
        full, _ = M.cross_matrix(
            self.left, self.left_coordinates,
            self.right, self.right_coordinates, self.eta)
        total = [[Q(0) for _ in self.right_coordinates]
                 for _ in self.left_coordinates]
        max_r = min(self.k - 1, self.left.max_large(),
                    self.right.max_large())
        for r in range(max_r + 1):
            block, _ = M.cross_matrix(
                self.left, self.left_coordinates,
                self.right, self.right_coordinates, self.eta,
                selected_r=r)
            for i in range(len(total)):
                for j in range(len(total[i])):
                    total[i][j] += block[i][j]
        self.assertEqual(total, full)

    def test_base_source_pin(self):
        self.assertEqual(M.sha256(M.BASE_PATH), M.PINNED_BASE_SHA256)


if __name__ == "__main__":
    unittest.main()
