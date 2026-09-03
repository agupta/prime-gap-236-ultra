#!/usr/bin/env python3
"""Source-bound, computation-free plan for refining the active BV D18 run.

This script never opens the active SQLite cache.  It derives dimensions,
historical convergence diagnostics, and resource estimates only from frozen
source files and the completed D14/D16 artifacts.
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import math
import os
import sys
from decimal import Decimal, localcontext
from fractions import Fraction as Q
from pathlib import Path


FILE = Path(__file__).resolve()
REPO = FILE.parents[3]
EI = REPO / "agents/exact-integrator"
sys.path.insert(0, str(EI / "src"))

import exact_integrator as exact  # noqa: E402


PINNED = {
    "agents/exact-integrator/src/exact_integrator.py":
        "941ee82bc72fd8488a95eb5e536fe47f8c95d39a1b618dae7d6ef7eb27122e52",
    "agents/exact-integrator/run_basis.py":
        "f660a30d8dd83f13459e0412ded1e28c7ec0864abb41ad04a396475a7905e1d4",
    "agents/small-delta-frontier/certify_bv_cached.py":
        "1e1e9aece98190b06684be1c206583de72969218b4ec5a5dfaf374fb7d26d387",
    "agents/exact-integrator/results/aquarter_fullsimplex_k48_B14_current_repro.json":
        "d8d7b27ad4a412fe5a2e1b3e0750380e336d0affa569f7b538cbeb3c754cb19a",
    "agents/exact-integrator/results/aquarter_fullsimplex_k48_B16_current.json":
        "75112cf5d8cda1e9313ddc4dc9228b05ee9abf826515ac3d46c6bd66b353922c",
    "agents/small-delta-frontier/bv_aquarter_B16_vector_exact.json":
        "59715ddffa483c696c035634a81c3cc8ffe882e9d6eaceec74bea23996b72d62",
}

PARAMETERS = {
    "alpha": "103/400", "delta": "7/250", "eta": "97/400",
    "beta1": "103/400", "beta2": "103/400",
    "beta3plus": "103/400",
}
TARGET_K = 48
TARGET_DEGREE = 18
TARGET_DIMENSION = 471
TARGET_ENTRIES = TARGET_DIMENSION * (TARGET_DIMENSION + 1) // 2
D20_DIMENSION = 707
D20_NEW_LABELS = 236
D20_SELECTED_LABELS = 24


def sha256(path_or_bytes):
    data = (path_or_bytes if isinstance(path_or_bytes, bytes)
            else Path(path_or_bytes).read_bytes())
    return hashlib.sha256(data).hexdigest()


def strict_json(path):
    def pairs(items):
        answer = {}
        for key, value in items:
            if key in answer:
                raise ValueError(f"duplicate JSON key {key}")
            answer[key] = value
        return answer

    return json.loads(Path(path).read_bytes(), object_pairs_hook=pairs,
                      parse_constant=lambda token: (_ for _ in ()).throw(
                          ValueError(f"nonfinite JSON token {token}")))


def validate_sources():
    for relative, digest in PINNED.items():
        if sha256(REPO / relative) != digest:
            raise ValueError(f"pinned D18-plan input changed: {relative}")
    if sha256(Path(exact.__file__).resolve()) != PINNED[
            "agents/exact-integrator/src/exact_integrator.py"]:
        raise ValueError("imported exact integrator is not the pinned source")
    return dict(PINNED)


def validate_completed_artifacts():
    d14 = strict_json(
        REPO / "agents/exact-integrator/results/"
               "aquarter_fullsimplex_k48_B14_current_repro.json")
    d16 = strict_json(
        REPO / "agents/exact-integrator/results/"
               "aquarter_fullsimplex_k48_B16_current.json")
    certificate = strict_json(
        REPO / "agents/small-delta-frontier/"
               "bv_aquarter_B16_vector_exact.json")
    expected = ((d14, 14, 195, 19110),
                (d16, 16, 307, 47278))
    for artifact, degree, dimension, entries in expected:
        if (artifact.get("k") != TARGET_K or
                artifact.get("degree") != degree or
                artifact.get("basis_dimension") != dimension or
                artifact.get("parameters") != PARAMETERS or
                artifact.get("integrator_sha256") !=
                PINNED["agents/exact-integrator/src/exact_integrator.py"] or
                len(artifact.get("basis", ())) != dimension or
                artifact.get("cache_hits", 0) +
                artifact.get("cache_misses", 0) != entries):
            raise ValueError(f"completed D{degree} run schema changed")
    if (certificate.get("k") != TARGET_K or
            certificate.get("degree") != 16 or
            certificate.get("parameters") != PARAMETERS or
            certificate.get("source_run_sha256") != PINNED[
                "agents/exact-integrator/results/"
                "aquarter_fullsimplex_k48_B16_current.json"] or
            certificate.get("run_basis_sha256") != PINNED[
                "agents/exact-integrator/run_basis.py"] or
            certificate.get("integrator_sha256") != PINNED[
                "agents/exact-integrator/src/exact_integrator.py"] or
            len(certificate.get("rational_vector", ())) != 307):
        raise ValueError("completed D16 certificate schema changed")
    return d14, d16, certificate


def d16_convergence_diagnostic(certificate):
    trace = certificate.get("power_trace")
    if (not isinstance(trace, list) or len(trace) != 8 or
            [row[0] for row in trace] != list(range(40, 321, 40))):
        raise ValueError("D16 convergence trace changed")
    with localcontext() as context:
        context.prec = 100
        values = [Decimal(row[1]) for row in trace]
        gains = [values[i] - values[i - 1]
                 for i in range(1, len(values))]
        if any(gain <= 0 for gain in gains):
            raise ArithmeticError("historical D16 trace is not increasing")
        ratios = [gains[i] / gains[i - 1]
                  for i in range(1, len(gains))]
        last_ratio = ratios[-1]
        if not Decimal("0.06") < last_ratio < Decimal("0.08"):
            raise ArithmeticError("historical convergence ratio changed")
        tail = gains[-1] * last_ratio / (1 - last_ratio)

        iterations = {}
        for threshold in (Decimal("1e-15"), Decimal("1e-20"),
                          Decimal("1e-25"), Decimal("1e-30")):
            blocks = 0
            gain = gains[-1]
            while gain > threshold:
                gain *= last_ratio
                blocks += 1
            iterations[str(threshold)] = 40 * blocks
        return {
            "trace": trace,
            "forty_iteration_gains": [str(value) for value in gains],
            "successive_gain_ratios": [str(value) for value in ratios],
            "last_gain": str(gains[-1]),
            "geometric_tail_estimate_after_320": str(tail),
            "additional_iterations_to_gain_threshold": iterations,
            "diagnostic_only_not_an_eigenvalue_bound": True,
        }


def resource_estimates(d14, d16):
    n14, n16, n18 = 195, 307, TARGET_DIMENSION
    entries14 = n14 * (n14 + 1) // 2
    entries16 = n16 * (n16 + 1) // 2
    new16 = entries16 - entries14
    new18 = TARGET_ENTRIES - entries16
    seconds16 = Q(str(d16["exact_matrix_seconds"]))
    linear = seconds16 * new18 / new16
    matrix_conservative = 3 * linear

    # These two peaks/times are frozen ledger observations from the completed
    # D16 run.  They are deliberately inflated by exact n^2/n^3 ratios below.
    d16_refinement_seconds = Q("88.78")
    d16_refinement_peak_kib = 138064
    d16_build_peak_kib = 237660
    dimension_square = Q(n18 * n18, n16 * n16)
    dimension_cube = Q(n18 ** 3, n16 ** 3)
    build_peak = math.ceil(d16_build_peak_kib * dimension_square)
    refinement_peak_180 = math.ceil(
        d16_refinement_peak_kib * dimension_square * Q(180, 140))
    refinement_peak_240 = math.ceil(
        d16_refinement_peak_kib * dimension_square * Q(240, 140))

    # 640 iterations at p=180 plus a seeded 160-iteration p=240 replay.
    # Scaling the entire D16 320-iteration wall by n^3, precision, and the
    # iteration multiplier is conservative because it also doubles LU work.
    primary = (d16_refinement_seconds * dimension_cube *
               Q(180, 140) * 2)
    replay = (d16_refinement_seconds * dimension_cube *
              Q(240, 140))
    return {
        "dimensions": {"D14": n14, "D16": n16, "D18": n18},
        "symmetric_entries": {
            "D14": entries14, "D16": entries16, "D18": TARGET_ENTRIES,
            "new_D14_to_D16": new16, "new_D16_to_D18": new18,
        },
        "matrix_build": {
            "D16_increment_seconds": str(seconds16),
            "D16_increment_entries": new16,
            "D18_increment_entries": new18,
            "linear_D18_seconds": str(linear),
            "threefold_conservative_D18_seconds": str(matrix_conservative),
            "threefold_conservative_D18_hours_decimal":
                format(float(matrix_conservative / 3600), ".6f"),
            "n_squared_peak_projection_kib": build_peak,
            "operational_peak_cap_kib": 786432,
        },
        "decimal_refinement": {
            "primary_precision": 180, "primary_max_iterations": 640,
            "replay_precision": 240, "replay_iterations": 160,
            "primary_scaled_seconds": str(primary),
            "replay_scaled_seconds": str(replay),
            "combined_scaled_seconds": str(primary + replay),
            "combined_scaled_minutes_decimal":
                format(float((primary + replay) / 60), ".6f"),
            "projected_peak_kib_p180": refinement_peak_180,
            "projected_peak_kib_p240": refinement_peak_240,
            "operational_peak_cap_kib": 786432,
        },
        "cache_free_checker": {
            "entry_count": TARGET_ENTRIES,
            "estimated_wall_seconds": str(matrix_conservative),
            "estimated_wall_hours_decimal":
                format(float(matrix_conservative / 3600), ".6f"),
            "operational_peak_cap_kib": 1048576,
            "estimate_status": "calibrated upper planning estimate, not a bound",
        },
    }


def d20_pruned_route(d16):
    """Exact inventory and algebra for a D18-seeded pruned D20 extension."""
    basis18 = exact.even_basis(18)
    basis20 = exact.even_basis(20)
    if (len(basis18) != TARGET_DIMENSION or
            len(basis20) != D20_DIMENSION or
            basis20[:TARGET_DIMENSION] != basis18):
        raise ArithmeticError("graded B18/B20 nesting changed")
    new_labels = basis20[TARGET_DIMENSION:]
    if len(new_labels) != D20_NEW_LABELS:
        raise ArithmeticError("B20 minus B18 inventory changed")
    full_entries = D20_DIMENSION * (D20_DIMENSION + 1) // 2
    full_increment = full_entries - TARGET_ENTRIES
    scan_cross = D20_NEW_LABELS * TARGET_DIMENSION
    scan_self = D20_NEW_LABELS
    scan_total = scan_cross + scan_self
    selected_off_diagonal = (
        D20_SELECTED_LABELS * (D20_SELECTED_LABELS - 1) // 2)
    selected_increment = scan_total + selected_off_diagonal
    selected_dimension = TARGET_DIMENSION + D20_SELECTED_LABELS
    selected_total_entries = selected_dimension * (selected_dimension + 1) // 2
    if (full_increment != 139122 or scan_total != 111392 or
            selected_increment != 111668 or
            selected_total_entries != 122760):
        raise ArithmeticError("pruned D20 moment arithmetic changed")

    serialized_new_labels = [
        {"a": a, "partition": list(partition),
         "total_degree": a + sum(partition)}
        for a, partition in new_labels
    ]
    degree_counts = Counter(label["total_degree"]
                            for label in serialized_new_labels)
    if degree_counts != {19: 97, 20: 139}:
        raise ArithmeticError("B20 minus B18 degree inventory changed")

    per_entry = Q(str(d16["exact_matrix_seconds"])) / 28168
    full_seconds = 3 * per_entry * full_increment
    selected_seconds = 3 * per_entry * selected_increment
    return {
        "basis": {
            "D18_dimension": TARGET_DIMENSION,
            "D20_dimension": D20_DIMENSION,
            "new_B20_minus_B18_labels": D20_NEW_LABELS,
            "canonical_order": (
                "the exact_integrator.even_basis(20) suffix after the first "
                "471 B18 labels; serialized verbatim below"),
            "new_label_degree_counts": {
                str(degree): count
                for degree, count in sorted(degree_counts.items())
            },
            "new_labels": serialized_new_labels,
            "new_labels_sha256": sha256(
                (json.dumps([[a, list(partition)]
                             for a, partition in new_labels],
                            separators=(",", ":")) + "\n").encode("ascii")),
        },
        "exact_one_coordinate_scan": {
            "base_new_cross_pairs": scan_cross,
            "new_diagonal_pairs": scan_self,
            "total_new_moment_pairs": scan_total,
            "forms_for_label_h": [
                "a01=I(F18,h)", "b01=48J(F18,h)",
                "a11=I(h,h)", "b11=48J(h,h)",
                "detA=a00*a11-a01^2 must be positive",
                "residual=b01-(b00/a00)*a01",
            ],
            "top_root_characteristic": (
                "det(A)*lambda^2 - "
                "(b00*a11+b11*a00-2*b01*a01)*lambda + det(B)=0"),
            "ranking_rule": (
                "Isolate the larger algebraic root with outward rational "
                "intervals; also rationalize its stationary scalar on a "
                "common 60-digit grid and rank by the resulting exact "
                "particular-vector gain. Overlapping algebraic intervals are "
                "ties, never favorably ordered."),
            "source_bound_cache_role": (
                "Reuse exact D18 old-old entries and store each new old-new/"
                "diagonal recurrence value under the integrator-hashed v2 "
                "key. Cache values remain discovery inputs, not checker data."),
        },
        "selected_block": {
            "selection_count": D20_SELECTED_LABELS,
            "rule": (
                "Take the first 24 labels in decreasing exact rational trial "
                "gain, breaking exact ties by the canonical graded label; no "
                "data-dependent enlargement."),
            "additional_selected_off_diagonal_pairs": selected_off_diagonal,
            "incremental_pairs_after_D18": selected_increment,
            "selected_total_dimension": selected_dimension,
            "selected_total_symmetric_entries": selected_total_entries,
            "full_D20_incremental_pairs_after_D18": full_increment,
            "full_D20_total_symmetric_entries": full_entries,
            "incremental_pair_fraction_of_full":
                str(Q(selected_increment, full_increment)),
            "total_matrix_fraction_of_full":
                str(Q(selected_total_entries, full_entries)),
            "decimal_solver_n_cubed_fraction_of_full":
                str(Q(selected_dimension ** 3, D20_DIMENSION ** 3)),
            "matrix_memory_n_squared_fraction_of_full":
                str(Q(selected_dimension ** 2, D20_DIMENSION ** 2)),
        },
        "cost_estimate": {
            "calibration": (
                "D16 incremental seconds per new exact pair, multiplied by "
                "three; degree-20 arithmetic may still be slower"),
            "selected_increment_seconds": str(selected_seconds),
            "selected_increment_hours_decimal":
                format(float(selected_seconds / 3600), ".6f"),
            "full_increment_seconds": str(full_seconds),
            "full_increment_hours_decimal":
                format(float(full_seconds / 3600), ".6f"),
            "saved_incremental_pairs": full_increment - selected_increment,
            "saved_pair_fraction":
                str(Q(full_increment - selected_increment, full_increment)),
            "important_limitation": (
                "Exact all-label ranking already costs about 80 percent of "
                "the full D20 incremental pair inventory. The main saving is "
                "the 495-dimensional Ritz solve and cache-free checker, not "
                "the moment scan."),
        },
        "continuation_gate": {
            "requires_cache_free_D18_certificate": True,
            "minimum_sum_of_top24_exact_individual_gains": "1e-4",
            "minimum_selected_block_discovery_quotient": "0.99",
            "maximum_selection_count": D20_SELECTED_LABELS,
            "full_D20_build_authorized": False,
            "pruned_D20_scan_authorized": False,
            "independent_selected_block_checker_required": True,
            "heuristic_not_an_upper_bound": True,
        },
        "checker": (
            "The independent checker reconstructs only the canonical B18 "
            "basis plus the frozen 24-label list, all 122760 lower-triangle "
            "entries, directly from the recurrence with no persistent cache."),
    }


def build_plan():
    sources = validate_sources()
    d14, d16, certificate = validate_completed_artifacts()
    d18_basis = exact.even_basis(TARGET_DEGREE)
    if (len(d18_basis) != TARGET_DIMENSION or
            len(set(d18_basis)) != TARGET_DIMENSION or
            d18_basis[:307] != exact.even_basis(16)):
        raise ArithmeticError("D18 graded even-basis inventory changed")
    convergence = d16_convergence_diagnostic(certificate)
    resources = resource_estimates(d14, d16)
    d20 = d20_pruned_route(d16)
    return {
        "status": "BV-D18-refinement-plan-frozen-no-active-cache-read",
        "rigorous": False,
        "theorem_ready": False,
        "active_D18_cache_read": False,
        "active_D18_cache_modified": False,
        "D18_refinement_run": False,
        "D18_cache_free_checker_run": False,
        "script_sha256": sha256(FILE),
        "source_hashes": sources,
        "target": {
            "k": TARGET_K, "degree": TARGET_DEGREE,
            "basis_dimension": TARGET_DIMENSION,
            "symmetric_entry_count": TARGET_ENTRIES,
            "parameters": PARAMETERS,
            "basis_prefix_D16_dimension": 307,
        },
        "run_basis_role": (
            "The eventual 471-coordinate decimal_vector is a seed only. Its "
            "80-iteration Decimal100 vector and per-coordinate denominator-"
            "1e6 rationalization are forbidden as a final certificate."),
        "historical_D16_convergence": convergence,
        "resource_estimates": resources,
        "adaptive_refinement": {
            "primary": {
                "precision": 180, "trace_every": 40,
                "initial_iterations": 320, "maximum_iterations": 640,
                "seed": "eventual source-bound D18 run decimal_vector",
            },
            "cheap_trace_diagnostics": [
                "Rayleigh increment over 40 iterations",
                "ratio of the last three 40-iteration increments",
                "geometric-tail heuristic Delta*r/(1-r)",
                "scaled generalized residual infinity norm",
                "projective infinity-norm change to A^-1 B v",
                "two-vector Ritz gain on span{v,A^-1 B v}",
            ],
            "rationalization_readiness": {
                "at_least_four_traces": True,
                "all_recent_Rayleigh_increments_positive": True,
                "maximum_recent_increment_ratio": "9/10",
                "maximum_geometric_tail_heuristic": "1e-16",
                "maximum_scaled_generalized_residual": "1e-28",
                "maximum_two_vector_Ritz_gain": "1e-18",
                "note": "diagnostic thresholds are discovery gates, not upper bounds",
            },
            "slow_convergence_escape": (
                "If the recent increment ratio is >=0.9 or the projected "
                "iterations to the tail gate exceed 640, stop scalar power "
                "iteration and use a 4-vector A-inner-product Krylov/Ritz "
                "restart; do not merely extend to thousands of iterations."),
            "cross_precision_replay": {
                "precision": 240, "iterations": 160,
                "seed": "normalized final Decimal180 vector",
                "maximum_Rayleigh_disagreement": "1e-25",
                "maximum_projective_vector_disagreement": "1e-20",
            },
            "exact_rationalization": {
                "normalization": "divide by largest-magnitude coordinate",
                "significant_digit_trials": [45, 60, 75],
                "method": "one common decimal significant-digit grid, not limit_denominator",
                "selection": "largest exact cache-recontracted quotient",
                "required_exact_quotient_spread": "<=1e-25",
            },
        },
        "certificate_contract": {
            "particular_vector_only": True,
            "optimality_claim": False,
            "required_bindings": [
                "exact run-result bytes/SHA", "integrator bytes/SHA",
                "run_basis bytes/SHA", "refiner bytes/SHA",
                "exact 471-label graded basis", "exact support parameters",
                "matrix canonical SHA", "rational vector and exact I,48J",
            ],
            "required_exact_checks": [
                "len(vector)=471 and every rational is canonical",
                "I(c)>0", "48J(c) and I(c) reconstructed exactly",
                "exact quotient and signed margin printed without float conversion",
            ],
        },
        "independent_cache_free_checker": {
            "must_import_certifier_or_run_basis": False,
            "persistent_cache_allowed": False,
            "basis_enumeration": "independent graded even-partition generator",
            "matrix_reconstruction": (
                "call pinned OneStratumSupport.basis_m1 and 48*basis_j for "
                "all 111156 lower-triangular entries; stream diagonal plus "
                "twice-off-diagonal exact vector contractions"),
            "matrix_hash": (
                "canonical label-pair/value lower-triangle hash reconstructed "
                "from recurrence, never copied from run/cache"),
            "mandatory_gates": [
                "exactly 111156 unique entries", "no missing/duplicate label pair",
                "independent basis equals certificate basis in order",
                "reconstructed exact I and 48J equal certificate strings",
                "I>0 and exact margin sign is reported",
                "reverse-order second run gives the same exact forms/hash",
                "normal/-O low-k signed tests pass",
                "partial-limit or cache argument cannot print PASS",
            ],
            "claim_after_pass": (
                "exact particular-vector quotient only; no largest-eigenvalue "
                "or finite-space optimality claim"),
        },
        "pruned_D20_extension": d20,
    }


def canonical_json(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"),
                       allow_nan=False) + "\n").encode("ascii")


def publish_new(path, payload):
    path = Path(path).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    encoded = canonical_json(payload)
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(encoded)
        handle.flush()
        os.fsync(handle.fileno())
    if sha256(path) != sha256(encoded):
        raise RuntimeError("D18 plan output changed after publication")
    return sha256(encoded)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output")
    args = parser.parse_args()
    plan = build_plan()
    if args.output:
        print(publish_new(args.output, plan))
    else:
        print(canonical_json(plan).decode("ascii"), end="")


if __name__ == "__main__":
    main()
