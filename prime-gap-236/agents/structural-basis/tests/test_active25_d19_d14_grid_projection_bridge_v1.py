#!/usr/bin/env python3

import hashlib
import importlib.util
from pathlib import Path
import sys
import unittest


HERE = Path(__file__).resolve()
REPO = HERE.parents[3]
SOURCE = REPO / (
    "agents/structural-basis/code/active25_d19_d14_grid_projection_bridge_v1.py")
SOURCE_SHA256 = "3f4f3055abc51c333c345ece89d084d5890935d8207f1d2c5f1ef410d0f26f31"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_source():
    spec = importlib.util.spec_from_file_location("d14_grid_projection_test", SOURCE)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class D14GridProjectionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_source()

    def test_frozen_source_and_candidates(self):
        self.assertEqual(digest(SOURCE), SOURCE_SHA256)
        lower = self.module.load(
            "d14_grid_projection_lower_test", self.module.LOWER_SCREEN,
            self.module.LOWER_SCREEN_SHA256)
        _, candidates = lower.load_candidates()
        data, grids = self.module.load_grid_candidates(candidates["D14"][1])
        self.assertEqual(
            data["status"], "EXACT D14 COMMON-GRID PARTICULAR VECTORS PASS")
        self.assertEqual(set(grids), {12, 14, 16})

    def test_crn_difference_zero(self):
        row = {"per_chain_projected_energy_over_inner_I": [1, 2, 3, 4]}
        mean, error, values = self.module.crn_difference(row, row)
        self.assertEqual((mean, error), (0, 0))
        self.assertEqual(values, [0, 0, 0, 0])

    def test_grid_inner_quotients_are_negative_signal(self):
        lower = self.module.load(
            "d14_grid_projection_lower_test_2", self.module.LOWER_SCREEN,
            self.module.LOWER_SCREEN_SHA256)
        _, candidates = lower.load_candidates()
        _, grids = self.module.load_grid_candidates(candidates["D14"][1])
        from fractions import Fraction as Q
        self.assertTrue(all(Q(row[0]["exact_quotient"]) < Q(1, 4)
                            for row in grids.values()))


if __name__ == "__main__":
    unittest.main()
