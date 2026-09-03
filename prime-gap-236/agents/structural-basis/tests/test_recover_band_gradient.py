#!/usr/bin/env python3
"""Hostile byte-integrity tests for rejected-gradient recovery."""

import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
CODE = HERE.parent / "code"
sys.path.insert(0, str(CODE))

from recover_band_gradient import (EXPECTED_MISMATCHES, RAW_SHA, sha,  # noqa: E402
                                   require_distinct_output, validate_rejected)


ROOT = HERE.parents[2]
RAW = ROOT / "agents/structural-basis/results/c10_D12_band_sparse_gradient_mp100.json"
SOURCE = ROOT / "agents/exact-integrator/results/hb_c10_fullsimplex_noones_D12.json"
BANDS = ROOT / "agents/structural-basis/results/c10_D12_degree_bands.json"


class RecoverBandGradientTests(unittest.TestCase):
    def test_actual_rejected_artifact_recovers_only_exact_halves(self):
        raw_bytes = RAW.read_bytes()
        self.assertEqual(sha(raw_bytes), RAW_SHA)
        raw, recovered, evidence = validate_rejected(
            raw_bytes, str(SOURCE), str(BANDS))
        self.assertEqual({key: {row["index"] for row in rows}
                          for key, rows in evidence.items()}, EXPECTED_MISMATCHES)
        from fractions import Fraction
        for recovered_key, gradient_key in (
                ("a_theta", "grad_denominator"),
                ("b_theta", "grad_numerator")):
            self.assertEqual([Fraction(x) for x in recovered[recovered_key]],
                             [Fraction(x) / 2 for x in raw[gradient_key]])

    def test_materially_corrupted_gradient_is_rejected_by_byte_pin(self):
        raw = json.loads(RAW.read_bytes())
        raw["grad_denominator"][0] = str(
            __import__("fractions").Fraction(raw["grad_denominator"][0]) + 1)
        corrupted = (json.dumps(raw, sort_keys=True) + "\n").encode()
        with self.assertRaisesRegex(ValueError, "raw artifact SHA"):
            validate_rejected(corrupted, str(SOURCE), str(BANDS))

    def test_output_alias_is_rejected_on_harmless_temp_standins(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            trusted = [root / "raw.json", root / "dependency.py",
                       root / "baseline.json"]
            for path in trusted:
                path.write_text("standin\n")
            for path in trusted:
                with self.subTest(path=path.name):
                    with self.assertRaisesRegex(ValueError, "output aliases"):
                        require_distinct_output(path, trusted)
            require_distinct_output(root / "safe-output.json", trusted)


if __name__ == "__main__":
    unittest.main()
