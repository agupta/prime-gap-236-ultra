#!/usr/bin/env python3
"""Independent hostile checks for the frozen importance diagnostics/kernel.

This is discovery-infrastructure validation only.  It neither estimates nor
certifies a sieve quotient.  The source hashes are deliberately pinned so a
later producer edit cannot inherit this verdict silently.
"""

from __future__ import annotations

import hashlib
import math
import random
import sys
from pathlib import Path

import numpy as np


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CODE = ROOT / "agents" / "structural-basis" / "code"
TESTS = ROOT / "agents" / "structural-basis" / "tests"
RESULTS = ROOT / "agents" / "exact-integrator" / "results"
sys.path.insert(0, str(CODE))

import importance_conditional as conditional  # noqa: E402
import importance_density as density  # noqa: E402
import importance_statistics as statistics  # noqa: E402


EXPECTED_HASHES = {
    CODE / "importance_statistics.py":
        "dd7a919b23f1eedc7cbb1093612c0dabfbcce2a5f7d30407503e2cc963686d26",
    CODE / "importance_conditional.py":
        "6e502c09354eb0fedf82c90d9d5ba12d7313609dc4392c0c947ca1166bad0258",
    TESTS / "test_importance_statistics.py":
        "604c7d5b0ed89d2792732912e80db97a23530e288ed5659942ac15e7bca3ecb1",
    TESTS / "test_importance_conditional.py":
        "b379fe6c2f2a29173dfae0ea8986b70eab79e9206c56a37b1c62445fe10f8adb",
    CODE / "importance_sampler.py":
        "54c936221fff3c2f981b98fee4110abfc384cf9b3e65d759b3997ff27c9812e4",
    CODE / "importance_envelope.py":
        "7c28633e89987c6d2d3493d4f05e699914b5fb7a023d31ccb458878587bc7110",
    CODE / "importance_point_eval.py":
        "ea88f6d29b744f59ad146bdebf9b2003a2d57e40eea5b7a03fb48f2309cdfc01",
    CODE / "importance_density.py":
        "d656c788b3cbedf6029a95e74ac5a1cc9e8b6e3794ea9ca3d624af460ced9380",
    RESULTS / "c10_stratum_quadratic_cappedopt_D4_exact.json":
        "fbc8c38d2cf4241fdba03beb4251e2692e96af01ad4918c9a3a1075af2ed6e86",
    RESULTS / "c10_capped_D4_decimal55_vector_input.json":
        "2b11a18c697e9a2be61204b5493bf7a235ce4add39d853bbb4d76ef31fb4666b",
}


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def require_raises(exception, function, *args, **kwargs):
    try:
        function(*args, **kwargs)
    except exception:
        return
    except Exception as error:
        raise AssertionError(
            f"expected {exception.__name__}, got {type(error).__name__}"
        ) from error
    raise AssertionError(f"expected {exception.__name__}, no error raised")


def check_hashes():
    for path, expected in EXPECTED_HASHES.items():
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        require(actual == expected, f"source drift: {path}: {actual}")


def check_split_rhat():
    base = np.array([0.0, 2.0, 0.0, 2.0])
    values = np.stack((base, base))[:, :, None]
    answer = statistics.split_rhat(values)
    require(answer.shape == (1,), "R-hat feature shape changed")
    require(float(answer[0]) == 1.0, "identical split chains must give one")

    shifted = values.copy()
    shifted[1] += 10.0
    answer = statistics.split_rhat(shifted)
    expected = math.sqrt((1.0 + (200.0 / 3.0) / 2.0) / 2.0)
    require(math.isclose(float(answer[0]), expected, rel_tol=2e-16),
            "split chain/batch axes or between factor changed")
    require_raises(ValueError, statistics.split_rhat, np.zeros((2, 3, 1)))
    require(math.isinf(float(statistics.split_rhat(
        np.array([[[1e308], [1e308], [1e308], [1e308]],
                  [[-1e308], [-1e308], [-1e308], [-1e308]]]))[0])),
        "overflowed R-hat must fail as infinity")


def check_ess():
    batch_values = np.array(
        [[[-1.0], [0.0], [1.0], [2.0]],
         [[-1.0], [0.0], [1.0], [2.0]]])
    raw_mean = np.array([0.5])
    # Each size-two batch is represented by mean +/- 1.
    raw_second = np.array([2.5])
    answer = statistics.batch_means_ess(
        raw_mean, raw_second, batch_values, 2)
    expected = 16.0 * 2.25 / (2.0 * (10.0 / 7.0))
    require(math.isclose(float(answer[0]), expected, rel_tol=2e-16),
            "batch-size ESS factor changed")

    constant = statistics.batch_means_ess(
        np.array([3.0]), np.array([9.0]),
        np.full((2, 4, 1), 3.0), 17)
    require(float(constant[0]) == 136.0,
            "proved constant must receive total sample count")

    alternating = np.array(
        [[[-1e-3], [1e-3], [-1e-3], [1e-3]],
         [[-1e-3], [1e-3], [-1e-3], [1e-3]]])
    require_raises(
        ArithmeticError, statistics.batch_means_ess,
        np.array([0.0]), np.array([0.0]), alternating, 10)
    require_raises(
        ArithmeticError, statistics.batch_means_ess,
        np.array([10.0]), np.array([0.0]),
        np.full((2, 4, 1), 10.0), 10)
    require_raises(
        ValueError, statistics.batch_means_ess,
        np.array([0.0]), np.array([1.0]), np.zeros((1, 4, 1)), 10)


def check_joint_ratio():
    z = np.array([[0.5, 1.0, 1.5, 2.0],
                  [0.75, 1.25, 1.75, 0.25]])
    fixed = np.array([[0.2, -0.05], [-0.05, 0.3]])
    signs = np.array([[1.0, -1.0, 1.0, -1.0],
                      [-1.0, 1.0, -1.0, 1.0]])
    perturbation = signs[..., None, None] * np.array(
        [[0.002, 0.003], [0.003, -0.002]])
    y = z[..., None, None] * fixed + perturbation
    answer = statistics.ratio_matrix_delta(y, z)
    mean_y = np.mean(y, axis=(0, 1))
    mean_z = float(np.mean(z))
    expected_ratio = mean_y / mean_z
    residual = y - z[..., None, None] * expected_ratio
    expected_se = np.std(residual.reshape((8, 2, 2)), axis=0, ddof=1) / (
        mean_z * math.sqrt(8))
    require(np.array_equal(answer["ratio"], expected_ratio),
            "joint ratio mean algebra changed")
    require(np.array_equal(answer["standard_error"], expected_se),
            "joint numerator/denominator delta residual changed")

    require_raises(ArithmeticError, statistics.ratio_matrix_delta, y, -z)
    bad = y.copy()
    bad[0, 0, 0, 0] = -0.1
    require_raises(ArithmeticError, statistics.ratio_matrix_delta, bad, z)
    bad = y.copy()
    bad[0, 0, 0, 1] = 0.6
    bad[0, 0, 1, 0] = 0.6
    require_raises(ArithmeticError, statistics.ratio_matrix_delta, bad, z)
    bad = y.copy()
    bad[0, 0, 0, 1] += 0.01
    require_raises(ArithmeticError, statistics.ratio_matrix_delta, bad, z)
    require_raises(
        ArithmeticError, statistics.ratio_matrix_delta,
        np.ones((2, 4, 1, 1)), np.full((2, 4), 1e-320))


def check_generalized_root():
    a = np.diag([1.0, 1e-30, 0.0])
    b = np.diag([1.0, 2e-30, 0.0])
    answer = statistics.largest_generalized_root(
        a, b, active_indices=[0, 1])
    require(answer["rank"] == 2, "rare positive diagonal was truncated")
    require(math.isclose(answer["root"], 2.0, rel_tol=2e-15),
            "rare-coordinate generalized root changed")
    require(math.isclose(answer["root"], answer["rayleigh"], rel_tol=2e-15),
            "mapped-back Rayleigh value disagrees")
    require_raises(
        ArithmeticError, statistics.largest_generalized_root,
        np.diag([1.0, 1.0]), np.diag([1.0, 100.0]),
        active_indices=[0])
    require_raises(
        ArithmeticError, statistics.largest_generalized_root,
        np.diag([1.0, -0.1]), np.eye(2), active_indices=[0, 1])


class _FakeAdapter:
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


class _ForcedRng:
    def __init__(self, fraction):
        self.draws = iter((0.1, fraction))

    def random(self):
        return next(self.draws)

    @staticmethod
    def randrange(_dimension):
        return 0

    @staticmethod
    def sample(_population, _count):
        raise AssertionError("forced move must select slack")


def check_power_zero_boundary():
    state = (0.1, 0.1)
    rejected = conditional.conditional_metropolis_step(
        _FakeAdapter(), "I", 0, state, _ForcedRng(0.6), density_power=0)
    require(not rejected.result.accepted and rejected.result.support_rejected,
            "power zero accepted represented zero-density proposal")
    require(rejected.result.state == state, "rejected state changed")

    accepted = conditional.conditional_metropolis_step(
        _FakeAdapter(), "I", 0, state, _ForcedRng(0.2), density_power=0)
    require(accepted.result.accepted and not accepted.result.support_rejected,
            "power zero rejected positive-density supported proposal")


def check_c10_starts_and_power_zero():
    adapter = density.C10ImportanceDensity(
        RESULTS / "c10_capped_D4_decimal55_vector_input.json",
        RESULTS / "c10_stratum_quadratic_cappedopt_D4_exact.json")
    require(adapter.strata == tuple(range(16)),
            "C10 active stratum list changed")
    for target in ("I", "J"):
        dimension = adapter.k if target == "I" else adapter.k - 1
        upper = adapter.alpha if target == "I" else adapter.eta
        log_density = conditional.conditional_log_density(adapter, target)
        for r in adapter.strata:
            point = conditional.randomized_interior_start(
                adapter, target, r, 17000 + 101 * r)
            require(len(point) == dimension, "initializer dimension mismatch")
            require(0 <= sum(point) < upper,
                    "initializer did not retain strict simplex interior")
            large = [x for x in point if x > adapter.delta]
            small = [x for x in point if x <= adapter.delta]
            require(len(large) == r, "initializer returned wrong stratum")
            require(all(x > adapter.delta for x in large),
                    "large initializer coordinate hit threshold")
            require(all(0 <= x < adapter.delta for x in small),
                    "small initializer coordinate hit threshold")
            if r:
                require(sum(large) < adapter.beta(r),
                        "initializer lacks strict cap reserve")
            require(conditional.conditional_support(adapter, target, r)(point),
                    "initializer failed its conditional support")
            require(math.isfinite(float(log_density(point))),
                    "initializer target density is not positive")

        for r in (0, 7, 15):
            state = conditional.randomized_interior_start(
                adapter, target, r, 33000 + 41 * r)
            rng = random.Random(44000 + 53 * r + (target == "J"))
            accepted = 0
            move_types = set()
            for _ in range(80):
                step = conditional.conditional_metropolis_step(
                    adapter, target, r, state, rng, density_power=0)
                move_types.add(step.move_type)
                if not step.result.support_rejected:
                    require(step.result.accepted,
                            "finite supported power-zero move was not accepted")
                    accepted += 1
                state = step.result.state
                require(conditional.point_stratum(adapter, state) == r,
                        "conditional move escaped its fixed stratum")
                require(math.isfinite(float(log_density(state))),
                        "power-zero chain entered represented zero density")
            require(accepted > 0, "power-zero fixture had no accepted proposal")
            require(move_types == {"physical-slack", "physical-physical"},
                    "mixed proposal did not exercise both move channels")


def main():
    check_hashes()
    check_split_rhat()
    check_ess()
    check_joint_ratio()
    check_generalized_root()
    check_power_zero_boundary()
    check_c10_starts_and_power_zero()
    print("AUDIT PASS: pinned importance statistics/conditional checks")


if __name__ == "__main__":
    main()
