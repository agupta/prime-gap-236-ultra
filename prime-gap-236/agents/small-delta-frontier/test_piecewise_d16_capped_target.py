#!/usr/bin/env python3

from __future__ import annotations

import importlib.util
import json
from fractions import Fraction as Q
from pathlib import Path
import sys
import tempfile
import unittest


FILE = Path(__file__).resolve()
SOURCE = FILE.with_name("piecewise_d16_capped_target.py")
SPEC = importlib.util.spec_from_file_location("piecewise_d16_target", SOURCE)
M = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = M
SPEC.loader.exec_module(M)


def kernel(k, labels, coefficients):
    payload = {
        "basis": [[a, list(lam)] for a, lam in labels],
        "basis_dimension": len(labels),
        "degree": max(a + sum(lam) for a, lam in labels),
        "k": k,
        "rational_vector": [str(Q(x)) for x in coefficients],
    }
    data = (json.dumps(payload, sort_keys=True,
                       separators=(",", ":")) + "\n").encode("ascii")
    return M.kernel_core.compile_kernel_bytes(data)


def all_j(support, fixed_kernel):
    evaluator = M.kernel_core.KernelEvaluator(support, fixed_kernel, Q)
    value, _, _ = evaluator.evaluate_j(False, 1)
    return value


def all_i(support, fixed_kernel):
    evaluator = M.kernel_core.KernelEvaluator(support, fixed_kernel, Q)
    value, _, _ = evaluator.evaluate_i(False, 1)
    return value


class PiecewiseCappedTargetTests(unittest.TestCase):
    def test_exact_degree4_distinct_kernel_polarization(self):
        # Full even D4 labels: this catches differing L-powers, orbit labels,
        # and the absence of a hidden factor two in the ordered cross routine.
        labels = tuple(M.ei.even_basis(4))
        left_coeffs = tuple(Q((-1) ** i * (i + 2), i + 3)
                            for i in range(len(labels)))
        right_coeffs = tuple(Q((i % 3) - 1, i + 5)
                             for i in range(len(labels)))
        sum_coeffs = tuple(x + y for x, y in
                           zip(left_coeffs, right_coeffs))
        kernels = {"inner": kernel(3, labels, left_coeffs),
                   "outer": kernel(3, labels, right_coeffs)}
        summed = kernel(3, labels, sum_coeffs)
        support = M.ScheduledSupport.make(
            3, Q(7, 20), Q(1, 20), Q(1, 4),
            (Q(1, 5), Q(1, 4), Q(3, 10)))
        supports = {"inner_x": support, "outer_y": support}
        got = Q(0)
        transpose = Q(0)
        for r in range(3):
            tables, _, _ = M.cross_bundle_r(
                supports, kernels, Q,
                (("xy", "inner_x", "outer_y"),
                 ("yx", "outer_y", "inner_x")), r)
            got += sum(tables["xy"].values(), Q(0))
            transpose += sum(tables["yx"].values(), Q(0))
        expected = (all_j(support, summed) -
                    all_j(support, kernels["inner"]) -
                    all_j(support, kernels["outer"])) / 2
        self.assertEqual(got, expected)
        self.assertEqual(transpose, expected)

    def test_exact_degree4_shell_difference(self):
        labels = tuple(M.ei.even_basis(4))
        inner_coeffs = tuple(Q(i + 1, i + 2) for i in range(len(labels)))
        outer_coeffs = tuple(Q((-1) ** i * (2 * i + 1), i + 4)
                             for i in range(len(labels)))
        kernels = {"inner": kernel(3, labels, inner_coeffs),
                   "outer": kernel(3, labels, outer_coeffs)}
        delta, eta = Q(1, 20), Q(1, 4)
        inner = M.ei.OneStratumSupport(
            3, Q(13, 50), delta, eta,
            Q(13, 50), Q(13, 50), Q(13, 50))
        high = M.ScheduledSupport.make(
            3, Q(7, 20), delta, eta,
            (Q(1, 5), Q(1, 4), Q(3, 10)))
        low = M.ScheduledSupport.make(
            3, Q(13, 50), delta, eta,
            (Q(1, 5), Q(1, 4), Q(3, 10)))
        supports = {"inner_eta2": inner, "high": high, "low": low}
        catalog = (("fh", "inner_eta2", "high"),
                   ("hf", "high", "inner_eta2"),
                   ("fl", "inner_eta2", "low"),
                   ("lf", "low", "inner_eta2"),
                   ("hh", "high", "high"),
                   ("hl", "high", "low"),
                   ("lh", "low", "high"),
                   ("ll", "low", "low"))
        totals = {tag: Q(0) for tag, _, _ in catalog}
        for r in range(3):
            tables, _, _ = M.cross_bundle_r(
                supports, kernels, Q, catalog, r)
            for tag in totals:
                totals[tag] += sum(tables[tag].values(), Q(0))

        # Cross orientation is computed independently and must transpose
        # entry-by-entry.  Shell self is the literal high-low expansion.
        outer = kernels["outer"]
        self.assertEqual(totals["fh"], totals["hf"])
        self.assertEqual(totals["fl"], totals["lf"])
        self.assertEqual(totals["hl"], totals["lh"])
        shell_j = (totals["hh"] - totals["hl"] -
                   totals["lh"] + totals["ll"])
        self.assertEqual(shell_j,
                         all_j(high, outer) + all_j(low, outer) -
                         2 * totals["hl"])
        fused_rows = [M.fused_i_shell_r(high, low, outer, Q, r)
                      for r in range(4)]
        for r, row in enumerate(fused_rows):
            high_eval = M.kernel_core.KernelEvaluator(high, outer, Q)
            low_eval = M.kernel_core.KernelEvaluator(low, outer, Q)
            hv, hf = high_eval.evaluate_i_r(
                high_eval.square_residual_terms(), r)
            lv, lf = low_eval.evaluate_i_r(
                low_eval.square_residual_terms(), r)
            direct = (hv, lv, hv - lv, {"high": hf, "low": lf})
            self.assertEqual(row, direct)
        shell_i = sum((row[2] for row in fused_rows), Q(0))
        self.assertEqual(shell_i, all_i(high, outer) - all_i(low, outer))

    def test_piecewise_reference_recontracts(self):
        raw, A, B = M.strict_piecewise_reference()
        self.assertEqual(raw["parameters"]["inner_c"], "1")
        self.assertEqual(raw["parameters"]["outer_c"], "3090/3211")
        self.assertGreater(A[0][0], 0)
        self.assertGreater(A[1][1], 0)
        self.assertGreater(B[0][1], 0)
        self.assertGreater(
            M.parse_q(raw["rows"][1]["exact_numerator"]),
            M.parse_q(raw["rows"][1]["exact_denominator"]))

    def test_full_preflight_pins(self):
        self.assertTrue(M.require_piecewise_pins())
        M.validate_geometry_sources()

    def test_fail_closed_publication(self):
        with self.assertRaises(ValueError):
            M.write_new(M.CERT, b"must not overwrite a dependency\n")
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "stage.json"
            M.write_new(target, b"{}\n")
            self.assertEqual(target.read_bytes(), b"{}\n")
            with self.assertRaises(FileExistsError):
                M.write_new(target, b"replacement\n")


if __name__ == "__main__":
    unittest.main()
