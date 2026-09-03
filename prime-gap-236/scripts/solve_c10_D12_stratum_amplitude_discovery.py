#!/usr/bin/env python3
"""Reproducible Decimal solve of the frozen C10 D12 amplitude blocks.

The input blocks came from a Decimal100 integration, so this is deliberately
only a discovery result.  Finite-decimal entries and the selected rational
amplitudes are contracted exactly to make the numerical claim reproducible;
they are not promoted to exact integrals.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from decimal import Decimal, localcontext
from fractions import Fraction as Q
from pathlib import Path


FILE = Path(__file__).resolve()
REPO = FILE.parents[1]
DEFAULT_INPUT = (REPO / "agents/exact-integrator/results/"
                 "c10_D12_stratum_amplitude_decimal100.json")
INPUT_SHA256 = "7bc4f1a29bcbb292a6b613017dae1db2fc81851dd1286d81eff63e3368f6c26d"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def finite_decimal(text: object) -> Decimal:
    if not isinstance(text, str):
        raise ValueError("moment entry is not a string")
    value = Decimal(text)
    if not value.is_finite():
        raise ValueError("nonfinite moment entry")
    return value


def rayleigh(a: list[Decimal], d: list[Decimal], s: list[Decimal],
             vector: list[Decimal]) -> Decimal:
    denominator = sum((a[i] * vector[i] * vector[i]
                       for i in range(len(a))), Decimal(0))
    numerator = sum((d[i] * vector[i] * vector[i]
                     for i in range(len(a))), Decimal(0))
    numerator += 2 * sum((s[i] * vector[i] * vector[i + 1]
                          for i in range(len(s))), Decimal(0))
    return numerator / denominator


def solve(a: list[Decimal], d: list[Decimal], s: list[Decimal],
          iterations: int) -> tuple[list[Decimal], list[list[object]]]:
    vector = [Decimal(1) for _ in a]
    trace: list[list[object]] = []
    for iteration in range(1, iterations + 1):
        image = []
        for i in range(len(a)):
            value = d[i] * vector[i]
            if i:
                value += s[i - 1] * vector[i - 1]
            if i + 1 < len(a):
                value += s[i] * vector[i + 1]
            image.append(value / a[i])
        scale = max(abs(x) for x in image)
        if not scale.is_finite() or scale == 0:
            raise ArithmeticError("invalid power-iteration normalization")
        vector = [x / scale for x in image]
        if iteration % 50 == 0 or iteration == iterations:
            trace.append([iteration, str(rayleigh(a, d, s, vector))])
    scale = max(abs(x) for x in vector)
    return [x / scale for x in vector], trace


def exact_contract(a: list[Q], d: list[Q], s: list[Q], vector: list[Q]):
    denominator = sum((a[i] * vector[i] ** 2 for i in range(len(a))), Q(0))
    numerator = sum((d[i] * vector[i] ** 2 for i in range(len(a))), Q(0))
    numerator += 2 * sum((s[i] * vector[i] * vector[i + 1]
                          for i in range(len(s))), Q(0))
    return denominator, numerator


def publish(path: Path, payload: bytes) -> None:
    path = path.resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    with os.fdopen(descriptor, "wb", closefd=True) as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--precision", type=int, default=120)
    parser.add_argument("--iterations", type=int, default=600)
    parser.add_argument("--max-denominator", type=int, default=10**12)
    args = parser.parse_args()
    if args.precision < 100 or args.iterations < 100 or args.max_denominator < 1:
        parser.error("insufficient solve parameters")
    if sha256(args.input) != INPUT_SHA256:
        raise RuntimeError("frozen amplitude-block input changed")
    raw = json.loads(args.input.read_bytes())
    if (raw.get("status") != "multiprecision-stratum-amplitude-blocks-discovery"
            or raw.get("rigorous") is not False or raw.get("k") != 48
            or raw.get("basis_dimension") != 272):
        raise ValueError("input identity changed")
    with localcontext() as context:
        context.prec = args.precision
        a = [finite_decimal(x) for x in raw["a_diagonal"]]
        d = [finite_decimal(x) for x in raw["b_diagonal"]]
        s = [finite_decimal(x) for x in raw["b_superdiagonal"]]
        if len(a) != 16 or len(d) != 16 or len(s) != 15 or min(a) <= 0:
            raise ValueError("invalid tridiagonal block dimensions")
        amplitudes_decimal, trace = solve(a, d, s, args.iterations)
        amplitudes = [Q(x).limit_denominator(args.max_denominator)
                      for x in amplitudes_decimal]
        af, df, sf = ([Q(str(x)) for x in values] for values in (a, d, s))
        denominator, numerator = exact_contract(af, df, sf, amplitudes)
        baseline_denominator = Q(raw["all_ones_denominator"])
        baseline_numerator = Q(raw["all_ones_numerator"])
        quotient = numerator / denominator
        baseline = baseline_numerator / baseline_denominator
        result = {
            "status": "c10-D12-stratum-amplitude-discovery-negative",
            "rigorous": False,
            "theorem_ready": False,
            "reason_not_rigorous": "input moments are Decimal100 approximations",
            "script_sha256": sha256(FILE),
            "input_sha256": INPUT_SHA256,
            "precision": args.precision,
            "iterations": args.iterations,
            "max_rationalization_denominator": args.max_denominator,
            "power_trace": trace,
            "rational_amplitudes": [str(x) for x in amplitudes],
            "serialized_block_denominator": str(denominator),
            "serialized_block_numerator": str(numerator),
            "serialized_block_quotient": str(quotient),
            "serialized_block_margin": str(numerator - denominator),
            "baseline_quotient": str(baseline),
            "heuristic_gain": str(quotient - baseline),
            "quotient_decimal": format(Decimal(quotient.numerator) /
                                       Decimal(quotient.denominator), ".70g"),
            "margin_negative_on_serialized_blocks": numerator < denominator,
        }
    payload = (json.dumps(result, sort_keys=True, separators=(",", ":")) +
               "\n").encode("ascii")
    publish(args.output, payload)
    print(payload.decode("ascii"), end="")


if __name__ == "__main__":
    main()
