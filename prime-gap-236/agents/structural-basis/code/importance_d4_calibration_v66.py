#!/usr/bin/env python3
"""V6.6: fail closed on every nonfinite J-z reconstruction quantity.

Frozen v6.5 checked a derived square only for underflow.  A finite forged
weighted marginal could therefore overflow to infinity, make both the
comparison discrepancy and tolerance infinite, and pass ``inf > inf``.
This immutable successor validates the normalized marginal invariant and
checks every product, sum, pre-square overflow condition, square, returned z,
tolerance, and discrepancy before making an ordering comparison.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import importance_d4_calibration_v65 as v65


HERE = Path(__file__).resolve()
REPO_ROOT = HERE.parents[3]
DRIVER_RELATIVE = \
    "agents/structural-basis/code/importance_d4_calibration_v66.py"
V65_GATE_RELATIVE = \
    "agents/structural-basis/results/importance_d4_calibration_gate_v65.json"
V65_GATE_SHA256 = \
    "5aec092841721a8e54292eb631e43c5e298088960e4031e7528df6272def905a"
FROZEN_V65_EXPECTED_CONVENTIONS = v65.expected_conventions
FROZEN_V65_VALIDATE_CHAIN_RECORD = v65.validate_chain_record
FROZEN_V65_J_ENVELOPE_POINT = v65.j_envelope_point

V65_FAILURE_ARTIFACT_HASHES = {
    "agents/audit/IMPORTANCE-D4-CALIBRATION-V65-PRELAUNCH-AUDIT.md":
        "6dc014424f5a551b46d086cd8305a535cf905a0f36696fd398866b8d57bb3a80",
    "agents/audit/verify_importance_d4_calibration_v65.py":
        "5ca07de73cc4f10cabe9cc2d3e61c2c1b7bc0f2088041ba4301ebf834c7d0b7b",
    "agents/audit/test_importance_d4_calibration_v65_square_overflow.py":
        "f400f250b6485a4d77f02a346eae319cea3f4283acadf5630d32c5aa873c8ad2",
}

ADDITIONAL_SOURCE_PATHS = (
    DRIVER_RELATIVE,
    "agents/structural-basis/code/build_importance_d4_calibration_gate_v66.py",
    "agents/structural-basis/tests/test_importance_d4_calibration_v66.py",
    "agents/structural-basis/IMPORTANCE-D4-CALIBRATION-V66-SPEC.md",
    *V65_FAILURE_ARTIFACT_HASHES,
)
REQUIRED_SOURCE_PATHS = tuple(dict.fromkeys(
    tuple(v65.REQUIRED_SOURCE_PATHS) + ADDITIONAL_SOURCE_PATHS))
REQUIRED_DATA_PATHS = tuple(v65.REQUIRED_DATA_PATHS) + (V65_GATE_RELATIVE,)

UNIT_NORM_ULPS = 4096
UNIT_COORDINATE_ULPS = 64
SQUARE_COMPARISON_ULPS = 16


def validate_v65_failure_artifacts():
    for relative, expected in V65_FAILURE_ARTIFACT_HASHES.items():
        if v65.v64.v63.v62.v61.v6.v5.sha256_file(
                REPO_ROOT / relative) != expected:
            raise ValueError(f"frozen v6.5 failure artifact changed: {relative}")
    return True


def expected_conventions():
    answer = FROZEN_V65_EXPECTED_CONVENTIONS()
    answer.update({
        "j_z_unit_coordinates_and_norm_revalidated": True,
        "j_z_all_derived_quantities_finite_before_comparison": True,
        "j_z_square_overflow_checked_before_multiplication": True,
        "j_z_comparison_ulp_multiplier": SQUARE_COMPARISON_ULPS,
        "invalid_prelaunch_v65_gate_sha256": V65_GATE_SHA256,
    })
    return answer


def load_and_validate_gate(path):
    validate_v65_failure_artifacts()
    snapshot = v65.v64.v63.v62.v61.v6.v5.read_file_snapshot(path)
    gate = v65.v64.v63.v62.v61.v6.v5.strict_json_bytes(
        snapshot["data"], "v6.6 calibration gate")
    v65.v64.v63.v62.v61.v6.v5._exact_keys(gate, {
        "status", "rigorous", "production_launch_authorized",
        "supersedes_invalid_gate_sha256", "float_encoding", "source_hashes",
        "data_hashes", "schedule", "thresholds", "conventions",
        "extension_rule", "continuation_rule"}, "v6.6 calibration gate")
    if (gate["status"] !=
            "frozen-d4-exact-whitened-calibration-prelaunch-v6.6" or
            gate["rigorous"] is not False or
            gate["production_launch_authorized"] is not False or
            gate["supersedes_invalid_gate_sha256"] != V65_GATE_SHA256 or
            gate["float_encoding"] !=
            v65.v64.v63.v62.v61.v6.v5.FLOAT_ENCODING or
            gate["schedule"] !=
            v65.v64.v63.v62.v61.v6.v5.expected_schedule() or
            gate["thresholds"] !=
            v65.v64.v63.v62.v61.v6.v5.expected_thresholds() or
            gate["conventions"] != expected_conventions() or
            gate["extension_rule"] !=
            v65.v64.v63.v62.v61.v6.expected_extension_rule() or
            gate["continuation_rule"] !=
            v65.v64.v63.v62.v61.v6.expected_continuation_rule()):
        raise ValueError("v6.6 gate status, schedule, or conventions changed")
    for field, expected_paths in (
            ("source_hashes", REQUIRED_SOURCE_PATHS),
            ("data_hashes", REQUIRED_DATA_PATHS)):
        table = gate[field]
        if not isinstance(table, dict) or set(table) != set(expected_paths):
            raise ValueError(f"v6.6 {field} has missing or extra paths")
        for relative, expected in table.items():
            if (not isinstance(expected, str) or len(expected) != 64 or
                    any(character not in "0123456789abcdef"
                        for character in expected) or
                    v65.v64.v63.v62.v61.v6.v5.sha256_file(
                        REPO_ROOT / relative) != expected):
                raise ValueError(f"v6.6 dependency mismatch: {relative}")
    if gate["data_hashes"].get(V65_GATE_RELATIVE) != V65_GATE_SHA256:
        raise ValueError("v6.6 gate does not bind invalid v6.5 bytes")
    for relative, expected in V65_FAILURE_ARTIFACT_HASHES.items():
        if gate["source_hashes"].get(relative) != expected:
            raise ValueError("v6.6 gate does not bind frozen v6.5 failure")
    return {
        **v65.v64.v63.v62.v61.v6.v5.public_binding(snapshot),
        "gate": gate,
    }


def _require_plain_finite_float(value, name):
    if type(value) is not float or not math.isfinite(value):
        raise ArithmeticError(f"{name} is not a finite binary64 value")
    return value


def _finite_resolved_square(value):
    """Square one finite float, detecting overflow before multiplication."""
    value = _require_plain_finite_float(value, "weighted m0")
    magnitude = abs(value)
    if magnitude > 1.0:
        overflow_limit = sys.float_info.max / magnitude
        if not math.isfinite(overflow_limit) or magnitude > overflow_limit:
            raise ArithmeticError("weighted m0 square would overflow")
    square = value * value
    if not math.isfinite(square):
        raise ArithmeticError("weighted m0 square is nonfinite")
    if value != 0 and (square == 0 or square < sys.float_info.min):
        raise ArithmeticError("nonzero weighted m0 has unresolved square")
    return square


def _validate_unit_and_weights(adapter, point):
    unit = getattr(point, "unit_marginals", None)
    weights = getattr(adapter, "base_constant_weights", None)
    exact_weights = getattr(adapter, "base_constant_weights_exact", None)
    dimension = getattr(adapter, "dimension", None)
    strata = getattr(adapter, "strata", None)
    if (not isinstance(unit, tuple) or not isinstance(weights, tuple) or
            not isinstance(exact_weights, tuple) or
            isinstance(dimension, bool) or dimension != 96 or
            len(unit) != dimension or len(weights) != dimension or
            len(exact_weights) != dimension or
            tuple(strata) != tuple(range(16))):
        raise ArithmeticError("v6.6 weighted-m0 inputs are malformed")
    if (any(type(value) is not float or not math.isfinite(value)
            for value in unit + weights) or
            tuple(float(value) for value in exact_weights) != weights):
        raise ArithmeticError("v6.6 unit/weight values are not pinned finite floats")
    if any(weight != 0 for index, weight in enumerate(weights)
           if index % 6 != 0):
        raise ArithmeticError("base constant weight leaked off tagged channels")
    coordinate_tolerance = UNIT_COORDINATE_ULPS * math.ulp(1.0)
    if any(abs(value) > 1.0 + coordinate_tolerance for value in unit):
        raise ArithmeticError("normalized marginal coordinate exceeds one")
    norm_squared = math.fsum(value * value for value in unit)
    norm_tolerance = UNIT_NORM_ULPS * math.ulp(1.0)
    if (not math.isfinite(norm_squared) or
            abs(norm_squared - 1.0) > norm_tolerance):
        raise ArithmeticError("normalized marginal vector has invalid norm")
    return unit, weights, tuple(strata)


def _weighted_m0_and_square(adapter, point):
    unit, weights, strata = _validate_unit_and_weights(adapter, point)
    terms = []
    for r in strata:
        weight, value = weights[6 * r], unit[6 * r]
        term = weight * value
        if not math.isfinite(term):
            raise ArithmeticError("tagged weighted-m0 product is nonfinite")
        if weight != 0 and value != 0 and (
                term == 0 or 0 < abs(term) < sys.float_info.min):
            raise ArithmeticError("tagged weighted-m0 product is unresolved")
        terms.append(term)
    try:
        weighted = math.fsum(terms)
    except OverflowError as exc:
        raise ArithmeticError("weighted-m0 sum overflowed") from exc
    weighted = _require_plain_finite_float(weighted, "weighted m0")
    return weighted, _finite_resolved_square(weighted)


def _authenticate_recomputed_square(recorded, square):
    recorded = _require_plain_finite_float(recorded, "returned J z")
    square = _require_plain_finite_float(square, "recomputed J z")
    if (recorded < 0 or
            (recorded == 0 and math.copysign(1.0, recorded) < 0)):
        raise ArithmeticError("returned J z is negative or negative zero")
    if (recorded == 0) != (square == 0):
        raise ArithmeticError("returned J z lost weighted-m0 support")
    tolerance = SQUARE_COMPARISON_ULPS * max(
        math.ulp(recorded), math.ulp(square))
    if not math.isfinite(tolerance) or tolerance < 0:
        raise ArithmeticError("returned J z comparison tolerance is nonfinite")
    discrepancy = abs(recorded - square)
    if not math.isfinite(discrepancy):
        raise ArithmeticError("returned J z comparison discrepancy is nonfinite")
    if discrepancy > tolerance:
        raise ArithmeticError("returned J z differs from recomputed square")
    return True


def j_envelope_point(adapter, common):
    point = FROZEN_V65_J_ENVELOPE_POINT(adapter, common)
    if point is None:
        return None
    _, square = _weighted_m0_and_square(adapter, point)
    _authenticate_recomputed_square(getattr(point, "z", None), square)
    return point


def j_envelope_log_density(adapter, common):
    point = j_envelope_point(adapter, common)
    return -math.inf if point is None else point.log_g


def validate_chain_record(record, chain_spec, schedule, *, adapter=None):
    FROZEN_V65_VALIDATE_CHAIN_RECORD(
        record, chain_spec, schedule, adapter=adapter)
    return True


def install_runtime():
    v65.v64.v63.v62.v61.v6.DRIVER_RELATIVE = DRIVER_RELATIVE
    v65.v64.v63.v62.v61.v6.REQUIRED_SOURCE_PATHS = REQUIRED_SOURCE_PATHS
    v65.v64.v63.v62.v61.v6.REQUIRED_DATA_PATHS = REQUIRED_DATA_PATHS
    v65.v64.v63.v62.v61.v6.expected_conventions = expected_conventions
    v65.v64.v63.v62.v61.v6.load_and_validate_gate = load_and_validate_gate
    v65.v64.v63.v62.v61.v6.validate_chain_record = validate_chain_record
    v65.v64.v63.v62.v61.v6.j_envelope_point = j_envelope_point
    v65.v64.v63.v62.v61.v6.j_envelope_log_density = j_envelope_log_density


def main():
    install_runtime()
    return v65.v64.v63.v62.v61.v6.main()


if __name__ == "__main__":
    main()
