#!/usr/bin/env python3
"""Small hostile tests for the exact one-band shard assembler."""

from __future__ import annotations

from fractions import Fraction as Q
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest


HERE = Path(__file__).resolve().parent
SOURCE = HERE / "assemble_one_band_236_shards.py"


def load_source():
    spec = importlib.util.spec_from_file_location("one_band_236_assembler_test", SOURCE)
    if spec is None or spec.loader is None:
        raise ImportError(SOURCE)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


M = load_source()


def payload(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


class OneBandAssemblerTests(unittest.TestCase):
    def test_constants_and_incomplete_set_fail_closed(self):
        self.assertEqual(M.K, 48)
        self.assertEqual(M.COUNTS, tuple(range(13)))
        self.assertEqual(M.FORM_SCALE, 10**174)
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            (directory / "r00.json").write_text("{}")
            with self.assertRaisesRegex(ValueError, "incomplete/noncanonical"):
                M.require_exact_files(directory, "r")

    def test_a_shard_requires_exact_scale_and_difference(self):
        source = M.DEFAULT_A_DIR / "r03.json"
        row = json.loads(source.read_text())
        observed = M.parse_a_shard(source, payload(row), 3)
        self.assertGreater(observed, 0)
        row["exact_values"]["band_I_count"] = str(observed + 1)
        with self.assertRaises(ArithmeticError):
            M.parse_a_shard(Path("a.json"), payload(row), 3)

    def test_b_shard_recombines_single_factor_48(self):
        count = 5
        high_branches = M.expected_branches(M.ALPHA2, count)
        low_branches = M.expected_branches(M.ALPHA1, count)
        stat = {
            "active_shifts": 1, "packed_terms": 1, "tag_groups": 1,
            "collected_affine_terms": 1, "requested_moments": 1,
            "scalar_products": 1, "nonzero_product_monomials": 1,
            "cancelled_product_monomials": 0,
            "maximum_affine_denominator_bits": 1,
            "maximum_moment_denominator_bits": 1,
        }
        high = {branch: "1" for branch in high_branches}
        low = {branch: "0" for branch in low_branches}
        expected_value = 48 * len(high_branches)
        row = {
            "algorithm": M.B_ALGORITHM,
            "format": "D14-grid38-scaled-cutoff-cross-common-r-collected-v5",
            "status": "EXACT COLLECTED COMMON-r CROSS SHARD PASS",
            "rigorous": True,
            "common_r": count,
            "producer_sha256": M.PINNED[M.B_RUNNER],
            "serialized_matrices_read": False,
            "scaling": {
                "inner_F": str(M.SCALE_F),
                "outer_H": str(M.SCALE_H),
                "b_factor": str(M.SCALE_F * M.SCALE_H),
                "invariant": "b_scaled^2/A_scaled = 10^174*(b^2/A)",
            },
            "geometry": {
                "k": 48, "delta": str(M.DELTA),
                "alpha1": str(M.ALPHA1), "alpha2": str(M.ALPHA2),
                "eta": str(M.ETA),
                "natural_dilation_alpha1_over_alpha2": str(M.DILATION),
                "schedule": list(map(str, M.SCHEDULE)),
                "definition5_cutoff_retained": True,
            },
            "candidate": {
                "inner": "pinned strict cache-free exact D19 v2",
                "outer": "D14_grid_1e-38", "inner_basis_dimension": 568,
                "outer_basis_dimension": 195,
                "inner_common_denominator_lcm": str(M.SCALE_F),
                "outer_common_denominator_lcm": str(M.SCALE_H),
                "dilation_point_check": True,
            },
            "source_hashes": M.B_SOURCE_HASHES,
            "scaled_b_shard": str(expected_value),
            "branch_values_and_fast_stats": {
                "high": high, "low": low,
                "high_stats": {branch: dict(stat) for branch in high_branches},
                "low_stats": {branch: dict(stat) for branch in low_branches},
                "integer_radialization": {}, "timing_seconds": {},
            },
            "family_stats": {}, "kernel_stats": {},
            "peak_rss_kib": 1, "timing_seconds": {},
        }
        self.assertEqual(M.parse_b_shard(Path("b.json"), payload(row), count),
                         expected_value)
        row["scaled_b_shard"] = str(expected_value + 1)
        with self.assertRaises(ArithmeticError):
            M.parse_b_shard(Path("b.json"), payload(row), count)

    def test_noncanonical_fraction_and_duplicate_json_rejected(self):
        with self.assertRaises(ValueError):
            M.canonical_q("2/4", "bad")
        with self.assertRaisesRegex(ValueError, "duplicate JSON key"):
            M.strict_json(b'{"x":1,"x":2}', "duplicate")


if __name__ == "__main__":
    unittest.main()
