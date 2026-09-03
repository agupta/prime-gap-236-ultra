#!/usr/bin/env python3

import importlib.util
from fractions import Fraction as Q
from pathlib import Path
import sys
import unittest


HERE = Path(__file__).resolve()
SOURCE = (HERE.parents[1] / "code" /
          "verify_bv_dilation_fullsimplex_proxy_v2.py")
SPEC = importlib.util.spec_from_file_location("bv_dilation_auditor_tested", SOURCE)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load dilation auditor")
M = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = M
SPEC.loader.exec_module(M)


class VerifyBvDilationFullSimplexProxyTests(unittest.TestCase):
    def test_full_direct_target_reconstruction_passes(self):
        result = M.audit()
        self.assertEqual(result["status"], "AUDIT PASS")
        self.assertFalse(result["analytic_support_approved"])
        self.assertFalse(result["theorem_ready"])
        self.assertGreater(Q(result["direct_target_quotient"]), 1)
        self.assertGreater(Q(result["direct_target_margin"]), 0)
        self.assertEqual(result["direct_basis_square_term_count"], 5825)
        self.assertEqual(result["direct_marginal_square_term_count"], 5825)

    def test_one_ulp_like_coefficient_mutation_changes_direct_forms(self):
        basis = M.exact.even_basis(4)
        vector = [Q((i % 5) - 2, i + 3) for i in range(len(basis))]
        transformed = M.independent_transform(basis, vector)
        denominator, numerator, _, _ = M.direct_target_forms(
            basis, transformed)
        mutation = list(transformed)
        mutation[0] += Q(1, 10 ** 80)
        changed_denominator, changed_numerator, _, _ = M.direct_target_forms(
            basis, mutation)
        self.assertNotEqual(changed_denominator, denominator)
        self.assertNotEqual(changed_numerator, numerator)

    def test_wrong_dependency_hash_rejects(self):
        relative = next(iter(M.PINNED))
        expected = M.PINNED[relative]
        M.PINNED[relative] = "f" * 64
        try:
            with self.assertRaises(ValueError):
                M.validate_closure()
        finally:
            M.PINNED[relative] = expected


if __name__ == "__main__":
    unittest.main()
