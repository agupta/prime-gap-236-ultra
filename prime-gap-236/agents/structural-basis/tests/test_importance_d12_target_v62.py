#!/usr/bin/env python3

import importlib
import sys
import unittest
from fractions import Fraction
from pathlib import Path


HERE = Path(__file__).resolve()
REPO = HERE.parents[3]
CODE = HERE.parents[1] / "code"
sys.path.insert(0, str(CODE))
T = importlib.import_module("importance_d12_target_v62")


class D12TargetV62Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.package = T.exact_identity_package(REPO)

    def test_exact_identity_transform(self):
        identity = self.package["identity"]
        self.assertEqual(len(identity["labels"]), 96)
        self.assertEqual(len(identity["transformed_rational_vector"]), 96)
        old = [Fraction(value) for value in identity["old_rational_vector"]]
        self.assertEqual(old, [Fraction(int(i % 6 == 0))
                               for i in range(96)])
        self.assertTrue(identity["old_vector_is_16_tagged_constants"])
        self.assertEqual(T.sha256_canonical(identity),
                         self.package["identity_sha256"])

    def test_unmultiplied_baseline_and_normalizers(self):
        normalizers = self.package["normalizers"]
        self.assertEqual(sum(normalizers["i_weights"], Fraction(0)), 1)
        self.assertEqual(sum(normalizers["j_weights"], Fraction(0)), 1)
        self.assertEqual(normalizers["j_scale_to_numerator"], 48)
        self.assertGreater(normalizers["base_quotient"],
                           T.core.Decimal("0.9709"))
        self.assertLess(normalizers["base_quotient"],
                        T.core.Decimal("0.9711"))
        self.assertLess(
            normalizers["relative_errors"]["raw_i_to_grouped_baseline"],
            T.core.BASELINE_RELATIVE_TOLERANCE)

    def test_negative_transfer_is_not_target(self):
        negative = T.core.strict_metadata_json(
            (REPO / T.core.NEGATIVE_TRANSFER_RELATIVE).read_bytes(),
            "negative transfer")
        self.assertNotEqual(negative["input_sha256"],
                            T.EXPECTED_HASHES[T.core.D12_SOURCE_RELATIVE])
        self.assertLess(T.core.positive_decimal(
            negative["quotient"], "negative quotient"),
            T.core.NEGATIVE_TRANSFER_MAXIMUM_QUOTIENT)

    def test_gate_generation_is_blocked_before_independent_v62_pass(self):
        self.assertEqual(T.V62_AUDIT_ARTIFACT_HASHES, {})
        with self.assertRaises(ValueError):
            T.validate_v62_audit_artifacts()


if __name__ == "__main__":
    unittest.main()
