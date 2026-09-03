#!/usr/bin/env python3
"""Independent low-k hostile tests for paired-face exact A production."""

from __future__ import annotations

from dataclasses import dataclass
from collections import defaultdict
from fractions import Fraction as Q
import importlib.util
from pathlib import Path
import random
import sys
import unittest


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


M = load(
    "hostile_a_v2_target",
    REPO / "agents/structural-basis/code/exact_d14_one_band_a_shard_v2.py",
)
O = load(
    "hostile_a_v2_literal_oracle",
    HERE / "test_symmetric_cutoff_cross_independent.py",
)
EXACT, STRATUM, GROUPED = M.B.load_integrators()


@dataclass(frozen=True)
class Support(STRATUM.StratumSupport):
    schedule: tuple[Q, ...] = ()

    def beta(self, count):
        if count <= 0:
            raise ValueError(count)
        return self.schedule[min(count, len(self.schedule)) - 1]


def support(k, alpha, delta, schedule):
    schedule = tuple(schedule)
    return Support(
        k, Q(alpha), Q(delta), Q(1, 2),
        schedule[0], schedule[min(1, len(schedule) - 1)],
        schedule[min(2, len(schedule) - 1)], schedule,
    )


def literal_values(basis, vector, *, high_alpha, low_alpha, delta, schedule):
    terms = defaultdict(Q)
    for label, coefficient in zip(basis, vector, strict=True):
        terms[label] += coefficient
    terms = {label: coefficient for label, coefficient in terms.items()
             if coefficient}
    polynomial = O.terms_poly_2(terms)
    squared = O.multiply_poly(polynomial, polynomial)
    high = [
        O.direct_i_stratum(
            squared, alpha=high_alpha, delta=delta, schedule=schedule,
            number_large=count,
        )
        for count in range(3)
    ]
    low = [
        O.direct_i_stratum(
            squared, alpha=low_alpha, delta=delta, schedule=schedule,
            number_large=count,
        )
        for count in range(3)
    ]
    return high, low


class PairedExactAHostileAudit(unittest.TestCase):
    BASIS = (
        (0, ()), (1, ()), (2, ()), (0, (2,)),
        (1, (2,)), (0, (3,)), (0, (2, 2)), (0, (3, 2)),
    )

    def assert_literal(self, basis, vector, geometry):
        high_support = support(
            2, geometry["high_alpha"], geometry["delta"],
            geometry["schedule"],
        )
        low_support = support(
            2, geometry["low_alpha"], geometry["delta"],
            geometry["schedule"],
        )
        high_expected, low_expected = literal_values(
            basis, vector, **geometry,
        )
        for count in range(3):
            row = M.paired_evaluate(
                GROUPED, high_support, low_support, basis, vector,
                count, False,
            )
            self.assertEqual(row[0], high_expected[count], (count, "high"))
            self.assertEqual(row[1], low_expected[count], (count, "low"))
            self.assertGreaterEqual(row[0] - row[1], 0)

    def test_every_basis_pair_cap_multiplicity_and_alpha_dependence(self):
        geometry = dict(
            high_alpha=Q(39, 100), low_alpha=Q(31, 100),
            delta=Q(1, 10), schedule=(Q(23, 100), Q(31, 100)),
        )
        # Squaring each two-term polynomial makes the cross-orbit
        # multiplicities observable, including repeated/distinct exponents.
        for left in self.BASIS:
            for right in self.BASIS:
                self.assert_literal(
                    (left, right), (Q(2, 3), Q(-5, 7)), geometry,
                )

    def test_random_vectors_geometries_and_common_max_h(self):
        generator = random.Random(236_014_076)
        for case in range(16):
            # Both endpoints lie strictly in (0.3,0.4), so floor(alpha/delta)
            # is the common value 3, while the endpoint radii really differ.
            low_units = generator.randint(31, 36)
            high_units = generator.randint(low_units + 1, 39)
            # Keep every k=2 count active; the target paired producer is
            # intentionally restricted to its active counts as well.
            beta1_units = generator.randint(21, 28)
            beta2_units = beta1_units + generator.randint(0, 10)
            geometry = dict(
                high_alpha=Q(high_units, 100),
                low_alpha=Q(low_units, 100),
                delta=Q(1, 10),
                schedule=(Q(beta1_units, 100), Q(beta2_units, 100)),
            )
            vector = tuple(
                Q(generator.randint(-4, 4), generator.randint(1, 9))
                for _ in self.BASIS
            )
            if not any(vector):
                vector = (Q(1),) + vector[1:]
            self.assert_literal(self.BASIS, vector, geometry)

    def test_reuse_rejects_different_face_combinatorics_or_cap(self):
        basis, vector = ((0, ()),), (Q(1),)
        delta = Q(1, 10)
        schedule = (Q(1, 4), Q(3, 10))
        # Floors 3 and 2 differ, hence so do the inclusion-exclusion face sets.
        high = support(2, Q(31, 100), delta, schedule)
        low = support(2, Q(29, 100), delta, schedule)
        with self.assertRaisesRegex(ArithmeticError, "face combinatorics"):
            M.paired_evaluate(GROUPED, high, low, basis, vector, 0, False)

        high = support(2, Q(39, 100), delta, schedule)
        low = support(2, Q(31, 100), delta,
                      (Q(6, 25), Q(3, 10)))
        with self.assertRaisesRegex(ArithmeticError, "cap mismatch"):
            M.paired_evaluate(GROUPED, high, low, basis, vector, 1, False)

        different_delta = support(
            2, Q(31, 100), Q(1, 20), schedule,
        )
        with self.assertRaisesRegex(ArithmeticError, "face combinatorics"):
            M.paired_evaluate(
                GROUPED, high, different_delta, basis, vector, 0, False,
            )


if __name__ == "__main__":
    unittest.main()
