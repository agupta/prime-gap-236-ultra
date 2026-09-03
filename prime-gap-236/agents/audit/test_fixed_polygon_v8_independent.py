#!/usr/bin/env python3
"""Independent exact tests for the fixed-polygon-v8 moment substitution.

The oracle uses Green's theorem on an independently constructed half-plane
intersection polygon.  It neither triangulates the polygon nor imports the
producer's reference moment routine.
"""

from __future__ import annotations

from fractions import Fraction as Q
import hashlib
import importlib.util
import json
import math
from pathlib import Path
from types import SimpleNamespace
import sys
import tempfile
import unittest
from unittest import mock


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
MOMENT_PATH = REPO / "agents/exact-projection-engine/fixed_polygon_moments.py"
RADIAL_PATH = REPO / "verify/exact_capped_certificate.py"
CROSS_PATH = REPO / "agents/exact-projection-engine/symmetric_cutoff_cross.py"
FAST_PATH = REPO / "agents/exact-projection-engine/fast_tagged_scalar.py"
RUNNER_PATH = REPO / (
    "agents/exact-projection-engine/"
    "d14_grid38_scaled_b_shard_fixed_polygon_v8.py")
PINS = {
    MOMENT_PATH:
        "4100a9eeb86563ae84bf02ed4df9a2a5b696b5cc9ff163d15ac482b242b637bb",
    RADIAL_PATH:
        "1787e7b482a5c2982de56486bc774794f6e671b3db4d9ab7207ebb1c85dc079c",
    CROSS_PATH:
        "d3aa9c1793a6c1d7e9ad2b71cb2d81dee690e7d9aaaea56134c428a752967726",
    FAST_PATH:
        "5d9d82ae7b097a40b852a8471e281d5bd5ad69d08240e1a73d3928e21a40aaa2",
    RUNNER_PATH:
        "36a8e027c83cabb272aa28a5d542dc571793cbcf90c5ca48787bc20092a55b72",
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(name, path):
    expected = PINS[path]
    if digest(path) != expected:
        raise RuntimeError(f"pinned source changed: {path}")
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


M = load("fixed_polygon_v8_independent_core", MOMENT_PATH)
R = load("fixed_polygon_v8_independent_radial", RADIAL_PATH)
C = load("fixed_polygon_v8_independent_cross", CROSS_PATH)
F = load("fixed_polygon_v8_independent_fast", FAST_PATH)
V8 = load("fixed_polygon_v8_independent_runner", RUNNER_PATH)


def cross(o, a, b):
    return ((a[0] - o[0]) * (b[1] - o[1]) -
            (a[1] - o[1]) * (b[0] - o[0]))


def convex_hull(points):
    points = sorted(set(points))
    if len(points) <= 2:
        return points
    lower = []
    for point in points:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], point) <= 0:
            lower.pop()
        lower.append(point)
    upper = []
    for point in reversed(points):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], point) <= 0:
            upper.pop()
        upper.append(point)
    return lower[:-1] + upper[:-1]


def halfplane_polygon(total_bound, x_bound=None, y_lower=None,
                      y_upper=None, total_lower=None):
    """Construct the runtime polygon by pairwise half-plane intersections."""
    constraints = [
        (Q(-1), Q(0), Q(0)),       # x >= 0
        (Q(0), Q(-1), Q(0)),       # y >= 0
        (Q(1), Q(1), Q(total_bound)),
    ]
    if x_bound is not None:
        constraints.append((Q(1), Q(0), Q(x_bound)))
    if y_upper is not None:
        constraints.append((Q(0), Q(1), Q(y_upper)))
    if y_lower is not None:
        constraints.append((Q(0), Q(-1), -Q(y_lower)))
    if total_lower is not None:
        constraints.append((Q(-1), Q(-1), -Q(total_lower)))
    vertices = set()
    for i, (a1, b1, c1) in enumerate(constraints):
        for a2, b2, c2 in constraints[i + 1:]:
            determinant = a1 * b2 - a2 * b1
            if not determinant:
                continue
            x = (c1 * b2 - c2 * b1) / determinant
            y = (a1 * c2 - a2 * c1) / determinant
            if all(a * x + b * y <= c for a, b, c in constraints):
                vertices.add((x, y))
    return convex_hull(vertices)


def edge_moment(polygon, a, b):
    """Green's-theorem oracle: integral x^a y^b = int x^(a+1)y^b dy/(a+1)."""
    if len(polygon) < 3:
        return Q(0)
    total = Q(0)
    for index, (x0, y0) in enumerate(polygon):
        x1, y1 = polygon[(index + 1) % len(polygon)]
        dx, dy = x1 - x0, y1 - y0
        edge = Q(0)
        for i in range(a + 2):
            x_coefficient = Q(math.comb(a + 1, i)) * x0 ** (a + 1 - i) * dx**i
            for j in range(b + 1):
                y_coefficient = Q(math.comb(b, j)) * y0 ** (b - j) * dy**j
                edge += x_coefficient * y_coefficient / (i + j + 1)
        total += dy * edge / (a + 1)
    return total


def edge_batch(polygon, powers):
    return {power: edge_moment(polygon, *power) for power in powers}


def common_denominator(polygon, maximum_degree):
    scale = 1
    for point in polygon:
        for coordinate in point:
            scale = math.lcm(scale, Q(coordinate).denominator)
    return scale ** (maximum_degree + 2) * math.factorial(maximum_degree + 2)


class IndependentPolygonMomentTest(unittest.TestCase):
    def check(self, polygon, powers):
        observed = M.polygon_monomial_batch_fixed(polygon, powers)
        expected = edge_batch(convex_hull(tuple(map(tuple, polygon))), powers)
        self.assertEqual(observed, expected)
        if powers and len(polygon) >= 3:
            maximum = max(a + b for a, b in powers)
            denominator = common_denominator(polygon, maximum)
            for value in observed.values():
                self.assertEqual(denominator % value.denominator, 0)

    def test_closed_forms_orientation_rotation_and_degeneracy(self):
        powers = {(0, 0), (1, 0), (0, 1), (2, 3), (7, 5),
                  (80, 0), (0, 80), (39, 41)}
        triangle = [(Q(-2, 7), Q(-1, 5)),
                    (Q(11, 13), Q(2, 9)),
                    (Q(1, 17), Q(19, 23))]
        self.check(triangle, powers)
        self.check(list(reversed(triangle)), powers)
        self.check(triangle[1:] + triangle[:1], powers)
        simplex = [(Q(0), Q(0)), (Q(1), Q(0)), (Q(0), Q(1))]
        observed = M.polygon_monomial_batch_fixed(simplex, powers)
        for (a, b), value in observed.items():
            self.assertEqual(
                value, Q(math.factorial(a) * math.factorial(b),
                         math.factorial(a + b + 2)))
        for polygon in ((), ((Q(0), Q(0)),),
                        ((Q(0), Q(0)), (Q(1), Q(1))),
                        ((Q(0), Q(0)), (Q(1), Q(1)), (Q(2), Q(2)))):
            self.assertEqual(
                M.polygon_monomial_batch_fixed(polygon, powers),
                {power: Q(0) for power in powers})

    def test_dense_target_density_offsets_through_degree_80(self):
        polygon = halfplane_polygon(
            Q(173, 997), Q(29, 211), Q(7, 101), Q(41, 199), Q(13, 127))
        # A two-dimensional r=9 target face has radial-density offsets
        # x^(r-1)y^(47-r-1)=x^8 y^37.  The two polynomial marginals add at
        # most 35 further powers, giving every target-shaped exponent here.
        powers = {(8 + a, 37 + b)
                  for a in range(36) for b in range(36 - a)}
        self.check(polygon, powers)

    def test_every_target_polygon_domain_high_degree(self):
        k = 48
        delta = Q(1, 60)
        alpha_low = Q(103, 400)
        alpha_high = Q(9500917, 36000000)
        eta = Q(8960917, 36000000)
        schedule = tuple(map(Q, (
            "1123/8000", "157041/1000000", "5267/31250",
            "87169/500000", "11593/62500", "1523/8000",
            "193097/1000000", "98573/500000", "202047/1000000",
            "20709/100000", "52917/250000", "52917/250000")))
        checked = 0
        nonempty = 0
        for common_r in range(1, 13):
            base_x = common_r - 1
            base_y = 46 - common_r
            powers = {
                (base_x, base_y),
                (base_x + 1, base_y), (base_x, base_y + 1),
                (base_x + 2, base_y + 3),
                (base_x + 3, base_y + 2),
                (base_x + 35, base_y),
                (base_x, base_y + 35),
                (base_x + 34, base_y + 1),
                (base_x + 1, base_y + 34),
                (base_x + 17, base_y + 18),
            }
            for alpha in (alpha_low, alpha_high):
                jobs = C.scheduled_cross_branch_jobs(
                    R, k=k, alpha=alpha, eta=eta, delta=delta,
                    schedule=schedule, common_r=common_r)
                for _branch, _family, domain, _affine in jobs:
                    for shift_count in range(15 - common_r):
                        shift = shift_count * delta
                        total = domain.total_bound - shift
                        y_lower = (None if domain.y_lower is None else
                                   domain.y_lower - shift)
                        y_upper = (None if domain.y_upper is None else
                                   domain.y_upper - shift)
                        total_lower = (
                            None if domain.total_lower is None else
                            domain.total_lower - shift)
                        if total <= 0:
                            continue
                        production_polygon = R._shifted_polygon(
                            total, domain.x_bound, y_lower, y_upper, total_lower)
                        independent_polygon = halfplane_polygon(
                            total, domain.x_bound, y_lower, y_upper, total_lower)
                        observed = M.polygon_monomial_batch_fixed(
                            production_polygon, powers)
                        expected = edge_batch(independent_polygon, powers)
                        self.assertEqual(
                            observed, expected,
                            (common_r, alpha, _branch, shift_count,
                             production_polygon, independent_polygon))
                        denominator = common_denominator(production_polygon, 80)
                        for value in observed.values():
                            self.assertEqual(denominator % value.denominator, 0)
                        checked += 1
                        nonempty += bool(len(independent_polygon) >= 3)
        self.assertGreater(checked, 500)
        self.assertGreater(nonempty, 100)

    def test_zero_dimensional_faces_bypass_polygon_batch(self):
        class Bomb:
            @staticmethod
            def _polygon_monomial_batch(_polygon, _requested):
                raise AssertionError("polygon batch called on zero-dimensional face")

        domain = SimpleNamespace(
            total_bound=Q(3, 5), x_bound=None, y_lower=None,
            y_upper=None, total_lower=None)
        point = F._domain_moments(Bomb, {(0, 0), (1, 0)}, 0, 0, domain, Q(0))
        self.assertEqual(point, {(0, 0): Q(1), (1, 0): Q(0)})
        y_line = F._domain_moments(
            Bomb, {(0, 0), (0, 2), (1, 0)}, 0, 5, domain, Q(0))
        self.assertEqual(y_line, {
            (0, 0): Q(3, 5), (0, 2): Q(9, 125), (1, 0): Q(0)})
        x_line = F._domain_moments(
            Bomb, {(0, 0), (2, 0), (0, 1)}, 5, 0, domain, Q(0))
        self.assertEqual(x_line, {
            (0, 0): Q(3, 5), (2, 0): Q(9, 125), (0, 1): Q(0)})


class RuntimeSubstitutionTest(unittest.TestCase):
    def test_real_runner_loader_patches_the_runtime_radial_module(self):
        original_load = V8.load
        evidence = {}

        def intercepted_load(name, path, data):
            module = original_load(name, path, data)
            if name == "d14_grid38_fixed_polygon_v8_v2":
                def probe_build(_common_r, _local, dependencies, base, _fast,
                                **_kwargs):
                    radial = base.import_snapshot(
                        "fixed_polygon_v8_probe_radial", base.RADIAL,
                        dependencies[base.RADIAL])
                    expected = sys.modules[
                        "d14_grid38_fixed_polygon_v8_moments"
                    ].polygon_monomial_batch_fixed
                    evidence["patched"] = (
                        radial._polygon_monomial_batch is expected)
                    evidence["radial_path_type"] = type(base.RADIAL).__name__
                    return {"source_hashes": {}}
                module.build = probe_build
            return module

        with tempfile.TemporaryDirectory(prefix="fixed-polygon-v8-probe-") as root:
            output = Path(root) / "probe.json"
            argv = [
                str(RUNNER_PATH), "--common-r", "12", "--output", str(output),
                "--expected-self-sha256", PINS[RUNNER_PATH],
            ]
            with mock.patch.object(V8, "load", side_effect=intercepted_load), \
                    mock.patch.object(sys, "argv", argv):
                V8.main()
            raw = json.loads(output.read_bytes())
        self.assertEqual(evidence, {
            "patched": True, "radial_path_type": "PosixPath"})
        self.assertTrue(raw["algorithm"][
            "polygon_runtime_module_patched_after_pinned_load"])
        self.assertEqual(raw["producer_sha256"], PINS[RUNNER_PATH])
        self.assertEqual(raw["format"],
                         "D14-grid38-scaled-cutoff-cross-common-r-fixed-polygon-v8")


if __name__ == "__main__":
    unittest.main()
