#!/usr/bin/env python3

from __future__ import annotations

from fractions import Fraction as Q
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest


FILE = Path(__file__).resolve()
SOURCE = FILE.parents[1] / "code/active25_outer_b4_i_block_v1.py"
_spec = importlib.util.spec_from_file_location("active25_b4_i_tested", SOURCE)
M = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = M
_spec.loader.exec_module(M)


class Active25OuterB4ITests(unittest.TestCase):
    def test_target_pins_labels_and_counts(self):
        high, low = M.validate_target()
        self.assertEqual(len(M.basis_labels()), 10)
        self.assertEqual((high.max_large(), low.max_large()), (25, 25))
        self.assertEqual(high.schedule, low.schedule)
        self.assertGreater(high.alpha, low.alpha)

    def test_k3_literal_grouped_gram_and_shell_difference(self):
        k = 3
        delta = Q(1, 10)
        eta = Q(3, 10)
        schedule = (Q(1, 4), Q(3, 10), Q(7, 20))
        high = M.A25.shell.ScheduledStratumSupport.make(
            k, Q(2, 5), eta, delta, schedule)
        low = M.A25.shell.ScheduledStratumSupport.make(
            k, Q(7, 20), eta, delta, schedule)
        labels = tuple(M.EI.even_basis(2))
        ah, al, shell = M.matrices(high, low, labels)
        vectors = (
            (Q(1), Q(0), Q(0), Q(0)),
            (Q(1), Q(-2), Q(3), Q(-4)),
            (Q(2), Q(1), Q(-1), Q(3)),
        )
        for vector in vectors:
            literal_high = M.grouped_quadratic(high, labels, vector)
            literal_low = M.grouped_quadratic(low, labels, vector)
            self.assertEqual(M.exact_quadratic(ah, vector), literal_high)
            self.assertEqual(M.exact_quadratic(al, vector), literal_low)
            self.assertEqual(M.exact_quadratic(shell, vector),
                             literal_high - literal_low)

    def test_exact_ldl_and_rank(self):
        matrix = [[Q(4), Q(2), Q(0)],
                  [Q(2), Q(5), Q(1)],
                  [Q(0), Q(1), Q(3)]]
        lower, pivots = M.ldl_pivots(matrix)
        self.assertEqual(pivots, [Q(4), Q(4), Q(11, 4)])
        self.assertEqual(M.exact_rank(matrix), 3)
        self.assertTrue(all(x > 0 for x in pivots))
        self.assertEqual(len(lower), 3)
        with self.assertRaises(ArithmeticError):
            M.ldl_pivots([[Q(1), Q(1)], [Q(1), Q(1)]])
        self.assertEqual(M.exact_rank([[Q(1), Q(1)], [Q(1), Q(1)]]), 1)

    def test_invalid_geometry_and_dimensions_fail(self):
        high, low = M.validate_target()
        with self.assertRaises(ValueError):
            list(M.gram_rows(low, high, M.basis_labels()))
        with self.assertRaises(ValueError):
            M.exact_quadratic([[Q(1)]], (Q(1), Q(2)))
        with self.assertRaises(ValueError):
            M.ldl_pivots([[Q(1), Q(2)], [Q(0), Q(1)]])

    def test_exclusive_publication_and_alias(self):
        closure = M._closure_snapshots()
        with self.assertRaises(ValueError):
            M.publish_new(M.SPEC_FILE, {"x": 1}, closure)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "result.json"
            digest = M.publish_new(path, {"status": "test"}, closure)
            self.assertEqual(digest, M.sha256_file(path))
            with self.assertRaises(FileExistsError):
                M.publish_new(path, {"status": "replacement"}, closure)


if __name__ == "__main__":
    unittest.main()
