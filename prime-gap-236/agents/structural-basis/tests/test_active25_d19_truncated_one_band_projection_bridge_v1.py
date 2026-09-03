#!/usr/bin/env python3

import importlib.util
from pathlib import Path
import sys
import unittest

import numpy as np


TARGET = (Path(__file__).resolve().parents[1] / "code" /
          "active25_d19_truncated_one_band_projection_bridge_v1.py")
SPEC = importlib.util.spec_from_file_location(
    "active25_d19_truncated_one_band_projection_bridge_v1", TARGET)
if SPEC is None or SPEC.loader is None:
    raise ImportError(TARGET)
M = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = M
SPEC.loader.exec_module(M)


class D19TruncatedOneBandProjectionBridgeTest(unittest.TestCase):
    def test_base_pins(self):
        self.assertEqual(M.sha256(M.D19_BRIDGE), M.D19_BRIDGE_SHA256)
        self.assertEqual(M.sha256(M.D19_BRIDGE_TEST),
                         M.D19_BRIDGE_TEST_SHA256)

    def test_projection_summary_literal(self):
        a = np.asarray([[1, 1], [3, 3]], dtype=np.longdouble)
        b = np.asarray([[2, 2], [4, 4]], dtype=np.longdouble)
        row = M.projection_summary(a, b, 2)
        self.assertAlmostEqual(row["A_over_inner_I"], 4)
        self.assertAlmostEqual(row["b_over_inner_I"], 6)
        self.assertAlmostEqual(
            row["projected_energy_over_inner_I"], 9)
        self.assertEqual(len(row["per_chain_A_over_inner_I"]), 2)

    def test_rank_prune_and_normalized_solve(self):
        a = np.asarray([[1, 1, 0], [1, 1, 0], [0, 0, 2]],
                       dtype=np.longdouble)
        b = np.asarray([1, 1, 2], dtype=np.longdouble)
        kept = M.greedy_prune(a, M.RANK_RELATIVE_CUTOFF)
        self.assertEqual(kept, [0, 2])
        coefficients, rank, _, _ = M.normalized_solve(
            a[np.ix_(kept, kept)], b[kept], M.RANK_RELATIVE_CUTOFF)
        self.assertEqual(rank, 2)
        self.assertAlmostEqual(float(b[kept] @ coefficients), 3)

    def test_cli_has_no_resume_or_exact_target(self):
        text = TARGET.read_text()
        self.assertNotIn("attempt_001", text)
        self.assertNotIn("--resume", text)
        self.assertNotIn("--run", text)
        self.assertIn("launch_authorized\"] = False", text)


if __name__ == "__main__":
    unittest.main()
