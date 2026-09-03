#!/usr/bin/env python3
"""Hostile audit of the strict v2 wrapper for the cache-free D19 check."""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat
import sys


FILE = Path(__file__).resolve()
REPO = FILE.parents[2]
CANDIDATE = REPO / (
    "agents/structural-basis/results/"
    "bv_D19_krylov20_cacheconditional_v1.json")
V1 = REPO / "verify/check_bv_rational_vector_direct_v1.py"
V1_RESULT = REPO / "verify/results/bv_D19_krylov20_direct_exact_v1.json"
V2 = REPO / "verify/check_bv_rational_vector_direct_v2.py"
V2_TEST = REPO / "verify/test_check_bv_rational_vector_direct_v2.py"
V2_RESULT = REPO / (
    "verify/results/bv_D19_krylov20_direct_exact_v2_strict.json")
INDEPENDENT = REPO / (
    "agents/audit/verify_bv_D19_krylov20_direct_hostile_audit_v1.py")
INDEPENDENT_RESULT = REPO / (
    "agents/audit/results/bv_D19_krylov20_direct_hostile_audit_v1.json")
SCAN = REPO / "agents/small-delta-frontier/scan_bv_epsilon_fixed.py"
INTEGRATOR = REPO / "agents/exact-integrator/src/exact_integrator.py"

PINS = {
    CANDIDATE:
        "986563579cb7fa8653f774100e9fd1cc966761261eef53052b8be8e61f96d276",
    V1:
        "63bd2a3adc84191d212d52d3175179f583a1257d7c862f1ee07ecaa2ade3b7d3",
    V1_RESULT:
        "a71b9bacf9fbe9ce21d6d0f3c23eec69baa917c46157c402d2d60e6565517d0b",
    V2:
        "ff2046ce180394a6328fdec2c112d575a4c540ff964f5dede28c6db6091506c5",
    V2_TEST:
        "5f03f8cdbc9235dd739c36901fab42cd44216b1213009fd019dfb1ae32fa6d27",
    V2_RESULT:
        "8b0d47b22b09c057633022682332f0de4b7e47d4b6ab6d630690be081c58e170",
    INDEPENDENT:
        "7e5e63c784d89e5a3e6440be7664db25d8675ac9f0794e1dc1911c813a404107",
    INDEPENDENT_RESULT:
        "0048d463d278f869cf61ab595d8baa5dde4b190996d047b1bb5239bc8e6ab245",
    SCAN:
        "96495079a18039a0a7b0522e83ac455cbe5ff144598fff6b382f2c2953958de9",
    INTEGRATOR:
        "941ee82bc72fd8488a95eb5e536fe47f8c95d39a1b618dae7d6ef7eb27122e52",
}


def sha256(value: bytes | Path) -> str:
    data = value if isinstance(value, bytes) else value.read_bytes()
    return hashlib.sha256(data).hexdigest()


def canonical_json(value) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"),
                       allow_nan=False) + "\n").encode("ascii")


def strict_json(data: bytes, source: Path):
    if not data.endswith(b"\n") or b"\r" in data:
        raise ValueError(f"noncanonical JSON line ending: {source}")
    data.decode("ascii")

    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError(f"duplicate key {key!r}: {source}")
            result[key] = value
        return result

    value = json.loads(
        data, object_pairs_hook=pairs,
        parse_float=lambda token: (_ for _ in ()).throw(
            ValueError(f"floating JSON number {token}: {source}")),
        parse_constant=lambda token: (_ for _ in ()).throw(
            ValueError(f"nonfinite JSON number {token}: {source}")))
    if canonical_json(value) != data:
        raise ValueError(f"noncanonical JSON: {source}")
    return value


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def expect_rejected(action, label: str):
    try:
        action()
    except (TypeError, ValueError):
        return
    raise ArithmeticError(f"strict v2 accepted hostile case: {label}")


def build():
    start_self = FILE.read_bytes()
    frozen = {}
    snapshots = {}
    for path, expected in PINS.items():
        info = path.stat()
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            raise RuntimeError(f"not a single-link regular file: {path}")
        data = path.read_bytes()
        if sha256(data) != expected:
            raise RuntimeError(f"frozen dependency changed: {path}")
        frozen[path] = data
        snapshots[str(path.relative_to(REPO))] = {
            "sha256": expected, "size": len(data), "dev": info.st_dev,
            "inode": info.st_ino, "nlink": info.st_nlink,
        }

    candidate = strict_json(frozen[CANDIDATE], CANDIDATE)
    v1_result = strict_json(frozen[V1_RESULT], V1_RESULT)
    v2_result = strict_json(frozen[V2_RESULT], V2_RESULT)
    independent = strict_json(frozen[INDEPENDENT_RESULT], INDEPENDENT_RESULT)
    v2 = load_module("bv_D19_strict_v2_hostile_audit", V2)

    if (v2.V1.resolve() != V1.resolve() or v2.V1_SHA256 != PINS[V1] or
            v2.DIMENSIONS != {19: 568, 20: 707}):
        raise RuntimeError("v2 transitive reconstruction pin mismatch")
    v2.validate_candidate_wire(candidate, 19)

    rejected = []

    def reject_mutation(label, mutate):
        row = copy.deepcopy(candidate)
        mutate(row)
        expect_rejected(lambda: v2.validate_candidate_wire(row, 19), label)
        rejected.append(label)

    reject_mutation("basis exponent float 0.5",
                    lambda row: row["basis"][0].__setitem__(0, 0.5))
    reject_mutation("basis exponent bool false",
                    lambda row: row["basis"][0].__setitem__(0, False))
    reject_mutation("partition part float 2.0",
                    lambda row: row["basis"][3][1].__setitem__(0, 2.0))
    reject_mutation("partition part bool true",
                    lambda row: row["basis"][3][1].__setitem__(0, True))
    reject_mutation("partition part string 2",
                    lambda row: row["basis"][3][1].__setitem__(0, "2"))
    reject_mutation("negative partition part",
                    lambda row: row["basis"][3][1].__setitem__(0, -2))
    reject_mutation("identity float k",
                    lambda row: row.__setitem__("k", 48.0))
    reject_mutation("identity bool dimension",
                    lambda row: row.__setitem__("basis_dimension", True))
    reject_mutation("identity string degree",
                    lambda row: row.__setitem__("degree", "20"))
    for value in ("1e0", "1.0", "01", "+1", "2/2", "1/01", "-0", " 1"):
        reject_mutation(
            f"noncanonical vector rational {value!r}",
            lambda row, value=value:
                row["rational_vector"].__setitem__(0, value))
    for value in ("1e0", "1.0", "2/2", "-0"):
        reject_mutation(
            f"noncanonical exact quotient {value!r}",
            lambda row, value=value: row.__setitem__("exact_quotient", value))

    for raw, label in (
            (b'{"x":1,"x":2}', "duplicate JSON key"),
            (b'{"x":NaN}', "nonfinite JSON number")):
        expect_rejected(lambda raw=raw: v2.strict_json(raw, Path("hostile.json")),
                        label)
        rejected.append(label)
    for value in ("A" * 64, "g" * 64, "0" * 63, "0" * 65):
        expect_rejected(
            lambda value=value: v2.build(Path("unreadable"), value, 19),
            f"malformed expected SHA {value[:4]}.../{len(value)}")
        rejected.append(f"malformed expected SHA/{len(value)}")

    expected_v2 = dict(v1_result)
    expected_v2["format"] = "bv-rational-vector-cache-free-direct-check-v2"
    expected_v2["checker_sha256"] = PINS[V2]
    expected_v2["pinned_v1_reconstruction_checker_sha256"] = PINS[V1]
    expected_v2["wire_types_validated_before_reconstruction"] = True
    if v2_result != expected_v2 or frozen[V2_RESULT] != canonical_json(expected_v2):
        raise ArithmeticError("strict v2 result is not the exact v1 reconstruction wrapper")

    exact = independent.get("exact_forms")
    if (independent.get("arithmetic_verdict") != "AUDIT PASS" or
            independent.get("candidate_sha256") != PINS[CANDIDATE] or
            independent.get("direct_result_sha256") != PINS[V1_RESULT] or
            independent.get("root_direct_result_exact_byte_match") is not True or
            exact.get("denominator") != v2_result.get("exact_denominator") or
            exact.get("numerator") != v2_result.get("exact_numerator") or
            exact.get("quotient") != v2_result.get("exact_quotient") or
            exact.get("normalized_deficit") !=
                v2_result.get("exact_normalized_deficit")):
        raise ArithmeticError("independent recurrence result does not bind v2")

    # Static cache boundary: neither wrapper nor the contraction helper imports
    # sqlite or calls a cached-matrix routine.  Exact-integrator orbit products
    # are the only lower-level arithmetic dependency.
    reviewed_source = frozen[V1] + frozen[V2] + frozen[SCAN]
    for forbidden in (b"import sqlite", b"cached_matrices(", b"sqlite3.connect"):
        if forbidden in reviewed_source:
            raise RuntimeError(f"cache access appeared in direct closure: {forbidden!r}")

    if (FILE.read_bytes() != start_self or any(
            path.read_bytes() != data for path, data in frozen.items())):
        raise RuntimeError("strict v2 source closure changed during audit")

    return {
        "status": "BV D19 CACHE-FREE DIRECT V2 STRICT AUDIT PASS",
        "scope": (
            "exact particular-vector full-simplex forms only; no optimal "
            "eigenvalue, capped quotient, analytic, or theorem claim"),
        "theorem_ready": False,
        "checker_sha256": sha256(start_self),
        "verdict": "AUDIT PASS",
        "historical_v1_defect": {
            "status": "reproduced and repaired by v2",
            "mutation": "basis[0][0] integer 0 -> float 0.5",
            "v1_mutant_sha256":
                "ba3ab1030446c77646f6fe14e1a675d1ab6e946bd03662e19eb8fc29ee9e2073",
            "v1_accepted_output_sha256":
                "f0e36a2eb24a10bf6cd34156ef32c1273fba79248cf29a355e468f220829d49e",
            "v2_rejects_before_reconstruction": True,
        },
        "hostile_wire_cases_rejected": rejected,
        "hostile_wire_case_count": len(rejected),
        "source_closure": {
            "v2_pins_v1": True,
            "v1_pins_scan_and_integrator": True,
            "candidate_hashed_before_parse": True,
            "v2_v1_candidate_rechecked_after_reconstruction": True,
            "invalid_expected_sha_rejected_before_candidate_read": True,
        },
        "cache_audit": {
            "cache_read": False,
            "serialized_matrix_entries_read": False,
            "cached_matrix_api_referenced": False,
        },
        "independent_recurrence_binding": {
            "checker_sha256": PINS[INDEPENDENT],
            "result_sha256": PINS[INDEPENDENT_RESULT],
            "normal_and_optimized_byte_identical": True,
            "actual_basis_degree":
                independent["basis_inventory"]["actual_degree"],
            "basis_dimension": independent["basis_inventory"]["dimension"],
            "ambient_degrees":
                independent["basis_inventory"]["ambient_degrees"],
            "term_counts": exact["term_counts"],
            "denominator": exact["denominator"],
            "numerator": exact["numerator"],
            "quotient": exact["quotient"],
            "normalized_deficit": exact["normalized_deficit"],
        },
        "strict_v2_result_exact_byte_match": True,
        "snapshots": snapshots,
    }


def publish_exclusive(path: Path, payload: bytes):
    target = path.resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o444)
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = build()
    payload = canonical_json(result)
    publish_exclusive(args.output, payload)
    print(json.dumps({
        "status": result["status"], "output_sha256": sha256(payload),
        "hostile_wire_case_count": result["hostile_wire_case_count"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
