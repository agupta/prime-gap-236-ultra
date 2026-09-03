#!/usr/bin/env python3
"""Generate an exact integer-scaled fixed-vector input.

If L is the least common multiple of all vector denominators, replacing F by
L*F multiplies I, J, and 48J-I by L^2 while preserving their quotient and sign.
The grouped evaluator can therefore avoid repeated gcd work on 272 unrelated
coefficient denominators without any change to its audited source.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from fractions import Fraction
from math import gcd, lcm
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("source_json")
    parser.add_argument("output_json")
    args = parser.parse_args()
    source_path = Path(args.source_json)
    output_path = Path(args.output_json)
    if output_path.exists():
        raise SystemExit(f"refusing to overwrite {output_path}")
    source_bytes = source_path.read_bytes()
    source = json.loads(source_bytes)
    basis = source["basis"]
    vector = [Fraction(x) for x in source["rational_vector"]]
    if len(basis) != len(vector) or len(set(map(str, basis))) != len(basis):
        raise SystemExit("source basis/vector is malformed")
    common = 1
    for value in vector:
        common = lcm(common, value.denominator)
    integers = [value * common for value in vector]
    if any(value.denominator != 1 for value in integers):
        raise AssertionError("LCM failed to clear a denominator")
    content = 0
    for value in integers:
        content = gcd(content, abs(value.numerator))
    if content != 1:
        raise SystemExit(f"integer-scaled vector is not primitive: content={content}")
    output = {
        "status": "exact-integer-scaled-fixed-vector-input",
        "k": source["k"],
        "degree": source["degree"],
        "basis_dimension": len(basis),
        "basis": basis,
        "rational_vector": [str(value.numerator) for value in integers],
        "integer_scaling": {
            "source_json": (Path("results") / source_path.name).as_posix(),
            "source_sha256": hashlib.sha256(source_bytes).hexdigest(),
            "least_common_denominator": str(common),
            "form_scale": "least_common_denominator^2",
            "quotient_and_margin_sign_preserved": True,
        },
    }
    output_path.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print("INTEGER-SCALED INPUT WRITTEN")
    print(f"source_sha256={output['integer_scaling']['source_sha256']}")
    print(f"least_common_denominator_bits={common.bit_length()}")
    print(f"least_common_denominator_digits={len(str(common))}")
    print(f"output_sha256={hashlib.sha256(output_path.read_bytes()).hexdigest()}")


if __name__ == "__main__":
    main()
