#!/usr/bin/env python3
"""Independent, production-free hostile audit of the D4 importance gate v5.

This file never runs the 128-chain schedule.  Its only stochastic work is the
eight-sample smoke schedule used to check normal/-O replay and checkpoint
plumbing.  It deliberately does not import the producer's unittest module.
"""

from __future__ import annotations

import copy
import hashlib
import importlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from decimal import Decimal, localcontext
from fractions import Fraction
from pathlib import Path
from unittest import mock

import numpy as np


HERE = Path(__file__).resolve()
PROJECT = HERE.parents[2]
CODE = PROJECT / "agents/structural-basis/code"
sys.path.insert(0, str(CODE))

CAL = importlib.import_module("importance_d4_calibration")
DENSITY = importlib.import_module("importance_density")
ORACLE = importlib.import_module("importance_oracle")
WEIGHTS = importlib.import_module("importance_stratum_weights")

DRIVER = CODE / "importance_d4_calibration.py"
PRODUCER_TEST = PROJECT / \
    "agents/structural-basis/tests/test_importance_d4_calibration.py"
SPEC = PROJECT / "agents/structural-basis/IMPORTANCE-D4-CALIBRATION-SPEC.md"
GATE = PROJECT / \
    "agents/structural-basis/results/importance_d4_calibration_gate_v5.json"
INVALID_V1 = PROJECT / \
    "agents/structural-basis/results/importance_d4_calibration_gate.json"
INVALID_V2 = PROJECT / \
    "agents/structural-basis/results/importance_d4_calibration_gate_v2.json"
INVALID_V3 = PROJECT / \
    "agents/structural-basis/results/importance_d4_calibration_gate_v3.json"
INVALID_V4 = PROJECT / \
    "agents/structural-basis/results/importance_d4_calibration_gate_v4.json"
PARAMETERS = PROJECT / \
    "agents/exact-integrator/results/c10_stratum_quadratic_cappedopt_D4_exact.json"
VECTOR = PROJECT / \
    "agents/exact-integrator/results/c10_capped_D4_decimal55_vector_input.json"
NORMALIZERS = PROJECT / \
    "agents/exact-integrator/results/c10_stratum_linear_D4_decimal160_cut10.json"

EXPECTED = {
    DRIVER: "b0b4350ff1804530724c87b8693aa4dd0059904f3eb9d72696497fb3c90c1b41",
    PRODUCER_TEST:
        "f3439db90a057b94d8df031e07ab648020f5d76430b85b097973e80b7fe0399c",
    SPEC: "2de6acd05a8cb4b969368887efec8c721a939e9c33b84a1ed67e88581b7a7b48",
    GATE: "860a9a51284187388e2384b7ca19615dc7d17eb523a7a4fa4d5617e2e6f29196",
}
INVALID_SHAS = (
    "fcce4e339c9b7d23eb39bf74fe88f82592ea101fd0be1fea3c9691f760ed237c",
    "0d52e2d0c730f01d459c20a3091f312edfec3ea86a253775b452de26fa5dcb03",
    "2e2417e30ded2520a16a5778cb9d56833b17524fe92b51add5418bf1ae27e282",
    "a2ca98514d0aa31463aaeca2d46baec400e8d4d54f9fc54e068b8684d235f8f6",
)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class ImportanceV5HostileAudit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        for path, wanted in EXPECTED.items():
            if digest(path) != wanted:
                raise AssertionError(f"candidate bytes changed: {path}")
        cls.bound = CAL.load_and_validate_gate(GATE)
        cls.gate = cls.bound["gate"]
        cls.adapter = DENSITY.C10ImportanceDensity(VECTOR, PARAMETERS)
        cls.oracle = ORACLE.load_exact_expectation_oracle(PARAMETERS)
        normalizer_sha = cls.gate["data_hashes"][
            CAL.REQUIRED_DATA_PATHS[2]]
        cls.weights = WEIGHTS.load_stratum_weights(
            NORMALIZERS, normalizer_sha, prefix="baseline_",
            j_scale_to_numerator=1)

    @classmethod
    def tearDownClass(cls):
        for path, wanted in EXPECTED.items():
            if digest(path) != wanted:
                raise AssertionError(f"candidate mutated during audit: {path}")

    def test_gate_schema_supersession_and_complete_closure(self):
        self.assertEqual(self.bound["sha256"], EXPECTED[GATE])
        self.assertEqual(self.gate["supersedes_invalid_gate_sha256s"],
                         list(INVALID_SHAS))
        self.assertFalse(self.gate["production_launch_authorized"])
        self.assertFalse(self.gate["rigorous"])
        self.assertEqual(self.gate["conventions"], CAL.expected_conventions())
        self.assertEqual(self.gate["conventions"]["k"], 48)
        self.assertEqual(
            self.gate["conventions"]["feature_normalization"],
            "(L/alpha)^a*(Z/alpha)^b")
        self.assertEqual(
            self.gate["conventions"]
            ["j_stratum_artifact_scale_to_48J_numerator"], 1)
        for old in (INVALID_V1, INVALID_V2, INVALID_V3, INVALID_V4):
            with self.assertRaises(ValueError):
                CAL.load_and_validate_gate(old)
        # The gate path set is exact, not a permissive subset.
        self.assertEqual(set(self.gate["source_hashes"]),
                         set(CAL.REQUIRED_SOURCE_PATHS))
        self.assertEqual(set(self.gate["data_hashes"]),
                         set(CAL.REQUIRED_DATA_PATHS))

    def test_exact_geometry_masks_and_only_local_whitelist(self):
        self.assertTrue(CAL.validate_adapter_provenance(
            self.adapter, self.gate))
        self.assertTrue(CAL.validate_analytic_zero_se_proofs(self.oracle))
        branches = CAL.exact_c10_common_branch_presence()
        self.assertEqual([row["small"] for row in branches], [True] * 16)
        self.assertEqual([row["large"] for row in branches],
                         [True] * 15 + [False])
        self.assertGreater(Fraction(16, 100), Fraction(97, 625))
        self.assertLess(Fraction(15, 100), Fraction(97, 625))
        self.assertEqual(sum(len(CAL.exact_local_active_pairs("I", r))
                             for r in range(16)), 321)
        self.assertEqual(sum(len(CAL.exact_local_active_pairs("J", r))
                             for r in range(16)), 1158)
        i_mask, j_mask = CAL.structural_masks()
        self.assertEqual((int(i_mask.sum()), int(j_mask.sum())), (336, 876))

        local = np.zeros((6, 6))
        se = np.ones((6, 6))
        local[0, 0] = 1
        se[0, 0] = 0
        self.assertEqual(CAL.local_zero_se_failures("J", 15, local, se), [])
        se[0, 1] = se[1, 0] = 0
        self.assertEqual(CAL.local_zero_se_failures("J", 15, local, se),
                         [(0, 1)])
        exact = np.zeros((96, 96))
        global_se = np.ones((96, 96))
        mask = np.zeros((96, 96), dtype=bool)
        exact[90, 90] = 1
        global_se[90, 90] = 0
        mask[90, 90] = True
        self.assertEqual(CAL.global_zero_se_failures(
            exact, global_se, mask), [(90, 90)])

    def test_normalizer_factor_and_exact_base_forms(self):
        self.assertEqual(self.weights["j_scale_to_numerator"], 1)
        self.assertTrue(CAL.validate_weight_provenance(
            self.weights, self.oracle, self.gate))
        self.assertEqual(sum(self.weights["i_weights"]), Decimal(1))
        self.assertEqual(sum(self.weights["j_weights"]), Decimal(1))
        with localcontext() as context:
            context.prec = 220
            exact_i = Decimal(self.oracle["I0"].numerator) / \
                Decimal(self.oracle["I0"].denominator)
            exact_b = Decimal(self.oracle["B0"].numerator) / \
                Decimal(self.oracle["B0"].denominator)
            self.assertLess(abs(self.weights["denominator"] / exact_i - 1),
                            Decimal("1e-110"))
            self.assertLess(abs(self.weights["numerator"] / exact_b - 1),
                            Decimal("1e-110"))
        wrong = dict(self.weights)
        wrong["j_scale_to_numerator"] = 48
        with self.assertRaises(ValueError):
            CAL.validate_weight_provenance(wrong, self.oracle, self.gate)

    def test_normal_and_optimized_smoke_records_are_identical(self):
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            outputs = []
            for optimized in (False, True):
                output = directory / ("optimized.json" if optimized else
                                      "normal.json")
                command = [sys.executable]
                if optimized:
                    command.append("-O")
                command += [str(DRIVER), "--gate", str(GATE),
                            "--mode", "smoke", "--output", str(output)]
                subprocess.run(command, cwd=PROJECT, check=True,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, text=True)
                outputs.append(json.loads(output.read_bytes()))
            for value in outputs:
                value.pop("wall_seconds")
                value.pop("peak_rss_kib")
            self.assertEqual(outputs[0], outputs[1])
            self.assertEqual(outputs[0]["status"],
                             "d4-calibration-tiny-smoke-only")
            self.assertEqual(len(outputs[0]["records"]), 2)

    def test_second_moment_pairing_and_fresh_only_trust_boundary(self):
        schedule = CAL.tiny_smoke_schedule()
        spec = schedule["chains"][0]
        honest = CAL.run_one_chain(self.adapter, spec, schedule)
        self.assertTrue(CAL.validate_chain_record(
            honest, spec, schedule, adapter=self.adapter))

        # A coordinated forgery can satisfy algebraic moment consistency.
        # This is expected and is why no preexisting checkpoint is trusted.
        coordinated = copy.deepcopy(honest)
        column = 1
        forged_second = 0.9
        for row in coordinated["batch_upper_second_means"]:
            row[column] = float(forged_second).hex()
        coordinated["raw_second_sum"][column] = float(
            forged_second * coordinated["sample_count"]).hex()
        self.assertTrue(CAL.validate_chain_record(
            coordinated, spec, schedule, adapter=self.adapter))

        with tempfile.TemporaryDirectory() as directory:
            record_dir = Path(directory) / "records"
            record_dir.mkdir()
            binding = CAL.read_directory_binding(record_dir)
            handle = CAL.open_bound_directory(binding)
            try:
                checkpoint = CAL.chain_checkpoint_path(record_dir, spec)
                checkpoint.write_text(json.dumps({"record": coordinated}))
                with self.assertRaises(FileExistsError):
                    CAL.validate_fresh_checkpoint_directory(
                        handle, CAL.expected_schedule()["chains"])
            finally:
                CAL.close_bound_directory(handle)

    def test_create_after_absence_scan_is_closed_by_o_excl(self):
        schedule = CAL.tiny_smoke_schedule()
        spec = schedule["chains"][0]
        honest = CAL.run_one_chain(self.adapter, spec, schedule)
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            record_dir = directory / "records"
            record_dir.mkdir()
            directory_binding = CAL.read_directory_binding(record_dir)
            directory_handle = CAL.open_bound_directory(directory_binding)
            CAL.validate_fresh_checkpoint_directory(
                directory_handle, CAL.expected_schedule()["chains"])
            gate_file = directory / "gate.json"
            gate_file.write_text("{}")
            auth_file = directory / "auth.json"
            auth_file.write_text("{}")
            gate_snapshot = CAL.read_file_snapshot(gate_file)
            auth_snapshot = CAL.read_file_snapshot(auth_file)
            gate_bound = {**gate_snapshot,
                          "gate": {"source_hashes": {}, "data_hashes": {}}}
            target = CAL.chain_checkpoint_path(record_dir, spec)

            def create_racer(*_args, **_kwargs):
                target.write_bytes(b"foreign-create-after-scan")
                return honest

            try:
                with mock.patch.object(CAL, "run_one_chain",
                                       side_effect=create_racer):
                    with self.assertRaises(FileExistsError):
                        CAL.run_fresh_initial_chain(
                            self.adapter, spec, schedule, directory_handle,
                            "a" * 64, "b" * 64, auth_snapshot, gate_bound,
                            progress=False)
                self.assertEqual(target.read_bytes(),
                                 b"foreign-create-after-scan")
            finally:
                CAL.close_bound_directory(directory_handle)

    def test_mutable_ancestor_symlink_cannot_redirect_authorized_directory(self):
        """Regression for the v3 raw-path/canonical-path TOCTOU.

        The authorization binds real_a/records.  A raw spelling through an
        ancestor symlink must not be usable after that symlink is redirected
        to real_b.  Candidate v3 incorrectly succeeds and writes in real_b;
        the repaired driver must raise before publishing any checkpoint.
        """
        schedule = CAL.tiny_smoke_schedule()
        spec = schedule["chains"][0]
        honest = CAL.run_one_chain(self.adapter, spec, schedule)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            real_a = root / "real-a"
            real_b = root / "real-b"
            (real_a / "records").mkdir(parents=True)
            (real_b / "records").mkdir(parents=True)
            alias = root / "alias"
            alias.symlink_to(real_a, target_is_directory=True)
            raw_record_dir = alias / "records"
            binding = CAL.read_directory_binding(raw_record_dir)
            self.assertEqual(binding["path"],
                             str((real_a / "records").resolve()))
            handle = CAL.open_bound_directory(binding)
            CAL.validate_fresh_checkpoint_directory(
                handle, CAL.expected_schedule()["chains"])

            gate_file = root / "gate.json"
            gate_file.write_text("{}")
            auth_file = root / "auth.json"
            auth_file.write_text("{}")
            gate_snapshot = CAL.read_file_snapshot(gate_file)
            auth_snapshot = CAL.read_file_snapshot(auth_file)
            gate_bound = {**gate_snapshot,
                          "gate": {"source_hashes": {}, "data_hashes": {}}}

            alias.unlink()
            alias.symlink_to(real_b, target_is_directory=True)
            try:
                with mock.patch.object(CAL, "run_one_chain",
                                       return_value=honest):
                    loaded = CAL.run_fresh_initial_chain(
                        self.adapter, spec, schedule, handle,
                        "a" * 64, "b" * 64, auth_snapshot, gate_bound,
                        progress=False)
                intended = CAL.chain_checkpoint_path(real_a / "records", spec)
                foreign = CAL.chain_checkpoint_path(real_b / "records", spec)
                self.assertEqual(loaded["path"], str(intended.resolve()))
                self.assertTrue(intended.exists())
                self.assertFalse(foreign.exists())
            finally:
                CAL.close_bound_directory(handle)

    def test_extension_output_uses_held_parent_after_ancestor_swap(self):
        schedule = CAL.tiny_smoke_schedule()
        spec = schedule["chains"][0]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            initial_dir = root / "initial"
            extension_a = root / "extension-a" / "records"
            extension_b = root / "extension-b" / "records"
            initial_dir.mkdir()
            extension_a.mkdir(parents=True)
            extension_b.mkdir(parents=True)
            alias = root / "extension-alias"
            alias.symlink_to(root / "extension-a", target_is_directory=True)

            gate_file = root / "gate.json"
            initial_auth_file = root / "initial-auth.json"
            extension_auth_file = root / "extension-auth.json"
            parent_file = root / "parent.json"
            for path, value in ((gate_file, b"gate"),
                                (initial_auth_file, b"initial-auth"),
                                (extension_auth_file, b"extension-auth"),
                                (parent_file, b"parent")):
                path.write_bytes(value)
            gate_snapshot = CAL.read_file_snapshot(gate_file)
            gate_bound = {**gate_snapshot,
                          "gate": {"source_hashes": {}, "data_hashes": {}}}
            initial_auth = CAL.read_file_snapshot(initial_auth_file)
            extension_auth = CAL.read_file_snapshot(extension_auth_file)
            parent = CAL.read_file_snapshot(parent_file)
            initial_handle = CAL.open_bound_directory(
                CAL.read_directory_binding(initial_dir))
            extension_handle = CAL.open_bound_directory(
                CAL.read_directory_binding(alias / "records"))
            try:
                initial = CAL.run_fresh_initial_chain(
                    self.adapter, spec, schedule, initial_handle,
                    "a" * 64, "b" * 64, initial_auth, gate_bound,
                    progress=False)
                CAL.validate_fresh_checkpoint_directory(
                    extension_handle, CAL.expected_schedule()["chains"],
                    extension=True)
                alias.unlink()
                alias.symlink_to(root / "extension-b",
                                 target_is_directory=True)
                extended = CAL.run_fresh_extended_chain(
                    self.adapter, initial, spec, schedule, extension_handle,
                    "a" * 64, "b" * 64, extension_auth, parent,
                    gate_bound, progress=False)
                intended = CAL.chain_checkpoint_path(
                    extension_a, spec, extension=True)
                foreign = CAL.chain_checkpoint_path(
                    extension_b, spec, extension=True)
                self.assertEqual(extended["path"], str(intended.resolve()))
                self.assertTrue(intended.exists())
                self.assertFalse(foreign.exists())
            finally:
                CAL.close_bound_directory(extension_handle)
                CAL.close_bound_directory(initial_handle)

    def test_output_inode_replacement_and_dynamic_inode_are_fail_closed(self):
        empty_gate = {"source_hashes": {}, "data_hashes": {}}
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            output = directory / "result.json"
            calls = 0

            def replace_on_second_dependency_check(_gate):
                nonlocal calls
                calls += 1
                if calls == 2:
                    output.unlink()
                    output.write_bytes(b"foreign-inode")
                    raise RuntimeError("forced output replacement")
                return {}

            with mock.patch.object(
                    CAL, "_dependency_snapshot",
                    side_effect=replace_on_second_dependency_check):
                with self.assertRaises(RuntimeError):
                    CAL.write_new_result(output, {"status": "must-not-pass"},
                                         empty_gate)
            self.assertEqual(output.read_bytes(), b"foreign-inode")

            dynamic = directory / "dynamic.json"
            dynamic.write_bytes(b"same")
            snapshot = CAL.read_file_snapshot(dynamic)
            replacement = directory / "replacement.json"
            replacement.write_bytes(b"same")
            os.replace(replacement, dynamic)
            with self.assertRaisesRegex(ValueError, "inode changed"):
                CAL._extra_snapshot({str(dynamic.resolve()):
                                     CAL.inode_binding(snapshot)})

    def test_result_output_ancestor_symlink_cannot_redirect_publication(self):
        """Regression for invalid v4 generic-result path handling.

        The output parent is A when publication starts.  Swapping the raw
        ancestor alias to B during the first dependency callback must either
        fail closed or continue publishing through a held A directory fd.  A
        successful publication in B is a provenance failure.
        """
        empty_gate = {"source_hashes": {}, "data_hashes": {}}
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            intended = root / "intended"
            foreign = root / "foreign"
            intended.mkdir()
            foreign.mkdir()
            alias = root / "output-alias"
            alias.symlink_to(intended, target_is_directory=True)
            output = alias / "result.json"
            calls = 0

            def swap_ancestor(extra):
                nonlocal calls
                calls += 1
                if calls == 1:
                    alias.unlink()
                    alias.symlink_to(foreign, target_is_directory=True)
                return {}

            rejected = False
            try:
                with mock.patch.object(CAL, "_extra_snapshot",
                                       side_effect=swap_ancestor):
                    CAL.write_new_result(
                        output, {"status": "must-not-be-redirected"},
                        empty_gate)
            except (ValueError, ArithmeticError, FileExistsError, OSError):
                rejected = True
            self.assertFalse((foreign / "result.json").exists(),
                             "final result was redirected into foreign parent")
            self.assertTrue(rejected or (intended / "result.json").exists())

    def test_resource_and_statistical_fail_values(self):
        self.assertEqual(CAL.validate_run_metrics(float(1).hex(), 1), (1.0, 1))
        for wall, rss in ((float(0).hex(), 1),
                          (float("inf").hex(), 1),
                          (float(1).hex(), True),
                          (float(1).hex(), 0)):
            with self.assertRaises(ValueError):
                CAL.validate_run_metrics(wall, rss)
        # A zero-SE discrepancy is infinite, so it cannot satisfy the <=12
        # one-extension gate even though +inf R-hat is extension-eligible.
        coverage = CAL.simultaneous_coverage(
            np.array([[0.0]]), np.array([[0.0]]), np.array([[1.0]]),
            np.array([[True]]), 6)
        self.assertFalse(coverage["pass"])
        self.assertEqual(coverage["max_standardized_discrepancy"],
                         float("inf"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
