#!/usr/bin/env python3
"""Lightweight hostile/integrity tests for the exact v4 width portfolio."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
import unittest
from fractions import Fraction as Q
from pathlib import Path


HERE = Path(__file__).resolve().parent
CHECKER = HERE / "verify_one_band_width_portfolio_v4.py"
RESULT = HERE / "one_band_width_portfolio_v4_exact.json"
CHECKER_SHA256 = "67cadda54da344c0760bec204d9656d09e8e1fa8ff70adb0e8648423c982a923"
RESULT_SHA256 = "4d8053a4ef6160ea30bab5b4573379d1903bb235c4dc513d9985d6bc6297b7e5"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


spec = importlib.util.spec_from_file_location("one_band_width_v4_tested",
                                              CHECKER)
if spec is None or spec.loader is None:
    raise ImportError("cannot load width portfolio checker")
v = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = v
spec.loader.exec_module(v)


class WidthPortfolioTests(unittest.TestCase):
    def test_hash_and_status_closure(self):
        self.assertEqual(sha256(CHECKER), CHECKER_SHA256)
        self.assertEqual(sha256(RESULT), RESULT_SHA256)
        payload = json.loads(RESULT.read_text(encoding="ascii"))
        self.assertEqual(payload["checker_sha256"], CHECKER_SHA256)
        self.assertEqual(payload["status"],
                         "EXACT ONE-OUTER-BAND WIDTH PORTFOLIO PASS")
        self.assertIn("No structural-basis result",
                      payload["acceptance_independence"])

    def test_candidate_inventory_and_strict_reserves(self):
        payload = json.loads(RESULT.read_text(encoding="ascii"))
        self.assertEqual([candidate["width_fraction_of_old_outer"]
                          for candidate in payload["candidates"]],
                         ["19/20", "39/40", "1"])
        for candidate in payload["candidates"]:
            self.assertEqual(candidate["outer_active_counts"], list(range(13)))
            self.assertEqual(len(candidate["outer_schedule_head_12"]), 12)
            through_empty = candidate["outer_schedule_through_first_empty"]
            self.assertEqual(through_empty[-1], through_empty[-2])
            inventory = candidate["ordered_pair_packing"]
            self.assertEqual((inventory["main_ordered_pairs"],
                              inventory["near_ordered_pairs"],
                              inventory["IIa_III_checks"]),
                             (582, 168, 1500))
            self.assertEqual((inventory["dynamic_pairs"],
                              inventory["dynamic_checks"]), (168, 43008))
            strict = candidate["strict_outer_cap_interval"]
            self.assertGreater(Q(strict["base_minimum_packing_reserve"]), 0)
            self.assertGreater(Q(strict["upper_minimum_packing_reserve"]), 0)
            self.assertGreater(Q(candidate["main_direct_HB_face_reserve"]), 0)

    def test_dependency_pin_and_dirty_global_fail_closed(self):
        v.dependency_check()
        original = v.v3.ENDPOINT
        try:
            v.v3.ENDPOINT += Q(1, 10**9)
            with self.assertRaisesRegex(ArithmeticError,
                                        "kernel globals dirty"):
                with v.configured(v.CANDIDATES[0]):
                    pass
        finally:
            v.v3.ENDPOINT = original

    def test_exact_open_width_obstruction(self):
        payload = json.loads(RESULT.read_text(encoding="ascii"))
        obstruction = payload["maximum_rational_interior_width_obstruction"]
        self.assertEqual(Q(obstruction["width_supremum"]), Q(1, 144))
        self.assertEqual(Q(obstruction["supremum_fraction_of_old_outer"]),
                         Q(6250, 6241))
        self.assertLess(Q(payload["parameters_common"]["old_outer_width"]),
                        Q(obstruction["width_supremum"]))


if __name__ == "__main__":
    unittest.main()
