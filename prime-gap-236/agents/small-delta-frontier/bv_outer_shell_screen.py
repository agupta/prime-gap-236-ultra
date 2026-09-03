#!/usr/bin/env python3
"""Exact single-direction screen for outer-shell BV basis functions.

Each candidate is h=1_{V<sum(t)<R}(1-P1)^a P_lambda.  Exact I and kJ
cross/self forms against the certified global D16 vector are reconstructed
from full-simplex moments and cross-upper-radius marginals.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from collections import defaultdict
from decimal import Decimal, localcontext
from fractions import Fraction as Q
from pathlib import Path

if hasattr(sys, "set_int_max_str_digits"):
    sys.set_int_max_str_digits(0)

HERE = Path(__file__).resolve().parent
EI_DIR = HERE.parent / "exact-integrator"
sys.path.insert(0, str(EI_DIR / "src"))
sys.path.insert(0, str(HERE))

import exact_integrator as ei
from bv_radial_two_amplitudes import recenter_at, subtract
from scan_bv_epsilon_fixed import marginal_polynomial, square_orbit_polynomial


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def cross_orbit_polynomial(left, right):
    out = defaultdict(Q)
    for (a, lam), c in left.items():
        for (b, mu), d in right.items():
            if not c or not d:
                continue
            for nu, multiplicity in ei.multiply_monomial_orbits(lam, mu):
                out[(a + b, nu)] += c * d * multiplicity
    return {key: value for key, value in out.items() if value}


def integrate_residual_poly(poly, common_support):
    return sum(coefficient * ei.orbit_size(common_support.k, nu) *
               common_support.canonical_support_residual(nu, power)
               for (power, nu), coefficient in poly.items())


def two_vector_exact(D, N, a, b, d, n, precision, digits):
    c2 = D * d - a * a
    c1 = -N * d - n * D + 2 * a * b
    c0 = N * n - b * b
    if c2 <= 0:
        raise ArithmeticError("nonpositive exact Gram novelty")
    disc = c1 * c1 - 4 * c2 * c0
    if disc < 0:
        raise ArithmeticError("negative exact pencil discriminant")
    with localcontext() as ctx:
        ctx.prec = precision

        def dec(x):
            return Decimal(x.numerator) / Decimal(x.denominator)

        lam = (-dec(c1) + dec(disc).sqrt()) / (2 * dec(c2))
        first = dec(b) - lam * dec(a)
        second = dec(n) - lam * dec(d)
        if abs(first) >= abs(second):
            t_dec = (lam * dec(D) - dec(N)) / first
        else:
            t_dec = (lam * dec(a) - dec(b)) / second
        t = Q(format(t_dec, f".{digits}E"))
    out_D = D + 2 * t * a + t * t * d
    out_N = N + 2 * t * b + t * t * n
    if out_D <= 0:
        raise ArithmeticError("rationalized candidate denominator nonpositive")
    return str(lam), t, out_N / out_D, out_N - out_D


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("certificate", type=Path)
    ap.add_argument("--degree", type=int, default=8)
    ap.add_argument("--precision", type=int, default=140)
    ap.add_argument("--digits", type=int, default=45)
    ap.add_argument("--radial-artifact", type=Path)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()

    cert_bytes = args.certificate.read_bytes()
    cert = json.loads(cert_bytes)
    source_path = EI_DIR / "src" / "exact_integrator.py"
    source_hash = sha(source_path)
    if cert.get("integrator_sha256") != source_hash:
        raise ValueError("certificate/integrator source mismatch")
    k = int(cert["k"])
    p = cert["parameters"]
    R, V, delta = Q(p["alpha"]), Q(p["eta"]), Q(p["delta"])
    if not (Q(p["beta1"]) == Q(p["beta2"]) ==
            Q(p["beta3plus"]) == R):
        raise ValueError("outer-shell preset requires full simplex")
    basis = [(int(a), tuple(int(x) for x in lam))
             for a, lam in cert["basis"]]
    vector = [Q(x) for x in cert["rational_vector"]]
    D, N = Q(cert["exact_denominator"]), Q(cert["exact_numerator"])
    q0 = N / D
    support_R = ei.OneStratumSupport(k, R, delta, V, R, R, R)
    support_V = ei.OneStratumSupport(k, V, delta, V, V, V, V)
    common = ei.OneStratumSupport(k - 1, V, delta, V, V, V, V)

    raw_base_R = marginal_polynomial(basis, vector, k, R)
    base_R = recenter_at(raw_base_R, R, V)
    base_R_norm = integrate_residual_poly(
        square_orbit_polynomial(base_R), common)
    if k * base_R_norm != N:
        raise AssertionError("base RR marginal failed exact certificate match")

    # Strong implementation regression: the special shell direction h=F0 on
    # the outer region is exactly the earlier two-amplitude radial family.
    raw_base_V = marginal_polynomial(basis, vector, k, V)
    base_V = recenter_at(raw_base_V, V, V)
    base_D = subtract(base_R, base_V)
    radial_self_J = integrate_residual_poly(square_orbit_polynomial(base_D), common)
    radial_cross_J = integrate_residual_poly(
        cross_orbit_polynomial(base_R, base_D), common)
    f_terms = {(a, lam): coefficient
               for coefficient, (a, lam) in zip(vector, basis) if coefficient}
    f_square = square_orbit_polynomial(f_terms)
    inner_I = sum(coefficient * support_V.orbit_support_moment(nu, power)
                  for (power, nu), coefficient in f_square.items())
    radial_self_I = D - inner_I
    radial_cross_I = radial_self_I
    radial_regression = None
    if args.radial_artifact:
        radial = json.loads(args.radial_artifact.read_bytes())
        amp_a, amp_b = map(Q, radial["rational_amplitudes"])
        if amp_a != 1:
            raise ValueError("radial regression expects first amplitude one")
        t = amp_b - 1
        den = D + 2 * t * radial_cross_I + t * t * radial_self_I
        num = N + 2 * t * k * radial_cross_J + t * t * k * radial_self_J
        if str(num / den) != radial["exact_quotient"]:
            raise AssertionError("outer-F0 regression failed radial artifact")
        radial_regression = {
            "artifact_sha256": sha(args.radial_artifact),
            "exact_quotient_match": True,
        }

    rows = []
    candidates = ei.even_basis(args.degree)
    for index, g in enumerate(candidates, 1):
        # I shell is the difference of two full-simplex forms.
        cross_I = sum(coefficient *
                      (support_R.basis_m1(x, g) - support_V.basis_m1(x, g))
                      for coefficient, x in zip(vector, basis))
        self_I = support_R.basis_m1(g, g) - support_V.basis_m1(g, g)

        raw_R = marginal_polynomial([g], [Q(1)], k, R)
        raw_V = marginal_polynomial([g], [Q(1)], k, V)
        shell_marginal = subtract(recenter_at(raw_R, R, V),
                                  recenter_at(raw_V, V, V))
        cross_J = integrate_residual_poly(
            cross_orbit_polynomial(base_R, shell_marginal), common)
        self_J = integrate_residual_poly(
            square_orbit_polynomial(shell_marginal), common)
        cross_kJ, self_kJ = k * cross_J, k * self_J
        eigenvalue, t, quotient, margin = two_vector_exact(
            D, N, cross_I, cross_kJ, self_I, self_kJ,
            args.precision, args.digits)
        novelty = self_I - cross_I * cross_I / D
        residual = cross_kJ - q0 * cross_I
        rows.append({
            "label": [g[0], list(g[1])],
            "cross_I": str(cross_I), "cross_kJ": str(cross_kJ),
            "self_I": str(self_I), "self_kJ": str(self_kJ),
            "exact_I_novelty_against_vector": str(novelty),
            "exact_eigen_residual": str(residual),
            "decimal_2d_optimum": eigenvalue,
            "rational_shell_coefficient": str(t),
            "exact_quotient": str(quotient),
            "exact_gain": str(quotient - q0),
            "exact_margin": str(margin),
            "exact_quotient_decimal": format(float(quotient), ".17g"),
            "exact_gain_decimal": format(float(quotient - q0), ".17g"),
        })
        print(f"candidate {index}/{len(candidates)} {g}: "
              f"gain={float(quotient-q0):.8g}", file=sys.stderr, flush=True)
    rows.sort(key=lambda row: Q(row["exact_quotient"]), reverse=True)
    sum_single_gains = sum(max(Q(0), Q(row["exact_gain"])) for row in rows)
    output = {
        "format": "direct-bv-outer-shell-single-directions-exact-v1",
        "claim_scope": ("Each row is the exact rational-vector quotient in "
                        "span{stored global vector, one outer-shell label}; "
                        "the sum of gains is only a heuristic screen."),
        "k": k, "R": str(R), "V": str(V), "degree": args.degree,
        "integrator_sha256": source_hash,
        "script_sha256": sha(Path(__file__)),
        "certificate_sha256": hashlib.sha256(cert_bytes).hexdigest(),
        "candidate_count": len(candidates),
        "base_RR_exact_match": True,
        "radial_regression": radial_regression,
        "base_exact_quotient": str(q0),
        "sum_positive_single_gains_heuristic": str(sum_single_gains),
        "sum_positive_single_gains_decimal": format(float(sum_single_gains), ".17g"),
        "rows": rows,
    }
    encoded = (json.dumps(output, sort_keys=True, separators=(",", ":")) + "\n").encode()
    args.output.write_bytes(encoded)
    print("top", [(row["label"], row["exact_gain_decimal"])
                  for row in rows[:10]])
    print("sum_positive_single_gains", output["sum_positive_single_gains_decimal"])
    print("artifact_sha256", hashlib.sha256(encoded).hexdigest())


if __name__ == "__main__":
    main()
