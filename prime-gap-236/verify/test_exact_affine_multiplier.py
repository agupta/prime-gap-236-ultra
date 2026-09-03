#!/usr/bin/env python3

import hashlib
import json
import sys
import tempfile
import unittest
from fractions import Fraction as Q
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from verify.affine_multiplier_oracle import compute_affine_literal
from verify.exact_affine_multiplier import (
    affine_multipliers_from_mapping,
    compute_affine_tagged,
    load_exact_affine_multiplier,
)
from verify.exact_capped_certificate import (
    CertificateError,
    Parameters,
    build_basis_terms,
    build_polynomial,
    compute_i_tagged,
    compute_j_tagged,
)


def parameters(k):
    return Parameters(
        name=f"exact-affine-test-k{k}", k=k, degree=3,
        alpha=Q(2, 5), eta=Q(3, 10), delta=Q(1, 10),
        beta1=Q(1, 4), beta2=Q(3, 10), beta3plus=Q(7, 20))


class ExactTaggedAffineTests(unittest.TestCase):
    def test_signed_k3_matches_literal_in_both_orders_and_worker_counts(self):
        params = parameters(3)
        labels = [(0, ()), (1, ()), (2, ()), (0, (2,)), (0, (3,))]
        base = [Q(2, 3), Q(-3, 5), Q(1, 7), Q(-2, 9), Q(4, 11)]
        source = {
            0: (Q(2), Q(-1), Q(3)),
            1: (Q(-4, 3), Q(5, 2), Q(-7, 4)),
            2: (Q(9, 5), Q(-11, 6), Q(13, 7)),
            3: (Q(-3, 2), Q(7, 3), Q(5, 4)),
        }
        multipliers = affine_multipliers_from_mapping(params, source)
        basis_terms = build_basis_terms(labels, base)
        polynomial = build_polynomial(labels, base, params.k)
        expected = compute_affine_literal(polynomial, params, source)
        for reverse in (False, True):
            for workers in (1, 2):
                with self.subTest(reverse=reverse, workers=workers):
                    self.assertEqual(
                        compute_affine_tagged(
                            basis_terms, params, multipliers,
                            reverse_faces=reverse, workers=workers),
                        expected)

    def test_constant_multiplier_reduces_to_audited_tagged_backend(self):
        params = parameters(3)
        labels = [(0, ()), (1, ()), (0, (2,)), (0, (3,))]
        base = [Q(5, 7), Q(-2, 3), Q(3, 11), Q(-4, 13)]
        basis_terms = build_basis_terms(labels, base)
        multipliers = affine_multipliers_from_mapping(
            params, {r: (Q(1), Q(0), Q(0)) for r in range(4)})
        actual_i, actual_m2 = compute_affine_tagged(
            basis_terms, params, multipliers)
        self.assertEqual(actual_i, compute_i_tagged(basis_terms, params))
        self.assertEqual(
            actual_m2, params.k * compute_j_tagged(basis_terms, params))

    def test_cutoff_and_exact_artifact_parser_fail_closed(self):
        params = parameters(2)
        source = {
            0: (Q(2), Q(0), Q(-3)),
            1: (Q(-5), Q(7), Q(11)),
            2: (Q(13), Q(17), Q(-19)),
        }
        payload = {
            "status": "exact-stratum-linear-rational-vector",
            "k": 2,
            "rigorous_forms": True,
            "block_direct_bitwise_equal": True,
            "linear_labels": [[r, channel]
                              for r in range(3)
                              for channel in ("1", "L", "Z")],
            "rational_vector": [str(value)
                                for r in range(3)
                                for value in source[r]],
        }
        encoded = (json.dumps(payload, separators=(",", ":")) + "\n").encode()
        expected_sha = hashlib.sha256(encoded).hexdigest()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "multiplier.json"
            path.write_bytes(encoded)
            parsed = load_exact_affine_multiplier(
                path, params, expected_sha, linear_cutoff=0)
            self.assertEqual(parsed.at(0), source[0])
            self.assertEqual(parsed.at(1), (source[1][0], Q(0), Q(0)))
            self.assertEqual(parsed.at(2), (source[2][0], Q(0), Q(0)))
            labels = [(0, ()), (1, ()), (0, (2,))]
            base = [Q(5, 7), Q(-2, 3), Q(3, 11)]
            expected_mapping = {
                r: (a, b if r == 0 else Q(0), c if r == 0 else Q(0))
                for r, (a, b, c) in source.items()
            }
            expected = compute_affine_literal(
                build_polynomial(labels, base, params.k),
                params, expected_mapping)
            self.assertEqual(
                compute_affine_tagged(
                    build_basis_terms(labels, base), params, parsed),
                expected)

            path.write_bytes(encoded + b" ")
            with self.assertRaises(CertificateError):
                load_exact_affine_multiplier(
                    path, params, expected_sha, linear_cutoff=0)

            malformed = dict(payload)
            malformed["linear_labels"] = list(payload["linear_labels"])
            malformed["linear_labels"][1] = [0, "Z"]
            broken = (json.dumps(malformed, separators=(",", ":")) + "\n").encode()
            path.write_bytes(broken)
            with self.assertRaises(CertificateError):
                load_exact_affine_multiplier(
                    path, params, hashlib.sha256(broken).hexdigest(),
                    linear_cutoff=0)


if __name__ == "__main__":
    unittest.main()
