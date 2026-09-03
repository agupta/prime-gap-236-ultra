#!/usr/bin/env python3

from __future__ import annotations

from fractions import Fraction as Q
import importlib.util
import json
from pathlib import Path
import sys
import unittest


HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent / "code/bv_d16_r15_fused_scalar_probe.py"
SPEC = importlib.util.spec_from_file_location("bv_r15_fused_tested", SOURCE)
F = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = F
SPEC.loader.exec_module(F)
M = F.M


def kernel(k, labels, coefficients):
    payload = {
        "basis": [[a, list(lam)] for a, lam in labels],
        "basis_dimension": len(labels),
        "degree": max(a + sum(lam) for a, lam in labels),
        "k": k,
        "rational_vector": [str(Q(value)) for value in coefficients],
    }
    raw = (json.dumps(payload, sort_keys=True, separators=(",", ":")) +
           "\n").encode("ascii")
    return M.kernel_core.compile_kernel_bytes(raw)


class FusedR15Tests(unittest.TestCase):
    def setUp(self):
        self.k = 3
        self.target = 2
        labels = tuple(M.ei.even_basis(4))
        inner = tuple(Q((-1) ** i * (i + 1), i + 2)
                      for i in range(len(labels)))
        outer = tuple(Q(2 * i + 3, i + 5)
                      for i in range(len(labels)))
        self.kernels = {
            "inner": kernel(self.k, labels, inner),
            "outer": kernel(self.k, labels, outer),
        }
        delta, eta = Q(1, 10), Q(1, 4)
        inner_support = M.ei.OneStratumSupport(
            self.k, Q(33, 100), delta, eta,
            Q(33, 100), Q(33, 100), Q(33, 100))
        schedule = (Q(1, 5), Q(3, 10), Q(2, 5))
        high = M.ScheduledSupport.make(
            self.k, Q(7, 20), delta, eta, schedule)
        low = M.ScheduledSupport.make(
            self.k, Q(33, 100), delta, eta, schedule)
        self.supports = {
            "inner_eta2": inner_support,
            "high": high,
            "low": low,
        }

    def literal_expansion(self, common_r):
        catalog = (
            ("fh", "inner_eta2", "high"),
            ("fl", "inner_eta2", "low"),
            ("hh", "high", "high"),
            ("hl", "high", "low"),
            ("lh", "low", "high"),
            ("ll", "low", "low"),
        )
        tables, _, _ = M.cross_bundle_r(
            self.supports, self.kernels, Q, catalog, common_r)

        def total(tag, left_inner=False, right_inner=False):
            return sum((value for (left, right), value in tables[tag].items()
                        if ((left_inner or left == self.target) and
                            (right_inner or right == self.target))), Q(0))

        return {
            "fx": total("fh", True, False) - total("fl", True, False),
            "xx": (total("hh") - total("hl") - total("lh") +
                   total("ll")),
        }

    def test_exact_literal_expansion_both_common_rows(self):
        for common_r in (self.target - 1, self.target):
            got, diagnostics = F.fused_face(
                self.supports, self.kernels, Q, common_r, self.target,
                selected_h=None)
            self.assertEqual(got, self.literal_expansion(common_r))
            self.assertGreater(diagnostics["domain_integrals"], 0)
            self.assertLessEqual(diagnostics["unique_block_products"],
                                 diagnostics["naive_density_lifts"])

    def test_exact_face_staging(self):
        for common_r in (self.target - 1, self.target):
            complete, _ = F.fused_face(
                self.supports, self.kernels, Q, common_r, self.target,
                selected_h=None)
            max_h = int(self.supports["high"].eta /
                        self.supports["high"].delta) - common_r
            staged = {"fx": Q(0), "xx": Q(0)}
            for h in range(max_h + 1):
                row, diagnostics = F.fused_face(
                    self.supports, self.kernels, Q, common_r, self.target,
                    selected_h=h)
                for name in staged:
                    staged[name] += row[name]
                self.assertLessEqual(diagnostics["faces"], 1)
            self.assertEqual(staged, complete)

    def test_high_low_fixed_bound_piece_is_interned(self):
        # At common r=target the Sdelta marginal polynomial is independent of
        # alpha.  Its high/low domain indicators differ, but the exact block
        # identity must be recognized before orbit multiplication.
        evaluators = M.evaluators_for_cross(self.supports, self.kernels, Q)
        data = {name: M.component_data(evaluator)
                for name, evaluator in evaluators.items()}
        r, h = self.target, 0
        dimension = self.k - 1
        outer = self.supports["high"].eta - r * self.supports["high"].delta
        high = F.selected_branch_blocks(
            evaluators["high"], data["high"], ("Sdelta",), r, h,
            dimension, outer)["Sdelta"][0]
        low = F.selected_branch_blocks(
            evaluators["low"], data["low"], ("Sdelta",), r, h,
            dimension, outer)["Sdelta"][0]
        self.assertTrue(high)
        self.assertEqual(F.block_signature(high), F.block_signature(low))

    def test_constraint_canonicalization(self):
        constraints = ((Q(1), Q(0), Q(3, 5)),
                       (Q(2), Q(0), Q(6, 5)),
                       (Q(1), Q(0), Q(1, 2)),
                       (Q(-2), Q(0), Q(-1)))
        self.assertEqual(
            F.canonical_constraints(constraints),
            ((Q(-1), Q(0), Q(-1, 2)), (Q(1), Q(0), Q(1, 2))))

    def test_source_pin_and_production_branch_rows(self):
        self.assertEqual(F.sha256(F.TARGET), F.PINNED_TARGET_SHA256)
        self.assertEqual(F.outer_branches(15, 14), ("Ltotal", "Lbig"))
        self.assertEqual(F.outer_branches(15, 15), ("Sdelta", "Stotal"))
        self.assertEqual(F.outer_branches(15, 13), ())


if __name__ == "__main__":
    unittest.main()
