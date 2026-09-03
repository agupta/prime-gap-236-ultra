#!/usr/bin/env python3
"""Greedy discovery of high-leverage orbit/slack ladders from an exact cache."""

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
from exact_integrator import decimal_generalized_power, exact_quadratic  # noqa:E402


SEED = [(), (2,), (3,), (4,), (5,), (2, 2), (3, 2), (4, 2),
        (3, 3), (2, 2, 2)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("json")
    ap.add_argument("cache")
    ap.add_argument("--rounds", type=int, default=8)
    ap.add_argument("--precision", type=int, default=130)
    ap.add_argument("--iterations", type=int, default=140)
    args = ap.parse_args()
    raw = json.load(open(args.json, encoding="utf-8"))
    labels = [(int(a), tuple(int(x) for x in lam)) for a, lam in raw["basis"]]
    p = raw["parameters"]
    cp = [raw["k"], p["alpha"], p["delta"], p["eta"],
          p["beta1"], p["beta2"], p["beta3plus"]]
    n = len(labels)
    db = sqlite3.connect(args.cache)
    A = [[Q(0) for _ in range(n)] for _ in range(n)]
    B = [[Q(0) for _ in range(n)] for _ in range(n)]
    for i in range(n):
        for j in range(i + 1):
            key = json.dumps([1, cp, [labels[i][0], list(labels[i][1])],
                              [labels[j][0], list(labels[j][1])]], separators=(",", ":"))
            row = db.execute("select m1,m2 from entries where cache_key=?", (key,)).fetchone()
            if row is None:
                raise SystemExit(f"cache miss {labels[i]} {labels[j]}")
            A[i][j] = A[j][i] = Q(row[0]); B[i][j] = B[j][i] = Q(row[1])
    db.close()
    all_groups = sorted({lam for _, lam in labels}, key=lambda x: (sum(x), len(x), x))
    active = [x for x in SEED if x in all_groups]

    def solve(groups, rational=False):
        ind = [i for i, (_, lam) in enumerate(labels) if lam in groups]
        a = [[A[i][j] for j in ind] for i in ind]
        b = [[B[i][j] for j in ind] for i in ind]
        q, v = decimal_generalized_power(a, b, args.precision, args.iterations)
        if not rational:
            return q, len(ind), None
        c = [Q(str(x)).limit_denominator(10**15) for x in v]
        exact = exact_quadratic(b, c) / exact_quadratic(a, c)
        return q, len(ind), exact

    q, dim, exact = solve(active, True)
    print("CACHE DISCOVERY ONLY")
    print("seed", active, "dimension", dim, "decimal", q, "exact", float(exact))
    for rnd in range(args.rounds):
        candidates = []
        for g in all_groups:
            if g in active:
                continue
            qg, dg, _ = solve(active + [g])
            candidates.append((qg, -dg, g, dg))
        q, _, winner, dim = max(candidates)
        active.append(winner)
        q, dim, exact = solve(active, True)
        print("round", rnd + 1, "added", winner, "dimension", dim,
              "decimal", q, "exact", float(exact), flush=True)
    print("groups", active)


if __name__ == "__main__":
    main()
