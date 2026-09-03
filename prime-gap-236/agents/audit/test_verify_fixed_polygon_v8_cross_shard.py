#!/usr/bin/env python3
"""Mutation tests for the fixed-polygon-v8 result checker."""

from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile


HERE = Path(__file__).resolve().parent
CHECKER = HERE / "verify_fixed_polygon_v8_cross_shard.py"
V7_TEST = HERE / "test_verify_cached_v7_cross_shard.py"
V6_TEST = HERE / "test_verify_fixed_v6_cross_shard.py"


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"),
                       ensure_ascii=True, allow_nan=False) + "\n").encode("ascii")


def to_v8(checker, raw):
    raw = copy.deepcopy(raw)
    raw["format"] = (
        "D14-grid38-scaled-cutoff-cross-common-r-fixed-polygon-v8")
    raw["status"] = "EXACT FIXED-POLYGON COMMON-r CROSS SHARD PASS"
    raw["producer_sha256"] = checker.PRODUCER_SHA
    raw["source_hashes"] = checker.SOURCE_HASHES
    raw["algorithm"] = checker.ALGORITHM
    return raw


def expect_failure(checker, raw, fragment):
    with tempfile.TemporaryDirectory() as root:
        path = Path(root) / "mutant.json"
        path.write_bytes(canonical(raw))
        try:
            checker.audit(path)
        except Exception as error:
            if fragment not in str(error):
                raise AssertionError((fragment, type(error).__name__, str(error)))
        else:
            raise AssertionError(f"mutant unexpectedly passed: {fragment}")


def main():
    checker = load("fixed_polygon_v8_checker_test", CHECKER)
    t7 = load("fixed_polygon_v8_v7_fixture", V7_TEST)
    t6 = load("fixed_polygon_v8_v6_fixture", V6_TEST)
    v7 = t7.to_v7(checker.V7, t6.synthetic_r0(checker.V7.V6))
    raw = to_v8(checker, v7)
    with tempfile.TemporaryDirectory() as root:
        path = Path(root) / "valid-v8.json"
        reference = Path(root) / "valid-v7.json"
        path.write_bytes(canonical(raw))
        changed_timing = copy.deepcopy(v7)
        changed_timing["timing_seconds"]["total"] += 123.0
        changed_timing["branch_values_and_fast_stats"]["timing_seconds"][
            "integrate_globally_collected_integers"] += 17.0
        reference.write_bytes(canonical(changed_timing))
        result = checker.audit(path, reference)
        if result["reference_exact_fields_bit_equal"] is not True:
            raise AssertionError("reference exact-field comparison was skipped")
        if result["recombined_exactly"] is not True:
            raise AssertionError("v7 recombination audit was skipped")
        if result["fixed_polygon_denominator_proof_pinned"] is not True:
            raise AssertionError("fixed-polygon proof pin was skipped")

    mutant = copy.deepcopy(raw)
    mutant["algorithm"][
        "polygon_moments_accumulated_under_one_batch_denominator"] = False
    expect_failure(checker, mutant, "identity/source")
    mutant = copy.deepcopy(raw)
    del mutant["source_hashes"][checker.MOMENT_SOURCE]
    expect_failure(checker, mutant, "identity/source")
    mutant = copy.deepcopy(raw)
    mutant["scaled_b_shard"] = "0"
    expect_failure(checker, mutant, "factor 48")
    print("4/4 fixed-polygon-v8 structural/result checker tests passed")


if __name__ == "__main__":
    main()
