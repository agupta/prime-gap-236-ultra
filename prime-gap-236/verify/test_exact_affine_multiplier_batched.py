#!/usr/bin/env python3

import random
import sys
import unittest
from fractions import Fraction as Q
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from verify.affine_multiplier_oracle import compute_affine_literal
from verify.exact_affine_multiplier import affine_multipliers_from_mapping
from verify.exact_affine_multiplier_batched import (
    compute_affine_tagged_batched,
)
from verify.exact_capped_certificate import (
    Parameters,
    build_basis_terms,
    build_polynomial,
)


def parameters(k):
    return Parameters(
        name=f"exact-affine-batched-test-k{k}", k=k, degree=3,
        alpha=Q(2, 5), eta=Q(3, 10), delta=Q(1, 10),
        beta1=Q(1, 4), beta2=Q(3, 10), beta3plus=Q(7, 20))


class ExactBatchedAffineTests(unittest.TestCase):
    def check_case(self, k, labels, base, source):
        params = parameters(k)
        multipliers = affine_multipliers_from_mapping(params, source)
        terms = build_basis_terms(labels, base)
        expected = compute_affine_literal(
            build_polynomial(labels, base, k), params, source)
        for reverse in (False, True):
            for workers in (1, 2):
                with self.subTest(k=k, reverse=reverse, workers=workers):
                    self.assertEqual(
                        compute_affine_tagged_batched(
                            terms, params, multipliers,
                            reverse_faces=reverse, workers=workers),
                        expected)

    def test_signed_fixed_case_all_orders_and_workers(self):
        self.check_case(
            3,
            [(0, ()), (1, ()), (2, ()), (0, (2,)), (0, (3,))],
            [Q(2, 3), Q(-3, 5), Q(1, 7), Q(-2, 9), Q(4, 11)],
            {
                0: (Q(2), Q(-1), Q(3)),
                1: (Q(-4, 3), Q(5, 2), Q(-7, 4)),
                2: (Q(9, 5), Q(-11, 6), Q(13, 7)),
                3: (Q(-3, 2), Q(7, 3), Q(5, 4)),
            },
        )

    def test_deterministic_signed_random_cases(self):
        generator = random.Random(0x236B47C)
        for case in range(8):
            k = 2 + case % 2
            labels = [(0, ()), (1, ()), (2, ()), (0, (2,)), (0, (3,))]
            if k == 2:
                labels = labels[:-1]
            base = [Q(generator.randint(-9, 9), generator.randint(1, 11))
                    for _ in labels]
            if all(value == 0 for value in base):
                base[0] = Q(1)
            source = {
                r: tuple(Q(generator.randint(-13, 13),
                           generator.randint(1, 13)) for _ in range(3))
                for r in range(k + 1)
            }
            self.check_case(k, labels, base, source)


if __name__ == "__main__":
    unittest.main()
