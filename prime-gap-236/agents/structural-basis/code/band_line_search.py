#!/usr/bin/env python3
"""Prepare and finish the first capped degree-band correction line.

The gradient artifact determines a full-simplex-I-preconditioned direction.
``prepare`` emits that direction as an ordinary 272-term rational-vector input
for the audited scalar grouped evaluator.  After evaluating it, ``finish``
solves the exact two-dimensional Rayleigh stationary equation in Decimal
arithmetic and emits an ordinary rational-vector candidate.  All outputs are
discovery artifacts; the candidate still needs scalar Fraction reconstruction.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from decimal import Decimal, getcontext, localcontext
from fractions import Fraction
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
EXACT_AGENT = os.path.abspath(os.path.join(HERE, "..", "..", "exact-integrator"))
sys.path[:0] = [HERE, EXACT_AGENT, os.path.join(EXACT_AGENT, "src")]

from band_operator import (BandMap, decimal_solve, dot,  # noqa: E402
                           full_simplex_i_preconditioner, matvec)


PINNED = {
    "source": "719c656e6e45388273b4c27f51f7a18b33e9ed1abb5f883e6fcc5de5d6d64a87",
    "bands": "29d38a9e7ca7a352560c0a01813f2dfd2f477ec8cb829c433cce18d8229d31e9",
    "sparse_operator": "e1545435f0c7ad22a17115ac46c291436c1ead5101fd3de6d2a80ab65bc9c257",
    "band_operator": "e4fbf7a97d061d362c32b54bf0d49a89c4195b965e96d7ab89a2581bc907c073",
    "grouped": "47167e92a0f346e969706dc282ccb2dfd4ac31a0a75b654938ffbe8423cf4a4a",
    "integrator": "941ee82bc72fd8488a95eb5e536fe47f8c95d39a1b618dae7d6ef7eb27122e52",
}
PARAMETERS = {
    "alpha": Fraction(79247, 300000), "delta": Fraction(1, 100),
    "eta": Fraction(76247, 300000), "beta1": Fraction(3, 20),
    "beta2": Fraction(3, 20), "beta3plus": Fraction(97, 625),
}
EXPECTED_GRADIENT_GATES = {
    "decimal_dps_at_least_90", "source_sha_pinned", "bands_sha_pinned",
    "operator_unchanged_during_run", "band_dependency_sha_pinned_and_unchanged",
    "grouped_sha_pinned_and_unchanged", "integrator_sha_pinned_and_unchanged",
    "source_k48_dim272_banddim20", "parameters_exact_c10",
    "all_vectors_length20", "all_numbers_finite", "gradient_halves_match",
    "denominator_positive", "quotient_recomputed", "euler_relative_below_1e50",
    "complete_traversal_counts", "stratum_buckets_sum",
    "baseline_artifact_sha_pinned", "baseline_dependencies_match",
    "baseline_forms_50_digits",
}


def file_sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def dec(text):
    q = Fraction(text)
    return Decimal(q.numerator) / Decimal(q.denominator)


def rational_string(x):
    return str(Fraction(str(x)))


def load_bound(path):
    data = Path(path).read_bytes()
    return json.loads(data), hashlib.sha256(data).hexdigest()


def validate_gradient(gradient, band_map, source_path, bands_path):
    """Repeat every fail-closed binding before consuming a gradient."""
    errors = []

    def require(condition, message):
        if not condition:
            errors.append(message)

    require(gradient.get("status") ==
            "multiprecision-degree-band-gradient-discovery", "status")
    require(gradient.get("implementation") == "sparse-structure-of-arrays",
            "implementation")
    require(gradient.get("rigorous") is False and gradient.get("complete") is True,
            "arithmetic/status")
    require(int(gradient.get("decimal_dps", 0)) >= 90, "precision")
    require(gradient.get("gates_passed") is True and
            set(gradient.get("gates", {})) == EXPECTED_GRADIENT_GATES and
            all(gradient.get("gates", {}).values()),
            "producer gates")
    require(file_sha(source_path) == band_map.source_sha256 == PINNED["source"],
            "source SHA")
    require(file_sha(bands_path) == band_map.bands_sha256 == PINNED["bands"],
            "bands SHA")
    require(gradient.get("source_sha256") == PINNED["source"] and
            gradient.get("bands_sha256") == PINNED["bands"],
            "serialized source/bands SHA")
    require(gradient.get("operator_sha256") == PINNED["sparse_operator"] and
            file_sha(Path(HERE) / "band_operator_sparse.py") ==
            PINNED["sparse_operator"], "sparse operator SHA")
    require(gradient.get("band_operator_dependency_sha256") ==
            PINNED["band_operator"] and
            file_sha(Path(HERE) / "band_operator.py") == PINNED["band_operator"],
            "band dependency SHA")
    require(gradient.get("grouped_evaluator_sha256") == PINNED["grouped"] and
            file_sha(Path(EXACT_AGENT) / "grouped_fixed_vector.py") ==
            PINNED["grouped"], "grouped evaluator SHA")
    require(gradient.get("integrator_sha256") == PINNED["integrator"] and
            file_sha(Path(EXACT_AGENT) / "src" / "exact_integrator.py") ==
            PINNED["integrator"], "integrator SHA")
    require(all(Fraction(gradient.get("parameters", {}).get(key, "NaN")) == value
                for key, value in PARAMETERS.items()), "C10 parameters")
    source = json.loads(Path(source_path).read_bytes())
    require(int(source.get("k", -1)) == 48 and len(source.get("basis", [])) == 272 and
            band_map.dimension == 20, "dimensions")
    vector_keys = ("theta", "a_theta", "b_theta",
                   "grad_denominator", "grad_numerator")
    require(all(len(gradient.get(key, [])) == 20 for key in vector_keys),
            "vector lengths")
    try:
        vectors = {key: [dec(x) for x in gradient[key]] for key in vector_keys}
        scalars = {key: dec(gradient[key]) for key in
                   ("denominator", "numerator", "quotient",
                    "euler_denominator_error", "euler_numerator_error")}
        require(all(x.is_finite() for values in vectors.values() for x in values) and
                all(x.is_finite() for x in scalars.values()), "finite numbers")
        require(all(2 * a == g for a, g in zip(
            vectors["a_theta"], vectors["grad_denominator"])) and all(
            2 * b == g for b, g in zip(
                vectors["b_theta"], vectors["grad_numerator"])),
                "gradient halves")
        with localcontext() as ctx:
            ctx.prec = int(gradient["decimal_dps"])
            recomputed_quotient = (scalars["numerator"] /
                                   scalars["denominator"])
        require(scalars["denominator"] > 0 and
                scalars["quotient"] == recomputed_quotient,
                "denominator/quotient")
        require(abs(scalars["euler_denominator_error"]) <=
                Decimal("1e-50") * abs(scalars["denominator"]) and
                abs(scalars["euler_numerator_error"]) <=
                Decimal("1e-50") * abs(scalars["numerator"]), "Euler")
        with localcontext() as ctx:
            ctx.prec = int(gradient["decimal_dps"])
            expected_theta = [Decimal(q.numerator) / Decimal(q.denominator)
                              for q in band_map.theta0_q]
        require(vectors["theta"] == expected_theta, "theta0")
    except Exception as exc:
        errors.append(f"numeric parse/check: {exc}")
    require((gradient.get("i_orbit_groups"), gradient.get("i_faces"),
             gradient.get("marginal_components"),
             gradient.get("j_branch_integrals")) == (1575, 312, 695, 1200),
            "traversal counts")
    require(len(gradient.get("i_value_by_r", [])) == 16 and
            len(gradient.get("j_value_by_r", [])) == 16, "by-r bucket lengths")
    try:
        i_buckets = [dec(x) for x in gradient["i_value_by_r"]]
        j_buckets = [dec(x) for x in gradient["j_value_by_r"]]
        with localcontext() as ctx:
            ctx.prec = int(gradient["decimal_dps"])
            i_sum = sum(i_buckets, Decimal(0))
            n_sum = Decimal(48) * sum(j_buckets, Decimal(0))
        require(i_sum == scalars["denominator"] and
                n_sum == scalars["numerator"],
                "by-r sums")
        baseline_path = Path(EXACT_AGENT) / "results" / \
            "c10_capped_fullD12_vector_grouped_mp100.json"
        baseline, baseline_sha = load_bound(baseline_path)
        require(baseline_sha == gradient.get("baseline_sha256") ==
                "02e1a6676a68380592fd272845f7714d583574bd74f73b9a96727171751281d9",
                "baseline SHA")
        require(baseline.get("input_sha256") == PINNED["source"] and
                baseline.get("script_sha256") == PINNED["grouped"] and
                baseline.get("integrator_sha256") == PINNED["integrator"] and
                all(Fraction(baseline.get("parameters", {}).get(key, "NaN")) == value
                    for key, value in PARAMETERS.items()), "baseline bindings")
        tolerance = Decimal("1e-50")
        for key in ("denominator", "numerator", "quotient"):
            reference = dec(baseline[key])
            require(abs(scalars[key] - reference) <= tolerance * abs(reference),
                    f"baseline {key}")
    except Exception as exc:
        errors.append(f"bucket/baseline check: {exc}")
    if errors:
        raise SystemExit("gradient validation failed: " + ", ".join(errors))
    return vectors, scalars


def direction_from_gradient(gradient, band_map, precision):
    with localcontext() as ctx:
        ctx.prec = precision
        theta = [dec(x) for x in gradient["theta"]]
        a_theta = [dec(x) for x in gradient["a_theta"]]
        b_theta = [dec(x) for x in gradient["b_theta"]]
        quotient = dec(gradient["quotient"])
        residual = [b - quotient * a for a, b in zip(a_theta, b_theta)]
        alpha = dec(gradient["parameters"]["alpha"])
        p = full_simplex_i_preconditioner(
            band_map, 48, alpha, Decimal, False)
        raw_direction = decimal_solve(p, residual, precision)
        raw_p_direction = matvec(p, raw_direction, Decimal(0))
        raw_solve_error = max(abs(x - y) for x, y in
                              zip(raw_p_direction, residual)) / max(
                                  max(abs(x) for x in residual), Decimal(1).scaleb(-999))
        direction = raw_direction
        ptheta = matvec(p, theta, Decimal(0))
        pdir = matvec(p, direction, Decimal(0))
        projection = dot(theta, pdir, Decimal(0)) / dot(theta, ptheta, Decimal(0))
        direction = [d - projection * t for d, t in zip(direction, theta)]
        pdir = matvec(p, direction, Decimal(0))
        norm2 = dot(direction, pdir, Decimal(0))
        if norm2 <= 0:
            raise ArithmeticError("nonpositive correction norm")
        norm = norm2.sqrt()
        direction = [+(d / norm) for d in direction]
        pdir = matvec(p, direction, Decimal(0))
        orthogonality = dot(theta, pdir, Decimal(0))
        normalized_error = dot(direction, pdir, Decimal(0)) - Decimal(1)
        diagnostics = {
            "raw_solve_relative_infinity_error": raw_solve_error,
            "theta_p_direction": orthogonality,
            "direction_p_norm_error": normalized_error,
            "theta_p_norm": dot(theta, ptheta, Decimal(0)),
        }
        return theta, a_theta, b_theta, direction, residual, diagnostics


def expand_rational(band_map, theta):
    theta_q = [Fraction(str(x)) for x in theta]
    return [str(band_map.weight_q[i] * theta_q[band_map.owner[i]])
            for i in range(len(band_map.labels))]


def prepare(args):
    gradient, gradient_sha = load_bound(args.gradient)
    band_map = BandMap.from_source_and_bands(args.source, args.bands)
    validate_gradient(gradient, band_map, args.source, args.bands)
    first = direction_from_gradient(
        gradient, band_map, args.precision)
    second = direction_from_gradient(
        gradient, band_map, args.precision + 40)
    theta, a_theta, b_theta, direction, residual, diagnostics = first
    second_direction = second[3]
    stability_scale = max(max(abs(x) for x in second_direction), Decimal(1))
    direction_stability = max(abs(x - y) for x, y in
                              zip(direction, second_direction)) / stability_scale
    normalized_orthogonality = (abs(diagnostics["theta_p_direction"]) /
                                diagnostics["theta_p_norm"].sqrt())
    if (direction_stability > Decimal("1e-80") or
            diagnostics["raw_solve_relative_infinity_error"] > Decimal("1e-180") or
            normalized_orthogonality > Decimal("1e-180") or
            abs(diagnostics["direction_p_norm_error"]) > Decimal("1e-180")):
        raise SystemExit("preconditioned direction failed stability/residual gates")
    line_hash = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    vector_input = {
        "status": "degree-band-preconditioned-direction-input",
        "k": 48,
        "basis": [[a, list(lam)] for a, lam in band_map.labels],
        "rational_vector": expand_rational(band_map, direction),
        "provenance": {
            "gradient_json": args.gradient,
            "gradient_sha256": gradient_sha,
            "source_sha256": band_map.source_sha256,
            "bands_sha256": band_map.bands_sha256,
            "line_search_sha256": line_hash,
            "sparse_operator_sha256": PINNED["sparse_operator"],
            "band_operator_sha256": PINNED["band_operator"],
            "grouped_evaluator_sha256": PINNED["grouped"],
            "integrator_sha256": PINNED["integrator"],
            "precision": args.precision,
            "second_precision": args.precision + 40,
            "theta": [str(x) for x in theta],
            "a_theta": [str(x) for x in a_theta],
            "b_theta": [str(x) for x in b_theta],
            "direction": [str(x) for x in direction],
            "residual": [str(x) for x in residual],
            "raw_solve_relative_infinity_error": str(
                diagnostics["raw_solve_relative_infinity_error"]),
            "theta_p_direction": str(diagnostics["theta_p_direction"]),
            "theta_p_norm": str(diagnostics["theta_p_norm"]),
            "normalized_p_orthogonality": str(normalized_orthogonality),
            "direction_p_norm_error": str(
                diagnostics["direction_p_norm_error"]),
            "direction_second_precision_relative_difference": str(
                direction_stability),
        },
    }
    Path(args.output).write_text(json.dumps(vector_input, indent=2) + "\n")
    print(json.dumps({"output": args.output,
                      "gradient_sha256": gradient_sha,
                      "direction_p_normalized": True,
                      "direction_stability": str(direction_stability),
                      "precision": args.precision}, indent=2))


def rayleigh(a0, a1, a2, b0, b1, b2, t):
    return ((b0 + 2 * b1 * t + b2 * t * t) /
            (a0 + 2 * a1 * t + a2 * t * t))


def validate_direction_result(direction_result, direction_input,
                              direction_input_sha, band_map, gradient,
                              gradient_sha):
    errors = []

    def require(condition, message):
        if not condition:
            errors.append(message)

    provenance = direction_input.get("provenance", {})
    require(direction_input.get("status") ==
            "degree-band-preconditioned-direction-input", "input status")
    require(direction_input.get("k") == 48, "input k")
    require(provenance.get("gradient_sha256") == gradient_sha,
            "gradient binding")
    require(provenance.get("source_sha256") == PINNED["source"] and
            provenance.get("bands_sha256") == PINNED["bands"],
            "input source/bands")
    require(provenance.get("line_search_sha256") == file_sha(__file__),
            "line-search SHA")
    require(provenance.get("sparse_operator_sha256") == PINNED["sparse_operator"] and
            provenance.get("band_operator_sha256") == PINNED["band_operator"] and
            provenance.get("grouped_evaluator_sha256") == PINNED["grouped"] and
            provenance.get("integrator_sha256") == PINNED["integrator"],
            "input dependency SHAs")
    expected_basis = [[a, list(lam)] for a, lam in band_map.labels]
    require(direction_input.get("basis") == expected_basis, "input basis")
    direction = provenance.get("direction", [])
    require(len(direction) == 20 and len(direction_input.get("rational_vector", [])) == 272,
            "direction dimensions")
    if len(direction) == 20:
        expected_vector = expand_rational(band_map, [dec(x) for x in direction])
        require(all(Fraction(x) == Fraction(y) for x, y in zip(
            direction_input.get("rational_vector", []), expected_vector)),
                "direction expansion")
    try:
        precision = int(provenance.get("precision", 0))
        second_precision = int(provenance.get("second_precision", 0))
        require(precision >= 220 and second_precision == precision + 40,
                "preconditioner precisions")
        first = direction_from_gradient(gradient, band_map, precision)
        second = direction_from_gradient(gradient, band_map, second_precision)
        theta, a_theta, b_theta, expected_direction, residual, diagnostics = first
        require([dec(x) for x in provenance.get("theta", [])] == theta,
                "recomputed theta")
        require([dec(x) for x in provenance.get("a_theta", [])] == a_theta,
                "recomputed Atheta")
        require([dec(x) for x in provenance.get("b_theta", [])] == b_theta,
                "recomputed Btheta")
        require([dec(x) for x in direction] == expected_direction,
                "recomputed direction")
        require([dec(x) for x in provenance.get("residual", [])] == residual,
                "recomputed residual")
        second_direction = second[3]
        stability_scale = max(max(abs(x) for x in second_direction), Decimal(1))
        stability = max(abs(x - y) for x, y in
                        zip(expected_direction, second_direction)) / stability_scale
        normalized_orthogonality = (
            abs(diagnostics["theta_p_direction"]) /
            diagnostics["theta_p_norm"].sqrt())
        recomputed = {
            "raw_solve_relative_infinity_error":
                diagnostics["raw_solve_relative_infinity_error"],
            "theta_p_direction": diagnostics["theta_p_direction"],
            "theta_p_norm": diagnostics["theta_p_norm"],
            "normalized_p_orthogonality": normalized_orthogonality,
            "direction_p_norm_error": diagnostics["direction_p_norm_error"],
            "direction_second_precision_relative_difference": stability,
        }
        require(all(dec(provenance.get(key, "NaN")) == value
                    for key, value in recomputed.items()),
                "recomputed direction diagnostics")
        require(stability <= Decimal("1e-80") and
                diagnostics["raw_solve_relative_infinity_error"] <=
                Decimal("1e-180") and
                normalized_orthogonality <= Decimal("1e-180") and
                abs(diagnostics["direction_p_norm_error"]) <= Decimal("1e-180"),
                "direction residual gates")
    except Exception as exc:
        errors.append(f"direction recomputation: {exc}")

    recognized = {"multiprecision-grouped-fixed-vector-discovery",
                  "exact-grouped-fixed-vector"}
    require(direction_result.get("status") in recognized, "result status")
    require(direction_result.get("input_sha256") == direction_input_sha,
            "result/input SHA")
    require(direction_result.get("k") == 48 and
            direction_result.get("basis_dimension") == 272, "result dimensions")
    require(direction_result.get("script_sha256") == PINNED["grouped"] and
            direction_result.get("integrator_sha256") == PINNED["integrator"],
            "result dependencies")
    require(all(Fraction(direction_result.get("parameters", {}).get(key, "NaN")) == value
                for key, value in PARAMETERS.items()), "result parameters")
    require((direction_result.get("i_orbit_groups"), direction_result.get("i_faces"),
             direction_result.get("marginal_components"),
             direction_result.get("j_branch_integrals")) == (1575, 312, 695, 1200),
            "result traversal counts")
    require(direction_result.get("denominator_positive") is True,
            "positive direction I")
    if not direction_result.get("rigorous"):
        require(int(direction_result.get("decimal_dps", 0)) >= 100,
                "result precision")
    try:
        if direction_result.get("rigorous"):
            denominator_q = Fraction(direction_result["denominator"])
            j_value_q = Fraction(direction_result["j_value"])
            numerator_q = Fraction(direction_result["numerator"])
            quotient_q = Fraction(direction_result["quotient"])
            require(numerator_q == 48 * j_value_q, "48J reconstruction")
            require(quotient_q == numerator_q / denominator_q,
                    "quotient reconstruction")
        else:
            denominator = dec(direction_result["denominator"])
            j_value = dec(direction_result["j_value"])
            numerator = dec(direction_result["numerator"])
            quotient = dec(direction_result["quotient"])
            with localcontext() as ctx:
                ctx.prec = int(direction_result["decimal_dps"])
                numerator_recomputed = Decimal(48) * j_value
                quotient_recomputed = numerator / denominator
            require(numerator == numerator_recomputed, "48J reconstruction")
            require(quotient == quotient_recomputed, "quotient reconstruction")
    except Exception as exc:
        errors.append(f"result numeric check: {exc}")
    if errors:
        raise SystemExit("direction validation failed: " + ", ".join(errors))
    return [dec(x) for x in direction]


def solve_projected_line(forms, precision):
    with localcontext() as ctx:
        ctx.prec = precision
        a0, a1, a2, b0, b1, b2 = map(lambda x: +x, forms)
        c0 = b1 * a0 - a1 * b0
        c1 = b2 * a0 - a2 * b0
        c2 = b2 * a1 - a2 * b1
        candidates = [Decimal(0)]
        if c2:
            discriminant = c1 * c1 - Decimal(4) * c2 * c0
            if discriminant >= 0:
                root = discriminant.sqrt()
                candidates.extend(((-c1 + root) / (Decimal(2) * c2),
                                   (-c1 - root) / (Decimal(2) * c2)))
        elif c1:
            candidates.append(-c0 / c1)
        feasible = []
        for t in candidates:
            denominator = a0 + Decimal(2) * a1 * t + a2 * t * t
            if denominator > 0:
                feasible.append((rayleigh(a0, a1, a2, b0, b1, b2, t), t))
        feasible.append((b2 / a2, None))
        quotient, t = max(feasible, key=lambda x: x[0])
        return (+quotient, None if t is None else +t,
                (+c0, +c1, +c2), [(+q, None if x is None else +x)
                                   for q, x in feasible])


def finish(args):
    gradient, gradient_sha = load_bound(args.gradient)
    band_map = BandMap.from_source_and_bands(args.source, args.bands)
    validate_gradient(gradient, band_map, args.source, args.bands)
    direction_result, direction_result_sha = load_bound(args.direction_result)
    direction_input_path = Path(direction_result["input_json"])
    if not direction_input_path.is_absolute():
        direction_input_path = Path.cwd() / direction_input_path
    direction_input, direction_input_sha = load_bound(direction_input_path)
    provenance = direction_input.get("provenance", {})
    direction = validate_direction_result(
        direction_result, direction_input, direction_input_sha,
        band_map, gradient, gradient_sha)
    with localcontext() as ctx:
        ctx.prec = args.precision
        theta = [dec(x) for x in gradient["theta"]]
        a_theta = [dec(x) for x in gradient["a_theta"]]
        b_theta = [dec(x) for x in gradient["b_theta"]]
        a0, b0 = dec(gradient["denominator"]), dec(gradient["numerator"])
        a1 = dot(direction, a_theta, Decimal(0))
        b1 = dot(direction, b_theta, Decimal(0))
        a2 = dec(direction_result["denominator"])
        b2 = dec(direction_result["numerator"])
        forms = (a0, a1, a2, b0, b1, b2)
        quotient, t, coefficients, feasible = solve_projected_line(
            forms, args.precision)
        quotient2, t2, _, _ = solve_projected_line(
            forms, args.precision + 40)
        quotient_stability = abs(quotient - quotient2) / max(
            abs(quotient2), Decimal(1))
        if t is None or t2 is None:
            t_stability = Decimal(0) if t is t2 else Decimal("Infinity")
        else:
            t_stability = abs(t - t2) / max(abs(t2), Decimal(1))
        gram_determinant = a0 * a2 - a1 * a1
        gram_relative = gram_determinant / (a0 * a2)
        if (gram_relative <= Decimal("1e-40") or
                quotient_stability > Decimal("1e-80") or
                t_stability > Decimal("1e-80")):
            raise SystemExit("projected line failed Gram/stability gates")
        if t is None:
            candidate = direction
        else:
            candidate = [x + t * d for x, d in zip(theta, direction)]
        expanded = expand_rational(band_map, candidate)
    source = json.loads(Path(args.source).read_bytes())
    candidate_input = {
        "status": "degree-band-two-dimensional-line-candidate",
        "k": 48,
        "basis": source["basis"],
        "rational_vector": expanded,
        "line_search": {
            "rigorous": False,
            "gradient_sha256": gradient_sha,
            "direction_result_sha256": direction_result_sha,
            "direction_input_sha256": direction_input_sha,
            "precision": args.precision,
            "a00": str(a0), "a01": str(a1), "a11": str(a2),
            "b00": str(b0), "b01": str(b1), "b11": str(b2),
            "i_gram_determinant": str(gram_determinant),
            "i_gram_relative_determinant": str(gram_relative),
            "stationary_coefficients": [str(x) for x in coefficients],
            "all_feasible_projected_points": [
                {"quotient": str(q), "t": None if x is None else str(x)}
                for q, x in feasible],
            "winning_t": None if t is None else str(t),
            "projected_quotient": str(quotient),
            "second_precision": args.precision + 40,
            "winning_t_relative_stability": str(t_stability),
            "projected_quotient_relative_stability": str(quotient_stability),
            "compressed_theta": [str(x) for x in candidate],
        },
    }
    Path(args.output).write_text(json.dumps(candidate_input, indent=2) + "\n")
    print(json.dumps(candidate_input["line_search"], indent=2))


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="command", required=True)
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--source", required=True)
    common.add_argument("--bands", required=True)
    common.add_argument("--gradient", required=True)
    common.add_argument("--precision", type=int, default=230)
    common.add_argument("--output", required=True)
    p = sub.add_parser("prepare", parents=[common])
    p.set_defaults(function=prepare)
    p = sub.add_parser("finish", parents=[common])
    p.add_argument("--direction-result", required=True)
    p.set_defaults(function=finish)
    args = ap.parse_args()
    getcontext().prec = args.precision
    args.function(args)


if __name__ == "__main__":
    main()
