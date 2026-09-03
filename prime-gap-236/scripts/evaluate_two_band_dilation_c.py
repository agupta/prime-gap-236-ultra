#!/usr/bin/env python3
"""Exact local search point for the Definition-5 two-band dilation parameter.

This discovery helper imports the frozen two-band arithmetic and evaluates one
rational c.  It omits the redundant marginal self-test performed by the frozen
baseline script, but independently checks the band recombination identity.
The outer band is uncapped and analytically unapproved; no output is a sieve
certificate.
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
    parser.add_argument("--c", type=Q, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if sha((FILE.parent / "full_simplex_two_band_dilated_pencil.py").read_bytes()) \
            != PINNED_PENCIL_SHA256:
        raise RuntimeError("frozen two-band arithmetic changed")
    if not Q(9, 10) < args.c <= Q(1):
        parser.error("require 9/10<c<=1")

    certificate_bytes = args.certificate.read_bytes()
    raw = json.loads(certificate_bytes)
    k = int(raw["k"])
    if k != 48:
        raise ValueError("expected k=48")
    basis = [(int(a), tuple(int(x) for x in lam)) for a, lam in raw["basis"]]
    source = [Q(x) for x in raw["rational_vector"]]
    vector = dilation.dilate_vector(basis, source, args.c)
    alpha1, eta1 = Q(103, 400), Q(97, 400)
    alpha2, eta2 = Q(3211, 12000), Q(3031, 12000)
    delta = Q(361, 50000)

    a00, b00, *_ = scan.direct_forms(k, basis, vector, alpha1, eta1, delta)
    a00_again, b00_eta2, *_ = scan.direct_forms(
        k, basis, vector, alpha1, eta2, delta)
    a02, b22_total, *_ = scan.direct_forms(
        k, basis, vector, alpha2, eta2, delta)
    if a00 != a00_again or not 0 < a00 < a02:
        raise AssertionError("denominator nesting failed")
    a11 = a02 - a00
    m1 = scan.marginal_polynomial(basis, vector, k, alpha1)
    m2 = scan.marginal_polynomial(basis, vector, k, alpha2)
    cross_j, product_count = pencil.marginal_cross(
        k, m1, m2, alpha1, alpha2, eta2)
    cross = k * cross_j
    b01 = cross - b00_eta2
    b11 = b22_total + b00_eta2 - 2 * cross
    if b11 <= 0:
        raise ArithmeticError("nonpositive outer self block")
    unit = pencil.exact_quotient(a00, a11, b00, b01, b11, Q(1))
    stationary = pencil.stationary_amplitude(
        a00, a11, b00, b01, b11, 140)
    amplitude = Q(format(stationary, ".60E"))
    optimized = pencil.exact_quotient(
        a00, a11, b00, b01, b11, amplitude)
    if unit[1] != b00 + b22_total - b00_eta2:
        raise AssertionError("Definition-5 recombination failed")

    def row(name, a, forms):
        denominator, numerator, quotient = forms
        return {"name": name, "outer_amplitude": str(a),
                "exact_denominator": str(denominator),
                "exact_numerator": str(numerator),
                "exact_quotient": str(quotient),
                "exact_quotient_decimal": format(float(quotient), ".17g"),
                "margin_positive": numerator > denominator}

    output = {
        "format": "exact-uncapped-two-band-dilation-c-search-point-v1",
        "status": "exact-search-point",
        "analytic_support_approved": False,
        "theorem_ready": False,
        "c": str(args.c),
        "certificate_sha256": sha(certificate_bytes),
        "script_sha256": sha(FILE.read_bytes()),
        "pinned_two_band_script_sha256": PINNED_PENCIL_SHA256,
        "marginal_cross_products": product_count,
        "I_matrix": [[str(a00), "0"], ["0", str(a11)]],
        "kJ_matrix": [[str(b00), str(b01)], [str(b01), str(b11)]],
        "rows": [row("unit", Q(1), unit),
                 row("rationalized_stationary", amplitude, optimized)],
    }
    encoded = (json.dumps(output, sort_keys=True, separators=(",", ":")) +
               "\n").encode("ascii")
    args.output.write_bytes(encoded)
    print("c", args.c, "unit", output["rows"][0]["exact_quotient_decimal"],
          "opt", output["rows"][1]["exact_quotient_decimal"],
          "+" if output["rows"][1]["margin_positive"] else "-")
    print("sha256", sha(encoded))


if __name__ == "__main__":
    main()
