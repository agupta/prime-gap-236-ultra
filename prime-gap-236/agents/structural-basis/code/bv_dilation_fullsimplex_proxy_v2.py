#!/usr/bin/env python3
"""Exact full-simplex dilation proxy v2 for the certified BV D16 polynomial.

This is a search calculation only.  It deliberately makes no claim that the
larger full-simplex parameters satisfy Stadlmann's analytic hypotheses.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from decimal import Decimal, localcontext
from fractions import Fraction as Q
import hashlib
import json
from math import comb, factorial
import os
from pathlib import Path
import sys
import time


FILE = Path(__file__).resolve()
REPO = FILE.parents[3]
EI_SOURCE = REPO / "agents/exact-integrator/src/exact_integrator.py"
CERTIFICATE = REPO / "agents/small-delta-frontier/bv_aquarter_B16_vector_exact.json"

PINNED = {
    "agents/exact-integrator/src/exact_integrator.py":
        "941ee82bc72fd8488a95eb5e536fe47f8c95d39a1b618dae7d6ef7eb27122e52",
    "agents/small-delta-frontier/bv_aquarter_B16_vector_exact.json":
        "59715ddffa483c696c035634a81c3cc8ffe882e9d6eaceec74bea23996b72d62",
}

sys.path.insert(0, str(EI_SOURCE.parent))
import exact_integrator as exact  # noqa: E402


K = 48
DEGREE = 16
ALPHA0 = Q(103, 400)
ETA0 = Q(97, 400)
ALPHA1 = Q(3211, 12000)
ETA1 = Q(3031, 12000)
C = ALPHA0 / ALPHA1


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


def parse_canonical_q(value):
    if not isinstance(value, str):
        raise TypeError("rational must be a string")
    parsed = Q(value)
    if format_q(parsed) != value:
        raise ValueError("rational is not canonical")
    return parsed


def validate_sources():
    for relative, expected in PINNED.items():
        if sha256(REPO / relative) != expected:
            raise ValueError(f"pinned dilation input changed: {relative}")
    if Path(exact.__file__).resolve() != EI_SOURCE.resolve():
        raise ValueError("wrong exact_integrator module loaded")
    if sha256(Path(exact.__file__).resolve()) != PINNED[
            "agents/exact-integrator/src/exact_integrator.py"]:
        raise ValueError("loaded exact_integrator bytes changed")


def load_certificate():
    validate_sources()
    data = strict_json(CERTIFICATE)
    expected_parameters = {
        "alpha": "103/400", "delta": "7/250", "eta": "97/400",
        "beta1": "103/400", "beta2": "103/400",
        "beta3plus": "103/400",
    }
    basis = [(a, tuple(partition)) for a, partition in data.get("basis", ())]
    vector = [parse_canonical_q(value)
              for value in data.get("rational_vector", ())]
    if (data.get("k") != K or data.get("degree") != DEGREE or
            data.get("parameters") != expected_parameters or
            data.get("integrator_sha256") != PINNED[
                "agents/exact-integrator/src/exact_integrator.py"] or
            data.get("source_run_sha256") !=
            "75112cf5d8cda1e9313ddc4dc9228b05ee9abf826515ac3d46c6bd66b353922c" or
            basis != exact.even_basis(DEGREE) or len(vector) != 307):
        raise ValueError("D16 certificate schema or basis changed")
    denominator = parse_canonical_q(data["exact_denominator"])
    numerator = parse_canonical_q(data["exact_numerator"])
    quotient = parse_canonical_q(data["exact_quotient"])
    if numerator / denominator != quotient or denominator <= 0:
        raise ArithmeticError("D16 certificate exact forms are inconsistent")
    return data, basis, vector, denominator, numerator


def dilation_transform(basis, vector, c):
    """Expand F(c*t) in the same (1-sum)^b P_lambda basis."""
    if len(basis) != len(vector):
        raise ValueError("basis/vector length mismatch")
    c = Q(c)
    target = {label: i for i, label in enumerate(basis)}
    if len(target) != len(basis):
        raise ValueError("duplicate basis label")
    answer = [Q(0) for _ in basis]
    for coefficient, (a, lam) in zip(vector, basis):
        coefficient = Q(coefficient)
        for b in range(a + 1):
            label = (b, lam)
            if label not in target:
                raise ValueError("dilation image is absent from target basis")
            answer[target[label]] += (
                coefficient * comb(a, b) * (1 - c) ** (a - b) *
                c ** (b + sum(lam)))
    return answer


def split_orbit_at_distinguished(lam, k):
    """Independent literal P_lambda(u,t) split, including repeated parts."""
    lam = tuple(lam)
    answer = []
    if len(lam) < k:
        answer.append((0, lam))
    for exponent in sorted(set(lam)):
        rest = list(lam)
        rest.remove(exponent)
        answer.append((exponent, tuple(rest)))
    return tuple(answer)


def marginal_terms(basis, vector, k, alpha):
    """Return coefficients of (alpha-U)^p P_lambda(u) in int F(u,t)dt."""
    alpha = Q(alpha)
    terms = defaultdict(Q)
    for coefficient, (a, lam) in zip(vector, basis):
        coefficient = Q(coefficient)
        for exponent, rest in split_orbit_at_distinguished(lam, k):
            for j in range(a + 1):
                power = exponent + j + 1
                beta_integral = Q(
                    factorial(exponent) * factorial(j),
                    factorial(exponent + j + 1))
                terms[(power, rest)] += (
                    coefficient * comb(a, j) *
                    (1 - alpha) ** (a - j) * beta_integral)
    return {label: value for label, value in terms.items() if value}


def square_marginal_terms(terms):
    """Square an orbit marginal, retaining exact orbit structure constants."""
    items = sorted(terms.items(), key=lambda row: (row[0][0], row[0][1]))
    squared = defaultdict(Q)
    for i, ((p, lam), x) in enumerate(items):
        for j in range(i + 1):
            (q, mu), y = items[j]
            symmetry = 1 if i == j else 2
            for nu, multiplicity in exact.multiply_monomial_orbits(lam, mu):
                squared[(p + q, nu)] += (
                    symmetry * x * y * multiplicity)
    return {label: value for label, value in squared.items() if value}


def square_basis_terms(basis, vector):
    """Square sum theta_(a,lambda)(1-S)^a P_lambda by lower pairs."""
    items = [(label, Q(coefficient))
             for label, coefficient in zip(basis, vector) if coefficient]
    squared = defaultdict(Q)
    for i, ((a, lam), x) in enumerate(items):
        for j in range(i + 1):
            (b, mu), y = items[j]
            symmetry = 1 if i == j else 2
            for nu, multiplicity in exact.multiply_monomial_orbits(lam, mu):
                squared[(a + b, nu)] += (
                    symmetry * x * y * multiplicity)
    return {label: value for label, value in squared.items() if value}


def cutoff_orbit_moment(dimension, lam, residual_power, alpha, eta):
    """Integral over sum(u)<=eta of P_lam(u)*(alpha-sum(u))^r."""
    if len(lam) > dimension:
        return Q(0)
    alpha, eta = Q(alpha), Q(eta)
    if not Q(0) < eta <= alpha:
        raise ValueError("cutoff must lie in (0,alpha]")
    angular = 1
    for exponent in lam:
        angular *= factorial(exponent)
    total = sum(lam)
    answer = Q(0)
    for d in range(residual_power + 1):
        radial_degree = total + dimension + d
        answer += (
            comb(residual_power, d) *
            (alpha - eta) ** (residual_power - d) *
            Q(angular * factorial(d), factorial(radial_degree)) *
            eta ** radial_degree)
    return exact.orbit_size(dimension, tuple(lam)) * answer


def integrate_squared_marginal(squared, dimension, alpha, eta):
    return sum(
        coefficient * cutoff_orbit_moment(
            dimension, lam, power, alpha, eta)
        for (power, lam), coefficient in squared.items())


def canonical_term_hash(terms):
    rows = [[power, list(lam), format_q(coefficient)]
            for (power, lam), coefficient in sorted(
                terms.items(), key=lambda row: (row[0][0], row[0][1]))]
    encoded = (json.dumps(rows, separators=(",", ":"),
                          ensure_ascii=True) + "\n").encode("ascii")
    return sha256(encoded)


def decimal_string(value, precision=90):
    with localcontext() as context:
        context.prec = precision
        return str(Decimal(value.numerator) / Decimal(value.denominator))


def compute_proxy(progress=False):
    started = time.monotonic()
    _, basis, vector, old_denominator, old_numerator = load_certificate()
    transformed = dilation_transform(basis, vector, C)
    marginal = marginal_terms(basis, vector, K, ALPHA0)
    if progress:
        print(f"marginal_terms={len(marginal)}", file=sys.stderr, flush=True)
    squared = square_marginal_terms(marginal)
    if progress:
        print(f"squared_terms={len(squared)}", file=sys.stderr, flush=True)

    reconstructed_old_j = integrate_squared_marginal(
        squared, K - 1, ALPHA0, ETA0)
    if K * reconstructed_old_j != old_numerator:
        raise ArithmeticError("independent marginal formula misses D16 numerator")

    scaled_eta = C * ETA1
    source_cutoff_j = integrate_squared_marginal(
        squared, K - 1, ALPHA0, scaled_eta)
    new_denominator = old_denominator / C ** K
    new_j = source_cutoff_j / C ** (K + 1)
    new_numerator = K * new_j
    quotient = new_numerator / new_denominator
    margin = new_numerator - new_denominator
    if quotient != (K * source_cutoff_j / old_denominator) / C:
        raise ArithmeticError("dilation quotient scaling identity failed")

    # A second exact row keeps the same transformed polynomial but truncates
    # the target full simplex at the old alpha.  This is the inner block for a
    # later inner/shell amplitude pencil; it is not obtained by subtracting
    # close serialized decimals.
    transformed_square = square_basis_terms(basis, transformed)
    inner_denominator = integrate_squared_marginal(
        transformed_square, K, Q(1), ALPHA0)
    inner_marginal = marginal_terms(basis, transformed, K, ALPHA0)
    inner_marginal_square = square_marginal_terms(inner_marginal)
    inner_numerator = K * integrate_squared_marginal(
        inner_marginal_square, K - 1, ALPHA0, ETA1)
    inner_quotient = inner_numerator / inner_denominator
    if not (inner_denominator > 0 and inner_quotient < 1):
        raise ArithmeticError("inner-block dilation regression changed sign")

    old_quotient = old_numerator / old_denominator
    cutoff_gap = scaled_eta - ETA0
    monotone_lower_bound = old_quotient / C
    if not (cutoff_gap > 0 and quotient >= monotone_lower_bound > 1):
        raise ArithmeticError("exact monotone dilation lower bound failed")

    return {
        "status": "exact-full-simplex-dilation-search-proxy",
        "rigorous_arithmetic": True,
        "analytic_support_approved": False,
        "theorem_ready": False,
        "k": K,
        "degree": DEGREE,
        "basis_dimension": len(basis),
        "source_hashes": dict(PINNED),
        "script_sha256": sha256(FILE),
        "parameters": {
            "alpha0": format_q(ALPHA0), "eta0": format_q(ETA0),
            "alpha1": format_q(ALPHA1), "eta1": format_q(ETA1),
            "c_alpha0_over_alpha1": format_q(C),
            "scaled_source_cutoff_c_eta1": format_q(scaled_eta),
        },
        "coefficient_map": (
            "theta_(a,lambda) contributes theta*binom(a,b)*"
            "(1-c)^(a-b)*c^(b+|lambda|) to (b,lambda), 0<=b<=a"),
        "transformed_rational_vector": [format_q(x) for x in transformed],
        "marginal_term_count": len(marginal),
        "squared_marginal_term_count": len(squared),
        "squared_marginal_terms_sha256": canonical_term_hash(squared),
        "source_numerator_reconstruction": {
            "48J": format_q(K * reconstructed_old_j),
            "matches_certificate_exactly": True,
        },
        "monotonicity_certificate": {
            "scaled_cutoff_minus_eta0": format_q(cutoff_gap),
            "square_integrand_nonnegative": True,
            "exact_quotient_lower_bound": format_q(monotone_lower_bound),
            "exact_lower_bound_minus_one": format_q(
                monotone_lower_bound - 1),
            "actual_quotient_minus_lower_bound": format_q(
                quotient - monotone_lower_bound),
        },
        "inner_alpha0_wide_eta_block": {
            "description": (
                "The transformed polynomial on sum(t)<=alpha0, with shared "
                "J cutoff eta1; exact inner block for a future inner/shell "
                "amplitude pencil."),
            "alpha": format_q(ALPHA0),
            "eta": format_q(ETA1),
            "denominator": format_q(inner_denominator),
            "numerator_48J": format_q(inner_numerator),
            "margin_48J_minus_I": format_q(
                inner_numerator - inner_denominator),
            "quotient": format_q(inner_quotient),
            "quotient_decimal_90": decimal_string(inner_quotient),
            "shortfall_to_one": format_q(1 - inner_quotient),
            "shortfall_decimal_90": decimal_string(1 - inner_quotient),
            "quotient_greater_than_one": False,
            "basis_square_term_count": len(transformed_square),
            "marginal_term_count": len(inner_marginal),
            "marginal_square_term_count": len(inner_marginal_square),
        },
        "exact_forms": {
            "denominator": format_q(new_denominator),
            "numerator_48J": format_q(new_numerator),
            "margin_48J_minus_I": format_q(margin),
            "quotient": format_q(quotient),
            "quotient_decimal_90": decimal_string(quotient),
            "margin_positive": margin > 0,
            "quotient_greater_than_one": quotient > 1,
        },
        "change_of_variables": {
            "I_new": "c^(-48)*I_old",
            "J_new": "c^(-49)*J_old_with_shared_cutoff_c*eta1",
            "quotient_new": (
                "c^(-1)*48*J_old(c*eta1)/I_old"),
        },
        "scope": (
            "Exact arithmetic for a full-simplex search proxy only. The "
            "larger support has not been shown to satisfy Proposition 1, so "
            "q>1 here is neither a bounded-gap theorem nor an upper bound for "
            "an analytically valid finite space."),
        "wall_seconds": time.monotonic() - started,
    }


def canonical_json(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"),
                       allow_nan=False) + "\n").encode("ascii")


def publish_new(path, value):
    path = Path(path).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    encoded = canonical_json(value)
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(encoded)
        handle.flush()
        os.fsync(handle.fileno())
    if sha256(path) != sha256(encoded):
        raise RuntimeError("published dilation result changed")
    return sha256(encoded)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output")
    parser.add_argument("--progress", action="store_true")
    args = parser.parse_args()
    result = compute_proxy(progress=args.progress)
    if args.output:
        print(publish_new(args.output, result))
    else:
        print(canonical_json(result).decode("ascii"), end="")


if __name__ == "__main__":
    main()
