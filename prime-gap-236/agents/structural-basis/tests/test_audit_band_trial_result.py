#!/usr/bin/env python3
"""Fail-closed tests for the near20 grouped-result auditor."""

import json
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
CODE = HERE.parent / "code"
ROOT = HERE.parents[2]
sys.path.insert(0, str(CODE))

from audit_band_trial_result import (COUNTS, GROUPED_SHA, INTEGRATOR_SHA,  # noqa: E402
                                     PARAMETERS, TRIAL_SHA,
                                     validate_result, validate_trial)


TRIAL = ROOT / "agents/structural-basis/results/c10_D12_h12_near_20pct_v3.json"
MANIFEST = ROOT / "agents/structural-basis/results/c10_D12_band_trials_manifest_v3.json"
SOURCE = ROOT / "agents/exact-integrator/results/hb_c10_fullsimplex_noones_D12.json"
BANDS = ROOT / "agents/structural-basis/results/c10_D12_degree_bands.json"


def synthetic_pair():
    result = {
        "status": "multiprecision-grouped-fixed-vector-discovery",
        "rigorous": False, "decimal_dps": 100,
        "input_json": str(TRIAL), "k": 48, "parameters": PARAMETERS,
        "basis_dimension": 272, "workers": 2,
        **COUNTS, "input_sha256": TRIAL_SHA,
        "i_seconds": 10.0, "j_seconds": 20.0, "total_seconds": 30.0,
        "peak_rss_kib": 100, "child_peak_rss_kib": 200,
        "peak_rss_note": "parent and child",
        "denominator_positive": True, "margin_positive": True,
        "denominator": "2", "j_value": "0.05", "numerator": "2.40",
        "quotient": "1.20", "quotient_decimal_display": 1.2,
        "margin": "0.40", "script_sha256": GROUPED_SHA,
        "integrator_sha256": INTEGRATOR_SHA,
    }
    stage = {
        "status": "grouped-fixed-vector-I-stage", "i_complete": True,
        "rigorous": False, "decimal_dps": 100, "input_json": str(TRIAL),
        "input_sha256": TRIAL_SHA, "script_sha256": GROUPED_SHA,
        "integrator_sha256": INTEGRATOR_SHA, "parameters": PARAMETERS,
        "i_orbit_groups": 1575, "i_faces": 312, "i_seconds": 10.0,
        "denominator_positive": True, "denominator": "2",
        "peak_rss_kib": 100, "child_peak_rss_kib": 200,
    }
    return result, stage


class AuditBandTrialResultTests(unittest.TestCase):
    def test_pinned_trial_preflight_reconstructs_exactly(self):
        trial, band_map, theta, vector = validate_trial(
            TRIAL.read_bytes(), MANIFEST.read_bytes(), str(SOURCE), str(BANDS))
        self.assertEqual(trial["trial"]["name"], "h12_near_20pct")
        self.assertEqual(len(theta), 20)
        self.assertEqual(len(vector), 272)
        self.assertEqual(vector, list(band_map.expand(theta)))

    def test_valid_synthetic_result_recomputes_all_scalars(self):
        result, stage = synthetic_pair()
        observed, _, values = validate_result(
            (json.dumps(result) + "\n").encode(),
            (json.dumps(stage) + "\n").encode(), str(TRIAL))
        self.assertTrue(observed["margin_positive"])
        self.assertEqual(str(values["quotient"]), "1.20")

    def test_material_scalar_and_provenance_corruption_fail(self):
        result, stage = synthetic_pair()
        result["numerator"] = "2.41"
        with self.assertRaisesRegex(ValueError, "N=48J"):
            validate_result((json.dumps(result) + "\n").encode(),
                            (json.dumps(stage) + "\n").encode(), str(TRIAL))
        result, stage = synthetic_pair()
        result["input_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "input/dimensions"):
            validate_result((json.dumps(result) + "\n").encode(),
                            (json.dumps(stage) + "\n").encode(), str(TRIAL))

    def test_trial_byte_mutation_fails_before_parsing(self):
        mutated = bytearray(TRIAL.read_bytes())
        mutated[-2] = ord(" ")
        with self.assertRaisesRegex(ValueError, "trial SHA"):
            validate_trial(bytes(mutated), MANIFEST.read_bytes(),
                           str(SOURCE), str(BANDS))


if __name__ == "__main__":
    unittest.main()
