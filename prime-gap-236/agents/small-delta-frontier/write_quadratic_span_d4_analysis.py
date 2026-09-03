#!/usr/bin/env python3
"""Emit the exact-matrix D4 analysis which gates the span contingency."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from fractions import Fraction
from pathlib import Path

import build_quadratic_span_contingency as core


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True)
    parser.add_argument("--expect-source-sha256", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    core.require(args.expect_source_sha256 == core.SOURCE_SHA,
                 "caller did not pin the frozen D4 source")
    core.require(len({Path(args.source).resolve(), Path(args.output).resolve(),
                      Path(__file__).resolve()}) == 3,
                 "source/output/analyzer paths must be distinct")
    source_bytes, raw = core.read_pinned(
        args.source, core.SOURCE_SHA, "quadratic source")
    parsed = core.parse_source(raw)
    result = core.reconstruct(parsed, Fraction(1))
    stationary = core.d4_span_stationary(result)
    q_quotient = result["q_forms"][1] / result["q_forms"][0]
    maximum_decimal = stationary["maximum_point"]["quotient"]
    with core.localcontext() as context:
        context.prec = 160
        maximum_minus_q = (
            core.Decimal(maximum_decimal) -
            core.Decimal(q_quotient.numerator) /
            core.Decimal(q_quotient.denominator))
    payload = {
        "status": "exact-D4-constant-Q-span-analysis",
        "rigorous_forms": True,
        "theorem_ready": False,
        "source_multiplier_sha256": core.SOURCE_SHA,
        "source_multiplier_json": str(Path(args.source)),
        "analyzer_sha256": core.file_sha(__file__),
        "builder_sha256": core.file_sha(core.__file__),
        "k": 48,
        "parameters": core.PARAMETERS,
        "pencil_gauge": "1+t*Q",
        "base_denominator": str(result["base_forms"][0]),
        "base_numerator": str(result["base_forms"][1]),
        "base_q_i_cross": str(result["cross_forms"][0]),
        "base_q_n_cross": str(result["cross_forms"][1]),
        "q_denominator": str(result["q_forms"][0]),
        "q_numerator": str(result["q_forms"][1]),
        "q_quotient": str(q_quotient),
        "h_equal_one_plus_q_quotient": str(
            result["h_forms"][1] / result["h_forms"][0]),
        "projective_stationary": stationary,
        "maximum_minus_q_decimal160": str(maximum_minus_q),
        "decision": ("H=1+Q is base-dominated and is not launched.  The "
                     "generic transfer artifact uses H=Q+s*1 with nonzero "
                     "exact s chosen only after the D12 Q output."),
    }
    core.require(hashlib.sha256(Path(args.source).read_bytes()).hexdigest() ==
                 core.SOURCE_SHA, "source mutated during analysis")
    data = core.canonical_bytes(payload)
    fd, identity = core.reserve_output(args.output)
    published = False
    try:
        core.publish_reserved(fd, args.output, identity, data)
        published = True
    finally:
        os.close(fd)
        if not published and core.owned_path(args.output, identity):
            os.unlink(args.output)
    print(json.dumps({
        "output": args.output,
        "output_sha256": hashlib.sha256(data).hexdigest(),
        "q_quotient": payload["q_quotient"],
        "maximum": maximum_decimal,
        "maximum_minus_q": payload["maximum_minus_q_decimal160"],
        "h_equal_one_plus_q_quotient":
            payload["h_equal_one_plus_q_quotient"],
    }, indent=2))


if __name__ == "__main__":
    main()
