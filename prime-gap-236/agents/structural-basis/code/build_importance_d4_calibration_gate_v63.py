#!/usr/bin/env python3
"""Build the production-disabled v6.3 D4 calibration gate."""

from __future__ import annotations

import argparse
from pathlib import Path

import importance_d4_calibration_v63 as v63


HERE = Path(__file__).resolve()


def _sha(value):
    if (not isinstance(value, str) or len(value) != 64 or
            any(character not in "0123456789abcdef" for character in value)):
        raise ValueError("expected builder hash is not canonical SHA-256")
    return value


def build_gate(expected_self_sha256):
    expected_self_sha256 = _sha(expected_self_sha256)
    if v63.v62.v61.v6.v5.sha256_file(HERE) != expected_self_sha256:
        raise ValueError("executed v6.3 builder differs from trust root")
    v63.validate_v62_failure_artifacts()
    source_hashes = {relative: v63.v62.v61.v6.v5.sha256_file(
        v63.REPO_ROOT / relative) for relative in v63.REQUIRED_SOURCE_PATHS}
    data_hashes = {relative: v63.v62.v61.v6.v5.sha256_file(
        v63.REPO_ROOT / relative) for relative in v63.REQUIRED_DATA_PATHS}
    if (source_hashes[str(HERE.relative_to(v63.REPO_ROOT))] !=
            expected_self_sha256 or
            data_hashes[v63.V62_GATE_RELATIVE] != v63.V62_GATE_SHA256):
        raise ArithmeticError("v6.3 builder/predecessor binding failed")
    for relative, expected in v63.V62_FAILURE_ARTIFACT_HASHES.items():
        if source_hashes.get(relative) != expected:
            raise ArithmeticError("v6.3 failure-artifact binding failed")
    return {
        "status": "frozen-d4-exact-whitened-calibration-prelaunch-v6.3",
        "rigorous": False,
        "production_launch_authorized": False,
        "supersedes_invalid_gate_sha256": v63.V62_GATE_SHA256,
        "float_encoding": v63.v62.v61.v6.v5.FLOAT_ENCODING,
        "source_hashes": source_hashes,
        "data_hashes": data_hashes,
        "schedule": v63.v62.v61.v6.v5.expected_schedule(),
        "thresholds": v63.v62.v61.v6.v5.expected_thresholds(),
        "conventions": v63.expected_conventions(),
        "extension_rule": v63.v62.v61.v6.expected_extension_rule(),
        "continuation_rule": v63.v62.v61.v6.expected_continuation_rule(),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--expected-self-sha256", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    gate = build_gate(args.expected_self_sha256)
    v63.install_runtime()
    v63.v62.v61.v6._patch_v5_runtime()
    digest = v63.v62.v61.v6.v5.write_new_result(args.output, gate, gate)
    print(digest)


if __name__ == "__main__":
    main()
