#!/usr/bin/env python3
"""Fail-closed wrapper for the cache-free BV rational-vector checker.

Revision 1 reconstructs the exact forms correctly, but its wire parser could
coerce a JSON float in a basis exponent through ``int``.  This revision pins
that reconstruction engine, validates every mathematical wire type before it
is called, and binds both source files for the duration of the run.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import sys
from fractions import Fraction as Q


if hasattr(sys, "set_int_max_str_digits"):
    sys.set_int_max_str_digits(0)

FILE = Path(__file__).resolve()
V1 = FILE.with_name("check_bv_rational_vector_direct_v1.py")
V1_SHA256 = "63bd2a3adc84191d212d52d3175179f583a1257d7c862f1ee07ecaa2ade3b7d3"
DIMENSIONS = {19: 568, 20: 707}
RATIONAL_WIRE = re.compile(r"-?(?:0|[1-9][0-9]*)(?:/[1-9][0-9]*)?\Z")


def sha256(value: bytes | Path) -> str:
    data = value if isinstance(value, bytes) else value.read_bytes()
    return hashlib.sha256(data).hexdigest()


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def strict_json(data: bytes, source: Path):
    def pairs(items):
        answer = {}
        for key, value in items:
            if key in answer:
                raise ValueError(f"duplicate key {key!r} in {source}")
            answer[key] = value
        return answer

    return json.loads(
        data, object_pairs_hook=pairs,
        parse_constant=lambda token: (_ for _ in ()).throw(
            ValueError(f"nonfinite JSON token {token} in {source}")))


def require_exact_int(value, label: str, *, nonnegative: bool = False):
    if type(value) is not int or (nonnegative and value < 0):
        raise ValueError(f"{label} must be an exact JSON integer")
    return value


def validate_candidate_wire(candidate, basis_degree: int):
    """Reject lossy coercions before the pinned v1 arithmetic is entered."""
    if type(candidate) is not dict or basis_degree not in DIMENSIONS:
        raise ValueError("invalid candidate object or basis degree")
    dimension = DIMENSIONS[basis_degree]
    for key in ("k", "degree", "basis_dimension"):
        require_exact_int(candidate.get(key), key, nonnegative=True)
    basis = candidate.get("basis")
    if type(basis) is not list or len(basis) != dimension:
        raise ValueError("basis wire inventory mismatch")
    for row_index, row in enumerate(basis):
        if type(row) is not list or len(row) != 2:
            raise ValueError(f"basis[{row_index}] must be a two-item JSON list")
        require_exact_int(row[0], f"basis[{row_index}][0]", nonnegative=True)
        lam = row[1]
        if type(lam) is not list:
            raise ValueError(f"basis[{row_index}][1] must be a JSON list")
        for part_index, part in enumerate(lam):
            require_exact_int(
                part, f"basis[{row_index}][1][{part_index}]",
                nonnegative=True)
    vector = candidate.get("rational_vector")
    if type(vector) is not list or len(vector) != dimension or any(
            type(value) is not str for value in vector):
        raise ValueError("rational vector must be a complete string list")
    for index, value in enumerate(vector):
        if RATIONAL_WIRE.fullmatch(value) is None or str(Q(value)) != value:
            raise ValueError(
                f"rational_vector[{index}] is not a canonical rational")
    for key in ("exact_denominator", "exact_numerator", "exact_quotient",
                "exact_deficit_over_denominator"):
        value = candidate.get(key)
        if (type(value) is not str or RATIONAL_WIRE.fullmatch(value) is None or
                str(Q(value)) != value):
            raise ValueError(f"{key} must be a canonical rational string")
    return candidate


def build(candidate_path: Path, expected_candidate_sha: str,
          basis_degree: int):
    start_self = FILE.read_bytes()
    start_v1 = V1.read_bytes()
    if sha256(start_v1) != V1_SHA256:
        raise RuntimeError("pinned v1 reconstruction checker changed")
    if (type(expected_candidate_sha) is not str or
            re.fullmatch(r"[0-9a-f]{64}", expected_candidate_sha) is None):
        raise ValueError("expected candidate SHA-256 must be lowercase hex")
    candidate_bytes = candidate_path.read_bytes()
    if sha256(candidate_bytes) != expected_candidate_sha:
        raise ValueError("candidate SHA-256 mismatch")
    candidate = strict_json(candidate_bytes, candidate_path)
    validate_candidate_wire(candidate, basis_degree)

    v1 = load_module("bv_rational_direct_checker_v2_pinned_v1", V1)
    result = v1.build(candidate_path, expected_candidate_sha, basis_degree)
    if (FILE.read_bytes() != start_self or V1.read_bytes() != start_v1 or
            candidate_path.read_bytes() != candidate_bytes):
        raise RuntimeError("v2 checker source closure changed")
    result["format"] = "bv-rational-vector-cache-free-direct-check-v2"
    result["checker_sha256"] = sha256(start_self)
    result["pinned_v1_reconstruction_checker_sha256"] = V1_SHA256
    result["wire_types_validated_before_reconstruction"] = True
    return result


def canonical_json(value) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"),
                       allow_nan=False) + "\n").encode("ascii")


def publish_exclusive(path: Path, payload: bytes):
    target = path.resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o444)
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("candidate", type=Path)
    parser.add_argument("--expected-candidate-sha", required=True)
    parser.add_argument("--basis-degree", type=int, choices=(19, 20), required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = build(args.candidate.resolve(), args.expected_candidate_sha,
                   args.basis_degree)
    payload = canonical_json(result)
    publish_exclusive(args.output, payload)
    print(json.dumps({
        "output_sha256": sha256(payload),
        "status": result["status"],
        "exact_quotient": result["exact_quotient"],
        "exact_normalized_deficit": result["exact_normalized_deficit"],
        "term_counts": result["term_counts"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
