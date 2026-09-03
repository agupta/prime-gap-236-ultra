#!/usr/bin/env python3

from __future__ import annotations

import importlib.util
import json
from fractions import Fraction as Q
from pathlib import Path
import sys
import unittest


HERE = Path(__file__).resolve().parent
SOURCE = HERE / "piecewise_d16_R15_specialized.py"
SPEC = importlib.util.spec_from_file_location("piecewise_R15_tested", SOURCE)
M = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = M
SPEC.loader.exec_module(M)
P = M.M


def kernel(k, labels, coefficients):
    payload = {"basis": [[a, list(lam)] for a, lam in labels],
               "basis_dimension": len(labels),
               "degree": max(a + sum(lam) for a, lam in labels),
               "k": k, "rational_vector": [str(Q(x)) for x in coefficients]}
    data = (json.dumps(payload, sort_keys=True,
                       separators=(",", ":")) + "\n").encode("ascii")
    return P.kernel_core.compile_kernel_bytes(data)


class R15SpecializedTests(unittest.TestCase):
    def setUp(self):
        self.k = 3
        self.labels = tuple(P.ei.even_basis(4))
        inner = tuple(Q((-1) ** i * (i + 1), i + 2)
                      for i in range(len(self.labels)))
        outer = tuple(Q(2 * i + 3, i + 5)
                      for i in range(len(self.labels)))
        self.kernels = {"inner": kernel(self.k, self.labels, inner),
                        "outer": kernel(self.k, self.labels, outer)}
        delta, eta = Q(1, 10), Q(1, 4)
        inner_support = P.ei.OneStratumSupport(
            self.k, Q(13, 50), delta, eta,
            Q(13, 50), Q(13, 50), Q(13, 50))
        schedule = (Q(1, 5), Q(3, 10), Q(2, 5))
        high = P.ScheduledSupport.make(
            self.k, Q(7, 20), delta, eta, schedule)
        low = P.ScheduledSupport.make(
            self.k, Q(13, 50), delta, eta, schedule)
        self.supports = {"inner_eta2": inner_support,
                         "high": high, "low": low}
        self.catalog = (("fh", "inner_eta2", "high"),
                        ("fl", "inner_eta2", "low"),
                        ("hh", "high", "high"),
                        ("hl", "high", "low"),
                        ("ll", "low", "low"))

    def test_branch_inventory(self):
        self.assertEqual(M.outer_branches(2, 1), ("Ltotal", "Lbig"))
        self.assertEqual(M.outer_branches(2, 2), ("Sdelta", "Stotal"))
        self.assertEqual(M.outer_branches(2, 0), ())

    def test_exact_D4_filtered_keys_equal_full_tables(self):
        target = 2
        for common_r in (1, 2):
            got, got_counts, got_faces = M.specialized_cross_r(
                self.supports, self.kernels, Q, self.catalog,
                common_r, target)
            full, _, full_faces = P.cross_bundle_r(
                self.supports, self.kernels, Q, self.catalog, common_r)
            self.assertEqual(got_faces, full_faces)
            for tag, left_name, right_name in self.catalog:
                expected = sum((value for (left, right), value in full[tag].items()
                                if ((left_name.startswith("inner") or
                                     left == target) and
                                    (right_name.startswith("inner") or
                                     right == target))), Q(0))
                self.assertEqual(got[tag], expected, (common_r, tag))
                self.assertGreaterEqual(got_counts[tag], 0)

    def test_exact_h_staging_sums_to_complete(self):
        target = 2
        for common_r in (1, 2):
            complete, _, _ = M.specialized_cross_r(
                self.supports, self.kernels, Q, self.catalog,
                common_r, target)
            max_h = int(self.supports["high"].eta /
                        self.supports["high"].delta) - common_r
            staged = {tag: Q(0) for tag, _, _ in self.catalog}
            for h in range(max_h + 1):
                row, _, faces = M.specialized_cross_r(
                    self.supports, self.kernels, Q, self.catalog,
                    common_r, target, selected_h=h)
                self.assertLessEqual(faces, 1)
                for tag in staged:
                    staged[tag] += row[tag]
            self.assertEqual(staged, complete)

    def test_source_pin_and_production_branch_mapping(self):
        self.assertEqual(M.sha256(M.TARGET_PATH), M.PINNED_TARGET_SHA256)
        self.assertEqual(M.outer_branches(15, 14),
                         ("Ltotal", "Lbig"))
        self.assertEqual(M.outer_branches(15, 15),
                         ("Sdelta", "Stotal"))


if __name__ == "__main__":
    unittest.main()
