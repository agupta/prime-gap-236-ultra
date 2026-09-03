#!/usr/bin/env python3
"""Independent exact Definition-5 two-band dilation search proxy.

The outer simplex is deliberately uncapped and analytically unapproved.  The
calculation is useful only for measuring how much a later cap may remove.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from decimal import Decimal, localcontext
from fractions import Fraction as Q
from functools import lru_cache
import hashlib
import json
from math import comb, factorial, isfinite
import os
from pathlib import Path
import sys
import time


FILE = Path(__file__).resolve()
REPO = FILE.parents[3]
EI = REPO / "agents/exact-integrator/src/exact_integrator.py"
CERT = REPO / "agents/small-delta-frontier/bv_aquarter_B16_vector_exact.json"
ROOT_SCRIPT = REPO / "scripts/full_simplex_two_band_dilated_pencil.py"
ROOT_RESULT = REPO / "results/wide_c722_D16_dilated_uncapped_two_band_pencil_exact.json"
ONE_BAND_RESULT = REPO / (
    "agents/structural-basis/results/"
    "bv_D16_dilation_alpha3211_fullsimplex_exact_v2_frozen.json")

PINNED = {
    "agents/exact-integrator/src/exact_integrator.py":
        "941ee82bc72fd8488a95eb5e536fe47f8c95d39a1b618dae7d6ef7eb27122e52",
    "agents/small-delta-frontier/bv_aquarter_B16_vector_exact.json":
        "59715ddffa483c696c035634a81c3cc8ffe882e9d6eaceec74bea23996b72d62",
    "scripts/full_simplex_two_band_dilated_pencil.py":
        "85c4847c4803015d9aa14f67d257be62a4d23edbff5843f191e903ce885d4804",
    "results/wide_c722_D16_dilated_uncapped_two_band_pencil_exact.json":
        "9a75380bb2f168adbae70751b6ca04ef9372892fa34c2f66bb0a1a05d59d3d7d",
    "agents/structural-basis/code/bv_dilation_fullsimplex_proxy_v2.py":
        "890f0ca43b24a592a33b95dc0cb3a8b853767b66d2a215f112f94f1652d571ce",
    "agents/structural-basis/results/bv_D16_dilation_alpha3211_fullsimplex_exact_v2_frozen.json":
        "34966e5e2161ed49c32de12e51f78d90ac196899ccb3a82d37a011d22192ba7f",
}

sys.path.insert(0, str(EI.parent))
import exact_integrator as exact  # noqa: E402


K = 48
ALPHA_INNER = Q(103, 400)
ETA_INNER = Q(97, 400)
ALPHA_OUTER = Q(3211, 12000)
ETA_OUTER = Q(3031, 12000)
C = ALPHA_INNER / ALPHA_OUTER


def sha256(value):
    data = value if isinstance(value, bytes) else Path(value).read_bytes()
    return hashlib.sha256(data).hexdigest()


def format_q(value):
    value = Q(value)
    return (str(value.numerator) if value.denominator == 1 else
            f"{value.numerator}/{value.denominator}")


def parse_q(value):
    if not isinstance(value, str):
        raise TypeError("rational must be a string")
    answer = Q(value)
    if format_q(answer) != value:
        raise ValueError("noncanonical rational")
    return answer


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
                          ValueError(f"nonfinite token {token}")))


def validate_sources():
    for relative, digest in PINNED.items():
        if sha256(REPO / relative) != digest:
            raise ValueError(f"two-band proxy input changed: {relative}")
    if (Path(exact.__file__).resolve() != EI.resolve() or
            sha256(Path(exact.__file__).resolve()) != PINNED[
                "agents/exact-integrator/src/exact_integrator.py"]):
        raise ValueError("wrong exact_integrator module")


def load_source_vector():
    validate_sources()
    cert = strict_json(CERT)
    basis = [(a, tuple(lam)) for a, lam in cert.get("basis", ())]
    vector = [parse_q(value)
              for value in cert.get("rational_vector", ())]
    if (cert.get("k") != K or cert.get("degree") != 16 or
            basis != exact.even_basis(16) or len(vector) != 307 or
            cert.get("parameters") != {
                "alpha": "103/400", "delta": "7/250", "eta": "97/400",
                "beta1": "103/400", "beta2": "103/400",
                "beta3plus": "103/400"}):
        raise ValueError("source certificate schema changed")
    return cert, basis, vector


def dilate(basis, vector):
    index = {label: position for position, label in enumerate(basis)}
    if len(index) != len(basis):
        raise ValueError("duplicate basis")
    answer = [Q(0)] * len(basis)
    for theta, (a, lam) in zip(vector, basis):
        for b in range(a + 1):
            position = index.get((b, lam))
            if position is None:
                raise ValueError("dilation leaves finite basis")
            answer[position] += (
                theta * comb(a, b) * (1 - C) ** (a - b) *
                C ** (b + sum(lam)))
    return answer


def split_distinguished(lam, k):
    answer = []
    if len(lam) < k:
        answer.append((0, lam))
    for exponent in sorted(set(lam)):
        rest = list(lam)
        rest.remove(exponent)
        answer.append((exponent, tuple(rest)))
    return answer


def marginal(basis, vector, alpha):
    answer = defaultdict(Q)
    for theta, (a, lam) in zip(vector, basis):
        for exponent, rest in split_distinguished(lam, K):
            for j in range(a + 1):
                answer[(exponent + j + 1, rest)] += (
                    theta * comb(a, j) * (1 - alpha) ** (a - j) *
                    Q(factorial(exponent) * factorial(j),
                      factorial(exponent + j + 1)))
    return {key: value for key, value in answer.items() if value}


def orbit_product_terms(left, right, symmetric=False):
    """Multiply residual-orbit polynomials, preserving left/right powers."""
    left_items = sorted(left.items())
    right_items = sorted(right.items())
    answer = defaultdict(Q)
    if symmetric:
        if left != right:
            raise ValueError("symmetric product requires identical inputs")
        for i, ((p, lam), x) in enumerate(left_items):
            for j in range(i + 1):
                (q, mu), y = left_items[j]
                factor = 1 if i == j else 2
                for nu, multiplicity in exact.multiply_monomial_orbits(
                        lam, mu):
                    answer[(p, q, nu)] += factor * x * y * multiplicity
    else:
        for (p, lam), x in left_items:
            for (q, mu), y in right_items:
                for nu, multiplicity in exact.multiply_monomial_orbits(
                        lam, mu):
                    answer[(p, q, nu)] += x * y * multiplicity
    return {key: value for key, value in answer.items() if value}


@lru_cache(maxsize=None)
def two_residual_moment(dimension, nu, p, q, alpha, beta, eta):
    """Integral P_nu(U)(alpha-U)^p(beta-U)^q for U<=eta."""
    if len(nu) > dimension:
        return Q(0)
    if not Q(0) < eta <= min(alpha, beta):
        raise ValueError("invalid cross-moment cutoff")
    angular = 1
    for exponent in nu:
        angular *= factorial(exponent)
    total_degree = sum(nu)
    canonical = Q(0)
    for d in range(p + 1):
        for e in range(q + 1):
            radial = d + e
            degree = total_degree + dimension + radial
            canonical += (
                comb(p, d) * (alpha - eta) ** (p - d) *
                comb(q, e) * (beta - eta) ** (q - e) *
                Q(angular * factorial(radial), factorial(degree)) *
                eta ** degree)
    return exact.orbit_size(dimension, nu) * canonical


def integrate_product(terms, dimension, alpha, beta, eta):
    return sum(
        coefficient * two_residual_moment(
            dimension, nu, p, q, alpha, beta, eta)
        for (p, q, nu), coefficient in terms.items())


def basis_square(basis, vector):
    raw = {(a, lam): theta
           for theta, (a, lam) in zip(vector, basis) if theta}
    return orbit_product_terms(raw, raw, symmetric=True)


def decimal_q(value, precision=90):
    with localcontext() as context:
        context.prec = precision
        return str(Decimal(value.numerator) / Decimal(value.denominator))


def exact_row(name, amplitude, a00, a11, b00, b01, b11):
    denominator = a00 + amplitude * amplitude * a11
    numerator = b00 + 2 * amplitude * b01 + amplitude * amplitude * b11
    quotient = numerator / denominator
    return {
        "name": name,
        "outer_amplitude": format_q(amplitude),
        "denominator": format_q(denominator),
        "numerator_48J": format_q(numerator),
        "margin_48J_minus_I": format_q(numerator - denominator),
        "quotient": format_q(quotient),
        "quotient_decimal_90": decimal_q(quotient),
        "margin_positive": numerator > denominator,
    }


def stationary_amplitude(a00, a11, b00, b01, b11, precision):
    with localcontext() as context:
        context.prec = precision
        dec = lambda x: Decimal(x.numerator) / Decimal(x.denominator)
        aa = dec(a11 * b01)
        bb = dec(a11 * b00 - b11 * a00)
        cc = -dec(b01 * a00)
        discriminant = bb * bb - 4 * aa * cc
        if discriminant <= 0 or aa == 0:
            raise ArithmeticError("unexpected stationary discriminant")
        candidates = [(-bb + discriminant.sqrt()) / (2 * aa),
                      (-bb - discriminant.sqrt()) / (2 * aa)]
        candidates = [value for value in candidates if value > 0]
        if not candidates:
            raise ArithmeticError("no positive stationary amplitude")
        return max(candidates)


def compute(progress=False):
    started = time.monotonic()
    _, basis, source = load_source_vector()
    vector = dilate(basis, source)
    polynomial_square = basis_square(basis, vector)
    if progress:
        print(f"basis_square_terms={len(polynomial_square)}",
              file=sys.stderr, flush=True)
    a00 = integrate_product(polynomial_square, K, Q(1), Q(1), ALPHA_INNER)
    a02 = integrate_product(polynomial_square, K, Q(1), Q(1), ALPHA_OUTER)
    a11 = a02 - a00
    if not (a00 > 0 and a11 > 0):
        raise ArithmeticError("nonpositive disjoint denominator block")

    m1 = marginal(basis, vector, ALPHA_INNER)
    m2 = marginal(basis, vector, ALPHA_OUTER)
    m11 = orbit_product_terms(m1, m1, symmetric=True)
    m22 = orbit_product_terms(m2, m2, symmetric=True)
    m12 = orbit_product_terms(m1, m2, symmetric=False)
    if progress:
        print(f"marginal_product_terms={len(m11)},{len(m22)},{len(m12)}",
              file=sys.stderr, flush=True)

    b00 = K * integrate_product(
        m11, K - 1, ALPHA_INNER, ALPHA_INNER, ETA_INNER)
    b00_eta2 = K * integrate_product(
        m11, K - 1, ALPHA_INNER, ALPHA_INNER, ETA_OUTER)
    b22_total = K * integrate_product(
        m22, K - 1, ALPHA_OUTER, ALPHA_OUTER, ETA_OUTER)
    cross_total = K * integrate_product(
        m12, K - 1, ALPHA_INNER, ALPHA_OUTER, ETA_OUTER)
    b01 = cross_total - b00_eta2
    b11 = b22_total + b00_eta2 - 2 * cross_total
    if b11 <= 0:
        raise ArithmeticError("nonpositive outer marginal self block")

    root100 = stationary_amplitude(a00, a11, b00, b01, b11, 100)
    root160 = stationary_amplitude(a00, a11, b00, b01, b11, 160)
    if abs(root160 - root100) > Decimal("1e-90"):
        raise ArithmeticError("stationary root precision mismatch")
    amplitude = Q(format(root160, ".70E"))
    unit = exact_row("unit_outer_amplitude", Q(1),
                     a00, a11, b00, b01, b11)
    optimized = exact_row("rationalized_stationary_amplitude", amplitude,
                          a00, a11, b00, b01, b11)
    if unit["margin_positive"] or optimized["margin_positive"]:
        raise ArithmeticError("two-band relaxation sign unexpectedly changed")

    root = strict_json(ROOT_RESULT)
    root_a = [[parse_q(value) for value in row]
              for row in root.get("I_matrix", ())]
    root_b = [[parse_q(value) for value in row]
              for row in root.get("kJ_matrix", ())]
    if (root_a != [[a00, Q(0)], [Q(0), a11]] or
            root_b != [[b00, b01], [b01, b11]] or
            root.get("script_sha256") != PINNED[
                "scripts/full_simplex_two_band_dilated_pencil.py"] or
            root.get("certificate_sha256") != PINNED[
                "agents/small-delta-frontier/bv_aquarter_B16_vector_exact.json"]):
        raise ArithmeticError("independent two-band matrix differs from root")
    root_rows = {row["name"]: row for row in root.get("rows", ())}
    for ours in (unit, optimized):
        theirs = root_rows.get(ours["name"])
        if (not isinstance(theirs, dict) or
                parse_q(theirs.get("outer_amplitude")) !=
                parse_q(ours["outer_amplitude"]) or
                parse_q(theirs.get("exact_denominator")) !=
                parse_q(ours["denominator"]) or
                parse_q(theirs.get("exact_numerator")) !=
                parse_q(ours["numerator_48J"]) or
                parse_q(theirs.get("exact_quotient")) !=
                parse_q(ours["quotient"])):
            raise ArithmeticError("independent row differs from root")

    one_band = strict_json(ONE_BAND_RESULT)
    one_band_q = parse_q(one_band["exact_forms"]["quotient"])
    inner_wide_q = parse_q(
        one_band["inner_alpha0_wide_eta_block"]["quotient"])
    if (one_band_q != b22_total / a02 or
            inner_wide_q != b00_eta2 / a00):
        raise ArithmeticError("one-band component rows disagree")

    inner_q = b00 / a00
    tail = b00_eta2 - b00
    if not (tail > 0 and inner_q < inner_wide_q < 1 < one_band_q):
        raise ArithmeticError("Definition-5 cutoff ordering failed")

    return {
        "status": "exact-Definition5-two-band-dilation-search-proxy-v2",
        "rigorous_arithmetic": True,
        "analytic_support_approved": False,
        "theorem_ready": False,
        "source_hashes": dict(PINNED),
        "script_sha256": sha256(FILE),
        "parameters": {
            "k": K, "alpha_inner": format_q(ALPHA_INNER),
            "eta_inner": format_q(ETA_INNER),
            "alpha_outer": format_q(ALPHA_OUTER),
            "eta_outer": format_q(ETA_OUTER),
            "dilation_c": format_q(C),
        },
        "basis_dimension": len(basis),
        "transformed_vector_sha256": sha256(
            (json.dumps([format_q(x) for x in vector],
                        separators=(",", ":")) + "\n").encode("ascii")),
        "term_counts": {
            "basis_square": len(polynomial_square),
            "inner_marginal": len(m1), "outer_marginal": len(m2),
            "inner_self_product": len(m11),
            "outer_self_product": len(m22),
            "inner_outer_product": len(m12),
        },
        "I_matrix": [[format_q(a00), "0"], ["0", format_q(a11)]],
        "kJ_matrix": [[format_q(b00), format_q(b01)],
                       [format_q(b01), format_q(b11)]],
        "cutoff_diagnostics": {
            "Definition5_inner_48J": format_q(b00),
            "incorrect_wide_cutoff_inner_48J": format_q(b00_eta2),
            "subtracted_inner_tail_48J": format_q(tail),
            "Definition5_inner_quotient": format_q(inner_q),
            "Definition5_inner_quotient_decimal_90": decimal_q(inner_q),
            "wide_cutoff_inner_quotient": format_q(inner_wide_q),
            "wide_cutoff_inner_quotient_decimal_90": decimal_q(inner_wide_q),
            "uncapped_one_band_outer_quotient": format_q(one_band_q),
            "uncapped_one_band_outer_quotient_decimal_90": decimal_q(one_band_q),
        },
        "stationary_amplitude_decimal_100": str(root100),
        "stationary_amplitude_decimal_160": str(root160),
        "rows": [unit, optimized],
        "best_exact_shortfall_to_one": format_q(
            1 - parse_q(optimized["quotient"])),
        "best_shortfall_decimal_90": decimal_q(
            1 - parse_q(optimized["quotient"])),
        "root_matrix_and_rows_match_exactly": True,
        "scope": (
            "Exact uncapped two-band search relaxation. The outer simplex "
            "has no analytic Proposition-1 approval; this is not a capped "
            "quotient, theorem, or finite-space upper bound."),
        "wall_seconds": time.monotonic() - started,
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
        raise RuntimeError("two-band output changed after publication")
    return sha256(encoded)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output")
    parser.add_argument("--progress", action="store_true")
    args = parser.parse_args()
    result = compute(progress=args.progress)
    if args.output:
        print(publish_new(args.output, result))
    else:
        print(canonical_json(result).decode("ascii"), end="")


if __name__ == "__main__":
    main()
