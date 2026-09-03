#!/usr/bin/env python3
"""Exact uncapped Definition-5 pencil with separate band dilations.

The inner coordinate is F_0(c_inner t) on S<alpha_1.  The outer coordinate
is F_0(c_outer t) on alpha_1<S<alpha_2.  Definition 5 uses eta_1 for the
inner/inner block and eta_2 for every block involving the outer band.

The outer simplex is uncapped and analytically unapproved.  Output is an
exact finite-form search point, never a Proposition-1 certificate.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from fractions import Fraction as Q
from pathlib import Path


FILE = Path(__file__).resolve()
REPO = FILE.parent.parent
sys.path[:0] = [str(FILE.parent),
                str(REPO / "agents" / "small-delta-frontier")]

import full_simplex_dilated_vector_proxy as dilation  # noqa: E402
import full_simplex_two_band_dilated_pencil as pencil  # noqa: E402
import scan_bv_epsilon_fixed as scan  # noqa: E402


PINNED_PENCIL_SHA256 = \
    "85c4847c4803015d9aa14f67d257be62a4d23edbff5843f191e903ce885d4804"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("certificate", type=Path)
    parser.add_argument("--inner-c", type=Q, required=True)
    parser.add_argument("--outer-c", type=Q, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if sha((FILE.parent / "full_simplex_two_band_dilated_pencil.py").read_bytes()) \
            != PINNED_PENCIL_SHA256:
        raise RuntimeError("frozen two-band arithmetic changed")
    if not (Q(9, 10) < args.inner_c <= Q(1) and
            Q(9, 10) < args.outer_c <= Q(1)):
        parser.error("require 9/10<c_inner,c_outer<=1")

    certificate_bytes = args.certificate.read_bytes()
    raw = json.loads(certificate_bytes)
    k = int(raw["k"])
    if k != 48:
        raise ValueError("expected k=48")
    basis = [(int(a), tuple(int(x) for x in lam)) for a, lam in raw["basis"]]
    source = [Q(x) for x in raw["rational_vector"]]
    inner = dilation.dilate_vector(basis, source, args.inner_c)
    outer = dilation.dilate_vector(basis, source, args.outer_c)
    alpha1, eta1 = Q(103, 400), Q(97, 400)
    alpha2, eta2 = Q(3211, 12000), Q(3031, 12000)
    delta = Q(361, 50000)

    a00, b00, *_ = scan.direct_forms(
        k, basis, inner, alpha1, eta1, delta)
    ao1, bo1, *_ = scan.direct_forms(
        k, basis, outer, alpha1, eta2, delta)
    ao2, bo2, *_ = scan.direct_forms(
        k, basis, outer, alpha2, eta2, delta)
    a11 = ao2 - ao1
    if not (a00 > 0 and a11 > 0):
        raise ArithmeticError("nonpositive exact I block")

    mi = scan.marginal_polynomial(basis, inner, k, alpha1)
    mo1 = scan.marginal_polynomial(basis, outer, k, alpha1)
    mo2 = scan.marginal_polynomial(basis, outer, k, alpha2)
    ci2, n_ci2 = pencil.marginal_cross(
        k, mi, mo2, alpha1, alpha2, eta2)
    ci1, n_ci1 = pencil.marginal_cross(
        k, mi, mo1, alpha1, alpha1, eta2)
    co12, n_co12 = pencil.marginal_cross(
        k, mo1, mo2, alpha1, alpha2, eta2)
    b01 = k * (ci2 - ci1)
    b11 = bo2 + bo1 - 2 * k * co12
    if b11 <= 0:
        raise ArithmeticError("nonpositive exact outer J block")

    unit = pencil.exact_quotient(a00, a11, b00, b01, b11, Q(1))
    stationary = pencil.stationary_amplitude(
        a00, a11, b00, b01, b11, 150)
    amplitude = Q(format(stationary, ".70E"))
    optimized = pencil.exact_quotient(
        a00, a11, b00, b01, b11, amplitude)

    def row(name, a, forms):
        denominator, numerator, quotient = forms
        return {"name": name, "outer_amplitude": str(a),
                "exact_denominator": str(denominator),
                "exact_numerator": str(numerator),
                "exact_quotient": str(quotient),
                "exact_quotient_decimal": format(float(quotient), ".17g"),
                "exact_margin": str(numerator - denominator),
                "margin_positive": numerator > denominator}

    output = {
        "format": "exact-uncapped-two-band-piecewise-dilations-v1",
        "status": "exact-search-point",
        "analytic_support_approved": False,
        "theorem_ready": False,
        "never_implies": ["Proposition-1 support", "a capped-support bound",
                          "H1<=236"],
        "parameters": {"k": k, "alpha1": str(alpha1),
                       "eta1": str(eta1), "alpha2": str(alpha2),
                       "eta2": str(eta2), "delta": str(delta),
                       "inner_c": str(args.inner_c),
                       "outer_c": str(args.outer_c)},
        "certificate_sha256": sha(certificate_bytes),
        "script_sha256": sha(FILE.read_bytes()),
        "pinned_two_band_script_sha256": PINNED_PENCIL_SHA256,
        "marginal_cross_products": {
            "inner_outer_high": n_ci2,
            "inner_outer_low": n_ci1,
            "outer_low_high": n_co12,
        },
        "I_matrix": [[str(a00), "0"], ["0", str(a11)]],
        "kJ_matrix": [[str(b00), str(b01)], [str(b01), str(b11)]],
        "inner_exact_quotient": str(b00 / a00),
        "stationary_amplitude_decimal": str(stationary),
        "rows": [row("unit", Q(1), unit),
                 row("rationalized_stationary", amplitude, optimized)],
    }
    encoded = (json.dumps(output, sort_keys=True, separators=(",", ":")) +
               "\n").encode("ascii")
    args.output.write_bytes(encoded)
    for item in output["rows"]:
        print(item["name"], item["exact_quotient_decimal"],
              "+" if item["margin_positive"] else "-")
    print("inner", format(float(b00 / a00), ".17g"))
    print("sha256", sha(encoded))


if __name__ == "__main__":
    main()
