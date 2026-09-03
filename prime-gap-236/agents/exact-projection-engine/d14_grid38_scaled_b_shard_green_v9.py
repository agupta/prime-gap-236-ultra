#!/usr/bin/env python3
"""Exact D14 mixed shard with Green-theorem polygon moments.

This v9 runner keeps the recursively pinned cached-v7 transform and replaces
only the exact convex-polygon moment batch.  The replacement expands each
boundary edge as a one-variable polynomial and accumulates integers over the
proved denominator ``L^(E+2)*((E+2)!)^2``.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import resource
import sys


if hasattr(sys, "set_int_max_str_digits"):
    sys.set_int_max_str_digits(0)

FILE = Path(__file__).resolve()
REPO = FILE.parents[2]
V7_RUNNER_PATH = FILE.with_name("d14_grid38_scaled_b_shard_cached_v7.py")
GREEN_PATH = FILE.with_name("green_polygon_moments.py")
GREEN_TEST_PATH = FILE.with_name("test_green_polygon_moments.py")
GREEN_BENCHMARK_PATH = FILE.with_name("benchmark_green_polygon_target.py")
LOCAL_PINNED = {
    V7_RUNNER_PATH:
        "b427c6961c377cb79d5a72b54f8c2e8c7642b87d66d338f53b5dc56d98991984",
    GREEN_PATH:
        "019fecc00727bfdeb62fc3a02277298c6d08543db4d71ce47f049a73bc1d7a0c",
    GREEN_TEST_PATH:
        "05684adf3d1bfef537718819372525e97dd72cfc24b88e0a697a269a44cd9bfe",
    GREEN_BENCHMARK_PATH:
        "480f8c2e4bc67d270a4739df2bc2c048203c27fdc0b580dca140f0a09bc14217",
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
        raise RuntimeError("externally pinned Green-v9 runner SHA mismatch")
    if not 0 <= args.common_r <= 12:
        raise ValueError("the frozen support has common r=0..12")
    if args.output.exists():
        raise FileExistsError(f"refusing to overwrite {args.output}")

    local_snapshots = {path: path.read_bytes() for path in LOCAL_PINNED}
    for path, digest in LOCAL_PINNED.items():
        if sha256_bytes(local_snapshots[path]) != digest:
            raise RuntimeError(f"local pinned source changed: {path}")
    v7_reference = load(
        "d14_grid38_green_v9_v7_reference", V7_RUNNER_PATH,
        local_snapshots[V7_RUNNER_PATH])
    v7_snapshots = {
        path: path.read_bytes() for path in v7_reference.LOCAL_PINNED}
    for path, digest in v7_reference.LOCAL_PINNED.items():
        if sha256_bytes(v7_snapshots[path]) != digest:
            raise RuntimeError(f"v7 pinned source changed: {path}")
    v6_runner = load(
        "d14_grid38_green_v9_v6_runner", v7_reference.V6_RUNNER_PATH,
        v7_snapshots[v7_reference.V6_RUNNER_PATH])
    v6_snapshots = {
        path: path.read_bytes() for path in v6_runner.LOCAL_PINNED}
    for path, digest in v6_runner.LOCAL_PINNED.items():
        if sha256_bytes(v6_snapshots[path]) != digest:
            raise RuntimeError(f"v6 pinned source changed: {path}")
    v5_runner = load(
        "d14_grid38_green_v9_v5_runner", v6_runner.V5_RUNNER_PATH,
        v6_snapshots[v6_runner.V5_RUNNER_PATH])
    v5_snapshots = {
        path: path.read_bytes() for path in v5_runner.LOCAL_PINNED}
    for path, digest in v5_runner.LOCAL_PINNED.items():
        if sha256_bytes(v5_snapshots[path]) != digest:
            raise RuntimeError(f"v5 pinned source changed: {path}")
    v2 = load("d14_grid38_green_v9_v2", v5_runner.V2_PATH,
              v5_snapshots[v5_runner.V2_PATH])
    v2_snapshots = {path: path.read_bytes() for path in v2.LOCAL_PINNED}
    for path, digest in v2.LOCAL_PINNED.items():
        if sha256_bytes(v2_snapshots[path]) != digest:
            raise RuntimeError(f"v2 pinned source changed: {path}")
    base = load("d14_grid38_green_v9_base", v2.BASE_PATH,
                v2_snapshots[v2.BASE_PATH])
    fast_v2 = load("d14_grid38_green_v9_fast_v2", v2.FAST_PATH,
                   v2_snapshots[v2.FAST_PATH])
    pruned_v3 = load(
        "d14_grid38_green_v9_pruned_v3", v5_runner.V3_PATH,
        v5_snapshots[v5_runner.V3_PATH])
    collected_v5 = load(
        "d14_grid38_green_v9_collected_v5", v5_runner.V5_PATH,
        v5_snapshots[v5_runner.V5_PATH])
    fixed_v6 = load(
        "d14_grid38_green_v9_fixed_v6", v6_runner.FIXED_PATH,
        v6_snapshots[v6_runner.FIXED_PATH])
    cached_v7 = load(
        "d14_grid38_green_v9_cached_v7", v7_reference.CACHED_PATH,
        v7_snapshots[v7_reference.CACHED_PATH])
    green = load(
        "d14_grid38_green_v9_moments", GREEN_PATH,
        local_snapshots[GREEN_PATH])
    publish_source = load(
        "d14_grid38_green_v9_publish", v5_runner.PUBLISH_SOURCE_PATH,
        v5_snapshots[v5_runner.PUBLISH_SOURCE_PATH])

    pruned_v3.FAST_V2 = fast_v2
    collected_v5.FAST_V2 = fast_v2
    collected_v5.PRUNED_V3 = pruned_v3
    fixed_v6.FAST_V2 = fast_v2
    fixed_v6.COLLECTED_V5 = collected_v5
    cached_v7.FIXED_V6 = fixed_v6
    cached_v7.FAST_V2 = fast_v2
    cached_v7.COLLECTED_V5 = collected_v5

    original_import_snapshot = base.import_snapshot

    def import_snapshot_with_green_polygon(name, path, data):
        module = original_import_snapshot(name, path, data)
        if path == base.RADIAL:
            module._polygon_monomial_batch = \
                green.polygon_monomial_batch_green
        return module

    base.import_snapshot = import_snapshot_with_green_polygon

    dependency_snapshots = {path: path.read_bytes() for path in base.PINNED}
    for path, digest in base.PINNED.items():
        if sha256_bytes(dependency_snapshots[path]) != digest:
            raise RuntimeError(f"inherited pinned source changed: {path}")

    result = v2.build(
        args.common_r, v2_snapshots, dependency_snapshots, base, cached_v7)
    result["format"] = "D14-grid38-scaled-cutoff-cross-common-r-green-v9"
    result["status"] = "EXACT GREEN-POLYGON COMMON-r CROSS SHARD PASS"
    result["algorithm"] = {
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
    result["source_hashes"].update({
        str(path.relative_to(REPO)): digest
        for path, digest in {
            **v6_runner.LOCAL_PINNED, **v5_runner.LOCAL_PINNED,
            **v7_reference.LOCAL_PINNED, **LOCAL_PINNED}.items()})
    result["peak_rss_kib"] = resource.getrusage(
        resource.RUSAGE_SELF).ru_maxrss

    if (FILE.read_bytes() != self_data or
            any(path.read_bytes() != data
                for path, data in local_snapshots.items()) or
            any(path.read_bytes() != data
                for path, data in v7_snapshots.items()) or
            any(path.read_bytes() != data
                for path, data in v6_snapshots.items()) or
            any(path.read_bytes() != data
                for path, data in v5_snapshots.items()) or
            any(path.read_bytes() != data
                for path, data in v2_snapshots.items()) or
            any(path.read_bytes() != data
                for path, data in dependency_snapshots.items())):
        raise RuntimeError("Green-v9 source closure changed")
    result["producer_sha256"] = args.expected_self_sha256
    payload = canonical_json(result)
    publish_source.publish_exclusive(args.output, payload)
    print(sha256_bytes(payload), args.output)


if __name__ == "__main__":
    main()
