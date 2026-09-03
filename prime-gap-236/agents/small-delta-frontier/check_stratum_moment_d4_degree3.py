#!/usr/bin/env python3
"""Fail-closed exact D4 degree-three fused-moment fallback.

Production performs both the fused SoA and the independently implemented
unfused moment traversal.  It publishes only after all exact entries, moment
tables, the complete degree-two oracle submatrix, and one embedded exact
particular-vector contraction agree.  The shipped gate does not authorize a
production run.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import resource
import stat
import sys
import time
from fractions import Fraction as Q
from pathlib import Path


HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[1]
EI = HERE.parent / "exact-integrator"
sys.path[:0] = [str(HERE), str(EI), str(EI / "src")]

import exact_integrator as ei  # noqa: E402
from stratum_moment_table import (  # noqa: E402
    StratumMomentTableEvaluator,
    channel_powers,
    quadratic,
)
from stratum_moment_table_fused import (  # noqa: E402
    FusedStratumMomentTableEvaluator,
    canonical_schema_sha256,
    validate_moment_tag_schema,
)
from stratum_quadratic import StratumQuadraticEvaluator  # noqa: E402


DEGREE = 3
PARAMETERS = {
    "alpha": Q(79247, 300000), "delta": Q(1, 100),
    "eta": Q(76247, 300000), "beta1": Q(3, 20),
    "beta2": Q(3, 20), "beta3plus": Q(97, 625),
}
INPUT = EI / "results/c10_capped_D4_decimal55_vector_input.json"
REFERENCE = EI / "results/c10_stratum_quadratic_cappedopt_D4_exact.json"
INPUT_SHA = "2b11a18c697e9a2be61204b5493bf7a235ce4add39d853bbb4d76ef31fb4666b"
REFERENCE_SHA = "fbc8c38d2cf4241fdba03beb4251e2692e96af01ad4918c9a3a1075af2ed6e86"
TAG_SCHEMA_SHA = "320272a9dfb08ab6d12396127de3ff35ffe35c47b4715e4035bc985e67981aad"
EXPECTED_COUNTS = {
    "matrix_dimension": 160,
    "i_faces": 312,
    "j_branch_domains": 1200,
    "j_fused_traversals": 1200,
    "i_scalar_moment_integrals": 8736,
    "j_logical_moment_products": 14712,
    "j_scalar_moment_integrals": 167380,
}
SOURCE_PATHS = (
    "agents/small-delta-frontier/check_stratum_moment_d4_degree3.py",
    "agents/small-delta-frontier/test_check_stratum_moment_d4_degree3.py",
    "agents/small-delta-frontier/stratum_moment_table_fused.py",
    "agents/small-delta-frontier/stratum_moment_table.py",
    "agents/small-delta-frontier/test_stratum_moment_table_fused.py",
    "agents/exact-integrator/src/exact_integrator.py",
    "agents/exact-integrator/grouped_fixed_vector.py",
    "agents/exact-integrator/stratum_quadratic.py",
    "agents/exact-integrator/stratum_linear.py",
    "agents/exact-integrator/stratum_amplitude.py",
    "agents/exact-integrator/robust_generalized_solve.py",
    "agents/exact-integrator/run_scheduled_basis.py",
    "agents/exact-integrator/verify_scheduled_fixed_vector.py",
)
DATA_PATHS = (
    "agents/exact-integrator/results/c10_capped_D4_decimal55_vector_input.json",
    "agents/exact-integrator/results/c10_stratum_quadratic_cappedopt_D4_exact.json",
    "agents/small-delta-frontier/results/c10_D4_stratum_moment_table_fused_oracle.json",
)
BASELINE_MEASUREMENT = {
    "degree": 2,
    "artifact_sha256":
        "72ece5aa4a15536153d7634ee630ebf5e1090dc2ce0a7104cf00190bf310f6eb",
    "forms_seconds": "449.47953073098324",
    "peak_rss_kib": 50108,
    "j_scalar_moment_integrals": 57788,
    "degree3_scalar_count_ratio": "167380/57788",
    "projection_method": "degree2_wall_seconds_times_exact_J_scalar_count_ratio",
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def sha_file(path):
    return sha(Path(path).read_bytes())


def strict_json(data, name):
    require(type(data) is bytes and len(data) <= 256_000_000,
            f"{name} must be bounded bytes")

    def hook(pairs):
        answer = {}
        for key, value in pairs:
            require(type(key) is str and key not in answer,
                    f"{name} duplicate/non-string key")
            answer[key] = value
        return answer

    def reject(_token):
        raise ValueError(f"{name} forbids JSON floats/nonfinite tokens")

    return json.loads(data.decode(), object_pairs_hook=hook,
                      parse_float=reject, parse_constant=reject)


def exact_keys(value, keys, name):
    require(type(value) is dict and set(value) == set(keys),
            f"{name} schema mismatch")


def load_gate(path):
    path = Path(path)
    raw = path.read_bytes()
    gate = strict_json(raw, "degree-three gate")
    exact_keys(gate, {
        "status", "rigorous", "production_launch_authorized", "degree",
        "parameters", "source_hashes", "data_hashes", "tag_schema_sha256",
        "expected_counts", "resource_gate", "validation_targets",
        "baseline_measurement",
    }, "degree-three gate")
    require(gate["status"] == "frozen-c10-d4-degree3-moment-prelaunch" and
            gate["rigorous"] is False and
            gate["production_launch_authorized"] is False and
            type(gate["degree"]) is int and gate["degree"] == DEGREE,
            "degree-three gate status")
    require(gate["parameters"] == {k: str(v) for k, v in PARAMETERS.items()},
            "degree-three parameters")
    require(gate["tag_schema_sha256"] == TAG_SCHEMA_SHA ==
            canonical_schema_sha256(DEGREE), "degree-three tag schema")
    require(gate["expected_counts"] == EXPECTED_COUNTS,
            "degree-three expected counts")
    require(gate["resource_gate"] == {
        "predicted_fused_seconds": "1301.89457765889068165016958538",
        "maximum_fused_seconds": 1800,
        "maximum_total_validation_seconds": 3600,
        "maximum_peak_rss_kib": 262144,
    }, "degree-three resource gate")
    require(gate["validation_targets"] == [
        "fused_equals_unfused_all_moments_and_all_160x160_entries",
        "degree2_principal_submatrix_equals_fbc8_oracle_all_entries",
        "embedded_fbc8_vector_contraction_equals_exact_denominator_numerator",
        "inputs_sources_and_gate_unchanged_at_publication",
    ], "degree-three validation targets")
    require(gate["baseline_measurement"] == BASELINE_MEASUREMENT,
            "degree-three baseline measurement")
    for field, expected_paths in (("source_hashes", SOURCE_PATHS),
                                  ("data_hashes", DATA_PATHS)):
        table = gate[field]
        require(type(table) is dict and set(table) == set(expected_paths),
                f"{field} path set mismatch")
        for relative, wanted in table.items():
            require(type(relative) is str and type(wanted) is str and
                    len(wanted) == 64 and
                    all(c in "0123456789abcdef" for c in wanted),
                    f"malformed {field} entry")
            resolved = (PROJECT / relative).resolve()
            try:
                resolved.relative_to(PROJECT.resolve())
            except ValueError as error:
                raise ValueError(f"{field} path escape") from error
            require(sha_file(resolved) == wanted,
                    f"{field} hash mismatch: {relative}")
    return gate, sha(raw), raw


def authorization(path, gate_sha, driver_sha):
    raw = Path(path).read_bytes()
    value = strict_json(raw, "degree-three authorization")
    exact_keys(value, {"status", "authorized", "mode", "gate_sha256",
                       "driver_sha256"}, "degree-three authorization")
    require(value == {
        "status": "root-authorized-c10-d4-degree3-moment-run",
        "authorized": True,
        "mode": "exact-D4-degree3-fused-plus-unfused",
        "gate_sha256": gate_sha,
        "driver_sha256": driver_sha,
    }, "degree-three authorization mismatch")
    return sha(raw), raw


def load_data():
    input_raw, reference_raw = INPUT.read_bytes(), REFERENCE.read_bytes()
    require(sha(input_raw) == INPUT_SHA and sha(reference_raw) == REFERENCE_SHA,
            "D4 data SHA mismatch")
    source = json.loads(input_raw)
    reference = json.loads(reference_raw)
    require(source.get("k") == reference.get("k") == 48,
            "D4 k mismatch")
    require(reference.get("parameters") ==
            {k: str(v) for k, v in PARAMETERS.items()},
            "D4 parameter mismatch")
    labels = [(int(r), tuple(map(int, p))) for r, p in source["basis"]]
    coefficients = [Q(x) for x in source["rational_vector"]]
    require(len(labels) == len(coefficients) == 12,
            "D4 base dimension")
    return labels, coefficients, reference, input_raw, reference_raw


def reference_dense(support, labels, coefficients, reference):
    i_blocks = {int(r): [[Q(x) for x in row] for row in block]
                for r, block in reference["i_blocks"].items()}
    j_entries = {}
    for key, value in reference["j_entries"].items():
        parsed = ast.literal_eval(key)
        require(type(parsed) is tuple and len(parsed) == 2,
                "reference J key")
        j_entries[parsed] = Q(value)
    evaluator = StratumQuadraticEvaluator(
        support, labels, coefficients, Q)
    return evaluator.assemble_dense(i_blocks, j_entries)


def matrix_sha(matrix):
    return sha(json.dumps([[str(x) for x in row] for row in matrix],
                          separators=(",", ":")).encode())


def moment_rows(table, j=False):
    rows = []
    for r in sorted(table):
        for key in sorted(table[r]):
            rows.append([r, *key, str(table[r][key])])
    return rows


def embedded_degree2_vector(labels3, reference, labels2):
    powers2 = channel_powers(2)
    powers3 = channel_powers(3)
    mapping = {power: index for index, power in enumerate(powers3)}
    source_vector = [Q(x) for x in reference["rational_vector"]]
    require(len(source_vector) == len(labels2) == 96,
            "reference vector dimension")
    values = {(r, mapping[powers2[p]]): source_vector[index]
              for index, (r, p) in enumerate(labels2)}
    return [values.get(label, Q(0)) for label in labels3]


def dependency_snapshot(gate):
    return {relative: sha_file(PROJECT / relative)
            for field in ("source_hashes", "data_hashes")
            for relative in gate[field]}


def publish(path, payload, protected, closure):
    path = Path(path)
    resolved = path.resolve()
    require(resolved not in {Path(x).resolve() for x in protected},
            "output aliases protected input")
    encoded = (json.dumps(payload, sort_keys=True, separators=(",", ":")) +
               "\n").encode()
    path.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_CREAT | os.O_EXCL | os.O_RDWR
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags, 0o600)
    try:
        require(stat.S_ISREG(os.fstat(descriptor).st_mode),
                "output descriptor not regular")
        closure()
        with os.fdopen(descriptor, "wb", closefd=False) as handle:
            handle.write(encoded); handle.flush(); os.fsync(handle.fileno())
        require(sha_file(path) == sha(encoded), "published bytes mismatch")
        closure()
        require(sha_file(path) == sha(encoded),
                "published bytes changed after closure")
    except Exception:
        rejection = b'{"status":"rejected-incomplete-degree3-output"}\n'
        os.lseek(descriptor, 0, os.SEEK_SET)
        os.ftruncate(descriptor, 0)
        os.write(descriptor, rejection)
        os.fsync(descriptor)
        raise
    finally:
        os.close(descriptor)
    return sha(encoded)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--gate", required=True)
    parser.add_argument("--mode", choices=("preflight", "production"),
                        default="preflight")
    parser.add_argument("--authorization")
    parser.add_argument("--output", required=True)
    parser.add_argument("--progress", action="store_true")
    args = parser.parse_args()

    gate, gate_sha, gate_raw = load_gate(args.gate)
    driver_relative = str(Path(__file__).resolve().relative_to(PROJECT))
    driver_sha = gate["source_hashes"][driver_relative]
    require(driver_sha == sha_file(__file__), "driver self hash mismatch")
    if args.mode == "production":
        require(args.authorization is not None,
                "production requires authorization")
        auth_sha, auth_raw = authorization(
            args.authorization, gate_sha, driver_sha)
    else:
        require(args.authorization is None,
                "preflight rejects authorization")
        auth_sha, auth_raw = None, None

    protected = [args.gate, __file__, INPUT, REFERENCE]
    if args.authorization:
        protected.append(args.authorization)
    start_snapshot = dependency_snapshot(gate)
    if args.mode == "preflight":
        payload = {
            "status": "c10-d4-degree3-moment-preflight-pass",
            "rigorous_forms": False,
            "theorem_ready": False,
            "production_run_performed": False,
            "gate_sha256": gate_sha,
            "driver_sha256": driver_sha,
            "tag_schema_sha256": TAG_SCHEMA_SHA,
            "expected_counts": EXPECTED_COUNTS,
            "resource_gate": gate["resource_gate"],
            "validation_targets": gate["validation_targets"],
        }
        def preflight_closure():
            require(dependency_snapshot(gate) == start_snapshot and
                    Path(args.gate).read_bytes() == gate_raw,
                    "preflight closure changed")
        digest = publish(args.output, payload, protected, preflight_closure)
        print(json.dumps({"status": payload["status"],
                          "output_sha256": digest}, sort_keys=True))
        return

    labels, coefficients, reference, input_raw, reference_raw = load_data()
    support = ei.OneStratumSupport(
        48, PARAMETERS["alpha"], PARAMETERS["delta"], PARAMETERS["eta"],
        PARAMETERS["beta1"], PARAMETERS["beta2"], PARAMETERS["beta3plus"])

    fused_start = time.perf_counter()
    fused = FusedStratumMomentTableEvaluator(
        support, labels, coefficients, Q, degree=DEGREE
    ).evaluate_moment_forms(progress=args.progress)
    fused_seconds = time.perf_counter() - fused_start
    validate_moment_tag_schema(fused["tag_schema"], DEGREE)

    unfused_start = time.perf_counter()
    unfused = StratumMomentTableEvaluator(
        support, labels, coefficients, Q, degree=DEGREE
    ).evaluate_moment_forms(progress=args.progress)
    unfused_seconds = time.perf_counter() - unfused_start
    total_seconds = fused_seconds + unfused_seconds

    for key in ("labels", "a_matrix", "b_matrix", "i_moments", "j_moments"):
        require(fused[key] == unfused[key], f"fused/unfused mismatch: {key}")
    observed = {key: (len(fused["labels"]) if key == "matrix_dimension"
                      else fused[key]) for key in EXPECTED_COUNTS}
    require(observed == EXPECTED_COUNTS, "degree-three exact count mismatch")

    labels2, ref_a, ref_b = reference_dense(
        support, labels, coefficients, reference)
    powers3 = channel_powers(3)
    power_to_index3 = {p: i for i, p in enumerate(powers3)}
    positions3 = {label: i for i, label in enumerate(fused["labels"])}
    positions2in3 = [positions3[(r, power_to_index3[channel_powers(2)[p]])]
                     for r, p in labels2]
    require([[fused["a_matrix"][i][j] for j in positions2in3]
             for i in positions2in3] == ref_a,
            "degree-two I principal submatrix mismatch")
    require([[fused["b_matrix"][i][j] for j in positions2in3]
             for i in positions2in3] == ref_b,
            "degree-two 48J principal submatrix mismatch")
    vector = embedded_degree2_vector(fused["labels"], reference, labels2)
    denominator = quadratic(fused["a_matrix"], vector)
    numerator = quadratic(fused["b_matrix"], vector)
    require(denominator == Q(reference["denominator"]) and
            numerator == Q(reference["numerator"]),
            "embedded particular contraction mismatch")

    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    resource_pass = (
        fused_seconds <= gate["resource_gate"]["maximum_fused_seconds"] and
        total_seconds <= gate["resource_gate"][
            "maximum_total_validation_seconds"] and
        peak <= gate["resource_gate"]["maximum_peak_rss_kib"])
    require(resource_pass, "degree-three resource gate failed")
    def production_closure():
        require(dependency_snapshot(gate) == start_snapshot and
                Path(args.gate).read_bytes() == gate_raw and
                Path(args.authorization).read_bytes() == auth_raw and
                INPUT.read_bytes() == input_raw and
                REFERENCE.read_bytes() == reference_raw,
                "production closure changed")
    production_closure()
    payload = {
        "status": "exact-c10-d4-degree3-moment-pass",
        "rigorous_forms": True,
        "theorem_ready": False,
        "scope": "D4 degree-three finite space only; no D12 sign",
        "gate_sha256": gate_sha,
        "authorization_sha256": auth_sha,
        "driver_sha256": driver_sha,
        "input_sha256": INPUT_SHA,
        "reference_sha256": REFERENCE_SHA,
        "tag_schema_sha256": TAG_SCHEMA_SHA,
        "expected_counts": EXPECTED_COUNTS,
        "all_fused_unfused_entries_equal": True,
        "all_degree2_oracle_entries_equal": True,
        "particular_denominator": str(denominator),
        "particular_numerator": str(numerator),
        "particular_quotient": str(numerator / denominator),
        "a_matrix_sha256": matrix_sha(fused["a_matrix"]),
        "b48_matrix_sha256": matrix_sha(fused["b_matrix"]),
        "i_moment_rows": moment_rows(fused["i_moments"]),
        "j_moment_rows": moment_rows(fused["j_moments"], j=True),
        "fused_seconds": fused_seconds,
        "unfused_seconds": unfused_seconds,
        "total_validation_seconds": total_seconds,
        "peak_rss_kib": peak,
        "resource_gate_passed": True,
    }
    digest = publish(args.output, payload, protected, production_closure)
    print(json.dumps({"status": payload["status"],
                      "output_sha256": digest,
                      "particular_quotient": payload["particular_quotient"],
                      "total_validation_seconds": total_seconds,
                      "peak_rss_kib": peak}, sort_keys=True))


if __name__ == "__main__":
    main()
