#!/usr/bin/env python3
"""Discovery scan of low-cardinality power-sum partition families.

Each selected partition lambda denotes the whole slack ladder
``(1-P1)^a prod_{r in lambda} p_r``, ``a+|lambda|<=D``.  The products of
power sums and monomial-orbit bases are related triangularly, so selecting a
set of partition groups defines an explicit symmetry-adapted subspace.  For a
downward-closed list in partition length the monomial-orbit labels with those
lambda give the same span, which is what this cache-based scanner uses.
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from fractions import Fraction as Q

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.abspath(os.path.join(HERE, "..", "..", "exact-integrator", "src"))
sys.path.insert(0, SRC)

from exact_integrator import decimal_generalized_power, exact_quadratic  # noqa: E402


FAMILIES = [
    [()],
    [(), (2,)],
    [(), (2,), (3,)],
    [(), (2,), (3,), (2, 2)],
    [(), (2,), (3,), (2, 2), (3, 2)],
    [(), (2,), (3,), (4,), (2, 2), (3, 2)],
    [(), (2,), (3,), (4,), (5,), (2, 2), (3, 2)],
    [(), (2,), (3,), (4,), (5,), (2, 2), (3, 2), (4, 2)],
    [(), (2,), (3,), (4,), (5,), (2, 2), (3, 2), (4, 2), (3, 3)],
    [(), (2,), (3,), (4,), (5,), (2, 2), (3, 2), (4, 2), (3, 3), (2, 2, 2)],
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("json")
    ap.add_argument("cache")
    ap.add_argument("--precision", type=int, default=180)
    ap.add_argument("--iterations", type=int, default=180)
    args = ap.parse_args()
    raw = json.load(open(args.json, encoding="utf-8"))
    labels = [(int(a), tuple(int(x) for x in lam)) for a, lam in raw["basis"]]
    params = raw["parameters"]
    cache_params = [raw["k"], params["alpha"], params["delta"], params["eta"],
                    params["beta1"], params["beta2"], params["beta3plus"]]
    n = len(labels)
    db = sqlite3.connect(args.cache)
    A = [[Q(0) for _ in range(n)] for _ in range(n)]
    B = [[Q(0) for _ in range(n)] for _ in range(n)]
    for i in range(n):
        for j in range(i + 1):
            key = json.dumps([1, cache_params,
                              [labels[i][0], list(labels[i][1])],
                              [labels[j][0], list(labels[j][1])]], separators=(",", ":"))
            row = db.execute("select m1,m2 from entries where cache_key=?", (key,)).fetchone()
            if row is None:
                raise SystemExit(f"cache miss {labels[i]} {labels[j]}")
            A[i][j] = A[j][i] = Q(row[0])
            B[i][j] = B[j][i] = Q(row[1])
    db.close()

    print("CACHE-BASED DISCOVERY; exact rational vector check follows each solve")
    for fam in FAMILIES:
        selected = [i for i, (_, lam) in enumerate(labels) if lam in fam]
        a = [[A[i][j] for j in selected] for i in selected]
        b = [[B[i][j] for j in selected] for i in selected]
        q, vector = decimal_generalized_power(a, b, args.precision, args.iterations)
        cq = [Q(str(x)).limit_denominator(10**15) for x in vector]
        den = exact_quadratic(a, cq)
        num = exact_quadratic(b, cq)
        print("dimension", len(selected), "groups", fam)
        print("decimal", q)
        print("exact", float(num / den), "den_positive", den > 0)


if __name__ == "__main__":
    main()
