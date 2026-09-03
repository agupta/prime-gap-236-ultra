#!/usr/bin/env python3
"""Independent records-only audit of the frozen v6.7 recovery candidate.

No chain and no recovery publication is executed.  The checker reopens and
validates all 128 v6.6 checkpoints, verifies the unauthorized trust-root
template, tests a hypothetical authorization only through the preflight and
binding stages, and checks the narrowly scoped NumPy-Boolean serializer fix.
It deliberately emits no quotient or recovered analysis.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
from unittest import mock

import numpy as np


FILE = Path(__file__).resolve()
REPO = FILE.parents[2]
SOURCE = REPO / "agents/structural-basis/code/importance_d4_calibration_v67_recover.py"
BUILDER = REPO / "agents/structural-basis/code/build_importance_d4_calibration_v67_recovery_authorization.py"
TESTS = REPO / "agents/structural-basis/tests/test_importance_d4_calibration_v67_recover.py"
SPEC = REPO / "agents/structural-basis/IMPORTANCE-D4-CALIBRATION-V67-RECOVERY.md"
TEMPLATE = REPO / "agents/structural-basis/results/importance_d4_calibration_v67_recovery_authorization_template.json"
PINS = {
    SOURCE: "118b56e6e7fe07c3a95ed1f49da6cbaf1c0352f5f9776526ea8bb5aa0d4782f8",
    BUILDER: "31a54a963812d0da4e1ac2bbface6f145ec55fa6d0ba23752ed8ae0858680715",
    TESTS: "529a85d02902311eab5262a8809d425d43606cd6cab0bd7ac9cccf17ac019463",
    SPEC: "b4ca66588bbc0a0361530bce73c9035f3a345c3c49d5abb9c8c56108cfafd726",
    TEMPLATE: "ccaffa3cdcee2e5d5dfd42ff4c526b273b2d05cb25d35bc336bc39b5e2dccde4",
}
V66_PINS = {
    "gate": "fa1019605ef6b5efd486b234451806efcf1912f7b3f181c9511839d873b63bf6",
    "authorization": "25c516af4cefacf08405632f38797f2e43d46a7275d1e07ee3f4202a192489c2",
    "rejection": "a4f8518b52de5fb9c79e58c770d0c861c7e283481d745c31b6a8a3802761d879",
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ArithmeticError(message)


def load_recovery():
    spec = importlib.util.spec_from_file_location(
        "independent_v67_records_recovery", SOURCE)
    require(spec is not None and spec.loader is not None,
            "cannot load recovery source")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    require(Path(module.__file__).resolve() == SOURCE.resolve(),
            "wrong recovery module imported")
    return module


def canonical(value) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"),
                       allow_nan=False) + "\n").encode("ascii")


def no_chain_calls_in_sources():
    forbidden = {
        "run_one_chain", "extend_one_chain", "run_fresh_initial_chain",
        "run_fresh_extended_chain", "run_smoke"}
    found = []
    for path in (SOURCE, BUILDER):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                function = node.func
                name = (function.id if isinstance(function, ast.Name) else
                        function.attr if isinstance(function, ast.Attribute) else
                        None)
                if name in forbidden:
                    found.append((path.name, name, node.lineno))
    require(not found, f"recovery contains a chain execution call: {found}")
    return True


def make_authorization(recovery, template, target: Path, path: Path,
                       *, mutate_checkpoint=False, record_parent=False):
    raw = json.loads(json.dumps(template))
    raw["status"] = "root-authorized-v6.7-records-only-recovery"
    raw["authorized"] = True
    raw["recovery_driver_sha256"] = PINS[SOURCE]
    if record_parent:
        raw["output_parent_binding"] = recovery.V5.read_directory_binding(
            recovery.V66_RECORD_DIRECTORY)
    else:
        raw["output_parent_binding"] = recovery.V5.read_directory_binding(
            target.parent)
    raw["output_leaf"] = target.name
    if mutate_checkpoint:
        raw["checkpoint_bindings"][0]["sha256"] = "0" * 64
    path.write_bytes(canonical(raw))
    return recovery.preflight_recovery_authorization(
        path, target, PINS[SOURCE])


def build():
    for path, expected in PINS.items():
        require(sha(path) == expected, f"frozen v6.7 input changed: {path}")
    no_chain_calls_in_sources()
    recovery = load_recovery()
    require(recovery.PINNED_V66_SHA256 ==
            "69698f7766d9077bd5026dee8fc1e065b762a1f3d344ea2b7af0282763ce21f9" and
            recovery.PINNED_V66_GATE_SHA256 == V66_PINS["gate"] and
            recovery.PINNED_V66_AUTHORIZATION_SHA256 ==
            V66_PINS["authorization"] and
            recovery.PINNED_V66_REJECTED_OUTPUT_SHA256 ==
            V66_PINS["rejection"], "v6.6 trust roots changed")

    template_snapshot = recovery.V5.read_file_snapshot(TEMPLATE)
    template = recovery.V5.strict_json_bytes(
        template_snapshot["data"], "v6.7 unauthorized template")
    recovery.V5._exact_keys(template, {
        "status", "authorized", "mode", "recovery_driver_sha256",
        "recovery_source_hashes", "v66_gate_binding",
        "v66_authorization_binding", "v66_rejected_output_binding",
        "record_directory_binding", "checkpoint_bindings",
        "output_parent_binding", "output_leaf"}, "v6.7 template")
    require(template["status"] ==
            "v6.7-records-only-recovery-authorization-template" and
            template["authorized"] is False and
            template["mode"] == "records-only-no-chain-execution" and
            template["recovery_driver_sha256"] == PINS[SOURCE],
            "shipped template is not fail-closed")
    require(template["recovery_source_hashes"] == {
        relative: sha(REPO / relative)
        for relative in recovery.RECOVERY_SOURCE_RELATIVES},
            "template source closure changed")
    try:
        recovery.preflight_recovery_authorization(
            TEMPLATE, REPO / template["output_parent_binding"]["path"] /
            template["output_leaf"], PINS[SOURCE])
    except ValueError:
        pass
    else:
        raise ArithmeticError("unauthorized template passed preflight")

    # Patch every inherited execution entry point while reopening records.
    patches = []
    forbidden = lambda *a, **k: (_ for _ in ()).throw(
        AssertionError("chain execution forbidden in records-only audit"))
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
        require(len(loaded) == len(context["expected_names"]) == 128 and
                recovery.validate_record_leaf_set(context),
                "completed checkpoint inventory changed")
        bindings = [recovery.V5.public_binding(item) for item in loaded]
        require(template["checkpoint_bindings"] == bindings and
                template["record_directory_binding"] == {
                    "path": context["directory"]["path"],
                    "device": context["directory"]["device"],
                    "inode": context["directory"]["inode"]} and
                template["v66_gate_binding"] ==
                recovery.V5.public_binding(context["bound"]) and
                template["v66_authorization_binding"] ==
                recovery.V5.public_binding(context["authorization"]) and
                template["v66_rejected_output_binding"] ==
                recovery.V5.public_binding(context["rejected"]),
                "template does not exactly bind completed v6.6 inputs")

        # Locate only the serializer failure type/path.  Do not inspect or
        # emit any root, quotient, estimate, or other analysis field.
        reduced = recovery.V6.analyze_records(
            [item["record"] for item in loaded], oracle, weights,
            context["gate"]["schedule"], adapter=adapter,
            do_jackknife=False)
        bool_paths = recovery.numpy_bool_paths(reduced)
        require(tuple(bool_paths) == recovery.EXPECTED_NUMPY_BOOL_PATHS,
                "actual NumPy-Boolean repair path changed")

        # Exercise the trust-root logic without running full analysis or
        # publication.  The exact template bindings should pass once an
        # external root changes only status/output authorization.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "recovered.json"
            auth_path = root / "authorization.json"
            authorized = make_authorization(
                recovery, template, target, auth_path)
            recovery.complete_recovery_authorization(
                authorized, context, loaded, target)
            require(not target.exists(),
                    "authorization audit unexpectedly published recovery")

            bad_target = root / "bad.json"
            bad_auth = root / "bad-authorization.json"
            bad = make_authorization(
                recovery, template, bad_target, bad_auth,
                mutate_checkpoint=True)
            try:
                recovery.complete_recovery_authorization(
                    bad, context, loaded, bad_target)
            except ValueError:
                pass
            else:
                raise ArithmeticError("changed checkpoint manifest accepted")

            record_target = recovery.V66_RECORD_DIRECTORY / "forbidden.json"
            record_auth_path = root / "record-authorization.json"
            record_auth = make_authorization(
                recovery, template, record_target, record_auth_path,
                record_parent=True)
            try:
                recovery.complete_recovery_authorization(
                    record_auth, context, loaded, record_target)
            except ValueError:
                pass
            else:
                raise ArithmeticError("record-directory output alias accepted")
    finally:
        recovery.V5.close_bound_directory(context["directory"])
        for patch in reversed(patches):
            patch.stop()

    # Confirm the successor is serializer-narrow on representative legacy
    # values and still rejects every unrelated unknown type.
    representative = {
        "none": None, "builtin": True, "integer": 3,
        "string": "x", "tuple": (1, 2), "array": np.asarray([1, 2]),
        "float": 0.25, "nested": [{"x": 1}],
    }
    require(recovery.json_safe_v67(representative) ==
            recovery.LEGACY_JSON_SAFE(representative),
            "v6.7 changed a legacy serializer case")
    require(recovery.json_safe_v67(np.bool_(True)) is True,
            "NumPy Boolean repair failed")
    try:
        recovery.LEGACY_JSON_SAFE(np.bool_(True))
    except TypeError:
        pass
    else:
        raise ArithmeticError("legacy serializer no longer exhibits failure")
    try:
        recovery.json_safe_v67(object())
    except TypeError:
        pass
    else:
        raise ArithmeticError("unrelated unknown serializer type accepted")

    for path, expected in PINS.items():
        require(sha(path) == expected,
                f"v6.7 input moved during audit: {path}")
    return {
        "status": "AUDIT PASS",
        "scope": "v6.7 records-only recovery authorization and replay only",
        "checker_sha256": sha(FILE),
        "pinned": {str(path.relative_to(REPO)): digest
                   for path, digest in PINS.items()},
        "checks": {
            "shipped_authorization_template_is_false": True,
            "static_chain_execution_calls_absent": True,
            "runtime_chain_entry_points_trapped": True,
            "checkpoint_count": 128,
            "all_checkpoint_hashes_and_inodes_match_template": True,
            "held_record_directory_and_exact_leaf_set": True,
            "v66_gate_authorization_rejection_sentinel_bound": True,
            "recovery_source_and_loaded_module_closure": True,
            "actual_numpy_bool_paths": bool_paths,
            "repair_is_serializer_narrow": True,
            "unknown_types_still_reject": True,
            "hypothetical_authorization_preflight_only": True,
            "checkpoint_manifest_mutation_rejected": True,
            "record_directory_output_alias_rejected": True,
            "recovery_publication_executed": False,
            "recovery_analysis_with_jackknife_executed": False,
            "quotient_or_root_inspected": False,
        },
        "decision": (
            "safe for an explicit external root authorization of this "
            "byte-frozen records-only recovery; any resulting calibration "
            "remains nonrigorous discovery data and requires exact "
            "reconstruction before mathematical use"),
    }


def main():
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
