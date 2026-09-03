#!/usr/bin/env python3
"""Exact BV-core plus all-small outer-band Ritz block.

This is a finite-dimensional screen for the two-band support

    band 1: 0 <= sum(t) < 103/400,
    band 2: 103/400 <= sum(t) < 521/2000.

The first coordinate is the already certified, radially corrected BV D16
function on band 1.  The remaining coordinates are

    1_band2 1_{all t_i <= 7/250} (1-sum(t))^a P_lambda(t)

for the explicit even orbit basis through ``--degree``.  All entries of the
I and 48J pencil are Fractions.  Decimal eigensolving only discovers a
particular vector, whose two forms are then contracted exactly.

The two Definition-5 cutoffs are deliberately unequal: J_11 stops at
97/400, whereas the cross and shell blocks stop at 491/2000.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import resource
import sys
import time
from collections import defaultdict
from decimal import Decimal, localcontext
from fractions import Fraction as Q
from pathlib import Path

if hasattr(sys, "set_int_max_str_digits"):
    sys.set_int_max_str_digits(0)

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
EI = REPO / "agents" / "exact-integrator"
SMALL = REPO / "agents" / "small-delta-frontier"
sys.path[:0] = [str(EI / "src"), str(EI), str(SMALL)]

import exact_integrator as ei
from bv_outer_shell_screen import cross_orbit_polynomial, integrate_residual_poly
from bv_radial_two_amplitudes import recenter_at
from robust_generalized_solve import solve_once
from run_scheduled_basis import matrix_sha
from scan_bv_epsilon_fixed import marginal_polynomial


K = 48
DELTA = Q(7, 250)
R1 = Q(103, 400)
V1 = Q(97, 400)
R2 = Q(521, 2000)
V2 = Q(491, 2000)
L0 = R1 - DELTA
L1 = R2 - DELTA


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def linear_combination(*terms):
    out = defaultdict(Q)
    for poly, scalar in terms:
        for key, value in poly.items():
            out[key] += scalar * value
    return {key: value for key, value in out.items() if value}


def fixed_delta_marginal(label):
    """Integral from t=0 to DELTA, represented in powers of 1-U."""
    a, lam = label
    out = defaultdict(Q)
    for exponent, rest in ei.OneStratumSupport.split_at_distinguished(lam, K):
        for c in range(a + 1):
            out[(a - c, rest)] += (
                Q(math.comb(a, c) * ((-1) ** c), exponent + c + 1)
                * DELTA ** (exponent + c + 1)
            )
    return {key: value for key, value in out.items() if value}


def all_small_support(dimension: int, radius: Q):
    # beta=delta makes every positive-large-count piece empty in the helper;
    # this is an integration representation, not a Definition-1 parameter.
    return ei.OneStratumSupport(
        dimension, radius, DELTA, radius, DELTA, DELTA, DELTA
    )


def integrate_upto(poly, center: Q, endpoint: Q):
    shifted = recenter_at(poly, center, endpoint)
    return integrate_residual_poly(shifted, all_small_support(K - 1, endpoint))


def integrate_interval(poly, center: Q, lower: Q, upper: Q):
    if upper <= lower:
        return Q(0)
    return integrate_upto(poly, center, upper) - integrate_upto(poly, center, lower)


def exact_ldl_pivots(matrix):
    n = len(matrix)
    lower = [[Q(int(i == j)) for j in range(n)] for i in range(n)]
    pivots = []
    for j in range(n):
        pivot = matrix[j][j] - sum(
            lower[j][h] * lower[j][h] * pivots[h] for h in range(j)
        )
        if pivot <= 0:
            raise ArithmeticError(f"nonpositive exact I pivot {j}: {pivot}")
        pivots.append(pivot)
        for i in range(j + 1, n):
            lower[i][j] = (
                matrix[i][j]
                - sum(lower[i][h] * lower[j][h] * pivots[h] for h in range(j))
            ) / pivot
    for i in range(n):
        for j in range(i + 1):
            rebuilt = sum(lower[i][h] * pivots[h] * lower[j][h]
                          for h in range(j + 1))
            if rebuilt != matrix[i][j]:
                raise ArithmeticError("exact LDL reconstruction failed")
    return pivots


def publish_exclusive(path: Path, data: bytes):
    path = path.resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    try:
        with os.fdopen(fd, "wb", closefd=True) as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
    except BaseException:
        try:
            path.unlink()
        except FileNotFoundError:
            pass
        raise


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--certificate",
        type=Path,
        default=SMALL / "bv_aquarter_B16_vector_exact.json",
    )
    parser.add_argument(
        "--radial-certificate",
        type=Path,
        default=SMALL / "bv_D16_radial_two_amplitudes_exact.json",
    )
    parser.add_argument("--degree", type=int, default=6)
    parser.add_argument("--precisions", default="160,240")
    parser.add_argument("--digits", type=int, default=70)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    precisions = [int(value) for value in args.precisions.split(",")]
    if len(precisions) < 2 or min(precisions) < 100:
        parser.error("give at least two precisions, both at least 100")
    if not 0 <= args.degree <= 16 or args.digits < 40:
        parser.error("require 0<=degree<=16 and digits>=40")

    started = time.monotonic()
    certificate_bytes = args.certificate.read_bytes()
    radial_bytes = args.radial_certificate.read_bytes()
    certificate = json.loads(certificate_bytes)
    radial = json.loads(radial_bytes)
    if certificate.get("integrator_sha256") != sha256(Path(ei.__file__)):
        raise ValueError("base certificate/integrator mismatch")
    if radial.get("certificate_sha256") != hashlib.sha256(certificate_bytes).hexdigest():
        raise ValueError("radial/base certificate mismatch")
    if (int(certificate["k"]) != K or int(radial["k"]) != K
            or Q(radial["R"]) != R1 or Q(radial["V"]) != V1):
        raise ValueError("unexpected base support")

    basis = [(int(a), tuple(int(x) for x in lam))
             for a, lam in certificate["basis"]]
    vector = [Q(value) for value in certificate["rational_vector"]]
    amplitude = Q(radial["rational_amplitudes"][1])
    base_i = Q(radial["exact_denominator"])
    base_48j = Q(radial["exact_numerator"])

    marginal_r1 = marginal_polynomial(basis, vector, K, R1)
    marginal_v1 = marginal_polynomial(basis, vector, K, V1)

    def core_low(center):
        return linear_combination(
            (recenter_at(marginal_r1, R1, center), amplitude),
            (recenter_at(marginal_v1, V1, center), 1 - amplitude),
        )

    def core_high(center):
        return linear_combination(
            (recenter_at(marginal_r1, R1, center), amplitude),
        )

    shell_basis = ei.even_basis(args.degree)
    dimension = 1 + len(shell_basis)
    m1 = [[Q(0) for _ in range(dimension)] for _ in range(dimension)]
    m2 = [[Q(0) for _ in range(dimension)] for _ in range(dimension)]
    m1[0][0] = base_i
    m2[0][0] = base_48j

    # Store each shell marginal in a center appropriate to its integration
    # interval.  Combining polynomials at different centers was a discarded
    # prototype bug; keeping the centers explicit prevents its recurrence.
    branch_a = []                 # L0 < U < L1, centered at L1
    branch_b = []                 # L1 < U < V1, centered at V1
    branch_c = []                 # V1 < U < V2, centered at V2
    for index, label in enumerate(shell_basis, 1):
        m_r1 = marginal_polynomial([label], [Q(1)], K, R1)
        m_r2 = marginal_polynomial([label], [Q(1)], K, R2)
        m_delta = fixed_delta_marginal(label)
        qa = linear_combination(
            (recenter_at(m_delta, Q(1), L1), Q(1)),
            (recenter_at(m_r1, R1, L1), Q(-1)),
        )
        qb = linear_combination(
            (recenter_at(m_r2, R2, V1), Q(1)),
            (recenter_at(m_r1, R1, V1), Q(-1)),
        )
        qc = linear_combination(
            (recenter_at(m_r2, R2, V2), Q(1)),
            (recenter_at(m_r1, R1, V2), Q(-1)),
        )
        branch_a.append(qa)
        branch_b.append(qb)
        branch_c.append(qc)
        cross_j = (
            integrate_interval(
                cross_orbit_polynomial(core_low(L1), qa), L1, L0, L1
            )
            + integrate_interval(
                cross_orbit_polynomial(core_low(V1), qb), V1, L1, V1
            )
            + integrate_interval(
                cross_orbit_polynomial(core_high(V2), qc), V2, V1, V2
            )
        )
        m2[0][index] = m2[index][0] = K * cross_j
        print(f"cross {index}/{len(shell_basis)}", file=sys.stderr, flush=True)

    # The constant shell direction has known literal marginals.  On branch A
    # it is U-L0=(R2-R1)-(L1-U); afterwards it is R2-R1.
    width = R2 - R1
    expected_a = {(0, ()): width, (1, ()): Q(-1)}
    expected_b = {(0, ()): width}
    if branch_a[0] != expected_a or branch_b[0] != expected_b \
            or branch_c[0] != expected_b:
        raise AssertionError("constant shell marginal regression failed")

    support_r2 = all_small_support(K, R2)
    support_r1 = all_small_support(K, R1)
    for i, left in enumerate(shell_basis):
        for j in range(i + 1):
            right = shell_basis[j]
            denominator = (
                support_r2.basis_m1(left, right)
                - support_r1.basis_m1(left, right)
            )
            marginal_form = (
                integrate_interval(
                    cross_orbit_polynomial(branch_a[i], branch_a[j]),
                    L1, L0, L1,
                )
                + integrate_interval(
                    cross_orbit_polynomial(branch_c[i], branch_c[j]),
                    V2, L1, V2,
                )
            )
            m1[i + 1][j + 1] = m1[j + 1][i + 1] = denominator
            m2[i + 1][j + 1] = m2[j + 1][i + 1] = K * marginal_form
        print(f"row {i + 1}/{len(shell_basis)}", file=sys.stderr, flush=True)

    if any(m1[0][j] for j in range(1, dimension)):
        raise AssertionError("disjoint-band I cross block is not zero")
    shell_volume = (
        support_r2.canonical_support_residual((), 0)
        - support_r1.canonical_support_residual((), 0)
    )
    if m1[1][1] != shell_volume:
        raise AssertionError("constant shell volume regression failed")
    pivots = exact_ldl_pivots(m1)

    solves = [solve_once(m1, m2, precision) for precision in precisions]
    winner = solves[-1]
    with localcontext() as context:
        context.prec = max(precisions) + 30
        rational_vector = [
            Q(format(Decimal(value), f".{args.digits}E"))
            for value in winner["vector"]
        ]
    exact_i = ei.exact_quadratic(m1, rational_vector)
    exact_48j = ei.exact_quadratic(m2, rational_vector)
    if exact_i <= 0:
        raise ArithmeticError("rationalized vector has nonpositive I")

    result = {
        "format": "two-band-bv-radial-D16-plus-r0-shell-even-block-exact-v1",
        "claim_scope": (
            "Every matrix entry and the emitted vector forms are exact; the "
            "largest-root claim is Decimal discovery only. The two-band "
            "equidistribution theorem is a separate analytic obligation."
        ),
        "k": K,
        "parameters": {
            "delta": str(DELTA), "R1": str(R1), "V1": str(V1),
            "R2": str(R2), "V2": str(V2),
        },
        "shell_condition": "band 2 and every coordinate <= delta",
        "shell_degree": args.degree,
        "basis_dimension": dimension,
        "shell_basis": [[a, list(lam)] for a, lam in shell_basis],
        "certificate_sha256": hashlib.sha256(certificate_bytes).hexdigest(),
        "radial_certificate_sha256": hashlib.sha256(radial_bytes).hexdigest(),
        "integrator_sha256": sha256(Path(ei.__file__)),
        "script_sha256": sha256(Path(__file__)),
        "solver_sha256": sha256(EI / "robust_generalized_solve.py"),
        "matrix_sha256": matrix_sha(m1, m2),
        "exact_I_LDL_positive": True,
        "exact_I_LDL_pivots": [str(value) for value in pivots],
        "base_exact_quotient": str(base_48j / base_i),
        "cross_precision_solves": solves,
        "rational_significant_digits": args.digits + 1,
        "rational_vector": [str(value) for value in rational_vector],
        "exact_denominator": str(exact_i),
        "exact_numerator": str(exact_48j),
        "exact_quotient": str(exact_48j / exact_i),
        "exact_gain": str(exact_48j / exact_i - base_48j / base_i),
        "exact_margin": str(exact_48j - exact_i),
        "denominator_positive": exact_i > 0,
        "margin_positive": exact_48j > exact_i,
        "total_seconds": time.monotonic() - started,
        "peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
    }
    encoded = (json.dumps(result, sort_keys=True, separators=(",", ":")) + "\n").encode()
    publish_exclusive(args.output, encoded)
    print(json.dumps({
        "matrix_sha256": result["matrix_sha256"],
        "exact_quotient": result["exact_quotient"],
        "exact_gain": result["exact_gain"],
        "margin_positive": result["margin_positive"],
        "total_seconds": result["total_seconds"],
        "peak_rss_kib": result["peak_rss_kib"],
        "artifact_sha256": hashlib.sha256(encoded).hexdigest(),
    }, indent=2))


if __name__ == "__main__":
    main()
