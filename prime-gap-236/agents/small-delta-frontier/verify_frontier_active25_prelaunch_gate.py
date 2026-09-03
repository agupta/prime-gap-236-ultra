#!/usr/bin/env python3
"""Fail-closed verifier for the disabled active-count-25 resource gate."""

from __future__ import annotations

from decimal import Decimal
from fractions import Fraction as Q
import hashlib
import importlib.util
import json
from pathlib import Path
import sys


FILE = Path(__file__).resolve()
HERE = FILE.parent
CORE = HERE / "frontier_active25_inner_d16_tagged_shell.py"
TEST = HERE / "test_frontier_active25_inner_d16_tagged_shell.py"
GATE = HERE / "results/frontier_active25_innerD16_tagged_shell_prelaunch_gate.json"
ORACLE = HERE / "results/frontier_active25_innerD16_shell_cross_r10_h10_ungrouped_oracle.json"
DIRECT = HERE / "results/frontier_active25_innerD16_shell_cross_r10_h10_direct_v2.json"
PROBES = {
    (0, 17): HERE / "results/frontier_active25_innerD16_shell_cross_r00_h17_direct_v2.json",
    (5, 15): HERE / "results/frontier_active25_innerD16_shell_cross_r05_h15_direct_v2.json",
    (10, 10): DIRECT,
    (15, 10): HERE / "results/frontier_active25_innerD16_shell_cross_r15_h10_direct_v2.json",
    (22, 6): HERE / "results/frontier_active25_innerD16_shell_cross_r22_h06_direct_v2.json",
    (25, 5): HERE / "results/frontier_active25_innerD16_shell_cross_r25_h05_direct_v2.json",
}
PINS = {
    CORE: "1393a2dd29e5660f10e632b19b6b5eeafe9363bf79b2cd4a8254049d1f9c669a",
    TEST: "a9c822357bb2cb9225030b0df46f11bca225ec05158e48ee0d57ff2394f7071f",
    GATE: "1642a5efcc4e2b304271fe3b785d439ce9b1ddb405855f56a7e62a1b4e61e6ac",
    ORACLE: "f97e16231e47d028406a88702631457fb110fe1cf00fcb9a2a4ba71557dbc21c",
    DIRECT: "37b0d249a0fd17e823f154277bfabe162c3b80c72c344c97686312c7fac7e393",
    PROBES[(0, 17)]: "73f351f24defafc0cb6c0a293d258bac33d504e457771ea11362ff5d67bd9107",
    PROBES[(5, 15)]: "5603845bf7514a4f6dcb4831ed3854b1915189d39424d9d1b47f2bc6f2cd1901",
    PROBES[(15, 10)]: "5f4d88417ed0b84d26c52512ddf710b35bd9e7d55e9df4a68ad2114dc3602d29",
    PROBES[(22, 6)]: "8e023686703d353bb63faad3be541238920bc8b7640a4ba3202b924d0385ace9",
    PROBES[(25, 5)]: "9c13277024543c51b2c945743ce74c5ebfc5b1d2eb3e21d264740bcf0e35e6df",
}


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_pinned(path: Path) -> bytes:
    data = path.read_bytes()
    if sha256(data) != PINS[path]:
        raise RuntimeError(f"pinned byte mismatch: {path}")
    return data


def strict_object(value, keys, name):
    if type(value) is not dict or set(value) != set(keys):
        raise ValueError(f"{name} schema mismatch")


def load_core():
    spec = importlib.util.spec_from_file_location("active25_gate_core", CORE)
    if spec is None or spec.loader is None:
        raise ImportError(CORE)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def main():
    snapshots = {path: read_pinned(path) for path in PINS}
    core = load_core()
    analytic = core.validate_analytic()
    active = analytic["parameters"]["outer_active"]
    if active != list(range(26)) or 1 + len(active) != 27:
        raise ArithmeticError("active-count/dimension derivation failed")

    gate = json.loads(snapshots[GATE])
    strict_object(gate, {
        "active_outer_counts", "analytic_audit_sha256",
        "arithmetic_core_sha256", "arithmetic_test_sha256",
        "benchmark_artifacts", "cross_face_count", "dimension", "format",
        "grouped_geometric_domain_upper", "launch_authorized",
        "literal_branch_product_upper", "max_observed_face_wall_seconds",
        "max_observed_peak_rss_kib", "oracle_artifact_sha256",
        "oracle_direct_exact_equal", "projected_one_worker_seconds",
        "resource_gate", "rss_envelope_kib", "schedule_canonical_sha256",
        "stage_common_r", "status", "wall_envelope_seconds"}, "gate")
    expected_fixed = {
        "active_outer_counts": active,
        "analytic_audit_sha256": core.PINNED[core.ANALYTIC],
        "arithmetic_core_sha256": PINS[CORE],
        "arithmetic_test_sha256": PINS[TEST],
        "cross_face_count": 585,
        "dimension": 27,
        "format": "frontier-active25-inner-D16-tagged-shell-prelaunch-gate-v1",
        "grouped_geometric_domain_upper": 7731,
        "launch_authorized": False,
        "literal_branch_product_upper": 37024,
        "oracle_artifact_sha256": PINS[ORACLE],
        "oracle_direct_exact_equal": True,
        "rss_envelope_kib": 152640,
        "schedule_canonical_sha256":
            analytic["parameters"]["outer_schedule_canonical_sha256"],
        "stage_common_r": active,
        "status": "PRELAUNCH DISABLED PENDING INDEPENDENT IMPLEMENTATION AUDIT",
    }
    for key, value in expected_fixed.items():
        if gate[key] != value or type(gate[key]) is not type(value):
            raise ValueError(f"gate field mismatch: {key}")
    strict_object(gate["resource_gate"], {
        "max_total_wall_seconds", "minimum_mem_available_kib_each_reading",
        "required_stable_mem_readings", "rss_safety_factor",
        "wall_safety_factor", "workers"}, "resource gate")
    if gate["resource_gate"] != {
            "max_total_wall_seconds": 14400,
            "minimum_mem_available_kib_each_reading": 1400000,
            "required_stable_mem_readings": 2,
            "rss_safety_factor": 4,
            "wall_safety_factor": 3,
            "workers": 1}:
        raise ValueError("resource policy mismatch")

    rows = gate["benchmark_artifacts"]
    if type(rows) is not list or len(rows) != len(PROBES):
        raise ValueError("benchmark list mismatch")
    observed_wall = []
    observed_rss = []
    for row in rows:
        strict_object(row, {"common_r", "h", "peak_rss_kib", "sha256",
                            "wall_seconds"}, "benchmark row")
        key = (row["common_r"], row["h"])
        if key not in PROBES or row["sha256"] != PINS[PROBES[key]]:
            raise ValueError("benchmark identity mismatch")
        payload = json.loads(snapshots[PROBES[key]])
        if (payload.get("script_sha256") != PINS[CORE] or
                payload.get("evaluation_mode") != "direct-full-grouped" or
                payload.get("common_r") != key[0] or
                payload.get("selected_h") != key[1] or
                payload.get("parameters") != core.parameter_record() or
                type(payload.get("peak_rss_kib")) is not int or
                payload["peak_rss_kib"] != row["peak_rss_kib"] or
                str(payload.get("wall_seconds")) != row["wall_seconds"]):
            raise ValueError("benchmark payload mismatch")
        observed_wall.append(Decimal(row["wall_seconds"]))
        observed_rss.append(row["peak_rss_kib"])

    maximum = max(observed_wall)
    projected = maximum * Decimal(gate["cross_face_count"])
    if (Decimal(gate["max_observed_face_wall_seconds"]) != maximum or
            Decimal(gate["projected_one_worker_seconds"]) != projected or
            Decimal(gate["wall_envelope_seconds"]) !=
            projected * gate["resource_gate"]["wall_safety_factor"] or
            gate["max_observed_peak_rss_kib"] != max(observed_rss) or
            gate["rss_envelope_kib"] !=
            max(observed_rss) * gate["resource_gate"]["rss_safety_factor"] or
            Decimal(gate["wall_envelope_seconds"]) >=
            gate["resource_gate"]["max_total_wall_seconds"]):
        raise ArithmeticError("resource arithmetic mismatch")

    oracle = json.loads(snapshots[ORACLE])
    direct = json.loads(snapshots[DIRECT])
    if (oracle.get("evaluation_mode") != "ungrouped-four-branch-oracle" or
            direct.get("evaluation_mode") != "direct-full-grouped" or
            oracle.get("script_sha256") != PINS[CORE] or
            direct.get("script_sha256") != PINS[CORE] or
            oracle.get("parameters") != direct.get("parameters") or
            [Q(x) for x in oracle["radial_cross_by_target_R"]] !=
            [Q(x) for x in direct["radial_cross_by_target_R"]]):
        raise ArithmeticError("oracle/direct equality mismatch")

    # Rebind every input after all validation.  This also catches a source or
    # cost-artifact mutation during the check.
    if any(path.read_bytes() != data for path, data in snapshots.items()):
        raise RuntimeError("input changed during gate verification")
    print("AUDIT PASS: disabled active25 resource gate and exact oracle equality")


if __name__ == "__main__":
    main()
