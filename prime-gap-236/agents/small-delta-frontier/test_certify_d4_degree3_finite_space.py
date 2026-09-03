#!/usr/bin/env python3
"""Lightweight tests for the rigorous D4 degree-three obstruction checker."""

from __future__ import annotations

import hashlib
import importlib.util
import os
import tempfile
import unittest
from fractions import Fraction as Q
from pathlib import Path


HERE = Path(__file__).resolve().parent
SOURCE = HERE / "certify_d4_degree3_finite_space.py"
SPEC = importlib.util.spec_from_file_location("d4d3_obstruction", SOURCE)
CHECKER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CHECKER)


class ObstructionTests(unittest.TestCase):
    def test_floor_and_ceil_log2(self):
        cases = (Q(1, 9), Q(1, 8), Q(3, 8), Q(1), Q(3), Q(8), Q(17))
        for value in cases:
            floor = CHECKER.floor_log2(value)
            ceil = CHECKER.ceil_log2(value)
            self.assertLessEqual(CHECKER.power2(floor), value)
            self.assertLess(value, CHECKER.power2(floor + 1))
            self.assertLessEqual(value, CHECKER.power2(ceil))

    def test_interval_operations_enclose_exact_values(self):
        scale = 1 << 96
        values = (Q(-7, 11), Q(-1, 3), Q(0), Q(2, 7), Q(13, 5))
        intervals = [CHECKER.interval_encode(value, scale)
                     for value in values]
        for value, interval in zip(values, intervals):
            self.assertTrue(CHECKER.interval_contains(interval, value, scale))
        for left, left_interval in zip(values, intervals):
            for right, right_interval in zip(values, intervals):
                product = CHECKER.interval_mul(
                    left_interval, right_interval, scale)
                self.assertTrue(CHECKER.interval_contains(
                    product, left * right, scale))
                difference = CHECKER.interval_sub(left_interval, right_interval)
                self.assertTrue(CHECKER.interval_contains(
                    difference, left - right, scale))
            square = CHECKER.interval_square(left_interval, scale)
            self.assertTrue(CHECKER.interval_contains(
                square, left * left, scale))
        positive = (Q(1, 13), Q(4, 9), Q(7, 2))
        for left in values:
            for right in positive:
                quotient = CHECKER.interval_div(
                    CHECKER.interval_encode(left, scale),
                    CHECKER.interval_encode(right, scale), scale)
                self.assertTrue(CHECKER.interval_contains(
                    quotient, left / right, scale))

    def test_small_rigorous_certificate(self):
        matrix = [
            [Q(4), Q(1), Q(1, 2), Q(0)],
            [Q(1), Q(3), Q(1, 3), Q(1, 4)],
            [Q(1, 2), Q(1, 3), Q(2), Q(1, 5)],
            [Q(0), Q(1, 4), Q(1, 5), Q(2)],
        ]
        certificate = CHECKER.certify_matrix(
            matrix, [0, 0, 1, 1], interval_bits=160, norm_bits=128)
        self.assertEqual(len(certificate["pivots"]), 4)
        self.assertTrue(all(lo > 0 for lo, _ in certificate["pivots"]))
        self.assertLess(certificate["residual"],
                        certificate["base_lower"])

    def test_indefinite_and_nonband_mutations_rejected(self):
        with self.assertRaisesRegex(ValueError, "nonpositive LDL pivot"):
            CHECKER.certify_matrix(
                [[Q(1), Q(2)], [Q(2), Q(1)]], [0, 0],
                interval_bits=128, norm_bits=96)
        nonband = [
            [Q(2), Q(0), Q(1, 10)],
            [Q(0), Q(2), Q(0)],
            [Q(1, 10), Q(0), Q(2)],
        ]
        with self.assertRaisesRegex(ValueError, "not exact block tridiagonal"):
            CHECKER.certify_matrix(
                nonband, [0, 1, 2], interval_bits=128, norm_bits=96)

    def test_wrong_hash_and_post_read_mutation_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "input"
            path.write_bytes(b"frozen\n")
            digest = hashlib.sha256(b"frozen\n").hexdigest()
            with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
                CHECKER.read_pinned(path, "0" * 64, "test", 100)
            snapshot = CHECKER.read_pinned(path, digest, "test", 100)
            path.write_bytes(b"mutated\n")
            with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
                CHECKER.verify_snapshot(snapshot, "test closure", 100)

    def test_frozen_consumer_loaded_from_snapshotted_bytes(self):
        snapshot = CHECKER.read_pinned(
            CHECKER.CONSUMER, CHECKER.CONSUMER_SHA,
            "frozen reconstruction consumer", CHECKER.MAX_SOURCE_BYTES)
        module = CHECKER.load_frozen_consumer(snapshot)
        self.assertEqual(module.MATRIX_QUERY_TAG_COUNT, 10980)
        self.assertEqual(len(module.matrix_query_tag_inventory()), 10980)
        CHECKER.verify_snapshot(
            snapshot, "frozen reconstruction consumer closure",
            CHECKER.MAX_SOURCE_BYTES)

    def test_publish_is_new_only_and_closure_precedes_link(self):
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            source = directory / "source"
            source.write_bytes(b"source\n")
            digest = hashlib.sha256(b"source\n").hexdigest()
            snapshot = CHECKER.read_pinned(source, digest, "source", 100)
            output = directory / "artifact.json"
            raw = b'{"rigorous":true}\n'
            observed = CHECKER.publish_new(
                output, raw, ((snapshot, "source closure", 100),))
            self.assertEqual(observed, hashlib.sha256(raw).hexdigest())
            self.assertEqual(output.read_bytes(), raw)
            with self.assertRaisesRegex(ValueError, "output path must be new"):
                CHECKER.publish_new(
                    output, raw, ((snapshot, "source closure", 100),))


if __name__ == "__main__":
    unittest.main(verbosity=2)
