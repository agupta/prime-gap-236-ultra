#!/usr/bin/env python3
"""Independent hostile tests for the frozen fixed-v6 scalar wrapper."""

from __future__ import annotations

import copy
from fractions import Fraction as Q
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys
import tempfile
import unittest


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
SOURCE = REPO / "verify/assemble_one_band_236_fixed_v6.py"
SOURCE_SHA = "91ab96385d32921c035bd5537a56e8254455a8033bf41e2298b7ec13be552bbc"
V5_R0 = (REPO / "agents/exact-projection-engine/results/"
         "d14_grid38_scaled_b_collected_v5/common_r_00.json")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


if digest(SOURCE) != SOURCE_SHA:
    raise RuntimeError("fixed-v6 assembler is not the audited frozen snapshot")
M = load("fixed_v6_assembler_independent_audit", SOURCE)


def canonical(row):
    return (json.dumps(row, sort_keys=True, separators=(",", ":"),
                       ensure_ascii=True, allow_nan=False) + "\n").encode("ascii")


def v6_r0_fixture():
    row = json.loads(V5_R0.read_text())
    row["format"] = "D14-grid38-scaled-cutoff-cross-common-r-fixed-v6"
    row["status"] = "EXACT FIXED-DENOMINATOR COMMON-r CROSS SHARD PASS"
    row["producer_sha256"] = M.V6_RUNNER_SHA256
    row["algorithm"] = M.V6_ALGORITHM
    row["source_hashes"] = M.V6_SOURCE_HASHES
    integer = row["branch_values_and_fast_stats"]["integer_radialization"]
    integer["active_branch_families"] = ["large", "small", "small_total"]
    integer["inactive_families_pruned_before_radialization"] = []
    radial = integer["radial_stats"]
    degree, ceiling = 32, 78
    provisional = 60**degree*math.factorial(ceiling)
    radial_denominator = int(integer["radial_denominator"])
    if provisional % radial_denominator:
        raise AssertionError("fixture radial denominator is not cleared by D")
    radial.update({
        "fixed_provisional_denominator_bits": provisional.bit_length(),
        "fixed_denominator_common_gcd_bits":
            (provisional//radial_denominator).bit_length(),
        "maximum_orbit_degree": degree, "factorial_ceiling": ceiling,
    })
    timing = row["branch_values_and_fast_stats"]["timing_seconds"]
    timing["radialize_fixed_denominator_integers"] = timing.pop(
        "radialize_integer")
    return row


def v6_r12_fixture():
    row = v6_r0_fixture()
    row["common_r"] = 12
    block = row["branch_values_and_fast_stats"]
    for side in ("high", "low", "high_stats", "low_stats"):
        block[side] = {key: value for key, value in block[side].items()
                       if key in {"Sdelta", "Stotal"}}
    high = sum(map(Q, block["high"].values()), Q(0))
    low = sum(map(Q, block["low"].values()), Q(0))
    row["scaled_b_shard"] = str(48*(high-low))
    integer = block["integer_radialization"]
    integer["active_branch_families"] = ["small", "small_total"]
    integer["inactive_families_pruned_before_radialization"] = ["large"]
    entries = row["family_stats"]["family_orbit_tag_entries"]
    active_entries = entries["small"]+entries["small_total"]
    integer["clear_stats"]["family_coefficients"] = active_entries
    radial = integer["radial_stats"]
    radial["orbit_tag_associations"] = active_entries
    radial["maximum_shift_pruned_inside_convolution"] = 2
    integer["family_denominator"] = "1"
    integer["radial_denominator"] = "1"
    integer["combined_denominator_bits"] = 1
    integer["clear_stats"]["common_denominator_bits"] = 1
    radial["radial_denominator_bits"] = 1
    degree = radial["maximum_orbit_degree"]
    provisional = 60**degree*math.factorial(degree+46)
    radial["fixed_denominator_common_gcd_bits"] = provisional.bit_length()
    return row


class FixedV6AssemblerIndependentAudit(unittest.TestCase):
    def test_exact_runner_wire_union_and_live_pins(self):
        self.assertEqual(digest(SOURCE), SOURCE_SHA)
        runner = load(
            "fixed_v6_assembler_audit_runner", M.V6_RUNNER)
        v5 = load("fixed_v6_assembler_audit_v5", runner.V5_RUNNER_PATH)
        v2 = load("fixed_v6_assembler_audit_v2", v5.V2_PATH)
        base = load("fixed_v6_assembler_audit_base", v2.BASE_PATH)
        wire = {str(path.relative_to(REPO)): expected for path, expected in {
            **base.PINNED, **v2.LOCAL_PINNED,
            **v5.LOCAL_PINNED, **runner.LOCAL_PINNED}.items()}
        self.assertEqual(M.V6_SOURCE_HASHES, wire)
        self.assertEqual(len(wire), 23)
        self.assertEqual(len(M.PINS), 34)
        self.assertIn(M.B.INNER_RESULT, M.PINS)
        for path, expected in M.PINS.items():
            self.assertEqual(digest(path), expected, str(path))

    def test_real_r0_mathematical_fields_under_v6_wire_contract(self):
        row = v6_r0_fixture()
        observed = M.parse_b_shard(Path("r0-synthetic-v6.json"),
                                   canonical(row), 0)
        self.assertEqual(observed, Q(json.loads(V5_R0.read_text())[
            "scaled_b_shard"]))

    def test_r12_pruning_and_active_work_inventory(self):
        row = v6_r12_fixture()
        M.parse_b_shard(Path("r12-synthetic-v6.json"), canonical(row), 12)
        mutant = copy.deepcopy(row)
        mutant["branch_values_and_fast_stats"]["integer_radialization"][
            "clear_stats"]["family_coefficients"] += 1
        with self.assertRaisesRegex(ArithmeticError, "denominator/work"):
            M.parse_b_shard(Path("mutant.json"), canonical(mutant), 12)
        mutant = copy.deepcopy(row)
        mutant["branch_values_and_fast_stats"]["integer_radialization"][
            "radial_stats"]["orbit_tag_associations"] += 1
        with self.assertRaisesRegex(ArithmeticError, "denominator/work"):
            M.parse_b_shard(Path("mutant.json"), canonical(mutant), 12)

    def test_huge_degree_and_ceiling_rejected_before_factorial(self):
        row = v6_r12_fixture()
        radial = row["branch_values_and_fast_stats"]["integer_radialization"][
            "radial_stats"]
        radial["maximum_orbit_degree"] = 10**9
        radial["factorial_ceiling"] = 10**9+46
        original = M.math.factorial
        M.math.factorial = lambda value: (_ for _ in ()).throw(
            AssertionError("factorial evaluated before fail-fast bound"))
        try:
            with self.assertRaisesRegex(ArithmeticError,
                                        "degree/factorial ceiling"):
                M.parse_b_shard(Path("huge.json"), canonical(row), 12)
        finally:
            M.math.factorial = original

    def test_factor48_source_and_fixed_denominator_mutations_rejected(self):
        row = v6_r0_fixture()
        mutant = copy.deepcopy(row)
        mutant["scaled_b_shard"] = str(Q(mutant["scaled_b_shard"])+1)
        with self.assertRaisesRegex(ArithmeticError, "factor-48"):
            M.parse_b_shard(Path("mutant.json"), canonical(mutant), 0)
        mutant = copy.deepcopy(row)
        mutant["source_hashes"][next(iter(mutant["source_hashes"]))] = "0"*64
        with self.assertRaisesRegex(ValueError, "identity"):
            M.parse_b_shard(Path("mutant.json"), canonical(mutant), 0)
        mutant = copy.deepcopy(row)
        mutant["branch_values_and_fast_stats"]["integer_radialization"][
            "radial_denominator"] = "7"
        with self.assertRaisesRegex(ArithmeticError, "denominator"):
            M.parse_b_shard(Path("mutant.json"), canonical(mutant), 0)

    def test_base_parser_monkeypatch_restored_and_snapshots_complete(self):
        old_parser = M.B.parse_b_shard
        old_build = M.B.build
        old_publish = M.B.publish_exclusive
        seen = {}

        def fake_build(a_dir, b_dir, snapshots):
            self.assertIs(M.B.parse_b_shard, M.parse_b_shard)
            self.assertEqual(set(snapshots), set(M.PINS))
            self.assertIn(M.B.INNER_RESULT, snapshots)
            seen["called"] = True
            return {"theorem_ready_scalar": True, "source_hashes": {}}

        def fake_publish(path, payload):
            seen["payload"] = payload

        try:
            M.B.build = fake_build
            M.B.publish_exclusive = fake_publish
            with tempfile.TemporaryDirectory() as directory:
                result = M.main([
                    "--a-dir", directory, "--b-dir", directory,
                    "--output", str(Path(directory)/"out.json"),
                    "--expected-self-sha256", SOURCE_SHA])
            self.assertEqual(result, 0)
            self.assertTrue(seen["called"])
            self.assertIn(b'"b_engine":"fixed-denominator-v6"',
                          seen["payload"])
            self.assertIs(M.B.parse_b_shard, old_parser)

            def fail(*args):
                raise RuntimeError("sentinel")
            M.B.build = fail
            with tempfile.TemporaryDirectory() as directory:
                with self.assertRaisesRegex(RuntimeError, "sentinel"):
                    M.main([
                        "--a-dir", directory, "--b-dir", directory,
                        "--output", str(Path(directory)/"out.json"),
                        "--expected-self-sha256", SOURCE_SHA])
            self.assertIs(M.B.parse_b_shard, old_parser)
        finally:
            M.B.parse_b_shard = old_parser
            M.B.build = old_build
            M.B.publish_exclusive = old_publish

    def test_aggregation_scope_is_not_integration_replay(self):
        row = v6_r0_fixture()
        row["branch_values_and_fast_stats"]["high"]["Sdelta"] = str(
            Q(row["branch_values_and_fast_stats"]["high"]["Sdelta"])+1)
        high = sum(map(Q, row["branch_values_and_fast_stats"]["high"].values()))
        low = sum(map(Q, row["branch_values_and_fast_stats"]["low"].values()))
        row["scaled_b_shard"] = str(48*(high-low))
        self.assertEqual(
            M.parse_b_shard(Path("self-consistent.json"), canonical(row), 0),
            48*(high-low))


if __name__ == "__main__":
    unittest.main()
