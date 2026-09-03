#!/usr/bin/env python3
"""Independent exact regressions for the one-band .16/.177 support audit."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from fractions import Fraction as Q
from pathlib import Path


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
VERIFY = HERE / "verify_one_band_177_prop1.py"
GEOMETRY = HERE / "two_band_mixed_audit.py"
ARTIFACT = HERE / "results/one_band_177_and_two_band_geometry.json"
ANALYTIC = HERE / "results/one_band_177_prop1_audit.json"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class OneBand177Tests(unittest.TestCase):
    def test_frozen_hashes_and_schema(self):
        self.assertEqual(sha(GEOMETRY),
                         "7323ab20b12e550799646684720e23487ec379886a24f325546d5cef7bb03116")
        self.assertEqual(sha(ARTIFACT),
                         "0190e729eb2a4bc547aea0a057c0cb631c480f0a3fd596702340cfc452ccfbeb")
        self.assertEqual(sha(ANALYTIC),
                         "8d8fc9da82012c607a5239596774b806d049458124b811f51f20bfa34a3e5fba")
        data = json.loads(ANALYTIC.read_bytes())
        self.assertEqual(data["status"], "one-band-177-analytic-parameter-pass")
        self.assertFalse(data["theorem_ready"])
        self.assertEqual(data["parameters"]["k"], 48)
        self.assertEqual(data["fresh_cover_counts"]["pairs"], 27)

    def test_critical_iic_endpoint_is_genuinely_strict(self):
        c1 = Q(1599999995521, 5000000000000)
        b = Q(159999999, 10**9)
        self.assertEqual(c1 - 2 * b, Q(5521, 5000000000000))
        self.assertEqual(2 * Q(4, 25) - c1,
                         Q(4479, 5000000000000))
        c2 = Q(799999995521, 10000000000000)
        self.assertGreater(b, c2)

    def test_definition1_and_strict_support_enlargement(self):
        delta = Q(7, 250)
        schedule = [Q(159999999, 10**9)] * 2 + [Q(177, 1000)] * 33
        self.assertEqual(len(schedule), 35)
        for left, right in zip(schedule, schedule[1:]):
            self.assertLessEqual(left, right)
            self.assertLessEqual(right, left + delta)
        self.assertLessEqual(6 * delta, schedule[5])
        self.assertLess(schedule[6], 7 * delta)
        # Published support is contained, and the containment is strict in
        # both the one-large and three-large strata.
        self.assertGreater(schedule[0], Q(3, 20))
        self.assertGreater(schedule[2], Q(17, 100))

    def test_type0_and_prop2_bookkeeping(self):
        h = Q(1, 10**10)
        sigma = Q(1, 10) + h / 10
        A = Q(253, 1000)
        self.assertEqual(1 - ((Q(1, 2) - sigma) + 2 * A),
                         Q(9400000001, 100000000000))
        xi1, xi2 = Q(19, 50), Q(2, 5)
        self.assertLess(2 * xi1 + 3 * xi2, 2)
        self.assertLess(xi1 + 9 * xi2, 4)
        self.assertGreater(2 * xi1 + xi2, 1)
        self.assertLess(17 * xi2, 7)
        self.assertGreater(1 - 2 * xi2, Q(159999999, 10**9))

    def test_normal_and_optimized_outputs_identical(self):
        normal = subprocess.run(
            [sys.executable, str(VERIFY)], cwd=REPO, check=True,
            stdout=subprocess.PIPE).stdout
        optimized = subprocess.run(
            [sys.executable, "-O", str(VERIFY)], cwd=REPO, check=True,
            stdout=subprocess.PIPE).stdout
        self.assertEqual(normal, optimized)
        self.assertEqual(normal, ANALYTIC.read_bytes())

    def test_hash_gate_rejects_mutation(self):
        sys.path.insert(0, str(HERE))
        import verify_one_band_177_prop1 as verifier
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "mutated"
            path.write_bytes(b"not the pinned source")
            with self.assertRaises(RuntimeError):
                verifier.require_sha(path, "0" * 64)


if __name__ == "__main__":
    unittest.main()
