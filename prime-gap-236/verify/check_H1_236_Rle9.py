#!/usr/bin/env python3
"""Standalone source-reconstructing replay of the k=48 R<=9 certificate.

This checker regenerates the exact inner forms, all thirteen outer-norm
strata, and the ten nonzero mixed strata from the rational vectors.  It
independently applies the total-large-count rule at common r=9 and compares
the result with a compact certificate only after reconstruction.  Serialized
matrix entries are never read.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import importlib.util
import json
import os
from fractions import Fraction as Q
from pathlib import Path
import re
import subprocess
import sys
import tempfile


if hasattr(sys, "set_int_max_str_digits"):
    sys.set_int_max_str_digits(0)

FILE = Path(__file__).resolve()
REPO = FILE.parents[1]
K = 48
A_COUNTS = tuple(range(13))
B_COUNTS = tuple(range(10))
KEPT_A_COUNTS = tuple(range(10))
ZEROED_A_COUNTS = (10, 11, 12)
R9_BRANCHES = ("Sdelta", "Stotal")
SCALE_F = 10**87
SCALE_H = 10**38
FORM_SCALE = SCALE_F**2
HEX64 = re.compile(r"[0-9a-f]{64}\Z")

BASE_CHECKER = REPO / "verify/check_H1_236.py"
BASE_CHECKER_SHA256 = \
    "99779b2954459f79caa24952ae977dc5d3504bea1be324fbbea7d4308fd04ee3"
ASSEMBLER = REPO / "verify/assemble_one_band_236_fixed_polygon_v8_r09.py"
ASSEMBLER_SHA256 = \
    "67c479a18b12f7e5d4df84a854dd8364f981ecdbcfd2daf2fd256edb2029b557"
ASSEMBLER_TEST = REPO / (
    "verify/test_assemble_one_band_236_fixed_polygon_v8_r09.py")
ASSEMBLER_TEST_SHA256 = \
    "6efe3b8a8db114e7d20834c922e514ec018c577029149598cdb5ce0b22f55a76"
DEFAULT_CERTIFICATE = REPO / "certificate/H1_236_one_band_Rle9_v1.json"


class VerificationError(RuntimeError):
    pass


def sha256(data_or_path) -> str:
    data = (data_or_path if isinstance(data_or_path, bytes)
            else Path(data_or_path).read_bytes())
    return hashlib.sha256(data).hexdigest()


def load_pinned(name, path, expected):
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


BASE = load_pinned(
    "H1_236_Rle9_pinned_full_replay_helpers",
    BASE_CHECKER, BASE_CHECKER_SHA256)
AGG = load_pinned(
    "H1_236_Rle9_pinned_v8_assembler",
    ASSEMBLER, ASSEMBLER_SHA256)

INNER_CANDIDATE = BASE.INNER_CANDIDATE
INNER_CHECKER = BASE.INNER_CHECKER
INNER_FROZEN = BASE.INNER_FROZEN
A_PRODUCER = BASE.A_PRODUCER
A_RADIAL_CHECKER = BASE.A_RADIAL_CHECKER
B_PRODUCER = AGG.V8_RUNNER
B_RESULT_CHECKER = AGG.V8_CHECKER
SUPPORT_CHECKER = BASE.SUPPORT_CHECKER
SUPPORT_FROZEN = BASE.SUPPORT_FROZEN
TUPLE_CHECKER = BASE.TUPLE_CHECKER
TUPLE_DATA = BASE.TUPLE_DATA

PINS = dict(BASE.PINS)
for obsolete in (BASE.B_PRODUCER, BASE.B_RESULT_CHECKER, BASE.ASSEMBLER):
    PINS.pop(obsolete, None)
for path, expected in AGG.PINS.items():
    previous = PINS.get(path)
    if previous is not None and previous != expected:
        raise RuntimeError(f"inconsistent R<=9 replay pin: {path}")
    PINS[path] = expected
PINS.update({
    BASE_CHECKER: BASE_CHECKER_SHA256,
    ASSEMBLER: ASSEMBLER_SHA256,
    ASSEMBLER_TEST: ASSEMBLER_TEST_SHA256,
})


def rational(value, label):
    if type(value) is not str:
        raise VerificationError(f"{label} is not a rational string")
    try:
        parsed = Q(value)
    except (ValueError, ZeroDivisionError) as exc:
        raise VerificationError(f"invalid rational {label}: {exc}") from exc
    if str(parsed) != value:
        raise VerificationError(f"noncanonical rational {label}")
    return parsed


def run_stage(name, arguments, timeout, stderr_validator=None):
    print(f"REPLAY {name}", file=sys.stderr, flush=True)
    try:
        completed = subprocess.run(
            list(arguments), cwd=REPO, env=os.environ.copy(),
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, timeout=timeout, check=False)
    except (OSError, subprocess.SubprocessError) as exc:
        raise VerificationError(f"{name} could not complete: {exc}") from exc
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout)[-4000:].decode(
            "utf-8", errors="replace")
        raise VerificationError(
            f"{name} exited {completed.returncode}: {detail}")
    if stderr_validator is not None:
        if not stderr_validator(completed.stderr):
            raise VerificationError(
                f"{name} emitted malformed progress stderr: " +
                completed.stderr[-4000:].decode("utf-8", errors="replace"))
    elif completed.stderr:
        raise VerificationError(
            f"{name} emitted stderr: " +
            completed.stderr[-4000:].decode("utf-8", errors="replace"))
    if len(completed.stdout) > 5_000_000:
        raise VerificationError(f"{name} stdout exceeds 5 MB")
    return completed.stdout


def run_count_jobs(name, counts, jobs, command_for_count, timeout,
                   stderr_validator_for_count=None):
    def one(count):
        validator = (None if stderr_validator_for_count is None else
                     stderr_validator_for_count(count))
        stdout = run_stage(
            f"{name} r={count}", command_for_count(count), timeout,
            stderr_validator=validator)
        return count, stdout

    results = {}
    with ThreadPoolExecutor(max_workers=jobs) as pool:
        futures = {pool.submit(one, count): count for count in counts}
        for future in as_completed(futures):
            count, stdout = future.result()
            results[count] = stdout
    if set(results) != set(counts):
        raise VerificationError(f"{name} count inventory is incomplete")
    return results


def canonical_bytes(data, label):
    value = BASE.strict_loads(data, label)
    encoded = (json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
        allow_nan=False) + "\n").encode("ascii")
    if encoded != data or type(value) is not dict:
        raise VerificationError(f"noncanonical JSON object: {label}")
    return value


def parse_a_rows(paths, snapshots):
    rows = []
    for count, path in zip(A_COUNTS, paths, strict=True):
        raw = canonical_bytes(snapshots[path], f"audited A[{count}]")
        if type(raw.get("count")) is not int or raw.get("count") != count:
            raise VerificationError(f"fresh A shard has wrong count {count}")
        values = raw.get("exact_values")
        if type(values) is not dict:
            raise VerificationError(f"fresh A shard lacks values {count}")
        rows.append(rational(values.get("band_I_count"), f"A[{count}]"))
    return rows


def parse_b_rows(paths, snapshots):
    selected, full, rules = [], [], []
    for count, path in zip(B_COUNTS, paths, strict=True):
        raw = canonical_bytes(snapshots[path], f"audited b[{count}]")
        if type(raw.get("common_r")) is not int or raw.get("common_r") != count:
            raise VerificationError(f"fresh b shard has wrong count {count}")
        full_value = rational(raw.get("scaled_b_shard"), f"b-full[{count}]")
        if count < 9:
            selected_value = full_value
            rule = "all-distinguished-branches"
        else:
            block = raw.get("branch_values_and_fast_stats")
            if type(block) is not dict:
                raise VerificationError("fresh r=9 branch block is malformed")
            high, low = block.get("high"), block.get("low")
            if type(high) is not dict or type(low) is not dict:
                raise VerificationError("fresh r=9 endpoint blocks are malformed")
            high_small = sum(
                (rational(high.get(name), f"b[9].high.{name}")
                 for name in R9_BRANCHES), Q(0))
            low_small = sum(
                (rational(low.get(name), f"b[9].low.{name}")
                 for name in R9_BRANCHES), Q(0))
            selected_value = K * (high_small - low_small)
            rule = "small-distinguished-only:Sdelta+Stotal"
        selected.append(selected_value)
        full.append(full_value)
        rules.append(rule)
    return selected, full, rules


def exact_scalar_reconstruction(inner, a_paths, b_paths, audited_shards):
    inner_i = rational(inner.get("exact_denominator"), "inner I")
    inner_48j = rational(inner.get("exact_numerator"), "inner 48J")
    inner_d = rational(inner.get("exact_deficit"), "inner deficit")
    if inner_i <= 0 or inner_d <= 0 or inner_i - inner_48j != inner_d:
        raise VerificationError("fresh inner exact forms are inconsistent")
    if set(audited_shards) != set(a_paths) | set(b_paths):
        raise VerificationError("audited shard byte inventory is incomplete")
    all_a = parse_a_rows(a_paths, audited_shards)
    selected_b, full_b, rules = parse_b_rows(b_paths, audited_shards)
    a_value = sum((all_a[count] for count in KEPT_A_COUNTS), Q(0))
    b_value = sum(selected_b, Q(0))
    i_value = inner_i * FORM_SCALE
    d_value = inner_d * FORM_SCALE
    margin = b_value**2 - a_value * d_value
    denominator = a_value * i_value + b_value**2
    if a_value <= 0 or i_value <= 0 or denominator <= 0:
        raise VerificationError("fresh R<=9 denominator is nonpositive")
    exact = {
        "A_scaled": a_value,
        "b_scaled": b_value,
        "I_F_scaled": i_value,
        "D_scaled": d_value,
        "margin_b_squared_minus_A_D": margin,
        "mixing_coefficient_b_over_A": b_value / a_value,
        "normalized_inner_deficit": d_value / i_value,
        "normalized_projected_energy": b_value**2 / (a_value * i_value),
        "quotient_margin_lower_bound": margin / denominator,
        "quotient_lower_bound": Q(1) + margin / denominator,
    }
    return {
        "exact": exact,
        "all_a": all_a,
        "selected_b": selected_b,
        "full_b": full_b,
        "rules": rules,
        "a_hashes": [sha256(audited_shards[path]) for path in a_paths],
        "b_hashes": [sha256(audited_shards[path]) for path in b_paths],
    }


def expected_outer_direction():
    return {
        "definition": "H=1_{total-large-count<=9}*H_full",
        "symmetric": True,
        "single_outer_band": True,
        "nonzero_total_large_counts": list(KEPT_A_COUNTS),
        "zeroed_total_large_counts": list(ZEROED_A_COUNTS),
        "mixed_common_counts": list(B_COUNTS),
        "common_r_9_branches": list(R9_BRANCHES),
        "common_r_0_through_8_branches": "all",
    }


def check_row_list(owner, rows, counts, values, hashes, fields,
                   full_values=None, rules=None, bind_hashes=False):
    if type(rows) is not list or len(rows) != len(counts):
        raise VerificationError(f"{owner} shard inventory is incomplete")
    if any(type(row) is not dict or set(row) != fields for row in rows):
        raise VerificationError(f"{owner} shard row schema differs")
    if any(type(row.get("count")) is not int for row in rows):
        raise VerificationError(f"{owner} shard count is not an integer")
    by_count = {row["count"]: row for row in rows}
    if set(by_count) != set(counts) or len(by_count) != len(rows):
        raise VerificationError(f"{owner} shard counts differ")
    for index, count in enumerate(counts):
        row = by_count[count]
        if row["value"] != str(values[index]):
            raise VerificationError(f"{owner} value differs at count {count}")
        digest = row.get("sha256")
        if type(digest) is not str or HEX64.fullmatch(digest) is None:
            raise VerificationError(f"{owner} hash malformed at count {count}")
        if bind_hashes and digest != hashes[index]:
            raise VerificationError(f"{owner} hash differs at count {count}")
        if full_values is not None and \
                row.get("full_shard_value") != str(full_values[index]):
            raise VerificationError(
                f"{owner} full value differs at count {count}")
        if rules is not None and row.get("selection") != rules[index]:
            raise VerificationError(
                f"{owner} selection rule differs at count {count}")


def compare_certificate(certificate, aggregate, reconstructed):
    top = {
        "format", "status", "rigorous", "theorem_ready_scalar", "k",
        "outer_direction", "scales", "exact", "a_shards",
        "zeroed_a_shards", "b_shards", "trust_scope", "assembler_sha256",
        "rle9_base_assembler_sha256", "full_assembler_sha256", "b_engine",
        "source_hashes",
    }
    if (type(certificate) is not dict or set(certificate) != top or
            type(aggregate) is not dict or set(aggregate) != top):
        raise VerificationError("compact/fresh R<=9 aggregate schema differs")
    stable = top - {"exact", "a_shards", "zeroed_a_shards", "b_shards"}
    if any(certificate.get(key) != aggregate.get(key) for key in stable):
        raise VerificationError("fresh R<=9 stable metadata differs")
    if (certificate.get("format") !=
            "H1-236-one-band-fixed-polygon-v8-Rle9-exact-aggregate-v1" or
            certificate.get("status") !=
                "EXACT R<=9 ONE-BAND SCALAR CERTIFICATE PASS" or
            certificate.get("rigorous") is not True or
            certificate.get("theorem_ready_scalar") is not True or
            type(certificate.get("k")) is not int or
            certificate.get("k") != K or
            certificate.get("outer_direction") != expected_outer_direction() or
            certificate.get("scales") != {
                "F": str(SCALE_F), "H": str(SCALE_H),
                "quadratic_inner": str(FORM_SCALE)} or
            certificate.get("assembler_sha256") != ASSEMBLER_SHA256 or
            certificate.get("rle9_base_assembler_sha256") !=
                AGG.R09_ASSEMBLER_SHA256 or
            certificate.get("full_assembler_sha256") !=
                AGG.R09.FULL_ASSEMBLER_SHA256 or
            certificate.get("b_engine") !=
                "fixed-polygon-v8-with-Rle9-branch-projection"):
        raise VerificationError("compact certificate is not an armed k=48 pass")
    exact = reconstructed["exact"]
    for owner, record in (("certificate", certificate),
                          ("fresh aggregate", aggregate)):
        if type(record.get("exact")) is not dict or \
                set(record["exact"]) != set(exact):
            raise VerificationError(f"{owner} exact scalar schema differs")
        for key, value in exact.items():
            if record["exact"].get(key) != str(value):
                raise VerificationError(f"{owner} exact field differs: {key}")

    all_a = reconstructed["all_a"]
    kept_a = [all_a[count] for count in KEPT_A_COUNTS]
    zeroed_a = [all_a[count] for count in ZEROED_A_COUNTS]
    kept_a_hashes = [reconstructed["a_hashes"][count]
                     for count in KEPT_A_COUNTS]
    zeroed_a_hashes = [reconstructed["a_hashes"][count]
                       for count in ZEROED_A_COUNTS]
    a_fields = {"count", "value", "sha256"}
    b_fields = {
        "count", "value", "full_shard_value", "selection", "sha256"}
    for owner, record, bind in (
            ("certificate A", certificate, False),
            ("fresh aggregate A", aggregate, True)):
        check_row_list(owner, record.get("a_shards"), KEPT_A_COUNTS,
                       kept_a, kept_a_hashes, a_fields, bind_hashes=bind)
        check_row_list(owner + " zeroed", record.get("zeroed_a_shards"),
                       ZEROED_A_COUNTS, zeroed_a, zeroed_a_hashes, a_fields,
                       bind_hashes=bind)
        check_row_list(owner.replace(" A", " b"), record.get("b_shards"),
                       B_COUNTS, reconstructed["selected_b"],
                       reconstructed["b_hashes"], b_fields,
                       full_values=reconstructed["full_b"],
                       rules=reconstructed["rules"], bind_hashes=bind)
    if exact["margin_b_squared_minus_A_D"] <= 0:
        raise VerificationError("exact reconstructed b^2-A*D is not positive")
    if exact["quotient_lower_bound"] <= 1:
        raise VerificationError("exact reconstructed quotient is not above one")


def validate_b_progress(data, count):
    escaped = str(count).encode("ascii")
    patterns = (
        rb"fast-v2 kernel r=" + escaped +
            rb" \{[^\r\n]*\} seconds=[0-9]+\.[0-9]{3}",
        rb"fast-v2 families r=" + escaped +
            rb" \{[^\r\n]*\} seconds=[0-9]+\.[0-9]{3}",
        rb"fast-v2 done r=" + escaped +
            rb" seconds=[0-9]+\.[0-9]{3}",
    )
    lines = data.splitlines()
    return len(lines) == 3 and all(
        re.fullmatch(pattern, line) is not None
        for pattern, line in zip(patterns, lines, strict=True))


def verify(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--certificate", type=Path, default=DEFAULT_CERTIFICATE)
    parser.add_argument("--expected-certificate-sha256", required=True)
    parser.add_argument("--expected-self-sha256", required=True)
    parser.add_argument("--jobs", type=int, choices=(1, 2), default=1)
    args = parser.parse_args(argv)
    for label, value in (("certificate", args.expected_certificate_sha256),
                         ("checker", args.expected_self_sha256)):
        if type(value) is not str or HEX64.fullmatch(value) is None:
            raise VerificationError(
                f"expected {label} SHA-256 is not lowercase hex")
    self_data = FILE.read_bytes()
    if sha256(self_data) != args.expected_self_sha256:
        raise VerificationError("R<=9 standalone checker self hash mismatch")
    snapshots = {path: path.read_bytes() for path in PINS}
    for path, expected in PINS.items():
        if sha256(snapshots[path]) != expected:
            raise VerificationError(f"pinned replay dependency changed: {path}")
    certificate, certificate_data = BASE.canonical_object(
        args.certificate.resolve())
    if sha256(certificate_data) != args.expected_certificate_sha256:
        raise VerificationError("compact certificate SHA-256 mismatch")

    with tempfile.TemporaryDirectory(prefix="H1-236-Rle9-replay-") as root:
        work = Path(root)
        child_python = BASE.python_prefix(work / "empty-private-pycache")

        support_output = work / "support.json"
        run_stage("analytic support", child_python + [
            str(SUPPORT_CHECKER), "--output", str(support_output)], 900)
        support, _ = BASE.canonical_object(support_output)
        frozen_support, _ = BASE.canonical_object(SUPPORT_FROZEN)
        fresh_portable = BASE.deterministic_support_projection(
            support, "fresh", snapshots)
        frozen_portable = BASE.deterministic_support_projection(
            frozen_support, "frozen", snapshots)
        if fresh_portable != frozen_portable:
            raise VerificationError("fresh analytic-support result differs")

        tuple_stdout = run_stage(
            "admissible tuple", child_python + [str(TUPLE_CHECKER)], 60)
        tuple_result = BASE.strict_loads(tuple_stdout, "tuple checker stdout")
        if (type(tuple_result) is not dict or
                tuple_result.get("tuple_verified") is not True or
                tuple_result.get("sha256") != PINS[TUPLE_DATA] or
                tuple_result.get("size") != 48 or
                tuple_result.get("minimum") != 0 or
                tuple_result.get("maximum") != 236 or
                tuple_result.get("diameter") != 236):
            raise VerificationError("fresh admissible-tuple verification failed")

        inner_output = work / "inner.json"
        run_stage("inner I and 48J", child_python + [
            str(INNER_CHECKER), str(INNER_CANDIDATE),
            "--expected-candidate-sha", PINS[INNER_CANDIDATE],
            "--basis-degree", "19", "--output", str(inner_output)], 7200)
        inner, inner_data = BASE.canonical_object(inner_output)
        if inner_data != snapshots[INNER_FROZEN]:
            raise VerificationError("fresh inner reconstruction differs bit-for-bit")

        a_dir, b_dir = work / "A", work / "b"
        a_dir.mkdir()
        b_dir.mkdir()
        a_paths = [a_dir / f"r{count:02d}.json" for count in A_COUNTS]
        b_paths = [b_dir / f"common_r_{count:02d}.json" for count in B_COUNTS]
        run_count_jobs(
            "outer norm A", A_COUNTS, args.jobs,
            lambda count: child_python + [
                str(A_PRODUCER), "--count", str(count),
                "--output", str(a_paths[count])], 3600)
        a_radial_output = work / "A-radial-audit.json"
        run_stage("independent outer-norm radial replay", child_python + [
            str(A_RADIAL_CHECKER), *map(str, a_paths),
            "--output", str(a_radial_output),
            "--expected-self-sha256", PINS[A_RADIAL_CHECKER]], 14_400)
        a_radial, _ = BASE.canonical_object(a_radial_output)
        if (a_radial.get("status") !=
                "INDEPENDENT EXACT RADIAL A-v2 SHARD CHECK PASS" or
                a_radial.get("checked_counts") != list(A_COUNTS)):
            raise VerificationError("independent A replay did not pass")
        radial_rows = a_radial.get("rows")
        if type(radial_rows) is not list or len(radial_rows) != len(A_COUNTS):
            raise VerificationError("independent A row inventory is incomplete")
        radial_by_count = {
            row.get("count"): row for row in radial_rows if type(row) is dict}
        if set(radial_by_count) != set(A_COUNTS):
            raise VerificationError("independent A count inventory differs")
        bound_shards = {}
        for count, path in enumerate(a_paths):
            data = path.read_bytes()
            if radial_by_count[count].get("shard_sha256") != sha256(data):
                raise VerificationError(
                    f"A shard r={count} differs from audited bytes")
            bound_shards[path] = data

        run_count_jobs(
            "mixed Definition-5 b", B_COUNTS, args.jobs,
            lambda count: child_python + [
                str(B_PRODUCER), "--common-r", str(count),
                "--output", str(b_paths[count]),
                "--expected-self-sha256", PINS[B_PRODUCER]], 14_400,
            stderr_validator_for_count=lambda count: (
                lambda data: validate_b_progress(data, count)))
        for count, path in enumerate(b_paths):
            stdout = run_stage(
                f"independent b result audit r={count}", child_python + [
                    str(B_RESULT_CHECKER), "--expected-self-sha256",
                    PINS[B_RESULT_CHECKER], str(path)], 600)
            audited = BASE.strict_loads(stdout, f"b audit stdout r={count}")
            if (type(audited) is not dict or
                    audited.get("status") !=
                        "FIXED-POLYGON-V8 CROSS SHARD STRUCTURAL/RESULT AUDIT PASS" or
                    audited.get("common_r") != count or
                    audited.get("recombined_exactly") is not True or
                    audited.get("fixed_polygon_denominator_proof_pinned") is not True):
                raise VerificationError(f"independent b audit failed at r={count}")
            data = path.read_bytes()
            if audited.get("input_sha256") != sha256(data):
                raise VerificationError(
                    f"b shard r={count} differs from audited bytes")
            bound_shards[path] = data

        if any(path.read_bytes() != data for path, data in bound_shards.items()):
            raise VerificationError("an audited shard changed before aggregation")
        aggregate_output = work / "aggregate.json"
        run_stage("exact R<=9 scalar aggregation", child_python + [
            str(ASSEMBLER), "--a-dir", str(a_dir), "--b-dir", str(b_dir),
            "--output", str(aggregate_output),
            "--expected-self-sha256", PINS[ASSEMBLER]], 600)
        aggregate, _ = BASE.canonical_object(aggregate_output)
        reconstructed = exact_scalar_reconstruction(
            inner, a_paths, b_paths, bound_shards)
        if any(path.read_bytes() != data for path, data in bound_shards.items()):
            raise VerificationError("an audited shard changed during aggregation")
        if a_radial.get("sum_scaled_band_I") != \
                str(sum(reconstructed["all_a"], Q(0))):
            raise VerificationError("independent full A aggregate differs")
        compare_certificate(certificate, aggregate, reconstructed)

    if (FILE.read_bytes() != self_data or
            any(path.read_bytes() != data for path, data in snapshots.items()) or
            args.certificate.resolve().read_bytes() != certificate_data):
        raise VerificationError("checker/certificate/source closure changed")
    exact = reconstructed["exact"]
    result = {
        "status": (
            "AUDIT PASS: exact k=48 R<=9 quotient > 1; "
            "admissible diameter-236 tuple verified"),
        "theorem": "H_1 <= 236",
        "certificate_sha256": args.expected_certificate_sha256,
        "checker_sha256": args.expected_self_sha256,
        "k": K,
        "exact_margin_b_squared_minus_A_D":
            str(exact["margin_b_squared_minus_A_D"]),
        "exact_quotient_lower_bound": str(exact["quotient_lower_bound"]),
        "all_integrals_reconstructed": True,
        "serialized_matrix_entries_read": False,
        "tuple_verified": True,
    }
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


def main(argv=None):
    try:
        return verify(argv)
    except (VerificationError, OSError, ValueError) as exc:
        print(json.dumps({"verified": False, "error": str(exc)}, sort_keys=True),
              file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
