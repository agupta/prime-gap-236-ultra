#!/usr/bin/env python3
"""Build the production-disabled v6.1 D4 calibration gate."""

from __future__ import annotations

import argparse
from pathlib import Path

import importance_d4_calibration_v61 as v61


HERE = Path(__file__).resolve()


def _sha(value):
    if (not isinstance(value, str) or len(value) != 64 or
            any(character not in "0123456789abcdef" for character in value)):
        raise ValueError("expected builder hash is not canonical SHA-256")
    return value


def build_gate(expected_self_sha256):
    expected_self_sha256 = _sha(expected_self_sha256)
    if v61.v6.v5.sha256_file(HERE) != expected_self_sha256:
        raise ValueError("executed v6.1 builder differs from trust root")
    v61.validate_v6_failure_artifacts()
    source_hashes = {relative: v61.v6.v5.sha256_file(
        v61.REPO_ROOT / relative) for relative in v61.REQUIRED_SOURCE_PATHS}
    data_hashes = {relative: v61.v6.v5.sha256_file(
        v61.REPO_ROOT / relative) for relative in v61.REQUIRED_DATA_PATHS}
    if (source_hashes[str(HERE.relative_to(v61.REPO_ROOT))] !=
            expected_self_sha256 or
            data_hashes[v61.V6_GATE_RELATIVE] != v61.V6_GATE_SHA256):
        raise ArithmeticError("v6.1 builder/predecessor binding failed")
    return {
        "status": "frozen-d4-exact-whitened-calibration-prelaunch-v6.1",
        "rigorous": False,
        "production_launch_authorized": False,
        "supersedes_invalid_gate_sha256": v61.V6_GATE_SHA256,
        "float_encoding": v61.v6.v5.FLOAT_ENCODING,
        "source_hashes": source_hashes,
        "data_hashes": data_hashes,
        "schedule": v61.v6.v5.expected_schedule(),
        "thresholds": v61.v6.v5.expected_thresholds(),
        "conventions": v61.expected_conventions(),
        "extension_rule": v61.v6.expected_extension_rule(),
        "continuation_rule": v61.v6.expected_continuation_rule(),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--expected-self-sha256", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    gate = build_gate(args.expected_self_sha256)
    v61.install_runtime()
    v61.v6._patch_v5_runtime()
    digest = v61.v6.v5.write_new_result(args.output, gate, gate)
    print(digest)


if __name__ == "__main__":
    main()
