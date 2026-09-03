#!/usr/bin/env python3
"""Exact regressions for the per-stratum span{1,L,Z} evaluator."""

import os
import sys
import unittest
from collections import defaultdict
from fractions import Fraction as Q

HERE = os.path.dirname(os.path.abspath(__file__))
AGENT = os.path.abspath(os.path.join(HERE, ".."))
sys.path[:0] = [AGENT, os.path.join(AGENT, "src")]

import exact_integrator as ei  # noqa: E402
from stratum_amplitude import StratumAmplitudeEvaluator  # noqa: E402
from stratum_linear import (  # noqa: E402
    StratumLinearEvaluator,
    exact_determinant,
    independent_gram_indices,
    quadratic,
)


def poly_mul(left, right):
    answer = [Q(0)] * (len(left) + len(right) - 1)
    for i, x in enumerate(left):
        for j, y in enumerate(right):
            answer[i + j] += x * y
    return answer


def poly_integral(poly, lo, hi):
    return sum((value * (hi ** (i + 1) - lo ** (i + 1)) / (i + 1)
                for i, value in enumerate(poly)), Q(0))


class StratumLinearTests(unittest.TestCase):
    def test_exact_discovery_prunes_null_L_at_R_zero(self):
        support = ei.OneStratumSupport(
            2, Q(1, 2), Q(1, 10), Q(1, 2),
            Q(1, 4), Q(9, 50), Q(9, 50))
        evaluator = StratumLinearEvaluator(
            support, [(0, ())], [Q(1)], Q)
        forms = evaluator.evaluate_forms()
        selected, discarded = independent_gram_indices(
            forms["a_matrix"], forms["labels"])
        discarded_labels = [forms["labels"][i] for i in discarded]
        self.assertIn((0, 1), discarded_labels)  # L=0 on the all-small stratum.
        reduced = [[forms["a_matrix"][i][j] for j in selected]
                   for i in selected]
        # Each retained R block has all exact leading principal minors > 0.
        offsets = defaultdict(list)
        for position, original in enumerate(selected):
            offsets[forms["labels"][original][0]].append(position)
        for positions in offsets.values():
            for size in range(1, len(positions) + 1):
                prefix = positions[:size]
                self.assertGreater(exact_determinant(
                    [[reduced[i][j] for j in prefix] for i in prefix]), 0)

    def test_cancelled_standard_marginal_does_not_drop_shifted_channel(self):
        # k=1, delta=1/10: Sdelta integrates t on the fixed interval [0,delta].
        # F0(t)=t-delta/2 has zero unweighted integral, while
        # integral t*F0(t) dt = delta^3/12 is nonzero.  The Z channel on a
        # small distinguished branch must retain precisely that shifted term.
        delta = Q(1, 10)
        support = ei.OneStratumSupport(
            1, Q(1, 5), delta, Q(3, 20),
            Q(3, 20), Q(3, 20), Q(17, 100))
        evaluator = StratumLinearEvaluator(
            support, [(0, ()), (0, (1,))], [-delta / 2, Q(1)], Q)
        _, lrs, by_lr = evaluator._j_component_data()
        blocks = evaluator._channel_branch_blocks(
            lrs, by_lr, 0, 0, 0, support.eta)
        self.assertEqual(blocks["Sdelta"][0], {})
        self.assertEqual(blocks["Sdelta"][2][()][(0, 0)], delta ** 3 / 12)
        entries, domains, _ = evaluator.evaluate_j_r_linear(lrs, by_lr, 0)
        self.assertGreater(domains, 0)
        self.assertEqual(entries[((0, 2), (0, 2))],
                         (delta ** 3 / 12) ** 2)

    def test_constant_channels_reduce_bitwise_to_stratum_amplitudes(self):
        support = ei.OneStratumSupport(
            3, Q(13, 50), Q(1, 20), Q(6, 25),
            Q(3, 20), Q(4, 25), Q(17, 100))
        labels = [(0, ()), (1, ()), (0, (2,)), (0, (3,))]
        coefficients = [Q(2), Q(-3), Q(5), Q(7)]
        linear = StratumLinearEvaluator(
            support, labels, coefficients, Q)
        forms = linear.evaluate_forms()
        amplitude_evaluator = StratumAmplitudeEvaluator(
            support, labels, coefficients, Q)
        amplitude = amplitude_evaluator.evaluate_all_blocks()
        for r in range(len(amplitude["a_diagonal"])):
            self.assertEqual(forms["a_matrix"][3 * r][3 * r],
                             amplitude["a_diagonal"][r])
            self.assertEqual(forms["b_matrix"][3 * r][3 * r],
                             amplitude["b_diagonal"][r])
            if r + 1 < len(amplitude["a_diagonal"]):
                self.assertEqual(forms["b_matrix"][3 * r][3 * (r + 1)],
                                 amplitude["b_superdiagonal"][r])

        # Compare the three common-r branch classes before diagonal assembly:
        # SS, SL (stored as an off-diagonal entry, hence half of twoSL), LL.
        _, lrs, by_lr = linear._j_component_data()
        for r in linear._r_values_j():
            linear_r, _, _ = linear.evaluate_j_r_linear(lrs, by_lr, r)
            amplitude_r, _ = amplitude_evaluator.evaluate_j_r_blocks(
                lrs, by_lr, r)
            ss, two_sl, ll = amplitude_r
            self.assertEqual(linear_r.get(((r, 0), (r, 0)), Q(0)), ss)
            self.assertEqual(linear_r.get(((r, 0), (r + 1, 0)), Q(0)),
                             two_sl / 2)
            self.assertEqual(linear_r.get(((r + 1, 0), (r + 1, 0)), Q(0)),
                             ll)
        constants = [Q(1) if p == 0 else Q(0)
                     for _, p in forms["labels"]]
        self.assertEqual(quadratic(forms["a_matrix"], constants, Q(0)),
                         amplitude["all_ones_denominator"])
        self.assertEqual(quadratic(forms["b_matrix"], constants, Q(0)),
                         amplitude["all_ones_numerator"])

        # Exact symmetry and the claimed block sparsity are explicit
        # falsification tests, not inferred from how the matrices were filled.
        for matrix in (forms["a_matrix"], forms["b_matrix"]):
            for i, (ri, _) in enumerate(forms["labels"]):
                for j, (rj, _) in enumerate(forms["labels"]):
                    self.assertEqual(matrix[i][j], matrix[j][i])
                    if matrix is forms["a_matrix"] and ri != rj:
                        self.assertEqual(matrix[i][j], 0)
                    if matrix is forms["b_matrix"] and abs(ri - rj) > 1:
                        self.assertEqual(matrix[i][j], 0)

    def test_signed_linear_vector_block_equals_fresh_direct_traversal(self):
        support = ei.OneStratumSupport(
            3, Q(13, 50), Q(1, 20), Q(6, 25),
            Q(3, 20), Q(4, 25), Q(17, 100))
        labels = [(0, ()), (1, ()), (0, (2,)), (0, (3,))]
        coefficients = [Q(2), Q(-3), Q(5), Q(7)]
        evaluator = StratumLinearEvaluator(
            support, labels, coefficients, Q)
        forms = evaluator.evaluate_forms()
        vector = [Q((-1) ** i * (i + 2), i + 3)
                  for i in range(len(forms["labels"]))]
        expected = (quadratic(forms["a_matrix"], vector, Q(0)),
                    quadratic(forms["b_matrix"], vector, Q(0)))
        direct = evaluator.evaluate_direct(vector)
        self.assertEqual(direct[:2], expected)
        self.assertEqual(direct[2], forms["i_faces"])
        self.assertEqual(direct[3], forms["j_branch_domains"])

    def test_k2_constant_polynomial_matches_hand_piece_recurrence(self):
        d, b = Q(1, 10), Q(1, 4)
        support = ei.OneStratumSupport(
            2, Q(1, 2), d, Q(1, 2), b, Q(9, 50), Q(9, 50))
        evaluator = StratumLinearEvaluator(
            support, [(0, ())], [Q(1)], Q)
        forms = evaluator.evaluate_forms()
        self.assertEqual(forms["labels"],
                         [(0, 0), (0, 1), (0, 2),
                          (1, 0), (1, 1), (1, 2)])

        expected_a0 = [
            [d * d, Q(0), d ** 3],
            [Q(0), Q(0), Q(0)],
            [d ** 3, Q(0), Q(7, 6) * d ** 4],
        ]
        c = b - d
        expected_a1 = [
            [2 * c * d, d * (b * b - d * d), c * d * d],
            [d * (b * b - d * d),
             Q(2, 3) * d * (b ** 3 - d ** 3),
             (b * b - d * d) * d * d / 2],
            [c * d * d, (b * b - d * d) * d * d / 2,
             Q(2, 3) * c * d ** 3],
        ]
        self.assertEqual(forms["i_blocks"][0], expected_a0)
        self.assertEqual(forms["i_blocks"][1], expected_a1)

        # Independent marginal polynomials on u intervals [0,d] and [d,b].
        # Coefficients are in ascending powers of u.
        ell = (b * b - d * d) / 2
        small_segment = [
            [d], [Q(0)], [d * d / 2, d],
            [c], [ell], [Q(0), c],
        ]
        large_segment = [
            [Q(0)], [Q(0)], [Q(0)],
            [d], [Q(0), d], [d * d / 2],
        ]
        expected_b = [[Q(0) for _ in range(6)] for _ in range(6)]
        for i in range(6):
            for j in range(6):
                j_value = poly_integral(poly_mul(
                    small_segment[i], small_segment[j]), Q(0), d)
                j_value += poly_integral(poly_mul(
                    large_segment[i], large_segment[j]), d, b)
                expected_b[i][j] = 2 * j_value
        self.assertEqual(forms["b_matrix"], expected_b)


if __name__ == "__main__":
    unittest.main()
