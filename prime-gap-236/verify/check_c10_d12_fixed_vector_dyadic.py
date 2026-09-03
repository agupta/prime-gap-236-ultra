#!/usr/bin/env python3
"""Rigorous staged dyadic checker for one explicit C10 D12 fixed vector.

The input is only an ordered no-ones degree-at-most-12 basis and an exact
rational coefficient vector.  This driver clears the common denominator,
removes integer content, reconstructs the orbit products, and evaluates the
support integrals with integer-directed outward-rounded intervals.  It never
reads a matrix, eigenvalue, Decimal integral, or serialized moment table.

This is certificate plumbing, not by itself a theorem claim.  A positive
output must still receive an independent code/output audit and a second
reconstruction.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import resource
import sys
import tempfile
import time
from fractions import Fraction
from pathlib import Path

if hasattr(sys, "set_int_max_str_digits"):
    sys.set_int_max_str_digits(0)

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
ENGINE = ROOT / "agents/exact-integrator"
sys.path[:0] = [str(ROOT), str(ENGINE), str(ENGINE / "src")]

import exact_integrator as ei  # noqa: E402
from dyadic_backend import install_dyadic  # noqa: E402
from grouped_fixed_vector import GroupedEvaluator, precompute_orbits  # noqa: E402
from verify.dyadic_interval import DyadicInterval  # noqa: E402
from verify.exact_capped_certificate import (  # noqa: E402
    CertificateError,
    TARGET_C10_D12,
    _reject_constant,
    _reject_duplicate_object,
    expected_labels,
    ordered_payload_sha256,
    parse_fraction,
    validate_parameters,
)


EXPECTED_DIMENSION = 272
EXPECTED_ORBIT_PRODUCTS = 5929
EXPECTED_I_GROUPS = 1575
EXPECTED_I_FACES = 312
EXPECTED_MARGINAL_COMPONENTS = 695
EXPECTED_J_DOMAINS = 1200

DEPENDENCY_SHAS = {
    ROOT / "verify/dyadic_interval.py":
        "f6f1730f77ba490f04326338e7b3bfe5ab2e5c6438f10892bdf3f5bfe6fc875d",
    ROOT / "verify/exact_capped_certificate.py":
        "1787e7b482a5c2982de56486bc774794f6e671b3db4d9ab7207ebb1c85dc079c",
    ENGINE / "dyadic_backend.py":
        "1dae20016b5fcbde5f56cf222ce92b45899f14bd5ff07fd3c70b7b10ce4ce608",
    ENGINE / "grouped_fixed_vector.py":
        "47167e92a0f346e969706dc282ccb2dfd4ac31a0a75b654938ffbe8423cf4a4a",
    ENGINE / "src/exact_integrator.py":
        "941ee82bc72fd8488a95eb5e536fe47f8c95d39a1b618dae7d6ef7eb27122e52",
}


class FixedDyadicError(RuntimeError):
    pass


class OrderedGroupedEvaluator(GroupedEvaluator):
    """Add an explicit serial reverse-r traversal without editing the engine."""

    def __init__(self, *args, reverse_faces: bool = False, **kwargs):
        super().__init__(*args, **kwargs)
        self.reverse_faces = reverse_faces

    def evaluate_i(self, progress=False, workers=1):
        if not self.reverse_faces:
            return super().evaluate_i(progress, workers)
        if workers != 1:
            raise FixedDyadicError("reverse-r traversal requires one worker")
        grouped = self.square_residual_terms()
        max_r = min(self.support.k, self.support.max_large())
        r_values = list(reversed(range(max_r + 1)))
        results = [self.evaluate_i_r(grouped, r, progress) for r in r_values]
        answer = sum((value for value, _ in results), self.zero)
        return answer, len(grouped), sum(count for _, count in results)

    def evaluate_j(self, progress=False, workers=1):
        if not self.reverse_faces:
            return super().evaluate_j(progress, workers)
        if workers != 1:
            raise FixedDyadicError("reverse-r traversal requires one worker")
        components = self.marginal_components()
        lrs = sorted({lr for lr, _, _ in components})
        by_lr = {
            lr: [(e, a, value) for (x, e, a), value in components.items()
                 if x == lr]
            for lr in lrs
        }
        max_r = min(self.support.k - 1, self.support.max_large())
        r_values = list(reversed(range(max_r + 1)))
        results = [self.evaluate_j_r(lrs, by_lr, r, progress) for r in r_values]
        answer = sum((value for value, _ in results), self.zero)
        return answer, len(components), sum(count for _, count in results)


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def sha256(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def require_sha_text(value: str, description: str) -> None:
    if (not isinstance(value, str) or len(value) != 64 or
            any(character not in "0123456789abcdef" for character in value)):
        raise FixedDyadicError(f"{description} is not a lowercase SHA-256")


def read_pinned(path: Path, expected: str, description: str) -> bytes:
    require_sha_text(expected, f"expected {description} SHA")
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise FixedDyadicError(f"cannot read {description}: {exc}") from exc
    if len(raw) > 20_000_000:
        raise FixedDyadicError(f"{description} exceeds 20 MB")
    actual = sha256_bytes(raw)
    if actual != expected:
        raise FixedDyadicError(
            f"{description} SHA mismatch: expected {expected}, got {actual}")
    return raw


def strict_json(raw: bytes, description: str) -> dict:
    try:
        value = json.loads(
            raw,
            object_pairs_hook=_reject_duplicate_object,
            parse_constant=_reject_constant,
        )
    except (json.JSONDecodeError, UnicodeError, CertificateError) as exc:
        raise FixedDyadicError(f"malformed {description}: {exc}") from exc
    if not isinstance(value, dict):
        raise FixedDyadicError(f"{description} is not an object")
    return value


def dependency_snapshot() -> dict[str, str]:
    snapshot = {}
    for path, expected in DEPENDENCY_SHAS.items():
        actual = sha256(path)
        if actual != expected:
            raise FixedDyadicError(
                f"dependency SHA mismatch for {path}: {actual} != {expected}")
        snapshot[str(path.relative_to(ROOT))] = actual
    return snapshot


def parse_input(path: Path, expected_sha: str):
    raw_bytes = read_pinned(path, expected_sha, "fixed-vector input")
    raw = strict_json(raw_bytes, "fixed-vector input")
    if raw.get("k") != 48 or isinstance(raw.get("k"), bool):
        raise FixedDyadicError("input k must be the integer 48")
    basis = raw.get("basis")
    vector = raw.get("rational_vector")
    if not isinstance(basis, list) or not isinstance(vector, list):
        raise FixedDyadicError("basis and rational_vector must be arrays")
    if len(basis) != EXPECTED_DIMENSION or len(vector) != EXPECTED_DIMENSION:
        raise FixedDyadicError("target basis/vector dimension mismatch")

    labels = []
    for index, item in enumerate(basis):
        if (not isinstance(item, list) or len(item) != 2 or
                isinstance(item[0], bool) or not isinstance(item[0], int) or
                item[0] < 0 or not isinstance(item[1], list)):
            raise FixedDyadicError(f"malformed basis label {index}")
        residual, parts = item
        if any(isinstance(x, bool) or not isinstance(x, int) for x in parts):
            raise FixedDyadicError(f"noninteger partition at basis label {index}")
        partition = tuple(parts)
        if (any(x < 2 for x in partition) or
                tuple(sorted(partition, reverse=True)) != partition or
                len(partition) > 48 or residual + sum(partition) > 12):
            raise FixedDyadicError(f"noncanonical basis label {index}")
        labels.append((residual, partition))
    if len(set(labels)) != EXPECTED_DIMENSION:
        raise FixedDyadicError("basis labels are not distinct")
    if set(labels) != expected_labels(12, 48):
        raise FixedDyadicError("basis is not the complete no-ones D12 basis")

    try:
        coefficients = [
            parse_fraction(value, f"rational_vector[{index}]")
            for index, value in enumerate(vector)
        ]
        payload_sha = ordered_payload_sha256(raw)
    except CertificateError as exc:
        raise FixedDyadicError(f"invalid coefficient payload: {exc}") from exc
    if not any(coefficients):
        raise FixedDyadicError("coefficient vector is identically zero")

    common_denominator = 1
    for value in coefficients:
        common_denominator = math.lcm(common_denominator, value.denominator)
    integers = [value.numerator * (common_denominator // value.denominator)
                for value in coefficients]
    content = 0
    for value in integers:
        content = math.gcd(content, abs(value))
    if content <= 0:
        raise FixedDyadicError("integer content is not positive")
    primitive = [value // content for value in integers]
    if math.gcd(*primitive) != 1:
        raise FixedDyadicError("primitive coefficient reconstruction failed")
    for original, scaled in zip(coefficients, primitive):
        if original * common_denominator != scaled * content:
            raise FixedDyadicError("integer scaling changed a coefficient")
    return raw_bytes, labels, primitive, common_denominator, content, payload_sha


def prepare(input_path: Path, input_sha: str, precision: int,
            shadow_bits: int, reverse_faces: bool):
    validate_parameters(TARGET_C10_D12)
    raw_bytes, labels, primitive, denominator_lcm, content, payload_sha = \
        parse_input(input_path, input_sha)
    dependencies = dependency_snapshot()
    orbit_table = precompute_orbits(labels, TARGET_C10_D12.k)
    if len(orbit_table) != EXPECTED_ORBIT_PRODUCTS:
        raise FixedDyadicError("orbit-product count mismatch")
    scalar = install_dyadic(orbit_table, precision, shadow_bits)
    parameters = (
        TARGET_C10_D12.alpha,
        TARGET_C10_D12.delta,
        TARGET_C10_D12.eta,
        TARGET_C10_D12.beta1,
        TARGET_C10_D12.beta2,
        TARGET_C10_D12.beta3plus,
    )
    support = ei.OneStratumSupport(
        TARGET_C10_D12.k,
        *(scalar(value.numerator, value.denominator) for value in parameters),
    )
    evaluator = OrderedGroupedEvaluator(
        support, labels, [scalar(value) for value in primitive], scalar,
        reverse_faces=reverse_faces)
    common = {
        "input_sha256": sha256_bytes(raw_bytes),
        "ordered_label_vector_payload_sha256": payload_sha,
        "input_common_denominator": str(denominator_lcm),
        "input_integer_content_removed": str(content),
        "primitive_integer_vector_sha256": sha256_bytes(
            json.dumps(primitive, separators=(",", ":")).encode("ascii")),
        "dependencies": dependencies,
        "precision_bits": precision,
        "shadow_bits": shadow_bits,
        "reverse_faces": reverse_faces,
        "support": {
            "k": 48,
            "degree": 12,
            "alpha": str(TARGET_C10_D12.alpha),
            "eta": str(TARGET_C10_D12.eta),
            "delta": str(TARGET_C10_D12.delta),
            "beta1": str(TARGET_C10_D12.beta1),
            "beta2": str(TARGET_C10_D12.beta2),
            "beta3plus": str(TARGET_C10_D12.beta3plus),
            "c1": "0",
            "c2": "0",
        },
        "basis_dimension": EXPECTED_DIMENSION,
        "orbit_product_pairs": EXPECTED_ORBIT_PRODUCTS,
    }
    return evaluator, common


def interval_data(value: DyadicInterval) -> dict:
    if not isinstance(value, DyadicInterval):
        raise FixedDyadicError("computed result is not a dyadic interval")
    precision = DyadicInterval.PRECISION
    return {
        "precision_bits": precision,
        "lo_integer": str(value.lo),
        "hi_integer": str(value.hi),
        "lower_fraction": str(Fraction(value.lo, 1 << precision)),
        "upper_fraction": str(Fraction(value.hi, 1 << precision)),
        "width_units": str(value.hi - value.lo),
    }


def interval_from_data(raw, description: str) -> DyadicInterval:
    expected_keys = {
        "precision_bits", "lo_integer", "hi_integer",
        "lower_fraction", "upper_fraction", "width_units",
    }
    if not isinstance(raw, dict) or set(raw) != expected_keys:
        raise FixedDyadicError(f"malformed staged {description}")
    if raw["precision_bits"] != DyadicInterval.PRECISION:
        raise FixedDyadicError(f"staged {description} precision mismatch")
    for key in ("lo_integer", "hi_integer", "lower_fraction",
                "upper_fraction", "width_units"):
        if not isinstance(raw[key], str) or not raw[key]:
            raise FixedDyadicError(
                f"staged {description} {key} must be a nonempty string")
    try:
        lo, hi = int(raw["lo_integer"]), int(raw["hi_integer"])
        lower, upper = Fraction(raw["lower_fraction"]), Fraction(raw["upper_fraction"])
        width = int(raw["width_units"])
    except (TypeError, ValueError, ZeroDivisionError) as exc:
        raise FixedDyadicError(f"invalid staged {description}: {exc}") from exc
    if any(str(value) != raw[key] for value, key in (
            (lo, "lo_integer"), (hi, "hi_integer"), (width, "width_units"))):
        raise FixedDyadicError(f"noncanonical staged {description} integer")
    if (str(lower) != raw["lower_fraction"] or
            str(upper) != raw["upper_fraction"]):
        raise FixedDyadicError(f"noncanonical staged {description} fraction")
    if lo > hi or width != hi - lo:
        raise FixedDyadicError(f"reversed/inconsistent staged {description}")
    scale = 1 << DyadicInterval.PRECISION
    if lower != Fraction(lo, scale) or upper != Fraction(hi, scale):
        raise FixedDyadicError(f"staged {description} endpoint mismatch")
    return DyadicInterval._from_bounds(lo, hi)


def atomic_write(path: Path, payload: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        dir=path.parent, prefix=f".{path.name}.", suffix=".tmp", text=True)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def exact_metadata_equal(left, right) -> bool:
    """Compare JSON metadata without Python's bool==int coercion."""
    if type(left) is not type(right):
        return False
    if isinstance(left, dict):
        return (set(left) == set(right) and
                all(exact_metadata_equal(left[key], right[key]) for key in left))
    if isinstance(left, list):
        return (len(left) == len(right) and
                all(exact_metadata_equal(x, y) for x, y in zip(left, right)))
    return left == right


def failed_output(path: Path, phase: str, message: str) -> None:
    """Replace a possibly stale result by a non-certificate failure record."""
    atomic_write(path, json.dumps({
        "status": "failed-fixed-vector-dyadic-invocation",
        "phase": phase,
        "theorem_ready": False,
        "error": message,
    }, indent=2, sort_keys=True) + "\n")


def validate_paths(input_path: Path, stage_path: Path, output_path: Path) -> None:
    resolved = [input_path.resolve(), stage_path.resolve(), output_path.resolve()]
    if len(set(resolved)) != len(resolved):
        raise FixedDyadicError("input, stage, and output paths must be distinct")
    protected = {Path(__file__).resolve(),
                 *(path.resolve() for path in DEPENDENCY_SHAS)}
    if any(path in protected for path in resolved):
        raise FixedDyadicError("an input/output path collides with checker code")


def run_i(evaluator, common: dict, input_path: Path, stage_path: Path,
          workers: int, progress: bool):
    driver_sha = sha256(Path(__file__))
    wall, cpu = time.perf_counter(), time.process_time()
    denominator, groups, faces = evaluator.evaluate_i(progress, workers)
    wall, cpu = time.perf_counter() - wall, time.process_time() - cpu
    if groups != EXPECTED_I_GROUPS or faces != EXPECTED_I_FACES:
        raise FixedDyadicError("I traversal count mismatch")
    if denominator.lo <= 0:
        raise FixedDyadicError("I lower endpoint is not strictly positive")
    read_pinned(input_path, common["input_sha256"], "fixed-vector input")
    if sha256(Path(__file__)) != driver_sha or dependency_snapshot() != common["dependencies"]:
        raise FixedDyadicError("input/checker/dependency changed during I")
    stage = {
        "status": "c10-d12-fixed-vector-rigorous-dyadic-i-stage",
        **common,
        "workers": workers,
        "driver_sha256": driver_sha,
        "I": interval_data(denominator),
        "I_strictly_positive": True,
        "i_orbit_groups": groups,
        "i_faces": faces,
        "i_wall_seconds": wall,
        "i_cpu_seconds": cpu,
        "i_peak_rss_kib_linux": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "i_child_peak_rss_kib_linux": resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,
    }
    rendered = json.dumps(stage, indent=2, sort_keys=True) + "\n"
    expected_stage_sha = sha256_bytes(rendered.encode("utf-8"))
    atomic_write(stage_path, rendered)
    try:
        read_pinned(input_path, common["input_sha256"], "fixed-vector input")
        if (sha256(stage_path) != expected_stage_sha or
                sha256(Path(__file__)) != driver_sha or
                dependency_snapshot() != common["dependencies"]):
            raise FixedDyadicError("postwrite closure changed during I")
    except Exception as exc:
        failed_output(stage_path, "i", str(exc))
        raise
    return stage, expected_stage_sha


def load_stage(stage_path: Path, expected_sha: str, common: dict,
               workers: int):
    stage = strict_json(read_pinned(stage_path, expected_sha, "I stage"), "I stage")
    expected_keys = {
        "status", *common.keys(), "workers", "driver_sha256", "I",
        "I_strictly_positive", "i_orbit_groups", "i_faces",
        "i_wall_seconds", "i_cpu_seconds", "i_peak_rss_kib_linux",
        "i_child_peak_rss_kib_linux",
    }
    if set(stage) != expected_keys:
        raise FixedDyadicError("I-stage field set mismatch")
    if stage["status"] != "c10-d12-fixed-vector-rigorous-dyadic-i-stage":
        raise FixedDyadicError("I-stage status mismatch")
    for key, value in common.items():
        if not exact_metadata_equal(stage.get(key), value):
            raise FixedDyadicError(f"I-stage metadata mismatch at {key}")
    if (type(stage.get("workers")) is not int or
            stage.get("workers") != workers or
            stage.get("driver_sha256") != sha256(Path(__file__)) or
            stage.get("I_strictly_positive") is not True or
            stage.get("i_orbit_groups") != EXPECTED_I_GROUPS or
            stage.get("i_faces") != EXPECTED_I_FACES):
        raise FixedDyadicError("I-stage completeness gate failed")
    for key in ("i_wall_seconds", "i_cpu_seconds"):
        value = stage.get(key)
        if (isinstance(value, bool) or not isinstance(value, (int, float)) or
                not math.isfinite(value) or value < 0):
            raise FixedDyadicError(f"invalid I-stage timing at {key}")
    for key in ("i_peak_rss_kib_linux", "i_child_peak_rss_kib_linux"):
        value = stage.get(key)
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise FixedDyadicError(f"invalid I-stage resource value at {key}")
    denominator = interval_from_data(stage["I"], "I")
    if denominator.lo <= 0:
        raise FixedDyadicError("staged I is not strictly positive")
    return stage, denominator


def run_j(evaluator, common: dict, input_path: Path, stage_path: Path,
          stage_sha: str, output_path: Path, workers: int, progress: bool):
    stage, denominator = load_stage(stage_path, stage_sha, common, workers)
    driver_sha = sha256(Path(__file__))
    wall, cpu = time.perf_counter(), time.process_time()
    j_value, components, domains = evaluator.evaluate_j(progress, workers)
    wall, cpu = time.perf_counter() - wall, time.process_time() - cpu
    if components != EXPECTED_MARGINAL_COMPONENTS or domains != EXPECTED_J_DOMAINS:
        raise FixedDyadicError("J traversal count mismatch")
    numerator = DyadicInterval(48) * j_value
    margin = numerator - denominator
    quotient = numerator / denominator
    positive = margin.lo > 0
    read_pinned(input_path, common["input_sha256"], "fixed-vector input")
    if (sha256(stage_path) != stage_sha or sha256(Path(__file__)) != driver_sha or
            dependency_snapshot() != common["dependencies"]):
        raise FixedDyadicError("input/stage/checker/dependency changed during J")
    result = {
        "status": ("c10-d12-fixed-vector-rigorous-dyadic-positive-candidate"
                   if positive else
                   "c10-d12-fixed-vector-rigorous-dyadic-nonpositive-result"),
        **common,
        "workers": workers,
        "driver_sha256": driver_sha,
        "i_stage_sha256": stage_sha,
        "I": stage["I"],
        "J": interval_data(j_value),
        "M2": interval_data(numerator),
        "M2_minus_M1": interval_data(margin),
        "quotient": interval_data(quotient),
        "I_strictly_positive": denominator.lo > 0,
        "margin_strictly_positive": positive,
        "acceptance_rule": "I.lo > 0 and (48*J-I).lo > 0",
        "integer_directed_outward_rounding": True,
        "j_marginal_components": components,
        "j_branch_domains": domains,
        "j_wall_seconds": wall,
        "j_cpu_seconds": cpu,
        "j_peak_rss_kib_linux": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "j_child_peak_rss_kib_linux": resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,
        "theorem_ready": False,
        "audit_required": True,
    }
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    expected_output_sha = sha256_bytes(rendered.encode("utf-8"))
    atomic_write(output_path, rendered)
    try:
        read_pinned(input_path, common["input_sha256"], "fixed-vector input")
        if (sha256(stage_path) != stage_sha or
                sha256(output_path) != expected_output_sha or
                sha256(Path(__file__)) != driver_sha or
                dependency_snapshot() != common["dependencies"]):
            raise FixedDyadicError("postwrite closure changed during J")
    except Exception as exc:
        failed_output(output_path, "j", str(exc))
        raise
    return result, positive


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input_json", type=Path)
    parser.add_argument("--expect-input-sha256", required=True)
    parser.add_argument("--phase", choices=("i", "j"), required=True)
    parser.add_argument("--precision", type=int, default=512)
    parser.add_argument("--shadow-bits", type=int, default=96)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--reverse-faces", action="store_true")
    parser.add_argument("--progress", action="store_true")
    parser.add_argument("--stage", type=Path, required=True)
    parser.add_argument("--expected-stage-sha256")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not 256 <= args.precision <= 4096:
        raise FixedDyadicError("precision must lie in [256,4096]")
    if not 32 <= args.shadow_bits <= 512:
        raise FixedDyadicError("shadow bits must lie in [32,512]")
    if not 1 <= args.workers <= 4:
        raise FixedDyadicError("workers must lie in [1,4]")
    if args.reverse_faces and args.workers != 1:
        raise FixedDyadicError("reverse-r traversal requires one worker")
    if args.phase == "j" and not args.expected_stage_sha256:
        raise FixedDyadicError("J phase requires --expected-stage-sha256")
    if args.phase == "i" and args.expected_stage_sha256:
        raise FixedDyadicError("I phase must not receive a stage SHA")
    validate_paths(args.input_json, args.stage, args.output)
    # Replace a stale success before any input parsing or expensive work.  A
    # failed or interrupted invocation therefore leaves an unmistakable
    # non-certificate sentinel at the destination relevant to this phase.
    sentinel_path = args.stage if args.phase == "i" else args.output
    atomic_write(sentinel_path, json.dumps({
        "status": "incomplete-fixed-vector-dyadic-invocation",
        "phase": args.phase,
        "theorem_ready": False,
        "expected_input_sha256": args.expect_input_sha256,
    }, indent=2, sort_keys=True) + "\n")
    evaluator, common = prepare(
        args.input_json, args.expect_input_sha256, args.precision,
        args.shadow_bits, args.reverse_faces)
    if args.phase == "i":
        _, stage_sha = run_i(
            evaluator, common, args.input_json, args.stage,
            args.workers, args.progress)
        print(json.dumps({"status": "I complete", "stage": str(args.stage),
                          "stage_sha256": stage_sha}, indent=2))
        return 0
    result, positive = run_j(
        evaluator, common, args.input_json, args.stage,
        args.expected_stage_sha256,
        args.output, args.workers, args.progress)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if positive else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (FixedDyadicError, CertificateError, ArithmeticError,
            OSError, TypeError, ValueError, ZeroDivisionError) as exc:
        print(f"CHECK FAILED: {exc}", file=sys.stderr)
        raise SystemExit(2)
