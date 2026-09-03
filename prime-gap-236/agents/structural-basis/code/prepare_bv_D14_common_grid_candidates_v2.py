#!/usr/bin/env python3
"""Exact 10^-38/10^-40/10^-42 common-grid D14 candidates.

Version 1 established that 10^-12 through 10^-16 catastrophically destroy the
ill-conditioned D14 coordinate.  This refinement keeps roughly the original
40-decimal-digit coefficient accuracy while replacing unrelated denominators
by one shared power-of-ten grid.
"""

from __future__ import annotations

import argparse
from fractions import Fraction as Q
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import resource
import sys
import time


if hasattr(sys, "set_int_max_str_digits"):
    sys.set_int_max_str_digits(0)

FILE = Path(__file__).resolve()
REPO = FILE.parents[3]
V1 = FILE.with_name("prepare_bv_D14_common_grid_candidates_v1.py")
V1_SHA256 = "55eece4f4fc15ae2112a55bb78eafd6d3e10f4e2a21d6a5981a165e853692787"
V1_RESULT = REPO / (
    "agents/structural-basis/results/bv_D14_common_grid_candidates_exact_v1.json")
V1_RESULT_SHA256 = "761bc005f666d57ac459d54d53a18f7b7c771c15c3af26e807bdac03d8810309"
V1_TEST = REPO / (
    "agents/structural-basis/tests/test_prepare_bv_D14_common_grid_candidates_v1.py")
V1_TEST_SHA256 = "f9f584630bb56c0e95491cafa447f58ea53ec2ed2a960336d2d7a891ad53c325"
GRID_DIGITS = (38, 40, 42)


def sha256(value):
    data = value if isinstance(value, bytes) else Path(value).read_bytes()
    return hashlib.sha256(data).hexdigest()


def load(name, path, expected):
    if sha256(path) != expected:
        raise RuntimeError(f"pinned D14 grid-v2 input changed: {path}")
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def build():
    snapshots = {path: path.read_bytes()
                 for path in (FILE, V1, V1_RESULT, V1_TEST)}
    for path, expected in ((V1, V1_SHA256), (V1_RESULT, V1_RESULT_SHA256),
                           (V1_TEST, V1_TEST_SHA256)):
        if sha256(snapshots[path]) != expected:
            raise RuntimeError(f"pinned D14 grid-v2 input changed: {path}")
    v1 = load("bv_D14_common_grid_v1_for_v2", V1, V1_SHA256)
    exact_row, basis, original = v1.load_d14()
    scan = v1.load_module("bv_D14_common_grid_scan_v2", v1.SCAN)
    scan.self_test()
    original_quotient = Q(exact_row["exact_quotient"])
    candidates = []
    started_all = time.monotonic()
    for digits in GRID_DIGITS:
        started = time.monotonic()
        vector = tuple(v1.round_common_grid(value, digits) for value in original)
        maximum_error = max(abs(left - right)
                            for left, right in zip(original, vector))
        if (maximum_error > Q(1, 2 * 10 ** digits) or
                max(abs(value) for value in vector) != 1):
            raise ArithmeticError("fine-grid rounding contract failed")
        denominator, numerator, square_count, marginal_count, marginal_square = \
            scan.direct_forms(v1.K, basis, vector, v1.ALPHA, v1.ETA, v1.DELTA)
        quotient = numerator / denominator
        if (denominator <= numerator or numerator <= 0 or
                (square_count, marginal_count, marginal_square) !=
                (3034, 195, 3034)):
            raise ArithmeticError("fine-grid exact form/inventory mismatch")
        candidates.append({
            "name": f"D14_grid_1e-{digits}",
            "grid_digits": digits,
            "rounding": "nearest integer after multiplication by 10^digits; exact ties to even",
            "basis_dimension": 195,
            "rational_vector": [str(value) for value in vector],
            "maximum_absolute_coefficient_error": str(maximum_error),
            "maximum_grid_units_error": str(maximum_error * 10 ** digits),
            "maximum_reduced_denominator_bits": max(
                value.denominator.bit_length() for value in vector),
            "maximum_absolute_coefficient": str(max(abs(x) for x in vector)),
            "nonzero_coefficients": sum(x != 0 for x in vector),
            "exact_denominator": str(denominator),
            "exact_numerator_48J": str(numerator),
            "exact_quotient": str(quotient),
            "exact_normalized_deficit": str((denominator - numerator) / denominator),
            "exact_quotient_minus_original": str(quotient - original_quotient),
            "absolute_quotient_change": str(abs(quotient - original_quotient)),
            "term_counts": {
                "square_product_groups": square_count,
                "marginal_groups": marginal_count,
                "marginal_square_product_groups": marginal_square,
            },
            "reconstruction_seconds": time.monotonic() - started,
        })
    if any(path.read_bytes() != payload for path, payload in snapshots.items()):
        raise RuntimeError("D14 grid-v2 source closure changed")
    return {
        "format": "bv-D14-fine-common-grid-candidates-exact-v2",
        "status": "EXACT D14 FINE COMMON-GRID PARTICULAR VECTORS PASS",
        "rigorous": True,
        "cache_read": False,
        "serialized_matrix_entries_read": False,
        "claim_scope": (
            "exact full-simplex I and 48J for 10^-38/10^-40/10^-42 "
            "rounded vectors; capped projection remains a separate gate"),
        "k": v1.K, "degree": 14, "basis_dimension": 195,
        "basis": [[a, list(lam)] for a, lam in basis],
        "source_D14": {
            "path": exact_row["candidate_path"],
            "sha256": exact_row["candidate_sha256"],
            "cache_free_direct_result_sha256": v1.LOWER_RESULT_SHA256,
            "exact_quotient": exact_row["exact_quotient"],
        },
        "coarse_grid_negative_control": {
            "path": str(V1_RESULT.relative_to(REPO)),
            "sha256": V1_RESULT_SHA256,
            "observed_exact_quotient_range": "approximately 0.22965 to 0.23514",
            "conclusion": "10^-12 through 10^-16 rejected",
        },
        "parameters": {"alpha": str(v1.ALPHA), "eta": str(v1.ETA),
                       "delta": str(v1.DELTA)},
        "candidates": candidates,
        "total_reconstruction_seconds": time.monotonic() - started_all,
        "peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "source_sha256": sha256(snapshots[FILE]),
        "source_hashes": {
            str(V1.relative_to(REPO)): V1_SHA256,
            str(V1_RESULT.relative_to(REPO)): V1_RESULT_SHA256,
            str(V1_TEST.relative_to(REPO)): V1_TEST_SHA256,
        },
        "launch_authorized": False,
        "exact_target_started": False,
        "resume_supported": False,
        "theorem_ready": False,
    }


def canonical_json(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"),
                       allow_nan=False) + "\n").encode("ascii")


def publish_exclusive(path, payload):
    target = Path(path).resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o444)
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = build()
    payload = canonical_json(result)
    publish_exclusive(args.output, payload)
    print(json.dumps({
        "status": result["status"], "output_sha256": sha256(payload),
        "seconds": result["total_reconstruction_seconds"],
        "peak_rss_kib": result["peak_rss_kib"],
        "candidates": [{
            "name": row["name"],
            "quotient": str(float(Q(row["exact_quotient"]))),
            "absolute_quotient_change":
                str(float(Q(row["absolute_quotient_change"]))),
            "max_denominator_bits": row["maximum_reduced_denominator_bits"],
        } for row in result["candidates"]],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
