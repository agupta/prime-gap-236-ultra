#!/usr/bin/env python3
"""Exact fixed-polynomial epsilon scan on the direct-BV full simplex.

The input vector is not reoptimized.  Its square and distinguished-coordinate
marginal are first collected as finite orbit polynomials, so one epsilon point
needs only a few thousand scalar Dirichlet moments rather than a full matrix.
The original epsilon is required to reproduce the certificate's exact I and
kJ forms bit for bit.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from collections import defaultdict
from fractions import Fraction as Q
from pathlib import Path

if hasattr(sys, "set_int_max_str_digits"):
    sys.set_int_max_str_digits(0)

HERE = Path(__file__).resolve().parent
EI_DIR = HERE.parent / "exact-integrator"
sys.path.insert(0, str(EI_DIR / "src"))

import exact_integrator as ei


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def square_orbit_polynomial(terms):
    """Square sum c_(a,lam) L^a P_lam, collecting (L-power,orbit)."""
    items = [(key, value) for key, value in terms.items() if value]
    out = defaultdict(Q)
    for i, ((a, lam), left) in enumerate(items):
        for j in range(i + 1):
            (b, mu), right = items[j]
            pair = left * right * (1 if i == j else 2)
            for nu, multiplicity in ei.multiply_monomial_orbits(lam, mu):
                out[(a + b, nu)] += pair * multiplicity
    return {key: value for key, value in out.items() if value}


def marginal_polynomial(basis, vector, k, alpha):
    """Collect integral_0^(alpha-U) F(u,t)dt as P_lam(u)(alpha-U)^p."""
    out = defaultdict(Q)
    for coefficient, (a, lam) in zip(vector, basis):
        if not coefficient:
            continue
        for exponent, rest in ei.OneStratumSupport.split_at_distinguished(lam, k):
            for c in range(a + 1):
                power = exponent + c + 1
                factor = Q(math.comb(a, c) * math.factorial(exponent) *
                           math.factorial(c), math.factorial(exponent + c + 1))
                out[(power, rest)] += (coefficient * factor *
                                       ((1 - alpha) ** (a - c)))
    return {key: value for key, value in out.items() if value}


def truncated_residual_orbit(k_minus_one, nu, power, alpha, eta):
    """Integral P_nu(u)(alpha-sum u)^power over sum u<=eta."""
    if len(nu) > k_minus_one:
        return Q(0)
    prod = math.prod(math.factorial(x) for x in nu)
    total = sum(nu)
    canonical = Q(0)
    for d in range(power + 1):
        radial_degree = total + k_minus_one + d
        canonical += (math.comb(power, d) *
                      ((alpha - eta) ** (power - d)) *
                      Q(prod * math.factorial(d), math.factorial(radial_degree)) *
                      (eta ** radial_degree))
    return ei.orbit_size(k_minus_one, nu) * canonical


def direct_forms(k, basis, vector, alpha, eta, delta, precomputed_square=None):
    support = ei.OneStratumSupport(k, alpha, delta, eta, alpha, alpha, alpha)
    if not support.is_full_simplex():
        raise AssertionError("B_m=alpha must be recognized as a full simplex")
    f_terms = {(a, lam): coefficient
               for coefficient, (a, lam) in zip(vector, basis) if coefficient}
    f_square = (precomputed_square if precomputed_square is not None
                else square_orbit_polynomial(f_terms))
    denominator = sum(
        coefficient * support.orbit_support_moment(nu, power)
        for (power, nu), coefficient in f_square.items())
    marginal = marginal_polynomial(basis, vector, k, alpha)
    marginal_square = square_orbit_polynomial(marginal)
    j = sum(coefficient * truncated_residual_orbit(
                k - 1, nu, power, alpha, eta)
            for (power, nu), coefficient in marginal_square.items())
    return denominator, k * j, len(f_square), len(marginal), len(marginal_square)


def self_test() -> None:
    k = 4
    basis = ei.even_basis(4)
    vector = [Q((i % 5) - 2, i + 3) for i in range(len(basis))]
    alpha, eta, delta = Q(13, 50), Q(6, 25), Q(1, 20)
    support = ei.OneStratumSupport(k, alpha, delta, eta,
                                  alpha, alpha, alpha)
    m1, m2 = support.matrices(basis)
    expected = ei.exact_quadratic(m1, vector), ei.exact_quadratic(m2, vector)
    got = direct_forms(k, basis, vector, alpha, eta, delta)[:2]
    if got != expected:
        raise AssertionError("low-k direct-polynomial/matrix mismatch")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("certificate", type=Path)
    ap.add_argument("--epsilons", default=(
        "1/1000,1/500,1/400,3/1000,1/300,7/2000,1/250,1/200,"
        "3/500,7/1000,3/400,1/125,9/1000,1/100,1/80"))
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    self_test()

    cert_bytes = args.certificate.read_bytes()
    cert = json.loads(cert_bytes)
    source_path = EI_DIR / "src" / "exact_integrator.py"
    source_hash = sha(source_path)
    if cert.get("integrator_sha256") != source_hash:
        raise ValueError("certificate/integrator source mismatch")
    k = int(cert["k"])
    basis = [(int(a), tuple(int(x) for x in lam))
             for a, lam in cert["basis"]]
    vector = [Q(x) for x in cert["rational_vector"]]
    p = cert["parameters"]
    original_alpha, original_eta = Q(p["alpha"]), Q(p["eta"])
    A = (original_alpha + original_eta) / 2
    original_epsilon = (original_alpha - original_eta) / 2
    delta = Q(p["delta"])
    if (A != Q(1, 4) or Q(p["beta1"]) != original_alpha or
            Q(p["beta2"]) != original_alpha or
            Q(p["beta3plus"]) != original_alpha):
        raise ValueError("input is not the direct-BV full-simplex family")
    epsilon_values = sorted(set(Q(x) for x in args.epsilons.split(",")))
    if original_epsilon not in epsilon_values:
        epsilon_values.append(original_epsilon)
        epsilon_values.sort()
    if any(e <= 0 or e >= Q(1, 4) for e in epsilon_values):
        raise ValueError("direct-BV family requires 0<epsilon<1/4")

    f_terms = {(a, lam): coefficient
               for coefficient, (a, lam) in zip(vector, basis) if coefficient}
    f_square = square_orbit_polynomial(f_terms)
    rows = []
    baseline_match = False
    for epsilon in epsilon_values:
        alpha, eta = A + epsilon, A - epsilon
        denominator, numerator, ni, nm, nj = direct_forms(
            k, basis, vector, alpha, eta, delta, f_square)
        if denominator <= 0:
            raise ArithmeticError("nonpositive fixed-vector denominator")
        quotient = numerator / denominator
        if epsilon == original_epsilon:
            if (str(denominator) != cert["exact_denominator"] or
                    str(numerator) != cert["exact_numerator"] or
                    str(quotient) != cert["exact_quotient"]):
                raise AssertionError("baseline does not reproduce certificate forms")
            baseline_match = True
        row = {
            "epsilon": str(epsilon), "alpha": str(alpha), "eta": str(eta),
            "B_all": str(alpha),
            "definition1_margins": {
                "epsilon": str(epsilon),
                "one_half_minus_epsilon_minus_A": str(Q(1, 4) - epsilon),
                "B1_minus_delta": str(alpha - delta),
                "beta_minus_B1": str(Q(1, 4) - epsilon),
            },
            "relevant_modulus_exponent": "1/2",
            "exact_denominator": str(denominator),
            "exact_numerator": str(numerator),
            "exact_quotient": str(quotient),
            "exact_margin": str(numerator - denominator),
            "exact_quotient_decimal": format(float(quotient), ".17g"),
            "exact_margin_positive": numerator > denominator,
            "term_counts": {"F_square": ni, "marginal": nm,
                            "marginal_square": nj},
        }
        rows.append(row)
        print("epsilon", epsilon, "q", row["exact_quotient_decimal"],
              "sign", "+" if numerator > denominator else "-")
    if not baseline_match:
        raise AssertionError("baseline epsilon was not evaluated")

    winner = max(rows, key=lambda row: Q(row["exact_quotient"]))
    analytic_note = HERE.parent / "independent-attack" / "direct-bv-family.md"
    output = {
        "format": "direct-bv-fixed-vector-epsilon-scan-v1",
        "claim_scope": ("Every row is an exact particular-vector quotient on "
                        "an analytically valid direct-BV support. The vector is "
                        "not reoptimized away from its original epsilon."),
        "analytic_family": {
            "A": "1/4", "delta": str(delta), "range": "0<epsilon<1/4",
            "support": "sum(t_i)<1/4+epsilon; B_m=1/4+epsilon",
            "J_common_coordinate_cutoff": "1/4-epsilon",
            "relevant_modulus_bound": "x^((1-epsilon0)/2)",
            "rho": "1_P", "c1": 0, "c2": 0, "beta": "1/2",
        },
        "analytic_note_sha256": sha(analytic_note),
        "integrator_sha256": source_hash,
        "script_sha256": sha(Path(__file__)),
        "certificate_sha256": hashlib.sha256(cert_bytes).hexdigest(),
        "original_epsilon": str(original_epsilon),
        "baseline_exact_match": baseline_match,
        "winner_epsilon": winner["epsilon"],
        "winner_exact_quotient": winner["exact_quotient"],
        "winner_exact_quotient_decimal": winner["exact_quotient_decimal"],
        "rows": rows,
    }
    encoded = (json.dumps(output, sort_keys=True, separators=(",", ":")) + "\n").encode()
    args.output.write_bytes(encoded)
    print("winner", winner["epsilon"], winner["exact_quotient_decimal"])
    print("artifact_sha256", hashlib.sha256(encoded).hexdigest())


if __name__ == "__main__":
    main()
