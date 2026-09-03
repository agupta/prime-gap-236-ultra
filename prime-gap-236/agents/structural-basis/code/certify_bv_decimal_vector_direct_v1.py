#!/usr/bin/env python3
"""Cache-free exact contraction of a run_basis Decimal vector.

This is a particular-vector checker, not an eigenvalue certificate.  It
rebuilds the finite polynomial from the source run's Decimal discovery vector,
rationalizes every coefficient on an explicit significant-digit grid, and
contracts the square and one-coordinate marginal directly.  It never reads a
matrix cache or trusts the source run's serialized matrix entries.
"""

from __future__ import annotations

import argparse
from decimal import Decimal, localcontext
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
REPO = FILE.parents[3]
SCAN = REPO / "agents/small-delta-frontier/scan_bv_epsilon_fixed.py"
INTEGRATOR = REPO / "agents/exact-integrator/src/exact_integrator.py"
K = 48
ALPHA = Q(103, 400)
ETA = Q(97, 400)
DELTA_SOURCE = Q(7, 250)
DELTA_TARGET = Q(1, 60)


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
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError(f"duplicate key {key!r} in {source}")
            result[key] = value
        return result

    return json.loads(
        data, object_pairs_hook=pairs,
        parse_constant=lambda token: (_ for _ in ()).throw(
            ValueError(f"nonfinite JSON token {token} in {source}")))


def rationalize_significant(text: str, digits: int) -> Q:
    if type(text) is not str or type(digits) is not int or not 1 <= digits <= 100:
        raise ValueError("bad Decimal coefficient or digit count")
    with localcontext() as ctx:
        ctx.prec = digits + 20
        value = Decimal(text)
        if not value.is_finite():
            raise ValueError("nonfinite Decimal coefficient")
        if not value:
            return Q(0)
        return Q(format(value, f".{digits - 1}E"))


def expected_basis(ei, degree: int):
    basis = list(ei.even_basis(degree))
    basis.sort(key=lambda x: (
        x[0] + sum(x[1]), sum(x[1]), len(x[1]), x[1], x[0]))
    return tuple(basis)


def build(run_path: Path, expected_run_sha: str, degree: int, digits: int):
    start_self = FILE.read_bytes()
    scan_bytes, integrator_bytes = SCAN.read_bytes(), INTEGRATOR.read_bytes()
    run_bytes = run_path.read_bytes()
    if sha256(run_bytes) != expected_run_sha:
        raise ValueError("source run SHA-256 mismatch")
    run = strict_json(run_bytes, run_path)
    scan = load_module("bv_decimal_direct_scan_v1", SCAN)
    scan.self_test()
    ei = scan.ei
    basis = tuple((int(a), tuple(int(x) for x in lam))
                  for a, lam in run.get("basis", ()))
    wanted = expected_basis(ei, degree)
    expected_dimension = {18: 471, 20: 707}.get(degree)
    if expected_dimension is None:
        raise ValueError("this checker permits only the frozen D18/D20 ladder")
    if basis != wanted or len(basis) != expected_dimension:
        raise ValueError("source run basis inventory mismatch")
    params = run.get("parameters")
    expected_params = {
        "alpha": str(ALPHA), "delta": str(DELTA_SOURCE),
        "eta": str(ETA), "beta1": str(ALPHA),
        "beta2": str(ALPHA), "beta3plus": str(ALPHA),
    }
    if ((run.get("k"), run.get("degree"), run.get("basis_dimension")) !=
            (K, degree, expected_dimension) or params != expected_params):
        raise ValueError("source run parameter mismatch")
    if run.get("integrator_sha256") != sha256(integrator_bytes):
        raise ValueError("source run integrator provenance mismatch")
    decimals = run.get("decimal_vector")
    if not isinstance(decimals, list) or len(decimals) != expected_dimension:
        raise ValueError("source run Decimal vector mismatch")
    vector = tuple(rationalize_significant(x, digits) for x in decimals)
    if not any(vector):
        raise ArithmeticError("zero rationalized vector")

    source_forms = scan.direct_forms(
        K, basis, vector, ALPHA, ETA, DELTA_SOURCE)
    target_forms = scan.direct_forms(
        K, basis, vector, ALPHA, ETA, DELTA_TARGET)
    if source_forms != target_forms:
        raise ArithmeticError("full-simplex forms changed with delta")
    denominator, numerator, square_terms, marginal_terms, marginal_square = (
        target_forms)
    if denominator <= 0:
        raise ArithmeticError("nonpositive exact denominator")
    quotient = numerator / denominator
    if (FILE.read_bytes() != start_self or SCAN.read_bytes() != scan_bytes or
            INTEGRATOR.read_bytes() != integrator_bytes or
            run_path.read_bytes() != run_bytes):
        raise RuntimeError("source closure changed during direct contraction")
    return {
        "format": "bv-decimal-vector-direct-exact-v1",
        "status": "EXACT PARTICULAR INNER VECTOR",
        "theorem_ready": False,
        "never_implies": [
            "largest finite-dimensional eigenvalue", "a capped quotient",
            "Proposition 1", "H1<=236"],
        "k": K, "degree": degree, "basis_dimension": expected_dimension,
        "parameters": {
            "alpha": str(ALPHA), "eta": str(ETA),
            "source_delta": str(DELTA_SOURCE),
            "target_delta": str(DELTA_TARGET),
            "full_simplex_delta_independence_exact": True,
        },
        "rationalization_significant_digits": digits,
        "basis": [[a, list(lam)] for a, lam in basis],
        "rational_vector": [str(x) for x in vector],
        "exact_denominator": str(denominator),
        "exact_numerator": str(numerator),
        "exact_quotient": str(quotient),
        "exact_margin_to_one": str(numerator - denominator),
        "denominator_positive": True,
        "margin_positive": numerator > denominator,
        "term_counts": {
            "square": square_terms, "marginal": marginal_terms,
            "marginal_square": marginal_square,
        },
        "discovery_decimal_eigenvalue": run.get(
            "decimal_generalized_eigenvalue"),
        "source_run_sha256": expected_run_sha,
        "checker_sha256": sha256(start_self),
        "source_hashes": {
            str(SCAN.relative_to(REPO)): sha256(scan_bytes),
            str(INTEGRATOR.relative_to(REPO)): sha256(integrator_bytes),
        },
    }


def canonical_json(value) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"),
                       allow_nan=False) + "\n").encode("ascii")


def publish_exclusive(path: Path, payload: bytes) -> None:
    target = path.resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o444)
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("run_result", type=Path)
    parser.add_argument("--expected-run-sha", required=True)
    parser.add_argument("--degree", type=int, required=True, choices=(18, 20))
    parser.add_argument("--digits", type=int, default=60)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = build(args.run_result.resolve(), args.expected_run_sha,
                   args.degree, args.digits)
    payload = canonical_json(result)
    publish_exclusive(args.output, payload)
    print(json.dumps({
        "output_sha256": sha256(payload),
        "exact_quotient": result["exact_quotient"],
        "margin_positive": result["margin_positive"],
        "term_counts": result["term_counts"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
