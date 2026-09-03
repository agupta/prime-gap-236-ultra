#!/usr/bin/env python3
"""Source-bound BV even-basis power refinement and exact vector contraction.

The matrix cache is only a performance device: keys include the exact
integrator source hash.  The generalized eigenvalue remains discovery-only;
the output's particular rational-vector quadratic forms are exact.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from decimal import Decimal, localcontext
from fractions import Fraction as Q
from pathlib import Path

HERE = Path(__file__).resolve().parent
EI_DIR = HERE.parent / "exact-integrator"
sys.path.insert(0, str(EI_DIR))
sys.path.insert(0, str(EI_DIR / "src"))

import exact_integrator as ei
import run_basis as rb


def matrix_sha(m1, m2):
    h = hashlib.sha256()
    for name, matrix in (("M1", m1), ("M2", m2)):
        h.update((name + "\n").encode())
        for row in matrix:
            h.update(("\t".join(str(x) for x in row) + "\n").encode())
    return h.hexdigest()


def resumed_power(m1, m2, seed, precision, iterations, trace_every):
    n = len(m1)
    with localcontext() as ctx:
        ctx.prec = precision
        def dec(x):
            return Decimal(x.numerator) / Decimal(x.denominator)
        scales = [dec(m1[i][i]).sqrt() for i in range(n)]
        A = [[dec(m1[i][j]) / scales[i] / scales[j] for j in range(n)]
             for i in range(n)]
        B = [[dec(m2[i][j]) / scales[i] / scales[j] for j in range(n)]
             for i in range(n)]
        LU = [row[:] for row in A]
        piv = list(range(n))
        for col in range(n):
            p = max(range(col, n), key=lambda i: abs(LU[i][col]))
            if LU[p][col] == 0:
                raise ArithmeticError("singular scaled Gram matrix")
            if p != col:
                LU[p], LU[col] = LU[col], LU[p]
                piv[p], piv[col] = piv[col], piv[p]
            pivot = LU[col][col]
            for i in range(col + 1, n):
                LU[i][col] /= pivot
                mul = LU[i][col]
                for j in range(col + 1, n):
                    LU[i][j] -= mul * LU[col][j]

        def solve(rhs):
            y = [rhs[piv[i]] for i in range(n)]
            for i in range(n):
                for j in range(i):
                    y[i] -= LU[i][j] * y[j]
            x = y[:]
            for i in range(n - 1, -1, -1):
                for j in range(i + 1, n):
                    x[i] -= LU[i][j] * x[j]
                x[i] /= LU[i][i]
            return x

        if seed is None:
            v = [Decimal(1) / Decimal(i + 1) for i in range(n)]
        else:
            if len(seed) != n:
                raise ValueError("seed length mismatch")
            # Stored vectors are in the original coordinates u=D^{-1}v.
            v = [Decimal(seed[i]) * scales[i] for i in range(n)]
        nv = max(abs(x) for x in v)
        v = [x / nv for x in v]
        trace = []
        for it in range(1, iterations + 1):
            rhs = [sum(B[i][j] * v[j] for j in range(n)) for i in range(n)]
            w = solve(rhs)
            norm = max(abs(x) for x in w)
            v = [x / norm for x in w]
            if it == iterations or (trace_every and it % trace_every == 0):
                av = [sum(A[i][j] * v[j] for j in range(n)) for i in range(n)]
                bv = [sum(B[i][j] * v[j] for j in range(n)) for i in range(n)]
                ray = sum(v[i] * bv[i] for i in range(n)) / sum(
                    v[i] * av[i] for i in range(n))
                trace.append((it, str(ray)))
        u = [v[i] / scales[i] for i in range(n)]
        norm = max(abs(x) for x in u)
        return trace, [x / norm for x in u]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run_result", type=Path)
    ap.add_argument("--cache", type=Path, required=True)
    ap.add_argument("--precision", type=int, default=140)
    ap.add_argument("--resume-iterations", type=int, default=320)
    ap.add_argument("--trace-every", type=int, default=40)
    ap.add_argument("--digits", type=int, default=35)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    result_bytes = args.run_result.read_bytes()
    old = json.loads(result_bytes)
    basis = [(int(a), tuple(lam)) for a, lam in old["basis"]]
    p = old["parameters"]
    source_path = EI_DIR / "src" / "exact_integrator.py"
    source_hash = hashlib.sha256(source_path.read_bytes()).hexdigest()
    if old["integrator_sha256"] != source_hash:
        raise ValueError("run result was produced by a different integrator source")
    support = ei.OneStratumSupport(
        int(old["k"]), Q(p["alpha"]), Q(p["delta"]), Q(p["eta"]),
        Q(p["beta1"]), Q(p["beta2"]), Q(p["beta3plus"]))
    m1, m2, hits, misses = rb.cached_matrices(
        support, basis, str(args.cache), source_hash)
    msha = matrix_sha(m1, m2)
    if msha != old["exact_matrices_sha256"]:
        raise ValueError("cache reconstruction matrix SHA mismatch")
    trace, dv = resumed_power(
        m1, m2, old.get("decimal_vector"), args.precision,
        args.resume_iterations, args.trace_every)
    vector = [Q(format(x, f".{args.digits}E")) if x else Q(0) for x in dv]
    den, num = ei.exact_quadratic(m1, vector), ei.exact_quadratic(m2, vector)
    if den <= 0:
        raise ArithmeticError("nonpositive exact denominator")
    out = {
        "format": "bv-even-exact-vector-v1",
        "k": int(old["k"]), "degree": int(old["degree"]),
        "basis": [[a, list(lam)] for a, lam in basis],
        "parameters": p,
        "integrator_sha256": source_hash,
        "run_basis_sha256": hashlib.sha256(Path(rb.__file__).read_bytes()).hexdigest(),
        "source_run_sha256": hashlib.sha256(result_bytes).hexdigest(),
        "matrix_sha256": msha,
        "cache_file_sha256": hashlib.sha256(args.cache.read_bytes()).hexdigest(),
        "cache_hits": hits, "cache_misses": misses,
        "discovery_rigorous": False,
        "particular_vector_forms_rigorous": True,
        "seed_power_eigenvalue": old["decimal_generalized_eigenvalue"],
        "resume_precision": args.precision,
        "resume_iterations": args.resume_iterations,
        "power_trace": [[i, q] for i, q in trace],
        "rationalization_significant_digits": args.digits + 1,
        "rational_vector": [str(x) for x in vector],
        "exact_denominator": str(den),
        "exact_numerator": str(num),
        "exact_quotient": str(num / den),
        "exact_margin": str(num - den),
        "denominator_positive": den > 0,
        "margin_positive": num > den,
    }
    encoded = (json.dumps(out, sort_keys=True, separators=(",", ":")) + "\n").encode()
    args.output.write_bytes(encoded)
    print("matrix", msha, "hits", hits, "misses", misses)
    print("power_trace", trace)
    print("exact_q_decimal", format(float(num / den), ".17g"))
    print("margin_sign", "positive" if num > den else "negative")
    print("sha256", hashlib.sha256(encoded).hexdigest())


if __name__ == "__main__":
    main()
