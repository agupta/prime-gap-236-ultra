#!/usr/bin/env python3
"""Independent exact audit of the frozen Definition-5 two-band proxies.

The expensive orbit contractions were produced by two distinct programs.
This small checker imports neither program: it pins all bytes, compares their
exact matrices and rows, reconstructs every displayed contraction, verifies
the Definition-5 tail identity, and proves the whole frozen 2D pencil is below
one by an exact Sylvester-criterion calculation.
"""

from __future__ import annotations

import argparse
from decimal import Decimal, localcontext
from fractions import Fraction as Q
import hashlib
import json
import os
from pathlib import Path


FILE = Path(__file__).resolve()
REPO = FILE.parents[2]
ROOT_RESULT = "results/wide_c722_D16_dilated_uncapped_two_band_pencil_exact.json"
INDEPENDENT_RESULT = (
    "agents/structural-basis/results/"
    "bv_D16_dilation_Definition5_two_band_exact_v2.json")
ONE_BAND_RESULT = "results/wide_c722_D16_dilated_fullsimplex_proxy_exact.json"

PINNED = {
    "scripts/full_simplex_two_band_dilated_pencil.py":
        "85c4847c4803015d9aa14f67d257be62a4d23edbff5843f191e903ce885d4804",
    ROOT_RESULT:
        "9a75380bb2f168adbae70751b6ca04ef9372892fa34c2f66bb0a1a05d59d3d7d",
    "agents/structural-basis/code/bv_dilation_definition5_two_band_proxy_v2.py":
        "0b322ed3b6ea45bfb4f6a7a57deebe34cc57f2a41df68f6f0a592c91dd848d95",
    "agents/structural-basis/tests/test_bv_dilation_definition5_two_band_proxy_v2.py":
        "bca7147b8e98a76f504fa50f45cb7dc0b4b43a72b1bedd21563f79749e3b77fe",
    INDEPENDENT_RESULT:
        "05410084611a86d04877ebe2b73a17899e45915fdf1b9b466a25996d28db3171",
    "scripts/full_simplex_dilated_vector_proxy.py":
        "3219047bd9d339e15946947f68bd6484d23af722337ba70771c488e3e1238794",
    ONE_BAND_RESULT:
        "27a893e9d68f5117f688a42de4f18ead59a860c24a507820b59db19f750f0ba1",
    "agents/small-delta-frontier/bv_aquarter_B16_vector_exact.json":
        "59715ddffa483c696c035634a81c3cc8ffe882e9d6eaceec74bea23996b72d62",
    "agents/exact-integrator/src/exact_integrator.py":
        "941ee82bc72fd8488a95eb5e536fe47f8c95d39a1b618dae7d6ef7eb27122e52",
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


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


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ArithmeticError(message)


def q(value) -> Q:
    require(isinstance(value, str), "exact value must be a rational string")
    parsed = Q(value)
    rendered = (str(parsed.numerator) if parsed.denominator == 1 else
                f"{parsed.numerator}/{parsed.denominator}")
    require(rendered == value, "noncanonical rational")
    return parsed


def matrix(value):
    require(isinstance(value, list) and len(value) == 2 and
            all(isinstance(row, list) and len(row) == 2 for row in value),
            "expected a 2x2 matrix")
    return [[q(entry) for entry in row] for row in value]


def decimal(value: Q, precision: int = 50) -> str:
    with localcontext() as context:
        context.prec = precision
        return str(Decimal(value.numerator) / Decimal(value.denominator))


def contraction(a, b, amplitude: Q):
    vector = (Q(1), amplitude)
    denominator = sum(vector[i] * a[i][j] * vector[j]
                      for i in range(2) for j in range(2))
    numerator = sum(vector[i] * b[i][j] * vector[j]
                    for i in range(2) for j in range(2))
    return denominator, numerator, numerator / denominator


def build() -> dict[str, object]:
    for relative, expected in PINNED.items():
        require(sha(REPO / relative) == expected,
                f"frozen Definition-5 input changed: {relative}")
    root = strict_json(ROOT_RESULT)
    independent = strict_json(INDEPENDENT_RESULT)
    one_band = strict_json(ONE_BAND_RESULT)
    require(all(isinstance(x, dict) for x in (root, independent, one_band)),
            "top-level artifacts must be objects")

    expected_root_parameters = {
        "k": 48, "alpha1": "103/400", "eta1": "97/400",
        "alpha2": "3211/12000", "eta2": "3031/12000",
        "delta": "361/50000", "dilation_c": "3090/3211"}
    expected_independent_parameters = {
        "k": 48, "alpha_inner": "103/400", "eta_inner": "97/400",
        "alpha_outer": "3211/12000", "eta_outer": "3031/12000",
        "dilation_c": "3090/3211"}
    require(root.get("parameters") == expected_root_parameters and
            independent.get("parameters") == expected_independent_parameters,
            "two-band parameters/cutoffs changed")
    require(Q(97, 400) < Q(3031, 12000) < Q(103, 400) <
            Q(3211, 12000), "cutoff/band ordering changed")

    a_root, b_root = matrix(root.get("I_matrix")), matrix(
        root.get("kJ_matrix"))
    a_ind, b_ind = matrix(independent.get("I_matrix")), matrix(
        independent.get("kJ_matrix"))
    require(a_root == a_ind and b_root == b_ind,
            "independent exact 2x2 matrices disagree")
    a, b = a_root, b_root
    require(a[0][0] > 0 and a[1][1] > 0 and
            a[0][1] == a[1][0] == 0 and b[0][1] == b[1][0],
            "denominator/symmetry structure changed")

    # Stronger than checking the displayed vector: A-B positive definite
    # proves kJ/I<1 for every nonzero real vector in this frozen 2D pencil.
    d00 = a[0][0] - b[0][0]
    d11 = a[1][1] - b[1][1]
    determinant = d00 * d11 - b[0][1] ** 2
    require(d00 > 0 and determinant > 0,
            "A-B is not exactly positive definite")

    root_rows = {row.get("name"): row for row in root.get("rows", ())
                 if isinstance(row, dict)}
    independent_rows = {
        row.get("name"): row for row in independent.get("rows", ())
        if isinstance(row, dict)}
    require(set(root_rows) == set(independent_rows) == {
        "unit_outer_amplitude", "rationalized_stationary_amplitude"},
        "row inventory changed")
    audited_rows = {}
    for name in sorted(root_rows):
        left, right = root_rows[name], independent_rows[name]
        amplitude = q(left["outer_amplitude"])
        require(amplitude == q(right["outer_amplitude"]),
                f"{name} amplitude disagreement")
        denominator, numerator, quotient = contraction(a, b, amplitude)
        require(denominator == q(left["exact_denominator"]) ==
                q(right["denominator"]) and
                numerator == q(left["exact_numerator"]) ==
                q(right["numerator_48J"]) and
                quotient == q(left["exact_quotient"]) ==
                q(right["quotient"]) and
                numerator - denominator == q(left["exact_margin"]) ==
                q(right["margin_48J_minus_I"]) and numerator < denominator,
                f"{name} exact contraction disagreement")
        audited_rows[name] = {
            "outer_amplitude": str(amplitude),
            "quotient": str(quotient),
            "quotient_decimal_50": decimal(quotient),
            "shortfall_to_one": str(1 - quotient),
            "shortfall_decimal_50": decimal(1 - quotient),
        }

    # Definition 5: inner/inner uses eta1; mixed and outer/outer use eta2.
    # At unit amplitude this is exactly the old one-band eta2 numerator minus
    # the positive inner/inner tail eta1<U<eta2.
    one_band_target = next(row for row in one_band["rows"]
                           if row["name"] == "dilated_target_cutoff")
    total_i, total_b = q(one_band_target["exact_denominator"]), q(
        one_band_target["exact_numerator"])
    tail = q(root["inner_tail_subtracted_from_one_band_numerator"])
    unit_i, unit_b, _ = contraction(a, b, Q(1))
    require(a[0][0] + a[1][1] == total_i and tail > 0 and
            unit_i == total_i and unit_b == total_b - tail,
            "Definition-5 inner-tail subtraction identity failed")
    require(q(root["inner_exact_quotient"]) == b[0][0] / a[0][0] and
            q(root["one_band_eta2_quotient"]) == total_b / total_i,
            "root cutoff diagnostics inconsistent")
    diagnostics = independent.get("cutoff_diagnostics")
    require(isinstance(diagnostics, dict) and
            q(diagnostics["Definition5_inner_48J"]) == b[0][0] and
            q(diagnostics["subtracted_inner_tail_48J"]) == tail and
            q(diagnostics["Definition5_inner_quotient"]) ==
            b[0][0] / a[0][0] and
            q(diagnostics["uncapped_one_band_outer_quotient"]) ==
            total_b / total_i,
            "independent cutoff diagnostics inconsistent")

    best = audited_rows["rationalized_stationary_amplitude"]
    require(q(independent["best_exact_shortfall_to_one"]) ==
            q(best["shortfall_to_one"]),
            "best particular-vector shortfall changed")
    require(independent.get("root_matrix_and_rows_match_exactly") is True,
            "independent producer did not record exact root equality")

    require(root.get("format") == "uncapped-two-band-dilated-pencil-v1" and
            root.get("status") == "exact-search-relaxation" and
            root.get("rigorous_particular_forms") is True and
            root.get("analytic_support_approved") is False and
            root.get("theorem_ready") is False,
            "root scope flags changed")
    require(independent.get("rigorous_arithmetic") is True and
            independent.get("analytic_support_approved") is False and
            independent.get("theorem_ready") is False,
            "independent scope flags changed")
    for artifact in (root, independent):
        text = json.dumps(artifact.get("never_implies", artifact.get("scope", "")))
        require("H1<=236" in text or "not a capped" in text,
                "negative theorem scope is missing")

    return {
        "status": "AUDIT PASS",
        "scope": "frozen uncapped Definition-5 two-band BV-D16 pencil",
        "checker_sha256": sha(FILE),
        "pinned": PINNED,
        "exact_checks": {
            "independent_matrices_equal": True,
            "independent_rows_equal": True,
            "inner_inner_cutoff": "97/400",
            "mixed_and_outer_cutoff": "3031/12000",
            "numerator_convention": "48J (factor 48 applied exactly once)",
            "positive_inner_tail_subtracted": True,
            "A_minus_kJ_positive_definite": True,
            "all_nonzero_vectors_in_this_2D_pencil_have_quotient_below_one": True,
        },
        "rows": audited_rows,
        "decision": (
            "the natural-dilation uncapped 2D pencil is rigorously below one; "
            "the earlier 1.020782 one-band value is only a looser search signal; "
            "a capped-support contraction remains necessary"),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    payload = (json.dumps(build(), sort_keys=True, separators=(",", ":")) +
               "\n").encode("ascii")
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
