#!/usr/bin/env python3
"""Exact two-amplitude radial kink for the certified direct-BV polynomial.

Use a*F0 on sum(t)<=V and b*F0 on V<sum(t)<R.  The I form is diagonal.
For J, the distinguished-coordinate marginal is

  a M_V + b (M_R-M_V),

so all entries follow from three exact marginal norms on the common
(k-1)-simplex of radius V.
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
from scan_bv_epsilon_fixed import marginal_polynomial, square_orbit_polynomial


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def recenter_at(poly, alpha, center):
    """Rewrite P_lam*(alpha-U)^p in powers of center-U."""
    out = defaultdict(Q)
    for (power, lam), coefficient in poly.items():
        for d in range(power + 1):
            out[(d, lam)] += (coefficient * math.comb(power, d) *
                              ((alpha - center) ** (power - d)))
    return {key: value for key, value in out.items() if value}


def subtract(left, right):
    out = defaultdict(Q, left)
    for key, value in right.items():
        out[key] -= value
    return {key: value for key, value in out.items() if value}


def marginal_norm(poly, common_support):
    square = square_orbit_polynomial(poly)
    value = sum(coefficient *
                ei.orbit_size(common_support.k, nu) *
                common_support.canonical_support_residual(nu, power)
                for (power, nu), coefficient in square.items())
    return value, len(square)


def max_2d(A0, A1, B00, B01, B11, precision):
    if A0 <= 0 or A1 <= 0:
        raise ArithmeticError("nonpositive radial I block")
    c2 = A0 * A1
    c1 = -(B00 * A1 + B11 * A0)
    c0 = B00 * B11 - B01 * B01
    disc = c1 * c1 - 4 * c2 * c0
    if disc < 0:
        raise ArithmeticError("negative 2x2 discriminant")
    with localcontext() as ctx:
        ctx.prec = precision

        def dec(x):
            return Decimal(x.numerator) / Decimal(x.denominator)

        eigenvalue = (-dec(c1) + dec(disc).sqrt()) / (2 * dec(c2))
        if B01:
            ratio = (eigenvalue * dec(A0) - dec(B00)) / dec(B01)
        elif dec(B00) / dec(A0) >= dec(B11) / dec(A1):
            ratio = Decimal(0)
        else:
            # a=0,b=1 cannot be represented by finite b/a; signal separately.
            ratio = Decimal("Infinity")
        return str(eigenvalue), ratio


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("certificate", type=Path)
    ap.add_argument("--precision", type=int, default=140)
    ap.add_argument("--digits", type=int, default=45)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    if args.precision < 80 or args.digits < 20:
        ap.error("use precision>=80 and digits>=20")

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
        raise ValueError("two-amplitude preset requires a full simplex")
    basis = [(int(a), tuple(int(x) for x in lam))
             for a, lam in cert["basis"]]
    vector = [Q(x) for x in cert["rational_vector"]]
    original_I = Q(cert["exact_denominator"])
    original_kJ = Q(cert["exact_numerator"])

    # I on the inner simplex is a fresh exact scalar contraction of F0^2.
    f_terms = {(a, lam): coefficient
               for coefficient, (a, lam) in zip(vector, basis) if coefficient}
    f_square = square_orbit_polynomial(f_terms)
    inner_support = ei.OneStratumSupport(k, V, delta, V, V, V, V)
    inner_I = sum(coefficient * inner_support.orbit_support_moment(nu, power)
                  for (power, nu), coefficient in f_square.items())
    outer_I = original_I - inner_I

    # Both marginals are rewritten in powers of V-U before squaring.  This is
    # exactly the cross-upper-radius formula requested: R-U=(R-V)+(V-U).
    raw_R = marginal_polynomial(basis, vector, k, R)
    raw_V = marginal_polynomial(basis, vector, k, V)
    marginal_R = recenter_at(raw_R, R, V)
    marginal_V = recenter_at(raw_V, V, V)
    marginal_D = subtract(marginal_R, marginal_V)
    common = ei.OneStratumSupport(k - 1, V, delta, V, V, V, V)
    J_RR, terms_RR = marginal_norm(marginal_R, common)
    J_VV, terms_VV = marginal_norm(marginal_V, common)
    J_DD, terms_DD = marginal_norm(marginal_D, common)
    J_VD = (J_RR - J_VV - J_DD) / 2

    if k * J_RR != original_kJ:
        raise AssertionError("RR marginal failed exact baseline J reproduction")
    if inner_I <= 0 or outer_I <= 0:
        raise ArithmeticError("inner/outer I mass is not strictly positive")
    A0, A1 = inner_I, outer_I
    B00, B01, B11 = k * J_VV, k * J_VD, k * J_DD
    if A0 + A1 != original_I or B00 + 2 * B01 + B11 != original_kJ:
        raise AssertionError("amplitude (1,1) does not reproduce baseline forms")

    eigenvalue, ratio_dec = max_2d(A0, A1, B00, B01, B11, args.precision)
    if not ratio_dec.is_finite():
        rational_a, rational_b = Q(0), Q(1)
    else:
        rational_a = Q(1)
        rational_b = Q(format(ratio_dec, f".{args.digits}E"))
    denominator = rational_a * rational_a * A0 + rational_b * rational_b * A1
    numerator = (rational_a * rational_a * B00 +
                 2 * rational_a * rational_b * B01 +
                 rational_b * rational_b * B11)
    if denominator <= 0:
        raise ArithmeticError("rational amplitude denominator nonpositive")

    output = {
        "format": "direct-bv-radial-two-amplitude-exact-v1",
        "claim_scope": ("Exact particular piecewise-vector forms; Decimal "
                        "eigenvalue discovery is not itself a certificate."),
        "piecewise_function": "a*F0 for sum(t)<=V; b*F0 for V<sum(t)<R",
        "k": k, "R": str(R), "V": str(V),
        "integrator_sha256": source_hash,
        "script_sha256": sha(Path(__file__)),
        "certificate_sha256": hashlib.sha256(cert_bytes).hexdigest(),
        "basis_dimension": len(basis),
        "baseline_RR_J_exact_match": True,
        "baseline_amplitudes_11_exact_match": True,
        "I_matrix": [[str(A0), "0"], ["0", str(A1)]],
        "kJ_matrix": [[str(B00), str(B01)], [str(B01), str(B11)]],
        "marginal_term_counts": {
            "raw_R": len(raw_R), "raw_V": len(raw_V),
            "recentered_R": len(marginal_R),
            "recentered_V": len(marginal_V),
            "difference": len(marginal_D),
            "square_RR": terms_RR, "square_VV": terms_VV,
            "square_DD": terms_DD,
        },
        "decimal_precision": args.precision,
        "decimal_discovery_eigenvalue": eigenvalue,
        "rationalization_significant_digits": args.digits + 1,
        "rational_amplitudes": [str(rational_a), str(rational_b)],
        "exact_denominator": str(denominator),
        "exact_numerator": str(numerator),
        "exact_quotient": str(numerator / denominator),
        "exact_margin": str(numerator - denominator),
        "denominator_positive": denominator > 0,
        "margin_positive": numerator > denominator,
        "exact_quotient_decimal": format(float(numerator / denominator), ".17g"),
        "baseline_quotient_decimal": format(float(original_kJ / original_I), ".17g"),
        "exact_gain_decimal": format(float(numerator / denominator -
                                                original_kJ / original_I), ".17g"),
        "inner_I_fraction_decimal": format(float(inner_I / original_I), ".17g"),
    }
    encoded = (json.dumps(output, sort_keys=True, separators=(",", ":")) + "\n").encode()
    args.output.write_bytes(encoded)
    print("inner_I_fraction", output["inner_I_fraction_decimal"])
    print("decimal_eigenvalue", eigenvalue)
    print("rational_amplitudes", output["rational_amplitudes"])
    print("exact_quotient", output["exact_quotient_decimal"])
    print("exact_gain", output["exact_gain_decimal"])
    print("margin_sign", "+" if numerator > denominator else "-")
    print("artifact_sha256", hashlib.sha256(encoded).hexdigest())


if __name__ == "__main__":
    main()
