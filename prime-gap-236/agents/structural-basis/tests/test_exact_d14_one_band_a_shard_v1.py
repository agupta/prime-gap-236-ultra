#!/usr/bin/env python3
"""Tests for the independent exact D14 one-band A shard producer."""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction as Q
import hashlib
import importlib.util
from itertools import permutations
from pathlib import Path
import sys
import tempfile
import unittest


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
SOURCE = REPO / (
    "agents/structural-basis/code/exact_d14_one_band_a_shard_v1.py")


def load_source():
    spec = importlib.util.spec_from_file_location(
        "test_exact_d14_one_band_a_shard_v1_source", SOURCE)
    if spec is None or spec.loader is None:
        raise ImportError(SOURCE)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


M = load_source()


def orbit_value(point, lam):
    padded = tuple(lam) + (0,) * (len(point) - len(lam))
    return sum(
        __import__("math").prod(x ** exponent
                                for x, exponent in zip(point, exponents))
        for exponents in set(permutations(padded)))


def polynomial_value(basis, vector, point):
    total = sum(point, Q(0))
    return sum(theta * (1 - total) ** a * orbit_value(point, lam)
               for theta, (a, lam) in zip(vector, basis))


class ExactD14OneBandAShardTests(unittest.TestCase):
    def test_frozen_inputs_and_selected_vector(self):
        snapshots = {path: path.read_bytes() for path in M.PINNED_INPUTS}
        M.validate_pins(snapshots)
        fine, row, basis, vector, one_band = M.load_inputs()
        self.assertEqual(len(basis), M.DIMENSION)
        self.assertEqual(len(vector), M.DIMENSION)
        self.assertEqual(row["name"], "D14_grid_1e-38")
        self.assertEqual(fine["status"],
                         "EXACT D14 FINE COMMON-GRID PARTICULAR VECTORS PASS")
        self.assertEqual(one_band["status"],
                         "EXACT TRUNCATED ONE-OUTER-BAND ENERGY SUPPORT PASS")
        self.assertEqual(M.ACTIVE_COUNTS, tuple(range(13)))
        self.assertTrue(all((M.VECTOR_SCALE * value).denominator == 1
                            for value in vector))
        with self.assertRaises(ValueError):
            M.build_shard(13)

    def test_natural_dilation_literal_point_identity(self):
        basis = (
            (0, ()), (1, ()), (2, ()),
            (0, (2,)), (1, (2,)),
        )
        vector = (Q(3, 7), Q(-2, 5), Q(11, 13), Q(7, 17), Q(-5, 19))
        dilation = Q(5, 7)
        common = M.natural_dilation_common_vector(basis, vector, dilation)
        scaled = M.natural_dilation_common_vector(
            basis, tuple(M.VECTOR_SCALE * x for x in vector), dilation)
        self.assertEqual(scaled,
                         tuple(M.VECTOR_SCALE * x for x in common))
        for point in ((Q(1, 11), Q(2, 13), Q(1, 17)),
                      (Q(0), Q(1, 8), Q(3, 20))):
            scaled = tuple(dilation * x for x in point)
            self.assertEqual(polynomial_value(basis, vector, scaled),
                             polynomial_value(basis, common, point))
        for center in (Q(2, 3), Q(3, 4)):
            self.assertEqual(
                M.centered_from_common(basis, common, center),
                M.centered_direct_from_original(
                    basis, vector, dilation, center))

    def test_grouped_per_count_equals_literal_stratum_quadratic_low_k(self):
        exact, stratum, grouped = M.load_integrators()

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
        basis = ((0, ()), (1, ()), (0, (2,)))
        vector = (Q(2, 3), Q(-3, 7), Q(5, 11))

        def make(alpha):
            return Support(k, alpha, delta, eta,
                           schedule[0], schedule[1], schedule[2], schedule)

        totals = []
        for count in range(k + 1):
            values = []
            for support in (make(Q(3, 4)), make(Q(2, 3))):
                evaluator = grouped.GroupedEvaluator(
                    support, basis, vector, Q)
                by_orbit = evaluator.square_residual_terms()
                grouped_value, _ = evaluator.evaluate_i_r(
                    by_orbit, count, False)
                literal = sum(
                    vector[i] * vector[j] *
                    support.basis_m1_in_strata(
                        count, basis[i], count, basis[j])
                    for i in range(len(basis)) for j in range(len(basis)))
                self.assertEqual(grouped_value, literal)
                values.append(grouped_value)
            self.assertGreaterEqual(values[0] - values[1], 0)
            totals.append(values[0] - values[1])
        self.assertGreater(sum(totals, Q(0)), 0)

    def test_exclusive_publication(self):
        payload = b'{"status":"test"}\n'
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "shard.json"
            M.publish_exclusive(path, payload)
            self.assertEqual(path.read_bytes(), payload)
            with self.assertRaises(FileExistsError):
                M.publish_exclusive(path, payload)
        self.assertEqual(M.sha256(payload), hashlib.sha256(payload).hexdigest())


if __name__ == "__main__":
    unittest.main()
