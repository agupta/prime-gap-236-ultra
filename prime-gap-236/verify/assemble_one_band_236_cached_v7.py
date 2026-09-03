#!/usr/bin/env python3
"""Fail-closed exact scalar assembly for cached-fixed-v7 b shards.

The already audited fixed-v6 assembler supplies the A parser, inner-form
normalization, exact projection algebra, and complete r=0..12 inventory.
Each cached-v7 b snapshot is first checked by the separately pinned v7 result
checker, which normalizes only the two proved cache-diagnostic fields and then
replays the independent fixed-v6 structural/result audit.  This file remains
an aggregation/provenance layer, not an integration replay.
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
V6_ASSEMBLER = FILE.with_name("assemble_one_band_236_fixed_v6.py")
V6_ASSEMBLER_SHA256 = \
    "91ab96385d32921c035bd5537a56e8254455a8033bf41e2298b7ec13be552bbc"
V7_CHECKER = REPO / "agents/audit/verify_cached_v7_cross_shard.py"
V7_CHECKER_SHA256 = \
    "80ec3329215f66e784708039f9a1d673d7064769c48a31825961dc44f6ae7343"
V7_RUNNER = REPO / (
    "agents/exact-projection-engine/"
    "d14_grid38_scaled_b_shard_cached_v7.py")
V7_RUNNER_SHA256 = \
    "b427c6961c377cb79d5a72b54f8c2e8c7642b87d66d338f53b5dc56d98991984"
V7_BACKEND = REPO / (
    "agents/exact-projection-engine/cached_fixed_denominator_radial.py")
V7_BACKEND_SHA256 = \
    "79c9a8ef26de0b7fba55fbdb6e113a88f0b52b20f9cbcb34cbc2dbb507ba74c4"
V7_TEST = REPO / (
    "agents/exact-projection-engine/test_cached_fixed_denominator_radial.py")
V7_TEST_SHA256 = \
    "0f0bd15426ff961e47281b32d57795f1848e75280fd645abc599df8d1410fd5b"
TRANSITIVE_CHECKER_PINS = {
    "agents/audit/verify_fixed_v6_cross_shard.py":
        "46a8bd9b116a59078d5e3e6cc7a19887032421b60cbbb5afc605d205fa1ba954",
    "agents/audit/verify_collected_v5_cross_shard.py":
        "11e2930bce62f13faf8c4874a439ab02220e155a384ea1f0e0587a871cb4abb9",
    "agents/audit/verify_pruned_v3_cross_shard.py":
        "0abbf021581092ed4b27a1ee303046ad349804d50f7c4882a307cee9b750ba92",
}
DEFAULT_B_DIR = REPO / (
    "agents/exact-projection-engine/results/"
    "d14_grid38_scaled_b_cached_v7")


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


V6 = load_pinned("one_band_236_cached_v7_pinned_v6_assembler",
                 V6_ASSEMBLER, V6_ASSEMBLER_SHA256)
V7 = load_pinned("one_band_236_cached_v7_pinned_result_checker",
                 V7_CHECKER, V7_CHECKER_SHA256)

PINS = dict(V6.PINS)
PINS.update({
    V6_ASSEMBLER: V6_ASSEMBLER_SHA256,
    V7_CHECKER: V7_CHECKER_SHA256,
    V7_RUNNER: V7_RUNNER_SHA256,
    V7_BACKEND: V7_BACKEND_SHA256,
    V7_TEST: V7_TEST_SHA256,
})
for relative, expected in V7.SOURCE_HASHES.items():
    path = REPO / relative
    previous = PINS.get(path)
    if previous is not None and previous != expected:
        raise RuntimeError(f"inconsistent v7 source pin: {relative}")
    PINS[path] = expected
for relative, expected in TRANSITIVE_CHECKER_PINS.items():
    path = REPO / relative
    previous = PINS.get(path)
    if previous is not None and previous != expected:
        raise RuntimeError(f"inconsistent transitive checker pin: {relative}")
    PINS[path] = expected


def parse_b_shard(path: Path, data: bytes, count: int):
    """Audit the exact supplied byte snapshot, never a second path read."""
    with tempfile.TemporaryDirectory(prefix="cached-v7-assembler-audit-") as root:
        snapshot = Path(root) / f"common_r_{count:02d}.json"
        snapshot.write_bytes(data)
        audited = V7.audit(snapshot)
    if (audited.get("status") !=
            "CACHED-V7 CROSS SHARD STRUCTURAL/RESULT AUDIT PASS" or
            type(audited.get("common_r")) is not int or
            audited.get("common_r") != count or
            audited.get("input_sha256") != sha256(data) or
            audited.get("recombined_exactly") is not True or
            audited.get("fixed_denominator_relation_verified") is not True or
            audited.get("cache_inventory_semantics_verified") is not True or
            audited.get("source_closure_verified") is not True):
        raise ArithmeticError(f"cached-v7 result audit failed: {path}")
    return V6.B.canonical_q(audited.get("scaled_b_shard"), f"b[{count}]")


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--a-dir", type=Path, default=V6.B.DEFAULT_A_DIR)
    parser.add_argument("--b-dir", type=Path, default=DEFAULT_B_DIR)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--expected-self-sha256", required=True)
    args = parser.parse_args(argv)
    self_data = FILE.read_bytes()
    if sha256(self_data) != args.expected_self_sha256:
        raise RuntimeError("cached-v7 assembler source does not match external pin")
    snapshots = {path: path.read_bytes() for path in PINS}
    for path, expected in PINS.items():
        if sha256(snapshots[path]) != expected:
            raise RuntimeError(f"pinned cached-v7 dependency changed: {path}")
    old_parser = V6.B.parse_b_shard
    try:
        V6.B.parse_b_shard = parse_b_shard
        result = V6.B.build(args.a_dir, args.b_dir, snapshots)
    finally:
        V6.B.parse_b_shard = old_parser
    if (FILE.read_bytes() != self_data or
            any(path.read_bytes() != data for path, data in snapshots.items())):
        raise RuntimeError("cached-v7 assembler source closure changed")
    result["format"] = "H1-236-one-band-cached-v7-exact-shard-aggregate-v1"
    result["assembler_sha256"] = args.expected_self_sha256
    result["base_assembler_sha256"] = V6_ASSEMBLER_SHA256
    result["b_engine"] = "cached-fixed-v7"
    result["source_hashes"] = {
        str(path.relative_to(REPO)): expected for path, expected in PINS.items()
    }
    payload = V6.B.canonical_json(result)
    V6.B.publish_exclusive(args.output, payload)
    print(sha256(payload), args.output)
    return 0 if result["theorem_ready_scalar"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
