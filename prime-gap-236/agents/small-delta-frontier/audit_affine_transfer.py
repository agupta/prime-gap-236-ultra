#!/usr/bin/env python3
"""Read-only hostile audit of the D4 affine-transfer calibration."""

from __future__ import annotations

import ast
import hashlib
import json
import sys
from decimal import Decimal, localcontext
from fractions import Fraction as Q
from pathlib import Path

if hasattr(sys, "set_int_max_str_digits"):
    sys.set_int_max_str_digits(0)

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
EI = ROOT / "agents" / "exact-integrator"
RESULTS = EI / "results"

EXPECTED_CURRENT = {
    EI / "stratum_linear_transfer_decimal.py":
        "91d1b4ad0c675ccfe36100166bee20bb4007af49e1d0cfe618c8c82c8857f354",
    EI / "tests/test_stratum_linear_transfer_decimal.py":
        "5399df38abc2e5dac58a4f4514d1e5324d3479ca4d7517e0f45f1fe9fc48508f",
    EI / "stratum_linear_decimal.py":
        "ba3ff83b186e7784634a97bf82f13ae3abdd4a4e753b226f0eaed23d659dfbc0",
    EI / "stratum_linear.py":
        "7400369a2e0e321ed032374f1e45f35785b0f0c53a085af18bf5ec2cb3c80162",
    EI / "stratum_amplitude.py":
        "d23d42315d7b518ae5d3f200a6192f47f3500d6eebd3a73fb6aa4ce7a23c7887",
    EI / "grouped_fixed_vector.py":
        "47167e92a0f346e969706dc282ccb2dfd4ac31a0a75b654938ffbe8423cf4a4a",
    EI / "src/exact_integrator.py":
        "941ee82bc72fd8488a95eb5e536fe47f8c95d39a1b618dae7d6ef7eb27122e52",
    EI / "robust_generalized_solve.py":
        "2086244acb674e5bd92e4880fb38d32d6dd981cd0272db595de2578554da257e",
}
EXPECTED_EXACT_SHA = \
    "ffa607e0f2a8a3b6648f248efb13dc7ac2f1e7ef5809771f31c5f04b30f53158"
EXPECTED_OLD_TRANSFER_SHA = \
    "3390decc8bc479ecdf6d2b15bc12c877b8f7cf3bbfebb8bad2ff25640aad1285"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fail(message):
    raise SystemExit("AUDIT FAIL: " + message)


def quadratic_i(exact, coefficients):
    answer = Q(0)
    for r in range(16):
        block = [[Q(x) for x in row] for row in exact["i_blocks"][str(r)]]
        vector = [coefficients[(r, p)] for p in range(3)]
        answer += sum(vector[p] * block[p][q] * vector[q]
                      for p in range(3) for q in range(3))
    return answer


def quadratic_j(exact, coefficients):
    answer = Q(0)
    for token, value in exact["j_entries"].items():
        left, right = ast.literal_eval(token)
        term = Q(value) * coefficients[left] * coefficients[right]
        answer += term if left == right else 2 * term
    return 48 * answer


def main():
    for path, expected in EXPECTED_CURRENT.items():
        if sha(path) != expected:
            fail(f"current dependency changed: {path}")
    exact_path = RESULTS / "c10_stratum_linear_cappedopt_D4_exact.json"
    transfer_path = RESULTS / "c10_D4_affine_transfer_decimal100_cut10.json"
    if sha(exact_path) != EXPECTED_EXACT_SHA:
        fail("exact D4 affine artifact SHA mismatch")
    if sha(transfer_path) != EXPECTED_OLD_TRANSFER_SHA:
        fail("historical D4 transfer artifact SHA mismatch")
    exact = json.loads(exact_path.read_bytes())
    transfer = json.loads(transfer_path.read_bytes())
    labels = [(int(r), ("1", "L", "Z").index(channel))
              for r, channel in exact["linear_labels"]]
    if labels != [(r, p) for r in range(16) for p in range(3)]:
        fail("exact coordinate ordering mismatch")
    cutoff = int(transfer["linear_cutoff"])
    if cutoff != 10:
        fail("historical calibration cutoff is not 10")
    vector = list(map(Q, exact["rational_vector"]))
    coefficients = {
        label: (value if label[1] == 0 or label[0] <= cutoff else Q(0))
        for label, value in zip(labels, vector)
    }
    # This is the exact meaning of the cutoff: constants survive at every R;
    # only L/Z coordinates above the cutoff vanish.
    for label, source_value in zip(labels, vector):
        r, p = label
        expected_value = (Q(0) if p != 0 and r > cutoff else source_value)
        if coefficients[label] != expected_value:
            fail(f"cutoff semantics mismatch at {label}")

    denominator = quadratic_i(exact, coefficients)
    numerator = quadratic_j(exact, coefficients)
    quotient = numerator / denominator
    margin = numerator - denominator
    with localcontext() as context:
        context.prec = 130
        def dec(x):
            return Decimal(x.numerator) / Decimal(x.denominator)
        comparisons = {
            "denominator": denominator,
            "numerator": numerator,
            "quotient": quotient,
            "margin": margin,
        }
        decimal_values = {name: str(dec(value))
                          for name, value in comparisons.items()}
        errors = {}
        for name, expected in comparisons.items():
            got = Decimal(transfer[name])
            error = abs(got - dec(expected)) / max(Decimal(1), abs(dec(expected)))
            errors[name] = error
            if error > Decimal("1e-70"):
                fail(f"D4 transfer/exact {name} error {error}")
    if transfer.get("gates_passed") is not True or transfer.get("rigorous") is not False:
        fail("historical transfer status malformed")

    print("AFFINE TRANSFER ARITHMETIC AUDIT PASS; PROVENANCE GATE REPAIRED")
    print(json.dumps({
        "scope": ("D4 exact calibration, cutoff semantics, current import "
                  "closure; not a D12 theorem certificate"),
        "exact_denominator_decimal": decimal_values["denominator"],
        "exact_numerator_decimal": decimal_values["numerator"],
        "exact_quotient_decimal": decimal_values["quotient"],
        "exact_margin_decimal": decimal_values["margin"],
        "worst_historical_decimal_relative_error": str(max(errors.values())),
        "old_unpinned_stage_counterexample": {
            "old_driver_sha256":
                "f8e642c5fcccbd64f1cce3c515b7c2eec30b569776136c448c1ed0fc6ea50732",
            "altered_stage_sha256":
                "4c37b9e8c7cf7c7e73aea31985206a01990aafb417681de3b7e603cecfe979df",
            "old_process_returncode": 0,
            "old_gates_passed": True,
        },
        "current_transfer_sha256": EXPECTED_CURRENT[
            EI / "stratum_linear_transfer_decimal.py"],
        "current_transfer_tests_sha256": EXPECTED_CURRENT[
            EI / "tests/test_stratum_linear_transfer_decimal.py"],
        "theorem_ready": False,
    }, indent=2))


if __name__ == "__main__":
    main()
