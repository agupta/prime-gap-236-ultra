#!/usr/bin/env python3
"""Independent exact/core/runtime tests for the repaired Green-v9 bundle."""

from __future__ import annotations

import copy
from fractions import Fraction as Q
import hashlib
import importlib.util
import itertools
import json
import math
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
GREEN_PATH = REPO / "agents/exact-projection-engine/green_polygon_moments.py"
FIXED_PATH = REPO / "agents/exact-projection-engine/fixed_polygon_moments.py"
RADIAL_PATH = REPO / "verify/exact_capped_certificate.py"
CROSS_PATH = REPO / "agents/exact-projection-engine/symmetric_cutoff_cross.py"
FAST_PATH = REPO / "agents/exact-projection-engine/fast_tagged_scalar.py"
RUNNER_PATH = REPO / (
    "agents/exact-projection-engine/d14_grid38_scaled_b_shard_green_v9.py")
PINS = {
    GREEN_PATH:
        "019fecc00727bfdeb62fc3a02277298c6d08543db4d71ce47f049a73bc1d7a0c",
    FIXED_PATH:
        "4100a9eeb86563ae84bf02ed4df9a2a5b696b5cc9ff163d15ac482b242b637bb",
    RADIAL_PATH:
        "1787e7b482a5c2982de56486bc774794f6e671b3db4d9ab7207ebb1c85dc079c",
    CROSS_PATH:
        "d3aa9c1793a6c1d7e9ad2b71cb2d81dee690e7d9aaaea56134c428a752967726",
    FAST_PATH:
        "5d9d82ae7b097a40b852a8471e281d5bd5ad69d08240e1a73d3928e21a40aaa2",
    RUNNER_PATH:
        "ad38951dadecdb5a5c51d1221b0a078bc9f804e9c4ec8d434706fca55a11935a",
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(name, path):
    if path in PINS and digest(path) != PINS[path]:
        raise RuntimeError(f"pinned audit input changed: {path}")
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


G = load("independent_green_v9_core", GREEN_PATH)
T = load("independent_green_v9_triangle_oracle", FIXED_PATH)
R = load("independent_green_v9_radial", RADIAL_PATH)
C = load("independent_green_v9_cross", CROSS_PATH)
F = load("independent_green_v9_fast", FAST_PATH)
V9 = load("independent_green_v9_runner", RUNNER_PATH)


def twice_area(polygon):
    return sum(
        polygon[i][0] * polygon[(i + 1) % len(polygon)][1] -
        polygon[i][1] * polygon[(i + 1) % len(polygon)][0]
        for i in range(len(polygon)))


def common_coordinate_denominator(polygon):
    answer = 1
    for point in polygon:
        for coordinate in point:
            answer = math.lcm(answer, Q(coordinate).denominator)
    return answer


class GreenV9CoreAudit(unittest.TestCase):
    def check_against_triangle_oracle(self, polygon, powers):
        observed = G.polygon_monomial_batch_green(polygon, powers)
        expected = T.polygon_monomial_batch_fixed(polygon, powers)
        self.assertEqual(observed, expected)
        if powers and len(polygon) >= 3 and twice_area(polygon):
            degree = max(a + b for a, b in powers)
            scale = common_coordinate_denominator(polygon)
            clearing = (scale ** (degree + 2) *
                        math.factorial(degree + 2) ** 2)
            for value in observed.values():
                self.assertEqual(clearing % value.denominator, 0)

    def test_closed_forms_orientation_collinearity_and_fail_close(self):
        powers = {(0, 0), (1, 0), (0, 1), (2, 3),
                  (80, 0), (0, 80), (39, 41)}
        simplex = ((Q(0), Q(0)), (Q(1), Q(0)), (Q(0), Q(1)))
        for polygon in (simplex, tuple(reversed(simplex)),
                        simplex[1:] + simplex[:1]):
            self.check_against_triangle_oracle(polygon, powers)
        observed = G.polygon_monomial_batch_green(simplex, powers)
        for (a, b), value in observed.items():
            self.assertEqual(
                value, Q(math.factorial(a) * math.factorial(b),
                         math.factorial(a + b + 2)))

        collinear_edge = ((Q(0), Q(0)), (Q(1), Q(0)), (Q(2), Q(0)),
                          (Q(2), Q(1)), (Q(0), Q(1)))
        self.check_against_triangle_oracle(collinear_edge, powers)
        self.check_against_triangle_oracle(tuple(reversed(collinear_edge)), powers)

        repeated = simplex + simplex
        hull = ((Q(0), Q(0)), (Q(2), Q(0)), (Q(3), Q(1)),
                (Q(1), Q(3)), (Q(-1), Q(1)))
        star = tuple(hull[i] for i in (0, 2, 4, 1, 3))
        interior = ((Q(0), Q(0)), (Q(3), Q(0)), (Q(1), Q(1)),
                    (Q(3), Q(3)), (Q(0), Q(3)))
        zero_shoelace_noncollinear = (
            (Q(5), Q(-2)), (Q(2), Q(1)), (Q(-2), Q(-3)),
            (Q(0), Q(-4)), (Q(-4), Q(4)), (Q(-5), Q(3)))
        self.assertEqual(twice_area(zero_shoelace_noncollinear), 0)
        for invalid in (repeated, star, interior,
                        zero_shoelace_noncollinear):
            with self.assertRaises(ValueError):
                G.polygon_monomial_batch_green(invalid, {(0, 0)})

        # On a strictly convex five-point set, exactly the five rotations of
        # each of the two cyclic orientations may pass; all star/mixed orders
        # must fail.  This independently exercises the global edge guard.
        accepted = 0
        for permutation in itertools.permutations(hull):
            try:
                G.polygon_monomial_batch_green(permutation, {(0, 0)})
            except ValueError:
                continue
            accepted += 1
        self.assertEqual(accepted, 10)

    def test_dense_target_degree80_matches_independent_triangle_engine(self):
        delta = Q(1, 60)
        alpha = Q(103, 400)
        eta = Q(8960917, 36000000)
        schedule = tuple(map(Q, (
            "1123/8000", "157041/1000000", "5267/31250",
            "87169/500000", "11593/62500", "1523/8000",
            "193097/1000000", "98573/500000", "202047/1000000",
            "20709/100000", "52917/250000", "52917/250000")))
        jobs = C.scheduled_cross_branch_jobs(
            R, k=48, alpha=alpha, eta=eta, delta=delta,
            schedule=schedule, common_r=8)
        domains = [domain for branch, _family, domain, _first in jobs
                   if branch == "Stotal"]
        self.assertEqual(len(domains), 1)
        domain = domains[0]
        shift = 3 * delta
        polygon = R._shifted_polygon(
            domain.total_bound - shift, domain.x_bound,
            None if domain.y_lower is None else domain.y_lower - shift,
            None if domain.y_upper is None else domain.y_upper - shift,
            None if domain.total_lower is None else domain.total_lower - shift)
        powers = {(8 + a, 37 + b)
                  for a in range(36) for b in range(36 - a)}
        self.assertEqual(len(powers), 666)
        self.assertEqual(max(a + b for a, b in powers), 80)
        self.check_against_triangle_oracle(polygon, powers)

    def test_all_target_polygons_are_convex_and_low_moments_match(self):
        delta = Q(1, 60)
        alpha_low = Q(103, 400)
        alpha_high = Q(9500917, 36000000)
        eta = Q(8960917, 36000000)
        schedule = tuple(map(Q, (
            "1123/8000", "157041/1000000", "5267/31250",
            "87169/500000", "11593/62500", "1523/8000",
            "193097/1000000", "98573/500000", "202047/1000000",
            "20709/100000", "52917/250000", "52917/250000")))
        checked = nonempty = 0
        for common_r in range(1, 13):
            for alpha in (alpha_low, alpha_high):
                jobs = C.scheduled_cross_branch_jobs(
                    R, k=48, alpha=alpha, eta=eta, delta=delta,
                    schedule=schedule, common_r=common_r)
                for branch, _family, domain, _first in jobs:
                    for shift_count in range(15 - common_r):
                        shift = shift_count * delta
                        total = domain.total_bound - shift
                        if total <= 0:
                            continue
                        polygon = R._shifted_polygon(
                            total, domain.x_bound,
                            None if domain.y_lower is None else
                                domain.y_lower - shift,
                            None if domain.y_upper is None else
                                domain.y_upper - shift,
                            None if domain.total_lower is None else
                                domain.total_lower - shift)
                        if len(polygon) >= 3:
                            self.assertEqual(len(polygon), len(set(polygon)))
                            orientation = G._orientation(
                                G._scaled_vertices(polygon)[0])
                            self.assertIn(orientation, (-1, 1))
                            nonempty += 1
                        self.check_against_triangle_oracle(
                            polygon, {(0, 0), (1, 0), (0, 1)})
                        checked += 1
        self.assertEqual(checked, 804)
        self.assertEqual(nonempty, 711)

    def test_zero_dimensional_dispatch_bypasses_green_polygon(self):
        class Bomb:
            @staticmethod
            def _polygon_monomial_batch(_polygon, _powers):
                raise AssertionError("Green polygon called on zero dimension")

        domain = type("Domain", (), dict(
            total_bound=Q(3, 5), x_bound=None, y_lower=None,
            y_upper=None, total_lower=None))()
        self.assertEqual(
            F._domain_moments(Bomb, {(0, 0), (0, 2), (1, 0)},
                              0, 5, domain, Q(0)),
            {(0, 0): Q(3, 5), (0, 2): Q(9, 125), (1, 0): Q(0)})
        self.assertEqual(
            F._domain_moments(Bomb, {(0, 0), (2, 0), (0, 1)},
                              5, 0, domain, Q(0)),
            {(0, 0): Q(3, 5), (2, 0): Q(9, 125), (0, 1): Q(0)})


class GreenV9RuntimeAudit(unittest.TestCase):
    def test_runner_patches_only_the_runtime_radial_module(self):
        original_load = V9.load
        evidence = {}

        def intercepted(name, path, data):
            module = original_load(name, path, data)
            if name == "d14_grid38_green_v9_v2":
                def probe(_count, _local, dependencies, base, _backend,
                          **_kwargs):
                    radial = base.import_snapshot(
                        "green_v9_probe_radial", base.RADIAL,
                        dependencies[base.RADIAL])
                    green = sys.modules[
                        "d14_grid38_green_v9_moments"
                    ].polygon_monomial_batch_green
                    evidence["patched"] = radial._polygon_monomial_batch is green
                    evidence["radial_path_type"] = type(base.RADIAL).__name__
                    return {"source_hashes": {}}
                module.build = probe
            return module

        with tempfile.TemporaryDirectory(prefix="green-v9-runner-probe-") as text:
            output = Path(text) / "result.json"
            argv = [str(RUNNER_PATH), "--common-r", "9", "--output",
                    str(output), "--expected-self-sha256", PINS[RUNNER_PATH]]
            with mock.patch.object(V9, "load", side_effect=intercepted), \
                    mock.patch.object(sys, "argv", argv):
                V9.main()
            raw = json.loads(output.read_bytes())
        self.assertEqual(evidence, {"patched": True,
                                    "radial_path_type": "PosixPath"})
        self.assertEqual(raw["producer_sha256"], PINS[RUNNER_PATH])
        self.assertEqual(raw["format"],
                         "D14-grid38-scaled-cutoff-cross-common-r-green-v9")
        self.assertTrue(raw["algorithm"][
            "polygon_runtime_module_patched_after_pinned_load"])
        for path, expected in V9.LOCAL_PINNED.items():
            self.assertEqual(digest(path), expected)


if __name__ == "__main__":
    unittest.main()
