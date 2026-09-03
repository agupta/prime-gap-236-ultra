#!/usr/bin/env python3

from __future__ import annotations

from fractions import Fraction as Q
import importlib.util
from pathlib import Path
import sys
import unittest


FILE = Path(__file__).resolve()
SOURCE = FILE.parents[1] / "code/active25_outer_b4_i_block_v2.py"
_spec = importlib.util.spec_from_file_location("active25_b4_i_v2_tested", SOURCE)
M = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = M
_spec.loader.exec_module(M)


class CountingSupport:
    def __init__(self, support):
        self.support = support
        self.calls = 0
        for name in ("k", "delta", "schedule", "alpha"):
            setattr(self, name, getattr(support, name))

    def basis_m1(self, left, right):
        self.calls += 1
        return self.support.basis_m1(left, right)


class Active25OuterB4IV2Tests(unittest.TestCase):
    def test_exactly_55_pairs_not_v1_ordered_100(self):
        k = 3
        delta, eta = Q(1, 10), Q(3, 10)
        schedule = (Q(1, 4), Q(3, 10), Q(7, 20))
        high = M.V1.A25.shell.ScheduledStratumSupport.make(
            k, Q(2, 5), eta, delta, schedule)
        low = M.V1.A25.shell.ScheduledStratumSupport.make(
            k, Q(7, 20), eta, delta, schedule)
        labels = M.V1.basis_labels()
        counted_high, counted_low = CountingSupport(high), CountingSupport(low)
        ah, al, shell, pairs = M.upper_triangle_matrices(
            counted_high, counted_low, labels)
        self.assertEqual(pairs, 55)
        self.assertEqual((counted_high.calls, counted_low.calls), (55, 55))
        old_h, old_l, old_shell = M.V1.matrices(high, low, labels)
        self.assertEqual(ah, old_h)
        self.assertEqual(al, old_l)
        self.assertEqual(shell, old_shell)

    def test_low_k_literal_and_difference(self):
        k = 3
        delta, eta = Q(1, 10), Q(3, 10)
        schedule = (Q(1, 4), Q(3, 10), Q(7, 20))
        high = M.V1.A25.shell.ScheduledStratumSupport.make(
            k, Q(2, 5), eta, delta, schedule)
        low = M.V1.A25.shell.ScheduledStratumSupport.make(
            k, Q(7, 20), eta, delta, schedule)
        labels = tuple(M.V1.EI.even_basis(2))
        ah, al, shell, pairs = M.upper_triangle_matrices(high, low, labels)
        self.assertEqual(pairs, 10)
        for vector in ((1, -2, 3, -4), (2, 1, -1, 3)):
            gh = M.V1.grouped_quadratic(high, labels, vector)
            gl = M.V1.grouped_quadratic(low, labels, vector)
            self.assertEqual(M.V1.exact_quadratic(ah, vector), gh)
            self.assertEqual(M.V1.exact_quadratic(al, vector), gl)
            self.assertEqual(M.V1.exact_quadratic(shell, vector), gh - gl)

    def test_v1_frozen_and_exact_ldl(self):
        for path, expected in M.PINNED_V1.items():
            self.assertEqual(M._sha(path), expected)
        old = json_load(M.V1_ARTIFACT)
        shell = [[Q(x) for x in row] for row in old["shell_matrix"]]
        _, pivots = M.V1.ldl_pivots(shell)
        self.assertEqual(M.V1.exact_rank(shell), 10)
        self.assertTrue(all(x > 0 for x in pivots))


def json_load(path):
    import json
    return json.loads(Path(path).read_bytes())


if __name__ == "__main__":
    unittest.main()
