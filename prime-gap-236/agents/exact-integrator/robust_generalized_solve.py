#!/usr/bin/env python3
"""Robust high-precision discovery solve for a cached exact scheduled pencil.

This does not certify an eigenvalue.  It reconstructs the exact rational
matrices, performs a symmetric Decimal Cholesky reduction followed by a
Jacobi eigendecomposition at two precisions, rationalizes the selected vector,
and certifies only that particular vector's two quadratic forms exactly.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from decimal import Decimal, localcontext
from fractions import Fraction as Q
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "src"))

import exact_integrator as ei
from run_scheduled_basis import cached_matrices, matrix_sha
from verify_scheduled_fixed_vector import (
    PairwiseScheduledSupport,
    canonical_schedule_bytes,
    parse_schedule_bytes,
    sha,
)


def dec(value):
    return Decimal(value.numerator) / Decimal(value.denominator)


def matmul(left, right):
    rows, inner, columns = len(left), len(right), len(right[0])
    if not rows or len(left[0]) != inner:
        raise ValueError("matrix dimension mismatch")
    zero = Decimal(0)
    return [[sum((left[i][k] * right[k][j] for k in range(inner)), zero)
             for j in range(columns)] for i in range(rows)]


def transpose(matrix):
    return [list(row) for row in zip(*matrix)]


def cholesky(matrix):
    n = len(matrix)
    zero = Decimal(0)
    lower = [[zero for _ in range(n)] for _ in range(n)]
    for i in range(n):
        for j in range(i + 1):
            value = matrix[i][j] - sum(
                (lower[i][k] * lower[j][k] for k in range(j)), zero)
            if i == j:
                if value <= 0:
                    raise ArithmeticError(
                        f"scaled Gram Cholesky pivot {i} is not positive")
                lower[i][j] = value.sqrt()
            else:
                lower[i][j] = value / lower[j][j]
    return lower


def inverse_lower(lower):
    n = len(lower)
    zero, one = Decimal(0), Decimal(1)
    inverse = [[zero for _ in range(n)] for _ in range(n)]
    for column in range(n):
        for i in range(n):
            rhs = one if i == column else zero
            rhs -= sum((lower[i][k] * inverse[k][column]
                        for k in range(i)), zero)
            inverse[i][column] = rhs / lower[i][i]
    return inverse


def jacobi_symmetric(matrix, precision):
    """All eigenpairs of a real symmetric Decimal matrix."""
    n = len(matrix)
    a = [list(row) for row in matrix]
    zero, one = Decimal(0), Decimal(1)
    vectors = [[one if i == j else zero for j in range(n)]
               for i in range(n)]
    tolerance = Decimal(10) ** (-(precision - 30))
    max_rotations = 20000 * max(1, n)
    for rotation in range(max_rotations):
        p, q, largest = 0, 1, abs(a[0][1]) if n > 1 else zero
        for i in range(n):
            for j in range(i):
                candidate = abs(a[i][j])
                if candidate > largest:
                    p, q, largest = j, i, candidate
        scale = max(one, max(abs(a[i][i]) for i in range(n)))
        if largest <= tolerance * scale:
            return [a[i][i] for i in range(n)], vectors, rotation
        apq, app, aqq = a[p][q], a[p][p], a[q][q]
        tau = (aqq - app) / (2 * apq)
        sign = one if tau >= 0 else -one
        t = sign / (abs(tau) + (one + tau * tau).sqrt())
        c = one / (one + t * t).sqrt()
        s = t * c
        for k in range(n):
            if k == p or k == q:
                continue
            akp, akq = a[k][p], a[k][q]
            a[k][p] = a[p][k] = c * akp - s * akq
            a[k][q] = a[q][k] = s * akp + c * akq
        a[p][p] = app - t * apq
        a[q][q] = aqq + t * apq
        a[p][q] = a[q][p] = zero
        for k in range(n):
            vkp, vkq = vectors[k][p], vectors[k][q]
            vectors[k][p] = c * vkp - s * vkq
            vectors[k][q] = s * vkp + c * vkq
    raise ArithmeticError("Jacobi eigensolver did not converge")


def dot(left, right):
    return sum((x * y for x, y in zip(left, right)), Decimal(0))


def matvec(matrix, vector):
    return [dot(row, vector) for row in matrix]


def solve_once(m1, m2, precision):
    with localcontext() as context:
        context.prec = precision
        a = [[dec(x) for x in row] for row in m1]
        b = [[dec(x) for x in row] for row in m2]
        scales = [a[i][i].sqrt() for i in range(len(a))]
        if any(x <= 0 for x in scales):
            raise ArithmeticError("nonpositive exact Gram diagonal")
        scaled_a = [[a[i][j] / scales[i] / scales[j]
                     for j in range(len(a))] for i in range(len(a))]
        scaled_b = [[b[i][j] / scales[i] / scales[j]
                     for j in range(len(a))] for i in range(len(a))]
        lower = cholesky(scaled_a)
        inverse = inverse_lower(lower)
        reduced = matmul(matmul(inverse, scaled_b), transpose(inverse))
        # Roundoff from the two matrix products is symmetrized explicitly.
        reduced = [[(reduced[i][j] + reduced[j][i]) / 2
                    for j in range(len(a))] for i in range(len(a))]
        values, vectors, rotations = jacobi_symmetric(reduced, precision)
        index = max(range(len(values)), key=values.__getitem__)
        eigenvector = [vectors[i][index] for i in range(len(a))]
        # w=L^{-T}y = (L^{-1})^T y; v=D^{-1}w.
        w = matvec(transpose(inverse), eigenvector)
        vector = [w[i] / scales[i] for i in range(len(a))]
        normalization = max(abs(x) for x in vector)
        vector = [x / normalization for x in vector]
        av, bv = matvec(a, vector), matvec(b, vector)
        quotient = dot(vector, bv) / dot(vector, av)
        residual = max(abs(bv[i] - quotient * av[i])
                       for i in range(len(a)))
        residual_scale = max(Decimal(1), max(abs(x) for x in bv),
                             abs(quotient) * max(abs(x) for x in av))
        return {
            "precision": precision,
            "eigenvalue": str(values[index]),
            "rayleigh_quotient": str(quotient),
            "relative_residual_bound": str(residual / residual_scale),
            "jacobi_rotations": rotations,
            "vector": [str(x) for x in vector],
        }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("basis_json")
    parser.add_argument("--schedule-json", required=True)
    parser.add_argument("--alpha", type=Q, required=True)
    parser.add_argument("--delta", type=Q, required=True)
    parser.add_argument("--eta", type=Q, required=True)
    parser.add_argument("--cache", required=True)
    parser.add_argument("--precisions", default="160,240")
    parser.add_argument("--rational-denominator", type=int, default=10**15)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    precisions = [int(x) for x in args.precisions.split(",")]
    if len(precisions) < 2 or min(precisions) < 80:
        parser.error("give at least two comma-separated precisions >=80")
    raw_bytes = Path(args.basis_json).read_bytes()
    raw = json.loads(raw_bytes)
    basis = [(int(a), tuple(int(x) for x in lam))
             for a, lam in raw["basis"]]
    schedule_bytes = Path(args.schedule_json).read_bytes()
    schedule = parse_schedule_bytes(schedule_bytes, int(raw["k"]))
    schedule_sha = sha(canonical_schedule_bytes(schedule))
    support = PairwiseScheduledSupport.from_schedule(
        int(raw["k"]), args.alpha, args.delta, args.eta, schedule)
    m1, m2, hits, misses = cached_matrices(
        support, basis, schedule_sha, args.cache)
    solves = [solve_once(m1, m2, precision) for precision in precisions]
    winner = solves[-1]
    vector = [Q(x).limit_denominator(args.rational_denominator)
              for x in winner["vector"]]
    denominator = ei.exact_quadratic(m1, vector)
    numerator = ei.exact_quadratic(m2, vector)
    result = {
        "status": "robust-decimal-discovery-exact-rational-vector",
        "eigenvalue_claim_rigorous": False,
        "particular_vector_forms_rigorous": True,
        "k": int(raw["k"]),
        "basis": [[a, list(lam)] for a, lam in basis],
        "basis_dimension": len(basis),
        "parameters": {"alpha": str(args.alpha), "delta": str(args.delta),
                       "eta": str(args.eta)},
        "beta_schedule": [str(x) for x in schedule],
        "source_basis_sha256": hashlib.sha256(raw_bytes).hexdigest(),
        "schedule_file_sha256": hashlib.sha256(schedule_bytes).hexdigest(),
        "script_sha256": sha(__file__),
        "integrator_sha256": sha(ei.__file__),
        "matrix_sha256": matrix_sha(m1, m2),
        "cache_hits": hits,
        "cache_misses": misses,
        "cross_precision_solves": solves,
        "rational_denominator_limit": args.rational_denominator,
        "rational_vector": [str(x) for x in vector],
        "exact_denominator": str(denominator),
        "exact_numerator": str(numerator),
        "exact_quotient": str(numerator / denominator),
        "exact_margin": str(numerator - denominator),
        "denominator_positive": denominator > 0,
        "margin_positive": numerator > denominator,
    }
    Path(args.output).write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({key: result[key] for key in (
        "matrix_sha256", "exact_quotient", "exact_margin",
        "denominator_positive", "margin_positive")}, indent=2))
    for solve in solves:
        print(json.dumps({key: solve[key] for key in (
            "precision", "rayleigh_quotient", "relative_residual_bound",
            "jacobi_rotations")}, indent=2))


if __name__ == "__main__":
    main()
