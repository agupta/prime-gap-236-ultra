#!/usr/bin/env python3

import hashlib
import importlib.util
import math
from pathlib import Path
import sys
import unittest

import numpy as np


HERE = Path(__file__).resolve()
REPO = HERE.parents[3]
SOURCE = REPO / (
    "agents/structural-basis/code/"
    "active25_d19_lower_degree_projection_bridge_v1.py")
SOURCE_SHA256 = "82a9a357d6605faa349c830d56b410cb7bd5c45f2b2ab05d81754ed55b8a84a7"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_source():
    spec = importlib.util.spec_from_file_location("lower_projection_bridge_test", SOURCE)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class LowerProjectionBridgeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_source()

    def test_frozen_source_and_exact_candidate_closure(self):
        self.assertEqual(digest(SOURCE), SOURCE_SHA256)
        data, rows = self.module.load_candidates()
        self.assertEqual(
            data["status"],
            "INDEPENDENT EXACT LOWER-DEGREE PARTICULAR VECTORS PASS")
        self.assertEqual(set(rows), {"D12", "D14", "D16"})
        self.assertEqual(
            [len(rows[name][1]) for name in ("D12", "D14", "D16")],
            [120, 195, 307])

    def test_projection_is_coordinate_scale_invariant(self):
        base = self.module.load(
            "lower_projection_summary_test_base", self.module.BASE,
            self.module.BASE_SHA256)
        a = np.asarray([[1.0, 2.0, 1.5], [0.8, 1.8, 1.2],
                        [1.1, 2.1, 1.4], [0.9, 1.9, 1.3]])
        b = np.asarray([[0.4, 0.5, 0.3], [0.35, 0.45, 0.25],
                        [0.42, 0.52, 0.32], [0.38, 0.48, 0.28]])
        first = base.projection_summary(a, b, 0.125)
        factor = -7.25
        second = base.projection_summary(
            a * factor * factor, b * factor, 0.125)
        self.assertTrue(math.isclose(
            first["projected_energy_over_inner_I"],
            second["projected_energy_over_inner_I"], rel_tol=2e-15))

    def test_cost_inventory_constants_are_strictly_ordered(self):
        inventories = [self.module.EXPECTED[name]
                       for name in ("D12", "D14", "D16")]
        self.assertEqual([row["A_groups"] for row in inventories],
                         [1508, 3034, 5825])
        self.assertEqual([row["global_b_keys"] for row in inventories],
                         [67880, 104902, 157438])
        self.assertTrue(all(
            left["global_b_keys"] < right["global_b_keys"]
            for left, right in zip(inventories, inventories[1:])))


if __name__ == "__main__":
    unittest.main()
