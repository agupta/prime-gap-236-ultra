#!/usr/bin/env python3
"""Hostile cache-free audit of the frozen 568-term D19 BV vector.

This checker does not import the contraction helper under review and does not
read a matrix or SQLite file.  It collects the explicit vector's square and
distinguished-coordinate marginal square from the pinned orbit-product
recurrence, then evaluates independent full-simplex Dirichlet formulas.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from fractions import Fraction as Q
import hashlib
import importlib.util
import json
from math import comb, factorial
import os
from pathlib import Path
import stat
import sys


if hasattr(sys, "set_int_max_str_digits"):
    sys.set_int_max_str_digits(0)

FILE = Path(__file__).resolve()
REPO = FILE.parents[2]
CANDIDATE = REPO / (
    "agents/structural-basis/results/"
    "bv_D19_krylov20_cacheconditional_v1.json")
DIRECT_CHECKER = REPO / "verify/check_bv_rational_vector_direct_v1.py"
DIRECT_TEST = REPO / "verify/test_check_bv_rational_vector_direct_v1.py"
DIRECT_RESULT = REPO / "verify/results/bv_D19_krylov20_direct_exact_v1.json"
SCAN = REPO / "agents/small-delta-frontier/scan_bv_epsilon_fixed.py"
INTEGRATOR = REPO / "agents/exact-integrator/src/exact_integrator.py"
PRODUCER = REPO / "agents/structural-basis/code/krylov_bv_d20_from_d18_v1.py"

PINS = {
    CANDIDATE:
        "986563579cb7fa8653f774100e9fd1cc966761261eef53052b8be8e61f96d276",
    DIRECT_CHECKER:
        "63bd2a3adc84191d212d52d3175179f583a1257d7c862f1ee07ecaa2ade3b7d3",
    DIRECT_TEST:
        "a8d5dd13cf73dc3c59f89dbfdee21819cbc4c230ed063d7bdec42d57bcf81247",
    DIRECT_RESULT:
        "a71b9bacf9fbe9ce21d6d0f3c23eec69baa917c46157c402d2d60e6565517d0b",
    SCAN:
        "96495079a18039a0a7b0522e83ac455cbe5ff144598fff6b382f2c2953958de9",
    INTEGRATOR:
        "941ee82bc72fd8488a95eb5e536fe47f8c95d39a1b618dae7d6ef7eb27122e52",
    PRODUCER:
        "6dc0857cc40b5b47bfe65bfd7ccf50d98891df0251cf52f6adee56549cbf5993",
}

K = 48
ALPHA = Q(103, 400)
ETA = Q(97, 400)
DELTA_SOURCE = Q(7, 250)
DELTA_TARGET = Q(1, 60)
PARAMETERS = {
    "alpha": "103/400", "delta": "7/250", "eta": "97/400",
    "beta1": "103/400", "beta2": "103/400",
    "beta3plus": "103/400",
}
MALFORMED_SHA = (
    "ba3ab1030446c77646f6fe14e1a675d1ab6e946bd03662e19eb8fc29ee9e2073")
MALFORMED_ACCEPTED_OUTPUT_SHA = (
    "f0e36a2eb24a10bf6cd34156ef32c1273fba79248cf29a355e468f220829d49e")


def sha256(value: bytes | Path) -> str:
    data = value if isinstance(value, bytes) else value.read_bytes()
    return hashlib.sha256(data).hexdigest()


def snapshot(path: Path, expected: str) -> tuple[bytes, dict[str, object]]:
    info = path.stat()
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        raise RuntimeError(f"not a single-link regular file: {path}")
    data = path.read_bytes()
    if sha256(data) != expected:
        raise RuntimeError(f"frozen input changed: {path}")
    return data, {
        "sha256": expected, "size": len(data), "dev": info.st_dev,
        "inode": info.st_ino, "nlink": info.st_nlink,
    }


def strict_json(data: bytes, source: Path):
    if not data.endswith(b"\n") or b"\r" in data:
        raise ValueError(f"noncanonical line ending: {source}")
    try:
        data.decode("ascii")
    except UnicodeDecodeError as error:
        raise ValueError(f"non-ASCII JSON: {source}") from error

    def pairs(items):
        answer = {}
        for key, value in items:
            if key in answer:
                raise ValueError(f"duplicate key {key!r}: {source}")
            answer[key] = value
        return answer

    value = json.loads(
        data, object_pairs_hook=pairs,
        parse_float=lambda token: (_ for _ in ()).throw(
            ValueError(f"floating JSON number {token}: {source}")),
        parse_constant=lambda token: (_ for _ in ()).throw(
            ValueError(f"nonfinite JSON number {token}: {source}")))
    if canonical_json(value) != data:
        raise ValueError(f"noncanonical JSON serialization: {source}")
    return value


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def integer_partitions(n: int, maximum: int | None = None):
    if n == 0:
        yield ()
        return
    maximum = n if maximum is None else min(maximum, n)
    for first in range(maximum, 0, -1):
        for rest in integer_partitions(n - first, first):
            yield (first,) + rest


def canonical_even_basis(degree: int):
    answer = []
    for half_degree in range(degree // 2 + 1):
        for half_partition in integer_partitions(half_degree):
            lam = tuple(2 * item for item in half_partition)
            for a in range(degree - 2 * half_degree + 1):
                answer.append((a, lam))
    answer.sort(key=lambda item: (
        item[0] + sum(item[1]), sum(item[1]), len(item[1]),
        item[1], item[0]))
    return tuple(answer)


def exact_int(value, label: str) -> int:
    if type(value) is not int:
        raise ValueError(f"{label} is not an integer")
    return value


def canonical_fraction(value, label: str) -> Q:
    if type(value) is not str:
        raise ValueError(f"{label} is not a rational string")
    try:
        answer = Q(value)
    except (ValueError, ZeroDivisionError) as error:
        raise ValueError(f"malformed fraction at {label}") from error
    if str(answer) != value:
        raise ValueError(f"noncanonical fraction at {label}")
    return answer


def parse_basis(raw):
    if type(raw) is not list:
        raise ValueError("basis is not a list")
    answer = []
    for index, entry in enumerate(raw):
        if type(entry) is not list or len(entry) != 2:
            raise ValueError(f"malformed basis entry {index}")
        a = exact_int(entry[0], f"basis[{index}].a")
        if type(entry[1]) is not list:
            raise ValueError(f"basis[{index}].lambda is not a list")
        lam = tuple(exact_int(x, f"basis[{index}].lambda") for x in entry[1])
        if (a < 0 or any(x <= 0 or x % 2 for x in lam) or
                tuple(sorted(lam, reverse=True)) != lam):
            raise ValueError(f"invalid even basis entry {index}")
        answer.append((a, lam))
    return tuple(answer)


def orbit_size(k: int, lam: tuple[int, ...]) -> int:
    if len(lam) > k:
        return 0
    answer = factorial(k) // factorial(k - len(lam))
    for multiplicity in Counter(lam).values():
        answer //= factorial(multiplicity)
    return answer


def square_orbit_polynomial(ei, terms):
    """Collect a symmetric orbit polynomial square from exact coefficients."""
    items = [(key, coefficient) for key, coefficient in terms.items()
             if coefficient]
    answer = defaultdict(Q)
    pair_count = 0
    for i, ((a, lam), left) in enumerate(items):
        for j in range(i + 1):
            (b, mu), right = items[j]
            pair_count += 1
            factor = left * right * (1 if i == j else 2)
            for nu, multiplicity in ei.multiply_monomial_orbits(lam, mu):
                answer[(a + b, nu)] += factor * multiplicity
    return ({key: value for key, value in answer.items() if value}, pair_count)


def full_simplex_orbit_moment(k: int, nu: tuple[int, ...], power: int,
                              alpha: Q) -> Q:
    product = 1
    for exponent in nu:
        product *= factorial(exponent)
    total = sum(nu)
    canonical = Q(0)
    for c in range(power + 1):
        degree = total + k + c
        canonical += (comb(power, c) * ((1 - alpha) ** (power - c)) *
                      Q(product * factorial(c), factorial(degree)) *
                      (alpha ** degree))
    return orbit_size(k, nu) * canonical


def split_distinguished(lam: tuple[int, ...], k: int):
    answer = []
    if len(lam) < k:
        answer.append((0, lam))
    for exponent in sorted(set(lam)):
        rest = list(lam)
        rest.remove(exponent)
        answer.append((exponent, tuple(rest)))
    return tuple(answer)


def marginal_polynomial(basis, vector, k: int, alpha: Q):
    answer = defaultdict(Q)
    for coefficient, (a, lam) in zip(vector, basis):
        if not coefficient:
            continue
        for exponent, rest in split_distinguished(lam, k):
            for c in range(a + 1):
                power = exponent + c + 1
                factor = Q(comb(a, c) * factorial(exponent) * factorial(c),
                           factorial(exponent + c + 1))
                answer[(power, rest)] += (
                    coefficient * factor * ((1 - alpha) ** (a - c)))
    return {key: value for key, value in answer.items() if value}


def truncated_residual_orbit(k: int, nu: tuple[int, ...], power: int,
                             alpha: Q, eta: Q) -> Q:
    product = 1
    for exponent in nu:
        product *= factorial(exponent)
    total = sum(nu)
    canonical = Q(0)
    for d in range(power + 1):
        degree = total + k + d
        canonical += (comb(power, d) * ((alpha - eta) ** (power - d)) *
                      Q(product * factorial(d), factorial(degree)) *
                      (eta ** degree))
    return orbit_size(k, nu) * canonical


def direct_contract(ei, basis, vector, k: int, alpha: Q, eta: Q):
    terms = {term: coefficient for term, coefficient in zip(basis, vector)
             if coefficient}
    square, square_pairs = square_orbit_polynomial(ei, terms)
    denominator = sum(
        coefficient * full_simplex_orbit_moment(k, nu, power, alpha)
        for (power, nu), coefficient in square.items())
    marginal = marginal_polynomial(basis, vector, k, alpha)
    marginal_square, marginal_pairs = square_orbit_polynomial(ei, marginal)
    j = sum(
        coefficient * truncated_residual_orbit(
            k - 1, nu, power, alpha, eta)
        for (power, nu), coefficient in marginal_square.items())
    return {
        "denominator": denominator,
        "numerator": k * j,
        "term_counts": {
            "square": len(square), "marginal": len(marginal),
            "marginal_square": len(marginal_square),
            "square_input_pairs": square_pairs,
            "marginal_square_input_pairs": marginal_pairs,
        },
        "ambient_degrees": {
            "basis": max(a + sum(lam) for a, lam in basis),
            "square": max(power + sum(nu) for power, nu in square),
            "marginal": max(power + sum(nu) for power, nu in marginal),
            "marginal_square": max(
                power + sum(nu) for power, nu in marginal_square),
        },
    }


def full_simplex_guard(ei, delta: Q) -> dict[str, object]:
    support = ei.OneStratumSupport(
        K, ALPHA, delta, ETA, ALPHA, ALPHA, ALPHA)
    possible_large_counts = min(K, int(ALPHA // delta))
    if not support.is_full_simplex():
        raise ArithmeticError("caps unexpectedly restrict the simplex")
    return {
        "delta": str(delta),
        "possible_large_counts": possible_large_counts,
        "all_large_sum_caps_equal_alpha": True,
        "is_full_simplex": True,
    }


def low_degree_identity(ei):
    basis = canonical_even_basis(4)
    vector = tuple(Q((index % 5) - 2, index + 3)
                   for index in range(len(basis)))
    direct = direct_contract(ei, basis, vector, 4, Q(13, 50), Q(6, 25))
    support = ei.OneStratumSupport(
        4, Q(13, 50), Q(1, 20), Q(6, 25),
        Q(13, 50), Q(13, 50), Q(13, 50))
    m1, m2 = support.matrices(basis)
    expected = (ei.exact_quadratic(m1, vector),
                ei.exact_quadratic(m2, vector))
    if (direct["denominator"], direct["numerator"]) != expected:
        raise ArithmeticError("independent contraction fails low-degree matrix identity")
    return {
        "k": 4, "basis_degree": 4, "dimension": len(basis),
        "denominator": str(expected[0]), "numerator": str(expected[1]),
    }


def expected_direct_result(candidate, basis, vector, forms):
    denominator = forms["denominator"]
    numerator = forms["numerator"]
    term_counts = forms["term_counts"]
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
        "basis_degree": 19,
        "basis_dimension": len(basis),
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
            "square": term_counts["square"],
            "marginal": term_counts["marginal"],
            "marginal_square": term_counts["marginal_square"],
        },
        "candidate_sha256": PINS[CANDIDATE],
        "candidate_producer_sha256": candidate["checker_sha256"],
        "checker_sha256": PINS[DIRECT_CHECKER],
        "source_hashes": {
            "agents/exact-integrator/src/exact_integrator.py": PINS[INTEGRATOR],
            "agents/small-delta-frontier/scan_bv_epsilon_fixed.py": PINS[SCAN],
        },
    }


def build():
    start_self = FILE.read_bytes()
    frozen = {}
    snapshots = {}
    for path, expected in PINS.items():
        data, record = snapshot(path, expected)
        frozen[path] = data
        snapshots[str(path.relative_to(REPO))] = record

    candidate = strict_json(frozen[CANDIDATE], CANDIDATE)
    direct_result = strict_json(frozen[DIRECT_RESULT], DIRECT_RESULT)
    if (candidate.get("format") !=
            "bv-d20-krylov-refinement-cacheconditional-v1" or
            candidate.get("status") !=
            "EXACT PARTICULAR VECTOR CONDITIONAL ON CACHE" or
            candidate.get("rigorous_given_cache_entries") is not True or
            candidate.get("cache_entries_independently_reconstructed") is not False or
            candidate.get("theorem_ready") is not False or
            exact_int(candidate.get("k"), "k") != K or
            exact_int(candidate.get("degree"), "degree") != 20 or
            exact_int(candidate.get("basis_dimension"), "basis_dimension") != 568 or
            candidate.get("parameters") != PARAMETERS or
            candidate.get("checker_sha256") != PINS[PRODUCER]):
        raise ValueError("candidate identity or provenance mismatch")

    basis = parse_basis(candidate.get("basis"))
    d19 = canonical_even_basis(19)
    d20 = canonical_even_basis(20)
    if (len(d19), len(d20)) != (568, 707) or basis != d19 or d20[:568] != d19:
        raise ValueError("candidate is not the complete canonical D19 basis")
    if any(a + sum(lam) > 19 for a, lam in basis):
        raise ValueError("basis exceeds degree 19")
    if len(d20[568:]) != 139 or any(
            a + sum(lam) != 20 for a, lam in d20[568:]):
        raise ArithmeticError("D20-prefix/D19 relation failed")

    raw_vector = candidate.get("rational_vector")
    if type(raw_vector) is not list or len(raw_vector) != 568:
        raise ValueError("vector inventory mismatch")
    vector = tuple(canonical_fraction(value, f"vector[{index}]")
                   for index, value in enumerate(raw_vector))
    if not any(vector) or any(value == 0 for value in vector):
        raise ValueError("expected the frozen all-nonzero vector")

    ei = load_module("bv_D19_hostile_audit_exact_integrator", INTEGRATOR)
    if tuple(ei.even_basis(19)) != d19 or tuple(ei.even_basis(20)) != d20:
        raise ArithmeticError("independent basis generator disagrees with integrator")
    low_degree = low_degree_identity(ei)
    guards = [full_simplex_guard(ei, DELTA_SOURCE),
              full_simplex_guard(ei, DELTA_TARGET)]
    forms = direct_contract(ei, basis, vector, K, ALPHA, ETA)
    denominator = forms["denominator"]
    numerator = forms["numerator"]
    if denominator <= 0 or denominator - numerator <= 0:
        raise ArithmeticError("unexpected sign in independently rebuilt forms")
    scalar_fields = {
        "exact_denominator": denominator,
        "exact_numerator": numerator,
        "exact_quotient": numerator / denominator,
        "exact_deficit_over_denominator":
            (denominator - numerator) / denominator,
    }
    for key, expected in scalar_fields.items():
        if canonical_fraction(candidate.get(key), key) != expected:
            raise ArithmeticError(f"candidate {key} disagrees with direct recurrence")

    expected_result = expected_direct_result(candidate, basis, vector, forms)
    if direct_result != expected_result or canonical_json(expected_result) != frozen[DIRECT_RESULT]:
        raise ArithmeticError("frozen direct result is not the exact expected record")

    # Concrete hostile record: v1 parses a fractional polynomial exponent and
    # silently maps it back to zero with int().  Reconstruct its expected PASS
    # bytes without trusting or rerunning its contraction.
    needle = b'"basis":[[0,[]]'
    replacement = b'"basis":[[0.5,[]]'
    if frozen[CANDIDATE].count(needle) != 1:
        raise RuntimeError("counterexample mutation anchor changed")
    malformed_bytes = frozen[CANDIDATE].replace(needle, replacement, 1)
    if sha256(malformed_bytes) != MALFORMED_SHA:
        raise RuntimeError("counterexample hash changed")
    v1 = load_module("bv_D19_hostile_audit_v1_under_test", DIRECT_CHECKER)
    parsed_by_v1 = v1.strict_json(malformed_bytes, Path("malformed.json"))
    coerced = tuple((int(a), tuple(int(x) for x in lam))
                    for a, lam in parsed_by_v1["basis"])
    if type(parsed_by_v1["basis"][0][0]) is not float or coerced != basis:
        raise RuntimeError("v1 malformed-basis acceptance path changed")
    malformed_expected = dict(expected_result)
    malformed_expected["candidate_sha256"] = MALFORMED_SHA
    malformed_output = canonical_json(malformed_expected)
    if sha256(malformed_output) != MALFORMED_ACCEPTED_OUTPUT_SHA:
        raise RuntimeError("malformed accepted output hash changed")

    if (FILE.read_bytes() != start_self or any(
            path.read_bytes() != data for path, data in frozen.items())):
        raise RuntimeError("source closure changed during audit")

    return {
        "status": "D19 EXACT ARITHMETIC PASS; V1 FAIL-CLOSED AUDIT FAIL",
        "scope": (
            "cache-free exact forms for the frozen particular vector; no "
            "largest-eigenvalue, capped-support, analytic, or theorem claim"),
        "theorem_ready": False,
        "checker_sha256": sha256(start_self),
        "arithmetic_verdict": "AUDIT PASS",
        "v1_fail_closed_verdict": "AUDIT FAIL",
        "candidate_sha256": PINS[CANDIDATE],
        "direct_result_sha256": PINS[DIRECT_RESULT],
        "basis_inventory": {
            "actual_degree": 19,
            "dimension": len(basis),
            "all_coefficients_nonzero": True,
            "D20_prefix_equals_complete_D19": True,
            "D20_degree20_tail_dimension": len(d20) - len(d19),
            "ambient_degrees": forms["ambient_degrees"],
        },
        "full_simplex_guards": guards,
        "low_degree_matrix_identity": low_degree,
        "exact_forms": {
            "denominator": str(denominator),
            "numerator": str(numerator),
            "quotient": str(numerator / denominator),
            "deficit": str(denominator - numerator),
            "normalized_deficit": str(
                (denominator - numerator) / denominator),
            "term_counts": forms["term_counts"],
        },
        "root_direct_result_exact_byte_match": True,
        "cache_audit": {
            "cache_read": False,
            "serialized_matrix_entries_read": False,
            "only_arithmetic_module_imported":
                "agents/exact-integrator/src/exact_integrator.py",
            "scan_helper_imported_for_reconstruction": False,
        },
        "smallest_concrete_checker_defect": {
            "input_mutation": "basis[0][0]: JSON integer 0 -> JSON float 0.5",
            "mathematical_problem":
                "a polynomial exponent is nonintegral in the serialized record",
            "v1_behavior":
                "strict_json accepts the float; int(0.5) silently coerces it to 0",
            "mutated_candidate_sha256": MALFORMED_SHA,
            "observed_full_v1_run_exit_code": 0,
            "observed_full_v1_run_status":
                "INDEPENDENT EXACT PARTICULAR INNER VECTOR PASS",
            "observed_full_v1_output_sha256": MALFORMED_ACCEPTED_OUTPUT_SHA,
            "required_repair":
                "reject all JSON floats and require exact integer basis entries before conversion",
        },
        "snapshots": snapshots,
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
        "exact_quotient": result["exact_forms"]["quotient"],
        "exact_normalized_deficit":
            result["exact_forms"]["normalized_deficit"],
        "term_counts": result["exact_forms"]["term_counts"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
