#!/usr/bin/env python3
"""Fail-closed comparator and frozen-gate evaluator for D12 face samples."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import stat
from fractions import Fraction as Q
from pathlib import Path


HERE = Path(__file__).resolve().parent
GATE = HERE / "d12_fused_face_benchmark_gate.json"
GATE_SHA = "5ffe7844270f51c1d58e9529f81fed4469f035a03a6c556e4f96370c3439180b"
D4_FUSED = HERE / "results/c10_D4_stratum_moment_table_fused_oracle.json"
D4_UNFUSED = HERE / "results/c10_D4_stratum_moment_table_oracle.json"
EXPECTED_I_FACES = [[0, 0], [7, 9], [15, 0]]
EXPECTED_J_FACES = [[0, 0], [7, 9], [15, 0]]
EXPECTED_PARAMETERS = {
    "alpha": "79247/300000", "delta": "1/100",
    "eta": "76247/300000", "beta1": "3/20",
    "beta2": "3/20", "beta3plus": "97/625",
}


class AnalysisError(RuntimeError):
    pass


def require(condition, message):
    if not condition:
        raise AnalysisError(message)


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def finite_nonnegative(value, label):
    require(type(value) in (int, float) and not isinstance(value, bool) and
            math.isfinite(value) and value >= 0, f"invalid {label}")
    return value


def canonical_fraction(token, label):
    require(type(token) is str and re.fullmatch(
        r"(?:0|-?[1-9][0-9]*)(?:/[1-9][0-9]*)?", token) is not None,
        f"noncanonical fraction {label}")
    value = Q(token)
    require(str(value) == token, f"unreduced fraction {label}")
    return value


def aggregate_powers(maximum_degree):
    return [[a, total - a] for total in range(maximum_degree + 1)
            for a in range(total, -1, -1)]


def independent_degree_three_schema():
    degree = 3
    channels = aggregate_powers(degree)
    same_products = [[j, k] for j in range(degree + 1)
                     for k in range(j + 1)]
    cross_products = [[j, k] for j in range(degree + 1)
                      for k in range(degree + 1)]
    return {
        "degree": degree,
        "channels": channels,
        "i_tags": aggregate_powers(2 * degree),
        "same_branch_product_tags": same_products,
        "cross_branch_product_tags": cross_products,
        "same_branch_scalar_tags": [
            [j, k, u, v] for j, k in same_products
            for u, v in aggregate_powers(2 * degree - j - k)],
        "cross_branch_scalar_tags": [
            [j, k, u, v] for j, k in cross_products
            for u, v in aggregate_powers(2 * degree - j - k)],
    }


def validate_table(rows, width, label):
    require(type(rows) is list, f"{label} table type")
    previous = None
    result = []
    for index, row in enumerate(rows):
        require(type(row) is list and len(row) == width and
                all(type(x) is int for x in row[:-1]),
                f"{label} row structure {index}")
        key = tuple(row[:-1])
        require(previous is None or previous < key,
                f"{label} table order/duplicate {index}")
        value = canonical_fraction(row[-1], f"{label}[{index}]")
        require(value != 0, f"{label} serialized zero {index}")
        result.append((key, value))
        previous = key
    raw = json.dumps(rows, separators=(",", ":")).encode("ascii")
    return result, sha256(raw)


def validate_worker_result(path, expected_sha, expected_mode, gate):
    raw = Path(path).read_bytes()
    require(sha256(raw) == expected_sha, f"{expected_mode} result SHA")
    data = json.loads(raw)
    expected_keys = {
        "status", "rigorous_sample_forms", "theorem_ready", "scope", "mode",
        "k", "base_degree", "multiplier_degree", "parameters",
        "original_input_sha256", "scaled_input_sha256", "base_lcm_bits",
        "basis_dimension", "integer_vector_content",
        "prelaunch_available_memory_mib",
        "required_prelaunch_available_memory_mib", "tag_schema",
        "tag_schema_sha256", "selected_i_faces", "selected_j_faces",
        "i_orbit_groups", "marginal_components", "i_setup_seconds",
        "j_setup_seconds", "i_results", "j_results", "total_seconds",
        "peak_rss_kib", "dependency_hashes",
    }
    require(type(data) is dict and set(data) == expected_keys,
            f"{expected_mode} result schema")
    require(data["status"] ==
            "exact-D12-degree3-fused-face-benchmark-pass" and
            data["rigorous_sample_forms"] is True and
            data["theorem_ready"] is False and
            data["mode"] == expected_mode and data["k"] == 48 and
            data["base_degree"] == 12 and data["multiplier_degree"] == 3,
            f"{expected_mode} result identity")
    require(data["parameters"] == EXPECTED_PARAMETERS and
            data["original_input_sha256"] ==
            gate["d12_original_input_sha256"] and
            data["scaled_input_sha256"] == gate["d12_scaled_input_sha256"] and
            data["base_lcm_bits"] == 714 and
            data["basis_dimension"] == 272 and
            data["integer_vector_content"] == 1,
            f"{expected_mode} source/support identity")
    require(type(data["prelaunch_available_memory_mib"]) is int and
            data["prelaunch_available_memory_mib"] >= 1844 and
            data["required_prelaunch_available_memory_mib"] == 1844,
            f"{expected_mode} prelaunch memory gate")
    require(data["tag_schema_sha256"] ==
            gate["degree_three_tag_schema_sha256"],
            f"{expected_mode} tag schema SHA")
    canonical_schema = independent_degree_three_schema()
    canonical_schema_raw = json.dumps(
        canonical_schema, sort_keys=True, separators=(",", ":")).encode()
    require(data["tag_schema"] == canonical_schema and
            sha256(canonical_schema_raw) ==
            gate["degree_three_tag_schema_sha256"],
            f"{expected_mode} noncanonical tag schema")
    require(data["selected_i_faces"] == EXPECTED_I_FACES and
            data["selected_j_faces"] == EXPECTED_J_FACES and
            data["i_orbit_groups"] == 1575 and
            data["marginal_components"] == 695,
            f"{expected_mode} selected faces/setup counts")
    for key in ("i_setup_seconds", "j_setup_seconds", "total_seconds",
                "peak_rss_kib"):
        finite_nonnegative(data[key], f"{expected_mode} {key}")
    require(type(data["dependency_hashes"]) is dict and
            len(data["dependency_hashes"]) == 10 and
            all(type(key) is str and
                re.fullmatch(r"[0-9a-f]{64}", value or "") is not None
                for key, value in data["dependency_hashes"].items()),
            f"{expected_mode} dependency hashes")
    dependency_values = set(data["dependency_hashes"].values())
    require(gate["worker_sha256"] in dependency_values and
            gate["fused_engine_sha256"] in dependency_values and
            gate["unfused_engine_sha256"] in dependency_values and
            gate["d12_original_input_sha256"] in dependency_values and
            gate["d12_scaled_input_sha256"] in dependency_values,
            f"{expected_mode} pinned dependency closure")

    require(type(data["i_results"]) is list and
            len(data["i_results"]) == 3 and
            type(data["j_results"]) is list and
            len(data["j_results"]) == 3,
            f"{expected_mode} face result cardinality")
    for expected_face, result in zip(EXPECTED_I_FACES, data["i_results"]):
        require(type(result) is dict and set(result) == {
            "face", "table", "table_sha256", "face_polynomial_seconds",
            "aggregate_integral_seconds", "scalar_integrals"},
            f"{expected_mode} I face schema")
        require(result["face"] == expected_face and
                result["scalar_integrals"] == 28,
                f"{expected_mode} I face identity/count")
        _, digest = validate_table(
            result["table"], 3, f"{expected_mode} I {expected_face}")
        require(digest == result["table_sha256"],
                f"{expected_mode} I table SHA")
        finite_nonnegative(result["face_polynomial_seconds"], "I face time")
        finite_nonnegative(result["aggregate_integral_seconds"],
                           "I integral time")

    j_keys = {
        "face", "table", "table_sha256", "branch_domains",
        "fused_traversals", "logical_moment_products", "scalar_integrals",
        "orbit_pair_visits", "tagged_polynomial_multiplies",
        "density_visits", "density_tag_contractions",
        "branch_blocks_seconds", "product_integral_seconds",
    }
    for expected_face, result in zip(EXPECTED_J_FACES, data["j_results"]):
        require(type(result) is dict and set(result) == j_keys and
                result["face"] == expected_face,
                f"{expected_mode} J face schema/identity")
        _, digest = validate_table(
            result["table"], 7, f"{expected_mode} J {expected_face}")
        require(digest == result["table_sha256"],
                f"{expected_mode} J table SHA")
        for key in ("branch_domains", "fused_traversals",
                    "logical_moment_products", "scalar_integrals",
                    "orbit_pair_visits", "tagged_polynomial_multiplies",
                    "density_visits", "density_tag_contractions"):
            require(type(result[key]) is int and result[key] >= 0,
                    f"{expected_mode} J counter {key}")
        if expected_mode == "fused":
            require(result["fused_traversals"] == result["branch_domains"],
                    "fused traversal/domain mismatch")
        else:
            require(all(result[key] == 0 for key in
                        ("fused_traversals", "orbit_pair_visits",
                         "tagged_polynomial_multiplies", "density_visits",
                         "density_tag_contractions")),
                    "unfused result carries fused counters")
        finite_nonnegative(result["branch_blocks_seconds"], "J block time")
        finite_nonnegative(result["product_integral_seconds"],
                           "J product time")
    return data, raw


def validate_d4(gate):
    fused_raw, unfused_raw = D4_FUSED.read_bytes(), D4_UNFUSED.read_bytes()
    require(sha256(fused_raw) == gate["d4_fused_artifact_sha256"] and
            sha256(unfused_raw) == gate["d4_unfused_artifact_sha256"],
            "D4 artifact SHA")
    fused, unfused = json.loads(fused_raw), json.loads(unfused_raw)
    require(fused.get("status") ==
            "exact-D4-fused-stratum-moment-oracle-pass" and
            unfused.get("status") ==
            "exact-D4-stratum-moment-table-oracle-pass" and
            fused.get("all_entries_equal_frozen_D4_oracle") is True and
            unfused.get("all_entries_equal_frozen_D4_oracle") is True,
            "D4 exact status")
    for key in ("matrix_dimension", "i_matrix_sha256", "b48_matrix_sha256",
                "particular_denominator", "particular_numerator",
                "particular_quotient", "i_faces", "i_scalar_moment_integrals",
                "j_branch_domains", "j_scalar_moment_integrals"):
        require(fused.get(key) == unfused.get(key), f"D4 equality: {key}")
    require(fused.get("j_logical_moment_products") ==
            unfused.get("j_moment_products") == 8556 and
            fused.get("j_fused_traversals") == 1200,
            "D4 logical/fused counts")


def ceil_fraction(numerator, denominator):
    return (numerator + denominator - 1) // denominator


def publish_owned(path_text, payload, trusted):
    path = Path(path_text).resolve()
    require(path not in trusted, "analysis output aliases input/dependency")
    raw = (json.dumps(payload, indent=2) + "\n").encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_CREAT | os.O_EXCL | os.O_RDWR
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(path, flags, 0o600)
    try:
        require(stat.S_ISREG(os.fstat(fd).st_mode), "analysis output regular")
        offset = 0
        while offset < len(raw):
            count = os.write(fd, raw[offset:])
            require(count > 0, "analysis short write")
            offset += count
        os.fsync(fd)
        fs, ps = os.fstat(fd), os.stat(path, follow_symlinks=False)
        require((fs.st_dev, fs.st_ino) == (ps.st_dev, ps.st_ino) and
                path.read_bytes() == raw, "analysis output ownership/bytes")
        for trusted_path, original in trusted.items():
            require(trusted_path.read_bytes() == original,
                    f"analysis input changed: {trusted_path}")
    finally:
        os.close(fd)
    print(json.dumps({"status": payload["status"],
                      "output_sha256": sha256(raw)}, indent=2))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--fused", required=True)
    parser.add_argument("--fused-sha", required=True)
    parser.add_argument("--unfused", required=True)
    parser.add_argument("--unfused-sha", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    paths = [Path(x).resolve() for x in
             (args.fused, args.unfused, args.output)]
    require(len(set(paths)) == 3, "analysis input/output path alias")
    trusted_paths = (GATE.resolve(), D4_FUSED.resolve(), D4_UNFUSED.resolve(),
                     Path(__file__).resolve(), paths[0], paths[1])
    require(len(set(trusted_paths)) == len(trusted_paths),
            "analysis dependency path alias")
    trusted = {path: path.read_bytes() for path in trusted_paths}
    require(sha256(trusted[GATE.resolve()]) == GATE_SHA, "frozen gate SHA")
    gate = json.loads(trusted[GATE.resolve()])
    require(gate.get("status") ==
            "predeclared-D12-degree3-fused-face-benchmark-gate" and
            gate.get("frozen_before_D12_face_timing") is True,
            "frozen gate identity")
    validate_d4(gate)
    fused, _ = validate_worker_result(
        args.fused, args.fused_sha, "fused", gate)
    unfused, _ = validate_worker_result(
        args.unfused, args.unfused_sha, "unfused", gate)
    require(fused["tag_schema"] == unfused["tag_schema"],
            "fused/unfused schema object mismatch")
    exact_equal = True
    for f, u in zip(fused["i_results"], unfused["i_results"]):
        exact_equal &= (f["table"] == u["table"] and
                        f["table_sha256"] == u["table_sha256"] and
                        f["scalar_integrals"] == u["scalar_integrals"])
    for f, u in zip(fused["j_results"], unfused["j_results"]):
        exact_equal &= (f["table"] == u["table"] and
                        f["table_sha256"] == u["table_sha256"] and
                        f["branch_domains"] == u["branch_domains"] and
                        f["logical_moment_products"] ==
                        u["logical_moment_products"] and
                        f["scalar_integrals"] == u["scalar_integrals"])
    require(exact_equal, "sample fused/unfused exact equality")

    i_times = [x["face_polynomial_seconds"] +
               x["aggregate_integral_seconds"]
               for x in fused["i_results"]]
    j_times = [x["branch_blocks_seconds"] + x["product_integral_seconds"]
               for x in fused["j_results"]]
    projected_wall = (fused["i_setup_seconds"] + fused["j_setup_seconds"] +
                      312 * max(i_times) + 296 * max(j_times))
    central = 1
    central_fused = j_times[central]
    central_unfused = (unfused["j_results"][central]["branch_blocks_seconds"] +
                       unfused["j_results"][central][
                           "product_integral_seconds"])
    require(central_fused > 0, "zero fused central-face time")
    central_speedup = central_unfused / central_fused
    all_tables = ([x["table"] for x in fused["i_results"]] +
                  [x["table"] for x in fused["j_results"]])
    max_token_chars = max(len(row[-1]) for table in all_tables
                          for row in table)
    projected_rss = (fused["peak_rss_kib"] +
                     ceil_fraction(16668 * (1024 + 2 * max_token_chars),
                                   1024))
    conditions = {
        "d4_exact_equality": True,
        "sample_exact_equality": exact_equal,
        "central_j_speedup_at_least_1_25": central_speedup >= 1.25,
        "projected_wall_at_most_10800_seconds": projected_wall <= 10800,
        "sample_peak_rss_below_819200_kib":
            fused["peak_rss_kib"] < 819200,
        "projected_peak_rss_below_819200_kib": projected_rss < 819200,
    }
    verdict = "GO-CONSIDER-LATER-FULL-RUN" if all(conditions.values()) \
        else "NO-GO-FULL-D12-DEGREE3"
    payload = {
        "status": "exact-D12-fused-face-benchmark-analyzed",
        "theorem_ready": False,
        "full_D12_matrix_was_not_run": True,
        "frozen_gate_sha256": GATE_SHA,
        "fused_result_sha256": args.fused_sha,
        "unfused_result_sha256": args.unfused_sha,
        "selected_i_faces": EXPECTED_I_FACES,
        "selected_j_faces": EXPECTED_J_FACES,
        "exact_tables_and_counts_equal": exact_equal,
        "fused_i_setup_seconds": fused["i_setup_seconds"],
        "fused_j_setup_seconds": fused["j_setup_seconds"],
        "fused_i_face_seconds": i_times,
        "fused_j_face_seconds": j_times,
        "unfused_j_face_seconds": [
            x["branch_blocks_seconds"] + x["product_integral_seconds"]
            for x in unfused["j_results"]],
        "central_j_unfused_over_fused_speedup": central_speedup,
        "projected_full_wall_seconds": projected_wall,
        "sample_fused_peak_rss_kib": fused["peak_rss_kib"],
        "maximum_sample_fraction_token_characters": max_token_chars,
        "projected_full_sparse_peak_rss_kib": projected_rss,
        "gate_conditions": conditions,
        "gate_verdict": verdict,
        "verdict_scope": "engineering launch recommendation only; no finite-space quotient or theorem",
    }
    publish_owned(args.output, payload, trusted)


if __name__ == "__main__":
    main()
