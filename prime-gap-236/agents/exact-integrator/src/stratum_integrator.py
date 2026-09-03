#!/usr/bin/env python3
"""Exact support-stratum basis extension.

A tag ``R`` means multiplication by the symmetric indicator that exactly R
coordinates exceed delta.  These discontinuous, square-integrable functions are
aligned with Stadlmann's support pieces.  The I matrix is block diagonal in R.
For J, deleting the distinguished coordinate changes the large-coordinate count
by at most one, so blocks with |R-S|>1 vanish exactly.
"""

from __future__ import annotations

from fractions import Fraction as Q
from functools import lru_cache
from math import comb, factorial
from typing import Sequence, Tuple

from exact_integrator import (
    OneStratumSupport,
    Partition,
    _integrate_poly_interval,
    _integrate_poly_z_interval,
    _large_shift_dp,
    _poly_mul,
    _selected_exponent_splits,
    _small_box_dp,
    integrate_poly_polygon,
    multiply_monomial_orbits,
    orbit_size,
    polygon,
)

PolynomialLabel = Tuple[int, Partition]
StratumLabel = Tuple[int, PolynomialLabel]


class StratumSupport(OneStratumSupport):
    """One-stratum support with exact large-coordinate-count indicators."""

    @lru_cache(maxsize=None)
    def canonical_support_residual_in_stratum(
            self, lam: Partition, c: int, stratum: int) -> Q:
        lam = tuple(sorted(lam, reverse=True))
        if len(lam) > self.k or not 0 <= stratum <= self.k:
            return Q(0)
        ans = Q(0)
        for mult, large, small in _selected_exponent_splits(
                self.k, lam, stratum):
            ans += mult * self._piece_residual(large, small, c)
        return ans

    @lru_cache(maxsize=None)
    def canonical_support_moment_in_stratum(
            self, lam: Partition, b: int, stratum: int) -> Q:
        return sum(Q(comb(b, c)) * ((1 - self.alpha) ** (b - c)) *
                   self.canonical_support_residual_in_stratum(lam, c, stratum)
                   for c in range(b + 1))

    def orbit_support_moment_in_stratum(
            self, lam: Partition, b: int, stratum: int) -> Q:
        return (orbit_size(self.k, lam) *
                self.canonical_support_moment_in_stratum(lam, b, stratum))

    @staticmethod
    def _branches_for_total_stratum(common_r: int, total_r: int):
        if total_r == common_r:
            return ("Sdelta", "Stotal")
        if total_r == common_r + 1:
            return ("Ltotal", "Lbig")
        return ()

    @lru_cache(maxsize=None)
    def _j_piece_strata(self, large: Tuple[int, ...], small: Tuple[int, ...],
                        e: int, a: int, f: int, b: int,
                        left_stratum: int, right_stratum: int) -> Q:
        r, s = len(large), len(small)
        left_branches = self._branches_for_total_stratum(r, left_stratum)
        right_branches = self._branches_for_total_stratum(r, right_stratum)
        if not left_branches or not right_branches:
            return Q(0)
        max_h = int(self.eta // self.delta) - r
        if max_h < 0:
            return Q(0)
        sd = _small_box_dp(small, self.delta, max_h)
        ld = _large_shift_dp(large, self.delta)
        ans = Q(0)
        for qdeg, lc0 in ld.items():
            lc = lc0 / factorial(qdeg + r - 1) if r else lc0
            zpow = qdeg + r - 1 if r else 0
            for (h, pdeg), sc0 in sd.items():
                outer = self.eta - (r + h) * self.delta
                if outer <= 0:
                    continue
                sc = sc0 / factorial(pdeg + s - 1) if s else sc0
                wpow = pdeg + s - 1 if s else 0
                for br1 in left_branches:
                    p1 = dict(self._marginal_poly(r, h, br1, e, a))
                    c1 = self._branch_constraints(r, h, br1)
                    if not p1 or c1 is None:
                        continue
                    for br2 in right_branches:
                        p2 = dict(self._marginal_poly(r, h, br2, f, b))
                        c2 = self._branch_constraints(r, h, br2)
                        if not p2 or c2 is None:
                            continue
                        integrand = _poly_mul(p1, p2)
                        if r and s:
                            value = integrate_poly_polygon(
                                integrand, polygon(outer, c1 + c2), zpow, wpow)
                        elif r:
                            i1 = self._branch_z_interval(r, h, br1)
                            i2 = self._branch_z_interval(r, h, br2)
                            if i1 is None or i2 is None:
                                continue
                            lo, hi = max(i1[0], i2[0]), min(i1[1], i2[1])
                            value = _integrate_poly_z_interval(
                                integrand, lo, hi, zpow)
                        else:
                            i1 = self._branch_interval(r, h, br1)
                            i2 = self._branch_interval(r, h, br2)
                            if i1 is None or i2 is None:
                                continue
                            lo, hi = max(i1[0], i2[0]), min(i1[1], i2[1])
                            value = _integrate_poly_interval(
                                integrand, lo, hi, wpow)
                        ans += lc * sc * value
        return ans

    @lru_cache(maxsize=None)
    def canonical_j_moment_in_strata(
            self, nu: Partition, e: int, a: int, f: int, b: int,
            left_stratum: int, right_stratum: int) -> Q:
        ku = self.k - 1
        if abs(left_stratum - right_stratum) > 1:
            return Q(0)
        if ku == 0:
            values = []
            for te, residual, total_r in (
                    (e, a, left_stratum), (f, b, right_stratum)):
                value = Q(0)
                for branch in self._branches_for_total_stratum(0, total_r):
                    interval = self._branch_interval(0, 0, branch)
                    if interval is not None and interval[0] <= 0 <= interval[1]:
                        value += dict(self._marginal_poly(
                            0, 0, branch, te, residual)).get((0, 0), Q(0))
                values.append(value)
            return values[0] * values[1]
        if len(nu) > ku:
            return Q(0)
        ans = Q(0)
        # A common stratum r can contribute only when each total stratum is r
        # (small distinguished coordinate) or r+1 (large distinguished one).
        possible_r = set((left_stratum, left_stratum - 1)).intersection(
            (right_stratum, right_stratum - 1))
        for r in sorted(x for x in possible_r if 0 <= x <= ku):
            for mult, large, small in _selected_exponent_splits(ku, nu, r):
                ans += mult * self._j_piece_strata(
                    large, small, e, a, f, b, left_stratum, right_stratum)
        return ans

    def orbit_j_moment_in_strata(
            self, nu: Partition, e: int, a: int, f: int, b: int,
            left_stratum: int, right_stratum: int) -> Q:
        return (orbit_size(self.k - 1, nu) *
                self.canonical_j_moment_in_strata(
                    nu, e, a, f, b, left_stratum, right_stratum))

    @lru_cache(maxsize=None)
    def basis_m1_in_strata(self, left_stratum: int, x: PolynomialLabel,
                           right_stratum: int, y: PolynomialLabel) -> Q:
        if left_stratum != right_stratum:
            return Q(0)
        a, lam = x
        b, mu = y
        return sum(coeff * self.orbit_support_moment_in_stratum(
                       nu, a + b, left_stratum)
                   for nu, coeff in multiply_monomial_orbits(lam, mu))

    @lru_cache(maxsize=None)
    def basis_j_in_strata(self, left_stratum: int, x: PolynomialLabel,
                          right_stratum: int, y: PolynomialLabel) -> Q:
        if abs(left_stratum - right_stratum) > 1:
            return Q(0)
        a, lam = x
        b, mu = y
        ans = Q(0)
        for e, lr in self.split_at_distinguished(lam, self.k):
            for f, mr in self.split_at_distinguished(mu, self.k):
                for nu, coeff in multiply_monomial_orbits(lr, mr):
                    ans += coeff * self.orbit_j_moment_in_strata(
                        nu, e, a, f, b, left_stratum, right_stratum)
        return ans

    def stratum_matrices(self, basis: Sequence[StratumLabel]):
        n = len(basis)
        m1 = [[Q(0) for _ in range(n)] for _ in range(n)]
        m2 = [[Q(0) for _ in range(n)] for _ in range(n)]
        for i, (ri, xi) in enumerate(basis):
            for j in range(i + 1):
                rj, xj = basis[j]
                if ri == rj:
                    m1[i][j] = m1[j][i] = self.basis_m1_in_strata(
                        ri, xi, rj, xj)
                if abs(ri - rj) <= 1:
                    m2[i][j] = m2[j][i] = self.k * self.basis_j_in_strata(
                        ri, xi, rj, xj)
        return m1, m2
