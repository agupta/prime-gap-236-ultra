#!/usr/bin/env python3

import hashlib
import importlib.util
from pathlib import Path
import sys
import unittest


HERE = Path(__file__).resolve()
REPO = HERE.parents[3]
SOURCE = REPO / (
    "agents/structural-basis/code/active25_d19_d14_fine_grid_projection_bridge_v2.py")
SOURCE_SHA256 = "789aeeb6a95b9cd52e93a649abdc4a9c8ada55fb2c0d1309d196894a662e38f6"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_source():
    spec = importlib.util.spec_from_file_location("d14_fine_grid_projection_test", SOURCE)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class D14FineGridProjectionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_source()

    def test_frozen_source_and_grid_closure(self):
        self.assertEqual(digest(SOURCE), SOURCE_SHA256)
        lower = self.module.load(
            "d14_fine_grid_lower_test", self.module.LOWER_SCREEN,
            self.module.LOWER_SCREEN_SHA256)
        _, candidates = lower.load_candidates()
        data, grids = self.module.load_fine_candidates(candidates["D14"][1])
        self.assertEqual(
            data["status"],
            "EXACT D14 FINE COMMON-GRID PARTICULAR VECTORS PASS")
        self.assertEqual(set(grids), {38, 40, 42})

    def test_crn_difference_zero(self):
        row = {"per_chain_projected_energy_over_inner_I": [1, 2, 3, 4]}
        mean, error, values = self.module.crn_difference(row, row)
        self.assertEqual((mean, error), (0, 0))
        self.assertEqual(values, [0, 0, 0, 0])

    def test_grid_order_is_coarsest_first(self):
        self.assertEqual((38, 40, 42), tuple(sorted((38, 40, 42))))


if __name__ == "__main__":
    unittest.main()
