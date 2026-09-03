#!/usr/bin/env python3
"""Exact D16-global plus outer-shell even-basis block on direct BV support.

The first basis vector is the certified global D16 polynomial F0.  The
remaining vectors are

    1_{V < sum(t) < R} (1-P1)^a P_lambda

for every label in ``even_basis(degree)``.  Both quadratic-form matrices are
reconstructed from exact Fraction moments.  Decimal whitening/Jacobi is only
used to discover a vector; the emitted particular-vector forms are contracted
exactly.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from decimal import Decimal, localcontext
from fractions import Fraction as Q
from pathlib import Path

if hasattr(sys, "set_int_max_str_digits"):
    sys.set_int_max_str_digits(0)

HERE = Path(__file__).resolve().parent
EI_DIR = HERE.parent / "exact-integrator"
sys.path.insert(0, str(EI_DIR / "src"))
sys.path.insert(0, str(EI_DIR))
sys.path.insert(0, str(HERE))

import exact_integrator as ei
from bv_outer_shell_screen import (
    cross_orbit_polynomial,
    integrate_residual_poly,
    marginal_polynomial,
    recenter_at,
    square_orbit_polynomial,
    subtract,
)
from robust_generalized_solve import solve_once
from run_scheduled_basis import matrix_sha


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def exact_forms(m1, m2, vector):
    return ei.exact_quadratic(m1, vector), ei.exact_quadratic(m2, vector)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("certificate", type=Path)
    ap.add_argument("--degree", type=int, default=8)
    ap.add_argument("--precisions", default="100,160")
    ap.add_argument("--digits", type=int, default=55)
    ap.add_argument("--radial-artifact", type=Path)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    precisions = [int(x) for x in args.precisions.split(",")]
    if len(precisions) < 2 or min(precisions) < 80:
        ap.error("give at least two precisions >=80")
    if args.degree < 0 or args.digits < 30:
        ap.error("degree must be nonnegative and digits at least 30")

    cert_bytes = args.certificate.read_bytes()
    cert = json.loads(cert_bytes)
    integrator_path = EI_DIR / "src" / "exact_integrator.py"
    integrator_sha = sha(integrator_path)
    if cert.get("integrator_sha256") != integrator_sha:
        raise ValueError("certificate/integrator source mismatch")
    k = int(cert["k"])
    p = cert["parameters"]
    R, V, delta = Q(p["alpha"]), Q(p["eta"]), Q(p["delta"])
    if not (Q(p["beta1"]) == Q(p["beta2"]) ==
            Q(p["beta3plus"]) == R):
        raise ValueError("outer-shell preset requires full simplex")
    global_basis = [(int(a), tuple(int(x) for x in lam))
                    for a, lam in cert["basis"]]
    global_vector = [Q(x) for x in cert["rational_vector"]]
    D, N = Q(cert["exact_denominator"]), Q(cert["exact_numerator"])
    q0 = N / D

    shell_basis = ei.even_basis(args.degree)
    support_R = ei.OneStratumSupport(k, R, delta, V, R, R, R)
    support_V = ei.OneStratumSupport(k, V, delta, V, V, V, V)
    common = ei.OneStratumSupport(k - 1, V, delta, V, V, V, V)

    # The global marginal M_R(F0), recentered at the common endpoint V.
    base_R = recenter_at(
        marginal_polynomial(global_basis, global_vector, k, R), R, V)
    if k * integrate_residual_poly(square_orbit_polynomial(base_R), common) != N:
        raise AssertionError("base RR marginal failed exact certificate match")

    # Reconstruct all outer-shell marginals once.
    shell_marginals = []
    for index, g in enumerate(shell_basis, 1):
        raw_R = marginal_polynomial([g], [Q(1)], k, R)
        raw_V = marginal_polynomial([g], [Q(1)], k, V)
        shell_marginals.append(subtract(recenter_at(raw_R, R, V),
                                        recenter_at(raw_V, V, V)))
        print(f"marginal {index}/{len(shell_basis)} {g}",
              file=sys.stderr, flush=True)

    n = 1 + len(shell_basis)
    m1 = [[Q(0) for _ in range(n)] for _ in range(n)]
    m2 = [[Q(0) for _ in range(n)] for _ in range(n)]
    m1[0][0], m2[0][0] = D, N
    for j, (g, marginal) in enumerate(zip(shell_basis, shell_marginals), 1):
        x = sum(coefficient *
                (support_R.basis_m1(label, g) -
                 support_V.basis_m1(label, g))
                for coefficient, label in zip(global_vector, global_basis))
        y = k * integrate_residual_poly(
            cross_orbit_polynomial(base_R, marginal), common)
        m1[0][j] = m1[j][0] = x
        m2[0][j] = m2[j][0] = y

    for i, (left, left_marginal) in enumerate(
            zip(shell_basis, shell_marginals), 1):
        for j in range(1, i + 1):
            right, right_marginal = shell_basis[j - 1], shell_marginals[j - 1]
            x = (support_R.basis_m1(left, right) -
                 support_V.basis_m1(left, right))
            y = k * integrate_residual_poly(
                cross_orbit_polynomial(left_marginal, right_marginal), common)
            m1[i][j] = m1[j][i] = x
            m2[i][j] = m2[j][i] = y
        print(f"matrix row {i}/{len(shell_basis)}",
              file=sys.stderr, flush=True)

    # Exact structural regressions against both the input certificate and the
    # earlier scalar radial split (whose shell direction is F0 itself).
    base_vector = [Q(1)] + [Q(0)] * len(shell_basis)
    base_D, base_N = exact_forms(m1, m2, base_vector)
    if (base_D, base_N) != (D, N):
        raise AssertionError("principal global-vector form mismatch")
    radial_regression = None
    if args.radial_artifact:
        radial = json.loads(args.radial_artifact.read_bytes())
        amplitude_inner, amplitude_outer = map(Q, radial["rational_amplitudes"])
        if amplitude_inner != 1:
            raise ValueError("radial regression expects inner amplitude one")
        shell_f0 = [Q(0)] + [Q(0)] * len(shell_basis)
        # F0 need not itself be a shell label.  Contract it directly using the
        # same exact formulas and compare the earlier two-vector result.
        f_terms = {(a, lam): c for c, (a, lam) in
                   zip(global_vector, global_basis) if c}
        inner_I = sum(c * support_V.orbit_support_moment(lam, a)
                      for (a, lam), c in
                      square_orbit_polynomial(f_terms).items())
        radial_I = D - inner_I
        base_V = recenter_at(
            marginal_polynomial(global_basis, global_vector, k, V), V, V)
        outer_marginal = subtract(base_R, base_V)
        radial_cross_J = integrate_residual_poly(
            cross_orbit_polynomial(base_R, outer_marginal), common)
        radial_self_J = integrate_residual_poly(
            square_orbit_polynomial(outer_marginal), common)
        t = amplitude_outer - 1
        radial_D = D + 2 * t * radial_I + t * t * radial_I
        radial_N = N + 2 * t * k * radial_cross_J + t * t * k * radial_self_J
        if str(radial_N / radial_D) != radial["exact_quotient"]:
            raise AssertionError("direct shell-F0 regression failed")
        radial_regression = {
            "artifact_sha256": sha(args.radial_artifact),
            "exact_quotient_match": True,
        }

    solves = [solve_once(m1, m2, precision) for precision in precisions]
    winner = solves[-1]
    with localcontext() as ctx:
        ctx.prec = max(precisions) + 20
        rational_vector = [Q(format(Decimal(x), f".{args.digits}E"))
                           for x in winner["vector"]]
    exact_D, exact_N = exact_forms(m1, m2, rational_vector)
    if exact_D <= 0:
        raise ArithmeticError("rationalized block vector has nonpositive I")
    quotient = exact_N / exact_D

    result = {
        "format": "direct-bv-global-D16-plus-outer-shell-even-block-exact-v1",
        "claim_scope": ("The matrix and particular-vector forms are exact. "
                        "Cross-precision Decimal whitening/Jacobi is discovery "
                        "only and is not a rigorous optimality certificate."),
        "k": k,
        "R": str(R),
        "V": str(V),
        "degree": args.degree,
        "basis_dimension": n,
        "shell_basis": [[a, list(lam)] for a, lam in shell_basis],
        "global_certificate_sha256": hashlib.sha256(cert_bytes).hexdigest(),
        "integrator_sha256": integrator_sha,
        "screen_script_sha256": sha(HERE / "bv_outer_shell_screen.py"),
        "solver_script_sha256": sha(EI_DIR / "robust_generalized_solve.py"),
        "script_sha256": sha(Path(__file__)),
        "matrix_sha256": matrix_sha(m1, m2),
        "base_forms_exact_match": True,
        "radial_regression": radial_regression,
        "base_exact_quotient": str(q0),
        "cross_precision_solves": solves,
        "rational_significant_digits": args.digits + 1,
        "rational_vector": [str(x) for x in rational_vector],
        "exact_denominator": str(exact_D),
        "exact_numerator": str(exact_N),
        "exact_quotient": str(quotient),
        "exact_gain": str(quotient - q0),
        "exact_margin": str(exact_N - exact_D),
        "denominator_positive": exact_D > 0,
        "margin_positive": exact_N > exact_D,
    }
    encoded = (json.dumps(result, sort_keys=True, separators=(",", ":")) +
               "\n").encode()
    args.output.write_bytes(encoded)
    print(json.dumps({
        "matrix_sha256": result["matrix_sha256"],
        "exact_quotient": result["exact_quotient"],
        "exact_gain": result["exact_gain"],
        "margin_positive": result["margin_positive"],
        "artifact_sha256": hashlib.sha256(encoded).hexdigest(),
        "solves": [{key: solve[key] for key in (
            "precision", "rayleigh_quotient", "relative_residual_bound",
            "jacobi_rotations")} for solve in solves],
    }, indent=2))


if __name__ == "__main__":
    main()
