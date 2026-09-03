#!/usr/bin/env python3
"""Exact global-polynomial plus support-stratum correction search.

Basis labels are either ``["G", [a,lambda]]`` or
``["R", r, [a,lambda]]``.  The latter multiplies the polynomial by the
indicator that exactly r coordinates exceed delta.  One reference stratum is
omitted from the correction basis, removing the evident relation
``G = sum_r R_r G``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
import sys
import time
from fractions import Fraction as Q
from pathlib import Path

if hasattr(sys, "set_int_max_str_digits"):
    sys.set_int_max_str_digits(0)

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.abspath(os.path.join(HERE, "..", "..", "exact-integrator", "src"))
sys.path.insert(0, SRC)

from exact_integrator import (decimal_generalized_power, exact_quadratic,  # noqa:E402
                              no_ones_basis)
from stratum_integrator import StratumSupport  # noqa:E402


def qarg(value):
    return Q(value)


def encode(label):
    if label[0] == "G":
        a, lam = label[1]
        return ["G", [a, list(lam)]]
    _, r, (a, lam) = label
    return ["R", r, [a, list(lam)]]


def entry(support, left, right):
    if left[0] == "G" and right[0] == "G":
        x, y = left[1], right[1]
        return support.basis_m1(x, y), support.k * support.basis_j(x, y)
    if left[0] == "G":
        x = left[1]; _, r, y = right
        m1 = support.basis_m1_in_strata(r, x, r, y)
        j = sum(support.basis_j_in_strata(s, x, r, y)
                for s in range(max(0, r - 1), min(support.k, r + 1) + 1))
        return m1, support.k * j
    if right[0] == "G":
        m1, m2 = entry(support, right, left)
        return m1, m2
    _, r, x = left; _, s, y = right
    m1 = (support.basis_m1_in_strata(r, x, s, y) if r == s else Q(0))
    m2 = (support.k * support.basis_j_in_strata(r, x, s, y)
          if abs(r - s) <= 1 else Q(0))
    return m1, m2


def matrices(support, basis, cache_path, global_cache_path=None):
    Path(cache_path).parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(cache_path, timeout=300)
    db.execute("pragma busy_timeout=300000")
    db.execute("create table if not exists entries "
               "(cache_key text primary key,m1 text not null,m2 text not null)")
    global_db = sqlite3.connect(global_cache_path) if global_cache_path else None
    params = [support.k, str(support.alpha), str(support.delta), str(support.eta),
              str(support.beta1), str(support.beta2), str(support.beta3plus)]
    n = len(basis); A = [[Q(0) for _ in range(n)] for _ in range(n)]
    B = [[Q(0) for _ in range(n)] for _ in range(n)]
    hits = misses = 0
    for i in range(n):
        for j in range(i + 1):
            key = json.dumps(["hybrid-v1", params, encode(basis[i]), encode(basis[j])],
                             separators=(",", ":"))
            row = db.execute("select m1,m2 from entries where cache_key=?", (key,)).fetchone()
            # Reuse only as a computational cache.  The result still records a
            # reconstructible matrix hash and the verifier must rebuild entries.
            if (row is None and global_db is not None and basis[i][0] == "G"
                    and basis[j][0] == "G"):
                standard_key = json.dumps(
                    [1, params,
                     [basis[i][1][0], list(basis[i][1][1])],
                     [basis[j][1][0], list(basis[j][1][1])]],
                    separators=(",", ":"))
                row = global_db.execute(
                    "select m1,m2 from entries where cache_key=?", (standard_key,)).fetchone()
                if row is not None:
                    db.execute("insert into entries values (?,?,?)", (key, row[0], row[1]))
            if row is None:
                x, y = entry(support, basis[i], basis[j])
                db.execute("insert into entries values (?,?,?)", (key, str(x), str(y)))
                misses += 1
            else:
                x, y = Q(row[0]), Q(row[1]); hits += 1
            A[i][j] = A[j][i] = x; B[i][j] = B[j][i] = y
        db.commit()
        print(f"row {i+1}/{n} hits={hits} misses={misses}", file=sys.stderr, flush=True)
    db.close()
    if global_db is not None:
        global_db.close()
    return A, B, hits, misses


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--k", type=int, default=48)
    ap.add_argument("--global-degree", type=int, default=4)
    ap.add_argument("--correction-degree", type=int, default=0)
    ap.add_argument("--reference-stratum", type=int, default=0)
    ap.add_argument("--strata", help="comma-separated, default all nonempty")
    for name in ("alpha", "delta", "eta", "beta1", "beta2", "beta3plus"):
        ap.add_argument("--" + name, type=qarg, required=True)
    ap.add_argument("--cache", required=True)
    ap.add_argument("--global-cache")
    ap.add_argument("--output")
    ap.add_argument("--precision", type=int, default=180)
    ap.add_argument("--iterations", type=int, default=300)
    ap.add_argument("--rational-denominator", type=int, default=10**20)
    args = ap.parse_args()
    support = StratumSupport(args.k, args.alpha, args.delta, args.eta,
                             args.beta1, args.beta2, args.beta3plus)
    if args.strata:
        strata = sorted(set(int(x) for x in args.strata.split(",")))
    else:
        strata = [r for r in range(args.k + 1)
                   if support.canonical_support_moment_in_stratum((), 0, r) > 0]
    corr_strata = [r for r in strata if r != args.reference_stratum]
    gb = no_ones_basis(args.global_degree)
    cb = no_ones_basis(args.correction_degree)
    basis = [("G", x) for x in gb] + [("R", r, x) for r in corr_strata for x in cb]
    start = time.perf_counter(); A, B, hits, misses = matrices(
        support, basis, args.cache, args.global_cache)
    matrix_seconds = time.perf_counter() - start
    eigen, v = decimal_generalized_power(A, B, args.precision, args.iterations)
    rv = [Q(str(x)).limit_denominator(args.rational_denominator) for x in v]
    den = exact_quadratic(A, rv); num = exact_quadratic(B, rv)
    h = hashlib.sha256()
    for name, M in (("M1", A), ("M2", B)):
        h.update((name + "\n").encode())
        for row in M: h.update(("\t".join(str(x) for x in row) + "\n").encode())
    result = {
        "status": "exact-reconstructed-hybrid",
        "k": args.k,
        "parameters": {x: str(getattr(args, x)) for x in
                       ("alpha", "delta", "eta", "beta1", "beta2", "beta3plus")},
        "global_degree": args.global_degree,
        "correction_degree": args.correction_degree,
        "strata": strata,
        "reference_stratum": args.reference_stratum,
        "basis_dimension": len(basis),
        "basis": [encode(x) for x in basis],
        "matrix_sha256": h.hexdigest(),
        "matrix_seconds": matrix_seconds,
        "cache_hits": hits, "cache_misses": misses,
        "decimal_generalized_eigenvalue": str(eigen),
        "rational_vector": [str(x) for x in rv],
        "denominator_positive": den > 0,
        "exact_margin_positive": num > den,
        "exact_quotient": str(num / den),
        "exact_quotient_decimal": float(num / den),
        "exact_margin": str(num - den),
    }
    rendered = json.dumps(result, indent=2) + "\n"
    if args.output: Path(args.output).write_text(rendered, encoding="utf-8")
    print(rendered, end="")


if __name__ == "__main__":
    main()
