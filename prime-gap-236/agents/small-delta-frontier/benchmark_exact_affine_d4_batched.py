#!/usr/bin/env python3
"""Instrumented exact D4 benchmark of the batched affine J layer.

This consumes the already verified integer-scaled I stage produced by
``benchmark_exact_affine_d4.py``.  Thin counting wrappers delegate every
arithmetic call to the frozen batched implementation, and the final exact
result must equal the independently contracted D4 reference form after the
known global integer scaling.
"""

from __future__ import annotations

import argparse
import json
import resource
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import benchmark_exact_affine_d4 as baseline  # noqa: E402
import verify.exact_affine_multiplier_batched as batched  # noqa: E402
from verify.exact_capped_certificate import C10_D4_REGRESSION  # noqa: E402


BASELINE_WRAPPER_SHA256 = \
    "71becffba9913c7f4933d5b4be50629fbf4d7311b428784146c82d9dc65350dc"
BATCHED_SHA256 = \
    "d824ab8ebb59da4cd94da7b17350c36ba5888bc2260fdeb8e976f4f825405ee8"
DEFAULT_STAGE = HERE / "exact_affine_d4_integer_benchmark.stage.json"
DEFAULT_STAGE_SHA256 = \
    "88a843f9372d1cae191e90fb340c35cc1b28895f2894c900f5a20a16fa37b4ee"


class BatchedBenchmarkError(RuntimeError):
    pass


def require_sources() -> dict[str, str]:
    paths = {
        "baseline_benchmark": HERE / "benchmark_exact_affine_d4.py",
        "batched_affine": ROOT / "verify/exact_affine_multiplier_batched.py",
    }
    expected = {
        "baseline_benchmark": BASELINE_WRAPPER_SHA256,
        "batched_affine": BATCHED_SHA256,
    }
    for key, path in paths.items():
        actual = baseline.sha256(path)
        if actual != expected[key]:
            raise BatchedBenchmarkError(
                f"{key} SHA mismatch: expected {expected[key]}, got {actual}")
    baseline.dependency_snapshot()
    return expected


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", type=Path, default=DEFAULT_STAGE)
    parser.add_argument(
        "--expected-stage-sha256", default=DEFAULT_STAGE_SHA256)
    parser.add_argument(
        "--output", type=Path,
        default=HERE / "exact_affine_d4_integer_batched_benchmark.json")
    args = parser.parse_args()

    sources = require_sources()
    stage, staged_i = baseline.load_stage(
        args.stage, args.expected_stage_sha256)
    terms, multipliers, base_lcm, affine_lcm = \
        baseline.load_integer_scaled_inputs()
    reference_i, reference_kj = baseline.reference_forms()
    form_scale = (base_lcm * affine_lcm) ** 2
    if staged_i != reference_i * form_scale:
        raise BatchedBenchmarkError("staged I/reference scaling mismatch")

    metrics = {
        "face_radialization_calls": 0,
        "tagged_target_polynomials": 0,
        "distinct_source_partitions_summed_over_faces": 0,
        "nonzero_radial_keys_summed_over_targets": 0,
        "tagged_domain_integral_calls": 0,
        "packed_shift_groups_reused_across_domains": 0,
        "packed_terms_reused_across_domains": 0,
        "nominal_boundary_zero_measure_checks": 0,
    }
    original_radialize = batched._radialize_tagged_targets
    original_integrate = batched._integrate_tagged_radial_polynomials
    original_boundary = batched._integrate_radial_polynomial

    def counted_radialize(polynomials, *positional, **keywords):
        metrics["face_radialization_calls"] += 1
        metrics["tagged_target_polynomials"] += len(polynomials)
        metrics["distinct_source_partitions_summed_over_faces"] += len(
            set().union(*(poly.keys() for poly in polynomials.values())))
        result = original_radialize(polynomials, *positional, **keywords)
        metrics["nonzero_radial_keys_summed_over_targets"] += sum(
            len(radial) for radial in result.values())
        return result

    def counted_integrate(*positional, **keywords):
        metrics["tagged_domain_integral_calls"] += 1
        packed = keywords.get("packed_by_shift")
        if packed is not None:
            metrics["packed_shift_groups_reused_across_domains"] += len(packed)
            metrics["packed_terms_reused_across_domains"] += sum(
                len(terms_for_shift) for terms_for_shift in packed.values())
        return original_integrate(*positional, **keywords)

    def counted_boundary(*positional, **keywords):
        metrics["nominal_boundary_zero_measure_checks"] += 1
        return original_boundary(*positional, **keywords)

    batched._radialize_tagged_targets = counted_radialize
    batched._integrate_tagged_radial_polynomials = counted_integrate
    batched._integrate_radial_polynomial = counted_boundary
    try:
        started_wall = time.perf_counter()
        started_cpu = time.process_time()
        j_value = batched.compute_j_affine_tagged_batched(
            terms, C10_D4_REGRESSION, multipliers, workers=1)
        wall = time.perf_counter() - started_wall
        cpu = time.process_time() - started_cpu
    finally:
        batched._radialize_tagged_targets = original_radialize
        batched._integrate_tagged_radial_polynomials = original_integrate
        batched._integrate_radial_polynomial = original_boundary

    kj_value = C10_D4_REGRESSION.k * j_value
    if kj_value != reference_kj * form_scale:
        raise BatchedBenchmarkError(
            "batched integer-scaled kJ disagrees with exact D4 reference")
    quotient = kj_value / staged_i
    if quotient != reference_kj / reference_i:
        raise BatchedBenchmarkError("integer scaling changed exact quotient")
    # r=15 still has an active small distinguished-fiber branch because
    # beta(15)-15*delta = 13/2500 > 0, although its r+1 large branch is dead.
    if metrics["face_radialization_calls"] != 16:
        raise BatchedBenchmarkError("unexpected active common-count face count")
    require_sources()
    baseline.require_sha(args.stage, args.expected_stage_sha256)

    payload = {
        "status": "exact-affine-d4-integer-batched-benchmark-complete",
        "scope": "C10 D4 batched-layer audit benchmark; not D12 certificate",
        "source_sha256": sources,
        "stage_path": str(args.stage.relative_to(ROOT)),
        "stage_sha256": args.expected_stage_sha256,
        "base_lcm": str(base_lcm),
        "effective_affine_lcm": str(affine_lcm),
        "direct_i": baseline.fraction_json(staged_i),
        "direct_kj": baseline.fraction_json(kj_value),
        "direct_margin_kj_minus_i": baseline.fraction_json(kj_value - staged_i),
        "direct_quotient": baseline.fraction_json(quotient),
        "quotient_decimal_45": baseline.decimal_string(quotient),
        "unscaled_margin_decimal_45": baseline.decimal_string(
            (kj_value - staged_i) / form_scale),
        "j_wall_seconds": wall,
        "j_cpu_seconds": cpu,
        "j_process_peak_rss_kib_linux": int(
            resource.getrusage(resource.RUSAGE_SELF).ru_maxrss),
        "traversal_metrics": metrics,
        "direct_reference_bitwise_equal_after_scaling": True,
        "quotient_invariant_under_integer_scaling": True,
        "counting_wrappers_delegate_without_arithmetic_change": True,
        "theorem_ready": False,
    }
    output_sha = baseline.atomic_json(args.output, payload)
    print(json.dumps({
        "output": str(args.output),
        "output_sha256": output_sha,
        "wall_seconds": wall,
        "peak_rss_kib_linux": payload["j_process_peak_rss_kib_linux"],
        "quotient_decimal_45": payload["quotient_decimal_45"],
        "traversal_metrics": metrics,
    }, sort_keys=True))


if __name__ == "__main__":
    try:
        main()
    except (BatchedBenchmarkError, baseline.BenchmarkError, ValueError,
            ArithmeticError, OSError) as exc:
        raise SystemExit(f"BATCHED BENCHMARK FAIL: {exc}") from exc
