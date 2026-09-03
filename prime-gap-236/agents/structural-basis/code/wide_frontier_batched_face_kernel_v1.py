#!/usr/bin/env python3
"""One-face exact rectangular cross kernel for wide-support cost probes.

This module is deliberately support-agnostic.  It evaluates one fixed
``(r,h)`` face using the already tested face-batched cross implementation.
Low-dimensional tests sum every face and recover the complete literal cross
matrix exactly.  It contains no target schedule and cannot launch a k=48 run.
"""

from __future__ import annotations

from fractions import Fraction as Q
import hashlib
import importlib.util
from pathlib import Path
import sys


FILE = Path(__file__).resolve()
BATCH_PATH = FILE.with_name("wide_frontier_r10_batched_cross_v1.py")
PINNED_BATCH_SHA256 = (
    "c3f1559e460ecefa0427a47e0f793faa679acb51d18fbd09e332af3fef9d01ea"
)


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


if sha256(BATCH_PATH) != PINNED_BATCH_SHA256:
    raise RuntimeError("batched cross dependency changed")
_spec = importlib.util.spec_from_file_location(
    "wide_frontier_face_batch_dependency", BATCH_PATH)
M = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = M
_spec.loader.exec_module(M)
P = M.P


def face_geometry(left_support, right_support, common_eta, r, h):
    """Validate and return ``(dimension,max_h,outer)`` for one face."""
    if (left_support.k != right_support.k or
            left_support.delta != right_support.delta):
        raise ValueError("cross supports disagree in k or delta")
    if (isinstance(r, bool) or not isinstance(r, int) or
            isinstance(h, bool) or not isinstance(h, int)):
        raise TypeError("face indices must be integers")
    dimension = left_support.k - 1
    max_r = min(dimension, left_support.max_large(),
                right_support.max_large())
    if not 0 <= r <= max_r:
        raise ValueError("common count outside supported range")
    max_h = int(Q(common_eta) // left_support.delta) - r
    if not 0 <= h <= max_h:
        raise ValueError("inclusion-exclusion face outside supported range")
    outer = Q(common_eta) - (r + h) * left_support.delta
    if outer <= 0:
        raise ValueError("zero-volume face")
    return dimension, max_h, outer


def cross_face_matrix(left_support, left_coordinates,
                      right_support, right_coordinates, common_eta,
                      r, h):
    """Return an exact rectangular matrix from one fixed common face."""
    left_coordinates = tuple(tuple(row) for row in left_coordinates)
    right_coordinates = tuple(tuple(row) for row in right_coordinates)
    if not left_coordinates or not right_coordinates:
        raise ValueError("coordinate families must be nonempty")
    dimension, max_h, outer = face_geometry(
        left_support, right_support, common_eta, r, h)
    evaluator = P.GroupedEvaluator(left_support, [], [], Q)
    left_blocks = [P.branch_polynomials(
        left_support, coordinate, r, h) for coordinate in left_coordinates]
    right_blocks = [P.branch_polynomials(
        right_support, coordinate, r, h) for coordinate in right_coordinates]
    matrix = [[Q(0) for _ in right_coordinates]
              for _ in left_coordinates]
    counters = {
        "faces": 1,
        "branch_domains": 0,
        "scalar_integrals": 0,
        "density_cache_misses": 0,
    }
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
                    integrand = M.density_product(
                        left, right, evaluator, dimension, r, h, max_h)
                    if not integrand:
                        continue
                    matrix[i][j] += evaluator.integrate_domain(
                        integrand, dimension, r, outer, constraints)
                    counters["scalar_integrals"] += 1
            counters["density_cache_misses"] += (
                evaluator.orbit_density.cache_info().misses - before)
    evaluator.clear_face_caches(clear_marginals=True)
    evaluator.clear_radial_caches()
    return matrix, counters


def all_faces(left_support, right_support, common_eta):
    """Canonical nonzero face inventory used by exact sum regressions."""
    if (left_support.k != right_support.k or
            left_support.delta != right_support.delta):
        raise ValueError("cross supports disagree in k or delta")
    dimension = left_support.k - 1
    max_r = min(dimension, left_support.max_large(),
                right_support.max_large())
    faces = []
    for r in range(max_r + 1):
        max_h = int(Q(common_eta) // left_support.delta) - r
        for h in range(max(0, max_h + 1)):
            if Q(common_eta) - (r + h) * left_support.delta > 0:
                faces.append((r, h))
    return tuple(faces)


__all__ = ["all_faces", "cross_face_matrix", "face_geometry"]
