#!/usr/bin/env python3
"""Independent exact proxy for two wide-C722 outer-cap schedules.

The target finite space is the certified BV D16 radial function plus one
constant on the full outer shell.  This script does *not* run that expensive
k=48 contraction.  It independently reconstructs the cross-support branch
formula, validates it literally at k=2, and prepares an exact k=30 radial-D4
proxy for both proposed schedules.  Below k=30 the high-plateau outer shell
is empty.  Target cost is estimated from a separately pinned completed run;
all output is discovery-only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import resource
import sys
import time
from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal, localcontext
from fractions import Fraction as Q
from pathlib import Path

if hasattr(sys, "set_int_max_str_digits"):
    sys.set_int_max_str_digits(0)

FILE = Path(__file__).resolve()
REPO = FILE.parents[3]
EI_DIR = REPO / "agents/exact-integrator"
sys.path[:0] = [str(EI_DIR / "src"), str(EI_DIR)]

import exact_integrator as ei  # noqa: E402
from grouped_fixed_vector import GroupedEvaluator, add_poly  # noqa: E402


INTEGRATOR_SHA256 = \
    "941ee82bc72fd8488a95eb5e536fe47f8c95d39a1b618dae7d6ef7eb27122e52"
GROUPED_SHA256 = \
    "47167e92a0f346e969706dc282ccb2dfd4ac31a0a75b654938ffbe8423cf4a4a"
CERTIFICATE_RELATIVE = \
    "agents/small-delta-frontier/bv_aquarter_B16_vector_exact.json"
CERTIFICATE_SHA256 = \
    "59715ddffa483c696c035634a81c3cc8ffe882e9d6eaceec74bea23996b72d62"
RADIAL_RELATIVE = \
    "agents/small-delta-frontier/bv_D16_radial_two_amplitudes_exact.json"
RADIAL_SHA256 = \
    "33fe5d555e736fe5ea3826d569477414fadd2d8a9defc2eaa35718a4f06f82ca"
COST_CALIBRATION_RELATIVE = (
    "agents/small-delta-frontier/results/"
    "full_bv_two_band_full_outer_constant_2x2_exact_v2.json")
COST_CALIBRATION_SHA256 = \
    "4a4d94f20ca5ae21a0fc83e874531299586db75e01ee357a16d1c1c9bdae0006"
SHELL_VOLUME_RELATIVE = (
    "agents/small-delta-frontier/results/"
    "wide_c722_outer_volume_comparison_v3.json")
SHELL_VOLUME_SHA256 = \
    "c9fefd5c06c02e6033e5a93666287597acfafa8ad575945c950ab9cb833f36a0"
ANALYTIC_AUDIT_HASHES = {
    "agents/audit/WIDE-C722-P172-ANALYTIC-AUDIT.md":
        "2948b4c0958e30b0f28a3c11f9e533397137d036ad8f05d8145cdd29a1255722",
    "agents/audit/verify_wide_c722_p172_analytic.py":
        "b0a972af7d5a708fe0cb52eabeb9a477f70606399743c4f6856559271ab7af06",
    "agents/audit/results/wide_c722_p172_analytic_audit.json":
        "5f43cbf346f5e3fbfe3dd4f908c8fdbb49ee5b4309ab3ff2e84d80d310b951eb",
    "agents/audit/WIDE-C722-VOLUME-RAMP-ANALYTIC-AUDIT.md":
        "f6c3eb4d1904fe670fdeb6459c8ab3e30428e6f29b63075f3937b47c59aa25c6",
    "agents/audit/verify_wide_c722_volume_ramp_analytic.py":
        "f6882dd2df8c0fa6eee900c12f31a9dce453603a948ac7c391c4ad62815bb5a4",
    "agents/audit/results/wide_c722_volume_ramp_analytic_audit.json":
        "88b6e1aeb04bd2e7d8600e5f4a7bcca8726b5307b95e5a4e9337a20c8f7afa96",
}

TARGET_K = 48
PROXY_K = 30
DELTA = Q(361, 50000)
ALPHA1 = Q(103, 400)
ETA1 = Q(97, 400)
ALPHA2 = Q(3211, 12000)
ETA2 = Q(3031, 12000)
BRANCHES = ("Sdelta", "Stotal", "Ltotal", "Lbig")
PROXY_BASIS = ((4, ()),)

MIN_PROXY_GAIN = Q(1, 100000)
MIN_PROXY_SCHEDULE_SEPARATION = Q(1, 10000000)
MAX_ESTIMATED_TARGET_WALL_SECONDS = Q(14400)
MAX_ESTIMATED_PROXY_WALL_SECONDS = Q(900)
MAX_PROXY_PEAK_RSS_KIB = 131072
MAX_PROXY_AGGREGATE_RSS_KIB = 262144


def sha256(path_or_bytes):
    data = (path_or_bytes if isinstance(path_or_bytes, bytes)
            else Path(path_or_bytes).read_bytes())
    return hashlib.sha256(data).hexdigest()


def canonical_json(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"),
                       allow_nan=False) + "\n").encode("ascii")


def high_plateau_schedule():
    return tuple(min(Q(11, 200) + (m - 1) * DELTA, Q(43, 250))
                 for m in range(1, 25))


def volume_ramp_schedule():
    return tuple(min(Q(49, 625) + (m - 1) * DELTA, Q(1599, 10000))
                 for m in range(1, 24))


SCHEDULES = {
    "high_plateau": high_plateau_schedule(),
    "volume_ramp": volume_ramp_schedule(),
}


@dataclass(frozen=True)
class ScheduledSupport(ei.OneStratumSupport):
    schedule: tuple = ()

    @classmethod
    def make(cls, k, alpha, delta, eta, schedule):
        schedule = tuple(Q(value) for value in schedule)
        if (isinstance(k, bool) or not isinstance(k, int) or k < 2 or
                not schedule or len(schedule) > k or
                any(value <= delta for value in schedule)):
            raise ValueError("invalid scheduled support")
        if any(right < left or right > left + delta
               for left, right in zip(schedule, schedule[1:])):
            raise ValueError("schedule violates B_m <= B_(m+1) <= B_m+delta")
        return cls(k, Q(alpha), Q(delta), Q(eta), schedule[0],
                   schedule[min(1, len(schedule) - 1)],
                   schedule[min(2, len(schedule) - 1)], schedule)

    def beta(self, r):
        if isinstance(r, bool) or not isinstance(r, int) or r <= 0:
            raise ValueError("beta requires a positive exact count")
        return self.schedule[min(r, len(self.schedule)) - 1]


def active_counts(schedule):
    schedule = tuple(schedule)
    return ((0,) + tuple(m for m, value in enumerate(schedule, 1)
                         if m * DELTA <= value))


def validate_schedules():
    expected = {"high_plateau": tuple(range(24)),
                "volume_ramp": tuple(range(23))}
    for name, schedule in SCHEDULES.items():
        support = ScheduledSupport.make(
            TARGET_K, ALPHA2, DELTA, ETA2, schedule)
        if active_counts(schedule) != expected[name]:
            raise ArithmeticError(f"{name} active-count inventory changed")
        first_empty = len(schedule)
        if not first_empty * DELTA > schedule[-1]:
            raise ArithmeticError(f"{name} does not end at first empty count")
        if support.max_large() != first_empty - 1:
            raise ArithmeticError(f"{name} support max-large changed")
    return True


def components(basis, vector, k):
    if len(basis) != len(vector):
        raise ValueError("basis/vector lengths differ")
    out = defaultdict(Q)
    for coefficient, (residual, partition) in zip(vector, basis):
        for exponent, rest in ei.OneStratumSupport.split_at_distinguished(
                tuple(partition), k):
            out[(rest, exponent, residual)] += Q(coefficient)
    return tuple((rest, exponent, residual, coefficient)
                 for (rest, exponent, residual), coefficient in out.items()
                 if coefficient)


def branch_polynomials(support, component_list, r, h):
    answer = {}
    for branch in BRANCHES:
        if support._branch_constraints(r, h, branch) is None:
            answer[branch] = {}
            continue
        block = {}
        for rest, exponent, residual, coefficient in component_list:
            polynomial = dict(support._marginal_poly(
                r, h, branch, exponent, residual))
            if polynomial:
                destination = block.setdefault(rest, defaultdict(Q))
                add_poly(destination, polynomial, coefficient)
        answer[branch] = {
            orbit: dict(polynomial) for orbit, polynomial in block.items()
            if polynomial
        }
    return answer


def cross_marginal(left_support, left_components,
                   right_support, right_components, common_eta,
                   *, return_by_r=False):
    """Exact J cross form from independently intersected literal branches."""
    if (left_support.k != right_support.k or
            left_support.delta != right_support.delta):
        raise ValueError("cross supports disagree in k or delta")
    dimension = left_support.k - 1
    dummy = GroupedEvaluator(left_support, [], [], Q)
    max_r = min(dimension, left_support.max_large(),
                right_support.max_large())
    by_r = []
    integral_calls = 0
    for r in range(max_r + 1):
        subtotal = Q(0)
        max_h = int(Q(common_eta) // left_support.delta) - r
        if max_h < 0:
            by_r.append(Q(0))
            continue
        for h in range(max_h + 1):
            outer = Q(common_eta) - (r + h) * left_support.delta
            if outer <= 0:
                continue
            left = branch_polynomials(
                left_support, left_components, r, h)
            right = branch_polynomials(
                right_support, right_components, r, h)
            for left_branch in BRANCHES:
                if not left[left_branch]:
                    continue
                left_constraints = left_support._branch_constraints(
                    r, h, left_branch)
                if left_constraints is None:
                    continue
                for right_branch in BRANCHES:
                    if not right[right_branch]:
                        continue
                    right_constraints = right_support._branch_constraints(
                        r, h, right_branch)
                    if right_constraints is None:
                        continue
                    combined = defaultdict(lambda: defaultdict(Q))
                    for left_orbit, left_poly in left[left_branch].items():
                        for right_orbit, right_poly in right[right_branch].items():
                            product = ei._poly_mul(left_poly, right_poly)
                            for orbit, multiplicity in \
                                    ei.multiply_monomial_orbits(
                                        left_orbit, right_orbit):
                                add_poly(combined[orbit], product,
                                         Q(multiplicity))
                    integrand = defaultdict(Q)
                    for orbit, marginal_poly in combined.items():
                        density = dummy.orbit_density(
                            dimension, orbit, r, h, max_h)
                        if density:
                            add_poly(integrand, ei._poly_mul(
                                density, marginal_poly), Q(1))
                    # For k much smaller than eta/delta, inclusion-exclusion
                    # faces past the physical dimension have zero density.
                    if not integrand:
                        continue
                    subtotal += dummy.integrate_domain(
                        dict(integrand), dimension, r, outer,
                        left_constraints + right_constraints)
                    integral_calls += 1
            dummy.clear_face_caches(clear_marginals=True)
        dummy.clear_radial_caches()
        by_r.append(subtotal)
    answer = sum(by_r, Q(0))
    if return_by_r:
        return answer, tuple(by_r), integral_calls
    return answer


def constant_marginal_k2(support, common):
    """Literal t-length from Definition 1 for a k=2 constant function."""
    remaining = support.alpha - common
    if remaining <= 0 or common < 0:
        return Q(0)
    if common <= support.delta:
        return max(Q(0), min(remaining, support.beta(1)))
    if common > support.beta(1):
        return Q(0)
    small = max(Q(0), min(support.delta, remaining))
    large_upper = min(remaining, support.beta(2) - common)
    large = max(Q(0), large_upper - support.delta)
    return small + large


def literal_constant_cross_k2(left, right, eta):
    points = {Q(0), Q(eta)}
    for support in (left, right):
        points.update((
            support.delta, support.alpha,
            support.alpha - support.delta,
            support.alpha - support.beta(1), support.beta(1),
            support.beta(2) - support.delta, support.beta(2)))
    points = sorted(value for value in points if 0 <= value <= eta)
    answer = Q(0)
    for lo, hi in zip(points, points[1:]):
        if hi <= lo:
            continue
        x1, x2 = (2 * lo + hi) / 3, (lo + 2 * hi) / 3
        left1, left2 = (constant_marginal_k2(left, x1),
                        constant_marginal_k2(left, x2))
        right1, right2 = (constant_marginal_k2(right, x1),
                          constant_marginal_k2(right, x2))
        left_slope = (left2 - left1) / (x2 - x1)
        right_slope = (right2 - right1) / (x2 - x1)
        left_zero = left1 - left_slope * x1
        right_zero = right1 - right_slope * x1
        midpoint = (lo + hi) / 2
        if (constant_marginal_k2(left, midpoint) !=
                left_zero + left_slope * midpoint or
                constant_marginal_k2(right, midpoint) !=
                right_zero + right_slope * midpoint):
            raise AssertionError("literal marginal breakpoint is incomplete")
        answer += (
            left_zero * right_zero * (hi - lo) +
            (left_zero * right_slope + left_slope * right_zero) *
            (hi ** 2 - lo ** 2) / 2 +
            left_slope * right_slope * (hi ** 3 - lo ** 3) / 3)
    return answer


def low_k_signed_literal_tests():
    delta = Q(1, 20)
    eta = Q(1, 5)
    left = ScheduledSupport.make(
        2, Q(6, 25), delta, eta, (Q(4, 25), Q(9, 50)))
    right = ScheduledSupport.make(
        2, Q(13, 50), delta, eta, (Q(9, 50), Q(1, 5)))
    one = (((), 0, 0, Q(1)),)
    got = cross_marginal(left, one, right, one, eta)
    literal = literal_constant_cross_k2(left, right, eta)
    if got != literal or got != cross_marginal(
            right, one, left, one, eta):
        raise AssertionError("k=2 literal cross/symmetry regression failed")

    labels = ((0, ()), (1, ()), (0, (2,)))
    vector = (Q(2), Q(-3), Q(5))
    got_signed = cross_marginal(
        left, components(labels, vector, 2),
        left, components(labels, vector, 2), eta)
    expected_signed = sum(
        vector[i] * vector[j] * left.basis_j(labels[i], labels[j])
        for i in range(len(labels)) for j in range(len(labels)))
    if got_signed != expected_signed:
        raise AssertionError("signed orbit/canonical k=2 regression failed")

    high = ScheduledSupport.make(
        2, Q(6, 25), delta, eta, (Q(6, 25), Q(6, 25)))
    low = ScheduledSupport.make(
        2, Q(11, 50), delta, eta, (Q(6, 25), Q(6, 25)))
    hh = cross_marginal(high, one, high, one, eta)
    hl = cross_marginal(high, one, low, one, eta)
    ll = cross_marginal(low, one, low, one, eta)
    shell = hh - 2 * hl + ll
    if shell <= 0 or Q(2) * shell == shell:
        raise AssertionError("polarization or kJ factor regression failed")
    return {"literal_cross": str(got), "signed_self": str(got_signed),
            "shell_j": str(shell), "k2_shell_numerator": str(2 * shell)}


def validate_sources():
    expected = {
        Path(ei.__file__).resolve(): INTEGRATOR_SHA256,
        (EI_DIR / "grouped_fixed_vector.py").resolve(): GROUPED_SHA256,
        (REPO / CERTIFICATE_RELATIVE).resolve(): CERTIFICATE_SHA256,
        (REPO / RADIAL_RELATIVE).resolve(): RADIAL_SHA256,
        (REPO / COST_CALIBRATION_RELATIVE).resolve():
            COST_CALIBRATION_SHA256,
        (REPO / SHELL_VOLUME_RELATIVE).resolve(): SHELL_VOLUME_SHA256,
    }
    expected.update({(REPO / relative).resolve(): digest
                     for relative, digest in ANALYTIC_AUDIT_HASHES.items()})
    for path, digest in expected.items():
        if sha256(path) != digest:
            raise RuntimeError(f"pinned source changed: {path}")
    return {str(path.relative_to(REPO)): digest
            for path, digest in expected.items()}


def exact_target_shell_masses():
    """Reconstruct the two constant-shell I entries at k=48 exactly."""
    comparison = json.loads((REPO / SHELL_VOLUME_RELATIVE).read_bytes())
    if (comparison.get("status") != "exact-shell-volume-comparison-pass" or
            comparison.get("integrator_sha256") != INTEGRATOR_SHA256 or
            comparison.get("parameters") != {
                "alpha1": str(ALPHA1), "alpha2": str(ALPHA2),
                "delta": str(DELTA), "epsilon": "3/400",
                "eta2": str(ETA2), "k": TARGET_K}):
        raise ValueError("pinned exact shell-volume artifact changed schema")
    artifact_keys = {"high_plateau": "balanced",
                     "volume_ramp": "volume_ramp"}
    answer = {}
    for name, schedule in SCHEDULES.items():
        hi = ScheduledSupport.make(
            TARGET_K, ALPHA2, DELTA, ETA2, schedule)
        lo = ScheduledSupport.make(
            TARGET_K, ALPHA1, DELTA, ETA2, schedule)
        mass = (hi.basis_m1((0, ()), (0, ())) -
                lo.basis_m1((0, ()), (0, ())))
        block = comparison[artifact_keys[name]]
        if (tuple(Q(value) for value in block["schedule"]) != schedule or
                tuple(block["active_counts"]) != active_counts(schedule) or
                Q(block["exact_I_shell"]) != mass or mass <= 0):
            raise ArithmeticError(
                f"{name} exact shell mass does not match pinned reconstruction")
        answer[name] = mass
    return answer


def outer_coordinate_complexity():
    """Count grouped components for the optional same-BV outer coordinate.

    This is a cost assessment, not a quotient comparison.  The same BV D16
    polynomial is a mathematically valid second outer coordinate, but its
    grouped marginal blocks are not comparable in cost to one constant.
    """
    certificate = json.loads((REPO / CERTIFICATE_RELATIVE).read_bytes())
    basis = tuple((int(residual), tuple(int(x) for x in partition))
                  for residual, partition in certificate["basis"])
    vector = tuple(Q(value) for value in certificate["rational_vector"])
    if len(basis) != 307 or len(vector) != 307:
        raise ValueError("BV D16 coordinate inventory changed")
    bv_components = components(basis, vector, TARGET_K)
    rest_orbits = len({rest for rest, _, _, _ in bv_components})
    if len(bv_components) != 769 or rest_orbits != 67:
        raise ArithmeticError("BV D16 marginal component inventory changed")
    return {
        "constant": {"basis_terms": 1, "marginal_components": 1,
                     "rest_orbits": 1},
        "same_bv_d16": {"basis_terms": len(basis),
                         "marginal_components": len(bv_components),
                         "rest_orbits": rest_orbits},
        "raw_rest_orbit_pair_ratio_cross_vs_constant": rest_orbits,
        "raw_rest_orbit_pair_ratio_self_vs_constant": rest_orbits ** 2,
        "same_bv_d16_is_cheap": False,
        "initial_coordinate": "constant_full_outer_shell",
        "reason": (
            "The constant shell has one marginal rest orbit. Reusing F0 has "
            "67 rest orbits (769 distinguished components), so a base/F0 "
            "cross exposes 67 times and an F0/F0 self block 4489 times as "
            "many raw rest-orbit pairs before polynomial expansion."),
    }


def load_radial_base():
    certificate = json.loads((REPO / CERTIFICATE_RELATIVE).read_bytes())
    radial = json.loads((REPO / RADIAL_RELATIVE).read_bytes())
    if (radial.get("certificate_sha256") != CERTIFICATE_SHA256 or
            radial.get("integrator_sha256") != INTEGRATOR_SHA256 or
            radial.get("R") != str(ALPHA1) or
            radial.get("V") != str(ETA1) or
            certificate.get("k") != TARGET_K or
            certificate.get("degree") != 16):
        raise ValueError("certified BV radial provenance changed")
    amplitudes = tuple(Q(value) for value in radial["rational_amplitudes"])
    if len(amplitudes) != 2 or amplitudes[0] != 1:
        raise ValueError("certified BV radial amplitudes changed")
    matrix_i = [[Q(value) for value in row] for row in radial["I_matrix"]]
    matrix_b = [[Q(value) for value in row] for row in radial["kJ_matrix"]]
    denominator = sum(amplitudes[i] * matrix_i[i][j] * amplitudes[j]
                      for i in range(2) for j in range(2))
    numerator = sum(amplitudes[i] * matrix_b[i][j] * amplitudes[j]
                    for i in range(2) for j in range(2))
    if (denominator != Q(radial["exact_denominator"]) or
            numerator != Q(radial["exact_numerator"]) or
            numerator / denominator != Q(radial["exact_quotient"])):
        raise ArithmeticError("certified radial form contraction changed")
    return {"amplitudes": amplitudes, "denominator": denominator,
            "numerator": numerator,
            "quotient": numerator / denominator}


def decimal_root(a00, a11, b00, b01, b11, precision=120):
    with localcontext() as context:
        context.prec = precision

        def decimal(value):
            return Decimal(value.numerator) / Decimal(value.denominator)

        left = decimal(b00) / decimal(a00)
        right = decimal(b11) / decimal(a11)
        coupling = decimal(b01) ** 2 / (decimal(a00) * decimal(a11))
        root = (left + right +
                ((left - right) ** 2 + 4 * coupling).sqrt()) / 2
        ratio = ((root * decimal(a00) - decimal(b00)) / decimal(b01)
                 if b01 else Decimal(0))
        return root, ratio


def proxy_base_forms(k, amplitudes):
    inner_amplitude, outer_amplitude = amplitudes
    difference = inner_amplitude - outer_amplitude
    full_r = ei.OneStratumSupport(
        k, ALPHA1, DELTA, ETA1, ALPHA1, ALPHA1, ALPHA1)
    full_v = ei.OneStratumSupport(
        k, ETA1, DELTA, ETA1, ETA1, ETA1, ETA1)
    label = PROXY_BASIS[0]
    i_r = full_r.basis_m1(label, label)
    i_v = full_v.basis_m1(label, label)
    denominator = (outer_amplitude ** 2 * i_r +
                   (inner_amplitude ** 2 - outer_amplitude ** 2) * i_v)
    component = components(PROXY_BASIS, (Q(1),), k)
    rr, _, n_rr = cross_marginal(
        full_r, component, full_r, component, ETA1, return_by_r=True)
    rv, _, n_rv = cross_marginal(
        full_r, component, full_v, component, ETA1, return_by_r=True)
    vv, _, n_vv = cross_marginal(
        full_v, component, full_v, component, ETA1, return_by_r=True)
    j_value = (outer_amplitude ** 2 * rr +
               2 * outer_amplitude * difference * rv +
               difference ** 2 * vv)
    return {
        "denominator": denominator, "numerator": k * j_value,
        "component": component, "full_r": full_r, "full_v": full_v,
        "integral_calls": n_rr + n_rv + n_vv,
    }


def proxy_schedule_forms(name, schedule, base, amplitudes, k):
    started = time.monotonic()
    inner_amplitude, outer_amplitude = amplitudes
    difference = inner_amplitude - outer_amplitude
    prefix = tuple(schedule[:k])
    outer_hi = ScheduledSupport.make(k, ALPHA2, DELTA, ETA2, prefix)
    outer_lo = ScheduledSupport.make(k, ALPHA1, DELTA, ETA2, prefix)
    one = (((), 0, 0, Q(1)),)
    component = base["component"]
    values = {}
    counts = {}
    by_r = {}
    for tag, left_support, left_component, right_support, right_component in (
            ("rr", base["full_r"], component, outer_hi, one),
            ("rl", base["full_r"], component, outer_lo, one),
            ("vr", base["full_v"], component, outer_hi, one),
            ("vl", base["full_v"], component, outer_lo, one),
            ("hh", outer_hi, one, outer_hi, one),
            ("hl", outer_hi, one, outer_lo, one),
            ("ll", outer_lo, one, outer_lo, one)):
        value, strata, count = cross_marginal(
            left_support, left_component, right_support, right_component,
            ETA2, return_by_r=True)
        values[tag], counts[tag], by_r[tag] = value, count, strata
    cross_j = (outer_amplitude * (values["rr"] - values["rl"]) +
               difference * (values["vr"] - values["vl"]))
    shell_j = values["hh"] - 2 * values["hl"] + values["ll"]
    a00, b00 = base["denominator"], base["numerator"]
    a11 = (outer_hi.basis_m1((0, ()), (0, ())) -
           outer_lo.basis_m1((0, ()), (0, ())))
    b01, b11 = k * cross_j, k * shell_j
    if a00 <= 0 or a11 <= 0 or b11 <= 0:
        raise ArithmeticError(f"{name} proxy has nonpositive form")
    root120, ratio120 = decimal_root(a00, a11, b00, b01, b11, 120)
    root200, ratio200 = decimal_root(a00, a11, b00, b01, b11, 200)
    if abs(root120 - root200) > Decimal("1e-105"):
        raise ArithmeticError("proxy root is precision-unstable")
    rational_ratio = Q(format(ratio200, ".60E"))
    denominator = a00 + rational_ratio ** 2 * a11
    numerator = (b00 + 2 * rational_ratio * b01 +
                 rational_ratio ** 2 * b11)
    quotient = numerator / denominator
    return {
        "name": name, "schedule_prefix": [str(value) for value in prefix],
        "I_matrix": [[str(a00), "0"], ["0", str(a11)]],
        "kJ_matrix": [[str(b00), str(b01)], [str(b01), str(b11)]],
        "root_decimal_120": str(root120),
        "root_decimal_200": str(root200),
        "rational_vector": ["1", str(rational_ratio)],
        "exact_denominator": str(denominator),
        "exact_numerator": str(numerator),
        "exact_quotient": str(quotient),
        "exact_gain": str(quotient - b00 / a00),
        "integral_calls": counts,
        "by_r_lengths": {tag: len(items) for tag, items in by_r.items()},
        "elapsed_seconds": time.monotonic() - started,
    }


def geometric_call_upper(left, right, common_eta):
    """Support-only upper bound on nonempty branch-pair integrations."""
    dimension = left.k - 1
    max_r = min(dimension, left.max_large(), right.max_large())
    calls = 0
    faces = 0
    by_r = []
    for r in range(max_r + 1):
        subtotal = 0
        max_h = min(dimension - r,
                    int(Q(common_eta) // left.delta) - r)
        for h in range(max_h + 1):
            if Q(common_eta) - (r + h) * left.delta <= 0:
                continue
            faces += 1
            left_branches = sum(
                left._branch_constraints(r, h, branch) is not None
                for branch in BRANCHES)
            right_branches = sum(
                right._branch_constraints(r, h, branch) is not None
                for branch in BRANCHES)
            subtotal += left_branches * right_branches
        by_r.append(subtotal)
        calls += subtotal
    return {"faces": faces, "branch_pair_upper": calls,
            "by_r": by_r}


def target_geometry_estimate(schedule):
    full_r = ei.OneStratumSupport(
        TARGET_K, ALPHA1, DELTA, ETA2, ALPHA1, ALPHA1, ALPHA1)
    full_v = ei.OneStratumSupport(
        TARGET_K, ETA1, DELTA, ETA2, ETA1, ETA1, ETA1)
    outer_hi = ScheduledSupport.make(
        TARGET_K, ALPHA2, DELTA, ETA2, schedule)
    outer_lo = ScheduledSupport.make(
        TARGET_K, ALPHA1, DELTA, ETA2, schedule)
    supports = {
        "rr": (full_r, outer_hi), "rl": (full_r, outer_lo),
        "vr": (full_v, outer_hi), "vl": (full_v, outer_lo),
        "hh": (outer_hi, outer_hi), "hl": (outer_hi, outer_lo),
        "ll": (outer_lo, outer_lo),
    }
    return {tag: geometric_call_upper(left, right, ETA2)
            for tag, (left, right) in supports.items()}


def proxy_geometry_estimate():
    full_r_base = ei.OneStratumSupport(
        PROXY_K, ALPHA1, DELTA, ETA1, ALPHA1, ALPHA1, ALPHA1)
    full_v_base = ei.OneStratumSupport(
        PROXY_K, ETA1, DELTA, ETA1, ETA1, ETA1, ETA1)
    base = {
        "rr": geometric_call_upper(full_r_base, full_r_base, ETA1),
        "rv": geometric_call_upper(full_r_base, full_v_base, ETA1),
        "vv": geometric_call_upper(full_v_base, full_v_base, ETA1),
    }
    schedules = {}
    for name, schedule in SCHEDULES.items():
        prefix = schedule[:PROXY_K]
        full_r = ei.OneStratumSupport(
            PROXY_K, ALPHA1, DELTA, ETA2, ALPHA1, ALPHA1, ALPHA1)
        full_v = ei.OneStratumSupport(
            PROXY_K, ETA1, DELTA, ETA2, ETA1, ETA1, ETA1)
        outer_hi = ScheduledSupport.make(
            PROXY_K, ALPHA2, DELTA, ETA2, prefix)
        outer_lo = ScheduledSupport.make(
            PROXY_K, ALPHA1, DELTA, ETA2, prefix)
        supports = {
            "rr": (full_r, outer_hi), "rl": (full_r, outer_lo),
            "vr": (full_v, outer_hi), "vl": (full_v, outer_lo),
            "hh": (outer_hi, outer_hi), "hl": (outer_hi, outer_lo),
            "ll": (outer_lo, outer_lo),
        }
        schedules[name] = {
            tag: geometric_call_upper(left, right, ETA2)
            for tag, (left, right) in supports.items()
        }
    total = (sum(item["branch_pair_upper"] for item in base.values()) +
             sum(item["branch_pair_upper"]
                 for block in schedules.values() for item in block.values()))
    return {"base": base, "schedules": schedules,
            "total_branch_pair_upper": total}


def build_cost_probe():
    """Time one exact D4 cross form and extrapolate the full k=30 proxy."""
    started = time.monotonic()
    sources = validate_sources()
    validate_schedules()
    low_k = low_k_signed_literal_tests()
    full_r = ei.OneStratumSupport(
        PROXY_K, ALPHA1, DELTA, ETA2, ALPHA1, ALPHA1, ALPHA1)
    outer_hi = ScheduledSupport.make(
        PROXY_K, ALPHA2, DELTA, ETA2,
        SCHEDULES["high_plateau"][:PROXY_K])
    component = components(PROXY_BASIS, (Q(1),), PROXY_K)
    one = (((), 0, 0, Q(1)),)
    contraction_started = time.monotonic()
    value, by_r, calls = cross_marginal(
        full_r, component, outer_hi, one, ETA2, return_by_r=True)
    contraction_seconds = time.monotonic() - contraction_started
    geometry = proxy_geometry_estimate()
    if calls != geometry["schedules"]["high_plateau"]["rr"][
            "branch_pair_upper"]:
        raise ArithmeticError("cost-probe call count differs from geometry")
    seconds_per_call = Q(str(contraction_seconds)) / calls
    estimated = (seconds_per_call *
                 geometry["total_branch_pair_upper"] * Q(3, 2))
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return {
        "status": "wide-hybrid-D4-k30-cost-probe-complete",
        "rigorous": False,
        "theorem_ready": False,
        "script_sha256": sha256(FILE),
        "source_hashes": sources,
        "low_k_signed_literal": low_k,
        "probe": {
            "k": PROXY_K, "radial_degree": 4,
            "schedule": "high_plateau", "cross_tag": "rr",
            "exact_value": str(value), "branch_calls": calls,
            "nonzero_common_strata": sum(item != 0 for item in by_r),
            "contraction_seconds": contraction_seconds,
            "peak_rss_kib": peak,
        },
        "full_proxy_geometry": geometry,
        "extrapolation": {
            "seconds_per_branch_call": str(seconds_per_call),
            "safety_factor": "3/2",
            "estimated_wall_seconds": str(estimated),
            "estimated_wall_seconds_decimal": format(float(estimated), ".6f"),
            "maximum_wall_seconds": str(MAX_ESTIMATED_PROXY_WALL_SECONDS),
            "maximum_peak_rss_kib": MAX_PROXY_PEAK_RSS_KIB,
            "resource_gate_pass": (
                estimated <= MAX_ESTIMATED_PROXY_WALL_SECONDS and
                peak <= MAX_PROXY_PEAK_RSS_KIB),
        },
        "target_k48_integration_run": False,
        "proxy_quotient_run": False,
        "wall_seconds": time.monotonic() - started,
        "peak_rss_kib": peak,
    }


def parallel_proxy_resource_estimate(cost_probe):
    """Exact rational extrapolation for one schedule in each of two processes."""
    if (cost_probe.get("status") !=
            "wide-hybrid-D4-k30-cost-probe-complete" or
            cost_probe.get("script_sha256") != sha256(FILE) or
            cost_probe.get("target_k48_integration_run") is not False or
            cost_probe.get("proxy_quotient_run") is not False):
        raise ValueError("cost probe is not bound to this frozen evaluator")
    geometry = proxy_geometry_estimate()
    if cost_probe.get("full_proxy_geometry") != geometry:
        raise ArithmeticError("cost probe geometry differs from reconstruction")
    calls = int(cost_probe["probe"]["branch_calls"])
    seconds = Q(str(cost_probe["probe"]["contraction_seconds"]))
    if calls != 7008 or seconds <= 0:
        raise ValueError("cost probe calibration datum changed")
    rate = seconds / calls
    base_calls = sum(value["branch_pair_upper"]
                     for value in geometry["base"].values())
    per_schedule = {
        name: base_calls + sum(value["branch_pair_upper"]
                               for value in block.values())
        for name, block in geometry["schedules"].items()
    }
    wall = {name: rate * count * Q(3, 2)
            for name, count in per_schedule.items()}
    peak = int(cost_probe["probe"]["peak_rss_kib"])
    aggregate_peak = 2 * peak
    gate = (max(wall.values()) <= MAX_ESTIMATED_PROXY_WALL_SECONDS and
            peak <= MAX_PROXY_PEAK_RSS_KIB and
            aggregate_peak <= MAX_PROXY_AGGREGATE_RSS_KIB)
    return {
        "process_count": 2,
        "one_schedule_per_process": True,
        "base_recomputed_in_each_process": True,
        "branch_calls_per_process": per_schedule,
        "seconds_per_branch_call": str(rate),
        "linear_safety_factor": "3/2",
        "estimated_wall_seconds_per_process": {
            name: str(value) for name, value in wall.items()},
        "estimated_parallel_wall_seconds": str(max(wall.values())),
        "measured_peak_rss_kib_per_process": peak,
        "estimated_aggregate_peak_rss_kib": aggregate_peak,
        "maximum_wall_seconds": str(MAX_ESTIMATED_PROXY_WALL_SECONDS),
        "maximum_peak_rss_kib_per_process": MAX_PROXY_PEAK_RSS_KIB,
        "maximum_aggregate_peak_rss_kib": MAX_PROXY_AGGREGATE_RSS_KIB,
        "resource_gate_pass": gate,
    }


def resource_estimate(target_geometry):
    calibration = json.loads(
        (REPO / COST_CALIBRATION_RELATIVE).read_bytes())
    counts = calibration["branch_integral_counts"]
    old_calls = sum(int(value) for value in counts.values())
    if old_calls <= 0 or calibration["elapsed_seconds"] <= 0:
        raise ValueError("cost calibration metadata is invalid")
    calls = sum(item["branch_pair_upper"]
                for item in target_geometry.values())
    seconds_per_call = Q(str(calibration["elapsed_seconds"])) / old_calls
    # Upper geometry counts include some algebraically empty branches, while
    # the smaller delta increases polynomial density complexity.  Use a 3/2
    # safety factor rather than presenting the linear extrapolation as exact.
    wall = seconds_per_call * calls * Q(3, 2)
    return {
        "calibration_elapsed_seconds": calibration["elapsed_seconds"],
        "calibration_branch_calls": old_calls,
        "target_branch_pair_upper": calls,
        "linear_safety_factor": "3/2",
        "estimated_wall_seconds": str(wall),
        "estimated_wall_hours_decimal": format(float(wall / 3600), ".6f"),
        "calibration_peak_rss_kib": calibration["peak_rss_kib"],
        "projected_peak_rss_kib": 131072,
    }


def build_result():
    started = time.monotonic()
    sources = validate_sources()
    validate_schedules()
    low_k = low_k_signed_literal_tests()
    radial = load_radial_base()
    shell_masses = exact_target_shell_masses()
    coordinate_cost = outer_coordinate_complexity()
    proxy_base = proxy_base_forms(PROXY_K, radial["amplitudes"])
    proxy = {
        name: proxy_schedule_forms(
            name, schedule, proxy_base, radial["amplitudes"], PROXY_K)
        for name, schedule in SCHEDULES.items()
    }
    proxy_quotients = {
        name: Q(value["exact_quotient"]) for name, value in proxy.items()}
    proxy_gains = {name: Q(value["exact_gain"])
                   for name, value in proxy.items()}
    ranked = sorted(proxy_quotients,
                    key=lambda name: proxy_quotients[name], reverse=True)
    separation = proxy_quotients[ranked[0]] - proxy_quotients[ranked[1]]
    geometry = {name: target_geometry_estimate(schedule)
                for name, schedule in SCHEDULES.items()}
    resources = {name: resource_estimate(geometry[name])
                 for name in SCHEDULES}
    best = ranked[0]
    math_gate = (proxy_gains[best] >= MIN_PROXY_GAIN and
                 separation >= MIN_PROXY_SCHEDULE_SEPARATION)
    resource_gate = (Q(resources[best]["estimated_wall_seconds"]) <=
                     MAX_ESTIMATED_TARGET_WALL_SECONDS)
    return {
        "status": "wide-hybrid-outer-constant-proxy-complete",
        "rigorous": False,
        "theorem_ready": False,
        "target_k48_integration_run": False,
        "target_launch_authorized": False,
        "scope": (
            "Exact k=30 radial-D4 schedule sensitivity and support-only k=48 "
            "cost estimate; not the BV D16 target quotient."),
        "script_sha256": sha256(FILE),
        "source_hashes": sources,
        "parameters": {
            "delta": str(DELTA), "alpha1": str(ALPHA1),
            "eta1": str(ETA1), "alpha2": str(ALPHA2),
            "eta2": str(ETA2),
        },
        "schedules": {
            name: {"caps": [str(value) for value in schedule],
                   "active_counts": list(active_counts(schedule))}
            for name, schedule in SCHEDULES.items()},
        "certified_radial_base": {
            "k": TARGET_K, "degree": 16,
            "denominator": str(radial["denominator"]),
            "numerator": str(radial["numerator"]),
            "quotient": str(radial["quotient"]),
            "amplitudes": [str(value) for value in radial["amplitudes"]],
        },
        "low_k_signed_literal": low_k,
        "exact_target_constant_shell_I": {
            name: str(value) for name, value in shell_masses.items()},
        "outer_coordinate_cost_assessment": coordinate_cost,
        "proxy": {"k": PROXY_K, "radial_degree": 4,
                  "base_denominator": str(proxy_base["denominator"]),
                  "base_numerator": str(proxy_base["numerator"]),
                  "base_integral_calls": proxy_base["integral_calls"],
                  "schedules": proxy,
                  "ranking": ranked,
                  "best_minus_other": str(separation)},
        "target_geometry_upper": geometry,
        "resource_estimates": resources,
        "continuation_gate": {
            "minimum_exact_proxy_gain": str(MIN_PROXY_GAIN),
            "minimum_exact_schedule_separation":
                str(MIN_PROXY_SCHEDULE_SEPARATION),
            "maximum_estimated_target_wall_seconds":
                str(MAX_ESTIMATED_TARGET_WALL_SECONDS),
            "mathematical_gate_pass": math_gate,
            "resource_gate_pass": resource_gate,
            "independent_formula_audit_required": True,
            "session_11209_must_be_finished": True,
            "separate_root_authorization_required": True,
            "recommended_schedule_if_all_gates_pass": best,
            "target_launch_authorized": False,
        },
        "wall_seconds": time.monotonic() - started,
        "peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
    }


def build_one_schedule_result(name):
    """Evaluate one proxy so the two schedules can run in parallel later."""
    if name not in SCHEDULES:
        raise ValueError("unknown proxy schedule")
    started = time.monotonic()
    sources = validate_sources()
    validate_schedules()
    low_k = low_k_signed_literal_tests()
    radial = load_radial_base()
    shell_mass = exact_target_shell_masses()[name]
    coordinate_cost = outer_coordinate_complexity()
    proxy_base = proxy_base_forms(PROXY_K, radial["amplitudes"])
    proxy = proxy_schedule_forms(
        name, SCHEDULES[name], proxy_base, radial["amplitudes"], PROXY_K)
    quotient = Q(proxy["exact_quotient"])
    gain = Q(proxy["exact_gain"])
    return {
        "status": "wide-hybrid-outer-constant-one-schedule-proxy-complete",
        "rigorous": False,
        "theorem_ready": False,
        "target_k48_integration_run": False,
        "target_launch_authorized": False,
        "script_sha256": sha256(FILE),
        "source_hashes": sources,
        "parameters": {
            "delta": str(DELTA), "alpha1": str(ALPHA1),
            "eta1": str(ETA1), "alpha2": str(ALPHA2),
            "eta2": str(ETA2),
        },
        "schedule": name,
        "caps": [str(value) for value in SCHEDULES[name]],
        "active_counts": list(active_counts(SCHEDULES[name])),
        "low_k_signed_literal": low_k,
        "exact_target_constant_shell_I": str(shell_mass),
        "outer_coordinate_cost_assessment": coordinate_cost,
        "proxy": {"k": PROXY_K, "radial_degree": 4,
                  "base_denominator": str(proxy_base["denominator"]),
                  "base_numerator": str(proxy_base["numerator"]),
                  "base_integral_calls": proxy_base["integral_calls"],
                  "schedule_result": proxy},
        "individual_gain_gate_pass": gain >= MIN_PROXY_GAIN,
        "exact_quotient_for_comparison": str(quotient),
        "fresh_other_schedule_and_comparator_required": True,
        "wall_seconds": time.monotonic() - started,
        "peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
    }


def publish_new(path, payload):
    path = Path(path).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    data = canonical_json(payload)
    with os.fdopen(descriptor, "wb", closefd=True) as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    if sha256(path) != sha256(data):
        raise RuntimeError("published proxy bytes changed")
    return sha256(data)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test-only", action="store_true")
    parser.add_argument("--cost-probe-only", action="store_true")
    parser.add_argument("--schedule", choices=tuple(SCHEDULES))
    parser.add_argument("--output")
    args = parser.parse_args()
    validate_sources()
    validate_schedules()
    low_k = low_k_signed_literal_tests()
    if args.self_test_only:
        print(json.dumps({"status": "LOW-K PASS", **low_k}, sort_keys=True))
        return
    if not args.output:
        parser.error("--output is required unless --self-test-only")
    if args.cost_probe_only and args.schedule:
        parser.error("--cost-probe-only and --schedule are mutually exclusive")
    if args.cost_probe_only:
        result = build_cost_probe()
    elif args.schedule:
        result = build_one_schedule_result(args.schedule)
    else:
        result = build_result()
    digest = publish_new(args.output, result)
    print(json.dumps({
        "status": result["status"], "output_sha256": digest,
        "ranking": result.get("proxy", {}).get("ranking"),
        "best_minus_other": result.get("proxy", {}).get("best_minus_other"),
        "mathematical_gate_pass": result.get(
            "continuation_gate", {}).get("mathematical_gate_pass"),
        "wall_seconds": result["wall_seconds"],
        "peak_rss_kib": result["peak_rss_kib"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
