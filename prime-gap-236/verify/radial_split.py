#!/usr/bin/env python3
"""Two-piece radial-amplitude probe for a full-simplex sieve polynomial.

The candidate is ``a*F`` on ``sum(t)<=V`` and ``b*F`` on
``V<sum(t)<=R``.  The script reconstructs the two denominator blocks and all
three marginal-product blocks from the literal symmetric polynomial.  It is
independent of serialized matrices used to discover F.

Decimal mode is for discovery.  Fraction mode (``--exact``) evaluates the
same finite Dirichlet-moment identities exactly.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from collections import defaultdict
from decimal import Decimal, getcontext
from fractions import Fraction as Q
from functools import lru_cache
from math import comb, factorial
from pathlib import Path

HERE = Path(__file__).resolve().parent
EI_DIR = HERE.parent / "agents" / "exact-integrator" / "src"
sys.path.insert(0, str(EI_DIR))

import exact_integrator as ei  # noqa: E402


def power(x, n, one):
    return one if n == 0 else x ** n


def expand_square(basis, vector, scalar):
    answer = defaultdict(lambda: scalar(0))
    for i, (a, lam) in enumerate(basis):
        for j in range(i + 1):
            b, mu = basis[j]
            coefficient = vector[i] * vector[j] * (1 if i == j else 2)
            for nu, multiplicity in ei.multiply_monomial_orbits(lam, mu):
                answer[(a + b, nu)] += coefficient * multiplicity
    return {key: value for key, value in answer.items() if value}


def simplex_residual_moment(k, radius, c, nu, scalar):
    """Integral of ``(1-S)^c P_nu`` on the radius simplex."""
    one = scalar(1)
    degree = sum(nu)
    product_factorials = 1
    for exponent in nu:
        product_factorials *= factorial(exponent)
    answer = scalar(0)
    for d in range(c + 1):
        radial_degree = k + degree + d
        answer += (scalar(comb(c, d) * product_factorials * factorial(d),
                          factorial(radial_degree)) *
                   power(one - radius, c - d, one) *
                   power(radius, radial_degree, one))
    return scalar(ei.orbit_size(k, nu)) * answer


def marginal_expansion(basis, vector, k, upper, scalar):
    """Expand integral in the distinguished variable up to upper-U."""
    one = scalar(1)
    answer = defaultdict(lambda: scalar(0))
    for coefficient, (a, lam) in zip(vector, basis):
        for e, rest in ei.OneStratumSupport.split_at_distinguished(lam, k):
            for c in range(a + 1):
                p = e + c + 1
                beta = scalar(comb(a, c) * factorial(e) * factorial(c),
                              factorial(e + c + 1))
                beta *= power(one - upper, a - c, one)
                answer[(rest, p)] += coefficient * beta
    return {key: value for key, value in answer.items() if value}


class CrossMoments:
    def __init__(self, dimension, shared_radius, scalar):
        self.dimension = dimension
        self.shared_radius = shared_radius
        self.scalar = scalar
        self.zero = scalar(0)
        self.one = scalar(1)

    @lru_cache(maxsize=None)
    def moment(self, nu, p, q, left_upper, right_upper):
        degree = sum(nu)
        product_factorials = 1
        for exponent in nu:
            product_factorials *= factorial(exponent)
        answer = self.zero
        for d in range(p + 1):
            left = (self.scalar(comb(p, d)) *
                    power(left_upper - self.shared_radius, p - d, self.one))
            for e in range(q + 1):
                total_residual = d + e
                radial_degree = degree + self.dimension + total_residual
                right = (self.scalar(comb(q, e)) *
                         power(right_upper - self.shared_radius,
                               q - e, self.one))
                answer += (left * right *
                           self.scalar(product_factorials *
                                       factorial(total_residual),
                                       factorial(radial_degree)) *
                           power(self.shared_radius, radial_degree, self.one))
        return self.scalar(ei.orbit_size(self.dimension, nu)) * answer

    def contract(self, left, right, left_upper, right_upper, progress=0):
        # Aggregate orbit products first; many marginal pairs lead to the same
        # (nu,p,q) moment.
        products = defaultdict(lambda: self.scalar(0))
        left_items, right_items = list(left.items()), list(right.items())
        symmetric = left is right and left_upper == right_upper
        if symmetric:
            for i, ((lam, p), x) in enumerate(left_items):
                for j in range(i + 1):
                    (mu, q), y = left_items[j]
                    coefficient = x * y * (1 if i == j else 2)
                    pp, qq = (p, q) if p >= q else (q, p)
                    for nu, multiplicity in ei.multiply_monomial_orbits(lam, mu):
                        products[(nu, pp, qq)] += coefficient * multiplicity
        else:
            for (lam, p), x in left_items:
                for (mu, q), y in right_items:
                    for nu, multiplicity in ei.multiply_monomial_orbits(lam, mu):
                        products[(nu, p, q)] += x * y * multiplicity
        products = {key: value for key, value in products.items() if value}
        print(f"cross_products {len(products)}", flush=True)
        answer = self.zero
        for index, ((nu, p, q), coefficient) in enumerate(products.items(), 1):
            answer += coefficient * self.moment(
                nu, p, q, left_upper, right_upper)
            if progress and index % progress == 0:
                print(f"cross_moments {index}/{len(products)}", flush=True)
        return answer


def largest_generalized_2x2(i_inner, i_outer, j_ii, j_io, j_oo, scalar):
    """Return eigenvalues after diagonal denominator whitening (Decimal only)."""
    a = j_ii / i_inner
    d = j_oo / i_outer
    b2 = (j_io * j_io) / (i_inner * i_outer)
    disc = ((a - d) * (a - d) + scalar(4) * b2).sqrt()
    return (a + d + disc) / scalar(2), (a + d - disc) / scalar(2)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("certificate", type=Path)
    parser.add_argument("--exact", action="store_true")
    parser.add_argument("--dps", type=int, default=100)
    parser.add_argument("--progress", type=int, default=500)
    args = parser.parse_args()
    if args.dps < 50:
        parser.error("require dps >= 50")
    cert_bytes = args.certificate.read_bytes()
    cert = json.loads(cert_bytes)
    k = int(cert["k"])
    basis = [(int(a), tuple(int(x) for x in lam))
             for a, lam in cert["basis"]]
    rational_vector = [Q(x) for x in cert["rational_vector"]]
    if len(basis) != len(rational_vector):
        raise ValueError("basis/vector mismatch")
    radius_q = Q(cert["parameters"]["alpha"])
    cutoff_q = Q(cert["parameters"]["eta"])

    if args.exact:
        scalar = Q
    else:
        getcontext().prec = args.dps

        def scalar(numerator=0, denominator=None):
            if isinstance(numerator, Q):
                return Decimal(numerator.numerator) / Decimal(numerator.denominator)
            if denominator is None:
                return Decimal(numerator)
            return Decimal(numerator) / Decimal(denominator)

    radius, cutoff = scalar(radius_q), scalar(cutoff_q)
    vector = [scalar(x) for x in rational_vector]
    start = time.perf_counter()

    square = expand_square(basis, vector, scalar)
    inner_i = sum((coefficient * simplex_residual_moment(
        k, cutoff, c, nu, scalar) for (c, nu), coefficient in square.items()),
                  scalar(0))
    full_i = scalar(Q(cert["exact_denominator"]))
    outer_i = full_i - inner_i
    print(f"denominator_done terms={len(square)} seconds={time.perf_counter()-start:.3f}",
          flush=True)

    marginal_r = marginal_expansion(basis, vector, k, radius, scalar)
    marginal_v = marginal_expansion(basis, vector, k, cutoff, scalar)
    print(f"marginal_terms R={len(marginal_r)} V={len(marginal_v)}", flush=True)
    cross = CrossMoments(k - 1, cutoff, scalar)
    rr = cross.contract(marginal_r, marginal_r, radius, radius, args.progress)
    vv = cross.contract(marginal_v, marginal_v, cutoff, cutoff, args.progress)
    vr = cross.contract(marginal_v, marginal_r, cutoff, radius, args.progress)

    factor = scalar(k)
    j_ii = factor * vv
    j_io = factor * (vr - vv)
    j_oo = factor * (rr - scalar(2) * vr + vv)
    recorded_num = scalar(Q(cert["exact_numerator"]))
    baseline_delta = factor * rr - recorded_num
    print("status", "exact" if args.exact else "decimal-discovery")
    print("certificate_sha256", hashlib.sha256(cert_bytes).hexdigest())
    print("I_inner", inner_i)
    print("I_outer", outer_i)
    print("M2_inner_inner", j_ii)
    print("M2_inner_outer", j_io)
    print("M2_outer_outer", j_oo)
    print("baseline_M2_delta", baseline_delta)
    if not args.exact:
        high, low = largest_generalized_2x2(
            inner_i, outer_i, j_ii, j_io, j_oo, scalar)
        print("eigenvalue_high", high)
        print("eigenvalue_low", low)
        print("margin_high", high - scalar(1))
    print("seconds", time.perf_counter() - start)


if __name__ == "__main__":
    main()
