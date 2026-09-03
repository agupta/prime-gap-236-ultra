#!/usr/bin/env python3
"""Exact D14-grid38 shard with cached direct integer radial costs.

This v7 wrapper is algebraically the audited fixed-v6 transform.  It only
hoists repeated factorial ratios and rational-cap powers out of the inner
partition-split loops.  All coefficients, denominators, branch values, and
publication semantics remain exact.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import resource
import sys


if hasattr(sys, "set_int_max_str_digits"):
    sys.set_int_max_str_digits(0)

FILE = Path(__file__).resolve()
REPO = FILE.parents[2]
V6_RUNNER_PATH = FILE.with_name("d14_grid38_scaled_b_shard_fixed_v6.py")
CACHED_PATH = FILE.with_name("cached_fixed_denominator_radial.py")
CACHED_TEST_PATH = FILE.with_name("test_cached_fixed_denominator_radial.py")
LOCAL_PINNED = {
    V6_RUNNER_PATH:
        "89c7c57aa439b0535bd17b85683dd1fd4ece2d1439e1b5d8bd9562c44eb57e17",
    CACHED_PATH:
        "79c9a8ef26de0b7fba55fbdb6e113a88f0b52b20f9cbcb34cbc2dbb507ba74c4",
    CACHED_TEST_PATH:
        "0f0bd15426ff961e47281b32d57795f1848e75280fd645abc599df8d1410fd5b",
}


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def load(name, path, data):
    if path.read_bytes() != data:
        raise RuntimeError(f"source changed before import: {path}")
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def canonical_json(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"),
                       ensure_ascii=True, allow_nan=False) + "\n").encode("ascii")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--common-r", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--expected-self-sha256", required=True)
    args = parser.parse_args()
    self_data = FILE.read_bytes()
    if sha256_bytes(self_data) != args.expected_self_sha256:
        raise RuntimeError("externally pinned cached-v7 runner SHA mismatch")
    if not 0 <= args.common_r <= 12:
        raise ValueError("the frozen support has common r=0..12")
    if args.output.exists():
        raise FileExistsError(f"refusing to overwrite {args.output}")

    local_snapshots = {path: path.read_bytes() for path in LOCAL_PINNED}
    for path, digest in LOCAL_PINNED.items():
        if sha256_bytes(local_snapshots[path]) != digest:
            raise RuntimeError(f"local pinned source changed: {path}")
    v6_runner = load("d14_grid38_cached_v7_v6_runner", V6_RUNNER_PATH,
                     local_snapshots[V6_RUNNER_PATH])
    v6_snapshots = {
        path: path.read_bytes() for path in v6_runner.LOCAL_PINNED}
    for path, digest in v6_runner.LOCAL_PINNED.items():
        if sha256_bytes(v6_snapshots[path]) != digest:
            raise RuntimeError(f"v6 pinned source changed: {path}")
    v5_runner = load(
        "d14_grid38_cached_v7_v5_runner", v6_runner.V5_RUNNER_PATH,
        v6_snapshots[v6_runner.V5_RUNNER_PATH])
    v5_snapshots = {
        path: path.read_bytes() for path in v5_runner.LOCAL_PINNED}
    for path, digest in v5_runner.LOCAL_PINNED.items():
        if sha256_bytes(v5_snapshots[path]) != digest:
            raise RuntimeError(f"v5 pinned source changed: {path}")
    v2 = load("d14_grid38_cached_v7_v2", v5_runner.V2_PATH,
              v5_snapshots[v5_runner.V2_PATH])
    v2_snapshots = {path: path.read_bytes() for path in v2.LOCAL_PINNED}
    for path, digest in v2.LOCAL_PINNED.items():
        if sha256_bytes(v2_snapshots[path]) != digest:
            raise RuntimeError(f"v2 pinned source changed: {path}")
    base = load("d14_grid38_cached_v7_base", v2.BASE_PATH,
                v2_snapshots[v2.BASE_PATH])
    fast_v2 = load("d14_grid38_cached_v7_fast_v2", v2.FAST_PATH,
                   v2_snapshots[v2.FAST_PATH])
    pruned_v3 = load("d14_grid38_cached_v7_pruned_v3", v5_runner.V3_PATH,
                     v5_snapshots[v5_runner.V3_PATH])
    collected_v5 = load(
        "d14_grid38_cached_v7_collected_v5", v5_runner.V5_PATH,
        v5_snapshots[v5_runner.V5_PATH])
    fixed_v6 = load("d14_grid38_cached_v7_fixed_v6", v6_runner.FIXED_PATH,
                    v6_snapshots[v6_runner.FIXED_PATH])
    cached_v7 = load("d14_grid38_cached_v7_algorithm", CACHED_PATH,
                     local_snapshots[CACHED_PATH])
    publish_source = load(
        "d14_grid38_cached_v7_publish", v5_runner.PUBLISH_SOURCE_PATH,
        v5_snapshots[v5_runner.PUBLISH_SOURCE_PATH])
    pruned_v3.FAST_V2 = fast_v2
    collected_v5.FAST_V2 = fast_v2
    collected_v5.PRUNED_V3 = pruned_v3
    fixed_v6.FAST_V2 = fast_v2
    fixed_v6.COLLECTED_V5 = collected_v5
    cached_v7.FIXED_V6 = fixed_v6
    cached_v7.FAST_V2 = fast_v2
    cached_v7.COLLECTED_V5 = collected_v5
    dependency_snapshots = {path: path.read_bytes() for path in base.PINNED}
    for path, digest in base.PINNED.items():
        if sha256_bytes(dependency_snapshots[path]) != digest:
            raise RuntimeError(f"inherited pinned source changed: {path}")

    result = v2.build(
        args.common_r, v2_snapshots, dependency_snapshots, base, cached_v7)
    result["format"] = (
        "D14-grid38-scaled-cutoff-cross-common-r-cached-v7")
    result["status"] = "EXACT CACHED-FIXED COMMON-r CROSS SHARD PASS"
    result["algorithm"] = {
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
    result["source_hashes"].update({
        str(path.relative_to(REPO)): digest
        for path, digest in {
            **v6_runner.LOCAL_PINNED, **v5_runner.LOCAL_PINNED,
            **LOCAL_PINNED}.items()})
    result["peak_rss_kib"] = resource.getrusage(
        resource.RUSAGE_SELF).ru_maxrss

    if (FILE.read_bytes() != self_data or
            any(path.read_bytes() != data
                for path, data in local_snapshots.items()) or
            any(path.read_bytes() != data
                for path, data in v6_snapshots.items()) or
            any(path.read_bytes() != data
                for path, data in v5_snapshots.items()) or
            any(path.read_bytes() != data
                for path, data in v2_snapshots.items()) or
            any(path.read_bytes() != data
                for path, data in dependency_snapshots.items())):
        raise RuntimeError("cached-v7 source closure changed during computation")
    result["producer_sha256"] = args.expected_self_sha256
    payload = canonical_json(result)
    publish_source.publish_exclusive(args.output, payload)
    print(sha256_bytes(payload), args.output)


if __name__ == "__main__":
    main()
