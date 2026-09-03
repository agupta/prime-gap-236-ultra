#!/usr/bin/env python3
"""Read-only exact-oracle whitening postmortem for the D4 v5 calibration.

This diagnostic never changes the calibrated records and never certifies a
sieve quotient.  It asks one predeclared question: does a fixed rational
coordinate transform, constructed solely from the exact D4 denominator
oracle, restore all 93 active coordinates under the unchanged ``1e-12``
numerical-rank threshold?
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import os
import sys
from fractions import Fraction
from pathlib import Path

HERE = Path(__file__).resolve()
REPO_ROOT = HERE.parents[3]
CODE_DIR = HERE.parent
DRIVER = CODE_DIR / "importance_d4_calibration.py"
RESULT = REPO_ROOT / \
    "agents/structural-basis/results/importance_d4_calibration_v5_production.json"
AUDIT = REPO_ROOT / \
    "agents/structural-basis/results/importance_d4_calibration_v5_production_audit_v3.json"
GATE = REPO_ROOT / \
    "agents/structural-basis/results/importance_d4_calibration_gate_v5.json"
AUTHORIZATION = REPO_ROOT / \
    "agents/structural-basis/results/importance_d4_calibration_v5_authorization.json"
RECORD_DIRECTORY = REPO_ROOT / \
    "agents/structural-basis/results/importance_d4_calibration_v5_records"

DRIVER_SHA256 = \
    "b0b4350ff1804530724c87b8693aa4dd0059904f3eb9d72696497fb3c90c1b41"
GATE_SHA256 = \
    "860a9a51284187388e2384b7ca19615dc7d17eb523a7a4fa4d5617e2e6f29196"
AUTHORIZATION_SHA256 = \
    "11f75e01e019be90be1caea052f8e6452d59f8d59bbaea9bddf5022a9bb978dd"
AUDITOR_SHA256 = \
    "7a0685f089125654f5faddced809cce784f9b7aabfd9c4ae8e669771710ab2da"
DECISION_TABLE_SHA256 = \
    "3660ae47168ccbadb8cfa2cb2152deecf64321f9cd78ba2df1d4a0f8a68c29b4"
CONVENTIONS_SHA256 = \
    "43c7a2d225f5ee676ee345194219f9460a5a24135a7ccc052de47368a92efde2"
SCHEDULE_SHA256 = \
    "7d618324c2167e2eaf8caf8ba7c6a097a881ef23e8d35350469c78ea182fe755"
NUMPY_VERSION = "2.2.4"
NUMPY_INIT_SHA256 = \
    "6ae17b070c0f70a8e3cad89a510a256942e5a1f37ea5feb120cec167ed2a6236"
RANK_TOLERANCE = 1e-12
np = None

LOCAL_MODULE_PATHS = {
    "importance_conditional":
        "agents/structural-basis/code/importance_conditional.py",
    "importance_density":
        "agents/structural-basis/code/importance_density.py",
    "importance_envelope":
        "agents/structural-basis/code/importance_envelope.py",
    "importance_oracle":
        "agents/structural-basis/code/importance_oracle.py",
    "importance_point_eval":
        "agents/structural-basis/code/importance_point_eval.py",
    "importance_sampler":
        "agents/structural-basis/code/importance_sampler.py",
    "importance_statistics":
        "agents/structural-basis/code/importance_statistics.py",
    "importance_stratum_weights":
        "agents/structural-basis/code/importance_stratum_weights.py",
}

RESULT_KEYS = {
    "status", "rigorous", "theorem_ready", "mode", "gate_path",
    "gate_sha256", "driver_sha256", "authorization_sha256",
    "parent_result_sha256", "gate_binding", "authorization_binding",
    "parent_result_binding", "wall_seconds", "peak_rss_kib",
    "float_encoding", "conventions", "schedule", "records",
    "record_checkpoints", "analysis", "analysis_failure",
    "fresh_exact_reconstruction_required",
}
AUDIT_KEYS = {
    "status", "rigorous", "theorem_ready", "scope", "decision",
    "decision_exit_code", "driver_sha256", "gate_sha256",
    "authorization_sha256", "production_result_binding",
    "decision_table_sha256", "auditor_sha256",
    "supersedes_invalid_auditor_sha256", "record_directory_binding",
    "checkpoint_count", "record_leaf_names_sha256",
    "checkpoint_manifest_sha256", "records_core_sha256",
    "analysis_core_sha256", "analysis_failure", "hard_gate_failures",
    "statistical_gate_failures", "wall_seconds", "peak_rss_kib",
    "numpy_version", "numpy_init_sha256",
    "fresh_exact_reconstruction_required", "never_implies",
}


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def sha256_file(path):
    return sha256_bytes(Path(path).read_bytes())


def require_sha256(value, name):
    if (not isinstance(value, str) or len(value) != 64 or
            any(character not in "0123456789abcdef" for character in value)):
        raise ValueError(f"{name} is not canonical lowercase SHA-256")
    return value


def canonical_sha256(value):
    return sha256_bytes(json.dumps(
        value, sort_keys=True, separators=(",", ":"),
        allow_nan=False).encode())


def validate_expected_self(expected):
    expected = require_sha256(expected, "expected postmortem SHA-256")
    if sha256_file(HERE) != expected:
        raise ValueError("postmortem bytes differ from external trust root")
    return expected


def _validate_public_binding(value, expected, name):
    if (not isinstance(value, dict) or set(value) != {
            "path", "sha256", "device", "inode"} or
            value != {key: expected[key]
                      for key in ("path", "sha256", "device", "inode")}):
        raise ValueError(f"{name} differs from the exact file snapshot")


def expected_checkpoint_names():
    return [f"{target}_r{stratum:02d}_rep{replicate}_initial.json"
            for target in ("I", "J") for stratum in range(16)
            for replicate in range(4)]


def validate_completed_artifacts(result, audit, *, result_snapshot,
                                 gate_snapshot, authorization_snapshot):
    failure = {
        "exception_type": "ArithmeticError",
        "message": "active denominator matrix is numerically rank deficient",
    }
    if (not isinstance(result, dict) or set(result) != RESULT_KEYS or
            result["status"] != "d4-stratified-calibration-rejected" or
            result["rigorous"] is not False or
            result["theorem_ready"] is not False or
            result["mode"] != "production" or
            result["gate_path"] != str(GATE.relative_to(REPO_ROOT)) or
            result["gate_sha256"] != GATE_SHA256 or
            result["driver_sha256"] != DRIVER_SHA256 or
            result["authorization_sha256"] != AUTHORIZATION_SHA256 or
            result["parent_result_sha256"] is not None or
            result["parent_result_binding"] is not None or
            result["float_encoding"] != "python-float-hex" or
            canonical_sha256(result["conventions"]) != CONVENTIONS_SHA256 or
            canonical_sha256(result["schedule"]) != SCHEDULE_SHA256 or
            not isinstance(result["records"], list) or
            len(result["records"]) != 128 or
            not isinstance(result["record_checkpoints"], list) or
            len(result["record_checkpoints"]) != 128 or
            result["analysis"] is not None or
            result["analysis_failure"] != failure or
            result["fresh_exact_reconstruction_required"] is not True):
        raise ValueError("completed v5 result schema/identity is invalid")
    _validate_public_binding(
        result["gate_binding"], gate_snapshot, "result gate binding")
    _validate_public_binding(
        result["authorization_binding"], authorization_snapshot,
        "result authorization binding")
    expected_paths = [str(RECORD_DIRECTORY.resolve() / name)
                      for name in expected_checkpoint_names()]
    if [item.get("path") if isinstance(item, dict) else None
            for item in result["record_checkpoints"]] != expected_paths:
        raise ValueError("completed checkpoint order/path is invalid")
    for item in result["record_checkpoints"]:
        if (set(item) != {"path", "sha256", "device", "inode"} or
                require_sha256(item["sha256"], "checkpoint SHA-256") !=
                item["sha256"] or
                any(isinstance(item[key], bool) or
                    not isinstance(item[key], int) or item[key] < 0
                    for key in ("device", "inode"))):
            raise ValueError("completed checkpoint binding is malformed")
    records_core = canonical_sha256(result["records"])
    analysis_core = canonical_sha256({
        "analysis": result["analysis"],
        "analysis_failure": result["analysis_failure"],
    })
    if (not isinstance(audit, dict) or set(audit) != AUDIT_KEYS or
            audit["status"] !=
            "complete-independent-d4-v5-production-audit" or
            audit["rigorous"] is not False or
            audit["theorem_ready"] is not False or
            audit["scope"] !=
            "D4-stratified-importance-calibration-discovery-only" or
            audit["decision"] != "IMPLEMENTATION_REJECTED" or
            audit["decision_exit_code"] != 1 or
            audit["driver_sha256"] != DRIVER_SHA256 or
            audit["gate_sha256"] != GATE_SHA256 or
            audit["authorization_sha256"] != AUTHORIZATION_SHA256 or
            audit["decision_table_sha256"] != DECISION_TABLE_SHA256 or
            audit["auditor_sha256"] != AUDITOR_SHA256 or
            audit["supersedes_invalid_auditor_sha256"] !=
            "4e9ab0002b3f33019162d537f03310880e0ff788d48b36239957d05cb9608cf7" or
            audit["checkpoint_count"] != 128 or
            audit["record_leaf_names_sha256"] != canonical_sha256(
                sorted(expected_checkpoint_names())) or
            audit["checkpoint_manifest_sha256"] != canonical_sha256(
                result["record_checkpoints"]) or
            audit["records_core_sha256"] != records_core or
            audit["analysis_core_sha256"] != analysis_core or
            audit["analysis_failure"] != failure or
            audit["hard_gate_failures"] != [] or
            audit["statistical_gate_failures"] != [] or
            audit["wall_seconds"] != result["wall_seconds"] or
            audit["peak_rss_kib"] != result["peak_rss_kib"] or
            audit["numpy_version"] != NUMPY_VERSION or
            audit["numpy_init_sha256"] != NUMPY_INIT_SHA256 or
            audit["fresh_exact_reconstruction_required"] is not True or
            audit["never_implies"] != [
                "rigorous_error_bound", "exact_sieve_quotient",
                "H1_at_most_236"]):
        raise ValueError("completed v5 audit schema/identity is invalid")
    _validate_public_binding(
        audit["production_result_binding"], result_snapshot,
        "audit production-result binding")
    directory = audit["record_directory_binding"]
    if (not isinstance(directory, dict) or set(directory) != {
            "path", "device", "inode"} or
            directory["path"] != str(RECORD_DIRECTORY.resolve()) or
            any(isinstance(directory[key], bool) or
                not isinstance(directory[key], int) or directory[key] < 0
                for key in ("device", "inode"))):
        raise ValueError("audit record-directory binding is invalid")
    return {"records_core_sha256": records_core,
            "analysis_core_sha256": analysis_core}


def _fraction_matrix(matrix):
    if (not isinstance(matrix, (list, tuple)) or not matrix or
            any(not isinstance(row, (list, tuple)) or
                len(row) != len(matrix) for row in matrix)):
        raise ValueError("exact denominator must be a nonempty square matrix")
    answer = [[entry if isinstance(entry, Fraction) else Fraction(entry)
               for entry in row] for row in matrix]
    if any(answer[i][j] != answer[j][i]
           for i in range(len(answer)) for j in range(i)):
        raise ValueError("exact denominator is not symmetric")
    return answer


def exact_ldlt(matrix):
    """Return exact unit-lower ``L`` and positive diagonal ``D``."""
    a = _fraction_matrix(matrix)
    dimension = len(a)
    lower = [[Fraction(int(i == j)) for j in range(dimension)]
             for i in range(dimension)]
    diagonal = [Fraction(0) for _ in range(dimension)]
    for j in range(dimension):
        pivot = a[j][j] - sum(
            lower[j][k] * lower[j][k] * diagonal[k]
            for k in range(j))
        if pivot <= 0:
            raise ArithmeticError(
                f"exact denominator is not positive definite at pivot {j}")
        diagonal[j] = pivot
        for i in range(j + 1, dimension):
            residual = a[i][j] - sum(
                lower[i][k] * lower[j][k] * diagonal[k]
                for k in range(j))
            lower[i][j] = residual / pivot
    # An exact reconstruction is cheap at D4 and makes the transform's trust
    # boundary explicit rather than relying on the elimination narrative.
    for i in range(dimension):
        for j in range(i + 1):
            rebuilt = sum(lower[i][k] * diagonal[k] * lower[j][k]
                          for k in range(j + 1))
            if rebuilt != a[i][j]:
                raise ArithmeticError("exact LDL reconstruction failed")
    return lower, diagonal


def power_two_equilibrators(diagonal):
    """Choose rational ``s=2^e`` with ``1 <= s^2 D < 4`` exactly."""
    scales = []
    exponents = []
    scaled_pivots = []
    for pivot in diagonal:
        pivot = Fraction(pivot)
        if pivot <= 0:
            raise ValueError("LDL pivot must be positive")
        exponent = 0
        scaled = pivot
        while scaled < 1:
            scaled *= 4
            exponent += 1
        while scaled >= 4:
            scaled /= 4
            exponent -= 1
        scale = (Fraction(2 ** exponent) if exponent >= 0 else
                 Fraction(1, 2 ** (-exponent)))
        if not (1 <= scale * scale * pivot < 4):
            raise AssertionError("power-of-two equilibration invariant failed")
        scales.append(scale)
        exponents.append(exponent)
        scaled_pivots.append(scale * scale * pivot)
    return scales, exponents, scaled_pivots


def exact_whitening_transform(lower, scales):
    """Return exact ``T=L^{-T} diag(scales)`` by back substitution."""
    dimension = len(lower)
    if len(scales) != dimension:
        raise ValueError("scale/LDL dimensions differ")
    transform = [[Fraction(0) for _ in range(dimension)]
                 for _ in range(dimension)]
    for column in range(dimension):
        for i in range(dimension - 1, -1, -1):
            right = scales[column] if i == column else Fraction(0)
            right -= sum(lower[k][i] * transform[k][column]
                         for k in range(i + 1, dimension))
            # L is unit lower, hence L^T has unit diagonal.
            transform[i][column] = right
    for i in range(dimension):
        for j in range(dimension):
            observed = sum(lower[k][i] * transform[k][j]
                           for k in range(dimension))
            expected = scales[j] if i == j else 0
            if observed != expected:
                raise ArithmeticError("exact L^T T = S check failed")
    return transform


def canonical_transform_sha256(transform):
    encoded = json.dumps(
        [[str(entry) for entry in row] for row in transform],
        separators=(",", ":"), allow_nan=False).encode()
    return sha256_bytes(encoded)


def transform_float_form(matrix, transform):
    values = np.asarray(matrix, dtype=float)
    t_matrix = np.asarray(
        [[float(entry) for entry in row] for row in transform], dtype=float)
    if (values.ndim != 2 or values.shape[0] != values.shape[1] or
            values.shape != t_matrix.shape or
            not np.all(np.isfinite(values)) or
            not np.all(np.isfinite(t_matrix))):
        raise ArithmeticError("sampled form/transform is nonfinite or malformed")
    answer = t_matrix.T @ ((values + values.T) / 2) @ t_matrix
    answer = (answer + answer.T) / 2
    if not np.all(np.isfinite(answer)):
        raise ArithmeticError("transformed sampled form is nonfinite")
    return answer


def equilibrated_spectrum(matrix, tolerance=RANK_TOLERANCE):
    matrix = np.asarray(matrix, dtype=float)
    matrix = (matrix + matrix.T) / 2
    diagonal = np.diag(matrix)
    if np.any(~np.isfinite(matrix)) or np.any(diagonal <= 0):
        raise ArithmeticError("sampled active denominator has invalid diagonal")
    scale_vector = 1 / np.sqrt(diagonal)
    equilibrated = scale_vector[:, None] * matrix * scale_vector[None, :]
    eigenvalues = np.linalg.eigvalsh(equilibrated)
    scale = max(float(np.max(np.abs(eigenvalues), initial=0)), 1.0)
    threshold = tolerance * scale
    return {
        "dimension": len(diagonal),
        "rank": int(np.sum(eigenvalues > threshold)),
        "threshold": threshold,
        "smallest": float(eigenvalues[0]),
        "largest": float(eigenvalues[-1]),
        "condition_if_positive": (
            float(eigenvalues[-1] / eigenvalues[0])
            if eigenvalues[0] > 0 else None),
    }


def degree_ordered_active_indices(oracle):
    powers = oracle["channel_powers"]
    active = [index for index in range(oracle["dimension"])
              if oracle["E_I"][index][index] > 0]
    active.sort(key=lambda index: (
        sum(powers[index % len(powers)]),
        index // len(powers), index % len(powers)))
    counts = {
        degree: sum(sum(powers[index % len(powers)]) <= degree
                    for index in active)
        for degree in (0, 1, 2)}
    if counts != {0: 16, 1: 47, 2: 93}:
        raise ArithmeticError(f"unexpected exact active counts: {counts}")
    return active, counts


def sampled_degree_rank_spectra(sampled_a, active_indices, degree_counts,
                                transform):
    sampled_active = np.asarray(sampled_a, dtype=float)[
        np.ix_(active_indices, active_indices)]
    answer = {}
    for degree in (0, 1, 2):
        dimension = degree_counts[degree]
        degree_transform = [row[:dimension]
                            for row in transform[:dimension]]
        degree_a = sampled_active[:dimension, :dimension]
        answer[str(degree)] = {
            "original": equilibrated_spectrum(degree_a),
            "whitened": equilibrated_spectrum(
                transform_float_form(degree_a, degree_transform)),
        }
    return answer


def whitening_postmortem(exact_a, sampled_a, sampled_b, active_indices,
                         degree_counts):
    exact_active = [[exact_a[i][j] for j in active_indices]
                    for i in active_indices]
    sampled_active_a = np.asarray(sampled_a, dtype=float)[
        np.ix_(active_indices, active_indices)]
    sampled_active_b = np.asarray(sampled_b, dtype=float)[
        np.ix_(active_indices, active_indices)]
    lower, diagonal = exact_ldlt(exact_active)
    scales, exponents, scaled_pivots = power_two_equilibrators(diagonal)
    transform = exact_whitening_transform(lower, scales)
    rank_spectra = sampled_degree_rank_spectra(
        sampled_a, active_indices, degree_counts, transform)
    reports = {}
    for degree in (0, 1, 2):
        dimension = degree_counts[degree]
        degree_transform = [row[:dimension]
                            for row in transform[:dimension]]
        degree_a = sampled_active_a[:dimension, :dimension]
        degree_b = sampled_active_b[:dimension, :dimension]
        transformed_b = transform_float_form(degree_b, degree_transform)
        original = rank_spectra[str(degree)]["original"]
        whitened = rank_spectra[str(degree)]["whitened"]
        reports[str(degree)] = {
            "active_dimension": dimension,
            "original_sampled_spectrum": original,
            "exact_whitened_diagonal_min": str(min(scaled_pivots[:dimension])),
            "exact_whitened_diagonal_max": str(max(scaled_pivots[:dimension])),
            "exact_whitened_condition_less_than_four":
                max(scaled_pivots[:dimension]) /
                min(scaled_pivots[:dimension]) < 4,
            "whitened_sampled_spectrum": whitened,
            "unchanged_rank_gate_pass": whitened["rank"] == dimension,
            # Kept for a subsequent root calculation; it is not a rigorous
            # quotient and is deliberately not interpreted here.
            "transformed_numerator_frobenius":
                float(np.linalg.norm(transformed_b)),
        }
    return {
        "active_indices_degree_ordered": active_indices,
        "ldlt_pivot_count": len(diagonal),
        "scale_exponent_min": min(exponents),
        "scale_exponent_max": max(exponents),
        "transform_sha256": canonical_transform_sha256(transform),
        "degree_reports": reports,
        "all_93_active_coordinates_preserved":
            reports["2"]["active_dimension"] == 93,
        "all_degrees_pass_unchanged_rank_gate": all(
            report["unchanged_rank_gate_pass"]
            for report in reports.values()),
    }


def deletion_rank_summary(deletion_spectra, degree_counts):
    if len(deletion_spectra) != 128:
        raise ValueError("rank postmortem requires all 128 chain deletions")
    answer = {}
    for degree in (0, 1, 2):
        key = str(degree)
        dimension = degree_counts[degree]
        original_failures = []
        whitened_failures = []
        original_smallest = math.inf
        whitened_smallest = math.inf
        original_min_rank = dimension
        whitened_min_rank = dimension
        original_max_condition = 0.0
        whitened_max_condition = 0.0
        for item in deletion_spectra:
            original = item["spectra"][key]["original"]
            whitened = item["spectra"][key]["whitened"]
            original_min_rank = min(original_min_rank, original["rank"])
            whitened_min_rank = min(whitened_min_rank, whitened["rank"])
            original_smallest = min(original_smallest, original["smallest"])
            whitened_smallest = min(whitened_smallest,
                                    whitened["smallest"])
            if original["condition_if_positive"] is not None:
                original_max_condition = max(
                    original_max_condition,
                    original["condition_if_positive"])
            if whitened["condition_if_positive"] is not None:
                whitened_max_condition = max(
                    whitened_max_condition,
                    whitened["condition_if_positive"])
            if original["rank"] != dimension:
                original_failures.append({
                    "identity": item["identity"], "spectrum": original})
            if whitened["rank"] != dimension:
                whitened_failures.append({
                    "identity": item["identity"], "spectrum": whitened})
        answer[key] = {
            "active_dimension": dimension,
            "deletion_count": len(deletion_spectra),
            "original_min_rank": original_min_rank,
            "whitened_min_rank": whitened_min_rank,
            "original_min_smallest_eigenvalue": original_smallest,
            "whitened_min_smallest_eigenvalue": whitened_smallest,
            "original_max_condition_if_positive": original_max_condition,
            "whitened_max_condition_if_positive": whitened_max_condition,
            "original_rank_failure_count": len(original_failures),
            "whitened_rank_failure_count": len(whitened_failures),
            "original_rank_failures": original_failures,
            "whitened_rank_failures": whitened_failures,
        }
    return answer


def load_frozen_driver():
    global np
    if sha256_file(DRIVER) != DRIVER_SHA256:
        raise ValueError("frozen v5 driver bytes changed")
    occupied = sorted(name for name in LOCAL_MODULE_PATHS
                      if name in sys.modules)
    occupied_numpy = sorted(name for name in sys.modules
                            if name == "numpy" or name.startswith("numpy."))
    if occupied or occupied_numpy:
        raise ValueError(
            "standalone postmortem rejects preloaded computational modules")
    if str(CODE_DIR) not in sys.path:
        sys.path.insert(0, str(CODE_DIR))
    specification = importlib.util.spec_from_file_location(
        "importance_d4_rank_postmortem_frozen_driver", DRIVER)
    if specification is None or specification.loader is None:
        raise ImportError("cannot load frozen v5 driver")
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    if module.sha256_file(module.HERE) != DRIVER_SHA256:
        raise ValueError("loaded v5 driver differs from frozen bytes")
    np = sys.modules.get("numpy")
    if (np is None or np.__version__ != NUMPY_VERSION or
            Path(np.__file__).resolve() != Path(
                "/usr/lib/python3/dist-packages/numpy/__init__.py") or
            sha256_file(np.__file__) != NUMPY_INIT_SHA256):
        raise ValueError("NumPy runtime differs from frozen v5 runtime")
    return module


def bind_loaded_runtime(driver, gate):
    bindings = {
        str(HERE): sha256_file(HERE),
        str(DRIVER.resolve()): DRIVER_SHA256,
        str(Path(np.__file__).resolve()): NUMPY_INIT_SHA256,
    }
    for name, relative in LOCAL_MODULE_PATHS.items():
        module = sys.modules.get(name)
        if module is None or not isinstance(getattr(module, "__file__", None),
                                            str):
            raise ValueError(f"postmortem dependency {name} was not loaded")
        path = Path(module.__file__).resolve()
        expected_path = (REPO_ROOT / relative).resolve()
        expected_sha = gate["source_hashes"].get(relative)
        if (path != expected_path or expected_sha is None or
                sha256_file(path) != expected_sha):
            raise ValueError(f"postmortem dependency {name} is not gate-pinned")
        bindings[str(path)] = expected_sha
    return bindings


def rebind_runtime(bindings):
    for path, expected in bindings.items():
        if sha256_file(path) != expected:
            raise ValueError("postmortem dependency changed during computation")
    return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--expected-postmortem-sha256", required=True)
    parser.add_argument("--expected-result-sha256", required=True)
    parser.add_argument("--expected-audit-sha256", required=True)
    args = parser.parse_args()
    expected_self = validate_expected_self(
        args.expected_postmortem_sha256)
    expected_result = require_sha256(
        args.expected_result_sha256, "completed result SHA-256")
    expected_audit = require_sha256(
        args.expected_audit_sha256, "completed audit SHA-256")
    driver = load_frozen_driver()
    gate = driver.load_and_validate_gate(GATE)
    if gate["sha256"] != GATE_SHA256:
        raise ValueError("postmortem gate differs from frozen v5")
    runtime_bindings = bind_loaded_runtime(driver, gate["gate"])
    if runtime_bindings[str(HERE)] != expected_self:
        raise ValueError("runtime closure differs from external self token")
    authorization_snapshot = driver.read_file_snapshot(AUTHORIZATION)
    if authorization_snapshot["sha256"] != AUTHORIZATION_SHA256:
        raise ValueError("v5 authorization differs from frozen bytes")
    result_snapshot = driver.read_file_snapshot(RESULT)
    audit_snapshot = driver.read_file_snapshot(AUDIT)
    if result_snapshot["sha256"] != expected_result:
        raise ValueError("completed result differs from external token")
    if audit_snapshot["sha256"] != expected_audit:
        raise ValueError("completed audit differs from external token")
    result = driver.strict_json_bytes(result_snapshot["data"], "v5 result")
    audit = driver.strict_json_bytes(audit_snapshot["data"], "v5 audit")
    cores = validate_completed_artifacts(
        result, audit, result_snapshot=result_snapshot,
        gate_snapshot=gate,
        authorization_snapshot=authorization_snapshot)
    oracle_path = REPO_ROOT / driver.REQUIRED_DATA_PATHS[0]
    weights_path = REPO_ROOT / driver.REQUIRED_DATA_PATHS[2]
    oracle = driver.load_exact_expectation_oracle(oracle_path)
    weights = driver.load_stratum_weights(
        weights_path,
        gate["gate"]["data_hashes"][driver.REQUIRED_DATA_PATHS[2]],
        prefix="baseline_", j_scale_to_numerator=1)
    reconstruction = driver.reconstruct_matrices(
        result["records"], oracle, weights, gate["gate"]["schedule"],
        diagnostics=False)
    active, counts = degree_ordered_active_indices(oracle)
    report = whitening_postmortem(
        oracle["E_I"], reconstruction["A"], reconstruction["B"],
        active, counts)
    # The production exception was raised inside the 128-member deletion
    # audit, not necessarily at the full-sample matrix.  Reproduce every
    # deletion under both the original chart and the one fixed transform.
    exact_active = [[oracle["E_I"][i][j] for j in active] for i in active]
    lower, diagonal = exact_ldlt(exact_active)
    scales, _, _ = power_two_equilibrators(diagonal)
    transform = exact_whitening_transform(lower, scales)
    deletion_spectra = []
    for record in result["records"]:
        identity_tuple = driver._record_identity(record)
        deleted = driver.reconstruct_matrices(
            result["records"], oracle, weights,
            gate["gate"]["schedule"],
            excluded_identity=identity_tuple, diagnostics=False)
        deletion_spectra.append({
            "identity": {
                "target": identity_tuple[0],
                "stratum": identity_tuple[1],
                "replicate": identity_tuple[2],
            },
            "spectra": sampled_degree_rank_spectra(
                deleted["A"], active, counts, transform),
        })
    deletion_summary = deletion_rank_summary(deletion_spectra, counts)
    deletion_gate_pass = all(
        item["whitened_rank_failure_count"] == 0
        for item in deletion_summary.values())
    payload = {
        "status": "complete-read-only-d4-v5-rank-postmortem",
        "rigorous": False,
        "theorem_ready": False,
        "result_sha256": expected_result,
        "audit_sha256": expected_audit,
        "postmortem_sha256": expected_self,
        "driver_sha256": DRIVER_SHA256,
        "gate_sha256": GATE_SHA256,
        "rank_tolerance_unchanged": "1/1000000000000",
        "coordinate_transform":
            "degree-ordered exact rational LDL^-T times rational powers of 2",
        **report,
        "leave_one_chain_deletion_rank_summary": deletion_summary,
        "all_128_deletions_pass_whitened_unchanged_rank_gate":
            deletion_gate_pass,
        "fixed_transform_reopening_gate_pass":
            report["all_degrees_pass_unchanged_rank_gate"] and
            deletion_gate_pass,
        "records_core_sha256": cores["records_core_sha256"],
        "analysis_core_sha256": cores["analysis_core_sha256"],
        "runtime_dependency_hashes": runtime_bindings,
        "never_implies": ["rigorous_error_bound", "exact_sieve_quotient",
                          "H1_at_most_236"],
    }
    rebind_runtime(runtime_bindings)
    if sha256_file(RESULT) != expected_result or \
            sha256_file(AUDIT) != expected_audit or \
            sha256_file(AUTHORIZATION) != AUTHORIZATION_SHA256 or \
            sha256_file(GATE) != GATE_SHA256:
        raise ValueError("completed postmortem inputs changed during computation")
    print(json.dumps(payload, sort_keys=True, separators=(",", ":"),
                     allow_nan=False))


if __name__ == "__main__":
    main()
