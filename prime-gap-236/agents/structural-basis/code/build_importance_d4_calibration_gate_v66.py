#!/usr/bin/env python3
"""Build the production-disabled v6.6 D4 calibration gate."""

from __future__ import annotations

import argparse
from pathlib import Path

import importance_d4_calibration_v66 as v66


HERE = Path(__file__).resolve()


def _sha(value):
    if (not isinstance(value, str) or len(value) != 64 or
            any(character not in "0123456789abcdef" for character in value)):
        raise ValueError("expected builder hash is not canonical SHA-256")
    return value


def build_gate(expected_self_sha256):
    expected_self_sha256 = _sha(expected_self_sha256)
    sha256_file = v66.v65.v64.v63.v62.v61.v6.v5.sha256_file
    if sha256_file(HERE) != expected_self_sha256:
        raise ValueError("executed v6.6 builder differs from trust root")
    v66.validate_v65_failure_artifacts()
    source_hashes = {
        relative: sha256_file(v66.REPO_ROOT / relative)
        for relative in v66.REQUIRED_SOURCE_PATHS
    }
    data_hashes = {
        relative: sha256_file(v66.REPO_ROOT / relative)
        for relative in v66.REQUIRED_DATA_PATHS
    }
    if (source_hashes[str(HERE.relative_to(v66.REPO_ROOT))] !=
            expected_self_sha256 or
            data_hashes[v66.V65_GATE_RELATIVE] != v66.V65_GATE_SHA256):
        raise ArithmeticError("v6.6 builder/predecessor binding failed")
    for relative, expected in v66.V65_FAILURE_ARTIFACT_HASHES.items():
        if source_hashes.get(relative) != expected:
            raise ArithmeticError("v6.6 failure-artifact binding failed")
    return {
        "status": "frozen-d4-exact-whitened-calibration-prelaunch-v6.6",
        "rigorous": False,
        "production_launch_authorized": False,
        "supersedes_invalid_gate_sha256": v66.V65_GATE_SHA256,
        "float_encoding": v66.v65.v64.v63.v62.v61.v6.v5.FLOAT_ENCODING,
        "source_hashes": source_hashes,
        "data_hashes": data_hashes,
        "schedule": v66.v65.v64.v63.v62.v61.v6.v5.expected_schedule(),
        "thresholds": v66.v65.v64.v63.v62.v61.v6.v5.expected_thresholds(),
        "conventions": v66.expected_conventions(),
        "extension_rule":
            v66.v65.v64.v63.v62.v61.v6.expected_extension_rule(),
        "continuation_rule":
            v66.v65.v64.v63.v62.v61.v6.expected_continuation_rule(),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--expected-self-sha256", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    gate = build_gate(args.expected_self_sha256)
    v66.install_runtime()
    v66.v65.v64.v63.v62.v61.v6._patch_v5_runtime()
    digest = v66.v65.v64.v63.v62.v61.v6.v5.write_new_result(
        args.output, gate, gate)
    print(digest)


if __name__ == "__main__":
    main()
