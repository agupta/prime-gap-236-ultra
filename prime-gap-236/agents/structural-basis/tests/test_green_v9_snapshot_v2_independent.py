#!/usr/bin/env python3
"""Independent bounded audit of the repaired Green-polygon-v9 snapshot.

This test does not import the producer's polygon reference implementation.
It checks closed forms, the fail-closed polygon contract, every polygon made
by the frozen target geometry, the runtime substitution, and the checker's
identity-only normalization.
"""

from __future__ import annotations

from fractions import Fraction as Q
import copy
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
CORE_PATH = REPO / "agents/exact-projection-engine/green_polygon_moments.py"
CORE_TEST_PATH = REPO / (
    "agents/exact-projection-engine/test_green_polygon_moments.py")
RUNNER_PATH = REPO / (
    "agents/exact-projection-engine/d14_grid38_scaled_b_shard_green_v9.py")
CHECKER_PATH = REPO / "agents/audit/verify_green_v9_cross_shard.py"
CHECKER_TEST_PATH = REPO / "agents/audit/test_verify_green_v9_cross_shard.py"
RADIAL_PATH = REPO / "verify/exact_capped_certificate.py"
CROSS_PATH = REPO / (
    "agents/exact-projection-engine/symmetric_cutoff_cross.py")
PINS = {
    CORE_PATH:
        "019fecc00727bfdeb62fc3a02277298c6d08543db4d71ce47f049a73bc1d7a0c",
    CORE_TEST_PATH:
        "05684adf3d1bfef537718819372525e97dd72cfc24b88e0a697a269a44cd9bfe",
    RUNNER_PATH:
        "ad38951dadecdb5a5c51d1221b0a078bc9f804e9c4ec8d434706fca55a11935a",
    CHECKER_PATH:
        "7dbb352011d840a5bddf8f6f101f864d0a1b1e436ff4ebb5533ef1137217b4a7",
    CHECKER_TEST_PATH:
        "6510af2c6705bd9ad1efde5ecd802547fda93243d361e3edc6c82502a96e4c4c",
    RADIAL_PATH:
        "1787e7b482a5c2982de56486bc774794f6e671b3db4d9ab7207ebb1c85dc079c",
    CROSS_PATH:
        "d3aa9c1793a6c1d7e9ad2b71cb2d81dee690e7d9aaaea56134c428a752967726",
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(name, path):
    if digest(path) != PINS[path]:
        raise RuntimeError(f"pinned source changed: {path}")
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


for _path, _expected in PINS.items():
    if digest(_path) != _expected:
        raise RuntimeError(f"pinned source changed: {_path}")


G = load("green_v9_independent_core", CORE_PATH)
R = load("green_v9_independent_radial", RADIAL_PATH)
C = load("green_v9_independent_cross", CROSS_PATH)
RUNNER = load("green_v9_independent_runner", RUNNER_PATH)
CHECKER = load("green_v9_independent_checker", CHECKER_PATH)


def twice_area(polygon):
    return sum(
        polygon[index][0] * polygon[(index + 1) % len(polygon)][1] -
        polygon[index][1] * polygon[(index + 1) % len(polygon)][0]
        for index in range(len(polygon)))


def common_coordinate_denominator(polygon):
    answer = 1
    for point in polygon:
        for coordinate in point:
            answer = math.lcm(answer, Q(coordinate).denominator)
    return answer


class FormulaAndConvexityTest(unittest.TestCase):
    def test_closed_forms_orientation_sign_and_common_denominator(self):
        powers = {(a, b) for a in range(11) for b in range(11 - a)}
        powers.update({(80, 0), (0, 80), (39, 41)})
        simplex = ((Q(0), Q(0)), (Q(1), Q(0)), (Q(0), Q(1)))
        expected_simplex = {
            (a, b): Q(math.factorial(a) * math.factorial(b),
                      math.factorial(a + b + 2))
            for a, b in powers
        }
        self.assertEqual(
            G.polygon_monomial_batch_green(simplex, powers),
            expected_simplex)
        self.assertEqual(
            G.polygon_monomial_batch_green(tuple(reversed(simplex)), powers),
            expected_simplex)

        x0, x1 = Q(-2, 3), Q(5, 7)
        y0, y1 = Q(-3, 5), Q(4, 11)
        rectangle = ((x0, y0), (x1, y0), (x1, y1), (x0, y1))
        observed = G.polygon_monomial_batch_green(rectangle, powers)
        expected = {
            (a, b):
                (x1 ** (a + 1) - x0 ** (a + 1)) *
                (y1 ** (b + 1) - y0 ** (b + 1)) /
                ((a + 1) * (b + 1))
            for a, b in powers
        }
        self.assertEqual(observed, expected)
        maximum = max(a + b for a, b in powers)
        scale = common_coordinate_denominator(rectangle)
        proved_denominator = (
            scale ** (maximum + 2) *
            math.factorial(maximum + 2) ** 2)
        for value in observed.values():
            self.assertEqual(proved_denominator % value.denominator, 0)

    def test_zero_area_repair_and_global_supporting_halfplane_gate(self):
        powers = {(0, 0), (1, 0), (0, 1), (2, 3)}
        # Every nonzero local turn is positive, but the signed boundary area
        # vanishes.  The superseded snapshot incorrectly returned all zeros.
        zero_area_nonconvex = (
            (Q(5), Q(-2)), (Q(2), Q(1)), (Q(-2), Q(-3)),
            (Q(0), Q(-4)), (Q(-4), Q(4)), (Q(-5), Q(3)))
        self.assertEqual(twice_area(zero_area_nonconvex), 0)
        with self.assertRaisesRegex(ValueError, "noncollinear.*zero"):
            G.polygon_monomial_batch_green(zero_area_nonconvex, powers)

        # This separate positive-area cyclic walk has only positive nonzero
        # local turns, yet one edge is traversed backwards.  Only the global
        # supporting-half-plane check rejects it.
        positive_area_nonconvex = (
            (Q(-2), Q(-2)), (Q(-2), Q(0)), (Q(-2), Q(-1)),
            (Q(-1), Q(-2)), (Q(-2), Q(1)))
        self.assertGreater(twice_area(positive_area_nonconvex), 0)
        with self.assertRaisesRegex(ValueError, "supporting half-plane"):
            G.polygon_monomial_batch_green(positive_area_nonconvex, powers)

        collinear = ((Q(0), Q(0)), (Q(3), Q(3)), (Q(1), Q(1)))
        self.assertEqual(
            G.polygon_monomial_batch_green(collinear, powers),
            {power: Q(0) for power in powers})

    def test_global_convex_gate_on_every_frozen_target_polygon(self):
        delta = Q(1, 60)
        alpha_low = Q(103, 400)
        alpha_high = Q(9500917, 36000000)
        eta = Q(8960917, 36000000)
        schedule = tuple(map(Q, (
            "1123/8000", "157041/1000000", "5267/31250",
            "87169/500000", "11593/62500", "1523/8000",
            "193097/1000000", "98573/500000", "202047/1000000",
            "20709/100000", "52917/250000", "52917/250000")))
        polygons = []
        empty = 0
        sizes = {}
        for common_r in range(1, 13):
            for alpha in (alpha_low, alpha_high):
                jobs = C.scheduled_cross_branch_jobs(
                    R, k=48, alpha=alpha, eta=eta, delta=delta,
                    schedule=schedule, common_r=common_r)
                for _branch, _family, domain, _affine in jobs:
                    for shift_count in range(15 - common_r):
                        shift = shift_count * delta
                        total = domain.total_bound - shift
                        if total <= 0:
                            continue
                        polygon = tuple(R._shifted_polygon(
                            total, domain.x_bound,
                            None if domain.y_lower is None else
                                domain.y_lower - shift,
                            None if domain.y_upper is None else
                                domain.y_upper - shift,
                            None if domain.total_lower is None else
                                domain.total_lower - shift))
                        polygons.append(polygon)
                        if len(polygon) < 3:
                            empty += 1
                            continue
                        sizes[len(polygon)] = sizes.get(len(polygon), 0) + 1
                        scaled, _denominator = G._scaled_vertices(polygon)
                        self.assertEqual(G._orientation(scaled), 1)
                        area2 = twice_area(polygon)
                        self.assertGreater(area2, 0)
                        for index, first in enumerate(polygon):
                            second = polygon[(index + 1) % len(polygon)]
                            dx = second[0] - first[0]
                            dy = second[1] - first[1]
                            for point in polygon:
                                self.assertGreaterEqual(
                                    dx * (point[1] - first[1]) -
                                    dy * (point[0] - first[0]), 0)
                        self.assertEqual(
                            G.polygon_monomial_batch_green(
                                polygon, {(0, 0)})[(0, 0)],
                            area2 / 2)
        self.assertEqual(len(polygons), 804)
        self.assertEqual(len(set(polygons)), 438)
        self.assertEqual(empty, 93)
        self.assertEqual(sizes, {3: 305, 4: 401, 5: 5})


class WiringAndCheckerTest(unittest.TestCase):
    def test_recursive_source_closure_and_runtime_radial_substitution(self):
        original_load = RUNNER.load
        evidence = {}

        def intercepted_load(name, path, data):
            module = original_load(name, path, data)
            if name == "d14_grid38_green_v9_v2":
                def probe_build(_common_r, _local, dependencies, base,
                                _cached_v7, **_kwargs):
                    radial = base.import_snapshot(
                        "green_v9_probe_radial", base.RADIAL,
                        dependencies[base.RADIAL])
                    expected = sys.modules[
                        "d14_grid38_green_v9_moments"
                    ].polygon_monomial_batch_green
                    evidence["patched"] = (
                        radial._polygon_monomial_batch is expected)
                    evidence["radial_path"] = str(
                        base.RADIAL.relative_to(REPO))
                    evidence["dependency_count"] = len(dependencies)
                    source_hashes = {
                        str(path.relative_to(REPO)): expected
                        for path, expected in {
                            **base.PINNED, **module.LOCAL_PINNED}.items()
                    }
                    return {"source_hashes": source_hashes}
                module.build = probe_build
            return module

        with tempfile.TemporaryDirectory(prefix="green-v9-wiring-") as root:
            output = Path(root) / "probe.json"
            argv = [
                str(RUNNER_PATH), "--common-r", "9", "--output", str(output),
                "--expected-self-sha256", PINS[RUNNER_PATH],
            ]
            with mock.patch.object(
                    RUNNER, "load", side_effect=intercepted_load), \
                    mock.patch.object(sys, "argv", argv):
                RUNNER.main()
            raw = json.loads(output.read_bytes())
        self.assertTrue(evidence["patched"])
        self.assertEqual(evidence["radial_path"],
                         "verify/exact_capped_certificate.py")
        self.assertGreater(evidence["dependency_count"], 5)
        self.assertEqual(raw["producer_sha256"], PINS[RUNNER_PATH])
        self.assertEqual(
            raw["format"],
            "D14-grid38-scaled-cutoff-cross-common-r-green-v9")
        self.assertEqual(raw["source_hashes"], CHECKER.SOURCE_HASHES)
        self.assertEqual(raw["algorithm"], CHECKER.ALGORITHM)
        self.assertTrue(raw["algorithm"][
            "polygon_runtime_module_patched_after_pinned_load"])
        for path, expected in RUNNER.LOCAL_PINNED.items():
            self.assertEqual(digest(path), expected)

    def test_checker_normalization_changes_only_identity_fields(self):
        raw = {
            "format": "D14-grid38-scaled-cutoff-cross-common-r-green-v9",
            "status": "EXACT GREEN-POLYGON COMMON-r CROSS SHARD PASS",
            "producer_sha256": CHECKER.PRODUCER_SHA,
            "source_hashes": copy.deepcopy(CHECKER.SOURCE_HASHES),
            "algorithm": copy.deepcopy(CHECKER.ALGORITHM),
            "scaled_b_shard": "123/456",
            "common_r": 9,
            "branch_values_and_fast_stats": {
                "high": "7/11", "low": "5/13",
                "nested": [1, {"unchanged": True}]},
        }
        before = copy.deepcopy(raw)
        normalized = CHECKER.normalized_v8(raw)
        identity = {
            "format", "status", "producer_sha256", "source_hashes",
            "algorithm"}
        self.assertEqual(
            {key for key in raw if raw[key] != normalized[key]}, identity)
        self.assertEqual(raw, before)
        for key in set(raw) - identity:
            self.assertEqual(normalized[key], raw[key])
        self.assertEqual(normalized["producer_sha256"],
                         CHECKER.V8.PRODUCER_SHA)
        self.assertEqual(normalized["source_hashes"],
                         CHECKER.V8.SOURCE_HASHES)
        self.assertEqual(normalized["algorithm"], CHECKER.V8.ALGORITHM)


if __name__ == "__main__":
    unittest.main()
