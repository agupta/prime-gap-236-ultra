#!/usr/bin/env python3
"""Independent exact adversarial checks for ``fast_tagged_scalar.py``.

Expected cross values come from the literal polygon oracle in
``test_symmetric_cutoff_cross_independent.py``.  This file separately checks
the ordinary fast path and the common-denominator integer path; it does not
let equality with the older radial contraction stand in for a literal test.
"""

from __future__ import annotations

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


O = load(
    "fast_hostile_literal_oracle",
    HERE / "test_symmetric_cutoff_cross_independent.py",
)
FAST = load(
    "fast_hostile_target",
    REPO / "agents/exact-projection-engine/fast_tagged_scalar.py",
)

ZERO = Q(0)
ONE = Q(1)


def build_families(inner_terms, outer_terms, alpha_f, delta, k=2):
    marginal = O.M.marginal_polynomial(
        O.F.ei, tuple(inner_terms), tuple(inner_terms.values()), k, alpha_f,
    )
    components = O.M.distinguished_components(
        O.F.ei, tuple(outer_terms), tuple(outer_terms.values()), k,
    )
    kernel, _ = O.M.global_cross_kernel(O.F.ei, marginal, components)
    families, _ = O.M.primitive_tagged_families(
        kernel, alpha_f=alpha_f, delta=delta,
    )
    return families


def fast_rows(families, geometry, integer):
    function = FAST.band_cross_r_integer if integer else FAST.band_cross_r
    total = ZERO
    rows = {}
    for r in (0, 1):
        value, row = function(
            O.M, O.R, families, k=2,
            alpha_high=geometry["alpha_high"],
            alpha_low=geometry["alpha_low"],
            alpha_f=geometry["alpha_f"], eta=geometry["eta"],
            delta=geometry["delta"], schedule=geometry["schedule"],
            common_r=r,
        )
        total += value
        rows[r] = row
    return total, rows


class FastTaggedScalarHostileAudit(unittest.TestCase):
    maxDiff = None

    def assert_fast_literal(self, inner_terms, outer_terms, geometry):
        families = build_families(
            inner_terms, outer_terms, geometry["alpha_f"], geometry["delta"],
        )
        poly = O.marginal_times_outer(
            inner_terms, outer_terms, geometry["alpha_f"],
        )
        high = O.direct_cross_endpoint(
            poly, alpha=geometry["alpha_high"], eta=geometry["eta"],
            delta=geometry["delta"], schedule=geometry["schedule"],
        )
        low = O.direct_cross_endpoint(
            poly, alpha=geometry["alpha_low"], eta=geometry["eta"],
            delta=geometry["delta"], schedule=geometry["schedule"],
        )
        raw = sum(
            high[r][branch] - low[r][branch]
            for r in (0, 1) for branch in O.M.BRANCHES
        )
        expected = 2 * raw
        for integer in (False, True):
            observed, rows = fast_rows(families, geometry, integer)
            self.assertEqual(observed, expected, (integer, "band"))
            for r in (0, 1):
                for branch in O.M.BRANCHES:
                    self.assertEqual(
                        rows[r]["high"].get(branch, ZERO),
                        high[r][branch],
                        (integer, r, branch, "high"),
                    )
                    self.assertEqual(
                        rows[r]["low"].get(branch, ZERO),
                        low[r][branch],
                        (integer, r, branch, "low"),
                    )

    def test_all_basis_pairs_against_literal_polygons(self):
        geometry = dict(O.IndependentLiteralCrossAudit.GEOMETRY)
        for inner_label in O.IndependentLiteralCrossAudit.BASIS:
            for outer_label in O.IndependentLiteralCrossAudit.BASIS:
                self.assert_fast_literal(
                    {inner_label: ONE}, {outer_label: ONE}, geometry,
                )

    def test_random_coefficients_and_geometries_against_literal_polygons(self):
        generator = random.Random(236_048_125)
        labels = O.IndependentLiteralCrossAudit.BASIS
        for case in range(16):
            delta_units = generator.choice((8, 10, 12))
            low_units = generator.randint(34, 43)
            geometry = dict(
                alpha_f=Q(low_units, 120),
                alpha_low=Q(low_units, 120),
                alpha_high=Q(low_units + generator.randint(3, 10), 120),
                eta=Q(generator.randint(15, low_units - 1), 120),
                delta=Q(delta_units, 120),
            )
            beta1 = generator.randint(delta_units + 1, low_units + 5)
            beta2 = beta1 + generator.randint(0, delta_units)
            geometry["schedule"] = (Q(beta1, 120), Q(beta2, 120))
            inner = {
                label: Q(generator.randint(-3, 3), generator.randint(1, 7))
                for label in labels
            }
            outer = {
                label: Q(generator.randint(-3, 3), generator.randint(1, 7))
                for label in labels
            }
            inner = {key: value for key, value in inner.items() if value}
            outer = {key: value for key, value in outer.items() if value}
            self.assert_fast_literal(
                inner or {(0, ()): ONE}, outer or {(0, ()): ONE}, geometry,
            )

    def test_integer_radial_coefficients_restore_exact_reference(self):
        geometry = dict(O.IndependentLiteralCrossAudit.GEOMETRY)
        inner = {
            (0, ()): Q(2, 3), (2, ()): Q(-5, 7),
            (1, (2,)): Q(11, 13), (0, (3, 2)): Q(-7, 5),
        }
        outer = {
            (1, ()): Q(-4, 9), (0, (2,)): Q(8, 7),
            (2, (3,)): Q(-9, 11), (0, (2, 2)): Q(13, 19),
        }
        families = build_families(
            inner, outer, geometry["alpha_f"], geometry["delta"],
        )
        integers, family_denominator, _ = \
            FAST.clear_family_denominators(families)
        for family, tagged in families.items():
            for tag, polynomial in tagged.items():
                for part, coefficient in polynomial.items():
                    self.assertEqual(
                        Q(integers[family][tag][part], family_denominator),
                        coefficient,
                    )

        cutoff = geometry["eta"]
        maximum_shift = O.R._maximum_active_shift(
            cutoff, geometry["delta"],
        )
        for r in (0, 1):
            reference = O.M.radialize_tagged_families(
                O.R, families, number_variables=1, number_large=r,
                delta=geometry["delta"], maximum_shift=maximum_shift,
            )
            packed, radial_denominator, _ = FAST.radialize_integer_families(
                O.R, integers, number_variables=1, number_large=r,
                delta=geometry["delta"], maximum_shift=maximum_shift,
            )
            combined = family_denominator * radial_denominator
            for family in families:
                expected = defaultdict(Q)
                for shift, rows in reference[family].items():
                    for fp, sp, xp, yp, coefficient in rows:
                        expected[(shift, fp, sp, xp, yp)] += coefficient
                observed = defaultdict(Q)
                for shift, rows in packed[family].items():
                    for fp, sp, xp, yp, coefficient in rows:
                        observed[(shift, fp, sp, xp, yp)] += Q(
                            coefficient, combined,
                        )
                self.assertEqual(dict(observed), dict(expected), (r, family))

    def test_zero_dimensional_shared_face_has_exact_closed_form(self):
        # k=1 has no shared variables at all.  F=H=1 gives
        # J_endpoint=alpha_f*min(alpha,beta_1).  This tests the special r=s=0
        # moment code without relying on the reference radial contraction.
        k = 1
        alpha_f, low, high = Q(8, 25), Q(3, 10), Q(2, 5)
        eta, delta, schedule = Q(1, 5), Q(1, 10), (Q(7, 20),)
        families = build_families(
            {(0, ()): ONE}, {(0, ()): ONE}, alpha_f, delta, k=k,
        )
        expected = alpha_f * (min(high, schedule[0]) - min(low, schedule[0]))
        for function in (FAST.band_cross_r, FAST.band_cross_r_integer):
            observed, row = function(
                O.M, O.R, families, k=k, alpha_high=high,
                alpha_low=low, alpha_f=alpha_f, eta=eta, delta=delta,
                schedule=schedule, common_r=0,
            )
            self.assertEqual(observed, expected)
            self.assertEqual(
                sum(row["high"].values(), ZERO)
                - sum(row["low"].values(), ZERO),
                expected,
            )


if __name__ == "__main__":
    unittest.main()
