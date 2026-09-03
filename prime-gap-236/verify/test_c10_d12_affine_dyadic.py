#!/usr/bin/env python3

import sys
import unittest
from fractions import Fraction as Q
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENGINE = ROOT / "agents/exact-integrator"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ENGINE))
sys.path.insert(0, str(ENGINE / "src"))

import exact_integrator as ei
from grouped_fixed_vector import precompute_orbits
from verify.affine_multiplier_oracle import compute_affine_literal
from verify.check_c10_d12_affine_dyadic import (
    BASE_PATH,
    DyadicTransferEvaluator,
    DyadicCertificateError,
    interval_data,
    interval_from_data,
    reverse_count_methods,
    validate_output_paths,
)
from dyadic_backend import install_dyadic
from verify.exact_capped_certificate import (
    Parameters,
    build_polynomial,
)


class DyadicResultDriverTests(unittest.TestCase):
    def test_signed_grouped_traversal_contains_independent_exact_oracle(self):
        params = Parameters(
            name="dyadic-result-driver-k3", k=3, degree=3,
            alpha=Q(2, 5), eta=Q(3, 10), delta=Q(1, 10),
            beta1=Q(1, 4), beta2=Q(3, 10), beta3plus=Q(7, 20))
        labels = [(0, ()), (1, ()), (2, ()), (0, (2,)), (0, (3,))]
        base = [Q(2, 3), Q(-3, 5), Q(1, 7), Q(-2, 9), Q(4, 11)]
        source = {
            0: (Q(2), Q(-1), Q(3)),
            1: (Q(-4, 3), Q(5, 2), Q(-7, 4)),
            2: (Q(9, 5), Q(-11, 6), Q(13, 7)),
            3: (Q(-3, 2), Q(7, 3), Q(5, 4)),
        }
        expected_i, expected_kj = compute_affine_literal(
            build_polynomial(labels, base, params.k), params, source)

        orbit_table = precompute_orbits(labels, params.k)
        scalar = install_dyadic(orbit_table, precision=384, shadow_bits=96)
        support = ei.OneStratumSupport(
            params.k,
            scalar(params.alpha.numerator, params.alpha.denominator),
            scalar(params.delta.numerator, params.delta.denominator),
            scalar(params.eta.numerator, params.eta.denominator),
            scalar(params.beta1.numerator, params.beta1.denominator),
            scalar(params.beta2.numerator, params.beta2.denominator),
            scalar(params.beta3plus.numerator, params.beta3plus.denominator),
        )
        evaluator = DyadicTransferEvaluator(
            support, labels,
            [scalar(value.numerator, value.denominator) for value in base],
            scalar)
        amplitudes = {
            r: tuple(scalar(value.numerator, value.denominator)
                     for value in source[r])
            for r in source
        }
        actual_i, groups, faces = evaluator.evaluate_i_transfer(amplitudes)
        actual_kj, components, domains = evaluator.evaluate_j_transfer(
            amplitudes)
        self.assertTrue(actual_i.contains(expected_i))
        self.assertTrue(actual_kj.contains(expected_kj))
        self.assertGreater(groups, 0)
        self.assertGreater(faces, 0)
        self.assertGreater(components, 0)
        self.assertGreater(domains, 0)

        # The reverse-count traversal is a separate summation order and must
        # enclose the same exact values without relying on byte equality of
        # rounded endpoints.
        reverse_count_methods(evaluator)
        reverse_i, reverse_groups, reverse_faces = \
            evaluator.evaluate_i_transfer(amplitudes)
        reverse_kj, reverse_components, reverse_domains = \
            evaluator.evaluate_j_transfer(amplitudes)
        self.assertTrue(reverse_i.contains(expected_i))
        self.assertTrue(reverse_kj.contains(expected_kj))
        self.assertEqual((reverse_groups, reverse_faces), (groups, faces))
        self.assertEqual((reverse_components, reverse_domains),
                         (components, domains))

        encoded = interval_data(actual_i)
        decoded = interval_from_data(encoded, "test I", 384)
        self.assertEqual((decoded.lo, decoded.hi),
                         (actual_i.lo, actual_i.hi))
        malformed = dict(encoded)
        malformed["width_units"] += 1
        with self.assertRaises(Exception):
            interval_from_data(malformed, "test I", 384)

        with self.assertRaises(DyadicCertificateError):
            validate_output_paths(Path("same.json"), Path("same.json"))
        with self.assertRaises(DyadicCertificateError):
            validate_output_paths(BASE_PATH, Path("otherwise-safe.json"))


if __name__ == "__main__":
    unittest.main()
