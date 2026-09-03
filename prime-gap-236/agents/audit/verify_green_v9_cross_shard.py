#!/usr/bin/env python3
"""Fail-closed structural/result checker for Green-polygon-v9 shards."""

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
V8_CHECKER_PATH = FILE.with_name("verify_fixed_polygon_v8_cross_shard.py")
V8_CHECKER_SHA = \
    "ec0162a73381d031e4ab7b5d8cb1fa16381e41f19c74a6fd74aafa0c30a8655c"
PRODUCER = (
    "agents/exact-projection-engine/"
    "d14_grid38_scaled_b_shard_green_v9.py")
PRODUCER_SHA = \
    "ad38951dadecdb5a5c51d1221b0a078bc9f804e9c4ec8d434706fca55a11935a"
V7_RUNNER = (
    "agents/exact-projection-engine/"
    "d14_grid38_scaled_b_shard_cached_v7.py")
GREEN_SOURCE = "agents/exact-projection-engine/green_polygon_moments.py"
GREEN_TEST = "agents/exact-projection-engine/test_green_polygon_moments.py"
GREEN_BENCHMARK = (
    "agents/exact-projection-engine/benchmark_green_polygon_target.py")


def sha256(value):
    data = Path(value).read_bytes() if isinstance(value, (str, Path)) else value
    return hashlib.sha256(data).hexdigest()


if sha256(V8_CHECKER_PATH) != V8_CHECKER_SHA:
    raise RuntimeError("pinned fixed-polygon-v8 checker changed")
_spec = importlib.util.spec_from_file_location(
    "green_v9_pinned_v8_auditor", V8_CHECKER_PATH)
if _spec is None or _spec.loader is None:
    raise ImportError(V8_CHECKER_PATH)
V8 = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = V8
_spec.loader.exec_module(V8)


SOURCE_HASHES = dict(V8.V7.SOURCE_HASHES)
SOURCE_HASHES.update({
    V7_RUNNER:
        "b427c6961c377cb79d5a72b54f8c2e8c7642b87d66d338f53b5dc56d98991984",
    GREEN_SOURCE:
        "019fecc00727bfdeb62fc3a02277298c6d08543db4d71ce47f049a73bc1d7a0c",
    GREEN_TEST:
        "05684adf3d1bfef537718819372525e97dd72cfc24b88e0a697a269a44cd9bfe",
    GREEN_BENCHMARK:
        "480f8c2e4bc67d270a4739df2bc2c048203c27fdc0b580dca140f0a09bc14217",
})
ALGORITHM = {
    "direct_fixed_denominator_partition_radial_integers": True,
    "fixed_denominator_globally_gcd_reduced": True,
    "factorial_ratios_cached_outside_partition_inner_loops": True,
    "rational_cap_powers_cached_outside_partition_inner_loops": True,
    "coefficient_denominator_and_packed_maps_equal_fixed_v6_in_tests": True,
    "polygon_moments_accumulated_by_green_boundary": True,
    "polygon_common_denominator_L_Eplus2_factorial_squared": True,
    "polygon_fraction_normalization_only_after_edge_accumulation": True,
    "polygon_convex_cyclic_order_checked": True,
    "polygon_runtime_module_patched_after_pinned_load": True,
    "inactive_branch_families_pruned_before_radialization": True,
    "complete_affine_radial_product_collected_by_final_monomial": True,
    "moment_common_denominator_integer_contraction": True,
    "denominators_restored_exactly": True,
    "full_low_k_fixed_v6_branch_equality_in_pinned_tests": True,
}


def normalized_v8(raw):
    normalized = copy.deepcopy(raw)
    normalized["format"] = (
        "D14-grid38-scaled-cutoff-cross-common-r-fixed-polygon-v8")
    normalized["status"] = "EXACT FIXED-POLYGON COMMON-r CROSS SHARD PASS"
    normalized["producer_sha256"] = V8.PRODUCER_SHA
    normalized["source_hashes"] = V8.SOURCE_HASHES
    normalized["algorithm"] = V8.ALGORITHM
    return normalized


def audit(path, reference_path=None):
    raw, raw_bytes = V8.V7.load_canonical(path)
    if type(raw) is not dict or set(raw) != V8.V7.V6.TOP:
        raise ValueError("unexpected or incomplete Green-v9 schema")
    if (raw["format"] !=
            "D14-grid38-scaled-cutoff-cross-common-r-green-v9" or
            raw["status"] !=
                "EXACT GREEN-POLYGON COMMON-r CROSS SHARD PASS" or
            raw["rigorous"] is not True or
            raw["serialized_matrices_read"] is not False or
            raw["producer_sha256"] != PRODUCER_SHA or
            raw["algorithm"] != ALGORITHM or
            raw["source_hashes"] != SOURCE_HASHES):
        raise ValueError("Green-v9 identity/source contract mismatch")
    if sha256(REPO / PRODUCER) != PRODUCER_SHA:
        raise ValueError("live Green-v9 producer hash mismatch")
    for relative, expected in SOURCE_HASHES.items():
        if sha256(REPO / relative) != expected:
            raise ValueError(f"live Green-v9 source hash mismatch: {relative}")

    normalized = normalized_v8(raw)
    payload = (json.dumps(
        normalized, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
        allow_nan=False) + "\n").encode("ascii")
    with tempfile.TemporaryDirectory(prefix="green-v9-audit-") as root:
        normalized_path = Path(root) / "normalized-v8.json"
        normalized_path.write_bytes(payload)
        v8_result = V8.audit(normalized_path)

    reference_sha = None
    reference_equal = None
    if reference_path is not None:
        reference_result = V8.audit(reference_path)
        reference, reference_bytes = V8.V7.load_canonical(reference_path)
        if reference["common_r"] != raw["common_r"]:
            raise ValueError("Green-v9/v8 reference count mismatch")
        for key in {
                "scaled_b_shard", "kernel_stats", "family_stats",
                "geometry", "candidate", "scaling"}:
            if raw[key] != reference[key]:
                raise ArithmeticError(
                    f"Green-v9/v8 exact field differs: {key}")
        for key in {"high", "low", "high_stats", "low_stats",
                    "integer_radialization"}:
            if (raw["branch_values_and_fast_stats"][key] !=
                    reference["branch_values_and_fast_stats"][key]):
                raise ArithmeticError(
                    f"Green-v9/v8 exact branch field differs: {key}")
        if reference_result["scaled_b_shard"] != v8_result["scaled_b_shard"]:
            raise ArithmeticError("independently parsed v9/v8 values differ")
        reference_sha = sha256(reference_bytes)
        reference_equal = True

    return {
        "status": "GREEN-V9 CROSS SHARD STRUCTURAL/RESULT AUDIT PASS",
        "input_sha256": sha256(raw_bytes),
        "common_r": v8_result["common_r"],
        "scaled_b_shard": v8_result["scaled_b_shard"],
        "recombined_exactly": v8_result["recombined_exactly"],
        "maximum_active_shift": v8_result["maximum_active_shift"],
        "active_branch_families": v8_result["active_branch_families"],
        "fixed_denominator_relation_verified":
            v8_result["fixed_denominator_relation_verified"],
        "cache_inventory_semantics_verified":
            v8_result["cache_inventory_semantics_verified"],
        "green_boundary_denominator_proof_pinned": True,
        "convexity_fail_closed": True,
        "source_closure_verified": True,
        "reference_exact_fields_bit_equal": reference_equal,
        "reference_sha256": reference_sha,
        "total_scalar_products": v8_result["total_scalar_products"],
        "total_surviving_product_monomials":
            v8_result["total_surviving_product_monomials"],
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
        raise RuntimeError("externally pinned Green-v9 checker SHA mismatch")
    result = audit(args.shard, args.reference)
    payload = (json.dumps(
        result, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
        allow_nan=False) + "\n").encode("ascii")
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
