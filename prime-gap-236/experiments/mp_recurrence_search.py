#!/usr/bin/env python3
"""Multiprecision discovery using the exact integrator's combinatorial recurrence.

Unlike ``fast_float_search.py``, this retains enough precision to survive the
large inclusion--exclusion cancellations.  It is still discovery-only: a
winning finite rational vector must be rerun by the Fraction implementation.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
import json
from functools import lru_cache
from math import comb, factorial
import os
import sys
import time

from decimal import Decimal, getcontext, localcontext

HERE = os.path.dirname(os.path.abspath(__file__))
INTEGRATOR_SRC = os.path.abspath(
    os.path.join(HERE, "..", "agents", "exact-integrator", "src")
)
sys.path.insert(0, INTEGRATOR_SRC)

import exact_integrator as ei  # noqa: E402


def parse_mp(text: str):
    if "/" in text:
        p, q = text.split("/", 1)
        return Decimal(p) / Decimal(q)
    return Decimal(text)


def precompute_orbit_products(basis):
    """Compute integral orbit constants before replacing Fraction by mpf."""
    needed = set()
    for _, lam in basis:
        for _, mu in basis:
            needed.add((lam, mu))
            for _, lr in ei.OneStratumSupport.split_at_distinguished(lam, 48):
                for _, mr in ei.OneStratumSupport.split_at_distinguished(mu, 48):
                    needed.add((lr, mr))
    table = {}
    for lam, mu in needed:
        table[(lam, mu)] = ei.multiply_monomial_orbits(lam, mu)
    return table


def install_mp_scalar(orbit_table):
    def mpq(numerator=0, denominator=None):
        if denominator is None:
            return Decimal(numerator)
        return Decimal(numerator) / Decimal(denominator)

    def orbit_lookup(lam, mu):
        key = (tuple(lam), tuple(mu))
        if key in orbit_table:
            return orbit_table[key]
        # Products are symmetric; retain a defensive reverse lookup.
        rev = (key[1], key[0])
        if rev in orbit_table:
            return orbit_table[rev]
        raise KeyError(f"orbit product was not precomputed: {key}")

    ei.Q = mpq
    ei.multiply_monomial_orbits = orbit_lookup

    # Decimal deliberately signals 0**0 whereas the exact polynomial expansion
    # correctly interprets every zero exponent as the multiplicative identity.
    @lru_cache(maxsize=None)
    def decimal_linear_power(c0, cz, cw, n):
        out = defaultdict(Decimal)
        for i in range(n + 1):
            for j in range(n - i + 1):
                h = n - i - j
                coeff = Decimal(factorial(n)) / (
                    Decimal(factorial(i)) * Decimal(factorial(j)) * Decimal(factorial(h))
                )
                pz = Decimal(1) if i == 0 else cz ** i
                pw = Decimal(1) if j == 0 else cw ** j
                pc = Decimal(1) if h == 0 else c0 ** h
                out[(i, j)] += coeff * pz * pw * pc
        return tuple(out.items())

    ei._linear_power = decimal_linear_power

    def dpow(x, n):
        return Decimal(1) if n == 0 else x ** n

    @lru_cache(maxsize=None)
    def decimal_polygon_monomial(poly, az, aw):
        if not poly:
            return Decimal(0)
        ans = Decimal(0)
        ap = az + 1
        for idx, (x0, y0) in enumerate(poly):
            x1, y1 = poly[(idx + 1) % len(poly)]
            dx, dy = x1 - x0, y1 - y0
            if dy == 0:
                continue
            if dx == 0:
                ans += dpow(x0, ap) * (
                    dpow(y1, aw + 1) - dpow(y0, aw + 1)
                ) / Decimal(ap * (aw + 1))
                continue
            if dx + dy == 0:
                const = x0 + y0
                edge = Decimal(0)
                for i in range(ap + 1):
                    edge += (Decimal(((-1) ** i) * comb(ap, i)) /
                             Decimal(aw + i + 1) * dpow(const, ap - i) *
                             (dpow(y1, aw + i + 1) - dpow(y0, aw + i + 1)))
                ans += edge / Decimal(ap)
                continue
            edge = Decimal(0)
            for i in range(ap + 1):
                for j in range(aw + 1):
                    edge += (Decimal(comb(ap, i) * comb(aw, j)) /
                             Decimal(i + j + 1) * dpow(x0, ap - i) * dpow(dx, i) *
                             dpow(y0, aw - j) * dpow(dy, j))
            ans += dy * edge / Decimal(ap)
        return ans

    ei.polygon_monomial = decimal_polygon_monomial


def generalized_eigen(m1, m2, iterations=120):
    """Decimal power iteration on the diagonally scaled generalized problem."""
    n = len(m1)
    scale = [m1[i][i].sqrt() for i in range(n)]
    a = [[m1[i][j] / scale[i] / scale[j] for j in range(n)] for i in range(n)]
    b = [[m2[i][j] / scale[i] / scale[j] for j in range(n)] for i in range(n)]

    lu = [row[:] for row in a]
    piv = list(range(n))
    for col in range(n):
        p = max(range(col, n), key=lambda i: abs(lu[i][col]))
        if lu[p][col] == 0:
            raise ArithmeticError("Decimal Gram matrix is singular at this precision")
        if p != col:
            lu[p], lu[col] = lu[col], lu[p]
            piv[p], piv[col] = piv[col], piv[p]
        pivot = lu[col][col]
        for i in range(col + 1, n):
            lu[i][col] /= pivot
            mul = lu[i][col]
            for j in range(col + 1, n):
                lu[i][j] -= mul * lu[col][j]

    def solve(rhs):
        y = [rhs[piv[i]] for i in range(n)]
        for i in range(n):
            for j in range(i):
                y[i] -= lu[i][j] * y[j]
        x = y[:]
        for i in range(n - 1, -1, -1):
            for j in range(i + 1, n):
                x[i] -= lu[i][j] * x[j]
            x[i] /= lu[i][i]
        return x

    v = [Decimal(1) / Decimal(i + 1) for i in range(n)]
    quotient = Decimal(0)
    for _ in range(iterations):
        rhs = [sum((b[i][j] * v[j] for j in range(n)), Decimal(0)) for i in range(n)]
        w = solve(rhs)
        norm = max(abs(x) for x in w)
        v = [x / norm for x in w]
        av = [sum((a[i][j] * v[j] for j in range(n)), Decimal(0)) for i in range(n)]
        bv = [sum((b[i][j] * v[j] for j in range(n)), Decimal(0)) for i in range(n)]
        quotient = sum((v[i] * bv[i] for i in range(n)), Decimal(0)) / sum(
            (v[i] * av[i] for i in range(n)), Decimal(0)
        )

    vector = [v[i] / scale[i] for i in range(n)]
    denom = sum((vector[i] * m1[i][j] * vector[j]
                 for i in range(n) for j in range(n)), Decimal(0))
    numer = sum((vector[i] * m2[i][j] * vector[j]
                 for i in range(n) for j in range(n)), Decimal(0))
    quotient = numer / denom
    residual = max(abs(sum((m2[i][j] * vector[j] - quotient * m1[i][j] * vector[j]
                            for j in range(n)), Decimal(0))) for i in range(n))
    return quotient, vector, residual


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--k", type=int, default=48)
    ap.add_argument("--degree", type=int, default=4)
    ap.add_argument("--family", choices=("even", "no-ones"), default="no-ones")
    ap.add_argument("--max-length", type=int)
    ap.add_argument("--dps", type=int, default=70)
    ap.add_argument("--alpha", default="163/625")
    ap.add_argument("--eta", default="627/2500")
    ap.add_argument("--delta", default="1/50")
    ap.add_argument("--beta1", default="3/20")
    ap.add_argument("--beta2", default="3/20")
    ap.add_argument("--beta3plus", default="17/100")
    ap.add_argument("--output")
    args = ap.parse_args()

    getcontext().prec = args.dps
    basis_fn = ei.even_basis if args.family == "even" else ei.no_ones_basis
    basis = basis_fn(args.degree, args.max_length)
    orbit_table = precompute_orbit_products(basis)
    install_mp_scalar(orbit_table)
    support = ei.OneStratumSupport(
        args.k,
        *map(parse_mp, (args.alpha, args.delta, args.eta,
                        args.beta1, args.beta2, args.beta3plus)),
    )
    start = time.perf_counter()
    m1, m2 = support.matrices(basis)
    matrix_seconds = time.perf_counter() - start
    quotient, vector, residual = generalized_eigen(m1, m2)
    scaled = [abs(vector[i]) * m1[i][i].sqrt() for i in range(len(basis))]
    order = sorted(range(len(basis)), key=lambda i: scaled[i], reverse=True)
    result = {
        "rigorous": False,
        "status": "multiprecision discovery only",
        "dps": args.dps,
        "parameters": vars(args),
        "basis_dimension": len(basis),
        "matrix_seconds": matrix_seconds,
        "quotient": str(quotient),
        "residual_norm": str(residual),
        "basis": basis,
        "vector": [str(vector[i]) for i in range(len(basis))],
        "leverage_order": order,
    }
    rendered = json.dumps(result, indent=2) + "\n"
    if args.output:
        os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as out:
            out.write(rendered)
    print(rendered, end="")


if __name__ == "__main__":
    main()
