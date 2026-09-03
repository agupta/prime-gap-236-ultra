#!/usr/bin/env python3
"""Low-k and fail-closed tests for the D12 fused-face benchmark."""

from __future__ import annotations

import copy
import sys
import unittest
from fractions import Fraction as Q
from pathlib import Path


HERE = Path(__file__).resolve().parent
EI = HERE.parent / "exact-integrator"
sys.path[:0] = [str(HERE), str(EI), str(EI / "src")]

import exact_integrator as ei  # noqa: E402
import benchmark_stratum_moment_d12_faces as bench  # noqa: E402
from stratum_moment_table import StratumMomentTableEvaluator  # noqa: E402
from stratum_moment_table_fused import (  # noqa: E402
    FusedStratumMomentTableEvaluator, moment_tag_schema,
    validate_moment_tag_schema,
)


class FaceBenchmarkTests(unittest.TestCase):
    @staticmethod
    def fixture(evaluator_class):
        support = ei.OneStratumSupport(
            3, Q(13, 50), Q(1, 20), Q(6, 25),
            Q(3, 20), Q(4, 25), Q(17, 100))
        labels = [(0, ()), (1, ()), (0, (2,)), (0, (3,))]
        coefficients = [Q(2), Q(-3), Q(5), Q(7)]
        return evaluator_class(
            support, labels, coefficients, Q, degree=3)

    def test_real_source_reconstructs_primitive_714_bit_scaling(self):
        labels, integers, common, original, scaled = \
            bench.load_source_bound_inputs()
        self.assertEqual(len(labels), 272)
        self.assertEqual(len(integers), 272)
        self.assertEqual(common.bit_length(), 714)
        self.assertEqual(bench.sha256(original), bench.ORIGINAL_SHA)
        self.assertEqual(bench.sha256(scaled), bench.SCALED_SHA)
        self.assertGreater(bench.available_memory_mib(), 0)
        self.assertEqual(bench.MINIMUM_AVAILABLE_MIB, 1844)

    def test_one_signed_k3_face_matches_exactly(self):
        unfused = self.fixture(StratumMomentTableEvaluator)
        fused = self.fixture(FusedStratumMomentTableEvaluator)
        grouped_u = unfused.square_residual_terms()
        grouped_f = fused.square_residual_terms()
        self.assertEqual(grouped_f, grouped_u)
        iu, icu = bench.evaluate_i_face(unfused, grouped_u, 0, 0)
        i_f, icf = bench.evaluate_i_face(fused, grouped_f, 0, 0)
        self.assertEqual(i_f, iu)
        self.assertEqual(icu["scalar_integrals"], 28)
        self.assertEqual(icf["scalar_integrals"], 28)

        _, lrs_u, by_lr_u = unfused._j_component_data()
        _, lrs_f, by_lr_f = fused._j_component_data()
        ju, jcu = bench.evaluate_j_face(
            unfused, lrs_u, by_lr_u, 0, 0, False)
        j_f, jcf = bench.evaluate_j_face(
            fused, lrs_f, by_lr_f, 0, 0, True)
        self.assertEqual(j_f, ju)
        self.assertEqual(jcf["branch_domains"], jcu["branch_domains"])
        self.assertEqual(jcf["logical_moment_products"],
                         jcu["logical_moment_products"])
        self.assertEqual(jcf["scalar_integrals"], jcu["scalar_integrals"])
        self.assertEqual(jcf["fused_traversals"],
                         jcf["branch_domains"])
        self.assertEqual(
            bench.table_sha(bench.canonical_j_table(j_f)),
            bench.table_sha(bench.canonical_j_table(ju)))

    def test_noncanonical_tags_and_tokens_fail_closed(self):
        schema = moment_tag_schema(3)
        self.assertTrue(validate_moment_tag_schema(schema, 3))
        bad = copy.deepcopy(schema)
        bad["cross_branch_product_tags"][0][0] = True
        with self.assertRaises(ValueError):
            validate_moment_tag_schema(bad, 3)
        for token in (True, 1, "01", "1/01", "2/2", "+1", "-0"):
            with self.assertRaises(bench.BenchmarkError):
                bench.parse_canonical_fraction(token, "mutation")
        for label in ([True, []], [0, [1]], [0, [2, 3]], [0, [2, True]]):
            with self.assertRaises(bench.BenchmarkError):
                bench.parse_label(label, 0)


if __name__ == "__main__":
    unittest.main()
