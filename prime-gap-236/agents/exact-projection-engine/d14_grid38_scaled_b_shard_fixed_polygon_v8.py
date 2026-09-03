#!/usr/bin/env python3
"""Exact D14 mixed shard with fixed-denominator polygon moments.

This v8 runner keeps the audited cached-v7 radial transform and replaces
only the exact polygon-moment batch.  Rational vertices are scaled to one
integer grid and every requested moment is accumulated under the proved
common denominator L^(E+2)(E+2)!, avoiding Fraction gcd work inside the
triangle expansion.
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
V7_RUNNER_PATH = FILE.with_name("d14_grid38_scaled_b_shard_cached_v7.py")
MOMENT_PATH = FILE.with_name("fixed_polygon_moments.py")
MOMENT_TEST_PATH = FILE.with_name("test_fixed_polygon_moments.py")
LOCAL_PINNED = {
    V7_RUNNER_PATH:
        "b427c6961c377cb79d5a72b54f8c2e8c7642b87d66d338f53b5dc56d98991984",
    MOMENT_PATH:
        "4100a9eeb86563ae84bf02ed4df9a2a5b696b5cc9ff163d15ac482b242b637bb",
    MOMENT_TEST_PATH:
        "165bacf0b02778e35151327112832898f6c40870ac68d8de3d349ac52e6ffd36",
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
        raise RuntimeError("externally pinned fixed-polygon-v8 runner SHA mismatch")
    if not 0 <= args.common_r <= 12:
        raise ValueError("the frozen support has common r=0..12")
    if args.output.exists():
        raise FileExistsError(f"refusing to overwrite {args.output}")

    local_snapshots = {path: path.read_bytes() for path in LOCAL_PINNED}
    for path, digest in LOCAL_PINNED.items():
        if sha256_bytes(local_snapshots[path]) != digest:
            raise RuntimeError(f"local pinned source changed: {path}")
    v7_reference = load(
        "d14_grid38_fixed_polygon_v8_v7_reference", V7_RUNNER_PATH,
        local_snapshots[V7_RUNNER_PATH])
    v7_snapshots = {
        path: path.read_bytes() for path in v7_reference.LOCAL_PINNED}
    for path, digest in v7_reference.LOCAL_PINNED.items():
        if sha256_bytes(v7_snapshots[path]) != digest:
            raise RuntimeError(f"v7 pinned source changed: {path}")
    v6_runner = load(
        "d14_grid38_fixed_polygon_v8_v6_runner",
        v7_reference.V6_RUNNER_PATH,
        v7_snapshots[v7_reference.V6_RUNNER_PATH])
    v6_snapshots = {
        path: path.read_bytes() for path in v6_runner.LOCAL_PINNED}
    for path, digest in v6_runner.LOCAL_PINNED.items():
        if sha256_bytes(v6_snapshots[path]) != digest:
            raise RuntimeError(f"v6 pinned source changed: {path}")
    v5_runner = load(
        "d14_grid38_fixed_polygon_v8_v5_runner", v6_runner.V5_RUNNER_PATH,
        v6_snapshots[v6_runner.V5_RUNNER_PATH])
    v5_snapshots = {
        path: path.read_bytes() for path in v5_runner.LOCAL_PINNED}
    for path, digest in v5_runner.LOCAL_PINNED.items():
        if sha256_bytes(v5_snapshots[path]) != digest:
            raise RuntimeError(f"v5 pinned source changed: {path}")
    v2 = load("d14_grid38_fixed_polygon_v8_v2", v5_runner.V2_PATH,
              v5_snapshots[v5_runner.V2_PATH])
    v2_snapshots = {path: path.read_bytes() for path in v2.LOCAL_PINNED}
    for path, digest in v2.LOCAL_PINNED.items():
        if sha256_bytes(v2_snapshots[path]) != digest:
            raise RuntimeError(f"v2 pinned source changed: {path}")
    base = load("d14_grid38_fixed_polygon_v8_base", v2.BASE_PATH,
                v2_snapshots[v2.BASE_PATH])
    fast_v2 = load("d14_grid38_fixed_polygon_v8_fast_v2", v2.FAST_PATH,
                   v2_snapshots[v2.FAST_PATH])
    pruned_v3 = load(
        "d14_grid38_fixed_polygon_v8_pruned_v3", v5_runner.V3_PATH,
        v5_snapshots[v5_runner.V3_PATH])
    collected_v5 = load(
        "d14_grid38_fixed_polygon_v8_collected_v5", v5_runner.V5_PATH,
        v5_snapshots[v5_runner.V5_PATH])
    fixed_v6 = load(
        "d14_grid38_fixed_polygon_v8_fixed_v6", v6_runner.FIXED_PATH,
        v6_snapshots[v6_runner.FIXED_PATH])
    cached_v7 = load(
        "d14_grid38_fixed_polygon_v8_cached_v7", v7_reference.CACHED_PATH,
        v7_snapshots[v7_reference.CACHED_PATH])
    fixed_moments = load(
        "d14_grid38_fixed_polygon_v8_moments", MOMENT_PATH,
        local_snapshots[MOMENT_PATH])
    publish_source = load(
        "d14_grid38_fixed_polygon_v8_publish",
        v5_runner.PUBLISH_SOURCE_PATH,
        v5_snapshots[v5_runner.PUBLISH_SOURCE_PATH])

    pruned_v3.FAST_V2 = fast_v2
    collected_v5.FAST_V2 = fast_v2
    collected_v5.PRUNED_V3 = pruned_v3
    fixed_v6.FAST_V2 = fast_v2
    fixed_v6.COLLECTED_V5 = collected_v5
    cached_v7.FIXED_V6 = fixed_v6
    cached_v7.FAST_V2 = fast_v2
    cached_v7.COLLECTED_V5 = collected_v5

    # ``base.RADIAL`` is the pinned source *path*.  ``v2.build`` creates the
    # corresponding module later through ``base.import_snapshot``.  Wrap that
    # loader so the sole mathematical substitution is made on the exact
    # runtime module which is then passed into cached-v7.  (Assigning an
    # attribute on ``base.RADIAL`` itself would only touch a Path and cannot
    # affect the computation.)
    original_import_snapshot = base.import_snapshot

    def import_snapshot_with_fixed_polygon(name, path, data):
        module = original_import_snapshot(name, path, data)
        if path == base.RADIAL:
            module._polygon_monomial_batch = \
                fixed_moments.polygon_monomial_batch_fixed
        return module

    base.import_snapshot = import_snapshot_with_fixed_polygon

    dependency_snapshots = {path: path.read_bytes() for path in base.PINNED}
    for path, digest in base.PINNED.items():
        if sha256_bytes(dependency_snapshots[path]) != digest:
            raise RuntimeError(f"inherited pinned source changed: {path}")

    result = v2.build(
        args.common_r, v2_snapshots, dependency_snapshots, base, cached_v7)
    result["format"] = (
        "D14-grid38-scaled-cutoff-cross-common-r-fixed-polygon-v8")
    result["status"] = "EXACT FIXED-POLYGON COMMON-r CROSS SHARD PASS"
    result["algorithm"] = {
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
        raise RuntimeError("fixed-polygon-v8 source closure changed")
    result["producer_sha256"] = args.expected_self_sha256
    payload = canonical_json(result)
    publish_source.publish_exclusive(args.output, payload)
    print(sha256_bytes(payload), args.output)


if __name__ == "__main__":
    main()
