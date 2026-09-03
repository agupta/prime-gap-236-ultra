#!/usr/bin/env python3

from __future__ import annotations

from fractions import Fraction as Q
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest


SOURCE = (Path(__file__).resolve().parents[1] /
          "code/wide_frontier_r10_d16_outer_b4_v1.py")
SPEC = importlib.util.spec_from_file_location("frontier_r10_b4_tested", SOURCE)
M = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = M
SPEC.loader.exec_module(M)


class FrontierR10B4Tests(unittest.TestCase):
    def test_schedule_and_active_inventory(self):
        self.assertEqual(M.validate_schedule(), tuple(range(23)))
        self.assertEqual(M.SCHEDULE[0], Q(13, 125))
        self.assertEqual(M.SCHEDULE[8], Q(1011, 6250))
        self.assertEqual(M.SCHEDULE[9:], (Q(83, 500),) * 14)
        self.assertLessEqual(22 * M.DELTA, M.SCHEDULE[21])
        self.assertGreater(23 * M.DELTA, M.SCHEDULE[22])

    def test_finite_space_inventory_and_base_pin(self):
        self.assertEqual(M.BASIS, tuple(M.P.ei.even_basis(4)))
        self.assertEqual(len(M.BASIS), 10)
        base = M.load_base()
        self.assertEqual(len(base["basis"]), 307)
        self.assertEqual(base["numerator"] / base["denominator"],
                         base["quotient"])
        self.assertEqual(M.sha256(base["bytes"]),
                         M.PINNED_CERTIFICATE_SHA256)

    def test_low_k_literal_factor_and_symmetry(self):
        result = M.low_k_regression()
        self.assertEqual(result["D4_kJ"], str(2 * Q(result["D4_shell_J"])))
        self.assertGreater(Q(result["D4_shell_J"]), 0)

    def test_transpose_shell_polarization(self):
        # The two mixed terms need not agree entrywise for different basis
        # labels.  The full matrix entry uses both orientations exactly once.
        self.assertEqual(M.signed_shell_bilinear(
            Q(17), Q(5), Q(7), Q(11)), Q(16))
        self.assertNotEqual(M.signed_shell_bilinear(
            Q(17), Q(5), Q(7), Q(11)), Q(17) - 2 * Q(5) + Q(11))

    def test_exact_ldl_and_particular_solve(self):
        a = [[Q(2), Q(1)], [Q(1), Q(3)]]
        b = [[Q(1), Q(2)], [Q(2), Q(4)]]
        pivots = M.exact_ldl(a)
        self.assertEqual(pivots, [Q(2), Q(5, 2)])
        solves, vector, denominator, numerator = M.solve_particular(
            a, b, precisions=(90, 120), digits=40)
        self.assertEqual(len(solves), 2)
        self.assertEqual(denominator,
                         M.P.ei.exact_quadratic(a, vector))
        self.assertEqual(numerator, M.P.ei.exact_quadratic(b, vector))
        self.assertGreater(denominator, 0)

    def test_source_snapshot_and_fresh_publication(self):
        snapshots = M.snapshot_sources()
        self.assertEqual(M.sha256(snapshots[M.PROXY_PATH]),
                         M.PINNED_PROXY_SHA256)
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "result.json"
            digest = M.publish_new(output, {"status": "test"}, snapshots)
            self.assertEqual(digest, M.sha256(output))
            with self.assertRaises(FileExistsError):
                M.publish_new(output, {"status": "overwrite"}, snapshots)


if __name__ == "__main__":
    unittest.main()
