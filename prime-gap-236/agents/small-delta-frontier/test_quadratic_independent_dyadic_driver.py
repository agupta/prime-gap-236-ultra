#!/usr/bin/env python3
"""Fail-closed tests for the staged quadratic dyadic target driver."""

from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from fractions import Fraction
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from verify import check_c10_d12_quadratic_independent_dyadic as driver
from verify.dyadic_interval import DyadicInterval


class QuadraticIndependentDriverTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        DyadicInterval.configure(192, 64)

    def test_pinned_loader_reconstructs_both_primitive_scalings(self):
        terms, quadratic, quadratic_lcm, base_lcm = driver.load_scaled_inputs()
        self.assertEqual(len(terms), 272)
        self.assertEqual(len(quadratic.coefficients), 16)
        self.assertEqual(sum(value != 0 for row in quadratic.coefficients
                             for value in row), 93)
        self.assertEqual(base_lcm.bit_length(), 714)
        self.assertEqual(quadratic_lcm.bit_length(), 2310)
        self.assertEqual(driver.active_face_counts(), (16, 16))

    def test_interval_serialization_rejects_boolean_width_and_extra_field(self):
        encoded = driver.interval_data(DyadicInterval(7, 11))
        decoded = driver.interval_from_data(encoded, 192, "test")
        self.assertEqual((decoded.lo, decoded.hi),
                         (DyadicInterval(7, 11).lo,
                          DyadicInterval(7, 11).hi))
        self.assertTrue(decoded.contains(Fraction(7, 11)))
        malformed = dict(encoded)
        malformed["width_units"] = False
        with self.assertRaisesRegex(Exception, "width mismatch"):
            driver.interval_from_data(malformed, 192, "test")
        malformed = dict(encoded)
        malformed["extra"] = 0
        with self.assertRaisesRegex(Exception, "malformed staged"):
            driver.interval_from_data(malformed, 192, "test")

    def test_path_collisions_and_unbound_j_stage_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "out.json"
            args = SimpleNamespace(
                precision=192, shadow_bits=64,
                stage=driver.SOURCE_PATH, output=output,
                phase="i", expected_stage_sha256=None)
            with self.assertRaisesRegex(Exception, "collides"):
                driver.validate_options(args)
            args.stage = Path(directory) / "stage.json"
            args.output = args.stage
            with self.assertRaisesRegex(Exception, "must differ"):
                driver.validate_options(args)
            args.output = output
            args.phase = "j"
            with self.assertRaisesRegex(Exception, "requires"):
                driver.validate_options(args)

    def test_factor_48_and_only_strict_lower_margin_accepts(self):
        common = {"precision_bits": 192, "dependency_sha256": {}}
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            stage_path = directory / "stage.json"
            output_path = directory / "output.json"
            stage = {
                "status": "c10-d12-quadratic-independent-dyadic-i-stage",
                **common,
                "driver_sha256": driver.sha256(Path(driver.__file__)),
                "I": driver.interval_data(DyadicInterval(10)),
                "I_strictly_positive": True,
                "i_wall_seconds": 0.0,
                "i_peak_rss_kib_linux": 1,
            }
            stage_path.write_text(
                json.dumps(stage, indent=2, sort_keys=True) + "\n")
            stage_sha = hashlib.sha256(stage_path.read_bytes()).hexdigest()
            with patch.object(driver, "compute_j_quadratic_tagged",
                              return_value=DyadicInterval(1, 4)), \
                    patch.object(driver, "dependency_snapshot", return_value={}), \
                    patch.object(driver, "reread_inputs", return_value=None):
                payload, positive = driver.run_j(
                    {}, None, common, stage_path, stage_sha,
                    output_path, False)
            self.assertTrue(positive)
            self.assertEqual(payload["M2"]["lower_fraction"], "12")
            self.assertTrue(payload["margin_strictly_positive"])
            self.assertEqual(payload["acceptance_rule"],
                             "I.lo > 0 and (48*J-I).lo > 0")

            with patch.object(driver, "compute_j_quadratic_tagged",
                              return_value=DyadicInterval(5, 24)), \
                    patch.object(driver, "dependency_snapshot", return_value={}), \
                    patch.object(driver, "reread_inputs", return_value=None):
                payload, positive = driver.run_j(
                    {}, None, common, stage_path, stage_sha,
                    output_path, False)
            self.assertFalse(positive)  # margin is exactly zero, not > 0
            self.assertFalse(payload["margin_strictly_positive"])


if __name__ == "__main__":
    unittest.main()
