#!/usr/bin/env python3
"""Reusable fixed-base moment tables for per-stratum L/Z multipliers.

For P_d={(a,b):a,b>=0,a+b<=d}, the basis is
    1_{R=r} F0 L^a Z^b.
The expensive fixed-polynomial orbit products are accumulated independently
of a multiplier vector.  I needs moments through degree 2d.  J uses the
distinguished-fiber moments t^j, 0<=j<=d, and aggregate moments through the
remaining degree 2d-j-k.  The resulting I matrix is block diagonal in r and
the J matrix is block tridiagonal.

This is a research prototype, not a target D12 result driver.  It imports the
audited exact geometry primitives but has a separate source identity.
"""

from __future__ import annotations

import math
import os
import sys
from collections import defaultdict
from fractions import Fraction
from pathlib import Path


HERE = Path(__file__).resolve().parent
EI = HERE.parent / "exact-integrator"
sys.path[:0] = [str(EI), str(EI / "src")]

import exact_integrator as ei  # noqa: E402
from grouped_fixed_vector import add_poly  # noqa: E402
from stratum_quadratic import StratumQuadraticEvaluator  # noqa: E402


BRANCHES = ("Sdelta", "Stotal", "Ltotal", "Lbig")


def channel_powers(degree: int):
    if type(degree) is not int or not 0 <= degree <= 8:
        raise ValueError("moment-table degree must be an integer in [0,8]")
    return tuple((a, total - a) for total in range(degree + 1)
                 for a in range(total, -1, -1))


def aggregate_powers(maximum_degree: int):
    return tuple((a, total - a) for total in range(maximum_degree + 1)
                 for a in range(total, -1, -1))


def distinguished_limit(power, large_branch):
    a, b = power
    return a if large_branch else b


def remaining_power(power, moment, large_branch):
    a, b = power
    return (a - moment, b) if large_branch else (a, b - moment)


class StratumMomentTableEvaluator(StratumQuadraticEvaluator):
    """Exact multiplier-independent moments for one fixed polynomial F0."""

    def __init__(self, support, labels, coefficients, scalar=Fraction,
                 degree=3):
        super().__init__(support, labels, coefficients, scalar)
        self.degree = degree
        self.moment_channels = channel_powers(degree)
        self.aggregate_moments = aggregate_powers(2 * degree)

    def _aggregate_polynomial(self, r, h, u, v):
        left = dict(ei._linear_power(
            self.scalar(r) * self.support.delta,
            self.one, self.zero, u))
        right = dict(ei._linear_power(
            self.scalar(h) * self.support.delta,
            self.zero, self.one, v))
        return ei._poly_mul(left, right)

    def evaluate_i_r_moments(self, grouped, r, progress=False):
        """Return U_r[u,v]=integral F0^2 L^u Z^v on R=r."""
        answer = defaultdict(self.scalar)
        dimension = self.support.k
        faces = scalar_integrals = 0
        max_h = int(self.support.alpha // self.support.delta) - r
        if max_h < 0:
            return {}, faces, scalar_integrals
        constraints = ()
        if r:
            cap = self.support.beta(r) - r * self.support.delta
            if cap <= 0:
                return {}, faces, scalar_integrals
            constraints = ((self.one, self.zero, cap),)
        for h in range(max_h + 1):
            outer = self.support.alpha - (r + h) * self.support.delta
            if outer <= 0:
                continue
            base = self._i_face_polynomial(
                grouped, dimension, r, h, max_h, outer)
            for u, v in self.aggregate_moments:
                weighted = ei._poly_mul(
                    base, self._aggregate_polynomial(r, h, u, v))
                answer[(u, v)] += self.integrate_domain(
                    weighted, dimension, r, outer, constraints)
                scalar_integrals += 1
            faces += 1
            if progress:
                print(f"moment I r={r} h={h} faces={faces} "
                      f"moments={scalar_integrals}", flush=True)
            self.clear_face_caches()
        self.clear_radial_caches()
        return dict(answer), faces, scalar_integrals

    def evaluate_i_moments(self, progress=False):
        grouped = self.square_residual_terms()
        values = {}
        faces = scalar_integrals = 0
        for r in self._r_values_i():
            block, count, moments = self.evaluate_i_r_moments(
                grouped, r, progress)
            values[r] = block
            faces += count
            scalar_integrals += moments
        return values, len(grouped), faces, scalar_integrals

    def _moment_branch_blocks(self, lrs, by_lr, r, h, dimension, outer):
        """Return the marginal blocks M_{B,j}, 0<=j<=degree."""
        answer = {}
        for branch in BRANCHES:
            constraints = self.support._branch_constraints(r, h, branch)
            if dimension == 0:
                interval = self.support._branch_interval(0, 0, branch)
                active = (interval is not None and
                          interval[0] <= self.zero <= interval[1])
            else:
                active = (constraints is not None and self.integrate_domain(
                    {(0, 0): self.one}, dimension, r, outer, constraints) > 0)
            if not active:
                answer[branch] = tuple({} for _ in range(self.degree + 1))
                continue
            answer[branch] = tuple(self._shifted_marginal_block_by(
                lrs, by_lr, r, h, branch, j)
                for j in range(self.degree + 1))
        return answer

    def _density_product_polynomial(self, left, right, dimension,
                                    r, h, max_h):
        combined = self._ordinary_orbit_product(left, right)
        total = defaultdict(self.scalar)
        for nu, marginal in combined.items():
            density = self.orbit_density(dimension, nu, r, h, max_h)
            if density:
                add_poly(total, ei._poly_mul(density, marginal), self.one)
        return dict(total)

    @staticmethod
    def _class(branch):
        return 0 if branch in ("Sdelta", "Stotal") else 1

    @staticmethod
    def _add_j_value(answer, key, value):
        if value:
            answer[key] += value

    def evaluate_j_r_moments(self, lrs, by_lr, r, progress=False):
        """Return multiplier-independent W_r^(sigma,tau)[j,k,u,v].

        sigma/tau are 0 for a small distinguished branch and 1 for a large
        branch.  Branch pieces are summed as *ordered* branch pairs.  Hence
        W(1,0,k,j,u,v)=W(0,1,j,k,u,v) follows exactly, and matrix assembly
        needs no extra factor two.
        """
        answer = defaultdict(self.scalar)
        dimension = self.support.k - 1
        branch_domains = product_radializations = scalar_integrals = 0
        max_h = int(self.support.eta // self.support.delta) - r
        if max_h < 0:
            return {}, branch_domains, product_radializations, scalar_integrals
        for h in range(max_h + 1):
            if dimension == 0 and (r != 0 or h != 0):
                continue
            outer = self.support.eta - (r + h) * self.support.delta
            if outer <= 0:
                continue
            blocks = self._moment_branch_blocks(
                lrs, by_lr, r, h, dimension, outer)
            aggregate = {power: self._aggregate_polynomial(r, h, *power)
                         for power in self.aggregate_moments}
            for left_index, left_branch in enumerate(BRANCHES):
                for right_branch in BRANCHES[:left_index + 1]:
                    constraints = self._active_branch_pair(
                        blocks, left_branch, right_branch,
                        dimension, r, h, outer)
                    if constraints is None:
                        continue
                    branch_domains += 1
                    left_class = self._class(left_branch)
                    right_class = self._class(right_branch)
                    same_branch = left_branch == right_branch
                    moment_pairs = (
                        ((j, k) for j in range(self.degree + 1)
                         for k in range(j + 1)) if same_branch else
                        ((j, k) for j in range(self.degree + 1)
                         for k in range(self.degree + 1)))
                    for j, k in moment_pairs:
                        if not blocks[left_branch][j] or \
                                not blocks[right_branch][k]:
                            continue
                        base = self._density_product_polynomial(
                            blocks[left_branch][j], blocks[right_branch][k],
                            dimension, r, h, max_h)
                        if not base:
                            continue
                        product_radializations += 1
                        maximum = 2 * self.degree - j - k
                        for u, v in aggregate_powers(maximum):
                            value = self.integrate_domain(
                                ei._poly_mul(base, aggregate[(u, v)]),
                                dimension, r, outer, constraints)
                            key = (left_class, right_class, j, k, u, v)
                            self._add_j_value(answer, key, value)
                            if not same_branch:
                                mirror = (right_class, left_class,
                                          k, j, u, v)
                                self._add_j_value(answer, mirror, value)
                            elif j != k:
                                mirror = (left_class, right_class,
                                          k, j, u, v)
                                self._add_j_value(answer, mirror, value)
                            scalar_integrals += 1
            if progress:
                print(f"moment J r={r} h={h} domains={branch_domains} "
                      f"products={product_radializations} "
                      f"moments={scalar_integrals}", flush=True)
            self.clear_face_caches(clear_marginals=True)
        self.clear_radial_caches()
        return dict(answer), branch_domains, product_radializations, \
            scalar_integrals

    def evaluate_j_moments(self, progress=False):
        _, lrs, by_lr = self._j_component_data()
        values = {}
        domains = products = scalar_integrals = 0
        for r in self._r_values_j():
            block, dcount, pcount, mcount = self.evaluate_j_r_moments(
                lrs, by_lr, r, progress)
            values[r] = block
            domains += dcount
            products += pcount
            scalar_integrals += mcount
        return values, len(self.marginal_components()), domains, products, \
            scalar_integrals

    def _j_channel_entry(self, table, left_power, right_power,
                         left_class, right_class):
        answer = self.zero
        left_max = distinguished_limit(left_power, bool(left_class))
        right_max = distinguished_limit(right_power, bool(right_class))
        for j in range(left_max + 1):
            left_remaining = remaining_power(
                left_power, j, bool(left_class))
            left_scale = self.scalar(math.comb(left_max, j))
            for k in range(right_max + 1):
                right_remaining = remaining_power(
                    right_power, k, bool(right_class))
                right_scale = self.scalar(math.comb(right_max, k))
                u = left_remaining[0] + right_remaining[0]
                v = left_remaining[1] + right_remaining[1]
                answer += left_scale * right_scale * table.get(
                    (left_class, right_class, j, k, u, v), self.zero)
        return answer

    def assemble_dense_from_moments(self, i_moments, j_moments):
        max_r = max(i_moments, default=-1)
        powers = self.moment_channels
        labels = [(r, p) for r in range(max_r + 1)
                  for p in range(len(powers))]
        positions = {label: i for i, label in enumerate(labels)}
        n = len(labels)
        a = [[self.zero for _ in range(n)] for _ in range(n)]
        b = [[self.zero for _ in range(n)] for _ in range(n)]
        for r, table in i_moments.items():
            for p, left in enumerate(powers):
                for q, right in enumerate(powers):
                    a[positions[(r, p)]][positions[(r, q)]] = table.get(
                        (left[0] + right[0], left[1] + right[1]), self.zero)
        kfactor = self.scalar(self.support.k)
        for common_r, table in j_moments.items():
            for left_class in (0, 1):
                left_r = common_r + left_class
                if (left_r, 0) not in positions:
                    continue
                for right_class in (0, 1):
                    right_r = common_r + right_class
                    if (right_r, 0) not in positions:
                        continue
                    for p, left in enumerate(powers):
                        i = positions[(left_r, p)]
                        for q, right in enumerate(powers):
                            j = positions[(right_r, q)]
                            b[i][j] += kfactor * self._j_channel_entry(
                                table, left, right,
                                left_class, right_class)
        if any(a[i][j] != a[j][i] or b[i][j] != b[j][i]
               for i in range(n) for j in range(n)):
            raise ArithmeticError("moment-table assembly lost symmetry")
        return labels, a, b

    def evaluate_moment_forms(self, progress=False):
        i, groups, i_faces, i_scalar = self.evaluate_i_moments(progress)
        j, components, domains, products, j_scalar = \
            self.evaluate_j_moments(progress)
        labels, a, b = self.assemble_dense_from_moments(i, j)
        return {
            "degree": self.degree,
            "channel_powers": self.moment_channels,
            "labels": labels,
            "a_matrix": a,
            "b_matrix": b,
            "i_moments": i,
            "j_moments": j,
            "i_orbit_groups": groups,
            "i_faces": i_faces,
            "i_scalar_moment_integrals": i_scalar,
            "marginal_components": components,
            "j_branch_domains": domains,
            "j_moment_products": products,
            "j_scalar_moment_integrals": j_scalar,
        }


def quadratic(matrix, vector, zero=Fraction(0)):
    return sum((vector[i] * matrix[i][j] * vector[j]
                for i in range(len(vector)) for j in range(len(vector))),
               zero)


__all__ = [
    "StratumMomentTableEvaluator", "aggregate_powers", "channel_powers",
    "distinguished_limit", "quadratic", "remaining_power",
]
