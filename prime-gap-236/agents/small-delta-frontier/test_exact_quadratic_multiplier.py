#!/usr/bin/env python3
"""Hostile low-k checks for the independent tagged quadratic backend."""

from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from fractions import Fraction as Q
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from verify.affine_multiplier_oracle import compute_quadratic_literal
from verify.dyadic_interval import DyadicInterval
from verify.exact_capped_certificate import (
    Parameters,
    build_basis_terms,
    build_polynomial,
    compute_i_tagged,
    compute_j_tagged,
)
from verify.exact_quadratic_multiplier import (
    CHANNELS,
    QuadraticMultipliers,
    compute_quadratic_tagged,
    load_exact_quadratic_multiplier,
    quadratic_multipliers_from_mapping,
)


def parameters(k: int) -> Parameters:
    return Parameters(
        name=f"tagged-quadratic-test-k{k}", k=k, degree=2,
        alpha=Q(2, 5), eta=Q(3, 10), delta=Q(1, 10),
        beta1=Q(1, 4), beta2=Q(3, 10), beta3plus=Q(7, 20))


def signed_case(k: int):
    labels = [(0, ()), (1, ()), (0, (2,))]
    base = [Q(2, 3), Q(-3, 5), Q(-2, 9)]
    values = {
        r: tuple(Q((-1) ** (6 * r + channel) * (6 * r + channel + 2),
                     6 * r + channel + 3)
                 for channel in range(6))
        for r in range(k + 1)
    }
    return labels, base, values


class ExactQuadraticMultiplierTests(unittest.TestCase):
    def test_signed_k2_and_k3_match_literal_oracle_both_orders(self):
        for k in (2, 3):
            params = parameters(k)
            labels, base, values = signed_case(k)
            expected = compute_quadratic_literal(
                build_polynomial(labels, base, k), params, values)
            terms = build_basis_terms(labels, base)
            multipliers = quadratic_multipliers_from_mapping(params, values)
            for reverse in (False, True):
                with self.subTest(k=k, reverse=reverse):
                    self.assertEqual(
                        compute_quadratic_tagged(
                            terms, params, multipliers,
                            reverse_faces=reverse, workers=1),
                        expected)

    def test_constant_channel_reduces_to_tagged_capped_backend(self):
        params = parameters(3)
        labels, base, _ = signed_case(3)
        terms = build_basis_terms(labels, base)
        multipliers = quadratic_multipliers_from_mapping(
            params, {r: (Q(1), Q(0), Q(0), Q(0), Q(0), Q(0))
                     for r in range(4)})
        actual_i, actual_kj = compute_quadratic_tagged(
            terms, params, multipliers)
        self.assertEqual(actual_i, compute_i_tagged(terms, params))
        self.assertEqual(actual_kj, params.k * compute_j_tagged(terms, params))

    def test_dyadic_encloses_signed_k2_literal_oracle(self):
        params = parameters(2)
        labels, base, values = signed_case(2)
        expected_i, expected_kj = compute_quadratic_literal(
            build_polynomial(labels, base, 2), params, values)
        DyadicInterval.configure(192, 64)
        terms = {label: DyadicInterval(value)
                 for label, value in build_basis_terms(labels, base).items()}
        multipliers = QuadraticMultipliers(tuple(
            tuple(DyadicInterval(value) for value in values[r])
            for r in range(3)))
        actual_i, actual_kj = compute_quadratic_tagged(
            terms, params, multipliers, reverse_faces=True)
        self.assertTrue(actual_i.contains(expected_i))
        self.assertTrue(actual_kj.contains(expected_kj))

    def test_actual_artifact_parser_and_semantic_mutation(self):
        params = Parameters(
            name="C10", k=48, degree=12,
            alpha=Q(79247, 300000), eta=Q(76247, 300000),
            delta=Q(1, 100), beta1=Q(3, 20), beta2=Q(3, 20),
            beta3plus=Q(97, 625))
        source = (ROOT / "agents/exact-integrator/results/"
                  "c10_stratum_quadratic_cappedopt_D4_exact.json")
        source_bytes = source.read_bytes()
        source_sha = hashlib.sha256(source_bytes).hexdigest()
        parsed = load_exact_quadratic_multiplier(source, params, source_sha)
        self.assertEqual(len(parsed.coefficients), 16)
        self.assertEqual(parsed.at(0)[1], Q(0))
        self.assertEqual(parsed.at(0)[3], Q(0))
        self.assertEqual(parsed.at(0)[4], Q(0))

        payload = json.loads(source_bytes)
        payload["active_quadratic_labels"] = list(
            payload["active_quadratic_labels"])
        payload["active_quadratic_labels"].append([0, "L"])
        encoded = (json.dumps(payload, separators=(",", ":")) + "\n").encode()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "mutated.json"
            path.write_bytes(encoded)
            with self.assertRaisesRegex(Exception, "active-label semantics"):
                load_exact_quadratic_multiplier(
                    path, params, hashlib.sha256(encoded).hexdigest())


if __name__ == "__main__":
    unittest.main()
