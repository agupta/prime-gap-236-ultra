#!/usr/bin/env python3
"""Exact-whitened v6 D4 stratified importance calibration.

This is a discovery calibration only.  It reuses the audited v5 chain,
checkpoint, statistics, and publication machinery, while replacing the
finite multiplier coordinates by one gate-pinned exact rational transform
and evaluating those transformed features directly at every retained point.
"""

from __future__ import annotations

import argparse
import copy
import json
import math
import resource
import sys
import time
from decimal import Decimal, localcontext
from fractions import Fraction
from pathlib import Path

import numpy as np

import importance_conditional
import importance_d4_calibration as v5
from importance_envelope_v6 import (
    bounded_outer_entry,
    j_envelope_log_density,
    j_envelope_point,
)
from importance_whitening_v6 import (
    WhitenedC10ImportanceDensity,
    load_transformed_oracle,
)


HERE = Path(__file__).resolve()
REPO_ROOT = HERE.parents[3]
DRIVER_RELATIVE = \
    "agents/structural-basis/code/importance_d4_calibration_v6.py"
TRANSFORM_SHA256 = \
    "f2a0e8325809956c6883191d04cde6bc67ea74c4af34f86dce7a1ac60c4ac1fb"
V5_GATE_SHA256 = \
    "860a9a51284187388e2384b7ca19615dc7d17eb523a7a4fa4d5617e2e6f29196"
V5_EXPECTED_CONVENTIONS = v5.expected_conventions
V5_VALIDATE_CHAIN_RECORD = v5.validate_chain_record

V6_ADDITIONAL_SOURCE_PATHS = (
    DRIVER_RELATIVE,
    "agents/structural-basis/code/build_importance_d4_calibration_gate_v6.py",
    "agents/structural-basis/code/importance_whitening_v6.py",
    "agents/structural-basis/code/importance_envelope_v6.py",
    "agents/structural-basis/code/importance_d4_rank_postmortem.py",
    "agents/structural-basis/tests/test_importance_whitening_v6.py",
    "agents/structural-basis/tests/test_importance_d4_calibration_v6.py",
    "agents/structural-basis/tests/test_importance_d4_rank_postmortem.py",
    "agents/structural-basis/IMPORTANCE-D4-CALIBRATION-V6-SPEC.md",
)
REQUIRED_SOURCE_PATHS = tuple(dict.fromkeys(
    tuple(v5.REQUIRED_SOURCE_PATHS) + V6_ADDITIONAL_SOURCE_PATHS))
REQUIRED_DATA_PATHS = tuple(v5.REQUIRED_DATA_PATHS) + (
    "agents/structural-basis/results/importance_d4_calibration_gate_v5.json",
)


def expected_conventions():
    base = V5_EXPECTED_CONVENTIONS()
    base.update({
        "feature_normalization":
            "direct exact-rational T^T times (L/alpha)^a*(Z/alpha)^b",
        "j_envelope":
            "g=sum_i(transformed_m_i^2); y_ij=m_i*m_j/g; "
            "z=(sum_r w_r*m_(r,0))^2/g",
        "exact_whitening": {
            "construction": "per-stratum degree-ordered A=L*D*L^T; "
                            "T=L^-T*S; S dyadic; 1<=S^2*D<4",
            "transform_sha256": TRANSFORM_SHA256,
            "active_dimensions": {"degree_0": 16, "degree_1": 47,
                                  "degree_2": 93},
            "direct_point_evaluation": True,
            "postprocess_v5_estimates": False,
            "rank_tolerance": "1/1000000000000",
        },
        "base_recombination":
            "old tagged constants = exact w_r times transformed tagged constants",
    })
    return base


def expected_extension_rule():
    return {
        "allowed_failure_classes": [
            "split_rhat", "batch_means_ess", "z_precision",
            "simultaneous_coverage"],
        "forbidden_after_any_algebraic_failure": True,
        "requires_max_standardized_discrepancy_at_most": "12",
        "continues_serialized_prng_states": True,
        "post_extension_samples_per_chain": 16000,
        "post_extension_batches_per_chain": 80,
    }


def expected_continuation_rule():
    return {
        "d12_screen_requires_v6_calibration_pass": True,
        "d12_leave_one_chain_quotient_strictly_greater_than": "1.005",
        "d12_lower_endpoint_strictly_greater_than": "1.002",
        "d12_screen_separately_authorized": True,
        "never_implies_exact_certificate": True,
    }


def load_and_validate_gate(path):
    snapshot = v5.read_file_snapshot(path)
    gate = v5.strict_json_bytes(snapshot["data"], "v6 calibration gate")
    v5._exact_keys(gate, {
        "status", "rigorous", "production_launch_authorized",
        "supersedes_gate_sha256", "float_encoding", "source_hashes",
        "data_hashes", "schedule", "thresholds", "conventions",
        "extension_rule", "continuation_rule"}, "v6 calibration gate")
    if (gate["status"] !=
            "frozen-d4-exact-whitened-calibration-prelaunch-v6" or
            gate["rigorous"] is not False or
            gate["production_launch_authorized"] is not False or
            gate["supersedes_gate_sha256"] != V5_GATE_SHA256 or
            gate["float_encoding"] != v5.FLOAT_ENCODING or
            gate["schedule"] != v5.expected_schedule() or
            gate["thresholds"] != v5.expected_thresholds() or
            gate["conventions"] != expected_conventions() or
            gate["extension_rule"] != expected_extension_rule() or
            gate["continuation_rule"] != expected_continuation_rule()):
        raise ValueError("v6 gate status, schedule, or conventions changed")
    for field, expected_paths in (
            ("source_hashes", REQUIRED_SOURCE_PATHS),
            ("data_hashes", REQUIRED_DATA_PATHS)):
        table = gate[field]
        if not isinstance(table, dict) or set(table) != set(expected_paths):
            raise ValueError(f"v6 {field} has missing or extra paths")
        for relative, expected in table.items():
            if (not isinstance(expected, str) or len(expected) != 64 or
                    any(character not in "0123456789abcdef"
                        for character in expected) or
                    v5.sha256_file(REPO_ROOT / relative) != expected):
                raise ValueError(f"v6 dependency mismatch: {relative}")
    return {**v5.public_binding(snapshot), "gate": gate}


def validate_adapter_provenance(adapter, gate):
    parameter_path, vector_path = REQUIRED_DATA_PATHS[:2]
    if (adapter.vector_sha256 != gate["data_hashes"][vector_path] or
            adapter.parameter_sha256 != gate["data_hashes"][parameter_path] or
            adapter.whitening_transform_sha256 != TRANSFORM_SHA256 or
            adapter.k != 48 or adapter.dimension != 96 or
            tuple(adapter.strata) != tuple(range(16))):
        raise ValueError("v6 adapter is not bound to vector/oracle/transform")
    oracle = load_transformed_oracle(REPO_ROOT / parameter_path)
    if (adapter.base_constant_weights_exact !=
            oracle["transform"]["base_weights"]):
        raise ArithmeticError("v6 adapter base weights differ from oracle")
    return True


def validate_weight_provenance(weights, oracle, gate):
    expected_path = REQUIRED_DATA_PATHS[2]
    if (weights["sha256"] != gate["data_hashes"][expected_path] or
            weights["prefix"] != "baseline_" or
            weights["j_scale_to_numerator"] != 1 or
            oracle["transform"]["sha256"] != TRANSFORM_SHA256):
        raise ValueError("v6 weights/transform provenance mismatch")
    with localcontext() as context:
        context.prec = 240

        def decimal_fraction(value):
            return Decimal(value.numerator) / Decimal(value.denominator)

        tolerance = Decimal("1e-110")
        if (abs(weights["denominator"] /
                decimal_fraction(oracle["I0"]) - 1) > tolerance or
                abs(weights["numerator"] /
                    decimal_fraction(oracle["B0"]) - 1) > tolerance or
                abs(weights["base_quotient"] /
                    decimal_fraction(oracle["base_quotient"]) - 1) >
                tolerance):
            raise ArithmeticError("v6 base normalizers differ from oracle")
        base = oracle["transform"]["base_weights"]
        for r in range(16):
            index = 6 * r
            exact_weight = base[index] ** 2 * oracle["E_I"][index][index]
            if abs(weights["i_weights"][r] /
                   decimal_fraction(exact_weight) - 1) > tolerance:
                raise ArithmeticError(
                    f"v6 transformed I stratum weight {r} mismatch")
        if (abs(sum(weights["i_weights"]) - 1) > Decimal("1e-180") or
                abs(sum(weights["j_weights"]) - 1) > Decimal("1e-180") or
                any(value <= 0 for value in
                    weights["i_weights"] + weights["j_weights"])):
            raise ArithmeticError("v6 normalized stratum weights invalid")
    return True


def analyze_records(records, oracle, weights, schedule, *, adapter=None,
                    do_jackknife=True):
    v5.validate_analytic_zero_se_proofs(oracle)
    chain_specs = schedule["chains"]
    if len(records) != len(chain_specs):
        raise ValueError("v6 result must contain exactly 128 chains")
    by_identity = {v5._record_identity(record): record for record in records}
    if len(by_identity) != len(records):
        raise ValueError("duplicate v6 chain identity")
    ordered = []
    for spec in chain_specs:
        identity = (spec["target"], spec["stratum"], spec["replicate"])
        if identity not in by_identity:
            raise ValueError("missing frozen v6 chain")
        record = by_identity[identity]
        v5.validate_chain_record(record, spec, schedule, adapter=adapter)
        ordered.append(record)
    records = ordered
    reconstruction = v5.reconstruct_matrices(
        records, oracle, weights, schedule)
    i_mask, j_mask = v5.structural_masks()
    exact_a = np.asarray([[float(x) for x in row] for row in oracle["E_I"]])
    exact_b = np.asarray([[float(x) for x in row] for row in oracle["E_J"]])
    if (np.any(reconstruction["A"][~(i_mask | i_mask.T)] != 0) or
            np.any(reconstruction["B"][~(j_mask | j_mask.T)] != 0)):
        raise ArithmeticError("v6 nonstructural matrix entry is nonzero")
    coverage_i = v5.simultaneous_coverage(
        reconstruction["A"], reconstruction["A_standard_error"], exact_a,
        i_mask, 6)
    coverage_j = v5.simultaneous_coverage(
        reconstruction["B"], reconstruction["B_standard_error"], exact_b,
        j_mask, 6)
    if coverage_i["checked_entries"] != 336 or \
            coverage_j["checked_entries"] != 876:
        raise AssertionError("v6 structural coverage counts changed")
    analytic_i_global = {(6 * r, 6 * r) for r in range(16)}
    bad_zero_se_i = v5.global_zero_se_failures(
        exact_a, reconstruction["A_standard_error"], i_mask,
        allowed=analytic_i_global)
    bad_zero_se_j = v5.global_zero_se_failures(
        exact_b, reconstruction["B_standard_error"], j_mask)
    base = np.asarray(oracle["transform"]["base_weights"], dtype=float)
    base_a = float(base @ reconstruction["A"] @ base)
    base_b = float(base @ reconstruction["B"] @ base)
    tolerance = 256 * np.finfo(float).eps
    base_pass = abs(base_a - 1) <= tolerance and abs(base_b - 1) <= tolerance
    acceptance = v5._acceptance_gates(records)
    roots = v5._exact_and_estimated_roots(reconstruction, oracle)
    jackknife = (v5._jackknife_roots(
        records, reconstruction, oracle, weights, schedule)
        if do_jackknife else {})
    hard_gates = {
        "all_128_chains_present": True,
        "structural_counts_336_876": True,
        "nonstructural_entries_exact_zero": True,
        "raw_antisymmetry_bitwise_zero": all(
            v5.parse_float_hex(record["raw_antisymmetry"]) == 0
            for record in records),
        "no_nontrivial_exact_nonzero_zero_se": (
            len(reconstruction["local_zero_se_failures"]) == 0 and
            len(bad_zero_se_i) == 0 and len(bad_zero_se_j) == 0),
        "constant_coordinate_sums_one": base_pass,
        "positive_acceptance_each_move_each_chain":
            acceptance["chain_move_positive"],
        "aggregate_acceptance_at_least_one_percent":
            acceptance["aggregate_move_rate_pass"],
        "active_counts_and_full_rank": all(
            roots[degree]["estimated"]["rank"] == expected
            for degree, expected in ((0, 16), (1, 47), (2, 93))),
        "roots_finite": all(math.isfinite(data["estimated"]["root"])
                            for data in roots.values()),
        "root_deletion_stability": (not do_jackknife or all(
            item["exact_in_interval"] and item["relative_discrepancy_pass"]
            for item in jackknife.values())),
    }
    statistical_gates = {
        "split_rhat": reconstruction["maximum_split_rhat"] <= 1.05,
        "batch_means_ess": reconstruction["minimum_batch_means_ess"] >= 200,
        "z_precision": reconstruction["all_z_precision_pass"],
        "simultaneous_coverage": coverage_i["pass"] and coverage_j["pass"],
    }
    max_standardized = max(
        coverage_i["max_standardized_discrepancy"],
        coverage_j["max_standardized_discrepancy"])
    failed_statistical = [key for key, value in statistical_gates.items()
                          if not value]
    extension_authorized = (
        all(hard_gates.values()) and bool(failed_statistical) and
        max_standardized <= 12 and set(failed_statistical) <= {
            "split_rhat", "batch_means_ess", "z_precision",
            "simultaneous_coverage"})
    return {
        "records": records,
        "reconstruction": reconstruction,
        "coverage_i": coverage_i,
        "coverage_j": coverage_j,
        "constant_sum_i": base_a,
        "constant_sum_j": base_b,
        "bad_local_zero_se": reconstruction["local_zero_se_failures"],
        "bad_zero_se_i": [list(map(int, row)) for row in bad_zero_se_i],
        "bad_zero_se_j": [list(map(int, row)) for row in bad_zero_se_j],
        "acceptance": acceptance,
        "roots": roots,
        "jackknife": jackknife,
        "hard_gates": hard_gates,
        "statistical_gates": statistical_gates,
        "maximum_standardized_oracle_discrepancy": max_standardized,
        "gates_passed": all(hard_gates.values()) and
                        all(statistical_gates.values()),
        "extension_authorized": extension_authorized,
        "transform_sha256": TRANSFORM_SHA256,
    }


def capture_analysis(records, oracle, weights, schedule, *, adapter):
    try:
        return analyze_records(records, oracle, weights, schedule,
                               adapter=adapter, do_jackknife=True), None
    except (ArithmeticError, ValueError, AssertionError) as error:
        return None, {"exception_type": type(error).__name__,
                      "message": str(error)}


def _i_outer_abs_bounds(adapter, stratum):
    offset = 6 * stratum
    transform = adapter.whitening_transform_exact
    feature_bounds = [sum(abs(float(transform[offset + i][offset + j]))
                          for i in range(6))
                      for j in range(6)]
    return [feature_bounds[i] * feature_bounds[j]
            for i, j in v5.upper_pairs(6)]


def _normalized_i_record_for_v5_validation(record, adapter):
    """Affine-map each bounded signed I outer entry into ``[0,1]``.

    This lets the already-hostile-tested v5 schema/Jensen/aggregate validator
    cover the transformed record without pretending the new signed features
    obey the old monomial bound.  The map and its second moment are exact
    algebraic consequences of ``z=(y+B)/(2B)``.
    """
    clone = copy.deepcopy(record)
    bounds = _i_outer_abs_bounds(adapter, record["stratum"])
    sample_count = record["sample_count"]
    for column, bound in enumerate(bounds):
        if not math.isfinite(bound) or bound < 0:
            raise ArithmeticError("v6 I pointwise bound is invalid")
        if bound == 0:
            fields = ("batch_upper_means", "batch_upper_second_means")
            if any(v5.parse_float_hex(row[column]) != 0
                   for field in fields for row in record[field]) or \
                    v5.parse_float_hex(record["raw_sum"][column]) != 0 or \
                    v5.parse_float_hex(record["raw_second_sum"][column]) != 0:
                raise ArithmeticError("inactive v6 I observable is nonzero")
            continue
        batch_means = [v5.parse_float_hex(row[column])
                       for row in record["batch_upper_means"]]
        batch_seconds = [v5.parse_float_hex(row[column])
                         for row in record["batch_upper_second_means"]]
        tolerance = 512 * np.finfo(float).eps * max(1.0, bound)
        if any(not -bound - tolerance <= value <= bound + tolerance
               for value in batch_means):
            raise ArithmeticError("v6 I batch mean exceeds exact feature bound")
        if any(not 0 <= value <= bound * bound +
               512 * np.finfo(float).eps * max(1.0, bound * bound)
               for value in batch_seconds):
            raise ArithmeticError("v6 I batch second exceeds exact bound")
        for row, mean in zip(clone["batch_upper_means"], batch_means):
            row[column] = v5.float_hex((mean + bound) / (2 * bound))
        for row, mean, second in zip(
                clone["batch_upper_second_means"],
                batch_means, batch_seconds):
            row[column] = v5.float_hex(
                (second + 2 * bound * mean + bound * bound) /
                (4 * bound * bound))
        raw_sum = v5.parse_float_hex(record["raw_sum"][column])
        raw_second = v5.parse_float_hex(record["raw_second_sum"][column])
        clone["raw_sum"][column] = v5.float_hex(
            (raw_sum + sample_count * bound) / (2 * bound))
        clone["raw_second_sum"][column] = v5.float_hex(
            (raw_second + 2 * bound * raw_sum +
             sample_count * bound * bound) / (4 * bound * bound))
    return clone


def _validate_original_i_moments(record, schedule, adapter):
    """Validate signed I moments before the compatibility affine map.

    The old v5 validator assumes every I outer observable lies in ``[0,1]``.
    Exact whitening makes observables signed and, in rare strata, very large.
    Merely affine-mapping them before applying the old checks is insufficient:
    adding a small inconsistency to a huge bound can round away in that map.
    These checks therefore bind the original serialized batches/raw sums and
    all Jensen and pointwise bounds at their natural per-coordinate scale.
    """
    if record.get("target") != "I":
        raise ValueError("signed I validator received a non-I record")
    if (isinstance(record.get("stratum"), bool) or
            not isinstance(record.get("stratum"), int) or
            record["stratum"] not in adapter.strata):
        raise ValueError("signed I record has invalid stratum")
    bounds = np.asarray(_i_outer_abs_bounds(adapter, record["stratum"]),
                        dtype=float)
    batch_count = schedule.get("batches_per_chain")
    samples_per_batch = schedule.get("samples_per_batch")
    if (isinstance(batch_count, bool) or not isinstance(batch_count, int) or
            isinstance(samples_per_batch, bool) or
            not isinstance(samples_per_batch, int) or
            batch_count <= 0 or samples_per_batch <= 0):
        raise ValueError("signed I validation schedule is invalid")
    width = len(bounds)
    means_raw = record.get("batch_upper_means")
    seconds_raw = record.get("batch_upper_second_means")
    raw_sum_raw = record.get("raw_sum")
    raw_second_raw = record.get("raw_second_sum")
    if (not isinstance(means_raw, list) or len(means_raw) != batch_count or
            not isinstance(seconds_raw, list) or
            len(seconds_raw) != batch_count or
            any(not isinstance(row, list) or len(row) != width
                for row in means_raw + seconds_raw) or
            not isinstance(raw_sum_raw, list) or len(raw_sum_raw) != width or
            not isinstance(raw_second_raw, list) or
            len(raw_second_raw) != width):
        raise ValueError("signed I moment arrays have invalid shape")
    means = np.asarray([
        [v5.parse_float_hex(value, "signed I batch mean") for value in row]
        for row in means_raw], dtype=float)
    seconds = np.asarray([
        [v5.parse_float_hex(value, "signed I batch second") for value in row]
        for row in seconds_raw], dtype=float)
    raw_sum = np.asarray([
        v5.parse_float_hex(value, "signed I raw sum")
        for value in raw_sum_raw], dtype=float)
    raw_second = np.asarray([
        v5.parse_float_hex(value, "signed I raw second")
        for value in raw_second_raw], dtype=float)
    if not (np.all(np.isfinite(bounds)) and np.all(bounds >= 0) and
            np.all(np.isfinite(means)) and np.all(np.isfinite(seconds)) and
            np.all(np.isfinite(raw_sum)) and np.all(np.isfinite(raw_second))):
        raise ArithmeticError("signed I moment or exact bound is nonfinite")
    epsilon = np.finfo(float).eps
    bound2 = bounds * bounds
    mean_tolerance = 1024 * epsilon * np.maximum(1.0, bounds)
    second_tolerance = 2048 * epsilon * np.maximum(1.0, bound2)
    if np.any(np.abs(means) > bounds + mean_tolerance):
        raise ArithmeticError("signed I batch mean exceeds pointwise bound")
    if np.any(seconds < 0) or np.any(
            seconds > bound2 + second_tolerance):
        raise ArithmeticError("signed I batch second exceeds pointwise bound")
    sample_count = batch_count * samples_per_batch
    raw_mean = raw_sum / sample_count
    raw_second_mean = raw_second / sample_count
    batch_mean = np.mean(means, axis=0)
    batch_second_mean = np.mean(seconds, axis=0)
    if np.any(np.abs(raw_mean - batch_mean) > mean_tolerance +
              1024 * epsilon * np.maximum(
                  np.abs(raw_mean), np.abs(batch_mean))):
        raise ArithmeticError("signed I raw sums disagree with batches")
    if np.any(np.abs(raw_second_mean - batch_second_mean) >
              second_tolerance + 2048 * epsilon * np.maximum(
                  np.abs(raw_second_mean), np.abs(batch_second_mean))):
        raise ArithmeticError("signed I raw second sums disagree with batches")
    jensen_tolerance = 4096 * epsilon * np.maximum.reduce((
        np.ones_like(bound2), bound2, np.abs(raw_second_mean),
        raw_mean * raw_mean))
    if np.any(raw_second_mean < raw_mean * raw_mean - jensen_tolerance) or \
            np.any(raw_second_mean <
                   np.mean(means * means, axis=0) - jensen_tolerance):
        raise ArithmeticError("signed I raw moments violate Jensen")
    batch_jensen_tolerance = 4096 * epsilon * np.maximum(
        1.0, np.maximum(bound2[None, :],
                        np.maximum(seconds, means * means)))
    if np.any(seconds < means * means - batch_jensen_tolerance):
        raise ArithmeticError("signed I batch moments violate Jensen")
    inactive = bounds == 0
    if (np.any(means[:, inactive] != 0) or
            np.any(seconds[:, inactive] != 0) or
            np.any(raw_sum[inactive] != 0) or
            np.any(raw_second[inactive] != 0)):
        raise ArithmeticError("inactive signed I observable is nonzero")
    return True


def validate_chain_record(record, chain_spec, schedule, *, adapter=None):
    if record.get("target") != "I":
        return V5_VALIDATE_CHAIN_RECORD(
            record, chain_spec, schedule, adapter=adapter)
    if adapter is None:
        raise ValueError("v6 I record validation requires transformed adapter")
    _validate_original_i_moments(record, schedule, adapter)
    normalized = _normalized_i_record_for_v5_validation(record, adapter)
    return V5_VALIDATE_CHAIN_RECORD(
        normalized, chain_spec, schedule, adapter=adapter)


def _patch_v5_runtime():
    v5.REQUIRED_SOURCE_PATHS = REQUIRED_SOURCE_PATHS
    v5.REQUIRED_DATA_PATHS = REQUIRED_DATA_PATHS
    v5.C10ImportanceDensity = WhitenedC10ImportanceDensity
    v5.load_exact_expectation_oracle = load_transformed_oracle
    v5.j_envelope_point = j_envelope_point
    v5.bounded_outer_entry = bounded_outer_entry
    v5.expected_conventions = expected_conventions
    v5.analyze_records = analyze_records
    v5.validate_chain_record = validate_chain_record
    importance_conditional.j_envelope_log_density = j_envelope_log_density


def load_parent_result(path, gate_sha256, driver_sha256, schedule):
    snapshot = v5.read_file_snapshot(path)
    raw = v5.strict_json_bytes(snapshot["data"], "v6 parent result")
    v5._exact_keys(raw, {
        "status", "rigorous", "theorem_ready", "mode", "gate_path",
        "gate_sha256", "driver_sha256", "authorization_sha256",
        "parent_result_sha256", "gate_binding", "authorization_binding",
        "parent_result_binding", "float_encoding", "conventions", "schedule",
        "wall_seconds", "peak_rss_kib", "records", "record_checkpoints",
        "analysis", "analysis_failure", "fresh_exact_reconstruction_required"},
        "v6 parent result")
    v5.validate_public_binding(raw["gate_binding"],
                               expected_sha256=gate_sha256)
    v5.validate_public_binding(raw["authorization_binding"],
                               expected_sha256=raw["authorization_sha256"])
    if (raw["status"] != "d4-exact-whitened-calibration-rejected" or
            raw["rigorous"] is not False or raw["theorem_ready"] is not False or
            raw["mode"] != "production" or raw["gate_sha256"] != gate_sha256 or
            raw["driver_sha256"] != driver_sha256 or
            raw["parent_result_sha256"] is not None or
            raw["parent_result_binding"] is not None or
            raw["float_encoding"] != v5.FLOAT_ENCODING or
            raw["conventions"] != expected_conventions() or
            raw["schedule"] != schedule or raw["analysis"] is None or
            raw["analysis_failure"] is not None or
            not raw["analysis"].get("extension_authorized") or
            raw["fresh_exact_reconstruction_required"] is not True or
            len(raw["records"]) != 128 or
            len(raw["record_checkpoints"]) != 128):
        raise ValueError("v6 parent is not an extendible rejected run")
    v5.validate_run_metrics(raw["wall_seconds"], raw["peak_rss_kib"])
    return {"raw": raw, **v5.public_binding(snapshot)}


def _main(open_directories):
    _patch_v5_runtime()
    started = time.perf_counter()
    parser = argparse.ArgumentParser()
    parser.add_argument("--gate", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--mode", choices=(
        "preflight", "smoke", "production", "extension"),
                        default="preflight")
    parser.add_argument("--authorization")
    parser.add_argument("--record-dir")
    parser.add_argument("--extension-record-dir")
    parser.add_argument("--parent-result")
    parser.add_argument("--progress", action="store_true")
    args = parser.parse_args()
    bound = load_and_validate_gate(args.gate)
    gate = bound["gate"]
    driver_sha = gate["source_hashes"][DRIVER_RELATIVE]
    authorization = None
    authorization_digest = None
    parent_digest = None
    record_directory = None
    initial_directory = None
    extension_directory = None
    if args.mode == "production":
        if not args.authorization or not args.record_dir:
            raise SystemExit("v6 production requires authorization/record-dir")
        authorization = v5.validate_authorization(
            args.authorization, bound["sha256"], driver_sha, args.record_dir)
        authorization_digest = authorization["sha256"]
        record_directory = v5.open_bound_directory(
            authorization["raw"]["record_directory_binding"])
        open_directories.append(record_directory)
        v5.validate_fresh_checkpoint_directory(
            record_directory, gate["schedule"]["chains"])
        if args.extension_record_dir or args.parent_result:
            raise SystemExit("v6 production rejects extension arguments")
    elif args.mode == "extension":
        if not (args.authorization and args.record_dir and
                args.extension_record_dir and args.parent_result):
            raise SystemExit("v6 extension requires all parent/directory inputs")
    elif (args.authorization or args.record_dir or
          args.extension_record_dir or args.parent_result):
        raise SystemExit("v6 run-only arguments require production/extension")
    oracle_path = REPO_ROOT / REQUIRED_DATA_PATHS[0]
    vector_path = REPO_ROOT / REQUIRED_DATA_PATHS[1]
    weights_path = REPO_ROOT / REQUIRED_DATA_PATHS[2]
    oracle = load_transformed_oracle(oracle_path)
    v5.validate_analytic_zero_se_proofs(oracle)
    adapter = WhitenedC10ImportanceDensity(vector_path, oracle_path)
    validate_adapter_provenance(adapter, gate)
    weights = v5.load_stratum_weights(
        weights_path, gate["data_hashes"][REQUIRED_DATA_PATHS[2]],
        prefix="baseline_", j_scale_to_numerator=1)
    validate_weight_provenance(weights, oracle, gate)
    if args.mode == "preflight":
        records, checkpoints, analysis, failure = [], [], None, None
        extras = {bound["path"]: v5.inode_binding(bound)}
        status = "d4-exact-whitened-calibration-preflight-only"
    elif args.mode == "smoke":
        records = v5.run_smoke(adapter)
        checkpoints, analysis, failure = [], None, None
        extras = {bound["path"]: v5.inode_binding(bound)}
        status = "d4-exact-whitened-calibration-tiny-smoke-only"
    elif args.mode == "production":
        loaded = [v5.run_fresh_initial_chain(
            adapter, spec, gate["schedule"], record_directory,
            bound["sha256"], driver_sha, authorization, bound,
            progress=args.progress) for spec in gate["schedule"]["chains"]]
        records = [item["record"] for item in loaded]
        checkpoints = [v5.public_binding(item) for item in loaded]
        analysis, failure = capture_analysis(
            records, oracle, weights, gate["schedule"], adapter=adapter)
        status = ("d4-exact-whitened-calibration-pass"
                  if analysis is not None and analysis["gates_passed"] else
                  "d4-exact-whitened-calibration-rejected")
        extras = {
            bound["path"]: v5.inode_binding(bound),
            authorization["path"]: v5.inode_binding(authorization),
            record_directory["path"]:
                v5.directory_inode_binding(record_directory),
            **{item["path"]: v5.inode_binding(item) for item in loaded},
        }
    else:
        parent = load_parent_result(
            args.parent_result, bound["sha256"], driver_sha, gate["schedule"])
        authorization = v5.validate_extension_authorization(
            args.authorization, bound["sha256"], driver_sha,
            parent["sha256"], args.extension_record_dir)
        authorization_digest = authorization["sha256"]
        parent_digest = parent["sha256"]
        extension_directory = v5.open_bound_directory(
            authorization["raw"]["extension_record_directory_binding"])
        open_directories.append(extension_directory)
        v5.validate_fresh_checkpoint_directory(
            extension_directory, gate["schedule"]["chains"], extension=True)
        _, initial_directory = v5.validate_parent_checkpoint_manifest(
            parent, args.record_dir, gate["schedule"])
        open_directories.append(initial_directory)
        initial = [v5.load_chain_checkpoint(
            v5.chain_checkpoint_path(initial_directory["path"], spec), spec,
            bound["sha256"], driver_sha,
            parent["raw"]["authorization_sha256"], gate["schedule"],
            adapter=adapter, directory_handle=initial_directory)
                   for spec in gate["schedule"]["chains"]]
        if ([item["record"] for item in initial] != parent["raw"]["records"] or
                [v5.public_binding(item) for item in initial] !=
                parent["raw"]["record_checkpoints"]):
            raise ValueError("v6 parent records/checkpoints changed")
        initial_analysis = analyze_records(
            [item["record"] for item in initial], oracle, weights,
            gate["schedule"], adapter=adapter, do_jackknife=True)
        if not initial_analysis["extension_authorized"]:
            raise ValueError("v6 parent reconstruction forbids extension")
        loaded = [v5.run_fresh_extended_chain(
            adapter, item, spec, gate["schedule"], extension_directory,
            bound["sha256"], driver_sha, authorization, parent, bound,
            progress=args.progress) for item, spec in zip(
                initial, gate["schedule"]["chains"])]
        records = [item["record"] for item in loaded]
        checkpoints = [v5.public_binding(item) for item in loaded]
        analysis, failure = capture_analysis(
            records, oracle, weights, v5.extended_schedule(gate["schedule"]),
            adapter=adapter)
        status = ("d4-exact-whitened-calibration-extension-pass"
                  if analysis is not None and analysis["gates_passed"] else
                  "d4-exact-whitened-calibration-extension-rejected")
        extras = {
            bound["path"]: v5.inode_binding(bound),
            authorization["path"]: v5.inode_binding(authorization),
            parent["path"]: v5.inode_binding(parent),
            initial_directory["path"]:
                v5.directory_inode_binding(initial_directory),
            extension_directory["path"]:
                v5.directory_inode_binding(extension_directory),
            **{item["path"]: v5.inode_binding(item) for item in initial},
            **{item["path"]: v5.inode_binding(item) for item in loaded},
        }
    wall = time.perf_counter() - started
    peak = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    v5.validate_run_metrics(v5.float_hex(wall), peak)
    payload = {
        "status": status, "rigorous": False, "theorem_ready": False,
        "mode": args.mode, "gate_path": str(Path(args.gate)),
        "gate_sha256": bound["sha256"], "driver_sha256": driver_sha,
        "authorization_sha256": authorization_digest,
        "parent_result_sha256": parent_digest,
        "gate_binding": v5.public_binding(bound),
        "authorization_binding": (None if authorization is None else
                                  v5.public_binding(authorization)),
        "parent_result_binding": (None if args.mode != "extension" else
                                  v5.public_binding(parent)),
        "wall_seconds": v5.float_hex(wall), "peak_rss_kib": peak,
        "float_encoding": v5.FLOAT_ENCODING,
        "conventions": gate["conventions"],
        "schedule": (v5.tiny_smoke_schedule() if args.mode == "smoke" else
                     v5.extended_schedule(gate["schedule"])
                     if args.mode == "extension" else gate["schedule"]),
        "records": records, "record_checkpoints": checkpoints,
        "analysis": analysis, "analysis_failure": failure,
        "fresh_exact_reconstruction_required": True,
    }
    digest = v5.write_new_result(
        args.output, payload, gate, extra_hashes=extras)
    print(json.dumps({"status": status, "output_sha256": digest,
                      "record_count": len(records)}, sort_keys=True))
    if args.mode in ("production", "extension") and (
            analysis is None or not analysis["gates_passed"]):
        raise SystemExit("v6 D4 calibration failed frozen gates")


def main():
    directories = []
    try:
        return _main(directories)
    finally:
        for directory in reversed(directories):
            v5.close_bound_directory(directory)


if __name__ == "__main__":
    main()
