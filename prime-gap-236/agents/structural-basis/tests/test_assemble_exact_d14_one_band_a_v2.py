#!/usr/bin/env python3
"""Tests for strict-v2 D19 provenance in the exact D14 A aggregate."""

from __future__ import annotations

from fractions import Fraction as Q
import importlib.util
from pathlib import Path
import sys
import unittest


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
SOURCE = REPO / (
    "agents/structural-basis/code/assemble_exact_d14_one_band_a_v2.py")


def load_source():
    spec = importlib.util.spec_from_file_location(
        "test_assemble_exact_d14_one_band_a_v2_source", SOURCE)
    if spec is None or spec.loader is None:
        raise ImportError(SOURCE)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


M = load_source()


class AssembleExactD14OneBandAV2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = M.build_aggregate()

    def test_strict_v2_provenance_and_exact_A(self):
        row = self.result
        self.assertEqual(row["status"],
                         "EXACT D14 ONE-BAND A AGGREGATE STRICT-V2 PASS")
        provenance = row["D19_inner_provenance"]
        self.assertEqual(provenance["checker_sha256"],
                         M.STRICT_D19_CHECKER_SHA256)
        self.assertEqual(provenance["result_sha256"],
                         M.STRICT_D19_RESULT_SHA256)
        self.assertEqual(provenance["test_sha256"],
                         M.STRICT_D19_TEST_SHA256)
        self.assertEqual(Q(row["exact_A_scaled"]),
                         10**76 * Q(row["exact_A_unscaled"]))
        self.assertTrue(row["provenance_repair"][
            "strict_D19_provenance_is_theorem_facing"])

    def test_static_hashes_and_determinism(self):
        self.assertEqual(M.B.sha256(M.BASE), M.BASE_SHA256)
        self.assertEqual(M.B.sha256(M.STRICT_D19_CHECKER),
                         M.STRICT_D19_CHECKER_SHA256)
        self.assertEqual(M.B.sha256(M.STRICT_D19_RESULT),
                         M.STRICT_D19_RESULT_SHA256)
        self.assertEqual(M.B.sha256(M.STRICT_D19_TEST),
                         M.STRICT_D19_TEST_SHA256)
        self.assertEqual(M.B.canonical_json(self.result),
                         M.B.canonical_json(M.build_aggregate()))
        self.assertFalse(self.result["b_launch_authorized"])


if __name__ == "__main__":
    unittest.main()
