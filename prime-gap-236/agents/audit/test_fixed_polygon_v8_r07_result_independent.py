#!/usr/bin/env python3
"""Independent result-level audit for the frozen fixed-polygon-v8 r=7 shard.

This script does not import the producer or its arithmetic modules.  It
checks the serialized exact branch identity directly, checks the complete
serialized source closure against live bytes, and invokes the separately
frozen structural checker in normal and optimized isolated Python processes.
"""

from __future__ import annotations

from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess
import sys
import tempfile


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
SHARD = (REPO / "agents/exact-projection-engine/results/"
         "d14_grid38_scaled_b_fixed_polygon_v8/common_r_07.json")
CHECKER = HERE / "verify_fixed_polygon_v8_cross_shard.py"
NORMAL_AUDIT = (HERE / "results/d14_grid38_scaled_b_fixed_polygon_v8/"
                "common_r_07.normal.audit.json")
OPT_AUDIT = (HERE / "results/d14_grid38_scaled_b_fixed_polygon_v8/"
             "common_r_07.optimized.audit.json")

SHARD_SHA = "8636441adc493afae16daaa81e60cd3bad5e1b63ce362391c7067e57fddece18"
CHECKER_SHA = "ec0162a73381d031e4ab7b5d8cb1fa16381e41f19c74a6fd74aafa0c30a8655c"
AUDIT_SHA = "951414e9ed0cad4d65f55ac9d73fd9855ba2d917558897eb6fc4392c5e34e675"
PRODUCER_SHA = "36a8e027c83cabb272aa28a5d542dc571793cbcf90c5ca48787bc20092a55b72"
CORE_SHA = "4100a9eeb86563ae84bf02ed4df9a2a5b696b5cc9ff163d15ac482b242b637bb"
EXPECTED_TOP = {
    "algorithm", "branch_values_and_fast_stats", "candidate", "common_r",
    "family_stats", "format", "geometry", "kernel_stats", "peak_rss_kib",
    "producer_sha256", "rigorous", "scaled_b_shard", "scaling",
    "serialized_matrices_read", "source_hashes", "status", "timing_seconds",
}
BRANCHES = {"Lbig", "Ltotal", "Sdelta", "Stotal"}
RATIONAL = re.compile(r"-?(?:0|[1-9][0-9]*)(?:/[1-9][0-9]*)?\Z")
HEX64 = re.compile(r"[0-9a-f]{64}\Z")


def fail(message: str) -> None:
    raise RuntimeError(message)


def sha(value: bytes | Path) -> str:
    if isinstance(value, Path):
        value = value.read_bytes()
    return hashlib.sha256(value).hexdigest()


def canonical(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"),
                       ensure_ascii=True, allow_nan=False) + "\n").encode("ascii")


def parse_json(data: bytes) -> object:
    def reject_constant(token: str) -> None:
        fail(f"non-finite JSON token: {token}")
    return json.loads(data, parse_constant=reject_constant)


def rational(value: object, label: str) -> Fraction:
    if type(value) is not str or RATIONAL.fullmatch(value) is None:
        fail(f"{label} is not a canonical rational string")
    answer = Fraction(value)
    if str(answer) != value:
        fail(f"{label} is not reduced/canonical")
    return answer


def run_checker(shard: Path, optimized: bool = False,
                output: Path | None = None) -> subprocess.CompletedProcess[bytes]:
    with tempfile.TemporaryDirectory(prefix="r07-v8-private-cache-") as root:
        prefix = Path(root) / "absent-private-pycache"
        command = [sys.executable]
        if optimized:
            command.append("-O")
        command.extend([
            "-B", "-I", "-X", f"pycache_prefix={prefix}", str(CHECKER),
            "--expected-self-sha256", CHECKER_SHA,
        ])
        if output is not None:
            command.extend(["--output", str(output)])
        command.append(str(shard))
        completed = subprocess.run(command, cwd=REPO, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, check=False)
        if prefix.exists():
            fail("isolated checker unexpectedly created its private bytecode path")
        return completed


def exact_snapshot_test() -> bytes:
    before = SHARD.read_bytes()
    if sha(before) != SHARD_SHA:
        fail("r7 shard bytes do not match the external pin")
    raw = parse_json(before)
    if type(raw) is not dict or set(raw) != EXPECTED_TOP:
        fail("r7 top-level schema mismatch")
    if canonical(raw) != before:
        fail("r7 shard is not strict canonical JSON")
    if (raw["common_r"] != 7 or type(raw["common_r"]) is not int or
            raw["geometry"]["k"] != 48 or
            type(raw["geometry"]["k"]) is not int):
        fail("wrong k or common count")
    if (raw["rigorous"] is not True or
            raw["serialized_matrices_read"] is not False or
            raw["producer_sha256"] != PRODUCER_SHA):
        fail("r7 identity/status contract mismatch")

    source_hashes = raw["source_hashes"]
    if type(source_hashes) is not dict or not source_hashes:
        fail("source closure is not a nonempty object")
    if source_hashes.get(
            "agents/exact-projection-engine/fixed_polygon_moments.py") != CORE_SHA:
        fail("fixed-polygon core is not pinned")
    root = REPO.resolve()
    for relative, expected in source_hashes.items():
        if (type(relative) is not str or not relative or relative.startswith("/") or
                type(expected) is not str or HEX64.fullmatch(expected) is None):
            fail("malformed serialized source pin")
        path = (REPO / relative).resolve()
        try:
            path.relative_to(root)
        except ValueError:
            fail("serialized source path escapes the repository")
        if sha(path) != expected:
            fail(f"live source closure mismatch: {relative}")
    if sha(CHECKER) != CHECKER_SHA:
        fail("independent checker pin changed")

    block = raw["branch_values_and_fast_stats"]
    if type(block) is not dict or set(block["high"]) != BRANCHES or \
            set(block["low"]) != BRANCHES:
        fail("r7 does not contain all four branches at both endpoints")
    high = {name: rational(value, f"high.{name}")
            for name, value in block["high"].items()}
    low = {name: rational(value, f"low.{name}")
           for name, value in block["low"].items()}
    observed = rational(raw["scaled_b_shard"], "scaled_b_shard")
    recomputed = 48 * (sum(high.values(), Fraction(0)) -
                       sum(low.values(), Fraction(0)))
    if observed != recomputed:
        fail("independent exact factor-48 branch recombination failed")
    if observed <= 0:
        fail("r7 exact shard value is not positive")
    if (observed.numerator.bit_length(), observed.denominator.bit_length()) != \
            (2372, 2480):
        fail("unexpected exact result bit lengths")

    active_shifts = 14 - raw["common_r"] + 1
    scalar_products = 0
    monomials = 0
    for side in ("high_stats", "low_stats"):
        rows = block[side]
        if type(rows) is not dict or set(rows) != BRANCHES:
            fail(f"{side} branch-stat inventory mismatch")
        for name, row in rows.items():
            if type(row) is not dict or row.get("active_shifts") != active_shifts:
                fail(f"{side}.{name} has wrong active-shift count")
            for key, value in row.items():
                if type(value) is not int or value < 0:
                    fail(f"{side}.{name}.{key} is not a nonnegative exact integer")
            scalar_products += row["scalar_products"]
            monomials += row["nonzero_product_monomials"]
    if scalar_products != 317128584 or monomials != 42032:
        fail("independent work-inventory totals disagree")
    if block["integer_radialization"]["radial_stats"]["maximum_shift_pruned_inside_convolution"] != 7:
        fail("maximum active shift is not H=14-r=7")
    if block["integer_radialization"]["active_branch_families"] != \
            ["large", "small", "small_total"]:
        fail("active family inventory mismatch")
    for where in (raw["timing_seconds"], block["timing_seconds"]):
        if type(where) is not dict or any(
                type(value) not in (int, float) or isinstance(value, bool) or
                not math.isfinite(value) or value < 0 for value in where.values()):
            fail("invalid timing diagnostics")
    if SHARD.read_bytes() != before:
        fail("r7 shard changed during independent exact audit")
    return before


def mode_and_mutation_test(original: bytes) -> None:
    normal = run_checker(SHARD)
    optimized = run_checker(SHARD, optimized=True)
    for label, completed in (("normal", normal), ("optimized", optimized)):
        if completed.returncode != 0 or completed.stderr:
            fail(f"{label} checker failed: {completed.stderr.decode('utf-8', 'replace')}")
        if sha(completed.stdout) != AUDIT_SHA:
            fail(f"{label} checker output hash mismatch")
    if normal.stdout != optimized.stdout:
        fail("normal and optimized checker outputs differ")
    if NORMAL_AUDIT.read_bytes() != normal.stdout or OPT_AUDIT.read_bytes() != normal.stdout:
        fail("preserved audit outputs differ from fresh mode outputs")
    audit = parse_json(normal.stdout)
    if audit["input_sha256"] != SHARD_SHA or audit["recombined_exactly"] is not True:
        fail("checker output is not bound to the audited r7 bytes")

    raw = parse_json(original)
    mutants: list[tuple[str, object]] = []
    changed = json.loads(json.dumps(raw))
    changed["scaled_b_shard"] = str(rational(changed["scaled_b_shard"], "scaled") + 1)
    mutants.append(("changed scalar", changed))
    changed = json.loads(json.dumps(raw))
    changed["branch_values_and_fast_stats"]["high"]["Sdelta"] = "0"
    mutants.append(("changed branch", changed))
    changed = json.loads(json.dumps(raw))
    changed["source_hashes"]["agents/exact-projection-engine/fixed_polygon_moments.py"] = "0" * 64
    mutants.append(("changed source pin", changed))
    changed = json.loads(json.dumps(raw))
    changed["common_r"] = True
    mutants.append(("Boolean count alias", changed))
    changed = json.loads(json.dumps(raw))
    changed["extra"] = 0
    mutants.append(("extra schema field", changed))
    with tempfile.TemporaryDirectory(prefix="r07-v8-mutants-") as root:
        root_path = Path(root)
        for index, (label, mutant) in enumerate(mutants):
            path = root_path / f"mutant-{index}.json"
            path.write_bytes(canonical(mutant))
            completed = run_checker(path)
            if completed.returncode == 0:
                fail(f"checker accepted {label}")

        sentinel = root_path / "sentinel.json"
        sentinel_bytes = b"DO-NOT-OVERWRITE\n"
        sentinel.write_bytes(sentinel_bytes)
        completed = run_checker(SHARD, output=sentinel)
        if completed.returncode == 0 or sentinel.read_bytes() != sentinel_bytes:
            fail("exclusive output publication overwrote an existing path")
    if SHARD.read_bytes() != original:
        fail("r7 shard changed across mutation/mode checks")


def main() -> None:
    original = exact_snapshot_test()
    mode_and_mutation_test(original)
    print("2/2 independent fixed-polygon-v8 r7 result suites passed")


if __name__ == "__main__":
    main()
