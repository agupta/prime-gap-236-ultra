#!/usr/bin/env python3
"""Independent cache-safety and exact-identity tests for cached radial v7."""

from __future__ import annotations

from fractions import Fraction as Q
import hashlib
import importlib.util
import math
from pathlib import Path
import random
import sys
import unittest


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
ENGINE_DIR = REPO / "agents/exact-projection-engine"
V7_PATH = ENGINE_DIR / "cached_fixed_denominator_radial.py"
RUNNER_PATH = ENGINE_DIR / "d14_grid38_scaled_b_shard_cached_v7.py"
TEST_PATH = ENGINE_DIR / "test_cached_fixed_denominator_radial.py"
EXPECTED = {
    V7_PATH: "79c9a8ef26de0b7fba55fbdb6e113a88f0b52b20f9cbcb34cbc2dbb507ba74c4",
    RUNNER_PATH: "b427c6961c377cb79d5a72b54f8c2e8c7642b87d66d338f53b5dc56d98991984",
    TEST_PATH: "0f0bd15426ff961e47281b32d57795f1848e75280fd645abc599df8d1410fd5b",
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


FIXED = load("v7_audit_fixed", ENGINE_DIR / "fixed_denominator_radial.py")
V7 = load("v7_audit_target", V7_PATH)
RADIAL = load("v7_audit_radial", REPO / "verify/exact_capped_certificate.py")
V7.FIXED_V6 = FIXED


def fixed_call(part, n, r, delta, h, maximum_degree):
    ceiling = max(0, maximum_degree+n-1)
    denominator = delta.denominator**maximum_degree*math.factorial(ceiling)
    kwargs = dict(maximum_degree=maximum_degree,
                  factorial_ceiling=ceiling,
                  common_denominator=denominator)
    return (
        FIXED.partition_face_scaled_integer(
            RADIAL, part, n, r, delta, h, **kwargs),
        V7.partition_face_scaled_integer(
            RADIAL, part, n, r, delta, h, **kwargs),
    )


class CachedV7IndependentAudit(unittest.TestCase):
    def test_frozen_recursive_source_and_publisher_closure(self):
        for path, expected in EXPECTED.items():
            self.assertEqual(digest(path), expected, str(path))
        runner = load("v7_audit_runner", RUNNER_PATH)
        for path, expected in runner.LOCAL_PINNED.items():
            self.assertEqual(digest(path), expected, str(path))
        v6 = load("v7_audit_v6_runner", runner.V6_RUNNER_PATH)
        for path, expected in v6.LOCAL_PINNED.items():
            self.assertEqual(digest(path), expected, str(path))
        v5 = load("v7_audit_v5_runner", v6.V5_RUNNER_PATH)
        for path, expected in v5.LOCAL_PINNED.items():
            self.assertEqual(digest(path), expected, str(path))
        v2 = load("v7_audit_v2_runner", v5.V2_PATH)
        for path, expected in v2.LOCAL_PINNED.items():
            self.assertEqual(digest(path), expected, str(path))
        base = load("v7_audit_base_runner", v2.BASE_PATH)
        for path, expected in base.PINNED.items():
            self.assertEqual(digest(path), expected, str(path))
        self.assertEqual(
            digest(v5.PUBLISH_SOURCE_PATH),
            "ce5236eaed52be549a316587e8c3c543a0b02b1594c14ba32f4c1a877fd9bb26")

    def test_cold_and_warm_alternating_calls_equal_v6(self):
        cases = []
        parts = ((), (1,), (2,), (3, 1), (4, 2), (2, 2, 1))
        for delta in (Q(1, 60), Q(2, 9), Q(7, 31)):
            for n in range(0, 7):
                valid = [part for part in parts if len(part) <= n]
                degree = max(map(sum, valid), default=0)
                for r in range(n+1):
                    for part in valid:
                        cases.append((part, n, r, delta,
                                      min(3, n-r), degree))
        rng = random.Random(7_236_048)
        rng.shuffle(cases)
        for repeat in range(2):
            if repeat == 0:
                V7._factorials_through.cache_clear()
                V7._factorial_ratio.cache_clear()
                V7._delta_scales.cache_clear()
            for case in cases:
                expected, observed = fixed_call(*case)
                self.assertEqual(observed, expected, case)
            cases.reverse()

    def test_cache_keys_and_values_are_complete_and_immutable(self):
        self.assertEqual(V7._factorials_through(6),
                         (1, 1, 2, 6, 24, 120, 720))
        self.assertIsInstance(V7._factorials_through(6), tuple)
        self.assertEqual(V7._factorial_ratio(6, 2, 3), 60)
        # Every input on which the delta table depends changes one at a time.
        tables = {
            V7._delta_scales(1, 60, 8, 5),
            V7._delta_scales(2, 60, 8, 5),
            V7._delta_scales(1, 61, 8, 5),
            V7._delta_scales(1, 60, 9, 5),
            V7._delta_scales(1, 60, 8, 4),
        }
        self.assertEqual(len(tables), 5)
        self.assertTrue(all(isinstance(table, tuple) for table in tables))

    def test_random_family_maps_denominators_and_rows_equal_v6(self):
        rng = random.Random(700_600_048)
        parts = ((), (1,), (2,), (3,), (2, 1), (4, 2), (2, 2, 1))
        for _ in range(40):
            n = rng.randrange(1, 9)
            r = rng.randrange(n+1)
            families = {"small": {(0, 0): {}}, "large": {(1, 2): {}}}
            for part in parts:
                if len(part) <= n:
                    family = "small" if rng.randrange(2) else "large"
                    coefficient = rng.randrange(-9, 10)
                    if coefficient:
                        families[family][next(iter(families[family]))][part] = \
                            coefficient
            kwargs = dict(number_variables=n, number_large=r,
                          delta=Q(rng.randrange(1, 8), rng.randrange(9, 24)),
                          maximum_shift=min(3, n-r))
            expected = FIXED.radialize_integer_families_fixed(
                RADIAL, families, **kwargs)
            observed = V7.radialize_integer_families_fixed(
                RADIAL, families, **kwargs)
            self.assertEqual(observed[:2], expected[:2])
            stats = observed[2]
            self.assertEqual(stats["cached_factorial_ratios"],
                             V7._factorial_ratio.cache_info().currsize)
            self.assertEqual(stats["cached_delta_scale_tables"],
                             V7._delta_scales.cache_info().currsize)

    def test_target_dimension_extreme_faces_and_h_boundaries(self):
        parts = ((), (2,), (8,), (6, 4, 2), (14, 10, 8, 6, 4, 2))
        degree = max(map(sum, parts))
        for r in (0, 1, 11, 12, 46, 47):
            for h in {0, 1, 2, max(0, 14-r)}:
                for part in parts:
                    expected, observed = fixed_call(
                        part, 47, r, Q(1, 60), h, degree)
                    self.assertEqual(observed, expected, (part, r, h))


if __name__ == "__main__":
    unittest.main()
