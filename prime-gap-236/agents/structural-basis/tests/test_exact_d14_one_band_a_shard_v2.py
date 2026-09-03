#!/usr/bin/env python3
"""Tests for paired-face exact D14 A shard production."""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction as Q
import hashlib
import importlib.util
from pathlib import Path
import sys
import unittest


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
SOURCE = REPO / (
    "agents/structural-basis/code/exact_d14_one_band_a_shard_v2.py")


def load_source():
    spec = importlib.util.spec_from_file_location(
        "test_exact_d14_one_band_a_shard_v2_source", SOURCE)
    if spec is None or spec.loader is None:
        raise ImportError(SOURCE)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


M = load_source()
B = M.B


class ExactD14OneBandAShardV2Tests(unittest.TestCase):
    def test_base_pin_and_no_resume_interface(self):
        self.assertEqual(hashlib.sha256(M.BASE.read_bytes()).hexdigest(),
                         M.BASE_SHA256)
        self.assertEqual(B.ACTIVE_COUNTS, tuple(range(13)))
        self.assertFalse(hasattr(M, "resume"))
        with self.assertRaises(ValueError):
            M.build_shard(-1)

    def test_paired_faces_equal_separate_grouped_and_literal_low_k(self):
        exact, stratum, grouped = B.load_integrators()

        @dataclass(frozen=True)
        class Support(stratum.StratumSupport):
            schedule: tuple[Q, ...] = ()

            def beta(self, r):
                if r <= 0:
                    raise ValueError(r)
                return self.schedule[min(r, len(self.schedule)) - 1]

        k = 3
        delta = Q(1, 5)
        eta = Q(1, 2)
        schedule = (Q(2, 5), Q(3, 5), Q(3, 4))
        high = Support(k, Q(3, 4), delta, eta,
                       schedule[0], schedule[1], schedule[2], schedule)
        low = Support(k, Q(2, 3), delta, eta,
                      schedule[0], schedule[1], schedule[2], schedule)
        basis = ((0, ()), (1, ()), (0, (2,)))
        vector = (Q(2, 3), Q(-3, 7), Q(5, 11))
        for count in range(k + 1):
            paired = M.paired_evaluate(
                grouped, high, low, basis, vector, count, False)
            high_value, low_value = paired[:2]
            separate = []
            for support in (high, low):
                evaluator = grouped.GroupedEvaluator(
                    support, basis, vector, Q)
                by_orbit = evaluator.square_residual_terms()
                value, _ = evaluator.evaluate_i_r(by_orbit, count, False)
                literal = sum(
                    vector[i] * vector[j] *
                    support.basis_m1_in_strata(
                        count, basis[i], count, basis[j])
                    for i in range(len(basis)) for j in range(len(basis)))
                self.assertEqual(value, literal)
                separate.append(value)
            self.assertEqual((high_value, low_value), tuple(separate))
            self.assertGreaterEqual(high_value - low_value, 0)

    def test_grid_scale_clears_denominators_and_preserves_square(self):
        _fine, selected, basis, vector, _one_band = B.load_inputs()
        scaled = tuple(B.VECTOR_SCALE * x for x in vector)
        self.assertTrue(all(x.denominator == 1 for x in scaled))
        dilation = B.ALPHA1 / B.ALPHA2
        left = B.natural_dilation_common_vector(basis, scaled, dilation)
        right = tuple(B.VECTOR_SCALE * x for x in
                      B.natural_dilation_common_vector(
                          basis, vector, dilation))
        self.assertEqual(left, right)
        self.assertEqual(Q(selected["exact_denominator"]) * B.VECTOR_SCALE**2,
                         Q(selected["exact_denominator"]) * 10**76)


if __name__ == "__main__":
    unittest.main()
