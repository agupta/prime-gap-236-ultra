#!/usr/bin/env python3

import importlib
import math
import random
import sys
import unittest
from pathlib import Path


HERE = Path(__file__).resolve()
CODE = HERE.parents[1] / "code"
sys.path.insert(0, str(CODE))
COND = importlib.import_module("importance_conditional")
DENSITY = importlib.import_module("importance_density")
EXACT_RESULTS = HERE.parents[2] / "exact-integrator" / "results"
PARAMETERS = EXACT_RESULTS / "c10_stratum_quadratic_cappedopt_D4_exact.json"
D4 = EXACT_RESULTS / "c10_capped_D4_decimal55_vector_input.json"


class ImportanceConditionalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.adapter = DENSITY.C10ImportanceDensity(D4, PARAMETERS)

    def test_all_i_and_j_strata_have_finite_interior_starts(self):
        for target in ("I", "J"):
            density = COND.conditional_log_density(self.adapter, target)
            for r in self.adapter.strata:
                point = COND.randomized_interior_start(
                    self.adapter, target, r, 1000 + 37 * r)
                self.assertTrue(
                    COND.conditional_support(self.adapter, target, r)(point))
                self.assertEqual(COND.point_stratum(self.adapter, point), r)
                self.assertTrue(math.isfinite(density(point)))

    def test_conditional_steps_preserve_stratum_and_both_move_types(self):
        rng = random.Random(4321)
        state = COND.randomized_interior_start(self.adapter, "J", 7, 99)
        types = set()
        accepted = 0
        for _ in range(300):
            step = COND.conditional_metropolis_step(
                self.adapter, "J", 7, state, rng, density_power=0.4)
            state = step.result.state
            types.add(step.move_type)
            accepted += int(step.result.accepted)
            self.assertEqual(COND.point_stratum(self.adapter, state), 7)
        self.assertEqual(types, {"physical-slack", "physical-physical"})
        self.assertGreater(accepted, 0)

    def test_fail_closed_arguments(self):
        with self.assertRaises(ValueError):
            COND.conditional_support(self.adapter, "I", 16)
        with self.assertRaises(ValueError):
            COND.randomized_interior_start(self.adapter, "bad", 0, 1)
        with self.assertRaises(ValueError):
            COND.choose_mixed_pair(1, random.Random(0))
        with self.assertRaises(ValueError):
            COND.choose_mixed_pair(4, random.Random(0), 1.0)

    def test_power_zero_rejects_represented_zero_density_candidate(self):
        class FakeAdapter:
            k = 2
            alpha = 1.0
            eta = 0.5
            delta = 0.8
            strata = (0,)

            @staticmethod
            def i_support(point):
                return (len(point) == 2 and min(point) >= 0 and
                        sum(point) < 1 and max(point) <= 0.8)

            @staticmethod
            def i_log_density(point):
                return 0.0 if max(point) < 0.5 else -math.inf

        class ForcedRng:
            def __init__(self):
                self.draws = iter((0.1, 0.6))

            def random(self):
                return next(self.draws)

            @staticmethod
            def randrange(_dimension):
                return 0

            @staticmethod
            def sample(_population, _count):
                raise AssertionError("forced move must select slack")

        state = (0.1, 0.1)
        step = COND.conditional_metropolis_step(
            FakeAdapter(), "I", 0, state, ForcedRng(), density_power=0)
        self.assertFalse(step.result.accepted)
        self.assertTrue(step.result.support_rejected)
        self.assertEqual(step.result.state, state)


if __name__ == "__main__":
    unittest.main()
