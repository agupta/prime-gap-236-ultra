#!/usr/bin/env python3

from __future__ import annotations

import importlib.util
import json
from fractions import Fraction as Q
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / (
    "agents/structural-basis/code/"
    "bv_d16_volume_ramp_capped_probe_v1.py")
SPEC = importlib.util.spec_from_file_location("capped_probe_v1", SOURCE)
M = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = M
SPEC.loader.exec_module(M)


def tiny_kernel(k=2):
    labels = ((0, ()), (1, ()), (0, (2,)))
    coefficients = (Q(2), Q(-3), Q(5))
    payload = {
        "basis": [[a, list(lam)] for a, lam in labels],
        "basis_dimension": len(labels), "degree": 2, "k": k,
        "rational_vector": [str(x) for x in coefficients],
    }
    data = (json.dumps(payload, sort_keys=True,
                       separators=(",", ":")) + "\n").encode()
    return M.kernel_core.compile_kernel_bytes(data), labels, coefficients


def tiny_kernel_with(coefficients, k=2):
    labels = ((0, ()), (1, ()), (0, (2,)))
    payload = {
        "basis": [[a, list(lam)] for a, lam in labels],
        "basis_dimension": len(labels), "degree": 2, "k": k,
        "rational_vector": [str(Q(x)) for x in coefficients],
    }
    data = (json.dumps(payload, sort_keys=True,
                       separators=(",", ":")) + "\n").encode()
    return M.kernel_core.compile_kernel_bytes(data)


class CappedVolumeProbeTests(unittest.TestCase):
    def test_dilation_matches_direct_polynomial(self):
        basis = tuple(M.ei.even_basis(6))
        vector = tuple(Q((-1) ** i * (i + 1), i + 2)
                       for i in range(len(basis)))
        c = Q(17, 18)
        transformed = M.dilate(basis, vector, c)
        points = (Q(1, 17), Q(2, 19), Q(3, 23))

        def power_sum(lam, xs):
            answer = Q(1)
            for exponent in lam:
                answer *= sum(x ** exponent for x in xs)
            return answer

        source = sum(theta * (1 - c * sum(points)) ** a *
                     power_sum(lam, tuple(c * x for x in points))
                     for theta, (a, lam) in zip(vector, basis))
        target = sum(theta * (1 - sum(points)) ** a *
                     power_sum(lam, points)
                     for theta, (a, lam) in zip(transformed, basis))
        self.assertEqual(source, target)
        self.assertEqual(M.dilate(basis, vector, Q(1)), vector)

    def test_ordered_product_has_no_hidden_two(self):
        kernel, _, _ = tiny_kernel()
        support = M.ei.OneStratumSupport(
            2, Q(6, 25), Q(1, 20), Q(1, 5),
            Q(4, 25), Q(9, 50), Q(9, 50))
        evaluator = M.kernel_core.KernelEvaluator(support, kernel, Q)
        left = {(2,): {(0, 0): Q(3)}}
        right = {(2,): {(0, 0): Q(5)}}
        got = M.ordered_orbit_product(left, right, evaluator)
        expected = {}
        for nu, multiplicity in kernel.orbit_lookup((2,), (2,)):
            expected[nu] = {(0, 0): Q(15 * multiplicity)}
        self.assertEqual(got, expected)

    def test_cross_same_support_matches_grouped_self_by_r(self):
        kernel, _, _ = tiny_kernel()
        support = M.ScheduledSupport.make(
            2, Q(6, 25), Q(1, 20), Q(1, 5),
            (Q(4, 25), Q(9, 50)))
        evaluator = M.kernel_core.KernelEvaluator(support, kernel, Q)
        data = M.component_data(evaluator)
        for r in range(2):
            direct, _ = evaluator.evaluate_j_r(*data, r)
            tables, _, _ = M.cross_bundle_r(
                {"x": support}, kernel, Q, (("xx", "x", "x"),), r)
            self.assertEqual(sum(tables["xx"].values(), Q(0)), direct)
            self.assertTrue(all(abs(i - j) <= 1
                                for i, j in tables["xx"]))

    def test_cross_transpose_symmetry_and_shell_sign(self):
        payload = {
            "basis": [[0, []]], "basis_dimension": 1,
            "degree": 0, "k": 2, "rational_vector": ["1"],
        }
        data = (json.dumps(payload, sort_keys=True,
                           separators=(",", ":")) + "\n").encode()
        kernel = M.kernel_core.compile_kernel_bytes(data)
        delta, eta = Q(1, 20), Q(1, 5)
        high = M.ScheduledSupport.make(
            2, Q(3, 10), delta, eta, (Q(1, 4), Q(3, 10)))
        low = M.ScheduledSupport.make(
            2, Q(11, 50), delta, eta, (Q(1, 4), Q(3, 10)))
        pairs = (("hl", "h", "l"), ("lh", "l", "h"),
                 ("hh", "h", "h"), ("ll", "l", "l"))
        totals = {tag: {} for tag, _, _ in pairs}
        for r in range(2):
            tables, _, _ = M.cross_bundle_r(
                {"h": high, "l": low}, kernel, Q, pairs, r)
            for tag in totals:
                for key, value in tables[tag].items():
                    totals[tag][key] = totals[tag].get(key, Q(0)) + value
        self.assertEqual(totals["hl"],
                         {(j, i): x for (i, j), x in totals["lh"].items()})
        shell = sum(totals["hh"].values(), Q(0)) + \
            sum(totals["ll"].values(), Q(0)) - \
            sum(totals["hl"].values(), Q(0)) - \
            sum(totals["lh"].values(), Q(0))
        self.assertGreater(shell, 0)

    def test_distinct_inner_outer_kernels_and_h_staging(self):
        inner_coefficients = (Q(2), Q(-3), Q(5))
        outer_coefficients = (Q(-1), Q(4), Q(2))
        inner = tiny_kernel_with(inner_coefficients)
        outer = tiny_kernel_with(outer_coefficients)
        labels = ((0, ()), (1, ()), (0, (2,)))
        support = M.ScheduledSupport.make(
            2, Q(6, 25), Q(1, 20), Q(1, 5),
            (Q(4, 25), Q(9, 50)))
        direct = sum(
            inner_coefficients[i] * outer_coefficients[j] *
            support.basis_j(labels[i], labels[j])
            for i in range(3) for j in range(3))
        total = Q(0)
        staged = Q(0)
        for r in range(2):
            tables, _, _ = M.cross_bundle_r(
                {"i": support, "o": support},
                {"i": inner, "o": outer}, Q,
                (("io", "i", "o"),), r)
            total += sum(tables["io"].values(), Q(0))
            max_h = int(support.eta // support.delta) - r
            for h in range(max_h + 1):
                piece, _, faces = M.cross_bundle_r(
                    {"i": support, "o": support},
                    {"i": inner, "o": outer}, Q,
                    (("io", "i", "o"),), r, selected_h=h)
                self.assertLessEqual(faces, 1)
                staged += sum(piece["io"].values(), Q(0))
        self.assertEqual(total, direct)
        self.assertEqual(staged, direct)

    def test_three_support_decomposition_is_not_scheduled_inner(self):
        # At count one the ramp cap is 49/625, strictly below alpha_inner.
        self.assertLess(M.SCHEDULE[0], M.ALPHA_INNER)
        self.assertNotEqual(M.SCHEDULE[0], M.ALPHA_INNER)
        self.assertEqual(tuple(range(23)), tuple(range(len(M.SCHEDULE))))

    def test_pinned_preflight(self):
        self.assertTrue(M.require_pins())
        M.validate_geometry_sources()
        base = M.load_piecewise_exact_base()
        certificate = json.loads(M.CERT.read_bytes())
        self.assertEqual(Q(base["I_matrix"][0][0]),
                         Q(certificate["exact_denominator"]))
        self.assertEqual(Q(base["kJ_matrix"][0][0]),
                         Q(certificate["exact_numerator"]))


if __name__ == "__main__":
    unittest.main()
