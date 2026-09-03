#!/usr/bin/env python3
"""Bounded exact probe for the direct distinguished-coordinate b formula.

For one symmetric outer coordinate H and one band V,

  48 J(F,H 1_V) = 48 integral_V H(t) m_F(t without coordinate 1) dt.

This implementation forms the exact 47-variable marginal m_F first, then
multiplies it by each literal distinguished-coordinate branch of H before a
single grouped domain integration.  It avoids slicing the capped H marginal
into 97 separately integrated right-orbit jobs.  The executable action is one
fixed exact face probe only; no full target or resume path exists.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from fractions import Fraction as Q
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import resource
import signal
import sys
import time


FILE = Path(__file__).resolve()
REPO = FILE.parents[3]
PLAN = FILE.with_name("active25_d18_two_band_exact_certificate_plan_v1.py")
PLAN_SHA256 = "079b961fb9393f04ea01b04f9c653f0339bf94d3ae4473fbae9d8511dc6dc347"
MAX_WALL_SECONDS = 300
MAX_RSS_KIB = 512 * 1024


def sha256(value):
    data = value if isinstance(value, bytes) else Path(value).read_bytes()
    return hashlib.sha256(data).hexdigest()


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


if sha256(PLAN) != PLAN_SHA256:
    raise RuntimeError("pinned minimal exact plan changed")
plan = load("active25_d18_direct_b_pinned_plan", PLAN)


def marginal_orbit_block(frontier, marginal, alpha1, u0):
    """Collect m_F as orbit -> exact polynomial in aggregate (z,w)."""
    block = {}
    for (power, orbit), coefficient in marginal.items():
        destination = block.setdefault(orbit, defaultdict(Q))
        frontier.shell.add_poly(
            destination,
            dict(frontier.ei._linear_power(
                alpha1 - u0, Q(-1), Q(-1), power)),
            coefficient)
    return {orbit: dict(polynomial) for orbit, polynomial in block.items()
            if polynomial}


def combine_orbit_blocks(frontier, left, right):
    combined = {}
    logical_pairs = 0
    orbit_products = 0
    for left_orbit, left_poly in left.items():
        for right_orbit, right_poly in right.items():
            logical_pairs += 1
            polynomial = frontier.ei._poly_mul(left_poly, right_poly)
            for orbit, multiplicity in frontier.ei.multiply_monomial_orbits(
                    left_orbit, right_orbit):
                destination = combined.setdefault(orbit, defaultdict(Q))
                frontier.shell.add_poly(
                    destination, polynomial, Q(multiplicity))
                orbit_products += 1
    return ({orbit: dict(polynomial)
             for orbit, polynomial in combined.items() if polynomial},
            logical_pairs, orbit_products)


def exact_direct_b_face(
        frontier, basis, outer_vector, marginal, *, k, delta, alpha1,
        eta, schedule, low, high, common_r, h):
    """Exact endpoint values for one complete shared-coordinate face."""
    if (type(common_r) is not int or type(h) is not int or
            not Q(0) < low < high or not Q(0) < eta <= alpha1 or
            not 0 <= common_r < k):
        raise ValueError("invalid direct-b face parameters")
    max_h = int(eta // delta) - common_r
    if not 0 <= h <= max_h:
        raise ValueError("translated small-face count is outside the face")
    outer_radius = eta - (common_r + h) * delta
    u0 = (common_r + h) * delta
    inner_block = marginal_orbit_block(frontier, marginal, alpha1, u0)
    components = frontier.outer_core.components(basis, outer_vector, k)
    support_type = frontier.shell.ScheduledStratumSupport
    supports = {
        "low": support_type.make(k, low, eta, delta, schedule),
        "high": support_type.make(k, high, eta, delta, schedule),
    }
    dummy = frontier.GroupedEvaluator(supports["high"], [], [], Q)
    density_cache = {}
    endpoint_values = {}
    endpoint_rows = {}
    for endpoint, capped in supports.items():
        branches = frontier.outer_core.branch_polynomials(
            capped, components, common_r, h)
        total_value = Q(0)
        rows = []
        for branch in frontier.BRANCHES:
            right = branches[branch]
            constraints = capped._branch_constraints(common_r, h, branch)
            if not right or constraints is None:
                continue
            domain = frontier.canonical_domain_key(
                dummy, k - 1, common_r, outer_radius, constraints)
            if domain is None:
                continue
            combined, logical_pairs, orbit_products = combine_orbit_blocks(
                frontier, inner_block, right)
            integrand = defaultdict(Q)
            for orbit, polynomial in combined.items():
                if orbit not in density_cache:
                    density_cache[orbit] = dummy.orbit_density(
                        k - 1, orbit, common_r, h, max_h)
                density = density_cache[orbit]
                if density:
                    frontier.shell.add_poly(
                        integrand,
                        frontier.ei._poly_mul(density, polynomial), Q(1))
            value = frontier.integrate_canonical_domain(dict(integrand), domain)
            total_value += value
            rows.append({
                "branch": branch,
                "outer_total_large_count": frontier.branch_total(
                    common_r, branch),
                "right_marginal_orbits": len(right),
                "logical_orbit_pairs": logical_pairs,
                "expanded_orbit_products": orbit_products,
                "combined_orbits": len(combined),
                "integrand_monomials": len(integrand),
                "J": value,
            })
        endpoint_values[endpoint] = total_value
        endpoint_rows[endpoint] = rows
    dummy.clear_face_caches(clear_marginals=True)
    dummy.clear_radial_caches()
    return {
        "low_J": endpoint_values["low"],
        "high_J": endpoint_values["high"],
        "band_J": endpoint_values["high"] - endpoint_values["low"],
        "band_48J": 48 * (endpoint_values["high"] - endpoint_values["low"]),
        "inner_marginal_orbits": len(inner_block),
        "density_orbits_reused_across_endpoints_and_branches":
            len(density_cache),
        "endpoints": endpoint_rows,
    }


def exact_direct_band_b(
        frontier, basis, outer_vector, marginal, *, k, delta, alpha1,
        eta, schedule, low, high):
    """Low-k oracle/full formula; production k=48 is deliberately unreachable."""
    maximum_r = min(k - 1, max(
        r for r in range(1, k + 1) if r * delta < schedule[min(
            r, len(schedule)) - 1]))
    total = Q(0)
    for common_r in range(maximum_r + 1):
        for h in range(int(eta // delta) - common_r + 1):
            row = exact_direct_b_face(
                frontier, basis, outer_vector, marginal, k=k, delta=delta,
                alpha1=alpha1, eta=eta, schedule=schedule, low=low,
                high=high, common_r=common_r, h=h)
            total += row["band_J"]
    return 48 * total


def cost_probe():
    start_self = FILE.read_bytes()
    start_plan = PLAN.read_bytes()
    start_pins = plan.snapshots()
    started = time.monotonic()
    frontier, basis, vector, outer, _square, _inner_i, _inner_b = \
        plan.load_inputs()
    scan = plan.load("active25_d18_direct_b_scan", plan.SCAN)
    marginal = scan.marginal_polynomial(
        basis, vector, plan.K, plan.ALPHA1)
    if len(marginal) != 471:
        raise ArithmeticError("refined D18 marginal inventory changed")
    reconstruction_seconds = time.monotonic() - started
    band = plan.BANDS[0]
    face_started = time.monotonic()
    # r=0 eliminates large-coordinate split combinatorics while retaining all
    # D18 orbit products, both endpoints, and all live H branches.
    common_r = 0
    h = int(band["eta"] // plan.DELTA)
    face = exact_direct_b_face(
        frontier, basis, outer, marginal, k=plan.K, delta=plan.DELTA,
        alpha1=plan.ALPHA1, eta=band["eta"],
        schedule=band["schedule"], low=band["low"], high=band["high"],
        common_r=common_r, h=h)
    face_seconds = time.monotonic() - face_started
    total_seconds = time.monotonic() - started
    if (FILE.read_bytes() != start_self or PLAN.read_bytes() != start_plan or
            any(path.read_bytes() != payload
                for path, payload in start_pins.items())):
        raise RuntimeError("direct-b source closure changed during probe")
    faces = sum(plan.stage_inventory()["b"][
        "common_face_count_per_endpoint"].values())
    return {
        "format": "active25-d18-direct-distinguished-b-cost-probe-v1",
        "status": "BOUNDED EXACT DIRECT-B FACE PROBE",
        "source_sha256": sha256(start_self),
        "plan_sha256": PLAN_SHA256,
        "dependency_sha256": {
            str(path.relative_to(REPO)): digest for path, digest in plan.PINS.items()},
        "identity": (
            "48J(F,H*1_band)=48*integral_band H(t)*m_F(t_without_1)dt"),
        "factor_48_applied_exactly_once": True,
        "probe": {
            "band": band["name"], "common_r": common_r, "h": h,
            "reconstruction_seconds": reconstruction_seconds,
            "face_seconds": face_seconds,
            "face": {
                key: (str(value) if isinstance(value, Q) else
                      [{k: (str(v) if isinstance(v, Q) else v)
                        for k, v in item.items()} for item in value]
                      if isinstance(value, list) else value)
                for key, value in face.items()},
            "logical_band_face_shards": faces,
            "linear_all_face_projection_seconds": face_seconds * faces,
            "linear_all_face_projection_hours": face_seconds * faces / 3600,
            "projection_warning": (
                "one r=0 boundary face extrapolated across heterogeneous faces; "
                "not a runtime bound or launch authorization"),
        },
        "wall_seconds": total_seconds,
        "wall_limit_seconds": MAX_WALL_SECONDS,
        "peak_rss_kib": int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss),
        "rss_limit_kib": MAX_RSS_KIB,
        "production_target_started": False,
        "launch_authorized": False,
        "resume_supported": False,
        "theorem_ready": False,
    }


def canonical_json(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"),
                       allow_nan=False) + "\n").encode("ascii")


def publish_exclusive(path, payload):
    target = Path(path).resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())


def apply_limits():
    cap = MAX_RSS_KIB * 1024
    soft, hard = resource.getrlimit(resource.RLIMIT_AS)
    new_hard = hard if hard != resource.RLIM_INFINITY else cap
    resource.setrlimit(resource.RLIMIT_AS, (min(cap, new_hard), new_hard))
    signal.alarm(MAX_WALL_SECONDS)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cost-probe", action="store_true", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    apply_limits()
    payload = canonical_json(cost_probe())
    publish_exclusive(args.output, payload)
    sys.stdout.buffer.write(payload)


if __name__ == "__main__":
    main()
