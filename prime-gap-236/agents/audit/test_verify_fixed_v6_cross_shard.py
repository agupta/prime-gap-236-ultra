#!/usr/bin/env python3
"""Mutation tests for the strict fixed-v6 target result checker."""

from __future__ import annotations

import copy
from fractions import Fraction as Q
import importlib.util
import json
import math
from pathlib import Path
import tempfile


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
CHECKER = HERE / "verify_fixed_v6_cross_shard.py"
V5_R0 = (REPO / "agents/exact-projection-engine/results/"
         "d14_grid38_scaled_b_collected_v5/common_r_00.json")


def load_checker():
    spec = importlib.util.spec_from_file_location("fixed_v6_result_auditor", CHECKER)
    if spec is None or spec.loader is None:
        raise ImportError(CHECKER)
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


def synthetic_r0(checker):
    raw = checker.B.strict_load(V5_R0.read_bytes(), str(V5_R0))
    raw["format"] = "D14-grid38-scaled-cutoff-cross-common-r-fixed-v6"
    raw["status"] = "EXACT FIXED-DENOMINATOR COMMON-r CROSS SHARD PASS"
    raw["producer_sha256"] = checker.PRODUCER_SHA
    raw["source_hashes"] = checker.SOURCE_HASHES
    raw["algorithm"] = checker.ALGORITHM
    integer = raw["branch_values_and_fast_stats"]["integer_radialization"]
    integer["active_branch_families"] = ["large", "small", "small_total"]
    integer["inactive_families_pruned_before_radialization"] = []
    radial = integer["radial_stats"]
    degree = 32
    ceiling = degree+46
    provisional = 60**degree*math.factorial(ceiling)
    radial_denominator = int(integer["radial_denominator"])
    assert provisional % radial_denominator == 0
    radial.update({
        "fixed_provisional_denominator_bits": provisional.bit_length(),
        "fixed_denominator_common_gcd_bits":
            (provisional//radial_denominator).bit_length(),
        "maximum_orbit_degree": degree,
        "factorial_ceiling": ceiling,
    })
    timing = raw["branch_values_and_fast_stats"]["timing_seconds"]
    timing["radialize_fixed_denominator_integers"] = timing.pop(
        "radialize_integer")
    return raw


def synthetic_r12(checker):
    raw = synthetic_r0(checker)
    raw["common_r"] = 12
    block = raw["branch_values_and_fast_stats"]
    for side in ("high", "low", "high_stats", "low_stats"):
        block[side] = {key: value for key, value in block[side].items()
                       if key in {"Sdelta", "Stotal"}}
    high = sum(map(Q, block["high"].values()), Q(0))
    low = sum(map(Q, block["low"].values()), Q(0))
    raw["scaled_b_shard"] = str(48*(high-low))
    integer = block["integer_radialization"]
    integer["active_branch_families"] = ["small", "small_total"]
    integer["inactive_families_pruned_before_radialization"] = ["large"]
    entries = raw["family_stats"]["family_orbit_tag_entries"]
    active_entries = entries["small"]+entries["small_total"]
    integer["clear_stats"]["family_coefficients"] = active_entries
    integer["radial_stats"]["orbit_tag_associations"] = active_entries
    integer["radial_stats"]["maximum_shift_pruned_inside_convolution"] = 2
    # A synthetic filtered-family denominator.  This test targets schema and
    # exact fixed-D/gcd relations, not a claim about the r12 integral.
    integer["family_denominator"] = "1"
    integer["clear_stats"]["common_denominator_bits"] = 1
    integer["radial_denominator"] = "1"
    integer["radial_stats"]["radial_denominator_bits"] = 1
    degree = integer["radial_stats"]["maximum_orbit_degree"]
    provisional = 60**degree*math.factorial(degree+46)
    integer["radial_stats"]["fixed_denominator_common_gcd_bits"] = \
        provisional.bit_length()
    integer["combined_denominator_bits"] = 1
    return raw


def main():
    checker = load_checker()
    raw = synthetic_r0(checker)
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "valid-r0.json"
        path.write_bytes(canonical(raw))
        result = checker.audit(path, V5_R0)
        assert result["reference_mathematical_fields_bit_equal"] is True
        assert result["maximum_active_shift"] == 14
        assert result["maximum_orbit_degree"] == 32

    r12 = synthetic_r12(checker)
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "valid-r12.json"
        path.write_bytes(canonical(r12))
        result = checker.audit(path)
        assert result["maximum_active_shift"] == 2
        assert result["active_branch_families"] == ["small", "small_total"]
        assert result["inactive_families_pruned_before_radialization"] == ["large"]

    mutant = copy.deepcopy(raw)
    mutant["branch_values_and_fast_stats"]["integer_radialization"][
        "radial_stats"]["maximum_shift_pruned_inside_convolution"] = 13
    expect_failure(checker, mutant, "H=14-r")

    mutant = copy.deepcopy(raw)
    mutant["branch_values_and_fast_stats"]["integer_radialization"][
        "active_branch_families"].remove("large")
    expect_failure(checker, mutant, "active/inactive")

    mutant = copy.deepcopy(raw)
    mutant["branch_values_and_fast_stats"]["integer_radialization"][
        "radial_stats"]["factorial_ceiling"] -= 1
    expect_failure(checker, mutant, "factorial ceiling")

    mutant = copy.deepcopy(raw)
    mutant["branch_values_and_fast_stats"]["integer_radialization"][
        "radial_stats"]["maximum_orbit_degree"] = 10**9
    mutant["branch_values_and_fast_stats"]["integer_radialization"][
        "radial_stats"]["factorial_ceiling"] = 10**9+46
    expect_failure(checker, mutant, "factorial ceiling")

    mutant = copy.deepcopy(raw)
    mutant["branch_values_and_fast_stats"]["integer_radialization"][
        "radial_stats"]["fixed_provisional_denominator_bits"] -= 1
    expect_failure(checker, mutant, "provisional denominator")

    mutant = copy.deepcopy(raw)
    mutant["branch_values_and_fast_stats"]["integer_radialization"][
        "radial_stats"]["fixed_denominator_common_gcd_bits"] -= 1
    expect_failure(checker, mutant, "gcd metadata")

    mutant = copy.deepcopy(raw)
    mutant["scaled_b_shard"] = str(Q(mutant["scaled_b_shard"])+1)
    expect_failure(checker, mutant, "factor 48")

    mutant = copy.deepcopy(raw)
    del mutant["source_hashes"][next(iter(mutant["source_hashes"]))]
    expect_failure(checker, mutant, "source closure")

    mutant = copy.deepcopy(r12)
    mutant["branch_values_and_fast_stats"]["integer_radialization"][
        "clear_stats"]["family_coefficients"] += 1
    expect_failure(checker, mutant, "work inventory")

    # Preserve internal factor-48 recombination but violate the independent
    # same-r v5 comparison.
    mutant = copy.deepcopy(raw)
    mutant["branch_values_and_fast_stats"]["high"]["Sdelta"] = str(
        Q(mutant["branch_values_and_fast_stats"]["high"]["Sdelta"])+1)
    mutant["scaled_b_shard"] = str(Q(mutant["scaled_b_shard"])+48)
    expect_failure(checker, mutant, "bit-for-bit", V5_R0)

    print("12/12 fixed-v6 structural/result checker tests passed")


if __name__ == "__main__":
    main()
