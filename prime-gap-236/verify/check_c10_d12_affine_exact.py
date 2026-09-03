#!/usr/bin/env python3
"""Staged cache-free exact checker for the transferred C10 D12 candidate.

The candidate function is the pinned 272-term symmetric polynomial ``F0``
multiplied, on the stratum having ``R`` coordinates above ``delta``, by

    a_R + b_R L + c_R Z.

Only the two pinned coefficient files are consumed.  Matrix entries,
discovery integrals, Decimal values, eigenvalues, and persistent moment caches
are neither read nor trusted.  The base and effective affine coefficients are
cleared of denominators independently before exact integration; this applies
one nonzero global scale to the function and therefore preserves the quotient
and the sign of ``48*J-I``.

This driver is prepared but must not be described as a certificate until a
complete positive output has been independently audited.  Its I stage is
byte-SHA bound to all inputs and arithmetic dependencies, so a J-only resume
fails closed after any change.
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
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from verify.exact_affine_multiplier import (  # noqa: E402
    AffineMultipliers,
    compute_i_affine_tagged,
    load_exact_affine_multiplier,
)
from verify.exact_affine_multiplier_batched import (  # noqa: E402
    compute_j_affine_tagged_batched,
)
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


BASE_PATH = (ROOT / "agents/exact-integrator/results/"
             "hb_c10_fullsimplex_noones_D12_integer_scaled.json")
SOURCE_PATH = (ROOT / "agents/exact-integrator/results/"
               "hb_c10_fullsimplex_noones_D12.json")
AFFINE_PATH = (ROOT / "agents/exact-integrator/results/"
               "c10_stratum_linear_cappedopt_D4_exact.json")
BASE_SHA256 = "8650e44cace6b6d3e4eee8e1632cfd8a59cde6a48f76a8763dcfb400e49f4a93"
AFFINE_SHA256 = "ffa607e0f2a8a3b6648f248efb13dc7ac2f1e7ef5809771f31c5f04b30f53158"
SOURCE_VECTOR_SHA256 = \
    "719c656e6e45388273b4c27f51f7a18b33e9ed1abb5f883e6fcc5de5d6d64a87"
SOURCE_METADATA_PATH = "results/hb_c10_fullsimplex_noones_D12.json"
LINEAR_CUTOFF = 11
DEPENDENCY_SHAS = {
    ROOT / "verify/exact_affine_multiplier.py":
        "9c21d73af25f63ad16c62a2a1935a9cfd3a8d134d7b7ada2620eddc12e1c3d3e",
    ROOT / "verify/exact_affine_multiplier_batched.py":
        "d824ab8ebb59da4cd94da7b17350c36ba5888bc2260fdeb8e976f4f825405ee8",
    ROOT / "verify/exact_capped_certificate.py":
        "1787e7b482a5c2982de56486bc774794f6e671b3db4d9ab7207ebb1c85dc079c",
}


class ExactAffineCertificateError(RuntimeError):
    pass


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_pinned(path: Path, expected: str, description: str) -> bytes:
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise ExactAffineCertificateError(
            f"cannot read {description}: {exc}") from exc
    if len(raw) > 20_000_000:
        raise ExactAffineCertificateError(f"{description} exceeds 20 MB")
    actual = hashlib.sha256(raw).hexdigest()
    if actual != expected:
        raise ExactAffineCertificateError(
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
        raise ExactAffineCertificateError(
            f"malformed {description}: {exc}") from exc
    if not isinstance(value, dict):
        raise ExactAffineCertificateError(f"{description} is not an object")
    return value


def dependency_snapshot() -> dict[str, str]:
    answer = {}
    for path, expected in DEPENDENCY_SHAS.items():
        read_pinned(path, expected, str(path.relative_to(ROOT)))
        answer[str(path.relative_to(ROOT))] = expected
    return answer


def parse_labels(raw_labels) -> list[tuple[int, tuple[int, ...]]]:
    if not isinstance(raw_labels, list):
        raise ExactAffineCertificateError("base basis is not a list")
    labels = []
    for index, label in enumerate(raw_labels):
        if (not isinstance(label, list) or len(label) != 2 or
                isinstance(label[0], bool) or not isinstance(label[0], int) or
                not isinstance(label[1], list) or
                any(isinstance(value, bool) or not isinstance(value, int)
                    for value in label[1])):
            raise ExactAffineCertificateError(f"malformed basis label {index}")
        residual = label[0]
        part = tuple(label[1])
        if (residual < 0 or tuple(sorted(part, reverse=True)) != part or
                any(value < 2 for value in part) or
                residual + sum(part) > TARGET_C10_D12.degree):
            raise ExactAffineCertificateError(
                f"noncanonical/out-of-degree basis label {index}")
        labels.append((residual, part))
    if len(labels) != 272 or len(set(labels)) != len(labels):
        raise ExactAffineCertificateError("base basis dimension/uniqueness failed")
    if set(labels) != expected_labels(TARGET_C10_D12.degree,
                                      TARGET_C10_D12.k):
        raise ExactAffineCertificateError("base basis is not complete through D12")
    return labels


def lcm_denominators(values) -> int:
    answer = 1
    for value in values:
        if not isinstance(value, Fraction):
            raise ExactAffineCertificateError("LCM input is not exact")
        answer = math.lcm(answer, value.denominator)
    return answer


def load_scaled_inputs():
    validate_parameters(TARGET_C10_D12)
    source = strict_json(
        read_pinned(SOURCE_PATH, SOURCE_VECTOR_SHA256, "original D12 source"),
        "original D12 source")
    required_source = {"k", "degree", "basis_dimension", "basis",
                       "rational_vector"}
    if not required_source.issubset(source):
        raise ExactAffineCertificateError(
            "original D12 source fields are incomplete")
    if (source.get("k") != 48 or source.get("degree") != 12 or
            source.get("basis_dimension") != 272):
        raise ExactAffineCertificateError(
            "original D12 source metadata mismatch")
    if ordered_payload_sha256(source) != TARGET_ORDERED_PAYLOAD_SHA256:
        raise ExactAffineCertificateError(
            "original ordered D12 label/vector payload mismatch")
    source_labels = parse_labels(source.get("basis"))
    raw_source_coefficients = source.get("rational_vector")
    if (not isinstance(raw_source_coefficients, list) or
            len(raw_source_coefficients) != 272):
        raise ExactAffineCertificateError(
            "original D12 vector length mismatch")
    source_coefficients = [
        parse_fraction(value, f"source rational_vector[{index}]")
        for index, value in enumerate(raw_source_coefficients)
    ]

    base = strict_json(read_pinned(BASE_PATH, BASE_SHA256, "D12 base"),
                       "D12 base")
    if (set(base) != {"status", "k", "degree", "basis_dimension",
                     "basis", "rational_vector", "integer_scaling"} or
            base.get("status") != "exact-integer-scaled-fixed-vector-input" or
            base.get("k") != 48 or base.get("degree") != 12 or
            base.get("basis_dimension") != 272):
        raise ExactAffineCertificateError("D12 base metadata mismatch")
    scaling = base.get("integer_scaling")
    expected_scaling_keys = {
        "source_json", "source_sha256", "least_common_denominator",
        "form_scale", "quotient_and_margin_sign_preserved",
    }
    if (not isinstance(scaling, dict) or set(scaling) != expected_scaling_keys or
            scaling.get("source_json") != SOURCE_METADATA_PATH or
            scaling.get("source_sha256") != SOURCE_VECTOR_SHA256 or
            scaling.get("form_scale") != "least_common_denominator^2" or
            scaling.get("quotient_and_margin_sign_preserved") is not True):
        raise ExactAffineCertificateError("D12 base scaling metadata mismatch")
    labels = parse_labels(base.get("basis"))
    if labels != source_labels:
        raise ExactAffineCertificateError("scaled/source ordered basis mismatch")
    raw_coefficients = base.get("rational_vector")
    if not isinstance(raw_coefficients, list) or len(raw_coefficients) != 272:
        raise ExactAffineCertificateError("D12 base vector length mismatch")
    coefficients = [
        parse_fraction(value, f"base rational_vector[{index}]")
        for index, value in enumerate(raw_coefficients)
    ]
    if any(value.denominator != 1 for value in coefficients):
        raise ExactAffineCertificateError("D12 input coefficients are not integers")
    if not any(coefficients):
        raise ExactAffineCertificateError("D12 base polynomial is zero")
    raw_base_lcm = scaling.get("least_common_denominator")
    if (not isinstance(raw_base_lcm, str) or not raw_base_lcm.isdigit() or
            raw_base_lcm.startswith("0")):
        raise ExactAffineCertificateError("noncanonical base-vector LCM")
    base_lcm = int(raw_base_lcm)
    reconstructed_lcm = lcm_denominators(source_coefficients)
    if base_lcm != reconstructed_lcm:
        raise ExactAffineCertificateError("base-vector LCM was not reconstructed")
    for index, (source_value, scaled_value) in enumerate(
            zip(source_coefficients, coefficients, strict=True)):
        if source_value * reconstructed_lcm != scaled_value:
            raise ExactAffineCertificateError(
                f"scaled base coefficient mismatch at index {index}")
    content = 0
    for value in coefficients:
        content = math.gcd(content, abs(value.numerator))
    if content != 1:
        raise ExactAffineCertificateError(
            f"scaled base vector is not primitive (content {content})")

    affine = load_exact_affine_multiplier(
        AFFINE_PATH,
        TARGET_C10_D12,
        AFFINE_SHA256,
        linear_cutoff=LINEAR_CUTOFF,
    )
    effective = [value for triple in affine.coefficients for value in triple]
    affine_lcm = lcm_denominators(effective)
    integer_triples = tuple(
        tuple(value * affine_lcm for value in triple)
        for triple in affine.coefficients
    )
    if any(value.denominator != 1
           for triple in integer_triples for value in triple):
        raise ExactAffineCertificateError("affine LCM scaling failed")
    integer_affine = AffineMultipliers(
        integer_triples,
        source_sha256=AFFINE_SHA256,
        linear_cutoff=LINEAR_CUTOFF,
    )
    integer_affine.validate_for(TARGET_C10_D12)
    return (build_basis_terms(labels, coefficients), integer_affine,
            affine_lcm, reconstructed_lcm)


def common_metadata(dependencies: dict[str, str], affine_lcm: int,
                    base_lcm: int,
                    reverse_faces: bool, workers: int) -> dict:
    return {
        "scope": "C10 D12 transferred-affine exact reconstruction",
        "k": 48,
        "degree_of_base": 12,
        "base_dimension": 272,
        "linear_cutoff": LINEAR_CUTOFF,
        "base_path": str(BASE_PATH.relative_to(ROOT)),
        "base_sha256": BASE_SHA256,
        "original_source_path": str(SOURCE_PATH.relative_to(ROOT)),
        "original_source_sha256": SOURCE_VECTOR_SHA256,
        "original_ordered_payload_sha256": TARGET_ORDERED_PAYLOAD_SHA256,
        "source_vector_sha256": SOURCE_VECTOR_SHA256,
        "reconstructed_base_lcm": str(base_lcm),
        "reconstructed_base_lcm_bits": base_lcm.bit_length(),
        "affine_path": str(AFFINE_PATH.relative_to(ROOT)),
        "affine_sha256": AFFINE_SHA256,
        "effective_affine_lcm": str(affine_lcm),
        "effective_affine_lcm_bits": affine_lcm.bit_length(),
        "global_function_scale_note": (
            "base file is already globally integer-scaled; affine table is "
            "additionally scaled by effective_affine_lcm"
        ),
        "quotient_and_margin_sign_invariant_under_scaling": True,
        "parameters": {
            "alpha": str(TARGET_C10_D12.alpha),
            "eta": str(TARGET_C10_D12.eta),
            "delta": str(TARGET_C10_D12.delta),
            "beta1": str(TARGET_C10_D12.beta1),
            "beta2": str(TARGET_C10_D12.beta2),
            "beta3plus": str(TARGET_C10_D12.beta3plus),
        },
        "reverse_faces": reverse_faces,
        "workers": workers,
        "dependency_sha256": dependencies,
    }


def atomic_json(path: Path, payload: dict) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + f".tmp.{os.getpid()}")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)
    return sha256(path)


def rss_kib() -> int:
    return int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)


def run_i(stage_path: Path, reverse_faces: bool,
          workers: int) -> tuple[dict, str]:
    self_hash = sha256(Path(__file__))
    dependencies = dependency_snapshot()
    terms, affine, affine_lcm, base_lcm = load_scaled_inputs()
    started_wall = time.perf_counter()
    started_cpu = time.process_time()
    i_value = compute_i_affine_tagged(
        terms, TARGET_C10_D12, affine,
        reverse_faces=reverse_faces, workers=workers)
    wall = time.perf_counter() - started_wall
    cpu = time.process_time() - started_cpu
    if i_value <= 0:
        raise ExactAffineCertificateError("exact I is not positive")
    if sha256(Path(__file__)) != self_hash:
        raise ExactAffineCertificateError("driver changed during I stage")
    if dependency_snapshot() != dependencies:
        raise ExactAffineCertificateError("dependency changed during I stage")
    read_pinned(BASE_PATH, BASE_SHA256, "D12 base")
    read_pinned(SOURCE_PATH, SOURCE_VECTOR_SHA256, "original D12 source")
    read_pinned(AFFINE_PATH, AFFINE_SHA256, "affine multiplier")
    payload = {
        "status": "c10-d12-affine-exact-i-stage",
        **common_metadata(
            dependencies, affine_lcm, base_lcm, reverse_faces, workers),
        "driver_sha256": self_hash,
        "I": str(i_value),
        "I_positive": True,
        "i_wall_seconds": wall,
        "i_cpu_seconds_parent": cpu,
        "i_peak_rss_kib_linux_parent": rss_kib(),
    }
    return payload, atomic_json(stage_path, payload)


def load_stage(stage_path: Path, expected_sha: str, reverse_faces: bool,
               workers: int):
    if (not isinstance(expected_sha, str) or len(expected_sha) != 64 or
            any(character not in "0123456789abcdef" for character in expected_sha)):
        raise ExactAffineCertificateError(
            "J phase requires a lowercase 64-hex I-stage SHA")
    stage = strict_json(read_pinned(stage_path, expected_sha, "I stage"),
                        "I stage")
    if stage.get("status") != "c10-d12-affine-exact-i-stage":
        raise ExactAffineCertificateError("I-stage status mismatch")
    dependencies = dependency_snapshot()
    _, _, affine_lcm, base_lcm = load_scaled_inputs()
    expected_common = common_metadata(
        dependencies, affine_lcm, base_lcm, reverse_faces, workers)
    expected_keys = {
        "status", *expected_common.keys(), "driver_sha256", "I",
        "I_positive", "i_wall_seconds", "i_cpu_seconds_parent",
        "i_peak_rss_kib_linux_parent",
    }
    if set(stage) != expected_keys:
        missing = sorted(expected_keys.difference(stage))
        extra = sorted(set(stage).difference(expected_keys))
        raise ExactAffineCertificateError(
            f"I-stage field set mismatch: missing={missing}, extra={extra}")
    for key, value in expected_common.items():
        if stage.get(key) != value:
            raise ExactAffineCertificateError(
                f"I-stage metadata mismatch at {key}")
    if stage.get("driver_sha256") != sha256(Path(__file__)):
        raise ExactAffineCertificateError("I-stage driver SHA mismatch")
    i_value = parse_fraction(stage.get("I"), "staged I")
    if stage.get("I_positive") is not True or i_value <= 0:
        raise ExactAffineCertificateError("staged I is not positive")
    return stage, i_value, expected_common


def run_j(stage_path: Path, expected_stage_sha: str, output_path: Path,
          reverse_faces: bool, workers: int) -> tuple[dict, bool]:
    self_hash = sha256(Path(__file__))
    stage, i_value, common = load_stage(
        stage_path, expected_stage_sha, reverse_faces, workers)
    terms, affine, _, _ = load_scaled_inputs()
    started_wall = time.perf_counter()
    started_cpu = time.process_time()
    j_value = compute_j_affine_tagged_batched(
        terms, TARGET_C10_D12, affine,
        reverse_faces=reverse_faces, workers=workers)
    wall = time.perf_counter() - started_wall
    cpu = time.process_time() - started_cpu
    kj_value = TARGET_C10_D12.k * j_value
    margin = kj_value - i_value
    quotient = kj_value / i_value
    if sha256(Path(__file__)) != self_hash:
        raise ExactAffineCertificateError("driver changed during J stage")
    if dependency_snapshot() != common["dependency_sha256"]:
        raise ExactAffineCertificateError("dependency changed during J stage")
    read_pinned(stage_path, expected_stage_sha, "I stage")
    read_pinned(BASE_PATH, BASE_SHA256, "D12 base")
    read_pinned(SOURCE_PATH, SOURCE_VECTOR_SHA256, "original D12 source")
    read_pinned(AFFINE_PATH, AFFINE_SHA256, "affine multiplier")
    positive = margin > 0
    payload = {
        "status": ("c10-d12-affine-exact-positive-candidate"
                   if positive else "c10-d12-affine-exact-negative-result"),
        **common,
        "driver_sha256": self_hash,
        "i_stage_path": str(stage_path),
        "i_stage_sha256": expected_stage_sha,
        "I": str(i_value),
        "J": str(j_value),
        "M2": str(kj_value),
        "M2_minus_M1": str(margin),
        "quotient": str(quotient),
        "I_positive": True,
        "margin_positive": positive,
        "exact_fraction_arithmetic": True,
        "matrix_entries_consumed": False,
        "persistent_moment_cache_consumed": False,
        "j_wall_seconds": wall,
        "j_cpu_seconds_parent": cpu,
        "j_peak_rss_kib_linux_parent": rss_kib(),
        "i_wall_seconds": stage["i_wall_seconds"],
        "theorem_ready": False,
        "theorem_ready_reason": (
            "a positive output still requires an independent result-driver "
            "audit, a second reconstruction, and the end-to-end analytic audit"
        ),
    }
    atomic_json(output_path, payload)
    return payload, positive


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=("i", "j", "all"), default="all")
    parser.add_argument("--stage", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--expected-stage-sha256")
    parser.add_argument("--reverse-faces", action="store_true")
    parser.add_argument("--workers", type=int, choices=(1, 2), default=1)
    return parser.parse_args()


def validate_output_paths(stage: Path, output: Path) -> None:
    stage_resolved = stage.resolve(strict=False)
    output_resolved = output.resolve(strict=False)
    protected = {
        Path(__file__).resolve(), SOURCE_PATH.resolve(), BASE_PATH.resolve(),
        AFFINE_PATH.resolve(), *(path.resolve() for path in DEPENDENCY_SHAS),
    }
    if stage_resolved == output_resolved:
        raise ExactAffineCertificateError("stage and output paths must differ")
    if stage_resolved in protected or output_resolved in protected:
        raise ExactAffineCertificateError(
            "stage/output path collides with a pinned input or dependency")


def main() -> int:
    args = parse_args()
    validate_output_paths(args.stage, args.output)
    expected_stage_sha = args.expected_stage_sha256
    if args.phase in ("i", "all"):
        stage, expected_stage_sha = run_i(
            args.stage, args.reverse_faces, args.workers)
        print(json.dumps({
            "phase": "I complete",
            "I": stage["I"],
            "stage": str(args.stage),
            "stage_sha256": expected_stage_sha,
            "wall_seconds": stage["i_wall_seconds"],
            "peak_rss_kib_linux_parent": stage["i_peak_rss_kib_linux_parent"],
        }, sort_keys=True), flush=True)
    if args.phase in ("j", "all"):
        if expected_stage_sha is None:
            raise ExactAffineCertificateError(
                "J phase requires --expected-stage-sha256")
        result, positive = run_j(
            args.stage, expected_stage_sha, args.output,
            args.reverse_faces, args.workers)
        print(json.dumps({
            "phase": "J complete",
            "output": str(args.output),
            "output_sha256": sha256(args.output),
            "quotient": result["quotient"],
            "margin": result["M2_minus_M1"],
            "margin_positive": positive,
            "wall_seconds": result["j_wall_seconds"],
            "peak_rss_kib_linux_parent": result["j_peak_rss_kib_linux_parent"],
        }, sort_keys=True), flush=True)
        if not positive:
            return 4
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ExactAffineCertificateError, CertificateError, ValueError,
            ArithmeticError, OSError) as exc:
        print(json.dumps({"verified": False, "error": str(exc)},
                         sort_keys=True), file=sys.stderr)
        raise SystemExit(3) from exc
