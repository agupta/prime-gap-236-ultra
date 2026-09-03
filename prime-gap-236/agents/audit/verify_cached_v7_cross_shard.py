#!/usr/bin/env python3
"""Fail-closed structural/result checker for cached-v7 cross shards.

The mathematical checks are reduced exactly to the independently audited
fixed-v6 checker after first validating every v7-only wire difference.  The
two cache counters are diagnostics only: they count distinct immutable cache
keys in the fresh runner process and never enter a coefficient or integral.
An optional same-r fixed-v6 shard is audited separately and compared in all
mathematical and exact-work fields.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import tempfile


FILE = Path(__file__).resolve()
REPO = FILE.parents[2]
V6_CHECKER_PATH = FILE.with_name("verify_fixed_v6_cross_shard.py")
V6_CHECKER_SHA = (
    "46a8bd9b116a59078d5e3e6cc7a19887032421b60cbbb5afc605d205fa1ba954")
PRODUCER = (
    "agents/exact-projection-engine/"
    "d14_grid38_scaled_b_shard_cached_v7.py")
PRODUCER_SHA = (
    "b427c6961c377cb79d5a72b54f8c2e8c7642b87d66d338f53b5dc56d98991984")


def sha256(value):
    if isinstance(value, (str, Path)):
        value = Path(value).read_bytes()
    return hashlib.sha256(value).hexdigest()


if sha256(V6_CHECKER_PATH) != V6_CHECKER_SHA:
    raise RuntimeError("pinned fixed-v6 result checker changed")
_spec = importlib.util.spec_from_file_location(
    "cached_v7_pinned_v6_auditor", V6_CHECKER_PATH)
if _spec is None or _spec.loader is None:
    raise ImportError(V6_CHECKER_PATH)
V6 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(V6)


SOURCE_HASHES = dict(V6.SOURCE_HASHES)
SOURCE_HASHES.update({
    "agents/exact-projection-engine/"
    "d14_grid38_scaled_b_shard_fixed_v6.py":
        "89c7c57aa439b0535bd17b85683dd1fd4ece2d1439e1b5d8bd9562c44eb57e17",
    "agents/exact-projection-engine/cached_fixed_denominator_radial.py":
        "79c9a8ef26de0b7fba55fbdb6e113a88f0b52b20f9cbcb34cbc2dbb507ba74c4",
    "agents/exact-projection-engine/test_cached_fixed_denominator_radial.py":
        "0f0bd15426ff961e47281b32d57795f1848e75280fd645abc599df8d1410fd5b",
})
ALGORITHM = {
    "direct_fixed_denominator_partition_radial_integers": True,
    "fixed_denominator_globally_gcd_reduced": True,
    "factorial_ratios_cached_outside_partition_inner_loops": True,
    "rational_cap_powers_cached_outside_partition_inner_loops": True,
    "coefficient_denominator_and_packed_maps_equal_fixed_v6_in_tests": True,
    "inactive_branch_families_pruned_before_radialization": True,
    "complete_affine_radial_product_collected_by_final_monomial": True,
    "moment_common_denominator_integer_contraction": True,
    "denominators_restored_exactly": True,
    "full_low_k_fixed_v6_branch_equality_in_pinned_tests": True,
}
CACHE_STATS = {"cached_factorial_ratios", "cached_delta_scale_tables"}


def load_canonical(path):
    return V6.load_canonical(path)


def nonnegative_integer(value, label):
    if type(value) is not int or value < 0:
        raise ValueError(f"{label} is not a nonnegative integer")
    return value


def normalized_v6(raw):
    """Remove only the proved v7 cache-wrapper wire differences."""
    normalized = copy.deepcopy(raw)
    normalized["format"] = (
        "D14-grid38-scaled-cutoff-cross-common-r-fixed-v6")
    normalized["status"] = (
        "EXACT FIXED-DENOMINATOR COMMON-r CROSS SHARD PASS")
    normalized["producer_sha256"] = V6.PRODUCER_SHA
    normalized["source_hashes"] = V6.SOURCE_HASHES
    normalized["algorithm"] = V6.ALGORITHM
    block = normalized["branch_values_and_fast_stats"]
    radial = block["integer_radialization"]["radial_stats"]
    for key in CACHE_STATS:
        del radial[key]
    timing = block["timing_seconds"]
    timing["radialize_fixed_denominator_integers"] = timing.pop(
        "radialize_cached_fixed_denominator_integers")
    return normalized


def audit(path, reference_path=None):
    raw, raw_bytes = load_canonical(path)
    if type(raw) is not dict or set(raw) != V6.TOP:
        raise ValueError("unexpected or incomplete v7 top-level schema")
    if (raw["format"] !=
            "D14-grid38-scaled-cutoff-cross-common-r-cached-v7"
            or raw["status"] !=
                "EXACT CACHED-FIXED COMMON-r CROSS SHARD PASS"
            or raw["rigorous"] is not True
            or raw["serialized_matrices_read"] is not False
            or raw["producer_sha256"] != PRODUCER_SHA):
        raise ValueError("v7 identity/status mismatch")
    if raw["algorithm"] != ALGORITHM:
        raise ValueError("v7 frozen algorithm mismatch")
    if raw["source_hashes"] != SOURCE_HASHES:
        raise ValueError("v7 serialized source closure mismatch")
    if sha256(REPO / PRODUCER) != PRODUCER_SHA:
        raise ValueError("live v7 producer hash mismatch")
    for relative, expected in SOURCE_HASHES.items():
        if sha256(REPO / relative) != expected:
            raise ValueError(f"live v7 source hash mismatch: {relative}")

    block = raw.get("branch_values_and_fast_stats")
    if type(block) is not dict:
        raise ValueError("v7 branch block is not an object")
    integer = block.get("integer_radialization")
    if type(integer) is not dict or type(integer.get("radial_stats")) is not dict:
        raise ValueError("v7 integer-radial block is malformed")
    radial = integer["radial_stats"]
    if set(radial) != V6.FIXED_RADIAL_STATS | CACHE_STATS:
        raise ValueError("v7 radial-stat schema mismatch")
    ratios = nonnegative_integer(
        radial["cached_factorial_ratios"], "cached factorial ratios")
    scales = nonnegative_integer(
        radial["cached_delta_scale_tables"], "cached delta tables")
    degree = radial["maximum_orbit_degree"]
    ceiling = radial["factorial_ceiling"]
    transforms = radial["orbit_transforms"]
    # The runner imports a fresh cache module and calls build exactly once.
    # Each delta table is keyed by an occurring total degree T in [0,E]; each
    # factorial ratio is keyed by x,y powers in [0,ceiling].
    if (type(degree) is not int or not 0 <= degree <= 64
            or type(ceiling) is not int or ceiling != degree + 46):
        raise ArithmeticError("v7 degree/factorial ceiling is invalid")
    if not 1 <= scales <= min(degree + 1, transforms):
        raise ArithmeticError("v7 delta-table cache inventory is impossible")
    if not 1 <= ratios <= (ceiling + 1) ** 2:
        raise ArithmeticError("v7 factorial-ratio cache inventory is impossible")
    timing = block.get("timing_seconds")
    if (type(timing) is not dict or
            set(timing) != {
                "clear_family_denominators",
                "radialize_cached_fixed_denominator_integers",
                "integrate_globally_collected_integers"}):
        raise ValueError("v7 nested timing schema mismatch")

    # V6.audit is an independent, pinned checker.  The normalized temporary
    # object differs from the input only in the identities above, the two
    # diagnostic counters, and the label of the radial timing component.
    normalized = normalized_v6(raw)
    payload = (json.dumps(normalized, sort_keys=True, separators=(",", ":"),
                          ensure_ascii=True, allow_nan=False) + "\n").encode("ascii")
    with tempfile.TemporaryDirectory(prefix="cached-v7-audit-") as directory:
        normalized_path = Path(directory) / "normalized-v6.json"
        normalized_path.write_bytes(payload)
        v6_result = V6.audit(normalized_path)

    reference_sha = None
    reference_equal = None
    if reference_path is not None:
        reference_result = V6.audit(reference_path)
        reference, reference_bytes = load_canonical(reference_path)
        if reference["common_r"] != raw["common_r"]:
            raise ValueError("v7/v6 reference count mismatch")
        for key in {"scaled_b_shard", "kernel_stats", "family_stats",
                    "geometry", "candidate", "scaling"}:
            if raw[key] != reference[key]:
                raise ArithmeticError(
                    f"v7/v6 mathematical field differs bit-for-bit: {key}")
        new_block = raw["branch_values_and_fast_stats"]
        old_block = reference["branch_values_and_fast_stats"]
        for key in {"high", "low", "high_stats", "low_stats"}:
            if new_block[key] != old_block[key]:
                raise ArithmeticError(
                    f"v7/v6 branch field differs bit-for-bit: {key}")
        new_integer = copy.deepcopy(new_block["integer_radialization"])
        for key in CACHE_STATS:
            del new_integer["radial_stats"][key]
        if new_integer != old_block["integer_radialization"]:
            raise ArithmeticError(
                "v7/v6 fixed-radial exact metadata differs bit-for-bit")
        if reference_result["scaled_b_shard"] != v6_result["scaled_b_shard"]:
            raise ArithmeticError("v7/v6 independently parsed values differ")
        reference_sha = sha256(reference_bytes)
        reference_equal = True

    return {
        "status": "CACHED-V7 CROSS SHARD STRUCTURAL/RESULT AUDIT PASS",
        "input_sha256": sha256(raw_bytes),
        "common_r": v6_result["common_r"],
        "scaled_b_shard": v6_result["scaled_b_shard"],
        "recombined_exactly": v6_result["recombined_exactly"],
        "maximum_active_shift": v6_result["maximum_active_shift"],
        "active_branch_families": v6_result["active_branch_families"],
        "inactive_families_pruned_before_radialization":
            v6_result["inactive_families_pruned_before_radialization"],
        "maximum_orbit_degree": degree,
        "factorial_ceiling": ceiling,
        "fixed_denominator_relation_verified":
            v6_result["fixed_denominator_relation_verified"],
        "cache_inventory_semantics_verified": True,
        "cached_factorial_ratios": ratios,
        "cached_delta_scale_tables": scales,
        "source_closure_verified": True,
        "reference_mathematical_fields_bit_equal": reference_equal,
        "reference_sha256": reference_sha,
        "total_scalar_products": v6_result["total_scalar_products"],
        "total_surviving_product_monomials":
            v6_result["total_surviving_product_monomials"],
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
        raise RuntimeError("externally pinned v7 checker SHA mismatch")
    result = audit(args.shard, args.reference)
    payload = (json.dumps(result, sort_keys=True, separators=(",", ":"),
                          ensure_ascii=True, allow_nan=False) + "\n").encode("ascii")
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
