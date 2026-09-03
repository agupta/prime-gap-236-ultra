#!/usr/bin/env python3
"""Unit and mutation tests for the Green-v9 standalone replay adapter."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
from pathlib import Path
import sys
import unittest
from unittest import mock


HERE = Path(__file__).resolve().parent
SOURCE = HERE / "check_H1_236_Rle9_green_v9.py"


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


M = load("check_H1_236_Rle9_green_v9_test", SOURCE)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def audit_fixture():
    return {
        "status": "GREEN-V9 CROSS SHARD STRUCTURAL/RESULT AUDIT PASS",
        "input_sha256": "1" * 64,
        "scaled_b_shard": "7/11",
        "green_boundary_denominator_proof_pinned": True,
        "convexity_fail_closed": True,
        "source_closure_verified": True,
        "recombined_exactly": True,
        "fixed_denominator_relation_verified": True,
        "cache_inventory_semantics_verified": True,
        "maximum_active_shift": 11,
        "active_branch_families": ["large", "small", "small_total"],
        "reference_exact_fields_bit_equal": None,
        "reference_sha256": None,
        "total_scalar_products": 19,
        "total_surviving_product_monomials": 13,
        "common_r": 3,
    }


class GreenStandaloneAdapterTest(unittest.TestCase):
    def test_flat_pin_closure_and_runtime_configuration(self):
        for path, expected in M.PINS.items():
            self.assertEqual(digest(path), expected, str(path))
        self.assertIs(M.BASE.FILE, M.FILE)
        self.assertIs(M.BASE.AGG, M.GREEN)
        self.assertEqual(M.BASE.B_PRODUCER, M.GREEN.GREEN_RUNNER)
        self.assertEqual(M.BASE.B_RESULT_CHECKER, M.GREEN.GREEN_CHECKER)
        self.assertEqual(M.BASE.PINS, M.PINS)

    def test_green_audit_translation_is_narrow_and_fail_closed(self):
        raw = audit_fixture()
        translated = M.adapt_b_audit(raw, "b audit stdout r=3")
        self.assertEqual(raw, audit_fixture())
        self.assertEqual(
            translated["status"],
            "FIXED-POLYGON-V8 CROSS SHARD STRUCTURAL/RESULT AUDIT PASS")
        self.assertTrue(translated["fixed_polygon_denominator_proof_pinned"])
        self.assertNotIn("green_boundary_denominator_proof_pinned", translated)
        for key in ("convexity_fail_closed", "recombined_exactly", "common_r"):
            self.assertEqual(translated[key], raw[key])
        for key in ("green_boundary_denominator_proof_pinned",
                    "convexity_fail_closed", "source_closure_verified",
                    "recombined_exactly", "fixed_denominator_relation_verified",
                    "cache_inventory_semantics_verified"):
            mutant = copy.deepcopy(raw)
            mutant[key] = False
            with self.assertRaises(M.BASE.VerificationError):
                M.adapt_b_audit(mutant, "mutant")
        for key, value in (
                ("common_r", True),
                ("maximum_active_shift", 10),
                ("active_branch_families", ["large", "small"]),
                ("reference_exact_fields_bit_equal", True),
                ("reference_sha256", "2" * 64),
                ("scaled_b_shard", "0.5"),
                ("total_scalar_products", True)):
            mutant = copy.deepcopy(raw)
            mutant[key] = value
            with self.assertRaises(M.BASE.VerificationError):
                M.adapt_b_audit(mutant, "mutant")
        mutant = copy.deepcopy(raw)
        mutant["extra"] = 1
        with self.assertRaises(M.BASE.VerificationError):
            M.adapt_b_audit(mutant, "mutant")

    def test_certificate_adapter_changes_only_two_backend_names(self):
        certificate = {
            "format": M._GREEN_FORMAT,
            "b_engine": M._GREEN_ENGINE,
            "sentinel": {"x": 7},
        }
        aggregate = copy.deepcopy(certificate)
        reconstructed = object()

        def oracle(c, a, r):
            self.assertIs(r, reconstructed)
            self.assertEqual(c["format"], M._V8_FORMAT)
            self.assertEqual(a["format"], M._V8_FORMAT)
            self.assertEqual(c["b_engine"], M._V8_ENGINE)
            self.assertEqual(a["b_engine"], M._V8_ENGINE)
            self.assertEqual(c["sentinel"], {"x": 7})
            self.assertEqual(a["sentinel"], {"x": 7})
            return "PASS"

        with mock.patch.object(M, "_OLD_COMPARE_CERTIFICATE", oracle):
            self.assertEqual(M.compare_green_certificate(
                certificate, aggregate, reconstructed), "PASS")
        self.assertEqual(certificate["format"], M._GREEN_FORMAT)
        self.assertEqual(aggregate["b_engine"], M._GREEN_ENGINE)
        for bad_key, bad_value in (("format", "wrong"),
                                   ("b_engine", "wrong")):
            mutant = copy.deepcopy(certificate)
            mutant[bad_key] = bad_value
            with self.assertRaises(M.BASE.VerificationError):
                M.compare_green_certificate(mutant, aggregate, reconstructed)


if __name__ == "__main__":
    unittest.main()
