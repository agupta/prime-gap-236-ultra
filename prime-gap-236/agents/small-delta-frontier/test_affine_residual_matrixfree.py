#!/usr/bin/env python3
"""Independent small tests for the matrix-free affine residual recurrence."""

from __future__ import annotations

import json
import hashlib
import sys
import tempfile
import unittest
from decimal import Decimal, getcontext
from fractions import Fraction as Q
from pathlib import Path
from types import SimpleNamespace


HERE = Path(__file__).resolve().parent
ENGINE = HERE.parent / "exact-integrator"
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ENGINE))
sys.path.insert(0, str(ENGINE / "src"))

import exact_integrator as ei  # noqa: E402
from affine_residual_matrixfree import (  # noqa: E402
    MatrixFreeAffineResidual,
    load_baseline_result,
    two_vector_eigenvalue,
)
from stratum_linear import StratumLinearEvaluator  # noqa: E402


class MatrixFreeResidualTests(unittest.TestCase):
    def test_low_k_every_cross_and_diagonal(self):
        support = ei.OneStratumSupport(
            3, Q(2, 5), Q(1, 10), Q(3, 10),
            Q(1, 4), Q(3, 10), Q(7, 20))
        labels, base = [(0, ())], [Q(1)]
        full = StratumLinearEvaluator(
            support, labels, base, Q).evaluate_forms(False)
        coordinates = {
            (0, 0), (0, 2),
            (1, 0), (1, 1), (1, 2),
            (2, 0), (2, 1), (2, 2), (3, 0),
        }
        coefficients = {
            (r, p): Q((r + 1) * (p + 2), 7)
            for r in range(4) for p in range(3)
        }
        coefficients[(0, 1)] = Q(0)
        coefficients[(3, 1)] = coefficients[(3, 2)] = Q(0)
        got = MatrixFreeAffineResidual(
            support, labels, base, Q).evaluate_residual_data(
                coefficients, coordinates, False)
        position = {label: i for i, label in enumerate(full["labels"])}
        vector = [coefficients[label] for label in full["labels"]]
        for label in coordinates:
            i = position[label]
            expected_i = sum(full["a_matrix"][i][j] * vector[j]
                             for j in range(len(vector)))
            expected_j = sum(full["b_matrix"][i][j] * vector[j]
                             for j in range(len(vector)))
            self.assertEqual(got["i_cross"][label], expected_i)
            self.assertEqual(got["j_cross"][label], expected_j)
            self.assertEqual(got["i_diagonal"][label],
                             full["a_matrix"][i][i])
            self.assertEqual(got["j_diagonal"][label],
                             full["b_matrix"][i][i])
        self.assertEqual(got["i_faces"], 10)
        self.assertEqual(got["j_branch_domains"], 24)

    def test_stored_d4_run_covers_all_effective_coordinates(self):
        path = HERE / "c10_D4_affine_residual_all_exact.json"
        raw = json.loads(path.read_bytes())
        self.assertEqual(raw["oracle_status"],
                         "exact-cross-and-diagonal-match")
        self.assertIs(raw["rigorous_forms"], True)
        self.assertEqual(raw["effective_dimension"], 39)
        self.assertEqual(raw["screen_dimension"], 39)
        self.assertEqual(len(raw["rows"]), 39)
        self.assertEqual(raw["i_faces"], 312)
        self.assertEqual(raw["j_branch_domains"], 1200)
        self.assertEqual(raw["j_common_r"], list(range(16)))

    def test_current_source_bound_boundary_artifact(self):
        path = HERE / "c10_D4_affine_residual_boundary_exact.json"
        raw = json.loads(path.read_bytes())
        source_sha = hashlib.sha256(
            (HERE / "affine_residual_matrixfree.py").read_bytes()).hexdigest()
        self.assertEqual(raw["dependency_hashes"]["script"], source_sha)
        self.assertEqual(raw["oracle_status"],
                         "exact-cross-and-diagonal-match")
        self.assertEqual(raw["coordinates"], [
            [11, "1"], [11, "L"], [11, "Z"], [12, "1"], [13, "1"]])
        self.assertEqual(raw["i_faces"], 45)
        self.assertEqual(raw["j_common_r"], [10, 11, 12, 13])
        self.assertEqual(raw["j_branch_domains"], 222)

    def test_two_vector_formula(self):
        # A=identity, B=diag(2,3): maximum generalized eigenvalue is 3.
        value = two_vector_eigenvalue(
            Q(1), Q(2), Q(0), Q(0), Q(1), Q(3))
        self.assertEqual(str(value), "3")
        # Dependent Gram direction is rejected rather than divided by zero.
        self.assertIsNone(two_vector_eigenvalue(
            Q(1), Q(2), Q(1), Q(2), Q(1), Q(4)))

    def test_target_baseline_loader_and_count_mutation(self):
        getcontext().prec = 100
        args = SimpleNamespace(
            linear_cutoff=11, decimal_dps=100,
            alpha=Q(79247, 300000), delta=Q(1, 100),
            eta=Q(76247, 300000), beta1=Q(3, 20),
            beta2=Q(3, 20), beta3plus=Q(97, 625))
        raw = {
            "status": "multiprecision-transferred-affine-candidate",
            "complete": True, "rigorous": False, "theorem_ready": False,
            "linear_cutoff": 11, "input_sha256": "input",
            "multiplier_sha256": "multiplier", "decimal_dps": 100,
            "gates_passed": True, "fixed_basis_dimension": 272,
            "multiplier_dimension": 48, "marginal_components": 695,
            "j_branch_domains": 1200,
            "parameters": {
                "alpha": "79247/300000", "delta": "1/100",
                "eta": "76247/300000", "beta1": "3/20",
                "beta2": "3/20", "beta3plus": "97/625"},
            "denominator": "2", "numerator": "1", "quotient": "0.5",
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "baseline.json"
            path.write_text(json.dumps(raw))
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            _, denominator, numerator, quotient = load_baseline_result(
                path, digest, args, "input", "multiplier")
            self.assertEqual(
                (denominator, numerator, quotient),
                (Decimal(2), Decimal(1), Decimal("0.5")))
            raw["j_branch_domains"] = 1199
            path.write_text(json.dumps(raw))
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            with self.assertRaises(SystemExit):
                load_baseline_result(
                    path, digest, args, "input", "multiplier")


if __name__ == "__main__":
    unittest.main()
