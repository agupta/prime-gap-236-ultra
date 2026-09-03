#!/usr/bin/env python3
"""Independent hostile tests for the fixed-vector dyadic driver.

The first two tests preserve counterexamples found against driver SHA
1dfa65ca and require the repaired driver to fail closed.  The final test is a
positive containment oracle independent of the target D12 traversal.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
import tempfile
import unittest
from fractions import Fraction as Q
from pathlib import Path
from unittest.mock import patch

import exact_integrator as ei
from dyadic_backend import install_dyadic
from grouped_fixed_vector import GroupedEvaluator, precompute_orbits
import verify.check_c10_d12_fixed_vector_dyadic as driver
from verify.dyadic_interval import DyadicInterval


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "agents/exact-integrator/results/hb_c10_fullsimplex_noones_D12.json"


def write_json(path: Path, value) -> str:
    raw = (json.dumps(value, indent=2) + "\n").encode()
    path.write_bytes(raw)
    return hashlib.sha256(raw).hexdigest()


def contains(interval, exact):
    scale = 1 << DyadicInterval.PRECISION
    return Q(interval.lo, scale) <= exact <= Q(interval.hi, scale)


class FixedDyadicHostileExtra(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        DyadicInterval.configure(384, 96)

    def test_boolean_fraction_endpoint_is_rejected(self):
        scale = 1 << DyadicInterval.PRECISION
        malformed = {
            "precision_bits": DyadicInterval.PRECISION,
            "lo_integer": str(scale), "hi_integer": str(scale),
            "lower_fraction": True, "upper_fraction": True,
            "width_units": "0",
        }
        with self.assertRaisesRegex(driver.FixedDyadicError,
                                    "must be a nonempty string"):
            driver.interval_from_data(malformed, "Boolean endpoint")

    def test_input_mutation_during_output_write_fails_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            candidate = directory / "candidate.json"
            shutil.copyfile(SOURCE, candidate)
            input_sha = hashlib.sha256(candidate.read_bytes()).hexdigest()
            common = {"dependencies": {}, "input_sha256": input_sha,
                      "audit_sentinel": "fixed"}
            denominator = DyadicInterval(2)
            stage = {
                "status": "c10-d12-fixed-vector-rigorous-dyadic-i-stage",
                **common, "workers": 1,
                "driver_sha256": driver.sha256(Path(driver.__file__)),
                "I": driver.interval_data(denominator),
                "I_strictly_positive": True,
                "i_orbit_groups": driver.EXPECTED_I_GROUPS,
                "i_faces": driver.EXPECTED_I_FACES,
                "i_wall_seconds": 1.0, "i_cpu_seconds": 1.0,
                "i_peak_rss_kib_linux": 1,
                "i_child_peak_rss_kib_linux": 1,
            }
            stage_path = directory / "stage.json"
            stage_sha = write_json(stage_path, stage)
            output = directory / "output.json"
            original_write = driver.atomic_write

            class Evaluator:
                @staticmethod
                def evaluate_j(progress, workers):
                    return (DyadicInterval(1, 16),
                            driver.EXPECTED_MARGINAL_COMPONENTS,
                            driver.EXPECTED_J_DOMAINS)

            def mutate_then_write(path, payload):
                candidate.write_bytes(candidate.read_bytes() + b"\n")
                original_write(path, payload)

            with patch.object(driver, "dependency_snapshot", return_value={}), \
                    patch.object(driver, "atomic_write", mutate_then_write):
                with self.assertRaisesRegex(driver.FixedDyadicError,
                                            "input SHA mismatch"):
                    driver.run_j(Evaluator(), common, candidate, stage_path,
                                 stage_sha, output, 1, False)
            self.assertEqual(json.loads(output.read_bytes())["status"],
                             "failed-fixed-vector-dyadic-invocation")
            self.assertNotEqual(hashlib.sha256(candidate.read_bytes()).hexdigest(),
                                input_sha)

    def test_signed_low_k_forward_reverse_enclose_fraction_oracle(self):
        labels = [(0, ()), (1, ()), (2, ()), (0, (2,))]
        coefficients = [Q(1), Q(-2), Q(3), Q(-1)]
        parameters = (Q(3, 5), Q(1, 10), Q(1, 2),
                      Q(1, 2), Q(1, 2), Q(1, 2))
        exact_support = ei.OneStratumSupport(2, *parameters)
        exact_evaluator = GroupedEvaluator(
            exact_support, labels, coefficients, Q)
        exact_i, groups, faces = exact_evaluator.evaluate_i(False, 1)
        exact_j, components, domains = exact_evaluator.evaluate_j(False, 1)
        self.assertEqual((groups, faces, components, domains), (4, 15, 5, 31))

        scalar = install_dyadic(precompute_orbits(labels, 2), 384, 96)
        dyadic_support = ei.OneStratumSupport(
            2, *(scalar(x.numerator, x.denominator) for x in parameters))
        for reverse in (False, True):
            evaluator = driver.OrderedGroupedEvaluator(
                dyadic_support, labels, [scalar(x) for x in coefficients],
                scalar, reverse_faces=reverse)
            interval_i, _, _ = evaluator.evaluate_i(False, 1)
            interval_j, _, _ = evaluator.evaluate_j(False, 1)
            self.assertTrue(contains(interval_i, exact_i))
            self.assertTrue(contains(interval_j, exact_j))


if __name__ == "__main__":
    unittest.main()
