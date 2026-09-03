#!/usr/bin/env python3
"""Independent audit of the completed, rejected v6.7 records-only recovery.

This checker reopens the byte-pinned v6.6 inputs and all 128 checkpoints,
recomputes the complete v6.7 analysis, and requires byte-for-byte JSON-value
equality with the recovered analysis.  Root and quotient values participate in
that equality check but are deliberately never printed or copied into this
audit artifact.  The emitted diagnostics are limited to the frozen rejection
gates and non-root convergence/coverage summaries.
"""

from __future__ import annotations

import argparse
from fractions import Fraction
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import sys
from unittest import mock


FILE = Path(__file__).resolve()
REPO = FILE.parents[2]
SOURCE = REPO / "agents/structural-basis/code/importance_d4_calibration_v67_recover.py"
BUILDER = REPO / "agents/structural-basis/code/build_importance_d4_calibration_v67_recovery_authorization.py"
TESTS = REPO / "agents/structural-basis/tests/test_importance_d4_calibration_v67_recover.py"
SPEC = REPO / "agents/structural-basis/IMPORTANCE-D4-CALIBRATION-V67-RECOVERY.md"
AUTHORIZATION = REPO / "agents/structural-basis/results/importance_d4_calibration_v67_recovery_authorization.json"
RECOVERED = REPO / "agents/structural-basis/results/importance_d4_calibration_v67_recovered_from_v66.json"
V66_SOURCE = REPO / "agents/structural-basis/code/importance_d4_calibration_v66.py"
V66_GATE = REPO / "agents/structural-basis/results/importance_d4_calibration_gate_v66.json"
V66_AUTHORIZATION = REPO / "agents/structural-basis/results/importance_d4_calibration_v66_authorization.json"
V66_REJECTION = REPO / "agents/structural-basis/results/importance_d4_calibration_v66_production.json"

PINS = {
    SOURCE: "118b56e6e7fe07c3a95ed1f49da6cbaf1c0352f5f9776526ea8bb5aa0d4782f8",
    BUILDER: "31a54a963812d0da4e1ac2bbface6f145ec55fa6d0ba23752ed8ae0858680715",
    TESTS: "529a85d02902311eab5262a8809d425d43606cd6cab0bd7ac9cccf17ac019463",
    SPEC: "b4ca66588bbc0a0361530bce73c9035f3a345c3c49d5abb9c8c56108cfafd726",
    AUTHORIZATION: "1656f18c9ce0601b08616ee072511cfc2caf89b3513f10115a3e3bf0c63a7bae",
    RECOVERED: "3ff38ac49371100c66777f321d993f00b8ba9ef673c42c1f41cb1c7b8ebf79b0",
    V66_SOURCE: "69698f7766d9077bd5026dee8fc1e065b762a1f3d344ea2b7af0282763ce21f9",
    V66_GATE: "fa1019605ef6b5efd486b234451806efcf1912f7b3f181c9511839d873b63bf6",
    V66_AUTHORIZATION: "25c516af4cefacf08405632f38797f2e43d46a7275d1e07ee3f4202a192489c2",
    V66_REJECTION: "a4f8518b52de5fb9c79e58c770d0c861c7e283481d745c31b6a8a3802761d879",
}

TOP_LEVEL_KEYS = {
    "analysis", "analysis_failure", "conventions", "float_encoding",
    "fresh_exact_reconstruction_required", "mode",
    "numpy_bool_paths_converted", "peak_rss_kib", "record_checkpoints",
    "record_directory_binding", "records", "recovery_authorization_binding",
    "recovery_driver_sha256", "rigorous", "schedule", "status",
    "theorem_ready", "v66_authorization_binding", "v66_gate_binding",
    "v66_rejected_output_binding", "wall_seconds",
}


class AuditFailure(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AuditFailure(message)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def float_hex(value: float) -> str:
    value = float(value)
    require(math.isfinite(value), "nonfinite rejection diagnostic")
    return value.hex()


def decoded_float(value, name: str) -> float:
    require(isinstance(value, dict) and set(value) == {"float_hex"} and
            isinstance(value["float_hex"], str),
            f"malformed serialized float: {name}")
    result = float.fromhex(value["float_hex"])
    require(math.isfinite(result), f"nonfinite serialized float: {name}")
    return result


def load_recovery():
    spec = importlib.util.spec_from_file_location(
        "independent_v67_completed_recovery", SOURCE)
    require(spec is not None and spec.loader is not None,
            "cannot load frozen v6.7 recovery source")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    require(Path(module.__file__).resolve() == SOURCE.resolve(),
            "wrong recovery module imported")
    return module


def expected_thresholds() -> dict[str, str]:
    return {
        "extension_max_standardized_discrepancy": "12",
        "maximum_split_rhat": "1.05",
        "maximum_z_relative_se": "1/50",
        "minimum_aggregate_acceptance_by_move": "1/100",
        "minimum_batch_means_ess": "200",
        "minimum_move_acceptance_per_chain": "positive",
        "minimum_z_six_se_lower": "0",
        "relative_rank_tolerance": "1/1000000000000",
        "root_jackknife_multiplier": "6",
        "root_relative_discrepancy": "1/200",
        "simultaneous_multiplier": "6",
    }


def summarize_serialized_rejection(serialized: dict, thresholds: dict) -> dict:
    """Fail-closed consistency check using no root/quotient values."""
    require(thresholds == expected_thresholds(), "frozen thresholds changed")
    hard = serialized.get("hard_gates")
    statistical = serialized.get("statistical_gates")
    require(isinstance(hard, dict) and isinstance(statistical, dict),
            "missing recovered gate tables")
    failed_hard = sorted(key for key, passed in hard.items()
                         if passed is not True)
    failed_statistical = sorted(key for key, passed in statistical.items()
                                if passed is not True)
    require(failed_hard == ["root_deletion_stability"],
            "completed hard-gate rejection surface changed")
    require(failed_statistical == [
        "batch_means_ess", "simultaneous_coverage", "split_rhat",
        "z_precision"], "completed statistical rejection surface changed")
    require(serialized.get("gates_passed") is False and
            serialized.get("extension_authorized") is False,
            "rejected analysis advertises passage or extension")

    jackknife = serialized.get("jackknife")
    require(isinstance(jackknife, dict) and set(jackknife) == {"0", "1", "2"},
            "jackknife degree inventory changed")
    jackknife_flags = {}
    relative = {}
    for degree in ("0", "1", "2"):
        row = jackknife[degree]
        flags = {
            "exact_in_interval": row.get("exact_in_interval"),
            "relative_discrepancy_pass": row.get(
                "relative_discrepancy_pass"),
        }
        require(all(type(value) is bool for value in flags.values()),
                f"malformed jackknife flags at degree {degree}")
        jackknife_flags[degree] = flags
        relative[degree] = decoded_float(
            row.get("relative_discrepancy"),
            f"jackknife[{degree}].relative_discrepancy")
    require(jackknife_flags == {
        "0": {"exact_in_interval": True,
              "relative_discrepancy_pass": True},
        "1": {"exact_in_interval": True,
              "relative_discrepancy_pass": False},
        "2": {"exact_in_interval": True,
              "relative_discrepancy_pass": False},
    }, "jackknife rejection flags changed")
    relative_limit = float(Fraction(thresholds["root_relative_discrepancy"]))
    require(relative["0"] <= relative_limit and
            relative["1"] > relative_limit and
            relative["2"] > relative_limit,
            "jackknife discrepancy comparisons do not explain hard failure")

    reconstruction = serialized.get("reconstruction")
    require(isinstance(reconstruction, dict), "missing reconstruction")
    maximum_rhat = decoded_float(
        reconstruction.get("maximum_split_rhat"), "maximum_split_rhat")
    minimum_ess = decoded_float(
        reconstruction.get("minimum_batch_means_ess"),
        "minimum_batch_means_ess")
    require(maximum_rhat > float(thresholds["maximum_split_rhat"]),
            "split-R-hat failure not reproduced")
    require(minimum_ess < float(thresholds["minimum_batch_means_ess"]),
            "batch-means ESS failure not reproduced")
    require(reconstruction.get("all_z_precision_pass") is False,
            "z-precision failure not reproduced")
    conditional = reconstruction.get("conditional")
    require(isinstance(conditional, list), "conditional diagnostics missing")
    failed_z = [row for row in conditional
                if row.get("target") == "J" and
                isinstance(row.get("z"), dict) and
                row["z"].get("pass") is False]
    require(len(failed_z) == 16,
            "expected every one of 16 J z-precision groups to fail")

    coverage_i = serialized.get("coverage_i")
    coverage_j = serialized.get("coverage_j")
    require(isinstance(coverage_i, dict) and isinstance(coverage_j, dict),
            "coverage diagnostics missing")
    require(coverage_i.get("pass") is False and
            coverage_i.get("checked_entries") == 336 and
            coverage_j.get("pass") is False and
            coverage_j.get("checked_entries") == 876,
            "simultaneous-coverage failure/counts changed")
    standardized_i = decoded_float(
        coverage_i.get("max_standardized_discrepancy"),
        "coverage_i.max_standardized_discrepancy")
    standardized_j = decoded_float(
        coverage_j.get("max_standardized_discrepancy"),
        "coverage_j.max_standardized_discrepancy")
    maximum_standardized = decoded_float(
        serialized.get("maximum_standardized_oracle_discrepancy"),
        "maximum_standardized_oracle_discrepancy")
    require(maximum_standardized == max(standardized_i, standardized_j) and
            maximum_standardized > float(
                thresholds["extension_max_standardized_discrepancy"]),
            "extension discrepancy rejection not reproduced")

    return {
        "only_failed_hard_gate": failed_hard[0],
        "first_failed_jackknife_degree": 1,
        "jackknife_flags": jackknife_flags,
        "jackknife_relative_discrepancy_hex": {
            degree: float_hex(relative[degree]) for degree in ("0", "1", "2")
        },
        "root_relative_discrepancy_limit": thresholds[
            "root_relative_discrepancy"],
        "failed_statistical_gates": failed_statistical,
        "maximum_split_rhat_hex": float_hex(maximum_rhat),
        "maximum_split_rhat_limit": thresholds["maximum_split_rhat"],
        "minimum_batch_means_ess_hex": float_hex(minimum_ess),
        "minimum_batch_means_ess_limit": thresholds[
            "minimum_batch_means_ess"],
        "failed_j_z_precision_groups": len(failed_z),
        "j_z_precision_group_count": 16,
        "coverage_i_checked": 336,
        "coverage_i_max_standardized_hex": float_hex(standardized_i),
        "coverage_j_checked": 876,
        "coverage_j_max_standardized_hex": float_hex(standardized_j),
        "maximum_standardized_hex": float_hex(maximum_standardized),
        "extension_max_standardized_limit": thresholds[
            "extension_max_standardized_discrepancy"],
    }


def build() -> dict:
    for path, expected in PINS.items():
        require(sha(path) == expected, f"frozen input changed: {path}")
    recovery = load_recovery()
    output_snapshot = recovery.V5.read_file_snapshot(RECOVERED)
    require(output_snapshot["sha256"] == PINS[RECOVERED],
            "recovered output snapshot changed")
    raw = recovery.V5.strict_json_bytes(
        output_snapshot["data"], "v6.7 recovered output")
    recovery.V5._exact_keys(raw, TOP_LEVEL_KEYS, "v6.7 recovered output")

    recovery_authorization = recovery.preflight_recovery_authorization(
        AUTHORIZATION, RECOVERED, PINS[SOURCE])
    require(recovery_authorization["sha256"] == PINS[AUTHORIZATION],
            "wrong v6.7 recovery authorization parsed")

    forbidden = lambda *args, **kwargs: (_ for _ in ()).throw(
        AssertionError("chain execution/publication forbidden in completed audit"))
    patches = [mock.patch.object(recovery, "publish_recovery", forbidden)]
    for module in (recovery.V5, recovery.V6):
        for name in ("run_one_chain", "extend_one_chain",
                     "run_fresh_initial_chain", "run_fresh_extended_chain",
                     "run_smoke"):
            if hasattr(module, name):
                patches.append(mock.patch.object(module, name, forbidden))
    for patch in patches:
        patch.start()

    context = recovery.open_completed_v66_inputs()
    try:
        loaded, oracle, adapter, weights = recovery.load_completed_checkpoints(
            context)
        require(len(loaded) == 128 and recovery.validate_record_leaf_set(context),
                "completed checkpoint set changed")
        recovery.complete_recovery_authorization(
            recovery_authorization, context, loaded, RECOVERED)

        require(raw["status"] ==
                "d4-exact-whitened-calibration-v67-recovery-rejected" and
                raw["rigorous"] is False and raw["theorem_ready"] is False and
                raw["mode"] == "records-only-no-chain-execution" and
                raw["fresh_exact_reconstruction_required"] is True,
                "recovered output scope/status changed")
        require(raw["recovery_driver_sha256"] == PINS[SOURCE] and
                raw["recovery_authorization_binding"] ==
                recovery.V5.public_binding(recovery_authorization) and
                raw["v66_gate_binding"] ==
                recovery.V5.public_binding(context["bound"]) and
                raw["v66_authorization_binding"] ==
                recovery.V5.public_binding(context["authorization"]) and
                raw["v66_rejected_output_binding"] ==
                recovery.V5.public_binding(context["rejected"]),
                "recovered trust-root bindings changed")
        require(raw["record_directory_binding"] == {
                    "path": context["directory"]["path"],
                    "device": context["directory"]["device"],
                    "inode": context["directory"]["inode"],
                }, "recovered record-directory binding changed")
        require(raw["record_checkpoints"] == [
                    recovery.V5.public_binding(item) for item in loaded] and
                raw["records"] == recovery.json_safe_v67(
                    [item["record"] for item in loaded]),
                "recovered checkpoint/record serialization changed")
        require(raw["schedule"] == context["gate"]["schedule"] and
                raw["conventions"] == context["gate"]["conventions"] and
                raw["float_encoding"] == recovery.V5.FLOAT_ENCODING,
                "recovered schedule/conventions changed")
        recovery.V5.validate_run_metrics(
            raw["wall_seconds"], raw["peak_rss_kib"])
        require(raw["analysis_failure"] is None and
                raw["numpy_bool_paths_converted"] == list(
                    recovery.EXPECTED_NUMPY_BOOL_PATHS),
                "recovery analysis/serializer status changed")

        # Full independent replay.  Equality deliberately covers every
        # unreported root/matrix field without exposing those values here.
        analysis, failure = recovery.analyze_completed_records(
            loaded, oracle, adapter, weights, context["gate"]["schedule"])
        require(failure is None and analysis is not None,
                f"fresh full analysis failed: {failure!r}")
        require(tuple(recovery.numpy_bool_paths(analysis)) ==
                recovery.EXPECTED_NUMPY_BOOL_PATHS,
                "fresh NumPy Boolean surface changed")
        require(recovery.json_safe_v67(analysis) == raw["analysis"],
                "serialized analysis differs from fresh reconstruction")

        summary = summarize_serialized_rejection(
            raw["analysis"], context["gate"]["thresholds"])
        # Repeat every declared gate independently from the raw fresh
        # analysis, rather than accepting its Boolean tables as an oracle.
        hard = analysis["hard_gates"]
        statistical = analysis["statistical_gates"]
        expected_statistical = {
            "split_rhat":
                analysis["reconstruction"]["maximum_split_rhat"] <= 1.05,
            "batch_means_ess":
                analysis["reconstruction"]["minimum_batch_means_ess"] >= 200,
            "z_precision":
                analysis["reconstruction"]["all_z_precision_pass"],
            "simultaneous_coverage":
                analysis["coverage_i"]["pass"] and
                analysis["coverage_j"]["pass"],
        }
        require(statistical == expected_statistical and
                analysis["gates_passed"] ==
                (all(hard.values()) and all(expected_statistical.values())),
                "fresh gate Boolean contraction is inconsistent")
        failed_statistical = {
            key for key, passed in expected_statistical.items() if not passed}
        independently_extension_eligible = (
            all(hard.values()) and bool(failed_statistical) and
            analysis["maximum_standardized_oracle_discrepancy"] <= 12 and
            failed_statistical <= {
                "split_rhat", "batch_means_ess", "z_precision",
                "simultaneous_coverage"})
        require(analysis["extension_authorized"] ==
                independently_extension_eligible is False,
                "extension authorization contraction is inconsistent")
    finally:
        recovery.V5.close_bound_directory(context["directory"])
        for patch in reversed(patches):
            patch.stop()

    for path, expected in PINS.items():
        require(sha(path) == expected,
                f"frozen input moved during audit: {path}")
    return {
        "status": "AUDIT PASS OF REJECTED OUTPUT",
        "scope": "completed v6.7 records-only recovery; no root/quotient disclosed",
        "checker_sha256": sha(FILE),
        "pinned": {str(path.relative_to(REPO)): digest
                   for path, digest in PINS.items()},
        "checks": {
            "record_count": 128,
            "all_checkpoint_hashes_inodes_and_leaf_set_revalidated": True,
            "v66_gate_authorization_and_rejection_sentinel_revalidated": True,
            "v67_authorization_and_source_closure_revalidated": True,
            "chain_execution_and_publication_trapped": True,
            "complete_analysis_recomputed": True,
            "complete_serialized_analysis_exactly_equal": True,
            "unreported_matrix_and_root_fields_covered_by_equality": True,
            "numeric_root_or_quotient_emitted": False,
        },
        "rejection": summary,
        "decision": {
            "recovered_output_accepted_as_authentic_rejection": True,
            "any_matrix_or_candidate_admissible_even_heuristically": False,
            "extension_authorized": False,
            "reason": (
                "the sole failed hard gate is deletion stability (degrees 1 "
                "and 2 exceed the 1/200 relative-discrepancy limit); all four "
                "statistical gates also fail, and the standardized discrepancy "
                "exceeds the extension ceiling"),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    payload = (json.dumps(build(), sort_keys=True, separators=(",", ":"),
                          allow_nan=False) + "\n").encode("ascii")
    if args.output is not None:
        target = args.output.resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                             0o644)
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    print(payload.decode("ascii"), end="")


if __name__ == "__main__":
    main()
