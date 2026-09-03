#!/usr/bin/env python3
"""Hostile independent tests for the repaired Green-v9 replay adapter."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
SOURCE = REPO / "verify/check_H1_236_Rle9_green_v9.py"
SOURCE_SHA256 = \
    "ef26a71fee7ee60f1c3b9e6e0ea227649fe70c45ae5d8d47f5da8f597b4045c5"


def digest(value):
    data = value if isinstance(value, bytes) else Path(value).read_bytes()
    return hashlib.sha256(data).hexdigest()


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"),
                       ensure_ascii=True, allow_nan=False) + "\n").encode("ascii")


if digest(SOURCE) != SOURCE_SHA256:
    raise RuntimeError("frozen repaired Green standalone adapter changed")
M = load("independent_green_Rle9_standalone", SOURCE)


def audit_fixture(count=3):
    return {
        "status": "GREEN-V9 CROSS SHARD STRUCTURAL/RESULT AUDIT PASS",
        "input_sha256": "1" * 64,
        "common_r": count,
        "scaled_b_shard": "7/11",
        "recombined_exactly": True,
        "maximum_active_shift": 14-count,
        "active_branch_families": ["large", "small", "small_total"],
        "fixed_denominator_relation_verified": True,
        "cache_inventory_semantics_verified": True,
        "green_boundary_denominator_proof_pinned": True,
        "convexity_fail_closed": True,
        "source_closure_verified": True,
        "reference_exact_fields_bit_equal": None,
        "reference_sha256": None,
        "total_scalar_products": 19,
        "total_surviving_product_monomials": 13,
    }


def make_inputs(root):
    root = Path(root)
    a_paths = [root / f"r{count:02d}.json" for count in M.BASE.A_COUNTS]
    b_paths = [root / f"common_r_{count:02d}.json"
               for count in M.BASE.B_COUNTS]
    snapshots = {}
    for count, path in enumerate(a_paths):
        data = canonical({
            "count": count,
            "exact_values": {"band_I_count": str(count+1)},
        })
        path.write_bytes(data)
        snapshots[path] = data
    large = 10**100
    for count, path in enumerate(b_paths):
        value = large+count
        raw = {"common_r": count, "scaled_b_shard": str(value)}
        if count == 9:
            raw["branch_values_and_fast_stats"] = {
                "high": {"Sdelta": str(value), "Stotal": "0"},
                "low": {"Sdelta": "0", "Stotal": "0"},
            }
        data = canonical(raw)
        path.write_bytes(data)
        snapshots[path] = data
    inner = {
        "exact_denominator": "2",
        "exact_numerator": "1",
        "exact_deficit": "1",
    }
    return inner, a_paths, b_paths, snapshots


def aggregate_record(reconstructed, bind_hashes):
    dummy = "f" * 64
    result = {
        "format": M._GREEN_FORMAT,
        "status": "EXACT R<=9 ONE-BAND SCALAR CERTIFICATE PASS",
        "rigorous": True,
        "theorem_ready_scalar": True,
        "k": 48,
        "outer_direction": M.BASE.expected_outer_direction(),
        "scales": {
            "F": str(M.BASE.SCALE_F), "H": str(M.BASE.SCALE_H),
            "quadratic_inner": str(M.BASE.FORM_SCALE),
        },
        "exact": {key: str(value)
                  for key, value in reconstructed["exact"].items()},
        "a_shards": [],
        "zeroed_a_shards": [],
        "b_shards": [],
        "trust_scope": "synthetic exact Green adapter fixture",
        "assembler_sha256": M.GREEN_AGGREGATOR_SHA256,
        "rle9_base_assembler_sha256": M.GREEN.R09_ASSEMBLER_SHA256,
        "full_assembler_sha256": M.GREEN.R09.FULL_ASSEMBLER_SHA256,
        "b_engine": M._GREEN_ENGINE,
        "source_hashes": {},
    }
    for count in M.BASE.KEPT_A_COUNTS:
        result["a_shards"].append({
            "count": count,
            "value": str(reconstructed["all_a"][count]),
            "sha256": (reconstructed["a_hashes"][count]
                       if bind_hashes else dummy),
        })
    for count in M.BASE.ZEROED_A_COUNTS:
        result["zeroed_a_shards"].append({
            "count": count,
            "value": str(reconstructed["all_a"][count]),
            "sha256": (reconstructed["a_hashes"][count]
                       if bind_hashes else dummy),
        })
    for count in M.BASE.B_COUNTS:
        result["b_shards"].append({
            "count": count,
            "value": str(reconstructed["selected_b"][count]),
            "full_shard_value": str(reconstructed["full_b"][count]),
            "selection": reconstructed["rules"][count],
            "sha256": (reconstructed["b_hashes"][count]
                       if bind_hashes else dummy),
        })
    return result


class GreenStandaloneAdapterAudit(unittest.TestCase):
    def test_flat_closure_and_runtime_configuration(self):
        self.assertEqual(len(M.PINS), 74)
        self.assertEqual(len(M.PINS), len(set(M.PINS)))
        for path, expected in M.PINS.items():
            self.assertEqual(digest(path), expected, str(path))
        self.assertEqual(
            M.PINS.get(M._OLD_AGGREGATOR_PATH), M._OLD_AGGREGATOR_SHA256)
        self.assertEqual(
            M.PINS.get(M.REPO / M.GREEN.GREEN.V8.PRODUCER),
            M.GREEN.GREEN.V8.PRODUCER_SHA)
        self.assertIs(M.BASE.FILE, M.FILE)
        self.assertIs(M.BASE.AGG, M.GREEN)
        self.assertEqual(M.BASE.ASSEMBLER, M.GREEN_AGGREGATOR_PATH)
        self.assertEqual(M.BASE.B_PRODUCER, M.GREEN.GREEN_RUNNER)
        self.assertEqual(M.BASE.B_RESULT_CHECKER, M.GREEN.GREEN_CHECKER)
        self.assertEqual(M.BASE.DEFAULT_CERTIFICATE, M.DEFAULT_CERTIFICATE)
        self.assertEqual(M.BASE.PINS, M.PINS)
        self.assertIs(M.BASE.compare_certificate, M.compare_green_certificate)
        self.assertIs(M.BASE.BASE.strict_loads, M.strict_loads_for_green)

    def test_fresh_import_has_no_explicit_repo_read_outside_closure(self):
        original = Path.read_bytes
        seen = set()
        repo = REPO.resolve()

        def recording_read(path):
            resolved = path.resolve()
            try:
                resolved.relative_to(repo)
            except ValueError:
                pass
            else:
                seen.add(resolved)
            return original(path)

        with mock.patch.object(Path, "read_bytes", recording_read):
            fresh = load("independent_green_adapter_read_trace", SOURCE)
        self.assertTrue(seen)
        self.assertEqual(seen - (set(fresh.PINS) | {fresh.FILE}), set())
        self.assertIn(fresh._OLD_AGGREGATOR_PATH, seen)

    def test_exact_green_audit_schema_and_types(self):
        raw = audit_fixture()
        translated = M.adapt_b_audit(raw, "b audit stdout r=3")
        self.assertEqual(raw, audit_fixture())
        self.assertEqual(
            translated["status"],
            "FIXED-POLYGON-V8 CROSS SHARD STRUCTURAL/RESULT AUDIT PASS")
        self.assertTrue(translated["fixed_polygon_denominator_proof_pinned"])
        self.assertNotIn("green_boundary_denominator_proof_pinned", translated)

        for key in raw:
            mutant = copy.deepcopy(raw)
            del mutant[key]
            with self.assertRaises(M.BASE.VerificationError, msg=key):
                M.adapt_b_audit(mutant, "mutant")
        mutant = copy.deepcopy(raw)
        mutant["extra"] = 0
        with self.assertRaises(M.BASE.VerificationError):
            M.adapt_b_audit(mutant, "mutant")
        for key, value in (
                ("common_r", True), ("common_r", 3.0),
                ("common_r", -1), ("common_r", 10),
                ("maximum_active_shift", True),
                ("maximum_active_shift", 10),
                ("active_branch_families", ["small", "large", "small_total"]),
                ("input_sha256", "A" * 64),
                ("input_sha256", "0" * 63),
                ("scaled_b_shard", "14/22"),
                ("scaled_b_shard", "0.5"),
                ("scaled_b_shard", 1),
                ("total_scalar_products", True),
                ("total_scalar_products", 0),
                ("total_surviving_product_monomials", -1),
                ("reference_exact_fields_bit_equal", True),
                ("reference_sha256", "2" * 64)):
            mutant = copy.deepcopy(raw)
            mutant[key] = value
            with self.assertRaises(M.BASE.VerificationError, msg=f"{key}={value!r}"):
                M.adapt_b_audit(mutant, "mutant")
        for key in (
                "recombined_exactly", "fixed_denominator_relation_verified",
                "cache_inventory_semantics_verified",
                "green_boundary_denominator_proof_pinned",
                "convexity_fail_closed", "source_closure_verified"):
            mutant = copy.deepcopy(raw)
            mutant[key] = False
            with self.assertRaises(M.BASE.VerificationError, msg=key):
                M.adapt_b_audit(mutant, "mutant")

    def test_strict_loader_translation_is_nonmutating_and_scoped(self):
        raw = audit_fixture()
        data = canonical(raw)
        translated = M.strict_loads_for_green(data, "b audit stdout r=3")
        self.assertEqual(raw, audit_fixture())
        self.assertIn("fixed_polygon_denominator_proof_pinned", translated)
        untouched = M.strict_loads_for_green(data, "tuple checker stdout")
        self.assertEqual(untouched, raw)

    def test_certificate_adapter_reuses_complete_exact_base_comparison(self):
        with tempfile.TemporaryDirectory(prefix="green-adapter-exact-") as text:
            inner, a_paths, b_paths, snapshots = make_inputs(text)
            reconstructed = M.BASE.exact_scalar_reconstruction(
                inner, a_paths, b_paths, snapshots)
            self.assertGreater(
                reconstructed["exact"]["margin_b_squared_minus_A_D"], 0)
            certificate = aggregate_record(reconstructed, bind_hashes=False)
            aggregate = aggregate_record(reconstructed, bind_hashes=True)
            M.compare_green_certificate(certificate, aggregate, reconstructed)
            self.assertEqual(certificate["format"], M._GREEN_FORMAT)
            self.assertEqual(aggregate["b_engine"], M._GREEN_ENGINE)

            for owner, key, value in (
                    (certificate, "format", "wrong"),
                    (aggregate, "b_engine", "wrong"),
                    (certificate, "assembler_sha256", "0" * 64)):
                mutant = copy.deepcopy(owner)
                mutant[key] = value
                c = mutant if owner is certificate else certificate
                a = mutant if owner is aggregate else aggregate
                with self.assertRaises(M.BASE.VerificationError):
                    M.compare_green_certificate(c, a, reconstructed)
            mutant = copy.deepcopy(aggregate)
            mutant["exact"]["b_scaled"] = "0"
            with self.assertRaises(M.BASE.VerificationError):
                M.compare_green_certificate(certificate, mutant, reconstructed)

    def test_base_self_and_pin_gate_precedes_every_heavy_stage(self):
        with tempfile.TemporaryDirectory(prefix="green-adapter-fail-fast-") as text:
            certificate = Path(text) / "certificate.json"
            certificate.write_bytes(b"{}\n")
            with mock.patch.object(
                    M.BASE, "run_stage",
                    side_effect=AssertionError("heavy stage was reached")):
                with self.assertRaisesRegex(
                        M.BASE.VerificationError,
                        "compact certificate SHA-256 mismatch"):
                    M.BASE.verify([
                        "--certificate", str(certificate),
                        "--expected-certificate-sha256", "0" * 64,
                        "--expected-self-sha256", SOURCE_SHA256,
                    ])


if __name__ == "__main__":
    unittest.main()
