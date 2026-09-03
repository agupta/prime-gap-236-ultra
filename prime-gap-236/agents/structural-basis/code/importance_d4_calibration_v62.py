#!/usr/bin/env python3
"""V6.2: locally scaled J aggregation/Jensen checks over frozen v6.1.

Frozen v6.1 added exact per-common-stratum upper bounds, but inherited
absolute tolerances proportional to one could still erase every meaningful
consistency check in the smallest strata.  This successor retains all prior
checks and adds scale-local comparisons for the serialized J z moments.
"""

from __future__ import annotations

import math
from fractions import Fraction
from pathlib import Path

import importance_d4_calibration_v61 as v61


HERE = Path(__file__).resolve()
REPO_ROOT = HERE.parents[3]
DRIVER_RELATIVE = \
    "agents/structural-basis/code/importance_d4_calibration_v62.py"
V61_GATE_RELATIVE = \
    "agents/structural-basis/results/importance_d4_calibration_gate_v61.json"
V61_GATE_SHA256 = \
    "ff1b6c71bf07824180a822722bbf8a627c0e671f5a4034906ce6902348ece83d"
FROZEN_V61_EXPECTED_CONVENTIONS = v61.expected_conventions
FROZEN_V61_VALIDATE_CHAIN_RECORD = v61.validate_chain_record
FROZEN_V61_J_ENVELOPE_POINT = v61.j_envelope_point

# These frozen independent artifacts are part of the source closure, not
# optional prose.
V61_FAILURE_ARTIFACT_HASHES = {
    "agents/audit/IMPORTANCE-D4-CALIBRATION-V61-PRELAUNCH-AUDIT.md":
        "3e86f5b7bcdb3221c8279044cb1c1d9bd06919e1db8f1690fa7d162433fa2d81",
    "agents/audit/verify_importance_d4_calibration_v61.py":
        "ce527cf6176fe168fd0862be1189bdef0ccccbe96c48bc205327a53c3fbfe69c",
    "agents/audit/test_importance_d4_calibration_v61_tail_moments.py":
        "339e3620adae4c13bac0a00499740462dd2a3647f821a4246dc7ef32d4d2d4e6",
}

ADDITIONAL_SOURCE_PATHS = (
    DRIVER_RELATIVE,
    "agents/structural-basis/code/build_importance_d4_calibration_gate_v62.py",
    "agents/structural-basis/tests/test_importance_d4_calibration_v62.py",
    "agents/structural-basis/IMPORTANCE-D4-CALIBRATION-V62-SPEC.md",
    *V61_FAILURE_ARTIFACT_HASHES,
)
REQUIRED_SOURCE_PATHS = tuple(dict.fromkeys(
    tuple(v61.REQUIRED_SOURCE_PATHS) + ADDITIONAL_SOURCE_PATHS))
REQUIRED_DATA_PATHS = tuple(v61.REQUIRED_DATA_PATHS) + (V61_GATE_RELATIVE,)


def validate_v61_failure_artifacts():
    if not V61_FAILURE_ARTIFACT_HASHES:
        raise ValueError("frozen v6.1 failure artifacts have not been pinned")
    for relative, expected in V61_FAILURE_ARTIFACT_HASHES.items():
        if v61.v6.v5.sha256_file(REPO_ROOT / relative) != expected:
            raise ValueError(f"frozen v6.1 failure artifact changed: {relative}")
    return True


def expected_conventions():
    answer = FROZEN_V61_EXPECTED_CONVENTIONS()
    answer.update({
        "j_z_local_aggregation_checks": True,
        "j_z_local_jensen_checks": True,
        "j_z_tolerance_scale":
            "max of compared local magnitudes; never max(1,...)",
        "invalid_prelaunch_v61_gate_sha256": V61_GATE_SHA256,
    })
    return answer


def load_and_validate_gate(path):
    validate_v61_failure_artifacts()
    snapshot = v61.v6.v5.read_file_snapshot(path)
    gate = v61.v6.v5.strict_json_bytes(snapshot["data"],
                                       "v6.2 calibration gate")
    v61.v6.v5._exact_keys(gate, {
        "status", "rigorous", "production_launch_authorized",
        "supersedes_invalid_gate_sha256", "float_encoding", "source_hashes",
        "data_hashes", "schedule", "thresholds", "conventions",
        "extension_rule", "continuation_rule"}, "v6.2 calibration gate")
    if (gate["status"] !=
            "frozen-d4-exact-whitened-calibration-prelaunch-v6.2" or
            gate["rigorous"] is not False or
            gate["production_launch_authorized"] is not False or
            gate["supersedes_invalid_gate_sha256"] != V61_GATE_SHA256 or
            gate["float_encoding"] != v61.v6.v5.FLOAT_ENCODING or
            gate["schedule"] != v61.v6.v5.expected_schedule() or
            gate["thresholds"] != v61.v6.v5.expected_thresholds() or
            gate["conventions"] != expected_conventions() or
            gate["extension_rule"] != v61.v6.expected_extension_rule() or
            gate["continuation_rule"] != v61.v6.expected_continuation_rule()):
        raise ValueError("v6.2 gate status, schedule, or conventions changed")
    for field, expected_paths in (
            ("source_hashes", REQUIRED_SOURCE_PATHS),
            ("data_hashes", REQUIRED_DATA_PATHS)):
        table = gate[field]
        if not isinstance(table, dict) or set(table) != set(expected_paths):
            raise ValueError(f"v6.2 {field} has missing or extra paths")
        for relative, expected in table.items():
            if (not isinstance(expected, str) or len(expected) != 64 or
                    any(character not in "0123456789abcdef"
                        for character in expected) or
                    v61.v6.v5.sha256_file(REPO_ROOT / relative) != expected):
                raise ValueError(f"v6.2 dependency mismatch: {relative}")
    if gate["data_hashes"].get(V61_GATE_RELATIVE) != V61_GATE_SHA256:
        raise ValueError("v6.2 gate does not bind invalid v6.1 bytes")
    for relative, expected in V61_FAILURE_ARTIFACT_HASHES.items():
        if gate["source_hashes"].get(relative) != expected:
            raise ValueError("v6.2 gate does not bind frozen v6.1 failure")
    return {**v61.v6.v5.public_binding(snapshot), "gate": gate}


def _local_roundoff_tolerance(left, right, operation_count):
    """Conservative local IEEE-double comparison allowance.

    All z quantities are nonnegative sums, so their rounding error scales
    with the represented local magnitude rather than with one or with the
    (possibly much larger) pointwise envelope bound.  The operation-count
    factor covers both sequential raw accumulation and batch regrouping.
    """
    if (not math.isfinite(left) or not math.isfinite(right) or
            isinstance(operation_count, bool) or
            not isinstance(operation_count, int) or operation_count < 0):
        raise ValueError("invalid local-roundoff comparison")
    scale = max(abs(left), abs(right))
    if scale == 0:
        return 0.0
    epsilon = math.ulp(1.0)
    factor = 128 + 32 * operation_count
    if factor * epsilon >= Fraction(1, 1000):
        raise ArithmeticError("schedule is too large for local error bound")
    # In the subnormal range the usual relative-error model is unavailable;
    # retain an operation-count-scaled absolute ULP allowance as well.
    ulp_term = (64 + 4 * operation_count) * max(
        math.ulp(left), math.ulp(right), math.ulp(scale))
    answer = factor * epsilon * scale + ulp_term
    if not math.isfinite(answer) or answer <= 0:
        raise ArithmeticError("local-roundoff tolerance is invalid")
    return answer


def _require_locally_close(left, right, operation_count, message):
    tolerance = _local_roundoff_tolerance(left, right, operation_count)
    if abs(left - right) > tolerance:
        raise ArithmeticError(message)


def _require_local_jensen(second, mean, operation_count, message):
    square = mean * mean
    if (not math.isfinite(square) or (mean != 0 and square == 0)):
        raise ArithmeticError("local J Jensen square is nonfinite/underflowed")
    tolerance = _local_roundoff_tolerance(second, square, operation_count)
    if second < square - tolerance:
        raise ArithmeticError(message)


def _validate_j_local_consistency(record, schedule):
    if record.get("target") != "J":
        raise ValueError("local J-z validator received a non-J record")
    batch_count = schedule.get("batches_per_chain")
    samples_per_batch = schedule.get("samples_per_batch")
    if (isinstance(batch_count, bool) or not isinstance(batch_count, int) or
            isinstance(samples_per_batch, bool) or
            not isinstance(samples_per_batch, int) or
            batch_count <= 0 or samples_per_batch <= 0):
        raise ValueError("local J-z schedule is invalid")
    sample_count = batch_count * samples_per_batch
    means = [v61.v6.v5.parse_float_hex(value, "v6.2 J z batch")
             for value in record["batch_z_means"]]
    seconds = [v61.v6.v5.parse_float_hex(value, "v6.2 J z second batch")
               for value in record["batch_z_second_means"]]
    raw = v61.v6.v5.parse_float_hex(
        record["raw_sum"][-1], "v6.2 J raw z")
    raw_second = v61.v6.v5.parse_float_hex(
        record["raw_second_sum"][-1], "v6.2 J raw z second")
    if len(means) != batch_count or len(seconds) != batch_count:
        raise ValueError("local J-z batch count changed")
    if any(not math.isfinite(value) or value < 0
           for value in means + seconds + [raw, raw_second]):
        raise ArithmeticError("local J-z moment is negative or nonfinite")

    mean_from_raw = raw / sample_count
    second_from_raw = raw_second / sample_count
    mean_from_batches = math.fsum(means) / batch_count
    second_from_batches = math.fsum(seconds) / batch_count
    aggregation_ops = sample_count + batch_count + samples_per_batch + 16
    _require_locally_close(
        mean_from_raw, mean_from_batches, aggregation_ops,
        "local J raw z sum disagrees with batch means")
    _require_locally_close(
        second_from_raw, second_from_batches, aggregation_ops,
        "local J raw z-second sum disagrees with batch means")

    for mean, second in zip(means, seconds):
        _require_local_jensen(
            second, mean, samples_per_batch + 16,
            "local J batch z moments violate Jensen")
    _require_local_jensen(
        second_from_raw, mean_from_raw, sample_count + 16,
        "local J raw z moments violate Jensen")
    squares = [value * value for value in means]
    if any(value != 0 and square == 0
           for value, square in zip(means, squares)):
        raise ArithmeticError("local J batch-square underflowed")
    batch_square_mean = math.fsum(squares) / batch_count
    tolerance = _local_roundoff_tolerance(
        second_from_raw, batch_square_mean, aggregation_ops)
    if second_from_raw < batch_square_mean - tolerance:
        raise ArithmeticError("local J raw moments violate batch Jensen")
    return True


def j_envelope_point(adapter, common):
    return FROZEN_V61_J_ENVELOPE_POINT(adapter, common)


def j_envelope_log_density(adapter, common):
    point = j_envelope_point(adapter, common)
    return -math.inf if point is None else point.log_g


def validate_chain_record(record, chain_spec, schedule, *, adapter=None):
    FROZEN_V61_VALIDATE_CHAIN_RECORD(
        record, chain_spec, schedule, adapter=adapter)
    if record.get("target") == "J":
        _validate_j_local_consistency(record, schedule)
    return True


def install_runtime():
    v61.v6.DRIVER_RELATIVE = DRIVER_RELATIVE
    v61.v6.REQUIRED_SOURCE_PATHS = REQUIRED_SOURCE_PATHS
    v61.v6.REQUIRED_DATA_PATHS = REQUIRED_DATA_PATHS
    v61.v6.expected_conventions = expected_conventions
    v61.v6.load_and_validate_gate = load_and_validate_gate
    v61.v6.validate_chain_record = validate_chain_record
    v61.v6.j_envelope_point = j_envelope_point
    v61.v6.j_envelope_log_density = j_envelope_log_density


def main():
    install_runtime()
    return v61.v6.main()


if __name__ == "__main__":
    main()
