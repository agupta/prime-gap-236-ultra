#!/usr/bin/env python3
"""Desired regressions for v6.1 tail-scale aggregation/Jensen closure.

Both tests intentionally FAIL against frozen v6.1.  A corrected successor
must reject each mutation with ArithmeticError.
"""

from __future__ import annotations

import copy
import math
import sys
import unittest
from pathlib import Path


HERE = Path(__file__).resolve()
REPO = HERE.parents[2]
CODE = REPO / "agents/structural-basis/code"
sys.path.insert(0, str(CODE))

import importance_d4_calibration_v61 as V61  # noqa: E402
from importance_whitening_v6 import WhitenedC10ImportanceDensity  # noqa: E402


ORACLE = REPO / V61.v6.REQUIRED_DATA_PATHS[0]
VECTOR = REPO / V61.v6.REQUIRED_DATA_PATHS[1]


class V61TailMomentRegression(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        V61.install_runtime()
        V61.v6._patch_v5_runtime()
        cls.adapter = WhitenedC10ImportanceDensity(VECTOR, ORACLE)
        cls.schedule = V61.v6.v5.tiny_smoke_schedule()
        cls.spec = V61.v6.v5.expected_chain_table()[124]  # J,r=15,rep=0.
        cls.record = V61.v6.v5.run_one_chain(
            cls.adapter, cls.spec, cls.schedule)

    def test_raw_z_sum_must_reconstruct_positive_batch_means_at_tail_scale(self):
        mutated = copy.deepcopy(self.record)
        self.assertGreater(sum(V61.v6.v5.parse_float_hex(value)
                               for value in mutated["batch_z_means"]), 0)
        mutated["raw_sum"][-1] = V61.v6.v5.float_hex(0.0)
        with self.assertRaises(ArithmeticError):
            V61.validate_chain_record(
                mutated, self.spec, self.schedule, adapter=self.adapter)

    def test_positive_batch_z_mean_requires_positive_second_moment(self):
        mutated = copy.deepcopy(self.record)
        mean = V61.v6.v5.parse_float_hex(mutated["batch_z_means"][0])
        self.assertGreater(mean, 0)
        seconds = [V61.v6.v5.parse_float_hex(value)
                   for value in mutated["batch_z_second_means"]]
        seconds[0] = 0.0
        mutated["batch_z_second_means"][0] = V61.v6.v5.float_hex(0.0)
        mutated["raw_second_sum"][-1] = V61.v6.v5.float_hex(
            self.schedule["samples_per_batch"] * math.fsum(seconds))
        with self.assertRaises(ArithmeticError):
            V61.validate_chain_record(
                mutated, self.spec, self.schedule, adapter=self.adapter)


if __name__ == "__main__":
    unittest.main()
