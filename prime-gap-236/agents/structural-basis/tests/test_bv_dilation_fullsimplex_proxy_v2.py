#!/usr/bin/env python3

import importlib.util
from fractions import Fraction as Q
from itertools import permutations
from math import comb
from pathlib import Path
import sys
import unittest


HERE = Path(__file__).resolve()
SOURCE = HERE.parents[1] / "code" / "bv_dilation_fullsimplex_proxy_v2.py"
SPEC = importlib.util.spec_from_file_location("bv_dilation_proxy_tested", SOURCE)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load dilation proxy")
M = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = M
SPEC.loader.exec_module(M)


def orbit_value(k, lam, point):
    padded = tuple(lam) + (0,) * (k - len(lam))
    return sum(
        prod(x ** exponent for x, exponent in zip(point, assignment))
        for assignment in set(permutations(padded)))


def prod(values):
    answer = Q(1)
    for value in values:
        answer *= value
    return answer


def polynomial_value(basis, vector, point):
    residual = 1 - sum(point)
    return sum(coefficient * residual ** a * orbit_value(
        len(point), lam, point)
        for coefficient, (a, lam) in zip(vector, basis))


def marginal_value_from_terms(terms, alpha, shared):
    residual = alpha - sum(shared)
    return sum(coefficient * residual ** power * orbit_value(
        len(shared), lam, shared)
        for (power, lam), coefficient in terms.items())


def literal_marginal_value(basis, vector, alpha, shared):
    """Expand in t around 1-U, independently of the beta-integral shift."""
    upper = alpha - sum(shared)
    one_minus_u = 1 - sum(shared)
    answer = Q(0)
    k = len(shared) + 1
    for coefficient, (a, lam) in zip(vector, basis):
        for exponent, rest in M.split_orbit_at_distinguished(lam, k):
            orbit = orbit_value(k - 1, rest, shared)
            integral = sum(
                (-1) ** j * comb(a, j) * one_minus_u ** (a - j) *
                upper ** (exponent + j + 1) / (exponent + j + 1)
                for j in range(a + 1))
            answer += coefficient * orbit * integral
    return answer


class BvDilationFullSimplexProxyTests(unittest.TestCase):
    def test_coefficient_map_is_pointwise_exact_with_repeated_parts(self):
        basis = M.exact.even_basis(6, max_length=3)
        vector = [Q((i % 7) - 3, i + 2) for i in range(len(basis))]
        c = Q(7, 9)
        transformed = M.dilation_transform(basis, vector, c)
        point = (Q(1, 11), Q(2, 13), Q(1, 17))
        self.assertEqual(
            polynomial_value(basis, transformed, point),
            polynomial_value(basis, vector,
                             tuple(c * x for x in point)))
        repeated = basis.index((0, (2, 2)))
        unit = [Q(0)] * len(basis)
        unit[repeated] = Q(1)
        transformed_unit = M.dilation_transform(basis, unit, c)
        self.assertEqual(transformed_unit[repeated], c ** 4)

    def test_identity_dilation_and_missing_image_fail(self):
        basis = M.exact.even_basis(4, max_length=2)
        vector = [Q(i - 2, i + 1) for i in range(len(basis))]
        self.assertEqual(M.dilation_transform(basis, vector, 1), vector)
        with self.assertRaises(ValueError):
            M.dilation_transform([(2, ())], [1], Q(1, 2))

    def test_marginal_beta_formula_matches_literal_integration(self):
        k = 3
        basis = M.exact.even_basis(5, max_length=k)
        vector = [Q((3 * i) % 11 - 5, i + 3) for i in range(len(basis))]
        alpha = Q(7, 20)
        shared = (Q(1, 23), Q(2, 29))
        terms = M.marginal_terms(basis, vector, k, alpha)
        self.assertEqual(
            marginal_value_from_terms(terms, alpha, shared),
            literal_marginal_value(basis, vector, alpha, shared))

    def test_squared_orbit_normalization_and_j_match_literal_integrator(self):
        k = 3
        alpha, eta = Q(7, 20), Q(3, 10)
        basis = M.exact.even_basis(4, max_length=k)
        vector = [Q((5 * i) % 13 - 6, i + 5) for i in range(len(basis))]
        terms = M.marginal_terms(basis, vector, k, alpha)
        squared = M.square_marginal_terms(terms)
        reconstructed = M.integrate_squared_marginal(
            squared, k - 1, alpha, eta)
        support = M.exact.OneStratumSupport(
            k, alpha, Q(1, 100), eta, alpha, alpha, alpha)
        _, matrix_kj = support.matrices(basis)
        direct_j = M.exact.exact_quadratic(matrix_kj, vector) / k
        self.assertEqual(reconstructed, direct_j)

        basis_square = M.square_basis_terms(basis, vector)
        reconstructed_i = M.integrate_squared_marginal(
            basis_square, k, Q(1), alpha)
        direct_i = M.exact.exact_quadratic(
            support.matrices(basis)[0], vector)
        self.assertEqual(reconstructed_i, direct_i)

    def test_low_k_dilation_change_of_variables_for_i_and_j(self):
        k = 2
        alpha0, eta0 = Q(3, 10), Q(1, 4)
        alpha1, eta1 = Q(2, 5), Q(7, 20)
        c = alpha0 / alpha1
        basis = M.exact.even_basis(4, max_length=k)
        vector = [Q((7 * i) % 17 - 8, 2 * i + 3)
                  for i in range(len(basis))]
        transformed = M.dilation_transform(basis, vector, c)

        old = M.exact.OneStratumSupport(
            k, alpha0, Q(1, 100), c * eta1,
            alpha0, alpha0, alpha0)
        new = M.exact.OneStratumSupport(
            k, alpha1, Q(1, 100), eta1,
            alpha1, alpha1, alpha1)
        old_m1, old_kj = old.matrices(basis)
        new_m1, new_kj = new.matrices(basis)
        old_i = M.exact.exact_quadratic(old_m1, vector)
        old_j = M.exact.exact_quadratic(old_kj, vector) / k
        new_i = M.exact.exact_quadratic(new_m1, transformed)
        new_j = M.exact.exact_quadratic(new_kj, transformed) / k
        self.assertEqual(new_i, old_i / c ** k)
        self.assertEqual(new_j, old_j / c ** (k + 1))

        # eta0 is deliberately irrelevant to the mapped cutoff; this catches
        # the tempting but false substitution c*eta1=eta0.
        self.assertNotEqual(c * eta1, eta0)

    def test_pinned_source_mutation_rejects(self):
        relative = next(iter(M.PINNED))
        expected = M.PINNED[relative]
        M.PINNED[relative] = "0" * 64
        try:
            with self.assertRaises(ValueError):
                M.validate_sources()
        finally:
            M.PINNED[relative] = expected

    def test_exact_monotone_lower_bound_already_crosses_one(self):
        _, _, _, denominator, numerator = M.load_certificate()
        self.assertGreater(M.C * M.ETA1, M.ETA0)
        lower_bound = (numerator / denominator) / M.C
        self.assertGreater(lower_bound, 1)
        self.assertGreater(lower_bound - 1, Q(19, 1000))


if __name__ == "__main__":
    unittest.main()
