#!/usr/bin/env python3
"""Independent compact verifier for the frozen v6.2 underflow failure."""

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

import importance_d4_calibration_v62 as V62  # noqa: E402
from importance_whitening_v6 import WhitenedC10ImportanceDensity  # noqa: E402


GATE = REPO / "agents/structural-basis/results/importance_d4_calibration_gate_v62.json"
EXPECTED = {
    "agents/structural-basis/code/importance_d4_calibration_v62.py":
        "031f244728fd5ff4df041bb50bfa006bd3bab6724d2c9e3bb82298882f54c63a",
    "agents/structural-basis/code/build_importance_d4_calibration_gate_v62.py":
        "53365198be4a959ad327a9cba59e2be3f4343ea563022ea48c751e236abad690",
    "agents/structural-basis/tests/test_importance_d4_calibration_v62.py":
        "3b9c98665488bfbfe6d7406812198f4c16bb30fc39e7201845390b2fa500ba2e",
    "agents/structural-basis/IMPORTANCE-D4-CALIBRATION-V62-SPEC.md":
        "1ffe7458d400c88d6aa297b3925c9bf1a2938c385dc26458a6bacfbd45e6103b",
    "agents/structural-basis/results/importance_d4_calibration_gate_v62.json":
        "3642ace1f95b13e32259190ccb1690d726fcc2bd7cbda3298875a6f14d082bca",
    "agents/audit/test_importance_d4_calibration_v62_underflow.py":
        "bb2a1aa0689d1d351fb094e4cb2b3133ba6e5fd3e267423766cff5f8c1dc0dd8",
}


class AuditFailure(RuntimeError):
    pass


def require(condition, message):
    if not condition:
        raise AuditFailure(message)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def verify_frozen_gate():
    for relative, expected in EXPECTED.items():
        require(digest(REPO / relative) == expected,
                f"frozen v6.2 hash mismatch: {relative}")
    bound = V62.load_and_validate_gate(GATE)
    gate = bound["gate"]
    require(gate["production_launch_authorized"] is False,
            "v6.2 gate unexpectedly authorizes production")
    require(gate["rigorous"] is False,
            "v6.2 gate unexpectedly claims rigor")
    require(gate["supersedes_invalid_gate_sha256"] == V62.V61_GATE_SHA256,
            "v6.2 predecessor binding changed")
    for table in (gate["source_hashes"], gate["data_hashes"]):
        for relative, expected in table.items():
            require(digest(REPO / relative) == expected,
                    f"gate dependency changed: {relative}")
    return gate


def short_record(*, raw, raw_second, means, seconds):
    encode = V62.v61.v6.v5.float_hex
    return {
        "target": "J",
        "batch_z_means": [encode(value) for value in means],
        "batch_z_second_means": [encode(value) for value in seconds],
        "raw_sum": [encode(raw)],
        "raw_second_sum": [encode(raw_second)],
    }


def verify_underflow_counterexamples():
    tiny = math.ulp(0.0)
    zero = 0.0
    schedule = {"batches_per_chain": 4, "samples_per_batch": 2}
    require(tiny > 0 and tiny / 8 == 0,
            "binary64 minimum-subnormal fixture changed")
    require(2 * tiny > 0 and 2 * tiny / 8 == 0,
            "binary64 second-moment fixture changed")

    fixtures = {
        "positive_raw_first_lost": short_record(
            raw=tiny, raw_second=zero,
            means=[zero] * 4, seconds=[zero] * 4),
        "positive_raw_second_lost": short_record(
            raw=zero, raw_second=tiny,
            means=[zero] * 4, seconds=[zero] * 4),
        "positive_batch_second_lost": short_record(
            raw=zero, raw_second=2 * tiny,
            means=[zero] * 4, seconds=[tiny, zero, zero, zero]),
    }
    accepted = {}
    for label, record in fixtures.items():
        accepted[label] = V62._validate_j_local_consistency(record, schedule)
        require(accepted[label] is True,
                f"known v6.2 counterexample unexpectedly rejected: {label}")

    # Exercise the public wrapper without storing or printing the large chain.
    V62.install_runtime()
    V62.v61.v6._patch_v5_runtime()
    oracle = REPO / V62.v61.v6.REQUIRED_DATA_PATHS[0]
    vector = REPO / V62.v61.v6.REQUIRED_DATA_PATHS[1]
    adapter = WhitenedC10ImportanceDensity(vector, oracle)
    smoke = V62.v61.v6.v5.tiny_smoke_schedule()
    spec = V62.v61.v6.v5.expected_chain_table()[124]
    record = V62.v61.v6.v5.run_one_chain(adapter, spec, smoke)
    require(V62.validate_chain_record(
        record, spec, smoke, adapter=adapter) is True,
        "valid tail smoke record rejected")
    mutated = copy.deepcopy(record)
    encoded_zero = V62.v61.v6.v5.float_hex(0.0)
    mutated["batch_z_means"] = [encoded_zero] * 4
    mutated["batch_z_second_means"] = [encoded_zero] * 4
    mutated["raw_sum"][-1] = V62.v61.v6.v5.float_hex(tiny)
    mutated["raw_second_sum"][-1] = encoded_zero
    public_accepted = V62.validate_chain_record(
        mutated, spec, smoke, adapter=adapter)
    require(public_accepted is True,
            "known v6.2 public counterexample unexpectedly rejected")

    return {
        "minimum_positive_binary64": tiny.hex(),
        "sample_count": 8,
        "positive_raw_divides_to": (tiny / 8).hex(),
        "positive_second_divides_to": (2 * tiny / 8).hex(),
        "local_tolerance_after_loss": V62._local_roundoff_tolerance(
            0.0, 0.0, 30).hex(),
        "accepted_short_fixtures": sorted(accepted),
        "public_validator_accepted": public_accepted,
    }


def main():
    gate = verify_frozen_gate()
    failure = verify_underflow_counterexamples()
    print(json.dumps({
        "status": "AUDIT FAIL",
        "reason": "v6.2 divides positive serialized J totals/aggregates to zero before comparing them",
        "gate_sha256": digest(GATE),
        "source_count": len(gate["source_hashes"]),
        "data_count": len(gate["data_hashes"]),
        "failure": failure,
    }, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
