#!/usr/bin/env python3
"""Lightweight schema/algebra tests; never read a degree-three result."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import tempfile
import unittest
from decimal import Decimal
from fractions import Fraction as Q
from pathlib import Path


HERE = Path(__file__).resolve().parent
SCRIPT = HERE / "consume_stratum_moment_d4_degree3.py"


def load_module():
    spec = importlib.util.spec_from_file_location("d4d3_consumer", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class DegreeThreeConsumerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = load_module()
        cls.producer_gate, _ = cls.mod.load_producer_gate()

    def test_pinned_gate_and_degree2_reference_schema(self):
        consumer_gate, consumer_snapshot = self.mod.load_consumer_gate()
        authorization, authorization_snapshot = self.mod.load_authorization()
        reference, reference_snapshot = self.mod.load_reference()
        self.assertEqual(consumer_snapshot.digest,
                         self.mod.CONSUMER_GATE_SHA)
        self.assertEqual(reference_snapshot.digest, self.mod.REFERENCE_SHA)
        self.assertEqual(authorization_snapshot.digest,
                         self.mod.AUTHORIZATION_SHA)
        self.assertTrue(authorization["authorized"])
        self.assertEqual(consumer_gate["authorization_sha256"],
                         self.mod.AUTHORIZATION_SHA)
        self.assertFalse(consumer_gate["production_launch_authorized"])
        inventory = self.mod.matrix_query_tag_inventory()
        self.assertEqual(len(inventory), self.mod.MATRIX_QUERY_TAG_COUNT)
        self.assertEqual(self.mod.tag_inventory_sha(inventory),
                         self.mod.MATRIX_QUERY_TAG_SHA)
        self.assertEqual({tag[1:3] for tag in inventory if tag[0] == 15},
                         {(0, 0)})
        selected, discarded, _ = self.mod.gram_independent_coordinates(
            reference["a"], reference["b"], reference["labels"],
            self.mod.CHANNELS2,
            expected_discarded=((0, (1, 0)), (0, (2, 0)),
                                (0, (1, 1))), expected_rank=93)
        self.assertEqual(len(selected), 93)
        self.assertEqual(discarded, [1, 3, 4])

    def test_synthetic_canonical_rows_reconstruct_entries(self):
        degree = 1
        i_rows = []
        for r, u, v in sorted((0, u, v) for u in range(3)
                              for v in range(3 - u)):
            i_rows.append([r, u, v, str(Q(10 + 2 * u + 3 * v))])
        i_table = self.mod.parse_i_rows(i_rows, degree=degree, strata=1)
        entries = {
            (0, 0, 0, 0, 0, 0, 0): Q(2),
            (0, 0, 0, 0, 0, 0, 1): Q(3),
            (0, 0, 0, 0, 0, 1, 0): Q(5),
            (0, 0, 0, 0, 1, 0, 0): Q(7),
            (0, 0, 0, 1, 0, 0, 0): Q(7),
            (0, 0, 0, 1, 1, 0, 0): Q(11),
        }
        j_rows = [list(key) + [str(entries[key])]
                  for key in sorted(entries)]
        j_table = self.mod.parse_j_rows(j_rows, degree=degree, strata=1)
        labels, a, b = self.mod.reconstruct_matrices(
            i_table, j_table, degree=degree, strata=1, k_factor=48)
        self.assertEqual(labels, [(0, 0), (0, 1), (0, 2)])
        self.assertEqual(a[1][2], Q(15))
        self.assertEqual(b[0][0], Q(96))
        self.assertEqual(b[1][0], Q(240))
        self.assertEqual(b[2][0], Q(480))
        self.assertEqual(b[2][2], Q(528))
        encoded = json.dumps([[str(x) for x in row] for row in a],
                             separators=(",", ":")).encode()
        self.assertEqual(self.mod.matrix_sha(a),
                         hashlib.sha256(encoded).hexdigest())

        with self.assertRaisesRegex(ValueError, "canonical order"):
            self.mod.parse_i_rows(list(reversed(i_rows)), degree=degree,
                                  strata=1)
        malformed = copy.deepcopy(i_rows)
        malformed[0][-1] = "2/2"
        with self.assertRaisesRegex(ValueError, "not reduced"):
            self.mod.parse_i_rows(malformed, degree=degree, strata=1)

    def test_j_inventory_rejects_unused_r15_and_malformed_coordinates(self):
        self.assertEqual(
            self.mod.parse_j_rows([], degree=1, strata=1), {})
        rows = [[r, 0, 0, 0, 0, 0, 0, "1"]
                for r in range(self.mod.STRATA)]
        rows.extend([
            [15, 0, 1, 0, 0, 0, 0, "1"],
            [15, 1, 0, 0, 0, 0, 0, "1"],
        ])
        rows.sort(key=lambda row: tuple(row[:7]))
        with self.assertRaisesRegex(ValueError, "matrix-query tag inventory"):
            self.mod.parse_j_rows(rows)

        with self.assertRaisesRegex(ValueError, "tag range"):
            self.mod.parse_j_rows(
                [[0, 0, 0, 0, 0, -1, 0, "1"]], degree=1, strata=1)
        with self.assertRaisesRegex(ValueError, "shape/types"):
            self.mod.parse_j_rows(
                [[0, 0, 0, 0, 0, "0", 0, "1"]], degree=1, strata=1)

    def test_exact_gram_selection_checks_A_and_B_dependence(self):
        a = [[Q(1), Q(2), Q(3)],
             [Q(2), Q(4), Q(6)],
             [Q(3), Q(6), Q(10)]]
        b = [[Q(2), Q(4), Q(5)],
             [Q(4), Q(8), Q(10)],
             [Q(5), Q(10), Q(7)]]
        labels = [(0, 0), (0, 1), (0, 2)]
        powers = ((0, 0), (1, 0), (0, 1))
        selected, discarded, pivots = \
            self.mod.gram_independent_coordinates(
                a, b, labels, powers,
                expected_discarded=((0, (1, 0)),), expected_rank=2)
        self.assertEqual(selected, [0, 2])
        self.assertEqual(discarded, [1])
        self.assertEqual(pivots, [Q(1), Q(1)])

        incompatible = [list(row) for row in b]
        incompatible[1][2] = incompatible[2][1] = Q(11)
        with self.assertRaisesRegex(ValueError, "B-column dependence"):
            self.mod.gram_independent_coordinates(
                a, incompatible, labels, powers)

    def test_two_precision_gate_and_conditional_rationalization(self):
        a = [[Q(1), Q(0)], [Q(0), Q(1)]]
        b = [[Q(1, 2), Q(0)], [Q(0), Q(3, 2)]]
        solves = [self.mod.solve_once(a, b, precision)
                  for precision in self.mod.PRECISIONS]
        rationalized, disagreement = self.mod.rationalize_if_improved(
            solves, [0, 1], 2, a, b)
        self.assertEqual(disagreement, Decimal(0))
        self.assertIsNotNone(rationalized)
        self.assertEqual(Q(rationalized["quotient"]), Q(3, 2))
        self.assertTrue(rationalized["exact_continuation_gate"])

        below = [[Q(1, 2), Q(0)], [Q(0), Q(3, 4)]]
        below_solves = [self.mod.solve_once(a, below, precision)
                        for precision in self.mod.PRECISIONS]
        skipped, _ = self.mod.rationalize_if_improved(
            below_solves, [0, 1], 2, a, below)
        self.assertIsNone(skipped)

    def test_strict_result_metadata_and_json_rejections(self):
        value = {
            "status": "exact-c10-d4-degree3-moment-pass",
            "rigorous_forms": True,
            "theorem_ready": False,
            "scope": "D4 degree-three finite space only; no D12 sign",
            "gate_sha256": self.mod.PRODUCER_GATE_SHA,
            "authorization_sha256": self.mod.AUTHORIZATION_SHA,
            "driver_sha256": self.mod.PRODUCER_SHA,
            "input_sha256": self.mod.INPUT_SHA,
            "reference_sha256": self.mod.REFERENCE_SHA,
            "tag_schema_sha256": self.mod.TAG_SCHEMA_SHA,
            "expected_counts": self.mod.EXPECTED_COUNTS,
            "all_fused_unfused_entries_equal": True,
            "all_degree2_oracle_entries_equal": True,
            "particular_denominator": "2",
            "particular_numerator": "3",
            "particular_quotient": "3/2",
            "a_matrix_sha256": "b" * 64,
            "b48_matrix_sha256": "c" * 64,
            "i_moment_rows": [],
            "j_moment_rows": [],
            "fused_seconds": Decimal("1000.0"),
            "unfused_seconds": Decimal("1100.0"),
            "total_validation_seconds": Decimal("2100.0"),
            "peak_rss_kib": 100000,
            "resource_gate_passed": True,
        }
        self.mod.validate_result_metadata(value, self.producer_gate)
        extra = dict(value, unexpected=True)
        with self.assertRaisesRegex(ValueError, "schema mismatch"):
            self.mod.validate_result_metadata(extra, self.producer_gate)
        late = dict(value, fused_seconds=Decimal("1800.0001"))
        with self.assertRaisesRegex(ValueError, "resource gate"):
            self.mod.validate_result_metadata(late, self.producer_gate)
        inconsistent = dict(value, total_validation_seconds=Decimal("2200.0"))
        with self.assertRaisesRegex(ValueError, "timing sum"):
            self.mod.validate_result_metadata(inconsistent, self.producer_gate)
        wrong_authorization = dict(value, authorization_sha256="a" * 64)
        with self.assertRaisesRegex(ValueError, "status/provenance"):
            self.mod.validate_result_metadata(
                wrong_authorization, self.producer_gate)
        with self.assertRaisesRegex(ValueError, "duplicate"):
            self.mod.strict_json(b'{"x":1,"x":2}', "duplicate test")
        with self.assertRaisesRegex(ValueError, "nonfinite"):
            self.mod.strict_json(b'{"x":NaN}', "nonfinite test")

    def test_caller_pinned_self_wrong_hash_and_post_read_mutation(self):
        with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
            self.mod.read_pinned(
                SCRIPT, "0" * 64, "consumer self wrong hash", 5_000_000)
        with tempfile.TemporaryDirectory() as directory:
            missing_result = Path(directory) / "must-not-be-opened.json"
            with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
                self.mod.consume(
                    missing_result, "1" * 64, "0" * 64)
        raw = SCRIPT.read_bytes()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "consumer.py"
            path.write_bytes(raw)
            snapshot = self.mod.read_pinned(
                path, hashlib.sha256(raw).hexdigest(),
                "consumer self snapshot", 5_000_000)
            mutated = bytes([raw[0] ^ 1]) + raw[1:]
            path.write_bytes(mutated)
            with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
                self.mod.verify_snapshot(
                    snapshot, "consumer self final closure", 5_000_000)


if __name__ == "__main__":
    unittest.main()
