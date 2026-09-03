#!/usr/bin/env python3
"""Independent exact tests for global affine--radial product collection."""

from fractions import Fraction as Q
import hashlib
import importlib.util
import json
from pathlib import Path
import random
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


ENGINE = load("collect_test_engine", HERE / "symmetric_cutoff_cross.py")
FAST = load("collect_test_fast", HERE / "fast_tagged_scalar.py")
PRUNED = load("collect_test_pruned", HERE / "pruned_integer_radial.py")
WEIGHT = load("collect_test_weight", HERE / "integer_weight_scalar.py")
TARGET = load("collect_test_target", HERE / "collected_integer_scalar.py")
RADIAL = load("collect_test_radial", REPO / "verify/exact_capped_certificate.py")
FRONTIER = load(
    "collect_test_frontier",
    REPO / "agents/small-delta-frontier/"
    "frontier_active25_inner_d16_tagged_shell.py")
PRUNED.FAST_V2 = FAST
WEIGHT.FAST_V2 = FAST
WEIGHT.PRUNED_V3 = PRUNED
TARGET.FAST_V2 = FAST
TARGET.PRUNED_V3 = PRUNED


class CollectedIntegerScalarTest(unittest.TestCase):
    def test_frozen_r0_cost_inventory_distinguishes_two_counters(self):
        artifact = (HERE / "results/d14_grid38_scaled_b_fast_v2/"
                    "common_r_00.json")
        raw = artifact.read_bytes()
        self.assertEqual(
            hashlib.sha256(raw).hexdigest(),
            "6594f8a5e4079907a065e5fae434cf4ecb2710ffb72de7e1af451d60676f50ea")
        result = json.loads(raw)
        diagnostics = result["branch_values_and_fast_stats"]
        scalar_products = sum(
            branch["scalar_products"]
            for endpoint in ("high_stats", "low_stats")
            for branch in diagnostics[endpoint].values())
        distributed_terms = diagnostics["integer_radialization"][
            "radial_stats"]["distributed_terms"]
        self.assertEqual(scalar_products, 89_911_320)
        self.assertEqual(distributed_terms, 22_244_880)
        self.assertNotEqual(scalar_products, distributed_terms)

    def test_cross_tag_collision_and_complete_monomial_cancellation(self):
        # 2*(X/2)*Y and -3*(Y/3)*X collide at X*Y and cancel.  The
        # unrelated constant survives.  This directly checks that global
        # collection neither drops nor double-counts cross-tag collisions.
        packed = {0: (
            (1, 0, 0, 1, 2),
            (0, 1, 1, 0, -3),
            (0, 0, 0, 0, 5),
        )}
        kwargs = dict(
            r=1, s=1, delta=Q(1, 10),
            domain=RADIAL.AggregateDomain(Q(2, 5)),
            first_affine=(Q(0), Q(1, 2), Q(0)),
            second_affine=(Q(0), Q(0), Q(1, 3)))
        expected, _ = FAST.integrate_packed(RADIAL, packed, **kwargs)
        observed, stats = TARGET.integrate_packed_collected_integers(
            RADIAL, packed, **kwargs)
        self.assertEqual(observed, expected)
        self.assertEqual(observed, Q(2, 5))  # 5 * area of the 2/5 triangle
        self.assertGreaterEqual(stats["cancelled_product_monomials"], 1)

    def test_deterministic_random_packed_against_two_exact_references(self):
        rng = random.Random(236)
        domains = (
            RADIAL.AggregateDomain(Q(5, 11)),
            RADIAL.AggregateDomain(Q(5, 11), x_bound=Q(3, 11)),
            RADIAL.AggregateDomain(Q(5, 11), y_lower=Q(1, 11)),
            RADIAL.AggregateDomain(Q(5, 11), y_upper=Q(2, 11)),
            RADIAL.AggregateDomain(Q(5, 11), total_lower=Q(2, 11)),
        )
        for trial in range(12):
            r, s = ((2, 3), (0, 3), (2, 0))[trial % 3]
            packed = {}
            for shift in (0, 1, 2, 7):
                terms = []
                for _ in range(2 + trial % 4):
                    xp = 0 if r == 0 else rng.randrange(4)
                    yp = 0 if s == 0 else rng.randrange(4)
                    coefficient = rng.randrange(-23, 24) or 1
                    terms.append((rng.randrange(5), rng.randrange(5),
                                  xp, yp, coefficient))
                packed[shift] = tuple(terms)
            first = (Q(rng.randrange(-7, 8), rng.randrange(2, 13)),
                     Q(rng.randrange(-7, 8), rng.randrange(2, 13)),
                     Q(rng.randrange(-7, 8), rng.randrange(2, 13)))
            second = (Q(rng.randrange(-7, 8), rng.randrange(2, 13)),
                      Q(rng.randrange(-7, 8), rng.randrange(2, 13)),
                      Q(rng.randrange(-7, 8), rng.randrange(2, 13)))
            domain = domains[trial % len(domains)]
            kwargs = dict(r=r, s=s, delta=Q(1, 11), domain=domain,
                          first_affine=first, second_affine=second)
            direct, _ = FAST.integrate_packed(RADIAL, packed, **kwargs)
            integer_weight, _ = WEIGHT.integrate_packed_integer_weights(
                RADIAL, packed, **kwargs)
            observed, stats = TARGET.integrate_packed_collected_integers(
                RADIAL, packed, **kwargs)
            self.assertEqual(observed, direct)
            self.assertEqual(observed, integer_weight)
            self.assertGreaterEqual(stats["scalar_products"],
                                    stats["nonzero_product_monomials"])

    def test_zero_dimensional_and_exact_boundary_domains(self):
        packed = {0: ((0, 0, 0, 0, 9), (2, 1, 0, 0, -5)),
                  1: ((1, 2, 0, 0, 7),)}
        cases = (
            RADIAL.AggregateDomain(Q(0)),
            RADIAL.AggregateDomain(Q(0), x_bound=Q(-1, 17)),
            RADIAL.AggregateDomain(Q(1, 10), y_lower=Q(0)),
            RADIAL.AggregateDomain(Q(1, 10), y_upper=Q(-1, 13)),
            RADIAL.AggregateDomain(Q(1, 10), total_lower=Q(0)),
        )
        for domain in cases:
            kwargs = dict(
                r=0, s=0, delta=Q(1, 10), domain=domain,
                first_affine=(Q(2, 3), Q(7, 5), Q(-3, 8)),
                second_affine=(Q(5, 7), Q(-2, 9), Q(11, 13)))
            expected, _ = FAST.integrate_packed(RADIAL, packed, **kwargs)
            observed, _ = TARGET.integrate_packed_collected_integers(
                RADIAL, packed, **kwargs)
            self.assertEqual(observed, expected)

    def test_nonuniform_full_band_matches_pruned_v3_branch_by_branch(self):
        k = 4
        delta, alpha_f, eta = Q(1, 10), Q(7, 20), Q(29, 100)
        low_alpha, high_alpha = Q(7, 20), Q(21, 50)
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
        observed_branches = set()
        for r in range(k):
            kwargs = dict(
                k=k, alpha_high=high_alpha, alpha_low=low_alpha,
                alpha_f=alpha_f, eta=eta, delta=delta,
                schedule=schedule, common_r=r)
            expected, expected_diagnostics = PRUNED.band_cross_r_integer(
                ENGINE, RADIAL, families, **kwargs)
            observed, diagnostics = TARGET.band_cross_r_integer(
                ENGINE, RADIAL, families, **kwargs)
            self.assertEqual(observed, expected)
            self.assertEqual(diagnostics["high"],
                             expected_diagnostics["high"])
            self.assertEqual(diagnostics["low"],
                             expected_diagnostics["low"])
            observed_branches.update(diagnostics["high"])
            observed_branches.update(diagnostics["low"])
        self.assertEqual(observed_branches,
                         {"Sdelta", "Stotal", "Ltotal", "Lbig"})


if __name__ == "__main__":
    unittest.main()
