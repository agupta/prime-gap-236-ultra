#!/usr/bin/env python3
"""Cost/equality benchmark for the independent tagged dyadic path at D4.

The calculation encloses integer-scaled coefficients before entering the
independent tagged-affine recurrence.  Serialized D4 forms are read only after
the traversal as a regression oracle; they are not used to compute either
interval.  This benchmark is not a D12 certificate.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import resource
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BENCHMARK_DIR = ROOT / "agents/small-delta-frontier"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(BENCHMARK_DIR))

import benchmark_exact_affine_d4 as baseline  # noqa: E402
from verify.dyadic_interval import DyadicInterval  # noqa: E402
from verify.exact_affine_multiplier import (  # noqa: E402
    AffineMultipliers,
    compute_i_affine_tagged,
)
from verify.exact_affine_multiplier_batched import (  # noqa: E402
    compute_j_affine_tagged_batched,
)
from verify.exact_capped_certificate import C10_D4_REGRESSION  # noqa: E402


PINNED = {
    BENCHMARK_DIR / "benchmark_exact_affine_d4.py":
        "71becffba9913c7f4933d5b4be50629fbf4d7311b428784146c82d9dc65350dc",
    ROOT / "verify/dyadic_interval.py":
        "f6f1730f77ba490f04326338e7b3bfe5ab2e5c6438f10892bdf3f5bfe6fc875d",
    ROOT / "verify/exact_affine_multiplier.py":
        "9c21d73af25f63ad16c62a2a1935a9cfd3a8d134d7b7ada2620eddc12e1c3d3e",
    ROOT / "verify/exact_affine_multiplier_batched.py":
        "d824ab8ebb59da4cd94da7b17350c36ba5888bc2260fdeb8e976f4f825405ee8",
    ROOT / "verify/exact_capped_certificate.py":
        "1787e7b482a5c2982de56486bc774794f6e671b3db4d9ab7207ebb1c85dc079c",
}


class BenchmarkError(RuntimeError):
    pass


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require_pins() -> dict[str, str]:
    result = {}
    for path, expected in PINNED.items():
        actual = sha256(path)
        if actual != expected:
            raise BenchmarkError(
                f"dependency SHA mismatch for {path}: {actual}")
        result[str(path.relative_to(ROOT))] = expected
    baseline.dependency_snapshot()
    return result


def interval_data(value: DyadicInterval) -> dict:
    return {
        "lo_integer": str(value.lo),
        "hi_integer": str(value.hi),
        "lower_fraction": str(value.lower_fraction()),
        "upper_fraction": str(value.upper_fraction()),
        "width_units": value.width_units(),
    }


def decimal_endpoint(value, digits=45) -> str:
    from decimal import Decimal, localcontext
    with localcontext() as context:
        context.prec = digits
        return str(Decimal(value.numerator) / Decimal(value.denominator))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--precision", type=int, default=512)
    parser.add_argument("--shadow-bits", type=int, default=96)
    parser.add_argument(
        "--output", type=Path,
        default=BENCHMARK_DIR / "independent_affine_d4_dyadic_benchmark.json")
    args = parser.parse_args()
    if not 256 <= args.precision <= 4096:
        raise BenchmarkError("precision must be in [256,4096]")
    if not 32 <= args.shadow_bits <= 512:
        raise BenchmarkError("shadow bits must be in [32,512]")
    dependencies = require_pins()

    exact_terms, exact_affine, base_lcm, affine_lcm = \
        baseline.load_integer_scaled_inputs()
    reference_i, reference_kj = baseline.reference_forms()
    form_scale = (base_lcm * affine_lcm) ** 2
    scaled_reference_i = reference_i * form_scale
    scaled_reference_kj = reference_kj * form_scale

    DyadicInterval.configure(args.precision, args.shadow_bits)
    terms = {
        label: DyadicInterval(value)
        for label, value in exact_terms.items()
    }
    affine = AffineMultipliers(
        tuple(tuple(DyadicInterval(value) for value in triple)
              for triple in exact_affine.coefficients),
        source_sha256=exact_affine.source_sha256,
        linear_cutoff=exact_affine.linear_cutoff,
    )

    started = time.perf_counter()
    i_started = time.perf_counter()
    i_value = compute_i_affine_tagged(
        terms, C10_D4_REGRESSION, affine, workers=1)
    i_seconds = time.perf_counter() - i_started
    j_started = time.perf_counter()
    j_value = compute_j_affine_tagged_batched(
        terms, C10_D4_REGRESSION, affine, workers=1)
    j_seconds = time.perf_counter() - j_started
    kj_value = DyadicInterval(C10_D4_REGRESSION.k) * j_value
    quotient = kj_value / i_value

    if not i_value.contains(scaled_reference_i):
        raise BenchmarkError("independent dyadic I misses exact D4 reference")
    if not kj_value.contains(scaled_reference_kj):
        raise BenchmarkError("independent dyadic kJ misses exact D4 reference")
    exact_quotient = reference_kj / reference_i
    if not quotient.contains(exact_quotient):
        raise BenchmarkError("independent dyadic quotient misses exact D4 value")
    if i_value.lo <= 0:
        raise BenchmarkError("D4 I positivity was not enclosed")
    if require_pins() != dependencies:
        raise BenchmarkError("dependency changed during benchmark")

    payload = {
        "status": "independent-affine-d4-dyadic-benchmark-complete",
        "scope": "C10 D4 cost/equality regression; not D12 certificate",
        "driver_sha256": sha256(Path(__file__)),
        "dependency_sha256": dependencies,
        "precision_bits": args.precision,
        "shadow_bits": args.shadow_bits,
        "base_lcm": str(base_lcm),
        "effective_affine_lcm": str(affine_lcm),
        "I": interval_data(i_value),
        "M2": interval_data(kj_value),
        "quotient": interval_data(quotient),
        "quotient_lower_decimal_45": decimal_endpoint(
            quotient.lower_fraction()),
        "quotient_upper_decimal_45": decimal_endpoint(
            quotient.upper_fraction()),
        "exact_reference_quotient": str(exact_quotient),
        "exact_reference_contained": True,
        "i_wall_seconds": i_seconds,
        "j_wall_seconds": j_seconds,
        "total_wall_seconds": time.perf_counter() - started,
        "peak_rss_kib_linux": int(
            resource.getrusage(resource.RUSAGE_SELF).ru_maxrss),
        "matrix_consumed_by_traversal": False,
        "reference_matrix_consumed_after_traversal_for_regression": True,
        "theorem_ready": False,
    }
    output_sha = baseline.atomic_json(args.output, payload)
    print(json.dumps({
        "output": str(args.output),
        "output_sha256": output_sha,
        "quotient_lower_decimal_45": payload["quotient_lower_decimal_45"],
        "quotient_upper_decimal_45": payload["quotient_upper_decimal_45"],
        "i_wall_seconds": i_seconds,
        "j_wall_seconds": j_seconds,
        "peak_rss_kib_linux": payload["peak_rss_kib_linux"],
    }, sort_keys=True))


if __name__ == "__main__":
    try:
        main()
    except (BenchmarkError, baseline.BenchmarkError, ValueError,
            ArithmeticError, OSError) as exc:
        raise SystemExit(f"INDEPENDENT DYADIC D4 BENCHMARK FAIL: {exc}") from exc
