#!/usr/bin/env python3
"""Fresh hostile verifier for the frozen D4 calibration v6.4 package."""

from __future__ import annotations

import copy
import hashlib
import json
import math
import sys
from pathlib import Path
from types import SimpleNamespace


HERE = Path(__file__).resolve()
REPO = HERE.parents[2]
CODE = REPO / "agents/structural-basis/code"
sys.path[:0] = [str(CODE), str(HERE.parent)]

import importance_d4_calibration_v64 as V64  # noqa: E402
from importance_whitening_v6 import WhitenedC10ImportanceDensity  # noqa: E402


GATE = REPO / "agents/structural-basis/results/importance_d4_calibration_gate_v64.json"
EXPECTED = {
    "agents/structural-basis/code/importance_d4_calibration_v64.py":
        "189177cec83727077e3ce21ae5e56264b08db4479ee8a20f5b5f36db9fb2cbdd",
    "agents/structural-basis/code/build_importance_d4_calibration_gate_v64.py":
        "d55a40144b598bff009a4c1e3cfd1c0f78f4f30125fdfc65efb619f72d44f0ea",
    "agents/structural-basis/tests/test_importance_d4_calibration_v64.py":
        "bd3963224ae9a4cc7435684803c046919c2e8708d70c78c1c43ad286c7a3f728",
    "agents/structural-basis/IMPORTANCE-D4-CALIBRATION-V64-SPEC.md":
        "8e58655c569e01ae49593a4d5ba74fff0e9ae0d8c254bdaa1a7a022bda08495f",
    "agents/structural-basis/results/importance_d4_calibration_gate_v64.json":
        "6fac38311cb0914761c15f8bbab6abca839bf622ab60418df2e9cde7eeb0c8ad",
    "agents/audit/test_importance_d4_calibration_v64_presquare.py":
        "3e387aca92ac30f14dff5f88d5c9de67f17d645e5776fbb0aa55def64890c517",
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
                f"frozen v6.4 hash mismatch: {relative}")
    bound = V64.load_and_validate_gate(GATE)
    gate = bound["gate"]
    require(gate["production_launch_authorized"] is False and
            gate["rigorous"] is False,
            "v6.4 gate unexpectedly authorizes or claims rigor")
    require(gate["supersedes_invalid_gate_sha256"] == V64.V63_GATE_SHA256,
            "v6.4 predecessor binding mismatch")
    for table in (gate["source_hashes"], gate["data_hashes"]):
        for relative, expected in table.items():
            require(digest(REPO / relative) == expected,
                    f"v6.4 gate dependency changed: {relative}")
    for relative, expected in V64.V63_FAILURE_ARTIFACT_HASHES.items():
        require(gate["source_hashes"].get(relative) == expected,
                f"v6.4 omitted frozen v6.3 failure: {relative}")
    return gate


def make_adapter():
    oracle = REPO / V64.v63.v62.v61.v6.REQUIRED_DATA_PATHS[0]
    vector = REPO / V64.v63.v62.v61.v6.REQUIRED_DATA_PATHS[1]
    return WhitenedC10ImportanceDensity(vector, oracle)


def validator_fixture():
    V64.install_runtime()
    V64.v63.v62.v61.v6._patch_v5_runtime()
    adapter = make_adapter()
    schedule = V64.v63.v62.v61.v6.v5.tiny_smoke_schedule()
    spec = V64.v63.v62.v61.v6.v5.expected_chain_table()[124]
    record = V64.v63.v62.v61.v6.v5.run_one_chain(
        adapter, spec, schedule)
    require(V64.validate_chain_record(
        record, spec, schedule, adapter=adapter) is True,
        "valid v6.4 tail record rejected")
    return adapter, schedule, spec, record


def verify_predecessor_attacks(adapter, schedule, spec, record):
    parse = V64.v63.v62.v61.v6.v5.parse_float_hex
    encode = V64.v63.v62.v61.v6.v5.float_hex
    attacks = {}

    mutation = copy.deepcopy(record)
    bound = float(V64.v63.v62.v61.J_Z_BOUNDS_EXACT[15])
    seconds = [parse(value) for value in mutation["batch_z_second_means"]]
    seconds[0] = 2 * bound * bound
    mutation["batch_z_second_means"][0] = encode(seconds[0])
    mutation["raw_second_sum"][-1] = encode(
        schedule["samples_per_batch"] * math.fsum(seconds))
    attacks["v6_upper_bound"] = expect_rejection(
        lambda: V64.validate_chain_record(
            mutation, spec, schedule, adapter=adapter), "v6 upper bound")

    mutation = copy.deepcopy(record)
    mutation["raw_sum"][-1] = encode(0.0)
    attacks["v61_raw_regrouping"] = expect_rejection(
        lambda: V64.validate_chain_record(
            mutation, spec, schedule, adapter=adapter), "v6.1 regrouping")
    mutation = copy.deepcopy(record)
    seconds = [parse(value) for value in mutation["batch_z_second_means"]]
    seconds[0] = 0.0
    mutation["batch_z_second_means"][0] = encode(0.0)
    mutation["raw_second_sum"][-1] = encode(
        schedule["samples_per_batch"] * math.fsum(seconds))
    attacks["v61_local_jensen"] = expect_rejection(
        lambda: V64.validate_chain_record(
            mutation, spec, schedule, adapter=adapter), "v6.1 Jensen")

    tiny = math.ulp(0.0)
    mutation = copy.deepcopy(record)
    mutation["batch_z_means"] = [encode(0.0)] * 4
    mutation["batch_z_second_means"] = [encode(0.0)] * 4
    mutation["raw_sum"][-1] = encode(tiny)
    mutation["raw_second_sum"][-1] = encode(0.0)
    attacks["v62_raw_underflow"] = expect_rejection(
        lambda: V64.validate_chain_record(
            mutation, spec, schedule, adapter=adapter), "v6.2 raw underflow")
    mutation["raw_sum"][-1] = encode(0.0)
    mutation["batch_z_second_means"][0] = encode(tiny)
    mutation["raw_second_sum"][-1] = encode(2 * tiny)
    attacks["v62_batch_underflow"] = expect_rejection(
        lambda: V64.validate_chain_record(
            mutation, spec, schedule, adapter=adapter),
        "v6.2 batch underflow")

    h = float.fromhex("0x1p-537")
    mutation = copy.deepcopy(record)
    mutation["batch_z_means"] = [encode(h)] * 4
    mutation["batch_z_second_means"] = [encode(0.0)] * 4
    mutation["raw_sum"][-1] = encode(8 * h)
    mutation["raw_second_sum"][-1] = encode(0.0)
    attacks["v63_zero_second"] = expect_rejection(
        lambda: V64.validate_chain_record(
            mutation, spec, schedule, adapter=adapter),
        "v6.3 positive first/zero second")
    return attacks


def verify_representation_boundaries():
    encode = V64.v63.v62.v61.v6.v5.float_hex
    minimum_normal = sys.float_info.min
    maximum_subnormal = math.nextafter(minimum_normal, 0.0)
    cases = {
        "positive_zero_passes": V64._resolved_nonnegative(
            [encode(0.0)], "zero") == [0.0],
        "minimum_subnormal_rejects": expect_rejection(
            lambda: V64._resolved_nonnegative(
                [encode(math.ulp(0.0))], "minimum subnormal"),
            "minimum subnormal"),
        "maximum_subnormal_rejects": expect_rejection(
            lambda: V64._resolved_nonnegative(
                [encode(maximum_subnormal)], "maximum subnormal"),
            "maximum subnormal"),
        "minimum_normal_passes": V64._resolved_nonnegative(
            [encode(minimum_normal)], "minimum normal") == [minimum_normal],
        "negative_zero_rejects": expect_rejection(
            lambda: V64._resolved_nonnegative([(-0.0).hex()], "negative zero"),
            "negative zero"),
    }

    # Exact Jensen boundary: mean^2 is the smallest normal number.
    mean = math.sqrt(minimum_normal)
    schedule = {"batches_per_chain": 4, "samples_per_batch": 2}
    record = {
        "target": "J",
        "batch_z_means": [encode(mean)] * 4,
        "batch_z_second_means": [encode(minimum_normal)] * 4,
        "raw_sum": [encode(8 * mean)],
        "raw_second_sum": [encode(8 * minimum_normal)],
    }
    cases["minimum_normal_jensen_boundary_passes"] = all((
        V64._validate_j_first_second_support(record, schedule),
        V64.v63._validate_j_totals_before_averaging(record, schedule),
        V64.v63.v62._validate_j_local_consistency(record, schedule),
    ))

    original = V64.FROZEN_V63_J_ENVELOPE_POINT
    root = math.sqrt(minimum_normal)
    try:
        V64.FROZEN_V63_J_ENVELOPE_POINT = lambda _a, _c: \
            SimpleNamespace(z=math.nextafter(root, 0.0), log_g=0.0)
        cases["point_below_second_normal_boundary_rejects"] = \
            expect_rejection(lambda: V64.j_envelope_point(None, ()),
                             "point below normal-square boundary")
        for label, z in (("at", root),
                         ("above", math.nextafter(root, math.inf))):
            V64.FROZEN_V63_J_ENVELOPE_POINT = \
                lambda _a, _c, z=z: SimpleNamespace(z=z, log_g=0.0)
            cases[f"point_{label}_second_normal_boundary_passes"] = \
                V64.j_envelope_point(None, ()) is not None
    finally:
        V64.FROZEN_V63_J_ENVELOPE_POINT = original
    require(all(cases.values()), "representation boundary check failed")
    return cases


def verify_presquare_failure():
    adapter = make_adapter()
    marginals = [0.0] * adapter.dimension
    marginals[0] = float.fromhex("0x1p-600")
    marginals[1] = 1.0
    adapter.j_support = lambda _common: True
    adapter.j_marginals = lambda _common: tuple(marginals)

    def j_m0(_common, transformed=None):
        values = marginals if transformed is None else transformed
        return math.fsum(
            adapter.base_constant_weights[6 * r] * values[6 * r]
            for r in adapter.strata)

    adapter.j_m0 = j_m0
    common = (0.0,) * 47
    point = V64.j_envelope_point(adapter, common)
    weighted_m0 = math.fsum(
        adapter.base_constant_weights[6 * r] *
        point.unit_marginals[6 * r]
        for r in adapter.strata)
    require(weighted_m0.hex() == "0x1.0000000000000p-607",
            "pre-square weighted-m0 fixture changed")
    require(weighted_m0 != 0 and weighted_m0 * weighted_m0 == 0 and
            point.z == 0,
            "pre-square underflow mechanism changed")
    return {
        "weighted_m0": weighted_m0.hex(),
        "weighted_m0_square": (weighted_m0 * weighted_m0).hex(),
        "returned_point_z": point.z.hex(),
        "v64_point_wrapper_accepted": True,
        "real_base_weight_0": adapter.base_constant_weights[0].hex(),
    }


def main():
    gate = verify_gate()
    adapter, schedule, spec, record = validator_fixture()
    attacks = verify_predecessor_attacks(adapter, schedule, spec, record)
    require(all(attacks.values()), "a predecessor attack was not closed")
    boundaries = verify_representation_boundaries()
    failure = verify_presquare_failure()
    print(json.dumps({
        "status": "AUDIT FAIL",
        "reason": "v6.4 trusts point.z after weighted-m0 squaring has already underflowed to zero",
        "gate_sha256": digest(GATE),
        "source_count": len(gate["source_hashes"]),
        "data_count": len(gate["data_hashes"]),
        "all_v6_through_v63_attacks_closed": all(attacks.values()),
        "predecessor_checks": attacks,
        "boundary_checks": boundaries,
        "failure": failure,
    }, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
