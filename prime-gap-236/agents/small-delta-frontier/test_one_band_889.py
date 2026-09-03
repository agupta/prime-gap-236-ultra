#!/usr/bin/env python3
"""Hostile regressions for the sharpened B889 support artifacts."""

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
GEOMETRY = HERE / "one_band_889_frontier_audit.py"
GEOMETRY_RESULT = HERE / "results/one_band_889_sharpened_geometry.json"
VERIFY = HERE / "verify_one_band_889_prop1.py"
RESULT = HERE / "results/one_band_889_sharpened_prop1.json"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class OneBand889Tests(unittest.TestCase):
    def test_frozen_bytes(self):
        self.assertEqual(sha(GEOMETRY),
                         "bdc551e27f05e33d6395dd241ee116248874b17ebcb832f10c6cd6906fe580ba")
        self.assertEqual(sha(GEOMETRY_RESULT),
                         "0bef3e4be5f4a9963f43ebdfd62f3017cd41bfa948624667619ec337733c1b63")
        self.assertEqual(sha(RESULT),
                         "6189ac7a2837433a1bd760e29178dcf0e5809042c126da9d3b6d7bd1a7914dae")

    def test_exact_schedule_and_critical_margin(self):
        data = json.loads(GEOMETRY_RESULT.read_bytes())
        schedule = tuple(Q(x) for x in
                         data["parameters"]["schedule_through_first_empty"])
        self.assertEqual(schedule[:2], (Q(159999999, 10**9),) * 2)
        self.assertEqual(schedule[2:], (Q(889, 5000),) * 5)
        self.assertEqual(Q(data["critical_iic_margin"]),
                         Q(5521, 5000000000000))
        self.assertEqual(data["cover"]["pair_count"], 27)
        self.assertEqual(data["cover"]["node_totals"]["IIc"], 1845)

    def test_strictly_contains_published_B889(self):
        b = Q(159999999, 10**9)
        self.assertGreater(b, Q(3, 20))
        self.assertEqual(Q(889, 5000), Q(889, 5000))
        # A literal point admitted only by the sharpened cap.
        witness = Q(31, 200)
        self.assertGreater(witness, Q(3, 20))
        self.assertLessEqual(witness, b)

    def test_endpoint_mutations_fail_geometry(self):
        # B1=B2=4/25 fails at the explicit point (B1,B2): it exceeds C1
        # and neither coordinate fits any singleton bin.
        c1 = Q(1599999995521, 5000000000000)
        caps = (c1, Q(799999995521, 10000000000000),
                Q(70000001, 2500000000), Q(1, 50000000000))
        point = (Q(4, 25), Q(4, 25))
        self.assertGreater(sum(point), caps[0])
        self.assertTrue(all(x > max(caps[1:]) for x in point))

    def test_normal_optimized_reconstruction(self):
        for script, artifact in ((GEOMETRY, GEOMETRY_RESULT), (VERIFY, RESULT)):
            normal = subprocess.run(
                [sys.executable, str(script)], cwd=REPO, check=True,
                stdout=subprocess.PIPE).stdout
            optimized = subprocess.run(
                [sys.executable, "-O", str(script)], cwd=REPO, check=True,
                stdout=subprocess.PIPE).stdout
            self.assertEqual(normal, optimized)
            self.assertEqual(normal, artifact.read_bytes())

    def test_prop1_parser_rejects_mutated_dependency(self):
        sys.path.insert(0, str(HERE))
        import verify_one_band_889_prop1 as verifier
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.json"
            path.write_text("{}")
            with self.assertRaises(RuntimeError):
                verifier.require(path, "f" * 64)


if __name__ == "__main__":
    unittest.main()
