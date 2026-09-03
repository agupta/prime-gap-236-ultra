#!/usr/bin/env python3
"""Exact, disabled staging plan for the missing active-25 outer numerator.

This file does not launch the k=48 traversal and does not form a quotient.
It fixes two candidate routes:

* the literal ten-coordinate even-B4 shell, whose numerator block is

      48 (J_HH - J_HL - J_LH + J_LL),

  with the ordered mixed block retained before transposition; and
* the cheaper count-specific normalized cap-slack coordinates

      C_(R,d) = 1_{#large=R} ((B_R-R*delta-z_R)/(B_R-R*delta))^d.

For the latter, this module supplies the exact grouped common-r kernel for
the cross with the fixed radial D16 coordinate.  The target CLI is
deliberately preflight-only.  A successor must bind an external authorization
before any complete k=48 cross traversal is allowed.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from fractions import Fraction as Q
import hashlib
import importlib.util
import json
from pathlib import Path
import statistics
import sys


FILE = Path(__file__).resolve()
REPO = FILE.parents[3]
TEST_FILE = (REPO / "agents/structural-basis/tests/"
             "test_active25_outer_b4_j_cross_plan_v1.py")
SPEC_FILE = (REPO / "agents/structural-basis/"
             "ACTIVE25-OUTER-B4-J-CROSS-PLAN-V1.md")

CORE = (REPO / "agents/small-delta-frontier/"
        "frontier_active25_inner_d16_tagged_shell.py")
B4_I_SOURCE = (REPO / "agents/structural-basis/code/"
               "active25_outer_b4_i_block_v2.py")
B4_I_ARTIFACT = (REPO / "agents/structural-basis/results/"
                 "active25_outer_even_b4_shell_i_exact_v2.json")
B4_I_AUDITOR = REPO / "agents/audit/verify_active25_outer_b4_i_block_v2.py"
B4_I_AUDIT = (REPO / "agents/audit/results/"
              "active25_outer_b4_i_block_v2_audit.json")
B4_I_REPORT = REPO / "agents/audit/ACTIVE25-OUTER-B4-I-BLOCK-V2-AUDIT.md"
CAP_SOURCE = REPO / "scripts/active25_count_cap_slack_shell.py"
CAP_TEST = REPO / "scripts/test_active25_count_cap_slack_shell.py"
CAP_RESULTS = tuple(
    REPO / f"results/active25_count_cap_slack_shell_d{degree}_v1.json"
    for degree in range(3))
COST_RESULTS = tuple(
    REPO / "agents/small-delta-frontier/results" / name for name in (
        "frontier_active25_innerD16_shell_cross_r00_h17_direct_v2.json",
        "frontier_active25_innerD16_shell_cross_r05_h15_direct_v2.json",
        "frontier_active25_innerD16_shell_cross_r10_h10_direct_v2.json",
        "frontier_active25_innerD16_shell_cross_r15_h10_direct_v2.json",
        "frontier_active25_innerD16_shell_cross_r22_h06_direct_v2.json",
        "frontier_active25_innerD16_shell_cross_r25_h05_direct_v2.json",
    ))

PINNED = {
    CORE: "1393a2dd29e5660f10e632b19b6b5eeafe9363bf79b2cd4a8254049d1f9c669a",
    B4_I_SOURCE: "ddad99bdd12710e669870fcade850eb72e1c5989ef4747b2e0658be28551b6bb",
    B4_I_ARTIFACT: "ffe98de8ee5d47da7f046f4aa91aaadc3f7981222f7b7803276556ea558e756c",
    B4_I_AUDITOR: "aa8b8cdb5eaaaf656c20fd44c0fe85a10d9c472dc80a747cca83daa154bc0605",
    B4_I_AUDIT: "9888d3190a4f989a13a288e46d553f1f16eb780447b6e3bb1dd645130b77d23a",
    B4_I_REPORT: "8a2a2040c5af0da68d3c314742626020cec827f5d30335833436d8d81b2f39c9",
    CAP_SOURCE: "bf460e36c0cc1586b82b6563464dab52773ca8895a87a930ad970b6b4935339b",
    CAP_TEST: "d119c246c9483bb5416d40bc860b683281f89130ea66ac22134a4fba93a6b815",
    CAP_RESULTS[0]: "6e97c4b35d27e40f40e258dd00726d84f2dfc3c910ef9542250d45be9624e195",
    CAP_RESULTS[1]: "3d6532fdf9f641583598d45bae55b9d40641391136e0498748f446d783030b68",
    CAP_RESULTS[2]: "c66cd86055385dc372d948d2f209f84fb850136120d21b55554806ba25d73d63",
    COST_RESULTS[0]: "73f351f24defafc0cb6c0a293d258bac33d504e457771ea11362ff5d67bd9107",
    COST_RESULTS[1]: "5603845bf7514a4f6dcb4831ed3854b1915189d39424d9d1b47f2bc6f2cd1901",
    COST_RESULTS[2]: "37b0d249a0fd17e823f154277bfabe162c3b80c72c344c97686312c7fac7e393",
    COST_RESULTS[3]: "5f4d88417ed0b84d26c52512ddf710b35bd9e7d55e9df4a68ad2114dc3602d29",
    COST_RESULTS[4]: "8e023686703d353bb63faad3be541238920bc8b7640a4ba3202b924d0385ace9",
    COST_RESULTS[5]: "9c13277024543c51b2c945743ce74c5ebfc5b1d2eb3e21d264740bcf0e35e6df",
}


def sha256(value) -> str:
    data = value if isinstance(value, bytes) else Path(value).read_bytes()
    return hashlib.sha256(data).hexdigest()


def require_pins():
    found = {}
    for path, expected in PINNED.items():
        actual = sha256(path)
        if actual != expected:
            raise RuntimeError(f"pinned dependency changed: {path}: {actual}")
        found[str(path.relative_to(REPO))] = actual
    return found


require_pins()


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


A25 = _load("active25_j_plan_core", CORE)
CAP = _load("active25_j_plan_cap_reference", CAP_SOURCE)
EI = A25.ei
GroupedEvaluator = A25.GroupedEvaluator
BRANCHES = A25.BRANCHES
Q0, Q1 = Q(0), Q(1)


def cap_labels(max_degree=2, max_count=25):
    """Canonical active-25 cap basis; count zero has only degree zero."""
    if (type(max_degree) is not int or not 0 <= max_degree <= 8 or
            type(max_count) is not int or not 0 <= max_count <= 25):
        raise ValueError("invalid cap-label bounds")
    return ((0, 0),) + tuple(
        (count, degree) for count in range(1, max_count + 1)
        for degree in range(max_degree + 1))


def branch_total(common_r, branch):
    if branch in ("Sdelta", "Stotal"):
        return common_r
    if branch in ("Ltotal", "Lbig"):
        return common_r + 1
    raise ValueError("unknown branch")


def independent_cap_marginal(support, r, h, branch, degree):
    """Exact normalized cap-slack marginal, derived by antiderivatives.

    This implementation is intentionally separate from ``CAP``.  Small
    branches have fixed slack ``gamma-z``.  On large branches the integrand
    is ``(gamma+delta-z-t)^degree`` and is integrated at the literal branch
    endpoints.
    """
    if type(degree) is not int or degree < 0:
        raise ValueError("invalid cap degree")
    if support._branch_constraints(r, h, branch) is None:
        return {}
    count = branch_total(r, branch)
    if count == 0:
        if degree:
            return {}
        gamma = None
    else:
        gamma = support.beta(count) - count * support.delta
        if gamma <= 0:
            return {}
    u0 = (r + h) * support.delta
    if branch in ("Sdelta", "Stotal"):
        length = (dict(support._marginal_poly(r, h, branch, 0, 0)))
        if not degree:
            return length
        raw = EI._poly_mul(
            length, dict(EI._linear_power(gamma, -Q1, Q0, degree)))
        return EI._poly_scale(raw, gamma ** (-degree))

    # Integral of (A-t)^d is ((A-lo)^(d+1)-(A-hi)^(d+1))/(d+1),
    # with A=gamma+delta-z.  The two expanded forms below avoid a symbolic
    # division by a polynomial and remain exact Fractions.
    cap_upper = dict(EI._linear_power(gamma, -Q1, Q0, degree + 1))
    if branch == "Lbig":
        raw = cap_upper
    elif branch == "Ltotal":
        # A-hi = beta(count)-alpha+h*delta+w.
        lower_slack = dict(EI._linear_power(
            support.beta(count) - support.alpha + h * support.delta,
            Q0, Q1, degree + 1))
        raw = EI._poly_add(cap_upper, EI._poly_scale(lower_slack, -Q1))
    else:  # defensive; branch names were checked above
        raise ValueError(branch)
    scale = Q(1, degree + 1)
    if count:
        scale /= gamma ** degree
    return EI._poly_scale(raw, scale)


def _poly_add_inplace(destination, source, scale=Q1):
    for monomial, value in source.items():
        destination[monomial] += scale * value
        if not destination[monomial]:
            del destination[monomial]


def assemble_natural_outer_b48(hh, hl, ll, *, k=48):
    """Assemble ``k J`` while retaining the ordered mixed block.

    ``J_LH`` is the transpose of ``J_HL``.  Entrywise replacement by
    ``2*J_HL`` is invalid unless the mixed block happens to be symmetric.
    """
    n = len(hh)
    if (not n or any(len(matrix) != n or any(len(row) != n for row in matrix)
                     for matrix in (hh, hl, ll)) or
            any(hh[i][j] != hh[j][i] or ll[i][j] != ll[j][i]
                for i in range(n) for j in range(n)) or
            type(k) is not int or k <= 0):
        raise ValueError("invalid natural outer blocks")
    return [[Q(k) * (hh[i][j] - hl[i][j] - hl[j][i] + ll[i][j])
             for j in range(n)] for i in range(n)]


def assemble_inner_cross_b48(rh, rl, vh, vl, amplitudes, *, k=48):
    """Assemble the D16/shell cross; all inputs are raw ``J`` vectors."""
    if (not all(type(values) in (tuple, list)
                for values in (rh, rl, vh, vl)) or
            len({len(values) for values in (rh, rl, vh, vl)}) != 1 or
            len(amplitudes) != 2 or type(k) is not int or k <= 0):
        raise ValueError("invalid radial cross blocks")
    inner_amplitude, outer_amplitude = map(Q, amplitudes)
    return [Q(k) * (outer_amplitude * (Q(rh[i]) - Q(rl[i])) +
                    (inner_amplitude - outer_amplitude) *
                    (Q(vh[i]) - Q(vl[i])))
            for i in range(len(rh))]


def _right_cap_blocks(support, basis, r, h):
    by_count = defaultdict(list)
    for label in basis:
        by_count[label[0]].append(label)
    blocks = {}
    for branch in BRANCHES:
        count = branch_total(r, branch)
        blocks[branch] = {
            label: independent_cap_marginal(
                support, r, h, branch, label[1])
            for label in by_count.get(count, ())
        }
        blocks[branch] = {label: poly for label, poly in
                          blocks[branch].items() if poly}
    return blocks


def grouped_inner_cap_cross_shard(common_r, *, basis=None,
                                  inner_loader=A25.load_inner_coordinate,
                                  supports=None, common_eta=None,
                                  selected_h=None, progress=False):
    """Exact raw-J cross of the radial inner coordinate with cap coordinates.

    A shard contains every inclusion-exclusion face for one common count.
    The uncapped inner marginal is formed directly over its full distinguished
    fiber.  Contributions from R/V against H/L are grouped by exact output
    coordinate and canonical integration domain before integration.
    """
    if type(common_r) is not int or common_r < 0:
        raise ValueError("invalid common count")
    if supports is None:
        supports = A25.make_supports()
    common_eta = A25.ETA2 if common_eta is None else Q(common_eta)
    k = supports["H"].k
    if not all(support.k == k and support.delta == supports["H"].delta
               for support in supports.values()):
        raise ValueError("support geometry mismatch")
    if not 0 <= common_r < k:
        raise ValueError("common count outside dimension")
    basis = cap_labels() if basis is None else tuple(basis)
    if len(set(basis)) != len(basis):
        raise ValueError("duplicate cap label")

    inner_basis, inner_vector, amplitudes, inner_i, inner_b = inner_loader()
    components = A25.outer_core.components(inner_basis, inner_vector, k)
    left = {"R": (supports["R"], components),
            "V": (supports["V"], components)}
    right = {"H": supports["H"], "L": supports["L"]}
    weights = {"RH": amplitudes[1], "RL": -amplitudes[1],
               "VH": amplitudes[0] - amplitudes[1],
               "VL": -(amplitudes[0] - amplitudes[1])}
    catalog = (("RH", "R", "H"), ("RL", "R", "L"),
               ("VH", "V", "H"), ("VL", "V", "L"))
    dummy = GroupedEvaluator(supports["H"], [], [], Q)
    dimension = k - 1
    max_h = int(common_eta // supports["H"].delta) - common_r
    values = {label: Q0 for label in basis}
    literal_terms = 0
    geometric_groups = 0
    nonzero_groups = 0
    faces = 0
    if max_h < 0:
        return values, {
            "faces": 0, "literal_weighted_terms": 0,
            "geometric_groups": 0, "nonzero_groups": 0,
            "complete_common_r": selected_h is None,
            "selected_h": selected_h,
            "inner_I": inner_i, "inner_48J": inner_b,
        }

    if selected_h is None:
        h_values = range(max_h + 1)
    else:
        if type(selected_h) is not int or not 0 <= selected_h <= max_h:
            raise ValueError("selected h is outside the common-r face list")
        h_values = (selected_h,)
    for h in h_values:
        outer = common_eta - (common_r + h) * supports["H"].delta
        if outer <= 0:
            continue
        faces += 1
        left_blocks = {}
        left_constraints = {}
        for name, (support, pieces) in left.items():
            block, constraint = A25.direct_full_simplex_marginal(
                support, pieces, common_r, h)
            left_blocks[name] = block
            left_constraints[name] = constraint
        right_blocks = {
            name: _right_cap_blocks(support, basis, common_r, h)
            for name, support in right.items()
        }
        density_cache = {}
        lifted = {}
        for name, block in left_blocks.items():
            polynomial = defaultdict(Q)
            for orbit, marginal in block.items():
                if orbit not in density_cache:
                    density_cache[orbit] = dummy.orbit_density(
                        dimension, orbit, common_r, h, max_h)
                density = density_cache[orbit]
                if density:
                    _poly_add_inplace(
                        polynomial, EI._poly_mul(density, marginal))
            lifted[name] = dict(polynomial)

        grouped = {}
        for tag, left_name, right_name in catalog:
            if not weights[tag] or not lifted[left_name]:
                continue
            lc = left_constraints[left_name]
            if lc is None:
                continue
            support = right[right_name]
            for branch, coordinate_polys in right_blocks[right_name].items():
                rc = support._branch_constraints(common_r, h, branch)
                if rc is None:
                    continue
                domain = A25.canonical_domain_key(
                    dummy, dimension, common_r, outer, lc + rc)
                if domain is None:
                    continue
                for label, right_poly in coordinate_polys.items():
                    literal_terms += 1
                    key = (label, domain)
                    destination = grouped.setdefault(key, defaultdict(Q))
                    _poly_add_inplace(
                        destination,
                        EI._poly_mul(lifted[left_name], right_poly),
                        weights[tag])
        geometric_groups += len(grouped)
        for (label, domain), polynomial in grouped.items():
            if polynomial:
                nonzero_groups += 1
                values[label] += A25.integrate_canonical_domain(
                    dict(polynomial), domain)
        if progress:
            print(f"cap-cross r={common_r} h={h}/{max_h} "
                  f"groups={geometric_groups}", flush=True)
        dummy.clear_face_caches(clear_marginals=True)
    dummy.clear_radial_caches()
    return values, {
        "faces": faces, "literal_weighted_terms": literal_terms,
        "geometric_groups": geometric_groups,
        "nonzero_groups": nonzero_groups,
        "complete_common_r": selected_h is None,
        "selected_h": selected_h,
        "inner_I": inner_i, "inner_48J": inner_b,
    }


def target_work_inventory(max_degree=2):
    """Exact face/term inventory without constructing target polynomials."""
    basis = cap_labels(max_degree)
    degree_count = max_degree + 1
    face_total = 0
    cap_cross_terms = 0
    natural_cross_terms = 0
    natural_outer_terms = 0
    by_r = {}
    max_common = min(25, int(A25.ETA2 // A25.DELTA))
    for r in range(max_common + 1):
        faces = int(A25.ETA2 // A25.DELTA) - r + 1
        face_total += faces
        # H/L each have two small and two large branches.  R=0 has only d=0;
        # R=26 is absent.  There are two full-simplex radial left supports.
        small_coordinates = 1 if r == 0 else degree_count
        large_coordinates = 0 if r == 25 else degree_count
        per_face_cap_cross = 4 * (small_coordinates + large_coordinates)
        # Four here is 2 inner supports times 2 outer inclusion supports;
        # each count appears on two literal t branches.
        per_face_cap_cross *= 2
        # Equivalent simplified count: 4 tags times
        # (2 small branches*nsmall + 2 large branches*nlarge).
        expected = 4 * (2 * small_coordinates + 2 * large_coordinates)
        if per_face_cap_cross != expected:
            raise ArithmeticError("cap cross inventory identity failed")
        cap_cross_terms += faces * expected
        # Ten natural B4 columns occur on every one of four t branches and
        # every one of four radial/support inclusion tags.
        natural_cross_terms += faces * 10 * 4 * 4
        # HH and LL use 55 symmetric entries; HL is 100 ordered entries and
        # LH is recovered by transpose: 210 entries per 16 branch pairs.
        natural_outer_terms += faces * 210 * 16
        by_r[str(r)] = {
            "faces": faces,
            "cap_cross_literal_terms": faces * expected,
            "natural_b4_cross_literal_terms": faces * 160,
            "natural_b4_outer_j_literal_terms": faces * 3360,
        }
    cap_nonzero_i = 1 + 25 * ((degree_count * (degree_count + 1)) // 2)
    cap_j_upper = (
        1  # R=0 diagonal
        + 25 * ((degree_count * (degree_count + 1)) // 2)
        + degree_count  # 0--1 block
        + 24 * degree_count * degree_count)
    return {
        "common_r": list(range(max_common + 1)),
        "faces": face_total,
        "natural_b4_dimension": 10,
        "natural_b4_outer_j_unique_entries": 55,
        "natural_b4_outer_j_support_matrices":
            "HH upper55, HL ordered100, LL upper55; LH=HL^T",
        "natural_b4_outer_j_literal_entry_branch_terms": natural_outer_terms,
        "natural_b4_inner_cross_entries": 10,
        "natural_b4_inner_cross_literal_weighted_terms": natural_cross_terms,
        "cap_degree": max_degree,
        "cap_dimension": len(basis),
        "cap_I_unique_nonzero_entries": cap_nonzero_i,
        "cap_J_unique_upper_nonzero_entries": cap_j_upper,
        "cap_inner_cross_entries": len(basis),
        "cap_inner_cross_literal_weighted_terms": cap_cross_terms,
        "by_common_r": by_r,
    }


def measured_cost_model():
    cap = [json.loads(path.read_bytes()) for path in CAP_RESULTS]
    probes = [json.loads(path.read_bytes()) for path in COST_RESULTS]
    if ([row["maximum_cap_slack_degree"] for row in cap] != [0, 1, 2] or
            any(row.get("contains_inner_cross") is not False for row in cap) or
            any(row.get("complete_cross") is not False for row in probes)):
        raise ValueError("cost calibration artifact schema changed")
    times = [float(row["wall_seconds"]) for row in probes]
    rss = [int(row["peak_rss_kib"]) for row in probes]
    faces = target_work_inventory()["faces"]
    d0_projection = statistics.mean(times) * faces
    # D0 is one cap coordinate per active count and is algebraically the
    # already measured tagged-constant cross.  Three cap degrees reuse the
    # same expensive lifted D16 marginal; 3x is intentionally conservative.
    d2_projection = 3 * d0_projection
    natural_projection = 10 * d0_projection
    cap_outer_integrals = sum(
        row["J_work"][tag]["polynomial_integrals"]
        for row in cap for tag in ("hh", "hl", "lh", "ll"))
    return {
        "constant_cross_face_probe_seconds": times,
        "constant_cross_face_mean_seconds": statistics.mean(times),
        "constant_cross_face_median_seconds": statistics.median(times),
        "constant_cross_probe_peak_rss_kib": max(rss),
        "projected_full_constant_cross_seconds": d0_projection,
        "projected_cap_d0_d2_cross_seconds_conservative": d2_projection,
        "projected_natural_b4_cross_seconds_conservative": natural_projection,
        "cap_shell_exact_runs": [{
            "degree": row["maximum_cap_slack_degree"],
            "dimension": row["dimension"],
            "wall_seconds": row["wall_seconds"],
            "peak_rss_kib": row["peak_rss_kib"],
            "polynomial_integrals_total": sum(
                row["J_work"][tag]["polynomial_integrals"]
                for tag in ("hh", "hl", "lh", "ll")),
            "artifact_sha256": PINNED[CAP_RESULTS[index]],
        } for index, row in enumerate(cap)],
        "cap_shell_polynomial_integrals_all_three_runs": cap_outer_integrals,
        "memory_gate_kib": 262144,
        "single_face_wall_gate_seconds": 20,
        "projected_complete_cross_wall_gate_seconds": 10800,
    }


def build_plan():
    pins = require_pins()
    inventory = target_work_inventory(2)
    costs = measured_cost_model()
    # Exact formula agreement with the independently written producer is a
    # preflight identity, not an audit of its publication/provenance layer.
    support = A25.make_supports()["H"]
    checked = 0
    for r in (0, 1, 10, 24, 25):
        max_h = int(A25.ETA2 // A25.DELTA) - r
        for h in sorted(set((0, max_h // 2, max_h))):
            for branch in BRANCHES:
                if support._branch_constraints(r, h, branch) is None:
                    continue
                for degree in range(3):
                    left = independent_cap_marginal(
                        support, r, h, branch, degree)
                    right = CAP.cap_slack_marginal(
                        support, r, h, branch, degree)
                    if left != right:
                        raise ArithmeticError("cap marginal implementations differ")
                    checked += 1
    return {
        "status": "active25-outer-b4-j-cross-disabled-plan-v1",
        "rigorous_values": False,
        "target_run_started": False,
        "contains_J_values": False,
        "contains_quotient": False,
        "source_sha256": sha256(FILE),
        "package_sha256": {
            str(FILE.relative_to(REPO)): sha256(FILE),
            str(TEST_FILE.relative_to(REPO)): sha256(TEST_FILE),
            str(SPEC_FILE.relative_to(REPO)): sha256(SPEC_FILE),
        },
        "dependency_sha256": pins,
        "parameters": A25.parameter_record(),
        "denominator_audit_scope": "exact 10x10 even-B4 shell I block only",
        "formula": {
            "natural_outer_B48":
                "48*(J_HH-J_HL-J_HL_transpose+J_LL)",
            "natural_inner_B48_cross":
                "48*(a_R*(J_RH-J_RL)+(a_V)*(J_VH-J_VL))",
            "cap_coordinate":
                "1_{count=R}*((B_R-R*delta-z_R)/(B_R-R*delta))^d",
            "cap_J_sparsity": "only |R-S|<=1",
            "cap_inner_cross":
                "same radial inclusion formula, grouped by (coordinate, exact domain)",
        },
        "cap_reference_formula_checks": checked,
        "work_inventory": inventory,
        "measured_cost_model": costs,
        "selected_first_route": "D16 crossed with normalized cap-slack d=0,1,2",
        "selection_reason": (
            "27280 weighted branch-column terms versus 93600 for natural B4; "
            "the exact cap shell block is already available in 110.03 seconds"
        ),
        "stage_unit": "one common_r in 0..25; exact Fraction vector; O_EXCL output",
        "prelaunch_gate": {
            "required_single_face": [10, 10],
            "single_face_wall_seconds_at_most": 20,
            "peak_rss_kib_at_most": 262144,
            "projected_total_wall_seconds_at_most": 10800,
            "workers": 1,
            "launch_authorized": False,
        },
        "continuation_gate_after_exact_cap_cross": {
            "natural_B4_or_higher_degree_launch_if":
                "exact particular Ritz q>=1.002 OR exact gain over inner-only q>=1e-4",
            "otherwise": "retire this outer-polynomial family",
        },
        "warning": (
            "cap-slack shell-only q values near 0.071 are not the combined "
            "inner/cross quotient; no sign follows until the exact cross exists"
        ),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--preflight-only", action="store_true")
    parser.add_argument("--stage-r", type=int)
    args = parser.parse_args()
    if args.stage_r is not None:
        raise SystemExit(
            "target stages are disabled in v1; freeze an authorized successor")
    if not args.preflight_only:
        raise SystemExit("v1 supports --preflight-only only")
    payload = build_plan()
    print(json.dumps(payload, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
