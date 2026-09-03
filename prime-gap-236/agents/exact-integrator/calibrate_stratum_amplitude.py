#!/usr/bin/env python3
"""Low-degree exact calibration of fixed-vector stratum amplitudes.

The only floating-point step is a 16-by-16 generalized eigensolve used to pick
amplitudes.  Those amplitudes are rationalized, and both the tridiagonal form
and a fresh branch-scaled grouped traversal are then evaluated with Fraction.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import resource
import sys
import time
from fractions import Fraction
from pathlib import Path

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "src")
sys.path.insert(0, SRC)

import exact_integrator as ei  # noqa: E402
from stratum_amplitude import StratumAmplitudeEvaluator  # noqa: E402


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def render(value):
    if isinstance(value, dict):
        return {str(key): render(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [render(item) for item in value]
    return str(value)


def solve_scaled(a_diagonal, b_diagonal, b_superdiagonal):
    a = np.asarray([float(x) for x in a_diagonal], dtype=np.float64)
    if not np.all(np.isfinite(a)) or np.any(a <= 0):
        raise ArithmeticError("nonpositive/nonfinite stratum I block")
    n = len(a)
    b = np.zeros((n, n), dtype=np.float64)
    for i, value in enumerate(b_diagonal):
        b[i, i] = float(value)
    for i, value in enumerate(b_superdiagonal):
        b[i, i + 1] = b[i + 1, i] = float(value)
    scales = np.sqrt(a)
    c = b / scales[:, None] / scales[None, :]
    c = (c + c.T) / 2
    values, vectors = np.linalg.eigh(c)
    y = vectors[:, -1]
    amplitude = y / scales
    amplitude /= np.max(np.abs(amplitude))
    residual = c @ y - values[-1] * y
    return float(values[-1]), amplitude, float(np.max(np.abs(residual)))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input_json")
    parser.add_argument("--output", required=True)
    parser.add_argument("--max-denominator", type=int, default=10**9)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--progress", action="store_true")
    args = parser.parse_args()
    if args.workers < 1 or args.max_denominator < 1:
        parser.error("workers/max-denominator must be positive")

    input_bytes = Path(args.input_json).read_bytes()
    raw = json.loads(input_bytes)
    if int(raw.get("k", -1)) != 48:
        raise SystemExit("calibration is pinned to k=48")
    labels = [(int(a), tuple(int(x) for x in lam)) for a, lam in raw["basis"]]
    coefficients = [Fraction(x) for x in raw["rational_vector"]]
    if len(labels) != len(coefficients):
        raise SystemExit("basis/vector dimension mismatch")
    support = ei.OneStratumSupport(
        48, Fraction(79247, 300000), Fraction(1, 100),
        Fraction(76247, 300000), Fraction(3, 20), Fraction(3, 20),
        Fraction(97, 625))
    evaluator = StratumAmplitudeEvaluator(
        support, labels, coefficients, Fraction)

    start = time.perf_counter()
    blocks = evaluator.evaluate_all_blocks(args.progress, args.workers)
    after_blocks = time.perf_counter()
    eigenvalue, amplitude_float, residual = solve_scaled(
        blocks["a_diagonal"], blocks["b_diagonal"],
        blocks["b_superdiagonal"])
    amplitudes = [Fraction(float(x)).limit_denominator(args.max_denominator)
                  for x in amplitude_float]
    if not any(amplitudes):
        raise ArithmeticError("rationalized amplitude vector is zero")
    block_denominator = evaluator.tridiagonal_quadratic(
        blocks["a_diagonal"], (), amplitudes, Fraction(0))
    block_numerator = evaluator.tridiagonal_quadratic(
        blocks["b_diagonal"], blocks["b_superdiagonal"], amplitudes,
        Fraction(0))
    direct = evaluator.evaluate_amplitudes_direct(
        amplitudes, blocks["i_by_r"], args.progress, args.workers)
    after_direct = time.perf_counter()
    if direct[0] != block_denominator or direct[1] != block_numerator:
        raise ArithmeticError("direct amplitude traversal disagrees with blocks")

    baseline_denominator = blocks["all_ones_denominator"]
    baseline_numerator = blocks["all_ones_numerator"]
    output = {
        "status": "exact-rational-stratum-amplitude-D4-calibration",
        "rigorous_forms": True,
        "eigenvector_discovery_rigorous": False,
        "input_json": args.input_json,
        "input_sha256": hashlib.sha256(input_bytes).hexdigest(),
        "script_sha256": sha(__file__),
        "stratum_amplitude_sha256": sha(Path(HERE) / "stratum_amplitude.py"),
        "grouped_evaluator_sha256": sha(Path(HERE) / "grouped_fixed_vector.py"),
        "integrator_sha256": sha(Path(SRC) / "exact_integrator.py"),
        "k": 48,
        "basis_dimension": len(labels),
        "parameters": {
            "alpha": "79247/300000", "delta": "1/100",
            "eta": "76247/300000", "beta1": "3/20",
            "beta2": "3/20", "beta3plus": "97/625",
        },
        "stratum_dimension": len(amplitudes),
        "floating_generalized_eigenvalue": repr(eigenvalue),
        "floating_scaled_residual_infinity": repr(residual),
        "max_rationalization_denominator": args.max_denominator,
        "rational_amplitudes": [str(x) for x in amplitudes],
        "baseline_denominator": str(baseline_denominator),
        "baseline_numerator": str(baseline_numerator),
        "baseline_quotient": str(baseline_numerator / baseline_denominator),
        "block_denominator": str(block_denominator),
        "block_numerator": str(block_numerator),
        "block_quotient": str(block_numerator / block_denominator),
        "direct_denominator": str(direct[0]),
        "direct_numerator": str(direct[1]),
        "direct_quotient": str(direct[1] / direct[0]),
        "exact_gain": str(block_numerator / block_denominator -
                          baseline_numerator / baseline_denominator),
        "block_direct_bitwise_equal": True,
        "i_orbit_groups": blocks["i_orbit_groups"],
        "i_faces": blocks["i_faces"],
        "marginal_components": blocks["marginal_components"],
        "j_branch_integrals": blocks["j_branch_integrals"],
        "direct_j_branch_integrals": direct[3],
        "blocks_seconds": after_blocks - start,
        "direct_seconds": after_direct - after_blocks,
        "total_seconds": after_direct - start,
        "peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "child_peak_rss_kib": resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,
        "a_diagonal": render(blocks["a_diagonal"]),
        "b_diagonal": render(blocks["b_diagonal"]),
        "b_superdiagonal": render(blocks["b_superdiagonal"]),
    }
    rendered = json.dumps(output, indent=2) + "\n"
    Path(args.output).write_text(rendered)
    print(json.dumps({key: output[key] for key in (
        "input_sha256", "floating_generalized_eigenvalue",
        "baseline_quotient", "direct_quotient", "exact_gain",
        "block_direct_bitwise_equal", "total_seconds")}, indent=2))


if __name__ == "__main__":
    main()
