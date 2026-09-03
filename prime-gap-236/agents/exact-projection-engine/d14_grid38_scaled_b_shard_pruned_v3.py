#!/usr/bin/env python3
"""Maximum-shift-pruned exact D14-grid38 cross shard producer.

This v3 wrapper reuses every source/geometry/candidate check in frozen fast
v2.  Its only algebraic change is to discard inclusion--exclusion shifts with
empty support *during* the small-coordinate convolution instead of after a
complete orbit transform has been built.
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
PRUNED_PATH = FILE.with_name("pruned_integer_radial.py")
PRUNED_TEST_PATH = FILE.with_name("test_pruned_integer_radial.py")
PUBLISH_TEST_PATH = FILE.with_name("test_pruned_v3_exclusive_publish.py")
LOCAL_PINNED = {
    V2_PATH: "4613b0fb117bf58c732e9bdeb22fa9d847a1152cc1bcac3b8b92f584231709d3",
    PRUNED_PATH: "834f624647094bf71364ad5c2b47e00371c7e7e78ed37c1d06eeca9186f73afe",
    PRUNED_TEST_PATH: "17b5eac692f859728d502e90a52b2c9c5ce03ef45e7966ce9104d8878910adfd",
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


def publish_exclusive(output, payload):
    """Durably publish bytes without ever replacing an extant final path."""
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(f".{output.name}.tmp.{os.getpid()}")
    if temporary.exists():
        raise FileExistsError(temporary)
    try:
        with temporary.open("xb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        # link(2) is atomic and fails with EEXIST.  Unlike replace(2), a
        # competing/intervening certificate can never be overwritten.
        os.link(temporary, output)
        directory_flags = os.O_RDONLY
        if hasattr(os, "O_DIRECTORY"):
            directory_flags |= os.O_DIRECTORY
        directory = os.open(output.parent, directory_flags)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if temporary.exists():
            temporary.unlink()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--common-r", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--expected-self-sha256", required=True)
    args = parser.parse_args()
    self_data = FILE.read_bytes()
    if sha256_bytes(self_data) != args.expected_self_sha256:
        raise RuntimeError("externally pinned pruned-v3 runner SHA mismatch")
    if not 0 <= args.common_r <= 12:
        raise ValueError("the frozen support has common r=0..12")
    if args.output.exists():
        raise FileExistsError(f"refusing to overwrite {args.output}")

    local_snapshots = {path: path.read_bytes() for path in LOCAL_PINNED}
    for path, digest in LOCAL_PINNED.items():
        if sha256_bytes(local_snapshots[path]) != digest:
            raise RuntimeError(f"local pinned source changed: {path}")
    v2 = load("d14_grid38_pruned_v3_v2", V2_PATH,
              local_snapshots[V2_PATH])
    v2_snapshots = {path: path.read_bytes() for path in v2.LOCAL_PINNED}
    for path, digest in v2.LOCAL_PINNED.items():
        if sha256_bytes(v2_snapshots[path]) != digest:
            raise RuntimeError(f"v2 pinned source changed: {path}")
    base = load("d14_grid38_pruned_v3_base", v2.BASE_PATH,
                v2_snapshots[v2.BASE_PATH])
    fast_v2 = load("d14_grid38_pruned_v3_fast_v2", v2.FAST_PATH,
                   v2_snapshots[v2.FAST_PATH])
    pruned = load("d14_grid38_pruned_v3_algorithm", PRUNED_PATH,
                  local_snapshots[PRUNED_PATH])
    pruned.FAST_V2 = fast_v2
    dependency_snapshots = {path: path.read_bytes() for path in base.PINNED}
    for path, digest in base.PINNED.items():
        if sha256_bytes(dependency_snapshots[path]) != digest:
            raise RuntimeError(f"inherited pinned source changed: {path}")

    result = v2.build(
        args.common_r, v2_snapshots, dependency_snapshots, base, pruned)
    result["format"] = (
        "D14-grid38-scaled-cutoff-cross-common-r-pruned-v3")
    result["status"] = "EXACT PRUNED COMMON-r CROSS SHARD PASS"
    result["algorithm"] = {
        "family_common_denominator_integer_accumulation": True,
        "radial_common_denominator_integer_accumulation": True,
        "affine_products_collected_once_per_tag_and_shift": True,
        "empty_shifts_pruned_inside_small_coordinate_convolution": True,
        "coefficient_level_reference_transform_equality_in_pinned_tests": True,
        "full_low_k_fast_v2_branch_equality_in_pinned_tests": True,
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
        raise RuntimeError("pruned-v3 source closure changed during computation")
    result["producer_sha256"] = args.expected_self_sha256
    payload = canonical_json(result)
    publish_exclusive(args.output, payload)
    print(sha256_bytes(payload), args.output)


if __name__ == "__main__":
    main()
