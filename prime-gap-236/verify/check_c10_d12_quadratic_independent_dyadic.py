#!/usr/bin/env python3
"""Staged independent dyadic checker for the C10 D12 quadratic candidate.

This driver reconstructs the pinned 272-term integer-scaled base from its
original rational source, parses the pinned exact six-channel multiplier,
clears its denominators by one global scale, encloses coefficient leaves in
the audited fixed-point interval ring, and invokes the separate tagged
quadratic recurrence.  It consumes no Decimal producer output, matrices,
eigenvalues, or persistent moment cache.

The target traversal must not be launched unless the separate Decimal
discovery run reports a positive sign.  Even a positive output from this
driver remains a candidate until the driver and output receive a final
independent audit.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import resource
import sys
import time
from fractions import Fraction
from pathlib import Path

if hasattr(sys, "set_int_max_str_digits"):
    sys.set_int_max_str_digits(0)

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))

from verify.dyadic_interval import DyadicInterval  # noqa: E402
from verify.exact_capped_certificate import (  # noqa: E402
    CertificateError,
    TARGET_C10_D12,
    TARGET_ORDERED_PAYLOAD_SHA256,
    _reject_constant,
    _reject_duplicate_object,
    build_basis_terms,
    expected_labels,
    ordered_payload_sha256,
    parse_fraction,
    validate_parameters,
)
from verify.exact_quadratic_multiplier import (  # noqa: E402
    QuadraticMultipliers,
    compute_i_quadratic_tagged,
    compute_j_quadratic_tagged,
    load_exact_quadratic_multiplier,
)


BASE_PATH = (ROOT / "agents/exact-integrator/results/"
             "hb_c10_fullsimplex_noones_D12_integer_scaled.json")
SOURCE_PATH = (ROOT / "agents/exact-integrator/results/"
               "hb_c10_fullsimplex_noones_D12.json")
QUADRATIC_PATH = (ROOT / "agents/exact-integrator/results/"
                  "c10_stratum_quadratic_cappedopt_D4_exact.json")
BASE_SHA256 = "8650e44cace6b6d3e4eee8e1632cfd8a59cde6a48f76a8763dcfb400e49f4a93"
SOURCE_SHA256 = "719c656e6e45388273b4c27f51f7a18b33e9ed1abb5f883e6fcc5de5d6d64a87"
QUADRATIC_SHA256 = "fbc8c38d2cf4241fdba03beb4251e2692e96af01ad4918c9a3a1075af2ed6e86"
SOURCE_METADATA_PATH = "results/hb_c10_fullsimplex_noones_D12.json"
DEPENDENCY_SHAS = {
    ROOT / "verify/dyadic_interval.py":
        "f6f1730f77ba490f04326338e7b3bfe5ab2e5c6438f10892bdf3f5bfe6fc875d",
    ROOT / "verify/exact_affine_multiplier.py":
        "9c21d73af25f63ad16c62a2a1935a9cfd3a8d134d7b7ada2620eddc12e1c3d3e",
    ROOT / "verify/exact_capped_certificate.py":
        "1787e7b482a5c2982de56486bc774794f6e671b3db4d9ab7207ebb1c85dc079c",
    ROOT / "verify/exact_quadratic_multiplier.py":
        "096bba04401b4d5241229bcd3c5332ca3ec13e825f692c09618f8c4469be5123",
}
EXPECTED_ACTIVE_I_FACES = 16
EXPECTED_ACTIVE_J_FACES = 16
EXPECTED_QUADRATIC_LABELS = 96
EXPECTED_EFFECTIVE_LABELS = 93


class IndependentQuadraticDyadicError(RuntimeError):
    pass


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_pinned(path: Path, expected: str, description: str) -> bytes:
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise IndependentQuadraticDyadicError(
            f"cannot read {description}: {exc}") from exc
    if len(raw) > 20_000_000:
        raise IndependentQuadraticDyadicError(f"{description} exceeds 20 MB")
    actual = hashlib.sha256(raw).hexdigest()
    if actual != expected:
        raise IndependentQuadraticDyadicError(
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
        raise IndependentQuadraticDyadicError(
            f"malformed {description}: {exc}") from exc
    if not isinstance(value, dict):
        raise IndependentQuadraticDyadicError(f"{description} is not an object")
    return value


def dependency_snapshot() -> dict[str, str]:
    answer = {}
    for path, expected in DEPENDENCY_SHAS.items():
        read_pinned(path, expected, str(path.relative_to(ROOT)))
        answer[str(path.relative_to(ROOT))] = expected
    return answer


def parse_labels(raw_labels) -> list[tuple[int, tuple[int, ...]]]:
    if not isinstance(raw_labels, list):
        raise IndependentQuadraticDyadicError("base basis is not a list")
    labels = []
    for index, label in enumerate(raw_labels):
        if (not isinstance(label, list) or len(label) != 2 or
                isinstance(label[0], bool) or not isinstance(label[0], int) or
                not isinstance(label[1], list) or
                any(isinstance(value, bool) or not isinstance(value, int)
                    for value in label[1])):
            raise IndependentQuadraticDyadicError(
                f"malformed basis label {index}")
        residual = label[0]
        part = tuple(label[1])
        if (residual < 0 or tuple(sorted(part, reverse=True)) != part or
                any(value < 2 for value in part) or
                residual + sum(part) > TARGET_C10_D12.degree):
            raise IndependentQuadraticDyadicError(
                f"noncanonical/out-of-degree basis label {index}")
        labels.append((residual, part))
    if len(labels) != 272 or len(set(labels)) != len(labels):
        raise IndependentQuadraticDyadicError(
            "base basis dimension/uniqueness failed")
    if set(labels) != expected_labels(TARGET_C10_D12.degree,
                                      TARGET_C10_D12.k):
        raise IndependentQuadraticDyadicError(
            "base basis is not complete through D12")
    return labels


def lcm_denominators(values) -> int:
    answer = 1
    for value in values:
        if not isinstance(value, Fraction):
            raise IndependentQuadraticDyadicError("LCM input is not exact")
        answer = math.lcm(answer, value.denominator)
    return answer


def load_scaled_inputs():
    """Reconstruct both global integer scalings from pinned rational data."""
    validate_parameters(TARGET_C10_D12)
    source = strict_json(
        read_pinned(SOURCE_PATH, SOURCE_SHA256, "original D12 source"),
        "original D12 source")
    if not {"k", "degree", "basis_dimension", "basis",
            "rational_vector"}.issubset(source):
        raise IndependentQuadraticDyadicError(
            "original D12 source fields are incomplete")
    if (source.get("k") != 48 or source.get("degree") != 12 or
            source.get("basis_dimension") != 272):
        raise IndependentQuadraticDyadicError(
            "original D12 source metadata mismatch")
    if ordered_payload_sha256(source) != TARGET_ORDERED_PAYLOAD_SHA256:
        raise IndependentQuadraticDyadicError(
            "original ordered D12 payload mismatch")
    source_labels = parse_labels(source.get("basis"))
    raw_source_coefficients = source.get("rational_vector")
    if (not isinstance(raw_source_coefficients, list) or
            len(raw_source_coefficients) != 272):
        raise IndependentQuadraticDyadicError(
            "original D12 vector length mismatch")
    source_coefficients = [
        parse_fraction(value, f"source rational_vector[{index}]")
        for index, value in enumerate(raw_source_coefficients)]

    base = strict_json(read_pinned(BASE_PATH, BASE_SHA256, "integer D12 base"),
                       "integer D12 base")
    expected_base_keys = {"status", "k", "degree", "basis_dimension",
                          "basis", "rational_vector", "integer_scaling"}
    if (set(base) != expected_base_keys or
            base.get("status") != "exact-integer-scaled-fixed-vector-input" or
            base.get("k") != 48 or base.get("degree") != 12 or
            base.get("basis_dimension") != 272):
        raise IndependentQuadraticDyadicError("integer D12 metadata mismatch")
    scaling = base.get("integer_scaling")
    expected_scaling_keys = {
        "source_json", "source_sha256", "least_common_denominator",
        "form_scale", "quotient_and_margin_sign_preserved",
    }
    if (not isinstance(scaling, dict) or set(scaling) != expected_scaling_keys or
            scaling.get("source_json") != SOURCE_METADATA_PATH or
            scaling.get("source_sha256") != SOURCE_SHA256 or
            scaling.get("form_scale") != "least_common_denominator^2" or
            scaling.get("quotient_and_margin_sign_preserved") is not True):
        raise IndependentQuadraticDyadicError(
            "integer D12 scaling metadata mismatch")
    labels = parse_labels(base.get("basis"))
    if labels != source_labels:
        raise IndependentQuadraticDyadicError(
            "integer/source ordered basis mismatch")
    raw_coefficients = base.get("rational_vector")
    if not isinstance(raw_coefficients, list) or len(raw_coefficients) != 272:
        raise IndependentQuadraticDyadicError("integer D12 vector malformed")
    coefficients = [parse_fraction(value, f"base rational_vector[{index}]")
                    for index, value in enumerate(raw_coefficients)]
    if any(value.denominator != 1 for value in coefficients):
        raise IndependentQuadraticDyadicError(
            "integer D12 coefficients are not integers")
    raw_base_lcm = scaling.get("least_common_denominator")
    if (not isinstance(raw_base_lcm, str) or not raw_base_lcm.isdigit() or
            raw_base_lcm.startswith("0")):
        raise IndependentQuadraticDyadicError("noncanonical base LCM")
    base_lcm = int(raw_base_lcm)
    reconstructed_base_lcm = lcm_denominators(source_coefficients)
    if base_lcm != reconstructed_base_lcm:
        raise IndependentQuadraticDyadicError("base LCM reconstruction failed")
    for index, (source_value, integer_value) in enumerate(
            zip(source_coefficients, coefficients, strict=True)):
        if source_value * base_lcm != integer_value:
            raise IndependentQuadraticDyadicError(
                f"integer base mismatch at coefficient {index}")
    content = 0
    for value in coefficients:
        content = math.gcd(content, abs(value.numerator))
    if content != 1:
        raise IndependentQuadraticDyadicError(
            f"integer base is not primitive (content {content})")

    quadratic = load_exact_quadratic_multiplier(
        QUADRATIC_PATH, TARGET_C10_D12, QUADRATIC_SHA256)
    if len(quadratic.coefficients) * 6 != EXPECTED_QUADRATIC_LABELS:
        raise IndependentQuadraticDyadicError(
            "quadratic multiplier label count mismatch")
    effective_values = [value for row in quadratic.coefficients for value in row]
    if sum(value != 0 for value in effective_values) != EXPECTED_EFFECTIVE_LABELS:
        raise IndependentQuadraticDyadicError(
            "quadratic effective-coordinate count mismatch")
    quadratic_lcm = lcm_denominators(effective_values)
    integer_rows = tuple(tuple(value * quadratic_lcm for value in row)
                         for row in quadratic.coefficients)
    if any(value.denominator != 1
           for row in integer_rows for value in row):
        raise IndependentQuadraticDyadicError("quadratic LCM scaling failed")
    multiplier_content = 0
    for row in integer_rows:
        for value in row:
            multiplier_content = math.gcd(multiplier_content,
                                          abs(value.numerator))
    if multiplier_content != 1:
        raise IndependentQuadraticDyadicError(
            f"integer quadratic multiplier is not primitive "
            f"(content {multiplier_content})")
    integer_quadratic = QuadraticMultipliers(
        integer_rows, source_sha256=QUADRATIC_SHA256)
    integer_quadratic.validate_for(TARGET_C10_D12)
    return (build_basis_terms(labels, coefficients), integer_quadratic,
            quadratic_lcm, base_lcm)


def active_face_counts() -> tuple[int, int]:
    params = TARGET_C10_D12
    i_faces = sum(
        params.alpha - r * params.delta > 0 and
        (r == 0 or params.beta(r) - r * params.delta > 0)
        for r in range(params.k + 1))
    j_faces = 0
    for r in range(params.k):
        if params.eta - r * params.delta <= 0:
            continue
        small = r == 0 or params.beta(r) - r * params.delta > 0
        large = params.beta(r + 1) - (r + 1) * params.delta > 0
        if small or large:
            j_faces += 1
    return i_faces, j_faces


def intervalize(precision: int, shadow_bits: int):
    DyadicInterval.configure(precision, shadow_bits)
    exact_terms, exact_quadratic, quadratic_lcm, base_lcm = load_scaled_inputs()
    terms = {label: DyadicInterval(value)
             for label, value in exact_terms.items()}
    quadratic = QuadraticMultipliers(tuple(
        tuple(DyadicInterval(value) for value in row)
        for row in exact_quadratic.coefficients),
        source_sha256=exact_quadratic.source_sha256)
    quadratic.validate_for(TARGET_C10_D12)
    faces = active_face_counts()
    if faces != (EXPECTED_ACTIVE_I_FACES, EXPECTED_ACTIVE_J_FACES):
        raise IndependentQuadraticDyadicError(
            f"active-face mismatch: expected (16,16), got {faces}")
    return terms, quadratic, quadratic_lcm, base_lcm, faces


def interval_data(value: DyadicInterval) -> dict:
    if not isinstance(value, DyadicInterval):
        raise IndependentQuadraticDyadicError("computed value is not dyadic")
    return {
        "precision_bits": DyadicInterval.PRECISION,
        "lo_integer": str(value.lo),
        "hi_integer": str(value.hi),
        "lower_fraction": str(value.lower_fraction()),
        "upper_fraction": str(value.upper_fraction()),
        "width_units": value.width_units(),
    }


def interval_from_data(raw, precision: int, description: str):
    expected = {"precision_bits", "lo_integer", "hi_integer",
                "lower_fraction", "upper_fraction", "width_units"}
    if not isinstance(raw, dict) or set(raw) != expected:
        raise IndependentQuadraticDyadicError(f"malformed staged {description}")
    if raw.get("precision_bits") != precision:
        raise IndependentQuadraticDyadicError(
            f"staged {description} precision mismatch")
    try:
        lo = int(raw["lo_integer"])
        hi = int(raw["hi_integer"])
    except (TypeError, ValueError) as exc:
        raise IndependentQuadraticDyadicError(
            f"invalid staged {description} endpoints") from exc
    if str(lo) != raw["lo_integer"] or str(hi) != raw["hi_integer"]:
        raise IndependentQuadraticDyadicError(
            f"noncanonical staged {description} endpoints")
    width = raw.get("width_units")
    if (isinstance(width, bool) or not isinstance(width, int) or width < 0 or
            hi - lo != width):
        raise IndependentQuadraticDyadicError(
            f"staged {description} width mismatch")
    value = DyadicInterval._from_bounds(lo, hi)
    if (str(value.lower_fraction()) != raw.get("lower_fraction") or
            str(value.upper_fraction()) != raw.get("upper_fraction")):
        raise IndependentQuadraticDyadicError(
            f"staged {description} endpoint fractions mismatch")
    return value


def common_metadata(dependencies, precision, shadow_bits, quadratic_lcm,
                    base_lcm, reverse_faces, faces):
    return {
        "scope": "independent tagged C10 D12 quadratic dyadic enclosure",
        "k": 48,
        "degree_of_base": 12,
        "base_dimension": 272,
        "quadratic_channels": ["1", "L", "Z", "L^2", "LZ", "Z^2"],
        "quadratic_channel_powers": [[0, 0], [1, 0], [0, 1],
                                     [2, 0], [1, 1], [0, 2]],
        "quadratic_label_count": EXPECTED_QUADRATIC_LABELS,
        "quadratic_effective_label_count": EXPECTED_EFFECTIVE_LABELS,
        "discarded_identically_zero_labels": [[0, "L"], [0, "L^2"],
                                               [0, "LZ"]],
        "base_path": str(BASE_PATH.relative_to(ROOT)),
        "base_sha256": BASE_SHA256,
        "original_source_path": str(SOURCE_PATH.relative_to(ROOT)),
        "original_source_sha256": SOURCE_SHA256,
        "original_ordered_payload_sha256": TARGET_ORDERED_PAYLOAD_SHA256,
        "quadratic_path": str(QUADRATIC_PATH.relative_to(ROOT)),
        "quadratic_sha256": QUADRATIC_SHA256,
        "reconstructed_base_lcm": str(base_lcm),
        "reconstructed_base_lcm_bits": base_lcm.bit_length(),
        "reconstructed_quadratic_lcm": str(quadratic_lcm),
        "reconstructed_quadratic_lcm_bits": quadratic_lcm.bit_length(),
        "global_function_scale_note": (
            "base and the whole six-channel multiplier are independently "
            "scaled by global LCMs; quotient and margin sign are invariant"),
        "parameters": {
            "alpha": str(TARGET_C10_D12.alpha),
            "eta": str(TARGET_C10_D12.eta),
            "delta": str(TARGET_C10_D12.delta),
            "beta1": str(TARGET_C10_D12.beta1),
            "beta2": str(TARGET_C10_D12.beta2),
            "beta3plus": str(TARGET_C10_D12.beta3plus),
        },
        "precision_bits": precision,
        "shadow_bits": shadow_bits,
        "reverse_faces": reverse_faces,
        "active_i_faces": faces[0],
        "active_j_faces": faces[1],
        "ordered_j_branch_slots_per_face": 16,
        "matrix_entries_consumed": False,
        "decimal_integrals_consumed": False,
        "persistent_moment_cache_consumed": False,
        "dependency_sha256": dependencies,
    }


def atomic_json(path: Path, payload: dict) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + f".tmp.{os.getpid()}")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n",
                         encoding="utf-8")
    os.replace(temporary, path)
    return sha256(path)


def reread_inputs() -> None:
    read_pinned(SOURCE_PATH, SOURCE_SHA256, "original D12 source")
    read_pinned(BASE_PATH, BASE_SHA256, "integer D12 base")
    read_pinned(QUADRATIC_PATH, QUADRATIC_SHA256, "quadratic multiplier")


def run_i(terms, quadratic, common, stage_path, reverse_faces):
    self_hash = sha256(Path(__file__))
    started = time.perf_counter()
    denominator = compute_i_quadratic_tagged(
        terms, TARGET_C10_D12, quadratic,
        reverse_faces=reverse_faces, workers=1)
    wall = time.perf_counter() - started
    if not isinstance(denominator, DyadicInterval) or denominator.lo <= 0:
        raise IndependentQuadraticDyadicError(
            "I enclosure is not strictly positive")
    if sha256(Path(__file__)) != self_hash:
        raise IndependentQuadraticDyadicError("driver changed during I stage")
    if dependency_snapshot() != common["dependency_sha256"]:
        raise IndependentQuadraticDyadicError(
            "dependency changed during I stage")
    reread_inputs()
    payload = {
        "status": "c10-d12-quadratic-independent-dyadic-i-stage",
        **common,
        "driver_sha256": self_hash,
        "I": interval_data(denominator),
        "I_strictly_positive": True,
        "i_wall_seconds": wall,
        "i_peak_rss_kib_linux": int(resource.getrusage(
            resource.RUSAGE_SELF).ru_maxrss),
    }
    return payload, atomic_json(stage_path, payload)


def load_stage(stage_path, expected_sha, common):
    if (not isinstance(expected_sha, str) or len(expected_sha) != 64 or
            any(character not in "0123456789abcdef"
                for character in expected_sha)):
        raise IndependentQuadraticDyadicError("invalid I-stage SHA")
    stage = strict_json(
        read_pinned(stage_path, expected_sha, "I stage"), "I stage")
    expected_keys = {"status", *common.keys(), "driver_sha256", "I",
                     "I_strictly_positive", "i_wall_seconds",
                     "i_peak_rss_kib_linux"}
    if set(stage) != expected_keys:
        raise IndependentQuadraticDyadicError("I-stage field set mismatch")
    if stage.get("status") != "c10-d12-quadratic-independent-dyadic-i-stage":
        raise IndependentQuadraticDyadicError("I-stage status mismatch")
    for key, value in common.items():
        if stage.get(key) != value:
            raise IndependentQuadraticDyadicError(
                f"I-stage metadata mismatch at {key}")
    if stage.get("driver_sha256") != sha256(Path(__file__)):
        raise IndependentQuadraticDyadicError("I-stage driver SHA mismatch")
    denominator = interval_from_data(
        stage.get("I"), common["precision_bits"], "I")
    if stage.get("I_strictly_positive") is not True or denominator.lo <= 0:
        raise IndependentQuadraticDyadicError("staged I is not positive")
    return stage, denominator


def run_j(terms, quadratic, common, stage_path, expected_sha, output_path,
          reverse_faces):
    self_hash = sha256(Path(__file__))
    stage, denominator = load_stage(stage_path, expected_sha, common)
    started = time.perf_counter()
    j_value = compute_j_quadratic_tagged(
        terms, TARGET_C10_D12, quadratic,
        reverse_faces=reverse_faces, workers=1)
    wall = time.perf_counter() - started
    numerator = DyadicInterval(48) * j_value
    margin = numerator - denominator
    quotient = numerator / denominator
    positive = denominator.lo > 0 and margin.lo > 0
    if sha256(Path(__file__)) != self_hash:
        raise IndependentQuadraticDyadicError("driver changed during J stage")
    if dependency_snapshot() != common["dependency_sha256"]:
        raise IndependentQuadraticDyadicError(
            "dependency changed during J stage")
    read_pinned(stage_path, expected_sha, "I stage")
    reread_inputs()
    payload = {
        "status": ("c10-d12-quadratic-independent-dyadic-positive-candidate"
                   if positive else
                   "c10-d12-quadratic-independent-dyadic-nonpositive-result"),
        **common,
        "driver_sha256": self_hash,
        "i_stage_path": str(stage_path),
        "i_stage_sha256": expected_sha,
        "I": interval_data(denominator),
        "M2": interval_data(numerator),
        "M2_minus_M1": interval_data(margin),
        "quotient": interval_data(quotient),
        "I_strictly_positive": denominator.lo > 0,
        "margin_strictly_positive": positive,
        "acceptance_rule": "I.lo > 0 and (48*J-I).lo > 0",
        "integer_directed_outward_rounding": True,
        "j_wall_seconds": wall,
        "j_peak_rss_kib_linux": int(resource.getrusage(
            resource.RUSAGE_SELF).ru_maxrss),
        "i_wall_seconds": stage["i_wall_seconds"],
        "theorem_ready": False,
        "theorem_ready_reason": (
            "target launch is discovery-sign gated; driver/output and final "
            "end-to-end analytic audits remain"),
    }
    atomic_json(output_path, payload)
    return payload, positive


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=("i", "j", "all"), default="all")
    parser.add_argument("--stage", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--expected-stage-sha256")
    parser.add_argument("--precision", type=int, default=512)
    parser.add_argument("--shadow-bits", type=int, default=96)
    parser.add_argument("--reverse-faces", action="store_true")
    return parser.parse_args()


def validate_options(args) -> None:
    if not 128 <= args.precision <= 4096:
        raise IndependentQuadraticDyadicError(
            "precision must be in [128,4096]")
    if not 8 <= args.shadow_bits <= 512:
        raise IndependentQuadraticDyadicError(
            "shadow bits must be in [8,512]")
    protected = {
        Path(__file__).resolve(), SOURCE_PATH.resolve(), BASE_PATH.resolve(),
        QUADRATIC_PATH.resolve(), *(path.resolve() for path in DEPENDENCY_SHAS),
    }
    stage = args.stage.resolve(strict=False)
    output = args.output.resolve(strict=False)
    if stage == output:
        raise IndependentQuadraticDyadicError(
            "stage and output paths must differ")
    if stage in protected or output in protected:
        raise IndependentQuadraticDyadicError(
            "output path collides with pinned input")
    if args.phase == "j" and not args.expected_stage_sha256:
        raise IndependentQuadraticDyadicError(
            "J phase requires --expected-stage-sha256")
    if args.phase != "j" and args.expected_stage_sha256:
        raise IndependentQuadraticDyadicError(
            "expected stage SHA is only accepted in J phase")


def main() -> int:
    args = parse_args()
    validate_options(args)
    dependencies = dependency_snapshot()
    terms, quadratic, quadratic_lcm, base_lcm, faces = intervalize(
        args.precision, args.shadow_bits)
    common = common_metadata(
        dependencies, args.precision, args.shadow_bits, quadratic_lcm,
        base_lcm, args.reverse_faces, faces)
    if args.phase == "i":
        _, stage_sha = run_i(
            terms, quadratic, common, args.stage, args.reverse_faces)
        print(f"I_STAGE_SHA256={stage_sha}")
        return 0
    if args.phase == "j":
        _, positive = run_j(
            terms, quadratic, common, args.stage,
            args.expected_stage_sha256, args.output, args.reverse_faces)
        return 0 if positive else 1
    _, stage_sha = run_i(
        terms, quadratic, common, args.stage, args.reverse_faces)
    _, positive = run_j(
        terms, quadratic, common, args.stage, stage_sha,
        args.output, args.reverse_faces)
    return 0 if positive else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (IndependentQuadraticDyadicError, CertificateError,
            ArithmeticError, ValueError, OSError) as exc:
        print(f"FAIL CLOSED: {exc}", file=sys.stderr)
        raise SystemExit(2)
