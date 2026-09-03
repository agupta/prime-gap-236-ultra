#!/usr/bin/env python3
"""Backward-prune a certified rational vector by whole orbit families.

This is a discovery compressor.  It reads a reconstructible-result JSON and a
SQLite moment cache, then greedily removes all slack powers belonging to one
partition lambda at a time.  The cache is never evidence for a theorem; the
printed finite label/vector pair must be reconstructed by the exact integrator.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
from decimal import Decimal, localcontext
from fractions import Fraction as Q
from pathlib import Path


def dec(x: Q) -> Decimal:
    return Decimal(x.numerator) / Decimal(x.denominator)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("json")
    ap.add_argument("cache")
    ap.add_argument("--minimum-dimension", type=int, default=20)
    ap.add_argument("--output")
    args = ap.parse_args()

    source = json.load(open(args.json, encoding="utf-8"))
    labels = [(int(a), tuple(int(x) for x in lam)) for a, lam in source["basis"]]
    coeff = [Q(x) for x in source["rational_vector"]]
    params = source["parameters"]
    cache_params = [source["k"], params["alpha"], params["delta"], params["eta"],
                    params["beta1"], params["beta2"], params["beta3plus"]]
    db = sqlite3.connect(args.cache)

    n = len(labels)
    A = [[Q(0) for _ in range(n)] for _ in range(n)]
    B = [[Q(0) for _ in range(n)] for _ in range(n)]
    for i in range(n):
        for j in range(i + 1):
            key = json.dumps([1, cache_params,
                              [labels[i][0], list(labels[i][1])],
                              [labels[j][0], list(labels[j][1])]], separators=(",", ":"))
            row = db.execute("select m1,m2 from entries where cache_key=?", (key,)).fetchone()
            if row is None:
                raise SystemExit(f"cache miss for {labels[i]} {labels[j]}")
            A[i][j] = A[j][i] = Q(row[0])
            B[i][j] = B[j][i] = Q(row[1])
    db.close()

    with localcontext() as ctx:
        ctx.prec = 100
        # Store full ordered quadratic contributions, so a kept-set quotient is
        # just a stable Decimal sum.  The final checkpoint is recomputed exactly.
        ca = [[dec(coeff[i] * A[i][j] * coeff[j]) for j in range(n)] for i in range(n)]
        cb = [[dec(coeff[i] * B[i][j] * coeff[j]) for j in range(n)] for i in range(n)]

        kept = set(range(n))
        groups = {lam: {i for i, (_, x) in enumerate(labels) if x == lam}
                  for _, lam in labels}
        trace = []

        def quotient(indices) -> Decimal:
            den = sum(ca[i][j] for i in indices for j in indices)
            num = sum(cb[i][j] for i in indices for j in indices)
            if den <= 0:
                return Decimal("-Infinity")
            return num / den

        print("CACHE-BASED DISCOVERY ONLY")
        print("initial", n, quotient(kept))
        while groups and len(kept) > args.minimum_dimension:
            options = []
            for lam, members in groups.items():
                trial = kept - members
                if len(trial) < args.minimum_dimension:
                    continue
                options.append((quotient(trial), -len(members), lam, trial))
            if not options:
                break
            q, negsize, lam, trial = max(options)
            removed = sorted(kept - trial)
            kept = trial
            del groups[lam]
            row = {"dimension": len(kept), "quotient_fixed_vector": str(q),
                   "removed_partition": list(lam), "removed_count": len(removed)}
            trace.append(row)
            print(len(kept), q, "removed", lam, len(removed))

        chosen = sorted(kept)
        den = sum(coeff[i] * A[i][j] * coeff[j] for i in chosen for j in chosen)
        num = sum(coeff[i] * B[i][j] * coeff[j] for i in chosen for j in chosen)
        result = {
            "status": "discovery-cache-only",
            "source_json": args.json,
            "source_matrix_sha256": source["exact_matrices_sha256"],
            "basis": [[labels[i][0], list(labels[i][1])] for i in chosen],
            "rational_vector": [str(coeff[i]) for i in chosen],
            "dimension": len(chosen),
            "exact_cached_quotient": str(num / den),
            "exact_cached_quotient_decimal": float(num / den),
            "denominator_positive": den > 0,
            "trace": trace,
        }
        if args.output:
            Path(args.output).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        print("final exact cached quotient", num / den, float(num / den))


if __name__ == "__main__":
    main()
