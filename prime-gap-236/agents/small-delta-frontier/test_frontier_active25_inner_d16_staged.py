#!/usr/bin/env python3

from __future__ import annotations

from fractions import Fraction as Q
import importlib.util
from pathlib import Path
import sys
import unittest


FILE = Path(__file__).resolve()
SOURCE = FILE.with_name("frontier_active25_inner_d16_staged.py")
SPEC = importlib.util.spec_from_file_location("active25_staged", SOURCE)
M = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = M
SPEC.loader.exec_module(M)


def fake_shard(r, value=Q(1)):
    vector = [Q(0)] * (M.core.K + 1)
    vector[r] = value
    vector[r + 1] = -value / 2
    return {
        "common_r": r,
        "complete_common_r": True,
        "domain_counts": {"rh": 1, "rl": 1, "vh": 1, "vl": 1},
        "faces": 1,
        "geometric_group_count": 1,
        "inner_48J": "7/5",
        "inner_I": "3/2",
        "inner_basis_dimension": 307,
        "nonzero_group_count": 1,
        "raw_J_cross_by_target_R": [str(x) for x in vector],
    }


class StagedTests(unittest.TestCase):
    def test_frozen_disabled_gate_and_preflight(self):
        self.assertTrue(M.snapshots())
        gate = M.load_gate()
        self.assertIs(gate["launch_authorized"], False)
        with self.assertRaises(RuntimeError):
            M.require_authorized()
        preflight = M.preflight()
        self.assertEqual(preflight["active_common_r"], list(range(26)))
        self.assertEqual(preflight["dimension"], 27)
        self.assertIs(preflight["launch_authorized"], False)

    def test_pluggable_inner_loader_contract(self):
        def loader():
            return (((0, ()),), (Q(2),), (Q(1), Q(3, 4)),
                    Q(5, 7), Q(11, 13))

        named, catalog, weights, inner_i, inner_b, dimension = \
            M.production_inputs(loader)
        self.assertEqual(set(named), {"R", "V", "H", "L"})
        self.assertEqual(tuple(tag for tag, _, _ in catalog),
                         ("rh", "rl", "vh", "vl"))
        self.assertEqual(weights, {"rh": Q(3, 4), "rl": Q(-3, 4),
                                   "vh": Q(1, 4), "vl": Q(-1, 4)})
        self.assertEqual((inner_i, inner_b, dimension),
                         (Q(5, 7), Q(11, 13), 1))

    def test_deterministic_exact_merge_forward_reverse(self):
        shards = [fake_shard(r, Q(r + 1)) for r in range(26)]
        forward, identity = M.merge_exact_shards(shards)
        reverse, identity_reverse = M.merge_exact_shards(list(reversed(shards)))
        self.assertEqual(forward, reverse)
        self.assertEqual(identity, identity_reverse)
        expected = [Q(0)] * (M.core.K + 1)
        for r in range(26):
            expected[r] += r + 1
            expected[r + 1] -= Q(r + 1, 2)
        self.assertEqual(forward, expected)

    def test_low_k_actual_common_r_shards_equal_full(self):
        k = 3
        delta = Q(1, 10)
        alpha = Q(2, 5)
        eta = Q(3, 10)
        support = M.core.shell.ScheduledStratumSupport.make(
            k, alpha, eta, delta, (alpha,) * k)
        components = M.core.outer_core.components(
            ((0, ()), (1, ())), (Q(2), Q(-3)), k)
        one = (((), 0, 0, Q(1)),)
        named = {"P": (support, components), "C": (support, one)}
        catalog = (("pc", "P", "C"),)
        weights = {"pc": Q(7, 11)}
        full, _, _, _, _ = M.core.grouped_weighted_cross(
            named, catalog, weights, eta, direct_full_left=("P",))
        pieces = []
        for r in range(k):
            piece, _, _, _, _ = M.core.grouped_weighted_cross(
                named, catalog, weights, eta, common_strata=(r,),
                direct_full_left=("P",))
            pieces.append(piece)
        forward = [sum((piece[i] for piece in pieces), Q(0))
                   for i in range(k + 1)]
        reverse = [sum((piece[i] for piece in reversed(pieces)), Q(0))
                   for i in range(k + 1)]
        self.assertEqual(forward, full)
        self.assertEqual(reverse, full)

    def test_merge_fails_closed(self):
        shards = [fake_shard(r) for r in range(26)]
        with self.assertRaises(ValueError):
            M.merge_exact_shards(shards[:-1])
        with self.assertRaises(ValueError):
            M.merge_exact_shards(shards + [fake_shard(0)])
        bad = [dict(x) for x in shards]
        escaped = list(bad[3]["raw_J_cross_by_target_R"])
        escaped[10] = "1"
        bad[3]["raw_J_cross_by_target_R"] = escaped
        with self.assertRaises(ValueError):
            M.merge_exact_shards(bad)
        bad = [dict(x) for x in shards]
        bad[4]["inner_I"] = "4/3"
        with self.assertRaises(ValueError):
            M.merge_exact_shards(bad)

    def test_strict_boolean_and_schema_rejection(self):
        shard = fake_shard(0)
        shard["common_r"] = False
        with self.assertRaises(ValueError):
            M.strict_shard(shard)
        shard = fake_shard(0)
        shard["extra"] = 1
        with self.assertRaises(ValueError):
            M.strict_shard(shard)
        shard = fake_shard(0)
        shard["inner_I"] = "6/4"
        with self.assertRaises(ValueError):
            M.strict_shard(shard)
        shard = fake_shard(0)
        shard["domain_counts"] = dict(shard["domain_counts"], rh=False)
        with self.assertRaises(ValueError):
            M.strict_shard(shard)


if __name__ == "__main__":
    unittest.main()
