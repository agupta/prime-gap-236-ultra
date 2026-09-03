#!/usr/bin/env python3

import importlib.util
from fractions import Fraction as Q
from math import comb
from pathlib import Path
import sys
import unittest


HERE = Path(__file__).resolve()
SOURCE = (HERE.parents[1] / "code" /
          "bv_dilation_definition5_two_band_proxy_v2.py")
SPEC = importlib.util.spec_from_file_location("definition5_dilation_tested", SOURCE)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load Definition-5 dilation proxy")
M = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = M
SPEC.loader.exec_module(M)


def literal_one_dimensional_moment(nu, p, q, alpha, beta, eta):
    """Directly expand all three powers for dimension one."""
    exponent = nu[0] if nu else 0
    answer = Q(0)
    for d in range(p + 1):
        for e in range(q + 1):
            coefficient = ((-1) ** (d + e) * comb(p, d) * comb(q, e) *
                           alpha ** (p - d) * beta ** (q - e))
            answer += (coefficient * eta ** (exponent + d + e + 1) /
                       (exponent + d + e + 1))
    return answer


class Definition5DilationProxyV2Tests(unittest.TestCase):
    def test_two_residual_moment_matches_literal_dimension_one(self):
        for nu in ((), (2,), (4,)):
            for p, q in ((0, 0), (1, 3), (4, 2)):
                alpha, beta, eta = Q(3, 5), Q(7, 10), Q(1, 4)
                self.assertEqual(
                    M.two_residual_moment(
                        1, nu, p, q, alpha, beta, eta),
                    literal_one_dimensional_moment(
                        nu, p, q, alpha, beta, eta))

    def test_cross_product_has_no_unordered_factor_two(self):
        left = {(1, ()): Q(2), (2, (2,)): Q(3)}
        right = {(1, ()): Q(5), (3, (2,)): Q(7)}
        product = M.orbit_product_terms(left, right, symmetric=False)
        # The constant/constant product is a single ordered cross term.
        self.assertEqual(product[(1, 1, ())], 10)
        # P2*P2=P4+2P22 in sufficiently many variables.
        self.assertEqual(product[(2, 3, (4,))], 21)
        self.assertEqual(product[(2, 3, (2, 2))], 42)

    def test_symmetric_lower_pair_factor_and_signed_values(self):
        terms = {(1, ()): Q(2), (2, (2,)): Q(-3)}
        product = M.orbit_product_terms(terms, terms, symmetric=True)
        self.assertEqual(product[(1, 1, ())], 4)
        self.assertEqual(product[(2, 1, (2,))], -12)
        self.assertEqual(product[(2, 2, (4,))], 9)
        self.assertEqual(product[(2, 2, (2, 2))], 18)

    def test_definition5_tail_subtraction_algebra(self):
        b00, b00_wide, b22, cross = map(
            Q, ("2/5", "1/2", "9/10", "3/5"))
        b01 = cross - b00_wide
        b11 = b22 + b00_wide - 2 * cross
        self.assertEqual(b00 + 2 * b01 + b11,
                         b00 + b22 - b00_wide)
        self.assertNotEqual(b00, b00_wide)

    def test_stationary_amplitude_is_a_true_derivative_root(self):
        a00, a11 = Q(7, 5), Q(3, 4)
        b00, b01, b11 = Q(6, 5), Q(1, 7), Q(2, 3)
        root = M.stationary_amplitude(
            a00, a11, b00, b01, b11, 100)
        # Decimal residual uses exactly the coefficient convention in code.
        from decimal import Decimal, localcontext
        with localcontext() as context:
            context.prec = 80
            dec = lambda x: Decimal(x.numerator) / Decimal(x.denominator)
            residual = (dec(a11 * b01) * root * root +
                        dec(a11 * b00 - b11 * a00) * root -
                        dec(b01 * a00))
            self.assertLess(abs(residual), Decimal("1e-75"))

    def test_dependency_mutation_rejects(self):
        relative = next(iter(M.PINNED))
        expected = M.PINNED[relative]
        M.PINNED[relative] = "0" * 64
        try:
            with self.assertRaises(ValueError):
                M.validate_sources()
        finally:
            M.PINNED[relative] = expected

    def test_frozen_full_result_has_exact_negative_definition5_pencil(self):
        path = (HERE.parents[1] / "results" /
                "bv_D16_dilation_Definition5_two_band_exact_v2.json")
        self.assertEqual(
            M.sha256(path),
            "05410084611a86d04877ebe2b73a17899e45915fdf1b9b466a25996d28db3171")
        result = M.strict_json(path)
        self.assertEqual(
            result["script_sha256"],
            "0b322ed3b6ea45bfb4f6a7a57deebe34cc57f2a41df68f6f0a592c91dd848d95")
        a00 = M.parse_q(result["I_matrix"][0][0])
        a11 = M.parse_q(result["I_matrix"][1][1])
        b00 = M.parse_q(result["kJ_matrix"][0][0])
        b01 = M.parse_q(result["kJ_matrix"][0][1])
        b11 = M.parse_q(result["kJ_matrix"][1][1])
        self.assertGreater(a00, 0)
        self.assertGreater(a11, 0)
        self.assertEqual(result["I_matrix"][0][1], "0")
        self.assertEqual(result["I_matrix"][1][0], "0")
        self.assertEqual(result["kJ_matrix"][1][0], result["kJ_matrix"][0][1])
        rows = {row["name"]: row for row in result["rows"]}
        for row in rows.values():
            amplitude = M.parse_q(row["outer_amplitude"])
            expected = M.exact_row(
                row["name"], amplitude, a00, a11, b00, b01, b11)
            self.assertEqual(row, expected)
        unit_q = M.parse_q(rows["unit_outer_amplitude"]["quotient"])
        best_q = M.parse_q(
            rows["rationalized_stationary_amplitude"]["quotient"])
        self.assertLess(unit_q, best_q)
        self.assertLess(best_q, 1)
        diagnostics = result["cutoff_diagnostics"]
        self.assertLess(
            M.parse_q(diagnostics["Definition5_inner_quotient"]),
            M.parse_q(diagnostics["wide_cutoff_inner_quotient"]))
        self.assertGreater(
            M.parse_q(diagnostics["uncapped_one_band_outer_quotient"]), 1)


if __name__ == "__main__":
    unittest.main()
