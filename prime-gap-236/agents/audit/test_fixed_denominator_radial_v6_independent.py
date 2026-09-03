#!/usr/bin/env python3
"""Hostile independent tests for fixed-denominator radialization v6.

The principal oracle below enumerates literal monomials in an orbit and the
Cartesian large/small expansions.  It does not call the v3 radial transform
or either falling-factorial helper from v6.
"""

from __future__ import annotations

from collections import defaultdict
from fractions import Fraction as Q
import hashlib
import importlib.util
from itertools import product, permutations
import math
from pathlib import Path
import random
import sys
import unittest


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
ENGINE_DIR = REPO / "agents/exact-projection-engine"
V6_PATH = ENGINE_DIR / "fixed_denominator_radial.py"
RUNNER_PATH = ENGINE_DIR / "d14_grid38_scaled_b_shard_fixed_v6.py"
TEST_PATH = ENGINE_DIR / "test_fixed_denominator_radial.py"
EXPECTED = {
    V6_PATH: "430d6376d803abaad40c3bf9fb88d5f4db75ad144649e8c9446d47f1e771b228",
    RUNNER_PATH: "89c7c57aa439b0535bd17b85683dd1fd4ece2d1439e1b5d8bd9562c44eb57e17",
    TEST_PATH: "a02f51377800e4906e711da2cd62bd4f406999b73d8bb58dfa2e6d0eb1ed2f45",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


ENGINE = load("v6_audit_engine", ENGINE_DIR / "symmetric_cutoff_cross.py")
FAST = load("v6_audit_fast", ENGINE_DIR / "fast_tagged_scalar.py")
PRUNED = load("v6_audit_pruned", ENGINE_DIR / "pruned_integer_radial.py")
COLLECTED = load("v6_audit_collected", ENGINE_DIR / "collected_integer_scalar.py")
V6 = load("v6_audit_target", V6_PATH)
RADIAL = load("v6_audit_radial", REPO / "verify/exact_capped_certificate.py")
PRUNED.FAST_V2 = FAST
COLLECTED.FAST_V2 = FAST
COLLECTED.PRUNED_V3 = PRUNED
V6.FAST_V2 = FAST
V6.COLLECTED_V5 = COLLECTED


def unique_permutations(values):
    return set(permutations(values))


def literal_orbit_radial(part, n, r, delta, maximum_shift):
    """Expand every orbit monomial and every coordinate choice literally."""
    if len(part) > n or maximum_shift < 0:
        return {}
    delta = Q(delta)
    s = n - r
    answer = defaultdict(Q)
    for exponents in unique_permutations(tuple(part) + (0,) * (n-len(part))):
        large_exponents = exponents[:r]
        small_exponents = exponents[r:]

        large = defaultdict(Q)
        if not r:
            large[0] = Q(1)
        else:
            choices = []
            for exponent in large_exponents:
                choices.append(tuple(
                    (power, Q(math.comb(exponent, power)
                              * math.factorial(power))
                     * delta ** (exponent-power))
                    for power in range(exponent+1)))
            for selection in product(*choices):
                degree = sum(item[0] for item in selection)
                coefficient = math.prod((item[1] for item in selection),
                                        start=Q(1))
                power = degree+r-1
                large[power] += coefficient/math.factorial(power)

        small = defaultdict(Q)
        if not s:
            small[(0, 0)] = Q(1)
        else:
            choices = []
            for exponent in small_exponents:
                coordinate = [(0, exponent, Q(math.factorial(exponent)))]
                coordinate.extend(
                    (1, power,
                     -Q(math.comb(exponent, power)*math.factorial(power))
                     * delta**(exponent-power))
                    for power in range(exponent+1))
                choices.append(tuple(coordinate))
            for selection in product(*choices):
                shift = sum(item[0] for item in selection)
                if shift > maximum_shift:
                    continue
                degree = sum(item[1] for item in selection)
                coefficient = math.prod((item[2] for item in selection),
                                        start=Q(1))
                power = degree+s-1
                small[(shift, power)] += coefficient/math.factorial(power)

        for x_power, left in large.items():
            for (shift, y_power), right in small.items():
                # The count-r stratum is the union over all choices of which
                # r labelled coordinates are large.  Symmetry lets the
                # production code group those choices; this literal oracle
                # fixes the first r coordinates and restores their count.
                answer[(shift, x_power, y_power)] += (
                    math.comb(n, r)*left*right)
    return {key: value for key, value in answer.items() if value}


def integer_result_as_fractions(part, n, r, delta, maximum_shift,
                                maximum_degree):
    ceiling = max(0, maximum_degree+n-1)
    denominator = delta.denominator**maximum_degree*math.factorial(ceiling)
    observed = V6.partition_face_scaled_integer(
        RADIAL, part, n, r, delta, maximum_shift,
        maximum_degree=maximum_degree, factorial_ceiling=ceiling,
        common_denominator=denominator)
    return {key: Q(value, denominator) for key, value in observed.items()}


class FixedDenominatorV6IndependentAudit(unittest.TestCase):
    def test_frozen_bytes(self):
        for path, expected in EXPECTED.items():
            self.assertEqual(sha256(path), expected, str(path))

    def test_recursive_runner_source_closure(self):
        runner = load("v6_audit_runner", RUNNER_PATH)
        for path, expected in runner.LOCAL_PINNED.items():
            self.assertEqual(sha256(path), expected, str(path))
        v5_runner = load("v6_audit_v5_runner", runner.V5_RUNNER_PATH)
        for path, expected in v5_runner.LOCAL_PINNED.items():
            self.assertEqual(sha256(path), expected, str(path))
        v2_runner = load("v6_audit_v2_runner", v5_runner.V2_PATH)
        for path, expected in v2_runner.LOCAL_PINNED.items():
            self.assertEqual(sha256(path), expected, str(path))
        base = load("v6_audit_base_runner", v2_runner.BASE_PATH)
        for path, expected in base.PINNED.items():
            self.assertEqual(sha256(path), expected, str(path))
        # v6 publishes through the already-audited O_EXCL/link/fsync helper,
        # rather than the nonexclusive v2 os.replace path.
        self.assertEqual(
            sha256(v5_runner.PUBLISH_SOURCE_PATH),
            "ce5236eaed52be549a316587e8c3c543a0b02b1594c14ba32f4c1a877fd9bb26")
        self.assertEqual(
            sha256(v5_runner.PUBLISH_TEST_PATH),
            "855b3e07ee71f75917a9ddceb2d969e10aab8c81550aa036423f7104eb5ef78d")

    def test_literal_orbit_cartesian_oracle_exhaustive_small(self):
        parts = ((), (1,), (2,), (3,), (1, 1), (2, 1), (2, 2),
                 (3, 1, 1))
        for delta in (Q(1, 6), Q(2, 5), Q(7, 11)):
            for n in range(0, 6):
                valid = [part for part in parts if len(part) <= n]
                maximum_degree = max(map(sum, valid), default=0)
                for r in range(n+1):
                    for maximum_shift in range(0, min(3, n-r)+1):
                        for part in valid:
                            expected = literal_orbit_radial(
                                part, n, r, delta, maximum_shift)
                            observed = integer_result_as_fractions(
                                part, n, r, delta, maximum_shift,
                                maximum_degree)
                            self.assertEqual(observed, expected,
                                             (part, n, r, delta,
                                              maximum_shift))

    def test_target_dimension_zero_and_boundary_faces(self):
        parts = ((), (1,), (2,), (8,), (6, 4, 2),
                 (14, 10, 8, 6, 4, 2))
        n = 47
        maximum_degree = max(map(sum, parts))
        for r in (0, 1, 11, 12, 46, 47):
            for maximum_shift in (0, 1, 2, 14-r if r <= 12 else 0):
                if maximum_shift < 0:
                    continue
                for part in parts:
                    expected = PRUNED.partition_face_radial_pruned(
                        RADIAL, part, n, r, Q(1, 60), maximum_shift)
                    observed = integer_result_as_fractions(
                        part, n, r, Q(1, 60), maximum_shift,
                        maximum_degree)
                    self.assertEqual(observed, expected,
                                     (part, r, maximum_shift))
        self.assertEqual(
            integer_result_as_fractions((), 0, 0, Q(1, 60), 0, 0),
            {(0, 0, 0): Q(1)})

    def test_minimal_common_denominator_identity_random_families(self):
        rng = random.Random(236_600_048)
        available = ((), (1,), (2,), (3,), (2, 1), (2, 2), (4, 1))
        for _ in range(40):
            n = rng.randrange(1, 8)
            r = rng.randrange(n+1)
            maximum_shift = rng.randrange(0, min(3, n-r)+1)
            delta = Q(rng.randrange(1, 8), rng.randrange(9, 23))
            valid = [part for part in available if len(part) <= n]
            families = {"family": {(0, 0): {}}}
            for part in valid:
                coefficient = rng.randrange(-7, 8)
                if coefficient:
                    families["family"][(0, 0)][part] = coefficient
            observed, denominator, _ = V6.radialize_integer_families_fixed(
                RADIAL, families, number_variables=n, number_large=r,
                delta=delta, maximum_shift=maximum_shift)
            reference, reference_denominator, _ = \
                PRUNED.radialize_integer_families_pruned(
                    RADIAL, families, number_variables=n, number_large=r,
                    delta=delta, maximum_shift=maximum_shift)
            self.assertEqual(denominator, reference_denominator)
            self.assertEqual(observed, reference)

            # Independently characterize the transform denominator as the
            # LCM of literal-oracle coefficient denominators, before family
            # distribution/cancellation (the same semantic used by v3).
            literal_lcm = 1
            for part in families["family"][(0, 0)]:
                for value in literal_orbit_radial(
                        part, n, r, delta, maximum_shift).values():
                    literal_lcm = math.lcm(literal_lcm, value.denominator)
            self.assertEqual(denominator, literal_lcm)

    def test_target_geometry_full_branch_value_and_inactive_family(self):
        families = {
            "small": {(0, 0): {(): Q(2), (2,): Q(-3, 5)}},
            "small_total": {(1, 0): {(1,): Q(4, 7), (2, 1): Q(1, 3)}},
            "large": {(0, 1): {(): Q(-2, 9), (3,): Q(5, 11)}},
        }
        kwargs0 = dict(
            k=48, alpha_high=Q(9500917, 36000000),
            alpha_low=Q(103, 400), alpha_f=Q(103, 400),
            eta=Q(8960917, 36000000), delta=Q(1, 60),
            schedule=tuple(map(Q, (
                "1123/8000", "157041/1000000", "5267/31250",
                "87169/500000", "11593/62500", "1523/8000",
                "193097/1000000", "98573/500000", "202047/1000000",
                "20709/100000", "52917/250000", "52917/250000"))))
        for r in (0, 11, 12):
            kwargs = dict(kwargs0, common_r=r)
            expected, expected_diagnostics = COLLECTED.band_cross_r_integer(
                ENGINE, RADIAL, families, **kwargs)
            observed, diagnostics = V6.band_cross_r_integer(
                ENGINE, RADIAL, families, **kwargs)
            self.assertEqual(observed, expected)
            self.assertEqual(diagnostics["high"],
                             expected_diagnostics["high"])
            self.assertEqual(diagnostics["low"],
                             expected_diagnostics["low"])
            radial = diagnostics["integer_radialization"]
            self.assertEqual(
                radial["radial_stats"]
                ["maximum_shift_pruned_inside_convolution"], 14-r)
            if r == 12:
                self.assertEqual(radial["active_branch_families"],
                                 ["small", "small_total"])
                self.assertEqual(
                    radial["inactive_families_pruned_before_radialization"],
                    ["large"])
            else:
                self.assertEqual(radial["active_branch_families"],
                                 ["large", "small", "small_total"])

    def test_invalid_fixed_denominator_rejected(self):
        with self.assertRaisesRegex(ArithmeticError, "denominator mismatch"):
            V6.partition_face_scaled_integer(
                RADIAL, (2,), 3, 1, Q(1, 6), 1,
                maximum_degree=2, factorial_ceiling=4,
                common_denominator=6**2*math.factorial(4)+1)
        with self.assertRaisesRegex(ValueError, "delta must be positive"):
            V6.partition_face_scaled_integer(
                RADIAL, (), 1, 0, Q(0), 0,
                maximum_degree=0, factorial_ceiling=0,
                common_denominator=1)


if __name__ == "__main__":
    unittest.main()
