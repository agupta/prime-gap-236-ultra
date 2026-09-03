#!/usr/bin/env python3
"""Face-batched exact cross matrices for the frontier-r10 outer block.

This helper changes only evaluation order.  It constructs all requested
marginal coordinates on an ``(r,h)`` face, then shares orbit densities across
the full rectangular coordinate block.  Exact low-dimensional tests compare
every entry with the scalar literal branch engine.
"""

from __future__ import annotations

from collections import defaultdict
from fractions import Fraction as Q
import hashlib
import importlib.util
from pathlib import Path
import sys


FILE = Path(__file__).resolve()
BASE_PATH = FILE.with_name("wide_frontier_r10_d16_outer_b4_v1.py")
PINNED_BASE_SHA256 = (
    "ccfa357fa340c9e839406dcc8ac3b0bc95d76488e02f2e6679984eb0f1f44bc9"
)


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


if sha256(BASE_PATH) != PINNED_BASE_SHA256:
    raise RuntimeError("frontier-r10 base source changed")
_spec = importlib.util.spec_from_file_location(
    "frontier_r10_batched_base", BASE_PATH)
B = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = B
_spec.loader.exec_module(B)
P = B.P


def density_product(left, right, evaluator, dimension, r, h, max_h):
    """One exact ordered marginal product with cached face densities."""
    combined = defaultdict(lambda: defaultdict(Q))
    for left_orbit, left_poly in left.items():
        for right_orbit, right_poly in right.items():
            product = P.ei._poly_mul(left_poly, right_poly)
            for orbit, multiplicity in P.ei.multiply_monomial_orbits(
                    left_orbit, right_orbit):
                P.add_poly(combined[orbit], product, Q(multiplicity))
    integrand = defaultdict(Q)
    for orbit, polynomial in combined.items():
        density = evaluator.orbit_density(
            dimension, orbit, r, h, max_h)
        if density:
            P.add_poly(integrand,
                       P.ei._poly_mul(density, dict(polynomial)), Q(1))
    return dict(integrand)


def cross_matrix(left_support, left_coordinates,
                 right_support, right_coordinates, common_eta,
                 *, progress=False, selected_r=None):
    """Return the exact rectangular J matrix for two coordinate families."""
    left_coordinates = tuple(tuple(row) for row in left_coordinates)
    right_coordinates = tuple(tuple(row) for row in right_coordinates)
    if (not left_coordinates or not right_coordinates or
            left_support.k != right_support.k or
            left_support.delta != right_support.delta):
        raise ValueError("invalid batched cross request")
    dimension = left_support.k - 1
    evaluator = P.GroupedEvaluator(left_support, [], [], Q)
    max_r = min(dimension, left_support.max_large(),
                right_support.max_large())
    if selected_r is None:
        r_values = range(max_r + 1)
    else:
        if (isinstance(selected_r, bool) or not isinstance(selected_r, int) or
                not 0 <= selected_r <= max_r):
            raise ValueError("selected common count outside range")
        r_values = (selected_r,)
    matrix = [[Q(0) for _ in right_coordinates]
              for _ in left_coordinates]
    counters = {
        "faces": 0, "branch_domains": 0, "scalar_integrals": 0,
        "density_cache_misses": 0,
    }
    for r in r_values:
        max_h = int(Q(common_eta) // left_support.delta) - r
        if max_h < 0:
            continue
        for h in range(max_h + 1):
            outer = Q(common_eta) - (r + h) * left_support.delta
            if outer <= 0:
                continue
            left_blocks = [P.branch_polynomials(
                left_support, coordinate, r, h)
                for coordinate in left_coordinates]
            right_blocks = [P.branch_polynomials(
                right_support, coordinate, r, h)
                for coordinate in right_coordinates]
            counters["faces"] += 1
            for left_branch in P.BRANCHES:
                left_constraints = left_support._branch_constraints(
                    r, h, left_branch)
                if left_constraints is None:
                    continue
                for right_branch in P.BRANCHES:
                    right_constraints = right_support._branch_constraints(
                        r, h, right_branch)
                    if right_constraints is None:
                        continue
                    constraints = left_constraints + right_constraints
                    if (dimension and evaluator.integrate_domain(
                            {(0, 0): Q(1)}, dimension, r, outer,
                            constraints) <= 0):
                        continue
                    counters["branch_domains"] += 1
                    before = evaluator.orbit_density.cache_info().misses
                    for i, left_coordinate in enumerate(left_blocks):
                        left = left_coordinate[left_branch]
                        if not left:
                            continue
                        for j, right_coordinate in enumerate(right_blocks):
                            right = right_coordinate[right_branch]
                            if not right:
                                continue
                            integrand = density_product(
                                left, right, evaluator, dimension, r, h,
                                max_h)
                            if not integrand:
                                continue
                            matrix[i][j] += evaluator.integrate_domain(
                                integrand, dimension, r, outer, constraints)
                            counters["scalar_integrals"] += 1
                    after = evaluator.orbit_density.cache_info().misses
                    counters["density_cache_misses"] += after - before
            if progress:
                print(f"batch r={r} h={h}/{max_h} {counters}", flush=True)
            evaluator.clear_face_caches(clear_marginals=True)
        evaluator.clear_radial_caches()
    return matrix, counters


def scalar_replay(left_support, left_coordinates,
                  right_support, right_coordinates, common_eta):
    """Slow exact reference used only by low-dimensional tests."""
    return [[P.cross_marginal(left_support, left, right_support, right,
                              common_eta)
             for right in right_coordinates]
            for left in left_coordinates]


__all__ = ["cross_matrix", "density_product", "scalar_replay"]
