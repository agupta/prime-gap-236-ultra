#!/usr/bin/env python3

import importlib
import json
import sys
import tempfile
import unittest
from unittest import mock
from decimal import Decimal, localcontext
from fractions import Fraction
from pathlib import Path


HERE = Path(__file__).resolve()
CODE = HERE.parents[1] / "code"
sys.path.insert(0, str(CODE))
MOD = importlib.import_module("importance_stratum_weights")
EXACT_RESULTS = HERE.parents[2] / "exact-integrator" / "results"
SOURCE = EXACT_RESULTS / "c10_stratum_linear_D4_decimal160_cut10.json"
SOURCE_SHA = "96e0655e0ace238cc561aa654d1facb8ac1e93257835f3ad174efef42d09d42e"
EXACT_ORACLE = EXACT_RESULTS / "c10_stratum_quadratic_cappedopt_D4_exact.json"
D12_SOURCE = EXACT_RESULTS / "c10_D12_affine_transfer_decimal100_cut11.json"
D12_SOURCE_SHA = "e83d3610b8130d743757a5f01aacc6ff2d2b2acd3128e5ff21b9a01cfa53d8da"


class ImportanceStratumWeightTests(unittest.TestCase):
    def test_baseline_weights_and_exact_i_agreement(self):
        weights = MOD.load_stratum_weights(
            SOURCE, SOURCE_SHA, prefix="baseline_", j_scale_to_numerator=1)
        self.assertEqual(sum(weights["i_weights"]), Decimal(1))
        self.assertEqual(sum(weights["j_weights"]), Decimal(1))
        self.assertLess(weights["relative_i_residual"],
                        weights["residual_limit"])
        self.assertLess(weights["relative_j_residual"],
                        weights["residual_limit"])
        exact_raw = json.loads(EXACT_ORACLE.read_text())
        exact_i = [Fraction(exact_raw["i_blocks"][str(r)][0][0])
                   for r in range(16)]
        exact_i_total = sum(exact_i)
        with localcontext() as context:
            context.prec = 180
            for r, observed in enumerate(weights["i_weights"]):
                exact = exact_i[r] / exact_i_total
                wanted = Decimal(exact.numerator) / Decimal(exact.denominator)
                # The Decimal160 traversal loses about 25 digits to the
                # signed polynomial contractions but still agrees with the
                # independent exact oracle far beyond the required 80.
                self.assertLess(abs(observed - wanted), Decimal("2e-135"))
            self.assertEqual(
                str(weights["base_quotient"])[:35],
                "0.896367678342782628811614262630620")

    def test_hash_schema_and_mass_mutations_fail_closed(self):
        with self.assertRaises(ValueError):
            MOD.load_stratum_weights(
                SOURCE, "0" * 64, prefix="baseline_",
                j_scale_to_numerator=1)
        with self.assertRaises((ValueError, ArithmeticError)):
            MOD.load_stratum_weights(
                SOURCE, SOURCE_SHA, prefix="baseline_",
                j_scale_to_numerator=48)
        with self.assertRaises(ValueError):
            MOD.load_stratum_weights(
                SOURCE, SOURCE_SHA, prefix="baseline_",
                j_scale_to_numerator=True)
        raw = json.loads(SOURCE.read_text())
        mutations = []
        missing = dict(raw)
        missing["baseline_i_by_r"] = missing["baseline_i_by_r"][:-1]
        mutations.append(missing)
        bad_mass = dict(raw)
        bad_mass["baseline_j_by_common_r"] = list(
            bad_mass["baseline_j_by_common_r"])
        bad_mass["baseline_j_by_common_r"][4] = str(
            Decimal(bad_mass["baseline_j_by_common_r"][4]) * 2)
        mutations.append(bad_mass)
        incomplete = dict(raw)
        incomplete["complete"] = False
        mutations.append(incomplete)
        for mutation in mutations:
            with tempfile.NamedTemporaryFile(mode="w", suffix=".json") as handle:
                json.dump(mutation, handle, sort_keys=True)
                handle.flush()
                digest = MOD.sha256_file(handle.name)
                with self.assertRaises((ValueError, ArithmeticError)):
                    MOD.load_stratum_weights(
                        handle.name, digest, prefix="baseline_",
                        j_scale_to_numerator=1)

    def test_d12_unscaled_j_convention_is_explicit(self):
        weights = MOD.load_stratum_weights(
            D12_SOURCE, D12_SOURCE_SHA, prefix="",
            j_scale_to_numerator=48)
        self.assertEqual(weights["j_scale_to_numerator"], 48)
        with localcontext() as context:
            context.prec = 150
            self.assertLess(abs(sum(weights["i_weights"]) - 1),
                            Decimal("1e-125"))
            self.assertLess(abs(sum(weights["j_weights"]) - 1),
                            Decimal("1e-125"))
        with self.assertRaises(ArithmeticError):
            MOD.load_stratum_weights(
                D12_SOURCE, D12_SOURCE_SHA, prefix="",
                j_scale_to_numerator=1)

    def test_single_read_duplicate_keys_and_decimal_precision(self):
        original_read = Path.read_bytes
        calls = []

        def counted_read(path):
            calls.append(path)
            if len(calls) > 1:
                raise AssertionError("loader reread a hash-pinned path")
            return original_read(path)

        with mock.patch.object(Path, "read_bytes", counted_read):
            MOD.load_stratum_weights(
                SOURCE, SOURCE_SHA, prefix="baseline_",
                j_scale_to_numerator=1)
        self.assertEqual(len(calls), 1)

        encoded = SOURCE.read_bytes()
        self.assertIn(b'"decimal_dps": 160', encoded)
        duplicate = encoded.replace(
            b'"decimal_dps": 160',
            b'"decimal_dps": 160, "decimal_dps": 160', 1)
        with self.assertRaises(ValueError):
            MOD._strict_json_bytes(duplicate)
        with self.assertRaises(ValueError):
            MOD._strict_json_bytes(b'{"timing":1e99999}')

        raw = json.loads(SOURCE.read_text())
        raw["baseline_i_by_r"][0] = "1E-19"
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json") as handle:
            json.dump(raw, handle)
            handle.flush()
            with self.assertRaises(ValueError):
                MOD.load_stratum_weights(
                    handle.name, MOD.sha256_file(handle.name),
                    prefix="baseline_", j_scale_to_numerator=1)

    def test_parameter_and_prefix_schema_fail(self):
        raw = json.loads(SOURCE.read_text())
        raw["parameters"]["delta"] = "11/1000"
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json") as handle:
            json.dump(raw, handle)
            handle.flush()
            with self.assertRaises(ValueError):
                MOD.load_stratum_weights(
                    handle.name, MOD.sha256_file(handle.name),
                    prefix="baseline_", j_scale_to_numerator=1)
        with self.assertRaises(ValueError):
            MOD.load_stratum_weights(
                SOURCE, SOURCE_SHA, prefix="../baseline_",
                j_scale_to_numerator=1)


if __name__ == "__main__":
    unittest.main()
