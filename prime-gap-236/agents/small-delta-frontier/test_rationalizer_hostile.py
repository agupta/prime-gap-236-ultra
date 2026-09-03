#!/usr/bin/env python3
"""Independent hostile regression for the compact rationalizer boundary."""

from __future__ import annotations

import hashlib
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]
CODE = ROOT / "agents" / "structural-basis" / "code"
sys.path.insert(0, str(CODE))

import rationalize_band_candidate as rationalizer  # noqa: E402


SOURCE = ROOT / "agents" / "exact-integrator" / "results" / \
    "hb_c10_fullsimplex_noones_D12.json"
BANDS = ROOT / "agents" / "structural-basis" / "results" / \
    "c10_D12_degree_bands.json"
class RationalizerHostileTests(unittest.TestCase):
    def test_postpublish_mutation_rewrites_owned_inode_to_rejection(self):
        """Regression for the false accept found against SHA fddb3735."""
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            candidate = directory / "candidate"
            output = directory / "compact.json"
            candidate.write_bytes(b"pinned candidate")
            candidate_sha = hashlib.sha256(candidate.read_bytes()).hexdigest()
            descriptor, identity = rationalizer.reserve_output(output)

            def mutate(_target):
                candidate.write_bytes(b"mutated after publish")

            with self.assertRaisesRegex(ValueError, "trusted rationalizer byte"):
                rationalizer.publish_reserved(
                    output, "generated output\n", descriptor, identity,
                    {candidate.resolve(): candidate_sha}, mutate)
            self.assertEqual(
                rationalizer.strict_json_loads(output.read_bytes()),
                {"status": "REJECTED-rationalizer-publication",
                 "rigorous": False})
            self.assertFalse(list(directory.glob("compact.json.rejected.*")))

    def test_stat_race_preserves_foreign_inode(self):
        """Regression for SHA 57c8ebb1's check/rename race."""
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            candidate = directory / "candidate"
            output = directory / "compact.json"
            candidate.write_bytes(b"pinned candidate")
            expected = hashlib.sha256(candidate.read_bytes()).hexdigest()
            descriptor, identity = rationalizer.reserve_output(output)
            original_stat = os.stat
            swapped = False

            def mutate_dependency(_target):
                candidate.write_bytes(b"mutated dependency")

            def racing_stat(path, *args, **kwargs):
                nonlocal swapped
                result = original_stat(path, *args, **kwargs)
                if Path(path) == output and not swapped:
                    # Return the saved owned-inode stat, but replace the
                    # pathname before the subsequent dependency failure.
                    output.unlink()
                    output.write_bytes(b"foreign concurrent file")
                    swapped = True
                return result

            with patch.object(rationalizer.os, "stat", racing_stat):
                with self.assertRaisesRegex(ValueError,
                                            "trusted rationalizer byte"):
                    rationalizer.publish_reserved(
                        output, "generated output\n", descriptor, identity,
                        {candidate.resolve(): expected}, mutate_dependency)
            self.assertTrue(swapped)
            self.assertEqual(output.read_bytes(), b"foreign concurrent file")
            self.assertFalse(list(directory.glob("compact.json.rejected.*")))


if __name__ == "__main__":
    unittest.main()
