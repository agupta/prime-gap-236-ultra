#!/usr/bin/env python3
"""V6.5: recover weighted m0 before accepting a returned J z value.

Frozen v6.4 could not distinguish exact cancellation from underflow because
its guard inspected only the already-squared ``point.z``.  This successor
recomputes the weighted base marginal from the returned unit marginals before
squaring and authenticates the returned z at its own local ULP scale.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import importance_d4_calibration_v64 as v64


HERE = Path(__file__).resolve()
REPO_ROOT = HERE.parents[3]
DRIVER_RELATIVE = \
    "agents/structural-basis/code/importance_d4_calibration_v65.py"
V64_GATE_RELATIVE = \
    "agents/structural-basis/results/importance_d4_calibration_gate_v64.json"
V64_GATE_SHA256 = \
    "6fac38311cb0914761c15f8bbab6abca839bf622ab60418df2e9cde7eeb0c8ad"
FROZEN_V64_EXPECTED_CONVENTIONS = v64.expected_conventions
FROZEN_V64_VALIDATE_CHAIN_RECORD = v64.validate_chain_record
FROZEN_V64_J_ENVELOPE_POINT = v64.j_envelope_point

V64_FAILURE_ARTIFACT_HASHES = {
    "agents/audit/IMPORTANCE-D4-CALIBRATION-V64-PRELAUNCH-AUDIT.md":
        "aea310d56b7aa7e8f63cc14db12e474aad270f7ee9b04869b240351dc8512ceb",
    "agents/audit/verify_importance_d4_calibration_v64.py":
        "fd3370ae784a04b35f8846512de6db14c456049cb77a1ccd47f447e9eb166714",
    "agents/audit/test_importance_d4_calibration_v64_presquare.py":
        "3e387aca92ac30f14dff5f88d5c9de67f17d645e5776fbb0aa55def64890c517",
}

ADDITIONAL_SOURCE_PATHS = (
    DRIVER_RELATIVE,
    "agents/structural-basis/code/build_importance_d4_calibration_gate_v65.py",
    "agents/structural-basis/tests/test_importance_d4_calibration_v65.py",
    "agents/structural-basis/IMPORTANCE-D4-CALIBRATION-V65-SPEC.md",
    *V64_FAILURE_ARTIFACT_HASHES,
)
REQUIRED_SOURCE_PATHS = tuple(dict.fromkeys(
    tuple(v64.REQUIRED_SOURCE_PATHS) + ADDITIONAL_SOURCE_PATHS))
REQUIRED_DATA_PATHS = tuple(v64.REQUIRED_DATA_PATHS) + (V64_GATE_RELATIVE,)


def validate_v64_failure_artifacts():
    for relative, expected in V64_FAILURE_ARTIFACT_HASHES.items():
        if v64.v63.v62.v61.v6.v5.sha256_file(REPO_ROOT / relative) != expected:
            raise ValueError(f"frozen v6.4 failure artifact changed: {relative}")
    return True


def expected_conventions():
    answer = FROZEN_V64_EXPECTED_CONVENTIONS()
    answer.update({
        "j_z_weighted_m0_recomputed_before_square": True,
        "j_z_tagged_product_underflow_rejected": True,
        "j_z_return_value_authenticated_at_local_ulp_scale": True,
        "invalid_prelaunch_v64_gate_sha256": V64_GATE_SHA256,
    })
    return answer


def load_and_validate_gate(path):
    validate_v64_failure_artifacts()
    snapshot = v64.v63.v62.v61.v6.v5.read_file_snapshot(path)
    gate = v64.v63.v62.v61.v6.v5.strict_json_bytes(
        snapshot["data"], "v6.5 calibration gate")
    v64.v63.v62.v61.v6.v5._exact_keys(gate, {
        "status", "rigorous", "production_launch_authorized",
        "supersedes_invalid_gate_sha256", "float_encoding", "source_hashes",
        "data_hashes", "schedule", "thresholds", "conventions",
        "extension_rule", "continuation_rule"}, "v6.5 calibration gate")
    if (gate["status"] !=
            "frozen-d4-exact-whitened-calibration-prelaunch-v6.5" or
            gate["rigorous"] is not False or
            gate["production_launch_authorized"] is not False or
            gate["supersedes_invalid_gate_sha256"] != V64_GATE_SHA256 or
            gate["float_encoding"] != v64.v63.v62.v61.v6.v5.FLOAT_ENCODING or
            gate["schedule"] != v64.v63.v62.v61.v6.v5.expected_schedule() or
            gate["thresholds"] !=
            v64.v63.v62.v61.v6.v5.expected_thresholds() or
            gate["conventions"] != expected_conventions() or
            gate["extension_rule"] !=
            v64.v63.v62.v61.v6.expected_extension_rule() or
            gate["continuation_rule"] !=
            v64.v63.v62.v61.v6.expected_continuation_rule()):
        raise ValueError("v6.5 gate status, schedule, or conventions changed")
    for field, expected_paths in (
            ("source_hashes", REQUIRED_SOURCE_PATHS),
            ("data_hashes", REQUIRED_DATA_PATHS)):
        table = gate[field]
        if not isinstance(table, dict) or set(table) != set(expected_paths):
            raise ValueError(f"v6.5 {field} has missing or extra paths")
        for relative, expected in table.items():
            if (not isinstance(expected, str) or len(expected) != 64 or
                    any(character not in "0123456789abcdef"
                        for character in expected) or
                    v64.v63.v62.v61.v6.v5.sha256_file(REPO_ROOT / relative) !=
                    expected):
                raise ValueError(f"v6.5 dependency mismatch: {relative}")
    if gate["data_hashes"].get(V64_GATE_RELATIVE) != V64_GATE_SHA256:
        raise ValueError("v6.5 gate does not bind invalid v6.4 bytes")
    for relative, expected in V64_FAILURE_ARTIFACT_HASHES.items():
        if gate["source_hashes"].get(relative) != expected:
            raise ValueError("v6.5 gate does not bind frozen v6.4 failure")
    return {**v64.v63.v62.v61.v6.v5.public_binding(snapshot), "gate": gate}


def _weighted_m0_and_square(adapter, point):
    unit = getattr(point, "unit_marginals", None)
    weights = getattr(adapter, "base_constant_weights", None)
    dimension = getattr(adapter, "dimension", None)
    strata = getattr(adapter, "strata", None)
    if (not isinstance(unit, tuple) or not isinstance(weights, tuple) or
            isinstance(dimension, bool) or dimension != 96 or
            len(unit) != dimension or len(weights) != dimension or
            tuple(strata) != tuple(range(16)) or
            not all(math.isfinite(value) for value in unit + weights)):
        raise ArithmeticError("v6.5 weighted-m0 inputs are malformed")
    terms = []
    for r in strata:
        weight, value = weights[6 * r], unit[6 * r]
        term = weight * value
        if weight != 0 and value != 0 and (
                term == 0 or 0 < abs(term) < sys.float_info.min):
            raise ArithmeticError("tagged weighted-m0 product is unresolved")
        terms.append(term)
    weighted = math.fsum(terms)
    if not math.isfinite(weighted):
        raise ArithmeticError("weighted m0 is nonfinite")
    square = weighted * weighted
    if weighted != 0 and (square == 0 or square < sys.float_info.min):
        raise ArithmeticError("nonzero weighted m0 has unresolved square")
    return weighted, square


def j_envelope_point(adapter, common):
    point = FROZEN_V64_J_ENVELOPE_POINT(adapter, common)
    if point is None:
        return None
    _, square = _weighted_m0_and_square(adapter, point)
    recorded = point.z
    if not math.isfinite(recorded) or recorded < 0:
        raise ArithmeticError("returned J z is negative or nonfinite")
    if (recorded == 0) != (square == 0):
        raise ArithmeticError("returned J z lost weighted-m0 support")
    tolerance = 16 * max(math.ulp(recorded), math.ulp(square))
    if abs(recorded - square) > tolerance:
        raise ArithmeticError("returned J z differs from recomputed square")
    return point


def j_envelope_log_density(adapter, common):
    point = j_envelope_point(adapter, common)
    return -math.inf if point is None else point.log_g


def validate_chain_record(record, chain_spec, schedule, *, adapter=None):
    FROZEN_V64_VALIDATE_CHAIN_RECORD(
        record, chain_spec, schedule, adapter=adapter)
    return True


def install_runtime():
    v64.v63.v62.v61.v6.DRIVER_RELATIVE = DRIVER_RELATIVE
    v64.v63.v62.v61.v6.REQUIRED_SOURCE_PATHS = REQUIRED_SOURCE_PATHS
    v64.v63.v62.v61.v6.REQUIRED_DATA_PATHS = REQUIRED_DATA_PATHS
    v64.v63.v62.v61.v6.expected_conventions = expected_conventions
    v64.v63.v62.v61.v6.load_and_validate_gate = load_and_validate_gate
    v64.v63.v62.v61.v6.validate_chain_record = validate_chain_record
    v64.v63.v62.v61.v6.j_envelope_point = j_envelope_point
    v64.v63.v62.v61.v6.j_envelope_log_density = j_envelope_log_density


def main():
    install_runtime()
    return v64.v63.v62.v61.v6.main()


if __name__ == "__main__":
    main()
