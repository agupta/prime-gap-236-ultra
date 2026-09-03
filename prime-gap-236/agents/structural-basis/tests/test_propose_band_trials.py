#!/usr/bin/env python3
"""Exact projective-step and provenance tests for rational band trials."""

import json
import sys
import tempfile
import unittest
from fractions import Fraction
from pathlib import Path

HERE = Path(__file__).resolve().parent
CODE = HERE.parent / "code"
sys.path.insert(0, str(CODE))

from band_operator import BandMap  # noqa: E402
from propose_band_trials import (RECOVERY_ARTIFACT_SHA,  # noqa: E402
                                  bind_written_trials,
                                  build_trials,
                                  projective_steps,
                                  rebind_trusted,
                                  recursive_keys,
                                  validate_recovery)


ROOT = HERE.parents[2]
RAW = ROOT / "agents/structural-basis/results/c10_D12_band_sparse_gradient_mp100.json"
RECOVERY = ROOT / "agents/structural-basis/results/c10_D12_band_sparse_gradient_recovered_v2.json"
SOURCE = ROOT / "agents/exact-integrator/results/hb_c10_fullsimplex_noones_D12.json"
BANDS = ROOT / "agents/structural-basis/results/c10_D12_degree_bands.json"


class ProposeBandTrialsTests(unittest.TestCase):
    def test_exact_projective_bracket_attains_target(self):
        ratios = [Fraction(-3), Fraction(-2)]
        near, pole, far, spread, c = projective_steps(
            ratios, 1, Fraction(1))
        self.assertEqual((near, pole, far, spread, c),
                         (Fraction(1, 3), Fraction(1, 2), Fraction(1),
                          Fraction(1), Fraction(2)))
        for step in (near, far):
            normalized = [(1 + step * value) /
                          (1 + step * ratios[1]) for value in ratios]
            self.assertEqual(max(abs(x - 1) for x in normalized), 1)

    def test_pinned_recovery_is_consumed_without_recorded_halves(self):
        recovery_bytes, raw_bytes = RECOVERY.read_bytes(), RAW.read_bytes()
        self.assertEqual(__import__("hashlib").sha256(
            recovery_bytes).hexdigest(), RECOVERY_ARTIFACT_SHA)
        raw, recovered = validate_recovery(
            recovery_bytes, raw_bytes, str(SOURCE), str(BANDS))
        self.assertEqual(recovered["a_theta"],
                         json.loads(recovery_bytes)[
                             "a_theta_exact_fraction_half"])
        self.assertNotEqual(raw["a_theta"], recovered["a_theta"])

    def test_recovery_mutation_is_rejected(self):
        recovery = json.loads(RECOVERY.read_bytes())
        recovery["grad_denominator"][0] = "0"
        mutated = (json.dumps(recovery) + "\n").encode()
        with self.assertRaisesRegex(ValueError, "recovery artifact SHA"):
            validate_recovery(mutated, RAW.read_bytes(), str(SOURCE), str(BANDS))

    def test_actual_trials_are_exact_band_expansions_without_form_claims(self):
        raw, recovered = validate_recovery(
            RECOVERY.read_bytes(), RAW.read_bytes(), str(SOURCE), str(BANDS))
        band_map = BandMap.from_source_and_bands(str(SOURCE), str(BANDS))
        diagnostics, trials = build_trials(raw, recovered, band_map, 230)
        targets = {
            "h12_near_5pct": Fraction(1, 20),
            "h12_near_10pct": Fraction(1, 10),
            "h12_near_20pct": Fraction(1, 5),
        }
        self.assertEqual([item["trial"]["name"] for item in trials],
                         list(targets))
        self.assertEqual(len(diagnostics["direction"]), 20)
        self.assertLess(Fraction(diagnostics[
            "theta_dot_residual_relative_to_numerator"]), Fraction(1, 10**50))
        for item in trials:
            detail = item["trial"]
            theta = [Fraction(x) for x in item["compressed_theta"]]
            expanded = [Fraction(x) for x in item["rational_vector"]]
            self.assertEqual(expanded, list(band_map.expand(theta)))
            self.assertEqual(theta[19], 1)
            self.assertEqual(item["parameters"], raw["parameters"])
            self.assertEqual(Fraction(
                detail["normalized_max_relative_coefficient_change"]),
                targets[detail["name"]])
            self.assertGreater(Fraction(
                detail["normalized_trial_first_derivative_exact"]), 0)
            keys = set(recursive_keys(item))
            self.assertTrue({"finite_form_value_claimed",
                             "fresh_scalar_reevaluation_required"} <= keys)
            self.assertFalse({"quotient", "denominator", "numerator"} & keys)

    def test_trusted_rebind_rejects_byte_mutation(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "trusted"
            path.write_bytes(b"before")
            expected = __import__("hashlib").sha256(b"before").hexdigest()
            rebind_trusted({path.resolve(): expected})
            path.write_bytes(b"after")
            with self.assertRaisesRegex(RuntimeError, "trusted trial input changed"):
                rebind_trusted({path.resolve(): expected})

    def test_manifest_binding_rejects_between_write_trial_mutation(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "trial.json"
            path.write_bytes(b"written trial")
            expected = __import__("hashlib").sha256(
                b"written trial").hexdigest()
            written = [{"name": "trial", "path": str(path),
                        "sha256": expected}]
            closure = {}
            bind_written_trials(written, closure)
            self.assertEqual(closure[path.resolve()], expected)
            path.write_bytes(b"concurrent mutation")
            with self.assertRaisesRegex(RuntimeError,
                                        "trusted trial input changed"):
                bind_written_trials(written, {})


if __name__ == "__main__":
    unittest.main()
