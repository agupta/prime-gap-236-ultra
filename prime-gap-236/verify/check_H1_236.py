#!/usr/bin/env python3
"""Standalone source-reconstructing replay of the exact one-band k=48 certificate.

The default path is deliberately expensive: it regenerates the inner forms,
all thirteen outer norms, and all thirteen mixed Definition-5 shards from the
finite rational vectors.  Serialized matrix entries and serialized scalar
shards are never inputs.  A compact aggregate is used only as an expected
answer and is accepted only after exact reconstruction.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from fractions import Fraction as Q
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile


if hasattr(sys, "set_int_max_str_digits"):
    sys.set_int_max_str_digits(0)

FILE = Path(__file__).resolve()
REPO = FILE.parents[1]
COUNTS = tuple(range(13))
K = 48
SCALE_F = 10**87
SCALE_H = 10**38
FORM_SCALE = SCALE_F**2
HEX64 = re.compile(r"[0-9a-f]{64}\Z")

INNER_CANDIDATE = REPO / (
    "agents/structural-basis/results/"
    "bv_D19_krylov20_cacheconditional_v1.json")
INNER_CHECKER = REPO / "verify/check_bv_rational_vector_direct_v2.py"
INNER_FROZEN = REPO / (
    "verify/results/bv_D19_krylov20_direct_exact_v2_strict.json")
A_PRODUCER = REPO / (
    "agents/structural-basis/code/exact_d14_one_band_a_shard_v2.py")
A_RADIAL_CHECKER = REPO / (
    "agents/audit/verify_d14_one_band_a_v2_radial.py")
B_PRODUCER = REPO / (
    "agents/exact-projection-engine/"
    "d14_grid38_scaled_b_shard_cached_v7.py")
B_RESULT_CHECKER = REPO / "agents/audit/verify_cached_v7_cross_shard.py"
ASSEMBLER = REPO / "verify/assemble_one_band_236_cached_v7.py"
SUPPORT_CHECKER = REPO / (
    "agents/audit/verify_truncated_lower_energy_v3_hostile_audit.py")
SUPPORT_FROZEN = REPO / (
    "agents/audit/results/truncated_lower_energy_v3_hostile_audit.json")
TUPLE_CHECKER = REPO / "verify/independent_tuple_verifier.py"
TUPLE_DATA = REPO / "sources/admissible_48_236.txt"
DEFAULT_CERTIFICATE = REPO / "certificate/H1_236_one_band_v1.json"

PINS = {
    INNER_CANDIDATE:
        "986563579cb7fa8653f774100e9fd1cc966761261eef53052b8be8e61f96d276",
    INNER_CHECKER:
        "ff2046ce180394a6328fdec2c112d575a4c540ff964f5dede28c6db6091506c5",
    INNER_FROZEN:
        "8b0d47b22b09c057633022682332f0de4b7e47d4b6ab6d630690be081c58e170",
    A_PRODUCER:
        "2e91dbd8bcb8d0bfd102f964236d3a7d60d974bfecedab96a4a19a1124e81c2d",
    A_RADIAL_CHECKER:
        "e51a8719b4665dc2e38c454f467abfc8b894410d53b3882dd931c7ed82e37666",
    B_PRODUCER:
        "b427c6961c377cb79d5a72b54f8c2e8c7642b87d66d338f53b5dc56d98991984",
    B_RESULT_CHECKER:
        "80ec3329215f66e784708039f9a1d673d7064769c48a31825961dc44f6ae7343",
    ASSEMBLER:
        "08fb7e612f37050a21bc94d27e4b8ed0ad1838f64ce5e2a147d15aef9f076f05",
    SUPPORT_CHECKER:
        "b4e889ab47690fb8619342267e4259dab5b31882ef5a25b9015957d4e210394b",
    SUPPORT_FROZEN:
        "fea750c78b8bc7a022d8ee7d407a59405f4f790b1729305f47b21f8d4f2117a1",
    TUPLE_CHECKER:
        "645d3e61f587f9f961b3c72037a0f4499ac29c85c64be601b6b14e6a4b898f78",
    TUPLE_DATA:
        "adfe71549293c2ff0efda34397e46c72269b2895ae23fc2fdfc34ccacc579ba9",
}
BASE_ASSEMBLER_SHA256 = \
    "91ab96385d32921c035bd5537a56e8254455a8033bf41e2298b7ec13be552bbc"
SUPPORT_SNAPSHOT_PINS = {
    "agents/analytic-new-lever/verify_truncated_lower_energy_v3.py":
        "fff280573fa1bf539fe8fcba72270aa088c6d35255f39da24d7fb77fce5a75d5",
    "agents/analytic-new-lever/truncated_lower_energy_v3_exact.json":
        "c9be4426ece4cc50063ee64ccae72d26c66af5296d7312b2fb9ac0192ba30c9f",
    "agents/analytic-new-lever/verify_three_outer_energy_v2.py":
        "87747ad848c502e4d0047d60ca324d77ba94c9b0f5cb2afd6b5d46b953575605",
    "agents/analytic-new-lever/verify_two_outer_band_v1.py":
        "187a87f6c29532645100d9a91b94ce8038c38511dfff22326efe9722ea0f8001",
    "agents/analytic-new-lever/verify_adaptive_support_v1.py":
        "b8abaa8fec6f992c1071b4e550e666946444ff7c559b850960dc633836ce2c6d",
    "agents/audit/verify_adaptive_support_v1_hostile_audit.py":
        "0a6b6dbc6ab2cc1a1ec85e0e1a62e19cd6df498e97e68c8c0d5a6bd2202ed918",
    "agents/audit/results/adaptive_support_v1_hostile_audit.json":
        "eabffdc8927a50cb95fb1f8b707dd9b5c76b53778022ea039e160fb9cd2908d5",
    "sources/stadlmann-2608.31126-src/Bounded_Gaps_2.0.tex":
        "c0d5d2317c77f4de7eacdef6e1d4b1eb6433e6240b5c09273b3d4eee99e6c3ba",
    "sources/stadlmann-2309.00425-src/Primes_in_arithmetic_progressions.tex":
        "60c0440f33d9cbf504470716491fb4d45b45b26d9a960c8e34ff2af500837a30",
    "sources/polymath8-edz-1402.0811-src/newergap.tex":
        "fdffe1dfb7b820d8a45ecc0e07e2f7e17404e6e10b63db110c2d44afe42013ea",
}
for relative, expected in SUPPORT_SNAPSHOT_PINS.items():
    path = REPO / relative
    if path in PINS and PINS[path] != expected:
        raise RuntimeError(f"inconsistent support replay pin: {relative}")
    PINS[path] = expected


class VerificationError(RuntimeError):
    pass


def sha256(data: bytes | Path) -> str:
    raw = data if isinstance(data, bytes) else data.read_bytes()
    return hashlib.sha256(raw).hexdigest()


def strict_loads(data: bytes, label: str):
    def pairs(items):
        answer = {}
        for key, value in items:
            if key in answer:
                raise VerificationError(f"duplicate JSON key {key!r} in {label}")
            answer[key] = value
        return answer

    try:
        return json.loads(
            data, object_pairs_hook=pairs,
            parse_constant=lambda token: (_ for _ in ()).throw(
                VerificationError(f"nonfinite token {token!r} in {label}")))
    except (json.JSONDecodeError, UnicodeError, ValueError) as exc:
        if isinstance(exc, VerificationError):
            raise
        raise VerificationError(f"invalid JSON in {label}: {exc}") from exc


def canonical_object(path: Path):
    data = path.read_bytes()
    value = strict_loads(data, str(path))
    encoded = (json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
        allow_nan=False) + "\n").encode("ascii")
    if encoded != data:
        raise VerificationError(f"noncanonical JSON: {path}")
    if type(value) is not dict:
        raise VerificationError(f"top-level JSON is not an object: {path}")
    return value, data


def deterministic_support_projection(result, label: str, source_bytes):
    """Strip only host-specific identity numbers after validating them.

    The support checker uses device/inode pairs to detect mutation during its
    own run.  Those numbers are deliberately not reproducible across an
    independent checkout; every mathematical field and every byte hash/size
    remains exact and portable.
    """
    expected_top = {
        "checker_sha256", "continuum_completion", "independent_reconstruction",
        "producer_comparison", "proposition_interface_reused_and_rechecked",
        "retained_and_deleted_bands", "scope", "snapshots", "status",
        "strict_common_cap_translation",
    }
    if type(result) is not dict or set(result) != expected_top:
        raise VerificationError(f"{label} support-result schema differs")
    rows = result.get("snapshots")
    if type(rows) is not dict or set(rows) != set(SUPPORT_SNAPSHOT_PINS):
        raise VerificationError(f"{label} support snapshot inventory differs")
    portable = dict(result)
    portable_rows = {}
    for relative, expected_sha in SUPPORT_SNAPSHOT_PINS.items():
        row = rows[relative]
        if type(row) is not dict or set(row) != {
                "sha256", "size", "dev", "inode", "nlink"}:
            raise VerificationError(
                f"{label} support snapshot schema differs: {relative}")
        if (type(row["sha256"]) is not str or
                HEX64.fullmatch(row["sha256"]) is None or
                type(row["size"]) is not int or row["size"] < 0 or
                type(row["dev"]) is not int or row["dev"] < 0 or
                type(row["inode"]) is not int or row["inode"] <= 0 or
                type(row["nlink"]) is not int or row["nlink"] != 1):
            raise VerificationError(
                f"{label} support snapshot metadata malformed: {relative}")
        data = source_bytes[REPO / relative]
        if row["sha256"] != expected_sha or sha256(data) != expected_sha or \
                row["size"] != len(data):
            raise VerificationError(
                f"{label} support snapshot bytes differ: {relative}")
        portable_rows[relative] = {
            "sha256": row["sha256"], "size": row["size"], "nlink": 1}
    portable["snapshots"] = portable_rows
    return portable


def rational(value, label: str) -> Q:
    if type(value) is not str:
        raise VerificationError(f"{label} is not a rational string")
    try:
        parsed = Q(value)
    except (ValueError, ZeroDivisionError) as exc:
        raise VerificationError(f"invalid rational {label}: {exc}") from exc
    if str(parsed) != value:
        raise VerificationError(f"noncanonical rational {label}")
    return parsed


def python_prefix(pycache_prefix: Path):
    """Isolated child interpreter with no readable or writable repo cache."""
    pycache_prefix = pycache_prefix.resolve()
    return ([sys.executable, "-B"] +
            (["-O"] if sys.flags.optimize else []) +
            ["-I", "-X", f"pycache_prefix={pycache_prefix}"])


def run_stage(name: str, arguments, timeout: int, stderr_validator=None):
    environment = os.environ.copy()
    print(f"REPLAY {name}", file=sys.stderr, flush=True)
    try:
        completed = subprocess.run(
            list(arguments), cwd=REPO, env=environment,
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


def validate_b_progress(data: bytes, count: int) -> bool:
    """Accept only the three deterministic progress-line shapes of v7."""
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
    return len(lines) == len(patterns) and all(
        re.fullmatch(pattern, line) is not None
        for pattern, line in zip(patterns, lines, strict=True))


def run_count_jobs(name, jobs, command_for_count, timeout,
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
        futures = {pool.submit(one, count): count for count in COUNTS}
        for future in as_completed(futures):
            count, stdout = future.result()
            results[count] = stdout
    if set(results) != set(COUNTS):
        raise VerificationError(f"{name} did not complete exactly r=0..12")
    return results


def exact_scalar_reconstruction(inner, a_paths, b_paths):
    inner_i = rational(inner.get("exact_denominator"), "inner I")
    inner_48j = rational(inner.get("exact_numerator"), "inner 48J")
    inner_d = rational(inner.get("exact_deficit"), "inner deficit")
    if inner_i <= 0 or inner_d <= 0 or inner_i - inner_48j != inner_d:
        raise VerificationError("fresh inner exact forms are inconsistent")
    a_rows, b_rows = [], []
    for count, path in enumerate(a_paths):
        row, _ = canonical_object(path)
        if row.get("count") != count:
            raise VerificationError(f"fresh A shard has wrong count {count}")
        values = row.get("exact_values")
        if type(values) is not dict:
            raise VerificationError(f"fresh A shard lacks values {count}")
        band = rational(values.get("band_I_count"), f"A[{count}]")
        a_rows.append(band)
    for count, path in enumerate(b_paths):
        row, _ = canonical_object(path)
        if row.get("common_r") != count:
            raise VerificationError(f"fresh b shard has wrong count {count}")
        b_rows.append(rational(row.get("scaled_b_shard"), f"b[{count}]"))
    a_value = sum(a_rows, Q(0))
    b_value = sum(b_rows, Q(0))
    i_value = inner_i * FORM_SCALE
    d_value = inner_d * FORM_SCALE
    margin = b_value**2 - a_value * d_value
    denominator = a_value * i_value + b_value**2
    if a_value <= 0 or denominator <= 0:
        raise VerificationError("fresh certificate denominator is nonpositive")
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
    return (exact, a_rows, b_rows,
            [sha256(path.read_bytes()) for path in a_paths],
            [sha256(path.read_bytes()) for path in b_paths])


def compare_certificate(certificate, aggregate, exact, a_rows, b_rows,
                        fresh_a_hashes, fresh_b_hashes):
    top = {
        "format", "status", "rigorous", "theorem_ready_scalar", "k",
        "counts", "scales", "exact", "a_shards", "b_shards",
        "source_hashes", "trust_scope", "assembler_sha256",
        "base_assembler_sha256", "b_engine",
    }
    if (type(certificate) is not dict or set(certificate) != top or
            type(aggregate) is not dict or set(aggregate) != top):
        raise VerificationError("compact/fresh aggregate schema is not exact")
    if (certificate.get("format") !=
            "H1-236-one-band-cached-v7-exact-shard-aggregate-v1" or
            certificate.get("status") != "EXACT ONE-BAND SCALAR CERTIFICATE PASS" or
            certificate.get("rigorous") is not True or
            certificate.get("theorem_ready_scalar") is not True or
            type(certificate.get("k")) is not int or
            certificate.get("k") != K or
            type(certificate.get("counts")) is not list or
            len(certificate.get("counts")) != len(COUNTS) or
            any(type(value) is not int for value in certificate.get("counts")) or
            certificate.get("counts") != list(COUNTS) or
            certificate.get("scales") != {
                "F": str(SCALE_F), "H": str(SCALE_H),
                "quadratic_inner": str(FORM_SCALE)} or
            certificate.get("assembler_sha256") != PINS[ASSEMBLER] or
            certificate.get("base_assembler_sha256") !=
                BASE_ASSEMBLER_SHA256 or
            certificate.get("b_engine") != "cached-fixed-v7"):
        raise VerificationError("compact certificate is not an armed k=48 pass")
    stable = {
        "format", "status", "rigorous", "theorem_ready_scalar", "k",
        "counts", "scales", "source_hashes", "trust_scope",
        "assembler_sha256", "base_assembler_sha256", "b_engine",
    }
    if any(aggregate.get(key) != certificate.get(key) for key in stable):
        raise VerificationError("fresh aggregate stable metadata differs")
    if (aggregate.get("status") != certificate.get("status") or
            aggregate.get("theorem_ready_scalar") is not True or
            type(aggregate.get("k")) is not int or
            type(aggregate.get("counts")) is not list or
            len(aggregate.get("counts")) != len(COUNTS) or
            any(type(value) is not int for value in aggregate.get("counts")) or
            aggregate.get("counts") != list(COUNTS) or
            aggregate.get("k") != K):
        raise VerificationError("fresh aggregate did not return a k=48 pass")
    if (type(certificate.get("exact")) is not dict or
            set(certificate["exact"]) != set(exact) or
            type(aggregate.get("exact")) is not dict or
            set(aggregate["exact"]) != set(exact)):
        raise VerificationError("aggregate exact-scalar schema differs")
    for key, value in exact.items():
        expected = str(value)
        if certificate.get("exact", {}).get(key) != expected:
            raise VerificationError(f"certificate exact field differs: {key}")
        if aggregate.get("exact", {}).get(key) != expected:
            raise VerificationError(f"fresh aggregate exact field differs: {key}")
    def check_rows(owner, label, rows, values, expected_hashes=None):
        if type(rows) is not list or len(rows) != len(COUNTS):
            raise VerificationError(
                f"{owner} {label} shard list is incomplete")
        if any(type(row) is not dict or
               set(row) != {"count", "value", "sha256"} for row in rows):
            raise VerificationError(
                f"{owner} {label} shard row is malformed")
        if any(type(row["count"]) is not int for row in rows):
            raise VerificationError(
                f"{owner} {label} shard count is not an exact integer")
        by_count = {row["count"]: row for row in rows}
        if set(by_count) != set(COUNTS):
            raise VerificationError(
                f"{owner} {label} counts are not exact")
        if expected_hashes is not None and len(expected_hashes) != len(COUNTS):
            raise VerificationError(
                f"fresh {label} hash inventory is incomplete")
        for count, value in enumerate(values):
            row = by_count[count]
            if row["value"] != str(value):
                raise VerificationError(
                    f"{owner} {label} value differs at count {count}")
            if type(row["sha256"]) is not str or \
                    HEX64.fullmatch(row["sha256"]) is None:
                raise VerificationError(
                    f"{owner} {label} SHA-256 is malformed at count {count}")
            if (expected_hashes is not None and
                    row["sha256"] != expected_hashes[count]):
                raise VerificationError(
                    f"{owner} {label} SHA-256 differs at count {count}")

    # The compact certificate's shard hashes identify the original, archived
    # runs and are syntax-checked here.  Fresh hashes need not equal them
    # because timing/RSS diagnostics are part of each deterministic-schema
    # shard.  The fresh aggregate, however, must bind byte-for-byte to the
    # freshly generated and independently audited shards.
    check_rows("certificate", "A", certificate.get("a_shards"), a_rows)
    check_rows("certificate", "b", certificate.get("b_shards"), b_rows)
    check_rows("fresh aggregate", "A", aggregate.get("a_shards"), a_rows,
               fresh_a_hashes)
    check_rows("fresh aggregate", "b", aggregate.get("b_shards"), b_rows,
               fresh_b_hashes)
    if exact["margin_b_squared_minus_A_D"] <= 0:
        raise VerificationError("exact reconstructed b^2-A*D is not positive")
    if exact["quotient_lower_bound"] <= 1:
        raise VerificationError("exact reconstructed quotient bound is not above one")


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
            raise VerificationError(f"expected {label} SHA-256 is not lowercase hex")
    self_data = FILE.read_bytes()
    if sha256(self_data) != args.expected_self_sha256:
        raise VerificationError("standalone checker self hash mismatch")
    snapshots = {path: path.read_bytes() for path in PINS}
    for path, expected in PINS.items():
        if sha256(snapshots[path]) != expected:
            raise VerificationError(f"pinned replay dependency changed: {path}")
    certificate, certificate_data = canonical_object(args.certificate.resolve())
    if sha256(certificate_data) != args.expected_certificate_sha256:
        raise VerificationError("compact certificate SHA-256 mismatch")

    with tempfile.TemporaryDirectory(prefix="H1-236-replay-") as temporary:
        work = Path(temporary)
        # The directory is private and this child path is never created.
        # Together with -B it prevents both reading and writing repository
        # pyc files while retaining isolated-mode imports.
        child_python = python_prefix(work / "empty-private-pycache")
        support_output = work / "support.json"
        run_stage("analytic support", child_python + [
            str(SUPPORT_CHECKER), "--output", str(support_output)], 900)
        support, _ = canonical_object(support_output)
        frozen_support, _ = canonical_object(SUPPORT_FROZEN)
        fresh_portable = deterministic_support_projection(
            support, "fresh", snapshots)
        frozen_portable = deterministic_support_projection(
            frozen_support, "frozen", snapshots)
        if fresh_portable != frozen_portable:
            raise VerificationError("fresh analytic-support result differs")

        tuple_stdout = run_stage(
            "admissible tuple", child_python + [str(TUPLE_CHECKER)], 60)
        tuple_result = strict_loads(tuple_stdout, "tuple checker stdout")
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
        inner, inner_data = canonical_object(inner_output)
        if sha256(inner_data) != PINS[INNER_FROZEN] or inner_data != snapshots[INNER_FROZEN]:
            raise VerificationError("fresh inner reconstruction differs bit-for-bit")

        a_dir, b_dir = work / "A", work / "b"
        a_dir.mkdir()
        b_dir.mkdir()
        a_paths = [a_dir / f"r{count:02d}.json" for count in COUNTS]
        b_paths = [b_dir / f"common_r_{count:02d}.json" for count in COUNTS]
        run_count_jobs("outer norm A", args.jobs, lambda count: child_python + [
            str(A_PRODUCER), "--count", str(count),
            "--output", str(a_paths[count])], 3600)
        a_radial_output = work / "A-radial-audit.json"
        run_stage("independent outer-norm radial replay", child_python + [
            str(A_RADIAL_CHECKER), *map(str, a_paths),
            "--output", str(a_radial_output),
            "--expected-self-sha256", PINS[A_RADIAL_CHECKER]], 14_400)
        a_radial, _ = canonical_object(a_radial_output)
        if (a_radial.get("status") !=
                "INDEPENDENT EXACT RADIAL A-v2 SHARD CHECK PASS" or
                a_radial.get("checked_counts") != list(COUNTS)):
            raise VerificationError("independent A radial replay did not pass all counts")
        radial_rows = a_radial.get("rows")
        if type(radial_rows) is not list or len(radial_rows) != len(COUNTS):
            raise VerificationError("independent A replay row inventory is incomplete")
        radial_by_count = {
            row.get("count"): row for row in radial_rows if type(row) is dict}
        if set(radial_by_count) != set(COUNTS):
            raise VerificationError("independent A replay count inventory differs")
        bound_shards = {}
        for count, path in enumerate(a_paths):
            data = path.read_bytes()
            if radial_by_count[count].get("shard_sha256") != sha256(data):
                raise VerificationError(
                    f"A shard r={count} differs from independently audited bytes")
            bound_shards[path] = data

        run_count_jobs("mixed Definition-5 b", args.jobs,
                       lambda count: child_python + [
            str(B_PRODUCER), "--common-r", str(count),
            "--output", str(b_paths[count]),
            "--expected-self-sha256", PINS[B_PRODUCER]], 14_400,
                       stderr_validator_for_count=lambda count: (
                           lambda data: validate_b_progress(data, count)))
        for count, path in enumerate(b_paths):
            stdout = run_stage(f"independent b result audit r={count}",
                               child_python + [
                str(B_RESULT_CHECKER), "--expected-self-sha256",
                PINS[B_RESULT_CHECKER], str(path)], 600)
            audited = strict_loads(stdout, f"b audit stdout r={count}")
            if (type(audited) is not dict or
                    audited.get("status") !=
                        "CACHED-V7 CROSS SHARD STRUCTURAL/RESULT AUDIT PASS" or
                    audited.get("common_r") != count):
                raise VerificationError(f"independent b audit failed at r={count}")
            data = path.read_bytes()
            if audited.get("input_sha256") != sha256(data):
                raise VerificationError(
                    f"b shard r={count} differs from independently audited bytes")
            bound_shards[path] = data

        if any(path.read_bytes() != data for path, data in bound_shards.items()):
            raise VerificationError("an audited shard changed before aggregation")

        aggregate_output = work / "aggregate.json"
        run_stage("exact scalar aggregation", child_python + [
            str(ASSEMBLER), "--a-dir", str(a_dir), "--b-dir", str(b_dir),
            "--output", str(aggregate_output),
            "--expected-self-sha256", PINS[ASSEMBLER]], 600)
        aggregate, _ = canonical_object(aggregate_output)
        exact, a_rows, b_rows, fresh_a_hashes, fresh_b_hashes = \
            exact_scalar_reconstruction(
            inner, a_paths, b_paths)
        if any(path.read_bytes() != data for path, data in bound_shards.items()):
            raise VerificationError("an audited shard changed during aggregation")
        if a_radial.get("sum_scaled_band_I") != str(exact["A_scaled"]):
            raise VerificationError("independent A replay aggregate differs")
        compare_certificate(certificate, aggregate, exact, a_rows, b_rows,
                            fresh_a_hashes, fresh_b_hashes)

    if (FILE.read_bytes() != self_data or
            any(path.read_bytes() != data for path, data in snapshots.items()) or
            args.certificate.resolve().read_bytes() != certificate_data):
        raise VerificationError("checker/certificate/source closure changed during replay")
    result = {
        "status": (
            "AUDIT PASS: exact k=48 quotient > 1; "
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
