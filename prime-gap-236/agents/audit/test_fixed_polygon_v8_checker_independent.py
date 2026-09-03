#!/usr/bin/env python3
"""Independent hostile tests for the repaired fixed-polygon-v8 checker."""

from __future__ import annotations

import copy
from fractions import Fraction as Q
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock


HERE = Path(__file__).resolve().parent
CHECKER_PATH = HERE / "verify_fixed_polygon_v8_cross_shard.py"
V7_FIXTURE_PATH = HERE / "test_verify_cached_v7_cross_shard.py"
V6_FIXTURE_PATH = HERE / "test_verify_fixed_v6_cross_shard.py"
PINS = {
    CHECKER_PATH:
        "ec0162a73381d031e4ab7b5d8cb1fa16381e41f19c74a6fd74aafa0c30a8655c",
    V7_FIXTURE_PATH:
        "669ab6178848201927a42c36c9271a27c119f67038606873ca9924a2883db186",
    V6_FIXTURE_PATH:
        "3f7eb92c2f14923740f3eb6454eca354793420a7d033d83b5cda7a63438fb887",
}


def digest(value):
    raw = value if isinstance(value, bytes) else value.read_bytes()
    return hashlib.sha256(raw).hexdigest()


def load(name, path):
    if digest(path) != PINS[path]:
        raise RuntimeError(f"pinned audit fixture changed: {path}")
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


V = load("fixed_polygon_v8_independent_checker", CHECKER_PATH)
T7 = load("fixed_polygon_v8_independent_v7_fixture", V7_FIXTURE_PATH)
T6 = load("fixed_polygon_v8_independent_v6_fixture", V6_FIXTURE_PATH)


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"),
                       ensure_ascii=True, allow_nan=False) + "\n").encode("ascii")


def fixtures():
    v7 = T7.to_v7(V.V7, T6.synthetic_r0(V.V7.V6))
    v8 = copy.deepcopy(v7)
    v8.update({
        "format": "D14-grid38-scaled-cutoff-cross-common-r-fixed-polygon-v8",
        "status": "EXACT FIXED-POLYGON COMMON-r CROSS SHARD PASS",
        "producer_sha256": V.PRODUCER_SHA,
        "source_hashes": V.SOURCE_HASHES,
        "algorithm": V.ALGORITHM,
    })
    return v8, v7


def write(root, name, raw):
    path = root / name
    path.write_bytes(canonical(raw))
    return path


class FixedPolygonV8CheckerIndependentTest(unittest.TestCase):
    def test_normalization_changes_only_proved_identity_fields(self):
        raw, v7 = fixtures()
        normalized = V.normalized_v7(raw)
        changed = {
            key for key in raw if normalized[key] != raw[key]}
        self.assertEqual(changed, {
            "format", "status", "producer_sha256", "source_hashes", "algorithm"})
        self.assertEqual(normalized, v7)

    def test_valid_audit_binds_bytes_and_allows_only_timing_rss_differences(self):
        raw, reference = fixtures()
        reference["timing_seconds"]["total"] += 99.5
        reference["branch_values_and_fast_stats"]["timing_seconds"][
            "integrate_globally_collected_integers"] += 88.25
        reference["peak_rss_kib"] += 12345
        with tempfile.TemporaryDirectory(prefix="v8-check-valid-") as root_text:
            root = Path(root_text)
            path = write(root, "v8.json", raw)
            reference_path = write(root, "v7.json", reference)
            result = V.audit(path, reference_path)
            self.assertEqual(result["input_sha256"], digest(path))
            self.assertEqual(result["common_r"], 0)
            self.assertTrue(result["recombined_exactly"])
            self.assertTrue(result["fixed_polygon_denominator_proof_pinned"])
            self.assertTrue(result["reference_exact_fields_bit_equal"])
            self.assertEqual(result["reference_sha256"], digest(reference_path))

    def test_consistent_exact_branch_change_fails_reference_comparison(self):
        raw, reference = fixtures()
        branch = "Sdelta"
        old = Q(raw["branch_values_and_fast_stats"]["high"][branch])
        raw["branch_values_and_fast_stats"]["high"][branch] = str(old + 1)
        raw["scaled_b_shard"] = str(Q(raw["scaled_b_shard"]) + 48)
        with tempfile.TemporaryDirectory(prefix="v8-check-branch-") as root_text:
            root = Path(root_text)
            path = write(root, "v8.json", raw)
            reference_path = write(root, "v7.json", reference)
            with self.assertRaisesRegex(ArithmeticError, "exact field differs|branch field"):
                V.audit(path, reference_path)

    def test_schema_source_count_and_work_mutations_fail(self):
        base, _ = fixtures()
        mutants = []
        raw = copy.deepcopy(base)
        raw["extra"] = None
        mutants.append(raw)
        raw = copy.deepcopy(base)
        raw["producer_sha256"] = "0" * 64
        mutants.append(raw)
        raw = copy.deepcopy(base)
        raw["source_hashes"][V.MOMENT_SOURCE] = "0" * 64
        mutants.append(raw)
        raw = copy.deepcopy(base)
        raw["common_r"] = True
        mutants.append(raw)
        raw = copy.deepcopy(base)
        raw["branch_values_and_fast_stats"]["integer_radialization"][
            "radial_stats"]["cached_factorial_ratios"] = -1
        mutants.append(raw)
        with tempfile.TemporaryDirectory(prefix="v8-check-mutants-") as root_text:
            root = Path(root_text)
            for index, raw in enumerate(mutants):
                path = write(root, f"mutant-{index}.json", raw)
                with self.assertRaises(Exception, msg=index):
                    V.audit(path)

    def test_cli_self_pin_and_exclusive_output(self):
        raw, _ = fixtures()
        with tempfile.TemporaryDirectory(prefix="v8-check-cli-") as root_text:
            root = Path(root_text)
            shard = write(root, "v8.json", raw)
            output = root / "audit.json"
            argv = [
                str(CHECKER_PATH), "--expected-self-sha256", PINS[CHECKER_PATH],
                "--output", str(output), str(shard),
            ]
            with mock.patch.object(sys, "argv", argv):
                V.main()
            original = output.read_bytes()
            parsed = json.loads(original)
            self.assertEqual(parsed["input_sha256"], digest(shard))
            with mock.patch.object(sys, "argv", argv):
                with self.assertRaises(FileExistsError):
                    V.main()
            self.assertEqual(output.read_bytes(), original)
            argv[2] = "0" * 64
            with mock.patch.object(sys, "argv", argv):
                with self.assertRaises(RuntimeError):
                    V.main()


if __name__ == "__main__":
    unittest.main()
