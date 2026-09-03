#!/usr/bin/env python3
"""Fail-closed structural/result checker for frozen collected-v5 shards."""

from __future__ import annotations

import argparse
from fractions import Fraction as Q
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path


FILE = Path(__file__).resolve()
REPO = FILE.parents[2]
BASE_AUDITOR_PATH = FILE.with_name("verify_pruned_v3_cross_shard.py")
BASE_AUDITOR_SHA = "0abbf021581092ed4b27a1ee303046ad349804d50f7c4882a307cee9b750ba92"
PRODUCER = "agents/exact-projection-engine/d14_grid38_scaled_b_shard_collected_v5.py"
PRODUCER_SHA = "eaa22454347d17201c60c30e1ed5ac01e34ba39368bc4711c1ea2c7f6d03ba82"


def sha256(data):
    if isinstance(data, (str, Path)):
        data = Path(data).read_bytes()
    return hashlib.sha256(data).hexdigest()


if sha256(BASE_AUDITOR_PATH) != BASE_AUDITOR_SHA:
    raise RuntimeError("pinned common cross-shard auditor changed")
_spec = importlib.util.spec_from_file_location(
    "collected_v5_common_audit", BASE_AUDITOR_PATH)
if _spec is None or _spec.loader is None:
    raise ImportError(BASE_AUDITOR_PATH)
B = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(B)


SOURCE_HASHES = dict(B.FAST_V2_SOURCE_HASHES)
SOURCE_HASHES.update({
    "agents/exact-projection-engine/d14_grid38_scaled_b_shard_fast_v2.py":
        "4613b0fb117bf58c732e9bdeb22fa9d847a1152cc1bcac3b8b92f584231709d3",
    "agents/exact-projection-engine/pruned_integer_radial.py":
        "834f624647094bf71364ad5c2b47e00371c7e7e78ed37c1d06eeca9186f73afe",
    "agents/exact-projection-engine/collected_integer_scalar.py":
        "aef0a183d71b9c41b5373806d03481b94cb4e61a1ff3561888b8c31f94e8c890",
    "agents/exact-projection-engine/test_pruned_integer_radial.py":
        "17b5eac692f859728d502e90a52b2c9c5ce03ef45e7966ce9104d8878910adfd",
    "agents/exact-projection-engine/test_collected_integer_scalar.py":
        "281ff70246041cc0d2ed948c41187b406a26b9d7ba9b94a1f4b502dab63d31d4",
    "agents/exact-projection-engine/d14_grid38_scaled_b_shard_pruned_v3.py":
        "ce5236eaed52be549a316587e8c3c543a0b02b1594c14ba32f4c1a877fd9bb26",
    "agents/exact-projection-engine/test_pruned_v3_exclusive_publish.py":
        "855b3e07ee71f75917a9ddceb2d969e10aab8c81550aa036423f7104eb5ef78d",
})
ALGORITHM = {
    "family_common_denominator_integer_accumulation": True,
    "radial_common_denominator_integer_accumulation": True,
    "empty_shifts_pruned_inside_small_coordinate_convolution": True,
    "affine_products_collected_once_per_tag_and_shift": True,
    "complete_affine_radial_product_collected_by_final_monomial": True,
    "affine_common_denominator_integer_collection": True,
    "moment_common_denominator_integer_contraction": True,
    "one_moment_multiplication_per_surviving_product_monomial": True,
    "denominators_restored_exactly_once_per_shift": True,
    "coefficient_level_reference_transform_equality_in_pinned_tests": True,
    "full_low_k_pruned_v3_branch_equality_in_pinned_tests": True,
}
TOP = {
    "algorithm", "branch_values_and_fast_stats", "candidate", "common_r",
    "family_stats", "format", "geometry", "kernel_stats", "peak_rss_kib",
    "producer_sha256", "rigorous", "scaled_b_shard", "scaling",
    "serialized_matrices_read", "source_hashes", "status", "timing_seconds",
}
COMMON_STATS = {
    "active_shifts", "packed_terms", "tag_groups",
    "collected_affine_terms", "requested_moments", "scalar_products",
}
V5_STATS = COMMON_STATS | {
    "nonzero_product_monomials", "cancelled_product_monomials",
    "maximum_affine_denominator_bits", "maximum_moment_denominator_bits",
}


def load_canonical(path):
    data = path.read_bytes()
    raw = B.strict_load(data, str(path))
    canonical = (json.dumps(
        raw, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
        allow_nan=False) + "\n").encode("ascii")
    if data != canonical:
        raise ValueError(f"noncanonical JSON: {path}")
    return raw, data


def expected_geometry():
    return {
        "k": B.K, "delta": str(B.DELTA), "alpha1": str(B.ALPHA1),
        "alpha2": str(B.ALPHA2), "eta": str(B.ETA),
        "natural_dilation_alpha1_over_alpha2": str(B.DILATION),
        "schedule": list(map(str, B.SCHEDULE)),
        "definition5_cutoff_retained": True,
    }


def expected_scaling():
    return {
        "inner_F": str(B.SCALE_F), "outer_H": str(B.SCALE_H),
        "b_factor": str(B.SCALE_F * B.SCALE_H),
        "invariant": "b_scaled^2/A_scaled = 10^174*(b^2/A)",
    }


def expected_candidate():
    return {
        "inner": "pinned strict cache-free exact D19 v2",
        "outer": "D14_grid_1e-38", "inner_basis_dimension": 568,
        "outer_basis_dimension": 195,
        "inner_common_denominator_lcm": str(B.SCALE_F),
        "outer_common_denominator_lcm": str(B.SCALE_H),
        "dilation_point_check": True,
    }


def check_v5_stats(stats, expected_branches, where):
    if type(stats) is not dict or set(stats) != expected_branches:
        raise ValueError(f"{where} branch inventory disagrees with geometry")
    for branch, row in stats.items():
        B.check_integer_map(row, V5_STATS, f"{where}.{branch}")
        if (row["requested_moments"] != row["nonzero_product_monomials"]
                or row["scalar_products"] < row["nonzero_product_monomials"]
                or row["scalar_products"] < row["collected_affine_terms"]
                or (row["active_shifts"] > 0 and
                    (row["maximum_affine_denominator_bits"] < 1 or
                     row["maximum_moment_denominator_bits"] < 1))):
            raise ArithmeticError(f"{where}.{branch} collection inventory failed")


def check_reference(reference_path, raw, block, r):
    reference, data = load_canonical(reference_path)
    fmt = reference.get("format")
    if fmt == "D14-grid38-scaled-cutoff-cross-common-r-fast-v2":
        status = "EXACT FAST COMMON-r CROSS SHARD PASS"
        producer = B.FAST_V2_PRODUCER_SHA
        hashes = B.FAST_V2_SOURCE_HASHES
    elif fmt == "D14-grid38-scaled-cutoff-cross-common-r-pruned-v3":
        status = "EXACT PRUNED COMMON-r CROSS SHARD PASS"
        producer = B.PRODUCER_SHA
        hashes = B.SOURCE_HASHES
        # Run the already pinned full v3 result checker as well.
        B.audit(reference_path)
    else:
        raise ValueError("reference is not a frozen fast-v2/pruned-v3 shard")
    if (type(reference) is not dict or set(reference) != TOP
            or reference.get("status") != status
            or reference.get("producer_sha256") != producer
            or reference.get("rigorous") is not True
            or reference.get("serialized_matrices_read") is not False
            or reference.get("common_r") != r
            or reference.get("source_hashes") != hashes
            or reference.get("geometry") != raw["geometry"]
            or reference.get("candidate") != raw["candidate"]
            or reference.get("scaling") != raw["scaling"]):
        raise ValueError("reference identity/source/geometry mismatch")
    reference_block = reference["branch_values_and_fast_stats"]
    if (reference["scaled_b_shard"] != raw["scaled_b_shard"]
            or reference_block["high"] != block["high"]
            or reference_block["low"] != block["low"]
            or reference["kernel_stats"] != raw["kernel_stats"]
            or reference["family_stats"] != raw["family_stats"]):
        raise ArithmeticError("v5 mathematical values differ bit-for-bit")
    for side in ("high_stats", "low_stats"):
        for branch, stats in block[side].items():
            old = reference_block[side][branch]
            for key in COMMON_STATS - {"requested_moments"}:
                if stats[key] != old[key]:
                    raise ArithmeticError(
                        f"v5/reference common work inventory differs: {side}.{branch}.{key}")
            if stats["requested_moments"] > old["requested_moments"]:
                raise ArithmeticError("global collection increased requested moments")
    integer = block["integer_radialization"]
    old_integer = reference_block["integer_radialization"]
    if (integer["family_denominator"] != old_integer["family_denominator"]
            or integer["radial_denominator"] != old_integer["radial_denominator"]
            or integer["combined_denominator_bits"] !=
                old_integer["combined_denominator_bits"]
            or integer["clear_stats"] != old_integer["clear_stats"]):
        raise ArithmeticError("v5/reference upstream denominator metadata differs")
    for key in {
            "orbit_tag_associations", "orbit_transforms", "transform_terms",
            "radial_denominator_bits", "distributed_terms", "packed_nonzero_terms"}:
        if integer["radial_stats"][key] != old_integer["radial_stats"][key]:
            raise ArithmeticError(f"v5/reference radial inventory differs: {key}")
    return sha256(data), fmt


def audit(path, reference_path=None):
    raw, raw_bytes = load_canonical(path)
    if type(raw) is not dict or set(raw) != TOP:
        raise ValueError("unexpected or incomplete v5 top-level schema")
    if (raw["format"] != "D14-grid38-scaled-cutoff-cross-common-r-collected-v5"
            or raw["status"] != "EXACT COLLECTED COMMON-r CROSS SHARD PASS"
            or raw["rigorous"] is not True
            or raw["serialized_matrices_read"] is not False
            or raw["producer_sha256"] != PRODUCER_SHA):
        raise ValueError("v5 identity/status mismatch")
    r = raw["common_r"]
    if type(r) is not int or not 0 <= r <= 12:
        raise ValueError("invalid common_r")
    if (raw["geometry"] != expected_geometry()
            or raw["scaling"] != expected_scaling()
            or raw["candidate"] != expected_candidate()
            or raw["algorithm"] != ALGORITHM):
        raise ValueError("v5 frozen geometry/candidate/algorithm mismatch")
    if raw["source_hashes"] != SOURCE_HASHES:
        raise ValueError("v5 serialized source closure mismatch")
    if sha256(REPO / PRODUCER) != PRODUCER_SHA:
        raise ValueError("live v5 producer hash mismatch")
    for relative, digest in SOURCE_HASHES.items():
        if sha256(REPO / relative) != digest:
            raise ValueError(f"live v5 source hash mismatch: {relative}")

    B.check_integer_map(raw["kernel_stats"], {
        "marginal_terms", "distinguished_components", "input_pairs",
        "expanded_orbit_products", "output_orbits", "output_kernel_terms",
    }, "kernel_stats")
    kernel = raw["kernel_stats"]
    if (min(kernel.values()) <= 0
            or kernel["input_pairs"] !=
                kernel["marginal_terms"] * kernel["distinguished_components"]
            or kernel["expanded_orbit_products"] < kernel["output_kernel_terms"]
            or kernel["output_kernel_terms"] < kernel["output_orbits"]):
        raise ArithmeticError("kernel inventory relation failed")
    families = raw["family_stats"]
    if type(families) is not dict or set(families) != {
            "source_kernel_terms", "literal_antiderivative_expansions",
            "family_tag_counts", "family_orbit_tag_entries"}:
        raise ValueError("family_stats schema mismatch")
    B.require_nonnegative_int(families["source_kernel_terms"], "source terms")
    B.require_nonnegative_int(families["literal_antiderivative_expansions"],
                              "antiderivative expansions")
    B.check_integer_map(families["family_tag_counts"],
                        {"small", "small_total", "large"}, "family tags")
    B.check_integer_map(families["family_orbit_tag_entries"],
                        {"small", "small_total", "large"}, "family entries")
    if (families["source_kernel_terms"] != kernel["output_kernel_terms"]
            or families["literal_antiderivative_expansions"] <=
                families["source_kernel_terms"]
            or min(families["family_tag_counts"].values()) <= 0
            or min(families["family_orbit_tag_entries"].values()) <= 0):
        raise ArithmeticError("family inventory relation failed")

    block = raw["branch_values_and_fast_stats"]
    if type(block) is not dict or set(block) != {
            "high", "low", "high_stats", "low_stats",
            "integer_radialization", "timing_seconds"}:
        raise ValueError("v5 diagnostic schema mismatch")
    high_expected = B.expected_branches(B.ALPHA2, r)
    low_expected = B.expected_branches(B.ALPHA1, r)
    if set(block["high"]) != high_expected or set(block["low"]) != low_expected:
        raise ValueError("v5 branch inventory disagrees with exact geometry")
    high = {key: B.rational(value, f"high.{key}")
            for key, value in block["high"].items()}
    low = {key: B.rational(value, f"low.{key}")
           for key, value in block["low"].items()}
    check_v5_stats(block["high_stats"], high_expected, "high_stats")
    check_v5_stats(block["low_stats"], low_expected, "low_stats")
    observed = B.rational(raw["scaled_b_shard"], "scaled_b_shard")
    if observed != B.K * (sum(high.values(), Q(0)) - sum(low.values(), Q(0))):
        raise ArithmeticError("v5 branches do not recombine with factor 48")

    integer = block["integer_radialization"]
    if type(integer) is not dict or set(integer) != {
            "family_denominator", "radial_denominator",
            "combined_denominator_bits", "clear_stats", "radial_stats"}:
        raise ValueError("v5 integer-radial metadata schema mismatch")
    family_den = B.positive_integer_string(integer["family_denominator"],
                                           "family denominator")
    radial_den = B.positive_integer_string(integer["radial_denominator"],
                                           "radial denominator")
    if integer["combined_denominator_bits"] != \
            (family_den * radial_den).bit_length():
        raise ArithmeticError("v5 combined denominator bit length mismatch")
    B.check_integer_map(integer["clear_stats"], {
        "family_coefficients", "common_denominator_bits"}, "clear_stats")
    B.check_integer_map(integer["radial_stats"], {
        "orbit_tag_associations", "orbit_transforms", "transform_terms",
        "radial_denominator_bits", "distributed_terms", "packed_nonzero_terms",
        "maximum_shift_pruned_inside_convolution"}, "radial_stats")
    clear, radial = integer["clear_stats"], integer["radial_stats"]
    expected_coefficients = sum(families["family_orbit_tag_entries"].values())
    expected_h = B.maximum_active_shift(B.ETA - r * B.DELTA)
    if (expected_h != 14 - r
            or radial["maximum_shift_pruned_inside_convolution"] != expected_h
            or clear["common_denominator_bits"] != family_den.bit_length()
            or radial["radial_denominator_bits"] != radial_den.bit_length()
            or clear["family_coefficients"] != expected_coefficients
            or radial["orbit_tag_associations"] != expected_coefficients
            or radial["orbit_transforms"] <= 0 or radial["transform_terms"] <= 0
            or radial["distributed_terms"] < radial["packed_nonzero_terms"]
            or radial["packed_nonzero_terms"] <= 0):
        raise ArithmeticError("v5 pruned-radial inventory relation failed")

    timing = raw["timing_seconds"]
    nested = block["timing_seconds"]
    if (type(timing) is not dict or set(timing) != {
            "marginal_and_components", "global_kernel", "primitive_families",
            "integer_radialize_and_collected_integrate", "total"}
            or type(nested) is not dict or set(nested) != {
                "clear_family_denominators", "radialize_integer",
                "integrate_globally_collected_integers"}):
        raise ValueError("v5 timing schema mismatch")
    for values in (timing, nested):
        if any(type(value) not in (int, float) or isinstance(value, bool)
               or not math.isfinite(value) or value < 0
               for value in values.values()):
            raise ValueError("invalid v5 timing value")
    if timing["total"] < max(value for key, value in timing.items()
                              if key != "total"):
        raise ArithmeticError("v5 total time smaller than component")
    B.require_nonnegative_int(raw["peak_rss_kib"], "peak_rss_kib")

    reference_sha = reference_format = None
    if reference_path is not None:
        reference_sha, reference_format = check_reference(
            reference_path, raw, block, r)
    return {
        "status": "COLLECTED-V5 CROSS SHARD STRUCTURAL/RESULT AUDIT PASS",
        "input_sha256": sha256(raw_bytes), "common_r": r,
        "scaled_b_shard": str(observed), "recombined_exactly": True,
        "maximum_active_shift": expected_h, "source_closure_verified": True,
        "reference_mathematical_fields_bit_equal":
            True if reference_path is not None else None,
        "reference_format": reference_format,
        "reference_sha256": reference_sha,
        "total_scalar_products": sum(
            row["scalar_products"] for side in ("high_stats", "low_stats")
            for row in block[side].values()),
        "total_surviving_product_monomials": sum(
            row["nonzero_product_monomials"]
            for side in ("high_stats", "low_stats")
            for row in block[side].values()),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--expected-self-sha256")
    parser.add_argument("--reference", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("shard", type=Path)
    args = parser.parse_args()
    if args.expected_self_sha256 is not None and \
            sha256(FILE) != args.expected_self_sha256:
        raise RuntimeError("externally pinned v5 checker SHA mismatch")
    result = audit(args.shard, args.reference)
    payload = (json.dumps(
        result, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
        allow_nan=False) + "\n").encode("ascii")
    if args.output is None:
        print(payload.decode("ascii"), end="")
        return
    args.output.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                         0o444)
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())
    print(json.dumps({
        "status": result["status"], "common_r": result["common_r"],
        "output": str(args.output), "output_sha256": sha256(payload),
    }, sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    main()
