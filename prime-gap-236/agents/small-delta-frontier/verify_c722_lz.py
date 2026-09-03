#!/usr/bin/env python3
"""Fail-closed reconstruction checker for the C722 exact L,Z D2 vector.

This checker does not read or trust ``c722_lz_D2_exact.json``.  It imports the
recurrence/integration implementation, reconstructs both matrices from the
audited rational C722 parameters, and also contracts the vector through the
independent sum-first/square-second path.
"""

from __future__ import annotations

import argparse
import json
from fractions import Fraction as Q
from pathlib import Path

from exact_lz_integrator import LZMatrixBuilder, c722_support, self_test


HERE = Path(__file__).resolve().parent
DEFAULT_CERT = HERE / "c722_lz_D2_vector.json"


def require(cond: bool, message: str) -> None:
    if not cond:
        raise AssertionError(message)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("certificate", nargs="?", type=Path, default=DEFAULT_CERT)
    ap.add_argument("--skip-low-k-tests", action="store_true")
    args = ap.parse_args()
    if not args.skip_low_k_tests:
        self_test()

    raw = json.loads(args.certificate.read_text())
    require(raw.get("format") == "exact-lz-vector-v1", "wrong certificate format")
    require(raw.get("k") == 48, "certificate is not k=48")
    degree = raw.get("degree")
    require(degree in (2, 3, 4),
            "checker accepts only audited D=2, D=3, or D=4 certificates")

    support = c722_support(48)
    builder = LZMatrixBuilder(support, degree)
    labels = [tuple(x) for x in raw.get("labels", ())]
    require(tuple(labels) == builder.labels, "missing, extra, or reordered labels")
    coeff = tuple(Q(x) for x in raw.get("coefficients", ()))
    require(len(coeff) == len(builder.labels), "coefficient count mismatch")

    print(f"reconstructing exact C722 D{degree} matrices; no serialized entries are read")
    I, J = builder.matrices()
    den = builder.quadratic(I, coeff)
    jform = builder.quadratic(J, coeff)
    direct_i, direct_j = builder.direct_fixed_vector(coeff)
    require((den, jform) == (direct_i, direct_j),
            "matrix/direct fixed-vector contraction mismatch")
    require(den > 0, "I form is not positive")
    num = support.k * jform
    quotient = num / den
    gap = den - num

    require(den == Q(raw["I_form"]), "I form differs from certificate")
    require(jform == Q(raw["J_form"]), "J form differs from certificate")
    require(num == Q(raw["kJ_form"]), "kJ form differs from certificate")
    require(gap == Q(raw["I_minus_kJ"]), "I-kJ differs from certificate")
    require(quotient == Q(raw["quotient"]), "quotient differs from certificate")
    # This artifact is a rigorous baseline/shortfall, not a claimed H_1 proof.
    require(gap > 0 and quotient < 1, "expected a rigorously subcritical D2 vector")

    print(f"C722 EXACT LZ D{degree} AUDIT PASS")
    print("labels", len(labels), "active_strata", support.active_strata()[0],
          support.active_strata()[-1])
    print("matrix/direct bitwise", "PASS")
    print("quotient", quotient)
    print("quotient_decimal", format(float(quotient), ".17g"))
    print("shortfall_1_minus_q", 1 - quotient)


if __name__ == "__main__":
    main()
