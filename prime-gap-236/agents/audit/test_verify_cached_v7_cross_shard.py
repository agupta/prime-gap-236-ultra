#!/usr/bin/env python3
"""Mutation tests for the cached-v7 target result checker."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile


HERE = Path(__file__).resolve().parent
CHECKER = HERE / "verify_cached_v7_cross_shard.py"
V6_TEST = HERE / "test_verify_fixed_v6_cross_shard.py"
V5_R0 = (HERE.parent / "exact-projection-engine/results/"
         "d14_grid38_scaled_b_collected_v5/common_r_00.json")
PINS = {
    CHECKER:
        "80ec3329215f66e784708039f9a1d673d7064769c48a31825961dc44f6ae7343",
    V6_TEST:
        "3f7eb92c2f14923740f3eb6454eca354793420a7d033d83b5cda7a63438fb887",
    V5_R0:
        "d097b5cdcd8e6fca25144e82a9bc2760d17441b62f74bef996d4a211f8feece1",
}
for _path, _expected in PINS.items():
    if hashlib.sha256(_path.read_bytes()).hexdigest() != _expected:
        raise RuntimeError(f"cached-v7 result-test pin changed: {_path}")


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
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


def to_v7(checker, raw):
    raw = copy.deepcopy(raw)
    raw["format"] = "D14-grid38-scaled-cutoff-cross-common-r-cached-v7"
    raw["status"] = "EXACT CACHED-FIXED COMMON-r CROSS SHARD PASS"
    raw["producer_sha256"] = checker.PRODUCER_SHA
    raw["source_hashes"] = checker.SOURCE_HASHES
    raw["algorithm"] = checker.ALGORITHM
    block = raw["branch_values_and_fast_stats"]
    radial = block["integer_radialization"]["radial_stats"]
    radial["cached_factorial_ratios"] = 1
    radial["cached_delta_scale_tables"] = 1
    timing = block["timing_seconds"]
    timing["radialize_cached_fixed_denominator_integers"] = timing.pop(
        "radialize_fixed_denominator_integers")
    return raw


def main():
    checker = load("cached_v7_checker_test", CHECKER)
    v6_test = load("cached_v7_v6_fixture", V6_TEST)
    fixed = v6_test.synthetic_r0(checker.V6)
    raw = to_v7(checker, fixed)
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        path = root / "valid-v7.json"
        reference = root / "valid-v6.json"
        path.write_bytes(canonical(raw))
        reference.write_bytes(canonical(fixed))
        result = checker.audit(path, reference)
        if result["reference_mathematical_fields_bit_equal"] is not True:
            raise AssertionError("same-r v6 equality flag is absent")
        if result["maximum_active_shift"] != 14:
            raise AssertionError("r0 maximum shift differs")
        if result["cache_inventory_semantics_verified"] is not True:
            raise AssertionError("cache inventory flag is absent")

    mutant = copy.deepcopy(raw)
    del mutant["branch_values_and_fast_stats"]["integer_radialization"][
        "radial_stats"]["cached_delta_scale_tables"]
    expect_failure(checker, mutant, "radial-stat schema")

    mutant = copy.deepcopy(raw)
    mutant["branch_values_and_fast_stats"]["integer_radialization"][
        "radial_stats"]["cached_factorial_ratios"] = -1
    expect_failure(checker, mutant, "nonnegative integer")

    mutant = copy.deepcopy(raw)
    radial = mutant["branch_values_and_fast_stats"][
        "integer_radialization"]["radial_stats"]
    radial["cached_delta_scale_tables"] = radial["maximum_orbit_degree"] + 2
    expect_failure(checker, mutant, "delta-table cache inventory")

    mutant = copy.deepcopy(raw)
    radial = mutant["branch_values_and_fast_stats"][
        "integer_radialization"]["radial_stats"]
    radial["cached_factorial_ratios"] = (radial["factorial_ceiling"] + 1) ** 2 + 1
    expect_failure(checker, mutant, "factorial-ratio cache inventory")

    mutant = copy.deepcopy(raw)
    mutant["algorithm"]["factorial_ratios_cached_outside_partition_inner_loops"] = False
    expect_failure(checker, mutant, "algorithm")

    mutant = copy.deepcopy(raw)
    del mutant["source_hashes"][next(iter(mutant["source_hashes"]))]
    expect_failure(checker, mutant, "source closure")

    mutant = copy.deepcopy(raw)
    mutant["scaled_b_shard"] = "0"
    expect_failure(checker, mutant, "factor 48")

    # Preserve internal factor-48 recombination, but disagree with the audited
    # same-r v6 reference in exact branch/value fields.
    mutant = copy.deepcopy(raw)
    high = mutant["branch_values_and_fast_stats"]["high"]
    from fractions import Fraction as Q
    high["Sdelta"] = str(Q(high["Sdelta"]) + 1)
    mutant["scaled_b_shard"] = str(Q(mutant["scaled_b_shard"]) + 48)
    with tempfile.TemporaryDirectory() as directory:
        reference = Path(directory) / "valid-v6.json"
        reference.write_bytes(canonical(fixed))
        expect_failure(checker, mutant, "bit-for-bit", reference)

    print("9/9 cached-v7 structural/result checker tests passed")


if __name__ == "__main__":
    main()
