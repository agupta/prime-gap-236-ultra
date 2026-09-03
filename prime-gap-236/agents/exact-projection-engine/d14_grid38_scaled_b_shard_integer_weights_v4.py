#!/usr/bin/env python3
"""Exact D14-grid38 cross shard with integer scalar-moment contraction.

This v4 wrapper retains the audited maximum-shift-pruned radial transform.
For each surviving shift it additionally clears a common denominator from
the collected affine coefficients and from the polygon moments, performs the
large scalar contraction over integers, and restores those denominators once.
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
V2_PATH = FILE.with_name("d14_grid38_scaled_b_shard_fast_v2.py")
V3_PATH = FILE.with_name("pruned_integer_radial.py")
V4_PATH = FILE.with_name("integer_weight_scalar.py")
V3_TEST_PATH = FILE.with_name("test_pruned_integer_radial.py")
V4_TEST_PATH = FILE.with_name("test_integer_weight_scalar.py")
PUBLISH_SOURCE_PATH = FILE.with_name(
    "d14_grid38_scaled_b_shard_pruned_v3.py")
PUBLISH_TEST_PATH = FILE.with_name("test_pruned_v3_exclusive_publish.py")
LOCAL_PINNED = {
    V2_PATH: "4613b0fb117bf58c732e9bdeb22fa9d847a1152cc1bcac3b8b92f584231709d3",
    V3_PATH: "834f624647094bf71364ad5c2b47e00371c7e7e78ed37c1d06eeca9186f73afe",
    V4_PATH: "316ef7ab97f22c7163ec2687cc21db8351c47ff7697122d5d58476cfacbc5b32",
    V3_TEST_PATH: "17b5eac692f859728d502e90a52b2c9c5ce03ef45e7966ce9104d8878910adfd",
    V4_TEST_PATH: "5f073c808d7f73b07ab92c31117b76fe1f5c05c1201640e7072736a0b1fa64d8",
    PUBLISH_SOURCE_PATH: "ce5236eaed52be549a316587e8c3c543a0b02b1594c14ba32f4c1a877fd9bb26",
    PUBLISH_TEST_PATH: "855b3e07ee71f75917a9ddceb2d969e10aab8c81550aa036423f7104eb5ef78d",
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
        raise RuntimeError("externally pinned integer-weights-v4 runner SHA mismatch")
    if not 0 <= args.common_r <= 12:
        raise ValueError("the frozen support has common r=0..12")
    if args.output.exists():
        raise FileExistsError(f"refusing to overwrite {args.output}")

    local_snapshots = {path: path.read_bytes() for path in LOCAL_PINNED}
    for path, digest in LOCAL_PINNED.items():
        if sha256_bytes(local_snapshots[path]) != digest:
            raise RuntimeError(f"local pinned source changed: {path}")
    v2 = load("d14_grid38_integer_v4_v2", V2_PATH,
              local_snapshots[V2_PATH])
    v2_snapshots = {path: path.read_bytes() for path in v2.LOCAL_PINNED}
    for path, digest in v2.LOCAL_PINNED.items():
        if sha256_bytes(v2_snapshots[path]) != digest:
            raise RuntimeError(f"v2 pinned source changed: {path}")
    base = load("d14_grid38_integer_v4_base", v2.BASE_PATH,
                v2_snapshots[v2.BASE_PATH])
    fast_v2 = load("d14_grid38_integer_v4_fast_v2", v2.FAST_PATH,
                   v2_snapshots[v2.FAST_PATH])
    pruned_v3 = load("d14_grid38_integer_v4_pruned_v3", V3_PATH,
                     local_snapshots[V3_PATH])
    integer_v4 = load("d14_grid38_integer_v4_algorithm", V4_PATH,
                      local_snapshots[V4_PATH])
    pruned_v3.FAST_V2 = fast_v2
    integer_v4.FAST_V2 = fast_v2
    integer_v4.PRUNED_V3 = pruned_v3
    publish_source = load(
        "d14_grid38_integer_v4_publish", PUBLISH_SOURCE_PATH,
        local_snapshots[PUBLISH_SOURCE_PATH])
    dependency_snapshots = {path: path.read_bytes() for path in base.PINNED}
    for path, digest in base.PINNED.items():
        if sha256_bytes(dependency_snapshots[path]) != digest:
            raise RuntimeError(f"inherited pinned source changed: {path}")

    result = v2.build(
        args.common_r, v2_snapshots, dependency_snapshots, base, integer_v4)
    result["format"] = (
        "D14-grid38-scaled-cutoff-cross-common-r-integer-weights-v4")
    result["status"] = "EXACT INTEGER-WEIGHTS COMMON-r CROSS SHARD PASS"
    result["algorithm"] = {
        "family_common_denominator_integer_accumulation": True,
        "radial_common_denominator_integer_accumulation": True,
        "empty_shifts_pruned_inside_small_coordinate_convolution": True,
        "affine_products_collected_once_per_tag_and_shift": True,
        "affine_common_denominator_integer_contraction": True,
        "moment_common_denominator_integer_contraction": True,
        "denominators_restored_exactly_once_per_shift": True,
        "coefficient_level_reference_transform_equality_in_pinned_tests": True,
        "full_low_k_pruned_v3_branch_equality_in_pinned_tests": True,
    }
    result["source_hashes"].update({
        str(path.relative_to(REPO)): digest
        for path, digest in LOCAL_PINNED.items()})
    result["peak_rss_kib"] = resource.getrusage(
        resource.RUSAGE_SELF).ru_maxrss

    if (FILE.read_bytes() != self_data or
            any(path.read_bytes() != data
                for path, data in local_snapshots.items()) or
            any(path.read_bytes() != data
                for path, data in v2_snapshots.items()) or
            any(path.read_bytes() != data
                for path, data in dependency_snapshots.items())):
        raise RuntimeError("integer-weights-v4 source closure changed during computation")
    result["producer_sha256"] = args.expected_self_sha256
    payload = canonical_json(result)
    publish_source.publish_exclusive(args.output, payload)
    print(sha256_bytes(payload), args.output)


if __name__ == "__main__":
    main()
