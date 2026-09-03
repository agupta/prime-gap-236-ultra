#!/usr/bin/env python3
"""Independent cross-engine result audit for Green-v9 common r=9."""

from __future__ import annotations

from fractions import Fraction
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
GREEN = (REPO / "agents/exact-projection-engine/results/"
         "d14_grid38_scaled_b_green_v9_crosscheck_r9/common_r_09.json")
V8 = (REPO / "agents/exact-projection-engine/results/"
      "d14_grid38_scaled_b_fixed_polygon_v8/common_r_09.json")
CHECKER = HERE / "verify_green_v9_cross_shard.py"
NORMAL = (HERE / "results/d14_grid38_scaled_b_green_v9_crosscheck_r9/"
          "common_r_09.normal.audit.json")
OPTIMIZED = (HERE / "results/d14_grid38_scaled_b_green_v9_crosscheck_r9/"
             "common_r_09.optimized.audit.json")
GREEN_SHA = "b6cb9eb5ccbb5d9ef73fc6637481efb5bf020846316487357a097272aaf56853"
V8_SHA = "e9397f72f78f9ad53716d61bb3f10854a640081f81632028904836d6c6778d88"
CHECKER_SHA = "7dbb352011d840a5bddf8f6f101f864d0a1b1e436ff4ebb5533ef1137217b4a7"
AUDIT_SHA = "45705683105f637d49b27f3e95332cdc6f94331ed99d1dddec3c03c0528c7c62"
PRODUCER_SHA = "ad38951dadecdb5a5c51d1221b0a078bc9f804e9c4ec8d434706fca55a11935a"
CORE_SHA = "019fecc00727bfdeb62fc3a02277298c6d08543db4d71ce47f049a73bc1d7a0c"
BRANCHES = {"Lbig", "Ltotal", "Sdelta", "Stotal"}
EXACT_TOP_FIELDS = {
    "scaled_b_shard", "kernel_stats", "family_stats", "geometry",
    "candidate", "scaling",
}
EXACT_BLOCK_FIELDS = {
    "high", "low", "high_stats", "low_stats", "integer_radialization",
}
RATIONAL = re.compile(r"-?(?:0|[1-9][0-9]*)(?:/[1-9][0-9]*)?\Z")
HEX64 = re.compile(r"[0-9a-f]{64}\Z")


def fail(message):
    raise RuntimeError(message)


def digest(value):
    data = value if isinstance(value, bytes) else Path(value).read_bytes()
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"),
                       ensure_ascii=True, allow_nan=False) + "\n").encode("ascii")


def parse(data):
    def reject(token):
        fail(f"nonfinite JSON token {token}")
    return json.loads(data, parse_constant=reject)


def rational(value, label):
    if type(value) is not str or RATIONAL.fullmatch(value) is None:
        fail(f"noncanonical rational syntax: {label}")
    answer = Fraction(value)
    if str(answer) != value:
        fail(f"unreduced rational: {label}")
    return answer


def run_checker(green, reference, optimized=False, output=None):
    with tempfile.TemporaryDirectory(prefix="green-r9-private-cache-") as text:
        prefix = Path(text) / "absent-private-pycache"
        command = [sys.executable]
        if optimized:
            command.append("-O")
        command.extend([
            "-B", "-I", "-X", f"pycache_prefix={prefix}", str(CHECKER),
            "--expected-self-sha256", CHECKER_SHA,
            "--reference", str(reference),
        ])
        if output is not None:
            command.extend(["--output", str(output)])
        command.append(str(green))
        result = subprocess.run(command, cwd=REPO, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, check=False)
        if prefix.exists():
            fail("private bytecode path was unexpectedly created")
        return result


def independent_exact_crosscheck():
    green_bytes = GREEN.read_bytes()
    v8_bytes = V8.read_bytes()
    if digest(green_bytes) != GREEN_SHA or digest(v8_bytes) != V8_SHA:
        fail("target or reference byte pin mismatch")
    green = parse(green_bytes)
    v8 = parse(v8_bytes)
    if canonical(green) != green_bytes or canonical(v8) != v8_bytes:
        fail("target or reference is not canonical JSON")
    if (type(green.get("common_r")) is not int or green["common_r"] != 9 or
            type(green["geometry"].get("k")) is not int or
            green["geometry"]["k"] != 48 or
            green.get("producer_sha256") != PRODUCER_SHA or
            green.get("rigorous") is not True or
            green.get("serialized_matrices_read") is not False):
        fail("Green r9 identity/count contract mismatch")
    for field in EXACT_TOP_FIELDS:
        if green[field] != v8[field]:
            fail(f"Green/v8 exact top field mismatch: {field}")
    gb = green["branch_values_and_fast_stats"]
    vb = v8["branch_values_and_fast_stats"]
    for field in EXACT_BLOCK_FIELDS:
        if gb[field] != vb[field]:
            fail(f"Green/v8 exact branch field mismatch: {field}")
    if set(gb["high"]) != BRANCHES or set(gb["low"]) != BRANCHES:
        fail("Green r9 branch inventory mismatch")
    high = [rational(value, f"high.{name}")
            for name, value in gb["high"].items()]
    low = [rational(value, f"low.{name}")
           for name, value in gb["low"].items()]
    observed = rational(green["scaled_b_shard"], "scaled_b_shard")
    if observed != 48 * (sum(high, Fraction(0)) - sum(low, Fraction(0))):
        fail("independent Green r9 factor-48 recombination failed")
    if observed != rational(v8["scaled_b_shard"], "v8.scaled_b_shard") or observed <= 0:
        fail("Green and v8 exact scalar values differ or are nonpositive")
    if (observed.numerator.bit_length(), observed.denominator.bit_length()) != (2338, 2458):
        fail("Green r9 exact result bit lengths changed")
    for side in ("high_stats", "low_stats"):
        if set(gb[side]) != BRANCHES:
            fail(f"Green r9 {side} inventory mismatch")
        for name, row in gb[side].items():
            if row["active_shifts"] != 6:
                fail(f"Green r9 {side}.{name} does not use shifts 0..5")
            if any(type(value) is not int or value < 0 for value in row.values()):
                fail(f"Green r9 {side}.{name} has noninteger work metadata")
    scalar_products = sum(row["scalar_products"]
                          for side in ("high_stats", "low_stats")
                          for row in gb[side].values())
    monomials = sum(row["nonzero_product_monomials"]
                    for side in ("high_stats", "low_stats")
                    for row in gb[side].values())
    if scalar_products != 233384424 or monomials != 31524:
        fail("Green r9 independent work totals changed")
    if gb["integer_radialization"]["radial_stats"][
            "maximum_shift_pruned_inside_convolution"] != 5:
        fail("Green r9 maximum active shift is not H=14-r=5")
    if gb["integer_radialization"]["active_branch_families"] != \
            ["large", "small", "small_total"]:
        fail("Green r9 family inventory changed")

    sources = green["source_hashes"]
    if type(sources) is not dict or len(sources) != 30:
        fail("Green r9 source-map cardinality mismatch")
    if sources.get("agents/exact-projection-engine/green_polygon_moments.py") != CORE_SHA:
        fail("Green core source is not pinned")
    root = REPO.resolve()
    for relative, expected in sources.items():
        if type(expected) is not str or HEX64.fullmatch(expected) is None:
            fail("malformed Green source SHA")
        path = (REPO / relative).resolve()
        try:
            path.relative_to(root)
        except ValueError:
            fail("Green source pin escapes repository")
        if digest(path) != expected:
            fail(f"live Green source mismatch: {relative}")
    if digest(CHECKER) != CHECKER_SHA:
        fail("Green result checker changed")
    if GREEN.read_bytes() != green_bytes or V8.read_bytes() != v8_bytes:
        fail("target/reference bytes changed during independent arithmetic")
    return green_bytes, v8_bytes


def mode_mutation_and_binding(green_bytes, v8_bytes):
    normal = run_checker(GREEN, V8)
    optimized = run_checker(GREEN, V8, optimized=True)
    for label, result in (("normal", normal), ("optimized", optimized)):
        if result.returncode != 0 or result.stderr:
            fail(f"{label} Green checker failed: {result.stderr.decode('utf-8', 'replace')}")
        if digest(result.stdout) != AUDIT_SHA:
            fail(f"{label} Green checker output hash mismatch")
    if normal.stdout != optimized.stdout:
        fail("normal/optimized Green audit outputs differ")
    if NORMAL.read_bytes() != normal.stdout or OPTIMIZED.read_bytes() != normal.stdout:
        fail("preserved Green audit outputs differ from fresh output")
    audit = parse(normal.stdout)
    if (audit["input_sha256"] != GREEN_SHA or
            audit["reference_sha256"] != V8_SHA or
            audit["reference_exact_fields_bit_equal"] is not True or
            audit["recombined_exactly"] is not True):
        fail("Green checker output is not bound to both exact snapshots")

    green = parse(green_bytes)
    v8 = parse(v8_bytes)
    mutants = []
    mutant = json.loads(json.dumps(green))
    mutant["scaled_b_shard"] = str(rational(mutant["scaled_b_shard"], "q") + 1)
    mutants.append((mutant, v8, "changed scalar"))
    mutant = json.loads(json.dumps(green))
    mutant["branch_values_and_fast_stats"]["high"]["Sdelta"] = "0"
    mutants.append((mutant, v8, "changed branch"))
    mutant = json.loads(json.dumps(green))
    mutant["algorithm"]["polygon_convex_cyclic_order_checked"] = False
    mutants.append((mutant, v8, "changed Green contract"))
    mutant = json.loads(json.dumps(green))
    mutant["source_hashes"]["agents/exact-projection-engine/green_polygon_moments.py"] = "0" * 64
    mutants.append((mutant, v8, "changed source pin"))
    reference = json.loads(json.dumps(v8))
    reference["branch_values_and_fast_stats"]["low"]["Stotal"] = "0"
    mutants.append((green, reference, "changed exact reference"))

    with tempfile.TemporaryDirectory(prefix="green-r9-mutants-") as text:
        root = Path(text)
        for index, (target, reference, label) in enumerate(mutants):
            target_path = root / f"target-{index}.json"
            reference_path = root / f"reference-{index}.json"
            target_path.write_bytes(canonical(target))
            reference_path.write_bytes(canonical(reference))
            result = run_checker(target_path, reference_path)
            if result.returncode == 0:
                fail(f"Green checker accepted {label}")
        sentinel = root / "sentinel.json"
        sentinel_bytes = b"do-not-overwrite\n"
        sentinel.write_bytes(sentinel_bytes)
        result = run_checker(GREEN, V8, output=sentinel)
        if result.returncode == 0 or sentinel.read_bytes() != sentinel_bytes:
            fail("Green checker overwrote an existing output")
    if GREEN.read_bytes() != green_bytes or V8.read_bytes() != v8_bytes:
        fail("target/reference path changed across mode/mutation audit")


def main():
    snapshots = independent_exact_crosscheck()
    mode_mutation_and_binding(*snapshots)
    print("2/2 independent Green-v9 r9 result suites passed")


if __name__ == "__main__":
    main()
