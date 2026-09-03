#!/usr/bin/env python3
"""Independent exact audit tests for the face-grouped fixed-vector evaluator.

These tests deliberately compare the grouped contraction with the older
pairwise matrix path only on tiny instances.  They do not trust a serialized
matrix and exercise odd/repeated orbit labels and every pair of conditional-J
branches.
"""

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from collections import Counter, defaultdict
from fractions import Fraction as Q
from pathlib import Path


HERE = os.path.dirname(os.path.abspath(__file__))
EXACT_AGENT = os.path.abspath(os.path.join(HERE, "..", "..", "exact-integrator"))
EXACT_SRC = os.path.join(EXACT_AGENT, "src")
sys.path[:0] = [EXACT_AGENT, EXACT_SRC]

import exact_integrator as ei  # noqa: E402
from grouped_fixed_vector import GroupedEvaluator  # noqa: E402


def poly_add(target, source, factor=Q(1)):
    for monomial, value in source.items():
        target[monomial] += factor * value
        if target[monomial] == 0:
            del target[monomial]


def ordered_orbit_product(left, right):
    """Literal ordered product, used to audit unordered-pair factors."""
    answer = {}
    for lr, p in left.items():
        for mr, q in right.items():
            pq = ei._poly_mul(p, q)
            for nu, multiplicity in ei.multiply_monomial_orbits(lr, mr):
                dest = answer.setdefault(nu, defaultdict(Q))
                poly_add(dest, pq, Q(multiplicity))
    return {nu: dict(poly) for nu, poly in answer.items() if poly}


def add_orbit_products(a, b):
    answer = {nu: defaultdict(Q, poly) for nu, poly in a.items()}
    for nu, poly in b.items():
        dest = answer.setdefault(nu, defaultdict(Q))
        poly_add(dest, poly)
    return {nu: dict(poly) for nu, poly in answer.items() if poly}


class GroupedEvaluatorAudit(unittest.TestCase):
    def exact_quadratic_check(self, support, labels, vector):
        grouped = GroupedEvaluator(support, labels, vector, Q)
        denominator, _, _ = grouped.evaluate_i()
        j_value, _, _ = grouped.evaluate_j()
        m1, m2 = support.matrices(labels)
        self.assertEqual(denominator, ei.exact_quadratic(m1, vector))
        self.assertEqual(support.k * j_value, ei.exact_quadratic(m2, vector))

    def test_grouped_equals_pairwise_mixed_odd_orbits_k3(self):
        support = ei.OneStratumSupport(
            3, Q(13, 50), Q(1, 20), Q(6, 25),
            Q(3, 20), Q(4, 25), Q(17, 100))
        self.exact_quadratic_check(
            support,
            [(0, ()), (1, ()), (0, (2,)), (0, (3,))],
            [Q(2), Q(-3), Q(5), Q(7)])

    def test_grouped_equals_pairwise_repeated_parts_k4(self):
        support = ei.OneStratumSupport(
            4, Q(27, 100), Q(1, 25), Q(6, 25),
            Q(3, 20), Q(4, 25), Q(9, 50))
        self.exact_quadratic_check(
            support,
            [(0, ()), (2, ()), (0, (2, 2)), (1, (3,))],
            [Q(11, 3), Q(-5, 2), Q(7, 4), Q(2, 9)])

    def test_unordered_branch_and_orbit_factors(self):
        support = ei.OneStratumSupport(
            4, Q(27, 100), Q(1, 25), Q(6, 25),
            Q(3, 20), Q(4, 25), Q(9, 50))
        grouped = GroupedEvaluator(support, [], [], Q)
        left = {
            (): {(0, 0): Q(2), (1, 0): Q(-3)},
            (2,): {(0, 1): Q(5)},
            (3,): {(1, 1): Q(7)},
        }
        right = {
            (): {(0, 0): Q(-11)},
            (2,): {(2, 0): Q(13), (0, 1): Q(17)},
        }

        # Same-branch unordered contraction must equal the literal ordered
        # square, including unequal-orbit terms twice.
        self.assertEqual(
            grouped.branch_orbit_product(left, left, True),
            ordered_orbit_product(left, left))

        # An unordered pair of *different* branches represents both orders.
        expected_cross = add_orbit_products(
            ordered_orbit_product(left, right),
            ordered_orbit_product(right, left))
        self.assertEqual(
            grouped.branch_orbit_product(left, right, False), expected_cross)

    def test_c10_complementary_branch_intersections_have_zero_measure(self):
        support = ei.OneStratumSupport(
            48, Q(79247, 300000), Q(1, 100), Q(76247, 300000),
            Q(3, 20), Q(3, 20), Q(97, 625))
        grouped = GroupedEvaluator(support, [], [], Q)
        dimension = 47
        one = {(0, 0): Q(1)}
        tested = 0
        max_r = min(dimension, support.max_large())
        for r in range(max_r + 1):
            max_h = int(support.eta // support.delta) - r
            for h in range(max_h + 1):
                outer = support.eta - (r + h) * support.delta
                if outer <= 0:
                    continue
                for left, right in (("Sdelta", "Stotal"),
                                    ("Ltotal", "Lbig")):
                    constraints = grouped.branch_domain(r, h, left, right)
                    if constraints is None:
                        continue
                    self.assertEqual(
                        grouped.integrate_domain(
                            one, dimension, r, outer, constraints),
                        Q(0),
                        msg=(r, h, left, right, constraints))
                    tested += 1
        self.assertGreater(tested, 0)

    def test_c10_positive_measure_branch_counts(self):
        """Exact geometry counts used by the safe pre-contraction filter."""
        support = ei.OneStratumSupport(
            48, Q(79247, 300000), Q(1, 100), Q(76247, 300000),
            Q(3, 20), Q(3, 20), Q(97, 625))
        grouped = GroupedEvaluator(support, [], [], Q)
        dimension = 47
        one = {(0, 0): Q(1)}
        branches = ("Sdelta", "Stotal", "Ltotal", "Lbig")
        active_branches = Counter()
        faces = raw_pairs = positive_pairs = 0
        for r in range(min(dimension, support.max_large()) + 1):
            max_h = int(support.eta // support.delta) - r
            for h in range(max_h + 1):
                outer = support.eta - (r + h) * support.delta
                if outer <= 0:
                    continue
                faces += 1
                for branch in branches:
                    constraints = support._branch_constraints(r, h, branch)
                    if (constraints is not None and
                            grouped.integrate_domain(
                                one, dimension, r, outer, constraints) > 0):
                        active_branches[branch] += 1
                for i, left in enumerate(branches):
                    for j in range(i + 1):
                        right = branches[j]
                        raw_pairs += 1
                        constraints = grouped.branch_domain(
                            r, h, left, right)
                        if (constraints is not None and
                                grouped.integrate_domain(
                                    one, dimension, r, outer, constraints) > 0):
                            positive_pairs += 1
        self.assertEqual(faces, 296)
        self.assertEqual(raw_pairs, 2960)
        self.assertEqual(positive_pairs, 1200)
        self.assertEqual(active_branches, Counter({
            "Sdelta": 296,
            "Ltotal": 285,
            "Lbig": 167,
        }))

    def test_zero_dimensional_l_branch_tie_is_assigned_once(self):
        # In J for k=2, the face r=1 has no shared small coordinate, so w=0.
        # If beta(r+1)=alpha, Ltotal and Lbig would agree on an interval rather
        # than merely a measure-zero point.  The source convention assigns that
        # tie to Ltotal by suppressing Lbig.
        support = ei.OneStratumSupport(
            2, Q(1, 4), Q(1, 20), Q(6, 25),
            Q(3, 20), Q(1, 4), Q(1, 4))
        self.assertIsNotNone(support._branch_constraints(1, 0, "Ltotal"))
        self.assertIsNone(support._branch_constraints(1, 0, "Lbig"))
        self.exact_quadratic_check(
            support,
            [(0, ()), (1, ()), (0, (2,))],
            [Q(3), Q(-2), Q(5)])

    def test_completed_pass_releases_face_and_radial_caches(self):
        support = ei.OneStratumSupport(
            3, Q(13, 50), Q(1, 20), Q(6, 25),
            Q(3, 20), Q(4, 25), Q(17, 100))
        labels = [(0, ()), (1, ()), (0, (2,)), (0, (3,))]
        vector = [Q(2), Q(-3), Q(5), Q(7)]
        grouped = GroupedEvaluator(support, labels, vector, Q)
        grouped.evaluate_i()
        self.assertEqual(grouped.orbit_density.cache_info().currsize, 0)
        self.assertEqual(ei._large_shift_dp.cache_info().currsize, 0)
        self.assertEqual(ei._small_box_dp.cache_info().currsize, 0)
        self.assertEqual(ei._selected_exponent_splits.cache_info().currsize, 0)
        grouped.evaluate_j()
        self.assertEqual(grouped.orbit_density.cache_info().currsize, 0)
        self.assertEqual(ei._large_shift_dp.cache_info().currsize, 0)
        self.assertEqual(ei._small_box_dp.cache_info().currsize, 0)
        self.assertEqual(ei._selected_exponent_splits.cache_info().currsize, 0)
        self.assertEqual(support._marginal_poly.cache_info().currsize, 0)

    def test_exact_serial_equals_two_fork_workers(self):
        support = ei.OneStratumSupport(
            4, Q(27, 100), Q(1, 25), Q(6, 25),
            Q(3, 20), Q(4, 25), Q(9, 50))
        labels = [(0, ()), (2, ()), (0, (2, 2)), (1, (3,))]
        vector = [Q(11, 3), Q(-5, 2), Q(7, 4), Q(2, 9)]
        serial = GroupedEvaluator(support, labels, vector, Q)
        parallel = GroupedEvaluator(support, labels, vector, Q)
        serial_i = serial.evaluate_i(workers=1)
        serial_j = serial.evaluate_j(workers=1)
        parallel_i = parallel.evaluate_i(workers=2)
        parallel_j = parallel.evaluate_j(workers=2)
        self.assertEqual(parallel_i, serial_i)
        self.assertEqual(parallel_j, serial_j)

    def test_k1_zero_dimensional_j_matches_reference(self):
        support = ei.OneStratumSupport(
            1, Q(1, 4), Q(1, 20), Q(6, 25),
            Q(3, 20), Q(3, 20), Q(17, 100))
        grouped = GroupedEvaluator(support, [(0, ())], [Q(1)], Q)
        denominator, _, _ = grouped.evaluate_i()
        j_value, _, _ = grouped.evaluate_j()
        self.assertEqual(denominator, Q(3, 20))
        self.assertEqual(j_value, Q(9, 400))
        self.assertEqual(
            j_value, support.basis_j((0, ()), (0, ())))

    def test_k1_small_branch_boundary_is_assigned_once(self):
        # At alpha=delta the Sdelta and Stotal conditions both contain the
        # sole aggregate point if interpreted as closed halfplanes.  In zero
        # dimensions that point has unit 0D measure, so the interval convention
        # must assign it to Stotal only rather than count two diagonal branches.
        support = ei.OneStratumSupport(
            1, Q(1, 10), Q(1, 10), Q(1, 10),
            Q(1, 20), Q(1, 20), Q(1, 20))
        grouped = GroupedEvaluator(support, [(0, ())], [Q(1)], Q)
        denominator, _, _ = grouped.evaluate_i()
        j_value, _, _ = grouped.evaluate_j()
        self.assertEqual(denominator, Q(1, 10))
        self.assertEqual(j_value, Q(1, 100))
        self.assertEqual(
            j_value, support.basis_j((0, ()), (0, ())))

    def test_rigorous_stage_fails_closed_on_integrator_hash(self):
        script = Path(EXACT_AGENT) / "grouped_fixed_vector.py"
        source = Path(EXACT_SRC) / "exact_integrator.py"
        raw = {"k": 1, "basis": [[0, []]], "rational_vector": ["1"]}
        parameters = {
            "alpha": "1/4", "delta": "1/20", "eta": "6/25",
            "beta1": "3/20", "beta2": "3/20", "beta3plus": "17/100",
        }
        with tempfile.TemporaryDirectory() as tmp:
            input_path = Path(tmp) / "input.json"
            stage_path = Path(tmp) / "stage.json"
            input_path.write_text(json.dumps(raw), encoding="utf-8")
            input_hash = hashlib.sha256(input_path.read_bytes()).hexdigest()
            stage = {
                "i_complete": True,
                "rigorous": True,
                "decimal_dps": None,
                "input_sha256": input_hash,
                "script_sha256": hashlib.sha256(script.read_bytes()).hexdigest(),
                "integrator_sha256": "0" * 64,
                "parameters": parameters,
                "denominator": "3/20",
                "i_orbit_groups": 1,
                "i_faces": 1,
                "i_seconds": 0,
            }
            stage_path.write_text(json.dumps(stage), encoding="utf-8")
            command = [
                sys.executable, str(script), str(input_path),
                "--alpha", parameters["alpha"],
                "--delta", parameters["delta"],
                "--eta", parameters["eta"],
                "--beta1", parameters["beta1"],
                "--beta2", parameters["beta2"],
                "--beta3plus", parameters["beta3plus"],
                "--resume-i-stage", str(stage_path),
                # This escape hatch is allowed only for legacy non-rigorous
                # discovery stages and must not weaken an exact run.
                "--accept-legacy-i-stage-no-integrator-sha",
            ]
            completed = subprocess.run(
                command, capture_output=True, text=True, check=False)
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("I-stage mismatch for integrator_sha256",
                          completed.stderr + completed.stdout)
            self.assertNotEqual(
                stage["integrator_sha256"],
                hashlib.sha256(source.read_bytes()).hexdigest())

    def test_rigorous_stage_rejects_explicit_script_hash_override(self):
        script = Path(EXACT_AGENT) / "grouped_fixed_vector.py"
        source = Path(EXACT_SRC) / "exact_integrator.py"
        raw = {"k": 1, "basis": [[0, []]], "rational_vector": ["1"]}
        parameters = {
            "alpha": "1/4", "delta": "1/20", "eta": "6/25",
            "beta1": "3/20", "beta2": "3/20", "beta3plus": "17/100",
        }
        stale_hash = "f" * 64
        with tempfile.TemporaryDirectory() as tmp:
            input_path = Path(tmp) / "input.json"
            stage_path = Path(tmp) / "stage.json"
            input_path.write_text(json.dumps(raw), encoding="utf-8")
            stage = {
                "i_complete": True,
                "rigorous": True,
                "decimal_dps": None,
                "input_sha256": hashlib.sha256(
                    input_path.read_bytes()).hexdigest(),
                "script_sha256": stale_hash,
                "integrator_sha256": hashlib.sha256(
                    source.read_bytes()).hexdigest(),
                "parameters": parameters,
                "denominator": "3/20",
                "i_orbit_groups": 1,
                "i_faces": 1,
                "i_seconds": 0,
            }
            stage_path.write_text(json.dumps(stage), encoding="utf-8")
            command = [
                sys.executable, str(script), str(input_path),
                "--alpha", parameters["alpha"],
                "--delta", parameters["delta"],
                "--eta", parameters["eta"],
                "--beta1", parameters["beta1"],
                "--beta2", parameters["beta2"],
                "--beta3plus", parameters["beta3plus"],
                "--resume-i-stage", str(stage_path),
                "--accept-i-stage-script-sha", stale_hash,
            ]
            completed = subprocess.run(
                command, capture_output=True, text=True, check=False)
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("I-stage mismatch for script_sha256",
                          completed.stderr + completed.stdout)


if __name__ == "__main__":
    unittest.main()
