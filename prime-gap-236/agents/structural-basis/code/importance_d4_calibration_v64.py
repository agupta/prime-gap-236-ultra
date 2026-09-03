#!/usr/bin/env python3
"""V6.4: forbid loss of positive J-z first/second moment support.

Frozen v6.3 checks raw totals before division.  This successor additionally
requires exact zero-status agreement between every nonnegative first and
second z moment and rejects unresolved positive subnormal moments.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import importance_d4_calibration_v63 as v63


HERE = Path(__file__).resolve()
REPO_ROOT = HERE.parents[3]
DRIVER_RELATIVE = \
    "agents/structural-basis/code/importance_d4_calibration_v64.py"
V63_GATE_RELATIVE = \
    "agents/structural-basis/results/importance_d4_calibration_gate_v63.json"
V63_GATE_SHA256 = \
    "b5098156a85f6b94d3c8f2c000839e4fa1de680c439800ee6736eccc8c22ce16"
FROZEN_V63_EXPECTED_CONVENTIONS = v63.expected_conventions
FROZEN_V63_VALIDATE_CHAIN_RECORD = v63.validate_chain_record
FROZEN_V63_J_ENVELOPE_POINT = v63.j_envelope_point

V63_FAILURE_ARTIFACT_HASHES = {
    "agents/audit/IMPORTANCE-D4-CALIBRATION-V63-PRELAUNCH-AUDIT.md":
        "9b65083f553d356f2f525197623eb153dba4e1f7fdd6f3d18fa200acb08ace98",
    "agents/audit/verify_importance_d4_calibration_v63.py":
        "6302c8f8d9dbc2e557081784e359fb811ca4b1d1998aa69955169029fd1dfe6b",
    "agents/audit/test_importance_d4_calibration_v63_zero_second.py":
        "0aa8fa5c9db51d3c433e6e1ecefaa740883c4b1282e09fbff7504ffa78934b65",
}

ADDITIONAL_SOURCE_PATHS = (
    DRIVER_RELATIVE,
    "agents/structural-basis/code/build_importance_d4_calibration_gate_v64.py",
    "agents/structural-basis/tests/test_importance_d4_calibration_v64.py",
    "agents/structural-basis/IMPORTANCE-D4-CALIBRATION-V64-SPEC.md",
    *V63_FAILURE_ARTIFACT_HASHES,
)
REQUIRED_SOURCE_PATHS = tuple(dict.fromkeys(
    tuple(v63.REQUIRED_SOURCE_PATHS) + ADDITIONAL_SOURCE_PATHS))
REQUIRED_DATA_PATHS = tuple(v63.REQUIRED_DATA_PATHS) + (V63_GATE_RELATIVE,)


def validate_v63_failure_artifacts():
    for relative, expected in V63_FAILURE_ARTIFACT_HASHES.items():
        if v63.v62.v61.v6.v5.sha256_file(REPO_ROOT / relative) != expected:
            raise ValueError(f"frozen v6.3 failure artifact changed: {relative}")
    return True


def expected_conventions():
    answer = FROZEN_V63_EXPECTED_CONVENTIONS()
    answer.update({
        "j_z_first_second_zero_status_identical": True,
        "j_z_positive_subnormal_moments_rejected": True,
        "j_z_pointwise_second_underflow_rejected": True,
        "invalid_prelaunch_v63_gate_sha256": V63_GATE_SHA256,
    })
    return answer


def load_and_validate_gate(path):
    validate_v63_failure_artifacts()
    snapshot = v63.v62.v61.v6.v5.read_file_snapshot(path)
    gate = v63.v62.v61.v6.v5.strict_json_bytes(
        snapshot["data"], "v6.4 calibration gate")
    v63.v62.v61.v6.v5._exact_keys(gate, {
        "status", "rigorous", "production_launch_authorized",
        "supersedes_invalid_gate_sha256", "float_encoding", "source_hashes",
        "data_hashes", "schedule", "thresholds", "conventions",
        "extension_rule", "continuation_rule"}, "v6.4 calibration gate")
    if (gate["status"] !=
            "frozen-d4-exact-whitened-calibration-prelaunch-v6.4" or
            gate["rigorous"] is not False or
            gate["production_launch_authorized"] is not False or
            gate["supersedes_invalid_gate_sha256"] != V63_GATE_SHA256 or
            gate["float_encoding"] != v63.v62.v61.v6.v5.FLOAT_ENCODING or
            gate["schedule"] != v63.v62.v61.v6.v5.expected_schedule() or
            gate["thresholds"] != v63.v62.v61.v6.v5.expected_thresholds() or
            gate["conventions"] != expected_conventions() or
            gate["extension_rule"] !=
            v63.v62.v61.v6.expected_extension_rule() or
            gate["continuation_rule"] !=
            v63.v62.v61.v6.expected_continuation_rule()):
        raise ValueError("v6.4 gate status, schedule, or conventions changed")
    for field, expected_paths in (
            ("source_hashes", REQUIRED_SOURCE_PATHS),
            ("data_hashes", REQUIRED_DATA_PATHS)):
        table = gate[field]
        if not isinstance(table, dict) or set(table) != set(expected_paths):
            raise ValueError(f"v6.4 {field} has missing or extra paths")
        for relative, expected in table.items():
            if (not isinstance(expected, str) or len(expected) != 64 or
                    any(character not in "0123456789abcdef"
                        for character in expected) or
                    v63.v62.v61.v6.v5.sha256_file(REPO_ROOT / relative) !=
                    expected):
                raise ValueError(f"v6.4 dependency mismatch: {relative}")
    if gate["data_hashes"].get(V63_GATE_RELATIVE) != V63_GATE_SHA256:
        raise ValueError("v6.4 gate does not bind invalid v6.3 bytes")
    for relative, expected in V63_FAILURE_ARTIFACT_HASHES.items():
        if gate["source_hashes"].get(relative) != expected:
            raise ValueError("v6.4 gate does not bind frozen v6.3 failure")
    return {**v63.v62.v61.v6.v5.public_binding(snapshot), "gate": gate}


def _resolved_nonnegative(values, name):
    answer = []
    for raw in values:
        value = v63.v62.v61.v6.v5.parse_float_hex(raw, name)
        if value < 0 or (value == 0 and math.copysign(1.0, value) < 0):
            raise ArithmeticError(f"{name} is negative or negative zero")
        if 0 < value < sys.float_info.min:
            raise ArithmeticError(f"{name} is an unresolved subnormal")
        answer.append(value)
    return answer


def _validate_j_first_second_support(record, schedule):
    if not isinstance(record, dict) or record.get("target") != "J":
        raise ValueError("v6.4 support validator requires one J record")
    batch_count = schedule.get("batches_per_chain")
    if (isinstance(batch_count, bool) or not isinstance(batch_count, int) or
            batch_count <= 0):
        raise ValueError("v6.4 support schedule is invalid")
    means_raw = record.get("batch_z_means")
    seconds_raw = record.get("batch_z_second_means")
    raw_sums = record.get("raw_sum")
    raw_seconds = record.get("raw_second_sum")
    if (not isinstance(means_raw, list) or len(means_raw) != batch_count or
            not isinstance(seconds_raw, list) or
            len(seconds_raw) != batch_count or
            not isinstance(raw_sums, list) or not raw_sums or
            not isinstance(raw_seconds, list) or not raw_seconds):
        raise ValueError("v6.4 J-z arrays have invalid shape")
    means = _resolved_nonnegative(means_raw, "v6.4 J z batch")
    seconds = _resolved_nonnegative(seconds_raw, "v6.4 J z-second batch")
    raw = _resolved_nonnegative([raw_sums[-1]], "v6.4 J raw z")[0]
    raw_second = _resolved_nonnegative(
        [raw_seconds[-1]], "v6.4 J raw z-second")[0]
    for mean, second in zip(means, seconds):
        if (mean == 0) != (second == 0):
            raise ArithmeticError(
                "J batch first/second moments disagree on zero support")
    if (raw == 0) != (raw_second == 0):
        raise ArithmeticError(
            "J raw first/second moments disagree on zero support")
    return True


def j_envelope_point(adapter, common):
    point = FROZEN_V63_J_ENVELOPE_POINT(adapter, common)
    if point is None:
        return None
    square = point.z * point.z
    if point.z > 0 and (square == 0 or square < sys.float_info.min):
        raise ArithmeticError("pointwise J z-second is unresolved/underflowed")
    return point


def j_envelope_log_density(adapter, common):
    point = j_envelope_point(adapter, common)
    return -math.inf if point is None else point.log_g


def validate_chain_record(record, chain_spec, schedule, *, adapter=None):
    if isinstance(record, dict) and record.get("target") == "J":
        _validate_j_first_second_support(record, schedule)
    FROZEN_V63_VALIDATE_CHAIN_RECORD(
        record, chain_spec, schedule, adapter=adapter)
    return True


def install_runtime():
    v63.v62.v61.v6.DRIVER_RELATIVE = DRIVER_RELATIVE
    v63.v62.v61.v6.REQUIRED_SOURCE_PATHS = REQUIRED_SOURCE_PATHS
    v63.v62.v61.v6.REQUIRED_DATA_PATHS = REQUIRED_DATA_PATHS
    v63.v62.v61.v6.expected_conventions = expected_conventions
    v63.v62.v61.v6.load_and_validate_gate = load_and_validate_gate
    v63.v62.v61.v6.validate_chain_record = validate_chain_record
    v63.v62.v61.v6.j_envelope_point = j_envelope_point
    v63.v62.v61.v6.j_envelope_log_density = j_envelope_log_density


def main():
    install_runtime()
    return v63.v62.v61.v6.main()


if __name__ == "__main__":
    main()
