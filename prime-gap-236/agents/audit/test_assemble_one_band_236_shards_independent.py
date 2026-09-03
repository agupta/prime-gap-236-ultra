#!/usr/bin/env python3
"""Independent hostile tests for the frozen one-band scalar assembler.

This deliberately does not import either shard producer.  It treats the
assembler as a cheap exact aggregator and separately demonstrates that its
parsers are *not* an integration replay.
"""

from __future__ import annotations

from fractions import Fraction as Q
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
SOURCE = REPO / "verify/assemble_one_band_236_shards.py"
EXPECTED_SOURCE_SHA256 = (
    "9963c94207ab4954ea235fe9c044fe240df2f74c8df5abe83e32467600648374")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_source():
    data = SOURCE.read_bytes()
    if sha256(data) != EXPECTED_SOURCE_SHA256:
        raise RuntimeError("assembler is not the frozen audited snapshot")
    spec = importlib.util.spec_from_file_location(
        "one_band_236_assembler_independent_audit", SOURCE)
    if spec is None or spec.loader is None:
        raise ImportError(SOURCE)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


M = load_source()


def payload(row) -> bytes:
    return (json.dumps(row, sort_keys=True, separators=(",", ":"),
                       ensure_ascii=True, allow_nan=False) + "\n").encode("ascii")


def literal_branch_inventory(alpha: Q, r: int) -> set[str]:
    """Non-production transcription of the four nonempty face domains.

    The common-coordinate total has remaining allowance eta-r*delta.  A
    distinguished small coordinate has the shared r-cap (unless r=0), while
    a distinguished large coordinate has the (r+1)-cap.  Strict versus weak
    endpoints cannot change these polynomial integrals.
    """
    remaining = Q(8960917, 36000000) - r * Q(1, 60)
    if remaining <= 0:
        return set()
    schedule = tuple(map(Q, (
        "1123/8000", "157041/1000000", "5267/31250",
        "87169/500000", "11593/62500", "1523/8000",
        "193097/1000000", "98573/500000", "202047/1000000",
        "20709/100000", "52917/250000", "52917/250000")))

    def cap(index: int) -> Q:
        return schedule[min(index, len(schedule)) - 1]

    small_cap = None if r == 0 else cap(r) - r * Q(1, 60)
    small_total = min(remaining, alpha - (r + 1) * Q(1, 60))
    result = set()
    if (small_cap is None or small_cap > 0) and small_total > 0:
        result.add("Sdelta")
    if ((small_cap is None or small_cap > 0)
            and remaining > alpha - (r + 1) * Q(1, 60)):
        result.add("Stotal")
    large_cap = cap(r + 1) - (r + 1) * Q(1, 60)
    if large_cap > 0:
        if small_total > 0:
            result.add("Ltotal")
        result.add("Lbig")
    return result


class IndependentAssemblerAudit(unittest.TestCase):
    def test_frozen_source_and_transitive_live_pins(self):
        self.assertEqual(sha256(SOURCE.read_bytes()), EXPECTED_SOURCE_SHA256)
        self.assertEqual(len(M.PINNED), 30)
        for path, expected in M.PINNED.items():
            self.assertEqual(sha256(path.read_bytes()), expected, str(path))

    def test_definition5_branch_inventory_all_counts_and_endpoints(self):
        for r in range(13):
            for alpha in (Q(103, 400), Q(9500917, 36000000)):
                self.assertEqual(M.expected_branches(alpha, r),
                                 literal_branch_inventory(alpha, r))
        # All four branches survive through r=11; the distinguished-large
        # cap is empty at r=12, leaving exactly the two small branches.
        self.assertEqual(literal_branch_inventory(Q(103, 400), 11),
                         {"Sdelta", "Stotal", "Ltotal", "Lbig"})
        self.assertEqual(literal_branch_inventory(Q(103, 400), 12),
                         {"Sdelta", "Stotal"})

    def test_all_real_a_shards_recombine_to_independently_audited_total(self):
        total = Q(0)
        for r in range(13):
            path = M.DEFAULT_A_DIR / f"r{r:02d}.json"
            total += M.parse_a_shard(path, path.read_bytes(), r)
        audited = json.loads((
            REPO / "agents/audit/results/"
            "d14_one_band_a_aggregate_v2_strict_audit.json").read_text())
        strict = json.loads((
            REPO / "agents/structural-basis/results/"
            "d14_one_band_a_aggregate_exact_v2_strict.json").read_text())
        self.assertTrue(audited["all_13_independent_radial_replays_equal"])
        self.assertEqual(total, Q(audited["exact_A_scaled"]))
        self.assertEqual(total, Q(strict["exact_A_scaled"]))

    def test_real_v5_r0_matches_independent_result_audit(self):
        path = M.DEFAULT_B_DIR / "common_r_00.json"
        observed = M.parse_b_shard(path, path.read_bytes(), 0)
        audit = json.loads((
            REPO / "agents/audit/results/"
            "d14_grid38_scaled_b_collected_v5/common_r_00.audit.json").read_text())
        self.assertEqual(sha256(path.read_bytes()), audit["input_sha256"])
        self.assertTrue(audit["reference_mathematical_fields_bit_equal"])
        self.assertEqual(observed, Q(audit["scaled_b_shard"]))
        self.assertEqual(
            json.loads(path.read_text())["branch_values_and_fast_stats"]
            ["integer_radialization"]["radial_stats"]
            ["maximum_shift_pruned_inside_convolution"], 14)

    def test_core_b_mutations_fail_closed(self):
        path = M.DEFAULT_B_DIR / "common_r_00.json"
        original = json.loads(path.read_text())

        row = json.loads(json.dumps(original))
        row["geometry"]["schedule"][0] = "1/7"
        with self.assertRaisesRegex(ValueError, "scale/geometry"):
            M.parse_b_shard(Path("mutated.json"), payload(row), 0)

        row = json.loads(json.dumps(original))
        row["source_hashes"][next(iter(row["source_hashes"]))] = "0" * 64
        with self.assertRaisesRegex(ValueError, "source closure"):
            M.parse_b_shard(Path("mutated.json"), payload(row), 0)

        row = json.loads(json.dumps(original))
        row["scaled_b_shard"] = str(Q(row["scaled_b_shard"]) + 1)
        with self.assertRaisesRegex(ArithmeticError, "recombination"):
            M.parse_b_shard(Path("mutated.json"), payload(row), 0)

        row = json.loads(json.dumps(original))
        del row["branch_values_and_fast_stats"]["high"]["Lbig"]
        with self.assertRaisesRegex(ValueError, "branch inventory"):
            M.parse_b_shard(Path("mutated.json"), payload(row), 0)

    def test_core_a_mutations_fail_closed(self):
        path = M.DEFAULT_A_DIR / "r00.json"
        original = json.loads(path.read_text())

        row = json.loads(json.dumps(original))
        row["geometry"]["eta"] = "1/4"
        with self.assertRaisesRegex(ValueError, "geometry"):
            M.parse_a_shard(Path("mutated.json"), payload(row), 0)

        row = json.loads(json.dumps(original))
        row["exact_values"]["band_I_count"] = str(
            Q(row["exact_values"]["band_I_count"]) + 1)
        with self.assertRaisesRegex(ArithmeticError, "arithmetic"):
            M.parse_a_shard(Path("mutated.json"), payload(row), 0)

        row = json.loads(json.dumps(original))
        row["source_hashes"][next(iter(row["source_hashes"]))] = "f" * 64
        with self.assertRaisesRegex(ValueError, "identity"):
            M.parse_a_shard(Path("mutated.json"), payload(row), 0)

    def test_exact_projection_algebra_independently(self):
        # If I(F,H)=0, A=I(H), b=48J(F,H), D=I(F)-48J(F), then
        # t=b/A maximizes -D+2tb-t^2 A.  Check both the positivity test and
        # the reported quotient formula over unrelated exact examples.
        samples = (
            (Q(7, 3), Q(2, 5), Q(11, 7)),
            (Q(13, 8), Q(3, 17), Q(-5, 9)),
            (Q(101, 37), Q(1, 1000), Q(19, 23)),
        )
        for inner_i, deficit, b in samples:
            a = Q(29, 31)
            t = b / a
            denominator = inner_i + t * t * a
            numerator = inner_i - deficit + 2 * t * b
            margin = b * b - a * deficit
            self.assertEqual(numerator / denominator - 1,
                             margin / (a * inner_i + b * b))
            self.assertEqual(numerator > denominator, margin > 0)

    def test_parser_is_not_an_integration_replay(self):
        # A self-consistent change to serialized branch values is accepted.
        # This is expected for this cheap aggregation layer and is why a PASS
        # here must never be cited as reconstruction of the integrals.
        path = M.DEFAULT_B_DIR / "common_r_00.json"
        row = json.loads(path.read_text())
        row["branch_values_and_fast_stats"]["high"]["Sdelta"] = str(
            Q(row["branch_values_and_fast_stats"]["high"]["Sdelta"]) + 1)
        high = sum(map(Q, row["branch_values_and_fast_stats"]["high"].values()))
        low = sum(map(Q, row["branch_values_and_fast_stats"]["low"].values()))
        row["scaled_b_shard"] = str(48 * (high - low))
        self.assertEqual(M.parse_b_shard(Path("self-consistent.json"),
                                         payload(row), 0), 48 * (high - low))


if __name__ == "__main__":
    unittest.main()
