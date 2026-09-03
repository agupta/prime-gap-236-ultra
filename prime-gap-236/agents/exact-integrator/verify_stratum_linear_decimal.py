#!/usr/bin/env python3
"""Independent D4 calibration checker for a batched Decimal D1 artifact.

The checker compares every retained I and J entry with the previously rebuilt
exact Fraction D4 forms.  It is intentionally a calibration checker, not an
exact certificate for a high-degree Decimal result.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
from decimal import Decimal, localcontext
from fractions import Fraction
from pathlib import Path


EXPECTED_DEPENDENCIES = {
    "stratum_linear":
        "7400369a2e0e321ed032374f1e45f35785b0f0c53a085af18bf5ec2cb3c80162",
    "grouped":
        "47167e92a0f346e969706dc282ccb2dfd4ac31a0a75b654938ffbe8423cf4a4a",
    "integrator":
        "941ee82bc72fd8488a95eb5e536fe47f8c95d39a1b618dae7d6ef7eb27122e52",
    "robust_solver":
        "2086244acb674e5bd92e4880fb38d32d6dd981cd0272db595de2578554da257e",
}


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def parse_entries(raw):
    answer = {}
    for token, value in raw.items():
        key = ast.literal_eval(token)
        if not (isinstance(key, tuple) and len(key) == 2):
            raise ValueError(f"malformed entry key {token!r}")
        answer[key] = Decimal(value)
    return answer


def fraction_decimal(token, precision):
    value = Fraction(token)
    with localcontext() as context:
        context.prec = precision
        return Decimal(value.numerator) / Decimal(value.denominator)


def close(got, expected, dps, label):
    # The high-R D4 blocks are tiny differences of much larger Decimal terms;
    # the measured condition loss is about 40 digits.  Demand fifty guarded
    # digits beyond that loss at dps=100, and scale nonzero entries relatively.
    tolerance = Decimal(10) ** (-(dps - 50))
    if not expected:
        if got:
            raise ArithmeticError(
                f"{label} should vanish exactly, got {got}")
        return Decimal(0)
    relative_error = abs(got - expected) / abs(expected)
    if relative_error > tolerance:
        raise ArithmeticError(
            f"{label} differs: got {got}, expected {expected}, "
            f"relative error {relative_error}, tolerance {tolerance}")
    return relative_error


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("result_json")
    parser.add_argument("exact_d4_json")
    args = parser.parse_args()
    result = json.loads(Path(args.result_json).read_text())
    exact = json.loads(Path(args.exact_d4_json).read_text())
    dps = int(result["decimal_dps"])
    if dps < 90 or result.get("status") != \
            "multiprecision-stratum-linear-pilot":
        raise SystemExit("not a completed multiprecision pilot")
    if result.get("rigorous") is not False or not result.get("gates_passed"):
        raise SystemExit("result rigor/status gates are malformed")
    if result.get("fixed_basis_dimension") != 12 or \
            exact.get("fixed_basis_dimension") != 12:
        raise SystemExit("D4 calibration requires the 12-coordinate base")
    if result.get("input_sha256") != exact.get("input_sha256"):
        raise SystemExit("fixed D4 input hashes differ")
    if result.get("dependency_hashes", {}).items() < \
            EXPECTED_DEPENDENCIES.items():
        raise SystemExit("dependency hashes are not the pinned set")
    cutoff = int(result["linear_cutoff"])
    labels = [(int(r), ("1", "L", "Z").index(channel))
              for r, channel in result["nominal_labels"]]
    expected_labels = [(r, p) for r in range(16)
                       for p in ((0, 1, 2) if r <= cutoff else (0,))]
    if labels != expected_labels:
        raise SystemExit("pilot labels are incomplete or out of order")
    if result.get("discarded_exact_null_labels") != [[0, "L"]]:
        raise SystemExit("unexpected null-direction declaration")
    if (result.get("i_orbit_groups"), result.get("i_faces"),
            result.get("marginal_components"),
            result.get("j_branch_domains")) != (20, 312, 19, 1200):
        raise SystemExit("calibration traversal counts differ")

    i_got = parse_entries(result["i_entries"])
    j_got = parse_entries(result["j_entries"])
    expected_i_keys = {((r, p), (r, q)) for r in range(16)
                       for p in ((0, 1, 2) if r <= cutoff else (0,))
                       for q in ((0, 1, 2) if r <= cutoff else (0,))
                       if q <= p}
    if set(i_got) != expected_i_keys:
        raise SystemExit("I entry key set is incomplete")
    precision = dps + 30
    checked_errors = []
    for (left, right), got in i_got.items():
        r, p = left
        _, q = right
        expected = fraction_decimal(exact["i_blocks"][str(r)][p][q],
                                    precision)
        checked_errors.append((
            close(got, expected, dps, f"I[{left},{right}]"),
            f"I[{left},{right}]"))

    exact_j = {ast.literal_eval(key): Fraction(value)
               for key, value in exact["j_entries"].items()}
    expected_j_keys = {key for key in exact_j
                       if key[0] in labels and key[1] in labels}
    if set(j_got) != expected_j_keys:
        missing = expected_j_keys - set(j_got)
        extra = set(j_got) - expected_j_keys
        raise SystemExit(f"J entry key mismatch: missing={missing}, extra={extra}")
    for key, got in j_got.items():
        expected = fraction_decimal(exact_j[key], precision)
        checked_errors.append((
            close(got, expected, dps, f"J[{key}]"), f"J[{key}]"))

    # The all-constant vector is exactly the fixed base polynomial.  Rebuild
    # its two forms independently from the exact entries and compare with the
    # pilot's baseline diagnostics.
    exact_i = sum((Fraction(exact["i_blocks"][str(r)][0][0])
                   for r in range(16)), Fraction(0))
    exact_j_value = sum((value * (1 if left == right else 2)
                         for (left, right), value in exact_j.items()
                         if left[1] == right[1] == 0), Fraction(0))
    exact_numerator = 48 * exact_j_value
    for field, value in (("baseline_denominator", exact_i),
                         ("baseline_numerator", exact_numerator),
                         ("baseline_quotient", exact_numerator / exact_i)):
        checked_errors.append((close(
            Decimal(result[field]), fraction_decimal(value, precision),
            dps, field), field))
    if sha256(args.result_json) == sha256(args.exact_d4_json):
        raise SystemExit("result and exact reference unexpectedly coincide")
    print("D4 DECIMAL CALIBRATION PASS")
    print(json.dumps({
        "result_sha256": sha256(args.result_json),
        "exact_reference_sha256": sha256(args.exact_d4_json),
        "decimal_dps": dps,
        "i_entries_checked": len(i_got),
        "j_entries_checked": len(j_got),
        "worst_relative_error": str(max(checked_errors)[0]),
        "worst_relative_error_label": max(checked_errors)[1],
        "baseline_quotient": result["baseline_quotient"],
        "pilot_quotient": result["quotient"],
    }, indent=2))


if __name__ == "__main__":
    main()
