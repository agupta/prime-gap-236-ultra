#!/usr/bin/env python3

from fractions import Fraction as Q
import importlib.util
from pathlib import Path
import subprocess
import sys
import unittest

import numpy as np


TARGET = (Path(__file__).resolve().parents[1] / "code" /
          "active25_d18_truncated_one_band_h2_bridge_v1.py")
SPEC = importlib.util.spec_from_file_location(
    "active25_d18_truncated_one_band_h2_bridge_v1", TARGET)
if SPEC is None or SPEC.loader is None:
    raise ImportError(TARGET)
M = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = M
SPEC.loader.exec_module(M)


class TruncatedOneBandH2BridgeTest(unittest.TestCase):
    def test_pins_and_literal_geometry(self):
        row = M.validate_support()
        self.assertEqual(row["checker_sha256"], M.CHECKER_SHA256)
        self.assertEqual(M.ALPHA2, Q(9500917, 36000000))
        self.assertEqual(M.ETA, Q(8960917, 36000000))
        self.assertEqual(M.SCHEDULE[:12], M.SCHEDULE_HEAD)
        self.assertEqual(len(M.SCHEDULE), 48)

    def test_count_zero_is_not_admitted_above_truncation(self):
        engine = M.configure_engine()
        core = engine.load("one_band_membership_test_core", engine.CORE,
                           engine.CORE_SHA256)
        engine.configure(core, M.GEOMETRY)
        counts = np.array([[0, 1, 13]])
        large_sums = np.array([[0.0, 0.14, 0.21]], dtype=np.longdouble)
        totals = np.array([[float(M.ALPHA2) + 1e-5,
                            float(M.ALPHA2) - 1e-5,
                            float(M.ALPHA2) - 1e-5]],
                          dtype=np.longdouble)
        observed = M.one_band_cap_membership(
            core, counts, large_sums, geometry=M.GEOMETRY, totals=totals,
            band_geometry=M.one_band_geometry(core))
        self.assertEqual(observed.tolist(), [[False, True, False]])

    def test_cli_has_no_resume_or_target_action(self):
        text = TARGET.read_text()
        self.assertNotIn("attempt_001", text)
        self.assertNotIn("--resume", text)
        self.assertNotIn("--run", text)
        completed = subprocess.run(
            [sys.executable, str(TARGET), "--help"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        self.assertEqual(completed.returncode, 0)
        self.assertNotIn(b"geometry", completed.stdout)


if __name__ == "__main__":
    unittest.main()
