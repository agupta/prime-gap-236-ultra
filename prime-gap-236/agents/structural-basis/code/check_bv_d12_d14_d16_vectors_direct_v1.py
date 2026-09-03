#!/usr/bin/env python3
"""Cache-free exact reconstruction of the frozen D12/D14/D16 vectors.

The D12 and D14 inputs are legacy generalized-eigenvector artifacts whose
recorded integrator hash predates the current source tree.  This checker uses
only their explicit rational basis/vector data and reconstructs I(F) and
48 J(F,F) with the current pinned recurrence.  The D16 input was refined from
a cached matrix, but its particular-vector forms are reconstructed in exactly
the same cache-free way.  No optimal-eigenvalue claim is made.
"""

from __future__ import annotations

from fractions import Fraction as Q
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import time


if hasattr(sys, "set_int_max_str_digits"):
    sys.set_int_max_str_digits(0)

FILE = Path(__file__).resolve()
REPO = FILE.parents[3]
SCAN = REPO / "agents/small-delta-frontier/scan_bv_epsilon_fixed.py"
SCAN_SHA256 = "96495079a18039a0a7b0522e83ac455cbe5ff144598fff6b382f2c2953958de9"
INTEGRATOR = REPO / "agents/exact-integrator/src/exact_integrator.py"
INTEGRATOR_SHA256 = "941ee82bc72fd8488a95eb5e536fe47f8c95d39a1b618dae7d6ef7eb27122e52"

CANDIDATES = (
    {
        "name": "D12",
        "degree": 12,
        "dimension": 120,
        "path": REPO / "agents/exact-integrator/results/aquarter_fullsimplex_k48_B12.json",
        "sha256": "b64591f6694d78dfe1dcf99d25a18058d987d94cdb3e1a02f7ade12af90ac4de",
        "recorded_integrator_sha256": "95877b624be5852b4809f812d10b610d29d41259c9382d6cc7db99a77df6cc3c",
        "provenance": "legacy exact generalized-eigenvector artifact",
    },
    {
        "name": "D14",
        "degree": 14,
        "dimension": 195,
        "path": REPO / "agents/exact-integrator/results/aquarter_fullsimplex_k48_B14.json",
        "sha256": "b2f8b726ed2051053fa0c516f605ad9a62e5193292ee8ae9c3f38eb13a59cd6e",
        "recorded_integrator_sha256": "95877b624be5852b4809f812d10b610d29d41259c9382d6cc7db99a77df6cc3c",
        "provenance": "legacy exact generalized-eigenvector artifact",
    },
    {
        "name": "D16",
        "degree": 16,
        "dimension": 307,
        "path": REPO / "agents/small-delta-frontier/bv_aquarter_B16_vector_exact.json",
        "sha256": "59715ddffa483c696c035634a81c3cc8ffe882e9d6eaceec74bea23996b72d62",
        "recorded_integrator_sha256": INTEGRATOR_SHA256,
        "provenance": "cache-discovered 36-digit rational vector; exact particular forms only",
    },
)

K = 48
ALPHA = Q(103, 400)
ETA = Q(97, 400)
DELTA_SOURCE = Q(7, 250)
DELTA_TARGET = Q(1, 60)
EXPECTED_PARAMETERS = {
    "alpha": str(ALPHA), "eta": str(ETA), "delta": str(DELTA_SOURCE),
    "beta1": str(ALPHA), "beta2": str(ALPHA), "beta3plus": str(ALPHA),
}


def sha256(value: bytes | Path) -> str:
    data = value if isinstance(value, bytes) else value.read_bytes()
    return hashlib.sha256(data).hexdigest()


def strict_json(data: bytes, path: Path):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError(f"duplicate JSON key {key!r} in {path}")
            result[key] = value
        return result
    return json.loads(
        data, object_pairs_hook=pairs,
        parse_constant=lambda token: (_ for _ in ()).throw(
            ValueError(f"nonfinite JSON token {token!r} in {path}")))


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


def parse_candidate(specification, scan):
    path = specification["path"]
    raw = path.read_bytes()
    if sha256(raw) != specification["sha256"]:
        raise RuntimeError(f"candidate hash mismatch: {path}")
    data = strict_json(raw, path)
    degree = specification["degree"]
    dimension = specification["dimension"]
    basis = tuple((int(a), tuple(int(x) for x in lam))
                  for a, lam in data.get("basis", ()))
    vector = tuple(Q(x) for x in data.get("rational_vector", ()))
    if (data.get("k") != K or data.get("degree") != degree or
            data.get("parameters") != EXPECTED_PARAMETERS or
            data.get("integrator_sha256") !=
                specification["recorded_integrator_sha256"] or
            len(basis) != dimension or len(vector) != dimension or
            len(set(basis)) != dimension or not any(vector) or
            basis != canonical_basis(scan.ei, degree)):
        raise ValueError(f"candidate identity mismatch: {path}")
    return raw, data, basis, vector


def reconstruct_one(specification, scan):
    raw, data, basis, vector = parse_candidate(specification, scan)
    started = time.monotonic()
    source = scan.direct_forms(K, basis, vector, ALPHA, ETA, DELTA_SOURCE)
    target = scan.direct_forms(K, basis, vector, ALPHA, ETA, DELTA_TARGET)
    if source != target:
        raise ArithmeticError("full-simplex forms changed when delta changed")
    denominator, numerator, squares, marginals, marginal_squares = target
    if denominator <= 0 or denominator - numerator <= 0:
        raise ArithmeticError("expected a positive norm and positive deficit")
    quotient = numerator / denominator
    recorded_value = data.get("exact_quotient_decimal")
    if recorded_value is None:
        recorded_value = data.get("exact_quotient")
    recorded_decimal = Q(str(recorded_value))
    decimal_error = abs(quotient - recorded_decimal)
    # Legacy JSON stores only a rounded floating rendering; five ulps at its
    # displayed precision is deliberately generous and is not used downstream.
    if specification["name"] != "D16" and decimal_error > Q(5, 10**15):
        raise ArithmeticError("direct quotient disagrees with recorded decimal")
    if specification["name"] == "D16":
        if (Q(data.get("exact_denominator", "0")) != denominator or
                Q(data.get("exact_numerator", "0")) != numerator or
                Q(data.get("exact_quotient", "0")) != quotient or
                data.get("particular_vector_forms_rigorous") is not True):
            raise ArithmeticError("D16 recorded exact forms mismatch")
    return {
        "name": specification["name"],
        "degree": specification["degree"],
        "basis_dimension": specification["dimension"],
        "basis": [[a, list(lam)] for a, lam in basis],
        "rational_vector": [str(x) for x in vector],
        "candidate_path": str(specification["path"].relative_to(REPO)),
        "candidate_sha256": specification["sha256"],
        "candidate_recorded_integrator_sha256":
            specification["recorded_integrator_sha256"],
        "candidate_provenance": specification["provenance"],
        "legacy_integrator_source_present_in_current_tree": (
            specification["recorded_integrator_sha256"] == INTEGRATOR_SHA256),
        "exact_denominator": str(denominator),
        "exact_numerator_48J": str(numerator),
        "exact_quotient": str(quotient),
        "exact_normalized_deficit": str((denominator - numerator) / denominator),
        "recorded_decimal_absolute_error": str(decimal_error),
        "term_counts": {
            "square_product_groups": squares,
            "marginal_groups": marginals,
            "marginal_square_product_groups": marginal_squares,
        },
        "reconstruction_seconds": time.monotonic() - started,
    }


def build():
    snapshots = {path: path.read_bytes() for path in (FILE, SCAN, INTEGRATOR)}
    if sha256(snapshots[SCAN]) != SCAN_SHA256:
        raise RuntimeError("pinned scan source changed")
    if sha256(snapshots[INTEGRATOR]) != INTEGRATOR_SHA256:
        raise RuntimeError("pinned integrator source changed")
    candidate_snapshots = {
        item["path"]: item["path"].read_bytes() for item in CANDIDATES}
    scan = load_module("bv_lower_vectors_direct_scan_v1", SCAN)
    scan.self_test()
    rows = [reconstruct_one(item, scan) for item in CANDIDATES]
    if (any(path.read_bytes() != payload for path, payload in snapshots.items()) or
            any(path.read_bytes() != payload
                for path, payload in candidate_snapshots.items())):
        raise RuntimeError("source closure changed during reconstruction")
    return {
        "format": "bv-d12-d14-d16-vectors-cache-free-direct-check-v1",
        "status": "INDEPENDENT EXACT LOWER-DEGREE PARTICULAR VECTORS PASS",
        "rigorous": True,
        "cache_read": False,
        "serialized_matrix_entries_read": False,
        "claim_scope": (
            "exact I and 48J for each explicit rational particular vector; "
            "no finite-space optimum or capped-geometry claim"),
        "k": K,
        "parameters": {
            "alpha": str(ALPHA), "eta": str(ETA),
            "source_delta": str(DELTA_SOURCE),
            "target_delta": str(DELTA_TARGET),
            "full_simplex_delta_independence_exact": True,
        },
        "rows": rows,
        "checker_sha256": sha256(snapshots[FILE]),
        "source_hashes": {
            str(SCAN.relative_to(REPO)): SCAN_SHA256,
            str(INTEGRATOR.relative_to(REPO)): INTEGRATOR_SHA256,
        },
        "theorem_ready": False,
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
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = build()
    payload = canonical_json(result)
    publish_exclusive(args.output, payload)
    print(json.dumps({
        "status": result["status"],
        "output_sha256": sha256(payload),
        "rows": [{
            "name": row["name"], "exact_quotient": row["exact_quotient"],
            "term_counts": row["term_counts"],
            "seconds": row["reconstruction_seconds"],
        } for row in result["rows"]],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
