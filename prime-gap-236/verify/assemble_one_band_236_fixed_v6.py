#!/usr/bin/env python3
"""Fail-closed exact scalar assembly for fixed-denominator-v6 b shards.

The hash-pinned v5 assembler supplies the independently audited A parsing,
inner-form normalization, shard-set completeness check, and final projection
algebra.  This thin revision replaces only the b-shard wire contract by the
fixed-v6 contract.  It remains a summation/provenance layer, not an
integration replay.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import math
from pathlib import Path
import sys


if hasattr(sys, "set_int_max_str_digits"):
    sys.set_int_max_str_digits(0)

FILE = Path(__file__).resolve()
REPO = FILE.parents[1]
BASE = FILE.with_name("assemble_one_band_236_shards.py")
BASE_SHA256 = \
    "9963c94207ab4954ea235fe9c044fe240df2f74c8df5abe83e32467600648374"
V6_RUNNER = REPO / (
    "agents/exact-projection-engine/"
    "d14_grid38_scaled_b_shard_fixed_v6.py")
V6_RUNNER_SHA256 = \
    "89c7c57aa439b0535bd17b85683dd1fd4ece2d1439e1b5d8bd9562c44eb57e17"
V6_BACKEND = REPO / "agents/exact-projection-engine/fixed_denominator_radial.py"
V6_BACKEND_SHA256 = \
    "430d6376d803abaad40c3bf9fb88d5f4db75ad144649e8c9446d47f1e771b228"
V6_TEST = REPO / "agents/exact-projection-engine/test_fixed_denominator_radial.py"
V6_TEST_SHA256 = \
    "a02f51377800e4906e711da2cd62bd4f406999b73d8bb58dfa2e6d0eb1ed2f45"
DEFAULT_B_DIR = REPO / (
    "agents/exact-projection-engine/results/"
    "d14_grid38_scaled_b_fixed_v6")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_base():
    data = BASE.read_bytes()
    if sha256(data) != BASE_SHA256:
        raise RuntimeError("pinned v5 scalar assembler changed")
    spec = importlib.util.spec_from_file_location(
        "one_band_236_fixed_v6_pinned_base", BASE)
    if spec is None or spec.loader is None:
        raise ImportError(BASE)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


B = load_base()
V6_ALGORITHM = {
    "family_common_denominator_integer_accumulation": True,
    "direct_fixed_denominator_partition_radial_integers": True,
    "fixed_denominator_globally_gcd_reduced": True,
    "coefficient_map_and_reduced_denominator_equal_v3_in_tests": True,
    "empty_shifts_pruned_inside_small_coordinate_convolution": True,
    "inactive_branch_families_pruned_before_radialization": True,
    "complete_affine_radial_product_collected_by_final_monomial": True,
    "moment_common_denominator_integer_contraction": True,
    "denominators_restored_exactly": True,
    "full_low_k_v3_and_v5_branch_equality_in_pinned_tests": True,
}
V6_SOURCE_HASHES = dict(B.B_SOURCE_HASHES)
V6_SOURCE_HASHES.update({
    "agents/exact-projection-engine/d14_grid38_scaled_b_shard_collected_v5.py":
        B.PINNED[B.B_RUNNER],
    str(V6_BACKEND.relative_to(REPO)): V6_BACKEND_SHA256,
    str(V6_TEST.relative_to(REPO)): V6_TEST_SHA256,
})
PINS = dict(B.PINNED)
PINS.update({
    BASE: BASE_SHA256,
    V6_RUNNER: V6_RUNNER_SHA256,
    V6_BACKEND: V6_BACKEND_SHA256,
    V6_TEST: V6_TEST_SHA256,
})


def positive_integer_string(value, label: str) -> int:
    parsed = B.canonical_q(value, label)
    if parsed.denominator != 1 or parsed <= 0:
        raise ValueError(f"{label} is not a positive integer")
    return parsed.numerator


def expected_identity():
    return {
        "scaling": {
            "inner_F": str(B.SCALE_F), "outer_H": str(B.SCALE_H),
            "b_factor": str(B.SCALE_F * B.SCALE_H),
            "invariant": "b_scaled^2/A_scaled = 10^174*(b^2/A)",
        },
        "geometry": {
            "k": B.K, "delta": str(B.DELTA), "alpha1": str(B.ALPHA1),
            "alpha2": str(B.ALPHA2), "eta": str(B.ETA),
            "natural_dilation_alpha1_over_alpha2": str(B.DILATION),
            "schedule": list(map(str, B.SCHEDULE)),
            "definition5_cutoff_retained": True,
        },
        "candidate": {
            "inner": "pinned strict cache-free exact D19 v2",
            "outer": "D14_grid_1e-38", "inner_basis_dimension": 568,
            "outer_basis_dimension": 195,
            "inner_common_denominator_lcm": str(B.SCALE_F),
            "outer_common_denominator_lcm": str(B.SCALE_H),
            "dilation_point_check": True,
        },
    }


def parse_b_shard(path: Path, data: bytes, count: int):
    row = B.strict_json(data, str(path))
    top = {
        "algorithm", "branch_values_and_fast_stats", "candidate", "common_r",
        "family_stats", "format", "geometry", "kernel_stats", "peak_rss_kib",
        "producer_sha256", "rigorous", "scaled_b_shard", "scaling",
        "serialized_matrices_read", "source_hashes", "status", "timing_seconds",
    }
    if (type(row) is not dict or set(row) != top or
            row.get("format") !=
                "D14-grid38-scaled-cutoff-cross-common-r-fixed-v6" or
            row.get("status") !=
                "EXACT FIXED-DENOMINATOR COMMON-r CROSS SHARD PASS" or
            row.get("rigorous") is not True or
            type(row.get("common_r")) is not int or
            row.get("common_r") != count or
            row.get("producer_sha256") != V6_RUNNER_SHA256 or
            row.get("serialized_matrices_read") is not False or
            row.get("algorithm") != V6_ALGORITHM or
            row.get("source_hashes") != V6_SOURCE_HASHES):
        raise ValueError(f"fixed-v6 b shard identity mismatch: {path}")
    identity = expected_identity()
    if any(row.get(key) != value for key, value in identity.items()):
        raise ValueError(f"fixed-v6 b shard geometry/candidate mismatch: {path}")

    kernel_keys = {
        "marginal_terms", "distinguished_components", "input_pairs",
        "expanded_orbit_products", "output_orbits", "output_kernel_terms",
    }
    kernel = row.get("kernel_stats")
    B.check_integer_map(kernel, kernel_keys, f"b[{count}].kernel_stats")
    if (min(kernel.values()) <= 0 or
            kernel["input_pairs"] !=
                kernel["marginal_terms"] * kernel["distinguished_components"] or
            kernel["expanded_orbit_products"] < kernel["output_kernel_terms"] or
            kernel["output_kernel_terms"] < kernel["output_orbits"]):
        raise ArithmeticError(f"fixed-v6 kernel inventory failed: {path}")
    families = row.get("family_stats")
    family_names = {"small", "small_total", "large"}
    if type(families) is not dict or set(families) != {
            "source_kernel_terms", "literal_antiderivative_expansions",
            "family_tag_counts", "family_orbit_tag_entries"}:
        raise ValueError(f"fixed-v6 family schema malformed: {path}")
    B.require_nonnegative_int(families["source_kernel_terms"],
                              f"b[{count}].source_kernel_terms")
    B.require_nonnegative_int(families["literal_antiderivative_expansions"],
                              f"b[{count}].literal_expansions")
    B.check_integer_map(families["family_tag_counts"], family_names,
                        f"b[{count}].family_tag_counts")
    B.check_integer_map(families["family_orbit_tag_entries"], family_names,
                        f"b[{count}].family_orbit_tag_entries")
    if (families["source_kernel_terms"] != kernel["output_kernel_terms"] or
            families["literal_antiderivative_expansions"] <=
                families["source_kernel_terms"] or
            min(families["family_tag_counts"].values()) <= 0 or
            min(families["family_orbit_tag_entries"].values()) <= 0):
        raise ArithmeticError(f"fixed-v6 primitive-family inventory failed: {path}")

    diagnostics = row.get("branch_values_and_fast_stats")
    if type(diagnostics) is not dict or set(diagnostics) != {
            "high", "low", "high_stats", "low_stats",
            "integer_radialization", "timing_seconds"}:
        raise ValueError(f"fixed-v6 b diagnostics malformed: {path}")
    high_expected = B.expected_branches(B.ALPHA2, count)
    low_expected = B.expected_branches(B.ALPHA1, count)
    high, low = diagnostics["high"], diagnostics["low"]
    if (type(high) is not dict or type(low) is not dict or
            set(high) != high_expected or set(low) != low_expected):
        raise ValueError(f"fixed-v6 b branch inventory mismatch: {path}")
    high_total = sum((B.canonical_q(value, f"b[{count}].high.{branch}")
                      for branch, value in high.items()), B.Q(0))
    low_total = sum((B.canonical_q(value, f"b[{count}].low.{branch}")
                     for branch, value in low.items()), B.Q(0))
    observed = B.canonical_q(row.get("scaled_b_shard"), f"b[{count}]")
    if observed != B.K * (high_total - low_total):
        raise ArithmeticError(f"fixed-v6 factor-48 recombination failed: {path}")

    stat_keys = {
        "active_shifts", "packed_terms", "tag_groups",
        "collected_affine_terms", "requested_moments", "scalar_products",
        "nonzero_product_monomials", "cancelled_product_monomials",
        "maximum_affine_denominator_bits", "maximum_moment_denominator_bits",
    }
    for side, expected in (("high_stats", high_expected),
                           ("low_stats", low_expected)):
        stats = diagnostics[side]
        if type(stats) is not dict or set(stats) != expected:
            raise ValueError(f"fixed-v6 b statistics branch mismatch: {path}")
        for branch, values in stats.items():
            B.check_integer_map(values, stat_keys,
                                f"b[{count}].{side}.{branch}")
            if (values["requested_moments"] !=
                    values["nonzero_product_monomials"] or
                    values["scalar_products"] <
                    values["nonzero_product_monomials"] or
                    values["scalar_products"] <
                    values["collected_affine_terms"]):
                raise ArithmeticError(
                    f"fixed-v6 collection inventory failed: {path}")

    integer = diagnostics["integer_radialization"]
    integer_keys = {
        "family_denominator", "radial_denominator",
        "combined_denominator_bits", "clear_stats", "radial_stats",
        "active_branch_families",
        "inactive_families_pruned_before_radialization",
    }
    if type(integer) is not dict or set(integer) != integer_keys:
        raise ValueError(f"fixed-v6 radial metadata malformed: {path}")
    active = set()
    for branch in high_expected | low_expected:
        active.add({"Sdelta": "small", "Stotal": "small_total",
                    "Ltotal": "large", "Lbig": "large"}[branch])
    all_families = family_names
    if (integer["active_branch_families"] != sorted(active) or
            integer["inactive_families_pruned_before_radialization"] !=
                sorted(all_families - active)):
        raise ArithmeticError(f"fixed-v6 family pruning mismatch: {path}")
    family_denominator = positive_integer_string(
        integer["family_denominator"], f"b[{count}].family_denominator")
    radial_denominator = positive_integer_string(
        integer["radial_denominator"], f"b[{count}].radial_denominator")
    if integer["combined_denominator_bits"] != \
            (family_denominator * radial_denominator).bit_length():
        raise ArithmeticError(f"fixed-v6 combined denominator mismatch: {path}")
    clear = integer["clear_stats"]
    B.check_integer_map(clear, {"family_coefficients", "common_denominator_bits"},
                        f"b[{count}].clear_stats")
    radial_keys = {
        "orbit_tag_associations", "orbit_transforms", "transform_terms",
        "radial_denominator_bits", "distributed_terms",
        "packed_nonzero_terms", "maximum_shift_pruned_inside_convolution",
        "fixed_provisional_denominator_bits",
        "fixed_denominator_common_gcd_bits", "maximum_orbit_degree",
        "factorial_ceiling",
    }
    radial = integer["radial_stats"]
    B.check_integer_map(radial, radial_keys, f"b[{count}].radial_stats")
    degree = radial["maximum_orbit_degree"]
    ceiling = radial["factorial_ceiling"]
    # Validate the small target-bound integers before exponentiation or
    # factorial evaluation, so malformed metadata cannot force resource
    # exhaustion ahead of a deterministic rejection.
    if degree > 64 or ceiling != degree + 46:
        raise ArithmeticError(f"fixed-v6 degree/factorial ceiling failed: {path}")
    provisional = 60**degree * math.factorial(ceiling)
    expected_coefficients = sum(
        families["family_orbit_tag_entries"][family] for family in active)
    if (radial["maximum_shift_pruned_inside_convolution"] != 14 - count or
            radial["radial_denominator_bits"] != radial_denominator.bit_length() or
            radial["fixed_provisional_denominator_bits"] !=
                provisional.bit_length() or
            provisional % radial_denominator or
            radial["fixed_denominator_common_gcd_bits"] !=
                (provisional // radial_denominator).bit_length() or
            clear["common_denominator_bits"] != family_denominator.bit_length() or
            clear["family_coefficients"] != expected_coefficients or
            radial["orbit_tag_associations"] != expected_coefficients or
            min(radial[key] for key in (
                "orbit_tag_associations", "orbit_transforms",
                "transform_terms", "packed_nonzero_terms")) <= 0 or
            radial["orbit_transforms"] > expected_coefficients or
            radial["distributed_terms"] < radial["transform_terms"] or
            radial["distributed_terms"] < radial["packed_nonzero_terms"]):
        raise ArithmeticError(f"fixed-v6 radial denominator/work mismatch: {path}")
    B.require_nonnegative_int(row.get("peak_rss_kib"), f"b[{count}].peak_rss")
    return observed


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--a-dir", type=Path, default=B.DEFAULT_A_DIR)
    parser.add_argument("--b-dir", type=Path, default=DEFAULT_B_DIR)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--expected-self-sha256", required=True)
    args = parser.parse_args(argv)
    self_data = FILE.read_bytes()
    if sha256(self_data) != args.expected_self_sha256:
        raise RuntimeError("fixed-v6 assembler source does not match external pin")
    snapshots = {path: path.read_bytes() for path in PINS}
    for path, expected in PINS.items():
        if sha256(snapshots[path]) != expected:
            raise RuntimeError(f"pinned fixed-v6 dependency changed: {path}")
    old_parser = B.parse_b_shard
    try:
        B.parse_b_shard = parse_b_shard
        result = B.build(args.a_dir, args.b_dir, snapshots)
    finally:
        B.parse_b_shard = old_parser
    if (FILE.read_bytes() != self_data or
            any(path.read_bytes() != data for path, data in snapshots.items())):
        raise RuntimeError("fixed-v6 assembler source closure changed")
    result["format"] = "H1-236-one-band-fixed-v6-exact-shard-aggregate-v1"
    result["assembler_sha256"] = args.expected_self_sha256
    result["base_assembler_sha256"] = BASE_SHA256
    result["b_engine"] = "fixed-denominator-v6"
    result["source_hashes"] = {
        str(path.relative_to(REPO)): expected for path, expected in PINS.items()
    }
    payload = B.canonical_json(result)
    B.publish_exclusive(args.output, payload)
    print(sha256(payload), args.output)
    return 0 if result["theorem_ready_scalar"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
