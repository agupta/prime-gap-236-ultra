#!/usr/bin/env python3
"""Freeze exact common-grid roundings of the audited D14 particular vector.

The legacy D14 rational vector has approximately 133-bit denominators.  This
producer rounds every explicit coefficient to the nearest multiple of
10^-16, 10^-14, and 10^-12 (ties to even), then reconstructs full-simplex
I and 48J directly from each rounded vector with no matrix/cache input.
"""

from __future__ import annotations

import argparse
from fractions import Fraction as Q
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import resource
import sys
import time


if hasattr(sys, "set_int_max_str_digits"):
    sys.set_int_max_str_digits(0)

FILE = Path(__file__).resolve()
REPO = FILE.parents[3]
LOWER_CHECKER = FILE.with_name("check_bv_d12_d14_d16_vectors_direct_v1.py")
LOWER_CHECKER_SHA256 = "9d5224cd36190dee55f3eebc69e78ef93f81273acaa29ba6db13cd1c5b2fe0b2"
LOWER_RESULT = REPO / (
    "agents/structural-basis/results/bv_D12_D14_D16_vectors_direct_exact_v1.json")
LOWER_RESULT_SHA256 = "77884ae1197beace517fd758323e53b92d4cc8ef055ddf873ae4cd858625dbe4"
SCAN = REPO / "agents/small-delta-frontier/scan_bv_epsilon_fixed.py"
SCAN_SHA256 = "96495079a18039a0a7b0522e83ac455cbe5ff144598fff6b382f2c2953958de9"
INTEGRATOR = REPO / "agents/exact-integrator/src/exact_integrator.py"
INTEGRATOR_SHA256 = "941ee82bc72fd8488a95eb5e536fe47f8c95d39a1b618dae7d6ef7eb27122e52"
GRID_DIGITS = (16, 14, 12)
K = 48
ALPHA = Q(103, 400)
ETA = Q(97, 400)
DELTA = Q(1, 60)


def sha256(value):
    data = value if isinstance(value, bytes) else Path(value).read_bytes()
    return hashlib.sha256(data).hexdigest()


def strict_json(path):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError(f"duplicate JSON key {key!r} in {path}")
            result[key] = value
        return result
    return json.loads(
        Path(path).read_bytes(), object_pairs_hook=pairs,
        parse_constant=lambda token: (_ for _ in ()).throw(
            ValueError(f"nonfinite JSON token {token!r} in {path}")))


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def nearest_integer_ties_even(value: Q) -> int:
    floor = value.numerator // value.denominator
    remainder = value - floor
    if remainder < Q(1, 2):
        return floor
    if remainder > Q(1, 2):
        return floor + 1
    return floor if floor % 2 == 0 else floor + 1


def round_common_grid(value: Q, digits: int) -> Q:
    if type(digits) is not int or digits < 0:
        raise ValueError("grid digits must be a nonnegative integer")
    denominator = 10 ** digits
    return Q(nearest_integer_ties_even(value * denominator), denominator)


def load_d14():
    if sha256(LOWER_RESULT) != LOWER_RESULT_SHA256:
        raise RuntimeError("pinned lower-degree direct result changed")
    data = strict_json(LOWER_RESULT)
    rows = [row for row in data.get("rows", ()) if row.get("name") == "D14"]
    if (data.get("status") !=
            "INDEPENDENT EXACT LOWER-DEGREE PARTICULAR VECTORS PASS" or
            data.get("checker_sha256") != LOWER_CHECKER_SHA256 or
            len(rows) != 1):
        raise ValueError("D14 direct reconstruction identity mismatch")
    row = rows[0]
    basis = tuple((int(a), tuple(int(x) for x in lam))
                  for a, lam in row.get("basis", ()))
    vector = tuple(Q(x) for x in row.get("rational_vector", ()))
    if (row.get("degree") != 14 or row.get("basis_dimension") != 195 or
            len(basis) != 195 or len(vector) != 195 or
            max(abs(value) for value in vector) != 1 or
            row.get("term_counts") != {
                "square_product_groups": 3034, "marginal_groups": 195,
                "marginal_square_product_groups": 3034}):
        raise ValueError("D14 vector identity/inventory mismatch")
    return row, basis, vector


def build():
    snapshots = {path: path.read_bytes() for path in
                 (FILE, LOWER_CHECKER, LOWER_RESULT, SCAN, INTEGRATOR)}
    pins = {
        LOWER_CHECKER: LOWER_CHECKER_SHA256,
        LOWER_RESULT: LOWER_RESULT_SHA256,
        SCAN: SCAN_SHA256,
        INTEGRATOR: INTEGRATOR_SHA256,
    }
    for path, expected in pins.items():
        if sha256(snapshots[path]) != expected:
            raise RuntimeError(f"pinned grid-candidate input changed: {path}")
    exact_row, basis, original = load_d14()
    scan = load_module("bv_D14_common_grid_scan_v1", SCAN)
    scan.self_test()
    candidates = []
    started_all = time.monotonic()
    for digits in GRID_DIGITS:
        started = time.monotonic()
        vector = tuple(round_common_grid(value, digits) for value in original)
        errors = tuple(abs(left - right) for left, right in zip(original, vector))
        maximum_error = max(errors)
        if (maximum_error > Q(1, 2 * 10 ** digits) or
                max(abs(value) for value in vector) != 1):
            raise ArithmeticError("common-grid rounding contract failed")
        denominator, numerator, square_count, marginal_count, marginal_square = \
            scan.direct_forms(K, basis, vector, ALPHA, ETA, DELTA)
        if (denominator <= numerator or numerator <= 0 or
                (square_count, marginal_count, marginal_square) !=
                (3034, 195, 3034)):
            raise ArithmeticError("rounded D14 exact form/inventory mismatch")
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
            "nonzero_coefficients": sum(value != 0 for value in vector),
            "maximum_absolute_coefficient": str(max(abs(x) for x in vector)),
            "exact_denominator": str(denominator),
            "exact_numerator_48J": str(numerator),
            "exact_quotient": str(numerator / denominator),
            "exact_normalized_deficit": str((denominator - numerator) / denominator),
            "term_counts": {
                "square_product_groups": square_count,
                "marginal_groups": marginal_count,
                "marginal_square_product_groups": marginal_square,
            },
            "reconstruction_seconds": time.monotonic() - started,
        })
    if any(path.read_bytes() != payload for path, payload in snapshots.items()):
        raise RuntimeError("grid-candidate source closure changed")
    return {
        "format": "bv-D14-common-grid-candidates-exact-v1",
        "status": "EXACT D14 COMMON-GRID PARTICULAR VECTORS PASS",
        "rigorous": True,
        "cache_read": False,
        "serialized_matrix_entries_read": False,
        "claim_scope": (
            "exact full-simplex I and 48J for three rounded particular "
            "vectors; capped projection and finite-space optimality are not claimed"),
        "k": K,
        "degree": 14,
        "basis_dimension": 195,
        "basis": [[a, list(lam)] for a, lam in basis],
        "source_D14": {
            "path": exact_row["candidate_path"],
            "sha256": exact_row["candidate_sha256"],
            "cache_free_direct_result_path": str(LOWER_RESULT.relative_to(REPO)),
            "cache_free_direct_result_sha256": LOWER_RESULT_SHA256,
            "exact_quotient": exact_row["exact_quotient"],
            "maximum_absolute_coefficient": "1",
        },
        "parameters": {"alpha": str(ALPHA), "eta": str(ETA),
                       "delta": str(DELTA)},
        "candidates": candidates,
        "total_reconstruction_seconds": time.monotonic() - started_all,
        "peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "source_sha256": sha256(snapshots[FILE]),
        "source_hashes": {
            str(path.relative_to(REPO)): expected for path, expected in pins.items()},
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
            "name": row["name"], "quotient": row["exact_quotient"],
            "max_error": row["maximum_absolute_coefficient_error"],
            "max_denominator_bits": row["maximum_reduced_denominator_bits"],
            "seconds": row["reconstruction_seconds"],
        } for row in result["candidates"]],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
