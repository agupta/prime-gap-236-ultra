#!/usr/bin/env python3
"""Low-cost exact tests for the independent near20 line auditor."""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from fractions import Fraction as Q
from pathlib import Path
from unittest.mock import patch


HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import audit_near20_scalar_line_independent as audit  # noqa: E402


ROOT = HERE.parents[1]
TRIAL = ROOT / "agents/structural-basis/results/c10_D12_h12_near_20pct_v3.json"
RECOVERY = ROOT / \
    "agents/structural-basis/results/c10_D12_band_sparse_gradient_recovered_v2.json"


class Near20LineIndependentTests(unittest.TestCase):
    def test_strict_json_rejects_duplicate(self):
        with self.assertRaisesRegex(ValueError, "duplicate JSON key"):
            audit.strict_json(b'{"x":1,"x":2}', "mutation")

    def test_raw_projective_endpoint_recovers_quadratic(self):
        theta = [Q(2), Q(-1)]
        direction = [Q(3, 5), Q(7, 4)]
        t, scale = Q(2, 7), Q(11, 9)
        a_theta = [Q(5, 3), Q(-2, 5)]
        b_theta = [Q(7, 8), Q(4, 9)]
        a00, b00 = Q(13, 6), Q(17, 10)
        a01, b01 = audit.dot(direction, a_theta), audit.dot(direction, b_theta)
        a11, b11 = Q(19, 7), Q(-23, 12)
        y = [scale * (x + t * d) for x, d in zip(theta, direction)]
        rebuilt_direction = [(yy / scale - x) / t for x, yy in zip(theta, y)]
        self.assertEqual(rebuilt_direction, direction)
        ay = scale * scale * (a00 + 2 * t * a01 + t * t * a11)
        by = scale * scale * (b00 + 2 * t * b01 + t * t * b11)
        rebuilt_a11 = (ay / (scale * scale) - a00 - 2 * t * a01) / (t * t)
        rebuilt_b11 = (by / (scale * scale) - b00 - 2 * t * b01) / (t * t)
        self.assertEqual((rebuilt_a11, rebuilt_b11), (a11, b11))

    def test_actual_trial_derivative_and_rounding_defect(self):
        trial = json.loads(TRIAL.read_bytes())
        recovery = json.loads(RECOVERY.read_bytes())
        theta = list(map(Q, recovery["theta"]))
        endpoint = list(map(Q, trial["compressed_theta"]))
        a_theta = list(map(Q, recovery["a_theta_exact_fraction_half"]))
        b_theta = list(map(Q, recovery["b_theta_exact_fraction_half"]))
        denominator = Q(recovery["denominator"])
        numerator = Q(recovery["numerator"])
        t = Q(trial["trial"]["exact_step_t"])
        scale = Q(trial["trial"]["exact_H12_gauge_scale"])
        direction = [(y / scale - x) / t for x, y in zip(theta, endpoint)]
        displacement = [y - x for x, y in zip(theta, endpoint)]
        direct = 2 * (
            audit.dot(displacement, b_theta) * denominator -
            audit.dot(displacement, a_theta) * numerator) / denominator**2
        recorded = Q(trial["trial"]["normalized_trial_first_derivative_exact"])
        self.assertEqual(direct, recorded)
        raw = 2 * (
            audit.dot(direction, b_theta) * denominator -
            audit.dot(direction, a_theta) * numerator) / denominator**2
        defect = scale * t * raw - direct
        self.assertNotEqual(defect, 0)
        self.assertLess(abs(defect), max(abs(direct), Q(1)) / 10**50)

    def test_stationary_polynomial_is_derivative_numerator(self):
        a00, a01, a11 = Q(5), Q(-2), Q(3)
        b00, b01, b11 = Q(7), Q(4), Q(-1)
        coefficients = (
            b01 * a00 - a01 * b00,
            b11 * a00 - a11 * b00,
            b11 * a01 - a11 * b01,
        )
        for u in (Q(-3, 2), Q(0), Q(7, 5)):
            denominator = a00 + 2 * a01 * u + a11 * u * u
            numerator = b00 + 2 * b01 * u + b11 * u * u
            direct = ((b01 + b11 * u) * denominator -
                      (a01 + a11 * u) * numerator)
            polynomial = coefficients[0] + coefficients[1] * u + \
                coefficients[2] * u * u
            self.assertEqual(direct, polynomial)

    def test_postwrite_closure_mutation_rejects_owned_output(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            trusted = directory / "trusted"
            output = directory / "audit.json"
            trusted.write_bytes(b"pinned")
            original_fsync = os.fsync
            calls = 0

            def mutate_after_first_fsync(descriptor):
                nonlocal calls
                original_fsync(descriptor)
                calls += 1
                if calls == 1:
                    trusted.write_bytes(b"mutated")

            with patch.object(audit.os, "fsync", mutate_after_first_fsync):
                with self.assertRaisesRegex(ValueError, "trusted byte changed"):
                    audit.publish_new(
                        output, '{"status":"PASS"}\n',
                        {trusted.resolve(): b"pinned"})
            self.assertEqual(
                audit.strict_json(output.read_bytes(), "rejection"),
                {"status": "REJECTED-independent-near20-audit",
                 "rigorous": False})


if __name__ == "__main__":
    unittest.main()
