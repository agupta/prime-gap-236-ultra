#!/usr/bin/env python3
"""Independent dead-core mass probe for the direct-BV full simplex.

For ``R=A+e`` and ``V=A-e``, the set

    C = {t >= 0: sum(t) < R and sum_{j != i} t_j > V for every i}

does not meet any fibre used by a ``J_i`` integral.  Replacing a symmetric
polynomial F by ``F * 1_{C^c}`` therefore leaves every J_i unchanged and
replaces I by ``I-I_C``.  This script reconstructs I_C from the literal
polynomial vector, rather than trusting a serialized dead-core integral.

The default Decimal calculation is a discovery probe.  ``--exact`` evaluates
the same finite formula with Fraction arithmetic and is intended for a final
certificate if the discovery sign is favorable.
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


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def power(x, n: int, one):
    return one if n == 0 else x ** n


class DeadCoreMoments:
    """Moments of ``(1-S)^c P_nu`` over C by inclusion--exclusion."""

    def __init__(self, k: int, radius, cutoff, scalar):
        if not (0 < cutoff < radius):
            raise ValueError("require 0 < V < R")
        self.k = k
        self.radius = radius
        self.cutoff = cutoff
        self.width = radius - cutoff
        self.scalar = scalar
        self.zero = scalar(0)
        self.one = scalar(1)

    @lru_cache(maxsize=None)
    def selection_coefficients(self, nu):
        """Return C[j,r] after selecting j shifted coordinates.

        For a selected coordinate with original exponent a, expand
        ``(x+u)^a``.  Here r is the total power of u and the coefficient
        already contains the factorials from the simplex-slice integral.
        Zero exponents are retained: they supply the binomial choice of which
        of the k coordinates belongs to the inclusion--exclusion subset.
        """
        if len(nu) > self.k or any(a <= 0 for a in nu):
            raise ValueError("malformed partition")
        exponents = tuple(nu) + (0,) * (self.k - len(nu))
        dp = {(0, 0): 1}
        for a in exponents:
            nxt = defaultdict(int)
            for (j, r), coefficient in dp.items():
                # Coordinate outside the selected subset.
                nxt[(j, r)] += coefficient * factorial(a)
                # Coordinate inside it; t=x+u and b is the x exponent.
                for b in range(a + 1):
                    nxt[(j + 1, r + a - b)] += (
                        coefficient * comb(a, b) * factorial(b)
                    )
            dp = dict(nxt)
        return tuple(sorted(dp.items()))

    @lru_cache(maxsize=None)
    def radial_integral(self, c: int, r: int, n: int, j: int):
        """Integrate ``(1-V-u)^c u^r (V-(j-1)u)^n`` exactly/numerically."""
        if min(c, r, n, j) < 0 or j > self.k:
            raise ValueError("invalid radial exponents")
        upper = self.width
        if j >= 2:
            upper = min(upper, self.cutoff / self.scalar(j - 1))
        answer = self.zero
        for a in range(c + 1):
            ca = (self.scalar((-1) ** a * comb(c, a)) *
                  power(self.one - self.cutoff, c - a, self.one))
            for b in range(n + 1):
                cb = (self.scalar((-1) ** b * comb(n, b)) *
                      power(self.cutoff, n - b, self.one) *
                      power(self.scalar(j - 1), b, self.one))
                degree = r + a + b + 1
                answer += ca * cb * power(upper, degree, self.one) / degree
        return answer

    @lru_cache(maxsize=None)
    def moment(self, c: int, nu):
        if c < 0:
            raise ValueError("negative residual exponent")
        nu = tuple(nu)
        degree = sum(nu)
        answer = self.zero
        for (j, r), coefficient in self.selection_coefficients(nu):
            radial_degree = self.k + degree - r - 1
            answer += (self.scalar((-1) ** j * coefficient) *
                       self.radial_integral(c, r, radial_degree, j) /
                       factorial(radial_degree))
        return self.scalar(ei.orbit_size(self.k, nu)) * answer


def expand_square(basis, vector, scalar):
    """Expand the literal symmetric polynomial square into (c,nu) terms."""
    answer = defaultdict(lambda: scalar(0))
    for i, (a, lam) in enumerate(basis):
        for j in range(i + 1):
            b, mu = basis[j]
            coefficient = vector[i] * vector[j]
            if i != j:
                coefficient *= 2
            if not coefficient:
                continue
            for nu, multiplicity in ei.multiply_monomial_orbits(lam, mu):
                answer[(a + b, nu)] += coefficient * multiplicity
    return {key: value for key, value in answer.items() if value}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("certificate", type=Path)
    parser.add_argument("--exact", action="store_true")
    parser.add_argument("--dps", type=int, default=100)
    parser.add_argument("--progress", type=int, default=500,
                        help="print every N reconstructed moments; 0 disables")
    args = parser.parse_args()
    if args.dps < 50:
        parser.error("require at least 50 decimal digits")

    cert_bytes = args.certificate.read_bytes()
    cert = json.loads(cert_bytes)
    k = int(cert["k"])
    basis = [(int(a), tuple(int(x) for x in lam))
             for a, lam in cert["basis"]]
    rational_vector = [Q(x) for x in cert["rational_vector"]]
    if len(basis) != len(rational_vector) or len(basis) != len(set(basis)):
        raise ValueError("basis/vector mismatch")
    parameters = cert["parameters"]
    radius_q, cutoff_q = Q(parameters["alpha"]), Q(parameters["eta"])
    if any(Q(parameters[key]) != radius_q
           for key in ("beta1", "beta2", "beta3plus")):
        raise ValueError("certificate is not a full-simplex constant schedule")

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

    vector = [scalar(x) for x in rational_vector]
    start = time.perf_counter()
    square = expand_square(basis, vector, scalar)
    print(f"expanded_terms {len(square)} seconds {time.perf_counter()-start:.3f}",
          flush=True)
    moments = DeadCoreMoments(k, scalar(radius_q), scalar(cutoff_q), scalar)
    dead = scalar(0)
    for index, ((c, nu), coefficient) in enumerate(square.items(), 1):
        dead += coefficient * moments.moment(c, nu)
        if args.progress and index % args.progress == 0:
            print(f"moments {index}/{len(square)} "
                  f"seconds {time.perf_counter()-start:.3f}", flush=True)

    denominator = scalar(Q(cert["exact_denominator"]))
    old_q = scalar(Q(cert["exact_quotient"]))
    dead_fraction = dead / denominator
    new_denominator = denominator - dead
    new_q = old_q * denominator / new_denominator
    if denominator <= 0 or dead < 0 or new_denominator <= 0:
        raise ArithmeticError("invalid reconstructed denominator masses")

    print("status", "exact" if args.exact else "decimal-discovery")
    print("certificate_sha256", hashlib.sha256(cert_bytes).hexdigest())
    print("integrator_sha256", sha256(EI_DIR / "exact_integrator.py"))
    print("dead_mass", dead)
    print("original_I", denominator)
    print("dead_fraction", dead_fraction)
    print("old_quotient", old_q)
    print("new_quotient", new_q)
    print("new_margin", new_q - scalar(1))
    print("seconds", time.perf_counter() - start)


if __name__ == "__main__":
    main()
