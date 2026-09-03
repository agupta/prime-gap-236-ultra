#!/usr/bin/env python3
"""Desired regressions for frozen v6.2 J-moment underflow closure.

These tests intentionally FAIL on v6.2.  A corrected successor must reject
each loss of a positive serialized quantity during averaging/regrouping.
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

import importance_d4_calibration_v62 as V62  # noqa: E402
from importance_whitening_v6 import WhitenedC10ImportanceDensity  # noqa: E402


class V62UnderflowRegression(unittest.TestCase):
    def test_positive_raw_first_and_second_totals_cannot_average_to_zero(self):
        encode = V62.v61.v6.v5.float_hex
        zero = encode(0.0)
        tiny = encode(math.ulp(0.0))
        schedule = {"batches_per_chain": 4, "samples_per_batch": 2}
        for raw_field in ("raw_sum", "raw_second_sum"):
            record = {
                "target": "J",
                "batch_z_means": [zero] * 4,
                "batch_z_second_means": [zero] * 4,
                "raw_sum": [zero],
                "raw_second_sum": [zero],
            }
            record[raw_field] = [tiny]
            with self.subTest(raw_field=raw_field), \
                    self.assertRaises(ArithmeticError):
                V62._validate_j_local_consistency(record, schedule)

    def test_positive_batch_second_cannot_disappear_in_batch_average(self):
        encode = V62.v61.v6.v5.float_hex
        zero = encode(0.0)
        tiny_value = math.ulp(0.0)
        record = {
            "target": "J",
            "batch_z_means": [zero] * 4,
            "batch_z_second_means": [encode(tiny_value), zero, zero, zero],
            "raw_sum": [zero],
            "raw_second_sum": [encode(2 * tiny_value)],
        }
        schedule = {"batches_per_chain": 4, "samples_per_batch": 2}
        with self.assertRaises(ArithmeticError):
            V62._validate_j_local_consistency(record, schedule)

    def test_public_validator_rejects_raw_subnormal_hidden_by_zero_batches(self):
        V62.install_runtime()
        V62.v61.v6._patch_v5_runtime()
        oracle = REPO / V62.v61.v6.REQUIRED_DATA_PATHS[0]
        vector = REPO / V62.v61.v6.REQUIRED_DATA_PATHS[1]
        adapter = WhitenedC10ImportanceDensity(vector, oracle)
        schedule = V62.v61.v6.v5.tiny_smoke_schedule()
        spec = V62.v61.v6.v5.expected_chain_table()[124]
        record = V62.v61.v6.v5.run_one_chain(adapter, spec, schedule)
        mutated = copy.deepcopy(record)
        zero = V62.v61.v6.v5.float_hex(0.0)
        mutated["batch_z_means"] = [zero] * 4
        mutated["batch_z_second_means"] = [zero] * 4
        mutated["raw_sum"][-1] = V62.v61.v6.v5.float_hex(math.ulp(0.0))
        mutated["raw_second_sum"][-1] = zero
        with self.assertRaises(ArithmeticError):
            V62.validate_chain_record(
                mutated, spec, schedule, adapter=adapter)


if __name__ == "__main__":
    unittest.main()
