#!/usr/bin/env python3
"""Hostile plumbing tests for the staged fixed-vector dyadic checker."""

from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

import verify.check_c10_d12_fixed_vector_dyadic as driver
from verify.dyadic_interval import DyadicInterval


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "agents/exact-integrator/results/hb_c10_fullsimplex_noones_D12.json"
SOURCE_SHA = "719c656e6e45388273b4c27f51f7a18b33e9ed1abb5f883e6fcc5de5d6d64a87"


def write_json(path: Path, value) -> str:
    raw = (json.dumps(value, indent=2) + "\n").encode()
    path.write_bytes(raw)
    return hashlib.sha256(raw).hexdigest()


class FixedVectorDyadicDriverTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        DyadicInterval.configure(384, 96)

    def test_real_source_scaling_and_payload(self):
        raw, labels, primitive, denominator, content, payload = \
            driver.parse_input(SOURCE, SOURCE_SHA)
        self.assertEqual((len(labels), len(primitive)), (272, 272))
        self.assertEqual(denominator.bit_length(), 714)
        self.assertEqual(content, 1)
        self.assertEqual(payload,
                         "8ea54de0e3bb4d9f978fee80a6788c81d542a7d6839ed8c69e22a5374845fe4e")
        self.assertEqual(hashlib.sha256(raw).hexdigest(), SOURCE_SHA)

    def test_common_denominator_and_integer_content_are_reconstructed(self):
        value = json.loads(SOURCE.read_bytes())
        value["rational_vector"] = ["0"] * 272
        value["rational_vector"][0] = "6/35"
        value["rational_vector"][1] = "-9/14"
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "candidate.json"
            expected = write_json(path, value)
            _, _, primitive, denominator, content, _ = \
                driver.parse_input(path, expected)
        self.assertEqual((denominator, content), (70, 3))
        self.assertEqual(primitive[:2], [4, -15])
        self.assertTrue(all(x == 0 for x in primitive[2:]))

    def test_duplicate_json_and_noncanonical_fraction_fail(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "duplicate.json"
            raw = b'{"k":48,"k":48,"basis":[],"rational_vector":[]}'
            path.write_bytes(raw)
            with self.assertRaisesRegex(driver.FixedDyadicError, "malformed"):
                driver.parse_input(path, hashlib.sha256(raw).hexdigest())

            value = json.loads(SOURCE.read_bytes())
            value["rational_vector"][0] = "2/2"
            expected = write_json(path, value)
            with self.assertRaisesRegex(driver.FixedDyadicError, "non-canonical"):
                driver.parse_input(path, expected)

    def test_interval_roundtrip_and_endpoint_mutations(self):
        value = DyadicInterval(7, 13)
        raw = driver.interval_data(value)
        rebuilt = driver.interval_from_data(raw, "test")
        self.assertEqual((rebuilt.lo, rebuilt.hi), (value.lo, value.hi))
        mutations = []
        bad = dict(raw)
        bad["extra"] = 0
        mutations.append(bad)
        bad = dict(raw)
        bad["width_units"] = str(int(bad["width_units"]) + 1)
        mutations.append(bad)
        bad = dict(raw)
        bad["lower_fraction"] = "0"
        mutations.append(bad)
        bad = dict(raw)
        bad["lower_fraction"] = True
        bad["upper_fraction"] = True
        mutations.append(bad)
        for bad in mutations:
            with self.assertRaises(driver.FixedDyadicError):
                driver.interval_from_data(bad, "test")

    def test_factor_48_and_strict_lower_margin_gate(self):
        common = {"dependencies": {}, "audit_sentinel": "fixed",
                  "input_sha256": SOURCE_SHA}
        driver_sha = driver.sha256(Path(driver.__file__))
        denominator = DyadicInterval(2)
        stage = {
            "status": "c10-d12-fixed-vector-rigorous-dyadic-i-stage",
            **common,
            "workers": 1,
            "driver_sha256": driver_sha,
            "I": driver.interval_data(denominator),
            "I_strictly_positive": True,
            "i_orbit_groups": driver.EXPECTED_I_GROUPS,
            "i_faces": driver.EXPECTED_I_FACES,
            "i_wall_seconds": 1.0,
            "i_cpu_seconds": 1.0,
            "i_peak_rss_kib_linux": 1,
            "i_child_peak_rss_kib_linux": 1,
        }

        class FakeEvaluator:
            def __init__(self, j_value):
                self.j_value = j_value

            def evaluate_j(self, progress, workers):
                return (self.j_value, driver.EXPECTED_MARGINAL_COMPONENTS,
                        driver.EXPECTED_J_DOMAINS)

        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            stage_path = directory / "stage.json"
            stage_sha = write_json(stage_path, stage)
            with patch.object(driver, "dependency_snapshot", return_value={}):
                positive_result, positive = driver.run_j(
                    FakeEvaluator(DyadicInterval(1, 16)), common, SOURCE,
                    stage_path, stage_sha, directory / "positive.json", 1, False)
                equality_result, equality = driver.run_j(
                    FakeEvaluator(DyadicInterval(1, 24)), common, SOURCE,
                    stage_path, stage_sha, directory / "equality.json", 1, False)
        self.assertTrue(positive)
        self.assertTrue(positive_result["margin_strictly_positive"])
        self.assertFalse(equality)
        self.assertFalse(equality_result["margin_strictly_positive"])
        self.assertEqual(positive_result["acceptance_rule"],
                         "I.lo > 0 and (48*J-I).lo > 0")

    def test_boolean_worker_and_reverse_metadata_fail(self):
        common = {"dependencies": {}, "reverse_faces": True,
                  "input_sha256": SOURCE_SHA}
        stage = {
            "status": "c10-d12-fixed-vector-rigorous-dyadic-i-stage",
            **common,
            "workers": True,
            "driver_sha256": driver.sha256(Path(driver.__file__)),
            "I": driver.interval_data(DyadicInterval(1)),
            "I_strictly_positive": True,
            "i_orbit_groups": driver.EXPECTED_I_GROUPS,
            "i_faces": driver.EXPECTED_I_FACES,
            "i_wall_seconds": 1.0,
            "i_cpu_seconds": 1.0,
            "i_peak_rss_kib_linux": 1,
            "i_child_peak_rss_kib_linux": 1,
        }
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "stage.json"
            stage_sha = write_json(path, stage)
            with self.assertRaisesRegex(driver.FixedDyadicError,
                                        "completeness gate"):
                driver.load_stage(path, stage_sha, common, 1)

            stage["workers"] = 1
            stage["reverse_faces"] = 1
            stage_sha = write_json(path, stage)
            with self.assertRaisesRegex(driver.FixedDyadicError,
                                        "reverse_faces"):
                driver.load_stage(path, stage_sha, common, 1)

    def test_reverse_evaluator_reverses_each_complete_r_list(self):
        i_order = []
        fake_i = types.SimpleNamespace(
            reverse_faces=True,
            zero=0,
            support=types.SimpleNamespace(k=3, max_large=lambda: 3),
            square_residual_terms=lambda: {"group": 1},
            evaluate_i_r=lambda grouped, r, progress:
                (i_order.append(r) or r, 1),
        )
        i_value, groups, faces = \
            driver.OrderedGroupedEvaluator.evaluate_i(fake_i, False, 1)
        self.assertEqual(i_order, [3, 2, 1, 0])
        self.assertEqual((i_value, groups, faces), (6, 1, 4))

        j_order = []
        components = {((), 0, 0): 1}
        fake_j = types.SimpleNamespace(
            reverse_faces=True,
            zero=0,
            support=types.SimpleNamespace(k=3, max_large=lambda: 3),
            marginal_components=lambda: components,
            evaluate_j_r=lambda lrs, by_lr, r, progress:
                (j_order.append(r) or r, 1),
        )
        j_value, count, domains = \
            driver.OrderedGroupedEvaluator.evaluate_j(fake_j, False, 1)
        self.assertEqual(j_order, [2, 1, 0])
        self.assertEqual((j_value, count, domains), (3, 1, 3))

        with self.assertRaisesRegex(driver.FixedDyadicError, "one worker"):
            driver.OrderedGroupedEvaluator.evaluate_i(fake_i, False, 2)

    def test_j_invocation_replaces_stale_output_before_input_failure(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            stage = directory / "stage.json"
            stage.write_text("stale stage\n")
            output = directory / "output.json"
            output.write_text('{"certificate_passes":true}\n')
            argv = [
                str(Path(driver.__file__)), str(SOURCE),
                "--expect-input-sha256", "0" * 64,
                "--phase", "j", "--expected-stage-sha256", "1" * 64,
                "--stage", str(stage), "--output", str(output),
            ]
            with patch.object(sys, "argv", argv):
                with self.assertRaisesRegex(driver.FixedDyadicError,
                                            "input SHA mismatch"):
                    driver.main()
            sentinel = json.loads(output.read_bytes())
        self.assertEqual(sentinel["status"],
                         "incomplete-fixed-vector-dyadic-invocation")
        self.assertFalse(sentinel["theorem_ready"])

    def test_postwrite_input_mutation_replaces_result_by_failure(self):
        common = {"dependencies": {}, "input_sha256": SOURCE_SHA}
        driver_sha = driver.sha256(Path(driver.__file__))
        stage = {
            "status": "c10-d12-fixed-vector-rigorous-dyadic-i-stage",
            **common,
            "workers": 1,
            "driver_sha256": driver_sha,
            "I": driver.interval_data(DyadicInterval(2)),
            "I_strictly_positive": True,
            "i_orbit_groups": driver.EXPECTED_I_GROUPS,
            "i_faces": driver.EXPECTED_I_FACES,
            "i_wall_seconds": 1.0,
            "i_cpu_seconds": 1.0,
            "i_peak_rss_kib_linux": 1,
            "i_child_peak_rss_kib_linux": 1,
        }

        class FakeEvaluator:
            def evaluate_j(self, progress, workers):
                return (DyadicInterval(1, 16),
                        driver.EXPECTED_MARGINAL_COMPONENTS,
                        driver.EXPECTED_J_DOMAINS)

        real_atomic = driver.atomic_write
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            input_path = directory / "input.json"
            input_path.write_bytes(SOURCE.read_bytes())
            stage_path = directory / "stage.json"
            stage_sha = write_json(stage_path, stage)
            output_path = directory / "output.json"
            mutated = False

            def hostile_atomic(path, payload):
                nonlocal mutated
                real_atomic(path, payload)
                if Path(path) == output_path and not mutated:
                    input_path.write_bytes(b"mutated after result write")
                    mutated = True

            with patch.object(driver, "dependency_snapshot", return_value={}), \
                    patch.object(driver, "atomic_write", side_effect=hostile_atomic):
                with self.assertRaisesRegex(driver.FixedDyadicError,
                                            "input SHA mismatch"):
                    driver.run_j(FakeEvaluator(), common, input_path,
                                 stage_path, stage_sha, output_path, 1, False)
            failure = json.loads(output_path.read_bytes())
        self.assertEqual(failure["status"],
                         "failed-fixed-vector-dyadic-invocation")
        self.assertFalse(failure["theorem_ready"])


if __name__ == "__main__":
    unittest.main()
