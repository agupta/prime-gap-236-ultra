#!/usr/bin/env python3
"""Evaluate a capped degree-band matrix action at an explicit input vector.

This is the Davidson continuation companion to the frozen theta0 gradient
producer.  It imports the audited sparse/SoA traversal without modifying it,
derives the 20 compressed coordinates independently from an explicit ordered
272-label polynomial, and returns ``A theta`` and ``B theta``.  Decimal output
is discovery-only; an improved polynomial must still undergo scalar exact
reconstruction.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import resource
from decimal import Decimal, getcontext
from fractions import Fraction
from pathlib import Path

import band_operator_sparse as sparse
from band_operator import BandMap, _parse_decimal
from grouped_fixed_vector import install_decimal, precompute_orbits


PINNED = {
    "source": "719c656e6e45388273b4c27f51f7a18b33e9ed1abb5f883e6fcc5de5d6d64a87",
    "bands": "29d38a9e7ca7a352560c0a01813f2dfd2f477ec8cb829c433cce18d8229d31e9",
    "sparse": "e1545435f0c7ad22a17115ac46c291436c1ead5101fd3de6d2a80ab65bc9c257",
    "band": "e4fbf7a97d061d362c32b54bf0d49a89c4195b965e96d7ab89a2581bc907c073",
    "grouped": "47167e92a0f346e969706dc282ccb2dfd4ac31a0a75b654938ffbe8423cf4a4a",
    "integrator": "941ee82bc72fd8488a95eb5e536fe47f8c95d39a1b618dae7d6ef7eb27122e52",
}
PARAMETERS = {
    "alpha": Fraction(79247, 300000), "delta": Fraction(1, 100),
    "eta": Fraction(76247, 300000), "beta1": Fraction(3, 20),
    "beta2": Fraction(3, 20), "beta3plus": Fraction(97, 625),
}


def file_sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def compressed_coordinates(input_data, band_map):
    """Recover and verify the unique compressed vector exactly."""
    expected_basis = [[a, list(lam)] for a, lam in band_map.labels]
    if input_data.get("k") != 48 or input_data.get("basis") != expected_basis:
        raise ValueError("input k or ordered basis mismatch")
    serialized = input_data.get("rational_vector", [])
    if len(serialized) != len(band_map.labels):
        raise ValueError("input vector dimension mismatch")
    coefficients = [Fraction(x) for x in serialized]
    theta = [None] * band_map.dimension
    for coefficient, owner, weight in zip(
            coefficients, band_map.owner, band_map.weight_q):
        if not weight:
            if coefficient:
                raise ValueError("nonzero coefficient on zero-weight label")
            continue
        value = coefficient / weight
        if theta[owner] is None:
            theta[owner] = value
        elif theta[owner] != value:
            raise ValueError("input does not lie in the degree-band space")
    if any(value is None for value in theta):
        raise ValueError("compressed direction has no nonzero-weight label")
    if band_map.expand(theta) != coefficients:
        raise ValueError("compressed expansion mismatch")
    return tuple(theta)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True)
    ap.add_argument("--bands", required=True)
    ap.add_argument("--input", required=True)
    ap.add_argument("--decimal-dps", type=int, default=100)
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--alpha", default="79247/300000")
    ap.add_argument("--delta", default="1/100")
    ap.add_argument("--eta", default="76247/300000")
    ap.add_argument("--beta1", default="3/20")
    ap.add_argument("--beta2", default="3/20")
    ap.add_argument("--beta3plus", default="97/625")
    ap.add_argument("--progress", action="store_true")
    ap.add_argument("--output", required=True)
    args = ap.parse_args()
    if args.decimal_dps < 90 or args.workers not in (1, 2):
        raise SystemExit("require decimal-dps>=90 and one or two workers")

    here = Path(__file__).resolve().parent
    exact_agent = here.parents[1] / "exact-integrator"
    paths = {
        "driver": Path(__file__),
        "sparse": here / "band_operator_sparse.py",
        "band": here / "band_operator.py",
        "grouped": exact_agent / "grouped_fixed_vector.py",
        "integrator": exact_agent / "src/exact_integrator.py",
    }
    hashes_start = {key: file_sha(path) for key, path in paths.items()}
    band_map = BandMap.from_source_and_bands(args.source, args.bands)
    source = json.loads(Path(args.source).read_bytes())
    input_bytes = Path(args.input).read_bytes()
    input_data = json.loads(input_bytes)
    try:
        theta_q = compressed_coordinates(input_data, band_map)
    except (KeyError, TypeError, ValueError, ZeroDivisionError) as exc:
        raise SystemExit(f"input validation failed: {exc}") from exc

    getcontext().prec = args.decimal_dps
    orbit_table = precompute_orbits(list(band_map.labels), 48)
    install_decimal(orbit_table, args.decimal_dps)
    actual_params = {
        "alpha": args.alpha, "delta": args.delta, "eta": args.eta,
        "beta1": args.beta1, "beta2": args.beta2,
        "beta3plus": args.beta3plus,
    }
    support = sparse.ei.OneStratumSupport(
        48, *[_parse_decimal(actual_params[key]) for key in PARAMETERS])
    theta = tuple(_parse_decimal(x) for x in theta_q)
    result = sparse.SparseBandOperator(
        support, band_map, theta, Decimal).apply(args.progress, args.workers)
    hashes_end = {key: file_sha(path) for key, path in paths.items()}

    tolerance = Decimal("1e-50")
    euler_d_relative = abs(result["euler_denominator_error"]) / abs(
        result["denominator"])
    euler_n_relative = abs(result["euler_numerator_error"]) / max(
        abs(result["numerator"]), Decimal(1).scaleb(-999))
    vectors = (theta, result["a_theta"], result["b_theta"],
               result["grad_denominator"], result["grad_numerator"])
    gates = {
        "source_k48_dim272_banddim20": (source.get("k") == 48 and
            len(band_map.labels) == 272 and band_map.dimension == 20),
        "source_sha_pinned": band_map.source_sha256 == PINNED["source"],
        "bands_sha_pinned": band_map.bands_sha256 == PINNED["bands"],
        "dependencies_pinned": all(hashes_start[key] == PINNED[key]
                                   for key in ("sparse", "band", "grouped",
                                               "integrator")),
        "dependencies_unchanged_during_run": hashes_start == hashes_end,
        "parameters_exact_c10": all(Fraction(actual_params[key]) == value
                                    for key, value in PARAMETERS.items()),
        "explicit_input_reexpanded": band_map.expand(theta_q) ==
            [Fraction(x) for x in input_data["rational_vector"]],
        "all_vectors_length20": all(len(vector) == 20 for vector in vectors),
        "all_numbers_finite": all(x.is_finite() for vector in vectors
                                  for x in vector) and all(
            result[key].is_finite() for key in
            ("denominator", "numerator", "quotient",
             "euler_denominator_error", "euler_numerator_error")),
        "gradient_halves_match": (all(2 * x == y for x, y in zip(
            result["a_theta"], result["grad_denominator"])) and all(
            2 * x == y for x, y in zip(
                result["b_theta"], result["grad_numerator"]))),
        "denominator_positive": result["denominator"] > 0,
        "quotient_recomputed": result["quotient"] ==
            result["numerator"] / result["denominator"],
        "euler_relative_below_1e50": (euler_d_relative <= tolerance and
                                      euler_n_relative <= tolerance),
        "complete_traversal_counts": (result["i_orbit_groups"] == 1575 and
            result["i_faces"] == 312 and result["marginal_components"] == 695 and
            result["j_branch_integrals"] == 1200),
        "stratum_buckets_sum": (sum(result["i_value_by_r"], Decimal(0)) ==
            result["denominator"] and 48 * sum(
                result["j_value_by_r"], Decimal(0)) == result["numerator"]),
    }
    passed = all(gates.values())
    output = {
        "status": ("multiprecision-degree-band-action-discovery" if passed else
                   "rejected-degree-band-action-discovery"),
        "implementation": "sparse-structure-of-arrays-arbitrary-action",
        "rigorous": False,
        "complete": True,
        "decimal_dps": args.decimal_dps,
        "workers": args.workers,
        "source_json": args.source,
        "source_sha256": band_map.source_sha256,
        "bands_json": args.bands,
        "bands_sha256": band_map.bands_sha256,
        "input_json": args.input,
        "input_sha256": hashlib.sha256(input_bytes).hexdigest(),
        "input_status": input_data.get("status"),
        "driver_sha256": hashes_start["driver"],
        "operator_sha256": hashes_start["sparse"],
        "band_operator_dependency_sha256": hashes_start["band"],
        "grouped_evaluator_sha256": hashes_start["grouped"],
        "integrator_sha256": hashes_start["integrator"],
        "parameters": actual_params,
        "theta": [str(x) for x in theta],
        **{key: ([str(x) for x in value] if isinstance(value, tuple) else
                 str(value) if isinstance(value, Decimal) else value)
           for key, value in result.items()},
        "peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "child_peak_rss_kib": resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,
        "gates_passed": passed,
        "gates": gates,
        "euler_denominator_relative": str(euler_d_relative),
        "euler_numerator_relative": str(euler_n_relative),
    }
    Path(args.output).write_text(json.dumps(output, indent=2) + "\n")
    print(json.dumps(output, indent=2))
    if not passed:
        raise SystemExit("action discovery failed one or more fail-closed gates")


if __name__ == "__main__":
    main()
