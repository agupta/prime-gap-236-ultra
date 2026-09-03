#!/usr/bin/env python3
"""Small fail-closed tests for the fixed-v6 scalar assembler revision."""

from __future__ import annotations

import importlib.util
import json
import math
from pathlib import Path
import sys
import unittest


HERE = Path(__file__).resolve().parent
SOURCE = HERE / "assemble_one_band_236_fixed_v6.py"


def load_source():
    spec = importlib.util.spec_from_file_location("fixed_v6_assembler_test", SOURCE)
    if spec is None or spec.loader is None:
        raise ImportError(SOURCE)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


M = load_source()


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def fixture():
    count = 12
    high_expected = M.B.expected_branches(M.B.ALPHA2, count)
    low_expected = M.B.expected_branches(M.B.ALPHA1, count)
    stat = {
        "active_shifts": 1, "packed_terms": 1, "tag_groups": 1,
        "collected_affine_terms": 1, "requested_moments": 1,
        "scalar_products": 1, "nonzero_product_monomials": 1,
        "cancelled_product_monomials": 0,
        "maximum_affine_denominator_bits": 1,
        "maximum_moment_denominator_bits": 1,
    }
    degree, ceiling = 2, 48
    provisional = 60**degree * math.factorial(ceiling)
    radial = {
        "orbit_tag_associations": 2, "orbit_transforms": 1,
        "transform_terms": 1, "radial_denominator_bits": provisional.bit_length(),
        "distributed_terms": 1, "packed_nonzero_terms": 1,
        "maximum_shift_pruned_inside_convolution": 2,
        "fixed_provisional_denominator_bits": provisional.bit_length(),
        "fixed_denominator_common_gcd_bits": 1,
        "maximum_orbit_degree": degree, "factorial_ceiling": ceiling,
    }
    row = {
        "format": "D14-grid38-scaled-cutoff-cross-common-r-fixed-v6",
        "status": "EXACT FIXED-DENOMINATOR COMMON-r CROSS SHARD PASS",
        "rigorous": True, "serialized_matrices_read": False,
        "common_r": count, "producer_sha256": M.V6_RUNNER_SHA256,
        "algorithm": M.V6_ALGORITHM, "source_hashes": M.V6_SOURCE_HASHES,
        **M.expected_identity(),
        "scaled_b_shard": str(48 * len(high_expected)),
        "branch_values_and_fast_stats": {
            "high": {branch: "1" for branch in high_expected},
            "low": {branch: "0" for branch in low_expected},
            "high_stats": {branch: dict(stat) for branch in high_expected},
            "low_stats": {branch: dict(stat) for branch in low_expected},
            "integer_radialization": {
                "family_denominator": "1",
                "radial_denominator": str(provisional),
                "combined_denominator_bits": provisional.bit_length(),
                "clear_stats": {
                    "family_coefficients": 2, "common_denominator_bits": 1},
                "radial_stats": radial,
                "active_branch_families": ["small", "small_total"],
                "inactive_families_pruned_before_radialization": ["large"],
            },
            "timing_seconds": {},
        },
        "family_stats": {
            "source_kernel_terms": 1,
            "literal_antiderivative_expansions": 2,
            "family_tag_counts": {
                "small": 1, "small_total": 1, "large": 1},
            "family_orbit_tag_entries": {
                "small": 1, "small_total": 1, "large": 1},
        },
        "kernel_stats": {
            "marginal_terms": 1, "distinguished_components": 1,
            "input_pairs": 1, "expanded_orbit_products": 1,
            "output_orbits": 1, "output_kernel_terms": 1,
        },
        "peak_rss_kib": 1, "timing_seconds": {},
    }
    return row


class FixedV6AssemblerTest(unittest.TestCase):
    def test_exact_factor_and_denominator_contract(self):
        row = fixture()
        self.assertEqual(M.parse_b_shard(Path("r12.json"), canonical(row), 12), 96)
        row["scaled_b_shard"] = "97"
        with self.assertRaises(ArithmeticError):
            M.parse_b_shard(Path("r12.json"), canonical(row), 12)

    def test_pruning_and_denominator_mutations_rejected(self):
        row = fixture()
        row["branch_values_and_fast_stats"]["integer_radialization"][
            "active_branch_families"] = ["large", "small", "small_total"]
        with self.assertRaises(ArithmeticError):
            M.parse_b_shard(Path("r12.json"), canonical(row), 12)
        row = fixture()
        row["branch_values_and_fast_stats"]["integer_radialization"][
            "clear_stats"]["family_coefficients"] = 3
        with self.assertRaises(ArithmeticError):
            M.parse_b_shard(Path("r12.json"), canonical(row), 12)
        row = fixture()
        row["branch_values_and_fast_stats"]["integer_radialization"][
            "radial_stats"]["factorial_ceiling"] = 10**9
        with self.assertRaises(ArithmeticError):
            M.parse_b_shard(Path("r12.json"), canonical(row), 12)
        row = fixture()
        row["branch_values_and_fast_stats"]["integer_radialization"][
            "radial_denominator"] = "7"
        with self.assertRaises(ArithmeticError):
            M.parse_b_shard(Path("r12.json"), canonical(row), 12)


if __name__ == "__main__":
    unittest.main()
