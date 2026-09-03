#!/usr/bin/env python3
"""Exact uncapped two-band pencil for the naturally dilated BV polynomial.

Definition 5 assigns the inner/inner block the cutoff eta_1, while blocks
involving the outer band use eta_2.  Thus a one-band full-simplex quotient at
(alpha_2,eta_2) overcounts the inner/inner tail eta_1<U<eta_2.  This script
constructs the correct 2-by-2 pencil for

  F_a = F_dilated * (1_{S<alpha_1} + a 1_{alpha_1<S<alpha_2})

with *uncapped* simplexes.  Every displayed rational-vector contraction is
exact.  The outer full simplex is not analytically approved, so the result is
only a search relaxation and never a bounded-gaps certificate.
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
from functools import lru_cache
from pathlib import Path


FILE = Path(__file__).resolve()
REPO = FILE.parent.parent
sys.path[:0] = [str(FILE.parent),
                str(REPO / "agents" / "small-delta-frontier")]

import full_simplex_dilated_vector_proxy as dilation  # noqa: E402
import scan_bv_epsilon_fixed as scan  # noqa: E402


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@lru_cache(maxsize=None)
def two_residual_orbit(dimension, nu, p, q, alpha, beta, eta):
    """Integral P_nu(u)(alpha-U)^p(beta-U)^q over U<=eta."""
    if len(nu) > dimension:
        return Q(0)
    product = math.prod(math.factorial(x) for x in nu)
    total = sum(nu)
    canonical = Q(0)
    for d in range(p + 1):
        left = math.comb(p, d) * (alpha - eta) ** (p - d)
        for e in range(q + 1):
            radial = d + e
            degree = total + dimension + radial
            canonical += (left * math.comb(q, e) *
                          (beta - eta) ** (q - e) *
                          Q(product * math.factorial(radial),
                            math.factorial(degree)) * eta ** degree)
    return scan.ei.orbit_size(dimension, nu) * canonical


def marginal_cross(k, left, right, alpha, beta, eta):
    answer = Q(0)
    products = 0
    for (p, lam), x in left.items():
        for (q, mu), y in right.items():
            if not x or not y:
                continue
            for nu, multiplicity in scan.ei.multiply_monomial_orbits(lam, mu):
                answer += (x * y * multiplicity *
                           two_residual_orbit(k - 1, nu, p, q,
                                              alpha, beta, eta))
                products += 1
    return answer, products


def exact_quotient(a00, a11, b00, b01, b11, amplitude):
    denominator = a00 + amplitude * amplitude * a11
    numerator = b00 + 2 * amplitude * b01 + amplitude * amplitude * b11
    if denominator <= 0:
        raise ArithmeticError("nonpositive exact denominator")
    return denominator, numerator, numerator / denominator


def stationary_amplitude(a00, a11, b00, b01, b11, precision=100):
    """Positive stationary root, used only to choose a rational amplitude."""
    with localcontext() as context:
        context.prec = precision
        dec = lambda x: Decimal(x.numerator) / Decimal(x.denominator)
        aa = dec(a11 * b01)
        bb = dec(a11 * b00 - b11 * a00)
        cc = -dec(b01 * a00)
        discriminant = bb * bb - 4 * aa * cc
        if discriminant <= 0 or aa == 0:
            raise ArithmeticError("unexpected stationary quadratic")
        roots = [(-bb + discriminant.sqrt()) / (2 * aa),
                 (-bb - discriminant.sqrt()) / (2 * aa)]
        candidates = [x for x in roots if x > 0]
        if not candidates:
            raise ArithmeticError("no positive stationary amplitude")
        return max(candidates)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("certificate", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    scan.self_test()

    certificate_bytes = args.certificate.read_bytes()
    certificate = json.loads(certificate_bytes)
    k = int(certificate["k"])
    if k != 48:
        raise ValueError("expected k=48")
    basis = [(int(a), tuple(int(x) for x in lam))
             for a, lam in certificate["basis"]]
    source = [Q(x) for x in certificate["rational_vector"]]
    alpha1, eta1 = Q(103, 400), Q(97, 400)
    alpha2, eta2 = Q(3211, 12000), Q(3031, 12000)
    delta = Q(361, 50000)
    c = alpha1 / alpha2
    vector = dilation.dilate_vector(basis, source, c)

    a00, b00, *_ = scan.direct_forms(
        k, basis, vector, alpha1, eta1, delta)
    a00_check, b00_eta2, *_ = scan.direct_forms(
        k, basis, vector, alpha1, eta2, delta)
    a02, b22_total, *_ = scan.direct_forms(
        k, basis, vector, alpha2, eta2, delta)
    if a00 != a00_check or not 0 < a00 < a02:
        raise AssertionError("simplex denominator nesting failed")
    a11 = a02 - a00

    m1 = scan.marginal_polynomial(basis, vector, k, alpha1)
    m2 = scan.marginal_polynomial(basis, vector, k, alpha2)
    cross, products = marginal_cross(k, m1, m2, alpha1, alpha2, eta2)
    self1, self_products = marginal_cross(
        k, m1, m1, alpha1, alpha1, eta2)
    if k * self1 != b00_eta2:
        raise AssertionError("independent marginal self-contraction failed")
    cross *= k
    b01 = cross - b00_eta2
    b11 = b22_total + b00_eta2 - 2 * cross
    if b11 <= 0:
        raise ArithmeticError("nonpositive exact outer self block")
    if b00 + 2 * b01 + b11 != b00 + b22_total - b00_eta2:
        raise AssertionError("Definition-5 tail subtraction identity failed")

    particular = exact_quotient(a00, a11, b00, b01, b11, Q(1))
    root100 = stationary_amplitude(a00, a11, b00, b01, b11, 100)
    root160 = stationary_amplitude(a00, a11, b00, b01, b11, 160)
    if abs(root160 - root100) > Decimal("1e-90"):
        raise ArithmeticError("stationary amplitude is precision-unstable")
    rational_amplitude = Q(format(root160, ".70E"))
    optimized = exact_quotient(
        a00, a11, b00, b01, b11, rational_amplitude)

    def contraction_row(name, amplitude, forms):
        denominator, numerator, quotient = forms
        return {
            "name": name,
            "outer_amplitude": str(amplitude),
            "exact_denominator": str(denominator),
            "exact_numerator": str(numerator),
            "exact_quotient": str(quotient),
            "exact_quotient_decimal": format(float(quotient), ".17g"),
            "exact_margin": str(numerator - denominator),
            "margin_positive": numerator > denominator,
        }

    output = {
        "format": "uncapped-two-band-dilated-pencil-v1",
        "status": "exact-search-relaxation",
        "rigorous_particular_forms": True,
        "analytic_support_approved": False,
        "theorem_ready": False,
        "never_implies": ["Proposition-1 support", "a capped-support bound",
                          "H1<=236"],
        "parameters": {"k": k, "alpha1": str(alpha1),
                       "eta1": str(eta1), "alpha2": str(alpha2),
                       "eta2": str(eta2), "delta": str(delta),
                       "dilation_c": str(c)},
        "certificate_sha256": sha(certificate_bytes),
        "script_sha256": sha(FILE.read_bytes()),
        "root_dilation_script_sha256": sha(
            (FILE.parent / "full_simplex_dilated_vector_proxy.py").read_bytes()),
        "integrator_sha256": scan.sha(
            REPO / "agents" / "exact-integrator" / "src" /
            "exact_integrator.py"),
        "basis_dimension": len(basis),
        "marginal_terms": {"inner": len(m1), "outer": len(m2),
                           "cross_products": products,
                           "self_test_products": self_products},
        "I_matrix": [[str(a00), "0"], ["0", str(a11)]],
        "kJ_matrix": [[str(b00), str(b01)],
                       [str(b01), str(b11)]],
        "inner_exact_quotient": str(b00 / a00),
        "one_band_eta2_quotient": str(b22_total / a02),
        "inner_tail_subtracted_from_one_band_numerator": str(
            b00_eta2 - b00),
        "stationary_amplitude_decimal_100": str(root100),
        "stationary_amplitude_decimal_160": str(root160),
        "rows": [contraction_row("unit_outer_amplitude", Q(1), particular),
                 contraction_row("rationalized_stationary_amplitude",
                                 rational_amplitude, optimized)],
    }
    encoded = (json.dumps(output, sort_keys=True, separators=(",", ":")) +
               "\n").encode("ascii")
    args.output.write_bytes(encoded)
    for row in output["rows"]:
        print(row["name"], row["exact_quotient_decimal"],
              "+" if row["margin_positive"] else "-")
    print("inner", format(float(b00 / a00), ".17g"))
    print("sha256", sha(encoded))


if __name__ == "__main__":
    main()
