#!/usr/bin/env python3
"""Independent direct-target checker for the BV D16 dilation proxy v2.

Unlike the producer, this checker does not use the change of variables to the
old support.  It reconstructs the transformed vector and integrates its square
and its marginal square directly at (alpha1, eta1).
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from fractions import Fraction as Q
import hashlib
import json
from math import comb, factorial, isfinite
import os
from pathlib import Path
import sys


FILE = Path(__file__).resolve()
REPO = FILE.parents[3]
EI = REPO / "agents/exact-integrator/src/exact_integrator.py"
CERT = REPO / "agents/small-delta-frontier/bv_aquarter_B16_vector_exact.json"
RESULT = REPO / "agents/structural-basis/results/bv_D16_dilation_alpha3211_fullsimplex_exact_v2_frozen.json"

PINNED = {
    "agents/exact-integrator/src/exact_integrator.py":
        "941ee82bc72fd8488a95eb5e536fe47f8c95d39a1b618dae7d6ef7eb27122e52",
    "agents/small-delta-frontier/bv_aquarter_B16_vector_exact.json":
        "59715ddffa483c696c035634a81c3cc8ffe882e9d6eaceec74bea23996b72d62",
    "agents/structural-basis/code/bv_dilation_fullsimplex_proxy_v2.py":
        "890f0ca43b24a592a33b95dc0cb3a8b853767b66d2a215f112f94f1652d571ce",
    "agents/structural-basis/results/bv_D16_dilation_alpha3211_fullsimplex_exact_v2_frozen.json":
        "34966e5e2161ed49c32de12e51f78d90ac196899ccb3a82d37a011d22192ba7f",
}

sys.path.insert(0, str(EI.parent))
import exact_integrator as exact  # noqa: E402


K = 48
ALPHA1 = Q(3211, 12000)
ETA1 = Q(3031, 12000)
C = Q(3090, 3211)


def sha256(value):
    data = value if isinstance(value, bytes) else Path(value).read_bytes()
    return hashlib.sha256(data).hexdigest()


def strict_json(path):
    def pairs(items):
        answer = {}
        for key, value in items:
            if key in answer:
                raise ValueError(f"duplicate JSON key {key}")
            answer[key] = value
        return answer

    return json.loads(Path(path).read_bytes(), object_pairs_hook=pairs,
                      parse_constant=lambda token: (_ for _ in ()).throw(
                          ValueError(f"nonfinite JSON token {token}")))


def format_q(value):
    value = Q(value)
    return (str(value.numerator) if value.denominator == 1 else
            f"{value.numerator}/{value.denominator}")


def parse_q(value):
    if not isinstance(value, str):
        raise TypeError("rational must be serialized as a string")
    result = Q(value)
    if format_q(result) != value:
        raise ValueError("noncanonical rational")
    return result


def validate_closure():
    for relative, digest in PINNED.items():
        if sha256(REPO / relative) != digest:
            raise ValueError(f"dilation audit input changed: {relative}")
    if (Path(exact.__file__).resolve() != EI.resolve() or
            sha256(Path(exact.__file__).resolve()) != PINNED[
                "agents/exact-integrator/src/exact_integrator.py"]):
        raise ValueError("wrong exact_integrator module")


def independent_transform(basis, vector):
    positions = {label: i for i, label in enumerate(basis)}
    if len(positions) != len(basis):
        raise ValueError("duplicate basis")
    result = [Q(0)] * len(basis)
    for theta, (a, lam) in zip(vector, basis):
        for b in range(a + 1):
            index = positions.get((b, lam))
            if index is None:
                raise ValueError("transform leaves basis")
            result[index] += (theta * Q(comb(a, b)) *
                              (1 - C) ** (a - b) *
                              C ** (b + sum(lam)))
    return result


def split_distinguished(lam, k):
    answer = []
    if len(lam) < k:
        answer.append((0, lam))
    for e in sorted(set(lam)):
        rest = list(lam)
        rest.remove(e)
        answer.append((e, tuple(rest)))
    return answer


def target_marginal(basis, vector, alpha=ALPHA1):
    result = defaultdict(Q)
    for theta, (a, lam) in zip(vector, basis):
        for e, rest in split_distinguished(lam, K):
            for j in range(a + 1):
                result[(e + j + 1, rest)] += (
                    theta * comb(a, j) * (1 - alpha) ** (a - j) *
                    Q(factorial(e) * factorial(j),
                      factorial(e + j + 1)))
    return {key: value for key, value in result.items() if value}


def orbit_square(terms):
    """Canonical lower-pair square, independently ordered from producer."""
    items = sorted(terms.items(), reverse=True)
    result = defaultdict(Q)
    for left_index, ((left_power, left_lam), left) in enumerate(items):
        for right_index in range(left_index, len(items)):
            (right_power, right_lam), right = items[right_index]
            factor = 1 if left_index == right_index else 2
            for nu, multiplicity in exact.multiply_monomial_orbits(
                    left_lam, right_lam):
                result[(left_power + right_power, nu)] += (
                    factor * left * right * multiplicity)
    return {key: value for key, value in result.items() if value}


def radial_orbit_integral(dimension, lam, residual_power,
                          residual_origin, cutoff):
    """Integrate P_lam(u)*(residual_origin-sum u)^power to cutoff."""
    if len(lam) > dimension:
        return Q(0)
    angular = 1
    for exponent in lam:
        angular *= factorial(exponent)
    total_degree = sum(lam)
    canonical = Q(0)
    for d in range(residual_power + 1):
        degree = total_degree + dimension + d
        canonical += (
            comb(residual_power, d) *
            (residual_origin - cutoff) ** (residual_power - d) *
            Q(angular * factorial(d), factorial(degree)) *
            cutoff ** degree)
    return exact.orbit_size(dimension, lam) * canonical


def integrate_terms(terms, dimension, residual_origin, cutoff):
    return sum(
        coefficient * radial_orbit_integral(
            dimension, lam, power, residual_origin, cutoff)
        for (power, lam), coefficient in terms.items())


def direct_target_forms(basis, transformed, alpha=ALPHA1, eta=ETA1):
    raw_basis = {(a, lam): theta
                 for theta, (a, lam) in zip(transformed, basis) if theta}
    square = orbit_square(raw_basis)
    denominator = integrate_terms(square, K, Q(1), alpha)
    marginal = target_marginal(basis, transformed, alpha)
    marginal_square = orbit_square(marginal)
    j = integrate_terms(marginal_square, K - 1, alpha, eta)
    return denominator, K * j, len(square), len(marginal_square)


def audit():
    validate_closure()
    cert = strict_json(CERT)
    result = strict_json(RESULT)
    basis = [(a, tuple(lam)) for a, lam in cert.get("basis", ())]
    vector = [parse_q(x) for x in cert.get("rational_vector", ())]
    if (basis != exact.even_basis(16) or len(vector) != 307 or
            cert.get("k") != K or result.get("k") != K or
            result.get("degree") != 16 or
            result.get("basis_dimension") != 307 or
            result.get("status") != "exact-full-simplex-dilation-search-proxy" or
            result.get("rigorous_arithmetic") is not True or
            result.get("analytic_support_approved") is not False or
            result.get("theorem_ready") is not False or
            result.get("script_sha256") != PINNED[
                "agents/structural-basis/code/bv_dilation_fullsimplex_proxy_v2.py"] or
            result.get("source_hashes") != {
                key: value for key, value in PINNED.items()
                if key in (
                    "agents/exact-integrator/src/exact_integrator.py",
                    "agents/small-delta-frontier/bv_aquarter_B16_vector_exact.json")
            }):
        raise ValueError("dilation result/certificate schema changed")
    wall = result.get("wall_seconds")
    if (isinstance(wall, bool) or not isinstance(wall, (int, float)) or
            not isfinite(wall) or wall < 0):
        raise ValueError("invalid producer runtime")

    transformed = independent_transform(basis, vector)
    serialized = [parse_q(x)
                  for x in result.get("transformed_rational_vector", ())]
    if transformed != serialized:
        raise ArithmeticError("transformed coefficient vector mismatch")
    denominator, numerator, square_count, marginal_square_count = (
        direct_target_forms(basis, transformed))
    exact_forms = result.get("exact_forms")
    if not isinstance(exact_forms, dict):
        raise ValueError("missing exact forms")
    expected_denominator = parse_q(exact_forms.get("denominator"))
    expected_numerator = parse_q(exact_forms.get("numerator_48J"))
    expected_margin = parse_q(exact_forms.get("margin_48J_minus_I"))
    expected_quotient = parse_q(exact_forms.get("quotient"))
    if (denominator != expected_denominator or numerator != expected_numerator or
            numerator - denominator != expected_margin or
            numerator / denominator != expected_quotient or
            denominator <= 0 or expected_margin <= 0 or
            exact_forms.get("margin_positive") is not True or
            exact_forms.get("quotient_greater_than_one") is not True):
        raise ArithmeticError("direct target forms do not match producer")

    inner_denominator, inner_numerator, inner_square_count, inner_j_count = (
        direct_target_forms(basis, transformed, Q(103, 400), ETA1))
    inner = result.get("inner_alpha0_wide_eta_block")
    if (not isinstance(inner, dict) or
            parse_q(inner.get("denominator")) != inner_denominator or
            parse_q(inner.get("numerator_48J")) != inner_numerator or
            parse_q(inner.get("margin_48J_minus_I")) !=
            inner_numerator - inner_denominator or
            parse_q(inner.get("quotient")) !=
            inner_numerator / inner_denominator or
            parse_q(inner.get("shortfall_to_one")) !=
            1 - inner_numerator / inner_denominator or
            not inner_numerator < inner_denominator or
            inner.get("quotient_greater_than_one") is not False or
            inner.get("basis_square_term_count") != inner_square_count or
            inner.get("marginal_square_term_count") != inner_j_count):
        raise ArithmeticError("direct inner-block forms do not match producer")

    old_q = parse_q(cert["exact_quotient"])
    monotone = result.get("monotonicity_certificate")
    lower = old_q / C
    if (not isinstance(monotone, dict) or
            parse_q(monotone.get("scaled_cutoff_minus_eta0")) !=
            C * ETA1 - Q(97, 400) or
            parse_q(monotone.get("exact_quotient_lower_bound")) != lower or
            parse_q(monotone.get("exact_lower_bound_minus_one")) != lower - 1 or
            parse_q(monotone.get("actual_quotient_minus_lower_bound")) !=
            numerator / denominator - lower or
            monotone.get("square_integrand_nonnegative") is not True or
            not numerator / denominator >= lower > 1):
        raise ArithmeticError("monotone lower-bound certificate mismatch")

    return {
        "status": "AUDIT PASS",
        "scope": (
            "Exact direct full-simplex target-chart reconstruction of the "
            "non-analytic dilation proxy; no Proposition-1 or theorem claim."),
        "auditor_sha256": sha256(FILE),
        "source_hashes": dict(PINNED),
        "direct_target_denominator": format_q(denominator),
        "direct_target_numerator_48J": format_q(numerator),
        "direct_target_margin": format_q(numerator - denominator),
        "direct_target_quotient": format_q(numerator / denominator),
        "direct_inner_denominator": format_q(inner_denominator),
        "direct_inner_numerator_48J": format_q(inner_numerator),
        "direct_inner_quotient": format_q(
            inner_numerator / inner_denominator),
        "direct_inner_shortfall": format_q(
            1 - inner_numerator / inner_denominator),
        "exact_monotone_quotient_lower_bound": format_q(lower),
        "direct_basis_square_term_count": square_count,
        "direct_marginal_square_term_count": marginal_square_count,
        "analytic_support_approved": False,
        "theorem_ready": False,
    }


def canonical_json(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"),
                       allow_nan=False) + "\n").encode("ascii")


def publish_new(path, value):
    path = Path(path).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    encoded = canonical_json(value)
    with os.fdopen(fd, "wb") as handle:
        handle.write(encoded)
        handle.flush()
        os.fsync(handle.fileno())
    if sha256(path) != sha256(encoded):
        raise RuntimeError("audit artifact changed after write")
    return sha256(encoded)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output")
    args = parser.parse_args()
    result = audit()
    if args.output:
        print(publish_new(args.output, result))
    else:
        print(canonical_json(result).decode("ascii"), end="")


if __name__ == "__main__":
    main()
