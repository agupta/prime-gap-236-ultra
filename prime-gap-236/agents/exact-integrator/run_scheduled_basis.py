#!/usr/bin/env python3
"""Build and optimize a small exact basis for an explicit B_m schedule.

This search driver reconstructs pairwise moments; its SQLite cache is only a
checkpoint.  The emitted rational vector is intended for a subsequent grouped
evaluation and the standalone pairwise checker.
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

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "src"))

import exact_integrator as ei  # noqa: E402
from verify_scheduled_fixed_vector import (  # noqa: E402
    PairwiseScheduledSupport,
    canonical_schedule_bytes,
    canonical_support_bytes,
    parse_schedule_bytes,
    sha,
)


CACHE_VERSION = 1


def cached_matrices(support, basis, schedule_sha, path):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    database = sqlite3.connect(path, timeout=300)
    database.execute("pragma busy_timeout=300000")
    database.execute("create table if not exists entries "
                     "(cache_key text primary key, m1 text not null, m2 text not null)")
    n = len(basis)
    m1 = [[Q(0) for _ in range(n)] for _ in range(n)]
    m2 = [[Q(0) for _ in range(n)] for _ in range(n)]
    hits = misses = 0
    params = [CACHE_VERSION, sha(ei.__file__), support.k,
              str(support.alpha), str(support.delta), str(support.eta),
              schedule_sha]
    for i in range(n):
        for j in range(i + 1):
            key = json.dumps([params, basis[i], basis[j]], separators=(",", ":"))
            row = database.execute(
                "select m1,m2 from entries where cache_key=?", (key,)).fetchone()
            if row is None:
                x = support.basis_m1(basis[i], basis[j])
                y = support.k * support.basis_j(basis[i], basis[j])
                database.execute("insert into entries values (?,?,?)",
                                 (key, str(x), str(y)))
                misses += 1
            else:
                x, y = Q(row[0]), Q(row[1])
                hits += 1
            m1[i][j] = m1[j][i] = x
            m2[i][j] = m2[j][i] = y
        database.commit()
        print(f"matrix row {i + 1}/{n}: hits={hits} misses={misses}",
              file=sys.stderr, flush=True)
    database.close()
    return m1, m2, hits, misses


def matrix_sha(m1, m2):
    digest = hashlib.sha256()
    for name, matrix in (("M1", m1), ("M2", m2)):
        digest.update((name + "\n").encode())
        for row in matrix:
            digest.update(("\t".join(str(x) for x in row) + "\n").encode())
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("basis_json")
    parser.add_argument("--schedule-json", required=True)
    parser.add_argument("--alpha", type=Q, required=True)
    parser.add_argument("--delta", type=Q, required=True)
    parser.add_argument("--eta", type=Q, required=True)
    parser.add_argument("--cache", required=True)
    parser.add_argument("--decimal-precision", type=int, default=120)
    parser.add_argument("--power-iterations", type=int, default=120)
    parser.add_argument("--rational-denominator", type=int, default=10**12)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    if min(args.decimal_precision, args.power_iterations,
           args.rational_denominator) <= 0:
        parser.error("precision/iterations/denominator must be positive")

    source_bytes = Path(args.basis_json).read_bytes()
    source = json.loads(source_bytes)
    k = int(source["k"])
    basis = [(int(a), tuple(int(x) for x in lam)) for a, lam in source["basis"]]
    if len(basis) != len(set(basis)):
        raise SystemExit("duplicate basis labels")
    schedule_bytes = Path(args.schedule_json).read_bytes()
    schedule = parse_schedule_bytes(schedule_bytes, k)
    schedule_sha = sha(canonical_schedule_bytes(schedule))
    support = PairwiseScheduledSupport.from_schedule(
        k, args.alpha, args.delta, args.eta, schedule)

    start = time.perf_counter()
    m1, m2, hits, misses = cached_matrices(
        support, basis, schedule_sha, args.cache)
    matrix_seconds = time.perf_counter() - start
    float_value, _ = ei.float_generalized_eigen(m1, m2)
    decimal_value, decimal_vector = ei.decimal_generalized_power(
        m1, m2, args.decimal_precision, args.power_iterations)
    rational_vector = [Q(str(x)).limit_denominator(args.rational_denominator)
                       for x in decimal_vector]
    denominator = ei.exact_quadratic(m1, rational_vector)
    numerator = ei.exact_quadratic(m2, rational_vector)
    result = {
        "status": "exact-scheduled-basis-rational-vector",
        "rigorous_forms": True,
        "eigenvector_discovery_rigorous": False,
        "k": k,
        "basis_dimension": len(basis),
        "basis": [[a, list(lam)] for a, lam in basis],
        "rational_vector": [str(x) for x in rational_vector],
        "decimal_vector": [str(x) for x in decimal_vector],
        "parameters": {"alpha": str(args.alpha), "delta": str(args.delta),
                       "eta": str(args.eta)},
        "beta_schedule": [str(x) for x in schedule],
        "extension": "constant",
        "source_basis_sha256": sha(source_bytes),
        "schedule_file_sha256": sha(schedule_bytes),
        "beta_schedule_sha256": schedule_sha,
        "support_sha256": sha(canonical_support_bytes(
            k, args.alpha, args.delta, args.eta, schedule)),
        "script_sha256": sha(__file__),
        "integrator_sha256": sha(ei.__file__),
        "pairwise_support_sha256": sha(HERE / "verify_scheduled_fixed_vector.py"),
        "matrix_sha256": matrix_sha(m1, m2),
        "matrix_seconds": matrix_seconds,
        "cache_hits": hits,
        "cache_misses": misses,
        "floating_generalized_eigenvalue": repr(float_value),
        "decimal_generalized_eigenvalue": str(decimal_value),
        "decimal_precision": args.decimal_precision,
        "power_iterations": args.power_iterations,
        "rational_denominator_limit": args.rational_denominator,
        "exact_denominator": str(denominator),
        "exact_numerator": str(numerator),
        "exact_quotient": str(numerator / denominator),
        "exact_margin": str(numerator - denominator),
        "denominator_positive": denominator > 0,
        "margin_positive": numerator > denominator,
    }
    rendered = json.dumps(result, indent=2) + "\n"
    Path(args.output).write_text(rendered)
    print(rendered, end="")


if __name__ == "__main__":
    main()
