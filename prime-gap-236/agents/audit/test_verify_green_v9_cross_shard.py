#!/usr/bin/env python3
"""Mutation tests for the Green-polygon-v9 result checker."""

from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile


HERE = Path(__file__).resolve().parent
CHECKER = HERE / "verify_green_v9_cross_shard.py"
V8_TEST = HERE / "test_verify_fixed_polygon_v8_cross_shard.py"
V7_TEST = HERE / "test_verify_cached_v7_cross_shard.py"
V6_TEST = HERE / "test_verify_fixed_v6_cross_shard.py"


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"),
                       ensure_ascii=True, allow_nan=False) + "\n").encode("ascii")


def to_v9(checker, raw):
    raw = copy.deepcopy(raw)
    raw["format"] = "D14-grid38-scaled-cutoff-cross-common-r-green-v9"
    raw["status"] = "EXACT GREEN-POLYGON COMMON-r CROSS SHARD PASS"
    raw["producer_sha256"] = checker.PRODUCER_SHA
    raw["source_hashes"] = checker.SOURCE_HASHES
    raw["algorithm"] = checker.ALGORITHM
    return raw


def expect_failure(checker, raw, fragment):
    with tempfile.TemporaryDirectory(prefix="green-v9-checker-mutant-") as root:
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
    checker = load("green_v9_checker_test", CHECKER)
    t8 = load("green_v9_v8_conversion", V8_TEST)
    t7 = load("green_v9_v7_fixture", V7_TEST)
    t6 = load("green_v9_v6_fixture", V6_TEST)
    v7 = t7.to_v7(checker.V8.V7, t6.synthetic_r0(checker.V8.V7.V6))
    v8 = t8.to_v8(checker.V8, v7)
    raw = to_v9(checker, v8)
    with tempfile.TemporaryDirectory(prefix="green-v9-valid-") as root:
        path = Path(root) / "valid-v9.json"
        reference = Path(root) / "valid-v8.json"
        path.write_bytes(canonical(raw))
        changed_timing = copy.deepcopy(v8)
        changed_timing["timing_seconds"]["total"] += 91.0
        changed_timing["branch_values_and_fast_stats"]["timing_seconds"][
            "integrate_globally_collected_integers"] += 17.0
        reference.write_bytes(canonical(changed_timing))
        result = checker.audit(path, reference)
        if result["reference_exact_fields_bit_equal"] is not True:
            raise AssertionError("v9/v8 exact comparison was skipped")
        if result["recombined_exactly"] is not True:
            raise AssertionError("v8/v7 recombination cascade was skipped")
        if result["green_boundary_denominator_proof_pinned"] is not True:
            raise AssertionError("Green denominator pin was skipped")

    mutant = copy.deepcopy(raw)
    mutant["algorithm"]["polygon_convex_cyclic_order_checked"] = False
    expect_failure(checker, mutant, "identity/source")
    mutant = copy.deepcopy(raw)
    del mutant["source_hashes"][checker.GREEN_SOURCE]
    expect_failure(checker, mutant, "identity/source")
    mutant = copy.deepcopy(raw)
    mutant["scaled_b_shard"] = "0"
    expect_failure(checker, mutant, "factor 48")
    print("4/4 Green-v9 structural/result checker tests passed")


if __name__ == "__main__":
    main()
