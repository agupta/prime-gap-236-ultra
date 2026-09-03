#!/usr/bin/env python3
"""Independent exact audit of the frozen uncapped D18 piecewise pencil.

The producer is not imported.  We load only its frozen rational coefficient
vector and rebuild every 2-by-2 I and 48J entry with the independently
implemented orbit-moment engine previously used for the D16 cross-check.
This certifies an exact search relaxation, never the analytically unapproved
uncapped outer support.
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
RESULT = "results/wide_c722_B18_piecewise_cinner1_couter_natural_exact.json"
CERT = "agents/exact-integrator/results/aquarter_fullsimplex_k48_B18_refined_exact.json"
ENGINE = "agents/structural-basis/code/bv_dilation_definition5_two_band_proxy_v2.py"

PINS = {
    PRODUCER: "f3bbc9c6c35e2cb8b1ac7ce6accf56144c01099be81dfe288407b4552165b7bb",
    RESULT: "49ecca1b962d06a8ee793e7ce0a3dcdf4ef1fd38595ccd86c784950636d903fd",
    CERT: "af6f1eb0d75bc59caf20cc82f79a3cb339be3ac7280af2afcad89eca0e31cf58",
    ENGINE: "0b322ed3b6ea45bfb4f6a7a57deebe34cc57f2a41df68f6f0a592c91dd848d95",
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
        answer = {}
        for key, value in items:
            if key in answer:
                raise ValueError(f"duplicate JSON key in {relative}: {key}")
            answer[key] = value
        return answer

    return json.loads(
        (REPO / relative).read_bytes(), object_pairs_hook=pairs,
        parse_constant=lambda token: (_ for _ in ()).throw(
            ValueError(f"nonfinite JSON token in {relative}: {token}")))


def q(value) -> Q:
    require(isinstance(value, str), "exact value must be a rational string")
    result = Q(value)
    canonical = (str(result.numerator) if result.denominator == 1 else
                 f"{result.numerator}/{result.denominator}")
    require(value == canonical, "noncanonical exact rational")
    return result


def matrix(value):
    require(isinstance(value, list) and len(value) == 2 and
            all(isinstance(row, list) and len(row) == 2 for row in value),
            "expected exact 2-by-2 matrix")
    return [[q(entry) for entry in row] for row in value]


def decimal(value: Q, precision: int = 70) -> str:
    with localcontext() as context:
        context.prec = precision
        return str(Decimal(value.numerator) / Decimal(value.denominator))


def load_engine():
    path = REPO / ENGINE
    spec = importlib.util.spec_from_file_location(
        "audit_d18_independent_orbit_engine", path)
    require(spec is not None and spec.loader is not None,
            "cannot load independent orbit engine")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    require(Path(module.__file__).resolve() == path.resolve(),
            "wrong orbit engine imported")
    return module


def load_d18(engine):
    cert = strict_json(CERT)
    basis = [(int(a), tuple(int(x) for x in lam))
             for a, lam in cert.get("basis", ())]
    vector = [q(value) for value in cert.get("rational_vector", ())]
    require(cert.get("format") == "bv-even-exact-vector-v1" and
            cert.get("k") == K and cert.get("degree") == 18 and
            basis == engine.exact.even_basis(18) and
            len(basis) == len(vector) == 471 and
            cert.get("parameters") == {
                "alpha": "103/400", "delta": "7/250", "eta": "97/400",
                "beta1": "103/400", "beta2": "103/400",
                "beta3plus": "103/400"} and
            cert.get("particular_vector_forms_rigorous") is True and
            cert.get("denominator_positive") is True,
            "D18 certificate schema/basis changed")
    require(len(set(basis)) == len(basis) and any(vector),
            "D18 basis/vector malformed")
    return cert, basis, vector


def reconstruct(engine, basis, inner):
    """Rebuild I and 48J with explicit Definition-5 cutoffs."""
    require(engine.C == OUTER_C, "independent dilation constant changed")
    outer = engine.dilate(basis, inner)
    inner_square = engine.basis_square(basis, inner)
    outer_square = engine.basis_square(basis, outer)
    integrate = engine.integrate_product
    a00 = integrate(inner_square, K, Q(1), Q(1), ALPHA1)
    outer_low = integrate(outer_square, K, Q(1), Q(1), ALPHA1)
    outer_high = integrate(outer_square, K, Q(1), Q(1), ALPHA2)
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

    # Definition 5: eta1 occurs only in the inner/inner block.  Every term
    # touching the outer band uses eta2.  Each scalar below is raw J until the
    # single explicit multiplication by K.
    j00 = integrate(ii, K - 1, ALPHA1, ALPHA1, ETA1)
    ji1 = integrate(io1, K - 1, ALPHA1, ALPHA1, ETA2)
    ji2 = integrate(io2, K - 1, ALPHA1, ALPHA2, ETA2)
    jo1 = integrate(oo1, K - 1, ALPHA1, ALPHA1, ETA2)
    jo2 = integrate(oo2, K - 1, ALPHA2, ALPHA2, ETA2)
    jo12 = integrate(oo12, K - 1, ALPHA1, ALPHA2, ETA2)
    b00 = K * j00
    b01 = K * (ji2 - ji1)
    b11 = K * (jo2 + jo1 - 2 * jo12)
    require(a00 > 0 and a11 > 0 and b11 > 0,
            "nonpositive independently reconstructed block")
    return ([[a00, Q(0)], [Q(0), a11]],
            [[b00, b01], [b01, b11]], {
                "inner_square": len(inner_square),
                "outer_square": len(outer_square),
                "inner_marginal": len(mi),
                "outer_low_marginal": len(mo1),
                "outer_high_marginal": len(mo2),
                "inner_self_product": len(ii),
                "inner_outer_low_product": len(io1),
                "inner_outer_high_product": len(io2),
                "outer_low_self_product": len(oo1),
                "outer_high_self_product": len(oo2),
                "outer_low_high_product": len(oo12),
            })


def contraction(a, b, amplitude: Q):
    denominator = a[0][0] + amplitude * amplitude * a[1][1]
    numerator = (b[0][0] + 2 * amplitude * b[0][1] +
                 amplitude * amplitude * b[1][1])
    require(denominator > 0, "nonpositive contraction denominator")
    return denominator, numerator, numerator / denominator


def build():
    for relative, expected in PINS.items():
        require(sha(REPO / relative) == expected,
                f"frozen D18 input changed: {relative}")
    engine = load_engine()
    cert, basis, inner = load_d18(engine)
    artifact = strict_json(RESULT)
    expected_parameters = {
        "k": 48, "alpha1": "103/400", "eta1": "97/400",
        "alpha2": "3211/12000", "eta2": "3031/12000",
        "delta": "361/50000", "inner_c": "1",
        "outer_c": "3090/3211"}
    require(artifact.get("parameters") == expected_parameters and
            ETA1 < ETA2 < ALPHA1 < ALPHA2 and
            OUTER_C == ALPHA1 / ALPHA2,
            "parameters/cutoff assignment changed")
    require(artifact.get("certificate_sha256") == PINS[CERT] and
            artifact.get("script_sha256") == PINS[PRODUCER] and
            artifact.get("pinned_two_band_script_sha256") ==
            PINS["scripts/full_simplex_two_band_dilated_pencil.py"],
            "artifact provenance changed")

    a_exact, b_exact, counts = reconstruct(engine, basis, inner)
    a_serial = matrix(artifact.get("I_matrix"))
    b_serial = matrix(artifact.get("kJ_matrix"))
    require(a_exact == a_serial and b_exact == b_serial,
            "independent D18 matrix reconstruction disagrees")
    require(a_exact[0][1] == a_exact[1][0] == 0 and
            b_exact[0][1] == b_exact[1][0],
            "matrix symmetry/diagonal-I structure changed")

    # Since c_inner=1, the inner block must exactly reproduce the independent
    # contraction embedded in the source certificate.
    require(a_exact[0][0] == q(cert["exact_denominator"]) and
            b_exact[0][0] == q(cert["exact_numerator"]) and
            q(artifact["inner_exact_quotient"]) ==
            b_exact[0][0] / a_exact[0][0],
            "inner c=1 block does not reproduce the D18 certificate")

    rows = artifact.get("rows")
    require(isinstance(rows, list) and len(rows) == 2 and
            [row.get("name") for row in rows] ==
            ["unit", "rationalized_stationary"],
            "row inventory changed")
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
            "quotient_decimal_70": decimal(quotient),
            "margin_over_I": str(quotient - 1),
            "margin_over_I_decimal_70": decimal(quotient - 1),
            "raw_numerator_minus_denominator": str(numerator - denominator),
        }

    # Exact algebra, independent of floating eigenvalue discovery: B-I is
    # indefinite, and the displayed rational direction has positive form.
    d00 = b_exact[0][0] - a_exact[0][0]
    d11 = b_exact[1][1] - a_exact[1][1]
    det = d00 * d11 - b_exact[0][1] ** 2
    best = rows[1]
    require(d00 < 0 and d11 < 0 and det < 0 and
            q(best["exact_numerator"]) - q(best["exact_denominator"]) > 0,
            "exact positive-direction signature changed")

    # Check that the recorded rational is a stable 70-digit rounding of the
    # stationary root, while keeping positivity certified solely by Fractions.
    root100 = engine.stationary_amplitude(
        a_exact[0][0], a_exact[1][1], b_exact[0][0], b_exact[0][1],
        b_exact[1][1], 100)
    root160 = engine.stationary_amplitude(
        a_exact[0][0], a_exact[1][1], b_exact[0][0], b_exact[0][1],
        b_exact[1][1], 160)
    require(abs(root160 - root100) <= Decimal("1e-90") and
            q(best["outer_amplitude"]) == Q(format(root160, ".70E")),
            "stationary rationalization changed")

    require(artifact.get("format") ==
            "exact-uncapped-two-band-piecewise-dilations-v1" and
            artifact.get("status") == "exact-search-point" and
            artifact.get("analytic_support_approved") is False and
            artifact.get("theorem_ready") is False and
            set(artifact.get("never_implies", ())) >= {
                "Proposition-1 support", "a capped-support bound", "H1<=236"},
            "negative theorem scope changed")

    return {
        "status": "AUDIT PASS",
        "scope": "frozen exact uncapped piecewise Definition-5 D18 pencil only",
        "checker_sha256": sha(FILE),
        "pinned": PINS,
        "exact_checks": {
            "producer_not_imported": True,
            "coefficient_vector_basis_dimension": len(basis),
            "independent_exact_matrix_reconstructed": True,
            "inner_c1_equals_source_certificate": True,
            "inner_inner_cutoff": "97/400",
            "all_outer_involving_cutoffs": "3031/12000",
            "numerator_convention": "48J (factor 48 exactly once)",
            "B_minus_I_determinant_negative": True,
            "displayed_rational_direction_exactly_positive": True,
            "stationary_root_stable_and_rationalized_at_70_digits": True,
            "term_counts": counts,
        },
        "rows": audited_rows,
        "decision": (
            "the rationalized D18 piecewise vector exceeds one exactly in "
            "the uncapped search pencil; the outer simplex remains "
            "analytically unapproved, so this is not a Proposition-1 or "
            "bounded-gap certificate"),
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
