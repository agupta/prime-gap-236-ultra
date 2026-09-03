#!/usr/bin/env python3
"""Records-only recovery for the frozen v6.6 calibration run.

The v6.6 production run completed all 128 authorized checkpoints, then its
final serializer rejected a ``numpy.bool_`` value (whose displayed type name
is ``bool``).  This successor never runs a Markov chain.  It reopens every
checkpoint through the held, originally authorized directory descriptor,
revalidates it with the byte-pinned v6.6 validator, recomputes the complete
analysis, converts NumPy booleans explicitly, and publishes to a new output.

Publication additionally requires a separate recovery authorization binding
this source, every checkpoint inode/hash, the original gate/authorization and
rejection sentinel, and the held output-parent inode.  This remains a
nonrigorous discovery calibration and emits no theorem claim.
"""

from __future__ import annotations

import argparse
from decimal import Decimal
from fractions import Fraction
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import resource
import stat
import sys
import time

import numpy as np


FILE = Path(__file__).resolve()
REPO = FILE.parents[3]
CODE = FILE.parent
V66_PATH = CODE / "importance_d4_calibration_v66.py"
V66_GATE = (
    REPO / "agents/structural-basis/results/"
    "importance_d4_calibration_gate_v66.json")
V66_AUTHORIZATION = (
    REPO / "agents/structural-basis/results/"
    "importance_d4_calibration_v66_authorization.json")
V66_REJECTED_OUTPUT = (
    REPO / "agents/structural-basis/results/"
    "importance_d4_calibration_v66_production.json")
V66_RECORD_DIRECTORY = (
    REPO / "agents/structural-basis/results/"
    "importance_d4_calibration_v66_records")

PINNED_V66_SHA256 = (
    "69698f7766d9077bd5026dee8fc1e065b762a1f3d344ea2b7af0282763ce21f9"
)
PINNED_V66_GATE_SHA256 = (
    "fa1019605ef6b5efd486b234451806efcf1912f7b3f181c9511839d873b63bf6"
)
PINNED_V66_AUTHORIZATION_SHA256 = (
    "25c516af4cefacf08405632f38797f2e43d46a7275d1e07ee3f4202a192489c2"
)
PINNED_V66_REJECTED_OUTPUT_SHA256 = (
    "a4f8518b52de5fb9c79e58c770d0c861c7e283481d745c31b6a8a3802761d879"
)
PINNED_V66_REJECTED_BYTES = \
    b'{"status":"rejected-incomplete-calibration-output"}\n'
EXPECTED_NUMPY_BOOL_PATHS = (
    "$.hard_gates.constant_coordinate_sums_one",
)

RUNTIME_MODULE_RELATIVES = {
    "importance_conditional":
        "agents/structural-basis/code/importance_conditional.py",
    "importance_d4_calibration":
        "agents/structural-basis/code/importance_d4_calibration.py",
    "importance_d4_calibration_v6":
        "agents/structural-basis/code/importance_d4_calibration_v6.py",
    "importance_d4_calibration_v61":
        "agents/structural-basis/code/importance_d4_calibration_v61.py",
    "importance_d4_calibration_v62":
        "agents/structural-basis/code/importance_d4_calibration_v62.py",
    "importance_d4_calibration_v63":
        "agents/structural-basis/code/importance_d4_calibration_v63.py",
    "importance_d4_calibration_v64":
        "agents/structural-basis/code/importance_d4_calibration_v64.py",
    "importance_d4_calibration_v65":
        "agents/structural-basis/code/importance_d4_calibration_v65.py",
    "importance_density":
        "agents/structural-basis/code/importance_density.py",
    "importance_envelope":
        "agents/structural-basis/code/importance_envelope.py",
    "importance_envelope_v6":
        "agents/structural-basis/code/importance_envelope_v6.py",
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
    "importance_whitening_v6":
        "agents/structural-basis/code/importance_whitening_v6.py",
}

RECOVERY_SOURCE_RELATIVES = (
    "agents/structural-basis/code/importance_d4_calibration_v67_recover.py",
    "agents/structural-basis/code/"
    "build_importance_d4_calibration_v67_recovery_authorization.py",
    "agents/structural-basis/tests/"
    "test_importance_d4_calibration_v67_recover.py",
    "agents/structural-basis/IMPORTANCE-D4-CALIBRATION-V67-RECOVERY.md",
    "agents/audit/IMPORTANCE-D4-CALIBRATION-V66-PRELAUNCH-AUDIT.md",
    "agents/audit/verify_importance_d4_calibration_v66.py",
    "agents/audit/test_importance_d4_calibration_v66_hostile.py",
)


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def sha256_file(path):
    return sha256_bytes(Path(path).read_bytes())


def validate_recovery_paths(output_target, authorization_output,
                            record_directory=V66_RECORD_DIRECTORY):
    target = Path(output_target).resolve()
    authority = Path(authorization_output).resolve()
    records = Path(record_directory).resolve()
    if target == authority:
        raise ValueError("recovery output and authorization output alias")
    for path in (target, authority):
        if path == records or path.is_relative_to(records):
            raise ValueError("recovery publication may not alter record directory")
        if path.exists():
            raise FileExistsError(f"fresh recovery path already exists: {path}")
    return target, authority


_occupied = sorted(set(RUNTIME_MODULE_RELATIVES) & set(sys.modules))
if _occupied:
    raise RuntimeError(
        "v6.7 recovery requires a fresh standalone interpreter; preloaded "
        "local modules: " + ",".join(_occupied))
if sha256_file(V66_PATH) != PINNED_V66_SHA256:
    raise RuntimeError("frozen v6.6 driver changed")
if str(CODE) not in sys.path:
    sys.path.insert(0, str(CODE))
_spec = importlib.util.spec_from_file_location(
    "importance_d4_calibration_v66_recovery_dependency", V66_PATH)
V66 = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = V66
_spec.loader.exec_module(V66)
V6 = V66.v65.v64.v63.v62.v61.v6
V5 = V6.v5
LEGACY_JSON_SAFE = V5._json_safe


def json_safe_v67(value):
    """Legacy JSON conversion plus an explicit NumPy-Boolean case."""
    if isinstance(value, np.bool_):
        return bool(value)
    if isinstance(value, np.ndarray):
        return json_safe_v67(value.tolist())
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, (np.floating, float)):
        number = float(value)
        if not math.isfinite(number):
            if math.isnan(number):
                label = "nan"
            elif number > 0:
                label = "positive-infinity"
            else:
                label = "negative-infinity"
            return {"nonfinite_float": label}
        return {"float_hex": V5.float_hex(number)}
    if isinstance(value, Fraction):
        return str(value)
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, tuple):
        return [json_safe_v67(item) for item in value]
    if isinstance(value, list):
        return [json_safe_v67(item) for item in value]
    if isinstance(value, dict):
        return {str(key): json_safe_v67(item)
                for key, item in value.items() if key != "local_cache"}
    if value is None or isinstance(value, (str, int, bool)):
        return value
    raise TypeError(f"cannot serialize value of type {type(value).__name__}")


def numpy_bool_paths(value, path="$", answer=None):
    """Return exact analysis paths converted by the v6.7 repair."""
    answer = [] if answer is None else answer
    if isinstance(value, np.bool_):
        answer.append(path)
    elif isinstance(value, np.ndarray):
        # Boolean ndarrays are serialized elementwise by the legacy ndarray
        # rule and therefore do not trigger the scalar failure.  Still list
        # their scalar paths so the repair surface is explicit.
        for index, item in np.ndenumerate(value):
            numpy_bool_paths(item, path + "[" + "][".join(
                str(i) for i in index) + "]", answer)
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            numpy_bool_paths(item, f"{path}[{index}]", answer)
    elif isinstance(value, dict):
        for key, item in value.items():
            if key != "local_cache":
                numpy_bool_paths(item, f"{path}.{key}", answer)
    return answer


def _exact_binding(value, expected, name):
    if value != expected:
        raise ValueError(f"{name} binding changed")
    V5.validate_public_binding(value, expected_sha256=expected["sha256"],
                               name=name)
    return True


def _snapshot_expected(path, digest, name):
    snapshot = V5.read_file_snapshot(path)
    if snapshot["sha256"] != digest:
        raise ValueError(f"{name} SHA-256 changed")
    return snapshot


def initialize_v66_runtime():
    """Install exactly the frozen v6.6 validation/analysis hooks."""
    if sha256_file(V66_PATH) != PINNED_V66_SHA256:
        raise RuntimeError("v6.6 driver changed after import")
    V66.install_runtime()
    V6._patch_v5_runtime()
    # Install the sole successor behavior only after the frozen hooks.
    V5._json_safe = json_safe_v67
    return True


def validate_loaded_module_closure(gate):
    """Bind every reused local Python object to the gate-pinned source."""
    for name, relative in RUNTIME_MODULE_RELATIVES.items():
        module = sys.modules.get(name)
        if module is None:
            raise RuntimeError(f"required runtime module was not loaded: {name}")
        path = Path(getattr(module, "__file__", "")).resolve()
        expected_path = (REPO / relative).resolve()
        if (path != expected_path or
                gate["source_hashes"].get(relative) != sha256_file(path)):
            raise RuntimeError(f"runtime module binding changed: {name}")
    if (Path(V66.__file__).resolve() != V66_PATH.resolve() or
            sha256_file(V66.__file__) != PINNED_V66_SHA256):
        raise RuntimeError("loaded v6.6 module binding changed")
    return True


def open_completed_v66_inputs():
    """Open and validate the original gate, authority, directory and data."""
    initialize_v66_runtime()
    gate_snapshot = _snapshot_expected(
        V66_GATE, PINNED_V66_GATE_SHA256, "v6.6 gate")
    bound = V66.load_and_validate_gate(V66_GATE)
    if V5.public_binding(gate_snapshot) != V5.public_binding(bound):
        raise ValueError("v6.6 gate was not parsed from the bound bytes")
    gate = bound["gate"]
    validate_loaded_module_closure(gate)
    driver_sha = gate["source_hashes"][V66.DRIVER_RELATIVE]
    if driver_sha != PINNED_V66_SHA256:
        raise ValueError("v6.6 gate driver binding changed")
    auth_snapshot = _snapshot_expected(
        V66_AUTHORIZATION, PINNED_V66_AUTHORIZATION_SHA256,
        "v6.6 authorization")
    authorization = V5.validate_authorization(
        V66_AUTHORIZATION, bound["sha256"], driver_sha,
        V66_RECORD_DIRECTORY)
    if V5.public_binding(auth_snapshot) != V5.public_binding(authorization):
        raise ValueError("v6.6 authorization was not parsed from bound bytes")
    rejected = _snapshot_expected(
        V66_REJECTED_OUTPUT, PINNED_V66_REJECTED_OUTPUT_SHA256,
        "v6.6 rejected output")
    if rejected["data"] != PINNED_V66_REJECTED_BYTES:
        raise ValueError("v6.6 rejection sentinel bytes changed")
    directory = V5.open_bound_directory(
        authorization["raw"]["record_directory_binding"])
    expected_names = tuple(V5.chain_checkpoint_path(
        directory["path"], chain).name for chain in gate["schedule"]["chains"])
    observed_names = tuple(sorted(os.listdir(directory["descriptor"])))
    if (len(expected_names) != 128 or len(set(expected_names)) != 128 or
            observed_names != tuple(sorted(expected_names))):
        V5.close_bound_directory(directory)
        raise ValueError("v6.6 completed directory is not the exact 128-leaf set")
    return {
        "bound": bound,
        "gate": gate,
        "authorization": authorization,
        "rejected": rejected,
        "directory": directory,
        "expected_names": expected_names,
    }


def load_completed_checkpoints(context):
    """Reopen all checkpoints in canonical schedule order and validate them."""
    gate = context["gate"]
    bound = context["bound"]
    authorization = context["authorization"]
    directory = context["directory"]
    oracle_path = REPO / V66.REQUIRED_DATA_PATHS[0]
    vector_path = REPO / V66.REQUIRED_DATA_PATHS[1]
    weights_path = REPO / V66.REQUIRED_DATA_PATHS[2]
    oracle = V6.load_transformed_oracle(oracle_path)
    V5.validate_analytic_zero_se_proofs(oracle)
    adapter = V6.WhitenedC10ImportanceDensity(vector_path, oracle_path)
    V6.validate_adapter_provenance(adapter, gate)
    weights = V5.load_stratum_weights(
        weights_path, gate["data_hashes"][V66.REQUIRED_DATA_PATHS[2]],
        prefix="baseline_", j_scale_to_numerator=1)
    V6.validate_weight_provenance(weights, oracle, gate)
    loaded = []
    for chain in gate["schedule"]["chains"]:
        path = V5.chain_checkpoint_path(directory["path"], chain)
        loaded.append(V5.load_chain_checkpoint(
            path, chain, bound["sha256"], PINNED_V66_SHA256,
            authorization["sha256"], gate["schedule"], adapter=adapter,
            directory_handle=directory))
    if [Path(item["path"]).name for item in loaded] != \
            list(context["expected_names"]):
        raise ValueError("v6.6 checkpoint load order changed")
    return loaded, oracle, adapter, weights


def preflight_recovery_authorization(path, output, expected_self_sha256):
    """Validate the external trust root before opening any checkpoint."""
    snapshot = V5.read_file_snapshot(path)
    raw = V5.strict_json_bytes(snapshot["data"], "v6.7 recovery authorization")
    V5._exact_keys(raw, {
        "status", "authorized", "mode", "recovery_driver_sha256",
        "recovery_source_hashes", "v66_gate_binding",
        "v66_authorization_binding", "v66_rejected_output_binding",
        "record_directory_binding", "checkpoint_bindings",
        "output_parent_binding", "output_leaf"},
        "v6.7 recovery authorization")
    driver_sha = sha256_file(FILE)
    if (raw["status"] != "root-authorized-v6.7-records-only-recovery" or
            raw["authorized"] is not True or
            raw["mode"] != "records-only-no-chain-execution" or
            raw["recovery_driver_sha256"] != driver_sha or
            driver_sha != expected_self_sha256):
        raise ValueError("v6.7 recovery authorization status changed")
    source_hashes = raw["recovery_source_hashes"]
    if (not isinstance(source_hashes, dict) or
            set(source_hashes) != set(RECOVERY_SOURCE_RELATIVES)):
        raise ValueError("v6.7 recovery source closure changed")
    source_snapshots = {}
    for relative, expected in source_hashes.items():
        if (not isinstance(expected, str) or len(expected) != 64 or
                any(character not in "0123456789abcdef"
                    for character in expected)):
            raise ValueError(f"malformed v6.7 source hash: {relative}")
        source = V5.read_file_snapshot(REPO / relative)
        if source["sha256"] != expected:
            raise ValueError(f"v6.7 recovery source changed: {relative}")
        source_snapshots[relative] = source
    if source_hashes[RECOVERY_SOURCE_RELATIVES[0]] != driver_sha:
        raise ValueError("authorization does not bind this recovery driver")
    output = Path(output)
    parent_binding = V5.validate_directory_binding(
        raw["output_parent_binding"], output.parent,
        name="v6.7 output parent")
    if (raw["output_leaf"] != output.name or
            output.name in ("", ".", "..") or "/" in output.name):
        raise ValueError("v6.7 recovery output path is unauthorized")
    if Path(snapshot["path"]) == output.resolve():
        raise ValueError("v6.7 authorization aliases recovery output")
    return {"raw": raw, **V5.public_binding(snapshot),
            "output_parent": parent_binding,
            "source_snapshots": source_snapshots}


def complete_recovery_authorization(preflight, context, loaded, output):
    """Bind original v6.6 inputs and all checkpoints to the trust root."""
    raw = preflight["raw"]
    _exact_binding(raw["v66_gate_binding"],
                   V5.public_binding(context["bound"]), "v6.6 gate")
    _exact_binding(raw["v66_authorization_binding"],
                   V5.public_binding(context["authorization"]),
                   "v6.6 authorization")
    _exact_binding(raw["v66_rejected_output_binding"],
                   V5.public_binding(context["rejected"]),
                   "v6.6 rejection sentinel")
    expected_directory = {
        "path": context["directory"]["path"],
        "device": context["directory"]["device"],
        "inode": context["directory"]["inode"],
    }
    if raw["record_directory_binding"] != expected_directory:
        raise ValueError("v6.7 authorization record directory changed")
    V5.validate_open_directory(context["directory"])
    expected_checkpoints = [V5.public_binding(item) for item in loaded]
    if raw["checkpoint_bindings"] != expected_checkpoints:
        raise ValueError("v6.7 authorization checkpoint manifest changed")
    output = Path(output)
    if output.parent.resolve() == Path(context["directory"]["path"]):
        raise ValueError("v6.7 recovery output path is unauthorized")
    return preflight


def validate_record_leaf_set(context):
    V5.validate_open_directory(context["directory"])
    observed = tuple(sorted(os.listdir(context["directory"]["descriptor"])))
    if observed != tuple(sorted(context["expected_names"])):
        raise ValueError("v6.6 record-directory leaf set changed")
    return True


def analyze_completed_records(loaded, oracle, adapter, weights, schedule):
    records = [item["record"] for item in loaded]
    return V6.capture_analysis(
        records, oracle, weights, schedule, adapter=adapter)


def publish_recovery(context, loaded, recovery_authorization,
                     analysis, failure, output, started):
    gate = context["gate"]
    paths = numpy_bool_paths(analysis) if analysis is not None else []
    # The frozen failure must be explained by at least one NumPy Boolean; do
    # not silently use this successor as an unrelated serialization rewrite.
    if analysis is not None and tuple(paths) != EXPECTED_NUMPY_BOOL_PATHS:
        raise ArithmeticError("v6.6 NumPy Boolean repair surface changed")
    status = ("d4-exact-whitened-calibration-v67-recovery-pass"
              if analysis is not None and analysis["gates_passed"] else
              "d4-exact-whitened-calibration-v67-recovery-rejected")
    wall = time.perf_counter() - started
    peak = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    V5.validate_run_metrics(V5.float_hex(wall), peak)
    payload = {
        "status": status,
        "rigorous": False,
        "theorem_ready": False,
        "mode": "records-only-no-chain-execution",
        "recovery_driver_sha256": sha256_file(FILE),
        "recovery_authorization_binding":
            V5.public_binding(recovery_authorization),
        "v66_gate_binding": V5.public_binding(context["bound"]),
        "v66_authorization_binding":
            V5.public_binding(context["authorization"]),
        "v66_rejected_output_binding":
            V5.public_binding(context["rejected"]),
        "record_directory_binding": {
            "path": context["directory"]["path"],
            "device": context["directory"]["device"],
            "inode": context["directory"]["inode"],
        },
        "wall_seconds": V5.float_hex(wall),
        "peak_rss_kib": peak,
        "float_encoding": V5.FLOAT_ENCODING,
        "conventions": gate["conventions"],
        "schedule": gate["schedule"],
        "records": [item["record"] for item in loaded],
        "record_checkpoints": [V5.public_binding(item) for item in loaded],
        "analysis": analysis,
        "analysis_failure": failure,
        "numpy_bool_paths_converted": paths,
        "fresh_exact_reconstruction_required": True,
    }
    extra = {
        context["bound"]["path"]: V5.inode_binding(context["bound"]),
        context["authorization"]["path"]:
            V5.inode_binding(context["authorization"]),
        context["rejected"]["path"]: V5.inode_binding(context["rejected"]),
        context["directory"]["path"]:
            V5.directory_inode_binding(context["directory"]),
        recovery_authorization["path"]:
            V5.inode_binding(recovery_authorization),
        str(FILE): V5.inode_binding(V5.read_file_snapshot(FILE)),
        **{item["path"]: V5.inode_binding(item) for item in loaded},
    }
    for snapshot in recovery_authorization["source_snapshots"].values():
        extra[snapshot["path"]] = V5.inode_binding(snapshot)
    validate_record_leaf_set(context)
    output_parent = V5.open_bound_directory(
        recovery_authorization["raw"]["output_parent_binding"])
    try:
        return status, V5.write_new_result(
            output, payload, gate, extra_hashes=extra,
            directory_handle=output_parent)
    finally:
        V5.close_bound_directory(output_parent)


def main():
    started = time.perf_counter()
    parser = argparse.ArgumentParser()
    parser.add_argument("--expected-recovery-sha256", required=True)
    parser.add_argument("--authorization", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    expected = args.expected_recovery_sha256
    if (len(expected) != 64 or
            any(character not in "0123456789abcdef" for character in expected) or
            sha256_file(FILE) != expected):
        raise SystemExit("v6.7 recovery source does not match external SHA-256")
    recovery_authorization = preflight_recovery_authorization(
        args.authorization, args.output, expected)
    context = open_completed_v66_inputs()
    try:
        loaded, oracle, adapter, weights = load_completed_checkpoints(context)
        complete_recovery_authorization(
            recovery_authorization, context, loaded, args.output)
        validate_record_leaf_set(context)
        analysis, failure = analyze_completed_records(
            loaded, oracle, adapter, weights, context["gate"]["schedule"])
        status, digest = publish_recovery(
            context, loaded, recovery_authorization, analysis, failure,
            args.output, started)
    finally:
        V5.close_bound_directory(context["directory"])
    print(json.dumps({"status": status, "output_sha256": digest,
                      "record_count": len(loaded)}, sort_keys=True))
    if analysis is None or not analysis["gates_passed"]:
        raise SystemExit("v6.7 recovered analysis failed frozen gates")


if __name__ == "__main__":
    main()
