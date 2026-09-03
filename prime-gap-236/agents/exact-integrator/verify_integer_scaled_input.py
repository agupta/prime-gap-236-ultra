#!/usr/bin/env python3
"""Independent fail-closed checker for an integer-scaled vector JSON."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from fractions import Fraction
from math import gcd
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("source_json")
    parser.add_argument("scaled_json")
    args = parser.parse_args()
    source_bytes = Path(args.source_json).read_bytes()
    scaled_bytes = Path(args.scaled_json).read_bytes()
    source = json.loads(source_bytes)
    scaled = json.loads(scaled_bytes)
    expected_top_keys = {"status", "k", "degree", "basis_dimension", "basis",
                         "rational_vector", "integer_scaling"}
    if not isinstance(scaled, dict) or set(scaled) != expected_top_keys:
        raise SystemExit("scaled input has an incomplete or unexpected top-level schema")
    if scaled["status"] != "exact-integer-scaled-fixed-vector-input":
        raise SystemExit("scaled input status mismatch")
    meta = scaled.get("integer_scaling", {})
    expected_meta_keys = {"source_json", "source_sha256",
                          "least_common_denominator", "form_scale",
                          "quotient_and_margin_sign_preserved"}
    if not isinstance(meta, dict) or set(meta) != expected_meta_keys:
        raise SystemExit("integer_scaling metadata schema mismatch")
    expected_source_metadata = (Path("results") /
                                Path(args.source_json).name).as_posix()
    if meta["source_json"] != expected_source_metadata:
        raise SystemExit("integer_scaling source_json mismatch")
    if meta["form_scale"] != "least_common_denominator^2":
        raise SystemExit("form_scale metadata mismatch")
    if meta["quotient_and_margin_sign_preserved"] is not True:
        raise SystemExit("sign-preservation metadata mismatch")
    source_hash = hashlib.sha256(source_bytes).hexdigest()
    if meta.get("source_sha256") != source_hash:
        raise SystemExit("source SHA mismatch")
    if scaled.get("k") != source.get("k") or scaled.get("degree") != source.get("degree"):
        raise SystemExit("k/degree mismatch")
    if scaled.get("basis") != source.get("basis"):
        raise SystemExit("basis mismatch")
    if (not isinstance(scaled["basis_dimension"], int) or
            scaled["basis_dimension"] != len(scaled["basis"]) or
            scaled["basis_dimension"] != source.get("basis_dimension")):
        raise SystemExit("basis_dimension mismatch")
    original = [Fraction(x) for x in source.get("rational_vector", [])]
    raw_scaled = scaled.get("rational_vector")
    if not isinstance(raw_scaled, list) or len(raw_scaled) != len(original):
        raise SystemExit("scaled vector length mismatch")
    integers = []
    for raw in raw_scaled:
        if not isinstance(raw, str) or re.fullmatch(r"(?:0|-?[1-9][0-9]*)", raw) is None:
            raise SystemExit("scaled vector contains a noncanonical integer token")
        integers.append(int(raw))
    raw_common = meta.get("least_common_denominator")
    if (not isinstance(raw_common, str) or
            re.fullmatch(r"[1-9][0-9]*", raw_common) is None):
        raise SystemExit("least_common_denominator is not a canonical positive integer")
    common = int(raw_common)
    if common <= 0 or any(common % value.denominator for value in original):
        raise SystemExit("claimed common denominator does not clear the vector")
    # Reconstruct the LCM independently via gcd, rather than trusting metadata
    # or the generator's call to math.lcm.
    expected_common = 1
    for value in original:
        expected_common = (expected_common //
                           gcd(expected_common, value.denominator) *
                           value.denominator)
    if common != expected_common:
        raise SystemExit("claimed common denominator is not the exact LCM")
    for index, (value, integer) in enumerate(zip(original, integers)):
        if value * common != integer:
            raise SystemExit(f"scaled coefficient mismatch at index {index}")
    # A primitive integer vector is a useful independent consequence of using
    # the least common denominator of reduced fractions.
    content = 0
    for integer in integers:
        content = gcd(content, abs(integer))
    if content != 1:
        raise SystemExit(f"scaled vector unexpectedly has content {content}")
    print("INTEGER-SCALED INPUT PASS")
    print(f"source_sha256={source_hash}")
    print(f"scaled_sha256={hashlib.sha256(scaled_bytes).hexdigest()}")
    print(f"dimension={len(integers)}")
    print(f"least_common_denominator_bits={common.bit_length()}")
    print("integer_content=1")


if __name__ == "__main__":
    main()
