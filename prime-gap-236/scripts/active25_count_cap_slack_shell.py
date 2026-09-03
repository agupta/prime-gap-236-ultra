#!/usr/bin/env python3
"""Exact search in count-tagged cap-slack polynomials on the active25 shell.

For a point with exactly ``R`` coordinates larger than ``delta``, put

    z_R = sum_{t_i>delta} (t_i-delta),
    gamma_R = B_R-R*delta.

The degree-``d`` coordinate is ``((gamma_R-z_R)/gamma_R)^d`` on the
outer shell and zero elsewhere.  These coordinates vanish towards the
count-specific cap and are therefore aligned with Definition 1 in a way that
ordinary global symmetric polynomials are not.  All I and kJ entries are
Fractions.  The floating eigensolve chooses a search vector only; the emitted
Rayleigh numerator, denominator, and margin are recomputed exactly.

This is a finite-space discovery calculation, not a theorem certificate.  It
does not contain the expensive cross block with the fixed inner polynomial.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from fractions import Fraction as Q
import hashlib
import importlib.util
import json
from math import comb, factorial
import os
from pathlib import Path
import resource
import sys
import time


FILE = Path(__file__).resolve()
REPO = FILE.parents[1]
CORE = REPO / "agents/small-delta-frontier/frontier_active25_inner_d16_tagged_shell.py"
CORE_SHA256 = "1393a2dd29e5660f10e632b19b6b5eeafe9363bf79b2cd4a8254049d1f9c669a"


def sha256(value) -> str:
    data = value if isinstance(value, bytes) else Path(value).read_bytes()
    return hashlib.sha256(data).hexdigest()


if sha256(CORE) != CORE_SHA256:
    raise RuntimeError("active25 exact core changed")
_spec = importlib.util.spec_from_file_location("active25_cap_slack_core", CORE)
if _spec is None or _spec.loader is None:
    raise ImportError(CORE)
A25 = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = A25
_spec.loader.exec_module(A25)

ei = A25.ei
GroupedEvaluator = A25.GroupedEvaluator
Q0, Q1 = Q(0), Q(1)
BRANCHES = A25.BRANCHES


def _add(left, right, scale=Q1):
    answer = defaultdict(Q)
    answer.update(left)
    for key, value in right.items():
        answer[key] += scale * value
    return {key: value for key, value in answer.items() if value}


def _scale(poly, scale):
    return {key: scale * value for key, value in poly.items() if scale * value}


def _linear_power(c0, cz, cw, power):
    return dict(ei._linear_power(c0, cz, cw, power))


def total_count(common_r: int, branch: str) -> int:
    return common_r if branch in ("Sdelta", "Stotal") else common_r + 1


def cap_slack_marginal(support, r: int, h: int, branch: str, degree: int):
    """Exact distinguished-coordinate marginal as a polynomial in (z,w)."""
    if type(degree) is not int or degree < 0:
        raise ValueError("degree must be a nonnegative integer")
    R = total_count(r, branch)
    if R == 0:
        if degree:
            return {}
        gamma = None
    else:
        gamma = support.beta(R) - R * support.delta
        if gamma <= 0:
            return {}
    u0 = (r + h) * support.delta
    if branch == "Sdelta":
        raw = {(0, 0): support.delta}
        if degree:
            raw = ei._poly_mul(raw, _linear_power(gamma, -Q1, Q0, degree))
    elif branch == "Stotal":
        raw = _linear_power(support.alpha - u0, -Q1, -Q1, 1)
        if degree:
            raw = ei._poly_mul(raw, _linear_power(gamma, -Q1, Q0, degree))
    elif branch == "Lbig":
        raw = _scale(_linear_power(gamma, -Q1, Q0, degree + 1),
                     Q(1, degree + 1))
    elif branch == "Ltotal":
        first = _linear_power(gamma, -Q1, Q0, degree + 1)
        # cap_upper-total_upper = beta(R)-alpha+h*delta+w.
        second = _linear_power(
            support.beta(R) - support.alpha + h * support.delta,
            Q0, Q1, degree + 1)
        raw = _scale(_add(first, second, -Q1), Q(1, degree + 1))
    else:
        raise ValueError(branch)
    return _scale(raw, Q1 if R == 0 else gamma ** (-degree))


def cap_slack_i_moment(support, R: int, power: int) -> Q:
    """Integral of the normalized cap slack to ``power`` in stratum R."""
    if type(R) is not int or not 0 <= R <= support.k:
        raise ValueError("invalid stratum")
    if type(power) is not int or power < 0:
        raise ValueError("invalid power")
    if R == 0:
        if power:
            return Q0
        return support.canonical_support_residual_in_stratum((), 0, 0)
    gamma = support.beta(R) - R * support.delta
    if gamma <= 0:
        return Q0
    s = support.k - R
    answer = Q0
    max_h = int(support.alpha // support.delta) - R
    for h in range(max_h + 1):
        length = support.alpha - (R + h) * support.delta
        upper = min(gamma, length)
        if upper <= 0:
            continue
        radial = Q0
        for i in range(power + 1):
            for j in range(s + 1):
                radial += (Q((-1) ** (i + j) * comb(power, i) * comb(s, j),
                             R + i + j) *
                           gamma ** (power - i) * length ** (s - j) *
                           upper ** (R + i + j))
        answer += ((-1) ** h * comb(s, h) * radial /
                   (factorial(R - 1) * factorial(s)))
    # The empty orbit has C(k,R) identical choices of the large subset.
    return Q(comb(support.k, R)) * answer / gamma ** power


def labels(max_degree: int):
    if type(max_degree) is not int or max_degree < 0:
        raise ValueError("invalid maximum degree")
    return ((0, 0),) + tuple(
        (R, degree) for R in range(1, 26) for degree in range(max_degree + 1))


def exact_i_matrix(high, low, basis):
    n = len(basis)
    matrix = [[Q0 for _ in range(n)] for _ in range(n)]
    calls = 0
    for i, (R, degree) in enumerate(basis):
        for j in range(i + 1):
            S, other_degree = basis[j]
            if R != S:
                continue
            value = (cap_slack_i_moment(high, R, degree + other_degree) -
                     cap_slack_i_moment(low, R, degree + other_degree))
            matrix[i][j] = matrix[j][i] = value
            calls += 1
    return matrix, calls


def ordered_j_matrix(left, right, basis, common_eta, *, progress=False):
    """J matrix of left-support marginals against right-support marginals."""
    if (left.k, left.delta) != (right.k, right.delta):
        raise ValueError("support geometry mismatch")
    lookup = {label: index for index, label in enumerate(basis)}
    n = len(basis)
    answer = [[Q0 for _ in range(n)] for _ in range(n)]
    dummy = GroupedEvaluator(left, [], [], Q)
    dimension = left.k - 1
    domains = 0
    integrals = 0
    max_r = min(dimension, left.max_large(), right.max_large())
    for r in range(max_r + 1):
        max_h = int(common_eta // left.delta) - r
        for h in range(max_h + 1):
            outer = common_eta - (r + h) * left.delta
            if outer <= 0:
                continue
            density = dummy.orbit_density(dimension, (), r, h, max_h)
            if not density:
                continue
            for left_branch in BRANCHES:
                lc = left._branch_constraints(r, h, left_branch)
                if lc is None:
                    continue
                R = total_count(r, left_branch)
                left_labels = [label for label in basis if label[0] == R]
                if not left_labels:
                    continue
                left_polys = {
                    label: cap_slack_marginal(
                        left, r, h, left_branch, label[1])
                    for label in left_labels
                }
                for right_branch in BRANCHES:
                    rc = right._branch_constraints(r, h, right_branch)
                    if rc is None:
                        continue
                    S = total_count(r, right_branch)
                    right_labels = [label for label in basis if label[0] == S]
                    if not right_labels:
                        continue
                    domains += 1
                    right_polys = {
                        label: cap_slack_marginal(
                            right, r, h, right_branch, label[1])
                        for label in right_labels
                    }
                    for x in left_labels:
                        if not left_polys[x]:
                            continue
                        for y in right_labels:
                            if not right_polys[y]:
                                continue
                            integrand = ei._poly_mul(
                                density, ei._poly_mul(left_polys[x], right_polys[y]))
                            answer[lookup[x]][lookup[y]] += dummy.integrate_domain(
                                integrand, dimension, r, outer, lc + rc)
                            integrals += 1
            dummy.clear_face_caches(clear_marginals=False)
        dummy.clear_radial_caches()
        if progress:
            print(f"J common-r {r}/{max_r} domains={domains} "
                  f"integrals={integrals}", flush=True)
    return answer, domains, integrals


def matrix_sum(*terms):
    n = len(terms[0][1])
    return [[sum((scale * matrix[i][j] for scale, matrix in terms), Q0)
             for j in range(n)] for i in range(n)]


def ldl(matrix):
    n = len(matrix)
    lower = [[Q0 for _ in range(n)] for _ in range(n)]
    diagonal = [Q0 for _ in range(n)]
    for i in range(n):
        lower[i][i] = Q1
        diagonal[i] = matrix[i][i] - sum(
            (lower[i][m] ** 2 * diagonal[m] for m in range(i)), Q0)
        if diagonal[i] <= 0:
            raise ArithmeticError(f"I block is not positive definite at {i}")
        for j in range(i + 1, n):
            lower[j][i] = (matrix[j][i] - sum(
                (lower[j][m] * lower[i][m] * diagonal[m]
                 for m in range(i)), Q0)) / diagonal[i]
    return lower, diagonal


def inverse_unit_lower(lower):
    n = len(lower)
    inverse = [[Q0 for _ in range(n)] for _ in range(n)]
    for column in range(n):
        inverse[column][column] = Q1
        for row in range(column + 1, n):
            inverse[row][column] = -sum(
                (lower[row][m] * inverse[m][column]
                 for m in range(column, row)), Q0)
    return inverse


def transpose(matrix):
    return [list(row) for row in zip(*matrix)]


def matmul(left, right):
    rt = transpose(right)
    return [[sum((x * y for x, y in zip(row, column)), Q0)
             for column in rt] for row in left]


def quadratic(matrix, vector):
    return sum((vector[i] * matrix[i][j] * vector[j]
                for i in range(len(vector)) for j in range(len(vector))), Q0)


def discovery_vector(a_matrix, b_matrix, denominator_limit: int):
    import numpy as np
    lower, diagonal = ldl(a_matrix)
    inverse = inverse_unit_lower(lower)
    transformed = matmul(matmul(inverse, b_matrix), transpose(inverse))
    scales = np.sqrt(np.array([float(x) for x in diagonal]))
    whitened = np.array([[float(transformed[i][j]) / scales[i] / scales[j]
                          for j in range(len(diagonal))]
                         for i in range(len(diagonal))])
    whitened = (whitened + whitened.T) / 2
    values, vectors = np.linalg.eigh(whitened)
    z = vectors[:, -1]
    y_float = z / scales
    y_float /= np.max(np.abs(y_float))
    y = [Q(float(value)).limit_denominator(denominator_limit)
         for value in y_float]
    # c = L^{-T} y.
    c = [sum((inverse[j][i] * y[j] for j in range(len(y))), Q0)
         for i in range(len(y))]
    norm = max(abs(x) for x in c)
    c = [x / norm for x in c]
    den = quadratic(a_matrix, c)
    num = quadratic(b_matrix, c)
    return {
        "binary64_discovery_root": repr(float(values[-1])),
        "denominator_limit": denominator_limit,
        "vector": c,
        "exact_denominator": den,
        "exact_numerator": num,
        "exact_margin": num - den,
        "exact_quotient": num / den,
    }


def sparse_upper(matrix):
    return [[i, j, str(matrix[i][j])]
            for i in range(len(matrix)) for j in range(i + 1)
            if matrix[i][j]]


def publish(path, payload):
    data = (json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n").encode()
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    fd = os.open(path, flags, 0o600)
    try:
        os.write(fd, data)
        os.fsync(fd)
    finally:
        os.close(fd)
    return sha256(data)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--degree", type=int, default=2)
    parser.add_argument("--denominator-limit", type=int, default=10**9)
    parser.add_argument("--output")
    parser.add_argument("--progress", action="store_true")
    args = parser.parse_args()
    if not 0 <= args.degree <= 8 or args.denominator_limit < 1:
        raise SystemExit("invalid search parameters")
    if not args.output:
        raise SystemExit("a fresh --output is required")
    started = time.monotonic()
    start_self = sha256(FILE)
    pins = A25.require_pins()
    A25.validate_analytic()
    high, low = A25.make_supports()["H"], A25.make_supports()["L"]
    basis = labels(args.degree)
    amat, i_calls = exact_i_matrix(high, low, basis)
    tables, counts = {}, {}
    for name, left, right in (("hh", high, high), ("hl", high, low),
                              ("lh", low, high), ("ll", low, low)):
        tables[name], domains, integrals = ordered_j_matrix(
            left, right, basis, A25.ETA2, progress=args.progress)
        counts[name] = {"domains": domains, "polynomial_integrals": integrals}
    jmat = matrix_sum((Q1, tables["hh"]), (-Q1, tables["hl"]),
                      (-Q1, tables["lh"]), (Q1, tables["ll"]))
    bmat = [[A25.K * value for value in row] for row in jmat]
    if amat != transpose(amat) or bmat != transpose(bmat):
        raise ArithmeticError("exact form lost symmetry")
    solution = discovery_vector(amat, bmat, args.denominator_limit)
    if sha256(FILE) != start_self or A25.require_pins() != pins:
        raise RuntimeError("source closure changed during calculation")
    payload = {
        "format": "active25-count-cap-slack-shell-exact-v1",
        "claim_scope": "exact shell-only finite forms and particular Rayleigh vector",
        "theorem_ready": False,
        "contains_inner_cross": False,
        "rigorous_matrix_entries": True,
        "rigorous_particular_vector_forms": True,
        "script_sha256": start_self,
        "core_sha256": CORE_SHA256,
        "dependency_sha256": pins,
        "parameters": {
            "k": A25.K, "delta": str(A25.DELTA),
            "alpha_high": str(A25.ALPHA2), "alpha_low": str(A25.ALPHA1),
            "eta": str(A25.ETA2), "schedule": [str(x) for x in A25.SCHEDULE],
        },
        "maximum_cap_slack_degree": args.degree,
        "basis": [list(x) for x in basis],
        "dimension": len(basis),
        "I_unique_nonzero_calls": i_calls,
        "J_work": counts,
        "I_upper_nonzero": sparse_upper(amat),
        "kJ_upper_nonzero": sparse_upper(bmat),
        "rational_vector": [str(x) for x in solution["vector"]],
        "binary64_discovery_root": solution["binary64_discovery_root"],
        "rational_denominator_limit": solution["denominator_limit"],
        "exact_denominator": str(solution["exact_denominator"]),
        "exact_numerator": str(solution["exact_numerator"]),
        "exact_margin": str(solution["exact_margin"]),
        "exact_quotient": str(solution["exact_quotient"]),
        "denominator_positive": solution["exact_denominator"] > 0,
        "margin_positive": solution["exact_margin"] > 0,
        "wall_seconds": time.monotonic() - started,
        "peak_rss_kib": int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss),
    }
    digest = publish(args.output, payload)
    print(json.dumps({
        "status": "exact shell finite-space result",
        "output_sha256": digest,
        "dimension": len(basis),
        "exact_quotient": payload["exact_quotient"],
        "margin_positive": payload["margin_positive"],
        "theorem_ready": False,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
