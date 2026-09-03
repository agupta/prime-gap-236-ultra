#!/usr/bin/env python3
"""Fresh hostile verifier for the frozen D4 calibration v6.1 successor."""

from __future__ import annotations

import copy
import hashlib
import json
import math
import sys
from pathlib import Path


HERE = Path(__file__).resolve()
REPO = HERE.parents[2]
CODE = REPO / "agents/structural-basis/code"
AUDIT = REPO / "agents/audit"
sys.path[:0] = [str(CODE), str(AUDIT)]

import importance_d4_calibration_v61 as V61  # noqa: E402
import importance_whitening_v6 as W  # noqa: E402
import verify_importance_d4_calibration_v6 as BASE  # noqa: E402


GATE = REPO / "agents/structural-basis/results/importance_d4_calibration_gate_v61.json"
ORACLE = REPO / V61.v6.REQUIRED_DATA_PATHS[0]
VECTOR = REPO / V61.v6.REQUIRED_DATA_PATHS[1]
EXPECTED = {
    "agents/structural-basis/code/importance_d4_calibration_v61.py":
        "3ecde36c901b2fb98bb0783ae77da7916e5e8bef062b9b3169b9f3b572f43409",
    "agents/structural-basis/code/build_importance_d4_calibration_gate_v61.py":
        "c8e4f9b49ccbded02c2b75a7b669d6a818ee50d773ae58a47f7de301bcc6b8cd",
    "agents/structural-basis/tests/test_importance_d4_calibration_v61.py":
        "7018e7e2d00610411981ff99e4897412346eee0fd914678993c5429d0a89a2d6",
    "agents/structural-basis/IMPORTANCE-D4-CALIBRATION-V61-SPEC.md":
        "c172e640803cd5840d3c3cf2aa5e890f048fb2c9687f8c2a7f184ead6cf04c88",
    "agents/structural-basis/results/importance_d4_calibration_gate_v61.json":
        "ff1b6c71bf07824180a822722bbf8a627c0e671f5a4034906ce6902348ece83d",
    **V61.V6_FAILURE_ARTIFACT_HASHES,
}


class AuditFailure(RuntimeError):
    pass


def require(condition, message):
    if not condition:
        raise AuditFailure(message)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def expect_rejection(callback, label):
    try:
        callback()
    except (ArithmeticError, ValueError, KeyError, IndexError, TypeError):
        return True
    raise AuditFailure(f"mutation was accepted: {label}")


def verify_gate():
    for relative, expected in EXPECTED.items():
        require(digest(REPO / relative) == expected,
                f"v6.1 frozen hash mismatch: {relative}")
    bound = V61.load_and_validate_gate(GATE)
    gate = bound["gate"]
    require(gate["production_launch_authorized"] is False,
            "v6.1 gate unexpectedly authorizes production")
    require(gate["supersedes_invalid_gate_sha256"] == V61.V6_GATE_SHA256,
            "v6.1 predecessor binding mismatch")
    for table in (gate["source_hashes"], gate["data_hashes"]):
        for relative, expected in table.items():
            require(digest(REPO / relative) == expected,
                    f"v6.1 gate dependency changed: {relative}")
    for relative, expected in V61.V6_FAILURE_ARTIFACT_HASHES.items():
        require(gate["source_hashes"].get(relative) == expected,
                f"v6.1 gate omitted failure artifact: {relative}")
    return gate


def verify_unchanged_math():
    independent = BASE.independent_oracle()
    package, _, _ = BASE.verify_exact_transform(independent)
    weights = BASE.verify_weights(independent, package)
    _, points = BASE.verify_direct_points_and_envelope(package)
    exact_bounds = tuple(
        package["base_weights"][6 * r] ** 2 +
        (package["base_weights"][6 * (r + 1)] ** 2 if r < 15 else 0)
        for r in range(16))
    require(exact_bounds == V61.J_Z_BOUNDS_EXACT,
            "v6.1 exact J-z table differs from independent base weights")
    require(max(exact_bounds) == V61.Fraction(1, 8),
            "v6.1 maximum exact J-z bound is not 1/8")
    return package, weights, points


def exercise_wrapper():
    V61.install_runtime()
    V61.v6._patch_v5_runtime()
    require(V61.v6.validate_chain_record is V61.validate_chain_record,
            "v6.1 wrapper did not replace v6 record validator")
    require(V61.v6.v5.validate_chain_record is V61.validate_chain_record,
            "v6.1 validator did not reach inherited runtime")
    require(V61.v6.j_envelope_point is V61.j_envelope_point,
            "v6.1 point envelope not installed")
    require(V61.v6.importance_conditional.j_envelope_log_density is
            V61.j_envelope_log_density,
            "v6.1 conditional target not installed")

    adapter = W.WhitenedC10ImportanceDensity(VECTOR, ORACLE)
    schedule = V61.v6.v5.tiny_smoke_schedule()
    spec = V61.v6.v5.expected_chain_table()[124]  # J,r=15,replicate=0.
    record = V61.v6.v5.run_one_chain(adapter, spec, schedule)
    require(V61.validate_chain_record(
        record, spec, schedule, adapter=adapter) is True,
        "valid v6.1 tail record rejected")

    # Confirm the v6 upper-bound counterexample is closed.
    repaired = copy.deepcopy(record)
    bound = float(V61.J_Z_BOUNDS_EXACT[15])
    seconds = [V61.v6.v5.parse_float_hex(value)
               for value in repaired["batch_z_second_means"]]
    seconds[0] = 2 * bound * bound
    repaired["batch_z_second_means"][0] = V61.v6.v5.float_hex(seconds[0])
    repaired["raw_second_sum"][-1] = V61.v6.v5.float_hex(
        schedule["samples_per_batch"] * math.fsum(seconds))
    expect_rejection(lambda: V61.validate_chain_record(
        repaired, spec, schedule, adapter=adapter), "v6 upper z^2 mutation")

    # Fresh v6.1 failure 1: a single raw field no longer reconstructs the
    # positive batch means, but max(1)-scaled v5 allclose hides the difference.
    bad_raw = copy.deepcopy(record)
    original_raw = V61.v6.v5.parse_float_hex(bad_raw["raw_sum"][-1])
    batch_mean = math.fsum(V61.v6.v5.parse_float_hex(value)
                           for value in bad_raw["batch_z_means"]) / \
        schedule["batches_per_chain"]
    bad_raw["raw_sum"][-1] = V61.v6.v5.float_hex(0.0)
    raw_accepted = V61.validate_chain_record(
        bad_raw, spec, schedule, adapter=adapter)
    require(raw_accepted is True,
            "known v6.1 raw aggregation gap was unexpectedly closed")

    # Fresh v6.1 failure 2: a positive batch mean with zero second moment.
    bad_jensen = copy.deepcopy(record)
    first_mean = V61.v6.v5.parse_float_hex(
        bad_jensen["batch_z_means"][0])
    old_first_second = V61.v6.v5.parse_float_hex(
        bad_jensen["batch_z_second_means"][0])
    seconds = [V61.v6.v5.parse_float_hex(value)
               for value in bad_jensen["batch_z_second_means"]]
    seconds[0] = 0.0
    bad_jensen["batch_z_second_means"][0] = V61.v6.v5.float_hex(0.0)
    bad_jensen["raw_second_sum"][-1] = V61.v6.v5.float_hex(
        schedule["samples_per_batch"] * math.fsum(seconds))
    jensen_accepted = V61.validate_chain_record(
        bad_jensen, spec, schedule, adapter=adapter)
    require(jensen_accepted is True,
            "known v6.1 tail Jensen gap was unexpectedly closed")

    # Schema, label/index, adapter, and upper-bound attacks do fail closed.
    attacks = {}
    for field in ("batch_z_means", "batch_z_second_means",
                  "raw_sum", "raw_second_sum"):
        malformed = copy.deepcopy(record)
        del malformed[field]
        attacks[f"missing_{field}"] = expect_rejection(
            lambda malformed=malformed: V61.validate_chain_record(
                malformed, spec, schedule, adapter=adapter),
            f"missing {field}")
    for label, value in (("bool", True), ("negative", -1), ("too_large", 16)):
        malformed = copy.deepcopy(record)
        malformed["stratum"] = value
        attacks[f"stratum_{label}"] = expect_rejection(
            lambda malformed=malformed: V61.validate_chain_record(
                malformed, spec, schedule, adapter=adapter),
            f"stratum {label}")
    malformed = copy.deepcopy(record)
    malformed["local_indices"][0] += 1
    attacks["local_index_map"] = expect_rejection(
        lambda: V61.validate_chain_record(
            malformed, spec, schedule, adapter=adapter), "local index map")
    attacks["adapter_required"] = expect_rejection(
        lambda: V61.validate_chain_record(record, spec, schedule, adapter=None),
        "missing transformed adapter")
    return {
        "upper_bound_repair_rejects": True,
        "schema_label_index_attacks_reject": all(attacks.values()),
        "tail_raw_counterexample": {
            "mutated_fields": ["raw_sum[-1]"],
            "original_raw_sum": original_raw,
            "mutated_raw_sum": 0.0,
            "positive_batch_mean": batch_mean,
            "accepted": raw_accepted,
        },
        "tail_jensen_counterexample": {
            "mutated_fields": ["batch_z_second_means[0]",
                               "raw_second_sum[-1]"],
            "positive_batch_mean": first_mean,
            "batch_mean_squared": first_mean * first_mean,
            "original_batch_second": old_first_second,
            "mutated_batch_second": 0.0,
            "accepted": jensen_accepted,
        },
        "exact_tail_z_bound": bound,
        "legacy_aggregation_atol": 128 * sys.float_info.epsilon,
        "legacy_jensen_atol": 256 * sys.float_info.epsilon,
    }


def main():
    gate = verify_gate()
    package, weights, points = verify_unchanged_math()
    wrapper = exercise_wrapper()
    print(json.dumps({
        "status": "AUDIT FAIL",
        "reason": "v6.1 inherits unit-scaled raw aggregation and Jensen tolerances that erase tail J moments",
        "gate_sha256": digest(GATE),
        "source_count": len(gate["source_hashes"]),
        "data_count": len(gate["data_hashes"]),
        "transform_sha256": package["sha256"],
        "unchanged_weight_checks": weights,
        "unchanged_direct_point_checks": points,
        "wrapper": wrapper,
    }, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
