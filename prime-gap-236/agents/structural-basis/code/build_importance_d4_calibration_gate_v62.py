#!/usr/bin/env python3
"""Build the production-disabled v6.2 D4 calibration gate."""

from __future__ import annotations

import argparse
from pathlib import Path

import importance_d4_calibration_v62 as v62


HERE = Path(__file__).resolve()


def _sha(value):
    if (not isinstance(value, str) or len(value) != 64 or
            any(character not in "0123456789abcdef" for character in value)):
        raise ValueError("expected builder hash is not canonical SHA-256")
    return value


def build_gate(expected_self_sha256):
    expected_self_sha256 = _sha(expected_self_sha256)
    if v62.v61.v6.v5.sha256_file(HERE) != expected_self_sha256:
        raise ValueError("executed v6.2 builder differs from trust root")
    v62.validate_v61_failure_artifacts()
    source_hashes = {relative: v62.v61.v6.v5.sha256_file(
        v62.REPO_ROOT / relative) for relative in v62.REQUIRED_SOURCE_PATHS}
    data_hashes = {relative: v62.v61.v6.v5.sha256_file(
        v62.REPO_ROOT / relative) for relative in v62.REQUIRED_DATA_PATHS}
    if (source_hashes[str(HERE.relative_to(v62.REPO_ROOT))] !=
            expected_self_sha256 or
            data_hashes[v62.V61_GATE_RELATIVE] != v62.V61_GATE_SHA256):
        raise ArithmeticError("v6.2 builder/predecessor binding failed")
    for relative, expected in v62.V61_FAILURE_ARTIFACT_HASHES.items():
        if source_hashes.get(relative) != expected:
            raise ArithmeticError("v6.2 failure-artifact binding failed")
    return {
        "status": "frozen-d4-exact-whitened-calibration-prelaunch-v6.2",
        "rigorous": False,
        "production_launch_authorized": False,
        "supersedes_invalid_gate_sha256": v62.V61_GATE_SHA256,
        "float_encoding": v62.v61.v6.v5.FLOAT_ENCODING,
        "source_hashes": source_hashes,
        "data_hashes": data_hashes,
        "schedule": v62.v61.v6.v5.expected_schedule(),
        "thresholds": v62.v61.v6.v5.expected_thresholds(),
        "conventions": v62.expected_conventions(),
        "extension_rule": v62.v61.v6.expected_extension_rule(),
        "continuation_rule": v62.v61.v6.expected_continuation_rule(),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--expected-self-sha256", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    gate = build_gate(args.expected_self_sha256)
    v62.install_runtime()
    v62.v61.v6._patch_v5_runtime()
    digest = v62.v61.v6.v5.write_new_result(args.output, gate, gate)
    print(digest)


if __name__ == "__main__":
    main()
