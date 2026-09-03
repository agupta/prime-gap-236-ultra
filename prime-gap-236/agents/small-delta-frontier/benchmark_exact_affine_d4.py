#!/usr/bin/env python3
"""Single-worker exact D4 benchmark for the affine-multiplier checker.

The discovery coefficients are first cleared of denominators.  The base
polynomial and the *effective* cutoff-10 affine table get separate integer
LCM scales.  Hence the evaluated function is the original function times
``base_lcm * affine_lcm`` and I and kJ are each scaled by its square.

The I stage is durable so that a long J phase can be resumed in a fresh
process.  A J-only invocation must supply the exact byte SHA of that stage.
This is a benchmark/regression, not the D12 theorem certificate.
"""

from __future__ import annotations

import argparse
import ast
import gc
import hashlib
import json
import math
import os
import resource
import re
import sys
import time
from fractions import Fraction
from pathlib import Path

if hasattr(sys, "set_int_max_str_digits"):
    sys.set_int_max_str_digits(0)

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
VERIFY = ROOT / "verify"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from verify.exact_affine_multiplier import (  # noqa: E402
    AffineMultipliers,
    compute_i_affine_tagged,
    compute_j_affine_tagged,
    load_exact_affine_multiplier,
)
from verify.exact_capped_certificate import (  # noqa: E402
    C10_D4_REGRESSION,
    _reject_constant,
    _reject_duplicate_object,
    build_basis_terms,
    parse_fraction,
)


BASE_PATH = (ROOT / "agents/exact-integrator/results/"
             "c10_capped_D4_decimal55_vector_input.json")
AFFINE_PATH = (ROOT / "agents/exact-integrator/results/"
               "c10_stratum_linear_cappedopt_D4_exact.json")
BASE_SHA256 = "2b11a18c697e9a2be61204b5493bf7a235ce4add39d853bbb4d76ef31fb4666b"
AFFINE_SHA256 = "ffa607e0f2a8a3b6648f248efb13dc7ac2f1e7ef5809771f31c5f04b30f53158"
DEPENDENCY_SHAS = {
    VERIFY / "exact_affine_multiplier.py":
        "9c21d73af25f63ad16c62a2a1935a9cfd3a8d134d7b7ada2620eddc12e1c3d3e",
    VERIFY / "exact_capped_certificate.py":
        "1787e7b482a5c2982de56486bc774794f6e671b3db4d9ab7207ebb1c85dc079c",
}
LINEAR_CUTOFF = 10
EXPECTED_BASIS = [
    (0, ()), (1, ()), (2, ()), (0, (2,)),
    (3, ()), (1, (2,)), (0, (3,)), (4, ()),
    (2, (2,)), (1, (3,)), (0, (4,)), (0, (2, 2)),
]


class BenchmarkError(RuntimeError):
    pass


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require_sha(path: Path, expected: str) -> bytes:
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise BenchmarkError(f"cannot read {path}: {exc}") from exc
    actual = hashlib.sha256(raw).hexdigest()
    if actual != expected:
        raise BenchmarkError(
            f"SHA mismatch for {path}: expected {expected}, got {actual}")
    return raw


def strict_json(raw: bytes, description: str) -> dict:
    try:
        value = json.loads(
            raw,
            object_pairs_hook=_reject_duplicate_object,
            parse_constant=_reject_constant,
        )
    except (json.JSONDecodeError, UnicodeError) as exc:
        raise BenchmarkError(f"malformed {description}: {exc}") from exc
    if not isinstance(value, dict):
        raise BenchmarkError(f"{description} is not an object")
    return value


def lcm_denominators(values) -> int:
    answer = 1
    for value in values:
        if not isinstance(value, Fraction):
            raise BenchmarkError("LCM input is not exact Fraction data")
        answer = math.lcm(answer, value.denominator)
    return answer


def parse_exact_decimal(value, label: str) -> Fraction:
    """Parse the pinned discovery decimals as finite exact rationals."""
    if not isinstance(value, str) or re.fullmatch(
            r"-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?", value) is None:
        raise BenchmarkError(f"malformed exact decimal at {label}")
    try:
        return Fraction(value)
    except (ValueError, ZeroDivisionError) as exc:
        raise BenchmarkError(f"malformed exact decimal at {label}") from exc


def load_integer_scaled_inputs():
    base_raw = strict_json(require_sha(BASE_PATH, BASE_SHA256), "D4 base input")
    if (base_raw.get("status") != "exact-fixed-vector-input" or
            base_raw.get("k") != C10_D4_REGRESSION.k or
            base_raw.get("basis_dimension") != len(EXPECTED_BASIS)):
        raise BenchmarkError("D4 base metadata mismatch")
    raw_labels = base_raw.get("basis")
    raw_vector = base_raw.get("rational_vector")
    if not isinstance(raw_labels, list) or not isinstance(raw_vector, list):
        raise BenchmarkError("D4 base labels/vector are absent")
    labels = []
    for index, label in enumerate(raw_labels):
        if (not isinstance(label, list) or len(label) != 2 or
                isinstance(label[0], bool) or not isinstance(label[0], int) or
                not isinstance(label[1], list) or
                any(isinstance(x, bool) or not isinstance(x, int)
                    for x in label[1])):
            raise BenchmarkError(f"malformed base label {index}")
        labels.append((label[0], tuple(label[1])))
    if labels != EXPECTED_BASIS:
        raise BenchmarkError("D4 base labels are not the pinned canonical list")
    if len(raw_vector) != len(labels):
        raise BenchmarkError("D4 base coefficient count mismatch")
    base_coefficients = [
        parse_exact_decimal(value, f"base rational_vector[{index}]")
        for index, value in enumerate(raw_vector)
    ]
    base_lcm = lcm_denominators(base_coefficients)
    scaled_base = [value * base_lcm for value in base_coefficients]
    if any(value.denominator != 1 for value in scaled_base):
        raise BenchmarkError("base LCM scaling did not produce integers")

    affine = load_exact_affine_multiplier(
        AFFINE_PATH,
        C10_D4_REGRESSION,
        AFFINE_SHA256,
        linear_cutoff=LINEAR_CUTOFF,
    )
    effective_values = [value for triple in affine.coefficients for value in triple]
    affine_lcm = lcm_denominators(effective_values)
    scaled_affine_coefficients = tuple(
        tuple(value * affine_lcm for value in triple)
        for triple in affine.coefficients
    )
    if any(value.denominator != 1
           for triple in scaled_affine_coefficients for value in triple):
        raise BenchmarkError("affine LCM scaling did not produce integers")
    scaled_affine = AffineMultipliers(
        scaled_affine_coefficients,
        source_sha256=AFFINE_SHA256,
        linear_cutoff=LINEAR_CUTOFF,
    )
    scaled_affine.validate_for(C10_D4_REGRESSION)
    return (
        build_basis_terms(labels, scaled_base),
        scaled_affine,
        base_lcm,
        affine_lcm,
    )


def reference_forms() -> tuple[Fraction, Fraction]:
    """Contract the producer's pinned D4 matrix as a regression oracle only."""
    raw = strict_json(require_sha(AFFINE_PATH, AFFINE_SHA256), "D4 affine artifact")
    labels = raw.get("linear_labels")
    vector = raw.get("rational_vector")
    expected_labels = [[r, channel]
                       for r in range(16) for channel in ("1", "L", "Z")]
    if labels != expected_labels or not isinstance(vector, list) or len(vector) != 48:
        raise BenchmarkError("D4 affine matrix coordinate order mismatch")
    coefficients = {}
    for index, ((r, channel), token) in enumerate(zip(labels, vector, strict=True)):
        value = parse_fraction(token, f"affine rational_vector[{index}]")
        if channel != "1" and r > LINEAR_CUTOFF:
            value = Fraction(0)
        coefficients[(r, ("1", "L", "Z").index(channel))] = value

    i_blocks = raw.get("i_blocks")
    j_entries = raw.get("j_entries")
    if not isinstance(i_blocks, dict) or not isinstance(j_entries, dict):
        raise BenchmarkError("D4 affine reference forms are absent")
    i_value = Fraction(0)
    for r in range(16):
        block = i_blocks.get(str(r))
        if (not isinstance(block, list) or len(block) != 3 or
                any(not isinstance(row, list) or len(row) != 3 for row in block)):
            raise BenchmarkError(f"malformed I reference block {r}")
        for left in range(3):
            for right in range(3):
                entry = parse_fraction(
                    block[left][right], f"i_blocks[{r}][{left}][{right}]")
                i_value += (coefficients[(r, left)] * entry *
                            coefficients[(r, right)])
    j_value = Fraction(0)
    for token, raw_entry in sorted(j_entries.items()):
        try:
            left, right = ast.literal_eval(token)
        except (SyntaxError, ValueError) as exc:
            raise BenchmarkError(f"malformed J coordinate {token!r}") from exc
        if (not isinstance(left, tuple) or not isinstance(right, tuple) or
                len(left) != 2 or len(right) != 2 or
                left not in coefficients or right not in coefficients or
                left > right):
            raise BenchmarkError(f"noncanonical J coordinate {token!r}")
        entry = parse_fraction(raw_entry, f"j_entries[{token!r}]")
        term = coefficients[left] * entry * coefficients[right]
        j_value += term if left == right else 2 * term
    return i_value, C10_D4_REGRESSION.k * j_value


def fraction_json(value: Fraction) -> dict:
    return {
        "numerator": str(value.numerator),
        "denominator": str(value.denominator),
    }


def fraction_from_json(value, label: str) -> Fraction:
    if not isinstance(value, dict) or set(value) != {"numerator", "denominator"}:
        raise BenchmarkError(f"malformed staged {label}")
    try:
        answer = Fraction(int(value["numerator"]), int(value["denominator"]))
    except (TypeError, ValueError, ZeroDivisionError) as exc:
        raise BenchmarkError(f"malformed staged {label}") from exc
    if str(answer.numerator) != value["numerator"] or \
            str(answer.denominator) != value["denominator"]:
        raise BenchmarkError(f"noncanonical staged {label}")
    return answer


def decimal_string(value: Fraction, digits: int = 45) -> str:
    # A diagnostic decimal only.  Exact acceptance never uses this string.
    from decimal import Decimal, localcontext
    with localcontext() as context:
        context.prec = digits
        return str(Decimal(value.numerator) / Decimal(value.denominator))


def rss_kib() -> int:
    # Linux reports KiB.  This benchmark is intentionally platform-labelled.
    return int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)


def atomic_json(path: Path, payload: dict) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + f".tmp.{os.getpid()}")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    os.replace(temporary, path)
    return sha256(path)


def dependency_snapshot() -> dict[str, str]:
    snapshot = {}
    for path, expected in DEPENDENCY_SHAS.items():
        require_sha(path, expected)
        snapshot[str(path.relative_to(ROOT))] = expected
    return snapshot


def require_dependencies_unchanged(snapshot: dict[str, str]) -> None:
    current = dependency_snapshot()
    if current != snapshot:
        raise BenchmarkError("arithmetic dependency set changed during benchmark")
    require_sha(BASE_PATH, BASE_SHA256)
    require_sha(AFFINE_PATH, AFFINE_SHA256)


def common_metadata(base_lcm: int, affine_lcm: int,
                    dependencies: dict[str, str]) -> dict:
    total_scale = base_lcm * affine_lcm
    return {
        "scope": "C10 D4 exact affine benchmark; not a D12 certificate",
        "k": C10_D4_REGRESSION.k,
        "degree": C10_D4_REGRESSION.degree,
        "linear_cutoff": LINEAR_CUTOFF,
        "workers": 1,
        "reverse_faces": False,
        "base_path": str(BASE_PATH.relative_to(ROOT)),
        "base_sha256": BASE_SHA256,
        "affine_path": str(AFFINE_PATH.relative_to(ROOT)),
        "affine_sha256": AFFINE_SHA256,
        "dependency_sha256": dependencies,
        "base_lcm": str(base_lcm),
        "base_lcm_bits": base_lcm.bit_length(),
        "effective_affine_lcm": str(affine_lcm),
        "effective_affine_lcm_bits": affine_lcm.bit_length(),
        "global_function_scale": str(total_scale),
        "global_form_scale_squared": str(total_scale * total_scale),
        "all_effective_coefficients_are_integers": True,
    }


def run_i(stage_path: Path) -> tuple[dict, str]:
    dependencies = dependency_snapshot()
    basis_terms, multipliers, base_lcm, affine_lcm = load_integer_scaled_inputs()
    reference_i, reference_kj = reference_forms()
    form_scale = (base_lcm * affine_lcm) ** 2
    started_wall = time.perf_counter()
    started_cpu = time.process_time()
    i_value = compute_i_affine_tagged(
        basis_terms, C10_D4_REGRESSION, multipliers, workers=1)
    wall = time.perf_counter() - started_wall
    cpu = time.process_time() - started_cpu
    if i_value != reference_i * form_scale:
        raise BenchmarkError("direct integer-scaled I disagrees with D4 reference")
    require_dependencies_unchanged(dependencies)
    payload = {
        "status": "exact-affine-d4-integer-i-stage",
        **common_metadata(base_lcm, affine_lcm, dependencies),
        "direct_i": fraction_json(i_value),
        "reference_unscaled_i": fraction_json(reference_i),
        "reference_unscaled_kj": fraction_json(reference_kj),
        "i_wall_seconds": wall,
        "i_cpu_seconds": cpu,
        "i_peak_rss_kib_linux": rss_kib(),
        "i_direct_reference_bitwise_equal_after_scaling": True,
    }
    stage_sha = atomic_json(stage_path, payload)
    return payload, stage_sha


def load_stage(stage_path: Path, expected_sha: str) -> tuple[dict, Fraction]:
    if not expected_sha or len(expected_sha) != 64:
        raise BenchmarkError("J-only phase requires a 64-hex expected stage SHA")
    raw = require_sha(stage_path, expected_sha)
    stage = strict_json(raw, "D4 I stage")
    if stage.get("status") != "exact-affine-d4-integer-i-stage":
        raise BenchmarkError("I stage status mismatch")
    return stage, fraction_from_json(stage.get("direct_i"), "direct_i")


def run_j(stage_path: Path, expected_stage_sha: str, output_path: Path) -> dict:
    dependencies = dependency_snapshot()
    stage, staged_i = load_stage(stage_path, expected_stage_sha)
    basis_terms, multipliers, base_lcm, affine_lcm = load_integer_scaled_inputs()
    expected_common = common_metadata(base_lcm, affine_lcm, dependencies)
    for key, value in expected_common.items():
        if stage.get(key) != value:
            raise BenchmarkError(f"I stage metadata mismatch at {key}")
    reference_i, reference_kj = reference_forms()
    form_scale = (base_lcm * affine_lcm) ** 2
    if staged_i != reference_i * form_scale:
        raise BenchmarkError("staged I no longer agrees with exact D4 reference")
    gc.collect()
    started_wall = time.perf_counter()
    started_cpu = time.process_time()
    j_value = compute_j_affine_tagged(
        basis_terms, C10_D4_REGRESSION, multipliers, workers=1)
    kj_value = C10_D4_REGRESSION.k * j_value
    wall = time.perf_counter() - started_wall
    cpu = time.process_time() - started_cpu
    if kj_value != reference_kj * form_scale:
        raise BenchmarkError("direct integer-scaled kJ disagrees with D4 reference")
    quotient = kj_value / staged_i
    margin = kj_value - staged_i
    require_sha(stage_path, expected_stage_sha)
    require_dependencies_unchanged(dependencies)
    payload = {
        "status": "exact-affine-d4-integer-benchmark-complete",
        **expected_common,
        "i_stage_path": str(stage_path.relative_to(ROOT)),
        "i_stage_sha256": expected_stage_sha,
        "direct_i": fraction_json(staged_i),
        "direct_kj": fraction_json(kj_value),
        "direct_margin_kj_minus_i": fraction_json(margin),
        "direct_quotient": fraction_json(quotient),
        "quotient_decimal_45": decimal_string(quotient),
        "margin_decimal_45": decimal_string(margin / form_scale),
        "j_wall_seconds": wall,
        "j_cpu_seconds": cpu,
        "j_process_peak_rss_kib_linux": rss_kib(),
        "i_wall_seconds": stage["i_wall_seconds"],
        "i_cpu_seconds": stage["i_cpu_seconds"],
        "i_process_peak_rss_kib_linux": stage["i_peak_rss_kib_linux"],
        "i_direct_reference_bitwise_equal_after_scaling": True,
        "kj_direct_reference_bitwise_equal_after_scaling": True,
        "quotient_invariant_under_integer_scaling":
            quotient == reference_kj / reference_i,
        "theorem_ready": False,
    }
    if payload["quotient_invariant_under_integer_scaling"] is not True:
        raise BenchmarkError("integer scaling changed the exact quotient")
    atomic_json(output_path, payload)
    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=("i", "j", "all"), default="all")
    parser.add_argument(
        "--stage",
        type=Path,
        default=HERE / "exact_affine_d4_integer_benchmark.stage.json",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=HERE / "exact_affine_d4_integer_benchmark.json",
    )
    parser.add_argument("--expected-stage-sha256")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    expected_stage_sha = args.expected_stage_sha256
    if args.phase in ("i", "all"):
        stage, expected_stage_sha = run_i(args.stage)
        print(json.dumps({
            "phase": "I complete",
            "stage": str(args.stage),
            "stage_sha256": expected_stage_sha,
            "wall_seconds": stage["i_wall_seconds"],
            "peak_rss_kib_linux": stage["i_peak_rss_kib_linux"],
        }, sort_keys=True), flush=True)
    if args.phase in ("j", "all"):
        result = run_j(args.stage, expected_stage_sha, args.output)
        print(json.dumps({
            "phase": "J complete",
            "output": str(args.output),
            "output_sha256": sha256(args.output),
            "wall_seconds": result["j_wall_seconds"],
            "peak_rss_kib_linux": result["j_process_peak_rss_kib_linux"],
            "quotient_decimal_45": result["quotient_decimal_45"],
        }, sort_keys=True), flush=True)


if __name__ == "__main__":
    try:
        main()
    except (BenchmarkError, ValueError, ArithmeticError, OSError) as exc:
        raise SystemExit(f"BENCHMARK FAIL: {exc}") from exc
