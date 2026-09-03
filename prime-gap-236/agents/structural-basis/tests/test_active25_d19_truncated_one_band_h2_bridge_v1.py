#!/usr/bin/env python3

from fractions import Fraction as Q
import importlib.util
from pathlib import Path
import sys
import unittest


TARGET = (Path(__file__).resolve().parents[1] / "code" /
          "active25_d19_truncated_one_band_h2_bridge_v1.py")
SPEC = importlib.util.spec_from_file_location(
    "active25_d19_truncated_one_band_h2_bridge_v1", TARGET)
if SPEC is None or SPEC.loader is None:
    raise ImportError(TARGET)
M = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = M
SPEC.loader.exec_module(M)


class D19TruncatedOneBandH2BridgeTest(unittest.TestCase):
    def test_vector_and_cache_provenance(self):
        row, direct, basis, vector, inner_i, inner_48j = M.load_d19()
        self.assertEqual(len(basis), 568)
        self.assertEqual(len(vector), 568)
        self.assertEqual(max(a + sum(lam) for a, lam in basis), 19)
        self.assertEqual(Q(direct["exact_normalized_deficit"]),
                         (inner_i - inner_48j) / inner_i)
        self.assertIs(row["cache_entries_independently_reconstructed"], False)
        self.assertIs(direct["cache_read"], False)
        self.assertIs(direct["serialized_matrix_entries_read"], False)

    def test_generic_marginal_inventory(self):
        one_band = M.load("d19_test_geometry", M.ONE_BAND,
                          M.ONE_BAND_SHA256)
        bridge = one_band.configure_engine()
        core = bridge.load("d19_test_core", bridge.CORE, bridge.CORE_SHA256)
        bridge.configure(core, one_band.GEOMETRY)
        _, _, basis, vector, _, _ = M.load_d19()
        inner = core.ResidualD18(
            basis, vector, center=core.ALPHA1, dilation=1)
        marginal = M.GenericMarginal(
            core, basis, vector, inner.scale, M.EXPECTED_DIMENSION)
        self.assertEqual(marginal.max_residual, 20)
        self.assertEqual(len(marginal.orbits.partitions), 97)

    def test_cli_has_no_resume_or_exact_target(self):
        text = TARGET.read_text()
        self.assertNotIn("attempt_001", text)
        self.assertNotIn("--resume", text)
        self.assertNotIn("--run", text)
        self.assertIn("launch_authorized\"] = False", text)


if __name__ == "__main__":
    unittest.main()
