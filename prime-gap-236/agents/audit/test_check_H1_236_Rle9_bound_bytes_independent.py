#!/usr/bin/env python3
"""Independent byte-binding tests for the frozen R<=9 standalone replay.

These tests exercise the narrow repair made after the hostile TOCTOU audit:
the exact scalar reconstruction must consume the already-audited byte
snapshots, never re-read the live shard names, and fresh aggregate hashes
must be bound to those same snapshots.
"""

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


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
SOURCE = REPO / "verify/check_H1_236_Rle9.py"
SOURCE_SHA256 = \
    "4179aeda84fef4d6712e62e7b02c0738bd277e69cb0e8d71f81de77863e324cb"


def digest(value):
    data = value if isinstance(value, bytes) else Path(value).read_bytes()
    return hashlib.sha256(data).hexdigest()


if digest(SOURCE) != SOURCE_SHA256:
    raise RuntimeError("frozen R<=9 standalone replay source changed")
_spec = importlib.util.spec_from_file_location(
    "independent_Rle9_bound_byte_target", SOURCE)
if _spec is None or _spec.loader is None:
    raise ImportError(SOURCE)
M = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = M
_spec.loader.exec_module(M)


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"),
                       ensure_ascii=True, allow_nan=False) + "\n").encode("ascii")


def make_inputs(root):
    root = Path(root)
    a_paths = [root / f"r{count:02d}.json" for count in M.A_COUNTS]
    b_paths = [root / f"common_r_{count:02d}.json"
               for count in M.B_COUNTS]
    snapshots = {}
    for count, path in enumerate(a_paths):
        data = canonical({
            "count": count,
            "exact_values": {"band_I_count": str(count + 1)},
        })
        path.write_bytes(data)
        snapshots[path] = data
    large = 10**100
    for count, path in enumerate(b_paths):
        value = large + count
        record = {"common_r": count, "scaled_b_shard": str(value)}
        if count == 9:
            record["branch_values_and_fast_stats"] = {
                "high": {"Sdelta": str(value), "Stotal": "0"},
                "low": {"Sdelta": "0", "Stotal": "0"},
            }
        data = canonical(record)
        path.write_bytes(data)
        snapshots[path] = data
    inner = {
        "exact_denominator": "2",
        "exact_numerator": "1",
        "exact_deficit": "1",
    }
    return inner, a_paths, b_paths, snapshots


def aggregate_record(reconstructed, *, bind_hashes):
    exact = reconstructed["exact"]
    hashes_a = reconstructed["a_hashes"]
    hashes_b = reconstructed["b_hashes"]
    dummy = "f" * 64
    result = {
        "format":
            "H1-236-one-band-fixed-polygon-v8-Rle9-exact-aggregate-v1",
        "status": "EXACT R<=9 ONE-BAND SCALAR CERTIFICATE PASS",
        "rigorous": True,
        "theorem_ready_scalar": True,
        "k": 48,
        "outer_direction": M.expected_outer_direction(),
        "scales": {
            "F": str(M.SCALE_F), "H": str(M.SCALE_H),
            "quadratic_inner": str(M.FORM_SCALE),
        },
        "exact": {key: str(value) for key, value in exact.items()},
        "a_shards": [],
        "zeroed_a_shards": [],
        "b_shards": [],
        "trust_scope": "synthetic exact byte-binding fixture",
        "assembler_sha256": M.ASSEMBLER_SHA256,
        "rle9_base_assembler_sha256": M.AGG.R09_ASSEMBLER_SHA256,
        "full_assembler_sha256": M.AGG.R09.FULL_ASSEMBLER_SHA256,
        "b_engine": "fixed-polygon-v8-with-Rle9-branch-projection",
        "source_hashes": {},
    }
    for count in M.KEPT_A_COUNTS:
        result["a_shards"].append({
            "count": count, "value": str(reconstructed["all_a"][count]),
            "sha256": hashes_a[count] if bind_hashes else dummy,
        })
    for count in M.ZEROED_A_COUNTS:
        result["zeroed_a_shards"].append({
            "count": count, "value": str(reconstructed["all_a"][count]),
            "sha256": hashes_a[count] if bind_hashes else dummy,
        })
    for count in M.B_COUNTS:
        result["b_shards"].append({
            "count": count,
            "value": str(reconstructed["selected_b"][count]),
            "full_shard_value": str(reconstructed["full_b"][count]),
            "selection": reconstructed["rules"][count],
            "sha256": hashes_b[count] if bind_hashes else dummy,
        })
    return result


class BoundShardByteAudit(unittest.TestCase):
    def test_reconstruction_never_rereads_mutated_live_names(self):
        with tempfile.TemporaryDirectory(prefix="Rle9-bound-byte-") as text:
            inner, a_paths, b_paths, snapshots = make_inputs(text)
            baseline = M.exact_scalar_reconstruction(
                inner, a_paths, b_paths, snapshots)

            # This is the precise hostile interleaving that defeated the
            # retired source: names change after their independent audits.
            a_paths[3].write_bytes(canonical({
                "count": 3, "exact_values": {"band_I_count": "999999"}}))
            b_paths[4].write_bytes(canonical({
                "common_r": 4, "scaled_b_shard": str(10**300)}))
            replay = M.exact_scalar_reconstruction(
                inner, a_paths, b_paths, snapshots)
            self.assertEqual(replay, baseline)
            self.assertEqual(
                replay["a_hashes"][3], digest(snapshots[a_paths[3]]))
            self.assertEqual(
                replay["b_hashes"][4], digest(snapshots[b_paths[4]]))
            self.assertNotEqual(replay["a_hashes"][3], digest(a_paths[3]))
            self.assertNotEqual(replay["b_hashes"][4], digest(b_paths[4]))

    def test_fresh_aggregate_hashes_bind_to_audited_bytes(self):
        with tempfile.TemporaryDirectory(prefix="Rle9-bind-hash-") as text:
            inner, a_paths, b_paths, snapshots = make_inputs(text)
            reconstructed = M.exact_scalar_reconstruction(
                inner, a_paths, b_paths, snapshots)
            self.assertGreater(
                reconstructed["exact"]["margin_b_squared_minus_A_D"], 0)
            certificate = aggregate_record(reconstructed, bind_hashes=False)
            aggregate = aggregate_record(reconstructed, bind_hashes=True)
            M.compare_certificate(certificate, aggregate, reconstructed)

            mutant = copy.deepcopy(aggregate)
            mutant["a_shards"][0]["sha256"] = "e" * 64
            with self.assertRaises(M.VerificationError):
                M.compare_certificate(certificate, mutant, reconstructed)
            mutant = copy.deepcopy(aggregate)
            mutant["b_shards"][9]["sha256"] = "e" * 64
            with self.assertRaises(M.VerificationError):
                M.compare_certificate(certificate, mutant, reconstructed)

    def test_snapshot_inventory_is_exact(self):
        with tempfile.TemporaryDirectory(prefix="Rle9-inventory-") as text:
            inner, a_paths, b_paths, snapshots = make_inputs(text)
            extra = Path(text) / "unreviewed.json"
            snapshots[extra] = b"{}\n"
            with self.assertRaises(M.VerificationError):
                M.exact_scalar_reconstruction(
                    inner, a_paths, b_paths, snapshots)


if __name__ == "__main__":
    unittest.main()
