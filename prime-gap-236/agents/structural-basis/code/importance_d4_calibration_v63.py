#!/usr/bin/env python3
"""V6.3 draft: reject J-moment information lost to float underflow.

This successor validates nonnegative serialized raw and batch totals before
forming averages.  Frozen v6.2 is preserved and remains unlaunchable.
"""

from __future__ import annotations

import math
from pathlib import Path

import importance_d4_calibration_v62 as v62


HERE = Path(__file__).resolve()
REPO_ROOT = HERE.parents[3]
DRIVER_RELATIVE = \
    "agents/structural-basis/code/importance_d4_calibration_v63.py"
V62_GATE_RELATIVE = \
    "agents/structural-basis/results/importance_d4_calibration_gate_v62.json"
V62_GATE_SHA256 = \
    "3642ace1f95b13e32259190ccb1690d726fcc2bd7cbda3298875a6f14d082bca"
FROZEN_V62_EXPECTED_CONVENTIONS = v62.expected_conventions
FROZEN_V62_VALIDATE_CHAIN_RECORD = v62.validate_chain_record
FROZEN_V62_J_ENVELOPE_POINT = v62.j_envelope_point

V62_FAILURE_ARTIFACT_HASHES = {
    "agents/audit/IMPORTANCE-D4-CALIBRATION-V62-PRELAUNCH-AUDIT.md":
        "3105d23283911725a914116ed50db36050cb34094a5874f1438f72c0c3f601f5",
    "agents/audit/verify_importance_d4_calibration_v62.py":
        "2c503f9f1b9c7e5d9ae9c3c99faf96ee4c2798a12746b3f307e4ca9564d0684b",
    "agents/audit/test_importance_d4_calibration_v62_underflow.py":
        "bb2a1aa0689d1d351fb094e4cb2b3133ba6e5fd3e267423766cff5f8c1dc0dd8",
}

ADDITIONAL_SOURCE_PATHS = (
    DRIVER_RELATIVE,
    "agents/structural-basis/code/build_importance_d4_calibration_gate_v63.py",
    "agents/structural-basis/tests/test_importance_d4_calibration_v63.py",
    "agents/structural-basis/IMPORTANCE-D4-CALIBRATION-V63-SPEC.md",
    *V62_FAILURE_ARTIFACT_HASHES,
)
REQUIRED_SOURCE_PATHS = tuple(dict.fromkeys(
    tuple(v62.REQUIRED_SOURCE_PATHS) + ADDITIONAL_SOURCE_PATHS))
REQUIRED_DATA_PATHS = tuple(v62.REQUIRED_DATA_PATHS) + (V62_GATE_RELATIVE,)


def validate_v62_failure_artifacts():
    if not V62_FAILURE_ARTIFACT_HASHES:
        raise ValueError("frozen v6.2 failure artifacts have not been pinned")
    for relative, expected in V62_FAILURE_ARTIFACT_HASHES.items():
        if v62.v61.v6.v5.sha256_file(REPO_ROOT / relative) != expected:
            raise ValueError(f"frozen v6.2 failure artifact changed: {relative}")
    return True


def expected_conventions():
    answer = FROZEN_V62_EXPECTED_CONVENTIONS()
    answer.update({
        "j_z_raw_total_checked_before_averaging": True,
        "j_z_positive_average_underflow_rejected": True,
        "j_z_signed_negative_zero_rejected": True,
        "invalid_prelaunch_v62_gate_sha256": V62_GATE_SHA256,
    })
    return answer


def load_and_validate_gate(path):
    validate_v62_failure_artifacts()
    snapshot = v62.v61.v6.v5.read_file_snapshot(path)
    gate = v62.v61.v6.v5.strict_json_bytes(snapshot["data"],
                                           "v6.3 calibration gate")
    v62.v61.v6.v5._exact_keys(gate, {
        "status", "rigorous", "production_launch_authorized",
        "supersedes_invalid_gate_sha256", "float_encoding", "source_hashes",
        "data_hashes", "schedule", "thresholds", "conventions",
        "extension_rule", "continuation_rule"}, "v6.3 calibration gate")
    if (gate["status"] !=
            "frozen-d4-exact-whitened-calibration-prelaunch-v6.3" or
            gate["rigorous"] is not False or
            gate["production_launch_authorized"] is not False or
            gate["supersedes_invalid_gate_sha256"] != V62_GATE_SHA256 or
            gate["float_encoding"] != v62.v61.v6.v5.FLOAT_ENCODING or
            gate["schedule"] != v62.v61.v6.v5.expected_schedule() or
            gate["thresholds"] != v62.v61.v6.v5.expected_thresholds() or
            gate["conventions"] != expected_conventions() or
            gate["extension_rule"] != v62.v61.v6.expected_extension_rule() or
            gate["continuation_rule"] !=
            v62.v61.v6.expected_continuation_rule()):
        raise ValueError("v6.3 gate status, schedule, or conventions changed")
    for field, expected_paths in (
            ("source_hashes", REQUIRED_SOURCE_PATHS),
            ("data_hashes", REQUIRED_DATA_PATHS)):
        table = gate[field]
        if not isinstance(table, dict) or set(table) != set(expected_paths):
            raise ValueError(f"v6.3 {field} has missing or extra paths")
        for relative, expected in table.items():
            if (not isinstance(expected, str) or len(expected) != 64 or
                    any(character not in "0123456789abcdef"
                        for character in expected) or
                    v62.v61.v6.v5.sha256_file(REPO_ROOT / relative) !=
                    expected):
                raise ValueError(f"v6.3 dependency mismatch: {relative}")
    if gate["data_hashes"].get(V62_GATE_RELATIVE) != V62_GATE_SHA256:
        raise ValueError("v6.3 gate does not bind invalid v6.2 bytes")
    for relative, expected in V62_FAILURE_ARTIFACT_HASHES.items():
        if gate["source_hashes"].get(relative) != expected:
            raise ValueError("v6.3 gate does not bind frozen v6.2 failure")
    return {**v62.v61.v6.v5.public_binding(snapshot), "gate": gate}


def _parsed_nonnegative(values, name):
    parsed = [v62.v61.v6.v5.parse_float_hex(value, name)
              for value in values]
    if any(value < 0 or (value == 0 and math.copysign(1.0, value) < 0)
           for value in parsed):
        raise ArithmeticError(f"{name} is negative or negative zero")
    return parsed


def _positive_average(total, divisor, name):
    if (not math.isfinite(total) or total < 0 or
            isinstance(divisor, bool) or not isinstance(divisor, int) or
            divisor <= 0):
        raise ValueError(f"invalid {name} average")
    answer = total / divisor
    if total > 0 and answer == 0:
        raise ArithmeticError(f"positive {name} underflowed while averaging")
    if not math.isfinite(answer):
        raise ArithmeticError(f"{name} average is nonfinite")
    return answer


def _require_total_close(left, right, operation_count, message):
    # For nonnegative observations, exact zero on only one side means that
    # averaging/grouping lost information.  It is never a rounding allowance.
    if (left == 0) != (right == 0):
        raise ArithmeticError(message + " (zero/nonzero mismatch)")
    v62._require_locally_close(left, right, operation_count, message)


def _validate_j_totals_before_averaging(record, schedule):
    if not isinstance(record, dict) or record.get("target") != "J":
        raise ValueError("v6.3 raw-total validator requires one J record")
    batch_count = schedule.get("batches_per_chain")
    samples_per_batch = schedule.get("samples_per_batch")
    if (isinstance(batch_count, bool) or not isinstance(batch_count, int) or
            isinstance(samples_per_batch, bool) or
            not isinstance(samples_per_batch, int) or
            batch_count <= 0 or samples_per_batch <= 0):
        raise ValueError("v6.3 raw-total schedule is invalid")
    means_raw = record.get("batch_z_means")
    seconds_raw = record.get("batch_z_second_means")
    raw_sums = record.get("raw_sum")
    raw_seconds = record.get("raw_second_sum")
    if (not isinstance(means_raw, list) or len(means_raw) != batch_count or
            not isinstance(seconds_raw, list) or
            len(seconds_raw) != batch_count or
            not isinstance(raw_sums, list) or not raw_sums or
            not isinstance(raw_seconds, list) or not raw_seconds):
        raise ValueError("v6.3 J-z arrays have invalid shape")
    means = _parsed_nonnegative(means_raw, "v6.3 J z batch")
    seconds = _parsed_nonnegative(seconds_raw, "v6.3 J z-second batch")
    raw = _parsed_nonnegative([raw_sums[-1]], "v6.3 J raw z")[0]
    raw_second = _parsed_nonnegative(
        [raw_seconds[-1]], "v6.3 J raw z-second")[0]

    batch_total = math.fsum(means)
    batch_second_total = math.fsum(seconds)
    if (any(value > 0 for value in means) and batch_total == 0) or \
            (any(value > 0 for value in seconds) and
             batch_second_total == 0):
        raise ArithmeticError("positive J batch component vanished in sum")
    reconstructed_raw = samples_per_batch * batch_total
    reconstructed_raw_second = samples_per_batch * batch_second_total
    if (batch_total > 0 and reconstructed_raw == 0) or \
            (batch_second_total > 0 and reconstructed_raw_second == 0):
        raise ArithmeticError("positive J batch total vanished in regrouping")
    operation_count = batch_count * samples_per_batch + batch_count + 16
    _require_total_close(
        raw, reconstructed_raw, operation_count,
        "J raw z total disagrees with regrouped batches")
    _require_total_close(
        raw_second, reconstructed_raw_second, operation_count,
        "J raw z-second total disagrees with regrouped batches")

    mean_from_raw = _positive_average(
        raw, batch_count * samples_per_batch, "raw J z")
    second_from_raw = _positive_average(
        raw_second, batch_count * samples_per_batch, "raw J z-second")
    mean_from_batches = _positive_average(
        batch_total, batch_count, "batched J z")
    second_from_batches = _positive_average(
        batch_second_total, batch_count, "batched J z-second")
    _require_total_close(
        mean_from_raw, mean_from_batches, operation_count,
        "J raw/batch z averages disagree")
    _require_total_close(
        second_from_raw, second_from_batches, operation_count,
        "J raw/batch z-second averages disagree")

    # A positive second moment with a zero first moment cannot arise from
    # nonnegative z observations; reject instead of treating it as a rare
    # floating-point corner.
    if any(mean == 0 and second > 0
           for mean, second in zip(means, seconds)) or \
            (mean_from_raw == 0 and second_from_raw > 0):
        raise ArithmeticError("positive J z-second has zero z first moment")
    return True


def j_envelope_point(adapter, common):
    return FROZEN_V62_J_ENVELOPE_POINT(adapter, common)


def j_envelope_log_density(adapter, common):
    point = j_envelope_point(adapter, common)
    return -math.inf if point is None else point.log_g


def validate_chain_record(record, chain_spec, schedule, *, adapter=None):
    if isinstance(record, dict) and record.get("target") == "J":
        _validate_j_totals_before_averaging(record, schedule)
    FROZEN_V62_VALIDATE_CHAIN_RECORD(
        record, chain_spec, schedule, adapter=adapter)
    return True


def install_runtime():
    v62.v61.v6.DRIVER_RELATIVE = DRIVER_RELATIVE
    v62.v61.v6.REQUIRED_SOURCE_PATHS = REQUIRED_SOURCE_PATHS
    v62.v61.v6.REQUIRED_DATA_PATHS = REQUIRED_DATA_PATHS
    v62.v61.v6.expected_conventions = expected_conventions
    v62.v61.v6.load_and_validate_gate = load_and_validate_gate
    v62.v61.v6.validate_chain_record = validate_chain_record
    v62.v61.v6.j_envelope_point = j_envelope_point
    v62.v61.v6.j_envelope_log_density = j_envelope_log_density


def main():
    install_runtime()
    return v62.v61.v6.main()


if __name__ == "__main__":
    main()
