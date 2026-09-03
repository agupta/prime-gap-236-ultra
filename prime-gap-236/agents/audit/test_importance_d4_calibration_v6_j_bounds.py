#!/usr/bin/env python3
"""Regression for the frozen v6 serialized-J Cauchy-bound gap.

This test intentionally FAILS against v6.  A corrected successor must reject
the two-field mutation below with ArithmeticError.
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

import importance_d4_calibration_v6 as V6  # noqa: E402
from importance_whitening_v6 import WhitenedC10ImportanceDensity  # noqa: E402


ORACLE = REPO / V6.REQUIRED_DATA_PATHS[0]
VECTOR = REPO / V6.REQUIRED_DATA_PATHS[1]


class SerializedJCauchyBoundRegression(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        V6._patch_v5_runtime()
        cls.adapter = WhitenedC10ImportanceDensity(VECTOR, ORACLE)

    def test_batch_z_second_cannot_exceed_stratum_cauchy_bound_squared(self):
        schedule = V6.v5.tiny_smoke_schedule()
        spec = V6.v5.expected_chain_table()[64]  # J, r=0, replicate=0.
        record = V6.v5.run_one_chain(self.adapter, spec, schedule)
        mutated = copy.deepcopy(record)

        z_bound = math.fsum((
            self.adapter.base_constant_weights[0] ** 2,
            self.adapter.base_constant_weights[6] ** 2,
        ))
        seconds = [V6.v5.parse_float_hex(value)
                   for value in mutated["batch_z_second_means"]]
        seconds[0] = 2 * z_bound * z_bound
        mutated["batch_z_second_means"][0] = V6.v5.float_hex(seconds[0])
        mutated["raw_second_sum"][-1] = V6.v5.float_hex(
            schedule["samples_per_batch"] * math.fsum(seconds))

        # V6 currently returns True.  A fixed validator must reject because
        # every point has z^2 <= z_bound^2 in this common stratum.
        with self.assertRaises(ArithmeticError):
            V6.validate_chain_record(
                mutated, spec, schedule, adapter=self.adapter)


if __name__ == "__main__":
    unittest.main()
