#!/usr/bin/env python3

import io
import json
import math
import tempfile
import unittest
from collections import defaultdict
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import replace
from fractions import Fraction
from itertools import permutations
from pathlib import Path
from unittest.mock import patch

import verify.exact_capped_certificate as checker

from verify.exact_capped_certificate import (
    AggregateDomain,
    C10_D4_REGRESSION,
    C20_D4_GENERAL_HISTORY,
    CertificateError,
    Parameters,
    TARGET_C10_D12,
    build_basis_terms,
    build_polynomial,
    clip_polygon,
    compute_i,
    compute_i_literal,
    compute_i_tagged,
    compute_j,
    compute_j_literal,
    compute_j_tagged,
    exact_check,
    _compute_j_k1_general_for_tests,
    _integrate_radial_polynomial,
    _integrate_tagged_radial_polynomials,
    _maximum_active_shift,
    _pack_tagged_radials_by_shift,
    _partition_face_radial,
    _polygon_monomial_batch,
    _tagged_i_square,
    _tagged_marginal_polynomials,
    fixed_assignment_integral,
    load_certificate,
    monomial_product,
    marginal_polynomials,
    poly_add_term,
    poly_multiply,
    polygon_monomial,
    symmetric_stratum_integral,
    validate_parameters,
)


class OrbitAlgebraTests(unittest.TestCase):
    def test_basic_products_have_unnormalized_monomial_convention(self) -> None:
        self.assertEqual(monomial_product((1,), (1,), 5), {(2,): 1, (1, 1): 2})
        self.assertEqual(monomial_product((2,), (2,), 5), {(4,): 1, (2, 2): 2})
        self.assertEqual(
            monomial_product((2, 1), (1,), 5),
            {(3, 1): 1, (2, 2): 2, (2, 1, 1): 2},
        )
        self.assertEqual(monomial_product((2, 2), (2,), 5), {(4, 2): 1, (2, 2, 2): 3})

    def test_basis_label_means_one_minus_sum_power(self) -> None:
        poly = build_polynomial([(2, ())], [Fraction(1)], 3)
        self.assertEqual(poly, {(): Fraction(1), (1,): Fraction(-2), (2,): Fraction(1), (1, 1): Fraction(2)})

    def test_products_match_literal_permutations_in_four_variables(self) -> None:
        parts = [(), (1,), (2,), (1, 1), (3,), (2, 1), (1, 1, 1), (2, 2)]

        def literal(part):
            padded = part + (0,) * (4 - len(part))
            return {exponents: Fraction(1) for exponents in set(permutations(padded))}

        for left in parts:
            for right in parts:
                with self.subTest(left=left, right=right):
                    expected = LowDimensionalIJTests.literal_multiply(literal(left), literal(right))
                    grouped = monomial_product(left, right, 4)
                    actual = LowDimensionalIJTests.literal_polynomial(
                        {part: Fraction(coefficient) for part, coefficient in grouped.items()},
                        4,
                    )
                    self.assertEqual(actual, expected)


class PolygonTests(unittest.TestCase):
    def test_triangle_moments(self) -> None:
        triangle = [
            (Fraction(0), Fraction(0)),
            (Fraction(2), Fraction(0)),
            (Fraction(0), Fraction(3)),
        ]
        self.assertEqual(polygon_monomial(triangle, 0, 0), 3)
        self.assertEqual(polygon_monomial(triangle, 1, 0), 2)
        self.assertEqual(polygon_monomial(triangle, 0, 1), 3)
        self.assertEqual(polygon_monomial(triangle, 1, 1), Fraction(3, 2))

    def test_independent_half_plane_clip(self) -> None:
        triangle = [
            (Fraction(0), Fraction(0)),
            (Fraction(2), Fraction(0)),
            (Fraction(0), Fraction(2)),
        ]
        clipped = clip_polygon(triangle, Fraction(1), Fraction(0), Fraction(1))
        self.assertEqual(polygon_monomial(clipped, 0, 0), Fraction(3, 2))

    def test_batched_moments_match_literal_triangulation(self) -> None:
        polygon = [
            (Fraction(1, 7), Fraction(1, 11)),
            (Fraction(5, 7), Fraction(1, 13)),
            (Fraction(4, 5), Fraction(3, 7)),
            (Fraction(2, 9), Fraction(5, 8)),
        ]
        requested = {(0, 0), (1, 0), (0, 2), (3, 1), (2, 4)}
        batched = _polygon_monomial_batch(polygon, requested)
        self.assertEqual(
            batched,
            {
                powers: polygon_monomial(polygon, *powers)
                for powers in requested
            },
        )


class StratumTests(unittest.TestCase):
    def test_one_small_coordinate_cap(self) -> None:
        delta = Fraction(1, 5)
        value = fixed_assignment_integral(
            [],
            [3],
            delta,
            AggregateDomain(total_bound=Fraction(1)),
        )
        self.assertEqual(value, delta**4 / 4)

    def test_one_shifted_large_coordinate(self) -> None:
        delta = Fraction(1, 5)
        length = Fraction(1, 7)
        value = fixed_assignment_integral(
            [2],
            [],
            delta,
            AggregateDomain(total_bound=Fraction(1), x_bound=length),
        )
        expected = ((delta + length) ** 3 - delta**3) / 3
        self.assertEqual(value, expected)

    def test_rectangle_after_aggregate_triangulation(self) -> None:
        delta = Fraction(1, 5)
        length = Fraction(1, 7)
        value = fixed_assignment_integral(
            [0],
            [0],
            delta,
            AggregateDomain(total_bound=length + delta, x_bound=length),
        )
        self.assertEqual(value, length * delta)

    def test_face_radial_aggregation_matches_term_oracle(self) -> None:
        delta = Fraction(1, 7)
        domain = AggregateDomain(
            total_bound=Fraction(3, 5),
            x_bound=Fraction(2, 5),
            y_lower=Fraction(1, 10),
            y_upper=Fraction(1, 2),
            total_lower=Fraction(1, 9),
        )
        for number_variables in (2, 3):
            for part in ((), (1,), (2,), (1, 1), (2, 1)):
                if len(part) > number_variables:
                    continue
                for number_large in range(number_variables + 1):
                    with self.subTest(
                        n=number_variables,
                        part=part,
                        r=number_large,
                    ):
                        expected = symmetric_stratum_integral(
                            {part: Fraction(1)},
                            number_variables,
                            number_large,
                            delta,
                            domain,
                            affine_power=2,
                            q0=Fraction(1, 2),
                            qx=Fraction(-1),
                            qy=Fraction(1, 3),
                        )
                        actual = _integrate_radial_polynomial(
                            _partition_face_radial(
                                part,
                                number_variables,
                                number_large,
                                delta,
                            ),
                            number_large,
                            number_variables - number_large,
                            delta,
                            domain,
                            affine_power=2,
                            q0=Fraction(1, 2),
                            qx=Fraction(-1),
                            qy=Fraction(1, 3),
                        )
                        self.assertEqual(actual, expected)

    def test_active_shift_bound_is_strict(self) -> None:
        delta = Fraction(1, 10)
        self.assertEqual(_maximum_active_shift(3 * delta, delta), 2)
        self.assertEqual(_maximum_active_shift(Fraction(31, 100), delta), 3)

    def test_two_affine_tag_batch_matches_combined_power(self) -> None:
        delta = Fraction(1, 10)
        domain = AggregateDomain(
            total_bound=Fraction(2, 5),
            x_bound=Fraction(1, 4),
            y_upper=Fraction(3, 10),
        )
        radial = _partition_face_radial((2, 1), 3, 1, delta)
        affine = (Fraction(7, 10), Fraction(-1), Fraction(-1))
        tagged = _integrate_tagged_radial_polynomials(
            {(2, 3): radial},
            1,
            2,
            delta,
            domain,
            first_affine=affine,
            second_affine=affine,
        )
        packed = _pack_tagged_radials_by_shift({(2, 3): radial})
        packed_tagged = _integrate_tagged_radial_polynomials(
            None,
            1,
            2,
            delta,
            domain,
            first_affine=affine,
            second_affine=affine,
            packed_by_shift=packed,
        )
        combined = _integrate_radial_polynomial(
            radial,
            1,
            2,
            delta,
            domain,
            affine_power=5,
            q0=affine[0],
            qx=affine[1],
            qy=affine[2],
        )
        self.assertEqual(tagged, combined)
        self.assertEqual(packed_tagged, tagged)


class LowDimensionalIJTests(unittest.TestCase):
    def test_private_general_k1_zero_shared_variable_edge(self) -> None:
        params = Parameters(
            name="general-test-only-k1",
            k=1,
            degree=0,
            alpha=Fraction(1, 10),
            eta=Fraction(1, 10),
            delta=Fraction(1, 10),
            beta1=Fraction(1, 5),
            beta2=Fraction(1, 5),
            beta3plus=Fraction(1, 5),
        )
        self.assertEqual(
            _compute_j_k1_general_for_tests({(): Fraction(1)}, params),
            Fraction(1, 100),
        )

    def test_constant_function_on_uncut_two_simplex(self) -> None:
        params = Parameters(
            name="unit-k2",
            k=2,
            degree=0,
            alpha=Fraction(1, 2),
            eta=Fraction(1, 3),
            delta=Fraction(1, 6),
            beta1=Fraction(1, 2),
            beta2=Fraction(1, 2),
            beta3plus=Fraction(1, 2),
        )
        polynomial = {(): Fraction(1)}
        basis_terms = {(0, ()): Fraction(1)}
        self.assertEqual(compute_i(polynomial, params), Fraction(1, 8))
        self.assertEqual(compute_j(polynomial, params), Fraction(13, 324))
        self.assertEqual(compute_i_tagged(basis_terms, params), Fraction(1, 8))
        self.assertEqual(compute_j_tagged(basis_terms, params), Fraction(13, 324))
        self.assertEqual(compute_i(polynomial, params), compute_i_literal(polynomial, params))
        self.assertEqual(compute_j(polynomial, params), compute_j_literal(polynomial, params))

    def test_constant_k2_with_interior_cap_total_branch_switch(self) -> None:
        params = Parameters(
            name="branch-switch-k2",
            k=2,
            degree=0,
            alpha=Fraction(2, 5),
            eta=Fraction(3, 10),
            delta=Fraction(1, 10),
            beta1=Fraction(7, 20),
            beta2=Fraction(7, 20),
            beta3plus=Fraction(7, 20),
        )
        polynomial = {(): Fraction(1)}
        basis_terms = {(0, ()): Fraction(1)}
        original_pack = checker._pack_tagged_radials_by_shift
        with patch.object(
            checker,
            "_pack_tagged_radials_by_shift",
            wraps=original_pack,
        ) as pack_call:
            tagged_j = compute_j_tagged(basis_terms, params)
        self.assertEqual(compute_i(polynomial, params), Fraction(11, 160))
        self.assertEqual(compute_j(polynomial, params), Fraction(403, 24000))
        self.assertEqual(compute_i_tagged(basis_terms, params), Fraction(11, 160))
        self.assertEqual(tagged_j, Fraction(403, 24000))
        # Two active base faces each use SS, SL, and LL.  Packing happens once
        # per family/face, not once for each of the seven ordered jobs.
        self.assertEqual(pack_call.call_count, 6)
        self.assertEqual(compute_i(polynomial, params), compute_i_literal(polynomial, params))
        self.assertEqual(compute_j(polynomial, params), compute_j_literal(polynomial, params))
        self.assertEqual(
            compute_i(polynomial, params, reverse_faces=True),
            Fraction(11, 160),
        )
        self.assertEqual(
            compute_j(polynomial, params, reverse_faces=True),
            Fraction(403, 24000),
        )

    @staticmethod
    def literal_polynomial(polynomial, number_variables):
        answer = defaultdict(Fraction)
        for part, coefficient in polynomial.items():
            padded = part + (0,) * (number_variables - len(part))
            for exponents in set(permutations(padded)):
                answer[exponents] += coefficient
        return dict(answer)

    @staticmethod
    def literal_multiply(left, right):
        answer = defaultdict(Fraction)
        for left_exponents, left_coefficient in left.items():
            for right_exponents, right_coefficient in right.items():
                output = tuple(a + b for a, b in zip(left_exponents, right_exponents, strict=True))
                answer[output] += left_coefficient * right_coefficient
        return dict(answer)

    @staticmethod
    def literal_power(poly, power, number_variables):
        answer = {(0,) * number_variables: Fraction(1)}
        for _ in range(power):
            answer = LowDimensionalIJTests.literal_multiply(answer, poly)
        return answer

    @staticmethod
    def simplex_integral(poly, bound):
        answer = Fraction(0)
        for exponents, coefficient in poly.items():
            degree = sum(exponents)
            numerator = math.prod(math.factorial(x) for x in exponents)
            answer += coefficient * bound ** (len(exponents) + degree) * numerator / math.factorial(len(exponents) + degree)
        return answer

    @classmethod
    def direct_full_simplex_i_j(cls, polynomial, k, alpha, eta):
        literal = cls.literal_polynomial(polynomial, k)
        direct_i = cls.simplex_integral(cls.literal_multiply(literal, literal), alpha)

        base_variables = k - 1
        marginal = defaultdict(Fraction)
        linear = {(0,) * base_variables: alpha}
        for coordinate in range(base_variables):
            unit = [0] * base_variables
            unit[coordinate] = 1
            linear[tuple(unit)] = Fraction(-1)
        for exponents, coefficient in literal.items():
            base_exponents, t_power = exponents[:-1], exponents[-1]
            fiber = cls.literal_power(linear, t_power + 1, base_variables)
            for fiber_exponents, fiber_coefficient in fiber.items():
                output = tuple(a + b for a, b in zip(base_exponents, fiber_exponents, strict=True))
                marginal[output] += coefficient * fiber_coefficient / (t_power + 1)
        direct_j = cls.simplex_integral(cls.literal_multiply(marginal, marginal), eta)
        return direct_i, direct_j

    def test_signed_vectors_against_literal_k2_k3_k4(self) -> None:
        labels = [(0, ()), (1, ()), (2, ()), (0, (2,))]
        coefficients = [Fraction(2, 3), Fraction(-3, 5), Fraction(1, 7), Fraction(-2, 9)]
        alpha = Fraction(2, 5)
        delta = Fraction(1, 10)
        eta = alpha - delta
        for k in (2, 3, 4):
            with self.subTest(k=k):
                params = Parameters(
                    name=f"literal-k{k}",
                    k=k,
                    degree=2,
                    alpha=alpha,
                    eta=eta,
                    delta=delta,
                    beta1=alpha,
                    beta2=alpha,
                    beta3plus=alpha,
                )
                polynomial = build_polynomial(labels, coefficients, k)
                basis_terms = build_basis_terms(labels, coefficients)
                expected_i, expected_j = self.direct_full_simplex_i_j(polynomial, k, alpha, eta)
                self.assertEqual(compute_i(polynomial, params), expected_i)
                self.assertEqual(compute_j(polynomial, params), expected_j)
                self.assertEqual(compute_i_tagged(basis_terms, params), expected_i)
                self.assertEqual(compute_j_tagged(basis_terms, params), expected_j)
                self.assertEqual(compute_i(polynomial, params), compute_i_literal(polynomial, params))
                self.assertEqual(compute_j(polynomial, params), compute_j_literal(polynomial, params))

    def test_signed_capped_branch_geometry_matches_literal_oracle(self) -> None:
        params = Parameters(
            name="signed-capped-k3",
            k=3,
            degree=2,
            alpha=Fraction(2, 5),
            eta=Fraction(3, 10),
            delta=Fraction(1, 10),
            beta1=Fraction(1, 4),
            beta2=Fraction(3, 10),
            beta3plus=Fraction(7, 20),
        )
        labels = [(0, ()), (1, ()), (2, ()), (0, (2,))]
        coefficients = [
            Fraction(2, 3),
            Fraction(-3, 5),
            Fraction(1, 7),
            Fraction(-2, 9),
        ]
        polynomial = build_polynomial(labels, coefficients, params.k)
        basis_terms = build_basis_terms(labels, coefficients)
        self.assertEqual(
            compute_i(polynomial, params),
            compute_i_literal(polynomial, params),
        )
        self.assertEqual(
            compute_j(polynomial, params),
            compute_j_literal(polynomial, params),
        )
        self.assertEqual(
            compute_i_tagged(basis_terms, params),
            compute_i_literal(polynomial, params),
        )
        self.assertEqual(
            compute_j_tagged(basis_terms, params),
            compute_j_literal(polynomial, params),
        )

    def test_degree_four_tagged_residuals_match_both_oracles(self) -> None:
        params = Parameters(
            name="tagged-d4-k4",
            k=4,
            degree=4,
            alpha=Fraction(2, 5),
            eta=Fraction(3, 10),
            delta=Fraction(1, 10),
            beta1=Fraction(1, 4),
            beta2=Fraction(3, 10),
            beta3plus=Fraction(7, 20),
        )
        labels = [
            (0, ()),
            (1, ()),
            (3, ()),
            (0, (2,)),
            (1, (2,)),
            (0, (3,)),
            (0, (2, 2)),
            (0, (4,)),
        ]
        coefficients = [
            Fraction(2, 3),
            Fraction(-3, 5),
            Fraction(1, 13),
            Fraction(-2, 9),
            Fraction(4, 17),
            Fraction(-1, 11),
            Fraction(2, 19),
            Fraction(-3, 23),
        ]
        polynomial = build_polynomial(labels, coefficients, params.k)
        basis_terms = build_basis_terms(labels, coefficients)
        tagged_i = compute_i_tagged(basis_terms, params)
        tagged_j = compute_j_tagged(basis_terms, params)
        self.assertEqual(
            tagged_i,
            compute_i(polynomial, params),
        )
        self.assertEqual(
            tagged_i,
            compute_i_literal(polynomial, params),
        )
        self.assertEqual(
            tagged_j,
            compute_j(polynomial, params),
        )
        self.assertEqual(
            tagged_j,
            compute_j_literal(polynomial, params),
        )

    def test_tagged_algebra_reexpands_to_expanded_oracle(self) -> None:
        params = Parameters(
            name="tagged-algebra-k4",
            k=4,
            degree=4,
            alpha=Fraction(2, 5),
            eta=Fraction(3, 10),
            delta=Fraction(1, 10),
            beta1=Fraction(1, 4),
            beta2=Fraction(3, 10),
            beta3plus=Fraction(7, 20),
        )
        labels = [(0, ()), (3, ()), (1, (2,)), (0, (3,)), (0, (2, 2))]
        coefficients = [
            Fraction(2, 3),
            Fraction(-1, 7),
            Fraction(3, 11),
            Fraction(-2, 13),
            Fraction(1, 17),
        ]
        basis_terms = build_basis_terms(labels, coefficients)
        expanded = build_polynomial(labels, coefficients, params.k)

        def powers(constant, maximum, number_variables):
            result = [{(): Fraction(1)}]
            generator = {(): constant, (1,): Fraction(-1)}
            for _ in range(maximum):
                result.append(poly_multiply(result[-1], generator, number_variables))
            return result

        tagged_square = _tagged_i_square(basis_terms, params.k, params.alpha)
        alpha_powers = powers(params.alpha, 2 * params.degree, params.k)
        reexpanded_square = {}
        for (_, residual_power), base_poly in tagged_square.items():
            term = poly_multiply(base_poly, alpha_powers[residual_power], params.k)
            for part, coefficient in term.items():
                poly_add_term(reexpanded_square, part, coefficient)
        self.assertEqual(
            reexpanded_square,
            poly_multiply(expanded, expanded, params.k),
        )

        tagged_small, tagged_large = _tagged_marginal_polynomials(
            basis_terms,
            params,
        )
        expanded_small, expanded_large = marginal_polynomials(expanded, params)
        one_minus_u_powers = powers(Fraction(1), params.degree, params.k - 1)

        def expand_marginals(tagged):
            answer = defaultdict(dict)
            for (fiber_power, residual_power), base_poly in tagged.items():
                term = poly_multiply(
                    base_poly,
                    one_minus_u_powers[residual_power],
                    params.k - 1,
                )
                for part, coefficient in term.items():
                    poly_add_term(answer[fiber_power], part, coefficient)
            return dict(answer)

        self.assertEqual(expand_marginals(tagged_small), {0: expanded_small})
        self.assertEqual(expand_marginals(tagged_large), expanded_large)

    def test_two_worker_contiguous_blocks_equal_serial(self) -> None:
        params = Parameters(
            name="worker-k3",
            k=3,
            degree=2,
            alpha=Fraction(2, 5),
            eta=Fraction(3, 10),
            delta=Fraction(1, 10),
            beta1=Fraction(1, 4),
            beta2=Fraction(3, 10),
            beta3plus=Fraction(7, 20),
        )
        polynomial = build_polynomial(
            [(0, ()), (1, ()), (0, (2,))],
            [Fraction(4, 9), Fraction(-2, 7), Fraction(3, 11)],
            params.k,
        )
        basis_terms = build_basis_terms(
            [(0, ()), (1, ()), (0, (2,))],
            [Fraction(4, 9), Fraction(-2, 7), Fraction(3, 11)],
        )
        for reverse_faces in (False, True):
            with self.subTest(reverse_faces=reverse_faces):
                self.assertEqual(
                    compute_i(
                        polynomial,
                        params,
                        reverse_faces=reverse_faces,
                        workers=2,
                    ),
                    compute_i(
                        polynomial,
                        params,
                        reverse_faces=reverse_faces,
                        workers=1,
                    ),
                )
                self.assertEqual(
                    compute_j(
                        polynomial,
                        params,
                        reverse_faces=reverse_faces,
                        workers=2,
                    ),
                    compute_j(
                        polynomial,
                        params,
                        reverse_faces=reverse_faces,
                        workers=1,
                    ),
                )
                self.assertEqual(
                    compute_i_tagged(
                        basis_terms,
                        params,
                        reverse_faces=reverse_faces,
                        workers=2,
                    ),
                    compute_i_tagged(
                        basis_terms,
                        params,
                        reverse_faces=reverse_faces,
                        workers=1,
                    ),
                )
                self.assertEqual(
                    compute_j_tagged(
                        basis_terms,
                        params,
                        reverse_faces=reverse_faces,
                        workers=2,
                    ),
                    compute_j_tagged(
                        basis_terms,
                        params,
                        reverse_faces=reverse_faces,
                        workers=1,
                    ),
                )
                self.assertEqual(
                    compute_i_tagged(basis_terms, params, reverse_faces=reverse_faces),
                    compute_i(polynomial, params, reverse_faces=reverse_faces),
                )
                self.assertEqual(
                    compute_j_tagged(basis_terms, params, reverse_faces=reverse_faces),
                    compute_j(polynomial, params, reverse_faces=reverse_faces),
                )

    def test_literal_oracles_refuse_high_dimension(self) -> None:
        polynomial = {(): Fraction(1)}
        with self.assertRaises(ValueError):
            compute_i_literal(polynomial, C10_D4_REGRESSION)
        with self.assertRaises(ValueError):
            compute_j_literal(polynomial, C10_D4_REGRESSION)
        with self.assertRaises(ValueError):
            compute_i(polynomial, C10_D4_REGRESSION)
        with self.assertRaises(ValueError):
            compute_j(polynomial, C10_D4_REGRESSION)


class ParserTests(unittest.TestCase):
    PARAMS = Parameters(
        name="parser",
        k=2,
        degree=0,
        alpha=Fraction(1, 2),
        eta=Fraction(1, 3),
        delta=Fraction(1, 6),
        beta1=Fraction(1, 2),
        beta2=Fraction(1, 2),
        beta3plus=Fraction(1, 2),
    )

    def write(self, text: str) -> Path:
        temporary = tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False)
        with temporary:
            temporary.write(text)
        self.addCleanup(Path(temporary.name).unlink)
        return Path(temporary.name)

    def test_minimal_valid_input(self) -> None:
        path = self.write(json.dumps({
            "k": 2,
            "degree": 0,
            "basis_dimension": 1,
            "basis": [[0, []]],
            "rational_vector": ["1"],
        }))
        self.assertEqual(load_certificate(path, self.PARAMS), ([(0, ())], [Fraction(1)]))

    def test_minimal_exact_check_uses_tagged_backend(self) -> None:
        path = self.write(json.dumps({
            "k": 2,
            "degree": 0,
            "basis_dimension": 1,
            "basis": [[0, []]],
            "rational_vector": ["1"],
        }))
        exact_params = replace(
            self.PARAMS,
            alpha=Fraction(2, 5),
            eta=Fraction(3, 10),
            delta=Fraction(1, 10),
            beta1=Fraction(2, 5),
            beta2=Fraction(2, 5),
            beta3plus=Fraction(2, 5),
        )
        result = exact_check(path, exact_params)
        self.assertEqual(result["I"], "2/25")
        self.assertEqual(result["J"], "21/1000")
        self.assertEqual(result["tagged_nonzero_source_terms"], 1)

    def test_duplicate_key_is_rejected(self) -> None:
        path = self.write(
            '{"k":2,"k":2,"degree":0,"basis_dimension":1,'
            '"basis":[[0,[]]],"rational_vector":["1"]}'
        )
        with self.assertRaises(CertificateError):
            load_certificate(path, self.PARAMS)

    def test_duplicate_label_is_rejected(self) -> None:
        path = self.write(json.dumps({
            "k": 2,
            "degree": 0,
            "basis_dimension": 2,
            "basis": [[0, []], [0, []]],
            "rational_vector": ["1", "2"],
        }))
        with self.assertRaises(CertificateError):
            load_certificate(path, self.PARAMS)

    def test_missing_coefficient_is_rejected(self) -> None:
        path = self.write(json.dumps({
            "k": 2,
            "degree": 0,
            "basis_dimension": 1,
            "basis": [[0, []]],
            "rational_vector": [],
        }))
        with self.assertRaises(CertificateError):
            load_certificate(path, self.PARAMS)

    def test_wrong_k_is_rejected(self) -> None:
        path = self.write(json.dumps({
            "k": 3,
            "degree": 0,
            "basis_dimension": 1,
            "basis": [[0, []]],
            "rational_vector": ["1"],
        }))
        with self.assertRaises(CertificateError):
            load_certificate(path, self.PARAMS)

    def test_truncated_json_is_rejected(self) -> None:
        path = self.write(
            '{"k":2,"degree":0,"basis_dimension":1,'
            '"basis":[[0,[]]],"rational_vector":["1"]'
        )
        with self.assertRaises(CertificateError):
            load_certificate(path, self.PARAMS)

    def test_noncanonical_or_incomplete_data_is_rejected(self) -> None:
        path = self.write(json.dumps({
            "k": 2,
            "degree": 0,
            "basis_dimension": 1,
            "basis": [[0, []]],
            "rational_vector": ["2/2"],
        }))
        with self.assertRaises(CertificateError):
            load_certificate(path, self.PARAMS)

    def test_target_ordered_payload_provenance_is_pinned(self) -> None:
        source = (
            Path(__file__).resolve().parent.parent
            / "agents/exact-integrator/results/hb_c10_fullsimplex_noones_D12.json"
        )
        raw = json.loads(source.read_text(encoding="utf-8"))
        raw["rational_vector"][0] = "0"
        path = self.write(json.dumps(raw))
        with self.assertRaises(CertificateError):
            load_certificate(path, TARGET_C10_D12)

    def test_raw_target_support_metadata_is_not_a_mathematical_input(self) -> None:
        source = (
            Path(__file__).resolve().parent.parent
            / "agents/exact-integrator/results/hb_c10_fullsimplex_noones_D12.json"
        )
        raw = json.loads(source.read_text(encoding="utf-8"))
        raw["parameters"] = {"beta1": "deliberately ignored discovery metadata"}
        path = self.write(json.dumps(raw))
        labels, coefficients = load_certificate(path, TARGET_C10_D12)
        self.assertEqual(len(labels), 272)
        self.assertEqual(len(coefficients), 272)

    def test_target_preset_rejects_wrong_capped_beta(self) -> None:
        with self.assertRaises(ValueError):
            validate_parameters(
                replace(TARGET_C10_D12, beta3plus=TARGET_C10_D12.alpha)
            )

    def test_same_geometry_c10_d4_regression_preset_is_valid(self) -> None:
        validate_parameters(C10_D4_REGRESSION)
        self.assertEqual(
            C10_D4_REGRESSION.alpha - C10_D4_REGRESSION.eta,
            C10_D4_REGRESSION.delta,
        )

    def test_historical_c20_tuple_is_rejected_by_target_geometry(self) -> None:
        self.assertEqual(
            C20_D4_GENERAL_HISTORY.alpha - C20_D4_GENERAL_HISTORY.eta,
            Fraction(1, 100),
        )
        self.assertEqual(C20_D4_GENERAL_HISTORY.delta, Fraction(1, 50))
        with self.assertRaises(ValueError):
            validate_parameters(C20_D4_GENERAL_HISTORY)

    def test_cli_atomic_output_matches_emitted_json_exactly(self) -> None:
        result = {
            "checker": "synthetic exact regression",
            "certificate_passes": False,
            "I": "2/3",
            "J": "5/17",
        }
        with tempfile.TemporaryDirectory() as directory_name:
            directory = Path(directory_name)
            input_path = directory / "input.json"
            input_path.write_text("{}\n", encoding="utf-8")
            output_path = directory / "result.json"
            stdout = io.StringIO()
            stderr = io.StringIO()
            with (
                patch.object(checker, "exact_check", return_value=result),
                redirect_stdout(stdout),
                redirect_stderr(stderr),
            ):
                status = checker.main(
                    [
                        str(input_path),
                        "--preset",
                        "regression-c10-d4",
                        "--output",
                        str(output_path),
                    ]
                )
            expected = checker._render_json(result)
            self.assertEqual(status, 1)
            self.assertEqual(stderr.getvalue(), "")
            self.assertEqual(stdout.getvalue(), expected)
            self.assertEqual(output_path.read_text(encoding="utf-8"), expected)
            self.assertEqual(list(directory.glob(".*.tmp")), [])

    def test_cli_atomic_output_replaces_stale_pass_with_failure(self) -> None:
        with tempfile.TemporaryDirectory() as directory_name:
            directory = Path(directory_name)
            input_path = directory / "input.json"
            input_path.write_text("{}\n", encoding="utf-8")
            output_path = directory / "result.json"
            output_path.write_text(
                '{"certificate_passes":true}\n',
                encoding="utf-8",
            )
            observed: dict[str, object] = {}

            def fail_after_sentinel(*args, **kwargs):
                observed.update(json.loads(output_path.read_text(encoding="utf-8")))
                raise CertificateError("synthetic certificate failure")

            stdout = io.StringIO()
            stderr = io.StringIO()
            with (
                patch.object(checker, "exact_check", side_effect=fail_after_sentinel),
                redirect_stdout(stdout),
                redirect_stderr(stderr),
            ):
                status = checker.main(
                    [
                        str(input_path),
                        "--preset",
                        "regression-c10-d4",
                        "--output",
                        str(output_path),
                    ]
                )
            persisted = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(status, 2)
            self.assertEqual(stdout.getvalue(), "")
            self.assertEqual(observed["certificate_passes"], False)
            self.assertEqual(observed["error"], "exact calculation did not complete")
            self.assertEqual(persisted["certificate_passes"], False)
            self.assertEqual(persisted["error"], "synthetic certificate failure")
            self.assertEqual(json.loads(stderr.getvalue()), persisted)
            self.assertEqual(list(directory.glob(".*.tmp")), [])


if __name__ == "__main__":
    unittest.main()
