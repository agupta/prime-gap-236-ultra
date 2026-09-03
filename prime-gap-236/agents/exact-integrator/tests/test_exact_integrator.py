#!/usr/bin/env python3
"""Independent low-dimensional regressions for the exact integrator."""

from __future__ import annotations

import os
import sys
import unittest
from fractions import Fraction as Q
from itertools import permutations
from math import factorial

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from exact_integrator import (  # noqa: E402
    OneStratumSupport,
    multiply_monomial_orbits,
    orbit_size,
    polygon,
    polygon_monomial,
)
from stratum_integrator import StratumSupport  # noqa: E402


def brute_orbit_polynomial(k, lam):
    padded = tuple(lam) + (0,) * (k - len(lam))
    return {p: 1 for p in set(permutations(padded))}


def brute_product(k, lam, mu):
    ans = {}
    for x in brute_orbit_polynomial(k, lam):
        for y in brute_orbit_polynomial(k, mu):
            z = tuple(a + b for a, b in zip(x, y))
            ans[z] = ans.get(z, 0) + 1
    return ans


class StructureConstants(unittest.TestCase):
    def test_against_labeled_three_variable_expansion(self):
        cases = [((2,), (2,)), ((4, 2), (2,)), ((2, 2), (4, 2)),
                 ((6, 2), (4,)), ((), (4, 2)),
                 # Odd signatures are essential in the unrestricted
                 # Polymath basis, so test them independently of the old
                 # even-signature speed restriction.
                 ((3,), (2,)), ((3, 2), (5,)), ((3, 3), (3, 2))]
        for lam, mu in cases:
            k = len(lam) + len(mu) + 1
            got = {}
            for nu, coeff in multiply_monomial_orbits(lam, mu):
                for mon in brute_orbit_polynomial(k, nu):
                    got[mon] = got.get(mon, 0) + coeff
            self.assertEqual(got, brute_product(k, lam, mu), (lam, mu))

    def test_all_no_one_partitions_through_degree_six(self):
        parts = [(), (2,), (3,), (4,), (2, 2), (5,), (3, 2),
                 (6,), (4, 2), (3, 3), (2, 2, 2)]
        # k=4 is sufficient for every product here and keeps literal orbit
        # enumeration small enough to serve as an independent oracle.
        for lam in parts:
            for mu in parts:
                if len(lam) + len(mu) > 4:
                    continue
                got = {}
                for nu, coeff in multiply_monomial_orbits(lam, mu):
                    for mon in brute_orbit_polynomial(4, nu):
                        got[mon] = got.get(mon, 0) + coeff
                self.assertEqual(got, brute_product(4, lam, mu), (lam, mu))


class PolygonMoments(unittest.TestCase):
    def test_standard_triangle_beta_identity(self):
        tri = polygon(Q(1))
        for a in range(5):
            for b in range(5):
                expected = Q(factorial(a) * factorial(b), factorial(a + b + 2))
                self.assertEqual(polygon_monomial(tri, a, b), expected)

    def test_clipped_rectangle(self):
        # [0,2/3] x [0,1/4] lies inside z+w<=1.
        rect = polygon(Q(1), ((Q(1), Q(0), Q(2, 3)),
                              (Q(0), Q(1), Q(1, 4))))
        self.assertEqual(polygon_monomial(rect, 2, 3),
                         Q(2, 3) ** 3 / 3 * Q(1, 4) ** 4 / 4)


class SupportMoments(unittest.TestCase):
    def test_max_large_allows_later_beta_jump(self):
        s = OneStratumSupport(6, Q(1, 2), Q(1, 10), Q(2, 5),
                              Q(1, 20), Q(3, 20), Q(9, 20))
        # r=1 is impossible, but r=3 and r=4 are possible after beta jumps.
        self.assertEqual(s.max_large(), 4)

    def test_full_simplex_dirichlet(self):
        # delta > alpha means only the r=0 piece exists and the coordinate box
        # never truncates the simplex.
        k = 3
        alpha = Q(2, 5)
        s = OneStratumSupport(k, alpha, Q(1), Q(1, 3), Q(3, 2), Q(3, 2), Q(3, 2))
        lam = (3, 1)
        c = 2
        padded = lam + (0,)
        expected = (Q(factorial(3) * factorial(1) * factorial(0) * factorial(c),
                      factorial(sum(lam) + k + c)) *
                    alpha ** (sum(lam) + k + c))
        self.assertEqual(s.canonical_support_residual(lam, c), expected)

    def test_published_k1_collapses_to_interval(self):
        s = OneStratumSupport.published(1)
        B = Q(3, 20)
        for a in range(5):
            for b in range(4):
                expected = sum(Q(((-1) ** j) * factorial(b),
                                 factorial(j) * factorial(b - j)) *
                               B ** (a + j + 1) / (a + j + 1)
                               for j in range(b + 1))
                self.assertEqual(s.canonical_support_moment((a,) if a else (), b),
                                 expected)

    def test_published_k2_area_by_elementary_decomposition(self):
        s = OneStratumSupport.published(2)
        d, b1, b2 = s.delta, s.beta1, s.beta2
        expected = d * d + 2 * d * (b1 - d) + (b2 - 2 * d) ** 2 / 2
        self.assertEqual(s.canonical_support_moment((), 0), expected)


class JMoments(unittest.TestCase):
    @staticmethod
    def _umul(p, q):
        out = {}
        for i, a in p.items():
            for j, b in q.items():
                out[i + j] = out.get(i + j, Q(0)) + a * b
        return {i: a for i, a in out.items() if a}

    @classmethod
    def _upow_linear(cls, c0, c1, n):
        ans = {0: Q(1)}
        for _ in range(n):
            ans = cls._umul(ans, {0: c0, 1: c1})
        return ans

    @classmethod
    def _independent_marginal(cls, upper, e, a):
        # upper is (constant, coefficient of u).  This expands the elementary
        # antiderivative directly and shares no polygon/branch code with the
        # implementation under test.
        ans = {}
        for j in range(a + 1):
            left = cls._upow_linear(Q(1), Q(-1), a - j)
            right = cls._upow_linear(upper[0], upper[1], e + j + 1)
            term = cls._umul(left, right)
            coeff = Q(((-1) ** j) * factorial(a),
                      factorial(j) * factorial(a - j) * (e + j + 1))
            for n, x in term.items():
                ans[n] = ans.get(n, Q(0)) + coeff * x
        return {n: x for n, x in ans.items() if x}

    @classmethod
    def _independent_k2_j(cls, nu, e, a, f, b):
        s = OneStratumSupport.published(2)
        d, B = s.delta, s.beta1
        intervals = ((Q(0), d, (B, Q(0))),
                     (d, B - d, (B, Q(-1))),
                     (B - d, B, (d, Q(0))))
        ans = Q(0)
        shared_power = nu[0] if nu else 0
        for lo, hi, upper in intervals:
            p = cls._umul(cls._independent_marginal(upper, e, a),
                          cls._independent_marginal(upper, f, b))
            for n, coeff in p.items():
                m = n + shared_power + 1
                ans += coeff * (hi ** m - lo ** m) / m
        return ans

    def test_published_k1_product_of_one_dimensional_marginals(self):
        s = OneStratumSupport.published(1)
        B = s.beta1

        def one(a, c):
            return sum(Q(((-1) ** j) * factorial(c),
                         factorial(j) * factorial(c - j)) *
                       B ** (a + j + 1) / (a + j + 1)
                       for j in range(c + 1))

        for e, a, f, b in ((0, 0, 0, 0), (2, 1, 4, 2), (1, 3, 0, 2)):
            self.assertEqual(s.canonical_j_moment((), e, a, f, b),
                             one(e, a) * one(f, b))

    def test_published_k2_constant_marginal_piecewise(self):
        s = OneStratumSupport.published(2)
        d, B = s.delta, s.beta1
        cut = B - d
        expected = (d * B ** 2 +
                    ((B - d) ** 3 - (B - cut) ** 3) / 3 +
                    (B - cut) * d ** 2)
        # More transparently: integral_d^cut (B-u)^2 du and then to B.
        expected = d * B ** 2 + ((B - d) ** 3 - (B - cut) ** 3) / 3 + (B - cut) * d ** 2
        self.assertEqual(s.canonical_j_moment((), 0, 0, 0, 0), expected)

    def test_published_k2_nonconstant_against_direct_antiderivatives(self):
        s = OneStratumSupport.published(2)
        cases = [((2,), 3, 2, 1, 4), ((5,), 0, 3, 4, 1),
                 ((), 2, 5, 2, 2), ((1,), 1, 0, 0, 3)]
        for nu, e, a, f, b in cases:
            self.assertEqual(s.canonical_j_moment(nu, e, a, f, b),
                             self._independent_k2_j(nu, e, a, f, b),
                             (nu, e, a, f, b))

    def test_symmetry_orbit_factor(self):
        s = OneStratumSupport.published(4)
        base = s.canonical_j_moment((2,), 0, 0, 0, 0)
        self.assertEqual(s.orbit_j_moment((2,), 0, 0, 0, 0),
                         orbit_size(3, (2,)) * base)

    def test_full_simplex_shortcut_matches_generic_branch_decomposition(self):
        class ForcedGeneric(OneStratumSupport):
            def is_full_simplex(self):
                return False

        args = (3, Q(2, 5), Q(1, 10), Q(7, 20), Q(2, 5), Q(2, 5), Q(2, 5))
        fast = OneStratumSupport(*args)
        slow = ForcedGeneric(*args)
        self.assertTrue(fast.is_full_simplex())
        for lam, c in [((2,), 3), ((3, 1), 0), ((), 4)]:
            self.assertEqual(fast.canonical_support_residual(lam, c),
                             slow.canonical_support_residual(lam, c))
        for case in [((2,), 1, 2, 3, 1), ((), 0, 3, 2, 2),
                     ((1, 1), 2, 0, 0, 4)]:
            self.assertEqual(fast.canonical_j_moment(*case),
                             slow.canonical_j_moment(*case), case)


class StratumMoments(unittest.TestCase):
    def test_stratum_partition_reconstructs_global_bilinear_forms(self):
        base = OneStratumSupport.published(3)
        tagged = StratumSupport(**base.__dict__)
        cases = [((1, (2,)), (0, (3,))),
                 ((0, ()), (2, (2,)))]
        strata = range(base.k + 1)
        for x, y in cases:
            got_i = sum(tagged.basis_m1_in_strata(r, x, r, y)
                        for r in strata)
            self.assertEqual(got_i, base.basis_m1(x, y), (x, y, "I"))
            got_j = sum(tagged.basis_j_in_strata(r, x, s, y)
                        for r in strata for s in strata)
            self.assertEqual(got_j, base.basis_j(x, y), (x, y, "J"))

    def test_exact_block_sparsity(self):
        tagged = StratumSupport.published(4)
        x, y = (1, (2,)), (0, (3,))
        self.assertEqual(tagged.basis_m1_in_strata(1, x, 2, y), 0)
        self.assertEqual(tagged.basis_j_in_strata(0, x, 2, y), 0)
        self.assertEqual(tagged.basis_j_in_strata(1, x, 2, y),
                         tagged.basis_j_in_strata(2, y, 1, x))


if __name__ == "__main__":
    unittest.main(verbosity=2)
