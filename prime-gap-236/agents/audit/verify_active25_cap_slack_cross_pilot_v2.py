#!/usr/bin/env python3
"""Independent prelaunch audit of the active25 cap-slack cross pilot v2.

This checker deliberately performs no target-sized integration.  It derives
the cap-slack I and distinguished-fiber formulas from the Definition-1
geometry on tiny rational examples, recontracts only the already-frozen sparse
exact forms, checks the disabled plan and its cost inputs, and runs the small
normal/optimized unit suites.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from decimal import Decimal, localcontext
from fractions import Fraction as Q
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import statistics
import subprocess
import sys


FILE = Path(__file__).resolve()
REPO = FILE.parents[2]

CAP_SOURCE = REPO / "scripts/active25_count_cap_slack_shell.py"
CAP_TEST = REPO / "scripts/test_active25_count_cap_slack_shell.py"
CAP_RESULTS = tuple(
    REPO / f"results/active25_count_cap_slack_shell_d{degree}_v1.json"
    for degree in range(3))
PILOT_SOURCE = (REPO / "agents/structural-basis/code/"
                "active25_cap_slack_cross_pilot_v2.py")
PILOT_TEST = (REPO / "agents/structural-basis/tests/"
              "test_active25_cap_slack_cross_pilot_v2.py")
PILOT_SPEC = (REPO / "agents/structural-basis/"
              "ACTIVE25-CAP-SLACK-CROSS-PILOT-V2.md")
PILOT_ARTIFACT = (REPO / "agents/structural-basis/results/"
                  "active25_cap_slack_d16_cross_pilot_disabled_v2.json")
V1_SOURCE = (REPO / "agents/structural-basis/code/"
             "active25_outer_b4_j_cross_plan_v1.py")
V1_TEST = (REPO / "agents/structural-basis/tests/"
           "test_active25_outer_b4_j_cross_plan_v1.py")
V1_SPEC = (REPO / "agents/structural-basis/"
           "ACTIVE25-OUTER-B4-J-CROSS-PLAN-V1.md")
V1_ARTIFACT = (REPO / "agents/structural-basis/results/"
               "active25_outer_b4_j_cross_disabled_plan_v1.json")
CORE = (REPO / "agents/small-delta-frontier/"
        "frontier_active25_inner_d16_tagged_shell.py")
SHELL_CORE = (REPO / "agents/small-delta-frontier/"
              "wide_shell_stratum_diagnostic.py")
OUTER_CORE = (REPO / "agents/small-delta-frontier/"
              "two_band_full_outer_constant.py")
INNER_CERT = (REPO / "agents/small-delta-frontier/"
              "bv_aquarter_B16_vector_exact.json")
RADIAL = (REPO / "agents/small-delta-frontier/"
          "bv_D16_radial_two_amplitudes_exact.json")
ANALYTIC = (REPO / "agents/audit/results/"
            "wide_c722_nonuniform_active25_tail_analytic_audit.json")
PROBES = tuple(
    REPO / "agents/small-delta-frontier/results" / name for name in (
        "frontier_active25_innerD16_shell_cross_r00_h17_direct_v2.json",
        "frontier_active25_innerD16_shell_cross_r05_h15_direct_v2.json",
        "frontier_active25_innerD16_shell_cross_r10_h10_direct_v2.json",
        "frontier_active25_innerD16_shell_cross_r15_h10_direct_v2.json",
        "frontier_active25_innerD16_shell_cross_r22_h06_direct_v2.json",
        "frontier_active25_innerD16_shell_cross_r25_h05_direct_v2.json",
    ))

PINS = {
    CAP_SOURCE: "bf460e36c0cc1586b82b6563464dab52773ca8895a87a930ad970b6b4935339b",
    CAP_TEST: "d119c246c9483bb5416d40bc860b683281f89130ea66ac22134a4fba93a6b815",
    CAP_RESULTS[0]: "6e97c4b35d27e40f40e258dd00726d84f2dfc3c910ef9542250d45be9624e195",
    CAP_RESULTS[1]: "3d6532fdf9f641583598d45bae55b9d40641391136e0498748f446d783030b68",
    CAP_RESULTS[2]: "c66cd86055385dc372d948d2f209f84fb850136120d21b55554806ba25d73d63",
    PILOT_SOURCE: "cd20a85e51d623476b5433626ec4ce35d242e8a00a5f706db1af05509b59d913",
    PILOT_TEST: "8f16fdc5a72f8e26ffc5c7b2a0ee5f0e8fc734a4383edeb3a2d414a97df94a1f",
    PILOT_SPEC: "ce965d905274af92a3c64496369ffdb5cd97bf5c75a088432428f5707d032851",
    PILOT_ARTIFACT: "3a07078ca5b480b0d8d554019b42e05b7fb732a1225d97ff761d5b5231abd31c",
    V1_SOURCE: "00eb639b2c4ad954be36aaf8f34268c838a2ab66e5606a8f78ad70b1de0f4145",
    V1_TEST: "e4bc091bcaaa12d02f7cdf07b54c1e746b3da5c1f9031b3d7090ba3dcd4cd10a",
    V1_SPEC: "35a3530e30a881df9ee393086039470708712e5f212f49db40781a3ff1349170",
    V1_ARTIFACT: "69dfd7594e5a14882d742c994cf3da451239eebb0fa3de83c8fddeccd2637df5",
    CORE: "1393a2dd29e5660f10e632b19b6b5eeafe9363bf79b2cd4a8254049d1f9c669a",
    SHELL_CORE: "dbbf990caf2c1e6bc418d525d4becdaedc82af54eec457e8eb5578da29555cc5",
    OUTER_CORE: "75637298284a40be523621ebe1fcdc85bda59dcac42514fb8b50ffd8b460259d",
    INNER_CERT: "59715ddffa483c696c035634a81c3cc8ffe882e9d6eaceec74bea23996b72d62",
    RADIAL: "33fe5d555e736fe5ea3826d569477414fadd2d8a9defc2eaa35718a4f06f82ca",
    ANALYTIC: "111a48a23dbf8bf3fdb058f30e6bc412d2eb3cd605557772d6f34056974b2bda",
    PROBES[0]: "73f351f24defafc0cb6c0a293d258bac33d504e457771ea11362ff5d67bd9107",
    PROBES[1]: "5603845bf7514a4f6dcb4831ed3854b1915189d39424d9d1b47f2bc6f2cd1901",
    PROBES[2]: "37b0d249a0fd17e823f154277bfabe162c3b80c72c344c97686312c7fac7e393",
    PROBES[3]: "5f4d88417ed0b84d26c52512ddf710b35bd9e7d55e9df4a68ad2114dc3602d29",
    PROBES[4]: "8e023686703d353bb63faad3be541238920bc8b7640a4ba3202b924d0385ace9",
    PROBES[5]: "9c13277024543c51b2c945743ce74c5ebfc5b1d2eb3e21d264740bcf0e35e6df",
}

CAP_KEYS = {
    "I_unique_nonzero_calls", "I_upper_nonzero", "J_work", "basis",
    "binary64_discovery_root", "claim_scope", "contains_inner_cross",
    "core_sha256", "denominator_positive", "dependency_sha256",
    "dimension", "exact_denominator", "exact_margin", "exact_numerator",
    "exact_quotient", "format", "kJ_upper_nonzero", "margin_positive",
    "maximum_cap_slack_degree", "parameters", "peak_rss_kib",
    "rational_denominator_limit", "rational_vector",
    "rigorous_matrix_entries", "rigorous_particular_vector_forms",
    "script_sha256", "theorem_ready", "wall_seconds",
}
PILOT_KEYS = {
    "contains_cross_values", "contains_quotient", "continuation",
    "coordinate_formula", "cost_model", "exact_D2_shell_denominator_ranking",
    "no_claim", "package_sha256", "parameters", "pinned_v1_sha256",
    "prelaunch_gate", "rigorous_values", "selection_is_not_upper_bound",
    "source_sha256", "staging", "status", "target_run_started",
    "work_inventory",
}

K = 48
DELTA = Q(361, 50000)
ALPHA_LOW = Q(103, 400)
ALPHA_HIGH = Q(3211, 12000)
ETA = Q(3031, 12000)
SCHEDULE = tuple(Q(value) for value in (
    "597/5000", "633/5000", "669/5000", "141/1000", "737/5000",
    "773/5000", "1553/10000", "809/5000", "81/500", "3329/20000",
    "169/1000", "339/2000", "859/5000", "1737/10000", "219/1250",
    "881/5000", "441/2500", "887/5000", "891/5000", "179/1000",
    "449/2500", "1801/10000", "903/5000", "1811/10000",
    "363/2000", "363/2000"))
TRANSITIVE_DEPENDENCIES = {
    str(ANALYTIC.relative_to(REPO)): PINS[ANALYTIC],
    str(RADIAL.relative_to(REPO)): PINS[RADIAL],
    str(INNER_CERT.relative_to(REPO)): PINS[INNER_CERT],
    str(OUTER_CORE.relative_to(REPO)): PINS[OUTER_CORE],
    str(SHELL_CORE.relative_to(REPO)): PINS[SHELL_CORE],
}


class AuditFailure(RuntimeError):
    pass


def require(condition, message):
    if not condition:
        raise AuditFailure(message)


def sha(value) -> str:
    data = value if isinstance(value, bytes) else Path(value).read_bytes()
    return hashlib.sha256(data).hexdigest()


def strict_json_bytes(data, name):
    def pairs(items):
        answer = {}
        for key, value in items:
            require(key not in answer, f"duplicate JSON key in {name}: {key}")
            answer[key] = value
        return answer

    return json.loads(
        data, object_pairs_hook=pairs,
        parse_constant=lambda value: (_ for _ in ()).throw(
            AuditFailure(f"nonfinite JSON constant in {name}: {value}")))


def strict_json(path):
    return strict_json_bytes(Path(path).read_bytes(), str(path))


def canonical_q(value, name):
    require(type(value) is str, f"{name} is not a rational string")
    try:
        parsed = Q(value)
    except (ValueError, ZeroDivisionError) as error:
        raise AuditFailure(f"invalid rational in {name}") from error
    require(str(parsed) == value, f"noncanonical rational in {name}")
    return parsed


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None,
            f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    require(Path(module.__file__).resolve() == path.resolve(),
            f"wrong module loaded for {path}")
    return module


@dataclass(frozen=True)
class TinySupport:
    k: int
    alpha: Q
    delta: Q
    betas: tuple[Q, ...]

    def beta(self, count):
        require(type(count) is int and 1 <= count <= len(self.betas),
                "tiny-support beta index is invalid")
        return self.betas[count - 1]

    def canonical_support_residual_in_stratum(self, *unused):
        raise AuditFailure("unexpected count-zero tiny I query")


def eval_poly(poly, z, w):
    return sum((Q(value) * z ** a * w ** b
                for (a, b), value in poly.items()), Q(0))


def check_definition_one_geometry():
    """Check the I formula and all four fiber branches with exact literals."""
    cap = load_module("independent_cap_slack_geometry_subject", CAP_SOURCE)

    # Example A: the count-one cap binds and the total constraint is inactive.
    # For each of the two choices of the large coordinate the domain is the
    # rectangle 0<=x<=gamma, 0<=y<=delta.
    cap_bound = TinySupport(2, Q(1, 2), Q(1, 10), (Q(2, 5), Q(1, 2)))
    gamma = cap_bound.beta(1) - cap_bound.delta
    for power in range(5):
        expected = Q(2) * cap_bound.delta * gamma / (power + 1)
        observed = cap.cap_slack_i_moment(cap_bound, 1, power)
        require(observed == expected,
                f"cap-bound tiny I mismatch at power {power}")

    # Example B: the total simplex binds while the cap is inactive.  Directly
    # integrate x^i over 0<=y<=delta, 0<=x<=L-y after expanding
    # ((gamma-x)/gamma)^power.  This is intentionally a different reduction
    # from the producer's two-factor radial expansion.
    total_bound = TinySupport(2, Q(3, 10), Q(1, 10), (Q(1, 2), Q(3, 5)))
    gamma = total_bound.beta(1) - total_bound.delta
    length = total_bound.alpha - total_bound.delta
    require(gamma >= length > total_bound.delta,
            "tiny total-bound geometry changed")
    for power in range(5):
        one_subset = sum(
            (Q((-1) ** i * math.comb(power, i), 1) * gamma ** (-i) *
             (length ** (i + 2) -
              (length - total_bound.delta) ** (i + 2)) /
             ((i + 1) * (i + 2))
             for i in range(power + 1)), Q(0))
        expected = 2 * one_subset
        observed = cap.cap_slack_i_moment(total_bound, 1, power)
        require(observed == expected,
                f"total-bound tiny I mismatch at power {power}")

    # Literal distinguished-coordinate endpoints from Definition 1.  The
    # points below lie respectively in Sdelta, Stotal, Lbig, and Ltotal.
    support = TinySupport(
        4, Q(3, 10), Q(1, 20),
        (Q(3, 20), Q(1, 5), Q(1, 4), Q(3, 10)))
    r, h = 1, 1
    u0 = (r + h) * support.delta
    samples = {
        "Sdelta": (Q(1, 100), Q(1, 200)),
        "Stotal": (Q(2, 25), Q(3, 40)),
        "Lbig": (Q(1, 50), Q(1, 100)),
        "Ltotal": (Q(1, 50), Q(7, 100)),
    }
    checked = 0
    for branch, (z, w) in samples.items():
        count = r if branch.startswith("S") else r + 1
        gamma = support.beta(count) - count * support.delta
        require(gamma > 0 and z < gamma, "tiny marginal cap is invalid")
        total_upper = support.alpha - u0 - z - w
        cap_upper = support.beta(count) - r * support.delta - z
        if branch == "Sdelta":
            require(total_upper > support.delta,
                    "Sdelta literal is on the wrong branch")
        elif branch == "Stotal":
            require(Q(0) < total_upper < support.delta,
                    "Stotal literal is on the wrong branch")
        elif branch == "Lbig":
            require(cap_upper < total_upper,
                    "Lbig literal is on the wrong branch")
        else:
            require(support.delta < total_upper < cap_upper,
                    "Ltotal literal is on the wrong branch")
        for degree in range(5):
            if branch == "Sdelta":
                literal = support.delta * (gamma - z) ** degree
            elif branch == "Stotal":
                literal = total_upper * (gamma - z) ** degree
            else:
                lower = support.delta
                upper = cap_upper if branch == "Lbig" else total_upper
                anchor = gamma + support.delta - z
                literal = ((anchor - lower) ** (degree + 1) -
                           (anchor - upper) ** (degree + 1)) / (degree + 1)
            literal /= gamma ** degree
            observed = eval_poly(
                cap.cap_slack_marginal(support, r, h, branch, degree), z, w)
            require(observed == literal,
                    f"{branch} tiny marginal mismatch at degree {degree}")
            checked += 1
    return {
        "coordinate":
            "1_R*((B_R-R*delta-z_R)/(B_R-R*delta))^d",
        "tiny_I_exact_cases": 10,
        "tiny_marginal_exact_cases": checked,
        "marginal_branches": ["Sdelta", "Stotal", "Ltotal", "Lbig"],
        "maximum_literal_degree": 4,
    }


def expected_parameters():
    return {
        "k": K, "delta": str(DELTA), "alpha_high": str(ALPHA_HIGH),
        "alpha_low": str(ALPHA_LOW), "eta": str(ETA),
        "schedule": [str(value) for value in SCHEDULE],
    }


def expected_labels(degree):
    return ((0, 0),) + tuple(
        (count, power) for count in range(1, 26)
        for power in range(degree + 1))


def parse_sparse(raw, dimension, name):
    require(type(raw) is list, f"{name} is not a list")
    result = []
    keys = []
    for position, row in enumerate(raw):
        require(type(row) is list and len(row) == 3,
                f"malformed {name} entry {position}")
        i, j, value = row
        require(type(i) is int and type(j) is int and
                0 <= j <= i < dimension,
                f"invalid {name} indices at entry {position}")
        number = canonical_q(value, f"{name}[{position}]")
        require(number != 0, f"explicit zero in {name}")
        keys.append((i, j))
        result.append((i, j, number))
    require(keys == sorted(keys) and len(keys) == len(set(keys)),
            f"{name} is not canonical sparse order")
    return result


def contract_sparse(entries, vector):
    return sum(
        (value * vector[i] * vector[j] * (1 if i == j else 2)
         for i, j, value in entries), Q(0))


def audit_shell_result(path, degree):
    raw = strict_json(path)
    require(type(raw) is dict and set(raw) == CAP_KEYS,
            f"cap D{degree} schema changed")
    labels = expected_labels(degree)
    dimension = len(labels)
    require(raw["format"] == "active25-count-cap-slack-shell-exact-v1" and
            raw["claim_scope"] ==
            "exact shell-only finite forms and particular Rayleigh vector" and
            raw["theorem_ready"] is False and
            raw["contains_inner_cross"] is False and
            raw["rigorous_matrix_entries"] is True and
            raw["rigorous_particular_vector_forms"] is True and
            raw["script_sha256"] == PINS[CAP_SOURCE] and
            raw["core_sha256"] == PINS[CORE] and
            raw["dependency_sha256"] == TRANSITIVE_DEPENDENCIES and
            raw["parameters"] == expected_parameters() and
            raw["maximum_cap_slack_degree"] == degree and
            raw["dimension"] == dimension and
            raw["basis"] == [list(label) for label in labels] and
            raw["rational_denominator_limit"] == 10**9,
            f"cap D{degree} identity metadata changed")
    vector_raw = raw["rational_vector"]
    require(type(vector_raw) is list and len(vector_raw) == dimension,
            f"cap D{degree} vector dimension changed")
    vector = [canonical_q(value, f"D{degree} vector")
              for value in vector_raw]
    require(any(vector) and max(abs(value) for value in vector) == 1,
            f"cap D{degree} vector normalization changed")
    i_entries = parse_sparse(
        raw["I_upper_nonzero"], dimension, f"D{degree} I")
    b_entries = parse_sparse(
        raw["kJ_upper_nonzero"], dimension, f"D{degree} kJ")
    require(all(labels[i][0] == labels[j][0]
                for i, j, _ in i_entries),
            f"cap D{degree} I lost exact-count block diagonality")
    require(all(abs(labels[i][0] - labels[j][0]) <= 1
                for i, j, _ in b_entries),
            f"cap D{degree} J lost adjacent-count sparsity")
    per_count = degree + 1
    expected_i = 1 + 25 * per_count * (per_count + 1) // 2
    expected_b = (1 + 25 * per_count * (per_count + 1) // 2 +
                  per_count + 24 * per_count * per_count)
    require(len(i_entries) == raw["I_unique_nonzero_calls"] == expected_i and
            len(b_entries) == expected_b,
            f"cap D{degree} sparse entry inventory changed")

    denominator = contract_sparse(i_entries, vector)
    numerator = contract_sparse(b_entries, vector)
    margin = numerator - denominator
    require(denominator > 0 and
            canonical_q(raw["exact_denominator"], "exact denominator") ==
            denominator and
            canonical_q(raw["exact_numerator"], "exact numerator") ==
            numerator and
            canonical_q(raw["exact_margin"], "exact margin") == margin and
            canonical_q(raw["exact_quotient"], "exact quotient") ==
            numerator / denominator and
            raw["denominator_positive"] is True and
            raw["margin_positive"] is (margin > 0),
            f"cap D{degree} exact stored-form contraction failed")
    require(type(raw["wall_seconds"]) in (int, float) and
            not isinstance(raw["wall_seconds"], bool) and
            math.isfinite(raw["wall_seconds"]) and
            raw["wall_seconds"] > 0 and
            type(raw["peak_rss_kib"]) is int and raw["peak_rss_kib"] > 0,
            f"cap D{degree} resource metadata is invalid")

    faces = 585
    n0, n = 1, degree + 1
    expected_integrals = (
        35 * 4 * (n0 + n) ** 2 +
        sum(35 - r for r in range(1, 25)) * 4 * (2 * n) ** 2 +
        10 * 4 * n ** 2)
    expected_work = {
        tag: {"domains": 9240,
              "polynomial_integrals": expected_integrals}
        for tag in ("hh", "hl", "lh", "ll")
    }
    require(raw["J_work"] == expected_work and faces ==
            sum(35 - r for r in range(26)),
            f"cap D{degree} shell work metadata changed")
    return raw, labels, vector, i_entries, {
        "degree": degree, "dimension": dimension,
        "I_sparse_entries": len(i_entries),
        "kJ_sparse_entries": len(b_entries),
        "exact_contraction_matches": True,
        "contains_inner_cross": False,
        "theorem_ready": False,
    }


def exact_denominator_ranking(raw, labels, vector, i_entries):
    contributions = {count: Q(0) for count in range(26)}
    for i, j, value in i_entries:
        count = labels[i][0]
        require(count == labels[j][0], "D2 denominator has a cross-count term")
        contributions[count] += (
            value * vector[i] * vector[j] * (1 if i == j else 2))
    total = sum(contributions.values(), Q(0))
    require(total == Q(raw["exact_denominator"]) and total > 0 and
            all(value >= 0 for value in contributions.values()),
            "D2 exact count contributions do not reconstruct the denominator")
    ranked = sorted(contributions, key=contributions.get, reverse=True)
    selected_counts = tuple(range(9, 15))
    selected = sum((contributions[count] for count in selected_counts), Q(0))
    fraction = selected / total
    record = {
        "total": str(total), "selected": str(selected),
        "selected_fraction": str(fraction), "ranked_counts": ranked,
        "fractions_by_count": {
            str(count): str(contributions[count] / total)
            for count in range(26)},
    }
    record_bytes = json.dumps(
        record, sort_keys=True, separators=(",", ":")).encode("ascii")
    require(ranked[:6] == [12, 11, 13, 10, 9, 14] and
            set(ranked[:6]) == set(selected_counts) and
            Q(19, 20) < fraction < 1 and
            sha(record_bytes) ==
            "3a15843d88e138f4e33a8f16d11f07f689a6cabeaa3ba4b3e42f9a71d5d310be",
            "D2 selected-count ranking/share changed")
    exact = str(fraction)
    with localcontext() as context:
        context.prec = 50
        decimal = str(Decimal(fraction.numerator) /
                      Decimal(fraction.denominator))
    return {
        "selected_counts": list(selected_counts),
        "ranked_top_eight": ranked[:8],
        "selected_fraction_exact": exact,
        "selected_fraction_exact_character_count": len(exact),
        "selected_fraction_exact_sha256": sha(exact.encode("ascii")),
        "selected_fraction_decimal_50": decimal,
        "selected_fraction_gt_19_over_20": True,
        "exact_contribution_record_sha256": sha(record_bytes),
        "interpretation": "share of the pinned D2 particular vector I denominator",
        "selection_is_not_upper_bound": True,
    }


def independent_work_inventory():
    max_h_base = int(ETA // DELTA)
    require(max_h_base == 34, "eta/delta face cutoff changed")
    pilot_counts = set(range(9, 15))
    pilot_n = {count: (3 if count in pilot_counts else 1)
               for count in range(26)}
    labels = [[count, degree]
              for count in range(26)
              for degree in ((0, 1, 2) if count in pilot_counts else (0,))]
    by_r = {}
    faces_total = pilot_terms = full_terms = natural_terms = 0
    for r in range(26):
        faces = max_h_base - r + 1
        small = pilot_n[r]
        large = pilot_n.get(r + 1, 0)
        terms = faces * 4 * (2 * small + 2 * large)
        by_r[str(r)] = {
            "faces": faces,
            "labels_on_small_branches": small,
            "labels_on_large_branches": large,
            "weighted_branch_column_terms": terms,
        }
        faces_total += faces
        pilot_terms += terms
        full_small = 1 if r == 0 else 3
        full_large = 0 if r == 25 else 3
        full_terms += faces * 4 * (2 * full_small + 2 * full_large)
        natural_terms += faces * 4 * 4 * 10
    require((faces_total, pilot_terms, full_terms, natural_terms) ==
            (585, 13888, 27280, 93600),
            "independent work totals changed")
    return {
        "dimension": len(labels), "labels": labels,
        "all_degree_zero_counts": list(range(26)),
        "positive_degree_counts": list(range(9, 15)),
        "positive_degrees": [1, 2], "common_r": list(range(26)),
        "faces": faces_total,
        "weighted_branch_column_terms": pilot_terms,
        "full_d0_d2_terms": full_terms,
        "natural_b4_terms": natural_terms,
        "by_common_r": by_r,
    }


def check_factor_and_cross_conventions():
    v1 = load_module("independent_cap_slack_factor_subject", V1_SOURCE)
    hh = [[Q(5), Q(2)], [Q(2), Q(7)]]
    hl = [[Q(1), Q(3)], [Q(4), Q(2)]]
    ll = [[Q(6), Q(1)], [Q(1), Q(8)]]
    expected_outer = [
        [Q(K) * (hh[i][j] - hl[i][j] - hl[j][i] + ll[i][j])
         for j in range(2)] for i in range(2)]
    observed_outer = v1.assemble_natural_outer_b48(hh, hl, ll, k=K)
    require(observed_outer == expected_outer ==
            [[Q(432), Q(-192)], [Q(-192), Q(528)]],
            "ordered mixed-block/factor-48 convention failed")
    require(observed_outer[0][1] !=
            K * (hh[0][1] - 2 * hl[0][1] + ll[0][1]),
            "asymmetric mixed block was incorrectly doubled entrywise")
    rh, rl, vh, vl = [3, 5], [1, 2], [7, 11], [2, 3]
    amplitudes = (Q(3), Q(2))
    expected_cross = [
        Q(K) * (amplitudes[1] * (Q(rh[i]) - Q(rl[i])) +
                (amplitudes[0] - amplitudes[1]) *
                (Q(vh[i]) - Q(vl[i])))
        for i in range(2)]
    observed_cross = v1.assemble_inner_cross_b48(
        rh, rl, vh, vl, amplitudes, k=K)
    require(observed_cross == expected_cross == [Q(432), Q(672)],
            "inner/shell cross factor/amplitude convention failed")
    return {
        "outer_formula": "48*(HH-HL-HL^T+LL)",
        "inner_cross_formula":
            "48*(a_R*(RH-RL)+(a_inner-a_R)*(VH-VL))",
        "mixed_block_transpose_required": True,
        "matrix_entry_has_no_polarization_factor": True,
        "tiny_asymmetric_matrix_fixture": [[str(x) for x in row]
                                            for row in observed_outer],
        "tiny_cross_fixture": [str(x) for x in observed_cross],
    }


def check_runtime_model(pilot):
    expected_faces = ((0, 17), (5, 15), (10, 10),
                      (15, 10), (22, 6), (25, 5))
    times, rss = [], []
    for path, (common_r, selected_h) in zip(PROBES, expected_faces):
        row = strict_json(path)
        require(row.get("status") ==
                "frontier-inner-D16-tagged-shell-exact-cost-probe" and
                row.get("claim_scope") ==
                "one exact face for cost only; no quotient" and
                row.get("rigorous_values") is True and
                row.get("theorem_ready") is False and
                row.get("complete_cross") is False and
                row.get("evaluation_mode") == "direct-full-grouped" and
                row.get("common_r") == common_r and
                row.get("selected_h") == selected_h and
                row.get("faces") == 1,
                f"cost probe identity changed: {path}")
        wall = row.get("wall_seconds")
        peak = row.get("peak_rss_kib")
        require(type(wall) in (int, float) and not isinstance(wall, bool) and
                math.isfinite(wall) and wall > 0 and
                type(peak) is int and peak > 0,
                f"cost probe resources are invalid: {path}")
        times.append(float(wall))
        rss.append(peak)
    mean = statistics.mean(times)
    projected = 2 * mean * 585
    model = pilot["cost_model"]
    require(model == {
                "pinned_constant_cross_face_mean_seconds": mean,
                "pinned_constant_cross_face_peak_rss_kib": max(rss),
                "projected_pilot_seconds_conservative": projected,
                "projected_pilot_hours_conservative": projected / 3600,
                "memory_gate_kib": 262144,
            }, "pilot cost model differs from six frozen probes")
    gate = pilot["prelaunch_gate"]
    require(gate == {
                "required_face": [10, 10],
                "wall_seconds_at_most": 20,
                "peak_rss_kib_at_most": 262144,
                "projected_complete_seconds_at_most": 7200,
                "launch_authorized": False,
            } and projected < 7200 and max(rss) < 262144 and
            pilot["staging"]["workers"] == 1,
            "pilot prelaunch gate changed")
    return {
        "probe_wall_seconds": times,
        "probe_peak_rss_kib": rss,
        "constant_face_mean_seconds": mean,
        "projected_pilot_seconds": projected,
        "projected_pilot_hours": projected / 3600,
        "projected_complete_gate_seconds": 7200,
        "memory_gate_kib": 262144,
        "required_pilot_face": [10, 10],
        "required_pilot_face_executed": False,
        "launch_authorized": False,
        "note": (
            "the same-face constant probe is calibration only; the cap-pilot "
            "wall/RSS gate remains outstanding"),
    }


def run_small_subprocess_checks(pilot):
    commands = (
        (str(CAP_TEST), False), (str(CAP_TEST), True),
        (str(V1_TEST), False), (str(V1_TEST), True),
        (str(PILOT_TEST), False), (str(PILOT_TEST), True),
    )
    labels = []
    for test, optimized in commands:
        command = [sys.executable]
        if optimized:
            command.append("-O")
        command.append(test)
        completed = subprocess.run(
            command, cwd=REPO, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, check=False)
        require(completed.returncode == 0 and b"OK" in completed.stderr,
                f"small test failed: {' '.join(command)}")
        labels.append(("-O " if optimized else "") +
                      str(Path(test).relative_to(REPO)))

    normal = subprocess.run(
        [sys.executable, str(PILOT_SOURCE), "--preflight-only"], cwd=REPO,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    optimized = subprocess.run(
        [sys.executable, "-O", str(PILOT_SOURCE), "--preflight-only"],
        cwd=REPO, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    require(normal.returncode == optimized.returncode == 0 and
            normal.stderr == optimized.stderr == b"" and
            normal.stdout == optimized.stdout,
            "normal/-O pilot preflight streams differ")
    emitted = strict_json_bytes(normal.stdout, "pilot preflight stdout")
    require(emitted == pilot,
            "pilot preflight payload differs from frozen artifact semantics")
    for optimized_mode in (False, True):
        command = [sys.executable]
        if optimized_mode:
            command.append("-O")
        command.extend((str(PILOT_SOURCE), "--stage-r", "10"))
        denied = subprocess.run(
            command, cwd=REPO, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, check=False)
        require(denied.returncode != 0 and b"disabled" in denied.stderr and
                denied.stdout == b"",
                "disabled target-stage CLI unexpectedly opened")
    return {
        "normal_and_optimized_test_commands_passed": labels,
        "test_processes": len(labels),
        "preflight_normal_optimized_byte_identical": True,
        "preflight_semantically_matches_frozen_artifact": True,
        "normal_and_optimized_stage_r_rejected": True,
    }


def build():
    for path, expected in PINS.items():
        require(sha(path) == expected, f"frozen input changed: {path}")

    definition_geometry = check_definition_one_geometry()
    shell_rows = []
    audited = []
    for degree, path in enumerate(CAP_RESULTS):
        raw, labels, vector, i_entries, summary = audit_shell_result(
            path, degree)
        shell_rows.append((raw, labels, vector, i_entries))
        audited.append(summary)
    d2_raw, d2_labels, d2_vector, d2_i = shell_rows[2]
    ranking = exact_denominator_ranking(
        d2_raw, d2_labels, d2_vector, d2_i)

    pilot = strict_json(PILOT_ARTIFACT)
    require(type(pilot) is dict and set(pilot) == PILOT_KEYS,
            "pilot artifact schema changed")
    expected_package = {
        str(PILOT_SOURCE.relative_to(REPO)): PINS[PILOT_SOURCE],
        str(PILOT_TEST.relative_to(REPO)): PINS[PILOT_TEST],
        str(PILOT_SPEC.relative_to(REPO)): PINS[PILOT_SPEC],
    }
    expected_v1 = {
        str(V1_SOURCE.relative_to(REPO)): PINS[V1_SOURCE],
        str(V1_TEST.relative_to(REPO)): PINS[V1_TEST],
        str(V1_SPEC.relative_to(REPO)): PINS[V1_SPEC],
        str(V1_ARTIFACT.relative_to(REPO)): PINS[V1_ARTIFACT],
    }
    require(pilot["status"] ==
            "active25-cap-slack-d16-cross-pilot-disabled-v2" and
            pilot["rigorous_values"] is False and
            pilot["target_run_started"] is False and
            pilot["contains_cross_values"] is False and
            pilot["contains_quotient"] is False and
            pilot["selection_is_not_upper_bound"] is True and
            pilot["source_sha256"] == PINS[PILOT_SOURCE] and
            pilot["package_sha256"] == expected_package and
            pilot["pinned_v1_sha256"] == expected_v1 and
            pilot["coordinate_formula"] ==
            "1_{count=R}*((B_R-R*delta-z_R)/(B_R-R*delta))^d" and
            pilot["no_claim"] ==
            "no J cross, combined quotient, or theorem claim",
            "pilot disabled scope/provenance changed")

    # Definition 1: every displayed B exceeds delta, adjacent increments lie
    # in [0,delta], and count 25 is the last nonempty cap stratum.
    require(len(SCHEDULE) == 26 and
            all(value > DELTA for value in SCHEDULE) and
            all(SCHEDULE[i] <= SCHEDULE[i + 1] <= SCHEDULE[i] + DELTA
                for i in range(25)),
            "Definition-1 B schedule changed")
    active = [0] + [count for count, value in enumerate(SCHEDULE, start=1)
                    if value > count * DELTA]
    require(active == list(range(26)) and
            SCHEDULE[24] > 25 * DELTA and
            SCHEDULE[25] < 26 * DELTA,
            "active-count boundary is not exactly 0..25")

    work = independent_work_inventory()
    require(pilot["work_inventory"] == work,
            "pilot work artifact differs from independent inventory")
    rank_meta = pilot["exact_D2_shell_denominator_ranking"]
    require(rank_meta == {
                "exact_reconstruction_sha256":
                    ranking["exact_contribution_record_sha256"],
                "ranked_counts": [12, 11, 13, 10, 9, 14, 8, 15,
                                  7, 16, 6, 17, 5, 18, 4, 3, 19, 2,
                                  20, 1, 21, 22, 0, 23, 24, 25],
                "selected_counts": list(range(9, 15)),
                "selected_fraction_gt_19_over_20": True,
                "total_matches_pinned_exact_denominator": True,
            }, "pilot D2 ranking summary changed")
    factor = check_factor_and_cross_conventions()
    runtime = check_runtime_model(pilot)
    subprocess_checks = run_small_subprocess_checks(pilot)

    for path, expected in PINS.items():
        require(sha(path) == expected, f"input changed during audit: {path}")
    return {
        "status": "SCOPED PRELAUNCH PASS",
        "scope": (
            "count-specific cap-slack geometry, frozen shell forms, and "
            "disabled pruned D16-cross plan; no target integration"),
        "checker_sha256": sha(FILE),
        "input_sha256": {
            str(path.relative_to(REPO)): expected
            for path, expected in PINS.items()},
        "checks": {
            "definition_1_geometry": definition_geometry,
            "shell_exact_outputs": audited,
            "factor_48_and_cross": factor,
            "active_counts": active,
            "I_count_diagonal_and_J_count_bandwidth_one": True,
            "selected_D2_denominator_share": ranking,
            "work_inventory": {
                "coordinates": work["dimension"],
                "faces": work["faces"],
                "pilot_weighted_branch_column_terms":
                    work["weighted_branch_column_terms"],
                "full_D2_weighted_branch_column_terms":
                    work["full_d0_d2_terms"],
                "natural_B4_weighted_branch_column_terms":
                    work["natural_b4_terms"],
            },
            "runtime_gates": runtime,
            "small_normal_optimized_execution": subprocess_checks,
            "target_run_started": False,
            "contains_cross_values": False,
            "contains_combined_quotient": False,
            "launch_authorized": False,
        },
        "decision": (
            "the disabled package is internally consistent and may proceed "
            "only to its separately authorized one-face resource gate; a "
            "full cross remains unauthorized"),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    payload = (json.dumps(build(), sort_keys=True, separators=(",", ":"),
                          allow_nan=False) + "\n").encode("ascii")
    if args.output is not None:
        target = args.output.resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                             0o644)
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    print(payload.decode("ascii"), end="")


if __name__ == "__main__":
    main()
