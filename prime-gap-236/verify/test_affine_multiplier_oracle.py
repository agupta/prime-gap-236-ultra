#!/usr/bin/env python3

import sys
import unittest
from fractions import Fraction as Q
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EI = ROOT / "agents" / "exact-integrator"
sys.path[:0] = [str(ROOT), str(EI), str(EI / "src")]

import exact_integrator as ei
from stratum_linear import StratumLinearEvaluator
from stratum_linear_transfer_decimal import TransferEvaluator
from verify.affine_multiplier_oracle import (
    compute_affine_literal,
    compute_quadratic_literal,
)
from verify.exact_capped_certificate import Parameters, build_polynomial


class AffineMultiplierOracleTests(unittest.TestCase):
    def _compare(self, k, labels, base, multipliers):
        params = Parameters(
            name=f"affine-oracle-k{k}", k=k, degree=3,
            alpha=Q(2, 5), eta=Q(3, 10), delta=Q(1, 10),
            beta1=Q(1, 4), beta2=Q(3, 10), beta3plus=Q(7, 20))
        polynomial = build_polynomial(labels, base, k)
        expected = compute_affine_literal(polynomial, params, multipliers)
        support = ei.OneStratumSupport(
            k, params.alpha, params.delta, params.eta,
            params.beta1, params.beta2, params.beta3plus)
        producer = StratumLinearEvaluator(support, labels, base, Q)
        maximum_r = max(producer._r_values_i())
        vector = [x for r in range(maximum_r + 1)
                  for x in multipliers.get(r, (Q(0), Q(0), Q(0)))]
        direct = producer.evaluate_direct(vector)
        self.assertEqual(direct[:2], expected)

        transfer = TransferEvaluator(support, labels, base, Q)
        amplitudes = {r: tuple(vector[3*r:3*r+3])
                      for r in range(maximum_r + 1)}
        _, lrs, by_lr = transfer._j_component_data()
        pieces = [transfer.evaluate_j_r_transfer(
            lrs, by_lr, amplitudes, r)[0]
                  for r in transfer._r_values_j()]
        self.assertEqual(k * sum(pieces, Q(0)), expected[1])

    def test_signed_k3_all_small_large_branch_channels(self):
        labels = [(0, ()), (1, ()), (2, ()), (0, (2,)), (0, (3,))]
        base = [Q(2, 3), Q(-3, 5), Q(1, 7), Q(-2, 9), Q(4, 11)]
        multipliers = {
            0: (Q(2), Q(-1), Q(3)),
            1: (Q(-4, 3), Q(5, 2), Q(-7, 4)),
            2: (Q(9, 5), Q(-11, 6), Q(13, 7)),
            3: (Q(-3, 2), Q(7, 3), Q(5, 4)),
        }
        self._compare(3, labels, base, multipliers)

    def test_k2_cutoff_semantics_zeroes_only_high_r_LZ(self):
        labels = [(0, ()), (1, ()), (0, (2,))]
        base = [Q(5, 7), Q(-2, 3), Q(3, 11)]
        source = {
            0: (Q(2), Q(0), Q(-3)),
            1: (Q(-5), Q(7), Q(11)),
            2: (Q(13), Q(17), Q(-19)),
        }
        cutoff = 0
        truncated = {
            r: (a, b if r <= cutoff else Q(0),
                c if r <= cutoff else Q(0))
            for r, (a, b, c) in source.items()
        }
        self._compare(2, labels, base, truncated)

    def test_independent_quadratic_oracle_matches_direct_transfer_k3(self):
        k = 3
        params = Parameters(
            name="quadratic-oracle-k3", k=k, degree=3,
            alpha=Q(2, 5), eta=Q(3, 10), delta=Q(1, 10),
            beta1=Q(1, 4), beta2=Q(3, 10), beta3plus=Q(7, 20))
        labels = [(0, ()), (1, ()), (2, ()), (0, (2,)), (0, (3,))]
        base = [Q(2, 3), Q(-3, 5), Q(1, 7), Q(-2, 9), Q(4, 11)]
        multipliers = {
            r: tuple(Q((-1) ** (6*r+p) * (6*r+p+2), 6*r+p+3)
                     for p in range(6))
            for r in range(4)
        }
        polynomial = build_polynomial(labels, base, k)
        expected = compute_quadratic_literal(polynomial, params, multipliers)
        support = ei.OneStratumSupport(
            k, params.alpha, params.delta, params.eta,
            params.beta1, params.beta2, params.beta3plus)
        from stratum_quadratic import StratumQuadraticEvaluator
        from stratum_quadratic_transfer_decimal import DirectQuadraticTransfer
        vector = [x for r in range(4) for x in multipliers[r]]
        reference = StratumQuadraticEvaluator(
            support, labels, base, Q).evaluate_direct(vector)
        self.assertEqual(reference[:2], expected)
        transfer = DirectQuadraticTransfer(support, labels, base, Q)
        grouped = transfer.square_residual_terms()
        i_value = sum((transfer.evaluate_i_r_transfer(
            grouped, multipliers, r)[0] for r in transfer._r_values_i()), Q(0))
        _, lrs, by_lr = transfer._j_component_data()
        j_value = k * sum((transfer.evaluate_j_r_transfer(
            lrs, by_lr, multipliers, r)[0]
                           for r in transfer._r_values_j()), Q(0))
        self.assertEqual((i_value, j_value), expected)


if __name__ == "__main__":
    unittest.main()
