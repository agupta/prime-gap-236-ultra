#!/usr/bin/env python3
"""Mutation tests for the strict collected-v5 result checker."""

from __future__ import annotations

import copy
from fractions import Fraction as Q
import importlib.util
import json
from pathlib import Path
import tempfile


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
CHECKER = HERE / "verify_collected_v5_cross_shard.py"
REFERENCE = (REPO / "agents/exact-projection-engine/results/"
             "d14_grid38_scaled_b_fast_v2/common_r_00.json")


def load_checker():
    spec = importlib.util.spec_from_file_location("collected_v5_auditor", CHECKER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"),
                       ensure_ascii=True, allow_nan=False) + "\n").encode("ascii")


def expect_failure(checker, raw, fragment, reference=None):
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "mutant.json"
        path.write_bytes(canonical(raw))
        try:
            checker.audit(path, reference)
        except Exception as error:
            if fragment not in str(error):
                raise AssertionError((fragment, type(error).__name__, str(error)))
        else:
            raise AssertionError(f"mutant unexpectedly passed: {fragment}")


def synthetic(checker):
    raw = checker.B.strict_load(REFERENCE.read_bytes(), str(REFERENCE))
    raw["format"] = "D14-grid38-scaled-cutoff-cross-common-r-collected-v5"
    raw["status"] = "EXACT COLLECTED COMMON-r CROSS SHARD PASS"
    raw["producer_sha256"] = checker.PRODUCER_SHA
    raw["source_hashes"] = checker.SOURCE_HASHES
    raw["algorithm"] = checker.ALGORITHM
    radial = raw["branch_values_and_fast_stats"]["integer_radialization"][
        "radial_stats"]
    radial["maximum_shift_pruned_inside_convolution"] = 14
    diagnostic = raw["branch_values_and_fast_stats"]
    for side in ("high_stats", "low_stats"):
        for row in diagnostic[side].values():
            row["nonzero_product_monomials"] = row["requested_moments"]
            row["cancelled_product_monomials"] = 0
            row["maximum_affine_denominator_bits"] = 1
            row["maximum_moment_denominator_bits"] = 1
    timing = diagnostic["timing_seconds"]
    timing["integrate_globally_collected_integers"] = timing.pop(
        "integrate_collected_affines")
    return raw


def main():
    checker = load_checker()
    raw = synthetic(checker)
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "valid.json"
        path.write_bytes(canonical(raw))
        result = checker.audit(path, REFERENCE)
        assert result["reference_mathematical_fields_bit_equal"] is True
        assert result["maximum_active_shift"] == 14

    mutant = copy.deepcopy(raw)
    mutant["branch_values_and_fast_stats"]["integer_radialization"][
        "radial_stats"]["maximum_shift_pruned_inside_convolution"] = 13
    expect_failure(checker, mutant, "pruned-radial inventory")

    mutant = copy.deepcopy(raw)
    mutant["scaled_b_shard"] = str(Q(mutant["scaled_b_shard"]) + 1)
    expect_failure(checker, mutant, "factor 48")

    mutant = copy.deepcopy(raw)
    mutant["branch_values_and_fast_stats"]["high_stats"]["Sdelta"][
        "nonzero_product_monomials"] -= 1
    expect_failure(checker, mutant, "collection inventory")

    mutant = copy.deepcopy(raw)
    del mutant["source_hashes"][next(iter(mutant["source_hashes"]))]
    expect_failure(checker, mutant, "source closure")

    # Preserve internal recombination while changing a mathematical field;
    # the optional frozen reference must still reject it bit-for-bit.
    mutant = copy.deepcopy(raw)
    mutant["branch_values_and_fast_stats"]["high"]["Sdelta"] = str(
        Q(mutant["branch_values_and_fast_stats"]["high"]["Sdelta"]) + 1)
    mutant["scaled_b_shard"] = str(Q(mutant["scaled_b_shard"]) + checker.B.K)
    expect_failure(checker, mutant, "bit-for-bit", REFERENCE)

    mutant = copy.deepcopy(raw)
    mutant["branch_values_and_fast_stats"]["timing_seconds"][
        "integrate_globally_collected_integers"] = float("inf")
    # Nonfinite numbers are rejected during strict JSON parsing; encode a
    # finite negative value to exercise the checker after canonicalization.
    mutant["branch_values_and_fast_stats"]["timing_seconds"][
        "integrate_globally_collected_integers"] = -1
    expect_failure(checker, mutant, "timing")
    print("7/7 collected-v5 structural/result checker tests passed")


if __name__ == "__main__":
    main()
