#!/usr/bin/env python3
"""V6.1: exact per-stratum J-z bounds over the frozen v6 implementation.

The v6 bytes remain preserved as an invalid prelaunch predecessor.  This
wrapper changes no stochastic formula: it adds the missing exact local bound
checks and gives the run a new byte-pinned driver/gate identity.
"""

from __future__ import annotations

import math
from fractions import Fraction
from pathlib import Path

import importance_d4_calibration_v6 as v6


HERE = Path(__file__).resolve()
REPO_ROOT = HERE.parents[3]
DRIVER_RELATIVE = \
    "agents/structural-basis/code/importance_d4_calibration_v61.py"
V6_GATE_RELATIVE = \
    "agents/structural-basis/results/importance_d4_calibration_gate_v6.json"
V6_GATE_SHA256 = \
    "d7ab62d01cc873e732857f1662d40af53624aa1fe36abaaf58bacbe03729521b"
V6_FAILURE_ARTIFACT_HASHES = {
    "agents/audit/IMPORTANCE-D4-CALIBRATION-V6-PRELAUNCH-AUDIT.md":
        "2c2b3ec5887b982185624216d041ecf44531bb0da279271e05a1a77a11d06ff4",
    "agents/audit/verify_importance_d4_calibration_v6.py":
        "b643bd7458e1ecdf3909d33a753fcabe83abbf9305d811d086a5d24030837ce7",
    "agents/audit/test_importance_d4_calibration_v6_j_bounds.py":
        "b278c5a78513e2e5ed017cdff873a519cef44c40a49ed1e076b32dfae41edc3d",
}
FROZEN_V6_EXPECTED_CONVENTIONS = v6.expected_conventions
FROZEN_V6_VALIDATE_CHAIN_RECORD = v6.validate_chain_record
FROZEN_V6_J_ENVELOPE_POINT = v6.j_envelope_point

# Exact Cauchy bounds.  For common stratum r only transformed tagged
# constants r and r+1 can be nonzero; at r=15 only r exists.
J_Z_BOUNDS_EXACT = tuple(Fraction(value) for value in (
    "17/16384", "17/1024", "5/64", "1/8", "1/8", "1/8", "1/8",
    "1/8", "5/64", "5/256", "17/4096", "17/65536",
    "257/16777216", "1025/17179869184",
    "16777217/288230376151711744", "1/288230376151711744"))

ADDITIONAL_SOURCE_PATHS = (
    DRIVER_RELATIVE,
    "agents/structural-basis/code/build_importance_d4_calibration_gate_v61.py",
    "agents/structural-basis/tests/test_importance_d4_calibration_v61.py",
    "agents/structural-basis/IMPORTANCE-D4-CALIBRATION-V61-SPEC.md",
    *V6_FAILURE_ARTIFACT_HASHES,
)
REQUIRED_SOURCE_PATHS = tuple(dict.fromkeys(
    tuple(v6.REQUIRED_SOURCE_PATHS) + ADDITIONAL_SOURCE_PATHS))
REQUIRED_DATA_PATHS = tuple(v6.REQUIRED_DATA_PATHS) + (V6_GATE_RELATIVE,)


def validate_v6_failure_artifacts():
    """Bind the exact independent failure that this successor repairs."""
    for relative, expected in V6_FAILURE_ARTIFACT_HASHES.items():
        if v6.v5.sha256_file(REPO_ROOT / relative) != expected:
            raise ValueError(f"frozen v6 failure artifact changed: {relative}")
    return True


def expected_conventions():
    answer = FROZEN_V6_EXPECTED_CONVENTIONS()
    answer.update({
        "j_z_bound_enforced_per_common_stratum": True,
        "j_z_bounds_exact": [str(value) for value in J_Z_BOUNDS_EXACT],
        "j_z_bound_formula":
            "sum exact transformed tagged-constant weights squared for r,r+1",
        "invalid_prelaunch_v6_gate_sha256": V6_GATE_SHA256,
    })
    return answer


def load_and_validate_gate(path):
    validate_v6_failure_artifacts()
    snapshot = v6.v5.read_file_snapshot(path)
    gate = v6.v5.strict_json_bytes(snapshot["data"], "v6.1 calibration gate")
    v6.v5._exact_keys(gate, {
        "status", "rigorous", "production_launch_authorized",
        "supersedes_invalid_gate_sha256", "float_encoding", "source_hashes",
        "data_hashes", "schedule", "thresholds", "conventions",
        "extension_rule", "continuation_rule"}, "v6.1 calibration gate")
    if (gate["status"] !=
            "frozen-d4-exact-whitened-calibration-prelaunch-v6.1" or
            gate["rigorous"] is not False or
            gate["production_launch_authorized"] is not False or
            gate["supersedes_invalid_gate_sha256"] != V6_GATE_SHA256 or
            gate["float_encoding"] != v6.v5.FLOAT_ENCODING or
            gate["schedule"] != v6.v5.expected_schedule() or
            gate["thresholds"] != v6.v5.expected_thresholds() or
            gate["conventions"] != expected_conventions() or
            gate["extension_rule"] != v6.expected_extension_rule() or
            gate["continuation_rule"] != v6.expected_continuation_rule()):
        raise ValueError("v6.1 gate status, schedule, or conventions changed")
    for field, expected_paths in (
            ("source_hashes", REQUIRED_SOURCE_PATHS),
            ("data_hashes", REQUIRED_DATA_PATHS)):
        table = gate[field]
        if not isinstance(table, dict) or set(table) != set(expected_paths):
            raise ValueError(f"v6.1 {field} has missing or extra paths")
        for relative, expected in table.items():
            if (not isinstance(expected, str) or len(expected) != 64 or
                    any(character not in "0123456789abcdef"
                        for character in expected) or
                    v6.v5.sha256_file(REPO_ROOT / relative) != expected):
                raise ValueError(f"v6.1 dependency mismatch: {relative}")
    if gate["data_hashes"][V6_GATE_RELATIVE] != V6_GATE_SHA256:
        raise ValueError("v6.1 gate does not bind invalid predecessor bytes")
    for relative, expected in V6_FAILURE_ARTIFACT_HASHES.items():
        if gate["source_hashes"].get(relative) != expected:
            raise ValueError("v6.1 gate does not bind frozen v6 failure")
    return {**v6.v5.public_binding(snapshot), "gate": gate}


def _validate_j_stratum_z_bounds(record, schedule, adapter):
    if record.get("target") != "J":
        raise ValueError("J-z validator received a non-J record")
    r = record.get("stratum")
    if isinstance(r, bool) or not isinstance(r, int) or not 0 <= r < 16:
        raise ValueError("J-z record has invalid common stratum")
    expected = sum(
        adapter.base_constant_weights_exact[6 * s] ** 2
        for s in (r, r + 1) if s < 16)
    if expected != J_Z_BOUNDS_EXACT[r]:
        raise ArithmeticError("J-z exact transform-derived bound changed")
    bound = float(expected)
    bound_second = bound * bound
    tolerance = 4096 * math.ulp(bound)
    second_tolerance = 8192 * math.ulp(bound_second)
    means = [v6.v5.parse_float_hex(value, "v6.1 J z batch")
             for value in record["batch_z_means"]]
    seconds = [v6.v5.parse_float_hex(value, "v6.1 J z second batch")
               for value in record["batch_z_second_means"]]
    raw = v6.v5.parse_float_hex(record["raw_sum"][-1], "v6.1 J raw z")
    raw_second = v6.v5.parse_float_hex(
        record["raw_second_sum"][-1], "v6.1 J raw z second")
    if (any(not math.isfinite(value) or
            not 0 <= value <= bound + tolerance for value in means) or
            any(not math.isfinite(value) or
                not 0 <= value <= bound_second + second_tolerance
                for value in seconds) or
            not math.isfinite(raw) or not math.isfinite(raw_second)):
        raise ArithmeticError("J z moment exceeds exact stratum bound")
    sample_count = schedule["batches_per_chain"] * \
        schedule["samples_per_batch"]
    if (not 0 <= raw <= sample_count * (bound + tolerance) or
            not 0 <= raw_second <=
            sample_count * (bound_second + second_tolerance)):
        raise ArithmeticError("J raw z moment exceeds exact stratum bound")
    return True


def j_envelope_point(adapter, common):
    """Apply the exact common-stratum bound at observation time as well."""
    point = FROZEN_V6_J_ENVELOPE_POINT(adapter, common)
    if point is None:
        return None
    r = sum(float(value) > float(adapter.delta) for value in common)
    if not 0 <= r < 16:
        raise ArithmeticError("v6.1 J point has invalid common stratum")
    exact = sum(
        adapter.base_constant_weights_exact[6 * s] ** 2
        for s in (r, r + 1) if s < 16)
    if exact != J_Z_BOUNDS_EXACT[r]:
        raise ArithmeticError("v6.1 pointwise J-z exact bound changed")
    bound = float(exact)
    tolerance = 4096 * math.ulp(bound)
    if (not math.isfinite(point.z) or
            not 0 <= point.z <= bound + tolerance or
            abs(point.z_bound - bound) > tolerance):
        raise ArithmeticError("v6.1 pointwise J z exceeds exact stratum bound")
    return point


def j_envelope_log_density(adapter, common):
    point = j_envelope_point(adapter, common)
    return -math.inf if point is None else point.log_g


def validate_chain_record(record, chain_spec, schedule, *, adapter=None):
    # Run every frozen v6/v5 schema, seed, support, moment, Jensen, and
    # acceptance check first.  The new check only tightens transformed J.
    FROZEN_V6_VALIDATE_CHAIN_RECORD(
        record, chain_spec, schedule, adapter=adapter)
    if record.get("target") == "J":
        if adapter is None:
            raise ValueError("v6.1 J validation requires transformed adapter")
        _validate_j_stratum_z_bounds(record, schedule, adapter)
    return True


def install_runtime():
    """Install v6.1 identities before entering the frozen v6 main loop."""
    v6.DRIVER_RELATIVE = DRIVER_RELATIVE
    v6.REQUIRED_SOURCE_PATHS = REQUIRED_SOURCE_PATHS
    v6.REQUIRED_DATA_PATHS = REQUIRED_DATA_PATHS
    v6.expected_conventions = expected_conventions
    v6.load_and_validate_gate = load_and_validate_gate
    v6.validate_chain_record = validate_chain_record
    v6.j_envelope_point = j_envelope_point
    v6.j_envelope_log_density = j_envelope_log_density


def main():
    install_runtime()
    return v6.main()


if __name__ == "__main__":
    main()
