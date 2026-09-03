#!/usr/bin/env python3

from __future__ import annotations

from fractions import Fraction as Q
import importlib.util
from pathlib import Path
import sys
import unittest


SOURCE = (Path(__file__).resolve().parents[1] /
          "code/wide_frontier_batched_face_kernel_v1.py")
SPEC = importlib.util.spec_from_file_location("wide_face_kernel_tested", SOURCE)
F = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = F
SPEC.loader.exec_module(F)
M, P = F.M, F.P


class FaceKernelTests(unittest.TestCase):
    def setUp(self):
        self.k = 3
        self.delta, self.eta = Q(1, 20), Q(1, 5)
        self.left = P.ScheduledSupport.make(
            self.k, Q(13, 50), self.delta, self.eta,
            (Q(9, 50), Q(1, 5), Q(11, 50)))
        self.right = P.ScheduledSupport.make(
            self.k, Q(6, 25), self.delta, self.eta,
            (Q(4, 25), Q(19, 100), Q(21, 100)))
        labels = tuple(P.ei.even_basis(2))
        self.left_coordinates = tuple(
            P.components((label,), (Q(1),), self.k) for label in labels)
        self.right_coordinates = tuple(
            P.components((label,), (Q(-1 if i == 1 else 1),), self.k)
            for i, label in enumerate(labels))

    def test_sum_of_faces_is_full_literal_matrix(self):
        total = [[Q(0) for _ in self.right_coordinates]
                 for _ in self.left_coordinates]
        observed_integrals = 0
        for r, h in F.all_faces(self.left, self.right, self.eta):
            block, counters = F.cross_face_matrix(
                self.left, self.left_coordinates,
                self.right, self.right_coordinates, self.eta, r, h)
            observed_integrals += counters["scalar_integrals"]
            for i in range(len(total)):
                for j in range(len(total[i])):
                    total[i][j] += block[i][j]
        expected = M.scalar_replay(
            self.left, self.left_coordinates,
            self.right, self.right_coordinates, self.eta)
        self.assertEqual(total, expected)
        self.assertGreater(observed_integrals, 0)

    def test_each_face_transposes_exactly(self):
        for r, h in F.all_faces(self.left, self.right, self.eta):
            forward, _ = F.cross_face_matrix(
                self.left, self.left_coordinates,
                self.right, self.right_coordinates, self.eta, r, h)
            reverse, _ = F.cross_face_matrix(
                self.right, self.right_coordinates,
                self.left, self.left_coordinates, self.eta, r, h)
            self.assertEqual(forward,
                             [list(row) for row in zip(*reverse)])

    def test_inventory_matches_grouped_selected_rows(self):
        by_r = {}
        for r, h in F.all_faces(self.left, self.right, self.eta):
            block, _ = F.cross_face_matrix(
                self.left, self.left_coordinates,
                self.right, self.right_coordinates, self.eta, r, h)
            if r not in by_r:
                by_r[r] = [[Q(0) for _ in self.right_coordinates]
                           for _ in self.left_coordinates]
            for i in range(len(block)):
                for j in range(len(block[i])):
                    by_r[r][i][j] += block[i][j]
        for r, expected in by_r.items():
            got, _ = M.cross_matrix(
                self.left, self.left_coordinates,
                self.right, self.right_coordinates, self.eta,
                selected_r=r)
            self.assertEqual(got, expected)

    def test_invalid_faces_and_types_fail_closed(self):
        args = (self.left, self.left_coordinates,
                self.right, self.right_coordinates, self.eta)
        with self.assertRaises(TypeError):
            F.cross_face_matrix(*args, True, 0)
        with self.assertRaises(ValueError):
            F.cross_face_matrix(*args, -1, 0)
        with self.assertRaises(ValueError):
            F.cross_face_matrix(*args, 0, 99)
        with self.assertRaises(ValueError):
            F.cross_face_matrix(self.left, (), self.right,
                                self.right_coordinates, self.eta, 0, 0)

    def test_dependency_pin(self):
        self.assertEqual(F.sha256(F.BATCH_PATH), F.PINNED_BATCH_SHA256)


if __name__ == "__main__":
    unittest.main()
