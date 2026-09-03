#!/usr/bin/env python3
"""Build an exact support-stratum-aligned polynomial Rayleigh quotient."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
import sys
import time
from fractions import Fraction

if hasattr(sys, "set_int_max_str_digits"):
    sys.set_int_max_str_digits(0)

HERE = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(HERE, "src"))

from exact_integrator import (decimal_generalized_power, even_basis,
                              exact_quadratic, no_ones_basis)  # noqa: E402
from stratum_integrator import StratumSupport  # noqa: E402


def qarg(text: str) -> Fraction:
    return Fraction(text)


def matrix_hash(m1, m2):
    digest = hashlib.sha256()
    for name, matrix in (("M1", m1), ("M2", m2)):
        digest.update((name + "\n").encode())
        for row in matrix:
            digest.update(("\t".join(str(x) for x in row) + "\n").encode())
    return digest.hexdigest()


def cached_stratum_matrices(support, basis, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    db = sqlite3.connect(path, timeout=300)
    db.execute("pragma busy_timeout=300000")
    db.execute("create table if not exists entries "
               "(cache_key text primary key, m1 text not null, m2 text not null)")
    n = len(basis)
    m1 = [[Fraction(0) for _ in range(n)] for _ in range(n)]
    m2 = [[Fraction(0) for _ in range(n)] for _ in range(n)]
    hits = misses = 0
    params = [support.k, str(support.alpha), str(support.delta), str(support.eta),
              str(support.beta1), str(support.beta2), str(support.beta3plus)]
    last_commit = time.monotonic()
    for i, (ri, xi) in enumerate(basis):
        for j in range(i + 1):
            rj, xj = basis[j]
            key = json.dumps(["stratum-v1", params, basis[i], basis[j]],
                             separators=(",", ":"))
            row = db.execute("select m1,m2 from entries where cache_key=?", (key,)).fetchone()
            if row is None:
                x = (support.basis_m1_in_strata(ri, xi, rj, xj)
                     if ri == rj else Fraction(0))
                y = (support.k * support.basis_j_in_strata(ri, xi, rj, xj)
                     if abs(ri - rj) <= 1 else Fraction(0))
                db.execute("insert into entries values (?,?,?)", (key, str(x), str(y)))
                misses += 1
                if time.monotonic() - last_commit >= 5:
                    db.commit()
                    last_commit = time.monotonic()
            else:
                x, y = Fraction(row[0]), Fraction(row[1])
                hits += 1
            m1[i][j] = m1[j][i] = x
            m2[i][j] = m2[j][i] = y
        db.commit()
        print(f"stratum matrix row {i + 1}/{n}: hits={hits} misses={misses}",
              file=sys.stderr, flush=True)
    db.close()
    return m1, m2, hits, misses


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--k", type=int, default=48)
    parser.add_argument("--degree", type=int, default=2)
    parser.add_argument("--family", choices=("no-ones", "even"), default="no-ones")
    parser.add_argument("--max-length", type=int)
    parser.add_argument("--strata", help="comma-separated stratum indices; default: all nonempty")
    parser.add_argument("--alpha", type=qarg, required=True)
    parser.add_argument("--eta", type=qarg, required=True)
    parser.add_argument("--delta", type=qarg, required=True)
    parser.add_argument("--beta1", type=qarg, required=True)
    parser.add_argument("--beta2", type=qarg, required=True)
    parser.add_argument("--beta3plus", type=qarg, required=True)
    parser.add_argument("--decimal-precision", type=int, default=180)
    parser.add_argument("--power-iterations", type=int, default=500)
    parser.add_argument("--rational-denominator", type=int, default=10**18)
    parser.add_argument("--cache", default=os.path.join(HERE, "cache", "stratum.sqlite3"))
    parser.add_argument("--output")
    args = parser.parse_args()

    support = StratumSupport(args.k, args.alpha, args.delta, args.eta,
                             args.beta1, args.beta2, args.beta3plus)
    polynomial_basis = (no_ones_basis(args.degree, args.max_length)
                        if args.family == "no-ones"
                        else even_basis(args.degree, args.max_length))
    if args.strata:
        strata = sorted(set(int(x) for x in args.strata.split(",")))
    else:
        strata = [r for r in range(args.k + 1)
                   if support.canonical_support_moment_in_stratum((), 0, r) > 0]
    if any(r < 0 or r > args.k for r in strata):
        parser.error("stratum index outside [0,k]")
    basis = [(r, label) for r in strata for label in polynomial_basis]

    hashes = {}
    for name in ("exact_integrator.py", "stratum_integrator.py"):
        path = os.path.join(HERE, "src", name)
        with open(path, "rb") as stream:
            hashes[name] = hashlib.sha256(stream.read()).hexdigest()
    start = time.perf_counter()
    m1, m2, hits, misses = cached_stratum_matrices(
        support, basis, args.cache)
    exact_seconds = time.perf_counter() - start
    eigen, vector = decimal_generalized_power(
        m1, m2, args.decimal_precision, args.power_iterations)
    rv = [Fraction(x).limit_denominator(args.rational_denominator) for x in vector]
    den = exact_quadratic(m1, rv)
    num = exact_quadratic(m2, rv)
    margin = num - den
    record = {
        "k": args.k,
        "degree": args.degree,
        "family": args.family,
        "strata": strata,
        "polynomial_basis_dimension": len(polynomial_basis),
        "basis_dimension": len(basis),
        "basis": [[r, [label[0], list(label[1])]] for r, label in basis],
        "parameters": {"alpha": str(args.alpha), "eta": str(args.eta),
                       "delta": str(args.delta), "beta1": str(args.beta1),
                       "beta2": str(args.beta2),
                       "beta3plus": str(args.beta3plus)},
        "source_sha256": hashes,
        "exact_matrices_sha256": matrix_hash(m1, m2),
        "exact_matrix_seconds": exact_seconds,
        "cache_hits": hits,
        "cache_misses": misses,
        "decimal_generalized_eigenvalue": str(eigen),
        "rational_vector": [str(x) for x in rv],
        "exact_denominator_positive": den > 0,
        "exact_margin_positive": margin > 0,
        "exact_quadratic_denominator": str(den),
        "exact_quadratic_numerator": str(num),
        "exact_quotient": str(num / den),
        "exact_quotient_decimal": float(num / den),
        "exact_margin": str(margin),
    }
    rendered = json.dumps(record, indent=2) + "\n"
    if args.output:
        with open(args.output, "w", encoding="utf-8") as stream:
            stream.write(rendered)
    print(rendered)


if __name__ == "__main__":
    main()
