#!/usr/bin/env python3
"""Exact input-space tests for the arbitrary sparse Davidson action."""

import json
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
CODE = HERE.parent / "code"
sys.path.insert(0, str(CODE))

from band_action_sparse import compressed_coordinates  # noqa: E402
from band_operator import BandMap  # noqa: E402


ROOT = HERE.parents[2]
SOURCE = ROOT / "agents/exact-integrator/results/hb_c10_fullsimplex_noones_D12.json"
BANDS = ROOT / "agents/structural-basis/results/c10_D12_degree_bands.json"


class SparseActionInputTests(unittest.TestCase):
    def setUp(self):
        self.band_map = BandMap.from_source_and_bands(str(SOURCE), str(BANDS))
        self.source = json.loads(SOURCE.read_bytes())

    def test_source_recovers_theta0(self):
        self.assertEqual(compressed_coordinates(self.source, self.band_map),
                         self.band_map.theta0_q)

    def test_inconsistent_coefficient_is_rejected(self):
        bad = dict(self.source)
        bad["rational_vector"] = list(self.source["rational_vector"])
        owner = 12
        positions = [i for i, value in enumerate(self.band_map.owner)
                     if value == owner]
        self.assertGreater(len(positions), 1)
        bad["rational_vector"][positions[1]] = str(
            self.band_map.weight_q[positions[1]] * 2)
        with self.assertRaisesRegex(ValueError, "does not lie"):
            compressed_coordinates(bad, self.band_map)


if __name__ == "__main__":
    unittest.main()
