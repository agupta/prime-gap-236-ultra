#!/usr/bin/env python3

import hashlib
import importlib.util
import copy
import json
import tempfile
import unittest
from fractions import Fraction
from pathlib import Path


HERE = Path(__file__).resolve()
MODULE_PATH = HERE.parents[1] / "code" / "importance_oracle.py"
SPEC = importlib.util.spec_from_file_location("importance_oracle", MODULE_PATH)
MOD = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MOD)
ORACLE_PATH = HERE.parents[2] / "exact-integrator" / "results" / \
    "c10_stratum_quadratic_cappedopt_D4_exact.json"


class ImportanceOracleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = json.loads(ORACLE_PATH.read_text())
        cls.oracle = MOD.load_exact_expectation_oracle(ORACLE_PATH)

    def test_pinned_source_and_base_quotient(self):
        self.assertEqual(
            hashlib.sha256(ORACLE_PATH.read_bytes()).hexdigest(),
            "fbc8c38d2cf4241fdba03beb4251e2692e96af01ad4918c9a3a1075af2ed6e86")
        self.assertEqual(self.oracle["dimension"], 96)
        self.assertEqual(self.oracle["base_quotient"],
                         self.oracle["B0"] / self.oracle["I0"])
        # The published result's rational vector is unrelated to the base
        # quotient; reconstruct the independently recorded fixed-base value.
        expected_prefix = "0.8963676783427826"
        decimal = format(float(self.oracle["base_quotient"]), ".16f")
        self.assertEqual(decimal, expected_prefix)
        self.assertEqual(self.oracle["source_sha256"],
                         MOD.PINNED_ORACLE_SHA256)

    def test_base_forms_recombine_directly_from_raw_constant_channels(self):
        raw_i0 = sum(Fraction(self.raw["i_blocks"][str(r)][0][0])
                     for r in range(16))
        raw_j0 = sum(
            Fraction(self.raw["j_entries"][f"(({r}, 0), ({r}, 0))"])
            for r in range(16))
        raw_j0 += 2 * sum(
            Fraction(self.raw["j_entries"][f"(({r}, 0), ({r + 1}, 0))"])
            for r in range(15))
        self.assertEqual(self.oracle["I0"], raw_i0)
        self.assertEqual(self.oracle["B0"], 48 * raw_j0)

    def test_exact_i_stratum_weights_expose_missing_stratum_obstruction(self):
        weights = [self.oracle["I"][6 * r][6 * r] / self.oracle["I0"]
                   for r in range(16)]
        self.assertEqual(sum(weights), Fraction(1))
        self.assertTrue(Fraction(1, 10**8) < weights[13] <
                        Fraction(11, 10**8))
        self.assertTrue(Fraction(7, 10**11) < weights[14] <
                        Fraction(8, 10**11))
        self.assertTrue(Fraction(8, 10**18) < weights[15] <
                        Fraction(9, 10**18))

    def test_constant_features_normalize_to_one(self):
        constants = [6 * r for r in range(16)]
        self.assertEqual(
            sum(self.oracle["E_I"][i][j]
                for i in constants for j in constants), Fraction(1))
        self.assertEqual(
            sum(self.oracle["E_J"][i][j]
                for i in constants for j in constants), Fraction(1))

    def test_symmetry_sparsity_and_exact_power_scaling(self):
        alpha = self.oracle["alpha"]
        for i in range(96):
            for j in range(96):
                self.assertEqual(self.oracle["I"][i][j],
                                 self.oracle["I"][j][i])
                self.assertEqual(self.oracle["B48"][i][j],
                                 self.oracle["B48"][j][i])
                if i // 6 != j // 6:
                    self.assertEqual(self.oracle["I"][i][j], 0)
                if abs(i // 6 - j // 6) > 1:
                    self.assertEqual(self.oracle["B48"][i][j], 0)
        # Spot-check the normalization against one raw nonzero I entry and
        # one raw J entry, including the mandatory factor 48.
        raw_i = Fraction(self.raw["i_blocks"]["3"][1][4])
        self.assertEqual(self.oracle["I"][19][22], raw_i / alpha ** 3)
        key = "((3, 1), (4, 4))"
        raw_j = Fraction(self.raw["j_entries"][key])
        self.assertEqual(self.oracle["B48"][19][28],
                         48 * raw_j / alpha ** 3)

    def test_principal_index_dimensions_and_rejections(self):
        strata = range(16)
        self.assertEqual(len(MOD.principal_indices(strata, 0)), 16)
        self.assertEqual(len(MOD.principal_indices(strata, 1)), 48)
        self.assertEqual(len(MOD.principal_indices(strata, 2)), 96)
        with self.assertRaises(ValueError):
            MOD.principal_indices(strata, 3)
        with self.assertRaises(ValueError):
            MOD.principal_indices([0.0], 1)
        with self.assertRaises(ValueError):
            MOD.principal_indices([0], True)
        bad = dict(self.raw)
        bad["k"] = 49
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json") as handle:
            json.dump(bad, handle)
            handle.flush()
            with self.assertRaises(ValueError):
                MOD.load_exact_expectation_oracle(handle.name)

    def parse_mutation(self, mutate):
        altered = copy.deepcopy(self.raw)
        mutate(altered)
        return MOD._parse_exact_expectation_oracle_bytes(
            json.dumps(altered).encode(), "<hostile mutation>", "0" * 64)

    def test_incomplete_or_nonlocal_j_and_asymmetric_i_fail(self):
        def missing_j(raw):
            raw["j_entries"].pop("((4, 2), (5, 3))")

        def long_j(raw):
            raw["j_entries"]["((0, 0), (2, 0))"] = "0"

        def asymmetric_i(raw):
            raw["i_blocks"]["4"][1][2] = "0"
            if raw["i_blocks"]["4"][2][1] == "0":
                raw["i_blocks"]["4"][1][2] = "1"

        for mutation in (missing_j, long_j, asymmetric_i):
            with self.subTest(mutation=mutation.__name__), \
                    self.assertRaises(ValueError):
                self.parse_mutation(mutation)

    def test_noncanonical_exact_fields_and_duplicate_json_fail(self):
        with self.assertRaises(ValueError):
            self.parse_mutation(
                lambda raw: raw["i_blocks"]["0"][0].__setitem__(0, "2/2"))
        encoded = ORACLE_PATH.read_bytes()
        self.assertIn(b'"k": 48', encoded)
        duplicate = encoded.replace(b'"k": 48', b'"k": 48, "k": 48', 1)
        with self.assertRaises(ValueError):
            MOD._strict_json_bytes(duplicate)
        with self.assertRaises(ValueError):
            MOD._strict_json_bytes(b'{"timing":1e99999}')


if __name__ == "__main__":
    unittest.main()
