#!/usr/bin/env python3
"""Fail-closed completed-output auditor for the frozen D4 v5 -O replication.

The caller must supply the SHA-256 of the *completed* result.  Without that
external completion token this program will not open the production result or
record directory.  The audit remains discovery-only and proves no sieve bound.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import sys
from pathlib import Path


HERE = Path(__file__).resolve()
REPO_ROOT = HERE.parents[3]
DRIVER = REPO_ROOT / \
    "agents/structural-basis/code/importance_d4_calibration.py"
GATE = REPO_ROOT / \
    "agents/structural-basis/results/importance_d4_calibration_gate_v5.json"
AUTHORIZATION = REPO_ROOT / \
    "agents/structural-basis/results/importance_d4_calibration_v5_authorization_opt.json"
PRODUCTION_RESULT = REPO_ROOT / \
    "agents/structural-basis/results/importance_d4_calibration_v5_production_opt.json"
RECORD_DIRECTORY = REPO_ROOT / \
    "agents/structural-basis/results/importance_d4_calibration_v5_records_opt"
DECISION_TABLE = REPO_ROOT / \
    "agents/structural-basis/results/importance_d4_calibration_v5_decision_table.json"

DRIVER_SHA256 = \
    "b0b4350ff1804530724c87b8693aa4dd0059904f3eb9d72696497fb3c90c1b41"
GATE_SHA256 = \
    "860a9a51284187388e2384b7ca19615dc7d17eb523a7a4fa4d5617e2e6f29196"
AUTHORIZATION_SHA256 = \
    "26f8da920c032d9fdf1f0000a65cec26894f07a47d17ba675b1f2ca2f6e117c9"
DECISION_TABLE_SHA256 = \
    "3660ae47168ccbadb8cfa2cb2152deecf64321f9cd78ba2df1d4a0f8a68c29b4"
SUPERSEDES_INVALID_AUDITOR_SHA256 = \
    "d67005ba95fc1a0435bbe8122d612393c8939b3ea6ea761416224954894227bd"
NUMPY_VERSION = "2.2.4"
NUMPY_INIT_SHA256 = \
    "6ae17b070c0f70a8e3cad89a510a256942e5a1f37ea5feb120cec167ed2a6236"

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

DECISION_EXIT_CODES = {
    "CALIBRATION_PASS": 0,
    "EXTENSION_ELIGIBLE": 2,
    "CALIBRATION_RETIRED": 3,
    "IMPLEMENTATION_REJECTED": 1,
}


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def sha256_file(path):
    return sha256_bytes(Path(path).read_bytes())


def _reject_json_float(_token):
    raise ValueError("JSON floats are forbidden")


def _reject_json_constant(_token):
    raise ValueError("nonfinite JSON token")


def strict_json_bytes(data, name):
    if not isinstance(data, bytes) or len(data) > 256_000_000:
        raise ValueError(f"{name} is not bounded bytes")

    def pairs_hook(pairs):
        answer = {}
        for key, value in pairs:
            if not isinstance(key, str) or key in answer:
                raise ValueError(f"{name} has a duplicate/non-string key")
            answer[key] = value
        return answer

    return json.loads(
        data.decode("utf-8"), object_pairs_hook=pairs_hook,
        parse_float=_reject_json_float, parse_constant=_reject_json_constant)


def require_sha256(value, name):
    if (not isinstance(value, str) or len(value) != 64 or
            any(character not in "0123456789abcdef" for character in value)):
        raise ValueError(f"{name} is not canonical lowercase SHA-256")
    return value


def validate_expected_auditor_sha256(expected):
    expected = require_sha256(expected, "expected auditor SHA-256")
    if sha256_file(HERE) != expected:
        raise ValueError("running auditor bytes differ from external trust root")
    return expected


def require_auditor_unchanged(expected):
    if sha256_file(HERE) != expected:
        raise ValueError("auditor changed after its initial trust check")
    return True


def validate_audit_output_path(path):
    """Canonicalize a fresh audit leaf without entering trusted inputs."""
    path = Path(path)
    if not path.name or Path(path.name).name != path.name:
        raise ValueError("audit output is not one safe leaf")
    parent = path.parent.resolve()
    if not parent.is_dir():
        raise ValueError("audit output parent must already exist")
    candidate = parent / path.name
    record_directory = RECORD_DIRECTORY.resolve()
    try:
        candidate.relative_to(record_directory)
    except ValueError:
        pass
    else:
        raise ValueError("audit output may not be inside record directory")
    trusted_files = {
        DRIVER.resolve(), GATE.resolve(), AUTHORIZATION.resolve(),
        PRODUCTION_RESULT.resolve(), DECISION_TABLE.resolve(), HERE.resolve(),
    }
    if candidate in trusted_files:
        raise ValueError("audit output aliases a trusted input")
    if os.path.lexists(candidate):
        raise FileExistsError("audit output must be a fresh path")
    return candidate


def _exact_keys(value, keys, name):
    if not isinstance(value, dict) or set(value) != set(keys):
        raise ValueError(f"{name} has an unexpected schema")


def load_gate_manifest_without_imports():
    data = GATE.read_bytes()
    if sha256_bytes(data) != GATE_SHA256:
        raise ValueError("frozen v5 gate bytes changed")
    raw = strict_json_bytes(data, "frozen v5 gate")
    if (not isinstance(raw, dict) or
            not isinstance(raw.get("source_hashes"), dict)):
        raise ValueError("frozen v5 gate source manifest is malformed")
    return raw


def load_frozen_driver():
    if sha256_file(DRIVER) != DRIVER_SHA256:
        raise ValueError("frozen production driver bytes changed")
    gate = load_gate_manifest_without_imports()
    occupied = sorted(name for name in LOCAL_MODULE_PATHS
                      if name in sys.modules)
    occupied_numpy = sorted(name for name in sys.modules
                            if name == "numpy" or name.startswith("numpy."))
    if occupied or occupied_numpy:
        raise ValueError(
            "standalone auditor rejects preloaded computational modules")
    code_dir = str(DRIVER.parent)
    if code_dir not in sys.path:
        sys.path.insert(0, code_dir)
    specification = importlib.util.spec_from_file_location(
        "importance_d4_calibration_v5_frozen", DRIVER)
    if specification is None or specification.loader is None:
        raise ImportError("cannot load frozen production driver")
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    if module.sha256_file(module.HERE) != DRIVER_SHA256:
        raise ValueError("loaded driver does not bind its frozen bytes")
    bindings = {}
    for name, relative in LOCAL_MODULE_PATHS.items():
        imported = sys.modules.get(name)
        if imported is None or not isinstance(getattr(imported, "__file__", None),
                                              str):
            raise ValueError(f"required local module {name} was not imported")
        path = Path(imported.__file__).resolve()
        expected_path = (REPO_ROOT / relative).resolve()
        expected_sha = gate["source_hashes"].get(relative)
        snapshot = module.read_file_snapshot(path)
        if (path != expected_path or expected_sha is None or
                snapshot["sha256"] != expected_sha):
            raise ValueError(f"loaded local module {name} is not gate-pinned")
        bindings[str(path)] = module.inode_binding(snapshot)
    numpy = sys.modules.get("numpy")
    if (numpy is None or numpy.__version__ != NUMPY_VERSION or
            Path(numpy.__file__).resolve() != Path(
                "/usr/lib/python3/dist-packages/numpy/__init__.py") or
            sha256_file(numpy.__file__) != NUMPY_INIT_SHA256):
        raise ValueError("NumPy runtime differs from frozen discovery runtime")
    numpy_snapshot = module.read_file_snapshot(numpy.__file__)
    if numpy_snapshot["sha256"] != NUMPY_INIT_SHA256:
        raise ValueError("NumPy bytes changed while binding loaded runtime")
    bindings[str(Path(numpy.__file__).resolve())] = \
        module.inode_binding(numpy_snapshot)
    module._completed_audit_module_bindings = bindings
    return module


def load_decision_table():
    data = DECISION_TABLE.read_bytes()
    if sha256_bytes(data) != DECISION_TABLE_SHA256:
        raise ValueError("decision table changed after predeclaration")
    raw = strict_json_bytes(data, "decision table")
    _exact_keys(raw, {"status", "rigorous", "scope", "ordered_rules",
                      "never_implies"}, "decision table")
    if (raw["status"] != "frozen-before-v5-production-completion" or
            raw["rigorous"] is not False or
            [row.get("decision") for row in raw["ordered_rules"]] != list(
                DECISION_EXIT_CODES) or
            [row.get("exit_code") for row in raw["ordered_rules"]] != list(
                DECISION_EXIT_CODES.values())):
        raise ValueError("decision table status/order changed")
    return raw


def classify(analysis, analysis_failure):
    if analysis is None:
        if analysis_failure is None:
            raise ValueError("missing analysis has no failure diagnostic")
        return "IMPLEMENTATION_REJECTED"
    if analysis_failure is not None:
        raise ValueError("successful analysis has a failure diagnostic")
    if analysis["gates_passed"] is True:
        return "CALIBRATION_PASS"
    if analysis["extension_authorized"] is True:
        return "EXTENSION_ELIGIBLE"
    return "CALIBRATION_RETIRED"


def validate_outer_result(raw, driver, gate_bound, authorization):
    gate = gate_bound["gate"]
    _exact_keys(raw, {
        "status", "rigorous", "theorem_ready", "mode", "gate_path",
        "gate_sha256", "driver_sha256", "authorization_sha256",
        "parent_result_sha256", "gate_binding", "authorization_binding",
        "parent_result_binding", "wall_seconds", "peak_rss_kib",
        "float_encoding", "conventions", "schedule", "records",
        "record_checkpoints", "analysis", "analysis_failure",
        "fresh_exact_reconstruction_required"}, "production result")
    if (raw["status"] not in {
            "d4-stratified-calibration-pass",
            "d4-stratified-calibration-rejected"} or
            raw["rigorous"] is not False or
            raw["theorem_ready"] is not False or
            raw["mode"] != "production" or
            Path(raw["gate_path"]).resolve() != GATE.resolve() or
            raw["gate_sha256"] != GATE_SHA256 or
            raw["driver_sha256"] != DRIVER_SHA256 or
            raw["authorization_sha256"] != AUTHORIZATION_SHA256 or
            raw["parent_result_sha256"] is not None or
            raw["parent_result_binding"] is not None or
            raw["float_encoding"] != driver.FLOAT_ENCODING or
            raw["conventions"] != driver.expected_conventions() or
            raw["schedule"] != gate["schedule"] or
            raw["fresh_exact_reconstruction_required"] is not True or
            not isinstance(raw["records"], list) or
            len(raw["records"]) != 128 or
            not isinstance(raw["record_checkpoints"], list) or
            len(raw["record_checkpoints"]) != 128):
        raise ValueError("production result identity/schema flags are invalid")
    driver.validate_run_metrics(raw["wall_seconds"], raw["peak_rss_kib"])
    if raw["gate_binding"] != driver.public_binding(gate_bound):
        raise ValueError("production result gate binding changed")
    if raw["authorization_binding"] != driver.public_binding(authorization):
        raise ValueError("production result authorization binding changed")
    return True


def audit_completed_output(expected_output_sha256,
                           expected_auditor_sha256, audit_output):
    expected_output_sha256 = require_sha256(
        expected_output_sha256, "completed output SHA-256")
    # Both external trust tokens are validated before any production path is
    # opened.  In particular, a modified copy cannot bless its own hash.
    expected_auditor_sha256 = validate_expected_auditor_sha256(
        expected_auditor_sha256)
    canonical_audit_output = validate_audit_output_path(audit_output)
    decision_table = load_decision_table()
    driver = load_frozen_driver()
    gate = driver.load_and_validate_gate(GATE)
    if gate["sha256"] != GATE_SHA256:
        raise ValueError("loaded gate SHA-256 differs from frozen v5")
    authorization = driver.validate_authorization(
        AUTHORIZATION, GATE_SHA256, DRIVER_SHA256, RECORD_DIRECTORY)
    if authorization["sha256"] != AUTHORIZATION_SHA256:
        raise ValueError("production authorization SHA-256 mismatch")

    # This is deliberately the first read of the production result.  The
    # root-supplied completed digest is required before reaching this line.
    result = driver.read_file_snapshot(PRODUCTION_RESULT)
    if result["sha256"] != expected_output_sha256:
        raise ValueError("production result is partial, changed, or misbound")
    raw = strict_json_bytes(result["data"], "completed production result")
    validate_outer_result(raw, driver, gate, authorization)

    record_directory = driver.open_bound_directory(
        authorization["raw"]["record_directory_binding"])
    try:
        if record_directory["path"] != str(RECORD_DIRECTORY.resolve()):
            raise ValueError("authorization record directory path changed")
        expected_names = [driver.chain_checkpoint_path(
            record_directory["path"], spec).name
                          for spec in gate["gate"]["schedule"]["chains"]]
        observed_names = sorted(os.listdir(record_directory["descriptor"]))
        if sorted(expected_names) != observed_names:
            raise ValueError("record directory is not exactly the 128 files")

        oracle_path = REPO_ROOT / driver.REQUIRED_DATA_PATHS[0]
        vector_path = REPO_ROOT / driver.REQUIRED_DATA_PATHS[1]
        weights_path = REPO_ROOT / driver.REQUIRED_DATA_PATHS[2]
        oracle = driver.load_exact_expectation_oracle(oracle_path)
        driver.validate_analytic_zero_se_proofs(oracle)
        adapter = driver.C10ImportanceDensity(vector_path, oracle_path)
        driver.validate_adapter_provenance(adapter, gate["gate"])
        weights = driver.load_stratum_weights(
            weights_path,
            gate["gate"]["data_hashes"][driver.REQUIRED_DATA_PATHS[2]],
            prefix="baseline_", j_scale_to_numerator=1)
        driver.validate_weight_provenance(weights, oracle, gate["gate"])

        loaded = []
        for spec, claimed in zip(
                gate["gate"]["schedule"]["chains"],
                raw["record_checkpoints"]):
            driver.validate_public_binding(
                claimed, name="production checkpoint binding")
            path = driver.chain_checkpoint_path(record_directory["path"], spec)
            if claimed["path"] != str(path):
                raise ValueError("checkpoint path/order differs from schedule")
            item = driver.load_chain_checkpoint(
                path, spec, GATE_SHA256, DRIVER_SHA256,
                AUTHORIZATION_SHA256, gate["gate"]["schedule"],
                adapter=adapter, directory_handle=record_directory)
            if driver.public_binding(item) != claimed:
                raise ValueError("checkpoint bytes/inode differ from result")
            loaded.append(item)
        records = [item["record"] for item in loaded]
        if records != raw["records"]:
            raise ValueError("embedded records differ from checkpoint bytes")

        analysis, analysis_failure = driver.capture_analysis(
            records, oracle, weights, gate["gate"]["schedule"],
            adapter=adapter)
        encoded_analysis = driver._json_safe(analysis)
        encoded_failure = driver._json_safe(analysis_failure)
        if (encoded_analysis != raw["analysis"] or
                encoded_failure != raw["analysis_failure"]):
            raise ValueError("independent analysis differs from production")
        expected_status = (
            "d4-stratified-calibration-pass" if
            analysis is not None and analysis["gates_passed"] else
            "d4-stratified-calibration-rejected")
        if raw["status"] != expected_status:
            raise ValueError("production status differs from reconstruction")
        decision = classify(analysis, analysis_failure)
        hard_failures = ([] if analysis is None else sorted(
            key for key, value in analysis["hard_gates"].items()
            if not value))
        statistical_failures = ([] if analysis is None else sorted(
            key for key, value in analysis["statistical_gates"].items()
            if not value))
        checkpoint_bindings = [driver.public_binding(item) for item in loaded]
        require_auditor_unchanged(expected_auditor_sha256)
        auditor_snapshot = driver.read_file_snapshot(HERE)
        decision_table_snapshot = driver.read_file_snapshot(DECISION_TABLE)
        if auditor_snapshot["sha256"] != expected_auditor_sha256:
            raise ValueError("auditor changed before closure construction")
        if decision_table_snapshot["sha256"] != DECISION_TABLE_SHA256:
            raise ValueError("decision table changed before closure construction")
        closure = {
            gate["path"]: driver.inode_binding(gate),
            authorization["path"]: driver.inode_binding(authorization),
            result["path"]: driver.inode_binding(result),
            str(HERE): driver.inode_binding(auditor_snapshot),
            str(DECISION_TABLE.resolve()):
                driver.inode_binding(decision_table_snapshot),
            record_directory["path"]:
                driver.directory_inode_binding(record_directory),
            **{item["path"]: driver.inode_binding(item) for item in loaded},
            **driver._completed_audit_module_bindings,
        }
        report = {
            "status": "complete-independent-d4-v5-production-audit",
            "rigorous": False,
            "theorem_ready": False,
            "scope": decision_table["scope"],
            "decision": decision,
            "decision_exit_code": DECISION_EXIT_CODES[decision],
            "driver_sha256": DRIVER_SHA256,
            "gate_sha256": GATE_SHA256,
            "authorization_sha256": AUTHORIZATION_SHA256,
            "production_result_binding": driver.public_binding(result),
            "decision_table_sha256": DECISION_TABLE_SHA256,
            "auditor_sha256": expected_auditor_sha256,
            "supersedes_invalid_auditor_sha256":
                SUPERSEDES_INVALID_AUDITOR_SHA256,
            "record_directory_binding": {
                key: record_directory[key]
                for key in ("path", "device", "inode")},
            "checkpoint_count": len(loaded),
            "record_leaf_names_sha256":
                driver.canonical_object_sha256(observed_names),
            "checkpoint_manifest_sha256":
                driver.canonical_object_sha256(checkpoint_bindings),
            "records_core_sha256": driver.canonical_object_sha256(records),
            "analysis_core_sha256":
                driver.canonical_object_sha256({
                    "analysis": encoded_analysis,
                    "analysis_failure": encoded_failure}),
            "analysis_failure": encoded_failure,
            "hard_gate_failures": hard_failures,
            "statistical_gate_failures": statistical_failures,
            "wall_seconds": raw["wall_seconds"],
            "peak_rss_kib": raw["peak_rss_kib"],
            "numpy_version": NUMPY_VERSION,
            "numpy_init_sha256": NUMPY_INIT_SHA256,
            "fresh_exact_reconstruction_required": True,
            "never_implies": decision_table["never_implies"],
        }
        return (driver, gate["gate"], report, closure,
                canonical_audit_output)
    finally:
        driver.close_bound_directory(record_directory)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--expected-output-sha256", required=True)
    parser.add_argument("--expected-auditor-sha256", required=True)
    parser.add_argument("--audit-output", required=True)
    args = parser.parse_args()
    driver, gate, report, closure, audit_output = audit_completed_output(
        args.expected_output_sha256, args.expected_auditor_sha256,
        args.audit_output)
    digest = driver.write_new_result(
        audit_output, report, gate, extra_hashes=closure)
    print(json.dumps({"audit_output_sha256": digest,
                      "decision": report["decision"],
                      "exit_code": report["decision_exit_code"]},
                     sort_keys=True))
    raise SystemExit(report["decision_exit_code"])


if __name__ == "__main__":
    main()
