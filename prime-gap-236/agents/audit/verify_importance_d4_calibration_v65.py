#!/usr/bin/env python3
"""Fresh hostile verifier for the frozen D4 calibration v6.5 package."""

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
sys.path.insert(0, str(CODE))

import importance_d4_calibration_v65 as V65  # noqa: E402
from importance_whitening_v6 import WhitenedC10ImportanceDensity  # noqa: E402


GATE = REPO / "agents/structural-basis/results/importance_d4_calibration_gate_v65.json"
EXPECTED = {
    "agents/structural-basis/code/importance_d4_calibration_v65.py":
        "6e6e74569dc707fc384b6774cd96d9407dcd7176ce1115ca395201d02dd12945",
    "agents/structural-basis/code/build_importance_d4_calibration_gate_v65.py":
        "00ecdddf83775a81d5f075911de664d896f2064960e15b7e070e26eaa8ff25f5",
    "agents/structural-basis/tests/test_importance_d4_calibration_v65.py":
        "486985bff8780ae85d04f2976240eb0004880ccdf1a9ace36f706fd061615e00",
    "agents/structural-basis/IMPORTANCE-D4-CALIBRATION-V65-SPEC.md":
        "66e1175d31f54b119833b6c238002b69d03bfb8e6972e579da885f862096313e",
    "agents/structural-basis/results/importance_d4_calibration_gate_v65.json":
        "5aec092841721a8e54292eb631e43c5e298088960e4031e7528df6272def905a",
    "agents/audit/test_importance_d4_calibration_v65_square_overflow.py":
        "f400f250b6485a4d77f02a346eae319cea3f4283acadf5630d32c5aa873c8ad2",
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
                f"frozen v6.5 hash mismatch: {relative}")
    bound = V65.load_and_validate_gate(GATE)
    gate = bound["gate"]
    require(gate["production_launch_authorized"] is False and
            gate["rigorous"] is False,
            "v6.5 gate unexpectedly authorizes or claims rigor")
    require(gate["supersedes_invalid_gate_sha256"] == V65.V64_GATE_SHA256,
            "v6.5 predecessor binding mismatch")
    for table in (gate["source_hashes"], gate["data_hashes"]):
        for relative, expected in table.items():
            require(digest(REPO / relative) == expected,
                    f"v6.5 gate dependency changed: {relative}")
    for relative, expected in V65.V64_FAILURE_ARTIFACT_HASHES.items():
        require(gate["source_hashes"].get(relative) == expected,
                f"v6.5 omitted frozen v6.4 failure: {relative}")
    return gate


def make_adapter():
    oracle = REPO / V65.v64.v63.v62.v61.v6.REQUIRED_DATA_PATHS[0]
    vector = REPO / V65.v64.v63.v62.v61.v6.REQUIRED_DATA_PATHS[1]
    return WhitenedC10ImportanceDensity(vector, oracle)


def synthetic_adapter(marginals):
    adapter = make_adapter()
    adapter.j_support = lambda _common: True
    adapter.j_marginals = lambda _common: tuple(marginals)

    def j_m0(_common, transformed=None):
        values = marginals if transformed is None else transformed
        return math.fsum(
            adapter.base_constant_weights[6 * r] * values[6 * r]
            for r in adapter.strata)

    adapter.j_m0 = j_m0
    return adapter


def validator_fixture():
    V65.install_runtime()
    V65.v64.v63.v62.v61.v6._patch_v5_runtime()
    adapter = make_adapter()
    schedule = V65.v64.v63.v62.v61.v6.v5.tiny_smoke_schedule()
    spec = V65.v64.v63.v62.v61.v6.v5.expected_chain_table()[124]
    record = V65.v64.v63.v62.v61.v6.v5.run_one_chain(
        adapter, spec, schedule)
    require(V65.validate_chain_record(
        record, spec, schedule, adapter=adapter) is True,
        "valid v6.5 tail record rejected")
    require(V65.v64.v63.v62.v61.v6.validate_chain_record is
            V65.validate_chain_record and
            V65.v64.v63.v62.v61.v6.v5.validate_chain_record is
            V65.validate_chain_record,
            "v6.5 record wrapper did not reach inherited runtime")
    return adapter, schedule, spec, record


def verify_record_attack_corpus(adapter, schedule, spec, record):
    parse = V65.v64.v63.v62.v61.v6.v5.parse_float_hex
    encode = V65.v64.v63.v62.v61.v6.v5.float_hex
    attacks = {}
    mutation = copy.deepcopy(record)
    bound = float(V65.v64.v63.v62.v61.J_Z_BOUNDS_EXACT[15])
    seconds = [parse(value) for value in mutation["batch_z_second_means"]]
    seconds[0] = 2 * bound * bound
    mutation["batch_z_second_means"][0] = encode(seconds[0])
    mutation["raw_second_sum"][-1] = encode(
        schedule["samples_per_batch"] * math.fsum(seconds))
    attacks["v6_upper_bound"] = expect_rejection(
        lambda: V65.validate_chain_record(
            mutation, spec, schedule, adapter=adapter), "v6 upper bound")
    mutation = copy.deepcopy(record)
    mutation["raw_sum"][-1] = encode(0.0)
    attacks["v61_raw_regrouping"] = expect_rejection(
        lambda: V65.validate_chain_record(
            mutation, spec, schedule, adapter=adapter), "v6.1 regrouping")
    mutation = copy.deepcopy(record)
    seconds = [parse(value) for value in mutation["batch_z_second_means"]]
    seconds[0] = 0.0
    mutation["batch_z_second_means"][0] = encode(0.0)
    mutation["raw_second_sum"][-1] = encode(
        schedule["samples_per_batch"] * math.fsum(seconds))
    attacks["v61_jensen"] = expect_rejection(
        lambda: V65.validate_chain_record(
            mutation, spec, schedule, adapter=adapter), "v6.1 Jensen")
    tiny = math.ulp(0.0)
    mutation = copy.deepcopy(record)
    mutation["batch_z_means"] = [encode(0.0)] * 4
    mutation["batch_z_second_means"] = [encode(0.0)] * 4
    mutation["raw_sum"][-1] = encode(tiny)
    mutation["raw_second_sum"][-1] = encode(0.0)
    attacks["v62_raw_underflow"] = expect_rejection(
        lambda: V65.validate_chain_record(
            mutation, spec, schedule, adapter=adapter), "v6.2 raw underflow")
    mutation["raw_sum"][-1] = encode(0.0)
    mutation["batch_z_second_means"][0] = encode(tiny)
    mutation["raw_second_sum"][-1] = encode(2 * tiny)
    attacks["v62_batch_underflow"] = expect_rejection(
        lambda: V65.validate_chain_record(
            mutation, spec, schedule, adapter=adapter),
        "v6.2 batch underflow")
    h = float.fromhex("0x1p-537")
    mutation = copy.deepcopy(record)
    mutation["batch_z_means"] = [encode(h)] * 4
    mutation["batch_z_second_means"] = [encode(0.0)] * 4
    mutation["raw_sum"][-1] = encode(8 * h)
    mutation["raw_second_sum"][-1] = encode(0.0)
    attacks["v63_zero_second"] = expect_rejection(
        lambda: V65.validate_chain_record(
            mutation, spec, schedule, adapter=adapter), "v6.3 zero second")
    return attacks


def verify_v64_and_signed_edges():
    common = (0.0,) * 47
    edges = {}
    for sign in (1.0, -1.0):
        marginals = [0.0] * 96
        marginals[0] = sign * float.fromhex("0x1p-600")
        marginals[1] = 1.0
        adapter = synthetic_adapter(marginals)
        edges[f"v64_presquare_sign_{int(sign)}"] = expect_rejection(
            lambda adapter=adapter: V65.j_envelope_point(adapter, common),
            f"v6.4 pre-square sign {sign}")

    # Exact signed cancellation of the two allowed tagged channels is valid.
    marginals = [0.0] * 96
    marginals[0], marginals[6] = 1.0, -0.25
    adapter = synthetic_adapter(marginals)
    point = V65.j_envelope_point(adapter, common)
    weighted, square = V65._weighted_m0_and_square(adapter, point)
    edges["exact_cancellation_passes"] = (
        weighted == 0 and square == 0 and point.z == 0)

    adapter = make_adapter()
    for sign in (1.0, -1.0):
        unit = [0.0] * 96
        unit[0] = sign * math.ulp(0.0)
        point = SimpleNamespace(unit_marginals=tuple(unit))
        edges[f"tagged_product_underflow_sign_{int(sign)}"] = \
            expect_rejection(
                lambda point=point: V65._weighted_m0_and_square(adapter, point),
                f"tagged product underflow sign {sign}")

    # The smallest resolved weighted square is accepted with either sign.
    for sign in (1.0, -1.0):
        unit = [0.0] * 96
        unit[0] = sign * float.fromhex("0x1p-504")
        point = SimpleNamespace(unit_marginals=tuple(unit))
        weighted, square = V65._weighted_m0_and_square(adapter, point)
        edges[f"normal_square_boundary_sign_{int(sign)}"] = (
            abs(weighted) == float.fromhex("0x1p-511") and
            square == sys.float_info.min)
    require(all(edges.values()), "signed/cancellation boundary check failed")
    return edges


def verify_square_overflow_failure():
    adapter = make_adapter()
    unit = [0.0] * 96
    unit[0] = sys.float_info.max
    point = SimpleNamespace(
        unit_marginals=tuple(unit), z=0.125, log_g=0.0)
    weighted, square = V65._weighted_m0_and_square(adapter, point)
    require(math.isfinite(weighted) and math.isinf(square),
            "v6.5 square-overflow fixture changed")
    original = V65.FROZEN_V64_J_ENVELOPE_POINT
    V65.FROZEN_V64_J_ENVELOPE_POINT = lambda _adapter, _common: point
    try:
        accepted = V65.j_envelope_point(adapter, ())
    finally:
        V65.FROZEN_V64_J_ENVELOPE_POINT = original
    require(accepted is point,
            "known v6.5 overflow counterexample unexpectedly rejected")
    tolerance = 16 * max(math.ulp(point.z), math.ulp(square))
    discrepancy = abs(point.z - square)
    return {
        "finite_weighted_m0": weighted.hex(),
        "recomputed_square": str(square),
        "recorded_z": point.z.hex(),
        "comparison_tolerance": str(tolerance),
        "comparison_discrepancy": str(discrepancy),
        "python_inf_gt_inf": discrepancy > tolerance,
        "public_wrapper_accepted": True,
    }


def main():
    gate = verify_gate()
    adapter, schedule, spec, record = validator_fixture()
    attacks = verify_record_attack_corpus(adapter, schedule, spec, record)
    require(all(attacks.values()), "a v6-v6.3 attack was not closed")
    edges = verify_v64_and_signed_edges()
    failure = verify_square_overflow_failure()
    print(json.dumps({
        "status": "AUDIT FAIL",
        "reason": "v6.5 permits an infinite recomputed square and then compares infinity to infinity",
        "gate_sha256": digest(GATE),
        "source_count": len(gate["source_hashes"]),
        "data_count": len(gate["data_hashes"]),
        "all_v6_through_v64_attacks_closed":
            all(attacks.values()) and edges["v64_presquare_sign_1"] and
            edges["v64_presquare_sign_-1"],
        "record_attack_checks": attacks,
        "signed_and_cancellation_checks": edges,
        "failure": failure,
    }, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
