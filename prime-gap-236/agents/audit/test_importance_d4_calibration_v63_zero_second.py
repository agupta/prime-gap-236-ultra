#!/usr/bin/env python3
"""Desired regressions for frozen v6.3's zero-second Jensen gap.

These tests intentionally FAIL on v6.3.  A corrected successor must reject a
positive first J moment paired with an exactly zero second J moment.
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

import importance_d4_calibration_v63 as V63  # noqa: E402
from importance_whitening_v6 import WhitenedC10ImportanceDensity  # noqa: E402


def impossible_short_record():
    encode = V63.v62.v61.v6.v5.float_hex
    mean = math.sqrt(math.ulp(0.0))
    return {
        "target": "J",
        "batch_z_means": [encode(mean)] * 4,
        "batch_z_second_means": [encode(0.0)] * 4,
        "raw_sum": [encode(8 * mean)],
        "raw_second_sum": [encode(0.0)],
    }


class V63ZeroSecondRegression(unittest.TestCase):
    def test_positive_batch_first_with_zero_second_is_rejected(self):
        mean = math.sqrt(math.ulp(0.0))
        self.assertEqual(mean * mean, math.ulp(0.0))
        schedule = {"batches_per_chain": 4, "samples_per_batch": 2}
        with self.assertRaises(ArithmeticError):
            V63._validate_j_totals_before_averaging(
                impossible_short_record(), schedule)

    def test_public_validator_rejects_positive_first_zero_second(self):
        V63.install_runtime()
        V63.v62.v61.v6._patch_v5_runtime()
        oracle = REPO / V63.v62.v61.v6.REQUIRED_DATA_PATHS[0]
        vector = REPO / V63.v62.v61.v6.REQUIRED_DATA_PATHS[1]
        adapter = WhitenedC10ImportanceDensity(vector, oracle)
        schedule = V63.v62.v61.v6.v5.tiny_smoke_schedule()
        spec = V63.v62.v61.v6.v5.expected_chain_table()[124]
        record = V63.v62.v61.v6.v5.run_one_chain(adapter, spec, schedule)
        mutated = copy.deepcopy(record)
        short = impossible_short_record()
        mutated["batch_z_means"] = short["batch_z_means"]
        mutated["batch_z_second_means"] = short["batch_z_second_means"]
        mutated["raw_sum"][-1] = short["raw_sum"][-1]
        mutated["raw_second_sum"][-1] = short["raw_second_sum"][-1]
        with self.assertRaises(ArithmeticError):
            V63.validate_chain_record(
                mutated, spec, schedule, adapter=adapter)


if __name__ == "__main__":
    unittest.main()
