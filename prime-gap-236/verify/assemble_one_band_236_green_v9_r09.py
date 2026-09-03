#!/usr/bin/env python3
"""Exact R<=9 one-band assembly for Green-polygon-v9 mixed shards.

The pinned R<=9 assembler fixes the mathematical count projection and exact
scalar algebra.  This wrapper changes only the mixed-shard parser.  Each
supplied byte snapshot is checked by the independent Green-v9 result checker,
which normalizes it to the independently audited fixed-polygon-v8 contract and
replays the complete v8/v7/v6 structural and recombination checks.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
from pathlib import Path
import sys
import tempfile


if hasattr(sys, "set_int_max_str_digits"):
    sys.set_int_max_str_digits(0)

FILE = Path(__file__).resolve()
REPO = FILE.parents[1]
R09_ASSEMBLER = FILE.with_name("assemble_one_band_236_cached_v7_r09.py")
R09_ASSEMBLER_SHA256 = \
    "aaa3dc5199636da3dcff198fd16a84b097a192a72d89a5326dc690206946ce29"
GREEN_CHECKER = REPO / "agents/audit/verify_green_v9_cross_shard.py"
GREEN_CHECKER_SHA256 = \
    "7dbb352011d840a5bddf8f6f101f864d0a1b1e436ff4ebb5533ef1137217b4a7"
GREEN_CHECKER_TEST = REPO / "agents/audit/test_verify_green_v9_cross_shard.py"
GREEN_CHECKER_TEST_SHA256 = \
    "6510af2c6705bd9ad1efde5ecd802547fda93243d361e3edc6c82502a96e4c4c"
GREEN_RUNNER = REPO / (
    "agents/exact-projection-engine/"
    "d14_grid38_scaled_b_shard_green_v9.py")
GREEN_RUNNER_SHA256 = \
    "ad38951dadecdb5a5c51d1221b0a078bc9f804e9c4ec8d434706fca55a11935a"
DEFAULT_B_DIR = REPO / (
    "agents/exact-projection-engine/results/"
    "d14_grid38_scaled_b_green_v9")


def sha256(data: bytes | Path) -> str:
    raw = data if isinstance(data, bytes) else data.read_bytes()
    return hashlib.sha256(raw).hexdigest()


def load_pinned(name: str, path: Path, expected: str):
    data = path.read_bytes()
    if sha256(data) != expected:
        raise RuntimeError(f"pinned {name} changed")
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


R09 = load_pinned(
    "one_band_236_green_v9_pinned_r09_assembler",
    R09_ASSEMBLER, R09_ASSEMBLER_SHA256)
GREEN = load_pinned(
    "one_band_236_green_v9_pinned_result_checker",
    GREEN_CHECKER, GREEN_CHECKER_SHA256)
B = R09.B

PINS = dict(R09.PINS)
PINS.update({
    R09_ASSEMBLER: R09_ASSEMBLER_SHA256,
    GREEN_CHECKER: GREEN_CHECKER_SHA256,
    GREEN_CHECKER_TEST: GREEN_CHECKER_TEST_SHA256,
    GREEN_RUNNER: GREEN_RUNNER_SHA256,
    GREEN.V8_CHECKER_PATH: GREEN.V8_CHECKER_SHA,
    REPO / GREEN.V8.PRODUCER: GREEN.V8.PRODUCER_SHA,
})
for source_map in (GREEN.SOURCE_HASHES, GREEN.V8.SOURCE_HASHES):
    for relative, expected in source_map.items():
        path = REPO / relative
        previous = PINS.get(path)
        if previous is not None and previous != expected:
            raise RuntimeError(f"inconsistent Green-v9 pin: {relative}")
        PINS[path] = expected


def parse_b_green(path: Path, data: bytes, count: int):
    """Audit the supplied immutable bytes, never a second read of ``path``."""
    with tempfile.TemporaryDirectory(prefix="green-v9-assembler-") as root:
        snapshot = Path(root) / f"common_r_{count:02d}.json"
        snapshot.write_bytes(data)
        audited = GREEN.audit(snapshot)
    if (audited.get("status") !=
            "GREEN-V9 CROSS SHARD STRUCTURAL/RESULT AUDIT PASS" or
            type(audited.get("common_r")) is not int or
            audited.get("common_r") != count or
            audited.get("input_sha256") != sha256(data) or
            audited.get("recombined_exactly") is not True or
            audited.get("fixed_denominator_relation_verified") is not True or
            audited.get("cache_inventory_semantics_verified") is not True or
            audited.get("green_boundary_denominator_proof_pinned") is not True or
            audited.get("convexity_fail_closed") is not True or
            audited.get("source_closure_verified") is not True or
            audited.get("reference_exact_fields_bit_equal") is not None or
            audited.get("reference_sha256") is not None):
        raise ArithmeticError(f"Green-v9 result audit failed: {path}")
    return B.canonical_q(audited.get("scaled_b_shard"), f"b[{count}]")


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--a-dir", type=Path, default=B.DEFAULT_A_DIR)
    parser.add_argument("--b-dir", type=Path, default=DEFAULT_B_DIR)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--expected-self-sha256", required=True)
    args = parser.parse_args(argv)
    self_data = FILE.read_bytes()
    if sha256(self_data) != args.expected_self_sha256:
        raise RuntimeError("Green-v9 R<=9 assembler source does not match external pin")
    snapshots = {path: path.read_bytes() for path in PINS}
    for path, expected in PINS.items():
        if sha256(snapshots[path]) != expected:
            raise RuntimeError(f"pinned Green-v9 R<=9 dependency changed: {path}")
    old_parser = R09.FULL.parse_b_shard
    try:
        R09.FULL.parse_b_shard = parse_b_green
        result = R09.build(args.a_dir, args.b_dir, snapshots)
    finally:
        R09.FULL.parse_b_shard = old_parser
    if (FILE.read_bytes() != self_data or
            any(path.read_bytes() != data
                for path, data in snapshots.items())):
        raise RuntimeError("Green-v9 R<=9 source closure changed")
    result["format"] = (
        "H1-236-one-band-green-v9-Rle9-exact-aggregate-v1")
    result["assembler_sha256"] = args.expected_self_sha256
    result["rle9_base_assembler_sha256"] = R09_ASSEMBLER_SHA256
    result["full_assembler_sha256"] = R09.FULL_ASSEMBLER_SHA256
    result["b_engine"] = "green-v9-with-Rle9-branch-projection"
    result["source_hashes"] = {
        str(path.relative_to(REPO)): expected
        for path, expected in PINS.items()}
    payload = B.canonical_json(result)
    B.publish_exclusive(args.output, payload)
    print(sha256(payload), args.output)
    return 0 if result["theorem_ready_scalar"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
