#!/usr/bin/env python3

import importlib.util
import math
import random
import sys
import unittest
from fractions import Fraction
from pathlib import Path


HERE = Path(__file__).resolve()
MODULE_PATH = HERE.parents[1] / "code" / "importance_sampler.py"
SPEC = importlib.util.spec_from_file_location("importance_sampler", MODULE_PATH)
MOD = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = MOD
SPEC.loader.exec_module(MOD)


class ImportanceSamplerTests(unittest.TestCase):
    def test_exact_forward_reverse_with_slack(self):
        state = (Fraction(1, 10), Fraction(1, 5), Fraction(1, 20))
        upper = Fraction(1, 2)
        for pair in ((0, 1), (0, 3), (1, 3), (1, 2)):
            candidate = MOD.redistribute_pair(
                state, upper, pair, Fraction(7, 19))
            reverse = MOD.reverse_fraction(state, candidate, upper, pair)
            recovered = MOD.redistribute_pair(candidate, upper, pair, reverse)
            self.assertEqual(recovered, state)
            old_augmented = state + (MOD.simplex_slack(state, upper),)
            new_augmented = candidate + (MOD.simplex_slack(candidate, upper),)
            total_old = old_augmented[pair[0]] + old_augmented[pair[1]]
            total_new = new_augmented[pair[0]] + new_augmented[pair[1]]
            self.assertEqual(total_old, total_new)
            # Conditional proposal density is 1/total in both directions.
            self.assertEqual(1 / total_old, 1 / total_new)

    def test_constant_density_accepts_every_feasible_proposal(self):
        state = (0.1, 0.2, 0.05)
        result = MOD.metropolis_step(
            state, 0.5, lambda _: 0.0, lambda _: True,
            random.Random(1), pair=(0, 3), fraction=0.7,
            log_uniform=-0.01)
        self.assertTrue(result.accepted)
        self.assertFalse(result.support_rejected)

    def test_metropolis_accept_reject_and_support_reject(self):
        state = (0.1, 0.2)
        density = lambda x: -10.0 * x[0]
        support = lambda x: x[0] <= 0.25
        better = MOD.metropolis_step(
            state, 0.5, density, support, pair=(0, 2), fraction=0.0,
            log_uniform=-0.001)
        self.assertTrue(better.accepted)
        worse = MOD.metropolis_step(
            better.state, 0.5, density, support, pair=(0, 2), fraction=0.8,
            log_uniform=-0.001)
        self.assertFalse(worse.accepted)
        outside = MOD.metropolis_step(
            state, 0.5, density, support, pair=(0, 2), fraction=1.0,
            log_uniform=-100.0)
        self.assertTrue(outside.support_rejected)
        self.assertEqual(outside.state, state)

    def test_density_power_zero_handles_zero_density(self):
        state = (0.1, 0.2)
        result = MOD.metropolis_step(
            state, 0.5, lambda _: -math.inf, lambda _: True,
            pair=(0, 2), fraction=0.4, density_power=0,
            log_uniform=-0.1)
        self.assertTrue(result.accepted)
        chain = MOD.run_chain(
            state, 0.5, lambda _: -math.inf, lambda _: True,
            5, 7, density_power=0)
        self.assertEqual(chain["accepted"], 5)
        self.assertEqual(chain["final_log_density"], -math.inf)

    def test_seeded_chain_is_reproducible_and_stays_in_simplex(self):
        args = dict(
            initial=(0.1, 0.1, 0.1), upper=0.5,
            log_density=lambda x: -sum(y*y for y in x),
            support_predicate=lambda x: sum(x) <= 0.5 and max(x) <= 0.3,
            steps=200, seed=902, record_every=7)
        first = MOD.run_chain(**args)
        second = MOD.run_chain(**args)
        self.assertEqual(first, second)
        self.assertEqual(len(first["samples"]), 200 // 7)
        for state in first["samples"]:
            self.assertLessEqual(sum(state), 0.5 + 1e-15)
            self.assertLessEqual(max(state), 0.3)

    def test_fail_closed_arguments(self):
        with self.assertRaises(ValueError):
            MOD.redistribute_pair((0.1,), 0.5, (0, 2), 0.5)
        with self.assertRaises(ValueError):
            MOD.metropolis_step((0.1,), 0.5, lambda _: 0,
                                lambda _: True, density_power=-1)
        with self.assertRaises(ValueError):
            MOD.run_chain((0.6,), 0.5, lambda _: 0, lambda _: True,
                          10, 1)
        with self.assertRaises(ValueError):
            MOD.metropolis_step((0.1,), 0.5, lambda _: 0,
                                lambda _: True, density_power=math.nan)
        with self.assertRaises(ValueError):
            MOD.simplex_slack((math.nan,), 0.5)
        with self.assertRaises(ValueError):
            MOD.simplex_slack((0.1,), "0.5")
        with self.assertRaises(ValueError):
            MOD.redistribute_pair((0.1,), 0.5, iter((0, 1)), 0.5)
        with self.assertRaises(ValueError):
            MOD.redistribute_pair((0.1,), 0.5, (0, 1), "0.5")
        with self.assertRaises(ArithmeticError):
            MOD.metropolis_step((0.1,), 0.5, lambda _: math.inf,
                                lambda _: True)
        with self.assertRaises(ValueError):
            MOD.metropolis_step((0.1,), 0.5, lambda x: -x[0],
                                lambda _: True, pair=(0, 1), fraction=1,
                                log_uniform=math.nan)
        with self.assertRaises(ValueError):
            MOD.metropolis_step((0.1,), 0.5, lambda x: x[0],
                                lambda _: True, pair=(0, 1), fraction=1,
                                log_uniform=math.nan)

    def test_float_boundary_drift_is_rejected_not_returned(self):
        state = (0.08713125686893501,
                 0.14560806566611612,
                 0.02026067746494888)
        upper = 0.253
        pair = (0, 1)
        fraction = 0.03588663142896331
        self.assertEqual(sum(state), upper)
        with self.assertRaises(MOD.NumericalSimplexDrift):
            MOD.redistribute_pair(state, upper, pair, fraction)
        result = MOD.metropolis_step(
            state, upper, lambda _: 0.0, lambda _: True,
            pair=pair, fraction=fraction)
        self.assertFalse(result.accepted)
        self.assertTrue(result.support_rejected)
        self.assertEqual(result.state, state)
        self.assertEqual(MOD.simplex_slack(result.state, upper), 0.0)

    def test_reverse_fraction_rejects_tiny_changed_pair_total(self):
        original = (1e-20, 0.0)
        candidate = (2e-20, 0.0)
        with self.assertRaisesRegex(ArithmeticError, "pair total changed"):
            MOD.reverse_fraction(original, candidate, 0.5, (0, 1))
        with self.assertRaisesRegex(ArithmeticError, "pair total changed"):
            MOD.reverse_fraction(original, (0.0, 0.0), 0.5, (0, 1))
        with self.assertRaisesRegex(ArithmeticError, "pair total changed"):
            MOD.reverse_fraction(
                (Fraction(1, 10**20), Fraction(0)),
                (Fraction(2, 10**20), Fraction(0)),
                Fraction(1, 2), (0, 1))


if __name__ == "__main__":
    unittest.main()
