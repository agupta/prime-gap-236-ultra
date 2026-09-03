#!/usr/bin/env python3
"""Fail-closed Decimal100 reconstruction of one sparse coordinate line."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from decimal import Decimal, localcontext
from fractions import Fraction
from pathlib import Path


HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[1]
MANIFEST_STATUS = "c10-D12-19-coordinate-sparse-self-form-manifest"
GENERATOR_SHA = "82ee455d319b770c114428fe98dfc5b76d0dd7ca1d3c095729c60ac2c23fb344"
GROUPED_SHA = "47167e92a0f346e969706dc282ccb2dfd4ac31a0a75b654938ffbe8423cf4a4a"
INTEGRATOR_SHA = "941ee82bc72fd8488a95eb5e536fe47f8c95d39a1b618dae7d6ef7eb27122e52"
LINE_CORE_SHA = "f2462e9688bf0f426856ff81f7354476a762e1617c1fd8c81b7b67a17098b797"
LINE_CORE = HERE/"recover_h6_scalar_line.py"


def require(ok, message):
    if not ok:
        raise ValueError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def strict_json(raw, description):
    def pairs(items):
        answer = {}
        for key, value in items:
            require(type(key) is str and key not in answer,
                    f"{description}: duplicate/non-string key")
            answer[key] = value
        return answer
    return json.loads(raw, object_pairs_hook=pairs,
                      parse_constant=lambda x: (_ for _ in ()).throw(
                          ValueError(f"{description}: nonfinite {x}")))


def load(path_text, expected, description):
    require(type(expected) is str and len(expected) == 64 and
            all(x in "0123456789abcdef" for x in expected),
            f"{description}: expected SHA")
    path = Path(path_text).resolve(); raw = path.read_bytes()
    require(len(raw) <= 20_000_000 and sha(raw) == expected,
            f"{description}: size/SHA")
    return path, raw, strict_json(raw, description)


def fraction(value, description):
    require(type(value) is str and value and value == value.strip(),
            f"{description}: rational string")
    try:
        return Fraction(value)
    except Exception as exc:
        raise ValueError(f"{description}: malformed rational") from exc


def load_line_core():
    raw = LINE_CORE.read_bytes()
    require(sha(raw) == LINE_CORE_SHA, "line algebra core SHA")
    spec = importlib.util.spec_from_file_location("sparse_line_core", LINE_CORE)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return raw, module


def decimal_replay(result):
    values = {}
    for key in ("denominator", "j_value", "numerator", "quotient", "margin"):
        text = result.get(key)
        require(type(text) is str and text and text == text.strip(),
                f"result {key} string")
        try:
            values[key] = Decimal(text)
        except Exception as exc:
            raise ValueError(f"result {key} Decimal") from exc
        require(values[key].is_finite(), f"result {key} finite")
    with localcontext() as context:
        context.prec = 100
        numerator = Decimal(48)*values["j_value"]
        quotient = values["numerator"]/values["denominator"]
        margin = values["numerator"]-values["denominator"]
    require(values["denominator"] > 0 and values["numerator"] == numerator and
            values["quotient"] == quotient and values["margin"] == margin,
            "result Decimal100 operation replay/factor48")
    return Fraction(result["denominator"]), Fraction(result["numerator"])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--expect-manifest-sha256", required=True)
    parser.add_argument("--direction", required=True)
    parser.add_argument("--expect-direction-sha256", required=True)
    parser.add_argument("--i-stage", required=True)
    parser.add_argument("--expect-i-stage-sha256", required=True)
    parser.add_argument("--self-result", required=True)
    parser.add_argument("--expect-self-result-sha256", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    paths = {}; trusted = {}
    for name, path, expected in (
            ("manifest", args.manifest, args.expect_manifest_sha256),
            ("direction", args.direction, args.expect_direction_sha256),
            ("I stage", args.i_stage, args.expect_i_stage_sha256),
            ("self result", args.self_result, args.expect_self_result_sha256)):
        p, raw, value = load(path, expected, name)
        require(p not in trusted, "trusted path alias")
        paths[name], trusted[p] = value, raw
    line_raw, line_core = load_line_core(); trusted[LINE_CORE.resolve()] = line_raw
    self_path = Path(__file__).resolve(); trusted[self_path] = self_path.read_bytes()

    manifest = paths["manifest"]
    require(manifest.get("status") == MANIFEST_STATUS and
            manifest.get("rigorous") is False and
            manifest.get("theorem_ready") is False and
            manifest.get("no_self_form_values_claimed") is True and
            manifest.get("k") == 48 and manifest.get("degree") == 12 and
            manifest.get("coordinates_included") == list(range(19)),
            "full manifest schema")
    provenance = manifest.get("provenance", {})
    require(provenance.get("generator_sha256") == GENERATOR_SHA and
            provenance.get("grouped_evaluator_sha256") == GROUPED_SHA and
            provenance.get("exact_integrator_sha256") == INTEGRATOR_SHA,
            "manifest arithmetic closure")
    matches = [x for x in manifest.get("full_ranking", [])
               if type(x) is dict and
               x.get("sha256") == args.expect_direction_sha256]
    require(len(matches) == 1, "manifest direction binding")
    entry = matches[0]; expected_counts = entry.get("expected_grouped_counts")
    require(type(expected_counts) is dict and
            set(expected_counts) == {"direction_labels", "precomputed_orbit_keys",
                "precomputed_orbit_terms", "i_orbit_groups",
                "i_grouped_residual_terms", "i_faces", "marginal_components",
                "distinct_marginal_orbits", "j_branch_integrals"},
            "manifest count schema")

    direction = paths["direction"]
    require(direction.get("status") ==
            "c10-D12-sparse-coordinate-self-form-direction" and
            direction.get("rigorous") is False and
            direction.get("theorem_ready") is False and
            direction.get("fresh_scalar_reevaluation_required") is True and
            direction.get("finite_form_value_claimed") is False and
            direction.get("k") == 48 and direction.get("degree") == 12 and
            direction.get("coordinate") == entry.get("coordinate") and
            direction.get("coordinate_name") == entry.get("name") and
            direction.get("orientation") == entry.get("orientation") and
            direction.get("basis_dimension") == entry.get("basis_dimension") and
            len(direction.get("basis", [])) == entry.get("basis_dimension") and
            len(direction.get("rational_vector", [])) == entry.get("basis_dimension") and
            direction.get("expected_grouped_counts") == expected_counts and
            direction.get("provenance") == provenance,
            "direction identity/schema")
    action = direction.get("cross_action", {})
    D0, N0, a01, b01 = [fraction(action.get(key), key) for key in
                         ("denominator_D0", "numerator_N0", "A_cross_a01",
                          "B48_cross_b01")]
    R = fraction(action.get("ascent_residual_R"), "R")
    require(D0 > N0 > 0 and R == D0*b01-N0*a01 > 0 and
            fraction(action.get("quotient_first_derivative"), "derivative") ==
            2*R/D0**2, "direction cross-action identities")

    stage = paths["I stage"]
    require(stage.get("status") == "grouped-fixed-vector-I-stage" and
            stage.get("i_complete") is True and stage.get("rigorous") is False and
            stage.get("decimal_dps") == 100 and
            stage.get("input_sha256") == args.expect_direction_sha256 and
            stage.get("script_sha256") == GROUPED_SHA and
            stage.get("integrator_sha256") == INTEGRATOR_SHA and
            stage.get("i_orbit_groups") == expected_counts["i_orbit_groups"] and
            stage.get("i_faces") == expected_counts["i_faces"] and
            stage.get("denominator_positive") is True,
            "I-stage provenance/counts")
    line_core.validate_parameters(stage.get("parameters"), "I-stage parameters")
    stage_D = fraction(stage.get("denominator"), "stage denominator")

    result = paths["self result"]
    require(result.get("status") == "multiprecision-grouped-fixed-vector-discovery" and
            result.get("rigorous") is False and result.get("decimal_dps") == 100 and
            result.get("k") == 48 and type(result.get("workers")) is int and
            1 <= result.get("workers") <= 2 and
            result.get("basis_dimension") == entry["basis_dimension"] and
            result.get("input_sha256") == args.expect_direction_sha256 and
            result.get("script_sha256") == GROUPED_SHA and
            result.get("integrator_sha256") == INTEGRATOR_SHA and
            result.get("i_orbit_groups") == expected_counts["i_orbit_groups"] and
            result.get("i_faces") == expected_counts["i_faces"] and
            result.get("marginal_components") == expected_counts["marginal_components"] and
            result.get("j_branch_integrals") == expected_counts["j_branch_integrals"] and
            result.get("denominator_positive") is True,
            "self-result provenance/counts")
    line_core.validate_parameters(result.get("parameters"), "result parameters")
    A11, B11 = decimal_replay(result)
    require(A11 == stage_D, "I stage/result denominator mismatch")
    line = line_core.line_reconstruction(D0, N0, a01, b01, A11, B11)
    output = {
        "status": "c10-D12-sparse-coordinate-line-reconstruction-discovery",
        "rigorous": False, "theorem_ready": False,
        "coordinate": entry["coordinate"], "coordinate_name": entry["name"],
        "direction_sha256": args.expect_direction_sha256,
        "i_stage_sha256": args.expect_i_stage_sha256,
        "self_result_sha256": args.expect_self_result_sha256,
        "manifest_sha256": args.expect_manifest_sha256,
        **line,
    }
    line_core.publish(args.output, output, trusted)


if __name__ == "__main__":
    main()
