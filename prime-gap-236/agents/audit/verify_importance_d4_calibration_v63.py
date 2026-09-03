#!/usr/bin/env python3
"""Fresh hostile verifier for the frozen D4 calibration v6.3 package."""

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
sys.path.insert(0, str(CODE))

import importance_d4_calibration_v63 as V63  # noqa: E402
from importance_whitening_v6 import WhitenedC10ImportanceDensity  # noqa: E402


GATE = REPO / "agents/structural-basis/results/importance_d4_calibration_gate_v63.json"
EXPECTED = {
    "agents/structural-basis/code/importance_d4_calibration_v63.py":
        "32030ecb5eaa2f73983309a20563a8702abfe9a4c0d22a2675936e7d802d9830",
    "agents/structural-basis/code/build_importance_d4_calibration_gate_v63.py":
        "724e2366bc8ef8db4914526dc16b273c0d077cfd38ab475afaaf5f4ac5d3b709",
    "agents/structural-basis/tests/test_importance_d4_calibration_v63.py":
        "13c2d7edbfadf15db7647147b409d4a56844b30d3fc7f3c80b4ece07677208ab",
    "agents/structural-basis/IMPORTANCE-D4-CALIBRATION-V63-SPEC.md":
        "2f5093edf295e49bdd6c36e103f1cb796574ddd1b3739a4fd98e9e49e661cf1f",
    "agents/structural-basis/results/importance_d4_calibration_gate_v63.json":
        "b5098156a85f6b94d3c8f2c000839e4fa1de680c439800ee6736eccc8c22ce16",
    "agents/audit/test_importance_d4_calibration_v63_zero_second.py":
        "0aa8fa5c9db51d3c433e6e1ecefaa740883c4b1282e09fbff7504ffa78934b65",
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
    except (ArithmeticError, ValueError, OverflowError, KeyError,
            IndexError, TypeError):
        return True
    raise AuditFailure(f"mutation was accepted: {label}")


def verify_gate():
    for relative, expected in EXPECTED.items():
        require(digest(REPO / relative) == expected,
                f"frozen v6.3 hash mismatch: {relative}")
    bound = V63.load_and_validate_gate(GATE)
    gate = bound["gate"]
    require(gate["production_launch_authorized"] is False,
            "v6.3 gate unexpectedly authorizes production")
    require(gate["rigorous"] is False,
            "v6.3 gate unexpectedly claims rigor")
    require(gate["supersedes_invalid_gate_sha256"] == V63.V62_GATE_SHA256,
            "v6.3 predecessor binding mismatch")
    for table in (gate["source_hashes"], gate["data_hashes"]):
        for relative, expected in table.items():
            require(digest(REPO / relative) == expected,
                    f"v6.3 gate dependency changed: {relative}")
    for relative, expected in V63.V62_FAILURE_ARTIFACT_HASHES.items():
        require(gate["source_hashes"].get(relative) == expected,
                f"v6.3 omitted frozen v6.2 failure: {relative}")
    return gate


def validator_fixture():
    V63.install_runtime()
    V63.v62.v61.v6._patch_v5_runtime()
    oracle = REPO / V63.v62.v61.v6.REQUIRED_DATA_PATHS[0]
    vector = REPO / V63.v62.v61.v6.REQUIRED_DATA_PATHS[1]
    adapter = WhitenedC10ImportanceDensity(vector, oracle)
    schedule = V63.v62.v61.v6.v5.tiny_smoke_schedule()
    spec = V63.v62.v61.v6.v5.expected_chain_table()[124]
    record = V63.v62.v61.v6.v5.run_one_chain(adapter, spec, schedule)
    require(V63.validate_chain_record(
        record, spec, schedule, adapter=adapter) is True,
        "valid v6.3 tail record rejected")
    return adapter, schedule, spec, record


def verify_predecessor_failures_closed(adapter, schedule, spec, record):
    encode = V63.v62.v61.v6.v5.float_hex
    closed = {}

    # V6: a batch z second moment above the exact stratum bound.
    mutation = copy.deepcopy(record)
    bound = float(V63.v62.v61.J_Z_BOUNDS_EXACT[15])
    seconds = [V63.v62.v61.v6.v5.parse_float_hex(value)
               for value in mutation["batch_z_second_means"]]
    seconds[0] = 2 * bound * bound
    mutation["batch_z_second_means"][0] = encode(seconds[0])
    mutation["raw_second_sum"][-1] = encode(
        schedule["samples_per_batch"] * math.fsum(seconds))
    closed["v6_stratum_upper_bound"] = expect_rejection(
        lambda: V63.validate_chain_record(
            mutation, spec, schedule, adapter=adapter),
        "v6 stratum-specific z-second bound")

    # V6.1: unit-scale aggregation and Jensen gaps.
    mutation = copy.deepcopy(record)
    mutation["raw_sum"][-1] = encode(0.0)
    closed["v61_raw_batch_scale"] = expect_rejection(
        lambda: V63.validate_chain_record(
            mutation, spec, schedule, adapter=adapter),
        "v6.1 raw/batch aggregation")
    mutation = copy.deepcopy(record)
    seconds = [V63.v62.v61.v6.v5.parse_float_hex(value)
               for value in mutation["batch_z_second_means"]]
    seconds[0] = 0.0
    mutation["batch_z_second_means"][0] = encode(0.0)
    mutation["raw_second_sum"][-1] = encode(
        schedule["samples_per_batch"] * math.fsum(seconds))
    closed["v61_batch_jensen_scale"] = expect_rejection(
        lambda: V63.validate_chain_record(
            mutation, spec, schedule, adapter=adapter),
        "v6.1 batch Jensen")

    # V6.2: positive serialized numerators disappear on division.
    tiny = math.ulp(0.0)
    mutation = copy.deepcopy(record)
    mutation["batch_z_means"] = [encode(0.0)] * 4
    mutation["batch_z_second_means"] = [encode(0.0)] * 4
    mutation["raw_sum"][-1] = encode(tiny)
    mutation["raw_second_sum"][-1] = encode(0.0)
    closed["v62_positive_raw_underflow"] = expect_rejection(
        lambda: V63.validate_chain_record(
            mutation, spec, schedule, adapter=adapter),
        "v6.2 raw numerator underflow")
    mutation["raw_sum"][-1] = encode(0.0)
    mutation["batch_z_second_means"][0] = encode(tiny)
    mutation["raw_second_sum"][-1] = encode(2 * tiny)
    closed["v62_positive_batch_underflow"] = expect_rejection(
        lambda: V63.validate_chain_record(
            mutation, spec, schedule, adapter=adapter),
        "v6.2 batch numerator underflow")
    return closed


def verify_v63_failure(adapter, schedule, spec, record):
    encode = V63.v62.v61.v6.v5.float_hex
    tiny = math.ulp(0.0)
    mean = math.sqrt(tiny)
    require(mean.hex() == "0x1.0000000000000p-537" and
            mean * mean == tiny,
            "binary64 one-ulp Jensen fixture changed")
    mutation = copy.deepcopy(record)
    mutation["batch_z_means"] = [encode(mean)] * 4
    mutation["batch_z_second_means"] = [encode(0.0)] * 4
    mutation["raw_sum"][-1] = encode(8 * mean)
    mutation["raw_second_sum"][-1] = encode(0.0)

    direct = V63._validate_j_totals_before_averaging(
        mutation, schedule)
    inherited = V63.v62._validate_j_local_consistency(
        mutation, schedule)
    public = V63.validate_chain_record(
        mutation, spec, schedule, adapter=adapter)
    require(direct is True and inherited is True and public is True,
            "known v6.3 Jensen counterexample unexpectedly rejected")

    # Confirm unrelated sign and overflow edges fail closed.
    signed = copy.deepcopy(mutation)
    signed["batch_z_means"][0] = (-0.0).hex()
    negative_zero_rejects = expect_rejection(
        lambda: V63._validate_j_totals_before_averaging(signed, schedule),
        "signed negative zero")
    overflow = {
        "target": "J",
        "batch_z_means": [encode(sys.float_info.max)] * 4,
        "batch_z_second_means": [encode(0.0)] * 4,
        "raw_sum": [encode(sys.float_info.max)],
        "raw_second_sum": [encode(0.0)],
    }
    overflow_rejects = expect_rejection(
        lambda: V63._validate_j_totals_before_averaging(overflow, schedule),
        "overflowing positive batch sum")
    return {
        "positive_batch_mean": mean.hex(),
        "mean_square": (mean * mean).hex(),
        "serialized_batch_second": (0.0).hex(),
        "inherited_jensen_tolerance_ulps": 64 + 4 * (
            schedule["samples_per_batch"] + 16),
        "pre_total_validator_accepted": direct,
        "inherited_local_validator_accepted": inherited,
        "public_validator_accepted": public,
        "negative_zero_rejects": negative_zero_rejects,
        "overflow_rejects": overflow_rejects,
    }


def main():
    gate = verify_gate()
    adapter, schedule, spec, record = validator_fixture()
    predecessor = verify_predecessor_failures_closed(
        adapter, schedule, spec, record)
    failure = verify_v63_failure(adapter, schedule, spec, record)
    print(json.dumps({
        "status": "AUDIT FAIL",
        "reason": "v6.3 accepts a positive J first moment with an exactly zero second moment",
        "gate_sha256": digest(GATE),
        "source_count": len(gate["source_hashes"]),
        "data_count": len(gate["data_hashes"]),
        "all_predecessor_counterexamples_closed": all(predecessor.values()),
        "predecessor_checks": predecessor,
        "failure": failure,
    }, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
