#!/usr/bin/env python3
"""Exact algebra regression for the I-only projected-line gate."""

import json
import sys
import unittest
from fractions import Fraction
from pathlib import Path

HERE = Path(__file__).resolve().parent
CODE = HERE.parent / "code"
ROOT = HERE.parents[2]
sys.path.insert(0, str(CODE))

from compute_band_line_threshold import (STAGE_SHA,  # noqa: E402
                                         threshold_from_endpoint_denominator)


ARTIFACT = ROOT / \
    "agents/structural-basis/results/c10_D12_h12_near20_line_threshold_from_I.json"


class BandLineThresholdTests(unittest.TestCase):
    def test_exact_determinant_threshold(self):
        # D(0)=1, N(0)=9/10; linear D,N coefficients 0,2/5;
        # endpoint D=2.  The margin-matrix determinant vanishes at q_y=19/20.
        observed = threshold_from_endpoint_denominator(
            Fraction(1), Fraction(9, 10), Fraction(0), Fraction(2, 5),
            Fraction(2))
        self.assertEqual(observed["base_margin"], Fraction(-1, 10))
        self.assertEqual(observed["quadratic_margin_threshold"],
                         Fraction(-2, 5))
        self.assertEqual(observed["endpoint_quotient_threshold"],
                         Fraction(19, 20))

    def test_frozen_artifact_uses_no_trial_numerator(self):
        result = json.loads(ARTIFACT.read_bytes())
        self.assertEqual(result["status"],
                         "near20-line-threshold-from-I-stage-discovery")
        self.assertEqual(result["i_stage_sha256"], STAGE_SHA)
        self.assertIs(result["trial_numerator_used"], False)
        self.assertIs(result["no_projected_sign_inferred"], True)
        self.assertEqual(
            result["endpoint_quotient_threshold_decimal"],
            "0.97847852790172937299688253020565949738918417351307213338994257959703425275919289")


if __name__ == "__main__":
    unittest.main()
