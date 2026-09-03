#!/usr/bin/env python3
"""Lightweight, fail-closed audit of the fixed no-ones D12 input.

This test never evaluates a support integral.  In particular, the grouped CLI
test replaces orbit precomputation and both quadratic evaluations with capture
stubs; it exercises only the real JSON-loading and rational-parsing path.
"""

from __future__ import annotations

import hashlib
import io
import json
import sqlite3
import sys
import unittest
from contextlib import redirect_stdout
from decimal import Decimal
from fractions import Fraction as Q
from pathlib import Path
from unittest import mock


HERE = Path(__file__).resolve().parent
STRUCTURAL = HERE.parent
AGENTS = STRUCTURAL.parent
EXACT = AGENTS / "exact-integrator"
SOURCE = EXACT / "results" / "hb_c10_fullsimplex_noones_D12.json"
BANDS = STRUCTURAL / "results" / "c10_D12_degree_bands.json"
INTEGRATOR = EXACT / "src" / "exact_integrator.py"

SOURCE_SHA256 = "719c656e6e45388273b4c27f51f7a18b33e9ed1abb5f883e6fcc5de5d6d64a87"
BANDS_SHA256 = "29d38a9e7ca7a352560c0a01813f2dfd2f477ec8cb829c433cce18d8229d31e9"
INTEGRATOR_SHA256 = "941ee82bc72fd8488a95eb5e536fe47f8c95d39a1b618dae7d6ef7eb27122e52"
MATRIX_SHA256 = "b882098bd6889ff251195b45153a2204e4df1c4ef843a2ae85dcc1b2fd3e041d"

SOURCE_KEYS = {
    "basis", "basis_dimension", "cache_hits", "cache_misses",
    "decimal_generalized_eigenvalue", "decimal_vector", "degree",
    "exact_denominator_positive", "exact_margin", "exact_margin_positive",
    "exact_matrices_sha256", "exact_matrix_seconds",
    "exact_quadratic_denominator", "exact_quadratic_numerator",
    "exact_quotient", "exact_quotient_decimal",
    "floating_generalized_eigenvalue", "integrator_sha256", "k",
    "parameters", "rational_vector", "rigorous",
}
BAND_KEYS = {
    "bands", "basis_convention", "compressed_basis_dimension", "core",
    "core_degree", "expanded_term_count", "identity", "source_json",
    "source_sha256", "status", "total_degree",
}
PARAMETERS = {
    "alpha": "79247/300000",
    "delta": "1/100",
    "eta": "76247/300000",
    "beta1": "79247/300000",
    "beta2": "79247/300000",
    "beta3plus": "79247/300000",
}
CAPPED_PARAMETERS = {
    "alpha": "79247/300000",
    "delta": "1/100",
    "eta": "76247/300000",
    "beta1": "3/20",
    "beta2": "3/20",
    "beta3plus": "97/625",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def normalize_label(raw, where: str):
    if not (isinstance(raw, list) and len(raw) == 2 and
            type(raw[0]) is int and isinstance(raw[1], list)):
        raise AssertionError(f"malformed label in {where}: {raw!r}")
    a, raw_partition = raw
    if a < 0 or any(type(part) is not int or part < 2
                    for part in raw_partition):
        raise AssertionError(f"not a no-ones label in {where}: {raw!r}")
    partition = tuple(raw_partition)
    if any(partition[index] < partition[index + 1]
           for index in range(len(partition) - 1)):
        raise AssertionError(f"partition is not weakly decreasing in {where}: {raw!r}")
    return a, partition


def complete_no_ones_basis(max_degree: int):
    """Enumerate all (a, lambda) with parts(lambda)>=2 and total degree <= D."""
    partitions = set()

    def visit(remaining, maximum, prefix):
        partitions.add(tuple(prefix))
        for part in range(min(remaining, maximum), 1, -1):
            visit(remaining - part, part, prefix + [part])

    visit(max_degree, max_degree, [])
    return {(a, partition)
            for partition in partitions
            for a in range(max_degree - sum(partition) + 1)}


class D12InputAudit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source_bytes = SOURCE.read_bytes()
        cls.source = json.loads(cls.source_bytes)
        cls.band_bytes = BANDS.read_bytes()
        cls.band = json.loads(cls.band_bytes)

    def source_terms(self):
        labels = [normalize_label(raw, f"source basis[{index}]")
                  for index, raw in enumerate(self.source["basis"])]
        coefficients = [Q(raw) for raw in self.source["rational_vector"]]
        return labels, coefficients

    def test_source_schema_labels_and_exact_nonzero_vector(self):
        record = self.source
        self.assertEqual(set(record), SOURCE_KEYS)
        self.assertIs(type(record["k"]), int)
        self.assertIs(type(record["degree"]), int)
        self.assertIs(type(record["basis_dimension"]), int)
        self.assertEqual((record["k"], record["degree"]), (48, 12))
        self.assertEqual(record["basis_dimension"], 272)
        self.assertIs(record["rigorous"], True)
        self.assertIs(record["exact_denominator_positive"], True)
        self.assertIs(record["exact_margin_positive"], True)
        self.assertEqual(record["parameters"], PARAMETERS)
        self.assertTrue(all(isinstance(value, str)
                            for value in record["parameters"].values()))

        for field in ("cache_hits", "cache_misses"):
            self.assertIs(type(record[field]), int)
            self.assertGreaterEqual(record[field], 0)
        self.assertIsInstance(record["exact_matrix_seconds"], (int, float))
        self.assertGreaterEqual(record["exact_matrix_seconds"], 0)
        for field in ("floating_generalized_eigenvalue",
                      "exact_quotient_decimal"):
            self.assertIsInstance(record[field], (int, float))
        for field in ("decimal_generalized_eigenvalue", "exact_margin",
                      "exact_quadratic_denominator",
                      "exact_quadratic_numerator", "exact_quotient"):
            self.assertIsInstance(record[field], str)
        Decimal(record["decimal_generalized_eigenvalue"])

        for field in ("basis", "rational_vector", "decimal_vector"):
            self.assertIsInstance(record[field], list)
            self.assertEqual(len(record[field]), 272)
        self.assertTrue(all(isinstance(value, str)
                            for value in record["rational_vector"]))
        self.assertTrue(all(isinstance(value, str)
                            for value in record["decimal_vector"]))
        for value in record["decimal_vector"]:
            Decimal(value)

        labels, coefficients = self.source_terms()
        self.assertEqual(len(labels), len(set(labels)), "duplicate source label")
        self.assertTrue(all(a + sum(partition) <= 12
                            for a, partition in labels))
        expected = complete_no_ones_basis(12)
        self.assertEqual(len(expected), 272)
        self.assertEqual(set(labels), expected)
        self.assertEqual(sum(value != 0 for value in coefficients), 272)

    def test_source_and_integrator_hashes(self):
        self.assertEqual(hashlib.sha256(self.source_bytes).hexdigest(),
                         SOURCE_SHA256)
        self.assertEqual(self.source["integrator_sha256"], INTEGRATOR_SHA256)
        self.assertEqual(sha256(INTEGRATOR), INTEGRATOR_SHA256)
        # The matrix digest is pinned as provenance.  There are no serialized
        # matrices in this artifact from which this test could reproduce it.
        self.assertEqual(self.source["exact_matrices_sha256"], MATRIX_SHA256)
        serialized_matrix_keys = {
            "m1", "m2", "M1", "M2", "matrices", "exact_matrices",
        }
        self.assertFalse(serialized_matrix_keys.intersection(self.source))

    def test_serialized_cache_matrix_replay_if_complete(self):
        """Use cached rationals only; never fill a missing matrix entry.

        The checked-in cache is currently incomplete for D12, so the concrete
        audit result is documented in D12-INPUT-AUDIT.md.  This conditional
        branch makes the regression durable: if all entries later exist, it
        replays both quadratic forms and the canonical matrix hash without
        calling any integrator routine.
        """
        labels, vector = self.source_terms()
        parameters = [self.source["k"]]
        parameters.extend(self.source["parameters"][name] for name in (
            "alpha", "delta", "eta", "beta1", "beta2", "beta3plus"))
        expected = {}
        for i, left in enumerate(labels):
            for j in range(i + 1):
                key = json.dumps([1, parameters, left, labels[j]],
                                 separators=(",", ":"))
                expected[key] = (i, j)

        # A cache key starts with the version and complete support tuple.  The
        # LIKE filter is read-only and avoids loading unrelated large entries.
        prefix = json.dumps([1, parameters], separators=(",", ":"))[:-1] + ","
        cached = {}
        cache_dir = EXACT / "cache"
        for path in sorted(cache_dir.glob("*.sqlite3")):
            connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
            try:
                has_entries = connection.execute(
                    "select 1 from sqlite_master "
                    "where type='table' and name='entries'").fetchone()
                if not has_entries:
                    continue
                rows = connection.execute(
                    "select cache_key,m1,m2 from entries where cache_key like ?",
                    (prefix + "%",))
                for key, raw_m1, raw_m2 in rows:
                    position = expected.get(key)
                    if position is None:
                        continue
                    value = (Q(raw_m1), Q(raw_m2))
                    if position in cached:
                        self.assertEqual(cached[position], value,
                                         f"conflicting cache row {position}")
                    cached[position] = value
            finally:
                connection.close()

        required = len(labels) * (len(labels) + 1) // 2
        self.assertLessEqual(len(cached), required)
        if len(cached) != required:
            # Absence is not repaired here: doing so would launch the moment
            # calculation this audit was designed to avoid.
            self.assertTrue(any((i, j) not in cached
                                for i in range(len(labels))
                                for j in range(i + 1)))
            return

        digest = hashlib.sha256()
        for matrix_index, name in enumerate(("M1", "M2")):
            digest.update((name + "\n").encode())
            for i in range(len(labels)):
                row = [cached[(max(i, j), min(i, j))][matrix_index]
                       for j in range(len(labels))]
                digest.update(("\t".join(str(value) for value in row) + "\n").encode())
        self.assertEqual(digest.hexdigest(), MATRIX_SHA256)

        forms = [Q(0), Q(0)]
        for i in range(len(labels)):
            for j in range(i + 1):
                symmetry = 1 if i == j else 2
                for matrix_index in range(2):
                    forms[matrix_index] += (
                        symmetry * vector[i] * cached[(i, j)][matrix_index] *
                        vector[j])
        self.assertEqual(forms[0], Q(self.source["exact_quadratic_denominator"]))
        self.assertEqual(forms[1], Q(self.source["exact_quadratic_numerator"]))
        self.assertEqual(forms[1] - forms[0], Q(self.source["exact_margin"]))

    def test_stored_quadratic_arithmetic_only(self):
        """Check stored scalars, without claiming a matrix regression."""
        denominator = Q(self.source["exact_quadratic_denominator"])
        numerator = Q(self.source["exact_quadratic_numerator"])
        margin = Q(self.source["exact_margin"])
        quotient = Q(self.source["exact_quotient"])
        self.assertGreater(denominator, 0)
        self.assertGreater(margin, 0)
        self.assertEqual(numerator - denominator, margin)
        self.assertEqual(numerator / denominator, quotient)

    def test_degree_band_schema_hash_and_coefficientwise_identity(self):
        artifact = self.band
        self.assertEqual(set(artifact), BAND_KEYS)
        self.assertIsInstance(artifact["core"], list)
        self.assertIsInstance(artifact["bands"], dict)
        for field in ("core_degree", "expanded_term_count",
                      "compressed_basis_dimension"):
            self.assertIs(type(artifact[field]), int)
        for field in ("basis_convention", "identity", "source_json",
                      "source_sha256", "status", "total_degree"):
            self.assertIsInstance(artifact[field], str)
        self.assertEqual(hashlib.sha256(self.band_bytes).hexdigest(),
                         BANDS_SHA256)
        self.assertEqual(artifact["source_sha256"], SOURCE_SHA256)
        self.assertEqual(hashlib.sha256(self.source_bytes).hexdigest(),
                         artifact["source_sha256"])
        self.assertEqual(
            artifact["source_json"],
            "prime-gap-236/agents/exact-integrator/results/"
            "hb_c10_fullsimplex_noones_D12.json")
        self.assertEqual(artifact["status"],
                         "exact-rational-degree-band-decomposition")
        self.assertEqual(artifact["core_degree"], 4)
        self.assertEqual(artifact["expanded_term_count"], 272)
        self.assertEqual(artifact["compressed_basis_dimension"], 20)
        self.assertEqual(set(artifact["bands"]),
                         {str(degree) for degree in range(5, 13)})

        labels, coefficients = self.source_terms()
        original = dict(zip(labels, coefficients))
        reconstructed = {}

        def add_entries(entries, where, expected_degree):
            self.assertIsInstance(entries, list)
            self.assertGreater(len(entries), 0)
            for index, entry in enumerate(entries):
                self.assertIsInstance(entry, dict)
                self.assertEqual(set(entry), {"label", "coefficient"})
                label = normalize_label(entry["label"], f"{where}[{index}]")
                degree = label[0] + sum(label[1])
                if where == "core":
                    self.assertLessEqual(degree, expected_degree)
                else:
                    self.assertEqual(degree, expected_degree)
                self.assertNotIn(label, reconstructed,
                                 f"duplicate reconstructed label {label}")
                self.assertIsInstance(entry["coefficient"], str)
                reconstructed[label] = Q(entry["coefficient"])

        add_entries(artifact["core"], "core", 4)
        self.assertEqual(len(artifact["core"]), 12)
        for raw_degree, entries in artifact["bands"].items():
            add_entries(entries, f"band {raw_degree}", int(raw_degree))
        self.assertEqual(reconstructed, original)

    def test_grouped_capped_cli_dry_loads_identical_labels_and_vector(self):
        """Exercise the production loader while stubbing every integration."""
        sys.path[:0] = [str(EXACT), str(EXACT / "src")]
        import grouped_fixed_vector as grouped  # noqa: E402

        expected_labels, expected_coefficients = self.source_terms()
        captured = {}

        def capture_precompute(labels, k):
            captured["precompute_labels"] = tuple(labels)
            captured["precompute_k"] = k
            return {}

        class CaptureEvaluator:
            def __init__(self, support, labels, coefficients, scalar):
                captured["support"] = support
                captured["labels"] = tuple(labels)
                captured["coefficients"] = tuple(coefficients)
                captured["scalar"] = scalar

            def evaluate_i(self, progress=False, workers=1):
                return Q(1), 0, 0

            def evaluate_j(self, progress=False, workers=1):
                return Q(1, 48), 0, 0

        argv = [str(EXACT / "grouped_fixed_vector.py"), str(SOURCE)]
        for name, value in CAPPED_PARAMETERS.items():
            argv.extend((f"--{name}", value))
        with (mock.patch.object(sys, "argv", argv),
              mock.patch.object(grouped, "precompute_orbits",
                                side_effect=capture_precompute),
              mock.patch.object(grouped, "GroupedEvaluator", CaptureEvaluator),
              redirect_stdout(io.StringIO())):
            grouped.main()

        expected_labels = tuple(expected_labels)
        expected_coefficients = tuple(expected_coefficients)
        self.assertEqual(captured["precompute_k"], 48)
        self.assertEqual(captured["precompute_labels"], expected_labels)
        self.assertEqual(captured["labels"], expected_labels)
        self.assertEqual(captured["coefficients"], expected_coefficients)
        self.assertIs(captured["scalar"], Q)
        support = captured["support"]
        self.assertEqual(support.k, 48)
        for name, raw_value in CAPPED_PARAMETERS.items():
            self.assertEqual(getattr(support, name), Q(raw_value))


if __name__ == "__main__":
    unittest.main()
