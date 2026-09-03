#!/usr/bin/env python3

from fractions import Fraction as Q
import importlib.util
from pathlib import Path
import sys
import unittest


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
FRONTIER = REPO / "agents/small-delta-frontier/frontier_active25_inner_d16_tagged_shell.py"
TARGET = HERE / "symmetric_cutoff_cross.py"
RUNNER_TARGET = HERE / "d14_grid38_scaled_b_shard.py"
FAST_TARGET = HERE / "fast_tagged_scalar.py"


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


M = load("symmetric_cutoff_cross_test_target", TARGET)
F = load("symmetric_cutoff_cross_test_frontier", FRONTIER)
RADIAL = load(
    "symmetric_cutoff_cross_test_radial",
    REPO / "verify/exact_capped_certificate.py")
RUNNER = load("symmetric_cutoff_cross_test_runner", RUNNER_TARGET)
FAST = load("symmetric_cutoff_cross_test_fast", FAST_TARGET)


class GlobalCutoffCrossTest(unittest.TestCase):
    def test_production_runner_import_and_frozen_scalars(self):
        # Importing the runner is a syntax/module-closure check kept in both
        # normal and -O mandatory executions.
        self.assertEqual(RUNNER.K, 48)
        self.assertEqual(RUNNER.SCALE_F, 10**87)
        self.assertEqual(RUNNER.SCALE_H, 10**38)
        self.assertEqual(RUNNER.DILATION, Q(9270000, 9500917))
        self.assertEqual(
            RUNNER.INNER.name,
            "bv_D19_krylov20_direct_exact_v2_strict.json")
        self.assertEqual(len(RUNNER.SCHEDULE), 12)

    def test_exact_dilation_and_common_scale_invariance(self):
        k = 5
        basis = tuple(F.ei.even_basis(8))
        vector = tuple(Q((i % 11) - 5, i + 7)
                       for i in range(len(basis)))
        terms = {label: coefficient for label, coefficient in
                 zip(basis, vector) if coefficient}
        dilation = Q(9270000, 9500917)
        dilated = M.dilate_residual_terms(basis, vector, dilation)
        point = (Q(1, 101), Q(2, 103), Q(3, 107), Q(5, 109), Q(7, 113))
        self.assertEqual(
            M.evaluate_residual_terms(dilated, point),
            M.evaluate_residual_terms(
                terms, tuple(dilation * value for value in point)))

        # Scaling before or after dilation is identical.  The cross kernel is
        # bilinear and the I polynomial is quadratic, which is precisely the
        # normalization used by the theorem runner (10^87 and 10^38).
        scale_f, scale_h = 10**7, 10**5
        scaled_dilated = M.dilate_residual_terms(
            basis, M.scale_vector(vector, scale_h), dilation)
        self.assertEqual(
            scaled_dilated,
            {label: scale_h * coefficient
             for label, coefficient in dilated.items()})

        marginal = M.marginal_polynomial(
            F.ei, basis, vector, k, Q(7, 20))
        components = M.distinguished_components(F.ei, basis, vector, k)
        kernel, _ = M.global_cross_kernel(F.ei, marginal, components)
        scaled_marginal = M.marginal_polynomial(
            F.ei, basis, M.scale_vector(vector, scale_f), k, Q(7, 20))
        scaled_components = M.distinguished_components(
            F.ei, basis, M.scale_vector(vector, scale_h), k)
        scaled_kernel, _ = M.global_cross_kernel(
            F.ei, scaled_marginal, scaled_components)
        self.assertEqual(
            scaled_kernel,
            {orbit: {tag: scale_f * scale_h * coefficient
                     for tag, coefficient in block.items()}
             for orbit, block in kernel.items()})

        square = M.square_residual_terms(F.ei, terms)
        scaled_terms = {label: scale_h * coefficient
                        for label, coefficient in terms.items()}
        scaled_square = M.square_residual_terms(F.ei, scaled_terms)
        self.assertEqual(
            scaled_square,
            {orbit: {power: scale_h**2 * coefficient
                     for power, coefficient in block.items()}
             for orbit, block in square.items()})

    def test_full_marginal_matches_independent_scan(self):
        scan_path = REPO / "agents/small-delta-frontier/scan_bv_epsilon_fixed.py"
        scan = load("symmetric_cutoff_cross_test_scan", scan_path)
        basis = tuple(F.ei.even_basis(6))
        vector = tuple(Q((i % 7) - 3, i + 5) for i in range(len(basis)))
        got = M.marginal_polynomial(F.ei, basis, vector, 4, Q(7, 20))
        expected = scan.marginal_polynomial(
            basis, vector, 4, Q(7, 20))
        self.assertEqual(got, expected)

    def test_kernel_matches_literal_orbit_block_product(self):
        basis = ((0, ()), (1, ()), (0, (2,)), (2, ()))
        inner = (Q(2), Q(-3), Q(5), Q(7, 3))
        outer = (Q(-1), Q(4), Q(2), Q(-5, 2))
        marginal = M.marginal_polynomial(
            F.ei, basis, inner, 3, Q(7, 20))
        components = M.distinguished_components(
            F.ei, basis, outer, 3)
        kernel, _ = M.global_cross_kernel(F.ei, marginal, components)
        # Expand the two sides at one arbitrary U value.  The kernel side is
        # compared coefficient-by-coefficient before any support integration.
        # Use a simple tagged coefficient ring (p,e,a) rather than bivariate
        # polynomial arithmetic; this directly checks global collection.
        expected = {}
        for (power, lo), lc in marginal.items():
            for (ro, exponent, residual), rc in components.items():
                for orbit, multiplicity in F.ei.multiply_monomial_orbits(lo, ro):
                    key = (orbit, power, exponent, residual)
                    expected[key] = expected.get(key, Q(0)) + lc * rc * multiplicity
        observed = {(orbit, *tag): coefficient
                    for orbit, block in kernel.items()
                    for tag, coefficient in block.items()}
        self.assertEqual(observed, {k: v for k, v in expected.items() if v})

    def test_low_k_cutoff_cross_matches_literal_j(self):
        # eta<alpha is deliberate: this catches omission of Definition 5's
        # shared-coordinate cutoff.  The band itself lies partly above eta.
        k = 3
        delta, alpha_f, eta = Q(1, 10), Q(2, 5), Q(1, 5)
        low_alpha, high_alpha = Q(1, 4), Q(9, 20)
        schedule = (Q(9, 20),) * k
        # Constants make the strict cutoff sensitivity transparent and rule
        # out a coincidental polynomial cancellation.
        basis = ((0, ()),)
        inner = (Q(1),)
        outer = (Q(1),)
        marginal = M.marginal_polynomial(
            F.ei, basis, inner, k, alpha_f)
        components = M.distinguished_components(
            F.ei, basis, outer, k)
        kernel, _ = M.global_cross_kernel(F.ei, marginal, components)
        support_type = F.shell.ScheduledStratumSupport
        high = support_type.make(k, high_alpha, eta, delta, schedule)
        low = support_type.make(k, low_alpha, eta, delta, schedule)
        observed, _ = M.evaluate_band_cross(
            F, kernel, high=high, low=low, alpha_f=alpha_f, eta=eta)

        full = support_type.make(k, alpha_f, eta, delta, (alpha_f,) * k)
        inner_components = F.outer_core.components(basis, inner, k)
        outer_components = F.outer_core.components(basis, outer, k)
        expected = k * (
            F.outer_core.cross_marginal(
                full, inner_components, high, outer_components, eta) -
            F.outer_core.cross_marginal(
                full, inner_components, low, outer_components, eta))
        self.assertEqual(observed, expected)

        # Raising eta changes this example, so an implementation which silently
        # integrates every omitted-coordinate marginal cannot pass by accident.
        eta_uncut = alpha_f
        high_uncut = support_type.make(
            k, high_alpha, eta_uncut, delta, schedule)
        low_uncut = support_type.make(
            k, low_alpha, eta_uncut, delta, schedule)
        uncut, _ = M.evaluate_band_cross(
            F, kernel, high=high_uncut, low=low_uncut,
            alpha_f=alpha_f, eta=eta_uncut)
        self.assertNotEqual(observed, uncut)

    def test_radialized_cross_matches_face_polynomial_oracle(self):
        k = 3
        delta, alpha_f, eta = Q(1, 10), Q(7, 20), Q(29, 100)
        low_alpha, high_alpha = Q(7, 20), Q(21, 50)
        # Genuinely nonuniform and Definition-1 compatible.  Across the two
        # endpoints and common r=0,1 this activates every S/L branch and both
        # beta(r) and beta(r+1) constraints.
        schedule = (Q(9, 50), Q(13, 50), Q(31, 100))
        basis = ((0, ()), (1, ()), (0, (2,)), (2, ()))
        inner = (Q(2), Q(-3), Q(5), Q(7, 3))
        outer = (Q(-1), Q(4), Q(2), Q(-5, 2))
        marginal = M.marginal_polynomial(
            F.ei, basis, inner, k, alpha_f)
        components = M.distinguished_components(
            F.ei, basis, outer, k)
        kernel, _ = M.global_cross_kernel(F.ei, marginal, components)
        families, _ = M.primitive_tagged_families(
            kernel, alpha_f=alpha_f, delta=delta)
        radial = Q(0)
        fast_radial = Q(0)
        branch_names = set()
        for r in range(k):
            value, diagnostics = M.radialized_band_cross_r(
                RADIAL, families, k=k, alpha_high=high_alpha,
                alpha_low=low_alpha, alpha_f=alpha_f, eta=eta,
                delta=delta, schedule=schedule, common_r=r)
            radial += value
            fast_value, fast_diagnostics = FAST.band_cross_r(
                M, RADIAL, families, k=k, alpha_high=high_alpha,
                alpha_low=low_alpha, alpha_f=alpha_f, eta=eta,
                delta=delta, schedule=schedule, common_r=r)
            self.assertEqual(fast_value, value)
            self.assertEqual(fast_diagnostics["high"], diagnostics["high"])
            self.assertEqual(fast_diagnostics["low"], diagnostics["low"])
            integer_value, integer_diagnostics = FAST.band_cross_r_integer(
                M, RADIAL, families, k=k, alpha_high=high_alpha,
                alpha_low=low_alpha, alpha_f=alpha_f, eta=eta,
                delta=delta, schedule=schedule, common_r=r)
            self.assertEqual(integer_value, value)
            self.assertEqual(integer_diagnostics["high"], diagnostics["high"])
            self.assertEqual(integer_diagnostics["low"], diagnostics["low"])
            fast_radial += fast_value
            branch_names.update(diagnostics["high"])
            branch_names.update(diagnostics["low"])

        support_type = F.shell.ScheduledStratumSupport
        high = support_type.make(k, high_alpha, eta, delta, schedule)
        low = support_type.make(k, low_alpha, eta, delta, schedule)
        literal, _ = M.evaluate_band_cross(
            F, kernel, high=high, low=low, alpha_f=alpha_f, eta=eta)
        self.assertEqual(radial, literal)
        self.assertEqual(fast_radial, literal)
        self.assertEqual(branch_names,
                         {"Sdelta", "Stotal", "Ltotal", "Lbig"})

    def test_radialized_band_i_matches_stratum_moments(self):
        k, delta = 4, Q(1, 10)
        low_alpha, high_alpha = Q(3, 10), Q(2, 5)
        schedule = (Q(9, 50), Q(13, 50), Q(31, 100), Q(7, 20))
        basis = tuple(F.ei.even_basis(4))
        vector = tuple(Q((i % 7) - 3, i + 5) for i in range(len(basis)))
        terms = {label: coefficient for label, coefficient in
                 zip(basis, vector) if coefficient}
        square = M.square_residual_terms(F.ei, terms)
        support_type = F.shell.ScheduledStratumSupport
        high = support_type.make(k, high_alpha, Q(1, 4), delta, schedule)
        low = support_type.make(k, low_alpha, Q(1, 4), delta, schedule)
        observed = Q(0)
        expected = Q(0)
        for r in range(k + 1):
            shard, _ = M.radialized_band_i_r(
                RADIAL, square, k=k, alpha_high=high_alpha,
                alpha_low=low_alpha, delta=delta, schedule=schedule,
                number_large=r)
            observed += shard
            for orbit, residuals in square.items():
                for power, coefficient in residuals.items():
                    expected += coefficient * (
                        high.orbit_support_moment_in_stratum(orbit, power, r) -
                        low.orbit_support_moment_in_stratum(orbit, power, r))
        self.assertEqual(observed, expected)


if __name__ == "__main__":
    unittest.main()
