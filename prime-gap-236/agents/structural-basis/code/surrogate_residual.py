#!/usr/bin/env python3
"""Rank explicit orbit directions by their one-step Rayleigh gain.

The expensive cut support is replaced only for *ranking* by the full simplex
having the same total-sum and J cutoffs.  Every label printed here is an exact
polynomial ``(1-sum(t))^a P_lambda(t)`` and can subsequently be tested by the
exact cut-support integrator.  No quotient from this script is a certificate
for the cut support.
"""

from __future__ import annotations

import argparse
import os
import sys
from decimal import Decimal, localcontext
from fractions import Fraction as Q

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.abspath(os.path.join(HERE, "..", "..", "exact-integrator", "src"))
sys.path.insert(0, SRC)

from exact_integrator import (  # noqa: E402
    OneStratumSupport,
    decimal_generalized_power,
    exact_quadratic,
    no_ones_basis,
)


def qd(x: Q) -> Decimal:
    return Decimal(x.numerator) / Decimal(x.denominator)


def top_2x2(a: Q, b: Q, u: Q, v: Q, d: Q, e: Q) -> Decimal:
    """Largest root of det(B-lambda A), for A=[[a,u],[u,d]]."""
    # (ad-u^2) L^2 + (-bd-ea+2uv)L + (be-v^2) = 0.
    aa = a * d - u * u
    bb = -(b * d + e * a - 2 * u * v)
    cc = b * e - v * v
    if aa <= 0:
        raise ArithmeticError("candidate is dependent in the A inner product")
    with localcontext() as ctx:
        ctx.prec = 100
        A, B, C = qd(aa), qd(bb), qd(cc)
        disc = B * B - Decimal(4) * A * C
        return (-B + disc.sqrt()) / (Decimal(2) * A)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-degree", type=int, default=4)
    ap.add_argument("--dictionary-degree", type=int, default=14)
    ap.add_argument("--top", type=int, default=30)
    ap.add_argument("--alpha", default="163/625")
    ap.add_argument("--eta", default="627/2500")
    args = ap.parse_args()

    alpha, eta = Q(args.alpha), Q(args.eta)
    # beta=alpha makes every stratum cap redundant; delta is immaterial.
    support = OneStratumSupport(48, alpha, Q(1, 50), eta,
                                alpha, alpha, alpha)
    base = no_ones_basis(args.base_degree)
    m1, m2 = support.matrices(base)
    lam, c = decimal_generalized_power(m1, m2, 130, 120)
    cq = [Q(str(x)).limit_denominator(10**12) for x in c]
    a = exact_quadratic(m1, cq)
    b = exact_quadratic(m2, cq)
    assert a > 0

    scored = []
    for g in no_ones_basis(args.dictionary_degree):
        if g in base:
            continue
        ar = [support.basis_m1(x, g) for x in base]
        br = [support.k * support.basis_j(x, g) for x in base]
        u = sum(cq[i] * ar[i] for i in range(len(base)))
        v = sum(cq[i] * br[i] for i in range(len(base)))
        d = support.basis_m1(g, g)
        e = support.k * support.basis_j(g, g)
        try:
            q = top_2x2(a, b, u, v, d, e)
        except ArithmeticError:
            continue
        scored.append((q, g))

    scored.sort(reverse=True)
    print("HEURISTIC FULL-SIMPLEX SURROGATE ONLY")
    print("base_dimension", len(base), "base_quotient", b / a, float(b / a))
    print("dictionary_dimension", len(no_ones_basis(args.dictionary_degree)))
    for q, g in scored[:args.top]:
        print(g, q, "gain", q - qd(b / a))


if __name__ == "__main__":
    main()
