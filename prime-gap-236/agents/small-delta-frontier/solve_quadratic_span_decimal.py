#!/usr/bin/env python3
"""Fail-closed discovery consumer for the D12 span {F,QF}.

The two fresh transfer outputs are Q and H=Q+s*1.  The only presently
available base output used the unscaled coefficient file, so its forms are
rescaled by the exact integer L^2 under an explicit heuristic flag.  This is
not a theorem or byte-identical SHA8650 base traversal.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import sys
from decimal import Decimal, localcontext
from fractions import Fraction
from math import gcd
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import build_quadratic_span_contingency as builder


BASE_OUTPUT_SHA = "02e1a6676a68380592fd272845f7714d583574bd74f73b9a96727171751281d9"
ORIGINAL_INPUT_SHA = "719c656e6e45388273b4c27f51f7a18b33e9ed1abb5f883e6fcc5de5d6d64a87"
SCALED_INPUT_SHA = "8650e44cace6b6d3e4eee8e1632cfd8a59cde6a48f76a8763dcfb400e49f4a93"
Q_MULTIPLIER_SHA = builder.SOURCE_SHA
BUILDER_SHA = "aa15dd4a8e578ad96edfa3697b138c21ac034010ac8e089515cbed03731e256c"
GROUPED_SHA = "47167e92a0f346e969706dc282ccb2dfd4ac31a0a75b654938ffbe8423cf4a4a"
INTEGRATOR_SHA = "941ee82bc72fd8488a95eb5e536fe47f8c95d39a1b618dae7d6ef7eb27122e52"
TRANSFER_DEPENDENCIES = {
    "driver": "cd1232cb448fbda9003fab366e9095ffd36913d83ddaeba9e9521d886057b07f",
    "quadratic": "62dad8c96005bdb06945552a36b6dc35cecea6633daa5f3cf06e514a6aa77234",
    "stratum_amplitude": "d23d42315d7b518ae5d3f200a6192f47f3500d6eebd3a73fb6aa4ce7a23c7887",
    "stratum_linear": "7400369a2e0e321ed032374f1e45f35785b0f0c53a085af18bf5ec2cb3c80162",
    "grouped": GROUPED_SHA,
    "integrator": INTEGRATOR_SHA,
    "robust_solver": "2086244acb674e5bd92e4880fb38d32d6dd981cd0272db595de2578554da257e",
    "scheduled_basis": "06f79a13dbf172f40716d603ae8d824b5f65d2d69ed08dee59bd5c091821c4d0",
    "scheduled_verifier": "97f36696712f9cbe0cc0fff1fab6c4dc5ec4850220c12ebcc63f9c794aff1a1a",
}
TRANSFER_GATES = {
    "dependencies_unchanged", "input_unchanged", "multiplier_unchanged",
    "i_stage_unchanged", "inputs_pinned", "counts_complete",
    "denominator_positive", "finite",
}
TRANSFER_KEYS = {
    "status", "rigorous", "complete", "space_note", "theorem_ready",
    "decimal_dps", "input_json", "input_sha256", "multiplier_json",
    "multiplier_sha256", "parameters", "dependency_hashes",
    "fixed_basis_dimension", "multiplier_dimension", "i_stage_json",
    "i_stage_sha256", "i_by_r", "j_by_common_r", "denominator",
    "numerator", "quotient", "margin", "margin_positive",
    "i_orbit_groups", "i_faces", "marginal_components",
    "j_branch_domains", "i_seconds", "j_seconds", "total_seconds",
    "peak_rss_kib", "gates", "gates_passed",
}
STAGE_KEYS = {
    "status", "rigorous", "complete", "decimal_dps", "input_sha256",
    "multiplier_sha256", "parameters", "dependency_hashes",
    "i_orbit_groups", "i_faces", "i_by_r", "denominator", "i_seconds",
}
H_MULTIPLIER_KEYS = {
    "status", "construction", "rigorous_forms",
    "eigenvector_discovery_rigorous", "theorem_ready", "k", "parameters",
    "fixed_basis_dimension", "quadratic_basis_dimension",
    "discovery_basis_dimension", "channel_powers", "quadratic_labels",
    "active_quadratic_labels", "discarded_gram_dependent_labels",
    "constant_scale_s", "source_multiplier_json",
    "source_multiplier_sha256", "input_json", "input_sha256",
    "script_sha256", "dependency_hashes", "rational_vector",
    "base_denominator", "base_numerator", "q_denominator", "q_numerator",
    "base_q_i_cross", "base_q_n_cross", "denominator", "numerator",
    "quotient", "margin", "denominator_positive", "margin_positive",
    "block_direct_bitwise_equal", "i_orbit_groups", "i_faces",
    "marginal_components", "j_branch_domains", "direct_i_faces",
    "direct_j_branch_domains", "direct_seconds", "exact_gates",
    "d4_span_stationary", "note",
}
DECIMAL_RE = re.compile(
    r"^-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:E[+-][0-9]+)?$")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def exact_decimal(text, name):
    require(isinstance(text, str) and DECIMAL_RE.fullmatch(text) is not None,
            f"{name} is not a canonical Decimal string")
    value = Decimal(text)
    require(value.is_finite() and str(value) == text,
            f"{name} is nonfinite or noncanonical")
    return value


def decimal_fraction(text, name):
    return Fraction(exact_decimal(text, name))


def replay_decimal_payload(raw, prefix):
    with localcontext() as context:
        context.prec = 100
        denominator = exact_decimal(raw.get("denominator"),
                                    f"{prefix} denominator")
        numerator = exact_decimal(raw.get("numerator"), f"{prefix} numerator")
        quotient = exact_decimal(raw.get("quotient"), f"{prefix} quotient")
        margin = exact_decimal(raw.get("margin"), f"{prefix} margin")
        require(numerator / denominator == quotient,
                f"{prefix} quotient does not replay at Decimal100")
        require(numerator - denominator == margin,
                f"{prefix} margin does not replay at Decimal100")
    return denominator, numerator


def validate_base(raw):
    require(isinstance(raw, dict), "base output must be an object")
    require(raw.get("status") == "multiprecision-grouped-fixed-vector-discovery" and
            raw.get("rigorous") is False,
            "wrong base output status/rigor")
    require(type(raw.get("decimal_dps")) is int and raw["decimal_dps"] == 100,
            "base output is not Decimal100")
    require(type(raw.get("k")) is int and raw["k"] == 48 and
            raw.get("parameters") == builder.PARAMETERS,
            "base output k/parameters changed")
    require(raw.get("input_sha256") == ORIGINAL_INPUT_SHA,
            "base output does not bind the original D12 input")
    require(raw.get("script_sha256") == GROUPED_SHA and
            raw.get("integrator_sha256") == INTEGRATOR_SHA,
            "base output arithmetic dependencies changed")
    require(type(raw.get("basis_dimension")) is int and
            raw["basis_dimension"] == 272 and
            type(raw.get("i_orbit_groups")) is int and
            raw["i_orbit_groups"] == 1575 and
            type(raw.get("i_faces")) is int and raw["i_faces"] == 312 and
            type(raw.get("marginal_components")) is int and
            raw["marginal_components"] == 695 and
            type(raw.get("j_branch_integrals")) is int and
            raw["j_branch_integrals"] == 1200,
            "base output counts changed")
    denominator, numerator = replay_decimal_payload(raw, "base")
    with localcontext() as context:
        context.prec = 100
        j_value = exact_decimal(raw.get("j_value"), "base j_value")
        require(Decimal(48) * j_value == numerator,
                "base factor-48 identity failed")
    require(raw.get("denominator_positive") is True and denominator > 0 and
            raw.get("margin_positive") is (numerator > denominator),
            "base sign booleans disagree")
    return Fraction(denominator), Fraction(numerator)


def validate_scaled_input(scaled, original):
    require(isinstance(scaled, dict) and isinstance(original, dict),
            "D12 inputs must be objects")
    require(scaled.get("status") == "exact-integer-scaled-fixed-vector-input" and
            type(scaled.get("k")) is int and scaled["k"] == 48 and
            type(scaled.get("degree")) is int and scaled["degree"] == 12 and
            type(scaled.get("basis_dimension")) is int and
            scaled["basis_dimension"] == 272,
            "scaled D12 input header changed")
    require(type(original.get("k")) is int and original["k"] == 48 and
            original.get("basis") == scaled.get("basis") and
            len(original.get("basis", [])) == 272,
            "original/scaled D12 bases disagree")
    metadata = scaled.get("integer_scaling")
    require(isinstance(metadata, dict) and
            set(metadata) == {"source_json", "source_sha256",
                              "least_common_denominator", "form_scale",
                              "quotient_and_margin_sign_preserved"} and
            metadata["source_sha256"] == ORIGINAL_INPUT_SHA and
            metadata["form_scale"] == "least_common_denominator^2" and
            metadata["quotient_and_margin_sign_preserved"] is True,
            "scaled D12 metadata changed")
    lcm = builder.canonical_fraction(
        metadata["least_common_denominator"], "base LCM")
    require(lcm.denominator == 1 and lcm > 0 and
            lcm.numerator.bit_length() == 714,
            "base LCM is not the frozen 714-bit positive integer")
    source_vector = original.get("rational_vector")
    scaled_vector = scaled.get("rational_vector")
    require(isinstance(source_vector, list) and isinstance(scaled_vector, list) and
            len(source_vector) == len(scaled_vector) == 272,
            "D12 vectors are malformed")
    integers = []
    for i, (source_value, scaled_value) in enumerate(
            zip(source_vector, scaled_vector)):
        source_coefficient = builder.canonical_fraction(
            source_value, f"source coefficient {i}")
        scaled_coefficient = builder.canonical_fraction(
            scaled_value, f"scaled coefficient {i}")
        require(scaled_coefficient.denominator == 1 and
                scaled_coefficient == lcm * source_coefficient,
                f"scaled coefficient {i} does not equal L times source")
        integers.append(abs(scaled_coefficient.numerator))
    content = 0
    for value in integers:
        content = gcd(content, value)
    require(content == 1, "scaled integer vector is not primitive")
    return lcm.numerator


def validate_stage(path, expected_sha, expected_multiplier_sha):
    data, raw = builder.read_pinned(path, expected_sha, "transfer I stage")
    require(isinstance(raw, dict) and set(raw) == STAGE_KEYS and
            raw.get("status") == "multiprecision-quadratic-transfer-I-stage" and
            raw.get("rigorous") is False and raw.get("complete") is True,
            "wrong transfer I-stage status")
    require(type(raw.get("decimal_dps")) is int and raw["decimal_dps"] == 100 and
            raw.get("input_sha256") == SCALED_INPUT_SHA and
            raw.get("multiplier_sha256") == expected_multiplier_sha and
            raw.get("parameters") == builder.PARAMETERS and
            raw.get("dependency_hashes") == TRANSFER_DEPENDENCIES,
            "transfer I-stage provenance changed")
    require(type(raw.get("i_orbit_groups")) is int and
            raw["i_orbit_groups"] == 1575 and
            type(raw.get("i_faces")) is int and raw["i_faces"] == 312,
            "transfer I-stage counts changed")
    i_by_r = raw.get("i_by_r")
    require(isinstance(i_by_r, list) and len(i_by_r) == 16,
            "transfer I-stage stratum list changed")
    with localcontext() as context:
        context.prec = 100
        values = [exact_decimal(x, f"stage I[{i}]")
                  for i, x in enumerate(i_by_r)]
        denominator = sum(values, Decimal(0))
        require(denominator == exact_decimal(
            raw.get("denominator"), "stage denominator"),
            "transfer I-stage denominator sum failed")
    stage_seconds = raw.get("i_seconds")
    require(not isinstance(stage_seconds, bool) and
            isinstance(stage_seconds, (int, float)) and
            math.isfinite(float(stage_seconds)) and stage_seconds >= 0,
            "transfer I-stage runtime is malformed")
    return data, raw


def validate_transfer(raw, expected_multiplier_sha, stage_path,
                      stage_sha, prefix):
    require(isinstance(raw, dict) and set(raw) == TRANSFER_KEYS and
            raw.get("status") == "multiprecision-transferred-quadratic-candidate" and
            raw.get("rigorous") is False and raw.get("complete") is True and
            raw.get("theorem_ready") is False,
            f"wrong {prefix} transfer status")
    require(type(raw.get("decimal_dps")) is int and raw["decimal_dps"] == 100 and
            raw.get("input_sha256") == SCALED_INPUT_SHA and
            raw.get("multiplier_sha256") == expected_multiplier_sha and
            raw.get("parameters") == builder.PARAMETERS and
            raw.get("dependency_hashes") == TRANSFER_DEPENDENCIES,
            f"{prefix} transfer provenance changed")
    require(type(raw.get("fixed_basis_dimension")) is int and
            raw["fixed_basis_dimension"] == 272 and
            type(raw.get("multiplier_dimension")) is int and
            raw["multiplier_dimension"] == 96 and
            type(raw.get("i_orbit_groups")) is int and
            raw["i_orbit_groups"] == 1575 and
            type(raw.get("i_faces")) is int and raw["i_faces"] == 312 and
            type(raw.get("marginal_components")) is int and
            raw["marginal_components"] == 695 and
            type(raw.get("j_branch_domains")) is int and
            raw["j_branch_domains"] == 1200,
            f"{prefix} transfer counts changed")
    gates = raw.get("gates")
    require(isinstance(gates, dict) and set(gates) == TRANSFER_GATES and
            all(value is True for value in gates.values()) and
            raw.get("gates_passed") is True,
            f"{prefix} transfer gates failed or changed")
    require(Path(raw.get("i_stage_json", "")).resolve() ==
            Path(stage_path).resolve() and
            raw.get("i_stage_sha256") == stage_sha,
            f"{prefix} transfer stage binding changed")
    _, stage = validate_stage(stage_path, stage_sha, expected_multiplier_sha)
    i_by_r = raw.get("i_by_r")
    j_by_r = raw.get("j_by_common_r")
    require(i_by_r == stage["i_by_r"] and isinstance(j_by_r, list) and
            len(i_by_r) == len(j_by_r) == 16,
            f"{prefix} transfer stratum arrays changed")
    denominator, numerator = replay_decimal_payload(raw, prefix)
    with localcontext() as context:
        context.prec = 100
        i_values = [exact_decimal(x, f"{prefix} I[{i}]")
                    for i, x in enumerate(i_by_r)]
        j_values = [exact_decimal(x, f"{prefix} J[{i}]")
                    for i, x in enumerate(j_by_r)]
        require(sum(i_values, Decimal(0)) == denominator,
                f"{prefix} I-stratum sum failed")
        require(Decimal(48) * sum(j_values, Decimal(0)) == numerator,
                f"{prefix} factor-48 J-stratum sum failed")
    require(raw.get("margin_positive") is (numerator > denominator),
            f"{prefix} sign boolean disagrees")
    for name in ("i_seconds", "j_seconds", "total_seconds", "peak_rss_kib"):
        value = raw.get(name)
        require(not isinstance(value, bool) and isinstance(value, (int, float)) and
                math.isfinite(float(value)) and value >= 0,
                f"{prefix} {name} is not finite nonnegative numeric metadata")
    return Fraction(denominator), Fraction(numerator)


def validate_h_multiplier(raw):
    require(isinstance(raw, dict) and set(raw) == H_MULTIPLIER_KEYS and
            raw.get("status") == "exact-stratum-quadratic-rational-vector" and
            raw.get("construction") == "H=Q+s*1 exact D4 span contingency" and
            raw.get("rigorous_forms") is True and
            raw.get("block_direct_bitwise_equal") is True and
            raw.get("theorem_ready") is False and
            raw.get("source_multiplier_sha256") == Q_MULTIPLIER_SHA and
            raw.get("input_sha256") == builder.INPUT_SHA and
            raw.get("script_sha256") == BUILDER_SHA,
            "H multiplier provenance/gates changed")
    s = builder.canonical_fraction(raw.get("constant_scale_s"), "H scale s")
    require(s != 0, "H scale s cannot vanish")
    _, source_raw = builder.read_pinned(
        builder.EI / "results" /
        "c10_stratum_quadratic_cappedopt_D4_exact.json",
        Q_MULTIPLIER_SHA, "Q multiplier")
    parsed = builder.parse_source(source_raw)
    reconstructed = builder.reconstruct(parsed, s)
    expected = reconstructed["h"]
    vector_raw = raw.get("rational_vector")
    require(isinstance(vector_raw, list) and len(vector_raw) == 96,
            "H multiplier vector dimension changed")
    vector = tuple(builder.canonical_fraction(x, f"H coordinate {i}")
                   for i, x in enumerate(vector_raw))
    require(vector == expected, "H multiplier is not exactly Q+s*1")
    gates = raw.get("exact_gates")
    require(isinstance(gates, dict) and set(gates) == {
                "source_q_forms_reconstructed", "block_sparse_bitwise_equal",
                "polarization_identity_exact", "fresh_direct_bitwise_equal",
                "direct_counts_complete", "denominator_positive"} and
            all(value is True for value in gates.values()),
            "H exact D4 gates did not all pass")
    require(type(raw.get("k")) is int and raw["k"] == 48 and
            raw.get("parameters") == builder.PARAMETERS and
            type(raw.get("fixed_basis_dimension")) is int and
            raw["fixed_basis_dimension"] == 12 and
            type(raw.get("quadratic_basis_dimension")) is int and
            raw["quadratic_basis_dimension"] == 96 and
            type(raw.get("discovery_basis_dimension")) is int and
            raw["discovery_basis_dimension"] == 93 and
            raw.get("channel_powers") == [list(x) for x in builder.CHANNEL_POWERS] and
            raw.get("quadratic_labels") == [[r, channel] for r in range(16)
                                               for channel in builder.CHANNELS] and
            raw.get("active_quadratic_labels") == [
                [r, channel] for r in range(16) for channel in builder.CHANNELS
                if (r, channel) not in builder.NULL_LABELS] and
            raw.get("discarded_gram_dependent_labels") ==
                [list(x) for x in builder.NULL_LABELS],
            "H multiplier basis metadata changed")
    expected_dependencies = {name: expected_sha for name, (_path, expected_sha)
                             in builder.DEPENDENCIES.items()}
    require(raw.get("dependency_hashes") == expected_dependencies,
            "H multiplier arithmetic dependencies changed")
    exact_fields = {
        "base_denominator": reconstructed["base_forms"][0],
        "base_numerator": reconstructed["base_forms"][1],
        "q_denominator": reconstructed["q_forms"][0],
        "q_numerator": reconstructed["q_forms"][1],
        "base_q_i_cross": reconstructed["cross_forms"][0],
        "base_q_n_cross": reconstructed["cross_forms"][1],
        "denominator": reconstructed["h_forms"][0],
        "numerator": reconstructed["h_forms"][1],
        "quotient": reconstructed["h_forms"][1] / reconstructed["h_forms"][0],
        "margin": reconstructed["h_forms"][1] - reconstructed["h_forms"][0],
    }
    for name, expected_value in exact_fields.items():
        require(builder.canonical_fraction(raw.get(name), f"H {name}") ==
                expected_value, f"H {name} does not reconstruct")
    require(raw.get("denominator_positive") is
                (reconstructed["h_forms"][0] > 0) and
            raw.get("margin_positive") is
                (reconstructed["h_forms"][1] > reconstructed["h_forms"][0]) and
            type(raw.get("i_orbit_groups")) is int and
            raw["i_orbit_groups"] == 20 and
            type(raw.get("i_faces")) is int and raw["i_faces"] == 312 and
            type(raw.get("marginal_components")) is int and
            raw["marginal_components"] == 19 and
            type(raw.get("j_branch_domains")) is int and
            raw["j_branch_domains"] == 1200 and
            type(raw.get("direct_i_faces")) is int and
            raw["direct_i_faces"] == 312 and
            type(raw.get("direct_j_branch_domains")) is int and
            raw["direct_j_branch_domains"] == 1200,
            "H form signs/counts changed")
    direct_seconds = raw.get("direct_seconds")
    require(not isinstance(direct_seconds, bool) and
            isinstance(direct_seconds, (int, float)) and
            math.isfinite(float(direct_seconds)) and direct_seconds >= 0,
            "H direct runtime is malformed")
    require(raw.get("d4_span_stationary") ==
            builder.d4_span_stationary(reconstructed),
            "H D4 stationary analysis changed")
    return s


def solve_pencil(d0, n0, d1, n1, dc, nc, precision=180):
    require(all(isinstance(x, Fraction) for x in
                (d0, n0, d1, n1, dc, nc)), "pencil forms must be Fractions")
    require(d0 > 0 and d1 > 0 and d0 * d1 - dc * dc > 0,
            "realized denominator pencil is not positive definite")
    coefficients = (nc * d0 - n0 * dc,
                    n1 * d0 - n0 * d1,
                    n1 * dc - nc * d1)
    with localcontext() as context:
        context.prec = precision

        def dec(value):
            return Decimal(value.numerator) / Decimal(value.denominator)

        a, b, c = (dec(x) for x in coefficients)
        roots = []
        if c != 0:
            discriminant = b * b - 4 * a * c
            require(discriminant >= 0, "stationary polynomial has no real roots")
            square = discriminant.sqrt()
            roots = [(-b + square) / (2 * c),
                     (-b - square) / (2 * c)]
        elif b != 0:
            roots = [-a / b]
        elif a != 0:
            raise ValueError("constant nonzero stationary polynomial")
        ranked = []
        for root in roots:
            denominator = dec(d0) + 2 * root * dec(dc) + root * root * dec(d1)
            require(denominator > 0, "finite stationary denominator is nonpositive")
            numerator = dec(n0) + 2 * root * dec(nc) + root * root * dec(n1)
            quotient = numerator / denominator
            require(quotient.is_finite(), "finite stationary quotient overflowed")
            ranked.append({"point": "finite", "t": str(root),
                           "denominator": str(denominator),
                           "quotient": str(quotient)})
        infinity = dec(n1) / dec(d1)
        require(infinity.is_finite(), "infinity quotient is nonfinite")
        ranked.append({"point": "infinity", "denominator": str(dec(d1)),
                       "quotient": str(infinity)})
        ranked.sort(key=lambda item: Decimal(item["quotient"]), reverse=True)
    return {
        "stationary_coefficients_ascending": [str(x) for x in coefficients],
        "decimal_precision": precision,
        "ranked_projective_points": ranked,
        "maximum": ranked[0],
    }


def reconstruct_span(base_forms, q_forms, h_forms, s):
    d0, n0 = base_forms
    d1, n1 = q_forms
    dh, nh = h_forms
    require(s != 0, "polarization scale s cannot be zero")
    dc = (dh - d1 - s * s * d0) / (2 * s)
    nc = (nh - n1 - s * s * n0) / (2 * s)
    solution = solve_pencil(d0, n0, d1, n1, dc, nc)
    return (dc, nc), solution


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-output", required=True)
    parser.add_argument("--expect-base-sha256", required=True)
    parser.add_argument("--original-input", required=True)
    parser.add_argument("--expect-original-input-sha256", required=True)
    parser.add_argument("--scaled-input", required=True)
    parser.add_argument("--expect-scaled-input-sha256", required=True)
    parser.add_argument("--q-output", required=True)
    parser.add_argument("--expect-q-output-sha256", required=True)
    parser.add_argument("--q-stage", required=True)
    parser.add_argument("--expect-q-stage-sha256", required=True)
    parser.add_argument("--h-multiplier", required=True)
    parser.add_argument("--expect-h-multiplier-sha256", required=True)
    parser.add_argument("--h-output", required=True)
    parser.add_argument("--expect-h-output-sha256", required=True)
    parser.add_argument("--h-stage", required=True)
    parser.add_argument("--expect-h-stage-sha256", required=True)
    parser.add_argument("--allow-heuristic-rescaled-base", action="store_true")
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    require(args.expect_base_sha256 == BASE_OUTPUT_SHA and
            args.expect_original_input_sha256 == ORIGINAL_INPUT_SHA and
            args.expect_scaled_input_sha256 == SCALED_INPUT_SHA,
            "caller did not pin the frozen base/input bytes")
    require(args.allow_heuristic_rescaled_base,
            "no fresh SHA8650 base exists; explicit heuristic opt-in required")
    consumer_start = builder.file_sha(__file__)
    all_paths = [Path(value).resolve() for value in (
        args.base_output, args.original_input, args.scaled_input,
        args.q_output, args.q_stage, args.h_multiplier, args.h_output,
        args.h_stage, args.output, __file__)]
    require(len(set(all_paths)) == len(all_paths),
            "every input/stage/output/driver path must be distinct")

    inputs = {}
    for name, path, expected in (
        ("base", args.base_output, BASE_OUTPUT_SHA),
        ("original", args.original_input, ORIGINAL_INPUT_SHA),
        ("scaled", args.scaled_input, SCALED_INPUT_SHA),
        ("q", args.q_output, args.expect_q_output_sha256),
        ("h_multiplier", args.h_multiplier,
         args.expect_h_multiplier_sha256),
        ("h", args.h_output, args.expect_h_output_sha256),
    ):
        data, raw = builder.read_pinned(path, expected, name)
        inputs[name] = (data, raw, expected, path)
    base_unscaled = validate_base(inputs["base"][1])
    lcm = validate_scaled_input(inputs["scaled"][1], inputs["original"][1])
    base_scaled = tuple(value * lcm * lcm for value in base_unscaled)
    q_forms = validate_transfer(
        inputs["q"][1], Q_MULTIPLIER_SHA, args.q_stage,
        args.expect_q_stage_sha256, "Q")
    s = validate_h_multiplier(inputs["h_multiplier"][1])
    h_forms = validate_transfer(
        inputs["h"][1], args.expect_h_multiplier_sha256, args.h_stage,
        args.expect_h_stage_sha256, "H")
    cross, solution = reconstruct_span(base_scaled, q_forms, h_forms, s)
    output = {
        "status": "heuristic-Decimal100-Q-constant-span-reconstruction",
        "complete": True,
        "rigorous": False,
        "theorem_ready": False,
        "heuristic_decimal_cross_reconstruction": True,
        "base_rescaling_warning": (
            "D00,N00 come from SHA719c Decimal100 strings multiplied by the "
            "exact SHA8650 coefficient LCM squared.  This is mathematically "
            "homogeneous but not a byte-identical fresh SHA8650 Decimal100 "
            "traversal; no rigorous error bound is attached."),
        "k": 48,
        "parameters": builder.PARAMETERS,
        "pencil_gauge": "1+t*Q",
        "polarization_input_gauge": "H=Q+s*1",
        "constant_scale_s": str(s),
        "consumer_sha256": consumer_start,
        "multiplier_builder_sha256": BUILDER_SHA,
        "input_hashes": {name: expected for name, (_data, _raw, expected, _path)
                         in inputs.items()},
        "q_stage_sha256": args.expect_q_stage_sha256,
        "h_stage_sha256": args.expect_h_stage_sha256,
        "integer_coefficient_lcm": str(lcm),
        "base_unscaled_denominator": str(base_unscaled[0]),
        "base_unscaled_numerator": str(base_unscaled[1]),
        "base_scaled_denominator": str(base_scaled[0]),
        "base_scaled_numerator": str(base_scaled[1]),
        "q_denominator": str(q_forms[0]),
        "q_numerator": str(q_forms[1]),
        "h_denominator": str(h_forms[0]),
        "h_numerator": str(h_forms[1]),
        "polarized_i_cross": str(cross[0]),
        "polarized_n_cross": str(cross[1]),
        "denominator_gram_determinant": str(
            base_scaled[0] * q_forms[0] - cross[0] * cross[0]),
        "solution": solution,
        "decision_note": (
            "This ranks serialized discovery forms only.  Any selected exact "
            "rational t must be evaluated afresh as (1+tQ)F by an exact or "
            "outward-rounded checker."),
    }
    # All producer bytes and both stages must remain unchanged through solve.
    for name, (data, _raw, expected, path) in inputs.items():
        require(hashlib.sha256(Path(path).read_bytes()).hexdigest() == expected and
                hashlib.sha256(data).hexdigest() == expected,
                f"{name} input mutated during solve")
    require(builder.file_sha(args.q_stage) == args.expect_q_stage_sha256 and
            builder.file_sha(args.h_stage) == args.expect_h_stage_sha256,
            "transfer stage mutated during solve")
    require(builder.file_sha(builder.__file__) == BUILDER_SHA,
            "pinned multiplier builder changed")
    require(builder.file_sha(__file__) == consumer_start,
            "span consumer changed during solve")
    data = builder.canonical_bytes(output)
    fd, identity = builder.reserve_output(args.output)
    published = False
    try:
        builder.publish_reserved(fd, args.output, identity, data)
        published = True
    finally:
        os.close(fd)
        if not published and builder.owned_path(args.output, identity):
            os.unlink(args.output)
    print(json.dumps({
        "output": args.output,
        "output_sha256": hashlib.sha256(data).hexdigest(),
        "maximum": solution["maximum"],
        "heuristic_decimal_cross_reconstruction": True,
        "theorem_ready": False,
    }, indent=2))


if __name__ == "__main__":
    main()
