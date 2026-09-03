#!/usr/bin/env python3
"""Independent cache-free checker for a BV rational particular vector.

The input may have been discovered from a cached generalized-eigenvalue
calculation, but this checker never opens that cache and never trusts a matrix
entry from the producer.  It rebuilds the polynomial square and the
distinguished-coordinate marginal square from the explicit rational vector,
integrates both by the source recurrence, and compares the resulting exact
forms with the producer's claims.
"""

from __future__ import annotations

import argparse
from fractions import Fraction as Q
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys


if hasattr(sys, "set_int_max_str_digits"):
    sys.set_int_max_str_digits(0)

FILE = Path(__file__).resolve()
REPO = FILE.parents[1]
SCAN = REPO / "agents/small-delta-frontier/scan_bv_epsilon_fixed.py"
SCAN_SHA256 = (
    "96495079a18039a0a7b0522e83ac455cbe5ff144598fff6b382f2c2953958de9")
INTEGRATOR = REPO / "agents/exact-integrator/src/exact_integrator.py"
INTEGRATOR_SHA256 = (
    "941ee82bc72fd8488a95eb5e536fe47f8c95d39a1b618dae7d6ef7eb27122e52")
K = 48
ALPHA = Q(103, 400)
ETA = Q(97, 400)
DELTA_SOURCE = Q(7, 250)
DELTA_TARGET = Q(1, 60)
PARAMETERS = {
    "alpha": "103/400", "delta": "7/250", "eta": "97/400",
    "beta1": "103/400", "beta2": "103/400", "beta3plus": "103/400",
}
DIMENSIONS = {19: 568, 20: 707}


def sha256(value: bytes | Path) -> str:
    data = value if isinstance(value, bytes) else value.read_bytes()
    return hashlib.sha256(data).hexdigest()


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


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def canonical_basis(ei, degree: int):
    basis = list(ei.even_basis(degree))
    basis.sort(key=lambda x: (
        x[0] + sum(x[1]), sum(x[1]), len(x[1]), x[1], x[0]))
    return tuple(basis)


def parse_fraction_list(raw, length: int):
    if not isinstance(raw, list) or len(raw) != length or any(
            type(item) is not str for item in raw):
        raise ValueError("rational vector inventory mismatch")
    try:
        vector = tuple(Q(item) for item in raw)
    except (ValueError, ZeroDivisionError) as error:
        raise ValueError("malformed rational coefficient") from error
    if not any(vector):
        raise ArithmeticError("zero rational vector")
    return vector


def build(candidate_path: Path, expected_candidate_sha: str,
          basis_degree: int):
    start_self = FILE.read_bytes()
    fixed = {SCAN: SCAN_SHA256, INTEGRATOR: INTEGRATOR_SHA256}
    snapshots = {path: path.read_bytes() for path in fixed}
    for path, expected in fixed.items():
        if sha256(snapshots[path]) != expected:
            raise RuntimeError(f"pinned checker dependency changed: {path}")
    candidate_bytes = candidate_path.read_bytes()
    if sha256(candidate_bytes) != expected_candidate_sha:
        raise ValueError("candidate SHA-256 mismatch")
    candidate = strict_json(candidate_bytes, candidate_path)

    if basis_degree not in DIMENSIONS:
        raise ValueError("basis degree must be 19 or 20")
    dimension = DIMENSIONS[basis_degree]
    if (candidate.get("format") not in {
                "bv-d20-krylov-refinement-cacheconditional-v1",
                "bv-d20-warm-refinement-cacheconditional-v1"} or
            candidate.get("status") !=
                "EXACT PARTICULAR VECTOR CONDITIONAL ON CACHE" or
            candidate.get("rigorous_given_cache_entries") is not True or
            candidate.get("cache_entries_independently_reconstructed") is not False or
            candidate.get("theorem_ready") is not False or
            (candidate.get("k"), candidate.get("degree"),
             candidate.get("basis_dimension")) != (K, 20, dimension) or
            candidate.get("parameters") != PARAMETERS):
        raise ValueError("candidate identity/status mismatch")

    scan = load_module("bv_rational_direct_checker_v1_scan", SCAN)
    scan.self_test()
    basis = tuple((int(a), tuple(int(x) for x in lam))
                  for a, lam in candidate.get("basis", ()))
    if basis != canonical_basis(scan.ei, basis_degree):
        raise ValueError("candidate is not the complete canonical basis")
    vector = parse_fraction_list(candidate.get("rational_vector"), dimension)

    # Delta is geometrically inert here because every B_m equals alpha.  The
    # duplicate reconstruction is an exact guard against accidentally using a
    # capped-support branch in what should be the full-simplex inner form.
    source_forms = scan.direct_forms(
        K, basis, vector, ALPHA, ETA, DELTA_SOURCE)
    target_forms = scan.direct_forms(
        K, basis, vector, ALPHA, ETA, DELTA_TARGET)
    if source_forms != target_forms:
        raise ArithmeticError("full-simplex forms changed with delta")
    denominator, numerator, square_count, marginal_count, marginal_square_count = (
        target_forms)
    if denominator <= 0 or denominator - numerator <= 0:
        raise ArithmeticError("expected positive denominator and inner deficit")
    if (Q(candidate.get("exact_denominator", "0")) != denominator or
            Q(candidate.get("exact_numerator", "0")) != numerator or
            Q(candidate.get("exact_quotient", "0")) != numerator / denominator or
            Q(candidate.get("exact_deficit_over_denominator", "0")) !=
                (denominator - numerator) / denominator):
        raise ArithmeticError("cache-conditional claims disagree with direct forms")

    if (FILE.read_bytes() != start_self or
            any(path.read_bytes() != data for path, data in snapshots.items()) or
            candidate_path.read_bytes() != candidate_bytes):
        raise RuntimeError("checker source closure changed during reconstruction")
    return {
        "format": "bv-rational-vector-cache-free-direct-check-v1",
        "status": "INDEPENDENT EXACT PARTICULAR INNER VECTOR PASS",
        "rigorous": True,
        "cache_read": False,
        "serialized_matrix_entries_read": False,
        "theorem_ready": False,
        "never_implies": [
            "largest finite-dimensional eigenvalue", "a capped quotient",
            "Proposition 1", "H1<=236"],
        "k": K,
        "basis_degree": basis_degree,
        "basis_dimension": dimension,
        "parameters": {
            "alpha": str(ALPHA), "eta": str(ETA),
            "source_delta": str(DELTA_SOURCE),
            "target_delta": str(DELTA_TARGET),
            "full_simplex_delta_independence_exact": True,
        },
        "basis": [[a, list(lam)] for a, lam in basis],
        "rational_vector": [str(value) for value in vector],
        "exact_denominator": str(denominator),
        "exact_numerator": str(numerator),
        "exact_quotient": str(numerator / denominator),
        "exact_deficit": str(denominator - numerator),
        "exact_normalized_deficit": str(
            (denominator - numerator) / denominator),
        "denominator_positive": True,
        "deficit_positive": True,
        "term_counts": {
            "square": square_count,
            "marginal": marginal_count,
            "marginal_square": marginal_square_count,
        },
        "candidate_sha256": expected_candidate_sha,
        "candidate_producer_sha256": candidate.get("checker_sha256"),
        "checker_sha256": sha256(start_self),
        "source_hashes": {
            str(path.relative_to(REPO)): expected for path, expected in fixed.items()},
    }


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
