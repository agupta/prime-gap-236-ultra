#!/usr/bin/env python3
"""Warm-started, A-orthogonal Krylov refinement for the BV B20 pencil.

This is a discovery/refinement producer.  It reconstructs exact rational
matrix entries from the source-bound cache, performs all large linear algebra
with Decimal arithmetic, and contracts the final rational vector exactly.
The particular-vector forms are rigorous conditional on those cache entries;
a theorem-facing result must still be replayed by a cache-free checker.

The motivation for the A-orthogonal Krylov space is numerical rather than
mathematical: ordinary generalized power iteration converges very slowly in
the badly conditioned monomial-orbit coordinates.  Ritz optimization in
span(v,Tv,...), T=A^{-1}B, retains the warm B18 direction while exposing the
new degree-19/20 directions much faster.
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


def dot(x, y):
    return sum((a * b for a, b in zip(x, y)), Decimal(0))


def matvec(matrix, vector):
    return [dot(row, vector) for row in matrix]


def lu_factor(matrix):
    """Decimal partial-pivoting LU, returning the row permutation."""
    n = len(matrix)
    lu = [row[:] for row in matrix]
    piv = list(range(n))
    for col in range(n):
        p = max(range(col, n), key=lambda i: abs(lu[i][col]))
        if lu[p][col] == 0:
            raise ArithmeticError("singular scaled Gram matrix")
        if p != col:
            lu[p], lu[col] = lu[col], lu[p]
            piv[p], piv[col] = piv[col], piv[p]
        pivot = lu[col][col]
        for i in range(col + 1, n):
            lu[i][col] /= pivot
            mul = lu[i][col]
            for j in range(col + 1, n):
                lu[i][j] -= mul * lu[col][j]
    return lu, piv


def lu_solve(lu, piv, rhs):
    n = len(lu)
    y = [rhs[piv[i]] for i in range(n)]
    for i in range(n):
        for j in range(i):
            y[i] -= lu[i][j] * y[j]
    x = y[:]
    for i in range(n - 1, -1, -1):
        for j in range(i + 1, n):
            x[i] -= lu[i][j] * x[j]
        x[i] /= lu[i][i]
    return x


def jacobi_top_symmetric(matrix, tolerance: Decimal, max_sweeps: int):
    """Largest eigenpair of a small Decimal symmetric matrix.

    Cyclic Jacobi rotations are slow for large matrices but exceptionally
    stable and dependency-free for the intended Krylov dimensions (<=40).
    """
    n = len(matrix)
    if n == 0 or any(len(row) != n for row in matrix):
        raise ValueError("Jacobi input must be nonempty and square")
    a = [[(matrix[i][j] + matrix[j][i]) / 2 for j in range(n)]
         for i in range(n)]
    vectors = [[Decimal(int(i == j)) for j in range(n)] for i in range(n)]
    rotations = 0
    for _ in range(max_sweeps):
        scale = max((abs(a[i][i]) for i in range(n)), default=Decimal(1))
        largest = max((abs(a[i][j]) for i in range(n)
                       for j in range(i + 1, n)), default=Decimal(0))
        if largest <= tolerance * max(scale, Decimal(1)):
            break
        for p in range(n - 1):
            for q in range(p + 1, n):
                apq = a[p][q]
                if abs(apq) <= tolerance * max(
                        abs(a[p][p]), abs(a[q][q]), Decimal(1)):
                    continue
                tau = (a[q][q] - a[p][p]) / (2 * apq)
                root = (Decimal(1) + tau * tau).sqrt()
                t = (Decimal(1) / (tau + root) if tau >= 0
                     else -Decimal(1) / (-tau + root))
                c = Decimal(1) / (Decimal(1) + t * t).sqrt()
                s = t * c
                app, aqq = a[p][p], a[q][q]
                a[p][p] = app - t * apq
                a[q][q] = aqq + t * apq
                a[p][q] = a[q][p] = Decimal(0)
                for r in range(n):
                    if r == p or r == q:
                        continue
                    arp, arq = a[r][p], a[r][q]
                    a[r][p] = a[p][r] = c * arp - s * arq
                    a[r][q] = a[q][r] = s * arp + c * arq
                for r in range(n):
                    vrp, vrq = vectors[r][p], vectors[r][q]
                    vectors[r][p] = c * vrp - s * vrq
                    vectors[r][q] = s * vrp + c * vrq
                rotations += 1
    else:
        raise ArithmeticError("Decimal Jacobi iteration did not converge")
    index = max(range(n), key=lambda i: a[i][i])
    vector = [vectors[i][index] for i in range(n)]
    norm = dot(vector, vector).sqrt()
    return a[index][index], [x / norm for x in vector], rotations


def krylov_refine_decimal(m1, m2, seed, precision: int, dimension: int,
                          jacobi_sweeps: int):
    """Return a Ritz vector in an A-orthogonal Krylov space.

    ``seed`` is in the original coordinates.  Returned coordinates are also
    original.  The trace contains the largest projected Rayleigh value after
    each added Krylov direction.
    """
    n = len(m1)
    if (n == 0 or len(m2) != n or len(seed) != n or
            any(len(row) != n for row in (*m1, *m2))):
        raise ValueError("matrix/vector dimension mismatch")
    if not 1 <= dimension <= min(n, 80):
        raise ValueError("invalid Krylov dimension")
    with localcontext() as context:
        context.prec = precision

        def dec(x):
            return (x if isinstance(x, Decimal)
                    else Decimal(x.numerator) / Decimal(x.denominator))

        scales = [dec(m1[i][i]).sqrt() for i in range(n)]
        if any(x == 0 for x in scales):
            raise ArithmeticError("zero diagonal in Gram matrix")
        a = [[dec(m1[i][j]) / scales[i] / scales[j] for j in range(n)]
             for i in range(n)]
        b = [[dec(m2[i][j]) / scales[i] / scales[j] for j in range(n)]
             for i in range(n)]
        lu, piv = lu_factor(a)

        q0 = [dec(seed[i]) * scales[i] for i in range(n)]
        aq0 = matvec(a, q0)
        norm2 = dot(q0, aq0)
        if norm2 <= 0:
            raise ArithmeticError("nonpositive seed A-norm")
        norm = norm2.sqrt()
        q0 = [x / norm for x in q0]
        vectors = [q0]
        b_images = []
        trace = []
        best_coefficients = [Decimal(1)]
        tolerance = Decimal(10) ** (-(precision - 20))

        for size in range(1, dimension + 1):
            while len(b_images) < len(vectors):
                b_images.append(matvec(b, vectors[len(b_images)]))
            projected = [[dot(vectors[i], b_images[j])
                          for j in range(size)] for i in range(size)]
            value, coeffs, rotations = jacobi_top_symmetric(
                projected, tolerance, jacobi_sweeps)
            trace.append((size, str(value), rotations))
            best_coefficients = coeffs
            if size == dimension:
                break

            raw = lu_solve(lu, piv, b_images[-1])
            # Two complete A-modified-Gram-Schmidt passes suppress the loss of
            # orthogonality caused by the ill-conditioned original orbit basis.
            for _ in range(2):
                araw = matvec(a, raw)
                coefficients = [dot(q, araw) for q in vectors]
                for coefficient, q in zip(coefficients, vectors):
                    if coefficient:
                        raw = [x - coefficient * y for x, y in zip(raw, q)]
            araw = matvec(a, raw)
            norm2 = dot(raw, araw)
            if norm2 <= tolerance:
                break
            norm = norm2.sqrt()
            vectors.append([x / norm for x in raw])

        ritz_scaled = [sum((best_coefficients[j] * vectors[j][i]
                            for j in range(len(best_coefficients))), Decimal(0))
                       for i in range(n)]
        original = [ritz_scaled[i] / scales[i] for i in range(n)]
        maxnorm = max(abs(x) for x in original)
        if maxnorm == 0:
            raise ArithmeticError("zero Ritz vector")
        return trace, [x / maxnorm for x in original]


def build(run_path: Path | None, expected_run_sha: str | None,
          prefix_dimension: int | None, cache: Path,
          expected_cache_sha: str, precision: int, krylov_dimension: int,
          jacobi_sweeps: int, digits: int):
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
    if not (100 <= precision <= 1000 and 1 <= krylov_dimension <= 40 and
            1 <= jacobi_sweeps <= 1000 and 20 <= digits < precision):
        raise ValueError("invalid refinement controls")

    refiner = load_module("krylov_d20_refiner_dependency_v1", REFINER)
    ei, rb = refiner.ei, refiner.rb
    seed_data = strict_json(inputs[SEED], SEED)
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
                       for a, lam in seed_data.get("basis", ()))
    seed_vector = tuple(Q(x) for x in seed_data.get("rational_vector", ()))
    if run is not None and (
            run.get("k") != K or run.get("degree") != 20 or
            run.get("basis_dimension") != len(basis) or
            not 472 <= len(basis) <= 707 or
            run.get("parameters") != PARAMETERS or
            run.get("integrator_sha256") != INTEGRATOR_SHA256 or
            basis != full_basis[:len(basis)]):
        raise ValueError("source run is not a canonical B20 prefix")
    if (seed_data.get("format") != "bv-even-exact-vector-v1" or
            (seed_data.get("k"), seed_data.get("degree")) != (K, 18) or
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
    warm = list(seed_vector) + [Q(0)] * (len(basis) - 471)
    trace, decimal_vector = krylov_refine_decimal(
        m1, m2, warm, precision, krylov_dimension, jacobi_sweeps)
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
        "format": "bv-d20-krylov-refinement-cacheconditional-v1",
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
        "precision": precision,
        "krylov_dimension_requested": krylov_dimension,
        "krylov_dimension_realized": len(trace),
        "jacobi_max_sweeps": jacobi_sweeps,
        "ritz_trace": [[i, value, rotations]
                       for i, value, rotations in trace],
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
        "source_hashes": {
            str(path.relative_to(REPO)) if path.is_relative_to(REPO) else str(path): digest
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
    parser.add_argument("--krylov-dimension", type=int, default=12)
    parser.add_argument("--jacobi-sweeps", type=int, default=200)
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
        args.krylov_dimension, args.jacobi_sweeps, args.digits)
    payload = canonical_json(result)
    publish_exclusive(args.output, payload)
    print(json.dumps({
        "output_sha256": sha256(payload),
        "basis_dimension": result["basis_dimension"],
        "ritz_trace": result["ritz_trace"],
        "exact_quotient": result["exact_quotient"],
        "exact_deficit": result["exact_deficit_over_denominator"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
