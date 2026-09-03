#!/usr/bin/env python3
"""Independent hostile tests for the repaired Green-v9 result checker."""

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
CHECKER = HERE / "verify_green_v9_cross_shard.py"
V7_FIXTURE = HERE / "test_verify_cached_v7_cross_shard.py"
V6_FIXTURE = HERE / "test_verify_fixed_v6_cross_shard.py"
PINS = {
    CHECKER:
        "7dbb352011d840a5bddf8f6f101f864d0a1b1e436ff4ebb5533ef1137217b4a7",
    V7_FIXTURE:
        "669ab6178848201927a42c36c9271a27c119f67038606873ca9924a2883db186",
    V6_FIXTURE:
        "3f7eb92c2f14923740f3eb6454eca354793420a7d033d83b5cda7a63438fb887",
}


def digest(value):
    data = value if isinstance(value, bytes) else Path(value).read_bytes()
    return hashlib.sha256(data).hexdigest()


def load(name, path):
    if digest(path) != PINS[path]:
        raise RuntimeError(f"pinned Green-v9 audit input changed: {path}")
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


V = load("independent_green_v9_checker", CHECKER)
T7 = load("independent_green_v9_v7_fixture", V7_FIXTURE)
T6 = load("independent_green_v9_v6_fixture", V6_FIXTURE)


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"),
                       ensure_ascii=True, allow_nan=False) + "\n").encode("ascii")


def fixtures():
    v7 = T7.to_v7(V.V8.V7, T6.synthetic_r0(V.V8.V7.V6))
    v8 = copy.deepcopy(v7)
    v8.update({
        "format": "D14-grid38-scaled-cutoff-cross-common-r-fixed-polygon-v8",
        "status": "EXACT FIXED-POLYGON COMMON-r CROSS SHARD PASS",
        "producer_sha256": V.V8.PRODUCER_SHA,
        "source_hashes": V.V8.SOURCE_HASHES,
        "algorithm": V.V8.ALGORITHM,
    })
    v9 = copy.deepcopy(v8)
    v9.update({
        "format": "D14-grid38-scaled-cutoff-cross-common-r-green-v9",
        "status": "EXACT GREEN-POLYGON COMMON-r CROSS SHARD PASS",
        "producer_sha256": V.PRODUCER_SHA,
        "source_hashes": V.SOURCE_HASHES,
        "algorithm": V.ALGORITHM,
    })
    return v9, v8


def write(root, name, raw):
    path = root / name
    path.write_bytes(canonical(raw))
    return path


class GreenV9CheckerAudit(unittest.TestCase):
    def test_normalization_changes_exactly_five_identity_fields(self):
        raw, v8 = fixtures()
        normalized = V.normalized_v8(raw)
        changed = {key for key in raw if raw[key] != normalized[key]}
        self.assertEqual(changed, {
            "format", "status", "producer_sha256", "source_hashes", "algorithm"})
        self.assertEqual(normalized, v8)

    def test_reference_allows_only_timing_and_rss_differences(self):
        raw, reference = fixtures()
        reference["timing_seconds"]["total"] += 19.25
        reference["branch_values_and_fast_stats"]["timing_seconds"][
            "integrate_globally_collected_integers"] += 17.5
        reference["peak_rss_kib"] += 1234
        with tempfile.TemporaryDirectory(prefix="green-v9-check-valid-") as text:
            root = Path(text)
            shard = write(root, "v9.json", raw)
            prior = write(root, "v8.json", reference)
            result = V.audit(shard, prior)
            self.assertEqual(result["input_sha256"], digest(shard))
            self.assertTrue(result["reference_exact_fields_bit_equal"])
            self.assertEqual(result["reference_sha256"], digest(prior))
            self.assertTrue(result["convexity_fail_closed"])
            self.assertTrue(result["green_boundary_denominator_proof_pinned"])

    def test_consistent_branch_and_factor48_mutation_fails_reference(self):
        raw, reference = fixtures()
        block = raw["branch_values_and_fast_stats"]
        block["high"]["Sdelta"] = str(Q(block["high"]["Sdelta"]) + 7)
        raw["scaled_b_shard"] = str(Q(raw["scaled_b_shard"]) + 48 * 7)
        with tempfile.TemporaryDirectory(prefix="green-v9-check-branch-") as text:
            root = Path(text)
            shard = write(root, "v9.json", raw)
            prior = write(root, "v8.json", reference)
            with self.assertRaisesRegex(ArithmeticError, "exact field differs|branch field"):
                V.audit(shard, prior)

    def test_schema_source_type_and_work_mutations_fail(self):
        base, _ = fixtures()
        mutants = []
        mutant = copy.deepcopy(base)
        mutant["extra"] = None
        mutants.append(mutant)
        mutant = copy.deepcopy(base)
        mutant["producer_sha256"] = "0" * 64
        mutants.append(mutant)
        mutant = copy.deepcopy(base)
        mutant["source_hashes"][V.GREEN_SOURCE] = "0" * 64
        mutants.append(mutant)
        mutant = copy.deepcopy(base)
        mutant["common_r"] = True
        mutants.append(mutant)
        mutant = copy.deepcopy(base)
        mutant["branch_values_and_fast_stats"]["integer_radialization"][
            "radial_stats"]["cached_factorial_ratios"] = -1
        mutants.append(mutant)
        with tempfile.TemporaryDirectory(prefix="green-v9-check-mutants-") as text:
            root = Path(text)
            for index, mutant in enumerate(mutants):
                path = write(root, f"mutant-{index}.json", mutant)
                with self.assertRaises(Exception, msg=index):
                    V.audit(path)

    def test_cli_self_pin_and_exclusive_publication(self):
        raw, _ = fixtures()
        with tempfile.TemporaryDirectory(prefix="green-v9-check-cli-") as text:
            root = Path(text)
            shard = write(root, "v9.json", raw)
            output = root / "audit.json"
            argv = [str(CHECKER), "--expected-self-sha256", PINS[CHECKER],
                    "--output", str(output), str(shard)]
            with mock.patch.object(sys, "argv", argv):
                V.main()
            original = output.read_bytes()
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
