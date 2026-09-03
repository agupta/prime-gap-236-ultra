#!/usr/bin/env python3

"""Hostile unit/smoke tests for the frozen D4 calibration driver.

The tests deliberately run only eight retained samples per selected chain.
They never invoke the 128-chain production schedule.
"""

import copy
import importlib
import json
import math
import os
import random
import sys
import tempfile
import types
import unittest
from decimal import Decimal
from fractions import Fraction
from pathlib import Path
from unittest import mock

import numpy as np


HERE = Path(__file__).resolve()
CODE = HERE.parents[1] / "code"
sys.path.insert(0, str(CODE))
MOD = importlib.import_module("importance_d4_calibration")
DENSITY = importlib.import_module("importance_density")
ORACLE = importlib.import_module("importance_oracle")
POINT = importlib.import_module("importance_point_eval")
WEIGHTS = importlib.import_module("importance_stratum_weights")
EXACT_RESULTS = HERE.parents[2] / "exact-integrator" / "results"
PARAMETERS = EXACT_RESULTS / "c10_stratum_quadratic_cappedopt_D4_exact.json"
D4 = EXACT_RESULTS / "c10_capped_D4_decimal55_vector_input.json"
GATE = HERE.parents[1] / "results" / "importance_d4_calibration_gate_v5.json"


class ImportanceD4CalibrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.adapter = DENSITY.C10ImportanceDensity(D4, PARAMETERS)

    def test_frozen_schedule_chain_table_and_structural_masks(self):
        schedule = MOD.expected_schedule()
        self.assertTrue(MOD.validate_schedule(schedule))
        table = schedule["chains"]
        identities = [(row["target"], row["stratum"], row["replicate"])
                      for row in table]
        seeds = [(row["initial_seed"], row["transition_seed"])
                 for row in table]
        self.assertEqual(len(table), 128)
        self.assertEqual(len(set(identities)), 128)
        self.assertEqual(len(set(sum(([a, b] for a, b in seeds), []))), 256)
        self.assertEqual(table[0], {
            "target": "I", "stratum": 0, "replicate": 0,
            "initial_seed": 2364800000, "transition_seed": 2364800001})
        self.assertEqual(table[-1], {
            "target": "J", "stratum": 15, "replicate": 3,
            "initial_seed": 2365815006, "transition_seed": 2365815007})
        i_mask, j_mask = MOD.structural_masks()
        self.assertEqual(int(i_mask.sum()), 336)
        self.assertEqual(int(j_mask.sum()), 876)
        self.assertEqual(sum(len(MOD.exact_local_active_pairs("I", r))
                             for r in range(16)), 321)
        self.assertEqual(sum(len(MOD.exact_local_active_pairs("J", r))
                             for r in range(16)), 1158)
        self.assertEqual([len(MOD.diagnostic_moment_indices("I", r))
                          for r in range(16)], [5] + [20] * 15)
        self.assertEqual([len(MOD.diagnostic_moment_indices("J", r))
                          for r in range(16)], [46] + [79] * 14 + [21])
        malformed = copy.deepcopy(schedule)
        malformed["retained_samples"] += 1
        with self.assertRaises(ValueError):
            MOD.validate_schedule(malformed)

    def test_gate_rebinds_every_frozen_dependency(self):
        if not GATE.exists():
            self.skipTest("gate is emitted only after driver/test bytes freeze")
        bound = MOD.load_and_validate_gate(GATE)
        self.assertEqual(bound["gate"]["schedule"], MOD.expected_schedule())
        self.assertFalse(bound["gate"]["production_launch_authorized"])
        self.assertEqual(
            bound["gate"]["source_hashes"][str(
                MOD.HERE.relative_to(MOD.REPO_ROOT))],
            MOD.sha256_file(MOD.HERE))

    def test_adapter_bytes_must_equal_the_gate_snapshot(self):
        gate = {"data_hashes": {
            MOD.REQUIRED_DATA_PATHS[0]: MOD.sha256_file(PARAMETERS),
            MOD.REQUIRED_DATA_PATHS[1]: MOD.sha256_file(D4),
        }}
        self.assertTrue(MOD.validate_adapter_provenance(self.adapter, gate))
        swapped = copy.copy(self.adapter)
        swapped.vector_sha256 = "0" * 64
        with self.assertRaises(ValueError):
            MOD.validate_adapter_provenance(swapped, gate)
        swapped = copy.copy(self.adapter)
        swapped.parameter_sha256 = "f" * 64
        with self.assertRaises(ValueError):
            MOD.validate_adapter_provenance(swapped, gate)

    def test_weight_normalizers_bind_the_exact_48j_oracle(self):
        weights_path = EXACT_RESULTS / \
            "c10_stratum_linear_D4_decimal160_cut10.json"
        digest = MOD.sha256_file(weights_path)
        weights = WEIGHTS.load_stratum_weights(
            weights_path, digest, prefix="baseline_",
            j_scale_to_numerator=1)
        oracle = ORACLE.load_exact_expectation_oracle(PARAMETERS)
        gate = {"data_hashes": {MOD.REQUIRED_DATA_PATHS[2]: digest}}
        self.assertTrue(MOD.validate_weight_provenance(
            weights, oracle, gate))
        wrong_factor = dict(weights)
        wrong_factor["j_scale_to_numerator"] = 48
        with self.assertRaises(ValueError):
            MOD.validate_weight_provenance(wrong_factor, oracle, gate)
        wrong_numerator = dict(weights)
        wrong_numerator["numerator"] /= 48
        with self.assertRaises(ArithmeticError):
            MOD.validate_weight_provenance(wrong_numerator, oracle, gate)
    def test_actual_tiny_i_and_j_chains_validate_and_corruption_rejects(self):
        schedule = MOD.tiny_smoke_schedule()
        self.assertTrue(MOD.validate_schedule(schedule, production=False))
        specs = [MOD.expected_chain_table()[0],
                 MOD.expected_chain_table()[64 + 15 * 4]]
        records = [MOD.run_one_chain(self.adapter, spec, schedule)
                   for spec in specs]
        for spec, record in zip(specs, records):
            self.assertTrue(MOD.validate_chain_record(
                record, spec, schedule, adapter=self.adapter))

        bad = copy.deepcopy(records[0])
        bad["raw_sum"][0] = float(1e6).hex()
        with self.assertRaises(ArithmeticError):
            MOD.validate_chain_record(
                bad, specs[0], schedule, adapter=self.adapter)
        bad = copy.deepcopy(records[1])
        bad["batch_z_means"][0] = float(-0.1).hex()
        with self.assertRaises(ArithmeticError):
            MOD.validate_chain_record(
                bad, specs[1], schedule, adapter=self.adapter)
        bad = copy.deepcopy(records[0])
        bad["acceptance"]["retained"]["physical-slack"]["attempted"] += 1
        with self.assertRaises(ValueError):
            MOD.validate_chain_record(
                bad, specs[0], schedule, adapter=self.adapter)
        # The fifth hostile-audit witness: raw second moments cannot be
        # changed independently of their retained per-batch counterparts.
        bad = copy.deepcopy(records[0])
        bad["raw_second_sum"][1] = float(7.2).hex()
        with self.assertRaisesRegex(ArithmeticError,
                                    "batch second means"):
            MOD.validate_chain_record(
                bad, specs[0], schedule, adapter=self.adapter)
        bad = copy.deepcopy(records[0])
        bad["batch_upper_second_means"][0][1] = float(0.9).hex()
        with self.assertRaises(ArithmeticError):
            MOD.validate_chain_record(
                bad, specs[0], schedule, adapter=self.adapter)

    def test_observations_reject_out_of_stratum_feature_leaks(self):
        fake = types.SimpleNamespace(delta=0.1)
        fake.i_features = lambda _state: [1.0] + [0.0] * 5 + [1.0] + [0.0] * 89
        with self.assertRaisesRegex(ArithmeticError, "I feature leaked"):
            MOD._observation(fake, "I", 0, (0.0,) * 48)

        unit = [0.0] * 96
        unit[0] = math.sqrt(0.5)
        unit[12] = math.sqrt(0.5)
        envelope = types.SimpleNamespace(
            unit_marginals=tuple(unit), z=0.5, log_g=0.0)
        with mock.patch.object(MOD, "j_envelope_point", return_value=envelope):
            with self.assertRaisesRegex(ArithmeticError,
                                         "J marginal leaked"):
                MOD._observation(fake, "J", 0, (0.0,) * 47)
    def test_tiny_continuation_reuses_exact_state_and_rng(self):
        schedule = MOD.tiny_smoke_schedule()
        spec = MOD.expected_chain_table()[0]
        initial = MOD.run_one_chain(self.adapter, spec, schedule)
        extended = MOD.extend_one_chain(
            self.adapter, initial, spec, schedule)
        combined = MOD.extended_schedule(schedule)
        self.assertEqual(extended["sample_count"], 16)
        self.assertEqual(extended["batch_count"], 8)
        self.assertEqual(extended["batch_upper_means"][:4],
                         initial["batch_upper_means"])
        self.assertEqual(extended["batch_upper_second_means"][:4],
                         initial["batch_upper_second_means"])
        self.assertTrue(MOD.validate_chain_record(
            extended, spec, combined, adapter=self.adapter))
        # Replaying from identical state and PRNG bytes must be bitwise stable.
        replay = MOD.extend_one_chain(
            self.adapter, initial, spec, schedule)
        self.assertEqual(extended, replay)

    def test_checkpoint_roundtrip_binds_record_schedule_and_parent(self):
        schedule = MOD.tiny_smoke_schedule()
        spec = MOD.expected_chain_table()[0]
        record = MOD.run_one_chain(self.adapter, spec, schedule)
        gate = {"source_hashes": {}, "data_hashes": {}}
        payload = MOD.chain_checkpoint_payload(
            record, spec, "a" * 64, "b" * 64, "c" * 64, schedule)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "record.json"
            digest = MOD.write_new_result(path, payload, gate)
            loaded = MOD.load_chain_checkpoint(
                path, spec, "a" * 64, "b" * 64, "c" * 64, schedule,
                adapter=self.adapter)
            self.assertEqual(loaded["sha256"], digest)
            self.assertEqual(loaded["record"], record)
            malformed = copy.deepcopy(spec)
            malformed["transition_seed"] += 2
            with self.assertRaises(ValueError):
                MOD.load_chain_checkpoint(
                    path, malformed, "a" * 64, "b" * 64, "c" * 64,
                    schedule,
                    adapter=self.adapter)

    def test_authorization_is_one_snapshot_and_rebound_at_publication(self):
        gate_sha = "a" * 64
        driver_sha = "b" * 64
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            record_dir = directory / "records"
            record_dir.mkdir()
            extension_dir = directory / "extensions"
            extension_dir.mkdir()
            authorization = directory / "authorization.json"
            valid = {
                "status": "root-authorized-d4-calibration",
                "authorized": True, "gate_sha256": gate_sha,
                "driver_sha256": driver_sha, "mode": "production",
                "record_directory_binding":
                    MOD.read_directory_binding(record_dir)}
            authorization.write_text(json.dumps(valid, sort_keys=True))
            bound = MOD.validate_authorization(
                authorization, gate_sha, driver_sha, record_dir)
            self.assertEqual(bound["sha256"],
                             MOD.sha256_file(authorization))

            output = directory / "result.json"

            def mutate_after_initial_snapshot(_gate):
                authorization.write_text('{"authorized":false}')
                return {}

            with mock.patch.object(
                    MOD, "_dependency_snapshot",
                    side_effect=mutate_after_initial_snapshot):
                with self.assertRaises(ValueError):
                    MOD.write_new_result(
                        output, {"status": "must-reject"},
                        {"source_hashes": {}, "data_hashes": {}},
                        extra_hashes={bound["path"]: bound["sha256"]})
            self.assertEqual(output.read_bytes(),
                             b'{"status":"rejected-incomplete-calibration-output"}\n')

            parent_sha = "c" * 64
            extension = {
                "status": "root-authorized-d4-calibration-extension",
                "authorized": True, "gate_sha256": gate_sha,
                "driver_sha256": driver_sha, "mode": "extension",
                "parent_result_sha256": parent_sha,
                "extension_record_directory_binding":
                    MOD.read_directory_binding(extension_dir)}
            authorization.write_text(json.dumps(extension, sort_keys=True))
            extension_bound = MOD.validate_extension_authorization(
                authorization, gate_sha, driver_sha, parent_sha,
                extension_dir)
            authorization.write_text('{"authorized":false}')
            self.assertNotEqual(extension_bound["sha256"],
                                MOD.sha256_file(authorization))
            with self.assertRaises(ValueError):
                MOD.write_new_result(
                    directory / "extension.json", {"status": "must-reject"},
                    {"source_hashes": {}, "data_hashes": {}},
                    extra_hashes={extension_bound["path"]:
                                  extension_bound["sha256"]})

    def test_fresh_only_checkpoint_directory_rejects_any_preexisting_path(self):
        chains = MOD.expected_schedule()["chains"]
        with tempfile.TemporaryDirectory() as directory:
            record_dir = Path(directory) / "records"
            record_dir.mkdir()
            binding = MOD.read_directory_binding(record_dir)
            handle = MOD.open_bound_directory(binding)
            try:
                self.assertIs(
                    MOD.validate_fresh_checkpoint_directory(handle, chains),
                    handle)
                first = MOD.chain_checkpoint_path(record_dir, chains[0])
                first.write_bytes(b"forged-or-stale-checkpoint")
                with self.assertRaises(FileExistsError):
                    MOD.validate_fresh_checkpoint_directory(handle, chains)
                with mock.patch.object(
                        MOD, "run_one_chain",
                        side_effect=AssertionError("must not run")):
                    with self.assertRaises(FileExistsError):
                        MOD.run_fresh_initial_chain(
                            self.adapter, chains[0],
                            MOD.tiny_smoke_schedule(), handle,
                            "a" * 64, "b" * 64,
                            {"sha256": "c" * 64}, {"gate": {}},
                            progress=False)
            finally:
                MOD.close_bound_directory(handle)

    def test_ancestor_symlink_swap_cannot_redirect_checkpoint_openat(self):
        schedule = MOD.tiny_smoke_schedule()
        spec = MOD.expected_chain_table()[0]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            authorized = root / "authorized" / "records"
            foreign = root / "foreign" / "records"
            authorized.mkdir(parents=True)
            foreign.mkdir(parents=True)
            alias = root / "alias"
            alias.symlink_to(root / "authorized", target_is_directory=True)
            raw_record_dir = alias / "records"
            binding = MOD.read_directory_binding(raw_record_dir)
            handle = MOD.open_bound_directory(binding)
            gate_file = root / "gate.json"
            auth_file = root / "authorization.json"
            gate_file.write_bytes(b"gate-bytes")
            auth_file.write_bytes(b"authorization-bytes")
            gate_bound = {**MOD.public_binding(
                MOD.read_file_snapshot(gate_file)),
                "gate": {"source_hashes": {}, "data_hashes": {}}}
            authorization = MOD.public_binding(
                MOD.read_file_snapshot(auth_file))
            try:
                MOD.validate_fresh_checkpoint_directory(
                    handle, MOD.expected_schedule()["chains"])
                alias.unlink()
                alias.symlink_to(root / "foreign", target_is_directory=True)
                loaded = MOD.run_fresh_initial_chain(
                    self.adapter, spec, schedule, handle,
                    "a" * 64, "b" * 64, authorization, gate_bound,
                    progress=False)
                self.assertEqual(
                    loaded["path"],
                    str(MOD.chain_checkpoint_path(authorized, spec).resolve()))
                self.assertTrue(
                    MOD.chain_checkpoint_path(authorized, spec).exists())
                self.assertFalse(
                    MOD.chain_checkpoint_path(foreign, spec).exists())
            finally:
                MOD.close_bound_directory(handle)

    def test_extension_openat_and_parent_manifest_resist_alias_swap(self):
        schedule = MOD.tiny_smoke_schedule()
        spec = MOD.expected_chain_table()[0]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            initial_dir = root / "initial"
            initial_dir.mkdir()
            extension_a = root / "extension-a" / "records"
            extension_b = root / "extension-b" / "records"
            extension_a.mkdir(parents=True)
            extension_b.mkdir(parents=True)
            gate_file = root / "gate.json"
            initial_auth_file = root / "initial-authorization.json"
            extension_auth_file = root / "extension-authorization.json"
            parent_file = root / "parent.json"
            for path, data in ((gate_file, b"gate"),
                               (initial_auth_file, b"initial-auth"),
                               (extension_auth_file, b"extension-auth"),
                               (parent_file, b"parent")):
                path.write_bytes(data)
            gate_bound = {**MOD.public_binding(
                MOD.read_file_snapshot(gate_file)),
                "gate": {"source_hashes": {}, "data_hashes": {}}}
            initial_auth = MOD.public_binding(
                MOD.read_file_snapshot(initial_auth_file))
            extension_auth = MOD.public_binding(
                MOD.read_file_snapshot(extension_auth_file))
            parent = MOD.public_binding(MOD.read_file_snapshot(parent_file))
            initial_handle = MOD.open_bound_directory(
                MOD.read_directory_binding(initial_dir))
            extension_alias = root / "extension-alias"
            extension_alias.symlink_to(
                root / "extension-a", target_is_directory=True)
            extension_handle = MOD.open_bound_directory(
                MOD.read_directory_binding(extension_alias / "records"))
            try:
                initial = MOD.run_fresh_initial_chain(
                    self.adapter, spec, schedule, initial_handle,
                    "a" * 64, "b" * 64, initial_auth, gate_bound,
                    progress=False)
                MOD.validate_fresh_checkpoint_directory(
                    extension_handle, MOD.expected_schedule()["chains"],
                    extension=True)
                extension_alias.unlink()
                extension_alias.symlink_to(
                    root / "extension-b", target_is_directory=True)
                extended = MOD.run_fresh_extended_chain(
                    self.adapter, initial, spec, schedule, extension_handle,
                    "a" * 64, "b" * 64, extension_auth, parent,
                    gate_bound, progress=False)
                expected_a = MOD.chain_checkpoint_path(
                    extension_a, spec, extension=True)
                expected_b = MOD.chain_checkpoint_path(
                    extension_b, spec, extension=True)
                self.assertEqual(extended["path"], str(expected_a.resolve()))
                self.assertTrue(expected_a.exists())
                self.assertFalse(expected_b.exists())
            finally:
                MOD.close_bound_directory(extension_handle)
                MOD.close_bound_directory(initial_handle)

            # A parent manifest that pins A cannot be redirected by resolving
            # a raw ancestor alias after it has been swapped to B.
            parent_alias = root / "parent-alias"
            parent_alias.symlink_to(
                root / "extension-a", target_is_directory=True)
            bindings = []
            records = []
            for chain in MOD.expected_schedule()["chains"]:
                bindings.append({
                    "path": str(MOD.chain_checkpoint_path(
                        extension_a, chain).resolve()),
                    "sha256": "d" * 64, "device": 1, "inode": 1})
                records.append(dict(chain))
            fake_parent = {"raw": {
                "record_checkpoints": bindings, "records": records}}
            parent_alias.unlink()
            parent_alias.symlink_to(
                root / "extension-b", target_is_directory=True)
            with self.assertRaisesRegex(ValueError, "path/order"):
                MOD.validate_parent_checkpoint_manifest(
                    fake_parent, parent_alias / "records",
                    MOD.expected_schedule())

    def test_resource_metrics_reject_bool_zero_and_nonfinite(self):
        self.assertEqual(
            MOD.validate_run_metrics(float(1.25).hex(), 1234),
            (1.25, 1234))
        for wall, rss in ((float(0).hex(), 1), (float("inf").hex(), 1),
                          (float(1).hex(), True), (float(1).hex(), 0)):
            with self.assertRaises(ValueError):
                MOD.validate_run_metrics(wall, rss)

    def test_main_closes_registered_directory_handles_on_failure(self):
        handle = {"descriptor": 17}

        def fail_after_registering(open_directories):
            open_directories.append(handle)
            raise RuntimeError("forced failure after directory open")

        with mock.patch.object(MOD, "_main",
                               side_effect=fail_after_registering), \
                mock.patch.object(MOD, "close_bound_directory") as close:
            with self.assertRaisesRegex(RuntimeError, "forced failure"):
                MOD.main()
        close.assert_called_once_with(handle)

    def test_output_is_no_overwrite_and_foreign_replacement_is_preserved(self):
        gate = {"source_hashes": {}, "data_hashes": {}}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "result.json"
            path.write_bytes(b"preexisting")
            with self.assertRaises(FileExistsError):
                MOD.write_new_result(path, {"status": "x"}, gate)
            self.assertEqual(path.read_bytes(), b"preexisting")

            raced = Path(directory) / "raced.json"
            calls = 0

            def replace_on_second_rebind(_gate):
                nonlocal calls
                calls += 1
                if calls == 2:
                    os.unlink(raced)
                    raced.write_bytes(b"foreign-inode")
                    raise RuntimeError("forced dependency race")
                return {}

            with mock.patch.object(
                    MOD, "_dependency_snapshot",
                    side_effect=replace_on_second_rebind):
                with self.assertRaises(RuntimeError):
                    MOD.write_new_result(raced, {"status": "x"}, gate)
            self.assertEqual(raced.read_bytes(), b"foreign-inode")

            dependency = Path(directory) / "checkpoint.json"
            dependency.write_bytes(b"same-bytes")
            snapshot = MOD.read_file_snapshot(dependency)
            replacement = Path(directory) / "replacement.json"
            replacement.write_bytes(b"same-bytes")
            os.replace(replacement, dependency)
            with self.assertRaisesRegex(ValueError, "inode changed"):
                MOD._extra_snapshot({
                    snapshot["path"]: MOD.inode_binding(snapshot)})

            # The generic/final-result path also uses a held canonical parent
            # dirfd.  Swapping a raw ancestor alias after its first validation
            # cannot redirect a successful publication.
            output_a = Path(directory) / "output-a"
            output_b = Path(directory) / "output-b"
            output_a.mkdir()
            output_b.mkdir()
            alias = Path(directory) / "output-alias"
            alias.symlink_to(output_a, target_is_directory=True)
            calls = 0

            def swap_alias_on_first_extra(_extra):
                nonlocal calls
                calls += 1
                if calls == 1:
                    alias.unlink()
                    alias.symlink_to(output_b, target_is_directory=True)
                return {}

            with mock.patch.object(
                    MOD, "_extra_snapshot",
                    side_effect=swap_alias_on_first_extra):
                digest = MOD.write_new_result(
                    alias / "final.json", {"status": "held-parent"}, gate)
            self.assertEqual(
                digest, MOD.sha256_file(output_a / "final.json"))
            self.assertFalse((output_b / "final.json").exists())

    def test_nonfinite_rejection_diagnostic_has_strict_tag(self):
        encoded = MOD._json_safe({"bad": math.inf, "nan": math.nan})
        self.assertEqual(encoded["bad"], {
            "nonfinite_float": "positive-infinity"})
        self.assertEqual(encoded["nan"], {"nonfinite_float": "nan"})
        self.assertNotIn("Infinity", json.dumps(encoded))

    def test_exact_oracle_active_dimensions_and_roots(self):
        oracle = ORACLE.load_exact_expectation_oracle(PARAMETERS)
        self.assertTrue(MOD.validate_analytic_zero_se_proofs(oracle))
        exact_a = np.asarray([[float(x) for x in row]
                              for row in oracle["E_I"]])
        exact_b = np.asarray([[float(x) for x in row]
                              for row in oracle["E_J"]])
        for degree, expected in ((0, 16), (1, 47), (2, 93)):
            principal = ORACLE.principal_indices(range(16), degree)
            active = [position for position, index in enumerate(principal)
                      if oracle["E_I"][index][index] > 0]
            self.assertEqual(len(active), expected)
            result = MOD.largest_generalized_root(
                exact_a[np.ix_(principal, principal)],
                exact_b[np.ix_(principal, principal)],
                base_quotient=float(oracle["base_quotient"]),
                active_indices=active)
            self.assertEqual(result["rank"], expected)
            self.assertTrue(math.isfinite(result["root"]))

    def test_only_pointwise_constant_local_entries_are_whitelisted(self):
        branches = MOD.exact_c10_common_branch_presence()
        self.assertEqual([row["small"] for row in branches], [True] * 16)
        self.assertEqual([row["large"] for row in branches],
                         [True] * 15 + [False])
        self.assertGreater(16 * self.adapter.delta_exact,
                           self.adapter.beta_exact(16))
        self.assertLess(15 * self.adapter.delta_exact,
                        self.adapter.beta_exact(15))

        # Exercise the pointwise y_00=z identity along actual r=15 states.
        spec = MOD.expected_chain_table()[64 + 15 * 4]
        state = MOD.randomized_interior_start(
            self.adapter, "J", 15, spec["initial_seed"])
        rng = random.Random(spec["transition_seed"])
        for _ in range(40):
            envelope = MOD.j_envelope_point(self.adapter, state)
            self.assertIsNotNone(envelope)
            constants = [envelope.unit_marginals[6 * r]
                         for r in range(16)]
            self.assertEqual(sum(value != 0 for value in constants), 1)
            self.assertEqual(constants[15] * constants[15], envelope.z)
            step = MOD.conditional_metropolis_step(
                self.adapter, "J", 15, state, rng,
                density_power=0.75, slack_probability=0.5)
            state = step.result.state

        local = np.zeros((6, 6))
        se = np.ones_like(local)
        local[0, 0] = 1.0
        se[0, 0] = 0.0
        self.assertEqual(MOD.local_zero_se_failures(
            "J", 15, local, se), [])
        # Even a forged/stuck zero-mean neighboring observable must fail.
        se[0, 1] = se[1, 0] = 0.0
        self.assertEqual(MOD.local_zero_se_failures(
            "J", 15, local, se), [(0, 1)])

        # The local r=15 identity must not whitelist aggregate global J.
        exact = np.zeros((96, 96))
        global_se = np.ones((96, 96))
        mask = np.zeros((96, 96), dtype=bool)
        exact[90, 90] = 1.0
        global_se[90, 90] = 0.0
        mask[90, 90] = True
        self.assertEqual(MOD.global_zero_se_failures(
            exact, global_se, mask), [(90, 90)])

    def test_exact_witnesses_exhaust_all_local_j_constant_products(self):
        raw = json.loads(D4.read_bytes())
        basis = [(residual, tuple(partition))
                 for residual, partition in raw["basis"]]
        coefficients = [Fraction(value) for value in raw["rational_vector"]]
        channels = [(r, a, b) for r in range(16)
                    for a, b in ORACLE.CHANNEL_POWERS]
        required = set()
        for _, partition in basis:
            required.add(partition)
            for exponent in set(partition):
                reduced = list(partition)
                reduced.remove(exponent)
                required.add(tuple(reduced))
        evaluator = POINT.MonomialSymmetricPointEvaluator(required)
        alpha = Fraction(79247, 300000)
        eta = Fraction(76247, 300000)
        delta = Fraction(1, 100)

        def beta(r):
            return Fraction(3, 20) if r in (1, 2) else Fraction(97, 625)

        for r in range(16):
            ratios = []
            reserve = (min(beta(r) - r * delta, eta - r * delta)
                       if r else Fraction(0))
            large_fractions = ([Fraction(0)] if r == 0 else
                               [Fraction(1, 6), Fraction(1, 4),
                                Fraction(1, 3)])
            for fraction in large_fractions:
                large = ([delta + reserve * fraction / r] * r if r else [])
                for small_total in (Fraction(0), Fraction(1, 1000),
                                    Fraction(1, 250)):
                    small = [small_total] + [Fraction(0)] * (46 - r)
                    common = large + small
                    marginals = POINT.marginal_multiplier_vector(
                        common, basis, coefficients, channels,
                        alpha, eta, delta, beta, normalize_powers=True,
                        evaluator=evaluator)
                    m0 = sum(marginals[6 * s] for s in range(16))
                    self.assertNotEqual(m0, 0)
                    local = [marginals[6 * r + i] / m0 for i in range(6)]
                    if r < 15:
                        local.extend(marginals[6 * (r + 1) + i] / m0
                                     for i in range(6))
                    ratios.append(local)
            nonzero_products = []
            constant_nonzero_products = []
            for i, j in MOD.upper_pairs(len(ratios[0])):
                values = [row[i] * row[j] for row in ratios]
                if any(values):
                    nonzero_products.append((i, j))
                    if len(set(values)) == 1:
                        constant_nonzero_products.append(
                            (i, j, values[0]))
            expected_count = 45 if r == 0 else 21 if r == 15 else 78
            self.assertEqual(len(nonzero_products), expected_count)
            self.assertEqual(
                constant_nonzero_products,
                [(0, 0, Fraction(1))] if r == 15 else [])

    def test_all_128_tiny_records_reach_fail_closed_analysis(self):
        schedule = MOD.tiny_smoke_schedule()
        records = [MOD.run_one_chain(self.adapter, spec, schedule)
                   for spec in schedule["chains"]]
        oracle = ORACLE.load_exact_expectation_oracle(PARAMETERS)
        # The tiny eight-sample run is intentionally far too short for the
        # frozen diagnostics, but it exercises every I/J stratum and the
        # complete grouping/reconstruction path without becoming a run.
        weights = {
            "i_weights": tuple(Decimal(1) / 16 for _ in range(16)),
            "j_weights": tuple(Decimal(1) / 16 for _ in range(16)),
        }
        analysis, failure = MOD.capture_analysis(
            records, oracle, weights, schedule, adapter=self.adapter)
        self.assertIsNone(analysis)
        self.assertEqual(failure["exception_type"], "ArithmeticError")
        self.assertIn("rank deficient", failure["message"])


if __name__ == "__main__":
    unittest.main()
