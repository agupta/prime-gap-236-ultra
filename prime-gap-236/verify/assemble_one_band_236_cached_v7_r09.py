#!/usr/bin/env python3
"""Exact one-band scalar assembly for the total-large-count <= 9 direction.

Let H_full be the naturally dilated D14 polynomial on the sole outer band,
and put H = 1_{R<=9} H_full, where R is the total number of coordinates
strictly larger than delta.  This symmetric truncation keeps A shards
R=0,...,9.  In the mixed marginal it keeps every distinguished-coordinate
branch for common count r=0,...,8, and only the two small-distinguished
branches for r=9.  Counts r>=10 vanish.  This is a separate function and a
separate certificate contract from the full-direction v7 aggregate.
"""

from __future__ import annotations

import argparse
from fractions import Fraction as Q
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat
import sys


if hasattr(sys, "set_int_max_str_digits"):
    sys.set_int_max_str_digits(0)

FILE = Path(__file__).resolve()
REPO = FILE.parents[1]
FULL_ASSEMBLER = FILE.with_name("assemble_one_band_236_cached_v7.py")
FULL_ASSEMBLER_SHA256 = \
    "08fb7e612f37050a21bc94d27e4b8ed0ad1838f64ce5e2a147d15aef9f076f05"
TOTAL_COUNTS = tuple(range(10))
ZEROED_TOTAL_COUNTS = (10, 11, 12)
MIXED_COMMON_COUNTS = tuple(range(10))
R9_BRANCHES = ("Sdelta", "Stotal")


def sha256(data: bytes | Path) -> str:
    raw = data if isinstance(data, bytes) else data.read_bytes()
    return hashlib.sha256(raw).hexdigest()


def load_full():
    data = FULL_ASSEMBLER.read_bytes()
    if sha256(data) != FULL_ASSEMBLER_SHA256:
        raise RuntimeError("pinned full-direction cached-v7 assembler changed")
    spec = importlib.util.spec_from_file_location(
        "one_band_236_cached_v7_r09_pinned_full", FULL_ASSEMBLER)
    if spec is None or spec.loader is None:
        raise ImportError(FULL_ASSEMBLER)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


FULL = load_full()
B = FULL.V6.B
PINS = dict(FULL.PINS)
PINS[FULL_ASSEMBLER] = FULL_ASSEMBLER_SHA256


def require_mixed_files(directory: Path):
    directory = directory.resolve()
    expected = {
        directory / f"common_r_{count:02d}.json"
        for count in MIXED_COMMON_COUNTS}
    if not directory.is_dir():
        raise FileNotFoundError(directory)
    observed = set(directory.glob("common_r_*.json"))
    if observed != expected:
        missing = sorted(str(path) for path in expected - observed)
        extra = sorted(str(path) for path in observed - expected)
        raise ValueError(
            f"incomplete/noncanonical r<=9 mixed shard set: "
            f"missing={missing}, extra={extra}")
    for path in expected:
        mode = path.lstat().st_mode
        if not stat.S_ISREG(mode) or path.is_symlink():
            raise ValueError(f"mixed shard is not a plain regular file: {path}")
    return tuple(sorted(expected))


def selected_b_shard(path: Path, data: bytes, count: int):
    if type(count) is not int or count not in MIXED_COMMON_COUNTS:
        raise ValueError("the R<=9 direction has mixed common counts 0..9")
    full_value = FULL.parse_b_shard(path, data, count)
    if count < 9:
        return full_value, full_value, "all-distinguished-branches"
    raw = B.strict_json(data, str(path))
    block = raw.get("branch_values_and_fast_stats")
    if type(block) is not dict:
        raise ValueError("r=9 branch block is malformed")
    high, low = block.get("high"), block.get("low")
    if (type(high) is not dict or type(low) is not dict or
            not set(R9_BRANCHES) <= set(high) or
            not set(R9_BRANCHES) <= set(low)):
        raise ValueError("r=9 small-distinguished branch inventory is incomplete")
    high_small = sum(
        (B.canonical_q(high[name], f"b[9].high.{name}")
         for name in R9_BRANCHES), Q(0))
    low_small = sum(
        (B.canonical_q(low[name], f"b[9].low.{name}")
         for name in R9_BRANCHES), Q(0))
    selected = B.K * (high_small - low_small)
    return selected, full_value, "small-distinguished-only:Sdelta+Stotal"


def build(a_dir: Path, b_dir: Path, snapshots):
    inner = B.strict_json(snapshots[B.INNER_RESULT], str(B.INNER_RESULT))
    if (inner.get("status") != "INDEPENDENT EXACT PARTICULAR INNER VECTOR PASS" or
            inner.get("rigorous") is not True or
            type(inner.get("k")) is not int or inner.get("k") != B.K or
            inner.get("deficit_positive") is not True or
            inner.get("denominator_positive") is not True):
        raise ValueError("inner result identity mismatch")
    inner_i = B.canonical_q(inner.get("exact_denominator"), "inner I")
    inner_j48 = B.canonical_q(inner.get("exact_numerator"), "inner 48J")
    inner_d = B.canonical_q(inner.get("exact_deficit"), "inner deficit")
    if inner_i - inner_j48 != inner_d or inner_i <= 0 or inner_d <= 0:
        raise ArithmeticError("inner exact-form relation mismatch")

    # A producer metadata describes the full active support, so validate all
    # thirteen immutable A shards before selecting the ten nonzero H strata.
    a_paths = B.require_exact_files(a_dir, "r")
    b_paths = require_mixed_files(b_dir)
    all_a = []
    for count, path in zip(B.COUNTS, a_paths, strict=True):
        data = path.read_bytes()
        all_a.append((count, B.parse_a_shard(path, data, count), sha256(data)))
    b_rows = []
    for count, path in zip(MIXED_COMMON_COUNTS, b_paths, strict=True):
        data = path.read_bytes()
        selected, full_value, selection = selected_b_shard(
            path, data, count)
        b_rows.append((count, selected, full_value, selection, sha256(data)))

    selected_a = [row for row in all_a if row[0] in TOTAL_COUNTS]
    zeroed_a = [row for row in all_a if row[0] in ZEROED_TOTAL_COUNTS]
    a_value = sum((value for _, value, _ in selected_a), Q(0))
    b_value = sum((value for _, value, _, _, _ in b_rows), Q(0))
    i_scaled = inner_i * B.FORM_SCALE
    d_scaled = inner_d * B.FORM_SCALE
    margin = b_value**2 - a_value * d_scaled
    denominator = a_value * i_scaled + b_value**2
    if a_value <= 0 or i_scaled <= 0 or denominator <= 0:
        raise ArithmeticError("R<=9 certificate denominator is nonpositive")
    exact = {
        "A_scaled": a_value,
        "b_scaled": b_value,
        "I_F_scaled": i_scaled,
        "D_scaled": d_scaled,
        "margin_b_squared_minus_A_D": margin,
        "mixing_coefficient_b_over_A": b_value / a_value,
        "normalized_inner_deficit": d_scaled / i_scaled,
        "normalized_projected_energy": b_value**2 / (a_value * i_scaled),
        "quotient_margin_lower_bound": margin /
            (a_value * i_scaled + b_value**2),
        "quotient_lower_bound": Q(1) + margin /
            (a_value * i_scaled + b_value**2),
    }
    return {
        "format": "H1-236-one-band-cached-v7-Rle9-exact-aggregate-v1",
        "status": ("EXACT R<=9 ONE-BAND SCALAR CERTIFICATE PASS"
                   if margin > 0 else
                   "EXACT R<=9 ONE-BAND SCALAR CERTIFICATE FAIL"),
        "rigorous": True,
        "theorem_ready_scalar": margin > 0,
        "k": B.K,
        "outer_direction": {
            "definition": "H=1_{total-large-count<=9}*H_full",
            "symmetric": True,
            "single_outer_band": True,
            "nonzero_total_large_counts": list(TOTAL_COUNTS),
            "zeroed_total_large_counts": list(ZEROED_TOTAL_COUNTS),
            "mixed_common_counts": list(MIXED_COMMON_COUNTS),
            "common_r_9_branches": list(R9_BRANCHES),
            "common_r_0_through_8_branches": "all",
        },
        "scales": {"F": str(B.SCALE_F), "H": str(B.SCALE_H),
                   "quadratic_inner": str(B.FORM_SCALE)},
        "exact": B.encode(exact),
        "a_shards": [
            {"count": count, "value": str(value), "sha256": digest}
            for count, value, digest in selected_a],
        "zeroed_a_shards": [
            {"count": count, "value": str(value), "sha256": digest}
            for count, value, digest in zeroed_a],
        "b_shards": [
            {"count": count, "value": str(value),
             "full_shard_value": str(full_value), "selection": selection,
             "sha256": digest}
            for count, value, full_value, selection, digest in b_rows],
        "trust_scope": (
            "aggregates exact audited shards for the symmetric R<=9 outer "
            "direction; independent integration replay remains separate"),
    }


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--a-dir", type=Path, default=B.DEFAULT_A_DIR)
    parser.add_argument("--b-dir", type=Path, default=FULL.DEFAULT_B_DIR)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--expected-self-sha256", required=True)
    args = parser.parse_args(argv)
    self_data = FILE.read_bytes()
    if sha256(self_data) != args.expected_self_sha256:
        raise RuntimeError("R<=9 assembler source does not match external pin")
    snapshots = {path: path.read_bytes() for path in PINS}
    for path, expected in PINS.items():
        if sha256(snapshots[path]) != expected:
            raise RuntimeError(f"pinned R<=9 dependency changed: {path}")
    result = build(args.a_dir, args.b_dir, snapshots)
    if (FILE.read_bytes() != self_data or
            any(path.read_bytes() != data for path, data in snapshots.items())):
        raise RuntimeError("R<=9 assembler source closure changed")
    result["assembler_sha256"] = args.expected_self_sha256
    result["full_assembler_sha256"] = FULL_ASSEMBLER_SHA256
    result["b_engine"] = "cached-fixed-v7-with-Rle9-branch-projection"
    result["source_hashes"] = {
        str(path.relative_to(REPO)): expected for path, expected in PINS.items()
    }
    payload = B.canonical_json(result)
    B.publish_exclusive(args.output, payload)
    print(sha256(payload), args.output)
    return 0 if result["theorem_ready_scalar"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
