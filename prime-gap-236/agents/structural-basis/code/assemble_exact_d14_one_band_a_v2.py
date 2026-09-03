#!/usr/bin/env python3
"""Strict-v2 D19 provenance repair for the exact D14 A aggregate.

The A shards and arithmetic are unchanged.  This wrapper pins the strict v2
cache-free D19 result used by the theorem-facing b assembly, replacing the
older but numerically identical v1 provenance attached by aggregate v1.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import sys


if hasattr(sys, "set_int_max_str_digits"):
    sys.set_int_max_str_digits(0)

FILE = Path(__file__).resolve()
BASE = FILE.with_name("assemble_exact_d14_one_band_a_v1.py")
BASE_SHA256 = \
    "5086d25b5c16c9462d27e9c6e6afb628627b4671ca9710a932928467f66c4fa4"


def load_base():
    import hashlib
    if hashlib.sha256(BASE.read_bytes()).hexdigest() != BASE_SHA256:
        raise RuntimeError("pinned exact-A v1 assembler changed")
    spec = importlib.util.spec_from_file_location(
        "assemble_exact_d14_one_band_a_v1_for_v2", BASE)
    if spec is None or spec.loader is None:
        raise ImportError(BASE)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


B = load_base()
STRICT_D19_CHECKER = B.REPO / "verify/check_bv_rational_vector_direct_v2.py"
STRICT_D19_CHECKER_SHA256 = \
    "ff2046ce180394a6328fdec2c112d575a4c540ff964f5dede28c6db6091506c5"
STRICT_D19_RESULT = B.REPO / (
    "verify/results/bv_D19_krylov20_direct_exact_v2_strict.json")
STRICT_D19_RESULT_SHA256 = \
    "8b0d47b22b09c057633022682332f0de4b7e47d4b6ab6d630690be081c58e170"
STRICT_D19_TEST = B.REPO / "verify/test_check_bv_rational_vector_direct_v2.py"
STRICT_D19_TEST_SHA256 = \
    "5f03f8cdbc9235dd739c36901fab42cd44216b1213009fd019dfb1ae32fa6d27"


def build_aggregate():
    snapshot = FILE.read_bytes()
    B.D19_CHECKER = STRICT_D19_CHECKER
    B.D19_CHECKER_SHA256 = STRICT_D19_CHECKER_SHA256
    B.D19_RESULT = STRICT_D19_RESULT
    B.D19_RESULT_SHA256 = STRICT_D19_RESULT_SHA256
    B.D19_TEST = STRICT_D19_TEST
    B.D19_TEST_SHA256 = STRICT_D19_TEST_SHA256
    row = B.build_aggregate()
    if FILE.read_bytes() != snapshot:
        raise RuntimeError("strict-v2 exact-A assembler changed during execution")
    row["format"] = "exact-d14-one-band-a-aggregate-v2"
    row["status"] = "EXACT D14 ONE-BAND A AGGREGATE STRICT-V2 PASS"
    row["source_sha256"] = B.sha256(snapshot)
    row["base_assembler"] = {
        "path": str(BASE.relative_to(B.REPO)),
        "sha256": BASE_SHA256,
        "role": "hash-pinned A shard validation and exact summation",
    }
    row["source_hashes"][str(BASE.relative_to(B.REPO))] = BASE_SHA256
    row["provenance_repair"] = {
        "replaced_aggregate_result": (
            "agents/structural-basis/results/"
            "d14_one_band_a_aggregate_exact_v1.json"),
        "replaced_aggregate_sha256": (
            "1e0e8e35449a19ce83bfc37896f75431c61ea39ccb82abbf99eb5669319fae22"),
        "reason": (
            "v1 attached older D19 checker/result/test metadata; exact A "
            "and all shard hashes were already correct and are unchanged"),
        "old_and_strict_D19_exact_values_equal": True,
        "strict_D19_provenance_is_theorem_facing": True,
    }
    return row


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = build_aggregate()
    payload = B.canonical_json(result)
    B.publish_exclusive(args.output, payload)
    print(json.dumps({
        "status": result["status"],
        "exact_A_scaled_decimal": result["exact_A_scaled_decimal"],
        "exact_A_unscaled_decimal": result["exact_A_unscaled_decimal"],
        "strict_D19_result_sha256": STRICT_D19_RESULT_SHA256,
        "output_sha256": B.sha256(payload),
    }, sort_keys=True))


if __name__ == "__main__":
    main()
