#!/usr/bin/env python3
"""Fail-closed structural/result checker for fixed-polygon-v8 shards.

After validating the sole v8 wire change and its pinned integer-moment
implementation, normalize the record to cached-v7 and invoke that independent
checker.  An optional same-r cached-v7 record is audited separately and
compared in every exact mathematical/work field.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile


FILE = Path(__file__).resolve()
REPO = FILE.parents[2]
V7_CHECKER_PATH = FILE.with_name("verify_cached_v7_cross_shard.py")
V7_CHECKER_SHA = \
    "80ec3329215f66e784708039f9a1d673d7064769c48a31825961dc44f6ae7343"
PRODUCER = (
    "agents/exact-projection-engine/"
    "d14_grid38_scaled_b_shard_fixed_polygon_v8.py")
PRODUCER_SHA = \
    "36a8e027c83cabb272aa28a5d542dc571793cbcf90c5ca48787bc20092a55b72"
V7_RUNNER = (
    "agents/exact-projection-engine/"
    "d14_grid38_scaled_b_shard_cached_v7.py")
MOMENT_SOURCE = "agents/exact-projection-engine/fixed_polygon_moments.py"
MOMENT_TEST = "agents/exact-projection-engine/test_fixed_polygon_moments.py"


def sha256(value):
    if isinstance(value, (str, Path)):
        value = Path(value).read_bytes()
    return hashlib.sha256(value).hexdigest()


if sha256(V7_CHECKER_PATH) != V7_CHECKER_SHA:
    raise RuntimeError("pinned cached-v7 result checker changed")
_spec = importlib.util.spec_from_file_location(
    "fixed_polygon_v8_pinned_v7_auditor", V7_CHECKER_PATH)
if _spec is None or _spec.loader is None:
    raise ImportError(V7_CHECKER_PATH)
V7 = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = V7
_spec.loader.exec_module(V7)


SOURCE_HASHES = dict(V7.SOURCE_HASHES)
SOURCE_HASHES.update({
    V7_RUNNER:
        "b427c6961c377cb79d5a72b54f8c2e8c7642b87d66d338f53b5dc56d98991984",
    MOMENT_SOURCE:
        "4100a9eeb86563ae84bf02ed4df9a2a5b696b5cc9ff163d15ac482b242b637bb",
    MOMENT_TEST:
        "165bacf0b02778e35151327112832898f6c40870ac68d8de3d349ac52e6ffd36",
})
ALGORITHM = {
    "direct_fixed_denominator_partition_radial_integers": True,
    "fixed_denominator_globally_gcd_reduced": True,
    "factorial_ratios_cached_outside_partition_inner_loops": True,
    "rational_cap_powers_cached_outside_partition_inner_loops": True,
    "coefficient_denominator_and_packed_maps_equal_fixed_v6_in_tests": True,
    "polygon_moments_accumulated_under_one_batch_denominator": True,
    "polygon_fraction_normalization_only_after_triangle_accumulation": True,
    "polygon_batch_equal_reference_in_pinned_tests": True,
    "polygon_runtime_module_patched_after_pinned_load": True,
    "inactive_branch_families_pruned_before_radialization": True,
    "complete_affine_radial_product_collected_by_final_monomial": True,
    "moment_common_denominator_integer_contraction": True,
    "denominators_restored_exactly": True,
    "full_low_k_fixed_v6_branch_equality_in_pinned_tests": True,
}


def normalized_v7(raw):
    normalized = copy.deepcopy(raw)
    normalized["format"] = (
        "D14-grid38-scaled-cutoff-cross-common-r-cached-v7")
    normalized["status"] = "EXACT CACHED-FIXED COMMON-r CROSS SHARD PASS"
    normalized["producer_sha256"] = V7.PRODUCER_SHA
    normalized["source_hashes"] = V7.SOURCE_HASHES
    normalized["algorithm"] = V7.ALGORITHM
    return normalized


def audit(path, reference_path=None):
    raw, raw_bytes = V7.load_canonical(path)
    if type(raw) is not dict or set(raw) != V7.V6.TOP:
        raise ValueError("unexpected or incomplete fixed-polygon-v8 schema")
    if (raw["format"] !=
            "D14-grid38-scaled-cutoff-cross-common-r-fixed-polygon-v8" or
            raw["status"] !=
                "EXACT FIXED-POLYGON COMMON-r CROSS SHARD PASS" or
            raw["rigorous"] is not True or
            raw["serialized_matrices_read"] is not False or
            raw["producer_sha256"] != PRODUCER_SHA or
            raw["algorithm"] != ALGORITHM or
            raw["source_hashes"] != SOURCE_HASHES):
        raise ValueError("fixed-polygon-v8 identity/source contract mismatch")
    if sha256(REPO / PRODUCER) != PRODUCER_SHA:
        raise ValueError("live fixed-polygon-v8 producer hash mismatch")
    for relative, expected in SOURCE_HASHES.items():
        if sha256(REPO / relative) != expected:
            raise ValueError(f"live v8 source hash mismatch: {relative}")

    normalized = normalized_v7(raw)
    payload = (json.dumps(normalized, sort_keys=True, separators=(",", ":"),
                          ensure_ascii=True, allow_nan=False) + "\n").encode("ascii")
    with tempfile.TemporaryDirectory(prefix="fixed-polygon-v8-audit-") as root:
        normalized_path = Path(root) / "normalized-v7.json"
        normalized_path.write_bytes(payload)
        v7_result = V7.audit(normalized_path)

    reference_sha = None
    reference_equal = None
    if reference_path is not None:
        reference_result = V7.audit(reference_path)
        reference, reference_bytes = V7.load_canonical(reference_path)
        if reference["common_r"] != raw["common_r"]:
            raise ValueError("v8/v7 reference count mismatch")
        for key in {
                "scaled_b_shard", "kernel_stats", "family_stats",
                "geometry", "candidate", "scaling"}:
            if raw[key] != reference[key]:
                raise ArithmeticError(
                    f"v8/v7 exact field differs bit-for-bit: {key}")
        new_block = raw["branch_values_and_fast_stats"]
        old_block = reference["branch_values_and_fast_stats"]
        for key in {"high", "low", "high_stats", "low_stats",
                    "integer_radialization"}:
            if new_block[key] != old_block[key]:
                raise ArithmeticError(
                    f"v8/v7 exact branch field differs bit-for-bit: {key}")
        if reference_result["scaled_b_shard"] != v7_result["scaled_b_shard"]:
            raise ArithmeticError("v8/v7 independently parsed values differ")
        reference_sha = sha256(reference_bytes)
        reference_equal = True

    return {
        "status": "FIXED-POLYGON-V8 CROSS SHARD STRUCTURAL/RESULT AUDIT PASS",
        "input_sha256": sha256(raw_bytes),
        "common_r": v7_result["common_r"],
        "scaled_b_shard": v7_result["scaled_b_shard"],
        "recombined_exactly": v7_result["recombined_exactly"],
        "maximum_active_shift": v7_result["maximum_active_shift"],
        "active_branch_families": v7_result["active_branch_families"],
        "fixed_denominator_relation_verified":
            v7_result["fixed_denominator_relation_verified"],
        "cache_inventory_semantics_verified":
            v7_result["cache_inventory_semantics_verified"],
        "fixed_polygon_denominator_proof_pinned": True,
        "source_closure_verified": True,
        "reference_exact_fields_bit_equal": reference_equal,
        "reference_sha256": reference_sha,
        "total_scalar_products": v7_result["total_scalar_products"],
        "total_surviving_product_monomials":
            v7_result["total_surviving_product_monomials"],
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--expected-self-sha256")
    parser.add_argument("--reference", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("shard", type=Path)
    args = parser.parse_args()
    if (args.expected_self_sha256 is not None and
            sha256(FILE) != args.expected_self_sha256):
        raise RuntimeError("externally pinned v8 checker SHA mismatch")
    result = audit(args.shard, args.reference)
    payload = (json.dumps(result, sort_keys=True, separators=(",", ":"),
                          ensure_ascii=True, allow_nan=False) + "\n").encode("ascii")
    if args.output is None:
        sys.stdout.buffer.write(payload)
    else:
        path = args.output.resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o444)
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())


if __name__ == "__main__":
    main()
