#!/usr/bin/env python3
"""Build a small exact B_D matrix and print a discovery eigenvalue.

This is a benchmark/search driver, not a certificate generator.  The matrices are
always reconstructed from the recurrence in src/exact_integrator.py.
"""

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
    # Exact certificate margins at D>=12 routinely contain more than 4300 digits.
    sys.set_int_max_str_digits(0)

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from exact_integrator import (OneStratumSupport, decimal_generalized_power,
                              even_basis, exact_quadratic, float_generalized_eigen,
                              no_ones_basis)

MOMENT_CACHE_VERSION = 2


def rational_arg(text: str) -> Fraction:
    return Fraction(text)


def cached_matrices(support, basis, path, source_hash):
    """Persistent experiment cache; entries remain reconstructible from source.

    The cache is not a certificate and is never trusted by the standalone tests.
    Its only purpose is to avoid recomputing the exact B_D principal submatrix
    when extending a basis greedily.
    """
    os.makedirs(os.path.dirname(path), exist_ok=True)
    db = sqlite3.connect(path, timeout=300)
    db.execute("pragma busy_timeout=300000")
    db.execute("create table if not exists entries "
               "(cache_key text primary key, m1 text not null, m2 text not null)")
    n = len(basis)
    m1 = [[Fraction(0) for _ in range(n)] for _ in range(n)]
    m2 = [[Fraction(0) for _ in range(n)] for _ in range(n)]
    hits = misses = 0
    last_commit = time.monotonic()
    # Bind cached moments to the implementation that generated them.  Version
    # 1 omitted this field, so a later integrator repair could silently reuse
    # stale entries with identical geometric parameters.
    params = [source_hash, support.k,
              str(support.alpha), str(support.delta), str(support.eta),
              str(support.beta1), str(support.beta2), str(support.beta3plus)]
    for i in range(n):
        for j in range(i + 1):
            key = json.dumps([MOMENT_CACHE_VERSION, params, basis[i], basis[j]],
                             separators=(",", ":"))
            row = db.execute("select m1,m2 from entries where cache_key=?", (key,)).fetchone()
            if row is None:
                x = support.basis_m1(basis[i], basis[j])
                y = support.k * support.basis_j(basis[i], basis[j])
                db.execute("insert into entries values (?,?,?)", (key, str(x), str(y)))
                misses += 1
                # Generic capped-support entries can each take minutes, while
                # full-simplex entries take milliseconds.  A time-based
                # checkpoint retains expensive rows without imposing thousands
                # of fsyncs on the fast path.
                if time.monotonic() - last_commit >= 5:
                    db.commit()
                    last_commit = time.monotonic()
            else:
                x, y = Fraction(row[0]), Fraction(row[1])
                hits += 1
            m1[i][j] = m1[j][i] = x
            m2[i][j] = m2[j][i] = y
        db.commit()
        print(f"matrix row {i + 1}/{n}: hits={hits} misses={misses}",
              file=sys.stderr, flush=True)
    db.close()
    return m1, m2, hits, misses


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--k", type=int, default=48)
    ap.add_argument("--degree", type=int, default=3)
    ap.add_argument("--max-length", type=int)
    ap.add_argument("--family", choices=("full", "no-ones", "core", "b4-total", "b4-core", "edges"),
                    default="full")
    ap.add_argument("--basis-json",
                    help="JSON file containing an explicit list of [a,[lambda parts]] labels; "
                         "overrides --degree/--family/--max-length")
    ap.add_argument("--include-label", action="append", default=[], metavar="A:PARTS",
                    help="append a basis label, e.g. 0:3,3 or 7: for (1-P1)^7")
    ap.add_argument("--limit", type=int, help="use only the first N graded basis functions")
    ap.add_argument("--rational-denominator", type=int, default=1_000_000)
    ap.add_argument("--decimal-precision", type=int, default=100)
    ap.add_argument("--power-iterations", type=int, default=80)
    ap.add_argument("--cache", default=os.path.join(os.path.dirname(__file__),
                                                    "cache", "matrix_entries.sqlite3"))
    ap.add_argument("--no-cache", action="store_true")
    ap.add_argument("--output", help="also write the complete JSON result to this path")
    ap.add_argument("--alpha", type=rational_arg, default=Fraction(521, 2000))
    ap.add_argument("--delta", type=rational_arg, default=Fraction(7, 250))
    ap.add_argument("--eta", type=rational_arg, default=Fraction(491, 2000))
    ap.add_argument("--beta1", type=rational_arg, default=Fraction(3, 20))
    ap.add_argument("--beta2", type=rational_arg, default=Fraction(3, 20))
    ap.add_argument("--beta3plus", type=rational_arg, default=Fraction(17, 100))
    args = ap.parse_args()

    full = even_basis(args.degree, args.max_length)
    if args.basis_json:
        with open(args.basis_json, encoding="utf-8") as stream:
            raw_basis = json.load(stream)
        basis = []
        for label in raw_basis:
            if (not isinstance(label, list) or len(label) != 2 or
                    not isinstance(label[0], int) or label[0] < 0 or
                    not isinstance(label[1], list) or
                    any(not isinstance(x, int) or x <= 0 for x in label[1])):
                ap.error(f"malformed basis label {label!r}")
            basis.append((label[0], tuple(label[1])))
        if len(basis) != len(set(basis)):
            ap.error("basis contains duplicate labels")
    elif args.family == "full":
        basis = full
    elif args.family == "no-ones":
        basis = no_ones_basis(args.degree, args.max_length)
    elif args.family == "core":
        basis = [x for x in full if x[1] in ((), (2,))]
    elif args.family == "b4-total":
        basis = list({*even_basis(min(4, args.degree)),
                      *((a, ()) for a in range(args.degree + 1))})
    elif args.family == "b4-core":
        basis = list({*even_basis(min(4, args.degree)),
                      *((a, ()) for a in range(args.degree + 1)),
                      *((a, (2,)) for a in range(max(0, args.degree - 1)))})
    else:
        basis_set = set(even_basis(min(4, args.degree)))
        for d in range(5, args.degree + 1):
            basis_set.add((d, ()))
            basis_set.add((d - 2, (2,)))
            basis_set.add((0, (2 * (d // 2),)))
            if d % 2 == 0:
                basis_set.add((0, (2,) * (d // 2)))
        basis = list(basis_set)
    for text in args.include_label:
        try:
            left, right = text.split(":", 1)
            label = (int(left), tuple(int(x) for x in right.split(",") if x))
        except ValueError:
            ap.error(f"malformed --include-label {text!r}")
        if label[0] < 0 or any(x <= 0 for x in label[1]):
            ap.error(f"malformed --include-label {text!r}")
        basis.append(label)
    if len(basis) != len(set(basis)):
        ap.error("basis contains duplicate labels")
    basis.sort(key=lambda x: (x[0] + sum(x[1]), sum(x[1]), len(x[1]), x[1], x[0]))
    if args.limit is not None:
        basis = basis[:args.limit]
    support = OneStratumSupport(args.k, args.alpha, args.delta, args.eta,
                                args.beta1, args.beta2, args.beta3plus)
    # Bind provenance before a potentially hours-long build.  Reading the hash
    # only at the end would mislabel a run if the source were edited while the
    # already-imported module was still computing.
    source_path = os.path.join(os.path.dirname(__file__), "src", "exact_integrator.py")
    source_hash = hashlib.sha256(open(source_path, "rb").read()).hexdigest()
    start = time.perf_counter()
    if args.no_cache:
        m1, m2 = support.matrices(basis)
        cache_hits, cache_misses = 0, len(basis) * (len(basis) + 1) // 2
    else:
        m1, m2, cache_hits, cache_misses = cached_matrices(
            support, basis, args.cache, source_hash)
    exact_seconds = time.perf_counter() - start
    float_eigenvalue, float_vector = float_generalized_eigen(m1, m2)
    decimal_eigenvalue, decimal_vector = decimal_generalized_power(
        m1, m2, args.decimal_precision, args.power_iterations)
    rational_vector = [Fraction(x).limit_denominator(args.rational_denominator)
                       for x in decimal_vector]
    denominator = exact_quadratic(m1, rational_vector)
    numerator = exact_quadratic(m2, rational_vector)
    exact_margin = numerator - denominator
    mh = hashlib.sha256()
    for name, matrix in (("M1", m1), ("M2", m2)):
        mh.update((name + "\n").encode())
        for row in matrix:
            mh.update(("\t".join(str(x) for x in row) + "\n").encode())
    result = {
        "k": args.k,
        "degree": args.degree,
        "basis_dimension": len(basis),
        "basis": basis,
        "parameters": {"alpha": str(args.alpha), "delta": str(args.delta),
                       "eta": str(args.eta), "beta1": str(args.beta1),
                       "beta2": str(args.beta2), "beta3plus": str(args.beta3plus)},
        "integrator_sha256": source_hash,
        "exact_matrices_sha256": mh.hexdigest(),
        "exact_matrix_seconds": exact_seconds,
        "cache_hits": cache_hits,
        "cache_misses": cache_misses,
        "floating_generalized_eigenvalue": float_eigenvalue,
        "decimal_generalized_eigenvalue": str(decimal_eigenvalue),
        "rigorous": True,
        "decimal_vector": [str(x) for x in decimal_vector],
        "rational_vector": [str(x) for x in rational_vector],
        "exact_denominator_positive": denominator > 0,
        "exact_margin_positive": exact_margin > 0,
        "exact_quadratic_denominator": str(denominator),
        "exact_quadratic_numerator": str(numerator),
        "exact_quotient": str(numerator / denominator),
        "exact_quotient_decimal": float(numerator / denominator),
        "exact_margin": str(exact_margin),
    }
    rendered = json.dumps(result, indent=2) + "\n"
    if args.output:
        directory = os.path.dirname(args.output)
        if directory:
            os.makedirs(directory, exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(rendered)
    print(rendered, end="")


if __name__ == "__main__":
    main()
