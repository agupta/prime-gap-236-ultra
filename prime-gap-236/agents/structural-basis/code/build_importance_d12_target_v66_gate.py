#!/usr/bin/env python3
"""Build a production-disabled D12/v6.6 identity-and-baseline gate."""

from __future__ import annotations

import argparse
from pathlib import Path

import importance_d12_target_v66 as target


HERE = Path(__file__).resolve()
REPO_ROOT = HERE.parents[3]
D4_GATE_RELATIVE = \
    "agents/structural-basis/results/importance_d4_calibration_gate_v66.json"
D4_GATE_SHA256 = \
    "fa1019605ef6b5efd486b234451806efcf1912f7b3f181c9511839d873b63bf6"
SOURCE_PATHS = (
    "agents/structural-basis/code/importance_d12_target_v6.py",
    "agents/structural-basis/code/importance_d12_target_v66.py",
    "agents/structural-basis/code/build_importance_d12_target_v66_gate.py",
    "agents/structural-basis/tests/test_importance_d12_target_v66.py",
    "agents/structural-basis/IMPORTANCE-D12-TARGET-V66-SPEC.md",
    *target.V66_AUDIT_ARTIFACT_HASHES,
)


def _sha(value, name):
    if (not isinstance(value, str) or len(value) != 64 or
            any(character not in "0123456789abcdef" for character in value)):
        raise ValueError(f"{name} is not canonical lowercase SHA-256")
    return value


def build_gate(expected_self_sha256, d4_gate_path):
    expected_self_sha256 = _sha(expected_self_sha256, "target builder SHA")
    if target.core.sha256_file(HERE) != expected_self_sha256:
        raise ValueError("executed target builder differs from trust root")
    target.validate_v66_audit_artifacts()
    d4_bound = target.d4.load_and_validate_gate(d4_gate_path)
    d4_gate = d4_bound["gate"]
    d4_gate_sha = target.core.sha256_file(d4_gate_path)
    if (d4_bound["sha256"] != D4_GATE_SHA256 or
            d4_gate_sha != D4_GATE_SHA256 or
            Path(d4_gate_path).resolve() !=
            (REPO_ROOT / D4_GATE_RELATIVE).resolve()):
        raise ValueError("D4 v6.6 gate path or bytes changed")
    if (d4_gate["status"] !=
            "frozen-d4-exact-whitened-calibration-prelaunch-v6.6" or
            d4_gate["production_launch_authorized"] is not False):
        raise ValueError("D4 v6.6 gate is not the frozen disabled gate")
    source_hashes = dict(d4_gate["source_hashes"])
    for relative in SOURCE_PATHS:
        source_hashes[relative] = target.core.sha256_file(REPO_ROOT / relative)
    if source_hashes[str(HERE.relative_to(REPO_ROOT))] != expected_self_sha256:
        raise ArithmeticError("target builder missing from source closure")
    for relative, expected in target.V66_AUDIT_ARTIFACT_HASHES.items():
        if source_hashes.get(relative) != expected:
            raise ArithmeticError("target gate does not bind v6.6 PASS")
    data_hashes = dict(d4_gate["data_hashes"])
    for relative, expected in target.EXPECTED_HASHES.items():
        if target.core.sha256_file(REPO_ROOT / relative) != expected:
            raise ValueError(f"D12 target dependency changed: {relative}")
        data_hashes[relative] = expected
    data_hashes[D4_GATE_RELATIVE] = d4_gate_sha
    package = target.exact_identity_package(REPO_ROOT)
    normalizers = package["normalizers"]
    return {
        "status": "frozen-d12-transformed-target-identity-prelaunch-v6.6",
        "rigorous": False,
        "screen_launch_authorized": False,
        "identity_dry_run_only": True,
        "d4_v66_gate_path": D4_GATE_RELATIVE,
        "d4_v66_gate_sha256": d4_gate_sha,
        "requires_independently_audited_d4_v66_calibration_pass": True,
        "transform_sha256":
            target.d4.v65.v64.v63.v62.v61.v6.TRANSFORM_SHA256,
        "base_target": {
            "semantics": "unmultiplied-272-label-D12-polynomial",
            "source_sha256": target.EXPECTED_HASHES[
                target.core.D12_SOURCE_RELATIVE],
            "integer_scaled_sha256": target.EXPECTED_HASHES[
                target.core.D12_INTEGER_RELATIVE],
            "k": 48, "degree": 12, "basis_dimension": 272,
        },
        "exact_identity": package["identity"],
        "exact_identity_sha256": package["identity_sha256"],
        "normalizers": {
            "raw_sha256": normalizers["raw_sha256"],
            "recovered_sha256": normalizers["recovered_sha256"],
            "baseline_sha256": normalizers["baseline_sha256"],
            "i_strata": 16, "j_common_strata": 16,
            "j_scale_to_numerator": 48,
            "base_quotient": str(normalizers["base_quotient"]),
            "sum_internal_relative_tolerance":
                str(target.core.SUM_INTERNAL_RELATIVE_TOLERANCE),
            "baseline_relative_tolerance":
                str(target.core.BASELINE_RELATIVE_TOLERANCE),
            "observed_relative_errors": {
                key: str(value)
                for key, value in normalizers["relative_errors"].items()},
        },
        "source_hashes": source_hashes,
        "data_hashes": data_hashes,
        "schedule":
            target.d4.v65.v64.v63.v62.v61.v6.v5.expected_schedule(),
        "unchanged_statistical_thresholds":
            target.d4.v65.v64.v63.v62.v61.v6.v5.expected_thresholds(),
        "data_split": {
            "training_replicates": [0, 1],
            "validation_replicates": [2, 3],
            "candidate_selection_uses_validation": False,
            "delete_each_validation_chain": True,
        },
        "cost_gate": {
            "estimated_cpu_seconds": 12832,
            "parallel_workers": 2,
            "estimated_wall_seconds": 6416,
            "wall_guard_seconds": 7058,
            "maximum_authorizable_wall_seconds": 7200,
            "estimated_peak_rss_kib_per_process": 43008,
            "maximum_authorizable_peak_rss_kib": 1048576,
            "estimate_is_not_a_completed_screen": True,
        },
        "continuation_rule":
            target.d4.v65.v64.v63.v62.v61.v6.expected_continuation_rule(),
        "next_stage": {
            "same_d4_driver_accepts_d12": False,
            "separate_d12_screen_driver_required": True,
            "separate_root_authorization_required": True,
            "screen_command": None,
        },
        "scalar_input_schema": {
            "consumer":
                "agents/exact-integrator/stratum_quadratic_transfer_decimal.py",
            "base_k": 48, "base_basis_dimension": 272,
            "multiplier_status": "exact-stratum-quadratic-rational-vector",
            "multiplier_k": 48, "multiplier_dimension": 96,
            "multiplier_labels":
                "all [r,1/L/Z/L^2/LZ/Z^2], r=0..15, in that order",
            "rational_vector_semantics": "exact old coordinates T*c_new",
            "fresh_grouped_reconstruction_required": True,
        },
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--expected-self-sha256", required=True)
    parser.add_argument("--d4-gate", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    gate = build_gate(args.expected_self_sha256, args.d4_gate)
    target.d4.install_runtime()
    target.d4.v65.v64.v63.v62.v61.v6._patch_v5_runtime()
    target.d4.v65.v64.v63.v62.v61.v6.v5.REQUIRED_SOURCE_PATHS = \
        tuple(gate["source_hashes"])
    target.d4.v65.v64.v63.v62.v61.v6.v5.REQUIRED_DATA_PATHS = \
        tuple(gate["data_hashes"])
    digest = target.d4.v65.v64.v63.v62.v61.v6.v5.write_new_result(
        args.output, gate, gate)
    print(digest)


if __name__ == "__main__":
    main()
