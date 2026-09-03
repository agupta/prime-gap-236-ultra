#!/usr/bin/env python3
"""Disabled exact-certificate plan for two capped natural-D18 bands.

Only a bounded cost probe is executable in this revision.  A later,
separately authorized producer may reconstruct, for each disjoint outer band,

    A_j = I(H_j),             b_j = 48 J(F,H_j),

where F is the frozen refined D18 coordinate and H_j is its single natural
outer dilation restricted to that band and its count cap.  Each band must be
tested separately:

    b_j^2/A_j > I(F)-48J(F,F).

This is sufficient because the same-band marginal square makes J(H_j,H_j)
nonnegative.  Disjoint I support does *not* make the multiband J kernel
positive semidefinite, so the two projected energies may not be summed unless
the exact outer J block or a separate sign proof is supplied.  No outer J
block is requested by this per-band plan.  The old F coordinate is explicit.
There is no production or resume CLI.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from fractions import Fraction as Q
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import resource
import signal
import sys
import time


FILE = Path(__file__).resolve()
REPO = FILE.parents[3]
FRONTIER = REPO / (
    "agents/small-delta-frontier/frontier_active25_inner_d16_tagged_shell.py")
DILATION = REPO / "scripts/full_simplex_dilated_vector_proxy.py"
SCAN = REPO / "agents/small-delta-frontier/scan_bv_epsilon_fixed.py"
CERT = REPO / (
    "agents/exact-integrator/results/"
    "aquarter_fullsimplex_k48_B18_refined_exact.json")
CONTRACTION = REPO / (
    "agents/structural-basis/results/"
    "d1over60_d18_uncapped_pencil_exact_v1.json")
TWO_BAND_CHECKER = REPO / "agents/analytic-new-lever/verify_two_outer_band_v1.py"
TWO_BAND_TEST = REPO / "agents/analytic-new-lever/test_two_outer_band_v1.py"
TWO_BAND_RESULT = REPO / "agents/analytic-new-lever/two_outer_band_v1_exact.json"
BRIDGE = REPO / "agents/structural-basis/code/active25_d18_h2_bridge_v1.py"
BRIDGE_TEST = REPO / (
    "agents/structural-basis/tests/test_active25_d18_h2_bridge_v1.py")
BRIDGE_RESULTS = (
    REPO / ("agents/structural-basis/results/"
            "active25_d18_h2_bridge_two_band_verified_radial_burn4000_"
            "seed2361817_v1.json"),
    REPO / ("agents/structural-basis/results/"
            "active25_d18_h2_bridge_two_band_verified_radial_burn4000_"
            "seed2361818_v1.json"),
)

PINS = {
    FRONTIER: "1393a2dd29e5660f10e632b19b6b5eeafe9363bf79b2cd4a8254049d1f9c669a",
    DILATION: "3219047bd9d339e15946947f68bd6484d23af722337ba70771c488e3e1238794",
    SCAN: "96495079a18039a0a7b0522e83ac455cbe5ff144598fff6b382f2c2953958de9",
    CERT: "af6f1eb0d75bc59caf20cc82f79a3cb339be3ac7280af2afcad89eca0e31cf58",
    CONTRACTION: "3bfaafb532da80a17bb40e4a2cfb94090beda8ca6df43acb07c4f531ce5be02f",
    TWO_BAND_CHECKER:
        "187a87f6c29532645100d9a91b94ce8038c38511dfff22326efe9722ea0f8001",
    TWO_BAND_TEST:
        "57b3ced2f04e36ae289f9faa82d47c95d87f76d545c672e1b91bdcc881e363cf",
    TWO_BAND_RESULT:
        "c74da6b53d351df7df00435709bde048d50ddd5d75ff42ad631b2b029627bdee",
    BRIDGE: "2d262e1ea4a1ea20f42ea03cb8c8bc6405ae75b8f94cc1db668dfeb0797dfe1b",
    BRIDGE_TEST:
        "05fdb84fd8be499b9d3d93a0958ea49d81e2278466a3fb1c6b640f77365d632b",
    BRIDGE_RESULTS[0]:
        "77f1975ae8e2326aa01816c10698921a5644a133a2286e6c5c5db65cfb4f2f3e",
    BRIDGE_RESULTS[1]:
        "4b7cfb8d3a71fe075f50134093347fe176c71517d98d5b8db624049d9be3d9c1",
}

K = 48
DEGREE = 18
DIMENSION = 471
ALPHA1 = Q(103, 400)
ALPHA2 = Q(237991, 900000)
DELTA = Q(1, 60)
BOUNDARY = Q(263741, 1000000)
LOWER_ETA = Q(248741, 1000000)
UPPER_ETA = Q(224491, 900000)
LOWER_SCHEDULE = tuple(Q(x, 1000000) for x in (
    139683, 156347, 157797, 173014, 180929, 183753,
    186776, 188864, 190396, 191607, 192583, 199985))
UPPER_SCHEDULE = tuple(Q(x, 1000000) for x in (
    138360, 155020, 158662, 171688, 177684, 180588,
    183402, 185486, 187011, 188221, 189137, 189137))
BANDS = (
    {"name": "lower_outer", "low": ALPHA1, "high": BOUNDARY,
     "eta": LOWER_ETA, "schedule": LOWER_SCHEDULE},
    {"name": "upper_outer", "low": BOUNDARY, "high": ALPHA2,
     "eta": UPPER_ETA, "schedule": UPPER_SCHEDULE},
)
SQUARE_GROUPS = 10761
A_GROUP_CHUNK = 250
B_RIGHT_ORBIT_CHUNK = 8
MAX_PROBE_WALL_SECONDS = 90
MAX_PROBE_RSS_KIB = 512 * 1024


def sha256(value):
    data = value if isinstance(value, bytes) else Path(value).read_bytes()
    return hashlib.sha256(data).hexdigest()


def strict_json(path):
    def pairs(items):
        answer = {}
        for key, value in items:
            if key in answer:
                raise ValueError(f"duplicate JSON key in {path}: {key}")
            answer[key] = value
        return answer
    return json.loads(Path(path).read_bytes(), object_pairs_hook=pairs,
                      parse_constant=lambda token: (_ for _ in ()).throw(
                          ValueError(f"nonfinite JSON token: {token}")))


def canonical_json(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"),
                       allow_nan=False) + "\n").encode("ascii")


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def snapshots():
    result = {}
    for path, expected in PINS.items():
        payload = path.read_bytes()
        if sha256(payload) != expected:
            raise RuntimeError(f"pinned exact-plan input changed: {path}")
        result[path] = payload
    return result


def validate_two_band():
    data = strict_json(TWO_BAND_RESULT)
    parameters = data.get("parameters", {})
    if (data.get("status") != "EXACT TWO-OUTER-BAND ANALYTIC SUPPORT PASS" or
            data.get("checker_sha256") != PINS[TWO_BAND_CHECKER] or
            parameters.get("alpha") != [
                "103/400", "263741/1000000", "237991/900000"] or
            parameters.get("A") != [
                "-3/400", "1/4", "256241/1000000", "231241/900000"] or
            tuple(Q(x) for x in parameters.get(
                "lower_schedule_through_first_empty", ())) != LOWER_SCHEDULE or
            tuple(Q(x) for x in parameters.get(
                "upper_schedule_through_first_empty", ())) != UPPER_SCHEDULE):
        raise ValueError("two-band analytic geometry mismatch")
    return data


def load_inputs():
    frontier = load("d18_two_band_plan_frontier", FRONTIER)
    dilation = load("d18_two_band_plan_dilation", DILATION)
    scan = load("d18_two_band_plan_scan", SCAN)
    scan.self_test()
    cert = strict_json(CERT)
    contraction = strict_json(CONTRACTION)
    validate_two_band()
    if (cert.get("format") != "bv-even-exact-vector-v1" or
            (cert.get("k"), cert.get("degree")) != (K, DEGREE) or
            cert.get("integrator_sha256") !=
            frontier.shell.PINNED[frontier.shell.EI_SRC / "exact_integrator.py"]):
        raise ValueError("refined D18 certificate identity mismatch")
    basis = tuple((int(a), tuple(int(x) for x in lam))
                  for a, lam in cert["basis"])
    vector = tuple(Q(x) for x in cert["rational_vector"])
    if (len(basis) != DIMENSION or len(vector) != DIMENSION or
            len(set(basis)) != DIMENSION or
            basis != tuple(frontier.ei.even_basis(DEGREE))):
        raise ValueError("refined D18 basis/vector inventory mismatch")
    expected = {
        "k": K, "alpha1": str(ALPHA1), "alpha2": str(ALPHA2),
        "eta1": "97/400", "eta2": str(UPPER_ETA),
        "delta": str(DELTA), "outer_c": str(ALPHA1 / ALPHA2),
    }
    if (contraction.get("format") !=
            "parameterized-d18-uncapped-pencil-exact-v1" or
            contraction.get("rigorous_values") is not True or
            contraction.get("parameters") != expected or
            Q(contraction["I_matrix"][0][0]) != Q(cert["exact_denominator"]) or
            Q(contraction["kJ_matrix"][0][0]) != Q(cert["exact_numerator"])):
        raise ValueError("exact inner/contraction identity mismatch")
    outer = tuple(dilation.dilate_vector(
        basis, vector, ALPHA1 / ALPHA2))
    terms = {(a, lam): coefficient for (a, lam), coefficient in
             zip(basis, outer) if coefficient}
    square = scan.square_orbit_polynomial(terms)
    if len(terms) != DIMENSION or len(square) != SQUARE_GROUPS:
        raise ArithmeticError("natural D18 orbit inventory changed")
    inner_i = Q(contraction["I_matrix"][0][0])
    inner_b = Q(contraction["kJ_matrix"][0][0])
    if inner_i - inner_b <= 0:
        raise ArithmeticError("inner deficit is not positive")
    return frontier, basis, vector, outer, square, inner_i, inner_b


def support(frontier, alpha, eta, schedule):
    return frontier.shell.ScheduledStratumSupport.make(
        K, Q(alpha), Q(eta), DELTA, tuple(schedule))


def active_counts(schedule):
    return tuple(r for r in range(K + 1)
                 if r == 0 or (r <= len(schedule) and
                               r * DELTA < schedule[r - 1]))


def band_a_slice(frontier, square, band, count, start, stop):
    ordered = sorted(square.items())
    if (type(count) is not int or count not in active_counts(band["schedule"]) or
            type(start) is not int or type(stop) is not int or
            not 0 <= start < stop <= len(ordered)):
        raise ValueError("invalid exact A slice")
    high = support(frontier, band["high"], band["eta"], band["schedule"])
    low = support(frontier, band["low"], band["eta"], band["schedule"])
    hi = lo = Q(0)
    for (power, orbit), coefficient in ordered[start:stop]:
        hi += coefficient * high.orbit_support_moment_in_stratum(
            orbit, power, count)
        lo += coefficient * low.orbit_support_moment_in_stratum(
            orbit, power, count)
    return hi, lo, hi - lo


def cross_face_orbit_slice_generic(
        frontier, basis, left_vector, right_vector, full, capped, common_eta,
        delta, common_r, h, branch, start, stop):
    """One exact J slice; production would sum all immutable slices.

    The left F marginal uses its direct full-simplex fiber.  The right H
    marginal uses one literal scheduled-support distinguished-coordinate
    branch.  Splitting by right marginal orbit is exactly additive.
    """
    k = full.k
    if (capped.k != k or full.delta != capped.delta or
            full.delta != delta or not full.is_full_simplex()):
        raise ValueError("cross slice support geometry mismatch")
    left_components = frontier.outer_core.components(
        basis, left_vector, k)
    right_components = frontier.outer_core.components(
        basis, right_vector, k)
    left, left_constraints = frontier.direct_full_simplex_marginal(
        full, left_components, common_r, h)
    right_all = frontier.outer_core.branch_polynomials(
        capped, right_components, common_r, h)
    if branch not in frontier.BRANCHES:
        raise ValueError("unknown right marginal branch")
    right = right_all[branch]
    right_constraints = capped._branch_constraints(common_r, h, branch)
    ordered = sorted(right.items())
    if (left_constraints is None or right_constraints is None or not left or
            not 0 <= start < stop <= len(ordered)):
        raise ValueError("empty or invalid exact b face slice")
    max_h = int(common_eta // delta) - common_r
    if not 0 <= h <= max_h:
        raise ValueError("h is outside the common face")
    outer_radius = common_eta - (common_r + h) * delta
    dummy = frontier.GroupedEvaluator(full, [], [], Q)
    domain = frontier.canonical_domain_key(
        dummy, k - 1, common_r, outer_radius,
        left_constraints + right_constraints)
    if domain is None:
        raise ValueError("selected exact b face has empty intersection")
    combined = {}
    pair_products = 0
    for left_orbit, left_poly in left.items():
        for right_orbit, right_poly in ordered[start:stop]:
            product = frontier.ei._poly_mul(left_poly, right_poly)
            for orbit, multiplicity in frontier.ei.multiply_monomial_orbits(
                    left_orbit, right_orbit):
                destination = combined.setdefault(orbit, defaultdict(Q))
                frontier.shell.add_poly(destination, product, Q(multiplicity))
                pair_products += 1
    total = defaultdict(Q)
    for orbit, polynomial in combined.items():
        density = dummy.orbit_density(
            k - 1, orbit, common_r, h, max_h)
        if density:
            frontier.shell.add_poly(
                total, frontier.ei._poly_mul(density, polynomial), Q(1))
    value = frontier.integrate_canonical_domain(dict(total), domain)
    dummy.clear_face_caches(clear_marginals=True)
    dummy.clear_radial_caches()
    return {
        "J_slice": value, "left_marginal_orbits": len(left),
        "right_marginal_orbits": len(ordered),
        "right_orbit_start": start, "right_orbit_stop": stop,
        "orbit_products_in_slice": pair_products,
        "combined_orbits": len(combined),
        "integrand_monomials": len(total),
    }


def cross_face_orbit_slice(frontier, basis, inner, outer, band, endpoint,
                           common_r, h, branch, start, stop):
    if endpoint not in ("low", "high"):
        raise ValueError("endpoint must be low or high")
    full = support(frontier, ALPHA1, band["eta"], (ALPHA1,) * K)
    capped = support(
        frontier, band[endpoint], band["eta"], band["schedule"])
    return cross_face_orbit_slice_generic(
        frontier, basis, inner, outer, full, capped, band["eta"], DELTA,
        common_r, h, branch, start, stop)


def exact_single_band_certificate_tests(a_values, b_values, inner_i, inner_b):
    if (len(a_values), len(b_values)) != (2, 2):
        raise ValueError("certificate inventory needs exactly two band tests")
    a = tuple(Q(x) for x in a_values)
    b = tuple(Q(x) for x in b_values)
    if min(a) <= 0:
        raise ArithmeticError("outer band I norm must be positive")
    deficit = Q(inner_i) - Q(inner_b)
    rows = []
    for band, aa, bb in zip(("lower_outer", "upper_outer"), a, b):
        energy = bb * bb / aa
        rows.append({"band": band, "captured_energy": energy,
                     "deficit": deficit, "margin": energy - deficit,
                     "passes": energy > deficit})
    return {
        "tests": rows, "any_single_band_passes": any(
            row["passes"] for row in rows),
        "energies_may_be_summed": False,
        "multiband_combination_requires":
            "exact outer 48J block or an independent sign proof",
    }


def stage_inventory():
    counts = {band["name"]: list(active_counts(band["schedule"]))
              for band in BANDS}
    a_chunks = math.ceil(SQUARE_GROUPS / A_GROUP_CHUNK)
    common_faces = {
        band["name"]: sum(
            int(band["eta"] // DELTA) - r + 1
            for r in range(max(active_counts(band["schedule"])) + 1))
        for band in BANDS
    }
    return {
        "logical_output_scalars": ["A_lower", "b_lower", "A_upper", "b_upper"],
        "certificate_use": "two separate one-band tests; never sum energies",
        "A": {
            "formula": (
                "sum_R sum_(p,nu) c_(p,nu) [M(high,B_j;p,nu,R)-"
                "M(low,B_j;p,nu,R)]"),
            "square_orbit_groups": SQUARE_GROUPS,
            "group_chunk": A_GROUP_CHUNK,
            "active_counts": counts,
            "immutable_slice_count": sum(
                len(row) * a_chunks for row in counts.values()),
        },
        "b": {
            "formula": (
                "48*sum_(r,h,q) integral D_(nu,r,h)(z,w) "
                "m_F^full(z,w)*m_H^q(z,w) over the exact common domain; "
                "take endpoint-high minus endpoint-low"),
            "common_face_count_per_endpoint": common_faces,
            "right_orbit_chunk": B_RIGHT_ORBIT_CHUNK,
            "distinguished_outer_branches": list((
                "Sdelta", "Stotal", "Ltotal", "Lbig")),
            "cross_factor_applied_only_by_assembler": 48,
        },
        "driver_policy": {
            "externally_bound_fresh_record_required": True,
            "immutable_shards": True,
            "resume_supported": False,
            "partial_record_after_failure_is_abandoned": True,
            "independent_reconstruction_required": True,
        },
    }


def bridge_gate():
    rows = [strict_json(path) for path in BRIDGE_RESULTS]
    expected_seeds = (2361817, 2361818)
    for row, seed in zip(rows, expected_seeds):
        calibration = row.get("mcmc_calibration", {})
        if (row.get("format") != "active25-d18-h2-bridge-v1" or
                row.get("status") != "H2-BRIDGE HEURISTIC CALIBRATED" or
                row.get("source_sha256") != PINS[BRIDGE] or
                row.get("schedule", {}).get("seed") != seed or
                row.get("parameters", {}).get("geometry") !=
                "d1over60_two_band_verified" or
                calibration.get("mixing_pass") is not True or
                calibration.get("cross_pass") is not True or
                row.get("launch_authorized") is not False or
                row.get("exact_target_started") is not False):
            raise ValueError("h2 bridge gate identity changed")
    estimates = [row["screen"]["capped_G_norm_over_inner_I"] for row in rows]
    errors = [row["screen"]["capped_G_norm_standard_error"] for row in rows]
    weights = [1 / (error * error) for error in errors]
    combined = sum(x * w for x, w in zip(estimates, weights)) / sum(weights)
    combined_se = math.sqrt(1 / sum(weights))
    threshold = rows[0]["screen"]["sufficient_threshold"]
    return {
        "rigorous": False, "seed_estimates": estimates,
        "seed_standard_errors": errors,
        "inverse_variance_combined": combined,
        "naive_combined_standard_error": combined_se,
        "single_band_sufficient_threshold_used_only_as_scale_reference":
            threshold,
        "summed_I_energy_minus_scale_reference_in_naive_SE":
            (combined - threshold) / combined_se,
        "summed_I_energy_is_a_multiband_certificate": False,
        "reason": (
            "Definition-5 cross-band J need not be positive semidefinite"),
        "decision": "DO_NOT_LAUNCH_NATURAL_D18_EXACT_TARGET",
        "can_be_reopened_by": [
            "independently calibrated D20 bridge above the exact-launch gate",
            "a materially stronger empirically calibrated cap-damped coordinate"],
    }


def preflight():
    start = snapshots()
    frontier, basis, vector, outer, square, inner_i, inner_b = load_inputs()
    if any(path.read_bytes() != payload for path, payload in start.items()):
        raise RuntimeError("exact-plan closure changed during preflight")
    return {
        "format": "active25-d18-two-band-minimal-exact-certificate-plan-v1",
        "status": "DISABLED_AFTER_HEURISTIC_GATE",
        "source_sha256": sha256(FILE),
        "dependency_sha256": {
            str(path.relative_to(REPO)): digest for path, digest in PINS.items()},
        "transitive_exact_engine_sha256": frontier.require_pins(),
        "separate_bases": [
            ["inner_refined_D18", "lower_outer_natural_D18"],
            ["inner_refined_D18", "upper_outer_natural_D18"]],
        "basis_dimension_per_test": 2,
        "inner_polynomial_terms": len(vector),
        "outer_polynomial_terms": len(outer),
        "square_orbit_groups": len(square),
        "natural_dilation": str(ALPHA1 / ALPHA2),
        "bands": [{key: ([str(x) for x in value]
                          if key == "schedule" else str(value)
                          if isinstance(value, Q) else value)
                   for key, value in band.items()} for band in BANDS],
        "inner_I": str(inner_i), "inner_48J": str(inner_b),
        "exact_sufficient_tests": [
            "b_lower^2/A_lower > inner_I-inner_48J",
            "b_upper^2/A_upper > inner_I-inner_48J"],
        "energies_may_be_summed": False,
        "multiband_J_counterexample": (
            "for eta_lower<s<=eta_upper the two-band cutoff kernel is "
            "[[0,1],[1,1]], with negative eigenvalue (1-sqrt(5))/2"),
        "outer_J_block_required_for_separate_single_band_tests": False,
        "outer_J_block_required_for_combined_multiband_test": True,
        "stage_inventory": stage_inventory(),
        "heuristic_launch_gate": bridge_gate(),
        "cost_probe_available": True,
        "cost_probe_is_production": False,
        "production_target_started": False,
        "launch_authorized": False,
        "resume_supported": False,
        "theorem_ready": False,
        "d20_ready_contract": {
            "same_full_simplex_inner_support": True,
            "expected_degree": 20, "expected_dimension": 707,
            "vector_requirement": (
                "externally pinned refined exact vector, or Decimal100 vector "
                "on one common rational grid with at least 40 decimal digits"),
            "limit_denominator_vector_forbidden": True,
            "d20_artifact_currently_bound": False,
        },
    }


def cost_probe():
    start = snapshots()
    started = time.monotonic()
    frontier, basis, vector, outer, square, _inner_i, _inner_b = load_inputs()
    reconstruction_seconds = time.monotonic() - started
    band = BANDS[0]
    probe_count = max(active_counts(band["schedule"]))
    a_started = time.monotonic()
    hi, lo, difference = band_a_slice(
        frontier, square, band, probe_count, 0, 8)
    a_seconds = time.monotonic() - a_started

    # A deterministic full-D18 cross slice: all left marginal orbits against
    # one right marginal orbit on the first nonempty r=10,h=4 branch.
    r, h = 10, 4
    chosen = None
    b_error = None
    for branch in frontier.BRANCHES:
        try:
            b_started = time.monotonic()
            candidate = cross_face_orbit_slice(
                frontier, basis, vector, outer, band, "high",
                r, h, branch, 0, 1)
            candidate["seconds"] = time.monotonic() - b_started
            candidate["common_r"] = r
            candidate["h"] = h
            candidate["right_branch"] = branch
            chosen = candidate
            break
        except ValueError as error:
            b_error = str(error)
    if chosen is None:
        raise RuntimeError(f"fixed exact cross probe has no live branch: {b_error}")
    elapsed = time.monotonic() - started
    if any(path.read_bytes() != payload for path, payload in start.items()):
        raise RuntimeError("exact-plan closure changed during cost probe")
    projected_a = (a_seconds / 8 * SQUARE_GROUPS *
                   sum(len(active_counts(band["schedule"])) for band in BANDS))
    b_branch_projection = (
        chosen["seconds"] * chosen["right_marginal_orbits"])
    maximum_b_branch_faces = (
        2 * len(frontier.BRANCHES) *
        sum(stage_inventory()["b"]["common_face_count_per_endpoint"].values()))
    maximum_b_projection = b_branch_projection * maximum_b_branch_faces
    return {
        "format": "active25-d18-two-band-exact-certificate-cost-probe-v1",
        "status": "BOUNDED EXACT COST PROBE ONLY",
        "source_sha256": sha256(FILE),
        "dependency_sha256": {
            str(path.relative_to(REPO)): digest for path, digest in PINS.items()},
        "probe": {
            "reconstruction_seconds": reconstruction_seconds,
            "A": {
                "band": band["name"], "count": probe_count,
                "square_group_start": 0, "square_group_stop": 8,
                "high_partial": str(hi), "low_partial": str(lo),
                "difference_partial": str(difference),
                "seconds": a_seconds,
                "linear_all_A_slice_projection_seconds": projected_a,
                "linear_all_A_slice_projection_hours": projected_a / 3600,
                "projection_warning": (
                    "single-count/slice linear extrapolation; not an authorization bound"),
            },
            "b": {
                **{key: (str(value) if isinstance(value, Q) else value)
                   for key, value in chosen.items()},
                "linear_full_fixed_face_branch_projection_seconds":
                    b_branch_projection,
                "maximum_branch_faces_across_bands_and_endpoints":
                    maximum_b_branch_faces,
                "linear_maximum_all_b_projection_seconds":
                    maximum_b_projection,
                "linear_maximum_all_b_projection_hours":
                    maximum_b_projection / 3600,
                "projection_warning": (
                    "one right-orbit slice extrapolated across variable faces; "
                    "a rough scale signal, never an authorization bound"),
            },
        },
        "wall_seconds": elapsed,
        "wall_limit_seconds": MAX_PROBE_WALL_SECONDS,
        "peak_rss_kib": int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss),
        "rss_limit_kib": MAX_PROBE_RSS_KIB,
        "production_target_started": False,
        "contains_partial_exact_integrals": True,
        "launch_authorized": False,
        "resume_supported": False,
        "theorem_ready": False,
    }


def apply_limits():
    soft, hard = resource.getrlimit(resource.RLIMIT_AS)
    cap = MAX_PROBE_RSS_KIB * 1024
    new_hard = hard if hard != resource.RLIM_INFINITY else cap
    resource.setrlimit(resource.RLIMIT_AS, (min(cap, new_hard), new_hard))
    signal.alarm(MAX_PROBE_WALL_SECONDS)


def publish_exclusive(path, payload):
    target = Path(path).resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())


def main():
    parser = argparse.ArgumentParser()
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--preflight-only", action="store_true")
    action.add_argument("--cost-probe", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    apply_limits()
    result = cost_probe() if args.cost_probe else preflight()
    payload = canonical_json(result)
    if args.output is not None:
        publish_exclusive(args.output, payload)
    elif args.cost_probe:
        parser.error("--cost-probe requires a fresh --output")
    sys.stdout.buffer.write(payload)


if __name__ == "__main__":
    main()
