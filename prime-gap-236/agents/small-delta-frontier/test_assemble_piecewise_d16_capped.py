#!/usr/bin/env python3

from __future__ import annotations

import importlib.util
import json
from fractions import Fraction as Q
from pathlib import Path
import sys
import unittest


HERE = Path(__file__).resolve().parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


P = load("piecewise_target_for_assembly_test",
         HERE / "piecewise_d16_capped_target.py")
A = load("piecewise_assembler_tested",
         HERE / "assemble_piecewise_d16_capped.py")


def kernel(k, labels, coefficients):
    payload = {
        "basis": [[a, list(lam)] for a, lam in labels],
        "basis_dimension": len(labels),
        "degree": max(a + sum(lam) for a, lam in labels),
        "k": k, "rational_vector": [str(Q(x)) for x in coefficients],
    }
    data = (json.dumps(payload, sort_keys=True,
                       separators=(",", ":")) + "\n").encode("ascii")
    return P.kernel_core.compile_kernel_bytes(data)


def full_i(support, fixed_kernel):
    evaluator = P.kernel_core.KernelEvaluator(support, fixed_kernel, Q)
    return evaluator.evaluate_i(False, 1)[0]


def full_j(support, fixed_kernel):
    evaluator = P.kernel_core.KernelEvaluator(support, fixed_kernel, Q)
    return evaluator.evaluate_j(False, 1)[0]


class PiecewiseAssemblyTests(unittest.TestCase):
    def test_factor_k_and_matrix_factor_two(self):
        z = Q(0)
        tables = {
            0: {
                "fh": {(0, 0): Q(2)}, "fl": {(0, 0): Q(1)},
                "hh": {(0, 0): Q(7), (0, 1): Q(3),
                       (1, 0): Q(3), (1, 1): Q(4)},
                "hl": {}, "lh": {}, "ll": {},
            },
            1: {
                "fh": {(1, 1): Q(5)}, "fl": {(1, 1): Q(2)},
                "hh": {}, "hl": {}, "lh": {}, "ll": {},
            },
        }
        M1, M2 = A.assemble_pencil(
            Q(5), Q(4), (0, 1), {0: Q(7), 1: Q(11)}, tables, 3)
        self.assertEqual(M1, [[Q(5), z, z], [z, Q(7), z], [z, z, Q(11)]])
        self.assertEqual(M2[0][1], Q(3))
        self.assertEqual(M2[0][2], Q(9))
        self.assertEqual(M2[1][2], Q(9))
        # Off diagonal appears twice only in the quadratic contraction.
        d, n, _ = A.contract(M1, M2, (Q(1), Q(2), Q(3)))
        direct_n = sum(M2[i][i] * (1, 2, 3)[i] ** 2
                       for i in range(3))
        direct_n += 2 * sum(M2[i][j] * (1, 2, 3)[i] * (1, 2, 3)[j]
                            for i in range(3) for j in range(i))
        self.assertEqual(n, direct_n)
        self.assertGreater(d, 0)

    def test_full_even_D4_count_inventory_and_all_ones(self):
        k = 3
        labels = tuple(P.ei.even_basis(4))
        inner_coeffs = tuple(Q((-1) ** i * (i + 1), i + 2)
                             for i in range(len(labels)))
        outer_coeffs = tuple(Q(2 * i + 3, i + 5)
                             for i in range(len(labels)))
        kernels = {"inner": kernel(k, labels, inner_coeffs),
                   "outer": kernel(k, labels, outer_coeffs)}
        # Delta is deliberately large enough that the r=0 all-small cube
        # reaches the radial shell; every tagged I coordinate is then live.
        delta, eta1, eta2 = Q(1, 10), Q(1, 5), Q(1, 4)
        inner_eta1 = P.ei.OneStratumSupport(
            k, Q(13, 50), delta, eta1,
            Q(13, 50), Q(13, 50), Q(13, 50))
        inner_eta2 = P.ei.OneStratumSupport(
            k, Q(13, 50), delta, eta2,
            Q(13, 50), Q(13, 50), Q(13, 50))
        schedule = (Q(1, 5), Q(3, 10), Q(2, 5))
        high = P.ScheduledSupport.make(
            k, Q(7, 20), delta, eta2, schedule)
        low = P.ScheduledSupport.make(
            k, Q(13, 50), delta, eta2, schedule)
        supports = {"inner_eta2": inner_eta2, "high": high, "low": low}
        counts = tuple(range(k + 1))
        i_by_count = {
            r: P.fused_i_shell_r(high, low, kernels["outer"], Q, r)[2]
            for r in counts
        }
        catalog = (("fh", "inner_eta2", "high"),
                   ("fl", "inner_eta2", "low"),
                   ("hh", "high", "high"),
                   ("hl", "high", "low"),
                   ("lh", "low", "high"),
                   ("ll", "low", "low"))
        tables = {}
        for r in range(k):
            row, _, _ = P.cross_bundle_r(
                supports, kernels, Q, catalog, r)
            tables[r] = row
        inner_i = full_i(inner_eta1, kernels["inner"])
        inner_b = k * full_j(inner_eta1, kernels["inner"])
        M1, M2 = A.assemble_pencil(
            inner_i, inner_b, counts, i_by_count, tables, k)
        ones = (Q(1),) * (k + 2)
        denominator, numerator, _ = A.contract(M1, M2, ones)
        self.assertEqual(denominator,
                         inner_i + full_i(high, kernels["outer"]) -
                         full_i(low, kernels["outer"]))
        expected_cross = sum((sum(row["fh"].values(), Q(0)) -
                              sum(row["fl"].values(), Q(0))
                              for row in tables.values()), Q(0))
        expected_shell = sum((sum(row["hh"].values(), Q(0)) -
                              sum(row["hl"].values(), Q(0)) -
                              sum(row["lh"].values(), Q(0)) +
                              sum(row["ll"].values(), Q(0))
                              for row in tables.values()), Q(0))
        self.assertEqual(numerator,
                         inner_b + 2 * k * expected_cross +
                         k * expected_shell)

    def test_missing_or_duplicate_inventory_rejected(self):
        complete = {0: {tag: {} for tag in
                        ("fh", "fl", "hh", "hl", "lh", "ll")}}
        with self.assertRaises(ValueError):
            A.assemble_pencil(Q(1), Q(1), (0,), {}, complete, 2)
        with self.assertRaises(ValueError):
            A.assemble_pencil(Q(1), Q(1), (0,), {0: Q(1)}, {}, 2)
        bad = {0: dict(complete[0])}
        del bad[0]["lh"]
        with self.assertRaises(ValueError):
            A.assemble_pencil(Q(1), Q(1), (0,), {0: Q(1)}, bad, 2)


if __name__ == "__main__":
    unittest.main()
