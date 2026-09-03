#!/usr/bin/env python3
"""Warm-start a source-bound B20 pencil from the exact refined B18 vector.

The generic run_basis power iteration starts from an unrelated dense vector
and can converge extremely slowly in the ill-conditioned high-degree basis.
This discovery/refinement driver embeds the independently exact B18 vector,
reuses the source-bound exact matrix cache, and performs the same Decimal LU
iteration from that warm start.  Its rationalized particular-vector forms are
exact conditional on the cache; a final claim still requires cache-free direct
reconstruction.
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
REFINER = REPO / "agents/small-delta-frontier/certify_bv_cached.py"
REFINER_SHA256 = (
    "1e1e9aece98190b06684be1c206583de72969218b4ec5a5dfaf374fb7d26d387")
INTEGRATOR = REPO / "agents/exact-integrator/src/exact_integrator.py"
INTEGRATOR_SHA256 = (
    "941ee82bc72fd8488a95eb5e536fe47f8c95d39a1b618dae7d6ef7eb27122e52")
RUN_BASIS = REPO / "agents/exact-integrator/run_basis.py"
RUN_BASIS_SHA256 = (
    "f660a30d8dd83f13459e0412ded1e28c7ec0864abb41ad04a396475a7905e1d4")
SEED = REPO / (
    "agents/exact-integrator/results/"
    "aquarter_fullsimplex_k48_B18_refined_exact.json")
SEED_SHA256 = (
    "af6f1eb0d75bc59caf20cc82f79a3cb339be3ac7280af2afcad89eca0e31cf58")
K = 48
PARAMETERS = {
    "alpha": "103/400", "delta": "7/250", "eta": "97/400",
    "beta1": "103/400", "beta2": "103/400", "beta3plus": "103/400",
}


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


def canonical_basis(ei, degree: int):
    basis = list(ei.even_basis(degree))
    basis.sort(key=lambda x: (
        x[0] + sum(x[1]), sum(x[1]), len(x[1]), x[1], x[0]))
    return tuple(basis)


def build(run_path: Path | None, expected_run_sha: str | None,
          prefix_dimension: int | None, cache: Path,
          expected_cache_sha: str, precision: int, iterations: int,
          trace_every: int, digits: int):
    start_self = FILE.read_bytes()
    fixed_paths = [REFINER, INTEGRATOR, RUN_BASIS, SEED, cache]
    if run_path is not None:
        fixed_paths.append(run_path)
    inputs = {path: path.read_bytes() for path in fixed_paths}
    expected = {
        REFINER: REFINER_SHA256, INTEGRATOR: INTEGRATOR_SHA256,
        RUN_BASIS: RUN_BASIS_SHA256, SEED: SEED_SHA256,
        cache: expected_cache_sha,
    }
    if run_path is not None:
        expected[run_path] = expected_run_sha
    for path, digest in expected.items():
        if sha256(inputs[path]) != digest:
            raise RuntimeError(f"source/input SHA-256 mismatch: {path}")
    if not (100 <= precision <= 1000 and 1 <= iterations <= 10000 and
            0 <= trace_every <= iterations and 20 <= digits < precision):
        raise ValueError("invalid refinement controls")

    # certify_bv_cached imports exact_integrator/run_basis by their ordinary
    # module names after inserting the source directories on sys.path.
    refiner = load_module("warm_d20_refiner_dependency_v1", REFINER)
    ei, rb = refiner.ei, refiner.rb
    seed = strict_json(inputs[SEED], SEED)
    full_basis = canonical_basis(ei, 20)
    if run_path is None:
        if prefix_dimension is None or not 472 <= prefix_dimension <= 707:
            raise ValueError("snapshot mode requires a canonical B20 prefix")
        run = None
        basis = full_basis[:prefix_dimension]
    else:
        if prefix_dimension is not None:
            raise ValueError("source-run and snapshot-prefix modes are exclusive")
        run = strict_json(inputs[run_path], run_path)
        basis = tuple((int(a), tuple(int(x) for x in lam))
                      for a, lam in run.get("basis", ()))
    seed_basis = tuple((int(a), tuple(int(x) for x in lam))
                       for a, lam in seed.get("basis", ()))
    seed_vector = tuple(Q(x) for x in seed.get("rational_vector", ()))
    if run is not None and (
            run.get("k") != K or run.get("degree") != 20 or
            run.get("basis_dimension") != len(basis) or
            not 472 <= len(basis) <= 707 or
            run.get("parameters") != PARAMETERS or
            run.get("integrator_sha256") != INTEGRATOR_SHA256 or
            basis != full_basis[:len(basis)]):
        raise ValueError("source run is not a canonical B20 prefix")
    if (seed.get("format") != "bv-even-exact-vector-v1" or
            (seed.get("k"), seed.get("degree")) != (K, 18) or
            seed_basis != canonical_basis(ei, 18) or
            basis[:471] != seed_basis or len(seed_vector) != 471):
        raise ValueError("refined B18 seed inventory mismatch")

    support = ei.OneStratumSupport(
        K, Q(PARAMETERS["alpha"]), Q(PARAMETERS["delta"]),
        Q(PARAMETERS["eta"]), Q(PARAMETERS["beta1"]),
        Q(PARAMETERS["beta2"]), Q(PARAMETERS["beta3plus"]))
    m1, m2, hits, misses = rb.cached_matrices(
        support, basis, str(cache), INTEGRATOR_SHA256)
    matrix_hash = refiner.matrix_sha(m1, m2)
    if (run is not None and matrix_hash != run.get("exact_matrices_sha256")) or misses:
        raise ValueError("cache reconstruction differs from the source run")
    # resumed_power accepts decimal coefficient strings, whereas the frozen
    # exact seed is serialized canonically as numerator/denominator strings.
    with localcontext() as context:
        context.prec = precision
        warm = [str(Decimal(x.numerator) / Decimal(x.denominator))
                for x in seed_vector]
    warm += ["0"] * (len(basis) - 471)
    trace, decimal_vector = refiner.resumed_power(
        m1, m2, warm, precision, iterations, trace_every)
    vector = [Q(format(x, f".{digits - 1}E")) if x else Q(0)
              for x in decimal_vector]
    denominator = ei.exact_quadratic(m1, vector)
    numerator = ei.exact_quadratic(m2, vector)
    if denominator <= 0:
        raise ArithmeticError("nonpositive exact denominator")
    if (FILE.read_bytes() != start_self or any(
            path.read_bytes() != data for path, data in inputs.items())):
        raise RuntimeError("source closure changed during refinement")
    return {
        "format": "bv-d20-warm-refinement-cacheconditional-v1",
        "status": "EXACT PARTICULAR VECTOR CONDITIONAL ON CACHE",
        "rigorous_given_cache_entries": True,
        "cache_entries_independently_reconstructed": False,
        "theorem_ready": False,
        "never_implies": ["a cache-free exact quotient", "a capped quotient",
                          "Proposition 1", "H1<=236"],
        "k": K, "degree": 20, "basis_dimension": len(basis),
        "basis": [[a, list(lam)] for a, lam in basis],
        "parameters": PARAMETERS,
        "seed_dimension": 471,
        "precision": precision, "iterations": iterations,
        "trace_every": trace_every,
        "power_trace": [[i, value] for i, value in trace],
        "rationalization_significant_digits": digits,
        "rational_vector": [str(x) for x in vector],
        "exact_denominator": str(denominator),
        "exact_numerator": str(numerator),
        "exact_quotient": str(numerator / denominator),
        "exact_deficit_over_denominator": str(
            (denominator - numerator) / denominator),
        "denominator_positive": True,
        "margin_positive": numerator > denominator,
        "matrix_sha256": matrix_hash,
        "cache_hits": hits, "cache_misses": misses,
        "input_mode": "source-run" if run is not None else "cache-snapshot-prefix",
        "source_run_sha256": expected_run_sha if run is not None else None,
        "source_hashes": {str(path.relative_to(REPO)) if path.is_relative_to(REPO)
                          else str(path): digest
                          for path, digest in expected.items()},
        "checker_sha256": sha256(start_self),
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
    parser.add_argument("run_result", type=Path, nargs="?")
    parser.add_argument("--expected-run-sha")
    parser.add_argument("--prefix-dimension", type=int)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--expected-cache-sha", required=True)
    parser.add_argument("--precision", type=int, default=180)
    parser.add_argument("--iterations", type=int, default=160)
    parser.add_argument("--trace-every", type=int, default=20)
    parser.add_argument("--digits", type=int, default=75)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if ((args.run_result is None) != (args.expected_run_sha is None) or
            (args.run_result is None) == (args.prefix_dimension is None)):
        parser.error("choose either a bound source run or --prefix-dimension")
    result = build(
        None if args.run_result is None else args.run_result.resolve(),
        args.expected_run_sha, args.prefix_dimension,
        args.cache.resolve(), args.expected_cache_sha, args.precision,
        args.iterations, args.trace_every, args.digits)
    payload = canonical_json(result)
    publish_exclusive(args.output, payload)
    print(json.dumps({
        "output_sha256": sha256(payload),
        "basis_dimension": result["basis_dimension"],
        "power_trace": result["power_trace"],
        "exact_quotient": result["exact_quotient"],
        "exact_deficit": result["exact_deficit_over_denominator"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
