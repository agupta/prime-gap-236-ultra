#!/usr/bin/env python3
"""Exact small Ritz extension of the frozen D18 vector inside B20.

This discovery tool reads only the entries needed for the span of the frozen
D18 vector and a consecutive block of new B20 coordinates.  It constructs the
small Gram pencil exactly, solves that pencil at high Decimal precision, and
checks the rationalized Ritz vector by exact arithmetic.  Cache entries are
not an independent certificate, so every output is explicitly non-theorem
ready and must later be reconstructed by a cache-free checker.
"""

from __future__ import annotations

import argparse
from decimal import Decimal
from fractions import Fraction as Q
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sqlite3
import sys


if hasattr(sys, "set_int_max_str_digits"):
    sys.set_int_max_str_digits(0)

FILE = Path(__file__).resolve()
REPO = FILE.parents[3]
INTEGRATOR = REPO / "agents/exact-integrator/src/exact_integrator.py"
CERT = REPO / (
    "agents/exact-integrator/results/"
    "aquarter_fullsimplex_k48_B18_refined_exact.json")
CERT_SHA256 = (
    "af6f1eb0d75bc59caf20cc82f79a3cb339be3ac7280af2afcad89eca0e31cf58")
INTEGRATOR_SHA256 = (
    "941ee82bc72fd8488a95eb5e536fe47f8c95d39a1b618dae7d6ef7eb27122e52")
CACHE_VERSION = 2
K = 48
ALPHA = Q(103, 400)
DELTA = Q(7, 250)
ETA = Q(97, 400)


def sha256(value: bytes | Path) -> str:
    data = value if isinstance(value, bytes) else value.read_bytes()
    return hashlib.sha256(data).hexdigest()


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def strict_json(data: bytes, source: Path):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError(f"duplicate key {key!r} in {source}")
            result[key] = value
        return result

    return json.loads(
        data, object_pairs_hook=pairs,
        parse_constant=lambda token: (_ for _ in ()).throw(
            ValueError(f"nonfinite JSON token {token} in {source}")))


def canonical_basis(ei, degree: int):
    basis = list(ei.even_basis(degree))
    basis.sort(key=lambda x: (
        x[0] + sum(x[1]), sum(x[1]), len(x[1]), x[1], x[0]))
    return tuple(basis)


def cache_key(basis_i, basis_j) -> str:
    params = [INTEGRATOR_SHA256, K, str(ALPHA), str(DELTA), str(ETA),
              str(ALPHA), str(ALPHA), str(ALPHA)]
    return json.dumps(
        [CACHE_VERSION, params, basis_i, basis_j], separators=(",", ":"))


def entry(db, basis_i, basis_j):
    row = db.execute(
        "select m1,m2 from entries where cache_key=?",
        (cache_key(basis_i, basis_j),)).fetchone()
    if row is None:
        raise ValueError(f"missing cache entry for {basis_i!r}, {basis_j!r}")
    return Q(row[0]), Q(row[1])


def ldl_positive(matrix):
    """Return exact no-pivot LDL pivots for a positive-definite Gram matrix."""
    n = len(matrix)
    lower = [[Q(0) for _ in range(n)] for _ in range(n)]
    pivots = []
    for i in range(n):
        lower[i][i] = Q(1)
        pivot = matrix[i][i] - sum(
            lower[i][r] * lower[i][r] * pivots[r] for r in range(i))
        if pivot <= 0:
            raise ArithmeticError(f"nonpositive exact Gram pivot {i}: {pivot}")
        pivots.append(pivot)
        for j in range(i + 1, n):
            lower[j][i] = (matrix[j][i] - sum(
                lower[j][r] * lower[i][r] * pivots[r]
                for r in range(i))) / pivot
    return tuple(pivots)


def exact_quadratic(matrix, vector):
    return sum(vector[i] * matrix[i][j] * vector[j]
               for i in range(len(vector)) for j in range(len(vector)))


def rationalize(value: Decimal, digits: int) -> Q:
    if not value.is_finite():
        raise ArithmeticError("nonfinite Decimal Ritz coefficient")
    if not value:
        return Q(0)
    return Q(format(value, f".{digits - 1}E"))


def build(cache: Path, expected_cache_sha: str, extra: int,
          precision: int, iterations: int, digits: int):
    start_self = FILE.read_bytes()
    cert_bytes = CERT.read_bytes()
    integrator_bytes = INTEGRATOR.read_bytes()
    cache_bytes = cache.read_bytes()
    if sha256(cert_bytes) != CERT_SHA256:
        raise RuntimeError("frozen D18 certificate changed")
    if sha256(integrator_bytes) != INTEGRATOR_SHA256:
        raise RuntimeError("exact integrator changed")
    if sha256(cache_bytes) != expected_cache_sha:
        raise RuntimeError("cache snapshot SHA-256 mismatch")
    if not (1 <= extra <= 236 and 80 <= precision <= 1000 and
            1 <= digits < precision and 1 <= iterations <= 10000):
        raise ValueError("invalid Ritz controls")

    ei = load_module("partial_d20_ritz_integrator_v1", INTEGRATOR)
    cert = strict_json(cert_bytes, CERT)
    basis18 = canonical_basis(ei, 18)
    basis20 = canonical_basis(ei, 20)
    frozen_basis = tuple((int(a), tuple(int(x) for x in lam))
                         for a, lam in cert.get("basis", ()))
    frozen = tuple(Q(x) for x in cert.get("rational_vector", ()))
    if (cert.get("format") != "bv-even-exact-vector-v1" or
            (cert.get("k"), cert.get("degree")) != (K, 18) or
            frozen_basis != basis18 or len(frozen) != 471 or
            basis20[:471] != basis18 or len(basis20) != 707):
        raise ValueError("frozen D18 basis/vector inventory mismatch")

    selected = basis20[471:471 + extra]
    dimension = extra + 1
    gram = [[Q(0) for _ in range(dimension)] for _ in range(dimension)]
    prime = [[Q(0) for _ in range(dimension)] for _ in range(dimension)]
    gram[0][0] = Q(cert["exact_denominator"])
    prime[0][0] = Q(cert["exact_numerator"])

    uri = f"file:{cache}?mode=ro&immutable=1"
    db = sqlite3.connect(uri, uri=True)
    try:
        for j, label in enumerate(selected, 1):
            g_cross = Q(0)
            p_cross = Q(0)
            for r, coefficient in enumerate(frozen):
                if coefficient:
                    g, p = entry(db, label, basis18[r])
                    g_cross += coefficient * g
                    p_cross += coefficient * p
            gram[0][j] = gram[j][0] = g_cross
            prime[0][j] = prime[j][0] = p_cross
            for i in range(1, j + 1):
                left = selected[j - 1]
                right = selected[i - 1]
                g, p = entry(db, left, right)
                gram[i][j] = gram[j][i] = g
                prime[i][j] = prime[j][i] = p
    finally:
        db.close()

    pivots = ldl_positive(gram)
    eigen, decimal_vector = ei.decimal_generalized_power(
        gram, prime, precision, iterations)
    ritz = tuple(rationalize(x, digits) for x in decimal_vector)
    denominator = exact_quadratic(gram, ritz)
    numerator = exact_quadratic(prime, ritz)
    if denominator <= 0:
        raise ArithmeticError("nonpositive rationalized Ritz denominator")
    full = [ritz[0] * x for x in frozen] + list(ritz[1:])
    if len(full) != 471 + extra:
        raise AssertionError("full coefficient inventory")
    if (FILE.read_bytes() != start_self or CERT.read_bytes() != cert_bytes or
            INTEGRATOR.read_bytes() != integrator_bytes or
            cache.read_bytes() != cache_bytes):
        raise RuntimeError("source closure changed during Ritz computation")
    return {
        "format": "partial-d20-small-ritz-exact-v1",
        "status": "EXACT CACHE-CONDITIONAL DISCOVERY",
        "rigorous_given_cache_entries": True,
        "cache_entries_independently_reconstructed": False,
        "theorem_ready": False,
        "never_implies": ["a cache-free exact quotient", "a capped quotient",
                          "Proposition 1", "H1<=236"],
        "k": K,
        "basis_degree": 20,
        "frozen_dimension": 471,
        "extra_dimension": extra,
        "ritz_dimension": dimension,
        "selected_labels": [[a, list(lam)] for a, lam in selected],
        "decimal_precision": precision,
        "power_iterations": iterations,
        "rationalization_significant_digits": digits,
        "decimal_generalized_eigenvalue": str(eigen),
        "ritz_vector": [str(x) for x in ritz],
        "full_vector": [str(x) for x in full],
        "exact_denominator": str(denominator),
        "exact_numerator": str(numerator),
        "exact_quotient": str(numerator / denominator),
        "exact_margin_to_one": str(numerator - denominator),
        "exact_deficit_over_denominator": str((denominator - numerator) /
                                                denominator),
        "gram_ldl_positive": True,
        "gram_ldl_pivots": [str(x) for x in pivots],
        "source_hashes": {
            str(CERT.relative_to(REPO)): CERT_SHA256,
            str(INTEGRATOR.relative_to(REPO)): INTEGRATOR_SHA256,
            str(cache): expected_cache_sha,
        },
        "checker_sha256": sha256(start_self),
    }


def canonical_json(value) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"),
                       allow_nan=False) + "\n").encode("ascii")


def publish_exclusive(path: Path, payload: bytes):
    target = path.resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o444)
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("cache", type=Path)
    parser.add_argument("--expected-cache-sha", required=True)
    parser.add_argument("--extra", type=int, default=11)
    parser.add_argument("--precision", type=int, default=300)
    parser.add_argument("--iterations", type=int, default=500)
    parser.add_argument("--digits", type=int, default=120)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = build(args.cache.resolve(), args.expected_cache_sha, args.extra,
                   args.precision, args.iterations, args.digits)
    payload = canonical_json(result)
    publish_exclusive(args.output, payload)
    print(json.dumps({
        "output_sha256": sha256(payload),
        "decimal_eigenvalue": result["decimal_generalized_eigenvalue"],
        "exact_quotient": result["exact_quotient"],
        "exact_deficit": result["exact_deficit_over_denominator"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
