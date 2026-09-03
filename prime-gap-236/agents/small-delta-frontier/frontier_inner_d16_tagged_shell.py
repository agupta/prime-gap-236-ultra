#!/usr/bin/env python3
"""Exact core for the frontier-shell tagged-constant diagnostic.

The finite space has one fixed inner coordinate -- the independently audited
radial BV D16 function -- and one constant coordinate on each exact total
large-count stratum of the outer shell.  Thus its dimension is 24.  The shell
I block is diagonal, the shell J block is tridiagonal, and all 23 inner/shell
cross entries are accumulated in one common-face traversal.

The target run is deliberately disabled in this revision.  ``--cost-probe``
evaluates one exact common face and ``--preflight-only`` inventories the full
work.  A separate byte-pinned authorization gate is required before a later
revision may execute the complete cross traversal.
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
import stat
import sys
import time


FILE = Path(__file__).resolve()
HERE = FILE.parent
REPO = FILE.parents[2]
SHELL_PATH = HERE / "wide_shell_stratum_diagnostic.py"
OUTER_PATH = HERE / "two_band_full_outer_constant.py"
CERT = HERE / "bv_aquarter_B16_vector_exact.json"
RADIAL = HERE / "bv_D16_radial_two_amplitudes_exact.json"
ANALYTIC = REPO / (
    "agents/audit/results/"
    "wide_c722_nonuniform_plateau16605_analytic_audit.json")

PINNED = {
    SHELL_PATH:
        "dbbf990caf2c1e6bc418d525d4becdaedc82af54eec457e8eb5578da29555cc5",
    OUTER_PATH:
        "75637298284a40be523621ebe1fcdc85bda59dcac42514fb8b50ffd8b460259d",
    CERT:
        "59715ddffa483c696c035634a81c3cc8ffe882e9d6eaceec74bea23996b72d62",
    RADIAL:
        "33fe5d555e736fe5ea3826d569477414fadd2d8a9defc2eaa35718a4f06f82ca",
    ANALYTIC:
        "700f7931b5a700a4b144a05a94f9c0f28791d3f40c257a4b56a5a8482617af7b",
}

K = 48
DELTA = Q(361, 50000)
EPSILON = Q(3, 400)
A1 = Q(1, 4)
A2 = Q(3121, 12000)
ALPHA1 = Q(103, 400)
ALPHA2 = Q(3211, 12000)
ETA1 = Q(97, 400)
ETA2 = Q(3031, 12000)
SCHEDULE = (Q(597, 5000), Q(633, 5000), Q(669, 5000), Q(141, 1000),
            Q(737, 5000), Q(773, 5000), Q(1553, 10000), Q(809, 5000),
            Q(81, 500)) + (Q(3321, 20000),) * 14
BRANCHES = ("Sdelta", "Stotal", "Ltotal", "Lbig")
PAIR_NAMES = ("rh", "rl", "vh", "vl")


def sha256(value) -> str:
    data = value if isinstance(value, bytes) else Path(value).read_bytes()
    return hashlib.sha256(data).hexdigest()


def require_pins():
    answer = {}
    for path, expected in PINNED.items():
        observed = sha256(path)
        if observed != expected:
            raise RuntimeError(f"frontier dependency changed: {path}")
        answer[str(path.relative_to(REPO))] = observed
    return dict(sorted(answer.items()))


require_pins()


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


shell = load_module("frontier_tagged_shell_core", SHELL_PATH)
outer_core = load_module("frontier_inner_cross_core", OUTER_PATH)
ei = shell.ei
GroupedEvaluator = shell.GroupedEvaluator


def validate_analytic():
    raw = json.loads(ANALYTIC.read_bytes())
    parameters = raw.get("parameters", {})
    expected_schedule = [str(x) for x in SCHEDULE]
    if (raw.get("status") != "AUDIT PASS" or
            raw.get("schedule_id") != "nonuniform-outer-plateau16605-v2" or
            raw.get("c1") != "0" or raw.get("c2") != "0" or
            parameters.get("k") != K or
            parameters.get("epsilon") != str(EPSILON) or
            parameters.get("delta") != str(DELTA) or
            parameters.get("A") != [str(-EPSILON), str(A1), str(A2)] or
            parameters.get("outer_plateau") != str(SCHEDULE[-1]) or
            parameters.get("outer_active") != list(range(23)) or
            parameters.get("outer_schedule_through_first_empty") !=
            expected_schedule):
        raise ValueError("frontier analytic identity changed")
    return raw


def load_inner_coordinate():
    cert = json.loads(CERT.read_bytes())
    radial = json.loads(RADIAL.read_bytes())
    if (cert.get("k") != K or cert.get("degree") != 16 or
            cert.get("integrator_sha256") != shell.PINNED[
                shell.EI_SRC / "exact_integrator.py"] or
            radial.get("format") !=
            "direct-bv-radial-two-amplitude-exact-v1" or
            radial.get("k") != K or
            radial.get("certificate_sha256") != PINNED[CERT] or
            radial.get("integrator_sha256") != cert.get(
                "integrator_sha256")):
        raise ValueError("inner D16 provenance mismatch")
    basis = tuple((int(a), tuple(int(x) for x in lam))
                  for a, lam in cert["basis"])
    vector = tuple(Q(x) for x in cert["rational_vector"])
    if len(basis) != 307 or len(vector) != len(basis):
        raise ValueError("inner D16 basis identity mismatch")
    amplitudes = tuple(Q(x) for x in radial["rational_amplitudes"])
    if len(amplitudes) != 2 or amplitudes[0] != 1:
        raise ValueError("radial amplitudes are not canonical")
    imat = [[Q(x) for x in row] for row in radial["I_matrix"]]
    bmat = [[Q(x) for x in row] for row in radial["kJ_matrix"]]
    denominator = sum(amplitudes[i] * imat[i][j] * amplitudes[j]
                      for i in range(2) for j in range(2))
    numerator = sum(amplitudes[i] * bmat[i][j] * amplitudes[j]
                    for i in range(2) for j in range(2))
    if (denominator != Q(radial["exact_denominator"]) or
            numerator != Q(radial["exact_numerator"]) or
            Q(radial["exact_quotient"]) != numerator / denominator or
            Q(radial["exact_margin"]) != numerator - denominator or
            radial.get("denominator_positive") is not (denominator > 0) or
            radial.get("margin_positive") is not (numerator > denominator)):
        raise ValueError("radial exact contraction mismatch")
    return basis, vector, amplitudes, denominator, numerator


def make_supports(k=K, schedule=None):
    if schedule is None:
        schedule = SCHEDULE if k == K else SCHEDULE[:k]
    schedule = tuple(schedule)
    high = shell.ScheduledStratumSupport.make(
        k, ALPHA2, ETA2, DELTA, schedule)
    low = shell.ScheduledStratumSupport.make(
        k, ALPHA1, ETA2, DELTA, schedule)
    full_r = ei.OneStratumSupport(
        k, ALPHA1, DELTA, ETA2, ALPHA1, ALPHA1, ALPHA1)
    full_v = ei.OneStratumSupport(
        k, ETA1, DELTA, ETA2, ETA1, ETA1, ETA1)
    return {"R": full_r, "V": full_v, "H": high, "L": low}


def branch_total(common_r, branch):
    return common_r if branch in ("Sdelta", "Stotal") else common_r + 1


def tagged_cross_catalog(named, pair_catalog, common_eta, *,
                         common_strata=None, selected_h=None,
                         integrate=True, progress=False):
    """Cross marginals tagged by the *right-hand* total large count.

    ``named`` maps a name to ``(support, component_list)`` and
    ``pair_catalog`` contains ``(tag,left_name,right_name)``.  No factor 48,
    polarization factor, or radial amplitude is hidden here.
    """
    if not pair_catalog:
        raise ValueError("empty pair catalog")
    supports = [named[name][0] for _, left, right in pair_catalog
                for name in (left, right)]
    k = supports[0].k
    delta = supports[0].delta
    if any(support.k != k or support.delta != delta
           for support in supports):
        raise ValueError("cross catalog geometry mismatch")
    if selected_h is not None and common_strata is None:
        raise ValueError("selected h requires one selected common stratum")
    max_right_common = min(
        k - 1, max(named[right][0].max_large()
                   for _, _, right in pair_catalog))
    selected = (range(max_right_common + 1) if common_strata is None else
                tuple(sorted(set(common_strata))))
    if any(type(r) is not int or not 0 <= r < k for r in selected):
        raise ValueError("invalid common stratum")
    if selected_h is not None and len(selected) != 1:
        raise ValueError("selected h requires exactly one common stratum")
    dimension = k - 1
    dummy = GroupedEvaluator(supports[0], [], [], Q)
    tables = {tag: [Q(0) for _ in range(k + 1)]
              for tag, _, _ in pair_catalog}
    counts = {tag: 0 for tag, _, _ in pair_catalog}
    faces = 0
    for r in selected:
        max_h = int(common_eta // delta) - r
        if max_h < 0:
            continue
        if selected_h is None:
            h_values = range(max_h + 1)
        else:
            if (type(selected_h) is not int or
                    not 0 <= selected_h <= max_h):
                raise ValueError("selected h is outside face list")
            h_values = (selected_h,)
        for h in h_values:
            outer = common_eta - (r + h) * delta
            if outer <= 0:
                continue
            blocks = {name: outer_core.branch_polynomials(
                support, components, r, h)
                for name, (support, components) in named.items()}
            density_cache = {}
            # Every right-hand coordinate in this diagnostic is a tagged
            # constant, hence has only the empty monomial orbit.  Lift each
            # left D16 branch through the common angular density once, then
            # multiply by the right scalar marginal polynomial.  The literal
            # orbit identity is P_nu * P_empty = P_nu with multiplicity one.
            # This removes eight identical density lifts per inner branch
            # without changing a single integration domain.
            right_names = {right for _, _, right in pair_catalog}
            for right_name in right_names:
                for branch, block in blocks[right_name].items():
                    if any(orbit != () for orbit in block):
                        raise ArithmeticError(
                            "right-hand tagged constant acquired a nonempty orbit")
            lifted_left = {}
            if integrate:
                for left_name in {left for _, left, _ in pair_catalog}:
                    for left_branch in BRANCHES:
                        lifted = defaultdict(Q)
                        for nu, marginal_poly in \
                                blocks[left_name][left_branch].items():
                            if nu not in density_cache:
                                density_cache[nu] = dummy.orbit_density(
                                    dimension, nu, r, h, max_h)
                            density = density_cache[nu]
                            if density:
                                shell.add_poly(
                                    lifted,
                                    ei._poly_mul(density, marginal_poly), Q(1))
                        lifted_left[(left_name, left_branch)] = dict(lifted)
            faces += 1
            for tag, left_name, right_name in pair_catalog:
                left_support = named[left_name][0]
                right_support = named[right_name][0]
                for left_branch in BRANCHES:
                    left = blocks[left_name][left_branch]
                    if not left:
                        continue
                    lc = left_support._branch_constraints(r, h, left_branch)
                    if lc is None:
                        continue
                    for right_branch in BRANCHES:
                        right = blocks[right_name][right_branch]
                        if not right:
                            continue
                        rc = right_support._branch_constraints(
                            r, h, right_branch)
                        if rc is None:
                            continue
                        counts[tag] += 1
                        if not integrate:
                            continue
                        right_poly = right.get(())
                        left_poly = lifted_left[(left_name, left_branch)]
                        integrand = ({} if right_poly is None or not left_poly
                                     else ei._poly_mul(left_poly, right_poly))
                        if integrand:
                            value = dummy.integrate_domain(
                                dict(integrand), dimension, r, outer, lc + rc)
                            tables[tag][branch_total(r, right_branch)] += value
            if progress:
                print(f"frontier cross r={r} h={h}/{max_h} counts={counts}",
                      file=sys.stderr, flush=True)
            dummy.clear_face_caches(clear_marginals=True)
        dummy.clear_radial_caches()
    return tables, counts, faces


def canonical_domain_key(dummy, dimension, r, outer, constraints):
    """Canonical exact integration domain, or ``None`` for measure zero.

    Grouping by this key is only an algebraic optimization: the returned
    polygon/interval is precisely the object used by
    ``GroupedEvaluator.integrate_domain``.  In particular, no floating-point
    geometry or containment comparison enters the grouping decision.
    """
    if outer <= 0:
        return None
    if dimension == 0:
        return None if any(cap < 0 for _, _, cap in constraints) else \
            ("point",)
    s = dimension - r
    if r and s:
        polygon = ei.polygon(outer, constraints)
        return None if not polygon else ("polygon", polygon)
    lo, hi = Q(0), outer
    axis = 0 if r else 1
    for az, aw, cap in constraints:
        coefficient = (az, aw)[axis]
        if coefficient > 0:
            hi = min(hi, cap / coefficient)
        elif coefficient < 0:
            lo = max(lo, cap / coefficient)
        elif cap < 0:
            return None
    if hi <= lo:
        return None
    return (("z" if r else "w"), lo, hi)


def integrate_canonical_domain(polynomial, key):
    """Integrate an exact polynomial over ``canonical_domain_key``."""
    if not polynomial or key is None:
        return Q(0)
    if key[0] == "point":
        return polynomial.get((0, 0), Q(0))
    if key[0] == "polygon":
        return ei.integrate_poly_polygon(polynomial, key[1])
    if key[0] == "z":
        return ei._integrate_poly_z_interval(polynomial, key[1], key[2])
    if key[0] == "w":
        return ei._integrate_poly_interval(polynomial, key[1], key[2])
    raise ValueError("unknown canonical domain")


def direct_full_simplex_marginal(support, component_list, r, h):
    """Direct full-fiber marginal, without four artificial t branches.

    For a genuinely uncapped simplex the distinguished coordinate ranges
    from 0 to ``alpha-U``.  The existing ``Stotal`` polynomial primitive is
    exactly that integral before its branch-domain restriction is imposed.
    We therefore reuse the audited primitive but impose only the literal
    full-fiber constraint ``U <= alpha``.  This is an identity, not a support
    enlargement; tests compare it to the sum of all four canonical branches.
    """
    if not support.is_full_simplex():
        raise ValueError("direct marginal requires a full-simplex support")
    cap = support.alpha - (r + h) * support.delta
    if cap <= 0:
        return {}, None
    block = {}
    for rest, exponent, residual, coefficient in component_list:
        polynomial = dict(support._marginal_poly(
            r, h, "Stotal", exponent, residual))
        if polynomial:
            destination = block.setdefault(rest, defaultdict(Q))
            shell.add_poly(destination, polynomial, coefficient)
    return ({orbit: dict(polynomial)
             for orbit, polynomial in block.items() if polynomial},
            ((Q(1), Q(1), cap),))


def grouped_weighted_cross(named, pair_catalog, pair_weights, common_eta, *,
                           common_strata=None, selected_h=None,
                           direct_full_left=(),
                           progress=False):
    """One exact weighted cross vector, grouped before integration.

    The literal cross is

      sum_tag pair_weights[tag] * J(left_tag, right_tag),

    tagged by the right-hand total large count.  Contributions with the same
    exact target count and integration polygon/interval are added as
    polynomials *before* integration.  Linearity therefore makes this exactly
    equal to ``tagged_cross_catalog`` followed by contraction, while avoiding
    repeated high-degree polygon moments.  The ungrouped routine remains in
    this file as an independent executable oracle.
    """
    tags = tuple(tag for tag, _, _ in pair_catalog)
    if (not tags or len(set(tags)) != len(tags) or
            set(pair_weights) != set(tags) or
            any(not isinstance(pair_weights[tag], Q)
                for tag in tags)):
        raise ValueError("invalid weighted pair catalog")
    direct_full_left = frozenset(direct_full_left)
    left_names = {left for _, left, _ in pair_catalog}
    right_names = {right for _, _, right in pair_catalog}
    if (not direct_full_left <= left_names or
            direct_full_left & right_names or
            any(not named[name][0].is_full_simplex()
                for name in direct_full_left)):
        raise ValueError("invalid direct full-simplex side")
    supports = [named[name][0] for _, left, right in pair_catalog
                for name in (left, right)]
    k = supports[0].k
    delta = supports[0].delta
    if any(support.k != k or support.delta != delta
           for support in supports):
        raise ValueError("cross catalog geometry mismatch")
    if selected_h is not None and common_strata is None:
        raise ValueError("selected h requires one selected common stratum")
    max_right_common = min(
        k - 1, max(named[right][0].max_large()
                   for _, _, right in pair_catalog))
    selected = (range(max_right_common + 1) if common_strata is None else
                tuple(sorted(set(common_strata))))
    if any(type(r) is not int or not 0 <= r < k for r in selected):
        raise ValueError("invalid common stratum")
    if selected_h is not None and len(selected) != 1:
        raise ValueError("selected h requires exactly one common stratum")
    dimension = k - 1
    dummy = GroupedEvaluator(supports[0], [], [], Q)
    table = [Q(0) for _ in range(k + 1)]
    literal_counts = {tag: 0 for tag in tags}
    geometric_groups = 0
    nonzero_groups = 0
    faces = 0
    for r in selected:
        max_h = int(common_eta // delta) - r
        if max_h < 0:
            continue
        h_values = range(max_h + 1) if selected_h is None else (selected_h,)
        if selected_h is not None and not 0 <= selected_h <= max_h:
            raise ValueError("selected h is outside face list")
        for h in h_values:
            outer = common_eta - (r + h) * delta
            if outer <= 0:
                continue
            blocks = {}
            constraints = {}
            for name, (support, components) in named.items():
                if name in direct_full_left:
                    block, domain = direct_full_simplex_marginal(
                        support, components, r, h)
                    blocks[name] = {"Full": block}
                    constraints[(name, "Full")] = domain
                else:
                    blocks[name] = outer_core.branch_polynomials(
                        support, components, r, h)
                    for branch in BRANCHES:
                        constraints[(name, branch)] = \
                            support._branch_constraints(r, h, branch)
            for right_name in right_names:
                for block in blocks[right_name].values():
                    if any(orbit != () for orbit in block):
                        raise ArithmeticError(
                            "right-hand tagged constant acquired a nonempty orbit")
            density_cache = {}
            lifted_left = {}
            for left_name in left_names:
                for left_branch in blocks[left_name]:
                    lifted = defaultdict(Q)
                    for nu, marginal_poly in blocks[left_name][left_branch].items():
                        if nu not in density_cache:
                            density_cache[nu] = dummy.orbit_density(
                                dimension, nu, r, h, max_h)
                        density = density_cache[nu]
                        if density:
                            shell.add_poly(
                                lifted,
                                ei._poly_mul(density, marginal_poly), Q(1))
                    lifted_left[(left_name, left_branch)] = dict(lifted)
            grouped = {}
            for tag, left_name, right_name in pair_catalog:
                left_support = named[left_name][0]
                right_support = named[right_name][0]
                weight = pair_weights[tag]
                for left_branch in blocks[left_name]:
                    if not blocks[left_name][left_branch]:
                        continue
                    left_poly = lifted_left[(left_name, left_branch)]
                    lc = constraints[(left_name, left_branch)]
                    if lc is None:
                        continue
                    for right_branch in BRANCHES:
                        right = blocks[right_name][right_branch]
                        right_poly = right.get(())
                        if right_poly is None:
                            continue
                        rc = constraints[(right_name, right_branch)]
                        if rc is None:
                            continue
                        literal_counts[tag] += 1
                        if not left_poly:
                            continue
                        domain = canonical_domain_key(
                            dummy, dimension, r, outer, lc + rc)
                        if domain is None:
                            continue
                        target = branch_total(r, right_branch)
                        key = (target, domain)
                        if key not in grouped:
                            grouped[key] = defaultdict(Q)
                        shell.add_poly(
                            grouped[key],
                            ei._poly_mul(left_poly, right_poly), weight)
            geometric_groups += len(grouped)
            for (target, domain), polynomial in grouped.items():
                if polynomial:
                    nonzero_groups += 1
                    table[target] += integrate_canonical_domain(
                        dict(polynomial), domain)
            faces += 1
            if progress:
                print(
                    f"frontier grouped cross r={r} h={h}/{max_h} "
                    f"literal={literal_counts} geometric={geometric_groups} "
                    f"nonzero={nonzero_groups}",
                    file=sys.stderr, flush=True)
            dummy.clear_face_caches(clear_marginals=True)
        dummy.clear_radial_caches()
    return table, literal_counts, geometric_groups, nonzero_groups, faces


def production_cross_inputs(k=K):
    basis, vector, amplitudes, inner_i, inner_b = load_inner_coordinate()
    supports = make_supports(k)
    base_components = outer_core.components(basis, vector, k)
    one = (((), 0, 0, Q(1)),)
    named = {"R": (supports["R"], base_components),
             "V": (supports["V"], base_components),
             "H": (supports["H"], one),
             "L": (supports["L"], one)}
    catalog = (("rh", "R", "H"), ("rl", "R", "L"),
               ("vh", "V", "H"), ("vl", "V", "L"))
    return named, catalog, amplitudes, inner_i, inner_b


def combine_radial_cross(tables, amplitudes):
    inner_amp, outer_amp = amplitudes
    return [outer_amp * (tables["rh"][r] - tables["rl"][r]) +
            (inner_amp - outer_amp) *
            (tables["vh"][r] - tables["vl"][r])
            for r in range(len(tables["rh"]))]


def production_pair_weights(amplitudes):
    inner_amp, outer_amp = amplitudes
    return {"rh": outer_amp, "rl": -outer_amp,
            "vh": inner_amp - outer_amp,
            "vl": -(inner_amp - outer_amp)}


def shell_i_and_j():
    supports = make_supports()
    high, low = supports["H"], supports["L"]
    max_r = max(high.max_large(), low.max_large())
    masses = [high.basis_m1_in_strata(r, (0, ()), r, (0, ())) -
              low.basis_m1_in_strata(r, (0, ()), r, (0, ()))
              for r in range(max_r + 1)]
    if any(value < 0 for value in masses):
        raise ArithmeticError("negative shell I mass")
    tables = {}
    counts = {}
    for tag, left, right in (("hh", high, high), ("hl", high, low),
                             ("ll", low, low)):
        tables[tag], counts[tag] = shell.cross_constant_stratum_table(
            left, right, ETA2)
    hl_t = [list(row) for row in zip(*tables["hl"])]
    raw_j = shell.matrix_add(
        (Q(1), tables["hh"]), (Q(-1), tables["hl"]),
        (Q(-1), hl_t), (Q(1), tables["ll"]))
    k_j = [[K * x for x in row] for row in raw_j]
    active = [r for r, mass in enumerate(masses) if mass > 0]
    if active != list(range(23)):
        raise ArithmeticError(f"unexpected active shell counts: {active}")
    if any(k_j[r][s] for r in active for s in active if abs(r - s) > 1):
        raise ArithmeticError("shell matrix is not tridiagonal")
    return active, masses, k_j, counts


def cross_inventory():
    # This is a conservative geometry-only inventory.  Constructing all D16
    # branch polynomials merely to count them costs a nontrivial fraction of a
    # traversal.  Every genuinely nonzero branch product is contained in this
    # constraints-only count; algebraic zero/cancellation can only reduce it.
    named, catalog, _, _, _ = production_cross_inputs()
    counts = {tag: 0 for tag, _, _ in catalog}
    faces = 0
    max_right_common = min(
        K - 1, max(named[right][0].max_large()
                   for _, _, right in catalog))
    for r in range(max_right_common + 1):
        max_h = int(ETA2 // DELTA) - r
        if max_h < 0:
            continue
        for h in range(max_h + 1):
            outer = ETA2 - (r + h) * DELTA
            if outer <= 0:
                continue
            active = {
                name: tuple(branch for branch in BRANCHES
                            if support._branch_constraints(r, h, branch)
                            is not None)
                for name, (support, _) in named.items()
            }
            faces += 1
            for tag, left, right in catalog:
                counts[tag] += len(active[left]) * len(active[right])
    return counts, faces


def grouped_geometry_inventory():
    """Exact upper inventory after target/domain grouping, before algebra.

    This traverses only the rational halfplanes; it neither constructs nor
    integrates a D16 polynomial.  A group whose weighted polynomial cancels
    is still counted, so the result is a conservative integration count.
    """
    named, catalog, amplitudes, _, _ = production_cross_inputs()
    weights = production_pair_weights(amplitudes)
    supports = [named[name][0] for _, left, right in catalog
                for name in (left, right)]
    dummy = GroupedEvaluator(supports[0], [], [], Q)
    dimension = K - 1
    max_right_common = min(
        K - 1, max(named[right][0].max_large()
                   for _, _, right in catalog))
    per_r = {}
    total_groups = 0
    total_faces = 0
    for r in range(max_right_common + 1):
        r_groups = 0
        r_faces = 0
        max_h = int(ETA2 // DELTA) - r
        if max_h < 0:
            continue
        for h in range(max_h + 1):
            outer = ETA2 - (r + h) * DELTA
            if outer <= 0:
                continue
            groups = set()
            for tag, left_name, right_name in catalog:
                if not weights[tag]:
                    continue
                left_support = named[left_name][0]
                right_support = named[right_name][0]
                for left_branch in BRANCHES:
                    lc = left_support._branch_constraints(r, h, left_branch)
                    if lc is None:
                        continue
                    for right_branch in BRANCHES:
                        rc = right_support._branch_constraints(
                            r, h, right_branch)
                        if rc is None:
                            continue
                        domain = canonical_domain_key(
                            dummy, dimension, r, outer, lc + rc)
                        if domain is not None:
                            groups.add((branch_total(r, right_branch), domain))
            r_groups += len(groups)
            r_faces += 1
            dummy.clear_face_caches()
        total_groups += r_groups
        total_faces += r_faces
        per_r[str(r)] = {"faces": r_faces,
                         "geometric_group_upper": r_groups}
    return total_groups, total_faces, per_r


def preflight():
    pins = require_pins()
    validate_analytic()
    _, _, _, _, _ = production_cross_inputs()
    counts, faces = cross_inventory()
    group_count, group_faces, per_r = grouped_geometry_inventory()
    if group_faces != faces:
        raise ArithmeticError("literal/grouped face inventory mismatch")
    return {
        "status": "frontier-inner-D16-tagged-shell-preflight",
        "target_run_started": False,
        "script_sha256": sha256(FILE),
        "dependency_sha256": pins,
        "parameters": parameter_record(),
        "dimension": 24,
        "cross_face_count": faces,
        "cross_domain_counts": counts,
        "cross_domain_count_total": sum(counts.values()),
        "cross_domain_inventory_is_conservative": True,
        "grouped_geometric_domain_upper": group_count,
        "grouped_geometric_inventory_is_conservative": True,
        "grouped_inventory_by_common_r": per_r,
        "mem_available_kib": mem_available_kib(),
        "full_cross_authorized": False,
        "authorization_requirement": (
            "a later source revision must pin an exact cost-probe artifact and "
            "a separately frozen resource gate"),
    }


def parameter_record():
    return {"k": K, "delta": str(DELTA), "epsilon": str(EPSILON),
            "A": [str(-EPSILON), str(A1), str(A2)],
            "alpha": [str(ALPHA1), str(ALPHA2)],
            "eta": [str(ETA1), str(ETA2)],
            "outer_schedule": [str(x) for x in SCHEDULE]}


def mem_available_kib():
    for line in Path("/proc/meminfo").read_text().splitlines():
        if line.startswith("MemAvailable:"):
            return int(line.split()[1])
    raise RuntimeError("MemAvailable missing")


def build_cost_probe(common_r, selected_h, *, direct_full=True):
    started = time.monotonic()
    self_start = sha256(FILE)
    pins = require_pins()
    validate_analytic()
    named, catalog, amplitudes, _, _ = production_cross_inputs()
    combined, counts, geometric_groups, nonzero_groups, faces = \
        grouped_weighted_cross(
            named, catalog, production_pair_weights(amplitudes), ETA2,
            common_strata=(common_r,), selected_h=selected_h,
            direct_full_left=(("R", "V") if direct_full else ()),
            progress=True)
    if sha256(FILE) != self_start or require_pins() != pins:
        raise RuntimeError("cost-probe closure changed")
    return {
        "status": "frontier-inner-D16-tagged-shell-exact-cost-probe",
        "rigorous_values": True,
        "theorem_ready": False,
        "complete_cross": False,
        "script_sha256": self_start,
        "dependency_sha256": pins,
        "parameters": parameter_record(),
        "common_r": common_r,
        "selected_h": selected_h,
        "direct_full_fiber": direct_full,
        "faces": faces,
        "domain_counts": counts,
        "radial_cross_by_target_R": [str(x) for x in combined],
        "geometric_group_count": geometric_groups,
        "nonzero_group_count": nonzero_groups,
        "wall_seconds": time.monotonic() - started,
        "peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "claim_scope": "one exact face for cost only; no quotient",
    }


def publish(path, payload):
    target = Path(path).resolve()
    protected = {FILE, *(path.resolve() for path in PINNED)}
    if target in protected:
        raise ValueError("output aliases a protected input")
    target.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    try:
        with os.fdopen(fd, "wb", closefd=False) as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise RuntimeError("cost output is not regular")
    finally:
        os.close(fd)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--preflight-only", action="store_true")
    parser.add_argument("--cost-probe-r", type=int)
    parser.add_argument("--cost-probe-h", type=int)
    parser.add_argument("--literal-full-branches", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.preflight_only:
        if any(value is not None for value in
               (args.cost_probe_r, args.cost_probe_h, args.output)):
            parser.error("preflight does not accept probe/output arguments")
        if args.literal_full_branches:
            parser.error("preflight does not accept literal branch mode")
        print(json.dumps(preflight(), sort_keys=True, indent=2))
        return
    if (args.cost_probe_r is None or args.cost_probe_h is None or
            args.output is None):
        parser.error("this revision supports only a complete cost-probe triple")
    result = build_cost_probe(
        args.cost_probe_r, args.cost_probe_h,
        direct_full=not args.literal_full_branches)
    payload = (json.dumps(result, sort_keys=True, separators=(",", ":")) +
               "\n").encode("ascii")
    publish(args.output, payload)
    print(json.dumps({"artifact_sha256": sha256(payload),
                      "wall_seconds": result["wall_seconds"],
                      "peak_rss_kib": result["peak_rss_kib"],
                      "domain_counts": result["domain_counts"]},
                     sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
