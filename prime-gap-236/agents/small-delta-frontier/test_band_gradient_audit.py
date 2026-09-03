#!/usr/bin/env python3
"""Hostile, memory-light tests for the frozen sparse 20-band operator."""

from __future__ import annotations

import copy
import hashlib
import json
import sys
import tempfile
import unittest
from decimal import Decimal, localcontext
from fractions import Fraction as Q
from pathlib import Path


HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[1]
STRUCTURAL = PROJECT / "agents" / "structural-basis"
EXACT_AGENT = PROJECT / "agents" / "exact-integrator"
sys.path[:0] = [str(HERE), str(STRUCTURAL / "code"), str(EXACT_AGENT),
                str(EXACT_AGENT / "src")]

import exact_integrator as ei  # noqa: E402
from band_gradient_postprocess import (  # noqa: E402
    EXPECTED_GATES, PINNED, ValidationError, file_sha, process)
from band_operator import BandMap  # noqa: E402
from band_operator_sparse import SparseBandOperator  # noqa: E402


SOURCE = EXACT_AGENT / "results" / "hb_c10_fullsimplex_noones_D12.json"
BANDS = STRUCTURAL / "results" / "c10_D12_degree_bands.json"
BASELINE = EXACT_AGENT / "results" / \
    "c10_capped_fullD12_vector_grouped_mp100.json"
SPARSE = STRUCTURAL / "code" / "band_operator_sparse.py"


def quadratic(matrix, vector):
    return sum(vector[i] * matrix[i][j] * vector[j]
               for i in range(len(vector)) for j in range(len(vector)))


def compressed_matrix(matrix, band_map):
    n = band_map.dimension
    out = [[Q(0) for _ in range(n)] for _ in range(n)]
    for p in range(len(band_map.labels)):
        for q in range(len(band_map.labels)):
            out[band_map.owner[p]][band_map.owner[q]] += (
                band_map.weight_q[p] * band_map.weight_q[q] * matrix[p][q])
    return out


def matvec(matrix, vector):
    return [sum(matrix[i][j] * vector[j] for j in range(len(vector)))
            for i in range(len(vector))]


def synthetic_gradient():
    """A structurally valid target-shaped record for consumer mutation tests.

    This is not claimed to be the real gradient.  Its forms are pinned to the
    scalar baseline, while an exactly Euler-orthogonal perturbation is inserted
    into ``b_theta`` to exercise trial selection.
    """
    baseline = json.loads(BASELINE.read_bytes())
    band_map = BandMap.from_source_and_bands(str(SOURCE), str(BANDS))
    dps = 100
    with localcontext() as ctx:
        ctx.prec = dps
        theta = [Decimal(x.numerator) / Decimal(x.denominator)
                 for x in band_map.theta0_q]
        denominator = Decimal(baseline["denominator"])
        baseline_numerator = Decimal(baseline["numerator"])
        j0 = baseline_numerator / Decimal(48)
        numerator = Decimal(48) * j0
        quotient = numerator / denominator
        a = [Decimal(0)] * 20
        a[12] = denominator
        u = abs(numerator) / Decimal(100)
        b = [Decimal(0)] * 20
        b[12] = numerator + u
        b[13] = -u
        grad_d = [Decimal(2) * x for x in a]
        grad_n = [Decimal(2) * x for x in b]
        euler_d = sum((x * y for x, y in zip(theta, grad_d)), Decimal(0)) - \
            Decimal(2) * denominator
        euler_n = sum((x * y for x, y in zip(theta, grad_n)), Decimal(0)) - \
            Decimal(2) * numerator
        rel_d = abs(euler_d) / abs(denominator)
        rel_n = abs(euler_n) / abs(numerator)
    return {
        "status": "multiprecision-degree-band-gradient-discovery",
        "implementation": "sparse-structure-of-arrays",
        "rigorous": False,
        "complete": True,
        "decimal_dps": dps,
        "workers": 2,
        "source_json": str(SOURCE),
        "source_sha256": PINNED["source"],
        "bands_json": str(BANDS),
        "bands_sha256": PINNED["bands"],
        "operator_sha256": PINNED["sparse"],
        "band_operator_dependency_sha256": PINNED["band"],
        "integrator_sha256": PINNED["integrator"],
        "grouped_evaluator_sha256": PINNED["grouped"],
        "baseline_json": str(BASELINE),
        "baseline_sha256": PINNED["baseline"],
        "parameters": {"alpha": "79247/300000", "delta": "1/100",
                       "eta": "76247/300000", "beta1": "3/20",
                       "beta2": "3/20", "beta3plus": "97/625"},
        "theta": [str(x) for x in theta],
        "denominator": str(denominator),
        "numerator": str(numerator),
        "quotient": str(quotient),
        "a_theta": [str(x) for x in a],
        "b_theta": [str(x) for x in b],
        "grad_denominator": [str(x) for x in grad_d],
        "grad_numerator": [str(x) for x in grad_n],
        "euler_denominator_error": str(euler_d),
        "euler_numerator_error": str(euler_n),
        "i_orbit_groups": 1575,
        "i_faces": 312,
        "marginal_components": 695,
        "j_branch_integrals": 1200,
        "i_seconds": 1.0,
        "j_seconds": 2.0,
        "total_seconds": 3.0,
        "i_value_by_r": [str(denominator)] + ["0"] * 15,
        "j_value_by_r": [str(j0)] + ["0"] * 15,
        "peak_rss_kib": 1,
        "child_peak_rss_kib": 1,
        "gates_passed": True,
        "gates": {key: True for key in EXPECTED_GATES},
        "euler_denominator_relative": str(rel_d),
        "euler_numerator_relative": str(rel_n),
        "baseline_relative_tolerance": "1E-50",
    }


class SparseAlgebraAudit(unittest.TestCase):
    def test_signed_multiowner_action_equals_fresh_exact_matrices(self):
        support = ei.OneStratumSupport(
            3, Q(13, 50), Q(1, 20), Q(6, 25),
            Q(3, 20), Q(4, 25), Q(17, 100))
        labels = [(0, ()), (1, ()), (0, (2,)), (2, ()),
                  (1, (2,)), (0, (3,))]
        owners = [0, 0, 1, 2, 1, 0]
        weights = [Q(2), Q(-1, 3), Q(5, 2), Q(-4), Q(-2, 5), Q(7, 3)]
        theta = [Q(-3, 2), Q(4, 3), Q(5, 7)]
        band_map = BandMap.from_explicit(labels, owners, weights, theta)
        m1, m2 = support.matrices(labels)
        a = compressed_matrix(m1, band_map)
        b = compressed_matrix(m2, band_map)
        operator = SparseBandOperator(support, band_map, theta, Q)
        result = operator.apply(workers=1)
        self.assertEqual(result["denominator"], quadratic(a, theta))
        self.assertEqual(result["numerator"], quadratic(b, theta))
        self.assertEqual(list(result["a_theta"]), matvec(a, theta))
        self.assertEqual(list(result["b_theta"]), matvec(b, theta))
        self.assertEqual(result["grad_denominator"],
                         tuple(2 * x for x in matvec(a, theta)))
        self.assertEqual(result["grad_numerator"],
                         tuple(2 * x for x in matvec(b, theta)))
        self.assertEqual(result["euler_denominator_error"], 0)
        self.assertEqual(result["euler_numerator_error"], 0)

        serial_i = copy.deepcopy(operator.i_channels_by_r)
        serial_j = copy.deepcopy(operator.j_channels_by_r)
        parallel_operator = SparseBandOperator(support, band_map, theta, Q)
        parallel = parallel_operator.apply(workers=2)
        for key in ("denominator", "numerator", "quotient", "a_theta",
                    "b_theta", "grad_denominator", "grad_numerator",
                    "i_orbit_groups", "i_faces", "marginal_components",
                    "j_branch_integrals", "i_value_by_r", "j_value_by_r"):
            self.assertEqual(result[key], parallel[key], key)
        self.assertEqual(serial_i, parallel_operator.i_channels_by_r)
        self.assertEqual(serial_j, parallel_operator.j_channels_by_r)

    def test_target_k48_factor_and_geometry_counts_from_constant_oracle(self):
        support = ei.OneStratumSupport(
            48, Q(79247, 300000), Q(1, 100), Q(76247, 300000),
            Q(3, 20), Q(3, 20), Q(97, 625))
        band_map = BandMap.from_explicit([(0, ())], [0], [Q(2)], [Q(3)])
        result = SparseBandOperator(
            support, band_map, band_map.theta0_q, Q).apply(workers=1)
        m1, m2 = support.matrices([(0, ())])
        coefficient = Q(6)
        self.assertEqual(result["denominator"], coefficient ** 2 * m1[0][0])
        # m2 is independently defined as k*basis_j in exact_integrator.py.
        self.assertEqual(result["numerator"], coefficient ** 2 * m2[0][0])
        self.assertEqual(result["numerator"],
                         48 * sum(result["j_value_by_r"], Q(0)))
        self.assertEqual(result["i_faces"], 312)
        self.assertEqual(result["j_branch_integrals"], 1200)
        self.assertEqual(len(result["i_value_by_r"]), 16)
        self.assertEqual(len(result["j_value_by_r"]), 16)

    def test_actual_band_ownership_and_marginal_partition(self):
        band_map = BandMap.from_source_and_bands(str(SOURCE), str(BANDS))
        support = ei.OneStratumSupport(
            48, Q(79247, 300000), Q(1, 100), Q(76247, 300000),
            Q(3, 20), Q(3, 20), Q(97, 625))
        operator = SparseBandOperator(
            support, band_map, band_map.theta0_q, Q)
        value, directions = operator.marginal_component_channels()
        self.assertEqual(len(value), 695)
        reconstructed = {}
        for key in set().union(*(block.keys() for block in directions)):
            reconstructed[key] = sum(
                band_map.theta0_q[owner] * directions[owner].get(key, Q(0))
                for owner in range(20))
        reconstructed = {key: value for key, value in reconstructed.items() if value}
        self.assertEqual(reconstructed, value)
        counts = [sum(owner == j for owner in band_map.owner) for j in range(20)]
        self.assertEqual(counts, [1] * 12 + [7, 11, 15, 22, 30, 42, 56, 77])
        # Products of two complete D12 no-ones orbit bases can have precisely
        # the no-ones partitions of total degree at most 24.  This independent
        # combinatorial count explains the target fingerprint 1575; it is not
        # being copied from the producer's narrative.
        possible_product_orbits = {
            lam for degree in range(25)
            for lam in ei.integer_partitions(degree)
            if all(part >= 2 for part in lam)
        }
        self.assertEqual(len(possible_product_orbits), 1575)

    def test_one_action_cannot_determine_a_finite_trial(self):
        # theta=e0.  Adding s*v*v^T with v=e1 changes no value/gradient at
        # theta but changes every nonzero finite displacement along v.
        theta = [Q(1), Q(0)]
        trial = [Q(1), Q(1)]
        a0 = [[Q(1), Q(0)], [Q(0), Q(1)]]
        b0 = [[Q(9, 10), Q(0)], [Q(0), Q(1)]]
        a1 = [[Q(1), Q(0)], [Q(0), Q(101)]]
        b1 = [[Q(9, 10), Q(0)], [Q(0), Q(1001)]]
        for left, right in ((a0, a1), (b0, b1)):
            self.assertEqual(quadratic(left, theta), quadratic(right, theta))
            self.assertEqual(matvec(left, theta), matvec(right, theta))
        q0 = quadratic(b0, trial) / quadratic(a0, trial)
        q1 = quadratic(b1, trial) / quadratic(a1, trial)
        self.assertNotEqual(q0, q1)


class PostprocessorAudit(unittest.TestCase):
    def write_gradient(self, directory, payload):
        path = Path(directory) / "gradient.json"
        path.write_text(json.dumps(payload, indent=2) + "\n")
        return path, hashlib.sha256(path.read_bytes()).hexdigest()

    def test_valid_record_emits_only_a_rational_trial_needing_reevaluation(self):
        with tempfile.TemporaryDirectory() as tmp:
            gradient, gradient_sha = self.write_gradient(tmp, synthetic_gradient())
            output = Path(tmp) / "trial.json"
            result = process(gradient, gradient_sha, SOURCE, BANDS, output)
            self.assertEqual(result["status"],
                             "rational-band-trial-needs-independent-reevaluation")
            self.assertFalse(result["rigorous"])
            self.assertFalse(result["theorem_ready"])
            self.assertFalse(result["proves_improvement"])
            self.assertEqual(len(result["rational_vector"]), 272)
            self.assertEqual(file_sha(output), hashlib.sha256(
                output.read_bytes()).hexdigest())
            band_map = BandMap.from_source_and_bands(str(SOURCE), str(BANDS))
            self.assertEqual(
                [Q(x) for x in result["rational_vector"]],
                band_map.expand([Q(x) for x in result["trial_theta_rational"]]))

    def test_mutations_and_extra_fields_fail_closed(self):
        cases = []
        extra = synthetic_gradient()
        extra["untrusted"] = True
        cases.append(extra)
        bad_half = synthetic_gradient()
        bad_half["grad_numerator"][0] = "1"
        cases.append(bad_half)
        bad_factor = synthetic_gradient()
        bad_factor["j_value_by_r"][0] = bad_factor["numerator"]
        cases.append(bad_factor)
        for index, payload in enumerate(cases):
            with self.subTest(index=index), tempfile.TemporaryDirectory() as tmp:
                gradient, gradient_sha = self.write_gradient(tmp, payload)
                with self.assertRaises(ValidationError):
                    process(gradient, gradient_sha, SOURCE, BANDS,
                            Path(tmp) / "trial.json")

    def test_wrong_sha_and_protected_output_collision_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            gradient, gradient_sha = self.write_gradient(tmp, synthetic_gradient())
            with self.assertRaisesRegex(ValidationError, "gradient byte SHA"):
                process(gradient, "0" * 64, SOURCE, BANDS,
                        Path(tmp) / "trial.json")
            source_sha = file_sha(SOURCE)
            with self.assertRaisesRegex(ValidationError, "collides"):
                process(gradient, gradient_sha, SOURCE, BANDS, SOURCE)
            self.assertEqual(file_sha(SOURCE), source_sha)

    def test_current_producer_has_postcheck_output_alias_counterexample(self):
        text = SPARSE.read_text()
        hash_end = text.index("operator_hash_end =")
        write = text.index("Path(args.output).write_text")
        self.assertLess(hash_end, write)
        self.assertNotIn("output path collides", text)
        self.assertNotIn("source_hash_end", text)
        self.assertNotIn("bands_hash_end", text)


if __name__ == "__main__":
    unittest.main()
