#!/usr/bin/env python3
"""Fail-closed assembler for checkpointed active25 D18 outer-I shards."""

from __future__ import annotations

import argparse
from decimal import Decimal, localcontext
from fractions import Fraction as Q
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat
import sys


FILE = Path(__file__).resolve()
REPO = FILE.parents[1]
PRODUCER = REPO / "scripts/stage_active25_d18_outer_i_exact.py"
PRODUCER_TEST = REPO / "scripts/test_stage_active25_d18_outer_i_exact.py"
PINS = {
    PRODUCER:
        "32deb9aef6c09c46c17b05d8145751029894f493452baa45375cdabab980cb40",
    PRODUCER_TEST:
        "6a6af5ccdb53b4195e41ff256460ae3e56a03031a1f637a33ea8996cdc140bd3",
}
GROUPS = 10761
CHUNK = 500
STRATA = 26


def sha256(value) -> str:
    data = value if isinstance(value, bytes) else Path(value).read_bytes()
    return hashlib.sha256(data).hexdigest()


def require_pins():
    result = {}
    for path, expected in PINS.items():
        data = path.read_bytes()
        if sha256(data) != expected:
            raise RuntimeError(f"assembler dependency changed: {path}")
        result[path] = data
    return result


_START = require_pins()
_SPEC = importlib.util.spec_from_file_location("active25_d18_i_stage", PRODUCER)
if _SPEC is None or _SPEC.loader is None:
    raise ImportError(PRODUCER)
stage = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = stage
_SPEC.loader.exec_module(stage)


def expected_intervals(groups=GROUPS, chunk=CHUNK):
    if (type(groups) is not int or type(chunk) is not int or
            groups <= 0 or chunk <= 0):
        raise ValueError("invalid interval geometry")
    return [(start, min(start + chunk, groups))
            for start in range(0, groups, chunk)]


def leaf_name(stratum, start, stop):
    return f"stratum_{stratum:02d}_groups_{start:05d}_{stop:05d}.json"


def strict_fraction(value, name):
    if type(value) is not str:
        raise ValueError(f"{name} is not a string")
    parsed = Q(value)
    if str(parsed) != value:
        raise ValueError(f"{name} is not a canonical rational")
    return parsed


def canonical_json(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"),
                       allow_nan=False) + "\n").encode("ascii")


def strict_stage(value, identity):
    keys = {
        "basis_dimension", "capped_outer_I_in_stratum",
        "complete_stratum", "dilation", "format",
        "high_I_in_stratum", "low_I_in_stratum", "parameters",
        "peak_rss_kib", "rigorous_values", "scalar_source_sha256",
        "script_sha256", "source_hashes", "square_orbit_groups",
        "square_orbit_group_start", "square_orbit_group_stop", "status",
        "stratum", "theorem_ready", "uncapped_outer_I",
        "wall_nanoseconds",
    }
    if type(value) is not dict or set(value) != keys:
        raise ValueError("stage schema mismatch")
    r = value["stratum"]
    start = value["square_orbit_group_start"]
    stop = value["square_orbit_group_stop"]
    expected_complete = start == 0 and stop == GROUPS
    if (type(r) is not int or r not in range(STRATA) or
            type(start) is not int or type(stop) is not int or
            not 0 <= start < stop <= GROUPS or
            value["basis_dimension"] != 471 or
            value["complete_stratum"] is not expected_complete or
            value["dilation"] != identity["dilation"] or
            value["format"] !=
            "active25-d18-natural-outer-I-stratum-v1" or
            value["parameters"] != identity["parameters"] or
            type(value["peak_rss_kib"]) is not int or
            value["peak_rss_kib"] <= 0 or
            value["rigorous_values"] is not True or
            value["scalar_source_sha256"] != stage.PINS[stage.SCALAR] or
            value["script_sha256"] != PINS[PRODUCER] or
            value["source_hashes"] != identity["source_hashes"] or
            value["square_orbit_groups"] != GROUPS or
            value["status"] != "EXACT I-ONLY STRATUM DIAGNOSTIC" or
            value["theorem_ready"] is not False or
            value["uncapped_outer_I"] != identity["uncapped_outer_I"] or
            type(value["wall_nanoseconds"]) is not int or
            value["wall_nanoseconds"] <= 0):
        raise ValueError("stage identity mismatch")
    hi = strict_fraction(value["high_I_in_stratum"], "high I")
    lo = strict_fraction(value["low_I_in_stratum"], "low I")
    capped = strict_fraction(
        value["capped_outer_I_in_stratum"], "capped I")
    if capped != hi - lo:
        raise ArithmeticError("stage H-L identity failed")
    if expected_complete and (hi < 0 or lo < 0 or capped < 0):
        raise ArithmeticError("complete exact square moment is negative")
    return r, start, stop, hi, lo, capped


def target_identity():
    scalar, core, _, uncapped, dilation, square, _, _ = stage.load_target()
    if len(square) != GROUPS:
        raise ArithmeticError("square inventory changed")
    return {
        "dilation": str(dilation),
        "parameters": core.parameter_record(),
        "source_hashes": {
            str(path.relative_to(REPO)): expected
            for path, expected in sorted(
                scalar.PINS.items(), key=lambda item: str(item[0]))
        },
        "uncapped_outer_I": uncapped["I_matrix"][1][1],
    }


def read_exact_directory(path):
    directory = Path(path).resolve(strict=True)
    flags = os.O_RDONLY
    if hasattr(os, "O_DIRECTORY"):
        flags |= os.O_DIRECTORY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(directory, flags)
    try:
        observed = os.fstat(descriptor)
        if not stat.S_ISDIR(observed.st_mode):
            raise ValueError("record path is not a directory")
        expected = {
            leaf_name(r, start, stop)
            for r in range(STRATA)
            for start, stop in expected_intervals()
        }
        actual = set(os.listdir(descriptor))
        if actual != expected:
            missing = sorted(expected - actual)
            extra = sorted(actual - expected)
            raise ValueError(
                f"incomplete/nonexact shard set: missing={missing[:3]}, "
                f"extra={extra[:3]}")
        identity = target_identity()
        rows = []
        bindings = []
        for r in range(STRATA):
            for start, stop in expected_intervals():
                leaf = leaf_name(r, start, stop)
                open_flags = os.O_RDONLY
                if hasattr(os, "O_NOFOLLOW"):
                    open_flags |= os.O_NOFOLLOW
                fd = os.open(leaf, open_flags, dir_fd=descriptor)
                try:
                    before = os.fstat(fd)
                    if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
                        raise ValueError("shard is not a singly linked regular file")
                    data = b""
                    while True:
                        block = os.read(fd, 1024 * 1024)
                        if not block:
                            break
                        data += block
                    after = os.fstat(fd)
                    if ((before.st_dev, before.st_ino, before.st_size,
                         before.st_mtime_ns) !=
                            (after.st_dev, after.st_ino, after.st_size,
                             after.st_mtime_ns)):
                        raise RuntimeError("shard changed while being read")
                finally:
                    os.close(fd)
                try:
                    value = json.loads(data)
                except (UnicodeDecodeError, json.JSONDecodeError) as error:
                    raise ValueError("shard is not strict JSON") from error
                if canonical_json(value) != data:
                    raise ValueError("shard JSON is not canonical")
                row = strict_stage(value, identity)
                if row[:3] != (r, start, stop):
                    raise ValueError("shard content/leaf mismatch")
                rows.append(row)
                bindings.append({"leaf": leaf, "sha256": sha256(data),
                                 "device": int(before.st_dev),
                                 "inode": int(before.st_ino)})
        return directory, int(observed.st_dev), int(observed.st_ino), \
            identity, rows, bindings
    finally:
        os.close(descriptor)


def build_result(record_dir):
    self_start = FILE.read_bytes()
    pin_start = require_pins()
    directory, device, inode, identity, rows, bindings = \
        read_exact_directory(record_dir)
    high = sum((row[3] for row in rows), Q(0))
    low = sum((row[4] for row in rows), Q(0))
    capped = sum((row[5] for row in rows), Q(0))
    uncapped = Q(identity["uncapped_outer_I"])
    if capped != high - low or not Q(0) < low < high or not capped <= uncapped:
        raise ArithmeticError("assembled exact denominator nesting failed")
    with localcontext() as context:
        context.prec = 50
        retained = Decimal(capped.numerator) / Decimal(capped.denominator)
        retained /= Decimal(uncapped.numerator) / Decimal(uncapped.denominator)
    if FILE.read_bytes() != self_start or require_pins() != pin_start:
        raise RuntimeError("assembler source closure changed")
    return {
        "assembler_sha256": sha256(self_start),
        "capped_outer_I": str(capped),
        "complete_exact_cover": True,
        "dilation": identity["dilation"],
        "exact_retained_fraction": str(capped / uncapped),
        "format": "active25-d18-natural-outer-I-assembled-v1",
        "high_I": str(high),
        "low_I": str(low),
        "parameters": identity["parameters"],
        "record_directory_binding": {
            "device": device, "inode": inode, "path": str(directory)},
        "retained_fraction_decimal_50": str(retained),
        "rigorous_values": True,
        "shard_bindings": bindings,
        "shard_count": len(rows),
        "source_hashes": identity["source_hashes"],
        "status": "EXACT I-ONLY DIAGNOSTIC",
        "theorem_ready": False,
        "uncapped_outer_I": str(uncapped),
    }


def publish_exclusive(path, payload):
    target = Path(path).resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    try:
        with os.fdopen(fd, "wb", closefd=False) as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    finally:
        os.close(fd)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--record-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = canonical_json(build_result(args.record_dir))
    publish_exclusive(args.output, payload)
    print(json.dumps({"output_sha256": sha256(payload)}, sort_keys=True))


if __name__ == "__main__":
    main()
