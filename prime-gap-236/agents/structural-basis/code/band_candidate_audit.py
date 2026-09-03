#!/usr/bin/env python3
"""Fail-closed polarization audit of a scalar degree-band line candidate.

This consumes the mandatory scalar evaluation of the final line candidate and
uses it to check both jet cross terms without an extra integration run.
It remains a multiprecision discovery audit, not an exact certificate.
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

from band_line_search import (PARAMETERS, PINNED, BandMap, dec, dot,  # noqa: E402
                              expand_rational, file_sha, load_bound,
                              solve_projected_line, validate_direction_result,
                              validate_gradient)


def validate_scalar_candidate(result, input_data, input_sha):
    errors = []

    def require(condition, message):
        if not condition:
            errors.append(message)

    recognized = {"multiprecision-grouped-fixed-vector-discovery",
                  "exact-grouped-fixed-vector"}
    require(result.get("status") in recognized, "status")
    require(result.get("input_sha256") == input_sha, "input SHA")
    require(result.get("k") == 48 and result.get("basis_dimension") == 272,
            "dimensions")
    require(result.get("script_sha256") == PINNED["grouped"] and
            result.get("integrator_sha256") == PINNED["integrator"],
            "dependencies")
    require(all(Fraction(result.get("parameters", {}).get(key, "NaN")) == value
                for key, value in PARAMETERS.items()), "parameters")
    require((result.get("i_orbit_groups"), result.get("i_faces"),
             result.get("marginal_components"), result.get("j_branch_integrals")) ==
            (1575, 312, 695, 1200), "traversal counts")
    require(result.get("denominator_positive") is True, "positive I")
    if not result.get("rigorous"):
        require(int(result.get("decimal_dps", 0)) >= 100, "precision")
    if errors:
        raise SystemExit("candidate scalar validation failed: " + ", ".join(errors))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True)
    ap.add_argument("--bands", required=True)
    ap.add_argument("--gradient", required=True)
    ap.add_argument("--direction-result", required=True)
    ap.add_argument("--candidate-result", required=True)
    ap.add_argument("--precision", type=int, default=230)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()
    getcontext().prec = args.precision

    band_map = BandMap.from_source_and_bands(args.source, args.bands)
    gradient, gradient_sha = load_bound(args.gradient)
    validate_gradient(gradient, band_map, args.source, args.bands)
    direction_result, direction_result_sha = load_bound(args.direction_result)
    direction_input_path = Path(direction_result["input_json"])
    if not direction_input_path.is_absolute():
        direction_input_path = Path.cwd() / direction_input_path
    direction_input, direction_input_sha = load_bound(direction_input_path)
    direction = validate_direction_result(
        direction_result, direction_input, direction_input_sha,
        band_map, gradient, gradient_sha)

    candidate_result, candidate_result_sha = load_bound(args.candidate_result)
    candidate_input_path = Path(candidate_result["input_json"])
    if not candidate_input_path.is_absolute():
        candidate_input_path = Path.cwd() / candidate_input_path
    candidate_input, candidate_input_sha = load_bound(candidate_input_path)
    validate_scalar_candidate(candidate_result, candidate_input, candidate_input_sha)
    line = candidate_input.get("line_search", {})
    if (candidate_input.get("status") !=
            "degree-band-two-dimensional-line-candidate" or
            candidate_input.get("k") != 48 or
            line.get("gradient_sha256") != gradient_sha or
            line.get("direction_result_sha256") != direction_result_sha or
            line.get("direction_input_sha256") != direction_input_sha):
        raise SystemExit("candidate line provenance mismatch")
    expected_basis = [[a, list(lam)] for a, lam in band_map.labels]
    if candidate_input.get("basis") != expected_basis:
        raise SystemExit("candidate basis mismatch")

    theta = [dec(x) for x in gradient["theta"]]
    candidate_theta = [dec(x) for x in line.get("compressed_theta", [])]
    if len(candidate_theta) != 20:
        raise SystemExit("candidate compressed dimension mismatch")
    expected_expansion = expand_rational(band_map, candidate_theta)
    if (len(candidate_input.get("rational_vector", [])) != 272 or
            not all(Fraction(x) == Fraction(y) for x, y in zip(
                candidate_input["rational_vector"], expected_expansion))):
        raise SystemExit("candidate expansion mismatch")

    t_text = line.get("winning_t")
    if t_text is None:
        raise SystemExit("polarization audit requires a finite winning t")
    t = dec(t_text)
    if not t:
        raise SystemExit("polarization audit requires nonzero t")
    expected_theta = [x + t * d for x, d in zip(theta, direction)]
    if candidate_theta != expected_theta:
        raise SystemExit("candidate is not theta+t*d")

    a0, b0 = dec(gradient["denominator"]), dec(gradient["numerator"])
    a2, b2 = dec(direction_result["denominator"]), dec(direction_result["numerator"])
    a1 = dot(direction, [dec(x) for x in gradient["a_theta"]], Decimal(0))
    b1 = dot(direction, [dec(x) for x in gradient["b_theta"]], Decimal(0))
    forms = (a0, a1, a2, b0, b1, b2)
    projected_q, projected_t, _, _ = solve_projected_line(
        forms, int(line["precision"]))
    if projected_t != t or projected_q != dec(line["projected_quotient"]):
        raise SystemExit("candidate does not recompute as winning projected point")

    observed_d = dec(candidate_result["denominator"])
    observed_n = dec(candidate_result["numerator"])
    expected_d = a0 + Decimal(2) * t * a1 + t * t * a2
    expected_n = b0 + Decimal(2) * t * b1 + t * t * b2
    observed_a1 = (observed_d - a0 - t * t * a2) / (Decimal(2) * t)
    observed_b1 = (observed_n - b0 - t * t * b2) / (Decimal(2) * t)
    tolerance = Decimal("1e-50")

    def relative(x, y):
        return abs(x - y) / max(abs(y), Decimal(1).scaleb(-999))

    checks = {
        "denominator_projected_relative_error": relative(observed_d, expected_d),
        "numerator_projected_relative_error": relative(observed_n, expected_n),
        "A01_polarization_relative_error": relative(observed_a1, a1),
        "B01_polarization_relative_error": relative(observed_b1, b1),
    }
    passed = all(value <= tolerance for value in checks.values())
    output = {
        "status": ("mp-scalar-candidate-polarization-pass" if passed else
                   "mp-scalar-candidate-polarization-fail"),
        "rigorous": False,
        "gradient_sha256": gradient_sha,
        "direction_result_sha256": direction_result_sha,
        "candidate_input_sha256": candidate_input_sha,
        "candidate_result_sha256": candidate_result_sha,
        "audit_script_sha256": file_sha(__file__),
        "tolerance": str(tolerance),
        **{key: str(value) for key, value in checks.items()},
        "observed_quotient": str(observed_n / observed_d),
        "passed": passed,
    }
    Path(args.output).write_text(json.dumps(output, indent=2) + "\n")
    print(json.dumps(output, indent=2))
    if not passed:
        raise SystemExit("candidate polarization audit failed")


if __name__ == "__main__":
    main()
