#!/usr/bin/env python3
"""Independent exact regressions for integer-weight scalar contraction."""

from fractions import Fraction as Q
import importlib.util
from pathlib import Path
import sys
import unittest


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


ENGINE = load("weight_test_engine", HERE / "symmetric_cutoff_cross.py")
FAST = load("weight_test_fast", HERE / "fast_tagged_scalar.py")
PRUNED = load("weight_test_pruned", HERE / "pruned_integer_radial.py")
TARGET = load("weight_test_target", HERE / "integer_weight_scalar.py")
RADIAL = load("weight_test_radial", REPO / "verify/exact_capped_certificate.py")
FRONTIER = load(
    "weight_test_frontier",
    REPO / "agents/small-delta-frontier/"
    "frontier_active25_inner_d16_tagged_shell.py")
PRUNED.FAST_V2 = FAST
TARGET.FAST_V2 = FAST
TARGET.PRUNED_V3 = PRUNED


class IntegerWeightScalarTest(unittest.TestCase):
    def test_manual_packed_equals_fraction_reference_on_all_domain_shapes(self):
        """Exercise denominator restoration independently of radialization."""
        packed = {
            0: (
                (0, 0, 0, 0, 7),
                (2, 1, 1, 0, -11),
                (1, 3, 0, 2, 13),
                (3, 2, 2, 1, -5),
            ),
            1: (
                (2, 2, 0, 0, 17),
                (1, 0, 2, 1, -19),
                (0, 3, 1, 2, 23),
            ),
            # This shift is deliberately outside each domain below.
            7: ((1, 1, 0, 0, 29),),
        }
        delta = Q(1, 11)
        affines = (
            ((Q(2, 7), Q(-3, 5), Q(4, 9)),
             (Q(5, 13), Q(2, 3), Q(-7, 8))),
            ((Q(-1, 6), Q(5, 12), Q(5, 12)),
             (Q(7, 10), Q(5, 12), Q(5, 12))),
        )
        cases = (
            (2, 3, RADIAL.AggregateDomain(Q(5, 11))),
            (2, 3, RADIAL.AggregateDomain(Q(5, 11), x_bound=Q(3, 11))),
            (2, 3, RADIAL.AggregateDomain(Q(5, 11), y_lower=Q(1, 11))),
            (2, 3, RADIAL.AggregateDomain(Q(5, 11), y_upper=Q(2, 11))),
            (2, 3, RADIAL.AggregateDomain(Q(5, 11), total_lower=Q(2, 11))),
            (0, 3, RADIAL.AggregateDomain(Q(5, 11), y_lower=Q(1, 11))),
            (2, 0, RADIAL.AggregateDomain(Q(5, 11), x_bound=Q(3, 11))),
        )
        for first, second in affines:
            for r, s, domain in cases:
                # Remove forbidden aggregate powers in zero-dimensional cases.
                allowed = {
                    shift: tuple(term for term in terms
                                 if not (r == 0 and term[2])
                                 and not (s == 0 and term[3]))
                    for shift, terms in packed.items()}
                expected, expected_stats = FAST.integrate_packed(
                    RADIAL, allowed, r=r, s=s, delta=delta,
                    domain=domain, first_affine=first,
                    second_affine=second)
                observed, stats = TARGET.integrate_packed_integer_weights(
                    RADIAL, allowed, r=r, s=s, delta=delta,
                    domain=domain, first_affine=first,
                    second_affine=second)
                self.assertEqual(observed, expected)
                self.assertEqual(stats["active_shifts"],
                                 expected_stats["active_shifts"])
                self.assertEqual(stats["scalar_products"],
                                 expected_stats["scalar_products"])

    def test_zero_dimensional_point_and_empty_boundary(self):
        packed = {0: ((0, 0, 0, 0, 9),), 1: ((0, 0, 0, 0, -4),)}
        first = (Q(2, 3), Q(7, 5), Q(-3, 8))
        second = (Q(5, 7), Q(-2, 9), Q(11, 13))
        domains = (
            RADIAL.AggregateDomain(Q(0)),
            RADIAL.AggregateDomain(Q(0), x_bound=Q(-1, 17)),
            RADIAL.AggregateDomain(Q(1, 10), y_lower=Q(0)),
            RADIAL.AggregateDomain(Q(1, 10), total_lower=Q(0)),
        )
        for domain in domains:
            expected, _ = FAST.integrate_packed(
                RADIAL, packed, r=0, s=0, delta=Q(1, 10),
                domain=domain, first_affine=first,
                second_affine=second)
            observed, _ = TARGET.integrate_packed_integer_weights(
                RADIAL, packed, r=0, s=0, delta=Q(1, 10),
                domain=domain, first_affine=first,
                second_affine=second)
            self.assertEqual(observed, expected)

    def test_full_band_matches_frozen_pruned_v3(self):
        k = 4
        delta, alpha_f, eta = Q(1, 10), Q(7, 20), Q(29, 100)
        low_alpha, high_alpha = Q(7, 20), Q(21, 50)
        # Genuinely nonuniform and weakly increasing; all four branch types
        # occur for at least one common count.
        schedule = (Q(9, 50), Q(13, 50), Q(31, 100), Q(7, 20))
        basis = tuple(FRONTIER.ei.even_basis(6))
        inner = tuple(Q((i % 7) - 3, i + 5) for i in range(len(basis)))
        outer = tuple(Q((i % 5) - 2, i + 7) for i in range(len(basis)))
        marginal = ENGINE.marginal_polynomial(
            FRONTIER.ei, basis, inner, k, alpha_f)
        components = ENGINE.distinguished_components(
            FRONTIER.ei, basis, outer, k)
        kernel, _ = ENGINE.global_cross_kernel(
            FRONTIER.ei, marginal, components)
        families, _ = ENGINE.primitive_tagged_families(
            kernel, alpha_f=alpha_f, delta=delta)
        for r in range(k):
            expected, expected_diagnostics = PRUNED.band_cross_r_integer(
                ENGINE, RADIAL, families, k=k, alpha_high=high_alpha,
                alpha_low=low_alpha, alpha_f=alpha_f, eta=eta,
                delta=delta, schedule=schedule, common_r=r)
            observed, diagnostics = TARGET.band_cross_r_integer(
                ENGINE, RADIAL, families, k=k, alpha_high=high_alpha,
                alpha_low=low_alpha, alpha_f=alpha_f, eta=eta,
                delta=delta, schedule=schedule, common_r=r)
            self.assertEqual(observed, expected)
            self.assertEqual(diagnostics["high"],
                             expected_diagnostics["high"])
            self.assertEqual(diagnostics["low"],
                             expected_diagnostics["low"])


if __name__ == "__main__":
    unittest.main()
