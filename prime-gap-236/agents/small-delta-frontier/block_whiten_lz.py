#!/usr/bin/env python3
"""Robust block-scaled eigendiscovery for an exact L/Z matrix.

I is block diagonal by R.  Each nonzero block is scaled by its exact diagonal
and Cholesky-whitened in Decimal arithmetic.  The resulting standard symmetric
eigenproblem is solved in float64, whose conditioning no longer contains the
tiny physical volumes or monomial Gram scales.  Repeating the Decimal
transformation at independent precisions is a discovery stability test only;
the chosen particular vector is always contracted with the original Fraction
matrices exactly.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from decimal import Decimal, localcontext
from fractions import Fraction as Q
from pathlib import Path

import numpy as np


def dec(x: Q) -> Decimal:
    return Decimal(x.numerator) / Decimal(x.denominator)


def cholesky(a):
    n = len(a)
    z = Decimal(0)
    L = [[z for _ in range(n)] for _ in range(n)]
    for i in range(n):
        for j in range(i + 1):
            v = a[i][j] - sum((L[i][u] * L[j][u] for u in range(j)), z)
            if i == j:
                if v <= 0:
                    raise ArithmeticError(f"nonpositive block Cholesky pivot {i}")
                L[i][j] = v.sqrt()
            else:
                L[i][j] = v / L[j][j]
    return L


def inverse_lower(L):
    n = len(L)
    z, one = Decimal(0), Decimal(1)
    X = [[z for _ in range(n)] for _ in range(n)]
    for col in range(n):
        for i in range(n):
            rhs = (one if i == col else z) - sum(
                (L[i][u] * X[u][col] for u in range(i)), z)
            X[i][col] = rhs / L[i][i]
    return X


def quadratic(M, c):
    return sum(c[i] * M[i][j] * c[j]
               for i in range(len(c)) for j in range(len(c)))


def qtext(x):
    return str(x.numerator) if x.denominator == 1 else f"{x.numerator}/{x.denominator}"


def solve(I, J, labels, k, precision, digits):
    n = len(labels)
    active_global = [i for i in range(n) if I[i][i] > 0]
    active_pos = {g: a for a, g in enumerate(active_global)}
    groups = {}
    for g in active_global:
        groups.setdefault(labels[g][0], []).append(g)
    # Exact block structure is part of the input invariant.
    for i in active_global:
        for j in active_global:
            if labels[i][0] != labels[j][0] and I[i][j]:
                raise ValueError("I is not R-block diagonal")
            if abs(labels[i][0] - labels[j][0]) > 1 and J[i][j]:
                raise ValueError("J is not R-block tridiagonal")

    with localcontext() as ctx:
        ctx.prec = precision
        block_data = {}
        for r, inds in groups.items():
            scales = [dec(I[i][i]).sqrt() for i in inds]
            gram = [[dec(I[i][j]) / scales[a] / scales[b]
                     for b, j in enumerate(inds)]
                    for a, i in enumerate(inds)]
            invL = inverse_lower(cholesky(gram))
            block_data[r] = (inds, scales, invL)

        N = len(active_global)
        Bp = np.zeros((N, N), dtype=np.float64)
        rs = sorted(groups)
        for r in rs:
            for s in (r, r + 1):
                if s not in groups:
                    continue
                ir, sr, xr = block_data[r]
                js, ss, xs = block_data[s]
                Bs = [[dec(k * J[i][j]) / sr[a] / ss[b]
                       for b, j in enumerate(js)]
                      for a, i in enumerate(ir)]
                # invL_r * Bs * invL_s^T.
                tmp = [[sum((xr[a][u] * Bs[u][b]
                             for u in range(len(ir))), Decimal(0))
                        for b in range(len(js))]
                       for a in range(len(ir))]
                out = [[sum((tmp[a][v] * xs[b][v]
                             for v in range(len(js))), Decimal(0))
                        for b in range(len(js))]
                       for a in range(len(ir))]
                for a, i in enumerate(ir):
                    ai = active_pos[i]
                    for b, j in enumerate(js):
                        bj = active_pos[j]
                        value = float(out[a][b])
                        Bp[ai, bj] = value
                        Bp[bj, ai] = value

        symmetry_defect = float(np.max(np.abs(Bp - Bp.T)))
        eig, vec = np.linalg.eigh((Bp + Bp.T) / 2)
        lam, y = float(eig[-1]), vec[:, -1]
        residual = float(np.max(np.abs(Bp @ y - lam * y)))

        cdec = [Decimal(0) for _ in range(n)]
        for r in rs:
            inds, scales, invL = block_data[r]
            yy = [Decimal(str(float(y[active_pos[i]]))) for i in inds]
            # c=D^{-1} L^{-T} y.
            for i, g in enumerate(inds):
                w = sum((invL[a][i] * yy[a] for a in range(len(inds))),
                        Decimal(0))
                cdec[g] = w / scales[i]
        norm = max(abs(x) for x in cdec)
        cdec = [x / norm for x in cdec]
        c = [Q(format(x, f".{digits}E")) if x else Q(0) for x in cdec]

    den = quadratic(I, c)
    jform = quadratic(J, c)
    num = k * jform
    if den <= 0:
        raise ArithmeticError("nonpositive exact I form")
    return {
        "precision": precision,
        "standard_eigenvalue": repr(lam),
        "standard_residual_inf": repr(residual),
        "symmetry_defect": repr(symmetry_defect),
        "active_dimension": len(active_global),
        "coefficients": c,
        "I_form": den,
        "J_form": jform,
        "kJ_form": num,
        "quotient": num / den,
        "I_minus_kJ": den - num,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("matrix", type=Path)
    ap.add_argument("--precisions", default="60,100")
    ap.add_argument("--digits", type=int, default=14)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    raw_bytes = args.matrix.read_bytes()
    raw = json.loads(raw_bytes)
    if raw.get("format") not in ("exact-lz-matrices-v1",
                                 "exact-lz-p2-matrices-v1"):
        raise ValueError("wrong matrix format")
    I = [[Q(x) for x in row] for row in raw["I"]]
    J = [[Q(x) for x in row] for row in raw["J"]]
    labels = [tuple(x) for x in raw["labels"]]
    k = int(raw["parameters"]["k"])
    precisions = [int(x) for x in args.precisions.split(",")]
    if len(precisions) < 2 or min(precisions) < 40:
        raise ValueError("give at least two precisions >=40")
    solves = [solve(I, J, labels, k, p, args.digits) for p in precisions]
    winner = solves[-1]
    out = {
        "format": "exact-lz-vector-v1",
        "matrix_sha256": hashlib.sha256(raw_bytes).hexdigest(),
        "k": k,
        "degree": int(raw["parameters"]["degree"]),
        "labels": [list(x) for x in labels],
        "coefficients": [qtext(x) for x in winner["coefficients"]],
        "I_form": qtext(winner["I_form"]),
        "J_form": qtext(winner["J_form"]),
        "kJ_form": qtext(winner["kJ_form"]),
        "I_minus_kJ": qtext(winner["I_minus_kJ"]),
        "quotient": qtext(winner["quotient"]),
        "eigenvalue_claim_rigorous": False,
        "particular_vector_forms_rigorous": True,
        "rationalization_significant_digits": args.digits + 1,
        "block_decimal_stability": [
            {key: (qtext(s[key]) if isinstance(s[key], Q) else s[key])
             for key in ("precision", "standard_eigenvalue",
                         "standard_residual_inf", "symmetry_defect",
                         "active_dimension", "quotient")}
            for s in solves
        ],
    }
    encoded = (json.dumps(out, sort_keys=True, separators=(",", ":")) + "\n").encode()
    args.output.write_bytes(encoded)
    for s in solves:
        print("precision", s["precision"], "eig", s["standard_eigenvalue"],
              "residual", s["standard_residual_inf"],
              "exact_q", format(float(s["quotient"]), ".17g"))
    print("wrote", args.output)
    print("sha256", hashlib.sha256(encoded).hexdigest())


if __name__ == "__main__":
    main()
