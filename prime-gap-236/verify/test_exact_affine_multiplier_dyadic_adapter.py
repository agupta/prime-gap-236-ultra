#!/usr/bin/env python3
"""Check that the independent exact-affine algebra accepts dyadic scalars.

This is deliberately separate from the grouped Decimal evaluator.  Geometry
parameters remain exact Fractions, while every coefficient entering the
polynomial algebra is enclosed before the independent tagged recurrence is
called.  A target-size driver may use this adapter as a second interval
reconstruction if the low-dimensional oracle test passes.
"""

import sys
import unittest
from fractions import Fraction as Q
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from verify.affine_multiplier_oracle import compute_affine_literal
from verify.dyadic_interval import DyadicInterval as D
from verify.exact_affine_multiplier import AffineMultipliers
from verify.exact_affine_multiplier_batched import compute_affine_tagged_batched
from verify.exact_capped_certificate import (
    Parameters,
    build_basis_terms,
    build_polynomial,
)


class IndependentDyadicAdapterTest(unittest.TestCase):
    def test_signed_k3_encloses_literal_oracle(self):
        params = Parameters(
            name="independent-dyadic-adapter-k3",
            k=3,
            degree=3,
            alpha=Q(2, 5),
            eta=Q(3, 10),
            delta=Q(1, 10),
            beta1=Q(1, 4),
            beta2=Q(3, 10),
            beta3plus=Q(7, 20),
        )
        labels = [(0, ()), (1, ()), (2, ()), (0, (2,)), (0, (3,))]
        base = [Q(2, 3), Q(-3, 5), Q(1, 7), Q(-2, 9), Q(4, 11)]
        source = {
            0: (Q(2), Q(-1), Q(3)),
            1: (Q(-4, 3), Q(5, 2), Q(-7, 4)),
            2: (Q(9, 5), Q(-11, 6), Q(13, 7)),
            3: (Q(-3, 2), Q(7, 3), Q(5, 4)),
        }
        exact_i, exact_kj = compute_affine_literal(
            build_polynomial(labels, base, params.k), params, source)

        D.configure(precision=256, shadow_bits=64)
        interval_terms = build_basis_terms(labels, [D(value) for value in base])
        interval_multiplier = AffineMultipliers(tuple(
            tuple(D(value) for value in source[r])
            for r in range(params.k + 1)
        ))
        interval_i, interval_kj = compute_affine_tagged_batched(
            interval_terms, params, interval_multiplier)

        self.assertIsInstance(interval_i, D)
        self.assertIsInstance(interval_kj, D)
        self.assertTrue(interval_i.contains(exact_i))
        self.assertTrue(interval_kj.contains(exact_kj))


if __name__ == "__main__":
    unittest.main()
