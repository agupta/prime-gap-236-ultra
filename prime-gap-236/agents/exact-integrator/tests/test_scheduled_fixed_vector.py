#!/usr/bin/env python3
"""Exact regressions for explicit constant-extended B_m schedules."""

import hashlib
import json
import os
import sys
import unittest
from fractions import Fraction as Q
from pathlib import Path

HERE = Path(__file__).resolve().parent
AGENT = HERE.parent
sys.path[:0] = [str(AGENT), str(AGENT / "src")]

import exact_integrator as ei  # noqa: E402
from scheduled_fixed_vector import (  # noqa: E402
    ScheduledSupport,
    canonical_schedule_bytes,
    evaluate_scheduled,
    parse_schedule_payload,
)
from verify_scheduled_fixed_vector import (  # noqa: E402
    PairwiseScheduledSupport,
    pairwise_forms,
)


class ScheduledFixedVectorTests(unittest.TestCase):
    def test_schedule_schema_extension_and_identity_bind_every_entry(self):
        raw = {
            "status": "constant-extension-beta-schedule",
            "extension": "constant",
            "beta_schedule": ["3/20", "3/20", "97/625", "4/25"],
        }
        schedule = parse_schedule_payload(raw, 6)
        support = ScheduledSupport.from_schedule(
            6, Q(1, 4), Q(1, 100), Q(6, 25), schedule)
        self.assertEqual([support.beta(r) for r in range(1, 7)],
                         [Q(3, 20), Q(3, 20), Q(97, 625),
                          Q(4, 25), Q(4, 25), Q(4, 25)])
        old_hash = hashlib.sha256(canonical_schedule_bytes(schedule)).digest()
        changed = schedule[:2] + (Q(31, 200),) + schedule[3:]
        self.assertNotEqual(old_hash, hashlib.sha256(
            canonical_schedule_bytes(changed)).digest())
        for mutation in (
                {**raw, "extension": "linear"},
                {**raw, "extra": True},
                {**raw, "beta_schedule": ["6/40"]},
                {**raw, "beta_schedule": ["0"]}):
            with self.assertRaises(ValueError):
                parse_schedule_payload(mutation, 6)

    def test_nonconstant_D4_grouped_equals_pairwise_and_fork(self):
        # Deliberately nonmonotone: r=2 is impossible, but r=3,4 are feasible.
        # This catches an implementation which stops at the first failed cap.
        schedule = (Q(1, 4), Q(19, 100), Q(7, 20), Q(21, 50))
        support = ScheduledSupport.from_schedule(
            4, Q(1, 2), Q(1, 10), Q(9, 20), schedule)
        labels = ei.no_ones_basis(4)
        coefficients = [Q((-1) ** i * (i + 1), i + 2)
                        for i in range(len(labels))]
        serial = evaluate_scheduled(support, labels, coefficients, Q, workers=1)
        parallel = evaluate_scheduled(support, labels, coefficients, Q, workers=2)
        self.assertEqual(parallel, serial)

        # Independent pairwise moment recurrence: reconstruct every basis pair,
        # then contract the matrices.  It shares support geometry but not the
        # grouped face contraction used by evaluate_scheduled.
        pairwise = PairwiseScheduledSupport.from_schedule(
            4, Q(1, 2), Q(1, 10), Q(9, 20), schedule)
        expected_i, _, expected_n, pairs = pairwise_forms(
            pairwise, labels, coefficients)
        self.assertEqual(pairs, len(labels) * (len(labels) + 1) // 2)
        self.assertEqual(serial["denominator"], expected_i)
        self.assertEqual(serial["numerator"], expected_n)
        self.assertEqual(support.max_large(), 4)

    def test_nonconstant_constant_polynomial_has_direct_k2_value(self):
        # alpha=eta=1/2, delta=1/10, B1=1/4, B2=9/50.
        # The support is the two-small square plus the two one-large strips:
        # I=1/100+2*(3/20)*(1/10)=1/25.  The marginal length is 1/4
        # for u in [0,1/10] and 1/10 for u in (1/10,1/4], so
        # J=(1/10)(1/4)^2+(3/20)(1/10)^2=31/4000.
        support = ScheduledSupport.from_schedule(
            2, Q(1, 2), Q(1, 10), Q(1, 2), (Q(1, 4), Q(9, 50)))
        result = evaluate_scheduled(support, [(0, ())], [Q(1)])
        self.assertEqual(result["denominator"], Q(1, 25))
        self.assertEqual(result["j_value"], Q(31, 4000))
        self.assertEqual(result["numerator"], Q(31, 2000))
        pairwise = PairwiseScheduledSupport.from_schedule(
            2, Q(1, 2), Q(1, 10), Q(1, 2), (Q(1, 4), Q(9, 50)))
        self.assertEqual(pairwise.basis_m1((0, ()), (0, ())), Q(1, 25))
        self.assertEqual(pairwise.basis_j((0, ()), (0, ())), Q(31, 4000))

    def test_C10_D4_constant_table_matches_pinned_scalar_artifact(self):
        source_path = AGENT / "results" / "c10_fullsimplex_k48_noones_D4.json"
        expected_path = AGENT / "results" / "c10_capped_fullD4_vector_grouped_exact.json"
        raw = json.loads(source_path.read_text())
        expected = json.loads(expected_path.read_text())
        self.assertEqual(expected["input_sha256"], hashlib.sha256(
            source_path.read_bytes()).hexdigest())
        labels = [(int(a), tuple(lam)) for a, lam in raw["basis"]]
        coefficients = [Q(x) for x in raw["rational_vector"]]
        support = ScheduledSupport.from_schedule(
            48, Q(79247, 300000), Q(1, 100), Q(76247, 300000),
            (Q(3, 20), Q(3, 20), Q(97, 625)))
        result = evaluate_scheduled(support, labels, coefficients)
        self.assertEqual(str(result["denominator"]), expected["denominator"])
        self.assertEqual(str(result["j_value"]), expected["j_value"])
        self.assertEqual(str(result["numerator"]), expected["numerator"])
        for key in ("i_orbit_groups", "i_faces", "marginal_components",
                    "j_branch_integrals"):
            self.assertEqual(result[key], expected[key])


if __name__ == "__main__":
    unittest.main()
