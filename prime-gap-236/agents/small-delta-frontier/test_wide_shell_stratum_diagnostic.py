#!/usr/bin/env python3
"""Exact low-k and fail-closed tests for the wide-shell R diagnostic."""

from __future__ import annotations

import importlib.util
import sys
import unittest
from fractions import Fraction as Q
from pathlib import Path


HERE = Path(__file__).resolve().parent
PATH = HERE / "wide_shell_stratum_diagnostic.py"
SPEC = importlib.util.spec_from_file_location("wide_shell_tested", PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot import diagnostic")
M = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = M
SPEC.loader.exec_module(M)


def literal_stratum_marginal_k2(support, u, total_r):
    """Length of the distinguished fiber in exact total stratum R."""
    if u < 0 or u >= support.alpha:
        return Q(0)
    d = support.delta
    remaining = support.alpha - u
    if u <= d:
        if total_r == 0:
            return max(Q(0), min(d, remaining))
        if total_r == 1:
            return max(Q(0), min(remaining, support.beta(1)) - d)
        return Q(0)
    if total_r == 1:
        if u >= support.beta(1):
            return Q(0)
        return max(Q(0), min(d, remaining))
    if total_r == 2:
        return max(Q(0), min(remaining, support.beta(2) - u) - d)
    return Q(0)


def literal_cross_table_k2(left, right, eta):
    points = {Q(0), eta, left.delta}
    for support in (left, right):
        points.update((
            support.alpha, support.alpha - support.delta,
            support.alpha - support.beta(1), support.beta(1),
            min(support.alpha, support.beta(2)) - support.delta,
        ))
    points = sorted(x for x in points if 0 <= x <= eta)
    answer = [[Q(0) for _ in range(3)] for _ in range(3)]
    for lo, hi in zip(points, points[1:]):
        if hi <= lo:
            continue
        x1, x2 = (2 * lo + hi) / 3, (lo + 2 * hi) / 3
        for r in range(3):
            for s in range(3):
                y1 = (literal_stratum_marginal_k2(left, x1, r) *
                      literal_stratum_marginal_k2(right, x1, s))
                y2 = (literal_stratum_marginal_k2(left, x2, r) *
                      literal_stratum_marginal_k2(right, x2, s))
                slope = (y2 - y1) / (x2 - x1)
                # A product of two affine marginals is quadratic, not affine.
                # Recover it from three interior values instead.
                x3 = (lo + hi) / 2
                y3 = (literal_stratum_marginal_k2(left, x3, r) *
                      literal_stratum_marginal_k2(right, x3, s))
                # Newton interpolation at x1,x2,x3, integrated exactly.
                d12 = (y2 - y1) / (x2 - x1)
                d23 = (y3 - y2) / (x3 - x2)
                d123 = (d23 - d12) / (x3 - x1)
                c2 = d123
                c1 = d12 - c2 * (x1 + x2)
                c0 = y1 - c1 * x1 - c2 * x1 * x1
                for check in ((3 * lo + hi) / 4,
                              (lo + 3 * hi) / 4):
                    expected = (literal_stratum_marginal_k2(left, check, r) *
                                literal_stratum_marginal_k2(right, check, s))
                    if expected != c0 + c1 * check + c2 * check * check:
                        raise AssertionError("missing literal k=2 breakpoint")
                answer[r][s] += (
                    c0 * (hi - lo) + c1 * (hi ** 2 - lo ** 2) / 2 +
                    c2 * (hi ** 3 - lo ** 3) / 3)
    return answer


class WideShellStratumTests(unittest.TestCase):
    def support(self, k, alpha, schedule):
        return M.ScheduledStratumSupport.make(
            k, alpha, Q(3, 10), Q(1, 10), schedule[:k])

    def test_k2_cross_table_against_literal_fibers(self):
        schedule = (Q(9, 50), Q(13, 50), Q(7, 20))
        left = self.support(2, Q(2, 5), schedule)
        right = self.support(2, Q(9, 20), schedule)
        got, _ = M.cross_constant_stratum_table(
            left, right, Q(3, 10))
        expected = literal_cross_table_k2(left, right, Q(3, 10))
        self.assertEqual([row[:3] for row in got[:3]], expected)
        self.assertTrue(all(got[i][j] == 0
                            for i in range(3) for j in range(3, len(got))))

    def test_same_support_matches_independent_tagged_recurrence(self):
        schedule = (Q(9, 50), Q(13, 50), Q(7, 20))
        for k in (2, 3):
            support = self.support(k, Q(2, 5), schedule)
            got, _ = M.cross_constant_stratum_table(
                support, support, Q(3, 10))
            for r in range(k + 1):
                for s in range(k + 1):
                    expected = support.basis_j_in_strata(
                        r, (0, ()), s, (0, ()))
                    self.assertEqual(got[r][s], expected)
            self.assertEqual(sum(map(sum, got)),
                             support.basis_j((0, ()), (0, ())))

    def test_cross_transpose_and_shell_degeneration(self):
        schedule = (Q(9, 50), Q(13, 50), Q(7, 20))
        left = self.support(3, Q(2, 5), schedule)
        right = self.support(3, Q(9, 20), schedule)
        lr, _ = M.cross_constant_stratum_table(left, right, Q(3, 10))
        rl, _ = M.cross_constant_stratum_table(right, left, Q(3, 10))
        self.assertEqual(lr, [list(row) for row in zip(*rl)])
        same, _ = M.cross_constant_stratum_table(left, left, Q(3, 10))
        zero = M.matrix_add((Q(1), same), (Q(-1), lr),
                            (Q(-1), [list(row) for row in zip(*lr)]),
                            (Q(1), rl))
        # This expression is not a support square unless right=left; check the
        # actual degeneration separately to guard every inclusion-exclusion sign.
        degenerate = M.matrix_add((Q(1), same), (Q(-1), same),
                                  (Q(-1), same), (Q(1), same))
        self.assertTrue(all(x == 0 for row in degenerate for x in row))
        self.assertEqual(len(zero), 4)

    def test_i_strata_reconstruct_and_factor_k_once(self):
        support = self.support(
            3, Q(2, 5), (Q(9, 50), Q(13, 50), Q(7, 20)))
        masses = [support.basis_m1_in_strata(
            r, (0, ()), r, (0, ())) for r in range(4)]
        self.assertEqual(sum(masses), support.basis_m1((0, ()), (0, ())))
        table, _ = M.cross_constant_stratum_table(
            support, support, Q(3, 10))
        self.assertEqual(Q(3) * sum(map(sum, table)),
                         Q(3) * support.basis_j((0, ()), (0, ())))

    def test_decimal_jacobi_known_pencil(self):
        answer = M.decimal_jacobi_diagonal_gram(
            [Q(1), Q(1)], [[Q(2), Q(1)], [Q(1), Q(2)]], 100)
        self.assertEqual(Q(answer["rayleigh_quotient"]), Q(3))
        self.assertEqual([Q(x) for x in answer["vector"]], [Q(1), Q(1)])
        self.assertEqual(Q(answer["relative_residual_bound"]), Q(0))
        pivots = M.tridiagonal_upper_bound_ldl(
            [Q(1), Q(1)], [Q(2), Q(2)], [Q(1)], Q(4))
        self.assertEqual(pivots, [Q(2), Q(3, 2)])
        self.assertTrue(all(x > 0 for x in pivots))
        boundary = M.tridiagonal_upper_bound_ldl(
            [Q(1), Q(1)], [Q(2), Q(2)], [Q(1)], Q(3))
        self.assertEqual(boundary[-1], 0)

    def test_target_inventory_and_invalid_subset(self):
        inventory = M.domain_inventory()
        self.assertEqual(inventory["domain_counts"],
                         {"hh": 8832, "hl": 8832, "ll": 8832})
        self.assertEqual(inventory["total_domain_count"], 26496)
        hi, _ = M.make_supports(3)
        with self.assertRaisesRegex(ValueError, "common stratum"):
            M.cross_constant_stratum_table(
                hi, hi, M.ETA2, integrate=False, common_strata=[4])


if __name__ == "__main__":
    unittest.main()
