#!/usr/bin/env python3
"""Independent exact audit of the frozen piecewise Definition-5 pencil.

The producer is never imported.  Exact matrix entries are reconstructed from
the frozen coefficient vector with the separately implemented orbit-integral
engine in ``bv_dilation_definition5_two_band_proxy_v2.py``.  The checker also
recontracts every serialized row and enforces the deliberately negative
uncapped/non-theorem scope.
"""

from __future__ import annotations

import argparse
from decimal import Decimal, localcontext
from fractions import Fraction as Q
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys


FILE = Path(__file__).resolve()
REPO = FILE.parents[2]
PRODUCER = "scripts/evaluate_two_band_piecewise_dilations.py"
RESULT = "results/wide_c722_D16_piecewise_cinner1_couter_natural_exact.json"
CERT = "agents/small-delta-frontier/bv_aquarter_B16_vector_exact.json"
ENGINE = (
    "agents/structural-basis/code/"
    "bv_dilation_definition5_two_band_proxy_v2.py")
ENGINE_RESULT = (
    "agents/structural-basis/results/"
    "bv_D16_dilation_Definition5_two_band_exact_v2.json")

PINNED = {
    PRODUCER:
        "f3bbc9c6c35e2cb8b1ac7ce6accf56144c01099be81dfe288407b4552165b7bb",
    RESULT:
        "e30a9a5f356b0303559bd1d3c1cb7a48474e973ec97b164c00832c919f761cb7",
    CERT:
        "59715ddffa483c696c035634a81c3cc8ffe882e9d6eaceec74bea23996b72d62",
    ENGINE:
        "0b322ed3b6ea45bfb4f6a7a57deebe34cc57f2a41df68f6f0a592c91dd848d95",
    ENGINE_RESULT:
        "05410084611a86d04877ebe2b73a17899e45915fdf1b9b466a25996d28db3171",
    "agents/exact-integrator/src/exact_integrator.py":
        "941ee82bc72fd8488a95eb5e536fe47f8c95d39a1b618dae7d6ef7eb27122e52",
    "agents/small-delta-frontier/scan_bv_epsilon_fixed.py":
        "96495079a18039a0a7b0522e83ac455cbe5ff144598fff6b382f2c2953958de9",
    "scripts/full_simplex_two_band_dilated_pencil.py":
        "85c4847c4803015d9aa14f67d257be62a4d23edbff5843f191e903ce885d4804",
    "scripts/full_simplex_dilated_vector_proxy.py":
        "3219047bd9d339e15946947f68bd6484d23af722337ba70771c488e3e1238794",
}

K = 48
ALPHA1, ETA1 = Q(103, 400), Q(97, 400)
ALPHA2, ETA2 = Q(3211, 12000), Q(3031, 12000)
OUTER_C = Q(3090, 3211)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ArithmeticError(message)


def strict_json(relative: str):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError(f"duplicate JSON key in {relative}: {key}")
            result[key] = value
        return result

    return json.loads(
        (REPO / relative).read_bytes(), object_pairs_hook=pairs,
        parse_constant=lambda token: (_ for _ in ()).throw(
            ValueError(f"nonfinite JSON token in {relative}: {token}")))


def q(value) -> Q:
    require(isinstance(value, str), "exact value must be a rational string")
    parsed = Q(value)
    rendered = (str(parsed.numerator) if parsed.denominator == 1 else
                f"{parsed.numerator}/{parsed.denominator}")
    require(rendered == value, "noncanonical rational string")
    return parsed


def decimal(value: Q, precision: int = 60) -> str:
    with localcontext() as context:
        context.prec = precision
        return str(Decimal(value.numerator) / Decimal(value.denominator))


def matrix(raw):
    require(isinstance(raw, list) and len(raw) == 2 and
            all(isinstance(row, list) and len(row) == 2 for row in raw),
            "expected exact 2x2 matrix")
    return [[q(value) for value in row] for row in raw]


def load_engine():
    path = REPO / ENGINE
    spec = importlib.util.spec_from_file_location(
        "audit_piecewise_independent_orbit_engine", path)
    require(spec is not None and spec.loader is not None,
            "cannot load independent engine")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    require(Path(module.__file__).resolve() == path.resolve(),
            "wrong independent engine imported")
    return module


def reconstruct(engine):
    """Rebuild I and 48J without importing the piecewise producer."""
    _, basis, inner = engine.load_source_vector()
    outer = engine.dilate(basis, inner)
    require(engine.C == OUTER_C, "independent dilation changed")

    inner_square = engine.basis_square(basis, inner)
    outer_square = engine.basis_square(basis, outer)
    a00 = engine.integrate_product(
        inner_square, K, Q(1), Q(1), ALPHA1)
    outer_low = engine.integrate_product(
        outer_square, K, Q(1), Q(1), ALPHA1)
    outer_high = engine.integrate_product(
        outer_square, K, Q(1), Q(1), ALPHA2)
    a11 = outer_high - outer_low

    mi = engine.marginal(basis, inner, ALPHA1)
    mo1 = engine.marginal(basis, outer, ALPHA1)
    mo2 = engine.marginal(basis, outer, ALPHA2)
    ii = engine.orbit_product_terms(mi, mi, symmetric=True)
    io1 = engine.orbit_product_terms(mi, mo1, symmetric=False)
    io2 = engine.orbit_product_terms(mi, mo2, symmetric=False)
    oo1 = engine.orbit_product_terms(mo1, mo1, symmetric=True)
    oo2 = engine.orbit_product_terms(mo2, mo2, symmetric=True)
    oo12 = engine.orbit_product_terms(mo1, mo2, symmetric=False)

    integrate = engine.integrate_product
    b00 = K * integrate(ii, K - 1, ALPHA1, ALPHA1, ETA1)
    ci1 = integrate(io1, K - 1, ALPHA1, ALPHA1, ETA2)
    ci2 = integrate(io2, K - 1, ALPHA1, ALPHA2, ETA2)
    b01 = K * (ci2 - ci1)
    bo1 = integrate(oo1, K - 1, ALPHA1, ALPHA1, ETA2)
    bo2 = integrate(oo2, K - 1, ALPHA2, ALPHA2, ETA2)
    co12 = integrate(oo12, K - 1, ALPHA1, ALPHA2, ETA2)
    b11 = K * (bo2 + bo1 - 2 * co12)

    require(a00 > 0 and a11 > 0 and b11 > 0,
            "nonpositive independently reconstructed block")
    return ([[a00, Q(0)], [Q(0), a11]],
            [[b00, b01], [b01, b11]], {
                "inner_square": len(inner_square),
                "outer_square": len(outer_square),
                "inner_marginal": len(mi),
                "outer_low_marginal": len(mo1),
                "outer_high_marginal": len(mo2),
                "inner_outer_low_product": len(io1),
                "inner_outer_high_product": len(io2),
                "outer_low_high_product": len(oo12),
            })


def contraction(a, b, amplitude):
    denominator = a[0][0] + amplitude * amplitude * a[1][1]
    numerator = (b[0][0] + 2 * amplitude * b[0][1] +
                 amplitude * amplitude * b[1][1])
    require(denominator > 0, "nonpositive contraction denominator")
    return denominator, numerator, numerator / denominator


def build():
    for relative, expected in PINNED.items():
        require(sha(REPO / relative) == expected,
                f"frozen piecewise input changed: {relative}")
    engine = load_engine()
    artifact = strict_json(RESULT)
    cert = strict_json(CERT)
    natural = strict_json(ENGINE_RESULT)

    expected_parameters = {
        "k": 48, "alpha1": "103/400", "eta1": "97/400",
        "alpha2": "3211/12000", "eta2": "3031/12000",
        "delta": "361/50000", "inner_c": "1",
        "outer_c": "3090/3211"}
    require(artifact.get("parameters") == expected_parameters,
            "piecewise parameters/cutoffs changed")
    require(ETA1 < ETA2 < ALPHA1 < ALPHA2 and
            OUTER_C == ALPHA1 / ALPHA2,
            "band/cutoff/dilation relation changed")
    require(artifact.get("certificate_sha256") == PINNED[CERT] and
            artifact.get("script_sha256") == PINNED[PRODUCER],
            "artifact provenance fields changed")

    a_serial, b_serial = matrix(artifact.get("I_matrix")), matrix(
        artifact.get("kJ_matrix"))
    a_exact, b_exact, term_counts = reconstruct(engine)
    require(a_serial == a_exact and b_serial == b_exact,
            "independent exact matrix differs from producer")
    require(a_exact[0][1] == a_exact[1][0] == 0 and
            b_exact[0][1] == b_exact[1][0],
            "matrix symmetry/diagonal-I structure changed")

    # c_inner=1 must preserve the original certified inner block exactly.
    require(a_exact[0][0] == q(cert["exact_denominator"]) and
            b_exact[0][0] == q(cert["exact_numerator"]) and
            q(artifact["inner_exact_quotient"]) ==
            b_exact[0][0] / a_exact[0][0],
            "c_inner=1 block does not reproduce the BV certificate")

    # The outer polynomial and outer band are exactly those of the separately
    # frozen natural-dilation pencil, even though its inner polynomial differs.
    natural_a, natural_b = matrix(natural["I_matrix"]), matrix(
        natural["kJ_matrix"])
    require(a_exact[1][1] == natural_a[1][1] and
            b_exact[1][1] == natural_b[1][1],
            "natural-dilation outer block changed")

    rows = artifact.get("rows")
    require(isinstance(rows, list) and len(rows) == 2 and
            [row.get("name") for row in rows] ==
            ["unit", "rationalized_stationary"],
            "piecewise row inventory changed")
    audited_rows = {}
    for row in rows:
        amplitude = q(row["outer_amplitude"])
        denominator, numerator, quotient = contraction(
            a_exact, b_exact, amplitude)
        require(denominator == q(row["exact_denominator"]) and
                numerator == q(row["exact_numerator"]) and
                quotient == q(row["exact_quotient"]) and
                numerator - denominator == q(row["exact_margin"]) and
                row.get("margin_positive") is (numerator > denominator),
                f"{row['name']} exact contraction changed")
        audited_rows[row["name"]] = {
            "outer_amplitude": str(amplitude),
            "quotient": str(quotient),
            "quotient_decimal_60": decimal(quotient),
            "margin_over_I": str(quotient - 1),
            "margin_over_I_decimal_60": decimal(quotient - 1),
        }

    # The amplitude need not be algebraic for certification, but independently
    # verify that the serialized rational is precisely the declared 70-digit
    # rationalization of the stable positive stationary root.
    root100 = engine.stationary_amplitude(
        a_exact[0][0], a_exact[1][1], b_exact[0][0], b_exact[0][1],
        b_exact[1][1], 100)
    root160 = engine.stationary_amplitude(
        a_exact[0][0], a_exact[1][1], b_exact[0][0], b_exact[0][1],
        b_exact[1][1], 160)
    require(abs(root160 - root100) <= Decimal("1e-90") and
            q(rows[1]["outer_amplitude"]) == Q(format(root160, ".70E")),
            "stationary-amplitude rationalization changed")
    require(q(rows[0]["exact_quotient"]) < 1 and
            q(rows[1]["exact_quotient"]) > 1,
            "expected unit failure / rational stationary success changed")

    # An exact indefinite test independently confirms that a real quotient
    # above one exists in this pencil; it does not rely on a decimal eigenvalue.
    d00 = b_exact[0][0] - a_exact[0][0]
    d11 = b_exact[1][1] - a_exact[1][1]
    det = d00 * d11 - b_exact[0][1] ** 2
    require(d00 < 0 and d11 < 0 and det < 0,
            "B-I signature no longer has exactly one positive direction")

    require(artifact.get("format") ==
            "exact-uncapped-two-band-piecewise-dilations-v1" and
            artifact.get("status") == "exact-search-point" and
            artifact.get("analytic_support_approved") is False and
            artifact.get("theorem_ready") is False,
            "negative scope flags changed")
    never = artifact.get("never_implies")
    require(isinstance(never, list) and
            set(never) >= {"Proposition-1 support", "a capped-support bound",
                           "H1<=236"},
            "negative theorem scope is incomplete")

    return {
        "status": "AUDIT PASS",
        "scope": "frozen exact uncapped piecewise Definition-5 2D pencil only",
        "checker_sha256": sha(FILE),
        "pinned": PINNED,
        "exact_checks": {
            "producer_not_imported": True,
            "independent_exact_matrix_reconstructed": True,
            "inner_c1_equals_original_certificate_block": True,
            "outer_block_equals_independent_natural_dilation_block": True,
            "inner_inner_cutoff": "97/400",
            "all_outer_involving_cutoffs": "3031/12000",
            "numerator_convention": "48J (factor 48 exactly once)",
            "B_minus_I_determinant_negative": True,
            "exact_positive_direction_exists": True,
            "stationary_root_stable_and_rationalized_at_70_digits": True,
            "term_counts": term_counts,
        },
        "rows": audited_rows,
        "decision": (
            "the rationalized piecewise vector exceeds one exactly in the "
            "uncapped search pencil; the outer simplex is analytically "
            "unapproved, so a capped-support contraction remains necessary"),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    payload = (json.dumps(build(), sort_keys=True, separators=(",", ":"),
                          allow_nan=False) + "\n").encode("ascii")
    if args.output is not None:
        target = args.output.resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                             0o644)
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    print(payload.decode("ascii"), end="")


if __name__ == "__main__":
    main()
