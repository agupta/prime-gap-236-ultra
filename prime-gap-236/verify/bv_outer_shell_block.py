#!/usr/bin/env python3
"""Fail-closed reconstruction of a direct-BV outer-shell block certificate."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import defaultdict
from decimal import Decimal, localcontext
from fractions import Fraction as Q
from pathlib import Path

if hasattr(sys, "set_int_max_str_digits"):
    sys.set_int_max_str_digits(0)

VERIFY_DIR = Path(__file__).resolve().parent
ROOT = VERIFY_DIR.parent
FRONTIER = ROOT / "agents" / "small-delta-frontier"
EI_DIR = ROOT / "agents" / "exact-integrator"
sys.path.insert(0, str(EI_DIR / "src"))
sys.path.insert(0, str(FRONTIER))

import exact_integrator as ei
from bv_radial_two_amplitudes import recenter_at, subtract
from scan_bv_epsilon_fixed import marginal_polynomial


def sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha_path(path: Path) -> str:
    return sha_bytes(path.read_bytes())


def cross_poly(left, right):
    out = defaultdict(Q)
    for (a, lam), c in left.items():
        for (b, mu), d in right.items():
            for nu, multiplicity in ei.multiply_monomial_orbits(lam, mu):
                out[(a + b, nu)] += c * d * multiplicity
    return {key: value for key, value in out.items() if value}


def integrate(poly, support):
    return sum(c * ei.orbit_size(support.k, lam) *
               support.canonical_support_residual(lam, a)
               for (a, lam), c in poly.items())


def matrix_hash(m1, m2):
    digest = hashlib.sha256()
    for name, matrix in (("M1", m1), ("M2", m2)):
        digest.update((name + "\n").encode())
        for row in matrix:
            digest.update(("\t".join(map(str, row)) + "\n").encode())
    return digest.hexdigest()


def quadratic(matrix, vector):
    return sum(vector[i] * matrix[i][j] * vector[j]
               for i in range(len(vector)) for j in range(len(vector)))


def fail(message):
    raise SystemExit("FAIL: " + message)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("artifact", type=Path)
    ap.add_argument("certificate", type=Path)
    ap.add_argument("--expected-artifact-sha256", required=True)
    ap.add_argument("--decimal-precision", type=int, default=60)
    args = ap.parse_args()

    artifact_bytes = args.artifact.read_bytes()
    if sha_bytes(artifact_bytes) != args.expected_artifact_sha256:
        fail("artifact SHA mismatch")
    artifact = json.loads(artifact_bytes)
    if artifact.get("format") != \
            "direct-bv-global-D16-plus-outer-shell-even-block-exact-v1":
        fail("wrong artifact format")
    cert_bytes = args.certificate.read_bytes()
    cert = json.loads(cert_bytes)
    if sha_bytes(cert_bytes) != artifact.get("global_certificate_sha256"):
        fail("base certificate SHA mismatch")

    dependency_paths = {
        "integrator_sha256": EI_DIR / "src" / "exact_integrator.py",
        "screen_script_sha256": FRONTIER / "bv_outer_shell_screen.py",
        "solver_script_sha256": EI_DIR / "robust_generalized_solve.py",
        "script_sha256": FRONTIER / "bv_outer_shell_block.py",
    }
    for key, path in dependency_paths.items():
        if sha_path(path) != artifact.get(key):
            fail(f"dependency hash mismatch: {key}")
    if cert.get("integrator_sha256") != artifact["integrator_sha256"]:
        fail("certificate integrator mismatch")

    k = int(cert["k"])
    p = cert["parameters"]
    R, V, delta = Q(p["alpha"]), Q(p["eta"]), Q(p["delta"])
    if [k, str(R), str(V)] != [artifact["k"], artifact["R"], artifact["V"]]:
        fail("parameter mismatch")
    if not (Q(p["beta1"]) == Q(p["beta2"]) ==
            Q(p["beta3plus"]) == R):
        fail("not a full-simplex certificate")
    shell_basis = ei.even_basis(int(artifact["degree"]))
    encoded_basis = [[a, list(lam)] for a, lam in shell_basis]
    if encoded_basis != artifact["shell_basis"]:
        fail("shell basis mismatch")
    if artifact["basis_dimension"] != len(shell_basis) + 1:
        fail("basis dimension mismatch")

    global_basis = [(int(a), tuple(map(int, lam)))
                    for a, lam in cert["basis"]]
    global_vector = list(map(Q, cert["rational_vector"]))
    D, N = Q(cert["exact_denominator"]), Q(cert["exact_numerator"])
    support_R = ei.OneStratumSupport(k, R, delta, V, R, R, R)
    support_V = ei.OneStratumSupport(k, V, delta, V, V, V, V)
    common = ei.OneStratumSupport(k - 1, V, delta, V, V, V, V)
    base_R = recenter_at(
        marginal_polynomial(global_basis, global_vector, k, R), R, V)
    if k * integrate(cross_poly(base_R, base_R), common) != N:
        fail("base J reconstruction mismatch")

    marginals = []
    for label in shell_basis:
        right = recenter_at(
            marginal_polynomial([label], [Q(1)], k, R), R, V)
        left = recenter_at(
            marginal_polynomial([label], [Q(1)], k, V), V, V)
        marginals.append(subtract(right, left))

    dimension = len(shell_basis) + 1
    m1 = [[Q(0) for _ in range(dimension)] for _ in range(dimension)]
    m2 = [[Q(0) for _ in range(dimension)] for _ in range(dimension)]
    m1[0][0], m2[0][0] = D, N
    for j, (label, marginal) in enumerate(zip(shell_basis, marginals), 1):
        m1[0][j] = m1[j][0] = sum(
            c * (support_R.basis_m1(g, label) -
                 support_V.basis_m1(g, label))
            for c, g in zip(global_vector, global_basis))
        m2[0][j] = m2[j][0] = k * integrate(
            cross_poly(base_R, marginal), common)
    for i, (left, left_marginal) in enumerate(zip(shell_basis, marginals), 1):
        for j in range(1, i + 1):
            right, right_marginal = shell_basis[j - 1], marginals[j - 1]
            m1[i][j] = m1[j][i] = (
                support_R.basis_m1(left, right) -
                support_V.basis_m1(left, right))
            m2[i][j] = m2[j][i] = k * integrate(
                cross_poly(left_marginal, right_marginal), common)
    if matrix_hash(m1, m2) != artifact["matrix_sha256"]:
        fail("matrix SHA mismatch")

    vector = list(map(Q, artifact["rational_vector"]))
    if len(vector) != dimension:
        fail("vector dimension mismatch")
    exact_D, exact_N = quadratic(m1, vector), quadratic(m2, vector)
    if str(exact_D) != artifact["exact_denominator"]:
        fail("exact denominator mismatch")
    if str(exact_N) != artifact["exact_numerator"]:
        fail("exact numerator mismatch")
    if exact_D <= 0:
        fail("nonpositive denominator")
    quotient = exact_N / exact_D
    if str(quotient) != artifact["exact_quotient"]:
        fail("exact quotient mismatch")
    if str(quotient - N / D) != artifact["exact_gain"]:
        fail("exact gain mismatch")
    if (exact_N > exact_D) != artifact["margin_positive"]:
        fail("margin sign mismatch")

    with localcontext() as ctx:
        ctx.prec = args.decimal_precision
        q_decimal = Decimal(quotient.numerator) / Decimal(quotient.denominator)
        gain = quotient - N / D
        gain_decimal = Decimal(gain.numerator) / Decimal(gain.denominator)
    print("AUDIT PASS")
    print("matrix_sha256", artifact["matrix_sha256"])
    print("exact_quotient_decimal", q_decimal)
    print("exact_gain_decimal", gain_decimal)
    print("margin_positive", exact_N > exact_D)


if __name__ == "__main__":
    main()
