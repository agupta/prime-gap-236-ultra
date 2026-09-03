#!/usr/bin/env python3
"""Fail-closed structural/result checker for frozen fixed-v6 cross shards.

This checker does not import production integration code.  It derives the
Definition-5 branch/family inventory and H=14-r from frozen rationals, checks
the complete serialized/live source closure, verifies the fixed-denominator
and gcd metadata arithmetically, and recombines exact branch values with one
factor 48.  An optional same-r collected-v5 result is checked independently
and compared in every mathematical field.
"""

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
V5_CHECKER_PATH = FILE.with_name("verify_collected_v5_cross_shard.py")
V5_CHECKER_SHA = (
    "11e2930bce62f13faf8c4874a439ab02220e155a384ea1f0e0587a871cb4abb9")
PRODUCER = (
    "agents/exact-projection-engine/"
    "d14_grid38_scaled_b_shard_fixed_v6.py")
PRODUCER_SHA = (
    "89c7c57aa439b0535bd17b85683dd1fd4ece2d1439e1b5d8bd9562c44eb57e17")


def sha256(value):
    if isinstance(value, (str, Path)):
        value = Path(value).read_bytes()
    return hashlib.sha256(value).hexdigest()


if sha256(V5_CHECKER_PATH) != V5_CHECKER_SHA:
    raise RuntimeError("pinned collected-v5 result checker changed")
_spec = importlib.util.spec_from_file_location(
    "fixed_v6_pinned_v5_auditor", V5_CHECKER_PATH)
if _spec is None or _spec.loader is None:
    raise ImportError(V5_CHECKER_PATH)
V5 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(V5)
B = V5.B


SOURCE_HASHES = dict(V5.SOURCE_HASHES)
SOURCE_HASHES.update({
    "agents/exact-projection-engine/"
    "d14_grid38_scaled_b_shard_collected_v5.py":
        "eaa22454347d17201c60c30e1ed5ac01e34ba39368bc4711c1ea2c7f6d03ba82",
    "agents/exact-projection-engine/fixed_denominator_radial.py":
        "430d6376d803abaad40c3bf9fb88d5f4db75ad144649e8c9446d47f1e771b228",
    "agents/exact-projection-engine/test_fixed_denominator_radial.py":
        "a02f51377800e4906e711da2cd62bd4f406999b73d8bb58dfa2e6d0eb1ed2f45",
})
ALGORITHM = {
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
TOP = V5.TOP
FAMILY_NAMES = {"small", "small_total", "large"}
BRANCH_FAMILY = {
    "Sdelta": "small", "Stotal": "small_total",
    "Ltotal": "large", "Lbig": "large",
}
FIXED_RADIAL_STATS = {
    "orbit_tag_associations", "orbit_transforms", "transform_terms",
    "radial_denominator_bits", "distributed_terms", "packed_nonzero_terms",
    "maximum_shift_pruned_inside_convolution",
    "fixed_provisional_denominator_bits",
    "fixed_denominator_common_gcd_bits", "maximum_orbit_degree",
    "factorial_ceiling",
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


def expected_active_families(high_branches, low_branches):
    return {BRANCH_FAMILY[branch]
            for branch in high_branches | low_branches}


def check_kernel_and_families(raw):
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
        raise ArithmeticError("v6 kernel inventory relation failed")

    families = raw["family_stats"]
    if type(families) is not dict or set(families) != {
            "source_kernel_terms", "literal_antiderivative_expansions",
            "family_tag_counts", "family_orbit_tag_entries"}:
        raise ValueError("v6 family_stats schema mismatch")
    B.require_nonnegative_int(families["source_kernel_terms"], "source terms")
    B.require_nonnegative_int(
        families["literal_antiderivative_expansions"],
        "antiderivative expansions")
    B.check_integer_map(families["family_tag_counts"], FAMILY_NAMES,
                        "family tag counts")
    B.check_integer_map(families["family_orbit_tag_entries"], FAMILY_NAMES,
                        "family entries")
    if (families["source_kernel_terms"] != kernel["output_kernel_terms"]
            or families["literal_antiderivative_expansions"] <=
                families["source_kernel_terms"]
            or min(families["family_tag_counts"].values()) <= 0
            or min(families["family_orbit_tag_entries"].values()) <= 0):
        raise ArithmeticError("v6 primitive-family inventory relation failed")
    return families


def check_reference(reference_path, raw, block, r, active):
    # This recursively checks the v5 reference's source closure, exact H,
    # branch geometry, denominator restoration, and factor-48 recombination.
    V5.audit(reference_path)
    reference, data = load_canonical(reference_path)
    if reference["common_r"] != r:
        raise ValueError("v5 reference count mismatch")
    reference_block = reference["branch_values_and_fast_stats"]
    if (reference["scaled_b_shard"] != raw["scaled_b_shard"]
            or reference_block["high"] != block["high"]
            or reference_block["low"] != block["low"]
            or reference["kernel_stats"] != raw["kernel_stats"]
            or reference["family_stats"] != raw["family_stats"]
            or reference["geometry"] != raw["geometry"]
            or reference["candidate"] != raw["candidate"]
            or reference["scaling"] != raw["scaling"]):
        raise ArithmeticError("v6/v5 mathematical fields differ bit-for-bit")
    # Collection work on every actually evaluated branch depends only on the
    # exact active packed maps, and is unchanged even when r=12 drops an
    # entirely unused family before radialization.
    if (reference_block["high_stats"] != block["high_stats"]
            or reference_block["low_stats"] != block["low_stats"]):
        raise ArithmeticError("v6/v5 active-branch work inventory differs")

    # Through r=11 all families are active.  In that case v6 promises the
    # same reduced transform denominator and packed map as v3/v5, so require
    # exact upstream metadata equality for the common fields as well.
    if active == FAMILY_NAMES:
        old = reference_block["integer_radialization"]
        new = block["integer_radialization"]
        if (new["family_denominator"] != old["family_denominator"]
                or new["radial_denominator"] != old["radial_denominator"]
                or new["combined_denominator_bits"] !=
                    old["combined_denominator_bits"]
                or new["clear_stats"] != old["clear_stats"]):
            raise ArithmeticError("v6/v5 unpruned denominator metadata differs")
        for key in {
                "orbit_tag_associations", "orbit_transforms",
                "transform_terms", "radial_denominator_bits",
                "distributed_terms", "packed_nonzero_terms",
                "maximum_shift_pruned_inside_convolution"}:
            if new["radial_stats"][key] != old["radial_stats"][key]:
                raise ArithmeticError(
                    f"v6/v5 unpruned radial inventory differs: {key}")
    return sha256(data)


def audit(path, reference_path=None):
    raw, raw_bytes = load_canonical(path)
    if type(raw) is not dict or set(raw) != TOP:
        raise ValueError("unexpected or incomplete v6 top-level schema")
    if (raw["format"] !=
            "D14-grid38-scaled-cutoff-cross-common-r-fixed-v6"
            or raw["status"] !=
                "EXACT FIXED-DENOMINATOR COMMON-r CROSS SHARD PASS"
            or raw["rigorous"] is not True
            or raw["serialized_matrices_read"] is not False
            or raw["producer_sha256"] != PRODUCER_SHA):
        raise ValueError("v6 identity/status mismatch")
    r = raw["common_r"]
    if type(r) is not int or not 0 <= r <= 12:
        raise ValueError("invalid v6 common_r")
    if (raw["geometry"] != V5.expected_geometry()
            or raw["scaling"] != V5.expected_scaling()
            or raw["candidate"] != V5.expected_candidate()
            or raw["algorithm"] != ALGORITHM):
        raise ValueError("v6 frozen geometry/candidate/algorithm mismatch")
    if raw["source_hashes"] != SOURCE_HASHES:
        raise ValueError("v6 serialized source closure mismatch")
    if sha256(REPO / PRODUCER) != PRODUCER_SHA:
        raise ValueError("live v6 producer hash mismatch")
    for relative, expected in SOURCE_HASHES.items():
        if sha256(REPO / relative) != expected:
            raise ValueError(f"live v6 source hash mismatch: {relative}")

    families = check_kernel_and_families(raw)
    block = raw["branch_values_and_fast_stats"]
    if type(block) is not dict or set(block) != {
            "high", "low", "high_stats", "low_stats",
            "integer_radialization", "timing_seconds"}:
        raise ValueError("v6 diagnostic schema mismatch")
    high_expected = B.expected_branches(B.ALPHA2, r)
    low_expected = B.expected_branches(B.ALPHA1, r)
    if set(block["high"]) != high_expected or set(block["low"]) != low_expected:
        raise ValueError("v6 branch inventory disagrees with exact geometry")
    high = {key: B.rational(value, f"high.{key}")
            for key, value in block["high"].items()}
    low = {key: B.rational(value, f"low.{key}")
           for key, value in block["low"].items()}
    V5.check_v5_stats(block["high_stats"], high_expected, "high_stats")
    V5.check_v5_stats(block["low_stats"], low_expected, "low_stats")
    observed = B.rational(raw["scaled_b_shard"], "scaled_b_shard")
    if observed != B.K * (sum(high.values(), Q(0)) - sum(low.values(), Q(0))):
        raise ArithmeticError("v6 branches do not recombine with factor 48")

    integer = block["integer_radialization"]
    if type(integer) is not dict or set(integer) != {
            "family_denominator", "radial_denominator",
            "combined_denominator_bits", "clear_stats", "radial_stats",
            "active_branch_families",
            "inactive_families_pruned_before_radialization"}:
        raise ValueError("v6 integer-radial metadata schema mismatch")
    active = expected_active_families(high_expected, low_expected)
    inactive = FAMILY_NAMES-active
    if (integer["active_branch_families"] != sorted(active)
            or integer["inactive_families_pruned_before_radialization"] !=
                sorted(inactive)):
        raise ValueError("v6 active/inactive family inventory is not exact")
    family_den = B.positive_integer_string(
        integer["family_denominator"], "family denominator")
    radial_den = B.positive_integer_string(
        integer["radial_denominator"], "radial denominator")
    if integer["combined_denominator_bits"] != \
            (family_den*radial_den).bit_length():
        raise ArithmeticError("v6 combined denominator bit length mismatch")
    B.check_integer_map(integer["clear_stats"], {
        "family_coefficients", "common_denominator_bits"}, "clear_stats")
    B.check_integer_map(integer["radial_stats"], FIXED_RADIAL_STATS,
                        "radial_stats")
    clear = integer["clear_stats"]
    radial = integer["radial_stats"]
    expected_coefficients = sum(
        families["family_orbit_tag_entries"][family] for family in active)
    expected_h = B.maximum_active_shift(B.ETA-r*B.DELTA)
    degree = radial["maximum_orbit_degree"]
    ceiling = radial["factorial_ceiling"]
    if expected_h != 14-r or \
            radial["maximum_shift_pruned_inside_convolution"] != expected_h:
        raise ArithmeticError("v6 maximum shift is not exact H=14-r")
    # The frozen D19/D14 product cannot exceed degree 64.  Check this small
    # target bound, and the forced ceiling, before either exponentiation or
    # factorial evaluation so malformed wire metadata fails cheaply.
    if degree > 64 or ceiling != degree+(B.K-1)-1:
        raise ArithmeticError("v6 degree/factorial ceiling is invalid")
    provisional = B.DELTA.denominator**degree*math.factorial(ceiling)
    if radial["fixed_provisional_denominator_bits"] != provisional.bit_length():
        raise ArithmeticError("v6 provisional denominator bit length mismatch")
    if provisional % radial_den:
        raise ArithmeticError("v6 reduced radial denominator does not divide D")
    common_gcd = provisional//radial_den
    if radial["fixed_denominator_common_gcd_bits"] != common_gcd.bit_length():
        raise ArithmeticError("v6 fixed-denominator gcd metadata mismatch")
    if (clear["common_denominator_bits"] != family_den.bit_length()
            or radial["radial_denominator_bits"] != radial_den.bit_length()
            or clear["family_coefficients"] != expected_coefficients
            or radial["orbit_tag_associations"] != expected_coefficients
            or radial["orbit_transforms"] <= 0
            or radial["orbit_transforms"] > expected_coefficients
            or radial["transform_terms"] <= 0
            or radial["distributed_terms"] < radial["transform_terms"]
            or radial["distributed_terms"] < radial["packed_nonzero_terms"]
            or radial["packed_nonzero_terms"] <= 0):
        raise ArithmeticError("v6 fixed-radial work inventory relation failed")

    timing = raw["timing_seconds"]
    nested = block["timing_seconds"]
    if type(timing) is not dict or set(timing) != {
            "marginal_and_components", "global_kernel", "primitive_families",
            "integer_radialize_and_collected_integrate", "total"}:
        raise ValueError("v6 timing schema mismatch")
    if type(nested) is not dict or set(nested) != {
            "clear_family_denominators",
            "radialize_fixed_denominator_integers",
            "integrate_globally_collected_integers"}:
        raise ValueError("v6 nested timing schema mismatch")
    for where, values in (("top timing", timing), ("nested timing", nested)):
        if any(type(value) not in (int, float) or isinstance(value, bool)
               or not math.isfinite(value) or value < 0
               for value in values.values()):
            raise ValueError(f"invalid v6 {where}")
    if timing["total"] < max(value for key, value in timing.items()
                              if key != "total"):
        raise ArithmeticError("v6 total time smaller than component")
    B.require_nonnegative_int(raw["peak_rss_kib"], "peak_rss_kib")

    reference_sha = None
    if reference_path is not None:
        reference_sha = check_reference(reference_path, raw, block, r, active)
    return {
        "status": "FIXED-V6 CROSS SHARD STRUCTURAL/RESULT AUDIT PASS",
        "input_sha256": sha256(raw_bytes), "common_r": r,
        "scaled_b_shard": str(observed), "recombined_exactly": True,
        "maximum_active_shift": expected_h,
        "active_branch_families": sorted(active),
        "inactive_families_pruned_before_radialization": sorted(inactive),
        "maximum_orbit_degree": degree, "factorial_ceiling": ceiling,
        "fixed_denominator_relation_verified": True,
        "source_closure_verified": True,
        "reference_mathematical_fields_bit_equal":
            True if reference_path is not None else None,
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
        raise RuntimeError("externally pinned v6 checker SHA mismatch")
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
