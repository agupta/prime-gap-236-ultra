#!/usr/bin/env python3
"""Second dyadic reconstruction through the independent tagged-affine algebra.

Unlike ``check_c10_d12_affine_dyadic.py``, this checker does not use the
grouped Decimal evaluator's face, marginal, or branch code.  It encloses the
input coefficients first and then evaluates the separately implemented
partition-radial recurrence in ``exact_affine_multiplier[_batched].py``.
Geometry parameters stay exact Fractions.  No matrix, Decimal integral, or
persistent moment cache is consumed.

The two phases are SHA-bound because a target J traversal can be long.  A
positive result remains a candidate until this driver and its output receive
an independent audit.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import resource
import sys
import time
from pathlib import Path

if hasattr(sys, "set_int_max_str_digits"):
    sys.set_int_max_str_digits(0)

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))

from verify.check_c10_d12_affine_exact import (  # noqa: E402
    AFFINE_PATH,
    AFFINE_SHA256,
    BASE_PATH,
    BASE_SHA256,
    SOURCE_PATH,
    SOURCE_VECTOR_SHA256,
    load_scaled_inputs,
    read_pinned,
)
from verify.dyadic_interval import (  # noqa: E402
    DyadicInterval,
    IndeterminateComparison,
)
from verify.exact_affine_multiplier import (  # noqa: E402
    AffineMultipliers,
    compute_i_affine_tagged,
)
from verify.exact_affine_multiplier_batched import (  # noqa: E402
    compute_j_affine_tagged_batched,
)
from verify.exact_capped_certificate import (  # noqa: E402
    CertificateError,
    TARGET_C10_D12,
    _reject_constant,
    _reject_duplicate_object,
)


DEPENDENCY_SHAS = {
    ROOT / "verify/check_c10_d12_affine_exact.py":
        "5514f63159ad74e54142cf1db2d88a9c69f552cad3d253cd50ca66452cf2784e",
    ROOT / "verify/dyadic_interval.py":
        "f6f1730f77ba490f04326338e7b3bfe5ab2e5c6438f10892bdf3f5bfe6fc875d",
    ROOT / "verify/exact_affine_multiplier.py":
        "9c21d73af25f63ad16c62a2a1935a9cfd3a8d134d7b7ada2620eddc12e1c3d3e",
    ROOT / "verify/exact_affine_multiplier_batched.py":
        "d824ab8ebb59da4cd94da7b17350c36ba5888bc2260fdeb8e976f4f825405ee8",
    ROOT / "verify/exact_capped_certificate.py":
        "1787e7b482a5c2982de56486bc774794f6e671b3db4d9ab7207ebb1c85dc079c",
}
EXPECTED_ACTIVE_I_FACES = 16
EXPECTED_ACTIVE_J_FACES = 16


class IndependentDyadicError(RuntimeError):
    pass


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dependency_snapshot() -> dict[str, str]:
    answer = {}
    for path, expected in DEPENDENCY_SHAS.items():
        read_pinned(path, expected, str(path.relative_to(ROOT)))
        answer[str(path.relative_to(ROOT))] = expected
    return answer


def strict_json(raw: bytes, description: str) -> dict:
    try:
        value = json.loads(
            raw,
            object_pairs_hook=_reject_duplicate_object,
            parse_constant=_reject_constant,
        )
    except (json.JSONDecodeError, UnicodeError, CertificateError) as exc:
        raise IndependentDyadicError(
            f"malformed {description}: {exc}") from exc
    if not isinstance(value, dict):
        raise IndependentDyadicError(f"{description} is not an object")
    return value


def active_face_counts() -> tuple[int, int]:
    params = TARGET_C10_D12
    i_faces = sum(
        params.alpha - r * params.delta > 0
        and (r == 0 or params.beta(r) - r * params.delta > 0)
        for r in range(params.k + 1)
    )
    j_active = []
    for r in range(params.k):
        if params.eta - r * params.delta <= 0:
            continue
        small = r == 0 or params.beta(r) - r * params.delta > 0
        large = params.beta(r + 1) - (r + 1) * params.delta > 0
        if small or large:
            j_active.append(r)
    return i_faces, len(j_active)


def intervalize(precision: int, shadow_bits: int):
    DyadicInterval.configure(precision, shadow_bits)
    exact_terms, exact_affine, affine_lcm, base_lcm = load_scaled_inputs()
    interval_terms = {
        label: DyadicInterval(value)
        for label, value in exact_terms.items()
    }
    interval_affine = AffineMultipliers(
        tuple(tuple(DyadicInterval(value) for value in triple)
              for triple in exact_affine.coefficients),
        source_sha256=exact_affine.source_sha256,
        linear_cutoff=exact_affine.linear_cutoff,
    )
    interval_affine.validate_for(TARGET_C10_D12)
    faces = active_face_counts()
    if faces != (EXPECTED_ACTIVE_I_FACES, EXPECTED_ACTIVE_J_FACES):
        raise IndependentDyadicError(
            f"active-face count mismatch: expected (16,16), got {faces}")
    return interval_terms, interval_affine, affine_lcm, base_lcm, faces


def interval_data(value: DyadicInterval) -> dict:
    if not isinstance(value, DyadicInterval):
        raise IndependentDyadicError("computed value is not dyadic")
    return {
        "precision_bits": DyadicInterval.PRECISION,
        "lo_integer": str(value.lo),
        "hi_integer": str(value.hi),
        "lower_fraction": str(value.lower_fraction()),
        "upper_fraction": str(value.upper_fraction()),
        "width_units": value.width_units(),
    }


def interval_from_data(raw, precision: int, description: str) -> DyadicInterval:
    expected = {"precision_bits", "lo_integer", "hi_integer",
                "lower_fraction", "upper_fraction", "width_units"}
    if not isinstance(raw, dict) or set(raw) != expected:
        raise IndependentDyadicError(f"malformed staged {description}")
    if raw.get("precision_bits") != precision:
        raise IndependentDyadicError(f"staged {description} precision mismatch")
    try:
        lo = int(raw["lo_integer"])
        hi = int(raw["hi_integer"])
    except (TypeError, ValueError) as exc:
        raise IndependentDyadicError(
            f"invalid staged {description} endpoints") from exc
    if str(lo) != raw["lo_integer"] or str(hi) != raw["hi_integer"]:
        raise IndependentDyadicError(
            f"noncanonical staged {description} endpoints")
    width = raw.get("width_units")
    if (isinstance(width, bool) or not isinstance(width, int) or
            width < 0 or hi - lo != width):
        raise IndependentDyadicError(f"staged {description} width mismatch")
    value = DyadicInterval._from_bounds(lo, hi)
    if (str(value.lower_fraction()) != raw.get("lower_fraction") or
            str(value.upper_fraction()) != raw.get("upper_fraction")):
        raise IndependentDyadicError(
            f"staged {description} endpoint fractions mismatch")
    return value


def common_metadata(dependencies, precision, shadow_bits, affine_lcm,
                    base_lcm, reverse_faces, faces):
    return {
        "scope": "independent tagged C10 D12 affine dyadic enclosure",
        "k": 48,
        "degree_of_base": 12,
        "base_dimension": 272,
        "linear_cutoff": 11,
        "base_path": str(BASE_PATH.relative_to(ROOT)),
        "base_sha256": BASE_SHA256,
        "original_source_path": str(SOURCE_PATH.relative_to(ROOT)),
        "original_source_sha256": SOURCE_VECTOR_SHA256,
        "affine_path": str(AFFINE_PATH.relative_to(ROOT)),
        "affine_sha256": AFFINE_SHA256,
        "reconstructed_base_lcm": str(base_lcm),
        "effective_affine_lcm": str(affine_lcm),
        "precision_bits": precision,
        "shadow_bits": shadow_bits,
        "reverse_faces": reverse_faces,
        "active_i_faces": faces[0],
        "active_j_faces": faces[1],
        "matrix_entries_consumed": False,
        "persistent_moment_cache_consumed": False,
        "dependency_sha256": dependencies,
    }


def atomic_json(path: Path, payload: dict) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + f".tmp.{os.getpid()}")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8")
    os.replace(temporary, path)
    return sha256(path)


def reread_inputs() -> None:
    read_pinned(SOURCE_PATH, SOURCE_VECTOR_SHA256, "original D12 source")
    read_pinned(BASE_PATH, BASE_SHA256, "D12 base")
    read_pinned(AFFINE_PATH, AFFINE_SHA256, "affine multiplier")


def run_i(terms, affine, common, stage_path, reverse_faces):
    self_hash = sha256(Path(__file__))
    started = time.perf_counter()
    denominator = compute_i_affine_tagged(
        terms, TARGET_C10_D12, affine,
        reverse_faces=reverse_faces, workers=1)
    wall = time.perf_counter() - started
    if not isinstance(denominator, DyadicInterval) or denominator.lo <= 0:
        raise IndependentDyadicError("I enclosure is not strictly positive")
    if sha256(Path(__file__)) != self_hash:
        raise IndependentDyadicError("driver changed during I stage")
    if dependency_snapshot() != common["dependency_sha256"]:
        raise IndependentDyadicError("dependency changed during I stage")
    reread_inputs()
    payload = {
        "status": "c10-d12-affine-independent-dyadic-i-stage",
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
        raise IndependentDyadicError("invalid I-stage SHA")
    stage = strict_json(
        read_pinned(stage_path, expected_sha, "I stage"), "I stage")
    expected_keys = {
        "status", *common.keys(), "driver_sha256", "I",
        "I_strictly_positive", "i_wall_seconds", "i_peak_rss_kib_linux",
    }
    if set(stage) != expected_keys:
        raise IndependentDyadicError("I-stage field set mismatch")
    if stage.get("status") != "c10-d12-affine-independent-dyadic-i-stage":
        raise IndependentDyadicError("I-stage status mismatch")
    for key, value in common.items():
        if stage.get(key) != value:
            raise IndependentDyadicError(f"I-stage metadata mismatch at {key}")
    if stage.get("driver_sha256") != sha256(Path(__file__)):
        raise IndependentDyadicError("I-stage driver SHA mismatch")
    denominator = interval_from_data(
        stage.get("I"), common["precision_bits"], "I")
    if stage.get("I_strictly_positive") is not True or denominator.lo <= 0:
        raise IndependentDyadicError("staged I is not strictly positive")
    return stage, denominator


def run_j(terms, affine, common, stage_path, expected_sha, output_path,
          reverse_faces):
    self_hash = sha256(Path(__file__))
    stage, denominator = load_stage(stage_path, expected_sha, common)
    started = time.perf_counter()
    j_value = compute_j_affine_tagged_batched(
        terms, TARGET_C10_D12, affine,
        reverse_faces=reverse_faces, workers=1)
    wall = time.perf_counter() - started
    numerator = DyadicInterval(48) * j_value
    margin = numerator - denominator
    quotient = numerator / denominator
    positive = margin.lo > 0
    if sha256(Path(__file__)) != self_hash:
        raise IndependentDyadicError("driver changed during J stage")
    if dependency_snapshot() != common["dependency_sha256"]:
        raise IndependentDyadicError("dependency changed during J stage")
    read_pinned(stage_path, expected_sha, "I stage")
    reread_inputs()
    payload = {
        "status": ("c10-d12-affine-independent-dyadic-positive-candidate"
                   if positive else
                   "c10-d12-affine-independent-dyadic-nonpositive-result"),
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
        "acceptance_rule": "I.lo > 0 and (M2-M1).lo > 0",
        "integer_directed_outward_rounding": True,
        "j_wall_seconds": wall,
        "j_peak_rss_kib_linux": int(resource.getrusage(
            resource.RUSAGE_SELF).ru_maxrss),
        "i_wall_seconds": stage["i_wall_seconds"],
        "theorem_ready": False,
        "theorem_ready_reason": (
            "driver/output audit and final end-to-end analytic audit remain"
        ),
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


def validate_paths(stage: Path, output: Path) -> None:
    protected = {
        Path(__file__).resolve(), SOURCE_PATH.resolve(), BASE_PATH.resolve(),
        AFFINE_PATH.resolve(), *(path.resolve() for path in DEPENDENCY_SHAS),
    }
    if stage.resolve(strict=False) == output.resolve(strict=False):
        raise IndependentDyadicError("stage and output paths must differ")
    if (stage.resolve(strict=False) in protected or
            output.resolve(strict=False) in protected):
        raise IndependentDyadicError("output path collides with pinned input")


def main() -> int:
    args = parse_args()
    if not 256 <= args.precision <= 4096:
        raise IndependentDyadicError("precision must be in [256,4096]")
    if not 32 <= args.shadow_bits <= 512:
        raise IndependentDyadicError("shadow bits must be in [32,512]")
    validate_paths(args.stage, args.output)
    self_hash = sha256(Path(__file__))
    dependencies = dependency_snapshot()
    terms, affine, affine_lcm, base_lcm, faces = intervalize(
        args.precision, args.shadow_bits)
    common = common_metadata(
        dependencies, args.precision, args.shadow_bits,
        affine_lcm, base_lcm, args.reverse_faces, faces)
    if sha256(Path(__file__)) != self_hash:
        raise IndependentDyadicError("driver changed during preparation")

    expected_sha = args.expected_stage_sha256
    if args.phase in ("i", "all"):
        stage, expected_sha = run_i(
            terms, affine, common, args.stage, args.reverse_faces)
        print(json.dumps({
            "phase": "I complete", "stage": str(args.stage),
            "stage_sha256": expected_sha,
            "I_lower": stage["I"]["lower_fraction"],
            "I_upper": stage["I"]["upper_fraction"],
            "wall_seconds": stage["i_wall_seconds"],
        }, sort_keys=True), flush=True)
    if args.phase in ("j", "all"):
        if expected_sha is None:
            raise IndependentDyadicError(
                "J phase requires --expected-stage-sha256")
        result, positive = run_j(
            terms, affine, common, args.stage, expected_sha,
            args.output, args.reverse_faces)
        print(json.dumps({
            "phase": "J complete", "output": str(args.output),
            "output_sha256": sha256(args.output),
            "quotient_lower": result["quotient"]["lower_fraction"],
            "quotient_upper": result["quotient"]["upper_fraction"],
            "margin_lower": result["M2_minus_M1"]["lower_fraction"],
            "margin_upper": result["M2_minus_M1"]["upper_fraction"],
            "margin_strictly_positive": positive,
            "wall_seconds": result["j_wall_seconds"],
        }, sort_keys=True), flush=True)
        if not positive:
            return 4
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (IndependentDyadicError, CertificateError,
            IndeterminateComparison, ValueError, ArithmeticError,
            OSError) as exc:
        print(json.dumps({"verified": False, "error": str(exc)},
                         sort_keys=True), file=sys.stderr)
        raise SystemExit(3) from exc
