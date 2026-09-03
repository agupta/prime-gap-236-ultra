#!/usr/bin/env python3

import importlib.util
from pathlib import Path
import subprocess
import sys
import unittest


TARGET = (Path(__file__).resolve().parents[1] / "code" /
          "check_active25_d19_truncated_one_band_projection_bridge_v1.py")
SPEC = importlib.util.spec_from_file_location(
    "check_active25_d19_truncated_one_band_projection_bridge_v1", TARGET)
if SPEC is None or SPEC.loader is None:
    raise ImportError(TARGET)
M = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = M
SPEC.loader.exec_module(M)


class CheckD19ProjectionBridgeTest(unittest.TestCase):
    def test_check(self):
        row = M.check()
        self.assertEqual(row["status"],
                         "INDEPENDENT D19 PROJECTION SCREEN CHECK PASS")
        screen = row["finite_chain_screen"]
        self.assertGreater(screen["natural_D19_projection"][
            "inverse_variance_combined"], row["exact_inner"][
                "deficit_over_I_decimal"])
        self.assertIs(row["launch_authorized"], False)

    def test_normal_optimized_identical(self):
        rows = [subprocess.run(command, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, check=False)
                for command in (
                    [sys.executable, str(TARGET)],
                    [sys.executable, "-O", str(TARGET)])]
        self.assertEqual([row.returncode for row in rows], [0, 0])
        self.assertEqual(rows[0].stdout, rows[1].stdout)


if __name__ == "__main__":
    unittest.main()
