#!/usr/bin/env python3

from __future__ import annotations

from copy import deepcopy
from fractions import Fraction as Q
import importlib.util
import json
from pathlib import Path
import sys
import unittest


FILE = Path(__file__).resolve()
SOURCE = FILE.with_name("frontier_active25_inner_d18_adapter.py")
SPEC = importlib.util.spec_from_file_location("active25_inner_d18_adapter", SOURCE)
M = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = M
SPEC.loader.exec_module(M)


def payloads():
    return tuple(json.loads(M._START[path])
                 for path in (M.CERT, M.RADIAL, M.BASELINE))


class D18AdapterTests(unittest.TestCase):
    def test_exact_d18_identity_and_baseline_reconstruction(self):
        basis, vector, amplitudes, denominator, numerator = \
            M.load_inner_coordinate()
        self.assertEqual(len(basis), 471)
        self.assertEqual(len(vector), 471)
        self.assertEqual(basis,
                         tuple(M.v2.core.shell.ei.even_basis(18)))
        self.assertEqual(amplitudes[0], 1)
        self.assertGreater(denominator, 0)
        radial = json.loads(M._START[M.RADIAL])
        self.assertEqual(numerator / denominator,
                         Q(radial["exact_quotient"]))

    def test_production_adapter_changes_only_inner_loader(self):
        named, catalog, weights, inner_i, inner_b, dimension = \
            M.production_inputs()
        self.assertEqual(dimension, 471)
        self.assertEqual(tuple(named), ("R", "V", "H", "L"))
        self.assertEqual(catalog, (("rh", "R", "H"),
                                   ("rl", "R", "L"),
                                   ("vh", "V", "H"),
                                   ("vl", "V", "L")))
        self.assertEqual(weights,
                         M.v2.core.production_pair_weights(
                             M.load_inner_coordinate()[2]))
        self.assertEqual((inner_i, inner_b),
                         M.load_inner_coordinate()[3:])
        self.assertEqual(named["H"][0].schedule, M.v2.core.SCHEDULE)
        self.assertEqual(named["L"][0].schedule, M.v2.core.SCHEDULE)

    def test_low_k_grouped_equals_literal_four_channel_contraction(self):
        basis = tuple(M.v2.core.shell.ei.even_basis(2))
        vector = (Q(2), Q(-3, 5), Q(7, 11), Q(-2, 13))
        amplitudes = (Q(1), Q(4, 5))
        named, catalog, weights, _, _, _ = M.low_k_inputs(
            2, basis, vector, amplitudes)
        literal, _, _ = M.v2.core.tagged_cross_catalog(
            named, catalog, M.v2.core.ETA2, common_strata=(0, 1),
            integrate=True)
        expected = [sum((weights[tag] * literal[tag][r]
                         for tag, _, _ in catalog), Q(0))
                    for r in range(3)]
        grouped, _, _, _, _ = M.v2.core.grouped_weighted_cross(
            named, catalog, weights, M.v2.core.ETA2,
            common_strata=(0, 1), direct_full_left=("R", "V"))
        self.assertEqual(grouped[:3], expected)
        self.assertTrue(all(value == 0 for value in grouped[3:]))

    def test_mutated_certificate_labels_coefficients_and_factor_reject(self):
        cert, radial, baseline = payloads()
        bad = deepcopy(cert)
        bad["basis"][0], bad["basis"][1] = bad["basis"][1], bad["basis"][0]
        with self.assertRaises(ValueError):
            M.validate_payloads(bad, radial, baseline)
        bad = deepcopy(cert)
        bad["rational_vector"][0] = "2/2"
        with self.assertRaises(ValueError):
            M.validate_payloads(bad, radial, baseline)
        bad_radial = deepcopy(radial)
        bad_radial["k"] = 47
        with self.assertRaises(ValueError):
            M.validate_payloads(cert, bad_radial, baseline)

    def test_mutated_radial_forms_baseline_and_schema_reject(self):
        cert, radial, baseline = payloads()
        bad = deepcopy(radial)
        bad["I_matrix"][0][0] = str(Q(bad["I_matrix"][0][0]) + 1)
        with self.assertRaises(ValueError):
            M.validate_payloads(cert, bad, baseline)
        bad = deepcopy(baseline)
        bad["rows"][0]["exact_numerator"] = cert["exact_denominator"]
        with self.assertRaises(ValueError):
            M.validate_payloads(cert, radial, bad)
        bad = deepcopy(radial)
        bad["extra"] = None
        with self.assertRaises(ValueError):
            M.validate_payloads(cert, bad, baseline)

    def test_preflight_is_read_only_and_degree_specific(self):
        value = M.preflight()
        self.assertEqual(value["basis_dimension"], 471)
        self.assertEqual(value["active_outer_counts"], list(range(26)))
        self.assertIs(value["target_started"], False)
        self.assertIs(value["theorem_ready"], False)


if __name__ == "__main__":
    unittest.main()
