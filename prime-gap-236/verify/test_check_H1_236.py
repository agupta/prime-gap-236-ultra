#!/usr/bin/env python3
"""Fast arithmetic/parser tests for the full H_1<=236 replay driver."""

from __future__ import annotations

from fractions import Fraction as Q
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


HERE = Path(__file__).resolve().parent
SOURCE = HERE / "check_H1_236.py"


def load_source():
    spec = importlib.util.spec_from_file_location("check_H1_236_test", SOURCE)
    if spec is None or spec.loader is None:
        raise ImportError(SOURCE)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


M = load_source()


def write_json(path, value):
    path.write_text(json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n")


def certificate_object(exact, a_values, b_values):
    return {
        "format": "H1-236-one-band-cached-v7-exact-shard-aggregate-v1",
        "status": "EXACT ONE-BAND SCALAR CERTIFICATE PASS",
        "rigorous": True, "theorem_ready_scalar": True, "k": 48,
        "counts": list(M.COUNTS),
        "scales": {"F": str(M.SCALE_F), "H": str(M.SCALE_H),
                   "quadratic_inner": str(M.FORM_SCALE)},
        "exact": {key: str(value) for key, value in exact.items()},
        "a_shards": [{"count": i, "value": str(value), "sha256": "0" * 64}
                     for i, value in enumerate(a_values)],
        "b_shards": [{"count": i, "value": str(value), "sha256": "0" * 64}
                     for i, value in enumerate(b_values)],
        "source_hashes": {}, "trust_scope": "test",
        "assembler_sha256": M.PINS[M.ASSEMBLER],
        "base_assembler_sha256": M.BASE_ASSEMBLER_SHA256,
        "b_engine": "cached-fixed-v7",
    }


class FullReplayDriverTest(unittest.TestCase):
    def test_exact_projection_arithmetic_and_certificate_comparison(self):
        inner = {
            "exact_denominator": "10", "exact_numerator": "8",
            "exact_deficit": "2",
        }
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            a_paths, b_paths = [], []
            for count in M.COUNTS:
                a_path, b_path = root / f"a{count}.json", root / f"b{count}.json"
                write_json(a_path, {
                    "count": count,
                    "exact_values": {"band_I_count": str(count + 1)}})
                write_json(b_path, {"common_r": count, "scaled_b_shard": "100000000000"})
                a_paths.append(a_path)
                b_paths.append(b_path)
            (exact, a_values, b_values, fresh_a_hashes,
             fresh_b_hashes) = M.exact_scalar_reconstruction(
                inner, a_paths, b_paths)
        self.assertEqual(exact["A_scaled"], sum(range(1, 14)))
        self.assertEqual(exact["b_scaled"], 13 * 10**11)
        self.assertEqual(exact["I_F_scaled"], 10 * M.FORM_SCALE)
        self.assertEqual(exact["D_scaled"], 2 * M.FORM_SCALE)
        # The synthetic b is far too small against 10^174, so replace only
        # this test's b values by a deliberately large exact value.
        big = 10**100
        b_values = [Q(big)] * 13
        b_total = 13 * big
        a_total = exact["A_scaled"]
        i_value, d_value = exact["I_F_scaled"], exact["D_scaled"]
        margin = b_total**2 - a_total * d_value
        denominator = a_total * i_value + b_total**2
        exact = {
            "A_scaled": a_total, "b_scaled": Q(b_total),
            "I_F_scaled": i_value, "D_scaled": d_value,
            "margin_b_squared_minus_A_D": margin,
            "mixing_coefficient_b_over_A": Q(b_total, a_total),
            "normalized_inner_deficit": d_value / i_value,
            "normalized_projected_energy": Q(b_total**2, a_total * i_value),
            "quotient_margin_lower_bound": Q(margin, denominator),
            "quotient_lower_bound": Q(1) + Q(margin, denominator),
        }
        certificate = certificate_object(exact, a_values, b_values)
        aggregate = json.loads(json.dumps(certificate))
        for count in M.COUNTS:
            aggregate["a_shards"][count]["sha256"] = fresh_a_hashes[count]
            aggregate["b_shards"][count]["sha256"] = fresh_b_hashes[count]
        M.compare_certificate(certificate, aggregate, exact, a_values, b_values,
                              fresh_a_hashes, fresh_b_hashes)
        certificate["exact"]["margin_b_squared_minus_A_D"] = str(margin + 1)
        with self.assertRaises(M.VerificationError):
            M.compare_certificate(certificate, aggregate, exact, a_values,
                                  b_values, fresh_a_hashes, fresh_b_hashes)

    def test_shard_hashes_are_fail_closed_and_fresh_aggregate_is_bound(self):
        exact = {
            "margin_b_squared_minus_A_D": Q(1),
            "quotient_lower_bound": Q(2),
        }
        a_values, b_values = [Q(1)] * 13, [Q(1)] * 13
        hashes = [f"{count:064x}" for count in M.COUNTS]
        certificate = certificate_object(exact, a_values, b_values)
        aggregate = json.loads(json.dumps(certificate))
        for count in M.COUNTS:
            aggregate["a_shards"][count]["sha256"] = hashes[count]
            aggregate["b_shards"][count]["sha256"] = hashes[count]
        M.compare_certificate(certificate, aggregate, exact, a_values, b_values,
                              hashes, hashes)

        malformed = json.loads(json.dumps(certificate))
        malformed["a_shards"][0]["sha256"] = "NOT-A-SHA"
        with self.assertRaises(M.VerificationError):
            M.compare_certificate(malformed, aggregate, exact, a_values,
                                  b_values, hashes, hashes)
        malformed = json.loads(json.dumps(certificate))
        malformed["b_shards"][0]["sha256"] = None
        with self.assertRaises(M.VerificationError):
            M.compare_certificate(malformed, aggregate, exact, a_values,
                                  b_values, hashes, hashes)
        wrong_aggregate = json.loads(json.dumps(aggregate))
        wrong_aggregate["a_shards"][0]["sha256"] = "f" * 64
        with self.assertRaises(M.VerificationError):
            M.compare_certificate(certificate, wrong_aggregate, exact,
                                  a_values, b_values, hashes, hashes)

        for impostor in (False, 0.0):
            malformed = json.loads(json.dumps(certificate))
            malformed["a_shards"][0]["count"] = impostor
            with self.assertRaises(M.VerificationError):
                M.compare_certificate(malformed, aggregate, exact, a_values,
                                      b_values, hashes, hashes)

    def test_integer_metadata_rejects_bool_and_float_aliases(self):
        exact = {
            "margin_b_squared_minus_A_D": Q(1),
            "quotient_lower_bound": Q(2),
        }
        values = [Q(1)] * 13
        hashes = ["0" * 64] * 13
        for field, impostor in (("k", 48.0), ("k", True)):
            certificate = certificate_object(exact, values, values)
            aggregate = json.loads(json.dumps(certificate))
            certificate[field] = impostor
            aggregate[field] = impostor
            with self.assertRaises(M.VerificationError):
                M.compare_certificate(certificate, aggregate, exact, values,
                                      values, hashes, hashes)
        for impostor in (0.0, False):
            certificate = certificate_object(exact, values, values)
            aggregate = json.loads(json.dumps(certificate))
            certificate["counts"][0] = impostor
            aggregate["counts"][0] = impostor
            with self.assertRaises(M.VerificationError):
                M.compare_certificate(certificate, aggregate, exact, values,
                                      values, hashes, hashes)

    def test_strict_json_and_rational_wire(self):
        with self.assertRaises(M.VerificationError):
            M.strict_loads(b'{"x":1,"x":2}', "duplicate")
        with self.assertRaises(M.VerificationError):
            M.rational("2/4", "bad")
        self.assertEqual(M.rational("-3/5", "good"), Q(-3, 5))

    def test_support_projection_ignores_only_host_identity(self):
        source_bytes = {
            M.REPO / relative: (M.REPO / relative).read_bytes()
            for relative in M.SUPPORT_SNAPSHOT_PINS}
        frozen, _ = M.canonical_object(M.SUPPORT_FROZEN)
        altered = json.loads(json.dumps(frozen))
        for row in altered["snapshots"].values():
            row["dev"] += 17
            row["inode"] += 31
        expected = M.deterministic_support_projection(
            frozen, "frozen", source_bytes)
        observed = M.deterministic_support_projection(
            altered, "altered", source_bytes)
        self.assertEqual(expected, observed)
        altered["snapshots"][next(iter(altered["snapshots"]))]["size"] += 1
        with self.assertRaises(M.VerificationError):
            M.deterministic_support_projection(
                altered, "bad-size", source_bytes)

    def test_only_exact_v7_progress_shape_is_allowed(self):
        good = (
            b"fast-v2 kernel r=12 {'x': 1} seconds=9.229\n"
            b"fast-v2 families r=12 {'y': 2} seconds=86.879\n"
            b"fast-v2 done r=12 seconds=1234.567\n")
        self.assertTrue(M.validate_b_progress(good, 12))
        self.assertFalse(M.validate_b_progress(good + b"warning\n", 12))
        self.assertFalse(M.validate_b_progress(good.replace(b"r=12", b"r=11"), 12))
        self.assertFalse(M.validate_b_progress(b"", 12))

    def test_child_python_uses_fresh_command_line_bytecode_barrier(self):
        with tempfile.TemporaryDirectory() as temporary:
            prefix_path = Path(temporary) / "must-remain-empty"
            command = M.python_prefix(prefix_path) + [
                "-c", "import json,sys;print(json.dumps({"
                "'dont':sys.dont_write_bytecode,"
                "'ignore':sys.flags.ignore_environment,"
                "'prefix':sys.pycache_prefix}))"]
            completed = subprocess.run(
                command, check=True, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, text=True)
            flags = json.loads(completed.stdout)
            self.assertIs(flags["dont"], True)
            self.assertEqual(flags["ignore"], 1)
            self.assertEqual(flags["prefix"], str(prefix_path.resolve()))
            self.assertFalse(prefix_path.exists())

    def test_missing_or_duplicate_shard_counts_fail(self):
        exact = {
            "margin_b_squared_minus_A_D": Q(1),
            "quotient_lower_bound": Q(2),
        }
        base = certificate_object(exact, [Q(1)] * 13, [Q(1)] * 13)
        base["a_shards"][-1]["count"] = 11
        with self.assertRaises(M.VerificationError):
            M.compare_certificate(base, dict(base), exact,
                                  [Q(1)] * 13, [Q(1)] * 13,
                                  ["0" * 64] * 13, ["0" * 64] * 13)


if __name__ == "__main__":
    unittest.main()
