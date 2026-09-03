#!/usr/bin/env python3
"""Build the production-disabled D12 transformed-target manifest."""

from __future__ import annotations

import argparse
from pathlib import Path

import importance_d12_target_v6 as d12
import importance_d4_calibration_v6 as d4


HERE = Path(__file__).resolve()
REPO_ROOT = HERE.parents[3]
D4_GATE_RELATIVE = \
    "agents/structural-basis/results/importance_d4_calibration_gate_v6.json"
ADDITIONAL_SOURCE_PATHS = (
    "agents/structural-basis/code/importance_d12_target_v6.py",
    "agents/structural-basis/code/build_importance_d12_target_v6_gate.py",
    "agents/structural-basis/tests/test_importance_d12_target_v6.py",
    "agents/structural-basis/IMPORTANCE-D12-TARGET-V6-SPEC.md",
)


def _canonical_sha(value, name):
    if (not isinstance(value, str) or len(value) != 64 or
            any(character not in "0123456789abcdef" for character in value)):
        raise ValueError(f"{name} is not a canonical SHA-256")
    return value


def build_gate(expected_self_sha256, d4_gate_path):
    expected_self_sha256 = _canonical_sha(
        expected_self_sha256, "expected target-gate builder SHA")
    if d12.sha256_file(HERE) != expected_self_sha256:
        raise ValueError("executed target-gate builder differs from trust root")
    d4_bound = d4.load_and_validate_gate(d4_gate_path)
    d4_gate = d4_bound["gate"]
    source_hashes = dict(d4_gate["source_hashes"])
    for relative in ADDITIONAL_SOURCE_PATHS:
        source_hashes[relative] = d12.sha256_file(REPO_ROOT / relative)
    if source_hashes[str(HERE.relative_to(REPO_ROOT))] != expected_self_sha256:
        raise ArithmeticError("target builder was not bound in source closure")
    data_hashes = dict(d4_gate["data_hashes"])
    for relative, expected in d12.EXPECTED_HASHES.items():
        if d12.sha256_file(REPO_ROOT / relative) != expected:
            raise ValueError(f"D12 target dependency changed: {relative}")
        data_hashes[relative] = expected
    d4_gate_resolved = str(Path(d4_gate_path).resolve())
    expected_d4_gate = d12.sha256_file(d4_gate_path)
    data_hashes[D4_GATE_RELATIVE] = expected_d4_gate
    if expected_d4_gate != d4_bound["sha256"] or \
            d4_gate_resolved != d4_bound["path"]:
        raise ValueError("D4 v6 gate path/snapshot changed")
    normalizers = d12.load_d12_normalizers(REPO_ROOT)
    errors = {key: str(value)
              for key, value in normalizers["relative_errors"].items()}
    return {
        "status": "frozen-d12-transformed-multiplier-target-prelaunch-v6",
        "rigorous": False,
        "screen_launch_authorized": False,
        "d4_v6_gate_path": D4_GATE_RELATIVE,
        "d4_v6_gate_sha256": expected_d4_gate,
        "requires_d4_v6_calibration_pass": True,
        "transform_sha256": d4.TRANSFORM_SHA256,
        "base_target": {
            "semantics": "unmultiplied-272-label-D12-polynomial",
            "source_sha256": d12.EXPECTED_HASHES[d12.D12_SOURCE_RELATIVE],
            "integer_scaled_sha256":
                d12.EXPECTED_HASHES[d12.D12_INTEGER_RELATIVE],
            "k": 48, "degree": 12, "basis_dimension": 272,
        },
        "normalizers": {
            "raw_sha256": normalizers["raw_sha256"],
            "recovered_sha256": normalizers["recovered_sha256"],
            "baseline_sha256": normalizers["baseline_sha256"],
            "i_strata": 16, "j_common_strata": 16,
            "j_scale_to_numerator": 48,
            "sum_internal_relative_tolerance":
                str(d12.SUM_INTERNAL_RELATIVE_TOLERANCE),
            "baseline_relative_tolerance":
                str(d12.BASELINE_RELATIVE_TOLERANCE),
            "observed_relative_errors": errors,
            "base_quotient": str(normalizers["base_quotient"]),
        },
        "source_hashes": source_hashes,
        "data_hashes": data_hashes,
        "schedule": d4.v5.expected_schedule(),
        "data_split": {
            "training_replicates": [0, 1],
            "validation_replicates": [2, 3],
            "candidate_selection_uses_validation": False,
            "delete_each_validation_chain": True,
        },
        "unchanged_statistical_thresholds": d4.v5.expected_thresholds(),
        "cost_gate": {
            "maximum_projected_wall_seconds": 7200,
            "maximum_projected_peak_rss_kib": 1048576,
            "requires_timed_D4_and_D12_adapter_smokes": True,
        },
        "continuation_rule": d4.expected_continuation_rule(),
        "scalar_input_schema": {
            "consumer": "agents/exact-integrator/stratum_quadratic_transfer_decimal.py",
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
    d4._patch_v5_runtime()
    # The inherited publisher's alias guard reads these globals.  Expand
    # them to the complete target-gate closure before opening the output.
    d4.v5.REQUIRED_SOURCE_PATHS = tuple(gate["source_hashes"])
    d4.v5.REQUIRED_DATA_PATHS = tuple(gate["data_hashes"])
    digest = d4.v5.write_new_result(args.output, gate, gate)
    print(digest)


if __name__ == "__main__":
    main()
