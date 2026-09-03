#!/usr/bin/env python3
"""Mutation tests for the independent pruned-v3 shard checker."""

from __future__ import annotations

import copy
from fractions import Fraction as Q
import importlib.util
import json
from pathlib import Path
import tempfile


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
CHECKER = HERE / "verify_pruned_v3_cross_shard.py"
REFERENCE = (REPO / "agents/exact-projection-engine/results/"
             "d14_grid38_scaled_b_fast_v2/common_r_00.json")


def load_checker():
    spec = importlib.util.spec_from_file_location("pruned_v3_auditor", CHECKER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"),
                       ensure_ascii=True, allow_nan=False) + "\n").encode("ascii")


def expect_failure(checker, raw, fragment):
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "mutant.json"
        path.write_bytes(canonical(raw))
        try:
            checker.audit(path)
        except Exception as error:
            if fragment not in str(error):
                raise AssertionError((fragment, type(error).__name__, str(error)))
        else:
            raise AssertionError(f"mutant unexpectedly passed: {fragment}")


def main():
    checker = load_checker()
    fast = checker.strict_load(REFERENCE.read_bytes(), str(REFERENCE))
    raw = copy.deepcopy(fast)
    raw["format"] = "D14-grid38-scaled-cutoff-cross-common-r-pruned-v3"
    raw["status"] = "EXACT PRUNED COMMON-r CROSS SHARD PASS"
    raw["producer_sha256"] = checker.PRODUCER_SHA
    raw["source_hashes"] = checker.SOURCE_HASHES
    raw["algorithm"] = {
        "family_common_denominator_integer_accumulation": True,
        "radial_common_denominator_integer_accumulation": True,
        "affine_products_collected_once_per_tag_and_shift": True,
        "empty_shifts_pruned_inside_small_coordinate_convolution": True,
        "coefficient_level_reference_transform_equality_in_pinned_tests": True,
        "full_low_k_fast_v2_branch_equality_in_pinned_tests": True,
    }
    raw["branch_values_and_fast_stats"]["integer_radialization"][
        "radial_stats"]["maximum_shift_pruned_inside_convolution"] = 14
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "valid.json"
        path.write_bytes(canonical(raw))
        result = checker.audit(path, REFERENCE)
        assert result["fast_v2_result_exactly_equal"] is True
        assert result["maximum_active_shift"] == 14

    mutant = copy.deepcopy(raw)
    mutant["branch_values_and_fast_stats"]["integer_radialization"][
        "radial_stats"]["maximum_shift_pruned_inside_convolution"] = 13
    expect_failure(checker, mutant, "H=14-r")

    mutant = copy.deepcopy(raw)
    mutant["scaled_b_shard"] = str(Q(mutant["scaled_b_shard"]) + 1)
    expect_failure(checker, mutant, "factor 48")

    mutant = copy.deepcopy(raw)
    del mutant["source_hashes"][next(iter(mutant["source_hashes"]))]
    expect_failure(checker, mutant, "source closure")

    mutant = copy.deepcopy(raw)
    del mutant["branch_values_and_fast_stats"]["high"]["Sdelta"]
    expect_failure(checker, mutant, "branch names")

    mutant = copy.deepcopy(raw)
    mutant["branch_values_and_fast_stats"]["integer_radialization"][
        "combined_denominator_bits"] += 1
    expect_failure(checker, mutant, "denominator bit length")

    print("6/6 pruned-v3 structural/result checker tests passed")


if __name__ == "__main__":
    main()
