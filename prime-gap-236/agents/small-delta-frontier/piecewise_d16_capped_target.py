#!/usr/bin/env python3
"""Staged capped contractions for the piecewise-dilated BV D16 vector.

This module is deliberately separate from the one-dilation discovery driver.
The inner band uses the original polynomial (``c_inner=1``), whereas the
outer band uses the natural dilation ``c_outer=3090/3211``.  For Definition 5
the inner/inner block has cutoff eta_1 and every block involving the outer
band has cutoff eta_2.

The expensive commands below produce Decimal discovery data only.  They are
split by total large count for I and common large count for J.  In particular,
no Decimal sign emitted by this module is a sieve certificate.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal
from fractions import Fraction as Q
import hashlib
import json
from math import comb
import os
from pathlib import Path
import resource
import stat
import sys
import time


FILE = Path(__file__).resolve()
REPO = FILE.parents[2]
EI_DIR = REPO / "agents/exact-integrator"
EI_SRC = EI_DIR / "src"
STRUCTURAL_CODE = REPO / "agents/structural-basis/code"
sys.path[:0] = [str(EI_SRC), str(EI_DIR), str(STRUCTURAL_CODE)]

import exact_integrator as ei  # noqa: E402
import grouped_fixed_vector as grouped  # noqa: E402
import fixed_vector_support_kernel as kernel_core  # noqa: E402

CERT = REPO / "agents/small-delta-frontier/bv_aquarter_B16_vector_exact.json"
ANALYTIC = REPO / (
    "agents/audit/results/wide_c722_volume_ramp_analytic_audit.json")
SHELL_DIAGNOSTIC = REPO / (
    "agents/small-delta-frontier/results/"
    "wide_volume_ramp_shell_stratum_pencil_v3.json")
PIECEWISE_SCRIPT = REPO / "scripts/evaluate_two_band_piecewise_dilations.py"
PIECEWISE_ARTIFACT = REPO / (
    "results/wide_c722_D16_piecewise_cinner1_couter_natural_exact.json")

PINNED_PIECEWISE_SCRIPT_SHA256 = \
    "f3bbc9c6c35e2cb8b1ac7ce6accf56144c01099be81dfe288407b4552165b7bb"
PINNED_PIECEWISE_ARTIFACT_SHA256 = \
    "e30a9a5f356b0303559bd1d3c1cb7a48474e973ec97b164c00832c919f761cb7"

INNER_C = Q(1)
OUTER_C = Q(3090, 3211)
K = 48
DEGREE = 16
DELTA = Q(361, 50000)
ALPHA_INNER = Q(103, 400)
ETA_INNER = Q(97, 400)
ALPHA_OUTER = Q(3211, 12000)
ETA_OUTER = Q(3031, 12000)
BRANCHES = ("Sdelta", "Stotal", "Ltotal", "Lbig")
SELECTED_COUNTS = (10, 11, 12, 13, 14)
BLOCK_TAGS = ("fh", "fl", "hh", "hl", "lh", "ll")

PINNED = {
    EI_SRC / "exact_integrator.py":
        "941ee82bc72fd8488a95eb5e536fe47f8c95d39a1b618dae7d6ef7eb27122e52",
    EI_DIR / "grouped_fixed_vector.py":
        "47167e92a0f346e969706dc282ccb2dfd4ac31a0a75b654938ffbe8423cf4a4a",
    STRUCTURAL_CODE / "fixed_vector_support_kernel.py":
        "774b8f3a09d77d79d6e4abe56cce4ed1eb82fc5f71ca08cb033bd383091073a3",
    CERT:
        "59715ddffa483c696c035634a81c3cc8ffe882e9d6eaceec74bea23996b72d62",
    ANALYTIC:
        "88b6e1aeb04bd2e7d8600e5f4a7bcca8726b5307b95e5a4e9337a20c8f7afa96",
    SHELL_DIAGNOSTIC:
        "5ad7b42edfcae72b27a0e6221a1f5c1296695749c56d69309e01f0d505abdaf9",
    PIECEWISE_SCRIPT: PINNED_PIECEWISE_SCRIPT_SHA256,
    PIECEWISE_ARTIFACT: PINNED_PIECEWISE_ARTIFACT_SHA256,
}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(Path(path).read_bytes())


def require_piecewise_pins():
    pins = {}
    for path, expected in PINNED.items():
        observed = sha256_file(path)
        if observed != expected:
            raise RuntimeError(f"piecewise dependency changed: {path}")
        pins[str(path.relative_to(REPO))] = observed
    return dict(sorted(pins.items()))


def strict_json_bytes(data: bytes):
    def pairs(items):
        answer = {}
        for key, value in items:
            if key in answer:
                raise ValueError(f"duplicate JSON key: {key}")
            answer[key] = value
        return answer

    def reject(token):
        raise ValueError(f"non-exact JSON token: {token}")

    return json.loads(data, object_pairs_hook=pairs, parse_float=reject,
                      parse_constant=reject)


def canonical_q(value: Q) -> str:
    value = Q(value)
    return (str(value.numerator) if value.denominator == 1 else
            f"{value.numerator}/{value.denominator}")


def parse_q(text: str) -> Q:
    if not isinstance(text, str):
        raise TypeError("rational must be a string")
    value = Q(text)
    if canonical_q(value) != text:
        raise ValueError("noncanonical rational")
    return value


def volume_ramp_schedule():
    return tuple(min(Q(49, 625) + (m - 1) * DELTA, Q(1599, 10000))
                 for m in range(1, 24))


SCHEDULE = volume_ramp_schedule()


@dataclass(frozen=True)
class ScheduledSupport(ei.OneStratumSupport):
    schedule: tuple = ()

    @classmethod
    def make(cls, k, alpha, delta, eta, schedule):
        schedule = tuple(schedule)
        if (isinstance(k, bool) or not isinstance(k, int) or k < 1 or
                not schedule or len(schedule) > k or
                any(value <= delta for value in schedule)):
            raise ValueError("invalid scheduled support")
        if any(right < left or right > left + delta
               for left, right in zip(schedule, schedule[1:])):
            raise ValueError("invalid scheduled transition")
        return cls(k, alpha, delta, eta, schedule[0],
                   schedule[min(1, len(schedule) - 1)],
                   schedule[min(2, len(schedule) - 1)], schedule)

    def beta(self, r):
        if isinstance(r, bool) or not isinstance(r, int) or r <= 0:
            raise ValueError("beta requires positive integer count")
        return self.schedule[min(r, len(self.schedule)) - 1]


def validate_geometry_sources():
    analytic = strict_json_bytes(ANALYTIC.read_bytes())
    expected = {
        "A": ["-3/400", "1/4", "3121/12000"],
        "delta": "361/50000", "epsilon": "3/400",
        "iic_aux_width": "288800001/40000000000",
        "inner_active": list(range(36)), "inward": "1/100000000000",
        "k": K, "outer_active": list(range(23)),
        "outer_cap": "1599/10000", "outer_start": "49/625",
        "source_zeta_max": "1/10000000000000",
    }
    if (analytic.get("status") != "AUDIT PASS" or
            analytic.get("parameters") != expected or
            analytic.get("schedule_id") != "volume-ramp"):
        raise ValueError("analytic volume-ramp artifact changed schema")
    diagnostic = strict_json_bytes(SHELL_DIAGNOSTIC.read_bytes())
    if (diagnostic.get("active_strata") != list(range(23)) or
            tuple(parse_q(x) for x in
                  diagnostic.get("parameters", {}).get(
                      "outer_schedule", ())) != SCHEDULE):
        raise ValueError("shell diagnostic schedule changed")


def load_source():
    raw = strict_json_bytes(CERT.read_bytes())
    basis = tuple((int(a), tuple(int(x) for x in lam))
                  for a, lam in raw.get("basis", ()))
    vector = tuple(parse_q(x) for x in raw.get("rational_vector", ()))
    if (raw.get("k") != K or raw.get("degree") != DEGREE or
            basis != tuple(ei.even_basis(DEGREE)) or len(vector) != 307 or
            raw.get("parameters") != {
                "alpha": "103/400", "beta1": "103/400",
                "beta2": "103/400", "beta3plus": "103/400",
                "delta": "7/250", "eta": "97/400"}):
        raise ValueError("source certificate schema changed")
    return basis, vector


def dilate(basis, vector, c):
    c = Q(c)
    if not Q(9, 10) < c < Q(11, 10):
        raise ValueError("dilation outside frozen interval")
    index = {label: i for i, label in enumerate(basis)}
    if len(index) != len(basis):
        raise ValueError("duplicate basis labels")
    answer = [Q(0)] * len(basis)
    for coefficient, (a, lam) in zip(vector, basis):
        for b in range(a + 1):
            target = index.get((b, lam))
            if target is None:
                raise ValueError("dilation left finite basis")
            answer[target] += (coefficient * comb(a, b) *
                               (1 - c) ** (a - b) *
                               c ** (b + sum(lam)))
    return tuple(answer)


def transformed_source_bytes(c):
    basis, source = load_source()
    vector = dilate(basis, source, c)
    payload = {
        "basis": [[a, list(lam)] for a, lam in basis],
        "basis_dimension": len(basis), "degree": DEGREE, "k": K,
        "rational_vector": [canonical_q(x) for x in vector],
    }
    return ((json.dumps(payload, sort_keys=True, separators=(",", ":")) +
             "\n").encode("ascii"), basis, vector)


def as_scalar(value, scalar):
    value = Q(value)
    return scalar(value.numerator) / scalar(value.denominator)


def make_supports(scalar):
    convert = lambda x: as_scalar(x, scalar)
    schedule = tuple(convert(x) for x in SCHEDULE)
    inner_eta1 = ei.OneStratumSupport(
        K, convert(ALPHA_INNER), convert(DELTA), convert(ETA_INNER),
        convert(ALPHA_INNER), convert(ALPHA_INNER), convert(ALPHA_INNER))
    inner_eta2 = ei.OneStratumSupport(
        K, convert(ALPHA_INNER), convert(DELTA), convert(ETA_OUTER),
        convert(ALPHA_INNER), convert(ALPHA_INNER), convert(ALPHA_INNER))
    high = ScheduledSupport.make(
        K, convert(ALPHA_OUTER), convert(DELTA), convert(ETA_OUTER), schedule)
    low = ScheduledSupport.make(
        K, convert(ALPHA_INNER), convert(DELTA), convert(ETA_OUTER), schedule)
    return {"inner_eta1": inner_eta1, "inner_eta2": inner_eta2,
            "high": high, "low": low}


def component_data(evaluator):
    components = evaluator.marginal_components()
    lrs = tuple(sorted({lr for lr, _, _ in components}))
    by_lr = {lr: tuple((e, a, value)
                       for (other, e, a), value in components.items()
                       if other == lr)
             for lr in lrs}
    return lrs, by_lr


def active_branch_blocks(evaluator, data, r, h, dimension, outer):
    lrs, by_lr = data
    answer = {}
    for branch in BRANCHES:
        constraints = evaluator.support._branch_constraints(r, h, branch)
        if dimension == 0:
            interval = evaluator.support._branch_interval(0, 0, branch)
            active = (interval is not None and
                      interval[0] <= evaluator.zero <= interval[1])
        else:
            active = (constraints is not None and evaluator.integrate_domain(
                {(0, 0): evaluator.one}, dimension, r, outer,
                constraints) > evaluator.zero)
        block = {}
        if active:
            for lr in lrs:
                polynomial = defaultdict(evaluator.scalar)
                for e, a, coefficient in by_lr[lr]:
                    grouped.add_poly(
                        polynomial,
                        dict(evaluator.support._marginal_poly(
                            r, h, branch, e, a)), coefficient)
                if polynomial:
                    block[lr] = dict(polynomial)
        answer[branch] = (block, constraints) if block else ({}, constraints)
    return answer


def branch_total_r(common_r, branch):
    if branch in ("Sdelta", "Stotal"):
        return common_r
    if branch in ("Ltotal", "Lbig"):
        return common_r + 1
    raise ValueError("unknown branch")


def ordered_orbit_product(left, right, evaluator):
    combined = {}
    for left_orbit, left_poly in left.items():
        for right_orbit, right_poly in right.items():
            product = ei._poly_mul(left_poly, right_poly)
            for nu, multiplicity in evaluator.kernel.orbit_lookup(
                    left_orbit, right_orbit):
                destination = combined.setdefault(
                    nu, defaultdict(evaluator.scalar))
                grouped.add_poly(destination, product,
                                 evaluator.scalar(multiplicity))
    return {nu: dict(poly) for nu, poly in combined.items() if poly}


def encode_table(table):
    return [{"left_total_count": left, "right_total_count": right,
             "value": str(value)}
            for (left, right), value in sorted(table.items())]


def strict_piecewise_reference():
    raw = strict_json_bytes(PIECEWISE_ARTIFACT.read_bytes())
    if (raw.get("format") != "exact-uncapped-two-band-piecewise-dilations-v1"
            or raw.get("status") != "exact-search-point"
            or raw.get("analytic_support_approved") is not False
            or raw.get("theorem_ready") is not False
            or raw.get("certificate_sha256") !=
            PINNED[CERT]
            or raw.get("parameters") != {
                "alpha1": "103/400", "alpha2": "3211/12000",
                "delta": "361/50000", "eta1": "97/400",
                "eta2": "3031/12000", "inner_c": "1",
                "k": 48, "outer_c": "3090/3211"}):
        raise ValueError("piecewise exact reference schema changed")
    imat, bmat = raw.get("I_matrix"), raw.get("kJ_matrix")
    if (not isinstance(imat, list) or len(imat) != 2 or
            not isinstance(bmat, list) or len(bmat) != 2 or
            any(not isinstance(row, list) or len(row) != 2
                for row in imat + bmat)):
        raise ValueError("piecewise matrix shape changed")
    A = [[parse_q(x) for x in row] for row in imat]
    B = [[parse_q(x) for x in row] for row in bmat]
    if (A[0][1] or A[1][0] or A[0][0] <= 0 or A[1][1] <= 0 or
            B[0][1] != B[1][0] or B[0][0] <= 0 or B[1][1] <= 0):
        raise ValueError("piecewise exact reference matrix invalid")
    # Recontract every serialized row rather than trusting its Boolean/display.
    for index, row in enumerate(raw.get("rows", ())):
        a = parse_q(row.get("outer_amplitude"))
        denominator = A[0][0] + a * a * A[1][1]
        numerator = B[0][0] + 2 * a * B[0][1] + a * a * B[1][1]
        if (parse_q(row.get("exact_denominator")) != denominator or
                parse_q(row.get("exact_numerator")) != numerator or
                parse_q(row.get("exact_quotient")) !=
                numerator / denominator or
                parse_q(row.get("exact_margin")) !=
                numerator - denominator or
                row.get("margin_positive") is not (numerator > denominator)):
            raise ValueError(f"piecewise exact row {index} is inconsistent")
    return raw, A, B


def prepare_piecewise_decimal(dps: int):
    """Compile the distinct inner and outer coefficient kernels exactly."""
    if isinstance(dps, bool) or dps not in (80, 100):
        raise ValueError("dps must be 80 or 100")
    inner_bytes, basis_i, vector_i = transformed_source_bytes(INNER_C)
    outer_bytes, basis_o, vector_o = transformed_source_bytes(OUTER_C)
    if basis_i != basis_o or len(vector_i) != len(vector_o):
        raise ArithmeticError("piecewise basis mismatch")
    inner = kernel_core.compile_kernel_bytes(inner_bytes)
    outer = kernel_core.compile_kernel_bytes(outer_bytes)
    if (inner.labels != outer.labels or
            set(inner.orbit_products) != set(outer.orbit_products) or
            any(inner.orbit_products[key] != outer.orbit_products[key]
                for key in inner.orbit_products)):
        raise ArithmeticError("piecewise orbit algebra mismatch")
    # install_decimal mutates only scalar arithmetic helpers.  Both coefficient
    # kernels were already compiled exactly, and their common orbit table is
    # immutable for the remainder of this process.
    scalar = grouped.install_decimal(dict(inner.orbit_products), dps)
    return {
        "inner": inner, "outer": outer, "scalar": scalar,
        "inner_source_sha256": sha256_bytes(inner_bytes),
        "outer_source_sha256": sha256_bytes(outer_bytes),
        "basis_dimension": len(basis_i),
    }


def evaluators_for_cross(supports, kernels, scalar):
    answer = {}
    for name, support in supports.items():
        kernel_name = "inner" if name.startswith("inner") else "outer"
        answer[name] = kernel_core.KernelEvaluator(
            support, kernels[kernel_name], scalar)
    # Orbit multiplication is coefficient-independent, but fail if the two
    # compiled tables ever cease to agree.
    if kernels["inner"].orbit_products != kernels["outer"].orbit_products:
        raise ArithmeticError("cross kernels have different orbit products")
    return answer


def fused_i_shell_r(high_support, low_support, outer_kernel, scalar, r,
                    progress: bool = False):
    """Compute high-minus-low I while sharing every angular density.

    On an ``(r,h)`` face the undilated residual factor is

        (1 - (r+h) delta - z - w)^d,

    independent of which radial cutoff alpha is imposed.  The two simplexes
    therefore differ only in the terminal integration domain.  This identity
    avoids rebuilding all 2,278 D16 orbit densities for the scheduled-low
    subtraction.
    """
    if (high_support.k != low_support.k or
            high_support.delta != low_support.delta or
            getattr(high_support, "schedule", None) !=
            getattr(low_support, "schedule", None)):
        raise ValueError("fused I supports must share k/delta/schedule")
    if isinstance(r, bool) or not isinstance(r, int) or not 0 <= r <= high_support.k:
        raise ValueError("invalid I total count")
    evaluator = kernel_core.KernelEvaluator(
        high_support, outer_kernel, scalar)
    dimension = high_support.k
    max_h_high = int(high_support.alpha / high_support.delta) - r
    max_h_low = int(low_support.alpha / low_support.delta) - r
    if max_h_high < 0:
        return scalar(0), scalar(0), scalar(0), {"high": 0, "low": 0}
    constraints = ()
    if r:
        cap = high_support.beta(r) - r * high_support.delta
        if cap <= evaluator.zero:
            return scalar(0), scalar(0), scalar(0), {"high": 0, "low": 0}
        constraints = ((evaluator.one, evaluator.zero, cap),)
    raw = {(nu, degree): scalar(value.numerator) / scalar(value.denominator)
           for (nu, degree), value in outer_kernel.i_raw.items()}
    by_nu = defaultdict(list)
    for (nu, degree), coefficient in raw.items():
        by_nu[nu].append((degree, coefficient))
    high_value = evaluator.zero
    low_value = evaluator.zero
    high_faces = 0
    low_faces = 0
    for h in range(max_h_high + 1):
        outer_high = high_support.alpha - (r + h) * high_support.delta
        if outer_high <= evaluator.zero:
            continue
        residual_constant = evaluator.one - (r + h) * high_support.delta
        total_poly = defaultdict(scalar)
        for nu, terms in by_nu.items():
            density = evaluator.orbit_density(
                dimension, nu, r, h, max_h_high)
            if not density:
                continue
            residual = defaultdict(scalar)
            for degree, coefficient in terms:
                grouped.add_poly(
                    residual,
                    dict(ei._linear_power(residual_constant,
                                          -evaluator.one, -evaluator.one,
                                          degree)), coefficient)
            grouped.add_poly(total_poly,
                             ei._poly_mul(density, residual), evaluator.one)
        high_value += evaluator.integrate_domain(
            dict(total_poly), dimension, r, outer_high, constraints)
        high_faces += 1
        if h <= max_h_low:
            outer_low = low_support.alpha - (r + h) * low_support.delta
            if outer_low > evaluator.zero:
                low_value += evaluator.integrate_domain(
                    dict(total_poly), dimension, r, outer_low, constraints)
                low_faces += 1
        if progress:
            print(f"piecewise fused I r={r} h={h}/{max_h_high} "
                  f"poly={len(total_poly)}", file=sys.stderr, flush=True)
        evaluator.clear_face_caches()
    evaluator.clear_radial_caches()
    return (high_value, low_value, high_value - low_value,
            {"high": high_faces, "low": low_faces})


def cross_bundle_r(supports, kernels, scalar, pair_names, r,
                   progress: bool = False, probe_h=None):
    """Ordered, count-tagged marginal cross integrals for one common r.

    No factor two is hidden here.  If ``left`` and ``right`` differ, the
    returned table is their bilinear J entry.  A quadratic contraction later
    supplies its ordinary matrix factor two.
    """
    support_k = next(iter(supports.values())).k
    if isinstance(r, bool) or not isinstance(r, int) or not 0 <= r < support_k:
        raise ValueError("invalid common count")
    if any(support.k != support_k for support in supports.values()):
        raise ValueError("cross support dimensions disagree")
    evaluators = evaluators_for_cross(supports, kernels, scalar)
    data = {name: component_data(evaluator)
            for name, evaluator in evaluators.items()}
    tables = {tag: defaultdict(scalar) for tag, _, _ in pair_names}
    counts = {tag: 0 for tag, _, _ in pair_names}
    dimension = support_k - 1
    first = next(iter(evaluators.values()))
    max_h = int(first.support.eta / first.support.delta) - r
    if max_h < 0:
        return {tag: {} for tag, _, _ in pair_names}, counts, 0
    if probe_h is not None:
        if (isinstance(probe_h, bool) or not isinstance(probe_h, int) or
                not 0 <= probe_h <= max_h):
            raise ValueError("probe h is outside this common-count face list")
        h_values = (probe_h,)
    else:
        h_values = range(max_h + 1)
    faces = 0
    for h in h_values:
        if dimension == 0 and (r or h):
            continue
        outer = first.support.eta - (r + h) * first.support.delta
        if outer <= first.zero:
            continue
        blocks = {
            name: active_branch_blocks(
                evaluators[name], data[name], r, h, dimension, outer)
            for name in supports
        }
        faces += 1
        for tag, left_name, right_name in pair_names:
            left_eval, right_eval = (evaluators[left_name],
                                     evaluators[right_name])
            if (left_eval.support.delta != right_eval.support.delta or
                    left_eval.support.eta != right_eval.support.eta):
                raise ValueError("cross supports disagree in delta/eta")
            for left_branch in BRANCHES:
                left, lc = blocks[left_name][left_branch]
                if not left or lc is None:
                    continue
                for right_branch in BRANCHES:
                    right, rc = blocks[right_name][right_branch]
                    if not right or rc is None:
                        continue
                    constraints = lc + rc
                    if dimension and first.integrate_domain(
                            {(0, 0): first.one}, dimension, r, outer,
                            constraints) <= first.zero:
                        continue
                    combined = ordered_orbit_product(left, right, first)
                    integrand = defaultdict(scalar)
                    for nu, polynomial in combined.items():
                        density = first.orbit_density(
                            dimension, nu, r, h, max_h)
                        if density:
                            grouped.add_poly(
                                integrand, ei._poly_mul(density, polynomial),
                                first.one)
                    if not integrand:
                        continue
                    value = first.integrate_domain(
                        dict(integrand), dimension, r, outer, constraints)
                    key = (branch_total_r(r, left_branch),
                           branch_total_r(r, right_branch))
                    tables[tag][key] += value
                    counts[tag] += 1
        if progress:
            print(f"piecewise J common_r={r} h={h}/{max_h} "
                  f"counts={counts}", file=sys.stderr, flush=True)
        first.clear_face_caches(clear_marginals=True)
    first.clear_radial_caches()
    return ({tag: {key: value for key, value in table.items() if value}
             for tag, table in tables.items()}, counts, faces)


def run_stage(dps, total_r, common_r, block_tags, progress=False,
              probe_h=None):
    started = time.monotonic()
    pins = require_piecewise_pins()
    strict_piecewise_reference()
    self_start = sha256_file(FILE)
    prepared = prepare_piecewise_decimal(dps)
    scalar = prepared["scalar"]
    supports = make_supports(scalar)
    kernels = {"inner": prepared["inner"], "outer": prepared["outer"]}
    result = {
        "status": "piecewise-capped-volume-ramp-D16-Decimal-stage",
        "rigorous": False,
        "theorem_ready": False,
        "never_implies": ["rigorous interval containment", "H1<=236"],
        "parameters": {
            "k": 48, "degree": 16, "inner_c": "1",
            "outer_c": "3090/3211", "alpha_inner": "103/400",
            "eta_inner": "97/400", "alpha_outer": "3211/12000",
            "eta_outer": "3031/12000", "delta": "361/50000",
            "schedule": [canonical_q(x) for x in SCHEDULE],
        },
        "decimal_dps": dps,
        "basis_dimension": prepared["basis_dimension"],
        "inner_source_sha256": prepared["inner_source_sha256"],
        "outer_source_sha256": prepared["outer_source_sha256"],
        "source_hashes": pins,
        "script_sha256": self_start,
        "selected_counts": list(SELECTED_COUNTS),
        "cost_probe_h": probe_h,
        "complete_stage": probe_h is None,
        "i_stage": None,
        "j_stage": None,
    }
    if total_r is not None:
        before = time.monotonic()
        hi, lo, shell, faces = fused_i_shell_r(
            supports["high"], supports["low"], prepared["outer"], scalar,
            total_r, progress)
        result["i_stage"] = {
            "total_count": total_r, "high": str(hi),
            "scheduled_low": str(lo), "shell_difference": str(shell),
            "faces": faces, "shell_nonnegative_observed": shell >= scalar(0),
            "seconds": time.monotonic() - before,
        }
    if common_r is not None:
        catalog = {
            "fh": ("inner_eta2", "high"),
            "fl": ("inner_eta2", "low"),
            "hh": ("high", "high"), "hl": ("high", "low"),
            "lh": ("low", "high"), "ll": ("low", "low"),
        }
        selected = tuple((tag, *catalog[tag]) for tag in block_tags)
        needed = {name: supports[name]
                  for _, left, right in selected for name in (left, right)}
        before = time.monotonic()
        tables, counts, faces = cross_bundle_r(
            needed, kernels, scalar, selected, common_r, progress, probe_h)
        result["j_stage"] = {
            "common_count": common_r,
            "ordered_cross_semantics": True,
            "hidden_factor_two": False,
            "tables": {tag: encode_table(tables[tag])
                       for tag in block_tags},
            "branch_domain_integrals": counts,
            "faces": faces, "seconds": time.monotonic() - before,
        }
    result["wall_seconds"] = time.monotonic() - started
    result["peak_rss_kib"] = resource.getrusage(
        resource.RUSAGE_SELF).ru_maxrss
    result["child_peak_rss_kib"] = resource.getrusage(
        resource.RUSAGE_CHILDREN).ru_maxrss
    if (sha256_file(FILE) != self_start or
            require_piecewise_pins() != pins):
        raise RuntimeError("piecewise source closure changed during traversal")
    return result


def write_new(path, payload):
    target = Path(path).resolve()
    protected = {FILE.resolve(),
                 *(Path(x).resolve() for x in PINNED)}
    if target in protected:
        raise ValueError("output aliases a protected input")
    target.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    try:
        with os.fdopen(fd, "wb", closefd=False) as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        observed = os.fstat(fd)
        if not stat.S_ISREG(observed.st_mode):
            raise RuntimeError("published output is not regular")
    finally:
        os.close(fd)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--decimal-dps", type=int, choices=(80, 100),
                        default=80)
    parser.add_argument("--total-r", type=int)
    parser.add_argument("--common-r", type=int)
    parser.add_argument("--blocks", default=",".join(BLOCK_TAGS))
    parser.add_argument("--progress", action="store_true")
    parser.add_argument(
        "--cost-probe-h", type=int,
        help="evaluate only this single J h-face; output is incomplete")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--preflight-only", action="store_true")
    args = parser.parse_args()
    tags = tuple(x for x in args.blocks.split(",") if x)
    if (len(tags) != len(set(tags)) or
            any(tag not in BLOCK_TAGS for tag in tags)):
        parser.error("--blocks must be a unique CSV subset of frozen tags")
    if args.preflight_only:
        pins = require_piecewise_pins()
        validate_geometry_sources()
        _, A, B = strict_piecewise_reference()
        print(json.dumps({
            "status": "preflight-pass", "target_run_started": False,
            "script_sha256": sha256_file(FILE), "source_hashes": pins,
            "inner_c": "1", "outer_c": "3090/3211",
            "selected_counts": list(SELECTED_COUNTS),
            "uncapped_reference_inner_I": canonical_q(A[0][0]),
            "uncapped_reference_inner_kJ": canonical_q(B[0][0]),
        }, sort_keys=True, indent=2))
        return
    if args.output is None or (args.total_r is None and args.common_r is None):
        parser.error("stage requires --output and a count selector")
    for name, value in (("total-r", args.total_r),
                        ("common-r", args.common_r)):
        if value is not None and not 0 <= value <= 22:
            parser.error(f"--{name} must lie in 0..22")
    if args.cost_probe_h is not None and args.common_r is None:
        parser.error("--cost-probe-h requires --common-r")
    if args.cost_probe_h is not None and args.total_r is not None:
        parser.error("cost probes may not be mixed with a complete I stage")
    result = run_stage(args.decimal_dps, args.total_r, args.common_r,
                       tags, args.progress, args.cost_probe_h)
    payload = (json.dumps(result, sort_keys=True, separators=(",", ":"),
                          allow_nan=False) + "\n").encode("ascii")
    write_new(args.output, payload)
    print(json.dumps({"artifact_sha256": sha256_bytes(payload),
                      "wall_seconds": result["wall_seconds"],
                      "peak_rss_kib": result["peak_rss_kib"],
                      "i_stage": result["i_stage"],
                      "j_counts": (None if result["j_stage"] is None else
                                   result["j_stage"][
                                       "branch_domain_integrals"])},
                     sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
